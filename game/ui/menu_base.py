"""`MenuBase` - the shared shape every full-screen modal in `game/ui/` follows.

There are two kinds of modal (see docs/DESIGN_PATTERNS.md's "Menu vs. Dialog"):

- a **menu** (`MenuBase`, `is_dialog = False`) is one you *dwell in* and leave
  explicitly (a Close/Resume button, ESC, or a hotkey);
- a **dialog** (`DialogBase`, `is_dialog = True`) sits *over* another modal and
  resolves as soon as you pick one of its choices.

Neither draws a Controls pane. Every modal shows its actions as
`ui_theme.draw_button` widgets **inside its own panel**, reachable by mouse
(hover + click) and keyboard (Tab / arrows to move focus, Enter to press).
Subclasses provide:

- `draw_content(surface)` - the panel/list/grid (was `draw()` before the split);
- `buttons()` - `[(id, label, accent_rgb, disabled_bool), ...]`, the action bar;
- `button_bar_rects(scale)` - where those buttons go (default: a centred row
  along the bottom of `panel_rect(scale)`);
- `panel_rect(scale)` - the main glass panel, so the default bar can anchor;
- `hint_text()` - an optional dim one-liner under the bar for controls that
  aren't buttons (grid browsing, drag-to-install, map panning).

`MenuBase.draw()` is a template method: it draws the content, then defers to
`active_popup()` if a sub-dialog is up, otherwise draws the button bar + hint.
"""
import pygame
from game.ui.ui_theme import draw_button
from game.utils import get_ui_scale, get_font
from game.constants import GRAY
from game.audio.sound_board import sound_board


class MenuBase:
    is_dialog = False
    button_layout = "row"  # "row" or "column" - which arrow keys move button focus

    # --- subclass hooks --------------------------------------------------
    def draw_content(self, surface):
        raise NotImplementedError

    def buttons(self):
        """`[(id, label, accent_rgb, disabled_bool), ...]` - the action bar."""
        return []

    def hint_text(self):
        """A dim one-liner under the button bar for non-button controls, or None."""
        return None

    def panel_rect(self, scale):
        """The main glass panel Rect, so the default button bar can anchor to
        its bottom edge. Return None if the subclass overrides
        `button_bar_rects()` itself."""
        return None

    def active_popup(self):
        """A sub-dialog drawn on top of this modal (e.g. `ShipBrowserMenu`'s
        purchase `ConfirmDialog`) - `draw()` hands it the screen while it's up."""
        return None

    # --- button geometry ----------------------------------------------
    def button_row_rects(self, center_x, center_y, count, scale, btn_w=160, btn_h=48, gap=20):
        w, h, g = int(btn_w * scale), int(btn_h * scale), int(gap * scale)
        total = count * w + (count - 1) * g
        x = center_x - total // 2
        return [pygame.Rect(x + i * (w + g), center_y - h // 2, w, h) for i in range(count)]

    def button_column_rects(self, center_x, top_y, count, scale, btn_w=340, btn_h=46, gap=12):
        w, h, g = int(btn_w * scale), int(btn_h * scale), int(gap * scale)
        return [pygame.Rect(center_x - w // 2, top_y + i * (h + g), w, h) for i in range(count)]

    def button_bar_rects(self, scale):
        """Default: a centred row of `buttons()` along the bottom inside
        `panel_rect(scale)`."""
        panel = self.panel_rect(scale)
        if panel is None:
            return []
        count = len(self.buttons())
        if not count:
            return []
        cy = panel.bottom - int(38 * scale)
        return self.button_row_rects(panel.centerx, cy, count, scale)

    # --- rendering ----------------------------------------------------
    def draw_buttons(self, surface, rects, scale):
        font = get_font(int(21 * scale))
        for i, ((_id, label, accent, disabled), rect) in enumerate(zip(self.buttons(), rects)):
            draw_button(surface, rect, label, font, scale,
                        selected=(i == self.button_index and not disabled),
                        accent=accent, disabled=disabled)

    def _draw_hint(self, surface, text, rects, scale):
        """A dim one-liner positioned relative to the button bar: above a
        bottom bar, below a mid-panel row, at the panel's bottom edge when
        the only button is a top corner Close."""
        font = get_font(int(15 * scale))
        rendered = font.render(text, True, GRAY)
        panel = self.panel_rect(scale)
        pad = int(12 * scale)
        cx = (sum(r.centerx for r in rects) // len(rects)) if rects else (
            panel.centerx if panel is not None else surface.get_width() // 2)

        if not rects:
            y = (panel.bottom - int(24 * scale)) if panel is not None else surface.get_height() - int(30 * scale)
        elif panel is not None and max(r.bottom for r in rects) < panel.centery:
            # top corner Close - hint sits at the panel's bottom edge
            cx, y = panel.centerx, panel.bottom - int(22 * scale)
        elif panel is not None and min(r.top for r in rects) > panel.centery:
            # bottom button bar - hint goes just above it
            y = min(r.top for r in rects) - pad - rendered.get_height()
        else:
            # mid-panel row (dialogs) - hint just below
            y = max(r.bottom for r in rects) + pad
        surface.blit(rendered, (cx - rendered.get_width() // 2, y))

    def draw(self, surface):
        self.draw_content(surface)

        popup = self.active_popup()
        if popup is not None:
            popup.draw(surface)
            return

        scale = get_ui_scale()
        rects = self.button_bar_rects(scale)
        if rects:
            self.draw_buttons(surface, rects, scale)
        hint = self.hint_text()
        if hint:
            self._draw_hint(surface, hint, rects, scale)

    # --- button input -----------------------------------------------
    button_index = 0

    def _step_focus(self, delta):
        entries = self.buttons()
        if not entries:
            return
        n = len(entries)
        for _ in range(n):
            self.button_index = (self.button_index + delta) % n
            if not entries[self.button_index][3]:
                return

    def _button_pressed(self, button_id):
        """Every menu/dialog button press funnels through here so the UI
        "ping" (see game/audio/sound_board.py) fires once, consistently,
        for keyboard-Enter and mouse-click alike - callers `return
        self._button_pressed(_id)`."""
        sound_board.play("ping")
        return button_id

    def handle_button_event(self, event, rects_fn=None):
        """Arrows / Tab / Enter / hover / click over the button bar. `rects_fn`
        is a 0-arg callable returning the rects - only invoked for a mouse
        event, so the keyboard path builds no geometry (testable without a
        real pygame). Returns the pressed button `id`, or `None`."""
        entries = self.buttons()
        if not entries:
            return None
        if event.type == pygame.KEYDOWN:
            fwd = (pygame.K_RIGHT, pygame.K_d) if self.button_layout == "row" else (pygame.K_DOWN, pygame.K_s)
            back = (pygame.K_LEFT, pygame.K_a) if self.button_layout == "row" else (pygame.K_UP, pygame.K_w)
            if event.key in fwd or event.key == pygame.K_TAB:
                self._step_focus(1)
            elif event.key in back:
                self._step_focus(-1)
            elif event.key == pygame.K_RETURN:
                _id, _label, _accent, disabled = entries[self.button_index]
                if not disabled:
                    return self._button_pressed(_id)
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and rects_fn is not None:
            for i, ((_id, _l, _a, disabled), rect) in enumerate(zip(entries, rects_fn())):
                if rect.collidepoint(event.pos) and not disabled:
                    self.button_index = i
                    if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
                        return self._button_pressed(_id)
        return None

    def handle_buttons(self, events):
        """Run `handle_button_event` over `events` (lazy rects), return the
        first pressed button `id` or `None`. The common case for `handle_input`."""
        for event in events:
            pressed = self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale()))
            if pressed is not None:
                return pressed
        return None

    def handle_button_click(self, event, rects_fn):
        """Mouse-only variant of `handle_button_event` - hover highlights,
        left-click presses. Used by the grid menus, where Enter/arrows drive
        the grid, not the (single Close) button, so the keyboard must not
        reach the button bar."""
        if event.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            return None
        for i, ((_id, _l, _a, disabled), rect) in enumerate(zip(self.buttons(), rects_fn())):
            if rect.collidepoint(event.pos) and not disabled:
                self.button_index = i
                if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
                    return self._button_pressed(_id)
        return None
