"""Phase 6.4 - the Ossuary slice (the Vigil), end to end.

Owns systems/ossuary.json. Run after gen_verdance (see docs/gen/README.md).
Produces the Vigil's austere vertical ships/station/buildings, a bespoke
mourning-dress wardrobe, the Name-Wall floor plan + roster, and the anchor
mission "the_vigil_record" - the one that delivers the true history of the
Silence and the warning, then lights the Span's beacon.

Vigil style (cultures.json): austere and vertical - long cold halls, name-walls,
narrow light, unpolished grey stone and violet-white glass, no decoration that
is not a record. A library that is also a tomb.
"""
from _slice_kit import (S, G, w, r, rect, concourse_plan, BAY_N, BAY_S, disc,  say, station_shell,
                        article, region, write_wardrobe, stole_region,
                        pendant_region, hood_region, sash_region, apron_region)

PFX = "vigil"
DRESS = "vigil_dress"


def name_grid(group, x0, x1, y0, y1, cols, rows, note, nw=2.2, nh=1.4):
    """A grid of tiny recessed niches - a name-wall. nw/nh are the niche
    half-size, in the design's own units (default building-scale; pass a
    small fraction for a ship or station where coords are fractions of size)."""
    out = []
    for r_ in range(rows):
        for c_ in range(cols):
            cx = x0 + (x1 - x0) * (c_ + 0.5) / cols
            cy = y0 + (y1 - y0) * (r_ + 0.5) / rows
            out.append({"group": group, "color": "engine", "shade": "matte", "role": "detail", "min_px": 8,
                        "note": f"{note} {r_}x{c_}",
                        "points": [[cx - nw, cy - nh], [cx + nw, cy - nh], [cx + nw, cy + nh], [cx - nw, cy + nh]]})
    return out


# ======================================================================
# 1. SHIPS  - narrow vertical spear hulls
# ======================================================================
VIGIL_COURIER = {
    "identity": "Vigil Stele - a narrow vertical dart: a long needle prow, a slender grey body, one small tail flare, a single violet-white lamp at the nose. No ornament. Reads at a dozen pixels as a thin bright-tipped line.",
    "tier": "ship_near", "palette": PFX, "size": 11,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "prow", "color": "metal", "shade": "metal", "flatten_px": 45, "note": "needle prow",
         "points": [[0.0, -1.3], [0.06, -0.7], [-0.06, -0.7]]},
        {"group": "hull", "color": "hull", "shade": "deep", "flatten_px": 40, "note": "slender body",
         "points": [[-0.16, -0.7], [0.16, -0.7], [0.2, 0.7], [0.14, 1.0], [-0.14, 1.0], [-0.2, 0.7]]},
        {"group": "flare", "color": "engine", "shade": "deep", "flatten_px": 45, "note": "tail flare",
         "points": [[-0.2, 0.8], [0.2, 0.8], [0.28, 1.08], [-0.28, 1.08]]},
    ],
    "details": [
        {"group": "hull", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 55,
         "note": "slit canopy", "points": [[-0.05, -0.6], [0.05, -0.6], [0.05, -0.2], [-0.05, -0.2]]},
        {"group": "hull", "color": "engine", "shade": "matte", "role": "detail", "min_px": 60,
         "note": "engraved band", "points": [[-0.18, 0.2], [0.19, 0.2], [0.19, 0.28], [-0.18, 0.28]]},
        {"group": "prow", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 90, "note": "nose lamp", "circle": [0.0, -1.24, 0.05]},
        {"group": "flare", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "thruster", "circle": [0.0, 1.08, 0.16]},
    ],
}

VIGIL_HAULER = {
    "identity": "Vigil Reliquary - a tall narrow barge: a vertical grey slab faced with rows of sealed niches like a columbarium, a slender command spine forward, a single broad tail thruster. Carries the dead and the archives, nothing lighter. Reads as a standing stone with a violet base-glow.",
    "tier": "ship_near", "palette": PFX, "size": 19,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "deep", "flatten_px": 60, "note": "reliquary slab",
         "points": [[-0.28, -1.05], [0.28, -1.05], [0.32, -0.85], [0.32, 0.9], [0.24, 1.06], [-0.24, 1.06], [-0.32, 0.9], [-0.32, -0.85]]},
        {"group": "spine", "color": "metal", "shade": "metal", "flatten_px": 50, "note": "command spine",
         "points": [[-0.05, -1.2], [0.05, -1.2], [0.05, -0.9], [-0.05, -0.9]]},
        {"group": "engine", "color": "engine", "shade": "deep", "flatten_px": 50, "note": "tail thruster block",
         "points": [[-0.3, 0.86], [0.3, 0.86], [0.22, 1.16], [-0.22, 1.16]]},
    ],
    "details": [
        *name_grid("hull", -0.24, 0.24, -0.7, 0.7, 2, 5, "sealed niche", nw=0.07, nh=0.05),
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 40, "note": "base glow",
         "points": [[-0.3, 0.78], [0.3, 0.78], [0.3, 0.84], [-0.3, 0.84]]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 16, "note": "thruster", "circle": [0.0, 1.14, 0.18]},
    ],
}

VIGIL_PATROL = {
    "identity": "Vigil Grave-watch - a long austere dart with a single forward light-lance running most of its length, a thin armoured collar amidships, one broad tail thruster. The Vigil does not raid; it keeps a distance and enforces one. Reads as a bright vertical needle.",
    "tier": "ship_near", "palette": PFX, "size": 15,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "deep", "flatten_px": 45, "note": "long dart",
         "points": [[0.0, -1.24], [0.14, -0.6], [0.18, 0.7], [0.12, 1.0], [-0.12, 1.0], [-0.18, 0.7], [-0.14, -0.6]]},
        {"group": "collar", "color": "metal", "shade": "metal", "flatten_px": 50, "note": "armoured collar",
         "points": [[-0.26, -0.1], [0.26, -0.1], [0.26, 0.12], [-0.26, 0.12]]},
        {"group": "flare", "color": "engine", "shade": "deep", "flatten_px": 45, "note": "tail thruster",
         "points": [[-0.2, 0.82], [0.2, 0.82], [0.26, 1.08], [-0.26, 1.08]]},
    ],
    "details": [
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 40,
         "note": "forward light-lance", "points": [[-0.04, -1.15], [0.04, -1.15], [0.04, 0.4], [-0.04, 0.4]]},
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 20, "note": "lance tip", "circle": [0.0, -1.2, 0.05]},
        {"group": "collar", "color": "engine", "shade": "matte", "role": "detail", "min_px": 50,
         "note": "engraved collar band", "points": [[-0.24, 0.0], [0.24, 0.0], [0.24, 0.05], [-0.24, 0.05]]},
        {"group": "flare", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "thruster", "circle": [0.0, 1.06, 0.14]},
    ],
}

SHIP_DESIGNS = {
    "vigil_courier": (VIGIL_COURIER, [[0.0, 1.06]],
                      [[0.0, -1.3], [0.2, 0.7], [0.28, 1.08], [-0.28, 1.08], [-0.2, 0.7]]),
    "vigil_hauler": (VIGIL_HAULER, [[0.0, 1.12]],
                     [[-0.32, -0.85], [0.32, -0.85], [0.32, 0.9], [0.22, 1.16], [-0.22, 1.16], [-0.32, 0.9]]),
    "vigil_patrol": (VIGIL_PATROL, [[0.0, 1.04]],
                     [[0.0, -1.24], [0.18, 0.7], [0.26, 1.08], [-0.26, 1.08], [-0.18, 0.7]]),
}
for sid, (design, thr, local) in SHIP_DESIGNS.items():
    w(f"{G}/ships/{sid}.json", design)

gfx = r(f"{S}/graphics.json")
for sid, (design, thr, local) in SHIP_DESIGNS.items():
    e = gfx["ships"][sid]
    e["local_points"] = local
    e["thrusters"] = thr
    e["thruster_width"] = 0.09
    e["thruster_length"] = 20

# ======================================================================
# 2. STATION  "the Name-Wall" - a standing-stone monolith
# ======================================================================
VIGIL_STATION = {
    "identity": "the Name-Wall - the Vigil's orbital dock: a tall narrow grey monolith, its whole face carved in ranked name-niches, three shallow docking notches down each side, a single violet-white crown light. It does not turn. Reads as a standing stone with a violet tip.",
    "tier": "station", "palette": PFX, "size": 46,
    "units": "fractions of `size`; NOT radially symmetric - a fixed vertical monolith.",
    "silhouette": [
        {"group": "shaft", "color": "hull", "shade": "deep", "flatten_px": 60, "note": "monolith shaft",
         "points": [[-0.34, -1.3], [0.34, -1.3], [0.4, -1.1], [0.4, 1.1], [0.3, 1.3], [-0.3, 1.3], [-0.4, 1.1], [-0.4, -1.1]]},
        {"group": "crown", "color": "glass", "shade": "flat", "flatten_px": 200, "note": "violet crown light",
         "points": [[-0.24, -1.4], [0.24, -1.4], [0.16, -1.28], [-0.16, -1.28]]},
        *[{"group": f"notch_{s}{i}", "color": "engine", "shade": "matte", "flatten_px": 55,
           "note": f"{'east' if s > 0 else 'west'} docking notch {i}",
           "points": [[s * 0.4, y - 0.12], [s * 0.56, y - 0.12], [s * 0.56, y + 0.12], [s * 0.4, y + 0.12]]}
          for s in (1, -1) for i, y in enumerate((-0.55, 0.0, 0.55))],
    ],
    "details": [
        {"group": "crown", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 24, "note": "crown glow", "circle": [0.0, -1.34, 0.1]},
        *name_grid("shaft", -0.3, 0.3, -1.0, 1.0, 4, 12, "name niche", nw=0.05, nh=0.03),
        *[{"group": f"notch_{s}{i}", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 26,
           "note": f"dock light {i}", "circle": [s * 0.5, y, 0.04]}
          for s in (1, -1) for i, y in enumerate((-0.55, 0.0, 0.55))],
    ],
}
w(f"{G}/stations/vigil_station.json", VIGIL_STATION)
gfx["space_stations"]["vigil_station"]["local_points"] = [
    [-0.34 * 46, -1.3 * 46], [0.34 * 46, -1.3 * 46], [0.4 * 46, -1.1 * 46], [0.4 * 46, 1.1 * 46],
    [0.3 * 46, 1.3 * 46], [-0.3 * 46, 1.3 * 46], [-0.4 * 46, 1.1 * 46], [-0.4 * 46, -1.1 * 46]]
gfx["space_stations"]["vigil_station"]["rotation_speed"] = 0.0

# ======================================================================
# 3. BUILDINGS  (elevation)
# ======================================================================
VIGIL_HALL = {
    "identity": "Vigil archive hall, head-on: a tall narrow slab of unpolished grey, its entire face a ranked grid of sealed name-niches, one narrow violet-lit doorway at the base, a thin cornice. Nothing that is not a record.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~3.4x PLAYER_H tall, ~2.2x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "matte", "note": "wall", "flatten_px": 60,
         "points": [[-34, 0], [34, 0], [34, -104], [-34, -104]]},
        {"group": "body", "color": "hull", "shade": "deep", "note": "cornice",
         "points": [[-36, -104], [36, -104], [36, -110], [-36, -110]]},
        {"group": "body", "color": "glass", "shade": "sheen", "note": "violet doorway",
         "points": [[-6, -22], [6, -22], [6, 0], [-6, 0]]},
    ],
    "details": name_grid("body", -30, 30, -100, -26, 5, 9, "name niche") + [
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 12, "note": "door lamp",
         "points": [[-5, -21], [5, -21], [5, -17], [-5, -17]]},
    ],
}

VIGIL_HOUSING = {
    "identity": "Vigil cell-block, head-on: a tall narrow grey stack, one column of small square cell windows lit violet-white, a single low doorway, a thin parapet. Austere to the point of severity.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~3x PLAYER_H tall, ~1.4x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "matte", "note": "wall", "flatten_px": 60,
         "points": [[-22, 0], [22, 0], [22, -94], [-22, -94]]},
        {"group": "body", "color": "hull", "shade": "deep", "note": "parapet",
         "points": [[-24, -94], [24, -94], [24, -100], [-24, -100]]},
        {"group": "body", "color": "engine", "shade": "matte", "note": "doorway",
         "points": [[-6, -14], [6, -14], [6, 0], [-6, 0]]},
    ],
    "details": [
        *[{"group": "body", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 10, "note": f"cell {i}",
           "points": [[-6, cy], [6, cy], [6, cy + 8], [-6, cy + 8]]} for i, cy in enumerate((-84, -68, -52, -36, -24))],
        {"group": "body", "color": "engine", "shade": "matte", "role": "detail", "min_px": 20, "note": "seam",
         "points": [[-20, -48], [20, -48], [20, -46], [-20, -46]]},
    ],
}

VIGIL_SPIRE = {
    "identity": "the Vigil-tower, head-on: a very tall thin grey obelisk tapering to a point, a single violet-white lamp at the peak, three engraved memorial bands down the shaft. The tallest thing in a dead system, and the quietest.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~5.2x PLAYER_H tall, ~1x wide at the base",
    "silhouette": [
        {"group": "body", "color": "hull", "shade": "deep", "note": "obelisk", "flatten_px": 55,
         "points": [[-15, 0], [15, 0], [4, -150], [-4, -150]]},
        {"group": "cap", "color": "metal", "shade": "metal", "note": "peak cap",
         "points": [[-4, -150], [4, -150], [0, -162]]},
    ],
    "details": [
        {"group": "cap", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 22, "note": "peak lamp", "circle": [0, -156, 4]},
        *[{"group": "body", "color": "engine", "shade": "matte", "role": "detail", "min_px": 16, "note": f"memorial band {i}",
           "points": [[-13 + i * 3, y], [13 - i * 3, y], [13 - i * 3, y + 3], [-13 + i * 3, y + 3]]}
          for i, y in enumerate((-30, -70, -110))],
        {"group": "body", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 12, "note": "base slit",
         "points": [[-3, -40], [3, -40], [3, -10], [-3, -10]]},
    ],
}

BUILDINGS = {
    "vigil_hall": (VIGIL_HALL, {"width": 68, "depth": 22.0}),
    "vigil_housing": (VIGIL_HOUSING, {"width": 44, "depth": 16.0}),
    "vigil_spire": (VIGIL_SPIRE, {"width": 30, "depth": 14.0}),
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
dress["identity"] = "Vigil dress - unbleached cold grey, unpolished pewter, a single violet-white lamp accent. Mourning colours worn every day. Human skin/hair unchanged."
dress.update({"cloth": "#4a4a54", "denim": "#3a3a44", "knit": "#565662", "leather": "#3e3e46",
              "metal": "#8a8a96", "glass": "#d6ccec", "lamp": "#c8bce8"})
w(f"{G}/palettes/{DRESS}.json", dress)

ARTICLES = {
    "vigil_mourning_stole": article(
        "Vigil mourning stole - two long narrow grey panels hung from the shoulders past the waist, each stitched with a single name. Worn by every member of the Vigil, every day.",
        DRESS, [stole_region("cloth", "matte", "mourning stole")]),
    "vigil_name_pendant": article(
        "Vigil name-pendant - a small pewter tablet on a cord at the sternum, carrying the name the wearer keeps watch for.",
        DRESS, [pendant_region("metal", "metal", "name tablet")]),
    "vigil_keeper_cowl": article(
        "Vigil keeper's cowl - a deep grey cowl drawn over the head in the cold halls, a faint violet lamp at the brow. Drops any hairstyle.",
        DRESS, [hood_region("cloth", "matte", "keeper's cowl")]),
    "vigil_ash_sash": article(
        "Vigil ash sash - a narrow grey band worn across the chest by the Wardens of Names, marked with the year they keep.",
        DRESS, [sash_region("denim", "matte", tag="bandolier", note="ash sash")]),
    "vigil_grave_apron": article(
        "Vigil grave-tender's apron - a plain grey apron to the shin with a single tool loop, worn on the grave-moon.",
        DRESS, [apron_region("leather", "deep", "grave apron")]),
}
ARTICLES["vigil_keeper_cowl"]["hides_hair"] = True

SETS = {
    "vigil_command": {"identity": "Vigil Keeper's turn-out - a long grey robe-coat, the mourning stole, a name-pendant, the keeper's cowl, dark shoes.",
                      "articles": ["tank_top", "coat_charcoal", "pants_charcoal", "shoes",
                                   "vigil_mourning_stole", "vigil_name_pendant", "vigil_keeper_cowl"]},
    "vigil_security": {"identity": "Vigil Warden turn-out - grey uniform, a plain helmet, the ash sash, mourning stole, a name-pendant.",
                       "articles": ["tank_top", "jacket_secblue", "pants_secblue", "boots_black", "helmet_sec",
                                    "vigil_ash_sash", "vigil_mourning_stole", "vigil_name_pendant"]},
    "vigil_dock": {"identity": "Vigil grave-tender kit - grey work robe under the apron, the cowl, gloves, a name-pendant.",
                   "articles": ["tank_top", "jacket_civ", "pants_charcoal", "boots_charcoal", "gloves_dark",
                                "vigil_grave_apron", "vigil_keeper_cowl", "vigil_name_pendant"]},
    "vigil_flight": {"identity": "Vigil stele-pilot kit - grey suit, a plain flight helmet, the mourning stole, a name-pendant.",
                     "articles": ["tank_top", "jacket_civ", "pants_charcoal", "boots_black", "helmet_flight",
                                  "vigil_mourning_stole", "vigil_name_pendant"]},
    "vigil_civilian": {"identity": "Vigil daily dress - plain grey robe, the mourning stole and name-pendant every member wears, soft shoes.",
                       "articles": ["tank_top", "jacket_civ", "pants", "shoes",
                                    "vigil_mourning_stole", "vigil_name_pendant", "hair_short"]},
}
ROLE_SET = {"civilian": "vigil_civilian", "official": "vigil_command", "flight": "vigil_flight",
            "security": "vigil_security", "dock": "vigil_dock"}
write_wardrobe(gfx, PFX, DRESS, ARTICLES, SETS, ROLE_SET)
w(f"{S}/graphics.json", gfx)

# ======================================================================
# 5. THE NAME-WALL floor plan + roster
# ======================================================================
# The Name-Wall's exterior (graphics/stations/vigil_station.json) is a tall
# narrow monolith, its face all ranked name-niches, three shallow docking
# notches down each side, a violet crown light - and it does not rotate. The
# floor plan is that standing stone stood on end: one long cold north-south
# nave (every other station in the story runs east-west - the Vigil's does
# not), the inner Vault at the crowned head, and three reading-niches off
# each side, matching the three notches. Austere, vertical, narrow light.
NW_ROOMS = [
    rect(660, 200, 940, 1200, "the Long Vigil"),        # the nave, north-south
    rect(580, 180, 1000, 380, "the inner Vault"),        # the crowned head
    rect(820, 320, 1120, 520, "the Long Vault"),         # E niche 1
    rect(820, 600, 1120, 800, "Reading Cells"),          # E niche 2
    rect(820, 880, 1120, 1080, "Vault of the First Decade"),  # E niche 3
    rect(480, 320, 780, 520, "Spare Stores"),            # W niche 1
    rect(480, 600, 780, 800, "the Refectory"),           # W niche 2
    rect(480, 880, 780, 1080, "the ferry cells"),        # W niche 3
]
NW_STRUCTURES = [
    {"x": 800, "y": 270, "building_type": "vigil_spire"},   # at the crowned head
    # the nave is kept deliberately bare - its bare vertical length is the point.
    # benches and stores live in the side niches.
    {"x": 540, "y": 760, "building_type": "pipeline_bench"},   # the Refectory
    {"x": 1060, "y": 650, "building_type": "pipeline_bench"},  # Reading Cells
    {"x": 540, "y": 380, "building_type": "crates"},           # Spare Stores
    {"x": 540, "y": 930, "building_type": "crates"},           # the ferry cells
]
NW_NPCS = [
    {"name": "Keeper Aramis", "x": 800, "y": 1000, "role": "concierge",
     "faction": "the_vigil", "outfit": "vigil_official_masc",
     "ambient": {"range": 720, "message": "You came to the Name-Wall. Few do, now. Walk over - there is something the Vigil records that you should carry with you."},
     "dialogue_tree": {"root": "start", "conditional_roots": [
         {"flag": "vigil_record_done", "node": "done"},
         {"flag": "vigil_record_accepted", "node": "midway"},
         {"faction": "the_vigil", "min": 25, "node": "warm"}],
      "nodes": {
        "start": {"text": "Everyone the first decades of the Silence killed is written on this wall. We stayed to keep it - and to keep the reason. We believe the Relay went dark on purpose, and that the signal now relighting it is finishing something that was meant to stay unfinished. Read the wall with me - three accounts - and then judge the Span for yourself. I will pass the signal to the core myself when you have.",
                  "options": [
                      {"label": "Show me the accounts.", "next": "accepted",
                       "actions": ["set_flag:vigil_record_accepted", "start_mission:the_vigil_record", "adjust_rep:the_vigil:4"]},
                      {"label": "The Authority sent me to reopen the beacons.", "next": "cold",
                       "requires_not_flag": "vigil_record_accepted", "action": "adjust_rep:the_vigil:-8"},
                      {"label": "Not now.", "next": None}]},
        "accepted": {"text": "Begin at the First Wall with Warden of Names Vane. Then the Reading Cells, then the inner Vault. Sister Edda will open it once you have read the first two.",
                     "options": [{"label": "I'll read", "next": None}]},
        "midway": {"text": "Keep reading. Vane at the First Wall, the Reading Cells, then the inner Vault. Your Mission Log holds the order.",
                   "options": [{"label": "Continue", "next": None},
                               {"label": "I've read enough.", "next": "declined", "action": "abandon_mission:the_vigil_record"}]},
        "declined": {"text": "Then you go to the Span less prepared than I would send you. The lane is keyed regardless - someone has to reach it. Choose as if the wall were watching.",
                     "options": [{"label": "Understood", "next": None, "action": "light_beacon:the_span"}]},
        "cold": {"text": "Of course they did. Read the wall anyway, if you ever change your mind. The dead do not take sides.",
                 "options": [{"label": "Leave", "next": None}]},
        "done": {"text": "You have read what we keep, and I passed the same warning to you by dispatch besides - the dead get no other voice, so we use every one we have. You know the Silence was a choice, roughly what it cost, and that the Vigil would neither make it again the same way nor unmake it carelessly. The Span's beacon is lit. Go and choose.",
                 "options": [{"label": "Understood", "next": None}]},
        "warm": {"text": "You carried the wall's account honestly. If the Hub asks what the dead would want, we would trust you to say it: understand a thing before you undo it.",
                 "options": [
                     {"label": "Pledge the Vigil your caution.", "next": "pledged",
                      "requires_not_flag": "patron:the_vigil",
                      "actions": ["set_exclusive_flag:patron:the_vigil", "adjust_rep:the_vigil:8"]},
                     {"label": "I'll think on it", "next": None}]},
        "pledged": {"text": "Then you speak for the dead at the Hub. Choose slowly.",
                    "options": [{"label": "I will", "next": None}]}}}},

    {"name": "Warden of Names Vane", "x": 1000, "y": 420, "role": "quartermaster",
     "faction": "the_vigil", "outfit": "vigil_official_femme",
     "dialogue_tree": {"root": "start", "conditional_roots": [{"flag": "vigil_read_first", "node": "read"}], "nodes": {
        "start": {"text": "The First Wall - the names of the first year. The accounts agree: the beacons did not fail. Every station logged the same order, the same hour - HOLD ALL TRAFFIC, NET DOWN BY INSTRUCTION. Someone sent that. Read it yourself.",
                  "options": [
                      {"label": "Read the First Wall.", "next": "ok", "requires_flag": "vigil_record_accepted",
                       "actions": ["set_flag:vigil_read_first"]},
                      {"label": "What can you spare to trade?", "action": "open_shop", "next": None}]},
        "ok": {"text": "Now the Reading Cells - the middle years, when they worked out why. Go to Brother Sol.",
               "options": [{"label": "Understood", "action": "open_shop", "next": None}]},
        "read": {"text": "You've read the First Wall. The Reading Cells next. I can spare archive copies if you'll carry them carefully.",
                 "options": [{"label": "Trade", "action": "open_shop", "next": None}, {"label": "Leave", "next": None}]}},
      }, "shop": {"type": "commodities", "stock": ["archive_copies", "relief_supplies"], "sell_multiplier": 1.0}},

    {"name": "Brother Sol", "x": 1000, "y": 700, "role": "clerk",
     "faction": "the_vigil", "outfit": "vigil_dock_masc",
     "dialogue_tree": {"root": "start", "conditional_roots": [{"flag": "vigil_read_second", "node": "read"}], "nodes": {
        "start": {"text": "The Reading Cells. The middle-year accounts don't agree on why - and that's the honest part. Some wrote it was a quarantine: something came through the Relay and the net was cut to trap it. Some wrote it was the last act of a war nobody won. One hand, near the end, wrote only: it broke, and we made the silence mean something. Read all three.",
                  "options": [
                      {"label": "Read the middle years.", "next": "ok", "requires_flag": "vigil_read_first",
                       "actions": ["set_flag:vigil_read_second"]},
                      {"label": "Later.", "next": None}]},
        "ok": {"text": "Now the inner Vault - the First Decade's own record, and the warning they left the Span. Sister Edda holds the door.",
               "options": [{"label": "Understood", "next": None}]},
        "read": {"text": "You've read the middle years. The inner Vault is the last of it - Sister Edda will open the door for you now.",
                 "options": [{"label": "Understood", "next": None}]}}}},

    {"name": "Sister Edda", "x": 720, "y": 300, "role": "magistrate",
     "faction": "the_vigil", "outfit": "vigil_official_femme",
     "dialogue_tree": {"root": "start", "conditional_roots": [{"flag": "vigil_read_vault", "node": "read"}], "nodes": {
        "start": {"text": "The Vault of the First Decade. Not for everyone - but you have read the wall, so. Inside is what the First Decade sent toward the core, in case the beacons ever woke: a warning, and an instruction. It says - whatever you find at the Span, the choice was left deliberately to whoever arrived last. That is you. Read it, and I will tell the Keeper you are ready.",
                  "options": [
                      {"label": "Enter the Vault.", "next": "ok", "requires_flag": "vigil_read_second",
                       "actions": ["set_flag:vigil_read_vault", "adjust_rep:the_vigil:5"]},
                      {"label": "I'm not ready.", "next": None}]},
        "ok": {"text": "Then you carry it. Go back to Keeper Aramis - he will light the lane to the Span, and you will go knowing what the wall knows.",
               "options": [{"label": "Understood", "next": None}]},
        "read": {"text": "You have read the Vault. The Keeper is expecting you.",
                 "options": [{"label": "Understood", "next": None}]}}}},

    {"name": "Deck-warden Oren", "x": 600, "y": 700, "role": "guard",
     "faction": "the_vigil", "outfit": "vigil_security_masc",
     "greeting": "The Vigil keeps a distance and asks the same of visitors. Stand off the graves and we will never speak again.",
     "dialogue_options": ["Understood", "Leave"]},

    {"name": "Quiet-warden Pell", "x": 1000, "y": 980, "role": "outfitter",
     "faction": "the_vigil", "outfit": "vigil_security_femme",
     "greeting": "We arm the grave-watch, nothing more. But a light-lance keeps a raider at a distance without a shot, and the Vigil approves of distance.",
     "shop": {"type": "outfits", "stock": ["laser_cannon", "pulse_blaster", "reinforced_hull", "afterburner", "cargo_expansion", "shield_capacitor", "sensor_array"]}},

    {"name": "Ferry-keeper Nis", "x": 600, "y": 980, "role": "ship_salesman",
     "faction": "the_vigil", "outfit": "vigil_official_masc",
     "greeting": "We keep a few stele hulls and one reliquary barge. Slow. Quiet. They carry what should be carried gently.",
     "shop": {"type": "ships", "stock": ["vigil_courier", "carrier_courier", "vigil_hauler"]}},

    {"name": "the Vigil-Master", "x": 800, "y": 620, "role": "resident",
     "faction": "the_vigil", "outfit": "vigil_official_femme",
     "greeting": "Three hundred of us keep this system. When the last of us is written on the wall, someone else will have to decide who keeps the wall. I hope the Relay does not answer that for us.",
     "dialogue_options": ["I understand", "Leave"]},

    {"name": "Sister of the Vigil", "x": 600, "y": 420, "role": "resident",
     "faction": "the_vigil", "outfit": "vigil_civilian_femme",
     "greeting": "It's quiet here. We prefer it. The quiet is the point - it's the shape the grief settled into.",
     "dialogue_options": ["I see", "Leave"]},

    {"name": "Authority envoy", "x": 800, "y": 1090, "role": "traveler",
     "faction": "harbor_authority", "outfit": "authority_official_femme",
     "requires_flag": "act_span",
     "greeting": "The Authority sent me to secure the archive before the Span decides anything. The Vigil won't speak to me. Perhaps they'll speak to you - tell them we only want it preserved.",
     "dialogue_options": ["I'll pass that on", "Leave"]},
]
NW_INTERIOR = {"label": "the Name-Wall", "culture": "the_vigil",
               "portals": [{"x": 800, "y": 1140, "connected_locations": [], "return_to_ship": True}],
               "rooms": NW_ROOMS, "structures": NW_STRUCTURES, "npcs": NW_NPCS,
               **station_shell(PFX, 204)}


def grave_moon():
    return {
        "name": "Vault of the First Decade", "x": 0.8, "y": 0.8, "size": 28, "color": [96, 96, 108],
        "crater_color": [70, 70, 82], "landing_distance": 34,
        "craters": [{"x": -7, "y": -4, "radius": 4}, {"x": 8, "y": 6, "radius": 4}, {"x": 1, "y": -9, "radius": 3}],
        "interiors": {"city": {
            "label": "the Grave-Yard", "culture": "the_vigil",
            "connected_locations": [], "entrance": {"x": 800, "y": 840},
            "rooms": [rect(200, 240, 1400, 1120, "the Grave-Yard")],
            "structures": [
                {"x": 800, "y": 520, "building_type": "vigil_hall"},
                {"x": 460, "y": 780, "building_type": "vigil_housing"},
                {"x": 1140, "y": 780, "building_type": "vigil_housing"},
                {"x": 800, "y": 320, "building_type": "vigil_spire"},
                {"x": 560, "y": 1000, "building_type": "pipeline_column"},
                {"x": 1040, "y": 1000, "building_type": "pipeline_column"},
                {"x": 320, "y": 1040, "building_type": "pipeline_bench"},
                {"x": 1280, "y": 1040, "building_type": "pipeline_bench"},
            ],
            "npcs": [
                {"name": "Grave-Keeper Toll", "x": 800, "y": 700, "role": "magistrate",
                 "faction": "the_vigil", "outfit": "vigil_official_masc",
                 "greeting": "The oldest graves are here, under the hall. If the Span's choice goes wrong, this is the moon that fills first. I would like you to have seen it before you decide.",
                 "dialogue_options": ["I have", "Leave"]},
                {"name": "Grave-tender Isa", "x": 560, "y": 620, "role": "dockworker",
                 "faction": "the_vigil", "outfit": "vigil_dock_femme",
                 "greeting": "I tend the First Decade's rows. Two centuries and we've never missed a name. Whatever the Relay brings back, we'll keep doing that.",
                 "dialogue_options": ["Understood", "Leave"]},
                {"name": "Novice Bre", "x": 1040, "y": 900, "role": "resident",
                 "faction": "the_vigil", "outfit": "vigil_civilian_masc",
                 "greeting": "I took a name to keep when I joined. Someone who died in the third year. I never met them. I think about them more than anyone I have met.",
                 "dialogue_options": ["I understand", "Leave"]},
            ],
        }},
    }


OSSUARY = {
    "name": "Ossuary",
    "description": "A dead system - one habitable moon, abandoned stations, and the Vigil: a monastic order of a few hundred who stayed to keep the graves and the archives of everyone the first decades of the Silence killed. They hold the truest history in the region.",
    "star_map_position": {"x": 40, "y": 260},
    "station_asset": "vigil_station", "moon_asset": "vigil_moon",
    "central_star": {"x": 0.5, "y": 0.5, "name": "Ossuary", "size": 70, "color": [206, 200, 226]},
    "player_start": {"x": 0.4, "y": 0.36}, "star_seed": 204,
    "asteroid_field": {"per_chunk_range": [1, 3], "types": [
        {"type": "gray_rock", "weight": 4, "size_range": [4, 22], "speed_range": [0.03, 0.2], "mine_yield": 10}]},
    "station": {"x": 0.2, "y": 0.24, "name": "the Name-Wall", "interiors": {"default": NW_INTERIOR}},
    "moon": grave_moon(),
    "celestial_bodies": [
        {"name": "the First Grave", "x": 0.62, "y": 0.5, "size": 16, "color": [120, 120, 134], "body_type": "rocky"},
        {"name": "Silent Verge", "x": 0.26, "y": 0.7, "size": 40, "color": [150, 145, 165], "body_type": "gas_giant",
         "has_ring": True, "ring_color": [130, 125, 150]}],
    "ai_ships": [
        {"name": "Grave-watch Vane", "x": 0.55, "y": 0.16, "ship_type": "vigil_patrol", "pilot": "vane_watch",
         "faction": "the_vigil", "route": ["station", "moon"]},
        {"name": "Reliquary Oskal", "x": 0.35, "y": 0.22, "ship_type": "vigil_hauler", "pilot": "oskal",
         "faction": "the_vigil", "route": ["moon", "station"]},
        {"name": "Stele Courier Aen", "x": 0.68, "y": 0.58, "ship_type": "vigil_courier", "pilot": "aen",
         "faction": "the_vigil", "route": ["station", "moon"]},
    ],
    "locked": True, "unlock_flag": "beacon_ossuary_lit",
}
w(f"{S}/systems/ossuary.json", OSSUARY)

# ======================================================================
# 6. ANCHOR MISSION  "the_vigil_record"  (the history + the warning; lights the Span)
# ======================================================================
KEEP = "Keeper Aramis"
RECORD = {
    "title": "Reading the Name-Wall",
    "on_end_flags": ["vigil_record_done", "beacon_the_span_lit", "act_span"],
    "on_start_rep": {"the_vigil": 2},
    "on_end_rep": {"the_vigil": 6},
    "stages": [
        {"text": "Read the First Wall with Warden of Names Vane - the Long Vault, first niche up the east wall of the nave.",
         "complete_flag": "vigil_read_first",
         "one_way_message": say(KEEP, "Warden of Names Vane keeps the First Wall in the Long Vault. The first year's names, and the order that started the Silence. Read it.")},
        {"text": "Read the middle years with Brother Sol - the Reading Cells, further up the east wall of the nave.",
         "complete_flag": "vigil_read_second",
         "one_way_message": say(KEEP, "Brother Sol has the middle-year accounts in the Reading Cells. Three explanations, none certain. Read all three - the uncertainty is the honest part.")},
        {"text": "Enter the Vault of the First Decade with Sister Edda, at the crowned head of the nave.",
         "complete_flag": "vigil_read_vault",
         "one_way_message": say(KEEP, "Sister Edda holds the inner Vault. What the First Decade sent toward the core, and why the last choice was left to whoever reached it. To you.")},
        {"text": "Return to Keeper Aramis.",
         "complete_flag": "vigil_record_reported",
         "one_way_message": say(KEEP, "Come back to me. I will light the lane to the Span, and you will carry the wall's account into whatever is waiting there.")},
    ],
}
missions = r(f"{S}/missions.json")
missions["the_vigil_record"] = RECORD
w(f"{S}/missions.json", missions)

sysj = r(f"{S}/systems/ossuary.json")
nw = sysj["station"]["interiors"]["default"]
for npc in nw["npcs"]:
    if npc["name"] == KEEP:
        npc["dialogue_tree"]["conditional_roots"].insert(1, {"flag": "vigil_read_vault", "node": "report"})
        npc["dialogue_tree"]["nodes"]["report"] = {
            "text": "You have read all three - the wall, the doubt, and the warning. Then I keep my word: the lane to the Span is lit. Go knowing that the Silence was a choice someone made carefully, and that unmaking it deserves the same care.",
            "options": [
                {"label": "Understood", "next": None, "requires_not_flag": "vigil_record_reported",
                 "actions": ["set_flag:vigil_record_reported"]}]}
w(f"{S}/systems/ossuary.json", sysj)

# ======================================================================
# 7. VIGIL PILOTS
# ======================================================================
pilots = r(f"{S}/pilots.json")
pilots.update({
    "vane_watch": {"name": "Warden Vane", "faction": "the_vigil", "role": "patrol_officer",
                   "personality": "Quiet to the point of severity; every word measured against the Name-Wall. Fires the lance only to hold a distance, never to close one.",
                   "hail_greeting": "The Vigil keeps this approach. State that you mean the graves no disrespect, and hold your distance."},
    "oskal": {"name": "Tender Oskal", "faction": "the_vigil", "role": "freighter_pilot",
              "personality": "Handles cargo the way others handle relics. Slow, deliberate, unhurried by anything.",
              "hail_greeting": "Reliquary transfer, moon to the Name-Wall. Fragile, and named. Keep well clear."},
    "aen": {"name": "Stele-pilot Aen", "faction": "the_vigil", "role": "courier_pilot",
            "personality": "Young for the Vigil; carries messages between the graves and the archive and says little else.",
            "hail_greeting": "Vigil courier. Archive traffic only. I'll pass you by."},
})
w(f"{S}/pilots.json", pilots)

print(f"Ossuary slice: 3 ships, 1 station, 3 buildings, dress + {len(ARTICLES)} articles / {len(SETS)} sets, "
      f"the Name-Wall ({len(NW_ROOMS)} rooms / {len(NW_NPCS)} NPCs), 'the_vigil_record' "
      f"({len(RECORD['stages'])} stages), {len(pilots)} pilots.")
