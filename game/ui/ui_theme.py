"""Shared visual helpers for menu-style screens: glass panels, glow titles,
and pulsing selection highlights. Utility functions, not a class - see
CLAUDE.md's One Class Per File rule for why this file is an exception."""
import math
import pygame
from game.constants import YELLOW, WHITE
from game.utils import get_font
import game.utils as utils
from game.world.ship import Ship

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


def draw_info_panel(surface, lines, ui_scale, topright):
    """Draw a top-right-anchored glass panel of aligned (text, color) lines -
    the ship-status/targeting readout style SpaceScreen's HUD uses and
    interior locations now share for their own credits/target readout.
    `lines` is a list of (text, color) tuples; `topright` is the (x, y)
    screen point for the panel's own top-right corner. Returns the drawn rect.
    """
    font = get_font(int(18 * ui_scale))
    pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
    line_height = int(22 * ui_scale)
    rendered = [font.render(text, True, color) for text, color in lines]
    panel_width = max(text.get_width() for text in rendered) + pad_x * 2
    panel_height = pad_y * 2 + line_height * len(rendered)
    rect = pygame.Rect(0, 0, panel_width, panel_height)
    rect.topright = topright
    draw_glass_panel(surface, rect, ui_scale)
    for i, text in enumerate(rendered):
        surface.blit(text, (rect.x + pad_x, rect.y + pad_y + i * line_height))
    return rect


def draw_status_pane(surface, status_lines, ui_scale):
    """Draw a bottom-center glass panel of stacked, colored status lines -
    transient "you can do X now" prompts (landing, jumping, autopilot,
    talking to an NPC...) that are each independently true or false and so
    stack as separate lines in one panel rather than being mutually
    exclusive. `status_lines` is a list of (text, color) tuples; drawing is
    skipped entirely (returns None) when there's nothing to show, so the
    panel doesn't flash an empty box. Anchored to the real screen edges
    (utils.screen_width/height), not get_ui_offset(), matching the rest of
    the space/interior HUD - see SpaceScreen._draw_hud's docstring for why.
    Shared by the space view and interior locations so their status panes
    look and behave identically.
    """
    if not status_lines:
        return None
    font_status = get_font(int(22 * ui_scale))
    pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
    margin = int(10 * ui_scale)
    status_rendered = [font_status.render(text, True, color) for text, color in status_lines]
    status_line_height = status_rendered[0].get_height() + int(4 * ui_scale)
    status_width = max(text.get_width() for text in status_rendered) + pad_x * 2
    status_height = pad_y * 2 + status_line_height * len(status_rendered) - int(4 * ui_scale)
    status_panel = pygame.Rect(0, 0, status_width, status_height)
    status_panel.midbottom = (utils.screen_width // 2, utils.screen_height - margin)
    draw_glass_panel(surface, status_panel, ui_scale)
    for i, text in enumerate(status_rendered):
        text_x = status_panel.centerx - text.get_width() // 2
        text_y = status_panel.y + pad_y + i * status_line_height
        surface.blit(text, (text_x, text_y))
    return status_panel


def draw_ship_glyph(surface, center_x, center_y, pixel_size, graphics):
    """Draw a ship's shape directly in screen pixels, centered on
    (center_x, center_y) - used by ShipBrowserMenu's preview panel and
    OutfittingMenu's diagram. Ship.draw() goes through to_screen()/
    get_scale() (the world camera), the wrong coordinate space for a UI
    panel sized via get_ui_scale()/get_ui_offset() - this reuses
    Ship._get_shape_points() (via a throwaway Ship instance whose .draw()
    is never called - only shape resolution is needed) so a custom
    local_points silhouette vs. a named built-in shape can't drift out of
    sync with how the real ship renders in space. Always drawn at a fixed
    "nose up" orientation (no rotation), which is what angle=0 already
    renders as - see Ship._draw_rotated_polygon's rotation math."""
    ship = Ship(0, 0, graphics=graphics)
    shape = graphics.get("shape", "triangle")
    local_points = ship._get_shape_points(pixel_size, shape)
    color = tuple(graphics.get("color", (150, 150, 150)))
    outline_color = tuple(graphics.get("outline_color", (20, 18, 25)))

    margin = 2
    outline_points = []
    for lx, ly in local_points:
        dist = math.hypot(lx, ly) or 1
        outline_points.append((center_x + lx * (dist + margin) / dist, center_y + ly * (dist + margin) / dist))
    points = [(center_x + lx, center_y + ly) for lx, ly in local_points]

    pygame.draw.polygon(surface, outline_color, outline_points)
    pygame.draw.polygon(surface, color, points)


def draw_selection_highlight(surface, rect, scale, pulse):
    """Draw a pulsing glow box behind a selected menu item. `pulse` is 0..1."""
    glow_alpha = int(90 + 90 * pulse)
    box_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    radius = int(10 * scale)
    pygame.draw.rect(box_surf, (*YELLOW, glow_alpha // 3), box_surf.get_rect(), border_radius=radius)
    pygame.draw.rect(box_surf, (*YELLOW, glow_alpha), box_surf.get_rect(), width=2, border_radius=radius)
    surface.blit(box_surf, rect.topleft)
