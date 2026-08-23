"""Base class for all game screens."""
import pygame


class ScreenBase:
    """Base class for all game screens (space, station, moon)"""
    def __init__(self, pilot_name=""):
        self.pilot_name = pilot_name

    def handle_input(self, events):
        """Process input events. Override in subclass."""
        raise NotImplementedError

    def update(self):
        """Update game logic. Override in subclass."""
        raise NotImplementedError

    def draw(self, surface):
        """Draw screen. Override in subclass."""
        raise NotImplementedError

    def get_state(self):
        """Return game state dict for saving. Override in subclass."""
        raise NotImplementedError

    def restore_state(self, state):
        """Restore game state from dict. Override in subclass."""
        raise NotImplementedError
