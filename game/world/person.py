"""Base class for NPCs and other characters in the game."""
import pygame
import math
from game.utils import to_screen, to_screen_x, to_screen_y, get_scale


class Person:
    """Base class for anyone with a position and a body - the player's own
    walking self (see PlayerCharacter), NPCs, and a ship's pilot all share
    this identity regardless of whether they currently have a ship."""
    def __init__(self, x, y, name=""):
        self.x = x
        self.y = y
        self.name = name

    def draw(self, surface):
        scale = get_scale()
        pygame.draw.rect(surface, (200, 100, 100), (*to_screen(self.x - 6, self.y), to_screen_x(12), to_screen_y(16)))
        pygame.draw.circle(surface, (255, 150, 150), to_screen(self.x, self.y - 6), max(1, int(5 * scale)))

    def get_distance(self, px, py):
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)
