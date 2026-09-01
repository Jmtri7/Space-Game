"""Sol Federation crew outfits, redrawn on the cinched-waist body with the
Federation signature: a regulation helmet with a horizontal visor slit + chin
guard (never a bubble), a white contrast centreline stripe, an amber
hazard-chevron shoulder flash, and a stencilled SF-### registration. Strokeless.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, rrect, offset_poly, bar, _u, _arm_rot

OUT = "#141219"
WAIST, BELT = 103, 99
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


def chevron_flash(x=81, side=1):
    """Amber hazard chevrons sitting on the (right) upper arm - authored at the
    straight-arm position, then rotated onto the splayed arm via _arm_rot."""
    o = []
    for k in range(3):
        y = 69 + k * 4
        o.append(poly([_arm_rot(1, px, py) for px, py in
                       [(x, y), (x + side * 4, y + 3), (x + side * 8, y),
                        (x + side * 7, y), (x + side * 4, y + 1.5), (x + side * 1, y)]], HAZ))
    return "".join(o)


def sf_stencil(num, y=100):
    return (f'<text x="70" y="{y}" fill="#8fb9c8" font-family="IBM Plex Mono, monospace" '
            f'font-size="7" text-anchor="middle" letter-spacing="0.5">SF-{num}</text>')


def SIG_HELM():
    """The visor-slit regulation helmet + chin guard - crew who wear a helmet."""
    return (poly([(56, 43), (84, 43), (82, 50), (58, 50)], DARK)
            + bar(57, 46, 83, 46, 1.0, "#8fb9c8")
            + op_s([(58, 53), (82, 53), (78, 61), (62, 61)], "#5a6b82"))


def SIG_LIVERY(num="000", stripe_to=WAIST):
    """White centreline stripe + amber chevron flash + SF-### stencil - on
    everyone, helmet or cap. The stripe starts at the collar (y66), clear of
    the chin and mouth."""
    return (poly([(68, 66), (72, 66), (72, stripe_to), (68, stripe_to)], STRIPE)
            + chevron_flash()
            + sf_stencil(num))


def SIG(num="000", stripe_to=WAIST):
    return SIG_HELM() + SIG_LIVERY(num, stripe_to)


# ---------------------------------------------------------------- outfits
def rating():
    return dict(helmet="#4a5a72", suit="#3a4a63", boot="#232c3a", collar=STRIPE), "", SIG("114")


def pilot():
    base = dict(helmet="#ced6dc", suit="#3a4658", boot="#282e38")
    post = (SIG("221", stripe_to=112)
            + rib([(53, 62), (70, 90), (87, 62)], 2.0, "#2b3542")                # flight harness
            + op_s(rrect(78, 142, 12, 16, 1), "#2b3542")                         # thigh checklist board
            + bar(80, 146, 88, 146, 0.9, "#8fb9c8") + bar(80, 150, 88, 150, 0.9, "#8fb9c8"))
    return base, "", post


def officer():
    base = dict(hat="#2e384a", helmet_r=17, suit="#2e384a", boot="#20262f",
                collar=STRIPE, shoulders="#28303e", coat=True)
    pre = (op_s([(49, WAIST), (91, WAIST), (95, 172), (45, 172)], "#28303e")     # frock coat skirt
           + op_s(rrect(85, BELT + 2, 7, 13, 1), DARK))                          # sidearm on the hip (behind arm)
    post = (SIG_LIVERY("O-2", stripe_to=WAIST)
            + poly([(53, 41), (87, 41), (81, 33), (74, 28), (66, 28), (59, 33)], "#2e384a")  # peaked cap
            + poly([(53, 41), (68, 41), (64, 37), (56, 37)], DARK)              # brim
            + "".join(bar(*_arm_rot(-1, 51, 110 + k * 5), *_arm_rot(-1, 59, 110 + k * 5), 1.4, HAZ) for k in range(3))  # cuff braid, left forearm
            + op_s(rrect(49, 65, 15, 6, 1), HAZ) + op_s(rrect(76, 65, 15, 6, 1), HAZ)   # shoulder boards
            + poly([(62, 80), (66, 85), (62, 90), (58, 85)], HAZ))              # command badge, left breast
    return base, pre, post


def marine():
    base = dict(helmet="#3c4550", suit="#2c333e", boot="#1a1e24", visor="#8fb9c8",
                backpack="#2a303a")
    post = (op_s([(56, 66), (84, 66), (82, 78), (58, 78)], "#48525f")           # carapace seg 1
            + op_s([(57, 82), (83, 82), (81, 96), (59, 96)], "#48525f")
            + op_s([(59, 100), (81, 100), (79, 114), (61, 114)], "#48525f")
            + "".join(circ(x, 68, 1.2, DARK) for x in (62, 70, 78))
            + chevron_flash(81, 1)
            + op_s(rrect(53, 168, 14, 10, 2), "#48525f") + op_s(rrect(70, 168, 14, 10, 2), "#48525f")  # shin guards
            + sf_stencil("M-07", y=98))
    return base, "", post


def gate_warden():
    base = dict(helmet="#4a5a72", suit="#3a4a63", boot="#232c3a", collar=STRIPE)
    post = (op_s([(58, 66), (82, 66), (80, 108), (60, 108)], HAZ)               # hi-vis over-vest
            + bar(60, 86, 80, 86, 1.4, "#c46a10")
            + poly([(64, 72), (76, 72), (76, 82), (64, 82)], DARK)              # SF badge on the vest
            + circ(70, 77, 2.0, GLASS)
            + poly([(56, 43), (84, 43), (82, 50), (58, 50)], DARK)              # visor slit
            + bar(57, 46, 83, 46, 1.0, "#8fb9c8")
            + rib([(90, 70), (93, 96), (91, 120)], 1.6, "#5a6b82")             # scanner wand
            + circ(91, 120, 2.0, GLASS)
            + op_s(rrect(48, 126, 12, 16, 1), "#2b3542"))                       # data slate in hand
    return base, "", post


def fleet_command():
    base = dict(hat="#dfe6ee", helmet_r=17, suit="#252d3c", boot="#181d26",
                collar=STRIPE, shoulders="#dfe6ee", coat=True)
    pre = op_s([(46, WAIST), (94, WAIST), (98, 178), (42, 178)], "#222a37")     # flag-officer greatcoat
    post = (SIG_LIVERY("FLAG", stripe_to=WAIST)
            + "".join(circ(x, y, 1.6, HAZ) for x in (64, 76) for y in (72, 82, 92, 102))  # double-breasted buttons
            + op_s(rrect(48, 64, 16, 7, 1), HAZ) + op_s(rrect(76, 64, 16, 7, 1), HAZ)   # heavy boards
            + "".join(bar(50, 66 + k, 60, 66 + k, 0.9, "#252d3c") for k in (0, 2, 4))   # board rank lines, L
            + "".join(bar(80, 66 + k, 90, 66 + k, 0.9, "#252d3c") for k in (0, 2, 4))   #                   R (mirrored)
            + poly([(52, 35), (88, 35), (92, 29), (83, 22), (57, 22), (48, 29)], "#252d3c")  # scrambled-egg cap
            + poly([(52, 35), (72, 35), (68, 31), (56, 31)], DARK)
            + "".join(poly([(54 + i * 3, 31), (57 + i * 3, 28), (60 + i * 3, 31)], HAZ) for i in range(4))  # cap braid
            + poly([(62, 80), (67, 85), (62, 90), (57, 85)], HAZ))              # flag badge, left breast
    return base, pre, post


OUTFITS = {
 "rating": (rating, "Issue Rating", "the crew every ship and station runs on"),
 "pilot": (pilot, "Issue Pilot", "small craft, shuttles, the Cutter"),
 "officer": (officer, "Fleet Officer", "watch command, a bridge, a wardroom"),
 "marine": (marine, "Fleet Marine", "boarding, the brig, gate security"),
 "gate_warden": (gate_warden, "Gate Warden", "customs & the transponder log"),
 "fleet_command": (fleet_command, "Fleet Command", "the flag tier - Procyon Gate control"),
}

# Full read-out of every drawn piece per outfit. Every Federation outfit carries
# the shared signature: a horizontal visor-slit helmet (dark slit + cyan line +
# chin guard), a white centreline stripe from the collar down, an amber
# hazard-chevron flash on the right upper arm, and a stencilled SF-### number.
DETAILS = {
 "rating":
   "Blue issue coveralls (`suit`), dark boots (`boot`), a blue-grey helmet "
   "(`helmet`), a white collar (`collar`). Signature: the visor-slit helmet, "
   "the white centreline stripe, the amber chevron flash on the right arm, and "
   "an `SF-114` stencil.",
 "pilot":
   "Light-grey flight helmet (`helmet`), slate suit (`suit`), dark boots "
   "(`boot`). Signature: visor-slit helmet, centreline stripe (to mid-torso), "
   "chevron flash, `SF-221` stencil — plus an X flight harness across the "
   "chest and a checklist board on the right thigh with two cyan lines.",
 "officer":
   "A dark-navy frock coat (`suit`, `coat` cut), near-black boots (`boot`), a "
   "peaked cap (`hat`), a white collar (`collar`), dark epaulettes "
   "(`shoulders`). Signature: centreline stripe and chevron flash — plus the "
   "coat skirt to mid-shin, a holstered sidearm on the right hip behind the "
   "arm, a peaked cap with a dark brim, three amber cuff-braid rings on the "
   "left forearm, an amber rank board on each shoulder, and an amber command "
   "diamond on the left breast.",
 "marine":
   "Boarding armour (`suit`), black boots (`boot`), a dark helmet (`helmet`) "
   "with a cyan visor (`visor`), a back pack (`backpack`). Signature: the "
   "chevron flash and an `M-07` stencil — plus three stacked carapace segments "
   "with three rivet dots and a shin guard on each leg.",
 "gate_warden":
   "Blue-grey uniform (`suit`), dark boots (`boot`), a helmet (`helmet`), a "
   "white collar (`collar`). Signature: the visor-slit helmet — plus a hi-vis "
   "amber over-vest with a dark `SF` badge and a cyan lamp, a scanner wand "
   "held down the right side with a glass tip, and a data slate in the left "
   "hand.",
 "fleet_command":
   "A flag-officer greatcoat (`suit`, `coat` cut), near-black boots (`boot`), "
   "a white cap (`hat`), a white collar (`collar`), white epaulettes "
   "(`shoulders`). Signature: centreline stripe, chevron flash, a `FLAG` "
   "stencil — plus the greatcoat to the shin, a double-breasted grid of gold "
   "buttons (two columns of four), a heavy gold rank board on each shoulder "
   "with three lines, a 'scrambled-egg' cap with a dark brim and gold braid, "
   "and a gold flag diamond on the left breast.",
}
