"""LocationScreen: dialogue — mixed into the class in screen.py."""
from game.screens.location_screen._defs import *  # noqa: F401,F403


class _DialogueMixin:

    def _first_selectable_option(self, options):
        """Index of the first option _option_blocked_reason doesn't block -
        used whenever the selection needs to (re)start (opening a
        conversation, arriving at a new node) so it's never pre-highlighted
        on an option the player can't actually take."""
        for i, option in enumerate(options):
            if not self._option_blocked_reason(option):
                return i
        return 0  # every option blocked - nothing better to land on

    def _choose_dialogue_option(self, index):
        """Act on the visible option at `index` (a mouse click on it) - apply
        its actions, then advance/close the conversation. Shared by the click
        handler; mirrors the old Enter path."""
        flags = self.player.possessions.flags
        rep = self.player.possessions.reputation
        options = self.active_dialogue.current_options(flags, rep)
        if not 0 <= index < len(options):
            return
        option = options[index]
        if self._option_blocked_reason(option):
            return
        for action in option_actions(option):
            self._apply_dialogue_action(action)
        # advance(option), not choose(index, ...) - an action just applied
        # (set_flag:/adjust_rep:) can change what current_options() returns.
        if self.active_dialogue.advance(option):
            self.active_dialogue = None
        else:
            self.active_dialogue.selected_option = self._first_selectable_option(
                self.active_dialogue.current_options(flags, rep))
