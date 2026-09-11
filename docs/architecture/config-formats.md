# Configuration Formats

Every per-story config file's shape: `systems/*.json`, interior layouts,
`story.json`, ship types, and interior geometry. The runtime classes that
consume these are in [class-hierarchy.md](class-hierarchy.md); the
design-JSON art pipeline is [GRAPHICS_PIPELINE.md](../GRAPHICS_PIPELINE.md).

## Configuration Files

Under `config/stories/{story}/` — two stories can define the same key with
different values. A story's `story.json` may also list shared **`modules`**
(`config/modules/{name}/`, same subtree shape) that the resolver merges under
the story's own files — see [CONFIG_MODULES.md](../CONFIG_MODULES.md). Configs
are never modified by play. See
[SAVE_SYSTEM.md](../SAVE_SYSTEM.md#directory-structure) for the full tree and
the story/save split.

### Stories in this repo

| Story | What it is |
|---|---|
| `default` | The original sandbox. Frozen hand-maintained art (see [DESIGN_ATLAS.md](../DESIGN_ATLAS.md)); not on the design-JSON pipeline. |
| `graphics_pipeline_test` | Reference story for the design-JSON art pipeline ([GRAPHICS_PIPELINE.md](../GRAPHICS_PIPELINE.md)). |
| `the_long_silence` | Five-system faction story — beacon jump-gating, reputation, ship combat, an ending fork. Act I plays end to end. Has its own docs tree: `config/stories/the_long_silence/docs/` (`STORY.md` narrative, `PLAN.md` build checklist, `gen/` slice generators). |
| `the_whisper_line` | Short linear 3-system story — a stranger's note leads the player out past the last beacon to a missing friend and a first-contact fork. Re-uses `graphics_pipeline_test`'s art via the `orbital-std` + `figures-human` modules; no new assets. Notes in `config/stories/the_whisper_line/docs/STORY.md`. |

**`systems/{system_id}.json`** — one star system's layout:
```json
{
  "star_map_position": {"x": 0, "y": 0},
  "locked": true,
  "unlock_flag": "beacon_kiln_lit",
  "station": {"x": 0.75, "y": 0.3},
  "ai_ships": [{"x": 0.75, "y": 0.1, "ship_type": "freighter", "faction": "..."}]
}
```
Both `"station"` and `"moon"` are optional - a system that omits one still
gets a placeholder `LandingSite` at default coordinates with no
`interiors` (`SpaceScreen._build_system_state`), purely so physics/
targeting/drawing/save-restore never need a None check. It's a real,
flyable, targetable body - just nothing to land *in*: `begin_landing()`
(`game/app/loop_helpers.py`) checks for that and turns an attempt to land
on it into a toast instead of opening a broken interior. A system genuinely
needs only the body/bodies its story actually uses.
Station/AI positions are fractions of `GAME_WIDTH`/`GAME_HEIGHT`. An `ai_ships[]`
entry (and an interior `npcs[]` / `structures[]` entry) may carry a `faction` id
(`factions.json`) and/or a **content gate** — `requires_flag` /
`requires_not_flag` (a `Possessions.flags` name) or `requires_rep` /
`requires_rep_below` (`"<faction>:<n>"`, standing `>= n` / `< n`). Gated content
is present only when its conditions hold *right now*: `content_gate.passes_content_gate`
is the check, re-run on **system (re-)entry and on launch** for ships
(`SpaceScreen._sync_conditional_ships`, from `_activate_system` / `board_ship`)
and on **interior (re-)entry** for NPCs + structures
(`LocationScreen._apply_content_gates`, from `arrive_from` — also rebuilds
`building_footprints` and invalidates the nav grid). Cosmetic `decorations` are
not gated. This is also what fixes "a character added to a story doesn't appear
in an old save" — the roster is re-derived from config on every entry, never
from the save. `locked: true` + `unlock_flag` (a `Possessions.flags` name)
make a system unreachable until that flag is set — beacon jump-gating, checked
by `utils.system_unlocked()` in `SpaceScreen.try_jump` and the `StarMap`; set
the flag with the `"light_beacon:<system_id>"` dialogue action, a mission's
`on_end_flags`, or a plain `set_flag:`. Add `"unlock_silent": true` to skip
the galaxy-wide "Beacon relit" broadcast when it unlocks — for a system that
is *keyed* for the player as a premise (the story's first lane) rather than
relit by them out in the dark (`SpaceScreen._check_beacons`).
`get_star_systems()` surfaces `name`, `star_map_position`, `station_name`,
`moon_name`, `locked`, `unlock_flag`, and `unlock_silent` (the star-map
projection — not the full system file).

**Interior layout** (per key in a landing site's `interiors`): a `culture`, one
or more `rooms` (`{"rect": […]}`, `{"polygon": [[x,y],…]}`, or `{"shape":
"circle", "center": […], "radius": r}` — walkable area is their union),
`portals` (`{"x", "y", "return_to_ship": true}` for a ship dock), optional
`decorations` (cosmetic decals) and `structures` (solid, if they carry a
`footprint`), and `npcs`. A `structures[]` or `npcs[]` entry may carry a
content gate (`requires_flag` / `requires_rep` / … — see the `systems/*.json`
note above); gated entries are (re-)evaluated on every interior entry. An
`npcs[]` entry may also carry `"facing"` (`"west"`/`"east"`/`"left"`/`"right"`
— initial facing for an NPC that stands still) and `"depart_flag"` (a
`Possessions.flags` name that, once set, swaps the NPC into `DepartRoutine` —
walk to the nearest portal and vanish for good; pair with
`requires_not_flag` on the same flag — see
[class-hierarchy.md](class-hierarchy.md)'s routine table). A
default-story station is one such interior. See "Interior geometry" below and
`game/screens/location_screen/` (config load + gates in `screen.py`, geometry
helpers in `_defs.py`).
```json
{
  "label": "Alpha Station", "culture": "vherathi",
  "portals": [{"x": 660, "y": 345, "return_to_ship": true}],
  "rooms": [{"label": "Concourse", "shape": "circle", "center": [400, 300], "radius": 150}],
  "npcs": [{"name": "…", "x": 400, "y": 100, "role": "bartender", "dialogue_options": [...]}]
}
```

For `story.json`'s own fields, see the "`story.json` fields" table below.
For `ship_types.json` / `graphics.json` and adding a ship type, see "Adding or
Updating a Ship Type".

## Adding or Updating a Ship Type

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
| `rotation_speed` (degrees/frame) | 1 – 3 | 3 – 5 | 5 |
| `size` (world units) | 8 – 14 | 14 – 24 | 24 – 35 |

**`rotation_speed` has a hard ceiling of 5 degrees/frame across the whole roster** - past that,
aiming (especially with the laser cannon, see below) stops feeling controllable. Don't add a
ship type above it.

A rule of thumb from the existing roster: big/slow cargo ships (`freighter`) pair low thrust +
low velocity + low rotation + high size; small/agile ships (`patrol`) pair medium-high thrust +
medium-high velocity + medium-high rotation + low size. Values well outside these ranges will
still work (nothing enforces them) but will feel very different from the rest of the fleet.

**Culture and material palette:** if a ship (or building — see `LandingSite`/`LocationScreen`
in [class-hierarchy.md](class-hierarchy.md)) belongs to an existing culture, set
`"culture": "<culture_id>"` in its `graphics.json`/
`building_types.json` entry instead of hardcoding `color`. `get_graphics_asset()`/
`get_building_type()` (in `utils.py`) automatically fill in `color`, `core_color`/
`window_color`, and `thrust_color` from that culture's `metal_color`/`glass_color`/
`thrust_color` in `config/stories/{story}/cultures.json`. Each culture entry also carries a
`theme` field — read it and follow it when designing new ships or buildings for that culture,
so the whole culture stays visually cohesive. See `config/stories/default/cultures.json` for
the currently defined cultures (e.g. the Vherathi Concord).

## `story.json` fields

Top-level per-story config, read via `utils.get_story()`. All optional
except where a story clearly needs it; code holds the default.

| Field | Purpose |
|---|---|
| `id` / `name` / `description` / `difficulty` | Identity + story-picker card |
| `version` | Save-compat version (see SAVE_SYSTEM.md) |
| `modules` | Optional list of shared config kits under `config/modules/` to merge under this story's files, earlier entries winning. A module's own `module.json` may carry a `"modules"` list too — the tree is flattened depth-first, first-occurrence-wins (see [CONFIG_MODULES.md](../CONFIG_MODULES.md)) |
| `starting_system` | Which `systems/*.json` a new game loads |
| `starting_mission` / `starting_mission_trigger` | Auto-started mission + when (`"ship_purchase"` / `"new_game"`) |
| `acts` | `[{"id", "name", "advance_flag"?}]` - the current act (last one whose predecessor's `advance_flag` is set) shows on the Space View HUD; `utils.current_act()` |
| `intro` | Optional opening crawl shown between the pilot-name dialog and the world: `{"title", "body": [paragraph, ...]}`. `body` may be a bare string. `{pilot}` in any paragraph is replaced with the entered name. Absent → no intro screen. See `game/ui/intro_screen.py`, [UI_FLOW.md](../UI_FLOW.md) |
| `start` | New-game state: `location` (`station`/`moon`/`space`), `interior`, `credits`, `ship`, `outfits[]`, `items{}`, `flags{}` (see `SpaceScreen._apply_start_config` / `begin_new_game`) |
| `loan` | `lender` / `amount` / `max_active` for the `take_loan` dialogue action |
| `jump` | `travel_frames` / `speed` / `arrival_distance` / `self_min_distance` |
| `brake_slow_threshold` | Speed the tutorial's braking stage completes below |
| `camera_zoom` / `camera_zoom_min` / `camera_zoom_max` | Space View world-render magnification: starting level + mouse-wheel zoom bounds (defaults `constants.CAMERA_ZOOM` / `_MIN` / `_MAX`) |
| `interior_camera_zoom` / `interior_camera_zoom_min` / `interior_camera_zoom_max` | Same, for interiors - a separate level and range (defaults `constants.INTERIOR_CAMERA_ZOOM` / `_MIN` / `_MAX`) |
| `walking_speed` | On-foot pace, player + AI dock-walkers (default `constants.WALKING_SPEED`) |
| `default_outfit` | `graphics.json` `outfits` id for the player + AI pilots |
| `ships.player_type` | Placeholder ship stats before one is owned (usually `null`) |

## Story dispatches (`dispatches.json`, optional)

`{dispatch_id: entry}` - "inbox" comms from faction handlers that arrive in
the Message Log when their condition first holds, no NPC in the room needed
(the story design's gap F). Merged from `modules` like `missions.json`.
`game/world/dispatch.py` is the logic; `SpaceScreen._check_dispatches` runs
it every frame (docked too), seeded silent on first call after a load, and
receives at most one dispatch per frame. Visible pacing is handled by the
shared message queue (`_post_message` / `_pump_message_queue`, ~7.5s /
`MESSAGE_SPACING_FRAMES` between any two one-way comms). Gate each dispatch
on the progress point it actually belongs to - don't hang several on one
early flag and rely on the spacing to sort them out.

A dispatch with a `start_mission` **is** that mission's opening comm: the
engine does not also deliver the started mission's stage-0 `one_way_message`
(author stage 0 without one). The dispatch `body` must name the first action.

```json
"combine_mobilises": {
  "sender": "Ninefold Combine — liaison",
  "subject": "Notice of closure",
  "body": "The Kiln lane is closing...",
  "requires_flag": "act_pressure",
  "requires_rep_below": "ninefold_combine:15",
  "on_receive_flags": ["combine_mobilised"],
  "on_receive_rep": {"ninefold_combine": -3},
  "start_mission": "combine_evacuation"
}
```

Gate keys are `content_gate`'s (`requires_flag` / `requires_not_flag` /
`requires_rep` / `requires_rep_below`); none = arrives on the first check.
Each key takes a **single** value - there's no AND of two `requires_flag`
on one entry, so a sequence chains on `dispatch:<id>` (see below) or on
story-progress flags that land in order.
On receipt a `dispatch:<id>` flag is set (usable as a later dispatch's
`requires_flag` to chain them), `on_receive_flags` / `on_receive_rep` apply,
and `start_mission` begins (if not already active/done) with its first
stage's `one_way_message` delivered. The `the_long_silence` "reactivation
front" chain (`relay_front_kiln` → `_verdance` → `_ossuary` → `_span`) is the
worked example - each hangs on the next system's unlock/act flag.

## Interior geometry (`LocationScreen`)

A culture-tagged interior's walkable
area is the **union of its `rooms`** — each a polygon (`normalize_room` folds
`{"rect": …}`, `{"polygon": […]}`, and `{"shape": "circle", …}` N-gons to one
form). Overlapping polygons read as one connected space; `can_move_to` is a
point-in-any-polygon test (concave-safe). `plan_path()` routes a walking body
(the player's own movement wall-slides; `DockRoutine` pilots use this) across
that area with a grid A* + string-pull (`IndoorPathfinder` / `NavGrid`, one
cached raster per interior, `can_move_to` as its oracle). `decorations` are
cosmetic floor/wall decals (`normalize_decoration`) with **no collision**;
each culture's `interior_decoration` generator (`edge_veins` room-edge veins /
`seam_rivets` edge ticks / `deck_grid` a spacing-`spacing` line grid clipped to
each room by `_clip_segment_convex`) stamps a pack onto every room
automatically. An interior config with `"space_backdrop": true` fills with the
Space View's black + a `StarField` (own `star_seed` / `star_density`) instead of
the flat wall colour, so the lit floor polygons read as decks open to the void
(the concourse in `graphics_pipeline_test`). `"seamless": true` drops the
per-room trim outline, the room-name labels, and the culture's edge-emphasising
`interior_decoration` — so an interior of overlapping room polygons reads as one
open deck rather than a set of boxes. `"floor_pattern": {"pattern": "hex" |
"square" | "triangle" | "rhombus", "tile": <world units>, "gap": <inset>,
"colors": [[r,g,b], …]}` fills every room with a repeating tile clipped to the
room polygon (`deck_grid.tessellate` / `clip_polygon_convex`); with no explicit
`colors` it cycles three shades derived from the culture's `floor_color` /
`wall_trim_color`. `the_long_silence`'s station concourses set all three (see
`config/stories/the_long_silence/docs/gen/_slice_kit.py` `station_shell`). `structures` that name a
`building_type` are solid: anything with a `footprint` block (spires, halls,
and the furniture types — `*_bench`, `*_planter`, `*_lamp`, `*_desk`,
`*_seat_pod`, `*_crate`, `*_barrel`) contributes a ground-level collision box
to `building_footprints`, which `can_move_to` (and therefore `plan_path`'s nav
grid) rejects. A `building_type` (and a ship/station in `graphics.json`) may
also carry an optional **`parts`** list — filled polygons / circles /
polylines (each with a `color`) drawn back-to-front by
`WorldObject.draw_parts()` with **no synthesised outline** (an outline is
already its own slightly-larger polygon/circle part), for multi-shape detail
the single base silhouette can't express. For the `default` story these lists
are frozen data in `config/stories/default/graphics.json` /
`building_types.json` ([DESIGN_ATLAS.md](../DESIGN_ATLAS.md)); a pipeline story's
entry instead names a `"design"` and `expand()` fills `parts` at load
([GRAPHICS_PIPELINE.md](../GRAPHICS_PIPELINE.md)). When `parts` is present it is the
*whole* drawn silhouette — `Ship.draw` / `LandingSite._draw_station` skip the
flat base polygon and the `windows` dots entirely — but `shape` / dims /
`local_points` still drive `_building_footprint` / `_structure_depth` /
collision / target brackets regardless. Keep furniture footprints clear of NPC spawn points, portals,
and the necks between rooms — `tests/test_location_screen.py`'s
`TestStationInteriorLayout` walks a real path across Alpha Station and fails if
a placement pinches it shut. See [DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md)'s
"Walkability-oracle navigation".
