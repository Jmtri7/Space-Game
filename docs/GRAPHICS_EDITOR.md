# Graphics Vertex Editor

`config/editor.html` is the hand-vertex editor for the design-JSON graphics
pipeline. Pipeline concepts, the expand() contract, fitting, and the asset
gates live in [GRAPHICS_PIPELINE.md](GRAPHICS_PIPELINE.md); this document owns
the editor's UI and repo-write behaviour.

It renders exactly what `expand()` would —
its shading is a hand-port of `expand.py` and must be kept in step with it. Drag
any handle; double-click an edge to insert a point; alt-click to delete.

Side-panel order: story / design pickers, the mode + body + article switchers,
then the mode-specific editing panels (Sections, Selected section, then
**Details**, then Curves in body-edit mode; Fit in tailor mode; Outfit in
outfit mode), then the generic **View** toggles, then the lone **Undo** button
and the drafts panel. The **Details** panel (the freestanding polygons/circles
layered over a region — formerly labelled "Polygons") always sits directly
below the Sections / Selected-section selector; in tailor mode it drops one
further, below Preview look, so the region's own look controls sit next to the
section editor.

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

Load a design by picking it from the **Workspace** panel (left rail, see below),
or with `?file=<repo-relative path>` in the URL directly. Either way the real
`materials.json` and the design's palette are read too, so tones and colours
match the game exactly. An image can still be dropped onto the canvas as a
tracing overlay — that's the only file-drop the editor takes now.

### The Workspace panel

A rail down the left edge, left of the editor's own side panel and always
present; drag the divider between the two (or the one between the side panel
and the canvas) to re-size either column — widths persist per browser
(`gpEditorWsWidth` / `gpEditorSideWidth`). Until an asset is loaded the side
panel is hidden entirely, leaving just the rail and an empty canvas. It lists
**every story and every shared module** in `config/` (each
row labelled `story` / `module`); expand one and it lists that source's assets
by category — Bodies, Faces, Articles, Items, Sets, Ships, Stations, Buildings,
Decorations, Palettes, Face slots, Collision, Interiors, Graphics config, Story
config, Systems, Manifest. Categories are discovered by scanning the source's
actual subtree (graphics categories resolve across the source **and its
modules**, dependencies included — same walk as
`config_source.resolved_modules()`), so a new asset kind shows up on its own.

When a `story` / `module` row is expanded, a **`depends on:` line** under its
header lists that source's *directly declared* modules; each name is a link
that expands and scrolls to that module's own row. In the graphics categories every leaf that
doesn't resolve to the source's own dir is tagged with the module it comes
from (`badge.json · figures-human`); a source-local file that *also* exists in
a module — i.e. a kit override — is tagged `· overrides module` instead. Names
are still de-duplicated: one row per filename, showing the copy that wins.

- **Bodies / Faces / Articles** open straight into the existing editor
  (body-edit, `edit=face`, or tailor mode against the source's first body — or
  the one remembered in `gpEditorFitBody:<source>`). Navigation is the normal
  full-reload `?file=` path; the rail re-renders from `localStorage`
  (`gpEditorWorkspaceV1` — the expanded set) and marks the open asset.
- **Every other category** opens a read-only **stub** in the canvas area
  (`?ws-asset=<path>`): the raw JSON pretty-printed, with a "not implemented
  yet" banner. A placeholder until each kind gets its own editor.
- **new story… / new module…** (need the repo open read-write) write a minimal
  skeleton — `story.json` + a bare `systems/<id>_start.json` for a story
  (inherits the standard module list; **appears in the game's story picker but
  is not playable** until its system has a landing site and the `start` block
  is filled), or `module.json` (`+` an optional `graphics/materials.json` copy)
  for a module. `serve_nocache.py`'s `PUT` now creates missing parent
  directories under `config/stories/` and `config/modules/` for this.
- **↻** rescans `config/`.

The legacy `story` / kind / design dropdowns are gone; the Workspace panel
replaces them. The in-editor **edit: body / face / tailor / outfit** and
**body / switch to** rows stay — they're within-asset navigation.

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
(`config/stories/<story>/graphics/...` or `config/modules/<name>/graphics/...`).
If the user grants `config/` rather
than the repo root, `VFS.prefix` strips the leading `config/`; `vfsProbe()`
detects which by looking for `config/stories/` vs `stories/`.

**`serve_nocache.py`** is `http.server` plus two things: every response carries
`Cache-Control: no-store` (plain `http.server` sends only `Last-Modified`, so a
browser can silently serve a stale cached `editor.html` after an edit), and a
`PUT` writes the request body back to the file — restricted to `.json` under
`config/stories/` or `config/modules/`, with an `Origin` check; it overwrites
an existing file or creates a new one, **creating any missing parent
directories** under those two roots (so `new story` / `new module` can lay down
a fresh tree). Run it from the repo root:
`python config/serve_nocache.py 8777`. If the page still looks stale (new
buttons missing), Ctrl+Shift+R.

**Where a design comes from.** The **Workspace** panel (see above) is the way
in — pick a body/face/article and it navigates the normal `?file=` boot path
(`?file=<path>` for body, `+&edit=face` for face,
`?file=<article>&fitbody=<body>` for tailor). `GBASE` is the loaded file's own
`graphics` dir (every save writes there); `GMODS` is the resolved-module
graphics dirs the loaded *story* pulls in — read-only fallback + listing merge,
so a body or article that lives only in a module still resolves (`gReadJSON` /
`gListDir` / `gResolve`, and `_resolvedModuleNames` for the recursive walk).
Editing a file that resolved to a module edits the module in place (the `src`
header shows the full path). There is still no hand-load / paste route — a
dropped file carries no repo path.

Coverage today is **body designs** (`sections`), **faces**, and **articles**
(`regions`, tailor mode); every other kind opens the read-only stub.

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
they call the same `reorderDetail` the Details panel's layer buttons do.
Every merged
detail carries a `_src` tag naming the file it came from — the serialized
`#out` and the `.face-export.json` draft download both keep it (this is the one
field `expand()` and a real committed design file never see; it is stripped when
the split files are written back).
**save checked to repo** (see Saving) does that split mechanically — groups the
edited details by `_src`, writes each group to the file it belongs in, `_src`
removed. A `.face-export.json` download (from the drafts panel) is the merged,
`_src`-tagged view for handing to the agent, not a design file to drop straight
into `config/`.

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
unchanged; it's stripped back out before it ever reaches `#out`.
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
drops every editing section (Details, Sections, Output, Fit, Reference image,
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

**Adding a region** *(tailor mode)*. The Details panel's **+ region** button
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
a detail's **Details** panel, tailor mode's **Preview look**) has a **color**
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
   the edited JSON out of the page (the hidden `#out` textarea, via
   `javascript_tool`), regenerates that asset's
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

**Download.** The **Save / download drafts** panel (bottom of the side panel) lists
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

