# Architecture & Class Design

Class hierarchy, entity patterns, and extensibility points for the space game.

## Class Hierarchy

### Entity Base Classes
```
Ship (abstract base)
├── Player (extends Ship)
└── AIShip (extends Ship)

Person (abstract base)
└── NPC (extends Person)
```

### Game Screens (State Machine)
```
Screen (implicit interface)
├── Menu
├── GameScreen
├── StationInterior
├── PauseMenu
└── LoadMenu, SaveDialog (sub-screens within Pause)
```

### Supporting Classes
- `StarField` — Procedural star generation with seeded randomness
- `SpaceStation` — Static station object in GameScreen
- `Dialogue` — Conversation tree system

## Entity Design Pattern

All entity classes follow this pattern:

```python
class Entity:
    def __init__(self, x, y, ...):
        # State
        self.x, self.y = x, y
        
    def update(self):
        # Physics/behavior each frame
        
    def draw(self, surface):
        # Render to screen-space
        
    def get_distance(self, x, y):
        # Utility for range checks
```

**Key principle:** Store positions in game-space, convert to screen-space only when drawing.

See [PHYSICS.md](PHYSICS.md#coordinate-system) for coordinate conversion details.

## Ship Class: Movement & Rotation

**Base Class: Ship**
- Stores: `x`, `y`, `angle`, `velocity_x`, `velocity_y`, `thrust`
- Physics: drag, max_velocity, rotation_speed
- Methods:
  - `draw_ship(surface, size, color)` — Rotated polygon + flame
  - `wrap_position()` — Screen-edge wrapping
  - `update()` — Physics simulation (velocity + drag)

**Subclass: Player**
- Extends `update()` with player input handling
- Adds `handle_input(keys)` for WASD/arrow controls

**Subclass: AIShip**
- Implements autonomous behavior (wander/avoid)
- Separate `update()` with AI decision-making

**Extending for new ship types:**
```python
class Shuttle(Ship):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_thrust = 0.5  # Different specs
        
    def update(self):
        # Custom AI behavior
        super().update()  # Physics still applies
```

## Person Class: NPCs & Drawing

**Base Class: Person**
- Stores position and appearance
- Implements `draw(surface)` — head + body
- Provides `get_distance(x, y)` for interaction checks

**Subclass: NPC**
- Adds `behavior` (bar/wander) and `Dialogue` system
- Movement logic: collision-aware wandering
- Extends `draw()` to show dialogue prompts

**Pattern: Behavior Encapsulation**
- Store behavior as string or enum
- Use conditional in `update()`:
  ```python
  if self.behavior == "bar":
      self._behavior_bar()
  elif self.behavior == "wander":
      self._behavior_wander()
  ```

## Game Screen Responsibility

**GameScreen contains:**
- Player (controlled entity)
- AIShip (autonomous entity)
- StarField (visual, procedural)
- SpaceStation (collision target)

**GameScreen provides:**
- `update()` — Update all entities each frame
- `draw()` — Render all entities
- `handle_input()` — Process player input
- `get_state()` — Capture state for save [see SAVE_SYSTEM.md](SAVE_SYSTEM.md)
- `restore_state()` — Restore from save file

**Why this design:**
- Clear separation of concerns
- Easy to pause/resume game state
- Simple to add new entity types (extend and add to update/draw)

## State Machine: Screen Flow

```
Menu ↔ LoadMenu
  ↓
GameScreen ← → PauseMenu
  ↓ (land)     ↓ (save)
  StationInterior ← → SaveDialog
```

**State transitions via return values:**
- `handle_input()` returns action string
- Main loop interprets and transitions screens
- See [UI_FLOW.md](UI_FLOW.md) for details

## Extensibility Points

### Adding a New Entity Type
1. Create class extending `Ship` or `Person`
2. Override `update()` and/or `draw()`
3. Add to GameScreen
4. Include in `get_state()`/`restore_state()` if saveable

### Adding a New Screen
1. Create class with `handle_input()`, `draw()`, `update()`
2. Add state string to main loop conditions
3. Implement transitions via handle_input return values

### Adding NPC Behaviors
1. Add behavior name to `station_interior.json`
2. Implement `_behavior_[name]()` method
3. Call from `update()` based on behavior enum

## Design Decisions

**Why base classes for Ship & Person?**
- DRY principle: shared movement, drawing, distance logic
- Polymorphism: both subclasses work with same interface
- Easy to add variants (Shuttle, Probe, Guard, Merchant, etc.)

**Why get_state()/restore_state() in GameScreen?**
- Centralized state capture for save/load
- Clear contract for what needs persistence
- Easy to extend when adding new saveable objects

**Why screen-wrapping over boundaries?**
- Creates infinite space feel with small coordinate system
- Simple physics (no out-of-bounds checks)
- Player can explore infinitely without loading new areas

See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) for reusable solutions across the codebase.
