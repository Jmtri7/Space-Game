"""Galaxy-scale star map overlay: pan around, select a system to jump to."""
import pygame
from game.constants import WHITE, YELLOW, GREEN, CYAN
from game.utils import get_ui_scale, get_star_systems
from game.ui.menu_base import MenuBase
from game.ui.ui_theme import draw_glass_panel

# Keyboard pan speed, in star-map-space units/frame (unrelated to ui_scale -
# see handle_input).
PAN_SPEED = 10


class StarMap(MenuBase):
    """Overlay showing every star system in the current story on a pannable
    galaxy map (systems only exist within one story - see space_screen.py).

    Positions are in an abstract "star map space" (each system's
    star_map_position, from config/stories/{story}/systems/*.json) - unrelated
    to in-system GAME_WIDTH/HEIGHT coordinates.
    """
    def __init__(self, story, current_system_id, selected_system_id=None):
        self.story = story
        self.systems = get_star_systems(story)
        self.current_system_id = current_system_id
        self.selected_system_id = selected_system_id if selected_system_id in self.systems else current_system_id

        current = self.systems.get(current_system_id, {})
        current_pos = current.get("star_map_position", {"x": 0, "y": 0})
        # The star-map-space point currently centered on screen.
        self.pan_x = current_pos.get("x", 0)
        self.pan_y = current_pos.get("y", 0)

        self.dragging = False
        self.drag_start_mouse = (0, 0)
        self.drag_start_pan = (self.pan_x, self.pan_y)
        self._screen_positions = {}  # system_id -> (sx, sy), refreshed each draw()
        self._hud_click_rects = []  # UI panel rects, refreshed each draw()
        self._controls_rect = None  # set by MenuBase.draw, read back next frame

    def help_items(self):
        return [
            ("Click", "Select System"),
            ("Drag", "Pan Map"),
            ("WASD/Arrows", "Scroll Map"),
            ("M/ESC", "Close Map"),
        ]

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_m):
                    return "close"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if any(rect.collidepoint(event.pos) for rect in self._hud_click_rects):
                    continue
                clicked = self._system_at(event.pos)
                if clicked:
                    self.selected_system_id = clicked
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

        # Keyboard scrolling - called every frame regardless of events (the
        # map has no update() of its own; main.py calls handle_input() once
        # per frame while the map is open), so held keys pan continuously.
        # Not scaled by ui_scale: pan_x/pan_y live in star-map space, not
        # screen pixels.
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.pan_x -= PAN_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.pan_x += PAN_SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.pan_y -= PAN_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.pan_y += PAN_SPEED
        return None

    def _system_at(self, mouse_pos, radius=16):
        for system_id, (sx, sy) in self._screen_positions.items():
            if (mouse_pos[0] - sx) ** 2 + (mouse_pos[1] - sy) ** 2 <= radius ** 2:
                return system_id
        return None

    def draw_content(self, surface):
        surface.fill((8, 8, 20))
        ui_scale = get_ui_scale()
        center_x, center_y = surface.get_width() / 2, surface.get_height() / 2

        font_label = pygame.font.Font(None, int(20 * ui_scale))
        font_title = pygame.font.Font(None, int(32 * ui_scale))
        font_tag = pygame.font.Font(None, int(16 * ui_scale))

        self._screen_positions = {}
        for system_id, sysdata in self.systems.items():
            pos = sysdata.get("star_map_position", {"x": 0, "y": 0})
            sx = int(center_x + (pos["x"] - self.pan_x) * ui_scale)
            sy = int(center_y + (pos["y"] - self.pan_y) * ui_scale)
            self._screen_positions[system_id] = (sx, sy)

            is_current = system_id == self.current_system_id
            is_selected = system_id == self.selected_system_id
            color = YELLOW if is_selected else (GREEN if is_current else WHITE)
            radius = int((9 if (is_current or is_selected) else 5) * ui_scale)

            pygame.draw.circle(surface, color, (sx, sy), max(1, radius))
            if is_current:
                # "You are here" ring
                pygame.draw.circle(surface, GREEN, (sx, sy), max(1, radius + int(9 * ui_scale)), 2)

            label = font_label.render(sysdata.get("name", system_id), True, color)
            label_x = sx + int(14 * ui_scale)
            surface.blit(label, (label_x, sy - label.get_height() // 2))
            if is_current:
                tag = font_tag.render("You are here", True, GREEN)
                surface.blit(tag, (label_x, sy - label.get_height() // 2 + label.get_height()))

        # Title sits top-centre so MenuBase.draw can own the top-left corner
        # with the shared Controls pane, like every other menu.
        title = font_title.render("Star Map", True, WHITE)
        surface.blit(title, (surface.get_width() // 2 - title.get_width() // 2, int(16 * ui_scale)))

        selected_rect = self._draw_selected_panel(surface, ui_scale, font_label)
        # self._controls_rect is set by MenuBase.draw (after this runs), so it
        # lags one frame here - fine, same cache-then-hit-test-next-frame idiom
        # as _screen_positions.
        self._hud_click_rects = [rect for rect in (self._controls_rect, selected_rect) if rect]

    def _draw_selected_panel(self, surface, ui_scale, font_label):
        """Top-right panel listing the selected system's station and moon,
        so a player deciding where to jump can see what's actually there."""
        selected = self.systems.get(self.selected_system_id)
        if not selected:
            return

        pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
        line_height = int(22 * ui_scale)
        lines = [
            (selected.get("name", self.selected_system_id), CYAN),
            (f"Station: {selected.get('station_name', 'Station')}", WHITE),
            (f"Moon: {selected.get('moon_name', 'Moon')}", WHITE),
        ]
        rendered = [font_label.render(text, True, color) for text, color in lines]
        panel_width = max(text.get_width() for text in rendered) + pad_x * 2
        panel_height = pad_y * 2 + line_height * len(rendered)
        margin = int(10 * ui_scale)
        panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
        panel_rect.topright = (surface.get_width() - margin, margin)
        draw_glass_panel(surface, panel_rect, ui_scale)
        for i, text in enumerate(rendered):
            surface.blit(text, (panel_rect.x + pad_x, panel_rect.y + pad_y + i * line_height))
        return panel_rect
