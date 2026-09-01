"""Signature layers for the Common Kit atlas - the culture-neutral civilian
and service outfits from graphics.json, each given a role-distinguishing
detail on top of the shared figure_parts body (a mechanic's tool belt, a
smuggler's hood, a surgeon's mask...). Strokeless <polygon>/<circle>.

build_outfit(key) -> (base_opts, pre_svg, post_svg)
composed by gen_common.py as:  grid + pre + figure_parts(**base) + post

Figure anchors after the full Grounded proportion remap (~6.1-head figure):
chest y72-106 (x57-83), waist y103 (x57-83), belt y95-108, hip y139, legs
y139-194, arms x50-60 / x80-90 y66-132, hands (57/83, 133), bare head (70,46)
r14 with the mouth line at y54, helmeted face (70,48) r11.5. Anything on the
hip/thigh that the arm should cover goes in `pre` (drawn behind the body), not
`post`.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, ngon, rrect, opoly, ocirc, bar, offset_poly, _u

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


def dots(x0, y0, x1, y1, n, r, col):
    return "".join(circ(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1), r, col)
                   for i in range(n))


def op_s(pts, fill, d=1.2, ol=OUT):
    return poly(offset_poly(pts, d), ol) + poly(pts, fill)


def star(cx, cy, r, col, n=5):
    pts = []
    for k in range(2 * n):
        a = -math.pi / 2 + math.pi * k / n
        rr = r if k % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return op_s(pts, col, d=0.9)


def toolbelt(col):
    """A low-slung utility belt with pouches + loops, over the waist belt."""
    o = [op_s(rrect(56, BELT + 2, 28, 8, 2), col)]
    for x in (58, 66, 78):
        o.append(op_s(rrect(x, BELT + 8, 7, 10, 1), col))
    for x in (73, 82):
        o.append(bar(x, BELT + 3, x, BELT + 13, 1.4, "#2a2a2e"))
    return "".join(o)


def hardhat(col, lamp=None):
    o = [op_s([(53, 42), (87, 42), (83, 33), (74, 27), (66, 27), (57, 33)], col)]
    o.append(bar(53, 40, 87, 40, 1.6, col))
    if lamp:
        o.append(op_s(rrect(66, 27, 8, 5, 1), "#3a3a40"))
        o.append(circ(70, 27, 2.2, lamp))
    return "".join(o)


# ---------------------------------------------------------------- outfits
def space_suit():
    return dict(helmet="#96969b", suit="#5a5a60", boot="#46464a"), "", ""


def flight_suit():
    base = dict(helmet="#ced6dc", suit="#3a4658", boot="#282e38")
    post = (rib([(53, 63), (70, 90), (87, 63)], 2.0, "#2b3542")        # chest harness, X-straps
            + op_s(rrect(78, 142, 12, 16, 1), "#2b3542")               # thigh checklist board
            + bar(80, 146, 88, 146, 0.9, "#8fb9c8") + bar(80, 150, 88, 150, 0.9, "#8fb9c8")
            + op_s(rrect(83, 42, 8, 7, 1), "#2b3542")                  # helmet comms box
            + circ(87, 45, 1.2, "#e15a5a"))
    return base, "", post


def mechanic():
    base = dict(helmet="#f0aa37", suit="#524e48", boot="#2e2a26")
    post = (hardhat("#f0aa37", lamp="#fff2c0")
            + toolbelt("#3a352f")
            + op_s([(51, 95), (60, 95), (60, 124), (51, 124)], "#3a352f")   # rolled sleeve cuff L (over the arm)
            + op_s(rrect(53, 150, 13, 9, 2), "#3a352f") + op_s(rrect(71, 150, 13, 9, 2), "#3a352f"))  # knee pads
    return base, "", post


def dockworker():
    base = dict(helmet="#f2962a", suit="#465060", boot="#2a303a")
    # hi-vis tabard over the suit (front panel + shoulder straps)
    pre = ""
    post = (op_s([(58, 68), (82, 68), (80, 110), (60, 110)], "#f2962a")     # hi-vis tabard front
            + bar(60, 88, 80, 88, 1.6, "#c46a10")
            + op_s([(57, 64), (64, 64), (62, 84), (55, 84)], "#f2962a")     # strap L
            + op_s([(76, 64), (83, 64), (85, 84), (78, 84)], "#f2962a")     # strap R
            + hardhat("#f2962a")
            + ocirc(57, 133, 4.0, "#2a303a", d=1.0) + ocirc(83, 133, 4.0, "#2a303a", d=1.0))  # heavy gloves
    return base, pre, post


def miner():
    base = dict(helmet="#ebcd5f", suit="#7a6648", boot="#483828")
    pre = op_s(rrect(49, 60, 42, 60, 5), "#5c4d34")                          # life-support backpack
    post = (hardhat("#ebcd5f", lamp="#fff2c0")
            + toolbelt("#463826")
            + rib([(90, 62), (92, 92), (90, 126)], 2.0, "#6a5a3c")           # drill stem down the back-right
            + poly([(87, 124), (95, 126), (91, 138)], "#3a2e1e")             # drill bit
            + op_s(rrect(78, 110, 12, 14, 2), "#463826")                     # ore-sample pouch
            + bar(56, 154, 66, 154, 1.4, "#5c4d34"))
    return base, pre, post


def security():
    base = dict(helmet="#606874", suit="#3a3f48", boot="#24272e", visor="#8fb9c8")
    post = (op_s([(56, 68), (84, 68), (82, 104), (58, 104)], "#2c3038")     # padded vest
            + bar(59, 80, 81, 80, 1.2, "#4a505a") + bar(59, 91, 81, 91, 1.2, "#4a505a")
            + op_s(rrect(84, BELT + 2, 5, 20, 1), "#20232a")                 # baton on the hip
            + op_s(rrect(49, 63, 8, 6, 1), "#20232a") + circ(53, 63, 1.4, "#8fb9c8"))  # shoulder radio
    return base, "", post


def station_command():
    base = dict(helmet="#ced2dc", suit="#2e384a", boot="#222832", collar="#dce1eb",
                shoulders="#28303e", badge="#ebcd5f")
    # double-breasted tunic: two rows of buttons + rank boards + a breast badge
    post = ("".join(circ(x, y, 1.4, "#ebcd5f") for x in (64, 76) for y in (74, 84, 94, 104))
            + op_s(rrect(49, 65, 15, 6, 1), "#ebcd5f") + op_s(rrect(76, 65, 15, 6, 1), "#ebcd5f")  # shoulder boards
            + "".join(bar(50, 67 + k, 60, 67 + k, 0.9, "#2e384a") for k in (0, 3))   # rank pips, board L
            + "".join(bar(80, 67 + k, 90, 67 + k, 0.9, "#2e384a") for k in (0, 3))   #             board R (mirrored)
            + op_s([(55, 41), (85, 41), (81, 33), (74, 28), (66, 28), (59, 33)], "#2e384a")  # peaked cap
            + poly([(55, 41), (68, 41), (64, 37), (56, 37)], "#1c2430"))           # cap brim
    return base, "", post   # (badge of office is the graphics.json badge_color, on the left breast)


def marshal():
    base = dict(hat="#3a3a40", helmet_r=17, suit="#33363e", boot="#1e2024", coat=True)
    pre = (op_s([(49, WAIST), (91, WAIST), (95, 176), (45, 176)], "#2b2e35")       # long coat skirt
           + op_s(rrect(85, BELT + 2, 8, 16, 1), "#1a1a1e")                        # holster on the right hip
           + bar(84, BELT, 92, BELT, 1.4, "#1a1a1e"))                              # (behind the arm)
    post = (star(62, 86, 5.5, "#e0c060")                                                       # marshal star, left breast
            + op_s([(53, 39), (87, 39), (93, 35), (83, 27), (57, 27), (47, 35)], "#3a3a40"))   # brim hat
    return base, pre, post


def medic():
    base = dict(helmet="#d2ece6", suit="#e6eaea", boot="#b0bcbc", coat=True,
                badge="#e15a5a", badge_cross=True)
    pre = op_s([(50, WAIST - 2), (90, WAIST - 2), (92, 158), (48, 158)], "#eef2f2")   # coat skirt
    post = (op_s([(50, 74), (59, 74), (59, 90), (50, 90)], "#e15a5a")                 # arm band, left upper arm
            + poly([(52, 83), (57, 83), (57, 79), (52, 79)], "#eef2f2")               # white cross on it
            + poly([(53, 85), (56, 85), (56, 77), (53, 77)], "#eef2f2")
            + op_s(rrect(83, 100, 14, 16, 2), "#eef2f2")                              # med satchel
            + poly([(87, 104), (93, 104), (93, 108), (90, 108), (90, 112), (88, 112),
                    (88, 108), (85, 108)], "#e15a5a"))                                # cross on the flap
    return base, pre, post


def surgeon():
    # no hard helmet - a scrub cap and a tie-on mask on a bare head
    base = dict(no_helmet=True, suit="#e9eded", boot="#b0bcbc", coat=True)
    pre = op_s([(50, WAIST - 2), (90, WAIST - 2), (92, 158), (48, 158)], "#f0f4f4")
    post = (op_s([(58, 47), (82, 47), (80, 60), (60, 60)], "#dfeae6")                 # mask over nose + mouth
            + bar(60, 50, 53, 45, 0.9, "#dfeae6") + bar(80, 50, 87, 45, 0.9, "#dfeae6")  # ear ties
            + op_s([(56, 40), (84, 40), (81, 30), (70, 26), (59, 30)], "#dfeae6")      # scrub cap over the crown
            + ocirc(57, 133, 3.6, "#eef2f2", d=1.0) + ocirc(83, 133, 3.6, "#eef2f2", d=1.0)  # gloves
            + circ(70, 95, 2.0, "#e15a5a"))
    return base, pre, post


def researcher():
    base = dict(no_helmet=True, suit="#8c98a4", boot="#5c626c", coat=True, visor="#cfe0f0")
    pre = op_s([(50, WAIST - 2), (90, WAIST - 2), (92, 154), (48, 154)], "#9aa6b2")
    post = ("".join(bar(x, 74, x, 84, 1.4, c) for x, c in ((63, "#e15a5a"), (66, "#8fb9c8"), (69, "#e0c060")))  # pen array
            + op_s(rrect(82, 102, 14, 18, 2), "#7c8894")                              # specimen case
            + bar(84, 108, 94, 108, 0.9, "#5c626c") + bar(84, 114, 94, 114, 0.9, "#5c626c"))
    return base, pre, post


def civilian():
    base = dict(no_helmet=True, suit="#606e78", boot="#3c4248")
    post = (op_s([(59, 63), (81, 63), (78, 73), (62, 73)], "#4c5860")                 # soft collar
            + op_s(rrect(83, 98, 12, 20, 3), "#54606a")                               # a satchel
            + rib([(59, 64), (89, 102)], 1.4, "#54606a"))                             # strap
    return base, "", post


def smuggler():
    base = dict(no_helmet=True, suit="#2e3431", boot="#1e211f")
    # a deep hood instead of a helmet + a long worn coat
    pre = op_s([(46, WAIST), (94, WAIST), (98, 170), (42, 170)], "#262b28")
    post = (op_s([(53, 50), (87, 50), (83, 26), (70, 19), (57, 26)], "#2a2f2c")       # hood
            + poly([(58, 48), (82, 48), (78, 36), (62, 36)], "#14100f")               # hood shadow over the face
            + circ(66, 44, 1.2, "#8a8f88") + circ(74, 44, 1.2, "#8a8f88")             # eyes in the dark
            + op_s([(62, 92), (78, 92), (76, 122), (64, 122)], "#20241f")             # inner-coat bulge (contraband)
            + bar(52, 122, 56, 110, 1.4, "#3a3f3b"))                                  # worn hem tear
    return base, pre, post


def ranger():
    base = dict(no_helmet=True, suit="#3a4a44", boot="#26302c", coat=True)
    pre = (op_s(rrect(48, 54, 44, 58, 6), "#2e3a36")                                  # big trek pack
           + op_s(rrect(46, 46, 48, 12, 4), "#5a4a36")                                # bedroll on top
           + op_s([(49, WAIST), (91, WAIST), (95, 168), (45, 168)], "#33413c"))       # field-coat skirt
    post = (op_s([(53, 48), (87, 48), (83, 26), (70, 18), (57, 26)], "#33413c")       # hood
            + rib([(50, 66), (60, 104), (64, 140)], 2.0, "#4a4038")                   # cross-body pack strap
            + circ(61, 74, 2.2, "#e0c060"))                                           # compass
    pre = pre + op_s(rrect(85, BELT + 2, 7, 10, 1), "#26302c")                        # canteen on the hip (behind arm)
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
