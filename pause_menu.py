"""Pause menu during gameplay."""
import pygame
import utils
from constants import YELLOW, GRAY
from utils import get_ui_scale, get_ui_offset


class PauseMenu:
    """Pause menu during gameplay."""
    def __init__(self):
        self.options = ["Resume", "Save Game", "Quit to Menu"]
        self.selected = 0
        self.success_timer = 0

    def update(self):
        if self.success_timer > 0:
            self.success_timer -= 1

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "resume"
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.selected = (self.selected - 1) % len(self.options)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.selected = (self.selected + 1) % len(self.options)
                elif event.key == pygame.K_RETURN:
                    if self.selected == 0:
                        return "resume"
                    elif self.selected == 1:
                        return "save"
                    elif self.selected == 2:
                        return "quit"
        return None

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        pygame.draw.rect(surface, (0, 0, 0), (0, 0, utils.screen_width, utils.screen_height))
        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + 800 * scale * 0.2), int(offset_y + 600 * scale * 0.3), int(800 * scale * 0.6), int(600 * scale * 0.4)))

        font_title = pygame.font.Font(None, int(48 * scale))
        font_option = pygame.font.Font(None, int(32 * scale))

        title = font_title.render("PAUSED", True, YELLOW)
        surface.blit(title, (int(offset_x + 800 * scale // 2 - title.get_width() // 2), int(offset_y + 600 * scale * 0.35)))

        for i, option in enumerate(self.options):
            color = YELLOW if i == self.selected else GRAY
            text = font_option.render(option, True, color)
            text_x = int(offset_x + 800 * scale // 2 - text.get_width() // 2)
            text_y = int(offset_y + 600 * scale * 0.5 + i * 50)
            surface.blit(text, (text_x, text_y))
            if i == self.selected:
                box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                pygame.draw.rect(surface, YELLOW, box_rect, 2)

        if self.success_timer > 0:
            font_success = pygame.font.Font(None, int(32 * scale))
            success_text = font_success.render("Saved!", True, (0, 255, 0))
            surface.blit(success_text, (int(offset_x + 800 * scale * 0.5 - success_text.get_width() // 2), int(offset_y + 600 * scale * 0.15)))
