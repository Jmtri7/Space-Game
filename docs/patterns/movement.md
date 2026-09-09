# Patterns: Movement, the Sim Loop & Navigation

Thrust/momentum, the fixed-timestep accumulator, always-on metrics, and the two
on-foot navigation patterns. Hub + working principles:
[DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md).

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
step arithmetic is unit-testable on its own. Feed it a `time.perf_counter()`
delta, not the frame limiter's whole-millisecond return — that quantization
alone is enough to cost the sim a step and stutter a pan.

**Keep `SIM_STEP` fixed (here: exactly 1/60 s).** The constants are
calibrated to that step, so at a held frame rate `n_steps == 1` every frame.

**Snap to one step, don't `floor`.** A textbook `floor(accumulator / step)`
emits a 0-step frame next to a 2-step frame under ordinary frame-time jitter,
and a "60 Hz" display that's really 59.94 makes that happen every ~20 s
(60 sim steps/s vs 59.94 frames/s — the surplus has to surface somewhere).
A 2-step frame is a visible lurch on a camera pan. Instead, run *exactly one*
step for any frame worth ~0.5–2.5 steps; multi-step catch-up only on a
sustained slowdown. The trade: a persistent sub-step surplus is dropped
rather than caught up, so the sim tracks the *display* rate not the wall
clock (< 0.1% drift). Fine for a single-player game where every timer is
frame-count based and there's no netcode; revisit if either changes.

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

## Pattern: One Movement Primitive on the Base Entity

**Problem:** Three different callers move a body on foot through an interior -
the player (input-driven), wandering NPCs (`WanderRoutine`), and dock-errand
pilots (`DockRoutine`, following pathfinder waypoints). Each had its own
step-and-slide loop. Two were copy-pasted; the player's was a worse variant
(no wall-slide - stopped dead against an angled wall - and full speed on each
axis, so diagonals were 1.41x faster). Fixing a movement bug meant finding and
fixing it in up to three places, and "how a person walks" wasn't actually one
thing.

**Solution:** Put the primitive on the base class every mover already shares
(`Person`): `step_toward(target_x, target_y, speed, can_move_to) -> bool`.
It normalizes the step, caps it at the distance to the target (no overshoot),
and wall-slides (full step, then x-only, then y-only) against the supplied
`can_move_to` oracle. Every caller reduces to *computing a target and a speed*
and calling it:

- `WanderRoutine` / `DockRoutine`: `person.step_toward(tx, ty, speed, can_move_to)`,
  using the return value to know when to re-plan (blocked → repick / restring).
- The player: `LocationScreen._handle_movement` turns the held direction keys
  into a target one step away and calls the same method - so the player now
  wall-slides and has speed-correct diagonals too, for free.

**Implementation:** `Person.step_toward` (`game/world/person.py`), consumed by
`LocationScreen._handle_movement`, `WanderRoutine.run`, `DockRoutine._step_toward`.
Pace: `LocationScreen.speed` (story.json `walking_speed`); `WanderRoutine` keeps
its own slower `WANDER_SPEED`.

**Benefits:** one place to fix a movement bug; the player inherits the good
behaviour instead of a hand-rolled subset; "walking" is genuinely one concept.

**Use case:** any behaviour that several entity kinds do slightly differently
because it was written separately each time - if they share a base class, that's
where the canonical version goes (see also "Base Class for Reusable Entity
Logic" in [entities.md](entities.md)).
