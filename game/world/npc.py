"""Non-player character with dialogue and behavior."""
import math
import random
from game.world.person import Person
from game.world.dialogue import Dialogue


class NPC(Person):
    """Non-player character with dialogue and behavior."""
    def __init__(self, x, y, behavior="wander", name="NPC", greeting="Hello!", dialogue_options=None, dialogue_tree=None, wander_radius=40):
        super().__init__(x, y, name=name)
        self.behavior = behavior
        self.greeting = greeting
        self.dialogue_options = dialogue_options or ["Talk", "Leave"]
        # A config-provided dialogue_tree ({"root": ..., "nodes": {...}})
        # opts this NPC into a real branching conversation (see
        # game/world/dialogue.py); everyone else keeps the old flat
        # greeting+options shape via Dialogue.from_flat().
        if dialogue_tree:
            self.dialogue = Dialogue(name, dialogue_tree["nodes"], root=dialogue_tree.get("root", "start"))
        else:
            self.dialogue = Dialogue.from_flat(name, greeting, self.dialogue_options)

        # Wander state - only meaningful for behavior="wander", but harmless
        # to always have (keeps __init__ simple, avoids a special case).
        self.origin_x, self.origin_y = x, y
        self.wander_radius = wander_radius
        self.wander_speed = 0.5
        self.wander_time = 0
        self.wander_x, self.wander_y = x, y

    def update(self):
        """Run this NPC's configured behavior, if recognized. An unrecognized
        behavior string is a safe no-op rather than a crash - lets config
        typos fail quietly instead of taking the game down."""
        behavior_method = getattr(self, f"_behavior_{self.behavior}", None)
        if behavior_method:
            behavior_method()

    def _behavior_wander(self):
        """Amble to a random point within wander_radius of where this NPC
        started, pause, then pick a new point."""
        self.wander_time -= 1
        if self.wander_time <= 0:
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, self.wander_radius)
            self.wander_x = self.origin_x + math.cos(angle) * radius
            self.wander_y = self.origin_y + math.sin(angle) * radius
            self.wander_time = random.randint(60, 180)

        dx, dy = self.wander_x - self.x, self.wander_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 1:
            step = min(self.wander_speed, dist)
            self.x += dx / dist * step
            self.y += dy / dist * step

    def _behavior_bar(self):
        """Stays put - explicit no-op rather than an implicit fallthrough."""
