"""Extract specimen SVG shapes from the design-atlas HTML and emit config
`parts` lists. Handles polygon / rect / circle / line / path (M L H V C S Q
T A Z, absolute + relative; curves/arcs flattened to short segments).

A filled shape keeps its SVG `stroke` as a per-part `"outline"`; a filled
shape with no stroke is emitted with `"outline": "none"` so it renders
un-outlined (WorldObject.draw_parts otherwise falls back to a dark outline).

Usage: python extract_atlas.py "<atlas.html>" "<vlabel substring>" [transform]
where transform is  cx cy scale flipy  applied as
   out = ((atlasX - cx) * scale, (atlasY - cy) * scale * (flipy? -1:1))
Prints a JSON parts list to stdout.
"""
import sys, re, json, math

ATLAS = sys.argv[1]
NEEDLE = sys.argv[2]
CX, CY, SCALE, FLIPY = (float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]),
                        int(sys.argv[6])) if len(sys.argv) > 6 else (0, 0, 1, 0)

html = open(ATLAS, encoding="utf-8").read()

# find each viewport block: <div class="viewport..."> ... <span class="vlabel">LABEL</span>
blocks = re.findall(r'<div class="viewport[^"]*">(.*?)<span class="vlabel">([^<]*)</span>', html, re.S)
svg = None
for body, label in blocks:
    if NEEDLE.lower() in label.lower():
        svg = body
        print(f"// matched: {label.strip()}", file=sys.stderr)
        break
if svg is None:
    sys.exit(f"no viewport whose vlabel contains {NEEDLE!r}")

num = r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?'


def nums(s):
    return [float(x) for x in re.findall(num, s)]


def flatten_path(d, seg=8):
    """path d -> list of subpaths, each a list of (x,y)."""
    tokens = re.findall(r'([MmLlHhVvCcSsQqTtAaZz])|(' + num + r')', d)
    i = 0
    cmds = []
    while i < len(tokens):
        letter = tokens[i][0]
        if not letter:
            i += 1
            continue
        args = []
        j = i + 1
        while j < len(tokens) and not tokens[j][0]:
            args.append(float(tokens[j][1]))
            j += 1
        cmds.append((letter, args))
        i = j
    subs = []
    cur = []
    x = y = 0.0
    sx = sy = 0.0
    prev_c2 = None
    for letter, a in cmds:
        rel = letter.islower()
        L = letter.upper()
        k = 0
        if L == "M":
            while k < len(a):
                nx, ny = a[k], a[k + 1]
                if rel:
                    nx += x; ny += y
                if k == 0:
                    if cur:
                        subs.append(cur)
                    cur = [(nx, ny)]
                    sx, sy = nx, ny
                else:
                    cur.append((nx, ny))
                x, y = nx, ny
                k += 2
        elif L == "L":
            while k < len(a):
                nx, ny = a[k], a[k + 1]
                if rel:
                    nx += x; ny += y
                cur.append((nx, ny)); x, y = nx, ny; k += 2
        elif L == "H":
            for v in a:
                nx = x + v if rel else v
                cur.append((nx, y)); x = nx
        elif L == "V":
            for v in a:
                ny = y + v if rel else v
                cur.append((x, ny)); y = ny
        elif L in ("C", "S"):
            step = 6 if L == "C" else 4
            while k < len(a):
                if L == "C":
                    c1 = (a[k], a[k + 1]); c2 = (a[k + 2], a[k + 3]); end = (a[k + 4], a[k + 5])
                else:
                    c1 = (2 * x - prev_c2[0], 2 * y - prev_c2[1]) if prev_c2 else (x, y)
                    c2 = (a[k], a[k + 1]); end = (a[k + 2], a[k + 3])
                if rel:
                    c1 = (c1[0] + x, c1[1] + y) if L == "C" else c1
                    c2 = (c2[0] + x, c2[1] + y); end = (end[0] + x, end[1] + y)
                for t in range(1, seg + 1):
                    tt = t / seg
                    mt = 1 - tt
                    bx = mt**3 * x + 3 * mt**2 * tt * c1[0] + 3 * mt * tt**2 * c2[0] + tt**3 * end[0]
                    by = mt**3 * y + 3 * mt**2 * tt * c1[1] + 3 * mt * tt**2 * c2[1] + tt**3 * end[1]
                    cur.append((bx, by))
                prev_c2 = c2
                x, y = end
                k += step
        elif L in ("Q", "T"):
            step = 4 if L == "Q" else 2
            while k < len(a):
                if L == "Q":
                    c1 = (a[k], a[k + 1]); end = (a[k + 2], a[k + 3])
                else:
                    c1 = (2 * x - prev_c2[0], 2 * y - prev_c2[1]) if prev_c2 else (x, y)
                    end = (a[k], a[k + 1])
                if rel:
                    if L == "Q":
                        c1 = (c1[0] + x, c1[1] + y)
                    end = (end[0] + x, end[1] + y)
                for t in range(1, seg + 1):
                    tt = t / seg
                    mt = 1 - tt
                    bx = mt**2 * x + 2 * mt * tt * c1[0] + tt**2 * end[0]
                    by = mt**2 * y + 2 * mt * tt * c1[1] + tt**2 * end[1]
                    cur.append((bx, by))
                prev_c2 = c1
                x, y = end
                k += step
        elif L == "A":
            while k < len(a):
                rx, ry, rot, laf, sf, ex, ey = a[k:k + 7]
                if rel:
                    ex += x; ey += y
                # crude: sample a circular-ish arc from (x,y) to (ex,ey)
                mx, my = (x + ex) / 2, (y + ey) / 2
                for t in range(1, seg + 1):
                    tt = t / seg
                    cur.append((x + (ex - x) * tt, y + (ey - y) * tt))
                x, y = ex, ey
                k += 7
        elif L == "Z":
            if cur:
                cur.append((sx, sy))
                subs.append(cur)
                cur = []
                x, y = sx, sy
    if cur:
        subs.append(cur)
    return subs


def tf(pts):
    out = []
    for x, y in pts:
        nx = (x - CX) * SCALE
        ny = (y - CY) * SCALE * (-1 if FLIPY else 1)
        out.append([round(nx, 3), round(ny, 3)])
    return out


import xml.etree.ElementTree as ET

parts = []
root = ET.fromstring("<svg xmlns:xlink='x'>" + re.sub(r'xmlns="[^"]*"', '', svg) + "</svg>")


class A:
    def __init__(self, s):
        self.s = s or ""

    def group(self, n):
        return self.s


def walk(el, inh):
    """inh: dict of inherited fill/stroke/stroke-width."""
    style = dict(inh)
    for k in ("fill", "stroke", "stroke-width"):
        if el.get(k) is not None:
            style[k] = el.get(k)
    tag = el.tag.split("}")[-1]
    if tag in ("polygon", "rect", "circle", "line", "path"):
        emit(tag, el, style)
    for child in el:
        walk(child, style)


def emit(tag, el, style):
    fillv = style.get("fill")
    strokev = style.get("stroke")
    fill = A(fillv) if fillv and fillv not in ("none", "url(#grid)", "url(#floorglow)") else None
    outline = strokev if (strokev and strokev not in ("none", "url(#grid)")) else None
    col = None
    if fill:
        col = fillv
    elif outline:
        col = outline       # stroke-only shape: the stroke *is* the shape's colour
        outline = None      # ...so it has no separate outline of its own
    if col is None:
        return
    swv = style.get("stroke-width")

    def g(el, k, default=0.0):
        v = el.get(k)
        return float(v) if v is not None else default

    def poly(pts):
        d = {"points": pts, "color": col, "outline": outline or "none"}
        parts.append(d)

    if tag == "polygon":
        p = nums(el.get("points", ""))
        pts = tf(list(zip(p[0::2], p[1::2])))
        if len(pts) >= 3:
            poly(pts)
    elif tag == "rect":
        x, y, w, h = g(el, "x"), g(el, "y"), g(el, "width"), g(el, "height")
        if w > 230 and h > 190:
            return  # background rect
        poly(tf([(x, y), (x + w, y), (x + w, y + h), (x, y + h)]))
    elif tag == "circle":
        c = tf([(g(el, "cx"), g(el, "cy"))])[0]
        d = {"circle": [c[0], c[1], round(g(el, "r") * SCALE, 3)], "color": col,
             "outline": outline or "none"}
        parts.append(d)
    elif tag == "line":
        pts = tf([(g(el, "x1"), g(el, "y1")), (g(el, "x2"), g(el, "y2"))])
        w = round(float(swv) * SCALE, 3) if swv else 2
        parts.append({"line": pts, "color": col, "width": w})
    elif tag == "path":
        d = el.get("d", "")
        filled = fill is not None
        for sub in flatten_path(d):
            pts = tf(sub)
            if filled and len(pts) >= 3:
                poly(pts)
            elif not filled and len(pts) >= 2:
                w = round(float(swv) * SCALE, 3) if swv else 2
                parts.append({"line": pts, "color": col, "width": w})


walk(root, {})


def hex_rgb(s):
    """'#rrggbb' / '#rgb' -> [r, g, b]; passes a list through."""
    if isinstance(s, (list, tuple)):
        return list(s)[:3]
    s = str(s).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return [int(s[i:i + 2], 16) for i in (0, 2, 4)]


MODE = sys.argv[7] if len(sys.argv) > 7 else "parts"

if MODE in ("hull", "nohull"):
    # find the largest filled polygon part - treat it as the hull
    best_i, best_area = None, -1
    for i, p in enumerate(parts):
        if "points" not in p:
            continue
        xs = [q[0] for q in p["points"]]
        ys = [q[1] for q in p["points"]]
        area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if area > best_area:
            best_area, best_i = area, i
    hull_part = parts[best_i] if best_i is not None else {}
    hull = hull_part.get("points", [])
    # The renderer draws the `parts` list and nothing else, so the hull fill
    # stays IN parts as its bottom layer. `local_points` is only a *copy* of
    # the hull outline for collision / target-bracket sizing.
    #   hull   mode: local_points = the atlas hull (parts[0] is that same fill)
    #   nohull mode: caller keeps its own hand-authored local_points; drop the
    #                atlas hull fill so the remaining (already complete) parts
    #                sit on the caller's collision shape.
    out = {"parts": parts}
    if MODE == "hull":
        out["local_points"] = hull
        if best_i not in (None, 0):
            parts.insert(0, parts.pop(best_i))
    elif best_i is not None:
        parts.pop(best_i)
    if hull_part.get("outline"):
        out["outline_color"] = hex_rgb(hull_part["outline"])
    print(json.dumps(out, indent=None))
    print(f"\n// {MODE} {len(hull)}hullpts + {len(parts)} parts"
          f" outline={out.get('outline_color')}", file=sys.stderr)
else:
    print(json.dumps(parts, indent=None))
    print(f"\n// {len(parts)} parts", file=sys.stderr)
