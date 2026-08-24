"""Infinite, seeded, procedurally generated asteroid field."""
import random
import game.utils as utils
from game.constants import GAME_WIDTH, GAME_HEIGHT
from game.world.asteroid import Asteroid

CHUNK_SIZE = 1200
ASTEROIDS_PER_CHUNK_RANGE = (1, 3)
CHUNK_MARGIN = 1        # extra ring of chunks generated beyond the viewport
CHUNK_KEEP_RADIUS = 2   # chunks farther than this from the viewport are forgotten


class AsteroidField:
    """Manages a live set of Asteroid objects, spawned per-chunk from a seed
    as the camera approaches, and culled once their chunk falls far out of
    view - so the player can fly arbitrarily far and keep finding new
    asteroids, without the field growing without bound."""
    def __init__(self, seed=0):
        self.seed = seed
        self.chunk_asteroids = {}  # (chunk_x, chunk_y) -> list of Asteroid

    def _chunk_seed(self, cx, cy):
        # Prime-multiply-xor spatial hash, distinct from StarField's (different
        # base seed value) so stars and asteroids don't line up identically.
        return (self.seed * 32452867) ^ (cx * 24036583) ^ (cy * 15485867)

    def _generate_chunk(self, cx, cy):
        rng = random.Random(self._chunk_seed(cx, cy))
        count = rng.randint(*ASTEROIDS_PER_CHUNK_RANGE)
        asteroids = []
        for _ in range(count):
            x = cx * CHUNK_SIZE + rng.uniform(0, CHUNK_SIZE)
            y = cy * CHUNK_SIZE + rng.uniform(0, CHUNK_SIZE)
            velocity_x = rng.uniform(-0.3, 0.3)
            velocity_y = rng.uniform(-0.3, 0.3)
            size = rng.uniform(3, 6)
            asteroids.append(Asteroid(x, y, velocity_x=velocity_x, velocity_y=velocity_y, size=size))
        return asteroids

    def _visible_chunk_range(self):
        cam_x, cam_y = utils.camera_offset_x, utils.camera_offset_y
        min_cx = int(cam_x // CHUNK_SIZE) - CHUNK_MARGIN
        max_cx = int((cam_x + GAME_WIDTH) // CHUNK_SIZE) + CHUNK_MARGIN
        min_cy = int(cam_y // CHUNK_SIZE) - CHUNK_MARGIN
        max_cy = int((cam_y + GAME_HEIGHT) // CHUNK_SIZE) + CHUNK_MARGIN
        return min_cx, max_cx, min_cy, max_cy

    def update(self):
        """Spawn newly-visible chunks, cull far ones, then advance every live asteroid."""
        min_cx, max_cx, min_cy, max_cy = self._visible_chunk_range()

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                if (cx, cy) not in self.chunk_asteroids:
                    self.chunk_asteroids[(cx, cy)] = self._generate_chunk(cx, cy)

        keep = {
            (cx, cy)
            for cx in range(min_cx - CHUNK_KEEP_RADIUS, max_cx + CHUNK_KEEP_RADIUS + 1)
            for cy in range(min_cy - CHUNK_KEEP_RADIUS, max_cy + CHUNK_KEEP_RADIUS + 1)
        }
        for key in list(self.chunk_asteroids.keys()):
            if key not in keep:
                del self.chunk_asteroids[key]

        for asteroids in self.chunk_asteroids.values():
            for asteroid in asteroids:
                asteroid.update()

    def draw(self, surface):
        for asteroids in self.chunk_asteroids.values():
            for asteroid in asteroids:
                asteroid.draw(surface)

    @property
    def asteroids(self):
        """Flat list of every currently-active asteroid (e.g. for debug markers)."""
        return [asteroid for chunk in self.chunk_asteroids.values() for asteroid in chunk]
