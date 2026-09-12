# Shared Config Modules

Config used to be strictly per-story: everything under
`config/stories/{story}/`, nothing shared, resolved by hardcoded
`f"config/stories/{story}/..."` paths. A story may now **opt into shared
modules** so several stories draw on one copy of an asset kit.

Source of truth for the resolver: [`game/config_source.py`](../game/config_source.py).

## Declaring modules

`story.json`:

```json
{
  "id": "the_long_silence",
  "name": "The Long Silence",
  "modules": ["figures-human", "audio-core"],
  ...
}
```

Each name is a directory `config/modules/<name>/` whose subtree **mirrors a
story's own** — `graphics/body/*.json`, `ship_types.json`, `audio.json`, and
so on. Order matters: **earlier modules win** over later ones, and the story
always wins over every module.

Each module carries a `module.json`:

```json
{ "name": "figures-human", "version": "1.0.0", "description": "...",
  "modules": ["figures-base"] }
```

### Modules may depend on other modules

`module.json`'s own `"modules"` list works exactly like a story's.
`config_source.resolved_modules(story)` flattens the whole tree: a depth-first,
pre-order walk (a module, then its own dependencies, then the story's later
modules), de-duplicated keeping the **first** occurrence. The precedence
contract is unchanged — the story always wins, and an earlier-listed module (or
dependency) wins over a later one. A dependency **cycle raises `ValueError`**
naming the chain.

`story_modules(story)` still returns only the story's *direct* list (it seeds
the walk); everything else — `_search_roots`, `story_catalogue`, `story_meta`,
`module_versions` — consumes `resolved_modules`.

## Two resolution modes

| Kind of file | Resolver | Rule |
|---|---|---|
| **Per-name pipeline files** — `graphics/<kind>/<name>.json` (ships, stations, bodies, articles, sets, palettes, faces, collision, interiors, decorations, floor_patterns) | `config_source.story_path(story, *relparts)` | First existing of `story/<rel>`, then `modules/<m>/<rel>` in declared order. Whole-file override: a story shadows a kit file by dropping its own copy at the same path. Falls back to the story path if nobody has it, so "missing file" is unchanged. |
| **Flat `{id: entry}` catalogues** — `graphics.json`, `cultures.json`, `commodities.json`, `items.json`, `ship_types.json`, `ship_outfits.json`, `building_types.json`, `asteroid_types.json`, `events.json`, `pilots.json`, `missions.json`, `factions.json`, `endings.json`, `graphics/materials.json`, `audio.json` | `config_source.story_catalogue(story, filename)` | Deep-merge: every module's dict layered under the story's, entry by entry (nested dicts merge, lists/scalars replace). A story overrides or extends one entry without copying the file. Result is cached and shared — treat read-only, exactly like `load_json`. |

`systems/*.json` is **not** shared — inherently story-specific — and loads by
direct path. `story.json` is a special case: a module may ship a partial
`story.json` (tuning blocks only) that `config_source.story_meta()` merges
*under* the real story's, so `get_story()` sees module defaults with every
story key still winning.

## Current modules

| Module | Provides | Used by |
|---|---|---|
| `figures-human` | The walk rig, masc/femme human bodies, generic wardrobe articles, faces, common decorations/collision/buildings, base `materials.json`. `the_long_silence` keeps ~114 faction-specific files locally but **no kit shadows** — its 10 hand-tuned kit files (`human_femme`, `draw_order`, `eyes_almond` / `lips_full` / `nose_soft`, `badge` / `buttons` / `hair_short` / `pants` / `stand_collar`) replaced the module copies in `1.1.0`, so both consuming stories now share them. (The old module `human_femme`/`draw_order` carried extra leg-pants fitting curves/layers that nothing referenced; recover from git if ever needed.) | `the_long_silence`, `the_whisper_line` |
| `orbital-std` | The **flat-catalogue** kind of sharing (`graphics.json`/`cultures.json`/`building_types.json`/`ship_types.json`, not the per-name `graphics/<kind>/<name>.json` kind `figures-human` provides) — the `orbital_std`/`regolith_std` cultures, the `courier` ship, the `trade_ring` station, `regolith_moon`, and a small settlement building set. Once shared with the design-JSON pipeline's now-retired reference/test story, this is the only home for that art. | `the_whisper_line` |
| `audio-core` | The default `SoundBoard` recipes and the two ambient music loops, as data (`audio.json`). See [SOUND.md](SOUND.md). | all four stories |
| `ships-core` | The standard ship-equipment kit — `ship_outfits.json` (weapons/engines/utility) and `asteroid_types.json` — that `default` and `the_long_silence` had entry-for-entry identical. Ship *hulls* stay per-story (no two stories share one). | all four stories |
| `common-goods` | `items.json` — the personal inventory items every story carries (`repair_kit`, `medkit`, `star_chart`, `engraved_flask`). | all four stories |
| `story-defaults` | A partial `story.json`: camera + interior zoom bounds, `walking_speed`, the `jump` drive constants. Merged under each story's own `story.json`. | all four stories |
| `system-events` | `events.json` — the shared catalogue a system's `"events"` block references by id (see [architecture/config-formats.md](architecture/config-formats.md)'s "System events"). Three kinds so far: `"special_asteroid"` (`rich_ore_vein`) and `"pirate_ambush"` (`lone_pirate`, a story-authored pilot demands tribute or fights — see [architecture/combat-and-mining.md](architecture/combat-and-mining.md)), both defined directly in this module's own `events.json`. `"derelict_ship"` instead follows a **three-layer split** (below) — this module owns only the mechanism, no concrete derelict types. More kinds (anomalies, wormholes) land here later, each with its own spawn code. | `mining_101` |
| `long-silence-floors` | The **per-name pipeline file** kind of sharing — six `graphics/floor_patterns/<name>.json` tessellation specs (`authority`/`combine`/`drift`/`vigil`/`warden`/`carrier`), one per `the_long_silence` culture prefix. A station's `floor_pattern` config is the name string; `station_shell()` in `docs/gen/_slice_kit.py` picks it per culture. Extracted (2026-09-11) from an inline `_STATION_STYLE` dict so the texture is a referenceable asset file instead of data baked into the generator. | `the_long_silence` |

### A three-layer pattern: module mechanism, story catalogue, system reference

Most flat catalogues (`ship_outfits.json`, `asteroid_types.json`, the
`system-events` module's own `special_asteroid`/`pirate_ambush` entries) are
two-layer: the module defines concrete, reusable entries, and a story either
uses them as-is or adds/overrides its own via a same-named story-scoped file
(`story_catalogue`'s ordinary merge). That's not always the right split —
`"derelict_ship"` (the `system-events` module's third event kind) needs a
third layer, since its concrete entries reference ids (a trap's pirate
ship/pilot) that are inherently story-specific and don't belong baked into a
shared module:

1. **Module** (`config/modules/system-events/`) defines the general
   mechanism only — what a `"derelict_ship"` kind *means* (spawn placement,
   targeting-range gate, boarding, the three possible outcomes) — and no
   concrete derelict types of its own.
2. **Story** (`config/stories/{story}/events.json`, merged over the module's
   `events.json` via the same `story_catalogue` two-layer merge every other
   flat catalogue uses) defines the actual named derelict types — their
   `"outcome"`, ship/pilot references, loot table or payout range. This is
   the layer that would otherwise have to live in the module if derelict
   types were two-layer like everything else.
3. **System** (`systems/*.json`) references a type by id in its `"events"`
   array, the same lightweight `{"event": <id>, "frequency": ...}` idiom
   every other event kind already uses — letting several systems in one
   story reuse the same derelict-type definition.

See [architecture/config-formats.md](architecture/config-formats.md)'s
"System events" section for the full field-by-field shape, and
`config/stories/mining_101/events.json` for the worked example
(`adrift_hauler`/`stranded_skiff`/`suspect_wreck`). A future config need with
the same "module mechanism, story-specific concrete data" shape should
follow this same three-layer split rather than stretching the two-layer
override pattern to fit.

## How the loaders use it

- `game/utils.py` — every `get_*` catalogue accessor calls `story_catalogue`.
  `clear_json_cache()` also clears the merged-catalogue cache.
- `game/graphics/story_assets.py` — `_load()` resolves via `story_path`;
  `_materials()` merges via `story_catalogue`.
- `game/audio/sound_board.py` / `music.py` — load `audio-core/audio.json` at
  construction; `SpaceScreen.__init__` then calls `sound_board.apply_story()`
  / `music.apply_story()` to layer a story's own `audio.json`.

## Save compatibility

A save records `game_state["module_versions"]` (`{name: version}` from each
module's `module.json`) — the **full resolved tree**, dependencies included.
On load, `main.py`'s
`warn_if_module_version_mismatch()` warns — non-blocking, alongside the story
version check — when a module the story now uses has changed version since the
save. **Bump a module's `module.json` version** whenever a change to it would
make an existing save's stored state mean something different (the same
criteria as bumping `story.json`'s version — see
[SAVE_SYSTEM.md](SAVE_SYSTEM.md#story-versioning)). A module change affects
*every* story that lists it, so bump deliberately.

## Gotchas

- The vertex editor's **Workspace** panel
  ([GRAPHICS_EDITOR.md](GRAPHICS_EDITOR.md)) lists every story *and* every
  module and lets you open an asset from either. Pick the module, not a
  consuming story, when the fix belongs to the shared kit — otherwise you write
  a story-local copy that shadows the module for that one story. Under a story,
  each inherited asset is tagged with the module it resolves from and each
  header carries a `depends on:` line linking to those modules, so you can jump
  straight to the kit. It also has **new story… / new module…** buttons (needs
  the repo open read-write).
- `story_catalogue` returns a cached, shared dict. Callers that mutate an
  entry already `dict(...)`-copy it first (same contract as `load_json`);
  keep it that way.

## Adding a module / extending sharing

1. `mkdir config/modules/<name>/`, add `module.json` (with its own
   `"modules": [...]` if it builds on another kit).
2. Move the shared files in, mirroring the story subtree.
3. Delete the now-redundant per-story copies (keep any a story deliberately
   customises — they shadow the module).
4. Add `"<name>"` to each consuming story's `story.json` `"modules"`.
5. `python run_tests.py`, then run each consuming story in-game
   ([WORKFLOW.md](WORKFLOW.md)) and eyeball the affected art/audio.

`commodities.json` is deliberately still per-story — the two real stories'
economies barely overlap (only `ore`, and its text differs).
