"""A scrollable, keyboard-navigable grid of selectable items, row-major,
`columns` wide - the layout ShopMenu uses so commodities/items read as a
shop shelf of icons instead of a bare price list. Sibling to SelectableList
(see docs/DESIGN_PATTERNS.md) for content that reads better as a 2D grid
than a single vertical column; IconGrid only owns selection/scroll layout,
leaving all drawing to a caller-supplied cell_draw_fn so it stays agnostic
about what a "cell" actually shows."""
import pygame


class IconGrid:
    """Owns selection/scroll state for a grid of items. Navigation always
    stays within the full item list - disabled items (e.g. can't afford)
    are still freely selectable so the player can browse/preview every
    item, the same way ShipBrowserMenu's list no longer skips over ships
    it can't afford; it's up to the caller to block the actual transaction
    on a disabled item, not to hide it from navigation."""

    def __init__(self, items, columns=3, max_rows=2):
        self.items = items
        self.columns = columns
        self.max_rows = max_rows
        self.selected = 0
        self.scroll_row = 0
        # {item_index: pygame.Rect}, screen space, for whichever cells were
        # visible the last time draw() ran - lets a caller hit-test a mouse
        # click against exactly what's currently on screen (see index_at),
        # the same "cache during draw, hit-test next frame" idiom
        # OutfittingMenu's own _slot_rects/_owned_item_rects already use.
        self.last_rects = {}

    def _clamp(self):
        if not self.items:
            self.selected = 0
            self.scroll_row = 0
            return
        self.selected = max(0, min(self.selected, len(self.items) - 1))
        total_rows = (len(self.items) + self.columns - 1) // self.columns
        max_scroll = max(0, total_rows - self.max_rows)
        selected_row = self.selected // self.columns
        if selected_row < self.scroll_row:
            self.scroll_row = selected_row
        elif selected_row >= self.scroll_row + self.max_rows:
            self.scroll_row = selected_row - self.max_rows + 1
        self.scroll_row = max(0, min(self.scroll_row, max_scroll))

    def current(self):
        """The currently selected item, or None if the grid is empty."""
        self._clamp()
        return self.items[self.selected] if self.items else None

    def scroll(self, delta):
        """Move the selection `delta` rows (mouse-wheel handler); `_clamp()`
        then pulls `scroll_row` along so it stays visible - the mouse-only
        equivalent of Up/Down."""
        if not self.items:
            return
        self._clamp()
        self.selected = max(0, min(self.selected + delta * self.columns, len(self.items) - 1))
        self._clamp()

    def handle_key(self, key):
        """Move the selection one step for an UP/DOWN/LEFT/RIGHT (or W/S)
        keypress, wrapping at the ends of the item list. Left/Right step
        through the flat row-major order (so they also cross row
        boundaries); Up/Down jump a full row, clamping to the nearest
        valid cell in the first/last row rather than wrapping, since
        wrapping vertically across a ragged last row has no single
        "correct" column to land on."""
        if not self.items:
            return
        self._clamp()
        count = len(self.items)
        if key == pygame.K_RIGHT:
            self.selected = (self.selected + 1) % count
        elif key == pygame.K_LEFT:
            self.selected = (self.selected - 1) % count
        elif key in (pygame.K_DOWN, pygame.K_s):
            candidate = self.selected + self.columns
            self.selected = candidate if candidate < count else count - 1
        elif key in (pygame.K_UP, pygame.K_w):
            candidate = self.selected - self.columns
            self.selected = candidate if candidate >= 0 else self.selected % self.columns
        self._clamp()

    @property
    def has_more_above(self):
        return self.scroll_row > 0

    @property
    def has_more_below(self):
        total_rows = (len(self.items) + self.columns - 1) // self.columns
        return self.scroll_row + self.max_rows < total_rows

    def draw(self, surface, top_left, cell_width, cell_height, gap, cell_draw_fn, disabled_fn=None):
        """Draw the visible window of rows starting at `top_left` (screen
        px). cell_draw_fn(surface, rect, item, is_selected, reason) draws
        one cell's content - IconGrid only computes each cell's rect and
        which item/selection state goes in it. disabled_fn(item) -> reason
        string or None, same contract as SelectableList."""
        self._clamp()
        self.last_rects = {}
        if not self.items:
            return
        x0, y0 = top_left
        start_index = self.scroll_row * self.columns
        end_index = min(len(self.items), start_index + self.columns * self.max_rows)
        for i in range(start_index, end_index):
            item = self.items[i]
            row = (i - start_index) // self.columns
            col = (i - start_index) % self.columns
            rect = pygame.Rect(x0 + col * (cell_width + gap), y0 + row * (cell_height + gap), cell_width, cell_height)
            self.last_rects[i] = rect
            is_selected = (i == self.selected)
            reason = disabled_fn(item) if disabled_fn else None
            cell_draw_fn(surface, rect, item, is_selected, reason)

    def index_at(self, pos):
        """Item index whose cell (from the most recent draw()) contains
        screen point pos, or None - lets a caller translate a mouse click
        into a grid selection, the same way handle_key() does for arrows."""
        for index, rect in self.last_rects.items():
            if rect.collidepoint(pos):
                return index
        return None
