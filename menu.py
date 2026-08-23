"""Main menu for game startup."""
import pygame
import utils
from constants import BLACK, WHITE, YELLOW, GRAY
from utils import get_font, get_centered_x, handle_menu_navigation


class Menu:
    """Main menu for game startup."""
    def __init__(self):
        self.items = ["NEW", "LOAD", "QUIT"]
        self.selected_index = 0

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                new_index = handle_menu_navigation(event, self.selected_index, len(self.items))
                if new_index is not None:
                    self.selected_index = new_index
                elif event.key == pygame.K_RETURN:
                    return self.items[self.selected_index].lower()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                return self._check_click(pygame.mouse.get_pos())
            elif event.type == pygame.MOUSEMOTION:
                self._update_selector_from_mouse(pygame.mouse.get_pos())
        return None

    def _update_selector_from_mouse(self, pos):
        for i in range(len(self.items)):
            rect = self._get_item_rect(i)
            if rect.collidepoint(pos):
                self.selected_index = i
                break

    def _check_click(self, pos):
        for i, item in enumerate(self.items):
            rect = self._get_item_rect(i)
            if rect.collidepoint(pos):
                self.selected_index = i
                return item.lower()
        return None

    def _get_item_rect(self, index):
        scale = min(utils.screen_width, utils.screen_height) / 600.0
        y_base = int(200 * scale)
        y_spacing = int(80 * scale)
        font_menu = get_font(int(48 * scale))
        text = font_menu.render(self.items[index], True, WHITE)
        rect = text.get_rect(center=(utils.screen_width // 2, y_base + index * y_spacing))
        return rect

    def draw(self, surface):
        surface.fill(BLACK)

        scale = min(utils.screen_width, utils.screen_height) / 600.0
        font_large = get_font(int(72 * scale))
        font_menu = get_font(int(48 * scale))

        title = font_large.render("MENU", True, WHITE)
        surface.blit(title, (get_centered_x(title.get_width()), int(50 * scale)))

        y_base = int(200 * scale)
        y_spacing = int(80 * scale)

        # Find max width of all menu items for padding
        max_width = max(font_menu.render(item, True, WHITE).get_width() for item in self.items)
        box_padding = int(20 * scale)
        box_width = max_width + box_padding * 2

        for i, item in enumerate(self.items):
            color = YELLOW if i == self.selected_index else GRAY
            text = font_menu.render(item, True, color)
            y = y_base + i * y_spacing
            text_x = get_centered_x(text.get_width())
            surface.blit(text, (text_x, y))

            if i == self.selected_index:
                box_x = utils.screen_width // 2 - box_width // 2
                box_top_padding = int(8 * scale)
                box_bottom_padding = int((y_spacing - text.get_height()) / 2)
                box_y = y - box_top_padding
                box_height = text.get_height() + box_top_padding + box_bottom_padding
                box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
                pygame.draw.rect(surface, YELLOW, box_rect, 2)
