"""Base class for positioned, drawable objects in the game world."""
import math
import pygame
from game.utils import to_screen, get_scale


def expand_polygon(pts, d, miter_limit=2.0):
    """Screen-space outward offset: every edge pushed out by a constant d
    pixels, so the outline is the same thickness on every side (a tall thin
    shape doesn't get a top-heavy border). Same technique the design atlases
    use - an outline is a larger copy of the shape drawn behind it, never a
    stroke - so the in-game silhouettes match the plates primitive-for-
    primitive (polygons + circles, no strokes).

    Corners are mitred; a corner too sharp to mitre within `miter_limit`*d is
    bevelled (a point per edge) instead. Without that, a pointed shape - a
    blade tip, a thruster nozzle, a tapered wedge - grows a long spike out
    its point (and on a rotating hull the spike sweeps around with it). The
    offset direction is taken from the polygon's signed area, not a
    distance-to-centroid guess on one vertex, so it never depends on how the
    shape happens to be rotated on screen."""
    n = len(pts)
    if n < 3:
        return pts
    area2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
               for i in range(n))
    sgn = 1.0 if area2 > 0 else -1.0

    def edge_normal(p, q):
        ux, uy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(ux, uy)
        if L < 1e-9:
            return None
        return (sgn * uy / L, -sgn * ux / L)

    out = []
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        n1 = edge_normal(a, b)
        n2 = edge_normal(b, c)
        if n1 is None and n2 is None:
            out.append(b)
            continue
        if n1 is None or n2 is None:
            nn = n1 or n2
            out.append((b[0] + nn[0] * d, b[1] + nn[1] * d))
            continue
        mx, my = n1[0] + n2[0], n1[1] + n2[1]
        ml = math.hypot(mx, my)
        cosv = (mx / ml) * n1[0] + (my / ml) * n1[1] if ml > 1e-9 else 0.0
        if cosv < 1.0 / miter_limit:                 # too sharp (or reflex): bevel
            out.append((b[0] + n1[0] * d, b[1] + n1[1] * d))
            out.append((b[0] + n2[0] * d, b[1] + n2[1] * d))
        else:
            out.append((b[0] + mx / ml * d / cosv, b[1] + my / ml * d / cosv))
    return out


def _ring_quads(center, r, band, segs):
    """A torus as `segs` radial quads - hole stays genuinely transparent
    (nothing is painted in the centre), matching the plates' ring_strip."""
    cx, cy = center
    r_in, r_out = max(0.5, r - band / 2), r + band / 2
    out = []
    for k in range(segs):
        a0 = 2 * math.pi * k / segs
        a1 = 2 * math.pi * (k + 1) / segs
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        out.append([(cx + r_in * c0, cy + r_in * s0), (cx + r_out * c0, cy + r_out * s0),
                    (cx + r_out * c1, cy + r_out * s1), (cx + r_in * c1, cy + r_in * s1)])
    return out


def draw_parts(surface, parts, ox, oy, angle, unit, metal_color, glass_color,
               outline_color=(12, 10, 16)):
    """Draw a composite-shape "parts" list about world point (ox, oy). Each
    part is one of:
      {"points": [[x, y], ...], "color": <c>}   filled polygon
      {"circle": [cx, cy, r], "color": <c>}     filled circle
      {"circle": [cx, cy, r], "color": <c>, "width": w}  ring (annulus), hole
                                                        stays transparent
      {"line": [[x1, y1], ...], "color": <c>, "width": w}  polyline

    Coords (and a line's `width`) are multiplied by `unit` - 1 for a
    building's absolute local units, `size` for a ship/station whose base
    points are fractions of size - then rotated `angle` degrees. Lets one
    config entry carry the multi-polygon designs a single base shape can't
    (see the design atlases). Colours (`color`, and an optional per-part
    `outline` - `"none"` to omit it, else defaults to `outline_color`)
    resolve via _resolve_part_color: an [r,g,b], "#rrggbb", "metal",
    "glass", or "shade:<n>".

    Drawn strokelessly - only filled polygons and circles, no pygame stroke
    calls - so it renders by the same rules as the design atlases: an
    outline is a larger copy of the shape behind it, a ring is a quad strip,
    a line is a thin quad."""
    if not parts:
        return
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    scale = get_scale()

    def project(x, y):
        x, y = x * unit, y * unit
        return to_screen(ox + (x * cos_a - y * sin_a), oy + (x * sin_a + y * cos_a))

    # Outline thickness: normally a fixed screen amount, but capped at ~2% of
    # a shape's *own* on-screen diagonal. Without the cap a small ship
    # (vherathi_skiff, size 10) or a small sub-part (a nozzle) gets an outline
    # as fat as a size-48 hull - it swallows the shape's point and reads like
    # a heavy stroke instead of the thin offset the atlases use.
    base_outline_w = max(1.0, 1.6 * scale)

    def outline_for(scr_pts):
        xs = [p[0] for p in scr_pts]
        ys = [p[1] for p in scr_pts]
        diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
        return max(1.0, min(base_outline_w, 0.02 * diag))

    def thick_seg(p, q, half):
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L * half, dx / L * half
        return [(p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny),
                (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)]

    for part in parts:
        color = _resolve_part_color(part.get("color"), metal_color, glass_color)
        ol_spec = part.get("outline")
        if ol_spec == "none":
            ol = None
        elif ol_spec is not None:
            ol = _resolve_part_color(ol_spec, metal_color, glass_color)
        else:
            ol = outline_color
        if "circle" in part:
            cx, cy, r = part["circle"]
            center = project(cx, cy)
            radius = max(1, int(round(r * unit * scale)))
            ring_w = part.get("width")
            if ring_w:
                band = max(1.0, ring_w * unit * scale)
                segs = max(14, min(44, int(radius / 2.2)))
                for quad in _ring_quads(center, radius, band, segs):
                    pygame.draw.polygon(surface, color, quad)
            else:
                if ol:
                    ow = max(1.0, min(base_outline_w, 0.04 * radius))
                    pygame.draw.circle(surface, ol, center, radius + max(1, int(round(ow))))
                pygame.draw.circle(surface, color, center, radius)
        elif "line" in part:
            pts = [project(px, py) for px, py in part["line"]]
            half = max(0.6, part.get("width", 2) * unit * scale / 2)
            for a, b in zip(pts, pts[1:]):
                pygame.draw.polygon(surface, color, thick_seg(a, b, half))
        else:
            pts = [project(px, py) for px, py in part.get("points", [])]
            if len(pts) >= 3:
                if ol:
                    pygame.draw.polygon(surface, ol, expand_polygon(pts, outline_for(pts)))
                pygame.draw.polygon(surface, color, pts)


def _resolve_part_color(spec, metal_color, glass_color):
    """A part's "color": an [r,g,b], a "#rrggbb" hex string, or one of the
    names "metal" / "glass", or "shade:<n>" (metal nudged n per channel).
    Defaults to metal."""
    if isinstance(spec, str):
        if spec == "metal":
            return tuple(metal_color)
        if spec == "glass":
            return tuple(glass_color)
        if spec.startswith("shade:"):
            try:
                d = int(spec[6:])
            except ValueError:
                d = 0
            return tuple(max(0, min(255, c + d)) for c in metal_color)
        if spec.startswith("#"):
            return tuple(pygame.Color(spec))[:3]
    if spec:
        return tuple(spec)
    return tuple(metal_color)


class WorldObject:
    """Base class for anything with a position in the game world (ships, landing sites)."""
    def __init__(self, x, y, graphics=None):
        self.x = x
        self.y = y
        self.graphics = graphics or {}

    def get_distance(self, target_x, target_y):
        """Calculate distance from this object to a point."""
        dx = target_x - self.x
        dy = target_y - self.y
        return math.sqrt(dx * dx + dy * dy)

    def _draw_rotated_polygon(self, surface, local_points, angle, color, outline_color=None, outline_width=2):
        """Rotate local_points by angle (degrees) around (x, y), draw as a filled polygon.

        If outline_color is given, it's drawn as a slightly larger filled
        polygon underneath the fill, rather than stroked along the fill's own
        edge - mainly for ships, so overlapping hulls of similar hue stay
        visually distinct instead of blending into one shape. Stroking the
        exact fill points doesn't miter sharp corners, which lets the fill's
        points (e.g. a ship's nose) poke out past the outline; expanding the
        underlying polygon outward from the local origin avoids that.

        Returns the projected screen-space points, in case the caller needs them
        (e.g. to anchor further drawing like a thrust flame) alongside cos/sin.
        """
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        points = []
        for lx, ly in local_points:
            rotated_x = lx * cos_a - ly * sin_a
            rotated_y = lx * sin_a + ly * cos_a
            points.append(to_screen(self.x + rotated_x, self.y + rotated_y))

        if outline_color:
            margin = outline_width / get_scale()
            outline_points = []
            for lx, ly in local_points:
                dist = math.hypot(lx, ly) or 1
                ox = lx * (dist + margin) / dist
                oy = ly * (dist + margin) / dist
                rotated_x = ox * cos_a - oy * sin_a
                rotated_y = ox * sin_a + oy * cos_a
                outline_points.append(to_screen(self.x + rotated_x, self.y + rotated_y))
            pygame.draw.polygon(surface, outline_color, outline_points)

        pygame.draw.polygon(surface, color, points)
        return points

    def _draw_parts(self, surface, parts, angle, unit, metal_color, glass_color,
                    outline_color=(12, 10, 16)):
        """Composite "parts" detail about this object's own (x, y) - see the
        module-level draw_parts()."""
        draw_parts(surface, parts, self.x, self.y, angle, unit, metal_color,
                   glass_color, outline_color)
