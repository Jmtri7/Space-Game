"""`MenuBase` - the shared shape every full-screen modal in `game/ui/` follows.

There are two kinds of modal (see docs/DESIGN_PATTERNS.md's "Menu vs. Dialog"):

- a **menu** (`MenuBase`, `is_dialog = False`) is one you *dwell in* and leave
  explicitly (a Close/Resume button in its own panel);
- a **dialog** (`DialogBase`, `is_dialog = True`) sits *over* another modal and
  resolves as soon as you click one of its choices.

**Menus and dialogs are mouse-only.** Every action is a `ui_theme.draw_button`
widget **inside the panel** - hover highlights it, left-click presses it. The
keyboard does nothing in a menu except type into a text field (the pilot-name
and new-save-name entries); it never moves a selection or presses a button.
There is no dim hint line - a menu is expected to be self-explanatory from its
buttons and labels.

Subclasses provide:

- `draw_content(surface)` - the panel/list/grid;
- `buttons()` - `[(id, label, accent_rgb, disabled_bool), ...]`, the action bar;
- `button_bar_rects(scale)` - where those buttons go (default: a centred row
  along the bottom of `panel_rect(scale)`);
- `panel_rect(scale)` - the main glass panel, so the default bar can anchor;
- `active_popup()` - a sub-dialog drawn on top, if any.

`MenuBase.draw()` is a template method: it draws the content, then defers to
`active_popup()` if a sub-dialog is up, otherwise draws the button bar.
"""
import pygame
from game.ui.ui_theme import draw_button
from game.utils import get_ui_scale, get_font
from game.audio.sound_board import sound_board


class MenuBase:
    is_dialog = False

    # --- subclass hooks --------------------------------------------------
    def draw_content(self, surface):
        raise NotImplementedError

    def buttons(self):
        """`[(id, label, accent_rgb, disabled_bool), ...]` - the action bar."""
        return []

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
    def button_row_rects(self, center_x, center_y, count, scale, btn_w=160, btn_h=48, gap=20, max_width=None):
        """A centred row of `count` equal buttons. If `max_width` is given and
        the natural row (button width + gap) is wider than it, the button
        width and gap are scaled down together to fit - so a 4-button bar
        can't spill past its panel's edges (they still never go below a
        legible floor)."""
        w, h, g = int(btn_w * scale), int(btn_h * scale), int(gap * scale)
        total = count * w + (count - 1) * g
        if max_width and total > max_width and count:
            shrink = max_width / total
            w = max(int(64 * scale), int(w * shrink))
            g = max(int(6 * scale), int(g * shrink))
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
        return self.button_row_rects(panel.centerx, cy, count, scale,
                                     max_width=panel.width - int(32 * scale))

    # --- rendering ----------------------------------------------------
    def draw_buttons(self, surface, rects, scale):
        font = get_font(int(21 * scale))
        for i, ((_id, label, accent, disabled), rect) in enumerate(zip(self.buttons(), rects)):
            draw_button(surface, rect, label, font, scale,
                        selected=(i == self.button_index and not disabled),
                        accent=accent, disabled=disabled)

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

    # --- mouse input -----------------------------------------------
    button_index = 0  # which button the pointer is hovering (for the highlight)

    # --- double-click ------------------------------------------------
    _last_click_ms = -99999
    _last_click_pos = (0, 0)

    def _is_double_click(self, pos, window_ms=400, slop=14):
        """True when this click lands close in time and space to the last
        one - lets a list/grid menu treat a double-click as "activate" (a
        single click still just selects). Call once per MOUSEBUTTONDOWN."""
        now = pygame.time.get_ticks()
        if not isinstance(now, (int, float)):  # mocked pygame (tests) - never a double-click
            return False
        prev_ms, prev_pos = self._last_click_ms, self._last_click_pos
        self._last_click_ms, self._last_click_pos = now, pos
        return (now - prev_ms <= window_ms
                and abs(pos[0] - prev_pos[0]) <= slop
                and abs(pos[1] - prev_pos[1]) <= slop)

    def _button_pressed(self, button_id):
        """Every menu/dialog button press funnels through here so the UI
        "ping" (see game/audio/sound_board.py) fires once - callers
        `return self._button_pressed(_id)`."""
        sound_board.play("ping")
        return button_id

    def handle_button_event(self, event, rects_fn):
        """Hover highlights a button, a left-click presses it. **Enter**
        presses whichever button is currently highlighted (`button_index`) -
        the one concession to the keyboard, for confirming a choice already
        made with the mouse. `rects_fn` is a 0-arg callable returning the
        button rects. Returns the pressed button `id`, or `None`."""
        entries = self.buttons()
        if not entries:
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            i = self.button_index if 0 <= self.button_index < len(entries) else 0
            _id, _l, _a, disabled = entries[i]
            return None if disabled else self._button_pressed(_id)
        if event.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            return None
        for i, ((_id, _l, _a, disabled), rect) in enumerate(zip(entries, rects_fn())):
            if rect.collidepoint(event.pos) and not disabled:
                self.button_index = i
                if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
                    return self._button_pressed(_id)
        return None

    # Back-compat name - identical to handle_button_event now that both are
    # mouse-only.
    handle_button_click = handle_button_event

    def handle_buttons(self, events):
        """Run `handle_button_event` over `events` (lazy rects), return the
        first pressed button `id` or `None`. The common case for `handle_input`."""
        for event in events:
            pressed = self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale()))
            if pressed is not None:
                return pressed
        return None
