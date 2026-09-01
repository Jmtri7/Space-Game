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


def box_respirator():
    """A bolted box over the mouth; a short hose runs down the RIGHT side of the
    jaw and shoulder to a canister clipped at the right hip - never across the
    chest. The canister sits inside the arm line so the arm laps its outer edge."""
    o = [op_s(rrect(62, 54, 16, 10, 1), "#5a4130")]        # box over nose + mouth
    for gx in (65, 69, 73):
        o.append(bar(gx, 56, gx, 62, 0.9, "#2c2018"))      # grille slats
    o.append(rib_line([(79, 58), (84, 68), (84, 96), (82, 112)], 1.6, "#5a4130"))  # hose down the right side
    o.append(op_s(rrect(76, 112, 12, 20, 2), "#6a4f39"))   # hip canister (x76-88, inside the arm)
    return "".join(o)


def mismatched_shoulders(big="#5a4130", accent="#8a6845"):
    # one big pauldron over the left shoulder/upper-arm (arm shaft x45-55)
    return op_s([(43, 62), (55, 60), (56, 76), (45, 80)], big) + circ(49, 70, 3, accent)


# ---------------------------------------------------------------- outfits
def vacsuit():
    return (dict(helmet="#ffc850", suit="#c89664", boot="#5a4130", sleeve="#a97f52"),
            "", patch_plates() + box_respirator() + mismatched_shoulders())


def coveralls():
    base = dict(no_helmet=True, suit="#dab488", boot="#5a4130", sleeve="#c89664", belt="#5a4130")
    post = (patch_plates([([(52, 72), (74, 70), (76, 98), (54, 100)], "#8a6845"),
                          ([(56, 102), (80, 106), (78, WAIST + 6), (54, WAIST + 2)], "#7a5c3f")])
            + op_s([(58, 54), (82, 54), (80, 65), (60, 65)], "#5a4130"))        # dust scarf over nose + mouth
    return base, "", post


def cutterman():
    base = dict(helmet="#ffc850", suit="#c89664", boot="#5a4130", sleeve="#c89664",
                shoulders="#5a4130", torch="#8a6845", belt="#5a4130", backpack="#7a5c3f")
    post = (patch_plates() + box_respirator()
            + op_s([(43, 92), (54, 92), (53, WAIST + 6), (44, WAIST + 6)], "#6a4f39")  # heavy cutting gauntlet on the left forearm
            + "".join(circ(48, 98 + k * 5, 1.0, "#3a2c1e") for k in range(3)))          # gauntlet rivets
    return base, "", post


def tallyman():
    base = dict(cap="#5a4130", suit="#dab488", boot="#5a4130", sleeve="#c89664",
                belt="#5a4130", badge="#ffe196")
    post = (patch_plates([([(52, 70), (72, 68), (73, 88), (53, 90)], "#8a6845")])
            + op_s(rrect(56, 74, 28, 22, 2), "#6a4f39")                         # chest ledger board
            + "".join(bar(59, 80 + k * 4, 81, 80 + k * 4, 0.9, "#3a2c1e") for k in range(3))
            + rib_line([(70, 96), (76, 100), (80, 96)], 1.0, "#3a2c1e") + circ(80, 96, 1.4, "#8a6845"))  # stylus on a short cord
    return base, "", post


def gun_bosun():
    base = dict(helmet="#ffc850", visor="#2c2622", suit="#a97f52", boot="#5a4130",
                sleeve="#a97f52", chest="#5a4130", belt="#5a4130")
    post = (patch_plates()
            + poly([(50, 60), (58, 66), (86, 116), (78, 120)], "#3a2c1e")       # ammo bandolier
            + "".join(op_s(rrect(t[0] - 2, t[1] - 3, 5, 8, 1), "#8a8f66")
                      for t in ((56, 74), (63, 88), (70, 102), (77, 116)))
            + box_respirator())
    return base, "", post


def foreman():
    base = dict(helmet="#ffc850", suit="#96703c", boot="#5a4130", sleeve="#8a6845",
                shoulders="#78583a", belt="#5a4130", badge="#ffc850")
    pre = op_s(rrect(74, 110, 13, 17, 2), "#5a4130")                            # clipboard on the hip (behind the arm)
    post = (patch_plates()
            + op_s([(50, 66), (74, 64), (76, 78), (52, 80)], "#ffc850")         # hi-vis foreman panel
            + mismatched_shoulders())
    return base, pre, post


def hauler():
    base = dict(no_helmet=True, suit="#bea073", boot="#5a4130", sleeve="#a97f52",
                backpack="#967452", belt="#5a4130")
    post = (patch_plates([([(52, 72), (74, 70), (76, 100), (54, 102)], "#8a6845")])
            + op_s([(45, 60), (56, 64), (55, 108), (45, 104)], "#5a4130")        # load strap over the left shoulder
            + op_s([(84, 64), (95, 60), (95, 104), (85, 108)], "#5a4130"))       # and the right
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
