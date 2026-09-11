"""Design-atlas renderer for the Graphics Pipeline (docs/GRAPHICS_PIPELINE.md).

A viewer: it holds no geometry. It loads design JSON, runs the shared
game.graphics.expand, and writes each specimen as inline SVG polygons beside
its identity text. Run from repo root:

    python config/stories/graphics_pipeline_test/docs/pipeline_atlas.py

Writes four pages next to this script, cross-linked at the top:
  pipeline-bodies.html      - the body variants, face kit, hair, walk rig
  pipeline-structures.html  - the ship, station, interior + its furniture
  pipeline-articles.html    - every base article in its authored colour (grid)
  pipeline-outfits.html     - every assembled set (grid)
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))
sys.path.insert(0, ROOT)
from game.graphics.expand import expand, compose_worn, apply_walk  # noqa: E402

STORY = "graphics_pipeline_test"
GDIR = os.path.join(ROOT, "config", "stories", STORY, "graphics")


def load(*parts):
    with open(os.path.join(GDIR, *parts), encoding="utf-8") as f:
        return json.load(f)


def load_story(fname):
    """A story-root file (cultures.json, story.json, ...) - a level above GDIR."""
    with open(os.path.join(GDIR, "..", fname), encoding="utf-8") as f:
        return json.load(f)


def palette_for(design):
    return load("palettes", design["palette"] + ".json")


def load_asset(kind, name):
    try:
        return load(kind, name + ".json")
    except FileNotFoundError:
        return None


try:
    DRAW_ORDER = load("draw_order.json").get("order")   # story worn-figure stack
except FileNotFoundError:
    DRAW_ORDER = None


def xbody(body):
    """expand a body, resolving its face slots."""
    return expand(body, palette_for(body), load("materials.json"), load=load_asset)


def worn_parts(name, pal, materials, body):
    """A set-list entry -> expanded parts. `name` may be an item (items/<n>.json,
    an article geometry + its own colour/shade) or a bare article id."""
    it = load_asset("items", name)
    if it and it.get("geometry"):
        art = load("articles", it["geometry"] + ".json")
        return expand(art, pal, materials, body=body, color=it.get("color"),
                      shade=it.get("shade"), parts=it.get("parts"))
    return expand(load("articles", name + ".json"), pal, materials, body=body)


def svg_specimen(parts, vb=(-8, -34, 16, 36), px=440, ground=True, ticks=None):
    x0, y0, w, h = vb
    out = [f'<svg viewBox="{x0} {y0} {w} {h}" width="{px}" '
           f'height="{px * h / w:.0f}" xmlns="http://www.w3.org/2000/svg">']
    out.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#0d0f13"/>')
    if ground:
        out.append(f'<rect x="{x0}" y="-0.15" width="{w}" height="0.3" fill="#2b3a2b"/>')
    for t in ticks or []:
        out.append(f'<rect x="{x0}" y="{t - 0.03:.2f}" width="0.6" height="0.06" fill="#3a4656"/>')
    for p in parts:
        pts = p.get("points")
        if not pts:
            continue
        c = p["color"]
        d = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
        op = p.get("opacity")
        if len(pts) == 2:                       # a stroked line (deck grid, seams)
            w = p.get("width", 0.4)
            oa = f' stroke-opacity="{op}"' if op is not None else ""
            out.append(f'<polyline points="{d}" fill="none" '
                       f'stroke="rgb({c[0]},{c[1]},{c[2]})" stroke-width="{w}"{oa}/>')
        elif len(pts) >= 3:
            oa = f' fill-opacity="{op}"' if op is not None else ""
            out.append(f'<polygon points="{d}" fill="rgb({c[0]},{c[1]},{c[2]})"{oa}/>')
    out.append("</svg>")
    return "".join(out)


def body_plate(name):
    design = load("body", name + ".json")
    materials = load("materials.json")
    pal = palette_for(design)
    parts = expand(design, pal, materials, load=load_asset)
    ph = materials["scale"]["PLAYER_H"]
    ticks = [-ph * k / 7 for k in range(8)]
    nverts = sum(len(p["points"]) for p in parts if "points" in p)
    return f"""
    <section class="plate">
      <div class="spec">{svg_specimen(parts, ticks=ticks)}</div>
      <div class="meta">
        <h2>{name}</h2>
        <p class="identity">{design['identity']}</p>
        <p class="stat">tier <b>{design.get('tier', '-')}</b> &middot;
           {len(parts)} parts &middot; {nverts} vertices &middot;
           {len(design['sections'])} sections</p>
        <p class="stat">height {ph} u &middot; 7 head-ticks shown</p>
      </div>
    </section>"""


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>{title}</title><style>
body{{background:#15171c;color:#c9ccd2;font:14px/1.5 system-ui,sans-serif;margin:0;padding:32px}}
h1{{font-size:20px}} .banner{{color:#8a94a6;margin-bottom:24px}}
.nav{{margin:0 0 20px}} .nav a{{color:#8ab4f8;text-decoration:none}} .nav a:hover{{text-decoration:underline}}
.plate{{display:flex;gap:24px;align-items:flex-start;border-top:1px solid #2a2e37;padding:24px 0}}
.spec{{flex:0 0 auto}} .meta{{max-width:520px}} h2{{font-size:16px;margin:0 0 6px}}
.identity{{color:#e7e9ee}} .stat{{color:#8a94a6;font-size:12px;margin:4px 0}}
svg{{border:1px solid #2a2e37}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px;margin-top:8px}}
.card{{border:1px solid #2a2e37;border-radius:6px;padding:14px;background:#191b21}}
.card svg{{width:100%;height:auto;display:block}}
.card h2{{margin:12px 0 4px}}
.card .identity{{font-size:12px;color:#c9ccd2;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}}
</style></head><body>
<h1>{title}</h1>
<p class="nav">{nav}</p>
<p class="banner">Rendered by <code>game.graphics.expand</code> - the same code the
game runs. Nothing here is wired into a playable story yet.</p>
{body}
</body></html>"""

ATLASES = [
    ("pipeline-bodies.html", "Human Bodies"),
    ("pipeline-structures.html", "Civilian Structures"),
    ("pipeline-articles.html", "Civilian Articles"),
    ("pipeline-outfits.html", "Civilian Outfits"),
]


def _nav(current):
    return "atlases: " + " &nbsp;&middot;&nbsp; ".join(
        f"<b>{t}</b>" if f == current else f'<a href="{f}">{t}</a>'
        for f, t in ATLASES)


def _names(sub, keep=lambda n: True):
    d = os.path.join(GDIR, sub)
    if not os.path.isdir(d):
        return []
    return sorted(n[:-5] for n in os.listdir(d)
                  if n.endswith(".json") and not n.startswith("rig_") and keep(n))


def _write(fname, title, plates):
    out = os.path.join(_HERE, fname)
    with open(out, "w", encoding="utf-8") as f:
        f.write(PAGE.format(title=title, nav=_nav(fname), body=plates))
    print("wrote", out)


def compare_plate():
    materials = load("materials.json")
    ph = materials["scale"]["PLAYER_H"]
    names = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "body")) if n.endswith(".json") and not n.startswith("rig_"))
    body = []
    dx = 0.0
    for name in names:
        design = load("body", name + ".json")
        parts = expand(design, palette_for(design), materials, load=load_asset)
        for p in parts:
            q = dict(p)
            q["points"] = [[x + dx, y] for x, y in p["points"]]
            body.append(q)
        dx += 12.0
    ticks = [-ph * k / 7 for k in range(8)]
    svg = svg_specimen(body, vb=(-7, -34, 12 * len(names) + 2, 36), px=360, ticks=ticks)
    return f"""
    <section class="plate">
      <div class="spec">{svg}</div>
      <div class="meta"><h2>variants, same scale</h2>
      <p class="identity">{' &nbsp;|&nbsp; '.join(names)}</p>
      <p class="stat">7 head-ticks &middot; player height {ph} u</p></div>
    </section>"""


def _shift(parts, dx):
    return [dict(p, points=[[x + dx, y] for x, y in p["points"]]) for p in parts if "points" in p]


def article_plate(name):
    design = load("articles", name + ".json")
    materials = load("materials.json")
    ph = materials["scale"]["PLAYER_H"]
    ticks = [-ph * k / 7 for k in range(8)]
    bodies = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "body")) if n.endswith(".json") and not n.startswith("rig_"))
    combined = []
    dx = 0.0
    for bn in bodies:
        body = load("body", bn + ".json")
        bp = xbody(body)
        ap = expand(design, palette_for(design), materials, body)
        combined += _shift(compose_worn(body, bp, ap, order=DRAW_ORDER), dx)
        dx += 12.0
    nvert = sum(len(p.get("points", [])) for p in expand(design, palette_for(design), materials,
                                                         load("body", bodies[0] + ".json")))
    svg = svg_specimen(combined, vb=(-7, -34, 12 * len(bodies) + 2, 36), px=360, ticks=ticks)
    return f"""
    <section class="plate">
      <div class="spec">{svg}</div>
      <div class="meta">
        <h2>{name}</h2>
        <p class="identity">{design['identity']}</p>
        <p class="stat">{" &middot; ".join(bodies)} &middot; {nvert} article vertices</p>
      </div>
    </section>"""


def article_card(name):
    """A compact grid card: the article on both bodies in its authored colour,
    its name and identity. No overrides, no stat block."""
    design = load("articles", name + ".json")
    materials = load("materials.json")
    bodies = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "body"))
                    if n.endswith(".json") and not n.startswith("rig_"))
    combined, dx = [], 0.0
    for bn in bodies:
        body = load("body", bn + ".json")
        ap = expand(design, palette_for(design), materials, body)
        combined += _shift(compose_worn(body, xbody(body), ap, order=DRAW_ORDER), dx)
        dx += 12.0
    svg = svg_specimen(combined, vb=(-7, -34, 12 * len(bodies) + 2, 36), px=300)
    return f"""
    <div class="card">{svg}
      <h2>{name}</h2>
      <p class="identity">{design['identity']}</p>
    </div>"""


def item_plate(name):
    it = load("items", name + ".json")
    geom = load("articles", it["geometry"] + ".json")
    materials = load("materials.json")
    pal = palette_for(geom)
    ph = materials["scale"]["PLAYER_H"]
    ticks = [-ph * k / 7 for k in range(8)]
    bodies = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "body"))
                    if n.endswith(".json") and not n.startswith("rig_"))
    combined, dx = [], 0.0
    for bn in bodies:
        body = load("body", bn + ".json")
        ap = expand(geom, pal, materials, body=body, color=it.get("color"),
                    shade=it.get("shade"), parts=it.get("parts"))
        combined += _shift(compose_worn(body, xbody(body), ap, order=DRAW_ORDER), dx)
        dx += 12.0
    svg = svg_specimen(combined, vb=(-7, -34, 12 * len(bodies) + 2, 36), px=360, ticks=ticks)
    look = ", ".join(filter(None, [
        f"color {it['color']}" if it.get("color") else None,
        f"shade {it['shade']}" if it.get("shade") else None,
        "parts " + " ".join(f"{k}={v.get('color', v.get('shade', '?'))}"
                             for k, v in it["parts"].items()) if it.get("parts") else None,
    ]))
    return f"""
    <section class="plate">
      <div class="spec">{svg}</div>
      <div class="meta">
        <h2>item: {name}</h2>
        <p class="identity">{it['identity']}</p>
        <p class="stat">geometry <code>{it['geometry']}</code> &middot; {look}</p>
      </div>
    </section>"""


def face_plate():
    materials = load("materials.json")
    bodies = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "body")) if n.endswith(".json") and not n.startswith("rig_"))
    combined, dx = [], 0.0
    for bn in bodies:
        body = load("body", bn + ".json")
        parts = xbody(body)
        combined += _shift(parts, dx)
        dx += 6.0
    svg = svg_specimen(combined, vb=(-3.6, -32.2, 6 * len(bodies) + 1.4, 7.6),
                       px=560, ground=False, ticks=None)
    return f"""
    <section class="plate">
      <div class="spec">{svg}</div>
      <div class="meta"><h2>face kit</h2>
      <p class="identity">{' &middot; '.join(bodies)} &mdash; heads at 3/4 turn</p></div>
    </section>"""


def hair_plate():
    materials = load("materials.json")
    hairs = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "articles"))
                   if n.startswith("hair_") and n.endswith(".json"))
    bodies = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "body")) if n.endswith(".json") and not n.startswith("rig_"))
    rows = []
    for bn in bodies:
        body = load("body", bn + ".json")
        bp = xbody(body)
        combined, dx = [], 0.0
        for label in ["(bare)"] + hairs:
            parts = list(bp)
            if label != "(bare)":
                art = load("articles", label + ".json")
                parts = compose_worn(body, bp, expand(art, palette_for(art), materials, body), order=DRAW_ORDER)
            combined += _shift(parts, dx)
            dx += 5.6
        svg = svg_specimen(combined, vb=(-3.4, -33.0, 5.6 * (len(hairs) + 1) + 1.2, 9.0),
                           px=620, ground=False, ticks=None)
        rows.append(f'<div class="spec">{svg}</div>')
    return f"""
    <section class="plate">
      <div style="flex:1">{"".join(rows)}
        <p class="stat">rows: {" &middot; ".join(bodies)} &middot; cols: bare, {", ".join(h[5:] for h in hairs)}</p></div>
      <div class="meta"><h2>hair styles</h2>
      <p class="identity">Each style fits <code>head.hairline</code> and adds free volume; the same file renders on either head.</p></div>
    </section>"""


def set_plate(name):
    design = load("sets", name + ".json")
    materials = load("materials.json")
    ph = materials["scale"]["PLAYER_H"]
    ticks = [-ph * k / 7 for k in range(8)]
    bodies = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "body")) if n.endswith(".json") and not n.startswith("rig_"))
    pal = load("palettes", design["palette"] + ".json")
    combined, dx = [], 0.0
    for bn in bodies:
        body = load("body", bn + ".json")
        bp = xbody(body)
        aps = [worn_parts(a, pal, materials, body) for a in design["articles"]]
        combined += _shift(compose_worn(body, bp, *aps, order=DRAW_ORDER), dx)
        dx += 12.0
    svg = svg_specimen(combined, vb=(-7, -34, 12 * len(bodies) + 2, 36), px=360, ticks=ticks)
    return f"""
    <section class="plate">
      <div class="spec">{svg}</div>
      <div class="meta"><h2>set: {name}</h2>
      <p class="identity">{design['identity']}</p>
      <p class="stat">{" + ".join(design['articles'])}</p></div>
    </section>"""


def set_card(name):
    """A compact grid card: the assembled outfit on both bodies, its name, its
    article/item list."""
    design = load("sets", name + ".json")
    materials = load("materials.json")
    pal = load("palettes", design["palette"] + ".json")
    bodies = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "body"))
                    if n.endswith(".json") and not n.startswith("rig_"))
    combined, dx = [], 0.0
    for bn in bodies:
        body = load("body", bn + ".json")
        aps = [worn_parts(a, pal, materials, body) for a in design["articles"]]
        combined += _shift(compose_worn(body, xbody(body), *aps, order=DRAW_ORDER), dx)
        dx += 12.0
    svg = svg_specimen(combined, vb=(-7, -34, 12 * len(bodies) + 2, 36), px=300)
    return f"""
    <div class="card">{svg}
      <h2>{name}</h2>
      <p class="identity">{design['identity']}</p>
      <p class="stat">{" + ".join(design['articles'])}</p>
    </div>"""


def _craft_parts(design, lod):
    mats = load("materials.json")
    pal = load("palettes", design["palette"] + ".json")
    s = design["size"]
    parts = expand(design, pal, mats, lod=lod)
    return [dict(p, points=[[x * s, y * s] for x, y in p["points"]]) for p in parts]


def craft_plate(kind, name):
    design = load(kind, name + ".json")
    s = design["size"]
    near = _craft_parts(design, 240)
    far = _craft_parts(design, 13)
    coll = load("collision", name + ".json")
    hb = [{"points": [[x * s, y * s] for x, y in coll["footprint"]],
           "color": [230, 90, 200], "opacity": 0.32}]
    vb = (-s * 1.25, -s * 1.35, s * 2.5, s * 2.7)
    # scale-vs-player: bare femme (feet at y0) beside the craft (centred at mid-height)
    fig = _shift(xbody(load("body", "human_femme.json")), -(s + 8))
    craftL = [dict(p, points=[[x + s * 0.15, y - s * 0.5] for x, y in p["points"]]) for p in near]
    span = max(s * 2.6, 40)
    cmp_vb = (-(s + 12), -s - 4, span, s + 6)
    return f"""
    <section class="plate">
      <div class="spec">{svg_specimen(near, vb=vb, px=280, ground=False)}</div>
      <div class="spec">{svg_specimen(far, vb=vb, px=280, ground=False)}</div>
      <div class="spec">{svg_specimen(near + hb, vb=vb, px=280, ground=False)}</div>
      <div class="spec">{svg_specimen(fig + craftL, vb=cmp_vb, px=280, ground=True)}</div>
      <div class="meta">
        <h2>{kind[:-1]}: {name}</h2>
        <p class="identity">{design['identity']}</p>
        <p class="stat">size <b>{s}</b> &middot; {design.get('scale_note','')}</p>
        <p class="stat">near (all detail) &middot; far (~13 px) &middot;
           hitbox overlay &middot; beside the player figure</p>
      </div>
    </section>"""


def _place(parts, at, angle):
    import math
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    ox, oy = at
    out = []
    for p in parts:
        if "points" not in p:
            continue
        out.append(dict(p, points=[[ox + x * ca - y * sa, oy + x * sa + y * ca]
                                   for x, y in p["points"]]))
    return out


def interior_plate(name):
    from game.graphics.navmesh import check_placements
    design = load("interiors", name + ".json")
    mats = load("materials.json")
    pal = load("palettes", design["palette"] + ".json")
    decos = {d: load("decorations", d + ".json")
             for d in {pl["decoration"] for pl in design["placements"]}}
    cols = {d: load("collision", d + ".json") for d in decos}

    from game.graphics.expand import resolve_color
    floor = []
    for room in design["rooms"] + design["portals"]:
        rgb = resolve_color(room.get("color", "hull"), 0, pal)
        floor.append({"points": room["points"], "color": rgb})

    raster, lane_cells, report = check_placements(design, decos, cols)
    lane_dots = []
    for c, r in lane_cells:
        x, y = raster.centre(c, r)
        h = raster.cell * 0.32
        lane_dots.append({"points": [[x - h, y - h], [x + h, y - h], [x + h, y + h], [x - h, y + h]],
                          "color": [240, 210, 90], "opacity": 0.9})

    deco_parts, hitboxes = [], []
    for pl, rep in zip(design["placements"], report):
        d = decos[pl["decoration"]]
        parts = expand(d, load("palettes", d["palette"] + ".json"), mats)
        deco_parts += _place(parts, pl["at"], pl.get("angle", 0))
        fp = _place([{"points": cols[pl["decoration"]]["footprint"]}], pl["at"], pl.get("angle", 0))[0]
        colr = [230, 70, 70] if rep["fault"] else ([120, 210, 130] if rep["allowed"] else [230, 90, 200])
        hitboxes.append(dict(fp, color=colr, opacity=0.34))

    xs = [x for room in design["rooms"] for x, y in room["points"]]
    ys = [y for room in design["rooms"] for x, y in room["points"]]
    pad = 10
    vb = (min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)
    plan = svg_specimen(floor + deco_parts, vb=vb, px=520, ground=False)
    lanes = svg_specimen(floor + lane_dots + deco_parts + hitboxes, vb=vb, px=520, ground=False)

    rows = "".join(
        f"<li>{r['decoration']} at {r['at']}: "
        + ("<b style='color:#e64646'>ON A LANE, not declared - FAULT</b>" if r["fault"]
           else "on a lane, declared <code>blocks_lane</code> - ok" if r["on_lane"]
           else "clear of lanes - ok") + "</li>"
        for r in report)

    # in-game the LocationScreen dresses this floor from the culture; the atlas
    # renders the bare navmesh plan, so note what the running interior adds.
    finish = ""
    try:
        cultures = load_story("cultures.json")
        if any(c.get("interior_decoration") for c in cultures.values()):
            finish = ("<p class='stat'>floor decoration: the culture's "
                      "<code>interior_decoration</code> pack is layered on top "
                      "(not shown), over the Space View starfield where the "
                      "interior config sets <code>space_backdrop</code>.</p>")
    except FileNotFoundError:
        pass
    return f"""
    <section class="plate">
      <div class="spec">{plan}</div>
      <div class="spec">{lanes}</div>
      <div class="meta">
        <h2>interior: {name}</h2>
        <p class="identity">{design['identity']}</p>
        <p class="stat">floor plan &middot; generated lanes (yellow) + placed hitboxes
          (green = declared blocker, magenta = clear, red = fault)</p>
        {finish}
        <ul class="stat">{rows}</ul>
      </div>
    </section>"""


def _footprint_spec(coll, px=120):
    """A small top-down plan of a collision footprint - a grey fill with the
    magenta hitbox over it."""
    if not (coll and coll.get("footprint")):
        return ""
    fp = coll["footprint"]
    xs, ys = [p[0] for p in fp], [p[1] for p in fp]
    r = max(max(xs) - min(xs), max(ys) - min(ys), 6) * 0.72
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    svg = svg_specimen([{"points": fp, "color": [118, 124, 132]},
                        {"points": fp, "color": [230, 90, 200], "opacity": 0.32}],
                       vb=(cx - r, cy - r, 2 * r, 2 * r), px=px, ground=False)
    return f'<div class="spec">{svg}</div>'


def _elevation_spec(design, parts, px, fig_scale=1.0):
    """The design drawn as its authored elevation (feet at y=0, up = -y),
    beside the player figure for scale."""
    xs = [q[0] for p in parts if "points" in p for q in p["points"]]
    ys = [q[1] for p in parts if "points" in p for q in p["points"]]
    fig = _shift(xbody(load("body", "human_femme.json")), min(xs) - 9)
    allx = [q[0] for p in fig for q in p["points"]] + xs
    h = max(-min(ys), 31.0) + 4
    vb = (min(allx) - 3, -h - 2, (max(allx) - min(allx)) + 6, h + 5)
    return svg_specimen(fig + parts, vb=vb, px=px, ground=True)


def decoration_plate(name):
    """One decoration (decorations/<name>.json), authored as an elevation: its
    side view beside the player figure, and its top-down collision footprint."""
    design = load("decorations", name + ".json")
    pal = load("palettes", design["palette"] + ".json")
    parts = expand(design, pal, load("materials.json"))
    coll = load_asset("collision", name)
    lane = " &middot; blocks lanes" if coll and coll.get("blocks_lane") else ""
    return f"""
    <section class="plate">
      <div class="spec">{_elevation_spec(design, parts, 240)}</div>
      {_footprint_spec(coll)}
      <div class="meta">
        <h2>decoration: {name}</h2>
        <p class="identity">{design['identity']}</p>
        <p class="stat">{design.get('scale_note', '')}</p>
        <p class="stat">elevation (as authored) beside the figure &middot;
          top-down footprint (magenta){lane}</p>
      </div>
    </section>"""


def building_plate(name):
    """One settlement building (buildings/<name>.json), authored as an
    elevation: its facade beside the player figure, and its footprint."""
    design = load("buildings", name + ".json")
    pal = load("palettes", design["palette"] + ".json")
    parts = expand(design, pal, load("materials.json"))
    coll = load_asset("collision", name)
    return f"""
    <section class="plate">
      <div class="spec">{_elevation_spec(design, parts, 320)}</div>
      {_footprint_spec(coll, px=150)}
      <div class="meta">
        <h2>building: {name}</h2>
        <p class="identity">{design['identity']}</p>
        <p class="stat">{design.get('scale_note', '')}</p>
        <p class="stat">facade (as authored) beside the player figure &middot;
          top-down footprint (magenta)</p>
      </div>
    </section>"""


def settlement_plate(name):
    """A surface-settlement floor plan (interiors/<name>.json with `structures`):
    the paved rooms, the buildings and decorations placed on them, then the
    same view with every footprint overlaid."""
    from game.graphics.expand import resolve_color
    design = load("interiors", name + ".json")
    mats = load("materials.json")
    pal = load("palettes", design["palette"] + ".json")

    floor = [{"points": r["points"],
              "color": resolve_color(r.get("color", "hull"), "mid", pal)}
             for r in design["rooms"]]
    portals = [{"points": p["points"], "color": [86, 116, 150], "opacity": 0.55}
               for p in design.get("portals", [])]

    # every structure and decoration, placed as an upright billboard rising from
    # its floor anchor (elevation designs: base at `at`, up = -y) - exactly how
    # LocationScreen draws it. Sorted south-first so nearer things draw on top.
    placed = [("buildings", s["building"], s) for s in design.get("structures", [])] \
        + [("decorations", p["decoration"], p) for p in design.get("placements", [])]
    placed.sort(key=lambda t: t[2]["at"][1])
    body, hitboxes = [], []
    for kind, ident, spec in placed:
        d = load(kind, ident + ".json")
        body += _place(expand(d, load("palettes", d["palette"] + ".json"), mats),
                       spec["at"], spec.get("angle", 0))
        c = load_asset("collision", ident)
        if c and c.get("footprint"):
            hitboxes.append(dict(_place([{"points": c["footprint"]}], spec["at"], spec.get("angle", 0))[0],
                                 color=[230, 90, 200], opacity=0.26))

    xs = [x for r in design["rooms"] for x, y in r["points"]] \
        + [q[0] for p in body for q in p["points"]]
    ys = [y for r in design["rooms"] for x, y in r["points"]] \
        + [q[1] for p in body for q in p["points"]]
    pad = 24
    vb = (min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)
    regolith = [{"points": [[vb[0], vb[1]], [vb[0] + vb[2], vb[1]],
                            [vb[0] + vb[2], vb[1] + vb[3]], [vb[0], vb[1] + vb[3]]],
                 "color": [138, 129, 117]}]
    plan = svg_specimen(regolith + floor + portals + body, vb=vb, px=560, ground=False)
    over = svg_specimen(regolith + floor + portals + body + hitboxes, vb=vb, px=560, ground=False)
    return f"""
    <section class="plate">
      <div class="spec">{plan}</div>
      <div class="spec">{over}</div>
      <div class="meta">
        <h2>settlement: {name}</h2>
        <p class="identity">{design['identity']}</p>
        <p class="stat">paved plaza on regolith &middot; blue = the landing-pad
          portal &middot; second view overlays every footprint (magenta)</p>
      </div>
    </section>"""


def walk_plate(set_name="civilian_work_femme", frames=8):
    materials = load("materials.json")
    rig = load("body", "rig_walk.json")
    bodies = sorted(n[:-5] for n in os.listdir(os.path.join(GDIR, "body")) if n.endswith(".json") and not n.startswith("rig_"))
    sd = load("sets", set_name + ".json")
    pal = load("palettes", sd["palette"] + ".json")
    rows = []
    for bn in bodies:
        body = load("body", bn + ".json")
        worn = compose_worn(body, xbody(body), *[worn_parts(a, pal, materials, body) for a in sd["articles"]], order=DRAW_ORDER)
        combined, dx = [], 0.0
        for k in range(frames):
            combined += _shift(apply_walk(worn, body, rig, k / frames), dx)
            dx += 8.0
        svg = svg_specimen(combined, vb=(-6, -34, 8 * frames + 2, 36), px=110 * frames,
                           ground=True, ticks=None)
        rows.append(f'<div class="spec">{svg}</div>')
    return f"""
    <section class="plate">
      <div style="flex:1">{"".join(rows)}
        <p class="stat">{set_name} &middot; {frames} frames of the cycle &middot; {" / ".join(bodies)}</p></div>
      <div class="meta"><h2>walk cycle</h2>
      <p class="identity">Each limb group is rotated about its body pivot by <code>rig_walk.json</code>'s
      swing; the clothing shares the group so it swings with the limb. Torso, head and arms ride a bob.</p></div>
    </section>"""


def main():
    # 1. Human Bodies - the body variants at one scale, the face kit, the hair
    # grid, the walk cycle. (compare_plate / hair_plate already cover every body
    # and every hairstyle, so no per-body / per-hair plates repeat them.)
    bodies = compare_plate() + face_plate() + hair_plate() + walk_plate()
    _write("pipeline-bodies.html", "Human Bodies", bodies)

    # 2. Civilian Structures - the ship, the station, the station interior, the
    # surface settlement + its buildings, and every furniture decoration.
    struct = "\n".join(craft_plate("ships", n) for n in _names("ships"))
    struct += "\n".join(craft_plate("stations", n) for n in _names("stations"))
    for n in _names("interiors"):
        design = load("interiors", n + ".json")
        struct += settlement_plate(n) if design.get("structures") else interior_plate(n)
    struct += "\n".join(building_plate(n) for n in _names("buildings"))
    struct += "\n".join(decoration_plate(n) for n in _names("decorations"))
    _write("pipeline-structures.html", "Civilian Structures", struct)

    # 3. Civilian Articles - every base article in its authored colour, gridded.
    _write("pipeline-articles.html", "Civilian Articles",
           '<div class="grid">'
           + "".join(article_card(n) for n in _names("articles")) + "</div>")

    # 4. Civilian Outfits - every assembled set, gridded.
    _write("pipeline-outfits.html", "Civilian Outfits",
           '<div class="grid">'
           + "".join(set_card(n) for n in _names("sets")) + "</div>")


if __name__ == "__main__":
    main()
