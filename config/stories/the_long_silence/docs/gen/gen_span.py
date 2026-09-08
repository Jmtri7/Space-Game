"""Phase 6.5 - the Span slice (the Wardens), Act I stub.

Owns systems/the_span.json. Run after gen_ossuary (see docs/gen/README.md).
The Span stays beacon-locked through Act I ("NO SIGNAL" on the star map) and
opens mid-Act II once the player carries the signal there (act_span +
standing). This slice authors the Warden exterior/interior art and a minimal
Hub Zero with the ending fork; the bespoke Warden wardrobe and a full roster
are deferred to Act II (the warden_* outfits stay palette recolours for now).

Warden style (cultures.json): vast smooth Relay-era forms in dark alloy and
teal light, patched with mismatched salvage and hand-lettered ritual markings.
"""
import math
from _slice_kit import S, G, w, r, rect, concourse_plan, BAY_N, BAY_S, station_shell

PFX = "warden"


def arc(cx, cy, rx, ry, a0, a1, n=16):
    return [[round(cx + rx * math.cos(a0 + (a1 - a0) * i / n), 3),
             round(cy + ry * math.sin(a0 + (a1 - a0) * i / n), 3)] for i in range(n + 1)]


def salvage(group, spots):
    """Mismatched hand-bolted salvage panels - each a different borrowed metal."""
    cols = ["#7a6a52", "#5a6a6a", "#6a5a5a", "#66707a"]
    return [{"group": group, "color": cols[i % len(cols)], "shade": "matte", "role": "detail", "min_px": 40,
             "note": f"salvage patch {i}",
             "points": [[x - w_, y - h_], [x + w_, y - h_], [x + w_, y + h_], [x - w_, y + h_]]}
            for i, (x, y, w_, h_) in enumerate(spots)]


# ======================================================================
# 1. SHIPS  - smooth monumental hulls, teal core, salvage cladding
# ======================================================================
WARDEN_COURIER = {
    "identity": "Warden Reader - a smooth dark-alloy wedge from the Relay era, a teal-lit core running its length, two hand-bolted salvage patches, a single wide tail glow. Ancient lines, mended by hand. Reads as a dark arrowhead with a teal seam.",
    "tier": "ship_near", "palette": PFX, "size": 12,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "metal", "flatten_px": 45, "note": "smooth wedge",
         "points": [[0.0, -1.16], [0.36, -0.3], [0.4, 0.7], [0.3, 1.02], [-0.3, 1.02], [-0.4, 0.7], [-0.36, -0.3]]},
        {"group": "core", "color": "glass", "shade": "flat", "flatten_px": 200, "note": "teal core seam",
         "points": [[-0.06, -0.9], [0.06, -0.9], [0.06, 0.8], [-0.06, 0.8]]},
        {"group": "tail", "color": "engine", "shade": "metal", "flatten_px": 45, "note": "tail block",
         "points": [[-0.32, 0.8], [0.32, 0.8], [0.26, 1.08], [-0.26, 1.08]]},
    ],
    "details": [
        *salvage("hull", [(-0.26, 0.1, 0.1, 0.16), (0.24, 0.4, 0.12, 0.12)]),
        {"group": "core", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 40, "note": "core light", "circle": [0.0, -0.2, 0.06]},
        {"group": "tail", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "thruster", "circle": [0.0, 1.06, 0.2]},
    ],
}

WARDEN_HAULER = {
    "identity": "Warden Barque - a monumental smooth Relay-era freighter: a long dark-alloy body with a teal spine-light, heavy salvage cladding bolted down both flanks, a broad low stern glow. Built for a network that no longer exists, kept running anyway.",
    "tier": "ship_near", "palette": PFX, "size": 22,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "metal", "flatten_px": 60, "note": "monumental body",
         "points": [[0.0, -1.1], [0.34, -0.7], [0.42, 0.8], [0.32, 1.06], [-0.32, 1.06], [-0.42, 0.8], [-0.34, -0.7]]},
        {"group": "core", "color": "glass", "shade": "flat", "flatten_px": 200, "note": "teal spine",
         "points": [[-0.05, -0.9], [0.05, -0.9], [0.05, 0.85], [-0.05, 0.85]]},
        {"group": "engine", "color": "engine", "shade": "metal", "flatten_px": 55, "note": "stern block",
         "points": [[-0.4, 0.82], [0.4, 0.82], [0.32, 1.16], [-0.32, 1.16]]},
    ],
    "details": [
        *salvage("hull", [(-0.3, -0.2, 0.1, 0.24), (-0.3, 0.4, 0.1, 0.2), (0.3, 0.0, 0.11, 0.22), (0.3, 0.5, 0.11, 0.18)]),
        {"group": "core", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 40, "note": "spine light", "circle": [0.0, 0.0, 0.05]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 16, "note": "right thruster", "circle": [0.18, 1.12, 0.16]},
        {"group": "engine", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 16, "note": "left thruster", "circle": [-0.18, 1.12, 0.16]},
    ],
}

WARDEN_PATROL = {
    "identity": "Warden Segment-guard - a smooth curved arc of dark alloy, a teal light-lance along the inner edge, salvage armour clamped at the shoulders, a wide twin stern glow. It patrols the ring segments like a piece of the ring broken loose. Reads as a dark crescent with a teal edge.",
    "tier": "ship_near", "palette": PFX, "size": 17,
    "units": "fractions of `size`; nose points up (-y); symmetric about x=0.",
    "silhouette": [
        {"group": "hull", "color": "hull", "shade": "metal", "flatten_px": 45, "note": "arc hull",
         "points": arc(0.0, 0.4, 0.9, 1.3, math.radians(-140), math.radians(-40), 14) +
                   arc(0.0, 0.55, 0.6, 0.95, math.radians(-40), math.radians(-140), 14)},
        {"group": "core", "color": "glass", "shade": "flat", "flatten_px": 200, "note": "teal lance edge",
         "points": arc(0.0, 0.42, 0.86, 1.24, math.radians(-135), math.radians(-45), 12) +
                   arc(0.0, 0.45, 0.82, 1.18, math.radians(-45), math.radians(-135), 12)},
    ],
    "details": [
        *salvage("hull", [(-0.6, 0.1, 0.12, 0.14), (0.6, 0.1, 0.12, 0.14)]),
        {"group": "core", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 20, "note": "lance tip", "circle": [0.0, -0.78, 0.06]},
        {"group": "hull", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "right thruster", "circle": [0.5, 0.86, 0.12]},
        {"group": "hull", "color": "thrust", "shade": "glow", "role": "detail", "min_px": 12, "note": "left thruster", "circle": [-0.5, 0.86, 0.12]},
    ],
}

SHIP_DESIGNS = {
    "warden_courier": (WARDEN_COURIER, [[0.0, 1.06]],
                       [[0.0, -1.16], [0.4, 0.7], [0.3, 1.02], [-0.3, 1.02], [-0.4, 0.7]]),
    "warden_hauler": (WARDEN_HAULER, [[0.18, 1.12], [-0.18, 1.12]],
                      [[0.0, -1.1], [0.42, 0.8], [0.32, 1.16], [-0.32, 1.16], [-0.42, 0.8]]),
    "warden_patrol": (WARDEN_PATROL, [[0.5, 0.86], [-0.5, 0.86]],
                      [[-0.9, -0.4], [0.9, -0.4], [0.6, 1.0], [-0.6, 1.0]]),
}
for sid, (design, thr, local) in SHIP_DESIGNS.items():
    w(f"{G}/ships/{sid}.json", design)

gfx = r(f"{S}/graphics.json")
for sid, (design, thr, local) in SHIP_DESIGNS.items():
    e = gfx["ships"][sid]
    e["local_points"] = local
    e["thrusters"] = thr
    e["thruster_width"] = 0.08
    e["thruster_length"] = 22

# ======================================================================
# 2. STATION  "Hub Zero" - a broken ring arc with a teal core
# ======================================================================
WARDEN_STATION = {
    "identity": "Hub Zero - the Relay core's dock: a vast smooth arc of the old ringworld, broken at both ends, a blinding teal reactor-core suspended at its centre on three salvage-braced spokes, hand-lettered warden markings across the inner face. It hums. Reads as a dark crescent cradling a teal star.",
    "tier": "station", "palette": PFX, "size": 50,
    "units": "fractions of `size`; a fixed broken arc, not radially symmetric.",
    "silhouette": [
        {"group": "arc", "color": "hull", "shade": "metal", "flatten_px": 70, "note": "ring arc",
         "points": arc(0.0, 0.0, 1.0, 1.0, math.radians(-165), math.radians(-15), 22) +
                   arc(0.0, 0.0, 0.66, 0.66, math.radians(-15), math.radians(-165), 22)},
        {"group": "core", "color": "glass", "shade": "flat", "flatten_px": 200, "note": "teal core",
         "points": arc(0.0, -0.1, 0.2, 0.2, 0, 2 * math.pi, 16)},
        *[{"group": f"spoke{i}", "color": "hull_dk", "shade": "matte", "flatten_px": 55, "note": f"brace spoke {i}",
           "points": [[0.02 * dx, -0.1], [-0.02 * dx, -0.1], [0.5 * dx, -0.72], [0.46 * dx, -0.72]]}
          for i, dx in enumerate((-1, 0.05, 1))],
    ],
    "details": [
        {"group": "core", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 18, "note": "core glare", "circle": [0.0, -0.1, 0.3]},
        *salvage("arc", [(-0.7, -0.5, 0.12, 0.14), (0.7, -0.5, 0.12, 0.14), (0.0, -0.92, 0.16, 0.1)]),
        *[{"group": "arc", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 40, "note": f"warden marking {i}",
           "points": [[x - 0.06, -0.82], [x + 0.06, -0.82], [x + 0.06, -0.7], [x - 0.06, -0.7]]}
          for i, x in enumerate((-0.4, -0.15, 0.15, 0.4))],
    ],
}
w(f"{G}/stations/warden_station.json", WARDEN_STATION)
gfx["space_stations"]["warden_station"]["local_points"] = (
    arc(0.0, 0.0, 1.0 * 50, 1.0 * 50, math.radians(-165), math.radians(-15), 14) +
    arc(0.0, 0.0, 0.66 * 50, 0.66 * 50, math.radians(-15), math.radians(-165), 14))
gfx["space_stations"]["warden_station"]["rotation_speed"] = 0.05
gfx["space_stations"]["warden_station"]["size"] = 50

# ======================================================================
# 3. BUILDINGS  (elevation) - monumental smooth arches + salvage
# ======================================================================
WARDEN_HALL = {
    "identity": "Warden Choir hall, head-on: a vast smooth Relay-era arch of dark alloy, a teal-lit inner recess, hand-lettered ritual markings across the span, mismatched salvage bolted along the base. Older than any culture that reads it now.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~2.2x PLAYER_H to the crown, ~4x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "metal", "note": "arch mass", "flatten_px": 60,
         "points": [[-62, 0], [-62, -40], [-42, -60], [0, -68], [42, -60], [62, -40], [62, 0], [40, 0], [40, -44], [0, -52], [-40, -44], [-40, 0]]},
        {"group": "body", "color": "glass", "shade": "flat", "note": "teal recess",
         "points": [[-38, 0], [-38, -42], [0, -50], [38, -42], [38, 0]]},
    ],
    "details": [
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 16, "note": "recess glow",
         "points": [[-34, -6], [34, -6], [34, 0], [-34, 0]]},
        *[{"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 12, "note": f"warden marking {i}",
           "points": [[x - 3, -58], [x + 3, -58], [x + 3, -48], [x - 3, -48]]} for i, x in enumerate((-24, -8, 8, 24))],
        *salvage("body", [(-52, -12, 8, 10), (52, -12, 8, 10), (0, -4, 10, 6)]),
    ],
}

WARDEN_HOUSING = {
    "identity": "Warden quarters, head-on: a smooth alloy half-vault the Wardens moved into, a single teal-lit hatch, salvage lean-tos bolted across the front, hand-lettered numbers where windows would be. Living in the margins of something enormous.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~2.4x PLAYER_H tall, ~2.6x wide",
    "silhouette": [
        {"group": "body", "color": "hull_dk", "shade": "metal", "note": "half-vault", "flatten_px": 60,
         "points": [[-40, 0], [-40, -40], [-24, -58], [24, -58], [40, -40], [40, 0]]},
        {"group": "body", "color": "engine", "shade": "matte", "note": "hatch",
         "points": [[-8, -18], [8, -18], [8, 0], [-8, 0]]},
    ],
    "details": [
        {"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 10, "note": "hatch light",
         "points": [[-7, -17], [7, -17], [7, -13], [-7, -13]]},
        *salvage("body", [(-30, -10, 9, 10), (30, -10, 9, 10), (0, -46, 12, 8)]),
        *[{"group": "body", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 10, "note": f"hand number {i}",
           "points": [[x - 3, -44], [x + 3, -44], [x + 3, -34], [x - 3, -34]]} for i, x in enumerate((-20, 20))],
    ],
}

WARDEN_SPIRE = {
    "identity": "the Signal-Mast, head-on: a colossal smooth Relay-era pylon rising out of sight, teal light climbing its length in pulses, a scaffold of salvage clinging to the base where the Wardens tend it. The thing the reactivation signal comes from.",
    "tier": "building", "palette": PFX, "view": "elevation",
    "units": "absolute local units (31 = player height). ELEVATION.",
    "scale_note": "~5.5x PLAYER_H of visible mast, ~1.6x wide at the base",
    "silhouette": [
        {"group": "body", "color": "hull", "shade": "metal", "note": "pylon", "flatten_px": 55,
         "points": [[-24, 0], [24, 0], [16, -168], [-16, -168]]},
        {"group": "core", "color": "glass", "shade": "flat", "note": "teal channel",
         "points": [[-5, 0], [5, 0], [4, -168], [-4, -168]]},
    ],
    "details": [
        *[{"group": "core", "color": "lamp", "shade": "glow", "role": "detail", "min_px": 12, "note": f"signal pulse {i}",
           "points": [[-4, y], [4, y], [4, y + 6], [-4, y + 6]]} for i, y in enumerate((-20, -60, -100, -140))],
        *salvage("body", [(-20, -14, 9, 12), (20, -14, 9, 12), (0, -30, 10, 8)]),
    ],
}

BUILDINGS = {
    "warden_hall": (WARDEN_HALL, {"width": 124, "depth": 36.0}),
    "warden_housing": (WARDEN_HOUSING, {"width": 80, "depth": 26.0}),
    "warden_spire": (WARDEN_SPIRE, {"width": 48, "depth": 18.0}),
}
bt = r(f"{S}/building_types.json")
for bid, (design, fp) in BUILDINGS.items():
    w(f"{G}/buildings/{bid}.json", design)
    bt[bid]["footprint"] = fp
w(f"{S}/building_types.json", bt)

# dress palette: keep the Act-II wardrobe deferred, but give the recolour
# a real teal-on-alloy identity so the placeholder outfits read as Warden.
dress = r(f"{G}/palettes/warden_dress.json")
dress["identity"] = "Warden dress (Act I placeholder recolour - bespoke wardrobe deferred to Act II) - dark alloy-grey work cloth, salvaged leather, hand-lettered white, a teal signal-lamp accent."
dress.update({"cloth": "#3c4240", "denim": "#2e3432", "knit": "#4a524e", "leather": "#4a4038",
              "metal": "#9a8a5c", "glass": "#78ffdc", "lamp": "#78ffdc"})
w(f"{G}/palettes/warden_dress.json", dress)
w(f"{S}/graphics.json", gfx)

# ======================================================================
# 4. HUB ZERO  minimal interior + the ending fork
# ======================================================================
HZ_ROOMS = concourse_plan("the Approach Span", [
    BAY_N(440, 900, "the Core Choir"),
    BAY_N(1180, 1480, "the Arrival Span"),
    BAY_S(220, 560, "the Signal-Tender's post"),
    BAY_S(1060, 1420, "Segment Four watch"),
])
HZ_STRUCTURES = [
    {"x": 800, "y": 640, "building_type": "warden_spire"},
    *[{"x": x, "y": 584, "building_type": "pipeline_column"} for x in (560, 720, 880, 1040)],
    *[{"x": x, "y": 716, "building_type": "pipeline_column"} for x in (560, 720, 880, 1040)],
    {"x": 360, "y": 900, "building_type": "crates"},
    {"x": 1240, "y": 900, "building_type": "crates"},
]
HZ_NPCS = [
    {"name": "First Warden", "x": 800, "y": 470, "role": "magistrate",
     "faction": "the_wardens", "outfit": "warden_official_femme",
     "dialogue_tree": {"root": "start", "nodes": {
        "start": {"text": "You reached the Span. The Hub sings, and it is asking a question it has asked no one in two hundred years: what should the Relay be? We tend the machinery. We do not decide for it. You will. Stand at the Core Choir and choose - there is no undoing it.",
                  "options": [
                      {"label": "Restore the Relay - one network, run from a hub.", "next": "confirm_restore"},
                      {"label": "Sever it. Destroy the core.", "next": "confirm_sever"},
                      {"label": "Keep the beacons, break only the hub - no one rules the network.",
                       "next": "confirm_middle", "requires_rep": "the_vigil:10",
                       "requires_not_flag": "patron:harbor_authority"},
                      {"label": "Not yet.", "next": None}]},
        "confirm_restore": {"text": "Then the lanes reopen, and whoever holds Halcyon holds the hub. A connected region, unequal and unstable. You are certain?",
                            "options": [{"label": "Do it.", "next": None, "action": "end_story:restore"},
                                        {"label": "Wait.", "next": "start"}]},
        "confirm_sever": {"text": "Then the core goes dark for good, and the systems stay islands - trade back to the slow carriers and their decade-long loops. You are certain?",
                          "options": [{"label": "Do it.", "next": None, "action": "end_story:sever"},
                                      {"label": "Wait.", "next": "start"}]},
        "confirm_middle": {"text": "Then the beacons stay lit and the hub breaks - no single system can dominate the network, and none can schedule it either. The hardest road to hold. You are certain?",
                           "options": [{"label": "Do it.", "next": None, "action": "end_story:hold_middle"},
                                       {"label": "Wait.", "next": "start"}]}}}},

    {"name": "the Signal-Tender", "x": 380, "y": 900, "role": "quartermaster",
     "faction": "the_wardens", "outfit": "warden_dock_masc",
     "greeting": "We keep the machinery, not a market. A carrier who runs parts to the outer segments is always welcome - and we are always short of parts.",
     "shop": {"type": "commodities", "stock": ["hub_parts", "salvage"], "sell_multiplier": 1.1}},

    {"name": "Keeper of the Hub", "x": 1240, "y": 900, "role": "resident",
     "faction": "the_wardens", "outfit": "warden_civilian_femme",
     "greeting": "Segment Four was dark since before my grandmother tended it. Now its lights come up one by one, and none of us set them to. The Hub is finishing something. We only keep it swept.",
     "dialogue_options": ["Understood", "Leave"]},

    {"name": "Warden of the Fourth Segment", "x": 800, "y": 700, "role": "guard",
     "faction": "the_wardens", "outfit": "warden_security_masc",
     "greeting": "You are inside the Span. The Hub hears you. Mind that it does - it has been listening a long time, for whoever came last.",
     "dialogue_options": ["Understood", "Leave"]},
]
HZ_INTERIOR = {"label": "Hub Zero", "culture": "the_wardens",
               "portals": [{"x": 1360, "y": 470, "connected_locations": [], "return_to_ship": True}],
               "rooms": HZ_ROOMS, "structures": HZ_STRUCTURES, "npcs": HZ_NPCS,
               **station_shell(PFX, 205)}


def core_moon():
    return {
        "name": "the Core Choir", "x": 0.82, "y": 0.78, "size": 26, "color": [90, 120, 116],
        "crater_color": [60, 90, 86], "landing_distance": 34,
        "craters": [{"x": -7, "y": -3, "radius": 4}, {"x": 8, "y": 7, "radius": 4}],
        "interiors": {"city": {
            "label": "Ring Segment Four", "culture": "the_wardens",
            "connected_locations": [], "entrance": {"x": 800, "y": 840},
            "rooms": [rect(220, 260, 1380, 1100, "Segment Four Floor")],
            "structures": [
                {"x": 800, "y": 520, "building_type": "warden_hall"},
                {"x": 470, "y": 780, "building_type": "warden_housing"},
                {"x": 1130, "y": 780, "building_type": "warden_housing"},
                {"x": 800, "y": 330, "building_type": "warden_spire"},
                {"x": 360, "y": 1000, "building_type": "crates"},
                {"x": 1240, "y": 1000, "building_type": "crates"},
            ],
            "npcs": [
                {"name": "Segment Warden Threa-kin", "x": 800, "y": 700, "role": "magistrate",
                 "faction": "the_wardens", "outfit": "warden_official_masc",
                 "greeting": "Segment Four wakes a little more each day. We do not know what it is waking for. When you stand at the Choir, ask it gently.",
                 "dialogue_options": ["I will", "Leave"]},
                {"name": "Core-hand Vess", "x": 520, "y": 620, "role": "dockworker",
                 "faction": "the_wardens", "outfit": "warden_dock_femme",
                 "greeting": "Been patching this segment my whole life with whatever the carriers bring. It has never once told me thank you. I keep doing it.",
                 "dialogue_options": ["Understood", "Leave"]},
            ],
        }},
    }


THE_SPAN = {
    "name": "The Span",
    "description": "A ringworld fragment around a blue-white star - the old Relay network core. Still powered, mostly automated, sparsely held by the Wardens: a maintenance cult operating Relay-era machinery they no longer understand. The reactivation signal originates here.",
    "star_map_position": {"x": 470, "y": 90},
    "station_asset": "warden_station", "moon_asset": "warden_moon",
    "central_star": {"x": 0.5, "y": 0.5, "name": "The Span", "size": 76, "color": [206, 224, 255]},
    "player_start": {"x": 0.4, "y": 0.35}, "star_seed": 205,
    "asteroid_field": {"per_chunk_range": [1, 3], "types": [
        {"type": "gray_rock", "weight": 3, "size_range": [4, 18], "speed_range": [0.05, 0.3], "mine_yield": 10}]},
    "station": {"x": 0.2, "y": 0.24, "name": "Hub Zero", "interiors": {"default": HZ_INTERIOR}},
    "moon": core_moon(),
    "celestial_bodies": [
        {"name": "Ring Segment 4", "x": 0.6, "y": 0.55, "size": 20, "color": [140, 160, 175], "body_type": "rocky"},
        {"name": "Hub Halo", "x": 0.3, "y": 0.72, "size": 44, "color": [180, 200, 230], "body_type": "gas_giant",
         "has_ring": True, "ring_color": [150, 190, 220]}],
    "ai_ships": [
        {"name": "Segment-guard Warden", "x": 0.55, "y": 0.16, "ship_type": "warden_patrol", "pilot": "segment_warden",
         "faction": "the_wardens", "route": ["station", "moon"]},
        {"name": "Core Barque Threa", "x": 0.35, "y": 0.22, "ship_type": "warden_hauler", "pilot": "threa",
         "faction": "the_wardens", "route": ["moon", "station"]},
    ],
    "locked": True, "unlock_flag": "beacon_the_span_lit",
}
w(f"{S}/systems/the_span.json", THE_SPAN)

# ======================================================================
# 5. WARDEN PILOTS
# ======================================================================
pilots = r(f"{S}/pilots.json")
pilots.update({
    "segment_warden": {"name": "Segment Warden", "faction": "the_wardens", "role": "patrol_officer",
                       "personality": "Talks about the Hub the way the devout talk about a god they also do the maintenance on. Never hostile without cause - the Hub does not approve of noise.",
                       "hail_greeting": "You are inside the Span. The Hub hears you. Hold your approach and it will let you pass."},
    "threa": {"name": "Core-hand Threa", "faction": "the_wardens", "role": "freighter_pilot",
              "personality": "Ferries salvage to the dark segments and never quite says what for. Has stopped asking herself.",
              "hail_greeting": "Parts run, Segment Four. It has been dark a long time. It is waking up, and we feed it."},
})
w(f"{S}/pilots.json", pilots)

print(f"The Span (Act I stub): 3 ships, 1 station, 3 buildings, Hub Zero ({len(HZ_ROOMS)} rooms / "
      f"{len(HZ_NPCS)} NPCs) with the ending fork, {len(pilots)} pilots. Wardrobe deferred to Act II.")
