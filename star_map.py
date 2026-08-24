"""Galaxy-scale star map overlay: pan around, select a system to jump to."""
import pygame
from constants import WHITE, YELLOW, GREEN, GRAY
from utils import get_ui_scale, get_star_systems


class StarMap:
    """Overlay showing every known star system on a pannable galaxy map.

    Positions are in an abstract "star map space" (each system's
    star_map_position, from config/stories/*/space_system.json) - unrelated
    to in-system GAME_WIDTH/HEIGHT coordinates.
    """
    def __init__(self, current_story_id, selected_story_id=None):
        self.systems = get_star_systems()
        self.current_story_id = current_story_id
        self.selected_story_id = selected_story_id if selected_story_id in self.systems else current_story_id

        current = self.systems.get(current_story_id, {})
        current_pos = current.get("star_map_position", {"x": 0, "y": 0})
        # The star-map-space point currently centered on screen.
        self.pan_x = current_pos.get("x", 0)
        self.pan_y = current_pos.get("y", 0)

        self.dragging = False
        self.drag_start_mouse = (0, 0)
        self.drag_start_pan = (self.pan_x, self.pan_y)
        self._screen_positions = {}  # story_id -> (sx, sy), refreshed each draw()

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_m):
                    return "close"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = self._system_at(event.pos)
                if clicked:
                    self.selected_story_id = clicked
                else:
                    self.dragging = True
                    self.drag_start_mouse = event.pos
                    self.drag_start_pan = (self.pan_x, self.pan_y)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
            elif event.type == pygame.MOUSEMOTION and self.dragging:
                ui_scale = get_ui_scale()
                dx = (event.pos[0] - self.drag_start_mouse[0]) / ui_scale
                dy = (event.pos[1] - self.drag_start_mouse[1]) / ui_scale
                self.pan_x = self.drag_start_pan[0] - dx
                self.pan_y = self.drag_start_pan[1] - dy
        return None

    def _system_at(self, mouse_pos, radius=16):
        for story_id, (sx, sy) in self._screen_positions.items():
            if (mouse_pos[0] - sx) ** 2 + (mouse_pos[1] - sy) ** 2 <= radius ** 2:
                return story_id
        return None

    def draw(self, surface):
        surface.fill((8, 8, 20))
        ui_scale = get_ui_scale()
        center_x, center_y = surface.get_width() / 2, surface.get_height() / 2

        font_label = pygame.font.Font(None, int(20 * ui_scale))
        font_title = pygame.font.Font(None, int(32 * ui_scale))
        font_help = pygame.font.Font(None, int(16 * ui_scale))

        self._screen_positions = {}
        for story_id, sysdata in self.systems.items():
            pos = sysdata.get("star_map_position", {"x": 0, "y": 0})
            sx = int(center_x + (pos["x"] - self.pan_x) * ui_scale)
            sy = int(center_y + (pos["y"] - self.pan_y) * ui_scale)
            self._screen_positions[story_id] = (sx, sy)

            is_current = story_id == self.current_story_id
            is_selected = story_id == self.selected_story_id
            color = YELLOW if is_selected else (GREEN if is_current else WHITE)
            radius = int((9 if (is_current or is_selected) else 5) * ui_scale)

            pygame.draw.circle(surface, color, (sx, sy), max(1, radius))
            if is_current:
                # "You are here" ring
                pygame.draw.circle(surface, GREEN, (sx, sy), max(1, radius + int(9 * ui_scale)), 2)

            label = font_label.render(sysdata.get("name", story_id), True, color)
            surface.blit(label, (sx + int(14 * ui_scale), sy - label.get_height() // 2))

        title = font_title.render("Star Map", True, WHITE)
        surface.blit(title, (20, 20))

        help_text = font_help.render("Click a system to select, drag to pan, M/ESC to close", True, GRAY)
        surface.blit(help_text, (20, surface.get_height() - 30))
