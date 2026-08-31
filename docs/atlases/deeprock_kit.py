"""Deeprock Mining Consortium - full frontier atlas content. Front-heavy hauler,
functional, hazard yellow, rivets. Strokeless. See culture_common.py.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, rrect, opoly, ocirc, bar, ngon
from culture_common import (grid_bg, ribbon, opoly_s, dot_run, chevrons, groove,
                            flame, stencil, label, OUT)

YELLOW = "#d6b03c"


# ================================================================ SHIPS
def prospector(P):
    from frontier_ships import deeprock
    return deeprock(P)


def crusher_hauler(P):
    """The main design - front-heavy with crush jaw."""
    from frontier_ships import deeprock
    return deeprock(P)


def ore_barge(P):
    """Broad slow hauler - like the gnaw but wider, no crusher, side chutes."""
    H, L, G, T, Y, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    # dual engine block
    o.append(flame(100, 178, 3, 20, T))
    o.append(flame(140, 176, 3, 18, T))
    o.append(opoly(rrect(84, 154, 72, 28, 2), L, d=1.6))
    # segmented tank body - very wide
    for i, ty in enumerate((88, 118, 148)):
        o.append(opoly(ngon(120, ty, 50 - i, 36 - i, 20), H, d=1.5))
    for ty in (102, 132):
        o.append(bar(70, ty, 170, ty, 1.4, S))
    # conveyor ridge
    o.append(opoly([(112, 50), (128, 50), (126, 156), (114, 156)], L, d=1.2))
    for ry in range(60, 150, 10):
        o.append(bar(113, ry, 127, ry, 1.0, S))
    # ore chutes on both flanks
    o.append(ribbon([(70, 96), (44, 88), (36, 102)], 5, L))
    o.append(ribbon([(170, 96), (196, 88), (204, 102)], 5, L))
    # hazard chevrons
    o.append(chevrons(84, 156, 152, 4, 4, Y, n=4))
    # quad thrusters
    for hx in (95, 110, 130, 145):
        o.append(opoly(rrect(hx - 4, 152, 8, 24, 1), S, d=1.0))
    return "".join(o)


SHIPS = {
    "prospector": (prospector, "Deeprock Scout", "scout - small hauler"),
    "crusher_hauler": (crusher_hauler, "Deeprock Gnaw", "the standard crusher-hauler"),
    "ore_barge": (ore_barge, "Deeprock Carrier", "broad ore barge"),
}


# ================================================================ STATION
def station(P):
    H, L, G, T, Y, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    cx = cy = 120.0
    o = [grid_bg()]
    # stacked riveted ore-tank drums
    for i, ry in enumerate((60, 100, 140)):
        o.append(opoly(ngon(cx, ry, 36 - i * 4, 28 - i * 2, 24), H, d=1.6, ol=S))
        o.append(bar(cx - 30, ry, cx + 30, ry, 1.2, S))
        for rn in range(7):
            o.append(circ(cx - 26 + rn * 8, ry - 2, 1.1, "#33302b"))
    # central conveyor spine
    o.append(opoly(rrect(cx - 8, 40, 16, 116, 1), L, d=1.0))
    o.append(bar(cx - 8, 50, cx + 8, 50, 1.2, Y))
    # floodlamp masts
    for mx in (cx - 24, cx + 24):
        o.append(bar(mx, 36, mx, 20, 1.6, S))
        o.append(circ(mx, 18, 3.4, G))
    # hazard chevrons + tailings chute
    o.append(chevrons(cx - 32, cx + 32, 50, 3.8, 3.2, Y, n=3))
    o.append(ribbon([(cx + 40, 80), (cx + 60, 100), (cx + 52, 130)], 6, L))
    return "".join(o)


STATION = {"station": (station, "Deeprock Platform", "ore processing station")}


# ================================================================ BUILDINGS
def ore_drum(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(ngon(100, 130, 28, 38, 20), H, d=1.6, ol=S))
    o.append(bar(100, 92, 100, 168, 1.4, S))
    for ry in (110, 130, 150):
        o.append(bar(76, ry, 124, ry, 1.1, S))
        for rn in range(7):
            o.append(circ(78 + rn * 7, ry, 0.9, "#33302b"))
    o.append(stencil(100, 186, "ORE DRUM", "#8a7a68", 6))
    return "".join(o)


def headframe(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    for x in (78, 122):
        o.append(opoly(rrect(x - 4, 90, 8, 74, 1), L, d=1.0))
    o.append(opoly(rrect(72, 88, 56, 10, 1), H, d=1.3))
    o.append(bar(76, 92, 124, 92, 1.2, YELLOW))
    o.append(chevrons(76, 124, 86, 3, 3, YELLOW, n=3, down=False))
    for k in range(4):
        o.append(bar(80 + k * 10, 88, 80 + k * 10, 70, 1.0, S))
    return "".join(o)


def processing_shed(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(54, 88, 92, 84, 2), H, d=1.6, ol=S))
    o.append(opoly(rrect(64, 96, 72, 68, 1), L, d=1.0))
    o.append(groove(72, 110, 14, 20, "#0e1116"))
    o.append(groove(98, 108, 16, 24, "#0e1116"))
    o.append(bar(56, 88, 144, 88, 1.2, YELLOW))
    o.append(chevrons(60, 140, 86, 3.2, 3, YELLOW, n=4, down=False))
    return "".join(o)


BUILDINGS = {
    "ore_drum": (ore_drum, "Ore Drum", "storage"),
    "headframe": (headframe, "Mine Headframe", "elevator tower"),
    "processing_shed": (processing_shed, "Processing Shed", "mill"),
}


# ================================================================ FURNITURE
def pipe_bench(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(56, 96, 88, 14, 1), L, d=1.4))
    for x in (68, 132):
        o.append(opoly(rrect(x - 5, 110, 10, 22, 1), S, d=1.0))
    o.append(bar(60, 98, 140, 98, 1.2, S))
    return "".join(o)


def tool_board(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(54, 80, 92, 92, 2), L, d=1.4))
    for gy in (96, 120, 144):
        o.append(groove(62, gy - 2, 76, 8, "#0e1116"))
    for row_k in range(3):
        for col_k in range(4):
            o.append(circ(74 + col_k * 14, 104 + row_k * 24, 1.8, "#33302b"))
    return "".join(o)


def sample_bin(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly([(70, 120), (130, 120), (126, 166), (74, 166)], H, d=1.5))
    o.append(opoly(rrect(72, 76, 56, 32, 2), H, d=1.3))
    o.append(bar(72, 76, 128, 76, 1.2, YELLOW))
    o.append(chevrons(76, 124, 74, 2.4, 2, YELLOW, n=2, down=False))
    return "".join(o)


FURNITURE = {
    "pipe_bench": (pipe_bench, "Pipe Bench", "seating"),
    "tool_board": (tool_board, "Tool Board", "wall unit"),
    "sample_bin": (sample_bin, "Sample Bin", "storage"),
}


# ================================================================ OUTFITS
def pit_foreman():
    base = dict(hat="#c9b083", suit="#8a7a68", boot="#3a342e", sleeve="#7a6a58",
                chest="#5c524a", rivets="#33302b", belt="#3a342e", buckle=YELLOW,
                band=YELLOW)
    p = []
    # ear defenders on hard hat
    for x in (52, 88):
        p.append(ocirc(x, 50, 4.4, "#4a423b", d=1.1))
        p.append(circ(x, 50, 2.2, YELLOW))
    p.append(bar(52, 44, 88, 44, 1.6, "#4a423b"))
    # shoulder floodlamp
    p.append(opoly_s(rrect(92, 66, 11, 9, 1), "#4a423b"))
    p.append(circ(97, 70, 2.6, "#ffe078"))
    p.append(poly([(97, 70), (120, 58), (120, 84)], "#ffe078", op=0.12))
    # ore-scoop gauntlet
    p.append(opoly_s([(37, 114), (50, 116), (51, 124), (48, 132), (39, 132), (35, 124)], "#5c524a"))
    p.append(bar(38, 119, 49, 120, 1.1, "#33302b"))
    p.append(bar(38, 125, 48, 126, 1.1, "#33302b"))
    p.append(poly([(35, 122), (31, 124), (33, 130), (37, 128)], "#4a423b"))
    return base, "", "".join(p)


def belt_crew():
    base = dict(suit="#6a5a48", boot="#3a2e24", sleeve="#5a4a38", belt="#33291f",
                chest="#4a3a28")
    p = []
    p.append(opoly_s([(56, 44), (84, 44), (82, 58), (58, 58)], "#7a6a58"))
    p.append(bar(56, 48, 84, 48, 1.4, YELLOW))
    for k in range(2):
        p.append(circ(62 + k * 16, 50, 1.2, YELLOW))
    p.append(bar(52, 66, 88, 66, 1.2, "#33302b"))
    return base, "", "".join(p)


def consortium_boss():
    base = dict(suit="#5a4a38", boot="#2a1e14", sleeve="#4a3a28", belt="#1e1410",
                buckle=YELLOW, chest=YELLOW)
    p = []
    p.append(opoly_s([(54, 40), (86, 40), (84, 56), (56, 56)], "#9a8a78"))
    p.append(bar(54, 45, 86, 45, 1.8, YELLOW))
    for k in range(3):
        p.append(circ(60 + k * 10, 47, 1.4, YELLOW))
    p.append(opoly_s([(50, 96), (90, 96), (92, 120), (48, 120)], "#4a3a28"))
    p.append(bar(50, 104, 90, 104, 1.4, YELLOW))
    for x in (56, 84):
        p.append(opoly_s(rrect(x - 8, 68, 16, 12, 1), "#6a5a48"))
    return base, "", "".join(p)


OUTFITS = {
    "pit_foreman": (pit_foreman, "Pit Foreman", "supervisor"),
    "belt_crew": (belt_crew, "Belt Crew", "worker"),
    "consortium_boss": (consortium_boss, "Consortium Boss", "management"),
}


# ================================================================ LAYOUTS
def station_plan(P):
    S = P["shadow"]
    room = "#5a4a38"
    o = [grid_bg(320, 200)]
    # central processing spine with drums on either side
    o.append(bar(160, 40, 160, 160, 12, room))
    o.append(circ(80, 70, 26, room))
    o.append(circ(240, 70, 26, room))
    o.append(circ(80, 130, 26, room))
    o.append(circ(240, 130, 26, room))
    # conveyor paths
    o.append(bar(98, 100, 222, 100, 2.4, S))
    for k in range(8):
        o.append(bar(102 + k * 15, 98, 102 + k * 15, 102, 0.9, S))
    # floodlamps
    o.append(circ(160, 30, 3.2, P["glass"]))
    o.append(circ(292, 100, 4.5, P["glass"]))
    o.append(bar(284, 100, 292, 100, 1.2, P["glass"]))
    o.append(label([(80, 40, "DRUM"), (240, 40, "DRUM"), (160, 174, "PROCESSING SPINE")], "#8a7a68"))
    return "".join(o)


def mining_camp(P):
    room = "#5a4a38"
    o = [grid_bg(320, 200)]
    # scattered structures around a central headframe
    o.append(opoly(rrect(50, 60, 44, 50, 1), room))
    o.append(opoly(rrect(46, 128, 52, 42, 1), room))
    o.append(opoly(rrect(226, 76, 48, 46, 1), room))
    for x in (76, 122):
        o.append(opoly(rrect(x - 4, 90, 8, 60, 1), P["hull_lo"], d=1.0))
    o.append(bar(72, 88, 126, 88, 1.2, YELLOW))
    o.append(chevrons(76, 122, 86, 2.6, 2, YELLOW, n=2, down=False))
    o.append(circ(292, 100, 4.5, P["glass"]))
    o.append(bar(284, 100, 292, 100, 1.2, P["glass"]))
    o.append(label([(72, 45, "SHACK"), (72, 120, "BUNK"), (250, 60, "MILL"), (100, 176, "MINE CAMP")], "#8a7a68"))
    return "".join(o)


LAYOUTS = {
    "station_plan": (station_plan, "Platform interior", "station floor plan"),
    "mining_camp": (mining_camp, "Mining site", "moon settlement plan"),
}
