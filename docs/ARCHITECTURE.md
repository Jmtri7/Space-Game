# Architecture & Class Design

Class hierarchy, entity patterns, and extensibility points for the space game.

## Class Hierarchy

### World Objects (Position + Drawing)
```
WorldObject (base — x, y, graphics, get_distance(), _draw_rotated_polygon())
├── Ship (physics, rotation; owns an Autopilot via composition)
└── Landable (space station or moon — config decides which)

Person (base — x, y, draw(), get_distance(), owns a Possessions)
```
There is no `AIShip`/`NPC` subclass anymore - every non-player character
(ship-flying or not) is a `Character` (`game/world/character.py`), which
*composes* a `Person` and, optionally, a `Ship` - it never inherits `Ship`,
exactly like `PlayerController` already didn't. A `Character` with no ship
(any station/moon NPC) is just a body with a role; one with a ship (an AI
pilot) is that same body plus the ship it flies. See "Character: AI Pilots
& NPCs" below.

Every `Person` — the player's own body (`PlayerCharacter`/`PlayerController.person`),
every `Character`'s `person`, and an AI pilot's `Character.person` — owns a
`Possessions` (credits, owned ships, loans) by composition, not just the
player. The player's one real `Possessions` object is shared by reference
across `SpaceScreen` and every `LocationScreen` (see
`SpaceScreen.get_interior_screen`'s `player_possessions` injection) so a
purchase in one location is instantly visible everywhere else.

`PlayerController` does **not** subclass `Ship` — it *owns* one (composition) and
exposes `x`/`y`/`velocity_x`/`velocity_y`/`angle`/`autopilot_active`/`autopilot_target`
as delegating properties for backward compatibility, plus `handle_input()` for
WASD/arrow control. `Character` mirrors this exact property list (only
meaningful when it has a ship) so both duck-type as a flyable ship the same
way for `SpaceScreen`/autopilot code.

### Screens (State Machine)
```
ScreenBase (implicit interface: handle_input/update/draw/get_state/restore_state)
├── SpaceScreen     — flight & exploration (owns player, AI ships, station, moon)
└── LocationScreen  — generic interior/exterior location, config-driven
                       (used for BOTH the station interior and moon locations)
```
Menus and dialogs (`Menu`, `StorySelector`, `PilotNameDialog`, `LoadMenu`,
`PauseMenu`, `SaveDialog`, `ConfirmDialog`, `LocationSelector`, `ExitMenu`,
`PossessionsMenu`) don't extend
`ScreenBase` — they're simpler `handle_input()`/`draw()` objects driven directly
by the main loop. See [UI_FLOW.md](UI_FLOW.md) for the full state machine.

### Supporting Classes
- `StarField` — Procedural star generation with seeded randomness
- `Dialogue` — Conversation tree used by `NPC`: nodes of text + options, each
  option either advancing to another node, closing (`"next": null`), or - for
  a few commerce-flavored NPCs - carrying an `"action"` (`"buy_ship:<id>"`,
  `"take_loan"`) that `LocationScreen` applies against the player's
  `Possessions`. `Dialogue.from_flat()` builds the simple one-node shape most
  NPCs still use.
- `Possessions` — credits/owned ships/loans, composed onto every `Person`
- `Autopilot` — flight computer owned by a `Ship` (see Ship Class section below)
- `CentralStar`, `Asteroid` — ambient `WorldObject`s (non-interactive, non-landable)

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
- Owns an `Autopilot` (see below) via `self.autopilot = Autopilot(self)`
- Methods:
  - `draw(surface, ship_size, color)` — rotated polygon (via `_draw_rotated_polygon`) + thruster flames
  - `update()` — runs `self.autopilot.update()`, then thrust/drag/velocity-cap physics
    (the world is open/unbounded — no screen-wrapping; see PHYSICS.md)
  - `engage_seek(target)` / `engage_orbit(center_x, center_y, radius)` — thin pass-throughs
    to the owned `Autopilot`
  - `autopilot_active` / `autopilot_target` — backward-compatible properties mirroring
    `self.autopilot.active` / `self.autopilot.target`

**Component: `Autopilot`** (in `autopilot.py`, one per `Ship`, composition not inheritance)
- Two standardized modes: `"seek"` (approach `target`, arrive once close and slow enough —
  the unified controller that redirects AND decelerates simultaneously) and `"orbit"`
  (continuously circle a fixed point at a fixed radius; never arrives)
- Talks to its ship only through kinematic reads and `turn_left()`/`turn_right()`/
  `increase_thrust()`/`release_thrust()` — see [PHYSICS.md](PHYSICS.md) for the controller math

**Wrapper: `PlayerController`**
- Owns a `Ship` instance, translates WASD/arrow keys into `turn_left()`/`turn_right()`/
  `increase_thrust()`/`point_to_reverse_velocity()`/`release_thrust()`
- Blocks input while `autopilot_active` is true
- Applies `ship_type` stats (`max_thrust`/`max_velocity`/`rotation_speed`) to its `Ship`
  at construction, same as `Character.for_ai_pilot()` does

**Composition: `Character`** (`game/world/character.py`) — see the full
section below; the AI-pilot equivalent of `PlayerController`. Built via
`Character.for_ai_pilot(...)`, which reads `acceleration_magnitude` (from
`ship_type`'s `max_thrust`), `max_velocity`, `rotation_speed` from a
`ship_type` dict (see `config/stories/{story}/ship_types.json`), falling
back to defaults if none given. Its `update()` never touches ship physics
directly — it runs the role's routine each frame (from `ROLE_ROUTINES`,
keyed by the pilot's role, with `FACTION_ROUTINE_OVERRIDES` checked first),
which calls `engage_seek()`/`engage_orbit()` (delegated to the owned
`Ship`), then `self.ship.update()` runs the real `Ship`/`Autopilot` physics.

### Adding or Updating a Ship Type

Almost always **data-driven, not a new class** — add an entry to
`config/stories/{story}/ship_types.json` (physics/turning: `max_thrust`, `max_velocity`,
`rotation_speed`) and a matching entry in `config/stories/{story}/graphics.json`'s `"ships"`
section (`size`, `color`, `shape`, `thrusters`, optionally `thruster_width`/`thruster_length`).
Reference the type's key from one of the story's `systems/{system_id}.json` files
(`ai_ships[].ship_type`) or `story.json` (`ships.player_type`) — no Python required.

Only subclass `Ship` when you need genuinely new *behavior*, not new stats -
and prefer composing one onto a `Character`/`PlayerController`-style wrapper
(as both already do) over subclassing it at all.

**Rough low / medium / high bands**, based on the spread across this game's ship roster
(`shuttle`, `freighter`, `patrol`, plus retired types `fighter`/`explorer`/`trader`/`scout`/
`hauler`/`liner`/`miner`/`courier` that established the range):

| Stat | Low | Medium | High |
|---|---|---|---|
| `max_thrust` (acceleration/frame) | 0.08 – 0.15 | 0.15 – 0.35 | 0.35 – 0.5 |
| `max_velocity` (units/frame) | 1.5 – 3 | 3 – 5 | 5 – 6.5 |
| `rotation_speed` (degrees/frame) | 1 – 3 | 3 – 7 | 7 – 10 |
| `size` (world units) | 8 – 14 | 14 – 24 | 24 – 35 |

A rule of thumb from the existing roster: big/slow cargo ships (`freighter`) pair low thrust +
low velocity + low rotation + high size; small/agile ships (`patrol`) pair medium-high thrust +
medium-high velocity + medium-high rotation + low size. Values well outside these ranges will
still work (nothing enforces them) but will feel very different from the rest of the fleet.

**Culture and material palette:** if a ship (or building — see `Landable`/`LocationScreen`
below) belongs to an existing culture, set `"culture": "<culture_id>"` in its `graphics.json`/
`building_types.json` entry instead of hardcoding `color`. `get_graphics_asset()`/
`get_building_type()` (in `utils.py`) automatically fill in `color`, `core_color`/
`window_color`, and `thrust_color` from that culture's `metal_color`/`glass_color`/
`thrust_color` in `config/stories/{story}/cultures.json`. Each culture entry also carries a
`theme` field — read it and follow it when designing new ships or buildings for that culture,
so the whole culture stays visually cohesive. See `config/stories/default/cultures.json` for
the currently defined cultures (e.g. the Vherathi Concord).

## Person Class: Bodies & Drawing

**Base Class: `Person`**
- Stores position, appearance, an `outfit`, and a `Possessions`
- Implements `draw(surface)` — head + body, with the outfit's helmet/suit/
  boot colors (if any) drawn over the shared body shape
- Provides `get_distance(x, y)` for interaction checks

`outfit` is a resolved `graphics.json` "outfits" asset (see
`get_graphics_asset(story, "outfits", outfit_id)`), same pattern as ship/
station graphics. Every `Person` today is built with `"space_suit"`
(`SpaceScreen`/`LocationScreen` resolve it and pass it in); a bare `Person`
with no outfit just shows the plain body colors. Adding a new outfit is a
new `graphics.json` entry plus whatever picks its id per-character (e.g.
an NPC config's `"outfit"` field) - no drawing-code changes needed.

`Person` itself has no behavior/role concept - that lives on `Character`
(see below), which owns a `Person` rather than subclassing it. Local NPCs
are built by `LocationScreen._build_local_character()`: a `Person` (with a
`Dialogue` attached), wrapped in a `Character` with `ship=None`.

## Character: AI Pilots & NPCs

**Class: `Character`** (`game/world/character.py`) - composes a `person`
(`Person`, always) and an optional `ship` (`Ship`, only for AI pilots), plus
a `role` string and the `Routine` that role picks. This is the *one*
mechanism behind every non-player character in the game:

- **AI ship pilots** (`ship` set): built via `Character.for_ai_pilot(...)`
  from `SpaceScreen._load_system_content()`. Role comes from `pilots.json`
  (`freighter_pilot`, `patrol_officer`, ...).
- **Station/moon NPCs** (`ship=None`): built inline by `LocationScreen`.
  Role comes from each `npcs[]` entry's `"role"` in the location's config
  (`bartender`, `guard`, `resident`, ...), defaulting to `"resident"` if
  omitted.

`ROLE_ROUTINES` (in `character.py`) maps every role, ship-flying or not, to
a `Routine` class - the same table, the same lookup, regardless of whether
that routine flies a ship or just moves a body around a room:

| Routine | File | Needs a ship? | Used by |
|---|---|---|---|
| `DockRoutine` | `dock_routine.py` | Yes | `freighter_pilot` - fly to a stop, walk in, talk, walk out, repeat |
| `ShuttleRoutine` | `shuttle_routine.py` | Yes | `trader_captain` - ping-pong stops, instant turnaround |
| `OrbitRoutine` | `orbit_routine.py` | Yes | `patrol_officer` - circle a fixed point forever |
| `IdleRoutine` | `idle_routine.py` | No | default for any role with no entry - never moves |
| `WanderRoutine` | `wander_routine.py` | No | `resident`/`traveler`/`roommate` - amble near spawn |
| `StationaryRoutine` | `stationary_routine.py` | No | `bartender`/`guard`/`ship_salesman`/`loan_officer` - stand still |

Every `Routine` implements the same two methods regardless of which table
row it's in: `start(character)` (once, at construction) and
`run(character)` (every frame). A ship-flying routine calls
`character.engage_seek(...)`/`character.autopilot_active` (delegated to
`character.ship`); a local routine only ever touches `character.person.x/y`
directly - never both, since a `Character` only ever gets one *kind* of
routine (whichever its role maps to).

`Character.update()` runs the routine, then (only if `self.ship` is set)
steps the ship's physics and mirrors `person.x/y` to it - unless
`self.ashore` is `True`, meaning `DockRoutine` currently has the person
walking around a station/moon interior independent of the (parked) ship.

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
- A list of `Character` (autonomous ship-flying entities, loaded from story config)
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
Menu → StorySelector → PilotNameDialog → LocationScreen (station: dormitory)
                                              ↓ (walk the connected-location graph, L)
                            LocationScreen (station: corridor/concourse/spaceport/loan_office) ←→ PauseMenu
                                              ↓ (buy a ship at the spaceport, then L: board) ↓ (save)
                                          SpaceScreen ←→ SaveDialog
                                              ↓ (land: L)
                            LocationScreen (station) ←→ PauseMenu

SpaceScreen → LocationSelector → LocationScreen (moon) ←→ PauseMenu
```
A new pilot never sees `SpaceScreen` at all until they own a ship - see
`main.py`'s `"pilot_name"` handler and `LocationScreen.ship_available`.

**State transitions via return values:**
- `handle_input()` returns an action string
- Main loop (`main.py`) interprets it and transitions `current_screen`
- See [UI_FLOW.md](UI_FLOW.md) for the full diagram and every state

## Extensibility Points

### Adding a New Entity Type
1. Create a class extending `Ship`, `Landable`, or `Person` - or, for a new
   *character*, prefer a new `Routine` (see below) over a new class
2. Override `update()` and/or `draw()`
3. Add to `SpaceScreen` (or a location's NPC list)
4. Include in `get_state()`/`restore_state()` if saveable

### Adding a New Screen
1. Create a class with `handle_input()`, `draw()` (and `update()` if it needs one)
2. Add a `current_screen` string and branch in `main.py`'s loop
3. Implement transitions via `handle_input()` return values

### Adding a New Role/Routine (AI pilot or NPC)
1. Create a `Routine` class (own file, one class per file) with
   `__init__(self, route)`, `start(self, character)`, `run(self, character)`
   - reach through `character.ship`-delegated methods (`engage_seek`, etc.)
   for ship-flying behavior, or `character.person.x/y` directly for local
   (no-ship) behavior - never both in the same routine
2. Register it in `ROLE_ROUTINES` (`game/world/character.py`), keyed by the
   role string
3. Set `"role": "<name>"` on the relevant `pilots.json` entry (ship-flying)
   or the location config's `npcs[]` entry (local) - no other code changes needed

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

**Why an open world instead of screen-wrapping?**
- Ships used to teleport at `GAME_WIDTH`/`GAME_HEIGHT` edges (torus topology); this was
  removed in favor of a genuinely unbounded world
- `StarField`/`AsteroidField` generate their content procedurally per-chunk from a seed
  as the camera approaches, and forget chunks once far behind it — so exploring
  indefinitely keeps finding new stars/asteroids without pre-generating (or wrapping)
  a fixed-size field, and without unbounded memory growth. See PHYSICS.md.

See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) for reusable solutions across the codebase.
