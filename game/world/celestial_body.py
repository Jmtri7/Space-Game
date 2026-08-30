"""A planet, ice ball, or gas giant drifting in a system - never a landing site."""
import pygame
import game.aa_draw as aa
from game.utils import get_scale, to_screen
from game.world.world_object import WorldObject


class CelestialBody(WorldObject):
    """Visible and targetable like a station or moon, but never a landing site -
    see SpaceScreen's hazard note in the HUD when one is targeted."""
    hazardous = True

    def __init__(self, x, y, graphics=None):
        super().__init__(x, y, graphics=graphics)
        self.name = self.graphics.get("name", "Unknown Body")
        self.size = self.graphics.get("size", 20)
        self.color = tuple(self.graphics.get("color", [150, 150, 150]))
        self.has_ring = self.graphics.get("has_ring", False)
        self.ring_color = tuple(self.graphics.get("ring_color", [200, 190, 150]))
        # Not a landing site, but still gives the autopilot/HUD a sane approach
        # distance to work with, the same way LandingSite.landing_distance does.
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
            ring_width = max(1, int(radius * 0.18))
            # Far half first (behind the planet) - the near half is drawn
            # again after the planet's disk, so the ring wraps around it
            # realistically instead of the whole ring sitting flatly behind
            # a fully opaque planet.
            self._draw_ring_half(surface, ring_rect, ring_width, top_half=True)

        aa.circle(surface, self.color, center, radius)

        if self.has_ring:
            self._draw_ring_half(surface, ring_rect, ring_width, top_half=False)

    def _draw_ring_half(self, surface, ring_rect, ring_width, top_half):
        """Draw only the top (far side, behind the planet) or bottom (near
        side, in front of the planet) half of the ring ellipse, via a clip
        rect over half of its bounding box."""
        half_height = ring_rect.height // 2 + 1
        if top_half:
            clip = pygame.Rect(ring_rect.left, ring_rect.top, ring_rect.width, half_height)
        else:
            clip = pygame.Rect(ring_rect.left, ring_rect.centery, ring_rect.width, half_height)
        previous_clip = surface.get_clip()
        surface.set_clip(previous_clip.clip(clip))
        pygame.draw.ellipse(surface, self.ring_color, ring_rect, ring_width)
        surface.set_clip(previous_clip)
