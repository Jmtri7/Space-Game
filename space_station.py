"""Space station object."""
import pygame
import math
import constants
from constants import GREEN
from utils import get_scale, to_screen, get_offset, load_json


class SpaceStation:
    """A rotating space station in the game world."""
    def __init__(self, x, y, graphics=None):
        self.x = x
        self.y = y
        self.rotation = 0

        # Load graphics from config or use defaults
        if graphics:
            self.size = graphics.get("size", 40)
            self.color = tuple(graphics.get("color", [100, 200, 255]))
            self.core_color = tuple(graphics.get("core_color", [150, 220, 255]))
            self.rotation_speed = graphics.get("rotation_speed", 0.5)
            self.local_points = graphics.get("local_points", self._default_points())
            self.landing_distance = graphics.get("landing_distance", self.size * 3.5)
        else:
            self.size = 40
            self.color = (100, 200, 255)
            self.core_color = (150, 220, 255)
            self.rotation_speed = 0.5
            self.local_points = self._default_points()
            self.landing_distance = 50

    def _default_points(self):
        """Default hexapod shape."""
        size = self.size
        return [
            (0, -size * 0.8),
            (size * 0.4, -size * 0.3),
            (size * 0.5, size * 0.3),
            (size * 0.2, size * 0.6),
            (-size * 0.2, size * 0.6),
            (-size * 0.5, size * 0.3),
            (-size * 0.4, -size * 0.3),
        ]

    def update(self):
        self.rotation = (self.rotation + self.rotation_speed) % 360

    def draw(self, surface):
        scale = get_scale()
        rad = math.radians(self.rotation)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        points = []
        for lx, ly in self.local_points:
            rotated_x = lx * cos_a - ly * sin_a
            rotated_y = lx * sin_a + ly * cos_a
            points.append(to_screen(self.x + rotated_x, self.y + rotated_y))

        pygame.draw.polygon(surface, self.color, points)
        pygame.draw.circle(surface, self.core_color, to_screen(self.x, self.y), max(1, int(round(self.size * 0.25 * scale))))

        # Debug: draw landing radius circle
        if constants.DEBUG_MODE:
            landing_radius_screen = int(self.landing_distance * scale)
            pygame.draw.circle(surface, GREEN, to_screen(self.x, self.y), landing_radius_screen, 1)

    def get_distance(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)
