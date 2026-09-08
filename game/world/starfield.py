"""Infinite, seeded, procedurally generated star field background."""
import math
import random
import pygame
import game.utils as utils
from game.utils import to_screen

CHUNK_SIZE = 1200
STARS_PER_CHUNK_RANGE = (20, 40)
CHUNK_MARGIN = 1        # extra ring of chunks generated beyond the viewport
CHUNK_KEEP_RADIUS = 3   # chunks farther than this from the viewport are forgotten


class StarField:
    """Stars are generated per-chunk from a seed, so the same world position
    always shows the same stars without ever pre-generating (or wrapping) a
    fixed-size field. New chunks are generated lazily as the camera approaches
    them; chunks far behind the camera are dropped to bound memory."""
    def __init__(self, seed=0, stars_per_chunk_range=STARS_PER_CHUNK_RANGE):
        self.seed = seed
        self.stars_per_chunk_range = stars_per_chunk_range
        self.chunks = {}  # (chunk_x, chunk_y) -> list of (x, y, brightness)

    def _chunk_seed(self, cx, cy):
        # Prime-multiply-xor spatial hash: deterministic, no reliance on
        # Python's (potentially randomized) hash() for strings/tuples.
        return (self.seed * 73856093) ^ (cx * 19349663) ^ (cy * 83492791)

    def _generate_chunk(self, cx, cy):
        rng = random.Random(self._chunk_seed(cx, cy))
        count = rng.randint(*self.stars_per_chunk_range)
        stars = []
        for _ in range(count):
            x = cx * CHUNK_SIZE + rng.uniform(0, CHUNK_SIZE)
            y = cy * CHUNK_SIZE + rng.uniform(0, CHUNK_SIZE)
            brightness = rng.randint(100, 255)
            stars.append((x, y, brightness))
        return stars

    def _visible_chunk_range(self):
        # The world rectangle actually on screen - which shrinks as the camera
        # zooms in, so a zoomed-in interior/Space View iterates a handful of
        # chunks instead of the whole GAME_WIDTH-at-zoom-1 span (that was ~9x
        # too wide at max interior zoom, generating and projecting hundreds of
        # off-screen stars every frame).
        min_x, min_y, max_x, max_y = utils.visible_world_bounds()
        min_cx = int(math.floor(min_x / CHUNK_SIZE)) - CHUNK_MARGIN
        max_cx = int(math.floor(max_x / CHUNK_SIZE)) + CHUNK_MARGIN
        min_cy = int(math.floor(min_y / CHUNK_SIZE)) - CHUNK_MARGIN
        max_cy = int(math.floor(max_y / CHUNK_SIZE)) + CHUNK_MARGIN
        return min_cx, max_cx, min_cy, max_cy

    def _update_chunks(self, min_cx, max_cx, min_cy, max_cy):
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                if (cx, cy) not in self.chunks:
                    self.chunks[(cx, cy)] = self._generate_chunk(cx, cy)

        keep = {
            (cx, cy)
            for cx in range(min_cx - CHUNK_KEEP_RADIUS, max_cx + CHUNK_KEEP_RADIUS + 1)
            for cy in range(min_cy - CHUNK_KEEP_RADIUS, max_cy + CHUNK_KEEP_RADIUS + 1)
        }
        for key in list(self.chunks.keys()):
            if key not in keep:
                del self.chunks[key]

    def draw(self, surface):
        min_cx, max_cx, min_cy, max_cy = self._visible_chunk_range()
        self._update_chunks(min_cx, max_cx, min_cy, max_cy)

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                for x, y, brightness in self.chunks.get((cx, cy), []):
                    pygame.draw.circle(surface, (brightness, brightness, brightness), to_screen(x, y), 1)
