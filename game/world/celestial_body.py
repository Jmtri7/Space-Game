"""A non-landable planet, ice ball, or gas giant drifting in a system."""
import pygame
from game.utils import get_scale, to_screen
from game.world.world_object import WorldObject


class CelestialBody(WorldObject):
    """Visible and targetable like a station or moon, but never landable -
    see SpaceScreen's hazard note in the HUD when one is targeted."""
    hazardous = True

    def __init__(self, x, y, graphics=None):
        super().__init__(x, y, graphics=graphics)
        self.name = self.graphics.get("name", "Unknown Body")
        self.size = self.graphics.get("size", 20)
        self.color = tuple(self.graphics.get("color", [150, 150, 150]))
        self.has_ring = self.graphics.get("has_ring", False)
        self.ring_color = tuple(self.graphics.get("ring_color", [200, 190, 150]))
        # Not landable, but still gives the autopilot/HUD a sane approach
        # distance to work with, the same way Landable.landing_distance does.
        self.landing_distance = self.size * 2.5

    def update(self):
        pass  # static - no orbit/rotation animation yet

    def draw(self, surface):
        scale = get_scale()
        center = to_screen(self.x, self.y)
        radius = max(1, int(round(self.size * scale)))

        if self.has_ring:
            ring_rect = pygame.Rect(0, 0, radius * 3, int(radius * 1.1))
            ring_rect.center = center
            pygame.draw.ellipse(surface, self.ring_color, ring_rect, max(1, int(radius * 0.18)))

        pygame.draw.circle(surface, self.color, center, radius)
