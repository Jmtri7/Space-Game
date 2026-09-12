"""Small drifting asteroid with constant velocity; round or jagged-polygon shape."""
import math
import random
from game.constants import GRAY
from game.world.world_object import WorldObject

DEFAULT_VERTEX_COUNT_RANGE = (7, 11)
DEFAULT_JAGGEDNESS = 0.35
DEFAULT_SPIN_SPEED_RANGE = (-1.5, 1.5)
ROUND_VERTEX_COUNT = 28  # ring samples for a "round" asteroid's shaded circle silhouette - enough for the smooth-band shading to read as a curve, not facets


class Asteroid(WorldObject):
    """An asteroid that drifts at a constant velocity. "round" asteroids
    (the default, if graphics omits "shape") draw as a shaded regular-polygon
    circle; "jagged" ones get an irregular polygon silhouette, generated once
    from `rng` at construction (regenerating it every frame would make them
    visibly writhe instead of looking like a solid rock), that spins in place
    at a fixed per-instance rate. Both shapes draw through the same faceted,
    lit fan (`_draw_shaded_polygon`) so every asteroid reads as a shaded rock
    rather than a flat silhouette. Asteroids can be damaged by projectiles;
    when health is depleted, small asteroids are destroyed, large ones break
    into fragments."""
    def __init__(self, x, y, velocity_x=0, velocity_y=0, size=4, graphics=None, rng=None, asteroid_type=None):
        super().__init__(x, y, graphics=graphics)
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.size = size
        self.color = tuple(self.graphics.get("color", GRAY))
        self.shape = self.graphics.get("shape", "round")
        self.angle = 0
        self.spin_speed = 0
        self.local_points = None  # (x, y) fractions of size, unrotated silhouette ring
        self.asteroid_type = asteroid_type
        health_multiplier = (asteroid_type or {}).get("health_multiplier", 1.0)
        self.health = max(3, size * 1.1 * health_multiplier)  # Health scales with size - lowered so asteroids break up faster under fire
        self.max_health = self.health
        self.rng = rng or random.Random()

        if self.shape == "jagged":
            rng = self.rng
            vertex_min, vertex_max = self.graphics.get("vertex_count_range", DEFAULT_VERTEX_COUNT_RANGE)
            vertex_count = rng.randint(vertex_min, vertex_max)
            jaggedness = self.graphics.get("jaggedness", DEFAULT_JAGGEDNESS)
            spin_min, spin_max = self.graphics.get("spin_speed_range", DEFAULT_SPIN_SPEED_RANGE)
            self.spin_speed = rng.uniform(spin_min, spin_max)
            self.local_points = []
            for i in range(vertex_count):
                theta = (2 * math.pi * i) / vertex_count
                radius_fraction = 1 + rng.uniform(-jaggedness, jaggedness)
                self.local_points.append((radius_fraction * math.cos(theta), radius_fraction * math.sin(theta)))
        else:
            # a regular polygon ring stands in for a perfect circle so the
            # same shaded-facet fan draws both shapes.
            self.local_points = [
                (math.cos(2 * math.pi * i / ROUND_VERTEX_COUNT), math.sin(2 * math.pi * i / ROUND_VERTEX_COUNT))
                for i in range(ROUND_VERTEX_COUNT)
            ]

    def take_damage(self, amount):
        """Reduce health; returns True if destroyed."""
        self.health -= amount
        return self.health <= 0

    def update(self):
        """Drift at constant velocity; jagged asteroids also spin in place."""
        self.x += self.velocity_x
        self.y += self.velocity_y
        if self.shape == "jagged":
            self.angle = (self.angle + self.spin_speed) % 360

    def draw(self, surface):
        scaled_points = [(lx * self.size, ly * self.size) for lx, ly in self.local_points]
        self._draw_shaded_polygon(surface, scaled_points, self.angle, self.color)
