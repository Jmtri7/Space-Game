"""Confirmation dialogs for user actions."""
import pygame
from game.constants import WHITE, YELLOW
from game.utils import get_ui_scale, get_ui_offset, _center_text_x, get_font
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_controls_pane


class ConfirmDialog:
    """Generic yes/no confirmation dialog with optional context data."""
    def __init__(self, title, message, context_data=None):
        self.title = title
        self.message = message
        self.context_data = context_data

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    return ("confirm", self.context_data)
                elif event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
                    return ("cancel", None)
        return (None, None)

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.1), int(offset_y + 600 * scale * 0.25), int(800 * scale * 0.8), int(600 * scale * 0.57))
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(32 * scale))
        font_text = get_font(int(24 * scale))

        draw_glow_title(surface, self.title, font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.3), color=WHITE, shadow_color=(30, 30, 30))

        message_text = font_text.render(self.message, True, YELLOW)
        surface.blit(message_text, (_center_text_x(surface, message_text, offset_x), int(offset_y + 600 * scale * 0.45)))

        # Top-left Controls pane, same spot/style every other menu uses -
        # takes over whatever was there (the menu underneath this
        # confirmation, or the base screen) since Y/N/ESC is the only
        # thing actually pressable right now.
        margin = int(10 * scale)
        draw_controls_pane(surface, margin, margin, "Controls", [("Y", "Yes"), ("N", "No"), ("ESC", "Cancel")], scale)
