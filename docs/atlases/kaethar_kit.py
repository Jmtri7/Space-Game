"""Kaethar Directorate - full frontier atlas content. Hard angles, gunmetal,
one warning colour (red). Every specimen strokeless. See culture_common.py.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, rrect, opoly, ocirc, bar
from culture_common import (grid_bg, ribbon, opoly_s, dot_run, chevrons, groove,
                            flame, stencil, label, OUT)

# ---- palette handles are passed in as P = {hull,hull_lo,glass,thrust,trim,shadow}
RED = "#d6402c"


def _arrowhull(P, cx, w_nose, w_mid, y0, y1, ymid):
    H, S = P["hull"], P["shadow"]
    return [(cx, y0), (cx + w_nose, ymid - 18), (cx + w_mid, ymid),
            (cx + w_mid - 4, y1), (cx - w_mid + 4, y1),
            (cx - w_mid, ymid), (cx - w_nose, ymid - 18)]


def _seams(P, x, y, w, rows):
    return "".join(groove(x, y + i * 26, w, 5, P["shadow"]) for i in range(rows))


def _sigil(cx, cy, r, col, back):
    return (poly([(cx, cy - r), (cx + r * 0.8, cy), (cx, cy + r), (cx - r * 0.8, cy)], col)
            + poly([(cx, cy - r * 0.5), (cx + r * 0.4, cy), (cx, cy + r * 0.5),
                    (cx - r * 0.4, cy)], back)
            + bar(cx - r * 1.3, cy, cx + r * 1.3, cy, 1.2, col))


# ================================================================ SHIPS
def picket(P):
    """Small fast interceptor - the arrowhead at its purest."""
    H, L, G, T, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["shadow"]
    o = [grid_bg()]
    for hx in (114, 126):
        o.append(flame(hx, 168, 2.4, 15, T))
    o.append(opoly(rrect(104, 150, 32, 20, 1), L, d=1.3))
    hull = [(120, 26), (140, 92), (138, 140), (128, 152), (112, 152), (102, 140), (100, 92)]
    o.append(opoly(hull, H, d=1.6, ol=S))
    o.append(_seams(P, 106, 74, 28, 2))
    o.append(bar(120, 30, 120, 150, 1.0, S))
    # forward-swept stub wings + red chevron
    for sx in (1, -1):
        wing = [(120 + sx * 16, 104), (120 + sx * 58, 78), (120 + sx * 62, 92),
                (120 + sx * 24, 122)]
        o.append(opoly(wing, H, d=1.3, ol=S))
        o.append(chevrons(120 + sx * 20, 120 + sx * 54, 84, 2.6, 3, RED, n=2, down=False))
    # spinal rail + muzzle
    o.append(opoly(rrect(117, 28, 6, 118, 1), L, d=0.9))
    o.append(poly([(117, 30), (123, 30), (121, 18), (119, 18)], S))
    o.append(circ(120, 18, 1.6, RED))
    o.append(_sigil(120, 60, 5, RED, "#333849"))
    o.append(circ(120, 100, 3, G))
    return "".join(o)


def line_cruiser(P):
    from frontier_ships import kaethar
    return kaethar(P)


def siege_carrier(P):
    """Heavy - a broad blocky wedge with a hangar mouth and a battery spine."""
    H, L, G, T, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["shadow"]
    o = [grid_bg()]
    for hx in (98, 112, 128, 142):
        o.append(flame(hx, 178, 2.8, 16, T))
    o.append(opoly(rrect(86, 156, 68, 24, 1), L, d=1.5))
    # wide wedge hull
    hull = [(120, 22), (160, 90), (164, 150), (156, 176), (84, 176), (76, 150), (80, 90)]
    o.append(opoly(hull, H, d=1.8, ol=S))
    o.append(_seams(P, 88, 70, 64, 3))
    # central hangar mouth
    o.append(opoly(rrect(104, 120, 32, 44, 1), "#0e1116", d=1.2))
    o.append(bar(104, 142, 136, 142, 1.4, RED))
    for gx in (110, 120, 130):
        o.append(bar(gx, 122, gx, 162, 0.8, S))
    # forward-swept flight decks
    for sx in (1, -1):
        deck = [(120 + sx * 30, 92), (120 + sx * 96, 58), (120 + sx * 104, 80),
                (120 + sx * 40, 128), (120 + sx * 30, 122)]
        o.append(opoly(deck, H, d=1.5, ol=S))
        o.append(chevrons(120 + sx * 36, 120 + sx * 92, 62, 3.4, 3.6, RED, n=3, down=False))
        o.append(opoly(rrect(120 + sx * 82 - 7, 58, 14, 18, 1), L, d=1.1))
    # spinal battery rail w/ three muzzles
    o.append(opoly(rrect(115, 24, 10, 132, 1), L, d=1.0))
    o.append(poly([(112, 28), (128, 28), (124, 12), (116, 12)], S))
    o.append(circ(120, 13, 2, RED))
    # shoulder turrets
    for sx in (1, -1):
        o.append(opoly(rrect(120 + sx * 44 - 9, 86, 18, 20, 1), L, d=1.2))
        o.append(bar(120 + sx * 44, 88, 120 + sx * 44, 66, 1.8, S))
    o.append(_sigil(120, 66, 7, RED, "#333849"))
    return "".join(o)


SHIPS = {
    "picket": (picket, "Kaethar Picket", "interceptor - lane patrol"),
    "line_cruiser": (line_cruiser, "Kaethar Spearhead", "line cruiser - the standard hull"),
    "siege_carrier": (siege_carrier, "Kaethar Bastion", "siege carrier - forward flight decks"),
}


# ================================================================ STATION
def station(P):
    H, L, G, T, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["shadow"]
    cx = cy = 120.0
    o = [grid_bg()]
    # square core
    o.append(opoly(rrect(cx - 34, cy - 34, 68, 68, 1), H, d=1.8, ol=S))
    o.append(opoly(rrect(cx - 22, cy - 22, 44, 44, 1), L, d=1.2))
    for gy in (cx - 24, cx, cx + 22):
        o.append(groove(cx - 30, gy - 2, 60, 4, S))
    # four forward-swept docking spurs (rotational, but each "leans" clockwise)
    for k in range(4):
        a = math.pi / 2 * k
        ca, sa = math.cos(a), math.sin(a)
        # spur base at core edge, tip pushed out and rotated a touch
        bx, by = cx + 30 * ca, cy + 30 * sa
        tx, ty = cx + 78 * ca - 20 * sa, cy + 78 * sa + 20 * ca
        px, py = -sa, ca
        spur = [(bx + px * 12, by + py * 12), (tx + px * 8, ty + py * 8),
                (tx - px * 8, ty - py * 8), (bx - px * 12, by - py * 12)]
        o.append(opoly(spur, H, d=1.4, ol=S))
        o.append(ribbon([(bx + px * 12, by + py * 12), (tx + px * 8, ty + py * 8)], 1.0, RED))
        o.append(opoly(rrect(tx - 6, ty - 6, 12, 12, 1), L, d=1.0))
        o.append(circ(tx, ty, 2.2, G))
    # comms mast off the top, forward-swept
    o.append(opoly(rrect(cx - 4, cy - 74, 8, 40, 1), L, d=1.0))
    o.append(poly([(cx - 4, cy - 70), (cx + 4, cy - 70), (cx + 10, cy - 92)], S))
    o.append(circ(cx + 8, cy - 90, 1.8, RED))
    o.append(_sigil(cx, cy, 8, RED, L))
    return "".join(o)


STATION = {"station": (station, "Kaethar Redoubt", "cross-plan fortress ring")}


# ================================================================ BUILDINGS
def _blockhouse(P, w, h, label_txt):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    cx = 100.0
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(cx - w / 2, 170 - h, w, h, 1), H, d=1.8, ol=S))
    o.append(opoly(rrect(cx - w / 2 + 6, 170 - h + 6, w - 12, h - 12, 1), L, d=1.0))
    for i in range(int(h / 22)):
        o.append(groove(cx - w / 2 + 4, 170 - h + 14 + i * 22, w - 8, 4, S))
    # doorway + red chevron
    o.append(opoly(rrect(cx - 9, 150, 18, 20, 1), "#0e1116", d=1.0))
    o.append(chevrons(cx - 12, cx + 12, 148, 3, 3, RED, n=2, down=False))
    o.append(_sigil(cx, 170 - h + 12, 5, RED, L))
    o.append(stencil(cx, 186, label_txt, "#8a8f98", 6))
    return "".join(o)


def bunker(P):
    return _blockhouse(P, 120, 90, "GARRISON")


def watch_post(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    # tall narrow tower, forward-swept top
    o.append(opoly([(80, 168), (120, 168), (120, 60), (128, 40), (96, 40), (80, 66)], H, d=1.8, ol=S))
    o.append(opoly(rrect(88, 72, 24, 88, 1), L, d=1.0))
    for i in range(3):
        o.append(groove(86, 84 + i * 24, 28, 4, S))
    o.append(opoly(rrect(92, 40, 32, 16, 1), L, d=1.1))
    o.append(bar(94, 44, 122, 44, 1.4, RED))
    o.append(circ(120, 34, 2, RED))
    o.append(chevrons(88, 112, 166, 3, 3, RED, n=3, down=True))
    o.append(stencil(100, 186, "WATCH", "#8a8f98", 6))
    return "".join(o)


def armoury(P):
    return _blockhouse(P, 150, 70, "ARMOURY")


BUILDINGS = {
    "bunker": (bunker, "Garrison Block", "hab / command"),
    "watch_post": (watch_post, "Watch Post", "lane sensor tower"),
    "armoury": (armoury, "Armoury", "depot"),
}


# ================================================================ FURNITURE
def bench(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(58, 96, 84, 12, 1), L, d=1.4))
    for x in (66, 134):
        o.append(opoly(rrect(x - 4, 108, 8, 22, 1), S, d=1.0))
    o.append(bar(60, 98, 140, 98, 1.2, S))
    return "".join(o)


def muster_post(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(94, 60, 12, 80, 1), L, d=1.3))
    o.append(opoly(rrect(84, 54, 32, 12, 1), H, d=1.2))
    o.append(bar(86, 60, 114, 60, 1.4, RED))
    o.append(_sigil(100, 92, 6, RED, L))
    o.append(circ(100, 140, 3, "#0e1116"))
    return "".join(o)


def rack(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(60, 60, 80, 84, 1), H, d=1.5))
    for i in range(3):
        o.append(groove(64, 70 + i * 24, 72, 6, "#0e1116"))
        for k in range(4):
            o.append(bar(72 + k * 18, 70 + i * 24, 72 + k * 18, 76 + i * 24, 1.2, L))
    o.append(bar(60, 60, 140, 60, 1.0, RED))
    return "".join(o)


def floor_sigil(P):
    L = P["hull_lo"]
    o = [grid_bg(200, 200)]
    o.append(circ(100, 100, 34, "#0e1116"))
    o.append(_sigil(100, 100, 20, RED, L))
    o.append(dot_run(72, 100, 128, 100, 2, 2, RED))
    return "".join(o)


FURNITURE = {
    "bench": (bench, "Issue Bench", "seating"),
    "muster_post": (muster_post, "Muster Post", "roster marker"),
    "rack": (rack, "Kit Rack", "wall unit"),
    "floor_sigil": (floor_sigil, "Sigil Marker", "floor decal"),
}


# ================================================================ OUTFITS
def _base_helm(crest=True):
    """the shared angular red-barred helm, drawn as post geometry."""
    o = [opoly_s([(55, 56), (56, 40), (70, 32), (84, 40), (85, 56), (78, 62), (62, 62)], "#3a4053")]
    if crest:
        o.append(poly([(66, 34), (74, 34), (72, 22), (68, 22)], "#3a4053"))
    o.append(bar(56, 47, 84, 47, 2.0, RED))
    return "".join(o)


def line_crew():
    base = dict(suit="#2b3040", boot="#171b26", leg="#20242f", sleeve="#2b3040",
                belt="#12151d", chest="#333849")
    p = [_base_helm(crest=False)]
    p.append(opoly_s([(58, 62), (82, 62), (80, 70), (60, 70)], "#3a4053"))  # gorget
    cx, cy = 70, 92
    p.append(poly([(cx, cy - 6), (cx + 5, cy), (cx, cy + 6), (cx - 5, cy)], RED))
    return base, "", "".join(p)


def line_officer():
    from frontier_outfits import kaethar
    return kaethar()


def gate_warden():
    base = dict(coat=True, torso_long=True, suit="#2b3040", boot="#171b26",
                leg="#20242f", sleeve="#2b3040", belt="#12151d")
    pre = opoly_s([(52, 112), (88, 112), (94, 172), (46, 172)], "#242938")
    p = [_base_helm(True)]
    p.append(opoly_s([(58, 62), (82, 62), (80, 70), (60, 70)], "#3a4053"))
    for x in (45, 95):
        p.append(opoly_s(rrect(x - 8, 68, 16, 10, 1), "#3a4053"))
        p.append(bar(x - 6, 73, x + 6, 73, 1.1, "#12151d"))
    p.append(opoly_s([(56, 76), (84, 76), (81, 110), (59, 112)], "#333849"))
    cx, cy = 70, 92
    p.append(poly([(cx, cy - 7), (cx + 6, cy), (cx, cy + 7), (cx - 6, cy)], RED))
    p.append(poly([(cx, cy - 3.5), (cx + 3, cy), (cx, cy + 3.5), (cx - 3, cy)], "#333849"))
    for k in range(2):
        p.append(bar(42, 96 + k * 5, 50, 96 + k * 5, 1.4, "#c9a24a"))
    # halberd
    p.append(opoly_s([(98, 40), (102, 40), (102, 150), (98, 150)], "#20242f"))
    p.append(poly([(96, 42), (110, 30), (108, 46), (100, 52)], "#b8bcc4"))
    return base, pre, "".join(p)


def high_command():
    base = dict(coat=True, torso_long=True, suit="#20242f", boot="#12151d",
                leg="#191d27", sleeve="#20242f", belt="#0d0f15", collar="#c9a24a")
    pre = opoly_s([(48, 110), (92, 110), (100, 180), (40, 180)], "#1a1e28")
    p = [_base_helm(True)]
    # laurel-less: heavier crest + double bar
    p.append(poly([(64, 30), (76, 30), (72, 16), (68, 16)], "#3a4053"))
    p.append(bar(56, 43, 84, 43, 1.4, "#c9a24a"))
    p.append(opoly_s([(56, 62), (84, 62), (82, 72), (58, 72)], "#c9a24a"))  # gold gorget
    for x in (44, 96):
        p.append(opoly_s(rrect(x - 10, 66, 20, 12, 1), "#3a4053"))
        p.append(dot_run(x - 7, 72, x + 7, 72, 3, 1.1, "#c9a24a"))
    p.append(opoly_s([(55, 76), (85, 76), (82, 112), (58, 114)], "#2b3040"))
    cx, cy = 70, 92
    p.append(poly([(cx, cy - 9), (cx + 7, cy), (cx, cy + 9), (cx - 7, cy)], RED))
    p.append(poly([(cx, cy - 4.5), (cx + 3.5, cy), (cx, cy + 4.5), (cx - 3.5, cy)], "#2b3040"))
    p.append(bar(cx - 12, cy, cx + 12, cy, 1.3, "#c9a24a"))
    for k in range(4):
        p.append(bar(41, 92 + k * 5, 51, 92 + k * 5, 1.5, "#c9a24a"))
    return base, pre, "".join(p)


OUTFITS = {
    "line_crew": (line_crew, "Line Crew", "rating"),
    "line_officer": (line_officer, "Line Officer", "watch officer"),
    "gate_warden": (gate_warden, "Gate Warden", "checkpoint / boarding"),
    "high_command": (high_command, "Directorate Command", "flag rank"),
}


# ================================================================ LAYOUTS
def station_plan(P):
    L, S = P["hull_lo"], P["shadow"]
    room = "#3b4150"
    o = [grid_bg(320, 200)]
    # straight spine, identical cells
    o.append(poly(rrect(30, 92, 260, 26, 2), room))
    for rx in (52, 112, 172, 232):
        o.append(poly(rrect(rx, 34, 44, 46, 2), room))
        o.append(poly(rrect(rx, 120, 44, 46, 2), room))
    o.append(bar(34, 105, 286, 105, 1.4, RED))            # the painted line
    for x in (74, 134, 194, 254):
        o.append(poly([(x - 3, 80), (x + 2, 80), (x, 74)], RED))
        o.append(poly([(x - 3, 120), (x + 2, 120), (x, 126)], RED))
    o.append(circ(300, 105, 4.5, P["glass"]))
    o.append(bar(292, 105, 300, 105, 1.2, P["glass"]))
    o.append(label([(74, 26, "CELL"), (134, 26, "CELL"), (194, 26, "ARMS"), (254, 26, "MED"),
                    (74, 190, "CELL"), (134, 190, "MESS"), (194, 190, "CELL"), (254, 190, "CELL"),
                    (160, 109, "MUSTER SPINE")]))
    return "".join(o)


def city_plan(P):
    S = P["shadow"]
    room = "#3b4150"
    o = [grid_bg(320, 200)]
    o.append(poly(rrect(40, 40, 240, 120, 2), room))
    for rx in (58, 138, 218):
        o.append(poly([(rx, 40), (rx, 160)], S) if False else groove(rx, 40, 3, 120, S))
    o.append(bar(48, 100, 272, 100, 1.4, RED))
    for x in (100, 160, 220):
        o.append(poly([(x - 3, 96), (x + 2, 96), (x, 90)], RED))
    o.append(_sigil_layout(160, 100, P))
    o.append(circ(292, 100, 4.5, P["glass"]))
    o.append(bar(284, 100, 292, 100, 1.2, P["glass"]))
    o.append(label([(78, 30, "BARRACKS"), (178, 30, "PARADE"), (250, 30, "STORES"),
                    (160, 172, "GARRISON ROW")]))
    return "".join(o)


def _sigil_layout(cx, cy, P):
    return (poly([(cx, cy - 10), (cx + 8, cy), (cx, cy + 10), (cx - 8, cy)], RED)
            + poly([(cx, cy - 5), (cx + 4, cy), (cx, cy + 5), (cx - 4, cy)], "#3b4150"))


LAYOUTS = {
    "station_plan": (station_plan, "Redoubt interior", "station floor plan"),
    "city_plan": (city_plan, "Garrison settlement", "moon city plan"),
}
