"""Base class for positioned, drawable objects in the game world."""
import math
import pygame
from constants import GAME_WIDTH, GAME_HEIGHT
from utils import to_screen


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

    def wrap_position(self):
        """Wrap position at world edges (torus topology)."""
        if self.x < 0:
            self.x = GAME_WIDTH
        elif self.x > GAME_WIDTH:
            self.x = 0
        if self.y < 0:
            self.y = GAME_HEIGHT
        elif self.y > GAME_HEIGHT:
            self.y = 0

    def _draw_rotated_polygon(self, surface, local_points, angle, color):
        """Rotate local_points by angle (degrees) around (x, y), draw as a filled polygon.

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

        pygame.draw.polygon(surface, color, points)
        return points
