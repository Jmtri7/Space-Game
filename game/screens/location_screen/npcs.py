"""LocationScreen: npcs — mixed into the class in screen.py."""
from game.screens.location_screen._defs import *  # noqa: F401,F403


class _NpcsMixin:

    def _build_local_character(self, cfg):
        """Build one config-driven local resident: a Person (with a
        Dialogue - a real tree if the config provides one, otherwise the
        flat greeting+options shape) wrapped in a Character with no ship.
        Their role picks the routine that decides whether they wander or
        stay put (see game/world/character.py's ROLE_ROUTINES) - the same
        role->routine mechanism AI ship pilots use, just never flying
        anything. A "routine" key in the NPC config names one outright
        (see ROUTINE_REGISTRY), for a role with no sensible default."""
        # "outfit" is per-NPC-config, defaulting to the story's
        # default_outfit like everyone else - lets an NPC config opt into a
        # different graphics.json outfit entry without any drawing-code changes.
        person = Person(cfg.get("x", 0), cfg.get("y", 0), name=cfg.get("name", "NPC"), outfit=get_graphics_asset(self.story, "outfits", cfg.get("outfit", self.default_outfit_id)))
        # Optional list of extra pipeline articles worn on top of the outfit's
        # own set (a belt, satchel, jacket) - see Person.equip_article. Lets
        # an NPC config accessorize an existing outfit/set without a new one.
        for article_name in cfg.get("equip", []):
            person.equip_article(article_name)
        dialogue_tree = cfg.get("dialogue_tree")
        if dialogue_tree:
            person.dialogue = Dialogue(person.name, dialogue_tree["nodes"], root=dialogue_tree.get("root", "start"), conditional_roots=dialogue_tree.get("conditional_roots"))
        else:
            person.dialogue = Dialogue.from_flat(person.name, cfg.get("greeting", "Hello!"), cfg.get("dialogue_options") or ["Talk", "Leave"])
        # A "shop" config key (see ShopMenu/ShipBrowserMenu/OutfittingMenu)
        # opens a purpose-built buy/sell screen instead of dialogue when T is
        # pressed - None for every NPC that's just flavor/dialogue.
        person.shop = cfg.get("shop")
        # Optional flag name that puts this NPC into FollowPlayerRoutine
        # (trailing the player on foot) while it's set, and back to its
        # normal role routine once cleared - the interior mirror of a ship
        # pilot's pilots.json "escort_flag" (see _sync_npc_escorts and
        # SpaceScreen._sync_escorts). None for an NPC that never escorts.
        person.escort_flag = cfg.get("escort_flag")
        # Optional {"message": ..., "range": ...} the NPC says over the
        # Message Log, once, when the player first gets close - the interior
        # counterpart to a pilot's "one_way_hail" (see _check_npc_ambient).
        # None for an NPC with nothing unprompted to say.
        person.ambient = cfg.get("ambient")
        return Character(person, role=cfg.get("role", "resident"), faction=cfg.get("faction"), can_move_to=self.can_move_to, routine_name=cfg.get("routine"))

    def _post_local_message(self, sender, text):
        """Add a one-way message to the shared log from an interior NPC.
        _refresh_messages() picks it up next frame and raises the banner +
        unread alert (light + pings), exactly as it does for a message that
        arrived while flying."""
        self.player.possessions.add_message(sender, text)

    def _refresh_messages(self):
        """Notice any message that's been appended to the shared
        possessions.message_log since last frame - by a mission stage
        advancing (SpaceScreen delivers those even while the player is
        docked), a hail, or an interior NPC (_post_local_message) - and
        raise the banner + unread light for it. Compares length rather than
        tracking identities; once the log is at its MESSAGE_LOG_MAX cap a
        further message won't re-trigger this, which is fine for the
        early-game tutorial context this mainly serves."""
        log = self.player.possessions.message_log
        if len(log) <= self._seen_message_count:
            self._seen_message_count = len(log)
            return
        self._seen_message_count = len(log)
        newest = log[0]
        self.message_alert_timer = MESSAGE_ALERT_FRAMES
        self._message_alert_pings_played = 0
        self.message_log_scroll = 0
        if not self.active_dialogue:
            self.message_banner = (f"Incoming message - {newest['sender']} (see Message Log)", CYAN)
            self.message_banner_timer = MESSAGE_BANNER_FRAMES

    def _sync_npc_escorts(self):
        """Swap any NPC with a configured "escort_flag" between trailing the
        player on foot (FollowPlayerRoutine) and its normal role routine,
        based on whether that flag is currently set in the player's
        Possessions.flags - the interior counterpart to
        SpaceScreen._sync_escorts(). Used for a station guide walking the
        player through the place (see missions.json's station_tour and
        Sela Cordova's dialogue), and back to standing still once that
        mission ends, finished or abandoned (see mission.py's escort_flag
        clearing)."""
        flags = self.player.possessions.flags
        for character in self.npcs:
            escort_flag = getattr(character.person, "escort_flag", None)
            if not escort_flag:
                continue
            should_escort = bool(flags.get(escort_flag))
            if should_escort and not character.escorting:
                character.set_routine(FollowPlayerRoutine(self.player))
                character.escorting = True
            elif not should_escort and character.escorting:
                normal = resolve_routine_class(character.role, character.faction, character.routine_name)
                character.set_routine(normal(character.route))
                character.escorting = False

    def _check_npc_ambient(self):
        """Let an interior NPC's "ambient" line (see _build_local_character)
        fire once the player first walks within range - the on-foot
        counterpart to SpaceScreen._check_one_way_hails. A per-NPC flag
        keeps it to one delivery ever."""
        flags = self.player.possessions.flags
        for character in self.npcs:
            ambient = getattr(character.person, "ambient", None)
            if not ambient:
                continue
            seen_flag = f"npc_ambient_seen:{character.person.name}"
            if flags.get(seen_flag):
                continue
            if character.person.get_distance(self.player.x, self.player.y) <= ambient.get("range", 160):
                flags[seen_flag] = True
                self._post_local_message(character.person.name or "Unknown", ambient.get("message", "..."))
                return  # one at a time - avoids two banners the same frame
