"""Base class for positioned, drawable objects in the game world."""
import math
import pygame
from game.utils import to_screen, get_scale


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
