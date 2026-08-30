"""Drossholt Company outfits, on the cinched-waist body with the Drossholt
signature: RIVETED PATCH-PLATES bolted on at odd angles in mismatched shades,
a bolted box respirator with a hose to a hip canister, and one big pauldron
over one bare shoulder - nothing built as a whole. Strokeless.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, offset_poly, bar, rrect, _u

OUT = "#141219"
WAIST, BELT = 108, 104
TAN, AMBER, RUST = "#b58a5c", "#ffc850", "#8a6845"


def op_s(pts, fill, d=1.1, ol=OUT):
    return poly(offset_poly(pts, d), ol) + poly(pts, fill)


def rib_line(pts, w, col):
    p = [pts[0]]
    for q in pts[1:]:
        if q != p[-1]:
            p.append(q)
    if len(p) < 2:
        return ""
    def u(v):
        L = math.hypot(*v) or 1
        return (v[0] / L, v[1] / L)
    L, R = [], []
    for i in range(len(p)):
        if i == 0:
            d = u((p[1][0] - p[0][0], p[1][1] - p[0][1]))
        elif i == len(p) - 1:
            d = u((p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]))
        else:
            d1 = u((p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]))
            d2 = u((p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]))
            d = u((d1[0] + d2[0], d1[1] + d2[1]))
        nb = (-d[1], d[0])
        L.append((p[i][0] + nb[0] * w, p[i][1] + nb[1] * w))
        R.append((p[i][0] - nb[0] * w, p[i][1] - nb[1] * w))
    return poly(L + R[::-1], col)


def patch_plates(spec=None):
    """Mismatched riveted rectangles bolted on at odd angles - the signature."""
    spec = spec or [([(50, 68), (72, 66), (74, 92), (52, 96)], "#8a6845"),
                    ([(72, 74), (90, 78), (88, 104), (70, 100)], "#9a7550"),
                    ([(54, 100), (78, 104), (76, WAIST + 4), (52, WAIST)], "#7a5c3f")]
    o = []
    for pts, col in spec:
        o.append(op_s(pts, col))
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        for dx, dy in ((-7, -7), (7, -7), (7, 7), (-7, 7)):
            o.append(circ(cx + dx, cy + dy, 1.2, "#4a3527"))
    return "".join(o)


def box_respirator(hose_to=(96, 96)):
    o = [op_s(rrect(62, 48, 16, 10, 1), "#5a4130")]
    for gx in (65, 69, 73):
        o.append(bar(gx, 50, gx, 56, 0.9, "#2c2018"))
    o.append(rib_line([(78, 54), (88, 58), hose_to], 1.4, "#5a4130"))
    o.append(op_s(rrect(hose_to[0] - 6, hose_to[1] - 12, 12, 22, 2), "#6a4f39"))  # hip canister
    return "".join(o)


def mismatched_shoulders(big="#5a4130", accent="#8a6845"):
    return op_s([(41, 62), (56, 60), (57, 76), (44, 80)], big) + circ(48, 70, 3, accent)


# ---------------------------------------------------------------- outfits
def vacsuit():
    return (dict(helmet="#ffc850", suit="#c89664", boot="#5a4130", sleeve="#a97f52"),
            "", patch_plates() + box_respirator() + mismatched_shoulders())


def coveralls():
    base = dict(no_helmet=True, suit="#dab488", boot="#5a4130", sleeve="#c89664", belt="#5a4130")
    post = (patch_plates([([(52, 72), (74, 70), (76, 98), (54, 100)], "#8a6845"),
                          ([(56, 102), (80, 106), (78, WAIST + 6), (54, WAIST + 2)], "#7a5c3f")])
            + op_s(rrect(60, 46, 20, 8, 1), "#5a4130")                          # dust scarf over the mouth
            + rib_line([(70, 62), (70, 100)], 0.9, "#5a4130"))
    return base, "", post


def cutterman():
    base = dict(helmet="#ffc850", suit="#c89664", boot="#5a4130", sleeve="#c89664",
                shoulders="#5a4130", torch="#8a6845", belt="#5a4130", backpack="#7a5c3f")
    post = (patch_plates() + box_respirator(hose_to=(44, 96))
            + op_s([(37, 92), (49, 92), (47, WAIST + 4), (35, WAIST - 4)], "#6a4f39")  # heavy cutting gauntlet
            + rib_line([(43, 96), (43, WAIST)], 0.8, "#3a2c1e"))
    return base, "", post


def tallyman():
    base = dict(cap="#5a4130", suit="#dab488", boot="#5a4130", sleeve="#c89664",
                belt="#5a4130", badge="#ffe196")
    post = (patch_plates([([(52, 70), (72, 68), (73, 88), (53, 90)], "#8a6845")])
            + op_s(rrect(56, 74, 28, 22, 2), "#6a4f39")                         # chest ledger board
            + "".join(bar(59, 80 + k * 4, 81, 80 + k * 4, 0.9, "#3a2c1e") for k in range(3))
            + rib_line([(84, 82), (92, 84)], 1.2, "#3a2c1e") + circ(92, 84, 1.4, "#8a6845"))  # stylus on a cord
    return base, "", post


def gun_bosun():
    base = dict(helmet="#ffc850", visor="#2c2622", suit="#a97f52", boot="#5a4130",
                sleeve="#a97f52", chest="#5a4130", belt="#5a4130")
    post = (patch_plates()
            + poly([(50, 60), (58, 66), (86, 116), (78, 120)], "#3a2c1e")       # ammo bandolier
            + "".join(op_s(rrect(t[0] - 2, t[1] - 3, 5, 8, 1), "#8a8f66")
                      for t in ((56, 74), (63, 88), (70, 102), (77, 116)))
            + box_respirator(hose_to=(40, 100)))
    return base, "", post


def foreman():
    base = dict(helmet="#ffc850", suit="#96703c", boot="#5a4130", sleeve="#8a6845",
                shoulders="#78583a", belt="#5a4130", badge="#ffc850")
    post = (patch_plates()
            + op_s([(50, 66), (74, 64), (76, 78), (52, 80)], "#ffc850")         # hi-vis foreman panel
            + op_s(rrect(80, 108, 14, 18, 2), "#5a4130")                        # clipboard on the hip
            + mismatched_shoulders())
    return base, "", post


def hauler():
    base = dict(no_helmet=True, suit="#bea073", boot="#5a4130", sleeve="#a97f52",
                backpack="#967452", belt="#5a4130")
    post = (patch_plates([([(52, 72), (74, 70), (76, 100), (54, 102)], "#8a6845")])
            + op_s([(44, 60), (58, 66), (56, 110), (42, 104)], "#5a4130")       # a load strap over one shoulder
            + op_s([(82, 66), (96, 60), (98, 104), (84, 110)], "#5a4130"))
    return base, "", post


OUTFITS = {
 "vacsuit": (vacsuit, "Vacsuit", "the standard bolted vacuum suit"),
 "coveralls": (coveralls, "Coveralls", "yard work, no vacuum"),
 "cutterman": (cutterman, "Cutterman", "torches derelicts apart"),
 "tallyman": (tallyman, "Tallyman", "counts what comes off the ships"),
 "gun_bosun": (gun_bosun, "Gun-Bo's'n", "runs the Bulwark's guns"),
 "foreman": (foreman, "Foreman", "runs the yard crew"),
 "hauler": (hauler, "Hauler", "moves the heavy freight by hand"),
}
