"""The shared strokeless drawing kit + the single `Person` figure generator.

`figure_parts()` is the one source for the `Person` silhouette: every culture
atlas (`gen_common.py`, `gen_split.py`, the frontier / culture kits) imports it
and the primitives below, and `build_person_figure.py` / `build_figure_signatures.py`
bake its output into `game/world/person_figure.py` and `figure_signatures.py`.

Strokeless drawing idioms used throughout:
  - outline  : an evenly-offset copy of the shape (offset_poly) drawn behind it,
               constant perpendicular width on every edge.
  - ovals    : many-sided polygons (ngon).
  - lines    : long thin polygons (bar); dashed = a run of short quads
               (dashed_bar); a dotted circle = a ring of dots (dots_ring).
  - ring hole: a torus built from radial quad segments (ring_strip) - nothing
               covers the centre, so the hole is genuinely transparent.

(Was also the "rewrite standard-issue.html in place" pass; that atlas was
superseded by Common Kit + Sol Federation and removed, so only the shared
figure half remains here.)
"""
import math

OUT   = "#141219"
SKIN  = "#e1b491"
SKINF = "#f4d0ab"
SKINL = "#bd8f6a"
EYE   = "#281e1e"
EYEW  = "#f4efe7"     # eye white
BROW  = "#3d2e24"     # eyebrow
SHAD  = "#2a3444"
GRID  = "url(#grid)"

# ---------------------------------------------------------------- primitives
def fmt(pts): return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

# Structured-shape recorder. When _REC is a list, every poly()/circ() also
# appends {"points"|"circle", "color", "group"} to it (raw figure-space
# geometry, not SVG) - used by build_person_figure.py to extract the shared
# Person body into game data. Off (None) during normal atlas generation, so
# the SVG output is unchanged. Colours are mapped to tokens the engine
# resolves per outfit; a hex not in the map passes through as a literal.
_REC = None
_GRP = "body"
_GATE = None
_TOK = {OUT: "outline", SKIN: "skin", SKINF: "skin_hi", SKINL: "skin_lo",
        EYE: "eye", SHAD: "shade"}

def _grp(name):
    global _GRP
    _GRP = name

def _gate(key):
    global _GATE
    _GATE = key

def _rec(kind, geom, color):
    if _REC is not None:
        _REC.append({kind: geom, "color": _TOK.get(color, color),
                     "group": _GRP, "gate": _GATE})

def figure_shapes(**tokens):
    """Run figure_parts with token colours and the recorder on -> the flat,
    ordered shape list (figure-space geometry) for build_person_figure.py."""
    global _REC, _GRP, _GATE
    _REC, _GRP, _GATE = [], "body", None
    figure_parts(**tokens)
    out, _REC = _REC, None
    return out

def poly(pts, fill, cls=None, op=None):
    if _XF:
        pts = _xf_shape(pts)
    if cls != "flame" and not (op is not None and op < 0.2):
        _rec("points", [(round(x, 2), round(y, 2)) for x, y in pts], fill)
    a = f' class="{cls}"' if cls else ""
    o = f' opacity="{op}"' if op is not None else ""
    return f'<polygon{a} points="{fmt(pts)}" fill="{fill}"{o}/>'

def circ(cx, cy, r, fill, op=None):
    if _XF:
        cy = _pw(cy)
    _rec("circle", [round(cx, 2), round(cy, 2), round(r, 2)], fill)
    o = f' opacity="{op}"' if op is not None else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{o}/>'

def ngon(cx, cy, rx, ry, n=16, rot=-math.pi / 2):
    return [(cx + rx * math.cos(rot + 2 * math.pi * i / n),
             cy + ry * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]

def rrect(x, y, w, h, r, seg=3):
    pts = []
    cs = [(x + r,     y + r,     math.pi,       1.5 * math.pi),
          (x + w - r, y + r,    -0.5 * math.pi, 0.0),
          (x + w - r, y + h - r, 0.0,           0.5 * math.pi),
          (x + r,     y + h - r, 0.5 * math.pi, math.pi)]
    for ccx, ccy, a0, a1 in cs:
        for i in range(seg + 1):
            a = a0 + (a1 - a0) * i / seg
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts

def _u(v):
    L = math.hypot(v[0], v[1]) or 1.0
    return (v[0] / L, v[1] / L)

def offset_poly(pts, d, miter_limit=2.0):
    """Outward offset by a constant d on every edge. Corners mitre; a corner
    too sharp to mitre within miter_limit*d bevels (a point per edge) instead,
    so a pointed shape (blade, nozzle, wedge) gets a clean cap, not a spike.
    Direction comes from the signed area, so it's winding-agnostic. Must stay
    in lockstep with game/world/world_object.py:expand_polygon."""
    n = len(pts)
    if n < 3:
        return pts
    area2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
               for i in range(n))
    sgn = 1.0 if area2 > 0 else -1.0

    def norm(p, q):
        ux, uy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(ux, uy)
        return None if L < 1e-9 else (sgn * uy / L, -sgn * ux / L)

    out = []
    for i in range(n):
        a, b, c = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        n1, n2 = norm(a, b), norm(b, c)
        if n1 is None and n2 is None:
            out.append(b); continue
        if n1 is None or n2 is None:
            k = n1 or n2
            out.append((b[0] + k[0] * d, b[1] + k[1] * d)); continue
        mx, my = n1[0] + n2[0], n1[1] + n2[1]
        ml = math.hypot(mx, my)
        cosv = (mx / ml) * n1[0] + (my / ml) * n1[1] if ml > 1e-9 else 0.0
        if cosv < 1.0 / miter_limit:
            out.append((b[0] + n1[0] * d, b[1] + n1[1] * d))
            out.append((b[0] + n2[0] * d, b[1] + n2[1] * d))
        else:
            out.append((b[0] + mx / ml * d / cosv, b[1] + my / ml * d / cosv))
    return out

def opoly(pts, fill, d=1.3, ol=OUT, cls=None):
    return poly(offset_poly(pts, d), ol) + poly(pts, fill, cls=cls)

def ocirc(cx, cy, r, fill, d=1.6, ol=OUT):
    return circ(cx, cy, r + d, ol) + circ(cx, cy, r, fill)

# One uniform outline weight for every structural part of the shared body,
# matching the Grounded study (docs/atlases/grounded-person.html) where the
# head, torso and limbs all carry the same thin edge (there it's a 1.1 stroke
# half-tucked under the fill; here the offset sits fully outside, so a slightly
# smaller number reads the same). Accessory layers keep their own weights.
_FD = 1.0

def ooval(cx, cy, rx, ry, fill, d=_FD, ol=OUT, n=30):
    """An oval as a many-sided polygon with the uniform body outline - the
    Grounded head/face shape (taller than wide), strokeless-safe."""
    return opoly(ngon(cx, cy, rx, ry, n), fill, d=d, ol=ol)

def ring_strip(cx, cy, r_out, r_in, col, n=40, op=None):
    """A torus of n radial quad segments - the centre stays empty."""
    out = []
    for k in range(n):
        a0 = 2 * math.pi * k / n
        a1 = 2 * math.pi * (k + 1) / n
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        out.append(poly([(cx + r_in * c0, cy + r_in * s0),
                         (cx + r_out * c0, cy + r_out * s0),
                         (cx + r_out * c1, cy + r_out * s1),
                         (cx + r_in * c1, cy + r_in * s1)], col, op=op))
    return "".join(out)

def oring(cx, cy, r_out, r_in, col, d=1.4, ol=OUT, n=44):
    return (ring_strip(cx, cy, r_out + d, r_out, ol, n)
            + ring_strip(cx, cy, r_out, r_in, col, n)
            + ring_strip(cx, cy, r_in, max(0.6, r_in - d), ol, n))

def bar(x0, y0, x1, y1, w, fill, op=None):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * w, dx / L * w
    return poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                 (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], fill, op=op)

def dashed_bar(x0, y0, x1, y1, w, col, dash=3.4, gap=2.8):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    out, t = [], 0.0
    while t < L:
        e = min(t + dash, L)
        out.append(bar(x0 + ux * t, y0 + uy * t, x0 + ux * e, y0 + uy * e, w, col))
        t += dash + gap
    return "".join(out)

def dots_ring(cx, cy, r, col, n=26, dot=1.0):
    return "".join(circ(cx + r * math.cos(2 * math.pi * k / n),
                        cy + r * math.sin(2 * math.pi * k / n), dot, col)
                   for k in range(n))

def sq(x, y, sz, fill):
    return poly([(x, y), (x + sz, y), (x + sz, y + sz), (x, y + sz)], fill)

def arcband(x0, x1, ytop, sag, w, fill, samp=12):
    top, bot = [], []
    for i in range(samp + 1):
        t = i / samp
        x = x0 + (x1 - x0) * t
        y = ytop - sag * 4 * t * (1 - t)
        top.append((x, y)); bot.append((x, y + w))
    return poly(top + bot[::-1], fill)

# ---------------------------------------------------------------- the figure
# The shared Person silhouette follows the "Grounded Person" study
# (docs/atlases/grounded-person.html): a ~6.1-head figure with a small head,
# a short neck, a long torso, legs on the true half-body line, and narrow
# rounded shoulders the domed arm top tucks under. That study works in its own
# units (feet at 0, y up, ~5.15 atlas units each); _gx / _gy map them into
# atlas figure-space (centre x = 70, y down). build_person_figure.py imports
# the anchors below so the walk-cycle pivots track any change here.

# ================================================================== Grounded
# The face kit, the hairstyles and the hard hat, ported from the study in
# docs/atlases/grounded-person.html. Everything below works in FACE-RADIUS
# units around the face centre with +y UP (the study's convention); _fp maps a
# list of them into atlas space, where +y is down. Kept as one block so the
# two can be diffed against each other.
#
# The shapes are generated, not typed: a hairstyle is the skull's own profile
# pushed out by a lift, closed by a hairline, and every piece past the fill
# (shade, sheen, the parting, the helmet's brim) is a contour ribbon that runs
# along that same edge and tapers to a point at both ends.
# ---------------------------------------------------------------------------
IRIS  = "#4b3325"     # default iris
GLINT = "#f8f5ef"     # catchlight
SKINS = "#e7c39e"     # the head's far side, one step off SKINF

HEAD_CROWN = 1.21
HEAD_SHAPE = [
    (0.00, 1.21), (0.20, 1.19), (0.40, 1.10), (0.57, 0.95),
    (0.70, 0.74), (0.78, 0.47), (0.81, 0.19), (0.80, 0.02),
    (0.75, -0.26), (0.64, -0.51), (0.49, -0.73), (0.32, -0.90),
    (0.15, -1.00), (0.00, -1.02),
    (-0.15, -1.00), (-0.32, -0.90), (-0.49, -0.73), (-0.64, -0.51),
    (-0.75, -0.26), (-0.80, 0.02), (-0.81, 0.19), (-0.78, 0.47),
    (-0.70, 0.74), (-0.57, 0.95), (-0.40, 1.10), (-0.20, 1.19),
]
# the head's side plane: a leaf, barely there at the crown, widest across the
# far cheek and jaw, gone by the chin. A constant-width strip reads as a
# stripe ruled down the face.
HEAD_SHADE = ([p for p in HEAD_SHAPE if p[0] > 0.001]
              + [(max(0.0, x - (0.03 + 0.19 * math.exp(-((y + 0.20) / 0.62) ** 2))), y)
                 for x, y in reversed([p for p in HEAD_SHAPE if p[0] > 0.001])])

# shallow "D" ear, low on the head (brow to nose base) and barely clear of the
# skull, so it reads as an ear rather than a knob
EAR_D = [(0.70, 0.12), (0.70, -0.34), (0.79, -0.31),
         (0.85, -0.16), (0.85, -0.01), (0.79, 0.10)]

_HEAD_HALF = sorted([p for p in HEAD_SHAPE if p[0] >= 0], key=lambda p: -p[1])


def head_r(deg):
    """The skull profile as a polar function."""
    th = math.radians(deg)
    dx, dy = math.cos(th), math.sin(th)
    for i in range(len(HEAD_SHAPE)):
        a, b = HEAD_SHAPE[i], HEAD_SHAPE[(i + 1) % len(HEAD_SHAPE)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = ex * dy - ey * dx
        if abs(den) < 1e-9:
            continue
        u = (a[1] * dx - a[0] * dy) / den
        if u < 0 or u > 1:
            continue
        t = (a[0] + u * ex) / dx if abs(dx) > abs(dy) else (a[1] + u * ey) / dy
        if t > 0:
            return t
    return 1.0


def head_lower_y(fx):
    """The head's lower silhouette at a given face-x - what the neck's contact
    shadow follows, so it tracks HEAD_SHAPE instead of being typed out."""
    a = abs(fx)
    pts = sorted([p for p in HEAD_SHAPE if p[0] >= 0 and p[1] <= 0.001])
    for i in range(len(pts) - 1):
        if a <= pts[i + 1][0]:
            t = (a - pts[i][0]) / (pts[i + 1][0] - pts[i][0])
            return pts[i][1] + t * (pts[i + 1][1] - pts[i][1])
    return pts[-1][1]


def head_half_at(y):
    """The skull's half-width at a height - what a fall of hair has to hug."""
    if y >= _HEAD_HALF[0][1]:
        return _HEAD_HALF[0][0]
    for i in range(len(_HEAD_HALF) - 1):
        a, b = _HEAD_HALF[i], _HEAD_HALF[i + 1]
        if y >= b[1]:
            return a[0] + (a[1] - y) / (a[1] - b[1]) * (b[0] - a[0])
    return 0.0


def head_band(cx, cy, fr, y0, y1, inset=0.0, n=8):
    """A band across the head whose sides follow the SKULL'S OWN PROFILE, so a
    visor, mask or cap sits on the round of the head instead of cutting across
    it with a straight chord. y0 is the upper atlas y."""
    left, right = [], []
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n
        h = max(0.6, head_half_at((cy - y) / fr) * fr - inset)
        left.append((cx - h, y))
        right.append((cx + h, y))
    return right + left[::-1]


def _fp(pts, cx, cy, fr):
    """Face-radius units (+y up) -> atlas space (+y down)."""
    return [(cx + x * fr, cy - y * fr) for x, y in pts]


def _tone(col, amt):
    c = col.lstrip("#")
    v = [int(c[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(x * amt[0] + amt[1]))) for x in v)


def hair_tone(col, t):
    """Three tones off one hair colour. Scaled rather than offset, so
    near-black hair still separates instead of clamping to the same black."""
    if t == "sheen":
        return _tone(col, (1.16, 26))
    if t == "shade":
        return _tone(col, (0.68, 5))
    return col


# ---------------------------------------------------------------- hairstyles
HAIR_STYLE = {
    "stubble":  dict(crown=0.00, temple=0.00, tempAng=26, peak=0.62, q=2.2, dip=0.05, bay=0, flat=True),
    "buzz":     dict(crown=0.08, temple=0.008, tempAng=25, peak=0.68, q=2.4, dip=0.06, bay=0,
                     wave=dict(n=2.2, a=0.011, p=0.7), burn=0.72),
    "crop":     dict(crown=0.285, temple=0.025, tempAng=22, peak=0.78, q=2.6, dip=0.04, bay=0.02,
                     lean=0.16, wave=dict(n=2.1, a=0.044, p=1.1), burn=1.0,
                     tips=dict(n=5, d=0.13, v=[1, 0.72, 1.15, 0.85, 0.95])),
    "sleek":    dict(crown=0.12, temple=0.015, tempAng=26, peak=0.82, q=2.2, dip=0, bay=0.03,
                     wave=dict(n=1.8, a=0.016, p=2.1), burn=0.85),
    "sidepart": dict(crown=0.305, temple=0.02, tempAng=22, peak=0.80, q=2.6, dip=0, bay=0.02,
                     skew=0.44, part=-0.26, sweep=0.25, jog=0.16, lean=0.14,
                     wave=dict(n=2.2, a=0.034, p=0.4), burn=1.15),
    "receding": dict(crown=0.08, temple=0.005, tempAng=30, peak=0.88, q=3.2, dip=0.14, bay=0.20,
                     wave=dict(n=2.0, a=0.013, p=1.6), burn=0.8, noSheen=True),
    "curls":    dict(crown=0.43, temple=0.05, tempAng=22, tuck=0.20, peak=0.72, q=2.6, dip=0.02, bay=0.02,
                     wave=dict(n=4.5, a=0.070, lobe=True), burn=1.1,
                     tips=dict(n=6, d=0.08, v=[1.2, 0.7, 1.0, 0.8, 1.15, 0.9])),
    "long":     dict(crown=0.285, temple=0.025, tempAng=19, peak=0.78, q=2.6, dip=0.04, bay=0.02,
                     lappet=True, fall=dict(a=56, f=0.30, y=-1.30),
                     wave=dict(n=2.0, a=0.042, p=2.6),
                     tips=dict(n=5, d=0.15, v=[0.9, 1.2, 0.7, 1.1, 0.85])),
}


def _ramp(t):
    return 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)


def hair_lift(st, deg):
    """The lift is what decides whether a style reads as hair or as a helmet.
    A bulge over the crown only makes the skull taller - the outline stays an
    offset copy of the skull, which is what helmet hair is. This is a PLATEAU:
    a smoothstep ramp up over the first `tuck` of the sweep, flat across the
    sides and the crown, and a matching ramp back down into the far sideburn,
    so the mass stands off the head everywhere and only tucks in at the tips.
    The ramp matters as much as the plateau - any power of a sine leaves a
    cusp, which shows up as a spike off each temple."""
    T = st["tempAng"]
    u = (deg - T) / (180 - 2 * T)
    if u <= 0 or u >= 1:
        return st["temple"]
    tuck = st.get("tuck", 0.17)
    w = (_ramp(u / tuck) * _ramp((1 - u) / tuck)
         * (0.76 + 0.24 * math.sin(math.pi * u))
         * (1 + st.get("lean", 0) * (2 * u - 1)))
    l = st["temple"] + (st["crown"] - st["temple"]) * w
    wv = st.get("wave")
    if wv:
        amp = wv["a"] * max(0.0, w) ** 0.45
        if wv.get("lobe"):    # clumps: fuller lobes and tighter valleys
            l += amp * (abs(math.sin(math.pi * wv["n"] * u)) ** 0.55 * 2 - 0.9)
        else:
            l += amp * math.sin(2 * math.pi * wv["n"] * u + wv.get("p", 0))
    return l * (1 - st["skew"] * math.cos(math.radians(deg))) if st.get("skew") else l


def edge_r(st, deg):
    return head_r(deg) + hair_lift(st, deg)


def _polar(deg, r):
    th = math.radians(deg)
    return (r * math.cos(th), r * math.sin(th))


def hair_edge(st, deg):
    return _polar(deg, edge_r(st, deg))


def build_hair_parts(st):
    """A style bakes into a PART LIST - {"p": pts, "t": tone} polygons and
    {"c": (x, y, r), "t": tone} circles - rather than one flat fill."""
    T = st["tempAng"]
    wv = st.get("wave")
    steps = max(64, round(wv["n"] * 22)) if wv else 28
    angs = [T + (180 - 2 * T) * i / steps for i in range(steps + 1)]
    for px, py in HEAD_SHAPE:
        a = math.degrees(math.atan2(py, px))
        if T + 0.5 < a < 180 - T - 0.5:
            angs.append(a)
    angs.sort()
    outer = [hair_edge(st, a) for a in angs]
    xT, yT = outer[0]

    def line(x):
        s = min(1.0, abs(x) / xT)
        y = st["peak"] - (st["peak"] - yT) * s ** st["q"]
        if st.get("bay"):
            y += st["bay"] * (math.sin(math.pi * (s - 0.42) / 0.58) if s > 0.42 else 0)
        if st.get("dip"):
            y -= st["dip"] * max(0.0, 1 - (s / 0.34) ** 2)
        if st.get("sweep"):
            y += st["sweep"] * (x / xT) * (1 - s ** 3)
        return y

    tips = st.get("tips")

    def line_lo(x):
        return line(x) - (tips["d"] * 0.62 if tips else 0)

    def band_depth(deg):
        """How far a ray can travel in from the outer edge before it leaves
        the hair through the hairline. Caps every ribbon's depth, so none of
        them can be deeper than the hair over it."""
        r = edge_r(st, deg)
        th = math.radians(deg)

        def out(t):
            q = r - t
            return q * math.sin(th) < line_lo(q * math.cos(th))
        if not out(r):
            return r
        lo, hi = 0.0, r
        for _ in range(22):
            m = (lo + hi) / 2
            if out(m):
                hi = m
            else:
                lo = m
        return lo

    def crescent(a0, a1, gap, depth, bias=1.0):
        """A ribbon along the outer edge between two angles, swelling in the
        middle and tapering to a point at both ends. No visible end, no
        straight chord across the mass - which is what a shade laid on as a
        flat wedge looks like."""
        N = 48 if wv else 24
        top, bot = [], []
        for i in range(N + 1):
            u = i / N
            a = a0 + (a1 - a0) * u
            e = math.sin(math.pi * u ** bias)
            room = band_depth(a) * 0.78
            g = min(gap, room)
            d = min(depth * e, room - g)
            r = edge_r(st, a)
            top.append(_polar(a, r - g))
            bot.append(_polar(a, r - g - d))
        return top + bot[::-1]

    # the hairline, left temple to right. tips cuts it into locks that
    # STRADDLE the curve - points below it, notches above - so a fringe reads
    # as cut hair instead of a row of bumps sitting on a line.
    N = 2 * tips["n"] if tips else 18
    inner = []
    for i in range(N + 1):
        x = -xT + 2 * xT * i / N
        if st.get("part") is not None and i > 0 and x >= st["part"] > -xT + 2 * xT * (i - 1) / N:
            inner.append((st["part"], line(st["part"])))
            inner.append((st["part"], line(st["part"]) + st["jog"]))
        off = 0.0
        if tips and 0 < i < N:
            v = tips.get("v")
            m = v[(i >> 1) % len(v)] if v else 1
            off = (0.48 if i % 2 else -0.62) * tips["d"] * m
        inner.append((x, line(x) + off))

    front = []
    if not st.get("lappet"):
        front.append({"p": outer + inner, "t": "base"})
    else:
        # long - the fall CASCADES off the top of the head rather than hanging
        # from the temple: its outer edge leaves the crown high up and is the
        # crescent's own radius plus a flare that opens as it comes down, so
        # the hair sweeps from the top of the skull out over the ear and past
        # the jaw in one line. Its inner edge hugs the skull while there is a
        # cheek to hug and then holds a line past the jaw. It hands back to
        # the hairline SHORT of the temple - run the hairline all the way out
        # and the loop doubles back on itself.
        F = st["fall"]
        cut = [p for p in inner if abs(p[0]) < xT * 0.92]
        join = cut[-1]
        crown = [hair_edge(st, a) for a in angs if F["a"] <= a <= 180 - F["a"]]
        outR = []
        for i in range(11):
            a = F["a"] - (F["a"] - 4) * i / 10
            outR.append(_polar(a, edge_r(st, a)
                               + F["f"] * _ramp((F["a"] - a) / (F["a"] - 22))))
        w0 = outR[-1][0]
        outR += [(w0, -0.34), (w0 * 0.97, -0.72), (w0 * 0.86, -1.02), (w0 * 0.64, F["y"])]
        inR = ([(w0 * 0.50, F["y"] + 0.10)]
               + [(max(head_half_at(y) - 0.035, w0 * 0.44), y)
                  for y in (-0.90, -0.62, -0.30, 0.02, 0.24)]
               + [join])
        flip = lambda p: [(-x, y) for x, y in p]
        front.append({"p": outR + inR + cut[::-1] + flip(inR)[::-1]
                           + flip(outR)[::-1] + crown[::-1], "t": "base"})
        nO = len(outR)
        front.append({"p": outR + [(x - (0.045 + 0.21 * _ramp(i / (nO - 1) / 0.45)
                                         * (1 - _ramp((i / (nO - 1) - 0.74) / 0.26))), y)
                                   for i, (x, y) in enumerate(outR)][::-1], "t": "shade"})

    # a wisp of hair in front of the ear. The crescent tapers to a clean point
    # at the temple, which is tidier than any real head.
    if st.get("burn"):
        k = st["burn"]
        bx, w, ln = xT - 0.05 * k, 0.135 * k, 0.54 * k
        top = line(bx) + 0.12
        sb = [(bx + w * 0.55, top), (bx + w * 0.44, top - ln * 0.52),
              (bx - w * 0.02, top - ln), (bx - w * 0.62, top - ln * 0.40),
              (bx - w * 0.58, top)]
        front.append({"p": sb, "t": "shade", "o": False})
        front.append({"p": [(-x, y) for x, y in sb], "t": "base", "o": False})

    if st.get("flat"):
        return {"front": front, "line": line, "xT": xT, "yT": yT}

    front.append({"p": crescent(st["fall"]["a"] if st.get("fall") else T, 104, 0, 0.34, 0.60),
                  "t": "shade"})
    if not st.get("noSheen"):
        front.append({"p": crescent(min(148, 180 - T - 12), 96, 0.035, 0.145, 0.85),
                      "t": "sheen"})
    if st.get("part") is not None:                  # the parting, over the crown
        b = (st["part"], line(st["part"]) + st["jog"] * 0.5)
        t2 = hair_edge(st, 102)
        pl = []
        for s in (-1, 1):
            for i in range(7):
                u = (i if s < 0 else 6 - i) / 6
                w = s * 0.048 * (1 - u) * (0.35 + 0.65 * (1 - u) ** 0.4)
                pl.append((b[0] + (t2[0] - b[0]) * u + w, b[1] + (t2[1] - b[1]) * u))
        front.append({"p": pl, "t": "shade"})
    return {"front": front, "line": line, "xT": xT, "yT": yT}


HAIR_PARTS = {k: build_hair_parts(v)["front"]
              for k, v in HAIR_STYLE.items() if k not in ("sleek",)}
_SLEEK = build_hair_parts(HAIR_STYLE["sleek"])["front"]
HAIR_PARTS["sleek"] = _SLEEK
# the knot for the bun - a ball of hair proud of the slicked crown, its
# outline rippled a touch so it isn't a plain ellipse
_BUN = []
_bcx, _bcy, _brx, _bry, _bN = 0.16, 1.30, 0.38, 0.33, 20


def _bun_at(i, k):
    a = 2 * math.pi * i / _bN
    m = k * (1 + 0.045 * math.sin(3 * a + 0.9))
    return (_bcx + _brx * m * math.cos(a), _bcy + _bry * m * math.sin(a))


_BUN.append({"p": [_bun_at(i, 1) for i in range(_bN)], "t": "base"})
_BUN.append({"p": [_bun_at(i, 1) for i in range(-_bN // 4, _bN // 4 + 1)]
                  + [_bun_at(i, 0.52) for i in range(_bN // 4, -_bN // 4 - 1, -1)], "t": "shade"})
_BUN.append({"c": (_bcx - _brx * 0.34, _bcy + _bry * 0.38, 0.10), "t": "sheen"})
HAIR_PARTS["bun"] = _SLEEK + _BUN
HAIR_PARTS["ponytail"] = list(_SLEEK)


def tail_parts(spine):
    """A tapered rope of hair from a centre line of (x, y, half-width) stops:
    the outline, then a shade strip down whichever side faces away."""
    A, B, M = [], [], []
    for i, (x, y, w) in enumerate(spine):
        q = spine[min(i + 1, len(spine) - 1)]
        o = spine[max(i - 1, 0)]
        dx, dy = q[0] - o[0], q[1] - o[1]
        m = math.hypot(dx, dy) or 1.0
        dx, dy = dx / m, dy / m
        A.append((x - dy * w, y + dx * w))
        B.append((x + dy * w, y - dx * w))
        M.append((x, y))
    far, near = (A, B) if sum(p[0] for p in A) > sum(p[0] for p in B) else (B, A)
    half = [(p[0] * 0.34 + M[i][0] * 0.66, p[1] * 0.34 + M[i][1] * 0.66)
            for i, p in enumerate(far)]
    return [{"p": far + near[::-1], "t": "base"},
            {"p": far + half[::-1], "t": "shade"}]


def hair_back_parts(style, e):
    """Hair that falls behind the back - emitted before the torso so the body
    covers its inner half. e is how far down it reaches."""
    if style == "long":
        # the drape has to be WIDER than the shoulders or the torso swallows
        # it whole, and it is BEHIND the head, so it reads in shadow - at the
        # same tone as the falls in front of it the whole side of the head
        # merges into one flat slab. Its top starts inside the front hair's
        # silhouette, or its corner pokes out over each temple as a horn.
        half = [(0.70, 0.42), (1.06, -0.20), (1.34, e * 0.30), (1.50, e * 0.60),
                (1.42, e * 0.84), (1.04, e * 0.97), (0.50, e * 1.02)]
        lit = [(-x, y) for x, y in half]
        return [{"p": lit + [(0, e * 1.04)] + half[::-1] + [(0.45, 0.30), (-0.45, 0.30)],
                 "t": "shade"},
                {"p": lit + [(-0.50, e * 0.94), (-0.96, e * 0.86), (-1.28, e * 0.58),
                             (-1.14, e * 0.28), (-0.90, -0.20), (-0.60, 0.42)], "t": "base"}]
    if style == "ponytail":
        return tail_parts([(0.30, 0.86, 0.30), (0.66, 0.76, 0.34), (0.92, 0.46, 0.36),
                           (1.02, 0.05, 0.34), (1.02, e * 0.34, 0.30), (0.94, e * 0.66, 0.25),
                           (0.82, e * 0.88, 0.17), (0.74, e, 0.06)])
    return []


# ------------------------------------------------------------- the hard hat
# A helmet is a hairstyle in everything but name, so it goes through the same
# generator and comes back with the same shade ribbon and sheen in its own
# colour. The layering is what matters: the old dome was a plain oval drawn
# BEHIND the head, so it could only be a halo round the face; this shell draws
# OVER the finished full-size head. A helmet covers a head, it doesn't replace
# one. The shell is shallow and stops high on the forehead, and the brim below
# it is wider, nearly flat underneath, and in the SHADE tone - in the base
# tone it merges into the shell and the whole thing reads as a turban.
HELMET_STYLE = dict(crown=0.22, temple=0.085, tempAng=8, peak=0.74,
                    q=3.0, dip=0, bay=0, tuck=0.14)
_HELM = build_hair_parts(HELMET_STYLE)


def _helmet_extra():
    """The shell, the brim and the rib. No chin strap: the shell is often
    hidden under an outfit's own headgear, and then the strap is all that
    shows - a stray coloured line down the side of the jaw."""
    line, xT = _HELM["line"], _HELM["xT"]
    N, W, flat = 20, 0.985, line(0) - 0.185
    top, bot = [], []
    for i in range(N + 1):
        t = -1 + 2 * i / N
        x = W * t
        y0 = line(max(-xT, min(xT, x)))
        top.append((x, y0 + 0.04))
        bot.append((x, min(y0 - 0.075, flat + 0.05 * t * t)))
    rib = [(-0.085, 0.78), (0.025, 0.78), (0.015, 1.40), (-0.075, 1.40)]
    return [{"p": rib, "t": "shade"},
            {"p": top + bot[::-1], "t": "shade", "o": True}]


# the lamp is a miner's fitting - opt in with lamp=True, or a flight helmet
# ends up wearing a headtorch
LAMP_PIECES = [{"c": (-0.03, 1.06, 0.175), "t": "shade"},
               {"c": (-0.03, 1.06, 0.107), "f": "#f7f0d6"},
               {"c": (-0.065, 1.088, 0.040), "f": "#ffffff"}]


_HX = _helmet_extra()
HELMET_LIST = _HELM["front"] + _HX               # shell, rib, brim
HELMET_LAMP_LIST = HELMET_LIST + LAMP_PIECES
HAT_LIST = list(HELMET_LIST)


def emit_hair(pieces, col, cx, cy, fr):
    """Walk a baked part list into atlas polygons/circles. Pieces on the
    SILHOUETTE take the body's uniform outline; shade, sheen and the small
    details are internal, so they don't."""
    out = []
    for pc in pieces:
        fill = pc.get("f") or hair_tone(col, pc.get("t", "base"))
        edge = pc.get("o", pc.get("t") == "base") and not pc.get("f")
        if "c" in pc:
            x, y, r = pc["c"]
            out.append((ocirc if edge else circ)(cx + x * fr, cy - y * fr, r * fr, fill)
                       if edge else circ(cx + x * fr, cy - y * fr, r * fr, fill))
        else:
            pts = _fp(pc["p"], cx, cy, fr)
            out.append(opoly(pts, fill, d=_FD) if edge else poly(pts, fill))
    return out


# ---------------------------------------------------------------- the face
_EYE_CY, _EYE_EX, _EYE_RX, _EYE_RY, _EYE_TILT = 0.05, 0.375, 0.185, 0.118, 6
_BROW_CY = 0.29


def _almond(rx, ry):
    """The eye opening: a full, rounded upper lid over a shallower lower one -
    an almond, not a wide oval."""
    p, N = [], 9
    for i in range(N + 1):
        t = i / N
        p.append((-rx + 2 * rx * t, ry * math.sin(math.pi * t) ** 0.78))
    for i in range(N, -1, -1):
        t = i / N
        p.append((-rx + 2 * rx * t, -0.78 * ry * math.sin(math.pi * t) ** 1.2))
    return p


_EYE_ALMOND = _almond(_EYE_RX, _EYE_RY)
# the lash line rides the upper lid, and doubles as the crop that takes the
# top off the iris - which is what makes the eye read lidded, not staring
_EYE_LASH = _EYE_ALMOND[:10] + [(x, y + 0.052 * math.sin(math.pi * i / 9) ** 0.5)
                                for i, (x, y) in reversed(list(enumerate(_EYE_ALMOND[:10])))]


def _rot(pts, deg):
    a = math.radians(deg)
    cs, sn = math.cos(a), math.sin(a)
    return [(x * cs - y * sn, x * sn + y * cs) for x, y in pts]


def lip_tone(skin):
    c = skin.lstrip("#")
    v = [int(c[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % (min(255, round(v[0] * 0.84 + 34)),
                              round(v[1] * 0.72 + 23), round(v[2] * 0.72 + 22))


def face_kit(cx, cy, fr, skin=SKINF, brow=BROW, iris=IRIS):
    """Nose and mouth, then the eyes over them, then the brows. Everything is
    a polygon or a circle, so the strokeless / no-<ellipse> rule holds."""
    P = []
    lo = _tone(skin, (1.0, -13))      # nose bridge
    tip = _tone(skin, (1.0, -34))     # nose tip
    P.append(poly(_fp([(-0.030, 0.155), (0.030, 0.155), (0.052, -0.150),
                       (0.070, -0.215), (-0.070, -0.215), (-0.052, -0.150)], cx, cy, fr), lo))
    P.append(poly(ngon(cx, cy + 0.238 * fr, 0.082 * fr, 0.050 * fr, 12), tip))

    lip = lip_tone(skin)
    upper, lower, seam_c = _tone(lip, (1.0, -22)), _tone(lip, (1.0, 12)), _tone(lip, (1.0, -52))
    hw, y0, N = 0.150, -0.55, 8
    seam, top, bot = [], [], []
    for i in range(N + 1):
        t = i / N
        x = -hw + 2 * hw * t
        w = math.sin(math.pi * t)
        sy = y0 + 0.018 - 0.030 * w
        top.append((x, sy + 0.048 * w ** 0.8 - 0.016 * math.exp(-(x / 0.045) ** 2)))
        seam.append((x, sy))
        bot.append((x, sy - 0.040 - 0.046 * w ** 0.9))
    P.append(poly(_fp(top + seam[::-1], cx, cy, fr), upper))
    P.append(poly(_fp(seam + bot[::-1], cx, cy, fr), lower))
    P.append(poly(_fp(seam + [(x, y - 0.014) for x, y in seam[::-1]], cx, cy, fr), seam_c))

    for sgn in (-1, 1):
        ox, oy = sgn * _EYE_EX, _EYE_CY
        at = lambda pts: [(ox + x, oy + y) for x, y in _rot(pts, -sgn * _EYE_TILT)]
        ix, iy = ox + sgn * 0.012, oy + 0.022
        P.append(poly(_fp(at(_EYE_ALMOND), cx, cy, fr), EYEW))
        P.append(circ(cx + ix * fr, cy - iy * fr, 0.112 * fr, iris))
        P.append(circ(cx + ix * fr, cy - iy * fr, 0.052 * fr, EYE))
        P.append(circ(cx + (ix - 0.040) * fr, cy - (iy + 0.058) * fr, 0.027 * fr, GLINT))
        P.append(poly(_fp(at(_EYE_LASH), cx, cy, fr), EYE))

    for sgn in (-1, 1):                # a fine tapered brow, thickest inboard
        x0, hw2, arch, N2 = sgn * _EYE_EX, 0.185, 0.048, 7
        lo_e, hi_e = [], []
        for i in range(N2 + 1):
            t = i / N2
            px = x0 + sgn * (2 * hw2 * t - hw2)
            lift = arch * math.sin(math.pi * t ** 1.25)
            th = 0.058 * (1 - 0.75 * t ** 1.6) * (0.45 + 0.55 * math.sin(math.pi * t ** 0.5))
            lo_e.append((px, _BROW_CY + lift))
            hi_e.append((px, _BROW_CY + lift + th))
        P.append(poly(_fp(lo_e + hi_e[::-1], cx, cy, fr), brow))
    return P


_G_SCALE = 5.15                       # atlas units per Grounded study unit
_G_GROUND = 202.2                     # atlas-y of the sole (study u = 0)


def _gx(dx):
    return 70.0 + _G_SCALE * dx


def _gy(u):
    return _G_GROUND - _G_SCALE * u


# The body, straight off the study's GROUNDED table. The study ships a
# masc/femme pair; the atlas draws one shared body, so this is the neutral
# base both builds are cut from.
_GT = [(0.95, 28.9), (1.66, 28.66), (2.38, 28.20), (3.00, 27.70), (3.50, 27.20),
       (3.78, 26.50), (3.70, 25.44), (3.43, 24.26), (2.95, 23.00), (2.44, 21.86),
       (2.68, 20.70), (3.18, 19.16), (3.48, 17.7), (3.5, 16.6)]
_HIP_U, _ANKLE_U, _HIP_HALF, _ANKLE_W = 16.6, 1.2, 3.4, 0.95
_LEG_MIDS = [(1.38, 12.6), (1.05, 8.2), (1.16, 5.4)]   # thigh, knee, calf
_A_SY, _A_WY, _A_TOP, _A_BOT, _A_HALF, _A_HAND = 26.5, 14.3, 1.40, 0.94, 3.02, 0.60
_NECK_HALF, _NECK_Y0 = 0.96, 28.0
_HEAD_U, _HEAD_R_U = 32.4, 2.60
_WAIST_U, _WAIST_HALF_U = 21.86, 2.44           # the narrowest point of the torso

FIG_HIP_Y = round(_gy(_HIP_U))       # 117 - where the legs join the torso
FIG_FOOT_Y = round(_gy(_ANKLE_U))    # 196 - ankle line; boots sit on the ground
FIG_KNEE_Y = round(_gy(_LEG_MIDS[1][1]))        # 160
FIG_WAIST_Y = round(_gy(_WAIST_U))              # 90
FIG_COLLAR_Y = round(_gy(_GT[0][1]))            # 53 - the trapezius yoke tip
FIG_HEAD_CY = round(_gy(_HEAD_U), 1)            # 35.3
FIG_HEAD_R = round(_G_SCALE * _HEAD_R_U, 2)     # 13.39


def torso_half_at(u):
    """The torso's half-width (study units) at a study height - what a chest
    plate, a band or a collar has to follow to sit ON the body."""
    pts = sorted(_GT, key=lambda p: -p[1])
    if u >= pts[0][1]:
        return pts[0][0]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if u >= b[1]:
            return a[0] + (a[1] - u) / (a[1] - b[1]) * (b[0] - a[0])
    return pts[-1][0]


def torso_band(u0, u1, inset=0.0, n=6):
    """A panel down the front of the torso, its sides tracking the body."""
    left, right = [], []
    for i in range(n + 1):
        u = u0 + (u1 - u0) * i / n
        h = max(0.4, torso_half_at(u) - inset)
        left.append((_gx(-h), _gy(u)))
        right.append((_gx(h), _gy(u)))
    return right + left[::-1]


def arm_top(s):
    """Atlas centre of the domed top of arm s, after the resting splay - where
    a shoulder pad actually sits."""
    return _arm_rot(s, _gx(s * _A_HALF), _gy(_A_SY + _A_TOP * 0.24), new=True)


def hand_shape(s, grow=0.0):
    """The mitt at the end of arm s, in atlas coordinates after the splay, so
    a glove can be drawn ON the hand rather than as a circle near it."""
    wx, wy, r = s * (_A_HALF - 0.55), _A_WY, _A_HAND + grow
    pts = [(wx - r * 0.88, wy + r * 0.12), (wx - r * 0.96, wy - r * 0.55),
           (wx - r * 0.72, wy - r * 1.34), (wx - r * 0.12, wy - r * 1.72),
           (wx + r * 0.56, wy - r * 1.48), (wx + r * 0.94, wy - r * 0.78),
           (wx + r * 0.92, wy + r * 0.12)]
    return [_arm_rot(s, _gx(x), _gy(y), new=True) for x, y in pts]


def head_band_fig(y0, y1, inset=0.0, n=8):
    """head_band on the figure's own head, in atlas coordinates - and
    inverse-mapped under fig_remap, so a signature layer authored in the old
    space can still put a mask or a cap on the round of the skull."""
    pts = head_band(70.0, FIG_HEAD_CY, FIG_HEAD_R, y0, y1, inset, n)
    return [(x, _pw(y, inv=True)) for x, y in pts] if _XF else pts


def head_dome(out=2.0, y_bot=None, n=16, wide=1.0):
    """A dome following the skull outward by `out` - a hood or a soft cap that
    sits ON the head and its hair instead of tenting over it in a trapezoid.
    `wide` stretches it sideways only, so a hood can clear a head of long hair
    without growing into a stovepipe."""
    cx, cy, fr = 70.0, FIG_HEAD_CY, FIG_HEAD_R
    top = []
    for i in range(n + 1):
        a = 6 + (180 - 12) * i / n
        r = head_r(a) * fr + out
        th = math.radians(a)
        top.append((cx + r * math.cos(th) * wide, cy - r * math.sin(th)))
    if y_bot is None:
        y_bot = cy + fr * 0.35
    pts = [(top[0][0], y_bot)] + top + [(top[-1][0], y_bot)]
    return [(x, _pw(y, inv=True)) for x, y in pts] if _XF else pts


def _cap_shade(pts, cx, frac=0.42):
    """The far half of a rounded cap, pulled in toward its centre - the same
    one-direction shade the body carries, for a pad or a plate."""
    far = [p for p in pts if p[0] >= cx]
    mid = [(cx + (x - cx) * frac, y) for x, y in far]
    return far + mid[::-1]


# old anchor line -> new one. Monotonic, so the map inverts cleanly.
_XF_KNOTS = [(31.6, round(_gy(_HEAD_U + _HEAD_R_U * 1.21), 1)),   # crown
             (45.6, round(_gy(_HEAD_U), 1)),                      # head centre
             (59.6, round(_gy(_HEAD_U - _HEAD_R_U * 1.02), 1)),   # chin
             (65.7, float(round(_gy(_GT[0][1])))),                # collar / yoke
             (68.8, float(round(_gy(26.5)))),                     # shoulder cap
             (103.3, float(round(_gy(_WAIST_U)))),                # waist
             (138.9, float(round(_gy(_HIP_U)))),                  # hip
             (158.0, float(round(_gy(_LEG_MIDS[1][1])))),         # knee
             (194.0, float(round(_gy(_ANKLE_U)))),                # ankle
             (202.2, 202.2)]                                      # ground


def _shade(col, amt=-24):
    """The one-direction shade every part carries down its screen-right side."""
    c = col.lstrip("#")
    if len(c) != 6:
        return col
    v = [int(c[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(max(0, min(255, x + amt)) for x in v)


def _mid(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)

# Resting arm splay: each arm hangs a small angle out from the body about the
# shoulder joint, so the default pose reads relaxed and slightly open (and, in
# the side-on in-game render, one arm slightly ahead of the other). Baked into
# the figure geometry here so the atlases and the game agree. _arm_rot maps a
# point on the notional straight-down arm to its splayed position; the
# *_outfits.py signature files import it to re-anchor arm-mounted detail.
ARM_REST_DEG = 7
_ARM_PIVOT = (_A_HALF, _A_SY)        # shoulder joint, study coords (|x|, y)


# ------------------------------------------------------- the signature remap
# The *_outfits.py signature files are authored against the PREVIOUS figure
# (chest y72-106, waist y103, hip y139, knee ~y158, hands (57/83, 133), bare
# head (70, 46) r14). The body below is the Grounded study's, which moves every
# one of those lines - the torso is shorter and higher, the legs much longer.
# Rather than re-typing several hundred coordinates across four signature
# files, they are drawn through this adapter: a piecewise-linear map from the
# old anchor lines onto the new ones.
#
# It maps SHAPES, not points: each poly()/circ() is translated by the map's
# offset at its own centre and scaled about that centre by the map's average
# slope over its span, clamped. Mapping points directly would stretch a knee
# pad to two and a half times its height, because the thigh really did get
# that much longer; this keeps a piece of kit its own size and puts it where
# it belongs. x is untouched - the new torso and stance are the same width.
#
# figure_parts draws in the NEW space and must stay outside the adapter; wrap
# only the call that builds an outfit's signature SVG.
_XF = False   # _XF_KNOTS is the table above


def _pw(v, inv=False):
    ks = [(b, a) for a, b in _XF_KNOTS] if inv else _XF_KNOTS
    lo, hi = ks[0], ks[1]
    if v >= ks[-1][0]:
        lo, hi = ks[-2], ks[-1]
    elif v > ks[0][0]:
        for i in range(len(ks) - 1):
            if v <= ks[i + 1][0]:
                lo, hi = ks[i], ks[i + 1]
                break
    return lo[1] + (v - lo[0]) * (hi[1] - lo[1]) / (hi[0] - lo[0])


def _xf_shape(pts):
    ys = [p[1] for p in pts]
    y0, y1 = min(ys), max(ys)
    c = (y0 + y1) / 2.0
    k = 1.0 if y1 - y0 < 1e-6 else max(0.85, min(1.45, (_pw(y1) - _pw(y0)) / (y1 - y0)))
    nc = _pw(c)
    return [(x, nc + (y - c) * k) for x, y in pts]


def _xon():
    global _XF
    _XF = True


def _xoff():
    global _XF
    _XF = False


class fig_remap:
    """Draw a layer authored in the old figure space."""
    def __enter__(self):
        _xon()
        return self

    def __exit__(self, *a):
        _xoff()
        return False


def _arm_rot(s, ax, ay, new=False):
    """Atlas point on the straight arm -> atlas point after the resting splay.
    s = -1 for the left arm, +1 for the right; both rotate outward.

    Under the remap the input is a point on the OLD arm, so it is first
    stretched onto the new arm's shoulder-to-wrist span, splayed by the new
    rest angle, and then run back through the map's inverse - because the
    shape it belongs to is about to be mapped forward again. Pass new=True for
    a point already in the new body's coordinates (it still comes back
    inverse-mapped, so it can be handed to a remapped signature layer)."""
    old = _XF and not new
    if old:
        u = (_G_GROUND - ay) / _G_SCALE
        u = _A_SY + (u - 25.9) * (_A_SY - _A_WY) / (25.9 - 12.7)
        ay = _gy(u)
    ux, uy = (ax - 70.0) / _G_SCALE, (_G_GROUND - ay) / _G_SCALE
    px, py = s * _ARM_PIVOT[0], _ARM_PIVOT[1]
    ang = math.radians(s * ARM_REST_DEG)
    ca, sa = math.cos(ang), math.sin(ang)
    dx, dy = ux - px, uy - py
    nx, ny = _gx(px + dx * ca - dy * sa), _gy(py + dx * sa + dy * ca)
    return (nx, _pw(ny, inv=True)) if _XF else (nx, ny)


def figure_parts(*, suit, boot, leg=None, sleeve=None, helmet=None, helmet_r=18,
                 hat=None, cap=None, no_helmet=False, legged=True, arms=True, coat=False,
                 torso_long=False, backpack=None, spikes=None, spikes_side="both",
                 antenna=None, collar=None, shoulders=None, shoulders_side="both",
                 chest=None, rivets=None, band=None, sash=None, badge=None,
                 badge_cross=False, belt=None, buckle=None, visor=None, harness=None,
                 harness_side="both", pod=None, blade=None, knee=None, torch=None,
                 hipline=False, helmet_ring=False, accent_dot=False,
                 accent="#8fb9c8", eyes=True, lamp=False,
                 hair=None, hair_col="#33241b", eye_col=IRIS, brow_col=None):
    leg = leg or boot
    sleeve = sleeve or suit
    P = []
    long_torso = torso_long or coat
    hip_y = 147 if long_torso else 139     # old-space: mapped with the rest
    # A cinched waist about halfway up the standing figure, well above the hip
    # line. Every belt, sash end and hip pouch anchors here (waist_y), not at
    # the hip; the torso pinches in at the waist and flares back out below.
    waist_y = 103                            # old-space; the map lands it on
    waist_hw = 13                            # the new torso's narrowest point
    belt_y = waist_y - 4
    foot_y = 194 if legged else 168          # old-space, like the rest

    # The figure reads side-on: the LEFT arm + LEFT leg are the FAR limbs, drawn
    # behind the torso; the RIGHT arm + leg are the NEAR limbs, drawn over it.
    # So one arm and one leg of each pair sits in front, the other behind (the
    # grounded-person study's layering). person.py picks the same split by
    # animation group and mirrors on facing.
    # ---- study geometry, in study units; _gp maps a list into atlas space ----
    def _gp(pts):
        return [(_gx(x), _gy(y)) for x, y in pts]

    def _arm_u(s):
        """arm poly in study units: 0-1 top-left, 2 apex, 3-4 top-right,
        5 wrist-right, 6 wrist-left. A domed top rounds into the shoulder."""
        sx, sy = s * _A_HALF, _A_SY
        wx, wy = s * (_A_HALF - 0.55), _A_WY
        tt, tb = _A_TOP * 0.5, _A_BOT * 0.5
        return [(sx - tt, sy), (sx - tt * 0.6, sy + tt * 0.62), (sx, sy + tt * 0.82),
                (sx + tt * 0.6, sy + tt * 0.62), (sx + tt, sy), (wx + tb, wy), (wx - tb, wy)]

    def _hand_u(s):
        """a tapered mitt hung off the wrist in the arm's own space, so it
        rides the splay like the rest of the limb - not a ball at the joint"""
        a = _arm_u(s)
        x, y, r = a[5][0] - _A_BOT * 0.5, a[5][1], _A_HAND
        return [(x - r * 0.88, y + r * 0.12), (x - r * 0.96, y - r * 0.55),
                (x - r * 0.72, y - r * 1.34), (x - r * 0.12, y - r * 1.72),
                (x + r * 0.56, y - r * 1.48), (x + r * 0.94, y - r * 0.78),
                (x + r * 0.92, y + r * 0.12)]

    def _leg_u(s):
        """thigh, knee and calf stops, so the leg carries a line instead of
        tapering straight from hip to ankle"""
        cx = s * _HIP_HALF * 0.5
        pts = [(s * _HIP_HALF, _HIP_U)]
        pts += [(cx + s * w, y) for w, y in _LEG_MIDS]
        pts.append((cx + s * _ANKLE_W, _ANKLE_U))
        pts.append((cx - s * _ANKLE_W, _ANKLE_U))
        pts += [(cx - s * w, y) for w, y in reversed(_LEG_MIDS)]
        pts.append((s * 0.15, _HIP_U))
        return pts

    def _leg_shade_u(s):
        p = _leg_u(s)
        n = (len(p) - 2) // 2
        outer, inner = p[:n + 1], p[n + 1:][::-1]
        edge = outer if s > 0 else inner
        return edge + [_mid(o, inner[i]) for i, o in enumerate(outer)][::-1]

    def _boot_u(s):
        """a foot: a low toe box pointing the way the figure faces, over a
        compact heel"""
        cx, w, a = s * _HIP_HALF * 0.5, _ANKLE_W, _ANKLE_U
        return [(cx + w * 0.86, a * 1.22), (cx - w * 0.44, a * 1.18),
                (cx - w * 0.92, a * 0.68), (cx - w * 1.58, a * 0.44),
                (cx - w * 2.08, a * 0.17), (cx - w * 2.08, 0), (cx + w * 1.10, 0),
                (cx + w * 1.34, a * 0.40), (cx + w * 1.00, a * 0.96)]

    def _knee(s):
        cx = s * _HIP_HALF * 0.5
        return _gp([(cx - s * 1.15, 9.3), (cx + s * 1.15, 9.3),
                    (cx + s * 1.05, 7.1), (cx - s * 1.05, 7.1)])

    def _emit_arm(s):
        _grp("arm_l" if s < 0 else "arm_r")
        a = _arm_u(s)
        P.append(opoly([_arm_rot(s, *_gp([p])[0]) for p in a], sleeve, d=_FD))
        P.append(poly([_arm_rot(s, *_gp([p])[0])
                       for p in [a[2], a[3], a[4], a[5], _mid(a[5], a[6])]], _shade(sleeve)))
        _grp("hand_l" if s < 0 else "hand_r")
        P.append(opoly([_arm_rot(s, *_gp([p])[0]) for p in _hand_u(s)], SKINF, d=_FD))

    def _emit_leg(s):
        _grp("boot_l" if s < 0 else "boot_r")
        P.append(opoly(_gp(_boot_u(s)), boot, d=_FD))
        _grp("leg_l" if s < 0 else "leg_r")
        P.append(opoly(_gp(_leg_u(s)), leg, d=_FD))
        P.append(poly(_gp(_leg_shade_u(s)), _shade(leg)))
        if knee:
            P.append(opoly(_knee(s), knee, d=_FD))

    _grp("body"); _gate(None)

    P.append(poly(ngon(70, (foot_y + 8) if legged else 172, 30, 7, 14), "#ffffff", op=0.05))

    # back pieces
    # These are authored against the real body, not the old figure, so they
    # sit outside the remap - see the note above fig_remap.
    if backpack:
        _grp("body"); _gate("backpack_color")
        P.append(opoly(rrect(51, 52, 38, 63, 6), backpack, d=1.3))
    if spikes:            # rooted at the shoulder; the pads then cover the root
        _grp("body"); _gate("spike_color")
        _sl = [(_gx(-3.55), _gy(25.4)), (_gx(-2.35), _gy(26.4)), (_gx(-4.6), _gy(30.6))]
        _sr = [(x + 2 * (70 - x), y) for x, y in _sl]
        if spikes_side in ("both", "left"):
            P.append(opoly(_sl, spikes, d=1.1))
        if spikes_side in ("both", "right"):
            P.append(opoly(_sr, spikes, d=1.1))
        if spikes_side == "uneven":              # Vherathi asymmetry
            P.append(opoly([(_gx(-3.5), _gy(25.4)), (_gx(-2.3), _gy(26.5)),
                            (_gx(-4.9), _gy(31.6))], spikes, d=1.1))
            P.append(opoly(_sr, spikes, d=1.1))
    if antenna:           # short, and rooted on the shell rather than the air
        _grp("body"); _gate("antenna_color")
        _ax, _ay = 70 + FIG_HEAD_R * 0.60, FIG_HEAD_CY - FIG_HEAD_R * 1.16
        P.append(bar(_ax, _ay, _ax + 3.0, _ay - 8.5, 1.1, antenna))
        P.append(ocirc(_ax + 3.0, _ay - 8.5, 1.5, antenna, d=1.0))
    _gate(None)
    if blade:                                    # grown guard-blade down one arm
        P.append(opoly([(46, 60), (51, 60), (52, 122), (48, 142), (44, 133)], blade, d=_FD))

    # hair that falls behind the back, before the body so the torso and
    # shoulders cover its inner half
    _grp("body")
    if hair and not (helmet or hat or cap):
        _gate("hair_color")
        for part in hair_back_parts(hair, -3.60 if hair == "long" else -2.90):
            P.append(poly(_fp(part["p"], 70.0, FIG_HEAD_CY, FIG_HEAD_R),
                          hair_tone(hair_col, part["t"])))
        _gate(None)

    _xoff()
    # ---- far arm + far leg (behind the torso) ----
    _grp("body"); _gate(None)
    if arms:
        _emit_arm(-1)
    if legged:
        _emit_leg(-1)
        if long_torso:
            _emit_leg(1)          # a coat covers both legs

    # torso - one smooth hourglass from the hip, through the cinched waist, up
    # to a narrow rounded shoulder (no armpit notch). _gt is the Grounded study
    # torso (left-silhouette half-widths, neck line down to hip); mirrored for
    # the right, so the curve is symmetric by construction.
    _grp("body"); _gate(None)
    _gt = list(_GT)
    if long_torso:
        _gt = _gt[:-1] + [(3.7, 10.6)]   # a coat hem, ~40% down the long leg
    torso = ([(_gx(-h), _gy(y)) for h, y in _gt]
             + [(_gx(h), _gy(y)) for h, y in reversed(_gt)])
    P.append(opoly(torso, suit, d=_FD))
    # a strip whose inner and outer edges both parallel the body's side curve,
    # so the shade sits off to one side instead of filling half the torso
    P.append(poly([(_gx(h), _gy(y)) for h, y in _gt]
                  + [(_gx(max(0.3, h - 1.35)), _gy(y)) for h, y in reversed(_gt)],
                  _shade(suit)))

    # a slimmer neck, long enough to actually show above the collar - the old
    # column put the chin on the collarbone
    P.append(opoly([(_gx(-_NECK_HALF), _gy(_NECK_Y0)),
                    (_gx(-_NECK_HALF), _gy(_HEAD_U - _HEAD_R_U * 0.7)),
                    (_gx(_NECK_HALF), _gy(_HEAD_U - _HEAD_R_U * 0.7)),
                    (_gx(_NECK_HALF), _gy(_NECK_Y0))], SKINF, d=_FD))
    # the contact shadow the jaw casts on it: a band whose lower edge
    # parallels the chin, deepest toward the facing side
    _ns, _nb = [], []
    for _i in range(7):
        _x = -_NECK_HALF + 2 * _NECK_HALF * _i / 6
        _c = _HEAD_U + head_lower_y(_x / _HEAD_R_U) * _HEAD_R_U + 0.06
        _ns.append((_gx(_x), _gy(_c)))
        _nb.append((_gx(_x), _gy(_c - 0.62)))
    P.append(poly(_ns + _nb[::-1], _shade(SKINF)))

    # hip kit - a pouch or a stowed cutting torch on the right hip, hung from
    # the waist. Drawn before the near arm so the arm hangs over it.
    _xon()
    _grp("body")
    if pod:
        P.append(opoly([(82, waist_y - 6), (88, waist_y - 6), (87, waist_y), (83, waist_y)], pod))  # hanger strap
        P.append(opoly(rrect(80, waist_y - 2, 12, 16, 2), pod, d=1.0))
        P.append(bar(82, waist_y + 4, 90, waist_y + 4, 0.8, "#2a2a30"))                             # flap seam
    if torch:                                     # a stowed cutter - canister + nozzle, not lit
        P.append(opoly(rrect(81, waist_y - 1, 9, 15, 1), torch, d=1.0))
        P.append(poly([(85, waist_y - 1), (90, waist_y - 7), (93, waist_y - 4),
                       (88, waist_y + 1)], "#5a5560"))          # nozzle head
        P.append(circ(92, waist_y - 5, 1.2, "#8a8590"))         # tip

    _grp("body")
    if hipline:
        P.append(dashed_bar(70 - waist_hw - 2, waist_y, 70 + waist_hw + 2, waist_y, 1.1, accent))
    _xoff()
    if band:                                      # chest band, above the belt
        P.append(opoly(torso_band(24.2, 22.2, 0.18), band, d=1.0))
    _xon()

    # helmet / hat / cap. The shell is drawn AFTER the face, further down -
    # a helmet covers a head, it doesn't replace one - so only the flat cap is
    # still emitted here, over the crown.
    _grp("body")
    _xoff()
    if cap:                                       # flat brimmed cap over the head
        P.append(opoly([(56.5, 28.5), (83.5, 28.5), (80.5, 22.5), (74, 18.2),
                        (66, 18.2), (59.5, 22.5)], cap, d=1.2))

    # front torso pieces: chest plate -> sash (over it) -> collar (over sash) -> belt
    if chest:
        _gate("chest_plate_color")
        _cp = torso_band(25.2, 20.4, 0.42)
        P.append(opoly(_cp, chest, d=1.2))
        P.append(poly(_cap_shade(_cp, 70, 0.52), _shade(chest, -22)))
        if rivets:
            for rx in (63.5, 76.5):
                for ry in (_gy(24.4), _gy(21.4)):
                    P.append(circ(rx, ry, 1.4, rivets))
        _gate(None)
    if sash:      # a baldric of even width: up OVER the top of the left
                  # shoulder, down across the chest, and then round the waist
                  # on the right, so both ends read as going somewhere
        _gate("sash_color")
        _sh = arm_top(-1)
        def _ribbon(p0, p1, w):
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            m = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / m * w / 2, dx / m * w / 2
            return [(p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny),
                    (p1[0] - nx, p1[1] - ny), (p0[0] - nx, p0[1] - ny)]
        _sb = (_sh[0] - 1.0, _sh[1] - 4.2)                # clear over the pad
        P.append(opoly(_ribbon(_sb, (_gx(1.7), _gy(22.4)), 4.6), sash, d=1.1))
        P.append(opoly(_ribbon((_gx(1.2), _gy(23.0)), (_gx(2.9), _gy(21.1)), 4.6),
                       sash, d=1.1))
        P.append(opoly(_ribbon((_gx(-0.2), _gy(21.2)), (_gx(3.0), _gy(21.2)), 4.2),
                       sash, d=1.1))                       # round the waist
        _gate(None)
    if collar:
        _gate("collar_color")
        _co = [(60.5, 51.8), (79.5, 51.8), (78.0, 63.5), (62.0, 63.5)]
        P.append(opoly(_co, collar, d=1.1))
        P.append(poly(_cap_shade(_co, 70, 0.46), _shade(collar, -20)))
        _gate(None)
    if belt:            # hugging the waist, over the top of the hip kit's strap
        _gate("belt_color")
        _bw = _WAIST_HALF_U + 0.28
        P.append(opoly(rrect(_gx(-_bw), _gy(21.4), 2 * _bw * _G_SCALE, 6.6, 2), belt, d=1.1))
        P.append(poly(rrect(67.2, _gy(21.4) + 1.6, 5.6, 3.6, 1), buckle or "#7a7a84"))
        _gate(None)
    _xon()

    # ---- near arm + near leg (over the torso) ----
    _xoff()
    _grp("body"); _gate(None)
    if arms:
        _emit_arm(1)
    if legged and not long_torso:
        _emit_leg(1)              # under a coat this leg went behind the torso
    elif not legged:
        _grp("body"); P.append(opoly(ngon(70, hip_y + 12, 13, 9, 14), SKINL, d=_FD))

    _grp("body"); _gate(None)
    if shoulders:      # a cap sat squarely on the top centre of each arm, so
                       # it reads as a pad ON the shoulder, not beside it
        _gate("shoulder_color")
        for _s in (-1, 1):
            if shoulders_side in ("both", "left" if _s < 0 else "right"):
                _c = arm_top(_s)
                _pad = ngon(_c[0], _c[1] - 0.6, 5.6, 4.0, 16)
                P.append(opoly(_pad, shoulders, d=1.2))
                P.append(poly(_cap_shade(_pad, _c[0], 0.40), _shade(shoulders, -22)))
        _gate(None)
    _xon()
    if harness:
        if harness_side in ("both", "left"):
            P.append(bar(56, 84, 82, 116, 2, harness))
        if harness_side in ("both", "right"):
            P.append(bar(84, 84, 58, 116, 2, harness))

    _xoff()
    # The head and the Grounded face kit. The head is FULL SIZE whether or
    # not there is a helmet - the shell goes over it further down, it doesn't
    # replace it - and it carries the same one-direction side plane the limbs
    # do, shaped as a leaf across the far cheek and jaw.
    _grp("body"); _gate(None)
    fr, face_cx, face_cy = FIG_HEAD_R, 70.0, FIG_HEAD_CY
    for sgn in (-1, 1):
        P.append(opoly(_fp([(sgn * dx, dy) for dx, dy in EAR_D], face_cx, face_cy, fr),
                       SKINF, d=_FD))
    P.append(opoly(_fp(HEAD_SHAPE, face_cx, face_cy, fr), SKINF, d=_FD))
    P.append(poly(_fp(HEAD_SHADE, face_cx, face_cy, fr), SKINS))

    if visor:
        # sides on the skull's own profile, bottom edge kept ABOVE the tip of
        # the nose, and the same one-direction shade the rest of the body has
        _gate("visor_color")
        _vt, _vb = face_cy - fr * 0.46, face_cy + fr * 0.215
        _vs = head_band(face_cx, face_cy, fr, _vt, _vb, inset=0.6)
        P.append(opoly(_vs, visor, d=1.2))
        P.append(poly(_cap_shade(_vs, face_cx, 0.34), _shade(visor, -26)))
        P.append(poly([(face_cx - fr * 0.62, _vt + 1.4), (face_cx - fr * 0.20, _vt + 1.4),
                       (face_cx - fr * 0.34, _vb - 1.6), (face_cx - fr * 0.70, _vb - 1.6)],
                      _shade(visor, 30)))                          # a catch of light
        _gate(None)
    elif eyes:
        P.extend(face_kit(face_cx, face_cy, fr, SKINF,
                          brow_col or _tone(hair_col, (0.74, 0)), eye_col))

    # hair, or the shell over the top of the head
    _grp("body")
    if helmet or hat:
        _gate("helmet_color" if helmet else None)
        P.extend(emit_hair((HELMET_LAMP_LIST if lamp else HELMET_LIST) if helmet
                           else HAT_LIST,
                           helmet or hat, face_cx, face_cy, fr))
        _gate(None)
    elif hair and not cap:
        _gate("hair_color")
        P.extend(emit_hair(HAIR_PARTS.get(hair, HAIR_PARTS["crop"]),
                           hair_col, face_cx, face_cy, fr))
        _gate(None)

    if badge_cross:
        _gate("badge_color")
        cx, cy = 70, round(_gy(23.4), 1)
        P.append(opoly([(cx-3,cy-6),(cx+3,cy-6),(cx+3,cy-3),(cx+6,cy-3),(cx+6,cy+3),
                        (cx+3,cy+3),(cx+3,cy+6),(cx-3,cy+6),(cx-3,cy+3),(cx-6,cy+3),
                        (cx-6,cy-3),(cx-3,cy-3)], badge, d=0.9))
        _gate(None)
    elif badge:            # a small diamond over the heart, high on the breast
        _gate("badge_color")
        bx, by = _gx(-1.55), _gy(24.3)
        P.append(opoly([(bx, by-2.3), (bx+2.3, by), (bx, by+2.3), (bx-2.3, by)],
                       badge, d=0.9))
        _gate(None)
    if helmet_ring:
        P.append(dots_ring(70, FIG_HEAD_CY, FIG_HEAD_R * 1.35, accent, n=26, dot=1.0))
    if accent_dot:
        P.append(circ(70, 203, 2.6, accent))
    return P


# ---------------------------------------------------------------- issue hardware
# The Sol Federation "issue" ships / station / buildings / decal / interior plan.
# Authored here; gen_split.py renders them straight into sol-federation.html
# (they used to be baked into the removed standard-issue.html and grabbed).
def _flame(pts): return poly(pts, "#8cb9ff", cls="flame")

def gen29(vb, aria):  # issue shuttle
    P = [poly([(0,0),(200,0),(200,200),(0,200)], GRID)]
    P.append(opoly(rrect(78,34,44,120,14), "#41506a", d=1.7, ol=SHAD))
    P.append(bar(100,40,100,148,3,"#dfe6ee"))
    P += [sq(84,54,7,"#cfe0f0"), sq(109,54,7,"#cfe0f0")]
    P.append(_flame([(96,152),(100,184),(104,152)]))
    P.append(opoly(rrect(93,154,14,20,3), "#5a6b82", d=1.4, ol=SHAD))
    P.append(poly([(92,158),(100,168),(108,158)], "#f2b23a"))
    P.append('<text x="100" y="122" fill="#8b97ab" font-family="IBM Plex Mono, monospace" '
             'font-size="7" text-anchor="middle">SF-04</text>')
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen30(vb, aria):  # issue lighter
    P = [poly([(0,0),(200,0),(200,200),(0,200)], GRID)]
    P.append(opoly(rrect(72,22,56,150,14), "#41506a", d=1.7, ol=SHAD))
    P.append(bar(72,72,128,72,1.4,SHAD)); P.append(bar(72,122,128,122,1.4,SHAD))
    P.append(bar(100,26,100,168,3,"#dfe6ee"))
    for wx,wy in [(80,40),(114,40),(80,90),(114,90),(80,140),(114,140)]:
        P.append(sq(wx,wy,6,"#cfe0f0"))
    P.append(_flame([(81,170),(85,202),(89,170)]))
    P.append(_flame([(111,170),(115,202),(119,170)]))
    for nx in (78,108):
        P.append(opoly(rrect(nx,172,14,20,3), "#5a6b82", d=1.4, ol=SHAD))
        P.append(poly([(nx,176),(nx+7,185),(nx+14,176)], "#f2b23a"))
    P.append('<text x="100" y="150" fill="#8b97ab" font-family="IBM Plex Mono, monospace" '
             'font-size="7" text-anchor="middle">SF-217</text>')
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen31(vb, aria):  # issue cutter
    P = [poly([(0,0),(200,0),(200,200),(0,200)], GRID)]
    hull = [(84,36),(116,36),(124,52),(124,146),(120,155),(112,158),
            (88,158),(80,155),(76,146),(76,52)]
    P.append(opoly(hull, "#41506a", d=1.7, ol=SHAD))
    P.append(poly([(76,88),(124,88),(124,98),(76,98)], "#f2b23a"))
    P.append(poly([(76,98),(124,98),(124,104),(76,104)], "#dfe6ee"))
    P.append(opoly(rrect(92,26,16,10,2), "#5a6b82", d=1.3, ol=SHAD))
    P.append(circ(100,20,3,"#e15a5a"))
    P += [sq(82,56,7,"#cfe0f0"), sq(111,56,7,"#cfe0f0")]
    P.append(_flame([(85,152),(88,182),(91,152)]))
    P.append(_flame([(109,152),(112,182),(115,152)]))
    for nx in (82,106):
        P.append(opoly(rrect(nx,154,12,18,3), "#5a6b82", d=1.4, ol=SHAD))
        P.append(poly([(nx,158),(nx+6,166),(nx+12,158)], "#f2b23a"))
    P.append('<text x="100" y="134" fill="#8b97ab" font-family="IBM Plex Mono, monospace" '
             'font-size="7" text-anchor="middle">SF-88</text>')
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen32(vb, aria):  # issue tender - docking-collar ring, strip-built, transparent hole
    P = [poly([(0,0),(200,0),(200,200),(0,200)], GRID)]
    P.append(opoly(rrect(70,60,60,94,14), "#41506a", d=1.7, ol=SHAD))
    P.append(oring(100, 48, 18, 11, "#5a6b82", d=1.5, n=44))
    P.append(poly([(74,96),(126,96),(126,101),(74,101)], "#f2b23a"))
    P.append(poly([(74,112),(126,112),(126,117),(74,117)], "#f2b23a"))
    P.append(poly([(74,60),(126,60),(126,64),(74,64)], "#f2b23a", op=0.9))
    P.append(poly([(74,150),(126,150),(126,154),(74,154)], "#f2b23a", op=0.9))
    P.append(bar(100,66,100,150,3,"#dfe6ee"))
    for nx in (75,91,105,121):
        P.append(_flame([(nx,150),(nx+2.5,176),(nx+5,150)]))
    for nx in (72,88,102,118):
        P.append(opoly(rrect(nx,152,11,16,2), "#5a6b82", d=1.2, ol=SHAD))
        P.append(poly([(nx,156),(nx+5.5,163),(nx+11,156)], "#f2b23a"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen33(vb, aria):  # standard ring - 3 strip-built modules, joined at the intersections
    P = [poly([(0,0),(240,0),(240,200),(0,200)], GRID)]
    rows = (58, 98, 138)
    Ro, Ri = 30, 20
    for cy in rows:                       # outer rims (behind), thin
        P.append(ring_strip(120, cy, Ro + 1.6, Ro, SHAD, n=38))
    for cy in rows:                       # bodies - one colour, they merge; empty centres
        P.append(ring_strip(120, cy, Ro, Ri, "#41506a", n=38))
    P.append(opoly(rrect(114, 14, 12, 168, 4), "#5a6b82", d=1.5, ol=SHAD))   # spine
    for cy in rows:                       # hazard chevrons on the flanks
        P.append(poly([(144, cy-4), (152, cy), (144, cy+4)], "#f2b23a"))
        P.append(poly([(96, cy-4), (88, cy), (96, cy+4)], "#f2b23a"))
    for wy in (24, 62, 102, 142):
        P.append(sq(118, wy, 4, "#cfe0f0"))
    P.append(opoly(rrect(108, 8, 24, 9, 3), "#5a6b82", d=1.4, ol=SHAD))
    P.append(opoly(rrect(108, 180, 24, 9, 3), "#5a6b82", d=1.4, ol=SHAD))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen34(vb, aria):  # issue block
    P = [poly([(0,0),(200,0),(200,210),(0,210)], GRID)]
    P.append(poly(ngon(100,192,60,8,16), "#ffffff", op=0.05))
    for fy in (150,108,66,24):
        P.append(opoly(rrect(66,fy,68,40,6), "#41506a", d=1.3, ol=SHAD))
    P.append(bar(73,24,73,190,3,"#dfe6ee"))
    for fy in (34,76,118,160):
        for wx in (88,106,122):
            P.append(sq(wx,fy,9,"#cfe0f0"))
    for cx in range(66,133,12):
        P.append(poly([(cx,188),(cx,182),(cx+6,185)], "#f2b23a"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen35(vb, aria):  # issue shed
    P = [poly([(0,0),(200,0),(200,210),(0,210)], GRID)]
    P.append(poly(ngon(100,184,86,8,16), "#ffffff", op=0.05))
    body = [(22,176),(22,92)]
    for i in range(1,10):
        t = i/10; body.append((22+156*t, 92-14*4*t*(1-t)))
    body += [(178,92),(178,176)]
    P.append(opoly(body, "#41506a", d=1.4, ol=SHAD))
    P.append(arcband(24, 176, 89, 12, 5, "#5a6b82"))
    P.append(opoly(rrect(72,112,56,64,8), "#5a6b82", d=1.4, ol=SHAD))
    P.append(poly([(70,110),(130,110),(130,118),(70,118)], "#f2b23a"))
    P.append(bar(72,130,128,130,1.3,SHAD)); P.append(bar(72,148,128,148,1.3,SHAD))
    for wx in (36,54,137,155):
        P.append(poly([(wx,98),(wx+9,98),(wx+9,105),(wx,105)], "#cfe0f0"))
    P.append(bar(29,90,29,176,3,"#dfe6ee"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen36(vb, aria):  # issue bollard
    P = [poly([(0,0),(200,0),(200,210),(0,210)], GRID)]
    P.append(poly(ngon(100,176,26,6,14), "#ffffff", op=0.05))
    P.append(poly(rrect(88,168,24,8,2), SHAD))
    P.append(opoly(rrect(92,86,16,84,7), "#41506a", d=1.4, ol=SHAD))
    P.append(poly([(92,120),(108,120),(108,127),(92,127)], "#dfe6ee"))
    P.append(poly([(90,86),(94,80),(100,78),(106,80),(110,86)], "#f2b23a"))
    P.append(circ(100,79,6,"#ffd98a"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen37(vb, aria):  # issue bench
    P = [poly([(0,0),(200,0),(200,210),(0,210)], GRID)]
    P.append(poly(ngon(100,168,44,7,14), "#ffffff", op=0.05))
    shell = [(52,140),(52,132),(54,124),(60,120),(66,118),(134,118),
             (140,120),(146,124),(148,132),(148,140)]
    P.append(opoly(shell, "#41506a", d=1.4, ol=SHAD))
    P.append(poly([(52,118),(148,118),(148,123),(52,123)], "#dfe6ee"))
    P.append(opoly(rrect(62,140,10,26,3), "#5a6b82", d=1.3, ol=SHAD))
    P.append(opoly(rrect(128,140,10,26,3), "#5a6b82", d=1.3, ol=SHAD))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen38(vb, aria):  # issue service counter
    P = [poly([(0,0),(200,0),(200,210),(0,210)], GRID)]
    P.append(poly(ngon(100,176,78,7,16), "#ffffff", op=0.05))
    shell = [(26,168),(26,84),(30,76),(36,74),(164,74),(170,76),(174,84),(174,168)]
    P.append(opoly(shell, "#41506a", d=1.4, ol=SHAD))
    P.append(poly([(26,74),(174,74),(174,79),(26,79)], "#dfe6ee"))
    for tx in (40,72,104,136):
        P.append(poly([(tx,92),(tx+20,92),(tx+20,104),(tx,104)], "#cfe0f0"))
    P.append(sq(92,60,10,"#f2b23a"))
    for cx in range(30,167,16):
        P.append(poly([(cx,168),(cx,160),(cx+8,164)], "#f2b23a"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen39(vb, aria):  # hazard chevron floor decal
    P = [poly([(0,0),(200,0),(200,160),(0,160)], GRID)]
    P.append(poly(rrect(30,50,140,60,4), SHAD))
    for x in (40,70,100,130):
        P.append(poly([(x,50),(x+18,80),(x,110),(x-10,110),(x+8,80),(x-10,50)], "#f2b23a"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'

def gen40(vb, aria):  # interior plan
    P = [poly([(0,0),(320,0),(320,200),(0,200)], GRID)]
    P.append(poly(rrect(40,82,240,36,6), "#4a5c76"))
    for ry in (30,116):
        for rx in (70,134,198):
            P.append(poly(rrect(rx,ry,52,54,8), "#4a5c76"))
    P.append(bar(44,100,276,100,1.4,"#f2b23a"))
    for x in (92,156,220):
        P.append(poly([(x-3,80),(x+2,80),(x,74)], "#f2b23a"))
        P.append(poly([(x-3,120),(x+2,120),(x,126)], "#f2b23a"))
    P.append(circ(292,100,4.5,"#8fb9c8"))
    P.append(bar(300,100,312,100,1.2,"#8fb9c8"))
    P.append(poly([(309,95),(316,100),(309,105),(311,100)], "#8fb9c8"))
    lab = ('<g fill="#c7d0de" font-family="IBM Plex Mono, monospace" font-size="6" letter-spacing="0.3">'
           '<text x="96" y="60" text-anchor="middle">DOCK</text>'
           '<text x="160" y="60" text-anchor="middle">OFFICES</text>'
           '<text x="224" y="60" text-anchor="middle">MED</text>'
           '<text x="96" y="148" text-anchor="middle">QUARTERS</text>'
           '<text x="160" y="148" text-anchor="middle">STORES</text>'
           '<text x="224" y="148" text-anchor="middle">QUARTERS</text>'
           '<text x="160" y="104" text-anchor="middle">CONCOURSE</text></g>')
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}{lab}</svg>'


# label substring (as gen_split lists them) -> (generator, viewBox)
ISSUE_PLATES = {
    "issue shuttle":       (gen29, "0 0 200 200"),
    "issue lighter":       (gen30, "0 0 200 200"),
    "issue cutter":        (gen31, "0 0 200 200"),
    "issue tender":        (gen32, "0 0 200 200"),
    "standard ring":       (gen33, "0 0 240 200"),
    "issue block":         (gen34, "0 0 200 210"),
    "issue shed":          (gen35, "0 0 200 210"),
    "issue bollard":       (gen36, "0 0 200 210"),
    "issue bench":         (gen37, "0 0 200 210"),
    "issue service counter": (gen38, "0 0 200 210"),
    "hazard chevron":      (gen39, "0 0 200 160"),
    "station interior":    (gen40, "0 0 320 200"),
}

def issue_plate(label):
    """The <svg> for a Federation hardware plate, matched by label substring."""
    key = next(k for k in ISSUE_PLATES if k in label.lower())
    fn, vb = ISSUE_PLATES[key]
    return fn(vb, label)
