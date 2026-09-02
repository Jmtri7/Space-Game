"""Base class for positioned, drawable objects in the game world."""
import math
import pygame
import game.aa_draw as aa
from game.utils import to_screen, get_scale, screen_affine


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


def draw_parts(surface, parts, ox, oy, angle, unit, metal_color, glass_color):
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
    (see the design atlases). Colours resolve via _resolve_part_color: an
    [r,g,b], "#rrggbb", "metal", "glass", or "shade:<n>".

    The list is drawn back-to-front with **no synthesised outline of any
    kind** - it's exactly the polygons and circles the atlas plate draws, and
    an outline there is already its own slightly-larger polygon/circle part
    sitting behind the fill (see docs/atlases/extract_atlas.py). So the
    in-game silhouette matches the plate primitive-for-primitive, and the
    outline scales with the shape instead of being a fixed-pixel border that
    swallows a small ship's nose."""
    if not parts:
        return
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    scale = get_scale()

    aff = screen_affine()
    if aff and not angle:
        # unrotated: fold ox/oy, unit and the camera transform into two
        # multiply-adds - project() is called ~100 times per building.
        a, tx, ty = aff
        _m, _bx, _by = unit * a, ox * a + tx, oy * a + ty

        def project(x, y):
            return (round(x * _m + _bx), round(y * _m + _by))
    else:
        def project(x, y):
            x, y = x * unit, y * unit
            return to_screen(ox + (x * cos_a - y * sin_a), oy + (x * sin_a + y * cos_a))

    def thick_seg(p, q, half):
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L * half, dx / L * half
        return [(p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny),
                (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)]

    for part in parts:
        color = _resolve_part_color(part.get("color"), metal_color, glass_color)
        if "circle" in part:
            cx, cy, r = part["circle"]
            center = project(cx, cy)
            radius = max(1, int(round(r * unit * scale)))
            ring_w = part.get("width")
            if ring_w:
                band = max(1.0, ring_w * unit * scale)
                segs = max(14, min(44, int(radius / 2.2)))
                for quad in _ring_quads(center, radius, band, segs):
                    aa.polygon(surface, color, quad)
            else:
                aa.circle(surface, color, center, radius)
        elif "line" in part:
            pts = [project(px, py) for px, py in part["line"]]
            half = max(0.6, part.get("width", 2) * unit * scale / 2)
            for a, b in zip(pts, pts[1:]):
                aa.polygon(surface, color, thick_seg(a, b, half))
        else:
            pts = [project(px, py) for px, py in part.get("points", [])]
            if len(pts) >= 3:
                aa.polygon(surface, color, pts)


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
            aa.polygon(surface, outline_color, outline_points)

        aa.polygon(surface, color, points)
        return points

    def _draw_parts(self, surface, parts, angle, unit, metal_color, glass_color):
        """Composite "parts" detail about this object's own (x, y) - see the
        module-level draw_parts()."""
        draw_parts(surface, parts, self.x, self.y, angle, unit, metal_color,
                   glass_color)
