"""Main space exploration screen with ships and landing."""
import pygame
import math
import game.constants as constants
from game.constants import GAME_WIDTH, GAME_HEIGHT, CAMERA_ZOOM, BLACK, YELLOW, WHITE, GREEN, GRAY, CYAN, RED
from game.utils import (
    get_scale, get_offset, get_ui_scale, load_json, set_camera_offset, set_camera_angle, set_camera_zoom,
    draw_debug_marker, draw_target_brackets, get_font, to_world,
    get_ship_type, get_graphics_asset, get_pilot, get_star_systems, get_ship_outfit,
    get_asteroid_type, get_missions, get_story
)
import game.utils as utils
from game.perf_metrics import metrics as perf
from game.audio.sound_board import sound_board
from game.ui.ui_theme import draw_glass_panel, draw_glow_message, draw_controls_pane, draw_status_pane, draw_info_panel, draw_message_log, side_panel_width, hud_margin, MESSAGE_ALERT_FRAMES, message_alert_state
from game.screens.screen_base import ScreenBase
from game.screens.location_screen import LocationScreen
from game.world.player_controller import PlayerController
from game.world.autopilot import has_arrived
from game.world.character import Character, resolve_routine_class
from game.world.orbit_player_routine import OrbitPlayerRoutine
from game.world.dialogue import option_actions, apply_shared_actions
from game.world.mission import start_mission, check_mission_progress
from game.world.landing_site import LandingSite
from game.world.starfield import StarField
from game.world.central_star import CentralStar
from game.world.celestial_body import CelestialBody
from game.world.asteroid_field import AsteroidField
from game.world.system_state import SystemState

# Hailing tuning
ONE_WAY_HAIL_RANGE = 500          # world units - how close an NPC-initiated hail can trigger from
ONE_WAY_HAIL_BANNER_FRAMES = 300  # ~5s at 60fps an incoming-hail banner stays up
HAIL_BUSY_BANNER_FRAMES = 150     # ~2.5s "no response" flash when hailing a docked/ashore pilot

# How slow (units/frame) counts as "braked to a stop" for the generic
# "braked_below_threshold" gameplay-event flag (see update_physics) - a
# mission's braking-practice stage can use this as its complete_flag.
# story.json's "brake_slow_threshold" overrides this per story (see
# SpaceScreen.brake_slow_threshold).
BRAKE_SLOW_THRESHOLD = 0.3

# Jump mechanic tuning - defaults; story.json's "jump" block overrides
# travel_frames / speed / arrival_distance / self_min_distance per story
# (see SpaceScreen.jump_* instance attributes, which is what the jump code
# actually reads - these module names are only the fallback).
JUMP_TRAVEL_FRAMES = 150        # ~2.5s at 60fps of high-speed travel
JUMP_SPEED = 40                 # world units/frame while traveling
JUMP_ARRIVAL_DISTANCE = 1400    # world units from system center on arrival
JUMP_SELF_MIN_DISTANCE = 3200   # must be at least this far from center to jump "back" -
# roughly the point where the station/moon have scrolled off the edge of the
# minimap (MINIMAP_RANGE, plus their own offset from center), so "far enough
# to jump" lines up with "you can't see home on radar anymore". Not exact -
# the minimap's reach varies a little with window aspect - and doesn't need
# to be.

# ~4s at 60fps a transient toast (jump done, mission start/stage/finish) stays up
TOAST_FRAMES = 240
# MESSAGE_ALERT_FRAMES (how long the Message Log's "unread" light is active
# after a message) now lives in ui_theme alongside the blink/ping schedule -
# imported above.
SYSTEM_CENTER = (GAME_WIDTH / 2, GAME_HEIGHT / 2)

# Degrees per frame the view rotates while Q/E is held (see handle_input).
# Purely a camera/view setting - never touches ship heading or physics.
CAMERA_ROTATE_SPEED = 2

# Minimap tuning - its on-screen size now tracks the shared side-panel width
# (see ui_theme.side_panel_width); this is just the radar's world reach.
MINIMAP_RANGE = 2600   # world units from player (center) to the minimap's edge

# Targeting modes - cycled with Tab, filters what T/[/] can select.
# "MISC" covers everything that's neither a ship nor a landing site (celestial
# bodies, the central star). LANDING SITES is the default since finding and
# landing on the station is the first thing a new pilot needs to target.
TARGET_MODES = ["SHIPS", "LANDING SITES", "MISC"]


class SpaceScreen(ScreenBase):
    """Main space exploration screen with ships and landing."""
    def __init__(self, system_config=None, pilot_name="", story="default", system_id=None):
        super().__init__(pilot_name=pilot_name)
        self.story = story  # fixed for the whole playthrough - stories are wholly separate

        # Load story metadata (player ship type, starting system, etc)
        story_meta = get_story(story)
        self.system_id = system_id or story_meta.get("starting_system", "default")
        # Recorded into every save (see main.py's build_save_game_state) so
        # a save always knows which version of the story it was made
        # against - bump story.json's "version" whenever a change to that
        # story's config or this game's state-handling code would make an
        # existing save behave differently once reloaded (see CLAUDE.md's
        # "Save Compatibility & Story Versioning" section).
        self.story_version = story_meta.get("version", "0.0.0")
        # Static mission definitions for this story (title + ordered stages -
        # see game/world/mission.py); which mission(s) a player actually has
        # active/completed is state on their own Possessions, not here.
        self.missions_config = get_missions(story)
        # Which mission (if any) automatically starts as the player enters
        # the game - config-driven so a story can opt into (or change, or
        # omit) a tutorial mission without touching this class. None = no
        # auto-started mission.
        self.starting_mission = story_meta.get("starting_mission")
        # When that mission fires: "ship_purchase" (default - the first time
        # the player buys a ship, see _on_ship_purchased) or "new_game" (the
        # moment a fresh game begins, see begin_new_game). A story that hands
        # the player a starting ship gets "new_game" behaviour automatically,
        # since no purchase ever happens.
        self.starting_mission_trigger = story_meta.get("starting_mission_trigger", "ship_purchase")
        # story.json's "start" block: the player's state at the beginning of
        # a brand-new game - starting credits/ship/spare outfits/personal
        # items/story flags, plus where in the world they begin ("location":
        # "station"/"moon"/"space", "interior": which interior key). Applied
        # by _apply_start_config() (state) + begin_new_game() (placement);
        # a loaded save overwrites all of this via restore_possessions().
        self.start_config = story_meta.get("start", {})
        # graphics.json "outfits" id worn by the player and every AI pilot
        # (station/moon NPCs pick their own per-config, see LocationScreen).
        self.default_outfit_id = story_meta.get("default_outfit", "space_suit")
        # World-render magnification for this story (UI scale is unaffected).
        # Global camera state - safe to set here since a session is only
        # ever in one story, and only a live SpaceScreen renders the world.
        set_camera_zoom(story_meta.get("camera_zoom", CAMERA_ZOOM))
        # Per-story tuning overrides (module-level names above are the
        # defaults / JumpDrive's own fallback).
        self.brake_slow_threshold = story_meta.get("brake_slow_threshold", BRAKE_SLOW_THRESHOLD)
        jump_cfg = story_meta.get("jump", {})
        self.jump_travel_frames = jump_cfg.get("travel_frames", JUMP_TRAVEL_FRAMES)
        self.jump_speed = jump_cfg.get("speed", JUMP_SPEED)
        self.jump_arrival_distance = jump_cfg.get("arrival_distance", JUMP_ARRIVAL_DISTANCE)
        self.jump_self_min_distance = jump_cfg.get("self_min_distance", JUMP_SELF_MIN_DISTANCE)

        # Load config for the current system within this story
        self.system_config = system_config or load_json(f"config/stories/{story}/systems/{self.system_id}.json") or {}

        # Get space system drag (default 0 = no drag)
        space_drag = self.system_config.get("drag", 0)

        # Placeholder ship stats/graphics for self.player before any ship is
        # actually owned - PlayerController always needs a Ship object to
        # exist, but a new pilot starts on foot in the station with none, and
        # this placeholder is never flown or even rendered until one is
        # bought (see _apply_ship_type()/_on_ship_purchased(), which
        # reconfigure it for real at that point). "player_type" should
        # normally stay null for that reason - a non-null value here does
        # NOT actually grant the player a starting ship (LocationScreen.
        # ship_available is driven entirely by Possessions.owned_ships,
        # which starts empty regardless), it would just be misleading
        # placeholder stats nobody sees.
        player_ship_type_id = story_meta.get("ships", {}).get("player_type")
        player_ship_type = get_ship_type(self.story, player_ship_type_id) if player_ship_type_id else None
        player_graphics = get_graphics_asset(self.story, "ships", player_ship_type_id) if player_ship_type_id else None

        # Spawn away from map center by default, since that's where a central
        # star (if the system has one) usually sits.
        player_start_cfg = self.system_config.get("player_start", {})
        player_x = GAME_WIDTH * player_start_cfg.get("x", 0.4)
        player_y = GAME_HEIGHT * player_start_cfg.get("y", 0.35)
        self.player = PlayerController(player_x, player_y, space_drag=space_drag, graphics=player_graphics, ship_type=player_ship_type, pilot_name=pilot_name, outfit=get_graphics_asset(self.story, "outfits", self.default_outfit_id))
        self._apply_start_config()

        # Every system this story defines gets built and kept simulating for
        # the whole session - not just whichever one the player currently
        # occupies (see SystemState, update_physics() below, and main.py's
        # update_background_locations(), which now walks every system's
        # cached interiors the same way it already did for the current
        # one). get_star_systems() discovers them all from
        # config/stories/{story}/systems/*.json; self.system_id is added
        # explicitly in case a save/story references one that scan somehow
        # missed, so activating it below can never KeyError.
        self.systems = {}
        self.system_configs = {}
        system_ids = set(get_star_systems(self.story).keys())
        system_ids.add(self.system_id)
        for sid in system_ids:
            config = self.system_config if sid == self.system_id else (load_json(f"config/stories/{story}/systems/{sid}.json") or {})
            self.system_configs[sid] = config
            self.systems[sid] = self._build_system_state(sid, config)
        self._activate_system(self.system_id)

        self.landing_text = 0
        self.landing_target = None
        self.camera_x = 0
        self.camera_y = 0
        # View rotation (degrees) applied to the whole Space View, driven by
        # Q/E. Player-preference view state only - not saved, not game state,
        # and reset to north-up (0) by interiors when the player lands.
        self.camera_angle = 0
        # Star map selection, for the Jump mechanic - never None: defaults to
        # (and resets to, after a jump) the current system, so "Jump Target"
        # always names somewhere and J is always meaningful.
        self.selected_system_id = self.system_id
        # True once the player is actually out flying (set by board_ship() /
        # every update() frame, cleared by park_at() and _mark_landed()).
        # update_physics() also runs in the background while the player is
        # docked in an interior - things that should only happen in the
        # cockpit (this story's starting_mission firing, an NPC's proximity
        # one-way hail) gate on this so they don't go off mid-conversation
        # in a station bar. See _on_ship_purchased / _check_one_way_hails.
        self.in_flight = False
        # Set by _on_ship_purchased when the starting_mission trigger is
        # "ship_purchase": the mission is armed here but only actually
        # started once the player launches (board_ship()), so the tutorial
        # toast and Kade's opening hail don't land while they're still
        # walking around the station having just bought the ship. Lives on
        # possessions.flags so it survives a save made in that gap.
        self.jump_state = None  # None, or a dict tracking the jump animation
        self.jump_message_timer = 0  # Transient "too close to jump" feedback
        # Transient center-screen toast (see _show_toast) - jump completion,
        # mission started / stage completed / mission finished.
        self.toast_text = None
        self.toast_color = CYAN
        self.toast_timer = 0
        self.active_dialogue = None  # Set to a hailed pilot's Dialogue while a hail is open (see handle_input's K_h)
        self.hail_banner = None  # (text, color) for a transient hail-related message (see below)
        self.hail_banner_timer = 0
        # HUD panel rects from the most recently drawn frame - a mouse click
        # on one of them (minimap, info panel, controls, status) shouldn't
        # also be interpreted as a click-to-target in the world behind it.
        # One frame stale by construction (draw() runs after handle_input()
        # each loop), which is fine since these panels don't move frame to
        # frame.
        self._hud_click_rects = []
        # Minimap panel rect + the plotted blips (screen_x, screen_y,
        # hit_radius, obj) from the last drawn frame, so handle_input() can
        # click-to-target a blip and _draw_minimap() can show hover text for
        # whichever one the pointer is over (see _minimap_blip_at). One frame
        # stale, same as _hud_click_rects.
        self._minimap_rect = None
        self._minimap_blips = []
        # Mouse-wheel scroll offsets (in lines) for the two scrollable HUD
        # side panes - the bottom-left Message Log and the top-right
        # targeting/info pane - plus each pane's rect from the last drawn
        # frame, for wheel hit-testing (see handle_input / _draw_hud). The
        # message scroll resets to 0 (newest) whenever one arrives
        # (_post_message).
        self.message_log_scroll = 0
        self._message_log_rect = None
        # Set by _draw_hud from draw_message_log's return each frame - see the
        # matching field/usage in LocationScreen (drives the
        # "scrolled_message_log" tutorial flag).
        self._message_log_max_scroll = 0
        self.info_panel_scroll = 0
        self._info_panel_rect = None
        # Frames left on the Message Log's blinking red "new message" light
        # (see MESSAGE_ALERT_FRAMES / _post_message / draw_message_log), and
        # how many of the MESSAGE_ALERT_BLINKS pings have sounded for the
        # current alert (reset in _post_message, advanced in update()).
        self.message_alert_timer = 0
        self._message_alert_pings_played = 0

    def _build_asteroid_types(self, config):
        """Resolve a system's "asteroid_field.types" entries (each just a
        {"type": asteroid_types.json id, "weight": ..., "size_range": ...,
        "speed_range": ...}) into the fully-populated list AsteroidField
        expects - looking up each "type" id's shape/color/jaggedness/spin
        from the story's shared asteroid_types.json, same split as ship_type
        id -> ship_types.json for AI ships above. Falls back to a single
        default gray/round type if the system defines no "asteroid_field"
        block at all, so existing system configs keep working unchanged."""
        type_entries = config.get("asteroid_field", {}).get("types", [{"type": "gray_rock", "weight": 1}])
        types = []
        for entry in type_entries:
            resolved = {"graphics": get_asteroid_type(self.story, entry.get("type", "gray_rock")), "weight": entry.get("weight", 1)}
            if "size_range" in entry:
                resolved["size_range"] = entry["size_range"]
            if "speed_range" in entry:
                resolved["speed_range"] = entry["speed_range"]
            types.append(resolved)
        return types

    def _build_system_state(self, system_id, config):
        """Build a SystemState (station/moon/central star/celestial bodies/
        AI ships) from one system's static config - called once per system
        the story defines (see self.systems), so every system exists and
        keeps simulating for the rest of the session, not just whichever
        one is active. Asteroid/star fields are built here too, but live on
        SystemState only as scenery kept alive between visits - see
        SystemState's docstring for why only the active system's copies
        ever get their own update() call."""
        space_drag = config.get("drag", 0)

        station_asset_id = config.get("station_asset", "station_alpha")
        moon_asset_id = config.get("moon_asset", "moon_silver")

        station_cfg = config.get("station", {})
        station_graphics = get_graphics_asset(self.story, "space_stations", station_asset_id)
        station = LandingSite(GAME_WIDTH * station_cfg.get("x", 0.75), GAME_HEIGHT * station_cfg.get("y", 0.3), graphics=station_graphics, interiors=station_cfg.get("interiors", {}), name=station_cfg.get("name", "Station"))

        moon_cfg = config.get("moon", {})
        moon_graphics = get_graphics_asset(self.story, "moons", moon_asset_id)
        moon = LandingSite(GAME_WIDTH * moon_cfg.get("x", 0.2), GAME_HEIGHT * moon_cfg.get("y", 0.4), graphics=moon_graphics, interiors=moon_cfg.get("interiors", {}), name=moon_cfg.get("name", "Moon"))

        # Central star (optional, drawn but not a landing site/targetable)
        central_star_cfg = config.get("central_star")
        central_star = CentralStar(GAME_WIDTH * central_star_cfg.get("x", 0.5), GAME_HEIGHT * central_star_cfg.get("y", 0.5), graphics=central_star_cfg) if central_star_cfg else None

        # Non-landing-site planets/ice balls/gas giants - just scenery to fly near,
        # never something you can dock at (see CelestialBody.hazardous, used
        # by the HUD's targeting note).
        celestial_bodies = [
            CelestialBody(GAME_WIDTH * body_cfg.get("x", 0.5), GAME_HEIGHT * body_cfg.get("y", 0.5), graphics=body_cfg)
            for body_cfg in config.get("celestial_bodies", [])
        ]

        state = SystemState(station, moon, central_star, celestial_bodies, ai_ships=[], space_drag=space_drag)
        state.star_field = StarField(seed=config.get("star_seed", 0))
        # No seed passed - unlike StarField, AsteroidField is meant to look
        # different every time (see its docstring), including the very
        # first chunks generated at game start, not just on revisit.
        state.asteroid_field = AsteroidField(
            types=self._build_asteroid_types(config),
            per_chunk_range=config.get("asteroid_field", {}).get("per_chunk_range", (1, 3)),
        )
        # Registered before AI ships are built below (not after) because
        # Character.__init__ runs its routine's start() synchronously -
        # ExplorerRoutine's needs to find this very system already in
        # self.systems the moment the first explorer is constructed.
        self.systems[system_id] = state

        # LandingSites that an AI ship's route config can reference by key
        landing_site_lookup = {"station": station, "moon": moon}

        for ai_cfg in config.get("ai_ships", []):
            ship_type_id = ai_cfg.get("ship_type", "freighter")
            ship_type = get_ship_type(self.story, ship_type_id)
            ship_graphics = get_graphics_asset(self.story, "ships", ship_type_id)
            pilot = get_pilot(self.story, ai_cfg["pilot"]) if "pilot" in ai_cfg else None
            route = [landing_site_lookup[key] for key in ai_cfg.get("route", []) if key in landing_site_lookup]
            ai_ship = Character.for_ai_pilot(
                GAME_WIDTH * ai_cfg.get("x", 0.75),
                GAME_HEIGHT * ai_cfg.get("y", 0.1),
                ship_type=ship_type,
                ship_type_id=ship_type_id,
                graphics=ship_graphics,
                pilot=pilot,
                route=route,
                get_interior_screen=self.get_interior_screen,
                space_drag=space_drag,
                outfit=get_graphics_asset(self.story, "outfits", self.default_outfit_id),
                systems=self.systems,
                system_id=system_id
            )
            state.ai_ships.append(ai_ship)

        return state

    def _activate_system(self, system_id):
        """Point every per-system alias (station/moon/ai_ships/...) at the
        already-built SystemState for system_id - called at construction
        and again after a jump completes. Never rebuilds anything (every
        system is built once, in _build_system_state, and kept alive for
        the whole session), and never touches the player except to
        re-apply the destination's own space drag."""
        self.system_id = system_id
        self.system_config = self.system_configs[system_id]
        state = self.systems[system_id]
        self.player.ship.space_drag = state.space_drag

        self.station = state.station
        self.moon = state.moon
        self.central_star = state.central_star
        self.celestial_bodies = state.celestial_bodies
        self.star_field = state.star_field
        self.asteroid_field = state.asteroid_field
        self.ai_ships = state.ai_ships
        # Keep self.ai_ship for backwards compatibility (first ship if it exists)
        self.ai_ship = state.ai_ships[0] if state.ai_ships else None

        self.current_target = None
        self.target_mode_index = TARGET_MODES.index("LANDING SITES")
        self.targetable_objects = [
            (self.station.name, self.station),
            (self.moon.name, self.moon),
        ]
        if self.central_star:
            self.targetable_objects.append((self.central_star.name, self.central_star))
        for body in self.celestial_bodies:
            self.targetable_objects.append((body.name, body))
        # Add all AI ships to targetable objects. Pilot name is shown
        # separately in the HUD (Character.person.name), not folded into
        # this label, so it stays just the ship type.
        for i, ship in enumerate(self.ai_ships):
            self.targetable_objects.append((self._ship_target_label(ship, i), ship))

    def _ship_target_label(self, ship, index=0):
        """HUD label for an AI ship in targetable_objects - just the ship
        type's display name (the pilot name is shown separately)."""
        ship_type = get_ship_type(self.story, ship.ship_type_id)
        return ship_type.get("name", f"AI Ship {index + 1}")

    def _approaching_label(self, obj):
        """Short name for whatever the autopilot is currently seeking, for
        the "Approaching: ..." status line - a ship's type display name
        (matching the targeting HUD's own label), or a landing site / body's
        own name."""
        if isinstance(obj, Character):
            return self._ship_target_label(obj)
        return getattr(obj, "name", "target")

    def get_interior_screen(self, landing_site, key):
        """Return the persistent LocationScreen for one of landing_site's
        interiors (key = "default" for a station, "city"/"wilderness" for
        the moon), creating and caching it on landing_site.interior_screens the
        first time it's visited. Later visits reuse the same instance, so
        NPCs and the player's position within it persist instead of
        resetting every time - and it can keep simulating in the
        background (see update_physics() calls in main.py) while the
        player is elsewhere. Returns None if the interior isn't configured.
        Sized from landing_site.interior_world_size, not a caller-supplied
        width/height - every call site used to pass the same 800x600/
        1600x1600 pair derived from is_station itself; asking the landing_site
        keeps that in one place.
        """
        world_width, world_height = landing_site.interior_world_size
        if key in landing_site.interior_screens:
            return landing_site.interior_screens[key]

        interior_config = landing_site.interiors.get(key)
        if not interior_config:
            return None

        # Display name for every sibling interior this location's portals
        # might connect to (see LocationScreen._display_name) - built from
        # landing_site.interiors directly rather than lazily inside
        # LocationScreen, since that dict (and any config files it points
        # to) belongs to the landing_site, not to any one interior within it.
        location_labels = {}
        for sibling_key, sibling_config in landing_site.interiors.items():
            sibling_config = load_json(sibling_config) if isinstance(sibling_config, str) else sibling_config
            location_labels[sibling_key] = (sibling_config or {}).get("label", sibling_key)

        if isinstance(interior_config, str):
            screen = LocationScreen(config_file=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story, player_possessions=self.player.person.possessions, on_ship_purchased=self._on_ship_purchased, location_labels=location_labels)
        else:
            screen = LocationScreen(config_data=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story, player_possessions=self.player.person.possessions, on_ship_purchased=self._on_ship_purchased, location_labels=location_labels)
        # Which interiors key this is (e.g. "default" for a station,
        # "city"/"wilderness" for a moon) - recorded into a save as
        # station_location / moon_location (see main.py's
        # build_save_game_state; only moon_location is honoured on load).
        screen.interior_key = key
        landing_site.interior_screens[key] = screen
        return screen

    def _apply_ship_type(self, ship_type_id):
        """Configure the player's real ship's stats/graphics to match
        ship_type_id - reapplies the same stat block __init__ applies from
        story.json's starting ship. Used both right after a purchase and
        (via restore_state) after loading a save, since __init__ always
        starts the player's placeholder Ship from story.json's default
        type - a save must re-equip whatever was actually last bought,
        or a save/load round-trip would silently revert to that default."""
        ship_type = get_ship_type(self.story, ship_type_id)
        graphics = get_graphics_asset(self.story, "ships", ship_type_id)
        self.player.ship.apply_ship_type(ship_type)
        self.player.ship.graphics = graphics
        # Re-apply installed outfits' stat modifiers on top of the fresh base
        # stats - covers both the purchase path (_on_ship_purchased) and the
        # load path (restore_possessions), since both funnel through here.
        installed = self.player.person.possessions.installed_outfits
        outfits = [get_ship_outfit(self.story, outfit_id) for outfit_id in installed.values()]
        self.player.ship.apply_outfits(outfits)

    def reapply_outfits(self):
        """Re-apply the current ship's installed outfit stat modifiers -
        call after any outfit equip/unequip (OutfittingMenu, via main.py's
        build_shop_menu) so thrust/velocity/cargo capacity update
        immediately instead of only on the next save/load. Just re-runs
        _apply_ship_type on whatever ship is currently flown, since that
        already re-reads installed_outfits every time (see there)."""
        owned_ships = self.player.person.possessions.owned_ships
        if owned_ships:
            self._apply_ship_type(owned_ships[-1])

    def _apply_start_config(self):
        """Seed the player's Possessions from story.json's "start" block -
        starting credits, a starting ship, spare outfits, personal items,
        and story flags. Runs unconditionally in __init__ (exactly like the
        placeholder ship is always built from story.json's default type):
        for a loaded save it's immediately overwritten by
        restore_possessions(); for a new game it is the actual starting
        state. Placement in the world and the tutorial hand-off happen
        separately in begin_new_game(), which main.py calls only for a
        fresh game."""
        start = self.start_config
        possessions = self.player.person.possessions
        possessions.credits = start.get("credits", possessions.credits)
        for item_id, qty in start.get("items", {}).items():
            possessions.add_item(item_id, qty)
        for outfit_id in start.get("outfits", []):
            possessions.add_outfit(outfit_id)
        for flag_name, value in start.get("flags", {}).items():
            possessions.flags[flag_name] = value
        starting_ship = start.get("ship")
        if starting_ship:
            possessions.add_ship(starting_ship)
            self._apply_ship_type(starting_ship)

    def begin_new_game(self):
        """One-time setup for a brand-new game (never a load): arm the
        story's tutorial mission if its trigger is "new_game" (or if the
        story handed the player a ship, so the "ship_purchase" trigger
        would never get a chance to). Returns (location, interior_key) for
        main.py - where to drop the player: ("space", None),
        ("station", <key>) or ("moon", <key>). Parks a starting ship at
        that landing_site so boarding out from the interior works the same as
        after a purchase."""
        start = self.start_config
        location = start.get("location", "station")
        interior = start.get("interior", "default")
        if self.starting_mission and (
            self.starting_mission_trigger == "new_game"
            or self.player.person.possessions.owned_ships
        ):
            if location == "space":
                self._start_tutorial_mission()
            else:
                # Starting docked - defer to the first launch (board_ship())
                # so the opening toast/hail land in the cockpit, not the bar.
                self.player.person.possessions.flags["starting_mission_armed"] = True
        if self.player.person.possessions.owned_ships:
            if location == "moon":
                self.park_at(self.moon)
            elif location == "station":
                self.park_at(self.station)
        return (location, None if location == "space" else interior)

    def _start_tutorial_mission(self):
        """Start story.json's starting_mission (a no-op if it's already
        active or completed, so a second trigger - buying another ship -
        never restarts it), announcing it with the same toast + first-stage
        message the purchase path uses."""
        if not self.starting_mission:
            return
        started = start_mission(self.missions_config, self.player.person.possessions, self.starting_mission)
        if started:
            title = self.missions_config.get(started[0], {}).get("title", started[0])
            self._show_toast(f"Mission started: {title}", GREEN)
        self._deliver_stage_message(started)

    def _on_ship_purchased(self, ship_type_id):
        """Configure the player's real ship to match a newly bought type,
        and park it right at the station - so it's "docked outside" exactly
        as a salesman's dialogue would say, ready the moment the player
        boards through the spaceport's exit. For a "ship_purchase" trigger
        this also *arms* the story's starting_mission - it doesn't start
        until the player actually launches (board_ship()), so the tutorial
        and Kade's opening hail don't fire while they're still standing in
        the shop having just bought the ship."""
        self._apply_ship_type(ship_type_id)
        self.park_at(self.station)
        possessions = self.player.person.possessions
        if (self.starting_mission_trigger == "ship_purchase" and self.starting_mission
                and self.starting_mission not in possessions.missions
                and self.starting_mission not in possessions.completed_missions):
            possessions.flags["starting_mission_armed"] = True

    def board_ship(self):
        """The player has launched from a docked interior back into space
        (main.py's interior -> game transitions call this; update() also
        calls it every flight frame as a catch-all for save-load-into-space
        and any missed transition). Marks the ship in flight and starts a
        starting_mission that _on_ship_purchased armed but deferred until
        launch - idempotent, safe to call every frame."""
        self.in_flight = True
        if self.player.person.possessions.flags.get("starting_mission_armed"):
            self.player.person.possessions.flags["starting_mission_armed"] = False
            self._start_tutorial_mission()

    def park_at(self, landing_site):
        """Position the player's ship at `landing_site`'s own space position
        and stop it - used both right after a purchase and when loading
        directly into a station/moon save (no actual flight/landing
        happened this session, so the ship has to be placed there
        explicitly rather than restored from a save - see
        restore_possessions() and main.py's load handling)."""
        self.player.x, self.player.y = landing_site.x, landing_site.y
        self.player.park()
        self.in_flight = False

    def handle_input(self, events):
        keys = pygame.key.get_pressed()
        # Manual rotation/thrust are locked out during a jump - _update_jump()
        # drives the ship's angle (align phase) and reads it straight back
        # into velocity every frame (travel phase, see _update_jump()), so a
        # held turn key during travel would otherwise silently steer the
        # jump off its heading instead of it being a fixed, committed course.
        # Also locked out while a hail is open (self.active_dialogue) - same
        # reason LocationScreen pauses movement for its own active_dialogue.
        if not self.jump_state and not self.active_dialogue:
            self.player.handle_input(keys)

        # Rotate the view (Q/E) - held, like ship turning. Allowed even
        # mid-jump (it's only the camera), blocked only while a hail has
        # input focus, same as flight controls.
        if not self.active_dialogue:
            if keys[pygame.K_q]:
                self.camera_angle = (self.camera_angle - CAMERA_ROTATE_SPEED) % 360
            if keys[pygame.K_e]:
                self.camera_angle = (self.camera_angle + CAMERA_ROTATE_SPEED) % 360

        for event in events:
            # An open hail is mouse-only and swallows all input: hover
            # highlights an option, a click picks it, the ✕ closes.
            if self.active_dialogue:
                if event.type == pygame.MOUSEMOTION:
                    hovered = self.active_dialogue.option_at(event.pos)
                    if hovered is not None:
                        self.active_dialogue.selected_option = hovered
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.active_dialogue.close_at(event.pos):
                        self.active_dialogue = None
                    else:
                        picked = self.active_dialogue.option_at(event.pos)
                        if picked is not None:
                            self._choose_hail_option(picked)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self._choose_hail_option(self.active_dialogue.selected_option)
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # A click on the minimap targets the blip under the pointer
                # (if any - a click on empty radar does nothing); a click
                # anywhere in the world that isn't on a HUD panel targets
                # whatever object was clicked directly.
                if self._minimap_rect and self._minimap_rect.collidepoint(event.pos):
                    blip_obj = self._minimap_blip_at(event.pos)
                    if blip_obj is not None:
                        self._select_target(blip_obj)
                elif not any(rect.collidepoint(event.pos) for rect in self._hud_click_rects):
                    self._select_target_at(*to_world(*event.pos))
                continue

            if event.type == pygame.MOUSEWHEEL:
                # Scroll whichever scrollable side pane the pointer is over -
                # the Message Log (bottom-left) or the targeting/info pane
                # (top-right). Wheel up (event.y > 0) moves toward the top;
                # the upper bound is clamped against max_scroll in _draw_hud
                # once each pane's real line count is known.
                mouse_pos = pygame.mouse.get_pos()
                if self._message_log_rect and self._message_log_rect.collidepoint(mouse_pos):
                    self.message_log_scroll = max(0, self.message_log_scroll - event.y)
                    if self._message_log_max_scroll > 0:
                        self.player.person.possessions.flags["scrolled_message_log"] = True
                elif self._info_panel_rect and self._info_panel_rect.collidepoint(mouse_pos):
                    self.info_panel_scroll = max(0, self.info_panel_scroll - event.y)
                continue

            if event.type != pygame.KEYDOWN:
                continue

            # Cancel autopilot on any key press (except ESC which handles
            # pause, and Q/E which only rotate the view - not a flight input)
            if self.player.autopilot_active and event.key not in (pygame.K_ESCAPE, pygame.K_q, pygame.K_e):
                self.player.autopilot_active = False
                self.player.autopilot_target = None
                return None

            if event.key == pygame.K_ESCAPE:
                return "pause"
            elif event.key == pygame.K_RIGHTBRACKET:
                self._cycle_target(1)
            elif event.key == pygame.K_LEFTBRACKET:
                self._cycle_target(-1)
            elif event.key == pygame.K_t:
                self._cycle_target_mode()
            elif event.key == pygame.K_h:
                self._start_hail()
            elif event.key == pygame.K_l:
                # Land only - never engages autopilot (see K_SPACE below
                # for that). If a landing site is targeted and already in
                # range, land on it directly; otherwise fall back to a
                # pure proximity check, which also covers an AI ship
                # being targeted or nothing being targeted at all.
                target_obj = self._get_target_object()
                if target_obj and self.current_target is not None and not isinstance(target_obj, Character):
                    distance = target_obj.get_distance(self.player.x, self.player.y)
                    speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
                    if distance < target_obj.landing_distance and speed < 0.4:
                        if target_obj == self.station:
                            self.landing_target = "station"
                            self._mark_landed()
                            return "land"
                        elif target_obj == self.moon:
                            self.landing_target = "moon"
                            self._mark_landed()
                            return "land"
                landing_target = self._check_landing()
                if landing_target:
                    self.landing_target = landing_target
                    self._mark_landed()
                    return "land"
            elif event.key == pygame.K_SPACE:
                # Engage autopilot toward the current target - follows an
                # AI ship, or approaches a landing site from any range (L
                # only lands once you're already close).
                target_obj = self._get_target_object()
                if target_obj and self.current_target is not None:
                    self.player.engage_seek(target_obj)
                    sound_board.play("confirm")
                    if isinstance(target_obj, Character):
                        # Generic gameplay-event flag (see the docstring on
                        # the "Hailing tuning" flags above) - any story's
                        # missions.json can use this as a stage's
                        # complete_flag without this class knowing about
                        # missions at all.
                        self.player.person.possessions.flags["used_autopilot_on_ship"] = True
            elif event.key == pygame.K_m and not self.jump_state:
                return "star_map"
            elif event.key == pygame.K_j and not self.jump_state:
                self.try_jump()
            elif event.key == pygame.K_p:
                return "possessions"
            elif event.key == pygame.K_n:
                # Generic gameplay-event flag (see K_SPACE's comment) - a
                # mission stage can use "viewed_mission_log" as its
                # complete_flag (see missions.json's first_flight).
                self.player.person.possessions.flags["viewed_mission_log"] = True
                return "missions"
            elif event.key == pygame.K_c:
                self._toggle_controls()
        return None

    def _mark_landed(self):
        """Set the generic "landed_on_landing_site" gameplay-event flag -
        called from every path that actually lands the ship (manual L,
        and update()'s auto-land-on-autopilot-arrival). See K_SPACE's own
        comment above for why this lives on Possessions.flags rather than
        a SpaceScreen-only field."""
        self.player.person.possessions.flags["landed_on_landing_site"] = True
        self.in_flight = False  # main.py is about to swap to the interior screen

    def _select_target_at(self, world_x, world_y):
        """Target whichever targetable object world_x/world_y falls within
        (closest one wins on overlap) - the click-to-target counterpart to
        cycling with []. current_target is always an index into the
        *filtered* list for whichever mode is active (see _filtered_targets),
        and a click has no mode of its own, so it infers one from what was
        actually clicked and switches target_mode_index to match before
        resolving the index, rather than requiring the player to already be
        in the right mode for whatever they click on."""
        best_obj, best_dist = None, None
        for _, obj in self.targetable_objects:
            radius = obj.ship.size if isinstance(obj, Character) else getattr(obj, "size", 20)
            distance = math.sqrt((obj.x - world_x) ** 2 + (obj.y - world_y) ** 2)
            if distance <= radius + 12 and (best_dist is None or distance < best_dist):
                best_obj, best_dist = obj, distance
        if best_obj is not None:
            self._select_target(best_obj)

    def _select_target(self, obj):
        """Point current_target at obj, inferring the target mode from what
        obj is and switching target_mode_index to match first (a click - on
        the world via _select_target_at, or on the minimap via handle_input -
        carries no mode of its own). current_target is an index into the
        filtered list for that mode (see _filtered_targets). No-op if obj
        somehow isn't in that list."""
        mode = "SHIPS" if isinstance(obj, Character) else "LANDING SITES" if isinstance(obj, LandingSite) else "MISC"
        self.target_mode_index = TARGET_MODES.index(mode)
        for i, (_, candidate) in enumerate(self._filtered_targets()):
            if candidate is obj:
                self.current_target = i
                sound_board.play("blip")
                return

    def _minimap_blip_at(self, pos):
        """The targetable object whose minimap blip is under screen point
        `pos` (closest wins on overlap), or None. Backs both the minimap
        hover text and minimap click-to-target - see _draw_minimap /
        handle_input. Reads _minimap_blips from the last drawn frame."""
        best_obj, best_dist = None, None
        for sx, sy, hit_r, obj in self._minimap_blips:
            d = math.hypot(sx - pos[0], sy - pos[1])
            if d <= hit_r and (best_dist is None or d < best_dist):
                best_obj, best_dist = obj, d
        return best_obj

    def _minimap_label(self, obj):
        """Readable name for a minimap blip - the same label the targeting
        HUD uses (from targetable_objects), plus the pilot name for a
        crewed ship."""
        label = next((lbl for lbl, o in self.targetable_objects if o is obj), None)
        if label is None:
            label = getattr(obj, "name", "Unknown")
        if isinstance(obj, Character):
            pilot = obj.person.name
            if pilot:
                label = f"{label} - {pilot}"
        return label

    def _filtered_targets(self):
        """targetable_objects narrowed to the current target mode - SHIPS
        (AI ships only), LANDING SITES (station/moon only), or MISC (everything
        else - celestial bodies, the central star). current_target is
        always an index into *this* list, not the master one, so switching
        modes changes what index 0 means. Departed AI ships are pruned from
        targetable_objects by _validate_target every frame, so this never
        sees a Character that's no longer in self.ai_ships."""
        mode = TARGET_MODES[self.target_mode_index]
        if mode == "SHIPS":
            return [entry for entry in self.targetable_objects if isinstance(entry[1], Character)]
        elif mode == "LANDING SITES":
            return [entry for entry in self.targetable_objects if isinstance(entry[1], LandingSite)]
        return [entry for entry in self.targetable_objects if not isinstance(entry[1], (Character, LandingSite))]

    def _cycle_target(self, direction=1):
        """Cycle through targetable objects in the current target mode - direction=1 for T/], -1 for [."""
        filtered = self._filtered_targets()
        if not filtered:
            return
        if self.current_target is None:
            self.current_target = 0
        else:
            self.current_target = (self.current_target + direction) % len(filtered)
        sound_board.play("blip")

    def _cycle_target_mode(self):
        """Switch which category T/[/] cycles through (Tab). Immediately
        selects the first object in the new category - empty if this
        system has none - so the mode switch itself gives feedback instead
        of leaving a stale target from the old category selected."""
        self.target_mode_index = (self.target_mode_index + 1) % len(TARGET_MODES)
        self.current_target = 0 if self._filtered_targets() else None
        sound_board.play("blip")
        if TARGET_MODES[self.target_mode_index] == "SHIPS":
            # Generic gameplay-event flag - see K_SPACE's own comment on
            # why these live on Possessions.flags instead of a
            # SpaceScreen-only field.
            self.player.person.possessions.flags["used_ships_target_mode"] = True

    def _get_target_name(self):
        """Get the name of the current target"""
        filtered = self._filtered_targets()
        if self.current_target is None or self.current_target >= len(filtered):
            return None
        return filtered[self.current_target][0]

    def _get_target_object(self):
        """Get the current target object"""
        filtered = self._filtered_targets()
        if self.current_target is None or self.current_target >= len(filtered):
            return None
        return filtered[self.current_target][1]

    def _validate_target(self):
        """Keep targetable_objects in sync with self.ai_ships - prune AI
        ships that have left this system, re-add any that have come back -
        keep current_target pointing at the same object across that change
        (or clear it if that object was the one that left), and disengage
        the player's autopilot if it was seeking a ship that's now gone.

        ExplorerRoutine can migrate a Character out of self.ai_ships into
        another system's list entirely (it jumped away) while
        targetable_objects, built once per _activate_system, still holds the
        now-stale tuple referencing it. That Character keeps updating every
        frame regardless of which system it's in (see
        SystemState.update_physics), so a stale entry left in place would
        keep the brackets/arrow tracking its position over in whatever
        system it jumped to. It also broke cycling: current_target indexes
        _filtered_targets(), so a ghost sitting at the end of the SHIPS list
        meant "[" from the first ship wrapped straight onto it and bounced
        back every time, never reaching the real ships in between (whereas
        "]" happened to hit them on the way past). Removing the tuple
        outright - and re-resolving current_target by identity - fixes both.

        The player's autopilot_target is a separate reference entirely (set
        by engage_seek, independent of current_target/targetable_objects),
        so it needs its own check."""
        target = self._get_target_object()
        stale = {entry[1] for entry in self.targetable_objects
                 if isinstance(entry[1], Character) and entry[1] not in self.ai_ships}
        # A ship can also come *back* (ExplorerRoutine jumps to a random
        # system and may pick this one) - re-add any AI ship that's in
        # self.ai_ships but has no tuple, so it becomes targetable again
        # without waiting for the next _activate_system.
        known = {entry[1] for entry in self.targetable_objects}
        returned = [ship for ship in self.ai_ships if ship not in known]
        if stale or returned:
            self.targetable_objects = [e for e in self.targetable_objects if e[1] not in stale]
            self.targetable_objects.extend((self._ship_target_label(s), s) for s in returned)
            if target is None or target in stale:
                self.current_target = None
            else:
                self.current_target = next(
                    (i for i, (_, obj) in enumerate(self._filtered_targets()) if obj is target),
                    None)

        autopilot_target = self.player.autopilot_target
        if isinstance(autopilot_target, Character) and autopilot_target not in self.ai_ships:
            self.player.autopilot_active = False
            self.player.autopilot_target = None

    def _target_bracket_size(self, target_obj):
        """Screen-pixel bracket half-width that actually hugs target_obj's
        own drawn radius, instead of one fixed size for every target
        regardless of how big it is on screen - a station (~120px radius)
        and a central star (~300px) both used to get the same tiny 40px
        brackets, leaving the brackets floating deep inside the target
        instead of framing it. Character (AI ships) wrap a Ship, whose
        actual drawn size is Ship.size (see draw()'s own ship_size
        resolution); everything else (LandingSite, CelestialBody, CentralStar)
        already exposes its drawn radius directly as `.size`."""
        world_radius = target_obj.ship.size if isinstance(target_obj, Character) else getattr(target_obj, "size", 20)
        padding = 12
        return int(world_radius * get_scale()) + padding

    def _draw_target_arrow(self, surface, target):
        """Draw an arrow on an imaginary circle around the player's ship, pointing toward the target."""
        dx, dy = target.x - self.player.x, target.y - self.player.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance == 0:
            return

        # Normalize direction, then rotate it into screen space so the arrow
        # points the right way when the view is rotated (Q/E).
        dir_x, dir_y = utils.rotate_camera_vector(dx / distance, dy / distance)

        ui_scale = get_ui_scale()
        ship_x, ship_y = utils.to_screen(self.player.x, self.player.y)

        # Position on the circle around the ship, on the side facing the target
        radius = 45 * ui_scale
        arrow_x = ship_x + dir_x * radius
        arrow_y = ship_y + dir_y * radius

        # Arrow head points in direction of target
        arrow_size = 10 * ui_scale
        tip_x = arrow_x + dir_x * arrow_size
        tip_y = arrow_y + dir_y * arrow_size

        # Arrow tail points opposite
        tail_x = arrow_x - dir_x * arrow_size
        tail_y = arrow_y - dir_y * arrow_size

        # Perpendicular for arrow wings
        perp_x = -dir_y
        perp_y = dir_x

        # Draw arrow as triangle
        wing_size = 4 * ui_scale
        wing1_x = tail_x + perp_x * wing_size
        wing1_y = tail_y + perp_y * wing_size
        wing2_x = tail_x - perp_x * wing_size
        wing2_y = tail_y - perp_y * wing_size

        points = [(tip_x, tip_y), (wing1_x, wing1_y), (wing2_x, wing2_y)]
        pygame.draw.polygon(surface, GREEN, points)

    def _draw_minimap(self, surface, target_obj):
        """Local radar in the top-right corner: player stays centered, every
        other system object is plotted as a point at its true relative
        position/color, scaled down to MINIMAP_RANGE world units per half-
        height. Objects beyond that range simply don't appear - this is a
        local radar, not the galaxy-scale StarMap (M key), so it never needs
        to pan/zoom. Returns its rect so the HUD can stack the info panel
        below it.
        """
        ui_scale = get_ui_scale()
        # Fills the full side-panel width (see side_panel_width) so it shares
        # both vertical edges with the info panel stacked below it. Height is
        # capped at 40% of the window so the info panel always has room -
        # on a wide window that makes the radar a wide-ish rectangle rather
        # than a square, which is fine for a local radar (you just see more
        # to the sides than fore/aft).
        width = side_panel_width(ui_scale)
        height = min(width, int(utils.screen_height * 0.4))
        margin = hud_margin(ui_scale)
        rect = pygame.Rect(0, 0, width, height)
        rect.topright = (utils.screen_width - margin, margin)

        draw_glass_panel(surface, rect, ui_scale)

        px_per_unit = (height / 2) / MINIMAP_RANGE

        def project(x, y):
            # Rotate with the view (Q/E) so a blip stays in the same screen
            # direction as the object it marks.
            dx, dy = utils.rotate_camera_vector(x - self.player.x, y - self.player.y)
            return rect.centerx + dx * px_per_unit, rect.centery + dy * px_per_unit

        # (object, dot color, dot radius in px) - central star/celestial
        # bodies only included if this system actually has them.
        points = []
        if self.central_star:
            points.append((self.central_star, (255, 220, 80), 3))
        points.append((self.station, WHITE, 3))
        points.append((self.moon, (180, 180, 200), 3))
        for body in self.celestial_bodies:
            points.append((body, (100, 160, 255), 2))
        for ai_ship in self.ai_ships:
            points.append((ai_ship, GREEN, 2))

        # Rebuilt every frame (blips move) - (screen_x, screen_y, hit_radius,
        # obj) for each on-radar point, consumed by _minimap_blip_at for
        # hover text and click-to-target (see handle_input).
        self._minimap_blips = []
        for obj, color, radius in points:
            sx, sy = project(obj.x, obj.y)
            if rect.left <= sx <= rect.right and rect.top <= sy <= rect.bottom:
                r = max(1, int(radius * ui_scale))
                pygame.draw.circle(surface, color, (int(sx), int(sy)), r)
                if obj is target_obj:
                    pygame.draw.circle(surface, YELLOW, (int(sx), int(sy)), r + int(4 * ui_scale), 1)
                # Generous minimum hit area so tightly clustered blips (and
                # the 2px celestial/ship dots) are still easy to click/hover.
                hit_r = max(r + int(4 * ui_scale), int(9 * ui_scale))
                self._minimap_blips.append((sx, sy, hit_r, obj))

        # Player is always exactly centered, drawn last so it stays on top.
        pygame.draw.circle(surface, CYAN, rect.center, max(2, int(3 * ui_scale)))

        font_label = get_font(int(20 * ui_scale))
        label = font_label.render("System Map", True, GRAY)
        surface.blit(label, (rect.x + int(6 * ui_scale), rect.y + int(4 * ui_scale)))

        # Hover readout - the name of whatever blip the pointer is over,
        # following the cursor but clamped inside the panel. Drawn last so it
        # sits above the blips. (The click-to-target half lives in
        # handle_input.)
        hover_obj = self._minimap_blip_at(pygame.mouse.get_pos())
        if hover_obj is not None:
            self._draw_minimap_tooltip(surface, rect, ui_scale, hover_obj)

        self._minimap_rect = rect
        return rect

    def _draw_minimap_tooltip(self, surface, rect, ui_scale, obj):
        """Small label box near the cursor naming the hovered minimap blip
        (see _draw_minimap). Clamped to stay wholly inside `rect`."""
        font = get_font(int(18 * ui_scale))
        text = font.render(self._minimap_label(obj), True, WHITE)
        pad = int(5 * ui_scale)
        mx, my = pygame.mouse.get_pos()
        box = pygame.Rect(0, 0, text.get_width() + pad * 2, text.get_height() + pad * 2)
        box.topleft = (mx + int(12 * ui_scale), my + int(12 * ui_scale))
        box.right = min(box.right, rect.right - pad)
        box.left = max(box.left, rect.left + pad)
        box.bottom = min(box.bottom, rect.bottom - pad)
        box.top = max(box.top, rect.top + pad)
        bg = pygame.Surface(box.size, pygame.SRCALPHA)
        bg.fill((20, 30, 40, 225))
        surface.blit(bg, box.topleft)
        pygame.draw.rect(surface, (120, 140, 160), box, 1)
        surface.blit(text, (box.x + pad, box.y + pad))
        return box

    def _start_hail(self):
        """Open a hail with the currently targeted ship (K_h - see
        docs/CONTROLS.md's Hailing section). Requires a targeted AI ship
        (SHIPS target mode - see _get_target_object/_filtered_targets);
        does nothing if nothing's targeted, or the target isn't a ship at
        all. A pilot currently ashore (DockRoutine has them walking around
        a station/moon interior right now) can't actually be reached this
        way - hailing them just flashes a brief "no response" banner
        instead of opening person.hail_dialogue, since they're not in the
        ship to answer."""
        target_obj = self._get_target_object()
        if not isinstance(target_obj, Character) or self.current_target is None:
            return
        pilot_name = target_obj.person.name or "Unknown"
        if target_obj.ashore:
            self.hail_banner = (f"{pilot_name}: no response - currently docked.", YELLOW)
            self.hail_banner_timer = HAIL_BUSY_BANNER_FRAMES
            return
        dialogue = target_obj.person.hail_dialogue
        possessions = self.player.person.possessions
        flags = possessions.flags
        # Generic gameplay-event flag (see K_SPACE's own comment) - any
        # story's missions.json can use "hailed_pilot:<name>" as a stage's
        # complete_flag without this class hardcoding which pilot.
        flags[f"hailed_pilot:{pilot_name}"] = True
        # resolve_root(), not .root directly, so an earlier flag (e.g.
        # having already been hailed by this pilot once - see
        # _check_one_way_hails) can open on a different greeting node.
        dialogue.current_node = dialogue.resolve_root(flags)
        dialogue.selected_option = 0
        self.active_dialogue = dialogue
        self.hail_banner = None
        self.hail_banner_timer = 0
        # Release thrust - handle_input() stops calling into
        # player.handle_input() the instant active_dialogue is set (see
        # there), so without this whatever thrust was already applied the
        # frame H was pressed would otherwise keep accelerating the ship
        # every physics frame for as long as the conversation stays open.
        self.player.thrust = 0

    def _choose_hail_option(self, index):
        """Act on the visible hail option at `index` (a mouse click on it).
        A hail option's action is only ever a shared one (set_flag/give_item/
        spend_credits - buy_ship:/take_loan don't make sense mid-flight), and
        none of those block on affordability, so there's no "skip blocked"
        pass like LocationScreen's."""
        possessions = self.player.person.possessions
        options = self.active_dialogue.current_options(possessions.flags)
        if not 0 <= index < len(options):
            return
        option = options[index]
        for action in option_actions(option):
            apply_shared_actions(action, possessions, self.missions_config)
        if self.active_dialogue.advance(option):
            self.active_dialogue = None
        else:
            self.active_dialogue.selected_option = 0

    def _show_toast(self, text, color=CYAN):
        """Flash a short, self-clearing message in the center of the screen
        (see _draw_hud) - used for jump completion and mission events
        (started / stage completed / finished). Unlike _post_message this
        is purely transient: nothing is written to the Messages log."""
        self.toast_text = text
        self.toast_color = color
        self.toast_timer = TOAST_FRAMES

    def _post_message(self, sender, text):
        """Show a transient hail banner and permanently log a one-way
        message from sender (see Possessions.add_message) - shared by
        pilot-proximity hails (_check_one_way_hails) and mission-stage-
        entry messages (missions.json's "one_way_message" - see
        _deliver_stage_message). The banner is skipped (but the message is
        still logged) while a hail conversation is already open, so an
        incoming banner can't visually collide with the dialogue box - the
        Messages pane still shows it once the conversation closes."""
        self.player.person.possessions.add_message(sender, text)
        # Snap the Message Log back to the newest entry and (re)start its
        # unread alert: the light blinks MESSAGE_ALERT_BLINKS times and the
        # "ping" cue sounds once per blink, driven from update() so the audio
        # stays in sync with the light (see message_alert_state).
        self.message_log_scroll = 0
        self.message_alert_timer = MESSAGE_ALERT_FRAMES
        self._message_alert_pings_played = 0
        if self.active_dialogue:
            return
        # Banner just announces the transmission - the message body itself
        # is in the Messages pane (bottom-left) and stays there to read.
        self.hail_banner = (f"Incoming transmission - {sender} (see Messages)", CYAN)
        self.hail_banner_timer = ONE_WAY_HAIL_BANNER_FRAMES

    def _deliver_stage_message(self, advanced_stage):
        """Post the one_way_message (if any) for a stage a mission just
        advanced into - advanced_stage is a (mission_id, stage_index) pair
        as returned by mission.py's start_mission()/check_mission_progress(),
        or None (nothing advanced this call, or the mission has no
        starting_mission - see both call sites)."""
        if not advanced_stage:
            return
        mission_id, stage_index = advanced_stage
        stage = self.missions_config[mission_id]["stages"][stage_index]
        message = stage.get("one_way_message")
        if message:
            self._post_message(message.get("sender", "Unknown"), message.get("text", "..."))

    def _check_one_way_hails(self):
        """Let an NPC-initiated hail (pilots.json's "one_way_hail" - see
        Character.for_ai_pilot) fire once the player gets close enough -
        see _post_message - and sets a flag so it never fires twice for
        the same pilot. Only checks the active system's ships
        (self.ai_ships) - proximity to the player only means anything in
        whichever system they're actually in - and skips entirely while a
        hail is already open, so an incoming banner can't steal focus out
        from under a conversation the player is already having, or while
        the player is docked in an interior (update_physics() still runs
        in the background then, but a pilot hailing your cockpit makes no
        sense when you're not in it - see self.in_flight)."""
        if self.active_dialogue or not self.in_flight:
            return
        flags = self.player.person.possessions.flags
        for ai_ship in self.ai_ships:
            one_way = getattr(ai_ship.person, "one_way_hail", None)
            if not one_way or ai_ship.ashore:
                continue
            seen_flag = f"one_way_hail_seen:{ai_ship.person.name}"
            if flags.get(seen_flag):
                continue
            hail_range = one_way.get("range", ONE_WAY_HAIL_RANGE)
            if ai_ship.get_distance(self.player.x, self.player.y) <= hail_range:
                flags[seen_flag] = True
                self._post_message(ai_ship.person.name or "Unknown", one_way.get("message", "..."))
                return  # one at a time - avoids stacking two banners the same frame

    def _sync_escorts(self):
        """Toggle any pilot with a configured "escort_flag" (pilots.json)
        between escorting the player (OrbitPlayerRoutine - circling nearby)
        and their normal role routine, based on whether that flag is currently set in the
        player's Possessions.flags - e.g. Kade Marsh following the player
        through the tutorial mission once they accept his offer to help
        (see his hail_dialogue_tree's "set_flag:kade_escorting" action),
        and back to his normal patrol once the mission ends, finished or
        declined (see mission.py's escort_flag clearing). Checks every
        system, not just the active one, so this stays correct regardless
        of which system is currently on screen."""
        flags = self.player.person.possessions.flags
        for state in self.systems.values():
            for ai_ship in state.ai_ships:
                escort_flag = getattr(ai_ship.person, "escort_flag", None)
                if not escort_flag:
                    continue
                should_escort = bool(flags.get(escort_flag))
                if should_escort and not ai_ship.escorting:
                    ai_ship.set_routine(OrbitPlayerRoutine(self.player))
                    ai_ship.escorting = True
                elif not should_escort and ai_ship.escorting:
                    ai_ship.set_routine(resolve_routine_class(ai_ship.role, ai_ship.faction, ai_ship.routine_name)(ai_ship.route))
                    ai_ship.escorting = False

    def _check_landing(self):
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)

        station_distance = self.station.get_distance(self.player.x, self.player.y)
        if station_distance < self.station.landing_distance and speed < 0.4:
            return "station"

        moon_distance = self.moon.get_distance(self.player.x, self.player.y)
        if moon_distance < self.moon.landing_distance and speed < 0.4:
            return "moon"

        return None

    def _drifted_from_center(self):
        """Whether the player has flown far enough from this system's
        center that jumping back (open the Star Map, select this system,
        J) is both possible and worth calling out - see _draw_hud's
        status-pane hint. Uses the exact same threshold try_jump already
        requires for a self-jump back to this system, so the hint and the
        mechanic it's pointing at agree by construction."""
        cx, cy = SYSTEM_CENTER
        return math.sqrt((self.player.x - cx) ** 2 + (self.player.y - cy) ** 2) >= self.jump_self_min_distance

    def try_jump(self):
        """Validate the current star map selection/distance, then start a jump
        if valid. Called both by K_J in the space view and by main.py when the
        player presses J to leave the Star Map with a destination selected."""
        if not self.selected_system_id:
            return
        cx, cy = SYSTEM_CENTER
        distance_from_center = math.sqrt((self.player.x - cx) ** 2 + (self.player.y - cy) ** 2)
        if self.selected_system_id == self.system_id and distance_from_center < self.jump_self_min_distance:
            self.jump_message_timer = 90  # brief "too close to jump" feedback
            return
        self._begin_jump()

    def _begin_jump(self):
        """Point the ship toward the destination system and begin the jump animation."""
        systems = get_star_systems(self.story)
        origin = systems.get(self.system_id)
        destination = systems.get(self.selected_system_id)
        if not origin or not destination:
            return

        if self.selected_system_id == self.system_id:
            # Self-jump ("jump home" to re-centre after drifting) - there's no
            # star-map direction, so aim the ship straight at the system
            # centre from wherever it currently is. It then travels toward
            # centre and arrives on the near side facing inward (see
            # _complete_jump).
            cx, cy = SYSTEM_CENTER
            dx, dy = cx - self.player.x, cy - self.player.y
            if dx == 0 and dy == 0:
                dx = 1
        else:
            origin_pos = origin["star_map_position"]
            dest_pos = destination["star_map_position"]
            dx = dest_pos["x"] - origin_pos["x"]
            dy = dest_pos["y"] - origin_pos["y"]
            if dx == 0 and dy == 0:
                dx = 1  # degenerate guard: two systems at the same map position

        heading = math.degrees(math.atan2(dx, -dy)) % 360

        self.player.autopilot_active = False
        self.player.autopilot_target = None
        self.player.thrust = 0
        self.player.ship.force_thrusters = True  # cleared in _complete_jump
        self.jump_state = {
            "phase": "align",
            "heading": heading,
            "timer": 0,
            "destination": self.selected_system_id,
        }

    def _update_jump(self):
        """Advance the jump animation by one frame: rotate to heading, then blast forward."""
        js = self.jump_state
        ship = self.player.ship

        if js["phase"] == "align":
            target_angle = js["heading"] % 360
            current_angle = ship.angle % 360
            diff = (target_angle - current_angle + 180) % 360 - 180
            step = ship.rotation_speed * 3  # snappier than normal turning, for a punchy feel
            if abs(diff) <= step:
                ship.angle = target_angle
                js["phase"] = "travel"
                js["timer"] = 0
            else:
                ship.angle = (ship.angle + step * (1 if diff > 0 else -1)) % 360

        elif js["phase"] == "travel":
            rad = math.radians(ship.angle)
            ship.velocity_x = math.sin(rad) * self.jump_speed
            ship.velocity_y = -math.cos(rad) * self.jump_speed
            ship.x += ship.velocity_x
            ship.y += ship.velocity_y
            js["timer"] += 1
            if js["timer"] >= self.jump_travel_frames:
                self._complete_jump()

    def _complete_jump(self):
        """Finish the jump: swap systems (within this story) if the destination differs,
        then arrive on the outskirts."""
        js = self.jump_state
        heading_rad = math.radians(js["heading"])
        destination = js["destination"]

        if destination != self.system_id:
            self._activate_system(destination)

        center_x, center_y = SYSTEM_CENTER
        arrival_x = center_x - math.sin(heading_rad) * self.jump_arrival_distance
        arrival_y = center_y + math.cos(heading_rad) * self.jump_arrival_distance

        ship = self.player.ship
        ship.x, ship.y = arrival_x, arrival_y
        ship.angle = js["heading"] % 360
        # Arrive coasting at the ship's own top speed - no faster (the base
        # physics only caps velocity while thrusting, so an over-max arrival
        # speed would otherwise persist until the player next thrusts).
        arrival_speed = ship.max_velocity
        ship.velocity_x = math.sin(heading_rad) * arrival_speed
        ship.velocity_y = -math.cos(heading_rad) * arrival_speed
        ship.thrust = 0
        ship.force_thrusters = False

        self.jump_state = None
        # Reset the jump target to wherever we just arrived (never None) -
        # matches __init__ and keeps "Jump Target" meaningful.
        self.selected_system_id = self.system_id
        arrival_name = get_star_systems(self.story).get(self.system_id, {}).get("name", self.system_id)
        self._show_toast(f"Jump complete - arrived at {arrival_name}", CYAN)
        # Generic gameplay-event flag - see K_SPACE's comment above on why
        # these live on Possessions.flags instead of a SpaceScreen-only
        # field. Set for any completed jump, not just a self-jump back to
        # this same system - both demonstrate the mechanic equally well.
        self.player.person.possessions.flags["completed_jump"] = True

    def update_physics(self):
        """Update physics without camera - used when space is background.

        Every system this story defines gets its station/moon/celestial
        bodies/AI ships advanced every frame - not just self.system_id, the
        one actually being flown in right now (see SystemState) - so
        traffic elsewhere keeps moving and NPCs at a station/moon the
        player isn't currently visiting keep going about their routine
        (main.py's update_background_locations() already does the
        equivalent for cached interiors). The asteroid/star fields are the
        one exception, kept to just the active system - both are pure,
        camera-driven decoration (see SystemState's docstring)."""
        with perf.span("sim.player"):
            if self.jump_state:
                self._update_jump()
            else:
                self.player.update()
        flags = self.player.person.possessions.flags
        if self.player.thrust > 0:
            # Generic gameplay-event flag - see K_SPACE's comment above on
            # why these live on Possessions.flags instead of a
            # SpaceScreen-only field.
            flags["used_thrust"] = True
        # Only meaningful once thrust and the brake control have both been
        # used at least once - otherwise a ship that simply never got
        # moving would trivially satisfy "speed below threshold" without
        # any actual braking having happened.
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
        if flags.get("used_thrust") and flags.get("used_brake") and speed < self.brake_slow_threshold:
            flags["braked_below_threshold"] = True
        with perf.span("sim.ai_ships"):
            for state in self.systems.values():
                state.update_physics()
            self.asteroid_field.update()
        if self.jump_message_timer > 0:
            self.jump_message_timer -= 1
        if self.hail_banner_timer > 0:
            self.hail_banner_timer -= 1
        if self.message_alert_timer > 0:
            self.message_alert_timer -= 1
        self._check_one_way_hails()
        self._validate_target()
        # Mission progress before _sync_escorts() - a mission finishing
        # this exact frame clears its escort_flag (see mission.py's
        # _on_mission_end), and escort sync needs to see that same-frame
        # rather than escorting for one extra frame after the tutorial's
        # already over.
        with perf.span("sim.missions"):
            possessions = self.player.person.possessions
            completed_before = set(possessions.completed_missions)
            for advanced_stage in check_mission_progress(self.missions_config, possessions):
                self._deliver_stage_message(advanced_stage)
                mission_id, stage_index = advanced_stage
                total = len(self.missions_config.get(mission_id, {}).get("stages", []))
                self._show_toast(f"Step {stage_index + 1}/{total} - see Mission Log (N)", GREEN)
            for mission_id in possessions.completed_missions:
                if mission_id not in completed_before:
                    title = self.missions_config.get(mission_id, {}).get("title", mission_id)
                    self._show_toast(f"Mission complete: {title}", YELLOW)
            self._sync_escorts()

    def update(self):
        """Full update including camera - only called when space is active screen"""
        # This screen only runs update() (rather than the background-only
        # update_physics()) while the player is actually flying it, so it's
        # also the catch-all "in flight now" hook - covers loading a save
        # straight into space, where no board_ship() transition fired.
        self.board_ship()
        # Auto-land when the autopilot brings the ship in. Two checks bracket
        # update_physics(): the pre-check catches has_arrived() being true at
        # the top of the frame (the tight distance/speed SeekMode itself uses
        # to stop, so we don't "give up" braking early with residual speed);
        # the post-check catches SeekMode disengaging *inside* update_physics()
        # - via its own arrival or its looser stall-bailout stop - and
        # finishing near enough to land. `pending` carries the target across
        # update_physics(), which clears autopilot_target once it disengages.
        pending = self.player.autopilot_target if (
            self.player.autopilot_active and self.player.autopilot_target in (self.station, self.moon)) else None

        if self.player.autopilot_active and self.player.autopilot_target and has_arrived(self.player, self.player.autopilot_target):
            target = self.player.autopilot_target
            self.player.park()
            self.player.autopilot_active = False
            self.player.autopilot_target = None
            # Only try to land on landing sites, not ships
            if target == self.station:
                self.landing_target = "station"
                self._mark_landed()
                return "land"
            elif target == self.moon:
                self.landing_target = "moon"
                self._mark_landed()
                return "land"

        self.update_physics()

        # The autopilot disengaged itself this frame (SeekMode's own arrival /
        # stall-bailout inside update_physics(), which uses a looser stop than
        # has_arrived()) - if it left us stopped within landing range of the
        # landing site it was seeking, finish the landing rather than leave the
        # ship parked-but-not-landed for the player to press L.
        if pending is not None and not self.player.autopilot_active:
            speed = math.hypot(self.player.velocity_x, self.player.velocity_y)
            if self.player.get_distance(pending.x, pending.y) < pending.landing_distance and speed < 0.4:
                self.player.park()
                self.landing_target = "station" if pending == self.station else "moon"
                self._mark_landed()
                return "land"

        # Toast counts down only here, not in update_physics() - so one
        # raised while docked (update_physics() still runs in the background
        # then) is still on screen when the player launches back into space.
        if self.toast_timer > 0:
            self.toast_timer -= 1

        # The unread-message ping sounds once per blink of the Message Log
        # light, exactly MESSAGE_ALERT_BLINKS times. Driven here (active
        # screen only, like the toast) rather than in update_physics(), which
        # also runs for background interiors - the alert timer itself still
        # counts down there. The while loop catches up if a slow frame ran
        # several sim steps at once.
        _, pings_due = message_alert_state(self.message_alert_timer)
        while self._message_alert_pings_played < pings_due:
            sound_board.play("ping")
            self._message_alert_pings_played += 1

        # Update camera to follow player, at the current view rotation
        set_camera_offset(self.player.x - GAME_WIDTH // 2, self.player.y - GAME_HEIGHT // 2)
        set_camera_angle(self.camera_angle)

        if self.jump_state:
            return  # skip landing checks entirely while jumping

        if self._check_landing():
            self.landing_text = 60
        else:
            self.landing_text = max(0, self.landing_text - 1)

    def draw(self, surface, draw_hud=True):
        """draw_hud=False skips the top-left Controls pane and bottom
        status pane - see LocationScreen.draw's docstring for why (used
        the same way here, when this screen is only being redrawn as the
        backdrop for a modal menu on top of it)."""
        # Re-assert the view rotation here too, not just in update() - when
        # this screen is only a backdrop for a modal (pause menu, possessions,
        # etc.) update() isn't called, but the stored camera angle could have
        # been left non-zero or reset by another screen in between.
        set_camera_angle(self.camera_angle)
        surface.fill(BLACK)
        with perf.span("render.starfield"):
            self.star_field.draw(surface)
        with perf.span("render.world"):
            if self.central_star:
                self.central_star.draw(surface)
            for body in self.celestial_bodies:
                body.draw(surface)
            self.station.draw(surface)
            self.moon.draw(surface)
            self.asteroid_field.draw(surface)
            for ai_ship in self.ai_ships:
                ai_ship.draw(surface)
            self.player.draw(surface)

        # Debug markers for entity positions
        if constants.DEBUG_MODE:
            draw_debug_marker(surface, self.player.x, self.player.y, 10)
            draw_debug_marker(surface, self.station.x, self.station.y, 10)
            draw_debug_marker(surface, self.moon.x, self.moon.y, 10)
            for ai_ship in self.ai_ships:
                draw_debug_marker(surface, ai_ship.x, ai_ship.y, 8)
            for asteroid in self.asteroid_field.asteroids:
                draw_debug_marker(surface, asteroid.x, asteroid.y, 6)

        # Target brackets/arrow are drawn over the world; everything else is
        # the HUD overlay (status panels, messages, help text).
        target_obj = self._get_target_object()
        if target_obj:
            draw_target_brackets(surface, target_obj.x, target_obj.y, size=self._target_bracket_size(target_obj))
            self._draw_target_arrow(surface, target_obj)

        scale = get_scale()
        offset_x, offset_y = get_offset()
        border_rect = (int(offset_x), int(offset_y), int(GAME_WIDTH * scale), int(GAME_HEIGHT * scale))
        pygame.draw.rect(surface, (100, 100, 100), border_rect, 2)

        with perf.span("render.hud"):
            self._draw_hud(surface, target_obj, draw_hud=draw_hud)

        # Active hail conversation, drawn last so it sits on top of the HUD
        # too - same reason LocationScreen draws active_dialogue last.
        if self.active_dialogue:
            self.active_dialogue.draw(surface, get_ui_scale(), flags=self.player.person.possessions.flags)

    def _draw_hud(self, surface, target_obj, draw_hud=True):
        """Ship status, targeting, jump-target, help, and status-message
        overlays - styled with the same glass-panel look as the menus
        (ui_theme.py) instead of each being its own ad-hoc text blit.

        Anchored directly to the real screen edges (0/screen_width/
        screen_height), not get_ui_offset() - that offset centers the
        menus' fixed 800x600 virtual canvas within the window, which this
        full-viewport HUD isn't confined to. Adding it while right/bottom-
        anchoring (screen_width - x) pushed panels past the real edge,
        which is why the jump target panel was rendering off-screen.
        """
        ui_scale = get_ui_scale()
        margin = int(10 * ui_scale)

        # --- Top-right: minimap, then targeting info (incl. jump target)
        # stacked directly below it.
        minimap_rect = self._draw_minimap(surface, target_obj)

        # Always every line (placeholder "None" for target/jump target
        # rather than omitting them) so the panel doesn't resize or
        # appear/disappear as targeting and jump selection change - only
        # colors change.
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
        target_name = self._get_target_name()
        mode_label = TARGET_MODES[self.target_mode_index]
        lines = [
            (f"Credits: {self.player.person.possessions.credits}", (255, 220, 100)),
            (f"Speed: {speed:.2f}", WHITE),
            (f"Mode: {mode_label}", WHITE),
        ]
        if target_obj and target_name:
            distance = self.player.get_distance(target_obj.x, target_obj.y)
            lines.append(("Target:", GREEN))
            lines.append((f"  Distance: {distance:.0f}", GREEN))
            lines.append((f"  {target_name}", GREEN))
            # Ships show their pilot; landing sites (station/moon) list what's
            # inside them so the player can see where they'll end up before
            # committing to land; other bodies show a hazard note if any -
            # these are mutually exclusive categories of targetable_objects.
            if isinstance(target_obj, Character):
                pilot_name = target_obj.person.name
                if pilot_name:
                    lines.append((f"  Pilot: {pilot_name}", GREEN))
            elif isinstance(target_obj, LandingSite):
                lines.append(("  Locations:", GREEN))
                for label in target_obj.get_interior_labels():
                    lines.append((f"    - {label}", GRAY))
            elif getattr(target_obj, "hazardous", False):
                lines.append(("  Hazardous - not a landing site", YELLOW))
        else:
            lines.append(("Target: None", GRAY))

        # selected_system_id is never None (see __init__) - it defaults to
        # the current system, so this line always names somewhere.
        systems = get_star_systems(self.story)
        selected_name = systems.get(self.selected_system_id, {}).get("name", self.selected_system_id)
        jump_label = selected_name
        if self.selected_system_id == self.system_id:
            jump_label += " (current)"
        lines.append((f"Jump Target: {jump_label}", CYAN))

        info_rect, info_max_scroll = draw_info_panel(surface, lines, ui_scale, (utils.screen_width - margin, minimap_rect.bottom + margin), scroll=self.info_panel_scroll)
        self.info_panel_scroll = max(0, min(self.info_panel_scroll, info_max_scroll))
        self._info_panel_rect = info_rect

        # --- Top-left: control-help pane (shared design with LocationScreen's -
        # see draw_controls_pane). Hidden (draw_hud=False) while a modal menu
        # is up, and while a hail conversation has focus (it's mouse-only -
        # click an option or the X). C collapses it to a two-liner.
        controls_rect = None
        if draw_hud and not self.active_dialogue:
            help_items = [
                ("ESC", "Pause"),
                ("WASD / Arrows", "Fly"),
                ("Q / E", "Rotate view"),
                ("T  /  [  ]", "Target mode / target"),
                ("Click / hover blip", "Minimap: target / name"),
                ("Space", "Autopilot"),
                ("L", "Land / board"),
                ("H", "Hail target"),
                ("J  /  M", "Jump / map"),
                ("P  /  N", "Gear / log"),
                ("Wheel", "Scroll pane"),
            ]
            controls_rect = draw_controls_pane(surface, margin, margin, "Controls", help_items, ui_scale,
                                               collapsed=self.controls_collapsed)

        # --- Top-center: transient popups, each in its own glass pane (see
        # draw_glow_message), stacked downward so they can never overlap -
        # the "too close to jump" warning / an incoming hail banner (only
        # one of those is ever up at once) plus the mission/jump toast,
        # which can coexist with a hail (a mission stage advancing delivers
        # both its one_way_message banner and a "stage complete" toast the
        # same frame).
        popups = []
        if self.jump_message_timer > 0:
            popups.append(("Too close to jump - move away from center first", YELLOW, (60, 45, 10)))
        elif self.hail_banner_timer > 0 and self.hail_banner:
            popups.append((self.hail_banner[0], self.hail_banner[1], (20, 30, 40)))
        if self.toast_timer > 0 and self.toast_text:
            popups.append((self.toast_text, self.toast_color, (20, 30, 40)))

        font_popup = get_font(int(20 * ui_scale))
        popup_y = margin + int(10 * ui_scale)
        for text, color, shadow in popups:
            popup_rect = draw_glow_message(
                surface, text, font_popup, utils.screen_width // 2, popup_y,
                color=color, shadow_color=shadow,
            )
            popup_y = popup_rect.bottom + int(8 * ui_scale)

        # --- Bottom-center: current status. Being mid-jump or having
        # autopilot engaged are exclusive committed states (almost any key
        # cancels/doesn't apply), but the land/jump/autopilot *availability*
        # prompts are independent of each other and can all be true at
        # once, so they stack as separate lines in one panel instead of
        # being mutually exclusive. Skipped entirely while active_dialogue
        # is set, same reason as the controls-pane swap above.
        status_rect = None
        if draw_hud and not self.active_dialogue:
            status_lines = []
            if self.jump_state:
                status_text = "Aligning for jump..." if self.jump_state["phase"] == "align" else "JUMPING..."
                status_lines = [(status_text, GREEN)]
            elif self.player.autopilot_active:
                status_lines = [("Autopilot engaged - press any key to cancel", GREEN)]
                if self.player.autopilot_target is not None:
                    status_lines.append((f"Approaching: {self._approaching_label(self.player.autopilot_target)}", GREEN))
            else:
                if self.landing_text > 0:
                    status_lines.append(("Press L to Land", GREEN))
                elif speed >= 0.4 and (
                    self.station.get_distance(self.player.x, self.player.y) < self.station.landing_distance
                    or self.moon.get_distance(self.player.x, self.player.y) < self.moon.landing_distance
                ):
                    status_lines.append(("Slow down to land", RED))
                # Jump Target is never None now (see __init__). A jump to a
                # *different* system is always allowed; a jump back to the
                # current one needs distance from center first (see try_jump/
                # JUMP_SELF_MIN_DISTANCE), so only prompt for it once that's
                # actually true.
                if self.selected_system_id != self.system_id:
                    status_lines.append(("Press J to Jump", GREEN))
                elif self._drifted_from_center():
                    status_lines.append(("Drifting far from the system - open the Star Map (M) and jump (J) back", YELLOW))
                if target_obj:
                    status_lines.append(("Press Space for Autopilot", GREEN))
                if isinstance(target_obj, Character):
                    status_lines.append((f"Press H to Hail {target_obj.person.name or 'Target'}", GREEN))

            status_rect = draw_status_pane(surface, status_lines, ui_scale)

        # --- Bottom-left: received one-way messages (see
        # _check_one_way_hails/Possessions.add_message) - easy to miss as
        # just a transient banner, so they also collect here until there's
        # something to actually look back at. Skipped along with the rest
        # of the HUD while a modal menu/hail dialogue has focus.
        message_log_rect = None
        if draw_hud and not self.active_dialogue:
            messages = [(m["sender"], m["text"]) for m in self.player.person.possessions.message_log]
            message_log_rect, message_log_max_scroll = draw_message_log(surface, messages, ui_scale, self.message_log_scroll, alert=message_alert_state(self.message_alert_timer)[0])
            # Clamp now that the real wrapped-line count is known (window
            # resize or a shrinking log can leave the stored offset too big).
            self.message_log_scroll = max(0, min(self.message_log_scroll, message_log_max_scroll))
            self._message_log_max_scroll = message_log_max_scroll
        self._message_log_rect = message_log_rect

        # Cached for handle_input()'s mouse-click targeting, so a click on
        # any of these panels doesn't also register as a click-to-target in
        # the world behind them (see _hud_click_rects' own comment).
        self._hud_click_rects = [rect for rect in (minimap_rect, info_rect, controls_rect, status_rect, message_log_rect) if rect]

    def get_state(self):
        state = {
            "player": {
                "x": self.player.x,
                "y": self.player.y,
                "angle": self.player.angle,
                "velocity_x": self.player.velocity_x,
                "velocity_y": self.player.velocity_y,
                "thrust": self.player.thrust
            },
            "possessions": self.player.person.possessions.get_state(),
        }
        if self.jump_state:
            state["jump_state"] = dict(self.jump_state)
        # Every AI ship in every system (not just self.system_id) - keyed by
        # pilot name rather than a per-system list index, since a
        # ExplorerRoutine-driven pilot can migrate to a different system
        # between saves, which a positional index can't survive (the list
        # it "belongs to" at load time may not be the one it was saved
        # from, and may not even be the same length). Ships with no pilot
        # name (ai_ships config entries with no "pilot" key) aren't
        # individually saveable this way and are skipped - same as never
        # being restorable at all before this, just now explicit about it.
        ai_ships = {}
        for sid, sys_state in self.systems.items():
            for ai_ship in sys_state.ai_ships:
                if not ai_ship.person.name:
                    continue
                ai_ships[ai_ship.person.name] = {
                    "system_id": sid,
                    "x": ai_ship.x,
                    "y": ai_ship.y,
                    "angle": ai_ship.angle,
                    "velocity_x": ai_ship.velocity_x,
                    "velocity_y": ai_ship.velocity_y,
                    "thrust": ai_ship.thrust
                }
        if ai_ships:
            state["ai_ships"] = ai_ships
        return state

    def restore_possessions(self, state):
        """Restore just the player's possessions (and re-equip whichever
        ship type that implies). Split out from restore_state() because
        state["player"] means something different depending on where a
        save was made: for a "space" save it's the ship's own position/
        velocity (handled by restore_state()); for a "station"/"moon" save
        it's the *LocationScreen's* walking position instead - a totally
        different coordinate space that main.py must never feed to the
        ship-position half of restore_state() (see park_at(), used
        alongside this one for station/moon loads)."""
        if not state or "possessions" not in state:
            return
        self.player.person.possessions.restore_from(state["possessions"])
        # __init__ always starts the player's Ship from story.json's
        # default type, regardless of what was actually bought before
        # saving - re-equip whichever ship they most recently bought
        # (last entry in owned_ships), or the ship visibly reverts to
        # that default (e.g. showing a Patrol when a Shuttle was
        # actually purchased) even though possessions itself is correct.
        owned_ships = self.player.person.possessions.owned_ships
        if owned_ships:
            self._apply_ship_type(owned_ships[-1])

    def restore_state(self, state):
        """Full restore for a "space" save - ship position/velocity,
        possessions, and every AI ship. Do NOT use this for a "station"/
        "moon" save; use restore_possessions() + park_at() instead (see
        restore_possessions() for why)."""
        if not state:
            return
        if "player" in state:
            player_state = state["player"]
            self.player.x = player_state.get("x", self.player.x)
            self.player.y = player_state.get("y", self.player.y)
            self.player.angle = player_state.get("angle", self.player.angle)
            self.player.velocity_x = player_state.get("velocity_x", self.player.velocity_x)
            self.player.velocity_y = player_state.get("velocity_y", self.player.velocity_y)
            self.player.thrust = player_state.get("thrust", self.player.thrust)
        saved_jump = state.get("jump_state")
        # Resume an in-progress jump exactly where it left off, rather than
        # leaving the huge jump-speed velocity above with no jump_state to
        # ever bring it back down - previously the ship was left flying at
        # JUMP_SPEED indefinitely (space has no drag), uncontrollable until
        # the player applied thrust and the velocity cap silently clamped it.
        self.jump_state = dict(saved_jump) if saved_jump else None
        self.restore_possessions(state)
        # Restore every AI ship in every system, keyed by pilot name (see
        # get_state()) - older saves stored this as a plain per-system list
        # instead (isinstance check below), which this deliberately does
        # NOT try to interpret: there's no reliable way to match its
        # entries back to today's ships once any of them may have migrated
        # between systems, so an old-format save just leaves every AI ship
        # at its freshly-built default rather than guessing wrong.
        saved_ai_ships = state.get("ai_ships")
        if isinstance(saved_ai_ships, dict):
            migrations = []
            for sid, sys_state in self.systems.items():
                for ai_ship in sys_state.ai_ships:
                    saved = saved_ai_ships.get(ai_ship.person.name)
                    if not saved:
                        continue
                    ai_ship.x = saved.get("x", ai_ship.x)
                    ai_ship.y = saved.get("y", ai_ship.y)
                    ai_ship.angle = saved.get("angle", ai_ship.angle)
                    ai_ship.velocity_x = saved.get("velocity_x", ai_ship.velocity_x)
                    ai_ship.velocity_y = saved.get("velocity_y", ai_ship.velocity_y)
                    ai_ship.thrust = saved.get("thrust", ai_ship.thrust)
                    dest_sid = saved.get("system_id", sid)
                    if dest_sid != sid and dest_sid in self.systems:
                        migrations.append((ai_ship, sys_state, dest_sid))
            # Applied after the scan above, not during it - moving a ship
            # out of sys_state.ai_ships while that same list is mid-iteration
            # would skip whichever ship shifts into the removed slot.
            for ai_ship, origin_state, dest_sid in migrations:
                origin_state.ai_ships.remove(ai_ship)
                self.systems[dest_sid].ai_ships.append(ai_ship)
                ai_ship.system_id = dest_sid
