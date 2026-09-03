# Design Atlases

A **design atlas** is a self-contained HTML page that draws out a family of the
game's assets — ships, outfits, buildings, decorations, stations — in more
detail than the current `config/` JSON expresses, so a human can look at a whole
set at once and decide what to build. It is a **design tool, not a spec**:
nothing in an atlas is wired into the game until someone does it deliberately,
and every plate says so.

Each atlas's HTML is committed under [`docs/atlases/`](atlases/) and is the only
copy that matters — open the file in a browser (or the preview pane) to view it.
This doc is the how: how to make one, how to keep it honest, and which ones exist.

## Restructure in progress

The three-atlas split (Resin & Rivets = 2 cultures, Standard Issue = body +
Federation) is being pulled apart into **one atlas per subject**, each with
full coverage (outfits · ships · stations · decorations · city & station
layouts). Shared page shell lives in
[`docs/atlases/atlas_shell.py`](atlases/atlas_shell.py) (`css()` + `DEFS`),
per-atlas accent colour.

| atlas | from | holds | state |
|---|---|---|---|
| **Common Kit** | Standard Issue ch. 01–04 | shared `Person` body (cinched-waist anatomy + accessory slot map) + the culture-neutral civilian / service outfits, each with a role detail. **Carries the Grounded study's redrawn face kit, hairstyles and hard hat** (see below) | **built** — `gen_common.py` + `common_kit.py` |
| **Sol Federation** | Standard Issue ch. 05 | the `standard_issue` culture: issued ships, Standard Ring station, buildings, hazard decal, spine-and-bays interior + Federation crew/command outfits (visor-slit / stencil signature) | **built** — `gen_split.py` + `federation_outfits.py` |
| **Vherathi Concord** | Resin & Rivets, Vherathi half | 6 grown hulls, reef station, 4 buildings, 6 furniture/deco, 4 layouts + outfits with asymmetric eye-bubble helm clusters + resin-bead glow | **built** — `gen_split.py` + `vherathi_outfits.py` |
| **Drossholt Company** | Resin & Rivets, Drossholt half | 5 bolted hulls, welded station, 4 buildings, 7 furniture/deco, 2 layouts + outfits with riveted patch-plates + box respirator | **built** — `gen_split.py` + `drossholt_outfits.py` |
| **Past the Reach** | (unchanged) | the seven *proposed* cultures — mockup only | done |

**All four splits are built.** `gen_split.py` builds the Vherathi / Drossholt
ship / station / building / furniture / layout plates by pulling them
**verbatim** from `resin-and-rivets.html` via `atlas_plates.grab`; the Federation
"issue" hardware is generated straight from `gen_si.issue_plate` (its plate
generators `gen29`–`gen40` live in `gen_si.py`). Then it adds the signature
outfits.

**`standard-issue.html` is removed** — superseded by Common Kit + Sol Federation.
`gen_si.py` was pruned to just the shared drawing kit + `figure_parts` +
`figure_shapes` + the issue-hardware generators (the "rewrite standard-issue.html
in place" pass and the `CREW`/`CONTACT` crew tables are gone). `apply_parts.py`'s
`SI` rows now read `sol-federation.html` (which carries the same grabbed plates).
**`resin-and-rivets.html` is still superseded but still live** — it's the plate
source for Vherathi / Drossholt hardware and for `apply_parts.py`'s `RR` rows;
removing it would mean moving `gen_rr.py`'s hardware generators into `gen_si.py`
the same way, a follow-up.

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

**Body: the cinched waist.** `figure_parts` pinches the torso to a waist
about halfway up the standing figure and flares back to a hip nearly as wide
as the chest — an hourglass whether or not an outfit covers it. **Every belt,
sash end, hip pouch and torch anchors at the waist**, not the hip line. Baked
into `game/world/person_figure.py` via `build_person_figure.py`, so the game
has it; `past-the-reach.html` shows it; `resin-and-rivets.html` picks it up on
its next regenerate.

**Body: the Grounded pass (full proportion remap).** `figure_parts` is now
generated straight from the [`grounded-person.html`](atlases/grounded-person.html)
study's proportion spec via a `_gx` / `_gy` transform (`_G_SCALE` 5.15 atlas
units per study unit, `_G_GROUND` 202.2): a **~6.1-head figure** — a small
**oval** head (`ooval`: a many-sided polygon, x-radius `0.92·fr`, taller than
wide — not a circle, matching the study; `fr` = 14 bare, 11.5 helmeted, down
from 15/12). The **helmet / hat** dome is the same oval (`helmet_r·0.92` x /
`helmet_r` y), not a circle, so it reads as an egg around the egg-shaped head;
the Vherathi grown dome (`vherathi_outfits._dome_pts`) got the same 0.9-x
squash. **Shallow D-ears** — `EAR_D` is now the study's exact profile (flat
side tucked *inside* the oval edge at `0.88·fr`, a small bulge to `1.06·fr`),
where it used to stand off at `1.02–1.30·fr` and read as knobs. A **short
neck** (a `SKINF`
column from the collar line up under the jaw), a **long torso**, and **legs on
the true half-body line** (`FIG_HIP_Y` 139, was 146; slight ankle taper + a
mid-calf point). **Narrow rounded shoulders** — the torso curves out to a modest
shoulder point (`attachHalf` ~3, arms tuck in close) and the upper arm gets a
**domed top** that tucks under it. The **face kit** shows on a bare or hatted
head (hidden by a helmet or a visor): **oval eyes** with a full-height pupil, a
short **straight brow** over each, a tan **under-nose shadow** (`SKINL`), a soft
**mouth** line, and the D-ears above; every feature scales with `fr`. **One
uniform outline weight** (`_FD` = 1.0) on every structural part — head, torso,
neck, arms, hands, legs, boots, helmet dome — so the figure reads with the
study's single thin edge instead of the old per-part `d` (head was `1.8`, torso
`1.5`). Baked into `person_figure.py` — the D-ears lead `BARE_HEAD`, and the
head is now the largest polygon in `BARE_HEAD` / `HELMET_FACE`, so
`Person._HELM_FACE_DY` picks it by vertex count (`person._face_cy`); the eyes
are `ngon` polygons, so
`tests/test_helpers.py::test_visor_replaces_the_eyes` counts the polygon delta
(8). `person.py`'s `LEG_HEIGHT` / `ARM_LENGTH` walk-cycle knobs and
`build_person_figure.py`'s pivots track the new limb lengths. Moving the arms in
meant **re-anchoring every outfit signature** (`common_kit.py` /
`federation_outfits.py` / `vherathi_outfits.py` / `drossholt_outfits.py`) to the
new lines: waist `y103`, belt `y99`, hands `(57/83, 133)`, arm shaft `x50-60` /
`x80-90`, bare head `(70, 46)` r14. The Common Kit / Sol Federation / Vherathi
Concord / Drossholt Company atlases all render it (re-run `gen_common.py` +
`gen_split.py` + `build_person_figure.py` + `build_figure_signatures.py`).

**Signature-accessory pass (with the Grounded body).** Moving the arms/hands in
meant re-anchoring the signature layers in `common_kit.py` / `federation_outfits.py`
/ `vherathi_outfits.py` / `drossholt_outfits.py`. The rules that came out of it:
anything on the **hip / thigh that the arm should cover** (holster, sidearm,
clipboard, canteen, respirator canister) goes in **`pre`**, not `post`; **gloves**
sit at the hand anchors `(57, 83)` at `y133`; a **badge** is a small diamond on
the **left breast** `(62, 84)`; the Federation **centreline stripe** starts at the
collar `y66` (clear of the chin/mouth) and the **chevron flash** sits *on* the
right upper arm (`x81–89`); the Vherathi **helmet dome** is a rounded arc that
hugs the (smaller) head and covers the ears, and a **sash** is a baldric over the
left shoulder to the opposite hip (`figure_parts` `sash` + each culture's own).
These anchors were all re-fitted for the full Grounded proportion remap above.
**Held weapons were removed for now** (mechanic's wrench, ranger's rifle,
marine's carbine, bounty-hunter's shoulder weapon) — they come back with the
weapons system.

## Current atlases

| Atlas | Source |
|---|---|
| **Grounded Person Model** *(hand-authored, interactive)* | [`docs/atlases/grounded-person.html`](atlases/grounded-person.html) |
| **Common Kit** | [`docs/atlases/common-kit.html`](atlases/common-kit.html) |
| **Sol Federation** | [`docs/atlases/sol-federation.html`](atlases/sol-federation.html) |
| **Vherathi Concord** | [`docs/atlases/vherathi-concord.html`](atlases/vherathi-concord.html) |
| **Drossholt Company** | [`docs/atlases/drossholt-company.html`](atlases/drossholt-company.html) |
| **Past the Reach** | [`docs/atlases/past-the-reach.html`](atlases/past-the-reach.html) |
| **Kaethar Directorate** | [`docs/atlases/kaethar-directorate.html`](atlases/kaethar-directorate.html) |
| **The Vetl** | [`docs/atlases/the-vetl.html`](atlases/the-vetl.html) |
| **The Salt Crows** | [`docs/atlases/salt-crows.html`](atlases/salt-crows.html) |
| **Deeprock Mining Consortium** | [`docs/atlases/deeprock-consortium.html`](atlases/deeprock-consortium.html) |
| **The Ashfall Rite** | [`docs/atlases/ashfall-rite.html`](atlases/ashfall-rite.html) |
| **The Meridian Free Ports** | [`docs/atlases/meridian-free-ports.html`](atlases/meridian-free-ports.html) |
| **The Theln Drift** | [`docs/atlases/theln-drift.html`](atlases/theln-drift.html) |
| ~~Resin & Rivets~~ *(superseded by Vherathi Concord + Drossholt Company; still the plate source for their hardware)* | [`docs/atlases/resin-and-rivets.html`](atlases/resin-and-rivets.html) |
| ~~Standard Issue~~ *(removed — Common Kit + Sol Federation; the issue-hardware generators moved into `gen_si.py`)* | — |

- **Grounded Person Model** — the design study that worked out the "Grounded"
  body + face pass now in `figure_parts`. **Hand-authored, not generated by a
  `gen_*.py`** — a standalone interactive page (JS builds the figures from a
  proportion spec; a `requestAnimationFrame` walk cycle you can pause / scrub).
  Sections: the reproportioned body with head-count ticks; the live walk cycle
  (arms opposite each other, counter to the stride); the hair / skin options
  on the head; the body in a few `graphics.json` outfits; and the figure at
  on-screen distances. It's a record of a **shipped** decision, kept because
  the interactive walk and the proportion rationale don't live anywhere else.
  Update it by editing the HTML directly.

  **The study has since been iterated past the shipped bake** — a later pass
  drops all outlines (fills only), runs a **leggy** proportion — short torso
  (~12.6 u), hip up at study-y 16.6 (~47% of height), shorter arms, bigger
  feet — reshapes the torso to an
  hourglass with a **trapezius yoke** that curves up behind the neck and a
  **convex hip flare** (a curve back out from the waist, not a straight
  taper); splits the body into **masc / femme** with no neutral (`bodyVariant()`
  — a shared base, each build setting its own torso silhouette and hip /
  arm-attach / leg-stance widths: masc broader up top and narrower at the
  hip, femme the reverse) and every figure on the page is one or the other;
  swaps the head oval for a big **egg** (`HEAD_SHAPE` polygon — tall full
  rounded crown to `HEAD_CROWN`, widest at the cheekbone, tapered chin;
  hairlines sit high on the forehead; the tick axis measures to the real
  crown), and **generates** every **hairstyle** from the skull rather than
  drawing it by hand — `buildHairParts()` traces `headR()` (the `HEAD_SHAPE` profile as a polar
  function, sampled on the head's own vertices so a flat style never cuts a
  chord inside it), pushes it out by a lift (`crown`, 0.08 for `buzz` up to 0.43
  for `curls`) shaped as a plateau — ramp up, hold across the sides and crown,
  ramp back down into the far sideburn —
  **ends the crescent at `tempAng` — a temple point kept above the brow**, so
  the temple stays bare and the ear clear, then closes it with a hairline that
  falls from a high `peak` to that same point, giving every style a sideburn
  taper instead of a blunt horizontal chop. `sidepart` adds `skew`/`sweep` and
  a stepped `part`/`jog`, `receding` cuts `bay` temple bays around a `dip`
  forelock, `bun`/`ponytail` use a tight `sleek` crown (knot tucked into it /
  high tail behind), `curls` scallops the built edge with a rim of clumps, and
  `long` hangs a panel down each side of the face over one back drape — the
  panel starts on the crescent's own temple point and hands back to the
  hairline *short* of it (`buildHair`'s `cut` / `join`), because running the
  hairline all the way out makes the loop double back and leaves a spur of
  hair standing off the temple. Plus a
  `stubble` (one fill mixed from skin + hair, built the same way with zero
  lift, a flush buzz-cut shadow the §1 lead figure wears);
  reshapes the boot to a **foot profile** (low toe box pointing
  the way the figure faces — screen-left as built — with a compact heel);
  draws the head **turned a shallow 3/4** toward the facing direction (skull
  off-centre `HEAD_DX`, features clustered further over `FACE_DX` and smaller
  `FACE_S`, hair and under-chin shadow riding the skull centre — the hair is
  built off the skull profile, so an offset of its own would slide it off the
  crown — near ear showing / far ear covered; the whole-figure mirror flips
  it);
  gives each arm / leg a **fixed one-direction shade polygon** down its
  screen-right side — the torso's a curve-following side strip, the neck's a
  band whose lower edge parallels the chin, and `legShadePts` reads the leg's
  stops off the polygon rather than indexing fixed slots, so adding a stop
  doesn't tear it — moves behind-the-back hair (long,
  ponytail) ahead of the body so the torso occludes it, and adds a
  **facing left/right** demo (`face: -1` mirrors the group, = `Person.facing`),
  head cards with an accurate neck + trapezius yoke, and a zoom-scrub section.

  **Then a redraw for looks** (the current state of the page). The head came
  **down** (r 2.72 → 2.60 u) and **up** (cy 32.1 → 32.4) over a **slimmer
  neck** (half 1.15 → 0.96) with the torso top dropped ~0.3 u, so ~1 u of neck
  is actually bare above the collar instead of the chin sitting on the
  collarbone — about 6.8 heads by the page's own tick metric. The skull is
  narrower overall, clearly widest at the **cheekbone** (y 0.19) and tapered
  through a narrower jaw to a small rounded chin. The **face kit is rewritten**
  (`drawFaceKit` is now the one call site for both the figure and the head
  cards): **almond eyes** — a built `almondPts` opening with a full upper lid
  over a shallower lower one, sclera / iris / pupil / catchlight, and an
  `EYE_LASH` band along the lid that doubles as the crop taking the top off the
  iris, which is what makes the eye read lidded instead of staring — set closer
  together (`EYE_EX` 0.42 → 0.375) and tilted 6°; a **fine tapered brow**
  (thickest over the inner third, thinning to a point outward) sitting lower;
  a **nose** of a slim bridge shadow running into a small soft tip, replacing
  the dark oval blob; and a **two-part mouth** — upper lip with a cupid's bow
  over a fuller lower lip in a `lipTone()` mixed off the skin, its seam a touch
  higher at the corners than at the centre. Per-character **`eyeCol`** joins
  `hairCol` / `browCol`, and `browColFor` now takes the brow a shade *deeper*
  than the hair (lifting it for near-black) so a blonde or grey head still has
  a face. The head carries the same one-direction shade as the limbs, but
  shaped like a face rather than ruled down it — `HEAD_SHADE` is a leaf, barely
  there at the crown, widest across the far cheek and jaw, gone by the chin, at
  a much lighter `FACE_SHADE`. The **ears** dropped to brow-to-nose-base height
  and barely clear the skull. On the body: the leg gained **thigh / knee /
  calf** stops, the **boot** lost its flipper toe, the **hand** became a
  tapered mitt polygon carried through the arm transform instead of a circle at
  the wrist, the arms taper to a slimmer wrist and hang closer at rest
  (`REST_SPLAY` 12° → 7°), and the head turn was eased (`FACE_DX` 0.22 → 0.16).

  **Hair redrawn on the same terms.** The generator survived; what it emits
  changed. A style now bakes into a **part list** — `{p|c, t}` pieces in
  head-radius units — instead of one polygon, and `drawHairPieces()` walks the
  same list for the figure and the head card, so they cannot drift apart.
  Every piece past the fill is one object: **`hairCrescent()`**, a ribbon that
  runs along the hair's own outer edge between two angles, swells in the middle
  and tapers to a point at both ends, with its depth on each ray capped by
  **`bandDepth()`** — a bisection for how far in from the edge that ray can
  travel before it leaves the hair through the hairline. So the **shade** (far
  side), the **sheen** (thinner, held off the edge over the near crown) and the
  **parting** all have no visible ends and no straight chord across the mass,
  and none of them can be deeper than the hair over it. A shade built as a
  wedge between the edge and the hairline — the first attempt — reads as a
  second colour painted on along a straight line; this doesn't.
  `hairTone()` scales rather than offsets, so near-black hair still separates.
  The hairline gained **`tips`**, locks that *straddle* the curve (points below
  it, notches above) at uneven depths — a smooth swept hairline was most of why
  every flat style read as a swim cap, and locks that merely ride on top of the
  curve read as bumps. `lean` carries the bulk to one side; **`wave`** ripples
  the lift itself, gently on most styles and into clumps on `curls`, so no
  edge is a clean arc.

  **The lift shape is what decides helmet or hair.** It started as
  `sin(u)^0.7` — a bulge over the crown — and no amount of depth fixed the
  read, because the outline stayed an offset copy of the skull. It is now a
  **plateau**: a smoothstep ramp over the first `tuck` (~1/6) of the sweep,
  flat across the sides and crown, and a matching ramp down into the far
  sideburn, times a slight swell over the crown so it isn't a bowl. The ramp
  matters as much as the plateau — any power of a sine leaves a cusp at the
  ends, which showed up as a spike off each temple; a smoothstep leaves the
  skull tangentially. `sidepart` dropped its `tips` in the same pass: it is
  combed, not cut, and with a fringe on it it was the crop in another
  colour.

  `long` **cascades** (`fall`): the side fall leaves the crown high up
  (~56°) and its outer edge is the crescent's own radius plus a flare that
  opens as it comes down, so the hair sweeps from the top of the skull out over
  the ear and past the jaw in one line rather than reading as a slab clipped to
  the side of the head — and the crown arc is trimmed to the two attachment
  angles so the crescent can't cut a chord across it. Every other style but
  `stubble` hangs a **`burn`**, a tapered sideburn wisp below the hairline and
  inboard of the ear (so it reads *in front* of it), its top edge set inside
  the hair so it joins rather than floats; the crescent's clean taper into the
  temple was tidier than any real head.

  **The helmet goes through the same generator.** A hard hat is a hairstyle in
  everything but name, so `HELMET_STYLE` is a `buildHairParts()` style — a
  shallow shell (`crown` 0.22) with a high, flat front edge (`peak` 0.74,
  `q` 3.0, `tempAng` 8) — and it comes back with the same shade ribbon and
  sheen in the helmet's own colour. What changed the read most was the
  **layering**: the old dome was a plain circle drawn *behind* the head, so it
  could only ever be a halo round the face; the shell draws **over** the
  finished full-size head. A helmet covers a head, it doesn't replace it, so
  the face no longer shrinks under one. On top go a **brim** — wider than the
  shell, nearly flat underneath, tapering to a lip at each end, and in the
  **shade** tone, because in the base tone it merges straight into the shell
  and the whole thing reads as a turban — a moulded rib, a chin strap and a
  lamp.

  The junctions are where a style actually goes wrong, and each is now built:
  the fall's inner edge follows **`headHalfAt()`** while there is a
  cheek to hug and then holds a line past the jaw, and it hands back to the
  hairline *short* of the temple. The back **drape** starts inside the front
  hair's silhouette (its corner used to poke out over each temple) and draws in
  the **shade** tone — at the same tone as the locks in front of it the whole
  side of the head merges into one flat slab. `bun`'s knot sits **proud** of
  the slicked crown with its own shade; `ponytail`'s tail is a tapered rope
  built from a centre line by **`tailParts()`**; and the drape falls **past the
  shoulders**, since narrower than that the torso swallows it whole and the
  style reads as hair that stops at the jaw. `stubble` is the one style with no
  shade or sheen: it is a shadow on the scalp, not a mass of hair.

  **The face kit, the hairstyles and the hard hat are now ported into
  `gen_si.py`,** so the **Common Kit** atlas draws them too — the whole block
  sits under a `# ==== Grounded` banner there and is a straight port of the
  study's JS (same names, same numbers), kept as one piece so the two can be
  diffed. `figure_parts` gained `hair` / `hair_col` / `eye_col` / `brow_col`;
  `emit_hair()` walks a baked part list and gives **silhouette** pieces the
  body's uniform outline while shade, sheen and the small details go without,
  which is what the outlined Common Kit style needs (an outline round the
  brim's near-zero tapering end reads as a stick, so the brim keeps a minimum
  thickness; the sideburn takes none, or it reads as a tab stuck on the
  temple). The helmet moved from *behind* the head to *over* it there too, and
  the head no longer shrinks under one.

  **Then the proportions followed** — `figure_parts` now draws the study's
  `GROUNDED` table directly (torso, hip, leg stops, arm, hand, boot, neck,
  head), so the two are the same body. That moves every anchor line the
  outfit signatures were written against: the torso top 66→53, the waist
  103→90, the hip 139→117, the knee 158→160, the hand from just above the hip
  to well below it. Rather than re-typing several hundred coordinates across
  four signature files, they are drawn through **`fig_remap()`** — a
  piecewise-linear map from the old anchor lines onto the new ones, applied to
  **shapes rather than points**: each `poly()`/`circ()` is translated by the
  map's offset at its own centre and scaled about that centre by the map's
  average slope over its span, clamped. Mapping points would stretch a knee
  pad to two and a half times its height, because the thigh really did get
  that much longer; this keeps a piece of kit its own size and puts it where
  it belongs. x is untouched — the new torso and stance are the same width.
  `figure_parts`' own accessory layers (collar, shoulders, sash, belt, cap,
  badge, backpack…) are authored in the same old space and go through the same
  map, bracketed by `_xon()`/`_xoff()`; the body itself draws in the new space
  and stays outside it. `_arm_rot()` is the one special case: under the map it
  stretches the point onto the new arm's shoulder-to-wrist span, splays it by
  the new rest angle, then runs it back through the map's *inverse*, because
  the shape it belongs to is about to be mapped forward again.

  Two consequences worth knowing: **new signature work stays in the old
  coordinates** (or the whole file gets re-authored and the adapter dropped),
  and `common_kit.py` no longer draws its own hard hat — `figure_parts` does,
  from the `helmet` key. The bare-headed civilian outfits gained hairstyles at
  the same time. Still ahead of `person_figure.py` until
  `build_person_figure.py` is re-run.

  The rest is deliberately ahead of `figure_parts` until a re-bake; the "One
  uniform outline weight" / "long torso" language above describes the current
  bake, not the study.

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
- **Standard Issue** *(removed)* — was the shared `Person` body + culture-neutral
  kit + the Sol Federation look, all now split into **Common Kit** + **Sol
  Federation**. Its `standard_issue` culture, ships/station, **Procyon Gate**
  system and buildings/furniture (issue_block / issue_shed / issue_bollard /
  issue_bench / issue_desk) shipped into `parts` and stay in `config/`. The
  issue-hardware plate generators (`gen29`–`gen40`) moved into `gen_si.py`
  (`gen_si.issue_plate`, `ISSUE_PLATES`), so Sol Federation still renders them and
  `apply_parts.py`'s `SI` rows still extract them (now from `sol-federation.html`).
  The strokeless-only rule it established (only `<polygon>` + `<circle>`, no
  stroke; offset-shape outlines; many-sided polygons for curves; `ring_strip`
  tori) carries on across every current atlas — see "Strokeless specimens".
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

### Updating an atlas

1. Edit the file in `docs/atlases/` (or re-run its `gen_*.py` for a generated one).
2. Open it in a browser to check it.
3. Commit the HTML change, and update this table / the notes above if scope moved.

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

**Every atlas** is drawn with **only `<polygon>` and `<circle>`, no `stroke`
anywhere** (the rule started with `standard-issue.html` /
`resin-and-rivets.html`) — it maps 1:1 to
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

**The figure reads side-on, from `figure_parts` outward.** `figure_parts` emits
the **far arm + far leg** (the left-side animation groups) *behind* the torso
and the **near arm + leg** (right-side) *in front* — the grounded-person study's
layering — and bakes a small **resting arm splay** (`gen_si.ARM_REST_DEG`, via
`_arm_rot`; the `*_outfits.py` signatures wrap arm-mounted detail through the
same helper). So every atlas card and `grounded-person.html` show it directly.
`Person.draw` adds only what's motion-dependent: `self.facing` (±1, from the
last mostly-horizontal step, kept when idle) mirrors every figure-space x about
`self.x` — the baked figure faces screen-left, so facing +1 is the mirrored
one — and `_arm_swing` swings the arms opposite each other, counter to the
stride, over that splayed rest pose.

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
- **The committed HTML is the atlas.** There is no other copy to keep in sync;
  edit the file (or its `gen_*.py`), view it in a browser, commit with the
  `atlas:` prefix.
- **Keep the table.** The "Current atlases" table here is the index; a new atlas
  isn't done until its row (source path) exists.

See also: [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) for in-engine drawing
conventions, and the per-culture `theme` strings in
`config/stories/default/cultures.json` for the source rubrics.
