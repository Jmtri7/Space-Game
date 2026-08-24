"""AI ship whose behavior is chosen by its pilot's faction and role."""
import random
from game.world.ship import Ship

# Default routine per role - what the ship does with its autopilot each frame.
# Roles with no entry here just sit idle (autopilot never engages).
ROLE_ROUTINES = {
    "freighter_pilot": "shuttle",
    "trader_captain": "shuttle",
    "patrol_officer": "orbit",
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
    and role."""
    def __init__(self, x, y, space_drag=0, ship_type=None, ship_type_id="freighter", graphics=None, pilot=None, route=None):
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
        self.route = route or []
        self.routine = self._choose_routine()
        self._route_index = 0

        if self.routine == "shuttle" and self.route:
            self.engage_seek(self.route[0])
        elif self.routine == "orbit" and self.route:
            center_x, center_y, radius = self._compute_orbit(self.route)
            self.engage_orbit(center_x, center_y, radius)

    def _choose_routine(self):
        """Decide this ship's behavior from its pilot's faction and role."""
        role = self.pilot.get("role")
        faction = self.pilot.get("faction")
        return FACTION_ROUTINE_OVERRIDES.get((faction, role), ROLE_ROUTINES.get(role, "idle"))

    def _compute_orbit(self, landables):
        """Center and radius of a circle that encloses every landable in the list."""
        center_x = sum(landable.x for landable in landables) / len(landables)
        center_y = sum(landable.y for landable in landables) / len(landables)
        radius = 0
        for landable in landables:
            margin = getattr(landable, 'landing_distance', 0)
            radius = max(radius, landable.get_distance(center_x, center_y) + margin)
        return center_x, center_y, radius

    def update(self):
        """Let the job routine advance, then run standard ship autopilot/physics."""
        self._run_routine()
        super().update()

    def _run_routine(self):
        if self.routine == "shuttle":
            self._run_shuttle_routine()
        # "orbit" needs no per-frame decision here - engage_orbit already put
        # the ship into a standing autopilot mode that runs itself every frame.

    def _run_shuttle_routine(self):
        """Ping-pong between the stops in self.route, one at a time."""
        if not self.route:
            return
        if not self.autopilot_active:
            self._route_index = (self._route_index + 1) % len(self.route)
            self.engage_seek(self.route[self._route_index])

    def draw(self, surface):
        """Draw AI ship using graphics asset."""
        super().draw(surface)
