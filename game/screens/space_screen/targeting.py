"""SpaceScreen: targeting — mixed into the class in screen.py."""
from game.screens.space_screen._defs import *  # noqa: F401,F403


class _TargetingMixin:

    def _ship_target_label(self, ship, index=0):
        """HUD label for an AI ship in targetable_objects - just the ship
        type's display name (the pilot name is shown separately)."""
        ship_type = get_ship_type(self.story, ship.ship_type_id)
        return ship_type.get("name", f"AI Ship {index + 1}")

    def _approaching_label(self, obj):
        """Short name for whatever the autopilot is currently seeking, for
        the "Approaching: ..." status line - a ship's type display name
        (matching the targeting HUD's own label), or a landing site / body's
        own name."""
        if isinstance(obj, Character):
            return self._ship_target_label(obj)
        return getattr(obj, "name", "target")

    def _select_target_at(self, world_x, world_y):
        """Target whichever targetable object world_x/world_y falls within
        (closest one wins on overlap) - the click-to-target counterpart to
        cycling with []. current_target is always an index into the
        *filtered* list for whichever mode is active (see _filtered_targets),
        and a click has no mode of its own, so it infers one from what was
        actually clicked and switches target_mode_index to match before
        resolving the index, rather than requiring the player to already be
        in the right mode for whatever they click on."""
        best_obj, best_dist = None, None
        for _, obj in self.targetable_objects:
            radius = obj.ship.size if isinstance(obj, Character) else getattr(obj, "size", 20)
            distance = math.sqrt((obj.x - world_x) ** 2 + (obj.y - world_y) ** 2)
            if distance <= radius + 12 and (best_dist is None or distance < best_dist):
                best_obj, best_dist = obj, distance
        if best_obj is not None:
            self._select_target(best_obj)

    def _select_target(self, obj):
        """Point current_target at obj, inferring the target mode from what
        obj is and switching target_mode_index to match first (a click - on
        the world via _select_target_at, or on the minimap via handle_input -
        carries no mode of its own). current_target is an index into the
        filtered list for that mode (see _filtered_targets). No-op if obj
        somehow isn't in that list."""
        mode = "SHIPS" if isinstance(obj, Character) else "LANDING SITES" if isinstance(obj, LandingSite) else "MISC"
        self.target_mode_index = TARGET_MODES.index(mode)
        for i, (_, candidate) in enumerate(self._filtered_targets()):
            if candidate is obj:
                self.current_target = i
                sound_board.play("blip")
                return

    def _minimap_blip_at(self, pos):
        """The targetable object whose minimap blip is under screen point
        `pos` (closest wins on overlap), or None. Backs both the minimap
        hover text and minimap click-to-target - see _draw_minimap /
        handle_input. Reads _minimap_blips from the last drawn frame."""
        best_obj, best_dist = None, None
        for sx, sy, hit_r, obj in self._minimap_blips:
            d = math.hypot(sx - pos[0], sy - pos[1])
            if d <= hit_r and (best_dist is None or d < best_dist):
                best_obj, best_dist = obj, d
        return best_obj

    def _minimap_label(self, obj):
        """Readable name for a minimap blip - the same label the targeting
        HUD uses (from targetable_objects), plus the pilot name for a
        crewed ship."""
        label = next((lbl for lbl, o in self.targetable_objects if o is obj), None)
        if label is None:
            label = getattr(obj, "name", "Unknown")
        if isinstance(obj, Character):
            pilot = obj.person.name
            if pilot:
                label = f"{label} - {pilot}"
        return label

    def _filtered_targets(self):
        """targetable_objects narrowed to the current target mode - SHIPS
        (AI ships only), LANDING SITES (station/moon only), or MISC (everything
        else - celestial bodies, the central star). current_target is
        always an index into *this* list, not the master one, so switching
        modes changes what index 0 means. Departed AI ships are pruned from
        targetable_objects by _validate_target every frame, so this never
        sees a Character that's no longer in self.ai_ships."""
        mode = TARGET_MODES[self.target_mode_index]
        if mode == "SHIPS":
            return [entry for entry in self.targetable_objects if isinstance(entry[1], Character)]
        elif mode == "LANDING SITES":
            return [entry for entry in self.targetable_objects if isinstance(entry[1], LandingSite)]
        return [entry for entry in self.targetable_objects if not isinstance(entry[1], (Character, LandingSite))]

    def _cycle_target(self, direction=1):
        """Cycle through targetable objects in the current target mode - direction=1 for T/], -1 for [."""
        filtered = self._filtered_targets()
        if not filtered:
            return
        if self.current_target is None:
            self.current_target = 0
        else:
            self.current_target = (self.current_target + direction) % len(filtered)
        sound_board.play("blip")

    def _cycle_target_mode(self):
        """Switch which category T/[/] cycles through (Tab). Immediately
        selects the first object in the new category - empty if this
        system has none - so the mode switch itself gives feedback instead
        of leaving a stale target from the old category selected."""
        self.target_mode_index = (self.target_mode_index + 1) % len(TARGET_MODES)
        self.current_target = 0 if self._filtered_targets() else None
        sound_board.play("blip")
        if TARGET_MODES[self.target_mode_index] == "SHIPS":
            # Generic gameplay-event flag - see K_f's own comment on
            # why these live on Possessions.flags instead of a
            # SpaceScreen-only field.
            self.player.person.possessions.flags["used_ships_target_mode"] = True

    def _get_target_name(self):
        """Get the name of the current target"""
        filtered = self._filtered_targets()
        if self.current_target is None or self.current_target >= len(filtered):
            return None
        return filtered[self.current_target][0]

    def _get_target_object(self):
        """Get the current target object"""
        filtered = self._filtered_targets()
        if self.current_target is None or self.current_target >= len(filtered):
            return None
        return filtered[self.current_target][1]

    def _validate_target(self):
        """Keep targetable_objects in sync with self.ai_ships - prune AI
        ships that have left this system, re-add any that have come back -
        keep current_target pointing at the same object across that change
        (or clear it if that object was the one that left), and disengage
        the player's autopilot if it was seeking a ship that's now gone.

        ExplorerRoutine can migrate a Character out of self.ai_ships into
        another system's list entirely (it jumped away) while
        targetable_objects, built once per _activate_system, still holds the
        now-stale tuple referencing it. That Character keeps updating every
        frame regardless of which system it's in (see
        SystemState.update_physics), so a stale entry left in place would
        keep the brackets/arrow tracking its position over in whatever
        system it jumped to. It also broke cycling: current_target indexes
        _filtered_targets(), so a ghost sitting at the end of the SHIPS list
        meant "[" from the first ship wrapped straight onto it and bounced
        back every time, never reaching the real ships in between (whereas
        "]" happened to hit them on the way past). Removing the tuple
        outright - and re-resolving current_target by identity - fixes both.

        The player's autopilot_target is a separate reference entirely (set
        by engage_seek, independent of current_target/targetable_objects),
        so it needs its own check."""
        target = self._get_target_object()
        stale = {entry[1] for entry in self.targetable_objects
                 if isinstance(entry[1], Character) and entry[1] not in self.ai_ships}
        # A ship can also come *back* (ExplorerRoutine jumps to a random
        # system and may pick this one) - re-add any AI ship that's in
        # self.ai_ships but has no tuple, so it becomes targetable again
        # without waiting for the next _activate_system.
        known = {entry[1] for entry in self.targetable_objects}
        returned = [ship for ship in self.ai_ships if ship not in known]
        if stale or returned:
            self.targetable_objects = [e for e in self.targetable_objects if e[1] not in stale]
            self.targetable_objects.extend((self._ship_target_label(s), s) for s in returned)
            if target is None or target in stale:
                self.current_target = None
            else:
                self.current_target = next(
                    (i for i, (_, obj) in enumerate(self._filtered_targets()) if obj is target),
                    None)

        autopilot_target = self.player.autopilot_target
        if isinstance(autopilot_target, Character) and autopilot_target not in self.ai_ships:
            self.player.autopilot_active = False
            self.player.autopilot_target = None

    def _target_bracket_size(self, target_obj):
        """Screen-pixel bracket half-width that actually hugs target_obj's
        own drawn radius, instead of one fixed size for every target
        regardless of how big it is on screen - a station (~120px radius)
        and a central star (~300px) both used to get the same tiny 40px
        brackets, leaving the brackets floating deep inside the target
        instead of framing it. Character (AI ships) wrap a Ship, whose
        actual drawn size is Ship.size (see draw()'s own ship_size
        resolution); everything else (LandingSite, CelestialBody, CentralStar)
        already exposes its drawn radius directly as `.size`."""
        world_radius = target_obj.ship.size if isinstance(target_obj, Character) else getattr(target_obj, "size", 20)
        padding = 12
        return int(world_radius * get_scale()) + padding
