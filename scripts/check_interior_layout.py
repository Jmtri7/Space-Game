"""Report interior layout problems: overlapping building footprints,
footprints sitting on a road/path decoration, and furniture packed closer
than a comfortable spacing. Read-only - prints findings for every default
story interior (or the one named on argv).

    python scripts/check_interior_layout.py [system_id]
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
pygame.init()

from game.screens.location_screen import LocationScreen  # noqa: E402
from game.utils import load_json  # noqa: E402

MIN_GAP = 14            # world units of clear floor wanted between two footprints
ROAD_COLORS = {(126, 100, 140), (78, 92, 112)}   # moon-city road decal fills
# street furniture is *meant* to line a road; only a real building sitting
# on one is a bug.
FURNITURE = {"lamp", "bollard", "bench", "planter", "seat_pod", "crate",
             "barrel", "desk", "pipe_rail", "concierge_desk", "fern", "vein_arch"}


def _is_building(bt):
    return not any(bt.endswith(f) for f in FURNITURE)


def _rects_overlap(a, b, pad=0.0):
    return (a[0] < b[0] + b[2] + pad and b[0] < a[0] + a[2] + pad
            and a[1] < b[1] + b[3] + pad and b[1] < a[1] + a[3] + pad)


def _seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy or 1.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return ((px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2) ** 0.5


def _on_road(fp, screen):
    """True when a building footprint actually overlaps a road decal - a
    real segment/rect test, not the loose axis-aligned bbox of a diagonal
    line."""
    fx, fy, fw, fh = fp
    corners = [(fx, fy), (fx + fw, fy), (fx, fy + fh), (fx + fw, fy + fh),
               (fx + fw / 2, fy + fh / 2)]
    for d in screen.decorations:
        if d["layer"] != "floor" or tuple(d["color"]) not in ROAD_COLORS:
            continue
        pts = d["points"]
        if d["shape"] == "line":
            half = max(6, d["width"]) / 2 + 4
            for a, b in zip(pts, pts[1:]):
                if any(_seg_dist(c, a, b) <= half for c in corners):
                    return True
        else:  # rect / polygon fill
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            if _rects_overlap(fp, (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))):
                return True
    return False


def check(system_id):
    system = load_json(f"config/stories/default/systems/{system_id}.json")
    for site in ("station", "moon"):
        for key, cfg in system.get(site, {}).get("interiors", {}).items():
            w, h = (1600, 1600) if site == "station" else (2400, 1800)
            scr = LocationScreen(config_data=cfg, world_width=w, world_height=h, story="default")
            label = f"{system_id}/{site}/{key}"
            fps = []
            for s in scr.structures:
                fp = scr._building_footprint(s)
                if fp:
                    fps.append((s.get("building_type"), s["x"], s["y"], fp))

            for i, (bt, sx, sy, fp) in enumerate(fps):
                if _is_building(bt) and _on_road(fp, scr):
                    print(f"{label}: BUILDING {bt} @({sx},{sy}) sits on a road decal")
                for bt2, sx2, sy2, fp2 in fps[i + 1:]:
                    # crate stacks / barrel clusters are deliberately packed
                    if bt == bt2 and bt.rsplit("_", 1)[-1] in ("crate", "barrel"):
                        continue
                    if _rects_overlap(fp, fp2):
                        print(f"{label}: {bt} @({sx},{sy}) OVERLAPS {bt2} @({sx2},{sy2})")
                    elif _rects_overlap(fp, fp2, pad=MIN_GAP):
                        print(f"{label}: {bt} @({sx},{sy}) <{MIN_GAP}u from {bt2} @({sx2},{sy2})")


if __name__ == "__main__":
    ids = [sys.argv[1]] if len(sys.argv) > 1 else ["sol_alpha", "keplers_reach", "procyon_gate"]
    for sid in ids:
        check(sid)
