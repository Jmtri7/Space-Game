# Shared imports, geometry helpers and constants for the location_screen package.
"""Configurable location for station, moon city, and moon wilderness."""
import functools
import pygame
import math
import game.aa_draw as aa
import game.constants as constants
from game.constants import GAME_WIDTH, GAME_HEIGHT, BLACK, WHITE, YELLOW, GREEN, GRAY, CYAN, NAV_CELL
from game.utils import get_scale, load_json, to_screen, to_world, draw_debug_marker, draw_target_brackets, get_ui_scale, get_font, set_camera_offset, set_camera_angle, set_camera_zoom, set_camera_zoom_limits, get_building_type, get_culture, get_ship_type, get_graphics_asset, get_story, get_missions
import game.utils as utils
from game.perf_metrics import metrics as perf
from game.audio.sound_board import sound_board
from game.ui.ui_theme import draw_controls_pane, draw_status_pane, draw_info_panel, draw_glass_panel, draw_message_log, draw_glow_message, center_panel_max_width, MESSAGE_ALERT_FRAMES, message_alert_state
from game.screens.screen_base import ScreenBase
from game.world.world_object import draw_parts
from game.world.character import Character, resolve_routine_class
from game.world.person import Person
from game.world.dialogue import Dialogue, option_actions, apply_shared_actions, shared_action_blocked_reason
from game.world.mission import start_mission
from game.world.player_character import PlayerCharacter
from game.world.content_gate import passes_content_gate
from game.world.follow_player_routine import FollowPlayerRoutine
from game.world.indoor_pathfinder import IndoorPathfinder, NavGrid
from game.world.starfield import StarField
from game.graphics.deck_grid import grid_segments as _grid_segments, tessellate as _tessellate


# Frames an interior message banner stays lit after a message arrives (see
# _refresh_messages). MESSAGE_ALERT_FRAMES (the unread light's lifetime) and
# its blink/ping schedule live in ui_theme now - imported above - so the
# space view and interiors share exactly one definition.
MESSAGE_BANNER_FRAMES = 300   # ~5s


# Default vertex count for a "circle"-shaped room/decoration - a regular
# polygon with this many sides reads as round at interior zoom while still
# being a plain polygon everywhere else (movement, pathfinding, drawing).
CIRCLE_SIDES = 28


def _regular_polygon(cx, cy, radius, sides):
    """`sides` points evenly spaced on a circle - the concrete geometry
    behind a `"shape": "circle"` room or decoration."""
    return [
        (cx + radius * math.cos(2 * math.pi * i / sides - math.pi / 2),
         cy + radius * math.sin(2 * math.pi * i / sides - math.pi / 2))
        for i in range(sides)
    ]


def normalize_room(cfg):
    """One interior room config -> {"polygon": [(x, y), ...], "label": str|None}.

    Accepts three authoring shapes, so old rect layouts and new polygon /
    near-circular ones all end up as a single polygon the rest of the
    class handles uniformly:
      - {"polygon": [[x, y], ...]}         used as-is (>= 3 vertices)
      - {"rect": [x, y, w, h]}             the pre-polygon shape, kept working
      - {"shape": "circle", "center": [x, y], "radius": r, "sides": n}
                                           regular n-gon (n defaults to CIRCLE_SIDES)
    """
    label = cfg.get("label")
    if "polygon" in cfg:
        poly = [(float(x), float(y)) for x, y in cfg["polygon"]]
    elif cfg.get("shape") == "circle":
        cx, cy = cfg["center"]
        poly = _regular_polygon(cx, cy, cfg["radius"], cfg.get("sides", CIRCLE_SIDES))
    else:
        x, y, w, h = cfg["rect"]
        poly = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return {"polygon": poly, "label": label, "bounds": _polygon_bounds(poly)}


def normalize_decoration(cfg):
    """One cosmetic decoration config -> a dict with a resolved point list.

    Shapes: "polygon" (points), "rect" ([x,y,w,h]), "circle" (center+radius),
    "line" (points, always stroked). `layer` is "floor" (drawn on top of the
    floor) or "wall" (drawn on the wall fill, behind the floor). `width` 0
    fills the shape; > 0 strokes it at that line width. Purely visual - no
    collision, never depth-sorted against people.
    """
    shape = cfg.get("shape", "polygon")
    if shape == "rect":
        x, y, w, h = cfg["rect"]
        points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    elif shape == "circle":
        cx, cy = cfg["center"]
        points = _regular_polygon(cx, cy, cfg["radius"], cfg.get("sides", CIRCLE_SIDES))
    else:  # polygon / line
        points = [(float(x), float(y)) for x, y in cfg["points"]]
    return {
        "shape": shape,
        "layer": cfg.get("layer", "floor"),
        "points": points,
        "color": tuple(cfg.get("color", (255, 255, 255))),
        "width": cfg.get("width", 0),
    }


def point_in_polygon(x, y, poly):
    """Even-odd ray cast, with a point on any edge counted as inside - so a
    step that lands exactly on the seam between two overlapping rooms is
    valid in at least one of them instead of falling through the crack."""
    n = len(poly)
    j = n - 1
    inside = False
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        # On-segment test (within ~half a pixel) - boundary counts as inside.
        cross = (xj - xi) * (y - yi) - (yj - yi) * (x - xi)
        if abs(cross) < 1.0 and min(xi, xj) - 0.5 <= x <= max(xi, xj) + 0.5 and min(yi, yj) - 0.5 <= y <= max(yi, yj) + 0.5:
            return True
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def _polygon_bounds(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def _silhouette_local_bounds(building_type):
    """(min_x, min_y, max_x, max_y) of a building_type's drawn silhouette in
    its own local space (anchor at 0,0; +y downward, so max_y is the base
    the object sits on). Reads the real geometry that gets drawn - the
    `parts` list first (see WorldObject.draw_parts), then `local_points`,
    then `width`/`height` (rect) or `radius` (circle) - because a stale
    `height` on a `parts`-authored building can overstate the drawn extent
    by tens of units, and the collision footprint is anchored to this
    (see _building_footprint)."""
    parts = building_type.get("parts")
    xs, ys = [], []
    if parts:
        for part in parts:
            if "circle" in part:
                cx, cy, r = part["circle"]
                xs += [cx - r, cx + r]
                ys += [cy - r, cy + r]
            else:
                for px, py in part.get("points") or part.get("line") or []:
                    xs.append(px)
                    ys.append(py)
    if not xs:
        pts = building_type.get("local_points")
        if pts:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
    if not xs:
        if building_type.get("shape") == "circle":
            r = building_type.get("radius", 50)
            return (-r, -r, r, r)
        w, h = building_type.get("width", 100), building_type.get("height", 100)
        return (0.0, 0.0, float(w), float(h))
    return (min(xs), min(ys), max(xs), max(ys))


@functools.lru_cache(maxsize=256)
def _silhouette_local_bounds_for(story, building_type_id):
    """Cached `_silhouette_local_bounds` keyed by id - a building type's drawn
    extent never changes at runtime, and it was being re-derived (re-scanning
    the whole `parts` list) for every structure every frame in the depth sort
    and the viewport cull."""
    return _silhouette_local_bounds(get_building_type(story, building_type_id))


def _polygon_centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def _inset_polygon(poly, inset):
    """Each vertex pulled `inset` world units toward the polygon's centroid -
    a cheap approximation of a true offset, good enough for tracing a
    decorative line just inside a room's edge."""
    cx, cy = _polygon_centroid(poly)
    out = []
    for x, y in poly:
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy) or 1.0
        f = min(1.0, inset / d)
        out.append((x + dx * f, y + dy * f))
    return out


def _clamp_rgb(c):
    return tuple(max(0, min(255, int(round(v)))) for v in c)


def _scale_rgb(c, f):
    return _clamp_rgb((c[0] * f, c[1] * f, c[2] * f))


def _mix_rgb(a, b, t):
    return _clamp_rgb((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t))


def _edge_ticks(poly, spacing, length):
    """Short segments straddling each polygon edge every `spacing` units -
    the geometry behind the "seam_rivets" culture decoration."""
    ticks = []
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        seg_len = math.hypot(x2 - x1, y2 - y1)
        if seg_len < 1:
            continue
        ux, uy = (x2 - x1) / seg_len, (y2 - y1) / seg_len
        px, py = -uy, ux
        d = spacing
        while d < seg_len:
            mx, my = x1 + ux * d, y1 + uy * d
            ticks.append([(mx - px * length / 2, my - py * length / 2), (mx + px * length / 2, my + py * length / 2)])
            d += spacing
    return ticks


# Fallback loan size when story.json defines no "loan" block. Bumped way up
# from the old "shuttle's cost" amount so a single loan covers any ship/
# outfit combo without grinding for credits first - revisit before treating
# this as real game balance. A story sets its own lender/amount/max_active
# in story.json's "loan" block (see _loan_terms).
DEFAULT_LOAN_AMOUNT = 100_000


# Export everything (including single-underscore helpers) so the
# sibling mixin modules get it all via `from ..._defs import *`.
__all__ = [_n for _n in dir() if not _n.startswith("__")]
