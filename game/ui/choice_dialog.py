"""`ChoiceDialog` - a one-shot "pick one" pop-up: a title and a column of
button choices, each of which closes the dialog and returns its key to
whatever opened it (ESC returns `"cancel"`).

Replaces the old `LocationSelector` (moon landing spot) and `ExitMenu`
(which interior door to leave by). `main.py` builds the `options` list; this
class doesn't know what the keys mean.
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
        self.title = title
        self.options = list(options)
        self.button_index = 0
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

    def hint_text(self):
        return "Up/Down + Enter, click, or ESC to cancel"

    def panel_rect(self, scale):
        return modal_panel_rect(scale, 0.22, 0.72, 0.58)

    def button_bar_rects(self, scale):
        panel = self.panel_rect(scale)
        top_y = int(panel.y + panel.height * 0.32)
        return self.button_column_rects(panel.centerx, top_y, len(self.options), scale)

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "cancel"
            result = self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale()))
            if result is not None:
                return result
        return None

    def draw_content(self, surface):
        scale = get_ui_scale()
        _, offset_y = get_ui_offset()
        panel = self.panel_rect(scale)
        draw_glass_panel(surface, panel, scale)
        font_title = get_font(int(40 * scale))
        draw_glow_title(surface, self.title, font_title, panel.centerx,
                        int(offset_y + 600 * scale * 0.3), color=WHITE, shadow_color=(30, 30, 30))
