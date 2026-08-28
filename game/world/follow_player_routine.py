"""Routine: follow a moving target on foot at a polite distance - the
on-foot counterpart to OrbitPlayerRoutine (which does the same for a ship).

A scripted, temporary override rather than one ever picked from a role (see
Character.set_routine and person.escort_flag) - used for an interior NPC
walking the player through a station/moon walkthrough (see an NPC config's
"escort_flag" and LocationScreen._sync_npc_escorts, the interior mirror of
SpaceScreen._sync_escorts). Kade Marsh does the flying-lesson version of
this from a ship; a station concierge does the walking-tour version from
this.
"""
import math


class FollowPlayerRoutine:
    """Step toward `target` (anything with live .x/.y - the PlayerCharacter
    works fine) each frame, stopping once within STOP_DISTANCE so the guide
    trails the player instead of standing on top of them. Movement goes
    through the character's own `can_move_to` with the same full-step /
    each-axis wall-slide WanderRoutine uses, so the guide deflects off a
    wall or pod doorway instead of clipping through it."""

    # A touch above the player's own walking pace (story.json "walking_speed"
    # default 2.5) so the guide can close a gap the player opened, but not so
    # fast it teleports up beside them.
    FOLLOW_SPEED = 3.0
    STOP_DISTANCE = 55  # world units - hold this far back once caught up

    def __init__(self, target, follow_speed=FOLLOW_SPEED):
        self.target = target
        self.follow_speed = follow_speed

    def start(self, character):
        pass

    def run(self, character):
        person = character.person
        dx, dy = self.target.x - person.x, self.target.y - person.y
        dist = math.hypot(dx, dy)
        if dist <= self.STOP_DISTANCE:
            return
        step = min(self.follow_speed, dist - self.STOP_DISTANCE)
        step_x, step_y = dx / dist * step, dy / dist * step
        can_move_to = character.can_move_to
        for candidate_x, candidate_y in (
            (person.x + step_x, person.y + step_y),
            (person.x + step_x, person.y),
            (person.x, person.y + step_y),
        ):
            if (candidate_x, candidate_y) == (person.x, person.y):
                continue
            if can_move_to is None or can_move_to(candidate_x, candidate_y):
                person.x, person.y = candidate_x, candidate_y
                return
