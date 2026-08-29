"""Static central star rendered in the space view."""
import pygame
from game.utils import get_scale, to_screen
from game.world.world_object import WorldObject


class CentralStar(WorldObject):
    """A large star at the center of the system - never a landing site,
    targetable like any other body, but always hazardous (see SpaceScreen's HUD)."""
    hazardous = True

    def __init__(self, x, y, graphics=None):
        super().__init__(x, y, graphics=graphics)
        self.name = self.graphics.get("name", "Star")
        self.size = self.graphics.get("size", 100)
        self.color = tuple(self.graphics.get("color", [255, 255, 100]))
        # Not a landing site, but gives the autopilot/HUD a sane approach distance.
        self.landing_distance = self.size * 3

    def draw(self, surface):
        """Draw the star as a solid core with a soft glow halo."""
        scale = get_scale()
        center = to_screen(self.x, self.y)
        radius = max(1, int(round(self.size * scale)))

        glow_color = tuple(int(c * 0.5) for c in self.color)
        pygame.draw.circle(surface, glow_color, center, int(radius * 1.4))
        pygame.draw.circle(surface, self.color, center, radius)
