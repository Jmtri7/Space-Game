"""Routine: continuously circle a point enclosing every landable in the
route - a standing patrol."""


class OrbitRoutine:
    """Continuously circle a point enclosing every landable in the route."""
    def __init__(self, route):
        self.route = route

    def start(self, character):
        if self.route:
            center_x, center_y, radius = self._compute_orbit(self.route)
            character.engage_orbit(center_x, center_y, radius)

    def run(self, character):
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
