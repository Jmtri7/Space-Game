"""Generic yes/no confirmation dialog (see DialogBase). Mouse-only."""
from game.constants import WHITE, YELLOW
from game.utils import get_ui_scale, get_ui_offset, _center_text_x, get_font
from game.ui.dialog_base import DialogBase
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, modal_panel_rect

YES_ACCENT = (120, 220, 140)   # green
NO_ACCENT = (230, 150, 150)    # muted red


class ConfirmDialog(DialogBase):
    """Yes/No confirmation - click a button. `handle_input` returns
    `(action, context_data)` with action `"confirm"` / `"cancel"` / `None`."""

    def __init__(self, title, message, context_data=None):
        self.title = title
        self.message = message
        self.context_data = context_data
        self.button_index = 1  # hover-highlight starts on the safer "No"

    def buttons(self):
        return [
            ("confirm", "Yes", YES_ACCENT, False),
            ("cancel", "No", NO_ACCENT, False),
        ]

    def panel_rect(self, scale):
        return modal_panel_rect(scale, 0.24, 0.8, 0.5)

    def button_bar_rects(self, scale):
        panel = self.panel_rect(scale)
        cy = panel.y + int(panel.height * 0.58)
        return self.button_row_rects(panel.centerx, cy, 2, scale, max_width=panel.width - int(32 * scale))

    def _result(self, button_id):
        if button_id == "confirm":
            return ("confirm", self.context_data)
        if button_id == "cancel":
            return ("cancel", None)
        return None

    def handle_input(self, events):
        for event in events:
            result = self._result(self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale())))
            if result is not None:
                return result
        return (None, None)

    def draw_content(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()
        panel_rect = self.panel_rect(scale)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(32 * scale))
        font_text = get_font(int(24 * scale))

        draw_glow_title(surface, self.title, font_title, panel_rect.centerx,
                        panel_rect.y + int(panel_rect.height * 0.13), color=WHITE, shadow_color=(30, 30, 30))
        message_text = font_text.render(self.message, True, YELLOW)
        surface.blit(message_text, (_center_text_x(surface, message_text, offset_x), panel_rect.y + int(panel_rect.height * 0.33)))
