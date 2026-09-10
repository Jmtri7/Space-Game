"""LocationScreen: targeting — mixed into the class in screen.py."""
from game.screens.location_screen._defs import *  # noqa: F401,F403


class _TargetingMixin:

    def _targetable_people(self):
        """NPCs plus any visiting AI pilots currently in this location -
        anyone the player can target with []/talk to with T. self.npcs holds
        Character wrappers (see _build_local_character); self.visitors are
        already bare Person objects (the *same* Character.person a visiting
        pilot's AIShip-successor tracks in SpaceScreen.ai_ships - never
        wrapped a second time here)."""
        return [character.person for character in self.npcs] + self.visitors

    def _cycle_npc_target(self, direction=1):
        """Cycle through targetable NPCs and visiting pilots - direction=1
        for ], -1 for [."""
        people = self._targetable_people()
        if not people:
            return
        if self.current_npc_target is None:
            self.current_npc_target = 0
        else:
            self.current_npc_target = (self.current_npc_target + direction) % len(people)
        # Generic gameplay-event flag (see PlayerController's "used_turn") -
        # lets a tutorial stage use "targeted_person" as its complete_flag.
        self.player.possessions.flags["targeted_person"] = True
        sound_board.play("blip")

    def _get_npc_target(self):
        """Get the currently targeted NPC or visiting pilot, if any."""
        people = self._targetable_people()
        if self.current_npc_target is None or self.current_npc_target >= len(people):
            return None
        return people[self.current_npc_target]

    def _select_person_target_at(self, world_x, world_y):
        """Target whichever targetable person (see _targetable_people)
        world_x/world_y falls within (closest one wins on overlap) - the
        click-to-target counterpart to cycling with []. Mirrors
        SpaceScreen._select_target_at, but over people on foot instead of
        ships/landing sites, and with a fixed click radius since Person has no
        drawn "size" of its own."""
        people = self._targetable_people()
        best_index, best_dist = None, None
        for i, person in enumerate(people):
            distance = person.get_distance(world_x, world_y)
            if distance <= 32 and (best_dist is None or distance < best_dist):
                best_index, best_dist = i, distance
        if best_index is not None:
            self.current_npc_target = best_index
            self.player.possessions.flags["targeted_person"] = True
            sound_board.play("blip")

    def _closest_person_in_range(self):
        """The closest targetable person within talk_range of the player, or
        None. This is deliberately independent of current_npc_target/
        _get_npc_target (manual []/click targeting) - walking up to someone
        no longer targets them, it just makes them talkable: T always talks
        to whoever this returns, and draw() labels their name/role above
        their head, regardless of what (if anything) is manually targeted."""
        in_range = [person for person in self._targetable_people() if person.get_distance(self.player.x, self.player.y) <= self.talk_range]
        if not in_range:
            return None
        return min(in_range, key=lambda person: person.get_distance(self.player.x, self.player.y))

    def _role_label(self, person):
        """Human-readable role for a name/role label (e.g. "outfitter" ->
        "Outfitter"), or None if this person has no role (e.g. the player -
        see Character.__init__, which is the only place person.role is set)."""
        role = getattr(person, "role", None)
        return role.replace("_", " ").title() if role else None

    def _draw_person_label(self, surface, person, ui_scale):
        """Floating name (and role, if any) centered just above person's
        head - used both for whoever's currently close enough to talk to
        (see _closest_person_in_range) and for a manually cycled/clicked
        target, so "who is this" is answered in-world without needing to
        check the info panel."""
        anchor_x, anchor_y = to_screen(person.x, person.y - self.LABEL_HEIGHT_ABOVE)
        bottom_y = anchor_y
        role_label = self._role_label(person)
        if role_label:
            font_role = get_font(int(13 * ui_scale))
            # Not GRAY (100,100,100) - too low-contrast to read at this
            # small size against the varied floor/wall colors behind it.
            role_surf = font_role.render(role_label, True, (210, 210, 225))
            role_rect = role_surf.get_rect(midbottom=(anchor_x, bottom_y))
            surface.blit(role_surf, role_rect)
            bottom_y = role_rect.top - 1
        font_name = get_font(int(16 * ui_scale))
        name_surf = font_name.render(person.name, True, WHITE)
        name_rect = name_surf.get_rect(midbottom=(anchor_x, bottom_y))
        surface.blit(name_surf, name_rect)
