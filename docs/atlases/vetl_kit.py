"""The Vetl - full frontier atlas content. Creature silhouettes, bone/hide,
spirit-teal light. Strokeless. See culture_common.py.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, opoly, ocirc, bar, ngon
from culture_common import grid_bg, ribbon, opoly_s, dot_run, flame, stencil, label, OUT

TEAL = "#7ce0c4"
BONE = "#e6ddc8"


def _motes(pts, col=TEAL, r=1.7):
    """Scattered spirit-motes. Just the beads - a connecting polyline turns to
    a teal scribble at sprite scale (same lesson as the Vherathi veins)."""
    o = []
    for i, (x, y) in enumerate(pts):
        o.append(circ(x, y, r + (1.3 if i == 0 else 0), col))
        if i == 0:
            o.append(circ(x, y, r + 3.4, col, op=0.22))
    return "".join(o)


def _hide_patches(spec, S):
    return "".join(circ(x, y, r, S, op=0.45) for x, y, r in spec)


# ================================================================ SHIPS
def scout(P):
    H, L, G, T, B, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    o.append(circ(120, 158, 5, T, op=0.20))
    o.append(circ(120, 154, 3, T, op=0.5))
    o.append(ribbon([(120, 138), (120, 168), (120, 190)], 2.2, H))
    o.append(poly([(116, 186), (124, 186), (120, 198)], B))
    body = ngon(120, 96, 40, 34, 26)
    o.append(opoly(body, H, d=1.6, ol=S))
    o.append(_hide_patches([(104, 84, 7), (136, 96, 8), (118, 116, 6)], S))
    o.append(bar(120, 64, 120, 138, 1.4, B))
    for sx in (1, -1):
        for k in range(4):
            sy = 74 + k * 14
            o.append(ribbon([(120, sy), (120 + sx * 18, sy + 2), (120 + sx * 34, sy - 3)], 0.8, B))
        o.append(ribbon([(120 + sx * 14, 62), (120 + sx * 28, 42), (120 + sx * 24, 24), (120 + sx * 12, 14)], 2.6, H))
        o.append(circ(120 + sx * 12, 14, 1.8, B))
    o.append(_motes([(112, 80), (128, 90), (120, 104), (108, 100)]))
    for sx in (1, -1):
        o.append(ocirc(120 + sx * 11, 74, 3.6, L, d=1.1))
        o.append(circ(120 + sx * 11, 74, 1.8, "#0e0c10"))
    return "".join(o)


def mantle(P):
    from frontier_ships import vetl
    return vetl(P)


def gather_ship(P):
    """Broad slow gather-ship - a very wide lens, short prongs, twin tails."""
    H, L, G, T, B, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    for tx in (108, 132):
        o.append(circ(tx, 176, 6, T, op=0.18))
        o.append(ribbon([(tx, 150), (tx + (tx - 120) * 0.3, 172), (tx, 196)], 2.4, H))
        o.append(poly([(tx - 4, 192), (tx + 4, 192), (tx, 204)], B))
    body = ngon(120, 100, 78, 44, 34)
    o.append(opoly(body, H, d=2.0, ol=S))
    o.append(_hide_patches([(80, 84, 12), (160, 96, 13), (110, 128, 10),
                            (150, 128, 9), (96, 112, 8)], S))
    o.append(bar(120, 56, 120, 150, 2.0, B))
    for sx in (1, -1):
        for k in range(6):
            sy = 66 + k * 15
            o.append(ribbon([(120, sy), (120 + sx * 34, sy + 3), (120 + sx * 64, sy - 5 + k)], 0.9, B))
        o.append(ribbon([(120 + sx * 22, 64), (120 + sx * 34, 44), (120 + sx * 30, 26)], 2.6, H))
        o.append(circ(120 + sx * 30, 26, 2, B))
    for k in range(8):
        sy = 62 + k * 12
        o.append(poly([(117, sy), (123, sy), (120, sy - 6)], B))
    o.append(_motes([(100, 78), (128, 74), (140, 96), (118, 108), (98, 118), (134, 122)]))
    for sx in (1, -1):
        o.append(ocirc(120 + sx * 16, 80, 5.5, L, d=1.3))
        o.append(circ(120 + sx * 16, 80, 2.6, "#0e0c10"))
        o.append(circ(120 + sx * 15, 79, 1, G))
    return "".join(o)


SHIPS = {
    "scout": (scout, "Vetl Drift-Eye", "scout - small manta"),
    "mantle": (mantle, "Vetl Mantle", "the standard creature-ship"),
    "gather_ship": (gather_ship, "Vetl Broadwing", "gather-ship - twin tail"),
}


# ================================================================ STATION
def station(P):
    H, L, G, T, B, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    cx = cy = 120.0
    o = [grid_bg()]
    o.append(opoly(ngon(cx, cy, 46, 42, 24), H, d=2.0, ol=S))
    # overlapping grown plates
    for a in range(0, 360, 45):
        rad = math.radians(a)
        px, py = cx + 30 * math.cos(rad), cy + 28 * math.sin(rad)
        o.append(circ(px, py, 11, L, op=0.6))
    o.append(circ(cx, cy, 20, "#0e0c10"))
    # three soft berthing lobes
    for a in (90, 210, 330):
        rad = math.radians(a)
        lx, ly = cx + 52 * math.cos(rad), cy + 50 * math.sin(rad)
        o.append(opoly(ngon(lx, ly, 14, 12, 16), L, d=1.4, ol=S))
        o.append(circ(lx, ly, 4, G))
    # bone rib arch over the top ("mouth")
    o.append(ribbon([(cx - 34, cy - 30), (cx, cy - 52), (cx + 34, cy - 30)], 2.2, B))
    o.append(_motes([(cx - 20, cy - 10), (cx + 4, cy - 24), (cx + 22, cy - 6),
                     (cx - 6, cy + 18), (cx + 16, cy + 20)]))
    return "".join(o)


STATION = {"station": (station, "Vetl Reef-Node", "grown shell station")}


# ================================================================ BUILDINGS
def _mound(P, w, h, label_txt, motes):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    cx = 100.0
    o = [grid_bg(200, 200)]
    o.append(opoly(ngon(cx, 150 - h * 0.3, w / 2, h / 2, 20), H, d=1.8, ol=S))
    for dx, dy, r in ((-w * 0.2, -h * 0.15, w * 0.16), (w * 0.22, h * 0.05, w * 0.14),
                      (0, h * 0.2, w * 0.12)):
        o.append(circ(cx + dx, 150 - h * 0.3 + dy, r, L, op=0.5))
    # woven-frame doorway
    o.append(opoly(ngon(cx, 158, 11, 15, 12), "#0e0c10", d=1.0))
    for k in range(3):
        o.append(bar(cx - 9, 150 + k * 5, cx + 9, 150 + k * 5, 0.8, "#5c4636"))
    # bone rib arch
    o.append(ribbon([(cx - w * 0.4, 150 - h * 0.1), (cx, 150 - h * 0.6),
                     (cx + w * 0.4, 150 - h * 0.1)], 1.8, BONE))
    o.append(_motes(motes))
    o.append(stencil(cx, 186, label_txt, "#8a7a5c", 6))
    return "".join(o)


def lodge(P):
    return _mound(P, 120, 96, "LODGE", [(70, 110), (92, 96), (118, 108), (130, 128)])


def spirit_house(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(ngon(100, 116, 34, 44, 18), H, d=1.8, ol=S))
    o.append(circ(94, 100, 12, L, op=0.5))
    o.append(circ(112, 122, 10, L, op=0.5))
    o.append(opoly(ngon(100, 150, 10, 14, 12), "#0e0c10", d=1.0))
    o.append(ribbon([(76, 96), (100, 60), (124, 96)], 2.0, BONE))
    o.append(circ(100, 58, 3, TEAL))
    o.append(_motes([(84, 92), (100, 78), (116, 92), (92, 112), (108, 116)]))
    o.append(stencil(100, 186, "SPIRIT HOUSE", "#8a7a5c", 6))
    return "".join(o)


def drying_rack(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    for x in (64, 136):
        o.append(bar(x, 68, x, 150, 2.0, "#5c4636"))
    for y in (78, 96, 114):
        o.append(bar(64, y, 136, y, 1.4, "#5c4636"))
        for k in range(4):
            hx = 74 + k * 18
            o.append(poly([(hx - 5, y), (hx + 5, y), (hx + 3, y + 14), (hx - 3, y + 14)], "#7a5a44", op=0.85))
    o.append(_motes([(84, 130), (116, 134)]))
    o.append(stencil(100, 186, "HIDE RACK", "#8a7a5c", 6))
    return "".join(o)


BUILDINGS = {
    "lodge": (lodge, "Reef Lodge", "hab mound"),
    "spirit_house": (spirit_house, "Spirit House", "shrine"),
    "drying_rack": (drying_rack, "Hide Rack", "workyard"),
}


# ================================================================ FURNITURE
def hide_mat(P):
    S = P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(ngon(100, 104, 40, 26, 14), "#6a4a34", d=1.4))
    o.append(circ(88, 98, 9, S, op=0.4))
    o.append(circ(112, 110, 8, S, op=0.4))
    for k in range(6):
        a = math.pi * (0.15 + 0.7 * k / 5)
        o.append(poly([(100 + 40 * math.cos(a) - 3, 104 + 26 * math.sin(a)),
                       (100 + 40 * math.cos(a) + 3, 104 + 26 * math.sin(a)),
                       (100 + 46 * math.cos(a), 104 + 30 * math.sin(a))], BONE))
    return "".join(o)


def staff_rack(P):
    o = [grid_bg(200, 200)]
    o.append(opoly_s([(70, 138), (130, 138), (126, 148), (74, 148)], "#5c4636"))
    for k, lean in enumerate((-6, -2, 2, 6)):
        bx = 80 + k * 13
        o.append(bar(bx, 138, bx + lean, 66, 1.6, "#4a3626"))
        o.append(opoly(ngon(bx + lean, 60, 4, 6, 8), "#6a4a34", d=1.0))
        for fx in (-4, 0, 4):
            o.append(ribbon([(bx + lean, 58), (bx + lean + fx, 48), (bx + lean + fx * 1.6, 38)], 1.0, BONE))
        o.append(circ(bx + lean, 56, 1.4, TEAL))
    return "".join(o)


def bead_curtain(P):
    o = [grid_bg(200, 200)]
    o.append(bar(58, 58, 142, 58, 2.0, "#5c4636"))
    for k in range(9):
        cx = 64 + k * 9.5
        for j in range(7):
            col = BONE if (k + j) % 2 else "#c98a3c"
            o.append(circ(cx, 66 + j * 12, 2.0, col))
        o.append(circ(cx, 66 + 7 * 12, 1.6, TEAL))
    return "".join(o)


def spirit_bowl(P):
    S = P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(ngon(100, 120, 22, 12, 16), "#4a3626", d=1.4))
    o.append(poly([(80, 116), (120, 116), (114, 128), (86, 128)], "#3a2a1e"))
    o.append(circ(100, 118, 8, TEAL, op=0.35))
    for fx, fy in ((94, 104), (100, 98), (106, 104)):
        o.append(ribbon([(100, 116), (fx, fy), (fx + (fx - 100) * 0.8, fy - 10)], 1.4, TEAL))
    o.append(_motes([(88, 96), (112, 92), (100, 82)]))
    return "".join(o)


FURNITURE = {
    "hide_mat": (hide_mat, "Hide Mat", "seating"),
    "staff_rack": (staff_rack, "Staff Rack", "wall unit"),
    "bead_curtain": (bead_curtain, "Bead Curtain", "doorway"),
    "spirit_bowl": (spirit_bowl, "Spirit Bowl", "shrine fire"),
}


# ================================================================ OUTFITS
def _antlers(spread, tall_):
    o = []
    for sx in (1, -1):
        o.append(ribbon([(70 + sx * 6, 40), (70 + sx * (10 + spread), 26),
                         (70 + sx * (6 + spread), 12 - tall_)], 1.6, BONE))
        o.append(ribbon([(70 + sx * (8 + spread * 0.6), 22), (70 + sx * (18 + spread), 18)], 1.2, BONE))
        o.append(ribbon([(70 + sx * (6 + spread * 0.4), 16), (70 + sx * (12 + spread), 6 - tall_)], 1.1, BONE))
    o.append(bar(58, 40, 82, 40, 2.0, BONE))
    return "".join(o)


def _facepaint():
    return bar(65, 44, 65, 54, 1.4, TEAL) + bar(75, 44, 75, 54, 1.4, "#c98a3c")


def _beads(strands):
    o = []
    for si in range(strands):
        r = 9 + si * 5
        col = BONE if si % 2 == 0 else "#c98a3c"
        for k in range(9):
            a = math.pi * (0.15 + 0.7 * k / 8)
            o.append(circ(70 + r * math.cos(a), 70 + r * math.sin(a), 1.3, col))
    return "".join(o)


def _spirit_motes(pts):
    return "".join(circ(x, y, 1.6, TEAL) for x, y in pts)


def scout_o():
    base = dict(no_helmet=True, suit="#6b4a35", boot="#3a2718", leg="#4a3122", sleeve="#5c3f2e")
    p = [_antlers(6, 0), _facepaint(), _beads(1),
         _spirit_motes([(44, 96), (108, 120)])]
    return base, "", "".join(p)


def bone_speaker():
    from frontier_outfits import vetl
    return vetl()


def hearth_keeper():
    base = dict(no_helmet=True, torso_long=True, suit="#5c4030", boot="#2e1f14",
                leg="#3f2b1e", sleeve="#4e3626", sash="#c98a3c")
    pre = opoly_s([(46, 62), (94, 62), (100, 118),
                   (92, 120), (80, 112), (68, 122), (56, 112), (44, 120)], "#4e3626")
    p = [_antlers(9, 2), _facepaint(), _beads(2)]
    # a hide apron with a woven band
    p.append(opoly_s([(56, 92), (84, 92), (82, 128), (58, 128)], "#6a4a34"))
    p.append(bar(56, 104, 84, 104, 1.4, TEAL))
    p.append(_spirit_motes([(42, 100), (100, 116), (52, 140), (96, 84)]))
    return base, pre, "".join(p)


def deep_elder():
    base = dict(no_helmet=True, torso_long=True, suit="#4a3222", boot="#241810",
                leg="#33241a", sleeve="#3e2b1e", sash="#7ce0c4")
    ragged = []
    for k in range(11):
        x = 102 - (102 - 38) * k / 10
        ragged.append((x, 116 + (6 if k % 2 else 20)))
    pre = opoly_s([(44, 58), (96, 58)] + ragged, "#3e2b1e")
    p = [_antlers(14, 4), _facepaint(), _beads(3)]
    p.append(opoly_s([(54, 88), (86, 88), (84, 132), (56, 132)], "#5c3f2e"))
    p.append(bar(54, 100, 86, 100, 1.6, TEAL))
    p.append(bar(54, 112, 86, 112, 1.4, "#c98a3c"))
    # carried staff with a big spirit mote
    p.append(opoly_s([(99, 46), (103, 46), (103, 160), (99, 160)], "#241810"))
    p.append(circ(101, 42, 4, TEAL))
    p.append(circ(101, 42, 7, TEAL, op=0.3))
    for fx, fy in ((94, 40), (101, 32), (110, 40)):
        p.append(ribbon([(101, 46), (fx, fy), (fx + (fx - 101) * 0.6, fy - 10)], 1.4, BONE))
    p.append(_spirit_motes([(40, 92), (110, 110), (46, 140), (100, 74), (120, 96)]))
    return base, pre, "".join(p)


OUTFITS = {
    "scout_o": (scout_o, "Drift Scout", "outrider"),
    "bone_speaker": (bone_speaker, "Bone-Speaker", "shaman"),
    "hearth_keeper": (hearth_keeper, "Hearth-Keeper", "lodge elder"),
    "deep_elder": (deep_elder, "Deep Elder", "spirit voice"),
}


# ================================================================ LAYOUTS
def station_plan(P):
    S = P["shadow"]
    room = "#5a4030"
    o = [grid_bg(320, 200)]
    o.append(circ(160, 100, 80, room))
    for a in (30, 150, 270):
        rad = math.radians(a)
        o.append(circ(160 + 74 * math.cos(rad), 100 + 74 * math.sin(rad), 30, room))
    o.append(circ(160, 100, 22, "#3a2a1e"))
    o.append(dot_run(120, 100, 200, 100, 6, 1.6, TEAL))
    o.append(circ(292, 100, 4.5, TEAL))
    o.append(bar(284, 100, 292, 100, 1.2, TEAL))
    o.append(label([(160, 60, "GATHER RING"), (110, 150, "LODGES"),
                    (210, 150, "SPIRIT"), (160, 190, "REEF-NODE INTERIOR")], "#c9bfae"))
    return "".join(o)


def city_plan(P):
    room = "#5a4030"
    o = [grid_bg(320, 200)]
    for cxk, cyk, rr in ((90, 90, 34), (170, 120, 40), (240, 80, 30), (200, 160, 26)):
        o.append(circ(cxk, cyk, rr, room))
    o.append(ribbon([(60, 120), (150, 100), (240, 130)], 3.0, "#7a5a44"))
    o.append(dot_run(60, 120, 240, 130, 8, 1.4, TEAL))
    o.append(circ(292, 120, 4.5, TEAL))
    o.append(bar(284, 120, 292, 120, 1.2, TEAL))
    o.append(label([(90, 90, "LODGE"), (170, 120, "GATHER"), (240, 78, "SPIRIT"),
                    (160, 186, "DRIFT CAMP")], "#c9bfae"))
    return "".join(o)


LAYOUTS = {
    "station_plan": (station_plan, "Reef-Node interior", "station floor plan"),
    "city_plan": (city_plan, "Drift camp", "moon settlement plan"),
}
