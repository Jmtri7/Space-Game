"""Flight Physics — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


class TestHandleScrollingInput(unittest.TestCase):
    """Test _handle_scrolling_input helper function"""

    def setUp(self):
        self.items = ["save1", "save2", "save3", "save4", "save5", "save6"]
        self.max_visible = 3

    def test_down_moves_selection(self):
        """Pressing DOWN should move selection forward"""
        selected, scroll = utils._handle_scrolling_input(
            274, 0, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)
        self.assertEqual(scroll, 0)

    def test_down_wraps_at_end(self):
        """Selection should wrap to 0 when reaching end"""
        selected, scroll = utils._handle_scrolling_input(
            274, 5, self.items, 3, self.max_visible
        )
        self.assertEqual(selected, 0)
        self.assertEqual(scroll, 0)

    def test_down_scrolls_when_needed(self):
        """Scroll should advance when selection reaches bottom of visible area"""
        selected, scroll = utils._handle_scrolling_input(
            274, 2, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 3)
        self.assertEqual(scroll, 1)

    def test_up_moves_selection_back(self):
        """Pressing UP should move selection backward"""
        selected, scroll = utils._handle_scrolling_input(
            273, 2, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)
        self.assertEqual(scroll, 0)

    def test_up_wraps_at_start(self):
        """Selection should wrap to end when moving up from 0"""
        selected, scroll = utils._handle_scrolling_input(
            273, 0, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 5)
        self.assertEqual(scroll, 3)

    def test_up_scrolls_when_needed(self):
        """Scroll should go back when selection is at top of visible area"""
        selected, scroll = utils._handle_scrolling_input(
            273, 2, self.items, 2, self.max_visible
        )
        self.assertEqual(selected, 1)
        self.assertEqual(scroll, 1)

    def test_w_key_is_up(self):
        """W key should behave like UP"""
        selected, scroll = utils._handle_scrolling_input(
            119, 2, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)

    def test_s_key_is_down(self):
        """S key should behave like DOWN"""
        selected, scroll = utils._handle_scrolling_input(
            115, 0, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)

    def test_invalid_key_no_change(self):
        """Invalid key should not change selection or scroll"""
        selected, scroll = utils._handle_scrolling_input(
            97, 2, self.items, 1, self.max_visible
        )
        self.assertEqual(selected, 2)
        self.assertEqual(scroll, 1)


class TestCameraRotation(unittest.TestCase):
    """Camera.set_angle() / to_screen() / to_world() view rotation (Q/E in
    the Space View). The focus point - where set_camera_offset() always
    parks the followed entity - must stay pinned on screen at any angle,
    and to_world must invert to_screen."""

    def _camera_focused_on(self, px, py, angle=0):
        cam = utils.Camera(1000, 800)
        cam.set_offset(px - GAME_WIDTH // 2, py - GAME_HEIGHT // 2)
        cam.set_angle(angle)
        return cam

    def test_focus_point_is_pinned_regardless_of_angle(self):
        px, py = 5000, 3000
        unrotated = self._camera_focused_on(px, py, 0).to_screen(px, py)
        for angle in (0, 15, 90, 180, 270, 359):
            rotated = self._camera_focused_on(px, py, angle).to_screen(px, py)
            self.assertEqual(rotated, unrotated)

    def test_angle_zero_matches_unrotated_projection(self):
        cam = self._camera_focused_on(1000, 1000, 0)
        # A point offset from focus projects exactly as scale+offset alone.
        self.assertEqual(cam.to_screen(1200, 1000), cam.to_screen(1200, 1000))
        scale = cam.get_scale()
        ox, oy = cam.get_world_offset()
        expected = (int(round((1200 - cam.offset_x) * scale + ox)),
                    int(round((1000 - cam.offset_y) * scale + oy)))
        self.assertEqual(cam.to_screen(1200, 1000), expected)

    def test_ninety_degrees_maps_north_to_east(self):
        px, py = 2000, 2000
        cam = self._camera_focused_on(px, py, 90)
        focus = cam.to_screen(px, py)
        # A point due north of the focus (smaller world y) should render
        # 90 deg clockwise from "up" - i.e. to the right of the focus, at
        # roughly the focus's screen height.
        north = cam.to_screen(px, py - 300)
        self.assertGreater(north[0], focus[0])
        self.assertAlmostEqual(north[1], focus[1], delta=2)

    def test_visible_world_bounds_shrink_as_the_camera_zooms_in(self):
        cam = self._camera_focused_on(4000, 4000, 0)
        cam.set_zoom_limits(1.0, 10.0)
        cam.set_zoom(2.0)
        wx0, wy0, wx1, wy1 = cam.visible_world_bounds()
        span_lo = (wx1 - wx0, wy1 - wy0)
        cam.set_zoom(8.0)
        wx0, wy0, wx1, wy1 = cam.visible_world_bounds()
        span_hi = (wx1 - wx0, wy1 - wy0)
        # 4x the zoom -> ~1/4 the visible world span, and the focus stays inside
        self.assertAlmostEqual(span_lo[0] / span_hi[0], 4.0, delta=0.2)
        self.assertTrue(wx0 <= 4000 <= wx1 and wy0 <= 4000 <= wy1)

    def test_visible_world_bounds_margin_grows_the_box(self):
        cam = self._camera_focused_on(0, 0, 0)
        a = cam.visible_world_bounds()
        b = cam.visible_world_bounds(100)
        self.assertAlmostEqual(b[0], a[0] - 100)
        self.assertAlmostEqual(b[2], a[2] + 100)

    def test_to_world_inverts_to_screen_at_an_angle(self):
        cam = self._camera_focused_on(7000, 1500, 37)
        for wx, wy in ((7000, 1500), (7200, 1400), (6800, 1750), (7000, 900)):
            sx, sy = cam.to_screen(wx, wy)
            rx, ry = cam.to_world(sx, sy)
            self.assertAlmostEqual(rx, wx, delta=1.0)
            self.assertAlmostEqual(ry, wy, delta=1.0)

    def test_rotate_vector_leaves_length_unchanged(self):
        cam = self._camera_focused_on(0, 0, 50)
        dx, dy = cam.rotate_vector(3, 4)
        self.assertAlmostEqual(math.hypot(dx, dy), 5.0, places=6)


class TestAutopilotPhysics(unittest.TestCase):
    """Test seek-mode autopilot arrives at a landing_site with precise position
    and velocity, using the real Ship/Autopilot/LandingSite classes and the
    same engage_seek() + ship.update() flow the game itself drives - not a
    reimplementation of the landing condition, so this can't drift out of
    sync with autopilot.py's actual disengage logic."""

    def simulate_autopilot_to_landing(self, ship, target_x, target_y, landing_distance=100, max_frames=2000):
        """Simulate ship autopilot from start to landing using real game physics"""
        target = LandingSite(target_x, target_y, graphics={"landing_distance": landing_distance})
        ship.x = 0
        ship.y = 0
        ship.angle = 0
        ship.velocity_x = 0
        ship.velocity_y = 0
        ship.thrust = 0
        ship.engage_seek(target)

        frames = 0
        min_distance = float('inf')
        oscillated = False  # Did ship overshoot then come back?

        while ship.autopilot_active and frames < max_frames:
            frames += 1
            ship.update()  # advances autopilot internally, exactly as the game does

            distance = target.get_distance(ship.x, ship.y)

            # Track closest approach and detect oscillation
            if distance < min_distance:
                min_distance = distance
            elif distance > min_distance + 50 and min_distance < landing_distance + 50:
                # Ship got close, then moved away significantly = oscillation
                oscillated = True

        # autopilot_active going False (via Autopilot.disengage()) is the
        # game's own signal that it landed - not a separate distance/speed
        # check re-guessed here.
        landed = not ship.autopilot_active
        distance = target.get_distance(ship.x, ship.y)
        speed = (ship.velocity_x ** 2 + ship.velocity_y ** 2) ** 0.5
        return {
            'landed': landed,
            'frames': frames,
            'distance': distance,
            'speed': speed,
            'min_distance': min_distance,
            'oscillated': oscillated,
        }

    def test_autopilot_shuttle_lands_precisely(self):
        """Shuttle (config/stories/default/ship_types.json stats) lands once, no oscillation"""
        ship = Ship(0, 0)
        ship.acceleration_magnitude = 0.12
        ship.max_velocity = 2.0
        ship.rotation_speed = 4

        result = self.simulate_autopilot_to_landing(ship, 500, 0)

        self.assertTrue(result['landed'], f"Autopilot failed to land (frames: {result['frames']})")
        self.assertLess(result['distance'], 20,
                        f"Shuttle distance {result['distance']:.1f} - should arrive close to the landing_site's center")
        self.assertEqual(result['speed'], 0,
                        f"Shuttle velocity {result['speed']:.3f} - should be fully parked (zero velocity)")
        self.assertFalse(result['oscillated'],
                        f"Shuttle oscillated - ship should come to stop once, not bounce")

    def test_autopilot_freighter_lands_precisely(self):
        """Freighter (config/stories/default/ship_types.json stats) lands once, no oscillation"""
        ship = Ship(0, 0)
        ship.acceleration_magnitude = 0.1
        ship.max_velocity = 2.0
        ship.rotation_speed = 1

        result = self.simulate_autopilot_to_landing(ship, 400, 0)

        self.assertTrue(result['landed'], f"Autopilot failed to land (frames: {result['frames']})")
        self.assertLess(result['distance'], 20,
                        f"Freighter distance {result['distance']:.1f} - should arrive close to the landing_site's center")
        self.assertEqual(result['speed'], 0,
                        f"Freighter velocity {result['speed']:.3f} - should be fully parked (zero velocity)")
        self.assertFalse(result['oscillated'],
                        f"Freighter oscillated - ship should come to stop once, not bounce")

    def test_autopilot_patrol_lands_precisely(self):
        """Patrol (config/stories/default/ship_types.json stats) lands once, no oscillation"""
        ship = Ship(0, 0)
        ship.acceleration_magnitude = 0.35
        ship.max_velocity = 5.0
        ship.rotation_speed = 7

        result = self.simulate_autopilot_to_landing(ship, 300, 0)

        self.assertTrue(result['landed'], f"Autopilot failed to land (frames: {result['frames']})")
        self.assertLess(result['distance'], 20,
                        f"Patrol distance {result['distance']:.1f} - should arrive close to the landing_site's center")
        self.assertEqual(result['speed'], 0,
                        f"Patrol velocity {result['speed']:.3f} - should be fully parked (zero velocity)")
        self.assertFalse(result['oscillated'],
                        f"Patrol oscillated - ship should come to stop once, not bounce")


class TestAsteroidField(unittest.TestCase):
    """Test AsteroidField's weighted type selection, per-type size/speed
    ranges, spin behavior, and revisit-produces-different-content -
    the pieces of PHYSICS.md's asteroid-specific non-determinism rule
    (see AsteroidField's own docstring) that would silently regress this
    back into StarField-style position-determinism if broken."""

    def _types(self):
        return [
            {"graphics": {"shape": "round", "color": [150, 150, 150]},
             "weight": 1, "size_range": (3, 6), "speed_range": (0, 0.3)},
            {"graphics": {"shape": "jagged", "color": [120, 85, 55], "vertex_count_range": (7, 11),
                          "jaggedness": 0.35, "spin_speed_range": (1.0, 1.0)},
             "weight": 1, "size_range": (5, 10), "speed_range": (0, 0.3)},
        ]

    def test_generate_chunk_respects_size_and_speed_ranges(self):
        field = AsteroidField(types=self._types(), per_chunk_range=(20, 20), seed=1)
        asteroids = field._generate_chunk(0, 0)
        self.assertEqual(len(asteroids), 20)
        for asteroid in asteroids:
            self.assertGreaterEqual(asteroid.size, 3)
            self.assertLessEqual(asteroid.size, 10)
            speed = (asteroid.velocity_x ** 2 + asteroid.velocity_y ** 2) ** 0.5
            self.assertLessEqual(speed, 0.3 + 1e-9)

    def test_generate_chunk_produces_both_configured_types(self):
        field = AsteroidField(types=self._types(), per_chunk_range=(200, 200), seed=2)
        shapes = {asteroid.shape for asteroid in field._generate_chunk(0, 0)}
        self.assertEqual(shapes, {"round", "jagged"})

    def test_jagged_asteroid_spins_round_does_not(self):
        field = AsteroidField(types=self._types(), per_chunk_range=(30, 30), seed=3)
        asteroids = field._generate_chunk(0, 0)
        jagged = [a for a in asteroids if a.shape == "jagged"]
        round_ones = [a for a in asteroids if a.shape == "round"]
        self.assertTrue(jagged and round_ones, "expected both shapes among 30 asteroids")

        for asteroid in jagged:
            start_angle = asteroid.angle
            asteroid.update()
            self.assertNotEqual(asteroid.angle, start_angle)
        for asteroid in round_ones:
            asteroid.update()
            self.assertEqual(asteroid.angle, 0)

    def test_revisiting_unloaded_chunk_generates_different_asteroids(self):
        """Same chunk key, generated twice in a row (simulating leave-and-return
        after CHUNK_KEEP_RADIUS drops it) - should NOT reproduce the same
        asteroids, unlike StarField's deterministic-by-position chunks."""
        field = AsteroidField(types=self._types(), per_chunk_range=(3, 3), seed=4)
        first = [(round(a.x, 3), round(a.y, 3), a.shape) for a in field._generate_chunk(0, 0)]
        second = [(round(a.x, 3), round(a.y, 3), a.shape) for a in field._generate_chunk(0, 0)]
        self.assertNotEqual(first, second)


class TestSpaceScreenParkAt(unittest.TestCase):
    """Regression test: loading directly into a station/moon save used to
    call the full restore_state(), which fed the LocationScreen's own
    walking-position dict (game_state["player"]) into the ship's x/y as if
    it were the ship's space position - scattering the ship to wherever
    that (unrelated, much smaller-scale) interior coordinate happened to
    be instead of docking it at the landing_site. main.py now calls
    restore_possessions() + park_at() for station/moon loads instead."""

    def test_park_at_places_the_ship_exactly_on_the_landing_site(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        game_screen.park_at(game_screen.moon)
        self.assertEqual((game_screen.player.x, game_screen.player.y), (game_screen.moon.x, game_screen.moon.y))
        self.assertEqual((game_screen.player.velocity_x, game_screen.player.velocity_y), (0, 0))

    def test_restore_possessions_does_not_touch_ship_position(self):
        """The whole point of the split: restore_possessions() must never
        read a "player" key at all, so a caller can safely follow it with
        park_at() without the interior's walking-position dict clobbering
        the ship's space position first."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        original_position = (game_screen.player.x, game_screen.player.y)
        # An interior-shaped state - x/y here mean a LocationScreen's local
        # walking position, wildly different scale from ship space coords.
        interior_shaped_state = {"player": {"x": 800, "y": 800}, "possessions": {"credits": 500, "owned_ships": [], "loans": []}}
        game_screen.restore_possessions(interior_shaped_state)
        self.assertEqual((game_screen.player.x, game_screen.player.y), original_position)
        self.assertEqual(game_screen.player.person.possessions.credits, 500)


class TestCameraZoomControl(unittest.TestCase):
    """Player-adjustable world zoom - mouse wheel over open space, clamped to
    the active context's range, remembered per context, saved with the game."""

    def _wheel(self, y):
        return SimpleNamespace(type=pygame_mock.MOUSEWHEEL, x=0, y=y)

    def test_space_wheel_zoom_clamps_to_story_range(self):
        s = SpaceScreen(pilot_name="T", story="default")
        for _ in range(40):
            s.handle_input([self._wheel(1)])   # zoom in, wheel up
        self.assertEqual(s.camera_zoom, s.camera_zoom_max)
        for _ in range(60):
            s.handle_input([self._wheel(-1)])  # zoom out
        self.assertEqual(s.camera_zoom, s.camera_zoom_min)

    def test_space_wheel_zoom_steps_and_reaches_the_shared_camera(self):
        s = SpaceScreen(pilot_name="T", story="default")
        start = s.camera_zoom
        s.handle_input([self._wheel(1)])
        self.assertAlmostEqual(s.camera_zoom, start + CAMERA_ZOOM_STEP)
        s.update()
        self.assertAlmostEqual(utils._camera.zoom, s.camera_zoom)

    def test_interior_wheel_zoom_clamps_to_its_own_range(self):
        loc = LocationScreen(config_data={"label": "X", "rooms": [{"rect": [0, 0, 800, 600]}]},
                             world_width=800, world_height=600, story="default")
        for _ in range(20):
            loc.handle_input([self._wheel(1)])
        self.assertEqual(loc.camera_zoom, loc.camera_zoom_max)  # 8.0, not the Space View's 9.0

    def test_zoom_survives_save_round_trip_and_reclamps(self):
        s = SpaceScreen(pilot_name="T", story="default")
        s.camera_zoom = 4.5
        state = s.get_state()
        self.assertEqual(state["camera_zoom"], 4.5)
        s2 = SpaceScreen(pilot_name="T", story="default")
        s2.restore_state(state)
        self.assertEqual(s2.camera_zoom, 4.5)
        # A level saved under looser limits is pulled back into range.
        s2.restore_state({"camera_zoom": 99.0})
        self.assertEqual(s2.camera_zoom, s2.camera_zoom_max)


if __name__ == "__main__":
    unittest.main()
