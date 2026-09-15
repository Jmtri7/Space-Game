"""Galaxy-scale star map overlay: drag to pan, click a system to select it.
Mouse-only."""
import pygame
from game.constants import (
    WHITE, YELLOW, GREEN, CYAN,
    STAR_MAP_WIDTH, STAR_MAP_HEIGHT,
    STAR_MAP_ZOOM, STAR_MAP_ZOOM_MIN, STAR_MAP_ZOOM_MAX, STAR_MAP_ZOOM_STEP,
)
from game.utils import get_ui_scale, get_star_systems, get_story, get_font, system_unlocked
from game.ui.menu_base import MenuBase
from game.ui.ui_theme import draw_glass_panel
from game.controls import Action, primary_label


class StarMap(MenuBase):
    """Overlay showing every star system in the current story on a pannable
    galaxy map (systems only exist within one story - see space_screen.py).

    Positions are in an abstract "star map space" (each system's
    star_map_position, from config/stories/{story}/systems/*.json) - unrelated
    to in-system GAME_WIDTH/HEIGHT coordinates.

    A system whose config sets "locked": true and whose "unlock_flag" isn't
    in `flags` (see utils.system_unlocked) is drawn dim with a "NO SIGNAL"
    tag and can't be picked as a jump target - the story's beacon
    progression. `flags` is the player's Possessions.flags.
    """
    def __init__(self, story, current_system_id, selected_system_id=None, flags=None):
        self.story = story
        self.systems = get_star_systems(story)
        self.flags = flags or {}
        self.current_system_id = current_system_id
        # A locked system (its beacon still dark - see utils.system_unlocked)
        # can't be selected as a jump target; fall back to the current system.
        self.selected_system_id = (
            selected_system_id
            if selected_system_id in self.systems and self._unlocked(selected_system_id)
            else current_system_id)

        current = self.systems.get(current_system_id, {})
        current_pos = current.get("star_map_position", {"x": 0, "y": 0})
        # The star-map-space point currently centered on screen.
        self.pan_x = current_pos.get("x", 0)
        self.pan_y = current_pos.get("y", 0)

        # Per-story map extent (story.json's "star_map": {"width", "height"})
        # - half-extents in star-map space. Panning is clamped to these so a
        # map edge can be dragged as far as screen center but no further.
        story_config = get_story(story).get("star_map", {})
        self.half_width = story_config.get("width", STAR_MAP_WIDTH) / 2
        self.half_height = story_config.get("height", STAR_MAP_HEIGHT) / 2
        self._clamp_pan()

        self.zoom = STAR_MAP_ZOOM

        self.dragging = False
        self.drag_start_mouse = (0, 0)
        self.drag_start_pan = (self.pan_x, self.pan_y)
        self._screen_positions = {}  # system_id -> (sx, sy), refreshed each draw()
        self._hud_click_rects = []  # UI panel rects, refreshed each draw()
        self.button_index = 0

    def _clamp_pan(self):
        self.pan_x = max(-self.half_width, min(self.half_width, self.pan_x))
        self.pan_y = max(-self.half_height, min(self.half_height, self.pan_y))

    def _unlocked(self, system_id):
        return system_unlocked(self.systems.get(system_id, {}), self.flags)

    def buttons(self):
        return [("close", "Close Map", (235, 235, 240), False)]

    def panel_rect(self, scale):
        import game.utils as _u
        return pygame.Rect(0, 0, _u.screen_width, _u.screen_height)

    def button_bar_rects(self, scale):
        m = int(14 * scale)
        return [pygame.Rect(m, m, int(150 * scale), int(38 * scale))]

    def handle_input(self, events):
        for event in events:
            if self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale())) == "close":
                return "close"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
                scale = get_ui_scale() * self.zoom
                dx = (event.pos[0] - self.drag_start_mouse[0]) / scale
                dy = (event.pos[1] - self.drag_start_mouse[1]) / scale
                self.pan_x = self.drag_start_pan[0] - dx
                self.pan_y = self.drag_start_pan[1] - dy
                self._clamp_pan()
            elif event.type == pygame.MOUSEWHEEL:
                self._zoom_at(pygame.mouse.get_pos(), event.y)
        return None

    def _zoom_at(self, mouse_pos, notches):
        """Zoom in/out (wheel up = in), keeping the world point under the
        cursor fixed on screen so zooming feels anchored to the pointer."""
        if notches == 0:
            return
        import game.utils as _u
        ui_scale = get_ui_scale()
        center_x, center_y = _u.screen_width / 2, _u.screen_height / 2
        old_scale = ui_scale * self.zoom
        world_x = self.pan_x + (mouse_pos[0] - center_x) / old_scale
        world_y = self.pan_y + (mouse_pos[1] - center_y) / old_scale

        factor = STAR_MAP_ZOOM_STEP ** notches
        self.zoom = max(STAR_MAP_ZOOM_MIN, min(STAR_MAP_ZOOM_MAX, self.zoom * factor))

        new_scale = ui_scale * self.zoom
        self.pan_x = world_x - (mouse_pos[0] - center_x) / new_scale
        self.pan_y = world_y - (mouse_pos[1] - center_y) / new_scale
        self._clamp_pan()

    def _system_at(self, mouse_pos, radius=16):
        for system_id, (sx, sy) in self._screen_positions.items():
            if (mouse_pos[0] - sx) ** 2 + (mouse_pos[1] - sy) ** 2 <= radius ** 2:
                # A locked system can't be picked as a jump target - clicking
                # it just does nothing (it reads "NO SIGNAL" on the map).
                return system_id if self._unlocked(system_id) else None
        return None

    def draw_content(self, surface):
        surface.fill((8, 8, 20))
        ui_scale = get_ui_scale()
        map_scale = ui_scale * self.zoom
        center_x, center_y = surface.get_width() / 2, surface.get_height() / 2

        font_label = get_font(int(20 * ui_scale))
        font_title = get_font(int(32 * ui_scale))
        font_tag = get_font(int(16 * ui_scale))

        border_left = int(center_x + (-self.half_width - self.pan_x) * map_scale)
        border_top = int(center_y + (-self.half_height - self.pan_y) * map_scale)
        border_rect = pygame.Rect(
            border_left, border_top,
            int(self.half_width * 2 * map_scale), int(self.half_height * 2 * map_scale))
        pygame.draw.rect(surface, (60, 60, 90), border_rect, max(1, int(2 * ui_scale)))

        self._screen_positions = {}
        for system_id, sysdata in self.systems.items():
            pos = sysdata.get("star_map_position", {"x": 0, "y": 0})
            sx = int(center_x + (pos["x"] - self.pan_x) * map_scale)
            sy = int(center_y + (pos["y"] - self.pan_y) * map_scale)
            self._screen_positions[system_id] = (sx, sy)

            is_current = system_id == self.current_system_id
            is_selected = system_id == self.selected_system_id
            is_locked = not self._unlocked(system_id)
            if is_locked:
                color = (95, 95, 110)
            else:
                color = YELLOW if is_selected else (GREEN if is_current else WHITE)
            radius = int((9 if (is_current or is_selected) else 5) * ui_scale)

            pygame.draw.circle(surface, color, (sx, sy), max(1, radius))
            if is_current:
                # "You are here" ring
                pygame.draw.circle(surface, GREEN, (sx, sy), max(1, radius + int(9 * ui_scale)), 2)

            label = font_label.render(sysdata.get("name", system_id), True, color)
            label_x = sx + int(14 * ui_scale)
            surface.blit(label, (label_x, sy - label.get_height() // 2))
            tag_y = sy - label.get_height() // 2 + label.get_height()
            if is_current:
                tag = font_tag.render("You are here", True, GREEN)
                surface.blit(tag, (label_x, tag_y))
                tag_y += tag.get_height()
            elif is_locked:
                tag = font_tag.render("NO SIGNAL", True, (150, 120, 120))
                surface.blit(tag, (label_x, tag_y))
                tag_y += tag.get_height()
            # Static map flavor (systems/*.json's "hazard": "pirates") - not
            # tied to whether a pirate_ambush event actually rolled there
            # this visit, see get_star_systems - so it still shows even once
            # this session's encounter (if any) has been resolved.
            if not is_locked and sysdata.get("hazard") == "pirates":
                tag = font_tag.render("PIRATE ACTIVITY", True, (235, 100, 90))
                surface.blit(tag, (label_x, tag_y))

        # Title top-centre (the top-left corner holds the Close button).
        title = font_title.render("Star Map", True, WHITE)
        surface.blit(title, (surface.get_width() // 2 - title.get_width() // 2, int(16 * ui_scale)))

        selected_rect = self._draw_selected_panel(surface, ui_scale, font_label)
        close_rect = self.button_bar_rects(ui_scale)[0]
        self._hud_click_rects = [rect for rect in (close_rect, selected_rect) if rect]

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
        if self.selected_system_id != self.current_system_id:
            lines.append((f"Press {primary_label(Action.JUMP)} to jump", YELLOW))
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
