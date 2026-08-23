"""Configurable location for station, moon city, and moon wilderness."""
import pygame
import constants
from constants import GAME_WIDTH, GAME_HEIGHT
from utils import get_scale, load_json, to_screen, draw_debug_marker
from walkable_area import WalkableArea


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
