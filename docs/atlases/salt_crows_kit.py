"""The Salt Crows - full frontier atlas content. Asymmetric raider, scavenged parts,
mismatched everything, the crow mark. Strokeless. See culture_common.py.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, rrect, opoly, ocirc, bar, ngon
from culture_common import (grid_bg, ribbon, opoly_s, dot_run, chevrons, groove,
                            flame, stencil, label, OUT)

BRASS = "#b98b4a"
BONE = "#e8e2d4"
RED_V = "#5a4068"
GREEN_D = "#8a6845"
BLUE_F = "#41506a"


def _crow(cx, cy, col):
    """A crude asymmetric crow mark - a simple glyph."""
    return poly([(cx - 8, cy - 2), (cx - 2, cy - 8), (cx + 4, cy - 4),
                 (cx, cy + 2), (cx + 6, cy + 4), (cx + 2, cy), (cx - 4, cy + 6),
                 (cx - 6, cy + 2), (cx - 8, cy + 2)], col)


# ================================================================ SHIPS
def cutter(P):
    H, L, G, T, O, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    o.append(flame(101, 162, 3.6, 18, O))
    o.append(opoly(rrect(94, 140, 14, 28, 1), L, d=1.4))
    o.append(opoly(rrect(96, 144, 8, 8, 0), S, d=0.8))
    # asymmetric wedge hull
    hull = [(120, 32), (138, 88), (130, 152), (102, 158), (80, 150), (88, 88)]
    o.append(opoly(hull, H, d=1.6, ol=S))
    o.append(groove(90, 70, 48, 16, "#4a241b"))
    # one small scavenged wing - Vherathi-ish curve
    o.append(opoly([(88, 96), (50, 88), (46, 100), (86, 108)], RED_V, d=1.1))
    o.append(circ(86, 102, 1.4, S))
    # ram prow
    o.append(poly([(106, 34), (124, 34), (120, 20), (110, 20)], L))
    o.append(bar(104, 32, 126, 32, 1.2, S))
    o.append(_crow(120, 110, BONE))
    return "".join(o)


def raider(P):
    from frontier_ships import salt_crows
    return salt_crows(P)


def breacher(P):
    """Heavy - massive paired engines, a boarding platform, multiple scavenged wings."""
    H, L, G, T, O, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    # two huge bolted engines
    o.append(flame(96, 178, 5, 24, O))
    o.append(flame(144, 172, 3.2, 18, O))
    o.append(ring_strip(96, 158, 15, 10, S, n=18))
    o.append(opoly(rrect(82, 138, 30, 40, 2), L, d=1.6))
    for rx in (88, 104):
        for ry in (148, 164):
            o.append(circ(rx, ry, 1.4, S))
    o.append(ring_strip(144, 154, 12, 8, "#b98b4a", n=14))
    o.append(opoly(rrect(132, 134, 24, 28, 2), BRASS, d=1.4))
    # broad asymmetric hull, kinked spine
    hull = [(120, 34), (146, 94), (152, 156), (128, 176), (76, 174), (62, 156),
            (68, 94), (104, 50)]
    o.append(opoly(hull, H, d=1.8, ol=S))
    o.append(groove(104, 74, 52, 22, "#4a241b"))
    # three mismatched wings, bolted on crooked
    o.append(opoly([(72, 96), (30, 84), (24, 100), (70, 112)], RED_V, d=1.2))
    o.append(opoly(rrect(156, 104, 40, 20, 1), GREEN_D, d=1.3))
    for rx in (162, 186):
        o.append(bar(rx, 108, rx, 120, 0.9, S))
    o.append(opoly([(76, 140), (32, 158), (38, 172), (80, 156)], BLUE_F, d=1.2))
    # boarding platform - a folded gantry
    o.append(ribbon([(156, 148), (180, 158), (184, 180), (176, 188)], 2.8, S))
    o.append(poly([(176, 188), (168, 192), (174, 200), (182, 196), (180, 188)], BRASS))
    # trophy trinkets on the rail
    for ty in (122, 140):
        o.append(bar(68, ty, 64, ty + 6, 0.8, BRASS))
        o.append(circ(62, ty + 8, 2, BONE))
    o.append(_crow(120, 100, BONE))
    return "".join(o)


def ring_strip(cx, cy, r_out, r_in, col, n=40, op=None):
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


SHIPS = {
    "cutter": (cutter, "Salt Crow Cutter", "fast trader - one wing"),
    "raider": (raider, "Salt Crow Magpie", "the standard raider"),
    "breacher": (breacher, "Salt Crow Dreadnought", "siege ship - dual engines"),
}


# ================================================================ STATION
def station(P):
    H, L, G, T, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["shadow"]
    cx = cy = 120.0
    o = [grid_bg()]
    # three hull sections lashed together at odd angles
    o.append(opoly(rrect(cx - 48, cy - 20, 58, 60, 2), H, d=1.8, ol=S))
    o.append(opoly(rrect(cx + 8, cy + 8, 52, 52, 2), H, d=1.6, ol=S))
    o.append(opoly(rrect(cx - 24, cy + 32, 48, 44, 2), H, d=1.7, ol=S))
    # tar seams + brass patches
    o.append(bar(cx - 48, cy + 24, cx + 50, cy + 22, 1.4, "#3a241a"))
    o.append(poly([(cx - 20, cy - 8), (cx - 12, cy - 2), (cx - 8, cy - 12)], BRASS, op=0.6))
    o.append(poly([(cx + 24, cy + 20), (cx + 32, cy + 26), (cx + 28, cy + 16)], BRASS, op=0.6))
    # mismatched dock arms
    for sx, ax in ((1, 30), (-1, -30)):
        armx = cx + sx * 62
        o.append(bar(cx + sx * 50, cy + 20, armx, cy + 18, 2.0, L))
        o.append(opoly(rrect(armx - 6, cy + 14, 12, 12, 1), "#0e1116", d=1.0))
        o.append(circ(armx, cy + 12, 2.4, G))
    # trophy running lights on a line
    for lx in (cx - 30, cx, cx + 30):
        o.append(bar(lx, cy - 70, lx, cy + 80, 0.6, "#3a241a"))
        for ly in (cy - 60, cy - 30, cy, cy + 30, cy + 60):
            o.append(circ(lx, ly, 1.8, T))
    o.append(_crow(cx, cy - 48, BONE))
    return "".join(o)


STATION = {"station": (station, "Salt Crow Hulk", "lashed-together station")}


# ================================================================ BUILDINGS
def _shack(P, w, h, label_txt):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    cx = 100.0
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(cx - w / 2, 170 - h, w, h, 0), H, d=1.8, ol=S))
    # mismatched panels, tar seams
    o.append(groove(cx - w * 0.38, 170 - h + 8, w * 0.18, h - 16, "#3a241a"))
    o.append(groove(cx - w * 0.08, 170 - h + 10, w * 0.16, h - 20, "#3a241a"))
    o.append(groove(cx + w * 0.24, 170 - h + 6, w * 0.20, h - 12, "#3a241a"))
    # brass patches at random spots
    for px, py in ((cx - w * 0.3, 170 - h + 20), (cx + w * 0.2, 170 - h + 40)):
        o.append(poly([(px - 8, py), (px + 8, py), (px + 8, py + 12), (px - 8, py + 12)],
                      BRASS, op=0.55))
    # bolted door frame
    o.append(opoly(rrect(cx - 12, 150, 24, 20, 1), "#0e1116", d=1.0))
    for dx, dy in ((-9, 152), (9, 152), (-9, 166), (9, 166)):
        o.append(circ(cx + dx, dy, 1.1, S))
    o.append(_crow(cx, 170 - h + 12, BONE))
    o.append(stencil(cx, 186, label_txt, "#8a6a5c", 6))
    return "".join(o)


def scrap_shack(P):
    return _shack(P, 130, 80, "STORES")


def tinker_shed(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(64, 120, 72, 68, 0), H, d=1.8, ol=S))
    o.append(groove(72, 132, 14, 28, "#3a241a"))
    o.append(groove(100, 130, 16, 32, "#3a241a"))
    o.append(groove(136, 134, 12, 24, "#3a241a"))
    o.append(poly([(76, 120), (124, 120), (122, 110), (78, 110)], BRASS, op=0.6))
    o.append(opoly(rrect(88, 150, 24, 16, 1), "#0e1116", d=1.0))
    o.append(bar(92, 152, 108, 152, 1.2, S))
    for dx, dy in ((-9, 150), (9, 150), (-9, 162), (9, 162)):
        o.append(circ(100 + dx, 158 + dy, 1.1, S))
    o.append(_crow(100, 134, BONE))
    o.append(stencil(100, 186, "TINKER SHED", "#8a6a5c", 6))
    return "".join(o)


def trophy_shrine(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(70, 110, 60, 80, 0), H, d=1.8, ol=S))
    # open shelves for trinkets
    for ry in (130, 150, 170):
        o.append(bar(76, ry, 124, ry, 1.6, S))
        for k in range(3):
            cx = 86 + k * 16
            o.append(circ(cx, ry - 6, 2.8, BRASS))
    o.append(bar(100, 108, 100, 188, 1.2, S))
    o.append(_crow(100, 100, BONE))
    o.append(stencil(100, 186, "TROPHY SHRINE", "#8a6a5c", 6))
    return "".join(o)


BUILDINGS = {
    "scrap_shack": (scrap_shack, "Scrap Shack", "storage / hab"),
    "tinker_shed": (tinker_shed, "Tinker Shed", "workshop"),
    "trophy_shrine": (trophy_shrine, "Trophy Shrine", "gathering hall"),
}


# ================================================================ FURNITURE
def barrel_table(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(circ(100, 114, 22, H))
    for k in range(6):
        a = 2 * math.pi * k / 6
        o.append(circ(100 + 18 * math.cos(a), 114 + 18 * math.sin(a), 2.2, S))
    o.append(bar(82, 114, 118, 114, 1.8, S))
    o.append(poly([(88, 110), (112, 110), (110, 118), (90, 118)], "#3a241a", op=0.7))
    return "".join(o)


def rope_hammock(P):
    o = [grid_bg(200, 200)]
    o.append(bar(64, 80, 64, 140, 2.2, "#5a4636"))
    o.append(bar(136, 80, 136, 140, 2.2, "#5a4636"))
    for ry in (90, 110, 130):
        o.append(ribbon([(70, ry), (90, ry + 8), (110, ry), (130, ry - 8)], 1.4, "#3a241a"))
    o.append(poly([(68, 120), (132, 120), (130, 148), (70, 148)], "#7a5a4a", op=0.75))
    return "".join(o)


def loot_rack(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(rrect(60, 80, 80, 90, 0), H, d=1.5))
    for i in range(4):
        o.append(groove(66, 92 + i * 20, 68, 12, "#0e1116"))
        for k in range(5):
            hx = 76 + k * 14
            o.append(circ(hx, 98 + i * 20, 2.4, BRASS))
    o.append(bar(60, 80, 140, 80, 1.0, S))
    return "".join(o)


def scrap_brazier(P):
    H, L, S = P["hull"], P["hull_lo"], P["shadow"]
    o = [grid_bg(200, 200)]
    o.append(opoly(ngon(100, 132, 18, 14, 8), H, d=1.4))
    o.append(poly([(88, 120), (112, 120), (108, 146), (92, 146)], "#0e1116"))
    o.append(circ(100, 124, 6, "#ff7a2a", op=0.4))
    o.append(circ(100, 124, 3, "#ff7a2a", op=0.8))
    for dx, dy in ((-8, -16), (8, -16), (0, -24)):
        o.append(bar(100 + dx, 132 + dy, 100 + dx, 120, 1.4, "#3a241a"))
    return "".join(o)


FURNITURE = {
    "barrel_table": (barrel_table, "Barrel Table", "seating"),
    "rope_hammock": (rope_hammock, "Rope Hammock", "bunk"),
    "loot_rack": (loot_rack, "Loot Rack", "display"),
    "scrap_brazier": (scrap_brazier, "Scrap Brazier", "fire"),
}


# ================================================================ OUTFITS
def deck_hand():
    base = dict(suit="#7a3b2c", boot="#3a2018", sleeve="#5a2c20", belt="#2c1a12")
    p = []
    # headwrap instead of helmet
    p.append(opoly_s([(55, 44), (85, 42), (86, 52), (54, 54)], "#c98a3c"))
    p.append(ribbon([(85, 48), (94, 52), (98, 62)], 1.6, "#c98a3c"))
    p.append(circ(63, 49, 1.0, "#2c1a12"))
    p.append(circ(73, 49, 1.0, "#2c1a12"))
    # salvaged monocle-visor
    p.append(ocirc(75.5, 49, 3.2, "#ffd24a", d=1.0))
    p.append(bar(78, 48, 88, 44, 0.8, "#3a2018"))
    # mismatched scavenged plates
    p.append(ribbon([(44, 68), (40, 80), (46, 92)], 3.0, RED_V))
    p.append(opoly_s([(58, 82), (82, 78), (84, 104), (60, 108)], GREEN_D))
    for dx, dy in ((-8, -8), (8, -8), (8, 8), (-8, 8)):
        p.append(circ(71 + dx, 93 + dy, 1.2, "#3a2018"))
    # hook-hand
    p.append(bar(94, 118, 94, 128, 1.4, "#b8b0a0"))
    p.append(ribbon([(94, 128), (99, 132), (98, 138), (92, 137)], 1.6, "#b8b0a0"))
    # bandolier sash
    p.append(poly([(52, 66), (60, 66), (92, 128), (84, 128)], "#2c1a12"))
    for t in (0.25, 0.5, 0.75):
        tx = 56 + (88 - 56) * t
        ty = 66 + (128 - 66) * t
        p.append(opoly_s(rrect(tx - 2, ty - 4, 4, 8, 1), "#b8b0a0"))
    # trophy trinkets
    for x in (58, 64, 82):
        p.append(bar(x, 112, x, 120, 0.7, "#c98a3c"))
        p.append(circ(x, 122, 1.6, BONE))
    p.append(_crow(70, 116, BONE))
    return base, "", "".join(p)


def captain():
    base = dict(suit="#6a2b1c", boot="#2a1810", sleeve="#4a1f10", belt="#1a0f08", buckle="#c98a3c")
    p = []
    # fancier wrap with brass
    p.append(opoly_s([(52, 40), (88, 38), (90, 54), (50, 56)], "#b8794c"))
    p.append(ribbon([(88, 46), (100, 50), (102, 68)], 2.0, "#b8794c"))
    for k in range(3):
        p.append(circ(60 + k * 10, 47, 1.4, BRASS))
    # eyepatch - larger monocle
    p.append(ocirc(76, 48, 4.2, "#c98a3c", d=1.2))
    p.append(bar(80, 46, 92, 42, 1.0, "#3a2018"))
    # captain's coat over standard fit
    p.append(opoly_s([(46, 68), (94, 68), (100, 128), (40, 128)], "#4a1f10"))
    p.append(ribbon([(46, 78), (40, 90), (44, 108)], 2.0, BRASS))
    p.append(ribbon([(94, 78), (100, 90), (96, 108)], 2.0, BRASS))
    # heavy bandolier with more trinkets
    p.append(poly([(50, 66), (60, 66), (96, 132), (86, 132)], "#1a0f08"))
    for t in (0.2, 0.4, 0.6, 0.8):
        tx = 54 + (90 - 54) * t
        ty = 66 + (132 - 66) * t
        p.append(opoly_s(rrect(tx - 2.4, ty - 5, 4.8, 10, 1), BRASS))
    # many trophy trinkets
    for x in (52, 58, 66, 74, 82, 88):
        p.append(bar(x, 110, x, 120, 0.8, BRASS))
        p.append(circ(x, 123, 2, BONE))
    p.append(_crow(70, 120, BONE))
    return base, "", "".join(p)


def salvage_master():
    base = dict(suit="#5a2b1c", boot="#2a1810", sleeve="#3a1a0f", belt="#1a0f08")
    p = []
    # wrap + tools strapped
    p.append(opoly_s([(54, 42), (86, 40), (88, 54), (52, 56)], "#a86a3c"))
    p.append(ribbon([(86, 48), (98, 52), (102, 70)], 1.8, "#a86a3c"))
    # visor + magnifying glass
    p.append(ocirc(74, 48, 3.8, "#ffd24a", d=1.0))
    p.append(circ(74, 48, 1.2, "#3a2018"))
    p.append(bar(76, 46, 88, 42, 0.9, "#3a2018"))
    # work belt with tool loops
    p.append(opoly_s([(54, 110), (86, 110), (88, 120), (52, 120)], "#3a1a0f"))
    for k in range(6):
        tx = 58 + k * 5
        p.append(bar(tx, 108, tx, 116, 0.7, "#b8b0a0"))
        p.append(poly(rrect(tx - 1, 116, 2, 3, 0), "#8a6a5c"))
    # apron with pockets
    p.append(poly([(54, 120), (86, 120), (84, 160), (56, 160)], "#2a1810"))
    for px in (62, 78):
        p.append(groove(px - 6, 130, 12, 18, "#1a0f08"))
    p.append(_crow(70, 112, BONE))
    return base, "", "".join(p)


OUTFITS = {
    "deck_hand": (deck_hand, "Deck Hand", "crew"),
    "captain": (captain, "Crow Captain", "captain"),
    "salvage_master": (salvage_master, "Salvage Master", "officer"),
}


# ================================================================ LAYOUTS
def station_plan(P):
    S = P["shadow"]
    G = P["glass"]
    room = "#5a3828"
    o = [grid_bg(320, 200)]
    # three lashed-together hulks - rough circles
    o.append(circ(80, 80, 32, room))
    o.append(circ(160, 110, 34, room))
    o.append(circ(110, 160, 30, room))
    # tar seam paths
    o.append(bar(76, 100, 142, 130, 2.4, "#3a241a"))
    o.append(bar(140, 130, 130, 170, 2.2, "#3a241a"))
    # trophy lights scattered
    for lx, ly in ((92, 65), (168, 85), (150, 140), (98, 155)):
        o.append(circ(lx, ly, 1.6, "#ff7a2a"))
    o.append(circ(292, 110, 4.5, G))
    o.append(bar(284, 110, 292, 110, 1.2, G))
    o.append(label([(80, 45, "STORES"), (160, 85, "HOLD"), (110, 150, "CREW"),
                    (160, 190, "HULK INTERIOR")], "#b8a89c"))
    return "".join(o)


def city_plan(P):
    room = "#5a3828"
    G = P["glass"]
    o = [grid_bg(320, 200)]
    # scattered shacks around a scrap yard
    o.append(opoly(rrect(52, 54, 48, 38, 0), room))
    o.append(opoly(rrect(140, 66, 52, 40, 0), room))
    o.append(opoly(rrect(64, 130, 44, 36, 0), room))
    o.append(opoly(rrect(158, 136, 48, 38, 0), room))
    # tar/rust connecting paths
    o.append(ribbon([(76, 92), (166, 86)], 2.6, "#3a241a"))
    o.append(ribbon([(166, 106), (86, 140)], 2.4, "#3a241a"))
    # central scrap pile (trophy shrine)
    o.append(circ(120, 100, 28, "#4a3828"))
    for k in range(8):
        a = 2 * math.pi * k / 8
        o.append(circ(120 + 20 * math.cos(a), 100 + 20 * math.sin(a), 2.8, BRASS, op=0.7))
    o.append(_crow(120, 98, BONE))
    o.append(circ(292, 110, 4.5, G))
    o.append(bar(284, 110, 292, 110, 1.2, G))
    o.append(label([(76, 42, "SHACKS"), (166, 50, "HULL DOCKS"), (120, 178, "SCRAP TOWN")],
                   "#b8a89c"))
    return "".join(o)


LAYOUTS = {
    "station_plan": (station_plan, "Hulk interior", "station floor plan"),
    "city_plan": (city_plan, "Scrap town", "moon settlement plan"),
}
