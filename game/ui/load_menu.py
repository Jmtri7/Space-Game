"""Menu for loading saved games."""
import pygame
from game.constants import GRAY
from game.utils import get_ui_scale, get_ui_offset, _center_text_x, get_save_files, get_font
from game.ui.ui_theme import draw_glass_panel, draw_glow_title
from game.ui.selectable_list import SelectableList


class LoadMenu:
    """Menu for loading saved games."""
    def __init__(self):
        self.list = SelectableList(get_save_files(), max_visible=5)

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                    self.list.handle_key(event.key)
                elif event.key == pygame.K_RETURN and self.list.current():
                    return ("load", self.list.current())
                elif event.key == pygame.K_d and self.list.current():
                    return ("delete", self.list.current())
                elif event.key == pygame.K_ESCAPE:
                    return ("cancel", None)
        return (None, None)

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.1), int(offset_y + 600 * scale * 0.2), int(800 * scale * 0.8), int(600 * scale * 0.6))
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(40 * scale))
        font_save = get_font(int(24 * scale))

        draw_glow_title(surface, "Load Game", font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.25))

        if not self.list.items:
            no_saves = font_save.render("No saves found", True, GRAY)
            surface.blit(no_saves, (_center_text_x(surface, no_saves, offset_x), int(offset_y + 600 * scale * 0.5)))

            help_text = font_save.render("ESC: cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.75)))
        else:
            self.list.draw(surface, font_save, panel_rect.centerx, int(offset_y + 600 * scale * 0.35), int(40 * scale), scale)

            help_text = font_save.render("Enter: load, D: delete, ESC: cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.75)))
