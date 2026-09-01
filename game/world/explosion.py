"""Small spark-burst visual for a laser hitting an asteroid - purely
cosmetic (no position interactions, no get_distance/collision use), so it
doesn't extend WorldObject the way Ship/LandingSite/Asteroid do."""
import math
import random
import pygame
from game.utils import to_screen, get_scale

LIFETIME_FRAMES = 14         # ~0.23s at 60fps - quick enough not to linger
                              # through a rapid-fire burst (see weapon_fire_rate)
PARTICLE_COUNT_RANGE = (5, 8)
PARTICLE_SPEED_RANGE = (1.5, 3.5)   # world units/frame, outward from impact
SPARK_COLOR = (255, 200, 120)       # warm orange-yellow, distinct from the
                                     # laser's own cyan so hit and shot read separately


class Explosion:
    """A brief burst of fading spark particles at a fixed world point,
    spawned on projectile-asteroid impact (see
    SpaceScreen._spawn_impact_explosion). Each particle is a short radiating
    line that shrinks and fades out over LIFETIME_FRAMES; the whole effect
    self-removes once every particle's fully faded (see update())."""
    def __init__(self, x, y, rng=None):
        self.x = x
        self.y = y
        rng = rng or random
        count = rng.randint(*PARTICLE_COUNT_RANGE)
        self.particles = []
        for _ in range(count):
            angle = rng.uniform(0, 2 * math.pi)
            speed = rng.uniform(*PARTICLE_SPEED_RANGE)
            self.particles.append({
                "dx": math.cos(angle) * speed,
                "dy": math.sin(angle) * speed,
                "dist": 0.0,
            })
        self.age = 0

    def update(self):
        """Advance particles outward and age the effect. Returns False once
        it's done (LIFETIME_FRAMES elapsed) so the caller can drop it."""
        self.age += 1
        for particle in self.particles:
            particle["dist"] += math.hypot(particle["dx"], particle["dy"])
        return self.age < LIFETIME_FRAMES

    def draw(self, surface):
        life_fraction = 1.0 - (self.age / LIFETIME_FRAMES)
        if life_fraction <= 0:
            return
        scale = get_scale()
        screen_x, screen_y = to_screen(self.x, self.y)
        alpha = max(0, min(255, int(255 * life_fraction)))
        for particle in self.particles:
            px = screen_x + int(particle["dx"] * particle["dist"] * scale)
            py = screen_y + int(particle["dy"] * particle["dist"] * scale)
            length = max(1, int(3 * life_fraction * scale))
            spark_surf = pygame.Surface((length * 2, length * 2), pygame.SRCALPHA)
            pygame.draw.circle(spark_surf, (*SPARK_COLOR, alpha), (length, length), length)
            surface.blit(spark_surf, (px - length, py - length))
