"""Pause menu during gameplay (see MenuBase) - a column of action buttons.
Mouse-only; **Resume** is the button, there is no ESC-to-resume."""
import pygame
import game.utils as utils
from game.utils import get_ui_scale, get_ui_offset, get_font
from game.ui.menu_base import MenuBase
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, modal_panel_rect

RESUME_ACCENT = (150, 200, 255)
NEUTRAL_ACCENT = (210, 210, 220)
QUIT_ACCENT = (230, 160, 150)


class PauseMenu(MenuBase):
    """Resume / Save Game / Load Game / Quit to Menu, as buttons. `handle_input`
    returns the clicked button's action string (`"resume"` / `"save"` /
    `"load"` / `"quit"`) or `None`."""

    def __init__(self):
        self._buttons = [
            ("resume", "Resume", RESUME_ACCENT),
            ("save", "Save Game", NEUTRAL_ACCENT),
            ("load", "Load Game", NEUTRAL_ACCENT),
            ("quit", "Quit to Menu", QUIT_ACCENT),
        ]
        self.button_index = 0
        self.success_timer = 0

    def buttons(self):
        return [(bid, label, accent, False) for bid, label, accent in self._buttons]

    def panel_rect(self, scale):
        return modal_panel_rect(scale, 0.24, 0.6, 0.56)

    def button_bar_rects(self, scale):
        panel = self.panel_rect(scale)
        top_y = int(panel.y + panel.height * 0.24)
        return self.button_column_rects(panel.centerx, top_y, len(self._buttons), scale, btn_w=300, btn_h=44, gap=14)

    def update(self):
        if self.success_timer > 0:
            self.success_timer -= 1

    def handle_input(self, events):
        for event in events:
            pressed = self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale()))
            if pressed is not None:
                return pressed
        return None

    def draw_content(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        pygame.draw.rect(surface, (0, 0, 0), (0, 0, utils.screen_width, utils.screen_height))
        panel_rect = self.panel_rect(scale)
        draw_glass_panel(surface, panel_rect, scale)

        draw_glow_title(surface, "PAUSED", get_font(int(48 * scale)), panel_rect.centerx, int(offset_y + 600 * scale * 0.28))

        if self.success_timer > 0:
            font_success = get_font(int(28 * scale))
            success_text = font_success.render("Saved!", True, (0, 255, 0))
            surface.blit(success_text, (panel_rect.centerx - success_text.get_width() // 2, int(offset_y + 600 * scale * 0.2)))
