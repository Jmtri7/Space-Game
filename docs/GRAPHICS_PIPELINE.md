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
├── materials.json          — shading profiles (dark/light deltas) + scale constants
├── draw_order.json         — worn-figure back-to-front stack: body sections + garment tags
├── palettes/
│   └── <group>.json        — a palette: colour key → hex, for one culture or role
├── body/
│   ├── <species>.json      — silhouette, sections, anchors, curves, pivots
│   └── rig_<motion>.json   — per-group swing amplitude & phase for one animation
├── articles/
│   └── <article>.json      — one garment or accessory, designed on its own
├── items/
│   └── <item>.json         — an article's geometry worn with its own colour/shade
├── sets/
│   └── <set>.json          — an ordered list of article/item ids + palette
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
  "palette": "vherathi",              // which palette resolves this design's colours
  "silhouette": [
    { "group": "hull",   "color": "resin", "shade": "deep",  "points": [[...], ...] },
    { "group": "canopy", "color": "glass", "shade": "sheen", "points": [[...], ...] }
  ],
  "details": [
    { "group": "canopy", "color": "lamp", "shade": "glow", "role": "detail",
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
  `port_nacelle`), a `color`, and a `shade` profile. Regions tile the
  silhouette; they do not overlap.
- **`details`** — polygons layered over the regions: trim, insignia, lights,
  panel seams. Each carries the `group` it belongs to, its own `color` /
  `shade`, and a short `note` the atlas shows.
- No shading polygons appear in the file. They are derived (see Auto-shade).

## The six stages

A design is authored — and read — in this order:

| # | Stage | Output in the file |
|---|---|---|
| 1 | **Identity** | `identity` — what makes this unique, tied to the culture theme |
| 2 | **Silhouette** | one outer form, fewest vertices, every choice justified by (1) |
| 3 | **Colour + shade** | the silhouette split into regions, each tagged `color` + `shade` |
| 4 | **Auto-shade** | *nothing* — `expand()` derives dark/mid/light per region from its `shade` profile |
| 5 | **Details** | the `details` list: trim, designs, lights, grouped by region |
| 6 | **Description** | `identity` + every detail's `note` name every colour and detail |

## Colour, shade, palettes, tones

**Colour and shade are two independent axes of a part's look.** A silhouette
region or detail carries:

- **`color`** — a palette key (`"denim"`), a literal `"#rrggbb"`, or `[r,g,b]`.
- **`shade`** — the name of a **shading profile** (how the surface catches the
  global light), or `false` to draw flat with no crescents. Missing → `matte`.

`materials.json` holds the profile table — each profile is a
`tone_dark` / `tone_light` pair (plus `emissive` for light sources):

```jsonc
// materials.json
"shading": {
  "flat":  { "tone_dark": 0,   "tone_light": 0 },
  "glow":  { "tone_dark": 0,   "tone_light": 0, "emissive": true },
  "soft":  { "tone_dark": -14, "tone_light": 12 },
  "matte": { "tone_dark": -24, "tone_light": 20 },
  "deep":  { "tone_dark": -34, "tone_light": 24 },
  "sheen": { "tone_dark": -20, "tone_light": 44 },
  "metal": { "tone_dark": -40, "tone_light": 48 }
}
```

A palette binds colour keys to hex for one culture or role:

```jsonc
// palettes/vherathi.json
{ "hull": "#6b7f5a", "glass": "#9fe8d0", "lamp": "#ffd98a" }
```

A design names one `palette`. `expand()` resolves `color` + `tone` → rgb
against it, and the `shade` profile supplies the dark/light deltas. So the same
shape can be *purple + sheen* on one item and *purple + matte* on another — the
two never have to move together. A modder retints an entire culture by editing
one palette file; a total conversion writes its own.

There is no `materials` map any more: `color` *is* the palette key. (`expand()`
still honours a legacy `"material": name` and a `materials: {name: profile}`
map if an unmigrated story carries them.)

## Auto-shade

`expand()` replaces each silhouette region with up to three polygons along one
global light vector (`materials.json` `light` key, default up-left):

- **mid** — the region polygon, `color` at the base (no delta).
- **dark** — a crescent hugging the region's far edge, `tone_dark`, tapering
  to zero width at both ends. Never a constant-width inset (that reads as a
  seam ruled down the middle). Clipped to the far half of the region first, so
  it works on any polygon shape.
- **light** — a thinner sliver on the near edge, `tone_light`, same taper.

The ribbon's outer edge is the region silhouette verbatim and its inner edge is
a depth-capped inward offset that is Laplacian-relaxed and corner-cut (Chaikin)
for smoothness, then snapped back inside wherever a smoothing pass pushed it out
across a concave stretch. So the shade is always **fully contained within the
region** — it never bleeds past the silhouette — and a coarsely faceted region
still gets a smoothly curved shade. Vertex count per ribbon is bounded (~30–45)
regardless of the region's own count.

A region drawn with a `shade` profile whose deltas are `0` (or `shade: false`,
or an `emissive` profile like `glow`) gets no crescents at all — one flat fill.

Details are not auto-shaded; they are drawn as authored, over the region. A
detail's own `shade` profile only affects it when it is drawn at a non-`mid`
`tone`.

## Fitting: anchors and curves

Bodies and articles publish, and consume, two kinds of named reference so that
an outfit fits a body it was not drawn against — and follows it when the body
is reproportioned.

A **body section** publishes:

- **anchor points** — `waist_center`, `shoulder_far`, `hand_near`, `head_crown`
  — a named point in body space, tied to one animation group.
- **edge curves** — `torso_left`, `hip_right`, `head_profile` — an ordered
  polyline along the section's silhouette.

**Curve storage.** A curve in `section.curves` is either a bare polyline
(legacy) or `{ "pts": [...], "ends": [[x,y],[x,y]], "dir": ±1 }`. `pts` is the
resolved polyline and the only field `expand()` (`_curve`) reads; `ends` (the
two endpoint coordinates) and `dir` (the boundary-walk direction) are what the
vertex editor uses to re-trace `pts` when the body is reshaped — see the editor
**Curves panel**. The editor writes the object form; hand-written designs may
use either.

`pts` is stored in the **neutral authoring frame**, like every other body
coordinate — `expand_body` rotates a limb section by `rig.rest_splay` before
drawing it. An article that fits to a curve is authored already in the rest
pose (splay baked into its `points`), so `_curve` carries the curve into that
same frame on the way out: it rotates `pts` by the rest transform of the
curve's own section group (`arm_near` / `hand_near` / `arm_far` / `hand_far`;
torso/leg/foot have none). Without this the fitted edge of a sleeve or glove
lands on the un-splayed arm — offset from the drawn limb by the splay angle
(~0.6 world units at the hand). The editor's `bodyCurve`, its "generate N
vertices between" trace, and `findBodyVertexIndex` all apply the same rotation
so tailor mode matches the game.

An **article region or detail** declares one of:

- `"group": "<animation group>"` — the piece rides that body part (`torso`,
  `head`, `neck`, `arm_near`…), moves with it in the walk cycle, and — with no
  tag — stacks at that section's slot. Default `torso`.
- `"tag": "<name>"` — stack the region at that named slot in the story draw
  order instead (see Draw order). Optional; omit to stack at `group`.
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

**A fully-traced region (`"fits": []`, every vertex free) stops being
body-portable.** It renders correctly on the body it was traced against and
literally unchanged — same fixed coordinates — on any other, so a garment two
bodies share (via one outfit set, or two sets naming the same article) will
look wrong on whichever body it wasn't traced for.

**Current state of the pipeline-test story: the masc side is further along
than the femme side.** `body/human_masc.json` carries edge curves on the
torso, both arms/hands, both legs, and both feet; `body/human_femme.json`
carries them on the torso and both arms/hands. `duty_boots` fits each foot
outline to `foot_{near,far}.shoe` on the masc body; other articles are being
fitted region by region, the masc variant leading. A region whose `fits`
can't resolve on a given body (curve absent) falls back to its free-vertex
trace for that body — `_curve` returns `None` and `_apply_fits` leaves the
span alone.

### One file per article, both body cuts inside it

An article is **one `articles/<name>.json`** (no `_masc` / `_femme` suffix).
The shared half of each region — `group`, `color`, `shade`, `tone`, `note`,
`tag`, `outset` — is written once on the region. The body-specific half
lives under a **`geometry` map**, one entry per body cut:

```jsonc
{ "identity": "...", "tier": "person", "palette": "civilian",
  "regions": [
    { "group": "torso", "color": "cloth", "shade": "matte", "note": "left panel",
      "geometry": {
        "masc":  { "points": [...], "fits": [{ "curve": "torso.side_left", "from": 1, "to": 1 }] },
        "femme": { "points": [...], "fits": [...] } } } ] }
```

`geometry.<variant>` holds `points`, `fits`, and — when the region has them —
`details`, `shade_dark`, `shade_light` (detail and frozen-crescent
coordinates are body-specific too). `expand()` picks the entry named by the
worn body's top-level `"variant"` (`masc` / `femme`); a pre-merge region with
`points` straight on it still works. There is no `fits_body` key any more —
the `geometry` keys carry it.

**Items and sets follow suit.** `items/<name>.json` names its geometry
unsuffixed (`"geometry": "long_coat"`). `sets/<name>.json` lists bare article
ids and is one file per outfit — unless the two cuts genuinely pick different
articles (`civilian_work`: short hair vs long hair), in which case it stays
`_masc` / `_femme`. `graphics.json` `outfits.<id>.set` points at whichever
exists; the outfit's `body` selects the variant everywhere downstream.

## Bodies

`body/<species>.json` is a design file with `sections` instead of a flat
`silhouette`:

```jsonc
{
  "identity": "...",
  "sections": {
    "torso": { "group": "body", "color": "skin", "shade": "soft",
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
about its group's pivot and bobs everything above the hips. A group with no
`rig_walk.swing` entry just rides the bob (that is `torso`, `neck`, `head`
today). Because a garment shares its limb's group, it swings with the limb for
free. The atlas renders a frame strip; the game will drive `t` from its own
clock.

**Every body section is its own animation group.** `human_masc` / `human_femme`
define `torso`, `neck`, `head`, and near/far `arm` · `hand` · `leg` · `foot` —
each limb group with a matching `pivots` entry, and `neck` / `head` too (base of
the neck, base of the skull). So a hat or hood can ride `group: "head"`, a collar
or necklace `group: "neck"`, and they move with that part for free. `torso` is
the default when a region names no group. `neck` and `head` carry no walk swing
yet — they exist so articles can attach to them; add `rig_walk.swing` entries
(and regroup the face-slot details + hairstyles off `torso`/`face` onto `head`)
when the head should actually move in the gait.

## Articles and sets

Every garment and accessory is **one `articles/<id>.json`** — its own identity,
silhouette, colours, shades, details, and fitting declarations — and gets **its
own atlas plate**, drawn on the bare reference body (both cuts, side by side).
Its regions carry a per-cut `geometry` map (see *One file per article* under
Fitting). The article file carries a *default* look; an **item** (below) can
wear the same geometry differently.

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

**Draw order — one list of body parts and tags.** The story publishes a single
back-to-front list in `graphics/draw_order.json` (`order`): the body's section
names interleaved with author-defined **tag** strings. Both are reorderable, but
only in the vertex editor's Outfit section.

```jsonc
{ "order": [
  "back", "arm_far", "hand_far", "leg_far", "foot_far",
  "torso", "neck", "hair_back", "head", "hair",
  "leg_near", "foot_near", "arm_near", "hand_near", "front"
] }
```

`compose_worn(body, body_parts, *article_parts, order=<that list>)` places every
part at its slot in the list:

- a **body part** → its section name
- an **article region** → its `"tag"` if it has one, else its animation
  `"group"` (a section name)

Within one slot the body part draws first, then article regions in worn order —
each successive `*article_parts` list on top of the ones before (the set's
`articles` order; `extra_articles` last). A name not in the list sorts to the
very front. With no `order`, the body's own `draw_order` (bare section list) is
the fallback.

`hair_back`, `hair`, `back`, `front` above are just tags — nothing structural.
The bulk of a hairstyle is a `"hair_back"`-tagged region (the skull occludes it),
its fringe a `"hair"` one; a backpack body a `"back"` region. `group` still
drives animation (which limb a region swings with); the tag only moves it in the
draw stack. There is no `over` / `under`, no `draw_layers`. `"layer": "<name>"`
and `"back": true` are earlier spellings still read as a tag.

Edit the list in the vertex editor's **Outfit** section (see below).

**`hides_hair`.** A headgear article may carry top-level `"hides_hair": true`
(a raised hood, a sealed helmet). If any worn article declares it,
`_body_worn` drops every hairstyle from the outfit — no geometry to clip
through the shell, one less thing to expand.

## Items

An **`items/<id>.json`** is a thin object: an article's *geometry* worn with its
own *look*. It is what a person actually owns — two people can carry the same
jacket shape in different colours and finishes.

```jsonc
{
  "identity": "Oxblood officer's coat — long_coat geometry, deep red, waxed sheen.",
  "geometry": "long_coat",            // required: the articles/<id> to take shape + details from
  "color":  "#3a1f2e",                // optional: retag every region + detail to this one colour
  "shade":  "sheen",                  // optional: redraw every region + detail with this profile
  "parts": {                          // optional: override one region/detail by its `note`
    "visor bezel": { "color": "#6fe0e0" }
  }
}
```

- `color`, `shade`, and `parts` are **independent** — set any combination.
  None → the item renders exactly like its geometry file.
- **`parts`** keys are region (or detail) `note` strings. Each value overrides
  that part's `color` / `shade` / `tone` **by identity** — it keeps working when
  the region's authored `color` key changes, and it can recolour one region
  without touching another that shares the same key. Every part whose `note`
  matches is hit (so a `near`/`far` pair with the same note both change). A
  `parts` entry wins over the article-wide `color` / `shade`.
  *(This replaces the old `colors` `{palette-key: hex}` patch, which broke
  silently whenever a region's authored colour key was edited.)*
- A `sets/<id>.json` `articles` list and an NPC `equip` list may name an **item
  id or an article id** interchangeably; `story_assets._body_worn` tries
  `items/<name>.json` first, else `articles/<name>.json`.
- The geometry file is untouched — it still renders standalone on its own atlas
  plate. Each item also gets its own plate.
- One file per item (`items/<id>.json`, no suffix); the worn body's `"variant"`
  picks the geometry cut, same as a bare article.

`expand(article, palette, materials, body, color=, shade=, parts=)` applies the
override: `color` / `shade` retag every region and detail, then a `parts` entry
overrides its named region/detail on top, before the normal emit.

## Expansion

`game/graphics/expand.py` is the one code path from design JSON to render
parts. Given a design and its resolved palette it returns the flat list the
renderer already draws:

1. resolve `fit:` curves against the body's current silhouette
2. resolve `anchor:` to an animation group and offset
3. apply any **item override** (`color` / `shade` / `parts`) — an article
   worn as an `items/<id>.json` (see Items) is retagged here
4. auto-shade each region from its `shade` profile → mid / dark / light
5. resolve `color` + `tone` → rgb via the palette
6. emit parts, each tagged `group` and `role` (`fill` \| `shade_dark` \|
   `shade_light` \| `detail`)

`rig.rest_splay` (the neutral arm pose the walk cycle swings from) is **not**
applied at expand time. `expand_body` bakes it into the body's own arm/hand
sections, and an `arm_near`/`arm_far` article region is authored with the same
rotation already baked into its stored `points` — so the sleeve and the arm
share one frame with no runtime rotation, in the game and the editor alike.

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
- Rooms carry an `id` and a `color`; portals carry an `id` and either
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

## In the game

The engine draws a pipeline asset through the **same `parts` list** the atlas
renders — `WorldObject.draw_parts` already takes `{points, color}` polygons with
`[r, g, b]` or `#hex` colours, which is exactly what `expand()` emits. Nothing
is baked: the design JSON stays the only source of geometry, expanded at load
and cached.

- **Catalogue entries point at a design.** In `graphics.json` /
  `building_types.json` an entry carries `"design": "<kind>/<name>"` (plus the
  plain metadata the engine still needs — `size`, `rotation_speed`,
  `local_points`, `culture`, `windows`, …) instead of an inline `parts` list.
  `get_graphics_asset` / `get_building_type` call
  `game/graphics/story_assets.py`'s `attach_design`, which runs `expand()` once
  (cached) and fills in `parts`. Ships keep fractional coords (`Ship.draw`
  passes `unit=size`); stations and decorations are scaled to absolute units
  (`LandingSite.draw` / `draw_parts` use `unit=1`), and their `local_points`
  are authored absolute to match.
- **People.** An `outfits` entry names a pipeline body — `{body, set, palette}`.
  `Person.draw` detects this and renders through `story_assets.body_frame`: the
  body + its set's articles (or items — see Items) composed via `compose_worn`, expanded once, then
  deformed each frame by `apply_walk` at the Person's own walk-cycle phase and
  faded in by `walk_intensity`. The body faces screen-left, so `facing == 1`
  mirrors x — same rule as the baked figure. The `default` story's baked
  `person_figure` path is untouched.
- **Equipping an article at runtime.** `Person.equip_article(name)` /
  `unequip_article(name)` add or drop one article on top of a pipeline
  outfit's own set — a belt, satchel, or jacket worn without swapping the
  whole set — by mutating `outfit["extra_articles"]`, a plain list on that
  Person's own (already per-instance) outfit dict. `story_assets._body_worn`
  takes `extra_articles` as a hashable tuple and appends it after the set's
  own article list before composing, so it stays part of the same `lru_cache`
  key as `(body, set, palette)` — equipping just changes which cache entry a
  Person draws from, nothing is mutated in place. An NPC config's `"equip":
  [...]` list (read in `LocationScreen._build_local_character`) calls
  `equip_article` once per name at spawn, for wiring an accessory onto an
  existing outfit/set without a new set file.

## Atlas

A design atlas is a generated page: one plate per asset, the specimen drawn by
`expand()` + a polygons-to-SVG writer, beside the `identity` text, the detail
notes, and a spec block naming the design file's real keys. The atlas is a
viewer — it holds no geometry and no copy of anything.

## Vertex editor

[`config/editor.html`](../config/editor.html) is a standalone page for
dragging a design's vertices by hand. It renders exactly what `expand()` would —
its shading is a hand-port of `expand.py` and must be kept in step with it. Drag
any handle; double-click an edge to insert a point; alt-click to delete.

Side-panel order: story / design pickers, the mode + body + article switchers,
then the mode-specific editing panels (Polygons, Sections, Selected section,
Curves in body-edit mode; Fit in tailor mode; Outfit in outfit mode), then the
generic **View** toggles, then Output and the drafts panel. In tailor mode the
order shifts: Sections and Selected section come first, then Preview look, then
Polygons (it edits details on the selected region, so it reads better below it).

Each
section has an eye toggle to hide/show it (isolate a limb, or drop the far side
to work on the near one) and a checkbox for its handles; hiding a section takes
its handles with it. Two buttons above the list, **Show / Hide All Sections**
and **Show / Hide All Vertices**, each flip everything at once — hide all if
all are currently shown, otherwise show all (vertices only ever track the
still-visible sections). The **original ghost**
(dashed blue) is the on-disk shape, drawn behind the live edit so a redesign
pass always shows its own before/after. "Freeze shade → editable" replaces a
region's computed crescent with an explicit `shade_dark` / `shade_light` point
list you can then drag.

Load a design by pointing the **story** and design dropdowns at it (or with
`?file=<repo-relative path>` in the URL directly). Either way the real
`materials.json` and the design's palette are read too, so tones and colours
match the game exactly. An image can still be dropped onto the canvas as a
tracing overlay — that's the only file-drop the editor takes now.

### Reading and writing repo files

The editor reaches story JSON (designs, `materials.json`, palettes, the
directory listings the dropdowns need) through a small **VFS layer**
(`VFS.readJSON` / `readText` / `writeText` / `listDir`) with three backends,
picked automatically:

| backend | when | reads | writes (Saving, below) |
|---|---|---|---|
| **http** | the page is served over `http(s)://` | `fetch` | `PUT` to `serve_nocache.py`, which writes the file |
| **fsapi** | from disk (`file://`) in Chrome / Edge | File System Access API | `createWritable()` straight to disk |
| **filelist** | `file://` in a browser without that API (Firefox) | `<input webkitdirectory>` pick, read-only, re-pick each visit | — none, use download or run the server |

**Two ways in:**

- **`config/open_editor.bat`** (the normal path) — starts `serve_nocache.py`
  on port 8777 minimized if nothing's there yet, opens
  `http://127.0.0.1:8777/config/editor.html`. http backend; save works in
  every browser. Safe to double-click again — a second server just fails to
  bind and exits.
- **`config/editor.html` straight from disk** — no server. fsapi backend in
  Chrome/Edge (click **Open repo folder** once, pick the repo or its
  `config/`; the handle is saved in IndexedDB and reconnects silently or in
  one click next time), filelist in Firefox.

Then: pick a story → pick a design → edit → **save** or download.

Paths handed to the VFS are always repo-relative
(`config/stories/<story>/graphics/...`). If the user grants `config/` rather
than the repo root, `VFS.prefix` strips the leading `config/`; `vfsProbe()`
detects which by looking for `config/stories/` vs `stories/`.

**`serve_nocache.py`** is `http.server` plus two things: every response carries
`Cache-Control: no-store` (plain `http.server` sends only `Last-Modified`, so a
browser can silently serve a stale cached `editor.html` after an edit), and a
`PUT` writes the request body back to the file — restricted to `.json` under
`config/stories/`, existing files only, with an `Origin` check. Run it from the
repo root: `python config/serve_nocache.py 8777`. If the page still looks stale
(new buttons missing), Ctrl+Shift+R.

**The story picker — the editor is not tied to one story.** The tool has no
built-in story. A **story** dropdown at the top of the side panel discovers
every `config/stories/<name>/graphics/` pipeline (it lists `config/stories/`,
then keeps each entry that has a `graphics/materials.json`; `PIPELINE_STORIES`
in the script is only a fallback for a backend that can't list a directory).
This is the only way a design gets loaded (there is no hand-load / paste
route — see below). Pick a story, then the
**body / face / tailor** kind selector and the **design** dropdown beside it
list that story's `graphics/body/*.json` (body and face) or
`graphics/articles/*.json` (tailor). Picking one navigates through the normal
`?file=` boot path — `?file=<base>/body/<b>` for body, `+ &edit=face` for face,
`?file=<base>/articles/<a>&fitbody=<base>/body/<b>` for tailor (the body is the
one last tailored against in that story, remembered per story, else the first
alphabetically). So `GBASE` gets set and every dependent dropdown lights up.
(The `tailor` option's value is still `outfit` in the markup — pre-dating the
separate outfit mode; only its label changed.)

The **story** dropdown is always shown; once a design is loaded the story is
derived from its path. The **design** dropdown beside it only appears when it
isn't a no-op — nothing loaded yet, or the story dropdown points at a story
*other* than the loaded design's (switch it there and the design list
re-scopes so you can hop to another story without retyping a URL; within the
current story the edit / body / switch-to controls below cover every move).
`?story=<name>` preselects a story on a bare load; the last pick is remembered
per browser (`gpEditorStory`). This is the mechanism that makes a second pipeline story
"just work" in the editor with no code change — it only needs a `graphics/`
directory with a `materials.json`.

There is no hand-load route (a dropped file or pasted JSON carried no repo
path, so nothing downstream — palette, save, the switchers — could work); the
story picker is how every design comes in.

Coverage today is **body designs** (`sections`); other kinds (`regions`
articles, `silhouette` ships) are being folded in.

**Face mode** — `?file=<body>&edit=face`. Loads the body, pulls in its
`head.face` slot files (`faces/<slot>_<name>.json`), inlines their `details` on
the head so the whole kit can be nudged on the model, and **locks every body
silhouette vertex** — only the face pieces (polygons and `circle` details, each
with a centre and a radius handle) are draggable — the radius handle also
carries rotation: it sits at the circle's current angle rather than fixed to
the right, so dragging it both resizes and spins the n-gon in one motion (a
multi-select group rotate, `,`/`.`, spins each selected circle's own facets
by the same amount too, not just its position about the pivot). The side
panel lists the
pieces grouped by source file; click one to isolate its handles, or use a
file group's own **all**/**none** buttons to isolate/hide its whole file at
once. **all handles** above the list shows every piece — and toggles to
**select none** when everything is already showing, hiding every handle in
one click instead. Each row also carries reorder arrows (↓/↑, same meaning as
elsewhere) that move the piece within the whole merged `head.details` array —
draw order, not just visibility, and not confined to its own file's group;
they call the same `reorderDetail` the Polygons panel's layer buttons do.
Every merged
detail carries a `_src` tag naming the file it came from — Copy/Download/the
Output box all keep it (this is the one field `expand()` and a real committed
design file never see; it is stripped when the split files are written back).
**save checked to repo** (see Saving) does that split mechanically — groups the
edited details by `_src`, writes each group to the file it belongs in, `_src`
removed. A `.face-export.json` download is the merged, `_src`-tagged view for
handing to the agent, not a design file to drop straight into `config/`.

**Curves panel** — plain body-edit mode only (hidden in face and tailor mode).
Below **Selected section**, it lists the selected section's `curves` by name
and point count, each with **rename** and **delete**. **Click a curve's name**
to highlight the boundary run it traces on the model — a pink polyline with a
dot on every curve point, the two endpoints ringed white; click again (or
switch section) to clear it. Read-only: it shows what the curve currently
covers and whether the auto-recut traced the span you expect, and vertex
handles stay grabbable underneath. To add one, select
exactly two of that section's own vertices (click one, shift-click the
other) — a **span** row appears with a **go the long way around** checkbox
(a polygon has two ways from one point to the other; the checkbox picks
whichever the curve should trace, showing the vertex count for each) and a
name field (autocompletes existing names). **save curve** copies that
boundary run, in order, as the curve's `pts` polyline, and also records its
two endpoint coordinates and the walk direction (`{ pts, ends, dir }` — see
**Curve storage**, below). Reusing an existing name overwrites it.

**Auto re-cut.** Because the endpoints are stored, the editor re-traces every
curve on a section from that section's *current* silhouette on every body-vertex
move (`recutCurves` in `sync()`: each endpoint snaps to the nearest present
vertex, `walkBoundary` re-walks the span in the saved `dir`). So moving a body
point keeps every curve it lies on in line, and any outfit fitted to
`section.curve` (via the Fit panel in tailor mode, see below) follows on the
next load — including from this same browser's autosaved draft, so switching
straight from a body edit to tailoring an outfit against it (or reloading tailor
mode) already shows the re-cut curve without saving to disk. A curve
saved before this carries no `ends` and shows as **static** — re-capture it once
(same name) to switch it over. Deleting a curve that some
article's `fits` still names leaves that fit unable to resolve (`bodyCurve`
returns `null` and the fit is silently skipped) — the panel doesn't check
other files for references before deleting.

**Tailor mode** — `?file=<article>&fitbody=<body>`. Loads the article (a
`regions` design) and draws the named body underneath as a **locked,
read-only backdrop** (its own vertices never show handles). The backdrop body
and its snap-dot vertices are drawn in the game's rest pose (`rest_splay`
applied — the same frame `expand_body` produces), and the article's own
`points` are already authored in that pose, so **what you drag is exactly
where it lands in the game** — no toggle, no splay/un-splay frame to reconcile.
Each region's authored `points` still render two ways: the **Fit** panel and
handle colour show the raw, sparse authored array (fit placeholders included),
while the drawn shape adds the `_apply_fits` + `outset` result — so a free
vertex sits `outset` (~0.12u) proud of the filled edge it controls. A handle
is <span style="color:#b479ff">▪</span>
**fitted** (its position is spliced from a body curve at expand time —
dragging it does nothing) or <span style="color:#ffcf6a">▪</span> **free**
(an authored coordinate — drag it like normal). Select one fitted-or-free
vertex to open the Fit panel: a dropdown of every `section.curve` on the
body, a reverse checkbox, **apply** (writes a single-point `fits` entry) and
**make free** (drops the fit, leaving the vertex at the curve's midpoint so
it doesn't jump to a stale placeholder). `D.sections` is a display-only alias
for `D.regions` in this mode (`region0`, `region1`, …) — reused so the
existing multiselect/scale/rotate/layer/handle machinery works on regions
unchanged; it's stripped back out before it ever reaches `#out`/Copy/Download.
Select two (same region) instead of one and the panel switches to bulk mode:
**make all free** clears every fitted vertex in the selection at once.

**Filling in an edge between two snapped vertices — no curve names involved.**
Every garment vertex is a plain free point (drag + snap onto the body, below).
To trace a whole stretch of the body's edge: snap two vertices onto the body
(**snap to body vertices**), select both, and the panel finds which body
*section* they both landed on and offers to **generate the N vertices between
them** — copied straight off that section's own silhouette, no curve lookup,
no dropdown. A polygon has two ways around between any two points; a
checkbox picks the short way (default) or the long way, showing the vertex
count for each so you can tell which is which before committing. Applying
replaces whatever was between the two selected vertices (other placeholders
included) with the traced points, as plain coordinates — a one-time trace,
not a live fit: it won't follow if the body is reshaped later. If the two
selected vertices aren't both snapped onto the same body section, the panel
just says so instead of guessing.

This is separate from (and doesn't require understanding) the `fits: [{curve,
from, to}]` mechanism — no article currently carries a fit, but selecting a
single vertex still shows the curve-name panel for applying, inspecting, or
clearing one, and the purple/free colour coding still reflects it.

Every body vertex also renders as a small dot (**show body vertices**,
on by default) — visible even where the garment covers the skin, since it
draws on top of the cloth. With **snap free vertices to them** on (also
default), dragging a free vertex within the given pixel radius snaps it to
the exact coordinate of the nearest body vertex — the highlighted dot. This
is a one-time alignment, not a live fit: the vertex becomes a normal authored
coordinate that happens to match the body right now, and won't follow if the
body is reshaped later (use the Fit panel's curve dropdown for that instead).

**Outfit mode** — `?file=<body>&edit=outfit`. Loads a body on its own to
preview whole outfits — no article is edited. It reuses the tailor-mode
compose/render path (the same `compose_worn` draw order the game uses, the
compare-body panel, the walk preview) with an empty synthetic article standing
in for the edited one, so `FITBODY` points at the body itself. The side panel
drops every editing section (Polygons, Sections, Output, Fit, Reference image,
Preview look — hidden by `body.outfit-mode` CSS) and shows the **Outfit**
section plus **View**. The **Outfit** section holds the **preview articles**
checkbox list (outfit-mode only) and
the **Draw order** editor (see below) — the one place the story's
`draw_order.json` is edited. The ticked articles are still drawn while tailoring
(see **Preview other articles**). Picks are remembered per story
(`gpEditorPreviewArt:<story>`, `gpEditorHair:<story>`). The preview itself
writes nothing; the Draw order editor keeps a draft (see below). Outfit mode has
no draft of its own (there's no edited article).

**Switching body / face / tailor / outfit without retyping the URL.** Once a
body (plain, `edit=face`, `edit=outfit`, or an article fit against one) is
loaded, an **edit: body / face / tailor / outfit** button row appears near the
top of the side panel, highlighting whichever you're in. **body** and **face**
both jump to `?file=<body>` (with/without `&edit=face`); **tailor** jumps to the
article you last tailored in this tab (per story, remembered in `sessionStorage`
as `gpLastArticle:<story>`), or the alphabetically-first `articles/*.json` fit
against that same body (`fitbody=`) if you haven't tailored one yet — from there
use the **switch to** dropdown below to pick a different one; **outfit** jumps to
`?file=<body>&edit=outfit` (outfit mode, below). Hidden when the loaded design
isn't a body-rooted one (a bare, unfit article, e.g.).

**Hide/show state is remembered per tab.** Which body sections you've hidden
or whose handles you've toggled (body-edit mode), and which backdrop body
parts / snap-dots you've hidden (tailor mode), are saved to `sessionStorage`
keyed by path (`gpVis:body:<path>` / `gpVis:tailor:<fitbody>`) and restored on
load — so the `?file=` navigations the mode/body/article switchers do don't
reset your setup. `sessionStorage` lives exactly as long as the tab: close it
and the memory is gone; a second tab starts fresh. Face-mode piece isolation
isn't persisted (its `detPick` indices shift when details reorder).

Right below it, a **body** dropdown (a `body/*.json` directory listing) is the
single body switcher for all three views: in plain or face mode it switches
which body is loaded outright, staying in the same mode; in tailor mode it
swaps `fitbody=` — which body the *same* outfit is checked against — leaving
`file=` on the article.

**Switching articles without retyping the URL.** In tailor mode a **switch
to** dropdown lists every `articles/*.json` next to the loaded one — picking
one navigates to that article, fit against the same `fitbody`. It's hidden in
plain / face mode (no article in play to switch away from — use the edit
**tailor** button to get into tailoring first). It's populated by fetching the
directory listing `python -m http.server` serves for a folder with no
`index.html`; on a server that doesn't do that, the dropdown just stays
hidden rather than showing something broken. Every article is one file now, so
the list isn't gender-filtered.

Beside the dropdown a **+ new** button creates a brand-new
`articles/<name>.json` (prompts for the name — lower-case letters, digits,
underscores) and jumps straight into tailoring it against the current
`fitbody`. The stub is one placeholder region — a small quad at chest height
with its own empty `fits:` — plus `identity` / `tier` / `palette` you fill in;
the masc/femme `geometry` split is grown on the first save. Needs the repo
opened read-write (Chrome/Edge from disk, or `config/serve_nocache.py`, whose
`PUT` now creates a file when its parent directory exists).

(Switching which body the article is fit
against is the **body** dropdown near the top of the panel — it swaps
`fitbody=`, and the reload lifts that body's `geometry` cut; an unsaved edit
to the other cut stays safe in its own `:fit:<body>` draft.)

**Hiding body parts.** In tailor mode, the Fit panel lists every body
section with two toggles: the eye hides the part entirely (fill *and* its
vertex dots — the dot toggle is implied off and greys out while the part is
hidden); the dot on its own hides just the vertex dots, leaving the fill
visible as a plain reference silhouette with nothing to accidentally snap
onto. (No reorder here — body-part draw order is only editable in the Outfit
section.) Above the
list, **show all** / **hide all** toggles every part at once (the label
follows state — it reads **show all** only when every part is already
hidden), beside **hide all verts**. This list is a decluttering/preview aid —
it never touches a file (tailor mode only writes the outfit back, never the
body) — but the tab remembers it (`sessionStorage`, see **Hide/show state is
remembered per tab** above) so switching views doesn't clear it.

**A single-point fit, unfolded.** A garment vertex fitted to a curve stands
in for the *whole* curve — that's normal (a shoe with one placeholder per foot
fitted to the foot-outline curve is exactly this), but it means there's nothing
to hand-tune point by point. Selecting a single vertex shows an **unfold into N
vertices** button next to the curve dropdown: pick a curve (or leave the one
it's already fitted to) and unfold drops any fit on that vertex and replaces
it with the curve's own points as plain, independently-draggable vertices —
same splice-and-reindex machinery as the two-vertex "generate between," just
triggered from one vertex instead of a fresh selection. It works whether the
vertex is currently fitted *or* already free (clearing a fit with "make free"
doesn't strand you — pick the curve again and unfold same as before).

**Inserting more than one point.** Double-click an edge, or select two
adjacent vertices and press **I** — both insert points evenly spaced between
the pair. The **insert N point(s) at a time** field (View) controls how many;
default 1. That's still not the only way to add vertices — "generate
between" and "unfold" (above) both add many at once, tracing the body rather
than interpolating a straight line.

Every add/remove path — double-click insert, **I**, alt-click delete,
Delete-key vertex delete — shifts the region's `fits` index spans by the same
splice so a fitted vertex keeps pointing at the vertex it named (deleting a
single-point fit's own vertex drops that fit). The **I** interpolation runs in
polygon-traversal order regardless of which of the two handles was clicked
first, so the inserted run never reverses.

**Selecting a whole polygon.** Double-click any one of its handles (shift to
add another polygon to the selection).

**Duplicating a polygon.** With exactly one whole polygon or circle selected,
its fill panel (name/material/tone/layer) carries a **⧉ duplicate** button:
copies it into the same section right after itself, auto-numbering the name
off the original's own note (`"near iris"` → `"near iris 2"`, and duplicating
that copy in turn counts up rather than stacking a second number). Works the
same on a body-section polygon as on a face-kit piece — whichever section is
selected owns the copy.

**Deleting a polygon.** Select a whole polygon or circle (dbl-click) and hit
**−selected polygon(s)** or Delete/Backspace. This removes a `details` piece
on any section (face kit, decoration on a garment, …). In tailor mode it also
removes an **entire outfit region** — select all of a region's own outline
vertices (dbl-click its fill, not a detail on it) and delete: that drops the
whole piece from `D.regions`, re-aliasing `region0`/`region1`/… to match. A
body's own sections (torso, head, …) never delete this way — they're
structurally required, unlike an outfit's freestanding regions.

**Adding a region** *(tailor mode)*. The Polygons panel's **+ region** button
pushes a new standalone region onto the article — a small placeholder quad at
the view centre, its own `fits: []`, with `group` and `tag` copied from
the currently-selected region. It's selected and aliased as the next `regionN`
straight away, so you can drag, fit, and reshade it like any other. **+ polygon**
/ **+ circle** by contrast add a *detail* to the selected region — it rides that
region's group, carries no fit, and isn't auto-shaded.

**Name, group and draw order** *(tailor mode)*. The **Selected section** panel's
top rows are a **name** field (writes the region's `note` — this is what the
Sections list shows; hover a row for its `regionN` alias), an **anim. group**
dropdown (which limb the region swings with, and its default draw-stack slot),
and a **draw order** **tag** field (a text input with a datalist of the story's
existing tags). Blank = stack at the anim. group. Type an existing tag to move
the region to that slot; type a new name and it's appended to the story order
(in its draft) so you can then position it in the **Outfit** section's Draw
order editor.
**all** stamps whatever's in the field onto every region of the article (it
reads the field live, so you can type a tag and hit **all** without tabbing out
first; Enter applies it to the selected region). A pre-existing `"layer"` /
`"back"` is read as a tag and rewritten to `"tag"` on the next edit.

**Orphaned-fit warning** *(tailor mode)*. A `fits` entry whose `from` / `to`
falls outside the region's `points` array (a hand-edit, or a vertex delete in
an old editor build that didn't shift the spans) has no placeholder vertex —
`_apply_fits` then splices the curve in at the wrong place and no handle
shows, so the fitted edge is "invisible". The Fit panel flags each one in
amber with **re-point to #\<last\>** (clamp it onto the last real vertex) and
**remove fit**.

**Copy a cut to the other body** *(tailor mode, Fit panel)*. A merged article
carries a `masc` and a `femme` cut under `regions[].geometry`. The
**copy this cut → `<other body>`** button writes the cut you're editing now
over the other body's cut on disk (every region's `points` / `fits` / `details`
/ shade polys), and saves the current cut in the same write — so you get a
same-shape starting point to re-fit by hand: click it, then switch the **body**
dropdown to the other body and drag. Shown only when the fit body is one of a
`<name>_masc.json` / `<name>_femme.json` pair and the sibling file exists; needs
the repo open read-write. If an unsaved draft for the other body already exists
it offers to discard it (else that draft would still shadow the fresh copy on
the next load).

**Comparing against the other body.** When the loaded design is a body (plain
or `edit=face`) or an outfit fit against one (`?fitbody=`), a small **compare
other body** panel appears in the corner, read-only, rendered by the same
`expand()`-equivalent draw path as the main canvas. Three controls (View)
shape it independently of the main edit:

- **against** — which body it shows. Defaults to the body already being
  edited itself (labelled `(live)`) — the panel then tracks the in-memory
  edit, not a stale disk fetch, acting as a second, independently framed
  camera on the same model. The dropdown (a `body/*.json` directory listing,
  same directory-listing trick as the **body** switcher) also lists `auto —
  counterpart`, the body found by swapping `_masc`/`_femme` in the loaded (or
  `fitbody`) filename, and every other body on disk. When the panel shows a
  body of the other cut, it draws that cut's own `geometry` from the article,
  not the edited cut fitted across. Whichever you pick sticks for the rest of
  the page's session (the default only applies fresh on load); empty/hidden if
  the loaded design isn't a body-rooted one.
- **frame** — `fit panel` (default) auto-fits whatever's drawn into the small
  panel, independent of the main canvas's own zoom; `match main view` reuses
  the main canvas's exact pan/zoom instead, so the two are pixel-comparable
  but a tight main crop can run outside the smaller panel.
- **show** — `whole body` (default) or `head only`. Filters the drawn parts
  to the body's `head` section — in tailor mode this mostly only matters if
  the outfit itself has head-group parts.

In tailor mode the panel draws the *same outfit* fit against whichever body
"against" resolves to, via the same `composeWornJS`/`applyFits` path the main
canvas uses, so a fit change is checked against the other body's proportions
without leaving the page. It re-fetches whenever the loaded design, `fitbody`,
or the "against" choice changes.

**Walk animation preview.** The View section's **walk animation** checkbox
loops the drawn figure through the gait, using the same math as the game — a
hand-port of `expand.py`'s `apply_walk` (`applyWalkJS`) driven off the body's
resolved `rig.walk` file (`loadWalkRig`, from `bodyDesign.rig.walk` in tailor
mode or `D.rig.walk` when editing a body directly). It deforms the composed
parts list each `requestAnimationFrame` tick at a fixed ~1.1 s stride period
(preview pace only — the game advances the cycle by distance walked, not wall
time). The **compare other body** panel animates in lockstep (same
`applyWalkJS`, the mirror body's own pivots). Vertex handles stay in the rest
pose while it runs, so turn it off to edit. The toggle is inert (and warns) if
the body has no walk rig.

**Draw order editor** (Outfit section — outfit mode). The whole story
`draw_order.json` list, rendered top-to-bottom = back-to-front. Every row —
body section (dim, labelled *body*) or **tag** — can be reordered by its
**↑ / ↓** buttons (one step) or by **dragging the row** (a blue line marks
where it will land). This is the **only** place the body-part draw order can be
reordered (the tailor-mode tag field only assigns a region's tag). A tag row
also shows how many loaded regions use it and an **×** to drop it (regions then
fall back to their group). **+ tag** adds a new one before `front`. The figure
re-renders on every change. On open, the panel scans every `articles/*.json` and
pulls in any tag a region references that the list is missing (so a tag assigned
in another session still shows up, and no region silently dangles to the front);
tailor mode does the same for the loaded article's own tags.
Edits go to a draft (`gpDraft:<gbase>/draw_order.json`), like an article — they
show as a row in **Save / download drafts** and only reach the real
`draw_order.json` on **save checked to repo**. On load, a draw-order draft wins
over the on-disk file (same as an article draft).

**Preview hair** (tailor + outfit mode). A dropdown of every
`articles/hair_*.json`, plus *— no hair —*, sitting just under the **switch
to** row. The pick draws that hairstyle on
the body (reference only, never written), so headgear layering against real
hair can be judged — its `geometry` cut is the previewed body's. The
choice is remembered per story (`gpEditorHair:<story>`) — so the hairstyle
picked in outfit mode carries into tailor mode and back — and defaults to
`hair_short`. Hidden when the loaded design is itself a hairstyle, or when the
tailored headgear declares `hides_hair` the hair is dropped from the compose.

**Preview other articles** — the tick list `gpEditorPreviewArt:<story>` (a name
array, hairstyles excluded). Ticked articles are drawn on the figure — fitted
and outset against the body, composed by the story draw order like the game.
Nothing here is ever written.

- The **checkbox list** that adds and removes ticks lives in the **Outfit**
  section and shows only in **outfit** mode, with a **show all** / **hide all**
  button above it. Draw order is each region's tag, not the tick order.
- The ticked articles are **drawn in tailor mode too** (minus the one currently
  being tailored) — reference for fitting a new piece into an existing look.
- Opening any article for tailoring auto-adds it to the list, so a set builds up
  piece by piece and every fitted garment is there when you switch to outfit
  mode.
- Each ticked article is loaded from its **unsaved tailor draft** for the current
  body (`gpDraft:<path>:fit:<fitbody>`) when one exists, else from disk — so a
  piece you just re-fitted in tailor mode shows its new shape the moment you
  switch to outfit mode (or tick it while tailoring another piece), without a
  save-to-repo first.

**This headgear hides hair** (tailor mode, Fit panel). A checkbox that writes
top-level `"hides_hair": true` onto the article being tailored — at runtime
`_body_worn` then drops every hairstyle from any outfit wearing it (see Faces
and hair).

**Colour and shade.** Every fill panel (a region's **Selected section** panel,
a detail's **Polygons** panel, tailor mode's **Preview look**) has a **color**
dropdown (palette keys) and a **shade** dropdown (the profile names from
`materials.json`, plus `false — flat`). The two are independent — that is the
whole point of the split. Each option in the colour dropdown is tinted with the
swatch it names (Chromium/Firefox), and a swatch of the current pick sits beside
the dropdown, so you can eyeball a colour before choosing it.

**Preview look** (tailor mode). A panel directly below **Selected section** that
swaps the *whole article's* colour and/or shade in the preview only — it is how an `items/<id>.json` would
render this shared geometry. Nothing here is written to the article file (it
stays pure geometry + its own default tags); the choice is remembered per
browser (`gpPreviewLook`).

The reference body's
head also gets its `faces/<slot>_<name>.json` kit pulled in for the preview
(same mechanism as face mode) — the raw body file carries no inline face
details, so without this the head would render bare no matter what. **Hide
face** (Fit panel) is a one-click shortcut for hiding the head part — shape
*and* its now-populated eyes/nose/lips together — handy while eyeballing
where hair sits without the face competing for attention; it's the same
underlying toggle as unchecking "head" in the body-parts list below it, kept
in sync either way.

### Editing a design with the agent

When the user wants to reshape an existing asset — "let's redesign the femme
body", "the skirt hem needs work", "fix the courier canopy" — the agent runs
this loop rather than hand-editing coordinates:

1. **Open it.** Start `python config/serve_nocache.py 8777` at the repo
   root (see **Reading and writing repo files**, above — not plain
   `http.server`, which can leave the user looking at a stale cached copy of
   the editor), open the Browser pane at
   `http://127.0.0.1:8777/config/editor.html?file=<path to the design JSON>`.
   An article opens only in tailor mode — add
   `&fitbody=<...>/body/human_masc.json` (or `_femme`); that body's `variant`
   picks which `geometry` cut you edit. Switch the **body** dropdown to work
   the other cut of the same file.
2. **User edits** in the pane — drags vertices, toggles sections, freezes shade
   where auto is wrong.
3. **Preview before writing.** When the user says they're done, the agent reads
   the edited JSON out of the page (`#out` textarea), regenerates that asset's
   atlas plate through the real `expand()` (not the editor's JS port — this is
   where any drift shows), and shows the before/after render plus a JSON diff.
4. **Confirm, then replace.** On an explicit yes, either the user hits **save
   checked to repo** or the agent writes the file. Update `identity` / notes
   and any dependent doc in the same change (the two binding rules still apply).

The editor *can* write now — **save** works over http (via `serve_nocache.py`)
and from disk in Chrome/Edge. But step 3 is still the agent's: only the real
`expand()` shows shading/fit drift, and `identity` + dependent docs don't
update themselves. So the agent drives the preview and the doc updates; the
write itself can be either hand.

**Autosave drafts, and a sharp edge.** The editor autosaves the live edit to
`localStorage` under `gpDraft:<loadedPath>` (plus `:face` or `:fit:<fitbody>`
for those modes) and offers to restore it on next load of the same design — so
a browser crash or an accidental navigation doesn't lose work. The draft is
written **only once the design has actually been edited** this session (`dirty`
latches in `sync()` when the serialised design first differs from what the first
`sync()` saw; a restored draft, or JSON pasted/loaded in by hand, starts
`dirty`) — opening a file and looking at it, or just selecting vertices, leaves
the drafts list untouched; the first real edit writes the draft immediately. A
clean "save checked to repo" of the loaded design re-baselines it back to clean.
The gotcha: **these keys are shared by every tab open on the same
origin**, not per-tab. If the agent opens its own scratch tab on the same
`http://127.0.0.1:8777` origin and loads the *same* file+mode the user is
mid-edit on — even just to verify something — it silently overwrites the
user's in-progress draft with whatever the scratch tab last held. Rules that
follow from this: always open a **fresh** scratch tab for any editor
verification, never navigate or reset a tab the user is actively using, and
avoid loading the exact file+mode combination the user has open unless the
goal *is* to read their draft. When recovering drafts after a session gap
(e.g. "save what I've edited"), read every `gpDraft:*` key in the user's own
tab via `javascript_tool`, diff each against the on-disk file, and treat only
genuine, non-trivial differences as real work — many keys will just be
stale residue from earlier autosaves already superseded by a save, or a
scratch tab's own leftovers.

### Saving

The **Save / download drafts** panel's **save checked to repo** button writes
each checked draft's edits to its real file(s) — enabled on the **http**
backend (via `serve_nocache.py`'s `PUT`) and the **fsapi** backend (straight to
disk); disabled on **filelist** (Firefox from disk) with a hint to run
`open_editor.bat` instead. It resolves each draft to its target file(s), shows
a confirm listing every path it will overwrite, then writes:

- `toRepoJSON()` — 2-space indent, **ASCII-only** (`\uXXXX` for anything ≥
  0x80, matching Python's `json.dump` default, so an em-dash in `identity`
  isn't rewritten every save), numbers to 3 dp, trailing newline.
- **Never creates** a file. A drag-dropped design with no repo path, or a
  renamed asset, has nothing to overwrite and is reported as "not found".
- A draft whose files all saved cleanly is dropped from `localStorage` — the
  file now matches disk.
- Every checked row is written — the confirm's path list is the guard against a
  stale draft you forgot to uncheck. `git diff` is the review; `git checkout --
  <file>` is the undo.

A **face** draft is split on save the way the agent otherwise does by hand:
`head.details` regrouped by each detail's `_src`, the `body`-tagged ones stay
on the body file (the key is *dropped* when that group is empty — a clean body
carries no `head.details`), each `faces/<slot>_<name>` group merged back into
that slot file (its other keys — `identity` etc. — preserved, only `details`
replaced). `_src` stripped from everything written.

The agent still owns the atlas-plate preview (drift only shows through the real
`expand()`, not the editor's JS port) and the `identity` / dependent-doc
updates — those don't happen on save.

**Download.** The same panel (bottom of the side panel, below Output) lists
every `gpDraft:*` key in this browser at once — not just the design currently
loaded — with a checkbox and an editable filename per row, defaulted from the
draft's own path (`.face-export.json` for a face draft, the article's real
name for a `fit` draft). **rescan** refreshes the list (e.g. after saving one
design mid-session); **download checked** fires one `<a download>` per checked
row, staggered 200ms apart so a browser doesn't throttle a burst of same-tick
downloads. Two rows that would land on
the same filename are highlighted — most commonly one merged article edited
against both bodies (a `:fit:<masc>` draft and a `:fit:<femme>` draft), whose
**download** names disambiguate (`jacket.vs-human_masc.json` /
`jacket.vs-human_femme.json`) while **save checked to repo** writes both to the
one `jacket.json`, each folding its cut into `geometry` and taking the other
cut from disk so save order doesn't matter; a genuine same-name collision
elsewhere is left for hand-renaming, with a confirm prompt before downloading
anyway.
**clear checked** permanently removes the checked rows' keys from
`localStorage` (with a confirm prompt) and rescans — this is the only control
that actually shrinks the list. The top **Reset** button does *not* do this:
it only drops the single draft for whatever design+mode is currently loaded
(`draftKey()`), so every other body/article/face/fit draft in the browser
stays and still shows up here.

**Shade overrides.** A region (body section, article region, or ship
silhouette entry) may carry `"shade": false` to draw flat, or explicit
`"shade_dark"` / `"shade_light"` polygons (one each) used verbatim instead of
the auto-shade. For a body section `expand_body` rotates those override
polygons with the section under `rest_splay`; an article authors them already
in the rest pose, like its `points`.

**A true hole via a seamed ring (`articles/helmet.json`).** The renderer has no
transparency for pipeline parts (`opacity` is an atlas-only convenience — the
game's own `Person._draw_pipeline_body` draws every part fully opaque), so a
"visor" can't be a tinted see-through pane over the real face. Instead, author
the region as **one polygon that is already a ring**: an outer boundary (traced
in full), a seam to one point on an inner boundary, the inner boundary traced
in full but in the *opposite* rotational direction, then back to the same seam
point. `points = outer + [inner[0]] + inner[1:][::-1] + [inner[0]]`. Nothing
downstream needs to know this is special — it's still just one region's
`points` — but the space *inside* the inner ring is a genuine gap in the
polygon, not a covered patch, so whatever is drawn underneath (the real face)
shows through untouched. Set `"shade": false` on a ring region — the crescent
fitter assumes a simple silhouette and the seam confuses it. The same trick
stacked one size smaller as a `detail` gives a visor bezel that reads as a rim
around the opening without covering it. Sizing the outer boundary generously
(real clearance past every hairstyle, not fit to the head) also solves the
"hair pokes through" problem for free: the shell is opaque and drawn on a
front-of-head layer (`hair` or `front`), so anything under it — hair included —
is simply hidden by geometry, no per-article suppression logic required.

## Faces and hair

The **face kit** is `details` on the body's `head` section — eyes (socket,
sclera, iris, pupil, lid, catchlight), tapered brows, a short nose (bridge
shadow + soft tip), two-part lips. Each is a small polygon; a round one may be
written `"circle": [cx, cy, r]` (an optional 4th element, `rot`, rotates the
n-gon about its own centre in degrees; omitted/0 = unrotated) and `expand()`
turns it into an ngon — `ngon()`'s side count defaults to an octagon floor
(`max(8, min(24, r*2))`), never fewer, so a small round detail still reads as
round rather than faceted. The kit is drawn at a shallow 3/4 turn: the near
eye larger, the far one compressed. It scales with the head.

**Face slots.** The head section carries a `"face"` map — `{eyes, brows, nose,
lips: <name>}` — and `load("faces", "<slot>_<name>")` supplies each slot's
`details`. So the features are interchangeable (`eyes_almond`, `eyes_deep`,
`nose_soft`, `nose_straight`, `lips_full`, `lips_thin`, …) without editing the
body.

**Hair is an article** — `group: "head"` (so it swings with the head), tagged
for the draw stack. Its bulk regions are `"tag": "hair_back"` (a slot before
`head`, so the skull hides the back and only the volume past the silhouette
shows); the framing bits — a thin band along `head.hairline`, sideburns, a
fringe, side panels — are `"tag": "hair"` (a slot after `head`) and draw over
the face. A hat/hood/helmet region tags itself `hair` to sit over the hair,
`hair_back` to tuck behind the head. A headgear article that should cover hair
entirely carries `"hides_hair": true` instead.

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
| **D — fit** ✅ | `group` / `fits` against the body | masc body publishes torso/limb/foot curves; `duty_boots` splices each foot outline from `foot_{near,far}.shoe` on the masc cut — see Fitting |
| **E — animation** ✅ | the rig: per-group pivot swing, clothing follows, torso bob | `civilian_work` on the walk-cycle frame strip |
| **F — world scale + LOD + collision** ✅ | size vs. player, detail culls, hitbox overlay | `courier` — near / far / hitbox / beside-the-figure plates |
| **G — interior** ✅ | floor plan sized to the player, generated navmesh, lane check | `concourse` — plan + generated lanes + `column` (declared) / `bench` (clear) |
| **H — in game** ✅ | the story boots and the renderer draws all of the above | `graphics_pipeline_test` story: courier + trade ring in space, concourse + bench + column + pipeline-bodied walkers in the interior |

Gates are sequential: B needs A, D needs B and C, E needs D, H needs everything.
Move a gate or add one when the work shows a seam that needs sign-off.

## Minimal asset set (pipeline test)

All eight gates pass. The `graphics_pipeline_test` story carries only what the
gates needed and no more, and is a bootable story (`story.json` + one system +
`concourse` interior; starts docked at the trade ring with a courier):

- 2 bodies (`human_masc` / `human_femme`), 1 palette (`civilian`),
  `materials.json`, `rig_walk.json`
- articles — tops, bottoms, footwear, hair, outerwear, accessories — one file
  each, both body cuts under `regions[].geometry` — and sets composing them
- items — `coat_charcoal` / `coat_oxblood`: the one `long_coat` geometry worn
  two ways, proving the colour/shade split; the `civilian_officer` set wears
  the oxblood one
- face kits (2 each of eyes / brows / nose / lips)
- 1 ship (`courier`), 1 station (`trade_ring`)
- 1 interior (`concourse`) with 2 decorations — `column` blocks a lane on
  purpose (`blocks_lane`), `bench` must not

**The Common Kit outfit pack** — the 15 culture-neutral outfits from the
retired `common-kit.html` atlas (space/flight suit, mechanic, dockworker,
prospector, security, station command, marshal, medic, surgeon, researcher,
civilian, smuggler, ranger, bounty hunter), rebuilt from the articles above:

- `items/<garment>_<colourway>.json` — a `color` (+ `shade`, and `parts` where
  one piece is two-tone like a helmet shell + visor bezel) over one base article
  per recoloured piece (`jacket_navy`, `coat_navy`, `boots_black`, `helmet_sec`,
  `cap_amber`, `collar_white`, `hood_field`, `backpack_brown`, `bandolier_black`,
  `star_gold`, `braid_gold`, …). Colours are read off the old atlas's prose
  descriptions.
- a few small **decal articles** carry geometry the recolours can't:
  `comms_box` (dark box + red indicator beside the helmet — flight suit),
  `med_cross` (breast cross — medic), `armband_medcross` (red band + white
  cross — medic), `pen_array` (red/cyan/gold breast-pocket pens — researcher),
  `visor` (a slim eye band — recoloured `items/visor_ice` light blue for
  security + researcher, `items/visor_red` for the bounty hunter),
  `peaked_cap` (a military wheel cap — `band` + a `crown` that flares wider than
  the band + a dark forward `peak`; `items/peaked_cap_command` is Station
  Command's navy officer cap), `stand_collar` (a trapezoid collar band —
  `items/stand_collar_white` is Station Command's), `buttons` (eight octagon
  buttons in two columns — `items/buttons_gold` is Station Command's
  double-breasted grid).
- `sets/ck_<outfit>_{masc,femme}.json` — the article + item list per outfit per
  body, `palette: "civilian"`.
- `graphics.json` `outfits` `ck_<outfit>_{masc,femme}` and one concourse NPC per
  outfit (alternating body) in `systems/proving_ground.json`.

Fidelity is silhouette + colour, not every prop: pieces with no article yet
(a drill, a baton, a holster, a trek bedroll) are omitted.

Grow the set now by the per-asset gates, not the build gates.

## Authoring checklist

1. Write the `identity`. If you cannot say what is unique in two sentences,
   the design is not ready.
2. Draw the silhouette. Stay under the tier budget. Justify each vertex.
3. Split it into regions on concept lines (`group`); tag each `color` + `shade`.
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
