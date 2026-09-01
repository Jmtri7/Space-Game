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
WAIST, BELT = 103, 99
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
    spec = spec or [([(51, 68), (72, 66), (73, 90), (53, 94)], "#8a6845"),
                    ([(70, 72), (87, 76), (85, 100), (68, 96)], "#9a7550"),
                    ([(54, 98), (78, 102), (76, WAIST + 2), (52, WAIST - 2)], "#7a5c3f")]
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
    o = [op_s(rrect(62, 48, 16, 10, 1), "#5a4130")]        # box over nose + mouth
    for gx in (65, 69, 73):
        o.append(bar(gx, 50, gx, 56, 0.9, "#2c2018"))      # grille slats
    o.append(rib_line([(80, 52), (86, 64), (86, 96), (84, 110)], 1.6, "#5a4130"))  # hose down the right side
    o.append(op_s(rrect(78, 106, 12, 20, 2), "#6a4f39"))   # hip canister (inside the arm)
    return "".join(o)


def mismatched_shoulders(big="#5a4130", accent="#8a6845"):
    # one big pauldron over the left shoulder/upper-arm (arm shaft x50-60)
    return op_s([(49, 62), (60, 60), (61, 76), (50, 80)], big) + circ(55, 70, 3, accent)


# ---------------------------------------------------------------- outfits
def vacsuit():
    return (dict(helmet="#ffc850", suit="#c89664", boot="#5a4130", sleeve="#a97f52"),
            "", patch_plates() + box_respirator() + mismatched_shoulders())


def coveralls():
    base = dict(no_helmet=True, suit="#dab488", boot="#5a4130", sleeve="#c89664", belt="#5a4130")
    post = (patch_plates([([(52, 70), (74, 68), (75, 94), (54, 97)], "#8a6845"),
                          ([(55, 99), (79, 103), (77, WAIST + 4), (53, WAIST)], "#7a5c3f")])
            + op_s([(59, 48), (81, 48), (79, 59), (61, 59)], "#5a4130"))        # dust scarf over nose + mouth
    return base, "", post


def cutterman():
    base = dict(helmet="#ffc850", suit="#c89664", boot="#5a4130", sleeve="#c89664",
                shoulders="#5a4130", torch="#8a6845", belt="#5a4130", backpack="#7a5c3f")
    post = (patch_plates() + box_respirator()
            + op_s([(49, 96), (60, 96), (59, WAIST + 4), (50, WAIST + 4)], "#6a4f39")  # heavy cutting gauntlet on the left forearm
            + "".join(circ(55, 100 + k * 5, 1.0, "#3a2c1e") for k in range(3)))          # gauntlet rivets
    return base, "", post


def tallyman():
    base = dict(cap="#5a4130", suit="#dab488", boot="#5a4130", sleeve="#c89664",
                belt="#5a4130", badge="#ffe196")
    post = (patch_plates([([(52, 68), (72, 66), (73, 86), (53, 88)], "#8a6845")])
            + op_s(rrect(57, 72, 26, 22, 2), "#6a4f39")                         # chest ledger board
            + "".join(bar(60, 78 + k * 4, 80, 78 + k * 4, 0.9, "#3a2c1e") for k in range(3))
            + rib_line([(70, 94), (76, 98), (80, 94)], 1.0, "#3a2c1e") + circ(80, 94, 1.4, "#8a6845"))  # stylus on a short cord
    return base, "", post


def gun_bosun():
    base = dict(helmet="#ffc850", visor="#2c2622", suit="#a97f52", boot="#5a4130",
                sleeve="#a97f52", chest="#5a4130", belt="#5a4130")
    post = (patch_plates()
            + poly([(52, 62), (59, 68), (84, 114), (77, 118)], "#3a2c1e")       # ammo bandolier
            + "".join(op_s(rrect(t[0] - 2, t[1] - 3, 5, 8, 1), "#8a8f66")
                      for t in ((57, 74), (63, 88), (69, 102), (75, 114)))
            + box_respirator())
    return base, "", post


def foreman():
    base = dict(helmet="#ffc850", suit="#96703c", boot="#5a4130", sleeve="#8a6845",
                shoulders="#78583a", belt="#5a4130", badge="#ffc850")
    pre = op_s(rrect(76, 104, 13, 17, 2), "#5a4130")                            # clipboard on the hip (behind the arm)
    post = (patch_plates()
            + op_s([(53, 70), (76, 68), (78, 82), (55, 84)], "#ffc850")         # hi-vis foreman panel
            + mismatched_shoulders())
    return base, pre, post


def hauler():
    base = dict(no_helmet=True, suit="#bea073", boot="#5a4130", sleeve="#a97f52",
                backpack="#967452", belt="#5a4130")
    post = (patch_plates([([(52, 70), (74, 68), (76, 98), (54, 100)], "#8a6845")])
            + op_s([(50, 60), (60, 64), (59, 104), (50, 100)], "#5a4130")        # load strap over the left shoulder
            + op_s([(80, 64), (90, 60), (90, 100), (81, 104)], "#5a4130"))       # and the right
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

# Full read-out of every drawn piece per outfit. The Drossholt signature is
# mismatched riveted patch-plates bolted on at odd angles (each with four
# corner bolt dots), a bolted box respirator over the mouth with a hose down
# the right side to a hip canister, and one oversized mismatched pauldron.
DETAILS = {
 "vacsuit":
   "The standard bolted vacuum suit: tan shell (`suit`), rust boots (`boot`), "
   "tan sleeves (`sleeve`), an amber hard hat (`helmet`). Signature: three "
   "mismatched riveted patch-plates across the torso, the bolted box "
   "respirator with a hose to a right-hip canister, and one oversized pauldron "
   "with an accent stud over the left shoulder.",
 "coveralls":
   "Yard coveralls, no vacuum: pale-tan shell (`suit`), rust boots (`boot`), "
   "tan sleeves (`sleeve`), a work belt (`belt`), bare head. Signature: two "
   "riveted patch-plates and a dust scarf tied over the nose and mouth.",
 "cutterman":
   "Torches derelicts apart: tan shell (`suit`, `sleeve`), rust boots "
   "(`boot`), an amber hard hat (`helmet`), a stowed cutting torch on the hip "
   "(`torch`), a pauldron (`shoulders`), a belt (`belt`), a back pack "
   "(`backpack`). Signature: patch-plates, the box respirator, and a heavy "
   "riveted cutting gauntlet on the left forearm.",
 "tallyman":
   "Counts what comes off the ships: pale-tan shell (`suit`, `sleeve`), rust "
   "boots (`boot`), a soft cap (`cap`), a belt (`belt`), a gold tally badge "
   "(`badge`). Signature: one patch-plate, a riveted chest ledger board with "
   "three ruled lines, and a stylus on a short cord.",
 "gun_bosun":
   "Runs the Bulwark's guns: rust shell (`suit`, `sleeve`), rust boots "
   "(`boot`), an amber hard hat (`helmet`) with a near-black visor (`visor`), "
   "a chest piece (`chest`), a belt (`belt`). Signature: patch-plates, a "
   "diagonal ammo bandolier with four shell loops, and the box respirator.",
 "foreman":
   "Runs the yard crew: ochre shell (`suit`), rust boots (`boot`), tan "
   "sleeves (`sleeve`), an amber hard hat (`helmet`), a pauldron "
   "(`shoulders`), a belt (`belt`), an amber badge (`badge`). Signature: "
   "patch-plates, a hi-vis amber foreman panel on the chest, one big left "
   "pauldron, and a clipboard on the right hip behind the arm.",
 "hauler":
   "Moves heavy freight by hand: sandy shell (`suit`), rust boots (`boot`), "
   "tan sleeves (`sleeve`), a back pack (`backpack`), a belt (`belt`), bare "
   "head. Signature: one patch-plate and a heavy load strap over each "
   "shoulder down to the waist.",
}
