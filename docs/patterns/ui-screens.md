# Patterns: UI, Menus & Screens

Scrollable lists and grids, the screen state machine, config-driven screen
dispatch, and the menu-vs-dialog split. Hub + working principles:
[DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md).

---

## Pattern: Scrollable Menu List

**Problem:** Show 5 items at a time but allow scrolling through unlimited items with visual feedback.

**Solution:** Track scroll_offset separately from selected_index.

**Implementation:**
```python
class ScrollableMenu:
    def __init__(self, items):
        self.items = items
        self.selected = 0
        self.scroll_offset = 0
        self.max_visible = 5

    def handle_input(self, events):
        for event in events:
            if event.key == DOWN:
                self.selected += 1
                if self.selected >= len(self.items):
                    self.selected = 0
                    self.scroll_offset = 0
                elif self.selected >= self.scroll_offset + self.max_visible:
                    self.scroll_offset += 1
            elif event.key == UP:
                self.selected -= 1
                if self.selected < 0:
                    self.selected = len(self.items) - 1
                    self.scroll_offset = max(0, len(self.items) - self.max_visible)
                elif self.selected < self.scroll_offset:
                    self.scroll_offset -= 1

    def draw(self, surface):
        # Show scroll indicator if not at top
        if self.scroll_offset > 0:
            draw_text(surface, "^ more")

        # Show visible items
        visible = self.items[self.scroll_offset:self.scroll_offset + self.max_visible]
        for i, item in enumerate(visible):
            is_selected = (self.scroll_offset + i == self.selected)
            draw_text(surface, item, highlight=is_selected)

        # Show scroll indicator if not at bottom
        if self.scroll_offset + self.max_visible < len(self.items):
            draw_text(surface, "v more")
```

**Why this works:**
- `scroll_offset`: What part of list to show (scrolling window)
- `selected`: Which item is highlighted (independent)
- Sync check: Adjusts scroll when selection moves outside window
- Wrapping: Selection loops at boundaries

**Use case:** Menus/lists that might exceed visible area.

---

## Pattern: Scrollable List Handler (Shared Logic)

**Problem:** The save and load screens both duplicate up/down navigation with wrapping and scroll-sync.

**Solution:** Extract to a pure function that returns (new_selected, new_scroll_offset).

**Implementation:**
```python
def _handle_scrolling_input(key, selected, items, scroll_offset, max_visible):
    """Handle up/down navigation with wrapping and auto-scroll."""
    if key in (pygame.K_UP, pygame.K_w):
        selected -= 1
        if selected < 0:
            selected = len(items) - 1
            scroll_offset = max(0, len(items) - max_visible)
        elif selected < scroll_offset:
            scroll_offset -= 1
    elif key in (pygame.K_DOWN, pygame.K_s):
        selected += 1
        if selected >= len(items):
            selected = 0
            scroll_offset = 0
        elif selected >= scroll_offset + max_visible:
            scroll_offset += 1
    return selected, scroll_offset

# SelectableList.handle_key() calls it; SaveBrowser (both modes) and
# ChoiceDialog's old list form all went through SelectableList.
self.selected, self.scroll_offset = _handle_scrolling_input(
    event.key, self.selected, self.items, self.scroll_offset, self.max_visible)
```

**Why this works:**
- Pure function (no side effects, testable in isolation)
- Reusable everywhere a list scrolls, via `SelectableList` (DRY)
- Single place to fix boundary/wrapping bugs
- Easy to add new key bindings (modify function signature once)

**Use case:** Multiple menus/lists that all need identical scrolling behavior.

---

## Pattern: 2D Grid Sibling to a Scrollable List

**Problem:** ShopMenu's buy/sell lists needed to read as a grid of icons
(name/price/quantity per cell) rather than one item per line, but
`SelectableList`'s navigation is 1D (up/down only) and its `draw()` assumes
a single column of text.

**Solution:** Rather than bolting grid support onto `SelectableList`, add a
sibling class (`IconGrid`, `game/ui/icon_grid.py`) with the same
`items`/`selected`/`current()` shape, but `handle_key()` understands
Left/Right (step through row-major order, wrapping) and Up/Down (jump a
full row, clamping - not wrapping - on a ragged last row). `draw()` stays
layout-only: it hands each cell's `pygame.Rect` to a caller-supplied
`cell_draw_fn(surface, rect, item, is_selected, reason)` instead of
rendering text itself, so the grid has no opinion about icons/fonts/colors.

**Why this works:**
- Same mental model as `SelectableList` (selection + scroll state, a
  `disabled_fn`/`reason` contract) so callers familiar with one can read
  the other, without forcing 1D and 2D navigation into one class's
  `handle_key()`.
- `cell_draw_fn` keeps `IconGrid` reusable for any grid content (it doesn't
  know what a "cell" looks like) the same way `_handle_scrolling_input`
  stays reusable by not knowing what a "row" looks like.

**Use case:** Any menu where content reads better as a 2D grid (icons,
thumbnails, a shop shelf) than a single vertical list - see `ShopMenu`,
`OutfittingMenu`'s Buy tab, and `ShipBrowserMenu`'s ship grid. All three
share one `cell_draw_fn` implementation too - `ui_theme.draw_shop_cell`
(highlight + icon + name + price/quantity, with a disabled `reason` always
left visible alongside the price rather than replacing it) - so each menu's
own `_draw_cell` only has to supply an `icon_fn` (a procedural item glyph,
or a static ship silhouette) and the name/detail strings.

---

## Pattern: Screen State Machine

**Problem:** Complex navigation between multiple screens (menu, game, pause, load, etc.).

**Solution:** Main loop interprets action strings to manage state transitions.

**Implementation:**
```python
current_screen = "menu"
menu = Menu()

while running:
    events = pygame.event.get()

    if current_screen == "menu":
        action = menu.handle_input(events)
        if action == "new":
            game_screen = SpaceScreen()
            current_screen = "game"
        elif action == "load":
            load_menu = SaveBrowser("load")
            current_screen = "load"

    elif current_screen == "game":
        action = game_screen.handle_input(events)
        if action == "pause":
            current_screen = "pause"
        game_screen.update()
        game_screen.draw(screen)

    elif current_screen == "pause":
        action = pause_menu.handle_input(events)
        if action == "resume":
            current_screen = previous_screen
        # ... draw
```

**Why this works:**
- Centralized state management
- Clear transitions (action string → new state)
- Easy to add screens (new elif branch)
- Separates input handling from state logic

**Use case:** Menu-driven games with multiple screens.

> **Note:** the real loop in `main.py` splits each iteration into three
> phases — input/transitions, then a fixed-timestep simulation, then render
> (see "Fixed-Timestep Accumulator" in [movement.md](movement.md)). Input and
> render still branch on `current_screen` the way shown above; only simulation
> is consolidated.

---

## Pattern: Config-Driven Screen Dispatch ("shop" NPCs)

**Problem:** Several different screen classes need to open from the same
trigger (talking to an NPC), where which class opens depends on what that
NPC is configured to do - a ship salesman needs a ship browser, a
quartermaster needs a commodities list, an outfitter needs a slot diagram.
Hardcoding "if this NPC's name is X, open Y" doesn't scale, and cramming
every case into one mega-menu class fights each screen's very different
layout needs.

**Solution:** Give the NPC config one key naming *what kind* of interaction
this is (`"shop": {"type": "commodities"|"items"|"ships"|"outfits", ...}`),
checked before falling back to the default interaction (`Dialogue`). A
single small dispatcher function picks the concrete screen class from that
`type`, so the call site (the input handler that reacts to "talk to this
NPC") never needs to know the full set of possible screens - only that
"shop config present" means "ask the dispatcher."

**Implementation:** (`LocationScreen._build_local_character`, `handle_input`;
`main.py`'s `build_shop_menu`)
```python
# NPC config: a "shop" key instead of (or alongside) a dialogue_tree
{"name": "Reeve Katic", "role": "outfitter",
 "shop": {"type": "outfits", "stock": ["laser_cannon", "afterburner"]}}

# Attached to the NPC's Person at build time, like dialogue is:
person.shop = cfg.get("shop")

# Checked first when the player interacts (T) - shop bypasses Dialogue
# entirely rather than being folded into it:
if target_npc.shop:
    self.active_shop = target_npc.shop
    return "shop"

# One dispatcher picks the concrete screen class by "type":
def build_shop_menu(possessions, story, shop_config, cargo_capacity, buy_ship_fn, on_outfits_changed):
    shop_type = shop_config.get("type")
    if shop_type == "ships":
        return ShipBrowserMenu(possessions, story, shop_config, on_buy=buy_ship_fn)
    if shop_type == "outfits":
        ship_type_id = possessions.owned_ships[-1] if possessions.owned_ships else None
        return OutfittingMenu(possessions, story, shop_config, ship_type_id, on_outfits_changed=on_outfits_changed)
    return ShopMenu(possessions, story, shop_config, cargo_capacity=cargo_capacity)
```

**Why this works:**
- The NPC config only declares *intent* ("I sell outfits"), not *how* to
  render that - the dispatcher owns the type→class mapping in one place, so
  adding a fifth shop type later is a one-line addition there, not a change
  scattered across every place an NPC can be talked to.
- Every resulting screen still shares the same underlying UI building
  blocks (`SelectableList`, `ui_theme`'s panel/title helpers, `ConfirmDialog`)
  even though each is its own class - config-driven dispatch picks the
  *class*, it doesn't force one mega-class with an internal mode switch for
  every possible shape of shop.
- Matches the "Role → Routine Registry" pattern (in [entities.md](entities.md))
  applied one layer up, to picking a screen instead of a routine.

**Use case:** Any place a single trigger (NPC interaction, a world object,
a menu option) needs to open one of several purpose-built screens depending
on config, without the trigger's own code needing to know about all of them.

---

## Pattern: Menu vs. Dialog (`MenuBase` / `DialogBase`)

**Problem:** Every full-screen modal in `game/ui/` re-implemented its own
"chrome" - some drew a top-left Controls pane (`draw_controls_pane`), some a
help line inside their panel, `LocationSelector` drew nothing, `ExitMenu` (a
one-shot picker) drew a full Controls pane like a dwelling menu. Nothing
enforced a consistent rule, and there were four pairs of near-duplicate
classes (`Menu`/`StorySelector`, `LocationSelector`/`ExitMenu`,
`PossessionsMenu`/`MissionLog`, `LoadMenu`/`SaveDialog`).

**Solution:** No modal draws a Controls pane (that pane is the in-world HUD's
alone). Every modal presents its actions as `ui_theme.draw_button` widgets
inside its own panel, and **is mouse-only** - hover highlights, left-click
presses; the keyboard is used only to type into a text field (pilot name,
new save name), never to move a selection or press a button, and there is no
ESC-to-close (every modal has a visible Close/Cancel/Resume/Back button).
`ESC` closes a modal, but this is handled in `main.py`'s state machine
(`_pressed_any`), never in the menu classes, which stay strictly
mouse-only: the pause menu (`ESC`), Star Map (`M`), Possessions (`P`), and
Mission Log (`N`) each also close on their own opening key; the shop /
outfitter / shipyard family (opened with `T` on an NPC, so no opening key
to toggle) closes on `ESC` alone, and a pending purchase `ConfirmDialog`
eats the `ESC` as a cancel first. A save/load `SaveBrowser` stacked on the
pause menu still swallows `ESC` (`dialog_was_open`) - close it with its
button.
There is no dim hint line - a modal is expected to be self-explanatory from
its buttons and labels.

**The NPC conversation / hail box is not one of these `game/ui/` modals** -
it's a `game/world/dialogue.py` `Dialogue` drawn and driven directly by
`SpaceScreen` / `LocationScreen`, not a `MenuBase`. It keeps the mouse for
picking options (hover + click, or the ✕) but also closes on **ESC** and
picks the highlighted option on **Enter**: a story conversation you can only
leave by finding the ✕ is a trap, and ESC while it's open closes the
conversation instead of opening the pause menu (handled in the screen's
`handle_input`, inside its `if self.active_dialogue:` branch).

Two base classes:

- **`MenuBase`** (`game/ui/menu_base.py`) - a **menu** you *dwell in*;
  acting doesn't close it. Owns all the button infrastructure: `buttons()` →
  `[(id, label, accent, disabled), ...]`, `button_bar_rects()` → where they
  go (default: a centred row along the panel bottom, `max_width`-clamped to
  the panel; a corner-Close menu overrides it), `panel_rect()` → the glass
  panel the default bar anchors to. `draw()` is a template method (content →
  `active_popup()` if a sub-dialog is up → buttons). `handle_button_event()`
  (alias `handle_button_click`) does hover + left-click only. `_is_double_
  click()` lets a list/grid treat a double-click as "activate".
- **`DialogBase(MenuBase)`** - a **dialog** shown *over* another modal that
  closes as soon as you click one of its `buttons()`. Adds nothing but
  `is_dialog = True` and the "clicking closes" semantics.

**Why this works:**
- One `draw()` template + one button-input path, not 15 copies of chrome.
- Classifying by *persistence* resolves the awkward cases: `SaveBrowser`
  stays open through delete/scroll/mode-switch → menu; `ChoiceDialog`
  pick-and-go → dialog.
- One widget per shape instead of per screen: `BackdropMenu(title, rows,
  seed, allow_cancel)` covers the main menu and story picker (a **Back**
  button appears when `allow_cancel`); `ChoiceDialog(title, options)` covers
  moon-landing and exit-door picking (a **Cancel** button is always
  appended); `ReportMenu(title, columns, tabs=None)` + a builder fn covers
  the possessions and mission read-outs; `SaveBrowser(mode)` covers load and
  save. `main.py` builds the data, the widget doesn't know the domain.

**Use case:** Any new full-screen modal - decide menu vs. dialog by "can you
navigate inside it without it closing?", subclass the matching base, provide
`buttons()` + `panel_rect()`, and the chrome is handled. Reach for an
existing widget (`BackdropMenu`, `ChoiceDialog`, `ReportMenu`) first.
