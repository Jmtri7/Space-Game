# Space Game Development Guide

**For detailed documentation, see [docs/README.md](docs/README.md)** — comprehensive guides on architecture, physics, save systems, UI flow, and design patterns.

## Project Overview
A pygame-based space exploration game with procedurally generated star fields, AI ships, space stations with NPCs, and a complete save/load system. The game features physics-based ship movement, NPC dialogue, and persistent game state.

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

## For Agents: Testing Guidance

**CRITICAL: After any code changes (features, fixes, refactors), you MUST:**
1. Close all running game instances
2. Run automated tests: `python run_tests.py`
3. Start the game fresh: `python main.py`
4. Test the feature/fix in-game to verify changes took effect

This is non-negotiable. Code changes must be loaded and verified in-game before considering work done.

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
├── main.py                 # Complete game implementation (~1000+ lines)
├── config/
│   ├── space_system.json  # System layout: station position, AI ships
│   └── station_interior.json # Station rooms, NPCs, dialogue
├── saves/                 # Player save files (generated at runtime)
└── requirements.txt       # pygame only
```

## Coordinate System
**Critical:** All game graphics are defined in **game-space** (800x600) and scaled to window size.
- Game space: 800x600 (fixed logical space)
- Screen space: Variable based on window resize
- Conversion functions: `to_screen(x, y)`, `to_screen_x()`, `to_screen_y()`
- Always use game-space for positions, velocities, etc.
- Only convert to screen-space when drawing

## Key Classes & Architecture

### Ships
- **Ship** (base class): Position, angle, velocity, thrust, drag, rotation
  - `draw_ship()`: Rotated polygon with flame at rear
  - `wrap_position()`: Screen-wrapping at edges
  - `update()`: Physics simulation
- **Player** (extends Ship): Handles WASD/arrow input, thrust control
- **AIShip** (extends Ship): Autonomous behavior (wanders, avoids)

### Game Screens
- **GameScreen**: Space view with player, AI ships, star field, station
  - `get_state()`: Saves player/AI positions for save files
  - `restore_state()`: Restores positions from save files
- **StationInterior**: First-person station exploration
- **Menu**: NEW/LOAD/QUIT menu (LOAD appears when saves exist)
- **PauseMenu**: Resume/Save/Quit with success banner
- **SaveDialog**: Shows all saves, allows overwriting, scrolling list
- **LoadMenu**: Browse and load saves with scrolling

### NPCs & Dialogue
- **Person** (base): Position, sprite drawing (body + head)
- **NPC** (extends Person): Behavior (bar/wander), dialogue system
- **Dialogue**: Text-based conversation tree with options

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

### Extracted Helper Functions (in main.py)
These functions eliminate duplication across menus:
- **`_list_files_by_pattern(directory, prefix, suffix)`** — Unifies file listing for SaveDialog and get_save_files()
- **`_handle_scrolling_input(key, selected, items, scroll_offset, max_visible)`** — Shared up/down navigation for SaveDialog and LoadMenu
- **`_center_text_x(surface, text, offset_x=0)`** — Unified menu text centering

### Physics Engine (in game_physics.py)
Pure functions decoupled from Pygame for testability:
- **`update_velocity(vx, vy, thrust, angle)`** — Apply thrust and drag, cap speed
- **`update_position(x, y, vx, vy)`** — Move ship by velocity
- **`wrap_position(x, y)`** — Handle screen wrapping (torus topology)
- **`update_thrust(thrust, keys_accel, keys_decel)`** — Control thrust input
- **`update_angle(angle, keys_left, keys_right)`** — Rotate ship
- **`get_distance(x1, y1, x2, y2)`** — Euclidean distance
- **`can_land(px, py, sx, sy)`** — Check landing conditions
- **`rotate_point(x, y, cx, cy, angle)`** — 2D point rotation

These are tested independently (31 tests) and can be used without Pygame.

### Constants
- **`SAVE_DIR = "saves"`** — Centralized save directory path (replaces hardcoded strings)

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
