"""Vherathi Concord outfits, on the Grounded body.

The Concord's kit is GROWN, not made: resin shells cultured on the wearer, so
nothing is symmetric and nothing has a seam. Three things carry the culture,
and every outfit uses at least two of them:

  - the DOME: a grown helm hugging the skull, always fuller on one side, with
    an asymmetric CLUSTER of glass eye-bubbles on it. Never a single visor.
  - the VEIN: a tapered resin runner rising from the hip, over a shoulder or
    down an arm, with luminous beads riding along it. It is a ribbon, not a
    row of floating dots - the beads sit ON something.
  - the CARAPACE: grown plates and vanes over one shoulder or one side of the
    chest, never both, so the silhouette is lopsided on purpose.

Strokeless, and drawn WITHOUT OUTLINES: where two shapes of the same colour
meet, the separation is a shade on the far side of one of them (the same one
light direction the body carries), not a line between them.

These signatures are authored in the pre-Grounded figure space and drawn
through gen_si.fig_remap() - see common_kit.py's header for the anchors and
the refit checklist. Head and arm work should go through the helpers
(head_dome, hand_shape, arm_top), which return coordinates already mapped.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import (poly, circ, ngon, _arm_rot, head_shell, hand_shape,
                    arm_top)

WAIST = 103
BELT = 99

# resin violets, and the mint the Concord grows for light
SHELL, SHELL_D = "#5a3f78", "#3f2a54"
GLASS, GLASS_HI, GLASS_LO = "#8fffcf", "#e8fff5", "#3f8f74"
MINT, DARK = "#96ffd7", "#2f1e3c"
COLLAR = "#6fd8b4"   # the mint the Concord wears, a step down from the glow


def _rgb(c):
    c = c.lstrip("#")
    return [int(c[i:i + 2], 16) for i in (0, 2, 4)]


def _tone(col, m, a):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v * m + a))) for v in _rgb(col))


def sh(col):
    """The far side of a grown surface - one step down, same hue."""
    return _tone(col, 0.70, 2)


def lt(col):
    """The lit side."""
    return _tone(col, 1.14, 22)


def far_side(pts, cx, depth=0.55):
    """The shade on the far side of a grown surface - the crescent that
    replaces an outline where two same-coloured pieces meet.

    The shape is clipped to x >= cx (so it works on any polygon, not just one
    whose vertices happen to straddle the centre) and the inner edge is pulled
    in by a width that tapers to nothing at both ends. A constant inset reads
    as a seam ruled down the middle of the piece, which on a helm looks like a
    join - and a grown helm has no joins."""
    out, n = [], len(pts)
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        p_in, q_in = p[0] >= cx, q[0] >= cx
        if p_in:
            out.append(p)
        if p_in != q_in:
            t = (cx - p[0]) / (q[0] - p[0])
            out.append((cx, p[1] + t * (q[1] - p[1])))
    if len(out) < 3:
        return []
    ys = [p[1] for p in out]
    y0, span = min(ys), (max(ys) - min(ys)) or 1.0
    inner = [(cx + (x - cx) * (1 - depth * max(0.0, math.sin(math.pi * (y - y0) / span)) ** 0.55), y)
             for x, y in out]
    return out + inner[::-1]


def shade_of(pts, cx, depth, col):
    """far_side as drawn - empty when the piece has no far side to shade."""
    band = far_side(pts, cx, depth)
    return poly(band, col) if len(band) >= 3 else ""


def ribbon(pts, w0, w1):
    """A tapered band along a polyline - the shape a grown runner takes."""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        q, o = pts[min(i + 1, n - 1)], pts[max(i - 1, 0)]
        dx, dy = q[0] - o[0], q[1] - o[1]
        m = math.hypot(dx, dy) or 1.0
        w = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
        left.append((x - dy / m * w, y + dx / m * w))
        right.append((x + dy / m * w, y - dx / m * w))
    return left + right[::-1]


# ------------------------------------------------------------- the signature
def bubble(x, y, r):
    """A grown glass eye-bubble: mint glass, the far side shaded, a catchlight
    on the near one."""
    ring = ngon(x, y, r, r, 14)
    return (poly(ring, GLASS)
            + shade_of(ring, x, 0.72, GLASS_LO)
            + circ(x - r * 0.34, y - r * 0.34, r * 0.34, GLASS_HI))


def dome(col, bubbles, out=2.4, grow=1.10):
    """The grown helm: the whole head silhouette swelled a little, and swelled
    a little more on the grown side. A dome cut off with a flat hem reads as a
    bucket; this keeps the head's own egg, chin included."""
    pts = head_shell(out, grow)
    o = [poly(pts, col), shade_of(pts, 70, 0.62, sh(col))]
    # a wet highlight down the grown side, following the shell
    o.append(poly(ribbon([(58.6, 33), (56.0, 40), (55.8, 47)], 2.6, 1.2), lt(col)))
    for bx, by, br in bubbles:
        o.append(bubble(bx, by, br))
    return "".join(o)


def vein(path, beads, w0=3.2, w1=1.1, col=None):
    """A resin runner with luminous beads riding it. The runner carries the
    beads; loose beads on their own read as specks at sprite size."""
    col = col or SHELL_D
    o = [poly(ribbon(path, w0, w1), col),
         shade_of(ribbon(path, w0, w1), sum(p[0] for p in path) / len(path), 0.5, sh(col))]
    for i, (bx, by, br) in enumerate(beads):
        o.append(circ(bx, by, br, GLASS))
        o.append(circ(bx - br * 0.3, by - br * 0.3, br * 0.38, GLASS_HI))
    return "".join(o)


def plate(pts, col):
    """A grown carapace plate, shaded on its far side."""
    cx = sum(p[0] for p in pts) / len(pts)
    return poly(pts, col) + shade_of(pts, cx, 0.58, sh(col))


def vanes(x, y, n, ln, a0, spread, col):
    """A fan of grown vanes - gill-fins over a shoulder."""
    o = []
    for i in range(n):
        a = math.radians(a0 + spread * (i / max(1, n - 1) - 0.5))
        tx, ty = x + ln * math.cos(a), y - ln * math.sin(a)
        o.append(poly(ribbon([(x, y), ((x + tx) / 2, (y + ty) / 2), (tx, ty)], 5.2, 0.8), col))
        o.append(poly(ribbon([(x, y), (tx, ty)], 1.6, 0.5), sh(col)))
    return "".join(o)


CLUSTER_L = ((62, 43, 2.6), (59.5, 49, 2.0), (65.5, 47.5, 1.5), (63, 37, 1.7))
CLUSTER_R = ((78.5, 42, 2.1), (80, 48, 1.4))
TORSO_VEIN = [(78, WAIST + 4), (79, 92), (76, 80), (70, 70), (62, 66)]
TORSO_BEADS = ((78, 100, 1.9), (78.5, 90, 1.5), (75, 79, 1.7), (69, 69.5, 1.4), (63, 66, 2.1))


# ---------------------------------------------------------------- outfits
def hardsuit():
    """The standard grown vacsuit."""
    base = dict(suit=SHELL, boot=DARK, sleeve=SHELL_D)
    post = (dome("#6b4c8e", CLUSTER_L + CLUSTER_R)
            + plate([(56, 70), (68, 68), (70, 92), (58, 96)], "#4a3266")   # left chest carapace
            + vanes(*arm_top(-1), 3, 13, 118, 46, "#4a3266")
            + vein(TORSO_VEIN, TORSO_BEADS))
    return base, "", post


def softsuit():
    """Station wear - no dome; the bubbles are worn as a half-mask."""
    base = dict(no_helmet=True, suit="#7a5f92", boot="#a486ab", sleeve="#66497e",
                hair="bun", hair_col="#2e1f3e")
    post = (plate([(54, 40), (66, 37), (68, 52), (56, 55)], "#5d4276")       # grown half-mask, left
            + "".join(bubble(x, y, r) for x, y, r in ((59, 44, 3.0), (57, 51, 2.2), (64, 48, 1.7)))
            + vein([(84, 118), (86, 104), (84, 90), (78, 76)],
                   ((85, 114, 1.7), (85.5, 101, 1.4), (82, 88, 1.6), (78.5, 77, 1.2)),
                   w0=2.6, w1=1.0, col="#5d4276"))
    return base, "", post


def reefwright():
    """Grows and tends the hulls."""
    base = dict(suit="#7d628c", boot="#4a3060", sleeve="#6a5080")
    loops = "".join(poly(ngon(56 + i * 7, 70 + i * 9.5, 2.4, 2.4, 10), DARK)
                    for i in range(4))
    post = (dome("#8467a4", CLUSTER_L + CLUSTER_R)
            + vein([(52, 66), (60, 80), (70, 94), (82, WAIST + 4)],
                   (), w0=6.0, w1=4.4, col="#5d4276")                        # tool baldric
            + loops
            + plate(hand_shape(1, 1.1), "#5d4276")                           # grown work gauntlet
            + vein(TORSO_VEIN, TORSO_BEADS))
    return base, "", post


def vault_warden():
    """Guards the light-vaults."""
    base = dict(suit="#4a3060", boot=DARK, sleeve=SHELL_D, belt=DARK)
    post = (vanes(*arm_top(-1), 3, 15, 116, 40, "#4a3266")            # grown crest
            + dome("#63458a", ((61, 43, 2.8), (58.5, 50, 2.1), (65, 48, 1.6),
                               (62.5, 36, 1.9), (67, 42, 1.3)) + ((79, 44, 1.8),),
                   out=3.0, grow=1.14)
            + plate([(55, 68), (70, 65), (72, 96), (57, 99)], "#3a264e")     # heavy left carapace
            + plate([_arm_rot(-1, x, y) for x, y in
                     [(53, 84), (58, 83), (58.5, 116), (55.5, 126), (52.5, 117)]],
                    "#63c9a4")                                        # grown guard-blade
            + vein(TORSO_VEIN, TORSO_BEADS))
    return base, "", post


def tide_pilot():
    """Flies the skiffs and tenders."""
    base = dict(helmet="#cdd2de", visor=GLASS, suit="#4a3060", boot=DARK,
                sleeve=SHELL_D, collar=COLLAR)
    post = ("".join(bubble(x, y, r) for x, y, r in ((83, 42, 2.7), (85.5, 48, 1.9), (80, 47, 1.5)))
            + vanes(88, 34, 3, 10, 24, 40, "#5d4276")                        # fin off the helm
            + "".join(poly(ribbon([(58, 72 + i * 9), (70, 76 + i * 9), (82, 72 + i * 9)], 3.0, 3.0),
                           "#3f2a54") for i in range(3))                     # grown rib harness
            + vein([(76, WAIST), (74, 90), (68, 78)],
                   ((75, 98, 1.6), (72, 85, 1.4), (68, 78, 1.8)), w0=2.6, w1=1.2))
    return base, "", post


def envoy():
    """Speaks for the Concord off-world."""
    base = dict(no_helmet=True, suit="#5a4270", boot="#96789e", sleeve="#4a3660",
                collar=COLLAR, badge="#ffffff", hair="long", hair_col="#2a1b38")
    post = (vein([(50, 64), (58, 76), (66, 94), (72, WAIST + 8)],
                 (), w0=7.0, w1=5.0, col="#6b5182")                          # grown stole, one shoulder
            + "".join(bubble(x, y, r) for x, y, r in
                      ((61, 33, 2.4), (66, 31, 1.8), (56, 36, 1.9), (71, 32, 1.4)))  # brow circlet
            + vein([(82, 116), (83, 100), (79, 86)],
                   ((82.5, 112, 1.6), (82, 99, 1.3), (79, 87, 1.7)), w0=2.4, w1=1.0))
    return base, "", post


def magistrate():
    """The Concord's judgment, worn."""
    base = dict(suit="#3c2854", boot="#28183a", coat=True, collar=COLLAR, badge=GLASS)
    _sk = [(50, WAIST), (90, WAIST), (95, 174), (45, 172)]
    pre = poly(_sk, "#33234a")
    post = (dome("#5b3f7e", ((61, 44, 2.6), (58.6, 50, 2.0), (65, 48.5, 1.5),
                             (63, 37, 1.7), (67.5, 43, 1.2), (57, 44, 1.1)) + ((79.5, 45, 1.6),),
                 out=3.0, grow=1.18)
            + plate([(50, 68), (70, 63), (72, 88), (52, 94)], "#4a3266")     # mantle, deep on the left
            + plate([(72, 64), (86, 68), (85, 84), (73, 82)], "#41295c")     #        shallow on the right
            + "".join(bubble(x, y, r) for x, y, r in
                      ((60, 78, 2.0), (55, 86, 1.5), (65, 88, 1.6), (58, 96, 1.3)))
            + vein([(80, WAIST + 2), (81, 92), (77, 82)],
                   ((80.5, 99, 1.6), (80, 90, 1.3)), w0=2.6, w1=1.1))
    from common_kit import skirt_over_legs
    return base, pre, skirt_over_legs(_sk, "#33234a") + post


OUTFITS = {
 "hardsuit": (hardsuit, "Hardsuit", "the standard grown vacsuit"),
 "softsuit": (softsuit, "Softsuit", "station wear - no dome"),
 "reefwright": (reefwright, "Reefwright", "grows and tends the hulls"),
 "vault_warden": (vault_warden, "Vault-Warden", "guards the light-vaults"),
 "tide_pilot": (tide_pilot, "Tide-Pilot", "flies the skiffs and tenders"),
 "envoy": (envoy, "Envoy", "speaks for the Concord off-world"),
 "magistrate": (magistrate, "Magistrate", "the Concord's judgment, worn"),
}

# What each outfit is made of. The Concord signature is the grown DOME with an
# asymmetric cluster of glass eye-bubbles, the resin VEIN - a tapered runner
# carrying luminous beads, so the beads sit on something - and grown CARAPACE
# plates or vanes weighted to one side.
DETAILS = {
 "hardsuit":
   "The standard grown vacsuit: resin-violet shell (`suit`), dark boots "
   "(`boot`) and sleeves (`sleeve`). Signature: the grown dome, fuller on the "
   "left, with a six-bubble asymmetric cluster and a wet highlight down the "
   "grown side; a carapace plate over the left chest; three gill-vanes over "
   "the left shoulder; and a resin vein rising from the right hip to the "
   "collar with five beads riding it.",
 "softsuit":
   "Station softsuit, no dome: lilac shell (`suit`), pale boots (`boot`), "
   "muted sleeves (`sleeve`), hair worn up. Signature: a grown resin patch "
   "over the left of the face carrying a three-bubble half-mask, and a vein "
   "with four beads up the right flank.",
 "reefwright":
   "The hull-grower's suit: mauve shell (`suit`), purple boots (`boot`) and "
   "sleeves (`sleeve`). Signature: the dome and its cluster; a wide grown "
   "baldric from the left shoulder to the right hip with four dark tool loops "
   "down it; a grown work gauntlet over the right hand; and the torso vein.",
 "vault_warden":
   "Vault guard: deep-violet shell (`suit`, `boot`, `sleeve`), uneven grown "
   "spikes (`spikes` + `spikes_side`), a belt (`belt`). Signature: a large "
   "left-weighted six-bubble cluster on a heavier dome, a thick carapace over "
   "the left chest, a mint guard-blade grown down the left forearm, and the "
   "torso vein.",
 "tide_pilot":
   "The skiff pilot: a flight helmet (`helmet`) with a mint visor (`visor`), "
   "violet suit (`suit`, `boot`, `sleeve`), a mint collar (`collar`). "
   "Signature: a three-bubble cluster grown onto the right of the helmet, a "
   "vane fin off its back, three grown ribs across the chest, and a short "
   "vein to the collar.",
 "envoy":
   "The off-world envoy, bare-headed with long hair: violet robe-suit "
   "(`suit`), pale boots (`boot`), a mint collar (`collar`), a white badge "
   "(`badge`). Signature: a grown stole over the left shoulder falling to the "
   "opposite hip, a four-bubble circlet across the brow, and a vein up the "
   "right flank.",
 "magistrate":
   "The Concord's judgment: a long asymmetric robe (`suit`, `coat` cut), dark "
   "boots (`boot`), a mint collar (`collar`), a glass badge (`badge`). "
   "Signature: the heaviest dome and a seven-bubble cluster, a grown mantle "
   "deep over the left shoulder and shallow over the right, a constellation "
   "of four bubbles across the chest, and a short vein at the right hip.",
}
