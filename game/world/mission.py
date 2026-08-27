"""Mission/stage progress tracking.

A mission is defined once (title + an ordered list of stages) in a story's
missions.json (static config, see game.utils.get_missions) - never mutated
by play. Which stage of which mission a player currently has active, and
which missions have finished every stage, is mutable player state instead
(see Possessions.missions/completed_missions).

Each stage names a "complete_flag" - a Possessions.flags name, the exact
same flag vocabulary Dialogue's requires_flag/"set_flag:" action already
use (see game/world/dialogue.py) - so a stage can be completed by a
dialogue choice, a one-way hail being seen, or any other code path that
sets a flag (SpaceScreen sets a handful of generic gameplay-event flags,
like having used thrust or landed somewhere, for exactly this purpose).
This keeps mission progress and conversation state in one shared
vocabulary instead of two parallel systems that would each need to notice
the same events.

A stage can also carry a "one_way_message" ({"sender": ..., "text": ...})
- delivered automatically (as a one-way hail banner + Messages log entry,
see SpaceScreen._post_message) the moment a mission advances *into* that
stage, whether via start_mission() or check_mission_progress(). Both
return which (mission_id, stage_index) pairs just became active so a
caller with access to the actual message-posting (SpaceScreen) can look
up and deliver each one's "one_way_message", if it has one - this module
stays pygame/UI-free on purpose.

A mission can also carry "escort_flag" (a flag name cleared - set False -
whenever the mission ends, finished or abandoned) and "on_end_flags" (a
list of flag names set True at that same point) - see _on_mission_end().
Lets a mission put an NPC pilot in FollowRoutine for its duration (see
person.escort_flag/SpaceScreen._sync_escorts) and leave a marker behind
(e.g. so a re-hailed pilot's dialogue can stop offering the same mission
again - see Dialogue.conditional_roots) without SpaceScreen needing to
know anything mission-specific.
"""


def _on_mission_end(mission, possessions):
    """Common cleanup for a mission that's no longer active - completed or
    abandoned (see check_mission_progress/abandon_mission)."""
    escort_flag = mission.get("escort_flag")
    if escort_flag:
        possessions.flags[escort_flag] = False
    for flag in mission.get("on_end_flags", []):
        possessions.flags[flag] = True


def start_mission(missions_config, possessions, mission_id):
    """Begin mission_id at its first stage, if it's a real mission and
    isn't already active or completed - a no-op otherwise, so starting the
    same mission twice (e.g. buying a second ship) never resets progress.
    Returns (mission_id, 0) if it actually started (so a caller can
    deliver that first stage's one_way_message, if it has one), else None."""
    if mission_id not in missions_config:
        return None
    if mission_id in possessions.missions or mission_id in possessions.completed_missions:
        return None
    possessions.missions[mission_id] = 0
    return (mission_id, 0)


def check_mission_progress(missions_config, possessions):
    """Advance every active mission whose current stage's complete_flag is
    now set in possessions.flags - to the next stage, or into
    completed_missions (running _on_mission_end) if that was the last one.
    Call this every frame (see SpaceScreen.update_physics) so a flag set
    by any means (a dialogue choice, a gameplay event) is picked up
    promptly regardless of which screen actually set it.

    Returns a list of (mission_id, new_stage_index) for every mission that
    advanced into a new, not-yet-finished stage this call - so a caller
    can deliver that stage's one_way_message, if it has one."""
    advanced = []
    for mission_id in list(possessions.missions.keys()):
        mission = missions_config.get(mission_id)
        if not mission:
            continue
        stages = mission.get("stages", [])
        stage_index = possessions.missions[mission_id]
        if stage_index >= len(stages):
            continue
        flag = stages[stage_index].get("complete_flag")
        if not flag or not possessions.flags.get(flag):
            continue
        next_index = stage_index + 1
        if next_index >= len(stages):
            del possessions.missions[mission_id]
            possessions.completed_missions.append(mission_id)
            _on_mission_end(mission, possessions)
        else:
            possessions.missions[mission_id] = next_index
            advanced.append((mission_id, next_index))
    return advanced


def abandon_mission(missions_config, possessions, mission_id):
    """Drop mission_id from possessions.missions without marking it
    completed - for a dialogue option that lets the player decline (e.g.
    "no thanks" to an NPC's offer to walk them through something). Runs
    the same _on_mission_end cleanup a normal finish would (an abandoned
    mission shouldn't leave an NPC still escorting the player, say) - a
    no-op if the mission wasn't actually active."""
    mission = missions_config.get(mission_id)
    if possessions.missions.pop(mission_id, None) is not None and mission:
        _on_mission_end(mission, possessions)


def mission_status_lines(missions_config, possessions):
    """[(display_title, [stage_text, ...], current_stage_index)] for every
    mission that's ever been started (active or completed) - the data
    MissionLog (game/ui/mission_log.py) renders. current_stage_index is
    None for a completed mission (every stage shown done - there's no
    "current" one anymore); stages before it are done, the stage at it is
    current, and stages after it are still pending."""
    lines = []
    for mission_id, stage_index in possessions.missions.items():
        mission = missions_config.get(mission_id)
        if not mission:
            continue
        lines.append((mission.get("title", mission_id), [s.get("text", "") for s in mission.get("stages", [])], stage_index))
    for mission_id in possessions.completed_missions:
        mission = missions_config.get(mission_id)
        if not mission:
            continue
        title = mission.get("title", mission_id) + " (Complete)"
        lines.append((title, [s.get("text", "") for s in mission.get("stages", [])], None))
    return lines
