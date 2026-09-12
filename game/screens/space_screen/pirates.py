"""SpaceScreen: pirate ambush events — mixed into the class in screen.py.

The "pirate_ambush" system-event kind (see docs/architecture/config-formats.md's
"System events" and events.json's "kind") - a lone hostile AI ship spawned a
short distance from the player on system entry, with a story-authored
pilots.json "one_way_hail" doing the actual warning (fires automatically once
the player is in range - see hailing.py._check_one_way_hails, no special
code needed here for that part). The countdown itself doesn't start ticking
until that warning has actually been delivered ("one_way_hail_seen:<name>")
- otherwise a player who docks or lingers before ever hearing the toll
demand would find the pirate already hostile the moment they undock, the
clock having run out unseen. From there the player has a fixed window to
hail the pirate and either pay tribute (a dialogue action combo -
"spend_credits:<n>" + "set_flag:pirate_tribute_paid:<name>") or refuse
("set_flag:hostile_to_player:<name>", the same flag _sync_hostiles already
watches for any hostile pilot - no new combat code needed either). Letting
the window expire without hailing sets that same hostile flag directly.

Only one ambush is tracked at a time (self.pirate_ambush, None when
inactive) - deliberately simple rather than a list, since "a lone raider"
is the whole premise; a system whose "events" roll a second one while the
first is still unresolved just doesn't roll (see _maybe_spawn_pirate_ambush).

**Rerolled periodically, not just on system entry.** A player who parks in
a system and just keeps mining never re-triggers _activate_system, so a
roll only on entry would mean at most one possible ambush per visit no
matter how long they linger.  _update_periodic_pirate_ambush (called every
flying frame from update_physics) ticks self.pirate_ambush_recheck_timer
down and calls _maybe_spawn_pirate_ambush again whenever it lapses - every
event's own "interval_seconds" (default DEFAULT_RECHECK_SECONDS) sets how
often that happens, and the timer is (re)armed by _maybe_spawn_pirate_ambush
itself, both on entry and after each periodic reroll, hit or miss.
"""
from game.screens.space_screen._defs import *  # noqa: F401,F403

DEFAULT_RECHECK_SECONDS = 60  # how often a lingering player gets rerolled for a fresh ambush


class _PiratesMixin:

    def _maybe_spawn_pirate_ambush(self, state):
        """Roll a system's "pirate_ambush" event configs (see
        setup.py._build_pirate_ambush_configs) - called on system
        (re-)entry (from _activate_system, before self.ai_ships is pointed
        at state.ai_ships, so the newly spawned Character is included in
        that alias and this frame's targetable_objects build) and again
        periodically thereafter while the player stays put (see
        _update_periodic_pirate_ambush). Always (re)arms the recheck timer
        first, off whichever config interval is shortest, so a lingering
        player keeps getting rerolled even while an ambush is already
        active or every roll keeps missing. A no-op past that whenever an
        ambush is already active anywhere (see the module docstring) or
        none of this system's configs roll a hit."""
        configs = getattr(state, "pirate_ambush_configs", None)
        if configs:
            interval = min(event.get("interval_seconds", DEFAULT_RECHECK_SECONDS) for event, _ in configs)
            self.pirate_ambush_recheck_timer = int(interval * constants.FPS)
        if self.pirate_ambush is not None:
            return
        for event, chance in configs or []:
            if random.random() >= chance:
                continue
            self._spawn_pirate_ambush(state, event)
            return  # one at a time, even if a system lists several kinds

    def _update_periodic_pirate_ambush(self):
        """Reroll the active system's pirate_ambush odds on a timer while
        the player is actually flying in it (not docked - see self.in_flight)
        - the entry-only roll in _maybe_spawn_pirate_ambush would otherwise
        let a player who parks in a rich belt and just keeps mining fly
        forever without ever facing a second encounter. A no-op for a
        system with no pirate_ambush events configured at all."""
        if not self.in_flight:
            return
        state = self.systems.get(self.system_id)
        if state is None or not getattr(state, "pirate_ambush_configs", None):
            return
        self.pirate_ambush_recheck_timer -= 1
        if self.pirate_ambush_recheck_timer <= 0:
            self._maybe_spawn_pirate_ambush(state)

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
        our own tracking so a later system-entry can roll a fresh one), or -
        once the player has actually heard the toll demand
        ("one_way_hail_seen:<name>") - count the warning window down and force hostility
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
        if not flags.get(f"one_way_hail_seen:{name}"):
            return  # hasn't heard the toll demand yet - the clock hasn't started
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
