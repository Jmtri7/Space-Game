# Patterns: Persistence & Data-Driven Config

How state is saved and how content is kept out of code. Hub + working
principles: [DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md). The full save format is
[SAVE_SYSTEM.md](../SAVE_SYSTEM.md).

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
