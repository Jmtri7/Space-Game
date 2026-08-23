"""Confirmation for deleting a save."""
from confirm_dialog import ConfirmDialog


class DeleteConfirmDialog(ConfirmDialog):
    """Confirmation for deleting a save"""
    def __init__(self, save_filename):
        self.save_filename = save_filename
        super().__init__("Delete Save?", save_filename[:50])

    def handle_input(self, events):
        result = super().handle_input(events)
        if result == "confirm":
            return ("confirm", self.save_filename)
        elif result == "cancel":
            return ("cancel", None)
        return (None, None)
