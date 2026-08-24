"""Menu for loading saved games."""
import pygame
from constants import YELLOW, GRAY
from utils import get_ui_scale, get_ui_offset, _center_text_x, _handle_scrolling_input, get_save_files


class LoadMenu:
    """Menu for loading saved games."""
    def __init__(self):
        self.saves = get_save_files()
        self.selected = 0
        self.scroll_offset = 0
        self.max_visible = 5

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                    self.selected, self.scroll_offset = _handle_scrolling_input(
                        event.key, self.selected, self.saves, self.scroll_offset, self.max_visible)
                elif event.key == pygame.K_RETURN and self.saves:
                    return ("load", self.saves[self.selected])
                elif event.key == pygame.K_d and self.saves:
                    return ("delete", self.saves[self.selected])
                elif event.key == pygame.K_ESCAPE:
                    return ("cancel", None)
        return (None, None)

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + 800 * scale * 0.1), int(offset_y + 600 * scale * 0.2), int(800 * scale * 0.8), int(600 * scale * 0.6)))

        font_title = pygame.font.Font(None, int(40 * scale))
        font_save = pygame.font.Font(None, int(24 * scale))

        title = font_title.render("Load Game", True, YELLOW)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + 600 * scale * 0.25)))

        if not self.saves:
            no_saves = font_save.render("No saves found", True, GRAY)
            surface.blit(no_saves, (_center_text_x(surface, no_saves, offset_x), int(offset_y + 600 * scale * 0.5)))
        else:
            if self.scroll_offset > 0:
                up_indicator = font_save.render("↑ more", True, GRAY)
                surface.blit(up_indicator, (int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.33)))

            visible_saves = self.saves[self.scroll_offset:self.scroll_offset + self.max_visible]
            for i, save in enumerate(visible_saves):
                is_selected = (self.scroll_offset + i == self.selected)
                color = YELLOW if is_selected else GRAY
                text = font_save.render(save, True, color)
                text_x = int(offset_x + 800 * scale * 0.15)
                text_y = int(offset_y + 600 * scale * 0.35 + i * 40)
                surface.blit(text, (text_x, text_y))
                if is_selected:
                    box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                    pygame.draw.rect(surface, YELLOW, box_rect, 2)

            if self.scroll_offset + self.max_visible < len(self.saves):
                down_indicator = font_save.render("↓ more", True, GRAY)
                surface.blit(down_indicator, (int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.35 + self.max_visible * 40)))

            help_text = font_save.render("Enter: load, D: delete, ESC: cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.75)))
