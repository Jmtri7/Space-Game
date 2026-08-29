"""Routine: continuously circle a point enclosing every landing site in the
route - a standing patrol."""


class OrbitRoutine:
    """Continuously circle a point enclosing every landing site in the route."""
    def __init__(self, route):
        self.route = route

    def start(self, character):
        if self.route:
            center_x, center_y, radius = self._compute_orbit(self.route)
            character.engage_orbit(center_x, center_y, radius)

    def run(self, character):
        pass  # engage_orbit already put the ship into a standing autopilot mode that runs itself every frame

    @staticmethod
    def _compute_orbit(landing_sites):
        """Center and radius of a circle that encloses every landing site in the list."""
        center_x = sum(site.x for site in landing_sites) / len(landing_sites)
        center_y = sum(site.y for site in landing_sites) / len(landing_sites)
        radius = 0
        for site in landing_sites:
            margin = getattr(site, 'landing_distance', 0)
            radius = max(radius, site.get_distance(center_x, center_y) + margin)
        return center_x, center_y, radius
