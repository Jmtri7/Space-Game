# UI Flow & Screen State Machine

Menu hierarchy, screen transitions, and state management.

**Menu vs. dialog classes:** every modal below extends `MenuBase` (a
**menu** - navigate freely, doesn't close on an action) or `DialogBase` (a
**dialog** - closes on any pick). Neither draws a Controls pane; both show
their actions as `draw_button` widgets in their own panel (mouse + Tab/arrow
+ Enter). See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md)'s "Menu vs. Dialog".
Four pairs of
old classes were merged: the main menu and story picker are both
`BackdropMenu`; the "landing spot" and "where to?" pickers are both
`ChoiceDialog`; the possessions and mission read-outs are both `ReportMenu`
(+ a `*_report()` builder fn); load and save are `SaveBrowser(mode="load"
|"save")`. State names in `main.py` (`"menu"`, `"load"`, `"exit_menu"`, …)
are unchanged.

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
          │ STATION         │        │  LANDING LOCATION │         │
          │ (LocationScreen)│        │ ChoiceDialog      │         │
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
        │              Resume / Save / Load / Quit                     │
        └───┬───────────────────────────┬───────────────────────┬────┘
            │                           │                       │
    ┌──────────────┐          ┌────────────────────┐   ┌──────────────────┐
    │ SAVE BROWSER │          │ OVERWRITE CONFIRM  │   │  DELETE CONFIRM   │
    │ SaveBrowser  │──(D)────►│   (ConfirmDialog)  │   │  (ConfirmDialog)  │
    └──────────────┘          └────────────────────┘   └──────────────────┘
```

The Load screen (`SaveBrowser("load")`) also has its own delete flow (its
own `ConfirmDialog` instance) for removing a save directly, independent of
the Pause-menu save browser's delete flow shown above.

The diagram above shows the simple case where a `LocationScreen`'s exit
(`L` near a portal) leads to only one place, and so acts immediately. A
location can have more than one portal (see STATION / MOON below); when
the one the player is standing next to has `connected_locations` and/or
`return_to_ship` adding up to more than one destination, `L` instead opens
the exit `ChoiceDialog` - the player picks "Return to Ship" (→ GAME) or a
connected location (→ that location's own `LocationScreen`, staying in
`"station"`/`"moon"`).

## Screen Descriptions

### Main Menu (`BackdropMenu`)
**States:** Showing NEW, LOAD, QUIT
- `main.py`'s `main_menu()` builds the rows; recreated each time the game
  returns to the menu

**Transitions:**
- NEW → Story Selector
- LOAD → `SaveBrowser("load")`
- QUIT → Exit application

### Story Selector (`BackdropMenu`, `allow_cancel=True`)
**Shows:** List of playable stories, scanned from `config/stories/*/story.json` by `main.py`'s `story_menu_rows()`, with each story's description

**Inputs:** UP/DOWN or W/S: navigate · RETURN: select · ESC: cancel

**Transitions:**
- RETURN → `PilotNameDialog` (remembers `selected_story`)
- ESC → Main Menu

### PilotNameDialog (`DialogBase`)
**Shows:** Text entry box for the pilot's name (30 char max) plus **Start / Cancel** buttons

**Inputs:** Type: add to name · BACKSPACE: delete last char · Left/Right/Tab: move between buttons · RETURN/click Start (name non-empty): confirm · ESC/click Cancel: cancel

**Transitions:**
- Start (non-empty name) → `SpaceScreen` created with `pilot_name` and `story`, then `game_screen.begin_new_game()` returns where to drop the player from `story.json`'s `"start"` block: `"station"`/`"moon"` at the given interior key, or `"space"` → `"game"`. The default story starts in `"station"` at `"default"` (0 credits, no ship - see the station layout under STATION / MOON below). `"start"` also seeds starting credits / ship / spare outfits / personal items / story flags.
- ESC → Main Menu

### Load Menu (`SaveBrowser`, `mode="load"`)
**Shows:** All save files from `saves/` directory, 5 at a time

**Inputs:** UP/DOWN or W/S: navigate (scrolls at boundaries) · RETURN: load · D: delete (opens its own `ConfirmDialog`) · ESC: cancel

**Transitions:**
- RETURN → Reads `game_state["location"]` from the save (`"space"` / `"station"` / `"moon"`) and jumps straight to the matching screen with state restored:
  - `"space"` → `SpaceScreen`
  - `"station"` → `SpaceScreen` (background) + `LocationScreen` for the station interior
  - `"moon"` → `SpaceScreen` (background) + `LocationScreen` for the saved moon location
- ESC → Main Menu (or Pause Menu when opened from there)

### GAME — `SpaceScreen`
**Shows:** Space view with player ship, AI ships, star field, station, moon, target HUD

**Inputs:**
- LEFT/RIGHT or A/D: rotate ship
- UP or W: thrust forward
- DOWN or S: turn to face reverse velocity
- T: cycle target (station, moon, each AI ship)
- L: land (or engage autopilot toward the current target if out of range)
- H: hail the targeted ship — opens a dialogue box and fully pauses the simulation until it closes (no `update()`/`update_background_locations()` while `game_screen.active_dialogue` is set)
- ESC: pause

**Transitions:**
- L, close + slow near station → `LocationScreen` (station interior)
- L, close + slow near moon → landing-spot `ChoiceDialog` (`"select_location"`)
- ESC → PauseMenu

### Landing Location (`ChoiceDialog`)
**Shows:** Moon landing sub-location choices (City / Wilderness) as a button column, built from the moon's `interiors` config by `main.py`'s `landing_location_options()`

**Inputs:** UP/DOWN or W/S: move between buttons · RETURN/click: pick · ESC: cancel (returns to `SpaceScreen`)

**Transitions:**
- RETURN → `LocationScreen` for the chosen moon location
- ESC → GAME

### STATION / MOON — `LocationScreen`
**Shows:** Top-down walkable view of the interior/exterior with NPCs. One generic,
config-driven class used for both the station interior and every moon location —
not a station-only or moon-only screen.

A default-story **station** is a single interior (key `"default"`): one
connected walkable area (polygon `rooms` unioned - concourse, bar, credit
union, ship dock, resin quarter) with **one** portal, the ship dock
(`return_to_ship: true`, disabled until a ship is owned - see
`ship_available` below). The new-game start, the loan officer, the ship
salesman, and the outfitter all live in that one interior. See
`config/stories/default/systems/sol_alpha.json`.

A location can still have more than one **portal** (`LocationScreen.portals`)
- a moon's `city` ↔ `wilderness`, or a multi-interior story station: each
portal leads somewhere specific, and walking back through the portal you
arrived from always leads back the way you came
(`LocationScreen.arrive_from()` / `portal_for()`). A config with a single
exit may still use the flat `"entrance"` / `"connected_locations"` /
`"return_to_ship"` keys, normalized into a one-item portal list internally.

**Inputs:**
- LEFT/RIGHT/UP/DOWN or WASD: move
- L: exit (only within range of a portal) - see `get_available_exit_options()`, scoped to whichever portal is nearest:
  - Exactly one destination *and it's actually usable* → goes there immediately (`"exit"` → GAME, or `"exit_to:<key>"` → that connected location)
  - More than one configured, or the only one isn't usable yet (e.g. "ship" with no ship owned) → opens the exit `ChoiceDialog`, so an unusable option is still visible with its reason instead of L doing nothing
- T (with an NPC targeted, in range): talk - opens that NPC's `Dialogue` (see below)
- P: possessions `ReportMenu` · N: mission `ReportMenu`
- ESC: pause

While docked, `SpaceScreen.update_physics()` still runs in the background (ships keep moving), just without camera updates.

**Transitions:**
- L (near a portal, single usable destination) → GAME or a connected location's `LocationScreen`
- L (near a portal, multiple destinations, or the only one isn't usable) → exit `ChoiceDialog`
- T (NPC targeted, in range, no `"shop"` config) → that NPC's `Dialogue`, always restarted at its root node
- T (NPC targeted, in range, has a `"shop"` config) → `ShopMenu` instead of `Dialogue`
- P → possessions `ReportMenu` · N → mission `ReportMenu`
- ESC → PauseMenu

### Dialogue
**Shows:** A conversation tree (`game/world/dialogue.py`) - most NPCs are a
single node with closing options only ("Thanks"/"Leave", built via
`Dialogue.from_flat`); a few (Bartender, the ship salesman, the loan
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

### Exit Menu (`ChoiceDialog`)
**Shows:** The destinations offered by the current location's exit as a
column of buttons - each `connected_locations` key (labeled from that
sibling interior's own `"label"`) plus "Return to Ship" if `return_to_ship`
allows it, built by `main.py`'s `exit_options()`. Shown whenever there's
more than one configured option, or the single option isn't currently usable
(e.g. "ship" with `get_exit_disabled_reasons()` returning `{"ship": "no ship
docked here"}` - the station dock before a purchase). Disabled entries render
as dimmed buttons and can't be selected. AI pilots (`DockRoutine`) pick from
this same option list automatically via `ROLE_EXIT_PREFERENCE` instead of
getting a dialog.

**Inputs:** UP/DOWN or W/S: move between buttons · RETURN/click: pick · ESC: cancel (stay in the current location)

**Transitions:**
- "Return to Ship" → GAME
- a connected location → that location's `LocationScreen` (still `"station"`/`"moon"`)
- ESC → back to the location the dialog was opened from

### Possessions / Missions (`ReportMenu`)
**Shows:** A read-only, one- or two-column text report. `possessions_report()`
(P): credits, owned ships, loans, the current ship's live stats
(thrust/max velocity/rotation/cargo usage - via the optional `ship` arg,
`PlayerController.ship`, so it reflects installed outfits immediately),
cargo, personal items, installed/spare outfits. `mission_report()` (N):
each mission's stages with `[x]` / `->` markers, hiding stages not yet
reached. Both live in `game/ui/report_menu.py`, drawn over whichever screen
opened them.

**Inputs:** P (possessions) or N (missions) or ESC: close

**Transitions:**
- close → back to whichever screen opened it (`possessions_return_screen` / `missions_return_screen` in `main.py`)

### ShopMenu
**Shows:** Buy/sell for commodities or personal items - `game/ui/
shop_menu.py`. Opened by talking (T) to an NPC whose config has a `"shop"`
key (`{"type": "commodities"|"items", "stock": [...], "sell_multiplier": ...}`)
instead of that NPC's `Dialogue`. Buy tab lists `stock` priced from
`commodities.json`/`items.json`; Sell tab lists whatever's currently in
`possessions.cargo`/`.items` for that category, priced at
`base_price * sell_multiplier`. Drawn over whichever screen it was opened
from (station or moon), same overlay pattern as the possessions `ReportMenu`.
Ships and ship outfits get their own dedicated menus, not this one.

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
stat readout for whichever is selected. Enter opens a `ConfirmDialog`
(returned from `active_popup()`, so `MenuBase.draw` draws it on top instead
of this menu's Close button - see the ConfirmDialog note below); confirming
calls the injected `on_buy` callback, which `main.py` wires to
`LocationScreen.buy_ship()` - the same mutation the old `"buy_ship:<id>"`
dialogue action performed (spend, `add_ship`, `on_ship_purchased`
callback), now shared by both purchase paths. The station's ship salesman
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

### PauseMenu (`MenuBase`)
**Shows:** A column of buttons - Resume / Save Game / Load Game / Quit to
Menu - plus an optional "Saved!" banner.

**Inputs:** UP/DOWN or W/S: move between buttons · RETURN or click: press · ESC: resume (quick exit)

**Transitions:**
- Resume → back to whichever screen was active (`previous_screen`)
- Save Game → `SaveBrowser("save")`
- Load Game → `SaveBrowser("load")` (with `load_return_screen = "pause"`, so cancelling it returns here instead of the Main Menu; a successful load replaces the running game and goes to `"game"`/`"station"`/`"moon"`)
- Quit to Menu → Main Menu

### Save Menu (`SaveBrowser`, `mode="save"`)
**Default name:** pre-filled as `"{pilot_name} - {timestamp}"`

**Two modes:**
- **Input mode** (no existing saves, or after pressing N): type a save name, RETURN to save
- **List mode** (existing saves present): browse and act on them

**Inputs (list mode):** UP/DOWN or W/S: navigate (scrolling) · RETURN: overwrite selected → `ConfirmDialog` ("Overwrite Save?") · N: switch to input mode · D: delete selected → `ConfirmDialog` ("Delete Save?") · ESC: cancel

**Transitions:**
- Save completes → success banner (2s) → PauseMenu
- Overwrite/Delete confirmed via their `ConfirmDialog` (Y = `"confirm"`, N/ESC = `"cancel"`)
- ESC → PauseMenu (no save)

### ConfirmDialog (`DialogBase`)
**Shows:** A title, a one-line message, and **Yes / No buttons**
(`MenuBase.draw_buttons` → `ui_theme.draw_button`, green / muted-red) with a
shortcut-reminder line - all **inside its own glass panel**. A dialog closes
on any pick. When it's a sub-dialog of a menu (`ShipBrowserMenu.
active_popup()` returns `self.confirm`), `MenuBase.draw` draws it on top.
Panel via `modal_panel_rect()`. Used for ship
purchases (`ShipBrowserMenu`) and save overwrite/delete confirmations.
Starts with **No** highlighted (the safe default for the destructive uses).

**Inputs:** Left/Right or Tab: move between buttons · Enter: pick the
highlighted one · Y: confirm · N / ESC: cancel · mouse hover highlights a
button, click acts on it. Returns `("confirm", context_data)` or
`("cancel", None)`.

## Screen-to-Screen Data Flow

### PauseMenu → Save Menu
```python
save_dialog = SaveBrowser("save", pilot_name=pilot_name)
```
Passes current pilot name so the browser can pre-fill a sensible default save name.

### Save Menu → create_save_file
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

### Load Menu → SpaceScreen / LocationScreen
```python
save_data = load_save_file(filename)
pilot_name = save_data.get("pilot_name", "")
game_screen = SpaceScreen(save_data.get("system", {}), pilot_name=pilot_name)
game_screen.restore_state(save_data.get("game_state", {}))
```
See [SAVE_SYSTEM.md](SAVE_SYSTEM.md) for the full file format.

## Menu Lifecycle

The main menu is rebuilt (`main.py`'s `main_menu()`) every time the game
returns to `"menu"` - from QUIT, from cancelling the load screen, or from a
completed load being abandoned - so nothing stale carries over.

## State Transitions & Validation

**Valid transitions (`current_screen` values in `main.py`):**
`"menu"` → `"story_select"` → `"pilot_name"` → `"station"` / `"moon"` / `"game"` per `story.json`'s `"start"` block (default story: `"station"` interior, ship-less)
`"menu"` → `"load"` → `"game"` / `"station"` / `"moon"` (whatever `location` the save has)
`"pause"` → `"load"` (Load Game; `load_return_screen = "pause"`) → `"game"` / `"station"` / `"moon"` on load, or back to `"pause"` on cancel
`"game"` → `"station"` (land near station) or `"select_location"` → `"moon"` (land near moon)
`"station"` / `"moon"` → `"exit_menu"` (L, exit has multiple destinations, or its one destination isn't usable yet) → `"game"`, or back to `"station"`/`"moon"` (a different interior, or ESC/cancel)
`"game"` / `"station"` / `"moon"` → `"possessions"` (P) → back to whichever of the three it came from
`"station"` / `"moon"` → `"shop"` (T, on an NPC with a `"shop"` config) → back to whichever of the two it came from
`"game"` / `"station"` / `"moon"` → `"pause"` (ESC) → back to `previous_screen` (Resume) or `"menu"` (Quit)

**Invalid (prevented by code):**
- PauseMenu blocks its own input while the save browser / a `ConfirmDialog` is open
- `LocationScreen` only exits (`L`) within `entrance_range` of a portal
- The exit `ChoiceDialog` only appears when `get_exit_options()` has more than one entry, or the single entry isn't usable (`get_exit_disabled_reasons()`); with exactly one usable entry it's skipped (immediate exit)
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
        story_selector = BackdropMenu("SELECT STORY", story_menu_rows(), seed=4242, allow_cancel=True)
        current_screen = "story_select"
    elif action == "load":
        load_menu = SaveBrowser("load")
        current_screen = "load"
```

This separation makes it easy to test input handlers independently.

## Main Loop: fixed-timestep, three phases

`main.py`'s `while running:` runs three phases per iteration:

1. **Input / transitions** — one big `if current_screen == …` that calls each
   screen's `handle_input(events)` and applies the resulting state changes
   (building menus, swapping `current_screen`, …). No `update()`/`draw()` here.
   A transition requested here lands *before* phase 2, so the accumulator
   never simulates the screen the player just left.
2. **Simulation** — `advance_accumulator()` (`game/utils.py`) converts the
   real milliseconds since the last frame (`clock.tick(FPS)`) into a whole
   number of fixed `SIM_STEP` (1/60 s) steps, and `step_world()` is called
   that many times. `step_world()` is the single simulation entry point: it
   does exactly what each screen branch used to do inline for *simulation*
   (`SpaceScreen.update()` / `update_physics()`, `LocationScreen.update()`,
   `update_background_locations()`, and the per-step countdown timers inside
   those). Screens that freeze the world (every menu/dialog, the star map,
   pause, any open `active_dialogue`) are no-ops here, exactly as before.
   When `SpaceScreen.update()` returns `"land"` (autopilot auto-land) the
   step returns it, `main()` applies the landing and stops draining.
3. **Render** — one `if current_screen == …` that draws the current screen
   (modal screens redraw the frozen backdrop with `draw_hud=False`, then
   their overlay), then `pygame.display.flip()`.

`SIM_STEP` **must stay 1/60**: every physics constant and per-step timer is
already calibrated to a 1/60 s step, so on a machine holding 60 FPS phase 2
runs exactly once and the result is byte-identical to the old
one-step-per-frame loop. It only diverges on a machine that can't keep up,
where it runs 2–5 catch-up steps per render (`MAX_STEPS_PER_FRAME` clamps
the spiral of death; `MAX_FRAME_TIME` clamps a debugger/asset-load hitch).
This is frame-rate *independence*, not render interpolation — motion is not
smoother at >60 Hz, `draw()` still paints the latest sim state.

Menu/dialog animations (`pause_menu.update()`'s success-banner countdown)
are render-side and stay in phase 3 — they're not simulation.

### Frame-timing metrics

The loop times each phase with `time.perf_counter()` deltas and feeds them to
`game/perf_metrics.py`'s shared `metrics` object once per iteration
(`metrics.record(...)`), along with `n_steps` (the catch-up sim-step count) and
`clock.get_fps()`. Finer-grained sub-sections are wrapped in
`with metrics.span("<name>"):` at their call site — currently `render.starfield`
/ `render.world` / `render.hud` in `SpaceScreen.draw`, `sim.player` /
`sim.ai_ships` / `sim.missions` in `SpaceScreen.update_physics`, and `sim.npcs` /
`render.location_entities` in `LocationScreen`. All of this runs unconditionally
(it's a few `perf_counter` calls and deque appends per frame); only the
bottom-left overlay that `perf_metrics.draw_overlay(screen)` paints is gated on
`constants.DEBUG_MODE`. Everything shown is a rolling average + peak over the
last `WINDOW` frames (~2 s).

**Agents:** when a change touches the main loop, a `draw()`/`update()` path, or
adds per-frame work (a new drawable, an AI routine, a scan over all entities),
toggle debug (`` ` ``) and watch the panel before and after — keep `frame` well
under the 16.67 ms budget and don't let a `sim.*` / `render.*` span balloon.
Wrap a genuinely new expensive section in its own `metrics.span(...)` so the
regression is visible next time.

See [ARCHITECTURE.md](ARCHITECTURE.md#state-machine-screen-flow) for class hierarchy.
