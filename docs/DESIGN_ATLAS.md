# Design Atlases (retired process)

The **old** asset pipeline built the `default` story's art from Python
generators (`docs/atlases/gen_*.py`, `*_kit.py`, `*_outfits.py`) that emitted
self-contained HTML **design atlases**, and from extractors
(`extract_atlas.py`, `apply_parts.py`, `build_person_figure.py`,
`build_figure_signatures.py`) that turned those atlases into committed config
and generated Python.

**That toolchain is gone.** The generators are deleted. What it produced is now
frozen, hand-maintained source:

- `game/world/person_figure.py`, `game/world/figure_signatures.py` — the
  `default` story's Person body + outfit signatures.
- `config/stories/default/graphics.json`, `building_types.json`,
  `ship_types.json`, `cultures.json` — the `default` story's ships, stations,
  buildings, outfits.

Edit those files directly if the `default` story needs a change.

The HTML atlases themselves are kept as visual reference for that art, under
[`config/stories/default/atlases/`](../config/stories/default/atlases/) — open
one in a browser. They include the per-culture kits (Common Kit, Sol Federation,
Vherathi Concord, Drossholt Company, Resin & Rivets), the Grounded Person study,
and the never-shipped proposal mockups (Past the Reach, Kaethar Directorate,
The Vetl, Salt Crows, Deeprock Consortium, Ashfall Rite, Meridian Free Ports,
Theln Drift).

## The current pipeline

New work uses the design-JSON pipeline: **[GRAPHICS_PIPELINE.md](GRAPHICS_PIPELINE.md)**.
Small committed JSON design files → one shared expander
(`game/graphics/expand.py`) → flat parts list, used identically by the game (at
load) and by the atlas viewer (`docs/atlases/pipeline_atlas.py` →
`pipeline-test.html`). There is a vertex editor at
[`docs/atlases/editor.html`](atlases/editor.html). The `graphics_pipeline_test`
story runs on it; `default` does not.
