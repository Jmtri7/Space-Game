"""Procedurally generated star field background."""
import pygame
import random
from constants import GAME_WIDTH, GAME_HEIGHT
from utils import to_screen


class StarField:
    """Procedurally generated star field background."""
    def __init__(self, num_stars=200):
        self.num_stars = num_stars
        self.stars = []
        self.generate_stars()

    def generate_stars(self):
        self.stars = []
        random.seed(42)
        for _ in range(self.num_stars):
            x = random.randint(0, GAME_WIDTH)
            y = random.randint(0, GAME_HEIGHT)
            brightness = random.randint(100, 255)
            self.stars.append((x, y, brightness))

    def draw(self, surface):
        for x, y, brightness in self.stars:
            pygame.draw.circle(surface, (brightness, brightness, brightness), to_screen(x, y), 1)
