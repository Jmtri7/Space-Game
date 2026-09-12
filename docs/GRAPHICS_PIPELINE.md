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

Every file below is resolved through the story's shared modules: `story_assets._load()`
checks `config/stories/<story>/graphics/<rel>` first, then each
`config/modules/<m>/graphics/<rel>` the story lists — first hit wins, so a
story overrides a shared kit file by dropping its own copy at the same path.
`materials.json` is instead **merged** across story + modules. See
[CONFIG_MODULES.md](CONFIG_MODULES.md); the `figures-human` module is the
shared human-figure kit today.

```
config/stories/<story>/graphics/   (+ config/modules/<m>/graphics/ for shared kit files)
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
├── buildings/   <building>.json      — an elevation facade (view: elevation)
├── decorations/ <decoration>.json    — furniture: top-down, or view: elevation
├── collision/   <id>.json         — hitboxes, one file per asset, loaded on their own
└── interiors/   <interior>.json   — floor plan: rooms, portals, decoration + building placements
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

Edit the list in the vertex editor's **Outfit** section (see [GRAPHICS_EDITOR.md](GRAPHICS_EDITOR.md)).

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

A low prefab outpost's buildings can sit well below the `building` row's 4×
nominal — e.g. ~2–3× player tall — and that's fine; it's not a city block.
Each design's `scale_note` states its real size.

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
- **Elevation billboards.** A `buildings/` or `decorations/` design with
  `"view": "elevation"` is authored feet-at-`y=0`, up = `-y`, centre-line
  `x=0` — the same figure space as a person. `attach_design` copies the flag
  onto the catalogue entry; `draw_parts` at `unit=1` draws it as an upright
  billboard rising from its floor anchor. `_structure_depth` sorts it by its
  floor line (`max` local y ≈ 0), like a person's feet. `_building_footprint`
  puts its collision box's **front edge exactly on that base line** (no front
  lip) and the box extends *behind* it by `footprint.depth`. No per-structure
  rotation. A plain top-down decoration (no `view`) still draws flat.

  The `footprint` for an elevation asset is derived from its own geometry:
  `width` = the silhouette's span where it meets the floor (roof overhangs
  excluded), `depth` ≈ `0.6 × min(width, height)` (a rough guess at how far
  the real 3D object reaches back), never wider than `width`. `collision/`
  and the `building_types.json` entry both carry it.
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

There is no maintained atlas-generator script. Use the vertex editor below, or
the running game, to check a design's render.

## Vertex editor

[`config/editor.html`](../config/editor.html) is a standalone page for dragging a
design's vertices by hand — it renders exactly what `expand()` would. Its UI,
modes (body / face / tailor / outfit), the fit and draw-order panels, and how it
reads and writes repo files are documented in **[GRAPHICS_EDITOR.md](GRAPHICS_EDITOR.md)**.

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
| **H — in game** ✅ | a story boots and the renderer draws all of the above | courier + trade ring in space, concourse + bench + column + pipeline-bodied walkers in the interior |

Gates are sequential: B needs A, D needs B and C, E needs D, H needs everything.
Move a gate or add one when the work shows a seam that needs sign-off.

## Minimal asset set (pipeline test)

All eight gates pass. The set below is what the gates needed and no more, and
is enough for a bootable story (a `story.json` + one system + a `concourse`
interior; docked at a trade ring with a courier) — it now lives in the
`figures-human` / `orbital-std` shared modules rather than a standalone story:

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
  `garrison_cap` (a soft creased side cap, pointed front and back, `curtain`
  seam, no peak; `items/garrison_cap_command` is Station Command's navy one),
  `stand_collar` (a trapezoid collar band that flares wider at the top —
  `items/stand_collar_white` is Station Command's), `buttons` (eight octagon
  buttons in two columns — `items/buttons_gold` is Station Command's
  double-breasted grid), `long_coat_closed` (the `long_coat` cut with the two
  front panels meeting on the midline and a `centre placket` seam — worn navy
  by Station Command via `items/coat_command`, charcoal by the Marshal via
  `items/coat_marshal`).
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
