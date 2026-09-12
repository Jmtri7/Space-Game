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
| `the_long_silence` | Five-system faction story — beacon jump-gating, reputation, ship combat, an ending fork. Act I plays end to end. Has its own docs tree: `config/stories/the_long_silence/docs/` (`STORY.md` narrative, `PLAN.md` build checklist, `gen/` slice generators). |
| `the_whisper_line` | Short linear 3-system story — a stranger's note leads the player out past the last beacon to a missing friend and a first-contact fork. Reuses the `orbital-std` + `figures-human` modules' art (see [GRAPHICS_PIPELINE.md](../GRAPHICS_PIPELINE.md)); no new assets. Notes in `config/stories/the_whisper_line/docs/STORY.md`. |
| `mining_101` | One-system, one-mission tutorial: buy and mount a laser, mine the belt (including a rare `system-events`-driven ore-rich asteroid), sell the haul. Reuses `orbital-std` + `figures-human`; no new assets. Notes in `config/stories/mining_101/docs/STORY.md`. |

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
`moon_name`, `locked`, `unlock_flag`, `unlock_silent`, and `hazard` (the
star-map projection — not the full system file). `"hazard": "pirates"` is
static map flavor only — "this system is known to see pirate activity" —
drawn by `StarMap.draw_content` as a "PIRATE ACTIVITY" tag next to the
system's name; it's independent of whether a `pirate_ambush` event has
actually rolled there this session (see "System events" below), so it
stays displayed either way. No other `hazard` value means anything yet.

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

An npc entry's optional `"icon_shape"`/`"icon_color"` swap its whole walking
figure for a small static item glyph at its position (`Person.icon_shape` /
`_draw_icon`, drawn with `ui_theme.draw_item_icon` - the same procedural
glyphs shop items/ore pickups/projectiles already use, `icon_shape` one of
its recognised names or any other value for its plain-crate fallback). Use
it for an NPC that's really an inanimate object with dialogue rather than
someone to talk to - a derelict-ship loot container
(`derelicts.py`'s `_build_loot_interior_config`) is the first user. Nothing
else about the NPC changes: dialogue, T-to-talk range, `role`/routine, and
position all work exactly as they do for a normal figure - only `draw()`
takes the icon branch instead of the walk-cycle body.

### System events

A system's config may carry an `"events"` array - entries a story opts into
from a shared `events.json` catalogue (id -> `{"kind": ..., ...fields}`,
resolved through modules exactly like `asteroid_types.json`/`ship_outfits.json`
- see [CONFIG_MODULES.md](../CONFIG_MODULES.md) - so a story lists the
`system-events` module rather than authoring its own). Each entry in a
system's `"events"` names one catalogue id plus a `"frequency"`, whose
meaning depends on the event's `"kind"`:

```json
"events": [
  {"event": "rich_ore_vein", "frequency": 0.12}
]
```

Today's only `"kind"` is `"special_asteroid"` - `"frequency"` is the
independent chance, rolled once per `AsteroidField` chunk as the player
travels, that one extra asteroid of that kind spawns in that chunk (on top
of, not instead of, the system's normal `asteroid_field.types` draws - see
[combat-and-mining.md](combat-and-mining.md)'s "System events" section for
the resolution path). The event's own catalogue entry carries the rest of an
`asteroid_types.json` type's fields (`graphics`, `size_range`, `speed_range`,
`mine_yield`, optionally `health_multiplier` - scales the asteroid's
size-based health, default 1.0) plus `"name"`/`"description"` for anything
that later surfaces them in UI:

```json
"rich_ore_vein": {
  "kind": "special_asteroid",
  "name": "Rich Ore Vein",
  "graphics": {"shape": "jagged", "color": [255, 195, 60], "vertex_count_range": [10, 14], "jaggedness": 0.45, "spin_speed_range": [-0.8, 0.8]},
  "size_range": [5, 9],
  "speed_range": [0.02, 0.12],
  "mine_yield": 45
}
```

The second `"kind"` is `"pirate_ambush"` - here `"frequency"` is the chance,
rolled on **system entry** (`SpaceScreen._activate_system`) and again every
`"interval_seconds"` thereafter as long as the player keeps flying in that
system without leaving (not per asteroid-field chunk - see
`_build_pirate_ambush_configs` in `game/screens/space_screen/setup.py` and
`_maybe_spawn_pirate_ambush`/`_update_periodic_pirate_ambush` in
`pirates.py`), that a hostile AI ship spawns a configured distance from the
player:

```json
"lone_pirate": {
  "kind": "pirate_ambush",
  "name": "Lone Pirate",
  "pilot": "pirate_lurker",
  "ship_type": "raider_skiff",
  "tribute": 300,
  "spawn_distance": 700,
  "timeout_seconds": 25,
  "interval_seconds": 60
}
```

`"pilot"`/`"ship_type"` are ids the *story* must resolve (`pilots.json`/
`ship_types.json`, exactly like an `ai_ships[]` entry's own `"pilot"`/
`"ship_type"` - not shared by this module, since a pirate's identity and
hull are as story-specific as any other pilot's). `"spawn_distance"` places
it that many world-units from the player at a random angle;
`"timeout_seconds"` is how long the player has, once it appears, before it
turns hostile on its own. `"interval_seconds"` (default 60, see
`pirates.py`'s `DEFAULT_RECHECK_SECONDS`) is how often, while the player
stays in the system, the chance gets rolled again - so parking in a belt to
mine for a long stretch doesn't mean safety after the first roll misses (or
after an earlier encounter resolves); with several `pirate_ambush` entries
in one system's `"events"`, the *shortest* `interval_seconds` among them
sets the recheck cadence. `"tribute"` is **documentation only** - nothing
reads it to drive the encounter; the actual pay/refuse choice and its
`spend_credits:`/`set_flag:` actions live in the pilot's own
`hail_dialogue_tree` (see `config/stories/mining_101/pilots.json`'s
`pirate_lurker` for the worked example) and must be kept in sync with it by
hand.

The rest of the mechanic needs no new machinery, deliberately - see
[combat-and-mining.md](combat-and-mining.md)'s "System events" section:
the pilot's own `one_way_hail` delivers the warning the moment the player's
in range, paying or refusing is a normal hail-dialogue choice
(`spend_credits:<n>` + `set_flag:pirate_tribute_paid:<name>`, or just
`set_flag:hostile_to_player:<name>`), and going hostile - whether from
refusing or the timeout expiring unanswered - is the same
`hostile_to_player:<name>` flag `_sync_hostiles` already watches for any
pilot, so the fight itself runs on existing `CombatRoutine`/weapon-fire code
with nothing pirate-specific in it.

The third `"kind"` is `"derelict_ship"` - a static, unpiloted wreck the
player can fly to and board with **G**. `"frequency"` means exactly what it
does for `"pirate_ambush"` (chance per system entry, rerolled every
`"interval_seconds"` while the player lingers - see
`_build_derelict_configs`/`_maybe_spawn_derelict`/`_update_periodic_derelict`
in `game/screens/space_screen/derelicts.py`), but the config for this kind is
split across **three layers**, not two, since a derelict type's definition
carries more (and more story-specific) data than a pirate ambush's - see
[CONFIG_MODULES.md](../CONFIG_MODULES.md) for the general module/story/system
split this follows:

1. **Module** (`config/modules/system-events/`) owns only the `derelict_ship`
   *mechanism* - the spawn-placement math, the targeting-range gate, boarding,
   and the three possible `"outcome"`s below. It defines no concrete derelict
   types itself (a trap's pirate ship/pilot ids are inherently story-specific).
2. **Story** (`config/stories/{story}/events.json`, merged over the module's
   `events.json` via `story_catalogue` - exactly like `ship_outfits.json`)
   defines each named derelict type in full. Every type carries `"kind":
   "derelict_ship"`, an `"outcome"` (`"loot"` / `"rescue"` / `"trap"`), a
   `"name"`/`"description"`, a `"ship_type"` (a `ship_types.json`/`graphics.json`
   id - what hull renders the wreck, dimmed - see `DerelictShip`), an
   `"interval_seconds"`, and outcome-specific fields:
   ```json
   "adrift_hauler": {
     "kind": "derelict_ship", "outcome": "loot",
     "name": "Adrift Hauler", "ship_type": "courier", "interval_seconds": 150,
     "loot": {"credits_range": [80, 220], "cargo": [{"commodity": "ore", "qty_range": [5, 15]}], "items": ["salvaged_part"]}
   },
   "stranded_skiff": {
     "kind": "derelict_ship", "outcome": "rescue",
     "name": "Stranded Skiff", "ship_type": "mining_skiff", "interval_seconds": 180,
     "payout_range": [150, 400]
   },
   "suspect_wreck": {
     "kind": "derelict_ship", "outcome": "trap",
     "name": "Suspicious Wreck", "ship_type": "raider_skiff", "interval_seconds": 200,
     "explosion_damage": 15, "pirate_ship_type": "raider_skiff", "pirate_pilot": "wreck_raider"
   }
   ```
   `"loot"` (loot outcome): `"credits_range"` (a random amount, one "Credit
   Stash" container), `"cargo"` (a list of `{"commodity", "qty_range"}`, one
   container each), `"items"` (personal `items.json` ids, one container
   each) - see `_build_loot_interior_config`. `"payout_range"` (rescue
   outcome) is the credit range paid when the hitched passenger is dropped
   off. `"pirate_ship_type"`/`"pirate_pilot"` (trap outcome) are ids the
   *story* resolves, exactly like `pirate_ambush`'s own `"pilot"`/`"ship_type"`
   - a fresh pilot with no `hail_dialogue_tree` (there's no toll to
   negotiate; see `mining_101/pilots.json`'s `wreck_raider`), spawned already
   `hostile_to_player:<name>` rather than via the hail/timeout dance.

   A "loot" outcome's generated interior (`_build_loot_interior_config`)
   uses the module's own `"derelict_hull"` culture
   (`config/modules/system-events/cultures.json`) - a dim, damaged-metal
   `floor_color`/`wall_color`, combined with `"space_backdrop": true` for a
   hull breached to the void beyond its one lit room (see this file's
   "Interior geometry" section on the two needing each other, and
   `orbital-std`'s `concourse` interior for another `space_backdrop` +
   culture pairing). A `"rooms"` list with no `"culture"` is silently
   dropped by `LocationScreen` - always give a generated interior a culture
   if it sets `"rooms"`. Each loot container is an ordinary NPC (its
   dialogue keeps working exactly like any other) but rendered as a static
   item glyph via `"icon_shape"`/`"icon_color"` (see "Interior geometry"'s
   NPC icon override) rather than the walking figure, so it reads as an
   object to search, not a person.
   `"explosion_damage"` (trap outcome, default `DERELICT_TRAP_DEFAULT_DAMAGE`
   = 12) is a flat hull-damage burst dealt to the player the instant it
   triggers.
3. **System** (`systems/*.json`) just references a type by id, same
   lightweight idiom as every other event kind:
   ```json
   "events": [
     {"event": "adrift_hauler", "frequency": 0.08},
     {"event": "stranded_skiff", "frequency": 0.05},
     {"event": "suspect_wreck", "frequency": 0.03}
   ]
   ```

**Spawn placement.** A hit spawns the wreck at a random angle from the
player, at a distance that's guaranteed to be both off-screen (even at this
story's minimum zoom) and outside minimap detection range -
`max(half the Space View's diagonal at camera_zoom_min, MINIMAP_RANGE) + 150`
(see `_derelict_spawn_distance`) - so it's never visible the instant it
appears; the player has to actually explore to find it. It then renders as a
static (non-drifting, non-tumbling) `DerelictShip` plus a looping
`SmokeTrail` particle effect (`game/world/smoke_trail.py`, distinct from the
one-shot spark-burst `Explosion`), and can't be cycled/clicked as a target
until the player is within `DERELICT_TARGET_RANGE` (1800 world units) of it
(`targeting.py`'s `_in_target_range`, a general per-object `target_range`
gate any future target type could also opt into) - once in range it also
starts appearing on the minimap. Pressing **G** while it's the current
target, within `DERELICT_BOARD_RANGE` (70 units) and under
`DERELICT_BOARD_SPEED_CAP` (0.4, matching the station/moon landing gate)
boards it, per its `"outcome"`:

- `"loot"`: opens a small generated walkable interior (reusing the ordinary
  `get_interior_screen`/`LocationScreen` machinery via a throwaway
  `LandingSite` wrapper, not a new rendering path) - one room, a
  `return_to_ship` portal, and one NPC "container" per loot-table entry,
  each handing over its reward exactly once via the shared `"earn_credits:"`/
  `"loot_cargo:"`/`"give_item:"` dialogue actions (`game/world/dialogue.py`).
  Walking back out (`SpaceScreen.exit_derelict`) despawns the wreck
  permanently - nothing left to find twice.
- `"rescue"`: resolved instantly, no interior (the fiction is someone
  boarding *your* ship) - sets a `"hitching_passenger"` flag plus that
  passenger's own `"rescue_payout:<event_id>"` amount
  (`Possessions.flags`, so it survives an ordinary save - see
  [SAVE_SYSTEM.md](../SAVE_SYSTEM.md)) and despawns the wreck. Paid out
  (and the flag cleared) the next time the player docks at the station or
  moon (`SpaceScreen._mark_landed`).
- `"trap"`: resolved instantly - a cosmetic `Explosion` plus the flat
  `"explosion_damage"` hull hit, then an already-hostile pirate spawned
  nearby exactly like `pirate_ambush`'s own hostile-spawn construction
  (`Character.for_ai_pilot`), and the wreck despawns.

A derelict (and its encounter state) is **not** persisted across save/load,
same as a `pirate_ambush`'s own spawn - see
[SAVE_SYSTEM.md](../SAVE_SYSTEM.md).

Other event kinds (scannable anomalies, wormholes to normally-disconnected
systems) are meant to land in this same catalogue and the same system-level
`"events"` array later, each with its own `"kind"` and its own
resolution/spawn code - `"frequency"` won't necessarily mean "chance per
asteroid-field chunk" or "chance per system entry" for a kind that fits
neither shape.

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
`seam_rivets` edge ticks) stamps a pack onto every room automatically. Each
room draws as a flat `floor_color` polygon with no trim outline — rooms read
as distinct only by contrast against the surrounding `wall_color` fill. An
interior config with `"space_backdrop": true` fills with the Space View's
black + a `StarField` (own `star_seed` / `star_density`) instead of the flat
wall colour, so the lit floor polygons read as decks open to the void (e.g. the
`orbital-std` module's `concourse` interior). `"seamless": true` drops the room-name
labels and the culture's edge-emphasising `interior_decoration` — so an
interior of overlapping room polygons reads as one open deck rather than a set
of boxes. `"floor_pattern"` fills every room with a
repeating tile clipped to the room polygon (`deck_grid.tessellate` /
`clip_polygon_convex`) — either an inline dict `{"pattern": "hex" | "square" |
"triangle" | "rhombus", "tile": <world units>, "gap": <inset>, "colors":
[[r,g,b], …]}`, or a string naming a `graphics/floor_patterns/<name>.json`
asset resolved through the story's modules (`get_floor_pattern`, see
`game/graphics/story_assets.py`). With no explicit `colors` it cycles three
shades derived from the culture's `floor_color` / `wall_trim_color`.
`the_long_silence`'s station concourses set `seamless` + `space_backdrop` +
a named `floor_pattern` (see `config/stories/the_long_silence/docs/gen/_slice_kit.py`
`station_shell`); the six named patterns themselves live in the
`long-silence-floors` module (see [CONFIG_MODULES.md](../CONFIG_MODULES.md)).
`structures` that name a
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
