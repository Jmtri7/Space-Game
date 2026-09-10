"""Phase 6.1 - the Halcyon slice, end to end. The worked example / template
for 6.2-6.6.

Produces, self-contained (run after gen_assets; see docs/gen/README.md):
  - graphics/ships/authority_{courier,hauler,patrol}.json   first-pass Authority hulls
  - graphics/stations/authority_station.json                 Authority orbital dock
  - graphics/buildings/authority_{hall,housing,spire}.json   Authority elevation buildings
  - patched graphics.json entries (thrusters / local_points / windows)
  - graphics/palettes/authority_dress.json                   navy + chrome dress
  - systems/halcyon.json      real Hub Control floor plan + full NPC roster
  - missions.json             the "induction" anchor tutorial (merged in - the
                              other slices add their own anchor missions here)
  - story.json                loan terms + version + description

Harbor Authority style (cultures.json theme): orderly and symmetrical,
chrome-and-navy livery, evenly ranked windows, a docking-guidance chevron
on every surface, over-signed. Rectilinear - no swept deltas, no circles.
"""
import json

S = "config/stories/the_long_silence"
G = f"{S}/graphics"


def w(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def r(path):
    with open(path) as f:
        return json.load(f)


# ======================================================================
# 1. SHIP DESIGNS  (units: fractions of `size`; nose = -y; symmetric about x=0)
# ======================================================================
def chevron(cy, half=0.22, drop=0.18, th=0.07):
    """A downward-pointing > guidance chevron centred on x=0 at height cy."""
    return [[-half, cy], [0, cy + drop], [half, cy], [half, cy - th],
            [0, cy + drop - th], [-half, cy - th]]


AUTHORITY_COURIER = {
    "identity": "Harbor Authority Courier - a small fast dispatch cutter. A clean rectilinear wedge: blunt chevron prow, a single ranked window band along each flank, a squared-off tail with two outboard thruster nacelles and a low dorsal fin. Chrome-and-navy, a lit guidance chevron on the nose. Reads at a dozen pixels as a bright-nosed arrow-box.",
    "tier": "ship_near", "palette": "authority", "size": 11,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "deep", "flatten_px": 40, "note": "wedge hull",
         "points": [[0.0, -1.18], [0.30, -0.66], [0.36, 0.62], [0.30, 1.02],
                    [-0.30, 1.02], [-0.36, 0.62], [-0.30, -0.66]]},
        {"group": "canopy", "color": "glass", "shade": "sheen", "flatten_px": 60, "note": "forward canopy",
         "points": [[0.0, -0.7], [0.14, -0.42], [0.12, 0.05], [0.0, 0.16], [-0.12, 0.05], [-0.14, -0.42]]},
        {"group": "nac_r", "color": "engine", "shade": "deep", "flatten_px": 50, "note": "right nacelle",
         "points": [[0.30, 0.28], [0.52, 0.28], [0.52, 1.06], [0.30, 1.06]]},
        {"group": "nac_l", "color": "engine", "shade": "deep", "flatten_px": 50, "note": "left nacelle",
         "points": [[-0.30, 0.28], [-0.52, 0.28], [-0.52, 1.06], [-0.30, 1.06]]},
        {"group": "fin", "color": "metal", "shade": "metal", "flatten_px": 45, "note": "dorsal fin",
         "points": [[-0.05, 0.2], [0.05, 0.2], [0.05, 0.98], [-0.05, 0.98]]},
    ],
    "details": [
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 55,
         "note": "guidance chevron, prow", "points": chevron(-0.86, half=0.2, drop=0.16)},
        {"group": "hull", "color": "hull_dk", "shade": "matte", "role": "detail", "min_px": 70,
         "note": "window band, right", "points": [[0.20, -0.5], [0.28, -0.5], [0.28, 0.5], [0.20, 0.5]]},
        {"group": "hull", "color": "hull_dk", "shade": "matte", "role": "detail", "min_px": 70,
         "note": "window band, left", "points": [[-0.20, -0.5], [-0.28, -0.5], [-0.28, 0.5], [-0.20, 0.5]]},
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 90,
         "note": "nav light, nose", "circle": [0.0, -1.1, 0.045]},
        {"group": "nac_r", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12,
         "note": "right thruster", "circle": [0.41, 1.06, 0.11]},
        {"group": "nac_l", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12,
         "note": "left thruster", "circle": [-0.41, 1.06, 0.11]},
    ],
}

AUTHORITY_HAULER = {
    "identity": "Harbor Authority Hauler - a mid-weight box freighter. A long slab hull carrying four ranked container cells, a small command cab set forward-left, a wide squared engine block aft with a paired thruster. Every cell is stencilled; a guidance chevron on the bow. Reads as a stack of lit boxes with a bright nose.",
    "tier": "ship_near", "palette": "authority", "size": 20,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "deep", "flatten_px": 60, "note": "slab hull",
         "points": [[-0.30, -1.1], [0.30, -1.1], [0.42, -0.9], [0.42, 0.86],
                    [0.30, 1.08], [-0.30, 1.08], [-0.42, 0.86], [-0.42, -0.9]]},
        {"group": "cab", "color": "glass", "shade": "sheen", "flatten_px": 55, "note": "command cab",
         "points": [[-0.36, -1.02], [-0.02, -1.02], [-0.02, -0.66], [-0.36, -0.66]]},
        {"group": "engine", "color": "engine", "shade": "deep", "flatten_px": 55, "note": "engine block",
         "points": [[-0.46, 0.78], [0.46, 0.78], [0.4, 1.16], [-0.4, 1.16]]},
    ],
    "details": [
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 55,
         "note": "guidance chevron, bow", "points": chevron(-0.98, half=0.24, drop=0.16)},
        # four container cells as recessed panels
        *[{"group": "hull", "color": "hull_dk", "shade": "matte", "role": "detail", "min_px": 40,
           "note": f"cell {i}", "points": [[-0.34, y], [0.34, y], [0.34, y + 0.4], [-0.34, y + 0.4]]}
          for i, y in enumerate((-0.56, -0.12, 0.32))],
        {"group": "hull", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 60,
         "note": "cell lamp strip", "points": [[-0.3, -0.16], [0.3, -0.16], [0.3, -0.1], [-0.3, -0.1]]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 14,
         "note": "right thruster", "circle": [0.24, 1.14, 0.13]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 14,
         "note": "left thruster", "circle": [-0.24, 1.14, 0.13]},
    ],
}

AUTHORITY_PATROL = {
    "identity": "Harbor Authority Patrol - a broad-shouldered interceptor. A flat rectilinear delta with squared wingtips, two forward gun rails flanking a narrow prow, a raised armoured canopy, and three ranked thrusters across a wide tail. Navy hull, chrome edging, a big lit chevron down the spine. Reads as an aggressive lit arrowhead.",
    "tier": "ship_near", "palette": "authority", "size": 16,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "deep", "flatten_px": 45, "note": "delta hull",
         "points": [[0.0, -1.16], [0.16, -0.7], [0.9, 0.5], [0.9, 0.92], [0.5, 0.92],
                    [0.3, 1.1], [-0.3, 1.1], [-0.5, 0.92], [-0.9, 0.92], [-0.9, 0.5], [-0.16, -0.7]]},
        {"group": "gun_r", "color": "metal", "shade": "metal", "flatten_px": 50, "note": "right gun rail",
         "points": [[0.14, -1.02], [0.24, -1.02], [0.24, -0.3], [0.14, -0.3]]},
        {"group": "gun_l", "color": "metal", "shade": "metal", "flatten_px": 50, "note": "left gun rail",
         "points": [[-0.14, -1.02], [-0.24, -1.02], [-0.24, -0.3], [-0.14, -0.3]]},
        {"group": "canopy", "color": "glass", "shade": "sheen", "flatten_px": 55, "note": "armoured canopy",
         "points": [[0.0, -0.5], [0.15, -0.24], [0.13, 0.18], [0.0, 0.3], [-0.13, 0.18], [-0.15, -0.24]]},
    ],
    "details": [
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 45,
         "note": "spine chevron", "points": chevron(-0.6, half=0.26, drop=0.2, th=0.08)},
        {"group": "hull", "color": "hull_dk", "shade": "matte", "role": "detail", "min_px": 70,
         "note": "wing panel R", "points": [[0.32, 0.32], [0.82, 0.6], [0.8, 0.82], [0.36, 0.66]]},
        {"group": "hull", "color": "hull_dk", "shade": "matte", "role": "detail", "min_px": 70,
         "note": "wing panel L", "points": [[-0.32, 0.32], [-0.82, 0.6], [-0.8, 0.82], [-0.36, 0.66]]},
        {"group": "gun_r", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 20, "note": "muzzle R", "circle": [0.19, -1.0, 0.05]},
        {"group": "gun_l", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 20, "note": "muzzle L", "circle": [-0.19, -1.0, 0.05]},
        *[{"group": "hull", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12,
           "note": f"thruster {i}", "circle": [x, 1.08, 0.1]} for i, x in enumerate((-0.34, 0.0, 0.34))],
    ],
}

SHIP_DESIGNS = {
    "authority_courier": (AUTHORITY_COURIER, [[0.41, 1.02], [-0.41, 1.02]],
                          [[0.0, -1.18], [0.36, 0.62], [0.30, 1.06], [-0.30, 1.06], [-0.36, 0.62]]),
    "authority_hauler": (AUTHORITY_HAULER, [[0.24, 1.1], [-0.24, 1.1]],
                         [[-0.42, -0.9], [0.42, -0.9], [0.42, 0.86], [-0.42, 0.86]]),
    "authority_patrol": (AUTHORITY_PATROL, [[-0.34, 1.05], [0.0, 1.05], [0.34, 1.05]],
                         [[0.0, -1.16], [0.9, 0.9], [0.3, 1.1], [-0.3, 1.1], [-0.9, 0.9]]),
}

for sid, (design, thr, local) in SHIP_DESIGNS.items():
    w(f"{G}/ships/{sid}.json", design)

gfx = r(f"{S}/graphics.json")
for sid, (design, thr, local) in SHIP_DESIGNS.items():
    e = gfx["ships"][sid]
    e["local_points"] = local
    e["thrusters"] = thr
    e["thruster_width"] = 0.06
    e["thruster_length"] = 20

# ======================================================================
# 2. STATION DESIGN  (radial; you dock at an arm end)
# ======================================================================
AUTHORITY_STATION = {
    "identity": "Harbor Authority orbital control - Hub Control. A rectilinear cross: a squared central control block with a lit core, four straight docking arms ending in blunt pods, and a tall signal mast off the top. Ranked window bands down every arm; a guidance chevron on each pod. Chrome-and-navy. Reads as a bright-cored plus with a mast.",
    "tier": "station", "palette": "authority", "size": 46,
    "units": "fractions of `size`; radially symmetric bar the mast, so orientation is nearly free.",
    "silhouette": [
        {"group": "arms", "color": "hull", "shade": "deep", "flatten_px": 55, "note": "the four docking arms as one plus",
         "points": [[-0.16, -1.0], [0.16, -1.0], [0.16, -0.16], [1.0, -0.16], [1.0, 0.16],
                    [0.16, 0.16], [0.16, 1.0], [-0.16, 1.0], [-0.16, 0.16], [-1.0, 0.16],
                    [-1.0, -0.16], [-0.16, -0.16]]},
        {"group": "core", "color": "hull", "shade": "deep", "flatten_px": 45, "note": "central control block",
         "points": [[-0.34, -0.34], [0.34, -0.34], [0.34, 0.34], [-0.34, 0.34]]},
        {"group": "lit", "color": "glass", "shade": "flat", "flatten_px": 200, "note": "lit core",
         "points": [[-0.15, -0.15], [0.15, -0.15], [0.15, 0.15], [-0.15, 0.15]]},
        {"group": "mast", "color": "metal", "shade": "metal", "flatten_px": 60, "note": "signal mast",
         "points": [[-0.05, -1.0], [0.05, -1.0], [0.05, -1.5], [-0.05, -1.5]]},
        *[{"group": f"pod_{d}", "color": "hull_dk", "shade": "matte", "flatten_px": 60, "note": f"{d} pod", "points": p}
          for d, p in (
              ("n", [[-0.26, -1.14], [0.26, -1.14], [0.3, -0.96], [-0.3, -0.96]]),
              ("s", [[-0.26, 1.14], [0.26, 1.14], [0.3, 0.96], [-0.3, 0.96]]),
              ("e", [[1.14, -0.26], [1.14, 0.26], [0.96, 0.3], [0.96, -0.3]]),
              ("w", [[-1.14, -0.26], [-1.14, 0.26], [-0.96, 0.3], [-0.96, -0.3]]))],
    ],
    "details": [
        {"group": "core", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 18, "note": "core glow", "circle": [0.0, 0.0, 0.22]},
        {"group": "mast", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 30, "note": "mast beacon", "circle": [0.0, -1.5, 0.06]},
        *[{"group": "arms", "color": "hull_dk", "shade": "matte", "role": "detail", "min_px": 80, "note": f"window band {d}", "points": p}
          for d, p in (
              ("n", [[-0.09, -0.9], [0.09, -0.9], [0.09, -0.3], [-0.09, -0.3]]),
              ("s", [[-0.09, 0.3], [0.09, 0.3], [0.09, 0.9], [-0.09, 0.9]]),
              ("e", [[0.3, -0.09], [0.9, -0.09], [0.9, 0.09], [0.3, 0.09]]),
              ("w", [[-0.9, -0.09], [-0.3, -0.09], [-0.3, 0.09], [-0.9, 0.09]]))],
        *[{"group": f"pod_{d}", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 26, "note": f"dock light {d}", "circle": c}
          for d, c in (("n", [0.0, -1.06, 0.05]), ("s", [0.0, 1.06, 0.05]), ("e", [1.06, 0.0, 0.05]), ("w", [-1.06, 0.0, 0.05]))],
    ],
}
w(f"{G}/stations/authority_station.json", AUTHORITY_STATION)
se = gfx["space_stations"]["authority_station"]
se["local_points"] = [[-0.16 * 46, -1.0 * 46], [0.16 * 46, -1.0 * 46], [0.16 * 46, -0.16 * 46],
                      [1.0 * 46, -0.16 * 46], [1.0 * 46, 0.16 * 46], [0.16 * 46, 0.16 * 46],
                      [0.16 * 46, 1.0 * 46], [-0.16 * 46, 1.0 * 46], [-0.16 * 46, 0.16 * 46],
                      [-1.0 * 46, 0.16 * 46], [-1.0 * 46, -0.16 * 46], [-0.16 * 46, -0.16 * 46]]

# ======================================================================
# 3. BUILDING DESIGNS  (view: elevation; x=facade about 0, y<=0 above floor)
# ======================================================================
AUTHORITY_HALL = {
    "identity": "Harbor Authority Hall - the public records-and-approach hall, head-on. A wide low civic block: a flat chrome fascia carrying a lit guidance chevron dead centre, a colonnade of six square navy piers along the front, a deep recessed entry, and a ranked band of tall narrow windows between the piers. Over-signed, symmetrical.",
    "tier": "building", "palette": "authority", "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~1.8x PLAYER_H to the fascia, ~3.6x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "matte", "note": "wall", "flatten_px": 60,
         "points": [[-58, 0], [58, 0], [58, -48], [-58, -48]]},
        {"group": "body", "color": "hull", "shade": "deep", "note": "fascia band",
         "points": [[-58, -48], [58, -48], [58, -58], [-58, -58]]},
        {"group": "body", "color": "engine", "shade": "matte", "note": "recessed entry",
         "points": [[-14, -30], [14, -30], [14, 0], [-14, 0]]},
    ],
    "details": [
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 16,
         "note": "guidance chevron on the fascia",
         "points": [[-14, -53], [0, -47], [14, -53], [14, -57], [0, -51], [-14, -57]]},
        *[{"group": "body", "color": "metal", "shade": "metal", "role": "detail", "min_px": 12, "note": f"pier {i}",
           "points": [[x - 4, -48], [x + 4, -48], [x + 4, 0], [x - 4, 0]]}
          for i, x in enumerate((-50, -30, -18, 18, 30, 50))],
        *[{"group": "body", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 13, "note": f"window {i}",
           "points": [[x - 3, -44], [x + 3, -44], [x + 3, -14], [x - 3, -14]]}
          for i, x in enumerate((-40, -24, 24, 40))],
    ],
}

AUTHORITY_HOUSING = {
    "identity": "Harbor Authority Housing - a tall navy residential slab, head-on. Four decks of identical ranked windows in a strict grid, a chrome parapet, a single centred lit entry, and a painted deck-number chevron above the door. Deliberately uniform - Authority housing is a filing system you live in.",
    "tier": "building", "palette": "authority", "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~3.5x PLAYER_H tall, ~2.2x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "matte", "note": "wall", "flatten_px": 60,
         "points": [[-34, 0], [34, 0], [34, -104], [-34, -104]]},
        {"group": "body", "color": "metal", "shade": "metal", "note": "parapet",
         "points": [[-36, -104], [36, -104], [36, -110], [-36, -110]]},
        {"group": "body", "color": "engine", "shade": "matte", "note": "entry",
         "points": [[-8, -18], [8, -18], [8, 0], [-8, 0]]},
    ],
    "details": [
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 14, "note": "deck chevron over the door",
         "points": [[-9, -26], [0, -21], [9, -26], [9, -29], [0, -24], [-9, -29]]},
        *[{"group": "body", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 11, "note": f"win r{ri} c{ci}",
           "points": [[cx - 6, cy], [cx + 6, cy], [cx + 6, cy + 12], [cx - 6, cy + 12]]}
          for ri, cy in enumerate((-98, -76, -54, -32))
          for ci, cx in enumerate((-22, -8, 8, 22))],
    ],
}

AUTHORITY_SPIRE = {
    "identity": "Harbor Authority Spire - the control mast, head-on: whose ground this is. A stepped navy tower in three receding tiers, a chrome-railed gallery near the top, a rotating scan-lamp at the peak, and a lit chevron blazon on the mid tier. Tall, narrow, symmetrical, unmistakable.",
    "tier": "building", "palette": "authority", "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~5x PLAYER_H tall, ~1.4x wide at the base",
    "silhouette": [
        {"group": "body", "color": "hull", "shade": "deep", "note": "base tier", "flatten_px": 55,
         "points": [[-22, 0], [22, 0], [22, -60], [-22, -60]]},
        {"group": "body", "color": "hull", "shade": "deep", "note": "mid tier",
         "points": [[-16, -60], [16, -60], [16, -118], [-16, -118]]},
        {"group": "body", "color": "hull", "shade": "deep", "note": "top tier",
         "points": [[-10, -118], [10, -118], [10, -150], [-10, -150]]},
        {"group": "gallery", "color": "metal", "shade": "metal", "note": "railed gallery",
         "points": [[-15, -122], [15, -122], [15, -128], [-15, -128]]},
        {"group": "mast", "color": "metal", "shade": "metal", "note": "peak mast",
         "points": [[-2, -150], [2, -150], [2, -166], [-2, -166]]},
    ],
    "details": [
        {"group": "mast", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 24, "note": "scan lamp", "circle": [0, -166, 5]},
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 16, "note": "chevron blazon, mid tier",
         "points": [[-10, -92], [0, -86], [10, -92], [10, -96], [0, -90], [-10, -96]]},
        *[{"group": "body", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 12, "note": f"base window {i}",
           "points": [[x - 4, -52], [x + 4, -52], [x + 4, -12], [x - 4, -12]]} for i, x in enumerate((-12, 12))],
        *[{"group": "body", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 12, "note": f"top window {i}",
           "points": [[x - 3, -144], [x + 3, -144], [x + 3, -132], [x - 3, -132]]} for i, x in enumerate((-4, 4))],
    ],
}

BUILDINGS = {
    "authority_hall": (AUTHORITY_HALL, {"width": 116, "depth": 30.0}),
    "authority_housing": (AUTHORITY_HOUSING, {"width": 72, "depth": 24.0}),
    "authority_spire": (AUTHORITY_SPIRE, {"width": 44, "depth": 18.0}),
}
bt = r(f"{S}/building_types.json")
for bid, (design, fp) in BUILDINGS.items():
    w(f"{G}/buildings/{bid}.json", design)
    bt[bid]["footprint"] = fp
w(f"{S}/building_types.json", bt)

# ======================================================================
# 4. DRESS PALETTE  (navy + chrome, over the shared civilian human tones)
# ======================================================================
dress = r(f"{G}/palettes/authority_dress.json")
dress["identity"] = "Harbor Authority dress - a pressed navy uniform with chrome fittings and an amber approach-light trim. Human skin/hair unchanged."
dress.update({"cloth": "#3a4560", "denim": "#2b3450", "knit": "#4a5878", "leather": "#4a4a52",
              "metal": "#c8cdd6", "glass": "#b4dcff", "lamp": "#ffd98a"})
w(f"{G}/palettes/authority_dress.json", dress)

# ======================================================================
# 4b. BESPOKE AUTHORITY WARDROBE
#     Five small free-drawn identity articles (no body fitting - they sit
#     the same on either cut, like badge / epaulettes / armband) plus five
#     culture sets that combine them with recoloured base garments. The
#     read: every Authority uniform carries the downward guidance chevron
#     at the throat, squared chrome fittings, a peaked service cap.
# ======================================================================
def down_chevron(cx, cy, half, drop, th):
    """A downward-pointing > guidance chevron, apex below (toward the feet)."""
    return [[cx - half, cy], [cx, cy + drop], [cx + half, cy],
            [cx + half, cy - th], [cx, cy + drop - th], [cx - half, cy - th]]


def article(regions):
    return {"tier": "person", "palette": "authority_dress", "regions": regions}


def region(group, tag, note, color, shade, masc, femme, m_det=None, f_det=None):
    g = {"masc": {"points": masc, "fits": []}, "femme": {"points": femme, "fits": []}}
    if m_det is not None:
        g["masc"]["details"] = m_det
    if f_det is not None:
        g["femme"]["details"] = f_det
    return {"group": group, "tag": tag, "note": note, "color": color, "shade": shade, "geometry": g}


ARTICLES = {
    # the identity mark: a lit amber approach-chevron on a chrome tab, worn
    # high on the chest over any coat. Every Authority kit carries it.
    "authority_chevron_tab": {
        "identity": "Harbor Authority approach-chevron tab - a downward amber guidance chevron on a chrome ground, worn at the throat. The Authority's mark; every uniform carries it.",
        **article([
            region("torso", "badge", "chevron backing", "metal", "metal",
                   [[-1.9, -23.5], [1.9, -23.5], [1.9, -25.3], [-1.9, -25.3]],
                   [[-1.7, -23.4], [1.7, -23.4], [1.7, -25.1], [-1.7, -25.1]]),
            region("torso", "badge", "approach chevron", "lamp", "glow",
                   down_chevron(0.0, -24.4, 1.5, 1.0, 0.45),
                   down_chevron(0.0, -24.2, 1.35, 0.9, 0.4)),
        ])},
    # squared, rigid chrome shoulder boards (harder-edged than soft epaulettes)
    "authority_shoulder_boards": {
        "identity": "Harbor Authority shoulder boards - a pair of stiff squared chrome boards, one per shoulder. Rank is read off the chevron pips, not the board.",
        **article([
            region("arm_near", "epaulette", "near board", "metal", "metal",
                   [[1.85, -24.62], [4.62, -24.5], [4.62, -23.86], [1.9, -23.98]],
                   [[1.3, -24.45], [3.42, -24.36], [3.42, -23.78], [1.32, -23.86]]),
            region("arm_far", "epaulette", "far board", "metal", "metal",
                   [[-2.5, -24.5], [-4.5, -24.58], [-4.5, -23.98], [-2.55, -23.9]],
                   [[-1.72, -24.42], [-3.4, -24.5], [-3.4, -23.94], [-1.75, -23.88]]),
        ])},
    # a peaked navy service cap with a chevron cap-badge
    "authority_service_cap": {
        "identity": "Harbor Authority service cap - a stiff navy peaked cap, chrome band, a small amber chevron badge above the peak. Worn by control and command staff.",
        **article([
            region("torso", "hat", "cap crown", "cloth", "matte",
                   [[-2.508, -29.684], [2.016, -29.659], [1.983, -30.314], [1.834, -31.006],
                    [1.52, -31.615], [0.98, -32.054], [0.21, -32.314], [-0.766, -32.294],
                    [-1.379, -32.01], [-1.915, -31.602], [-2.289, -30.934], [-2.482, -30.317]],
                   [[-2.456, -29.862], [-1.326, -29.872], [0.471, -29.89], [2.149, -29.878],
                    [2.157, -30.449], [1.992, -31.384], [1.527, -32.156], [0.805, -32.569],
                    [-0.636, -32.598], [-1.543, -32.201], [-2.201, -31.498], [-2.435, -30.512]],
                   m_det=[
                       {"group": "torso", "color": "metal", "shade": "metal", "note": "cap band",
                        "points": [[-2.52, -29.6], [2.03, -29.58], [2.0, -30.05], [-2.5, -30.08]]},
                       {"group": "torso", "color": "metal", "shade": "deep", "note": "cap peak",
                        "points": [[-2.4, -29.6], [-4.7, -30.05], [-4.5, -29.35], [-2.3, -29.1]]},
                       {"group": "torso", "color": "lamp", "shade": "glow", "note": "cap chevron badge",
                        "points": down_chevron(-0.25, -30.95, 0.9, 0.5, 0.28)},
                   ],
                   f_det=[
                       {"group": "torso", "color": "metal", "shade": "metal", "note": "cap band",
                        "points": [[-2.47, -29.78], [2.17, -29.79], [2.14, -30.25], [-2.45, -30.26]]},
                       {"group": "torso", "color": "metal", "shade": "deep", "note": "cap peak",
                        "points": [[-2.4, -29.78], [-4.7, -30.2], [-4.5, -29.5], [-2.3, -29.3]]},
                       {"group": "torso", "color": "lamp", "shade": "glow", "note": "cap chevron badge",
                        "points": down_chevron(-0.1, -31.05, 0.85, 0.5, 0.26)},
                   ]),
        ])},
    # the Approach Warden's wide brassard - a tall band with its own chevron
    "authority_brassard": {
        "identity": "Approach Warden's brassard - a wide navy band on the near upper arm carrying a lit amber chevron. Worn by Authority security and wardens.",
        **article([
            region("arm_near", "armband", "brassard band", "cloth", "matte",
                   [[2.42, -24.3], [4.62, -24.18], [4.62, -21.5], [2.5, -21.62]],
                   [[1.6, -21.5], [3.42, -21.62], [3.3, -24.28], [1.62, -24.05]],
                   m_det=[{"group": "arm_near", "color": "lamp", "shade": "glow", "note": "brassard chevron",
                           "points": [[2.7, -23.3], [3.55, -22.6], [4.4, -23.3], [4.4, -22.85],
                                      [3.55, -22.15], [2.7, -22.85]]}],
                   f_det=[{"group": "arm_near", "color": "lamp", "shade": "glow", "note": "brassard chevron",
                           "points": [[1.85, -23.2], [2.55, -22.55], [3.25, -23.2], [3.25, -22.78],
                                      [2.55, -22.13], [1.85, -22.78]]}]),
        ])},
    # duty belt with a chevron buckle and a side pouch
    "authority_duty_belt": {
        "identity": "Harbor Authority duty belt - a dark webbing belt with a chevron buckle and a squared side pouch on the near hip.",
        **article([
            region("torso", "belt", "duty belt", "leather", "deep",
                   [[-2.615, -19.748], [2.55, -19.623], [2.469, -18.974], [-2.432, -19.116]],
                   [[-1.678, -20.447], [1.822, -20.351], [2.037, -19.623], [-1.892, -19.714]],
                   m_det=[
                       {"group": "torso", "color": "lamp", "shade": "glow", "note": "chevron buckle",
                        "points": down_chevron(-0.2, -19.45, 0.62, 0.4, 0.22)},
                       {"group": "torso", "color": "leather", "shade": "deep", "note": "belt pouch",
                        "points": [[1.55, -19.85], [2.6, -19.7], [2.7, -18.5], [1.65, -18.6]]},
                   ],
                   f_det=[
                       {"group": "torso", "color": "lamp", "shade": "glow", "note": "chevron buckle",
                        "points": down_chevron(-0.1, -20.1, 0.58, 0.4, 0.2)},
                       {"group": "torso", "color": "leather", "shade": "deep", "note": "belt pouch",
                        "points": [[1.2, -20.5], [2.1, -20.35], [2.2, -19.3], [1.3, -19.4]]},
                   ]),
        ])},
}
for aid, design in ARTICLES.items():
    w(f"{G}/articles/{aid}.json", design)

# Five culture sets. Base garments are recoloured by the set palette
# (authority_dress); the five bespoke articles above give the silhouette.
SETS = {
    "authority_command": {
        "identity": "Harbor Authority command turn-out - navy tunic-coat and trousers, black boots, a white stand collar, chrome shoulder boards, a peaked service cap, and the approach-chevron tab.",
        "palette": "authority_dress",
        "articles": ["tank_top", "coat_command", "pants_navy", "boots_black", "stand_collar_white",
                     "authority_shoulder_boards", "authority_service_cap", "authority_chevron_tab", "hair_short"]},
    "authority_security": {
        "identity": "Approach Warden kit - blue-grey security uniform, stab vest, duty belt, a sealed helmet, the warden's brassard, and the approach-chevron tab.",
        "palette": "authority_dress",
        "articles": ["tank_top", "jacket_secblue", "pants_secblue", "boots_black", "helmet_sec",
                     "vest", "authority_duty_belt", "authority_brassard", "authority_chevron_tab"]},
    "authority_dock": {
        "identity": "Authority dock crew - navy work suit, amber hard hat and hi-vis tabard, heavy gloves, and the approach-chevron tab.",
        "palette": "authority_dress",
        "articles": ["tank_top", "jacket_dock", "pants_dock", "boots_charcoal", "cap_amber",
                     "hi_vis_tabard_amber", "gloves_dark", "authority_chevron_tab", "hair_short"]},
    "authority_flight": {
        "identity": "Authority flight rig - navy flight jacket and trousers, a flight helmet, chrome shoulder boards, and the approach-chevron tab.",
        "palette": "authority_dress",
        "articles": ["tank_top", "jacket_navy", "pants_navy", "boots_black", "helmet_flight",
                     "authority_shoulder_boards", "authority_chevron_tab", "hair_short"]},
    "authority_civilian": {
        "identity": "Authority civilian dress - plain navy clothes and a soft collar, worn with the approach-chevron tab as a lapel pin. Even the Authority's civilians wear the mark.",
        "palette": "authority_dress",
        "articles": ["tank_top", "jacket_civ", "pants", "shoes", "collar",
                     "authority_chevron_tab", "hair_long"]},
}
for sid, design in SETS.items():
    w(f"{G}/sets/{sid}.json", design)

# Repoint the ten authority_* outfit entries at the bespoke sets (the body
# still picks the masc/femme geometry cut everywhere downstream).
OUTFIT_SET = {"civilian": "authority_civilian", "official": "authority_command",
              "flight": "authority_flight", "security": "authority_security", "dock": "authority_dock"}
for role, sid in OUTFIT_SET.items():
    for cut in ("femme", "masc"):
        gfx["outfits"][f"authority_{role}_{cut}"] = {
            "body": f"human_{cut}", "set": sid, "palette": "authority_dress"}

w(f"{S}/graphics.json", gfx)

# ======================================================================
# 5. HUB CONTROL floor plan + full NPC roster
# ======================================================================
DECO_GRID_NOTE = "harbor_authority culture -> deck_grid decoration auto-stamps the painted floor grid."


def rect(x0, y0, x1, y1, label):
    return {"label": label, "polygon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


# Hub Control's exterior (graphics/stations/authority_station.json) is a
# rectilinear cross: a squared central control block, four straight docking
# arms, a signal mast. The floor plan is that plus - a central Control
# Rotunda with the mast at its heart and four ranked arms radiating N/S/E/W,
# each arm overlapping the core by ~60 u so the walkable union is one space.
# Symmetrical and over-ranked, per the Harbor Authority theme.
HUB_ROOMS = [
    rect(620, 520, 980, 880, "Control Rotunda"),   # central control block
    rect(670, 210, 930, 580, "Control Gallery"),    # N arm  (stationmaster)
    rect(670, 820, 930, 1190, "Lender's Office"),   # S arm  (loan)
    rect(180, 570, 680, 830, "Records Hall"),       # W arm  (bar + records)
    rect(920, 570, 1420, 830, "The Berth"),         # E arm  (ship dealer + outfitter + dock, ship portal)
]

HUB_STRUCTURES = [
    {"x": 800, "y": 700, "building_type": "authority_spire"},   # the signal mast, dead centre
    # ranked colonnades down the N and S approach arms (footprints hug the walls)
    *[{"x": x, "y": y, "building_type": "pipeline_column"}
      for x in (700, 900) for y in (270, 370, 470)],
    *[{"x": x, "y": y, "building_type": "pipeline_column"}
      for x in (700, 900) for y in (930, 1030, 1130)],
    {"x": 700, "y": 760, "building_type": "pipeline_bench"},     # rotunda
    {"x": 900, "y": 760, "building_type": "pipeline_bench"},
    {"x": 420, "y": 800, "building_type": "pipeline_bench"},     # Records Hall
    {"x": 1180, "y": 800, "building_type": "pipeline_bench"},    # The Berth
    {"x": 220, "y": 600, "building_type": "crates"},             # Records Hall corner
    {"x": 860, "y": 1160, "building_type": "crates"},            # Lender's Office corner
]

HUB_NPCS = [
    {"name": "Induction Officer Sella", "x": 880, "y": 800, "role": "concierge",
     "faction": "harbor_authority", "outfit": "authority_official_femme",
     "escort_flag": "induction_escorting",
     "ambient": {"range": 700, "message": "New pilot on the ring? I run inductions - walk over (WASD / arrows) and press T when you reach me."},
     "dialogue_tree": {"root": "start", "conditional_roots": [
         {"flag": "induction_done", "node": "done"}, {"flag": "induction_accepted", "node": "midway"}],
      "nodes": {
        "start": {"text": "Harbor Authority induction. First time flying our beacons? I'll walk you through the ring, get you a loan and a hull, and see you off toward Kiln - the next dark lane. Every step tracks in your Mission Log (N).",
                  "options": [
                      {"label": "Walk me through it.", "next": "accepted",
                       "actions": ["set_flag:induction_accepted", "start_mission:induction"]},
                      {"label": "I'll manage on my own.", "next": None}]},
        "accepted": {"text": "Good. Close the comm and lead off down the approach arm - I'm right behind you.",
                     "options": [{"label": "Lead on", "next": None}]},
        "midway": {"text": "Still on the induction - check your Mission Log (N) for the current step. Or strike out alone, your call.",
                   "options": [{"label": "Keep going", "next": None},
                               {"label": "I'll manage from here", "next": "declined", "action": "abandon_mission:induction"}]},
        "declined": {"text": "Understood. The Berth's the east arm - where you docked - for a hull. The Lender's Office is the south arm for the credits. Kiln's beacon lights when you're ready to leave - come back and tell me. Safe flying.",
                     "options": [{"label": "Thanks", "next": None}]},
        "done": {"text": "Back on the ring? The Authority remembers a clean induction. Safe flying, pilot.",
                 "options": [{"label": "Just passing through", "next": None}]}}}},

    {"name": "Controller Vane", "x": 800, "y": 340, "role": "stationmaster",
     "faction": "harbor_authority", "outfit": "authority_official_femme",
     "dialogue_tree": {"root": "start", "conditional_roots": [
         {"faction": "harbor_authority", "min": 25, "node": "warm"}],
      "nodes": {
        "start": {"text": "I run Hub Control. Beacon 1 is live again - the whole region's about to have company it didn't plan for. Fly our beacons, log what you find, and the Authority holds the network for all of us.",
                  "options": [
                      {"label": "Key the beacon to Kiln - I'm heading out.", "next": "keyed",
                       "requires_not_flag": "beacon_kiln_lit",
                       "actions": ["light_beacon:kiln", "adjust_rep:harbor_authority:4"]},
                      {"label": "Why does the Authority get to hold it?", "next": "why"},
                      {"label": "Understood", "next": None}]},
        "keyed": {"text": "Done - Kiln's lane is open. Log what you find and come back to Hub Control. Safe flying.",
                  "options": [{"label": "Understood", "next": None}]},
        "why": {"text": "Because someone has to schedule a crossing, and we're the only ones who kept the records to do it. Ask the Vigil what happens when nobody does.",
                "options": [{"label": "Noted", "next": None}]},
        "warm": {"text": "Good to see one of ours on the approach. When the Span asks its question, the Authority would be glad of your voice.",
                 "options": [
                     {"label": "Pledge the Authority your beacons.", "next": "pledged",
                      "requires_not_flag": "patron:harbor_authority",
                      "actions": ["set_exclusive_flag:patron:harbor_authority", "adjust_rep:harbor_authority:8"]},
                     {"label": "I'll think on it", "next": None}]},
        "pledged": {"text": "Logged, and remembered. You answer for the Authority at the Span.",
                    "options": [{"label": "Understood", "next": None}]}}}},

    {"name": "Signal Officer Doss", "x": 800, "y": 1040, "role": "loan_officer",
     "faction": "harbor_authority", "outfit": "authority_official_masc",
     "dialogue_tree": {"root": "start", "nodes": {
        "start": {"text": "Authority underwrites a starter loan for any pilot flying our beacons - 12,000 credits, enough for a hull and a little fitting-out. Interest is the reports you file.",
                  "options": [
                      {"label": "Take the loan - 12,000cr", "next": "loaned", "action": "take_loan"},
                      {"label": "Not yet", "next": None}]},
        "loaned": {"text": "Approved. The beacons are our ledger now - don't make us come find you.",
                   "options": [{"label": "Thanks", "next": None}]}}}},

    {"name": "Harbor-Master Crane", "x": 1120, "y": 660, "role": "ship_salesman",
     "faction": "harbor_authority", "outfit": "authority_official_femme",
     "greeting": "The Berth. Independent hulls, mostly - carriers who couldn't pay their approach fees, cleared for sale. Take your pick.",
     "shop": {"type": "ships", "stock": ["carrier_courier", "authority_courier", "authority_hauler", "carrier_hauler", "authority_patrol"]}},

    {"name": "Approach Warden Lund", "x": 1300, "y": 660, "role": "outfitter",
     "faction": "harbor_authority", "outfit": "authority_security_masc",
     "greeting": "Fitting out? Standard-issue only, but every piece is rated and logged.",
     "shop": {"type": "outfits", "stock": ["laser_cannon", "pulse_blaster", "afterburner", "cargo_expansion", "reinforced_hull", "shield_capacitor", "sensor_array"]}},

    {"name": "Quartermaster Ellin", "x": 1120, "y": 780, "role": "quartermaster",
     "faction": "harbor_authority", "outfit": "authority_dock_femme",
     "greeting": "Bring me goods off the outer beacons and I'll pay Hub rates. Relief supplies and salvage move fastest right now.",
     "shop": {"type": "commodities", "stock": ["relief_supplies", "salvage"], "sell_multiplier": 1.2}},

    {"name": "Deck-hand Rusk", "x": 1240, "y": 780, "role": "dockworker",
     "faction": "harbor_authority", "outfit": "authority_dock_masc",
     "greeting": "Busiest I've seen the Berth in my life. Everyone wants out before the lanes fill up.",
     "dialogue_options": ["Understood", "Leave"]},

    {"name": "Barkeep Ottre", "x": 320, "y": 690, "role": "bartender",
     "faction": "harbor_authority", "outfit": "authority_civilian_masc",
     "dialogue_tree": {"root": "start", "conditional_roots": [{"flag": "hub_bar_regular", "node": "regular"}], "nodes": {
        "start": {"text": "Records Hall bar. What'll it be?",
                  "options": [
                      {"label": "Order a drink", "next": "drink"},
                      {"label": "Buy the room a round - 25cr", "next": "round", "requires_not_flag": "hub_bar_regular",
                       "actions": ["spend_credits:25", "set_flag:hub_bar_regular"]},
                      {"label": "Ask what people are saying", "next": "gossip"},
                      {"label": "Leave", "next": None}]},
        "regular": {"text": "Back again - good. First one's poured.",
                    "options": [{"label": "Ask what people are saying", "next": "gossip"}, {"label": "Leave", "next": None}]},
        "drink": {"text": "Synth-ale, on the house for a new face. Cheers.", "options": [{"label": "Thanks", "next": "start"}]},
        "round": {"text": "Generous. That buys you the honest version of the news - ask away.", "options": [{"label": "Ask", "next": "gossip"}]},
        "gossip": {"text": "Combine's furious - says the beacon voids two centuries of contracts. The Vigil out at Ossuary say we shouldn't be lighting anything at all. And every carrier on the ring is drinking like the good years are over.",
                   "options": [{"label": "Noted", "next": None}]}}}},

    {"name": "Records Keeper Amsel", "x": 480, "y": 650, "role": "clerk",
     "faction": "harbor_authority", "outfit": "authority_official_masc",
     "dialogue_tree": {"root": "start", "nodes": {
        "start": {"text": "I keep the approach records - two hundred years of them, unbroken. It's why the Authority can run the lanes and no one else can.",
                  "options": [
                      {"label": "What do the oldest records say?", "next": "old"},
                      {"label": "Just looking", "next": None}]},
        "old": {"text": "The last clean entries before the Silence. Then a single line, every station, same hour: BEACON NET DOWN - HOLD ALL TRAFFIC. No cause logged. The Vigil think they know why. I only know we obeyed it for two centuries.",
                "options": [{"label": "Unsettling", "next": None}]}}}},

    {"name": "Displaced traveller", "x": 560, "y": 760, "role": "traveler",
     "faction": "free_carrier", "outfit": "carrier_civilian_femme",
     "requires_flag": "beacon_verdance_lit",
     "greeting": "Came in on the new lane from Verdance. Half the ring's doing the same. Nobody planned for this.",
     "dialogue_options": ["Safe travels", "Leave"]},

    {"name": "Deck Mechanic Prit", "x": 880, "y": 640, "role": "traveler",
     "faction": "harbor_authority", "outfit": "authority_dock_femme",
     "greeting": "If your hull rattles on the way out, that's me you come back to. I'll be here. Everyone comes back.",
     "dialogue_options": ["Good to know", "Leave"]},
]

HUB_INTERIOR = {
    "label": "Hub Control", "culture": "harbor_authority",
    "portals": [{"x": 1360, "y": 700, "connected_locations": [], "return_to_ship": True}],
    "rooms": HUB_ROOMS,
    "structures": HUB_STRUCTURES,
    "npcs": HUB_NPCS,
    # one open lit deck on the Space View starfield, ranked Authority floor
    # panels (see LocationScreen: seamless / space_backdrop / floor_pattern).
    "seamless": True,
    "space_backdrop": True,
    "star_seed": 101,
    "floor_pattern": {"pattern": "square", "tile": 64, "gap": 2.0},
}


def moon_city():
    return {
        "name": "Halcyon Watch", "x": 0.82, "y": 0.78, "size": 30, "color": [121, 137, 160],
        "crater_color": [91, 107, 130], "landing_distance": 35,
        "craters": [{"x": -8, "y": -4, "radius": 4}, {"x": 9, "y": 7, "radius": 5}, {"x": 3, "y": -9, "radius": 3}],
        "interiors": {"city": {
            "label": "Watch Station", "culture": "harbor_authority",
            "connected_locations": [], "entrance": {"x": 800, "y": 820},
            "rooms": [rect(160, 200, 1440, 1160, "Watch Yard")],
            "structures": [
                {"x": 800, "y": 520, "building_type": "authority_hall"},
                {"x": 420, "y": 760, "building_type": "authority_housing"},
                {"x": 1180, "y": 760, "building_type": "authority_housing"},
                {"x": 800, "y": 320, "building_type": "authority_spire"},
                {"x": 560, "y": 980, "building_type": "pipeline_bench"},
                {"x": 1040, "y": 980, "building_type": "pipeline_bench"},
                {"x": 300, "y": 1040, "building_type": "crates"},
                {"x": 1300, "y": 1040, "building_type": "crates"},
                *[{"x": x, "y": 620, "building_type": "pipeline_column"} for x in (520, 1080)],
            ],
            "npcs": [
                {"name": "Watch Officer Kesh", "x": 800, "y": 700, "role": "magistrate",
                 "faction": "harbor_authority", "outfit": "authority_official_masc",
                 "greeting": "Halcyon Watch. We track every hull in the system from here. Keep your approach clean and we'll never speak again.",
                 "dialogue_options": ["Understood", "Leave"]},
                {"name": "Relay Tech Bome", "x": 560, "y": 620, "role": "surface_tech",
                 "faction": "harbor_authority", "outfit": "authority_dock_femme",
                 "greeting": "Beacon 1's carrier signal came back clean after 200 years dark. Not a bit-error in it. That should be impossible. Nobody up here likes talking about it.",
                 "dialogue_options": ["Strange", "Leave"]},
                {"name": "Off-shift Rating", "x": 1080, "y": 900, "role": "resident",
                 "faction": "harbor_authority", "outfit": "authority_civilian_femme",
                 "greeting": "Quiet posting, the Watch. Was. Ask me again in a month.",
                 "dialogue_options": ["Ha", "Leave"]},
            ],
        }},
    }


HALCYON = {
    "name": "Halcyon",
    "description": "A cluster of well-kept orbital stations around a yellow star, run by the Harbor Authority - the descendants of the Relay's traffic controllers. The first beacon to relight.",
    "star_map_position": {"x": 0, "y": 0},
    "station_asset": "authority_station",
    "moon_asset": "authority_moon",
    "central_star": {"x": 0.5, "y": 0.5, "name": "Halcyon", "size": 100, "color": [255, 240, 150]},
    "player_start": {"x": 0.4, "y": 0.35},
    "star_seed": 101,
    "asteroid_field": {"per_chunk_range": [1, 3], "types": [
        {"type": "gray_rock", "weight": 3, "size_range": [4, 18], "speed_range": [0.05, 0.3], "mine_yield": 10},
        {"type": "brown_rock", "weight": 1, "size_range": [6, 25], "speed_range": [0.05, 0.25], "mine_yield": 15}]},
    "station": {"x": 0.15, "y": 0.2, "name": "Hub Control", "interiors": {"default": HUB_INTERIOR}},
    "moon": moon_city(),
    "celestial_bodies": [
        {"name": "Sentinel", "x": 0.6, "y": 0.55, "size": 16, "color": [180, 160, 140], "body_type": "rocky"},
        {"name": "Verge", "x": 0.08, "y": 0.9, "size": 46, "color": [225, 200, 150], "body_type": "gas_giant", "has_ring": True, "ring_color": [200, 190, 160]}],
    "ai_ships": [
        {"name": "Hub Patrol Kestrel", "x": 0.5, "y": 0.12, "ship_type": "authority_patrol", "pilot": "ackley",
         "faction": "harbor_authority", "route": ["station", "moon"]},
        {"name": "Approach Cutter Tern", "x": 0.22, "y": 0.28, "ship_type": "authority_courier", "pilot": "pell",
         "faction": "harbor_authority", "route": ["station", "moon"]},
        {"name": "Authority Freight 9", "x": 0.65, "y": 0.6, "ship_type": "authority_hauler", "pilot": "lund",
         "faction": "harbor_authority", "route": ["station", "moon"]},
        {"name": "Relief Hauler Vesper", "x": 0.7, "y": 0.35, "ship_type": "authority_hauler", "pilot": "voss",
         "faction": "harbor_authority", "route": ["moon", "station"]},
        {"name": "Ferro's Slip", "x": 0.3, "y": 0.55, "ship_type": "carrier_hauler", "pilot": "rell",
         "faction": "free_carrier", "route": ["station", "moon"]},
    ],
}
w(f"{S}/systems/halcyon.json", HALCYON)

# ======================================================================
# 6b. HALCYON PILOTS  (flesh out the three scaffold pilots + add two;
#     other systems keep the Phase 3/4 scaffold roster until their slice)
# ======================================================================
pilots = r(f"{S}/pilots.json")
pilots.update({
    "ackley": {
        "name": "Controller Ackley", "faction": "harbor_authority", "role": "patrol_officer",
        "personality": "Correct, unhurried, certain the regulations exist for a reason - and that you have not read them.",
        "hail_greeting": "Hub Control patrol, Kestrel. Your approach is logged and clean. Keep it that way and we've no business with each other."},
    "pell": {
        "name": "Approach Officer Pell", "faction": "harbor_authority", "role": "patrol_officer",
        "personality": "New to the cutter and keen to be seen doing it right; recites the beacon protocol at you unprompted.",
        "hail_greeting": "Cutter Tern on the inner approach. First time through Halcyon? Hold your heading for the beacon and let the guidance chevrons walk you in."},
    "lund": {
        "name": "Freight-Warden Lund", "faction": "harbor_authority", "role": "freighter_pilot",
        "personality": "Talks like a manifest - flat, exact, faintly relieved when a run closes out clean.",
        "hail_greeting": "Authority freight, station to moon, manifest sealed. Nothing on my ticket concerns you."},
    "voss": {
        "name": "Hauler Voss", "faction": "harbor_authority", "role": "freighter_pilot",
        "personality": "Twenty years on the milk run; now hauling relief crates for carriers stranded by the beacon and quietly furious about the waste.",
        "hail_greeting": "Relief hauler Vesper, moon to Hub. Half this load is for people who had homes last month. Give me room."},
    "rell": {
        "name": "Rell", "faction": "free_carrier", "role": "freighter_pilot",
        "personality": "Twenty years on the slow lanes; the beacon just made her route worthless and she is trying to laugh about it.",
        "hail_greeting": "Independent carrier, Ferro's Slip. I was running this lane before your beacon woke up, friend. Now I'm just in the way."},
})
w(f"{S}/pilots.json", pilots)

# ======================================================================
# 6. ANCHOR MISSION  "induction"  (replaces the borrowed missions.json)
# ======================================================================
def say(sender, text):
    return {"sender": sender, "text": text}


IND = "Induction Officer Sella"
INDUCTION = {
    "title": "Harbor Authority Induction",
    "escort_flag": "induction_escorting",
    # accepting the induction keys Kiln's beacon (the mission sends you
    # there). A player who skips the induction lights it via Controller
    # Vane's fallback option instead.
    "on_start_flags": ["induction_escorting", "beacon_kiln_lit"],
    "on_end_flags": ["induction_done"],
    "stages": [
        {"text": "Walk a lap of the Approach Concourse - WASD or the arrow keys.",
         "complete_flag": "walked_interior", "reset_on_activation": True,
         "one_way_message": say(IND, "You're on the induction - it tracks in your Mission Log (N). Feet first: walk the length of an approach arm on WASD or the arrow keys.")},
        {"text": "Target someone - press [ or ] to cycle a lock, or click them.",
         "complete_flag": "targeted_person", "reset_on_activation": True,
         "one_way_message": say(IND, "See everyone on the ring? Tap [ or ] to cycle a target lock, or just click a person. Their name and role show top-right.")},
        {"text": "Walk up to someone and talk - press T.",
         "complete_flag": "talked_to_npc", "reset_on_activation": True,
         "one_way_message": say(IND, "Get in close to anyone and press T. Shopkeepers open their store; everyone else has something to say.")},
        {"text": "Open your Mission Log - press N.",
         "complete_flag": "viewed_mission_log", "reset_on_activation": True,
         "one_way_message": say(IND, "Press N for your Mission Log. Every step I give you is listed there.")},
        {"text": "Open your Possessions - press P (check the Standing panel).",
         "complete_flag": "viewed_possessions", "reset_on_activation": True,
         "one_way_message": say(IND, "Press P for Possessions - credits, ships, cargo, and your Standing with each faction.")},
        {"text": "Take the Authority starter loan - Signal Officer Doss, Lender's Office (south arm).",
         "complete_flag": "took_loan",
         "one_way_message": say(IND, "The south arm - the Lender's Office. Talk to Signal Officer Doss and take the starter loan - you'll need it for a hull.")},
        {"text": "Buy a ship - Harbor-Master Crane, the Berth (east arm).",
         "complete_flag": "bought_ship",
         "one_way_message": say(IND, "The Berth is the east arm - the one you docked in. Harbor-Master Crane has hulls for sale there; the courier's an easy first ship. Buy whichever you like.")},
        {"text": "Board your ship - step on the Berth portal and press L.",
         "complete_flag": "bought_ship",
         "one_way_message": say(IND, "That's the ring done. Your ship's docked at the Berth - step on the portal and press L to board. I'll raise you once you're in the cockpit.")},
        {"text": "Turn both ways - left (A / Left), then right (D / Right).",
         "complete_flag": "turned_both_ways", "reset_on_activation": True, "reset_flags": ["turned_left", "turned_right"],
         "one_way_message": say(IND, "Hub Control, reading you in the cockpit. Start simple - turn left with A, then right with D. Give me both.")},
        {"text": "Thrust forward - W or Up. Watch your speed build.",
         "complete_flag": "used_thrust", "reset_on_activation": True,
         "one_way_message": say(IND, "Good. Hold W to thrust. Space doesn't slow you down on its own - remember that.")},
        {"text": "Turn around and brake until your speed drops - S, then thrust.",
         "complete_flag": "braked_below_threshold", "reset_on_activation": True, "reset_flags": ["used_brake"],
         "one_way_message": say(IND, "Now cancel it - hold S to point retrograde, then thrust to kill your speed.")},
        {"text": "Fly clear of the system centre, then jump to Kiln (M to pick it, J to jump).",
         "complete_flag": "jumped_to:kiln",
         "one_way_message": say(IND, "Last thing. Kiln's beacon is keyed - fly well clear of the star until the drift prompt shows, open the Star Map (M), select Kiln, and press J. Log what you find there, pilot. Halcyon out.")},
    ],
}
# Merge, don't overwrite - the other slices (gen_kiln / gen_verdance /
# gen_ossuary) each add their own anchor mission to this same file, and the
# gen chain no longer runs from a clean slate every time. "induction" stays
# first so it reads as the entry point.
try:
    missions = r(f"{S}/missions.json")
except FileNotFoundError:
    missions = {}
missions = {"induction": INDUCTION, **{k: v for k, v in missions.items() if k != "induction"}}
w(f"{S}/missions.json", missions)

# ======================================================================
# 7. story.json wiring
# ======================================================================
story = r(f"{S}/story.json")
# 0.11.0 cut the starter loan to 12k; 0.12.0 adds the shield_capacitor /
# sensor_array outfits + gives reinforced_hull a real +max_health (all from
# the ships-core module) and the Outfitter a sell-back tab.
story["version"] = "0.12.0"
# Starter-loan terms (see LocationScreen._loan_terms). 12k covers the
# carrier courier (7k) plus a weapon and a spare - deliberately not enough
# to be careless with (was the engine default of 100k, which trivialised
# the opening economy - see docs/BACKLOG.md).
story["loan"] = {"lender": "Harbor Authority", "amount": 12000, "max_active": 1}
# NOT starting_mission - that always defers to the first launch when the
# player starts docked (see docs/ARCHITECTURE.md), which would skip every
# station stage. The induction is started by Induction Officer Sella's
# dialogue instead (start_mission:induction), same as the default story's
# station_tour. Her ambient line prompts a new pilot to walk over.
story.pop("starting_mission", None)
story.pop("starting_mission_trigger", None)
story["start"]["flags"] = {}   # Kiln's beacon is lit by the induction's on_start_flags / Vane's fallback
story["description"] = ("The Relay went dark 200 years ago and is switching itself back on, system by system. "
                        "Fly ahead of the signal, re-contact cultures that grew strange in isolation, and decide what "
                        "reconnection means. Act I plays end to end - all five systems have authored culture art, "
                        "walkable stations, NPC rosters, and anchor missions; Acts II-III are in progress.")
w(f"{S}/story.json", story)

print(f"Halcyon slice written: 3 ships, 1 station, 3 buildings, dress palette, "
      f"{len(ARTICLES)} bespoke articles + {len(SETS)} culture sets, Hub Control ("
      f"{len(HUB_ROOMS)} rooms / {len(HUB_NPCS)} NPCs), induction mission "
      f"({len(INDUCTION['stages'])} stages), {len(pilots)} pilots. story 0.10.0.")
