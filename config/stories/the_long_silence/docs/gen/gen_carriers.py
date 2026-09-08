"""Phase 6.6 - the free-carriers pass. Runs LAST (after every system slice).

Carriers are a faction, not a system - their pilots appear across all five
systems. This slice:
  - authors the three patchwork carrier ship designs (carrier_{courier,hauler,patrol})
  - authors a light patched-depot look for carrier_{hall,housing,spire}
  - authors the bespoke carrier wardrobe (5 articles + 5 sets)
  - drops a free_carrier AI ship + a carrier berth NPC + berth dressing into
    every system's station interior (idempotent - keyed by name)
  - fleshes the carrier pilot roster

Carrier style (cultures.json): patchwork - mismatched hull segments from six
cultures welded into one working whole, cargo lashing everywhere, a hand-painted
name. No unified livery; that is the livery.
"""
from _slice_kit import (S, G, w, r, rect, say, article, region, write_wardrobe,
                        brassard_region, apron_region, pendant_region)

PFX = "carrier"
DRESS = "carrier_dress"

# one borrowed metal per other culture (cultures.json metal_color), for the welds
BORROW = ["#96a5b9", "#706660", "#7a986f", "#5c5c6a", "#a28e5c"]


def patch(group, spots):
    return [{"group": group, "color": BORROW[i % len(BORROW)], "shade": "matte", "role": "detail", "min_px": 35,
             "note": f"welded panel {i}",
             "points": [[x - a, y - b], [x + a, y - b], [x + a, y + b], [x - a, y + b]]}
            for i, (x, y, a, b) in enumerate(spots)]


def lashing(group, lines):
    return [{"group": group, "color": "#4a3f33", "shade": "deep", "role": "detail", "min_px": 45,
             "note": f"cargo lashing {i}", "points": [[x0, y0], [x1, y1], [x1 + 0.02, y1 + 0.02], [x0 + 0.02, y0 + 0.02]]}
            for i, (x0, y0, x1, y1) in enumerate(lines)]


# ======================================================================
# 1. SHIP DESIGNS  - welded from mismatched modules
# ======================================================================
CARRIER_COURIER = {
    "identity": "Free carrier run-hull - three mismatched hull modules welded nose-to-tail, a canopy scavenged from a fourth ship, two odd-sized nacelles, cargo lashing over the spine and a hand-painted name bar on the flank. Reads as a lumpy dark box with two bright dots and a bright stripe.",
    "tier": "ship_near", "palette": PFX, "size": 11,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "fwd", "color": "hull", "shade": "matte", "flatten_px": 40, "note": "forward module",
         "points": [[-0.28, -1.1], [0.28, -1.1], [0.34, -0.6], [-0.34, -0.6]]},
        {"group": "mid", "color": "hull_dk", "shade": "matte", "flatten_px": 45, "note": "mid module",
         "points": [[-0.38, -0.6], [0.38, -0.6], [0.42, 0.4], [-0.42, 0.4]]},
        {"group": "aft", "color": "engine", "shade": "deep", "flatten_px": 45, "note": "aft module",
         "points": [[-0.36, 0.4], [0.36, 0.4], [0.3, 0.98], [-0.3, 0.98]]},
        {"group": "canopy", "color": "glass", "shade": "sheen", "flatten_px": 55, "note": "scavenged canopy",
         "points": [[-0.13, -0.9], [0.15, -0.86], [0.13, -0.5], [-0.15, -0.54]]},
        {"group": "nac_r", "color": "metal", "shade": "metal", "flatten_px": 45, "note": "right nacelle (larger)",
         "points": [[0.36, 0.3], [0.58, 0.3], [0.58, 1.02], [0.36, 1.02]]},
        {"group": "nac_l", "color": "metal", "shade": "metal", "flatten_px": 45, "note": "left nacelle (smaller)",
         "points": [[-0.34, 0.36], [-0.5, 0.36], [-0.5, 0.94], [-0.34, 0.94]]},
    ],
    "details": [
        *patch("mid", [(-0.2, -0.3, 0.12, 0.12), (0.22, 0.1, 0.14, 0.1)]),
        *lashing("mid", [(-0.36, -0.2, 0.36, -0.1), (-0.36, 0.1, 0.36, 0.2)]),
        {"group": "mid", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 50,
         "note": "hand-painted name bar", "points": [[-0.36, -0.05], [0.36, -0.05], [0.36, 0.05], [-0.36, 0.05]]},
        {"group": "fwd", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 90, "note": "nav light", "circle": [0.0, -1.05, 0.05]},
        {"group": "nac_r", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "right thruster", "circle": [0.47, 1.02, 0.12]},
        {"group": "nac_l", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "left thruster", "circle": [-0.42, 0.94, 0.1]},
    ],
}

CARRIER_HAULER = {
    "identity": "Free carrier freight raft - a flat frame carrying nine lashed cargo cans in six different colours, a small scavenged cab bolted forward-left, an oversized patched engine block aft. The whole thing looks temporary and has flown for forty years. Reads as a raft of mismatched boxes with a bright engine.",
    "tier": "ship_near", "palette": PFX, "size": 21,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "frame", "color": "engine", "shade": "deep", "flatten_px": 60, "note": "flat frame",
         "points": [[-0.44, -0.95], [0.44, -0.95], [0.44, 0.85], [-0.44, 0.85]]},
        {"group": "cab", "color": "glass", "shade": "sheen", "flatten_px": 55, "note": "scavenged cab",
         "points": [[-0.4, -0.92], [-0.06, -0.92], [-0.06, -0.6], [-0.4, -0.6]]},
        {"group": "engine", "color": "hull_dk", "shade": "deep", "flatten_px": 55, "note": "patched engine block",
         "points": [[-0.5, 0.78], [0.5, 0.78], [0.42, 1.18], [-0.42, 1.18]]},
    ],
    "details": [
        *[{"group": "frame", "color": BORROW[i % len(BORROW)], "shade": "matte", "role": "detail", "min_px": 22,
           "note": f"cargo can {i}",
           "points": [[cx - 0.13, cy - 0.19], [cx + 0.13, cy - 0.19], [cx + 0.13, cy + 0.19], [cx - 0.13, cy + 0.19]]}
          for i, (cx, cy) in enumerate([(x, y) for y in (-0.4, 0.05, 0.5) for x in (-0.28, 0.0, 0.28)])],
        *lashing("frame", [(-0.42, -0.15, 0.42, -0.15), (-0.42, 0.3, 0.42, 0.3), (0.0, -0.9, 0.0, 0.75)]),
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 16, "note": "right thruster", "circle": [0.22, 1.14, 0.14]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 16, "note": "left thruster", "circle": [-0.22, 1.14, 0.14]},
    ],
}

CARRIER_PATROL = {
    "identity": "Free carrier escort hull - a run-hull with a bolted-on gun rail down one side, extra salvage armour plate clamped over the nose, and a second-hand thruster that doesn't match the first. Carriers don't build warships; they build this when a lane gets dangerous. Reads as a scrappy box bristling on one side.",
    "tier": "ship_near", "palette": PFX, "size": 15,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "matte", "flatten_px": 45, "note": "run-hull",
         "points": [[-0.3, -1.0], [0.3, -1.0], [0.42, -0.5], [0.42, 0.8], [0.3, 1.04], [-0.3, 1.04], [-0.42, 0.8], [-0.42, -0.5]]},
        {"group": "armour", "color": "metal", "shade": "metal", "flatten_px": 50, "note": "clamped nose armour",
         "points": [[-0.32, -1.0], [0.32, -1.0], [0.32, -0.7], [-0.32, -0.7]]},
        {"group": "gun", "color": "hull_dk", "shade": "deep", "flatten_px": 45, "note": "bolted gun rail",
         "points": [[0.42, -0.7], [0.56, -0.7], [0.56, 0.3], [0.42, 0.3]]},
        {"group": "canopy", "color": "glass", "shade": "sheen", "flatten_px": 50, "note": "canopy",
         "points": [[-0.13, -0.6], [0.13, -0.6], [0.13, -0.2], [-0.13, -0.2]]},
    ],
    "details": [
        *patch("hull", [(-0.24, 0.2, 0.12, 0.14), (0.2, 0.5, 0.12, 0.12)]),
        *lashing("hull", [(-0.4, 0.0, 0.4, 0.0)]),
        {"group": "gun", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 18, "note": "muzzle", "circle": [0.49, -0.66, 0.05]},
        {"group": "hull", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "right thruster (mismatched)", "circle": [0.26, 1.04, 0.13]},
        {"group": "hull", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "left thruster", "circle": [-0.26, 1.04, 0.1]},
    ],
}

SHIP_DESIGNS = {
    "carrier_courier": (CARRIER_COURIER, [[0.47, 1.02], [-0.42, 0.94]],
                        [[-0.28, -1.1], [0.28, -1.1], [0.42, 0.4], [0.3, 0.98], [-0.3, 0.98], [-0.42, 0.4]]),
    "carrier_hauler": (CARRIER_HAULER, [[0.22, 1.14], [-0.22, 1.14]],
                       [[-0.44, -0.95], [0.44, -0.95], [0.44, 0.85], [0.42, 1.18], [-0.42, 1.18], [-0.44, 0.85]]),
    "carrier_patrol": (CARRIER_PATROL, [[0.26, 1.04], [-0.26, 1.04]],
                       [[-0.3, -1.0], [0.3, -1.0], [0.56, 0.3], [0.42, 0.8], [0.3, 1.04], [-0.3, 1.04], [-0.42, 0.8], [-0.42, -0.5]]),
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
# 2. BUILDINGS  - a patched berth-depot look (light pass; carriers don't settle)
# ======================================================================
def depot(identity, w_, h_, note):
    return {
        "identity": identity, "tier": "building", "palette": PFX, "view": "elevation",
        "units": "absolute local units (31 = player height). ELEVATION.",
        "scale_note": f"~{h_ / 31:.1f}x PLAYER_H tall, ~{2 * w_ / 31:.1f}x wide",
        "silhouette": [
            {"group": "body", "color": "hull_dk", "shade": "matte", "note": "shed wall", "flatten_px": 60,
             "points": [[-w_, 0], [w_, 0], [w_, -h_ + 8], [w_ - 6, -h_], [-w_ + 6, -h_], [-w_, -h_ + 8]]},
            {"group": "body", "color": "engine", "shade": "matte", "note": "roller door",
             "points": [[-w_ * 0.4, -h_ * 0.6], [w_ * 0.4, -h_ * 0.6], [w_ * 0.4, 0], [-w_ * 0.4, 0]]},
        ],
        "details": patch("body", [(-w_ * 0.6, -h_ * 0.5, w_ * 0.14, h_ * 0.12),
                                  (w_ * 0.55, -h_ * 0.4, w_ * 0.16, h_ * 0.14),
                                  (0, -h_ * 0.85, w_ * 0.3, h_ * 0.08)]) + [
            {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 14, "note": "name-board",
             "points": [[-w_ * 0.5, -h_ * 0.72], [w_ * 0.5, -h_ * 0.72], [w_ * 0.5, -h_ * 0.6], [-w_ * 0.5, -h_ * 0.6]]},
        ],
    }


BUILDINGS = {
    "carrier_hall": (depot("Free carrier berth-hall, head-on: a wide patched cargo shed of welded panels in six greys, a roller door, a hand-painted name-board across the front. Whoever's tied up here this month.", 56, 44, "hall"),
                     {"width": 112, "depth": 40.0}),
    "carrier_housing": (depot("Free carrier bunk-shed, head-on: a smaller patched shed the crews sleep in between runs, a single door, a lit name-board, salvage panels bolted wherever a hole opened.", 36, 40, "housing"),
                        {"width": 72, "depth": 28.0}),
    "carrier_spire": (depot("Free carrier lash-tower, head-on: a tall narrow patchwork mast of stacked container frames the carriers use as a lookout and a comms rig, a name-board at the top, guy-lines everywhere.", 22, 90, "spire"),
                      {"width": 44, "depth": 18.0}),
}
bt = r(f"{S}/building_types.json")
for bid, (design, fp) in BUILDINGS.items():
    w(f"{G}/buildings/{bid}.json", design)
    bt[bid]["footprint"] = fp
w(f"{S}/building_types.json", bt)

# ======================================================================
# 3. DRESS PALETTE + BESPOKE WARDROBE
# ======================================================================
dress = r(f"{G}/palettes/{DRESS}.json")
dress["identity"] = "Free carrier dress - hard-worn canvas and salvaged leather in mismatched greys and tans, patched everywhere, a hand-painted name somewhere on it. Amber running-light trim. Human skin/hair unchanged."
dress.update({"cloth": "#8a8073", "denim": "#5c564e", "knit": "#9a8f7c", "leather": "#6a5a48",
              "metal": "#a8a090", "glass": "#ffcf8c", "lamp": "#ffbf7c"})
w(f"{G}/palettes/{DRESS}.json", dress)

ARTICLES = {
    "carrier_patch_vest": article(
        "Free carrier patch vest - a canvas work vest covered in mismatched patches, each from a different hull the wearer has crewed. Worn shut against the cargo bay chill.",
        DRESS, [region("torso", "vest", "patch vest", "cloth", "matte",
                       [[-3.4, -25.2], [3.4, -25.2], [3.0, -19.2], [-3.0, -19.2]],
                       [[-3.0, -25.1], [3.0, -25.1], [2.6, -19.6], [-2.6, -19.6]],
                       m_det=[{"group": "torso", "color": BORROW[0], "shade": "matte", "note": "vest patch a", "points": [[-2.6, -24.0], [-1.0, -24.0], [-1.0, -22.2], [-2.6, -22.2]]},
                              {"group": "torso", "color": BORROW[2], "shade": "matte", "note": "vest patch b", "points": [[0.8, -23.2], [2.6, -23.2], [2.6, -21.0], [0.8, -21.0]]},
                              {"group": "torso", "color": BORROW[4], "shade": "matte", "note": "vest patch c", "points": [[-1.6, -21.4], [0.4, -21.4], [0.4, -19.6], [-1.6, -19.6]]}],
                       f_det=[{"group": "torso", "color": BORROW[1], "shade": "matte", "note": "vest patch a", "points": [[-2.2, -24.0], [-0.8, -24.0], [-0.8, -22.4], [-2.2, -22.4]]},
                              {"group": "torso", "color": BORROW[3], "shade": "matte", "note": "vest patch b", "points": [[0.6, -23.0], [2.2, -23.0], [2.2, -21.2], [0.6, -21.2]]}])]),
    "carrier_lash_belt": article(
        "Free carrier lash belt - a heavy webbing belt hung with a coil of cargo strap, a shackle, and a folding knife. A carrier's whole toolkit is on it.",
        DRESS, [region("torso", "belt", "lash belt", "leather", "deep",
                       [[-2.7, -19.8], [2.7, -19.7], [2.6, -18.9], [-2.6, -19.0]],
                       [[-1.8, -20.5], [1.9, -20.4], [2.1, -19.6], [-2.0, -19.7]],
                       m_det=[{"group": "torso", "color": "metal", "shade": "metal", "note": "belt shackle", "points": [[-0.5, -19.9], [0.4, -19.9], [0.4, -19.0], [-0.5, -19.0]]},
                              {"group": "torso", "color": "leather", "shade": "deep", "note": "strap coil", "points": [[1.6, -20.2], [2.8, -20.0], [2.9, -18.4], [1.7, -18.6]]}],
                       f_det=[{"group": "torso", "color": "metal", "shade": "metal", "note": "belt shackle", "points": [[-0.4, -20.4], [0.4, -20.4], [0.4, -19.6], [-0.4, -19.6]]},
                              {"group": "torso", "color": "leather", "shade": "deep", "note": "strap coil", "points": [[1.3, -20.6], [2.4, -20.4], [2.5, -19.0], [1.4, -19.2]]}])]),
    "carrier_name_tag": article(
        "Free carrier name-tag - a hand-painted board on a cord at the chest with the wearer's ship and given name. Carriers introduce the hull before the person.",
        DRESS, [region("torso", "badge", "name board", "lamp", "glow",
                       [[-1.6, -23.6], [1.6, -23.6], [1.6, -22.2], [-1.6, -22.2]],
                       [[-1.4, -23.9], [1.4, -23.9], [1.4, -22.6], [-1.4, -22.6]],
                       m_det=[{"group": "torso", "color": "leather", "shade": "deep", "note": "name board cord", "points": [[-0.1, -25.4], [0.1, -25.4], [0.5, -23.6], [-0.5, -23.6]]}],
                       f_det=[{"group": "torso", "color": "leather", "shade": "deep", "note": "name board cord", "points": [[-0.1, -25.6], [0.1, -25.6], [0.45, -23.9], [-0.45, -23.9]]}])]),
    "carrier_deck_bib": article(
        "Free carrier deck bib - a scuffed canvas apron to the thigh with grease-black hand-prints and two big tool pockets, worn on the cargo deck.",
        DRESS, [apron_region("denim", "matte", "deck bib")]),
    "carrier_run_band": article(
        "Free carrier run-band - a plain arm band in a hull's colours with a painted route mark, worn by whoever's standing escort watch on a dangerous lane.",
        DRESS, [brassard_region("denim", "matte", "lamp", "run band")]),
}

SETS = {
    "carrier_command": {"identity": "Free carrier captain's turn-out - a worn long coat over canvas, the patch vest, a name-tag, the lash belt. No braid, no rank - just the oldest coat aboard.",
                        "articles": ["tank_top", "coat_field", "pants_tan", "boots_charcoal",
                                     "carrier_patch_vest", "carrier_name_tag", "carrier_lash_belt", "hair_short"]},
    "carrier_security": {"identity": "Free carrier escort-watch kit - work clothes, a scavenged helmet, the patch vest, the run-band, the lash belt.",
                         "articles": ["tank_top", "jacket_olive", "pants_field", "boots_charcoal", "helmet_bounty",
                                      "carrier_patch_vest", "carrier_run_band", "carrier_lash_belt"]},
    "carrier_dock": {"identity": "Free carrier deck-hand kit - canvas suit under the deck bib, the patch vest, gloves, a name-tag, the lash belt.",
                     "articles": ["tank_top", "jacket_dock", "pants_dock", "boots_charcoal", "gloves_dark",
                                  "carrier_deck_bib", "carrier_name_tag", "carrier_lash_belt"]},
    "carrier_flight": {"identity": "Free carrier pilot kit - a patched flight jacket, a scavenged helmet, the patch vest, a name-tag, the lash belt. This is the one carriers wear anywhere.",
                       "articles": ["tank_top", "jacket_tan", "pants_field", "boots_charcoal", "helmet_flight",
                                    "carrier_patch_vest", "carrier_name_tag", "carrier_lash_belt"]},
    "carrier_civilian": {"identity": "Free carrier off-watch dress - mismatched canvas, the patch vest half the crew owns, a name-tag, plaited-cord shoes.",
                         "articles": ["tank_top", "jacket_civ", "pants_tan", "shoes",
                                      "carrier_patch_vest", "carrier_name_tag", "hair_long"]},
}
ROLE_SET = {"civilian": "carrier_civilian", "official": "carrier_command", "flight": "carrier_flight",
            "security": "carrier_security", "dock": "carrier_dock"}
write_wardrobe(gfx, PFX, DRESS, ARTICLES, SETS, ROLE_SET)
w(f"{S}/graphics.json", gfx)

# ======================================================================
# 4. CARRIER PILOTS
# ======================================================================
pilots = r(f"{S}/pilots.json")
pilots.update({
    "rell": {"name": "Nix Ferro", "faction": "free_carrier", "role": "freighter_pilot",
             "personality": "Twenty years on the slow lanes; the beacon just made her route worthless and she is trying to laugh about it. Knows every berth in the region by its smell.",
             "hail_greeting": "Independent carrier, Ferro's Slip. I was running this lane before your beacon woke up, friend. Now I'm just in the way of it."},
    "ash": {"name": "Captain Ash", "faction": "free_carrier", "role": "freighter_pilot",
            "personality": "Old, unbothered, has outlived three governments and expects to outlive the Relay too.",
            "hail_greeting": "Carrier hull, no cargo you'd want. Forty years I've flown between these stars. A beacon doesn't change where they are."},
    "dume": {"name": "Dume Halloran", "faction": "free_carrier", "role": "courier_pilot",
             "personality": "Fast, chatty, runs messages and small freight and gossip in equal measure; thrilled the lanes are opening.",
             "hail_greeting": "Halloran, carrier courier. Quick run through. Anything you need moved, I'm cheaper than a beacon fee."},
    "sable": {"name": "Sable Nix", "faction": "free_carrier", "role": "patrol_officer",
              "personality": "Rides escort on the dangerous lanes for whoever pays; not a fighter by trade, just the one who stayed calm.",
              "hail_greeting": "Carrier escort, paid by the run. I'm not looking for trouble - I'm looking at you so trouble doesn't."},
})
w(f"{S}/pilots.json", pilots)

# ======================================================================
# 5. CARRIER PRESENCE IN EVERY SYSTEM  (idempotent - keyed by name)
# ======================================================================
CARRIER_SHIP = {
    "halcyon": {"name": "Ferro's Slip", "pilot": "rell", "ship_type": "carrier_hauler", "x": 0.3, "y": 0.55},
    "kiln": {"name": "Halloran's Run", "pilot": "dume", "ship_type": "carrier_courier", "x": 0.28, "y": 0.62},
    "verdance": {"name": "Captain Ash", "pilot": "ash", "ship_type": "carrier_hauler", "x": 0.72, "y": 0.28},
    "ossuary": {"name": "Sable's Watch", "pilot": "sable", "ship_type": "carrier_patrol", "x": 0.66, "y": 0.4},
    "the_span": {"name": "Ash's Barque", "pilot": "ash", "ship_type": "carrier_hauler", "x": 0.62, "y": 0.62},
}
BERTH_NPC = {
    "halcyon": ("Deckhand at the Slip", "Half the carriers on the ring are drinking like the good years are over. The other half are betting they're just starting. I haven't decided."),
    "kiln": ("Carrier at the claw", "Combine let me tie up for exactly one shift and charged me for the air. Two centuries of that. The beacon won't fix it but it might route around it."),
    "verdance": ("Carrier off the Slip", "Drift's the only berth in the region that just says 'tie up, rest'. Carriers remember that. When the Hub asks who to trust, we'll say the Drift."),
    "ossuary": ("Carrier keeping distance", "The Vigil doesn't trade much, but they'll let you tie up and they don't ask questions. For a carrier that's most of what you want from a port."),
    "the_span": ("Parts carrier", "I run salvage to the dark segments. The Wardens pay in whatever's lying around. It's honest work and nobody else wants it."),
}
CARRIER_OUT = {"halcyon": "carrier_flight_masc", "kiln": "carrier_flight_femme", "verdance": "carrier_civilian_masc",
               "ossuary": "carrier_flight_femme", "the_span": "carrier_dock_masc"}

for sysid, ship in CARRIER_SHIP.items():
    fn = f"{S}/systems/{sysid}.json"
    sj = r(fn)
    ships = sj.setdefault("ai_ships", [])
    if not any(a.get("name") == ship["name"] for a in ships):
        ships.append({"name": ship["name"], "x": ship["x"], "y": ship["y"],
                      "ship_type": ship["ship_type"], "pilot": ship["pilot"],
                      "faction": "free_carrier", "route": ["station", "moon"]})
    interior = sj["station"]["interiors"]["default"]
    npcs = interior["npcs"]
    bname, bline = BERTH_NPC[sysid]
    if not any(n.get("name") == bname for n in npcs):
        # tuck the berth NPC + a little dressing near the south-east of the concourse
        npcs.append({"name": bname, "x": 1180, "y": 700, "role": "traveler",
                     "faction": "free_carrier", "outfit": CARRIER_OUT[sysid],
                     "greeting": bline, "dialogue_options": ["Fair enough", "Leave"]})
    structs = interior.setdefault("structures", [])
    if not any(s.get("x") == 1140 and s.get("y") == 690 for s in structs):
        structs.append({"x": 1140, "y": 690, "building_type": "crates"})
    w(fn, sj)

print(f"Free carriers pass: 3 patchwork ships, 3 depot buildings, dress + {len(ARTICLES)} articles / "
      f"{len(SETS)} sets, {len(pilots)} pilots, carrier ship + berth NPC in all {len(CARRIER_SHIP)} systems.")
