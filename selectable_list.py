"""A scrollable, keyboard-navigable list of selectable items with the
game's standard highlight styling. Used by LoadMenu, SaveDialog's
overwrite list, and LocationSelector so each doesn't hand-roll its own
scroll/highlight logic (see docs/DESIGN_PATTERNS.md)."""
import math
import pygame
from constants import YELLOW, GRAY
from utils import _handle_scrolling_input
from ui_theme import draw_selection_highlight


class SelectableList:
    """Owns selection/scroll state for a list of items and draws them
    centered under a given point, one per line, with a pulsing highlight
    on the selected item and up/down "more" indicators when scrolled."""
    def __init__(self, items, max_visible=5):
        self.items = items
        self.max_visible = max_visible
        self.selected = 0
        self.scroll_offset = 0

    def handle_key(self, key):
        """Update selection/scroll for an UP/DOWN/W/S keypress."""
        self.selected, self.scroll_offset = _handle_scrolling_input(
            key, self.selected, self.items, self.scroll_offset, self.max_visible)

    def current(self):
        """The currently selected item, or None if the list is empty."""
        return self.items[self.selected] if self.items else None

    def draw(self, surface, font, center_x, start_y, line_height, scale, label_fn=str):
        if not self.items:
            return

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)

        if self.scroll_offset > 0:
            up_indicator = font.render("↑ more", True, GRAY)
            surface.blit(up_indicator, (center_x - up_indicator.get_width() // 2, int(start_y - line_height)))

        visible = self.items[self.scroll_offset:self.scroll_offset + self.max_visible]
        for i, item in enumerate(visible):
            is_selected = (self.scroll_offset + i == self.selected)
            color = YELLOW if is_selected else GRAY
            text = font.render(label_fn(item), True, color)
            text_x = center_x - text.get_width() // 2
            text_y = int(start_y + i * line_height)
            if is_selected:
                box_rect = pygame.Rect(text_x - 10, text_y - 4, text.get_width() + 20, text.get_height() + 8)
                draw_selection_highlight(surface, box_rect, scale, pulse)
            surface.blit(text, (text_x, text_y))

        if self.scroll_offset + self.max_visible < len(self.items):
            down_indicator = font.render("↓ more", True, GRAY)
            down_y = int(start_y + self.max_visible * line_height)
            surface.blit(down_indicator, (center_x - down_indicator.get_width() // 2, down_y))
