"""Phase 6.2 - the Kiln slice (Ninefold Combine), end to end.

Owns systems/kiln.json. Run after gen_halcyon (see docs/gen/README.md). Produces:
  graphics/ships/combine_{courier,hauler,patrol}.json   heavy ingot hulls
  graphics/stations/combine_station.json                the blast-hub "Combine Hold"
  graphics/buildings/combine_{hall,housing,spire}.json  low vaulted blast blocks
  graphics/palettes/combine_dress.json                  ember-on-iron work dress
  graphics/articles/combine_*.json + sets/combine_*.json  bespoke Combine wardrobe
  systems/kiln.json    real Combine Hold floor plan + roster + the anchor mission
  missions.json        += "combine_contract" (hostile-leaning; lights Verdance)
  pilots.json          += fleshed Combine pilots

Combine style (cultures.json): heavy dark iron banded with ember-orange hazard
light, blast doors, riveted seams, ration-stencil numerals, built for the deep
mines. Odd counts and ornament are waste - everything is blunt, paired, stencilled.
"""
from _slice_kit import (S, G, w, r, rect, concourse_plan, BAY_N, BAY_S, disc, octagon,  say, station_shell,
                        article, region, down_chevron, write_wardrobe,
                        numeral_plate_region, shoulder_slab_region, far_shoulder_slab_region,
                        bib_region, hip_seal_region, brassard_region, hood_region)

PFX = "combine"
DRESS = "combine_dress"


def rivets(group, ys, x0, x1, note):
    """A stencilled seam line as a thin recessed panel - Combine bulkhead seam."""
    return [{"group": group, "color": "engine", "shade": "matte", "role": "detail", "min_px": 40,
             "note": f"{note} seam {i}", "points": [[x0, y], [x1, y], [x1, y + 0.05], [x0, y + 0.05]]}
            for i, y in enumerate(ys)]


# ======================================================================
# 1. SHIP DESIGNS  (fractions of size; nose = -y; symmetric about x=0)
# ======================================================================
COMBINE_COURIER = {
    "identity": "Ninefold Combine Courier - a blunt iron ingot with a chopped prow, a single ranked hazard band each flank, two paired stub nacelles, an ember running light. No sweep, no taper the rules don't require. Reads at a dozen pixels as a short dark bar with two orange dots.",
    "tier": "ship_near", "palette": PFX, "size": 11,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "deep", "flatten_px": 40, "note": "ingot hull",
         "points": [[-0.30, -0.98], [0.30, -0.98], [0.40, -0.72], [0.40, 0.86],
                    [0.30, 1.04], [-0.30, 1.04], [-0.40, 0.86], [-0.40, -0.72]]},
        {"group": "canopy", "color": "glass", "shade": "sheen", "flatten_px": 55, "note": "armoured slit canopy",
         "points": [[-0.16, -0.66], [0.16, -0.66], [0.16, -0.34], [-0.16, -0.34]]},
        {"group": "nac_r", "color": "engine", "shade": "deep", "flatten_px": 45, "note": "right stub nacelle",
         "points": [[0.40, 0.42], [0.60, 0.42], [0.60, 1.02], [0.40, 1.02]]},
        {"group": "nac_l", "color": "engine", "shade": "deep", "flatten_px": 45, "note": "left stub nacelle",
         "points": [[-0.40, 0.42], [-0.60, 0.42], [-0.60, 1.02], [-0.40, 1.02]]},
    ],
    "details": [
        *rivets("hull", (-0.5, 0.0, 0.5), -0.30, 0.30, "hull"),
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 60,
         "note": "hazard band, right", "points": [[0.24, -0.5], [0.34, -0.5], [0.34, 0.5], [0.24, 0.5]]},
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 60,
         "note": "hazard band, left", "points": [[-0.24, -0.5], [-0.34, -0.5], [-0.34, 0.5], [-0.24, 0.5]]},
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 90,
         "note": "nav light, prow", "circle": [0.0, -0.9, 0.05]},
        {"group": "nac_r", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12,
         "note": "right thruster", "circle": [0.50, 1.02, 0.12]},
        {"group": "nac_l", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12,
         "note": "left thruster", "circle": [-0.50, 1.02, 0.12]},
    ],
}

COMBINE_HAULER = {
    "identity": "Ninefold Combine Hauler - a long ore ingot: a heavy slab split down the centreline by a blast seam, four ranked ore-cell hatches, a squat command box forward, a wide braced engine block aft on a paired thruster. Every hatch stencilled. Reads as a dark stack of numbered boxes.",
    "tier": "ship_near", "palette": PFX, "size": 20,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "deep", "flatten_px": 60, "note": "ore slab",
         "points": [[-0.40, -1.0], [0.40, -1.0], [0.46, -0.8], [0.46, 0.88],
                    [0.40, 1.06], [-0.40, 1.06], [-0.46, 0.88], [-0.46, -0.8]]},
        {"group": "cab", "color": "glass", "shade": "sheen", "flatten_px": 55, "note": "command box",
         "points": [[-0.22, -0.94], [0.22, -0.94], [0.22, -0.66], [-0.22, -0.66]]},
        {"group": "engine", "color": "engine", "shade": "deep", "flatten_px": 55, "note": "braced engine block",
         "points": [[-0.50, 0.8], [0.50, 0.8], [0.44, 1.18], [-0.44, 1.18]]},
    ],
    "details": [
        {"group": "hull", "color": "engine", "shade": "matte", "role": "detail", "min_px": 30,
         "note": "centreline blast seam", "points": [[-0.03, -0.8], [0.03, -0.8], [0.03, 0.78], [-0.03, 0.78]]},
        *[{"group": "hull", "color": "hull_dk", "shade": "matte", "role": "detail", "min_px": 40,
           "note": f"ore hatch {i}", "points": [[-0.36, y], [0.36, y], [0.36, y + 0.34], [-0.36, y + 0.34]]}
          for i, y in enumerate((-0.56, -0.14, 0.28))],
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 50,
         "note": "hazard stripe", "points": [[-0.42, -0.66], [0.42, -0.66], [0.42, -0.58], [-0.42, -0.58]]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 14,
         "note": "right thruster", "circle": [0.24, 1.16, 0.14]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 14,
         "note": "left thruster", "circle": [-0.24, 1.16, 0.14]},
    ],
}

COMBINE_PATROL = {
    "identity": "Ninefold Combine Patrol - a contract-enforcement ram: a heavy blunt wedge with a reinforced prow beam, thick side armour slabs, two short gun stubs flanking the nose, three ember thrusters across a braced tail. Built to board, not to chase. Reads as a dark hammerhead with an orange glare.",
    "tier": "ship_near", "palette": PFX, "size": 16,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "deep", "flatten_px": 45, "note": "ram wedge",
         "points": [[-0.24, -1.06], [0.24, -1.06], [0.5, -0.5], [0.7, 0.5], [0.7, 0.94],
                    [0.32, 1.1], [-0.32, 1.1], [-0.7, 0.94], [-0.7, 0.5], [-0.5, -0.5]]},
        {"group": "prow", "color": "metal", "shade": "metal", "flatten_px": 50, "note": "reinforced prow beam",
         "points": [[-0.24, -1.06], [0.24, -1.06], [0.24, -0.82], [-0.24, -0.82]]},
        {"group": "gun_r", "color": "engine", "shade": "deep", "flatten_px": 45, "note": "right gun stub",
         "points": [[0.24, -0.9], [0.4, -0.9], [0.4, -0.4], [0.24, -0.4]]},
        {"group": "gun_l", "color": "engine", "shade": "deep", "flatten_px": 45, "note": "left gun stub",
         "points": [[-0.24, -0.9], [-0.4, -0.9], [-0.4, -0.4], [-0.24, -0.4]]},
        {"group": "canopy", "color": "glass", "shade": "sheen", "flatten_px": 50, "note": "armoured canopy",
         "points": [[-0.16, -0.5], [0.16, -0.5], [0.16, -0.1], [-0.16, -0.1]]},
    ],
    "details": [
        {"group": "hull", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 45,
         "note": "prow hazard chevrons", "points": down_chevron(0.0, -0.72, 0.26, 0.16, 0.07)},
        {"group": "hull", "color": "hull_dk", "shade": "matte", "role": "detail", "min_px": 60,
         "note": "side armour slab R", "points": [[0.34, 0.1], [0.64, 0.3], [0.64, 0.8], [0.36, 0.66]]},
        {"group": "hull", "color": "hull_dk", "shade": "matte", "role": "detail", "min_px": 60,
         "note": "side armour slab L", "points": [[-0.34, 0.1], [-0.64, 0.3], [-0.64, 0.8], [-0.36, 0.66]]},
        {"group": "gun_r", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 18, "note": "muzzle R", "circle": [0.32, -0.88, 0.05]},
        {"group": "gun_l", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 18, "note": "muzzle L", "circle": [-0.32, -0.88, 0.05]},
        *[{"group": "hull", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12,
           "note": f"thruster {i}", "circle": [x, 1.08, 0.1]} for i, x in enumerate((-0.32, 0.0, 0.32))],
    ],
}

SHIP_DESIGNS = {
    "combine_courier": (COMBINE_COURIER, [[0.50, 1.02], [-0.50, 1.02]],
                        [[-0.40, -0.72], [0.40, -0.72], [0.40, 0.86], [0.60, 1.02], [-0.60, 1.02], [-0.40, 0.86]]),
    "combine_hauler": (COMBINE_HAULER, [[0.24, 1.1], [-0.24, 1.1]],
                       [[-0.46, -0.8], [0.46, -0.8], [0.46, 0.88], [0.44, 1.18], [-0.44, 1.18], [-0.46, 0.88]]),
    "combine_patrol": (COMBINE_PATROL, [[-0.32, 1.05], [0.0, 1.05], [0.32, 1.05]],
                       [[-0.24, -1.06], [0.24, -1.06], [0.7, 0.5], [0.32, 1.1], [-0.32, 1.1], [-0.7, 0.5]]),
}

for sid, (design, thr, local) in SHIP_DESIGNS.items():
    w(f"{G}/ships/{sid}.json", design)

gfx = r(f"{S}/graphics.json")
for sid, (design, thr, local) in SHIP_DESIGNS.items():
    e = gfx["ships"][sid]
    e["local_points"] = local
    e["thrusters"] = thr
    e["thruster_width"] = 0.07
    e["thruster_length"] = 18

# ======================================================================
# 2. STATION  "Combine Hold" - a blast-hub bolt-head
# ======================================================================
COMBINE_STATION = {
    "identity": "Combine Hold - the Ninefold Combine's orbital dock: a squat heavy octagonal drum with two opposed stub docking claws (not four arms - two is enough), a riveted hazard band around the waist, a single ember core port. Reads as a dark bolt-head with an orange centre.",
    "tier": "station", "palette": PFX, "size": 46,
    "units": "fractions of `size`; near-radially symmetric bar the two claws.",
    "silhouette": [
        {"group": "drum", "color": "hull", "shade": "deep", "flatten_px": 55, "note": "octagonal drum",
         "points": [[-0.42, -1.0], [0.42, -1.0], [1.0, -0.42], [1.0, 0.42], [0.42, 1.0],
                    [-0.42, 1.0], [-1.0, 0.42], [-1.0, -0.42]]},
        {"group": "core", "color": "glass", "shade": "flat", "flatten_px": 200, "note": "ember core port",
         "points": [[-0.2, -0.2], [0.2, -0.2], [0.2, 0.2], [-0.2, 0.2]]},
        {"group": "claw_e", "color": "hull_dk", "shade": "matte", "flatten_px": 60, "note": "east docking claw",
         "points": [[1.0, -0.3], [1.34, -0.3], [1.34, 0.3], [1.0, 0.3]]},
        {"group": "claw_w", "color": "hull_dk", "shade": "matte", "flatten_px": 60, "note": "west docking claw",
         "points": [[-1.0, -0.3], [-1.34, -0.3], [-1.34, 0.3], [-1.0, 0.3]]},
    ],
    "details": [
        {"group": "core", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 18, "note": "core glow", "circle": [0.0, 0.0, 0.24]},
        {"group": "drum", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 70,
         "note": "hazard waist band", "points": [[-0.96, -0.07], [0.96, -0.07], [0.96, 0.07], [-0.96, 0.07]]},
        *[{"group": "drum", "color": "engine", "shade": "matte", "role": "detail", "min_px": 50,
           "note": f"rivet seam {i}", "points": [[-0.5, y], [0.5, y], [0.5, y + 0.05], [-0.5, y + 0.05]]}
          for i, y in enumerate((-0.6, 0.55))],
        {"group": "claw_e", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 26, "note": "dock light E", "circle": [1.26, 0.0, 0.06]},
        {"group": "claw_w", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 26, "note": "dock light W", "circle": [-1.26, 0.0, 0.06]},
    ],
}
w(f"{G}/stations/combine_station.json", COMBINE_STATION)
gfx["space_stations"]["combine_station"]["local_points"] = [
    [-0.42 * 46, -1.0 * 46], [0.42 * 46, -1.0 * 46], [1.0 * 46, -0.42 * 46], [1.0 * 46, 0.42 * 46],
    [0.42 * 46, 1.0 * 46], [-0.42 * 46, 1.0 * 46], [-1.0 * 46, 0.42 * 46], [-1.0 * 46, -0.42 * 46]]

# ======================================================================
# 3. BUILDINGS  (elevation; feet at y=0, up -y, centreline x=0)
# ======================================================================
COMBINE_HALL = {
    "identity": "Combine Contract Hall, head-on: a low wide vaulted block of dark iron, a single heavy blast-door entry dead centre under an ember lintel, riveted horizontal seams across the whole face, a ration-stencil numeral panel each side of the door. Squat, symmetrical, unwelcoming.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~1.6x PLAYER_H to the parapet, ~3.8x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "matte", "note": "wall", "flatten_px": 60,
         "points": [[-60, 0], [60, 0], [60, -44], [-60, -44]]},
        {"group": "body", "color": "hull", "shade": "deep", "note": "parapet",
         "points": [[-60, -44], [60, -44], [60, -50], [-60, -50]]},
        {"group": "body", "color": "engine", "shade": "matte", "note": "blast-door entry",
         "points": [[-12, -32], [12, -32], [12, 0], [-12, 0]]},
    ],
    "details": [
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 16, "note": "ember lintel",
         "points": [[-16, -34], [16, -34], [16, -30], [-16, -30]]},
        *[{"group": "body", "color": "engine", "shade": "matte", "role": "detail", "min_px": 30,
           "note": f"rivet seam {i}", "points": [[-58, y], [58, y], [58, y + 1.5], [-58, y + 1.5]]}
          for i, y in enumerate((-12, -24, -36))],
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 14, "note": "ration numerals L",
         "points": [[-40, -26], [-24, -26], [-24, -10], [-40, -10]]},
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 14, "note": "ration numerals R",
         "points": [[24, -26], [40, -26], [40, -10], [24, -10]]},
    ],
}

COMBINE_HOUSING = {
    "identity": "Combine Housing, head-on: a dark iron residential slab, three decks of small deep-set square windows in a strict paired grid, a riveted parapet, one heavy centred entry with an ember deck-number panel above it. A place where air is metered.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~3x PLAYER_H tall, ~2x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "matte", "note": "wall", "flatten_px": 60,
         "points": [[-32, 0], [32, 0], [32, -92], [-32, -92]]},
        {"group": "body", "color": "hull", "shade": "deep", "note": "parapet",
         "points": [[-34, -92], [34, -92], [34, -98], [-34, -98]]},
        {"group": "body", "color": "engine", "shade": "matte", "note": "entry",
         "points": [[-8, -16], [8, -16], [8, 0], [-8, 0]]},
    ],
    "details": [
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 12, "note": "deck-number panel",
         "points": [[-8, -24], [8, -24], [8, -18], [-8, -18]]},
        *[{"group": "body", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 10, "note": f"win r{ri} c{ci}",
           "points": [[cx - 5, cy], [cx + 5, cy], [cx + 5, cy + 9], [cx - 5, cy + 9]]}
          for ri, cy in enumerate((-84, -62, -40))
          for ci, cx in enumerate((-20, -8, 8, 20))],
        *[{"group": "body", "color": "engine", "shade": "matte", "role": "detail", "min_px": 24,
           "note": f"rivet seam {i}", "points": [[-30, y], [30, y], [30, y + 1.4], [-30, y + 1.4]]}
          for i, y in enumerate((-30, -52, -74))],
    ],
}

COMBINE_SPIRE = {
    "identity": "Combine Deep-Warden's tower, head-on: a squat heavy two-tier block of dark iron - whose contract this is. A broad base, a stepped upper stage, a hazard beacon on a stub mast, a lit contract-seal disc blazoned on the upper face. Not tall - immovable.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~3.4x PLAYER_H tall, ~1.8x wide at the base",
    "silhouette": [
        {"group": "body", "color": "hull", "shade": "deep", "note": "base stage", "flatten_px": 55,
         "points": [[-28, 0], [28, 0], [28, -62], [-28, -62]]},
        {"group": "body", "color": "hull", "shade": "deep", "note": "upper stage",
         "points": [[-20, -62], [20, -62], [20, -104], [-20, -104]]},
        {"group": "mast", "color": "metal", "shade": "metal", "note": "stub mast",
         "points": [[-2.5, -104], [2.5, -104], [2.5, -120], [-2.5, -120]]},
    ],
    "details": [
        {"group": "mast", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 20, "note": "hazard beacon", "circle": [0, -120, 4]},
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 16, "note": "contract-seal disc",
         "points": [[-9, -92], [9, -92], [9, -74], [-9, -74]]},
        *[{"group": "body", "color": "glass", "shade": "sheen", "role": "detail", "min_px": 12, "note": f"slit {i}",
           "points": [[x - 3, -52], [x + 3, -52], [x + 3, -14], [x - 3, -14]]} for i, x in enumerate((-16, 16))],
        *[{"group": "body", "color": "engine", "shade": "matte", "role": "detail", "min_px": 24,
           "note": f"base rivet seam {i}", "points": [[-26, y], [26, y], [26, y + 1.6], [-26, y + 1.6]]}
          for i, y in enumerate((-20, -44))],
    ],
}

BUILDINGS = {
    "combine_hall": (COMBINE_HALL, {"width": 120, "depth": 30.0}),
    "combine_housing": (COMBINE_HOUSING, {"width": 68, "depth": 22.0}),
    "combine_spire": (COMBINE_SPIRE, {"width": 56, "depth": 20.0}),
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
dress["identity"] = "Ninefold Combine dress - dark iron-grey work cloth banded with ember hazard-orange, heavy leather, stencil-white numerals. Human skin/hair unchanged."
dress.update({"cloth": "#3a3430", "denim": "#2a2523", "knit": "#4a4038", "leather": "#3c332c",
              "metal": "#8a8078", "glass": "#ff8c3c", "lamp": "#ff9a44"})
w(f"{G}/palettes/{DRESS}.json", dress)

ARTICLES = {
    "combine_ration_plate": article(
        "Combine ration plate - a stencil-numeral iron plate on the chest recording the wearer's metered share. Every Combine kit carries one.",
        DRESS, [numeral_plate_region("metal", "metal", "ration plate")]),
    "combine_blast_pauldrons": article(
        "Combine blast pauldrons - a pair of heavy squared iron shoulder slabs, hazard-edged. Worn by wardens of contract and deep crews alike.",
        DRESS, [shoulder_slab_region("metal", "metal", "pauldron"),
                far_shoulder_slab_region("metal", "metal", "pauldron")]),
    "combine_hazard_bib": article(
        "Combine hazard bib - a stiff ember-orange chest bib with two reflective bars, worn over the work suit in the shafts.",
        DRESS, [region("torso", "work vest", "hazard bib", "lamp", "glow",
                       [[-3.1, -25.0], [3.1, -25.0], [3.1, -20.0], [-3.1, -20.0]],
                       [[-2.7, -25.1], [2.7, -25.1], [2.5, -20.4], [-2.5, -20.4]],
                       m_det=[{"group": "torso", "color": "metal", "shade": "metal", "note": "bib bar high",
                               "points": [[-2.9, -23.6], [2.9, -23.6], [2.9, -23.0], [-2.9, -23.0]]},
                              {"group": "torso", "color": "metal", "shade": "metal", "note": "bib bar low",
                               "points": [[-2.7, -21.4], [2.7, -21.4], [2.7, -20.8], [-2.7, -20.8]]}],
                       f_det=[{"group": "torso", "color": "metal", "shade": "metal", "note": "bib bar high",
                               "points": [[-2.5, -23.8], [2.5, -23.8], [2.5, -23.2], [-2.5, -23.2]]},
                              {"group": "torso", "color": "metal", "shade": "metal", "note": "bib bar low",
                               "points": [[-2.4, -21.6], [2.4, -21.6], [2.4, -21.0], [-2.4, -21.0]]}])]),
    "combine_contract_seal": article(
        "Combine contract seal - a heavy wax-and-iron disc worn at the near hip on a short chain, stamped with the wearer's lineage. Breaking it voids a contract.",
        DRESS, [hip_seal_region("leather", "deep", "contract seal")]),
    "combine_deep_hood": article(
        "Combine deep hood - a close iron-grey hood with an ember lamp at the brow, worn below-ground. Drops any hairstyle.",
        DRESS, [hood_region("cloth", "matte", "deep hood")]),
}
ARTICLES["combine_deep_hood"]["hides_hair"] = True

SETS = {
    "combine_command": {"identity": "Ninefold Combine command turn-out - dark iron tunic and trousers, blast pauldrons, the ration plate, a contract seal at the hip, near-black boots.",
                        "articles": ["tank_top", "coat_charcoal", "pants_charcoal", "boots_black",
                                     "combine_blast_pauldrons", "combine_ration_plate", "combine_contract_seal", "hair_short"]},
    "combine_security": {"identity": "Warden of Contract kit - heavy work suit, blast pauldrons, a sealed helmet, the ration plate, a hazard brassard.",
                         "articles": ["tank_top", "jacket_secblue", "pants_secblue", "boots_black", "helmet_sec",
                                      "combine_blast_pauldrons", "combine_ration_plate", "combine_contract_seal"]},
    "combine_dock": {"identity": "Combine rockjack kit - iron work suit under the hazard bib, deep hood, heavy gloves, the ration plate.",
                     "articles": ["tank_top", "jacket_dock", "pants_dock", "boots_charcoal", "gloves_dark",
                                  "combine_hazard_bib", "combine_deep_hood", "combine_ration_plate"]},
    "combine_flight": {"identity": "Combine hauler-pilot kit - work suit, flight helmet, the ration plate, a contract seal.",
                       "articles": ["tank_top", "jacket_olive", "pants_field", "boots_charcoal", "helmet_flight",
                                    "combine_ration_plate", "combine_contract_seal", "hair_short"]},
    "combine_civilian": {"identity": "Combine indentured dress - plain dark clothes, a soft collar, the ration plate every citizen wears, a contract seal.",
                         "articles": ["tank_top", "jacket_civ", "pants", "shoes", "collar",
                                      "combine_ration_plate", "combine_contract_seal", "hair_long"]},
}
ROLE_SET = {"civilian": "combine_civilian", "official": "combine_command", "flight": "combine_flight",
            "security": "combine_security", "dock": "combine_dock"}
write_wardrobe(gfx, PFX, DRESS, ARTICLES, SETS, ROLE_SET)
w(f"{S}/graphics.json", gfx)

# ======================================================================
# 5. COMBINE HOLD floor plan + roster
# ======================================================================
# Combine Hold's exterior (graphics/stations/combine_station.json) is a squat
# octagonal drum with exactly two opposed stub docking claws - "two is
# enough", odd counts are waste. The floor plan is that drum: one heavy
# eight-sided vault with the ember core spire at its heart, a blast-door
# claw east (the Ledger Dock, ship portal) and west (the Ration Store), and
# Cutters' Rest tacked onto the ration side. Low, dark, riveted.
HOLD_ROOMS = [
    octagon(800, 690, 340, 0.42, "The Hold"),          # the drum
    rect(1060, 590, 1440, 790, "The Ledger Dock"),      # east claw  (ship dealer + outfitter + portal)
    rect(160, 590, 540, 820, "Ration Store"),           # west claw  (rationed trade)
    rect(160, 720, 420, 1000, "Cutters' Rest"),         # off the ration side  (bar)
]

_RING = [  # eight vault columns ringing the ember spire, 45 deg apart at r=190
    (990, 690), (934, 824), (800, 880), (666, 824),
    (610, 690), (666, 556), (800, 500), (934, 556)]
HOLD_STRUCTURES = [
    {"x": 800, "y": 690, "building_type": "combine_spire"},
    *[{"x": x, "y": y, "building_type": "pipeline_column"} for x, y in _RING],
    {"x": 260, "y": 640, "building_type": "crates"},    # Ration Store
    {"x": 260, "y": 760, "building_type": "crates"},
    {"x": 300, "y": 920, "building_type": "crates"},    # Cutters' Rest
    {"x": 1180, "y": 760, "building_type": "pipeline_bench"},   # Ledger Dock
]

HOLD_NPCS = [
    {"name": "Factor Tol", "x": 800, "y": 450, "role": "stationmaster",
     "faction": "ninefold_combine", "outfit": "combine_official_masc",
     "ambient": {"range": 620, "message": "New hull on Combine ground. Nothing moves here without a contract - come to me before you trade a bolt."},
     "dialogue_tree": {"root": "start", "conditional_roots": [
         {"flag": "combine_contract_done", "node": "done"},
         {"flag": "combine_contract_accepted", "node": "midway"},
         {"faction": "ninefold_combine", "min": 25, "node": "warm"}],
      "nodes": {
        "start": {"text": "You're on Combine ground, and the Combine did not sign a contract with a beacon. But a hull that will carry a sealed manifest to Shaft VII and back has proven it can follow terms - and the Combine will key Verdance's lane for a partner, not a tourist. Or you can leave now.",
                  "options": [
                      {"label": "I'll sign. Give me the terms.", "next": "signed",
                       "actions": ["set_flag:combine_contract_accepted", "start_mission:combine_contract"]},
                      {"label": "The Authority opens this system with or without you.", "next": "threatened",
                       "actions": ["adjust_rep:ninefold_combine:-45"]},
                      {"label": "Just leave.", "next": None}]},
        "signed": {"text": "Terms: the manifest is sealed, you do not open it, you do not deviate. Tallykeeper Vess holds it - the Assay Office, north. The Warden of Contract witnesses your mark first.",
                   "options": [{"label": "Understood", "next": None}]},
        "midway": {"text": "The contract is open. Check your Mission Log. Break the seal or the route and it voids - and so does your welcome.",
                   "options": [{"label": "Keep going", "next": None},
                               {"label": "I'm done with this.", "next": "abandoned", "action": "abandon_mission:combine_contract"}]},
        "abandoned": {"text": "Void, then. Clear our space before the Warden logs it.",
                      "options": [{"label": "Leave", "next": None}]},
        "threatened": {"text": "Then the contract is void before it is written, and so is your safe conduct. The Combine has already voted on hulls that will not leave. Clear our space.",
                       "options": [{"label": "Leave", "next": None}]},
        "done": {"text": "The manifest is logged and the seal intact. Verdance's lane is keyed - the Combine will remember you kept terms. It will also remember that you now know the way to our door.",
                 "options": [{"label": "Understood", "next": None}]},
        "warm": {"text": "You've kept every term the Combine set you. When the Span asks its question, a voice that honours a contract is one the Combine would stand behind.",
                 "options": [
                     {"label": "Pledge the Combine your word.", "next": "pledged",
                      "requires_not_flag": "patron:ninefold_combine",
                      "actions": ["set_exclusive_flag:patron:ninefold_combine", "adjust_rep:ninefold_combine:8"]},
                     {"label": "I'll consider it", "next": None}]},
        "pledged": {"text": "Sealed. You answer for the Combine at the Span - and the Combine wants the beacons dark.",
                    "options": [{"label": "Understood", "next": None}]}}}},

    {"name": "Warden of Contract Raik", "x": 620, "y": 500, "role": "guard",
     "faction": "ninefold_combine", "outfit": "combine_security_masc",
     "dialogue_tree": {"root": "start", "conditional_roots": [{"flag": "combine_witnessed", "node": "witnessed"}], "nodes": {
        "start": {"text": "I witness marks and I enforce them. You're signing the Shaft VII carriage? Put your hand on the seal-stone and I'll log it.",
                  "options": [
                      {"label": "Witness my mark.", "next": "ok", "requires_flag": "combine_contract_accepted",
                       "actions": ["set_flag:combine_witnessed"]},
                      {"label": "Not yet.", "next": None}]},
        "ok": {"text": "Logged. Vess has the manifest. Break the seal and the next Combine hull you meet is a patrol, not a greeting.",
               "options": [{"label": "Understood", "next": None}]},
        "witnessed": {"text": "Your mark's logged. Keep the seal whole.",
                      "options": [{"label": "Understood", "next": None}]}}}},

    {"name": "Tallykeeper Vess", "x": 980, "y": 500, "role": "quartermaster",
     "faction": "ninefold_combine", "outfit": "combine_dock_masc",
     "dialogue_tree": {"root": "start", "conditional_roots": [
         {"flag": "combine_manifest_taken", "node": "taken"}], "nodes": {
        "start": {"text": "Sealed manifest for Shaft VII. Witnessed? Then it's yours to carry - and only to carry.",
                  "options": [
                      {"label": "Take the sealed manifest.", "next": "handed", "requires_flag": "combine_witnessed",
                       "actions": ["set_flag:combine_manifest_taken"]},
                      {"label": "Come back for it.", "next": None},
                      {"label": "Trade for supplies.", "action": "open_shop", "next": None}]},
        "handed": {"text": "Logged out. Shaft VII, hand it to Deepmaster Orin, bring back his tally. Don't open it.",
                   "options": [{"label": "Understood", "next": None}]},
        "taken": {"text": "You're carrying Combine cargo. Shaft VII. Orin. His tally comes back to me.",
                  "options": [{"label": "Understood", "next": None},
                              {"label": "Trade for supplies.", "action": "open_shop", "next": None}]}},
      }, "shop": {"type": "commodities", "stock": ["alloy", "ore"], "sell_multiplier": 1.15}},

    {"name": "Deck-chief Marn", "x": 1180, "y": 660, "role": "ship_salesman",
     "faction": "ninefold_combine", "outfit": "combine_official_femme",
     "greeting": "Combine hulls. Built heavy, priced by the contract, and they come back from the deep. What's your trade need?",
     "shop": {"type": "ships", "stock": ["combine_hauler", "combine_courier", "combine_patrol", "carrier_hauler"]}},

    {"name": "Assay-clerk Dorn", "x": 1000, "y": 690, "role": "clerk",
     "faction": "ninefold_combine", "outfit": "combine_dock_femme",
     "greeting": "Every gram in, every gram out, weighed twice. The Combine survived two centuries on that habit. We're not about to stop for a beacon.",
     "dialogue_options": ["Fair enough", "Leave"]},

    {"name": "Approach-Warden Sesk", "x": 1320, "y": 660, "role": "outfitter",
     "faction": "ninefold_combine", "outfit": "combine_security_femme",
     "greeting": "Combine-issue only, and rationed. Everything's rated for the shafts - it'll take worse than you can give it.",
     "shop": {"type": "outfits", "stock": ["pulse_blaster", "laser_cannon", "reinforced_hull", "cargo_expansion", "afterburner", "shield_capacitor", "sensor_array"]}},

    {"name": "Cutter Sol", "x": 280, "y": 890, "role": "bartender",
     "faction": "ninefold_combine", "outfit": "combine_civilian_masc",
     "dialogue_tree": {"root": "start", "nodes": {
        "start": {"text": "Cutters' Rest. Ration ale, one measure. What do you want?",
                  "options": [{"label": "A measure", "next": "drink"},
                              {"label": "What are people saying?", "next": "gossip"},
                              {"label": "Leave", "next": None}]},
        "drink": {"text": "One measure. Make it last - there isn't a second one coming.",
                  "options": [{"label": "Thanks", "next": "start"}]},
        "gossip": {"text": "The Factors held a closed vote last week. Nobody'll say on what. But the patrol crews are drilling boarding actions, and the assayers are counting hull-plate like we're going to need it.",
                   "options": [{"label": "Noted", "next": None}]}}}},

    {"name": "Deep-hand Corr", "x": 320, "y": 680, "role": "resident",
     "faction": "ninefold_combine", "outfit": "combine_civilian_femme",
     "greeting": "Air's metered by the shift down here. You get used to counting breaths. A beacon doesn't change what a lungful costs.",
     "dialogue_options": ["I see", "Leave"]},

    {"name": "Rockjack Bsix", "x": 660, "y": 880, "role": "dockworker",
     "faction": "ninefold_combine", "outfit": "combine_dock_masc",
     "ambient": {"range": 360, "message": "Mind the claw arm - it swings on the ember light, not before it."},
     "greeting": "Thirty years cutting the Ninefold Deep. The Combine fed me every one of them. I know what I owe.",
     "dialogue_options": ["Understood", "Leave"]},

    {"name": "Stranded carrier", "x": 430, "y": 730, "role": "traveler",
     "faction": "free_carrier", "outfit": "carrier_civilian_femme",
     "requires_flag": "beacon_ossuary_lit",
     "greeting": "Combine impounded my hold for an unpaid approach fee I didn't know I owed. Two centuries they set their own rules. Now the beacon's back and they still do.",
     "dialogue_options": ["Rough", "Leave"]},
]

HOLD_INTERIOR = {"label": "Combine Hold", "culture": "ninefold_combine",
                 "portals": [{"x": 1380, "y": 690, "connected_locations": [], "return_to_ship": True}],
                 "rooms": HOLD_ROOMS, "structures": HOLD_STRUCTURES, "npcs": HOLD_NPCS,
                 **station_shell(PFX, 202)}


def shaft_moon():
    return {
        "name": "Shaft VII", "x": 0.82, "y": 0.78, "size": 30, "color": [120, 108, 100],
        "crater_color": [90, 78, 70], "landing_distance": 35,
        "craters": [{"x": -8, "y": -4, "radius": 5}, {"x": 9, "y": 7, "radius": 4}, {"x": 2, "y": -9, "radius": 3}],
        "interiors": {"city": {
            "label": "Shaft VII Headworks", "culture": "ninefold_combine",
            "connected_locations": [], "entrance": {"x": 800, "y": 840},
            "rooms": [rect(160, 220, 1440, 1140, "Headworks Floor")],
            "structures": [
                {"x": 800, "y": 520, "building_type": "combine_hall"},
                {"x": 430, "y": 780, "building_type": "combine_housing"},
                {"x": 1170, "y": 780, "building_type": "combine_housing"},
                {"x": 800, "y": 330, "building_type": "combine_spire"},
                {"x": 560, "y": 1000, "building_type": "crates"},
                {"x": 1040, "y": 1000, "building_type": "crates"},
                {"x": 320, "y": 1060, "building_type": "pipeline_bench"},
                {"x": 1300, "y": 1060, "building_type": "pipeline_bench"},
                *[{"x": x, "y": 640, "building_type": "pipeline_column"} for x in (520, 1080)],
            ],
            "npcs": [
                {"name": "Deepmaster Orin", "x": 800, "y": 700, "role": "magistrate",
                 "faction": "ninefold_combine", "outfit": "combine_official_masc",
                 "dialogue_tree": {"root": "start", "conditional_roots": [
                     {"flag": "combine_tally_returned", "node": "returned"}], "nodes": {
                    "start": {"text": "Shaft VII. You're the carrier with Vess's manifest. Hand it here - sealed.",
                              "options": [
                                  {"label": "Deliver the sealed manifest.", "next": "ok", "requires_flag": "combine_manifest_taken",
                                   "actions": ["set_flag:combine_tally_returned", "adjust_rep:ninefold_combine:6"]},
                                  {"label": "Not yet.", "next": None}]},
                    "ok": {"text": "Seal's whole. Good. Here's my tally - back to Vess, and tell the Factor the Deep held its terms. It always does.",
                           "options": [{"label": "Understood", "next": None}]},
                    "returned": {"text": "You've your tally. The Hold's expecting it. Don't linger down here - the air's counted.",
                                 "options": [{"label": "Understood", "next": None}]}}}},
                {"name": "Shift-warden Palo", "x": 560, "y": 620, "role": "guard",
                 "faction": "ninefold_combine", "outfit": "combine_security_masc",
                 "greeting": "Every hull that lands here is logged against a contract. Yours checks out. Keep it that way.",
                 "dialogue_options": ["Understood", "Leave"]},
                {"name": "Cutter Rell", "x": 1080, "y": 900, "role": "resident",
                 "faction": "ninefold_combine", "outfit": "combine_civilian_femme",
                 "greeting": "Born in this shaft. I'll die in it. The Relay coming back just means more people to ration the same air.",
                 "dialogue_options": ["I see", "Leave"]},
            ],
        }},
    }


KILN = {
    "name": "Kiln",
    "description": "A red-dwarf system - one scorched inner world, deep-mine settlements under the moons. The Ninefold Combine rations everything, enforces it without mercy, and does not want the Relay back.",
    "star_map_position": {"x": 260, "y": -40},
    "station_asset": "combine_station", "moon_asset": "combine_moon",
    "central_star": {"x": 0.5, "y": 0.5, "name": "Kiln", "size": 84, "color": [255, 140, 96]},
    "player_start": {"x": 0.4, "y": 0.32}, "star_seed": 202,
    "asteroid_field": {"per_chunk_range": [2, 4], "types": [
        {"type": "gray_rock", "weight": 3, "size_range": [4, 20], "speed_range": [0.05, 0.3], "mine_yield": 12},
        {"type": "brown_rock", "weight": 2, "size_range": [8, 28], "speed_range": [0.04, 0.22], "mine_yield": 18}]},
    "station": {"x": 0.18, "y": 0.22, "name": "Combine Hold", "interiors": {"default": HOLD_INTERIOR}},
    "moon": shaft_moon(),
    "celestial_bodies": [
        {"name": "Kiln b", "x": 0.62, "y": 0.52, "size": 20, "color": [150, 96, 74], "body_type": "rocky"},
        {"name": "Cinder", "x": 0.3, "y": 0.72, "size": 12, "color": [120, 92, 84], "body_type": "rocky"}],
    "ai_ships": [
        {"name": "Combine Watch Tolvic", "x": 0.55, "y": 0.14, "ship_type": "combine_patrol", "pilot": "tolvic",
         "faction": "ninefold_combine", "route": ["station", "moon"]},
        {"name": "Boarding Cutter Raska", "x": 0.7, "y": 0.4, "ship_type": "combine_patrol", "pilot": "raska",
         "faction": "ninefold_combine", "route": ["station", "moon"]},
        {"name": "Ore Run Corran", "x": 0.35, "y": 0.2, "ship_type": "combine_hauler", "pilot": "corran",
         "faction": "ninefold_combine", "route": ["moon", "station"]},
        {"name": "Deep Freight Molt", "x": 0.66, "y": 0.66, "ship_type": "combine_hauler", "pilot": "molt",
         "faction": "ninefold_combine", "route": ["station", "moon"]},
    ],
    "locked": True, "unlock_flag": "beacon_kiln_lit",
}
w(f"{S}/systems/kiln.json", KILN)

# ======================================================================
# 6. ANCHOR MISSION  "combine_contract"  (hostile-leaning; lights Verdance)
# ======================================================================
FAC = "Factor Tol"
CONTRACT = {
    "title": "A Combine Carriage",
    "on_end_flags": ["combine_contract_done", "beacon_verdance_lit"],
    "on_start_rep": {"ninefold_combine": 2},
    "on_end_rep": {"ninefold_combine": 4},
    "stages": [
        {"text": "Have your mark witnessed - Warden of Contract Raik, the Contract Hall (north-west).",
         "complete_flag": "combine_witnessed",
         "one_way_message": say(FAC, "The Warden of Contract witnesses first. Contract Hall, north-west corner of the concourse. Put your hand on the seal-stone.")},
        {"text": "Collect the sealed manifest from Tallykeeper Vess, the Assay Office (north).",
         "complete_flag": "combine_manifest_taken",
         "one_way_message": say(FAC, "Vess has the manifest in the Assay Office. Sealed. You carry it - you do not open it.")},
        {"text": "Fly to the moon Shaft VII and land at its headworks.",
         "complete_flag": "landed_on_landing_site", "reset_on_activation": True,
         "one_way_message": say(FAC, "Shaft VII is the near moon. Fly clear of the Hold, match the moon, and set down at the headworks pad.")},
        {"text": "Deliver the manifest to Deepmaster Orin and take his tally.",
         "complete_flag": "combine_tally_returned",
         "one_way_message": say(FAC, "Deepmaster Orin runs the headworks. Hand him the manifest - sealed - and bring back his tally.")},
        {"text": "Carry the tally back to Tallykeeper Vess at the Combine Hold.",
         "complete_flag": "combine_tally_filed",
         "one_way_message": say(FAC, "Back to Vess with Orin's tally. Then the carriage is closed and the Factor will key Verdance's lane.")},
        {"text": "Report to Factor Tol.",
         "complete_flag": "combine_contract_reported",
         "one_way_message": say(FAC, "Come and tell me it's done. The Combine keys Verdance's beacon for a partner who kept terms - and remembers you now know our door.")},
    ],
}
missions = r(f"{S}/missions.json")
missions["combine_contract"] = CONTRACT
w(f"{S}/missions.json", missions)

# Vess needs a "file the tally" branch + Factor a "report" branch; both are
# small conditional additions to their trees, wired via extra flags above.
# (Vess: filing branch; Factor: the "done" node already sets nothing - add report.)
sysj = r(f"{S}/systems/kiln.json")
hold = sysj["station"]["interiors"]["default"]
for npc in hold["npcs"]:
    if npc["name"] == "Tallykeeper Vess":
        npc["dialogue_tree"]["conditional_roots"].insert(0, {"flag": "combine_tally_returned", "node": "filing"})
        npc["dialogue_tree"]["nodes"]["filing"] = {
            "text": "Orin's tally. Give it here - I'll file it against the carriage.",
            "options": [
                {"label": "File the tally.", "next": "filed", "requires_not_flag": "combine_tally_filed",
                 "actions": ["set_flag:combine_tally_filed"]},
                {"label": "In a moment.", "next": None}]}
        npc["dialogue_tree"]["nodes"]["filed"] = {
            "text": "Filed. Tell the Factor the carriage is closed.",
            "options": [{"label": "Understood", "next": None},
                        {"label": "Trade for supplies.", "action": "open_shop", "next": None}]}
    if npc["name"] == "Factor Tol":
        npc["dialogue_tree"]["conditional_roots"].insert(0, {"flag": "combine_tally_filed", "node": "report"})
        npc["dialogue_tree"]["nodes"]["report"] = {
            "text": "The carriage is closed and the seal was never touched. Verdance's lane is yours - the Combine keeps its word, and expects the same from a partner it now knows how to find.",
            "options": [
                {"label": "Understood", "next": None, "requires_not_flag": "combine_contract_reported",
                 "actions": ["set_flag:combine_contract_reported"]}]}
w(f"{S}/systems/kiln.json", sysj)

# ======================================================================
# 7. COMBINE PILOTS
# ======================================================================
pilots = r(f"{S}/pilots.json")
pilots.update({
    "tolvic": {"name": "Watch-Chief Tolvic", "faction": "ninefold_combine", "role": "patrol_officer",
               "personality": "Speaks only in what the contract permits, and it permits very little. Not cruel - correct.",
               "hail_greeting": "Combine watch. You are logged against a carriage contract. Hold a docking approach and do not deviate."},
    "raska": {"name": "Gun-bosun Raska", "faction": "ninefold_combine", "role": "patrol_officer",
              "personality": "Treats every contract breach as a personal insult and every insult as a firing solution.",
              "hail_greeting": "Boarding cutter. The Combine's writ runs here. Give me a reason - I keep a list."},
    "corran": {"name": "Hauler Corran", "faction": "ninefold_combine", "role": "freighter_pilot",
               "personality": "Counts every crate twice, trusts nothing that wasn't mined here, resents the beacon on principle.",
               "hail_greeting": "Ore run, Shaft VII to the Hold. Rationed cargo, sealed and tallied. Move along."},
    "molt": {"name": "Deep Freight Molt", "faction": "ninefold_combine", "role": "freighter_pilot",
             "personality": "Thirty years on the same loop; would keep flying it if the Relay swallowed every other lane whole.",
             "hail_greeting": "Combine deep freight. My route hasn't changed in three decades and it isn't changing for you."},
})
w(f"{S}/pilots.json", pilots)

print(f"Kiln slice: 3 ships, 1 station, 3 buildings, dress + {len(ARTICLES)} articles / {len(SETS)} sets, "
      f"Combine Hold ({len(HOLD_ROOMS)} rooms / {len(HOLD_NPCS)} NPCs), 'combine_contract' "
      f"({len(CONTRACT['stages'])} stages), {len(pilots)} pilots.")
