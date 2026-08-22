# UI Flow & Screen State Machine

Menu hierarchy, screen transitions, and state management.

## Screen State Machine

```
                    ┌─────────────────┐
                    │     MENU        │
                    │ NEW/LOAD/QUIT   │
                    └────────┬────────┘
                    ┌────────┴────────┐
                    │                 │
              ┌─────▼──┐         ┌────▼──────┐
              │  GAME  │         │ LOAD MENU │
              │ (space)│         │(scrollable)│
              └────┬───┘         └────┬──────┘
                   │                  │
            ┌──────▼──────┐           │
            │  PAUSE MENU │◄──────────┘
            │Resume/      │
            │Save/Quit    │
            └──────┬──────┘
                   │
          ┌────────┼────────┐
          │                 │
     ┌────▼────┐      ┌─────▼────────┐
     │STATION  │      │SAVE DIALOG   │
     │INTERIOR │      │(scrollable)   │
     └────┬────┘      └──────────────┘
          │
     ┌────▼──────┐
     │PAUSE MENU │ (from station)
     └───────────┘
```

## Screen Descriptions

### Main Menu
**States:** Showing NEW, LOAD (if saves exist), QUIT
- LOAD appears dynamically when save files exist
- Menu recreated each time user returns (refreshes LOAD visibility)

**Inputs:**
- UP/DOWN or W/S: Navigate
- Mouse: Move selector by hovering
- RETURN or CLICK: Select option

**Transitions:**
- NEW → GameScreen (fresh game)
- LOAD → LoadMenu
- QUIT → Exit application

### LoadMenu (Scrollable)
**Shows:** All save files from `saves/` directory, 5 at a time

**Display:**
- Filename shown in full
- Current selection highlighted (YELLOW)
- ↑ more indicator if there are saves above
- ↓ more indicator if there are saves below

**Inputs:**
- UP/DOWN or W/S: Navigate (scrolls list when at boundaries)
- RETURN: Load selected save
- ESC: Cancel, return to menu

**Transitions:**
- RETURN → GameScreen (with restored state)
- ESC → Menu

### GameScreen
**Shows:** Space view with player ship, AI ships, star field, station

**Inputs:**
- LEFT/RIGHT or A/D: Rotate ship
- UP or W: Thrust forward
- DOWN or S: Thrust backward
- L: Land on station (only if within range)
- ESC: Pause

**Transitions:**
- L (valid) → StationInterior
- ESC → PauseMenu

**HUD:**
- "Press L to land" prompt (appears when near station, within 100 units)

### PauseMenu
**Shows:** Resume/Save/Quit options with optional success banner

**States:**
- Normal: Menu selectable
- Saving: SaveDialog overlaid, menu interactions blocked
- Success: "Saved!" banner at top for 2 seconds

**Inputs:**
- UP/DOWN or W/S: Navigate
- RETURN: Select option
- ESC: Resume game (quick exit)

**Options:**
- Resume: Return to previous screen (game or station)
- Save Game: Open SaveDialog
- Quit to Menu: Return to main menu

**Transitions:**
- Resume → Return to Game/Station
- Save Game → SaveDialog (state: saving)
  - On save complete → Pause (state: success)
  - Success banner → Auto-dismiss after 2 seconds
- Quit → Menu

### SaveDialog (Scrollable)
**State 1: Choose Pilot (if no existing saves)**
- Prompt: "Enter Pilot Name:"
- Shows cursor (|)
- 30 char max

**State 2: Select Existing Save (if pilot has saves)**
- Shows title: "Select Save to Overwrite"
- Lists existing saves for that pilot, 5 at a time
- ↑/↓ more indicators

**Inputs (Pilot Entry):**
- Type: Add to name
- BACKSPACE: Delete last char
- RETURN: Save with entered name
- ESC: Cancel

**Inputs (Overwrite):**
- UP/DOWN or W/S: Navigate (with scrolling)
- RETURN: Overwrite selected save
- N: Switch to "Enter new name" mode
- ESC: Cancel

**Display:**
- Help text shows available actions
- Full save filenames when scrolling

**Transitions:**
- RETURN (save) → Success state (2s banner) → PauseMenu
- ESC → PauseMenu (no save)

### StationInterior
**Shows:** First-person view of station interior with NPCs

**Inputs:**
- LEFT/RIGHT or A/D: Move left/right
- UP or W: Move forward
- DOWN or S: Move backward
- T: Talk to nearby NPC (if within 50 units)
- L: Exit station, return to space
- ESC: Pause

**HUD:**
- "WASD/Arrows to move, L to exit, ESC for menu"
- "Press T to talk" (when NPC nearby)
- Dialogue box (when talking)

**Transitions:**
- L → GameScreen
- ESC → PauseMenu

**Dialogue System:**
- T opens conversation with nearby NPC
- UP/DOWN or W/S: Navigate options
- RETURN or CLICK: Select option
- ESC: Close dialogue, return to movement

## Screen-to-Screen Data Flow

### GameScreen → SaveDialog
```python
save_dialog = SaveDialog(pilot_name=pilot_name)
```
Passes current pilot name so dialog can show their existing saves.

### SaveDialog → create_save_file
```python
create_save_file(
    pilot_name,
    save_name,
    game_screen.system_config,
    {},
    game_screen.get_state()  # Current game state
)
```
Saves include both original config and current game state.

### LoadMenu → GameScreen
```python
save_data = load_save_file(filename)
pilot_name = save_data.get("pilot_name", "")
game_screen = GameScreen(save_data.get("system", {}), pilot_name=pilot_name)
game_screen.restore_state(save_data.get("game_state", {}))
```
Restores both config and player state.

## Menu Lifecycle

**On First Run:**
```
Menu created → has_saves = False → items = ["NEW", "QUIT"]
User plays → Saves → Quit
Menu recreated → has_saves = True → items = ["NEW", "LOAD", "QUIT"]
```

**Key:** Menu must be recreated when returning from game/load so LOAD appears.

## State Transitions & Validation

**Valid transitions:**
- Menu → GameScreen (NEW)
- Menu → LoadMenu (LOAD)
- GameScreen → PauseMenu (ESC)
- GameScreen → StationInterior (L, if near station)
- StationInterior → PauseMenu (ESC)
- PauseMenu → GameScreen (Resume from game)
- PauseMenu → StationInterior (Resume from station)
- PauseMenu → Menu (Quit)
- LoadMenu → GameScreen (Load)
- LoadMenu → Menu (Cancel)

**Invalid (prevented by code):**
- PauseMenu blocks SaveDialog actions until dialog closes
- Station interior only accessible within landing range
- Transitions ignore input when dialog is open

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
        game_screen = GameScreen()
        current_screen = "game"
    elif action == "load":
        load_menu = LoadMenu()
        current_screen = "load"
```

This separation makes it easy to test input handlers independently.

See [ARCHITECTURE.md](ARCHITECTURE.md#state-machine-screen-flow) for class hierarchy.
