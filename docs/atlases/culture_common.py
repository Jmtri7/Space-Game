"""Shared building blocks for the seven per-culture frontier atlases
(Deeprock / Kessari / Meridian / Theln / Kaethar / Vetl / Salt Crows).

Each culture's content lives in `<key>_kit.py` as six dicts -- SHIPS, STATION,
BUILDINGS, FURNITURE, OUTFITS, LAYOUTS -- of `key -> (fn, name[, role])`.
`gen_culture.py` wraps them in the shared page shell.

Everything is strokeless: `<polygon>` + `<circle>` only (plus `<text>` for a
stencilled label), on void-black, so a specimen could be extracted into
`parts` the same way Resin & Rivets was. Ship viewBox 240x200 (nose up,
centre ~120,100); figure viewBox 140x210; building/furniture 200x200;
layout 320x200.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import (poly, circ, ngon, rrect, offset_poly, opoly, ocirc, bar,
                    ring_strip, oring, _u, GRID)
from atlas_shell import css, DEFS

OUT = "#141219"


# ---------------------------------------------------------------- primitives
def grid_bg(w=240.0, h=200.0):
    return poly([(0, 0), (w, 0), (w, h), (0, h)], GRID)


def ribbon(pts, w, col, op=None):
    """Open polyline -> filled ribbon (a thick line as one polygon)."""
    pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    if len(pts) < 2:
        return ""
    n = len(pts)
    left, right = [], []
    for i in range(n):
        if i == 0:
            d = _u((pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]))
        elif i == n - 1:
            d = _u((pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
        else:
            d1 = _u((pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
            d2 = _u((pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
            d = _u((d1[0] + d2[0], d1[1] + d2[1]))
        nb = (-d[1], d[0])
        left.append((pts[i][0] + nb[0] * w, pts[i][1] + nb[1] * w))
        right.append((pts[i][0] - nb[0] * w, pts[i][1] - nb[1] * w))
    return poly(left + right[::-1], col, op=op)


def opoly_s(pts, fill, d=1.2, ol=OUT):
    """offset-outline behind + fill -- like gen_si.opoly but keeps the arg name."""
    return poly(offset_poly(pts, d), ol) + poly(pts, fill)


def dot_run(x0, y0, x1, y1, n, r, col):
    if n < 2:
        return circ(x0, y0, r, col)
    return "".join(circ(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1), r, col)
                   for i in range(n))


def rivets_line(x0, y0, x1, y1, n, r, col):
    return dot_run(x0, y0, x1, y1, n, r, col)


def teeth(x0, x1, y, h, n, col, down=True):
    s = 1 if down else -1
    step = (x1 - x0) / n
    pts = [(x0, y)]
    for i in range(n):
        pts.append((x0 + step * (i + 0.5), y + s * h))
        pts.append((x0 + step * (i + 1), y))
    return poly(pts + [(x1, y - s * 0.5), (x0, y - s * 0.5)], col)


def chevrons(x0, x1, y, w, h, col, down=True, n=3):
    s = 1 if down else -1
    step = (x1 - x0) / n
    out = []
    for i in range(n):
        cx = x0 + step * (i + 0.5)
        out.append(poly([(cx - w, y), (cx, y + s * h), (cx + w, y),
                         (cx + w - 1.4, y), (cx, y + s * (h - 2.2)), (cx - w + 1.4, y)], col))
    return "".join(out)


def radial_holes(cx, cy, r, n, dot, col, rings=(1.0,)):
    out = [circ(cx, cy, dot * 1.4, col)]
    for rr in rings:
        for k in range(n):
            a = 2 * math.pi * k / n
            out.append(circ(cx + r * rr * math.cos(a), cy + r * rr * math.sin(a), dot, col))
    return "".join(out)


def groove(x, y, w, h, col):
    return poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], col)


def flame(x, y, w, length, col):
    return poly([(x - w, y), (x, y + length), (x + w, y)], col, cls="flame")


def wave_pts(x0, x1, y, amp, n, phase=0.0):
    return [(x0 + (x1 - x0) * i / n,
             y + amp * math.sin(phase + math.pi * 2 * i / n * 1.5)) for i in range(n + 1)]


def scallop_hem(x0, x1, y, depth, n, col):
    step = (x1 - x0) / n
    pts = [(x0, y - depth)]
    for i in range(n):
        pts.append((x0 + step * i, y - depth))
        pts.append((x0 + step * (i + 0.5), y + depth))
    pts.append((x1, y - depth))
    return poly(pts, col)


def label(items, fill="#c7d0de", size=6):
    """items: list of (x, y, text). A stencil label group for a layout plan."""
    inner = "".join(f'<text x="{x}" y="{y}" text-anchor="middle">{t}</text>' for x, y, t in items)
    return (f'<g fill="{fill}" font-family="IBM Plex Mono, monospace" '
            f'font-size="{size}" letter-spacing="0.3">{inner}</g>')


def stencil(x, y, text, fill, size=7):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-family="IBM Plex Mono, monospace" '
            f'font-size="{size}" text-anchor="middle" letter-spacing="0.5">{text}</text>')


# ---------------------------------------------------------------- page shell
_SWATCH_LABELS = [("hull / wall", "hull"), ("hull shadow", "hull_lo"),
                  ("glass / lights", "glass"), ("thrust", "thrust"), ("trim", "trim")]


def _swatches(pal):
    return "".join(
        f'<div class="sw"><i style="background:{pal[k]}"></i>'
        f'<span><b>{lbl}</b>{pal[k].upper()}</span></div>'
        for lbl, k in _SWATCH_LABELS if k in pal)


def _directives(rubric):
    return "".join(f"<li><b>{t}</b> {d}</li>" for t, d in rubric)


def _diagram(inner, vlabel, vb="0 0 240 200", cls="diagram"):
    return (f'<div class="viewport {cls}"><svg viewBox="{vb}" role="img" aria-label="{vlabel}">'
            f'{inner}</svg><span class="vlabel">{vlabel[:46]}</span>'
            f'<span class="isnew">Mockup</span></div>')


def _plate(diagram_html, title, role, body, spec_rows="", full=""):
    spec = ""
    if spec_rows or full:
        fullhtml = f'<dd class="full">{full}</dd>' if full else ""
        spec = f'<dl class="spec">{spec_rows}{fullhtml}</dl>'
    return (f'<article class="plate">{diagram_html}<div class="plate-body">'
            f'<h3>{title} <span class="mk">MOCKUP</span></h3>'
            f'<p class="role">{role}</p><p>{body}</p>{spec}</div></article>')


def _section(sid, heading, lead, plates):
    return (f'<section class="chapter" id="{sid}"><p class="chapter-kicker">{heading}</p>'
            f'<h2>{heading}</h2><p class="lead">{lead}</p>{plates}</section>')


def _grid_cards(items):
    """items: (svg_inner, vb, caption, sub)."""
    cards = "".join(
        f'<figure class="card"><svg viewBox="{vb}" role="img" aria-label="{cap}">{inner}</svg>'
        f'<figcaption><b>{cap}</b><p class="role">{sub}</p></figcaption></figure>'
        for inner, vb, cap, sub in items)
    return f'<div class="grid-outfits">{cards}</div>'


def build_page(c, kit):
    """c: culture meta dict. kit: the <key>_kit module."""
    pal = c["pal"]
    nav = "".join(f'<a href="#{s}">{lbl}</a>' for s, lbl in
                  [("ships", "Ships"), ("station", "Station"), ("buildings", "Buildings"),
                   ("furniture", "Furniture"), ("outfits", "Outfits"), ("layouts", "Layouts")])

    # ---- ships: grid of cards, first one also gets a full plate
    ship_cards = []
    for key, entry in kit.SHIPS.items():
        fn, name = entry[0], entry[1]
        sub = entry[2] if len(entry) > 2 else "ship"
        ship_cards.append((fn(pal), "0 0 240 200", name, sub))
    lead_key = next(iter(kit.SHIPS))
    lead_fn, lead_name = kit.SHIPS[lead_key][0], kit.SHIPS[lead_key][1]
    ships_html = (
        _plate(_diagram(lead_fn(pal), f"Top-down {lead_name}: {c['ship']}"),
               lead_name, "ship_types.json &middot; graphics.json &rarr; ship type", c["ship"],
               f'<dt>silhouette</dt><dd>{c["rubric"][0][0].rstrip(".")}</dd>'
               f'<dt>colours</dt><dd>hull <code class="f">metal_color</code> &middot; '
               f'lights <code class="f">glass_color</code> &middot; '
               f'exhaust <code class="f">thrust_color</code> &middot; '
               f'trim <code class="f">wall_trim_color</code></dd>',
               'Strokeless, so extractable into <code class="f">parts</code> via '
               '<code class="f">extract_atlas.py</code>. The <code class="f">class="flame"</code> '
               'jet stays procedural (<code class="f">Ship._draw_thrusters</code>).')
        + _grid_cards(ship_cards))

    # ---- station
    st_fn, st_name = kit.STATION["station"][0], kit.STATION["station"][1]
    station_html = _plate(
        _diagram(st_fn(pal), f"Top-down {st_name}: {c['station']}"),
        st_name, "graphics.json &rarr; space_stations", c["station"],
        '<dt>on</dt><dd>hull polygon + <code class="f">windows</code>, or a '
        '<code class="f">parts</code> list</dd>')

    # ---- buildings / furniture as card grids
    def cards(d, vb="0 0 200 200"):
        out = []
        for key, entry in d.items():
            fn, name = entry[0], entry[1]
            sub = entry[2] if len(entry) > 2 else ""
            out.append((fn(pal), vb, name, sub))
        return _grid_cards(out)

    buildings_html = cards(kit.BUILDINGS)
    furniture_html = cards(kit.FURNITURE)

    # ---- outfits
    from gen_si import figure_parts
    ocards = []
    for key, entry in kit.OUTFITS.items():
        fn, name = entry[0], entry[1]
        role = entry[2] if len(entry) > 2 else ""
        base, pre, post = fn()
        inner = (poly([(0, 0), (140, 0), (140, 210), (0, 210)], GRID)
                 + pre + "".join(figure_parts(**base)) + post)
        ocards.append((inner, "0 0 140 210", name, role))
    outfits_html = _grid_cards(ocards)

    # ---- layouts
    lcards = []
    for key, entry in kit.LAYOUTS.items():
        fn, name = entry[0], entry[1]
        sub = entry[2] if len(entry) > 2 else ""
        lcards.append((fn(pal), "0 0 320 200", name, sub))
    layouts_html = _grid_cards(lcards)

    sections = (
        _section("ships", "Ships",
                 f"{len(kit.SHIPS)} hulls on the culture's silhouette rules. {c['ships_lead']}",
                 ships_html)
        + _section("station", "Station",
                   f"The {c['tab']} orbital, on the same shape language as the hulls.",
                   station_html)
        + _section("buildings", "Buildings",
                   c["buildings_lead"], buildings_html)
        + _section("furniture", "Furniture &amp; decorations",
                   c["furniture_lead"], furniture_html)
        + _section("outfits", "Outfits",
                   c["outfits_lead"], outfits_html)
        + _section("layouts", "Station &amp; city layouts",
                   "Floor plans on the interior model &mdash; room polygons, a portal, a "
                   "walk lane, furniture placed by rule.", layouts_html))

    return f"""<meta charset="utf-8">
<title>{c['name']}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap">
{css(c['accent'], c['accent_rgb'])}
{DEFS}
<header class="topbar"><div class="wrap">
  <span class="mark">{c['mark']}</span>
  <nav class="navlinks">{nav}</nav>
  <span class="tag-wip">Proposed culture &middot; nothing in config</span>
</div></header>

<main class="wrap">
  <section class="hero">
    <p class="eyebrow">Frontier culture design atlas &middot; Past the Reach</p>
    <h1>{c['tagline']}</h1>
    <p class="dek">{c['dek']}</p>
    <div class="status">{c['status']}</div>
    <dl class="legend" id="read">
      <div><dt>Every plate a mockup</dt><dd>Nothing here is in <code class="f">config/</code>. Spec blocks name real fields but are suggestions, never patches.</dd></div>
      <div><dt>Shapes only</dt><dd>Every specimen is <code class="f">&lt;polygon&gt;</code> + <code class="f">&lt;circle&gt;</code>, no stroke &mdash; outline is a larger offset shape behind.</dd></div>
      <div><dt>One silhouette</dt><dd>Ship, station, building and furniture all read from the same numbered rubric below.</dd></div>
      <div><dt>Its own kit</dt><dd>The outfits carry a signature piece &mdash; {c['signature_line']} &mdash; that no other culture wears.</dd></div>
    </dl>
    <div class="identity" style="margin-top:40px">
      <div><div class="swatches">{_swatches(pal)}</div>
        <p style="margin:14px 0 0;font-size:.8rem;color:var(--ink-3);font-family:'IBM Plex Mono',monospace">cultures.json &rarr; <code class="f">{c['key']}</code> &mdash; proposed, not in config</p></div>
      <ol class="directives">{_directives(c['rubric'])}</ol>
    </div>
  </section>
{sections}
  <section class="wiring" id="wiring">
    <h2>Wiring in</h2>
    <div class="wiring-grid">
      <section><h4>cultures.json</h4><p>One entry &mdash; <code class="f">name</code>, <code class="f">description</code>, the colour keys shown, a <code class="f">theme</code> string, an <code class="f">interior_decoration</code> generator. Self-contained; assets reference it by key.</p></section>
      <section><h4>ship_types.json + graphics.json</h4><p>One row per hull. Each ship silhouette here is strokeless and can be extracted into <code class="f">parts</code> via <code class="f">extract_atlas.py</code> / <code class="f">apply_parts.py</code> &mdash; add a row to the <code class="f">T</code> table.</p></section>
      <section><h4>outfits &amp; the figure renderer</h4><p>The recoloured base of each outfit is a <code class="f">graphics.json</code> entry. The signature pieces are baked geometry &mdash; the same path as the shipped cultures: a signature function in a <code class="f">{c['key']}_outfits.py</code>, baked by <code class="f">build_figure_signatures.py</code> into <code class="f">figure_signatures.py</code>, emitted by <code class="f">Person.draw()</code>.</p></section>
      <section><h4>system + routine</h4><p>{c['routine_line']} A culture is half a faction without a system to live in, a pilot roster and an AI routine.</p></section>
    </div>
    <div class="risk"><b>Adding a culture is additive; adding ship types and outfits is not free.</b> A new ship type shows in every shipyard and a new outfit in every outfitter &mdash; an old save loading a shop sees the new stock. That's a story-version bump (see <code class="f">SAVE_SYSTEM.md</code>), not a breakage: NPCs and outfits rebuild from story config on load.</div>
    <p class="lead" style="margin-top:30px">Part of <b>Past the Reach</b> &mdash; seven proposed frontier cultures. Companion atlases: <b>Common Kit</b>, <b>Sol Federation</b>, <b>Vherathi Concord</b>, <b>Drossholt Company</b>. Same visual system, same strokeless rule, same <code class="f">figure_parts</code> body.</p>
  </section>
</main>
<footer><div class="wrap">{c['name']} &middot; proposed frontier culture &middot; mockup, nothing in config &middot; Past the Reach</div></footer>
"""


FORBIDDEN = ('feGaussianBlur', 'backdrop-filter', 'background-attachment:fixed',
             'IntersectionObserver', 'stroke="', 'stroke-width', '<ellipse', '<line ',
             '<path ', '@keyframes')
