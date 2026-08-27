"""`BackdropMenu` - a top-level list screen over the animated `MenuBackdrop`:
a title, then a centred column of rows you arrow/click through, each row a
short label with an optional wrapped description line under it. Enter (or a
click) returns the focused row's value; ESC returns `"cancel"` when the menu
allows backing out.

Replaces the old `Menu` (main menu: NEW / LOAD / QUIT) and `StorySelector`
(pick a campaign, each with a blurb) - the same widget with and without the
per-row description.
"""
import math
import pygame
import game.utils as utils
from game.constants import WHITE, GRAY
from game.utils import get_font, _wrap_text
from game.ui.menu_base import MenuBase
from game.ui.menu_backdrop import MenuBackdrop
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_selection_highlight


class BackdropMenu(MenuBase):
    def __init__(self, title, rows, seed=None, allow_cancel=False):
        """`rows`: `[(value, label, description_or_None), ...]`."""
        self.title = title
        self.rows = list(rows)
        self.allow_cancel = allow_cancel
        self.selected_index = 0
        self.backdrop = MenuBackdrop(seed=seed) if seed is not None else MenuBackdrop()

    def help_items(self):
        items = [("Up/Down", "Navigate"), ("Enter", "Select"), ("Click", "Select")]
        if self.allow_cancel:
            items.append(("ESC", "Cancel"))
        return items

    # --- layout ---------------------------------------------------------
    def _layout(self):
        scale = min(utils.screen_width, utils.screen_height) / 600.0
        panel_width = int(560 * scale)
        panel_top = int(20 * scale)
        title_area = int(96 * scale)
        name_height = int(44 * scale)
        desc_line_height = int(22 * scale)
        row_padding = int(18 * scale)
        box_width = panel_width - int(40 * scale)

        font_desc = get_font(int(20 * scale))
        desc_lines = {}
        for value, _label, description in self.rows:
            desc_lines[value] = _wrap_text(font_desc, description, box_width - int(20 * scale)) if description else []
        row_heights = [name_height + len(desc_lines[v]) * desc_line_height + row_padding
                       for v, _l, _d in self.rows]

        panel_height = title_area + sum(row_heights) + int(20 * scale)
        panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
        panel_rect.centerx = utils.screen_width // 2
        panel_rect.top = panel_top
        return scale, panel_rect, title_area, row_heights, desc_lines, desc_line_height, name_height, box_width

    def _row_rects(self):
        scale, panel_rect, title_area, row_heights, _dl, _dlh, _nh, box_width = self._layout()
        rects = []
        row_top = panel_rect.top + title_area
        for h in row_heights:
            rect = pygame.Rect(0, row_top, box_width, h)
            rect.centerx = panel_rect.centerx
            rects.append(rect)
            row_top += h
        return rects

    # --- input --------------------------------------------------------
    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.selected_index = (self.selected_index - 1) % len(self.rows)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.selected_index = (self.selected_index + 1) % len(self.rows)
                elif event.key == pygame.K_RETURN:
                    return self.rows[self.selected_index][0]
                elif event.key == pygame.K_ESCAPE and self.allow_cancel:
                    return "cancel"
            elif event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(self._row_rects()):
                    if rect.collidepoint(event.pos):
                        self.selected_index = i
                        break
            elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
                for i, rect in enumerate(self._row_rects()):
                    if rect.collidepoint(event.pos):
                        self.selected_index = i
                        return self.rows[i][0]
        return None

    # --- rendering ----------------------------------------------------
    def draw_content(self, surface):
        self.backdrop.draw(surface)
        scale, panel_rect, title_area, row_heights, desc_lines, desc_line_height, name_height, box_width = self._layout()
        draw_glass_panel(surface, panel_rect, scale)
        draw_glow_title(surface, self.title, get_font(int(50 * scale)), panel_rect.centerx, panel_rect.top + int(18 * scale))

        font_menu = get_font(int(38 * scale))
        font_desc = get_font(int(20 * scale))
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)

        row_top = panel_rect.top + title_area
        for i, (value, label, _description) in enumerate(self.rows):
            row_height = row_heights[i]
            is_selected = i == self.selected_index
            row_rect = pygame.Rect(0, row_top, box_width, row_height)
            row_rect.centerx = panel_rect.centerx
            if is_selected:
                draw_selection_highlight(surface, row_rect, scale, pulse)

            text = font_menu.render(label, True, WHITE if is_selected else GRAY)
            surface.blit(text, text.get_rect(center=(panel_rect.centerx, row_top + name_height // 2)))

            desc_y = row_top + name_height + desc_line_height // 2
            for line in desc_lines[value]:
                desc_text = font_desc.render(line, True, GRAY)
                surface.blit(desc_text, desc_text.get_rect(center=(panel_rect.centerx, desc_y)))
                desc_y += desc_line_height

            row_top += row_height
