"""Shared visual helpers for menu-style screens: glass panels, glow titles,
and pulsing selection highlights. Utility functions, not a class - see
CLAUDE.md's One Class Per File rule for why this file is an exception."""
import pygame
from game.constants import YELLOW, WHITE
from game.utils import get_font

PANEL_COLOR = (8, 10, 20, 235)
PANEL_BORDER = (120, 120, 145)


def draw_glass_panel(surface, rect, scale):
    """Draw a semi-opaque rounded panel used as a backdrop for menu content."""
    panel_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    radius = int(14 * scale)
    pygame.draw.rect(panel_surf, PANEL_COLOR, panel_surf.get_rect(), border_radius=radius)
    pygame.draw.rect(panel_surf, PANEL_BORDER, panel_surf.get_rect(), width=1, border_radius=radius)
    surface.blit(panel_surf, rect.topleft)


def draw_glow_title(surface, text, font, center_x, top_y, color=YELLOW, shadow_color=(60, 45, 10)):
    """Draw a title with a soft drop-shadow for a glowing look. Returns its height."""
    shadow = font.render(text, True, shadow_color)
    title = font.render(text, True, color)
    x = center_x - title.get_width() // 2
    surface.blit(shadow, (x + 2, top_y + 2))
    surface.blit(title, (x, top_y))
    return title.get_height()


def draw_controls_pane(surface, x, y, title, items, ui_scale):
    """Draw a titled key/description control-reference panel with its
    top-left corner at (x, y) - keys are left-aligned at the margin, colons
    sit in a fixed column, and descriptions start after that column, so
    controls of different key-length still read as one aligned list (space-
    padding a single string wouldn't align, since the HUD font isn't
    monospace). `items` is a list of (key, description) tuples. Shared by
    the space view and interior locations so their control panes look and
    behave identically. Returns the drawn rect.
    """
    font = get_font(int(18 * ui_scale))
    pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
    line_height = int(22 * ui_scale)
    colon_gap = int(6 * ui_scale)
    desc_gap = int(8 * ui_scale)

    title_rendered = font.render(title, True, WHITE)
    key_rendered = [font.render(key, True, WHITE) for key, _ in items]
    desc_rendered = [font.render(desc, True, WHITE) for _, desc in items]
    colon_rendered = font.render(":", True, WHITE)
    key_column_width = max(text.get_width() for text in key_rendered)
    desc_x_offset = key_column_width + colon_gap + colon_rendered.get_width() + desc_gap

    panel_width = max(
        title_rendered.get_width(),
        desc_x_offset + max(text.get_width() for text in desc_rendered),
    ) + pad_x * 2
    # Title line, then a blank line's worth of gap, then one line per control.
    panel_height = pad_y * 2 + line_height * (len(items) + 2)
    rect = pygame.Rect(x, y, panel_width, panel_height)
    draw_glass_panel(surface, rect, ui_scale)

    surface.blit(title_rendered, (rect.x + pad_x, rect.y + pad_y))
    key_x = rect.x + pad_x
    colon_x = rect.x + pad_x + key_column_width + colon_gap
    desc_x = rect.x + pad_x + desc_x_offset
    for i, (key_text, desc_text) in enumerate(zip(key_rendered, desc_rendered)):
        row_y = rect.y + pad_y + (i + 2) * line_height
        surface.blit(key_text, (key_x, row_y))
        surface.blit(colon_rendered, (colon_x, row_y))
        surface.blit(desc_text, (desc_x, row_y))
    return rect


def draw_selection_highlight(surface, rect, scale, pulse):
    """Draw a pulsing glow box behind a selected menu item. `pulse` is 0..1."""
    glow_alpha = int(90 + 90 * pulse)
    box_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    radius = int(10 * scale)
    pygame.draw.rect(box_surf, (*YELLOW, glow_alpha // 3), box_surf.get_rect(), border_radius=radius)
    pygame.draw.rect(box_surf, (*YELLOW, glow_alpha), box_surf.get_rect(), width=2, border_radius=radius)
    surface.blit(box_surf, rect.topleft)
