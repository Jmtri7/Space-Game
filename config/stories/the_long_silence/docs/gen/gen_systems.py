import json, os

OUT = "config/stories/the_long_silence/systems"
os.makedirs(OUT, exist_ok=True)

# Phase 0 scaffold. Art borrowed from graphics_pipeline_test (design-JSON
# pipeline): station=trade_ring, moon=regolith_moon, ship=courier, ck_*/civilian_*
# outfits, pipeline_* / regolith building_types. Per-system culture palettes are
# real (cultures.json); the furniture/hull art is grey placeholder until Phase 6.

STATION_ASSET = "trade_ring"
MOON_ASSET = "regolith_moon"
SHIP = "courier"


def dock_portal():
    # Must sit INSIDE the walkable area - the player spawns on portal[0].
    # Concourse rooms below are a circle centred (800, 640); (800, 430) is
    # well inside and reads as the dock doorway at the north edge.
    return [{"x": 800, "y": 430, "connected_locations": [], "return_to_ship": True}]


def simple_room(label):
    return [{"label": label, "shape": "circle", "center": [800, 640], "radius": 320, "sides": 40}]


def moon_block(name, culture, city_label):
    return {
        "name": name,
        "x": 0.82, "y": 0.78, "size": 30, "color": [170, 170, 180],
        "crater_color": [130, 130, 140], "landing_distance": 35,
        "craters": [{"x": -8, "y": -5, "radius": 4}, {"x": 10, "y": 8, "radius": 5}],
        "interiors": {
            "city": {
                "label": city_label, "culture": culture,
                "connected_locations": [], "entrance": {"x": 800, "y": 800},
                "rooms": [{"label": city_label, "shape": "circle", "center": [800, 800], "radius": 300, "sides": 40}],
                "structures": [
                    {"x": 800, "y": 620, "building_type": "market_hall"},
                    {"x": 620, "y": 760, "building_type": "housing_block"},
                    {"x": 980, "y": 760, "building_type": "housing_block"},
                    {"x": 700, "y": 960, "building_type": "planter"},
                    {"x": 900, "y": 960, "building_type": "crates"},
                    {"x": 640, "y": 640, "building_type": "lamp_post"},
                    {"x": 960, "y": 640, "building_type": "lamp_post"},
                ],
                "npcs": [
                    {"name": "Surface Warden", "x": 800, "y": 900, "role": "resident",
                     "faction": culture,
                     "outfit": "ck_miner_masc", "greeting": "Nothing out here but us and the dust. Watch your seals.",
                     "dialogue_options": ["Understood", "Leave"]},
                ],
            }
        },
    }


def ai_ships(faction, entries):
    # Every scaffold ship flies the station<->moon route so its routine
    # (OrbitRoutine for a patrol_officer pilot, DockRoutine for a
    # freighter_pilot) actually does something - see the_long_silence
    # pilots.json. Real rosters/routes come in Phase 6.
    return [{"name": nm, "x": x, "y": y, "ship_type": SHIP, "pilot": pilot,
             "faction": fac or faction, "route": ["station", "moon"]}
            for nm, pilot, x, y, *rest in entries for fac in [rest[0] if rest else None]]


# ---------------------------------------------------------------- Halcyon (start)
halcyon = {
    "name": "Halcyon",
    "description": "A cluster of well-kept orbital stations around a yellow star, run by the Harbor Authority - the descendants of the Relay's traffic controllers. The first beacon to relight.",
    "star_map_position": {"x": 0, "y": 0},
    "station_asset": STATION_ASSET,
    "moon_asset": MOON_ASSET,
    "central_star": {"x": 0.5, "y": 0.5, "name": "Halcyon", "size": 100, "color": [255, 240, 150]},
    "player_start": {"x": 0.4, "y": 0.35},
    "star_seed": 101,
    "asteroid_field": {"per_chunk_range": [1, 3], "types": [
        {"type": "gray_rock", "weight": 3, "size_range": [4, 18], "speed_range": [0.05, 0.3], "mine_yield": 10},
        {"type": "brown_rock", "weight": 1, "size_range": [6, 25], "speed_range": [0.05, 0.25], "mine_yield": 15},
    ]},
    "station": {
        "x": 0.15, "y": 0.2, "name": "Hub Control",
        "interiors": {
            "default": {
                "label": "Hub Control", "culture": "harbor_authority",
                "portals": dock_portal(),
                "rooms": [
                    {"label": "Approach Concourse", "shape": "circle", "center": [800, 640], "radius": 320, "sides": 40},
                    {"label": "Lender's Office", "shape": "circle", "center": [300, 640], "radius": 200, "sides": 32},
                    {"label": "West Passage", "polygon": [[470, 580], [590, 580], [590, 700], [470, 700]]},
                    {"label": "The Berth", "shape": "circle", "center": [1300, 640], "radius": 210, "sides": 32},
                    {"label": "East Passage", "polygon": [[1010, 580], [1130, 580], [1130, 700], [1010, 700]]},
                ],
                "structures": [
                    {"x": 800, "y": 600, "building_type": "pipeline_column"},
                    {"x": 700, "y": 820, "building_type": "pipeline_bench"},
                    {"x": 900, "y": 820, "building_type": "pipeline_bench"},
                ],
                "npcs": [
                    {"name": "Controller Vane", "x": 800, "y": 520, "role": "stationmaster",
                     "faction": "harbor_authority", "outfit": "officer_femme",
                     "dialogue_tree": {"root": "start", "conditional_roots": [
                         {"faction": "harbor_authority", "min": 20, "node": "warm"}],
                      "nodes": {
                         "start": {"text": "Harbor Authority, Hub Control. Beacon 1 is live again - which is why you're here, and why the outer systems are about to have company. Fly our beacons and log what you find, and the Authority remembers it. Kiln's the nearest dark lane - say the word and I'll key our beacon to reach it.",
                                   "options": [
                                       {"label": "Light the lane to Kiln.", "next": "signed", "requires_not_flag": "vane_signed_on",
                                        "actions": ["set_flag:vane_signed_on", "adjust_rep:harbor_authority:6", "light_beacon:kiln"]},
                                       {"label": "Just passing through.", "next": None}]},
                         "signed": {"text": "Logged - Kiln's beacon is live. The Berth's east for a hull, the Lender's Office west for the credits to buy one.",
                                    "options": [{"label": "Understood", "next": None}]},
                         "warm": {"text": "Good to see one of ours on the approach. The outer beacons are yours to run - Hub Control has your back. If you mean that, say so, and the Authority will hold the network for all of us.",
                                  "options": [
                                      {"label": "Pledge the Authority your beacons.", "next": "pledged",
                                       "requires_not_flag": "patron:harbor_authority",
                                       "actions": ["set_exclusive_flag:patron:harbor_authority", "adjust_rep:harbor_authority:8"]},
                                      {"label": "Appreciated", "next": None}]},
                         "pledged": {"text": "Logged, and remembered. When the Span asks its question, you'll answer for the Authority.",
                                     "options": [{"label": "Understood", "next": None}]}}}},
                    {"name": "Signal Officer Doss", "x": 300, "y": 620, "role": "loan_officer",
                     "faction": "harbor_authority", "outfit": "ck_command_masc",
                     "dialogue_tree": {"root": "start", "nodes": {
                         "start": {"text": "Authority underwrites a starter loan for anyone flying our beacons. More than enough for a hull.",
                                   "options": [
                                       {"label": "Take loan - 100000cr", "next": "loaned", "action": "take_loan"},
                                       {"label": "Leave", "next": None}]},
                         "loaned": {"text": "Logged. The beacons keep our ledgers now - don't make us come find you.",
                                    "options": [{"label": "Thanks", "next": None}]}}}},
                    {"name": "Harbor-Master Crane", "x": 1290, "y": 600, "role": "ship_salesman",
                     "faction": "harbor_authority", "outfit": "ck_command_femme",
                     "greeting": "Impounded hulls, mostly - carriers who couldn't pay their approach fees. Cleared for sale.",
                     "shop": {"type": "ships", "stock": ["shuttle", "courier", "hauler", "interceptor", "liner"]}},
                    {"name": "Approach Warden Lund", "x": 1300, "y": 700, "role": "outfitter",
                     "faction": "harbor_authority", "outfit": "ck_security_masc",
                     "greeting": "Fitting out? Standard-issue only, but it's all rated.",
                     "shop": {"type": "outfits", "stock": ["laser_cannon", "pulse_blaster", "afterburner", "cargo_expansion", "reinforced_hull"]}},
                    {"name": "Quartermaster Ellin", "x": 640, "y": 700, "role": "quartermaster",
                     "faction": "harbor_authority", "outfit": "ck_dockworker_femme",
                     "greeting": "Bring me goods off the outer beacons and I'll pay Hub rates.",
                     "shop": {"type": "commodities", "stock": ["relief_supplies", "salvage"], "sell_multiplier": 1.2}},
                    {"name": "Rell, carrier pilot", "x": 900, "y": 720, "role": "traveler",
                     "faction": "free_carrier", "outfit": "ck_smuggler_masc",
                     "greeting": "Twenty years I ran the slow lanes to Verdance. Now a beacon does it in an afternoon. Don't know whether to celebrate.",
                     "dialogue_options": ["Safe flights", "Leave"]},
                    # Flag-conditional (Phase 4): only appears once Verdance's
                    # beacon is lit - the outer systems reaching Halcyon on
                    # the half-restored network.
                    {"name": "Displaced traveller", "x": 620, "y": 560, "role": "traveler",
                     "faction": "free_carrier", "outfit": "civilian_femme",
                     "requires_flag": "beacon_verdance_lit",
                     "greeting": "Came in on the new lane from Verdance. Half the ring's doing the same. Nobody planned for this.",
                     "dialogue_options": ["Safe travels", "Leave"]},
                ],
            }
        },
    },
    "moon": moon_block("Halcyon Watch", "harbor_authority", "Watch Station"),
    "celestial_bodies": [
        {"name": "Sentinel", "x": 0.6, "y": 0.55, "size": 16, "color": [180, 160, 140], "body_type": "rocky"},
        {"name": "Verge", "x": 0.08, "y": 0.9, "size": 46, "color": [225, 200, 150], "body_type": "gas_giant", "has_ring": True, "ring_color": [200, 190, 160]},
    ],
    "ai_ships": ai_ships("harbor_authority", [
        ("Hub Patrol", "ackley", 0.5, 0.12),
        ("Authority Freight", "lund", 0.65, 0.6),
        ("Ferro's Slip", "rell", 0.3, 0.55, "free_carrier"),
    ]),
}


def beacon_host(host_name, faction, greeting, next_system, next_name, on_light=()):
    """A default outer-system host dialogue: on first talk they point you at
    the next dark beacon and relight it (light_beacon:), so the scaffold
    chain is traversable before the Phase 6 anchor missions exist.
    `on_light` is extra actions to run alongside (e.g. an act advance)."""
    if not next_system:
        return {"greeting": greeting, "dialogue_options": ["Understood", "Leave"]}
    return {"dialogue_tree": {"root": "start", "conditional_roots": [
                {"flag": f"beacon_{next_system}_told", "node": "already"}],
        "nodes": {
            "start": {"text": greeting + f" The Relay signal is already reaching for {next_name} - I can key our beacon to pass it on, if you mean to go there.",
                      "options": [
                          {"label": f"Light the lane to {next_name}.", "next": "lit",
                           "actions": [f"set_flag:beacon_{next_system}_told", f"light_beacon:{next_system}", *on_light]},
                          {"label": "Not yet.", "next": None}]},
            "lit": {"text": f"Done. {next_name}'s beacon is live. Mind what you carry through it.",
                    "options": [{"label": "Understood", "next": None}]},
            "already": {"text": f"{next_name}'s lane is open. Safe transit.",
                        "options": [{"label": "Thanks", "next": None}]}}}}


# ---------------------------------------------------------------- outer systems
def outer_system(name, desc, smp, seed, culture, station_name, city, star_color, npc,
                 locked=False, unlock_flag=None):
    sysdict = {
        "name": name, "description": desc, "star_map_position": smp,
        "station_asset": STATION_ASSET, "moon_asset": MOON_ASSET,
        "central_star": {"x": 0.5, "y": 0.5, "name": name, "size": 90, "color": star_color},
        "player_start": {"x": 0.4, "y": 0.35}, "star_seed": seed,
        "asteroid_field": {"per_chunk_range": [1, 3], "types": [
            {"type": "gray_rock", "weight": 3, "size_range": [4, 18], "speed_range": [0.05, 0.3], "mine_yield": 10}]},
        "station": {
            "x": 0.2, "y": 0.25, "name": station_name,
            "interiors": {"default": {
                "label": station_name, "culture": culture,
                "portals": dock_portal(), "rooms": simple_room("Concourse"),
                "structures": [
                    {"x": 800, "y": 620, "building_type": "pipeline_column"},
                    {"x": 650, "y": 820, "building_type": "pipeline_bench"},
                    {"x": 950, "y": 820, "building_type": "pipeline_bench"},
                ],
                "npcs": [
                    dict({"name": npc["host"][0], "x": 800, "y": 540, "role": "stationmaster",
                          "faction": culture, "outfit": "officer_masc"},
                         **(npc.get("host_extra")
                            or beacon_host(npc["host"][0], culture, npc["host"][1],
                                           *(npc.get("next") or (None, None)),
                                           on_light=npc.get("next_on_light", ())))),
                    {"name": npc["trader"][0], "x": 650, "y": 700, "role": "quartermaster",
                     "faction": culture, "outfit": "ck_dockworker_masc", "greeting": npc["trader"][1],
                     "shop": {"type": "commodities", "stock": npc.get("trader_stock", []), "sell_multiplier": 1.15}},
                    {"name": npc["local"][0], "x": 960, "y": 700, "role": "resident",
                     "faction": culture, "outfit": "civilian_femme", "greeting": npc["local"][1],
                     "dialogue_options": ["I see", "Leave"]},
                    *npc.get("extra_npcs", []),
                ],
            }},
        },
        "moon": moon_block(city, culture, city),
        "celestial_bodies": [
            {"name": name + " b", "x": 0.62, "y": 0.5, "size": 18, "color": [160, 140, 130], "body_type": "rocky"}],
        "ai_ships": ai_ships(culture, [(npc["ship"][0], npc["ship"][1], 0.6, 0.55),
                                       (npc["ship2"][0], npc["ship2"][1], 0.35, 0.2)]),
    }
    if locked:
        sysdict["locked"] = True
        sysdict["unlock_flag"] = unlock_flag
    return sysdict


kiln = outer_system(
    "Kiln", "A red-dwarf system, one scorched world, deep-mine settlements under the moons. The Ninefold Combine rations everything and does not want the Relay back.",
    {"x": 260, "y": -40}, 202, "ninefold_combine", "Combine Hold", "Shaft VII", [255, 150, 110],
    {"host": ("Factor Tol", ""),
     "host_extra": {"dialogue_tree": {"root": "start", "nodes": {
             "start": {"text": "You're on Combine ground. Every transaction here is a contract, and we did not sign one with a beacon. State your business.",
                       "options": [
                           {"label": "I'm passing through - and heading for Verdance.", "next": "civil",
                            "requires_not_flag": "beacon_verdance_told",
                            "actions": ["set_flag:beacon_verdance_told", "light_beacon:verdance", "adjust_rep:ninefold_combine:4"]},
                           {"label": "The Authority is opening this system with or without your consent.", "next": "threatened",
                            "action": "adjust_rep:ninefold_combine:-50"},
                           {"label": "Nothing. Leaving.", "next": None}]},
             "civil": {"text": "Then be quick and be gone. Verdance's lane is keyed - the Combine will note that you asked politely.",
                       "options": [{"label": "Understood", "next": None}]},
             "threatened": {"text": "Then the contract is void, and so is your safe conduct. Clear our space.",
                            "options": [{"label": "Leave", "next": None}]}}}},
     "trader": ("Tallykeeper Vess", "Ore and rationed goods. Combine rates, non-negotiable - that's the point of them."),
     "trader_stock": ["alloy", "ore"],
     "extra_npcs": [{"name": "Deck-chief Marn", "x": 800, "y": 780, "role": "ship_salesman",
                     "faction": "ninefold_combine", "outfit": "ck_command_femme",
                     "greeting": "Combine hulls. Built heavy, priced by the contract. What's your trade need?",
                     "shop": {"type": "ships", "stock": ["hauler", "miner", "gunship", "freighter"]}}],
     "local": ("Deep-hand Corr", "Air's metered by the shift down here. You get used to counting breaths."),
     "ship": ("Combine Watch", "tolvic"), "ship2": ("Ore Run", "corran")},
    locked=True, unlock_flag="beacon_kiln_lit")

verdance = outer_system(
    "Verdance", "A gas giant with one enormous cloud-city and a ring of farm habitats. The Drift runs on rolling consensus and can't quite decide anything.",
    {"x": 210, "y": 150}, 203, "the_drift", "Highcanopy", "the Undergarden", [255, 230, 160],
    {"host": ("Sela of Highcanopy", "Welcome, welcome. There's no one in charge here exactly - if you need a decision, the assembly's rolling in the Undergarden. Might take a while."),
     "next": ("ossuary", "Ossuary"),
     "next_on_light": ["set_flag:act_pressure"],
     "trader": ("Seed-warden Nim", "Grain, fibre, water-credits. Pay what's fair and we'll trade again."),
     "trader_stock": ["grain", "water_credits"],
     "extra_npcs": [{"name": "Ferry-wright Osei", "x": 800, "y": 780, "role": "ship_salesman",
                     "faction": "the_drift", "outfit": "ck_command_masc",
                     "greeting": "We refit liners and passenger hulls, mostly. Roomy. Slow. Kind to fly.",
                     "shop": {"type": "ships", "stock": ["shuttle", "liner", "hauler"]}}],
     "local": ("Wander-from traveler", "The beacon relit and half of us are thrilled and half are terrified. That's Verdance for you."),
     "ship": ("Drift Watch", "sella"), "ship2": ("Canopy Hauler", "nim")},
    locked=True, unlock_flag="beacon_verdance_lit")

ossuary = outer_system(
    "Ossuary", "A dead system - one habitable moon, abandoned stations, and the Vigil: a few hundred who stayed to keep the graves and the archives.",
    {"x": 40, "y": 260}, 204, "the_vigil", "the Name-Wall", "Vault of the First Decade", [200, 200, 230],
    {"host": ("Keeper Aramis", ""),
     "host_extra": {"dialogue_tree": {
         "root": "start",
         "conditional_roots": [{"faction": "the_vigil", "min": 25, "node": "trusted"}],
         "nodes": {
             "start": {"text": "You've come to the Name-Wall. Everyone the first decade of the Silence killed is written here. We believe the Relay went dark to keep something out - and that relighting it is a mistake.",
                       "options": [
                           {"label": "Tell me what you know.", "next": "listen",
                            "actions": ["set_flag:vigil_heard_warning", "adjust_rep:the_vigil:5"]},
                           {"label": "The Authority sent me to reopen the beacons.", "next": "cold",
                            "requires_not_flag": "vigil_heard_warning", "action": "adjust_rep:the_vigil:-8"},
                           {"label": "Leave", "next": None}]},
             "listen": {"text": "Read the wall. Two hundred years of names, and every account agrees the shutdown was deliberate. If you must go to the Span, then go knowing that - and I'll pass the signal on to the core myself.",
                        "options": [{"label": "Do it.", "next": "toldspan",
                                     "actions": ["set_flag:beacon_the_span_told", "light_beacon:the_span", "set_flag:act_span"]},
                                    {"label": "I'll think on it.", "next": None}]},
             "toldspan": {"text": "The Span's beacon is live. May you choose better than they did.",
                          "options": [{"label": "Understood", "next": None}]},
             "cold": {"text": "Of course they did. Then we have nothing further to discuss.",
                      "options": [{"label": "Leave", "next": None}]},
             "trusted": {"text": "You've been honest with us, and it's noted. The archive's inner vault is open to you now - what the First Decade recorded is not for everyone. And if you'll carry our caution to the Span, say so.",
                         "options": [
                             {"label": "Ask about the inner vault", "next": "vault", "requires_rep": "the_vigil:25"},
                             {"label": "Pledge the Vigil your caution.", "next": "pledged",
                              "requires_not_flag": "patron:the_vigil",
                              "action": "set_exclusive_flag:patron:the_vigil"},
                             {"label": "Later", "next": None}]},
             "vault": {"text": "Later. When the Span's beacon lights and you have to choose - come back, and I'll show you what the Wardens have forgotten.",
                       "options": [{"label": "Understood", "next": None}]},
             "pledged": {"text": "Then you'll speak for the dead when the Hub asks. Choose as if they were listening.",
                         "options": [{"label": "I will", "next": None}]}}}},
     "trader": ("Warden of Names Vane", "We trade only what we can spare - archive copies, mostly. Knowledge, if you'll carry it carefully."),
     "trader_stock": ["archive_copies", "relief_supplies"],
     "local": ("Sister of the Vigil", "It's quiet here. We prefer it. The quiet is the point."),
     "ship": ("Vigil Watch", "vane_watch"), "ship2": ("Grave Tender", "oskal")},
    locked=True, unlock_flag="beacon_ossuary_lit")

the_span = outer_system(
    "The Span", "A ringworld fragment around a blue-white star, still powered, sparsely held by the Wardens - a maintenance cult operating Relay-era machinery. The reactivation signal starts here.",
    {"x": 470, "y": 90}, 205, "the_wardens", "Hub Zero", "the Core Choir", [200, 220, 255],
    {"host": ("First Warden", ""),
     "host_extra": {"dialogue_tree": {"root": "start", "nodes": {
         "start": {"text": "You reached the Span. The Hub sings, and it is asking you a question it has asked no one in two hundred years: what should the Relay be? Stand at the Choir and choose. There is no undoing it.",
                   "options": [
                       {"label": "Restore the Relay - one network, run from a hub.", "next": None,
                        "action": "end_story:restore"},
                       {"label": "Sever it. Destroy the core.", "next": None,
                        "action": "end_story:sever"},
                       {"label": "Keep the beacons, break only the hub - no one rules the network.",
                        "next": None, "requires_rep": "the_vigil:10",
                        "requires_not_flag": "patron:harbor_authority",
                        "action": "end_story:hold_middle"},
                       {"label": "Not yet.", "next": None}]}}}},
     "trader": ("Signal-Tender", "We keep the machinery, not a market. But a carrier who runs parts to the outer segments is always welcome."),
     "trader_stock": ["hub_parts", "salvage"],
     "local": ("Keeper of the Hub", "Segment 4 has been dark since before my grandmother tended it. Now its lights are coming up one by one."),
     "ship": ("Segment Patrol", "segment_warden"), "ship2": ("Core Freighter", "threa")},
    locked=True, unlock_flag="beacon_the_span_lit")

# Flag-conditional ship (Phase 4): a Combine raider that shows up over
# Verdance once the player has angered the Ninefold Combine - the Drift
# "least able to commit" while Kiln's ships arrive (see docs/STORY.md).
# Below -40 it (and every Combine ship) also turns hostile via the normal
# threshold; between -20 and -40 it's a menacing patrol.
verdance["ai_ships"].append({
    "name": "Combine Raider", "x": 0.55, "y": 0.45, "ship_type": SHIP,
    "pilot": "raska", "faction": "ninefold_combine",
    "route": ["station", "moon"], "requires_rep_below": "ninefold_combine:-20",
})

# halcyon is NOT written here - it's a finished Phase 6.1 slice owned by
# gen_halcyon.py. This script only regenerates the four stub systems.
for fn, data in [("kiln", kiln), ("verdance", verdance),
                 ("ossuary", ossuary), ("the_span", the_span)]:
    path = os.path.join(OUT, fn + ".json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print("wrote", path)
