"""Routine: fly to each stop, park, walk the character in to handle an
errand, then fly to the next stop - a small phase machine layered on top
of the same engage_seek()/park() plumbing ShuttleRoutine uses for pure
fly-only shuttling."""
import math
from collections import deque

from game.constants import WALKING_SPEED
from game.world.indoor_pathfinder import IndoorPathfinder

WALK_SPEED = WALKING_SPEED  # same pace as LocationScreen's player (see constants.WALKING_SPEED)
ARRIVAL_DISTANCE = 10    # how close counts as "reached" a walking destination
TALK_FRAMES = 180        # ~3 seconds at 60fps

# Sentinel usable inside a ROLE_EXIT_PREFERENCE list: resolves at each
# stop to the next hop along the shortest path (see _next_hop_toward_ship,
# which searches Landable.interior_adjacency) toward whichever interior
# actually leads back to the ship (Landable.get_ship_entry_key) - not a
# literal interior key, since that room's name is specific to one story's
# layout (sol_alpha calls it "spaceport"; nothing requires another story
# to). Resolves to None (no candidate) once already standing in that
# room, since "ship" itself is reachable there directly.
TOWARD_SHIP = "toward_ship"

# Which destination a character's role prefers when their current
# location has more than one reachable place across all its portals (see
# LocationScreen.all_exit_options) - checked in order, first one actually
# offered wins. Roles with no entry here fall back to
# DEFAULT_EXIT_PREFERENCE, i.e. they head straight back to the ship exactly
# like before connected_locations existed.
#
# TOWARD_SHIP is here because a station's landing room doesn't always
# offer "ship" directly (e.g. sol_alpha's concourse doesn't - only its
# spaceport does, gated on the player owning one) - a freighter pilot
# landing somewhere else needs an explicit route to wherever does, not
# just a preference that happens to be offered at the current stop.
#
# Deliberately does NOT include "wilderness"/"city" - an earlier version
# had freighter_pilot detour into the moon's other location before
# reboarding, but wilderness has no NPC to visit at all, so the pilot just
# stood at its entrance for a few seconds doing nothing - and if the player
# happened to be looking at wilderness at that moment (having landed there
# themselves while the pilot was in city), it looked exactly like the pilot
# glitching in and out of existence. Only detour toward a location that
# actually has something in it (like TOWARD_SHIP's target usually does).
ROLE_EXIT_PREFERENCE = {
    "freighter_pilot": [TOWARD_SHIP, "ship"],
}
DEFAULT_EXIT_PREFERENCE = ["ship"]

# Hard cap on lateral hops within one stop, regardless of role/preference/
# graph shape - guarantees _choose_exit always eventually reboards even if
# a future role's preference list never matches anything reachable from
# where it actually is (see the corridor<->dormitory ping-pong this caught
# during development, before ROLE_EXIT_PREFERENCE routed through the
# spaceport). Larger than any real station/moon graph's location count.
MAX_LATERAL_HOPS = 8


class DockRoutine:
    """Ping-pongs between the stops in a route like ShuttleRoutine, but
    each stop is a full stay instead of an instant turnaround:
    flying -> walking_in -> talking -> walking_out -> flying (next stop).

    Needs character.get_interior_screen (see Character/SpaceScreen.
    get_interior_screen) to find the stop's interior, and character.person
    as the body it walks around - both already exist on every ship-flying
    Character regardless of routine; this is just the first routine that
    uses them for more than tracking.
    """
    def __init__(self, route):
        self.route = route
        self._route_index = 0
        self.phase = "flying"
        self._location = None       # the interior LocationScreen currently being visited
        self._waypoints = []        # remaining points to walk through (see IndoorPathfinder), last one is the real destination
        self._talk_timer = 0
        self._pending_exit = None   # "ship" or a connected_locations key - chosen in "talking", acted on once "walking_out" arrives
        self._visited_this_stop = set()  # connected_locations keys already entered at this stop - keeps _choose_exit from ping-ponging forever between two locations that each prefer the other

    def start(self, character):
        if self.route:
            character.engage_seek(self.route[0])

    def run(self, character):
        if self.phase == "flying":
            self._run_flying(character)
        elif self.phase == "walking_in":
            if self._step_toward(character.person):
                self.phase = "talking"
                self._talk_timer = TALK_FRAMES
        elif self.phase == "talking":
            self._talk_timer -= 1
            if self._talk_timer <= 0:
                self._pending_exit = self._choose_exit(character)
                exit_portal = self._location.portal_for(self._pending_exit)
                self._set_waypoints(character.person, (exit_portal["x"], exit_portal["y"]))
                self.phase = "walking_out"
        elif self.phase == "walking_out":
            if self._step_toward(character.person):
                if self._pending_exit == "ship":
                    self._reboard(character)
                else:
                    self._move_to_connected_location(character, self._pending_exit)

    def _run_flying(self, character):
        if not self.route:
            return
        if not character.autopilot_active:
            # Arrived and parked (Ship.park() already ran, via SeekMode's
            # arrival hook) - go ashore.
            self._begin_walking_in(character)

    def _begin_walking_in(self, character):
        stop = self.route[self._route_index]
        if stop.is_station:
            # Walk in through the same doorway a ship actually docks at
            # (see Landable.get_ship_entry_key), not always "default" -
            # otherwise a pilot arriving fresh lands at whichever portal
            # happens to be listed first in that room's config (e.g. the
            # concourse's corridor/dormitory-side portal), not the
            # spaceport a ship actually opens into.
            key = stop.get_ship_entry_key()
        else:
            key = next((k for k in ("city", "wilderness") if k in stop.interiors), None)
        location = character.get_interior_screen(stop, key) if character.get_interior_screen and key else None

        if location is None:
            # No walkable interior configured for this stop - skip the
            # errand and just fly on, same as ShuttleRoutine would have.
            self._advance_route(character)
            return

        character.ashore = True
        self._visited_this_stop = {key}
        self._enter_location(character, location)

    def _choose_exit(self, character):
        """Pick a destination from this location's exit options, using the
        character's role preference (ROLE_EXIT_PREFERENCE) - the first
        preferred option that's actually offered here AND not already
        visited this stop wins (the visited check is what keeps two
        locations that each prefer the other from ping-ponging forever
        instead of ever reboarding).

        If no preference applies, keeps exploring an unvisited connected
        location rather than immediately reboarding, so a multi-hop layout
        (e.g. the station's dormitory/corridor/concourse/spaceport graph)
        still makes forward progress. "ship" is always returned - even if
        it isn't actually one of this location's exit options - once
        MAX_LATERAL_HOPS is hit or there's nothing unvisited left to try;
        run() reboards unconditionally on "ship", so this is always a safe
        way to give up and fly off rather than wander forever."""
        options = self._location.all_exit_options()
        if len(self._visited_this_stop) >= MAX_LATERAL_HOPS:
            return "ship"
        for preferred in ROLE_EXIT_PREFERENCE.get(character.role, DEFAULT_EXIT_PREFERENCE):
            candidate = self._next_hop_toward_ship() if preferred == TOWARD_SHIP else preferred
            if candidate and candidate in options and (candidate == "ship" or candidate not in self._visited_this_stop):
                return candidate
        unvisited = [option for option in options if option not in self._visited_this_stop]
        return unvisited[0] if unvisited else "ship"

    def _next_hop_toward_ship(self):
        """Resolve TOWARD_SHIP: a breadth-first search of the current
        stop's interior graph (Landable.interior_adjacency) from the room
        we're standing in toward whichever room actually leads back to the
        ship (Landable.get_ship_entry_key), returning just the first hop -
        or None if we're already there (nothing to route to) or no path
        exists. Only fetches self.route[self._route_index] when actually
        needed, so a role/test that never resolves TOWARD_SHIP (the common
        case - DEFAULT_EXIT_PREFERENCE never does) doesn't require a real
        route to be set up."""
        stop = self.route[self._route_index]
        start = self._location.interior_key
        target = stop.get_ship_entry_key()
        if start == target:
            return None
        graph = stop.interior_adjacency()
        came_from = {start: None}
        frontier = deque([start])
        while frontier:
            node = frontier.popleft()
            if node == target:
                while came_from[node] != start:
                    node = came_from[node]
                return node
            for neighbor in graph.get(node, []):
                if neighbor not in came_from:
                    came_from[neighbor] = node
                    frontier.append(neighbor)
        return None

    def _move_to_connected_location(self, character, key):
        """Walk the character laterally into a connected interior at the
        same stop (e.g. city -> wilderness) instead of reboarding."""
        stop = self.route[self._route_index]
        new_location = character.get_interior_screen(stop, key)
        if new_location is None:
            self._reboard(character)
            return

        old_location = self._location
        origin_key = old_location.interior_key
        if character.person in old_location.visitors:
            old_location.visitors.remove(character.person)
        self._visited_this_stop.add(key)
        self._enter_location(character, new_location, origin_key=origin_key)

    def _enter_location(self, character, location, origin_key=None):
        """Place the character at a location's portal, register them as a
        visitor, and head for its first NPC (or just stand at the portal if
        it has none). Shared by both arriving at a stop for the first time
        (origin_key=None - no "coming from" to match, so portal_for() falls
        back to the location's first/primary portal) and walking laterally
        into a connected location (origin_key = the location just left, so
        they arrive next to the specific portal leading back to it - see
        LocationScreen.portal_for/arrive_from)."""
        self._location = location
        portal = location.portal_for(origin_key)
        character.person.x, character.person.y = portal["x"], portal["y"]
        location.visitors.append(character.person)

        target_npc = location.npcs[0].person if location.npcs else None
        goal = (target_npc.x, target_npc.y) if target_npc else (character.person.x, character.person.y)
        self._set_waypoints(character.person, goal)
        self.phase = "walking_in"

    def _set_waypoints(self, person, goal):
        """(Re)plan the walk to `goal` through self._location's rooms and
        around its building footprints (see IndoorPathfinder) - routing
        through the doorway between rooms (or around a building in the way)
        instead of a straight line that might not be walkable at all is
        what stops a pilot (e.g. Elena Voss) from getting permanently stuck
        against a wall or building partway there."""
        self._waypoints = IndoorPathfinder.find_path(self._location.rooms, (person.x, person.y), goal, self._location.building_footprints)

    def _step_toward(self, person):
        """Move person one step toward the next waypoint in self._waypoints
        (see IndoorPathfinder), respecting self._location's walls
        (wall-sliding: try the full diagonal step, then each axis alone, so
        a wall corner deflects the walk instead of the pilot clipping
        straight through it) - the same walkable-area check the player's
        own movement uses (LocationScreen.can_move_to). Advances through
        waypoints already reached without waiting a frame; returns True
        once the final waypoint (the real destination) is reached."""
        while self._waypoints:
            target_x, target_y = self._waypoints[0]
            dx, dy = target_x - person.x, target_y - person.y
            dist = math.hypot(dx, dy)
            if dist <= ARRIVAL_DISTANCE:
                self._waypoints.pop(0)
                continue
            step = min(WALK_SPEED, dist)
            step_x, step_y = dx / dist * step, dy / dist * step
            for candidate_x, candidate_y in ((person.x + step_x, person.y + step_y), (person.x + step_x, person.y), (person.x, person.y + step_y)):
                if self._location.can_move_to(candidate_x, candidate_y):
                    person.x, person.y = candidate_x, candidate_y
                    break
            return False
        return True

    def _reboard(self, character):
        if self._location is not None and character.person in self._location.visitors:
            self._location.visitors.remove(character.person)
        character.ashore = False
        self._location = None
        self._visited_this_stop = set()
        self._advance_route(character)

    def _advance_route(self, character):
        self._route_index = (self._route_index + 1) % len(self.route)
        character.engage_seek(self.route[self._route_index])
        self.phase = "flying"
