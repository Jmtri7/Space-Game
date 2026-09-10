"""Phase 6.5 - the Span slice (the Wardens), Act I stub.

Owns systems/the_span.json. Run after gen_ossuary (see docs/gen/README.md).
The Span stays beacon-locked through Act I ("NO SIGNAL" on the star map) and
opens mid-Act II once the player carries the signal there (act_span +
standing). This slice authors the Warden exterior/interior art, the bespoke
Warden wardrobe (added Phase 7 - five identity articles + five culture sets,
composed from the shared _slice_kit shapes), and a minimal Hub Zero with the
ending fork.

Warden style (cultures.json): vast smooth Relay-era forms in dark alloy and
teal light, patched with mismatched salvage and hand-lettered ritual markings.
"""
import math
from _slice_kit import (S, G, w, r, rect, concourse_plan, BAY_N, BAY_S, disc, polar,  station_shell,
                        article, sash_region, shoulder_slab_region, far_shoulder_slab_region,
                        pendant_region, brassard_region, gorget_region, write_wardrobe)

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

# ======================================================================
# 3b. DRESS PALETTE + BESPOKE WARDEN WARDROBE  (Phase 7 - was deferred from 6.5)
# ======================================================================
DRESS = "warden_dress"
dress = r(f"{G}/palettes/{DRESS}.json")
dress["identity"] = "Warden dress - dark alloy-grey work cloth over salvaged leather, hand-lettered white ritual marking, a teal signal-lamp accent at the throat. Human skin/hair unchanged."
dress.update({"cloth": "#3c4240", "denim": "#2e3432", "knit": "#4a524e", "leather": "#4a4038",
              "metal": "#9a8a5c", "glass": "#78ffdc", "lamp": "#78ffdc"})
w(f"{G}/palettes/{DRESS}.json", dress)

# Five identity articles, composed from the shared free-drawn shapes in
# _slice_kit (recoloured by warden_dress). The signal gorget is the mark
# every Warden wears; the hub token is the Relay-era key they tend.
ARTICLES = {
    "warden_signal_gorget": article(
        "Warden signal gorget - a stiff alloy throat collar with a lit teal bar, the sign of one who tends the hub machinery. Every Warden wears one.",
        DRESS, [gorget_region("metal", "metal", "lamp", "signal gorget")]),
    "warden_hub_token": article(
        "Warden hub token - a small Relay-era key-tablet on a cord at the sternum, teal-lit. Passed down, not issued; losing yours is losing your place.",
        DRESS, [pendant_region("glass", "glow", "hub token", "badge")]),
    "warden_salvage_pauldrons": article(
        "Warden salvage pauldrons - two mismatched shoulder plates cut from old hull and hand-bolted on, one bigger than the other. Salvage crews and segment-wardens both.",
        DRESS, [shoulder_slab_region("leather", "deep", "salvage plate"),
                far_shoulder_slab_region("metal", "metal", "salvage plate")]),
    "warden_tender_sash": article(
        "Warden tender's sash - a wide alloy-grey band from shoulder to hip, hand-lettered in white with a litany of maintenance steps. Worn by the Core Choir.",
        DRESS, [sash_region("knit", "matte", "tender sash", "litany sash")]),
    "warden_lamp_brassard": article(
        "Warden lamp brassard - an upper-arm band with a lit teal mark, worn on watch in the segments.",
        DRESS, [brassard_region("leather", "deep", "lamp", "lamp brassard")]),
}

SETS = {
    "warden_command": {"identity": "Core Choir turn-out - a long alloy-grey coat, the signal gorget, the tender's litany sash, the hub token, dark boots.",
                       "articles": ["tank_top", "coat_charcoal", "pants_charcoal", "boots_black",
                                    "warden_signal_gorget", "warden_tender_sash", "warden_hub_token", "hair_short"]},
    "warden_security": {"identity": "Segment-warden watch kit - work suit, salvage pauldrons, the signal gorget, a lamp brassard, a visor.",
                        "articles": ["tank_top", "jacket_navy", "pants_navy", "boots_charcoal", "visor_ice",
                                     "warden_salvage_pauldrons", "warden_signal_gorget", "warden_lamp_brassard"]},
    "warden_dock": {"identity": "Warden salvage-crew kit - heavy work suit, salvage pauldrons, gloves, the signal gorget, the hub token.",
                    "articles": ["tank_top", "jacket_dock", "pants_dock", "boots_charcoal", "gloves_dark",
                                 "warden_salvage_pauldrons", "warden_signal_gorget", "warden_hub_token"]},
    "warden_flight": {"identity": "Warden courier kit - work suit, flight helmet, the signal gorget, the hub token.",
                      "articles": ["tank_top", "jacket_olive", "pants_field", "boots_charcoal", "helmet_flight",
                                   "warden_signal_gorget", "warden_hub_token", "hair_short"]},
    "warden_civilian": {"identity": "Warden everyday dress - plain alloy-grey clothes, a soft collar, the signal gorget and hub token every Warden wears from the day they are named.",
                        "articles": ["tank_top", "jacket_civ", "pants", "shoes", "collar",
                                     "warden_signal_gorget", "warden_hub_token", "hair_long"]},
}
ROLE_SET = {"civilian": "warden_civilian", "official": "warden_command", "flight": "warden_flight",
            "security": "warden_security", "dock": "warden_dock"}
write_wardrobe(gfx, PFX, DRESS, ARTICLES, SETS, ROLE_SET)
w(f"{S}/graphics.json", gfx)

# ======================================================================
# 4. HUB ZERO  minimal interior + the ending fork
# ======================================================================
# Hub Zero's exterior (graphics/stations/warden_station.json) is a vast
# smooth arc of the old ringworld, broken at both ends, a blinding teal
# reactor-core suspended at its centre on three salvage-braced spokes. The
# floor plan is that crescent: a curved five-segment Approach Span open at
# both termini (one is where you dock), the round Core Choir cradled above
# its low middle on three column-spokes, and the Wardens' patched habitats
# clinging to the arc's outer edge - the scavenged priesthood in the margins.
HZ_ROOMS = [
    rect(180, 380, 520, 660, "the west terminus"),      # broken end (open)
    rect(460, 470, 820, 710, "the Approach Span"),
    rect(760, 520, 1080, 790, "the Span floor"),         # low middle, under the core
    rect(980, 460, 1360, 710, "the Arrival Span"),      # broken end - ship portal
    rect(1300, 380, 1480, 620, "Segment Four"),
    disc(910, 400, 180, "the Core Choir"),               # the reactor-core chamber
    rect(220, 560, 460, 820, "the Signal-Tender's post"),  # margin habitat
    rect(640, 690, 1000, 960, "the Hub Archive"),          # margin habitat
    rect(1140, 560, 1400, 820, "Segment Four watch"),      # margin habitat
]
HZ_STRUCTURES = [
    {"x": 910, "y": 335, "building_type": "warden_spire"},   # the core, at the head of its chamber
    # the three salvage-braced spokes bridging the Span floor up to the core
    *[{"x": x, "y": 500, "building_type": "pipeline_column"} for x in (800, 910, 1020)],
    # the Hub Archive - a stack of Relay-era log columns
    {"x": 820, "y": 860, "building_type": "warden_housing"},
    *[{"x": x, "y": 780, "building_type": "pipeline_column"} for x in (700, 940)],
    {"x": 300, "y": 470, "building_type": "crates"},          # west terminus
    {"x": 1360, "y": 470, "building_type": "crates"},          # Segment Four
    {"x": 600, "y": 600, "building_type": "pipeline_bench"},
    {"x": 1180, "y": 600, "building_type": "pipeline_bench"},
]
HZ_NPCS = [
    {"name": "First Warden", "x": 910, "y": 400, "role": "magistrate",
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

    {"name": "the Signal-Tender", "x": 320, "y": 700, "role": "quartermaster",
     "faction": "the_wardens", "outfit": "warden_dock_masc",
     "greeting": "We keep the machinery, not a market. A carrier who runs parts to the outer segments is always welcome - and we are always short of parts.",
     "shop": {"type": "commodities", "stock": ["hub_parts", "salvage"], "sell_multiplier": 1.1}},

    {"name": "Keeper of the Hub", "x": 1260, "y": 700, "role": "resident",
     "faction": "the_wardens", "outfit": "warden_civilian_femme",
     "greeting": "Segment Four was dark since before my grandmother tended it. Now its lights come up one by one, and none of us set them to. The Hub is finishing something. We only keep it swept.",
     "dialogue_options": ["Understood", "Leave"]},

    {"name": "Warden of the Fourth Segment", "x": 640, "y": 600, "role": "guard",
     "faction": "the_wardens", "outfit": "warden_security_masc",
     "dialogue_tree": {"root": "start",
        "conditional_roots": [{"flag": "span_hailed", "node": "acknowledged"}],
        "nodes": {
        "start": {"text": "You are inside the Span. The Hub hears you. Mind that it does - it has been listening a long time, for whoever came last.",
                  "options": [{"label": "Understood", "next": None}]},
        "acknowledged": {"text": "The Hub keyed the beacon to your transponder before you cleared Ossuary - it has been expecting you by name for days. We do not know how it decided you were the one. We only opened the lane it asked us to open.",
                         "options": [{"label": "Understood", "next": None}]}}}},

    # The Hub Archive - the shutdown reason as a *place*, not only a dialogue
    # reveal in the_vigil_record. The machine's own logs give the same three
    # explanations, from the other end. Sets read_hub_archive.
    {"name": "Archivist of the Choir", "x": 700, "y": 800, "role": "clerk",
     "faction": "the_wardens", "outfit": "warden_official_masc",
     "dialogue_tree": {"root": "start", "nodes": {
        "start": {"text": "The Archive is the Hub's own memory of the night it went dark. Not the Vigil's account of it - the machine's. Three logs from that last hour, and they do not agree. The Choir has read them for two hundred years and is no closer. Read them yourself; you are the one it is asking.",
                  "options": [
                      {"label": "Read the first log.", "next": "quarantine"},
                      {"label": "Read the second log.", "next": "scorched"},
                      {"label": "Read the third log.", "next": "accident"},
                      {"label": "Enough.", "next": None, "action": "set_flag:read_hub_archive"}]},
        "quarantine": {"text": "First log: a containment order, priority absolute. Something crossed the Relay from outside the network and the beacons were cut to strand it between stars. If that is true, relighting them lets it finish the crossing. The log does not say what 'it' was. The field for that is blank - deliberately, the Choir thinks.",
                       "options": [{"label": "The second log.", "next": "scorched"},
                                   {"label": "The third.", "next": "accident"},
                                   {"label": "Enough.", "next": None, "action": "set_flag:read_hub_archive"}]},
        "scorched": {"text": "Second log: a military channel, the last order of a war the histories mostly forgot. The shutdown was the final act - deny the enemy the lanes by killing them for everyone. No monster. Just people, doing the worst arithmetic there is, and two centuries since spent making it a myth so it could be survived.",
                     "options": [{"label": "The first log.", "next": "quarantine"},
                                 {"label": "The third.", "next": "accident"},
                                 {"label": "Enough.", "next": None, "action": "set_flag:read_hub_archive"}]},
        "accident": {"text": "Third log: a fault cascade. A maintenance error at the core, then another, then the network folding one beacon at a time faster than anyone could stop it. No order, no enemy - it simply broke, and everything since has been a religion built in the quiet where an explanation should be. The Choir likes this one least. It is the one with no one to forgive.",
                     "options": [{"label": "The first log.", "next": "quarantine"},
                                 {"label": "The second.", "next": "scorched"},
                                 {"label": "Enough.", "next": None, "action": "set_flag:read_hub_archive"}]}}}},

    {"name": "Choir-hand Emel", "x": 920, "y": 900, "role": "resident",
     "faction": "the_wardens", "outfit": "warden_civilian_masc",
     "greeting": "I sweep the Archive. I have read every log in it. I could not tell you which is true and I have stopped needing to - the Hub will do what it does, and we will keep it swept either way.",
     "dialogue_options": ["Understood", "Leave"]},
]
HZ_INTERIOR = {"label": "Hub Zero", "culture": "the_wardens",
               "portals": [{"x": 1300, "y": 560, "connected_locations": [], "return_to_ship": True}],
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

print(f"The Span: 3 ships, 1 station, 3 buildings, dress + {len(ARTICLES)} articles / {len(SETS)} sets, "
      f"Hub Zero ({len(HZ_ROOMS)} rooms / {len(HZ_NPCS)} NPCs, incl. the Archive) with the ending fork, {len(pilots)} pilots.")
