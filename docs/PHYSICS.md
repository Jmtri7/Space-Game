# Physics & Coordinate System

Core physics simulation and critical coordinate system understanding.

## Coordinate System (Critical!)

**Game Space:** `GAME_WIDTH` x `GAME_HEIGHT` (2400x1800, logical, never changes) is the
camera's reference viewport size — not a hard boundary. The world itself is open and
unbounded: ships can fly arbitrarily far in any direction with no edge, no wrap.
- All entity positions and velocities stored here
- All game logic operates here
- Station/moon/central star are placed within this nominal area (as fractions of it),
  but nothing stops a ship from flying past it

**Screen Space:** Variable (scales with window)
- Only used for rendering
- Computed on-the-fly via `to_screen()` functions
- Never store screen-space coordinates

### Conversion Functions

```python
def get_scale():
    # Aspect ratio maintained, letterboxed if needed
    return min(screen_width / GAME_WIDTH, screen_height / GAME_HEIGHT)

def get_offset():
    # Center game-space on screen
    scale = get_scale()
    offset_x = (screen_width - GAME_WIDTH * scale) / 2
    offset_y = (screen_height - GAME_HEIGHT * scale) / 2
    return (offset_x, offset_y)

def to_screen(x, y):
    # Convert game-space (x,y) to a pixel on the world-render surface.
    # Ends in floor(... + camera sub-pixel remainder) + WORLD_MARGIN, not
    # round(...) - see "Frame Timing & Smooth Motion #2" for why.
    scale = get_scale()
    offset_x, offset_y = get_offset()
    fx, fy = subpixel()
    return (math.floor(x * scale + offset_x + fx) + WORLD_MARGIN,
            math.floor(y * scale + offset_y + fy) + WORLD_MARGIN)
```

**Common Mistakes:**
- ❌ Storing positions in screen-space (breaks on resize)
- ❌ Using screen coordinates in physics calculations
- ❌ Forgetting to convert when drawing

**Correct Pattern:**
```python
# Update in game-space
self.x += self.velocity_x
self.y += self.velocity_y

# Draw in screen-space
pygame.draw.circle(surface, color, to_screen(self.x, self.y), radius)
```

## Movement & Velocity

### Thrust System
```python
# Thrust increases when key pressed, decays when released
if keys[UP_KEY]:
    self.thrust = min(self.thrust + 0.02, max_thrust)  # Accelerate
else:
    self.thrust = max(self.thrust - 0.02, 0)  # Coast down

# Thrust applies force in direction ship is facing
rad = math.radians(self.angle)
self.velocity_x += math.sin(rad) * self.thrust
self.velocity_y -= math.cos(rad) * self.thrust
```

**Key behaviors:**
- Thrust OFF: velocity decays via drag (coasting)
- Thrust ON: acceleration in facing direction
- DOWN key: only decreases thrust, doesn't reverse (inertia)

### Velocity Capping
```python
# After applying thrust, clamp to max speed
speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)
if speed > max_velocity:
    scale = max_velocity / speed
    self.velocity_x *= scale
    self.velocity_y *= scale
```

**Why clamp?** Prevents unlimited acceleration when thrust is applied every frame.

### Drag (Friction)
```python
self.velocity_x *= drag  # 0.98 = 2% loss per frame
self.velocity_y *= drag
```

**Result:** Ship gradually slows down when thrust is off, creating drifting feel.

**Constants:**
- `max_velocity = 4.0` units/frame
- `drag = 0.98`
- `max_thrust = 0.3`
- `rotation_speed = 5` degrees/frame

> **"per frame" = "per simulation step".** The main loop runs a fixed-timestep
> accumulator (`SIM_STEP = 1/60 s`, see [UI_FLOW.md](UI_FLOW.md#main-loop-fixed-timestep-three-phases)):
> `step_world()` runs once per rendered frame on a machine holding ~60 FPS,
> and multi-steps only to catch up on a sustained slowdown (it deliberately
> holds at one step through normal jitter — see "Frame Timing & Smooth
> Motion" below). Every constant here is calibrated to that 1/60 s step and
> must not be converted to per-second — `SIM_STEP` is fixed precisely so they
> don't need to be.

## Rotation & Facing Direction

### 2D Rotation Matrix
When drawing a rotated polygon, use proper 2D rotation:

```python
rad = math.radians(angle)
cos_a = math.cos(rad)
sin_a = math.sin(rad)

for lx, ly in local_points:
    rotated_x = lx * cos_a - ly * sin_a
    rotated_y = lx * sin_a + ly * cos_a
    world_x = center_x + rotated_x
    world_y = center_y + rotated_y
```

**Common Mistake:** Using separate sin/cos for each point causes polygon deformation.

### Thrust Flame Direction
Flame shoots opposite to ship facing:

```python
# Find back center of ship polygon
mid_back_x = (left_back_x + right_back_x) / 2
mid_back_y = (left_back_y + right_back_y) / 2

# Rotate back point to world space
back_x = self.x + (mid_back_x * cos_a - mid_back_y * sin_a)
back_y = self.y + (mid_back_x * sin_a + mid_back_y * cos_a)

# Extend flame in opposite direction
flame_length = self.thrust * 30
flame_x = back_x - sin_a * flame_length
flame_y = back_y + cos_a * flame_length
```

## Collision & Boundary Detection

### No World Boundary — Chunk-Streamed Background Instead
There used to be a `wrap_position()` that teleported ships back to the opposite edge at
`GAME_WIDTH`/`GAME_HEIGHT` (torus topology). That's gone — ships now fly freely with no
boundary at all. To still give the player something to see arbitrarily far from the
start, `StarField` and `AsteroidField` (`starfield.py`/`asteroid_field.py`) generate
their content procedurally instead of pre-placing it. Each frame, the visible chunk
range is computed from the camera position (`utils.camera_offset_x/y`) plus a margin;
any chunk not yet generated is generated on the spot, and any chunk far enough behind
the camera is dropped. This keeps memory bounded while letting the player explore
indefinitely in any direction.

The two fields differ deliberately in *how* a chunk gets (re)generated:

```python
# StarField: deterministic per-chunk hash - same (seed, cx, cy) always
# regenerates the same stars, so backtracking looks consistent.
def _chunk_seed(self, cx, cy):
    return (self.seed * 73856093) ^ (cx * 19349663) ^ (cy * 83492791)

# AsteroidField: one random.Random advances continuously across every
# chunk it ever generates (never reseeded by position), so a chunk that
# gets unloaded and later revisited rolls fresh asteroids instead of
# replaying the same ones - asteroids are meant to feel different each
# time you come back, stars aren't.
```

**Why chunk-and-forget instead of one big pre-generated field?** A fixed field either
has to be huge (wasteful, and still finite) or small (visibly runs out). Generating
per-chunk on approach means there's no upper bound on how far the player can go.

### Range Checking
```python
def get_distance(self, x, y):
    dx = self.x - x
    dy = self.y - y
    return math.sqrt(dx**2 + dy**2)

# Use for interaction checks
if player.get_distance(station.x, station.y) < 100:
    show_land_prompt()
```

### Collision Areas (Station Interior)
A culture-tagged interior's walkable area is the **union of its room
polygons** (`LocationScreen.rooms`, from the interior's `"rooms"` config;
`normalize_room` folds `"rect"` / `"polygon"` / `"circle"` shapes to one
polygon form). Overlapping polygons read as one connected space, so a wide
corridor is just another polygon overlapping the rooms it joins. Movement is
allowed anywhere in that union, with a cheap bounding-box reject before the
per-vertex ray cast:
```python
def can_move_to(self, x, y):
    if any(fx <= x <= fx+fw and fy <= y <= fy+fh for fx,fy,fw,fh in self.building_footprints):
        return False
    if self.rooms:
        return any(bx0 <= x <= bx1 and by0 <= y <= by1 and point_in_polygon(x, y, room["polygon"])
                   for room in self.rooms for (bx0, by0, bx1, by1) in [room["bounds"]])
    return 0 < x < self.world_width and 0 < y < self.world_height
```
`point_in_polygon` is an even-odd ray cast (concave-safe) that counts a point
on any edge as inside. An interior with no `"rooms"` falls back to the full
world rect. AI walking (`DockRoutine`) uses `plan_path()` - a grid A* over
this same `can_move_to` (see ARCHITECTURE.md's "Walkability-oracle
navigation").

Actual on-foot motion - player, wanderers, and dock pilots alike - goes
through `Person.step_toward(tx, ty, speed, can_move_to)`: one normalized step
(diagonals aren't faster), capped at the distance to the target, wall-sliding
(full step → x-only → y-only) off whatever `can_move_to` rejects. `speed` is
`LocationScreen.speed` (story.json `walking_speed`, world units per 1/60 s
step); `WanderRoutine` uses its own slower `WANDER_SPEED`. See
DESIGN_PATTERNS.md's "One Movement Primitive on the Base Entity".

## Frame Timing & Smooth Motion — two deliberate tradeoffs

Motion smoothness on this engine runs into two hard constraints. Both are
currently resolved by a *calibrated compromise*, not a real fix. This section
records why, and what the real fixes would cost, so a future change is a
decision and not a surprise.

### 1. The sim drops a sliver of time to stay visually smooth

`advance_accumulator` (`game/utils.py`) does **not** do a textbook
`floor(accumulator / step)`. It runs *exactly one* step for any frame worth
~0.5–2.5 steps, and multi-step catch-up only on a sustained slowdown. The
positive remainder is clamped well under a step — i.e. a persistent sub-step
surplus is **discarded** rather than banked for a later catch-up frame.

- **Why:** `floor` emits a 0-step frame next to a 2-step frame under ordinary
  frame-time jitter, and a "60 Hz" panel that's really 59.94 Hz *guarantees*
  that every ~20 s (60 sim steps/s vs 59.94 frames/s — the surplus has to
  surface somewhere). A 2-step frame is a visible lurch on a camera pan.
- **Cost:** the sim tracks the *display* rate, not the wall clock — drift is
  well under 0.1 %. Benign here: every timer is frame-count based
  (`wait_frames`, `_talk_timer`, jump countdowns), there is no netcode, and
  nothing keys off real time-of-day.
- **The real fix — render interpolation:** keep each drawable's previous *and*
  current sim state and `lerp` between them at draw time by
  `accumulator / step`. Sim and render become fully independent — smooth at
  any refresh rate, nothing dropped. Cost: every `draw()` path needs a
  prev/current state pair and a lerp; it's a day of work touching every
  entity. Worth it only if >60 Hz becomes a real feature, or netcode arrives.
- **Revisit if:** multiplayer/netcode is added (needs wall-clock-accurate
  sim), or any real-time mechanic is added.

### 2. Non-integer scroll speed — fixed by a sub-pixel composite path

When the camera pans, a fixed world point moves at `walking_speed ×
get_scale()` screen-px/frame; at common window sizes that's a non-integer
rate (~3.3 px/frame). Snapping every point to a whole pixel renders that as
an irregular **3-3-3-4** cadence — a faint ~15 Hz shimmer of the *world*
(the player stays centred) during cardinal *and* diagonal motion, in the
Space View and in interiors alike. No fixed `walking_speed`/`camera_zoom` is
smooth at every window size, because `get_scale()`'s `min(w/2400, h/1800)`
term moves with the window.

**The fix — a two-layer sub-pixel composite** (`main.py` + `Camera`):

1. **`Camera` splits the camera pan** (`set_offset`) into a whole-pixel part
   and a sub-pixel remainder `_subpixel_x/y ∈ [0,1)`. `to_screen()` ends in
   `floor(... + _subpixel) + WORLD_MARGIN`, not `round(...)` — so between two
   frames a static point's world-surface pixel only ever changes by a *whole*
   number, and all the smooth motion is in the remainder. (`WORLD_MARGIN`, 1px,
   is the bleed border the world surface carries so the compositor's edge
   sample always has a texel.)
2. **The frame is drawn as two layers** — `world_surface` (the scrolling
   world; `<screen>.draw_world()`) and `hud_surface` (static overlay;
   `<screen>.draw_hud()`). `main.present_frame()` composites them.
3. **The world layer is shifted by the sub-pixel remainder** using the SDL2
   renderer's *logical size*: set it to `LOGICAL_SCALE`× (8×) the window,
   draw the world texture there offset by `round((WORLD_MARGIN + subpixel) ×
   8)` whole *logical* pixels, and let SDL's linear-filtered logical→window
   downscale turn that into a smooth fractional shift. Drawing the texture at
   a float destination directly does **not** work — every SDL2 backend on
   Windows quantises `SDL_RenderCopyF`'s position to whole pixels (verified
   across direct3d/11, opengl, opengles2, software). The HUD layer is then
   drawn with logical scaling off, 1:1 → **stays pixel-crisp**.

**Costs / tradeoffs, all accepted:**
- The world layer is slightly softened at non-integer offsets (bilinear
  sampling) — the intended tradeoff; it's *sharp* whenever the pan lands on a
  whole pixel (`floor` keeps static geometry crisp then).
- Two full-window `Texture.update()` per frame (`render.composite` span,
  ~2 ms at native res — both layer surfaces are `SRCALPHA`/BGRA so the upload
  is a straight memcpy, not a ~4.5 ms format conversion).
- `pygame._sdl2.video` is semi-experimental → a `pygame.display.set_mode`
  fallback path (whole-pixel scroll, the old look) runs if no `Renderer` can
  be created.
- **Revisit if:** the ~2 ms composite starts crowding the budget on some
  machine (lower `LOGICAL_SCALE`, or dirty-rect the HUD upload), or a future
  pygame exposes `SDL_RenderGeometry` (float UVs would remove the logical-size
  trick entirely).

## Performance Considerations

**Optimization done:**
- `to_screen()` floors to a stable whole-pixel world-surface grid; the
  sub-pixel scroll is applied once at composite time, not per point (see
  "Frame Timing & Smooth Motion #2" above)
- Both composite layers are `SRCALPHA`/BGRA so `Texture.update()` is a
  straight memcpy (~1 ms each) rather than a ~4.5 ms format conversion
- Scaled once per update cycle, cached
- Viewport letterboxing (only render once)

**Not optimized (and doesn't need to be at this scale):**
- Spatial partitioning for collision
- Dirty rectangle updating
- Sprite batching

For the current entity count (<10), per-entity physics is fine.

## Common Bugs & Fixes

**Bug: Graphics deform on resize**
- ❌ Storing/using screen-space coordinates
- ✅ Always convert to_screen() only when drawing

**Bug: Ships accelerate indefinitely**
- ❌ Forgetting velocity capping after thrust
- ✅ Check speed vs max_velocity and scale down

**Bug: Ship polygon looks squished/stretched**
- ❌ Using separate sin/cos for each point
- ✅ Pre-compute cos_a, sin_a, use for all points

**Bug: Flame drawn off to the side**
- ❌ Using front center instead of back center
- ✅ Average left/right back points for flame origin

**Bug: Star chunks look different on revisit**
- ❌ Seeding `random` globally, or including anything non-deterministic (e.g. wall-clock
  time) in the chunk hash
- ✅ Use a fresh `random.Random(chunk_seed)` per chunk, with `chunk_seed` derived purely
  from `(seed, chunk_x, chunk_y)`
- Note: this rule is `StarField`-only. `AsteroidField` intentionally does the opposite -
  see "No World Boundary" above - so don't "fix" asteroids back into determinism.

See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md#coordinate-conversion) for the coordinate conversion pattern.
