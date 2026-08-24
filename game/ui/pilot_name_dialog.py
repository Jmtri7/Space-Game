"""Dialog for entering pilot name when starting a new game."""
import pygame
from game.constants import WHITE, YELLOW, GRAY
from game.utils import get_ui_scale, get_ui_offset, _center_text_x, get_font
from game.ui.ui_theme import draw_glass_panel, draw_glow_title


class PilotNameDialog:
    """Dialog for entering pilot name when starting a new game."""
    def __init__(self):
        self.pilot_name = ""

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and self.pilot_name:
                    return self.pilot_name
                elif event.key == pygame.K_BACKSPACE:
                    self.pilot_name = self.pilot_name[:-1]
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
            elif event.type == pygame.TEXTINPUT:
                if len(self.pilot_name) < 30:
                    self.pilot_name += event.text
        return None

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.25), int(800 * scale * 0.7), int(600 * scale * 0.5))
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(40 * scale))
        font_text = get_font(int(28 * scale))

        draw_glow_title(surface, "New Game", font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.3))

        prompt = font_text.render("Enter Pilot Name:", True, WHITE)
        surface.blit(prompt, (_center_text_x(surface, prompt, offset_x), int(offset_y + 600 * scale * 0.4)))

        input_box = font_text.render(self.pilot_name + "|", True, YELLOW)
        surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + 600 * scale * 0.5)))

        help_text = font_text.render("Enter to start, ESC to cancel", True, GRAY)
        surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.65)))
