"""Ship specimens for the Past the Reach atlas - detailed, exotic-silhouette
top-down ships (240x200 viewBox, nose up, centre ~120,100). Strokeless:
<polygon> + <circle> only. Imported by gen_frontier.py.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, ngon, rrect, offset_poly, opoly, ocirc, bar, ring_strip, _u, GRID

CX, CY = 120.0, 100.0


# ---------------------------------------------------------------- extra helpers
def grid_bg(w=240.0, h=200.0):
    return poly([(0, 0), (w, 0), (w, h), (0, h)], GRID)


def ribbon(pts, w, col, op=None):
    """Open polyline -> filled ribbon (a thick line as one polygon)."""
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


def rivets_line(x0, y0, x1, y1, n, r, col):
    return "".join(circ(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1), r, col)
                   for i in range(n))


def teeth(x0, x1, y, h, n, col, down=True):
    """A sawtooth strip between x0..x1 at baseline y, teeth pointing +y (down) or -y."""
    s = 1 if down else -1
    step = (x1 - x0) / n
    pts = [(x0, y)]
    for i in range(n):
        pts.append((x0 + step * (i + 0.5), y + s * h))
        pts.append((x0 + step * (i + 1), y))
    return poly(pts + [(x1, y - s * 0.5), (x0, y - s * 0.5)], col)


def wave_pts(x0, x1, y, amp, n, phase=0.0):
    """A row of points along a sine ripple - a rippled trailing edge."""
    return [(x0 + (x1 - x0) * i / n,
             y + amp * math.sin(phase + math.pi * 2 * i / n * 1.5)) for i in range(n + 1)]


def chevrons(x0, x1, y, w, h, col, down=True, n=3):
    s = 1 if down else -1
    step = (x1 - x0) / n
    out = []
    for i in range(n):
        cx = x0 + step * (i + 0.5)
        out.append(poly([(cx - w, y), (cx, y + s * h), (cx + w, y),
                         (cx + w - 1.4, y), (cx, y + s * (h - 2.2)), (cx - w + 1.4, y)], col))
    return "".join(out)


def radial_holes(cx, cy, r, n, dot, col, rings=(1.0,)):
    out = [circ(cx, cy, dot * 1.4, col)]
    for rr in rings:
        for k in range(n):
            a = 2 * math.pi * k / n
            out.append(circ(cx + r * rr * math.cos(a), cy + r * rr * math.sin(a), dot, col))
    return "".join(out)


def groove(x, y, w, h, col):
    return poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], col)


def flame(x, y, w, length, col):
    return poly([(x - w, y), (x, y + length), (x + w, y)], col, cls="flame")


# ================================================================ 1. DEEPROCK
def deeprock(P):
    H, L, G, T, Y, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    # exhaust
    for hx in (100, 140):
        o.append(flame(hx, 176, 3, 20, T))
    # aft engine block + four thruster housings
    o.append(opoly(rrect(84, 148, 72, 30, 3), L, d=1.6))
    for hx in (95, 110, 130, 145):
        o.append(opoly(rrect(hx - 4, 150, 8, 26, 1), S, d=1.0))
        o.append(circ(hx, 174, 2.2, "#241f1b"))
    o.append(chevrons(86, 154, 149, 4, 4, Y, n=3))
    # segmented tank body - three barrel rings
    for i, ty in enumerate((84, 110, 138)):
        o.append(opoly(ngon(120, ty, 40 - i * 2, 15, 22), H, d=1.4))
    for ty in (97, 124):
        o.append(bar(82, ty, 158, ty, 1.2, S))
        o.append(rivets_line(84, ty, 156, ty, 9, 1.1, "#33302b"))
    # conveyor hump on the spine
    o.append(opoly([(112, 60), (128, 60), (126, 150), (114, 150)], L, d=1.2))
    for ry in range(66, 150, 9):
        o.append(bar(113, ry, 127, ry, 1.0, S))
    # rock-crusher jaw at the nose - upper + lower toothed plates
    o.append(opoly([(78, 44), (162, 44), (150, 70), (90, 70)], H, d=1.5))
    o.append(teeth(92, 148, 66, 7, 7, S, down=True))
    o.append(teeth(96, 144, 50, 6, 6, "#4a423b", down=False))
    o.append(groove(104, 46, 32, 8, "#2b2723"))
    # ore chute - asymmetric angled tube on the port flank
    o.append(ribbon([(84, 96), (58, 84), (44, 92)], 5, L))
    o.append(circ(44, 92, 4, S))
    # offset cabin box, low + forward
    o.append(opoly(rrect(62, 74, 22, 24, 3), "#6a6058", d=1.2))
    o.append(groove(66, 78, 14, 6, G))
    # forward floodlamp masts
    for mx, my in ((96, 40), (144, 40)):
        o.append(bar(mx, 46, mx, my, 1.4, S))
        o.append(circ(mx, my, 3.4, G))
        o.append(poly([(mx - 3, my), (mx + 3, my), (mx + 8, my - 14), (mx - 8, my - 14)], G, op=0.14))
    # hazard trim along the jaw lip
    o.append(bar(78, 45, 162, 45, 1.6, Y))
    return "".join(o)


# ================================================================ 2. KESSARI
def kessari(P):
    H, L, G, T, Y, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    o.append(flame(120, 168, 3.2, 18, T))
    # censer exhaust - a perforated ornate housing at the base
    o.append(opoly(rrect(100, 150, 40, 20, 2), L, d=1.4))
    o.append(radial_holes(120, 160, 9, 8, 1.3, T, rings=(0.55, 1.0)))
    o.append(chevrons(102, 138, 150, 3, 3, Y, n=4))
    # stepped flying-buttress flanks - three tapering steps each side
    for sx in (1, -1):
        steps = [(74, 60, 96), (66, 88, 132), (60, 118, 158)]
        for w, y0, y1 in steps:
            xa = 120 + sx * (w - 44)
            xb = 120 + sx * w
            o.append(opoly([(xa, y0 - 6), (xb, y0), (xb, y1), (xa, y1 + 8)], L, d=1.3, ol=S))
            o.append(bar(xb, y0 + 2, xb, y1 - 2, 1.2, Y))
    # central slab - blunt nose, base-heavy, one edge left irregular
    slab = [(103, 34), (137, 34), (144, 78), (149, 122), (150, 152), (150, 166),
            (90, 166), (90, 152), (92, 120), (95, 76)]
    o.append(opoly(slab, H, d=1.8, ol=S))
    # carved relief - recessed panel grooves across the face
    for gy in (48, 74, 100, 128):
        o.append(groove(98, gy, 44, 6, S))
    # ember spine with cross-ribs (a ladder)
    o.append(bar(120, 38, 120, 150, 2.6, G))
    for ry in range(50, 150, 16):
        o.append(bar(108, ry, 132, ry, 1.6, G))
    # rose-window aperture cluster near the nose
    o.append(radial_holes(120, 52, 8, 6, 1.8, G, rings=(1.0,)))
    # finial spire cluster at the very nose
    o.append(poly([(114, 40), (120, 26), (126, 40)], H))
    o.append(poly([(116, 38), (120, 30), (124, 38)], G))
    o.append(circ(120, 30, 1.8, "#ffe0b0"))
    return "".join(o)


# ================================================================ 3. MERIDIAN
def meridian(P):
    """A ship of state read as a galleon: a long narrow spindle hull with a
    pointed bowsprit forward, a tall stepped aftcastle at the stern, modest
    scalloped sail-vanes, brass banding and lantern light throughout."""
    H, L, G, T, Y, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    for hx in (112, 128):
        o.append(flame(hx, 176, 2.6, 16, T))
    # stern thrusters tucked under the aftcastle
    for hx in (112, 128):
        o.append(opoly(rrect(hx - 6, 160, 12, 16, 2), L, d=1.1))
    # tall stepped aftcastle - three decks stacked at the stern
    for w, y0, y1 in ((22, 128, 162), (28, 112, 150), (34, 96, 138)):
        o.append(opoly(rrect(120 - w, y0, 2 * w, y1 - y0, 3), H, d=1.4))
        o.append(bar(120 - w + 2, y0 + 3, 120 + w - 2, y0 + 3, 1.3, Y))
        for i in range(5):
            o.append(circ(120 - w + 6 + (2 * w - 12) * i / 4, y0 + 9, 1.6, G))
    # long narrow spindle hull with a fine pointed bowsprit
    hull = [(120, 20), (124, 44), (127, 80), (126, 120), (122, 150),
            (118, 150), (114, 120), (113, 80), (116, 44)]
    o.append(opoly(hull, H, d=1.5, ol=S))
    o.append(poly([(118, 34), (122, 34), (121, 12), (119, 12)], Y))    # bowsprit
    for by in (52, 72, 92, 112, 132):
        o.append(bar(114, by, 126, by, 1.2, Y))
    o.append(rivets_line(120, 40, 120, 146, 10, 0.8, S))
    # modest scalloped sail-vanes low on the hull, port and starboard
    for sx in (1, -1):
        vane = [(120 + sx * 8, 88), (120 + sx * 40, 100), (120 + sx * 44, 128),
                (120 + sx * 30, 130), (120 + sx * 10, 112)]
        o.append(opoly(vane, L, d=1.2, ol=S))
        for k in range(4):
            o.append(circ(120 + sx * (40 - 3 * k), 100 + 8 * k, 1.7, Y))
        o.append(ribbon([(120 + sx * 10, 94), (120 + sx * 34, 108)], 0.9, Y))
    # filigree scrollwork framing the fore hull
    for sx in (1, -1):
        o.append(ribbon([(120 + sx * 7, 40), (120 + sx * 14, 48),
                         (120 + sx * 8, 56), (120 + sx * 16, 64)], 0.9, Y))
    # sunburst figurehead at the bow
    for k in range(7):
        a = -math.pi / 2 + (k - 3) * 0.28
        o.append(bar(120, 36, 120 + 9 * math.cos(a), 36 + 9 * math.sin(a), 0.9, Y))
    o.append(ocirc(120, 36, 3.2, G, d=1.2))
    # crowning stern lantern
    o.append(poly([(116, 96), (124, 96), (122, 84), (118, 84)], Y))
    o.append(circ(120, 87, 2.2, G))
    return "".join(o)


# ================================================================ 4. THELN
def theln(P):
    F, L, G, T, M = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"]
    o = [grid_bg()]
    o.append(flame(120, 150, 2.4, 16, T))
    # asymmetric membrane sails with rippled trailing edges. Two shades of the
    # membrane tint, layered, so the sails read as lit fabric on black.
    M1, M2 = "#3f5f66", "#4d7078"
    spars = [(120, 56, 44, 100), (120, 56, 192, 82),
             (120, 132, 66, 172), (120, 132, 172, 150)]
    # sail 1 (big, port-forward)
    o.append(poly([(120, 56), (44, 100)] + wave_pts(44, 120, 150, 5, 9)[::-1], M1, op=0.85))
    o.append(poly([(120, 56), (44, 100), (82, 124)], M2, op=0.9))
    # sail 2 (starboard-forward, smaller)
    o.append(poly([(120, 56), (192, 82)] + wave_pts(120, 192, 146, 4, 8)[::-1], M1, op=0.8))
    # sail 3 (aft port, trailing)
    o.append(poly([(120, 132), (66, 172)] + wave_pts(66, 120, 150, 4, 7)[::-1], M1, op=0.85))
    # frame: spine + spars
    o.append(bar(120, 40, 120, 150, 2.4, F))
    for x0, y0, x1, y1 in spars:
        o.append(bar(x0, y0, x1, y1, 1.3, F))
    # long asymmetric tail boom + fin
    o.append(bar(120, 148, 106, 192, 1.6, F))
    o.append(poly([(106, 192), (94, 182), (102, 172), (112, 180)], M1, op=0.8))
    # running lights along every spar
    for x0, y0, x1, y1 in spars:
        o.append(rivets_line(x0, y0, x1, y1, 6, 1.2, G))
    o.append(rivets_line(120, 40, 120, 148, 8, 1.1, G))
    # sensory tendrils trailing from the nose
    for tx in (112, 120, 128):
        o.append(ribbon([(tx, 44), (tx + (tx - 120) * 0.4, 30), (tx + (tx - 120) * 1.1, 18)], 0.7, F))
        o.append(circ(tx + (tx - 120) * 1.1, 18, 1.2, G))
    # cockpit blister + accent pods
    o.append(ocirc(120, 50, 5.0, L, d=1.2))
    o.append(circ(120, 50, 2.6, G))
    o.append(ocirc(96, 92, 3.0, L, d=1.0))
    o.append(ocirc(150, 84, 3.0, L, d=1.0))
    return "".join(o)


# ================================================================ 5. KAETHAR
def kaethar(P):
    H, L, G, T, R, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    # aft engine block, four in a row
    o.append(opoly(rrect(92, 150, 56, 26, 2), L, d=1.5))
    for hx in (100, 112, 128, 140):
        o.append(flame(hx, 172, 2.6, 16, T))
        o.append(opoly(rrect(hx - 4, 152, 8, 22, 1), S, d=0.9))
    # hard arrowhead hull
    hull = [(120, 28), (150, 78), (152, 120), (146, 152), (94, 152), (88, 120), (90, 78)]
    o.append(opoly(hull, H, d=1.7, ol=S))
    # recessed panel seams
    for gy in (66, 92, 120):
        o.append(groove(96, gy, 48, 5, S))
    o.append(bar(120, 34, 120, 150, 1.2, S))
    # forward-swept wing pylons with hardpoint pods
    for sx in (1, -1):
        wing = [(120 + sx * 20, 96), (120 + sx * 86, 66), (120 + sx * 92, 82),
                (120 + sx * 34, 120), (120 + sx * 22, 116)]
        o.append(opoly(wing, H, d=1.4, ol=S))
        o.append(opoly(rrect(120 + sx * 74 - 6, 66, 12, 16, 1), L, d=1.1))
        o.append(chevrons(120 + sx * 24, 120 + sx * 80, 74, 3.2, 3.4, R, n=3, down=False))
    # spinal rail with a muzzle at the nose
    o.append(opoly(rrect(116, 30, 8, 116, 1), L, d=1.0))
    o.append(poly([(116, 34), (124, 34), (122, 20), (118, 20)], S))
    o.append(circ(120, 20, 1.8, R))
    # shoulder turret nacelles
    for sx in (1, -1):
        o.append(opoly(rrect(120 + sx * 30 - 8, 82, 16, 18, 2), L, d=1.2))
        o.append(bar(120 + sx * 30, 84, 120 + sx * 30, 66, 1.6, S))
        o.append(circ(120 + sx * 30, 91, 3, S))
    # unit sigil on the nose - a hard diamond-in-bar mark
    o.append(poly([(120, 60), (126, 68), (120, 76), (114, 68)], R))
    o.append(bar(112, 68, 128, 68, 1.4, R))
    return "".join(o)


# ================================================================ 6. VETL
def vetl(P):
    H, L, G, T, B, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    o = [grid_bg()]
    # soft exhaust glow at the tail base
    o.append(circ(120, 172, 7, T, op=0.20))
    o.append(circ(120, 168, 4, T, op=0.5))
    # long tapering whip tail with a barb, trailing straight back
    o.append(ribbon([(120, 148), (121, 168), (119, 188), (120, 200)], 3.2, H))
    o.append(poly([(115, 198), (125, 198), (120, 212)], B))
    for sy in (158, 172, 186):
        o.append(circ(120, sy, 1.5, S))
    # broad flat manta body - a wide smooth lens
    body = ngon(120, 100, 62, 46, 30)
    o.append(opoly(body, H, d=1.8, ol=S))
    # hide texture - mottled darker patches
    for px, py, pr in ((96, 84, 10), (142, 96, 12), (110, 124, 9), (134, 128, 8), (86, 110, 7)):
        o.append(circ(px, py, pr, S, op=0.45))
    # bone ribbing - each rib springs from its own point along the spine and
    # curves out to the wing edge (a fish/leaf vein fan, not a knot)
    o.append(bar(120, 58, 120, 150, 1.8, B))
    for sx in (1, -1):
        for k in range(5):
            sy = 70 + k * 16
            o.append(ribbon([(120, sy),
                             (120 + sx * 26, sy + 3),
                             (120 + sx * 50, sy - 4 + k * 1.5)], 0.9, B))
    # forward cephalic horn-prongs - long, curved, sweeping out and forward
    for sx in (1, -1):
        o.append(ribbon([(120 + sx * 20, 70), (120 + sx * 40, 46),
                         (120 + sx * 40, 22), (120 + sx * 24, 8), (120 + sx * 10, 6)], 3.4, H))
        o.append(ribbon([(120 + sx * 22, 66), (120 + sx * 36, 44), (120 + sx * 34, 24)], 1.0, B))
        o.append(circ(120 + sx * 10, 6, 2.4, B))
    # dorsal ridge of small spines
    for k in range(7):
        sy = 68 + k * 12
        o.append(poly([(117, sy), (123, sy), (120, sy - 6)], B))
    # ritual glow constellation on the back
    for gx, gy in ((110, 78), (128, 90), (118, 106), (132, 118), (104, 112), (124, 74)):
        o.append(circ(gx, gy, 1.8, G))
    o.append(ribbon([(110, 78), (124, 74)], 0.6, G))
    o.append(ribbon([(128, 90), (118, 106), (132, 118)], 0.6, G))
    # big eye-spots near the nose
    for sx in (1, -1):
        o.append(ocirc(120 + sx * 14, 78, 5, L, d=1.3))
        o.append(circ(120 + sx * 14, 78, 2.4, "#0e0c10"))
        o.append(circ(120 + sx * 13, 77, 0.9, G))
    return "".join(o)


# ================================================================ 7. SALT CROWS
def salt_crows(P):
    H, L, G, T, O, S = P["hull"], P["hull_lo"], P["glass"], P["thrust"], P["trim"], P["shadow"]
    BRASS, BONE = "#b98b4a", "#e8e2d4"
    o = [grid_bg()]
    # two mismatched oversized bolted engines
    o.append(flame(101, 172, 4.0, 22, O))
    o.append(flame(139, 166, 2.6, 15, O))
    o.append(opoly(rrect(88, 146, 28, 32, 2), L, d=1.6))          # big one, port
    o.append(ring_strip(101, 158, 12, 8, S, n=20))
    o.append(opoly(rrect(128, 144, 20, 22, 2), BRASS, d=1.4))     # smaller, starboard, scavenged brass
    for rx in (132, 144):
        for ry in (148, 158):
            o.append(circ(rx, ry, 1.3, S))
    # kinked asymmetric spine hull, wider to port
    hull = [(122, 40), (140, 70), (150, 104), (140, 150), (92, 150), (80, 108), (86, 78), (104, 50)]
    o.append(opoly(hull, H, d=1.6, ol=S))
    # rust streaks + mismatched panel patches
    o.append(groove(96, 66, 30, 20, "#7a3b28"))
    o.append(poly([(108, 92), (140, 96), (136, 120), (104, 116)], BRASS, op=0.55))
    o.append(rivets_line(104, 92, 136, 96, 5, 1.2, S))
    # THREE mismatched scavenged wings, bolted on crooked
    # 1: Vherathi-ish tapered (port, high)
    o.append(opoly([(88, 78), (40, 62), (34, 74), (86, 96)], "#5a4068", d=1.2))
    o.append(circ(86, 87, 1.6, S))
    # 2: Drossholt-ish blocky riveted (starboard, mid)
    o.append(opoly(rrect(150, 96, 44, 22, 2), "#8a6845", d=1.3))
    o.append(rivets_line(154, 100, 190, 100, 5, 1.2, S))
    o.append(rivets_line(154, 114, 190, 114, 5, 1.2, S))
    # 3: Federation-ish clean (port, low)
    o.append(opoly([(90, 128), (46, 150), (52, 162), (94, 146)], "#41506a", d=1.2))
    o.append(bar(70, 139, 92, 137, 1.0, "#dfe6ee"))
    # ram prow with reinforcement plates
    o.append(poly([(112, 44), (128, 44), (124, 22), (116, 22)], L))
    o.append(poly([(116, 22), (124, 22), (120, 10)], S))
    o.append(bar(110, 40, 130, 40, 1.8, S))
    o.append(bar(112, 34, 128, 34, 1.4, S))
    # boarding gantry - a folded arm with a grapnel head, on the starboard flank
    o.append(ribbon([(148, 120), (172, 128), (176, 146), (168, 156)], 2.4, S))
    o.append(poly([(168, 156), (160, 160), (166, 168), (174, 164), (172, 156)], BRASS))
    # trophy trinkets hung along the port rail
    for ty in (96, 110, 124):
        o.append(bar(82, ty, 78, ty + 5, 0.7, BRASS))
        o.append(circ(78, ty + 6, 1.8, BONE))
    # the salt-crow mark - a crude asymmetric bird glyph
    o.append(poly([(116, 96), (126, 92), (134, 98), (128, 100), (132, 108),
                   (124, 102), (118, 108), (120, 100), (112, 100)], BONE))
    return "".join(o)


SHIPS = {
 "deeprock": (deeprock, "Deeprock Gnaw"),
 "kessari": (kessari, "Kessari Reliquary"),
 "meridian": (meridian, "Meridian Argosy"),
 "theln": (theln, "Theln Kite"),
 "kaethar": (kaethar, "Kaethar Spearhead"),
 "vetl": (vetl, "Vetl Mantle"),
 "salt_crows": (salt_crows, "Salt Crow Magpie"),
}
