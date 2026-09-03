"""Signature layers for the Common Kit atlas - the culture-neutral civilian
and service outfits from graphics.json, each given a role-distinguishing
detail on top of the shared figure_parts body (a mechanic's tool belt, a
smuggler's hood, a surgeon's mask...). Strokeless <polygon>/<circle>.

build_outfit(key) -> (base_opts, pre_svg, post_svg)
composed by gen_common.py as:  grid + pre + figure_parts(**base) + post

REFITTING AN OUTFIT - read this before moving anything.

These signatures are authored against the PREVIOUS figure space and are drawn
through gen_si.fig_remap(), which maps the old anchor lines onto the Grounded
body's. x is untouched; y is remapped piecewise. Keep new work in these
coordinates - or re-author the whole file and drop the adapter.

  Old anchors (what you type here):
    collar/yoke y66 . shoulder cap y69 . chest y72-106 . waist y103 .
    belt y99 . coat hem y152 . hip y139 . knee y158 . ankle y194 .
    arms x50-60 / x80-90 . hands (57/83, 133) . bare head (70, 46) r14

  Where things actually land (what the reader sees), and the three facts that
  catch most refits out:
    - the ARMS HANG CLOSE: x50-56 and x84-90 at the waist, over a torso only
      x57-83 wide. Anything wider than the torso crosses a sleeve. Hip kit
      (holster, canteen, baton, satchel, pouch) goes in `pre`, so the near arm
      covers it; only its outer sliver should show.
    - the HEAD IS SMALL: about 22 wide and 27 tall. A hood or brim drawn much
      wider than that reads as baggy.
    - a COAT (`coat=True`) puts BOTH legs behind the torso, so the coat's
      own body covers them down to its hem. The skirt below that still needs
      repeating: put it in `pre` and pass it through skirt_over_legs(), which
      cuts at the hem and puts the hands back on top. Prepend the result to
      `post` so the outfit's own detail still lands over the coat.

  Don't guess at the body - ask it. These come back in atlas coordinates,
  already inverse-mapped, so they can be used from this file directly:
    hand_shape(s, grow)   the mitt, for a glove that covers the hand
    arm_top(s)            the centre of the arm's domed top, for a pad
    head_band_fig(y0, y1) a band whose sides follow the skull, for a mask
                          or a visor (y is in the NEW space - see gen_si)
    head_dome(out, y_bot) a dome over the head and its hair, for a hood
    _arm_rot(s, x, y)     a point carried onto the splayed arm
  And don't draw a second hat over the `helmet` shell: drop the helmet key
  and let the signature's own headgear be the headgear, or the shell's brim
  shows underneath it as a stray line.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import (poly, circ, ngon, rrect, opoly, ocirc, bar, offset_poly, _u,
                    _arm_rot, hand_shape, head_band_fig, head_dome, SKINF)

OUT = "#141219"
WAIST = 103
BELT = 99


def rib(pts, w, col, op=None):
    pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    if len(pts) < 2:
        return ""
    n = len(pts)
    left, right = [], []
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
        left.append((pts[i][0] + nb[0] * w, pts[i][1] + nb[1] * w))
        right.append((pts[i][0] - nb[0] * w, pts[i][1] - nb[1] * w))
    return poly(left + right[::-1], col, op=op)


COAT_CUT = 147         # a shade above the coat's own hem: the remap places a
                       # shape by its centre, so a cut exactly on the hem can
                       # land a unit or two below it and leave a gap


def skirt_over_legs(pts, col):
    """The part of a coat skirt below the coat's hem, repeated in `post` so it
    falls over the legs instead of behind them.

    The whole skirt can't live in `post` - it would bury the arms - and in
    `pre` alone the NEAR leg is drawn on top of it, since figure_parts draws
    that leg after the torso. Cutting at the hip covers the leg for its whole
    length; it also catches the hands, so those are drawn back on afterwards.
    Put the result at the FRONT of `post`, so the outfit's own detail still
    lands on top of the coat."""
    out, n = [], len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        a_in, b_in = a[1] >= COAT_CUT, b[1] >= COAT_CUT
        if a_in:
            out.append(a)
        if a_in != b_in:
            t = (COAT_CUT - a[1]) / (b[1] - a[1])
            out.append((a[0] + t * (b[0] - a[0]), COAT_CUT))
    if len(out) < 3:
        return ""
    return (op_s(out, col)
            + op_s(hand_shape(-1), SKINF, d=1.0) + op_s(hand_shape(1), SKINF, d=1.0))


def dots(x0, y0, x1, y1, n, r, col):
    return "".join(circ(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1), r, col)
                   for i in range(n))


def op_s(pts, fill, d=1.2, ol=OUT):
    return opoly(pts, fill, d=d, ol=ol)      # honours gen_si.set_outline


def star(cx, cy, r, col, n=5):
    pts = []
    for k in range(2 * n):
        a = -math.pi / 2 + math.pi * k / n
        rr = r if k % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return op_s(pts, col, d=0.9)


def toolbelt(col):
    """A low-slung utility belt with pouches + loops, over the waist belt."""
    o = [op_s(rrect(58, BELT + 2, 24, 8, 2), col)]
    for x in (59, 66, 74):
        o.append(op_s(rrect(x, BELT + 8, 6, 9, 1), col))
    for x in (72, 80):
        o.append(bar(x, BELT + 3, x, BELT + 12, 1.4, "#2a2a2e"))
    return "".join(o)


# (the hard hat itself now comes from figure_parts' `helmet` key - a shell
# drawn over the head with its own brim, rib, strap and lamp - so the
# signature layers no longer draw one)


# ---------------------------------------------------------------- outfits
def space_suit():
    return dict(helmet="#96969b", suit="#5a5a60", boot="#46464a"), "", ""


def flight_suit():
    base = dict(helmet="#ced6dc", suit="#3a4658", boot="#282e38")
    post = (rib([(56, 68), (84, 100)], 2.0, "#2b3542")                 # chest harness, X-straps
            + rib([(84, 68), (56, 100)], 2.0, "#2b3542")
            + op_s(rrect(75, 142, 11, 15, 1), "#2b3542")               # thigh checklist board
            + bar(77, 146, 84, 146, 0.9, "#8fb9c8") + bar(77, 150, 84, 150, 0.9, "#8fb9c8")
            + op_s(rrect(75, 41, 7, 6, 1), "#2b3542")                  # helmet comms box
            + circ(78.5, 44, 1.2, "#e15a5a"))
    return base, "", post


def mechanic():
    base = dict(helmet="#f0aa37", lamp=True, suit="#524e48", boot="#2e2a26")
    post = (toolbelt("#3a352f")
            + op_s([_arm_rot(-1, x, y) for x, y in
                    [(53.8, 102), (60.4, 102), (60.4, 117), (53.8, 117)]], "#3a352f")  # rolled sleeve cuff L
            + op_s(rrect(55, 150, 11, 9, 2), "#3a352f")
            + op_s(rrect(74, 150, 11, 9, 2), "#3a352f"))                    # knee pads
    return base, "", post


def dockworker():
    base = dict(helmet="#f2962a", suit="#465060", boot="#2a303a")
    # hi-vis tabard over the suit (front panel + shoulder straps)
    pre = ""
    post = (op_s([(58, 68), (82, 68), (80, 110), (60, 110)], "#f2962a")     # hi-vis tabard front
            + bar(60, 88, 80, 88, 1.6, "#c46a10")
            + op_s([(57, 64), (64, 64), (62, 84), (55, 84)], "#f2962a")     # strap L
            + op_s([(76, 64), (83, 64), (85, 84), (78, 84)], "#f2962a")     # strap R
            + op_s(hand_shape(-1, 0.18), "#2a303a", d=1.0)
            + op_s(hand_shape(1, 0.18), "#2a303a", d=1.0))                  # heavy gloves
    return base, pre, post


def miner():
    base = dict(helmet="#ebcd5f", lamp=True, suit="#7a6648", boot="#483828")
    pre = op_s(rrect(49, 60, 42, 60, 5), "#5c4d34")                          # life-support backpack
    pre = (pre + rib([(88, 62), (90, 92), (88, 126)], 2.0, "#6a5a3c")        # drill stem down the back-right
           + poly([(85, 124), (93, 126), (89, 138)], "#3a2e1e")              # drill bit
           + op_s(rrect(76, 108, 11, 13, 2), "#463826"))                     # ore-sample pouch (behind the arm)
    post = (toolbelt("#463826")
            + bar(56, 154, 66, 154, 1.4, "#5c4d34"))
    return base, pre, post


def security():
    base = dict(helmet="#606874", suit="#3a3f48", boot="#24272e", visor="#8fb9c8")
    post = (op_s([(56, 68), (84, 68), (82, 104), (58, 104)], "#2c3038")     # padded vest
            + bar(59, 80, 81, 80, 1.2, "#4a505a") + bar(59, 91, 81, 91, 1.2, "#4a505a")
            + op_s(rrect(53, 66, 7, 6, 1), "#20232a") + circ(56.5, 69, 1.3, "#8fb9c8"))  # shoulder radio
    pre = op_s(rrect(79, BELT + 2, 5, 19, 1), "#20232a")                        # baton (behind the arm)
    return base, pre, post


def station_command():
    base = dict(no_helmet=True, suit="#2e384a", boot="#222832", collar="#dce1eb",
                shoulders="#28303e", badge="#ebcd5f")
    # double-breasted tunic: two rows of buttons + rank boards + a breast badge
    post = ("".join(circ(x, y, 1.4, "#ebcd5f") for x in (64, 76) for y in (74, 84, 94, 104))
            + op_s(rrect(52, 66.5, 13, 5, 1), "#ebcd5f")                            # rank boards, running
            + op_s(rrect(75, 66.5, 13, 5, 1), "#ebcd5f")                            # from the collar to the pad
            + "".join(bar(53.5, 68 + k, 62, 68 + k, 0.8, "#2e384a") for k in (0, 2.4))
            + "".join(bar(78, 68 + k, 86.5, 68 + k, 0.8, "#2e384a") for k in (0, 2.4))
            + op_s(head_dome(2.6, 29.5), "#2e384a")                                 # peaked cap
            + poly([(55, 41), (69, 41), (65, 37), (56, 37)], "#1c2430"))            # cap brim
    return base, "", post   # (badge of office is the graphics.json badge_color, on the left breast)


def marshal():
    base = dict(hat="#3a3a40", helmet_r=17, suit="#33363e", boot="#1e2024", coat=True)
    _sk = [(52, WAIST), (88, WAIST), (91, 176), (49, 176)]
    pre = (op_s(_sk, "#2b2e35")       # long coat skirt
           + op_s(rrect(81, BELT + 2, 7, 15, 1), "#1a1a1e")                        # holster on the right hip
           + bar(80, BELT, 88, BELT, 1.4, "#1a1a1e"))                              # (behind the arm)
    post = (star(62, 86, 5.5, "#e0c060")                                                       # marshal star, left breast
            + op_s([(57, 38), (83, 38), (88, 34), (80, 27), (60, 27), (52, 34)], "#3a3a40"))   # brim hat
    post = skirt_over_legs(_sk, "#2b2e35") + post
    return base, pre, post


def medic():
    base = dict(helmet="#d2ece6", suit="#e6eaea", boot="#b0bcbc", coat=True,
                badge="#e15a5a", badge_cross=True)
    _sk = [(53, WAIST - 2), (87, WAIST - 2), (89, 158), (51, 158)]
    pre = (op_s(_sk, "#eef2f2")  # coat skirt
           + op_s(rrect(77, 104, 11, 13, 2), "#eef2f2")                          # med satchel (behind the arm)
           + poly([(84, 106), (89, 106), (89, 109), (86.5, 109), (86.5, 113), (84.5, 113),
                   (84.5, 109), (82, 109)], "#e15a5a"))                          # cross on its flap
    post = (op_s([_arm_rot(-1, x, y) for x, y in [(50, 74), (59, 74), (59, 90), (50, 90)]], "#e15a5a")   # arm band, left upper arm
            + poly([_arm_rot(-1, x, y) for x, y in [(52, 83), (57, 83), (57, 79), (52, 79)]], "#eef2f2")  # white cross on it
            + poly([_arm_rot(-1, x, y) for x, y in [(53, 85), (56, 85), (56, 77), (53, 77)]], "#eef2f2")
)
    post = skirt_over_legs(_sk, "#eef2f2") + post
    return base, pre, post


def surgeon():
    # no hard helmet - a scrub cap and a tie-on mask on a bare head
    base = dict(no_helmet=True, suit="#e9eded", boot="#b0bcbc", coat=True,
                hair="sleek", hair_col="#4c3323")
    _sk = [(53, WAIST - 2), (87, WAIST - 2), (89, 158), (51, 158)]
    pre = op_s(_sk, "#f0f4f4")
    post = (op_s(head_band_fig(36.0, 46.0, inset=0.4), "#dfeae6")                     # mask, on the round of the jaw
            + bar(61, 50, 58.5, 46.5, 0.9, "#dfeae6")
            + bar(79, 50, 81.5, 46.5, 0.9, "#dfeae6")                                 # ear ties
            + op_s(head_dome(1.6, 30.0), "#dfeae6")                                    # scrub cap over the crown
            + op_s(hand_shape(-1, 0.12), "#eef2f2", d=1.0)
            + op_s(hand_shape(1, 0.12), "#eef2f2", d=1.0)                    # gloves
            + circ(70, 95, 2.0, "#e15a5a"))
    post = skirt_over_legs(_sk, "#f0f4f4") + post
    return base, pre, post


def researcher():
    base = dict(no_helmet=True, suit="#8c98a4", boot="#5c626c", coat=True, visor="#cfe0f0",
                hair="sidepart", hair_col="#33241b")
    _sk = [(53, WAIST - 2), (87, WAIST - 2), (89, 154), (51, 154)]
    pre = (op_s(_sk, "#9aa6b2")
           + op_s(rrect(77, 102, 11, 16, 2), "#7c8894")                          # specimen case (behind the arm)
           + bar(79, 108, 86, 108, 0.9, "#5c626c") + bar(79, 114, 86, 114, 0.9, "#5c626c"))
    post = ("".join(bar(x, 74, x, 84, 1.4, c) for x, c in ((63, "#e15a5a"), (66, "#8fb9c8"), (69, "#e0c060")))  # pen array
)
    post = skirt_over_legs(_sk, "#9aa6b2") + post
    return base, pre, post


def civilian():
    base = dict(no_helmet=True, suit="#606e78", boot="#3c4248",
                hair="crop", hair_col="#6a3320")
    pre = op_s(rrect(78, 102, 11, 18, 3), "#54606a")                                  # satchel, behind the arm
    post = (op_s([(59, 63), (81, 63), (78, 73), (62, 73)], "#4c5860")                 # soft collar
            + rib([(54, 69), (83, 100)], 1.8, "#54606a"))                             # strap: over the shoulder cap, out to the far edge
    return base, pre, post


def smuggler():
    base = dict(no_helmet=True, suit="#2e3431", boot="#1e211f", coat=True,
                hair="stubble", hair_col="#1b191d")
    # a deep hood instead of a helmet + a long worn coat
    _sk = [(51, WAIST), (89, WAIST), (93, 170), (47, 170)]
    pre = op_s(_sk, "#262b28")
    post = (op_s(head_dome(3.4, 36.6, wide=1.16), "#2a2f2c")                         # hood, down to the brow
            + poly(head_band_fig(28.0, 36.0, inset=1.5), "#14100f")                   # eyes in shadow
            + circ(66, 44, 1.2, "#8a8f88") + circ(74, 44, 1.2, "#8a8f88")             # eyes in the dark
            + op_s([(62, 92), (78, 92), (76, 122), (64, 122)], "#20241f")             # inner-coat bulge (contraband)
            )
    post = skirt_over_legs(_sk, "#262b28") + post
    return base, pre, post


def ranger():
    base = dict(no_helmet=True, suit="#3a4a44", boot="#26302c", coat=True,
                hair="long", hair_col="#4c3323")
    _sk = [(52, WAIST), (88, WAIST), (91, 168), (49, 168)]
    pre = (op_s(rrect(48, 54, 44, 58, 6), "#2e3a36")                                  # big trek pack
           + op_s(rrect(46, 46, 48, 12, 4), "#5a4a36")                                # bedroll on top
           + op_s(_sk, "#33413c"))       # field-coat skirt
    post = (op_s(head_dome(3.6, 35.8, wide=1.34), "#33413c")                         # hood, wide enough for the hair
            + rib([(54, 69), (83, 101)], 2.0, "#4a4038")                              # pack strap: over the shoulder cap, out to the far edge
            + circ(61, 74, 2.2, "#e0c060"))                                           # compass
    pre = pre + op_s(rrect(81, BELT + 2, 6, 9, 1), "#26302c")                         # canteen on the hip (behind arm)
    post = skirt_over_legs(_sk, "#33413c") + post
    return base, pre, post


def bounty_hunter():
    base = dict(helmet="#3c4046", suit="#2c2e34", boot="#1c1e22", visor="#e15a5a",
                backpack="#282a30")
    post = (op_s([(56, 66), (84, 66), (82, 78), (58, 78)], "#3a3c44")                 # chest plate seg
            + op_s([(57, 82), (83, 82), (81, 96), (59, 96)], "#3a3c44")
            + op_s([(59, 100), (81, 100), (79, 112), (61, 112)], "#3a3c44")
            + "".join(circ(x, 68, 1.2, "#1c1e22") for x in (62, 70, 78))
            + poly([(52, 62), (59, 68), (84, 116), (77, 120)], "#20222a")             # bandolier
            + "".join(op_s(rrect(t[0] - 2, t[1] - 3, 4, 7, 1), "#8a8f96")
                      for t in ((57, 74), (64, 90), (71, 106))))
    pre = op_s(rrect(61, BELT + 4, 6, 9, 1), "#8a8f96")                               # trophy tag at the belt
    return base, pre, post


OUTFITS = {
 "space_suit": (space_suit, "Space Suit", "default_outfit - what the player starts in"),
 "flight_suit": (flight_suit, "Flight Suit", "pilots - anyone who flies"),
 "mechanic": (mechanic, "Mechanic", "outfitting bay - repair"),
 "dockworker": (dockworker, "Dockworker", "spaceport - loading & berths"),
 "miner": (miner, "Miner / Prospector", "asteroid & rock work"),
 "security": (security, "Security", "station patrol & the brig"),
 "station_command": (station_command, "Station Command", "the ring's authority tier"),
 "marshal": (marshal, "Marshal", "law past the settled lanes"),
 "medic": (medic, "Medic", "infirmary - anywhere someone's hurt"),
 "surgeon": (surgeon, "Surgeon", "the operating suite"),
 "researcher": (researcher, "Researcher", "labs & survey teams"),
 "civilian": (civilian, "Civilian", "passengers, residents, everyone else"),
 "smuggler": (smuggler, "Smuggler", "the fringe - doesn't want to be read"),
 "ranger": (ranger, "Ranger", "long survey treks, no station for weeks"),
 "bounty_hunter": (bounty_hunter, "Bounty Hunter", "the board pays by the head"),
}

# Full read-out of every drawn piece on each outfit: the recoloured base keys
# (graphics.json *_color) followed by the baked signature geometry. Rendered
# under each atlas card. Backtick spans name the graphics.json / figure_parts key.
DETAILS = {
 "space_suit":
   "A sealed EVA suit and nothing else. Mid-grey hard shell (`suit`), darker "
   "grey boots (`boot`), a plain domed pressure helmet (`helmet`) with the "
   "regulation visor gap over the eyes. No role detail — this is the "
   "neutral suit the player starts in.",
 "flight_suit":
   "Slate flight suit (`suit`), black boots (`boot`), light-grey flight helmet "
   "(`helmet`). Detail: an X of dark webbing across the chest (the ejection "
   "harness), a checklist board strapped to the right thigh with two cyan "
   "reference lines, and a small comms box with a red indicator on the right "
   "of the helmet.",
 "mechanic":
   "Olive coveralls (`suit`), dark boots (`boot`), an amber hard hat "
   "(`helmet`) with a forehead lamp, a webbing belt (`belt`). Detail: a "
   "low-slung tool belt with three pouches and two hanging loops, a rolled-back "
   "cuff on the left forearm, and a pad strapped over each knee.",
 "dockworker":
   "Blue-grey work suit (`suit`), dark boots (`boot`), amber hard hat "
   "(`helmet`). Detail: a hi-vis orange tabard over the chest with a darker "
   "cross-band and two shoulder straps, and heavy dark gloves on both hands.",
 "miner":
   "Tan rock suit (`suit`), dark boots (`boot`), a pale-gold hard hat "
   "(`helmet`) with a lamp. Detail: a boxy life-support pack on the back, a "
   "tool belt, a drill stem down the back-right to a dark drill bit, an "
   "ore-sample pouch on the right hip, and a short strap across the left shin.",
 "security":
   "Dark blue-grey uniform (`suit`), black boots (`boot`), grey helmet "
   "(`helmet`) with a cyan visor (`visor`). Detail: a padded stab vest with "
   "two seams, a baton sheathed on the right hip, and a small shoulder radio "
   "with a cyan lamp on the left.",
 "station_command":
   "Navy tunic (`suit`), near-black boots (`boot`), pale service helmet "
   "(`helmet`), white stand collar (`collar`), dark epaulettes (`shoulders`), "
   "a gold badge of office (`badge`) on the left breast. Detail: a "
   "double-breasted grid of gold buttons (two columns of four), a pipped rank "
   "board on each shoulder, and a peaked cap with a dark brim over the helmet.",
 "marshal":
   "A long charcoal coat (`suit`, `coat` cut), black boots (`boot`), a dark "
   "brimmed hat (`hat`). Detail: the coat skirt falls to mid-shin, a holstered "
   "sidearm rides the right hip behind the arm, a gold five-point marshal's "
   "star sits on the left breast, and the wide-brim hat crowns the head.",
 "medic":
   "White med coat (`suit`, `coat` cut), pale boots (`boot`), a mint helmet "
   "(`helmet`), a red cross badge (`badge` + `badge_cross`) on the breast. "
   "Detail: the coat skirt, a red armband with a white cross on the left upper "
   "arm, and a white med satchel on the right hip with a red cross on its flap.",
 "surgeon":
   "Pale scrub suit (`suit`) with a coat skirt, pale boots (`boot`), bare "
   "head. Detail: a tie-on surgical mask over the nose and mouth with ear "
   "ties, a scrub cap over the crown, white surgical gloves on both hands, and "
   "a small red status dot at the sternum.",
 "researcher":
   "Grey-blue lab coat (`suit`, `coat` cut), grey boots (`boot`), bare head "
   "with a clear work visor (`visor`). Detail: a three-pen array (red / cyan / "
   "gold) in the breast pocket and a grey specimen case on the right hip with "
   "two ruled lines.",
 "civilian":
   "Plain blue-grey clothes (`suit`), dark shoes (`boot`), bare head. Detail: "
   "a soft folded collar and a shoulder satchel on a cross-body strap.",
 "smuggler":
   "Dark green worn clothes (`suit`) and boots (`boot`) under a long coat. "
   "Detail: a deep raised hood with the face in shadow (only two glinting eyes "
   "show), a bulge of contraband inside the coat front, and a torn hem.",
 "ranger":
   "Field green (`suit`, `coat` cut), dark boots (`boot`), bare head. Detail: "
   "a tall trek pack with a bedroll lashed on top, a field-coat skirt, a "
   "canteen on the right hip behind the arm, a hood, a cross-body pack strap, "
   "and a small gold compass on the chest.",
 "bounty_hunter":
   "Near-black armour (`suit`), black boots (`boot`), a dark helmet (`helmet`) "
   "with a red visor (`visor`), a back pack (`backpack`). Detail: three "
   "stacked riveted chest-plate segments, a diagonal bandolier with three "
   "shell loops, and a small metal trophy tag at the belt.",
}
