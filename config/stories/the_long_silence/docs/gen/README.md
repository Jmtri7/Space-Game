# the_long_silence config generators

These scripts regenerate the story's config from a compact source of truth.
The generated JSON *is* committed (per the project convention); these are the
tools that produced it. **Run from the repo root**, in this order:

```bash
python config/stories/the_long_silence/docs/gen/gen_halcyon.py    # 6.1 Halcyon slice   (owns systems/halcyon.json)
python config/stories/the_long_silence/docs/gen/gen_kiln.py       # 6.2 Kiln slice      (owns systems/kiln.json)
python config/stories/the_long_silence/docs/gen/gen_verdance.py   # 6.3 Verdance slice  (owns systems/verdance.json)
python config/stories/the_long_silence/docs/gen/gen_ossuary.py    # 6.4 Ossuary slice   (owns systems/ossuary.json)
python config/stories/the_long_silence/docs/gen/gen_span.py       # 6.5 The Span stub   (owns systems/the_span.json)
python config/stories/the_long_silence/docs/gen/gen_carriers.py   # 6.6 free-carriers pass  (patches every system)
python config/stories/the_long_silence/docs/gen/gen_act2.py       # Phase 7 - Act II dispatch missions (merges into missions.json; run last)
```

The chain runs clean end to end and regenerates everything byte-identical
(`systems/`, `missions.json`, `graphics.json`, `building_types.json`,
`ship_types.json`, `pilots.json`, `graphics/articles/`, ...). **No `git checkout`
dance any more** — as of story `0.19.0`, `write_article()` (in `_slice_kit.py`,
mirrored in `gen_halcyon.py`) preserves any hand-tuned per-region `geometry`
already on disk, matching by `(group, note)`. So: edit article vertices in
`config/editor.html`, commit the JSON, and a later full gen re-run keeps that
geometry while still re-authoring identity / palette / colour / which regions
exist. To force a full regen of one article's geometry, delete its JSON first.
A region the generator *adds or renames* starts from the builder's rough
placeholder until it's edited.

- **`gen_assets.py` is retired** (deleted 2026-09-09, alongside Phase 0's
  `gen_systems.py` / `retag_assets.py`). It was the 6.0 bootstrap that stamped
  out placeholder per-culture stubs; slices 6.1-6.6 have since authored real
  geometry over every one of those stubs, so re-running it would only overwrite
  finished art with placeholders. It also broke on the config-module split
  (`graphics/palettes/civilian.json` moved into `figures-human`). The per-culture
  catalogue — `ship_types.json`, `building_types.json`, `graphics.json` ships/
  stations/moons/outfits, `graphics/palettes/` — is now slice-owned + hand-
  maintained. Its historical form is in git (commit `eb380c7` era).
- **`_slice_kit.py`** — shared helpers the `gen_<system>.py` scripts import
  (file IO, the connected-floor-plan builder, the free-drawn wardrobe-article
  builders). Not run directly.
- **Each `gen_<system>.py`** authors that culture's ship/station/building design
  JSON, a real interior floor plan + NPC roster + hail dialogue, a bespoke
  wardrobe (real `articles/` + culture `sets/`, replacing the `<pfx>_dress`
  palette recolours), an anchor mission, and fleshed pilots - and **owns** its
  `systems/<id>.json` outright (hand-edits there are lost on the next run).
  `gen_span.py` is lighter: the Span is an Act I stub (stays beacon-locked, no
  anchor mission, wardrobe deferred to Act II) but its exterior/interior art is
  authored.
- **`gen_carriers.py`**: authors the patchwork carrier ships + wardrobe, then
  patches a `free_carrier` AI ship + a berth NPC + dressing into every
  already-written `systems/*.json` (idempotent, keyed by name).
- **`gen_act2.py`** (Phase 7) runs last: merges the Act II courier missions
  (`carrier_relief_run`, `combine_evacuation`) into `missions.json`. These are
  handed out by `dispatches.json` (the faction inbox), not an NPC, and use the
  generic gameplay-event flags so they need no new characters. `dispatches.json`
  itself is hand-maintained (not generated).
- Phase 0's `gen_systems.py` + `retag_assets.py` and 6.0's `gen_assets.py` are
  retired - every system and every per-culture asset is now owned by a slice
  script or hand-maintained.
