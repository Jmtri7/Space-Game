"""Shared visual helpers for menu-style screens: glass panels, glow titles,
and pulsing selection highlights. Utility functions, not a class - an
intentional One Class Per File exception, see docs/ARCHITECTURE.md's "Project
Layout & File Conventions"."""
import math
import pygame
from game.constants import YELLOW, WHITE, GRAY
from game.utils import get_font, _wrap_text, get_ui_scale
import game.utils as utils
from game.world.ship import Ship
from game.world.world_object import _resolve_part_color, _ring_quads

PANEL_COLOR = (8, 10, 20, 235)
PANEL_BORDER = (120, 120, 145)
DISABLED_TEXT_COLOR = (150, 90, 90)
# Message Log sender-name styling (underlined + coloured, distinct from the
# message body) - brighter for the newest entry, dimmer for older ones, to
# match the WHITE/GRAY body treatment.
MESSAGE_SENDER_COLOR = (120, 210, 255)
MESSAGE_SENDER_COLOR_DIM = (95, 145, 180)


def side_panel_max_width():
    """Max width for a HUD panel anchored to the left or right edge
    (Controls, minimap, the targeting/credits info panel, the Messages
    log) - one fifth of the real window width. Both side panels and the
    middle status pane (see center_panel_max_width) size themselves from
    their own content and can otherwise grow arbitrarily wide (long NPC
    dialogue text, a long status message) regardless of window size/aspect
    ratio - get_ui_scale() alone doesn't prevent this, since on a wide
    window it's clamped by height, not width. Keeping every side panel
    within this fifth and the status pane within center_panel_max_width()
    is what stops them from visually overlapping regardless of window
    shape."""
    return utils.screen_width // 5


HUD_MARGIN_BASE = 10  # px at scale 1 - gap every HUD panel keeps from the screen edge


def hud_margin(ui_scale):
    """The gap a HUD panel leaves between itself and the screen edge -
    every edge-anchored pane (both screens' Controls / info / status /
    Messages panes, the minimap) uses this exact value so they line up."""
    return int(HUD_MARGIN_BASE * ui_scale)


def side_panel_width(ui_scale):
    """Exact width for an edge-anchored HUD side panel: its outer edge sits
    hud_margin() from the screen edge and its inner edge lands right on the
    quarter line (side_panel_max_width()), so the Controls / info / Messages
    panes all fill their quarter to the same width instead of each shrinking
    to its own content. Callers still add their own internal padding within
    this width."""
    return max(1, side_panel_max_width() - hud_margin(ui_scale))


def center_panel_max_width(ui_scale):
    """Max width for a HUD panel/message anchored to the horizontal center
    (the bottom status pane, the top-centre popup stack, modal menu panels).
    Half the window width minus a hud_margin() gap on each side - well clear
    of the 4/5 line where a side pane (now side_panel_max_width() = a fifth)
    begins, so nothing centred ever touches, let alone overlaps, a side pane
    regardless of window shape."""
    return max(1, utils.screen_width // 2 - 2 * hud_margin(ui_scale))


def modal_panel_rect(ui_scale, y_frac, w_frac, h_frac):
    """The main panel rect for a full-screen modal menu (shop, outfitting,
    possessions, mission log, the save/load/confirm dialogs, ...). Menus
    historically sized this by hand as fractions of the letterboxed 800x600
    UI canvas (`get_ui_offset()` + `800 * scale * frac`); on a window wider
    than 4:3 that canvas is height-bound and can grow wide enough to push a
    0.8-of-canvas panel well past the screen's middle-half zone.

    This keeps the same vertical placement (`y_frac`/`h_frac` are still
    canvas fractions) but caps the width at `center_panel_max_width()` and
    re-centres it on the real screen, so a modal menu respects the same
    horizontal zone discipline as the HUD's centre panes (see
    docs/DESIGN_PATTERNS.md's "HUD Zone Width Discipline"). Every menu's
    panel was already horizontally centred, so nothing shifts on a normal
    aspect ratio - the cap is a no-op there."""
    _, offset_y = utils.get_ui_offset()
    width = min(int(800 * ui_scale * w_frac), center_panel_max_width(ui_scale))
    height = int(600 * ui_scale * h_frac)
    x = int(utils.screen_width / 2 - width / 2)
    y = int(offset_y + 600 * ui_scale * y_frac)
    return pygame.Rect(x, y, width, height)


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


def draw_glow_message(surface, text, font, center_x, top_y, color=YELLOW, shadow_color=(60, 45, 10)):
    """Like draw_glow_title, but for free-form text that isn't a short,
    fixed UI label - a top-center jump/hail banner or a mission toast, whose
    text can be arbitrary story/dialogue content (an NPC's one-way hail
    message, for instance). Wraps to center_panel_max_width() and stacks
    each line via draw_glow_title, so a long message can't run wide enough
    to overlap a side panel the way a single unwrapped line could.

    Drawn inside a glass pane (same look as every other HUD panel) so these
    transient popups read as part of the UI rather than bare floating text.
    `top_y` is where the *text* starts; the pane extends a little above and
    around it. Returns the pane's pygame.Rect so a caller can stack another
    message directly below it."""
    scale = get_ui_scale()
    pad_x, pad_y = int(16 * scale), int(10 * scale)
    # Wrap so the whole pane (text + padding) stays within the centre zone,
    # not just the text - otherwise the padding can nudge a full-width
    # message's pane into a side panel's quarter (see center_panel_max_width).
    lines = _wrap_text(font, text, center_panel_max_width(scale) - pad_x * 2)
    rendered = [font.render(line, True, color) for line in lines]
    line_height = font.get_linesize()
    text_width = max((surf.get_width() for surf in rendered), default=0)
    text_height = line_height * max(1, len(lines))

    panel = pygame.Rect(0, 0, text_width + pad_x * 2, text_height + pad_y * 2)
    panel.midtop = (center_x, top_y - pad_y)
    draw_glass_panel(surface, panel, scale)

    y = top_y
    for line in lines:
        draw_glow_title(surface, line, font, center_x, y, color=color, shadow_color=shadow_color)
        y += line_height
    return panel


CONTROLS_TOGGLE_KEY = "C"  # key that shows/hides the Controls pane (see the screens' handle_input)


def draw_controls_pane(surface, x, y, title, items, ui_scale, collapsed=False):
    """Draw a titled key/description control-reference panel with its
    top-left corner at (x, y) - keys are left-aligned at the margin and
    descriptions sit in a fixed column after them, so different key lengths
    still read as one aligned list. A description too long for the remaining
    width **wraps** onto continuation lines (aligned under the description
    column) instead of running off the panel edge. `items` is a list of
    (key, description) tuples.

    When `collapsed` is True only the title and a single
    "<key> : Show controls" line are drawn - the pane folds to a two-liner.
    Either way it is exactly `side_panel_width()` wide so it lines up with
    the info / Messages panes. Returns the drawn rect.
    """
    font = get_font(int(17 * ui_scale))
    pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
    line_height = int(21 * ui_scale)
    colon_gap = int(5 * ui_scale)
    desc_gap = int(8 * ui_scale)
    panel_width = side_panel_width(ui_scale)
    key_color = (150, 220, 255)

    rows = [(CONTROLS_TOGGLE_KEY, "Show controls")] if collapsed \
        else list(items) + [(CONTROLS_TOGGLE_KEY, "Hide controls")]

    title_rendered = get_font(int(18 * ui_scale)).render(title, True, WHITE)
    colon_rendered = font.render(":", True, key_color)
    # Cap the key column so one long key can't crush the description column.
    key_col = min(max(font.size(k)[0] for k, _ in rows), int(panel_width * 0.42))
    desc_x_off = key_col + colon_gap + colon_rendered.get_width() + desc_gap
    desc_max_width = max(int(40 * ui_scale), panel_width - pad_x * 2 - desc_x_off)

    wrapped = [_wrap_text(font, d, desc_max_width) or [""] for _, d in rows]
    total_lines = sum(len(w) for w in wrapped)

    panel_height = pad_y * 2 + line_height * 2 + int(4 * ui_scale) + total_lines * line_height
    rect = pygame.Rect(x, y, panel_width, panel_height)
    draw_glass_panel(surface, rect, ui_scale)

    surface.blit(title_rendered, (rect.x + pad_x, rect.y + pad_y))
    key_x = rect.x + pad_x
    colon_x = key_x + key_col + colon_gap
    desc_x = rect.x + pad_x + desc_x_off

    row_y = rect.y + pad_y + line_height + int(4 * ui_scale)
    for (key, _d), desc_lines in zip(rows, wrapped):
        surface.blit(font.render(key, True, key_color), (key_x, row_y))
        surface.blit(colon_rendered, (colon_x, row_y))
        for line in desc_lines:
            surface.blit(font.render(line, True, WHITE), (desc_x, row_y))
            row_y += line_height
    return rect


INFO_LABEL_COLOR = (150, 170, 210)  # muted blue-grey for "Label:" prefixes - values keep their own color


def draw_info_panel(surface, lines, ui_scale, topright, scroll=0):
    """Draw a top-right-anchored glass panel of aligned text lines - the
    ship-status/targeting readout style SpaceScreen's HUD uses and interior
    locations now share for their own credits/target readout.
    `topright` is the (x, y) screen point for the panel's own top-right
    corner. Each entry in `lines` is either:

      (text, color)             - a plain single-colour line
      (label, value, value_col) - a two-tone line: `label` drawn in
                                  INFO_LABEL_COLOR, then `value` in
                                  `value_col`, so labels read distinctly
                                  from the values beside them

    A line can carry real story content (a target's name, an interior
    label) rather than fixed UI text, so it's wrapped (see _wrap_text) to
    fit; a two-tone line wraps its value with a hanging indent under the
    label. The panel is a fixed side_panel_width() wide so it fills its
    quarter of the window to the same edge as the Controls / Messages
    panes regardless of how long that content happens to be.

    Fixed maximum height: at most INFO_PANEL_VISIBLE_LINES wrapped lines are
    shown; a longer readout (many locations inside a targeted station, say)
    scrolls via `scroll` - a line offset clamped here, driven by the mouse
    wheel while the pointer is over the pane. `^`/`v` scroll hints show when
    there's more. Returns `(rect, max_scroll)`."""
    font = get_font(int(18 * ui_scale))
    pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
    line_height = int(22 * ui_scale)
    panel_width = side_panel_width(ui_scale)
    text_max_width = panel_width - pad_x * 2
    space_w = font.size(" ")[0]

    # Flatten every entry into rows, each a list of (surface, x_offset).
    rows = []
    for entry in lines:
        if len(entry) == 3:
            label, value, value_color = entry
            label_surf = font.render(f"{label} ", True, INFO_LABEL_COLOR)
            indent = label_surf.get_width()
            value_lines = _wrap_text(font, value, max(space_w, text_max_width - indent))
            for i, vline in enumerate(value_lines):
                value_surf = font.render(vline, True, value_color)
                if i == 0:
                    rows.append([(label_surf, 0), (value_surf, indent)])
                else:
                    rows.append([(value_surf, indent)])
        else:
            text, color = entry
            for wline in _wrap_text(font, text, text_max_width):
                rows.append([(font.render(wline, True, color), 0)])

    total = len(rows)
    visible = min(total, INFO_PANEL_VISIBLE_LINES)
    max_scroll = max(0, total - visible)
    scroll = max(0, min(scroll, max_scroll))
    scrollable = max_scroll > 0
    hint_height = font.get_height() + int(2 * ui_scale)

    panel_height = pad_y * 2 + line_height * visible + (hint_height * 2 if scrollable else 0)
    rect = pygame.Rect(0, 0, panel_width, panel_height)
    rect.topright = topright
    draw_glass_panel(surface, rect, ui_scale)

    y = rect.y + pad_y
    if scrollable:
        if scroll > 0:
            surface.blit(font.render("^ more  (scroll)", True, SCROLL_HINT_COLOR), (rect.x + pad_x, y))
        y += hint_height
    for row in rows[scroll:scroll + visible]:
        for surf, dx in row:
            surface.blit(surf, (rect.x + pad_x + dx, y))
        y += line_height
    if scrollable and scroll < max_scroll:
        surface.blit(font.render("v more  (scroll)", True, SCROLL_HINT_COLOR), (rect.x + pad_x, y))
    return rect, max_scroll


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
    A status line isn't always short, fixed UI text (the drift-far-from-
    system hint and the hail-busy message are full sentences), so each is
    wrapped (see _wrap_text) to fit within center_panel_max_width() before
    rendering - otherwise a long enough line can run wide enough to
    overlap a side panel (Controls, Messages, the minimap/info panel).
    """
    if not status_lines:
        return None
    font_status = get_font(int(22 * ui_scale))
    pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
    margin = int(10 * ui_scale)
    text_max_width = center_panel_max_width(ui_scale) - pad_x * 2
    wrapped_lines = [(line, color) for text, color in status_lines for line in _wrap_text(font_status, text, text_max_width)]
    status_rendered = [font_status.render(text, True, color) for text, color in wrapped_lines]
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


MESSAGE_LOG_VISIBLE_LINES = 7  # text lines drawn at once; the rest scroll (mouse wheel)
SCROLL_HINT_COLOR = (120, 200, 255)  # "^ newer" / "v older" arrows - a distinct blue, not the dim GRAY of older text
INFO_PANEL_VISIBLE_LINES = 8  # draw_info_panel lines shown at once before it scrolls

# Unread-message alert: the bottom-left Message Log's red light blinks
# exactly MESSAGE_ALERT_BLINKS times (on for MESSAGE_ALERT_BLINK_FRAMES,
# then off for the same) and the "ping" sound fires once at the start of
# each blink, then it goes quiet and dark. Both screens drive this off
# message_alert_timer counting down from MESSAGE_ALERT_FRAMES; the blink
# state and ping schedule come from message_alert_state() so they stay in
# sync. (Was a flat ~10s / ~14-blink wall-clock flash with a single ping.)
MESSAGE_ALERT_BLINKS = 3
MESSAGE_ALERT_BLINK_FRAMES = 21  # ~0.35s at 60fps per half-cycle (matches the old blink rate)
MESSAGE_ALERT_FRAMES = MESSAGE_ALERT_BLINKS * 2 * MESSAGE_ALERT_BLINK_FRAMES


def message_alert_state(frames_remaining):
    """Map message_alert_timer (counts down MESSAGE_ALERT_FRAMES -> 0) to
    `(blink_on, pings_due)`: whether the unread light is lit this frame, and
    how many pings should have sounded so far (0..MESSAGE_ALERT_BLINKS). The
    caller plays `pings_due` minus however many it has already played, so a
    frame-rate hitch that skips a blink still gets the right total. Returns
    `(False, MESSAGE_ALERT_BLINKS)` once the alert has run its course."""
    if frames_remaining <= 0:
        return False, MESSAGE_ALERT_BLINKS
    elapsed = MESSAGE_ALERT_FRAMES - frames_remaining
    cycle = 2 * MESSAGE_ALERT_BLINK_FRAMES
    blink_on = (elapsed % cycle) < MESSAGE_ALERT_BLINK_FRAMES
    pings_due = min(MESSAGE_ALERT_BLINKS, elapsed // cycle + 1)
    return blink_on, pings_due


def draw_message_log(surface, messages, ui_scale, scroll=0, alert=False):
    """Bottom-left glass panel of received one-way messages (see
    Possessions.add_message/message_log and SpaceScreen._check_one_way_hails),
    newest entry on top - the bottom-left counterpart to draw_status_pane
    (bottom-center) and draw_info_panel (top-right), for messages that
    arrived rather than the player's current status.

    `messages` is a list of (sender, text) tuples, already newest-first
    (see Possessions.add_message). The panel has a **fixed maximum height**:
    it grows to at most MESSAGE_LOG_VISIBLE_LINES wrapped text lines and
    then stops, so a long backlog can't push up over the Controls pane. The
    rest is reached with `scroll` - a line offset from the newest, clamped
    here - which SpaceScreen drives from the mouse wheel while the pointer
    is over this panel. `^ newer` / `v older` hints show when there's more
    in either direction.

    `alert` is this frame's on/off state for the red "unread" light (the
    caller resolves it via message_alert_state()); pass False to leave it
    dark.

    Returns `(rect, max_scroll)` so the caller can clamp its own stored
    scroll offset; returns `(None, 0)` when there are no messages yet (a
    fresh game shows no empty box - same pattern as draw_status_pane).

    box_width is the shared side_panel_width(), so this pane fills its
    quarter of the window to the same edge as the Controls / info panes."""
    if not messages:
        return None, 0
    font_title = get_font(int(16 * ui_scale))
    font_text = get_font(int(15 * ui_scale))
    pad_x, pad_y = int(12 * ui_scale), int(8 * ui_scale)
    line_height = int(18 * ui_scale)
    margin = hud_margin(ui_scale)
    box_width = side_panel_width(ui_scale)

    # Every message flattened to (line, is_newest_entry, sender_prefix) -
    # each entry wraps as one "Sender: text" unit (not sender/text
    # independently, so a short message stays on one line without a lone
    # "Sender:" above it). sender_prefix ("Sender: ") is carried on the
    # first wrapped line of each entry only, so the draw loop can pick the
    # sender name back out and style it (underlined, its own colour). The
    # newest entry's lines stay bright and the rest dim, kept as a cue even
    # after scrolling.
    flat = []
    for i, (sender, text) in enumerate(messages):
        prefix = f"{sender}: "
        for j, line in enumerate(_wrap_text(font_text, f"{sender}: {text}", box_width - pad_x * 2)):
            flat.append((line, i == 0, prefix if j == 0 else None))

    total = len(flat)
    visible = min(total, MESSAGE_LOG_VISIBLE_LINES)
    max_scroll = max(0, total - visible)
    scroll = max(0, min(scroll, max_scroll))
    scrollable = max_scroll > 0

    title_rendered = font_title.render("Message Log", True, (200, 220, 255))
    title_height = title_rendered.get_height() + int(4 * ui_scale)
    hint_height = font_text.get_height() + int(2 * ui_scale)
    # Both hint rows are reserved whenever the log is scrollable at all, so
    # the panel's height doesn't jump as the offset passes the ends - it
    # only changes with the message count, up to the visible-lines cap.
    box_height = pad_y * 2 + title_height + visible * line_height + (hint_height * 2 if scrollable else 0)

    rect = pygame.Rect(0, 0, box_width, box_height)
    rect.bottomleft = (margin, utils.screen_height - margin)
    draw_glass_panel(surface, rect, ui_scale)

    surface.blit(title_rendered, (rect.x + pad_x, rect.y + pad_y))
    # Red "unread" light in the panel's top-right corner. The caller passes
    # `alert` already resolved to this frame's on/off blink state (see
    # message_alert_state / message_alert_timer) - it blinks MESSAGE_ALERT_
    # BLINKS times in sync with the ping, then stays dark.
    if alert:
        r = max(3, int(5 * ui_scale))
        cx = rect.right - pad_x - r
        cy = rect.y + pad_y + title_rendered.get_height() // 2
        pygame.draw.circle(surface, (60, 15, 15), (cx, cy), r + max(1, int(2 * ui_scale)))
        pygame.draw.circle(surface, (255, 60, 60), (cx, cy), r)
    y = rect.y + pad_y + title_height
    if scrollable:
        if scroll > 0:
            surface.blit(font_text.render("^ newer  (scroll)", True, SCROLL_HINT_COLOR), (rect.x + pad_x, y))
        y += hint_height
    for line, is_newest, prefix in flat[scroll:scroll + visible]:
        text_color = WHITE if is_newest else GRAY
        x = rect.x + pad_x
        if prefix and line.startswith(prefix):
            # First line of an entry: draw the sender name underlined and in
            # the sender colour, then ": <message>" in the normal text colour.
            name = prefix[:-2]  # drop the ": " separator
            sender_color = MESSAGE_SENDER_COLOR if is_newest else MESSAGE_SENDER_COLOR_DIM
            font_text.set_underline(True)
            name_surf = font_text.render(name, True, sender_color)
            font_text.set_underline(False)
            surface.blit(name_surf, (x, y))
            surface.blit(font_text.render(": " + line[len(prefix):], True, text_color),
                         (x + name_surf.get_width(), y))
        else:
            surface.blit(font_text.render(line, True, text_color), (x, y))
        y += line_height
    if scrollable and scroll < max_scroll:
        surface.blit(font_text.render("v older  (scroll)", True, SCROLL_HINT_COLOR), (rect.x + pad_x, y))

    return rect, max_scroll


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

    # Thruster flame first, so the hull (or an extracted thruster port in
    # `parts`) is drawn over its root - matches Ship.draw()'s order.
    if thrust > 0.05:
        _draw_glyph_thrusters(surface, center_x, center_y, pixel_size, graphics, cos_a, sin_a, thrust)

    # A "parts" list is a complete multi-polygon silhouette (see the design
    # atlases / WorldObject.draw_parts) - when present it fully replaces the
    # base polygon and the window dots, exactly as Ship.draw does, so the
    # shop icon/preview matches the ship the player flies away in.
    parts = graphics.get("parts")
    if parts:
        _draw_glyph_parts(surface, center_x, center_y, pixel_size, parts,
                          _rotate, color, tuple(graphics.get("window_color", (200, 230, 255))))
    else:
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


def _draw_glyph_parts(surface, center_x, center_y, pixel_size, parts, rotate,
                      metal_color, glass_color):
    """Screen-pixel twin of WorldObject.draw_parts for draw_ship_glyph: each
    part's coords are fractions of the ship's "size" (pixel_size stands in
    for size here), rotated by the same `rotate` closure the base polygon
    uses. Colours resolve exactly as in-world (_resolve_part_color). No
    synthesised outline - the plate's own offset polygons/circles carry it."""
    def project(x, y):
        rx, ry = rotate(x * pixel_size, y * pixel_size)
        return (center_x + rx, center_y + ry)

    for part in parts:
        color = _resolve_part_color(part.get("color"), metal_color, glass_color)
        if "circle" in part:
            cx, cy, r = part["circle"]
            center = project(cx, cy)
            radius = max(1, round(r * pixel_size))
            ring_w = part.get("width")
            if ring_w:                       # ring: quad strip, transparent hole
                band = max(1, round(ring_w * pixel_size))
                for quad in _ring_quads(center, radius, band, max(14, min(44, radius // 2))):
                    pygame.draw.polygon(surface, color, quad)
            else:
                pygame.draw.circle(surface, color, center, radius)
        elif "line" in part:
            pts = [project(px, py) for px, py in part["line"]]
            half = max(0.6, round(part.get("width", 2) * pixel_size) / 2)
            for a, b in zip(pts, pts[1:]):
                dx, dy = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dy) or 1.0
                nx, ny = -dy / L * half, dx / L * half
                pygame.draw.polygon(surface, color, [
                    (a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                    (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)])
        else:
            pts = [project(px, py) for px, py in part.get("points", [])]
            if len(pts) >= 3:
                pygame.draw.polygon(surface, color, pts)


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
    thruster_width = graphics.get("thruster_width", 0.09)
    thruster_length = graphics.get("thruster_length", 38)
    thrust_color = tuple(graphics.get("thrust_color", YELLOW))
    world_size = graphics.get("size", 15) or 15
    flame_length = min(thrust * thruster_length * (pixel_size / world_size), pixel_size * 0.6)
    half_width = max(0.6, pixel_size * thruster_width)

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


def _rotate_points(points, center_x, center_y, angle):
    """Rotate a list of (x, y) points by `angle` radians about (center_x,
    center_y) - used by draw_item_icon's polygon-based glyphs when a caller
    passes a non-zero `angle` (e.g. a laser projectile orienting its outfit
    icon to its direction of travel)."""
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    rotated = []
    for px, py in points:
        lx, ly = px - center_x, py - center_y
        rx = lx * cos_a - ly * sin_a
        ry = lx * sin_a + ly * cos_a
        rotated.append((center_x + rx, center_y + ry))
    return rotated


def draw_item_icon(surface, center_x, center_y, size, icon_shape, icon_color, angle=0.0):
    """Draw a small procedural icon for a shop item/commodity, centered on
    (center_x, center_y) with pixel `size` roughly its radius. `icon_shape`
    selects a built-in glyph; None or any value not recognized here falls
    back to a plain crate glyph, so an item/commodity with no "icon_shape"
    configured still gets a sane default instead of nothing.

    `angle` (radians, default 0 = glyph's normal upright orientation) rotates
    the polygon-based glyphs (gem/star/blade/flame/shield) about the icon's
    own center - e.g. a fired projectile orienting its outfit's icon to its
    direction of travel (see game/world/projectile.py). The circle/rect-based
    glyphs (vial/gear/crate) ignore it; those read the same at any angle."""
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
        if angle:
            points = _rotate_points(points, center_x, center_y, angle)
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, width=1)
    elif icon_shape == "star":
        points = _star_points(center_x, center_y, size, size * 0.45, 5)
        if angle:
            points = _rotate_points(points, center_x, center_y, angle)
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, width=1)
    elif icon_shape == "blade":  # weapon outfits
        points = [
            (center_x, center_y - size * 1.1), (center_x + size * 0.25, center_y + size * 0.3),
            (center_x, center_y + size), (center_x - size * 0.25, center_y + size * 0.3),
        ]
        if angle:
            points = _rotate_points(points, center_x, center_y, angle)
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, width=1)
    elif icon_shape == "flame":  # engine outfits
        points = [
            (center_x, center_y - size), (center_x + size * 0.6, center_y + size * 0.2),
            (center_x + size * 0.3, center_y + size), (center_x, center_y + size * 0.6),
            (center_x - size * 0.3, center_y + size), (center_x - size * 0.6, center_y + size * 0.2),
        ]
        if angle:
            points = _rotate_points(points, center_x, center_y, angle)
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, width=1)
    elif icon_shape == "shield":  # shield outfits
        points = [
            (center_x - size * 0.8, center_y - size * 0.6), (center_x + size * 0.8, center_y - size * 0.6),
            (center_x + size * 0.8, center_y + size * 0.1), (center_x, center_y + size),
            (center_x - size * 0.8, center_y + size * 0.1),
        ]
        if angle:
            points = _rotate_points(points, center_x, center_y, angle)
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


def draw_button(surface, rect, label, font, ui_scale, selected=False, accent=(255, 255, 255), disabled=False):
    """A rounded dialog button. When `selected` (keyboard cursor or mouse
    hover) it fills with a translucent wash of `accent` and a bright accent
    border with white text; idle it's a faint outline with accent-coloured
    text; `disabled` is a dim, never-selectable variant (an unavailable
    choice, e.g. an exit with no ship to return to). Used by DialogBase so a
    dialog's choices read as distinct buttons rather than one line of help
    text."""
    radius = int(9 * ui_scale)
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    if disabled:
        pygame.draw.rect(surf, (255, 255, 255, 8), surf.get_rect(), border_radius=radius)
        pygame.draw.rect(surf, (90, 90, 100), surf.get_rect(), width=1, border_radius=radius)
        text_color = DISABLED_TEXT_COLOR
    elif selected:
        pygame.draw.rect(surf, (*accent, 55), surf.get_rect(), border_radius=radius)
        pygame.draw.rect(surf, accent, surf.get_rect(), width=max(2, int(2 * ui_scale)), border_radius=radius)
        text_color = WHITE
    else:
        pygame.draw.rect(surf, (255, 255, 255, 16), surf.get_rect(), border_radius=radius)
        pygame.draw.rect(surf, (140, 140, 155), surf.get_rect(), width=1, border_radius=radius)
        text_color = accent
    surface.blit(surf, rect.topleft)
    text = font.render(label, True, text_color)
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


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
