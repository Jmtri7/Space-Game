# Physics & Coordinate System

Core physics simulation and critical coordinate system understanding.

## Coordinate System (Critical!)

**Game Space:** 800x600 (logical, never changes)
- All entity positions and velocities stored here
- All game logic operates here
- Wrap-around boundaries at 800x600

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
    # Convert game-space (x,y) to screen-space
    scale = get_scale()
    offset_x, offset_y = get_offset()
    return (int(round(x * scale + offset_x)), int(round(y * scale + offset_y)))
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

### Screen Wrapping
```python
def wrap_position(self):
    if self.x < 0:
        self.x = GAME_WIDTH
    elif self.x > GAME_WIDTH:
        self.x = 0
    if self.y < 0:
        self.y = GAME_HEIGHT
    elif self.y > GAME_HEIGHT:
        self.y = 0
```

**Why game-space bounds?** Objects that go off-screen wrap around. Uses GAME_WIDTH/GAME_HEIGHT, not screen dimensions.

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
```python
def _is_in_valid_area(self, x, y):
    if self._is_in_hallway(x, y):
        return True
    if self._is_in_bar(x, y):
        return True
    return False
```

Movement only allowed in defined rooms to prevent walking through walls.

## Performance Considerations

**Optimization done:**
- Integer rounding on screen coordinates (no subpixel rendering)
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

**Bug: Objects don't wrap at edges**
- ❌ Checking against screen dimensions
- ✅ Use GAME_WIDTH/GAME_HEIGHT in wrap_position()

See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md#coordinate-conversion) for the coordinate conversion pattern.
