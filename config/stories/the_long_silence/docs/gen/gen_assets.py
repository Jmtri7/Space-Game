"""Phase 6 asset-stub generator for the_long_silence.

Produces one distinct, named, per-culture stub for every graphic asset the
story uses: a ship palette + a dress palette per culture, a per-culture
moon, 3 ships + 1 station + 3 buildings per culture, and per-culture person
outfits. Geometry is BORROWED (the existing courier / trade_ring /
market_hall / housing_block / admin_office designs) but each stub gets its
own file, its own catalogue entry, and a written `identity` brief derived
from that culture's `cultures.json` theme - so each is ready to shape in
config/editor.html knowing what it should be.

Idempotent: rewrites ship_types.json, building_types.json, the graphics.json
catalogue, and the graphics/palettes|ships|stations|buildings design files.
Furniture (bench/planter/lamp) stays the shared pipeline set for now.
"""
import json, os, copy

S = "config/stories/the_long_silence"
G = f"{S}/graphics"


def load(p):
    with open(p) as f:
        return json.load(f)


def dump(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2)


def hexof(rgb, mul=1.0):
    return "#" + "".join(f"{max(0, min(255, round(c * mul))):02x}" for c in rgb)


cultures = load(f"{S}/cultures.json")

COURIER_LOCAL = [[0.0, -1.1], [0.4, 0.05], [0.92, 0.9], [0.35, 1.12], [-0.35, 1.12], [-0.92, 0.9], [-0.4, 0.05]]
RING_LOCAL = [[0.0, -51.52], [15.64, -43.24], [35.88, -35.88], [43.24, -15.64], [51.52, 0.0],
              [43.24, 15.64], [35.88, 35.88], [15.64, 43.24], [0.0, 51.52], [-15.64, 43.24],
              [-35.88, 35.88], [-43.24, 15.64], [-51.52, 0.0], [-43.24, -15.64], [-35.88, -35.88], [-15.64, -43.24]]

# prefix used in every asset id  ·  human adjective  ·  theme keywords for briefs
CULTURE = {
    "harbor_authority": ("authority", "Harbor Authority",
        "orderly and symmetrical, chrome-and-navy livery, evenly ranked windows, a docking-guidance chevron on every surface, over-signed"),
    "ninefold_combine": ("combine", "Ninefold Combine",
        "heavy dark iron banded with ember-orange hazard light, blast doors, riveted seams, ration-stencil numerals, built for the deep mines"),
    "the_drift": ("drift", "the Drift",
        "soft and rounded, curved partitions, trellised grow-light, growing things worked into the structure, pale timber-and-canvas over a green cast"),
    "the_vigil": ("vigil", "the Vigil",
        "austere and vertical, long cold surfaces, narrow violet-white light, unpolished grey, no decoration that is not a record"),
    "the_wardens": ("warden", "the Wardens",
        "vast smooth Relay-era forms in dark alloy and teal light, patched with mismatched salvage and hand-lettered ritual markings"),
    "free_carrier": ("carrier", "the free carriers",
        "patchwork - mismatched hull segments welded into one working whole, cargo lashing everywhere, a hand-painted name"),
}

SHIPS = {
    "courier": ("Courier", "a small fast dispatch hull",
                dict(max_thrust=0.17, max_velocity=3.8, rotation_speed=4.2, size=11, cargo_capacity=14, max_health=24, cost=7000)),
    "hauler": ("Hauler", "a mid-weight cargo hull, slow to turn",
               dict(max_thrust=0.11, max_velocity=2.4, rotation_speed=2.3, size=20, cargo_capacity=55, max_health=58, cost=26000)),
    "patrol": ("Patrol", "an armed patrol / warship hull",
               dict(max_thrust=0.30, max_velocity=4.6, rotation_speed=4.4, size=16, cargo_capacity=14, max_health=70, cost=52000)),
}

BUILDINGS = {
    "hall": ("Hall", "buildings/market_hall", dict(width=112, depth=30.0),
             "the public / trading hall - the culture's front room, seen head-on"),
    "housing": ("Housing", "buildings/housing_block", dict(width=96, depth=28.0),
                "a residential block - where the culture's people actually live"),
    "spire": ("Spire", "buildings/admin_office", dict(width=70, depth=24.0),
              "the landmark - an administrative / ceremonial tower that says whose ground this is"),
}

# outfit role -> (existing set, body-neutral label)
OUTFITS = {
    "civilian": ("ck_civilian", "everyday civilian dress"),
    "official": ("civilian_officer", "an official / command uniform"),
    "flight": ("ck_flight", "a pilot's flight suit"),
    "security": ("ck_security", "a guard / security kit"),
    "dock": ("ck_dockworker", "dock / labour work gear"),
}

# ---------------------------------------------------------------- palettes
for cid, (pfx, adj, theme) in CULTURE.items():
    c = cultures[cid]
    m, gl, th, wt = c["metal_color"], c["glass_color"], c["thrust_color"], c["wall_trim_color"]
    dump(f"{G}/palettes/{pfx}.json", {
        "identity": f"{adj} ship palette - {theme}. Hull from the culture's metal, glass from its light, a distinct thruster glow.",
        "hull": hexof(m), "hull_dk": hexof(m, 0.62), "engine": hexof(m, 0.42),
        "metal": hexof(m, 0.85), "glass": hexof(gl), "lamp": hexof(gl, 0.9), "thrust": hexof(th),
    })
    civ = load(f"{G}/palettes/civilian.json")
    civ["identity"] = f"{adj} dress palette - human tones, cloth pulled toward the culture's colours ({theme})."
    civ["cloth"] = hexof(wt)
    civ["denim"] = hexof(m, 0.55)
    civ["knit"] = hexof(wt, 0.8)
    civ["leather"] = hexof(m, 0.5)
    civ["metal"] = hexof(m, 0.9)
    civ["glass"] = hexof(gl)
    civ["lamp"] = hexof(gl, 0.9)
    dump(f"{G}/palettes/{pfx}_dress.json", civ)

# ---------------------------------------------------------------- ships
base_ship = load(f"{G}/ships/courier.json")
ship_types = {"_comment": "Phase 6 stubs - per-culture ships. Geometry still borrowed from the courier design; each has its own design file + identity to shape in config/editor.html."}
gfx = load(f"{S}/graphics.json")
gfx_ships = {}
for cid, (pfx, adj, theme) in CULTURE.items():
    for kind, (klabel, kdesc, stats) in SHIPS.items():
        sid = f"{pfx}_{kind}"
        design = copy.deepcopy(base_ship)
        design["identity"] = (f"{adj} {klabel} - {kdesc}. STYLE: {theme}. "
                              f"(Geometry is a placeholder copy of the civilian courier - reshape.)")
        design["palette"] = pfx
        design["size"] = stats["size"]
        dump(f"{G}/ships/{sid}.json", design)
        gfx_ships[sid] = {"design": f"ships/{sid}", "culture": cid, "size": stats["size"],
                          "local_points": COURIER_LOCAL, "thrusters": [[0.56, 0.92], [-0.56, 0.92]],
                          "thruster_width": 0.07, "thruster_length": 22}
        ship_types[sid] = {
            "name": f"{klabel} ({adj})",
            "description": f"{adj[0].upper() + adj[1:]} {klabel.lower()} - {kdesc}.",
            "max_thrust": stats["max_thrust"], "max_velocity": stats["max_velocity"],
            "rotation_speed": stats["rotation_speed"], "size": stats["size"],
            "cargo_capacity": stats["cargo_capacity"], "max_health": stats["max_health"],
            "cost": stats["cost"], "color": cultures[cid]["metal_color"], "shape": "triangle",
            "slots": [
                {"id": "weapon_1", "type": "weapon", "x": 0.5, "y": 0.18},
                {"id": "engine_1", "type": "engine", "x": 0.5, "y": 0.88},
                {"id": "utility_1", "type": "utility", "x": 0.5, "y": 0.55},
            ] + ([{"id": "weapon_2", "type": "weapon", "x": 0.5, "y": 0.36},
                  {"id": "utility_2", "type": "utility", "x": 0.65, "y": 0.55}] if kind != "courier" else []),
        }
dump(f"{S}/ship_types.json", ship_types)

# ---------------------------------------------------------------- stations
base_station = load(f"{G}/stations/trade_ring.json")
gfx_stations = {}
for cid, (pfx, adj, theme) in CULTURE.items():
    sid = f"{pfx}_station"
    d = copy.deepcopy(base_station)
    d["identity"] = (f"{adj} station - the culture's main orbital dock. STYLE: {theme}. "
                     f"(Geometry is a placeholder copy of the civilian trade ring - reshape.)")
    d["palette"] = pfx
    dump(f"{G}/stations/{sid}.json", d)
    gfx_stations[sid] = {"design": f"stations/{sid}", "culture": cid, "size": 46,
                         "rotation_speed": 0.3, "landing_distance": 150,
                         "local_points": RING_LOCAL, "windows": []}

# ---------------------------------------------------------------- moons
gfx_moons = {}
for cid, (pfx, adj, theme) in CULTURE.items():
    c = cultures[cid]
    base = [int((f + w) / 2) for f, w in zip(c["floor_color"], c["metal_color"])]
    gfx_moons[f"{pfx}_moon"] = {
        "name": f"{adj} moon",
        "size": 30, "color": base,
        "crater_color": [max(0, x - 30) for x in base],
        "landing_distance": 35,
        "craters": [{"x": -8, "y": -4, "radius": 4}, {"x": 9, "y": 7, "radius": 5}, {"x": 3, "y": -9, "radius": 3}],
    }

# ---------------------------------------------------------------- buildings
building_types = {"_comment": "Phase 6 stubs - per-culture structures. Geometry borrowed (market_hall / housing_block / admin_office); furniture (pipeline_bench/planter/lamp_post) stays shared. Each has its own design file + identity."}
# keep the shared furniture entries
old_bt = load(f"{S}/building_types.json")
for k in ("pipeline_bench", "pipeline_column", "planter", "lamp_post", "crates"):
    if k in old_bt:
        building_types[k] = old_bt[k]
for cid, (pfx, adj, theme) in CULTURE.items():
    for kind, (klabel, borrow, fp, brief) in BUILDINGS.items():
        bid = f"{pfx}_{kind}"
        d = load(f"{G}/{borrow}.json")
        d = copy.deepcopy(d)
        d["identity"] = (f"{adj} {klabel} - {brief}. STYLE: {theme}. "
                         f"(Geometry is a placeholder copy of {borrow.split('/')[-1]} - reshape.)")
        d["palette"] = pfx
        dump(f"{G}/buildings/{bid}.json", d)
        cap = adj[0].upper() + adj[1:]
        building_types[bid] = {
            "culture": cid,
            "name": f"{cap} {klabel}",
            "description": f"{cap} {klabel.lower()} - {brief}. See buildings/{bid}.json.",
            "design": f"buildings/{bid}",
            "footprint": {"width": fp["width"], "depth": fp["depth"]},
        }
dump(f"{S}/building_types.json", building_types)

# ---------------------------------------------------------------- outfits
gfx_outfits = {}
# keep the borrowed generic ck_*/civilian_* outfits (unaffiliated NPCs still use them)
for k, v in gfx["outfits"].items():
    gfx_outfits[k] = v
for cid, (pfx, adj, theme) in CULTURE.items():
    for role, (setname, label) in OUTFITS.items():
        for body in ("femme", "masc"):
            gfx_outfits[f"{pfx}_{role}_{body}"] = {
                "body": f"human_{body}", "set": setname, "palette": f"{pfx}_dress",
            }

# ---------------------------------------------------------------- graphics.json
gfx["_comment"] = "Phase 6 stubs. Per-culture ships/stations/moons/outfits; each design file carries an identity brief. Geometry is placeholder (borrowed) until authored in config/editor.html."
gfx["ships"] = gfx_ships
gfx["space_stations"] = gfx_stations
gfx["moons"] = gfx_moons
gfx["outfits"] = gfx_outfits
dump(f"{S}/graphics.json", gfx)

print("ships:", len(gfx_ships), "| stations:", len(gfx_stations), "| moons:", len(gfx_moons),
      "| buildings:", len([k for k in building_types if not k.startswith(('_', 'pipeline_', 'planter', 'lamp_post', 'crates'))]),
      "| outfits:", len(gfx_outfits), "| palettes:", len(CULTURE) * 2)
