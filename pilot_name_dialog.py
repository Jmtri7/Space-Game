"""Dialog for entering pilot name when starting a new game."""
import pygame
from constants import GAME_WIDTH, GAME_HEIGHT, WHITE, YELLOW, GRAY
from utils import get_scale, get_offset, _center_text_x


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
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.25), int(GAME_WIDTH * scale * 0.7), int(GAME_HEIGHT * scale * 0.5)))

        font_title = pygame.font.Font(None, int(40 * scale))
        font_text = pygame.font.Font(None, int(28 * scale))

        title = font_title.render("New Game", True, YELLOW)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.3)))

        prompt = font_text.render("Enter Pilot Name:", True, WHITE)
        surface.blit(prompt, (_center_text_x(surface, prompt, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.4)))

        input_box = font_text.render(self.pilot_name + "|", True, YELLOW)
        surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.5)))

        help_text = font_text.render("Enter to start, ESC to cancel", True, GRAY)
        surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.65)))
