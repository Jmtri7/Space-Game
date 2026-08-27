# Design Patterns & Reusable Solutions

Proven patterns and architectural solutions discovered during development.

## Pattern: Coordinate Conversion

**Problem:** Graphics deform on window resize, objects render at wrong positions.

**Solution:** Separate game-space and screen-space with explicit conversion functions.

**Implementation:**
```python
# Store all positions in game-space (800x600)
self.x, self.y = 400, 300

# Convert only when drawing
def to_screen(x, y):
    scale = get_scale()  # Aspect ratio preserving scale
    offset_x, offset_y = get_offset()  # Letterbox offset
    return (int(round(x * scale + offset_x)), int(round(y * scale + offset_y)))

# In draw()
pygame.draw.circle(surface, color, to_screen(self.x, self.y), radius)
```

**Why this works:**
- Physics operates in stable game-space
- All calculations use same coordinate system
- Resize just recalculates scale/offset
- No coordinate conversion errors

**Use case:** Any game with resizable window.

---

## Pattern: 2D Rotation with Matrix

**Problem:** Rotated polygons deform when using separate sin/cos per point.

**Solution:** Pre-compute cos/sin once, reuse for all vertices.

**Implementation:**
```python
rad = math.radians(angle)
cos_a = math.cos(rad)
sin_a = math.sin(rad)

points = []
for lx, ly in local_points:
    # 2D rotation matrix: [cos -sin] [x]
    #                     [sin  cos] [y]
    rotated_x = lx * cos_a - ly * sin_a
    rotated_y = lx * sin_a + ly * cos_a
    world_x = center_x + rotated_x
    world_y = center_y + rotated_y
    points.append((world_x, world_y))

pygame.draw.polygon(surface, color, points)
```

**Why this works:**
- All points use same rotation matrix (consistent)
- Trig functions computed once (performance)
- Polygon stays rigid under rotation

**Use case:** Any rotating sprite/polygon (ships, objects).

---

## Pattern: Thrust & Momentum

**Problem:** Ship should drift when engines off, not stop instantly.

**Solution:** Separate thrust input from velocity, apply drag each frame.

**Implementation:**
```python
# Input → Thrust (acceleration)
if keys[UP]:
    self.thrust = min(self.thrust + 0.02, max_thrust)
else:
    self.thrust = max(self.thrust - 0.02, 0)

# Thrust → Velocity (persistent)
rad = math.radians(self.angle)
self.velocity_x += math.sin(rad) * self.thrust
self.velocity_y -= math.cos(rad) * self.thrust

# Velocity → Position (with drag)
self.velocity_x *= drag  # 0.98 = 2% friction per frame
self.velocity_y *= drag
self.x += self.velocity_x
self.y += self.velocity_y

# Velocity cap (prevent runaway)
speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)
if speed > max_velocity:
    scale = max_velocity / speed
    self.velocity_x *= scale
    self.velocity_y *= scale
```

**Why this works:**
- Thrust is input (player control)
- Velocity is physics state (persists when thrust ends)
- Drag creates natural deceleration
- Cap prevents unlimited acceleration

**Constants:**
- `max_velocity = 4.0` (units/frame)
- `drag = 0.98` (multiplicative, not additive)
- `max_thrust = 0.3` (acceleration per frame when active)

**Use case:** Any top-down spaceship game.

---

## Pattern: Base Class for Reusable Entity Logic

**Problem:** Multiple entity types (`Ship`, `Landable`) duplicate position/
distance/rotate-and-draw-polygon logic.

**Solution:** Extract shared logic into a base class (`WorldObject`), same
idea as any base class — see `game/world/world_object.py`.

**Use case:** Multiple entity types sharing core *physical-object*
functionality (position, drawing).

---

## Pattern: Compose, Don't Inherit, for "Who Flies It"

**Problem:** The player, AI ship pilots, and station/moon NPCs all need a
walking-around body (`Person`); only some of them also fly a `Ship`. An
earlier version of this game gave AI ships their own `Ship` subclass
(`AIShip(Ship)`) with a `Person` bolted on the side - which put the player
and AI pilots in *opposite* class shapes (`PlayerController` owns a `Ship`;
`AIShip` **is** one), and gave NPCs (no ship at all) no relationship to
either.

**Solution:** Nobody inherits `Ship`. `PlayerController` and `Character`
(`game/world/character.py`) both *compose* one - `self.ship` - alongside a
`self.person` (`Person`), with delegating properties (`x`/`y`/`velocity_x`/
`angle`/`engage_seek()`/...) so the rest of the game can duck-type either
one as a flyable ship without caring which it is. A `Character` with
`ship=None` (any station/moon NPC) is just a body with a role - not a
degenerate case, the normal one.

```python
class Character:
    def __init__(self, person, ship=None, role=None, ...):
        self.person = person
        self.ship = ship            # None for a local NPC
        self.routine = ROLE_ROUTINES.get(role, IdleRoutine)(route)

    @property
    def x(self):
        return self.ship.x          # only ever called when self.ship is set
    # ... same delegating-property set PlayerController already has

    def update(self):
        self.routine.run(self)
        if self.ship:
            self.ship.update()
```

**Why this works:**
- One ownership shape (compose a `Ship`+`Person`) for every character,
  instead of two incompatible ones
- A routine (see the next pattern) never needs to know or check whether its
  `Character` has a ship - it just calls the methods its own kind of
  behavior needs, and a `Character` only ever gets *one* kind of routine
- Adding a new kind of character (a shopkeeper, a second kind of ship) never
  means picking a base class to inherit - just which pieces to compose

**Use case:** Any time two-or-more entity "roles" overlap partially (some
fly, some don't; some have dialogue, some don't) - composition lets each
piece (body, ship, role) vary independently instead of forcing every
combination into its own subclass.

---

## Pattern: Role → Routine Registry

**Problem:** "What does this character do on its own" (fly a route, dock
and walk around, wander a room, stand still) needs to vary by role/job, for
*every* character, not just ship-flying ones - without an `if role ==
"..."` chain re-checked every frame.

**Solution:** A dict from role string to a `Routine` class, all implementing
the same two-method interface, looked up once at construction:

```python
ROLE_ROUTINES = {
    "freighter_pilot": DockRoutine,     # ship-flying
    "patrol_officer": OrbitRoutine,     # ship-flying
    "bartender": StationaryRoutine,     # local, no ship
    "resident": WanderRoutine,          # local, no ship
}

class Character:
    def __init__(self, person, ship=None, role=None, route=None, ...):
        self.routine = ROLE_ROUTINES.get(role, IdleRoutine)(route or [])
        self.routine.start(self)

    def update(self):
        self.routine.run(self)
        ...
```

Every `Routine` (`start(character)`, `run(character)`) lives in its own
file (see `game/world/dock_routine.py`, `wander_routine.py`, etc.) and reads
either `character.ship`'s delegated methods or `character.person.x/y`
directly - never both, since a role only ever maps to one kind.

**Why this works:**
- Adding a new job is data (`"role": "..."` in config) + one small class +
  one registry entry - never a new `if` branch in an existing `update()`
- The exact same mechanism serves AI ship pilots and local NPCs, so a
  future "walks to work then flies home" role isn't a special case, just a
  routine that does both

**Use case:** Any entity whose autonomous behavior should be chosen by a
config-driven category (job, faction, difficulty tier) rather than its
Python class.

---

## Pattern: State Persistence (get_state/restore_state)

**Problem:** Need to save/load game state without tightly coupling persistence logic.

**Solution:** Each entity provides get_state() and restore_state() methods.

**Implementation:**
```python
class SpaceScreen:
    def get_state(self):
        """Capture current state for saving"""
        return {
            "player": {
                "x": self.player.x,
                "y": self.player.y,
                "angle": self.player.angle,
                "velocity_x": self.player.velocity_x,
                "velocity_y": self.player.velocity_y,
                "thrust": self.player.thrust
            },
            "ai_ship": { ... }
        }
    
    def restore_state(self, state):
        """Restore state from save file"""
        if not state:
            return
        if "player" in state:
            p = state["player"]
            self.player.x = p.get("x", self.player.x)
            # ... restore all fields
```

**In save logic:**
```python
create_save_file(pilot_name, save_name, config, game_screen.get_state())
```

**In load logic:**
```python
game_screen = SpaceScreen(config, pilot_name)
game_screen.restore_state(saved_state)
```

**Why this works:**
- Decoupled: Entity doesn't know about files/format
- Extensible: Add new fields without changing save logic
- Graceful: Missing fields use current values
- Debuggable: Save JSON is human-readable

**Use case:** Any game with save/load.

---

## Pattern: Scrollable Menu List

**Problem:** Show 5 items at a time but allow scrolling through unlimited items with visual feedback.

**Solution:** Track scroll_offset separately from selected_index.

**Implementation:**
```python
class ScrollableMenu:
    def __init__(self, items):
        self.items = items
        self.selected = 0
        self.scroll_offset = 0
        self.max_visible = 5
    
    def handle_input(self, events):
        for event in events:
            if event.key == DOWN:
                self.selected += 1
                if self.selected >= len(self.items):
                    self.selected = 0
                    self.scroll_offset = 0
                elif self.selected >= self.scroll_offset + self.max_visible:
                    self.scroll_offset += 1
            elif event.key == UP:
                self.selected -= 1
                if self.selected < 0:
                    self.selected = len(self.items) - 1
                    self.scroll_offset = max(0, len(self.items) - self.max_visible)
                elif self.selected < self.scroll_offset:
                    self.scroll_offset -= 1
    
    def draw(self, surface):
        # Show scroll indicator if not at top
        if self.scroll_offset > 0:
            draw_text(surface, "^ more")
        
        # Show visible items
        visible = self.items[self.scroll_offset:self.scroll_offset + self.max_visible]
        for i, item in enumerate(visible):
            is_selected = (self.scroll_offset + i == self.selected)
            draw_text(surface, item, highlight=is_selected)
        
        # Show scroll indicator if not at bottom
        if self.scroll_offset + self.max_visible < len(self.items):
            draw_text(surface, "v more")
```

**Why this works:**
- `scroll_offset`: What part of list to show (scrolling window)
- `selected`: Which item is highlighted (independent)
- Sync check: Adjusts scroll when selection moves outside window
- Wrapping: Selection loops at boundaries

**Use case:** Menus/lists that might exceed visible area.

---

## Pattern: Scrollable List Handler (Shared Logic)

**Problem:** The save and load screens both duplicate up/down navigation with wrapping and scroll-sync.

**Solution:** Extract to a pure function that returns (new_selected, new_scroll_offset).

**Implementation:**
```python
def _handle_scrolling_input(key, selected, items, scroll_offset, max_visible):
    """Handle up/down navigation with wrapping and auto-scroll."""
    if key in (pygame.K_UP, pygame.K_w):
        selected -= 1
        if selected < 0:
            selected = len(items) - 1
            scroll_offset = max(0, len(items) - max_visible)
        elif selected < scroll_offset:
            scroll_offset -= 1
    elif key in (pygame.K_DOWN, pygame.K_s):
        selected += 1
        if selected >= len(items):
            selected = 0
            scroll_offset = 0
        elif selected >= scroll_offset + max_visible:
            scroll_offset += 1
    return selected, scroll_offset

# SelectableList.handle_key() calls it; SaveBrowser (both modes) and
# ChoiceDialog's old list form all went through SelectableList.
self.selected, self.scroll_offset = _handle_scrolling_input(
    event.key, self.selected, self.items, self.scroll_offset, self.max_visible)
```

**Why this works:**
- Pure function (no side effects, testable in isolation)
- Reusable everywhere a list scrolls, via `SelectableList` (DRY)
- Single place to fix boundary/wrapping bugs
- Easy to add new key bindings (modify function signature once)

**Use case:** Multiple menus/lists that all need identical scrolling behavior.

---

## Pattern: 2D Grid Sibling to a Scrollable List

**Problem:** ShopMenu's buy/sell lists needed to read as a grid of icons
(name/price/quantity per cell) rather than one item per line, but
`SelectableList`'s navigation is 1D (up/down only) and its `draw()` assumes
a single column of text.

**Solution:** Rather than bolting grid support onto `SelectableList`, add a
sibling class (`IconGrid`, `game/ui/icon_grid.py`) with the same
`items`/`selected`/`current()` shape, but `handle_key()` understands
Left/Right (step through row-major order, wrapping) and Up/Down (jump a
full row, clamping - not wrapping - on a ragged last row). `draw()` stays
layout-only: it hands each cell's `pygame.Rect` to a caller-supplied
`cell_draw_fn(surface, rect, item, is_selected, reason)` instead of
rendering text itself, so the grid has no opinion about icons/fonts/colors.

**Why this works:**
- Same mental model as `SelectableList` (selection + scroll state, a
  `disabled_fn`/`reason` contract) so callers familiar with one can read
  the other, without forcing 1D and 2D navigation into one class's
  `handle_key()`.
- `cell_draw_fn` keeps `IconGrid` reusable for any grid content (it doesn't
  know what a "cell" looks like) the same way `_handle_scrolling_input`
  stays reusable by not knowing what a "row" looks like.

**Use case:** Any menu where content reads better as a 2D grid (icons,
thumbnails, a shop shelf) than a single vertical list - see `ShopMenu`,
`OutfittingMenu`'s Buy tab, and `ShipBrowserMenu`'s ship grid. All three
share one `cell_draw_fn` implementation too - `ui_theme.draw_shop_cell`
(highlight + icon + name + price/quantity, with a disabled `reason` always
left visible alongside the price rather than replacing it) - so each menu's
own `_draw_cell` only has to supply an `icon_fn` (a procedural item glyph,
or a static ship silhouette) and the name/detail strings.

---

## Pattern: Screen State Machine

**Problem:** Complex navigation between multiple screens (menu, game, pause, load, etc.).

**Solution:** Main loop interprets action strings to manage state transitions.

**Implementation:**
```python
current_screen = "menu"
menu = Menu()

while running:
    events = pygame.event.get()
    
    if current_screen == "menu":
        action = menu.handle_input(events)
        if action == "new":
            game_screen = SpaceScreen()
            current_screen = "game"
        elif action == "load":
            load_menu = SaveBrowser("load")
            current_screen = "load"
    
    elif current_screen == "game":
        action = game_screen.handle_input(events)
        if action == "pause":
            current_screen = "pause"
        game_screen.update()
        game_screen.draw(screen)
    
    elif current_screen == "pause":
        action = pause_menu.handle_input(events)
        if action == "resume":
            current_screen = previous_screen
        # ... draw
```

**Why this works:**
- Centralized state management
- Clear transitions (action string → new state)
- Easy to add screens (new elif branch)
- Separates input handling from state logic

**Use case:** Menu-driven games with multiple screens.

> **Note:** the real loop in `main.py` splits each iteration into three
> phases — input/transitions, then a fixed-timestep simulation, then render
> (see the next pattern). Input and render still branch on `current_screen`
> the way shown above; only simulation is consolidated.

---

## Pattern: Fixed-Timestep Accumulator (decouple sim from render)

**Problem:** When the loop does exactly one `update()` + one `draw()` per
iteration and every constant is "per frame", a slow frame slows the
*simulation* down — ships coast less far, timers run long in wall-clock,
autopilot integrates differently. The game is frame-rate dependent.

**Solution:** Keep a running `accumulator` of real elapsed seconds. Each
frame, drain it in fixed `SIM_STEP`-sized chunks, running the simulation
once per chunk; render once per frame regardless.

**Implementation** (`game/utils.py` `advance_accumulator()`, `main.py`
`step_world()`):
```python
accumulator, n_steps = advance_accumulator(accumulator, real_dt_seconds)
for _ in range(n_steps):
    step_world(...)   # ONE fixed 1/60 s step of the whole simulation
render(...)           # once, paints the latest state
```
`advance_accumulator` clamps `real_dt` (hitch protection) and caps `n_steps`
(spiral-of-death protection), and is pure — no clock, no globals — so the
step arithmetic is unit-testable on its own.

**Keep `SIM_STEP` fixed (here: exactly 1/60 s).** The constants are already
calibrated to that step, so at a held frame rate `n_steps == 1` every frame
and the result is byte-identical to the old loop. It only diverges when the
machine can't keep up, running catch-up steps so the sim stays correct while
rendering gets choppy.

**One simulation entry point.** All per-step work (physics, AI, background
locations, countdown timers) goes through a single `step_world()` so it's
trivially called N times; input and rendering stay once per frame in their
own phases. Screens that freeze the world are a no-op in `step_world()`.

**Why this works:**
- Deterministic: fixed step ⇒ headless tests and the live game integrate identically
- No per-constant `* dt` rewrite, and no autopilot-prediction divergence
- Robustness-only change: zero gameplay difference at the target frame rate

**Not included:** render interpolation (storing prev+curr state and lerping
at draw time). That's a separate, optional smoothness feature — the
accumulator alone doesn't make motion smoother at >60 Hz.

**Use case:** Any real-time loop with "per frame" constants that must behave
the same on slow and fast machines.

---

## Pattern: Always-On Metrics, Gated Display

**Problem:** Per-frame performance regressions ("this looks fine on my
machine") slip in because nothing measures where a frame's time goes, and
bolting on measurement only when investigating means there's no before/after
baseline.

**Solution:** Measure unconditionally into a cheap rolling-window store; gate
only the *display* on a debug flag.

**Implementation** (`game/perf_metrics.py`, a shared instance like
`utils.Camera`):
```python
from game.perf_metrics import metrics as perf

# main loop: time each phase, hand the numbers over every frame
perf.record({"input": ..., "sim": ..., "render": ..., "present": ...}, n_steps, fps)

# any hot sub-section, at its call site:
with perf.span("render.starfield"):
    self.star_field.draw(surface)

# once per frame, after the active screen draws:
perf_metrics.draw_overlay(screen)   # no-op unless constants.DEBUG_MODE
```
`record()` is deque appends; `span()` is two `perf_counter()` calls — cheap
enough that there's no reason to conditionalise them, and "always recording"
means the panel is instantly useful the moment you toggle debug, mid-session,
with history already populated.

**Keys are namespaced by phase** (`render.*`, `sim.*`) and kept
non-overlapping so a phase's spans sum to something meaningful; a span that
doesn't fire a given frame records `0.0` so its average decays honestly
instead of freezing.

**Use case:** Any always-running subsystem whose cost you want visible on
demand — frame timing, allocation counts, entity counts, network round-trips.

---

## Pattern: Data-Driven Configuration

**Problem:** Game content (buildings, terrain features, NPC positions) hardcoded in classes makes it hard to iterate on level design, impossible to load from save files, and requires code changes for every content update.

**Solution:** Load all location content from JSON config files. Classes become generic containers that populate themselves from data.

**Implementation:**
```python
# config/moon_city.json
{
  "buildings": [
    {"x": 200, "y": 100, "width": 200, "height": 250, "color": [150, 150, 150]},
    {"x": 600, "y": 80, "width": 250, "height": 280, "color": [100, 100, 100]}
  ],
  "windows": [
    {"start_x": 200, "start_y": 100, "end_x": 400, "end_y": 350, "spacing": 40}
  ]
}

# In MoonCity class
class MoonCity(WalkableArea):
    def __init__(self, config=None, pilot_name=""):
        super().__init__(...)
        self.city_config = config or load_json("config/moon_city.json") or {}
        self.buildings = self.city_config.get("buildings", [])
        self.windows = self.city_config.get("windows", [])

    def draw(self, surface):
        # Draw buildings from config
        for building in self.buildings:
            bx, by, bw, bh = building["x"], building["y"], building["width"], building["height"]
            color = tuple(building.get("color", [150, 150, 150]))
            # ... draw using config data
```

**Save/Load Integration:**
```python
# When saving game
save_data = {
    "city_config": self.city_config,
    "wilderness_config": self.wilderness_config,
    ...
}

# When loading game
moon_city = MoonCity(config=save_data["city_config"], pilot_name=pilot_name)
```

**Why this works:**
- Content designers can edit JSON without touching code
- Entire locations reproducible from save files
- New locations created by writing JSON, not new classes
- Easy A/B testing (swap config files)
- Version control tracks content changes separately from code

**Benefits:**
- Separation of concerns: code handles logic, JSON holds data
- Faster iteration: change building position in JSON, reload
- Mod-friendly: players can customize content via JSON files
- Debuggable: `load_json("config/debug_map.json")` for testing

**Use case:** Any game with level layouts, NPC positions, environmental objects, or tunable parameters.

---

## Pattern: Y-Sorted Draw Order (Painter's Algorithm)

**Problem:** In a top-down view where some objects have real height (buildings,
structures) and others walk around among them (NPCs, the player), drawing them
in separate fixed layers (all structures, then all people) is wrong whenever
one has to occlude the other - a person "in front of" a tall structure should
draw on top of it, and one "behind" it should draw underneath, but a fixed
layer order can only ever pick one of those, globally, for every position.

**Solution:** Collect everything that has height into one list, each paired
with its own ground-level depth (typically a person's feet position, or a
structure's base/front edge - not its center or top), sort that list by
depth, and draw in that order every frame. Purely flat/ground-level things
(floor tiles, wall decals, room labels) don't need this - they never occlude
anyone and can stay in their own earlier, unsorted pass.

**Implementation:** (`LocationScreen.draw()`, `_structure_depth()`)
```python
def _structure_depth(self, structure):
    # ... return the structure's own base/front-edge y, not its top or center

def draw(self, surface):
    # flat/ground layers first (floor, wall decals) - never need sorting
    drawables = [(self._structure_depth(s), self._make_structure_drawer(s, scale)) for s in self.structures]
    drawables += [(character.person.y, character.person.draw) for character in self.npcs]
    drawables.append((self.player.y, self.player.draw))
    drawables.sort(key=lambda item: item[0])
    for _, draw_fn in drawables:
        draw_fn(surface)
```

**Why this works:**
- One sort replaces having to special-case every pairwise "is A in front of
  B?" relationship
- Depth key is just "how close to the camera" (larger y = closer, in a
  standard top-down screen-space y-axis) - the same idea `get_distance()`
  already uses for proximity checks, just applied to draw order instead
- Rebuilt fresh every frame from current positions, so it's automatically
  correct as things move - no manual re-layering needed

**Benefits:**
- Correct occlusion for any layout, without hand-authoring z-order per object
- New tall structure types (or new character types) just need a depth key,
  not a new fixed layer to slot into the right place by hand

**Use case:** Any 2D top-down scene mixing static tall scenery with moving
characters - the same idea generalizes to any renderer with a fixed camera
angle and objects of varying height (isometric games use exactly this,
usually called Y-sorting).

---

## Pattern: Walkability-Oracle Navigation

**Problem:** AI needs to walk a body from A to B across an area whose shape is
arbitrary (concave rooms, overlapping polygons, buildings sitting in the
middle). Walking straight and wall-sliding strands the walker whenever the
direct line leaves the walkable area. Encoding the geometry a second time for
the pathfinder (room-adjacency graphs, visibility graphs over obstacle
corners) means two representations that drift apart, and it can't handle
concave shapes without a full navmesh.

**Solution:** There's already one authority on "can a body be here?" - the
same predicate the player's own movement uses (`LocationScreen.can_move_to`,
folding in room polygons + building footprints). Rasterize *that* into a grid
once (`NavGrid`: every cell centre walkable or not), A* over the grid, then
string-pull the cell staircase back to real corners by dropping any waypoint
whose bypass segment is still fully walkable (sampled through the same
predicate). Concave rooms, overlaps, and obstacles are all just "cell not
walkable" - no special cases, and the pathfinder can never disagree with
movement because they share the oracle.

**Implementation:** `game/world/indoor_pathfinder.py` (`NavGrid`,
`IndoorPathfinder`), `LocationScreen.plan_path()` (builds + caches one grid
per interior - the walkable area never changes during play), consumed by
`DockRoutine._set_waypoints`. Callers keep wall-sliding each leg as the
safety net for the `[goal]` fallback `plan_path` returns when the goal isn't
walkable or no route exists.

**Benefits:** one geometry representation; concave-safe; a cheap bbox reject
in `can_move_to` keeps the one-time grid build well under a frame.

**Use case:** any grid-or-continuous space where "is this point valid?" is
already cheap to answer and you'd rather not maintain a parallel nav
structure.

---

## Pattern: Config-Driven Screen Dispatch ("shop" NPCs)

**Problem:** Several different screen classes need to open from the same
trigger (talking to an NPC), where which class opens depends on what that
NPC is configured to do - a ship salesman needs a ship browser, a
quartermaster needs a commodities list, an outfitter needs a slot diagram.
Hardcoding "if this NPC's name is X, open Y" doesn't scale, and cramming
every case into one mega-menu class fights each screen's very different
layout needs.

**Solution:** Give the NPC config one key naming *what kind* of interaction
this is (`"shop": {"type": "commodities"|"items"|"ships"|"outfits", ...}`),
checked before falling back to the default interaction (`Dialogue`). A
single small dispatcher function picks the concrete screen class from that
`type`, so the call site (the input handler that reacts to "talk to this
NPC") never needs to know the full set of possible screens - only that
"shop config present" means "ask the dispatcher."

**Implementation:** (`LocationScreen._build_local_character`, `handle_input`;
`main.py`'s `build_shop_menu`)
```python
# NPC config: a "shop" key instead of (or alongside) a dialogue_tree
{"name": "Reeve Katic", "role": "outfitter",
 "shop": {"type": "outfits", "stock": ["laser_cannon", "afterburner"]}}

# Attached to the NPC's Person at build time, like dialogue is:
person.shop = cfg.get("shop")

# Checked first when the player interacts (T) - shop bypasses Dialogue
# entirely rather than being folded into it:
if target_npc.shop:
    self.active_shop = target_npc.shop
    return "shop"

# One dispatcher picks the concrete screen class by "type":
def build_shop_menu(possessions, story, shop_config, cargo_capacity, buy_ship_fn, on_outfits_changed):
    shop_type = shop_config.get("type")
    if shop_type == "ships":
        return ShipBrowserMenu(possessions, story, shop_config, on_buy=buy_ship_fn)
    if shop_type == "outfits":
        ship_type_id = possessions.owned_ships[-1] if possessions.owned_ships else None
        return OutfittingMenu(possessions, story, shop_config, ship_type_id, on_outfits_changed=on_outfits_changed)
    return ShopMenu(possessions, story, shop_config, cargo_capacity=cargo_capacity)
```

**Why this works:**
- The NPC config only declares *intent* ("I sell outfits"), not *how* to
  render that - the dispatcher owns the type→class mapping in one place, so
  adding a fifth shop type later is a one-line addition there, not a change
  scattered across every place an NPC can be talked to.
- Every resulting screen still shares the same underlying UI building
  blocks (`SelectableList`, `ui_theme`'s panel/title helpers, `ConfirmDialog`)
  even though each is its own class - config-driven dispatch picks the
  *class*, it doesn't force one mega-class with an internal mode switch for
  every possible shape of shop.
- Matches the "Role → Routine Registry" pattern above (a config string key
  looked up in a small mapping to pick behavior) applied one layer up, to
  picking a screen instead of a routine.

**Use case:** Any place a single trigger (NPC interaction, a world object,
a menu option) needs to open one of several purpose-built screens depending
on config, without the trigger's own code needing to know about all of them.

---

## Pattern: HUD Zone Width Discipline

**Problem:** A HUD panel that sizes itself purely from its own content
(`draw_status_pane`, `draw_info_panel`, the bottom-left Messages log, a
top-center banner) can grow arbitrarily wide once that content is free-form
text - a long status sentence, an NPC's one-way hail message, a story
config's interior label. `get_ui_scale()` doesn't prevent this either: it's
`min(width/800, height/600)`, so a wide-but-short window is scaled by
*height*, not width - text renders proportionally larger than the window is
wide, and a panel that was comfortably narrow at a normal aspect ratio can
overflow into a neighboring panel's space at an unusual one (a real bug: a
long "drifting from the system" status line overlapping the Messages pane
at the bottom-left on a 1859x1024 window).

**Solution:** Divide the HUD horizontally into three zones - a left
quarter, a right quarter, and a center band - and give every panel a hard
cap matching whichever zone it's anchored to, derived from the *real*
window width rather than `ui_scale`. Edge-anchored panes take a *fixed*
`side_panel_width()` (the quarter minus the shared `hud_margin()`), so they
all line up on the quarter line rather than each shrinking to its own
content. Centered panes (status pane, the top-centre popup stack, modal
menu panels via `modal_panel_rect()`) cap at `center_panel_max_width()`,
which is `screen//2 - 2*hud_margin()` - so at max width a centred pane
still leaves a full `hud_margin()` gap before the quarter line, the same
gap the side panes leave from the screen edge. Nothing centred can touch a
side pane. Any free-form text wraps (`_wrap_text`) to fit its zone.

**Implementation:** (`game/ui/ui_theme.py`)
```python
def side_panel_max_width():
    return utils.screen_width // 4

def hud_margin(ui_scale):
    return int(HUD_MARGIN_BASE * ui_scale)

# Edge-anchored: fill the quarter from the edge margin to the quarter line.
def side_panel_width(ui_scale):
    return max(1, side_panel_max_width() - hud_margin(ui_scale))

# Centred: a full margin's gap from the quarter line on each side.
def center_panel_max_width(ui_scale):
    return max(1, utils.screen_width // 2 - 2 * hud_margin(ui_scale))

# Modal menu panels re-centre on the real screen and cap at the centre band.
def modal_panel_rect(ui_scale, y_frac, w_frac, h_frac):
    width = min(int(800 * ui_scale * w_frac), center_panel_max_width(ui_scale))
    ...

def draw_controls_pane(surface, x, y, title, items, ui_scale):
    ...
    panel_width = side_panel_width(ui_scale)   # not "shrink to content"
```

**Why this works:**
- One pair of functions defines what "side" and "center" mean in pixels;
  every panel - `draw_status_pane`, `draw_info_panel`, `draw_message_log`,
  `draw_controls_pane`, `draw_glow_message`, `SpaceScreen._draw_minimap` -
  reads from the same two numbers, so the zones can never drift out of
  sync with each other the way five independently-tuned pixel budgets
  would.
- Every edge-anchored pane is a fixed `side_panel_width()` (the quarter
  minus the shared `hud_margin()`), not sized to its own content, so the
  Controls / info / Messages / minimap panes all share one vertical edge on
  the quarter line instead of each stopping at a different ragged width.
- The bottom-left Message Log and the top-right info/targeting pane both
  additionally have a fixed *height* cap (`MESSAGE_LOG_VISIBLE_LINES` /
  `INFO_PANEL_VISIBLE_LINES`) and mouse-wheel scrolling for the overflow
  (`SpaceScreen.message_log_scroll` / `info_panel_scroll`, wheel routed to
  whichever pane the cursor is over), with blue `^`/`v` `(scroll)` hints -
  so neither can grow into the pane above/below it.
- The top-centre transient popups (hail banner, "too close to jump"
  warning, mission/jump toast) render as a downward stack of individual
  `draw_glow_message` panes, so two showing at once never overlap.
- Derived from `utils.screen_width` directly (not `ui_scale`), so the cap
  tracks the window's actual shape instead of a scale factor that can grow
  disproportionately to width on an unusual aspect ratio.
- Shared functions mean `LocationScreen`'s HUD (which reuses
  `draw_controls_pane`/`draw_status_pane`/`draw_info_panel`) gets the same
  discipline for free, without its own screen needing to know the rule
  exists.

**Use case:** Any HUD panel anchored to a screen edge or the horizontal
center, especially one whose content can include story/dialogue text
rather than only fixed, short UI labels.

---

## Pattern: Menu vs. Dialog (`MenuBase` / `DialogBase`)

**Problem:** Every full-screen modal in `game/ui/` re-implemented its own
"chrome" - some drew a top-left Controls pane (`draw_controls_pane`), some a
help line inside their panel, `LocationSelector` drew nothing, `ExitMenu` (a
one-shot picker) drew a full Controls pane like a dwelling menu. Nothing
enforced a consistent rule, and there were four pairs of near-duplicate
classes (`Menu`/`StorySelector`, `LocationSelector`/`ExitMenu`,
`PossessionsMenu`/`MissionLog`, `LoadMenu`/`SaveDialog`).

**Solution:** No modal draws a Controls pane (that pane is the in-world HUD's
alone). Every modal presents its actions as `ui_theme.draw_button` widgets
inside its own panel, mouse- and keyboard-driven. Two base classes:

- **`MenuBase`** (`game/ui/menu_base.py`) - a **menu** you *dwell in*;
  navigating/acting doesn't close it. Owns all the button infrastructure:
  `buttons()` → `[(id, label, accent, disabled), ...]`, `button_bar_rects()`
  → where they go (default: a centred row along the panel bottom; a corner
  Close menu overrides it), `panel_rect()` → the glass panel so the default
  bar and the dim `hint_text()` line can anchor. `draw()` is a template
  method (content → `active_popup()` if a sub-dialog is up → buttons + hint).
  `handle_button_event()` does arrows/Tab/Enter/hover/click; the keyboard
  path builds no geometry (testable without real pygame). `handle_button_
  click()` is the mouse-only variant for grid menus where Enter drives the
  grid, not the button.
- **`DialogBase(MenuBase)`** - a **dialog** shown *over* another modal that
  closes as soon as you pick one of its `buttons()`. Adds nothing but
  `is_dialog = True` and the "picking closes" semantics.

**Why this works:**
- One `draw()` template + one button-input path, not 15 copies of chrome.
- Classifying by *persistence* resolves the awkward cases: `SaveBrowser`
  stays open through delete/scroll/mode-switch → menu; `ChoiceDialog`
  pick-and-go → dialog.
- One widget per shape instead of per screen: `BackdropMenu(title, rows,
  seed, allow_cancel)` covers the main menu and story picker;
  `ChoiceDialog(title, options)` covers moon-landing and exit-door picking;
  `ReportMenu(title, columns, hotkey, hotkey_label)` + a builder fn covers
  the possessions and mission read-outs; `SaveBrowser(mode)` covers load and
  save. `main.py` builds the data, the widget doesn't know the domain.

**Use case:** Any new full-screen modal - decide menu vs. dialog by "can you
navigate inside it without it closing?", subclass the matching base, provide
`buttons()` + `panel_rect()`, and the chrome is handled. Reach for an
existing widget (`BackdropMenu`, `ChoiceDialog`, `ReportMenu`) first.

---

## Contributing Patterns

When you discover a reusable solution:

1. **Recognize the pattern:** Notice repeated code or design that could generalize
2. **Name it:** Pick a short, descriptive name (e.g., "Coordinate Conversion")
3. **Document here:** Add section with:
   - Problem (what issue it solves)
   - Solution (how to implement)
   - Implementation (code example)
   - Why this works (explanation)
   - Use case (when to apply it)
4. **Link from relevant docs:** Update other docs (ARCHITECTURE.md, etc.) to reference the pattern

**Example:**
When fixing a bug or implementing a feature, if you notice:
- Code being repeated in multiple classes
- A general solution that other code might need
- A design decision that took thought and worked well

...document it as a pattern so future code can reuse the solution.

See [README.md](README.md#for-agents-pattern-recognition--contribution) for the contribution workflow.
