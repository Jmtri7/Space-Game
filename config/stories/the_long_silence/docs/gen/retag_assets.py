"""Rewrite the_long_silence system JSONs to reference the Phase 6 per-culture
asset stubs (gen_assets.py output) instead of the shared placeholders.
Run AFTER gen_systems.py + gen_assets.py.

Maps, per a system's culture (and per NPC/ship faction where it differs):
  station_asset  trade_ring        -> <pfx>_station
  moon_asset     regolith_moon     -> <pfx>_moon
  ai ship_type   courier           -> <pfx>_{courier|hauler|patrol}  (by pilot role)
  structures     market_hall etc.  -> <pfx>_{hall|housing|spire}; furniture stays shared
  npc outfit     officer_femme etc.-> <pfx>_{role}_{femme|masc}
"""
import json, glob

S = "config/stories/the_long_silence"
pilots = json.load(open(f"{S}/pilots.json"))

PFX = {
    "harbor_authority": "authority", "ninefold_combine": "combine", "the_drift": "drift",
    "the_vigil": "vigil", "the_wardens": "warden", "free_carrier": "carrier",
}

ROLE_SHIP = {"patrol_officer": "patrol", "freighter_pilot": "hauler", "courier_pilot": "courier"}

ROLE_OUTFIT = {
    "stationmaster": "official", "loan_officer": "official", "ship_salesman": "official",
    "outfitter": "official", "concierge": "official", "magistrate": "official",
    "quartermaster": "dock", "clerk": "dock", "dockworker": "dock", "surface_tech": "dock",
    "guard": "security",
    "pilot": "flight",
    "traveler": "civilian", "resident": "civilian", "roommate": "civilian", "merchant": "civilian",
}

BUILDING = {
    "market_hall": "hall", "housing_block": "housing", "admin_office": "spire",
    "pipeline_column": "spire", "vherathi_spire": "spire", "vherathi_vein_arch": "spire",
}
SHARED_FURNITURE = {"planter", "lamp_post", "crates", "pipeline_bench", "vherathi_bench",
                    "vherathi_lamp", "vherathi_planter"}
FURNITURE_REMAP = {"vherathi_bench": "pipeline_bench", "vherathi_lamp": "lamp_post",
                   "vherathi_planter": "planter"}


def body_of(outfit):
    return "femme" if outfit.endswith("_femme") else "masc"


def retag_structures(structs, pfx):
    for s in structs:
        bt = s.get("building_type")
        if bt in BUILDING:
            s["building_type"] = f"{pfx}_{BUILDING[bt]}"
        elif bt in FURNITURE_REMAP:
            s["building_type"] = FURNITURE_REMAP[bt]


def retag_npcs(npcs, sys_culture):
    for npc in npcs:
        fac = npc.get("faction", sys_culture)
        pfx = PFX.get(fac, PFX[sys_culture])
        role = npc.get("role", "resident")
        out_role = ROLE_OUTFIT.get(role, "civilian")
        old = npc.get("outfit", "civilian_femme")
        npc["outfit"] = f"{pfx}_{out_role}_{body_of(old)}"


for fn in [f for f in glob.glob(f"{S}/systems/*.json") if "halcyon" not in f]:
    s = json.load(open(fn))
    culture = s["station"]["interiors"]["default"]["culture"]
    pfx = PFX[culture]
    s["station_asset"] = f"{pfx}_station"
    s["moon_asset"] = f"{pfx}_moon"

    for iv in s["station"]["interiors"].values():
        retag_structures(iv.get("structures", []), pfx)
        retag_npcs(iv.get("npcs", []), culture)
    for iv in s["moon"]["interiors"].values():
        mpfx = PFX.get(iv.get("culture", culture), pfx)
        retag_structures(iv.get("structures", []), mpfx)
        retag_npcs(iv.get("npcs", []), iv.get("culture", culture))

    for a in s.get("ai_ships", []):
        fac = a.get("faction", culture)
        apfx = PFX.get(fac, pfx)
        role = pilots.get(a.get("pilot", ""), {}).get("role", "courier_pilot")
        a["ship_type"] = f"{apfx}_{ROLE_SHIP.get(role, 'courier')}"

    json.dump(s, open(fn, "w"), indent=2)
    print("retagged", fn.split("/")[-1] or fn)

# ship-shop stock: rewrite in the generated files (they were written by gen_systems)
STOCK = {
    "authority": ["carrier_courier", "authority_courier", "authority_hauler", "carrier_hauler", "authority_patrol"],
    "combine": ["combine_hauler", "combine_courier", "combine_patrol", "carrier_hauler"],
    "drift": ["drift_courier", "drift_hauler", "carrier_courier", "carrier_hauler"],
    "vigil": ["vigil_courier", "carrier_courier", "vigil_hauler"],
    "warden": ["warden_courier", "warden_hauler", "carrier_hauler"],
}
for fn in [f for f in glob.glob(f"{S}/systems/*.json") if "halcyon" not in f]:
    s = json.load(open(fn))
    culture = s["station"]["interiors"]["default"]["culture"]
    pfx = PFX[culture]
    for iv in list(s["station"]["interiors"].values()) + list(s["moon"]["interiors"].values()):
        for npc in iv.get("npcs", []):
            shop = npc.get("shop")
            if shop and shop.get("type") == "ships":
                shop["stock"] = STOCK.get(pfx, ["carrier_courier", "carrier_hauler"])
    json.dump(s, open(fn, "w"), indent=2)
print("shop stock retagged")
