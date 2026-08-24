"""Non-player character with dialogue and behavior."""
from game.world.person import Person
from game.world.dialogue import Dialogue


class NPC(Person):
    """Non-player character with dialogue and behavior."""
    def __init__(self, x, y, behavior="wander", name="NPC", greeting="Hello!", dialogue_options=None):
        super().__init__(x, y)
        self.behavior = behavior
        self.name = name
        self.greeting = greeting
        self.dialogue_options = dialogue_options or ["Talk", "Leave"]
        self.dialogue = Dialogue(name, [greeting], self.dialogue_options)
