"""Routine: stay exactly where placed - for local characters with a fixed
post (behind a counter, at a desk) rather than wandering."""


class StationaryRoutine:
    """No-op routine - the character never moves on its own."""
    def __init__(self, route):
        pass

    def start(self, character):
        pass

    def run(self, character):
        pass
