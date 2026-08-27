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

## For Agents: Autopilot & Physics Routine Changes

**⚠️ Read [docs/AUTOPILOT_TESTING.md](docs/AUTOPILOT_TESTING.md) before changing `SeekMode`,
`OrbitMode`, or their shared helpers in `game/world/autopilot.py`.** This code has a real
history of regressions that looked fine in a quick manual test and weren't - warn the user
up front that you'll validate against the documented battery (headless simulation across all
three ship types, both at-rest and pre-existing-velocity scenarios) before calling any change
done, not just fly it once and report success.

Known-good versions are preserved by commit specifically so they can be restored surgically -
every change so far has touched only `SeekMode.update()` and its immediate helpers, never any
other file, so reverting is always `git show <commit>:game/world/autopilot.py >
game/world/autopilot.py`. See the version history table in AUTOPILOT_TESTING.md for which
commit is which.

## For Agents: Performance & the Frame Budget

The game holds 60 FPS by doing all of a frame's work (input + simulation +
render + present) in **under 16.67 ms**. `game/perf_metrics.py` measures this
every frame; press `` ` `` (backtick) in-game to show the bottom-left panel.

**Monitor it whenever your change adds per-frame work** - a new drawable, an
AI/physics routine, a per-frame scan over all entities/systems/interiors, a new
`update()`/`draw()` path, or anything in `main.py`'s loop. Note the `frame`
average and the relevant `sim.*` / `render.*` span with debug on, make the
change, then compare. A change that pushes `frame` toward the budget or balloons
a span is a regression even if it "looks fine" - the same failure mode the
autopilot section describes.

**Instrument genuinely new expensive sections** by wrapping them in
`with perf.span("sim.<name>")` / `"render.<name>"` at the call site (import
`from game.perf_metrics import metrics as perf`), so the cost shows up in the
panel and the next agent sees any regression. Keep spans sharing a prefix
non-overlapping. Recording is cheap and always on; only the overlay is gated on
`constants.DEBUG_MODE`. See
[docs/UI_FLOW.md](docs/UI_FLOW.md#frame-timing-metrics).

## For Agents: Save Compatibility & Story Versioning

**Read [docs/SAVE_SYSTEM.md](docs/SAVE_SYSTEM.md) before changing anything a save file
depends on** - the story/save split below has already caused three separate real bugs
in one session (system not restored, moon location misdetected, ship scattered to the
wrong space coordinates on load) purely from getting this discipline wrong.

**The split:** a save references a story (and system) by ID (`game_state["story"]`,
`["system_id"]`) - anything that *doesn't* change during play (room layouts, ship
stats, dialogue trees, prices, NPC rosters) is read fresh from that story's config at
load time, never duplicated into the save. Anything that *does* change during play
(player position, credits, owned ships, loans, which interior, AI ship state, ...) is
**mutable state** and must be captured by `get_state()`/restored by `restore_state()`
(or the narrower `restore_possessions()` - see SAVE_SYSTEM.md for when each applies)
and documented in SAVE_SYSTEM.md's save-format description.

**Whenever a change makes something mutable that wasn't before** (a new kind of
possession, a new interior graph, a new field that can now vary) - update
`get_state()`/`restore_state()` in the same change, and update SAVE_SYSTEM.md's
documented format alongside it. Don't let a save silently stop capturing something
the player can now actually change.

**When adding a new persistent/named entity** (a new AI ship pilot, a new
character with saveable state, or anything else `get_state()`/`restore_state()`
matches by name or ID) - check what happens when an *old* save (made before that
entity existed) loads it, don't just assume "new content" is automatically safe
because it's additive. Station/moon NPCs are the easy case: they're pure story
config, rebuilt fresh from `npcs` every time a location loads and never referenced
by a save at all, so a new one just appears regardless of which save you're
loading. AI ship pilots are the case that actually needs checking: `SpaceScreen.
get_state()`'s `ai_ships` dict is keyed by pilot name, and `restore_state()` uses
that name to reposition an existing ship - a new pilot with no matching save entry
just starts fresh from its config position (fine), but *renaming* an existing
pilot silently orphans its old save entry instead of erroring, so the ship quietly
resets to its config default instead of restoring where the player actually left
it. Load (or construct, in a test) an old-shaped save state after this kind of
change and confirm the actual outcome, rather than assuming it away.

**Warn the user, explicitly and up front, whenever a change you're making could
change what an *existing* save file means once reloaded** - not just "I added a new
field" (that's normal, `.get(key, default)` handles it), but anything that changes
how an *already-stored* value gets interpreted: renaming/repurposing a save key,
changing a default fallback, changing which class/coordinate-space a stored value
feeds into, or changing detection logic that a save's stored value depends on. Don't
discover this after the fact - say so before you make the change, the same way you'd
flag any other user-facing behavior change.

**Story versioning:** `story.json` has a `"version"` field (semver-ish, e.g.
`"1.0.0"`), recorded into every save as `game_state["story_version"]`
(`SpaceScreen.story_version`, set by `build_save_game_state()` in `main.py`).
Loading warns (via `main.py`'s `warn_if_story_version_mismatch()`, non-blocking - it
never refuses to load) whenever a save's recorded version doesn't match the story's
current one, or predates versioning entirely (no `story_version` key at all). Bump a
story's version whenever you make a change that fits the warning criteria above -
that's what actually gives the warning teeth instead of it silently staying accurate
by accident.

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

### Menu Discoverability
**Rule:** A modal's primary actions are `draw_button` widgets in its own panel
(`buttons()`); controls that *aren't* buttons (grid browsing, drag-to-install,
map panning) go in the one-line dim `hint_text()` under the button bar. Update
both when you add/change an action. No modal uses the top-left Controls pane -
that's the in-world HUD's.

**Menu vs. Dialog (`MenuBase` / `DialogBase`):** every full-screen modal in
`game/ui/` is one of two kinds. **Neither draws a Controls pane** - that pane
belongs to the in-world HUD (`SpaceScreen`/`LocationScreen`) only. Every
modal shows its actions as `ui_theme.draw_button` widgets **inside its own
panel**, driven by mouse (hover + click) and keyboard (Tab / arrows move
button focus, Enter presses). See docs/DESIGN_PATTERNS.md's "Menu vs. Dialog".

- A **menu** (`MenuBase`, `is_dialog = False`) is one you *dwell in* -
  navigating or acting inside it doesn't close it (a Close/Resume button,
  ESC, or a hotkey does). → `BackdropMenu`, `PauseMenu`, `SaveBrowser`,
  `ShopMenu`, `OutfittingMenu`, `ShipBrowserMenu`, `ReportMenu`, `StarMap`.
- A **dialog** (`DialogBase`, `is_dialog = True`) sits *over* another modal
  and closes as soon as you pick one of its `buttons()`. → `ConfirmDialog`,
  `PilotNameDialog`, `ChoiceDialog`.

Subclasses implement `draw_content()` (the panel), `buttons()` (the action
bar), `button_bar_rects()` (where those go - default is a centred row along
the panel bottom; corner-Close menus override it), `panel_rect()` (so the
default bar + `hint_text()` line can anchor). `MenuBase.draw()` is a template
method that draws the content then the buttons + hint. A grid menu whose
Enter drives the grid (not the button) uses `handle_button_click()`
(mouse-only) rather than the full `handle_button_event()`. A menu with a
sub-dialog on top (`ShipBrowserMenu`'s purchase `ConfirmDialog`) returns it
from `active_popup()` so `MenuBase.draw` defers to it.

`main.py` builds `Menu`/`StorySelector` from `BackdropMenu`,
`LocationSelector`/`ExitMenu` from `ChoiceDialog`, `PossessionsMenu`/
`MissionLog` from `ReportMenu` + a builder fn, `LoadMenu`/`SaveDialog` from
`SaveBrowser(mode=...)` - the old per-screen classes are gone.

**Every menu panel** uses `modal_panel_rect()` for its main panel, which
caps width at `center_panel_max_width()` and re-centres on the real screen,
so a menu can't spill past the centre zone on a wide window.

Transient in-world popups in the Space View (mission toasts, jump-complete
notice, one-way hail banners, the "too close to jump" warning) are each
wrapped in their own glass pane (`draw_glow_message` always draws its pane)
and rendered as a **downward stack** in `SpaceScreen._draw_hud` so two
showing at once never overlap.

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
Per the **One Class Per File** rule above, each class lives in its own
`snake_case.py` file (e.g. `Ship` → `ship.py`, `AIShip` → `ai_ship.py`,
`SpaceScreen` → `space_screen.py`). There is no `objects.py` or `screens.py`
grouping file. Python files live under the `game/` package, grouped into
`game/world/` (physics/entities), `game/screens/` (the two `ScreenBase`
screens), and `game/ui/` (menus/dialogs) — `game/constants.py` and
`game/utils.py` sit at the package root since they're shared by all three.
`main.py` and `run_tests.py` stay at the repo root as entry points. Run
`ls game/**/*.py` (or see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)) for
the current, authoritative class list and hierarchy diagrams. Imports are
absolute and rooted at the package, e.g. `from game.world.ship import Ship`,
`import game.utils as utils` — never relative imports.

```
space-game/
├── main.py                  # Game loop, screen state machine, pygame initialization
├── run_tests.py             # Test runner (discovers tests/test_*.py)
├── game/
│   ├── constants.py          # Colors, game dimensions, UI configuration
│   ├── utils.py               # Coordinate conversion, rendering helpers, file I/O, camera management
│   ├── world/
│   │   ├── world_object.py    # WorldObject base (position, drawing) — Ship and Landable extend it
│   │   ├── ship.py, ai_ship.py, player_controller.py, autopilot.py   # Ship physics, AI behavior, input, flight computer
│   │   └── central_star.py, asteroid.py, asteroid_field.py, starfield.py, landable.py,
│   │       person.py, npc.py, dialogue.py                            # World objects and NPCs
│   ├── screens/
│   │   └── screen_base.py, space_screen.py, location_screen.py       # ScreenBase and the two concrete screens
│   └── ui/
│       └── menu.py, menu_backdrop.py, story_selector.py, pause_menu.py, save_dialog.py, load_menu.py,
│           confirm_dialog.py, pilot_name_dialog.py, location_selector.py, star_map.py,
│           selectable_list.py, ui_theme.py                           # Menus/dialogs (not ScreenBase) + shared UI styling/widgets
├── config/
│   └── stories/{story}/    # All config is per-story — nothing shared between stories
│       ├── ship_types.json, graphics.json, cultures.json, building_types.json, pilots.json
│       └── systems/{system_id}.json  # System layout: station position, AI ships
├── saves/                  # Player save files (generated at runtime)
├── tests/                  # test_*.py, discovered by run_tests.py
├── docs/
│   ├── README.md           # Docs index and systems overview
│   ├── ARCHITECTURE.md     # Class hierarchy and design patterns (source of truth for structure)
│   ├── CONTROLS.md         # Keyboard bindings and control documentation
│   ├── DESIGN_PATTERNS.md  # Reusable patterns and best practices
│   ├── PHYSICS.md          # Coordinate system and movement physics
│   ├── SAVE_SYSTEM.md      # Save/load format and flow
│   └── UI_FLOW.md          # Screen state machine
└── requirements.txt        # pygame only
```

## Coordinate System
**Critical:** All game graphics are defined in **game-space** (2400x1800) and scaled to window size.
- Game space: 2400x1800 (fixed logical space, see `GAME_WIDTH`/`GAME_HEIGHT` in constants.py)
- Screen space: Variable based on window resize
- Conversion functions: `to_screen(x, y)`, `to_screen_x()`, `to_screen_y()`
- Always use game-space for positions, velocities, etc.
- Only convert to screen-space when drawing
- See [docs/PHYSICS.md](docs/PHYSICS.md#coordinate-system) for full details

## Key Classes & Architecture
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full, up-to-date class
hierarchy (World Objects, Screens, Ship physics, Autopilot) — do not rely on a
structure snapshot in this file for class details, only for the file-layout
convention above.

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
**config/stories/{story}/systems/{system_id}.json**: System layout
```json
{
  "station": {"x": 0.75, "y": 0.3},
  "ai_ships": [{"x": 0.75, "y": 0.1, "color": [...]}]
}
```

**Interior layout** (per key in a landable's `interiors`, in the system JSON): a
`culture`, one or more `rooms` (each a `{"rect": [...]}`, `{"polygon": [[x,y],…]}`,
or `{"shape": "circle", "center": […], "radius": r}` — walkable area is their
union), `portals` (usually one, `{"x", "y", "return_to_ship": true}` for a
station's ship dock), optional `decorations` (cosmetic floor/wall decals), and
`npcs`. A default-story station is now a **single** such interior. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)'s "Interior geometry" and
`game/screens/location_screen.py` (`normalize_room` / `normalize_decoration` /
`plan_path`).
```json
{
  "label": "Alpha Station", "culture": "vherathi",
  "portals": [{"x": 660, "y": 345, "connected_locations": [], "return_to_ship": true}],
  "rooms": [{"label": "Concourse", "shape": "circle", "center": [400, 300], "radius": 150}],
  "decorations": [{"layer": "floor", "shape": "circle", "center": [400, 300], "radius": 46, "color": [96, 74, 110]}],
  "npcs": [{"name": "...", "x": 400, "y": 100, "role": "bartender", "dialogue_options": [...]}]
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

### NPC / player collision inside a location
`LocationScreen.can_move_to(x, y)` is the one walkable-area check (point in the
union of the room polygons, minus building footprints). The player's movement,
`WanderRoutine`, and `DockRoutine` (via `plan_path`) all go through it — never
reimplement the bounds test.

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

**Current test coverage (21 tests, all in `tests/test_helpers.py`):**
- Helper functions (18 tests):
  - `_handle_scrolling_input()` — 9 tests covering up/down navigation, wrapping, scrolling
  - `_list_files_by_pattern()` — 6 tests covering file filtering, sorting, directory creation
  - `_center_text_x()` — 3 tests covering horizontal centering and offset handling
- Autopilot physics (3 tests): `TestAutopilotPhysics` drives a real `Ship` through `engage_seek()` +
  `ship.update()` toward a real `Landable`, using `ship.autopilot_active` (not a reimplemented distance/speed
  check) as the landing signal - one case per ship_types.json stat preset (shuttle/freighter/patrol), each
  asserting it lands, arrives close, stops, and doesn't oscillate.

There used to be a `tests/test_physics.py` testing a `game_physics` module (pure-function physics, plus
screen-wrap behavior) - neither exists in this codebase anymore (physics now lives on `Ship`/`WorldObject`/
`Autopilot`, and there's no screen-wrapping), so it always failed to import and never actually ran. Deleted
rather than resurrected, since a parallel `game_physics.py` would just duplicate the real logic. If you add a
new pure physics helper, prefer testing it as a method on the class that owns it, the way `TestAutopilotPhysics`
does now, rather than reintroducing a standalone physics module.

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
- Sound effects and music (started: runtime sound board with a UI "ping" — see [docs/SOUND.md](docs/SOUND.md))
- Multiplayer (local)
- Missions/objectives
