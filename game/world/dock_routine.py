"""AI routine: fly to each stop, park, walk the pilot in to handle an
errand, then fly to the next stop - a small phase machine layered on top
of the same engage_seek()/park() plumbing ShuttleRoutine uses for pure
fly-only shuttling."""
import math

WALK_SPEED = 3          # world units/frame - matches LocationScreen's player walk speed
ARRIVAL_DISTANCE = 10    # how close counts as "reached" a walking destination
TALK_FRAMES = 180        # ~3 seconds at 60fps

# Which destination a pilot's role prefers when their current location's
# exit leads to more than one place (see LocationScreen.get_exit_options) -
# checked in order, first one actually offered wins. Roles with no entry
# here fall back to DEFAULT_EXIT_PREFERENCE, i.e. they head straight back
# to the ship exactly like before connected_locations existed.
ROLE_EXIT_PREFERENCE = {
    "freighter_pilot": ["wilderness", "city", "ship"],
}
DEFAULT_EXIT_PREFERENCE = ["ship"]


class DockRoutine:
    """Ping-pongs between the stops in a route like ShuttleRoutine, but
    each stop is a full stay instead of an instant turnaround:
    flying -> walking_in -> talking -> walking_out -> flying (next stop).

    Needs ai_ship.get_interior_screen (see AIShip/SpaceScreen.
    get_interior_screen) to find the stop's interior, and
    ai_ship.pilot_person (see AIShip) as the body it walks around -
    both already exist on every AIShip regardless of routine; this is
    just the first routine that uses them for more than tracking.
    """
    def __init__(self, route):
        self.route = route
        self._route_index = 0
        self.phase = "flying"
        self._location = None       # the interior LocationScreen currently being visited
        self._destination = None    # (x, y) the pilot is currently walking toward
        self._talk_timer = 0
        self._pending_exit = None   # "ship" or a connected_locations key - chosen in "talking", acted on once "walking_out" arrives
        self._visited_this_stop = set()  # connected_locations keys already entered at this stop - keeps _choose_exit from ping-ponging forever between two locations that each prefer the other

    def start(self, ai_ship):
        if self.route:
            ai_ship.engage_seek(self.route[0])

    def run(self, ai_ship):
        if self.phase == "flying":
            self._run_flying(ai_ship)
        elif self.phase == "walking_in":
            if self._step_toward(ai_ship.pilot_person):
                self.phase = "talking"
                self._talk_timer = TALK_FRAMES
        elif self.phase == "talking":
            self._talk_timer -= 1
            if self._talk_timer <= 0:
                self._pending_exit = self._choose_exit(ai_ship)
                self._destination = (self._location.entrance_x, self._location.entrance_y)
                self.phase = "walking_out"
        elif self.phase == "walking_out":
            if self._step_toward(ai_ship.pilot_person):
                if self._pending_exit == "ship":
                    self._reboard(ai_ship)
                else:
                    self._move_to_connected_location(ai_ship, self._pending_exit)

    def _run_flying(self, ai_ship):
        if not self.route:
            return
        if not ai_ship.autopilot_active:
            # Arrived and parked (Ship.park() already ran, via SeekMode's
            # arrival hook) - go ashore.
            self._begin_walking_in(ai_ship)

    def _begin_walking_in(self, ai_ship):
        stop = self.route[self._route_index]
        key = "default" if stop.is_station else next((k for k in ("city", "wilderness") if k in stop.interiors), None)
        world_width, world_height = (800, 600) if stop.is_station else (1600, 1600)
        location = ai_ship.get_interior_screen(stop, key, world_width, world_height) if ai_ship.get_interior_screen and key else None

        if location is None:
            # No walkable interior configured for this stop - skip the
            # errand and just fly on, same as ShuttleRoutine would have.
            self._advance_route(ai_ship)
            return

        ai_ship.pilot_ashore = True
        self._visited_this_stop = {key}
        self._enter_location(ai_ship, location)

    def _choose_exit(self, ai_ship):
        """Pick a destination from this location's exit options, using the
        pilot's role preference (ROLE_EXIT_PREFERENCE) - the first preferred
        option that's actually offered here AND not already visited this
        stop wins (the visited check is what keeps two locations that each
        prefer the other from ping-ponging forever instead of ever
        reboarding). Falls back to "ship" once every preference is either
        unavailable or already visited."""
        options = self._location.get_exit_options()
        role = ai_ship.pilot.get("role")
        for preferred in ROLE_EXIT_PREFERENCE.get(role, DEFAULT_EXIT_PREFERENCE):
            if preferred in options and (preferred == "ship" or preferred not in self._visited_this_stop):
                return preferred
        return "ship" if "ship" in options else (options[0] if options else "ship")

    def _move_to_connected_location(self, ai_ship, key):
        """Walk the pilot laterally into a connected interior at the same
        stop (e.g. city -> wilderness) instead of reboarding."""
        stop = self.route[self._route_index]
        world_width, world_height = (800, 600) if stop.is_station else (1600, 1600)
        new_location = ai_ship.get_interior_screen(stop, key, world_width, world_height)
        if new_location is None:
            self._reboard(ai_ship)
            return

        old_location = self._location
        if ai_ship.pilot_person in old_location.visitors:
            old_location.visitors.remove(ai_ship.pilot_person)
        self._visited_this_stop.add(key)
        self._enter_location(ai_ship, new_location)

    def _enter_location(self, ai_ship, location):
        """Place the pilot at a location's entrance, register them as a
        visitor, and head for its first NPC (or just stand at the entrance
        if it has none). Shared by both arriving at a stop for the first
        time and walking laterally into a connected location."""
        self._location = location
        ai_ship.pilot_person.x = location.entrance_x
        ai_ship.pilot_person.y = location.entrance_y
        location.visitors.append(ai_ship.pilot_person)

        target_npc = location.npcs[0] if location.npcs else None
        self._destination = (target_npc.x, target_npc.y) if target_npc else (location.entrance_x, location.entrance_y)
        self.phase = "walking_in"

    def _step_toward(self, person):
        """Move person one step toward self._destination. Returns True once arrived."""
        dx, dy = self._destination[0] - person.x, self._destination[1] - person.y
        dist = math.hypot(dx, dy)
        if dist <= ARRIVAL_DISTANCE:
            return True
        step = min(WALK_SPEED, dist)
        person.x += dx / dist * step
        person.y += dy / dist * step
        return False

    def _reboard(self, ai_ship):
        if self._location is not None and ai_ship.pilot_person in self._location.visitors:
            self._location.visitors.remove(ai_ship.pilot_person)
        ai_ship.pilot_ashore = False
        self._location = None
        self._visited_this_stop = set()
        self._advance_route(ai_ship)

    def _advance_route(self, ai_ship):
        self._route_index = (self._route_index + 1) % len(self.route)
        ai_ship.engage_seek(self.route[self._route_index])
        self.phase = "flying"
