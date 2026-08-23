"""Moon celestial object."""
import pygame
import math
import constants
from constants import GREEN
from utils import get_scale, to_screen


class Moon:
    """A celestial moon object in space."""
    def __init__(self, x, y, graphics=None):
        self.x = x
        self.y = y
        self.phase = 0

        # Load graphics from config or use defaults
        if graphics:
            self.size = graphics.get("size", 30)
            self.color = tuple(graphics.get("color", [200, 200, 200]))
            self.crater_color = tuple(graphics.get("crater_color", [150, 150, 150]))
            self.craters = graphics.get("craters", [])
            self.landing_distance = graphics.get("landing_distance", self.size * 3.5)
        else:
            self.size = 30
            self.color = (200, 200, 200)
            self.crater_color = (150, 150, 150)
            self.craters = [
                {"x": -8, "y": -5, "radius": 4},
                {"x": 10, "y": 8, "radius": 5}
            ]
            self.landing_distance = 35

    def update(self):
        self.phase = (self.phase + 0.1) % 360

    def draw(self, surface):
        scale = get_scale()
        pygame.draw.circle(surface, self.color, to_screen(self.x, self.y), max(1, int(round(self.size * scale))))
        # Draw craters
        for crater in self.craters:
            crater_x = self.x + crater.get("x", 0)
            crater_y = self.y + crater.get("y", 0)
            crater_radius = crater.get("radius", 4)
            pygame.draw.circle(surface, self.crater_color, to_screen(crater_x, crater_y), max(1, int(crater_radius * scale)))

        # Debug: draw landing radius circle
        if constants.DEBUG_MODE:
            landing_radius_screen = int(self.landing_distance * scale)
            pygame.draw.circle(surface, GREEN, to_screen(self.x, self.y), landing_radius_screen, 1)

    def get_distance(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)
