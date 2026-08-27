"""Shared visual helpers for menu-style screens: glass panels, glow titles,
and pulsing selection highlights. Utility functions, not a class - see
CLAUDE.md's One Class Per File rule for why this file is an exception."""
import math
import pygame
from game.constants import YELLOW, WHITE, GRAY
from game.utils import get_font, _wrap_text
import game.utils as utils
from game.world.ship import Ship

PANEL_COLOR = (8, 10, 20, 235)
PANEL_BORDER = (120, 120, 145)
DISABLED_TEXT_COLOR = (150, 90, 90)


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


MESSAGE_LOG_MAX_VISIBLE = 5  # entries drawn at once, newest first - see Possessions.message_log for the full (capped) history


def draw_message_log(surface, messages, ui_scale):
    """Bottom-left glass panel of received one-way messages (see
    Possessions.add_message/message_log and SpaceScreen._check_one_way_hails),
    newest entry on top - the bottom-left counterpart to draw_status_pane
    (bottom-center) and draw_info_panel (top-right), for messages that
    arrived rather than the player's current status.

    `messages` is a list of (sender, text) tuples, already newest-first
    (see Possessions.add_message) - only the most recent
    MESSAGE_LOG_MAX_VISIBLE are drawn, so the panel has a fixed max size
    regardless of how long the full log has grown. Drawing is skipped
    entirely (returns None) when there are no messages yet, so a fresh
    game doesn't show an empty box in the corner - same pattern as
    draw_status_pane."""
    if not messages:
        return None
    font_title = get_font(int(16 * ui_scale))
    font_text = get_font(int(15 * ui_scale))
    pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
    line_height = int(18 * ui_scale)
    entry_gap = int(4 * ui_scale)
    margin = int(10 * ui_scale)
    box_width = int(320 * ui_scale)

    shown = messages[:MESSAGE_LOG_MAX_VISIBLE]
    # Each entry wraps as one "Sender: text" unit to the panel's width,
    # rather than sender and text wrapping independently - keeps a short
    # message on one line without a lone "Sender:" line above it.
    wrapped_entries = [_wrap_text(font_text, f"{sender}: {text}", box_width - pad_x * 2) for sender, text in shown]

    title_rendered = font_title.render("Messages", True, (200, 220, 255))
    title_height = title_rendered.get_height() + int(4 * ui_scale)
    total_lines = sum(len(lines) for lines in wrapped_entries)
    box_height = pad_y * 2 + title_height + total_lines * line_height + entry_gap * (len(shown) - 1)

    rect = pygame.Rect(0, 0, box_width, box_height)
    rect.bottomleft = (margin, utils.screen_height - margin)
    draw_glass_panel(surface, rect, ui_scale)

    surface.blit(title_rendered, (rect.x + pad_x, rect.y + pad_y))
    y = rect.y + pad_y + title_height
    for i, lines in enumerate(wrapped_entries):
        # Newest (first) entry reads brighter than older ones, so the most
        # recent arrival draws the eye without needing its own timer/flash.
        color = WHITE if i == 0 else GRAY
        for line in lines:
            line_surf = font_text.render(line, True, color)
            surface.blit(line_surf, (rect.x + pad_x, y))
            y += line_height
        y += entry_gap
    return rect


PURCHASE_MESSAGE_FRAMES = 110  # ~1.8s at 60fps before a "Bought 1 X" message starts fading
PURCHASE_MESSAGE_FADE_FRAMES = 30  # ~0.5s fade-out once the timer drops into this range
PURCHASE_MESSAGE_FILL = (25, 95, 45)
PURCHASE_MESSAGE_BORDER = (140, 255, 160)
PURCHASE_MESSAGE_TEXT = (200, 255, 205)


def draw_purchase_message(surface, message, timer, center_x, bottom_y, scale):
    """Draw a transient "Bought 1 X" confirmation, centered at (center_x,
    bottom_y) with its bottom edge there, fading out over its last
    PURCHASE_MESSAGE_FADE_FRAMES of `timer` - shared by ShopMenu/
    ShipBrowserMenu/OutfittingMenu so every purchase gets the same feedback.
    Drawn as a bordered pill (not just bare text) so it actually stands out
    against whatever's behind it, rather than blending into a crowded panel.
    Does nothing if timer <= 0 (the caller is expected to count `timer`
    down once per frame, e.g. inside its own draw(), and stop passing a
    message once it hits 0)."""
    if timer <= 0 or not message:
        return
    alpha = 255 if timer > PURCHASE_MESSAGE_FADE_FRAMES else int(255 * timer / PURCHASE_MESSAGE_FADE_FRAMES)
    font = get_font(int(24 * scale))
    text = font.render(message, True, PURCHASE_MESSAGE_TEXT)

    pad_x, pad_y = int(16 * scale), int(8 * scale)
    pill_rect = pygame.Rect(0, 0, text.get_width() + pad_x * 2, text.get_height() + pad_y * 2)
    pill_rect.midbottom = (center_x, bottom_y)
    radius = pill_rect.height // 2

    pill_surf = pygame.Surface(pill_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(pill_surf, (*PURCHASE_MESSAGE_FILL, 235), pill_surf.get_rect(), border_radius=radius)
    pygame.draw.rect(pill_surf, PURCHASE_MESSAGE_BORDER, pill_surf.get_rect(), width=2, border_radius=radius)
    pill_surf.blit(text, (pad_x, pad_y))
    pill_surf.set_alpha(alpha)
    surface.blit(pill_surf, pill_rect.topleft)


def draw_ship_glyph(surface, center_x, center_y, pixel_size, graphics, angle=0, thrust=0):
    """Draw a ship's shape directly in screen pixels, centered on
    (center_x, center_y) - used by ShipBrowserMenu's preview panel and
    OutfittingMenu's diagram. Ship.draw() goes through to_screen()/
    get_scale() (the world camera), the wrong coordinate space for a UI
    panel sized via get_ui_scale()/get_ui_offset() - this reuses
    Ship._get_shape_points() (via a throwaway Ship instance whose .draw()
    is never called - only shape resolution is needed) so a custom
    local_points silhouette vs. a named built-in shape can't drift out of
    sync with how the real ship renders in space. Drawn "nose up" by
    default (angle=0); OutfittingMenu's diagram relies on that since its
    slot positions are laid out around the glyph without any matching
    rotation. `thrust` (0..1) draws a thruster flame the same way
    Ship._draw_thrusters does, scaled to pixel_size instead of world
    units/get_scale() since this glyph is already in screen pixels."""
    ship = Ship(0, 0, graphics=graphics)
    shape = graphics.get("shape", "triangle")
    local_points = ship._get_shape_points(pixel_size, shape)
    color = tuple(graphics.get("color", (150, 150, 150)))
    outline_color = tuple(graphics.get("outline_color", (20, 18, 25)))

    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    def _rotate(lx, ly):
        return lx * cos_a - ly * sin_a, lx * sin_a + ly * cos_a

    margin = 2
    outline_points = []
    points = []
    for lx, ly in local_points:
        dist = math.hypot(lx, ly) or 1
        orx, ory = _rotate(lx * (dist + margin) / dist, ly * (dist + margin) / dist)
        outline_points.append((center_x + orx, center_y + ory))
        rx, ry = _rotate(lx, ly)
        points.append((center_x + rx, center_y + ry))

    pygame.draw.polygon(surface, outline_color, outline_points)
    pygame.draw.polygon(surface, color, points)
    _draw_glyph_windows(surface, center_x, center_y, pixel_size, graphics, cos_a, sin_a)
    if thrust > 0.05:
        _draw_glyph_thrusters(surface, center_x, center_y, pixel_size, graphics, cos_a, sin_a, thrust)


def _draw_glyph_windows(surface, center_x, center_y, pixel_size, graphics, cos_a, sin_a):
    """Window dots for draw_ship_glyph, mirroring Ship._draw_windows but in
    screen-pixel space (pixel_size already stands in for ship_size*scale)."""
    window_points = graphics.get("windows", [])
    if not window_points:
        return
    window_color = tuple(graphics.get("window_color", (200, 230, 255)))
    radius = max(1, int(round(pixel_size * 0.12)))
    for wx, wy in window_points:
        lx, ly = wx * pixel_size, wy * pixel_size
        rx, ry = lx * cos_a - ly * sin_a, lx * sin_a + ly * cos_a
        pygame.draw.circle(surface, window_color, (center_x + rx, center_y + ry), radius)


def _draw_glyph_thrusters(surface, center_x, center_y, pixel_size, graphics, cos_a, sin_a, thrust):
    """Thruster flames for draw_ship_glyph, mirroring Ship._draw_thrusters
    but in screen-pixel space. thruster_length is configured in world
    units (meaningful relative to a ship_type's own "size" field), so it's
    rescaled by pixel_size/size to keep flame proportions looking right at
    preview scale instead of full world scale - capped relative to
    pixel_size itself, since that ratio blows up for small-"size" ships
    (e.g. the shuttle) whose flame would otherwise dwarf the glyph and
    run into whatever's drawn below the preview."""
    thruster_points = graphics.get("thrusters", [(0, 0.6)])
    thruster_width = graphics.get("thruster_width", 0.15)
    thruster_length = graphics.get("thruster_length", 38)
    thrust_color = tuple(graphics.get("thrust_color", YELLOW))
    world_size = graphics.get("size", 15) or 15
    flame_length = min(thrust * thruster_length * (pixel_size / world_size), pixel_size * 0.6)
    half_width = max(2, pixel_size * thruster_width)

    back_x_dir, back_y_dir = -sin_a, cos_a
    right_x_dir, right_y_dir = cos_a, sin_a

    for tx, ty in thruster_points:
        lx, ly = tx * pixel_size, ty * pixel_size
        mount_x = center_x + (lx * cos_a - ly * sin_a)
        mount_y = center_y + (lx * sin_a + ly * cos_a)

        tip_x = mount_x + back_x_dir * flame_length
        tip_y = mount_y + back_y_dir * flame_length
        base_left = (mount_x + right_x_dir * half_width, mount_y + right_y_dir * half_width)
        base_right = (mount_x - right_x_dir * half_width, mount_y - right_y_dir * half_width)

        pygame.draw.polygon(surface, thrust_color, [(tip_x, tip_y), base_left, base_right])


ICON_DEFAULT_COLOR = (140, 140, 150)


def draw_item_icon(surface, center_x, center_y, size, icon_shape, icon_color):
    """Draw a small procedural icon for a shop item/commodity, centered on
    (center_x, center_y) with pixel `size` roughly its radius. `icon_shape`
    selects a built-in glyph; None or any value not recognized here falls
    back to a plain crate glyph, so an item/commodity with no "icon_shape"
    configured still gets a sane default instead of nothing."""
    color = tuple(icon_color) if icon_color else ICON_DEFAULT_COLOR
    outline = tuple(max(0, c - 70) for c in color)

    if icon_shape == "vial":
        body = pygame.Rect(0, 0, int(size * 1.1), int(size * 1.3))
        body.center = (center_x, center_y + size * 0.15)
        pygame.draw.rect(surface, color, body, border_radius=int(size * 0.3))
        pygame.draw.rect(surface, outline, body, width=1, border_radius=int(size * 0.3))
        neck = pygame.Rect(0, 0, max(2, int(size * 0.4)), max(2, int(size * 0.5)))
        neck.midbottom = body.midtop
        pygame.draw.rect(surface, outline, neck)
    elif icon_shape == "gem":
        points = [
            (center_x, center_y - size), (center_x + size * 0.85, center_y - size * 0.15),
            (center_x, center_y + size), (center_x - size * 0.85, center_y - size * 0.15),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, width=1)
    elif icon_shape == "star":
        points = _star_points(center_x, center_y, size, size * 0.45, 5)
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, width=1)
    elif icon_shape == "blade":  # weapon outfits
        points = [
            (center_x, center_y - size * 1.1), (center_x + size * 0.25, center_y + size * 0.3),
            (center_x, center_y + size), (center_x - size * 0.25, center_y + size * 0.3),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, width=1)
    elif icon_shape == "flame":  # engine outfits
        points = [
            (center_x, center_y - size), (center_x + size * 0.6, center_y + size * 0.2),
            (center_x + size * 0.3, center_y + size), (center_x, center_y + size * 0.6),
            (center_x - size * 0.3, center_y + size), (center_x - size * 0.6, center_y + size * 0.2),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, width=1)
    elif icon_shape == "shield":  # shield outfits
        points = [
            (center_x - size * 0.8, center_y - size * 0.6), (center_x + size * 0.8, center_y - size * 0.6),
            (center_x + size * 0.8, center_y + size * 0.1), (center_x, center_y + size),
            (center_x - size * 0.8, center_y + size * 0.1),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, width=1)
    elif icon_shape == "gear":  # utility outfits
        pygame.draw.circle(surface, color, (center_x, center_y), size)
        pygame.draw.circle(surface, outline, (center_x, center_y), size, width=1)
        pygame.draw.circle(surface, outline, (center_x, center_y), max(1, int(size * 0.35)), width=1)
    else:  # "crate" and any unrecognized/missing icon_shape - the default
        rect = pygame.Rect(0, 0, int(size * 2), int(size * 2))
        rect.center = (center_x, center_y)
        pygame.draw.rect(surface, color, rect, border_radius=int(size * 0.25))
        pygame.draw.rect(surface, outline, rect, width=1, border_radius=int(size * 0.25))
        pygame.draw.line(surface, outline, rect.midtop, rect.midbottom, 1)
        pygame.draw.line(surface, outline, (rect.left, rect.centery), (rect.right, rect.centery), 1)


def _star_points(cx, cy, outer_r, inner_r, num_points):
    """Vertices of a num_points-pointed star, alternating outer_r/inner_r
    radius, for draw_item_icon's "star" glyph."""
    points = []
    for i in range(num_points * 2):
        r = outer_r if i % 2 == 0 else inner_r
        point_angle = math.pi / num_points * i - math.pi / 2
        points.append((cx + r * math.cos(point_angle), cy + r * math.sin(point_angle)))
    return points


def draw_selection_highlight(surface, rect, scale, pulse):
    """Draw a pulsing glow box behind a selected menu item. `pulse` is 0..1."""
    glow_alpha = int(90 + 90 * pulse)
    box_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    radius = int(10 * scale)
    pygame.draw.rect(box_surf, (*YELLOW, glow_alpha // 3), box_surf.get_rect(), border_radius=radius)
    pygame.draw.rect(box_surf, (*YELLOW, glow_alpha), box_surf.get_rect(), width=2, border_radius=radius)
    surface.blit(box_surf, rect.topleft)


def draw_shop_cell(surface, rect, is_selected, reason, icon_fn, name, detail, scale):
    """Shared cell layout for the game's icon-grid shops (ShopMenu's buy/
    sell tabs, OutfittingMenu's Buy tab, ShipBrowserMenu's ship grid): a
    pulsing highlight when selected, an icon, a name line, and a detail
    line (price, or quantity + price). `icon_fn(surface, center_x,
    center_y, size)` draws whatever the icon actually is - a procedural
    item glyph (draw_item_icon) or a static ship silhouette
    (draw_ship_glyph) - so this stays agnostic about that. `reason` (a
    disabled-reason string or None) always leaves `detail` on screen -
    unlike SelectableList's dim rows, this never substitutes the reason
    for the price, only adds it as a second dim line - and dims the name/
    detail to match.
    """
    if is_selected:
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)
        draw_selection_highlight(surface, rect, scale, pulse)

    icon_cy = rect.y + int(rect.height * 0.3)
    icon_size = int(rect.height * 0.22)
    icon_fn(surface, rect.centerx, icon_cy, icon_size)

    font_name = get_font(int(19 * scale))
    font_detail = get_font(int(15 * scale))

    name_color = DISABLED_TEXT_COLOR if reason else (WHITE if is_selected else GRAY)
    name_text = font_name.render(name, True, name_color)
    surface.blit(name_text, (rect.centerx - name_text.get_width() // 2, rect.y + int(rect.height * 0.52)))

    detail_color = DISABLED_TEXT_COLOR if reason else YELLOW
    detail_text = font_detail.render(detail, True, detail_color)
    surface.blit(detail_text, (rect.centerx - detail_text.get_width() // 2, rect.y + int(rect.height * 0.7)))

    if reason:
        reason_text = font_detail.render(f"({reason})", True, DISABLED_TEXT_COLOR)
        surface.blit(reason_text, (rect.centerx - reason_text.get_width() // 2, rect.y + int(rect.height * 0.86)))
