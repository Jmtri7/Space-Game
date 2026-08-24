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

**Problem:** Multiple entity types (Player, AIShip) duplicate drawing and physics.

**Solution:** Extract shared logic into abstract base class.

**Implementation:**
```python
class Ship:  # Base class
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.velocity_x = self.velocity_y = 0
        self.thrust = 0
        self.angle = 0
    
    def draw_ship(self, surface, color=GRAY):
        # Shared drawing logic
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        # ... rotate and draw polygon
    
    def wrap_position(self):
        # Shared boundary logic
        if self.x < 0: self.x = GAME_WIDTH
        # ...
    
    def update(self):
        # Base physics (child can extend)
        self.velocity_x *= drag
        self.velocity_y *= drag
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.wrap_position()

class Player(Ship):  # Specialized
    def handle_input(self, keys):
        # Player-specific input
        if keys[UP]: self.thrust = min(self.thrust + 0.02, max_thrust)
    
    def update(self):
        # Call base physics
        super().update()

class AIShip(Ship):  # Specialized
    def update(self):
        # AI behavior
        self._behavior_wander()
        # Then base physics
        super().update()
```

**Why this works:**
- DRY: No duplicate draw_ship(), wrap_position()
- Extensible: New ship types inherit for free
- Polymorphic: Both subclasses work with same interface
- Testable: Base logic separable from child behavior

**Use case:** Multiple entity types sharing core functionality.

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
            draw_text(surface, "↑ more")
        
        # Show visible items
        visible = self.items[self.scroll_offset:self.scroll_offset + self.max_visible]
        for i, item in enumerate(visible):
            is_selected = (self.scroll_offset + i == self.selected)
            draw_text(surface, item, highlight=is_selected)
        
        # Show scroll indicator if not at bottom
        if self.scroll_offset + self.max_visible < len(self.items):
            draw_text(surface, "↓ more")
```

**Why this works:**
- `scroll_offset`: What part of list to show (scrolling window)
- `selected`: Which item is highlighted (independent)
- Sync check: Adjusts scroll when selection moves outside window
- Wrapping: Selection loops at boundaries

**Use case:** Menus/lists that might exceed visible area.

---

## Pattern: Scrollable List Handler (Shared Logic)

**Problem:** SaveDialog, LoadMenu both duplicate up/down navigation with wrapping and scroll-sync.

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

# In SaveDialog.handle_input():
self.selected, self.scroll_offset = _handle_scrolling_input(
    event.key, self.selected, self.items, self.scroll_offset, self.max_visible)

# In LoadMenu.handle_input():
self.selected, self.scroll_offset = _handle_scrolling_input(
    event.key, self.selected, self.items, self.scroll_offset, self.max_visible)
```

**Why this works:**
- Pure function (no side effects, testable in isolation)
- Reusable by both SaveDialog and LoadMenu (DRY)
- Single place to fix boundary/wrapping bugs
- Easy to add new key bindings (modify function signature once)

**Use case:** Multiple menus/lists that all need identical scrolling behavior.

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
            load_menu = LoadMenu()
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
