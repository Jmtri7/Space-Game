"""Sol Federation crew outfits, redrawn on the cinched-waist body with the
Federation signature: a regulation helmet with a horizontal visor slit + chin
guard (never a bubble), a white contrast centreline stripe, an amber
hazard-chevron shoulder flash, and a stencilled SF-### registration. Strokeless.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, rrect, offset_poly, bar, _u

OUT = "#141219"
WAIST, BELT = 108, 104
HULL, STRIPE, HAZ, GLASS, DARK = "#41506a", "#dfe6ee", "#f2b23a", "#cfe0f0", "#1c2430"


def rib(pts, w, col, op=None):
    pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    if len(pts) < 2:
        return ""
    n = len(pts)
    L, R = [], []
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
        L.append((pts[i][0] + nb[0] * w, pts[i][1] + nb[1] * w))
        R.append((pts[i][0] - nb[0] * w, pts[i][1] - nb[1] * w))
    return poly(L + R[::-1], col, op=op)


def op_s(pts, fill, d=1.1, ol=OUT):
    return poly(offset_poly(pts, d), ol) + poly(pts, fill)


def chevron_flash(x=85, side=1):
    """Amber hazard chevrons sitting on the (right) upper arm - x..x+8 stays
    inside the arm shaft (x85-95), so the flash tracks the arm, not the air."""
    o = []
    for k in range(3):
        y = 73 + k * 4
        o.append(poly([(x, y), (x + side * 4, y + 3), (x + side * 8, y),
                       (x + side * 7, y), (x + side * 4, y + 1.5), (x + side * 1, y)], HAZ))
    return "".join(o)


def sf_stencil(num, y=104):
    return (f'<text x="70" y="{y}" fill="#8fb9c8" font-family="IBM Plex Mono, monospace" '
            f'font-size="7" text-anchor="middle" letter-spacing="0.5">SF-{num}</text>')


def SIG_HELM():
    """The visor-slit regulation helmet + chin guard - crew who wear a helmet."""
    return (poly([(56, 48), (84, 48), (82, 55), (58, 55)], DARK)
            + bar(57, 51, 83, 51, 1.0, "#8fb9c8")
            + op_s([(58, 58), (82, 58), (78, 66), (62, 66)], "#5a6b82"))


def SIG_LIVERY(num="000", stripe_to=WAIST):
    """White centreline stripe + amber chevron flash + SF-### stencil - on
    everyone, helmet or cap. The stripe starts at the collar (y67), clear of
    the chin and mouth."""
    return (poly([(68, 67), (72, 67), (72, stripe_to), (68, stripe_to)], STRIPE)
            + chevron_flash()
            + sf_stencil(num))


def SIG(num="000", stripe_to=WAIST):
    return SIG_HELM() + SIG_LIVERY(num, stripe_to)


# ---------------------------------------------------------------- outfits
def rating():
    return dict(helmet="#4a5a72", suit="#3a4a63", boot="#232c3a", collar=STRIPE), "", SIG("114")


def pilot():
    base = dict(helmet="#ced6dc", suit="#3a4658", boot="#282e38")
    post = (SIG("221", stripe_to=118)
            + rib([(52, 64), (70, 94), (88, 64)], 2.0, "#2b3542")                # flight harness
            + op_s(rrect(80, 116, 12, 16, 1), "#2b3542")                         # thigh checklist board
            + bar(82, 120, 90, 120, 0.9, "#8fb9c8") + bar(82, 124, 90, 124, 0.9, "#8fb9c8"))
    return base, "", post


def officer():
    base = dict(hat="#2e384a", helmet_r=17, suit="#2e384a", boot="#20262f",
                collar=STRIPE, shoulders="#28303e", coat=True)
    pre = (op_s([(48, WAIST), (92, WAIST), (95, 172), (45, 172)], "#28303e")     # frock coat skirt
           + op_s(rrect(86, BELT + 4, 7, 13, 1), DARK))                          # sidearm on the hip (behind arm)
    post = (SIG_LIVERY("O-2", stripe_to=WAIST)
            + poly([(52, 46), (88, 46), (82, 38), (74, 33), (66, 33), (58, 38)], "#2e384a")  # peaked cap
            + poly([(52, 46), (68, 46), (64, 42), (56, 42)], DARK)              # brim
            + "".join(bar(47, 96 + k * 4, 54, 96 + k * 4, 1.4, HAZ) for k in range(3))  # cuff braid, left forearm
            + op_s(rrect(45, 68, 16, 6, 1), HAZ) + op_s(rrect(79, 68, 16, 6, 1), HAZ)   # shoulder boards
            + poly([(63, 84), (67, 89), (63, 94), (59, 89)], HAZ))              # command badge, left breast
    return base, pre, post


def marine():
    base = dict(helmet="#3c4550", suit="#2c333e", boot="#1a1e24", visor="#8fb9c8",
                backpack="#2a303a")
    post = (op_s([(54, 62), (86, 62), (84, 74), (56, 74)], "#48525f")           # carapace seg 1
            + op_s([(56, 78), (84, 78), (82, 94), (58, 94)], "#48525f")
            + op_s([(58, 98), (82, 98), (80, 112), (60, 112)], "#48525f")
            + "".join(circ(x, 68, 1.2, DARK) for x in (60, 70, 80))
            + chevron_flash(85, 1)
            + op_s(rrect(56, 156, 14, 10, 2), "#48525f") + op_s(rrect(70, 156, 14, 10, 2), "#48525f")  # shin guards
            + sf_stencil("M-07", y=100))
    return base, "", post


def gate_warden():
    base = dict(helmet="#4a5a72", suit="#3a4a63", boot="#232c3a", collar=STRIPE)
    post = (op_s([(58, 66), (82, 66), (80, 112), (60, 112)], HAZ)               # hi-vis over-vest
            + bar(60, 88, 80, 88, 1.4, "#c46a10")
            + poly([(64, 74), (76, 74), (76, 84), (64, 84)], DARK)              # SF badge on the vest
            + circ(70, 79, 2.0, GLASS)
            + poly([(56, 48), (84, 48), (82, 55), (58, 55)], DARK)              # visor slit
            + bar(57, 51, 83, 51, 1.0, "#8fb9c8")
            + rib([(96, 70), (100, 96), (98, 120)], 1.6, "#5a6b82")             # scanner wand
            + circ(98, 120, 2.0, GLASS)
            + op_s(rrect(40, 108, 12, 16, 1), "#2b3542"))                       # data slate in hand
    return base, "", post


def fleet_command():
    base = dict(hat="#dfe6ee", helmet_r=17, suit="#252d3c", boot="#181d26",
                collar=STRIPE, shoulders="#dfe6ee", coat=True)
    pre = op_s([(46, WAIST), (94, WAIST), (98, 178), (42, 178)], "#222a37")     # flag-officer greatcoat
    post = (SIG_LIVERY("FLAG", stripe_to=WAIST)
            + "".join(circ(x, y, 1.6, HAZ) for x in (62, 78) for y in (70, 80, 90, 100))  # double-breasted buttons
            + op_s(rrect(44, 66, 18, 7, 1), HAZ) + op_s(rrect(78, 66, 18, 7, 1), HAZ)   # heavy boards
            + "".join(bar(46, 68 + k, 58, 68 + k, 0.9, "#252d3c") for k in (0, 2, 4))   # board rank lines, L
            + "".join(bar(82, 68 + k, 94, 68 + k, 0.9, "#252d3c") for k in (0, 2, 4))   #                   R (mirrored)
            + poly([(50, 40), (90, 40), (94, 34), (84, 26), (56, 26), (46, 34)], "#252d3c")  # scrambled-egg cap
            + poly([(50, 40), (72, 40), (68, 36), (54, 36)], DARK)
            + "".join(poly([(52 + i * 3, 37), (55 + i * 3, 34), (58 + i * 3, 37)], HAZ) for i in range(4))  # cap braid
            + poly([(63, 84), (68, 90), (63, 96), (58, 90)], HAZ))              # flag badge, left breast
    return base, pre, post


OUTFITS = {
 "rating": (rating, "Issue Rating", "the crew every ship and station runs on"),
 "pilot": (pilot, "Issue Pilot", "small craft, shuttles, the Cutter"),
 "officer": (officer, "Fleet Officer", "watch command, a bridge, a wardroom"),
 "marine": (marine, "Fleet Marine", "boarding, the brig, gate security"),
 "gate_warden": (gate_warden, "Gate Warden", "customs & the transponder log"),
 "fleet_command": (fleet_command, "Fleet Command", "the flag tier - Procyon Gate control"),
}
