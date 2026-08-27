"""Routine: continuously orbit a moving target (typically the player) at a
fixed radius - a scripted, temporary override rather than one ever picked
from a role (see Character.set_routine and person.escort_flag/
SpaceScreen._sync_escorts), used for an NPC pilot escorting the player
(e.g. Kade Marsh during the tutorial mission) by circling nearby instead
of parking on top of them the way a plain seek-and-follow would."""

# World units from the target the escort tries to hold its circle at.
# OrbitMode settles a bit wider than this for a fast ship (see its
# docstring) - a patrol-stat ship asked for 130 settles into roughly a
# 180-220 unit circle, which reads clearly as "escorting close by" while
# staying comfortably on screen. The exact radius isn't load-bearing;
# "near the player, not parked on top of them" is the whole point.
ORBIT_RADIUS = 130


class OrbitPlayerRoutine:
    """Keep `target` (anything with live .x/.y - a moving Character or
    PlayerController works fine) at the centre of a fixed-radius orbit for
    as long as this routine is active."""
    def __init__(self, target, radius=ORBIT_RADIUS):
        self.target = target
        self.radius = radius

    def start(self, character):
        character.engage_orbit(self.target.x, self.target.y, self.radius)

    def run(self, character):
        # Re-engage every frame so the orbit centre tracks the target's
        # current position - OrbitMode itself circles a *fixed* point, so a
        # moving centre has to be re-supplied each frame. OrbitMode carries
        # no state worth preserving across the re-engage (just centre and
        # radius - see autopilot.py), so rebuilding it every frame is
        # cheap and correct.
        character.engage_orbit(self.target.x, self.target.y, self.radius)
