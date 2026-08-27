"""Pause menu during gameplay."""
import math
import pygame
import game.utils as utils
from game.constants import YELLOW, GRAY
from game.utils import get_ui_scale, get_ui_offset, get_font
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_selection_highlight, modal_panel_rect


class PauseMenu:
    """Pause menu during gameplay."""
    def __init__(self):
        # (label, action) - handle_input returns the action for the
        # highlighted row, so reordering/adding rows needs no index bookkeeping.
        self.entries = [
            ("Resume", "resume"),
            ("Save Game", "save"),
            ("Load Game", "load"),
            ("Quit to Menu", "quit"),
        ]
        self.selected = 0
        self.success_timer = 0

    @property
    def options(self):
        return [label for label, _ in self.entries]

    def update(self):
        if self.success_timer > 0:
            self.success_timer -= 1

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "resume"
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.selected = (self.selected - 1) % len(self.entries)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.selected = (self.selected + 1) % len(self.entries)
                elif event.key == pygame.K_RETURN:
                    return self.entries[self.selected][1]
        return None

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        pygame.draw.rect(surface, (0, 0, 0), (0, 0, utils.screen_width, utils.screen_height))
        panel_rect = modal_panel_rect(scale, 0.24, 0.6, 0.56)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(48 * scale))
        font_option = get_font(int(32 * scale))
        font_help = get_font(int(18 * scale))

        draw_glow_title(surface, "PAUSED", font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.29))

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)
        for i, option in enumerate(self.options):
            is_selected = i == self.selected
            text = font_option.render(option, True, YELLOW if is_selected else GRAY)
            text_x = panel_rect.centerx - text.get_width() // 2
            text_y = int(offset_y + 600 * scale * 0.42 + i * 44 * scale)
            if is_selected:
                box_rect = pygame.Rect(text_x - 10, text_y - 4, text.get_width() + 20, text.get_height() + 8)
                draw_selection_highlight(surface, box_rect, scale, pulse)
            surface.blit(text, (text_x, text_y))

        help_text = font_help.render("Up/Down: select, Enter: choose, ESC: resume", True, GRAY)
        surface.blit(help_text, (panel_rect.centerx - help_text.get_width() // 2, panel_rect.bottom - int(30 * scale)))

        if self.success_timer > 0:
            font_success = get_font(int(32 * scale))
            success_text = font_success.render("Saved!", True, (0, 255, 0))
            surface.blit(success_text, (int(offset_x + 800 * scale * 0.5 - success_text.get_width() // 2), int(offset_y + 600 * scale * 0.15)))
