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

# shallow "D" ear as (dx, dy) from the face centre in head-radii: flat side
# just outside the thick face outline (~1.12 r), a gentle bulge out past it,
# ~0.5 r tall. Mirrored on both sides. dy is SVG-down (positive = lower).
EAR_D = [(1.02, -0.30), (1.02, 0.26), (1.18, 0.20),
         (1.30, 0.02), (1.30, -0.12), (1.18, -0.26)]

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
    if cls != "flame" and not (op is not None and op < 0.2):
        _rec("points", [(round(x, 2), round(y, 2)) for x, y in pts], fill)
    a = f' class="{cls}"' if cls else ""
    o = f' opacity="{op}"' if op is not None else ""
    return f'<polygon{a} points="{fmt(pts)}" fill="{fill}"{o}/>'

def circ(cx, cy, r, fill, op=None):
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
_G_SCALE = 5.15                       # atlas units per Grounded study unit
_G_GROUND = 202.2                     # atlas-y of the sole (study u = 0)


def _gx(dx):
    return 70.0 + _G_SCALE * dx


def _gy(u):
    return _G_GROUND - _G_SCALE * u


FIG_HIP_Y = round(_gy(12.3))         # 139 - where the legs join the torso
FIG_FOOT_Y = round(_gy(1.6))         # 194 - ankle line; boots ~3 below, ground ~10

# Resting arm splay: each arm hangs a small angle out from the body about the
# shoulder joint, so the default pose reads relaxed and slightly open (and, in
# the side-on in-game render, one arm slightly ahead of the other). Baked into
# the figure geometry here so the atlases and the game agree. _arm_rot maps a
# point on the notional straight-down arm to its splayed position; the
# *_outfits.py signature files import it to re-anchor arm-mounted detail.
ARM_REST_DEG = 12
_ARM_PIVOT = (3.05, 25.9)            # shoulder joint, study coords (|x|, y)


def _arm_rot(s, ax, ay):
    """Atlas point on the straight arm -> atlas point after the resting splay.
    s = -1 for the left arm, +1 for the right; both rotate outward."""
    ux, uy = (ax - 70.0) / _G_SCALE, (_G_GROUND - ay) / _G_SCALE
    px, py = s * _ARM_PIVOT[0], _ARM_PIVOT[1]
    ang = math.radians(s * ARM_REST_DEG)
    ca, sa = math.cos(ang), math.sin(ang)
    dx, dy = ux - px, uy - py
    return _gx(px + dx * ca - dy * sa), _gy(py + dx * sa + dy * ca)


def figure_parts(*, suit, boot, leg=None, sleeve=None, helmet=None, helmet_r=18,
                 hat=None, cap=None, no_helmet=False, legged=True, arms=True, coat=False,
                 torso_long=False, backpack=None, spikes=None, spikes_side="both",
                 antenna=None, collar=None, shoulders=None, shoulders_side="both",
                 chest=None, rivets=None, band=None, sash=None, badge=None,
                 badge_cross=False, belt=None, buckle=None, visor=None, harness=None,
                 harness_side="both", pod=None, blade=None, knee=None, torch=None,
                 hipline=False, helmet_ring=False, accent_dot=False,
                 accent="#8fb9c8", eyes=True):
    leg = leg or boot
    sleeve = sleeve or suit
    P = []
    long_torso = torso_long or coat
    hip_y = round(_gy(10.8)) if long_torso else FIG_HIP_Y   # a coat hem drops lower
    # A cinched waist about halfway up the standing figure, well above the hip
    # line. Every belt, sash end and hip pouch anchors here (waist_y), not at
    # the hip; the torso pinches in at the waist and flares back out below.
    waist_y = round(_gy(19.2))               # 103
    waist_hw = 13
    belt_y = waist_y - 4
    foot_y = FIG_FOOT_Y if legged else round(_gy(6.5))

    # The figure reads side-on: the LEFT arm + LEFT leg are the FAR limbs, drawn
    # behind the torso; the RIGHT arm + leg are the NEAR limbs, drawn over it.
    # So one arm and one leg of each pair sits in front, the other behind (the
    # grounded-person study's layering). person.py picks the same split by
    # animation group and mirrors on facing.
    def _arm_shaft(s):
        # domed top centred on the shoulder joint, endpoints level with the
        # shoulder line so the (rotated) cap tucks under the torso, no spike
        return [(_gx(s * 2.3), _gy(25.5)), (_gx(s * 2.6), _gy(25.97)),
                (_gx(s * 3.05), _gy(26.12)), (_gx(s * 3.5), _gy(25.97)),
                (_gx(s * 3.8), _gy(25.5)), (_gx(s * 3.1), _gy(13.6)),
                (_gx(s * 1.9), _gy(13.6))]

    def _leg_trap(s):
        cx = s * 1.7
        # a clean trapezoid hip -> ankle (no mid vertex, so the walk-cycle
        # shear in Person._place doesn't kink it at the calf)
        return [(_gx(s * 3.4), _gy(12.3)), (_gx(cx + s * 0.95), _gy(1.6)),
                (_gx(cx - s * 0.95), _gy(1.6)), (_gx(s * 0.15), _gy(12.3))]

    def _knee(s):
        return [(_gx(s * 0.3), _gy(8.6)), (_gx(s * 2.3), _gy(8.6)),
                (_gx(s * 2.3), _gy(6.6)), (_gx(s * 0.3), _gy(6.6))]

    def _emit_arm(s):
        _grp("arm_l" if s < 0 else "arm_r")
        P.append(opoly([_arm_rot(s, x, y) for x, y in _arm_shaft(s)], sleeve, d=_FD))
        _grp("hand_l" if s < 0 else "hand_r")
        P.append(ocirc(*_arm_rot(s, _gx(s * 2.5), _gy(12.7)), 3.2, SKINF, d=_FD))

    def _emit_leg(s):
        _grp("leg_l" if s < 0 else "leg_r")
        P.append(opoly(_leg_trap(s), leg, d=_FD))
        if knee:
            _grp("leg_l" if s < 0 else "leg_r")
            P.append(opoly(_knee(s), knee, d=_FD))
        _grp("boot_l" if s < 0 else "boot_r")
        P.append(opoly(ngon(_gx(s * 1.7), 197, 9, 6, 12), boot, d=_FD))

    _grp("body"); _gate(None)

    P.append(poly(ngon(70, (foot_y + 8) if legged else 172, 30, 7, 14), "#ffffff", op=0.05))

    # back pieces
    if backpack:
        _grp("body"); _gate("backpack_color")
        P.append(opoly(rrect(50, 62, 40, 74, 6), backpack, d=1.3))
    if spikes:                                   # rooted low - shoulder pads sit over the base
        _grp("body"); _gate("spike_color")
        if spikes_side in ("both", "left"):
            P.append(opoly([(46, 80), (54, 76), (42, 50)], spikes, d=1.1))
        if spikes_side in ("both", "right"):
            P.append(opoly([(94, 80), (86, 76), (98, 50)], spikes, d=1.1))
        if spikes_side == "uneven":              # Vherathi asymmetry
            P.append(opoly([(47, 80), (55, 76), (44, 46)], spikes, d=1.1))
            P.append(opoly([(94, 80), (87, 77), (97, 58)], spikes, d=1.1))
    if antenna:
        _grp("body"); _gate("antenna_color")
        P.append(bar(80, 34, 88, 16, 1.3, antenna))
        P.append(ocirc(88, 16, 2.2, antenna, d=1.1))
    _gate(None)
    if blade:                                    # grown guard-blade down one arm
        P.append(opoly([(44, 60), (50, 60), (52, 132), (48, 150), (43, 142)], blade, d=_FD))

    # ---- far arm + far leg (behind the torso) ----
    _grp("body"); _gate(None)
    if arms:
        _emit_arm(-1)
    if legged:
        _emit_leg(-1)

    # torso - one smooth hourglass from the hip, through the cinched waist, up
    # to a narrow rounded shoulder (no armpit notch). _gt is the Grounded study
    # torso (left-silhouette half-widths, neck line down to hip); mirrored for
    # the right, so the curve is symmetric by construction.
    _grp("body"); _gate(None)
    _gt = [(2.6, 26.5), (3.2, 25.9), (3.55, 24.7), (3.5, 23.1),
           (3.3, 21.2), (2.5, 19.2), (3.4, 12.3)]
    if long_torso:
        _gt = _gt[:-1] + [(3.7, 10.8)]
    torso = ([(_gx(-h), _gy(y)) for h, y in _gt]
             + [(_gx(h), _gy(y)) for h, y in reversed(_gt)])
    P.append(opoly(torso, suit, d=_FD))

    # short neck - a skin column from the collar line up under the jaw, over
    # the torso and behind the head.
    P.append(opoly([(_gx(-1.15), _gy(26.4)), (_gx(-1.15), _gy(28.7)),
                    (_gx(1.15), _gy(28.7)), (_gx(1.15), _gy(26.4))], SKINF, d=_FD))

    # hip kit - a pouch or a stowed cutting torch on the right hip, hung from
    # the waist. Drawn before the near arm so the arm hangs over it.
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
    if band:                                      # chest band, above the belt
        P.append(opoly([(54, 88), (86, 88), (84, 100), (56, 100)], band, d=1.0))

    # helmet / hat / cap - same head height for every outfit
    _grp("body")
    if helmet:
        _gate("helmet_color"); P.append(ocirc(70, round(_gy(30.0), 1), helmet_r, helmet, d=_FD)); _gate(None)
    if hat:
        P.append(ocirc(70, round(_gy(30.0), 1), helmet_r, hat, d=_FD))
    if cap:                                       # flat brimmed cap over the head
        P.append(opoly([(56, 40), (84, 40), (80, 32), (73, 27), (65, 27), (58, 32)], cap, d=1.2))

    # front torso pieces: chest plate -> sash (over it) -> collar (over sash) -> belt
    if chest:
        _gate("chest_plate_color")
        P.append(opoly([(57, 72), (83, 72), (80, 106), (60, 106)], chest, d=1.2))
        if rivets:
            for rx in (63, 77):
                for ry in (80, 98):
                    P.append(circ(rx, ry, 1.4, rivets))
        _gate(None)
    if sash:      # a baldric: over the left shoulder, across the chest, tucked
                  # under the belt at the opposite (right) hip
        _gate("sash_color")
        P.append(opoly([(52, 65), (58, 62),                 # over the top of the left shoulder
                        (64, 80), (72, 95),                  # diagonally across the chest
                        (83, waist_y + 2),                   # down to the right waist
                        (77, waist_y + 9),                   # band width at the waist end
                        (66, 96), (58, 82), (48, 68)],       # back up the underside
                       sash, d=1.1))
        _gate(None)
    if collar:
        _gate("collar_color")
        P.append(opoly([(58, 63), (82, 63), (79, 74), (61, 74)], collar, d=1.1))
        _gate(None)
    if belt:                                       # over the top of the hip kit's strap
        _gate("belt_color")
        P.append(opoly(rrect(70 - waist_hw - 4, belt_y, 2 * (waist_hw + 4), 9, 2), belt, d=1.1))
        P.append(poly(rrect(66, belt_y + 2, 8, 5, 1), buckle or "#7a7a84"))
        _gate(None)

    # ---- near arm + near leg (over the torso) ----
    _grp("body"); _gate(None)
    if arms:
        _emit_arm(1)
    if legged:
        _emit_leg(1)
    else:
        _grp("body"); P.append(opoly(ngon(70, hip_y + 12, 13, 9, 14), SKINL, d=_FD))

    _grp("body"); _gate(None)
    if shoulders:                                # sit outboard + high, over the arm tops
        _gate("shoulder_color")
        if shoulders_side in ("both", "left"):
            P.append(ocirc(52, 69, 6, shoulders, d=1.2))
        if shoulders_side in ("both", "right"):
            P.append(ocirc(88, 69, 6, shoulders, d=1.2))
        _gate(None)
    if harness:
        if harness_side in ("both", "left"):
            P.append(bar(56, 84, 82, 116, 2, harness))
        if harness_side in ("both", "right"):
            P.append(bar(84, 84, 58, 116, 2, harness))

    # face - always ringed, so it has an edge wherever it clears the helmet.
    # The Grounded face kit: shallow D-ears (bare head only, tucked under the
    # face), oval eyes with a full-height pupil, a short straight brow over each,
    # a tan sideways-oval under-nose shadow, and a soft mouth line in the same
    # tone. fr is the face radius so every feature scales with helmet vs bare.
    _grp("body"); _gate(None)
    # The head reads as a Grounded-study oval - taller than wide (x radius
    # 0.92 * fr) - not a circle, with the same thin outline as the body.
    if helmet or hat:
        fr, face_cx, face_cy = 11.5, 70.0, round(_gy(29.9), 1)
        P.append(ooval(face_cx, face_cy, fr * 0.92, fr, SKINF))
    else:
        fr, face_cx, face_cy = 14.0, 70.0, round(_gy(30.4), 1)
        for sgn in (-1, 1):
            P.append(opoly([(face_cx + sgn * fr * dx, face_cy + fr * dy)
                            for dx, dy in EAR_D], SKINF, d=_FD))
        P.append(ooval(face_cx, face_cy, fr * 0.92, fr, SKINF))

    if visor:
        _gate("visor_color")
        P.append(opoly([(face_cx - fr * 0.98, face_cy - fr * 0.5),
                        (face_cx + fr * 0.98, face_cy - fr * 0.5),
                        (face_cx + fr * 0.9, face_cy + fr * 0.22),
                        (face_cx - fr * 0.9, face_cy + fr * 0.22)], visor, d=1.2))
        _gate(None)
    elif eyes:
        eye_cy = face_cy - fr * 0.08
        brow_y = face_cy - fr * 0.36
        for sgn in (-1, 1):
            exc = face_cx + sgn * fr * 0.42
            P.append(opoly(ngon(exc, eye_cy, fr * 0.22, fr * 0.15, 14), EYEW, d=0.7))
            P.append(poly(ngon(exc, eye_cy, fr * 0.135, fr * 0.15, 12), EYE))
            bw, bh = fr * 0.20, fr * 0.08
            P.append(poly([(exc - bw, brow_y), (exc + bw, brow_y),
                           (exc + bw, brow_y + bh), (exc - bw, brow_y + bh)], BROW))
        P.append(poly(ngon(face_cx, face_cy + fr * 0.28, fr * 0.22, fr * 0.09, 12), SKINL))
        P.append(bar(face_cx - fr * 0.22, face_cy + fr * 0.58,
                     face_cx + fr * 0.22, face_cy + fr * 0.58, 0.9, SKINL))

    if badge_cross:
        _gate("badge_color")
        cx, cy = 70, 95
        P.append(opoly([(cx-3,cy-6),(cx+3,cy-6),(cx+3,cy-3),(cx+6,cy-3),(cx+6,cy+3),
                        (cx+3,cy+3),(cx+3,cy+6),(cx-3,cy+6),(cx-3,cy+3),(cx-6,cy+3),
                        (cx-6,cy-3),(cx-3,cy-3)], badge, d=0.9))
        _gate(None)
    elif badge:                                   # a small diamond, worn on the left breast
        _gate("badge_color")
        P.append(opoly([(62,82),(66,87),(62,92),(58,87)], badge, d=0.9))
        _gate(None)

    if helmet_ring:
        P.append(dots_ring(70, round(_gy(30.4), 1), 18, accent, n=26, dot=1.0))
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
