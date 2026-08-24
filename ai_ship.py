"""AI ship whose behavior is driven by its pilot's job routine."""
import random
from ship import Ship

# Maps a pilot's role to the routine that decides its autopilot target each frame.
# Roles with no entry here just sit idle (autopilot never engages).
ROLE_ROUTINES = {
    "freighter_pilot": "shuttle",
    "patrol_officer": "shuttle",
    "trader_captain": "shuttle",
}


class AIShip(Ship):
    """AI-controlled ship. Movement uses the same Ship.update_autopilot() as the
    player; only the choice of autopilot target is autonomous, driven by the
    pilot's role."""
    def __init__(self, x, y, space_drag=0, ship_type=None, ship_type_id="trader", graphics=None, pilot=None, route=None):
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
        self.routine = ROLE_ROUTINES.get(self.pilot.get("role"), "idle")
        self._route_index = 0

        if self.routine == "shuttle" and self.route:
            self.autopilot_target = self.route[0]
            self.autopilot_active = True

    def update(self):
        """Let the job routine pick a target, then run standard ship autopilot/physics."""
        self._run_routine()
        super().update()

    def _run_routine(self):
        if self.routine == "shuttle":
            self._run_shuttle_routine()

    def _run_shuttle_routine(self):
        """Ping-pong between the stops in self.route, one at a time."""
        if not self.route:
            return
        if not self.autopilot_active:
            self._route_index = (self._route_index + 1) % len(self.route)
            self.autopilot_target = self.route[self._route_index]
            self.autopilot_active = True

    def draw(self, surface):
        """Draw AI ship using graphics asset."""
        super().draw(surface)
