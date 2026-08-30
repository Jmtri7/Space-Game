"""Redraw resin-and-rivets.html under the Standard Issue rules:
ONLY <polygon> + <circle>, no stroke. Two paths:

  - ships / stations / buildings / furniture / interiors: a mechanical
    SVG converter (path/rect/ellipse/line -> polygon/circle; every stroke
    becomes a mitre-offset outline behind the shape; a fill:none stroked
    circle becomes a ring_strip so its hole stays transparent; the bloom
    <filter> defs are dropped - flat bright fills on void-black already read
    as lit). The design of each specimen is preserved exactly.

  - the six culture outfits (Reefwright, Vault-Warden, Tide-Pilot, Cutterman,
    Tallyman, Gun-Bo's'n): rebuilt on the new legged + armed Person body from
    gen_si.figure_parts, keeping each outfit's spirit but matching the SI models.
"""
import sys, re, pathlib, math
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import (poly, circ, ngon, rrect, _u, offset_poly, opoly, ocirc,
                    ring_strip, bar, sq, figure_parts, GRID, OUT)

SRC = pathlib.Path("docs/atlases/resin-and-rivets.html")
html = SRC.read_text(encoding="utf-8")

num = r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?'
def nums(s): return [float(x) for x in re.findall(num, s or "")]

# ---- open polyline -> filled ribbon (a "thick line" as one polygon) ----
def ribbon(pts, w, col, op=None):
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

def rectpts(x, y, w, h, rx):
    if rx and rx > 0.5:
        return rrect(x, y, w, h, min(rx, w / 2, h / 2), seg=2)
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

# ---- SVG path flattening (from extract_atlas.py) ----
def flatten_path(d, seg=7):
    tokens = re.findall(r'([MmLlHhVvCcSsQqTtAaZz])|(' + num + r')', d)
    i, cmds = 0, []
    while i < len(tokens):
        letter = tokens[i][0]
        if not letter:
            i += 1; continue
        args, j = [], i + 1
        while j < len(tokens) and not tokens[j][0]:
            args.append(float(tokens[j][1])); j += 1
        cmds.append((letter, args)); i = j
    subs, cur = [], []
    x = y = sx = sy = 0.0
    prev_c2 = None
    for letter, a in cmds:
        rel = letter.islower(); L = letter.upper(); k = 0
        if L == "M":
            while k < len(a):
                nx, ny = a[k], a[k + 1]
                if rel: nx += x; ny += y
                if k == 0:
                    if cur: subs.append(cur)
                    cur = [(nx, ny)]; sx, sy = nx, ny
                else:
                    cur.append((nx, ny))
                x, y = nx, ny; k += 2
        elif L == "L":
            while k < len(a):
                nx, ny = a[k], a[k + 1]
                if rel: nx += x; ny += y
                cur.append((nx, ny)); x, y = nx, ny; k += 2
        elif L == "H":
            for v in a:
                nx = x + v if rel else v
                cur.append((nx, y)); x = nx
        elif L == "V":
            for v in a:
                ny = y + v if rel else v
                cur.append((x, ny)); y = ny
        elif L in ("C", "S"):
            step = 6 if L == "C" else 4
            while k < len(a):
                if L == "C":
                    c1 = (a[k], a[k + 1]); c2 = (a[k + 2], a[k + 3]); end = (a[k + 4], a[k + 5])
                else:
                    c1 = (2 * x - prev_c2[0], 2 * y - prev_c2[1]) if prev_c2 else (x, y)
                    c2 = (a[k], a[k + 1]); end = (a[k + 2], a[k + 3])
                if rel:
                    c1 = (c1[0] + x, c1[1] + y) if L == "C" else c1
                    c2 = (c2[0] + x, c2[1] + y); end = (end[0] + x, end[1] + y)
                for t in range(1, seg + 1):
                    tt = t / seg; mt = 1 - tt
                    bx = mt**3 * x + 3 * mt**2 * tt * c1[0] + 3 * mt * tt**2 * c2[0] + tt**3 * end[0]
                    by = mt**3 * y + 3 * mt**2 * tt * c1[1] + 3 * mt * tt**2 * c2[1] + tt**3 * end[1]
                    cur.append((bx, by))
                prev_c2 = c2; x, y = end; k += step
        elif L in ("Q", "T"):
            step = 4 if L == "Q" else 2
            while k < len(a):
                if L == "Q":
                    c1 = (a[k], a[k + 1]); end = (a[k + 2], a[k + 3])
                else:
                    c1 = (2 * x - prev_c2[0], 2 * y - prev_c2[1]) if prev_c2 else (x, y)
                    end = (a[k], a[k + 1])
                if rel:
                    if L == "Q": c1 = (c1[0] + x, c1[1] + y)
                    end = (end[0] + x, end[1] + y)
                for t in range(1, seg + 1):
                    tt = t / seg; mt = 1 - tt
                    bx = mt**2 * x + 2 * mt * tt * c1[0] + tt**2 * end[0]
                    by = mt**2 * y + 2 * mt * tt * c1[1] + tt**2 * end[1]
                    cur.append((bx, by))
                prev_c2 = c1; x, y = end; k += step
        elif L == "A":
            while k < len(a):
                rx, ry, rot, laf, sf, ex, ey = a[k:k + 7]
                if rel: ex += x; ey += y
                # sample a circular arc (good enough for the small arcs used here)
                for t in range(1, seg + 1):
                    tt = t / seg
                    cur.append((x + (ex - x) * tt, y + (ey - y) * tt))
                x, y = ex, ey; k += 7
        elif L == "Z":
            if cur:
                cur.append((sx, sy)); subs.append(cur); cur = []
                x, y = sx, sy
    if cur: subs.append(cur)
    return subs

# ---- the converter ----
VB = [0, 0, 240, 200]

def _col(v):
    return v if v and v not in ("none",) and not v.startswith("url(") else None

def _bg_poly():
    return poly([(VB[0], VB[1]), (VB[0] + VB[2], VB[1]),
                (VB[0] + VB[2], VB[1] + VB[3]), (VB[0], VB[1] + VB[3])], GRID)

def _is_bg(pts):
    x0, y0, x1, y1 = (min(p[0] for p in pts), min(p[1] for p in pts),
                      max(p[0] for p in pts), max(p[1] for p in pts))
    return (x1 - x0) >= VB[2] * 0.95 and (y1 - y0) >= VB[3] * 0.95

def emit(tag, el, st):
    raw_fill = st.get("fill")
    fill = _col(raw_fill)
    stroke = _col(st.get("stroke"))
    sw = float(st.get("stroke-width") or 1) if stroke else 0
    op = st.get("opacity")
    op = float(op) if op not in (None, "1") else None
    flame = "flame" in (el.get("class") or "").split()
    out = []

    def g(k, d=0.0):
        v = el.get(k)
        return float(v) if v is not None else d

    def filled(pts, f):
        if len(pts) < 3 or f is None:
            return
        if stroke and not flame:
            out.append(poly(offset_poly(pts, sw * 0.55), stroke))
        out.append(poly(pts, f, cls="flame" if flame else None, op=op))

    if tag == "polygon":
        pts = list(zip((n := nums(el.get("points")))[0::2], n[1::2]))
        if fill is None and stroke is None:            # bg grid, or nothing
            if _is_bg(pts):
                out.append(_bg_poly())
        else:
            filled(pts, fill or stroke)
    elif tag == "rect":
        x, y, w, h = g("x"), g("y"), g("width"), g("height")
        if _is_bg([(x, y), (x + w, y + h)]):
            out.append(_bg_poly())
        else:
            filled(rectpts(x, y, w, h, g("rx")), fill or stroke)
    elif tag == "ellipse":
        cx, cy, rx, ry = g("cx"), g("cy"), g("rx"), g("ry")
        if (raw_fill or "").startswith("url(#floorglow"):
            out.append(poly(ngon(cx, cy, rx, ry, 14), "#ffffff", op=0.05))
        else:
            filled(ngon(cx, cy, rx, ry, 18), fill or stroke)
    elif tag == "circle":
        cx, cy, r = g("cx"), g("cy"), g("r")
        if raw_fill == GRID:                           # already-converted ring hole
            return ""
        if fill is None and stroke:                    # ring -> keep the hole open
            out.append(ring_strip(cx, cy, r + sw / 2, max(0.4, r - sw / 2), stroke, n=32, op=op))
        elif fill or stroke:
            if stroke:
                out.append(circ(cx, cy, r + sw * 0.6, stroke, op=op))
            out.append(circ(cx, cy, r, fill or stroke, op=op))
    elif tag == "line":
        if stroke or fill:
            out.append(bar(g("x1"), g("y1"), g("x2"), g("y2"), max(0.5, sw / 2),
                           stroke or fill, op=op))
    elif tag == "path":
        subs = flatten_path(el.get("d", ""))
        if fill:
            for sub in subs:
                filled(sub, fill)
        elif flame:
            for sub in subs:
                if len(sub) >= 3:
                    out.append(poly(sub, stroke or "#dd5aff", cls="flame", op=op))
        elif stroke:                                    # stroke-only path -> ribbon(s)
            for sub in subs:
                out.append(ribbon(sub, max(0.5, sw / 2), stroke, op=op))
    return "".join(out)

DRAW = {"polygon", "rect", "circle", "ellipse", "line", "path"}
INHERIT = ("fill", "stroke", "stroke-width", "opacity")

def walk(el, inh, acc):
    st = dict(inh)
    for k in INHERIT:
        if el.get(k) is not None:
            st[k] = el.get(k)
    tag = el.tag.split("}")[-1]
    if tag in DRAW:
        acc.append(emit(tag, el, st))
    for ch in el:
        walk(ch, st, acc)

def convert_svg(svg_text):
    m = re.match(r'<svg([^>]*)>([\s\S]*)</svg>', svg_text)
    attrs, inner = m.group(1), m.group(2)
    vb = re.search(r'viewBox="([^"]*)"', attrs)
    global VB
    VB = [float(v) for v in vb.group(1).split()] if vb else [0, 0, 240, 200]
    inner = re.sub(r'<!--[\s\S]*?-->', '', inner)
    texts = re.findall(r'<text[\s\S]*?</text>', inner)
    root = ET.fromstring("<g>" + re.sub(r'\sxmlns="[^"]*"', '', inner) + "</g>")
    acc = []
    walk(root, {}, acc)
    body = "".join(acc)
    # keep <text> annotations verbatim, after the shapes
    return f'<svg{attrs}>{body}{"".join(texts)}</svg>'

# ---------------------------------------------------------------- the six outfits
V_GLASS = "#7dffca"
OUTFITS = {
 # Vherathi - organic, asymmetric, glass-green glow
 7:  dict(helmet="#b7a2c4", suit="#7d6290", boot="#4a3060", sleeve="#6a5080",
          shoulders="#4a3060", shoulders_side="left", sash=V_GLASS, badge=V_GLASS),
 8:  dict(helmet=V_GLASS, suit="#4a3060", boot="#2f1e3c", sleeve="#3f2a54",
          spikes=V_GLASS, spikes_side="uneven", blade=V_GLASS, collar=V_GLASS),
 9:  dict(helmet="#cdd2de", visor=V_GLASS, suit="#4a3060", boot="#2f1e3c",
          sleeve="#3f2a54", harness="#7d6290", harness_side="left", pod="#5a3f72", badge=V_GLASS),
 # Drossholt - bolted, symmetric, rivets, amber
 26: dict(helmet="#c89664", suit="#c89664", boot="#5a4130", sleeve="#a97f52",
          shoulders="#5a4130", chest="#8a6845", rivets="#5a4130",
          backpack="#8a6845", torch="#8a6845", belt="#5a4130"),
 27: dict(cap="#5a4130", suit="#dab488", boot="#5a4130", sleeve="#c89664",
          chest="#8a6845", rivets="#5a4130", belt="#5a4130", pod="#8a6845"),
 28: dict(helmet="#c89664", visor="#2c2622", suit="#a97f52", boot="#5a4130",
          sleeve="#c89664", harness="#5a4130", knee="#8a6845", belt="#5a4130"),
}

def outfit_svg(vb, aria, opts):
    # R&R outfit viewBox is "0 0 160 200"; the SI figure lives in 140x210 -
    # centre it and scale to fit.
    body = "".join(figure_parts(**opts))
    x0, y0, vw, vh = (float(v) for v in vb.split())
    bg = poly([(x0, y0), (x0 + vw, y0), (x0 + vw, y0 + vh), (x0, y0 + vh)], GRID)
    g = f'<g transform="translate({vw/2 - 70*0.92:.1f},{vh - 205*0.92:.1f}) scale(0.92)">{body}</g>'
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{bg}{g}</svg>'

# ---------------------------------------------------------------- rewrite pass
DEFS = ('<svg width="0" height="0" aria-hidden="true" style="position:absolute">'
        '<defs><pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse">'
        '<circle cx="1.5" cy="1.5" r="1" fill="#ffffff" fill-opacity="0.05"/>'
        '</pattern></defs></svg>')

svgs = list(re.finditer(r'<svg[\s\S]*?</svg>', html))
assert len(svgs) == 47, len(svgs)
OUTFIT_IDX = set(OUTFITS)

out, last = [], 0
for i, m in enumerate(svgs):
    out.append(html[last:m.start()])
    block = m.group(0)
    if i == 0:
        new = DEFS
    elif i in OUTFIT_IDX:
        vb = re.search(r'viewBox="([^"]*)"', block).group(1)
        aria = re.search(r'aria-label="([^"]*)"', block)
        new = outfit_svg(vb, aria.group(1) if aria else "", OUTFITS[i])
    else:
        new = convert_svg(block)
    out.append(new)
    last = m.end()
out.append(html[last:])
res = "".join(out)

for bad in ('stroke="', 'stroke-width', '<ellipse', '<line ', '<path ', '<rect ',
            'url(#floorglow)', 'url(#bloom', 'feGaussianBlur'):
    n = res.count(bad)
    # <rect is allowed only inside the (now-removed) defs; assert none survive in specimens
    if bad in ('stroke="', '<ellipse', '<line ', '<path ', 'url(#bloom', 'feGaussianBlur',
               'url(#floorglow)') and n:
        raise SystemExit(f"LEFTOVER {bad!r} x{n}")
SRC.write_text(res, encoding="utf-8")
print("rewrote", SRC, len(res), "bytes;", len(svgs), "svgs")
