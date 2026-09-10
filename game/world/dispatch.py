"""Story dispatches - faction-handler comms that arrive in the player's
Message Log by "inbox" rather than needing an NPC in the room (the story
design calls this gap F). A dispatch is a config entry in a story's
`dispatches.json` (a `{dispatch_id: entry}` dict, merged from modules the
same way `missions.json` is):

    "combine_mobilises": {
      "sender": "Ninefold Combine liaison",
      "subject": "Notice of closure",
      "body": "The Combine is sealing the Kiln lane. Any hull still inbound...",
      "requires_flag": "act_pressure",
      "requires_rep_below": "ninefold_combine:20",
      "on_receive_flags": ["combine_mobilised"],
      "on_receive_rep": {"ninefold_combine": -3},
      "start_mission": "combine_evacuation"
    }

The gate keys (`requires_flag` / `requires_not_flag` / `requires_rep` /
`requires_rep_below`) are exactly `content_gate`'s vocabulary. A dispatch
with no gate keys arrives immediately on the first check - use one to seed
an Act with its opening orders.

This module is pure logic (like `mission.py` / `content_gate.py`); the
per-frame check + Message Log posting lives in
`SpaceScreen._check_dispatches` (which runs while docked too - see
loop_helpers), seeded on first call so a loaded save with dispatches
already received stays quiet.
"""
from game.world.content_gate import passes_content_gate
from game.world.mission import start_mission


def received_flag(dispatch_id):
    """The `Possessions.flags` name that marks one dispatch as delivered -
    also usable as a `requires_flag` on a later dispatch to chain them."""
    return f"dispatch:{dispatch_id}"


def pending_dispatches(dispatches, possessions):
    """Every dispatch whose content-gate passes against the player's current
    flags/standing and that hasn't been received yet, in `dispatches` dict
    order. `dispatches` is `utils.get_dispatches(story)`."""
    flags = possessions.flags
    rep = possessions.reputation
    out = []
    for did, entry in dispatches.items():
        if did.startswith("_") or flags.get(received_flag(did)):
            continue
        if passes_content_gate(entry, flags, rep):
            out.append((did, entry))
    return out


def receive_dispatch(dispatch_id, entry, possessions, missions_config):
    """Mark `dispatch_id` received, apply its `on_receive_flags` /
    `on_receive_rep`, and start its `start_mission` (if any, and not already
    active/finished). Returns `(sender, subject, body, advanced_stage)` -
    `advanced_stage` is the `(mission_id, stage_index)` pair from
    `start_mission` (for the caller to deliver that stage's one_way_message),
    or None."""
    possessions.flags[received_flag(dispatch_id)] = True
    for flag in entry.get("on_receive_flags", []):
        possessions.flags[flag] = True
    for faction_id, delta in entry.get("on_receive_rep", {}).items():
        possessions.adjust_reputation(faction_id, delta)

    advanced = None
    mission_id = entry.get("start_mission")
    if (mission_id and mission_id not in possessions.missions
            and mission_id not in possessions.completed_missions):
        advanced = start_mission(missions_config, possessions, mission_id)

    return (entry.get("sender", "Relay Network"),
            entry.get("subject", "Dispatch"),
            entry.get("body", ""),
            advanced)
