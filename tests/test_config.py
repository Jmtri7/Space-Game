"""Config — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


class TestStoryTuningConfig(unittest.TestCase):
    """Per-story tuning knobs read from story.json (jump / brake / camera /
    walking) - defaults live in code, story.json overrides them."""

    def test_space_screen_reads_jump_and_brake_tuning(self):
        s = SpaceScreen(pilot_name="T", story="default")
        self.assertEqual(s.jump_speed, 40)
        self.assertEqual(s.jump_travel_frames, 150)
        self.assertEqual(s.jump_arrival_distance, 1400)
        self.assertEqual(s.jump_self_min_distance, 3200)
        self.assertEqual(s.brake_slow_threshold, 0.3)

    def test_space_screen_applies_camera_zoom_to_the_shared_camera(self):
        utils.set_camera_zoom(99.0)
        SpaceScreen(pilot_name="T", story="default")
        self.assertEqual(utils.get_scale(), utils._camera.get_scale())
        self.assertEqual(utils._camera.zoom, 3.0)  # story.json's camera_zoom

    def test_location_screen_walking_speed_from_story(self):
        screen = LocationScreen(config_data={"label": "X"}, world_width=800, world_height=600, story="default")
        self.assertEqual(screen.speed, 2.0)  # story.json's walking_speed

    def test_space_and_interior_camera_zoom_ranges_from_story(self):
        s = SpaceScreen(pilot_name="T", story="default")
        self.assertEqual((s.camera_zoom_min, s.camera_zoom, s.camera_zoom_max), (1.75, 3.0, 9.0))
        loc = LocationScreen(config_data={"label": "X"}, world_width=800, world_height=600, story="default")
        self.assertEqual((loc.camera_zoom_min, loc.camera_zoom, loc.camera_zoom_max), (2.25, 3.0, 8.0))


class TestVideoResolution(unittest.TestCase):
    """main.py's Video Settings model: the native default, aspect grouping,
    which aspects/resolutions a given desktop offers, and honouring /
    rejecting a saved choice. These read module-level NATIVE_* constants, so
    each desktop-size case recomputes them via _reload()."""

    CANDIDATES = [
        (1024, 768), (1280, 960), (1600, 1200),                # 4:3
        (1280, 1024),                                          # 5:4
        (2160, 1440),                                          # 3:2
        (1280, 800), (1440, 900), (1680, 1050), (1920, 1200),  # 16:10
        (1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160),  # 16:9
        (2560, 1080), (3440, 1440),                            # 21:9
    ]

    def _reload(self, w, h):
        """Point main at a `w`x`h` desktop and recompute its NATIVE_* module
        constants (normally set once at import)."""
        import main
        self._stack.enter_context(patch.object(main, "VIDEO_RESOLUTIONS", self.CANDIDATES))
        self._stack.enter_context(patch.object(main, "DESKTOP_WIDTH", w))
        self._stack.enter_context(patch.object(main, "DESKTOP_HEIGHT", h))
        self._stack.enter_context(patch.object(main, "NATIVE_RESOLUTION", (w, h)))
        self._stack.enter_context(patch.object(main, "NATIVE_ASPECT", main.aspect_label((w, h))))
        return main

    def setUp(self):
        import contextlib
        self._stack = contextlib.ExitStack()

    def tearDown(self):
        self._stack.close()

    def test_default_is_the_native_desktop_resolution(self):
        m = self._reload(2560, 1440)
        self.assertEqual(m.default_resolution(), (2560, 1440))

    def test_aspect_label_buckets_both_ultrawide_sizes_together(self):
        import main
        self.assertEqual(main.aspect_label((2560, 1080)), main.aspect_label((3440, 1440)))
        self.assertEqual(main.aspect_label((1920, 1080)), "16:9")
        self.assertEqual(main.aspect_label((1920, 1200)), "16:10")

    def test_available_aspects_lists_native_first(self):
        m = self._reload(2560, 1440)
        aspects = m.available_aspects()
        self.assertEqual(aspects[0], "16:9")
        self.assertIn("16:10", aspects)
        self.assertIn("4:3", aspects)

    def test_resolutions_for_aspect_are_fitting_and_grouped(self):
        m = self._reload(2560, 1440)
        self.assertEqual(m.resolutions_for_aspect("16:9"),
                         [(1280, 720), (1600, 900), (1920, 1080), (2560, 1440)])
        self.assertEqual(m.resolutions_for_aspect("16:10"),
                         [(1280, 800), (1440, 900), (1680, 1050), (1920, 1200)])

    def test_widescreen_desktop_defaults_and_groups_to_ultrawide(self):
        m = self._reload(3440, 1440)
        self.assertEqual(m.default_resolution(), (3440, 1440))
        self.assertEqual(m.available_aspects()[0], "21:9")
        self.assertEqual(m.resolutions_for_aspect("21:9"), [(2560, 1080), (3440, 1440)])

    def test_native_resolution_is_offered_even_if_not_a_candidate(self):
        m = self._reload(3000, 2000)  # 3:2, not in CANDIDATES
        self.assertIn((3000, 2000), m.resolutions_for_aspect(m.NATIVE_ASPECT))

    def test_load_resolution_honours_a_valid_saved_choice(self):
        m = self._reload(2560, 1440)
        with patch.object(m, "load_settings", return_value={"resolution": [1920, 1200]}):
            self.assertEqual(m.load_resolution(), (1920, 1200))  # off-aspect but valid

    def test_load_resolution_rejects_a_now_oversized_saved_choice(self):
        m = self._reload(2560, 1440)
        with patch.object(m, "load_settings", return_value={"resolution": [3840, 2160]}):
            self.assertEqual(m.load_resolution(), m.default_resolution())

    def test_load_resolution_default_when_nothing_saved(self):
        m = self._reload(2560, 1440)
        with patch.object(m, "load_settings", return_value={}):
            self.assertEqual(m.load_resolution(), m.default_resolution())


class TestConfigModuleResolver(unittest.TestCase):
    """game/config_source.py - the story-first, then module-by-module search
    path (story_path) and the deep-merge for flat catalogues (story_catalogue)."""

    def test_story_with_no_modules_is_unchanged(self):
        from game import config_source
        self.assertIn("audio-core", config_source.story_modules("default"))
        # a per-name file the story owns resolves to the story dir
        p = config_source.story_path("the_long_silence", "graphics", "graphics.json")
        self.assertIn(os.path.join("stories", "the_long_silence"), p)

    def test_story_path_falls_through_to_a_module(self):
        from game import config_source
        # rig_walk was moved into figures-human; the_long_silence keeps no copy
        p = config_source.story_path("the_long_silence", "graphics", "body", "rig_walk.json")
        self.assertTrue(os.path.exists(p))
        self.assertIn(os.path.join("modules", "figures-human"), p)

    def test_story_file_shadows_the_module(self):
        from game import config_source
        # the_long_silence deliberately keeps its own tuned human_femme body
        p = config_source.story_path("the_long_silence", "graphics", "body", "human_femme.json")
        self.assertIn(os.path.join("stories", "the_long_silence"), p)

    def test_catalogue_merge_layers_story_over_module(self):
        from game import config_source
        merged = config_source.story_catalogue("the_long_silence", "audio.json")
        # audio-core provides the sounds; the story adds none, so they're all present
        self.assertIn("ping", merged.get("sounds", {}))
        self.assertIn("laser", merged.get("sounds", {}))

    def test_module_versions_recorded(self):
        from game import config_source
        mv = config_source.module_versions("the_long_silence")
        self.assertLessEqual({"figures-human", "audio-core"}, set(mv))
        self.assertRegex(mv["figures-human"], r"^\d")

    def test_story_meta_merges_module_tuning_defaults(self):
        from game import config_source
        meta = config_source.story_meta("the_long_silence")
        # jump block + zoom bounds now come from the story-defaults module
        self.assertEqual(meta["jump"]["travel_frames"], 150)
        self.assertEqual(meta["camera_zoom_max"], 9.0)
        # graphics_pipeline_test keeps its own zoomed-in overrides
        gpt = config_source.story_meta("graphics_pipeline_test")
        self.assertEqual(gpt["camera_zoom"], 2.0)
        self.assertEqual(gpt["jump"]["speed"], 40)  # still inherited


if __name__ == "__main__":
    unittest.main()
