"""AI ship whose behavior is chosen by its pilot's faction and role."""
import random
from game.world.ship import Ship
from game.world.person import Person
from game.world.dock_routine import DockRoutine


class ShuttleRoutine:
    """Ping-pong between the stops in a route, one at a time."""
    def __init__(self, route):
        self.route = route
        self._route_index = 0

    def start(self, ai_ship):
        if self.route:
            ai_ship.engage_seek(self.route[0])

    def run(self, ai_ship):
        if not self.route:
            return
        if not ai_ship.autopilot_active:
            self._route_index = (self._route_index + 1) % len(self.route)
            ai_ship.engage_seek(self.route[self._route_index])


class OrbitRoutine:
    """Continuously circle a point enclosing every landable in the route."""
    def __init__(self, route):
        self.route = route

    def start(self, ai_ship):
        if self.route:
            center_x, center_y, radius = self._compute_orbit(self.route)
            ai_ship.engage_orbit(center_x, center_y, radius)

    def run(self, ai_ship):
        pass  # engage_orbit already put the ship into a standing autopilot mode that runs itself every frame

    @staticmethod
    def _compute_orbit(landables):
        """Center and radius of a circle that encloses every landable in the list."""
        center_x = sum(landable.x for landable in landables) / len(landables)
        center_y = sum(landable.y for landable in landables) / len(landables)
        radius = 0
        for landable in landables:
            margin = getattr(landable, 'landing_distance', 0)
            radius = max(radius, landable.get_distance(center_x, center_y) + margin)
        return center_x, center_y, radius


class IdleRoutine:
    """No autonomous movement - used for roles with no configured routine."""
    def __init__(self, route):
        pass

    def start(self, ai_ship):
        pass

    def run(self, ai_ship):
        pass


# Default routine per role - which Routine strategy an AI ship runs each
# frame. Roles with no entry here just get IdleRoutine (never engages the
# autopilot).
ROLE_ROUTINES = {
    "freighter_pilot": DockRoutine,
    "trader_captain": ShuttleRoutine,
    "patrol_officer": OrbitRoutine,
}

# Faction-specific overrides, checked before the role default above - lets a
# faction fly a role differently (e.g. a militarized trade faction patrolling
# instead of shuttling). Empty for now; both roles currently in use only
# belong to one faction each.
FACTION_ROUTINE_OVERRIDES = {}


class AIShip(Ship):
    """AI-controlled ship. Movement always runs through Ship's standardized
    autopilot (engage_seek / engage_orbit); only the decision of which mode
    to use, and its target, is autonomous - chosen from the pilot's faction
    and role, as a Routine strategy object (ShuttleRoutine/OrbitRoutine/
    IdleRoutine) rather than a string re-checked every frame.

    Also owns a Person (pilot_person) representing the character flying it -
    aboard and mirrored to the ship's position each frame, unless
    pilot_ashore is True (DockRoutine sets this while walking the pilot
    around a station/moon interior instead - see get_interior_screen)."""
    def __init__(self, x, y, space_drag=0, ship_type=None, ship_type_id="freighter", graphics=None, pilot=None, route=None, get_interior_screen=None):
        super().__init__(x, y, space_drag=space_drag, graphics=graphics)
        self.ship_type_id = ship_type_id
        self.angle = random.randint(0, 360)

        # Apply ship type properties if provided
        if ship_type:
            self.acceleration_magnitude = ship_type.get("max_thrust", 0.15)
            self.max_velocity = ship_type.get("max_velocity", 4.0)
            self.rotation_speed = ship_type.get("rotation_speed", 5)
        else:
            self.acceleration_magnitude = 0.15

        self.pilot = pilot or {}
        self.pilot_person = Person(x, y, name=self.pilot.get("name", ""))
        self.pilot_ashore = False  # True while DockRoutine has the pilot walking around a station/moon
        # SpaceScreen.get_interior_screen, bound - lets a routine (DockRoutine)
        # find/create a stop's interior LocationScreen without AIShip (a world
        # object) importing anything from game.screens, which this codebase
        # keeps strictly one-directional (screens depend on world, not the
        # reverse).
        self.get_interior_screen = get_interior_screen
        self.route = route or []
        self.routine = self._choose_routine()
        self.routine.start(self)

    def _choose_routine(self):
        """Decide this ship's behavior from its pilot's faction and role."""
        role = self.pilot.get("role")
        faction = self.pilot.get("faction")
        routine_cls = FACTION_ROUTINE_OVERRIDES.get((faction, role), ROLE_ROUTINES.get(role, IdleRoutine))
        return routine_cls(self.route)

    def update(self):
        """Let the job routine advance, then run standard ship autopilot/
        physics, then keep the pilot's Person aboard - unless they're
        ashore (DockRoutine), in which case it's walking them instead."""
        self.routine.run(self)
        super().update()
        if not self.pilot_ashore:
            self.pilot_person.x = self.x
            self.pilot_person.y = self.y

    def draw(self, surface):
        """Draw AI ship using graphics asset."""
        super().draw(surface)
