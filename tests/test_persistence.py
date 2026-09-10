"""Persistence — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


class TestBuildSaveGameState(unittest.TestCase):
    """Regression test: a save made while docked at a station/moon (in
    ANY system other than the story's starting one) used to always reload
    into the starting system - game_state["story"]/["system_id"] were set
    on an empty dict, then immediately discarded when the station/moon
    branch reassigned game_state from get_state(). build_save_game_state()
    centralizes this so story/system_id always land on the dict actually
    passed to create_save_file()."""

    def test_station_save_keeps_story_and_system_id(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        station_interior = game_screen.get_interior_screen(game_screen.station, "default")
        game_state, system_config_snapshot = build_save_game_state(game_screen, "station", station_interior, None)
        self.assertEqual(game_state["location"], "station")
        self.assertEqual(game_state["story"], "default")
        self.assertEqual(game_state["system_id"], "keplers_reach")
        self.assertEqual(system_config_snapshot, {})

    def test_moon_save_keeps_story_and_system_id(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        moon_interior = game_screen.get_interior_screen(game_screen.moon, "wilderness")
        game_state, system_config_snapshot = build_save_game_state(game_screen, "moon", None, moon_interior)
        self.assertEqual(game_state["location"], "moon")
        self.assertEqual(game_state["moon_location"], "wilderness")
        self.assertEqual(game_state["story"], "default")
        self.assertEqual(game_state["system_id"], "keplers_reach")

    def test_moon_save_uses_interior_key_not_label_text(self):
        """Regression test: moon_location used to be guessed from whether
        the interior's own label text contained the word "city" - Kepler's
        Reach's city interior is labeled "Rust Moon Settlement", which
        doesn't, so saving there was misdetected as "wilderness" and
        loading put the player in the wrong moon location entirely."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        city_interior = game_screen.get_interior_screen(game_screen.moon, "city")
        self.assertNotIn("city", city_interior.ui_label.lower())  # the actual label has no "city" in it
        game_state, _ = build_save_game_state(game_screen, "moon", None, city_interior)
        self.assertEqual(game_state["moon_location"], "city")

    def test_space_save_keeps_story_system_id_and_system_config(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        game_state, system_config_snapshot = build_save_game_state(game_screen, "game", None, None)
        self.assertEqual(game_state["location"], "space")
        self.assertEqual(game_state["system_id"], "keplers_reach")
        self.assertIs(system_config_snapshot, game_screen.system_config)


class TestStoryVersioning(unittest.TestCase):
    """Test story_version round-tripping through a save and the load-time
    mismatch warning (see docs/SAVE_SYSTEM.md's "Save Compatibility
    Discipline") - never blocks loading, just surfaces the risk
    that a save's story config or this game's state-handling code has
    changed since the save was made."""

    # Read the live version from story.json rather than pinning a literal, so
    # a routine version bump (see docs/SAVE_SYSTEM.md's story-versioning rules) doesn't
    # need a test edit - these assert the plumbing, not the number.
    CURRENT_VERSION = utils.get_story("default")["version"]

    def test_space_screen_reads_story_version_from_story_json(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        self.assertEqual(game_screen.story_version, self.CURRENT_VERSION)

    def test_build_save_game_state_records_story_version(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_state, _ = build_save_game_state(game_screen, "game", None, None)
        self.assertEqual(game_state["story_version"], self.CURRENT_VERSION)

    def test_matching_version_prints_no_warning(self):
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", self.CURRENT_VERSION)
        self.assertEqual(captured.getvalue(), "")

    def test_mismatched_version_warns(self):
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", "0.9.0")
        self.assertIn("0.9.0", captured.getvalue())
        self.assertIn(self.CURRENT_VERSION, captured.getvalue())

    def test_missing_version_warns(self):
        """A save made before story versioning existed has no
        story_version key at all - still worth flagging, not silently
        treated as compatible."""
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", None)
        self.assertNotEqual(captured.getvalue(), "")


class TestCreateSaveFileNameCollision(unittest.TestCase):
    """Regression test: the pre-populated save name only has minute
    resolution, so two new saves made within the same minute used to collide
    on the same filename and the second silently clobbered the first.
    create_save_file() should now append " (2)", " (3)", etc. instead."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch.object(utils, "SAVE_DIR", self.test_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_second_save_with_same_name_gets_suffixed(self):
        path1 = utils.create_save_file("Pilot", "2026-08-25 1430", {}, {})
        path2 = utils.create_save_file("Pilot", "2026-08-25 1430", {}, {})

        self.assertNotEqual(path1, path2)
        self.assertTrue(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))
        self.assertIn("(2)", path2)

    def test_third_save_with_same_name_increments_again(self):
        utils.create_save_file("Pilot", "clash", {}, {})
        utils.create_save_file("Pilot", "clash", {}, {})
        path3 = utils.create_save_file("Pilot", "clash", {}, {})

        self.assertIn("(3)", path3)

    def test_unique_name_is_not_suffixed(self):
        path = utils.create_save_file("Pilot", "unique_name", {}, {})
        self.assertTrue(path.endswith("save_unique_name.json"))

    def test_overwrite_flow_is_unaffected_since_old_file_is_deleted_first(self):
        """Mirrors main.py's overwrite path: delete the old file, then
        create_save_file() with the same name reuses it rather than
        appending a suffix."""
        path1 = utils.create_save_file("Pilot", "existing", {}, {})
        os.remove(path1)
        path2 = utils.create_save_file("Pilot", "existing", {}, {})
        self.assertEqual(path1, path2)


class TestSaveBrowserNameEntry(unittest.TestCase):
    """Typing a new save name - the one place the keyboard is still used in a
    menu (input_mode only, and only to edit the text field)."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_first_keystroke_replaces_the_prefilled_default_then_appends(self):
        b = SaveBrowser("save", pilot_name="Test")
        b._enter_input_mode()  # e.g. clicking "New Save"
        self.assertTrue(b.save_name)  # pre-filled
        b.handle_input([self._event(pygame_mock.TEXTINPUT, text="x")])
        self.assertEqual(b.save_name, "x")
        b.handle_input([self._event(pygame_mock.TEXTINPUT, text="y")])
        self.assertEqual(b.save_name, "xy")

    def test_typing_does_nothing_while_browsing_the_list(self):
        b = SaveBrowser("save", pilot_name="Test")
        b.list.items = ["save_old.json"]
        b.input_mode = False
        before = b.save_name
        b.handle_input([self._event(pygame_mock.TEXTINPUT, text="z")])
        self.assertEqual(b.save_name, before)


class TestSaveBrowserContract(unittest.TestCase):
    """The (action, payload) tuples main.py's load/pause branches switch on -
    driven by the button `_press()` now that the menu is mouse-only."""

    def test_load_mode_actions(self):
        b = SaveBrowser("load")
        b.list.items = ["save_a.json", "save_b.json"]
        b.list.selected = 0
        self.assertEqual(b._press("act"), ("load", "save_a.json"))
        self.assertEqual(b._press("delete"), ("delete", "save_a.json"))
        self.assertEqual(b._press("cancel"), ("cancel", None))
        self.assertNotIn("new", [btn[0] for btn in b.buttons()])

    def test_save_mode_overwrite_vs_new(self):
        b = SaveBrowser("save", pilot_name="Kai")
        b.list.items = ["save_old.json"]
        b.input_mode = False
        b.list.selected = 0
        self.assertEqual(b._press("act"), ("save", "save_old.json"))
        b._press("new")
        self.assertTrue(b.input_mode)
        self.assertEqual(b._press("save"), ("save", b.save_name))

    def test_display_name_strips_prefix_and_suffix(self):
        from game.utils import save_display_name
        self.assertEqual(save_display_name("save_Kai - 2026-01-02 0900.json"), "Kai - 2026-01-02 0900")
        self.assertEqual(save_display_name("already clean"), "already clean")


if __name__ == "__main__":
    unittest.main()
