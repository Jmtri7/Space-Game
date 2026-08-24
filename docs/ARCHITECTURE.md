# Architecture & Class Design

Class hierarchy, entity patterns, and extensibility points for the space game.

## Class Hierarchy

### World Objects (Position + Drawing)
```
WorldObject (base — x, y, graphics, get_distance(), _draw_rotated_polygon())
├── Ship (physics, autopilot, rotation)
│   └── AIShip (autonomous accelerate/brake wandering)
└── Landable (space station or moon — config decides which)

Person (base — x, y, draw(), get_distance())
└── NPC (adds behavior, name, Dialogue)
```

`PlayerController` does **not** subclass `Ship` — it *owns* one (composition) and
exposes `x`/`y`/`velocity_x`/`velocity_y`/`angle`/`autopilot_active`/`autopilot_target`
as delegating properties for backward compatibility, plus `handle_input()` for
WASD/arrow control.

### Screens (State Machine)
```
ScreenBase (implicit interface: handle_input/update/draw/get_state/restore_state)
├── SpaceScreen     — flight & exploration (owns player, AI ships, station, moon)
└── LocationScreen  — generic interior/exterior location, config-driven
                       (used for BOTH the station interior and moon locations)
```
Menus and dialogs (`Menu`, `StorySelector`, `PilotNameDialog`, `LoadMenu`,
`PauseMenu`, `SaveDialog`, `ConfirmDialog`, `LocationSelector`) don't extend
`ScreenBase` — they're simpler `handle_input()`/`draw()` objects driven directly
by the main loop. See [UI_FLOW.md](UI_FLOW.md) for the full state machine.

### Supporting Classes
- `StarField` — Procedural star generation with seeded randomness
- `Dialogue` — Conversation tree system used by `NPC`

## Entity Design Pattern

`WorldObject` factors out what `Ship` and `Landable` both need:

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

**Key principle:** Store positions in game-space, convert to screen-space only when drawing.

See [PHYSICS.md](PHYSICS.md#coordinate-system) for coordinate conversion details.

## Ship Class: Movement & Rotation

**Base Class: `Ship(WorldObject)`**
- Stores: `x`, `y`, `angle`, `velocity_x`, `velocity_y`, `thrust`, `space_drag`
- Physics: `acceleration_magnitude`, `max_velocity`, `rotation_speed`
- Methods:
  - `draw(surface, ship_size, color)` — rotated polygon (via `_draw_rotated_polygon`) + thrust flame
  - `wrap_position()` — screen-edge wrapping (torus topology)
  - `update()` — runs `update_autopilot()`, then thrust/drag/velocity-cap physics
  - `update_autopilot()`, `_autopilot_point_and_thrust()`, `_calculate_brake_redirect_angle()`,
    `_predict_braking_distance_from_stop()` — kinematic autopilot controller
  - `predict_landing_trajectory()` / `predict_landing_position()` — forward-simulates
    the autopilot to produce waypoints for the trajectory overlay

**Wrapper: `PlayerController`**
- Owns a `Ship` instance, translates WASD/arrow keys into `turn_left()`/`turn_right()`/
  `increase_thrust()`/`point_to_reverse_velocity()`/`release_thrust()`
- Blocks input while `autopilot_active` is true

**Subclass: `AIShip(Ship)`**
- Reads `acceleration_magnitude`/`max_velocity`/`rotation_speed` from a `ship_type` dict
  (see `config/ship_types.json`), falling back to defaults if none given
- Own `update()` implements a simple `"accelerate"` ↔ `"brake"` state machine with
  randomized timers and heading jitter — does not use the `Ship` autopilot

**Extending for new ship types:**
```python
class Shuttle(Ship):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_velocity = 2.0  # Different specs

    def update(self):
        # Custom behavior
        super().update()  # Physics still applies
```

## Person Class: NPCs & Drawing

**Base Class: `Person`**
- Stores position and appearance
- Implements `draw(surface)` — head + body
- Provides `get_distance(x, y)` for interaction checks

**Subclass: `NPC(Person)`**
- Adds `behavior` (bar/wander) and a `Dialogue` instance
- Loaded per-location from `npcs` entries in the location's config JSON

## Landable: Stations & Moons

**Class: `Landable(WorldObject)`**
- One class, two visual modes — decided at construction by inspecting `graphics`:
  `is_station = "rotation_speed" in graphics or graphics.get("shape") in ["hexapod", "octagon"]`
- Station mode: rotates (`rotation_speed`), drawn as a polygon with a glowing core
- Moon mode: static circle with craters
- `landing_distance` — how close the player must get (and how slow) to land
- `interiors` — dict of location keys → interior config (file path or inline dict),
  consumed by `LocationScreen` when the player lands

## SpaceScreen Responsibility

**`SpaceScreen` contains:**
- `PlayerController` (controlled entity)
- A list of `AIShip` (autonomous entities, loaded from story config)
- `StarField` (visual, procedural)
- Two `Landable` instances: `station` and `moon`

**`SpaceScreen` provides:**
- `update()` — advance all entity physics, recenter camera, auto-land when autopilot arrives
- `draw()` — render entities, target brackets/label/arrow, HUD
- `handle_input()` — targeting (T), landing/autopilot engage (L), pause (ESC)
- `get_state()` / `restore_state()` — capture/restore player + all AI ships for save
  [see SAVE_SYSTEM.md](SAVE_SYSTEM.md)

**Why this design:**
- Clear separation of concerns
- Easy to pause/resume game state
- Simple to add new entity types (extend and add to update/draw)

## State Machine: Screen Flow

```
Menu → StorySelector → PilotNameDialog → SpaceScreen ←→ PauseMenu
                                              ↓ (land: L)   ↓ (save)
                            LocationScreen (station) ←→ SaveDialog

SpaceScreen → LocationSelector → LocationScreen (moon) ←→ PauseMenu
```

**State transitions via return values:**
- `handle_input()` returns an action string
- Main loop (`main.py`) interprets it and transitions `current_screen`
- See [UI_FLOW.md](UI_FLOW.md) for the full diagram and every state

## Extensibility Points

### Adding a New Entity Type
1. Create a class extending `Ship`, `Landable`, or `Person`
2. Override `update()` and/or `draw()`
3. Add to `SpaceScreen` (or a location's NPC list)
4. Include in `get_state()`/`restore_state()` if saveable

### Adding a New Screen
1. Create a class with `handle_input()`, `draw()` (and `update()` if it needs one)
2. Add a `current_screen` string and branch in `main.py`'s loop
3. Implement transitions via `handle_input()` return values

### Adding NPC Behaviors
1. Add the behavior name to the location's config JSON (`npcs[].behavior`)
2. Implement a `_behavior_[name]()` method on `NPC`
3. Call it from `update()` based on the behavior string

## Design Decisions

**Why `WorldObject` as a base for `Ship` & `Landable`?**
- DRY: both needed position, `get_distance()`, and rotate-and-draw-polygon logic
- Added when the arrow-around-ship HUD feature surfaced the duplication directly

**Why one generic `LocationScreen` instead of separate station/moon classes?**
- Station interior, moon city, and moon wilderness are all "walk around, talk to
  NPCs, exit near the entrance" — the only difference is config data
- New locations are added by writing JSON, not new Python classes (see the
  Data-Driven Configuration pattern in [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md))

**Why `get_state()`/`restore_state()` on every screen?**
- Centralized state capture for save/load
- Clear contract for what needs persistence
- Easy to extend when adding new saveable objects

**Why screen-wrapping over boundaries?**
- Creates infinite space feel with small coordinate system
- Simple physics (no out-of-bounds checks)
- Player can explore infinitely without loading new areas

See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) for reusable solutions across the codebase.
