# Save System & State Persistence

Save file format, state capture, and restoration logic.

## Overview

Saves are stored as JSON files in `saves/` directory with pilot name and timestamp.

**Key principle:** Separate original config from player state.
- Original config (`space_system.json`) unchanged
- Player changes captured in `game_state` within save file
- Load = restore config + apply player state

## File Format

**Filename:** `save_{pilot_name}_{timestamp}.json`

**Example:** `save_Alice_20260821_171936.json`

**Content Structure:**
```json
{
  "pilot_name": "Alice",
  "name": "First Exploration",
  "timestamp": "20260821_171936",
  "system": {
    "station": {"x": 0.75, "y": 0.3},
    "ai_ships": [{"x": 0.75, "y": 0.1, "color": [150, 150, 200]}]
  },
  "game_state": {
    "player": {
      "x": 250.5,
      "y": 150.3,
      "angle": 45,
      "velocity_x": 1.2,
      "velocity_y": -0.5,
      "thrust": 0.15
    },
    "ai_ship": {
      "x": 600.0,
      "y": 180.0,
      "angle": 180,
      "velocity_x": -2.0,
      "velocity_y": 0.5,
      "thrust": 0.2
    }
  },
  "station": {}
}
```

## State Capture & Restoration

### Capturing State: `get_state()`

Called in GameScreen before saving:
```python
def get_state(self):
    return {
        "player": {
            "x": self.player.x,
            "y": self.player.y,
            "angle": self.player.angle,
            "velocity_x": self.player.velocity_x,
            "velocity_y": self.player.velocity_y,
            "thrust": self.player.thrust
        },
        "ai_ship": {
            "x": self.ai_ship.x,
            "y": self.ai_ship.y,
            "angle": self.ai_ship.angle,
            "velocity_x": self.ai_ship.velocity_x,
            "velocity_y": self.ai_ship.velocity_y,
            "thrust": self.ai_ship.thrust
        }
    }
```

**What's captured:**
- Player position, angle, velocity, thrust
- AI ship same
- Station position (could be restored but currently fixed)

**What's NOT captured:**
- Star field (deterministic, regenerated)
- Landing prompt visibility (transient UI state)
- NPC positions in station (reset on entry)

### Restoring State: `restore_state()`

Called in main loop after loading:
```python
game_screen.restore_state(save_data.get("game_state", {}))
```

**In GameScreen:**
```python
def restore_state(self, state):
    if not state:
        return
    if "player" in state:
        player_state = state["player"]
        self.player.x = player_state.get("x", self.player.x)
        self.player.y = player_state.get("y", self.player.y)
        # ... restore all properties
```

**Graceful fallback:** `.get(key, default)` means missing properties use current values.

## Save/Load Flow

### Saving

```
Pause Menu → User selects "Save Game"
    ↓
SaveDialog opens (shows all existing saves)
    ↓
User enters pilot name (or selects existing save)
    ↓
create_save_file(pilot_name, save_name, system_config, game_state)
    ↓
JSON written to saves/save_{pilot_name}_{timestamp}.json
    ↓
Success banner shown for 2 seconds
```

### Loading

```
Main Menu → User selects "Load"
    ↓
LoadMenu shows available saves (scrollable, 5 at a time)
    ↓
User selects save file
    ↓
load_save_file(filename) → parse JSON
    ↓
GameScreen created with restored config
    ↓
game_screen.restore_state(saved_game_state)
    ↓
Game resumes with player at saved position
```

## Save Dialog (Scrollable List)

Shows **all saves** in the directory, not filtered by pilot.

**Interaction:**
- ↑/↓ arrows to navigate (wraps around)
- Shows 5 saves at a time with ↑/↓ more indicators
- Enter to overwrite selected save
- N to create new save (prompts for pilot name)
- ESC to cancel

**Scrolling Logic:**
```python
if self.selected_existing >= self.scroll_offset + self.max_visible:
    self.scroll_offset += 1  # Scroll down when reaching bottom
elif self.selected_existing < self.scroll_offset:
    self.scroll_offset -= 1  # Scroll up when reaching top
```

## Extending State Persistence

When adding a new saveable entity:

1. **Add to get_state():**
   ```python
   def get_state(self):
       state = { ... }
       state["new_entity"] = {
           "x": self.new_entity.x,
           "y": self.new_entity.y,
           # ... other properties
       }
       return state
   ```

2. **Add to restore_state():**
   ```python
   if "new_entity" in state:
       entity_state = state["new_entity"]
       self.new_entity.x = entity_state.get("x", self.new_entity.x)
       # ... restore other properties
   ```

3. **Pass game_state to save:**
   ```python
   create_save_file(pilot_name, save_name, config, {}, game_screen.get_state())
   ```

## Directory Structure

```
space-game/
├── saves/                          # Auto-created on first save
│   ├── save_Alice_20260821.json
│   ├── save_Bob_20260821.json
│   └── save_Alice_20260821.json   # Can have multiple per pilot
├── config/
│   ├── space_system.json          # Original system config
│   └── station_interior.json      # Original station layout
```

**Note:** Original configs in `config/` are never modified. Each save captures a snapshot including its own `system` config (which is the original, but save includes it for self-containment).

## Save File Lifecycle

1. **On New Game:** System config loaded from `config/space_system.json`
2. **On Save:** Current game state + config snapshot → `saves/save_*.json`
3. **On Load:** Config + state from save restored to GameScreen
4. **On Station Entry:** Separate state (station interior state) managed (currently not saved, NPCs reset)

## Future Enhancements

- [ ] Station interior state persistence (player position in station)
- [ ] NPC state per save (learned dialogue, location changes)
- [ ] Multiple character support (switch pilots)
- [ ] Auto-save on exit
- [ ] Save slots with descriptions (not just filenames)
- [ ] Compression for large state objects

See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md#state-persistence) for the state persistence pattern.
