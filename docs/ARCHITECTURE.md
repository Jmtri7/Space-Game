# Architecture & Class Design

The hub for project structure. **Source of truth for project layout and file
conventions** — the sections below, not any snapshot in `CLAUDE.md`. The depth
lives in four sub-pages; read the one your task needs, not all four.

| Sub-page | Owns |
|---|---|
| [architecture/class-hierarchy.md](architecture/class-hierarchy.md) | Class hierarchy + composition: `WorldObject`/`Ship`/`Autopilot`/`PlayerController`, `Person`, `Character` + the `Routine` model, `Dialogue`, `Possessions`, `mission.py`, `LandingSite`, `SpaceScreen`, `SystemState` multi-system sim, the screen-flow state machine |
| [architecture/config-formats.md](architecture/config-formats.md) | Every per-story JSON shape: `systems/*.json`, interior layout + interior geometry, `story.json` fields, adding a ship type |
| [architecture/combat-and-mining.md](architecture/combat-and-mining.md) | Weapon outfits, ship-to-ship combat, provocation/hostility, asteroid breakup + ore pickups |
| [architecture/extensibility.md](architecture/extensibility.md) | Step-by-step recipes: new entity, new screen, new role/routine, new ship type |

See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) for reusable solutions across the codebase.

## Project Layout & File Conventions

A pygame space-exploration game: procedurally generated star fields, AI ships,
station/moon interiors with NPCs, physics-based flight, full save/load.

```
space-game/
├── main.py                  # Game loop, screen state machine, pygame init
├── run_tests.py             # Test runner (discovers tests/test_*.py)
├── game/
│   ├── constants.py          # Colors, dimensions, UI config (shared)
│   ├── utils.py              # Coord conversion, render helpers, file I/O, camera (shared)
│   ├── world/               # Physics / entities
│   │   ├── world_object.py   # WorldObject base — Ship and LandingSite extend it
│   │   ├── ship.py, ai_ship.py, player_controller.py, autopilot.py
│   │   ├── character.py, person.py, possessions.py, dialogue.py, mission.py
│   │   ├── *_routine.py      # One Routine class per file (dock/orbit/wander/…)
│   │   └── central_star.py, asteroid.py, asteroid_field.py, starfield.py, landing_site.py
│   ├── screens/             # ScreenBase and the two concrete screens
│   │   ├── screen_base.py
│   │   ├── space_screen/     # SpaceScreen: screen.py (core) + mixins
│   │   │   (setup/targeting/hud/hailing/npc_sync/jump/combat/mining), _defs.py
│   │   └── location_screen/  # LocationScreen: screen.py (core) + mixins
│   │       (portals/npcs/decor/draw/structures/movement), _defs.py
│   ├── ui/                  # Menus/dialogs (not ScreenBase) + shared UI styling
│   │   └── menu_base.py, dialog_base.py, ui_theme.py, save_browser.py, …
│   └── audio/
│       └── sound_board.py, music.py
├── config/
│   ├── stories/{story}/     # Per-story config (a story may also opt into shared modules)
│   │   ├── story.json, ship_types.json, graphics.json, cultures.json,
│   │   │   building_types.json, pilots.json, commodities.json, items.json, missions.json,
│   │   │   factions.json (optional — cross-system factions + player reputation),
│   │   │   endings.json (optional — epilogue text per "end_story:<id>", by faction standing)
│   │   └── systems/{system_id}.json   # Station/moon placement, AI ship roster
│   └── modules/{module}/    # Shared config kits stories opt into via story.json "modules"
│                            # — same subtree shape; see docs/CONFIG_MODULES.md
├── saves/                   # Player save files (runtime-generated)
├── tests/                   # test_*.py, discovered by run_tests.py
└── docs/                    # This documentation tree — see docs/README.md
```

**One Class Per File.** Each Python file contains exactly one class. Filename is
`snake_case.py` matching the class: `MyClass` → `my_class.py`. Exceptions are
utility/constant modules (`utils.py`, `constants.py`) and deliberately
function-only modules (`game/world/mission.py`) — a module-level docstring notes
when a file is an intentional exception (e.g. `ui_theme.py`, `perf_metrics.py`).
If a class extends another, both imports go at the top of the child file.

**Imports are absolute, rooted at the package** — `from game.world.ship import
Ship`, `import game.utils as utils`. Never relative imports.

**Entry points** (`main.py`, `run_tests.py`) stay at the repo root.

## Shared Helpers (`game/utils.py`, `game/constants.py`)

`utils.py` — used across all modules:

- `to_screen(x, y)`, `to_screen_x(x)`, `to_screen_y(y)` — world → screen coords
- `get_scale()`, `get_offset()` — render scale and letterbox centering
- `get_ui_scale()`, `get_ui_offset()` — UI scaling, independent of world zoom
- `set_camera_offset(x, y)`, `set_screen_size(w, h)` — camera / viewport
- `advance_accumulator(acc, dt)` — fixed-timestep step arithmetic (pure; see
  [UI_FLOW.md](UI_FLOW.md#main-loop-fixed-timestep-three-phases))
- `load_json()`, `save_json()` — file I/O with error handling
- `get_save_files()`, `create_save_file()`, `load_save_file()`,
  `delete_save_file()` — save-file management
- `_list_files_by_pattern()`, `_handle_scrolling_input()`, `_center_text_x()` —
  shared list/menu helpers (see [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md))
- `draw_debug_marker()`, `draw_target_brackets()` — debug visualization

`constants.py` — `GAME_WIDTH`/`GAME_HEIGHT` (2400×1800), `CAMERA_ZOOM`,
`SCREEN_WIDTH`/`SCREEN_HEIGHT`, `FPS` (60), `SAVE_DIR`, `WALKING_SPEED`,
`DEBUG_MODE`, `AA_MODE`, color constants.

## Entity Design Principle

`WorldObject` factors out what `Ship` and `LandingSite` both need:

```python
class WorldObject:
    def __init__(self, x, y, graphics=None):
        self.x, self.y = x, y
        self.graphics = graphics or {}

    def get_distance(self, target_x, target_y):
        # Shared range-check math

    def _draw_rotated_polygon(self, surface, local_points, angle, color):
        # Shared rotate-local-points-and-draw-polygon logic
```

**Key principle:** Store positions in game-space, convert to screen-space only
when drawing. See [PHYSICS.md](PHYSICS.md#coordinate-system) for coordinate
conversion details, and
[architecture/class-hierarchy.md](architecture/class-hierarchy.md) for how
`Ship`, `Person`, and `Character` build on this.

## Configuration Files

Config lives under `config/stories/{story}/`; two stories can define the same
key with different values. A story may additionally list shared **modules**
(`config/modules/{name}/`) in its `story.json` — the resolver in
[`game/config_source.py`](../game/config_source.py) merges those under the
story's own files, with the story always winning. See
[CONFIG_MODULES.md](CONFIG_MODULES.md). Configs are never modified by play.
The full per-file format reference is
[architecture/config-formats.md](architecture/config-formats.md); the
story/save split is in
[SAVE_SYSTEM.md](SAVE_SYSTEM.md#directory-structure).
