"""Whether a piece of flag/reputation-conditional world content is currently
present.

A config entry - an `ai_ships[]` ship, an interior `npcs[]` NPC or
`structures[]` building - may carry any of:

- `"requires_flag"` / `"requires_not_flag"` - a `Possessions.flags` name
- `"requires_rep"` / `"requires_rep_below"` - `"<faction>:<n>"`, meaning the
  player's standing with that faction is `>= n` / `< n` (a faction absent
  from `reputation` counts as 0)

`passes_content_gate` is the single check. An entry with none of these keys
always passes, so unconditional content is unaffected. It's the world-content
counterpart of `Dialogue.current_options`' per-option gate (same key
vocabulary); a function-only module like `game/world/mission.py`.

Callers re-run it whenever the relevant state can have changed -
`SpaceScreen._sync_conditional_ships` on system (re-)entry and on launch,
`LocationScreen._apply_content_gates` on interior (re-)entry - so a beacon
lit or a faction turned hostile actually changes what's in the world the
next time the player is there.
"""

GATE_KEYS = ("requires_flag", "requires_not_flag", "requires_rep", "requires_rep_below")


def is_gated(entry):
    """True if `entry` carries any conditional key at all (so a caller can
    skip the ones that never change)."""
    return any(k in entry for k in GATE_KEYS)


def passes_content_gate(entry, flags=None, reputation=None):
    """True if `entry`'s conditions (if any) are all met against `flags`
    ({name: True}) and `reputation` ({faction_id: int})."""
    flags = flags or {}
    reputation = reputation or {}

    rf = entry.get("requires_flag")
    if rf and not flags.get(rf):
        return False
    rnf = entry.get("requires_not_flag")
    if rnf and flags.get(rnf):
        return False

    rr = entry.get("requires_rep")
    if rr:
        faction_id, threshold = rr.split(":", 1)
        if reputation.get(faction_id, 0) < int(threshold):
            return False
    rrb = entry.get("requires_rep_below")
    if rrb:
        faction_id, threshold = rrb.split(":", 1)
        if reputation.get(faction_id, 0) >= int(threshold):
            return False

    return True
