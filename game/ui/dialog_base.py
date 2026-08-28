"""`DialogBase` - a modal shown *over* another modal that resolves as soon as
you click one of its choices (control then returns to whatever opened it).

All the button infrastructure lives on `MenuBase`; a dialog is just a menu
whose `buttons()` *are* its choices and where clicking one closes it.
Subclasses provide `buttons()` and their own panel + `button_bar_rects()`
placement (a mid-panel row for a yes/no choice, a column for a list). Like
every menu it is mouse-only - the safe/cancel choice is always one of the
buttons, so there is no ESC shortcut.
"""
from game.ui.menu_base import MenuBase


class DialogBase(MenuBase):
    is_dialog = True

    def buttons(self):
        """`[(id, label, accent_rgb, disabled_bool), ...]` - the choices.
        Clicking any one closes the dialog (its `id` is what `handle_input`
        returns to `main.py`)."""
        raise NotImplementedError
