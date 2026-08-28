# Design Atlases

A **design atlas** is a published visual document (a Claude Artifact) that draws
out a family of the game's assets — ships, outfits, buildings, decorations,
stations — in more detail than the current `config/` JSON expresses, so a human
can look at a whole set at once and decide what to build. It is a **design
tool, not a spec**: nothing in an atlas is wired into the game until someone
does it deliberately, and every plate says so.

Atlases live outside the repo (they're Artifacts, not committed files). This doc
is the committed part: how to make one, how to keep it honest, and which ones
currently exist.

## Current atlases

| Atlas | Scope | URL |
|---|---|---|
| **Resin & Rivets** | The two default-story cultures — Vherathi Concord & Drossholt Company: ships, stations, outfits, buildings, decorations, and **interiors** (floor-plan model, edge accents, decoration-placement rules). Refines of what ships today + new concepts. | https://claude.ai/code/artifact/36db8620-a17d-4480-97bd-52a2cbb7da4f |
| **Standard Issue** | The shared `Person` body model (**legged redesign + walk cycle shipped**), the culture-neutral outfits, and a **"Standard Issue" third design language** (civil-authority: ships, station, buildings, decorations, interior — all mockups). | https://claude.ai/code/artifact/674398c7-3cb8-49ab-988e-d9b6fe1c01ce |

Keep this table current. When an atlas is published or its URL changes, edit the
row.

## When to make one

Make a **new** atlas when there's a coherent family of assets that share a
visual language and would benefit from being seen together — a culture, a
faction, a biome, the shared character model. One subject per atlas; if you're
tempted to add a section that doesn't fit the title, that's a second atlas.

**Extend an existing** atlas when the new work is the same subject: a new
Vherathi ship goes into Resin & Rivets, not a new file.

Don't make an atlas for a single asset, or for something that's already fully
described by its JSON — the atlas earns its place by showing *more* than the
config does (silhouette intent, the rule it follows, what it would cost, how it
relates to its siblings).

## Anatomy of an atlas

- **Chapters.** One per sub-family (per culture, per tier). Each opens with an
  **identity spread**: the palette as named hex swatches keyed to their
  `cultures.json` / `graphics.json` source field, and a short **numbered rubric**
  of silhouette directives pulled from the culture's own `theme` string. The
  rubric is the actual deliverable — the drawings are just it, applied.
- **Plates.** One asset each: a **specimen SVG** on the left, and on the right a
  role line, a paragraph of design intent, a **spec block** written in the
  game's own JSON vocabulary (real field names from `ship_types.json`,
  `graphics.json`, `building_types.json`), and a **rules row** listing which
  rubric directives the design leans on.
- **"Not in game" framing.** A standing banner, plus per-plate: a **NEW badge**
  on assets that aren't in `config/stories/<story>` yet; unbadged plates are
  refines of something that already ships. Spec blocks are suggestions, never
  patches.
- **A closing "Wiring in" section.** Which file each category would land in, and
  any save/story-version consequence (adding ship types / outfits changes what
  an old save sees in a shop list — see [SAVE_SYSTEM.md](SAVE_SYSTEM.md)).

## Specimen SVG conventions

Keep every specimen consistent so silhouettes compare directly:

- **Fixed viewBox per specimen type.** `240 × 200` for top-down ships, stations,
  and building/decoration elevations; `160 × 200` (or `120 × 220`) for
  front-view figures. Centre the specimen; keep every shape inside the viewBox.
- **Faint grid** behind the specimen (a low-opacity `<pattern>`), plus a mono
  corner label (`designation · view`) and a scale note (`size N`).
- **Colours come from the palette, never invented.** Pull hull/wall from the
  culture's `metal_color`, glass/windows from `glass_color`, thrust from
  `thrust_color`; figures use the shared body palette or an outfit's `*_color`
  keys. If you need a shade that isn't in the palette, derive it (a darker
  `metal_color` for hull shadow) and label it "derived".
- **Flat bright fills on void-black.** The game renders sprites as flat polygons
  with no bloom — match that. Bright `glass_color` on near-black already reads
  as "lit"; don't fake a glow.
- **Committed dark theme is fine** for a sprite atlas (the sprites are authored
  against black), but paint every colour explicitly so the page holds on any
  host background.

## Hard technical rules (learned the hard way)

An atlas is one long scrolling page with 30+ inline SVGs. Several "nice" web
techniques break badly at that scale — every one of these caused a blank or
unrenderable page during the first build:

- **No SVG blur filters.** `feGaussianBlur` / `filter=` on dozens of elements
  stalls rendering indefinitely (each is an offscreen buffer). Use flat fills.
- **No infinite CSS animations.** A paused background tab freezes an
  `animation-fill-mode: both` at its `from` state — if that state is
  `opacity: 0`, the whole section is invisible. No pulsing glows.
- **No scroll-gated visibility.** No `IntersectionObserver` reveal, no
  `.thing { opacity: 0 }` waiting for JS. Content must render fully with zero
  JavaScript.
- **No `background-attachment: fixed`** and **no `backdrop-filter`** — both
  repaint the whole viewport on every scroll frame and can leave the page
  unable to composite.
- **`<meta charset="utf-8">`** at the top, or em-dashes and quotes render as
  mojibake.
- Prefer no `<script>` at all. If you must, the page has to be correct without
  it.

## Maintaining an atlas

- **Config changed?** If a ship / outfit / building / culture is added or
  reshaped in `config/`, update the matching plate (or add one) and fix its
  spec block and the "Wiring in" section so they still name real fields.
- **A plate got built?** When an atlas design is actually implemented in
  `config/` or code, either mark that plate done or drop it — an atlas full of
  already-shipped work stops being a design tool. Mention the atlas in the
  commit (`atlas:` prefix) so the next agent knows to reconcile it.
- **Republish, don't re-create.** Update the existing Artifact (same URL) so the
  link in the table above keeps working. Only make a new URL for a genuinely
  new subject.
- **Keep the table.** The "Current atlases" table here is the index; a new atlas
  isn't done until its row exists.

See also: [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) for in-engine drawing
conventions, and the per-culture `theme` strings in
`config/stories/default/cultures.json` for the source rubrics.
