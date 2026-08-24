"""Configurable location for station, moon city, and moon wilderness."""
import pygame
import math
import constants
from constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from utils import get_scale, load_json, to_screen, draw_debug_marker, draw_target_brackets, get_ui_scale, get_ui_offset, set_camera_offset, get_building_type, get_culture
from screen_base import ScreenBase
from npc import NPC


class LocationScreen(ScreenBase):
    """Configurable location for station, moon city, and moon wilderness. Loads layout and NPCs from config."""
    def __init__(self, config_file=None, config_data=None, world_width=1600, world_height=1600, pilot_name="", story="default"):
        self.story = story  # which story's config/building_types.json etc. to resolve against
        # Load config from file or use inline data
        if config_data is not None:
            self.config = config_data
            self.config_file = None
        else:
            self.config_file = config_file
            self.config = load_json(config_file) or {}
        entrance_cfg = self.config.get("entrance", {})
        start_x = entrance_cfg.get("x", world_width // 2)
        start_y = entrance_cfg.get("y", world_height - 80)

        # Initialize ScreenBase
        super().__init__(pilot_name=pilot_name)

        # Initialize walkable area properties
        self.player_x = start_x
        self.player_y = start_y
        self.world_width = world_width
        self.world_height = world_height
        self.speed = 3
        self.entrance_x = start_x  # Where player enters
        self.entrance_y = start_y
        self.entrance_range = 50  # How close to entrance to exit

        # Get display properties
        self.ui_label = self.config.get("label", "Location")
        self.bg_color = tuple(self.config.get("background_color", [50, 50, 70]))

        # A "culture" on the interior itself (independent of any exterior asset lookup)
        # walls become the culture's wall_color and a smaller inset floor rect in
        # floor_color marks the walkable area, so the room reads distinctly from its
        # walls instead of one flat fill. Locations with no culture keep the old
        # flat-background behavior (movement bounded by the full world rect).
        self.culture_id = self.config.get("culture")
        self.floor_rect = None
        self.floor_color = None
        if self.culture_id:
            culture = get_culture(self.story, self.culture_id)
            self.bg_color = tuple(culture.get("wall_color", self.bg_color))
            self.floor_color = tuple(culture.get("floor_color", self.bg_color))
            margin = self.config.get("wall_margin", 60)
            self.floor_rect = (margin, margin, world_width - 2 * margin, world_height - 2 * margin)

        # Load structures (buildings, craters, rocks, etc.)
        self.structures = self.config.get("structures", [])
        self.npcs_config = self.config.get("npcs", [])
        self.npcs = [
            NPC(
                cfg.get("x", 0), cfg.get("y", 0),
                behavior=cfg.get("behavior", "wander"),
                name=cfg.get("name", "NPC"),
                greeting=cfg.get("greeting", "Hello!"),
                dialogue_options=cfg.get("dialogue_options")
            )
            for cfg in self.npcs_config
        ]
        self.current_npc_target = None  # For T key targeting
        self.active_dialogue = None  # Set to an NPC's Dialogue while talking

    def _cycle_npc_target(self):
        """Cycle through targetable NPCs."""
        if not self.npcs:
            return
        if self.current_npc_target is None:
            self.current_npc_target = 0
        else:
            self.current_npc_target = (self.current_npc_target + 1) % len(self.npcs)

    def _get_npc_target(self):
        """Get the currently targeted NPC, if any."""
        if self.current_npc_target is None or self.current_npc_target >= len(self.npcs):
            return None
        return self.npcs[self.current_npc_target]

    def update(self):
        """Update location - handle movement and camera."""
        if not self.active_dialogue:
            keys = pygame.key.get_pressed()
            self._handle_movement(keys)
        self.update_camera()

    def draw(self, surface):
        """Draw location from config."""
        surface.fill(self.bg_color)
        scale = get_scale()

        # Walkable floor - an inset rect in the culture's floor_color, so the room
        # reads as distinct from the surrounding wall_color fill
        if self.floor_rect is not None:
            fx, fy, fw, fh = self.floor_rect
            x1, y1 = to_screen(fx, fy)
            x2, y2 = to_screen(fx + fw, fy + fh)
            pygame.draw.rect(surface, self.floor_color, (x1, y1, x2 - x1, y2 - y1))

        # Draw structures from config
        for structure in self.structures:
            building_type_id = structure.get("building_type")
            if building_type_id:
                self._draw_culture_building(surface, structure, building_type_id, scale)
                continue

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

        # Draw NPCs
        for npc in self.npcs:
            npc.draw(surface)

        # Highlight and label the targeted NPC
        target_npc = self._get_npc_target()
        if target_npc:
            draw_target_brackets(surface, target_npc.x, target_npc.y, size=25)

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
        ui_scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()
        self.draw_ui_text(surface, self.ui_label, scale=ui_scale)
        if target_npc:
            font_target = pygame.font.Font(None, int(20 * ui_scale))
            target_text = font_target.render(f"Target: {target_npc.name}", True, (100, 255, 100))
            surface.blit(target_text, (int(offset_x + 20), int(offset_y + 45)))

        font_help = pygame.font.Font(None, int(16 * ui_scale))
        help_text = font_help.render("WASD: move, T: target NPC, Enter: talk, L: exit, ESC: pause", True, WHITE)
        help_x = int(offset_x + surface.get_width() // 2 - help_text.get_width() // 2)
        help_y = int(offset_y + surface.get_height() - 30)
        surface.blit(help_text, (help_x, help_y))

        # Draw active dialogue box on top of everything
        if self.active_dialogue:
            self.active_dialogue.draw(surface, ui_scale)

    def _draw_culture_building(self, surface, structure, building_type_id, scale):
        """Draw a building whose hull/window colors come from its type's culture -
        fully config-driven metal (hull) + glass (windows) material palette.

        `structure` supplies only position ("x"/"y"); shape, size, and window
        layout all come from the building_type. Anchor point varies by shape:
        "rect" uses top-left (matching the generic rect structures above),
        "circle" uses center, "polygon" is whatever the type's local_points
        were authored relative to (typically ground level).
        """
        building_type = get_building_type(self.story, building_type_id)
        metal_color = tuple(building_type.get("color", (150, 150, 150)))
        glass_color = tuple(building_type.get("window_color", (255, 255, 0)))
        anchor_x, anchor_y = structure["x"], structure["y"]
        shape = building_type.get("shape", "rect")

        if shape == "circle":
            radius = building_type.get("radius", 50)
            cx, cy = to_screen(anchor_x, anchor_y)
            pygame.draw.circle(surface, metal_color, (cx, cy), max(1, int(radius * scale)))
        elif shape == "polygon":
            local_points = building_type.get("local_points", [])
            screen_points = [to_screen(anchor_x + lx, anchor_y + ly) for lx, ly in local_points]
            if len(screen_points) >= 3:
                pygame.draw.polygon(surface, metal_color, screen_points)
        else:  # rect
            width = building_type.get("width", 100)
            height = building_type.get("height", 100)
            x1, y1 = to_screen(anchor_x, anchor_y)
            x2, y2 = to_screen(anchor_x + width, anchor_y + height)
            pygame.draw.rect(surface, metal_color, (x1, y1, x2 - x1, y2 - y1))

        window_shape = building_type.get("window_shape", "rect")
        window_size = building_type.get("window_size", 12)
        half = max(1, int(window_size * scale / 2))
        for wx, wy in building_type.get("windows", []):
            px, py = to_screen(anchor_x + wx, anchor_y + wy)
            if window_shape == "circle":
                pygame.draw.circle(surface, glass_color, (px, py), half)
            else:
                pygame.draw.rect(surface, glass_color, (px - half, py - half, half * 2, half * 2))

    def handle_input(self, events):
        """Override for area-specific input (dialogue, etc.)"""
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if self.active_dialogue:
                # While talking, input drives the dialogue box instead of movement
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.active_dialogue.selected_option = (self.active_dialogue.selected_option - 1) % len(self.active_dialogue.options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.active_dialogue.selected_option = (self.active_dialogue.selected_option + 1) % len(self.active_dialogue.options)
                elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.active_dialogue = None
                continue

            if event.key == pygame.K_l:
                # Only allow exit if near entrance
                dist_to_entrance = math.sqrt((self.player_x - self.entrance_x) ** 2 + (self.player_y - self.entrance_y) ** 2)
                if dist_to_entrance <= self.entrance_range:
                    return "exit"
            elif event.key == pygame.K_t:
                self._cycle_npc_target()
            elif event.key == pygame.K_RETURN:
                target_npc = self._get_npc_target()
                if target_npc:
                    target_npc.dialogue.selected_option = 0
                    self.active_dialogue = target_npc.dialogue
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
        elif self.floor_rect is not None:
            fx, fy, fw, fh = self.floor_rect
            can_move = (fx < new_x < fx + fw and fy < new_y < fy + fh)
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

    def get_state(self):
        """Save player position state for locations"""
        return {
            "player": {
                "x": self.player_x,
                "y": self.player_y
            }
        }

    def restore_state(self, state):
        """Restore player position state for locations"""
        if not state or "player" not in state:
            return
        player_state = state["player"]
        self.player_x = player_state.get("x", self.player_x)
        self.player_y = player_state.get("y", self.player_y)
