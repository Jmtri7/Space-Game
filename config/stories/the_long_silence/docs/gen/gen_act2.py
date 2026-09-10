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
    "on_start_flags": ["relief_run_active"],
    "on_end_flags": ["relief_run_done"],
    "on_end_rep": {"free_carrier": 6, "the_vigil": 3},
    "stages": [
        {"text": "Take the run on - see the carrier off the Slip at the Highcanopy berth (Canopy Walk, by the Ferry Slip).",
         "complete_flag": "relief_run_loaded",
         "one_way_message": one_way("Free carriers", "It's a supply load for the Vigil at Ossuary - our crews pooled it, and it's on the ground at our berth on the Canopy Walk at Highcanopy, over toward the Ferry Slip. Whoever's off the Slip has the manifest. Tie up and take it.")},
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

# Phase 2 - the refugee barge escort. Offered by the drift_convoy_call
# dispatch (dispatches.json) once the Combine has mobilised. escort_flag
# "barge_under_escort" gates the barge ai_ship in BOTH Verdance and Ossuary
# (gen_verdance.py / gen_ossuary.py - escorts don't survive a jump) and is
# auto-cleared by _on_mission_end when the mission ends or is abandoned.
# Stage 0's "hailed_pilot:" string must exactly match the pilot's name.
ESCORT_BARGE = {
    "title": "Forty Families",
    "escort_flag": "barge_under_escort",
    "on_start_flags": ["barge_under_escort"],
    "on_end_flags": ["escort_barge_done"],
    "on_start_rep": {"the_drift": 2},
    "on_end_rep": {"the_drift": 6, "free_carrier": 4},
    "stages": [
        {"text": "Meet the barge Highcanopy-Nine over Verdance and signal ready - hail Barge-mother Sethe.",
         "complete_flag": "hailed_pilot:Barge-mother Sethe",
         "one_way_message": one_way("Sela of Highcanopy", "Barge Highcanopy-Nine is loading now - forty families, everything they could carry. Sethe flies the moment you're alongside and hail her. Stay between her and the Combine.")},
        {"text": "Hold escort to Ossuary - jump when the barge is with you.",
         "complete_flag": "jumped_to:ossuary", "reset_on_activation": True,
         "one_way_message": one_way("Barge-mother Sethe", "We're slow and we're full. Match our speed, keep the blockade off our flank, and jump to Ossuary when we're clear of the Highcanopy shelf. We'll be right behind you.")},
        {"text": "See the barge down at the Name-Wall - land at the Vigil dock.",
         "complete_flag": "landed_on_landing_site", "reset_on_activation": True,
         "one_way_message": one_way("Barge-mother Sethe", "Ossuary. The Vigil keeps a quiet dock and asks nothing - set down at the Name-Wall and they'll take my people in. Land alongside us.")},
        {"text": "Report back to the Drift - jump to Verdance.",
         "complete_flag": "jumped_to:verdance", "reset_on_activation": True,
         "one_way_message": one_way("Sela of Highcanopy", "They're down and safe - word already reached us. Come back to Highcanopy. The assembly should hear it from the pilot who flew it.")},
    ],
}

# Phase 3 - carry the Kiln beacon's handshake logs, then choose who acts on
# them. Linear spine; the fork is three delivery options on existing NPCs
# (Records Keeper Amsel / Sela of Highcanopy / Keeper Aramis), each gated
# requires_flag: front_recon_have_record + requires_not_flag:
# front_recon_delivered, setting one of front_to_{authority,drift,vigil}.
# Stage 1's flag is set by a short option on Assay-clerk Dorn at Combine
# Hold, gated on this mission's on_start_flags marker.
FRONT_RECON = {
    "title": "Reading the Front",
    "on_start_flags": ["front_recon_active"],
    "on_end_flags": ["front_recon_done"],
    "on_start_rep": {"free_carrier": 2},
    "stages": [
        {"text": "Read the front's approach at the Kiln relay - jump to Kiln.",
         "complete_flag": "jumped_to:kiln", "reset_on_activation": True,
         "one_way_message": one_way("Relay Network", "The relight signal handshakes every beacon it passes and the Kiln relay logged the lot. Jump to Kiln - the record is on the ground at Combine Hold.")},
        {"text": "Pull the beacon's own handshake logs - land at Combine Hold, then talk to Assay-clerk Dorn.",
         "complete_flag": "front_recon_have_record",
         "one_way_message": one_way("Relay Network", "Combine Hold weighs everything twice, the signal included. Assay-clerk Dorn keeps the relay tally. Ask for the front's timing - the Combine has no use for it and will part with it cheap.")},
        {"text": "Get the record to someone who'll act on it - jump to Verdance.",
         "complete_flag": "jumped_to:verdance", "reset_on_activation": True,
         "one_way_message": one_way("Relay Network", "You have the front's timing. It is worth something to whoever wants to be ready for it. Verdance is the crossroads - jump there and decide who gets it.")},
        {"text": "Deliver the intelligence - Records Keeper Amsel (Hub Control), Sela of Highcanopy, or Keeper Aramis (the Name-Wall).",
         "complete_flag": "front_recon_delivered",
         "one_way_message": one_way("Relay Network", "Three parties want this. The Authority at Hub Control would run the region on it. The Drift at Highcanopy would open their lanes ahead of it. The Vigil at the Name-Wall would slow it. Choose - you only get to hand it over once.")},
    ],
}

ACT2 = {
    "carrier_relief_run": CARRIER_RELIEF_RUN,
    "combine_evacuation": COMBINE_EVACUATION,
    "escort_barge": ESCORT_BARGE,
    "front_recon": FRONT_RECON,
}

missions = r(f"{S}/missions.json")
missions.update(ACT2)
w(f"{S}/missions.json", missions)

print(f"Act II missions merged: {', '.join(ACT2)} "
      f"(missions.json now has {len([k for k in missions if not k.startswith('_')])})")
