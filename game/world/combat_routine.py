"""Routine: attack a moving target (the player). A scripted, temporary
override - not a role default, never in ROLE_ROUTINES - swapped in by
SpaceScreen._sync_hostiles() when a pilot turns hostile (faction standing
below the threshold, or a flag), and swapped back to the pilot's normal
role routine once they're no longer hostile. The AI counterpart to holding
SPACE in the cockpit.

Drives the ship through its low-level controls (turn_left / turn_right /
increase_thrust / release_thrust) exactly as PlayerController does - it
never touches autopilot / SeekMode / OrbitMode, so it carries none of the
autopilot regression risk documented in docs/AUTOPILOT_TESTING.md. Firing
itself is left to SpaceScreen (which owns the projectile list): this
routine only sets character.firing each frame; SpaceScreen._update_ai_weapon_fire
reads it.
"""
import math

PREFERRED_RANGE = 320   # world units - close to this and the attacker stops thrusting
FIRING_RANGE = 440      # fire only within this distance
FIRING_CONE_DEG = 9     # ...and only when the nose is this close to on-target
THRUST_CONE_DEG = 28    # thrust to close distance only when roughly facing the target


def _signed_angle_delta(from_deg, to_deg):
    """Shortest signed rotation (degrees, -180..180) from from_deg to to_deg."""
    return (to_deg - from_deg + 180) % 360 - 180


class CombatRoutine:
    """Turn to face `target`, close to roughly PREFERRED_RANGE, and set
    character.firing while lined up and in range. `target` is anything with
    live .x/.y (the PlayerController works directly)."""
    def __init__(self, target):
        self.target = target

    def start(self, character):
        character.firing = False
        if character.ship:
            # Drop any autopilot mode so ship.update() runs plain physics on
            # the controls this routine sets.
            character.ship.autopilot.disengage()

    def run(self, character):
        ship = character.ship
        if not ship:
            return
        dx = self.target.x - ship.x
        dy = self.target.y - ship.y
        dist = math.hypot(dx, dy)
        desired_deg = math.degrees(math.atan2(dx, -dy)) % 360
        diff = _signed_angle_delta(ship.angle, desired_deg)

        deadband = ship.rotation_speed * 0.5
        if diff > deadband:
            ship.turn_right()
        elif diff < -deadband:
            ship.turn_left()

        if abs(diff) < THRUST_CONE_DEG and dist > PREFERRED_RANGE:
            ship.increase_thrust()
        else:
            ship.release_thrust()

        character.firing = abs(diff) < FIRING_CONE_DEG and dist < FIRING_RANGE
