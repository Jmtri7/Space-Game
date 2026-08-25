"""Routine: amble around near wherever this character started - for local
characters (no ship) with no fixed post."""
import math
import random


class WanderRoutine:
    """Amble to a random point within WANDER_RADIUS of where this character
    started, pause, then pick a new point. Used by roles with no fixed post
    (residents, travelers) as opposed to StationaryRoutine's "stay put"."""
    WANDER_RADIUS = 40
    WANDER_SPEED = 0.5

    def __init__(self, route):
        # `route` is unused - wandering has no destinations, just a home
        # point captured lazily in start(). Accepted anyway so every
        # Routine shares the same (route) constructor signature.
        self.origin_x = None
        self.origin_y = None
        self.target_x = None
        self.target_y = None
        self.wait_frames = 0

    def start(self, character):
        self.origin_x, self.origin_y = character.person.x, character.person.y
        self.target_x, self.target_y = self.origin_x, self.origin_y

    def run(self, character):
        self.wait_frames -= 1
        if self.wait_frames <= 0:
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, self.WANDER_RADIUS)
            self.target_x = self.origin_x + math.cos(angle) * radius
            self.target_y = self.origin_y + math.sin(angle) * radius
            self.wait_frames = random.randint(60, 180)

        person = character.person
        dx, dy = self.target_x - person.x, self.target_y - person.y
        dist = math.hypot(dx, dy)
        if dist > 1:
            step = min(self.WANDER_SPEED, dist)
            person.x += dx / dist * step
            person.y += dy / dist * step
