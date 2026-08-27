"""Routine: continuously chase a moving target (typically the player) - a
scripted, temporary override rather than one ever picked from a role (see
Character.set_routine and person.escort_flag/SpaceScreen._sync_escorts),
used for an NPC pilot escorting the player somewhere (e.g. Kade Marsh
following the player through the tutorial mission)."""


class FollowRoutine:
    """Keep seeking `target` (anything engage_seek accepts - a moving
    Character/PlayerController works fine, since SeekMode reads its
    position fresh every frame) for as long as this routine is active."""
    def __init__(self, target):
        self.target = target

    def start(self, character):
        character.engage_seek(self.target)

    def run(self, character):
        # Re-engage whenever autopilot isn't actively seeking anymore -
        # SeekMode disengages itself once "arrived" (close enough and slow
        # enough - see has_arrived), which a moving target reached only
        # momentarily. Re-issuing engage_seek picks the chase back up
        # instead of leaving the character parked wherever it last caught
        # up to the target.
        if not character.autopilot_active:
            character.engage_seek(self.target)
