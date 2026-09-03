"""Vherathi Concord hardware: ships, station and furniture/decorations,
GENERATED rather than grabbed from resin-and-rivets.html - the same move
Sol Federation's `issue_plate` already made for its own hardware (see
docs/DESIGN_ATLAS.md). Buildings and layouts are unchanged for now and still
come from resin-and-rivets.html via atlas_plates.grab; see PLATES at the
bottom for exactly what this module covers.

Same silhouette language the old grabbed plates already had - asymmetric,
faceted, tapering to one dominant point, a spine of glass beads instead of a
window grid - redrawn with the same SHADING technique vherathi_outfits.py
uses instead of the old offset-outline: fill + a far-side crescent (the
culture's own `hull_lo` from cultures.json, not an invented tone) + a sliver
of highlight on the near side. No `<polygon>`/`<circle>` in this module ever
carries a stroke or an outline copy behind it.

The shading helpers here mirror vherathi_outfits.py's (sh/lt/far_side/
shade_of/ribbon) rather than importing them, so a hardware-only change can't
regress the outfits or vice versa; if that duplication ever gets annoying,
factor both into one shared module.
"""
import math

from gen_si import poly, circ, GRID

HULL, HULL_LO, GLASS, THRUST = "#483060", "#2f1e3c", "#78ffc8", "#dc5aff"
GLASS_HI = "#e8fff5"


def _rgb(c):
    c = c.lstrip("#")
    return [int(c[i:i + 2], 16) for i in (0, 2, 4)]


def _tone(col, m, a):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v * m + a))) for v in _rgb(col))


def sh(col=HULL_LO):
    return col if col != HULL_LO else HULL_LO


def lt(col):
    return _tone(col, 1.16, 22)


def far_side(pts, cx, depth=0.5):
    """The far-side shading crescent - see vherathi_outfits.far_side for the
    full reasoning (clip to x>=cx first so it works on any polygon; taper the
    inner edge to nothing at both ends so it never reads as a ruled seam)."""
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
    band = far_side(pts, cx, depth)
    return poly(band, col) if len(band) >= 3 else ""


def ribbon(pts, w0, w1):
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


def hull(pts, col=HULL, lo=None, cx=None, depth=0.5, edge=0.42):
    """A grown hull plate: fill, a far-side shadow in the culture's own
    darker hull tone (never an invented one), and a thin lit sliver on the
    near edge - the two together are what read as volume instead of a flat
    faceted card."""
    lo = lo or HULL_LO
    cx = cx if cx is not None else sum(p[0] for p in pts) / len(pts)
    near = [p for p in pts if p[0] < cx]
    o = [poly(pts, col), shade_of(pts, cx, depth, lo)]
    if len(near) >= 2:
        rim = [(x + (cx - x) * edge, y) for x, y in near]
        o.append(poly(near + rim[::-1], lt(col)))
    return "".join(o)


def vein(path, beads, w0=3.2, w1=1.1, col=HULL_LO, glass=GLASS):
    """A resin runner tracing the hull's structural line, with luminous beads
    riding it - the Vherathi answer to a window grid."""
    rb = ribbon(path, w0, w1)
    o = [poly(rb, col), shade_of(rb, sum(p[0] for p in path) / len(path), 0.5, sh(col))]
    for bx, by, br in beads:
        o.append(circ(bx, by, br + 0.6, col))
        o.append(circ(bx, by, br, glass))
        o.append(circ(bx - br * 0.3, by - br * 0.3, br * 0.36, GLASS_HI))
    return "".join(o)


def thruster(x, y, w, h, deg, metal=HULL_LO, flame=THRUST):
    """A grown asymmetric resin flare, not a machined nozzle: the port is a
    tapered organic wedge (wider where it roots on the hull, drawn off-axis
    rather than a straight tube), and the exhaust is a SEPARATE narrower
    shape rooted inside it and drawn FIRST, so the port occludes its base and
    only the tail of the jet shows past the aft edge - the same port/flame
    split the doc's ship-drawing rules ask for."""
    th = math.radians(deg)
    ax, ay = math.cos(th), math.sin(th)  # the port's own "aft" axis
    nx, ny = -ay, ax
    root = [(x - nx * w * 0.55, y - ny * w * 0.55), (x + nx * w * 0.42, y + ny * w * 0.42)]
    tip = [(x + ax * h - nx * w * 0.22, y + ay * h - ny * w * 0.22),
           (x + ax * h + nx * w * 0.30, y + ay * h + ny * w * 0.30)]
    port = [root[0], tip[0], tip[1], root[1]]
    flame_pts = [(x + ax * h * 0.35 - nx * w * 0.14, y + ay * h * 0.35 - ny * w * 0.14),
                 (x + ax * h * 1.7, y + ay * h * 1.7),
                 (x + ax * h * 0.35 + nx * w * 0.20, y + ay * h * 0.35 + ny * w * 0.20)]
    o = [f'<polygon class="flame" points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in flame_pts)}" fill="{flame}"/>']
    o.append(poly(port, metal))
    o.append(shade_of(port, x + nx, 0.5, sh(metal)))
    return "".join(o)


def grid_bg(w, h):
    return poly([(0, 0), (w, 0), (w, h), (0, h)], GRID)


# ---------------------------------------------------------------- the ships
def resin_skiff(vb, aria):
    """Small and single-minded: a kite tapering to one point, one thruster."""
    P = [grid_bg(200, 200)]
    pts = [(100, 26), (140, 78), (128, 154), (86, 176), (58, 132), (68, 70)]
    P.append(hull(pts))
    P.append(vein([(100, 34), (96, 84), (100, 130), (92, 168)],
                  ((97, 60, 2.6), (98, 106, 2.1), (94, 150, 1.8))))
    P.append(thruster(96, 176, 16, 22, 90))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def reliquary_hauler(vb, aria):
    """Bulky and cargo-heavy: a hexagonal hold with grown cargo blisters down
    one flank, three thrusters (odd, unmirrored spacing)."""
    P = [grid_bg(200, 200)]
    pts = [(96, 22), (138, 52), (146, 118), (120, 176), (72, 182), (46, 128), (58, 58)]
    P.append(hull(pts))
    for bx, by, r in ((136, 78, 12), (140, 112, 10), (130, 144, 8)):
        blister = [(bx + r * math.cos(a), by + r * math.sin(a) * 0.8)
                  for a in [i * math.pi / 6 for i in range(12)]]
        P.append(hull(blister, col="#5a4076", cx=bx - r * 0.2, depth=0.55))
    P.append(vein([(88, 30), (84, 80), (90, 130), (82, 172)],
                  ((86, 54, 2.4), (88, 104, 2.6), (85, 152, 2.0))))
    for i, (tx, a) in enumerate([(70, 92), (94, 90), (82, 88)]):
        P.append(thruster(tx, 180 - i * 2, 15, 18, a))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def thornwing_corvette(vb, aria):
    """Angular and armed: one long swept thorn-wing off the right flank,
    tapering to a sharp point, two off-centre thrusters."""
    P = [grid_bg(200, 200)]
    pts = [(96, 18), (108, 70), (172, 138), (112, 122), (100, 182), (72, 158), (66, 62)]
    P.append(hull(pts, cx=94))
    P.append(vein([(96, 26), (100, 78), (94, 130), (90, 170)],
                  ((98, 48, 2.2), (97, 96, 2.5), (92, 148, 1.9))))
    P.append(thruster(82, 172, 14, 20, 92))
    P.append(thruster(102, 176, 13, 18, 88))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def spinewing_skiff(vb, aria):
    """Slender, a spine ridge with small wing-spurs down one side, like a
    fish bone; one thruster."""
    P = [grid_bg(200, 200)]
    pts = [(100, 20), (112, 96), (106, 176), (90, 176), (86, 96), (94, 20)]
    P.append(hull(pts))
    for i, sy in enumerate((58, 84, 110, 136)):
        spur = [(106, sy), (128 + i * 3, sy - 6), (112, sy + 10)]
        scx = sum(p[0] for p in spur) / 3          # each spur shaded on its OWN
        P.append(hull(spur, col="#5a4076", cx=scx, depth=0.55))  # centroid, not the hull's
    P.append(vein([(97, 26), (98, 90), (95, 150), (94, 172)],
                  ((97, 46, 2.0), (97, 108, 2.2), (95, 160, 1.7))))
    P.append(thruster(98, 176, 12, 18, 90))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def chorus_tender(vb, aria):
    """Rounded, a cluster of small grown pods along one side, echoing the
    bubble-cluster the Concord wears on its helms."""
    P = [grid_bg(200, 200)]
    pts = [(98, 24), (128, 50), (134, 120), (114, 172), (82, 172), (64, 116), (72, 48)]
    P.append(hull(pts))
    for bx, by, r in ((136, 66, 9), (140, 92, 7.5), (134, 118, 8.5), (128, 144, 6.5)):
        P.append(circ(bx, by, r, "#5a4076"))
        P.append(shade_of([(bx - r, by - r), (bx + r, by - r), (bx + r, by + r), (bx - r, by + r)],
                          bx, 0.5, sh(HULL_LO)))
        P.append(circ(bx - r * 0.3, by - r * 0.55, r * 0.32, GLASS))
    P.append(vein([(94, 32), (90, 84), (94, 132), (90, 168)],
                  ((92, 54, 2.3), (92, 104, 2.4), (91, 150, 1.9))))
    P.append(thruster(90, 172, 15, 18, 91))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def pale_ark(vb, aria):
    """The largest hull, pale-toned, a tall grown vessel with a dorsal fin
    near the crown and three thrusters at its base."""
    P = [grid_bg(200, 200)]
    pal = "#8f7aa8"
    pts = [(100, 14), (128, 44), (136, 108), (128, 168), (98, 188), (68, 168), (60, 100), (74, 42)]
    P.append(hull(pts, col=pal, lo="#5a4c74"))
    fin = [(112, 34), (134, 20), (124, 62), (110, 58)]
    P.append(hull(fin, col=pal, lo="#5a4c74", cx=118))
    P.append(vein([(98, 24), (94, 80), (100, 130), (96, 176)],
                  ((96, 46, 2.6), (98, 100, 2.8), (95, 150, 2.2), (97, 178, 1.8)), glass=GLASS))
    for i, tx in enumerate((80, 98, 116)):
        P.append(thruster(tx, 186 - (1 if i == 1 else 0), 14, 20, 90, metal="#5a4c74"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


# --------------------------------------------------------------- station(s)
def _dock_arm(cx, cy, ang, ln, w, col, lo):
    th = math.radians(ang)
    tip = (cx + ln * math.cos(th), cy + ln * math.sin(th))
    p = ribbon([(cx, cy), (tip[0], tip[1])], w, w * 0.4)
    return poly(p, col) + shade_of(p, cx, 0.5, lo) + circ(tip[0], tip[1], w * 0.55, col)


def vherathi_station(vb, aria):
    """The shipped silhouette - a grown hub ring with docking arms radiating
    at uneven angles and lengths - reshaded rather than reshaped."""
    P = [grid_bg(240, 200)]
    cx, cy, r = 120, 104, 46
    ring = [(cx + r * math.cos(a), cy + r * math.sin(a))
           for a in [i * math.pi / 18 for i in range(36)]]
    P.append(hull(ring, cx=cx))
    P.append(circ(cx, cy, r * 0.42, HULL_LO))
    for ang, ln, w in ((-32, 78, 7), (18, 62, 6), (146, 58, 6.5), (208, 50, 5.5)):
        P.append(_dock_arm(cx, cy, ang, ln, w, HULL, HULL_LO))
    # the vein hugs the ring rather than crossing the hub, so it never cuts
    # into the reactor-core dot drawn on top of it
    P.append(vein([(cx - r * 0.62, cy - r * 0.55), (cx - r * 0.78, cy),
                   (cx - r * 0.55, cy + r * 0.62)],
                  ((cx - r * 0.72, cy - r * 0.28, 2.3), (cx - r * 0.70, cy + r * 0.30, 2.1))))
    P.append(circ(cx, cy, r * 0.16, "#e8fff5"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def vherathi_bloom_cluster(vb, aria):
    """A NEW station design: several grown pods clustered around a spine,
    the way a reef clusters coral heads - no ring symmetry at all."""
    P = [grid_bg(240, 200)]
    pods = [(96, 100, 34), (150, 76, 24), (156, 132, 20), (64, 60, 18), (60, 144, 16)]
    for cx, cy, r in pods:
        ring = [(cx + r * math.cos(a), cy + r * math.sin(a))
               for a in [i * math.pi / 16 for i in range(32)]]
        P.append(hull(ring, cx=cx))
    for (ax, ay, ar), (bx, by, br) in zip(pods, pods[1:]):
        P.append(hull(ribbon([(ax, ay), (bx, by)], min(ar, br) * 0.7, min(ar, br) * 0.5),
                      cx=(ax + bx) / 2))
    # the vein first, then the core dot LAST so it isn't cut by the ribbon
    # passing under it (the same fix the station needed)
    P.append(vein([(96, 74), (100, 100), (94, 122), (98, 140)],
                  ((98, 86, 2.4), (96, 112, 2.2), (97, 132, 1.8))))
    for cx, cy, r in pods[1:]:
        P.append(circ(cx, cy, r * 0.22, GLASS))
    P.append(circ(96, 100, 10, "#e8fff5"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def vherathi_reef_spire(vb, aria):
    """A NEW station design: a tall vertical spire tapering to a point, with
    docking arms jutting at different heights - the vertical counterpart to
    the horizontal ring, in the same tapering-to-one-point ship language."""
    P = [grid_bg(240, 200)]
    pts = [(120, 12), (140, 60), (146, 120), (130, 184), (104, 184), (92, 116), (98, 56)]
    P.append(hull(pts, cx=116))
    P.append(vein([(118, 24), (114, 80), (120, 132), (114, 178)],
                  ((116, 44, 2.6), (117, 96, 2.8), (115, 148, 2.2), (116, 172, 1.8))))
    for ang, ln, w, ay in ((160, 46, 6, 76), (24, 40, 5.5, 108), (196, 34, 5, 150)):
        P.append(_dock_arm(120 if ay == 76 else (118 if ay == 108 else 116), ay,
                           ang, ln, w, HULL, HULL_LO))
    P.append(circ(120, 30, 6, "#e8fff5"))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


# --------------------------------------------------------- furniture & deco
def light_column(vb, aria):
    P = [grid_bg(200, 210)]
    pts = [(94, 20), (108, 20), (112, 150), (100, 190), (88, 150)]
    P.append(hull(pts, cx=98))
    P.append(vein([(100, 30), (98, 90), (100, 145)],
                  ((99, 50, 2.2), (99, 100, 2.4), (99, 140, 2.0))))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def fern_basin(vb, aria):
    P = [grid_bg(200, 210)]
    pts = [(60, 168), (140, 168), (132, 190), (68, 190)]
    P.append(hull(pts, cx=100))
    for i, (fx, fh) in enumerate([(76, 60), (94, 78), (112, 54), (126, 66)]):
        frond = [(fx, 168), (fx + 6 - i, 168 - fh), (fx + 10, 168)]
        P.append(hull(frond, col="#5a7a56", lo="#33502f", cx=fx + 4))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def lounge_pod(vb, aria):
    P = [grid_bg(200, 210)]
    cx, cy = 100, 150
    pts = [(cx + 46 * math.cos(a), cy + 26 * math.sin(a) - (10 if math.sin(a) < 0 else 0))
          for a in [math.pi + i * math.pi / 16 for i in range(17)]]
    P.append(hull(pts, cx=cx))
    P.append(vein([(70, 128), (100, 118), (130, 128)], ((100, 120, 2.0),)))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def concierge_desk(vb, aria):
    P = [grid_bg(200, 210)]
    pts = [(48, 150), (128, 138), (152, 150), (152, 176), (48, 176)]
    P.append(hull(pts, cx=100))
    P.append(vein([(60, 148), (100, 142), (144, 150)], ((70, 146, 1.8), (128, 146, 1.6))))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def resin_bench(vb, aria):
    P = [grid_bg(200, 210)]
    pts = [(56, 156), (144, 150), (150, 172), (50, 178)]
    P.append(hull(pts, cx=100))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


def vein_arch(vb, aria):
    P = [grid_bg(200, 210)]
    outer = [(40 + 120 * (1 - math.cos(a)) / 2, 190 - 150 * math.sin(a))
            for a in [i * math.pi / 20 for i in range(21)]]
    inner = [(52 + 96 * (1 - math.cos(a)) / 2, 190 - 116 * math.sin(a))
            for a in reversed([i * math.pi / 20 for i in range(21)])]
    P.append(hull(outer + inner, cx=100))
    P.append(vein([outer[3], outer[8], outer[13], outer[17]],
                  ((outer[6][0], outer[6][1], 2.2), (outer[11][0], outer[11][1], 2.0))))
    return f'<svg viewBox="{vb}" role="img" aria-label="{aria}">{"".join(P)}</svg>'


PLATES = {
 "resin skiff":             (resin_skiff, "0 0 200 200"),
 "reliquary hauler":        (reliquary_hauler, "0 0 200 200"),
 "thornwing corvette":      (thornwing_corvette, "0 0 200 200"),
 "spinewing skiff":         (spinewing_skiff, "0 0 200 200"),
 "chorus tender":           (chorus_tender, "0 0 200 200"),
 "pale ark":                (pale_ark, "0 0 200 200"),
 "redesigned vherathi station": (vherathi_station, "0 0 240 200"),
 "vherathi bloom cluster":  (vherathi_bloom_cluster, "0 0 240 200"),
 "vherathi reef spire":     (vherathi_reef_spire, "0 0 240 200"),
 "vherathi light column":   (light_column, "0 0 200 210"),
 "vherathi fern basin":     (fern_basin, "0 0 200 210"),
 "vherathi lounge pod":     (lounge_pod, "0 0 200 210"),
 "vherathi concierge desk": (concierge_desk, "0 0 200 210"),
 "vherathi resin bench":    (resin_bench, "0 0 200 210"),
 "vein arch":               (vein_arch, "0 0 200 210"),
}


def plate(label):
    """The <svg> for a generated Vherathi hardware plate, matched by label
    substring (case-insensitive) - mirrors gen_si.issue_plate. Raises
    StopIteration if this module doesn't cover that label (buildings and
    layouts don't yet - the caller should fall back to grab())."""
    key = next(k for k in PLATES if k in label.lower())
    fn, vb = PLATES[key]
    return fn(vb, label)
