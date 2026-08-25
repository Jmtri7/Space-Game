"""Routine: ping-pong between the stops in a route, one at a time, with an
instant turnaround at each (no walking-around errand - see DockRoutine for
that)."""


class ShuttleRoutine:
    """Ping-pong between the stops in a route, one at a time."""
    def __init__(self, route):
        self.route = route
        self._route_index = 0

    def start(self, character):
        if self.route:
            character.engage_seek(self.route[0])

    def run(self, character):
        if not self.route:
            return
        if not character.autopilot_active:
            self._route_index = (self._route_index + 1) % len(self.route)
            character.engage_seek(self.route[self._route_index])
