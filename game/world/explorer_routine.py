"""Routine: jump to a random system the character isn't currently in, orbit
a random object there for a while, then repeat - a wanderer with no fixed
route, unlike DockRoutine/ShuttleRoutine/OrbitRoutine which all ping-pong a
configured list of stops within one system."""
import random

ORBIT_MARGIN = 80                    # world units of clearance beyond the target's own landing_distance
ORBIT_DURATION_RANGE = (300, 600)    # frames to linger in orbit (~5-10s at 60fps) before moving on
IDLE_RETRY_FRAMES = 60               # brief pause before retrying if a system has nothing to orbit


class ExplorerRoutine:
    """Needs character.systems (system_id -> SystemState, see
    SpaceScreen.systems) and character.system_id (which system's ai_ships
    list currently holds this character) - both set by
    Character.for_ai_pilot when systems=... is passed in. Migrating between
    systems is just moving the Character between two SystemState.ai_ships
    lists and repositioning it: every system reuses the same game-space
    coordinates (see docs/PHYSICS.md), and only the system whose objects
    are currently aliased onto SpaceScreen (the active one) is ever drawn
    or updated with a camera, so a Character sitting in a different
    system's list is simply invisible/inert until the player jumps there,
    exactly like any other AI ship in that system."""
    def __init__(self, route=None):
        self._timer = 0

    def start(self, character):
        if not character.systems:
            return  # no galaxy to explore (e.g. built without systems= - see Character.for_ai_pilot)
        # Orbit something in the system the character was actually spawned
        # into first, rather than migrating immediately - the caller (see
        # SpaceScreen._build_system_state) hasn't appended this character to
        # its home SystemState.ai_ships yet at construction time, so
        # migrating away here would leave it belonging to neither system's
        # list once construction finishes.
        self._orbit_something_in(character, character.system_id)

    def run(self, character):
        if not character.systems:
            return
        self._timer -= 1
        if self._timer <= 0:
            self._jump_to_random_system(character)

    def _jump_to_random_system(self, character):
        systems = character.systems
        other_ids = [sid for sid in systems if sid != character.system_id]
        destination_id = random.choice(other_ids) if other_ids else character.system_id
        self._migrate(character, destination_id)
        self._orbit_something_in(character, destination_id)

    def _orbit_something_in(self, character, system_id):
        target = self._pick_orbit_target(character.systems[system_id])
        if target is None:
            self._timer = IDLE_RETRY_FRAMES
            return
        # Arrive already sitting on the orbit circle (not dead-center on the
        # target, which is a degenerate case for OrbitMode's tangent math -
        # see autopilot.py's OrbitMode) - and this avoids the ship appearing
        # wherever it happened to be sitting in the *previous* system's
        # unrelated coordinate space.
        radius = target.landing_distance + ORBIT_MARGIN
        character.x, character.y = target.x + radius, target.y
        character.engage_orbit(target.x, target.y, radius)
        self._timer = random.randint(*ORBIT_DURATION_RANGE)

    def _migrate(self, character, destination_id):
        if destination_id == character.system_id:
            return
        origin_state = character.systems.get(character.system_id)
        if origin_state and character in origin_state.ai_ships:
            origin_state.ai_ships.remove(character)
        character.systems[destination_id].ai_ships.append(character)
        character.system_id = destination_id
        character.velocity_x = 0
        character.velocity_y = 0

    @staticmethod
    def _pick_orbit_target(system_state):
        targets = system_state.orbit_targets()
        return random.choice(targets) if targets else None
