"""SpaceScreen: pirate ambush events — mixed into the class in screen.py.

The "pirate_ambush" system-event kind (see docs/architecture/config-formats.md's
"System events" and events.json's "kind") - a lone hostile AI ship spawned a
short distance from the player on system entry, with a story-authored
pilots.json "one_way_hail" doing the actual warning (fires automatically once
the player is in range - see hailing.py._check_one_way_hails, no special
code needed here for that part). From there the player has a fixed window to
hail the pirate and either pay tribute (a dialogue action combo -
"spend_credits:<n>" + "set_flag:pirate_tribute_paid:<name>") or refuse
("set_flag:hostile_to_player:<name>", the same flag _sync_hostiles already
watches for any hostile pilot - no new combat code needed either). Letting
the window expire without hailing sets that same hostile flag directly.

Only one ambush is tracked at a time (self.pirate_ambush, None when
inactive) - deliberately simple rather than a list, since "a lone raider"
is the whole premise; a system whose "events" roll a second one while the
first is still unresolved just doesn't roll (see _maybe_spawn_pirate_ambush).
"""
from game.screens.space_screen._defs import *  # noqa: F401,F403


class _PiratesMixin:

    def _maybe_spawn_pirate_ambush(self, state):
        """Roll a system's "pirate_ambush" event configs (see
        setup.py._build_pirate_ambush_configs) on system (re-)entry - called
        from _activate_system, before self.ai_ships is pointed at
        state.ai_ships, so the newly spawned Character is included in that
        alias and this frame's targetable_objects build. A no-op whenever an
        ambush is already active anywhere (see the module docstring) or none
        of this system's configs roll a hit."""
        if self.pirate_ambush is not None:
            return
        for event, chance in getattr(state, "pirate_ambush_configs", []):
            if random.random() >= chance:
                continue
            self._spawn_pirate_ambush(state, event)
            return  # one at a time, even if a system lists several kinds

    def _spawn_pirate_ambush(self, state, event):
        """Build the pirate Character (mirrors _build_ai_ship, but placed a
        configured distance from the player's current position rather than
        a system-config fraction of GAME_WIDTH/HEIGHT - an ambush finds the
        player wherever they are, not a fixed spot) and start tracking the
        encounter's timeout."""
        pilot_id = event.get("pilot")
        pilot = get_pilot(self.story, pilot_id)
        ship_type_id = event.get("ship_type", "raider_skiff")
        distance = event.get("spawn_distance", 700)
        angle = random.uniform(0, 2 * math.pi)
        x = self.player.x + math.cos(angle) * distance
        y = self.player.y + math.sin(angle) * distance
        pirate = Character.for_ai_pilot(
            x, y,
            ship_type=get_ship_type(self.story, ship_type_id),
            ship_type_id=ship_type_id,
            graphics=get_graphics_asset(self.story, "ships", ship_type_id),
            pilot=pilot,
            route=[],
            get_interior_screen=self.get_interior_screen,
            space_drag=state.space_drag,
            outfit=get_graphics_asset(self.story, "outfits", self.default_outfit_id),
            systems=self.systems,
            system_id=state.system_id,
            faction=event.get("faction"),
        )
        state.ai_ships.append(pirate)
        name = pirate.person.name or "Pirate"
        timeout_frames = int(event.get("timeout_seconds", 25) * constants.FPS)
        self.pirate_ambush = {
            "system_id": state.system_id,
            "character": pirate,
            "name": name,
            "timeout": timeout_frames,
        }

    def _update_pirate_ambush(self):
        """Advance the active ambush, if any: resolve payment (the pirate
        flees/despawns once "pirate_tribute_paid:<name>" is set - see the
        hail dialogue), notice the pirate's been destroyed in combat (clear
        our own tracking so a later system-entry can roll a fresh one), or
        count the warning window down and force hostility
        ("hostile_to_player:<name>") once it expires with the player never
        having hailed or refused. Nothing here runs the fight itself -
        _sync_hostiles/_update_ai_weapon_fire already do that, purely off
        the hostile flag, the moment it's set from any of these paths."""
        encounter = self.pirate_ambush
        if encounter is None:
            return
        flags = self.player.person.possessions.flags
        name = encounter["name"]
        if flags.get(f"pirate_tribute_paid:{name}"):
            self._show_toast(f"{name} takes the credits and jumps out.", CYAN)
            self._despawn_pirate_ambush()
            return
        state = self.systems.get(encounter["system_id"])
        if state is None or encounter["character"] not in state.ai_ships:
            # Destroyed in combat (or otherwise removed) - just stop
            # tracking it; _destroy_ship already did the actual cleanup.
            self.pirate_ambush = None
            return
        if flags.get(f"hostile_to_player:{name}"):
            return  # already fighting (or refused) - nothing left to count down
        encounter["timeout"] -= 1
        if encounter["timeout"] <= 0:
            flags[f"hostile_to_player:{name}"] = True
            self._show_toast(f"{name} grows impatient and opens fire!", (255, 120, 120))

    def _despawn_pirate_ambush(self):
        """Remove the active ambush's ship from its system (a payoff/flee,
        not a kill - no explosion) and stop tracking the encounter. Also
        called when the player jumps out of the system it's in - see
        jump.py._complete_jump - so an unresolved pirate never lingers,
        frozen, for a later visit to stumble back into."""
        encounter = self.pirate_ambush
        if encounter is not None:
            state = self.systems.get(encounter["system_id"])
            character = encounter["character"]
            if state is not None and character in state.ai_ships:
                state.ai_ships.remove(character)
            character.escorting = False
            character.in_combat = False
            character.firing = False
        self.pirate_ambush = None
