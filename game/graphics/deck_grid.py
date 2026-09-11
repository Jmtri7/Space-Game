"""Floor-pattern geometry: `tessellate()` - a repeating tile pattern (square /
hex / triangle / rhombus) that fills a room. Pure geometry, no pygame - shared
by `LocationScreen` (draws it in-game) and `config/.../pipeline_atlas.py`
(draws it on the review plate)."""
import math


def _centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def _bounds(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def _line_isect(p1, p2, a, nrm):
    """Intersection of segment p1->p2 with the line through `a` with normal `nrm`."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    den = nrm[0] * dx + nrm[1] * dy
    if abs(den) < 1e-12:
        return p2
    t = (nrm[0] * (a[0] - p1[0]) + nrm[1] * (a[1] - p1[1])) / den
    return (p1[0] + t * dx, p1[1] + t * dy)


def clip_polygon_convex(subject, clip):
    """Sutherland-Hodgman clip of `subject` polygon against convex `clip`.
    Winding-agnostic: each clip edge's inward normal is the one pointing at
    the clip centroid. Returns the (possibly empty) clipped point list."""
    cx, cy = _centroid(clip)
    out = [tuple(p) for p in subject]
    n = len(clip)
    for i in range(n):
        if not out:
            break
        ax, ay = clip[i]
        bx, by = clip[(i + 1) % n]
        nx, ny = -(by - ay), (bx - ax)
        if nx * (cx - ax) + ny * (cy - ay) < 0:
            nx, ny = -nx, -ny
        prev = out
        out = []
        s = prev[-1]
        s_in = nx * (s[0] - ax) + ny * (s[1] - ay) >= -1e-9
        for p in prev:
            p_in = nx * (p[0] - ax) + ny * (p[1] - ay) >= -1e-9
            if p_in:
                if not s_in:
                    out.append(_line_isect(s, p, (ax, ay), (nx, ny)))
                out.append(p)
            elif s_in:
                out.append(_line_isect(s, p, (ax, ay), (nx, ny)))
            s, s_in = p, p_in
    return out


def _tile_cells(kind, minx, miny, maxx, maxy, size):
    """Unclipped (points, shade) cells of a `kind` lattice covering the bounds.
    `size` is the nominal cell width in world units; `shade` cycles 0..2 for
    palette alternation."""
    cells = []
    s = max(8.0, float(size))
    if kind in ("square", "grid"):
        c0 = math.floor(minx / s) - 1
        r0 = math.floor(miny / s) - 1
        for r in range(r0, math.ceil(maxy / s) + 1):
            for c in range(c0, math.ceil(maxx / s) + 1):
                x, y = c * s, r * s
                cells.append(([(x, y), (x + s, y), (x + s, y + s), (x, y + s)], (c + 2 * r) % 3))
    elif kind in ("rhombus", "diamond"):
        h = s / 2
        c0 = math.floor((minx) / s) - 2
        r0 = math.floor((miny) / h) - 2
        for r in range(r0, math.ceil(maxy / h) + 2):
            off = h if r % 2 else 0.0
            for c in range(c0, math.ceil(maxx / s) + 2):
                x = c * s + off
                y = r * h
                cells.append(([(x, y - h), (x + h, y), (x, y + h), (x - h, y)], (c + r) % 3))
    elif kind in ("triangle", "tri"):
        h = s * math.sqrt(3) / 2
        c0 = math.floor(minx / s) - 2
        r0 = math.floor(miny / h) - 2
        for r in range(r0, math.ceil(maxy / h) + 2):
            y0, y1 = r * h, (r + 1) * h
            for c in range(c0, math.ceil(maxx / (s / 2)) + 2):
                x = c * (s / 2)
                up = (c + r) % 2 == 0
                if up:
                    cells.append(([(x, y1), (x + s, y1), (x + s / 2, y0)], (c + r) % 3))
                else:
                    cells.append(([(x, y0), (x + s, y0), (x + s / 2, y1)], (c + r + 1) % 3))
    else:  # hex (pointy-top), the default
        w = s
        h = s * 2 / math.sqrt(3)
        vspace = h * 0.75
        c0 = math.floor(minx / w) - 2
        r0 = math.floor(miny / vspace) - 2
        for r in range(r0, math.ceil(maxy / vspace) + 2):
            off = w / 2 if r % 2 else 0.0
            for c in range(c0, math.ceil(maxx / w) + 2):
                cx = c * w + off
                cy = r * vspace
                cells.append(([
                    (cx, cy - h / 2), (cx + w / 2, cy - h / 4), (cx + w / 2, cy + h / 4),
                    (cx, cy + h / 2), (cx - w / 2, cy + h / 4), (cx - w / 2, cy - h / 4),
                ], (c + r) % 3))
    return cells


def _inset_toward_centroid(poly, inset):
    """Each vertex pulled `inset` world units toward the polygon's own
    centroid - shrinking the tile before it's clipped to a room, not after,
    is what keeps two adjacent rooms' clipped fragments meeting flush at the
    shared edge instead of each shrinking toward a different (fragment)
    centroid there (see tessellate)."""
    if not inset:
        return poly
    cx, cy = _centroid(poly)
    out = []
    for x, y in poly:
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy) or 1.0
        f = min(1.0, inset / d)
        out.append((x + dx * f, y + dy * f))
    return out


def tessellate(poly, kind, size, gap=0.0):
    """Fill `poly`'s bounds with a repeating `kind` tile (square | hex |
    triangle | rhombus) of ~`size` world units, each tile clipped to the
    (convex) room polygon. `gap` shrinks each full tile toward its own
    centroid *before* clipping - a tile straddling two adjacent rooms is
    tessellated once per room, but both calls see the same lattice cell, so
    shrinking first (a deterministic function of the tile alone) then
    clipping means the two rooms' fragments still meet exactly along their
    shared edge; shrinking the already-clipped (room-specific) fragment
    instead pulls each side toward a different fragment centroid and opens a
    jagged seam. Returns [{"points": [[x, y], ...], "shade": 0..2}]."""
    minx, miny, maxx, maxy = _bounds(poly)
    out = []
    for pts, shade in _tile_cells(kind, minx, miny, maxx, maxy, size):
        if gap:
            pts = _inset_toward_centroid(pts, gap)
        clipped = clip_polygon_convex(pts, poly)
        if len(clipped) >= 3:
            out.append({"points": [[round(x, 2), round(y, 2)] for x, y in clipped], "shade": shade})
    return out
