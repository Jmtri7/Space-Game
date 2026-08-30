# Design Atlases

A **design atlas** is a published visual document (a Claude Artifact) that draws
out a family of the game's assets — ships, outfits, buildings, decorations,
stations — in more detail than the current `config/` JSON expresses, so a human
can look at a whole set at once and decide what to build. It is a **design
tool, not a spec**: nothing in an atlas is wired into the game until someone
does it deliberately, and every plate says so.

Each atlas's HTML **source is committed** under [`docs/atlases/`](atlases/); the
published Claude Artifact is a *render* of that file, at a stable URL. This doc
is the how: how to make one, how to keep it honest, and which ones exist.

## Current atlases

| Atlas | Source | Published URL |
|---|---|---|
| **Resin & Rivets** | [`docs/atlases/resin-and-rivets.html`](atlases/resin-and-rivets.html) | https://claude.ai/code/artifact/36db8620-a17d-4480-97bd-52a2cbb7da4f |
| **Standard Issue** | [`docs/atlases/standard-issue.html`](atlases/standard-issue.html) | https://claude.ai/code/artifact/674398c7-3cb8-49ab-988e-d9b6fe1c01ce |

- **Resin & Rivets** — the two default-story cultures (Vherathi Concord, Drossholt
  Company): ships, stations, outfits, buildings, decorations, interiors. **Fully
  shipped** as of story `1.10.0` — both station interiors and both moon cities are
  rebuilt to the floor-plan model, and **every** ship / station / building /
  furniture plate has had its specimen SVG extracted into that entry's `parts`
  list. That includes every 01·D / 02·D decoration & furniture plate (light-column,
  fern-basin, lounge-pod, resin-bench, concierge-desk, work-light, cargo-stack,
  drum, scrub-tub, plate-bench, trade-counter) and the concord-spire / bloompod /
  gathering-hall / watch-tower / bunker / warehouse building refines. The
  concierge-desk, resin-bench, plate-bench, trade-counter and scrub-tub plates
  were authored fresh (those entries had no plate). No `building_type` in
  `config/stories/default` is on the plain shape + window-dot fallback any more.
  Two gotchas that came out of this: cargo-stack / drum turn one entry into a
  whole *pile*, so the hand-placed crate/barrel clusters in `keplers_reach` were
  thinned to match; and a strokeless atlas shape now extracts with
  `"outline": "none"` so glow dots stop picking up a black ring.
  Every ship plate (01·A / 02·A) also has an explicit drawn **thruster port** at
  each mount, extracted into `parts` (with `fill="none"` ring circles for the
  station ring-modules / docking collars); the exhaust flame stays procedural
  via the `class="flame"` skip. See "Turning a plate into config" for the three
  engine-side rules that keep the flame on the nozzle.
  **As of 2026-08-29 the whole page was redrawn strokeless** — only `<polygon>`
  + `<circle>`, no `stroke`, matching Standard Issue (see "Strokeless specimens"
  below); the Vherathi glass-green edge is now each hull's outline colour, the
  bloom `<filter>` defs are gone, and the six outfits moved to the shared
  legged + armed body. `apply_parts.py` was **re-run** off the strokeless
  atlases (`extract_atlas.py` now folds the strokeless idioms back to compact
  parts — see "Strokeless specimens"), so the in-game `parts` are current with
  these plates again.
- **Standard Issue** — the shared `Person` body (legged redesign + walk cycle,
  **shipped**), the culture-neutral kit, and the Sol Federation "Standard Issue"
  look. The `standard_issue` culture, its ships/station, the **Procyon Gate**
  system, and all of its **buildings + furniture** (issue_block, issue_shed,
  issue_bollard, issue_bench, issue_desk — the last one a fresh plate) shipped
  into `parts` too. The culture-neutral **outfit redraws** (Chapters 02–04) stay
  mockups — the `Person` renderer is colour-key driven, so they need a parts-style
  figure renderer first. So does the 05·D **hazard-chevron floor decal**: the
  `decorations` system has no `parts`, so it's still authored as plain
  hazard-colour floor rects in the system JSON, not literal chevrons.
  The 05·A ship plates carry explicit thruster ports + `class="flame"` exhausts
  too, extracted the same way; the Standard Ring's ring modules and the Issue
  Tender's docking collar extract as transparent-hole ring parts.
  **Every specimen in `standard-issue.html` is drawn with only `<polygon>` and
  `<circle>`, no stroke** (outline = an evenly-offset copy of the shape behind
  it; ovals/curves = many-sided polygons; straight + dashed lines = long thin
  polygons; a ring/torus = radial quad segments so the centre is never covered
  and the hole is genuinely transparent; `<text>` kept only for
  labels/registrations). The figures carry **arms + hands** — shipped into
  `person.py` (a `sleeve_color` sleeve quad per shoulder, counter-swinging on
  the walk cycle) along with the culture-neutral kit becoming the Sol
  Federation look in each system.
  `apply_parts.py` runs off these plates: `extract_atlas.py`'s
  `collapse_strokeless` folds an offset-outline pair back into one part with a
  real `outline`, and a run of `ring_strip` quads back into a
  `{"circle", "width"}` ring — so the in-game part counts stay ~as small as the
  old stroked atlas (station rings extract as transparent-hole ring parts).

### Updating a published atlas

1. Edit the file in `docs/atlases/`.
2. Re-publish it to its **existing** URL — `Artifact` with `url:` set to the row
   above (from any conversation), or just re-publish the same file path in the
   conversation that last published it. Publishing *without* the URL creates a
   separate artifact and orphans the link.
3. Commit the HTML change, and update this table / the notes above if scope or
   URL moved.

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
- **Thruster ports, and the flame that isn't one.** Draw a **port** at every
  `thrusters` mount: a nozzle shape in the culture's `metal_color` (a darker
  derived shade is fine) with its edge colour as a hairline `stroke`. Culture
  cue: Vherathi = a grown asymmetric resin flare, odd-count clusters; Drossholt
  = a bolted rectangular housing with rivet dots, mirrored pairs; Standard Issue
  = a rounded-corner regulation nozzle with an amber hazard chevron over the
  throat (this is the reference the other two adapt). The **exhaust flame** is a
  *separate* shape — or a `<g>` — carrying `class="flame"`: `thrust_color`,
  **narrower** than the port mouth, rooted *inside* the port and drawn *before*
  it so the port occludes its base and only the tail of the jet shows past the
  port's aft edge. Ports are real silhouette and get extracted; `class="flame"`
  shapes are skipped by `extract_atlas.py` (see "Turning a plate into config").
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

## Strokeless specimens: outlines and holes

**Both atlases** (`standard-issue.html` and `resin-and-rivets.html`) are drawn
with **only `<polygon>` and `<circle>`, no `stroke` anywhere** — it maps 1:1 to
what `extract_atlas.py` reads, so plates extract with no black-ring
special-casing. `scratchpad/gen_si.py` bakes Standard Issue from scratch;
`scratchpad/gen_rr.py` imports its primitives + `figure_parts` and (a) rebuilds
the six R&R culture outfits on the shared body, (b) runs a **mechanical
converter** over every other R&R specimen — `path`/`rect`/`ellipse`/`line` →
polygon/circle, each stroke → a mitre outline behind, a `fill:none` stroked
circle → a `ring_strip`, bloom `<filter>` dropped — so the design is preserved
exactly. Two things needed a real technique to look right:

**Outlines — offset the polygon, don't inflate it.** The obvious approach —
copy the shape, push every vertex away from the centroid by `d`, draw that
behind in the outline colour — gives a **top-heavy outline** on any shape
that isn't roughly circular: a tall thin rectangle's end vertices move mostly
vertically, so the outline is thick on the ends and thin on the sides. What
works is a **constant-perpendicular mitre offset**: for each vertex, take the
two adjacent edge directions, average their outward normals to get the mitre
direction `m`, and move the vertex out by `d / (m · n)` where `n` is one
edge's normal (this is the standard mitre-join formula). Clamp `m · n` to
~`0.3` so a sharp corner doesn't shoot a spike. Then sanity-check that the
result actually grew (sum of vertex-distance-from-centroid went up) and flip
the sign if it didn't — that catches winding-order surprises. One extra
`<polygon>` behind the shape, uniform width on every edge. Circles are the
easy case: a bigger circle behind is already uniform.

**Transparent ring holes — build the torus from radial strips.** A single
"keyhole" annulus polygon (outer loop → bridge → reversed inner loop, one
`<polygon>`) technically has a hole, but against the dark viewport it reads as
a *filled dark disc* — indistinguishable from a solid fill, because there's
nothing bright behind it — and the self-touching bridge can fill oddly. The
fix that unambiguously reads as open: build the ring as **N radial quad
segments** (`ring_strip`), each a trapezoid from inner radius to outer radius
over one angular slice. Nothing is ever painted in the centre, so the page's
grid pattern shows straight through and it is visibly a hole. For several
**overlapping** rings on a spine (the Standard Ring station), draw *all* the
outer rims first, then *all* the bodies in one flat colour — the bodies merge
where they overlap, so the modules read as **joined at the intersections**
rather than stacked discs. Same `ring_strip` for the Issue Tender's docking
collar.

**Everything else:** ovals/curves = many-sided polygons; a straight or dashed
line = a long thin polygon (a run of short ones for dashes); a dotted circle
= a ring of small `<circle>` dots; `<text>` is allowed for annotation only
(corner tags, `SF-###` registrations, floor-plan room labels).

**Extraction folds both idioms back.** `extract_atlas.py`'s
`collapse_strokeless` (run automatically; pass `nocollapse` to skip) turns an
offset-outline polygon + fill polygon back into one part with a real
`"outline"` colour, and a run of ≥8 same-colour quads back into one
`{"circle", "width"}` ring per torus (split by edge-adjacency, so a row of
window squares is left alone). Result: `apply_parts.py` off the strokeless
atlas gives part counts within ±1 of the old stroked extraction, with the
station rings as transparent-hole ring parts. The `#888` fallback in
`gen_rr.py` was removed — a `url(#grid)` fill must pass through, or a second
run of the (non-idempotent) converter paints the background solid grey.

## Turning a plate into config

A specimen SVG is mostly polygons/paths/circles, and the engine can consume
that directly: `graphics.json` (ships, `space_stations`) and
`building_types.json` entries take an optional **`parts`** list —
`{"points": [...], "color": ..., "outline": ...}` /
`{"circle": [cx, cy, r], ...}` (filled) or `{"circle": [cx, cy, r], "width":
w}` (a **ring** — a `fill="none"` stroked circle in the plate, hole left
transparent) / `{"line": [...], "width": w, ...}`.
`WorldObject.draw_parts()` renders the list **and nothing else** — a `parts`
list is a *complete* silhouette, so the flat base polygon and the circular
`windows` dots are **not** also drawn under/over it (that just shows the old
shape bleeding past the new one). `local_points` / `shape` / `footprint`
stay authoritative for collision, depth sort, and target-bracket sizing, but
not for drawing. Colours (`color`, and an optional per-part `outline` —
`"none"` to omit it, else the entry-level `outline_color`) are `[r,g,b]`,
`"#rrggbb"`, `"metal"`, `"glass"`, or `"shade:<n>"`. Ship/station part coords
are fractions of `size` / absolute local units respectively; building coords
are absolute local units with y negative going up from the ground anchor.

So a detailed plate can be **extracted rather than re-drawn**: parse the
specimen SVG, flatten its paths to short segments (real cubic/quadratic
bézier sampling; SVG arcs `A` are approximated linearly — avoid them in a
plate you mean to extract), and map atlas-viewBox coords into the entry's
local space (one `(cx, cy, scale, flip)` transform per asset). The
extractor keeps the largest filled polygon as **both** `parts[0]` (the hull
fill, drawn) and a copy in `local_points` (collision only), and lifts that
polygon's `stroke` to the entry's `outline_color`. Every filled sub-shape
keeps its own `stroke` as a per-part `outline`, so the plate's coloured
edges survive into the game rather than collapsing to one black stroke —
and a sub-shape with **no** `stroke` in the SVG is emitted with
`"outline": "none"` (not the entry default), so an atlas glow dot / flat
accent stays un-outlined in game instead of gaining a black ring.
Tooling lives beside the atlas HTML: [`docs/atlases/extract_atlas.py`](atlases/extract_atlas.py)
(one plate → parts JSON) and [`docs/atlases/apply_parts.py`](atlases/apply_parts.py)
(the asset→plate table + targeted JSON injection; run from repo root, it's
idempotent). Add a row to `apply_parts.py`'s `T` table for a new asset.

**The thruster flame is not extracted.** Any specimen shape (or `<g>`) tagged
`class="flame"` is dropped by `extract_atlas.py` — only the drawn **port**
polygon lands in `parts`; the exhaust stays procedural in
`Ship._draw_thrusters()`. Three engine-side things keep the live flame reading
as firing *from* that port (all shipped):

1. **Draw order.** `Ship.draw()` (and `draw_ship_glyph`) draw the flame
   *before* the hull `parts`, so the port occludes its root and only the jet
   aft of the port lip shows.
2. **Width.** The flame half-width is `max(0.6, thruster_width · size)` (game
   units); `thruster_width` is `0.055` for every atlas ship (default `0.09`),
   comfortably under the ~`0.08·size` port-mouth half-width.
3. **Origin.** Each ship's `thrusters` mount is the plate's **port aft-edge
   point** mapped through that entry's `apply_parts.py` transform, so the flame
   starts at the drawn nozzle mouth at any thrust level. These are hand-kept in
   sync — if you move a port in a plate, re-derive its `thrusters` entry
   (`((plate_x − cx)·scale, (plate_y − cy)·scale)`).

## Maintaining an atlas

- **Config changed?** If a ship / outfit / building / culture is added or
  reshaped in `config/`, update the matching plate (or add one) and fix its
  spec block and the "Wiring in" section so they still name real fields.
- **A plate got built?** When an atlas design is actually implemented in
  `config/` or code, either mark that plate done or drop it — an atlas full of
  already-shipped work stops being a design tool. Mention the atlas in the
  commit (`atlas:` prefix) so the next agent knows to reconcile it.
- **Edit the source, then republish.** The HTML in `docs/atlases/` is the master;
  update it and re-publish to the **same URL** (see "Updating a published atlas"
  above) so the table's link keeps working. Only mint a new URL for a genuinely
  new subject. Commit the HTML change with the `atlas:` prefix.
- **Keep the table.** The "Current atlases" table here is the index; a new atlas
  isn't done until its row (source path + URL) exists.

See also: [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) for in-engine drawing
conventions, and the per-culture `theme` strings in
`config/stories/default/cultures.json` for the source rubrics.
