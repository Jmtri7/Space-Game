"""The player's own walking body, as a distinct, addressable identity."""
from game.world.person import Person


class PlayerCharacter(Person):
    """The player's own walking body in a location - a Person like any NPC,
    just distinguished by type so other code can recognize "this one is the
    player" (e.g. background-simulation logic that needs to know whether to
    move the camera) instead of comparing by name."""
