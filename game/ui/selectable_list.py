"""A scrollable, keyboard-navigable list of selectable items with the
game's standard highlight styling. Used by LoadMenu, SaveDialog's
overwrite list, and LocationSelector so each doesn't hand-roll its own
scroll/highlight logic (see docs/DESIGN_PATTERNS.md)."""
import math
import pygame
from game.constants import YELLOW, GRAY
from game.utils import _handle_scrolling_input
from game.ui.ui_theme import draw_selection_highlight


class SelectableList:
    """Owns selection/scroll state for a list of items and draws them
    centered under a given point, one per line, with a pulsing highlight
    on the selected item and up/down "more" indicators when scrolled."""
    def __init__(self, items, max_visible=5):
        self.items = items
        self.max_visible = max_visible
        self.selected = 0
        self.scroll_offset = 0

    def handle_key(self, key, disabled_fn=None):
        """Update selection/scroll for an UP/DOWN/W/S keypress.

        disabled_fn(item) -> reason string or None. When given, the cursor
        skips over any item it reports as disabled - it should never be
        possible to navigate onto (and thus confirm) one, matching draw()'s
        dim/unselectable rendering. Capped at len(items) steps so a list
        that's entirely disabled can't spin forever."""
        self.selected, self.scroll_offset = _handle_scrolling_input(
            key, self.selected, self.items, self.scroll_offset, self.max_visible)
        if not disabled_fn:
            return
        steps = 0
        while self.items and disabled_fn(self.current()) and steps < len(self.items):
            self.selected, self.scroll_offset = _handle_scrolling_input(
                key, self.selected, self.items, self.scroll_offset, self.max_visible)
            steps += 1

    def current(self):
        """The currently selected item, or None if the list is empty."""
        return self.items[self.selected] if self.items else None

    def draw(self, surface, font, center_x, start_y, line_height, scale, label_fn=str, disabled_fn=None):
        """disabled_fn(item) -> reason string or None. A disabled item is
        drawn dim with its reason appended, never in the normal selected/
        unselected colors - used for options the player can't currently
        take (e.g. can't afford, already own one)."""
        if not self.items:
            return

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)

        if self.scroll_offset > 0:
            up_indicator = font.render("↑ more", True, GRAY)
            surface.blit(up_indicator, (center_x - up_indicator.get_width() // 2, int(start_y - line_height)))

        visible = self.items[self.scroll_offset:self.scroll_offset + self.max_visible]
        for i, item in enumerate(visible):
            is_selected = (self.scroll_offset + i == self.selected)
            reason = disabled_fn(item) if disabled_fn else None
            if reason:
                color = (120, 70, 70)
                label = f"{label_fn(item)} ({reason})"
            else:
                color = YELLOW if is_selected else GRAY
                label = label_fn(item)
            text = font.render(label, True, color)
            text_x = center_x - text.get_width() // 2
            text_y = int(start_y + i * line_height)
            if is_selected and not reason:
                box_rect = pygame.Rect(text_x - 10, text_y - 4, text.get_width() + 20, text.get_height() + 8)
                draw_selection_highlight(surface, box_rect, scale, pulse)
            surface.blit(text, (text_x, text_y))

        if self.scroll_offset + self.max_visible < len(self.items):
            down_indicator = font.render("↓ more", True, GRAY)
            down_y = int(start_y + self.max_visible * line_height)
            surface.blit(down_indicator, (center_x - down_indicator.get_width() // 2, down_y))
