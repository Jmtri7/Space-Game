"""Phase 6.3 - the Verdance slice (the Drift), end to end.

Owns systems/verdance.json. Run after gen_kiln (see docs/gen/README.md).
Produces the Drift's rounded, planted ships/station/buildings, a bespoke
soft-goods wardrobe, the Highcanopy floor plan + roster, and the anchor
mission "the_drift_assembly" (the assembly can't decide; forcing the vote
lights Ossuary's beacon and opens Act II).

Drift style (cultures.json): soft, rounded, planted - curved partitions,
trellised grow-light, growing things worked into the structure, pale
timber-and-canvas over a green cast. Nothing load-bearing that could be woven.
"""
import math
from _slice_kit import (S, G, w, r, rect, concourse_plan, BAY_N, BAY_S, say, station_shell,
                        article, region, write_wardrobe, sash_region,
                        apron_region, brassard_region)

PFX = "drift"
DRESS = "drift_dress"


def blob(cx, cy, rx, ry, n=14, y0=0.0):
    """A rounded n-gon centred (cx,cy) - the Drift never draws a hard corner."""
    return [[round(cx + rx * math.sin(2 * math.pi * i / n), 3),
             round(cy - ry * math.cos(2 * math.pi * i / n), 3)] for i in range(n)]


# ======================================================================
# 1. SHIPS  - rounded leaf / pod hulls
# ======================================================================
DRIFT_COURIER = {
    "identity": "Drift Skiff - a rounded seed-pod hull, a bulbous forward canopy blister, a single soft dorsal fin, two short strut pods aft trailing a green grow-light. No hard edge anywhere. Reads at a dozen pixels as a smooth teardrop with two pale-green dots.",
    "tier": "ship_near", "palette": PFX, "size": 11,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "soft", "flatten_px": 40, "note": "seed-pod hull",
         "points": blob(0.0, 0.0, 0.42, 1.02, 16)},
        {"group": "canopy", "color": "glass", "shade": "sheen", "flatten_px": 55, "note": "canopy blister",
         "points": blob(0.0, -0.45, 0.18, 0.32, 12)},
        {"group": "pod_r", "color": "engine", "shade": "soft", "flatten_px": 45, "note": "right strut pod",
         "points": blob(0.42, 0.78, 0.14, 0.26, 10)},
        {"group": "pod_l", "color": "engine", "shade": "soft", "flatten_px": 45, "note": "left strut pod",
         "points": blob(-0.42, 0.78, 0.14, 0.26, 10)},
        {"group": "fin", "color": "metal", "shade": "soft", "flatten_px": 40, "note": "soft dorsal fin",
         "points": [[-0.05, 0.1], [0.05, 0.1], [0.04, 0.9], [-0.04, 0.9]]},
    ],
    "details": [
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 60,
         "note": "trellis grow-strip", "points": [[-0.06, -0.4], [0.06, -0.4], [0.06, 0.7], [-0.06, 0.7]]},
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 90,
         "note": "nav light, nose", "circle": [0.0, -0.96, 0.05]},
        {"group": "pod_r", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "right thruster", "circle": [0.42, 1.0, 0.11]},
        {"group": "pod_l", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "left thruster", "circle": [-0.42, 1.0, 0.11]},
    ],
}

DRIFT_HAULER = {
    "identity": "Drift Barge - a fat bulbous freighter: a rounded body swelling to three cargo blisters down each flank, a soft domed cab forward, a broad low engine ring aft. Grow-light runs the seams. Slow, roomy, kind to fly. Reads as a bunch of round pods with a green glow.",
    "tier": "ship_near", "palette": PFX, "size": 20,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "soft", "flatten_px": 60, "note": "bulbous body",
         "points": blob(0.0, 0.0, 0.46, 1.04, 18)},
        {"group": "cab", "color": "glass", "shade": "sheen", "flatten_px": 55, "note": "domed cab",
         "points": blob(0.0, -0.6, 0.22, 0.3, 12)},
        *[{"group": f"blister_{s}{i}", "color": "engine", "shade": "soft", "flatten_px": 45,
           "note": f"{'right' if s == 'r' else 'left'} cargo blister {i}",
           "points": blob(sx * 0.44, y, 0.16, 0.2, 10)}
          for s, sx in (("r", 1), ("l", -1)) for i, y in enumerate((-0.3, 0.1, 0.5))],
        {"group": "engine", "color": "engine", "shade": "soft", "flatten_px": 50, "note": "engine ring",
         "points": blob(0.0, 1.0, 0.4, 0.2, 14)},
    ],
    "details": [
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 50,
         "note": "seam grow-light", "points": [[-0.04, -0.5], [0.04, -0.5], [0.04, 0.7], [-0.04, 0.7]]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 14, "note": "right thruster", "circle": [0.2, 1.08, 0.13]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 14, "note": "left thruster", "circle": [-0.2, 1.08, 0.13]},
    ],
}

DRIFT_PATROL = {
    "identity": "Drift Watchboat - the Drift barely builds warships; this is a courier hull grown a little larger, with one soft spinal light-lance and a rounded sensor bulb on top. Reads as a bigger teardrop with a single bright spine - a deterrent, not a threat.",
    "tier": "ship_near", "palette": PFX, "size": 15,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "soft", "flatten_px": 45, "note": "grown hull",
         "points": blob(0.0, 0.0, 0.5, 1.06, 18)},
        {"group": "canopy", "color": "glass", "shade": "sheen", "flatten_px": 50, "note": "canopy",
         "points": blob(0.0, -0.4, 0.2, 0.34, 12)},
        {"group": "sensor", "color": "metal", "shade": "soft", "flatten_px": 40, "note": "sensor bulb",
         "points": blob(0.0, 0.3, 0.12, 0.16, 10)},
        {"group": "pod_r", "color": "engine", "shade": "soft", "flatten_px": 45, "note": "right pod", "points": blob(0.5, 0.8, 0.14, 0.26, 10)},
        {"group": "pod_l", "color": "engine", "shade": "soft", "flatten_px": 45, "note": "left pod", "points": blob(-0.5, 0.8, 0.14, 0.26, 10)},
    ],
    "details": [
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 40,
         "note": "spinal light-lance", "points": [[-0.05, -0.9], [0.05, -0.9], [0.05, 0.5], [-0.05, 0.5]]},
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 20, "note": "lance emitter", "circle": [0.0, -0.98, 0.06]},
        {"group": "pod_r", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "right thruster", "circle": [0.5, 1.02, 0.11]},
        {"group": "pod_l", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "left thruster", "circle": [-0.5, 1.02, 0.11]},
    ],
}

SHIP_DESIGNS = {
    "drift_courier": (DRIFT_COURIER, [[0.42, 1.0], [-0.42, 1.0]],
                      [[0.0, -1.02], [0.42, 0.6], [0.42, 1.0], [-0.42, 1.0], [-0.42, 0.6]]),
    "drift_hauler": (DRIFT_HAULER, [[0.2, 1.08], [-0.2, 1.08]],
                     [[0.0, -1.04], [0.46, 0.5], [0.4, 1.1], [-0.4, 1.1], [-0.46, 0.5]]),
    "drift_patrol": (DRIFT_PATROL, [[0.5, 1.02], [-0.5, 1.02]],
                     [[0.0, -1.06], [0.5, 0.6], [0.5, 1.02], [-0.5, 1.02], [-0.5, 0.6]]),
}
for sid, (design, thr, local) in SHIP_DESIGNS.items():
    w(f"{G}/ships/{sid}.json", design)

gfx = r(f"{S}/graphics.json")
for sid, (design, thr, local) in SHIP_DESIGNS.items():
    e = gfx["ships"][sid]
    e["local_points"] = local
    e["thrusters"] = thr
    e["thruster_width"] = 0.06
    e["thruster_length"] = 16

# ======================================================================
# 2. STATION  "Highcanopy" - a soft ring hung with pod-leaves
# ======================================================================
DRIFT_STATION = {
    "identity": "Highcanopy - the Drift's cloud-city dock: a soft rounded ring, its inner edge glowing green, hung with six teardrop habitat-pods like leaves off a branch, a bright grow-core at the hub on three woven spokes. No hard edge. Reads as a green-lit wreath.",
    "tier": "station", "palette": PFX, "size": 46,
    "units": "fractions of `size`; radially symmetric.",
    "silhouette": [
        {"group": "ring", "color": "hull", "shade": "soft", "flatten_px": 70, "note": "outer ring",
         "points": blob(0.0, 0.0, 1.0, 1.0, 28)},
        {"group": "well", "color": "engine", "shade": "flat", "flatten_px": 200, "note": "green inner well",
         "points": blob(0.0, 0.0, 0.6, 0.6, 24)},
        {"group": "hub", "color": "hull", "shade": "soft", "flatten_px": 45, "note": "grow-core hub",
         "points": blob(0.0, 0.0, 0.22, 0.22, 14)},
        *[{"group": f"pod{i}", "color": "hull_dk", "shade": "soft", "flatten_px": 55, "note": f"habitat pod {i}",
           "points": blob(1.06 * math.sin(a), -1.06 * math.cos(a), 0.2, 0.28, 10)}
          for i, a in enumerate(2 * math.pi * j / 6 for j in range(6))],
    ],
    "details": [
        {"group": "hub", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 18, "note": "grow-core glow", "circle": [0.0, 0.0, 0.24]},
        *[{"group": f"pod{i}", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 24, "note": f"pod light {i}",
           "circle": [1.06 * math.sin(a), -1.06 * math.cos(a), 0.05]}
          for i, a in enumerate(2 * math.pi * j / 6 for j in range(6))],
    ],
}
w(f"{G}/stations/drift_station.json", DRIFT_STATION)
gfx["space_stations"]["drift_station"]["local_points"] = blob(0.0, 0.0, 1.0 * 46, 1.0 * 46, 20)

# ======================================================================
# 3. BUILDINGS  (elevation)
# ======================================================================
DRIFT_HALL = {
    "identity": "Drift assembly pavilion, head-on: a wide low canvas dome on rounded timber posts, the whole front open, a planted roofline trailing greenery, a soft grow-lamp band under the eaves. Improvised by committee and quietly alive.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~1.6x PLAYER_H to the dome, ~3.6x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "soft", "note": "back wall", "flatten_px": 60,
         "points": [[-54, 0], [54, 0], [54, -34], [-54, -34]]},
        {"group": "body", "color": "hull", "shade": "soft", "note": "canvas dome",
         "points": [[-56, -34], [-40, -48], [0, -54], [40, -48], [56, -34]]},
        {"group": "body", "color": "engine", "shade": "soft", "note": "open front",
         "points": [[-44, -30], [44, -30], [44, 0], [-44, 0]]},
    ],
    "details": [
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 16, "note": "grow-lamp band",
         "points": [[-50, -32], [50, -32], [50, -27], [-50, -27]]},
        *[{"group": "body", "color": "metal", "shade": "soft", "role": "detail", "min_px": 14, "note": f"timber post {i}",
           "points": [[x - 3, -32], [x + 3, -32], [x + 3, 0], [x - 3, 0]]} for i, x in enumerate((-46, -20, 20, 46))],
        *[{"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 12, "note": f"roof greenery {i}",
           "points": [[x - 6, -50], [x + 6, -50], [x + 4, -42], [x - 4, -42]]} for i, x in enumerate((-30, 0, 30))],
    ],
}

DRIFT_HOUSING = {
    "identity": "Drift habitat terrace, head-on: three rounded residence pods stacked and stepped back, greenery spilling between each level, round windows, a soft timber entry arch. Grown, not built.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~2.8x PLAYER_H tall, ~2.4x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "soft", "note": "pod 1", "flatten_px": 60,
         "points": [[-38, 0], [38, 0], [34, -30], [-34, -30]]},
        {"group": "body", "color": "hull_dk", "shade": "soft", "note": "pod 2",
         "points": [[-32, -30], [32, -30], [28, -56], [-28, -56]]},
        {"group": "body", "color": "hull_dk", "shade": "soft", "note": "pod 3",
         "points": [[-24, -56], [24, -56], [18, -80], [-18, -80]]},
    ],
    "details": [
        {"group": "body", "color": "engine", "shade": "soft", "role": "detail", "min_px": 8, "note": "entry arch",
         "points": [[-8, -16], [8, -16], [6, 0], [-6, 0]]},
        *[{"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 10, "note": f"terrace greenery {i}",
           "points": [[x - 20, y], [x + 20, y], [x + 18, y + 4], [x - 18, y + 4]]} for i, (x, y) in enumerate([(0, -30), (0, -56)])],
        *[{"group": "body", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 10, "note": f"round window {i}",
           "points": [[cx - 4, cy - 4], [cx + 4, cy - 4], [cx + 4, cy + 4], [cx - 4, cy + 4]]}
          for i, (cx, cy) in enumerate([(-18, -16), (18, -16), (-14, -44), (14, -44), (0, -68)])],
    ],
}

DRIFT_SPIRE = {
    "identity": "Drift assembly-tree, head-on: a tall woven trellis mast strung with grow-lamps, widening to a lit canopy crown where the rolling assembly gathers. Not authority - a gathering point. The one tall thing in Highcanopy.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~4.2x PLAYER_H tall, ~1.8x wide at the crown",
    "silhouette": [
        {"group": "body", "color": "metal", "shade": "soft", "note": "trellis mast", "flatten_px": 55,
         "points": [[-6, 0], [6, 0], [5, -96], [-5, -96]]},
        {"group": "crown", "color": "hull", "shade": "soft", "note": "canopy crown",
         "points": [[-28, -96], [-18, -118], [0, -128], [18, -118], [28, -96]]},
    ],
    "details": [
        {"group": "crown", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 16, "note": "crown grow-lamp", "circle": [0, -112, 6]},
        *[{"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 10, "note": f"mast lamp {i}",
           "points": [[-5, y], [5, y], [5, y + 3], [-5, y + 3]]} for i, y in enumerate((-24, -48, -72))],
        *[{"group": "body", "color": "metal", "shade": "soft", "role": "detail", "min_px": 12, "note": f"trellis cross {i}",
           "points": [[-6, y], [6, y], [6, y + 2], [-6, y + 2]]} for i, y in enumerate((-12, -36, -60, -84))],
    ],
}

BUILDINGS = {
    "drift_hall": (DRIFT_HALL, {"width": 112, "depth": 34.0}),
    "drift_housing": (DRIFT_HOUSING, {"width": 76, "depth": 26.0}),
    "drift_spire": (DRIFT_SPIRE, {"width": 56, "depth": 20.0}),
}
bt = r(f"{S}/building_types.json")
for bid, (design, fp) in BUILDINGS.items():
    w(f"{G}/buildings/{bid}.json", design)
    bt[bid]["footprint"] = fp
w(f"{S}/building_types.json", bt)

# ======================================================================
# 4. DRESS PALETTE + BESPOKE WARDROBE
# ======================================================================
dress = r(f"{G}/palettes/{DRESS}.json")
dress["identity"] = "Drift dress - pale sage canvas and undyed timber-tan, soft brass fittings, a grow-green trim woven through. Human skin/hair unchanged."
dress.update({"cloth": "#b9c3a4", "denim": "#8f9a78", "knit": "#c9d0b4", "leather": "#a8916a",
              "metal": "#b7a67e", "glass": "#bff0a0", "lamp": "#c8f0a8"})
w(f"{G}/palettes/{DRESS}.json", dress)

ARTICLES = {
    "drift_speaker_sash": article(
        "Drift speaker-for-now sash - a wide woven band worn across the chest by whoever holds the floor in the rolling assembly. Passed on, not kept.",
        DRESS, [sash_region("lamp", "glow", tag="bandolier", note="speaker sash")]),
    "drift_leaf_mantle": article(
        "Drift leaf mantle - a soft layered shoulder wrap of overlapping canvas leaves, worn by growers and hosts against the cloud-city chill.",
        DRESS, [region("torso", "long coat", "leaf mantle", "cloth", "soft",
                       [[-4.6, -25.6], [4.6, -25.6], [3.8, -18.0], [-3.8, -18.0]],
                       [[-4.1, -25.5], [4.1, -25.5], [3.4, -18.6], [-3.4, -18.6]],
                       m_det=[{"group": "torso", "color": "denim", "shade": "soft", "note": "mantle leaf edge",
                               "points": [[-4.2, -20.5], [4.2, -20.5], [3.6, -18.4], [-3.6, -18.4]]}],
                       f_det=[{"group": "torso", "color": "denim", "shade": "soft", "note": "mantle leaf edge",
                               "points": [[-3.7, -21.0], [3.7, -21.0], [3.2, -19.0], [-3.2, -19.0]]}])]),
    "drift_grower_apron": article(
        "Drift grower's apron - a canvas apron from the waist to mid-shin with two seed pockets and a grow-green hem, worn on the agri-rings.",
        DRESS, [apron_region("denim", "soft", "grower's apron"),
                region("torso", "hip accessory", "seed pocket", "leather", "soft",
                       [[-2.6, -17.0], [-0.6, -17.0], [-0.6, -14.0], [-2.6, -14.0]],
                       [[-2.3, -17.4], [-0.5, -17.4], [-0.5, -14.4], [-2.3, -14.4]])]),
    "drift_woven_collar": article(
        "Drift woven collar - a soft open collar of plaited fibre with a small grow-lamp bead at the throat. Everyday Drift dress.",
        DRESS, [region("torso", "collar", "woven collar", "knit", "soft",
                       [[-2.2, -24.6], [2.2, -24.6], [2.4, -26.2], [-2.4, -26.2]],
                       [[-2.0, -24.7], [2.0, -24.7], [2.2, -26.0], [-2.2, -26.0]],
                       m_det=[{"group": "torso", "color": "lamp", "shade": "glow", "note": "collar bead", "points": [[-0.4, -25.6], [0.4, -25.6], [0.4, -25.0], [-0.4, -25.0]]}],
                       f_det=[{"group": "torso", "color": "lamp", "shade": "glow", "note": "collar bead", "points": [[-0.4, -25.5], [0.4, -25.5], [0.4, -24.9], [-0.4, -24.9]]}])]),
    "drift_militia_band": article(
        "Drift militia band - a plain arm band with a hand-painted mark, the whole of the Drift's 'security': a neighbour who agreed to stand watch this week.",
        DRESS, [brassard_region("denim", "soft", "lamp", "militia band")]),
}

SETS = {
    "drift_command": {"identity": "Drift speaker's turn-out - pale canvas tunic and soft trousers, the leaf mantle, the speaker-for-now sash, a woven collar, canvas shoes.",
                      "articles": ["tank_top", "jacket_tan", "pants_tan", "shoes",
                                   "drift_leaf_mantle", "drift_speaker_sash", "drift_woven_collar", "hair_swept"]},
    "drift_security": {"identity": "Drift watch kit - everyday clothes with the militia band and a woven collar. No uniform - the Drift doesn't have one.",
                       "articles": ["tank_top", "jacket_olive", "pants_field", "boots_charcoal",
                                    "drift_militia_band", "drift_woven_collar", "hair_short"]},
    "drift_dock": {"identity": "Drift grower / ferry-hand kit - work tunic under the grower's apron, the leaf mantle, gloves, a woven collar.",
                   "articles": ["tank_top", "jacket_dock", "pants_dock", "boots_charcoal", "gloves_dark",
                                "drift_grower_apron", "drift_woven_collar", "hair_bun"]},
    "drift_flight": {"identity": "Drift skiff-pilot kit - light canvas suit, a soft flight helmet, the leaf mantle, a woven collar.",
                     "articles": ["tank_top", "jacket_tan", "pants_tan", "shoes", "helmet_flight",
                                  "drift_leaf_mantle", "drift_woven_collar"]},
    "drift_civilian": {"identity": "Drift everyday dress - soft layered canvas, the woven collar everyone wears, plaited-fibre shoes.",
                       "articles": ["tank_top", "jacket_civ", "pants", "shoes",
                                    "drift_woven_collar", "drift_leaf_mantle", "hair_long"]},
}
ROLE_SET = {"civilian": "drift_civilian", "official": "drift_command", "flight": "drift_flight",
            "security": "drift_security", "dock": "drift_dock"}
write_wardrobe(gfx, PFX, DRESS, ARTICLES, SETS, ROLE_SET)
w(f"{S}/graphics.json", gfx)

# ======================================================================
# 5. HIGHCANOPY floor plan + roster
# ======================================================================
HC_ROOMS = concourse_plan("Canopy Walk", [
    BAY_N(240, 620, "The Rolling Assembly"),
    BAY_N(820, 1100, "Seed Store"),
    BAY_N(1200, 1480, "Ferry Slip"),
    BAY_S(160, 480, "Water Office"),
    BAY_S(1120, 1480, "Canopy Rest"),
])
HC_STRUCTURES = [
    {"x": 800, "y": 650, "building_type": "drift_spire"},
    *[{"x": x, "y": 582, "building_type": "planter"} for x in (560, 700, 900, 1040)],
    *[{"x": x, "y": 718, "building_type": "planter"} for x in (560, 700, 900, 1040)],
    {"x": 400, "y": 470, "building_type": "pipeline_bench"},
    {"x": 300, "y": 900, "building_type": "planter"},
    {"x": 1320, "y": 470, "building_type": "crates"},
    {"x": 1300, "y": 900, "building_type": "pipeline_bench"},
]
HC_NPCS = [
    {"name": "Sela of Highcanopy", "x": 800, "y": 660, "role": "concierge",
     "faction": "the_drift", "outfit": "drift_official_femme",
     "escort_flag": "assembly_walking",
     "ambient": {"range": 700, "message": "Oh - a new face! Welcome in. There's nobody in charge exactly, but I speak for the assembly this week. Come say hello (walk over, press T)."},
     "dialogue_tree": {"root": "start", "conditional_roots": [
         {"flag": "assembly_done", "node": "done"},
         {"flag": "assembly_accepted", "node": "midway"},
         {"faction": "the_drift", "min": 25, "node": "warm"}],
      "nodes": {
        "start": {"text": "The beacon relit and the assembly's been rolling for six days without a decision. Half of us want to open the lane to Ossuary, half think the Relay coming back is how Kiln finds an excuse to send warships. I can't force a vote - but if you carry three neighbours' views back here in person, the room has to sit and choose. Will you?",
                  "options": [
                      {"label": "I'll gather the three views.", "next": "accepted",
                       "actions": ["set_flag:assembly_accepted", "start_mission:the_drift_assembly"]},
                      {"label": "Decide it yourselves.", "next": None}]},
        "accepted": {"text": "Thank you. Ferry-wright Osei at the Slip, Water-keeper Tam at the Water Office, and old Bevin down in Canopy Rest. Hear each of them out and come back.",
                     "options": [{"label": "On my way", "next": None}]},
        "midway": {"text": "Still gathering? Osei, Tam, and Bevin. Your Mission Log has them. The room won't sit until all three have been heard.",
                   "options": [{"label": "Keep going", "next": None},
                               {"label": "I'll leave you to it", "next": "declined", "action": "abandon_mission:the_drift_assembly"}]},
        "declined": {"text": "That's alright. We'll get there. We always do, eventually. Ossuary's lane is keyed for you whenever you want it - go gently.",
                     "options": [{"label": "Thanks", "next": None, "action": "light_beacon:ossuary"}]},
        "done": {"text": "The room chose - narrowly, and nobody's happy, which is how you know it was fair. Ossuary's lane is open, and we've sent word we may need friends soon. Thank you for making us sit down.",
                 "options": [{"label": "Safe assembly", "next": None}]},
        "warm": {"text": "You gave us a decision when we couldn't reach one ourselves. If the Span asks what the Drift wants, we'd trust you to say it: open, and ungoverned.",
                 "options": [
                     {"label": "Pledge the Drift your voice.", "next": "pledged",
                      "requires_not_flag": "patron:the_drift",
                      "actions": ["set_exclusive_flag:patron:the_drift", "adjust_rep:the_drift:8"]},
                     {"label": "I'll think on it", "next": None}]},
        "pledged": {"text": "Then you speak for us at the Hub. Keep it open. Keep it everyone's.",
                    "options": [{"label": "Understood", "next": None}]}}}},

    {"name": "Ferry-wright Osei", "x": 1320, "y": 470, "role": "ship_salesman",
     "faction": "the_drift", "outfit": "drift_official_masc",
     "dialogue_tree": {"root": "start", "conditional_roots": [{"flag": "assembly_view_osei", "node": "heard"}], "nodes": {
        "start": {"text": "We refit liners and barges, mostly - roomy, slow, kind to fly. You're carrying views to the assembly? Mine's simple: open the lane. Trade's been a decades-long loop my whole life. Let it be a day.",
                  "options": [
                      {"label": "I'll carry that.", "next": "ok", "requires_flag": "assembly_accepted",
                       "actions": ["set_flag:assembly_view_osei"]},
                      {"label": "Just browsing.", "action": "open_shop", "next": None}]},
        "ok": {"text": "Good. Tell Sela the Slip votes to open. And come back if you need a hull with room to sleep in.",
               "options": [{"label": "Understood", "action": "open_shop", "next": None}]},
        "heard": {"text": "You've got my view. Open the lane. Now - a barge, or just looking?",
                  "options": [{"label": "Show me the hulls", "action": "open_shop", "next": None}, {"label": "Leave", "next": None}]}},
      }, "shop": {"type": "ships", "stock": ["drift_hauler", "drift_courier", "carrier_hauler", "carrier_courier"]}},

    {"name": "Water-keeper Tam", "x": 300, "y": 470, "role": "quartermaster",
     "faction": "the_drift", "outfit": "drift_dock_femme",
     "dialogue_tree": {"root": "start", "conditional_roots": [{"flag": "assembly_view_tam", "node": "heard"}], "nodes": {
        "start": {"text": "I keep the ring's water accounts. My view for the assembly? Caution. If we open the lane, Kiln's next through it, and they don't send traders. But I won't stand in the way of a vote.",
                  "options": [
                      {"label": "I'll carry that.", "next": "ok", "requires_flag": "assembly_accepted",
                       "actions": ["set_flag:assembly_view_tam"]},
                      {"label": "What do you trade?", "action": "open_shop", "next": None}]},
        "ok": {"text": "Thank you. Tell them the Water Office says wait - but says it, doesn't shout it.",
               "options": [{"label": "Understood", "action": "open_shop", "next": None}]},
        "heard": {"text": "You have my view. Trade, if you need to.", "options": [{"label": "Trade", "action": "open_shop", "next": None}, {"label": "Leave", "next": None}]}},
      }, "shop": {"type": "commodities", "stock": ["grain", "water_credits"], "sell_multiplier": 1.1}},

    {"name": "Old Bevin", "x": 1300, "y": 900, "role": "bartender",
     "faction": "the_drift", "outfit": "drift_civilian_masc",
     "dialogue_tree": {"root": "start", "conditional_roots": [{"flag": "assembly_view_bevin", "node": "heard"}], "nodes": {
        "start": {"text": "Canopy Rest. I've watched the Drift not-decide things for sixty years. My view? Doesn't matter which way. What matters is we choose together and mean it. Tell the room that.",
                  "options": [
                      {"label": "I'll carry that.", "next": "ok", "requires_flag": "assembly_accepted",
                       "actions": ["set_flag:assembly_view_bevin"]},
                      {"label": "Pour me one.", "next": "drink"}]},
        "ok": {"text": "Good lad. Now sit - one cup before you go back up there.",
               "options": [{"label": "Thanks", "next": "drink"}]},
        "heard": {"text": "Said my piece. Have a cup.", "options": [{"label": "Thanks", "next": "drink"}, {"label": "Leave", "next": None}]},
        "drink": {"text": "Highcanopy cordial. Grown three rings over. Sl? Cheers.", "options": [{"label": "Cheers", "next": None}]}}}},

    {"name": "Seed-warden Nim", "x": 900, "y": 470, "role": "clerk",
     "faction": "the_drift", "outfit": "drift_dock_masc",
     "greeting": "Every habitat sends a seed-share to the store, every habitat draws one back. It's worked for two hundred years without anyone in charge of it. That frightens the Authority more than any warship.",
     "dialogue_options": ["I can see why", "Leave"]},

    {"name": "Canopy-warden Rue", "x": 640, "y": 700, "role": "guard",
     "faction": "the_drift", "outfit": "drift_security_femme",
     "greeting": "I've the watch this week. It's just walking the Walk and being someone to shout for. Next week it's someone else. That's the whole militia.",
     "dialogue_options": ["Understood", "Leave"]},

    {"name": "Trellis-hand Fen", "x": 960, "y": 700, "role": "outfitter",
     "faction": "the_drift", "outfit": "drift_security_masc",
     "greeting": "We don't really make weapons. But the light-lances off the watchboats fit a civilian hull, and a hull that carries more grain is a hull worth more to everyone.",
     "shop": {"type": "outfits", "stock": ["pulse_blaster", "afterburner", "cargo_expansion", "reinforced_hull", "laser_cannon", "shield_capacitor", "sensor_array"]}},

    {"name": "Under-ring traveller", "x": 400, "y": 700, "role": "resident",
     "faction": "the_drift", "outfit": "drift_civilian_femme",
     "greeting": "The beacon relit and half of us are thrilled and half are terrified. That's Verdance for you. We'll talk about it for a month.",
     "dialogue_options": ["Ha", "Leave"]},

    {"name": "Carrier at the Slip", "x": 1240, "y": 700, "role": "traveler",
     "faction": "free_carrier", "outfit": "carrier_flight_masc",
     "requires_flag": "beacon_ossuary_lit",
     "greeting": "Drift's the only system that just lets us tie up and rest. Carriers won't forget that when the Hub asks who to trust.",
     "dialogue_options": ["Fly safe", "Leave"]},
]
HC_INTERIOR = {"label": "Highcanopy", "culture": "the_drift",
               "portals": [{"x": 1360, "y": 470, "connected_locations": [], "return_to_ship": True}],
               "rooms": HC_ROOMS, "structures": HC_STRUCTURES, "npcs": HC_NPCS,
               **station_shell(PFX, 203)}


def undergarden_moon():
    return {
        "name": "the Undergarden", "x": 0.8, "y": 0.8, "size": 32, "color": [110, 140, 100],
        "crater_color": [80, 108, 74], "landing_distance": 36,
        "craters": [{"x": -9, "y": -3, "radius": 4}, {"x": 8, "y": 8, "radius": 5}],
        "interiors": {"city": {
            "label": "the Undergarden", "culture": "the_drift",
            "connected_locations": [], "entrance": {"x": 800, "y": 840},
            "rooms": [rect(160, 220, 1440, 1140, "Undergarden Ring")],
            "structures": [
                {"x": 800, "y": 520, "building_type": "drift_hall"},
                {"x": 440, "y": 780, "building_type": "drift_housing"},
                {"x": 1160, "y": 780, "building_type": "drift_housing"},
                {"x": 800, "y": 320, "building_type": "drift_spire"},
                *[{"x": x, "y": 1000, "building_type": "planter"} for x in (520, 700, 900, 1080)],
                {"x": 320, "y": 1060, "building_type": "pipeline_bench"},
                {"x": 1300, "y": 1060, "building_type": "pipeline_bench"},
            ],
            "npcs": [
                {"name": "Speaker-for-now Adda", "x": 800, "y": 700, "role": "magistrate",
                 "faction": "the_drift", "outfit": "drift_official_femme",
                 "greeting": "The Undergarden grows most of what the ring eats. If the vote goes to open the lane, we're the ones Kiln's warships pass first. I hope your three views weigh that.",
                 "dialogue_options": ["Understood", "Leave"]},
                {"name": "Grower Pell", "x": 520, "y": 620, "role": "resident",
                 "faction": "the_drift", "outfit": "drift_civilian_masc",
                 "greeting": "Forty crops I've raised down here. Never once needed a hierarchy to do it. Tell that to whoever asks.",
                 "dialogue_options": ["I will", "Leave"]},
                {"name": "Canopy-hand Wen", "x": 1080, "y": 900, "role": "dockworker",
                 "faction": "the_drift", "outfit": "drift_dock_femme",
                 "greeting": "Grain run's ready whenever the assembly says a word. We've been ready for six days.",
                 "dialogue_options": ["Soon", "Leave"]},
            ],
        }},
    }


VERDANCE = {
    "name": "Verdance",
    "description": "A gas giant with a single enormous cloud-city and a ring of agricultural habitats. The Drift runs on rolling consensus, holds no fixed hierarchy, and is the most welcoming - and least decisive - system in the region.",
    "star_map_position": {"x": 210, "y": 150},
    "station_asset": "drift_station", "moon_asset": "drift_moon",
    "central_star": {"x": 0.5, "y": 0.5, "name": "Verdance", "size": 92, "color": [255, 236, 168]},
    "player_start": {"x": 0.4, "y": 0.35}, "star_seed": 203,
    "asteroid_field": {"per_chunk_range": [1, 2], "types": [
        {"type": "gray_rock", "weight": 3, "size_range": [3, 14], "speed_range": [0.05, 0.28], "mine_yield": 8}]},
    "station": {"x": 0.2, "y": 0.24, "name": "Highcanopy", "interiors": {"default": HC_INTERIOR}},
    "moon": undergarden_moon(),
    "celestial_bodies": [
        {"name": "Verdance", "x": 0.5, "y": 0.5, "size": 62, "color": [210, 190, 120], "body_type": "gas_giant",
         "has_ring": True, "ring_color": [180, 200, 150]},
        {"name": "Ring Nine", "x": 0.28, "y": 0.66, "size": 10, "color": [150, 170, 130], "body_type": "rocky"}],
    "ai_ships": [
        {"name": "Drift Watch Sella", "x": 0.55, "y": 0.16, "ship_type": "drift_patrol", "pilot": "sella",
         "faction": "the_drift", "route": ["station", "moon"]},
        {"name": "Canopy Barge Nim", "x": 0.35, "y": 0.22, "ship_type": "drift_hauler", "pilot": "nim",
         "faction": "the_drift", "route": ["station", "moon"]},
        {"name": "Grain Run Ost", "x": 0.68, "y": 0.6, "ship_type": "drift_hauler", "pilot": "ost",
         "faction": "the_drift", "route": ["moon", "station"]},
        {"name": "Combine Raider", "x": 0.55, "y": 0.45, "ship_type": "combine_patrol", "pilot": "raska",
         "faction": "ninefold_combine", "route": ["station", "moon"],
         "requires_rep_below": "ninefold_combine:-20"},
        # Kiln mobilisation (Act II) - the Combine's "notice of closure"
        # dispatch (combine_mobilises -> combine_mobilised) puts a blockade
        # pair over the Verdance lane. Hostile only if the player's Combine
        # standing has fallen past the threshold (_sync_hostiles); otherwise
        # a visible pressure on the region.
        {"name": "Combine Blockade Corran", "x": 0.62, "y": 0.3, "ship_type": "combine_patrol", "pilot": "corran",
         "faction": "ninefold_combine", "route": ["station", "moon"],
         "requires_flag": "combine_mobilised"},
        {"name": "Combine Blockade Molt", "x": 0.4, "y": 0.72, "ship_type": "combine_patrol", "pilot": "molt",
         "faction": "ninefold_combine", "route": ["moon", "station"],
         "requires_flag": "combine_mobilised"},
    ],
    "locked": True, "unlock_flag": "beacon_verdance_lit",
}
w(f"{S}/systems/verdance.json", VERDANCE)

# ======================================================================
# 6. ANCHOR MISSION  "the_drift_assembly"  (welcoming; lights Ossuary + Act II)
# ======================================================================
SELA = "Sela of Highcanopy"
ASSEMBLY = {
    "title": "A Rolling Assembly",
    "escort_flag": "assembly_walking",
    "on_end_flags": ["assembly_done", "beacon_ossuary_lit", "act_pressure"],
    "on_start_rep": {"the_drift": 3},
    "on_end_rep": {"the_drift": 6},
    "stages": [
        {"text": "Hear Ferry-wright Osei's view - the Ferry Slip (north-east).",
         "complete_flag": "assembly_view_osei",
         "one_way_message": say(SELA, "Osei's at the Ferry Slip, north-east end of the Walk. He'll have an opinion - he always does.")},
        {"text": "Hear Water-keeper Tam's view - the Water Office (south-west).",
         "complete_flag": "assembly_view_tam",
         "one_way_message": say(SELA, "Tam keeps the water accounts, south-west. Hers is the cautious voice. Hear it properly.")},
        {"text": "Hear Old Bevin's view - Canopy Rest (south-east).",
         "complete_flag": "assembly_view_bevin",
         "one_way_message": say(SELA, "Bevin's down in Canopy Rest with a cup. Sixty years of watching us dither - he's earned a hearing.")},
        {"text": "Bring the three views back to Sela and let the assembly sit.",
         "complete_flag": "assembly_convened",
         "one_way_message": say(SELA, "You've heard all three? Come back to the assembly floor. With every view in the room in person, we have to choose - and we will.")},
    ],
}
missions = r(f"{S}/missions.json")
missions["the_drift_assembly"] = ASSEMBLY
w(f"{S}/missions.json", missions)

# Sela needs a "convene the assembly" branch that fires the final stage +
# lights Ossuary; wired as a conditional root once all three views are in.
sysj = r(f"{S}/systems/verdance.json")
hc = sysj["station"]["interiors"]["default"]
for npc in hc["npcs"]:
    if npc["name"] == SELA:
        cr = npc["dialogue_tree"]["conditional_roots"]
        # after "assembly_done" (index 0), before "assembly_accepted"->midway:
        # once all three views are in, route to the convene-the-vote node.
        cr.insert(1, {"flag": "assembly_view_bevin", "node": "convene"})
        npc["dialogue_tree"]["nodes"]["convene"] = {
            "text": "All three, heard in person. Then the assembly sits - now, with you in the room. ... It's done. Narrowly. We open the lane to Ossuary, and we send word we may need friends. Thank you for making us choose.",
            "options": [
                {"label": "Understood", "next": None, "requires_not_flag": "assembly_convened",
                 "actions": ["set_flag:assembly_convened"]}]}
w(f"{S}/systems/verdance.json", sysj)

# ======================================================================
# 7. DRIFT PILOTS
# ======================================================================
pilots = r(f"{S}/pilots.json")
pilots.update({
    "sella": {"name": "Tide-pilot Sella", "faction": "the_drift", "role": "patrol_officer",
                "personality": "Friendly, unhurried, would rather talk anything through than escalate it. The watchboat's light-lance has never been fired.",
                "hail_greeting": "Highcanopy drift-watch. Welcome in - fly gentle near the habitats and we'll get along fine."},
    "nim": {"name": "Canopy-hand Nim", "faction": "the_drift", "role": "freighter_pilot",
            "personality": "Cheerful about the work, vague about the schedule, genuinely delighted to have company on the lane.",
            "hail_greeting": "Grain run for the Undergarden. Lovely day for it, isn't it. Wave if you pass close."},
    "ost": {"name": "Ring-hand Ost", "faction": "the_drift", "role": "freighter_pilot",
            "personality": "Quiet, steady, has flown the same ring loop so long the barge knows the way itself.",
            "hail_greeting": "Drift barge, ring to city. No hurry. There never is."},
})
w(f"{S}/pilots.json", pilots)

print(f"Verdance slice: 3 ships, 1 station, 3 buildings, dress + {len(ARTICLES)} articles / {len(SETS)} sets, "
      f"Highcanopy ({len(HC_ROOMS)} rooms / {len(HC_NPCS)} NPCs), 'the_drift_assembly' "
      f"({len(ASSEMBLY['stages'])} stages), {len(pilots)} pilots.")
