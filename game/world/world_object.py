"""Base class for positioned, drawable objects in the game world."""
import math
import pygame
import game.aa_draw as aa
from game.utils import to_screen, get_scale, screen_affine


def _longest_circular_run(mask):
    """Indices of the longest contiguous True stretch in a circular boolean
    list, in ring order - used to pick which arc of an asteroid's silhouette
    a light/dark shading band should hug."""
    n = len(mask)
    if all(mask):
        return list(range(n))
    if not any(mask):
        return []
    start = mask.index(False)
    order = [(start + i) % n for i in range(n)]
    best, cur = [], []
    for i in order:
        if mask[i]:
            cur.append(i)
            if len(cur) > len(best):
                best = cur[:]
        else:
            cur = []
    return best


def _chaikin_open(chain, iters=1):
    """Corner-cutting subdivision of an open polyline; the two endpoints stay
    put, every interior corner is rounded off - same idea as expand.py's
    `_chaikin_open`, duplicated here to keep world_object shading
    independent of the design-JSON pipeline."""
    for _ in range(iters):
        if len(chain) < 3:
            break
        out = [chain[0]]
        for i in range(len(chain) - 1):
            ax, ay = chain[i]
            bx, by = chain[i + 1]
            out.append((0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by))
            out.append((0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by))
        out.append(chain[-1])
        chain = out
    return chain


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
    kind** - it's exactly the polygons and circles the design defines, and an
    outline (where one exists) is already its own slightly-larger
    polygon/circle part sitting behind the fill. So the in-game silhouette
    matches the design primitive-for-primitive, and the outline scales with
    the shape instead of being a fixed-pixel border that swallows a small
    ship's nose."""
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
            # floats straight through - pygame.draw.polygon/circle take them,
            # gfxdraw mode (aa_draw) rounds internally. Saves ~2 round() per
            # vertex over the ~100 vertices a building emits each frame.
            return (x * _m + _bx, y * _m + _by)
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

    def _draw_shaded_polygon(self, surface, local_points, angle, color, light_dir=(-0.6, -0.75)):
        """Base fill plus a light and a dark crescent - the same "silhouette
        edge pulled inward by a tapered, corner-cut depth profile" technique
        person/article shading uses (`expand.py`'s `_crescent`), simplified
        for an asteroid's near-convex ring (no interior ray-casting needed):
        each band hugs whichever stretch of `local_points` faces toward/away
        from a fixed world-space `light_dir` (so the shading stays put as the
        shape spins - a rock, not a searchlight), swells at the stretch's
        middle and tapers to nothing at both ends, with its inner edge
        corner-cut (Chaikin) so a coarse ring does not facet the shade. Reads
        as a smoothly lit curved rock rather than flat center->edge facets."""
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        lx, ly = light_dir
        l_len = math.hypot(lx, ly) or 1
        lx, ly = lx / l_len, ly / l_len

        rotated = [(lpx * cos_a - lpy * sin_a, lpx * sin_a + lpy * cos_a) for lpx, lpy in local_points]
        n = len(rotated)
        if n < 3:
            return
        cx = sum(p[0] for p in rotated) / n
        cy = sum(p[1] for p in rotated) / n
        radius = sum(math.hypot(px - cx, py - cy) for px, py in rotated) / n or 1.0

        screen_pts = [to_screen(self.x + rx, self.y + ry) for rx, ry in rotated]
        aa.polygon(surface, color, screen_pts)

        max_depth = radius * 0.55
        for sign, tint in ((1, 45), (-1, -45)):
            run = _longest_circular_run([
                ((rx - cx) / (math.hypot(rx - cx, ry - cy) or 1)) * lx * sign
                + ((ry - cy) / (math.hypot(rx - cx, ry - cy) or 1)) * ly * sign > 0.05
                for rx, ry in rotated
            ])
            if len(run) < 2:
                continue
            m = len(run)
            inner = []
            for k, i in enumerate(run):
                rx, ry = rotated[i]
                onx, ony = (rx - cx) / radius, (ry - cy) / radius
                taper = math.sin(math.pi * (k + 0.5) / m)
                depth = max_depth * taper
                inner.append((rx - onx * depth, ry - ony * depth))
            inner = _chaikin_open(inner, 2)
            band = [screen_pts[i] for i in run] + [to_screen(self.x + px, self.y + py) for px, py in reversed(inner)]
            shaded = tuple(max(0, min(255, c + tint)) for c in color)
            aa.polygon(surface, shaded, band)

    def _draw_parts(self, surface, parts, angle, unit, metal_color, glass_color):
        """Composite "parts" detail about this object's own (x, y) - see the
        module-level draw_parts()."""
        draw_parts(surface, parts, self.x, self.y, angle, unit, metal_color,
                   glass_color)
