"""Base class for positioned, drawable objects in the game world."""
import math
import pygame
from game.utils import to_screen, get_scale


def draw_parts(surface, parts, ox, oy, angle, unit, metal_color, glass_color,
               outline_color=(12, 10, 16)):
    """Draw a composite-shape "parts" list about world point (ox, oy). Each
    part is one of:
      {"points": [[x, y], ...], "color": <c>}   filled polygon
      {"circle": [cx, cy, r], "color": <c>}     filled circle
      {"line": [[x1, y1], ...], "color": <c>, "width": w}  polyline

    Coords (and a line's `width`) are multiplied by `unit` - 1 for a
    building's absolute local units, `size` for a ship/station whose base
    points are fractions of size - then rotated `angle` degrees. Lets one
    config entry carry the multi-polygon designs a single base shape can't
    (see the design atlases). Colours resolve via _resolve_part_color:
    an [r,g,b], "metal", "glass", or "shade:<n>"."""
    if not parts:
        return
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    scale = get_scale()
    outline_w = max(1, int(round(1.6 * scale)))

    def project(x, y):
        x, y = x * unit, y * unit
        return to_screen(ox + (x * cos_a - y * sin_a), oy + (x * sin_a + y * cos_a))

    for part in parts:
        color = _resolve_part_color(part.get("color"), metal_color, glass_color)
        if "circle" in part:
            cx, cy, r = part["circle"]
            center = project(cx, cy)
            radius = max(1, int(round(r * unit * scale)))
            pygame.draw.circle(surface, color, center, radius)
            pygame.draw.circle(surface, outline_color, center, radius, outline_w)
        elif "line" in part:
            pts = [project(px, py) for px, py in part["line"]]
            if len(pts) >= 2:
                pygame.draw.lines(surface, color, False, pts,
                                  max(1, int(round(part.get("width", 2) * unit * scale))))
        else:
            pts = [project(px, py) for px, py in part.get("points", [])]
            if len(pts) >= 3:
                pygame.draw.polygon(surface, color, pts)
                pygame.draw.polygon(surface, outline_color, pts, outline_w)


def _resolve_part_color(spec, metal_color, glass_color):
    """A part's "color": an [r,g,b], or one of the names "metal" / "glass",
    or "shade:<n>" (metal nudged by n per channel). Defaults to metal."""
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
    if spec:
        return tuple(spec)
    return tuple(metal_color)


class WorldObject:
    """Base class for anything with a position in the game world (ships, landables)."""
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

    def _draw_parts(self, surface, parts, angle, unit, metal_color, glass_color):
        """Composite "parts" detail about this object's own (x, y) - see the
        module-level draw_parts()."""
        draw_parts(surface, parts, self.x, self.y, angle, unit, metal_color, glass_color)
