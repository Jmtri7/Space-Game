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
from game.world.ai_ship import AIShip
from game.world.landable import Landable
from game.world.starfield import StarField
from game.world.central_star import CentralStar
from game.world.celestial_body import CelestialBody
from game.world.asteroid_field import AsteroidField

# Jump mechanic tuning
JUMP_ALIGN_TOLERANCE = 3        # degrees; how close to heading before travel starts
JUMP_TRAVEL_FRAMES = 150        # ~2.5s at 60fps of high-speed travel
JUMP_SPEED = 40                 # world units/frame while traveling
JUMP_ARRIVAL_DISTANCE = 1400    # world units from system center on arrival
JUMP_SELF_MIN_DISTANCE = 700    # must be at least this far from center to jump "back"
SYSTEM_CENTER = (GAME_WIDTH / 2, GAME_HEIGHT / 2)


class SpaceScreen(ScreenBase):
    """Main space exploration screen with ships and landing."""
    def __init__(self, system_config=None, pilot_name="", story="default", system_id=None):
        super().__init__(pilot_name=pilot_name)
        self.story = story  # fixed for the whole playthrough - stories are wholly separate

        # Load story metadata (player ship type, starting system, etc)
        story_meta = load_json(f"config/stories/{story}/story.json") or {}
        self.system_id = system_id or story_meta.get("starting_system", "default")

        # Load config for the current system within this story
        self.system_config = system_config or load_json(f"config/stories/{story}/systems/{self.system_id}.json") or {}

        # Get space system drag (default 0 = no drag)
        space_drag = self.system_config.get("drag", 0)

        # Get player ship type and graphics (fixed for the story, not per-system)
        player_ship_type_id = story_meta.get("ships", {}).get("player_type", "shuttle")
        player_ship_type = get_ship_type(self.story, player_ship_type_id)
        player_graphics = get_graphics_asset(self.story, "ships", player_ship_type_id)

        # Spawn away from map center by default, since that's where a central
        # star (if the system has one) usually sits.
        player_start_cfg = self.system_config.get("player_start", {})
        player_x = GAME_WIDTH * player_start_cfg.get("x", 0.4)
        player_y = GAME_HEIGHT * player_start_cfg.get("y", 0.35)
        self.player = PlayerController(player_x, player_y, space_drag=space_drag, graphics=player_graphics, ship_type=player_ship_type, pilot_name=pilot_name)

        self._load_system_content()

        self.landing_text = 0
        self.landing_target = None
        self.camera_x = 0
        self.camera_y = 0
        self.selected_system_id = None  # Star map selection, for the Jump mechanic
        self.jump_state = None  # None, or a dict tracking the jump animation
        self.jump_message_timer = 0  # Transient "too close to jump" feedback

    def _load_system_content(self):
        """(Re)build station/moon/central star/asteroids/AI ships/star field from
        self.system_config. Called at construction, and again after a jump swaps
        the active system (within the same story) - the player (ship/pilot) is
        untouched by this."""
        space_drag = self.system_config.get("drag", 0)
        self.player.ship.space_drag = space_drag
        self.star_field = StarField(seed=self.system_config.get("star_seed", 0))

        # Load graphics assets for station and moon - each system picks its own
        station_asset_id = self.system_config.get("station_asset", "station_alpha")
        moon_asset_id = self.system_config.get("moon_asset", "moon_silver")

        station_cfg = self.system_config.get("station", {})
        station_graphics = get_graphics_asset(self.story, "space_stations", station_asset_id)
        self.station = Landable(GAME_WIDTH * station_cfg.get("x", 0.75), GAME_HEIGHT * station_cfg.get("y", 0.3), graphics=station_graphics, interiors=station_cfg.get("interiors", {}), name=station_cfg.get("name", "Station"))

        moon_cfg = self.system_config.get("moon", {})
        moon_graphics = get_graphics_asset(self.story, "moons", moon_asset_id)
        self.moon = Landable(GAME_WIDTH * moon_cfg.get("x", 0.2), GAME_HEIGHT * moon_cfg.get("y", 0.4), graphics=moon_graphics, interiors=moon_cfg.get("interiors", {}), name=moon_cfg.get("name", "Moon"))

        # Central star (optional, drawn but not landable/targetable)
        central_star_cfg = self.system_config.get("central_star")
        if central_star_cfg:
            self.central_star = CentralStar(GAME_WIDTH * central_star_cfg.get("x", 0.5), GAME_HEIGHT * central_star_cfg.get("y", 0.5), graphics=central_star_cfg)
        else:
            self.central_star = None

        # Non-landable planets/ice balls/gas giants - just scenery to fly near,
        # never something you can dock at (see CelestialBody.hazardous, used
        # by the HUD's targeting note).
        self.celestial_bodies = [
            CelestialBody(GAME_WIDTH * body_cfg.get("x", 0.5), GAME_HEIGHT * body_cfg.get("y", 0.5), graphics=body_cfg)
            for body_cfg in self.system_config.get("celestial_bodies", [])
        ]

        # Asteroids: infinite, seeded, generated only in chunks near the camera
        self.asteroid_field = AsteroidField(seed=self.system_config.get("asteroid_seed", 1))

        # Landables that an AI ship's route config can reference by key
        landable_lookup = {"station": self.station, "moon": self.moon}

        # Load all AI ships from config
        self.ai_ships = []
        for ai_cfg in self.system_config.get("ai_ships", []):
            ship_type_id = ai_cfg.get("ship_type", "freighter")
            ship_type = get_ship_type(self.story, ship_type_id)
            ship_graphics = get_graphics_asset(self.story, "ships", ship_type_id)
            pilot = get_pilot(self.story, ai_cfg["pilot"]) if "pilot" in ai_cfg else None
            route = [landable_lookup[key] for key in ai_cfg.get("route", []) if key in landable_lookup]
            ai_ship = AIShip(
                GAME_WIDTH * ai_cfg.get("x", 0.75),
                GAME_HEIGHT * ai_cfg.get("y", 0.1),
                space_drag=space_drag,
                ship_type=ship_type,
                ship_type_id=ship_type_id,
                graphics=ship_graphics,
                pilot=pilot,
                route=route,
                get_interior_screen=self.get_interior_screen
            )
            self.ai_ships.append(ai_ship)

        # Keep self.ai_ship for backwards compatibility (first ship if it exists)
        self.ai_ship = self.ai_ships[0] if self.ai_ships else None

        self.current_target = None
        self.targetable_objects = [
            (self.station.name, self.station),
            (self.moon.name, self.moon),
        ]
        if self.central_star:
            self.targetable_objects.append((self.central_star.name, self.central_star))
        for body in self.celestial_bodies:
            self.targetable_objects.append((body.name, body))
        # Add all AI ships to targetable objects
        for i, ship in enumerate(self.ai_ships):
            # Use ship type name if available, otherwise use generic label
            ship_type = get_ship_type(self.story, ship.ship_type_id)
            ship_name = ship_type.get("name", f"AI Ship {i+1}")
            pilot_name = ship.pilot.get("name")
            if pilot_name:
                ship_name = f"{ship_name} ({pilot_name})"
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
            screen = LocationScreen(config_file=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story)
        else:
            screen = LocationScreen(config_data=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story)
        landable.interior_screens[key] = screen
        return screen

    def handle_input(self, events):
        keys = pygame.key.get_pressed()
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
                elif event.key == pygame.K_l:
                    # If target is selected
                    target_obj = self._get_target_object()
                    if target_obj and self.current_target is not None:
                        # For AI ships, always engage autopilot to follow them
                        if isinstance(target_obj, AIShip):
                            self.player.engage_seek(target_obj)
                        # For landables (station/moon), check if in landing range
                        else:
                            distance = target_obj.get_distance(self.player.x, self.player.y)
                            speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
                            # If close and slow enough, land directly
                            if distance < target_obj.landing_distance and speed < 0.4:
                                if target_obj == self.station:
                                    self.landing_target = "station"
                                    return "land"
                                elif target_obj == self.moon:
                                    self.landing_target = "moon"
                                    return "land"
                            else:
                                # Otherwise engage autopilot to approach target
                                self.player.engage_seek(target_obj)
                    else:
                        # No target selected, check if close enough to land manually
                        landing_target = self._check_landing()
                        if landing_target:
                            self.landing_target = landing_target
                            return "land"
                elif event.key == pygame.K_m and not self.jump_state:
                    return "star_map"
                elif event.key == pygame.K_j and not self.jump_state:
                    self._try_jump()
        return None

    def _cycle_target(self, direction=1):
        """Cycle through targetable objects - direction=1 for T/], -1 for [."""
        if not self.targetable_objects:
            return
        if self.current_target is None:
            self.current_target = 0
        else:
            self.current_target = (self.current_target + direction) % len(self.targetable_objects)

    def _get_target_name(self):
        """Get the name of the current target"""
        if self.current_target is None or self.current_target >= len(self.targetable_objects):
            return None
        return self.targetable_objects[self.current_target][0]

    def _get_target_object(self):
        """Get the current target object"""
        if self.current_target is None or self.current_target >= len(self.targetable_objects):
            return None
        return self.targetable_objects[self.current_target][1]

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
            self.system_id = destination
            self.system_config = load_json(f"config/stories/{self.story}/systems/{destination}.json") or {}
            self._load_system_content()

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
        """Update physics without camera - used when space is background"""
        if self.jump_state:
            self._update_jump()
        else:
            self.player.update()
        self.station.update()
        self.moon.update()
        for body in self.celestial_bodies:
            body.update()
        for ai_ship in self.ai_ships:
            ai_ship.update()
        self.asteroid_field.update()
        if self.jump_message_timer > 0:
            self.jump_message_timer -= 1

    def update(self):
        """Full update including camera - only called when space is active screen"""
        self.update_physics()

        # Update camera to follow player
        set_camera_offset(self.player.x - GAME_WIDTH // 2, self.player.y - GAME_HEIGHT // 2)

        if self.jump_state:
            return  # skip landing checks entirely while jumping

        # Auto-land if autopilot is active and in range
        if self.player.autopilot_active and self.player.autopilot_target:
            distance = self.player.autopilot_target.get_distance(self.player.x, self.player.y)
            speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
            # Use landing_distance if available (for landables), otherwise use default close distance (for ships)
            landing_distance = getattr(self.player.autopilot_target, 'landing_distance', 100)
            if distance < landing_distance and speed < 0.4:
                self.player.autopilot_active = False
                # Only try to land on landables, not ships
                if self.player.autopilot_target == self.station:
                    self.landing_target = "station"
                    return "land"
                elif self.player.autopilot_target == self.moon:
                    self.landing_target = "moon"
                    return "land"

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
            draw_target_brackets(surface, target_obj.x, target_obj.y)
            self._draw_target_arrow(surface, target_obj)

        scale = get_scale()
        offset_x, offset_y = get_offset()
        border_rect = (int(offset_x), int(offset_y), int(GAME_WIDTH * scale), int(GAME_HEIGHT * scale))
        pygame.draw.rect(surface, (100, 100, 100), border_rect, 2)

        self._draw_hud(surface, target_obj)

    def _draw_hud(self, surface, target_obj):
        """Ship status, targeting, jump-target, and status-message overlays -
        styled with the same glass-panel look as the menus (ui_theme.py)
        instead of each being its own ad-hoc text blit.

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

        # --- Top-left: ship status panel (speed, plus target if any).
        # Always both lines (a placeholder "None" target line rather than
        # omitting it) so the panel doesn't resize every time targeting is
        # toggled - only its selected/deselected color changes.
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
        target_name = self._get_target_name()
        if target_obj and target_name:
            distance = self.player.get_distance(target_obj.x, target_obj.y)
            target_line, target_color = f"Target: {target_name} ({distance:.0f})", GREEN
        else:
            target_line, target_color = "Target: None", GRAY
        lines = [(f"Speed: {speed:.2f}", WHITE), (target_line, target_color)]
        # Landables (station/moon) list what's inside them, right under the
        # target line - lets the player see where they'll end up before
        # committing to land.
        if isinstance(target_obj, Landable):
            for label in target_obj.get_interior_labels():
                lines.append((f"  - {label}", GRAY))
        elif target_obj and getattr(target_obj, "hazardous", False):
            lines.append(("  Hazardous - not landable", YELLOW))

        line_height = int(22 * ui_scale)
        rendered = [font_body.render(text, True, color) for text, color in lines]
        panel_width = max(text.get_width() for text in rendered) + pad_x * 2
        panel_height = pad_y * 2 + line_height * len(rendered)
        status_rect = pygame.Rect(margin, margin, panel_width, panel_height)
        draw_glass_panel(surface, status_rect, ui_scale)
        for i, text in enumerate(rendered):
            surface.blit(text, (status_rect.x + pad_x, status_rect.y + pad_y + i * line_height))

        # --- Top-right: jump target panel (persists across star map open/close) ---
        if not self.jump_state and self.selected_system_id:
            systems = get_star_systems(self.story)
            selected_name = systems.get(self.selected_system_id, {}).get("name", self.selected_system_id)
            label = f"Jump Target: {selected_name}"
            if self.selected_system_id == self.system_id:
                label += " (current)"
            label_text = font_body.render(label, True, CYAN)
            jump_rect = pygame.Rect(0, 0, label_text.get_width() + pad_x * 2, label_text.get_height() + pad_y * 2)
            jump_rect.topright = (utils.screen_width - margin, margin)
            draw_glass_panel(surface, jump_rect, ui_scale)
            surface.blit(label_text, (jump_rect.x + pad_x, jump_rect.y + pad_y))

        # --- Top-center: transient "too close to jump" warning ---
        if self.jump_message_timer > 0:
            font_warn = get_font(int(20 * ui_scale))
            draw_glow_title(
                surface, "Too close to jump - move away from center first", font_warn,
                utils.screen_width // 2, margin + int(10 * ui_scale),
                color=YELLOW, shadow_color=(60, 45, 10)
            )

        # --- Bottom-center: a control-help bar (always) with the current
        # status (autopilot/landing/jump - mutually exclusive) as its own
        # panel directly above, so the two never crowd into one another.
        help_text = font_body.render("T/[/]: target, L: land, M: star map, ESC: pause", True, WHITE)
        help_rect = pygame.Rect(0, 0, help_text.get_width() + pad_x * 2, help_text.get_height() + pad_y * 2)
        help_rect.midbottom = (utils.screen_width // 2, utils.screen_height - margin)
        draw_glass_panel(surface, help_rect, ui_scale)
        surface.blit(help_text, (help_rect.x + pad_x, help_rect.y + pad_y))

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

        if status_text:
            font_status = get_font(int(22 * ui_scale))
            status_render = font_status.render(status_text, True, status_color)
            status_panel = pygame.Rect(0, 0, status_render.get_width() + pad_x * 2, status_render.get_height() + pad_y * 2)
            status_panel.midbottom = (utils.screen_width // 2, help_rect.top - int(8 * ui_scale))
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
            }
        }
        # Save all AI ships
        if self.ai_ships:
            state["ai_ships"] = []
            for ai_ship in self.ai_ships:
                state["ai_ships"].append({
                    "x": ai_ship.x,
                    "y": ai_ship.y,
                    "angle": ai_ship.angle,
                    "velocity_x": ai_ship.velocity_x,
                    "velocity_y": ai_ship.velocity_y,
                    "thrust": ai_ship.thrust
                })
        return state

    def restore_state(self, state):
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
        # Restore all AI ships
        if "ai_ships" in state:
            for i, ai_state in enumerate(state["ai_ships"]):
                if i < len(self.ai_ships):
                    self.ai_ships[i].x = ai_state.get("x", self.ai_ships[i].x)
                    self.ai_ships[i].y = ai_state.get("y", self.ai_ships[i].y)
                    self.ai_ships[i].angle = ai_state.get("angle", self.ai_ships[i].angle)
                    self.ai_ships[i].velocity_x = ai_state.get("velocity_x", self.ai_ships[i].velocity_x)
                    self.ai_ships[i].velocity_y = ai_state.get("velocity_y", self.ai_ships[i].velocity_y)
                    self.ai_ships[i].thrust = ai_state.get("thrust", self.ai_ships[i].thrust)
