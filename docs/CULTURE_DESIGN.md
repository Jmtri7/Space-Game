# Culture Design: Process & Approval Gates

How to build one culture's art kit as a `config/modules/<name>/` module on
the design-JSON pipeline ([GRAPHICS_PIPELINE.md](GRAPHICS_PIPELINE.md)) —
from an old retired design-atlas HTML (`config/stories/default/atlases/`),
from a plain text description, or from nothing but a one-line pitch. Distilled
from building the `vherathi-pilot` pilot module and finding out the hard way
that a first pass tends to produce assets that are *structurally* correct
(they load, they expand, nothing crashes) but not *visually* differentiated —
several ships or outfits that render as the same silhouette in different
colors. This doc exists to catch that before it repeats across every asset
in a category, not after.

See [CONFIG_MODULES.md](CONFIG_MODULES.md) for the module mechanics (how a
culture module is declared and resolved) and [GRAPHICS_PIPELINE.md](GRAPHICS_PIPELINE.md)
for the design-JSON format itself. This doc is the workflow layered on top.

## The hard rule: recoloring is not differentiation

A culture module's whole point is that its ships/outfits/buildings read as
*that culture's*, but that doesn't mean one silhouette wearing different
colors. Two rules that are not optional:

- **Every ship in a culture needs a genuinely different silhouette from
  every other ship in that culture** — a different hull shape, not the same
  wedge/hull nudged slightly. A courier, a patrol hull, and a hauler should
  be distinguishable from their outline alone, at a glance, in monochrome.
  Small asymmetric details (an off-center canopy, an uneven nacelle) read as
  *texture* on a silhouette, not as the silhouette's shape — don't rely on
  them to carry the differentiation between two ship types.
- **A role's bespoke articles must be load-bearing for that outfit's
  silhouette**, not small accent props added on top of an identical base
  garment. If three roles share the same base articles (coat/jacket/pants)
  in the same palette and differ only by a tiny pin or cuff, they will not
  read as different roles — the bespoke piece has to change the *outline*
  (a distinct headpiece, a cape/harness/skirt swap, a silhouette-changing
  layer), not just decorate it. Recoloring a shared article is fine as a
  *supporting* choice (e.g. one role in the culture's dark tone, another in
  its light tone) but never as the only differentiator between roles.

### Every role gets the same three bespoke slots

Give each role exactly three bespoke articles, one per slot, never fewer:

1. **Shoulder pads, on both shoulders.** One pad per side, always — never
   only the near shoulder. In an asymmetric culture the two pads are
   unequal in size (the near one bulkier is the common case, since it's
   the one most visible/on-model), not absent on one side; the asymmetry is
   in the size difference, not in only covering one shoulder.
2. **Headgear** (a helmet, a crest, a hood, a crown)
3. **A torso item** (a mantle, a cape, a breastplate, a harness)

That's 3 × the culture's role count — 9 articles for a 3-role culture. Each
slot can be subtle or bulky and symmetric or asymmetric independently of the
other two — a role doesn't have to be asymmetric everywhere just because one
piece is — but skipping a slot for one role (because "that role doesn't
really need a hat") is exactly how the differentiation problem creeps back
in: it removes a point of comparison between roles instead of adding one.
An asymmetric culture can still make one slot a plain, deliberately subtle
piece (a subtle shoulder pad is still a shoulder pad) rather than skip it.

### A coverage gradient across roles

When a culture has roles that plausibly differ in how armored/protected
they are (a civil role vs. a security role vs. a field role is the common
case), give them a deliberate light → medium → heavy gradient in body
coverage across the three slots together, not just in how bulky one piece
looks:

- **Light**: thin/small pieces that leave most of the body visible — a
  band, not a cap; a sash, not a plate.
- **Medium**: partial coverage — a hood over the crown and ears but the
  face open; a chest panel over the upper/center torso but not edge to
  edge.
- **Heavy**: a headgear piece that covers most or all of the face (a full
  helm, visor slit optional detail, not a requirement), a torso item that
  covers most or all of the torso, and at least one of the two shoulder
  pads sized bulky. The other shoulder pad can still be smaller for the
  asymmetry rule above — "heavy" describes the role's overall coverage,
  not a requirement that literally everything on it is oversized.

Reserve judgment on which role sits where until stage 0's identity pass —
it should follow from what the role actually does (a security/martial role
reads heavy, a civil/ceremonial one reads light), not be assigned
arbitrarily to force variety.

Check this by eye at every gate below (see "Rendering for a gate") before
moving on — a design that passes `expand()` without error can still fail
this rule, which is exactly what happened the first time through.

## Process

1. **Distill the identity first, no geometry yet.** From an atlas: pull the
   dek/theme sentence, the hex swatches, and every ship/station/building/
   outfit description it already gives you. From a description or a blank
   pitch: write the same things yourself — a one-paragraph silhouette rule
   (what makes this culture's shapes recognizable), a 5–7 color palette, and
   a naming convention for places/people/ships. This becomes the `identity`
   prose in every design file and the two palette files below — don't skip
   to geometry before this is written down somewhere (the module's
   `module.json` description is a fine place for the short version).
2. **Palettes before geometry.** Write the ship/building palette and the
   dress palette first (`graphics/palettes/<name>.json`,
   `graphics/palettes/<name>_dress.json`) so every design file that follows
   has real color keys to reference instead of placeholders.
3. **Author in the six stages below, gating after each one.** Within a
   stage, articles come before the outfits/sets that wear them — decide
   what makes each role's silhouette distinct before assembling the set,
   not after — but both are presented and approved together as stage 1,
   since a bespoke article has no reason to exist outside the outfit it
   defines.
4. **Catalogue wiring last per category** — `graphics.json`/
   `ship_types.json`/`building_types.json` entries, all carrying
   `"culture": "<id>"` so color resolves from the culture instead of being
   hardcoded.

## Approval gates

GRAPHICS_PIPELINE.md's own "Approval gates" section defines per-asset gates
(silhouette → materials/shade → finished → on-model → in-game) for authoring
*one* asset carefully. Building a whole culture means repeating that per
asset many times over, which is exactly how the differentiation problem
above slips through — each individual ship can pass its own silhouette gate
while still being indistinguishable from its culture-mates, because nothing
ever puts them side by side. The category gate below sits on top of the
per-asset ones: it's the point where every asset *of one kind* in the
culture gets compared against each other, not just against itself.

Finish **every asset in a stage** before rendering anything for it — three
ships, not one ship rendered three times. Then stop, render the whole
stage, write it up, and **wait for the user's approval before starting the
next stage.** Don't self-approve and continue, and don't fold two stages
into one render-and-describe pass even when it would be convenient (e.g.
buildings and their footprints).

The six stages, in order:

1. **Outfit designs** — every role's bespoke article(s) and the full set
   worn on both body cuts. The write-up here pays special attention to the
   roles and the bespoke articles specifically: what each role is, why its
   bespoke piece looks the way it does, and how that piece (not the shared
   base garments under it) is what makes the role's silhouette read as
   distinct from the others.
2. **Ship designs** — every ship in the culture, rendered at the same
   frame/zoom so silhouettes compare directly.
3. **Building and decoration designs** — every building type and every
   decoration, as standalone assets (not yet placed in a floor plan).
4. **Station exterior graphics** — every station design.
5. **Station floor plans** — the station interior(s), with the shared
   floor texture actually applied and every decoration placed, not a bare
   room outline.
6. **City floor plans** — the ground/settlement interior(s): floor texture,
   every building placed, every decoration placed.

Each write-up covers every asset finished in that stage (e.g. all three
outfits together, not one at a time) and gives, per asset: what it is, the
justification for its silhouette (why this shape and not another), and how
it fits the culture's identity from stage 0 (palette, theme, naming). A gate
that reveals a problem (weak differentiation, a scale bug, an invisible
detail) is fixed **before** moving to the next stage, even if that means
redoing the current stage's renders — don't carry a known problem forward
into a later stage that builds on it (a floor-plan gate is wasted if the
buildings it places already had a known problem at the buildings gate).

### Offer the live editor at every gate

After presenting a stage's renders and write-up, **ask the user whether
they'd like to open the vertex editor themselves and tweak the designs
directly**, before making further changes solo. Don't just barrel into the
next revision pass on their feedback — a described fit problem ("doesn't
cover the shoulder") is exactly the kind of thing that's faster and more
precise for a human to drag right in the editor than for the agent to
re-derive from screenshots and coordinate arithmetic. Concretely: start
`config/serve_nocache.py <port>` if it isn't already running, open
`http://127.0.0.1:<port>/config/editor.html` in the Browser pane, and select
the module/story and the specific asset just discussed so the user lands on
it directly rather than having to navigate there themselves. See
"Editor automation is unreliable" below for what to do (and not do) once
it's open.

## Sizing and fitting an article

A first pass at a bespoke article tends to come out wildly oversized and
disconnected from the body — a mantle twice as wide as the whole torso, a
crest floating a head-height above the actual head. It happens because the
body's real scale is easy to guess wrong and the article is authored blind
(no live preview) against free-drawn coordinates. Concrete numbers to check
against instead of guessing (from `human_masc.json`'s `sections`/`anchors` —
`human_femme.json`'s are the same shape, a few units smaller):

| Landmark | Approx. coordinate |
|---|---|
| Shoulder (near/far) | `(±3.4, -24.9)` |
| Torso width | ~7 units total (chest ±3.5 at its widest) |
| Torso height (collar to hip) | ~11 units (`-25.6` to `-15.4`) |
| Head crown / chin | `-31.1` / `-26.2` (~4.9 tall) |
| Head width | ~3.7 units |
| Waist / hip center | `(0, -19)` / `(0, -15.4)` |
| `PLAYER_H` (whole figure) | 31 units, feet at `y=0` |

Rules of thumb, in the order to check them:

1. **An article should be comparable in size to the body part it sits on**,
   not to the whole figure. A shoulder pad is a few units across (the
   shoulder anchors are only 6.8 units apart, near to far) — not half the
   torso's 7-unit width. A crest sits *on* a 3.7-unit-wide head, so a
   height of 3–5 units above the crown reads as a ridge; 10+ units reads as
   a sail. When a piece is supposed to be dramatic, make it dense/layered
   rather than just larger — bulk, not just size, is what "bulky" in the
   article-slots rule above should mean.
2. **`outset` is a clearance nudge, not a sizing control.** It pushes a
   region's own edge out a little so it doesn't z-fight with the body
   underneath — typically `0.03`–`0.08`. It does not compensate for
   authoring the base points too large or too small; get the `points`
   right first.
3. **Anchor the first and last point of a fitted piece to (or very near) a
   real body anchor** (a shoulder, the collar, the head crown) so it visibly
   attaches rather than floats near the body with a gap. A piece is allowed
   to extend past the body outline, but the *seam* — where it meets the
   figure — should sit right on or just outside the body's own edge.
4. **Render it alone on the bare body before adding it to any set.** This
   is what `render_pipeline_asset.py article` is for (see below) — checking
   fit against a full outfit hides scale problems behind the base garments
   sized correctly under it. Fix fit first, add other regions (trim, a
   second plate, layered detail) only once the base shape sits right.

## Rendering for a gate

Two tools, both using the game's real draw code — not an approximation:

- **`scripts/render_pipeline_asset.py`** — articles, ships, stations, and
  outfits, via the actual `Ship.draw` / `LandingSite.draw` / `Person.draw`
  code paths (correct shading, LOD, thruster flame, body-cut mirroring):
  ```bash
  python scripts/render_pipeline_asset.py article <story> <article_id> out.png [femme]
  python scripts/render_pipeline_asset.py outfit <story> <outfit_id> out.png
  python scripts/render_pipeline_asset.py ship <story> <ship_type_id> out.png
  python scripts/render_pipeline_asset.py station <story> <space_station_id> out.png
  ```
  `article` draws the bespoke piece alone on the bare body (masc by
  default, pass a truthy 4th arg for femme) — that's stage 1's per-role
  proof that the article itself, not the outfit around it, carries the
  silhouette. `station` covers stage 4's exteriors.
- **`scripts/render_interior.py`** — buildings/decorations as placed
  (stage 3 can render each standalone via a throwaway one-building
  interior, or just render the stage 5/6 floor plan a stage early and
  crop), and the real floor-plan stages (5 and 6), with the floor texture
  and every placement actually drawn, via the real `LocationScreen.draw`:
  ```bash
  python scripts/render_interior.py <story> <station|moon> <interior_key> out.png
  ```

Both need `SDL_VIDEODRIVER=dummy`/`SDL_AUDIODRIVER=dummy` (already set by
the scripts themselves) and a real story to resolve the module through —
see "Use a throwaway preview story" below. Neither tool needs a display;
render the PNG and look at it directly.

Don't substitute a hand-rolled polygon-to-image script for these. A quick
approximation can hide exactly the bugs that matter (a missing internal
`"size"` on a station design silently no-ops the real scale multiplier;
`_expand_craft` uses the *design file's own* `"size"`, not the
`graphics.json` catalogue entry's — this bit the pilot module, see below)
and won't catch draw-order/shading/mirroring issues the real path handles.

## Editor automation is unreliable

The vertex editor is genuinely the better tool for *diagnosing* a fit
problem — seeing a piece live on the real body beats re-deriving its shape
from a screenshot and coordinate math — and it's the right thing to open
when the user wants to tweak a design by hand (see "Offer the live editor
at every gate" above). Driving it yourself via browser automation to make
the actual edit is a different story:

- The page only renders correctly after a full reload at the final window
  size; resizing after load can leave the canvas computing a degenerate
  (all-zero) transform. Navigate fresh, then select the story/module/asset.
- Dropdowns and checkboxes are reliably driven via `javascript_tool` (set
  `.value`/`.checked` and dispatch a real `change`/`click` event) — that's
  fine for selecting an asset, a body cut, or which articles an outfit
  preview shows.
- Actually dragging a vertex precisely is not reliable this way, and
  there's no clean way to read back the exact local coordinate a drag
  landed on. For a coordinate-level fix, read the diagnosis off the editor,
  then make the edit in the JSON file directly and re-verify with
  `scripts/render_pipeline_asset.py` / `scripts/render_interior.py` — both
  call the same underlying draw code the editor uses, so this isn't a
  lesser check, just a more reliable one for the agent to drive.
- The editor's "Outfit" preview panel (tick articles worn together) renders
  in a flat default palette, not the story's actual dress palette — good
  for checking fit/silhouette/coverage across a whole outfit, not for
  judging final color.

## Use a throwaway preview story

A module is inert until some story's `"modules"` list depends on it, and
`get_graphics_asset`/`get_culture` need a real story to resolve through — so
build one small disposable story alongside the module for exactly this
purpose (see `config/stories/vp_test/` for the shape). Build it as **one
system**, not several — everything the culture makes should be reachable
without a jump, so a look at the whole kit is one system visit:

- `story.json` declares the new module (plus `figures-human` for outfit
  bodies/articles) and a `starting_system` pointing at the one system.
- A matching `cultures.json` entry, just enough for color resolution
  (`metal_color`/`glass_color`/`thrust_color`/wall/floor colors).
- A `pilots.json` entry per ship giving it a name and a real role
  (`courier_pilot`, `patrol_officer`, `freighter_pilot`, `miner`, ... — see
  `ROLE_ROUTINES` in `game/world/character.py`) instead of leaving it an
  anonymous `ai_ships` entry — a role is also a second differentiation
  check: a courier that flies like a hauler is a sign the ship and its
  stats/role don't agree.
- **One `systems/*.json`** with both the `"station"` and `"moon"` slots
  filled with the culture's two station designs (see "two stations in one
  system" below), every ship as an `ai_ships` entry with its real
  `pilot`/role and a `route` that actually visits both landing sites
  (`["station", "moon"]` for a shuttle/patrol role), and every building/
  decoration placed inside one station's interior and the other's, with an
  NPC wearing each outfit.

Delete the preview story (or fold it into the real story's wiring) once the
module is approved — it's scaffolding, not a deliverable.

### Two stations in one system

A system config only has a `"station"` slot and a `"moon"` slot, but nothing
requires the `"moon"` slot to hold an actual moon — set `moon_asset` to the
culture's *second* station id and give it a matching entry under
`graphics.json`'s `"moons"` catalogue (a straight copy of its
`"space_stations"` entry). `LandingSite` decides "is this a station"
by checking for a `rotation_speed` key, not by which slot it came from, so a
station-shaped asset dropped into the moon slot still renders and behaves
like a station. This is also why `attach_design` (`game/graphics/
story_assets.py`) needs to scale a `"moons"` entry's design the same way it
scales a `"space_stations"` one — `kind in ("space_stations", "moons")`, not
just `"space_stations"` — otherwise the second station silently renders at
1/40th scale in the moon slot even though the exact same design works fine
in the station slot. Fixed there for exactly this reason; if you hit a
station-shaped asset rendering tiny only in the moon slot, that's the bug to
check for.

## Gotchas

- **A station design file needs its own `"size"`.** `_expand_craft`
  (`game/graphics/story_assets.py`) scales a station's fractional silhouette
  by the *design file's* `"size"` key (`LandingSite` draws at `unit=1`) —
  not by the `graphics.json` catalogue entry's `"size"` field, which is
  metadata only for stations. Omitting it defaults to `1`, silently
  shrinking the whole station to a couple of units across. Ships don't have
  this problem (`Ship.draw` reads `ship_size` from the catalogue entry
  directly), which is part of why it's easy to miss on a station.
- **A raw `"decorations"` entry in an interior is cosmetic-only** (a flat
  shape with `points`/`color`, no collision, no catalogue reference).
  Placing a `building_types.json` id (a real building *or* a small
  decoration like a bench) — with collision, footprint, and its design file
  — goes in `"structures"` instead, as `{"x", "y", "building_type"}`. Don't
  reach for `"decorations"` when you mean "place this catalogue asset."
- **`config/editor.html` won't show you geometry for these asset kinds.**
  Ships/stations/buildings/decorations/sets/palettes render as read-only
  stubs there; only bodies/faces/articles are live-editable. Use the
  render scripts above, not the editor, to actually see a silhouette.
- **A far-side article region needs an explicit `"tag"` or it draws behind
  the torso.** `graphics/draw_order.json`'s `order` list puts `arm_far` very
  early (before `torso`), since that's correct for the body's own far-arm
  sleeve/skin, but a region on the far shoulder pad with no matching tag
  falls back to ranking by its `"group"` (`arm_far`) and gets drawn — then
  covered — before `torso`. Give a far-side region a `"tag"` that maps to a
  *later* slot in that order list (`"epaulette"` is last and works for any
  far-side accessory) so it draws in front of the torso and everything
  else, while its `"group"` stays `arm_far` so it still moves with the
  correct limb during animation. `"tag"` only ever changes draw order, never
  which body part a piece is rigged to.
- **Don't make an asymmetric shoulder/head pair by shrinking the far
  piece's *coverage* shape at all** — not toward the shoulder anchor, and
  not just at the lateral edge either. Either kind of shrink trades away
  real coverage (a gap at the neck seam, or a gap at the outer edge of the
  arm/head) for a smaller-looking piece, and a viewer reads the gap as a
  fit bug, not as a size choice. The piece that's actually load-bearing for
  coverage — the base cap/band that touches the seam and spans the full
  joint — should be an **exact mirror** of the near piece (negate `x`, same
  `y`), full stop. Put the asymmetry entirely in a *second, additive*
  layer instead: give the near piece a plate/trim/seam accent the far
  piece doesn't have (or a smaller version of it). The near side then
  reads as bulkier/more detailed while both sides still fully cover the
  body part underneath.
