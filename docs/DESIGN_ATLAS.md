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

## Restructure in progress

The three-atlas split (Resin & Rivets = 2 cultures, Standard Issue = body +
Federation) is being pulled apart into **one atlas per subject**, each with
full coverage (outfits · ships · stations · decorations · city & station
layouts). Shared page shell lives in
[`docs/atlases/atlas_shell.py`](atlases/atlas_shell.py) (`css()` + `DEFS`),
per-atlas accent colour.

| atlas | from | holds | state |
|---|---|---|---|
| **Common Kit** | Standard Issue ch. 01–04 | shared `Person` body (cinched-waist anatomy + accessory slot map) + the culture-neutral civilian / service outfits, each with a role detail | **built** — `gen_common.py` + `common_kit.py` |
| **Sol Federation** | Standard Issue ch. 05 | the `standard_issue` culture: issued ships, Standard Ring station, buildings, hazard decal, spine-and-bays interior + Federation crew/command outfits (visor-slit / stencil signature) | **built** — `gen_split.py` + `federation_outfits.py` |
| **Vherathi Concord** | Resin & Rivets, Vherathi half | 6 grown hulls, reef station, 4 buildings, 6 furniture/deco, 4 layouts + outfits with asymmetric eye-bubble helm clusters + resin-bead glow | **built** — `gen_split.py` + `vherathi_outfits.py` |
| **Drossholt Company** | Resin & Rivets, Drossholt half | 5 bolted hulls, welded station, 4 buildings, 7 furniture/deco, 2 layouts + outfits with riveted patch-plates + box respirator | **built** — `gen_split.py` + `drossholt_outfits.py` |
| **Past the Reach** | (unchanged) | the seven *proposed* cultures — mockup only | done |

**All four splits are built.** `gen_split.py` pulls the ship / station /
building / furniture / layout SVGs **verbatim** from `standard-issue.html` /
`resin-and-rivets.html` via `atlas_plates.grab` (they're already
detailed and extracted-to-`parts` — no reason to redraw), and adds the new
signature outfits. **`standard-issue.html` and `resin-and-rivets.html` are now
superseded** — keep them until their generators (`gen_rr.py`, and the
non-`figure_parts` half of `gen_si.py`) are pruned, but the four new atlases
are the record. `gen_si.figure_parts` / `FIG_*` / `figure_shapes` stay — they
feed `build_person_figure.py`.

**Outfit signatures ship in-game.** Each `*_outfits.py` signature function's
pre/post SVG is baked by
[`build_figure_signatures.py`](atlases/build_figure_signatures.py) into
`game/world/figure_signatures.py` (part lists in Person game units, literal
`#rrggbb` colours). A `graphics.json` outfit opts in with a `"signature": "<id>"`
key; `Person.draw()` emits the `pre` parts behind the body and `post` over it.
Re-run the baker after editing a signature function; `graphics.json` and the
default story's system NPC rosters carry the `"signature"` keys and Federation
crew entries. `tests/test_helpers.py` asserts every referenced signature is
baked.

**Body: the cinched waist.** `figure_parts` now pinches the torso to a waist
about halfway up the standing figure and flares back to a hip nearly as wide
as the chest — an hourglass whether or not an outfit covers it. **Every belt,
sash end, hip pouch and torch anchors at the waist**, not the hip line. Baked
into `game/world/person_figure.py` via `build_person_figure.py`, so the game
has it; `past-the-reach.html` shows it; `standard-issue.html` /
`resin-and-rivets.html` pick it up on their next regenerate.

## Current atlases

| Atlas | Source | Published URL |
|---|---|---|
| **Common Kit** | [`docs/atlases/common-kit.html`](atlases/common-kit.html) | https://claude.ai/code/artifact/801028b3-1b57-4883-b19a-ce6bdac213dc |
| **Sol Federation** | [`docs/atlases/sol-federation.html`](atlases/sol-federation.html) | https://claude.ai/code/artifact/fedf43de-02d7-4251-8c64-6263442678eb |
| **Vherathi Concord** | [`docs/atlases/vherathi-concord.html`](atlases/vherathi-concord.html) | https://claude.ai/code/artifact/d352d82f-d0f3-4165-94c6-32e14415de1f |
| **Drossholt Company** | [`docs/atlases/drossholt-company.html`](atlases/drossholt-company.html) | https://claude.ai/code/artifact/5124a8b1-4c9e-4c3c-b341-9c778e9d13d7 |
| **Past the Reach** | [`docs/atlases/past-the-reach.html`](atlases/past-the-reach.html) | https://claude.ai/code/artifact/d822ff88-5b66-4203-8b3c-e9c7459052fb |
| **Kaethar Directorate** | [`docs/atlases/kaethar-directorate.html`](atlases/kaethar-directorate.html) | https://claude.ai/code/artifact/87a840a9-b921-482c-b14a-351dd1353469 |
| **The Vetl** | [`docs/atlases/the-vetl.html`](atlases/the-vetl.html) | https://claude.ai/code/artifact/c046ebc1-2d81-4160-b956-0cc4e4312fc6 |
| **The Salt Crows** | [`docs/atlases/salt-crows.html`](atlases/salt-crows.html) | https://claude.ai/code/artifact/bca33565-f999-45cf-b8b2-55eeff986310 |
| **Deeprock Mining Consortium** | [`docs/atlases/deeprock-consortium.html`](atlases/deeprock-consortium.html) | https://claude.ai/code/artifact/d24ab6df-142b-4012-9b41-0f12b0720937 |
| **The Ashfall Rite** | [`docs/atlases/ashfall-rite.html`](atlases/ashfall-rite.html) | https://claude.ai/code/artifact/b123b6e5-653d-42f9-b9c5-adc146af735d |
| **The Meridian Free Ports** | [`docs/atlases/meridian-free-ports.html`](atlases/meridian-free-ports.html) | https://claude.ai/code/artifact/150329e8-d18e-40f8-93ee-092f060f33fc |
| **The Theln Drift** | [`docs/atlases/theln-drift.html`](atlases/theln-drift.html) | https://claude.ai/code/artifact/13308051-79e6-4c1c-a61c-820ea9b5f962 |
| ~~Resin & Rivets~~ *(superseded by Vherathi Concord + Drossholt Company)* | [`docs/atlases/resin-and-rivets.html`](atlases/resin-and-rivets.html) | https://claude.ai/code/artifact/36db8620-a17d-4480-97bd-52a2cbb7da4f |
| ~~Standard Issue~~ *(superseded by Common Kit + Sol Federation)* | [`docs/atlases/standard-issue.html`](atlases/standard-issue.html) | https://claude.ai/code/artifact/674398c7-3cb8-49ab-988e-d9b6fe1c01ce |

- **Common Kit** — the shared `Person` body and the culture-neutral outfits,
  split out of Standard Issue. **Body chapter:** a labelled cinched-waist
  anatomy plate + the accessory slot map (both **shipped** — `person_figure.py`
  carries the waist / rounded shoulders / belts-at-waist). **Outfit chapters:**
  ~15 `graphics.json` civilian / service outfits (space suit, flight suit,
  mechanic, dockworker, miner, security, station command, marshal, medic,
  surgeon, researcher, civilian, smuggler, ranger, bounty hunter) redrawn on
  the new body, each with a **role-distinguishing detail** — a mechanic's tool
  belt + lamp, a dockworker's hi-vis tabard, a smuggler's hood, a surgeon's
  mask. **Shipped** — the role details are now baked as
  `game/world/figure_signatures.py` (via `build_figure_signatures.py`) and
  `Person.draw()` renders them from each outfit's `"signature"` key.
  Built by [`gen_common.py`](atlases/gen_common.py) +
  [`common_kit.py`](atlases/common_kit.py). Accent: steel-cyan `#8fb9c8`.

Both atlases carry a **Naming** section per culture (01·N / 02·N / 05·N),
sourced from each culture's `naming` field in `cultures.json` and applied to
the default story's three systems as of story `1.13.0` (Aurelith / Vaelune
Ring / Ossira for the Vherathi; Kadmor Reach / Kadmor Yard / Skragg for the
Drossholt; Procyon Gate kept, minor body names catalogued for the Federation).
Internal `system_id` file names (`sol_alpha.json` etc.) are unchanged for save
compatibility.

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
  `apply_parts.py` runs off these plates: `extract_atlas.py` keeps every
  polygon/circle (an offset-outline shape stays its own part, drawn behind its
  fill), and `collapse_strokeless` folds only a `ring_strip` quad run back into
  a `{"circle", "width"}` ring (station rings extract as transparent-hole ring
  parts). The engine draws the list verbatim, no synthesised outline.
- **Past the Reach** — a **mockup-only** proposal: **seven** *proposed* cultures
  for the edge of the map — Deeprock Mining Consortium, the Ashfall Rite
  (Kessari), the Meridian Free Ports, the Theln Drift, and three brand-new ones:
  **the Kaethar Directorate** (cold militarist), **the Vetl** (shamanistic,
  creature-ships), **the Salt Crows** (pirate scavengers). **Nothing here is in
  `config/`** — no `cultures.json` entries, no ship types, no outfits. Per
  chapter: an identity spread (proposed palette swatches + numbered rubric) and
  two plates — a detailed exotic-silhouette top-down **ship** and a **signature
  outfit** (the shared `figure_parts` body + standard kit, then *signature*
  geometry no other culture uses — an ember-slit ceramic mask, an antler
  headdress, an eye-bubble helm). An opening "Signature kit" section carries the
  same idea back to the three **shipped** cultures (Vherathi eye-bubble helm,
  Drossholt riveted patch-plates, Federation visor-slit + stencil) as redesign
  recommendations that would land in Resin & Rivets / Standard Issue, not here.
  Built by [`gen_frontier.py`](atlases/gen_frontier.py) +
  [`frontier_ships.py`](atlases/frontier_ships.py) +
  [`frontier_outfits.py`](atlases/frontier_outfits.py) (all import the strokeless
  primitives + `figure_parts` from `gen_si`), so the ships obey the "only
  `<polygon>` + `<circle>`" rule and could be extracted into `parts`. The outfit
  *signature* pieces are new geometry, so those redraws wait on a parts-style
  figure renderer — the fix would be a `figure_signature` table keyed by culture,
  landing all ten (shipped included). Accent is amber (`#d9a441`). If any culture
  here gets built, split it out — a shipped culture belongs in its own atlas
  (or Resin & Rivets' successor), not in a proposals file.

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
works is a **constant-perpendicular offset** (`offset_poly` in `gen_si.py`):
push each *edge* out along its own outward normal by `d`, then close the gap
this opens at each corner. The engine has no equivalent step — it draws
`offset_poly`'s output as a plain part, so the plate and the game agree by
construction. The corner treatment is the same choice SVG makes with
`stroke-linejoin` + `stroke-miterlimit`:

- **Mitre** (default): extend both offset edges until they intersect — one
  sharp point that keeps the corner's original shape. Vertex moves out along
  the angle bisector `m` by `d / (m · n)`, `n` = an adjacent edge's normal
  (`m · n` = `cos(½ the corner's turn)`). This is right for rectangles,
  panels, gently-faceted hulls — a 90° corner stays a 90° corner, just bigger.
- **Bevel** (fallback): `d / (m · n)` blows up as the corner sharpens
  (`→ ∞` at a needle point), so when it would exceed `miter_limit · d`
  (`miter_limit = 2.0`, i.e. corners sharper than ~60°) emit **one point per
  edge** instead — a short flat cap ~`d` beyond the tip. A blade, a thruster
  nozzle, a tapered wedge caps cleanly rather than shooting a long spike.

Offset direction comes from the polygon's **signed area** (winding), not a
"did it grow? then flip" guess on one vertex. One extra `<polygon>` behind the
shape, uniform width on every edge; a bevelled corner just adds a vertex.
Circles are the easy case: a bigger circle behind is already uniform.

*Authoring implication:* a sharp point in a plate is fine — it caps, it
doesn't spike. And because the engine draws exactly these polygons (it never
re-derives an outline), the plate predicts the game 1:1 — including the
outline's thickness, which scales with the shape rather than being a
fixed-pixel border.

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

**Extraction keeps the outline as a real part.** `extract_atlas.py` emits the
offset-outline polygon/circle and the fill it sits behind as **two separate
parts**, exactly as the plate draws them — it does **not** fold them into an
`"outline"` colour key. `collapse_strokeless` folds only the one genuinely
wasteful idiom: a torus of dozens of tiny radial quads → one
`{"circle", "width"}` ring (the engine re-expands it to the same quads). The
`#888` fallback in `gen_rr.py` was removed — a `url(#grid)` fill must pass
through, or a second run of the (non-idempotent) converter paints the
background solid grey.

**The engine draws the parts list verbatim** — `WorldObject.draw_parts` (and
its UI twin `ui_theme._draw_glyph_parts`, and `Person.draw` off
`person_figure.py`) render each polygon/circle filled, back to front, with
**no synthesised outline of any kind** — no `pygame` stroke, no runtime
offset. The outline is already its own slightly-larger polygon/circle part in
the list, so it scales with the shape exactly as the plate drew it, instead
of a fixed-pixel border that (on a small ship like `vherathi_skiff`, size 10)
grew fat enough to swallow the nose. Rings render as `_ring_quads` (a strip),
lines as a thin quad. The in-game silhouette matches the plate
primitive-for-primitive.

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

**The Person body is extracted too, from `gen_si.figure_parts`.**
`figure_parts()` (in [`docs/atlases/gen_si.py`](atlases/gen_si.py)) is the
single generator for every Standard Issue crew/contact specimen; it carries
`_grp()` / `_gate()` markers that tag each shape with an animation group
(`body` / `arm_l` / `arm_r` / `hand_l` / `hand_r` / `leg_l` / `leg_r` /
`boot_l` / `boot_r`) and, for accessory pieces, the outfit colour-key that
gates them. `figure_shapes(**tokens)` re-runs it with a recorder on, and
[`docs/atlases/build_person_figure.py`](atlases/build_person_figure.py) diffs
a few token combinations (helmet vs bare head, each accessory on/off) into
`game/world/person_figure.py` — `BASE` / `BARE_HEAD` / `HELMET_RING` /
`HELMET_FACE` / `EYES_*` / `ACC[key]`, all in Person game units (centre-line
at x, feet at y, y negative going up), plus the walk pivots. `Person.draw()`
resolves the colour tokens per outfit, applies the walk-cycle transform per
group, and blits — no body drawing code of its own. Re-run the builder from
the repo root after editing the atlas figure; don't hand-edit
`person_figure.py`. Colours flow the other way too: the `--skin` / `--body-out`
CSS vars in the atlas quote `Person.SKIN_COLOR` / `Person.OUTLINE_COLOR`.

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
