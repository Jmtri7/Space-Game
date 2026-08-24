"""Pause menu during gameplay."""
import math
import pygame
import utils
from constants import YELLOW, GRAY
from utils import get_ui_scale, get_ui_offset, get_font
from ui_theme import draw_glass_panel, draw_glow_title, draw_selection_highlight


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
        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.2), int(offset_y + 600 * scale * 0.3), int(800 * scale * 0.6), int(600 * scale * 0.4))
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(48 * scale))
        font_option = get_font(int(32 * scale))

        draw_glow_title(surface, "PAUSED", font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.35))

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)
        for i, option in enumerate(self.options):
            is_selected = i == self.selected
            text = font_option.render(option, True, YELLOW if is_selected else GRAY)
            text_x = panel_rect.centerx - text.get_width() // 2
            text_y = int(offset_y + 600 * scale * 0.5 + i * 50)
            if is_selected:
                box_rect = pygame.Rect(text_x - 10, text_y - 4, text.get_width() + 20, text.get_height() + 8)
                draw_selection_highlight(surface, box_rect, scale, pulse)
            surface.blit(text, (text_x, text_y))

        if self.success_timer > 0:
            font_success = get_font(int(32 * scale))
            success_text = font_success.render("Saved!", True, (0, 255, 0))
            surface.blit(success_text, (int(offset_x + 800 * scale * 0.5 - success_text.get_width() // 2), int(offset_y + 600 * scale * 0.15)))
