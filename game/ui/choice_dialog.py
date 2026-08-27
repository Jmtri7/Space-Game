"""`ChoiceDialog` - a one-shot "pick one" pop-up: a title and a column of
button choices, each of which closes the dialog and returns its key to
whatever opened it (ESC returns `"cancel"`).

Replaces the old `LocationSelector` (moon landing spot) and `ExitMenu`
(which interior door to leave by) - both were the same shape: a titled list
of labelled options, optionally with some greyed out and unselectable.
`main.py` builds the `options` list; this class doesn't know or care what the
keys mean.
"""
import pygame
from game.constants import WHITE
from game.utils import get_ui_scale, get_ui_offset, get_font
from game.ui.dialog_base import DialogBase
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, modal_panel_rect

CHOICE_ACCENT = (170, 200, 235)


class ChoiceDialog(DialogBase):
    button_layout = "column"

    def __init__(self, title, options):
        """`options`: `[(key, label, disabled_reason_or_None), ...]`."""
        super().__init__()
        self.title = title
        self.options = list(options)
        # Never start focused on a disabled entry.
        for i, (_key, _label, reason) in enumerate(self.options):
            if not reason:
                self.button_index = i
                break

    def buttons(self):
        out = []
        for key, label, reason in self.options:
            text = f"{label}  ({reason})" if reason else label
            out.append((key, text, CHOICE_ACCENT, bool(reason)))
        return out

    def _panel(self, scale):
        return modal_panel_rect(scale, 0.22, 0.72, 0.58)

    def _button_rects(self, scale):
        panel = self._panel(scale)
        top_y = int(panel.y + panel.height * 0.34)
        return self.button_column_rects(panel.centerx, top_y, len(self.options), scale)

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "cancel"
            result = self.handle_button_event(event, lambda: self._button_rects(get_ui_scale()))
            if result is not None:
                return result
        return None

    def draw_content(self, surface):
        scale = get_ui_scale()
        _, offset_y = get_ui_offset()
        panel = self._panel(scale)
        draw_glass_panel(surface, panel, scale)

        font_title = get_font(int(40 * scale))
        draw_glow_title(surface, self.title, font_title, panel.centerx,
                        int(offset_y + 600 * scale * 0.3), color=WHITE, shadow_color=(30, 30, 30))

        self.draw_buttons(surface, self._button_rects(scale), scale)
