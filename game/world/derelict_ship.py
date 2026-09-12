"""A static, un-crewed wreck - the "derelict_ship" system-event kind (see
docs/architecture/combat-and-mining.md's "System events" and events.json's
"kind"). Pure scenery, deliberately: no Character, no routine, no ai_fire,
nothing that lets any existing NPC/AI/combat system notice or interact with
it (mirrors game/world/miner_routine.py's "NPCs don't touch drifting scenery"
rule - a derelict is the player's discovery alone). Extends Ship (not a bare
WorldObject) purely to reuse its graphics-driven draw()/_get_shape_points
pipeline for free - a derelict renders exactly like a normal ship hull, just
dimmed, motionless (thrust always 0, so no thruster flame), and frozen at
whatever angle it spawned facing. See game/screens/space_screen/derelicts.py
for spawn/board/resolve logic, and game/world/smoke_trail.py for the
looping smoke puffs drawn alongside it while unresolved."""
import random
from game.world.ship import Ship

# How much a derelict's hull color is darkened relative to the ship_type's
# normal graphics color - reads as "dead in the water" rather than a live
# ship of the same type just holding still.
DIM_FACTOR = 0.45


def _dim(color):
    return tuple(max(0, int(c * DIM_FACTOR)) for c in color)


class DerelictShip(Ship):
    """`event_def` is the resolved events.json entry (kind "derelict_ship") -
    kept in full so derelicts.py's resolution logic (loot/rescue/trap) can
    read its own fields (loot table, payout range, pirate ship/pilot ids)
    without a second lookup. `event_id` is that entry's own events.json id,
    used to key any per-derelict-type save flags (see the rescue flag in
    derelicts.py)."""
    def __init__(self, x, y, event_id, event_def, graphics=None, rng=None):
        super().__init__(x, y, space_drag=0, graphics=dict(graphics or {}))
        rng = rng or random
        if "color" in self.graphics:
            self.graphics["color"] = list(_dim(tuple(self.graphics["color"])))
        self.angle = rng.uniform(0, 360)
        self.event_id = event_id
        self.event_def = event_def
        self.outcome = event_def.get("outcome", "loot")
        self.name = event_def.get("name", "Derelict Ship")
        # Targeting range gate (see game/screens/space_screen/targeting.py's
        # _in_target_range) - a derelict can't be cycled/clicked as a target
        # from arbitrary range, only once the player has actually closed in
        # on it. Set by derelicts.py from DERELICT_TARGET_RANGE, not fixed
        # here, so it stays one tunable in one place.
        self.target_range = None

    def update(self):
        """No animation, no movement - a derelict is a frozen wreck. Present
        only so callers that update() every world object uniformly (none
        currently do, since derelicts.py drives it directly) don't need a
        special case."""
        return True
