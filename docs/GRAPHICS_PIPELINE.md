# Graphics Pipeline

Every visual asset in the game — ships, stations, buildings, people, outfits,
decorations — is a **design** stored as small hand-editable JSON, expanded at
load into flat polygons the renderer draws. Modders edit the JSON. The design
atlases render the same expansion, so a plate always shows exactly what the
game shows.

This document is the spec for that pipeline. It is written in the present
tense and describes the system as it is; history lives in git.

## Principles

1. **Polygons only.** No strokes, no circles, no arcs. Curves are many-sided
   polygons; a small round light is an octagon. The renderer has one drawing
   primitive: a filled polygon.
2. **Fewest vertices that read.** Each asset has a vertex budget for its tier
   (below). A silhouette earns every vertex against the identity.
3. **Separation by shade, not line.** Where two same-coloured shapes meet, the
   far one carries a shade that tapers to nothing at both ends, along one
   global light direction. There is no outline.
4. **One source of truth.** The design JSON is authored and committed. Nothing
   downstream is edited by hand; nothing upstream exists.
5. **Design, catalogue, and depict every article individually** — even the
   ones that are only ever worn as part of a set.

## Source layout

```
config/stories/<story>/graphics/
├── materials.json          — material → base tone + how dark/mid/light derive
├── palettes/
│   └── <group>.json        — a palette: material → colour, for one culture or role
├── body/
│   ├── <species>.json      — silhouette, sections, anchors, curves, pivots
│   └── rig_<motion>.json   — per-group swing amplitude & phase for one animation
├── articles/
│   └── <article>.json      — one garment or accessory, designed on its own
├── sets/
│   └── <set>.json          — an ordered list of article ids + palette
├── ships/       <ship>.json
├── stations/    <station>.json
├── buildings/   <building>.json
├── decorations/ <decoration>.json
├── collision/   <id>.json         — hitboxes, one file per asset, loaded on their own
└── interiors/   <interior>.json   — floor plan: rooms, portals, decoration placements
```

Each file is small and reads as a single design. The loader globs a directory;
a file's stem is its id. `collision/<id>.json` and `interiors/<id>.json` share
the asset's stem so the three (graphics, collision, interior placement) line up
without a manifest.

**Organizing it.** One design per file, `snake_case` id. A category directory is
one asset *kind* (`ships/`, `articles/`, …); add one only when a kind has more
than one asset or needs its own expander path (`faces/` earns its place because
`expand()` resolves face slots). Where a directory holds interchangeable
*variants of one slot*, prefix the id with the slot: `hair_short`,
`eyes_almond`, `rig_walk`. Curves and anchors live on the body section they
belong to, never a separate file. Once a story has more than one culture,
prefix ids `<culture>_<asset>` (`vherathi_skiff`); split a category into
subdirectories only when it passes ~15–20 files or clearly holds distinct
sub-families. The atlas mirrors this — one plate generator per category, and
once a story is large, one atlas *page* per subject (culture, the figure), not
one page for everything.

## Anatomy of a design file

```jsonc
{
  "identity": "A grown resin pod, asymmetric, tapering to one glass point.",
  "tier": "ship_far",                 // sets the vertex budget
  "palette": "vherathi",              // which palette resolves this design's materials
  "silhouette": [
    { "group": "hull",   "material": "resin", "points": [[...], ...] },
    { "group": "canopy", "material": "glass", "points": [[...], ...] }
  ],
  "details": [
    { "group": "canopy", "material": "light", "role": "detail",
      "note": "single running light at the nose",
      "points": [[...], ...] }
  ],
  "anchors": { ... },                 // bodies and articles only — see Fitting
  "curves":  { ... }                  //          "
}
```

- **`identity`** — one or two sentences. The design serves this. The atlas
  prints it verbatim.
- **`silhouette`** — the outer form, partitioned into **regions**. Each region
  is one polygon tagged with a `group` (a concept: `hull`, `canopy`, `spine`,
  `port_nacelle`) and a `material`. Regions tile the silhouette; they do not
  overlap.
- **`details`** — polygons layered over the regions: trim, insignia, lights,
  panel seams. Each carries the `group` it belongs to, its own `material`, and
  a short `note` the atlas shows.
- No shading polygons appear in the file. They are derived (see Auto-shade).

## The six stages

A design is authored — and read — in this order:

| # | Stage | Output in the file |
|---|---|---|
| 1 | **Identity** | `identity` — what makes this unique, tied to the culture theme |
| 2 | **Silhouette** | one outer form, fewest vertices, every choice justified by (1) |
| 3 | **Materials** | the silhouette split into `silhouette` regions, each `material`-tagged |
| 4 | **Auto-shade** | *nothing* — `expand()` derives dark/mid/light per region |
| 5 | **Details** | the `details` list: trim, designs, lights, grouped by region |
| 6 | **Description** | `identity` + every detail's `note` name every material and detail |

## Materials, palettes, tones

`materials.json` names each material and how its three tones derive from a base:

```jsonc
{
  "resin":  { "tone_dark": -34, "tone_light": +26 },
  "glass":  { "tone_dark": -20, "tone_light": +40 },
  "plate":  { "tone_dark": -30, "tone_light": +22 }
}
```

A palette binds materials to colours for one culture or role:

```jsonc
// palettes/vherathi.json
{ "resin": "#6b7f5a", "glass": "#9fe8d0", "light": "#ffd98a" }
```

A design names one `palette`. `expand()` resolves each part's
`material` + `tone` → rgb against it. A modder retints an entire culture by
editing one palette file; a total conversion writes its own. Parts may also
carry a literal `"#rrggbb"` for a one-off.

## Auto-shade

`expand()` replaces each silhouette region with up to three polygons along one
global light vector (`materials.json` `light` key, default up-left):

- **mid** — the region polygon, `material` at `tone_mid` (the base).
- **dark** — a crescent hugging the region's far edge, `tone_dark`, tapering
  to zero width at both ends. Never a constant-width inset (that reads as a
  seam ruled down the middle). Clipped to the far half of the region first, so
  it works on any polygon shape.
- **light** — a thinner sliver on the near edge, `tone_light`, same taper.

Details are not auto-shaded; they are drawn as authored, over the region.

Shininess is a later addition to this stage and changes nothing upstream.

## Fitting: anchors and curves

Bodies and articles publish, and consume, two kinds of named reference so that
an outfit fits a body it was not drawn against — and follows it when the body
is reproportioned.

A **body section** publishes:

- **anchor points** — `waist_center`, `shoulder_far`, `hand_near`, `head_crown`
  — a named point in body space, tied to one animation group.
- **edge curves** — `torso_left`, `hip_right`, `head_profile` — an ordered
  polyline along the section's silhouette.

An **article region or detail** declares one of:

- `"group": "<animation group>"` — the piece rides that body part (`torso`,
  `arm_near`…) and moves with it. Default `torso`.
- `"fits": [{ "curve": "<section>.<curve>", "from": i, "to": j, "reverse": … }]`
  — replaces polygon vertices `i…j` with the body's named edge curve, spliced
  in verbatim. The garment's edge is then the body's own silhouette; reshape
  the body and the edge follows. Multiple fits per region, applied
  high-index-first. Author the region's free vertices in body coordinates and
  put one placeholder vertex where each curve splices in.
- **Outset.** After fitting, every region is pushed out along its vertex
  normals by a small `outset` (default 0.12 world units, override per design or
  per region) so the garment sits just proud of the body and no sliver of body
  peeks through at the seam.
- **Prefer a fitted vertex to a free one.** Anywhere the garment edge meets the
  body — neckline, waistband, armhole, cuff, inseam — fit it to a curve. Leave
  a vertex free only for genuine garment shape (a flared hem, a collar point).
  A free vertex near the body is where skin peeks through on the other variant.
- **Fitting is once, at expand time.** The result is a flat parts list tagged
  by `group`. During animation the renderer rotates each group about its body
  pivot — a `leg_near` trouser leg swings rigidly with the near leg, a `torso`
  shirt stays with the torso. Nothing re-fits or soft-deforms per frame, which
  is correct because the rig rotates whole limb *segments*, not a soft skeleton;
  the garment segment shares the body segment's pivot and rest shape, so they
  move together.

Reproportion the body → anchors and curves move → every article follows, with
no coordinate migration. Articles are authored once, against the reference
body, and never need re-fitting when proportions change.

## Bodies

`body/<species>.json` is a design file with `sections` instead of a flat
`silhouette`:

```jsonc
{
  "identity": "...",
  "sections": {
    "torso": { "group": "body", "material": "skin",
               "points": [...], "anchors": {...}, "curves": {...} },
    "upper_arm_near": { "group": "arm_near", "pivot": [x, y], ... },
    ...
  }
}
```

Each section is a region (Stages 2–5 apply) plus, for a limb, a `pivot`. The
body carries the walk-cycle knobs; `rig_walk.json` carries the per-group swing.

## Animation

A rig is the static pipeline per **segment**, with three additions:

1. **Segments overlap at joints.** An upper arm has a domed top that tucks
   under the shoulder; a thigh runs past the hip. No gap opens when a group
   rotates about its pivot.
2. **Shade is baked into the segment** and rotates with it. Recomputing the
   light per frame over a small swing is not worth it.
3. **Group draw order encodes depth.** Far limbs draw behind the torso a shade
   darker; near limbs draw in front. `self.facing` mirrors the whole figure.

The swing lives in `body/rig_<motion>.json`: per animation group a `deg`
amplitude and a `phase` (fraction of the cycle), plus a torso `bob`. Legs swing
opposite each other; each arm counter to the leg on its side; feet pivot on the
ankle and lag their leg; hands pivot on the arm so the limb swings as one unit.
`apply_walk(parts, body_design, rig_walk, t)` takes a composed parts list and
returns it deformed into the pose at cycle fraction `t` — it rotates each part
about its group's pivot and bobs everything above the hips. Because a garment
shares its limb's group, it swings with the limb for free. The atlas renders a
frame strip; the game will drive `t` from its own clock.

## Articles and sets

Every garment and accessory is **one `articles/<id>.json`** — its own identity,
silhouette, materials, details, and fitting declarations — and gets **its own
atlas plate**, drawn on the bare reference body.

A `sets/<id>.json` composes them:

```jsonc
{
  "identity": "Dock crew, cold-weather.",
  "palette": "civilian",
  "articles": ["work_trousers", "quilted_coat", "duty_boots", "watch_cap"]
}
```

The set gets a combined plate: all its articles expanded onto one model, in
list order. A set adds no geometry of its own — only the article list and the
palette.

**Draw order.** `compose_worn(body, body_parts, *article_parts)` merges the
body and everything worn over it into one back-to-front list: each article part
draws immediately after the last body part of its own animation group. A
`torso` shirt sits over the torso but under the near arm; a `leg_near` trouser
leg sits over that leg; a `leg_far` one behind the torso. The renderer draws
that composed list; it does no layering of its own.

## Expansion

`game/graphics/expand.py` is the one code path from design JSON to render
parts. Given a design and its resolved palette it returns the flat list the
renderer already draws:

1. resolve `fit:` curves against the body's current silhouette
2. resolve `anchor:` to an animation group and offset
3. auto-shade each region → mid / dark / light
4. resolve `material` + `tone` → rgb via the palette
5. emit parts, each tagged `group` and `role` (`fill` \| `shade_dark` \|
   `shade_light` \| `detail`)

The game calls `expand()` once per asset at load and caches the result. The
atlas imports the same function. There is no bake step and no generated file.

## Renderer contract

`WorldObject.draw_parts()` and `Person.draw()` draw an expanded parts list and
nothing else — no synthesised outline, no base shape underneath. Each part is:

```jsonc
{ "points": [[x, y], ...], "color": <rgb>, "group": "...", "role": "..." }
```

`group` and `role` are ignored by the renderer; the atlas and debug tooling
use them. Ship/station coords are fractions of `size`; building and body
coords are absolute local units, y negative up.

## Scale and world space

One **world unit** is a fixed real length (the player figure is ~`PLAYER_H`
units tall — the reference every other size is quoted against). Every design
states its true size, and the atlas draws it to scale:

- A ship/station design is unit shapes scaled by its `size`. The design file
  records the `size` it is drawn for and a one-line **scale note**
  (`"about 3× the player's ship"`).
- A building, decoration, or body part is in absolute world units directly.
- A decoration records what it is scaled *for*: a bench seat sits at
  `SIT_H` above the floor, a doorway clears `PLAYER_W` plus a margin, a table
  clears knee height. These are named constants in `materials.json`'s
  `scale` block, not magic numbers in each file.

The atlas carries two comparison plates per family: **every asset beside the
player silhouette**, and **the smallest asset beside the largest** at one
scale, so a mismatch is visible before anything ships.

## Level of detail

The camera zoom ranges over `[zoom_min, zoom_max]` (Space View and interiors
set their own limits). A design is authored at its `ship_near` / dockable
detail level; `expand()` produces the far levels:

- `expand()` takes an `lod` — the asset's on-screen size in px. Each `details`
  entry has a `min_px`; below it the detail is dropped (trim, seams, nav lights
  go first). Below a region's `flatten_px` the crescents are dropped and it
  draws as one flat polygon. Emissive dots (thrusters) get a tiny `min_px` so
  they survive to the smallest sizes.
- The renderer picks the lod from the current scale and caches one parts list
  per bucket.

The vertex budget (below) is the *near* budget. A far bucket is whatever
survives the culls — it is not authored.

## Collision

Hitboxes live in `collision/<id>.json`, separate from the graphics and loaded
on their own — the physics and pathing code never touches a parts list, and a
headless server can load collision without expanding any geometry.

```jsonc
{
  "footprint": [[x, y], ...],        // one convex-ish polygon, world units
  "blocks_lane": true,                // optional: this prop may stand on a lane
  "boxes": [                          // optional extra solids
    { "points": [[...], ...], "blocks_lane": false, "note": "counter" }
  ],
  "sit": [[x, y], ...]                // optional: where a walker can sit / stand
}
```

Rules:

- A hitbox **sits inside the silhouette footprint** and is quoted in the same
  world units — the atlas overlays it on the plate (a translucent fill) so the
  fit is checked by eye every time the plate is regenerated.
- `footprint` is authoritative for depth sort, target brackets, and the
  interior walkability predicate. `local_points` / `shape` in the graphics
  data are for drawing bounds only.
- Multiple `boxes` for an L-shaped desk or a railing. `blocks_lane` opts a prop
  out of the lane check — set it on the whole file for a single-footprint prop
  (a column), or per `boxes` entry for one solid of a compound prop (a counter
  within a stall). See Interiors.

## Interiors

`interiors/<interior>.json` is a floor plan in world units, sized against the
player:

```jsonc
{
  "rooms":   [ { "id": "concourse", "points": [[...], ...] } ],
  "portals": [ { "between": ["concourse", "dock"], "points": [[...], ...] } ],
  "placements": [
    { "decoration": "resin_bench", "at": [x, y], "angle": 0 }
  ]
}
```

- **Rooms are drawn for pathing first.** A corridor is at least
  `2 × PLAYER_W + margin` wide; a portal clears `PLAYER_W` plus a margin; no
  room is narrower than a walker can turn in.
- **The navmesh is generated, never authored.** `game/graphics/navmesh.py`
  rasterises the rooms and portals into a walkable grid — the same raster
  `NavGrid` builds for A*, minus building and decoration hitboxes — and pulls
  the **traffic lanes** from the bare floor: a chamfer distance field, then the
  ridge cells (corridor centre-lines). `check_placements` flags any placement
  whose hitbox lands on a lane unless its `collision/<decoration>.json` sets
  `blocks_lane: true` (a structural column, a security checkpoint, a shop
  counter); `blocks_lane` also reads off an individual `boxes` entry. The atlas
  interior plate shows the floor, the lanes, and every placed hitbox — green
  for a declared blocker, magenta for clear, red for a fault.
- A placement references a decoration by id; its hitbox comes from
  `collision/<decoration>.json`, translated and rotated to `at` / `angle`.
- Rooms carry an `id` and a `material`; portals carry an `id` and either
  `between: [room, room]` or `to: "<name>"` for an exterior airlock.
- `sit` points on a bench become stand/sit targets for `DockRoutine` and idle
  NPCs.

## Vertex budget by tier

| tier | world size | on-screen (near) | budget (silhouette + details) |
|---|---|---|---|
| `ship_far` | 1–2× player's ship | ~12 px | 6–10 |
| `ship_near` | player's ship | docked view | ~24 |
| `station` | 20–60× player | dockable | ~40 |
| `building` | 4–15× player tall | city elevation | ~30 |
| `person` | ~1× player | body section | as needed; face kit exempt |
| `decoration` | 0.3–2× player | furniture, props | ~16 |

## Atlas

A design atlas is a generated page: one plate per asset, the specimen drawn by
`expand()` + a polygons-to-SVG writer, beside the `identity` text, the detail
notes, and a spec block naming the design file's real keys. The atlas is a
viewer — it holds no geometry and no copy of anything.

## Vertex editor

[`docs/atlases/editor.html`](atlases/editor.html) is a standalone page for
dragging a design's vertices by hand. Load a design JSON (file drop, or paste
into the output box), and it renders exactly what `expand()` would — its
shading is a hand-port of `expand.py` and must be kept in step with it. Drag any
handle; double-click an edge to insert a point; alt-click to delete. Each
section has an eye toggle to hide/show it (isolate a limb, or drop the far side
to work on the near one) and a checkbox for its handles. "Freeze
shade → editable" replaces a region's computed crescent with an explicit
`shade_dark` / `shade_light` point list you can then drag. Copy or download the
updated JSON back over the source file.

**Shade overrides.** A region (body section or ship silhouette entry) may carry
`"shade": false` to draw flat, or explicit `"shade_dark"` / `"shade_light"`
polygons (one each) used verbatim instead of the auto-shade. `expand()` honours
them and rotates them with the region under `rest_splay`.

## Faces and hair

The **face kit** is `details` on the body's `head` section — eyes (socket,
sclera, iris, pupil, lid, catchlight), tapered brows, a short nose (bridge
shadow + soft tip), two-part lips. Each is a small polygon; a round one may be
written `"circle": [cx, cy, r]` and `expand()` turns it into an ngon. The kit is
drawn at a shallow 3/4 turn: the near eye larger, the far one compressed. It
scales with the head.

**Face slots.** The head section carries a `"face"` map — `{eyes, brows, nose,
lips: <name>}` — and `load("faces", "<slot>_<name>")` supplies each slot's
`details`. So the features are interchangeable (`eyes_almond`, `eyes_deep`,
`nose_soft`, `nose_straight`, `lips_full`, `lips_thin`, …) without editing the
body.

**Hair is an article**, mostly drawn **behind** the head. Its bulk regions set
`"under": ["head"]` so the skull hides the back and only the volume past the
silhouette shows; the framing bits — a thin band along `head.hairline`,
sideburns, a fringe, side panels — set `"over": ["head"]` and draw in front of
the face. Group `torso` so it rides the head. `compose_worn`'s `"over"` /
`"under"` accept body **section** names, not just animation groups.

Per-character variation is a **palette override**: skin / hair / eye / lip
colours are palette keys, so a story or an NPC roster can swap them without
touching geometry.

## Approval gates

An approval gate is a point where the agent stops, shows a rendered proof, and
waits for a yes before spending effort downstream. There are two kinds.

### Per-asset design gates

Every new asset passes these, in order. Each shows a plate from `expand()`.

| after stage | gate | proof shown |
|---|---|---|
| 1–2 | **silhouette** | the outer form + identity text, one flat colour, on the tier's viewBox with the player-scale reference. No materials yet. |
| 3–4 | **materials & shade** | the region split and the auto-shade, palette applied. No details yet. |
| 5–6 | **finished** | details in, description complete, on its own plate. |
| — | **on model** *(articles only)* | the article fitted to the bare body, then in its set. |
| — | **in game** | the asset drawn by the running game at real scale beside its neighbours. |

Skip a gate only when the user says so. A silhouette change after the
materials gate reopens it.

### Pipeline-build gates

One-time, while the pipeline itself is being stood up. Each proves one
mechanism on the **smallest asset that exercises it**.

| gate | proves | proof |
|---|---|---|
| **A — mechanics** ✅ | design JSON → `expand()` → specimen, end to end | one body renders on a plate |
| **B — reference body** ✅ | proportions, sections, anchors, curves, draw order | `human_masc` / `human_femme` |
| **C — material & shade** ✅ | auto-shade (tapered crescents) + palette tones | side-lit crescents, one continuous per region |
| **D — fit** ✅ | `group` / `fits` against the body | `tank_top` sides spliced from the femme torso curves |
| **E — animation** ✅ | the rig: per-group pivot swing, clothing follows, torso bob | `civilian_work` on the walk-cycle frame strip |
| **F — world scale + LOD + collision** ✅ | size vs. player, detail culls, hitbox overlay | `courier` — near / far / hitbox / beside-the-figure plates |
| **G — interior** ✅ | floor plan sized to the player, generated navmesh, lane check | `concourse` — plan + generated lanes + `column` (declared) / `bench` (clear) |
| **H — in game** | the story boots and the renderer draws all of the above | screenshot from a running build |

Gates are sequential: B needs A, D needs B and C, E needs D, H needs everything.
Move a gate or add one when the work shows a seam that needs sign-off.

## Minimal asset set (pipeline test)

Until gate H passes, the `graphics_pipeline_test` story carries only what the
gates need and no more:

- 1 body (`human`), 1 palette (`civilian`), `materials.json`
- 3 articles — one top, one bottom, one footwear — and 1 set composing them
- 1 ship, 1 station
- 1 interior with 2 decorations (one that blocks a lane on purpose, one that
  must not)

New assets wait until the pipeline is proven end to end.

## Authoring checklist

1. Write the `identity`. If you cannot say what is unique in two sentences,
   the design is not ready.
2. Draw the silhouette. Stay under the tier budget. Justify each vertex.
3. Split it into `material` regions on concept lines (`group`).
4. Run `expand()` and look at the auto-shade. Adjust region edges, not shading.
5. Add `details`, each with a `group` and a `note`.
6. For a body or article, declare `anchor:` / `fit:` — never raw coordinates
   against the body.
7. State the true size and a scale note. Check the against-player and
   smallest-vs-largest comparison plates.
8. Give `details` a `min_px` and regions a `flatten_px`; check the far lod
   still reads.
9. Write `collision/<id>.json`. Confirm the hitbox sits inside the footprint
   on the overlaid plate.
10. For an interior, size corridors and portals to the player first, then
    place decorations; run the lane check and clear or justify every blocker.
11. Check the article's own plate, then its set plate.
