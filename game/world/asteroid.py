"""Small drifting asteroid with constant velocity."""
import pygame
from game.constants import GRAY
from game.utils import get_scale, to_screen
from game.world.world_object import WorldObject


class Asteroid(WorldObject):
    """An asteroid that drifts at a constant velocity."""
    def __init__(self, x, y, velocity_x=0, velocity_y=0, size=4, graphics=None):
        super().__init__(x, y, graphics=graphics)
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.size = size
        self.color = tuple(self.graphics.get("color", GRAY))

    def update(self):
        """Drift at constant velocity."""
        self.x += self.velocity_x
        self.y += self.velocity_y

    def draw(self, surface):
        scale = get_scale()
        radius = max(1, int(round(self.size * scale)))
        pygame.draw.circle(surface, self.color, to_screen(self.x, self.y), radius)
