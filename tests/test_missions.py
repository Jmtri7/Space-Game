"""Missions — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


class TestPossessionsMissions(unittest.TestCase):
    """missions/completed_missions (mission/stage progress - see
    game/world/mission.py) round-trip through get_state()/restore_from()/
    from_state() like every other Possessions field."""

    def test_missions_round_trip_through_get_state_and_restore_from(self):
        possessions = Possessions()
        possessions.missions["first_flight"] = 2
        possessions.completed_missions.append("old_mission")
        state = possessions.get_state()
        self.assertEqual(state["missions"], {"first_flight": 2})
        self.assertEqual(state["completed_missions"], ["old_mission"])

        restored = Possessions()
        restored.restore_from(state)
        self.assertEqual(restored.missions, {"first_flight": 2})
        self.assertEqual(restored.completed_missions, ["old_mission"])

    def test_from_state_defaults_to_no_missions_for_a_pre_existing_save(self):
        possessions = Possessions.from_state({"credits": 10})
        self.assertEqual(possessions.missions, {})
        self.assertEqual(possessions.completed_missions, [])


class TestMissionProgress(unittest.TestCase):
    """start_mission()/check_mission_progress()/mission_status_lines() -
    the mission/stage tracker itself. Stage completion is driven entirely
    by Possessions.flags (see game/world/mission.py's module docstring),
    the same flag vocabulary Dialogue's requires_flag/"set_flag:" use."""

    MISSIONS = {
        "first_flight": {
            "title": "First Flight",
            "stages": [
                {"text": "Say hello.", "complete_flag": "said_hello"},
                {"text": "Fly around.", "complete_flag": "used_thrust"},
            ],
        },
    }

    def test_start_mission_begins_at_stage_zero(self):
        possessions = Possessions()
        start_mission(self.MISSIONS, possessions, "first_flight")
        self.assertEqual(possessions.missions, {"first_flight": 0})

    def test_start_mission_is_a_noop_for_an_unknown_id(self):
        possessions = Possessions()
        start_mission(self.MISSIONS, possessions, "no_such_mission")
        self.assertEqual(possessions.missions, {})

    def test_start_mission_does_not_reset_an_already_active_mission(self):
        possessions = Possessions()
        possessions.missions["first_flight"] = 1
        start_mission(self.MISSIONS, possessions, "first_flight")
        self.assertEqual(possessions.missions["first_flight"], 1)

    def test_start_mission_does_not_reactivate_a_completed_mission(self):
        possessions = Possessions()
        possessions.completed_missions.append("first_flight")
        start_mission(self.MISSIONS, possessions, "first_flight")
        self.assertNotIn("first_flight", possessions.missions)

    def test_check_mission_progress_advances_stage_when_flag_is_set(self):
        possessions = Possessions()
        start_mission(self.MISSIONS, possessions, "first_flight")
        possessions.flags["said_hello"] = True
        check_mission_progress(self.MISSIONS, possessions)
        self.assertEqual(possessions.missions["first_flight"], 1)

    def test_check_mission_progress_does_nothing_before_the_flag_is_set(self):
        possessions = Possessions()
        start_mission(self.MISSIONS, possessions, "first_flight")
        check_mission_progress(self.MISSIONS, possessions)
        self.assertEqual(possessions.missions["first_flight"], 0)

    def test_check_mission_progress_completes_the_mission_on_its_last_stage(self):
        possessions = Possessions()
        possessions.missions["first_flight"] = 1  # already on the last stage
        possessions.flags["used_thrust"] = True
        check_mission_progress(self.MISSIONS, possessions)
        self.assertNotIn("first_flight", possessions.missions)
        self.assertEqual(possessions.completed_missions, ["first_flight"])

    def test_check_mission_progress_ignores_an_unknown_mission_id(self):
        """A mission that's active in possessions.missions but no longer
        exists in missions_config (e.g. removed from a later story update)
        must not raise."""
        possessions = Possessions()
        possessions.missions["ghost_mission"] = 0
        check_mission_progress(self.MISSIONS, possessions)  # must not raise
        self.assertEqual(possessions.missions["ghost_mission"], 0)

    def test_start_mission_returns_the_first_stage_when_it_actually_starts(self):
        possessions = Possessions()
        self.assertEqual(start_mission(self.MISSIONS, possessions, "first_flight"), ("first_flight", 0))

    def test_start_mission_returns_none_when_it_does_not_start(self):
        possessions = Possessions()
        self.assertIsNone(start_mission(self.MISSIONS, possessions, "no_such_mission"))
        possessions.missions["first_flight"] = 1
        self.assertIsNone(start_mission(self.MISSIONS, possessions, "first_flight"))

    def test_check_mission_progress_returns_newly_entered_stages(self):
        possessions = Possessions()
        start_mission(self.MISSIONS, possessions, "first_flight")
        possessions.flags["said_hello"] = True
        self.assertEqual(check_mission_progress(self.MISSIONS, possessions), [("first_flight", 1)])

    def test_check_mission_progress_returns_nothing_when_a_mission_completes(self):
        """A stage completing into completed_missions isn't a "newly
        entered stage" - there's no further stage to deliver a message
        for."""
        possessions = Possessions()
        possessions.missions["first_flight"] = 1
        possessions.flags["used_thrust"] = True
        self.assertEqual(check_mission_progress(self.MISSIONS, possessions), [])

    def test_check_mission_progress_returns_nothing_when_no_flag_is_set(self):
        possessions = Possessions()
        start_mission(self.MISSIONS, possessions, "first_flight")
        self.assertEqual(check_mission_progress(self.MISSIONS, possessions), [])


class TestMissionStageFlagReset(unittest.TestCase):
    """"reset_stage_flags_on_activation" - a step can't be satisfied by a
    latching gameplay-event flag (used_turn/used_thrust/...) the player
    tripped before that step was the active one. See mission.py's module
    docstring."""

    MISSIONS = {
        "tut": {
            "title": "Tutorial",
            "reset_stage_flags_on_activation": True,
            "stages": [
                {"text": "Turn.", "complete_flag": "used_turn"},
                {"text": "Thrust.", "complete_flag": "used_thrust"},
                {"text": "Brake.", "complete_flag": "braked_below_threshold", "reset_flags": ["used_brake"]},
            ],
        },
    }

    def test_start_clears_every_stage_flag_that_was_already_latched(self):
        possessions = Possessions()
        possessions.flags.update({"used_turn": True, "used_thrust": True, "used_brake": True})
        start_mission(self.MISSIONS, possessions, "tut")
        self.assertFalse(possessions.flags["used_turn"])
        self.assertFalse(possessions.flags["used_thrust"])
        self.assertFalse(possessions.flags["used_brake"])

    def test_pre_latched_flag_does_not_auto_advance_stage_zero(self):
        possessions = Possessions()
        possessions.flags["used_turn"] = True
        start_mission(self.MISSIONS, possessions, "tut")
        check_mission_progress(self.MISSIONS, possessions)
        self.assertEqual(possessions.missions["tut"], 0)  # must actually turn now

    def test_action_taken_during_an_earlier_stage_does_not_pre_complete_a_later_one(self):
        possessions = Possessions()
        start_mission(self.MISSIONS, possessions, "tut")
        possessions.flags["used_thrust"] = True  # thrusted while still on the "turn" step
        possessions.flags["used_turn"] = True
        check_mission_progress(self.MISSIONS, possessions)  # advances 0 -> 1
        self.assertEqual(possessions.missions["tut"], 1)
        self.assertFalse(possessions.flags["used_thrust"], "entering stage 1 re-clears its flag")
        check_mission_progress(self.MISSIONS, possessions)
        self.assertEqual(possessions.missions["tut"], 1)  # still there until a fresh thrust

    def test_reset_flags_list_is_cleared_on_activation(self):
        possessions = Possessions()
        possessions.missions["tut"] = 1
        possessions.flags["used_thrust"] = True
        possessions.flags["used_brake"] = True  # latched early
        check_mission_progress(self.MISSIONS, possessions)  # 1 -> 2
        self.assertEqual(possessions.missions["tut"], 2)
        self.assertFalse(possessions.flags["used_brake"], "listed in stage 2's reset_flags")

    def test_without_the_opt_in_a_pre_set_flag_still_advances(self):
        missions = {"m": {"title": "M", "stages": [{"text": "x", "complete_flag": "used_turn"}, {"text": "y", "complete_flag": "done"}]}}
        possessions = Possessions()
        possessions.flags["used_turn"] = True
        start_mission(missions, possessions, "m")
        check_mission_progress(missions, possessions)
        self.assertEqual(possessions.missions["m"], 1)

    def test_reset_on_activation_can_be_opted_in_per_stage(self):
        """No mission-level flag - just the one latching stage opts in."""
        missions = {"m": {"title": "M", "stages": [
            {"text": "say hi", "complete_flag": "said_hi"},
            {"text": "turn", "complete_flag": "used_turn", "reset_on_activation": True},
        ]}}
        possessions = Possessions()
        possessions.flags["used_turn"] = True  # latched before the mission
        start_mission(missions, possessions, "m")
        possessions.flags["said_hi"] = True
        check_mission_progress(missions, possessions)  # 0 -> 1, re-clears used_turn
        self.assertEqual(possessions.missions["m"], 1)
        self.assertFalse(possessions.flags["used_turn"])
        check_mission_progress(missions, possessions)
        self.assertEqual(possessions.missions["m"], 1)  # waits for a fresh turn

    def test_a_stage_can_opt_out_of_a_mission_level_default(self):
        missions = {"m": {"title": "M", "reset_stage_flags_on_activation": True, "stages": [
            {"text": "hail", "complete_flag": "hailed_pilot:X"},
            {"text": "accept", "complete_flag": "accepted", "reset_on_activation": False},
        ]}}
        possessions = Possessions()
        start_mission(missions, possessions, "m")
        # One frozen conversation: both the hail flag and the accept flag
        # get set before check_mission_progress next runs.
        possessions.flags["hailed_pilot:X"] = True
        possessions.flags["accepted"] = True
        check_mission_progress(missions, possessions)  # 0 -> 1; must NOT wipe "accepted"
        self.assertTrue(possessions.flags["accepted"])
        check_mission_progress(missions, possessions)  # 1 -> done
        self.assertEqual(possessions.completed_missions, ["m"])


class TestMissionEscortAndAbandon(unittest.TestCase):
    """escort_flag/on_end_flags (see mission.py's _on_mission_end) and
    abandon_mission() - the mechanism behind an NPC escorting the player
    for a mission's duration (see person.escort_flag/
    SpaceScreen._sync_escorts) and a dialogue option letting the player
    decline one (e.g. Kade Marsh's "No thanks, I've got it.")."""

    MISSIONS = {
        "first_flight": {
            "title": "First Flight",
            "escort_flag": "kade_escorting",
            "on_start_flags": ["kade_escorting"],
            "on_end_flags": ["kade_tutorial_done"],
            "stages": [
                {"text": "Say hello.", "complete_flag": "said_hello"},
            ],
        },
    }

    def test_start_mission_sets_on_start_flags(self):
        possessions = Possessions()
        start_mission(self.MISSIONS, possessions, "first_flight")
        self.assertTrue(possessions.flags.get("kade_escorting"))

    def test_finishing_a_mission_clears_its_escort_flag_and_sets_on_end_flags(self):
        possessions = Possessions()
        possessions.missions["first_flight"] = 0
        possessions.flags["kade_escorting"] = True
        possessions.flags["said_hello"] = True
        check_mission_progress(self.MISSIONS, possessions)
        self.assertEqual(possessions.completed_missions, ["first_flight"])
        self.assertFalse(possessions.flags["kade_escorting"])
        self.assertTrue(possessions.flags["kade_tutorial_done"])

    def test_abandon_mission_removes_it_without_completing_it(self):
        possessions = Possessions()
        possessions.missions["first_flight"] = 0
        abandon_mission(self.MISSIONS, possessions, "first_flight")
        self.assertNotIn("first_flight", possessions.missions)
        self.assertNotIn("first_flight", possessions.completed_missions)

    def test_abandon_mission_also_clears_escort_flag_and_sets_on_end_flags(self):
        possessions = Possessions()
        possessions.missions["first_flight"] = 0
        possessions.flags["kade_escorting"] = True
        abandon_mission(self.MISSIONS, possessions, "first_flight")
        self.assertFalse(possessions.flags["kade_escorting"])
        self.assertTrue(possessions.flags["kade_tutorial_done"])

    def test_abandon_mission_is_a_noop_for_a_mission_that_is_not_active(self):
        possessions = Possessions()
        abandon_mission(self.MISSIONS, possessions, "first_flight")  # must not raise
        self.assertNotIn("kade_escorting", possessions.flags)

    def test_on_start_rep_and_on_end_rep_shift_faction_standing(self):
        missions = {"job": {
            "title": "A Job",
            "on_start_rep": {"harbor_authority": 4},
            "on_end_rep": {"harbor_authority": 10, "ninefold_combine": -6},
            "stages": [{"text": "Do it.", "complete_flag": "did_it"}],
        }}
        possessions = Possessions()
        start_mission(missions, possessions, "job")
        self.assertEqual(possessions.reputation_with("harbor_authority"), 4)
        possessions.flags["did_it"] = True
        check_mission_progress(missions, possessions)
        self.assertEqual(possessions.reputation_with("harbor_authority"), 14)
        self.assertEqual(possessions.reputation_with("ninefold_combine"), -6)


class TestMissionOneWayMessage(unittest.TestCase):
    """A stage's optional "one_way_message" (see mission.py's module
    docstring) isn't read by mission.py itself - it's just data a caller
    (SpaceScreen._deliver_stage_message) looks up using the (mission_id,
    stage_index) pairs start_mission()/check_mission_progress() return."""

    MISSIONS = {
        "first_flight": {
            "title": "First Flight",
            "stages": [
                {"text": "Say hello.", "complete_flag": "said_hello"},
                {"text": "Fly around.", "complete_flag": "used_thrust",
                 "one_way_message": {"sender": "Kade Marsh", "text": "Now try flying."}},
            ],
        },
    }

    def test_advanced_stage_carries_its_one_way_message(self):
        possessions = Possessions()
        start_mission(self.MISSIONS, possessions, "first_flight")
        possessions.flags["said_hello"] = True
        advanced = check_mission_progress(self.MISSIONS, possessions)
        mission_id, stage_index = advanced[0]
        message = self.MISSIONS[mission_id]["stages"][stage_index]["one_way_message"]
        self.assertEqual(message, {"sender": "Kade Marsh", "text": "Now try flying."})

    def test_first_stage_has_no_one_way_message_in_this_fixture(self):
        """Mirrors the real first_flight mission's stage 0 - delivered via
        pilots.json's proximity-gated one_way_hail instead (see
        SpaceScreen._check_one_way_hails), not a stage-entry message."""
        self.assertNotIn("one_way_message", self.MISSIONS["first_flight"]["stages"][0])

    def test_mission_status_lines_reports_active_and_completed(self):
        possessions = Possessions()
        possessions.missions["first_flight"] = 1
        possessions.completed_missions.append("first_flight")  # contrived, but exercises both branches
        lines = mission_status_lines(self.MISSIONS, possessions)
        titles = [title for title, _, _ in lines]
        self.assertIn("First Flight", titles)
        self.assertIn("First Flight (Complete)", titles)
        active = next(entry for entry in lines if entry[0] == "First Flight")
        self.assertEqual(active[1], ["Say hello.", "Fly around."])
        self.assertEqual(active[2], 1)
        completed = next(entry for entry in lines if entry[0] == "First Flight (Complete)")
        self.assertIsNone(completed[2])


class TestMissionLog(unittest.TestCase):
    """The mission ReportMenu's handle_input() - draw() is exercised
    implicitly by TestMissionProgress's data (mission_status_lines) and isn't
    worth testing against a mocked pygame surface here."""

    MISSIONS = {
        "m1": {"title": "First", "stages": [
            {"text": "Do A", "complete_flag": "a"},
            {"text": "Do B", "complete_flag": "b"},
            {"text": "Do C", "complete_flag": "c"}]},
        "m2": {"title": "Second", "stages": [{"text": "Only step", "complete_flag": "x"}]},
    }

    def test_has_a_close_button_and_no_hotkey_label(self):
        menu = ReportMenu(*mission_report({}, Possessions()))
        self.assertEqual([b[0] for b in menu.buttons()], ["close"])
        self.assertEqual(menu.buttons()[0][1], "Close")  # not "Close (N)" anymore

    def test_keyboard_does_nothing(self):
        menu = ReportMenu(*mission_report(self.MISSIONS, Possessions()))
        for key in (pygame_mock.K_ESCAPE, pygame_mock.K_n, pygame_mock.K_RIGHTBRACKET, pygame_mock.K_DOWN):
            self.assertIsNone(menu.handle_input([SimpleNamespace(type=pygame_mock.KEYDOWN, key=key)]))
        self.assertEqual(menu.tab_index, 0)
        self.assertEqual(menu.scroll, 0)

    def test_report_splits_active_and_completed_onto_tabs(self):
        possessions = Possessions()
        possessions.missions["m1"] = 1
        possessions.completed_missions.append("m2")
        title, columns, tabs = mission_report(self.MISSIONS, possessions)
        self.assertEqual([t[0] for t in tabs], ["Active", "Completed"])
        active_headings = [sec[0] for sec in tabs[0][1][0]]
        done_headings = [sec[0] for sec in tabs[1][1][0]]
        self.assertIn("First", active_headings)
        self.assertIn("Second", done_headings)

    def test_stage_lines_are_numbered_and_marked(self):
        possessions = Possessions()
        possessions.missions["m1"] = 1  # step 1 done, on step 2
        _, _, tabs = mission_report(self.MISSIONS, possessions)
        first_section_lines = [line for line, _color in tabs[0][1][0][0][1]]
        self.assertEqual(first_section_lines, ["[x] 1. Do A", "-> 2. Do B"])

    def test_empty_tabs_show_a_placeholder(self):
        _, _, tabs = mission_report(self.MISSIONS, Possessions())
        self.assertEqual(tabs[0][1][0][0][1][0][0], "No active missions.")
        self.assertEqual(tabs[1][1][0][0][1][0][0], "No completed missions yet.")

    def test_selecting_a_tab_switches_and_resets_scroll(self):
        menu = ReportMenu(*mission_report(self.MISSIONS, Possessions()))
        menu.scroll = 5
        menu._select_tab(1)
        self.assertEqual(menu.tab_index, 1)
        self.assertEqual(menu.scroll, 0)
        menu._select_tab(2)  # wraps
        self.assertEqual(menu.tab_index, 0)

    def test_mouse_wheel_scrolls_within_bounds(self):
        menu = ReportMenu(*mission_report(self.MISSIONS, Possessions()))
        menu._max_scroll = 3  # normally set by draw()
        menu.handle_input([SimpleNamespace(type=pygame_mock.MOUSEWHEEL, y=-5)])
        self.assertEqual(menu.scroll, 3)
        menu.handle_input([SimpleNamespace(type=pygame_mock.MOUSEWHEEL, y=10)])
        self.assertEqual(menu.scroll, 0)

    def test_possessions_report_has_no_tabs(self):
        result = possessions_report(Possessions())
        self.assertEqual(len(result), 2)
        self.assertIsNone(ReportMenu(*result).tabs)


class TestActsAndEndings(unittest.TestCase):
    """utils.current_act (story.json "acts" + advance_flags), the
    set_exclusive_flag / end_story dialogue actions, and the EndingScreen
    (game/ui/ending_screen.py) - Phase 5's arc / ending framework."""

    def test_current_act_advances_as_advance_flags_are_set(self):
        self.assertEqual(utils.current_act("the_long_silence", {}).get("name"), "I - Contact")
        self.assertEqual(utils.current_act("the_long_silence", {"act_pressure": True}).get("name"), "II - Pressure")
        self.assertEqual(
            utils.current_act("the_long_silence", {"act_pressure": True, "act_span": True}).get("name"),
            "III - The Span")

    def test_current_act_is_empty_for_a_story_with_no_acts(self):
        self.assertEqual(utils.current_act("default", {}), {})

    def test_set_exclusive_flag_sets_one_and_clears_the_rest_of_its_group(self):
        p = Possessions()
        self.assertTrue(apply_shared_actions("set_exclusive_flag:patron:harbor_authority", p))
        self.assertTrue(p.flags["patron:harbor_authority"])
        apply_shared_actions("set_exclusive_flag:patron:the_vigil", p)
        self.assertFalse(p.flags["patron:harbor_authority"])
        self.assertTrue(p.flags["patron:the_vigil"])
        # a differently-prefixed flag is untouched
        p.flags["allegiance:kiln"] = True
        apply_shared_actions("set_exclusive_flag:patron:the_drift", p)
        self.assertTrue(p.flags["allegiance:kiln"])

    def test_end_story_sets_the_flags_resolve_ending_reads(self):
        p = Possessions()
        self.assertIsNone(utils.resolve_ending(p.flags))
        self.assertTrue(apply_shared_actions("end_story:sever", p))
        self.assertTrue(p.flags["story_over"])
        self.assertEqual(utils.resolve_ending(p.flags), "sever")

    def test_ending_report_picks_faction_lines_by_final_standing(self):
        p = Possessions()
        p.reputation = {"harbor_authority": 40, "ninefold_combine": -60}
        title, columns = ending_report("the_long_silence", "restore", p)
        self.assertEqual(title, "The Relay Restored")
        text = " ".join(line for _h, lines in columns[0] for line, _c in lines)
        self.assertIn("credits you by name", text)      # harbor_authority: allied
        self.assertIn("shoots first", text)             # ninefold_combine: hostile

    def test_ending_screen_button_returns_menu(self):
        p = Possessions()
        es = EndingScreen(*ending_report("the_long_silence", "hold_middle", p))
        self.assertEqual(es.buttons()[0][0], "menu")

    def test_every_ending_covers_every_faction_and_band(self):
        # PLAN Phase 7.1b - the restore ending used to list `the_drift`
        # twice (one block missing `hostile`); guard the full matrix.
        endings = utils.get_endings("the_long_silence")
        factions = list(utils.get_factions("the_long_silence"))
        for ending_id in ("restore", "sever", "hold_middle"):
            fe = endings[ending_id]["faction_epilogue"]
            for fid in factions:
                for band in ("allied", "neutral", "hostile"):
                    self.assertIn(band, fe.get(fid, {}),
                                  f"{ending_id}/{fid} missing {band}")


class TestContentGate(unittest.TestCase):
    """game/world/content_gate.py - the flag / reputation visibility check
    shared by SpaceScreen's conditional AI ships and LocationScreen's
    conditional NPCs / structures."""

    def test_an_entry_with_no_gate_keys_always_passes(self):
        self.assertFalse(is_gated({"name": "Bob"}))
        self.assertTrue(passes_content_gate({"name": "Bob"}, {}, {}))

    def test_requires_flag_and_requires_not_flag(self):
        self.assertTrue(is_gated({"requires_flag": "x"}))
        self.assertFalse(passes_content_gate({"requires_flag": "x"}, {}, {}))
        self.assertTrue(passes_content_gate({"requires_flag": "x"}, {"x": True}, {}))
        self.assertFalse(passes_content_gate({"requires_not_flag": "x"}, {"x": True}, {}))
        self.assertTrue(passes_content_gate({"requires_not_flag": "x"}, {}, {}))

    def test_requires_rep_and_requires_rep_below(self):
        self.assertFalse(passes_content_gate({"requires_rep": "kiln:10"}, {}, {}))
        self.assertTrue(passes_content_gate({"requires_rep": "kiln:10"}, {}, {"kiln": 10}))
        self.assertTrue(passes_content_gate({"requires_rep_below": "kiln:-20"}, {}, {"kiln": -30}))
        self.assertFalse(passes_content_gate({"requires_rep_below": "kiln:-20"}, {}, {"kiln": 0}))

    def test_all_conditions_must_hold(self):
        entry = {"requires_flag": "war", "requires_rep_below": "kiln:0"}
        self.assertFalse(passes_content_gate(entry, {"war": True}, {"kiln": 5}))
        self.assertTrue(passes_content_gate(entry, {"war": True}, {"kiln": -5}))


class TestConditionalWorldContent(unittest.TestCase):
    """Flag/reputation-gated NPCs and structures appear/disappear on interior
    (re-)entry (LocationScreen._apply_content_gates via arrive_from); gated
    AI ships appear/disappear on system (re-)entry
    (SpaceScreen._sync_conditional_ships). See docs/ARCHITECTURE.md."""

    def _interior(self, possessions):
        cfg = {
            "label": "Bay",
            "rooms": [{"shape": "circle", "center": [400, 400], "radius": 300, "sides": 24}],
            "portals": [{"x": 400, "y": 250, "return_to_ship": True}],
            "structures": [
                {"x": 400, "y": 400, "building_type": "vherathi_lamp"},
                {"x": 500, "y": 400, "building_type": "vherathi_lamp", "requires_flag": "mobilised"},
            ],
            "npcs": [
                {"name": "Local", "x": 350, "y": 400, "role": "resident"},
                {"name": "Refugee", "x": 450, "y": 400, "role": "resident", "requires_flag": "lane_open"},
            ],
        }
        return LocationScreen(config_data=cfg, world_width=800, world_height=800,
                              story="default", player_possessions=possessions)

    def test_gated_npc_and_structure_appear_when_the_flag_is_set(self):
        pos = Possessions()
        sc = self._interior(pos)
        self.assertEqual(sorted(c.person.name for c in sc.npcs), ["Local"])
        self.assertEqual(len(sc.structures), 1)
        pos.flags["lane_open"] = True
        pos.flags["mobilised"] = True
        sc.arrive_from("ship")
        self.assertEqual(sorted(c.person.name for c in sc.npcs), ["Local", "Refugee"])
        self.assertEqual(len(sc.structures), 2)

    def test_gated_npc_disappears_again_when_the_flag_clears(self):
        pos = Possessions()
        pos.flags["lane_open"] = True
        sc = self._interior(pos)
        self.assertIn("Refugee", [c.person.name for c in sc.npcs])
        pos.flags["lane_open"] = False
        sc.arrive_from("ship")
        self.assertNotIn("Refugee", [c.person.name for c in sc.npcs])

    def test_sync_conditional_ships_adds_and_removes_a_gated_ai_ship(self):
        gs = SpaceScreen(pilot_name="T", story="the_long_silence", system_id="verdance")
        pos = gs.player.person.possessions

        def has_raider():
            return any(getattr(s, "_spawn_cfg", {}).get("name") == "Combine Raider"
                       for s in gs.systems["verdance"].ai_ships)

        self.assertFalse(has_raider())
        pos.reputation["ninefold_combine"] = -30
        gs._sync_conditional_ships()
        self.assertTrue(has_raider())
        pos.reputation["ninefold_combine"] = 0
        gs._sync_conditional_ships()
        self.assertFalse(has_raider())


class TestLongSilenceDeepening(unittest.TestCase):
    """Act II/III deepening (docs/ACT2_3_DEEPENING.md) against the real
    story config - one class per phase's plumbing."""

    def setUp(self):
        self.missions = utils.get_missions("the_long_silence")
        self.dispatches = utils.get_dispatches("the_long_silence")

    # -- Phase 2: the refugee-barge escort -----------------------------
    def test_escort_barge_mission_shape(self):
        m = self.missions["escort_barge"]
        self.assertEqual(m["escort_flag"], "barge_under_escort")
        self.assertIn("barge_under_escort", m["on_start_flags"])
        self.assertIn("escort_barge_done", m["on_end_flags"])
        self.assertEqual(m["stages"][0]["complete_flag"], "hailed_pilot:Barge-mother Sethe")

    def test_drift_convoy_call_offers_escort_barge(self):
        d = self.dispatches["drift_convoy_call"]
        self.assertEqual(d["requires_flag"], "combine_mobilised")
        self.assertEqual(d["start_mission"], "escort_barge")

    def test_the_barge_ai_ship_is_gated_in_both_verdance_and_ossuary(self):
        for sysid in ("verdance", "ossuary"):
            sysj = utils.load_json(f"config/stories/the_long_silence/systems/{sysid}.json")
            barge = [s for s in sysj["ai_ships"] if s.get("pilot") == "barge_sethe"]
            self.assertEqual(len(barge), 1, sysid)
            self.assertEqual(barge[0]["requires_flag"], "barge_under_escort")

    # -- Phase 3: front_recon + the reputation fork + carrier pledge ---
    def _station_npc(self, system_id, npc_name):
        sysj = utils.load_json(f"config/stories/the_long_silence/systems/{system_id}.json")
        for n in sysj["station"]["interiors"]["default"]["npcs"]:
            if n["name"] == npc_name:
                return n
        raise AssertionError(f"{npc_name} not in {system_id}")

    def _dialogue(self, cfg):
        t = cfg["dialogue_tree"]
        return Dialogue(cfg["name"], t["nodes"], t.get("root", "start"), t.get("conditional_roots"))

    def test_front_recon_mission_shape(self):
        m = self.missions["front_recon"]
        self.assertIn("front_recon_active", m["on_start_flags"])
        self.assertIn("front_recon_done", m["on_end_flags"])
        self.assertEqual([s["complete_flag"] for s in m["stages"]],
                         ["jumped_to:kiln", "front_recon_have_record",
                          "jumped_to:verdance", "front_recon_delivered"])

    def test_carrier_recon_call_offers_front_recon_after_the_open_hand(self):
        d = self.dispatches["carrier_recon_call"]
        self.assertEqual(d["requires_flag"], "dispatch:carrier_open_hand")
        self.assertEqual(d["start_mission"], "front_recon")

    def test_the_pad_clerk_hands_over_the_record_only_during_the_mission(self):
        dlg = self._dialogue(self._station_npc("kiln", "Assay-clerk Dorn"))
        dlg.current_node = dlg.resolve_root({"front_recon_active": True})
        labels = [o["label"] for o in dlg.current_options({"front_recon_active": True})]
        self.assertTrue(any("timed in at" in l or "relight signal" in l.lower() for l in labels))
        # not offered before the mission, and not after the record is taken
        self.assertFalse(dlg.current_options({}) and
                         any("relight" in o["label"].lower() for o in dlg.current_options({})))
        self.assertFalse(any("relight" in o["label"].lower() for o in dlg.current_options(
            {"front_recon_active": True, "front_recon_have_record": True})))

    def test_each_fork_npc_offers_exactly_one_gated_delivery(self):
        cases = [
            ("halcyon", "Records Keeper Amsel", "front_to_authority"),
            ("verdance", "Sela of Highcanopy", "front_to_drift"),
            ("ossuary", "Keeper Aramis", "front_to_vigil"),
        ]
        for system_id, name, want_flag in cases:
            dlg = self._dialogue(self._station_npc(system_id, name))
            flags = {"front_recon_have_record": True, "authority_briefed": True,
                     "assembly_done": True, "vigil_record_done": True}
            dlg.current_node = dlg.resolve_root(flags)
            delivery = [o for o in dlg.current_options(flags)
                        if f"set_flag:{want_flag}" in o.get("actions", [])]
            self.assertEqual(len(delivery), 1, f"{name}")
            # gone once delivered
            flags["front_recon_delivered"] = True
            self.assertEqual([o for o in dlg.current_options(flags)
                              if f"set_flag:{want_flag}" in o.get("actions", [])], [])

    def test_verdance_carrier_berth_carries_the_fifth_pledge(self):
        dlg = self._dialogue(self._station_npc("verdance", "Carrier off the Slip"))
        rep = {"free_carrier": 30}
        dlg.current_node = dlg.resolve_root({}, rep)
        self.assertEqual(dlg.current_node, "warm")
        pledge = [o for o in dlg.current_options({}, rep)
                  if "set_exclusive_flag:patron:free_carrier" in o.get("actions", [])]
        self.assertEqual(len(pledge), 1)

    # -- Phase 4: the Act III Choir sequence ---------------------------
    def test_core_choir_mission_shape(self):
        m = self.missions["the_core_choir"]
        self.assertIn("core_choir_started", m["on_start_flags"])
        self.assertIn("core_choir_done", m["on_end_flags"])
        self.assertEqual([s["complete_flag"] for s in m["stages"]],
                         ["read_hub_archive", "heard_the_signal", "core_choir_reported"])
        self.assertTrue(m["stages"][0]["reset_on_activation"])

    def test_archivist_logs_set_an_archive_reason(self):
        arch = self._station_npc("the_span", "Archivist of the Choir")
        nodes = arch["dialogue_tree"]["nodes"]
        for log, reason in [("quarantine", "archive:quarantine"),
                            ("scorched", "archive:scorched"), ("accident", "archive:accident")]:
            enough = [o for o in nodes[log]["options"] if o["label"] == "Enough."][0]
            self.assertIn(f"set_exclusive_flag:{reason}", enough["actions"])
            self.assertIn("set_flag:read_hub_archive", enough["actions"])

    def test_core_voice_opens_on_the_reading_keyed_to_the_lingered_log(self):
        cv = self._dialogue(self._station_npc("the_span", "the Core Voice"))
        self.assertEqual(cv.resolve_root({"archive:quarantine": True}), "ai")
        self.assertEqual(cv.resolve_root({"archive:scorched": True}), "person")
        self.assertEqual(cv.resolve_root({"archive:accident": True}), "script")
        self.assertEqual(cv.resolve_root({}), "start")

    def test_core_voice_enough_leaves_the_player_believing_exactly_one(self):
        for node, sig in [("person", "signal:person"), ("ai", "signal:ai"), ("script", "signal:script")]:
            cv = self._dialogue(self._station_npc("the_span", "the Core Voice"))
            cv.current_node = node
            enough = [o for o in cv.current_options({}) if o["label"].startswith("Enough")][0]
            self.assertIn(f"set_exclusive_flag:{sig}", enough["actions"])
            self.assertIn("set_flag:heard_the_signal", enough["actions"])

    def test_first_warden_gates_the_fork_behind_the_choir_mission(self):
        fw = self._dialogue(self._station_npc("the_span", "First Warden"))
        # cold: opens on "start", which starts the mission, not the fork
        self.assertEqual(fw.resolve_root({}), "start")
        start_opts = fw.current_options({})
        self.assertTrue(any(o.get("action") == "start_mission:the_core_choir" for o in start_opts))
        self.assertFalse(any((o.get("next") or "").startswith("confirm_") for o in start_opts))
        # after the mission: opens straight on the fork with all three endings
        fw2 = self._dialogue(self._station_npc("the_span", "First Warden"))
        self.assertEqual(fw2.resolve_root({"core_choir_done": True}), "choose")
        fw2.current_node = "choose"
        actions = []
        for o in fw2.current_options({}, {"the_vigil": 20}):
            nxt = o.get("next")
            if nxt and nxt.startswith("confirm_"):
                actions += [x["action"] for x in fw2.nodes[nxt]["options"] if x.get("action")]
        self.assertEqual(set(actions), {"end_story:restore", "end_story:sever", "end_story:hold_middle"})

    def test_first_warden_report_option_appears_after_hearing_the_signal(self):
        fw = self._dialogue(self._station_npc("the_span", "First Warden"))
        flags = {"core_choir_started": True, "heard_the_signal": True}
        fw.current_node = fw.resolve_root(flags)
        report = [o for o in fw.current_options(flags) if o.get("action") == "set_flag:core_choir_reported"]
        self.assertEqual(len(report), 1)

    # -- Phase 5: Ring Segment Four + flag-keyed epilogues ------------
    def test_segment_four_npcs_are_all_reachable_from_the_entrance(self):
        gs = SpaceScreen(pilot_name="T", story="the_long_silence", system_id="the_span")
        it = gs.get_interior_screen(gs.moon, "city")
        it.arrive_from("ship")
        names = [c.person.name for c in it.npcs]
        self.assertEqual(len(names), 5)
        self.assertIn("Choir-hand Aud", names)
        start = it.entrance if isinstance(getattr(it, "entrance", None), tuple) else \
            (it.npcs and (it.portals[0]["x"], it.portals[0]["y"]) if getattr(it, "portals", None) else None)
        for c in it.npcs:
            p = c.person
            self.assertTrue(it.can_move_to(p.x, p.y), p.name)

    def test_threa_kin_reacts_to_the_signal_reading(self):
        it = utils.load_json("config/stories/the_long_silence/systems/the_span.json")
        threa = [n for n in it["moon"]["interiors"]["city"]["npcs"]
                 if n["name"] == "Segment Warden Threa-kin"][0]
        dlg = self._dialogue(threa)
        self.assertEqual(dlg.resolve_root({"signal:person": True}), "r_person")
        self.assertEqual(dlg.resolve_root({"signal:ai": True}), "r_ai")
        self.assertEqual(dlg.resolve_root({"signal:script": True}), "r_script")
        self.assertEqual(dlg.resolve_root({}), "start")

    def test_flag_keyed_epilogue_line_wins_over_the_band(self):
        p = Possessions()
        p.reputation = {"harbor_authority": -60}   # hostile band
        title, columns = ending_report("the_long_silence", "restore", p)
        text = " ".join(l for _h, lines in columns[0] for l, _c in lines)
        self.assertIn("nearly cost them it", text)   # hostile band line
        p.flags["front_to_authority"] = True
        _t, columns = ending_report("the_long_silence", "restore", p)
        text = " ".join(l for _h, lines in columns[0] for l, _c in lines)
        self.assertIn("carried to them by hand", text)
        self.assertNotIn("nearly cost them it", text)

    def test_every_ending_still_covers_every_faction_and_band(self):
        endings = utils.get_endings("the_long_silence")
        for eid in ("restore", "sever", "hold_middle"):
            for fid in utils.get_factions("the_long_silence"):
                fe = endings[eid]["faction_epilogue"].get(fid, {})
                for b in ("allied", "neutral", "hostile"):
                    self.assertIn(b, fe, f"{eid}/{fid}/{b}")

    # -- follow-up: patron pledge reachable after the anchor mission ---
    def test_patron_pledge_is_reachable_on_the_completion_node(self):
        cases = [
            ("kiln", "Factor Tol", {"combine_contract_done": True, "combine_tally_filed": True},
             "ninefold_combine", "patron:ninefold_combine"),
            ("verdance", "Sela of Highcanopy", {"assembly_done": True},
             "the_drift", "patron:the_drift"),
            ("ossuary", "Keeper Aramis", {"vigil_record_done": True, "vigil_read_vault": True},
             "the_vigil", "patron:the_vigil"),
        ]
        for system_id, name, flags, fid, pflag in cases:
            dlg = self._dialogue(self._station_npc(system_id, name))
            rep = {fid: 30}
            dlg.current_node = dlg.resolve_root(flags, rep)
            pledge = [o for o in dlg.current_options(flags, rep)
                      if f"set_exclusive_flag:{pflag}" in o.get("actions", [])]
            self.assertEqual(len(pledge), 1, f"{name} on {dlg.current_node}")
            # gone once pledged, node still has a way out
            flags[pflag] = True
            opts = dlg.current_options(flags, rep)
            self.assertFalse(any(f"set_exclusive_flag:{pflag}" in o.get("actions", []) for o in opts))
            self.assertTrue(any(o.get("next") is None for o in opts), f"{name}: no exit on {dlg.current_node}")

    def test_sync_conditional_ships_spawns_and_culls_the_barge(self):
        gs = SpaceScreen(pilot_name="T", story="the_long_silence", system_id="verdance")
        pos = gs.player.person.possessions

        def has_barge():
            return any(getattr(s, "_spawn_cfg", {}).get("pilot") == "barge_sethe"
                       for s in gs.systems["verdance"].ai_ships)

        self.assertFalse(has_barge())
        pos.flags["barge_under_escort"] = True
        gs._sync_conditional_ships()
        self.assertTrue(has_barge())
        pos.flags["barge_under_escort"] = False
        gs._sync_conditional_ships()
        self.assertFalse(has_barge())


class TestSystemUnlocked(unittest.TestCase):
    """utils.system_unlocked - a system is reachable unless "locked" and its
    "unlock_flag" isn't set (see docs/CONTROLS.md's Star Map / the story's
    beacon progression)."""

    def test_a_system_with_no_locked_key_is_always_reachable(self):
        self.assertTrue(utils.system_unlocked({"name": "Home"}, {}))

    def test_a_locked_system_is_unreachable_until_its_unlock_flag_is_set(self):
        cfg = {"locked": True, "unlock_flag": "beacon_kiln_lit"}
        self.assertFalse(utils.system_unlocked(cfg, {}))
        self.assertTrue(utils.system_unlocked(cfg, {"beacon_kiln_lit": True}))

    def test_a_locked_system_with_no_unlock_flag_stays_permanently_dark(self):
        self.assertFalse(utils.system_unlocked({"locked": True}, {"anything": True}))


class TestBeaconJumpGating(unittest.TestCase):
    """Locked systems can't be jumped to or picked on the Star Map until
    their beacon is lit; SpaceScreen posts a galaxy-wide message the frame
    a beacon flag flips. Uses the_long_silence, whose outer systems are
    beacon-locked."""

    def test_try_jump_refuses_a_locked_destination(self):
        gs = SpaceScreen(pilot_name="Test", story="the_long_silence", system_id="halcyon")
        gs.player.x, gs.player.y = 100, 100  # well clear of centre
        gs.selected_system_id = "kiln"
        gs.try_jump()
        self.assertIsNone(gs.jump_state)
        self.assertGreater(gs.jump_message_timer, 0)
        self.assertIn("Kiln", gs.jump_message)

    def test_try_jump_allows_the_destination_once_its_beacon_is_lit(self):
        gs = SpaceScreen(pilot_name="Test", story="the_long_silence", system_id="halcyon")
        gs.player.x, gs.player.y = 100, 100
        gs.player.person.possessions.flags["beacon_kiln_lit"] = True
        gs.selected_system_id = "kiln"
        gs.try_jump()
        self.assertIsNotNone(gs.jump_state)

    def test_star_map_drops_a_locked_initial_selection_and_wont_pick_one(self):
        sm = StarMap("the_long_silence", "halcyon", "kiln", flags={})
        self.assertEqual(sm.selected_system_id, "halcyon")
        sm._screen_positions = {"kiln": (100, 100)}
        self.assertIsNone(sm._system_at((100, 100)))
        sm_lit = StarMap("the_long_silence", "halcyon", "kiln", flags={"beacon_kiln_lit": True})
        self.assertEqual(sm_lit.selected_system_id, "kiln")

    def test_check_beacons_posts_a_message_the_frame_a_beacon_lights(self):
        gs = SpaceScreen(pilot_name="Test", story="the_long_silence", system_id="halcyon")
        possessions = gs.player.person.possessions
        gs._lit_beacons = None
        gs._check_beacons()  # seed - nothing lit yet
        self.assertEqual(possessions.message_log, [])
        possessions.flags["beacon_verdance_lit"] = True
        gs._check_beacons()
        self.assertEqual(len(possessions.message_log), 1)
        self.assertIn("Verdance", possessions.message_log[0]["text"])
        gs._check_beacons()  # no duplicate on the next frame
        self.assertEqual(len(possessions.message_log), 1)

    def test_check_beacons_stays_silent_for_an_unlock_silent_system(self):
        gs = SpaceScreen(pilot_name="Test", story="the_long_silence", system_id="halcyon")
        possessions = gs.player.person.possessions
        gs._lit_beacons = None
        gs._check_beacons()  # seed
        possessions.flags["beacon_kiln_lit"] = True  # Kiln is unlock_silent
        gs._check_beacons()
        self.assertEqual(possessions.message_log, [])


class TestSpaceScreenMissionIntegration(unittest.TestCase):
    """The default story's "first_flight" tutorial mission - real
    story.json ("starting_mission") + missions.json config, auto-started
    on first ship purchase and advanced by the generic gameplay-event
    flags SpaceScreen/PlayerController set (used_ships_target_mode/
    used_turn/used_thrust/braked_below_threshold/used_autopilot_on_ship/
    landed_on_landing_site/completed_jump) alongside "hailed_pilot:<name>"
    (set by _start_hail) and "accepted_kade_help" (set by Kade Marsh's own
    hail_dialogue_tree once the player agrees to be walked through it) -
    see docs/BACKLOG.md's tutorial mission item and game/world/mission.py."""

    def _boarded_screen(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        spaceport = game_screen.get_interior_screen(game_screen.station, "default")
        spaceport._apply_dialogue_action("buy_ship:shuttle")  # arms the mission (_on_ship_purchased)
        game_screen.board_ship()  # launching back into space is what actually starts it
        return game_screen

    def test_buying_the_first_ship_arms_but_does_not_yet_start_the_mission(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        spaceport = game_screen.get_interior_screen(game_screen.station, "default")
        spaceport._apply_dialogue_action("buy_ship:shuttle")
        possessions = game_screen.player.person.possessions
        self.assertNotIn("first_flight", possessions.missions)
        self.assertTrue(possessions.flags.get("starting_mission_armed"))
        game_screen.board_ship()
        self.assertEqual(possessions.missions.get("first_flight"), 0)
        self.assertFalse(possessions.flags.get("starting_mission_armed"))

    def test_buying_the_first_ship_auto_starts_the_configured_mission(self):
        game_screen = self._boarded_screen()
        self.assertEqual(game_screen.player.person.possessions.missions.get("first_flight"), 0)

    def test_kade_does_not_escort_until_the_player_accepts_and_he_pulls_alongside(self):
        """kade_escorting is no longer an on_start_flag - it's set by the
        "Sounds good" option after Kade says he'll pull alongside, so he
        only starts orbiting once the conversation about it is done."""
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        self.assertFalse(possessions.flags.get("kade_escorting"))
        game_screen.update_physics()
        kade = next(s for state in game_screen.systems.values() for s in state.ai_ships if s.person.name == "Kade Marsh")
        self.assertFalse(kade.escorting)

    def test_buying_a_second_ship_does_not_restart_the_mission(self):
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        possessions.flags["used_ships_target_mode"] = True
        game_screen.update_physics()  # advances to stage 1
        self.assertEqual(possessions.missions["first_flight"], 1)

        spaceport = game_screen.get_interior_screen(game_screen.station, "default")
        spaceport._apply_dialogue_action("buy_ship:patrol")
        self.assertEqual(possessions.missions["first_flight"], 1, "a second purchase must not reset progress")

    def test_cycling_to_ships_mode_sets_the_flag(self):
        game_screen = self._boarded_screen()
        game_screen._cycle_target_mode()
        while TARGET_MODES[game_screen.target_mode_index] != "SHIPS":
            game_screen._cycle_target_mode()
        self.assertTrue(game_screen.player.person.possessions.flags.get("used_ships_target_mode"))

    def test_turning_both_ways_advances_past_the_turning_stage(self):
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        possessions.missions["first_flight"] = 3  # the turning stage (mission-log stage removed)

        keys = {k: False for k in (pygame_mock.K_LEFT, pygame_mock.K_a, pygame_mock.K_RIGHT, pygame_mock.K_d, pygame_mock.K_UP, pygame_mock.K_w, pygame_mock.K_DOWN, pygame_mock.K_s)}
        keys[pygame_mock.K_a] = True  # left only
        game_screen.player.handle_input(keys)
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 3, "one direction isn't enough")
        keys[pygame_mock.K_a], keys[pygame_mock.K_d] = False, True  # now right
        game_screen.player.handle_input(keys)
        game_screen.update_physics()
        self.assertTrue(possessions.flags.get("turned_both_ways"))
        self.assertEqual(possessions.missions["first_flight"], 4)

    def test_thrusting_advances_past_the_flying_stage(self):
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        possessions.missions["first_flight"] = 4  # skip straight to the thrust stage

        game_screen.player.thrust = 0.2
        game_screen.update_physics()
        self.assertTrue(possessions.flags.get("used_thrust"))
        self.assertEqual(possessions.missions["first_flight"], 5)

    def test_engaging_autopilot_on_a_ship_sets_the_flag(self):
        game_screen = self._boarded_screen()
        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        game_screen.current_target = 0  # any AI ship in the default system
        target = game_screen._get_target_object()
        self.assertIsInstance(target, Character)

        # F engages autopilot (SPACE fires the equipped weapon instead - see
        # SpaceScreen.handle_input's K_f branch).
        game_screen.handle_input([SimpleNamespace(type=pygame_mock.KEYDOWN, key=pygame_mock.K_f)])
        self.assertTrue(game_screen.player.person.possessions.flags.get("used_autopilot_on_ship"))

    def test_landing_sets_the_flag(self):
        game_screen = self._boarded_screen()
        game_screen._mark_landed()
        self.assertTrue(game_screen.player.person.possessions.flags.get("landed_on_landing_site"))

    def test_autopilot_to_the_station_always_finishes_by_landing(self):
        """Regression (item G "autopilot landing seems to vary"): whether
        SeekMode reaches has_arrived() at the top of a frame (update()'s
        pre-check) or inside update_physics() (it then disengages itself),
        update() must return "land" - not leave the ship parked-but-not-
        landed for the player to press L."""
        for offset in ((300, 0), (140, 140), (0, 250), (-200, -80)):
            game_screen = self._boarded_screen()
            st = game_screen.station
            game_screen.player.ship.x, game_screen.player.ship.y = st.x + offset[0], st.y + offset[1]
            game_screen.player.ship.velocity_x = game_screen.player.ship.max_velocity  # arriving at full speed
            game_screen.player.engage_seek(st)
            for _ in range(2000):
                if game_screen.update() == "land":
                    break
            self.assertEqual(game_screen.landing_target, "station", f"offset {offset} never landed")
            self.assertFalse(game_screen.player.autopilot_active)

    def test_braking_below_threshold_sets_the_flag_and_advances_the_stage(self):
        """S/Down (point_to_reverse_velocity - see PlayerController.handle_input)
        sets "used_brake"; combined with "used_thrust" and a low enough
        speed, update_physics() sets "braked_below_threshold" - the flag
        the tutorial's braking stage completes on."""
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        possessions.missions["first_flight"] = 5  # skip straight to the braking stage
        possessions.flags["used_thrust"] = True
        game_screen.player.velocity_x, game_screen.player.velocity_y = 0, 0  # already slow

        keys = {k: False for k in (pygame_mock.K_LEFT, pygame_mock.K_a, pygame_mock.K_RIGHT, pygame_mock.K_d, pygame_mock.K_UP, pygame_mock.K_w, pygame_mock.K_DOWN, pygame_mock.K_s)}
        keys[pygame_mock.K_s] = True
        game_screen.player.handle_input(keys)
        self.assertTrue(possessions.flags.get("used_brake"))

        game_screen.update_physics()
        self.assertTrue(possessions.flags.get("braked_below_threshold"))
        self.assertEqual(possessions.missions["first_flight"], 6)

    def test_accepting_kades_help_advances_the_stage_and_the_close_starts_the_escort(self):
        """"Sure, show me the ropes." sets accepted_kade_help (advances past
        the conversation stage). kade_escorting - and so the escort itself -
        only fires once the player closes the follow-up "give me a second to
        pull alongside" line with "Sounds good"."""
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        possessions.missions["first_flight"] = 2  # skip straight to the conversation stage
        kade_char = next(s for state in game_screen.systems.values() for s in state.ai_ships if s.person.name == "Kade Marsh")

        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        for i, (_, obj) in enumerate(game_screen._filtered_targets()):
            if obj is kade_char:
                game_screen.current_target = i
        game_screen._start_hail()
        dialogue = game_screen.active_dialogue

        accept = dialogue.current_options(possessions.flags)[0]
        self.assertEqual(accept["label"], "Sure, show me the ropes.")
        for action in option_actions(accept):
            apply_shared_actions(action, possessions, game_screen.missions_config)
        dialogue.advance(accept)  # -> "accepted" node
        self.assertTrue(possessions.flags.get("accepted_kade_help"))
        self.assertFalse(possessions.flags.get("kade_escorting"))  # not yet
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 3)
        self.assertFalse(kade_char.escorting)

        done = dialogue.current_options(possessions.flags)[0]
        self.assertEqual(done["label"], "Sounds good.")
        for action in option_actions(done):
            apply_shared_actions(action, possessions, game_screen.missions_config)
        dialogue.advance(done)
        self.assertTrue(possessions.flags.get("kade_escorting"))
        game_screen.update_physics()
        self.assertTrue(kade_char.escorting)
        self.assertIsInstance(kade_char.routine, OrbitPlayerRoutine)

    def test_accepting_help_on_the_first_hail_still_completes_the_stage(self):
        """A hail freezes mission progress, so hailing Kade (stage 1's
        flag) and accepting his offer (stage 2's flag) both land before
        check_mission_progress next runs. Advancing into stage 2 must not
        wipe the accepted-help flag the player already earned - otherwise
        the mission strands on the conversation step forever."""
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        self.assertEqual(possessions.missions["first_flight"], 0)

        possessions.flags["used_ships_target_mode"] = True
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 1)

        # One frozen hail sets both flags with no update_physics() between.
        possessions.flags["hailed_pilot:Kade Marsh"] = True
        possessions.flags["accepted_kade_help"] = True
        possessions.flags["kade_escorting"] = True

        game_screen.update_physics()  # 1 -> 2
        self.assertTrue(possessions.flags.get("accepted_kade_help"),
                        "entering stage 2 must not clear the flag the player already set")
        game_screen.update_physics()  # 2 -> 3
        self.assertEqual(possessions.missions["first_flight"], 3)

    def test_declining_kades_help_abandons_the_mission_and_stops_escorting(self):
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        possessions.missions["first_flight"] = 2
        kade_char = next(s for state in game_screen.systems.values() for s in state.ai_ships if s.person.name == "Kade Marsh")

        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        for i, (_, obj) in enumerate(game_screen._filtered_targets()):
            if obj is kade_char:
                game_screen.current_target = i
        game_screen._start_hail()
        dialogue = game_screen.active_dialogue
        options = dialogue.current_options(possessions.flags)
        decline = next(o for o in options if o["label"] == "No thanks, I've got it.")
        for action in option_actions(decline):
            apply_shared_actions(action, possessions, game_screen.missions_config)
        dialogue.advance(decline)

        self.assertNotIn("first_flight", possessions.missions)
        self.assertNotIn("first_flight", possessions.completed_missions)
        self.assertTrue(possessions.flags.get("kade_tutorial_done"))
        game_screen.update_physics()
        self.assertFalse(kade_char.escorting)

        # Hailing him again after declining shouldn't re-offer the tutorial.
        game_screen.active_dialogue = None
        game_screen._start_hail()
        self.assertEqual(game_screen.active_dialogue.current_node, "casual")

    def test_completing_a_jump_sets_the_flag_and_full_playthrough_completes_the_mission(self):
        """Runs every stage in order against the real config, ending with
        the mission moved into completed_missions and Kade no longer
        escorting - the same end-to-end path a player actually taking the
        tutorial would follow."""
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        kade_char = next(s for state in game_screen.systems.values() for s in state.ai_ships if s.person.name == "Kade Marsh")

        possessions.flags["used_ships_target_mode"] = True
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 1)

        possessions.flags["hailed_pilot:Kade Marsh"] = True
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 2)

        possessions.flags["accepted_kade_help"] = True
        possessions.flags["kade_escorting"] = True  # (set on the "Sounds good" close in-game)
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 3)
        self.assertTrue(kade_char.escorting)

        possessions.flags["turned_both_ways"] = True
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 4)

        game_screen.player.thrust = 0.2
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 5)

        possessions.flags["used_brake"] = True
        game_screen.player.velocity_x, game_screen.player.velocity_y = 0, 0
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 6)

        game_screen.jump_state = {"phase": "travel", "heading": 0, "timer": 0, "destination": game_screen.system_id}
        game_screen._complete_jump()
        self.assertTrue(possessions.flags.get("completed_jump"))
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 7)

        game_screen._mark_landed()
        game_screen.update_physics()
        self.assertNotIn("first_flight", possessions.missions)
        self.assertEqual(possessions.completed_missions, ["first_flight"])
        self.assertTrue(possessions.flags.get("kade_tutorial_done"))
        self.assertFalse(possessions.flags.get("kade_escorting"))
        self.assertFalse(kade_char.escorting, "Kade must stop escorting once the tutorial finishes")

    def test_drifted_from_center_matches_the_self_jump_threshold(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        cx, cy = GAME_WIDTH / 2, GAME_HEIGHT / 2
        game_screen.player.x, game_screen.player.y = cx, cy
        self.assertFalse(game_screen._drifted_from_center())
        game_screen.player.x = cx + 5000
        self.assertTrue(game_screen._drifted_from_center())


if __name__ == "__main__":
    unittest.main()
