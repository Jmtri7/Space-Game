"""Shared visual helpers for menu-style screens: glass panels, glow titles,
and pulsing selection highlights. Utility functions, not a class - see
CLAUDE.md's One Class Per File rule for why this file is an exception."""
import pygame
from constants import YELLOW

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


def draw_selection_highlight(surface, rect, scale, pulse):
    """Draw a pulsing glow box behind a selected menu item. `pulse` is 0..1."""
    glow_alpha = int(90 + 90 * pulse)
    box_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    radius = int(10 * scale)
    pygame.draw.rect(box_surf, (*YELLOW, glow_alpha // 3), box_surf.get_rect(), border_radius=radius)
    pygame.draw.rect(box_surf, (*YELLOW, glow_alpha), box_surf.get_rect(), width=2, border_radius=radius)
    surface.blit(box_surf, rect.topleft)
