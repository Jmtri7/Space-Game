"""Routine: walk a local (no-ship) character to a point and then mark it
`gone` so its interior drops it from the roster.

A scripted, temporary override swapped in via `Character.set_routine`
(see an NPC config's `"depart_flag"` and
`LocationScreen._sync_npc_escorts`) - never a role default - for an NPC
that leaves the scene for good after a one-time story beat, e.g. the Grey
Courier walking off the ring the moment the note changes hands in
`the_whisper_line`. The interior's content gate (`requires_not_flag` on
the same flag) keeps them gone on every later visit.
"""
import math


class DepartRoutine:
    """Step toward `target` (an (x, y) tuple) each frame via the shared
    on-foot primitive `person.step_toward`, so the figure wall-slides and
    runs its walk cycle. Once within arrival distance - or the moment a
    step makes no progress (wall-boxed) - set `character.gone` and stop;
    `LocationScreen.update_physics` filters `gone` characters out after the
    NPC update pass."""

    SPEED = 2.2
    ARRIVE = 6

    def __init__(self, target):
        self.target = target

    def start(self, character):
        pass

    def run(self, character):
        person = character.person
        tx, ty = self.target
        if math.hypot(tx - person.x, ty - person.y) <= self.ARRIVE:
            character.gone = True
            return
        can_move_to = character.can_move_to or (lambda x, y: True)
        if not person.step_toward(tx, ty, self.SPEED, can_move_to):
            character.gone = True
