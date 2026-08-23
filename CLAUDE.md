# Space Game Development Guide

**For detailed documentation, see [docs/README.md](docs/README.md)** — comprehensive guides on architecture, physics, save systems, UI flow, controls, and design patterns.

**When adding or updating controls, check [docs/CONTROLS.md](docs/CONTROLS.md)** — all keyboard bindings are documented there for player discovery and consistency.

## Project Overview
A pygame-based space exploration game with procedurally generated star fields, AI ships, space stations with NPCs, and a complete save/load system. The game features physics-based ship movement, NPC dialogue, and persistent game state.

## For Agents: Controls & Documentation Trail

**Control Documentation:** When adding or changing ANY keyboard binding:
1. **First**: Check [docs/CONTROLS.md](docs/CONTROLS.md) for existing bindings
2. **Add/Update**: The control in CONTROLS.md with action description
3. **Add/Update**: Help text in the menu/screen displaying the control to players
4. **Commit**: Include "controls:" in the commit message so future agents know controls changed

This ensures players can discover controls, agents know where to look, and conflicts are avoided.

## For Agents: Pattern Recognition & Contributions

**Read this:** When implementing features or fixes, watch for opportunities to **generalize solutions into reusable patterns**. If you notice:

- Code being repeated in multiple places
- A clever solution that other code might benefit from
- A design pattern that worked well and could guide future work

...then **suggest adding it to [docs/DESIGN_PATTERNS.md](docs/DESIGN_PATTERNS.md)**. 

**Example suggestion:**
> "I noticed the save/load system uses a consistent {getter, setter} pattern for state capture. This could generalize to DESIGN_PATTERNS.md as a 'State Persistence Pattern' that future systems could follow when adding new saveable objects."

See [docs/README.md#for-agents](docs/README.md#for-agents-pattern-recognition--contribution) for the full contribution workflow.

## For Agents: Design Principles & Code Patterns

### Menu Help Text (Consistency & Discoverability)
**Rule:** All interactive menus and dialogs must display concise help text at the bottom showing available actions.
- **Format:** "Action: key/button, Action: key/button, ESC: cancel" (terse, scannable)
- **Maintenance:** Update help text whenever adding/changing menu options
- **Benefit:** Players discover features without trial-and-error; new menu options self-document

**Example:**
- Menu: `"Enter: select, ESC: cancel"`
- SaveDialog: `"Enter: save, N: new, D: delete, ESC: cancel"`
- LoadMenu: `"Enter: load, D: delete, ESC: cancel"`

### Cross-Cutting Concerns: Handle at the Source
**Principle:** When a behavior needs to apply everywhere (like window close, event filtering, startup logic), handle it once in the main loop or base class, not repeated in every subclass.
- **Benefit:** New screens inherit correct behavior by default; no need to remember to add it
- **Example:** pygame.QUIT is handled in the main event loop, so any new screen works without modification
- **Anti-pattern:** Duplicated QUIT checks in 10 different screen classes

### Generalization Strategy
When you notice the same pattern appearing in multiple places:
1. **Extract to a helper function** if it's utility code (e.g., `_handle_scrolling_input()`)
2. **Move to base class** if it's core to the entity type (e.g., `get_state()` in `ScreenBase`)
3. **Handle centrally** if it's a cross-cutting concern (e.g., QUIT events in main loop)
4. **Document in DESIGN_PATTERNS.md** if it's a reusable principle other parts of the game should follow

### One Class Per File
**Rule:** Each Python file should contain exactly one class.
- **File naming:** Use `snake_case.py` for the filename, matching the class name: `MyClass` → `my_class.py`
- **Exceptions:** Utility functions and constants can live in dedicated modules (e.g., `utils.py`, `constants.py`)
- **Inheritance:** If a class extends another, place both imports at the top of the child class file
- **Benefit:** Makes the codebase more navigable; easier to find and modify individual classes
- **Example:** `dialogue.py` contains only the `Dialogue` class; `station_interior.py` contains only the `StationInterior` class (which imports `Location`)

## For Agents: Development Workflow

**After each feature addition or code change:**

1. **Kill any running game instance** — Close all pygame windows from previous runs
   ```bash
   taskkill /f /im python.exe 2>nul || true  # Kill Python processes
   ```

2. **Run automated tests** (optional but recommended)
   ```bash
   python run_tests.py
   ```

3. **Start the game fresh** to load new code
   ```bash
   python main.py
   ```

4. **Test in-game** — Verify the feature/fix works as intended by interacting with it

5. **Commit the changes** with a clear message describing what changed and why
   ```bash
   git add .
   git commit -m "Feature: [description]"
   ```

**Why this matters:**
- Fresh app restart ensures new code is loaded (not cached from previous run)
- Testing in-game catches issues that automated tests miss
- Regular commits create a good history and let you revert if needed
- Clear commit messages help you and others understand what changed and when

**Example workflow:**
```
1. Edit ship.py to improve autopilot braking
2. Kill running game (taskkill /f /im python.exe)
3. Start fresh game (python main.py)
4. Test autopilot by targeting station and landing
5. Verify it brakes smoothly without overshooting
6. Commit: "Improve: Refine autopilot braking distance calculation"
```

**When making changes**, watch for untested critical logic:

1. **Discovered a bug during development?** Add a test case that catches it *before* fixing it, so it never regresses.
2. **Finding untested business logic?** If it's pure or testable, suggest adding a test (don't block the feature on it).
3. **Extracting a helper function?** Include unit tests in the same commit.

**Example:**
> "While implementing the new thruster balance, I noticed the velocity-capping logic has no tests. I've added 3 test cases to catch regressions when changing drag constants."

Keep the bar practical: test regressions you've actually seen or critical paths (save/load, physics, input handling). Don't test UI rendering or Pygame drawing.

## Running the Game
```bash
cd C:\Users\Play\Documents\Projects\space-game
python main.py
```

## Project Structure
```
space-game/
├── main.py                 # Game loop and initialization
├── constants.py            # Game config: colors, dimensions, FPS
├── utils.py                # Rendering, file I/O, coordinate conversion
├── ship.py                 # Ship, PlayerController, AIShip classes
├── objects.py              # SpaceStation, Moon, StarField, NPCs, Dialogue
├── screens.py              # All game screens and UI (GameScreen, Menus, Dialogs, etc.)
├── config/
│   ├── space_system.json   # System layout: station position, AI ships
│   └── station_interior.json # Station rooms, NPCs, dialogue
├── saves/                  # Player save files (generated at runtime)
├── docs/
│   ├── README.md           # Architecture and systems overview
│   ├── CONTROLS.md         # Keyboard bindings and control documentation
│   └── DESIGN_PATTERNS.md  # Reusable patterns and best practices
└── requirements.txt        # pygame only
```

**Module Responsibilities:**
- **main.py** — Game loop, screen state machine, pygame initialization
- **constants.py** — Colors, game dimensions, UI configuration
- **utils.py** — Coordinate conversion, rendering helpers, file I/O, camera management
- **ship.py** — Ship physics, autopilot logic, player input handling
- **objects.py** — World objects (station, moon, starfield, NPCs)
- **screens.py** — All user-facing screens (game, menus, dialogs, interior exploration)

## Coordinate System
**Critical:** All game graphics are defined in **game-space** (800x600) and scaled to window size.
- Game space: 800x600 (fixed logical space)
- Screen space: Variable based on window resize
- Conversion functions: `to_screen(x, y)`, `to_screen_x()`, `to_screen_y()`
- Always use game-space for positions, velocities, etc.
- Only convert to screen-space when drawing

## Key Classes & Architecture

### Ships (in ship.py)
- **Ship** (base class): Position, angle, velocity, thrust, space_drag, rotation
  - `draw()`: Rotated polygon with thrust flame
  - `update()`: Physics simulation with autopilot integration
  - `update_autopilot()`: Kinematic-based autopilot controller
  - `_predict_braking_distance()`: Predict stopping distance
  - `_autopilot_approach()`, `_autopilot_brake()`: Autopilot execution
  - `wrap_position()`: Screen-wrapping at edges (torus topology)
- **PlayerController**: Owns Ship, handles WASD/arrow input for thrust and rotation
- **AIShip** (extends Ship): Autonomous behavior (accelerate/brake cycling with random course changes)

### Game Screens (in screens.py)
- **ScreenBase**: Base class for all screens with `get_state()` and `restore_state()`
- **GameScreen**: Main space exploration view (player, AI ships, star field, station)
- **StationInterior**: First-person station interior exploration with NPCs
- **MoonCity**, **MoonOutdoor**: Lunar location exploration
- **Menu**: Main menu (NEW/LOAD/QUIT, LOAD appears when saves exist)
- **PauseMenu**: In-game pause (Resume/Save/Quit)
- **SaveDialog**, **LoadMenu**: Save file browsing and selection
- **PilotNameDialog**: Pilot name entry for new games
- **LocationSelector**: Target selection for autopilot

### World Objects (in objects.py)
- **SpaceStation**: Rotating space station with landing detection
- **Moon**: Celestial body with surface and city
- **StarField**: Procedurally generated background stars
- **Person** (base): Position, sprite with body and head
- **NPC** (extends Person): Interactive character with behavior (bar/wander) and dialogue
- **Dialogue**: Text-based conversation system with options

## Save System
**Location:** `saves/` directory (auto-created)
**Format:** `save_{pilot_name}_{timestamp}.json`
**Contents:**
- `pilot_name`: Player identifier
- `name`: Save description (user-entered)
- `timestamp`: When saved
- `system`: Original system config
- `game_state`: Player/AI positions, velocities, angles

**On Load:**
1. Restore player/AI positions and velocities from `game_state`
2. Use original `system` config for static objects (station, star field)

## UI/Menu Flow
1. **Main Menu** → NEW/LOAD/QUIT
2. **NEW Game** → GameScreen (player at center)
3. **Pause Menu** (ESC) → Resume/Save/Quit with success banner
4. **Save Dialog** → Shows all saves (scrollable), enter pilot name or select to overwrite
5. **Load Menu** → Browse saves (scrollable), select to load
6. **Station Landing** (L key near station) → StationInterior
7. **Station Interior** (ESC) → Pause Menu

## Physics & Movement
- **Velocity**: Continuous momentum-based (not tile-based)
- **Drag**: Applied each frame (0.98 multiplier)
- **Max Velocity**: 4.0 units/frame
- **Thrust**: Incremental acceleration (0-0.3 per frame)
- **Rotation**: 5 degrees per frame

**Key Behavior:**
- Thrust OFF: Velocity decays via drag (coasting to stop)
- Thrust ON: Acceleration in direction ship is facing
- Reverse (DOWN key in station): Only decreases thrust, doesn't reverse velocity

## Configuration Files
**space_system.json**: System layout
```json
{
  "station": {"x": 0.75, "y": 0.3},
  "ai_ships": [{"x": 0.75, "y": 0.1, "color": [...]}]
}
```

**station_interior.json**: Interior layout & NPCs
```json
{
  "bar": {"x": 0.5, "y": 0.15},
  "hallway": {"narrow_width": 80, "transition_y": 0.5},
  "npcs": [{"name": "...", "x": ..., "behavior": "bar/wander", "dialogue_options": [...]}]
}
```

## Code Organization & Helpers

### Rendering & Utility Functions (in utils.py)
Core utilities used across all modules:
- **`to_screen(x, y)`** — Convert world to screen coordinates
- **`to_screen_x(x)`, `to_screen_y(y)`** — Single-axis screen conversion
- **`get_scale()`, `get_offset()`** — Rendering scale and centering
- **`set_camera_offset(x, y)`, `set_screen_size(w, h)`** — Camera and viewport management
- **`get_ui_scale()`, `get_ui_offset()`** — UI element scaling (independent of world zoom)
- **`load_json()`, `save_json()`** — File I/O with error handling
- **`get_save_files()`, `create_save_file()`, `load_save_file()`, `delete_save_file()`** — Save file management
- **`_list_files_by_pattern()`** — Unified file listing
- **`_handle_scrolling_input()`** — Shared menu navigation logic
- **`_center_text_x()`** — Text centering helper
- **`draw_debug_marker()`, `draw_target_brackets()`** — Debug visualization

### Ship Physics (in ship.py)
Integrated into Ship class with kinematic autopilot:
- **`Ship.update()`** — Physics simulation: thrust, velocity capping, drag, movement
- **`Ship.update_autopilot()`** — Autopilot controller (approach → brake phases)
- **`Ship._predict_braking_distance()`** — Kinematic prediction of stopping distance
- **`Ship._autopilot_approach()`, `_autopilot_brake()`** — Autopilot execution logic

### Constants (in constants.py)
- **`GAME_WIDTH`, `GAME_HEIGHT`** — World dimensions (2400x1800)
- **`CAMERA_ZOOM`** — Camera magnification (3.0x)
- **`SCREEN_WIDTH`, `SCREEN_HEIGHT`** — Window dimensions
- **`SAVE_DIR`** — Save directory path
- **Color constants** — BLACK, WHITE, GRAY, YELLOW, DARK_GRAY, GREEN, CYAN
- **`FPS`** — Frame rate (60)

## Common Fixes & Known Patterns

### Screen Deformation Issues
Always convert to screen-space only when drawing. Never store screen-space coords.

### Ship Rotation Math
Use proper 2D rotation matrix:
```python
rad = math.radians(angle)
cos_a = math.cos(rad)
sin_a = math.sin(rad)
rotated_x = lx * cos_a - ly * sin_a
rotated_y = lx * sin_a + ly * cos_a
```

### NPC Collision
Use `_is_in_valid_area()` to check hallway + bar regions before moving.

### Save Dialog
- Shows ALL saves in directory (not filtered by pilot)
- Scrolls 5 at a time with ↑/↓ indicators
- User selects existing save to overwrite or presses N for new

### Menu Persistence
Menu must be recreated when returning from load/save so "LOAD" option appears dynamically.

## Testing Checklist
- [ ] Game starts without errors
- [ ] Menu shows LOAD option after first save
- [ ] Player can move and rotate smoothly
- [ ] Momentum works (coasting after thrust off)
- [ ] Can land on station (L key within range)
- [ ] Can walk in station interior
- [ ] Save/load preserves position and velocity
- [ ] Scrolling works in save/load menus (5+ saves)
- [ ] Window resizing scales graphics smoothly
- [ ] AI ship appears and moves autonomously

## Automated Testing

**Run tests after making changes** to catch regressions:

```bash
python run_tests.py
```

**Current test coverage (49 tests):**
- Helper functions (18 tests):
  - `_handle_scrolling_input()` — 12 tests covering up/down navigation, wrapping, scrolling
  - `_list_files_by_pattern()` — 6 tests covering file filtering, sorting, directory creation
  - `_center_text_x()` — 3 tests covering horizontal centering and offset handling
- Physics engine (31 tests):
  - `update_velocity()` — 4 tests for thrust, drag, speed cap
  - `update_position()` — 2 tests for movement
  - `wrap_position()` — 5 tests for screen boundary wrapping
  - `update_thrust()` — 4 tests for thrust control
  - `update_angle()` — 5 tests for rotation
  - `get_distance()` — 4 tests for distance calculation
  - `can_land()` — 4 tests for landing conditions
  - `rotate_point()` — 3 tests for point rotation

**When to add new tests:**
1. **Before fixing a bug:** Write a test that reproduces the bug, then fix it
2. **After extracting a helper function:** Add unit tests for the pure function
3. **For critical paths:** Save/load, menu navigation, file operations

**How to add a test:**
1. Add test case to `tests/test_helpers.py` in the appropriate test class
2. Run `python run_tests.py` to verify
3. Commit the test along with the feature/fix

**Example: Testing a new helper function**
```python
def test_my_new_function(self):
    """Brief description of what this tests"""
    result = main.my_new_function(input_data)
    self.assertEqual(result, expected_output)
```

## Commit Message Convention
```
[Feature/Fix] Brief description

- Bullet points of changes
- One per line

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

## Next Feature Ideas
- Station docking/departure sequence
- Inventory system
- Asteroid/obstacle collision
- Multiple star systems
- Sound effects and music
- Multiplayer (local)
- Missions/objectives
