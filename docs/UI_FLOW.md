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
- RETURN (non-empty name) → `SpaceScreen` created with `pilot_name` and `story`
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

**Inputs:**
- LEFT/RIGHT/UP/DOWN or WASD: move
- L: exit (only within range of the entrance marker) → back to GAME
- ESC: pause

While docked, `SpaceScreen.update_physics()` still runs in the background (ships keep moving), just without camera updates.

**Transitions:**
- L (near entrance) → GAME
- ESC → PauseMenu

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
`"station"` / `"moon"`, plus `"moon_location"` for moon saves).

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
`"menu"` → `"story_select"` → `"pilot_name"` → `"game"`
`"menu"` → `"load"` → `"game"` / `"station"` / `"moon"`
`"game"` → `"station"` (land near station) or `"select_location"` → `"moon"` (land near moon)
`"game"` / `"station"` / `"moon"` → `"pause"` (ESC) → back to `previous_screen` (Resume) or `"menu"` (Quit)

**Invalid (prevented by code):**
- PauseMenu blocks its own input while `SaveDialog`/`ConfirmDialog` is open
- `LocationScreen` only exits (`L`) within `entrance_range` of the entrance marker
- Landing only triggers when both close enough (`landing_distance`) and slow enough (`speed < 0.4`)

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
