"""Infinite, seeded, procedurally generated star field background."""
import random
import pygame
import utils
from constants import GAME_WIDTH, GAME_HEIGHT
from utils import to_screen

CHUNK_SIZE = 1200
STARS_PER_CHUNK_RANGE = (20, 40)
CHUNK_MARGIN = 1        # extra ring of chunks generated beyond the viewport
CHUNK_KEEP_RADIUS = 3   # chunks farther than this from the viewport are forgotten


class StarField:
    """Stars are generated per-chunk from a seed, so the same world position
    always shows the same stars without ever pre-generating (or wrapping) a
    fixed-size field. New chunks are generated lazily as the camera approaches
    them; chunks far behind the camera are dropped to bound memory."""
    def __init__(self, seed=0):
        self.seed = seed
        self.chunks = {}  # (chunk_x, chunk_y) -> list of (x, y, brightness)

    def _chunk_seed(self, cx, cy):
        # Prime-multiply-xor spatial hash: deterministic, no reliance on
        # Python's (potentially randomized) hash() for strings/tuples.
        return (self.seed * 73856093) ^ (cx * 19349663) ^ (cy * 83492791)

    def _generate_chunk(self, cx, cy):
        rng = random.Random(self._chunk_seed(cx, cy))
        count = rng.randint(*STARS_PER_CHUNK_RANGE)
        stars = []
        for _ in range(count):
            x = cx * CHUNK_SIZE + rng.uniform(0, CHUNK_SIZE)
            y = cy * CHUNK_SIZE + rng.uniform(0, CHUNK_SIZE)
            brightness = rng.randint(100, 255)
            stars.append((x, y, brightness))
        return stars

    def _visible_chunk_range(self):
        cam_x, cam_y = utils.camera_offset_x, utils.camera_offset_y
        min_cx = int(cam_x // CHUNK_SIZE) - CHUNK_MARGIN
        max_cx = int((cam_x + GAME_WIDTH) // CHUNK_SIZE) + CHUNK_MARGIN
        min_cy = int(cam_y // CHUNK_SIZE) - CHUNK_MARGIN
        max_cy = int((cam_y + GAME_HEIGHT) // CHUNK_SIZE) + CHUNK_MARGIN
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
