"""Signature layers for the Common Kit atlas - the culture-neutral civilian
and service outfits from graphics.json, each given a role-distinguishing
detail on top of the shared figure_parts body (a mechanic's tool belt, a
smuggler's hood, a surgeon's mask...). Strokeless <polygon>/<circle>.

build_outfit(key) -> (base_opts, pre_svg, post_svg)
composed by gen_common.py as:  grid + pre + figure_parts(**base) + post

Figure anchors after the cinched-waist change: chest y82 (x49-91), waist y108
(x58-82), belt y104-113, hip y146 (x51-89), legs y144-194, arms x41-54 /
x86-99 y66-120, hands (46/94, 123), bare head (70,48) r15.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, ngon, rrect, opoly, ocirc, bar, offset_poly, _u

OUT = "#141219"
WAIST = 108
BELT = 104


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
    o = [op_s([(52, 46), (88, 46), (84, 36), (74, 30), (66, 30), (56, 36)], col)]
    o.append(bar(52, 44, 88, 44, 1.6, col))
    if lamp:
        o.append(op_s(rrect(66, 30, 8, 5, 1), "#3a3a40"))
        o.append(circ(70, 30, 2.2, lamp))
    return "".join(o)


# ---------------------------------------------------------------- outfits
def space_suit():
    return dict(helmet="#96969b", suit="#5a5a60", boot="#46464a"), "", ""


def flight_suit():
    base = dict(helmet="#ced6dc", suit="#3a4658", boot="#282e38")
    post = (rib([(52, 66), (70, 96), (88, 66)], 2.0, "#2b3542")        # chest harness, X-straps
            + op_s(rrect(80, 118, 12, 16, 1), "#2b3542")               # thigh checklist board
            + bar(82, 122, 90, 122, 0.9, "#8fb9c8") + bar(82, 126, 90, 126, 0.9, "#8fb9c8")
            + op_s(rrect(84, 46, 8, 7, 1), "#2b3542")                  # helmet comms box
            + circ(88, 49, 1.2, "#e15a5a"))
    return base, "", post


def mechanic():
    base = dict(helmet="#f0aa37", suit="#524e48", boot="#2e2a26")
    post = (hardhat("#f0aa37", lamp="#fff2c0")
            + toolbelt("#3a352f")
            + op_s([(48, 90), (54, 90), (53, 118), (47, 118)], "#3a352f")   # rolled sleeve cuff L
            + op_s(rrect(58, 156, 12, 9, 2), "#3a352f") + op_s(rrect(70, 156, 12, 9, 2), "#3a352f")  # knee pads
            + rib([(40, 120), (36, 130), (40, 140)], 1.6, "#6a635a"))       # wrench in hand
    return base, "", post


def dockworker():
    base = dict(helmet="#f2962a", suit="#465060", boot="#2a303a")
    # hi-vis tabard over the suit (front panel + shoulder straps)
    pre = ""
    post = (op_s([(58, 68), (82, 68), (80, 116), (60, 116)], "#f2962a")     # hi-vis tabard front
            + bar(60, 90, 80, 90, 1.6, "#c46a10")
            + op_s([(56, 64), (63, 64), (61, 88), (54, 88)], "#f2962a")     # strap L
            + op_s([(77, 64), (84, 64), (86, 88), (79, 88)], "#f2962a")     # strap R
            + hardhat("#f2962a")
            + ocirc(46, 123, 4.2, "#2a303a", d=1.0) + ocirc(94, 123, 4.2, "#2a303a", d=1.0))  # heavy gloves
    return base, pre, post


def miner():
    base = dict(helmet="#ebcd5f", suit="#7a6648", boot="#483828")
    pre = op_s(rrect(46, 58, 48, 56, 5), "#5c4d34")                          # life-support backpack
    post = (hardhat("#ebcd5f", lamp="#fff2c0")
            + toolbelt("#463826")
            + rib([(96, 60), (100, 90), (98, 128)], 2.0, "#6a5a3c")          # drill stem down the back-right
            + poly([(93, 126), (103, 128), (98, 140)], "#3a2e1e")            # drill bit
            + op_s(rrect(78, 118, 12, 14, 2), "#463826")                     # ore-sample pouch
            + bar(58, 160, 68, 160, 1.4, "#5c4d34"))
    return base, pre, post


def security():
    base = dict(helmet="#606874", suit="#3a3f48", boot="#24272e", visor="#8fb9c8")
    post = (op_s([(54, 66), (86, 66), (83, 104), (57, 104)], "#2c3038")     # padded vest
            + bar(58, 78, 82, 78, 1.2, "#4a505a") + bar(58, 90, 82, 90, 1.2, "#4a505a")
            + op_s(rrect(82, BELT + 4, 5, 20, 1), "#20232a")                 # baton on the hip
            + op_s(rrect(46, 52, 8, 6, 1), "#20232a") + circ(50, 52, 1.4, "#8fb9c8"))  # shoulder radio
    return base, "", post


def station_command():
    base = dict(helmet="#ced2dc", suit="#2e384a", boot="#222832", collar="#dce1eb",
                shoulders="#28303e")
    # double-breasted tunic: two rows of buttons + a rank board
    post = ("".join(circ(x, y, 1.4, "#ebcd5f") for x in (63, 77) for y in (72, 82, 92, 102))
            + op_s(rrect(46, 68, 16, 6, 1), "#ebcd5f") + op_s(rrect(78, 68, 16, 6, 1), "#ebcd5f")  # shoulder boards
            + "".join(bar(48, 70 + k, 60, 70 + k, 0.9, "#2e384a") for k in (0, 3))
            + op_s([(54, 46), (86, 46), (82, 38), (74, 33), (66, 33), (58, 38)], "#2e384a")  # peaked cap
            + poly([(54, 46), (68, 46), (64, 42), (56, 42)], "#1c2430")            # cap brim
            + op_s([(68, 96), (74, 102), (68, 108), (62, 102)], "#ebcd5f"))        # command badge
    return base, "", post


def marshal():
    base = dict(hat="#3a3a40", helmet_r=17, suit="#33363e", boot="#1e2024", coat=True)
    pre = op_s([(48, WAIST), (92, WAIST), (96, 176), (44, 176)], "#2b2e35")        # long coat skirt
    post = (star(70, 100, 9, "#e0c060")                                                        # marshal star
            + op_s([(52, 44), (88, 44), (94, 40), (84, 32), (56, 32), (46, 40)], "#3a3a40")    # brim hat
            + op_s(rrect(82, BELT + 4, 8, 14, 1), "#1a1a1e")                       # holster
            + bar(82, BELT + 2, 90, BELT + 2, 1.4, "#1a1a1e"))
    return base, pre, post


def medic():
    base = dict(helmet="#d2ece6", suit="#e6eaea", boot="#b0bcbc", coat=True,
                badge="#e15a5a", badge_cross=True)
    pre = op_s([(50, WAIST - 2), (90, WAIST - 2), (92, 160), (48, 160)], "#eef2f2")   # coat skirt
    post = (op_s([(50, 92), (70, 92), (68, 108), (52, 108)], "#e15a5a")               # arm band
            + poly([(56, 96), (64, 96), (64, 92), (56, 92)], "#eef2f2")
            + op_s(rrect(84, 108, 14, 16, 2), "#eef2f2")                              # med satchel
            + poly([(88, 112), (94, 112), (94, 116), (91, 116), (91, 120), (89, 120),
                    (89, 116), (86, 116)], "#e15a5a"))                                # cross on the flap
    return base, pre, post


def surgeon():
    base = dict(helmet="#d2ece6", suit="#e9eded", boot="#b0bcbc", coat=True,
                visor="#cfe0dc")
    pre = op_s([(50, WAIST - 2), (90, WAIST - 2), (92, 160), (48, 160)], "#f0f4f4")
    post = (op_s([(58, 50), (82, 50), (80, 60), (60, 60)], "#dfeae6")                 # face mask
            + bar(58, 52, 63, 48, 0.9, "#dfeae6") + bar(82, 52, 77, 48, 0.9, "#dfeae6")
            + op_s([(56, 32), (84, 32), (82, 26), (58, 26)], "#dfeae6")               # scrub cap
            + ocirc(46, 123, 3.6, "#eef2f2", d=1.0) + ocirc(94, 123, 3.6, "#eef2f2", d=1.0)  # gloves
            + circ(70, 100, 2.0, "#e15a5a"))
    return base, pre, post


def researcher():
    base = dict(no_helmet=True, suit="#8c98a4", boot="#5c626c", coat=True, visor="#cfe0f0")
    pre = op_s([(50, WAIST - 2), (90, WAIST - 2), (92, 156), (48, 156)], "#9aa6b2")
    post = ("".join(bar(x, 68, x, 78, 1.4, c) for x, c in ((63, "#e15a5a"), (66, "#8fb9c8"), (69, "#e0c060")))  # pen array
            + op_s(rrect(82, 110, 14, 18, 2), "#7c8894")                              # specimen case
            + bar(84, 116, 94, 116, 0.9, "#5c626c") + bar(84, 122, 94, 122, 0.9, "#5c626c"))
    return base, pre, post


def civilian():
    base = dict(no_helmet=True, suit="#606e78", boot="#3c4248")
    post = (op_s([(58, 60), (82, 60), (79, 70), (61, 70)], "#4c5860")                 # soft collar
            + op_s(rrect(84, 104, 12, 20, 3), "#54606a")                              # a satchel
            + rib([(58, 62), (90, 108)], 1.4, "#54606a"))                             # strap
    return base, "", post


def smuggler():
    base = dict(no_helmet=True, suit="#2e3431", boot="#1e211f")
    # a deep hood instead of a helmet + a long worn coat
    pre = op_s([(46, WAIST), (94, WAIST), (98, 170), (42, 170)], "#262b28")
    post = (op_s([(52, 56), (88, 56), (84, 30), (70, 22), (56, 30)], "#2a2f2c")       # hood
            + poly([(58, 54), (82, 54), (78, 40), (62, 40)], "#14100f")               # hood shadow over the face
            + circ(66, 50, 1.2, "#8a8f88") + circ(74, 50, 1.2, "#8a8f88")             # eyes in the dark
            + op_s([(62, 98), (78, 98), (76, 130), (64, 130)], "#20241f")             # inner-coat bulge (contraband)
            + bar(50, 128, 54, 118, 1.4, "#3a3f3b"))                                  # worn hem tear
    return base, pre, post


def ranger():
    base = dict(no_helmet=True, suit="#3a4a44", boot="#26302c", coat=True)
    pre = (op_s(rrect(44, 52, 52, 60, 6), "#2e3a36")                                  # big trek pack
           + op_s(rrect(42, 44, 56, 12, 4), "#5a4a36")                                # bedroll on top
           + op_s([(48, WAIST), (92, WAIST), (95, 168), (45, 168)], "#33413c"))       # field-coat skirt
    post = (op_s([(52, 52), (88, 52), (84, 28), (70, 20), (56, 28)], "#33413c")       # hood
            + rib([(44, 66), (58, 108), (62, 150)], 2.4, "#4a4038")                   # slung rifle strap+stock
            + op_s(rrect(40, 96, 6, 34, 1), "#3a322a")
            + op_s(rrect(82, BELT + 4, 7, 9, 1), "#26302c")                           # canteen
            + circ(60, 74, 2.2, "#e0c060"))                                           # compass
    return base, pre, post


def bounty_hunter():
    base = dict(helmet="#3c4046", suit="#2c2e34", boot="#1c1e22", visor="#e15a5a",
                backpack="#282a30")
    post = (op_s([(54, 64), (86, 64), (84, 76), (56, 76)], "#3a3c44")                 # chest plate seg
            + op_s([(56, 80), (84, 80), (82, 96), (58, 96)], "#3a3c44")
            + op_s([(58, 100), (82, 100), (80, 112), (60, 112)], "#3a3c44")
            + "".join(circ(x, 70, 1.2, "#1c1e22") for x in (60, 70, 80))
            + poly([(50, 60), (58, 66), (86, 118), (78, 122)], "#20222a")             # bandolier
            + "".join(op_s(rrect(t[0] - 2, t[1] - 3, 4, 7, 1), "#8a8f96")
                      for t in ((56, 74), (64, 90), (72, 106)))
            + rib([(88, 52), (94, 44), (92, 30)], 2.4, "#3a3c44")                     # slung weapon over the shoulder
            + op_s(rrect(78, BELT + 6, 6, 8, 1), "#8a8f96"))                          # trophy tag
    return base, "", post


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
