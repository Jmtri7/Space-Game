"""Main space exploration screen with ships and landing."""
import pygame
import math
import constants
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK, YELLOW, WHITE, GREEN, CYAN
from utils import (
    get_scale, get_offset, get_ui_scale, get_ui_offset, load_json, set_camera_offset,
    draw_debug_marker, draw_target_brackets, draw_landing_prediction, draw_landing_trajectory,
    get_ship_type, get_graphics_asset
)
import utils
from screen_base import ScreenBase
from player_controller import PlayerController
from ai_ship import AIShip
from landable import Landable
from starfield import StarField


class GameScreen(ScreenBase):
    """Main space exploration screen with ships and landing."""
    def __init__(self, system_config=None, pilot_name="", story="default"):
        super().__init__(pilot_name=pilot_name)
        self.story = story

        # Load story metadata (ship types, graphics, etc)
        story_file = f"config/stories/{story}/story.json"
        story_meta = load_json(story_file) or {}

        # Load config from story directory
        config_file = f"config/stories/{story}/space_system.json"
        self.system_config = system_config or load_json(config_file) or {}

        # Get space system drag (default 0 = no drag)
        space_drag = self.system_config.get("drag", 0)

        self.player = PlayerController(GAME_WIDTH // 2, GAME_HEIGHT // 2, space_drag=space_drag)
        self.star_field = StarField()

        # Load graphics assets for station and moon
        station_asset_id = story_meta.get("assets", {}).get("space_station", "station_alpha")
        moon_asset_id = story_meta.get("assets", {}).get("moon", "moon_silver")

        station_cfg = self.system_config.get("station", {})
        station_graphics = get_graphics_asset("space_stations", station_asset_id)
        self.station = Landable(GAME_WIDTH * station_cfg.get("x", 0.75), GAME_HEIGHT * station_cfg.get("y", 0.3), graphics=station_graphics)

        moon_cfg = self.system_config.get("moon", {})
        moon_graphics = get_graphics_asset("moons", moon_asset_id)
        self.moon = Landable(GAME_WIDTH * moon_cfg.get("x", 0.2), GAME_HEIGHT * moon_cfg.get("y", 0.4), graphics=moon_graphics)

        # Load all AI ships from config
        self.ai_ships = []
        for ai_cfg in self.system_config.get("ai_ships", []):
            ship_type_id = ai_cfg.get("ship_type", "trader")
            ship_type = get_ship_type(ship_type_id)
            ai_ship = AIShip(
                GAME_WIDTH * ai_cfg.get("x", 0.75),
                GAME_HEIGHT * ai_cfg.get("y", 0.1),
                space_drag=space_drag,
                ship_type=ship_type,
                ship_type_id=ship_type_id
            )
            self.ai_ships.append(ai_ship)

        # Keep self.ai_ship for backwards compatibility (first ship if it exists)
        self.ai_ship = self.ai_ships[0] if self.ai_ships else None

        self.landing_text = 0
        self.landing_target = None
        self.camera_x = 0
        self.camera_y = 0
        self.current_target = None  # For T key targeting
        self.targetable_objects = [
            ("Station", self.station),
            ("Moon", self.moon),
        ]
        # Add all AI ships to targetable objects
        for i, ship in enumerate(self.ai_ships):
            self.targetable_objects.append((f"AI Ship {i+1}", ship))

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
                elif event.key == pygame.K_t:
                    self._cycle_target()
                elif event.key == pygame.K_l:
                    # If target is selected, check if already in landing range
                    target_obj = self._get_target_object()
                    if target_obj and self.current_target is not None:
                        distance = target_obj.get_distance(self.player.x, self.player.y)
                        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
                        # If close and slow enough, land directly
                        if distance < 150 and speed < 0.4:
                            if target_obj == self.station:
                                self.landing_target = "station"
                                return "land"
                            elif target_obj == self.moon:
                                self.landing_target = "moon"
                                return "land"
                        else:
                            # Otherwise engage autopilot to approach target
                            self.player.autopilot_active = True
                            self.player.autopilot_target = target_obj
                    else:
                        # No target selected, check if close enough to land manually
                        landing_target = self._check_landing()
                        if landing_target:
                            self.landing_target = landing_target
                            return "land"
        return None

    def _cycle_target(self):
        """Cycle through targetable objects"""
        if not self.targetable_objects:
            return
        # Find current target index
        if self.current_target is None:
            self.current_target = 0
        else:
            self.current_target = (self.current_target + 1) % len(self.targetable_objects)

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
        """Draw arrow at screen edge pointing toward target"""
        # Calculate direction from player to target
        dx = target.x - self.player.x
        dy = target.y - self.player.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance == 0:
            return

        # Normalize direction
        angle = math.atan2(dy, dx)
        dir_x = math.cos(angle)
        dir_y = math.sin(angle)

        # Find arrow position at screen edge
        ui_scale = get_ui_scale()
        ui_offset_x, ui_offset_y = get_ui_offset()
        surf_width = surface.get_width()
        surf_height = surface.get_height()

        # Screen bounds in UI space
        screen_left = ui_offset_x
        screen_right = ui_offset_x + surf_width
        screen_top = ui_offset_y
        screen_bottom = ui_offset_y + surf_height

        # Start from screen center (player position in UI space)
        center_x = ui_offset_x + surf_width // 2
        center_y = ui_offset_y + surf_height // 2

        # Calculate where ray hits screen edge
        t = 1
        if dir_x > 0:
            t = min(t, (screen_right - center_x) / dir_x)
        elif dir_x < 0:
            t = min(t, (screen_left - center_x) / dir_x)

        if dir_y > 0:
            t = min(t, (screen_bottom - center_y) / dir_y)
        elif dir_y < 0:
            t = min(t, (screen_top - center_y) / dir_y)

        arrow_x = center_x + dir_x * t
        arrow_y = center_y + dir_y * t

        # Clamp to screen edges with padding
        padding = 20
        arrow_x = max(screen_left + padding, min(screen_right - padding, arrow_x))
        arrow_y = max(screen_top + padding, min(screen_bottom - padding, arrow_y))

        # Draw arrow pointing toward target
        arrow_size = 12

        # Arrow head points in direction of target
        tip_x = arrow_x + dir_x * arrow_size
        tip_y = arrow_y + dir_y * arrow_size

        # Arrow tail points opposite
        tail_x = arrow_x - dir_x * arrow_size
        tail_y = arrow_y - dir_y * arrow_size

        # Perpendicular for arrow wings
        perp_x = -dir_y
        perp_y = dir_x

        # Draw arrow as triangle
        wing_size = 8
        wing1_x = tail_x + perp_x * wing_size
        wing1_y = tail_y + perp_y * wing_size
        wing2_x = tail_x - perp_x * wing_size
        wing2_y = tail_y - perp_y * wing_size

        points = [(tip_x, tip_y), (wing1_x, wing1_y), (wing2_x, wing2_y)]
        pygame.draw.polygon(surface, GREEN, points)

    def _check_landing(self):
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)

        station_distance = self.station.get_distance(self.player.x, self.player.y)
        if station_distance < self.station.landing_distance and speed < 0.4:
            return "station"

        moon_distance = self.moon.get_distance(self.player.x, self.player.y)
        if moon_distance < self.moon.landing_distance and speed < 0.4:
            return "moon"

        return None

    def update_physics(self):
        """Update physics without camera - used when space is background"""
        self.player.update()
        self.station.update()
        self.moon.update()
        for ai_ship in self.ai_ships:
            ai_ship.update()

    def update(self):
        """Full update including camera - only called when space is active screen"""
        self.update_physics()

        # Update camera to follow player
        set_camera_offset(self.player.x - GAME_WIDTH // 2, self.player.y - GAME_HEIGHT // 2)

        # Auto-land if autopilot is active and in range
        if self.player.autopilot_active and self.player.autopilot_target:
            distance = self.player.autopilot_target.get_distance(self.player.x, self.player.y)
            speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
            landing_distance = self.player.autopilot_target.landing_distance
            if distance < landing_distance and speed < 0.4:
                self.player.autopilot_active = False
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
        self.station.draw(surface)
        self.moon.draw(surface)
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

            # Draw velocity info
            speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
            ui_scale = get_ui_scale()
            ui_offset_x, ui_offset_y = get_ui_offset()
            font_debug = pygame.font.Font(None, int(16 * ui_scale))
            velocity_text = font_debug.render(f"Velocity: {speed:.2f}", True, (100, 255, 100))
            surface.blit(velocity_text, (int(ui_offset_x + 10), int(ui_offset_y + 40)))

        # Draw target brackets and label
        target_obj = self._get_target_object()
        target_name = self._get_target_name()
        if target_obj and target_name:
            draw_target_brackets(surface, target_obj.x, target_obj.y)
            ui_scale = get_ui_scale()
            ui_offset_x, ui_offset_y = get_ui_offset()
            font_target = pygame.font.Font(None, int(20 * ui_scale))
            target_text = font_target.render(f"Target: {target_name}", True, GREEN)
            surface.blit(target_text, (int(ui_offset_x + 10), int(ui_offset_y + 10)))

            # Draw directional arrow pointing toward target
            self._draw_target_arrow(surface, target_obj)

            # Draw predicted landing trajectory (debug visualization)
            if self.player.autopilot_active:
                waypoints = self.player.predict_landing_trajectory(target_obj)
                if waypoints and len(waypoints) > 0:
                    draw_landing_trajectory(surface, waypoints)
                    final_x, final_y = waypoints[-1]
                    draw_landing_prediction(surface, final_x, final_y)

        if self.player.autopilot_active:
            ui_scale = get_ui_scale()
            font = pygame.font.Font(None, int(24 * ui_scale))
            autopilot_text = font.render("Autopilot engaged - press any key to cancel", True, CYAN)
            ui_offset_x, ui_offset_y = get_ui_offset()
            ap_x = int(ui_offset_x + utils.screen_width // 2 - autopilot_text.get_width() // 2)
            ap_y = int(ui_offset_y + utils.screen_height - 60)
            surface.blit(autopilot_text, (ap_x, ap_y))
        elif self.landing_text > 0:
            ui_scale = get_ui_scale()
            font = pygame.font.Font(None, int(24 * ui_scale))
            land_text = font.render("Press L to land", True, YELLOW)
            ui_offset_x, ui_offset_y = get_ui_offset()
            land_x = int(ui_offset_x + utils.screen_width // 2 - land_text.get_width() // 2)
            land_y = int(ui_offset_y + utils.screen_height - 60)
            surface.blit(land_text, (land_x, land_y))

        scale = get_scale()
        offset_x, offset_y = get_offset()
        border_rect = (int(offset_x), int(offset_y), int(GAME_WIDTH * scale), int(GAME_HEIGHT * scale))
        pygame.draw.rect(surface, (100, 100, 100), border_rect, 2)

        # Draw help text at bottom
        ui_scale = get_ui_scale()
        ui_offset_x, ui_offset_y = get_ui_offset()
        font_help = pygame.font.Font(None, int(16 * ui_scale))
        help_text = font_help.render("T: target, L: land, ESC: pause", True, WHITE)
        help_x = int(ui_offset_x + utils.screen_width // 2 - help_text.get_width() // 2)
        help_y = int(ui_offset_y + utils.screen_height - 30)
        surface.blit(help_text, (help_x, help_y))

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
