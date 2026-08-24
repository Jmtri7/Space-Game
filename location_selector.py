"""Dialog for selecting moon landing location."""
import pygame
from utils import get_ui_scale, get_ui_offset, get_font
from ui_theme import draw_glass_panel, draw_glow_title
from selectable_list import SelectableList


class LocationSelector:
    """Dialog for selecting moon landing location."""
    def __init__(self, interior_configs=None):
        # interior_configs: dict of {"city": config_file, "wilderness": config_file, ...}
        self.interior_configs = interior_configs or {}
        location_keys = list(self.interior_configs.keys())
        self.location_labels = {
            "city": "Moon City",
            "wilderness": "Wilderness"
        }
        # max_visible covers every location, so this list never scrolls.
        self.list = SelectableList(location_keys, max_visible=max(1, len(location_keys)))

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                    self.list.handle_key(event.key)
                elif event.key == pygame.K_RETURN:
                    return self.list.current()
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

        label_fn = lambda key: self.location_labels.get(key, key.capitalize())
        self.list.draw(surface, font_text, panel_rect.centerx, int(offset_y + 600 * scale * 0.45), int(40 * scale), scale, label_fn=label_fn)
