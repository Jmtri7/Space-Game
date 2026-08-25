"""Main space exploration screen with ships and landing."""
import pygame
import math
import game.constants as constants
from game.constants import GAME_WIDTH, GAME_HEIGHT, BLACK, YELLOW, WHITE, GREEN, GRAY, CYAN
from game.utils import (
    get_scale, get_offset, get_ui_scale, load_json, set_camera_offset,
    draw_debug_marker, draw_target_brackets, get_font,
    get_ship_type, get_graphics_asset, get_pilot, get_star_systems
)
import game.utils as utils
from game.ui.ui_theme import draw_glass_panel, draw_glow_title
from game.screens.screen_base import ScreenBase
from game.screens.location_screen import LocationScreen
from game.world.player_controller import PlayerController
from game.world.autopilot import has_arrived
from game.world.character import Character
from game.world.landable import Landable
from game.world.starfield import StarField
from game.world.central_star import CentralStar
from game.world.celestial_body import CelestialBody
from game.world.asteroid_field import AsteroidField
from game.world.system_state import SystemState

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
        state.asteroid_field = AsteroidField(seed=config.get("asteroid_seed", 1))
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

    def get_interior_screen(self, landable, key, world_width, world_height):
        """Return the persistent LocationScreen for one of landable's
        interiors (key = "default" for a station, "city"/"wilderness" for
        the moon), creating and caching it on landable.interior_screens the
        first time it's visited. Later visits reuse the same instance, so
        NPCs and the player's position within it persist instead of
        resetting every time - and it can keep simulating in the
        background (see update_physics() calls in main.py) while the
        player is elsewhere. Returns None if the interior isn't configured.
        """
        if key in landable.interior_screens:
            return landable.interior_screens[key]

        interior_config = landable.interiors.get(key)
        if not interior_config:
            return None

        if isinstance(interior_config, str):
            screen = LocationScreen(config_file=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story, player_possessions=self.player.person.possessions, on_ship_purchased=self._on_ship_purchased)
        else:
            screen = LocationScreen(config_data=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story, player_possessions=self.player.person.possessions, on_ship_purchased=self._on_ship_purchased)
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
        self.player.ship.acceleration_magnitude = ship_type.get("max_thrust", self.player.ship.acceleration_magnitude)
        self.player.ship.max_velocity = ship_type.get("max_velocity", self.player.ship.max_velocity)
        self.player.ship.rotation_speed = ship_type.get("rotation_speed", self.player.ship.rotation_speed)
        self.player.ship.graphics = graphics

    def _on_ship_purchased(self, ship_type_id):
        """Configure the player's real ship to match a newly bought type,
        and park it right at the station - so it's "docked outside" exactly
        as a salesman's dialogue would say, ready the moment the player
        boards through the spaceport's exit."""
        self._apply_ship_type(ship_type_id)
        self.park_at(self.station)

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
        if not self.jump_state:
            self.player.handle_input(keys)

        for event in events:
            if event.type == pygame.KEYDOWN:
                # Cancel autopilot on any key press (except ESC which handles pause)
                if self.player.autopilot_active and event.key != pygame.K_ESCAPE:
                    self.player.autopilot_active = False
                    self.player.autopilot_target = None
                    return None

                if event.key == pygame.K_ESCAPE:
                    return "pause"
                elif event.key in (pygame.K_t, pygame.K_RIGHTBRACKET):
                    self._cycle_target(1)
                elif event.key == pygame.K_LEFTBRACKET:
                    self._cycle_target(-1)
                elif event.key == pygame.K_TAB:
                    self._cycle_target_mode()
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
                                return "land"
                            elif target_obj == self.moon:
                                self.landing_target = "moon"
                                return "land"
                    landing_target = self._check_landing()
                    if landing_target:
                        self.landing_target = landing_target
                        return "land"
                elif event.key == pygame.K_SPACE:
                    # Engage autopilot toward the current target - follows an
                    # AI ship, or approaches a landable from any range (L
                    # only lands once you're already close).
                    target_obj = self._get_target_object()
                    if target_obj and self.current_target is not None:
                        self.player.engage_seek(target_obj)
                elif event.key == pygame.K_m and not self.jump_state:
                    return "star_map"
                elif event.key == pygame.K_j and not self.jump_state:
                    self._try_jump()
                elif event.key == pygame.K_p:
                    return "possessions"
        return None

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

    def _check_landing(self):
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)

        station_distance = self.station.get_distance(self.player.x, self.player.y)
        if station_distance < self.station.landing_distance and speed < 0.4:
            return "station"

        moon_distance = self.moon.get_distance(self.player.x, self.player.y)
        if moon_distance < self.moon.landing_distance and speed < 0.4:
            return "moon"

        return None

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
        for state in self.systems.values():
            state.update_physics()
        self.asteroid_field.update()
        if self.jump_message_timer > 0:
            self.jump_message_timer -= 1

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
                return "land"
            elif target == self.moon:
                self.landing_target = "moon"
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

    def draw(self, surface):
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

        self._draw_hud(surface, target_obj)

    def _draw_hud(self, surface, target_obj):
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
        font_body = get_font(int(18 * ui_scale))
        pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
        margin = int(10 * ui_scale)
        line_height = int(22 * ui_scale)

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

        rendered = [font_body.render(text, True, color) for text, color in lines]
        panel_width = max(text.get_width() for text in rendered) + pad_x * 2
        panel_height = pad_y * 2 + line_height * len(rendered)
        info_rect = pygame.Rect(0, 0, panel_width, panel_height)
        info_rect.topright = (utils.screen_width - margin, minimap_rect.bottom + margin)
        draw_glass_panel(surface, info_rect, ui_scale)
        for i, text in enumerate(rendered):
            surface.blit(text, (info_rect.x + pad_x, info_rect.y + pad_y + i * line_height))

        # --- Top-left: control-help pane, one control per line, same text
        # size as the targeting info panel (font_body). Key and description
        # are rendered as separate columns (rather than one padded string)
        # so the colons line up visually despite the default pygame font
        # not being monospace - space-padding a single string wouldn't.
        help_title = "Controls"
        help_items = [
            ("T / ]", "Next Target"),
            ("[", "Previous Target"),
            ("Tab", "Target Mode"),
            ("Space", "Autopilot"),
            ("L", "Land"),
            ("M", "Star Map"),
            ("ESC", "Pause"),
        ]
        title_rendered = font_body.render(help_title, True, WHITE)
        key_rendered = [font_body.render(key, True, WHITE) for key, _ in help_items]
        desc_rendered = [font_body.render(desc, True, WHITE) for _, desc in help_items]
        colon_rendered = font_body.render(":", True, WHITE)
        key_column_width = max(text.get_width() for text in key_rendered)
        colon_gap = int(6 * ui_scale)
        desc_gap = int(8 * ui_scale)
        desc_x_offset = key_column_width + colon_gap + colon_rendered.get_width() + desc_gap

        help_panel_width = max(
            title_rendered.get_width(),
            desc_x_offset + max(text.get_width() for text in desc_rendered),
        ) + pad_x * 2
        # Title line, then a blank line's worth of gap, then one line per control.
        help_panel_height = pad_y * 2 + line_height * (len(help_items) + 2)
        help_rect = pygame.Rect(margin, margin, help_panel_width, help_panel_height)
        draw_glass_panel(surface, help_rect, ui_scale)

        surface.blit(title_rendered, (help_rect.x + pad_x, help_rect.y + pad_y))
        colon_x = help_rect.x + pad_x + key_column_width + colon_gap
        desc_x = help_rect.x + pad_x + desc_x_offset
        for i, (key_text, desc_text) in enumerate(zip(key_rendered, desc_rendered)):
            row_y = help_rect.y + pad_y + (i + 2) * line_height
            surface.blit(key_text, (colon_x - key_text.get_width(), row_y))
            surface.blit(colon_rendered, (colon_x, row_y))
            surface.blit(desc_text, (desc_x, row_y))

        # --- Top-center: transient "too close to jump" warning ---
        if self.jump_message_timer > 0:
            font_warn = get_font(int(20 * ui_scale))
            draw_glow_title(
                surface, "Too close to jump - move away from center first", font_warn,
                utils.screen_width // 2, margin + int(10 * ui_scale),
                color=YELLOW, shadow_color=(60, 45, 10)
            )

        # --- Bottom-center: current status (autopilot/landing/jump -
        # mutually exclusive), standalone now that the control-help bar
        # that used to anchor it has moved to the left pane.
        status_text, status_color = None, None
        if self.jump_state:
            status_text = "Aligning for jump..." if self.jump_state["phase"] == "align" else "JUMPING..."
            status_color = CYAN
        elif self.player.autopilot_active:
            status_text = "Autopilot engaged - press any key to cancel"
            status_color = CYAN
        elif self.landing_text > 0:
            status_text = "Press L to land"
            status_color = YELLOW
        elif self.selected_system_id:
            status_text = "Press J to Jump"
            status_color = CYAN

        if status_text:
            font_status = get_font(int(22 * ui_scale))
            status_render = font_status.render(status_text, True, status_color)
            status_panel = pygame.Rect(0, 0, status_render.get_width() + pad_x * 2, status_render.get_height() + pad_y * 2)
            status_panel.midbottom = (utils.screen_width // 2, utils.screen_height - margin)
            draw_glass_panel(surface, status_panel, ui_scale)
            surface.blit(status_render, (status_panel.x + pad_x, status_panel.y + pad_y))

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
