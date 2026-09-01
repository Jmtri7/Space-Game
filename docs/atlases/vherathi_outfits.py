"""Vherathi Concord outfits, on the cinched-waist body with the Vherathi
signature: a grown helmet dome carrying ASYMMETRIC CLUSTERS of circular
eye-bubbles (never one visor), a branching resin-vein glow tracing up the
torso and one arm, and one-sided grown fittings. Strokeless.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, offset_poly

OUT = "#141219"
WAIST = 103
METAL, GLASS, DARK = "#4a3060", "#8fffcf", "#2f1e3c"


def op_s(pts, fill, d=1.1, ol=OUT):
    return poly(offset_poly(pts, d), ol) + poly(pts, fill)


def _dome_pts():
    """A rounded grown helmet dome that hugs the head (circle r14 at 70,45.6)
    and comes down past the ear line - bigger radius on the left (grown side)."""
    cx, cy = 70, 45
    pts = []
    for a in range(200, 341, 14):          # crown arc, left temple -> right temple
        r = 18.0 if a < 270 else 16.4      # left side grown a touch fuller
        pts.append((cx + r * math.cos(math.radians(a)),
                    cy + r * math.sin(math.radians(a))))
    # down each side past the ears, then a soft jaw line under the chin bulge
    pts += [(84, 55), (79, 58), (70, 57), (61, 58), (56, 55)]
    return pts


def eye_bubbles(dome=METAL, left=((60, 41, 3.4), (58, 49, 2.6), (64, 47, 2.2), (61, 35, 2.4)),
                right=((80, 39, 3.0), (82, 47, 2.0))):
    """The signature - a rounded grown dome (covers the ears) + clustered bubbles."""
    o = [op_s(_dome_pts(), dome)]
    for bx, by, br in left + right:
        o.append(circ(bx, by, br + 1.0, OUT))
        o.append(circ(bx, by, br, GLASS))
        o.append(circ(bx - br * 0.3, by - br * 0.3, br * 0.35, "#e8fff5"))
    return "".join(o)


def veins(from_pt=(70, WAIST), branches=None, nodes=None):
    """Resin-node glow up the torso (asymmetric clusters of small grown
    beads, no connecting filaments - a thin polyline just turns to mint
    mush at sprite scale, so the beads carry it alone)."""
    nodes = nodes or [(64, 66, 2.0), (60, 76, 1.5), (66, 86, 1.3),
                      (59, 97, 1.7), (64, 106, 1.2), (74, 92, 1.4)]
    o = []
    for nx, ny, nr in nodes:
        o.append(circ(nx, ny, nr + 0.8, OUT))
        o.append(circ(nx, ny, nr, GLASS))
        o.append(circ(nx - nr * 0.3, ny - nr * 0.3, nr * 0.4, "#e8fff5"))
    return "".join(o)


# ---------------------------------------------------------------- outfits
def hardsuit():
    return dict(suit="#483060", boot="#2f1e3c", sleeve="#3f2a54"), "", eye_bubbles("#7a5c96") + veins()


def softsuit():
    base = dict(no_helmet=True, suit="#6e5580", boot="#96789e", sleeve="#5a4272")
    # softsuits: no dome, the eye-bubbles are worn as a light half-mask on one side
    post = ("".join(circ(x, y, r + 1, OUT) + circ(x, y, r, GLASS)
                    for x, y, r in ((62, 46, 2.6), (60, 52, 2.0), (65, 50, 1.6)))
            + veins(branches=[[(78, WAIST), (76, 118), (80, 96), (84, 74)],
                              [(80, 96), (88, 90), (92, 86)]]))
    return base, "", post


def reefwright():
    base = dict(suit="#7d628c", boot="#4a3060", sleeve="#6a5080",
                shoulders="#4a3060", shoulders_side="left")
    post = (eye_bubbles("#7a5c96")
            + op_s([(52, 65), (58, 62), (64, 80), (72, 95), (83, WAIST + 2),
                    (77, WAIST + 9), (66, 96), (58, 82), (48, 68)], GLASS)         # tool baldric, shoulder to opposite hip
            + "".join(circ(56 + i * 6, 72 + i * 9, 1.6, DARK) for i in range(4))   # tool clips down it
            + veins())
    return base, "", post


def vault_warden():
    base = dict(suit="#4a3060", boot="#2f1e3c", sleeve="#3f2a54",
                spikes="#96ffd7", spikes_side="uneven",
                chest="#3a264e", belt="#2f1e3c")
    post = (eye_bubbles("#7a5c96", left=((59, 42, 3.6), (57, 51, 2.8), (63, 49, 2.2),
                                         (60, 34, 2.6), (65, 40, 1.8)), right=((81, 44, 2.4),))
            + op_s([(49, 66), (54, 64), (56, 118), (52, 134), (48, 122), (47, 88)], "#8fffcf")  # grown guard-blade down the left forearm
            + veins())
    return base, "", post


def tide_pilot():
    base = dict(helmet="#cdd2de", visor="#8fffcf", suit="#4a3060", boot="#2f1e3c",
                sleeve="#3f2a54", collar="#96ffd7")
    # the pilot keeps a bubble cluster grown onto the flight helmet, off to one side
    post = ("".join(circ(x, y, r + 1, OUT) + circ(x, y, r, GLASS)
                    for x, y, r in ((84, 44, 2.6), (86, 50, 1.8), (81, 48, 1.6)))
            + veins(branches=[[(70, 96), (66, 84), (62, 70)], [(66, 84), (58, 80), (54, 78)]]))
    return base, "", post


def envoy():
    base = dict(no_helmet=True, suit="#5a4270", boot="#96789e", sleeve="#4a3660",
                collar="#96ffd7", sash="#8fffcf", badge="#ffffff")
    post = (eye_bubbles("#6a5286", left=((60, 45, 3.0), (58, 52, 2.2), (63, 40, 2.0)),
                        right=((80, 44, 2.6), (82, 50, 1.8)))
            + veins(branches=[[(78, WAIST), (76, 118), (80, 94), (82, 72)]]))
    return base, "", post


def magistrate():
    base = dict(helmet="#96789e", suit="#3c2854", boot="#28183a", coat=True,
                chest="#604a6e", collar="#96ffd7", sash="#96789e", badge="#8fffcf")
    pre = op_s([(46, WAIST), (94, WAIST), (100, 174), (44, 172)], "#33234a")     # long robe, asymmetric hem
    post = (eye_bubbles("#7a5c96", left=((59, 43, 3.4), (57, 51, 2.6), (63, 48, 2.0),
                                         (61, 36, 2.2), (66, 43, 1.6), (55, 44, 1.4)),
                        right=((82, 45, 2.2),))
            + veins(branches=[[(70, WAIST), (66, 118), (62, 94), (58, 70)],
                              [(62, 94), (54, 88), (48, 86)],
                              [(66, 118), (76, 106), (82, 92)]]))
    return base, pre, post


OUTFITS = {
 "hardsuit": (hardsuit, "Hardsuit", "the standard grown vacsuit"),
 "softsuit": (softsuit, "Softsuit", "station wear - no dome"),
 "reefwright": (reefwright, "Reefwright", "grows and tends the hulls"),
 "vault_warden": (vault_warden, "Vault-Warden", "guards the light-vaults"),
 "tide_pilot": (tide_pilot, "Tide-Pilot", "flies the skiffs and tenders"),
 "envoy": (envoy, "Envoy", "speaks for the Concord off-world"),
 "magistrate": (magistrate, "Magistrate", "the Concord's judgment, worn"),
}
