"""Confirmation dialogs for user actions."""
import pygame
from game.constants import WHITE, YELLOW, GRAY
from game.utils import get_ui_scale, get_ui_offset, _center_text_x, get_font
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_button, modal_panel_rect

YES_ACCENT = (120, 220, 140)   # green
NO_ACCENT = (230, 150, 150)    # muted red

# 0 = Yes, 1 = No. Starts on No: two of the three uses (delete/overwrite a
# save) are destructive, so the safe choice is the default. Y still confirms
# instantly, and hovering/clicking Yes needs no keyboard at all.
_YES, _NO = 0, 1


class ConfirmDialog:
    """Generic yes/no confirmation. The two choices are drawn as buttons
    (see ui_theme.draw_button) - move between them with Left/Right (or Tab),
    Enter picks the highlighted one; Y / N / ESC are still shortcuts; and
    each button is clickable (hover highlights, click acts)."""
    def __init__(self, title, message, context_data=None):
        self.title = title
        self.message = message
        self.context_data = context_data
        self.selected = _NO

    def _layout(self, scale):
        """(panel_rect, yes_rect, no_rect) - deterministic from screen size,
        so handle_input and draw agree without passing rects between frames."""
        panel = modal_panel_rect(scale, 0.25, 0.8, 0.42)
        btn_w, btn_h = int(160 * scale), int(50 * scale)
        gap = int(28 * scale)
        cy = panel.y + int(panel.height * 0.62)
        yes = pygame.Rect(0, 0, btn_w, btn_h)
        yes.midright = (panel.centerx - gap // 2, cy)
        no = pygame.Rect(0, 0, btn_w, btn_h)
        no.midleft = (panel.centerx + gap // 2, cy)
        return panel, yes, no

    def _result(self):
        return ("confirm", self.context_data) if self.selected == _YES else ("cancel", None)

    def handle_input(self, events):
        rects = None  # (yes_rect, no_rect) - computed lazily, only if a mouse event needs them
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    return ("confirm", self.context_data)
                if event.key in (pygame.K_n, pygame.K_ESCAPE):
                    return ("cancel", None)
                if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
                    self.selected ^= 1
                elif event.key == pygame.K_RETURN:
                    return self._result()
            elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                if rects is None:
                    _, yes_rect, no_rect = self._layout(get_ui_scale())
                    rects = (yes_rect, no_rect)
                yes_rect, no_rect = rects
                over_yes = yes_rect.collidepoint(event.pos)
                over_no = no_rect.collidepoint(event.pos)
                if over_yes:
                    self.selected = _YES
                elif over_no:
                    self.selected = _NO
                if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
                    if over_yes:
                        return ("confirm", self.context_data)
                    if over_no:
                        return ("cancel", None)
        return (None, None)

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()
        panel_rect, yes_rect, no_rect = self._layout(scale)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(32 * scale))
        font_text = get_font(int(24 * scale))
        font_btn = get_font(int(24 * scale))
        font_hint = get_font(int(16 * scale))

        draw_glow_title(surface, self.title, font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.3), color=WHITE, shadow_color=(30, 30, 30))

        message_text = font_text.render(self.message, True, YELLOW)
        surface.blit(message_text, (_center_text_x(surface, message_text, offset_x), int(offset_y + 600 * scale * 0.44)))

        draw_button(surface, yes_rect, "Yes", font_btn, scale, selected=self.selected == _YES, accent=YES_ACCENT)
        draw_button(surface, no_rect, "No", font_btn, scale, selected=self.selected == _NO, accent=NO_ACCENT)

        # A pop-up dialog shows its own choices - no top-left Controls pane
        # (see CLAUDE.md's "Menu Help Text" note); this one line under the
        # buttons is just the shortcut reminder.
        hint = font_hint.render("Click, or Left/Right + Enter    Y / N shortcut    ESC: cancel", True, GRAY)
        surface.blit(hint, (_center_text_x(surface, hint, offset_x), yes_rect.bottom + int(18 * scale)))
