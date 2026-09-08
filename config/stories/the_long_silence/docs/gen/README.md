# the_long_silence config generators

These four scripts regenerate the story's config from a compact source of
truth. The generated JSON *is* committed (per the project convention); these
are the tools that produced it. **Run from the repo root**, in this order:

```bash
python config/stories/the_long_silence/docs/gen/gen_systems.py     # kiln / verdance / ossuary / the_span (stub systems)
python config/stories/the_long_silence/docs/gen/gen_assets.py      # per-culture palettes / ships / stations / moons / buildings / outfits (Phase 6.0 stubs)
python config/stories/the_long_silence/docs/gen/retag_assets.py    # point those 4 stub systems at the per-culture asset ids
python config/stories/the_long_silence/docs/gen/gen_halcyon.py     # Phase 6.1: the finished Halcyon slice (owns systems/halcyon.json)
```

- `gen_systems.py` deliberately does **not** write `halcyon.json` - that's a
  finished slice owned by `gen_halcyon.py`. Same for `retag_assets.py` (skips
  halcyon).
- Hand-edits to the generated JSON will be lost on the next run - change the
  generator instead, or promote the file out of the generator's scope (as
  `gen_halcyon.py` did for halcyon).
- 6.2-6.6 each get their own `gen_<system>.py` on the `gen_halcyon.py` model:
  author the culture's ship/station/building designs + a real floor plan +
  roster + anchor mission, and take that `systems/<id>.json` out of
  `gen_systems.py`/`retag_assets.py`.
