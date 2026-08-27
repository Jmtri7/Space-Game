"""`MenuBase` - the shared shape every full-screen modal in `game/ui/` follows.

There are exactly two kinds of modal in this game (see
docs/DESIGN_PATTERNS.md's "Menu vs. Dialog"):

- a **menu** (`MenuBase`, `is_dialog = False`) is one you *dwell in* and leave
  explicitly (ESC / a close hotkey / "Resume"). Whenever it's the topmost modal
  it owns the top-left **Controls pane** (`ui_theme.draw_controls_pane`) - the
  same spot the base screen's own Controls pane uses, taken over wholesale.
- a **dialog** (`DialogBase`, `is_dialog = True`) sits *over* another modal,
  resolves in one action, and shows its choices as `draw_button` widgets inside
  its own panel - never a Controls pane, and the modal underneath hides its
  Controls pane too.

`draw()` here is a template method: subclasses implement `draw_content()` (their
actual panel/list/grid) plus `help_items()` (the Controls-pane rows), and this
class decides whether/where the chrome goes. `main.py` passes `chrome=False` to
whichever modal is *underneath* another one so exactly one set of controls is on
screen at a time.
"""
from game.ui.ui_theme import draw_controls_pane
from game.utils import get_ui_scale


class MenuBase:
    is_dialog = False
    controls_title = "Controls"

    def help_items(self):
        """`[(key, description), ...]` for the top-left Controls pane. Return
        `None` to suppress the pane entirely (a subclass drawing its own)."""
        raise NotImplementedError

    def active_popup(self):
        """A sub-modal (a `DialogBase`) drawn on top of this menu, e.g.
        `ShipBrowserMenu`'s purchase `ConfirmDialog`. While one is up this menu
        keeps drawing its own content but hands the chrome to the popup."""
        return None

    def draw_content(self, surface):
        """The menu's own panel/list/grid. Subclass hook - was `draw()` before
        the menu/dialog split."""
        raise NotImplementedError

    def draw(self, surface, chrome=True):
        self.draw_content(surface)

        popup = self.active_popup()
        if popup is not None:
            popup.draw(surface)
            self._controls_rect = None
            return

        self._controls_rect = None
        if chrome and not self.is_dialog:
            items = self.help_items()
            if items is not None:
                scale = get_ui_scale()
                margin = int(10 * scale)
                self._controls_rect = draw_controls_pane(
                    surface, margin, margin, self.controls_title, items, scale)
