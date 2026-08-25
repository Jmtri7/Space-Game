"""Dialog for choosing a destination when an interior location's exit
leads to more than one place - shown to the player instead of LocationScreen
immediately exiting, whenever get_exit_options() returns more than one
option (see docs/CONTROLS.md#exit-menu)."""
import pygame
from game.utils import get_ui_scale, get_ui_offset, get_font
from game.ui.ui_theme import draw_glass_panel, draw_glow_title
from game.ui.selectable_list import SelectableList


class ExitMenu:
    """Dialog for choosing a destination when an interior's exit leads to
    more than one place."""
    def __init__(self, options, interiors):
        # options: LocationScreen.get_exit_options() - connected_locations
        # keys plus "ship" if return_to_ship is set.
        # interiors: the landable's own interiors dict, used only to look
        # up a friendly label for each connected location key.
        self.options = options
        self.interiors = interiors
        self.list = SelectableList(options, max_visible=max(1, len(options)))

    def _label(self, key):
        if key == "ship":
            return "Return to Ship"
        interior_config = self.interiors.get(key)
        if isinstance(interior_config, dict):
            return interior_config.get("label", key.capitalize())
        return key.capitalize()

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

        draw_glow_title(surface, "Where To?", font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.3))

        self.list.draw(surface, font_text, panel_rect.centerx, int(offset_y + 600 * scale * 0.45), int(40 * scale), scale, label_fn=self._label)
