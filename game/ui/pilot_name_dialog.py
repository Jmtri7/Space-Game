"""Dialog for entering a pilot name when starting a new game (see DialogBase).
A text field plus [Start] / [Cancel] buttons; `handle_input` returns the typed
name, `"cancel"`, or `None`."""
import pygame
from game.constants import WHITE, YELLOW
from game.utils import get_ui_scale, get_ui_offset, _center_text_x, get_font
from game.ui.dialog_base import DialogBase
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, modal_panel_rect

START_ACCENT = (120, 220, 140)
CANCEL_ACCENT = (230, 150, 150)


class PilotNameDialog(DialogBase):
    def __init__(self):
        super().__init__()
        self.pilot_name = ""
        # Let held keys (Backspace, letters) auto-repeat while typing.
        pygame.key.set_repeat(400, 40)

    def buttons(self):
        return [
            ("start", "Start", START_ACCENT, not self.pilot_name),
            ("cancel", "Cancel", CANCEL_ACCENT, False),
        ]

    def _panel(self, scale):
        return modal_panel_rect(scale, 0.25, 0.7, 0.55)

    def _button_rects(self, scale):
        panel = self._panel(scale)
        cy = int(panel.y + panel.height * 0.72)
        return self.button_row_rects(panel.centerx, cy, 2, scale)

    def _finish(self, button_id):
        if button_id == "start" and self.pilot_name:
            pygame.key.set_repeat()
            return self.pilot_name
        if button_id == "cancel":
            pygame.key.set_repeat()
            return "cancel"
        return None

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.pilot_name = self.pilot_name[:-1]
                    continue
                if event.key == pygame.K_ESCAPE:
                    pygame.key.set_repeat()
                    return "cancel"
            elif event.type == pygame.TEXTINPUT:
                if len(self.pilot_name) < 30:
                    self.pilot_name += event.text
                continue
            result = self._finish(self.handle_button_event(event, lambda: self._button_rects(get_ui_scale())))
            if result is not None:
                return result
        return None

    def draw_content(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()
        panel_rect = self._panel(scale)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(40 * scale))
        font_text = get_font(int(28 * scale))

        draw_glow_title(surface, "New Game", font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.3))
        prompt = font_text.render("Enter Pilot Name:", True, WHITE)
        surface.blit(prompt, (_center_text_x(surface, prompt, offset_x), int(offset_y + 600 * scale * 0.4)))
        input_box = font_text.render(self.pilot_name + "|", True, YELLOW)
        surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + 600 * scale * 0.5)))

        self.draw_buttons(surface, self._button_rects(scale), scale)
