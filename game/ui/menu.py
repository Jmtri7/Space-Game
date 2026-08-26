"""Main menu for game startup, with an animated star system rendered behind it."""
import math
import pygame
import game.utils as utils
from game.constants import WHITE, YELLOW, GRAY
from game.utils import get_font, handle_menu_navigation
from game.ui.menu_backdrop import MenuBackdrop
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_selection_highlight, draw_controls_pane

TITLE = "GALAXY RISE"  # temp title


class Menu:
    """Main menu for game startup. Renders an animated star system (star,
    planet, station, and a ship flying an orbit) behind the menu items."""
    def __init__(self):
        self.items = ["NEW", "LOAD", "QUIT"]
        self.selected_index = 0
        self.backdrop = MenuBackdrop()

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

    def _layout(self):
        """Shared geometry for the panel and menu items, sized to fit every
        item so the panel outline never clips the last one."""
        scale = min(utils.screen_width, utils.screen_height) / 600.0
        panel_width = int(460 * scale)
        panel_top = int(20 * scale)
        title_area = int(90 * scale)
        y_spacing = int(70 * scale)
        panel_height = title_area + len(self.items) * y_spacing + int(20 * scale)

        panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
        panel_rect.centerx = utils.screen_width // 2
        panel_rect.top = panel_top

        y_base = panel_rect.top + title_area + y_spacing // 2
        return scale, panel_rect, y_base, y_spacing

    def _get_item_rect(self, index):
        scale, panel_rect, y_base, y_spacing = self._layout()
        font_menu = get_font(int(42 * scale))
        text = font_menu.render(self.items[index], True, WHITE)
        box_width = int(260 * scale)
        rect = pygame.Rect(0, 0, box_width, text.get_height() + int(24 * scale))
        rect.center = (panel_rect.centerx, y_base + index * y_spacing)
        return rect

    def draw(self, surface):
        self.backdrop.draw(surface)
        self._draw_panel_and_items(surface)
        scale, _, _, _ = self._layout()
        margin = int(10 * scale)
        help_items = [("Up/Down", "Navigate"), ("Enter", "Select"), ("Click", "Select")]
        draw_controls_pane(surface, margin, margin, "Controls", help_items, scale)

    def _draw_panel_and_items(self, surface):
        scale, panel_rect, y_base, y_spacing = self._layout()
        draw_glass_panel(surface, panel_rect, scale)

        font_large = get_font(int(52 * scale))
        draw_glow_title(surface, TITLE, font_large, panel_rect.centerx, panel_rect.top + int(20 * scale))

        font_menu = get_font(int(38 * scale))
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)

        for i, item in enumerate(self.items):
            rect = self._get_item_rect(i)
            is_selected = i == self.selected_index
            text = font_menu.render(item, True, WHITE if is_selected else GRAY)

            if is_selected:
                draw_selection_highlight(surface, rect, scale, pulse)

            text_rect = text.get_rect(center=rect.center)
            surface.blit(text, text_rect)
