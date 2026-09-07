"""The `deck_grid` floor pattern: a spacing-`spacing` line grid clipped to a
room polygon. Pure geometry, no pygame - shared by `LocationScreen` (draws it
in-game) and `config/.../pipeline_atlas.py` (draws it on the review plate)."""
import math


def _centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def _bounds(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def clip_segment_convex(p1, p2, poly):
    """Clip segment p1->p2 to convex `poly` (Cyrus-Beck). Returns (a, b) inside
    the polygon or None. Winding-agnostic - each edge's inward normal is the
    one pointing toward the centroid. A concave polygon keeps only its first
    inside span, which is fine for a decorative grid."""
    cx, cy = _centroid(poly)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    t0, t1 = 0.0, 1.0
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        nx, ny = -(by - ay), (bx - ax)
        mx, my = (ax + bx) / 2, (ay + by) / 2
        if nx * (cx - mx) + ny * (cy - my) < 0:
            nx, ny = -nx, -ny
        num = nx * (p1[0] - ax) + ny * (p1[1] - ay)
        den = nx * dx + ny * dy
        if abs(den) < 1e-9:
            if num < 0:
                return None
            continue
        t = -num / den
        if den > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return (p1[0] + t0 * dx, p1[1] + t0 * dy), (p1[0] + t1 * dx, p1[1] + t1 * dy)


def grid_segments(poly, spacing):
    """Axis-aligned lines every `spacing` world units across `poly`'s bounds,
    each clipped to the room polygon."""
    minx, miny, maxx, maxy = _bounds(poly)
    segs = []
    x = math.ceil(minx / spacing) * spacing
    while x < maxx:
        clip = clip_segment_convex((x, miny - 1), (x, maxy + 1), poly)
        if clip:
            segs.append([list(clip[0]), list(clip[1])])
        x += spacing
    y = math.ceil(miny / spacing) * spacing
    while y < maxy:
        clip = clip_segment_convex((minx - 1, y), (maxx + 1, y), poly)
        if clip:
            segs.append([list(clip[0]), list(clip[1])])
        y += spacing
    return segs
