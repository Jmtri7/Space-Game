"""SpaceScreen: hailing — mixed into the class in screen.py."""
from game.screens.space_screen._defs import *  # noqa: F401,F403


class _HailingMixin:

    def _start_hail(self):
        """Open a hail with the currently targeted ship (K_r - see
        docs/CONTROLS.md's Hailing section). Requires a targeted AI ship
        (SHIPS target mode - see _get_target_object/_filtered_targets);
        does nothing if nothing's targeted, or the target isn't a ship at
        all. A pilot currently ashore (DockRoutine has them walking around
        a station/moon interior right now) can't actually be reached this
        way - hailing them just flashes a brief "no response" banner
        instead of opening person.hail_dialogue, since they're not in the
        ship to answer."""
        target_obj = self._get_target_object()
        if not isinstance(target_obj, Character) or self.current_target is None:
            return
        pilot_name = target_obj.person.name or "Unknown"
        if target_obj.ashore:
            self.hail_banner = (f"{pilot_name}: no response - currently docked.", YELLOW)
            self.hail_banner_timer = HAIL_BUSY_BANNER_FRAMES
            return
        dialogue = target_obj.person.hail_dialogue
        possessions = self.player.person.possessions
        flags = possessions.flags
        # Generic gameplay-event flag (see K_f's own comment) - any
        # story's missions.json can use "hailed_pilot:<name>" as a stage's
        # complete_flag without this class hardcoding which pilot.
        flags[f"hailed_pilot:{pilot_name}"] = True
        # resolve_root(), not .root directly, so an earlier flag (e.g.
        # having already been hailed by this pilot once - see
        # _check_one_way_hails) can open on a different greeting node.
        dialogue.current_node = dialogue.resolve_root(flags, possessions.reputation)
        dialogue.selected_option = 0
        self.active_dialogue = dialogue
        self.hail_banner = None
        self.hail_banner_timer = 0
        # Release thrust - handle_input() stops calling into
        # player.handle_input() the instant active_dialogue is set (see
        # there), so without this whatever thrust was already applied the
        # frame H was pressed would otherwise keep accelerating the ship
        # every physics frame for as long as the conversation stays open.
        self.player.thrust = 0

    def _choose_hail_option(self, index):
        """Act on the visible hail option at `index` (a mouse click on it).
        A hail option's action is only ever a shared one (set_flag/give_item/
        spend_credits - buy_ship:/take_loan don't make sense mid-flight), and
        none of those block on affordability, so there's no "skip blocked"
        pass like LocationScreen's."""
        possessions = self.player.person.possessions
        options = self.active_dialogue.current_options(possessions.flags, possessions.reputation)
        if not 0 <= index < len(options):
            return
        option = options[index]
        for action in option_actions(option):
            apply_shared_actions(action, possessions, self.missions_config, story=self.story)
        if self.active_dialogue.advance(option):
            self.active_dialogue = None
        else:
            self.active_dialogue.selected_option = 0

    def _show_toast(self, text, color=CYAN):
        """Flash a short, self-clearing message in the center of the screen
        (see _draw_hud) - used for jump completion and mission events
        (started / stage completed / finished). Unlike _post_message this
        is purely transient: nothing is written to the Messages log."""
        self.toast_text = text
        self.toast_color = color
        self.toast_timer = TOAST_FRAMES

    def _post_message(self, sender, text):
        """Show a transient hail banner and permanently log a one-way
        message from sender (see Possessions.add_message) - shared by
        pilot-proximity hails (_check_one_way_hails) and mission-stage-
        entry messages (missions.json's "one_way_message" - see
        _deliver_stage_message). The banner is skipped (but the message is
        still logged) while a hail conversation is already open, so an
        incoming banner can't visually collide with the dialogue box - the
        Messages pane still shows it once the conversation closes."""
        self.player.person.possessions.add_message(sender, text)
        # Snap the Message Log back to the newest entry and (re)start its
        # unread alert: the light blinks MESSAGE_ALERT_BLINKS times and the
        # "ping" cue sounds once per blink, driven from update() so the audio
        # stays in sync with the light (see message_alert_state).
        self.message_log_scroll = 0
        self.message_alert_timer = MESSAGE_ALERT_FRAMES
        self._message_alert_pings_played = 0
        if self.active_dialogue:
            return
        # Banner just announces the transmission - the message body itself
        # is in the Messages pane (bottom-left) and stays there to read.
        self.hail_banner = (f"Incoming transmission - {sender} (see Messages)", CYAN)
        self.hail_banner_timer = ONE_WAY_HAIL_BANNER_FRAMES

    def _deliver_stage_message(self, advanced_stage):
        """Post the one_way_message (if any) for a stage a mission just
        advanced into - advanced_stage is a (mission_id, stage_index) pair
        as returned by mission.py's start_mission()/check_mission_progress(),
        or None (nothing advanced this call, or the mission has no
        starting_mission - see both call sites)."""
        if not advanced_stage:
            return
        mission_id, stage_index = advanced_stage
        stage = self.missions_config[mission_id]["stages"][stage_index]
        message = stage.get("one_way_message")
        if message:
            self._post_message(message.get("sender", "Unknown"), message.get("text", "..."))

    def _check_one_way_hails(self):
        """Let an NPC-initiated hail (pilots.json's "one_way_hail" - see
        Character.for_ai_pilot) fire once the player gets close enough -
        see _post_message - and sets a flag so it never fires twice for
        the same pilot. Only checks the active system's ships
        (self.ai_ships) - proximity to the player only means anything in
        whichever system they're actually in - and skips entirely while a
        hail is already open, so an incoming banner can't steal focus out
        from under a conversation the player is already having, or while
        the player is docked in an interior (update_physics() still runs
        in the background then, but a pilot hailing your cockpit makes no
        sense when you're not in it - see self.in_flight)."""
        if self.active_dialogue or not self.in_flight:
            return
        flags = self.player.person.possessions.flags
        for ai_ship in self.ai_ships:
            one_way = getattr(ai_ship.person, "one_way_hail", None)
            if not one_way or ai_ship.ashore:
                continue
            seen_flag = f"one_way_hail_seen:{ai_ship.person.name}"
            if flags.get(seen_flag):
                continue
            hail_range = one_way.get("range", ONE_WAY_HAIL_RANGE)
            if ai_ship.get_distance(self.player.x, self.player.y) <= hail_range:
                flags[seen_flag] = True
                self._post_message(ai_ship.person.name or "Unknown", one_way.get("message", "..."))
                return  # one at a time - avoids stacking two banners the same frame
