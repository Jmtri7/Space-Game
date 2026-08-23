"""Screen classes for game state management and UI rendering."""
import pygame
import math
import random
import os
from datetime import datetime
import constants
from constants import (
    GAME_WIDTH, GAME_HEIGHT, YELLOW, WHITE, GRAY, BLACK, CYAN, GREEN
)
import utils
from utils import (
    get_scale, get_offset, get_ui_scale, get_ui_offset, to_screen, to_screen_x, to_screen_y,
    load_json, delete_save_file, get_save_files, create_save_file, load_save_file,
    draw_debug_marker, draw_target_brackets, draw_landing_prediction, draw_landing_trajectory, _center_text_x, _handle_scrolling_input,
    set_camera_offset, get_ship_type, get_graphics_asset,
    get_font, get_centered_x, get_centered_y, render_help_text, handle_menu_navigation, draw_dialog_box
)
from player_controller import PlayerController
from ai_ship import AIShip
from objects import SpaceStation, NPC, Dialogue, StarField, Moon


class ScreenBase:
    """Base class for all game screens (space, station, moon)"""
    def __init__(self, pilot_name=""):
        self.pilot_name = pilot_name

    def handle_input(self, events):
        """Process input events. Override in subclass."""
        raise NotImplementedError

    def update(self):
        """Update game logic. Override in subclass."""
        raise NotImplementedError

    def draw(self, surface):
        """Draw screen. Override in subclass."""
        raise NotImplementedError

    def get_state(self):
        """Return game state dict for saving. Override in subclass."""
        raise NotImplementedError

    def restore_state(self, state):
        """Restore game state from dict. Override in subclass."""
        raise NotImplementedError


class WalkableArea(ScreenBase):
    """Base class for all walkable/explorable areas with camera system"""
    def __init__(self, start_x=GAME_WIDTH // 2, start_y=GAME_HEIGHT // 2, world_width=1600, world_height=1600, pilot_name=""):
        super().__init__(pilot_name=pilot_name)
        self.player_x = start_x
        self.player_y = start_y
        self.world_width = world_width
        self.world_height = world_height
        self.speed = 3
        self.entrance_x = start_x  # Where player enters
        self.entrance_y = start_y
        self.entrance_range = 50  # How close to entrance to exit

    def handle_input(self, events):
        """Override for area-specific input (dialogue, etc.)"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_l:
                    # Only allow exit if near entrance
                    dist_to_entrance = math.sqrt((self.player_x - self.entrance_x) ** 2 + (self.player_y - self.entrance_y) ** 2)
                    if dist_to_entrance <= self.entrance_range:
                        return "exit"
                elif event.key == pygame.K_ESCAPE:
                    return "pause"
        return None

    def _handle_movement(self, keys, can_move_func=None):
        """Generalized movement input handling"""
        new_x = self.player_x
        new_y = self.player_y

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_y += self.speed
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            new_x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            new_x += self.speed

        # Check bounds
        if can_move_func:
            can_move = can_move_func(new_x, new_y)
        else:
            can_move = (0 < new_x < self.world_width and 0 < new_y < self.world_height)

        if can_move:
            self.player_x = new_x
            self.player_y = new_y

    def update_camera(self):
        """Update global camera to follow player"""
        set_camera_offset(self.player_x - GAME_WIDTH // 2, self.player_y - GAME_HEIGHT // 2)

    def draw_ui_text(self, surface, text, scale=None):
        """Draw UI text that stays on screen (not camera-affected)"""
        if scale is None:
            scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()
        font = pygame.font.Font(None, int(24 * scale))
        ui_text = font.render(text, True, WHITE)
        surface.blit(ui_text, (int(offset_x + 20), int(offset_y + 20)))

    def update(self):
        """Override in subclass"""
        pass

    def draw(self, surface):
        """Override in subclass"""
        pass

    def get_state(self):
        """Save player position state for walkable areas"""
        return {
            "player": {
                "x": self.player_x,
                "y": self.player_y
            }
        }

    def restore_state(self, state):
        """Restore player position state for walkable areas"""
        if not state or "player" not in state:
            return
        player_state = state["player"]
        self.player_x = player_state.get("x", self.player_x)
        self.player_y = player_state.get("y", self.player_y)


class Location(WalkableArea):
    """Configurable location for station, moon city, and moon wilderness. Loads layout and NPCs from config."""
    def __init__(self, config_file, world_width=1600, world_height=1600, pilot_name=""):
        # Load config
        self.config = load_json(config_file) or {}
        entrance_cfg = self.config.get("entrance", {})
        start_x = entrance_cfg.get("x", world_width // 2)
        start_y = entrance_cfg.get("y", world_height - 80)

        super().__init__(start_x=start_x, start_y=start_y, world_width=world_width, world_height=world_height, pilot_name=pilot_name)

        # Set entrance
        self.entrance_x = start_x
        self.entrance_y = start_y
        self.player_x = self.entrance_x
        self.player_y = self.entrance_y

        # Get display properties
        self.ui_label = self.config.get("label", "Location")
        self.bg_color = tuple(self.config.get("background_color", [50, 50, 70]))

        # Load structures (buildings, craters, rocks, etc.)
        self.structures = self.config.get("structures", [])
        self.npcs_config = self.config.get("npcs", [])

    def update(self):
        """Update location - handle movement and camera."""
        keys = pygame.key.get_pressed()
        self._handle_movement(keys)
        self.update_camera()

    def draw(self, surface):
        """Draw location from config."""
        surface.fill(self.bg_color)
        scale = get_scale()

        # Draw structures from config
        for structure in self.structures:
            struct_type = structure.get("type", "rect")
            color = tuple(structure.get("color", [150, 150, 150]))

            if struct_type == "rect":
                x, y, w, h = structure["x"], structure["y"], structure["width"], structure["height"]
                x1, y1 = to_screen(x, y)
                x2, y2 = to_screen(x + w, y + h)
                pygame.draw.rect(surface, color, (x1, y1, x2 - x1, y2 - y1))

            elif struct_type == "circle":
                x, y, r = structure["x"], structure["y"], structure.get("radius", 50)
                cx, cy = to_screen(x, y)
                pygame.draw.circle(surface, color, (cx, cy), max(1, int(r * scale)))

            elif struct_type == "polygon":
                points = [(p["x"], p["y"]) for p in structure["points"]]
                screen_points = [to_screen(x, y) for x, y in points]
                pygame.draw.polygon(surface, color, screen_points)

        # Draw windows/details from config
        for detail in self.config.get("details", []):
            detail_type = detail.get("type", "window")
            color = tuple(detail.get("color", [255, 255, 0]))

            if detail_type == "window":
                sx, sy, ex, ey, spacing = detail["start_x"], detail["start_y"], detail["end_x"], detail["end_y"], detail.get("spacing", 50)
                for x in range(sx, ex, spacing):
                    for y in range(sy, ey, spacing):
                        px, py = to_screen(x, y)
                        pygame.draw.rect(surface, color, (px, py, 15, 15))

        # Draw entrance marker
        ex, ey = to_screen(self.entrance_x, self.entrance_y)
        pygame.draw.circle(surface, (0, 255, 100), (ex, ey), max(1, int(15 * scale)))
        pygame.draw.circle(surface, (100, 255, 150), (ex, ey), max(1, int(10 * scale)))

        # Draw player
        px, py = to_screen(self.player_x, self.player_y)
        pygame.draw.rect(surface, (200, 100, 100), (px - 6, py, 12, 16))
        pygame.draw.circle(surface, (255, 150, 150), (px, py - 10), 5)

        # Debug marker
        if constants.DEBUG_MODE:
            draw_debug_marker(surface, self.player_x, self.player_y, 10)

        # Draw UI
        self.draw_ui_text(surface, self.ui_label)


class StationInterior(Location):
    """Interior of a space station with NPCs and dialogue. Loads from config/station_interior.json."""
    def __init__(self, station_config=None, pilot_name=""):
        # Load config from story directory
        config_file = "config/stories/default/station_interior.json"
        self.station_config = station_config or load_json(config_file) or {}

        super().__init__(config_file=config_file, world_width=GAME_WIDTH, world_height=GAME_HEIGHT, pilot_name=pilot_name)

        self.room_width = GAME_WIDTH
        self.room_height = GAME_HEIGHT

        hallway_cfg = self.station_config.get("hallway", {})
        self.hallway_narrow_width = hallway_cfg.get("narrow_width", 80)
        self.hallway_wide_width = hallway_cfg.get("wide_width", 200)
        self.hallway_x = GAME_WIDTH // 2 - self.hallway_narrow_width // 2
        self.hallway_transition_y = int(GAME_HEIGHT * hallway_cfg.get("transition_y", 0.5))

        bar_cfg = self.station_config.get("bar", {})
        self.bar_x = int(GAME_WIDTH * bar_cfg.get("x", 0.5))
        self.bar_y = int(GAME_HEIGHT * bar_cfg.get("y", 0.15))

        door_cfg = self.station_config.get("door", {})
        self.door_x = int(GAME_WIDTH * door_cfg.get("x", 0.5))
        self.door_y = int(GAME_HEIGHT * door_cfg.get("y", 0.9))

        npcs_cfg = self.station_config.get("npcs", [])
        npc0 = npcs_cfg[0] if len(npcs_cfg) > 0 else {}
        npc1 = npcs_cfg[1] if len(npcs_cfg) > 1 else {}
        npc2 = npcs_cfg[2] if len(npcs_cfg) > 2 else {}

        # Load entrance from config
        entrance_cfg = self.station_config.get("entrance", {})
        self.entrance_x = int(GAME_WIDTH * entrance_cfg.get("x", 0.5))
        self.entrance_y = int(GAME_HEIGHT * entrance_cfg.get("y", 0.85))
        self.player_x = self.entrance_x
        self.player_y = self.entrance_y

        self.bartender = NPC(self.bar_x, self.bar_y, "bar", npc0.get("name", "Bartender"), npc0.get("greeting", "What'll it be?"), npc0.get("dialogue_options", ["Talk", "Leave"]))
        self.wanderer = NPC(self.room_width // 2, self.hallway_transition_y - 100, "wander", npc1.get("name", "Traveler"), npc1.get("greeting", "Safe travels!"), npc1.get("dialogue_options", ["Thanks", "Leave"]))
        self.door_guard = NPC(self.door_x, self.door_y, "bar", npc2.get("name", "Guard"), npc2.get("greeting", "Welcome to the station."), npc2.get("dialogue_options", ["Thanks", "Leave"]))

        self.npcs = [
            (self.bartender.name, self.bartender),
            (self.wanderer.name, self.wanderer),
            (self.door_guard.name, self.door_guard),
        ]

        self.current_dialogue = None
        self.nearby_npc = None
        self.current_target = None  # For T key targeting

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.current_dialogue:
                        self.current_dialogue = None
                    else:
                        return "pause"
                elif event.key == pygame.K_l:
                    # Only allow exit if near entrance
                    dist_to_entrance = math.sqrt((self.player_x - self.entrance_x) ** 2 + (self.player_y - self.entrance_y) ** 2)
                    if dist_to_entrance <= self.entrance_range:
                        return "exit"
                elif event.key == pygame.K_t:
                    self._cycle_target()
                elif event.key == pygame.K_RETURN:
                    if self.current_target is not None:
                        self.current_dialogue = self.npcs[self.current_target][1].dialogue
                    elif self.nearby_npc and not self.current_dialogue:
                        self.current_dialogue = self.nearby_npc.dialogue
                    elif self.current_dialogue:
                        self.current_dialogue = None
                elif self.current_dialogue:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.current_dialogue.selected_option = (self.current_dialogue.selected_option - 1) % len(self.current_dialogue.options)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.current_dialogue.selected_option = (self.current_dialogue.selected_option + 1) % len(self.current_dialogue.options)
                    elif event.key == pygame.K_RETURN:
                        self.current_dialogue = None
            elif event.type == pygame.MOUSEBUTTONDOWN and self.current_dialogue:
                self._handle_dialogue_click(pygame.mouse.get_pos())
        return None

    def _cycle_target(self):
        """Cycle through targetable NPCs"""
        if not self.npcs:
            return
        if self.current_target is None:
            self.current_target = 0
        else:
            self.current_target = (self.current_target + 1) % len(self.npcs)

    def _get_target_npc(self):
        """Get the currently targeted NPC"""
        if self.current_target is None or self.current_target >= len(self.npcs):
            return None
        return self.npcs[self.current_target][1]

    def _handle_dialogue_click(self, mouse_pos):
        scale = get_ui_scale()
        screen_w = pygame.display.get_surface().get_width()
        screen_h = pygame.display.get_surface().get_height()
        box_width = int(400 * scale)
        box_height = int(250 * scale)
        box_x = screen_w // 2 - box_width // 2
        box_y = screen_h // 2 - box_height // 2

        for i in range(len(self.current_dialogue.options)):
            option_y = box_y + 100 + i * int(30 * scale)
            if (mouse_pos[1] > option_y and mouse_pos[1] < option_y + int(25 * scale)):
                self.current_dialogue = None
                return

    def _is_in_hallway(self, x, y):
        if y > self.hallway_transition_y:
            return (x >= self.hallway_x + 10 and x <= self.hallway_x + self.hallway_narrow_width - 10 and y <= self.room_height - 30)
        else:
            hallway_wide_x = GAME_WIDTH // 2 - self.hallway_wide_width // 2
            return (x >= hallway_wide_x + 10 and x <= hallway_wide_x + self.hallway_wide_width - 10 and y >= 30)

    def _is_in_valid_area(self, x, y):
        if self._is_in_hallway(x, y):
            return True
        bar_left = self.bar_x - 100
        bar_right = self.bar_x + 100
        bar_top = 50
        bar_bottom = self.hallway_transition_y - 50
        return (x >= bar_left and x <= bar_right and y >= bar_top and y <= bar_bottom)

    def update(self):
        if self.current_dialogue:
            return

        keys = pygame.key.get_pressed()
        self._handle_movement(keys, self._is_in_valid_area)
        self.player_y = max(30, min(self.room_height - 30, self.player_y))
        self.update_camera()

        self.wanderer.wander_time -= 1
        if self.wanderer.wander_time <= 0:
            self.wanderer.wander_x = (random.random() - 0.5) * 2
            self.wanderer.wander_y = (random.random() - 0.5) * 2
            self.wanderer.wander_time = random.randint(60, 180)

        new_wander_x = self.wanderer.x + self.wanderer.wander_x
        new_wander_y = self.wanderer.y + self.wanderer.wander_y

        if self._is_in_valid_area(new_wander_x, new_wander_y):
            self.wanderer.x = new_wander_x
            self.wanderer.y = new_wander_y

        self.nearby_npc = None
        for npc in [self.bartender, self.wanderer, self.door_guard]:
            if npc.get_distance(self.player_x, self.player_y) < 50:
                self.nearby_npc = npc
                break

    def draw(self, surface):
        surface.fill((30, 30, 50))

        scale = get_scale()
        hallway_wide_x = GAME_WIDTH // 2 - self.hallway_wide_width // 2
        hallway_wide_width = self.hallway_wide_width

        pygame.draw.rect(surface, (50, 50, 70), (*to_screen(hallway_wide_x, 0), to_screen_x(hallway_wide_width), to_screen_y(self.hallway_transition_y)))
        pygame.draw.rect(surface, (50, 50, 70), (*to_screen(self.hallway_x, self.hallway_transition_y), to_screen_x(self.hallway_narrow_width), to_screen_y(self.room_height - self.hallway_transition_y)))

        pygame.draw.rect(surface, (60, 60, 80), (*to_screen(0, 0), to_screen_x(self.room_width), to_screen_y(self.room_height)), 3)

        pygame.draw.line(surface, (80, 80, 100), to_screen(hallway_wide_x, 0), to_screen(self.hallway_x, self.hallway_transition_y), 2)
        pygame.draw.line(surface, (80, 80, 100), to_screen(hallway_wide_x + hallway_wide_width, 0), to_screen(self.hallway_x + self.hallway_narrow_width, self.hallway_transition_y), 2)

        pygame.draw.rect(surface, (100, 80, 40), (*to_screen(self.bar_x - 60, self.bar_y - 20), to_screen_x(120), to_screen_y(40)))
        font = pygame.font.Font(None, int(20 * scale))
        bar_text = font.render("BAR", True, (200, 200, 100))
        surface.blit(bar_text, to_screen(self.bar_x - 20, self.bar_y - 10))

        self.bartender.draw(surface)
        self.wanderer.draw(surface)
        self.door_guard.draw(surface)

        pygame.draw.rect(surface, (0, 255, 0), (*to_screen(self.player_x - 6, self.player_y), to_screen_x(12), to_screen_y(16)))
        pygame.draw.circle(surface, (100, 255, 100), to_screen(self.player_x, self.player_y - 10), max(1, int(5 * scale)))

        # Debug marker for player position
        if constants.DEBUG_MODE:
            draw_debug_marker(surface, self.player_x, self.player_y, 10)
            draw_debug_marker(surface, self.bartender.x, self.bartender.y, 8)
            draw_debug_marker(surface, self.wanderer.x, self.wanderer.y, 8)
            draw_debug_marker(surface, self.door_guard.x, self.door_guard.y, 8)

        # Draw target brackets and label
        target_npc = self._get_target_npc()
        if target_npc:
            draw_target_brackets(surface, target_npc.x, target_npc.y)
            offset_x, offset_y = get_offset()
            font_target = pygame.font.Font(None, int(16 * scale))
            target_text = font_target.render(f"Target: {target_npc.name}", True, GREEN)
            surface.blit(target_text, (int(offset_x + 10), int(offset_y + 30)))

        offset_x, offset_y = get_offset()
        font_small = pygame.font.Font(None, int(16 * scale))
        help_text = font_small.render("WASD/Arrows to move, T to target, Enter to talk, L to exit, ESC for menu", True, (200, 200, 200))
        surface.blit(help_text, (int(offset_x + 10), int(offset_y + 10)))

        if self.nearby_npc and not self.current_dialogue:
            talk_text = font_small.render("Press T to talk", True, (255, 255, 0))
            surface.blit(talk_text, to_screen(self.nearby_npc.x - 30, self.nearby_npc.y - 30))

        if self.current_dialogue:
            self.current_dialogue.draw(surface, scale)

        offset_x, offset_y = get_offset()
        border_rect = (int(offset_x), int(offset_y), int(GAME_WIDTH * scale), int(GAME_HEIGHT * scale))
        pygame.draw.rect(surface, (100, 100, 100), border_rect, 2)


# Type aliases for Location instantiation - loads from story config
MoonCity = lambda pilot_name="": Location(config_file="config/stories/default/moon_city.json", world_width=1600, world_height=1600, pilot_name=pilot_name)
MoonOutdoor = lambda pilot_name="": Location(config_file="config/stories/default/moon_wilderness.json", world_width=1600, world_height=1600, pilot_name=pilot_name)


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
        self.station = SpaceStation(GAME_WIDTH * station_cfg.get("x", 0.75), GAME_HEIGHT * station_cfg.get("y", 0.3), graphics=station_graphics)

        moon_cfg = self.system_config.get("moon", {})
        moon_graphics = get_graphics_asset("moons", moon_asset_id)
        self.moon = Moon(GAME_WIDTH * moon_cfg.get("x", 0.2), GAME_HEIGHT * moon_cfg.get("y", 0.4), graphics=moon_graphics)

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
                        if distance < 150 and speed < 0.5:
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
        if station_distance < self.station.landing_distance and speed < 0.5:
            return "station"

        moon_distance = self.moon.get_distance(self.player.x, self.player.y)
        if moon_distance < self.moon.landing_distance and speed < 0.5:
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
            if distance < landing_distance and speed < 0.5:
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
                try:
                    waypoints = self.player.predict_landing_trajectory(target_obj)
                    if waypoints:
                        draw_landing_trajectory(surface, waypoints)
                        final_x, final_y = waypoints[-1]
                        draw_landing_prediction(surface, final_x, final_y)
                except Exception:
                    pass  # Silently skip trajectory if prediction fails

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


class SaveDialog:
    """Dialog for saving games with name input and overwrite selection."""
    def __init__(self, pilot_name=""):
        self.pilot_name = pilot_name
        # Pre-populate with default save name
        timestamp = datetime.now().strftime("%Y-%m-%d %H%M")
        self.save_name = f"{pilot_name} - {timestamp}" if pilot_name else timestamp
        self.success_timer = 0
        self.existing_saves = self._get_all_saves()
        self.selected_existing = 0 if self.existing_saves else None
        self.input_mode = not self.existing_saves
        self.scroll_offset = 0
        self.max_visible = 5

    def _get_all_saves(self):
        return get_save_files()

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.input_mode:
                    if event.key == pygame.K_RETURN and self.save_name:
                        self.success_timer = 120
                        return ("save", self.save_name)
                    elif event.key == pygame.K_BACKSPACE:
                        self.save_name = self.save_name[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        return ("cancel", None)
                else:
                    if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                        if self.selected_existing is not None:
                            self.selected_existing, self.scroll_offset = _handle_scrolling_input(
                                event.key, self.selected_existing, self.existing_saves,
                                self.scroll_offset, self.max_visible)
                    elif event.key == pygame.K_RETURN and self.selected_existing is not None:
                        return ("save", self.existing_saves[self.selected_existing])
                    elif event.key == pygame.K_d and self.selected_existing is not None:
                        return ("delete", self.existing_saves[self.selected_existing])
                    elif event.key == pygame.K_ESCAPE:
                        return ("cancel", None)
                    elif event.key == pygame.K_n:
                        self.input_mode = True
                        # Keep the pre-populated save name (don't clear it)
            elif event.type == pygame.TEXTINPUT:
                if self.input_mode and len(self.save_name) < 30:
                    self.save_name += event.text
        return (None, None)

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        if self.input_mode:
            draw_dialog_box(surface, offset_x + GAME_WIDTH * scale * 0.1, offset_y + GAME_HEIGHT * scale * 0.2, GAME_WIDTH * scale * 0.8, GAME_HEIGHT * scale * 0.6)
            font_title = get_font(int(32 * scale))
            font_text = get_font(int(24 * scale))

            title = font_title.render("Save Name:", True, WHITE)
            surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.25)))

            # Show full filename with save_ prefix and .json extension
            full_filename = f"save_{self.save_name}.json"
            input_box = font_text.render(full_filename, True, YELLOW)
            surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.4)))

            help_text = font_text.render("Enter to save, ESC to cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.6)))
        else:
            draw_dialog_box(surface, offset_x + GAME_WIDTH * scale * 0.1, offset_y + GAME_HEIGHT * scale * 0.15, GAME_WIDTH * scale * 0.8, GAME_HEIGHT * scale * 0.7)
            font_title = get_font(int(32 * scale))
            font_text = get_font(int(20 * scale))

            title = font_title.render("Select Save to Overwrite", True, YELLOW)
            surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.2)))

            if self.scroll_offset > 0:
                up_indicator = font_text.render("↑ more", True, GRAY)
                surface.blit(up_indicator, (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.33)))

            visible_saves = self.existing_saves[self.scroll_offset:self.scroll_offset + self.max_visible]
            for i, save in enumerate(visible_saves):
                is_selected = (self.scroll_offset + i == self.selected_existing)
                color = YELLOW if is_selected else GRAY
                text = font_text.render(save, True, color)
                text_x = int(offset_x + GAME_WIDTH * scale * 0.15)
                text_y = int(offset_y + GAME_HEIGHT * scale * 0.35 + i * 35)
                surface.blit(text, (text_x, text_y))
                if is_selected:
                    box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                    pygame.draw.rect(surface, YELLOW, box_rect, 2)

            if self.scroll_offset + self.max_visible < len(self.existing_saves):
                down_indicator = font_text.render("↓ more", True, GRAY)
                surface.blit(down_indicator, (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.35 + self.max_visible * 35)))

            help_text = font_text.render("Enter: overwrite, N: new save, D: delete, ESC: cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.75)))


class ConfirmDialog:
    """Generic yes/no confirmation dialog"""
    def __init__(self, title, message):
        self.title = title
        self.message = message

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    return "confirm"
                elif event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
                    return "cancel"
        return None

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.25), int(GAME_WIDTH * scale * 0.7), int(GAME_HEIGHT * scale * 0.5)))
        font_title = pygame.font.Font(None, int(32 * scale))
        font_text = pygame.font.Font(None, int(24 * scale))

        title = font_title.render(self.title, True, WHITE)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.3)))

        message_text = font_text.render(self.message, True, YELLOW)
        surface.blit(message_text, (_center_text_x(surface, message_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.45)))

        help_text = font_text.render("Y: Yes   N: No   ESC: Cancel", True, GRAY)
        surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.65)))


class DeleteConfirmDialog(ConfirmDialog):
    """Confirmation for deleting a save"""
    def __init__(self, save_filename):
        self.save_filename = save_filename
        super().__init__("Delete Save?", save_filename[:50])

    def handle_input(self, events):
        result = super().handle_input(events)
        if result == "confirm":
            return ("confirm", self.save_filename)
        elif result == "cancel":
            return ("cancel", None)
        return (None, None)


class OverwriteConfirmDialog(ConfirmDialog):
    """Confirmation for overwriting a save"""
    def __init__(self, save_filename):
        self.save_filename = save_filename
        super().__init__("Overwrite Save?", save_filename[:50])

    def handle_input(self, events):
        result = super().handle_input(events)
        if result == "confirm":
            return ("confirm", self.save_filename)
        elif result == "cancel":
            return ("cancel", None)
        return (None, None)


class LoadMenu:
    """Menu for loading saved games."""
    def __init__(self):
        self.saves = get_save_files()
        self.selected = 0
        self.scroll_offset = 0
        self.max_visible = 5

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                    self.selected, self.scroll_offset = _handle_scrolling_input(
                        event.key, self.selected, self.saves, self.scroll_offset, self.max_visible)
                elif event.key == pygame.K_RETURN and self.saves:
                    return ("load", self.saves[self.selected])
                elif event.key == pygame.K_d and self.saves:
                    return ("delete", self.saves[self.selected])
                elif event.key == pygame.K_ESCAPE:
                    return ("cancel", None)
        return (None, None)

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.1), int(offset_y + GAME_HEIGHT * scale * 0.2), int(GAME_WIDTH * scale * 0.8), int(GAME_HEIGHT * scale * 0.6)))

        font_title = pygame.font.Font(None, int(40 * scale))
        font_save = pygame.font.Font(None, int(24 * scale))

        title = font_title.render("Load Game", True, YELLOW)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.25)))

        if not self.saves:
            no_saves = font_save.render("No saves found", True, GRAY)
            surface.blit(no_saves, (_center_text_x(surface, no_saves, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.5)))
        else:
            if self.scroll_offset > 0:
                up_indicator = font_save.render("↑ more", True, GRAY)
                surface.blit(up_indicator, (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.33)))

            visible_saves = self.saves[self.scroll_offset:self.scroll_offset + self.max_visible]
            for i, save in enumerate(visible_saves):
                is_selected = (self.scroll_offset + i == self.selected)
                color = YELLOW if is_selected else GRAY
                text = font_save.render(save, True, color)
                text_x = int(offset_x + GAME_WIDTH * scale * 0.15)
                text_y = int(offset_y + GAME_HEIGHT * scale * 0.35 + i * 40)
                surface.blit(text, (text_x, text_y))
                if is_selected:
                    box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                    pygame.draw.rect(surface, YELLOW, box_rect, 2)

            if self.scroll_offset + self.max_visible < len(self.saves):
                down_indicator = font_save.render("↓ more", True, GRAY)
                surface.blit(down_indicator, (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.35 + self.max_visible * 40)))

            help_text = font_save.render("Enter: load, D: delete, ESC: cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.75)))


class PauseMenu:
    """Pause menu during gameplay."""
    def __init__(self):
        self.options = ["Resume", "Save Game", "Quit to Menu"]
        self.selected = 0
        self.success_timer = 0

    def update(self):
        if self.success_timer > 0:
            self.success_timer -= 1

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "resume"
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.selected = (self.selected - 1) % len(self.options)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.selected = (self.selected + 1) % len(self.options)
                elif event.key == pygame.K_RETURN:
                    if self.selected == 0:
                        return "resume"
                    elif self.selected == 1:
                        return "save"
                    elif self.selected == 2:
                        return "quit"
        return None

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (0, 0, 0), (0, 0, utils.screen_width, utils.screen_height))
        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.2), int(offset_y + GAME_HEIGHT * scale * 0.3), int(GAME_WIDTH * scale * 0.6), int(GAME_HEIGHT * scale * 0.4)))

        font_title = pygame.font.Font(None, int(48 * scale))
        font_option = pygame.font.Font(None, int(32 * scale))

        title = font_title.render("PAUSED", True, YELLOW)
        surface.blit(title, (int(offset_x + GAME_WIDTH * scale // 2 - title.get_width() // 2), int(offset_y + GAME_HEIGHT * scale * 0.35)))

        for i, option in enumerate(self.options):
            color = YELLOW if i == self.selected else GRAY
            text = font_option.render(option, True, color)
            text_x = int(offset_x + GAME_WIDTH * scale // 2 - text.get_width() // 2)
            text_y = int(offset_y + GAME_HEIGHT * scale * 0.5 + i * 50)
            surface.blit(text, (text_x, text_y))
            if i == self.selected:
                box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                pygame.draw.rect(surface, YELLOW, box_rect, 2)

        if self.success_timer > 0:
            font_success = pygame.font.Font(None, int(32 * scale))
            success_text = font_success.render("Saved!", True, (0, 255, 0))
            surface.blit(success_text, (int(offset_x + GAME_WIDTH * scale * 0.5 - success_text.get_width() // 2), int(offset_y + GAME_HEIGHT * scale * 0.15)))


class PilotNameDialog:
    """Dialog for entering pilot name when starting a new game."""
    def __init__(self):
        self.pilot_name = ""

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and self.pilot_name:
                    return self.pilot_name
                elif event.key == pygame.K_BACKSPACE:
                    self.pilot_name = self.pilot_name[:-1]
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
            elif event.type == pygame.TEXTINPUT:
                if len(self.pilot_name) < 30:
                    self.pilot_name += event.text
        return None

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.25), int(GAME_WIDTH * scale * 0.7), int(GAME_HEIGHT * scale * 0.5)))

        font_title = pygame.font.Font(None, int(40 * scale))
        font_text = pygame.font.Font(None, int(28 * scale))

        title = font_title.render("New Game", True, YELLOW)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.3)))

        prompt = font_text.render("Enter Pilot Name:", True, WHITE)
        surface.blit(prompt, (_center_text_x(surface, prompt, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.4)))

        input_box = font_text.render(self.pilot_name + "|", True, YELLOW)
        surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.5)))

        help_text = font_text.render("Enter to start, ESC to cancel", True, GRAY)
        surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.65)))


class LocationSelector:
    """Dialog for selecting moon landing location."""
    def __init__(self):
        self.locations = ["Moon City", "Wilderness"]
        self.selected = 0

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.selected = (self.selected - 1) % len(self.locations)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.selected = (self.selected + 1) % len(self.locations)
                elif event.key == pygame.K_RETURN:
                    return self.locations[self.selected]
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
        return None

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.25), int(GAME_WIDTH * scale * 0.7), int(GAME_HEIGHT * scale * 0.5)))

        font_title = pygame.font.Font(None, int(40 * scale))
        font_text = pygame.font.Font(None, int(28 * scale))

        title = font_title.render("Landing Location", True, YELLOW)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.3)))

        for i, location in enumerate(self.locations):
            color = YELLOW if i == self.selected else GRAY
            text = font_text.render(location, True, color)
            text_x = int(offset_x + GAME_WIDTH * scale * 0.3)
            text_y = int(offset_y + GAME_HEIGHT * scale * 0.45 + i * 40)
            surface.blit(text, (text_x, text_y))
            if i == self.selected:
                box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                pygame.draw.rect(surface, YELLOW, box_rect, 2)


class StorySelector:
    """Screen for selecting which story/campaign to play."""
    def __init__(self):
        # Scan for available stories
        stories_dir = "config/stories"
        self.stories = []
        if os.path.exists(stories_dir):
            for item in sorted(os.listdir(stories_dir)):
                item_path = os.path.join(stories_dir, item)
                if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "story.json")):
                    self.stories.append(item)

        self.selected_index = 0

    def handle_input(self, events):
        """Handle input and return selected story or 'cancel'."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Use menu navigation helper
                new_index = handle_menu_navigation(event, self.selected_index, len(self.stories))
                if new_index is not None:
                    self.selected_index = new_index
                elif event.key == pygame.K_RETURN:
                    return self.stories[self.selected_index]
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
        return None

    def draw(self, surface):
        """Draw story selection screen."""
        surface.fill(BLACK)
        scale = min(utils.screen_width, utils.screen_height) / 600.0

        # Title
        font_large = get_font(int(72 * scale))
        title = font_large.render("SELECT STORY", True, WHITE)
        title_rect = title.get_rect(center=(utils.screen_width // 2, int(100 * scale)))
        surface.blit(title, title_rect)

        # Story options
        font_menu = get_font(int(48 * scale))
        y_base = int(250 * scale)
        y_spacing = int(80 * scale)

        for i, story in enumerate(self.stories):
            color = YELLOW if i == self.selected_index else WHITE
            # Capitalize story name
            display_name = story.replace("_", " ").title()
            text = font_menu.render(display_name, True, color)
            text_x = get_centered_x(text.get_width())
            text_y = y_base + i * y_spacing
            surface.blit(text, (text_x, text_y))

            if i == self.selected_index:
                box_rect = pygame.Rect(text_x - 10, text_y - 5, text.get_width() + 20, text.get_height() + 10)
                pygame.draw.rect(surface, YELLOW, box_rect, 3)

        # Help text
        render_help_text(surface, "UP/DOWN: select, ENTER: play, ESC: cancel", utils.screen_height - int(50 * scale))


class Menu:
    """Main menu for game startup."""
    def __init__(self):
        self.items = ["NEW", "LOAD", "QUIT"]
        self.selected_index = 0

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                new_index = handle_menu_navigation(event, self.selected_index, len(self.items))
                if new_index is not None:
                    self.selected_index = new_index
                elif event.key == pygame.K_RETURN:
                    return self.items[self.selected_index].lower()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                return self._check_click(pygame.mouse.get_pos())
            elif event.type == pygame.MOUSEMOTION:
                self._update_selector_from_mouse(pygame.mouse.get_pos())
        return None

    def _update_selector_from_mouse(self, pos):
        for i in range(len(self.items)):
            rect = self._get_item_rect(i)
            if rect.collidepoint(pos):
                self.selected_index = i
                break

    def _check_click(self, pos):
        for i, item in enumerate(self.items):
            rect = self._get_item_rect(i)
            if rect.collidepoint(pos):
                self.selected_index = i
                return item.lower()
        return None

    def _get_item_rect(self, index):
        scale = min(utils.screen_width, utils.screen_height) / 600.0
        y_base = int(200 * scale)
        y_spacing = int(80 * scale)
        font_menu = get_font(int(48 * scale))
        text = font_menu.render(self.items[index], True, WHITE)
        rect = text.get_rect(center=(utils.screen_width // 2, y_base + index * y_spacing))
        return rect

    def draw(self, surface):
        surface.fill(BLACK)

        scale = min(utils.screen_width, utils.screen_height) / 600.0
        font_large = get_font(int(72 * scale))
        font_menu = get_font(int(48 * scale))

        title = font_large.render("MENU", True, WHITE)
        surface.blit(title, (get_centered_x(title.get_width()), int(50 * scale)))

        y_base = int(200 * scale)
        y_spacing = int(80 * scale)

        # Find max width of all menu items for padding
        max_width = max(font_menu.render(item, True, WHITE).get_width() for item in self.items)
        box_padding = int(20 * scale)
        box_width = max_width + box_padding * 2

        for i, item in enumerate(self.items):
            color = YELLOW if i == self.selected_index else GRAY
            text = font_menu.render(item, True, color)
            y = y_base + i * y_spacing
            text_x = get_centered_x(text.get_width())
            surface.blit(text, (text_x, y))

            if i == self.selected_index:
                box_x = utils.screen_width // 2 - box_width // 2
                box_top_padding = int(8 * scale)
                box_bottom_padding = int((y_spacing - text.get_height()) / 2)
                box_y = y - box_top_padding
                box_height = text.get_height() + box_top_padding + box_bottom_padding
                box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
                pygame.draw.rect(surface, YELLOW, box_rect, 2)
