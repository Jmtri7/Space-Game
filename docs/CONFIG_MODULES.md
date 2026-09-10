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
{ "name": "figures-human", "version": "1.0.0", "description": "..." }
```

## Two resolution modes

| Kind of file | Resolver | Rule |
|---|---|---|
| **Per-name pipeline files** — `graphics/<kind>/<name>.json` (ships, stations, bodies, articles, sets, palettes, faces, collision, interiors, decorations) | `config_source.story_path(story, *relparts)` | First existing of `story/<rel>`, then `modules/<m>/<rel>` in declared order. Whole-file override: a story shadows a kit file by dropping its own copy at the same path. Falls back to the story path if nobody has it, so "missing file" is unchanged. |
| **Flat `{id: entry}` catalogues** — `graphics.json`, `cultures.json`, `commodities.json`, `items.json`, `ship_types.json`, `ship_outfits.json`, `building_types.json`, `asteroid_types.json`, `pilots.json`, `missions.json`, `factions.json`, `endings.json`, `graphics/materials.json`, `audio.json` | `config_source.story_catalogue(story, filename)` | Deep-merge: every module's dict layered under the story's, entry by entry (nested dicts merge, lists/scalars replace). A story overrides or extends one entry without copying the file. Result is cached and shared — treat read-only, exactly like `load_json`. |

`systems/*.json` is **not** shared — inherently story-specific — and loads by
direct path. `story.json` is a special case: a module may ship a partial
`story.json` (tuning blocks only) that `config_source.story_meta()` merges
*under* the real story's, so `get_story()` sees module defaults with every
story key still winning.

## Current modules

| Module | Provides | Used by |
|---|---|---|
| `figures-human` | The walk rig, masc/femme human bodies, generic wardrobe articles, faces, common decorations/collision/buildings, base `materials.json`. The `graphics_pipeline_test` and `the_long_silence` figure kits were byte-identical here; `the_long_silence` keeps ~114 faction-specific files locally (and its 10 tuned kit files, which shadow the module's). | `the_long_silence`, `graphics_pipeline_test` |
| `audio-core` | The default `SoundBoard` recipes and the two ambient music loops, as data (`audio.json`). See [SOUND.md](SOUND.md). | all three stories |
| `ships-core` | The standard ship-equipment kit — `ship_outfits.json` (weapons/engines/utility) and `asteroid_types.json` — that `default` and `the_long_silence` had entry-for-entry identical. Ship *hulls* stay per-story (no two stories share one). | all three stories |
| `common-goods` | `items.json` — the personal inventory items every story carries (`repair_kit`, `medkit`, `star_chart`, `engraved_flask`). | all three stories |
| `story-defaults` | A partial `story.json`: camera + interior zoom bounds, `walking_speed`, the `jump` drive constants. Merged under each story's own `story.json`; `graphics_pipeline_test` keeps its zoomed-in camera overrides and still inherits `jump`. | all three stories |

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
module's `module.json`). On load, `main.py`'s
`warn_if_module_version_mismatch()` warns — non-blocking, alongside the story
version check — when a module the story now uses has changed version since the
save. **Bump a module's `module.json` version** whenever a change to it would
make an existing save's stored state mean something different (the same
criteria as bumping `story.json`'s version — see
[SAVE_SYSTEM.md](SAVE_SYSTEM.md#story-versioning)). A module change affects
*every* story that lists it, so bump deliberately.

## Gotchas

- The vertex editor ([GRAPHICS_EDITOR.md](GRAPHICS_EDITOR.md)) writes under
  `config/stories/<story>/graphics/`. Editing a file that actually lives in a
  module writes a **story-local copy** that then shadows the module for that
  story only — usually not what you want. Edit the file in
  `config/modules/<name>/graphics/` directly, or delete the accidental
  story-local copy afterward.
- `story_catalogue` returns a cached, shared dict. Callers that mutate an
  entry already `dict(...)`-copy it first (same contract as `load_json`);
  keep it that way.

## Adding a module / extending sharing

1. `mkdir config/modules/<name>/`, add `module.json`.
2. Move the shared files in, mirroring the story subtree.
3. Delete the now-redundant per-story copies (keep any a story deliberately
   customises — they shadow the module).
4. Add `"<name>"` to each consuming story's `story.json` `"modules"`.
5. `python run_tests.py`, then run each consuming story in-game
   ([WORKFLOW.md](WORKFLOW.md)) and eyeball the affected art/audio.

`commodities.json` is deliberately still per-story — the two real stories'
economies barely overlap (only `ore`, and its text differs).
