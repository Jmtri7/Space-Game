"""`DialogBase` - a modal shown *over* another modal that resolves in one
action. Its choices render as `ui_theme.draw_button` widgets inside its own
panel (a row for a fixed yes/no-style choice, a column for a variable list);
it never shows a Controls pane, and `MenuBase.draw` makes the modal underneath
hide its Controls pane while a dialog is up.

Subclasses provide `buttons()` (the choices) and their own panel layout, then
call `button_row_rects()` / `button_column_rects()` for geometry,
`draw_buttons()` to render, and `handle_button_event()` for keyboard/mouse
navigation. ESC and any letter shortcuts stay with the subclass.
"""
import pygame
from game.ui.menu_base import MenuBase
from game.ui.ui_theme import draw_button
from game.utils import get_font


class DialogBase(MenuBase):
    is_dialog = True
    button_layout = "row"  # "row" or "column" - drives which arrow keys move focus

    def __init__(self):
        self.button_index = 0

    # --- subclass hook -----------------------------------------------------
    def buttons(self):
        """`[(id, label, accent_rgb, disabled_bool), ...]` - the choices.
        Selecting any one closes the dialog (its `id` is what `handle_input`
        returns to `main.py`)."""
        raise NotImplementedError

    def help_items(self):
        # Dialogs never draw a Controls pane - their choices are the buttons.
        return None

    # --- geometry --------------------------------------------------------
    def button_row_rects(self, center_x, center_y, count, scale, btn_w=160, btn_h=50, gap=28):
        w, h, g = int(btn_w * scale), int(btn_h * scale), int(gap * scale)
        total = count * w + (count - 1) * g
        x = center_x - total // 2
        rects = []
        for _ in range(count):
            rects.append(pygame.Rect(x, center_y - h // 2, w, h))
            x += w + g
        return rects

    def button_column_rects(self, center_x, top_y, count, scale, btn_w=340, btn_h=46, gap=12):
        w, h, g = int(btn_w * scale), int(btn_h * scale), int(gap * scale)
        rects = []
        y = top_y
        for _ in range(count):
            rects.append(pygame.Rect(center_x - w // 2, y, w, h))
            y += h + g
        return rects

    # --- rendering ------------------------------------------------------
    def draw_buttons(self, surface, rects, scale):
        font = get_font(int(22 * scale))
        for i, ((_id, label, accent, disabled), rect) in enumerate(zip(self.buttons(), rects)):
            draw_button(surface, rect, label, font, scale,
                        selected=(i == self.button_index and not disabled),
                        accent=accent, disabled=disabled)

    # --- input ---------------------------------------------------------
    def _step_focus(self, delta):
        entries = self.buttons()
        if not entries:
            return
        n = len(entries)
        for _ in range(n):
            self.button_index = (self.button_index + delta) % n
            if not entries[self.button_index][3]:
                return

    def handle_button_event(self, event, rects_fn=None):
        """Arrows / Tab / Enter / hover / click over the button widgets.
        `rects_fn` is a 0-arg callable returning the button rects - only
        called for a mouse event, so the keyboard path never builds geometry
        (keeps this testable without a real pygame). Returns the chosen
        button `id`, or `None` if nothing was committed."""
        entries = self.buttons()
        if event.type == pygame.KEYDOWN:
            fwd = (pygame.K_RIGHT, pygame.K_d) if self.button_layout == "row" else (pygame.K_DOWN, pygame.K_s)
            back = (pygame.K_LEFT, pygame.K_a) if self.button_layout == "row" else (pygame.K_UP, pygame.K_w)
            if event.key in fwd or event.key == pygame.K_TAB:
                self._step_focus(1)
            elif event.key in back:
                self._step_focus(-1)
            elif event.key == pygame.K_RETURN and entries:
                _id, _label, _accent, disabled = entries[self.button_index]
                if not disabled:
                    return _id
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and rects_fn is not None:
            for i, ((_id, _label, _accent, disabled), rect) in enumerate(zip(entries, rects_fn())):
                if rect.collidepoint(event.pos) and not disabled:
                    self.button_index = i
                    if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
                        return _id
        return None
