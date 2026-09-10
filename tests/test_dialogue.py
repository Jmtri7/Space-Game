"""Dialogue — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


class TestDialogue(unittest.TestCase):
    """Test Dialogue's conversation tree - both the backward-compatible
    flat shape (from_flat) and real branching."""

    def test_from_flat_every_option_closes(self):
        """Matches the old flat greeting+options behavior exactly - any
        option chosen just ends the conversation."""
        dialogue = Dialogue.from_flat("Guard", "Welcome.", ["Thanks", "Leave"])
        self.assertEqual(dialogue.current_text(), "Welcome.")
        self.assertEqual([o["label"] for o in dialogue.current_options()], ["Thanks", "Leave"])
        self.assertTrue(dialogue.choose(0))
        self.assertTrue(dialogue.choose(1))

    def test_tree_advances_to_next_node(self):
        dialogue = Dialogue("Bartender", {
            "start": {"text": "What'll it be?", "options": [
                {"label": "Order a drink", "next": "drink"},
                {"label": "Leave", "next": None},
            ]},
            "drink": {"text": "Cheers.", "options": [
                {"label": "Thanks", "next": None},
            ]},
        })
        closed = dialogue.choose(0)
        self.assertFalse(closed)
        self.assertEqual(dialogue.current_node, "drink")
        self.assertEqual(dialogue.current_text(), "Cheers.")
        self.assertTrue(dialogue.choose(0))

    def test_tree_can_loop_back_to_an_earlier_node(self):
        dialogue = Dialogue("Bartender", {
            "start": {"text": "What'll it be?", "options": [{"label": "Chat", "next": "chat"}]},
            "chat": {"text": "...", "options": [{"label": "Back", "next": "start"}]},
        })
        dialogue.choose(0)
        dialogue.choose(0)
        self.assertEqual(dialogue.current_node, "start")


class TestDialogueConditionalOptions(unittest.TestCase):
    """requires_flag/requires_not_flag hide an option entirely (not just
    dim it, unlike an unaffordable action - see status_fn) until a
    Possessions.flags condition is met, and conditional_roots lets a fresh
    conversation open on a different node once a flag is set - the
    mechanism behind hailing/unlockable/consequence dialogue (see
    docs/CONTROLS.md's Hailing section and the bartender's "Buy him a
    round" example in sol_alpha.json)."""

    def test_requires_flag_hides_option_until_set(self):
        dialogue = Dialogue("Bartender", {
            "start": {"text": "Hi", "options": [
                {"label": "Secret", "next": None, "requires_flag": "unlocked"},
                {"label": "Leave", "next": None},
            ]},
        })
        self.assertEqual([o["label"] for o in dialogue.current_options()], ["Leave"])
        self.assertEqual([o["label"] for o in dialogue.current_options({"unlocked": True})], ["Secret", "Leave"])

    def test_requires_not_flag_hides_option_once_set(self):
        dialogue = Dialogue("Bartender", {
            "start": {"text": "Hi", "options": [
                {"label": "First time offer", "next": None, "requires_not_flag": "used"},
                {"label": "Leave", "next": None},
            ]},
        })
        self.assertEqual([o["label"] for o in dialogue.current_options()], ["First time offer", "Leave"])
        self.assertEqual([o["label"] for o in dialogue.current_options({"used": True})], ["Leave"])

    def test_choose_indexes_into_the_flag_filtered_list(self):
        """choose(index, flags) must use the same filtered list
        current_options(flags) displayed, so a UI that only shows visible
        options can pass its own selected index straight through."""
        dialogue = Dialogue("Bartender", {
            "start": {"text": "Hi", "options": [
                {"label": "Hidden", "next": None, "requires_flag": "nope"},
                {"label": "Chat", "next": "chat"},
            ]},
            "chat": {"text": "...", "options": [{"label": "Bye", "next": None}]},
        })
        # Index 0 of the filtered (flags={}) list is "Chat", not "Hidden".
        closed = dialogue.choose(0, {})
        self.assertFalse(closed)
        self.assertEqual(dialogue.current_node, "chat")

    def test_advance_is_immune_to_the_options_own_action_changing_the_filtered_list(self):
        """Regression test: an option hidden by requires_not_flag on the
        very flag its own "set_flag:" action sets used to break navigation
        - applying the action first (as every real caller does, so the
        flag takes effect immediately) then calling choose(index, flags)
        re-derived current_options(flags) *after* the flag was already
        set, so the now-shorter filtered list shifted every later index
        down by one and choose() advanced to the wrong node entirely.
        advance(option) - resolving the option once, before applying its
        actions, and advancing from that same object - must be immune."""
        dialogue = Dialogue("Bartender", {
            "start": {"text": "Hi", "options": [
                {"label": "Buy a round", "next": "thanks", "requires_not_flag": "bought", "action": "set_flag:bought"},
                {"label": "Ask something else", "next": "other"},
            ]},
            "thanks": {"text": "Cheers!", "options": [{"label": "Bye", "next": None}]},
            "other": {"text": "...", "options": [{"label": "Bye", "next": None}]},
        })
        flags = {}
        option = dialogue.current_options(flags)[0]
        self.assertEqual(option["label"], "Buy a round")
        apply_shared_actions(option["action"], SimpleNamespace(flags=flags))
        self.assertTrue(flags["bought"])
        dialogue.advance(option)
        self.assertEqual(dialogue.current_node, "thanks")

    def test_conditional_roots_picks_first_matching_flag_else_plain_root(self):
        dialogue = Dialogue("Bartender", {
            "start": {"text": "Hello stranger.", "options": []},
            "friendly": {"text": "Welcome back!", "options": []},
        }, conditional_roots=[{"flag": "met_before", "node": "friendly"}])
        self.assertEqual(dialogue.resolve_root(), "start")
        self.assertEqual(dialogue.resolve_root({"met_before": True}), "friendly")

    def test_requires_rep_and_requires_rep_below_gate_options(self):
        dialogue = Dialogue("Keeper", {
            "start": {"text": "...", "options": [
                {"label": "Inner vault", "next": None, "requires_rep": "the_vigil:25"},
                {"label": "You work for them", "next": None, "requires_rep_below": "the_vigil:0"},
                {"label": "Leave", "next": None},
            ]},
        })
        self.assertEqual([o["label"] for o in dialogue.current_options({}, {})], ["Leave"])
        self.assertEqual([o["label"] for o in dialogue.current_options({}, {"the_vigil": 30})],
                         ["Inner vault", "Leave"])
        self.assertEqual([o["label"] for o in dialogue.current_options({}, {"the_vigil": -5})],
                         ["You work for them", "Leave"])

    def test_conditional_roots_matches_a_faction_standing_entry(self):
        dialogue = Dialogue("Keeper", {
            "start": {"text": "Stranger.", "options": []},
            "trusted": {"text": "One of ours.", "options": []},
        }, conditional_roots=[{"faction": "the_vigil", "min": 25, "node": "trusted"}])
        self.assertEqual(dialogue.resolve_root({}, {"the_vigil": 10}), "start")
        self.assertEqual(dialogue.resolve_root({}, {"the_vigil": 25}), "trusted")


class TestDialogueSharedActions(unittest.TestCase):
    """option_actions()/apply_shared_actions()/shared_action_blocked_reason() -
    the generic dialogue-action vocabulary usable from any screen driving a
    Dialogue (LocationScreen's station/moon conversations and SpaceScreen's
    ship hails alike)."""

    def test_option_actions_normalizes_single_and_list_forms(self):
        self.assertEqual(option_actions({"label": "x", "next": None}), [])
        self.assertEqual(option_actions({"label": "x", "next": None, "action": "take_loan"}), ["take_loan"])
        self.assertEqual(option_actions({"label": "x", "next": None, "actions": ["a", "b"]}), ["a", "b"])

    def test_set_flag_give_item_and_spend_credits(self):
        possessions = Possessions(credits=100)
        self.assertTrue(apply_shared_actions("set_flag:met_bartender", possessions))
        self.assertTrue(possessions.flags["met_bartender"])
        self.assertTrue(apply_shared_actions("give_item:engraved_flask", possessions))
        self.assertEqual(possessions.items["engraved_flask"], 1)
        self.assertTrue(apply_shared_actions("spend_credits:20", possessions))
        self.assertEqual(possessions.credits, 80)

    def test_adjust_rep_action_shifts_standing_by_a_signed_delta(self):
        possessions = Possessions()
        self.assertTrue(apply_shared_actions("adjust_rep:the_vigil:8", possessions))
        self.assertEqual(possessions.reputation_with("the_vigil"), 8)
        self.assertTrue(apply_shared_actions("adjust_rep:the_vigil:-20", possessions))
        self.assertEqual(possessions.reputation_with("the_vigil"), -12)

    def test_light_beacon_action_sets_the_target_systems_unlock_flag(self):
        possessions = Possessions()
        # With a story, the flag name comes from the system's config.
        self.assertTrue(apply_shared_actions("light_beacon:kiln", possessions, story="the_long_silence"))
        self.assertTrue(possessions.flags.get("beacon_kiln_lit"))
        # Without a story, it falls back to the beacon_<id>_lit convention.
        self.assertTrue(apply_shared_actions("light_beacon:someplace", possessions))
        self.assertTrue(possessions.flags.get("beacon_someplace_lit"))

    def test_unrecognized_action_is_not_handled(self):
        self.assertFalse(apply_shared_actions("buy_ship:shuttle", Possessions()))

    def test_spend_credits_blocked_when_unaffordable(self):
        possessions = Possessions(credits=5)
        self.assertEqual(shared_action_blocked_reason("spend_credits:20", possessions), "not enough credits")
        self.assertIsNone(shared_action_blocked_reason("spend_credits:5", possessions))
        self.assertIsNone(shared_action_blocked_reason("set_flag:x", possessions))


class TestCharacterAIPilotDialogue(unittest.TestCase):
    """Regression test: talking to a visiting AI pilot (e.g. Elena Voss)
    while docked crashed the game - the pilot's Dialogue was once built
    with the old flat (name, [greeting], options) constructor after
    Dialogue became a tree, so current_text() indexed a list with a string
    key and raised. Character.for_ai_pilot() is the sole builder now."""

    def test_pilot_dialogue_is_usable(self):
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="freighter", graphics=None,
            pilot={"name": "Elena Voss", "personality": "Blunt and unhurried."},
            route=[], get_interior_screen=None,
        )
        dialogue = character.person.dialogue
        self.assertEqual(dialogue.current_text(), "Blunt and unhurried.")
        self.assertEqual([o["label"] for o in dialogue.current_options()], ["Nod", "Leave"])
        self.assertTrue(dialogue.choose(0))

    def test_pilot_without_hail_config_falls_back_to_ground_personality(self):
        """A pilot with no "hail_dialogue_tree"/"hail_greeting" of their
        own (see Character.for_ai_pilot) still gets a usable, separate
        hail_dialogue - flavored from the same personality line as their
        ground dialogue, but with comms-flavored closing options instead
        of "Nod"/"Leave"."""
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="freighter", graphics=None,
            pilot={"name": "Elena Voss", "personality": "Blunt and unhurried."},
            route=[], get_interior_screen=None,
        )
        hail = character.person.hail_dialogue
        self.assertIsNot(hail, character.person.dialogue)
        self.assertEqual(hail.current_text(), "Blunt and unhurried.")
        self.assertEqual([o["label"] for o in hail.current_options()], ["Acknowledged", "End transmission"])
        self.assertIsNone(character.person.one_way_hail)

    def test_pilot_with_hail_dialogue_tree_and_one_way_hail(self):
        pilot = {
            "name": "Kade Marsh",
            "personality": "...",
            "one_way_hail": {"range": 500, "message": "Identify yourself."},
            "hail_dialogue_tree": {
                "root": "start",
                "nodes": {"start": {"text": "State your business.", "options": [{"label": "Bye", "next": None}]}},
            },
        }
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot=pilot, route=[], get_interior_screen=None,
        )
        hail = character.person.hail_dialogue
        self.assertEqual(hail.current_text(), "State your business.")
        self.assertEqual(character.person.one_way_hail["message"], "Identify yourself.")
        self.assertIsNone(character.person.escort_flag)

    def test_pilot_with_escort_flag_configured(self):
        pilot = {"name": "Kade Marsh", "personality": "...", "role": "patrol_officer", "escort_flag": "kade_escorting"}
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot=pilot, route=[], get_interior_screen=None,
        )
        self.assertEqual(character.person.escort_flag, "kade_escorting")


class TestLocationScreenPausesDuringDialogue(unittest.TestCase):
    """Regression test: every other NPC in the room kept wandering around
    even while the player was mid-conversation with one of them - only the
    player's own movement paused. update_physics() must freeze every NPC
    in the location while active_dialogue is open, not just the one being
    talked to."""

    def test_npcs_freeze_while_a_dialogue_is_open(self):
        config = {
            "label": "Test Room",
            "npcs": [
                {"name": "Talker", "x": 100, "y": 100, "role": "resident"},
                {"name": "Bystander", "x": 200, "y": 200, "role": "resident"},
            ],
        }
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        talker = next(character for character in screen.npcs if character.person.name == "Talker")
        bystander = next(character for character in screen.npcs if character.person.name == "Bystander")

        screen.active_dialogue = talker.person.dialogue
        before = (bystander.person.x, bystander.person.y)
        for _ in range(50):
            screen.update_physics()
        self.assertEqual((bystander.person.x, bystander.person.y), before)

    def test_npcs_move_normally_with_no_dialogue_open(self):
        config = {
            "label": "Test Room",
            "npcs": [{"name": "Wanderer", "x": 100, "y": 100, "role": "resident"}],
        }
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        wanderer = screen.npcs[0].person
        before = (wanderer.x, wanderer.y)
        for _ in range(200):
            screen.update_physics()
        self.assertNotEqual((wanderer.x, wanderer.y), before)


class TestDialogueClosesOnEsc(unittest.TestCase):
    """ESC (and Enter on the highlighted option) closes an open NPC
    conversation / ship hail, instead of only the mouse ✕ - see
    docs/CONTROLS.md's Dialogue section and docs/DESIGN_PATTERNS.md. ESC
    while a conversation is open must NOT also fall through to the pause
    menu."""

    def _key(self, key):
        return SimpleNamespace(type=pygame_mock.KEYDOWN, key=key)

    def test_esc_closes_a_location_conversation_without_pausing(self):
        config = {"label": "Room", "npcs": [{"name": "Talker", "x": 100, "y": 100, "role": "resident"}]}
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        screen.active_dialogue = screen.npcs[0].person.dialogue
        action = screen.handle_input([self._key(pygame_mock.K_ESCAPE)])
        self.assertIsNone(screen.active_dialogue)
        self.assertNotEqual(action, "pause")

    def test_esc_still_opens_the_pause_menu_with_no_conversation_open(self):
        config = {"label": "Room", "npcs": []}
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        self.assertEqual(screen.handle_input([self._key(pygame_mock.K_ESCAPE)]), "pause")

    def test_esc_closes_a_ship_hail(self):
        gs = SpaceScreen(pilot_name="T", story="default", system_id="sol_alpha")
        gs.in_flight = True
        ai = gs.systems["sol_alpha"].ai_ships[0]
        gs.active_dialogue = ai.person.hail_dialogue
        gs.handle_input([self._key(pygame_mock.K_ESCAPE)])
        self.assertIsNone(gs.active_dialogue)


class TestBartenderConsequenceDialogue(unittest.TestCase):
    """Exercises the bartender's (Bram Solise, sol_alpha.json's "default"
    concourse) "Buy him a round" branch end-to-end against the real story
    config: an option with multiple actions (spend_credits/give_item/
    set_flag) that's itself hidden by requires_not_flag once used, a
    conditional_roots greeting change, and a *different* node's option
    unlocked elsewhere in the tree by requires_flag - the worked
    "conversation with consequences" example (mirrored in space by Kade
    Marsh's hail_dialogue_tree - see TestSpaceScreenHailing)."""

    def _bartender(self, credits=100):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.player.person.possessions.credits = credits
        concourse = game_screen.get_interior_screen(game_screen.station, "default")
        bartender = next(c.person for c in concourse.npcs if c.person.name == "Brahn Ossilis")
        return concourse, bartender

    def test_buying_a_round_spends_credits_grants_item_and_sets_flag(self):
        concourse, bartender = self._bartender(credits=100)
        dialogue = bartender.dialogue
        flags = concourse.player.possessions.flags
        dialogue.current_node = dialogue.resolve_root(flags)
        options = dialogue.current_options(flags)
        round_index = [o["label"] for o in options].index("Buy him a round - 20cr")
        round_option = options[round_index]
        for action in option_actions(round_option):
            concourse._apply_dialogue_action(action)
        # advance(option), not choose(index, flags) - see Dialogue.advance's
        # docstring: the set_flag action just applied hides this very
        # option from current_options(flags) going forward, so re-deriving
        # the filtered list now and re-indexing into it would silently
        # pick a different option.
        dialogue.advance(round_option)

        self.assertEqual(concourse.player.possessions.credits, 80)
        self.assertEqual(concourse.player.possessions.items.get("engraved_flask"), 1)
        self.assertTrue(flags.get("bought_bartender_round"))
        self.assertEqual(dialogue.current_node, "round_bought")

    def test_round_option_disappears_and_greeting_changes_after_buying_once(self):
        concourse, bartender = self._bartender(credits=100)
        dialogue = bartender.dialogue
        flags = concourse.player.possessions.flags
        flags["bought_bartender_round"] = True  # simulate having already bought one

        root = dialogue.resolve_root(flags)
        self.assertEqual(root, "start_friendly")
        dialogue.current_node = root
        labels = [o["label"] for o in dialogue.current_options(flags)]
        self.assertNotIn("Buy him a round - 20cr", labels)

    def test_smuggler_tip_option_is_unlocked_only_after_buying_a_round(self):
        concourse, bartender = self._bartender(credits=100)
        dialogue = bartender.dialogue
        flags = concourse.player.possessions.flags

        dialogue.current_node = "about_station"
        labels_before = [o["label"] for o in dialogue.current_options(flags)]
        self.assertNotIn("Ask about the quiet cargo runs", labels_before)

        flags["bought_bartender_round"] = True
        labels_after = [o["label"] for o in dialogue.current_options(flags)]
        self.assertIn("Ask about the quiet cargo runs", labels_after)


class TestStationTour(unittest.TestCase):
    """The station-interior walkthrough: Sela Cordova offers a tour, which
    starts missions.json's station_tour, and while it's active she trails
    the player on foot (FollowPlayerRoutine) - the interior counterpart to
    Kade Marsh's flying lesson. Also covers the shared Message Log now
    rendered in interiors, and interior NPCs' "ambient" lines."""

    def _concourse(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        concourse = game_screen.get_interior_screen(game_screen.station, "default")
        sela = next(c for c in concourse.npcs if c.person.name == "Selu Vaeren")
        self._game_screen = game_screen  # for tests that need the docked mission tick
        return concourse, sela

    def _accept_tour(self, concourse, sela):
        flags = concourse.player.possessions.flags
        dialogue = sela.person.dialogue
        dialogue.current_node = dialogue.resolve_root(flags)
        option = next(o for o in dialogue.current_options(flags) if o["next"] == "accepted")
        for action in option_actions(option):
            concourse._apply_dialogue_action(action)
        dialogue.advance(option)

    def test_start_mission_dialogue_action_begins_the_mission(self):
        possessions = Possessions()
        missions = utils.get_missions("default")
        self.assertTrue(apply_shared_actions("start_mission:station_tour", possessions, missions))
        self.assertIn("station_tour", possessions.missions)

    def test_start_mission_action_is_a_noop_without_missions_config(self):
        possessions = Possessions()
        apply_shared_actions("start_mission:station_tour", possessions, None)
        self.assertNotIn("station_tour", possessions.missions)

    def test_accepting_selas_tour_starts_the_mission_and_makes_her_escort(self):
        concourse, sela = self._concourse()
        self._accept_tour(concourse, sela)
        possessions = concourse.player.possessions
        self.assertIn("station_tour", possessions.missions)
        self.assertTrue(possessions.flags.get("station_guide_escorting"))
        concourse.update_physics()
        self.assertTrue(sela.escorting)
        self.assertIsInstance(sela.routine, FollowPlayerRoutine)

    def test_sela_follows_the_player_then_stops_when_the_mission_ends(self):
        concourse, sela = self._concourse()
        self._accept_tour(concourse, sela)
        concourse.update_physics()
        # Player moves off across the open concourse; Sela should trail in.
        concourse.player.x, concourse.player.y = sela.person.x + 220, sela.person.y - 90
        start_gap = sela.person.get_distance(concourse.player.x, concourse.player.y)
        for _ in range(200):
            concourse.update_physics()
        end_gap = sela.person.get_distance(concourse.player.x, concourse.player.y)
        self.assertLess(end_gap, start_gap - 100)
        self.assertLessEqual(end_gap, FollowPlayerRoutine.STOP_DISTANCE + 5)

    def test_sela_runs_her_walk_cycle_while_following(self):
        concourse, sela = self._concourse()
        self._accept_tour(concourse, sela)
        concourse.player.x, concourse.player.y = sela.person.x + 220, sela.person.y - 90
        for _ in range(10):
            concourse.update_physics()
        # Following moves through step_toward, so the legs/arms animate
        # instead of gliding along in the standing rest pose.
        self.assertGreater(sela.person.walk_intensity, 0)

        # Mission ends -> escort_flag cleared -> back to a stationary routine.
        concourse.player.possessions.flags["station_guide_escorting"] = False
        concourse.update_physics()
        self.assertFalse(sela.escorting)

    def test_declining_mid_tour_abandons_the_mission_and_stops_the_escort(self):
        concourse, sela = self._concourse()
        self._accept_tour(concourse, sela)
        concourse.update_physics()
        self.assertTrue(sela.escorting)

        flags = concourse.player.possessions.flags
        dialogue = sela.person.dialogue
        dialogue.current_node = dialogue.resolve_root(flags)  # -> "in_progress"
        option = next(o for o in dialogue.current_options(flags) if o.get("next") == "declined")
        for action in option_actions(option):
            concourse._apply_dialogue_action(action)
        dialogue.advance(option)
        self.assertNotIn("station_tour", concourse.player.possessions.missions)
        concourse.update_physics()
        self.assertFalse(sela.escorting)

    def test_tutorial_stages_advance_from_interior_gameplay_flags(self):
        concourse, sela = self._concourse()
        missions = concourse.missions_config
        possessions = concourse.player.possessions
        self._accept_tour(concourse, sela)
        # stage 0 completes on the flag the accept option set
        check_mission_progress(missions, possessions)
        self.assertEqual(possessions.missions["station_tour"], 1)

        for flag in ["walked_interior", "targeted_person", "talked_to_npc",
                     "viewed_mission_log", "viewed_possessions",
                     "scrolled_message_log", "took_loan"]:
            possessions.flags[flag] = True
            check_mission_progress(missions, possessions)
        # 7 flag-driven stages consumed -> now on the "buy a ship" stage
        self.assertEqual(possessions.missions["station_tour"], 8)

        possessions.flags["bought_ship"] = True
        check_mission_progress(missions, possessions)  # -> "board your ship" stage
        # buying doesn't complete the board step - that waits for the undock
        self.assertEqual(possessions.missions["station_tour"], 9)
        possessions.flags["boarded_ship"] = True
        check_mission_progress(missions, possessions)  # -> complete
        self.assertIn("station_tour", possessions.completed_missions)
        self.assertTrue(possessions.flags.get("station_tour_done"))
        self.assertFalse(possessions.flags.get("station_guide_escorting"))

    def test_accepting_the_tour_advances_stage_zero_and_prompts_without_movement(self):
        """Regression: after accepting Sela's offer, stage 0 ("accept the
        offer") completes on the very next docked simulation tick - the
        same `game_screen.update_physics()` main.py runs every frame while
        docked, which is where check_mission_progress lives - with zero
        player movement. That tick also delivers stage 1's one_way_message,
        so the player gets an immediate in-interior prompt instead of the
        tour appearing to do nothing until they happen to walk."""
        concourse, sela = self._concourse()
        self._accept_tour(concourse, sela)
        possessions = concourse.player.possessions
        self.assertEqual(possessions.missions["station_tour"], 0)

        before = len(possessions.message_log)
        self._game_screen.update_physics()  # one docked frame, no movement

        self.assertEqual(possessions.missions["station_tour"], 1,
                         "stage 0 must complete from the docked mission tick alone")
        walk_prompts = [m for m in possessions.message_log[:len(possessions.message_log) - before]
                        if m["sender"] == "Selu Vaeren" and "walk" in m["text"].lower()]
        self.assertTrue(walk_prompts, "stage 1's walk prompt should land immediately on accept")

    def test_message_log_banner_and_alert_fire_when_the_shared_log_grows(self):
        concourse, _ = self._concourse()
        concourse.player.possessions.add_message("Selu Vaeren", "Follow me.")
        concourse._refresh_messages()
        self.assertGreater(concourse.message_alert_timer, 0)
        self.assertIsNotNone(concourse.message_banner)
        self.assertGreater(concourse.message_banner_timer, 0)

    def test_interior_npc_ambient_line_posts_once_when_player_is_close(self):
        concourse, sela = self._concourse()
        concourse.player.x, concourse.player.y = sela.person.x, sela.person.y
        before = len(concourse.player.possessions.message_log)
        concourse._check_npc_ambient()
        concourse._check_npc_ambient()
        self.assertEqual(len(concourse.player.possessions.message_log), before + 1)
        self.assertEqual(concourse.player.possessions.message_log[0]["sender"], "Selu Vaeren")

    def test_background_interior_never_fires_its_ambient_lines(self):
        # A docking AI pilot can build+cache a station interior the player
        # has never entered; update_background_locations then ticks it via
        # update_physics() (player_present defaults False). The NPC ambient
        # check must not run there - otherwise every mission-giver greets
        # the player against a default spawn position (see the concourse's
        # 700px ambient range).
        concourse, sela = self._concourse()
        concourse.player.x, concourse.player.y = sela.person.x, sela.person.y
        before = len(concourse.player.possessions.message_log)
        for _ in range(5):
            concourse.update_physics()  # background tick, no player_present
        self.assertEqual(len(concourse.player.possessions.message_log), before)
        # ...but it does fire on the foreground tick.
        concourse.update_physics(player_present=True)
        self.assertEqual(len(concourse.player.possessions.message_log), before + 1)

    def test_walking_sets_the_walked_interior_flag(self):
        concourse, _ = self._concourse()
        keys = {k: False for k in (pygame_mock.K_LEFT, pygame_mock.K_a, pygame_mock.K_RIGHT,
                                   pygame_mock.K_d, pygame_mock.K_UP, pygame_mock.K_w,
                                   pygame_mock.K_DOWN, pygame_mock.K_s)}
        keys[pygame_mock.K_d] = True  # move right, into open concourse
        concourse._handle_movement(keys)
        self.assertTrue(concourse.player.possessions.flags.get("walked_interior"))

    def _wheel_over_log(self, concourse, max_scroll):
        """Simulate a mouse-wheel tick with the pointer over a drawn,
        `max_scroll`-deep Message Log pane."""
        concourse._message_log_rect = SimpleNamespace(collidepoint=lambda pos: True)
        concourse._message_log_max_scroll = max_scroll
        pygame_mock.mouse.get_pos.return_value = (10, 10)
        concourse.handle_input([SimpleNamespace(type=pygame_mock.MOUSEWHEEL, y=-1)])

    def test_scrolling_the_message_log_sets_the_scrolled_flag(self):
        concourse, _ = self._concourse()
        self._wheel_over_log(concourse, max_scroll=3)
        self.assertTrue(concourse.player.possessions.flags.get("scrolled_message_log"))

    def test_scrolling_an_unscrollable_log_does_not_set_the_flag(self):
        concourse, _ = self._concourse()
        self._wheel_over_log(concourse, max_scroll=0)
        self.assertFalse(concourse.player.possessions.flags.get("scrolled_message_log"))

    def test_scroll_message_log_is_a_station_tour_stage(self):
        stages = utils.get_missions("default")["station_tour"]["stages"]
        self.assertIn("scrolled_message_log", [s.get("complete_flag") for s in stages])


if __name__ == "__main__":
    unittest.main()
