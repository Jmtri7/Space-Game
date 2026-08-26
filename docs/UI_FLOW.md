# UI Flow & Screen State Machine

Menu hierarchy, screen transitions, and state management.

## Screen State Machine

```
                          ┌────────────────┐
                          │      MENU       │
                          │ NEW/LOAD/QUIT   │
                          └───────┬─────────┘
                     ┌────────────┴────────────┐
              ┌──────▼───────┐           ┌──────▼──────┐
              │ STORY SELECT │           │  LOAD MENU  │
              └──────┬───────┘           │(scrollable) │
              ┌──────▼───────┐           └──────┬──────┘
              │ PILOT NAME   │                  │
              └──────┬───────┘                  │
                     │                          │
              ┌──────▼──────────────────────────▼──┐
              │            GAME (SpaceScreen)        │◄───────────┐
              └───┬───────────────────────────┬─────┘            │
        (L: land on station)         (L: land on moon)           │
                  │                           │                   │
          ┌───────▼────────┐        ┌─────────▼─────────┐         │
          │ STATION         │        │ LOCATION SELECTOR │         │
          │ (LocationScreen)│        │ (city/wilderness) │         │
          └───────┬────────┘        └─────────┬─────────┘         │
             (L: exit) ─────────────► GAME     │                   │
                  │                  ┌─────────▼─────────┐         │
                  │                  │  MOON              │         │
                  │                  │ (LocationScreen)   │         │
                  │                  └─────────┬─────────┘         │
                  │                       (L: exit) ────────────────┘
                  │                                                │
        ┌─────────▼────────────────────────────────────────────────▼──┐
        │                          PAUSE MENU                          │
        │                    Resume / Save / Quit                     │
        └───┬───────────────────────────┬───────────────────────┬────┘
            │                           │                       │
    ┌───────▼──────┐          ┌─────────▼─────────┐   ┌─────────▼─────────┐
    │ SAVE DIALOG  │          │ OVERWRITE CONFIRM  │   │  DELETE CONFIRM   │
    │ (scrollable) │──(D)────►│    (ConfirmDialog)  │   │  (ConfirmDialog)  │
    └──────────────┘          └────────────────────┘   └────────────────────┘
```

`LoadMenu` also has its own delete flow (its own `ConfirmDialog` instance) for
removing a save directly from the Load screen, independent of the Pause-menu
Save dialog's delete flow shown above.

The diagram above shows the simple case where a `LocationScreen`'s exit
(`L` near a portal) leads to only one place, and so acts immediately. A
location can have more than one portal (see STATION / MOON below); when
the one the player is standing next to has `connected_locations` and/or
`return_to_ship` adding up to more than one destination, `L` instead opens
`ExitMenu` - the player picks "Return to Ship" (→ GAME) or a connected
location (→ that location's own `LocationScreen`, staying in
`"station"`/`"moon"`).

## Screen Descriptions

### Main Menu (`Menu`)
**States:** Showing NEW, LOAD (if saves exist), QUIT
- LOAD appears dynamically when save files exist
- Menu recreated each time user returns (refreshes LOAD visibility)

**Transitions:**
- NEW → `StorySelector`
- LOAD → `LoadMenu`
- QUIT → Exit application

### StorySelector
**Shows:** List of playable stories, scanned from `config/stories/*/story.json`, with each story's description

**Inputs:** UP/DOWN or W/S: navigate · RETURN: select · ESC: cancel

**Transitions:**
- RETURN → `PilotNameDialog` (remembers `selected_story`)
- ESC → Menu

### PilotNameDialog
**Shows:** Text entry box for the pilot's name (30 char max)

**Inputs:** Type: add to name · BACKSPACE: delete last char · RETURN: confirm · ESC: cancel

**Transitions:**
- RETURN (non-empty name) → `SpaceScreen` created with `pilot_name` and `story`, then straight into `"station"` at the `"dormitory"` interior (0 credits, no ship - see the station layout under STATION / MOON below) rather than `"game"`
- ESC → Menu

### LoadMenu (Scrollable)
**Shows:** All save files from `saves/` directory, 5 at a time

**Inputs:** UP/DOWN or W/S: navigate (scrolls at boundaries) · RETURN: load · D: delete (opens its own `ConfirmDialog`) · ESC: cancel

**Transitions:**
- RETURN → Reads `game_state["location"]` from the save (`"space"` / `"station"` / `"moon"`) and jumps straight to the matching screen with state restored:
  - `"space"` → `SpaceScreen`
  - `"station"` → `SpaceScreen` (background) + `LocationScreen` for the station interior
  - `"moon"` → `SpaceScreen` (background) + `LocationScreen` for the saved moon location
- ESC → Menu

### GAME — `SpaceScreen`
**Shows:** Space view with player ship, AI ships, star field, station, moon, target HUD

**Inputs:**
- LEFT/RIGHT or A/D: rotate ship
- UP or W: thrust forward
- DOWN or S: turn to face reverse velocity
- T: cycle target (station, moon, each AI ship)
- L: land (or engage autopilot toward the current target if out of range)
- ESC: pause

**Transitions:**
- L, close + slow near station → `LocationScreen` (station interior)
- L, close + slow near moon → `LocationSelector`
- ESC → PauseMenu

### LocationSelector
**Shows:** Moon landing sub-location choices (City / Wilderness), built from the moon's `interiors` config

**Inputs:** UP/DOWN or W/S: navigate · RETURN: select · ESC: cancel (returns to `SpaceScreen`)

**Transitions:**
- RETURN → `LocationScreen` for the chosen moon location
- ESC → GAME

### STATION / MOON — `LocationScreen`
**Shows:** Top-down walkable view of the interior/exterior with NPCs. One generic,
config-driven class used for both the station interior and every moon location —
not a station-only or moon-only screen.

The station's `interiors` now form a small connected graph, not just one
room: `dormitory` (new game starts here, no `return_to_ship`) ↔ `corridor`
↔ `default` (the concourse - kept as that key so `DockRoutine`'s station
lookup needs no changes) ↔ `spaceport` (ship salesman, `return_to_ship:
true` but disabled until a ship is owned - see `ship_available` below) /
`loan_office` (loan officer). See `config/stories/default/systems/
sol_alpha.json`.

A location can have more than one **portal** (`LocationScreen.portals`) -
a junction with several real destinations (like the concourse, which
connects to the corridor, spaceport, and loan office) gets one physically
distinct portal per destination instead of a single spot that offers all
of them, so walking back through the specific portal you arrived from
always leads back the way you came (`LocationScreen.arrive_from()`/
`portal_for()`) rather than re-presenting every destination the location
has. A config with only one exit still uses the older flat `"entrance"`/
`"connected_locations"`/`"return_to_ship"` keys, normalized into a
single-item portal list internally.

**Inputs:**
- LEFT/RIGHT/UP/DOWN or WASD: move
- L: exit (only within range of a portal) - see `get_available_exit_options()`, scoped to whichever portal is nearest:
  - Exactly one destination *and it's actually usable* → goes there immediately (`"exit"` → GAME, or `"exit_to:<key>"` → that connected location)
  - More than one configured, or the only one isn't usable yet (e.g. "ship" with no ship owned) → opens `ExitMenu`, so an unusable option is still visible with its reason instead of L doing nothing
- T (with an NPC targeted, in range): talk - opens that NPC's `Dialogue` (see below)
- P: `PossessionsMenu`
- ESC: pause

While docked, `SpaceScreen.update_physics()` still runs in the background (ships keep moving), just without camera updates.

**Transitions:**
- L (near a portal, single usable destination) → GAME or a connected location's `LocationScreen`
- L (near a portal, multiple destinations, or the only one isn't usable) → `ExitMenu`
- T (NPC targeted, in range, no `"shop"` config) → that NPC's `Dialogue`, always restarted at its root node
- T (NPC targeted, in range, has a `"shop"` config) → `ShopMenu` instead of `Dialogue`
- P → `PossessionsMenu`
- ESC → PauseMenu

### Dialogue
**Shows:** A conversation tree (`game/world/dialogue.py`) - most NPCs are a
single node with closing options only ("Thanks"/"Leave", built via
`Dialogue.from_flat`); a few (Bartender, the spaceport's salesman, the loan
officer) have a real `dialogue_tree` in config where an option's `"next"`
leads to another node instead of closing. An option can also carry an
`"action"` (`"buy_ship:<ship_type_id>"`, `"take_loan"`) applied by
`LocationScreen` right before advancing - this is how buying a ship or
taking a loan works today. An action option unaffordable or otherwise
blocked (`LocationScreen._option_blocked_reason`) renders dim with the
reason and can't be selected. NPCs selling commodities or personal items use
`ShopMenu` instead (see below) - a `"shop"` config key bypasses `Dialogue`
entirely rather than being another dialogue action.

**Inputs:** UP/DOWN or W/S: navigate · RETURN: choose (advance, close, or apply an action then advance/close) · ESC: close immediately

**Transitions:**
- RETURN on a closing option (`"next": null`) → dialogue closes
- RETURN on a branching option → advances to that node, dialogue stays open
- ESC → dialogue closes immediately, wherever it was in the tree

### ExitMenu
**Shows:** The destinations offered by the current location's exit - each
`connected_locations` key (labeled from that sibling interior's own
`"label"`) plus "Return to Ship" if `return_to_ship` allows it. Shown
whenever there's more than one configured option, or the single option
isn't currently usable (e.g. "ship" with `get_exit_disabled_reasons()`
returning `{"ship": "no ship docked here"}` - the spaceport before a
purchase). Disabled entries render dim with their reason and can't be
selected. AI pilots (`DockRoutine`) pick from this same option list
automatically via `ROLE_EXIT_PREFERENCE` instead of getting a menu.

**Inputs:** UP/DOWN or W/S: navigate · RETURN: select (no-op on a disabled entry) · ESC: cancel (stay in the current location)

**Transitions:**
- RETURN on "Return to Ship" → GAME
- RETURN on a connected location → that location's `LocationScreen` (still `"station"`/`"moon"`)
- ESC → back to the location the menu was opened from

### PossessionsMenu
**Shows:** Read-only credits, owned ships, and loans - `game/ui/
possessions_menu.py`. Opened over whichever screen it was opened from
(space, station, or moon), which is redrawn underneath it.

**Inputs:** P or ESC: close

**Transitions:**
- P or ESC → back to whichever screen opened it (`possessions_return_screen` in `main.py`)

### ShopMenu
**Shows:** Buy/sell for commodities or personal items - `game/ui/
shop_menu.py`. Opened by talking (T) to an NPC whose config has a `"shop"`
key (`{"type": "commodities"|"items", "stock": [...], "sell_multiplier": ...}`)
instead of that NPC's `Dialogue`. Buy tab lists `stock` priced from
`commodities.json`/`items.json`; Sell tab lists whatever's currently in
`possessions.cargo`/`.items` for that category, priced at
`base_price * sell_multiplier`. Drawn over whichever screen it was opened
from (station or moon), same overlay pattern as `PossessionsMenu`. Ships and
ship outfits get their own dedicated menus, not this one.

**Inputs:** LEFT/RIGHT or TAB: switch Buy/Sell · UP/DOWN or W/S: navigate ·
RETURN: buy/sell one unit of the selected item · ESC: close

**Transitions:**
- ESC → back to whichever screen opened it (`shop_return_screen` in `main.py`)

### ShipBrowserMenu
**Shows:** Ship-buying with a live preview - `game/ui/ship_browser_menu.py`.
Opened the same way as `ShopMenu` (T on an NPC with a `"shop"` config), but
for `"type": "ships"` - `main.py`'s `build_shop_menu()` dispatches to this
instead of `ShopMenu` based on the shop config's `type`. Left: the shop's
stock ship-type ids. Right: a live preview (`ui_theme.draw_ship_glyph`) and
stat readout for whichever is selected. Enter opens a `ConfirmDialog`;
confirming calls the injected `on_buy` callback, which `main.py` wires to
`LocationScreen.buy_ship()` - the same mutation the old `"buy_ship:<id>"`
dialogue action performed (spend, `add_ship`, `on_ship_purchased`
callback), now shared by both purchase paths. The spaceport's ship salesman
(`sol_alpha.json`'s Dax Renner) uses this instead of a `dialogue_tree`.

**Inputs:** UP/DOWN or W/S: navigate · RETURN: open purchase confirmation ·
Y/N or ESC: confirm/cancel the pending purchase · ESC: close (no purchase pending)

**Transitions:**
- ESC → back to whichever screen opened it (`shop_return_screen` in `main.py`)

### OutfittingMenu
**Shows:** Buy and install ship outfits - `game/ui/outfitting_menu.py`.
Opened like `ShopMenu`/`ShipBrowserMenu` (T on a `"shop"` NPC), for
`"type": "outfits"` - `main.py`'s `build_shop_menu()` dispatches here,
passing the current ship type (`possessions.owned_ships[-1]`, or `None` if
no ship is owned yet) and `game_screen.reapply_outfits` as the
stats-refresh callback. Buy tab: a `ShopMenu`-style list, but purchases add
to `possessions.owned_outfits` (spare, uninstalled) rather than equipping.
Install tab: a diagram of the current ship's `slots` (from
`ship_types.json`) plus the spare-outfits list; drag a spare onto a
matching-type slot to equip (or drag an installed one out to unequip), or
use the keyboard fallback (Tab: switch focus column, arrows: navigate,
Enter: open a compatible-outfit picker on an empty focused slot, or
uninstall directly on an occupied one). Every equip/uninstall calls
`on_outfits_changed`, which re-runs `SpaceScreen._apply_ship_type` so the
flown ship's stats update immediately - see `SpaceScreen.reapply_outfits`.

**Inputs:** LEFT/RIGHT: switch Buy/Install · (Install tab) TAB: switch
focus column · UP/DOWN or W/S: navigate · RETURN: buy (Buy tab) / open
picker or uninstall (Install tab, depending on slot state) · mouse drag:
equip/unequip directly · ESC: close (or cancel an open picker first)

**Transitions:**
- ESC → back to whichever screen opened it (`shop_return_screen` in `main.py`)

### PauseMenu
**Shows:** Resume/Save/Quit options with optional success banner

**Inputs:** UP/DOWN or W/S: navigate · RETURN: select · ESC: resume (quick exit)

**Transitions:**
- Resume → back to whichever screen was active (`previous_screen`)
- Save Game → `SaveDialog`
- Quit to Menu → Menu

### SaveDialog (Scrollable)
**Default name:** pre-filled as `"{pilot_name} - {timestamp}"`

**Two modes:**
- **Input mode** (no existing saves, or after pressing N): type a save name, RETURN to save
- **List mode** (existing saves present): browse and act on them

**Inputs (list mode):** UP/DOWN or W/S: navigate (scrolling) · RETURN: overwrite selected → `ConfirmDialog` ("Overwrite Save?") · N: switch to input mode · D: delete selected → `ConfirmDialog` ("Delete Save?") · ESC: cancel

**Transitions:**
- Save completes → success banner (2s) → PauseMenu
- Overwrite/Delete confirmed via their `ConfirmDialog` (Y = `"confirm"`, N/ESC = `"cancel"`)
- ESC → PauseMenu (no save)

## Screen-to-Screen Data Flow

### SpaceScreen → SaveDialog
```python
save_dialog = SaveDialog(pilot_name=pilot_name)
```
Passes current pilot name so the dialog can pre-fill a sensible default save name.

### SaveDialog → create_save_file
```python
create_save_file(
    pilot_name,
    save_description,
    game_screen.system_config,
    {},
    game_screen.get_state()  # Current game state
)
```
Saves the original system config alongside the current game state. Which `get_state()`
is called depends on `previous_screen` — `game_screen`, `station_interior`, or
`moon_interior` — and `game_state["location"]` is set accordingly (`"space"` /
`"station"` / `"moon"`, plus `"station_location"` / `"moon_location"` for
which interior). Both `SpaceScreen.get_state()` and `LocationScreen.get_state()`
also include `"possessions"` (credits/owned ships/loans) - see
[SAVE_SYSTEM.md](SAVE_SYSTEM.md).

### LoadMenu → SpaceScreen / LocationScreen
```python
save_data = load_save_file(filename)
pilot_name = save_data.get("pilot_name", "")
game_screen = SpaceScreen(save_data.get("system", {}), pilot_name=pilot_name)
game_screen.restore_state(save_data.get("game_state", {}))
```
See [SAVE_SYSTEM.md](SAVE_SYSTEM.md) for the full file format.

## Menu Lifecycle

**On First Run:**
```
Menu created → has_saves = False → items = ["NEW", "QUIT"]
User plays → Saves → Quit
Menu recreated → has_saves = True → items = ["NEW", "LOAD", "QUIT"]
```

**Key:** Menu must be recreated when returning from game/load so LOAD appears.

## State Transitions & Validation

**Valid transitions (`current_screen` values in `main.py`):**
`"menu"` → `"story_select"` → `"pilot_name"` → `"station"` (dormitory - new pilots start here, ship-less)
`"menu"` → `"load"` → `"game"` / `"station"` / `"moon"` (whatever `location` the save has)
`"game"` → `"station"` (land near station) or `"select_location"` → `"moon"` (land near moon)
`"station"` / `"moon"` → `"exit_menu"` (L, exit has multiple destinations, or its one destination isn't usable yet) → `"game"`, or back to `"station"`/`"moon"` (a different interior, or ESC/cancel)
`"game"` / `"station"` / `"moon"` → `"possessions"` (P) → back to whichever of the three it came from
`"station"` / `"moon"` → `"shop"` (T, on an NPC with a `"shop"` config) → back to whichever of the two it came from
`"game"` / `"station"` / `"moon"` → `"pause"` (ESC) → back to `previous_screen` (Resume) or `"menu"` (Quit)

**Invalid (prevented by code):**
- PauseMenu blocks its own input while `SaveDialog`/`ConfirmDialog` is open
- `LocationScreen` only exits (`L`) within `entrance_range` of a portal
- `ExitMenu` only appears when `get_exit_options()` has more than one entry, or the single entry isn't usable (`get_exit_disabled_reasons()`); with exactly one usable entry it's skipped (immediate exit)
- Landing only triggers when both close enough (`landing_distance`) and slow enough (`speed < 0.4`)
- A dialogue option with a blocked `"action"` (`LocationScreen._option_blocked_reason`) can't be selected - RETURN on it is a no-op

## Input Handling Pattern

Each screen handles its own input:

```python
class Screen:
    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Process key and return action string
        return None  # No state change
```

Main loop interprets action strings and manages state:

```python
if current_screen == "menu":
    action = menu.handle_input(events)
    if action == "new":
        story_selector = StorySelector()
        current_screen = "story_select"
    elif action == "load":
        load_menu = LoadMenu()
        current_screen = "load"
```

This separation makes it easy to test input handlers independently.

See [ARCHITECTURE.md](ARCHITECTURE.md#state-machine-screen-flow) for class hierarchy.
