# the_long_silence config generators

These scripts regenerate the story's config from a compact source of truth.
The generated JSON *is* committed (per the project convention); these are the
tools that produced it. **Run from the repo root**, in this order:

```bash
python config/stories/the_long_silence/docs/gen/gen_assets.py     # per-culture palettes / ship+station+moon+building catalogue / outfit stubs
python config/stories/the_long_silence/docs/gen/gen_halcyon.py    # 6.1 Halcyon slice   (owns systems/halcyon.json)
python config/stories/the_long_silence/docs/gen/gen_kiln.py       # 6.2 Kiln slice      (owns systems/kiln.json)
python config/stories/the_long_silence/docs/gen/gen_verdance.py   # 6.3 Verdance slice  (owns systems/verdance.json)
python config/stories/the_long_silence/docs/gen/gen_ossuary.py    # 6.4 Ossuary slice   (owns systems/ossuary.json)
python config/stories/the_long_silence/docs/gen/gen_span.py       # 6.5 The Span stub   (owns systems/the_span.json)
python config/stories/the_long_silence/docs/gen/gen_carriers.py   # 6.6 free-carriers pass  (patches every system - MUST run last)
```

- **`gen_assets.py`** writes the whole per-culture asset catalogue (12 palettes,
  18 ships + `ship_types.json`, 6 stations, 6 moons, 18 buildings +
  `building_types.json`, 60 outfit stubs in `graphics.json`). Geometry starts as
  a borrowed placeholder copy with an `identity` brief; each slice below then
  authors its culture's real geometry over the top.
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
- **`gen_carriers.py`** runs last: it authors the patchwork carrier ships +
  wardrobe, then patches a `free_carrier` AI ship + a berth NPC + dressing into
  every already-written `systems/*.json` (idempotent, keyed by name).
- Phase 0's `gen_systems.py` + `retag_assets.py` are retired - every system is
  now owned by a slice script.
