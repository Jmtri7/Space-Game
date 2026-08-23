"""Base class for NPCs and other characters in the game."""
import pygame
import math
from utils import to_screen, get_scale


class Person:
    """Base class for NPCs and other characters in the game."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.wander_time = 0
        self.wander_x = 0
        self.wander_y = 0

    def draw(self, surface):
        scale = get_scale()
        pygame.draw.rect(surface, (200, 100, 100), (*to_screen(self.x - 6, self.y), to_screen_x(12), to_screen_y(16)))
        pygame.draw.circle(surface, (255, 150, 150), to_screen(self.x, self.y - 6), max(1, int(5 * scale)))

    def get_distance(self, px, py):
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)


def to_screen_x(x):
    """Convert world X coordinate to screen space."""
    from utils import get_scale
    scale = get_scale()
    return int(round(x * scale))


def to_screen_y(y):
    """Convert world Y coordinate to screen space."""
    from utils import get_scale
    scale = get_scale()
    return int(round(y * scale))
