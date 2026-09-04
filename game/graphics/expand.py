"""Design JSON -> flat render parts list.

One code path, shared by the game (at load, cached) and the design atlases.
See docs/GRAPHICS_PIPELINE.md. This module is deliberately dependency-free
(no pygame) so the atlas tooling and a headless server can import it.
"""
import math


# ---------------------------------------------------------------- colour ----

def _hex_to_rgb(s):
    s = s.lstrip("#")
    return [int(s[i:i + 2], 16) for i in (0, 2, 4)]


def _clamp(c):
    return max(0, min(255, int(round(c))))


def resolve_color(material, tone, palette, materials):
    """material name + tone ("mid"|"dark"|"light") -> [r,g,b] via the palette.
    A literal "#rrggbb" passes straight through."""
    if isinstance(material, (list, tuple)):
        return [int(v) for v in material]
    if material.startswith("#"):
        base = _hex_to_rgb(material)
    else:
        base = _hex_to_rgb(palette[material])
    spec = materials.get("materials", {}).get(material, {})
    if tone == "dark":
        d = spec.get("tone_dark", -28)
    elif tone == "light":
        d = spec.get("tone_light", 22)
    else:
        d = 0
    return [_clamp(v + d) for v in base]


# ------------------------------------------------------------- geometry ----

def ngon(cx, cy, r, n=None, rot=0):
    """A filled circle as an n-sided polygon. n defaults to a count that
    reads round at the size r (never a real circle - principle 1). rot is
    degrees, rotating the whole n-gon about its own centre."""
    if n is None:
        n = max(8, min(24, int(r * 2)))
    a0 = math.radians(rot)
    return [[cx + r * math.cos(a0 + 2 * math.pi * k / n),
             cy + r * math.sin(a0 + 2 * math.pi * k / n)] for k in range(n)]


def _centroid(pts):
    n = len(pts)
    return [sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n]


def _clip_halfplane(pts, nx, ny, d):
    """Sutherland-Hodgman: keep the part of the polygon where n.p >= d."""
    out = []
    m = len(pts)
    for i in range(m):
        a, b = pts[i], pts[(i + 1) % m]
        da, db = nx * a[0] + ny * a[1] - d, nx * b[0] + ny * b[1] - d
        if da >= 0:
            out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            out.append([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])])
    return out


def _extent_along(pts, nx, ny):
    vals = [nx * p[0] + ny * p[1] for p in pts]
    return min(vals), max(vals)


def _signed_area(pts):
    s = 0.0
    m = len(pts)
    for i in range(m):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % m]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _ray_hit(px, py, dx, dy, pts, skip):
    """Nearest s > 0 where the ray (px,py)+s*(dx,dy) crosses a polygon edge
    not touching vertex index `skip`. inf if none."""
    m = len(pts)
    best = math.inf
    for i in range(m):
        j = (i + 1) % m
        if i == skip or j == skip:
            continue
        ax, ay = pts[i]
        bx, by = pts[j]
        ex, ey = bx - ax, by - ay
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        t = ((ax - px) * ey - (ay - py) * ex) / den      # along the ray
        u = ((ax - px) * dy - (ay - py) * dx) / den      # along the edge
        if t > 1e-6 and -1e-6 <= u <= 1 + 1e-6 and t < best:
            best = t
    return best


def _vertex_normals(pts):
    """Per-vertex outward unit normal, averaged from the two incident edges
    (polygon assumed counter-clockwise)."""
    m = len(pts)
    out = []
    for i in range(m):
        p0, p1, p2 = pts[(i - 1) % m], pts[i], pts[(i + 1) % m]
        nx = ny = 0.0
        for (ax, ay), (bx, by) in ((p0, p1), (p1, p2)):
            ex, ey = bx - ax, by - ay
            nx += ey
            ny += -ex
        n = math.hypot(nx, ny) or 1.0
        out.append((nx / n, ny / n))
    return out


def _runs(flags):
    """Maximal contiguous runs of True in a circular boolean list -> list of
    index lists. A run that wraps the end is stitched to the one at the start."""
    m = len(flags)
    if all(flags):
        return [list(range(m))]
    if not any(flags):
        return []
    runs, cur = [], []
    for i in range(m):
        if flags[i]:
            cur.append(i)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if len(runs) >= 2 and runs[0][0] == 0 and runs[-1][-1] == m - 1:
        runs[0] = runs.pop() + runs[0]
    return [r for r in runs if len(r) >= 2]


def _pip(x, y, poly):
    """True if (x, y) is inside the polygon (ray cast, even-odd)."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def _nearest_on_poly(x, y, poly):
    """The closest point on the polygon's boundary - used to snap a shade
    vertex that a smoothing pass pushed outside back onto the silhouette."""
    best, bd = [x, y], 1e18
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        t = ((x - ax) * ex + (y - ay) * ey) / (ex * ex + ey * ey or 1e-12)
        t = max(0.0, min(1.0, t))
        px, py = ax + t * ex, ay + t * ey
        d = (x - px) ** 2 + (y - py) ** 2
        if d < bd:
            bd, best = d, [px, py]
    return best


def _clip_to_poly(pt, poly):
    """`pt` unchanged if inside `poly`, else snapped to the nearest boundary
    point - so a ribbon vertex can never sit outside the region."""
    return pt if _pip(pt[0], pt[1], poly) else _nearest_on_poly(pt[0], pt[1], poly)


def _relax_open(chain, k, w):
    """k passes of endpoint-preserving Laplacian smoothing on a 1-D list."""
    for _ in range(k):
        chain = [chain[0]] + [
            b + w * ((a + c) / 2 - b) for a, b, c in zip(chain, chain[1:], chain[2:])
        ] + [chain[-1]]
    return chain


def _resample_open(chain, n):
    """An open polyline resampled to `n` points evenly spaced by arc length.
    Turns an unevenly-sampled edge (a few long segments, a few short) into a
    uniform one so the taper and the offset don't facet on the long spans."""
    if len(chain) < 2 or n < 2:
        return [list(p) for p in chain]
    seg = [math.hypot(chain[i + 1][0] - chain[i][0], chain[i + 1][1] - chain[i][1])
           for i in range(len(chain) - 1)]
    total = sum(seg) or 1.0
    out = [list(chain[0])]
    acc, j = 0.0, 0
    for k in range(1, n - 1):
        target = total * k / (n - 1)
        while j < len(seg) and acc + seg[j] < target:
            acc += seg[j]
            j += 1
        if j >= len(seg):
            break
        t = (target - acc) / (seg[j] or 1.0)
        a, b = chain[j], chain[j + 1]
        out.append([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])])
    out.append(list(chain[-1]))
    return out


def _chaikin_open(chain, iters=1):
    """Corner-cutting subdivision of an open polyline; the two endpoints stay
    put, every interior corner is rounded off."""
    for _ in range(iters):
        if len(chain) < 3:
            break
        out = [list(chain[0])]
        for i in range(len(chain) - 1):
            a, b = chain[i], chain[i + 1]
            out.append([0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]])
            out.append([0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]])
        out.append(list(chain[-1]))
        chain = out
    return chain


def _crescent(region_pts, light_dir, max_frac, cap_frac, thresh):
    """One smooth ribbon polygon hugging the region's edge wherever it faces
    `light_dir` (pass -light for the dark far edge, +light for the near lit
    edge). It swells in the middle and tapers to nothing at both ends; the
    outer edge follows the region silhouette, the inner edge is that edge
    pushed inward by a smoothed depth profile, capped by how far each ray fits
    inside the polygon. Both edges are arc-length resampled, Laplacian-relaxed
    and corner-cut (Chaikin) so a coarse silhouette does not facet the shade.
    A dead band `thresh` around the terminator keeps the dark and light
    ribbons from meeting."""
    pts = region_pts if _signed_area(region_pts) > 0 else region_pts[::-1]
    m = len(pts)
    if m < 4:
        return []
    dx, dy = light_dir
    nrm = _vertex_normals(pts)
    face = [nx * dx + ny * dy for nx, ny in nrm]
    perp = _extent_along(pts, -dy, dx)
    reach = (perp[1] - perp[0]) or 1.0
    if reach < 0.9:
        return []
    max_depth = reach * max_frac
    runs = _runs([f > thresh for f in face])
    if not runs:
        return []
    run = max(runs, key=len)                      # one continuous shade per region

    # even, dense samples along the facing edge - only for the normal / depth
    # math. `n` stays well above the run's own vertex count so the resample
    # never chords across (and outside) a concave notch.
    outer0 = [list(pts[i]) for i in run]
    n = min(60, max(3 * len(outer0), 16))
    outer = _resample_open(outer0, n)

    # smoothed outward normal at each sample (poly is CCW, so right-hand normal
    # of the forward tangent points out)
    nx, ny = [], []
    for i in range(n):
        a, b = outer[max(0, i - 1)], outer[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        tl = math.hypot(tx, ty) or 1.0
        nx.append(ty / tl)
        ny.append(-tx / tl)
    nx, ny = _relax_open(nx, 3, 0.5), _relax_open(ny, 3, 0.5)
    for i in range(n):
        nl = math.hypot(nx[i], ny[i]) or 1.0
        nx[i], ny[i] = nx[i] / nl, ny[i] / nl

    # depth profile: sine taper * min(max depth, how far the ray fits inside),
    # smoothed as a 1-D signal so a near wall cannot notch the ribbon
    depth = []
    for i in range(n):
        taper = math.sin(math.pi * (i + 0.5) / n) ** 0.85
        cap = _ray_hit(outer[i][0], outer[i][1], -nx[i], -ny[i], pts, -1) * cap_frac
        depth.append(min(max_depth * taper, cap))
    depth = _relax_open(depth, 6, 0.5)

    ix = _relax_open([outer[i][0] - nx[i] * max(1e-3, depth[i]) for i in range(n)], 6, 0.45)
    iy = _relax_open([outer[i][1] - ny[i] * max(1e-3, depth[i]) for i in range(n)], 6, 0.45)

    # Outer edge = the silhouette run verbatim: it is never resampled or
    # smoothed, so it cannot leave the region. Inner edge = the depth-capped
    # inward offset, corner-cut for smoothness, with every point snapped back
    # inside if a smoothing pass pushed it out across a concave stretch.
    inner = [_clip_to_poly([ix[i], iy[i]], pts) for i in range(n)]
    inner_c = [_clip_to_poly(p, pts)
               for p in _resample_open(_chaikin_open(inner, 1), 16)]

    poly = [list(p) for p in outer0] + [list(p) for p in reversed(inner_c)]
    return [poly] if len(poly) >= 3 else []


def shade_bands(region_pts, light, materials_spec):
    """(dark_polys, light_polys) for one region - tapered crescents on the
    edges facing away from / toward the global light. See
    docs/GRAPHICS_PIPELINE.md."""
    lx, ly = light
    L = math.hypot(lx, ly) or 1.0
    lx, ly = lx / L, ly / L
    dark = _crescent(region_pts, (-lx, -ly), max_frac=0.22, cap_frac=0.55, thresh=0.16)
    lite = _crescent(region_pts, (lx, ly), max_frac=0.09, cap_frac=0.45, thresh=0.2)
    return dark, lite


# --------------------------------------------------------------- expand ----

def _emit_region(parts, sec, group, palette, materials, sec_name=None, lod=None):
    """Emit a region's fill + its shading. `sec` is the section/silhouette
    dict: `points`, `material`, optional `tone`, and shade overrides -
    `"shade": false` to omit shading, or explicit `"shade_dark"` /
    `"shade_light"` point lists (each a single polygon) authored by hand or
    in the editor, used verbatim instead of the computed crescent. If `lod`
    (the asset's on-screen size in px) is below the region's `flatten_px`,
    the shading is dropped and it draws as one flat polygon."""
    pts = sec["points"]
    material = sec["material"]
    spec = materials.get("materials", {}).get(material, {})
    light = materials.get("light", [-0.55, -0.83])
    _sec = {"sec": sec_name} if sec_name else {}
    parts.append(dict(_sec, points=[list(p) for p in pts],
                      color=resolve_color(material, sec.get("tone", "mid"), palette, materials),
                      group=group, role="fill"))
    if spec.get("emissive") or sec.get("shade") is False:
        return
    if lod is not None and sec.get("flatten_px") and lod < sec["flatten_px"]:
        return
    if "shade_dark" in sec or "shade_light" in sec:
        dark = [sec["shade_dark"]] if sec.get("shade_dark") else []
        lite = [sec["shade_light"]] if sec.get("shade_light") else []
    else:
        dark, lite = shade_bands(pts, light, spec)
    for poly in lite:
        parts.append(dict(_sec, points=[list(p) for p in poly],
                          color=resolve_color(material, "light", palette, materials),
                          group=group, role="shade_light"))
    for poly in dark:
        parts.append(dict(_sec, points=[list(p) for p in poly],
                          color=resolve_color(material, "dark", palette, materials),
                          group=group, role="shade_dark"))


def _emit_detail(parts, d, group_default, palette, materials, sec_name=None, lod=None):
    if lod is not None and d.get("min_px") and lod < d["min_px"]:
        return                            # too small on screen to bother drawing
    pts = d.get("points")
    if not pts and d.get("circle"):
        c = d["circle"]
        cx, cy, r = c[0], c[1], c[2]
        rot = c[3] if len(c) > 3 else 0    # optional 4th element: degrees, rotates the n-gon in place
        pts = ngon(cx, cy, r, rot=rot)     # a small round detail -> polygon (principle 1)
    if not pts:
        return
    p = {"points": [list(p) for p in pts],
         "color": resolve_color(d["material"], d.get("tone", "mid"), palette, materials),
         "group": d.get("group", group_default), "role": "detail",
         "note": d.get("note", "")}
    if sec_name:
        p["sec"] = sec_name
    parts.append(p)


def _rot_about(pt, c, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    x, y = pt[0] - c[0], pt[1] - c[1]
    return [c[0] + x * ca - y * sa, c[1] + x * sa + y * ca]


def _rest_transforms(design):
    """group -> (pivot, degrees) from rig.rest_splay. The arm splay rotates
    both the arm and its hand about the arm's pivot so the limb swings as one
    piece; near side one way, far side mirrored."""
    rig = design.get("rig", {})
    piv = design.get("pivots", {})
    out = {}
    arm = rig.get("rest_splay", {}).get("arm")
    if arm:
        # positive `arm` = wrists swing away from the body. y is negative-up,
        # so the near (+x) side needs a negative rotation, the far side positive.
        out["arm_near"] = out["hand_near"] = (piv["arm_near"], -arm)
        out["arm_far"] = out["hand_far"] = (piv["arm_far"], arm)
    return out


def expand_body(design, palette, materials, load=None):
    """A body design (sections + pivots + draw_order) -> parts list, each part
    tagged with its animation group. No fitting is done here - a body fits
    nothing; articles fit it. rig.rest_splay is baked in as the neutral pose
    the walk cycle swings from.

    A section may carry a `"face"` slot map ({eyes, brows, nose, lips: name});
    `load("faces", "<slot>_<name>")` supplies each slot's `details`, so the
    features are interchangeable without editing the body."""
    parts = []
    sections = design["sections"]
    order = design.get("draw_order", list(sections))
    xf = _rest_transforms(design)
    for name in order:
        sec = sections[name]
        grp = sec.get("group", name)
        tr = xf.get(grp)
        rsec = sec
        if tr:
            rsec = dict(sec, points=[_rot_about(p, *tr) for p in sec["points"]])
            for key in ("shade_dark", "shade_light"):
                if sec.get(key):
                    rsec[key] = [_rot_about(p, *tr) for p in sec[key]]
        _emit_region(parts, rsec, grp, palette, materials, sec_name=name)
        dets = list(sec.get("details", []))
        face = sec.get("face")
        if face and load:
            for slot in ("brows", "eyes", "nose", "lips"):
                if face.get(slot):
                    fp = load("faces", f"{slot}_{face[slot]}") or {}
                    dets += fp.get("details", [])
        for d in dets:
            dd = dict(d)
            if tr and d.get("points"):
                dd["points"] = [_rot_about(p, *tr) for p in d["points"]]
            _emit_detail(parts, dd, grp, palette, materials, sec_name=name)
    return parts


def _curve(body, ref):
    """'<section>.<curve>' -> the named edge polyline from a body design, in
    body coordinates."""
    sec, name = ref.split(".")
    return [list(p) for p in body["sections"][sec]["curves"][name]]


def _apply_fits(points, fits, body):
    """Replace spans of an article polygon with body edge curves, so the
    garment's edge is the body's own silhouette and follows it when the body
    is reproportioned. Each fit: {curve, from, to, reverse?}. Applied
    high-index-first so a splice doesn't shift the spans below it."""
    pts = [list(p) for p in points]
    for f in sorted(fits, key=lambda f: f["from"], reverse=True):
        seg = _curve(body, f["curve"])
        if f.get("reverse"):
            seg = seg[::-1]
        pts[f["from"]:f["to"] + 1] = seg
    return pts


def _outset(pts, d):
    """Push every vertex out along its outward normal by `d` world units, so a
    fitted garment sits just proud of the body edge instead of exactly on it
    (where a sliver of body peeks through). d defaults small."""
    if not d:
        return pts
    poly = pts if _signed_area(pts) > 0 else pts[::-1]
    out = [[x + nx * d, y + ny * d] for (x, y), (nx, ny) in zip(poly, _vertex_normals(poly))]
    return out if poly is pts else out[::-1]


def expand_article(design, palette, materials, body):
    """One garment/accessory -> parts. Regions are authored in the reference
    body's coordinates; `fits` splice body edge curves into them, `group`
    assigns the animation group so the piece moves with that body part. Each
    region is then `outset` a little so it clears the body edge."""
    parts = []
    d_out = design.get("outset", 0.12)
    for region in design.get("regions", []):
        rpts = _outset(_apply_fits(region["points"], region.get("fits", []), body),
                       region.get("outset", d_out))
        start = len(parts)
        _emit_region(parts, dict(region, points=rpts),
                     region.get("group", "torso"), palette, materials)
        for d in region.get("details", []):
            _emit_detail(parts, d, region.get("group", "torso"), palette, materials)
        for key in ("over", "under"):
            if region.get(key):
                for p in parts[start:]:
                    p[key] = region[key]
    for d in design.get("details", []):
        _emit_detail(parts, d, "torso", palette, materials)
    return parts


def apply_walk(parts, body_design, rig_walk, t):
    """Deform a composed parts list into the walk pose at cycle fraction `t`
    (0..1). Each moving group swings `deg * sin(2pi(t + phase))` about its
    pivot; a group with a `parent` inherits the parent's swing first, so a
    foot pivots on an ankle that has already moved with the leg. Everything
    above the hips rides a vertical bob at twice the stride rate. A garment
    shares its limb's group, so it moves with the limb for free."""
    piv = body_design.get("pivots", {})
    sw = rig_walk.get("swing", {})
    bob = rig_walk.get("bob", {}).get("amp", 0.0) * math.sin(2 * math.pi * 2 * t)

    def chain(g):                                        # [(pivot, angle)] root-first
        cfg = sw.get(g)
        if not cfg:
            return []
        ang = cfg["deg"] * math.sin(2 * math.pi * (t + cfg.get("phase", 0.0)))
        step = [(list(piv.get(cfg.get("pivot", g), [0, 0])), ang)]
        return (chain(cfg["parent"]) if cfg.get("parent") else []) + step

    out = []
    for p in parts:
        if "points" not in p:
            out.append(p)
            continue
        g = p.get("group", "torso")
        lower = g.startswith("leg") or g.startswith("foot")
        by = 0.0 if lower else bob
        pts = [[q[0], q[1] + by] for q in p["points"]]
        c = [([pv[0], pv[1] + by], a) for pv, a in chain(g)]   # pivots in the bobbed frame
        for i, (pivot, ang) in enumerate(c):
            pv = pivot
            for base, a in c[:i]:                        # this pivot already moved by its parents
                pv = _rot_about(pv, base, a)
            pts = [_rot_about(q, pv, ang) for q in pts]
        out.append(dict(p, points=pts))
    return out


def compose_worn(body_design, body_parts, *article_parts):
    """Merge a body's parts with the parts of the articles worn over it into
    one back-to-front list. By default an article part draws right after the
    last body part of its own animation group - a trouser leg (group
    `leg_near`) sits over that leg. A region may override placement:
      "over":  ["<group-or-section>", ...] - draw after the LAST such part
               (a skirt uses ["leg_near"]; a fringe uses ["head"]).
      "under": ["<group-or-section>", ...] - draw before the FIRST such part
               (the bulk of a hairstyle uses ["head"] so the skull hides its
               back and only the volume beyond the silhouette shows).
    Both accept animation-group names and body-section names. Groups/sections
    the body doesn't have sort to the top."""
    order = body_design.get("draw_order", list(body_design.get("sections", {})))
    groups = {}
    for name in order:
        g = body_design["sections"][name].get("group", name)
        groups.setdefault(g, len(groups))
    keyed = [(i, p) for i, p in enumerate(body_parts)]
    last, first = {}, {}
    for i, p in keyed:
        for k in (p.get("group", "torso"), p.get("sec")):
            if k is None:
                continue
            last[k] = i
            first.setdefault(k, i)
    n = len(body_parts)
    for lst in article_parts:
        for p in lst:
            if p.get("under"):
                rank = min((first.get(k, 0) for k in p["under"]), default=0) - 0.5
            elif p.get("over"):
                rank = max((last.get(k, n + groups.get(k, 999)) for k in p["over"]), default=n) + 0.5
            else:
                g = p.get("group", "torso")
                rank = last.get(g, n + groups.get(g, 999)) + 0.5
            keyed.append((rank, p))
    keyed.sort(key=lambda t: t[0])
    return [p for _, p in keyed]


def expand(design, palette, materials, body=None, load=None, lod=None):
    """Dispatch on design shape. `body` (a body design) is required for an
    article - it declares `fits_body` and its regions carry `fits`. `load(kind,
    name)` resolves referenced sub-files (face slots). `lod` is the asset's
    on-screen size in px - regions below their `flatten_px` drop their shade,
    details below their `min_px` are omitted."""
    if "sections" in design:
        return expand_body(design, palette, materials, load)
    if "regions" in design:
        return expand_article(design, palette, materials, body)
    parts = []
    sil = design.get("silhouette", [])
    dets = design.get("details", [])
    seen = set()
    for region in sil:
        g = region.get("group", "hull")
        _emit_region(parts, region, g, palette, materials, lod=lod)
        for d in dets:                       # a detail draws right after its own region
            if d.get("group", "hull") == g:
                _emit_detail(parts, d, g, palette, materials, lod=lod)
        seen.add(g)
    for d in dets:                           # details with no matching region go on top
        if d.get("group", "hull") not in seen:
            _emit_detail(parts, d, "hull", palette, materials, lod=lod)
    return parts
