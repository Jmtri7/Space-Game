"""Confirmation dialogs for user actions."""
import pygame
from constants import WHITE, YELLOW, GRAY
from utils import get_ui_scale, get_ui_offset, _center_text_x


class ConfirmDialog:
    """Generic yes/no confirmation dialog with optional context data."""
    def __init__(self, title, message, context_data=None):
        self.title = title
        self.message = message
        self.context_data = context_data

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    return ("confirm", self.context_data)
                elif event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
                    return ("cancel", None)
        return (None, None)

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.25), int(800 * scale * 0.7), int(600 * scale * 0.5)))
        font_title = pygame.font.Font(None, int(32 * scale))
        font_text = pygame.font.Font(None, int(24 * scale))

        title = font_title.render(self.title, True, WHITE)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + 600 * scale * 0.3)))

        message_text = font_text.render(self.message, True, YELLOW)
        surface.blit(message_text, (_center_text_x(surface, message_text, offset_x), int(offset_y + 600 * scale * 0.45)))

        help_text = font_text.render("Y: Yes   N: No   ESC: Cancel", True, GRAY)
        surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.65)))
