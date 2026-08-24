# Save System & State Persistence

Save file format, state capture, and restoration logic.

## Overview

Saves are stored as JSON files in the `saves/` directory.

**Key principle:** Separate original config from player state.
- Original config (the current system's `config/stories/{story}/systems/{system_id}.json`)
  captured as a snapshot
- Player changes captured in `game_state` within the save file, including which `story`
  and `system_id` the save belongs to
- Load = restore config + apply player state

## File Format

**Filename:** `save_{name}.json`, where `name` is whatever the player typed/accepted
in `SaveDialog` — by default `"{pilot_name} - {timestamp}"`, but it's free text and
can be edited before saving. There's no separate timestamp field; if the default
name is kept, the timestamp lives inside it.

**Example:** `save_Alice - 2026-08-21 1719.json`

**Content Structure:**
```json
{
  "pilot_name": "Alice",
  "name": "Alice - 2026-08-21 1719",
  "system": {
    "station": {"x": 0.75, "y": 0.3},
    "ai_ships": [{"x": 0.75, "y": 0.1, "ship_type": "trader"}]
  },
  "station": {},
  "game_state": {
    "story": "default",
    "system_id": "sol_alpha",
    "location": "space",
    "player": {
      "x": 250.5,
      "y": 150.3,
      "angle": 45,
      "velocity_x": 1.2,
      "velocity_y": -0.5,
      "thrust": 0.15
    },
    "ai_ships": [
      {
        "x": 600.0,
        "y": 180.0,
        "angle": 180,
        "velocity_x": -2.0,
        "velocity_y": 0.5,
        "thrust": 0.2
      }
    ]
  }
}
```

`"station"` is written by `create_save_file()`'s `station_data` parameter — currently
always passed as `{}`; when saving from a `LocationScreen` it instead carries
`station_interior.station_config` for a station save.

`game_state["location"]` is one of `"space"`, `"station"`, or `"moon"` and drives
where `LoadMenu` sends you. Station/moon saves also add `game_state["moon_location"]`
(`"city"` or `"wilderness"`) when relevant. `game_state["story"]` and `game_state["system_id"]`
record which story and which star system within it the save belongs to, so loading
resolves config from the right place (`config/stories/{story}/...`) and jumps back into
the right system rather than always the story's starting one.

## State Capture & Restoration

### Capturing State: `get_state()`

Called on `SpaceScreen` before saving:
```python
def get_state(self):
    state = {
        "player": {
            "x": self.player.x,
            "y": self.player.y,
            "angle": self.player.angle,
            "velocity_x": self.player.velocity_x,
            "velocity_y": self.player.velocity_y,
            "thrust": self.player.thrust
        }
    }
    if self.ai_ships:
        state["ai_ships"] = [
            {"x": s.x, "y": s.y, "angle": s.angle,
             "velocity_x": s.velocity_x, "velocity_y": s.velocity_y, "thrust": s.thrust}
            for s in self.ai_ships
        ]
    return state
```

`LocationScreen.get_state()` is far simpler — it only tracks the player's walking position:
```python
def get_state(self):
    return {"player": {"x": self.player_x, "y": self.player_y}}
```

**What's captured:**
- Player position, angle, velocity, thrust (space) or just x/y (locations)
- Every AI ship's position, angle, velocity, thrust — as a list, in ship order
- Station/moon position (implicitly, via the `system` config snapshot)

**What's NOT captured:**
- Star field (deterministic, regenerated)
- Landing prompt visibility (transient UI state)
- NPC positions in a location (reset on entry)

### Restoring State: `restore_state()`

Called in the main loop after loading:
```python
game_screen.restore_state(save_data.get("game_state", {}))
```

**In `SpaceScreen`:** restores `player` fields with `.get(key, default)` fallback,
then loops `state["ai_ships"]` and restores each by index into `self.ai_ships`
(extra saved ships beyond the current story's count are ignored).

**In `LocationScreen`:** restores just `player_x`/`player_y`.

**Graceful fallback:** `.get(key, default)` means missing properties use current values.

## Save/Load Flow

### Saving

```
Pause Menu → User selects "Save Game"
    ↓
SaveDialog opens (shows all existing saves, pre-fills a default name)
    ↓
User picks an existing save to overwrite, or types a new name (N)
    ↓
Overwrite? → ConfirmDialog("Overwrite Save?") → old file deleted first
    ↓
create_save_file(pilot_name, save_description, system_config, station_data, game_state)
    ↓
JSON written to saves/save_{save_description}.json
    ↓
Success banner shown for 2 seconds
```

Which screen's state gets saved depends on `previous_screen` (`"game"`, `"station"`,
or `"moon"`) — see [UI_FLOW.md](UI_FLOW.md#screen-to-screen-data-flow).

### Loading

```
Main Menu → User selects "Load"
    ↓
LoadMenu shows available saves (scrollable, 5 at a time)
    ↓
User selects save file (or presses D to delete, with its own ConfirmDialog)
    ↓
load_save_file(filename) → parse JSON
    ↓
SpaceScreen created with restored system config + player/AI state
    ↓
game_state["location"] read: "station"/"moon" also creates a LocationScreen
for the saved interior, restored from the same game_state
    ↓
Game resumes at the saved screen and position
```

## Save Dialog (Scrollable List)

Shows **all saves** in the directory, not filtered by pilot.

**Interaction:**
- ↑/↓ arrows to navigate (wraps around)
- Shows 5 saves at a time with ↑/↓ more indicators
- Enter to overwrite selected save (confirms via `ConfirmDialog`)
- N to create new save (keeps the pre-filled default name, editable)
- D to delete selected save (confirms via `ConfirmDialog`)
- ESC to cancel

**Scrolling Logic:** shared with `LoadMenu` via `utils._handle_scrolling_input()`
(see the "Scrollable List Handler" pattern in [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md)).

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

3. **It flows through automatically** — `create_save_file()` just serializes whatever
   `get_state()` returns; no changes needed there.

## Directory Structure

```
space-game/
├── saves/                                  # Auto-created on first save
│   ├── save_Alice - 2026-08-21 1719.json
│   └── save_First Exploration.json         # Free-text names, not one-per-pilot
├── config/
│   └── stories/
│       └── default/
│           ├── story.json                  # Story metadata (title, ship/asset picks)
│           ├── ship_types.json             # This story's ship physics/stat presets
│           ├── graphics.json               # This story's visual assets (ships, stations, moons)
│           ├── cultures.json               # This story's material/design palettes
│           ├── building_types.json         # This story's building presets
│           ├── pilots.json                 # This story's AI pilot roster
│           └── systems/
│               ├── sol_alpha.json          # Station/moon placement, AI ship roster
│               └── keplers_reach.json      # A second star system within the same story
```

**Note:** Every config file lives entirely under one story's folder — nothing is shared
between stories, so two stories can define the same ship-type key with completely
different stats. Configs under `config/` are never modified by play. Each save captures
a snapshot of the current system's config as `system`, so the save is self-contained even
if the story config changes later.

## Save File Lifecycle

1. **On New Game:** System config loaded from
   `config/stories/{story}/systems/{system_id}.json`
2. **On Save:** Current game state + config snapshot → `saves/save_{name}.json`
3. **On Load:** Config + state from save restored to `SpaceScreen` (and a `LocationScreen`
   if the save was made while docked)
4. **Interior state persistence:** player x/y in a `LocationScreen` IS saved (via its own
   `get_state()`); NPC state is not — NPCs reset on entry

## Future Enhancements

- [ ] NPC state per save (learned dialogue, location changes)
- [ ] Multiple character support (switch pilots)
- [ ] Auto-save on exit
- [ ] Save slots with thumbnails/previews
- [ ] Compression for large state objects

See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md#state-persistence) for the state persistence pattern.
