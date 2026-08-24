"""Static central star rendered in the space view."""
import pygame
from utils import get_scale, to_screen
from world_object import WorldObject


class CentralStar(WorldObject):
    """A large, non-interactive star at the center of the system."""
    def __init__(self, x, y, graphics=None):
        super().__init__(x, y, graphics=graphics)
        self.size = self.graphics.get("size", 100)
        self.color = tuple(self.graphics.get("color", [255, 255, 100]))

    def draw(self, surface):
        """Draw the star as a solid core with a soft glow halo."""
        scale = get_scale()
        center = to_screen(self.x, self.y)
        radius = max(1, int(round(self.size * scale)))

        glow_color = tuple(int(c * 0.5) for c in self.color)
        pygame.draw.circle(surface, glow_color, center, int(radius * 1.4))
        pygame.draw.circle(surface, self.color, center, radius)
