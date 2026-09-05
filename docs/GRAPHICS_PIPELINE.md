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

The ribbon's outer edge is the region silhouette verbatim and its inner edge is
a depth-capped inward offset that is Laplacian-relaxed and corner-cut (Chaikin)
for smoothness, then snapped back inside wherever a smoothing pass pushed it out
across a concave stretch. So the shade is always **fully contained within the
region** — it never bleeds past the silhouette — and a coarsely faceted region
still gets a smoothly curved shade. Vertex count per ribbon is bounded (~30–45)
regardless of the region's own count.

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

**A fully-traced region (`"fits": []`, every vertex free) stops being
body-portable.** It renders correctly on the body it was traced against and
literally unchanged — same fixed coordinates — on any other, so a garment two
bodies share (via one outfit set, or two sets naming the same article) will
look wrong on whichever body it wasn't traced for. `tank_top_femme.json` /
`tank_top_masc.json` are separate files for exactly this reason: the femme
one is a hand-traced redesign (`fits: []`), so masc gets its own
curve-fitted file rather than sharing it. When a redesign trades fits for a
full trace, check whether anything else still expects that file to fit both
bodies before saving over the shared name.

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
  body + its set's articles composed via `compose_worn`, expanded once, then
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

[`docs/atlases/editor.html`](atlases/editor.html) is a standalone page for
dragging a design's vertices by hand. It renders exactly what `expand()` would —
its shading is a hand-port of `expand.py` and must be kept in step with it. Drag
any handle; double-click an edge to insert a point; alt-click to delete. Each
section has an eye toggle to hide/show it (isolate a limb, or drop the far side
to work on the near one) and a checkbox for its handles. The **original ghost**
(dashed blue) is the on-disk shape, drawn behind the live edit so a redesign
pass always shows its own before/after. "Freeze shade → editable" replaces a
region's computed crescent with an explicit `shade_dark` / `shade_light` point
list you can then drag.

Load a design three ways: `?file=<repo-relative path>` in the URL (needs the
page served over http, not `file://` — see **serving it** below), file-drop
onto the canvas, or paste into the Output box and hit "Load ← box". When
loaded by `?file=`, the real `materials.json` and the design's palette are
fetched too, so tones and colours match the game exactly.

**Serving it.** Use `python docs/atlases/serve_nocache.py 8777` from the repo
root, not plain `python -m http.server`. Both serve the same directory
listing the "switch to" / "fit against" / "against" dropdowns rely on, but
plain `http.server` sends only `Last-Modified` — no `Cache-Control` — so a
browser can silently reuse a stale cached copy of `editor.html` itself (not
just a design JSON) after the agent edits it, showing an old version of the
tool with no explained cause. `serve_nocache.py` is the identical handler
plus one header. If a page still looks stale after that (new markup/buttons
missing), a hard refresh (Ctrl+Shift+R) forces a re-fetch either way.

Opening `editor.html` straight from disk (`file://...`) does not work — every
`?file=`/directory-listing/materials/palette lookup is a `fetch()` call, which
browsers block against `file://`. There has to be a server. For a one-click
launch without a terminal, double-click **`docs/atlases/open_editor.bat`**
(Windows) — starts `serve_nocache.py` on port 8777 minimized in the
background if nothing's listening there yet, then opens the editor (no
`?file=`; use Load file / drag-drop, or bookmark a specific `?file=` URL)
in the default browser. Safe to double-click again later — if a server's
already up, the new one just fails to bind and exits; the browser still
opens against the existing one.
Coverage today is **body designs** (`sections`); other kinds (`regions`
articles, `silhouette` ships) are being folded in.

**Loading without a `?file=` URL.** Opening the bare editor (`open_editor.bat`,
no query string), or picking/dragging a file in, gets you a design with no
known repo path — the browser's File API only hands over a bare filename, not
where it lives in the tree — so `GBASE` never gets set and every dropdown
that depends on it (the mode switcher, mirror "against", "switch to"
articles, "fit against") stays hidden even once something's loaded. A
**start on** dropdown appears whenever that's the case, listing every real
`body/*.json` by its actual repo path (`PIPELINE_STORIES` in the script names
which story bases to check — currently just `graphics_pipeline_test`, the
only one with a `graphics/` pipeline; extend that list if a second one grows
one); picking one goes through the normal `?file=` boot path instead, and
everything lights up. It hides itself the moment a real path is known.

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
design file never see; the agent strips it when it writes the split files
back). On save the agent groups the edited details by `_src` and writes each
group to the file it belongs in — mechanical, no guessing from `note` text.
A `.face-export.json` download is that merged, `_src`-tagged view, not a
design file to drop straight into `config/` — hand it to the agent instead.

**Tailor mode** — `?file=<article>&fitbody=<body>`. Loads the article (a
`regions` design) and draws the named body underneath as a **locked,
read-only backdrop** (its own vertices never show handles). Each region's
authored `points` render two ways: the **Fit** panel and handle colour show
the raw, sparse authored array (fit placeholders included), while the drawn
shape is always the real `_apply_fits` + `outset` result, so what you see is
what the game draws. A handle is <span style="color:#b479ff">▪</span>
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
from, to}]` mechanism a real garment file like `tank_top_masc.json` already uses —
selecting a single vertex still shows the curve-name panel for inspecting or
clearing an existing fit, since that's how the shipped data works and the
purple/free colour coding still reflects it.

Every body vertex also renders as a small dot (**show body vertices**,
on by default) — visible even where the garment covers the skin, since it
draws on top of the cloth. With **snap free vertices to them** on (also
default), dragging a free vertex within the given pixel radius snaps it to
the exact coordinate of the nearest body vertex — the highlighted dot. This
is a one-time alignment, not a live fit: the vertex becomes a normal authored
coordinate that happens to match the body right now, and won't follow if the
body is reshaped later (use the Fit panel's curve dropdown for that instead).

**Switching body / face / outfit without retyping the URL.** Once a body
(plain, `edit=face`, or an outfit fit against one) is loaded, an **edit: body
/ face / outfit** button row appears near the top of the side panel,
highlighting whichever you're in. **body** and **face** both jump to
`?file=<body>` (with/without `&edit=face`); **outfit** jumps to the
alphabetically-first `articles/*.json` fit against that same body (`fitbody=`)
— from there use the **switch to** dropdown below to pick a different one, or
the mode row again to hop back to the body or its face. Hidden when the
loaded design isn't a body-rooted one (a bare, unfit article, e.g.).

Right below it, a **body** dropdown (plain or face mode only — a
`body/*.json` directory listing) switches which body is loaded outright,
staying in the same mode. Tailor mode doesn't show this row; its own **fit
against** dropdown in the Fit panel is the equivalent there (switches which
body the outfit is checked against instead of loading the body itself).

**Switching articles without retyping the URL.** Once a design is loaded, a
**switch to** dropdown appears listing every `articles/*.json` next to it —
picking one navigates to that article, keeping the current `fitbody` (or
dropping it if you weren't in tailor mode). It's populated by fetching the
directory listing `python -m http.server` serves for a folder with no
`index.html`; on a server that doesn't do that, the dropdown just stays
hidden rather than showing something broken. In tailor mode a second
**fit against** dropdown does the same for `body/*.json` — swaps which body
the *same* article is checked against without retyping the URL.

**Hiding body parts.** In tailor mode, the Fit panel lists every body
section with two toggles: the eye hides the part entirely (fill *and* its
vertex dots — the dot toggle is implied off and greys out while the part is
hidden); the dot on its own hides just the vertex dots, leaving the fill
visible as a plain reference silhouette with nothing to accidentally snap
onto. A pair of reorder arrows between them previews the reference body's own
`draw_order` (same up/down arrows as the Sections list elsewhere). Nothing in
this list is saved anywhere — it's a decluttering/preview aid, reset per page
load; tailor mode only ever writes the outfit back, never the body.

**A single-point fit, unfolded.** A garment vertex fitted to a curve stands
in for the *whole* curve — that's normal (`shoes.json`'s one placeholder per
foot is exactly this, doing real work), but it means there's nothing to
hand-tune point by point. Selecting a single vertex shows an **unfold into N
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

**Comparing against the other body.** When the loaded design is a body (plain
or `edit=face`) or an outfit fit against one (`?fitbody=`), a small **compare
other body** panel appears in the corner, read-only, rendered by the same
`expand()`-equivalent draw path as the main canvas. Three controls (View)
shape it independently of the main edit:

- **against** — which body it shows. Defaults to the body already being
  edited itself (labelled `(live)`) — the panel then tracks the in-memory
  edit, not a stale disk fetch, acting as a second, independently framed
  camera on the same model. The dropdown (a `body/*.json` directory listing,
  same trick as the tailor mode "fit against" picker) also lists `auto —
  counterpart`, the body found by swapping `_masc`/`_femme` in the loaded (or
  `fitbody`) filename, and every other body on disk. Whichever you pick
  sticks for the rest of the page's session (the default only applies fresh
  on load); empty/hidden if the loaded design isn't a body-rooted one.
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

**Draw order against the body.** A region's `over`/`under` (body section or
group names — same field the real game's `compose_worn` reads) is honoured
in the preview: a region tagged `"under": ["torso"]` draws behind the whole
body, `"over": ["head"]` draws after it, exactly like hair's back-drape and
front-cap regions are meant to. Without an explicit `over`/`under` a region
draws with its own animation group, same as the game. The reference body's
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

1. **Open it.** Start `python docs/atlases/serve_nocache.py 8777` at the repo
   root (see **Serving it**, above — not plain `http.server`, which can leave
   the user looking at a stale cached copy of the editor after a later
   change), open the Browser pane at
   `http://127.0.0.1:8777/docs/atlases/editor.html?file=<path to the design JSON>`.
   For an article, the bare body is the reference; open the body too if the fit
   matters.
2. **User edits** in the pane — drags vertices, toggles sections, freezes shade
   where auto is wrong.
3. **Preview before writing.** When the user says they're done, the agent reads
   the edited JSON out of the page (`#out` textarea), regenerates that asset's
   atlas plate through the real `expand()` (not the editor's JS port — this is
   where any drift shows), and shows the before/after render plus a JSON diff.
4. **Confirm, then replace.** Only on an explicit yes does the agent write the
   file over the old one. Update `identity` / notes and any dependent doc in the
   same change (the two binding rules still apply).

The agent stays in the loop for step 4 — the editor never writes to the repo.

**Autosave drafts, and a sharp edge.** The editor autosaves the live edit to
`localStorage` under `gpDraft:<loadedPath>` (plus `:face` or `:fit:<fitbody>`
for those modes) on every change, and offers to restore it on next load of
the same design — so a browser crash or an accidental navigation doesn't
lose work. The gotcha: **these keys are shared by every tab open on the same
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

**Batch download.** The **Batch download** panel (bottom of the side panel,
below Output) lists every `gpDraft:*` key in this browser at once — not just
the design currently loaded — with a checkbox and an editable filename per
row, defaulted from the draft's own path (`.face-export.json` for a face
draft, the article's real name for a `fit` draft). **rescan** refreshes the
list (e.g. after saving one design mid-session); **download checked** fires
one `<a download>` per checked row, staggered 200ms apart so a browser
doesn't throttle a burst of same-tick downloads. Two rows that would land on
the same filename are highlighted — most commonly the same article edited in
two separate tailor-mode sessions against different bodies, which the panel
auto-disambiguates (`hair_bun.vs-human_femme.json` /
`hair_bun.vs-human_masc.json`); a genuine same-name collision elsewhere is
left for hand-renaming, with a confirm prompt before downloading anyway.
**clear checked** permanently removes the checked rows' keys from
`localStorage` (with a confirm prompt) and rescans — this is the only control
that actually shrinks the list. The top **Reset** button does *not* do this:
it only drops the single draft for whatever design+mode is currently loaded
(`draftKey()`), so every other body/article/face/fit draft in the browser
stays and still shows up here.

**Shade overrides.** A region (body section or ship silhouette entry) may carry
`"shade": false` to draw flat, or explicit `"shade_dark"` / `"shade_light"`
polygons (one each) used verbatim instead of the auto-shade. `expand()` honours
them and rotates them with the region under `rest_splay`.

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
"hair pokes through" problem for free: the shell is opaque and drawn `"over":
["head"]`, so anything under it - hair included - is simply hidden by
geometry, no per-article suppression logic required.

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
| **D — fit** ✅ | `group` / `fits` against the body | `tank_top_masc` sides spliced from the masc torso curves |
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
- articles — tops, bottoms, footwear, hair — and sets composing them
- face kits (2 each of eyes / brows / nose / lips)
- 1 ship (`courier`), 1 station (`trade_ring`)
- 1 interior (`concourse`) with 2 decorations — `column` blocks a lane on
  purpose (`blocks_lane`), `bench` must not

Grow the set now by the per-asset gates, not the build gates.

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
