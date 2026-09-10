"""Misc — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


class TestListFilesByPattern(unittest.TestCase):
    """Test _list_files_by_pattern helper function"""

    def setUp(self):
        """Create temporary directory for testing"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.test_dir)

    def test_lists_matching_files(self):
        """Should list files matching prefix and suffix"""
        open(os.path.join(self.test_dir, "save_test1.json"), "w").close()
        open(os.path.join(self.test_dir, "save_test2.json"), "w").close()

        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(len(files), 2)
        self.assertIn("save_test1.json", files)
        self.assertIn("save_test2.json", files)

    def test_filters_prefix(self):
        """Should only match files with correct prefix"""
        open(os.path.join(self.test_dir, "save_test.json"), "w").close()
        open(os.path.join(self.test_dir, "other_test.json"), "w").close()

        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "save_test.json")

    def test_filters_suffix(self):
        """Should only match files with correct suffix"""
        open(os.path.join(self.test_dir, "save_test.json"), "w").close()
        open(os.path.join(self.test_dir, "save_test.txt"), "w").close()

        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "save_test.json")

    def test_returns_sorted_reverse(self):
        """Should return files sorted in reverse (newest first)"""
        # Create files
        for i in range(1, 4):
            open(os.path.join(self.test_dir, f"save_test{i}.json"), "w").close()

        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        # Should be reverse sorted
        self.assertEqual(files[0], "save_test3.json")
        self.assertEqual(files[-1], "save_test1.json")

    def test_creates_dir_if_missing(self):
        """Should create directory if it doesn't exist"""
        nonexistent = os.path.join(self.test_dir, "subdir")
        files = utils._list_files_by_pattern(nonexistent, "save_", ".json")
        self.assertTrue(os.path.exists(nonexistent))
        self.assertEqual(files, [])

    def test_empty_dir_returns_empty_list(self):
        """Should return empty list for directory with no matching files"""
        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(files, [])


class TestCenterTextX(unittest.TestCase):
    """Test _center_text_x helper function"""

    def test_returns_integer(self):
        """Should return an integer coordinate"""
        text = MagicMock()
        text.get_width.return_value = 100

        result = utils._center_text_x(None, text)
        self.assertIsInstance(result, int)

    def test_centers_horizontally(self):
        """Should center text within the UI's 800-unit-wide space (not
        GAME_WIDTH - _center_text_x uses get_ui_scale(), a separate scale
        for menus/dialogs, independent of the space camera's zoom)"""
        text = MagicMock()
        text.get_width.return_value = 200

        result = utils._center_text_x(None, text)
        ui_scale = utils.get_ui_scale()
        expected = int(800 * ui_scale * 0.5 - 200 // 2)
        self.assertEqual(result, expected)

    def test_respects_offset(self):
        """Should shift the centered position by offset_x"""
        text = MagicMock()
        text.get_width.return_value = 200

        result = utils._center_text_x(None, text, offset_x=50)
        ui_scale = utils.get_ui_scale()
        expected = int(50 + 800 * ui_scale * 0.5 - 200 // 2)
        self.assertEqual(result, expected)


class TestPressedAny(unittest.TestCase):
    """main._pressed_any drives the M/P/N + ESC close affordance for the
    Star Map / Possessions / Mission Log overlays in main.py's state machine."""

    def _keydown(self, key):
        return SimpleNamespace(type=pygame_mock.KEYDOWN, key=key)

    def test_matches_a_listed_key(self):
        events = [self._keydown("a"), self._keydown("m")]
        self.assertTrue(_pressed_any(events, "m", "esc"))

    def test_no_match_when_key_absent(self):
        events = [self._keydown("a"), self._keydown("j")]
        self.assertFalse(_pressed_any(events, "m", "esc"))

    def test_ignores_keyup_and_other_event_types(self):
        events = [SimpleNamespace(type=pygame_mock.KEYUP, key="m"),
                  SimpleNamespace(type=pygame_mock.MOUSEBUTTONDOWN, button=1, pos=(0, 0))]
        self.assertFalse(_pressed_any(events, "m"))

    def test_empty_events(self):
        self.assertFalse(_pressed_any([], "m"))


class TestAdvanceAccumulator(unittest.TestCase):
    """utils.advance_accumulator() - the fixed-timestep core the main loop
    drains each frame (see docs/BACKLOG.md "Fixed-timestep accumulator")."""

    STEP = 1.0 / 60.0

    def test_one_step_per_frame_at_60fps(self):
        """A frame worth of real time (~1/60 s) yields exactly one step -
        the byte-identical-to-the-old-loop case on a machine holding 60 FPS."""
        acc, n = utils.advance_accumulator(0.0, self.STEP)
        self.assertEqual(n, 1)
        self.assertAlmostEqual(acc, 0.0, places=9)

    def test_sub_step_frames_average_out_to_one_step_per_step_of_real_time(self):
        """Frames a bit under 1/60 s each: the steady-state snap runs one
        step per frame while it can (10 ms is 0.6 steps, inside the snap
        band), letting the accumulator go slightly negative, then a 0-step
        frame when it's drained - so N frames of ~1/60 s run ~N steps total
        and no single frame ever jumps two steps."""
        acc, total, twos = 0.0, 0, 0
        for _ in range(600):
            acc, n = utils.advance_accumulator(acc, 0.010)
            total += n
            twos += (n >= 2)
        self.assertEqual(twos, 0)                 # never a 2-step frame
        self.assertAlmostEqual(total, 600 * 0.010 / self.STEP, delta=2)  # ~360 steps

    def test_slight_refresh_mismatch_never_produces_a_two_step_frame(self):
        """A 59.94 Hz panel with no vsync feeds ~16.68 ms frames while the
        sim wants 16.667 ms. floor() would emit a 0-then-2 hitch every
        ~20 s; the snap keeps it at exactly one step per frame."""
        acc = 0.0
        for _ in range(6000):  # ~100 s of frames
            acc, n = utils.advance_accumulator(acc, 1.0 / 59.94)
            self.assertEqual(n, 1)

    def test_isolated_missed_vblank_stays_one_step(self):
        """A single ~2x frame (a dropped vblank on an otherwise smooth 60 Hz
        machine) runs ONE step, not two - the world must not double-jump on
        top of the frame the display already held twice. The next normal
        frame stays at one step too (no delayed catch-up lurch)."""
        acc, n = utils.advance_accumulator(0.0, 0.033)
        self.assertEqual(n, 1)
        acc, n = utils.advance_accumulator(acc, self.STEP)
        self.assertEqual(n, 1)

    def test_slow_frame_runs_multiple_steps(self):
        """A 50 ms frame (3x the budget) runs 3 catch-up steps."""
        acc, n = utils.advance_accumulator(0.0, 0.050)
        self.assertEqual(n, 3)
        self.assertAlmostEqual(acc, 0.050 - 3 * self.STEP, places=9)

    def test_max_steps_clamp_drops_the_remainder(self):
        """A frame far beyond MAX_STEPS_PER_FRAME * STEP is capped at
        max_steps steps and the leftover is discarded (no spiral of death)."""
        acc, n = utils.advance_accumulator(0.0, 10.0, max_steps=5)
        self.assertEqual(n, 5)
        self.assertEqual(acc, 0.0)

    def test_real_dt_is_clamped_before_accumulating(self):
        """A multi-second hitch (debugger pause) is clamped to
        max_frame_time first, so it can't dump seconds of catch-up in -
        with a generous max_steps it still only runs ~max_frame_time/STEP."""
        acc, n = utils.advance_accumulator(0.0, 30.0, max_steps=1000, max_frame_time=0.25)
        self.assertEqual(n, 15)  # 0.25 / (1/60) == 15
        self.assertAlmostEqual(acc, 0.25 - 15 * self.STEP, places=9)

    def test_negative_or_zero_dt_is_a_noop(self):
        acc, n = utils.advance_accumulator(0.005, 0.0)
        self.assertEqual(n, 0)
        self.assertAlmostEqual(acc, 0.005, places=9)


class TestStepWorld(unittest.TestCase):
    """main.step_world() - the single simulation entry point the fixed-
    timestep accumulator drains. One sim step must move the world exactly
    as one old loop iteration did, and frozen screens must not move it."""

    def _screen(self):
        return SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")

    def test_game_step_advances_ship_physics(self):
        from main import step_world
        gs = self._screen()
        gs.player.ship.velocity_x = 1.5
        gs.player.ship.velocity_y = -0.5
        x0, y0 = gs.player.x, gs.player.y
        result = step_world("game", gs, None, None)
        self.assertIsNone(result)
        self.assertAlmostEqual(gs.player.x, x0 + 1.5, places=6)
        self.assertAlmostEqual(gs.player.y, y0 - 0.5, places=6)

    def test_n_steps_move_n_times_as_far(self):
        from main import step_world
        gs = self._screen()
        gs.player.ship.velocity_x = 2.0
        x0 = gs.player.x
        for _ in range(5):
            step_world("game", gs, None, None)
        self.assertAlmostEqual(gs.player.x, x0 + 10.0, places=6)

    def test_frozen_screens_do_not_advance_the_world(self):
        from main import step_world
        gs = self._screen()
        gs.player.ship.velocity_x = 3.0
        x0 = gs.player.x
        for frozen in ("pause", "star_map", "possessions", "shop", "menu"):
            step_world(frozen, gs, None, None)
        self.assertEqual(gs.player.x, x0)

    def test_open_hail_freezes_the_game_screen(self):
        from main import step_world
        gs = self._screen()
        gs.player.ship.velocity_x = 3.0
        gs.active_dialogue = object()  # a hail is open
        x0 = gs.player.x
        step_world("game", gs, None, None)
        self.assertEqual(gs.player.x, x0)

    def test_autopilot_arrival_propagates_land_out_of_the_step(self):
        """When SpaceScreen.update() returns "land" (autopilot reached a
        landing_site) from inside a sim step, step_world() must surface it so
        the accumulator loop can stop and open the interior - the old loop
        dropped this return value and the auto-dock never happened."""
        from main import step_world, begin_landing
        gs = self._screen()
        st = gs.station
        gs.player.ship.x, gs.player.ship.y = st.x - 300, st.y
        gs.player.engage_seek(st)
        result = None
        for _ in range(4000):
            result = step_world("game", gs, None, None)
            if result:
                break
        self.assertEqual(result, "land")
        next_screen, si, _ls = begin_landing(gs)
        self.assertEqual(next_screen, "station")
        self.assertIsNotNone(si)
        self.assertEqual((gs.player.ship.velocity_x, gs.player.ship.velocity_y), (0, 0))


if __name__ == "__main__":
    unittest.main()
