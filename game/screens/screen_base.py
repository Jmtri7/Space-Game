"""Base class for all game screens."""
from abc import ABC, abstractmethod


class ScreenBase(ABC):
    """Base class for all game screens (space, station, moon). A real ABC -
    not just NotImplementedError stubs - so a subclass missing one of these
    fails at class-definition time (can't be instantiated) instead of only
    surfacing the gap when that particular method finally gets called."""
    def __init__(self, pilot_name=""):
        self.pilot_name = pilot_name
        # Top-left Controls pane starts collapsed to just its title + a
        # "C : Show controls" line - the full reference is a keypress away
        # but out of the way by default. Toggled with C in either screen.
        self.controls_collapsed = True

    def _toggle_controls(self):
        self.controls_collapsed = not self.controls_collapsed

    @abstractmethod
    def handle_input(self, events):
        """Process input events."""

    @abstractmethod
    def update(self):
        """Update game logic."""

    @abstractmethod
    def draw(self, surface):
        """Draw screen."""

    @abstractmethod
    def get_state(self):
        """Return game state dict for saving."""

    @abstractmethod
    def restore_state(self, state):
        """Restore game state from dict."""
