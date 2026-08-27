"""`DialogBase` - a modal shown *over* another modal that resolves as soon as
you pick one of its choices (control then returns to whatever opened it).

All the button infrastructure lives on `MenuBase` now; a dialog is just a
menu whose `buttons()` *are* its choices and where picking one closes it.
Subclasses provide `buttons()` and their own panel + `button_bar_rects()`
placement (a mid-panel row for a yes/no choice, a column for a list); ESC and
any letter shortcuts stay with the subclass.
"""
from game.ui.menu_base import MenuBase


class DialogBase(MenuBase):
    is_dialog = True

    def buttons(self):
        """`[(id, label, accent_rgb, disabled_bool), ...]` - the choices.
        Picking any one closes the dialog (its `id` is what `handle_input`
        returns to `main.py`)."""
        raise NotImplementedError
