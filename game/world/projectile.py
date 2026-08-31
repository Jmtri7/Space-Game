"""Laser projectile fired from the player's ship."""
import math
from game.utils import to_screen, get_scale
from game.world.world_object import WorldObject


PROJECTILE_SPEED = 15  # world units/frame
PROJECTILE_SIZE = 2
PROJECTILE_LIFETIME = 200  # frames before despawn
PROJECTILE_DAMAGE = 3


class Projectile(WorldObject):
    """A laser projectile fired by the player ship. Travels in a straight
    line and despawns after a set lifetime or on collision."""
    def __init__(self, x, y, velocity_x, velocity_y):
        super().__init__(x, y)
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.lifetime = PROJECTILE_LIFETIME
        self.damage = PROJECTILE_DAMAGE

    def update(self):
        """Move projectile; return False if expired."""
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.lifetime -= 1
        return self.lifetime > 0

    def draw(self, surface):
        """Draw as a small cyan dot with a trailing line."""
        scale = get_scale()
        screen_x, screen_y = to_screen(self.x, self.y)
        radius = max(1, int(round(PROJECTILE_SIZE * scale)))

        # Draw projectile dot
        import pygame
        pygame.draw.circle(surface, (100, 200, 255), (screen_x, screen_y), radius)
