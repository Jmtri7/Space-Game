"""Graphics Audio — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


class TestPersonOutfitRendering(unittest.TestCase):
    """Person.draw() with the default story's outfits - the culture/role
    suits plus the accessory-piece keys (shoulder/spike/collar/chest_plate/
    sash/belt/badge/backpack/antenna/visor). pygame is mocked here, so this
    exercises the geometry math (to_screen, _shade, the hypot in the sash
    band) and catches a typo'd color key in graphics.json, not the pixels."""

    KNOWN_OUTFIT_KEYS = {
        "helmet_color", "suit_color", "boot_color", "leg_color", "sleeve_color",
        "shoulder_color", "spike_color", "collar_color", "chest_plate_color",
        "sash_color", "belt_color", "badge_color", "backpack_color",
        "antenna_color", "visor_color",
        "signature",   # opts the outfit into a baked culture/role signature
    }

    def _all_outfit_ids(self):
        return list((utils.load_json("config/stories/default/graphics.json") or {}).get("outfits", {}))

    def test_every_default_story_outfit_draws_without_error(self):
        ids = self._all_outfit_ids()
        self.assertIn("space_suit", ids)
        for outfit_id in ids:
            outfit = utils.get_graphics_asset("default", "outfits", outfit_id)
            Person(570, 400, outfit=outfit).draw(MagicMock())

    def test_no_outfit_uses_an_unrecognized_key(self):
        outfits = (utils.load_json("config/stories/default/graphics.json") or {})["outfits"]
        for outfit_id, outfit in outfits.items():
            unknown = set(outfit) - self.KNOWN_OUTFIT_KEYS
            self.assertEqual(unknown, set(), f"{outfit_id} has unknown key(s): {unknown}")

    def test_every_referenced_signature_is_baked(self):
        from game.world.figure_signatures import SIGNATURE
        outfits = (utils.load_json("config/stories/default/graphics.json") or {})["outfits"]
        for outfit_id, outfit in outfits.items():
            sig = outfit.get("signature")
            if sig is not None:
                self.assertIn(sig, SIGNATURE, f"{outfit_id} references unbaked signature {sig!r}")

    def test_visor_replaces_the_eyes(self):
        def counts(outfit):
            # Person.draw() emits its shapes through game.aa_draw (aa.polygon /
            # aa.circle), which dispatch on constants.AA_MODE.
            with patch("game.world.person.aa") as mock_aa:
                Person(0, 0, outfit=outfit).draw(MagicMock())
                return mock_aa.polygon.call_count, mock_aa.circle.call_count
        polys_visor, circles_visor = counts({"suit_color": [10, 10, 10], "visor_color": [200, 120, 90]})
        polys_plain, circles_plain = counts({"suit_color": [10, 10, 10]})
        self.assertGreater(polys_visor, 0)
        # A plain face draws the whole Grounded face kit - oval eyes (white +
        # pupil), a brow over each, an under-nose shadow and a mouth line, all
        # polygons now (EYES_BARE, 10 parts). The visored face draws the visor
        # plate (2 polys) over that area instead, so it emits 8 fewer polygons;
        # circles (the hands - the head and ears are polygons now) are unchanged.
        self.assertEqual(polys_plain - polys_visor, 8)
        self.assertEqual(circles_plain, circles_visor)


class TestLongSilenceOutfitRendering(unittest.TestCase):
    """Every the_long_silence outfit is a design-JSON pipeline outfit
    ({body, set, palette}); this expands and draws all of them so a broken
    article / set / palette key in the bespoke Authority wardrobe (Phase 6.1)
    or the per-culture stubs is caught. pygame is mocked, so this exercises
    expand() + compose_worn + apply_walk, not the pixels."""

    def _all_outfit_ids(self):
        return list((utils.load_json("config/stories/the_long_silence/graphics.json") or {}).get("outfits", {}))

    def test_every_outfit_draws_without_error(self):
        ids = self._all_outfit_ids()
        self.assertGreater(len(ids), 50)
        for outfit_id in ids:
            outfit = utils.get_graphics_asset("the_long_silence", "outfits", outfit_id)
            Person(570, 400, outfit=outfit).draw(MagicMock())

    def test_bespoke_culture_wardrobes_are_wired(self):
        # Every Act I culture (Halcyon/Kiln/Verdance/Ossuary + carriers) has
        # its ten <pfx>_<role>_<cut> outfits pointed at a bespoke <pfx>_* set
        # backed by real culture-specific articles, not a <pfx>_dress recolour
        # of the borrowed ck_* sets. The Wardens are the exception - their
        # wardrobe is deferred to Act II (still a palette recolour).
        base = "config/stories/the_long_silence/graphics"
        gfx = utils.load_json(f"{base}/../graphics.json") or {}
        for pfx in ("authority", "combine", "drift", "vigil", "carrier"):
            sets_seen = set()
            for role in ("civilian", "official", "flight", "security", "dock"):
                for cut in ("femme", "masc"):
                    entry = gfx["outfits"][f"{pfx}_{role}_{cut}"]
                    self.assertTrue(entry["set"].startswith(f"{pfx}_"),
                                    f"{pfx}_{role}_{cut} -> {entry['set']}")
                    self.assertEqual(entry["body"], f"human_{cut}")
                    sets_seen.add(entry["set"])
            for sid in sets_seen:
                sj = utils.load_json(f"{base}/sets/{sid}.json")
                self.assertTrue(sj and any(a.startswith(f"{pfx}_") for a in sj["articles"]),
                                f"set {sid} has no bespoke {pfx}_ article")


class TestPerfMetrics(unittest.TestCase):
    """game.perf_metrics.PerfMetrics - the rolling frame-timing stats the
    DEBUG overlay reads. Fed once per frame by main.py's loop."""

    def _metrics(self):
        from game.perf_metrics import PerfMetrics
        return PerfMetrics(window=4)

    def test_frame_total_is_the_sum_of_its_phases(self):
        m = self._metrics()
        m.record({"input": 1.0, "sim": 2.0, "render": 5.0, "present": 0.5}, n_steps=1, fps=60.0)
        avg, peak = m._stat(m._frame)
        self.assertAlmostEqual(avg, 8.5, places=6)
        self.assertAlmostEqual(peak, 8.5, places=6)

    def test_averages_and_peaks_over_the_window(self):
        m = self._metrics()
        for render_ms in (4.0, 8.0, 6.0):
            m.record({"render": render_ms}, n_steps=1, fps=60.0)
        avg, peak = m._stat(m._phases["render"])
        self.assertAlmostEqual(avg, 6.0, places=6)
        self.assertAlmostEqual(peak, 8.0, places=6)

    def test_window_evicts_oldest_samples(self):
        m = self._metrics()  # window=4
        for i in range(6):
            m.record({"render": float(i)}, n_steps=1, fps=60.0)
        # only samples 2,3,4,5 survive
        avg, peak = m._stat(m._phases["render"])
        self.assertAlmostEqual(peak, 5.0, places=6)
        self.assertAlmostEqual(avg, (2 + 3 + 4 + 5) / 4, places=6)

    def test_span_accumulates_into_a_bucket_rolled_in_by_record(self):
        m = self._metrics()
        with m.span("render.starfield"):
            pass
        with m.span("render.starfield"):  # same name twice in a frame -> summed
            pass
        # not rolled in until record()
        self.assertEqual(m._spans, {})
        m.record({}, n_steps=1, fps=60.0)
        self.assertIn("render.starfield", m._spans)
        self.assertEqual(len(m._spans["render.starfield"]), 1)

    def test_span_that_skips_a_frame_records_zero_so_its_average_decays(self):
        m = self._metrics()
        with m.span("sim.missions"):
            pass
        m.record({}, n_steps=1, fps=60.0)
        m.record({}, n_steps=1, fps=60.0)  # span didn't fire this frame
        self.assertEqual(list(m._spans["sim.missions"])[-1], 0.0)

    def test_hot_spans_are_sorted_worst_average_first(self):
        m = self._metrics()
        m._spans = {
            "a": __import__("collections").deque([1.0]),
            "b": __import__("collections").deque([5.0]),
            "c": __import__("collections").deque([3.0]),
        }
        names = [row[0] for row in m.hot_spans()]
        self.assertEqual(names, ["b", "c", "a"])

    def test_summary_lines_are_all_strings(self):
        m = self._metrics()
        m.record({"input": 0.1, "sim": 1.0, "render": 4.0, "present": 0.2}, n_steps=2, fps=58.3)
        lines = m.summary_lines()
        self.assertTrue(all(isinstance(s, str) for s in lines))
        self.assertTrue(any("FPS" in s for s in lines))


class TestSoundBoard(unittest.TestCase):
    """The computer-generated UI sound synthesizer (game/audio/sound_board.py).
    render_waveform() is pure Python (no pygame) so the synthesis math is
    tested directly; SoundBoard.play() is exercised for its no-op guards."""

    def _layers(self):
        return [
            {"freq": 1244.51, "dur": 0.10, "wave": "sine", "decay": 0.055, "amp": 0.9},
            {"freq": 1864.66, "dur": 0.17, "wave": "sine", "decay": 0.11, "amp": 0.55, "delay": 0.035},
        ]

    def test_render_waveform_length_covers_the_latest_layer_end(self):
        from game.audio.sound_board import render_waveform
        samples = render_waveform(self._layers(), sample_rate=8000, channels=2)
        # longest layer ends at 0.035 + 0.17 = 0.205s -> 1640 frames, stereo
        self.assertEqual(len(samples), 1640 * 2)

    def test_render_waveform_is_normalized_and_in_16bit_range(self):
        from game.audio.sound_board import render_waveform, MAX_AMPLITUDE
        samples = render_waveform(self._layers(), sample_rate=16000, channels=1)
        peak = max(abs(s) for s in samples)
        self.assertLessEqual(peak, MAX_AMPLITUDE)
        self.assertGreater(peak, MAX_AMPLITUDE * 0.5)  # actually normalized up, not silent

    def test_render_waveform_starts_and_ends_near_zero(self):
        """Anti-click fade - first/last sample must not pop."""
        from game.audio.sound_board import render_waveform
        samples = render_waveform(self._layers(), sample_rate=16000, channels=1)
        self.assertEqual(samples[0], 0)
        self.assertEqual(samples[-1], 0)

    def test_render_waveform_supports_every_waveform(self):
        from game.audio.sound_board import render_waveform
        for wave in ("sine", "square", "saw", "triangle", "noise", "bogus"):
            samples = render_waveform([{"freq": 440.0, "dur": 0.02, "wave": wave}], sample_rate=8000, channels=1)
            self.assertEqual(len(samples), 160)

    def test_play_is_a_noop_when_disabled(self):
        from game.audio.sound_board import SoundBoard
        board = SoundBoard()
        board.enabled = False
        board._rendered.clear()
        board.play("ping")  # must not raise, must not render
        self.assertEqual(board._rendered, {})

    def test_play_ignores_unknown_sound_names(self):
        from game.audio.sound_board import SoundBoard
        board = SoundBoard()
        board.enabled = True
        board.play("does-not-exist")  # must not raise
        self.assertNotIn("does-not-exist", board._rendered)

    def test_default_board_defines_the_ping(self):
        from game.audio.sound_board import sound_board
        self.assertTrue(sound_board.has("ping"))

    def test_per_recipe_volume_scales_the_playback_gain(self):
        """A single-layer recipe can't be made quieter via layer "amp"
        (render_waveform normalizes each sound to the same peak), so
        define(volume=...) applies a gain at play() time instead. The
        default board sets the target-cycle "blip" below 1.0."""
        from game.audio.sound_board import SoundBoard
        board = SoundBoard()
        board.enabled = True
        board.master_volume = 1.0
        self.assertLess(board._recipe_volumes["blip"], 1.0)
        self.assertEqual(board._recipe_volumes.get("ping", 1.0), 1.0)

        played = []
        board.define("q", [{"freq": 440.0, "dur": 0.01}], volume=0.25)
        fake = SimpleNamespace(set_volume=lambda v: played.append(v), play=lambda: None)
        board._rendered["q"] = fake
        board.play("q", volume=0.5)
        self.assertAlmostEqual(played[0], 1.0 * 0.5 * 0.25)

    def test_menu_button_press_plays_the_ping(self):
        """Every menu/dialog button press funnels through
        MenuBase._button_pressed, which fires the ping."""
        from game.ui.menu_base import MenuBase
        with patch("game.ui.menu_base.sound_board") as mock_board:
            self.assertEqual(MenuBase()._button_pressed("resume"), "resume")
            mock_board.play.assert_called_once_with("ping")

    def test_audio_core_json_stays_in_sync_with_the_python_defaults(self):
        """config/modules/audio-core/audio.json is documented (SOUND.md) as
        a data mirror of _register_default_board()'s recipes, "kept in
        sync" by hand - and it's also what config/editor.html's sound
        editor reads, so a recipe added only in Python (as explosion_small/
        explosion_big once were - see git history) is invisible there even
        though it plays fine in game. Catch that drift here instead of by
        someone noticing a sound missing from the editor."""
        import json
        from game.audio.sound_board import SoundBoard
        board = SoundBoard.__new__(SoundBoard)
        board._recipes = {}
        board._recipe_volumes = {}
        board._rendered = {}
        board._freq = 44100
        board._channels = 2
        SoundBoard._register_default_board(board)

        with open("config/modules/audio-core/audio.json", encoding="utf-8") as f:
            mirrored = json.load(f).get("sounds", {})

        missing = set(board._recipes) - set(mirrored)
        self.assertFalse(missing, f"defined in Python but missing from audio-core/audio.json: {missing}")
        for name, layers in board._recipes.items():
            self.assertEqual(mirrored[name].get("layers"), layers, f"{name}: layers out of sync")
            self.assertEqual(mirrored[name].get("volume", 1.0), board._recipe_volumes.get(name, 1.0),
                              f"{name}: volume out of sync")


class TestBackgroundMusic(unittest.TestCase):
    """Procedural ambient loop synthesis (game/audio/music.py) and the
    scene -> track mapping main.py drives."""

    def setUp(self):
        # Redirect the on-disk track cache into a throwaway dir so cache
        # tests (and any pump() that finishes a render) never touch the real
        # music_cache/ next to the project.
        import tempfile
        from game.audio import music as music_mod
        self._cache_dir = tempfile.mkdtemp(prefix="musictest_")
        self._cache_patch = patch.object(music_mod, "MUSIC_CACHE_DIR", self._cache_dir)
        self._cache_patch.start()

    def tearDown(self):
        import shutil
        self._cache_patch.stop()
        shutil.rmtree(self._cache_dir, ignore_errors=True)

    def _small_spec(self):
        return {"loop": 0.5, "root": 110.0, "chords": [[0, 7]], "peak": 0.7}

    def test_render_ambient_loop_is_seamless_length_and_in_range(self):
        from game.audio.music import render_ambient_loop
        spec = {"loop": 2.0, "root": 110.0, "chords": [[0, 7, 12], [-3, 4, 9]], "peak": 0.7}
        samples = render_ambient_loop(spec, sample_rate=4000)
        self.assertEqual(len(samples), int(4000 * 2.0) * 2)  # stereo
        self.assertLessEqual(max(abs(s) for s in samples), 32767)
        self.assertGreater(max(abs(s) for s in samples), 32767 * 0.4)  # normalized, not silent

    def test_incremental_render_matches_the_one_shot_render(self):
        """The track is built incrementally (a few ms per frame via
        MusicPlayer.pump / _ambient_loop_frames) so it never blocks a frame
        or fights the GIL from a thread. Draining the generator by hand must
        produce exactly what the one-shot render_ambient_loop does."""
        from game.audio.music import render_ambient_loop, _ambient_loop_frames
        spec = {"loop": 2.0, "root": 110.0, "chords": [[0, 7, 12], [-3, 4, 9]], "peak": 0.7}
        one_shot = render_ambient_loop(spec, sample_rate=4000)
        gen = _ambient_loop_frames(spec, sample_rate=4000)
        yields = 0
        try:
            while True:
                next(gen)
                yields += 1
        except StopIteration as done:
            incremental = done.value
        self.assertGreater(yields, 5)          # actually pauses many times
        self.assertEqual(one_shot, incremental)

    def _drain(self, player, track, limit=5000):
        for _ in range(limit):
            player.pump()
            if track not in player._renders:
                return
        self.fail(f"render of {track!r} never finished")

    def test_pump_finishes_a_render_and_starts_it(self):
        """pump() advances the in-progress render and, on completion, wraps
        the PCM in a Sound and starts playback of the wanted track."""
        from game.audio.music import MusicPlayer
        player = MusicPlayer()
        player.enabled = True
        player._recipes["menu"] = self._small_spec()
        with patch.object(MusicPlayer, "_start") as mock_start:
            player.set_scene("menu")                     # queues an incremental render
            self.assertIn("menu", player._renders)
            self._drain(player, "menu")
            self.assertIn("menu", player._rendered)
            mock_start.assert_called_once()

    def test_prerender_all_queues_every_track(self):
        """Called at startup so both tracks build during menu time, not the
        first time each is needed."""
        from game.audio.music import MusicPlayer
        player = MusicPlayer()
        player.enabled = True
        player.prerender_all()
        self.assertEqual(set(player._renders), {"menu", "ingame"})

    def test_pump_uses_a_smaller_budget_and_still_finishes_during_gameplay(self):
        """In gameplay the per-frame render budget is smaller (a busy frame
        plus a full budget can miss the vblank), but pump() still drives the
        render to completion - just over more frames."""
        from game.audio.music import MusicPlayer
        self.assertLess(MusicPlayer.INGAME_RENDER_BUDGET_MS, MusicPlayer.RENDER_BUDGET_MS)
        player = MusicPlayer()
        player.enabled = True
        player._recipes["ingame"] = self._small_spec()
        with patch.object(MusicPlayer, "_start"):
            player.set_scene("game")            # _current -> "ingame", smaller budget
            self._drain(player, "ingame")
            self.assertIn("ingame", player._rendered)

    def test_finished_render_is_cached_and_the_next_run_loads_it(self):
        """First build writes a .raw to MUSIC_CACHE_DIR; a fresh player then
        loads that file instead of re-synthesizing, and gets identical PCM."""
        import os
        from game.audio.music import MusicPlayer, _cache_path, render_ambient_loop

        spec = self._small_spec()
        first = MusicPlayer()
        first.enabled = True
        first._recipes["menu"] = spec
        captured = {}
        with patch.object(MusicPlayer, "_start"), \
             patch("game.audio.music.pygame.mixer.Sound",
                   side_effect=lambda buffer=b"": captured.setdefault("first", bytes(buffer))):
            first._ensure_render("menu")
            self._drain(first, "menu")

        self.assertTrue(os.path.exists(_cache_path("menu", spec)))

        second = MusicPlayer()
        second.enabled = True
        second._recipes["menu"] = spec
        with patch.object(MusicPlayer, "_start"), \
             patch("game.audio.music.pygame.mixer.Sound",
                   side_effect=lambda buffer=b"": captured.setdefault("second", bytes(buffer))):
            second._ensure_render("menu")
            self._drain(second, "menu")

        self.assertEqual(captured["first"], captured["second"])
        self.assertEqual(captured["first"], render_ambient_loop(spec).tobytes())

    def test_a_corrupt_cache_file_is_ignored_and_re_rendered(self):
        from game.audio.music import MusicPlayer, _cache_path
        import os

        spec = self._small_spec()
        os.makedirs(self._cache_dir, exist_ok=True)
        with open(_cache_path("menu", spec), "wb") as f:
            f.write(b"\x01\x02\x03")            # wrong length -> must be rejected

        player = MusicPlayer()
        player.enabled = True
        player._recipes["menu"] = spec
        with patch.object(MusicPlayer, "_start"):
            player._ensure_render("menu")
            self._drain(player, "menu")
        self.assertIn("menu", player._rendered)   # recovered via a real render

    def test_cache_path_depends_on_the_recipe(self):
        from game.audio.music import _cache_path
        a = _cache_path("menu", {"loop": 2.0, "root": 110.0, "chords": [[0, 7]]})
        b = _cache_path("menu", {"loop": 2.0, "root": 110.0, "chords": [[0, 8]]})
        self.assertNotEqual(a, b)

    def test_set_scene_maps_menu_screens_to_the_menu_track(self):
        from game.audio.music import MusicPlayer
        player = MusicPlayer()
        player.enabled = True
        with patch.object(MusicPlayer, "_play") as mock_play:
            player.set_scene("menu")
            mock_play.assert_called_once_with("menu")
            mock_play.reset_mock()
            player.set_scene("pilot_name")   # still a menu screen - no switch
            mock_play.assert_not_called()
            player.set_scene("game")          # now gameplay - switch
            mock_play.assert_called_once_with("ingame")

    def test_set_scene_is_inert_when_disabled(self):
        from game.audio.music import MusicPlayer
        player = MusicPlayer()
        player.enabled = False
        with patch.object(MusicPlayer, "_play") as mock_play:
            player.set_scene("menu")
            mock_play.assert_not_called()

    def test_toggle_mute_flips_the_flag(self):
        from game.audio.music import MusicPlayer
        player = MusicPlayer()
        player.enabled = False  # keep it from touching a channel
        self.assertFalse(player.muted)
        player.toggle_mute()
        self.assertTrue(player.muted)
        player.toggle_mute()
        self.assertFalse(player.muted)


class TestAADraw(unittest.TestCase):
    """game/aa_draw.py: mode dispatch and the pygame.draw fallback. pygame is
    mocked here, so this checks which primitives get called, not pixels."""

    TRI = [(0, 0), (10, 0), (5, 10)]

    def setUp(self):
        import game.constants as constants
        self._prev = constants.AA_MODE
        self.addCleanup(setattr, constants, "AA_MODE", self._prev)

    def test_off_mode_uses_plain_pygame_draw(self):
        import game.aa_draw as aa
        import game.constants as constants
        constants.AA_MODE = "off"
        with patch("game.aa_draw.pygame") as mp:
            aa.polygon(MagicMock(), (1, 2, 3), self.TRI)
            aa.circle(MagicMock(), (1, 2, 3), (5, 5), 4)
            mp.draw.polygon.assert_called_once()
            mp.draw.circle.assert_called_once()
            mp.gfxdraw.filled_polygon.assert_not_called()
            mp.gfxdraw.aacircle.assert_not_called()

    def test_supersample_mode_also_uses_plain_pygame_draw(self):
        import game.aa_draw as aa
        import game.constants as constants
        constants.AA_MODE = "supersample"
        with patch("game.aa_draw.pygame") as mp:
            aa.polygon(MagicMock(), (1, 2, 3), self.TRI)
            mp.draw.polygon.assert_called_once()
            mp.gfxdraw.aapolygon.assert_not_called()

    def test_gfxdraw_mode_fills_and_outlines_via_gfxdraw(self):
        import game.aa_draw as aa
        import game.constants as constants
        constants.AA_MODE = "gfxdraw"
        with patch("game.aa_draw.pygame") as mp:
            aa.polygon(MagicMock(), (1, 2, 3), self.TRI)
            mp.gfxdraw.filled_polygon.assert_called_once()
            mp.gfxdraw.aapolygon.assert_called_once()
            mp.draw.polygon.assert_not_called()
            aa.circle(MagicMock(), (1, 2, 3), (5, 5), 4)
            mp.gfxdraw.filled_circle.assert_called_once()
            mp.gfxdraw.aacircle.assert_called_once()

    def test_gfxdraw_stroke_keeps_pygame_for_the_stroke(self):
        import game.aa_draw as aa
        import game.constants as constants
        constants.AA_MODE = "gfxdraw"
        with patch("game.aa_draw.pygame") as mp:
            aa.polygon(MagicMock(), (1, 2, 3), self.TRI, width=2)
            mp.draw.polygon.assert_called_once()       # the stroke itself
            mp.gfxdraw.aapolygon.assert_called_once()  # smoothed on top
            mp.gfxdraw.filled_polygon.assert_not_called()

    def test_gfxdraw_falls_back_when_coords_out_of_range(self):
        import game.aa_draw as aa
        import game.constants as constants
        constants.AA_MODE = "gfxdraw"
        with patch("game.aa_draw.pygame") as mp:
            aa.polygon(MagicMock(), (1, 2, 3), [(0, 0), (99999, 0), (0, 99999)])
            mp.draw.polygon.assert_called_once()
            mp.gfxdraw.filled_polygon.assert_not_called()

    def test_gfxdraw_falls_back_on_gfxdraw_error(self):
        import game.aa_draw as aa
        import game.constants as constants
        constants.AA_MODE = "gfxdraw"
        with patch("game.aa_draw.pygame") as mp:
            mp.gfxdraw.filled_circle.side_effect = ValueError("bad")
            aa.circle(MagicMock(), (1, 2, 3), (5, 5), 4)
            mp.draw.circle.assert_called_once()


class TestExpandShadingAndItems(unittest.TestCase):
    """expand.py: colour and shading are decoupled - a part carries a `color`
    and a `shade` profile name independently - plus the item-layer overrides
    (docs/GRAPHICS_PIPELINE.md)."""

    def _mats(self):
        return {
            "light": [-0.82, -0.57],
            "shading": {
                "flat": {"tone_dark": 0, "tone_light": 0},
                "matte": {"tone_dark": -24, "tone_light": 20},
                "deep": {"tone_dark": -34, "tone_light": 24},
                "sheen": {"tone_dark": -20, "tone_light": 44},
                "glow": {"tone_dark": 0, "tone_light": 0, "emissive": True},
            },
        }

    def test_shade_profile_resolves_by_name(self):
        from game.graphics.expand import shade_profile
        m = self._mats()
        self.assertEqual(shade_profile("deep", m)["tone_dark"], -34)
        self.assertTrue(shade_profile("glow", m).get("emissive"))

    def test_shade_profile_false_is_flat_and_missing_is_matte(self):
        from game.graphics.expand import shade_profile
        m = self._mats()
        self.assertIsNone(shade_profile(False, m))
        self.assertEqual(shade_profile(None, m), m["shading"]["matte"])
        self.assertEqual(shade_profile("bogus", m), m["shading"]["matte"])

    def test_shade_profile_passes_inline_dict_through(self):
        from game.graphics.expand import shade_profile
        inline = {"tone_dark": -5, "tone_light": 5}
        self.assertEqual(shade_profile(inline, self._mats()), inline)

    def test_resolve_color_only_shifts_dark_and_light(self):
        from game.graphics.expand import resolve_color, shade_profile
        m = self._mats()
        pal = {"denim": "#4d5a6b"}
        prof = shade_profile("deep", m)
        mid = resolve_color("denim", "mid", pal, prof)
        self.assertEqual(mid, [0x4d, 0x5a, 0x6b])
        self.assertEqual(resolve_color("denim", "dark", pal, prof),
                         [max(0, c - 34) for c in mid])

    def _article(self):
        return {"regions": [
            {"group": "torso", "color": "denim", "shade": "matte",
             "points": [[0, 0], [2, 0], [2, 3], [0, 3]],
             "details": [{"color": "metal", "shade": "metal",
                          "points": [[0, 0], [1, 0], [1, 1]]}]},
        ]}

    def test_item_color_override_keeps_each_part_shade(self):
        from game.graphics.expand import expand
        m = self._mats()
        m["shading"]["metal"] = {"tone_dark": -40, "tone_light": 48}
        pal = {"denim": "#404040", "plum": "#804060", "metal": "#c0c0c0"}
        over = expand(self._article(), pal, m, body=None, color="plum")
        fill = next(p for p in over if p["role"] == "fill")
        detail = next(p for p in over if p["role"] == "detail")
        self.assertEqual(fill["color"], [0x80, 0x40, 0x60])     # recoloured
        self.assertEqual(detail["color"], [0x80, 0x40, 0x60])   # detail recoloured too
        dark = next(p for p in over if p["role"] == "shade_dark")["color"]
        self.assertEqual(dark, [max(0, c - 24) for c in [0x80, 0x40, 0x60]])  # still matte

    def test_item_shade_override_keeps_each_part_colour(self):
        from game.graphics.expand import expand
        m = self._mats()
        pal = {"denim": "#606060", "metal": "#c0c0c0"}
        base = expand(self._article(), pal, m, body=None)
        shiny = expand(self._article(), pal, m, body=None, shade="sheen")
        self.assertEqual(next(p for p in shiny if p["role"] == "fill")["color"],
                         next(p for p in base if p["role"] == "fill")["color"])
        self.assertEqual(next(p for p in shiny if p["role"] == "shade_light")["color"],
                         [min(255, c + 44) for c in [0x60, 0x60, 0x60]])

    def test_item_parts_override_by_note_not_palette_key(self):
        from game.graphics.expand import expand
        m = self._mats()
        pal = {"denim": "#404040", "metal": "#c0c0c0"}
        art = {"regions": [
            {"group": "torso", "note": "shell", "color": "denim", "shade": "matte",
             "points": [[0, 0], [2, 0], [2, 3], [0, 3]],
             "details": [{"note": "trim", "color": "denim", "shade": "matte",
                          "points": [[0, 0], [1, 0], [1, 1]]}]},
        ]}
        # override targets the region by its note - independent of the "denim"
        # key both parts author; the detail (also "denim") is untouched.
        over = expand(art, pal, m, body=None, parts={"shell": {"color": "#101828"}})
        self.assertEqual(next(p for p in over if p["role"] == "fill")["color"],
                         [16, 24, 40])
        self.assertEqual(next(p for p in over if p["role"] == "detail")["color"],
                         [0x40, 0x40, 0x40])

    def test_parts_override_wins_over_article_wide_color(self):
        from game.graphics.expand import expand
        m = self._mats()
        pal = {"denim": "#404040", "metal": "#c0c0c0", "plum": "#804060"}
        art = {"regions": [
            {"group": "torso", "note": "shell", "color": "denim", "shade": "matte",
             "points": [[0, 0], [2, 0], [2, 3], [0, 3]]},
        ]}
        over = expand(art, pal, m, body=None, color="plum",
                      parts={"shell": {"color": "#101828"}})
        self.assertEqual(next(p for p in over if p["role"] == "fill")["color"],
                         [16, 24, 40])

    def test_no_override_is_identical_to_plain_expand(self):
        from game.graphics.expand import expand
        m = self._mats()
        m["shading"]["metal"] = {"tone_dark": -40, "tone_light": 48}
        pal = {"denim": "#404040", "metal": "#c0c0c0"}
        a = expand(self._article(), pal, m, body=None)
        b = expand(self._article(), pal, m, body=None, color=None, shade=None, parts=None)
        self.assertEqual(a, b)

    def test_rest_splay_is_not_applied_to_articles(self):
        """An arm-group region is authored in the body's rest pose already;
        expand_article must NOT rotate it (that would double the splay)."""
        from game.graphics.expand import expand
        m = self._mats()
        pal = {"denim": "#606060"}
        body = {"rig": {"rest_splay": {"arm": 30}},
                "pivots": {"arm_near": [0, 0], "arm_far": [0, 0]}}
        art = {"outset": 0,
               "regions": [{"group": "arm_near", "color": "denim", "shade": "flat",
                            "points": [[1, 0], [2, 0], [2, 1], [1, 1]], "fits": []}]}
        fill = next(p for p in expand(art, pal, m, body=body) if p["role"] == "fill")
        self.assertEqual([[round(x, 3), round(y, 3)] for x, y in fill["points"]],
                         [[1, 0], [2, 0], [2, 1], [1, 1]])


class TestCurveFormats(unittest.TestCase):
    """A body curve is either a bare polyline (legacy) or a
    {"pts", "ends", "dir"} object the vertex editor writes so it can re-trace
    the curve when the body is reshaped. `_curve` reads `pts` from either."""

    def _body(self, curve):
        return {"sections": {"torso": {"curves": {"side": curve}}}}

    def test_curve_reads_bare_polyline(self):
        from game.graphics.expand import _curve
        self.assertEqual(_curve(self._body([[0, 0], [1, 2]]), "torso.side"),
                         [[0, 0], [1, 2]])

    def test_curve_reads_object_form_pts_only(self):
        from game.graphics.expand import _curve
        c = {"pts": [[0, 0], [1, 2]], "ends": [[0, 0], [1, 2]], "dir": 1}
        self.assertEqual(_curve(self._body(c), "torso.side"), [[0, 0], [1, 2]])

    def test_apply_fits_splices_object_form_curve(self):
        from game.graphics.expand import _apply_fits
        body = self._body({"pts": [[9, 9], [8, 8]], "ends": [], "dir": 1})
        out = _apply_fits([[0, 0], [1, 1], [2, 2]],
                          [{"curve": "torso.side", "from": 1, "to": 1}], body)
        self.assertEqual(out, [[0, 0], [9, 9], [8, 8], [2, 2]])


class TestComposeWorn(unittest.TestCase):
    """compose_worn stacks every part by its position in the story draw order -
    body section names interleaved with garment tag strings. A region with no
    tag sits at its animation group. See docs/GRAPHICS_PIPELINE.md "Draw order"."""

    ORDER = ["back", "arm_far", "torso", "torso_front", "arm_near", "front"]

    def _body_parts(self):
        return [{"sec": s, "tag_": "body"} for s in ("arm_far", "torso", "arm_near")]

    @staticmethod
    def _r(group=None, tag=None, layer=None, name="?"):
        p = {"tag_": name}
        if group: p["group"] = group
        if tag: p["tag"] = tag
        if layer: p["layer"] = layer
        return p

    def test_untagged_region_sits_at_its_group_over_the_body_part(self):
        from game.graphics.expand import compose_worn
        shirt = [self._r(group="torso", name="shirt")]
        out = [p["tag_"] for p in
               compose_worn({}, self._body_parts(), shirt, order=self.ORDER)]
        self.assertEqual(out, ["body", "body", "shirt", "body"])  # after torso body part

    def test_tag_places_region_at_that_slot(self):
        from game.graphics.expand import compose_worn
        pack = [self._r(group="torso", tag="back", name="pack")]      # tag before arm_far
        rig = [self._r(group="torso", tag="torso_front", name="rig")]  # tag after torso
        out = [p["tag_"] for p in
               compose_worn({}, self._body_parts(), pack, rig, order=self.ORDER)]
        self.assertEqual(out, ["pack", "body", "body", "rig", "body"])

    def test_worn_order_breaks_ties_within_a_slot(self):
        from game.graphics.expand import compose_worn
        coat = [self._r(group="torso", name="coat")]
        jacket = [self._r(group="torso", name="jkt")]
        out = [p["tag_"] for p in
               compose_worn({}, self._body_parts(), coat, jacket, order=self.ORDER)]
        self.assertEqual(out[2:4], ["coat", "jkt"])   # jacket listed later -> on top

    def test_legacy_layer_reads_as_a_tag(self):
        from game.graphics.expand import compose_worn
        bag = [self._r(group="torso", layer="back", name="bag")]
        out = [p["tag_"] for p in
               compose_worn({}, self._body_parts(), bag, order=self.ORDER)]
        self.assertEqual(out[0], "bag")               # slot "back" is first

    def test_name_not_in_the_order_sorts_to_the_front(self):
        from game.graphics.expand import compose_worn
        cape = [self._r(group="cape", tag="cape_tag", name="cape")]
        out = [p["tag_"] for p in
               compose_worn({}, self._body_parts(), cape, order=self.ORDER)]
        self.assertEqual(out[-1], "cape")

    def test_expand_article_propagates_tag_and_legacy_layer(self):
        from game.graphics.expand import expand_article
        mats = {"light": [-0.8, -0.5], "shading": {"flat": {"tone_dark": 0, "tone_light": 0}}}
        art = {"outset": 0, "regions": [
            {"group": "torso", "color": "c", "shade": "flat", "layer": "back",
             "points": [[0, 0], [1, 0], [1, 1]]}]}
        parts = expand_article(art, {"c": "#808080"}, mats, body=None)
        self.assertTrue(all(p.get("tag") == "back" for p in parts))


class TestPipelineStoryMaterialsMigrated(unittest.TestCase):
    """The design-JSON pipeline is on the decoupled color/shade model:
    materials.json carries only `shading` profiles, and every design part names
    a `color` + a real `shade` (or `shade: false`). The figure kit lives in
    the shared `figures-human` module (and the ship/station/building set in
    `orbital-std`), so these walk every resolved graphics root (story +
    modules) of a story that pulls both in, not one hardcoded directory."""

    STORY = "the_whisper_line"

    def _graphics_roots(self):
        from game import config_source
        return [os.path.join(r, "graphics") + os.sep
                for r in config_source._search_roots(self.STORY)]

    def _graphics_files(self, subpath="**/*.json"):
        import glob
        seen = {}
        for base in self._graphics_roots():
            for f in glob.glob(base + subpath, recursive=True):
                seen.setdefault(os.path.relpath(f, base), f)  # story wins
        return sorted(seen.values())

    def test_materials_json_has_shading_and_no_material_map(self):
        from game.graphics import story_assets
        m = story_assets._materials(self.STORY)
        self.assertTrue(m.get("shading"))
        self.assertNotIn("materials", m)

    def test_every_part_names_a_known_shade_and_a_color(self):
        import json
        from game.graphics import story_assets
        profiles = set(story_assets._materials(self.STORY)["shading"])
        bad = []

        def walk(o, f):
            if isinstance(o, list):
                for v in o:
                    walk(v, f)
            elif isinstance(o, dict):
                if "material" in o:
                    bad.append(f"{f}: stray 'material' key")
                sh = o.get("shade")
                if sh not in (None, False) and sh not in profiles:
                    bad.append(f"{f}: shade {sh!r} not a profile")
                for v in o.values():
                    walk(v, f)

        for f in self._graphics_files():
            if f.endswith("materials.json"):
                continue
            walk(json.load(open(f, encoding="utf-8")), f)
        self.assertEqual(bad, [])

    def test_no_item_uses_the_retired_colors_key(self):
        import json
        bad = []
        for f in self._graphics_files("items/*.json"):
            if "colors" in json.load(open(f, encoding="utf-8")):
                bad.append(f)
        self.assertEqual(bad, [], "items now use `color` + `parts`, not `colors`")

    def test_every_item_parts_note_exists_in_its_geometry(self):
        import json
        from game import config_source
        bad = []
        for f in self._graphics_files("items/*.json"):
            it = json.load(open(f, encoding="utf-8"))
            if not it.get("parts"):
                continue
            art = json.load(open(config_source.story_path(
                self.STORY, "graphics", "articles", it["geometry"] + ".json"), encoding="utf-8"))
            notes = set()
            for r in art.get("regions", []):
                notes.add(r.get("note"))
                for d in r.get("details", []):
                    notes.add(d.get("note"))
                for cut in (r.get("geometry") or {}).values():
                    for d in cut.get("details", []):
                        notes.add(d.get("note"))
            missing = [n for n in it["parts"] if n not in notes]
            if missing:
                bad.append(f"{f}: parts note(s) not in {it['geometry']}: {missing}")
        self.assertEqual(bad, [])

    def test_every_common_kit_set_resolves_and_expands(self):
        import glob
        import json
        from game.graphics import story_assets
        for f in self._graphics_files("sets/ck_*.json"):
            name = os.path.basename(f)[:-5]
            for body in ("human_masc", "human_femme"):
                _, worn = story_assets._body_worn(
                    self.STORY, body, name, "civilian")
                self.assertTrue(worn, f"{name} on {body} expanded to nothing")


if __name__ == "__main__":
    unittest.main()
