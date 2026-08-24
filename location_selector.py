"""Dialog for selecting moon landing location."""
import math
import pygame
from constants import YELLOW, GRAY
from utils import get_ui_scale, get_ui_offset, get_font
from ui_theme import draw_glass_panel, draw_glow_title, draw_selection_highlight


class LocationSelector:
    """Dialog for selecting moon landing location."""
    def __init__(self, interior_configs=None):
        # interior_configs: dict of {"city": config_file, "wilderness": config_file, ...}
        self.interior_configs = interior_configs or {}
        self.location_keys = list(self.interior_configs.keys())
        self.location_labels = {
            "city": "Moon City",
            "wilderness": "Wilderness"
        }
        self.selected = 0

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.selected = (self.selected - 1) % len(self.location_keys)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.selected = (self.selected + 1) % len(self.location_keys)
                elif event.key == pygame.K_RETURN:
                    return self.location_keys[self.selected]
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
        return None

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.25), int(800 * scale * 0.7), int(600 * scale * 0.5))
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(40 * scale))
        font_text = get_font(int(28 * scale))

        draw_glow_title(surface, "Landing Location", font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.3))

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)
        for i, location_key in enumerate(self.location_keys):
            location_label = self.location_labels.get(location_key, location_key.capitalize())
            is_selected = i == self.selected
            text = font_text.render(location_label, True, YELLOW if is_selected else GRAY)
            text_x = panel_rect.centerx - text.get_width() // 2
            text_y = int(offset_y + 600 * scale * 0.45 + i * 40)
            if is_selected:
                box_rect = pygame.Rect(text_x - 10, text_y - 4, text.get_width() + 20, text.get_height() + 8)
                draw_selection_highlight(surface, box_rect, scale, pulse)
            surface.blit(text, (text_x, text_y))
