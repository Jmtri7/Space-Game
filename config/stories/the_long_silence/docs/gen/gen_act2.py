"""Act II ("Pressure") missions for the_long_silence.

These are cross-system courier runs the player is handed by *dispatch*
(dispatches.json - the faction-handler inbox, gap F), not by an NPC in a
room, so they don't belong to any one system slice. Their stages use the
generic gameplay-event flags (`jumped_to:<system>`, `landed_on_landing_site`)
with `reset_on_activation`, the same way the induction's flight stages do -
no bespoke dialogue flags, so no new NPCs are needed for this pass.

Merges into missions.json (keeps whatever the slice generators wrote). Run
after the slice chain + gen_carriers. Idempotent.
"""
import json

S = "config/stories/the_long_silence"


def r(path):
    with open(path) as f:
        return json.load(f)


def w(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def one_way(sender, text):
    return {"sender": sender, "text": text}


CARRIER_RELIEF_RUN = {
    "title": "Relief Down the Line",
    "on_end_flags": ["relief_run_done"],
    "on_end_rep": {"free_carrier": 6, "the_vigil": 3},
    "stages": [
        {"text": "Carry the relief load to Ossuary - jump there.",
         "complete_flag": "jumped_to:ossuary", "reset_on_activation": True,
         "one_way_message": one_way("Free carriers", "Load's aboard - grain, water filters, med stock. Ossuary's the Vigil; they won't ask and they won't thank you, but they need it. Jump when you're clear.")},
        {"text": "Land at the Name-Wall and hand the load over.",
         "complete_flag": "landed_on_landing_site", "reset_on_activation": True,
         "one_way_message": one_way("Free carriers", "Set down at the Name-Wall dock. Sister Edda's people will take it from the hold. That's the run.")},
        {"text": "Take word back down the lane - jump to Verdance.",
         "complete_flag": "jumped_to:verdance", "reset_on_activation": True,
         "one_way_message": one_way("Free carriers", "Good. Now back to Verdance - the Drift's still arguing and they should hear it landed. We owe you one, and we pay those.")},
    ],
}

COMBINE_EVACUATION = {
    "title": "Last Hull Out of Kiln",
    "on_end_flags": ["evac_run_done"],
    "on_end_rep": {"ninefold_combine": 3, "free_carrier": 5},
    "stages": [
        {"text": "Jump to Kiln before the Combine seals the lane.",
         "complete_flag": "jumped_to:kiln", "reset_on_activation": True,
         "one_way_message": one_way("Free carriers", "There's a carrier crew still on the ground at Combine Hold - their hull's impounded and the lane's closing around them. Get in there before the patrols lock it down.")},
        {"text": "Dock at Combine Hold and get the stranded crew aboard.",
         "complete_flag": "landed_on_landing_site", "reset_on_activation": True,
         "one_way_message": one_way("Free carriers", "Four of them, light kit, they'll fit. The Combine won't stop a hull that's leaving - it's hulls that stay they have a problem with.")},
        {"text": "Get them clear - jump back to Verdance.",
         "complete_flag": "jumped_to:verdance", "reset_on_activation": True,
         "one_way_message": one_way("Free carriers", "Out. Don't wait for an escort, don't answer a hail, just go. Verdance when you're through.")},
    ],
}

ACT2 = {
    "carrier_relief_run": CARRIER_RELIEF_RUN,
    "combine_evacuation": COMBINE_EVACUATION,
}

missions = r(f"{S}/missions.json")
missions.update(ACT2)
w(f"{S}/missions.json", missions)

print(f"Act II missions merged: {', '.join(ACT2)} "
      f"(missions.json now has {len([k for k in missions if not k.startswith('_')])})")
