"""SpaceScreen: npc sync — mixed into the class in screen.py."""
from game.screens.space_screen._defs import *  # noqa: F401,F403
from game.world.dispatch import pending_dispatches, receive_dispatch


class _NpcSyncMixin:

    def _check_dispatches(self):
        """Deliver any story dispatch (dispatches.json - faction-handler
        "inbox" comms, gap F) whose content-gate has just started passing:
        post it to the Message Log, apply its on-receive flags/standing, and
        start its attached mission. Runs every frame from update_physics
        (which ticks while docked too), so a dispatch can land in a station.
        self._dispatched is seeded on the first call so a loaded save with
        dispatches already received stays quiet, mirroring _check_beacons.

        When several dispatches' gates open on the same frame (e.g. one flag
        that several dispatches wait on), only the first is delivered now and
        the rest trickle in one per DISPATCH_SPACING_FRAMES, so a burst reads
        as separate incoming comms instead of a wall of messages."""
        possessions = self.player.person.possessions
        dispatches = get_dispatches(self.story)
        if not dispatches:
            return
        newly = pending_dispatches(dispatches, possessions)
        if self._dispatched is None:
            # First call after load: mark everything currently eligible as
            # already delivered without announcing it.
            for did, entry in newly:
                receive_dispatch(did, entry, possessions, self.missions_config)
            self._dispatched = True
            return
        if self._dispatch_cooldown > 0:
            self._dispatch_cooldown -= 1
            return
        if not newly:
            return
        did, entry = newly[0]
        sender, subject, body, advanced = receive_dispatch(
            did, entry, possessions, self.missions_config)
        text = f"{subject} — {body}" if body else subject
        self._post_message(sender, text)
        self._deliver_stage_message(advanced)
        if len(newly) > 1:
            self._dispatch_cooldown = DISPATCH_SPACING_FRAMES

    def _check_beacons(self):
        """Post a galaxy-wide "beacon relit" message the frame a locked
        system's unlock_flag first flips true (by the "light_beacon:"
        dialogue action, a mission's on_end_flags, or a plain set_flag:).
        The system is jumpable from that point on - see utils.system_unlocked
        and try_jump. self._lit_beacons is seeded (no announcement) on the
        first call so a loaded save with already-lit beacons stays quiet,
        then tracks flips from there."""
        flags = self.player.person.possessions.flags
        systems = get_star_systems(self.story)
        lit_now = {sid for sid, cfg in systems.items()
                   if cfg.get("locked") and cfg.get("unlock_flag") and flags.get(cfg["unlock_flag"])}
        if self._lit_beacons is None:
            self._lit_beacons = lit_now
            return
        for sid in lit_now - self._lit_beacons:
            name = systems.get(sid, {}).get("name", sid)
            self._post_message("Relay Network", f"Beacon relit: {name}. The jump lane is open.")
        self._lit_beacons = lit_now

    def _sync_escorts(self):
        """Toggle any pilot with a configured "escort_flag" (pilots.json)
        between escorting the player (OrbitPlayerRoutine - circling nearby)
        and their normal role routine, based on whether that flag is currently set in the
        player's Possessions.flags - e.g. Kade Marsh following the player
        through the tutorial mission once they accept his offer to help
        (see his hail_dialogue_tree's "set_flag:kade_escorting" action),
        and back to his normal patrol once the mission ends, finished or
        declined (see mission.py's escort_flag clearing). Checks every
        system, not just the active one, so this stays correct regardless
        of which system is currently on screen."""
        flags = self.player.person.possessions.flags
        for state in self.systems.values():
            for ai_ship in state.ai_ships:
                escort_flag = getattr(ai_ship.person, "escort_flag", None)
                if not escort_flag:
                    continue
                should_escort = bool(flags.get(escort_flag))
                if should_escort and not ai_ship.escorting:
                    ai_ship.set_routine(OrbitPlayerRoutine(self.player))
                    ai_ship.escorting = True
                elif not should_escort and ai_ship.escorting:
                    ai_ship.set_routine(resolve_routine_class(ai_ship.role, ai_ship.faction, ai_ship.routine_name)(ai_ship.route))
                    ai_ship.escorting = False

    def _provoke(self, ship):
        """The player shot an AI ship - it fights back. Once per pilot: set
        its "hostile_to_player:<name>" flag (persisted; _sync_hostiles picks
        it up next frame) and dock a one-time chunk of standing with its
        faction, so shooting up enough of a faction's ships eventually turns
        the whole faction hostile via the normal rep threshold. A nameless
        ship (no config pilot) just goes straight into CombatRoutine, since
        there's no flag key to hang persistence off."""
        if ship.in_combat:
            return
        flags = self.player.person.possessions.flags
        name = getattr(ship.person, "name", None)
        if name:
            key = f"hostile_to_player:{name}"
            if flags.get(key):
                return
            flags[key] = True
            if ship.faction:
                self.player.person.possessions.adjust_reputation(ship.faction, -10)
        else:
            ship.set_routine(CombatRoutine(self.player))
            ship.in_combat = True

    def _sync_conditional_ships(self):
        """Add/drop the flag- or reputation-gated AI ships of the *active*
        system so its roster matches the player's current state - a Kiln
        patrol wing that only appears once `kiln_mobilised` is set, a
        blockade that lifts when standing recovers. Run on system
        (re-)entry (_activate_system) and on launch (board_ship), not every
        frame, so a ship never pops in right in front of the player.
        Unconditional ships (no gate key) are never touched. See
        game/world/content_gate.py."""
        state = self.systems[self.system_id]
        possessions = self.player.person.possessions
        flags, reputation = possessions.flags, possessions.reputation
        for ship in list(state.ai_ships):
            cfg = getattr(ship, "_spawn_cfg", None)
            if cfg is not None and is_gated(cfg) and not passes_content_gate(cfg, flags, reputation):
                state.ai_ships.remove(ship)
        present = {id(getattr(s, "_spawn_cfg", None)) for s in state.ai_ships}
        for cfg in getattr(state, "ai_ship_configs", []):
            if is_gated(cfg) and id(cfg) not in present and passes_content_gate(cfg, flags, reputation):
                state.ai_ships.append(self._build_ai_ship(state, cfg))

    def _sync_hostiles(self):
        """Swap any AI pilot between CombatRoutine (attacking the player)
        and its normal role routine, based on whether it's currently
        hostile: faction standing at or below HOSTILE_REP_THRESHOLD, a
        per-pilot "hostile_to_player:<name>" flag, or a
        "faction_hostile:<faction>" flag. The hostility mirror of
        _sync_escorts; an escorting pilot is never made hostile. Checks
        every system so it stays correct across jumps."""
        possessions = self.player.person.possessions
        flags = possessions.flags
        for state in self.systems.values():
            for ship in state.ai_ships:
                if ship.escorting:
                    continue
                name = getattr(ship.person, "name", None)
                faction = ship.faction
                hostile = bool(
                    (name and flags.get(f"hostile_to_player:{name}"))
                    or (faction and flags.get(f"faction_hostile:{faction}"))
                    or (faction and possessions.reputation_with(faction) <= HOSTILE_REP_THRESHOLD)
                )
                if hostile and not ship.in_combat:
                    ship.set_routine(CombatRoutine(self.player))
                    ship.in_combat = True
                elif not hostile and ship.in_combat:
                    ship.set_routine(resolve_routine_class(ship.role, ship.faction, ship.routine_name)(ship.route))
                    ship.in_combat = False
                    ship.firing = False
