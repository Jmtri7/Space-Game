"""Infinite, procedurally generated asteroid field."""
import math
import random
import game.utils as utils
from game.constants import GAME_WIDTH, GAME_HEIGHT
from game.world.asteroid import Asteroid

CHUNK_SIZE = 1200
DEFAULT_PER_CHUNK_RANGE = (1, 3)
DEFAULT_SIZE_RANGE = (3, 6)
DEFAULT_SPEED_RANGE = (0, 0.3)
CHUNK_MARGIN = 1        # extra ring of chunks generated beyond the viewport
CHUNK_KEEP_RADIUS = 2   # chunks farther than this from the viewport are forgotten

# Fallback if a system's config doesn't define an "asteroid_field" block at all.
DEFAULT_TYPES = [{"graphics": {"shape": "round", "color": [150, 150, 150]}, "weight": 1}]


class AsteroidField:
    """Manages a live set of Asteroid objects, spawned per-chunk from a
    weighted type table as the camera approaches, and culled once their
    chunk falls far out of view - so the player can fly arbitrarily far and
    keep finding new asteroids, without the field growing without bound.

    Unlike StarField, chunk content here is NOT reproducible by position:
    one random.Random instance advances continuously across every chunk
    this field ever generates (rather than being reseeded per-(cx, cy)), so
    revisiting a chunk after it's been unloaded gets freshly-rolled
    asteroids instead of replaying the same ones. This is a deliberate
    asteroid-specific choice, not an oversight - see PHYSICS.md's "Common
    Bugs" section, which still requires StarField's positions to stay
    stable on revisit. Asteroids are pure scenery either way: neither field
    is captured by SpaceScreen.get_state()/restore_state() (see
    SAVE_SYSTEM.md), so this doesn't change what a save reproduces.

    `types` is a list of dicts describing what can spawn: each has
    "graphics" (an asteroid_types.json entry - shape/color/jaggedness/spin),
    "weight" (relative frequency), and optionally "size_range"/"speed_range"
    (world-units and world-units-per-frame respectively; velocity direction
    is always randomized). See systems/*.json's "asteroid_field" block for
    the config format that produces this list (SpaceScreen._build_system_state
    resolves each entry's "type" id against asteroid_types.json)."""
    def __init__(self, types=None, per_chunk_range=DEFAULT_PER_CHUNK_RANGE, seed=None):
        self.types = types or DEFAULT_TYPES
        self.per_chunk_range = per_chunk_range
        self._rng = random.Random(seed)
        self.chunk_asteroids = {}  # (chunk_x, chunk_y) -> list of Asteroid

    def _generate_chunk(self, cx, cy):
        rng = self._rng
        weights = [type_cfg.get("weight", 1) for type_cfg in self.types]
        count = rng.randint(*self.per_chunk_range)
        asteroids = []
        for _ in range(count):
            type_cfg = rng.choices(self.types, weights=weights, k=1)[0]
            x = cx * CHUNK_SIZE + rng.uniform(0, CHUNK_SIZE)
            y = cy * CHUNK_SIZE + rng.uniform(0, CHUNK_SIZE)
            size = rng.uniform(*type_cfg.get("size_range", DEFAULT_SIZE_RANGE))
            speed = rng.uniform(*type_cfg.get("speed_range", DEFAULT_SPEED_RANGE))
            heading = rng.uniform(0, 2 * math.pi)
            velocity_x = speed * math.cos(heading)
            velocity_y = speed * math.sin(heading)
            asteroids.append(Asteroid(
                x, y, velocity_x=velocity_x, velocity_y=velocity_y, size=size,
                graphics=type_cfg.get("graphics"), rng=rng,
                asteroid_type={"id": type_cfg.get("type"), "mine_yield": type_cfg.get("mine_yield", 10)}
            ))
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
