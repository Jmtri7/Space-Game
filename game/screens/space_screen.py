"""Main space exploration screen with ships and landing."""
import pygame
import math
import game.constants as constants
from game.constants import GAME_WIDTH, GAME_HEIGHT, BLACK, YELLOW, WHITE, GREEN, GRAY, CYAN, RED
from game.utils import (
    get_scale, get_offset, get_ui_scale, load_json, set_camera_offset,
    draw_debug_marker, draw_target_brackets, get_font, to_world,
    get_ship_type, get_graphics_asset, get_pilot, get_star_systems, get_ship_outfit,
    get_asteroid_type, get_missions
)
import game.utils as utils
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_controls_pane, draw_status_pane, draw_info_panel, draw_message_log
from game.screens.screen_base import ScreenBase
from game.screens.location_screen import LocationScreen
from game.world.player_controller import PlayerController
from game.world.autopilot import has_arrived
from game.world.character import Character
from game.world.dialogue import option_actions, apply_shared_actions
from game.world.mission import start_mission, check_mission_progress
from game.world.landable import Landable
from game.world.starfield import StarField
from game.world.central_star import CentralStar
from game.world.celestial_body import CelestialBody
from game.world.asteroid_field import AsteroidField
from game.world.system_state import SystemState

# Hailing tuning
ONE_WAY_HAIL_RANGE = 500          # world units - how close an NPC-initiated hail can trigger from
ONE_WAY_HAIL_BANNER_FRAMES = 300  # ~5s at 60fps an incoming-hail banner stays up
HAIL_BUSY_BANNER_FRAMES = 150     # ~2.5s "no response" flash when hailing a docked/ashore pilot

# Jump mechanic tuning
JUMP_ALIGN_TOLERANCE = 3        # degrees; how close to heading before travel starts
JUMP_TRAVEL_FRAMES = 150        # ~2.5s at 60fps of high-speed travel
JUMP_SPEED = 40                 # world units/frame while traveling
JUMP_ARRIVAL_DISTANCE = 1400    # world units from system center on arrival
JUMP_SELF_MIN_DISTANCE = 700    # must be at least this far from center to jump "back"
SYSTEM_CENTER = (GAME_WIDTH / 2, GAME_HEIGHT / 2)

# Minimap tuning
MINIMAP_SIZE = 240     # px, before ui_scale
MINIMAP_RANGE = 2600   # world units from player (center) to the minimap's edge

# Targeting modes - cycled with Tab, filters what T/[/] can select.
# "MISC" covers everything that's neither a ship nor a landable (celestial
# bodies, the central star). LANDABLES is the default since finding and
# landing on the station is the first thing a new pilot needs to target.
TARGET_MODES = ["SHIPS", "LANDABLES", "MISC"]


class SpaceScreen(ScreenBase):
    """Main space exploration screen with ships and landing."""
    def __init__(self, system_config=None, pilot_name="", story="default", system_id=None):
        super().__init__(pilot_name=pilot_name)
        self.story = story  # fixed for the whole playthrough - stories are wholly separate

        # Load story metadata (player ship type, starting system, etc)
        story_meta = load_json(f"config/stories/{story}/story.json") or {}
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
        # Which mission (if any) automatically starts the first time this
        # player boards a ship (see _on_ship_purchased) - config-driven so a
        # story can opt into (or change, or omit) a tutorial mission without
        # touching this class. None = no auto-started mission.
        self.starting_mission = story_meta.get("starting_mission")

        # Load config for the current system within this story
        self.system_config = system_config or load_json(f"config/stories/{story}/systems/{self.system_id}.json") or {}

        # Get space system drag (default 0 = no drag)
        space_drag = self.system_config.get("drag", 0)

        # Placeholder ship stats/graphics for self.player before any ship is
        # actually owned - PlayerController always needs a Ship object to
        # exist, but a new pilot starts in the dormitory with none, and
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
        self.player = PlayerController(player_x, player_y, space_drag=space_drag, graphics=player_graphics, ship_type=player_ship_type, pilot_name=pilot_name, outfit=get_graphics_asset(self.story, "outfits", "space_suit"))

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
        self.selected_system_id = None  # Star map selection, for the Jump mechanic
        self.jump_state = None  # None, or a dict tracking the jump animation
        self.jump_message_timer = 0  # Transient "too close to jump" feedback
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
        station = Landable(GAME_WIDTH * station_cfg.get("x", 0.75), GAME_HEIGHT * station_cfg.get("y", 0.3), graphics=station_graphics, interiors=station_cfg.get("interiors", {}), name=station_cfg.get("name", "Station"))

        moon_cfg = config.get("moon", {})
        moon_graphics = get_graphics_asset(self.story, "moons", moon_asset_id)
        moon = Landable(GAME_WIDTH * moon_cfg.get("x", 0.2), GAME_HEIGHT * moon_cfg.get("y", 0.4), graphics=moon_graphics, interiors=moon_cfg.get("interiors", {}), name=moon_cfg.get("name", "Moon"))

        # Central star (optional, drawn but not landable/targetable)
        central_star_cfg = config.get("central_star")
        central_star = CentralStar(GAME_WIDTH * central_star_cfg.get("x", 0.5), GAME_HEIGHT * central_star_cfg.get("y", 0.5), graphics=central_star_cfg) if central_star_cfg else None

        # Non-landable planets/ice balls/gas giants - just scenery to fly near,
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

        # Landables that an AI ship's route config can reference by key
        landable_lookup = {"station": station, "moon": moon}

        for ai_cfg in config.get("ai_ships", []):
            ship_type_id = ai_cfg.get("ship_type", "freighter")
            ship_type = get_ship_type(self.story, ship_type_id)
            ship_graphics = get_graphics_asset(self.story, "ships", ship_type_id)
            pilot = get_pilot(self.story, ai_cfg["pilot"]) if "pilot" in ai_cfg else None
            route = [landable_lookup[key] for key in ai_cfg.get("route", []) if key in landable_lookup]
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
                outfit=get_graphics_asset(self.story, "outfits", "space_suit"),
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
        self.target_mode_index = TARGET_MODES.index("LANDABLES")
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
            ship_type = get_ship_type(self.story, ship.ship_type_id)
            ship_name = ship_type.get("name", f"AI Ship {i+1}")
            self.targetable_objects.append((ship_name, ship))

    def get_interior_screen(self, landable, key):
        """Return the persistent LocationScreen for one of landable's
        interiors (key = "default" for a station, "city"/"wilderness" for
        the moon), creating and caching it on landable.interior_screens the
        first time it's visited. Later visits reuse the same instance, so
        NPCs and the player's position within it persist instead of
        resetting every time - and it can keep simulating in the
        background (see update_physics() calls in main.py) while the
        player is elsewhere. Returns None if the interior isn't configured.
        Sized from landable.interior_world_size, not a caller-supplied
        width/height - every call site used to pass the same 800x600/
        1600x1600 pair derived from is_station itself; asking the landable
        keeps that in one place.
        """
        world_width, world_height = landable.interior_world_size
        if key in landable.interior_screens:
            return landable.interior_screens[key]

        interior_config = landable.interiors.get(key)
        if not interior_config:
            return None

        # Display name for every sibling interior this location's portals
        # might connect to (see LocationScreen._display_name) - built from
        # landable.interiors directly rather than lazily inside
        # LocationScreen, since that dict (and any config files it points
        # to) belongs to the landable, not to any one interior within it.
        location_labels = {}
        for sibling_key, sibling_config in landable.interiors.items():
            sibling_config = load_json(sibling_config) if isinstance(sibling_config, str) else sibling_config
            location_labels[sibling_key] = (sibling_config or {}).get("label", sibling_key)

        if isinstance(interior_config, str):
            screen = LocationScreen(config_file=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story, player_possessions=self.player.person.possessions, on_ship_purchased=self._on_ship_purchased, location_labels=location_labels)
        else:
            screen = LocationScreen(config_data=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story, player_possessions=self.player.person.possessions, on_ship_purchased=self._on_ship_purchased, location_labels=location_labels)
        # Which interiors key this is (e.g. "dormitory", "default"/concourse,
        # "spaceport") - lets save/load record exactly which station room
        # the player was in, not just "station" (see main.py's
        # game_state["station_location"]).
        screen.interior_key = key
        landable.interior_screens[key] = screen
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

    def _on_ship_purchased(self, ship_type_id):
        """Configure the player's real ship to match a newly bought type,
        and park it right at the station - so it's "docked outside" exactly
        as a salesman's dialogue would say, ready the moment the player
        boards through the spaceport's exit. Also the natural "first launch
        with a ship" hook for this story's starting_mission (see __init__) -
        start_mission() is a no-op if it's already active/completed, so
        buying a second ship later doesn't reset or restart it."""
        self._apply_ship_type(ship_type_id)
        self.park_at(self.station)
        if self.starting_mission:
            start_mission(self.missions_config, self.player.person.possessions, self.starting_mission)

    def park_at(self, landable):
        """Position the player's ship at `landable`'s own space position
        and stop it - used both right after a purchase and when loading
        directly into a station/moon save (no actual flight/landing
        happened this session, so the ship has to be placed there
        explicitly rather than restored from a save - see
        restore_possessions() and main.py's load handling)."""
        self.player.x, self.player.y = landable.x, landable.y
        self.player.park()

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

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.active_dialogue and not any(rect.collidepoint(event.pos) for rect in self._hud_click_rects):
                    self._select_target_at(*to_world(*event.pos))
                continue

            if event.type != pygame.KEYDOWN:
                continue

            if self.active_dialogue:
                # While a hail is open, input drives the dialogue box
                # instead of flight - mirrors LocationScreen's own
                # active_dialogue branch (see there for why flags is
                # fetched fresh each time rather than cached).
                # A hail option's action is never a LocationScreen-only one
                # (buy_ship:/take_loan don't make sense mid-flight) - just
                # the shared set_flag/give_item/spend_credits actions (see
                # apply_shared_actions) - and none of those ever block on
                # affordability the way a ship purchase can, so unlike
                # LocationScreen, cycling/choosing here is a plain index
                # walk over whatever current_options(flags) returns, with
                # no "skip the blocked ones" pass needed.
                possessions = self.player.person.possessions
                flags = possessions.flags
                options = self.active_dialogue.current_options(flags)
                if event.key in (pygame.K_UP, pygame.K_w) and options:
                    self.active_dialogue.selected_option = (self.active_dialogue.selected_option - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s) and options:
                    self.active_dialogue.selected_option = (self.active_dialogue.selected_option + 1) % len(options)
                elif event.key == pygame.K_RETURN and options:
                    option = options[self.active_dialogue.selected_option]
                    for action in option_actions(option):
                        apply_shared_actions(action, possessions)
                    # advance(option), not choose(index, flags) - see
                    # Dialogue.advance's docstring (LocationScreen's own
                    # dialogue handling has the same comment).
                    if self.active_dialogue.advance(option):
                        self.active_dialogue = None
                    else:
                        self.active_dialogue.selected_option = 0
                elif event.key == pygame.K_ESCAPE:
                    self.active_dialogue = None
                continue

            # Cancel autopilot on any key press (except ESC which handles pause)
            if self.player.autopilot_active and event.key != pygame.K_ESCAPE:
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
                # for that). If a landable is targeted and already in
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
                # AI ship, or approaches a landable from any range (L
                # only lands once you're already close).
                target_obj = self._get_target_object()
                if target_obj and self.current_target is not None:
                    self.player.engage_seek(target_obj)
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
                self._try_jump()
            elif event.key == pygame.K_p:
                return "possessions"
            elif event.key == pygame.K_n:
                return "missions"
        return None

    def _mark_landed(self):
        """Set the generic "landed_on_landable" gameplay-event flag -
        called from every path that actually lands the ship (manual L,
        and update()'s auto-land-on-autopilot-arrival). See K_SPACE's own
        comment above for why this lives on Possessions.flags rather than
        a SpaceScreen-only field."""
        self.player.person.possessions.flags["landed_on_landable"] = True

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
        if best_obj is None:
            return
        mode = "SHIPS" if isinstance(best_obj, Character) else "LANDABLES" if isinstance(best_obj, Landable) else "MISC"
        self.target_mode_index = TARGET_MODES.index(mode)
        for i, (_, obj) in enumerate(self._filtered_targets()):
            if obj is best_obj:
                self.current_target = i
                return

    def _filtered_targets(self):
        """targetable_objects narrowed to the current target mode - SHIPS
        (AI ships only), LANDABLES (station/moon only), or MISC (everything
        else - celestial bodies, the central star). current_target is
        always an index into *this* list, not the master one, so switching
        modes changes what index 0 means."""
        mode = TARGET_MODES[self.target_mode_index]
        if mode == "SHIPS":
            return [entry for entry in self.targetable_objects if isinstance(entry[1], Character)]
        elif mode == "LANDABLES":
            return [entry for entry in self.targetable_objects if isinstance(entry[1], Landable)]
        return [entry for entry in self.targetable_objects if not isinstance(entry[1], (Character, Landable))]

    def _cycle_target(self, direction=1):
        """Cycle through targetable objects in the current target mode - direction=1 for T/], -1 for [."""
        filtered = self._filtered_targets()
        if not filtered:
            return
        if self.current_target is None:
            self.current_target = 0
        else:
            self.current_target = (self.current_target + direction) % len(filtered)

    def _cycle_target_mode(self):
        """Switch which category T/[/] cycles through (Tab). Immediately
        selects the first object in the new category - empty if this
        system has none - so the mode switch itself gives feedback instead
        of leaving a stale target from the old category selected."""
        self.target_mode_index = (self.target_mode_index + 1) % len(TARGET_MODES)
        self.current_target = 0 if self._filtered_targets() else None

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
        """Clear the current target - and disengage the player's autopilot,
        if it was seeking that same target - once it's an AI ship that has
        since left this system. ExplorerRoutine can migrate a Character out
        of self.ai_ships into another system's list entirely (it jumped
        away) while targetable_objects, built once per _activate_system,
        still holds the now-stale tuple referencing it, and the player's
        own autopilot_target is a separate reference entirely (set by
        engage_seek, independent of current_target/targetable_objects).
        Without this, both keep tracking that Character's position in
        whatever system it jumped to - a totally unrelated part of the same
        game-space coordinates - instead of the target being lost, and the
        autopilot disengaging, the way they should once the ship is gone."""
        target = self._get_target_object()
        if isinstance(target, Character) and target not in self.ai_ships:
            self.current_target = None

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
        resolution); everything else (Landable, CelestialBody, CentralStar)
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

        # Normalize direction
        dir_x = dx / distance
        dir_y = dy / distance

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

    def _draw_jump_streak(self, surface):
        """Bright motion-streak lines trailing the ship during high-speed jump travel."""
        rad = math.radians(self.player.angle)
        back_x, back_y = -math.sin(rad), math.cos(rad)
        right_x, right_y = math.cos(rad), math.sin(rad)
        ship_x, ship_y = self.player.x, self.player.y
        streak_length = 220

        for offset in (-14, -5, 5, 14):
            start_x = ship_x + right_x * offset
            start_y = ship_y + right_y * offset
            end_x = start_x + back_x * streak_length
            end_y = start_y + back_y * streak_length
            pygame.draw.line(surface, CYAN, utils.to_screen(start_x, start_y), utils.to_screen(end_x, end_y), 2)

    def _draw_minimap(self, surface, target_obj):
        """Square radar in the top-right corner: player stays centered, every
        other system object is plotted as a point at its true relative
        position/color, scaled down to MINIMAP_RANGE world units per half-width.
        Objects beyond that range simply don't appear - this is a local radar,
        not the galaxy-scale StarMap (M key), so it never needs to pan/zoom.
        Returns its rect so the HUD can stack the jump-target panel below it.
        """
        ui_scale = get_ui_scale()
        size = int(MINIMAP_SIZE * ui_scale)
        margin = int(10 * ui_scale)
        rect = pygame.Rect(0, 0, size, size)
        rect.topright = (utils.screen_width - margin, margin)

        draw_glass_panel(surface, rect, ui_scale)

        px_per_unit = (size / 2) / MINIMAP_RANGE

        def project(x, y):
            return rect.centerx + (x - self.player.x) * px_per_unit, rect.centery + (y - self.player.y) * px_per_unit

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

        for obj, color, radius in points:
            sx, sy = project(obj.x, obj.y)
            if rect.left <= sx <= rect.right and rect.top <= sy <= rect.bottom:
                r = max(1, int(radius * ui_scale))
                pygame.draw.circle(surface, color, (int(sx), int(sy)), r)
                if obj is target_obj:
                    pygame.draw.circle(surface, YELLOW, (int(sx), int(sy)), r + int(4 * ui_scale), 1)

        # Player is always exactly centered, drawn last so it stays on top.
        pygame.draw.circle(surface, CYAN, rect.center, max(2, int(3 * ui_scale)))

        font_label = get_font(int(14 * ui_scale))
        label = font_label.render("System Map", True, GRAY)
        surface.blit(label, (rect.x + int(6 * ui_scale), rect.y + int(4 * ui_scale)))

        return rect

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
        flags = self.player.person.possessions.flags
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

    def _check_one_way_hails(self):
        """Let an NPC-initiated hail (pilots.json's "one_way_hail" - see
        Character.for_ai_pilot) fire once the player gets close enough:
        shows a transient banner (not the full hail_dialogue - the player
        still has to hail back with H to actually talk, per
        docs/CONTROLS.md), records it in the Messages pane's log (see
        Possessions.add_message - the banner alone is easy to miss, but the
        log stays until read), and sets a flag so it never fires twice for
        the same pilot. Only checks the active system's ships
        (self.ai_ships) - proximity to the player only means anything in
        whichever system they're actually in - and skips entirely while a
        hail is already open, so an incoming banner can't steal focus out
        from under a conversation the player is already having."""
        if self.active_dialogue:
            return
        possessions = self.player.person.possessions
        flags = possessions.flags
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
                pilot_name = ai_ship.person.name or "Unknown"
                message = one_way.get("message", "...")
                self.hail_banner = (f'Incoming transmission - {pilot_name}: "{message}"', CYAN)
                self.hail_banner_timer = ONE_WAY_HAIL_BANNER_FRAMES
                possessions.add_message(pilot_name, message)
                return  # one at a time - avoids stacking two banners the same frame

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
        status-pane hint. Uses the exact same threshold _try_jump already
        requires for a self-jump back to this system, so the hint and the
        mechanic it's pointing at agree by construction."""
        cx, cy = SYSTEM_CENTER
        return math.sqrt((self.player.x - cx) ** 2 + (self.player.y - cy) ** 2) >= JUMP_SELF_MIN_DISTANCE

    def _try_jump(self):
        """Validate the current star map selection/distance, then start a jump if valid."""
        if not self.selected_system_id:
            return
        cx, cy = SYSTEM_CENTER
        distance_from_center = math.sqrt((self.player.x - cx) ** 2 + (self.player.y - cy) ** 2)
        if self.selected_system_id == self.system_id and distance_from_center < JUMP_SELF_MIN_DISTANCE:
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

        origin_pos = origin["star_map_position"]
        dest_pos = destination["star_map_position"]
        dx = dest_pos["x"] - origin_pos["x"]
        dy = dest_pos["y"] - origin_pos["y"]
        if dx == 0 and dy == 0:
            dx = 1  # degenerate guard: jumping to a system at the same map position

        heading = math.degrees(math.atan2(dx, -dy)) % 360

        self.player.autopilot_active = False
        self.player.autopilot_target = None
        self.player.thrust = 0
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
            ship.velocity_x = math.sin(rad) * JUMP_SPEED
            ship.velocity_y = -math.cos(rad) * JUMP_SPEED
            ship.x += ship.velocity_x
            ship.y += ship.velocity_y
            js["timer"] += 1
            if js["timer"] >= JUMP_TRAVEL_FRAMES:
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
        arrival_x = center_x - math.sin(heading_rad) * JUMP_ARRIVAL_DISTANCE
        arrival_y = center_y + math.cos(heading_rad) * JUMP_ARRIVAL_DISTANCE

        ship = self.player.ship
        ship.x, ship.y = arrival_x, arrival_y
        ship.angle = js["heading"] % 360
        arrival_speed = ship.max_velocity * 1.6
        ship.velocity_x = math.sin(heading_rad) * arrival_speed
        ship.velocity_y = -math.cos(heading_rad) * arrival_speed
        ship.thrust = 0

        self.jump_state = None
        self.selected_system_id = None
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
        if self.jump_state:
            self._update_jump()
        else:
            self.player.update()
        if self.player.thrust > 0:
            # Generic gameplay-event flag - see K_SPACE's comment above on
            # why these live on Possessions.flags instead of a
            # SpaceScreen-only field.
            self.player.person.possessions.flags["used_thrust"] = True
        for state in self.systems.values():
            state.update_physics()
        self.asteroid_field.update()
        if self.jump_message_timer > 0:
            self.jump_message_timer -= 1
        if self.hail_banner_timer > 0:
            self.hail_banner_timer -= 1
        self._check_one_way_hails()
        self._validate_target()
        check_mission_progress(self.missions_config, self.player.person.possessions)

    def update(self):
        """Full update including camera - only called when space is active screen"""
        # Auto-land if autopilot has actually arrived (has_arrived - the same
        # tight distance/speed SeekMode itself requires to stop). Checked
        # *before* update_physics() runs this frame's autopilot step: SeekMode
        # reaching that exact same condition inside update_physics() disengages
        # and clears autopilot_target itself, so checking after would just see
        # autopilot_active already False and never trigger the landing-screen
        # transition at all. This used to check its own looser distance/speed
        # (full landing_distance, speed<0.4) instead, so it fired well before
        # the ship actually braked down to SeekMode's intended stopping point -
        # visibly "giving up" on braking early with a lot of residual speed.
        if self.player.autopilot_active and self.player.autopilot_target and has_arrived(self.player, self.player.autopilot_target):
            target = self.player.autopilot_target
            self.player.park()
            self.player.autopilot_active = False
            self.player.autopilot_target = None
            # Only try to land on landables, not ships
            if target == self.station:
                self.landing_target = "station"
                self._mark_landed()
                return "land"
            elif target == self.moon:
                self.landing_target = "moon"
                self._mark_landed()
                return "land"

        self.update_physics()

        # Update camera to follow player
        set_camera_offset(self.player.x - GAME_WIDTH // 2, self.player.y - GAME_HEIGHT // 2)

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
        surface.fill(BLACK)
        self.star_field.draw(surface)
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
        if self.jump_state and self.jump_state["phase"] == "travel":
            self._draw_jump_streak(surface)

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
            # Ships show their pilot; landables (station/moon) list what's
            # inside them so the player can see where they'll end up before
            # committing to land; other bodies show a hazard note if any -
            # these are mutually exclusive categories of targetable_objects.
            if isinstance(target_obj, Character):
                pilot_name = target_obj.person.name
                if pilot_name:
                    lines.append((f"  Pilot: {pilot_name}", GREEN))
            elif isinstance(target_obj, Landable):
                lines.append(("  Locations:", GREEN))
                for label in target_obj.get_interior_labels():
                    lines.append((f"    - {label}", GRAY))
            elif getattr(target_obj, "hazardous", False):
                lines.append(("  Hazardous - not landable", YELLOW))
        else:
            lines.append(("Target: None", GRAY))

        if self.selected_system_id:
            systems = get_star_systems(self.story)
            selected_name = systems.get(self.selected_system_id, {}).get("name", self.selected_system_id)
            jump_label = selected_name
            if self.selected_system_id == self.system_id:
                jump_label += " (current)"
            lines.append((f"Jump Target: {jump_label}", CYAN))
        else:
            lines.append(("Jump Target: None", GRAY))

        info_rect = draw_info_panel(surface, lines, ui_scale, (utils.screen_width - margin, minimap_rect.bottom + margin))

        # --- Top-left: control-help pane (shared design with LocationScreen's -
        # see draw_controls_pane). Skipped (draw_hud=False) whenever a modal
        # menu on top of this screen is showing its own controls pane in
        # the same spot instead. Swapped for the hail dialogue's own
        # controls while active_dialogue is set - same idea as
        # LocationScreen's own active_dialogue swap - since none of the
        # normal flight/targeting controls apply while a conversation has
        # input focus (see handle_input).
        controls_rect = None
        if self.active_dialogue:
            help_items = [("W/S or Up/Down", "Navigate"), ("Enter", "Choose"), ("ESC", "Close")]
            controls_rect = draw_controls_pane(surface, margin, margin, "Controls", help_items, ui_scale)
        elif draw_hud:
            help_items = [
                ("ESC", "Pause"),
                ("WASD/Arrows", "Thrust/Turn"),
                ("T", "Target Mode"),
                ("]", "Next Target"),
                ("[", "Previous Target"),
                ("H", "Hail Target"),
                ("M", "Star Map"),
                ("P", "View Possessions"),
                ("N", "Mission Log"),
                ("Click", "Target Object"),
            ]
            controls_rect = draw_controls_pane(surface, margin, margin, "Controls", help_items, ui_scale)

        # --- Top-center: transient "too close to jump" warning, or an
        # incoming/blocked hail banner (see _check_one_way_hails/_start_hail) -
        # mutually exclusive with each other in practice (jumping and
        # hailing don't happen at the same moment) so sharing this one slot
        # is fine.
        if self.jump_message_timer > 0:
            font_warn = get_font(int(20 * ui_scale))
            draw_glow_title(
                surface, "Too close to jump - move away from center first", font_warn,
                utils.screen_width // 2, margin + int(10 * ui_scale),
                color=YELLOW, shadow_color=(60, 45, 10)
            )
        elif self.hail_banner_timer > 0 and self.hail_banner:
            text, color = self.hail_banner
            font_hail = get_font(int(20 * ui_scale))
            draw_glow_title(
                surface, text, font_hail,
                utils.screen_width // 2, margin + int(10 * ui_scale),
                color=color, shadow_color=(20, 30, 40)
            )

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
            else:
                if self.landing_text > 0:
                    status_lines.append(("Press L to Land", GREEN))
                elif speed >= 0.4 and (
                    self.station.get_distance(self.player.x, self.player.y) < self.station.landing_distance
                    or self.moon.get_distance(self.player.x, self.player.y) < self.moon.landing_distance
                ):
                    status_lines.append(("Slow down to land", RED))
                if self.selected_system_id:
                    status_lines.append(("Press J to Jump", GREEN))
                elif self._drifted_from_center():
                    # Reuses JUMP_SELF_MIN_DISTANCE (not a separate tuning
                    # value) - that's exactly the distance a self-jump back
                    # to this same system already requires, so the hint
                    # appears exactly when it becomes actionable.
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
            message_log_rect = draw_message_log(surface, messages, ui_scale)

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
