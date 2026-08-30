"""Signature outfit specimens for the Past the Reach atlas.

Each culture gets `figure_parts` for the shared body + standard accessory
kit, then a layer of *signature* shapes drawn behind (`pre`) and in front
(`post`) that no other culture uses - a full ceramic ember-slit mask for
Kessari, asymmetric eye-bubble helm clusters for Vherathi, an antler
headdress for the Vetl, and so on. Strokeless (<polygon> + <circle>).

build_outfit(key) -> (base_opts_dict, pre_svg, post_svg)
composed by gen_frontier.py as:  grid + pre + figure_parts(**base) + post
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, ngon, rrect, opoly, ocirc, bar, offset_poly, _u

OUT = "#141219"


def rib(pts, w, col, op=None):
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


def dot_run(x0, y0, x1, y1, n, r, col):
    return "".join(circ(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1), r, col)
                   for i in range(n))


def scallop_hem(x0, x1, y, depth, n, col):
    step = (x1 - x0) / n
    pts = [(x0, y - depth)]
    for i in range(n):
        pts.append((x0 + step * i, y - depth))
        pts.append((x0 + step * (i + 0.5), y + depth))
    pts.append((x1, y - depth))
    return poly(pts, col)


def opoly_s(pts, fill, d=1.2):
    return poly(offset_poly(pts, d), OUT) + poly(pts, fill)


# ================================================================ signatures
def deeprock():
    base = dict(hat="#c9b083", suit="#8a7a68", boot="#3a342e", sleeve="#7a6a58",
                chest="#5c524a", rivets="#33302b", belt="#3a342e", buckle="#d6b03c",
                band="#d6b03c")
    pre = ""
    p = []
    # ear defenders - pucks on the sides of the hard hat
    for x in (52, 88):
        p.append(ocirc(x, 50, 4.4, "#4a423b", d=1.1))
        p.append(circ(x, 50, 2.2, "#d6b03c"))
    p.append(bar(52, 44, 88, 44, 1.6, "#4a423b"))
    # shoulder floodlamp on the right, with a light cone
    p.append(opoly_s(rrect(92, 66, 11, 9, 1), "#4a423b"))
    p.append(circ(97, 70, 2.6, "#ffe078"))
    p.append(poly([(97, 70), (120, 58), (120, 84)], "#ffe078", op=0.12))
    # ore-scoop gauntlet - an oversized angular mitt over the left hand
    p.append(opoly_s([(37, 114), (50, 116), (51, 124), (48, 132), (39, 132), (35, 124)], "#5c524a"))
    p.append(bar(38, 119, 49, 120, 1.1, "#33302b"))
    p.append(bar(38, 125, 48, 126, 1.1, "#33302b"))
    p.append(poly([(35, 122), (31, 124), (33, 130), (37, 128)], "#4a423b"))   # thumb
    return base, pre, "".join(p)


def kessari():
    base = dict(coat=True, torso_long=True, suit="#241f2b", boot="#171420",
                leg="#1e1a26", sleeve="#241f2b", sash="#ff7a34", collar="#332c3c")
    p = []
    # smooth full ceramic mask over the whole face, one vertical ember slit
    p.append(ocirc(70, 51, 13.5, "#2a2432", d=1.4))
    p.append(poly([(69, 42), (71, 42), (71.5, 60), (68.5, 60)], "#ff7a34"))
    p.append(circ(70, 40, 1.4, "#ffd9a0"))
    # ash wrappings - thin bands across forearms and shins
    for y in (100, 106, 112):
        p.append(bar(41, y, 51, y, 1.1, "#b8ad9a"))
        p.append(bar(89, y, 99, y, 1.1, "#b8ad9a"))
    for y in (168, 176, 184):
        p.append(bar(57, y, 70, y, 1.1, "#b8ad9a"))
        p.append(bar(70, y, 83, y, 1.1, "#b8ad9a"))
    # a censer pendant on a chain at the chest
    p.append(bar(70, 62, 70, 88, 0.8, "#7a7060"))
    p.append(ocirc(70, 92, 5, "#2a2432", d=1.1))
    for k in range(6):
        a = 2 * math.pi * k / 6
        p.append(circ(70 + 3 * math.cos(a), 92 + 3 * math.sin(a), 0.9, "#ff7a34"))
    return base, "", "".join(p)


def meridian():
    base = dict(coat=True, cap="#4a3826", suit="#8a6a44", boot="#4a3826",
                sleeve="#7a5c38", belt="#3a2c1c", buckle="#e8ce96")
    # brocade over-mantle behind the arms with a scalloped hem
    pre = (opoly_s([(48, 66), (92, 66), (98, 120), (42, 120)], "#7a5c38")
           + scallop_hem(44, 96, 120, 4, 7, "#7a5c38"))
    p = []
    # gorget at the throat
    p.append(opoly_s([(58, 62), (82, 62), (80, 70), (60, 70)], "#e8ce96"))
    # gold frogging - braid bars across the chest
    for y in (78, 88, 98):
        p.append(bar(58, y, 82, y, 1.6, "#e8ce96"))
        p.append(circ(56, y, 1.6, "#e8ce96"))
        p.append(circ(84, y, 1.6, "#e8ce96"))
    # squared epaulettes
    for x in (46, 94):
        p.append(opoly_s(rrect(x - 8, 70, 16, 6, 1), "#e8ce96"))
        p.append(dot_run(x - 6, 76, x + 6, 76, 3, 1.0, "#4a3826"))
    # plumed cap - a feather sweeping back
    p.append(rib([(78, 42), (92, 34), (104, 22), (110, 10)], 2.2, "#e8ce96"))
    p.append(rib([(78, 42), (90, 36), (100, 26)], 1.0, "#ffeec8"))
    # a badge of office
    p.append(opoly_s([(70, 104), (75, 110), (70, 118), (65, 110)], "#ffeec8"))
    return base, pre, "".join(p)


def theln():
    base = dict(helmet="#d8d2c4", visor="#7fe8e8", suit="#c8c0b0", boot="#8a857a",
                sleeve="#bfb8a8", harness="#9a9384", harness_side="left", pod="#a8a294")
    # spar-frame membrane cape behind the body, echoing the ship wings
    pre = (poly([(70, 64), (30, 150), (70, 130)], "#4d7078", op=0.8)
           + poly([(70, 64), (112, 150), (70, 130)], "#3f5f66", op=0.75)
           + rib([(70, 64), (30, 150)], 1.0, "#c8c0b0")
           + rib([(70, 64), (112, 150)], 1.0, "#c8c0b0")
           + rib([(70, 64), (70, 132)], 1.0, "#c8c0b0"))
    p = []
    # light-strand trim along cape edge + harness
    p.append(dot_run(30, 150, 70, 130, 5, 1.1, "#7fe8e8"))
    p.append(dot_run(112, 150, 70, 130, 5, 1.1, "#7fe8e8"))
    p.append(dot_run(56, 90, 84, 120, 4, 1.0, "#7fe8e8"))
    # spar collar - two thin struts rising from the shoulders
    p.append(rib([(52, 68), (48, 52), (52, 40)], 1.0, "#c8c0b0"))
    p.append(rib([(88, 68), (92, 52), (88, 40)], 1.0, "#c8c0b0"))
    p.append(circ(52, 40, 1.4, "#7fe8e8"))
    p.append(circ(88, 40, 1.4, "#7fe8e8"))
    return base, pre, "".join(p)


def vherathi():
    base = dict(suit="#6b4f86", boot="#3c2b52", sleeve="#5a4272", blade="#8fffcf")
    p = []
    # helmet dome (asymmetric) + clusters of circular eye-bubbles
    p.append(opoly_s([(54, 54), (58, 34), (76, 30), (88, 38), (86, 56)], "#7a5c96"))
    left_bubbles = [(60, 44, 3.4), (58, 52, 2.6), (64, 50, 2.2), (62, 38, 2.4)]
    right_bubbles = [(80, 42, 3.0), (82, 50, 2.0)]
    for bx, by, br in left_bubbles + right_bubbles:
        p.append(ocirc(bx, by, br, "#8fffcf", d=1.0))
        p.append(circ(bx - br * 0.3, by - br * 0.3, br * 0.35, "#e8fff5"))
    # resin-vein tracery - asymmetric branching glow up the torso and one arm
    p.append(rib([(70, 150), (66, 120), (60, 96), (56, 76), (52, 64)], 0.8, "#8fffcf"))
    p.append(rib([(60, 96), (52, 88), (46, 84)], 0.7, "#8fffcf"))
    p.append(rib([(66, 120), (74, 108), (78, 96)], 0.7, "#8fffcf"))
    p.append(rib([(44, 80), (44, 110), (46, 118)], 0.7, "#8fffcf"))
    for vx, vy in ((56, 76), (52, 88), (78, 96), (46, 118)):
        p.append(circ(vx, vy, 1.3, "#8fffcf"))
    return base, "", "".join(p)


def drossholt():
    base = dict(suit="#b58a5c", boot="#5a4130", sleeve="#a97f52")
    p = []
    # riveted patch-plate armour - mismatched plates bolted on at odd angles
    plates = [([(50, 70), (72, 68), (74, 92), (52, 96)], "#8a6845"),
              ([(72, 74), (90, 78), (88, 104), (70, 100)], "#9a7550"),
              ([(54, 100), (78, 104), (76, 128), (52, 124)], "#7a5c3f")]
    for pts, col in plates:
        p.append(opoly_s(pts, col))
        cx = sum(x for x, _ in pts) / 4
        cy = sum(y for _, y in pts) / 4
        for dx, dy in ((-7, -7), (7, -7), (7, 7), (-7, 7)):
            p.append(circ(cx + dx, cy + dy, 1.2, "#4a3527"))
    # bolted box respirator over the mouth + hose to a side canister
    p.append(opoly_s(rrect(62, 48, 16, 10, 1), "#5a4130"))
    for gx in (65, 69, 73):
        p.append(bar(gx, 50, gx, 56, 0.9, "#2c2018"))
    p.append(rib([(78, 54), (92, 60), (96, 78)], 1.4, "#5a4130"))
    p.append(opoly_s(rrect(90, 78, 12, 20, 2), "#6a4f39"))
    # one big pauldron, one bare shoulder (mismatched)
    p.append(ocirc(46, 76, 8, "#5a4130", d=1.2))
    p.append(circ(46, 76, 4, "#8a6845"))
    return base, "", "".join(p)


def federation():
    base = dict(helmet="#4a5a72", suit="#3a4a63", boot="#232c3a", collar="#cfe0f0")
    p = []
    # regulation helmet: horizontal visor slit + chin guard (over the round helm)
    p.append(poly([(56, 48), (84, 48), (82, 55), (58, 55)], "#1c2430"))
    p.append(bar(56, 51, 84, 51, 1.0, "#8fb9c8"))
    p.append(opoly_s([(58, 58), (82, 58), (78, 66), (62, 66)], "#5a6b82"))
    # contrast centreline stripe down the torso
    p.append(poly([(68, 62), (72, 62), (72, 150), (68, 150)], "#dfe6ee"))
    # hazard-chevron shoulder flash (right)
    for k in range(3):
        y = 72 + k * 4
        p.append(poly([(88, y), (94, y + 3), (100, y), (98.5, y),
                       (94, y + 2), (89.5, y)], "#f2b23a"))
    # stencilled registration on the chest
    p.append('<text x="70" y="106" fill="#8fb9c8" font-family="IBM Plex Mono, monospace" '
             'font-size="7" text-anchor="middle" letter-spacing="0.5">SF-114</text>')
    return base, "", "".join(p)


def kaethar():
    base = dict(coat=True, torso_long=True, suit="#2b3040", boot="#171b26",
                leg="#20242f", sleeve="#2b3040", belt="#12151d")
    # straight-edged greatcoat skirt below the belt (sharp rectangular corners)
    pre = opoly_s([(50, 150), (90, 150), (94, 186), (46, 186)], "#242938")
    p = []
    # angular full helm: horizontal red sensor bar + peaked crest
    p.append(opoly_s([(55, 56), (56, 40), (70, 32), (84, 40), (85, 56),
                      (78, 62), (62, 62)], "#3a4053"))
    p.append(poly([(66, 34), (74, 34), (72, 22), (68, 22)], "#3a4053"))     # crest
    p.append(bar(56, 47, 84, 47, 2.0, "#d6402c"))                            # sensor bar
    # gorget + squared pauldrons
    p.append(opoly_s([(58, 62), (82, 62), (80, 70), (60, 70)], "#3a4053"))
    for x in (45, 95):
        p.append(opoly_s(rrect(x - 9, 68, 18, 12, 1), "#3a4053"))
        p.append(bar(x - 6, 74, x + 6, 74, 1.2, "#12151d"))
    # rigid breastplate with a hard geometric unit sigil
    p.append(opoly_s([(56, 76), (84, 76), (81, 112), (59, 112)], "#333849"))
    cx, cy = 70, 94
    p.append(poly([(cx, cy - 8), (cx + 7, cy), (cx, cy + 8), (cx - 7, cy)], "#d6402c"))
    p.append(poly([(cx, cy - 4), (cx + 3.5, cy), (cx, cy + 4), (cx - 3.5, cy)], "#333849"))
    # rank bars on the left sleeve
    for k in range(3):
        p.append(bar(42, 92 + k * 5, 50, 92 + k * 5, 1.4, "#c9a24a"))
    return base, pre, "".join(p)


def vetl():
    base = dict(no_helmet=True, torso_long=True, suit="#6b4a35", boot="#3a2718",
                leg="#4a3122", sleeve="#5c3f2e")
    # layered hide mantle behind the body, ragged feathered lower edge
    pre_pts = [(46, 62), (94, 62), (100, 112)]
    ragged = []
    for k in range(9):
        x = 100 - (100 - 40) * k / 8
        ragged.append((x, 112 + (6 if k % 2 else 16)))
    pre = opoly_s([(46, 62), (94, 62)] + ragged, "#5c3f2e")
    p = []
    # antler / horn headdress rising from the head
    for sx in (1, -1):
        p.append(rib([(70 + sx * 6, 40), (70 + sx * 16, 26), (70 + sx * 12, 12)], 1.6, "#e6ddc8"))
        p.append(rib([(70 + sx * 13, 22), (70 + sx * 24, 18)], 1.2, "#e6ddc8"))
        p.append(rib([(70 + sx * 10, 16), (70 + sx * 18, 6)], 1.1, "#e6ddc8"))
    p.append(bar(58, 40, 82, 40, 2.0, "#e6ddc8"))
    # face paint - two vertical marks
    p.append(bar(65, 44, 65, 54, 1.4, "#7ce0c4"))
    p.append(bar(75, 44, 75, 54, 1.4, "#c98a3c"))
    # bone-bead necklace strands
    for r, col in ((10, "#e6ddc8"), (16, "#c98a3c")):
        for k in range(9):
            a = math.pi * (0.15 + 0.7 * k / 8)
            p.append(circ(70 + r * math.cos(a), 66 + r * math.sin(a) + 4, 1.4, col))
    # carried staff with a bound bundle + feathers, held at the right side
    p.append(opoly_s([(99, 58), (103, 58), (103, 156), (99, 156)], "#2e1f14"))
    p.append(opoly_s(rrect(95, 50, 12, 14, 1), "#5c3f2e"))
    p.append(bar(95, 54, 107, 54, 1.2, "#c98a3c"))
    p.append(bar(95, 60, 107, 60, 1.2, "#c98a3c"))
    for fx, fy in ((92, 44), (101, 38), (110, 44)):
        p.append(rib([(101, 52), (fx, fy), (fx + (fx - 101) * 0.6, fy - 10)], 1.4, "#e6ddc8"))
        p.append(circ(fx + (fx - 101) * 0.6, fy - 10, 1.2, "#7ce0c4"))
    # spirit-glow motes around the figure
    for gx, gy in ((44, 96), (108, 120), (52, 138), (96, 78)):
        p.append(circ(gx, gy, 1.6, "#7ce0c4"))
    return base, pre, "".join(p)


def salt_crows():
    base = dict(suit="#7a3b2c", boot="#3a2018", sleeve="#5a2c20", belt="#2c1a12")
    p = []
    # tied headwrap (bandana) instead of a helmet + trailing tail
    p.append(opoly_s([(55, 44), (85, 42), (86, 52), (54, 54)], "#c98a3c"))
    p.append(rib([(85, 48), (94, 52), (98, 62)], 1.6, "#c98a3c"))
    p.append(circ(63, 49, 1.0, "#2c1a12"))
    p.append(circ(73, 49, 1.0, "#2c1a12"))
    # salvaged monocle-visor over one eye
    p.append(ocirc(75.5, 49, 3.2, "#ffd24a", d=1.0))
    p.append(bar(78, 48, 88, 44, 0.8, "#3a2018"))
    # mismatched scavenged plate - a green Vherathi-ish shoulder curve + a
    # riveted Drossholt-ish chest patch
    p.append(rib([(44, 68), (40, 80), (46, 92)], 3.0, "#3f6f5a"))
    p.append(opoly_s([(58, 82), (82, 78), (84, 104), (60, 108)], "#8a6845"))
    for dx, dy in ((-8, -8), (8, -8), (8, 8), (-8, 8)):
        p.append(circ(71 + dx, 93 + dy, 1.2, "#3a2018"))
    # hook-hand on the right arm
    p.append(bar(94, 118, 94, 128, 1.4, "#b8b0a0"))
    p.append(rib([(94, 128), (99, 132), (98, 138), (92, 137)], 1.6, "#b8b0a0"))
    # bandolier sash of tools across the chest
    p.append(poly([(52, 66), (60, 66), (92, 128), (84, 128)], "#2c1a12"))
    for t in (0.25, 0.5, 0.75):
        tx = 56 + (88 - 56) * t
        ty = 66 + (128 - 66) * t
        p.append(opoly_s(rrect(tx - 2, ty - 4, 4, 8, 1), "#b8b0a0"))
    # trophy trinkets at the belt
    for x in (60, 66, 80):
        p.append(bar(x, 150, x, 156, 0.7, "#c98a3c"))
        p.append(circ(x, 158, 1.6, "#e8e2d4"))
    # the salt-crow bird mark stencilled on the chest
    p.append(poly([(66, 116), (74, 113), (80, 118), (75, 119), (78, 125),
                   (72, 120), (67, 125), (69, 118), (63, 118)], "#e8e2d4"))
    return base, "", "".join(p)


OUTFITS = {
 "deeprock": (deeprock, "Pit Foreman"),
 "kessari": (kessari, "Ashfall Adept"),
 "meridian": (meridian, "Free-Port Factor"),
 "theln": (theln, "Drift Rigger"),
 "kaethar": (kaethar, "Line Officer"),
 "vetl": (vetl, "Bone-Speaker"),
 "salt_crows": (salt_crows, "Deck Hand"),
 "vherathi": (vherathi, "Reef-Diver"),
 "drossholt": (drossholt, "Rust-Hand"),
 "federation": (federation, "Issue Rating"),
}
