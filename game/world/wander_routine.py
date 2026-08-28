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
        if math.hypot(self.target_x - person.x, self.target_y - person.y) <= 1:
            return

        # One call to the shared on-foot primitive (Person.step_toward),
        # which wall-slides off walls/building corners. A tiny WANDER_RADIUS
        # means a target the wanderer can't reach at all (e.g. rolled just
        # inside a wall) would otherwise sit there bumping it forever - if
        # step_toward reports no movement, repick a target immediately
        # rather than waiting out wait_frames.
        can_move_to = character.can_move_to or (lambda x, y: True)
        if not person.step_toward(self.target_x, self.target_y, self.WANDER_SPEED, can_move_to):
            self.wait_frames = 0
