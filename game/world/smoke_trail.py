"""Persistent, looping smoke-puff effect for a derelict ship - distinct from
Explosion's one-shot spark burst (game/world/explosion.py): this keeps
emitting new puffs for as long as the caller keeps calling update() (it never
self-expires the way Explosion does), and each individual puff drifts/grows/
fades independently. See game/world/derelict_ship.py, which owns one of
these for as long as it's unresolved (drawn every frame alongside the wreck,
dropped the moment the derelict despawns)."""
import math
import random
import pygame
from game.utils import to_screen, get_scale

PUFF_LIFETIME_FRAMES = 70          # ~1.2s per puff before it's fully faded
EMIT_INTERVAL_FRAMES = 14          # a fresh puff roughly every ~0.23s
PUFF_DRIFT_SPEED_RANGE = (0.15, 0.4)   # world units/frame, gentle upward drift
PUFF_START_RADIUS = 2.0
PUFF_END_RADIUS = 9.0
SMOKE_COLOR = (120, 120, 130)      # dull gray, distinct from Explosion's warm spark color


class SmokeTrail:
    """Anchored at a fixed offset from `x, y` (world space) - the caller is
    expected to update x/y itself each frame if the anchor moves (a derelict
    is static, so in practice this never changes after construction, but the
    fields are plain and mutable rather than baked into a closure)."""
    def __init__(self, x, y, rng=None):
        self.x = x
        self.y = y
        self._rng = rng or random
        self._emit_timer = 0
        self.puffs = []

    def update(self):
        """Age existing puffs (dropping fully-faded ones) and emit a new one
        on schedule. Never returns False / self-expires - the owner decides
        how long this runs by whether it keeps calling update() at all."""
        for puff in self.puffs:
            puff["age"] += 1
            puff["x"] += puff["dx"]
            puff["y"] += puff["dy"]
        self.puffs = [p for p in self.puffs if p["age"] < PUFF_LIFETIME_FRAMES]
        self._emit_timer -= 1
        if self._emit_timer <= 0:
            self._emit_timer = EMIT_INTERVAL_FRAMES
            angle = self._rng.uniform(0, 2 * math.pi)
            speed = self._rng.uniform(*PUFF_DRIFT_SPEED_RANGE)
            self.puffs.append({
                "x": self.x + self._rng.uniform(-3, 3),
                "y": self.y + self._rng.uniform(-3, 3),
                "dx": math.cos(angle) * speed,
                "dy": math.sin(angle) * speed - 0.15,  # slight upward bias
                "age": 0,
            })

    def draw(self, surface):
        scale = get_scale()
        for puff in self.puffs:
            fraction = puff["age"] / PUFF_LIFETIME_FRAMES
            alpha = max(0, int(160 * (1.0 - fraction)))
            if alpha <= 0:
                continue
            radius = max(1, int(round((PUFF_START_RADIUS + (PUFF_END_RADIUS - PUFF_START_RADIUS) * fraction) * scale)))
            sx, sy = to_screen(puff["x"], puff["y"])
            puff_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(puff_surf, (*SMOKE_COLOR, alpha), (radius, radius), radius)
            surface.blit(puff_surf, (sx - radius, sy - radius))
