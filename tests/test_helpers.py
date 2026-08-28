"""Unit tests for helper functions extracted from main.py"""
import sys
import os
import io
import math
import tempfile
import shutil
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock, PropertyMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock pygame before importing modules to avoid display requirements
pygame_mock = MagicMock()
pygame_mock.K_UP = 273
pygame_mock.K_DOWN = 274
pygame_mock.K_LEFT = 276
pygame_mock.K_RIGHT = 275
pygame_mock.K_w = 119
pygame_mock.K_s = 115
pygame_mock.K_a = 97
pygame_mock.K_d = 100

# Mock display.Info to avoid display issues
info_mock = MagicMock()
info_mock.current_w = 1920
info_mock.current_h = 1080
pygame_mock.display.Info.return_value = info_mock
pygame_mock.init = MagicMock()

sys.modules['pygame'] = pygame_mock

import game.utils as utils
from game.world.ship import Ship
from game.world.landable import Landable
from game.world.person import Person
from game.world.possessions import Possessions
from game.world.dialogue import Dialogue, option_actions, apply_shared_actions, shared_action_blocked_reason
from game.world.mission import start_mission, check_mission_progress, mission_status_lines, abandon_mission
from game.ui.report_menu import ReportMenu, mission_report, possessions_report
from game.ui.ui_theme import side_panel_max_width, center_panel_max_width, side_panel_width, hud_margin
from game.screens.location_screen import LocationScreen, normalize_room, normalize_decoration, point_in_polygon
from game.world.dock_routine import DockRoutine, ROLE_EXIT_PREFERENCE, MAX_LATERAL_HOPS
from game.world.indoor_pathfinder import IndoorPathfinder, NavGrid
from game.world.character import Character
from game.world.orbit_player_routine import OrbitPlayerRoutine
from game.world.wander_routine import WanderRoutine
from game.world.system_state import SystemState
from game.world.asteroid_field import AsteroidField
from game.ui.selectable_list import SelectableList
from game.ui.save_browser import SaveBrowser
from game.ui.choice_dialog import ChoiceDialog
from game.ui.backdrop_menu import BackdropMenu
from game.ui.confirm_dialog import ConfirmDialog
from game.ui.shop_menu import ShopMenu
from game.ui.ship_browser_menu import ShipBrowserMenu, _approximate_size_label
from game.ui.icon_grid import IconGrid
from game.ui.outfitting_menu import OutfittingMenu, SLOT_COLORS
from game.screens.space_screen import SpaceScreen, TARGET_MODES
from game.constants import GAME_WIDTH, GAME_HEIGHT
from main import build_save_game_state, warn_if_story_version_mismatch


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


class TestAutopilotPhysics(unittest.TestCase):
    """Test seek-mode autopilot arrives at a landable with precise position
    and velocity, using the real Ship/Autopilot/Landable classes and the
    same engage_seek() + ship.update() flow the game itself drives - not a
    reimplementation of the landing condition, so this can't drift out of
    sync with autopilot.py's actual disengage logic."""

    def simulate_autopilot_to_landing(self, ship, target_x, target_y, landing_distance=100, max_frames=2000):
        """Simulate ship autopilot from start to landing using real game physics"""
        target = Landable(target_x, target_y, graphics={"landing_distance": landing_distance})
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
                        f"Shuttle distance {result['distance']:.1f} - should arrive close to the landable's center")
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
                        f"Freighter distance {result['distance']:.1f} - should arrive close to the landable's center")
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
                        f"Patrol distance {result['distance']:.1f} - should arrive close to the landable's center")
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


class TestPersonOutfitRendering(unittest.TestCase):
    """Person.draw() with the default story's outfits - the culture/role
    suits plus the accessory-piece keys (shoulder/spike/collar/chest_plate/
    sash/belt/badge/backpack/antenna/visor). pygame is mocked here, so this
    exercises the geometry math (to_screen, _shade, the hypot in the sash
    band) and catches a typo'd color key in graphics.json, not the pixels."""

    KNOWN_OUTFIT_KEYS = {
        "helmet_color", "suit_color", "boot_color",
        "shoulder_color", "spike_color", "collar_color", "chest_plate_color",
        "sash_color", "belt_color", "badge_color", "backpack_color",
        "antenna_color", "visor_color",
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

    def test_visor_replaces_the_eyes(self):
        with patch("game.world.person.pygame") as mock_pygame:
            Person(0, 0, outfit={"suit_color": [10, 10, 10], "visor_color": [200, 120, 90]}).draw(MagicMock())
            polygons = mock_pygame.draw.polygon.call_count
            circles = mock_pygame.draw.circle.call_count
        self.assertGreater(polygons, 0)
        # Head + its outline = 2 circles; a bare body would add 2 eye circles.
        self.assertEqual(circles, 2)


class TestLocationExitOptions(unittest.TestCase):
    """Test LocationScreen.get_exit_options() - the config-driven list of
    where an interior's exit leads (connected_locations plus "ship"),
    consumed by both the player's exit menu and DockRoutine's AI choice."""

    def test_no_config_defaults_to_ship_only(self):
        """A location with no connected_locations/return_to_ship in its
        config behaves exactly like before this feature existed - a single
        immediate exit back to the ship."""
        screen = LocationScreen(config_data={"label": "Station"}, world_width=800, world_height=600)
        self.assertEqual(screen.get_exit_options(), ["ship"])

    def test_connected_locations_come_before_ship(self):
        screen = LocationScreen(config_data={
            "label": "City", "connected_locations": ["wilderness"],
        }, world_width=1600, world_height=1600)
        self.assertEqual(screen.get_exit_options(), ["wilderness", "ship"])

    def test_return_to_ship_false_omits_ship(self):
        screen = LocationScreen(config_data={
            "label": "Wilderness", "connected_locations": ["city"], "return_to_ship": False,
        }, world_width=1600, world_height=1600)
        self.assertEqual(screen.get_exit_options(), ["city"])


class TestDockRoutineExitChoice(unittest.TestCase):
    """Test DockRoutine._choose_exit() - the AI-pilot equivalent of the
    player's exit menu, driven by ROLE_EXIT_PREFERENCE instead of a
    keypress."""

    def _make_ai_ship(self, role):
        return SimpleNamespace(role=role, person=Person(0, 0))

    def _register_test_role(self, role, preference):
        """Register a throwaway role -> preference entry in the real
        ROLE_EXIT_PREFERENCE dict for the duration of one test, so
        "does a role that prefers multiple connected locations behave
        correctly" can be tested as a general mechanism, independent of
        whatever the real game's freighter_pilot preference happens to be
        tuned to right now (see the "wilderness" flavor removed after it
        caused a visiting pilot to visibly glitch in and out of an empty
        room - the mechanism itself was never the problem)."""
        ROLE_EXIT_PREFERENCE[role] = preference
        self.addCleanup(ROLE_EXIT_PREFERENCE.pop, role, None)

    def test_unconfigured_role_always_returns_to_ship(self):
        """A role with no ROLE_EXIT_PREFERENCE entry falls back to
        DEFAULT_EXIT_PREFERENCE - reboards immediately, exactly like every
        pilot did before connected_locations existed."""
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(all_exit_options=lambda: ["wilderness", "ship"])
        ai_ship = self._make_ai_ship(role="patrol_officer")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_configured_role_prefers_connected_location(self):
        self._register_test_role("test_multi_stop_role", ["wilderness", "ship"])
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(all_exit_options=lambda: ["wilderness", "ship"])
        ai_ship = self._make_ai_ship(role="test_multi_stop_role")
        self.assertEqual(routine._choose_exit(ai_ship), "wilderness")

    def test_already_visited_location_is_skipped(self):
        """Regression test: a role preferring both connected locations
        must not pick one it already visited this stop, or it would
        ping-pong between them forever and never reboard."""
        self._register_test_role("test_multi_stop_role", ["city", "ship"])
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(all_exit_options=lambda: ["city", "ship"])
        routine._visited_this_stop = {"city"}
        ai_ship = self._make_ai_ship(role="test_multi_stop_role")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_full_stop_visits_every_connected_location_then_reboards(self):
        """End-to-end regression test for the ping-pong bug: a pilot whose
        role prefers both of two locations that each connect back to the
        other should visit both once, then reboard - never loop forever -
        using the real phase machine (run()), not a reimplementation of it.
        Uses a throwaway test role rather than the real freighter_pilot
        (see _register_test_role) - whether the mechanism terminates
        correctly shouldn't depend on the game's current flavor tuning."""
        self._register_test_role("test_multi_stop_role", ["wilderness", "city", "ship"])
        city_config = {"label": "City", "connected_locations": ["wilderness"], "npcs": []}
        wilderness_config = {"label": "Wilderness", "connected_locations": ["city"], "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={"city": city_config, "wilderness": wilderness_config})

        interior_cache = {}
        def get_interior_screen(landable, key):
            cache_key = (id(landable), key)
            if cache_key not in interior_cache:
                config = landable.interiors.get(key)
                if not config:
                    return None
                world_width, world_height = landable.interior_world_size
                interior_cache[cache_key] = LocationScreen(config_data=config, world_width=world_width, world_height=world_height)
            return interior_cache[cache_key]

        ai_ship = SimpleNamespace(
            role="test_multi_stop_role",
            person=Person(0, 0),
            ashore=False,
            get_interior_screen=get_interior_screen,
            autopilot_active=False,
            engage_seek=lambda target: None,
        )

        routine = DockRoutine(route=[stop])
        routine._begin_walking_in(ai_ship)

        # _visited_this_stop is cleared by _reboard() once the routine
        # actually leaves (so the *next* stop starts with a clean slate) -
        # so the only way to observe "did it visit both first" is to
        # accumulate it frame by frame, not just check its state after
        # the loop exits.
        frames = 0
        visited_history = set()
        while routine.phase != "flying" and frames < 2000:
            visited_history |= routine._visited_this_stop
            routine.run(ai_ship)
            frames += 1

        self.assertEqual(routine.phase, "flying", "Routine got stuck instead of reboarding")
        self.assertEqual(visited_history, {"city", "wilderness"},
                          "Should have visited both connected locations before leaving")
        self.assertFalse(ai_ship.ashore)

    def test_full_stop_with_a_real_character_not_a_fake(self):
        """Same scenario as test_full_stop_visits_every_connected_location_
        then_reboards, but built through the real Character.for_ai_pilot()
        factory (real Ship, real Person, real Possessions/Dialogue) instead
        of a SimpleNamespace fake - proves the composed Character actually
        duck-types as a ship (engage_seek/autopilot_active) and as a body
        (person.x/y) well enough for DockRoutine to drive both ends of it."""
        city_config = {"label": "City", "connected_locations": ["wilderness"], "npcs": []}
        wilderness_config = {"label": "Wilderness", "connected_locations": ["city"], "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={"city": city_config, "wilderness": wilderness_config})

        interior_cache = {}
        def get_interior_screen(landable, key):
            cache_key = (id(landable), key)
            if cache_key not in interior_cache:
                config = landable.interiors.get(key)
                if not config:
                    return None
                world_width, world_height = landable.interior_world_size
                interior_cache[cache_key] = LocationScreen(config_data=config, world_width=world_width, world_height=world_height)
            return interior_cache[cache_key]

        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="freighter",
            graphics=None, pilot={"name": "Elena Voss", "role": "freighter_pilot"},
            route=[stop], get_interior_screen=get_interior_screen,
        )
        self.assertIsInstance(character.routine, DockRoutine)
        character.routine.route = [stop]
        character.routine._route_index = 0
        character.routine._begin_walking_in(character)

        frames = 0
        while character.routine.phase != "flying" and frames < 2000:
            character.routine.run(character)
            frames += 1

        self.assertEqual(character.routine.phase, "flying", "Routine got stuck instead of reboarding")
        self.assertFalse(character.ashore)
        # The ship itself never moved (it's parked, waiting) - only the
        # person walked around on foot.
        self.assertEqual((character.ship.x, character.ship.y), (0, 0))

    def test_multi_hop_graph_routes_through_a_middle_node_to_ship(self):
        """Regression test for the station's concourse/spaceport layout:
        "ship" isn't directly reachable from the room a freighter lands in
        (only the spaceport offers it), so the routine must hop through
        whichever connected location actually leads to the ship - found by
        searching the interiors graph (Landable.interior_adjacency /
        get_ship_entry_key, resolved via TOWARD_SHIP), not wander into an
        unrelated dead end first."""
        hub_config = {"label": "Hub", "connected_locations": ["dead_end", "spaceport"], "return_to_ship": False, "npcs": []}
        dead_end_config = {"label": "Dead End", "connected_locations": ["hub"], "return_to_ship": False, "npcs": []}
        spaceport_config = {"label": "Spaceport", "connected_locations": ["hub"], "return_to_ship": True, "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={
            "hub": hub_config, "dead_end": dead_end_config, "spaceport": spaceport_config,
        })
        routine = DockRoutine(route=[stop])
        routine._location = SimpleNamespace(interior_key="hub", all_exit_options=lambda: ["dead_end", "spaceport"])
        routine._visited_this_stop = {"hub"}
        ai_ship = self._make_ai_ship(role="freighter_pilot")

        choice = routine._choose_exit(ai_ship)
        self.assertEqual(choice, "spaceport", "Should route toward the room that leads to the ship, not the dead end")

        routine._location = SimpleNamespace(interior_key="spaceport", all_exit_options=lambda: ["hub", "ship"])
        routine._visited_this_stop.add("spaceport")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_routes_to_the_ship_room_regardless_of_its_name(self):
        """The room that leads back to the ship isn't necessarily called
        "spaceport" - a different station could name it anything, as long
        as its own return_to_ship is set (Landable.get_ship_entry_key).
        Routing has to key off that, not a literal string - this is the
        scenario that would have failed under the old hardcoded
        ROLE_EXIT_PREFERENCE = ["spaceport", "ship"]."""
        hub_config = {"label": "Hub", "connected_locations": ["docking_bay"], "return_to_ship": False, "npcs": []}
        docking_bay_config = {"label": "Docking Bay", "connected_locations": ["hub"], "return_to_ship": True, "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={"hub": hub_config, "docking_bay": docking_bay_config})
        routine = DockRoutine(route=[stop])
        routine._location = SimpleNamespace(interior_key="hub", all_exit_options=lambda: ["docking_bay"])
        routine._visited_this_stop = {"hub"}
        ai_ship = self._make_ai_ship(role="freighter_pilot")

        self.assertEqual(routine._choose_exit(ai_ship), "docking_bay")

    def test_safety_cap_forces_reboard_when_ship_is_never_reachable(self):
        """If nothing ever leads to "ship" (a misconfigured or future
        role/graph combination this feature hasn't been tuned for), the
        MAX_LATERAL_HOPS cap must still force a reboard rather than wander
        forever - this is what actually caught the corridor<->dormitory
        ping-pong during development, before ROLE_EXIT_PREFERENCE routed
        freighter_pilot through the spaceport."""
        room_a = SimpleNamespace(all_exit_options=lambda: ["room_b"])
        room_b = SimpleNamespace(all_exit_options=lambda: ["room_a"])
        rooms = {"room_a": room_a, "room_b": room_b}

        routine = DockRoutine(route=[])
        routine._location = room_a
        routine._visited_this_stop = {"room_a"}
        ai_ship = self._make_ai_ship(role="patrol_officer")  # no ROLE_EXIT_PREFERENCE entry

        current_key = "room_a"
        for _ in range(MAX_LATERAL_HOPS + 5):
            choice = routine._choose_exit(ai_ship)
            if choice == "ship":
                break
            current_key = choice
            routine._location = rooms[current_key]
            routine._visited_this_stop.add(current_key)
        else:
            self.fail(f"never forced a reboard within {MAX_LATERAL_HOPS + 5} hops")
        self.assertLessEqual(len(routine._visited_this_stop), MAX_LATERAL_HOPS + 1)


class TestFreighterPilotDoesNotDetourIntoEmptyWilderness(unittest.TestCase):
    """Regression test: freighter_pilot's exit preference used to include
    "wilderness", so a freighter landing at the moon would visit city, then
    detour into wilderness (which has no NPC at all) just to stand at its
    entrance for a few seconds before reboarding. If the player happened to
    be looking at wilderness at that moment (having landed there themselves
    while the pilot was in city), the pilot appeared to glitch into
    existence at the entrance and vanish moments later. The real game's
    ROLE_EXIT_PREFERENCE must never route freighter_pilot into wilderness."""

    def test_elena_voss_visits_only_city_then_reboards(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        elena_ship = next(s for s in game_screen.ai_ships if s.person.name == "Elena Voss")
        routine = elena_ship.routine
        routine.route = [game_screen.moon]
        routine._route_index = 0
        routine._begin_walking_in(elena_ship)

        visited_wilderness = False
        frames = 0
        while routine.phase != "flying" and frames < 3000:
            if routine._location is not None and routine._location.interior_key == "wilderness":
                visited_wilderness = True
            routine.run(elena_ship)
            frames += 1

        self.assertEqual(routine.phase, "flying")
        self.assertFalse(visited_wilderness, "Freighter pilot should never detour into the empty wilderness")


class TestNormalizeRoom(unittest.TestCase):
    """normalize_room() folds every authored room shape (rect / polygon /
    circle) to a single {"polygon": [...], "label": ...} the rest of
    LocationScreen handles uniformly."""

    def test_rect_becomes_a_four_vertex_polygon(self):
        room = normalize_room({"rect": [10, 20, 100, 50], "label": "Bay"})
        self.assertEqual(room["label"], "Bay")
        self.assertEqual(room["polygon"], [(10, 20), (110, 20), (110, 70), (10, 70)])

    def test_polygon_is_kept_as_given(self):
        room = normalize_room({"polygon": [[0, 0], [10, 0], [5, 8]]})
        self.assertEqual(room["polygon"], [(0.0, 0.0), (10.0, 0.0), (5.0, 8.0)])

    def test_circle_becomes_a_regular_polygon(self):
        room = normalize_room({"shape": "circle", "center": [100, 100], "radius": 40, "sides": 6})
        self.assertEqual(len(room["polygon"]), 6)
        for x, y in room["polygon"]:
            self.assertAlmostEqual(math.hypot(x - 100, y - 100), 40, places=5)


class TestPointInPolygon(unittest.TestCase):
    def test_concave_notch_is_outside(self):
        # A C-shape: outer square 0..100 with a notch cut from the right side.
        poly = [(0, 0), (100, 0), (100, 40), (40, 40), (40, 60), (100, 60), (100, 100), (0, 100)]
        self.assertTrue(point_in_polygon(20, 50, poly))    # in the solid left bar
        self.assertFalse(point_in_polygon(70, 50, poly))   # in the notch
        self.assertTrue(point_in_polygon(70, 20, poly))    # above the notch, still solid

    def test_point_on_an_edge_counts_as_inside(self):
        poly = [(0, 0), (100, 0), (100, 100), (0, 100)]
        self.assertTrue(point_in_polygon(100, 50, poly))   # exactly on the right edge


class TestIndoorPathfinder(unittest.TestCase):
    """LocationScreen.plan_path() / IndoorPathfinder - the grid router that
    walks a visiting DockRoutine pilot across an interior's walkable area,
    around walls, concave notches, and building footprints. See
    TestDockRoutineRespectsWalls / TestDockRoutineRespectsBuildings for the
    full walking behavior this enables."""

    def _screen(self, rooms=None, structures=None, w=800, h=800):
        config = {"label": "Test", "culture": None}
        if rooms is not None:
            config["rooms"] = rooms
        if structures is not None:
            config["structures"] = structures
        screen = LocationScreen(config_data=config, world_width=w, world_height=h, story="default")
        if rooms is not None:
            screen.rooms = [normalize_room(r) for r in rooms]  # bypass culture-gated population
        return screen

    def _assert_walkable_path(self, screen, start, goal, path):
        self.assertEqual(path[-1], goal)
        prev = start
        for point in path:
            steps = max(1, int(math.hypot(point[0] - prev[0], point[1] - prev[1]) / 6))
            for i in range(steps + 1):
                t = i / steps
                x, y = prev[0] + (point[0] - prev[0]) * t, prev[1] + (point[1] - prev[1]) * t
                self.assertTrue(screen.can_move_to(x, y), f"Path leg {prev}->{point} leaves the walkable area at ({x:.0f},{y:.0f})")
            prev = point

    def test_same_area_returns_a_path_ending_at_goal(self):
        screen = self._screen(rooms=[{"rect": [0, 0, 400, 400]}])
        path = screen.plan_path((30, 30), (350, 350))
        self._assert_walkable_path(screen, (30, 30), (350, 350), path)

    def test_routes_around_a_concave_notch(self):
        # C-shaped area: a straight line from (60,60) to (60,540) is fine,
        # but (60,300)->(540,300) would cut straight through the notch.
        rooms = [
            {"rect": [40, 40, 60, 520]},    # left bar
            {"rect": [40, 40, 500, 60]},    # top bar
            {"rect": [40, 500, 500, 60]},   # bottom bar
        ]
        screen = self._screen(rooms=rooms, w=600, h=600)
        start, goal = (70, 300), (520, 520)
        path = screen.plan_path(start, goal)
        self._assert_walkable_path(screen, start, goal, path)

    def test_unreachable_goal_falls_back_to_the_direct_goal(self):
        screen = self._screen(rooms=[{"rect": [0, 0, 200, 200]}])
        self.assertEqual(screen.plan_path((10, 10), (5000, 5000)), [(5000, 5000)])

    def test_routes_around_a_building_footprint_with_no_rooms(self):
        # A moon interior: structures but no rooms. Start due north of the
        # bunker, goal due south - the direct line is straight through it.
        screen = self._screen(structures=[{"x": 500, "y": 500, "building_type": "drossholt_bunker"}], w=1600, h=1600)
        start, goal = (570, 400), (570, 700)
        path = screen.plan_path(start, goal)
        self._assert_walkable_path(screen, start, goal, path)


class TestDockRoutineRespectsWalls(unittest.TestCase):
    """Regression test: DockRoutine._step_toward() moved a visiting pilot
    in a dead-straight line toward their destination with no collision
    checking at all, unlike the player's own movement - reproducibly
    visible with Kepler's Reach's real station config (confirmed by
    simulating the old unconstrained formula: the pilot spent real frames
    outside every valid room on the way to the bartender). Fixed by giving
    _step_toward the same LocationScreen.can_move_to() wall-sliding check
    the player's movement already uses."""

    def _make_l_shaped_screen(self):
        """Two rooms forming an L: a straight line from the entrance to
        the NPC crosses empty space outside both, but a route that goes
        down the vertical corridor then across the horizontal one stays
        inside the union the whole way - exactly what wall-sliding should
        produce and straight-line movement can't."""
        config = {
            "label": "L-Shaped Test Room", "culture": None,
            "rooms": [
                {"label": "Vertical", "rect": [50, 50, 100, 500]},
                {"label": "Horizontal", "rect": [50, 450, 500, 100]},
            ],
            "npcs": [{"name": "Target", "x": 500, "y": 500, "role": "resident"}],
        }
        screen = LocationScreen(config_data=config, world_width=600, world_height=600)
        screen.rooms = [normalize_room(r) for r in config["rooms"]]  # bypass culture-gated room population, see other tests
        screen.entrance_x, screen.entrance_y = 100, 100
        return screen

    def test_pilot_never_leaves_the_walkable_area_walking_an_l_shaped_room(self):
        location = self._make_l_shaped_screen()
        ai_ship = SimpleNamespace(pilot_person=Person(100, 100))
        routine = DockRoutine(route=[])
        routine._location = location
        routine._set_waypoints(ai_ship.pilot_person, (500, 500))  # the NPC, in the far corner of the L

        frames = 0
        while frames < 2000:
            if routine._step_toward(ai_ship.pilot_person):
                break
            self.assertTrue(
                location.can_move_to(ai_ship.pilot_person.x, ai_ship.pilot_person.y),
                f"Pilot left the walkable area at ({ai_ship.pilot_person.x}, {ai_ship.pilot_person.y})",
            )
            frames += 1
        else:
            self.fail("Pilot never arrived within 2000 frames")


class TestBuildingFootprintCollision(unittest.TestCase):
    """Regression test for the backlog's "Building collision missing"
    bug: player/NPCs used to be able to walk straight through a building's
    drawn silhouette, since can_move_to() only ever checked room walls or
    the open-world bounds. Uses a real building_type from the default
    story's building_types.json (drossholt_bunker: 140x90, anchored
    top-left, so its footprint - see LocationScreen._building_footprint -
    sits at world x:500-640, y:545-635) rather than a synthetic one, so
    this breaks if that config's shape/footprint fields are renamed."""

    def _make_screen_with_bunker(self):
        config = {
            "label": "Test Yard",
            "structures": [{"x": 500, "y": 500, "building_type": "drossholt_bunker"}],
        }
        return LocationScreen(config_data=config, world_width=1600, world_height=1600, story="default")

    def test_footprint_is_computed_from_the_building_type(self):
        location = self._make_screen_with_bunker()
        self.assertEqual(location.building_footprints, [(500.0, 545.0, 140, 90)])

    def test_cannot_walk_into_the_footprint(self):
        location = self._make_screen_with_bunker()
        self.assertFalse(location.can_move_to(570, 590))  # dead center of the bunker

    def test_can_walk_around_the_sides(self):
        location = self._make_screen_with_bunker()
        self.assertTrue(location.can_move_to(480, 590))  # just left of the footprint
        self.assertTrue(location.can_move_to(660, 590))  # just right of the footprint

    def test_can_walk_behind_it(self):
        """North of the building (smaller y) is open ground once past the
        footprint's near edge - this is what lets a character walk behind
        the building and be drawn behind it (see draw()'s y-sort), instead
        of the whole tall silhouette being solid all the way through."""
        location = self._make_screen_with_bunker()
        self.assertTrue(location.can_move_to(570, 400))

    def test_decorative_structures_with_no_building_type_have_no_footprint(self):
        config = {
            "label": "Test Wilderness",
            "structures": [{"type": "circle", "x": 500, "y": 500, "radius": 50}],
        }
        location = LocationScreen(config_data=config, world_width=1600, world_height=1600, story="default")
        self.assertEqual(location.building_footprints, [])
        self.assertTrue(location.can_move_to(500, 500))


class TestDockRoutineRespectsBuildings(unittest.TestCase):
    """Regression test for the same stuck failure mode
    TestDockRoutineRespectsWalls covers for room walls, but triggered by a
    building instead: a moon's city/wilderness interior has structures (see
    LocationScreen.building_footprints) but no rooms at all, so the room
    graph IndoorPathfinder builds never learns about them on its own -
    without also routing around obstacles, a pilot walking straight at an
    NPC on the far side of a building got stuck exactly like Elena Voss used
    to (worst case here: the NPC is directly north/south of the pilot, so
    the wall-slide fallback's axis-only candidates are pure no-ops and never
    move the pilot at all). Uses the real drossholt_bunker building_type
    (see TestBuildingFootprintCollision), not a synthetic one."""

    def _make_screen_with_bunker(self, target_x, target_y):
        config = {
            "label": "Test Yard",
            "structures": [{"x": 500, "y": 500, "building_type": "drossholt_bunker"}],
            "npcs": [{"name": "Target", "x": target_x, "y": target_y, "role": "resident"}],
        }
        return LocationScreen(config_data=config, world_width=1600, world_height=1600, story="default")

    def test_pilot_routes_around_the_building_instead_of_getting_stuck(self):
        # Bunker footprint is x:500-640, y:545-635 (see
        # TestBuildingFootprintCollision) - start directly north of it,
        # target directly south, so dx is 0 for the entire direct line.
        target_x, target_y = 570, 700
        location = self._make_screen_with_bunker(target_x, target_y)
        person = Person(570, 400)
        routine = DockRoutine(route=[])
        routine._location = location
        routine._set_waypoints(person, (target_x, target_y))

        frames = 0
        while frames < 2000:
            if routine._step_toward(person):
                break
            self.assertTrue(
                location.can_move_to(person.x, person.y),
                f"Pilot walked into the building (or left the world) at ({person.x}, {person.y})",
            )
            frames += 1
        else:
            self.fail("Pilot never arrived within 2000 frames")
        # _step_toward's ARRIVAL_DISTANCE (10) means arrival can land up to
        # that far from the exact target, not pixel-perfect on it.
        self.assertLessEqual(math.hypot(person.x - target_x, person.y - target_y), 10)


class TestWanderRoutineRespectsWalls(unittest.TestCase):
    """WanderRoutine used to move a wandering NPC (resident/roommate/
    traveler role) with zero collision checking at all, unlike DockRoutine's
    visiting pilots - it could wander through a wall or a building. Fixed by
    giving it the same LocationScreen.can_move_to() check (via
    Character.can_move_to, injected by LocationScreen._build_local_character
    - see game/world/character.py), wall-sliding the same way DockRoutine's
    _step_toward does."""

    def test_never_leaves_the_walkable_area_over_many_wander_cycles(self):
        # A single small room - WANDER_RADIUS (40) reaches well past every
        # wall from the center, so without wall-awareness the wanderer would
        # cross one almost immediately.
        config = {
            "label": "Tiny Room", "culture": None,
            "rooms": [{"label": "Room", "rect": [100, 100, 60, 60]}],
        }
        location = LocationScreen(config_data=config, world_width=300, world_height=300)
        location.rooms = [normalize_room(r) for r in config["rooms"]]
        person = Person(130, 130)
        character = Character(person, role="resident", can_move_to=location.can_move_to)

        for _ in range(2000):
            character.routine.run(character)
            self.assertTrue(
                location.can_move_to(person.x, person.y),
                f"Wanderer left the walkable area at ({person.x}, {person.y})",
            )

    def test_never_enters_a_building_footprint(self):
        config = {
            "label": "Test Yard",
            "structures": [{"x": 500, "y": 500, "building_type": "drossholt_bunker"}],
        }
        location = LocationScreen(config_data=config, world_width=1600, world_height=1600, story="default")
        # Right against the bunker's near (north) edge, well within
        # WANDER_RADIUS of stepping into it.
        person = Person(570, 540)
        character = Character(person, role="resident", can_move_to=location.can_move_to)

        for _ in range(2000):
            character.routine.run(character)
            self.assertTrue(location.can_move_to(person.x, person.y))


class TestPersonStepToward(unittest.TestCase):
    """Person.step_toward - the one on-foot movement primitive shared by the
    player (LocationScreen._handle_movement), WanderRoutine, and DockRoutine."""

    def test_moves_a_full_step_toward_a_far_target(self):
        p = Person(0.0, 0.0)
        moved = p.step_toward(100.0, 0.0, 3.0, lambda x, y: True)
        self.assertTrue(moved)
        self.assertAlmostEqual(p.x, 3.0)
        self.assertAlmostEqual(p.y, 0.0)

    def test_diagonal_step_is_normalized_not_faster(self):
        p = Person(0.0, 0.0)
        p.step_toward(100.0, 100.0, 5.0, lambda x, y: True)
        self.assertAlmostEqual(math.hypot(p.x, p.y), 5.0)  # not 5*sqrt(2)

    def test_never_overshoots_a_near_target(self):
        p = Person(0.0, 0.0)
        p.step_toward(2.0, 0.0, 10.0, lambda x, y: True)
        self.assertAlmostEqual(p.x, 2.0)  # capped at the distance to the target

    def test_wall_slides_along_a_blocked_axis(self):
        p = Person(0.0, 0.0)
        # can't increase x past 0, but y is free - a step aimed up-right
        # should slide straight up instead of stopping.
        moved = p.step_toward(10.0, 10.0, 4.0, lambda x, y: x <= 0.0001)
        self.assertTrue(moved)
        self.assertAlmostEqual(p.x, 0.0)
        self.assertGreater(p.y, 0.0)

    def test_returns_false_and_does_not_move_when_fully_boxed_in(self):
        p = Person(5.0, 5.0)
        moved = p.step_toward(10.0, 10.0, 3.0, lambda x, y: False)
        self.assertFalse(moved)
        self.assertEqual((p.x, p.y), (5.0, 5.0))


class TestPossessions(unittest.TestCase):
    """Test Possessions - credits/ships/loans, composed onto every Person
    (see game/world/person.py), not just the player."""

    def test_starts_empty(self):
        possessions = Possessions()
        self.assertEqual(possessions.credits, 0)
        self.assertEqual(possessions.owned_ships, [])
        self.assertEqual(possessions.loans, [])

    def test_can_afford_and_spend(self):
        possessions = Possessions(credits=1200)
        self.assertTrue(possessions.can_afford(1200))
        self.assertFalse(possessions.can_afford(1201))
        possessions.spend(1200)
        self.assertEqual(possessions.credits, 0)
        possessions.earn(500)
        self.assertEqual(possessions.credits, 500)

    def test_add_ship(self):
        possessions = Possessions()
        possessions.add_ship("shuttle")
        self.assertEqual(possessions.owned_ships, ["shuttle"])

    def test_take_loan_adds_credits_and_records_loan(self):
        possessions = Possessions()
        possessions.take_loan("Station Credit Union", 1200)
        self.assertEqual(possessions.credits, 1200)
        self.assertEqual(possessions.loans, [{"lender": "Station Credit Union", "principal": 1200}])

    def test_get_state_roundtrips_through_from_state(self):
        possessions = Possessions(credits=300, owned_ships=["shuttle"], loans=[{"lender": "X", "principal": 100}])
        restored = Possessions.from_state(possessions.get_state())
        self.assertEqual(restored.credits, 300)
        self.assertEqual(restored.owned_ships, ["shuttle"])
        self.assertEqual(restored.loans, [{"lender": "X", "principal": 100}])

    def test_restore_from_mutates_in_place(self):
        """restore_from() must update the existing object, not replace it -
        every screen holding a reference to the player's one Possessions
        (see SpaceScreen.get_interior_screen) depends on that identity
        staying the same across a load."""
        possessions = Possessions(credits=50)
        same_object = possessions
        possessions.restore_from({"credits": 900, "owned_ships": ["patrol"], "loans": []})
        self.assertIs(possessions, same_object)
        self.assertEqual(possessions.credits, 900)
        self.assertEqual(possessions.owned_ships, ["patrol"])


class TestPossessionsFlags(unittest.TestCase):
    """flags (story-progress markers - see Dialogue's requires_flag/
    conditional_roots and the "set_flag:" dialogue action) round-trips
    through get_state()/restore_from()/from_state() like every other
    Possessions field - see docs/SAVE_SYSTEM.md."""

    def test_flags_round_trip_through_get_state_and_restore_from(self):
        possessions = Possessions()
        possessions.flags["hailed_kade"] = True
        state = possessions.get_state()
        self.assertEqual(state["flags"], {"hailed_kade": True})

        restored = Possessions()
        restored.restore_from(state)
        self.assertEqual(restored.flags, {"hailed_kade": True})

    def test_from_state_defaults_to_empty_flags_for_a_pre_existing_save(self):
        """A save made before this feature existed has no "flags" key at
        all - from_state()/restore_from() must default to {} rather than
        raising."""
        possessions = Possessions.from_state({"credits": 10})
        self.assertEqual(possessions.flags, {})


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


class TestPossessionsMessageLog(unittest.TestCase):
    """message_log (the Space View's bottom-left Messages pane's history -
    see ui_theme.draw_message_log and SpaceScreen._check_one_way_hails) -
    add_message()'s newest-first/capped behavior, and the usual save
    round-trip."""

    def test_add_message_inserts_newest_first(self):
        possessions = Possessions()
        possessions.add_message("Kade Marsh", "Identify yourself.")
        possessions.add_message("Elena Voss", "Hello there.")
        self.assertEqual(possessions.message_log[0], {"sender": "Elena Voss", "text": "Hello there."})
        self.assertEqual(possessions.message_log[1], {"sender": "Kade Marsh", "text": "Identify yourself."})

    def test_add_message_caps_the_log_length(self):
        possessions = Possessions()
        for i in range(30):
            possessions.add_message("Someone", f"message {i}")
        self.assertEqual(len(possessions.message_log), 20)
        self.assertEqual(possessions.message_log[0]["text"], "message 29")  # newest kept

    def test_message_log_round_trips_through_get_state_and_restore_from(self):
        possessions = Possessions()
        possessions.add_message("Kade Marsh", "Identify yourself.")
        state = possessions.get_state()
        self.assertEqual(state["message_log"], [{"sender": "Kade Marsh", "text": "Identify yourself."}])

        restored = Possessions()
        restored.restore_from(state)
        self.assertEqual(restored.message_log, [{"sender": "Kade Marsh", "text": "Identify yourself."}])

    def test_from_state_defaults_to_no_messages_for_a_pre_existing_save(self):
        possessions = Possessions.from_state({"credits": 10})
        self.assertEqual(possessions.message_log, [])


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

    def test_escape_and_n_both_close(self):
        menu = ReportMenu(*mission_report({}, Possessions()))
        for key in (pygame_mock.K_ESCAPE, pygame_mock.K_n):
            event = SimpleNamespace(type=pygame_mock.KEYDOWN, key=key)
            self.assertEqual(menu.handle_input([event]), "close")


class TestMenuDialogClassification(unittest.TestCase):
    """The menu-vs-dialog split (see game/ui/menu_base.py): both hide the
    Controls pane and drive their actions with buttons; a dialog additionally
    closes on any pick."""

    def test_is_dialog_flags(self):
        self.assertFalse(ReportMenu("x", [[]]).is_dialog)
        self.assertFalse(BackdropMenu("x", [("a", "A", None)]).is_dialog)
        self.assertTrue(ChoiceDialog("x", [("a", "A", None)]).is_dialog)
        self.assertTrue(ConfirmDialog("x", "y").is_dialog)

    def test_no_modal_renders_a_controls_pane(self):
        # help_items() was the Controls-pane hook - it's gone from every modal.
        for modal in (ReportMenu("x", [[]]), BackdropMenu("x", [("a", "A", None)]),
                      ChoiceDialog("x", [("a", "A", None)]), ConfirmDialog("x", "y")):
            self.assertFalse(hasattr(modal, "help_items"))

    def test_every_modal_exposes_buttons(self):
        self.assertTrue(ReportMenu("x", [[]]).buttons())
        self.assertTrue(BackdropMenu("x", [("a", "A", None)]).buttons())
        self.assertTrue(ChoiceDialog("x", [("a", "A", None)]).buttons())
        self.assertTrue(ConfirmDialog("x", "y").buttons())


class TestChoiceDialog(unittest.TestCase):
    """ChoiceDialog (was LocationSelector + ExitMenu): pick a key, or cancel;
    a disabled option can't be committed."""

    def _key(self, key):
        return SimpleNamespace(type=pygame_mock.KEYDOWN, key=key)

    def test_enter_returns_the_focused_key(self):
        dialog = ChoiceDialog("Where To?", [("bar", "Bar", None), ("dorm", "Dormitory", None)])
        self.assertEqual(dialog.handle_input([self._key(pygame_mock.K_RETURN)]), "bar")
        dialog.handle_input([self._key(pygame_mock.K_DOWN)])
        self.assertEqual(dialog.handle_input([self._key(pygame_mock.K_RETURN)]), "dorm")

    def test_escape_cancels(self):
        dialog = ChoiceDialog("Where To?", [("bar", "Bar", None)])
        self.assertEqual(dialog.handle_input([self._key(pygame_mock.K_ESCAPE)]), "cancel")

    def test_focus_never_lands_on_a_disabled_option(self):
        dialog = ChoiceDialog("Where To?", [("ship", "Return to Ship", "no ship owned"), ("bar", "Bar", None)])
        # Starts off the disabled first entry...
        self.assertEqual(dialog.handle_input([self._key(pygame_mock.K_RETURN)]), "bar")
        # ...and navigation skips over it rather than stopping on it.
        for _ in range(3):
            dialog.handle_input([self._key(pygame_mock.K_UP)])
            self.assertEqual(dialog.handle_input([self._key(pygame_mock.K_RETURN)]), "bar")


class TestBackdropMenu(unittest.TestCase):
    """BackdropMenu (was Menu + StorySelector): Enter returns the focused
    row's value; ESC only cancels when the menu allows it."""

    def _key(self, key):
        return SimpleNamespace(type=pygame_mock.KEYDOWN, key=key)

    def test_enter_returns_row_value(self):
        menu = BackdropMenu("MAIN", [("new", "NEW", None), ("quit", "QUIT", None)])
        self.assertEqual(menu.handle_input([self._key(pygame_mock.K_RETURN)]), "new")
        menu.handle_input([self._key(pygame_mock.K_DOWN)])
        self.assertEqual(menu.handle_input([self._key(pygame_mock.K_RETURN)]), "quit")

    def test_escape_only_cancels_when_allowed(self):
        no_cancel = BackdropMenu("MAIN", [("new", "NEW", None)])
        self.assertIsNone(no_cancel.handle_input([self._key(pygame_mock.K_ESCAPE)]))
        cancelable = BackdropMenu("STORY", [("a", "A", None)], allow_cancel=True)
        self.assertEqual(cancelable.handle_input([self._key(pygame_mock.K_ESCAPE)]), "cancel")


class TestPossessionsInventory(unittest.TestCase):
    """Test Possessions' cargo/items/outfit tracking - added alongside the
    inventory/buying-selling/outfitting feature. Cargo capacity itself lives
    on Ship, not here (Possessions stays config-free per the story/save
    split), so these tests only cover the plain-data bookkeeping."""

    def test_cargo_add_and_remove(self):
        possessions = Possessions()
        possessions.add_cargo("ore", 5)
        possessions.add_cargo("ore", 3)
        self.assertEqual(possessions.cargo["ore"], 8)
        self.assertEqual(possessions.cargo_quantity_total(), 8)
        possessions.remove_cargo("ore", 3)
        self.assertEqual(possessions.cargo["ore"], 5)

    def test_remove_cargo_down_to_zero_drops_the_key(self):
        possessions = Possessions()
        possessions.add_cargo("ore", 5)
        possessions.remove_cargo("ore", 5)
        self.assertNotIn("ore", possessions.cargo)

    def test_items_are_independent_of_cargo(self):
        possessions = Possessions()
        possessions.add_item("repair_kit", 1)
        possessions.add_cargo("ore", 5)
        self.assertEqual(possessions.items, {"repair_kit": 1})
        self.assertEqual(possessions.cargo, {"ore": 5})

    def test_add_outfit_and_install(self):
        possessions = Possessions()
        possessions.add_outfit("laser_cannon")
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])
        possessions.install_outfit("weapon_1", "laser_cannon")
        self.assertEqual(possessions.owned_outfits, [])
        self.assertEqual(possessions.installed_outfits, {"weapon_1": "laser_cannon"})

    def test_installing_into_an_occupied_slot_bumps_the_old_outfit_back_to_owned(self):
        possessions = Possessions(owned_outfits=["laser_cannon", "afterburner"])
        possessions.install_outfit("weapon_1", "laser_cannon")
        bumped = possessions.install_outfit("weapon_1", "afterburner")
        self.assertEqual(bumped, "laser_cannon")
        self.assertEqual(possessions.installed_outfits, {"weapon_1": "afterburner"})
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])

    def test_uninstall_outfit_returns_it_to_owned(self):
        possessions = Possessions(installed_outfits={"weapon_1": "laser_cannon"})
        removed = possessions.uninstall_outfit("weapon_1")
        self.assertEqual(removed, "laser_cannon")
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])

    def test_uninstall_empty_slot_is_a_noop(self):
        possessions = Possessions()
        self.assertIsNone(possessions.uninstall_outfit("weapon_1"))
        self.assertEqual(possessions.owned_outfits, [])

    def test_uninstall_all_outfits_moves_everything_back_to_owned(self):
        possessions = Possessions(
            owned_outfits=["reinforced_hull"],
            installed_outfits={"weapon_1": "laser_cannon", "utility_1": "cargo_expansion"},
        )
        possessions.uninstall_all_outfits()
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(sorted(possessions.owned_outfits), ["cargo_expansion", "laser_cannon", "reinforced_hull"])

    def test_uninstall_all_outfits_is_a_noop_with_nothing_installed(self):
        possessions = Possessions(owned_outfits=["laser_cannon"])
        possessions.uninstall_all_outfits()
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])

    def test_inventory_fields_roundtrip_through_save_state(self):
        possessions = Possessions(
            owned_outfits=["afterburner"],
            installed_outfits={"weapon_1": "laser_cannon"},
            cargo={"ore": 5},
            items={"repair_kit": 1},
        )
        restored = Possessions.from_state(possessions.get_state())
        self.assertEqual(restored.owned_outfits, ["afterburner"])
        self.assertEqual(restored.installed_outfits, {"weapon_1": "laser_cannon"})
        self.assertEqual(restored.cargo, {"ore": 5})
        self.assertEqual(restored.items, {"repair_kit": 1})

    def test_restore_from_defaults_missing_inventory_keys_for_old_saves(self):
        """A save made before this feature existed has no cargo/items/outfit
        keys at all - restoring it must not error, and should leave a
        freshly-constructed Possessions' empty defaults in place."""
        possessions = Possessions()
        possessions.restore_from({"credits": 500, "owned_ships": ["shuttle"], "loans": []})
        self.assertEqual(possessions.cargo, {})
        self.assertEqual(possessions.items, {})
        self.assertEqual(possessions.owned_outfits, [])
        self.assertEqual(possessions.installed_outfits, {})


class TestShipOutfits(unittest.TestCase):
    """Test Ship.apply_outfits() - stat modifiers stack additively on top of
    apply_ship_type()'s base stats, and never zero out a stat an outfit
    doesn't mention (same contract apply_ship_type itself documents)."""

    def test_apply_outfits_with_no_outfits_leaves_base_stats_unchanged(self):
        ship = Ship(0, 0)
        ship.apply_ship_type({"max_thrust": 0.1, "max_velocity": 2.0, "rotation_speed": 4})
        ship.apply_outfits([])
        self.assertEqual(ship.acceleration_magnitude, 0.1)
        self.assertEqual(ship.max_velocity, 2.0)
        self.assertEqual(ship.rotation_speed, 4)

    def test_single_outfit_modifier_stacks_onto_base_stat(self):
        ship = Ship(0, 0)
        ship.apply_ship_type({"max_thrust": 0.1, "max_velocity": 2.0, "rotation_speed": 4})
        ship.apply_outfits([{"stat_modifiers": {"max_velocity": 1.5}}])
        self.assertAlmostEqual(ship.max_velocity, 3.5)
        self.assertEqual(ship.acceleration_magnitude, 0.1)  # unmentioned stat untouched

    def test_multiple_outfits_stack_together(self):
        ship = Ship(0, 0)
        ship.apply_ship_type({"max_thrust": 0.1, "max_velocity": 2.0, "rotation_speed": 4})
        ship.apply_outfits([
            {"stat_modifiers": {"max_velocity": 1.5, "max_thrust": 0.05}},
            {"stat_modifiers": {"rotation_speed": -1}},
        ])
        self.assertAlmostEqual(ship.max_velocity, 3.5)
        self.assertAlmostEqual(ship.acceleration_magnitude, 0.15)
        self.assertEqual(ship.rotation_speed, 3)

    def test_cargo_capacity_set_by_ship_type_and_boosted_by_outfits(self):
        ship = Ship(0, 0)
        ship.apply_ship_type({"cargo_capacity": 10})
        ship.apply_outfits([{"stat_modifiers": {"cargo_capacity": 20}}])
        self.assertEqual(ship.cargo_capacity, 30)

    def test_stacked_negative_modifiers_are_clamped_to_a_safe_floor_not_zero(self):
        """Regression test: the freighter's base rotation_speed (1) plus a
        Cargo Expansion Module's -1 rotation modifier landed on exactly 0 -
        a ship that could never turn at all. Same floor applies to thrust/
        velocity/cargo so no stat can go to zero or negative from stacking."""
        ship = Ship(0, 0)
        ship.apply_ship_type({"max_thrust": 0.1, "max_velocity": 2.0, "rotation_speed": 1, "cargo_capacity": 80})
        ship.apply_outfits([{"stat_modifiers": {"rotation_speed": -1, "max_velocity": -3, "max_thrust": -1, "cargo_capacity": -100}}])
        self.assertGreater(ship.rotation_speed, 0)
        self.assertGreater(ship.max_velocity, 0)
        self.assertGreater(ship.acceleration_magnitude, 0)
        self.assertEqual(ship.cargo_capacity, 0)  # cargo has no "must always move a bit" floor, just can't go negative


class TestShopMenu(unittest.TestCase):
    """Test ShopMenu's buy/sell logic against the real "default" story's
    commodities.json/items.json (ore costs 12cr, repair_kit costs 150cr) -
    same convention as other config-dependent tests that pin to real story
    data rather than reimplementing get_commodity()/get_item() with a fake.
    Only the transaction/navigation logic is tested here, not draw() - see
    CLAUDE.md's "don't test UI rendering" and the fact that no other full
    menu class (ReportMenu, ConfirmDialog, ChoiceDialog) has a draw() test
    either."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_buying_a_commodity_spends_credits_and_adds_cargo(self):
        possessions = Possessions(credits=100)
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        shop._transact("ore")
        self.assertEqual(possessions.credits, 88)
        self.assertEqual(possessions.cargo, {"ore": 1})

    def test_buying_without_enough_credits_is_a_noop(self):
        possessions = Possessions(credits=5)
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        shop._transact("ore")
        self.assertEqual(possessions.credits, 5)
        self.assertEqual(possessions.cargo, {})

    def test_buying_a_commodity_at_full_cargo_capacity_is_a_noop(self):
        possessions = Possessions(credits=100, cargo={"ore": 10})
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        shop._transact("ore")
        self.assertEqual(possessions.credits, 100)  # unchanged - purchase blocked
        self.assertEqual(possessions.cargo, {"ore": 10})

    def test_selling_a_commodity_earns_credits_at_the_sell_multiplier(self):
        possessions = Possessions(credits=0, cargo={"ore": 3})
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"], "sell_multiplier": 0.5}, cargo_capacity=10)
        shop.mode = "sell"
        shop._transact("ore")
        self.assertEqual(possessions.credits, 6)  # 12cr base_price * 0.5
        self.assertEqual(possessions.cargo, {"ore": 2})

    def test_items_are_not_capacity_limited(self):
        possessions = Possessions(credits=200)
        shop = ShopMenu(possessions, "default", {"type": "items", "stock": ["repair_kit"]}, cargo_capacity=0)
        shop._transact("repair_kit")
        self.assertEqual(possessions.credits, 50)
        self.assertEqual(possessions.items, {"repair_kit": 1})

    def test_tab_toggles_buy_sell_mode(self):
        possessions = Possessions()
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]})
        self.assertEqual(shop.mode, "buy")
        import pygame as mocked_pygame
        shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_TAB)])
        self.assertEqual(shop.mode, "sell")
        shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_TAB)])
        self.assertEqual(shop.mode, "buy")

    def test_left_right_browse_the_grid_without_changing_mode(self):
        """Left/Right/Up/Down navigate the icon grid now (see IconGrid) -
        they used to toggle Buy/Sell, which Tab does instead."""
        possessions = Possessions()
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore", "medicine", "fuel_cells"]})
        import pygame as mocked_pygame
        shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RIGHT)])
        self.assertEqual(shop.mode, "buy")
        self.assertEqual(shop.buy_list.current(), "medicine")

    def test_escape_closes(self):
        import pygame as mocked_pygame
        shop = ShopMenu(Possessions(), "default", {"type": "commodities", "stock": ["ore"]})
        result = shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_ESCAPE)])
        self.assertEqual(result, "close")

    def test_empty_stock_shop_can_still_sell_owned_cargo_at_a_premium(self):
        """A shop with an empty "stock" (e.g. sol_alpha.json's Ilsa Farrow,
        who only buys - see docs/BACKLOG.md-adjacent trade-loop design) has
        nothing on the Buy tab, but the Sell tab isn't driven by "stock" at
        all - it always lists whatever's in possessions.cargo, so a
        buy-nothing/sell-only shop still works and can price above the
        commodity's own base_price to make a return trip profitable."""
        possessions = Possessions(credits=0, cargo={"ore": 2})
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": [], "sell_multiplier": 1.2})
        self.assertIsNone(shop.buy_list.current())  # nothing to buy
        shop.mode = "sell"
        self.assertEqual(shop.sell_list.items, ["ore"])
        shop._transact("ore")
        self.assertEqual(possessions.credits, 14)  # 12cr base_price * 1.2, truncated
        self.assertEqual(possessions.cargo, {"ore": 1})

    def test_enter_transacts_the_selected_item(self):
        import pygame as mocked_pygame
        possessions = Possessions(credits=100)
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertEqual(possessions.cargo, {"ore": 1})


class TestShipBrowserMenu(unittest.TestCase):
    """Test ShipBrowserMenu against the real "default" story's ship_types.json
    (shuttle costs 1200cr) - the on_buy callback is the injection point that
    lets this menu perform the same mutation as LocationScreen.buy_ship()
    without owning Possessions/on_ship_purchased itself."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_enter_opens_a_confirm_dialog_instead_of_buying_immediately(self):
        import pygame as mocked_pygame
        bought = []
        possessions = Possessions(credits=1200)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle"]}, on_buy=bought.append)
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertIsNotNone(menu.confirm)
        self.assertEqual(bought, [])  # not yet - still waiting on confirmation
        self.assertEqual(possessions.credits, 1200)

    def test_confirming_calls_on_buy_with_the_selected_ship_type(self):
        import pygame as mocked_pygame
        bought = []
        possessions = Possessions(credits=1200)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle"]}, on_buy=bought.append)
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_y)])
        self.assertEqual(bought, ["shuttle"])
        self.assertIsNone(menu.confirm)

    def test_cannot_afford_blocks_enter_from_opening_confirm(self):
        import pygame as mocked_pygame
        bought = []
        possessions = Possessions(credits=0)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle"]}, on_buy=bought.append)
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertIsNone(menu.confirm)
        self.assertEqual(bought, [])

    def test_escape_closes(self):
        import pygame as mocked_pygame
        menu = ShipBrowserMenu(Possessions(), "default", {"stock": ["shuttle"]}, on_buy=lambda x: None)
        result = menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_ESCAPE)])
        self.assertEqual(result, "close")

    def test_navigation_does_not_skip_unaffordable_ships(self):
        """Regression test: the preview used to be tied to a cursor that
        skipped over unaffordable ships whenever at least one WAS
        affordable, so you couldn't preview (or even see) a ship you
        couldn't yet buy. shuttle costs 1200cr, freighter costs 4500cr -
        affording the shuttle only must not block navigating onto/
        previewing the freighter."""
        import pygame as mocked_pygame
        possessions = Possessions(credits=1200)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle", "freighter"]}, on_buy=lambda x: None)
        self.assertEqual(menu.grid.current(), "shuttle")
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_DOWN)])
        self.assertEqual(menu.grid.current(), "freighter")


class TestApproximateSizeLabel(unittest.TestCase):
    """Test the Shipyard preview's "Approximate Size" bucketing - a plain
    world-units number (graphics.json's "size") means little to a player,
    so it's shown as a coarse label instead."""

    def test_small_ship(self):
        self.assertEqual(_approximate_size_label({"size": 10}), "Small")  # shuttle

    def test_medium_ship_at_the_small_boundary(self):
        self.assertEqual(_approximate_size_label({"size": 15}), "Medium")

    def test_large_ship(self):
        self.assertEqual(_approximate_size_label({"size": 35}), "Large")  # freighter

    def test_massive_ship_above_every_threshold(self):
        self.assertEqual(_approximate_size_label({"size": 100}), "Massive")

    def test_missing_size_falls_back_to_the_default_of_15(self):
        self.assertEqual(_approximate_size_label({}), "Medium")


class TestIconGrid(unittest.TestCase):
    """Test IconGrid's row-major navigation - the grid layout ShopMenu uses
    for its buy/sell lists (see docs/BACKLOG.md's icon-grid item)."""

    def test_right_and_left_wrap_across_row_boundaries(self):
        grid = IconGrid(["a", "b", "c", "d"], columns=2, max_rows=2)
        grid.selected = 1  # "b", end of row 0
        grid.handle_key(pygame_mock.K_RIGHT)
        self.assertEqual(grid.current(), "c")  # wraps onto row 1
        grid.handle_key(pygame_mock.K_LEFT)
        self.assertEqual(grid.current(), "b")

    def test_left_from_first_item_wraps_to_last(self):
        grid = IconGrid(["a", "b", "c"], columns=2, max_rows=2)
        grid.selected = 0
        grid.handle_key(pygame_mock.K_LEFT)
        self.assertEqual(grid.current(), "c")

    def test_down_jumps_a_full_row_and_clamps_on_a_ragged_last_row(self):
        grid = IconGrid(["a", "b", "c"], columns=2, max_rows=2)  # row 1 has only "c"
        grid.selected = 1  # "b"
        grid.handle_key(pygame_mock.K_DOWN)
        self.assertEqual(grid.current(), "c")  # clamped, not wrapped past the end

    def test_up_from_top_row_clamps_to_first_row(self):
        grid = IconGrid(["a", "b", "c", "d"], columns=2, max_rows=2)
        grid.selected = 1  # "b", already top row
        grid.handle_key(pygame_mock.K_UP)
        self.assertEqual(grid.current(), "b")  # candidate index negative - clamps in place

    def test_current_returns_none_when_empty(self):
        grid = IconGrid([], columns=3, max_rows=2)
        self.assertIsNone(grid.current())
        grid.handle_key(pygame_mock.K_RIGHT)  # must not raise


class TestOutfittingMenu(unittest.TestCase):
    """Test OutfittingMenu's keyboard-driven equip/unequip and slot/type
    filtering against the real "default" story's patrol ship type (slots:
    weapon_1/weapon, utility_1/utility) and ship_outfits.json (laser_cannon/
    weapon, afterburner/engine, cargo_expansion/utility). Mouse drag-and-
    drop itself isn't tested here - see CLAUDE.md's "don't test UI
    rendering" and the plan's note that the underlying Possessions.
    install_outfit/uninstall_outfit swap logic is already covered by
    TestPossessionsInventory; this class only covers the menu's own
    slot-focus/filtering/callback logic."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_compatible_owned_outfits_filters_by_slot_type(self):
        possessions = Possessions(owned_outfits=["laser_cannon", "afterburner"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        self.assertEqual(menu._compatible_owned_outfits("weapon"), ["laser_cannon"])
        self.assertEqual(menu._compatible_owned_outfits("engine"), ["afterburner"])
        self.assertEqual(menu._compatible_owned_outfits("shield"), [])

    def test_enter_on_empty_slot_opens_picker_filtered_to_compatible_outfits(self):
        import pygame as mocked_pygame
        possessions = Possessions(owned_outfits=["laser_cannon", "afterburner"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        menu.slot_focus = 0  # weapon_1, per ship_types.json's patrol entry
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertIsNotNone(menu.picker)
        self.assertEqual(menu.picker.items, ["laser_cannon"])

    def test_picker_enter_installs_and_calls_outfits_changed_callback(self):
        import pygame as mocked_pygame
        changed = []
        possessions = Possessions(owned_outfits=["laser_cannon"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol", on_outfits_changed=lambda: changed.append(True))
        menu.slot_focus = 0
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertEqual(possessions.installed_outfits, {"weapon_1": "laser_cannon"})
        self.assertEqual(possessions.owned_outfits, [])
        self.assertEqual(changed, [True])

    def test_enter_on_occupied_slot_uninstalls_and_calls_callback(self):
        import pygame as mocked_pygame
        changed = []
        possessions = Possessions(installed_outfits={"weapon_1": "laser_cannon"})
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol", on_outfits_changed=lambda: changed.append(True))
        menu.slot_focus = 0
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])
        self.assertEqual(changed, [True])

    def test_enter_on_empty_slot_with_no_compatible_outfits_does_not_open_picker(self):
        import pygame as mocked_pygame
        possessions = Possessions(owned_outfits=["afterburner"])  # engine, not weapon
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        menu.slot_focus = 0  # weapon_1
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertIsNone(menu.picker)

    def test_buying_an_outfit_spends_credits_and_adds_to_owned(self):
        possessions = Possessions(credits=1000)
        menu = OutfittingMenu(possessions, "default", {"stock": ["laser_cannon"]}, None)
        menu._buy_outfit("laser_cannon")
        self.assertEqual(possessions.credits, 200)  # 1000 - 800cr
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])

    def test_buy_grid_navigation_does_not_skip_unaffordable_outfits(self):
        """laser_cannon costs 800cr, afterburner costs 1500cr - affording
        only the cannon must not block browsing onto the afterburner (same
        preview-vs-selection fix as ShopMenu/ShipBrowserMenu)."""
        import pygame as mocked_pygame
        possessions = Possessions(credits=800)
        menu = OutfittingMenu(possessions, "default", {"stock": ["laser_cannon", "afterburner"]}, None)
        self.assertEqual(menu.buy_grid.current(), "laser_cannon")
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RIGHT)])
        self.assertEqual(menu.buy_grid.current(), "afterburner")

    def test_icon_for_defaults_to_slot_type_when_outfit_has_no_icon_shape(self):
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, None)
        icon_shape, icon_color = menu._icon_for("laser_cannon")  # weapon slot, no icon_shape in config
        self.assertEqual(icon_shape, "blade")
        self.assertEqual(icon_color, SLOT_COLORS["weapon"])

    def test_left_right_switches_focus_column(self):
        """Left/Right switches slot-diagram-vs-owned-list focus on the
        Install tab now (Tab moved to the top-level Buy/Install switch, to
        free Left/Right for the Buy tab's icon grid navigation)."""
        import pygame as mocked_pygame
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, "patrol")
        self.assertEqual(menu.focus_column, "slots")
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_LEFT)])
        self.assertEqual(menu.focus_column, "owned")

    def test_tab_switches_buy_install_tab(self):
        import pygame as mocked_pygame
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, "patrol")
        self.assertEqual(menu.tab, "install")
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_TAB)])
        self.assertEqual(menu.tab, "buy")

    def test_no_ship_defaults_to_buy_tab(self):
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, None)
        self.assertEqual(menu.tab, "buy")
        self.assertEqual(menu.slots, [])

    def test_escape_closes(self):
        import pygame as mocked_pygame
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, "patrol")
        result = menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_ESCAPE)])
        self.assertEqual(result, "close")


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

    def test_unrecognized_action_is_not_handled(self):
        self.assertFalse(apply_shared_actions("buy_ship:shuttle", Possessions()))

    def test_spend_credits_blocked_when_unaffordable(self):
        possessions = Possessions(credits=5)
        self.assertEqual(shared_action_blocked_reason("spend_credits:20", possessions), "not enough credits")
        self.assertIsNone(shared_action_blocked_reason("spend_credits:5", possessions))
        self.assertIsNone(shared_action_blocked_reason("set_flag:x", possessions))


class _FakeFont:
    """Stand-in for pygame.font.Font in wrap-width tests - width is just
    character count, so expected wrap points are exact and don't depend on
    real font metrics (pygame is mocked in this whole test module anyway)."""
    def size(self, text):
        return (len(text), 10)


class TestWrapText(unittest.TestCase):
    """Test utils._wrap_text() - shared by BackdropMenu and Dialogue (see
    Dialogue.draw()) so long NPC lines wrap inside their box instead of
    running off the edge."""

    def test_short_text_stays_one_line(self):
        self.assertEqual(utils._wrap_text(_FakeFont(), "Hello there", 100), ["Hello there"])

    def test_wraps_at_max_width(self):
        lines = utils._wrap_text(_FakeFont(), "one two three four", 8)
        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(len(line), 8)
        self.assertEqual(" ".join(lines), "one two three four")

    def test_single_long_word_is_not_split(self):
        """A word longer than max_width on its own still isn't broken mid-word."""
        self.assertEqual(utils._wrap_text(_FakeFont(), "supercalifragilistic", 5), ["supercalifragilistic"])


class TestHudZoneWidths(unittest.TestCase):
    """side_panel_max_width()/center_panel_max_width() (see
    docs/DESIGN_PATTERNS.md's "HUD Zone Width Discipline") - the two
    numbers every side/center HUD panel (draw_status_pane, draw_info_panel,
    draw_message_log, draw_controls_pane, draw_glow_message, the minimap)
    caps itself to, derived from the real window width rather than
    ui_scale so they can't drift out of sync with the window's actual
    shape (a wide-but-short window scales ui_scale from height alone -
    see their own docstrings)."""

    def setUp(self):
        self._original_size = (utils.screen_width, utils.screen_height)

    def tearDown(self):
        utils.set_screen_size(*self._original_size)

    def test_side_is_one_quarter_of_screen_width(self):
        utils.set_screen_size(1859, 1024)  # the reported bug's window size
        self.assertEqual(side_panel_max_width(), 1859 // 4)

    def test_center_leaves_a_full_margin_gap_from_each_side_zone(self):
        utils.set_screen_size(1859, 1024)
        ui_scale = utils.get_ui_scale()
        self.assertLess(center_panel_max_width(ui_scale), 1859 / 2)
        self.assertEqual(center_panel_max_width(ui_scale), 1859 // 2 - 2 * hud_margin(ui_scale))
        # A centred pane this wide reaches to within ~hud_margin() of the
        # quarter line (where a left/right side pane begins), never past it.
        centre_right_edge = 1859 / 2 + center_panel_max_width(ui_scale) / 2
        quarter_line = 1859 - side_panel_max_width()  # right side pane's inner edge
        self.assertLessEqual(centre_right_edge, quarter_line)
        self.assertAlmostEqual(quarter_line - centre_right_edge, hud_margin(ui_scale), delta=2)

    def test_zones_track_window_width_directly_not_ui_scale(self):
        """The whole point: on a wide-but-short window, ui_scale is capped
        by height (get_ui_scale() = min(w/800, h/600)), not width - the
        zone widths must still track the real (wide) screen_width, not
        that scale factor, or a panel sized from ui_scale alone could
        still overflow its zone."""
        utils.set_screen_size(1859, 1024)
        ui_scale = utils.get_ui_scale()
        self.assertLess(ui_scale, 1859 / 800, "fixture must reproduce the height-capped case")
        self.assertEqual(side_panel_max_width(), 1859 // 4)

    def test_side_panel_width_fills_quarter_from_margin_to_the_line(self):
        """An edge-anchored pane at hud_margin() from the edge, this wide,
        has its inner edge exactly on the quarter line."""
        utils.set_screen_size(1859, 1024)
        ui_scale = utils.get_ui_scale()
        self.assertEqual(hud_margin(ui_scale) + side_panel_width(ui_scale), side_panel_max_width())

    def test_side_panel_width_stays_positive_on_a_tiny_window(self):
        utils.set_screen_size(200, 200)
        self.assertGreaterEqual(side_panel_width(utils.get_ui_scale()), 1)


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


class TestCharacterSetRoutine(unittest.TestCase):
    """Character.set_routine()/resolve_routine_class() - the mechanism
    behind temporarily overriding a character's routine (e.g. an escort
    pilot following the player - see person.escort_flag/
    SpaceScreen._sync_escorts) and restoring their normal role routine
    afterward."""

    def test_set_routine_starts_it_immediately(self):
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot={"name": "Kade Marsh", "role": "patrol_officer"}, route=[], get_interior_screen=None,
        )
        target = SimpleNamespace(x=100, y=0, get_distance=lambda x, y: 100)
        character.set_routine(OrbitPlayerRoutine(target))
        self.assertIsInstance(character.routine, OrbitPlayerRoutine)
        self.assertTrue(character.autopilot_active)  # start() engaged orbit

    def test_resolve_routine_class_matches_the_role_used_at_construction(self):
        from game.world.character import resolve_routine_class, ROLE_ROUTINES
        self.assertIs(resolve_routine_class("patrol_officer"), ROLE_ROUTINES["patrol_officer"])

    def test_explicit_routine_name_overrides_the_role_default(self):
        from game.world.character import resolve_routine_class, ROUTINE_REGISTRY
        # an unknown role would normally be IdleRoutine
        self.assertIs(
            resolve_routine_class("smuggler", routine_name="wander"),
            ROUTINE_REGISTRY["wander"],
        )

    def test_unknown_routine_name_falls_back_to_idle(self):
        from game.world.character import resolve_routine_class, IdleRoutine
        self.assertIs(resolve_routine_class("patrol_officer", routine_name="nonsense"), IdleRoutine)

    def test_pilot_config_routine_key_picks_the_routine(self):
        from game.world.wander_routine import WanderRoutine
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot={"name": "Rove", "role": "smuggler", "routine": "wander"},
            route=[], get_interior_screen=None,
        )
        self.assertIsInstance(character.routine, WanderRoutine)
        self.assertEqual(character.routine_name, "wander")

    def test_escorting_flag_defaults_to_false(self):
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot={"name": "Kade Marsh", "role": "patrol_officer"}, route=[], get_interior_screen=None,
        )
        self.assertFalse(character.escorting)


class TestOrbitPlayerRoutine(unittest.TestCase):
    """OrbitPlayerRoutine - keeps an escort circling a moving target
    (typically the player) at a fixed radius by re-engaging orbit mode
    every frame with the target's current position as the centre, so the
    circle tracks the target instead of the escort parking on top of it."""

    def _character(self):
        return Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot={"name": "Kade Marsh", "role": "patrol_officer"}, route=[], get_interior_screen=None,
        )

    def test_start_engages_orbit_centred_on_the_target(self):
        character = self._character()
        target = SimpleNamespace(x=500, y=0, get_distance=lambda x, y: 500)
        OrbitPlayerRoutine(target).start(character)
        self.assertTrue(character.autopilot_active)
        mode = character.ship.autopilot._mode
        self.assertEqual((mode.center_x, mode.center_y), (500, 0))

    def test_run_moves_the_orbit_centre_to_follow_the_target(self):
        character = self._character()
        target = SimpleNamespace(x=500, y=0, get_distance=lambda x, y: 500)
        routine = OrbitPlayerRoutine(target)
        routine.start(character)
        target.x, target.y = 800, 200  # target flew somewhere else
        routine.run(character)
        mode = character.ship.autopilot._mode
        self.assertEqual((mode.center_x, mode.center_y), (800, 200))
        self.assertTrue(character.autopilot_active)


class TestExplorerRoutine(unittest.TestCase):
    """ExplorerRoutine migrates a Character between two SystemState.ai_ships
    lists and orbits something in whichever system it currently occupies -
    the mechanism the "Allow NPCs to jump between systems" backlog item and
    multi-system simulation both rely on."""

    @staticmethod
    def _make_system(offset_x, offset_y):
        station = Landable(offset_x, offset_y, graphics={}, interiors={})
        moon = Landable(offset_x + 500, offset_y, graphics={}, interiors={})
        return SystemState(station, moon, central_star=None, celestial_bodies=[], ai_ships=[])

    def test_starts_by_orbiting_something_in_its_home_system(self):
        systems = {"a": self._make_system(0, 0), "b": self._make_system(1000, 1000)}
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="shuttle", graphics=None,
            pilot={"name": "Juno Vale", "role": "explorer"}, route=[],
            get_interior_screen=None, systems=systems, system_id="a",
        )
        systems["a"].ai_ships.append(character)  # mimics _build_system_state's own append after construction

        self.assertEqual(character.system_id, "a")
        self.assertTrue(character.autopilot_active, "Should already be orbiting something in its home system")

    def test_migrates_to_another_system_once_its_timer_expires(self):
        systems = {"a": self._make_system(0, 0), "b": self._make_system(1000, 1000)}
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="shuttle", graphics=None,
            pilot={"name": "Juno Vale", "role": "explorer"}, route=[],
            get_interior_screen=None, systems=systems, system_id="a",
        )
        systems["a"].ai_ships.append(character)

        character.routine._timer = 1  # force the next update() to start a jump
        # Migration now only happens once the jump animation finishes (align,
        # bounded by 180deg / (rotation_speed*3) <= 12 frames at the default
        # rotation_speed of 5, then JUMP_TRAVEL_FRAMES=150) - 200 comfortably
        # clears that regardless of the animation's random heading.
        for _ in range(200):
            character.update()
            if character.system_id == "b":
                break

        self.assertEqual(character.system_id, "b", "Only system 'b' exists as an 'other' system to jump to")
        self.assertNotIn(character, systems["a"].ai_ships)
        self.assertIn(character, systems["b"].ai_ships)
        self.assertTrue(character.autopilot_active, "Should be orbiting something in the new system")
        self.assertFalse(character.jumping, "Jump animation should have finished")

    def test_jump_plays_an_align_and_travel_animation_before_migrating(self):
        """Regression: ExplorerRoutine used to migrate the Character the
        instant its timer expired - a silent teleport, with no visible
        transition. It should now wind up and fly off the same way the
        player's own jump does (see JumpDrive): staying put in the origin
        system, autopilot off and ship-driven, for the animation's
        duration before it actually migrates."""
        systems = {"a": self._make_system(0, 0), "b": self._make_system(1000, 1000)}
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="shuttle", graphics=None,
            pilot={"name": "Juno Vale", "role": "explorer"}, route=[],
            get_interior_screen=None, systems=systems, system_id="a",
        )
        systems["a"].ai_ships.append(character)

        character.routine._timer = 1
        character.update()  # begins the jump this frame

        self.assertTrue(character.jumping)
        self.assertFalse(character.autopilot_active, "Autopilot must be off so it can't fight the jump heading")
        self.assertEqual(character.system_id, "a", "Still in the origin system mid-animation")
        self.assertIn(character, systems["a"].ai_ships)

        for _ in range(200):
            character.update()
            if not character.jumping:
                break

        self.assertFalse(character.jumping)
        self.assertEqual(character.system_id, "b")

    def test_single_system_story_just_keeps_orbiting_at_home(self):
        """No "other" system to jump to - should orbit again in the same
        system rather than erroring or vanishing from every list."""
        systems = {"a": self._make_system(0, 0)}
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="shuttle", graphics=None,
            pilot={"name": "Juno Vale", "role": "explorer"}, route=[],
            get_interior_screen=None, systems=systems, system_id="a",
        )
        systems["a"].ai_ships.append(character)

        character.routine._timer = 1
        character.routine.run(character)

        self.assertEqual(character.system_id, "a")
        self.assertIn(character, systems["a"].ai_ships)
        self.assertEqual(len(systems["a"].ai_ships), 1, "Must not be duplicated into the list")


class TestMultiSystemSimulation(unittest.TestCase):
    """Regression coverage for simulating every system a story defines, not
    just whichever one the player currently occupies (see SystemState and
    SpaceScreen.systems) - previously, a system the player wasn't in didn't
    exist as live objects at all until re-visited, which reset its AI ships
    back to their config-file spawn points every time."""

    def test_background_system_ai_ships_keep_moving(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        background_ship = game_screen.systems["keplers_reach"].ai_ships[0]
        before = (background_ship.x, background_ship.y)

        # ai_ships[0] here is a drossholt_freighter (rotation_speed 1 deg/frame -
        # see ship_types.json), and Character.for_ai_pilot gives every AI ship a
        # random starting facing (character.py). SeekMode doesn't thrust until
        # it's turned within 10 degrees of its target heading, so a worst-case
        # starting angle (~180 degrees off) needs up to 171 frames of pure
        # turning before the ship moves at all - confirmed by sweeping every
        # starting angle 0-360 against this same rotation_speed. 120 frames
        # made this flaky (~1 in 4) purely on the random starting angle; 250
        # comfortably clears the proven worst case.
        for _ in range(250):
            game_screen.update_physics()

        self.assertNotEqual((background_ship.x, background_ship.y), before,
                             "AI ship in a system the player isn't in should still be moving")

    def test_jumping_does_not_rebuild_the_destination_system(self):
        """Jumping used to reload the destination system's config from
        scratch (_load_system_content), discarding any progress its AI
        ships had already made while simulating in the background."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        destination_state = game_screen.systems["keplers_reach"]
        for _ in range(120):
            game_screen.update_physics()
        moved_position = (destination_state.ai_ships[0].x, destination_state.ai_ships[0].y)

        game_screen.selected_system_id = "keplers_reach"
        game_screen._begin_jump()
        game_screen._complete_jump()

        self.assertIs(game_screen.systems["keplers_reach"], destination_state,
                       "Must reuse the same SystemState, not rebuild a fresh one")
        self.assertEqual((game_screen.ai_ships[0].x, game_screen.ai_ships[0].y), moved_position)

    def test_save_restore_round_trip_survives_a_migrated_ai_ship(self):
        """get_state()/restore_state() key ai_ships by pilot name and record
        which system each is in (see SAVE_SYSTEM.md) specifically so an
        ExplorerRoutine-driven pilot's system can round-trip through a save
        - a plain per-system list index can't survive it moving lists."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.systems["sol_alpha"].ai_ships if s.person.name == "Juno Vale")
        # Simulate it having wandered off to the other system already.
        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"
        explorer.x, explorer.y = 4242, 1337

        state = game_screen.get_state()
        self.assertEqual(state["ai_ships"]["Juno Vale"]["system_id"], "keplers_reach")

        fresh = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        fresh.restore_state(state)

        self.assertNotIn(explorer.person.name, [s.person.name for s in fresh.systems["sol_alpha"].ai_ships])
        restored = next(s for s in fresh.systems["keplers_reach"].ai_ships if s.person.name == "Juno Vale")
        self.assertEqual((restored.x, restored.y), (4242, 1337))
        self.assertEqual(restored.system_id, "keplers_reach")

    def test_targeting_a_ship_that_jumps_away_clears_the_target(self):
        """Regression: a targeted AI ship migrating to another system (see
        ExplorerRoutine._migrate) used to leave the target selected -
        targetable_objects (built once per _activate_system) still held
        the stale tuple referencing it, and that Character keeps updating
        every frame regardless of which system it's in (see
        SystemState.update_physics), so the brackets/arrow kept tracking
        its position in whatever system it jumped to - a totally
        unrelated part of the same game-space coordinates. Losing the
        ship should clear the target instead of following it there."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Juno Vale")

        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        filtered = game_screen._filtered_targets()
        game_screen.current_target = next(i for i, (_, obj) in enumerate(filtered) if obj is explorer)
        self.assertIs(game_screen._get_target_object(), explorer)

        # Simulate the ship having jumped away, the way ExplorerRoutine._migrate does.
        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"

        game_screen.update_physics()

        self.assertIsNone(game_screen.current_target, "Target should be lost once the ship leaves this system")
        self.assertIsNone(game_screen._get_target_object())

    def test_autopilot_seeking_a_ship_that_jumps_away_disengages(self):
        """Regression: engaging autopilot on an AI ship (engage_seek, the
        'G' key) sets player.autopilot_target independently of
        current_target/targetable_objects - clearing current_target alone
        (see test above) left the player's autopilot still committed to
        chasing that Character's position in whatever system it jumped to."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Juno Vale")

        game_screen.player.engage_seek(explorer)
        self.assertTrue(game_screen.player.autopilot_active)

        # Simulate the ship having jumped away, the way ExplorerRoutine._migrate does.
        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"

        game_screen.update_physics()

        self.assertFalse(game_screen.player.autopilot_active, "Autopilot should disengage once its target is gone")
        self.assertIsNone(game_screen.player.autopilot_target)

    def test_cycling_ships_still_reaches_every_ship_after_one_jumps_away(self):
        """Regression: a departed explorer's stale tuple stayed in
        _filtered_targets() (targetable_objects is built once per
        _activate_system and never pruned), so cycling wrapped onto a ghost
        that _validate_target cleared a frame later. Juno Vale is last in
        Sol Alpha's ship list, so once she jumped away, pressing "[" from
        the first ship wrapped straight onto her and bounced back - never
        landing on Kade Marsh in between. "]" happened to reach Kade on the
        step before the ghost, which is why only "[" looked broken."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Juno Vale")

        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"

        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        game_screen.update_physics()  # prunes the departed ship (see _validate_target)

        names = [obj.person.name for _, obj in game_screen._filtered_targets()]
        self.assertNotIn("Juno Vale", names, "Departed ship should drop out of the target list")
        self.assertEqual(set(names), {"Elena Voss", "Kade Marsh"})

        for direction in (-1, 1):  # "[" and "]"
            seen = set()
            game_screen.current_target = None
            for _ in range(len(names) * 2):
                game_screen._cycle_target(direction)
                self.assertIsNotNone(game_screen._get_target_object())
                game_screen._validate_target()
                still_targeted = game_screen._get_target_object()
                self.assertIsNotNone(
                    still_targeted,
                    f"Cycling with direction {direction} landed on a ship that immediately got cleared")
                seen.add(still_targeted.person.name)
            self.assertEqual(seen, {"Elena Voss", "Kade Marsh"})

    def test_a_ship_that_jumps_back_becomes_targetable_again(self):
        """_validate_target re-adds an AI ship that's returned to this
        system (ExplorerRoutine can jump back to where it started) so it
        doesn't stay untargetable until the next _activate_system."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Juno Vale")
        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")

        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"
        game_screen.update_physics()
        self.assertNotIn("Juno Vale", [o.person.name for _, o in game_screen._filtered_targets()])

        game_screen.systems["keplers_reach"].ai_ships.remove(explorer)
        game_screen.systems["sol_alpha"].ai_ships.append(explorer)
        explorer.system_id = "sol_alpha"
        game_screen.update_physics()
        self.assertIn("Juno Vale", [o.person.name for _, o in game_screen._filtered_targets()])


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


class TestLocationScreenDrawDoesNoPerFrameFontConstruction(unittest.TestCase):
    """Regression: LocationScreen.draw() built two `pygame.font.Font(None, ...)`
    objects every frame (room-label + portal-label fonts). Each construction
    opens pygame's bundled default-font file, and on Windows that file open
    has a fat latency tail (real-time AV scan) - the sporadic ~0.5 s freeze
    while walking around a station. Fonts must come from the cached
    `get_font()` helper, so a steady-state frame constructs none."""

    def test_per_frame_draw_paths_use_the_cached_get_font_helper(self):
        import inspect
        from game.screens import location_screen
        from game.world import dialogue as dialogue_mod
        from game.ui import star_map

        for label, fn in (
            ("LocationScreen.draw", location_screen.LocationScreen.draw),
            ("Dialogue.draw", dialogue_mod.Dialogue.draw),
            ("StarMap.draw_content", star_map.StarMap.draw_content),
        ):
            src = inspect.getsource(fn)
            self.assertNotIn(
                "pygame.font.Font", src,
                f"{label} constructs a font every frame - route it through utils.get_font() "
                f"so a slow (AV-scanned) font-file open can't stall the frame",
            )


class TestLocationScreenClickTargeting(unittest.TestCase):
    """Test LocationScreen._select_person_target_at() - click-to-target for
    NPCs/visitors on foot, the interior counterpart to SpaceScreen's own
    click-to-target over ships/landables."""

    def _make_screen(self):
        config = {
            "label": "Test Room",
            "npcs": [
                {"name": "Near", "x": 100, "y": 100, "role": "resident"},
                {"name": "Far", "x": 500, "y": 500, "role": "resident"},
            ],
        }
        return LocationScreen(config_data=config, world_width=800, world_height=600)

    def test_click_on_a_person_targets_them(self):
        screen = self._make_screen()
        screen._select_person_target_at(105, 100)
        self.assertEqual(screen._get_npc_target().name, "Near")

    def test_click_on_empty_space_leaves_target_unset(self):
        screen = self._make_screen()
        screen._select_person_target_at(300, 300)
        self.assertIsNone(screen._get_npc_target())

    def test_closest_person_wins_when_two_are_both_in_click_range(self):
        config = {
            "label": "Test Room",
            "npcs": [
                {"name": "Closer", "x": 100, "y": 100, "role": "resident"},
                {"name": "Farther", "x": 120, "y": 100, "role": "resident"},
            ],
        }
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        screen._select_person_target_at(105, 100)
        self.assertEqual(screen._get_npc_target().name, "Closer")

    def test_click_replaces_an_existing_target(self):
        screen = self._make_screen()
        screen._select_person_target_at(105, 100)
        self.assertEqual(screen._get_npc_target().name, "Near")
        screen._select_person_target_at(505, 500)
        self.assertEqual(screen._get_npc_target().name, "Far")


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
    mismatch warning (see CLAUDE.md's "Save Compatibility & Story
    Versioning" section) - never blocks loading, just surfaces the risk
    that a save's story config or this game's state-handling code has
    changed since the save was made."""

    def test_space_screen_reads_story_version_from_story_json(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        self.assertEqual(game_screen.story_version, "1.6.0")

    def test_build_save_game_state_records_story_version(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_state, _ = build_save_game_state(game_screen, "game", None, None)
        self.assertEqual(game_state["story_version"], "1.6.0")

    def test_matching_version_prints_no_warning(self):
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", "1.6.0")
        self.assertEqual(captured.getvalue(), "")

    def test_mismatched_version_warns(self):
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", "0.9.0")
        self.assertIn("0.9.0", captured.getvalue())
        self.assertIn("1.6.0", captured.getvalue())

    def test_missing_version_warns(self):
        """A save made before story versioning existed has no
        story_version key at all - still worth flagging, not silently
        treated as compatible."""
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", None)
        self.assertNotEqual(captured.getvalue(), "")


class TestLocationScreenTouchingRoomBoundary(unittest.TestCase):
    """Regression test: two touching rooms (e.g. Entrance Hall y:300-600 and
    Bar y:0-300, sharing the line y=300) both used strict "<" bounds, so a
    step that landed exactly on the shared boundary was invalid in *both*
    rooms at once - an invisible wall stranding the player one step short.
    point_in_polygon now counts an on-edge point as inside, so a step
    landing exactly on the seam is valid in at least one room."""

    def _make_two_room_screen(self):
        config = {
            "label": "Test", "culture": None,
            "rooms": [
                {"label": "Hall", "rect": [360, 300, 80, 300]},
                {"label": "Bar", "rect": [300, 0, 200, 300]},
            ],
            "npcs": [],
        }
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        # rooms only populate when a culture is set (see LocationScreen.__init__) -
        # set them directly to exercise the bounds check in isolation.
        screen.rooms = [normalize_room(r) for r in config["rooms"]]
        return screen

    def test_can_cross_from_hall_into_bar_at_every_starting_y(self):
        screen = self._make_two_room_screen()
        keys = {pygame_mock.K_UP: True, pygame_mock.K_w: False, pygame_mock.K_DOWN: False, pygame_mock.K_s: False, pygame_mock.K_LEFT: False, pygame_mock.K_a: False, pygame_mock.K_RIGHT: False, pygame_mock.K_d: False}
        max_steps = int((400 - 200) / screen.speed) + 5   # enough to walk from y=399 well past y=300
        for start_y in range(301, 400):
            screen.player.x, screen.player.y = 400, start_y
            for _ in range(max_steps):
                screen._handle_movement(keys)
                if screen.player.y <= 250:
                    break
            self.assertLessEqual(screen.player.y, 300, f"Got stuck at y={screen.player.y} starting from y={start_y}")


class TestSpaceScreenShipTypePersistence(unittest.TestCase):
    """Regression test: SpaceScreen.__init__() always starts the player's
    Ship from story.json's default player_type - after buying a ship and
    saving, loading the save (a fresh SpaceScreen + restore_state()) used
    to silently revert the player back to that story default instead of
    whatever they'd actually bought, even though Possessions itself
    restored correctly."""

    def test_restore_state_reequips_the_last_purchased_ship(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        spaceport = game_screen.get_interior_screen(game_screen.station, "default")
        spaceport._apply_dialogue_action("buy_ship:shuttle")
        self.assertEqual(game_screen.player.ship.graphics.get("size"), 10)  # shuttle's configured size

        state = game_screen.get_state()

        fresh = SpaceScreen(pilot_name="Test", story="default")
        fresh.restore_state(state)
        self.assertEqual(fresh.player.ship.graphics.get("size"), 10,
                          "Loading a save must re-equip the bought ship, not story.json's starting default")

    def test_restore_possessions_from_a_docked_location_save_also_reequips(self):
        """The station/moon load path calls restore_possessions() (not
        restore_state() - see its docstring for why: state["player"] there
        is the LocationScreen's own walking position, not the ship's space
        position) - it must still pick up "possessions" and re-equip
        accordingly."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        spaceport = game_screen.get_interior_screen(game_screen.station, "default")
        spaceport._apply_dialogue_action("buy_ship:shuttle")

        docked_state = spaceport.get_state()  # {"player": {...}, "possessions": {...}} - no ai_ships key

        fresh = SpaceScreen(pilot_name="Test", story="default")
        fresh.restore_possessions(docked_state)
        self.assertEqual(fresh.player.ship.graphics.get("size"), 10)


class TestSpaceScreenParkAt(unittest.TestCase):
    """Regression test: loading directly into a station/moon save used to
    call the full restore_state(), which fed the LocationScreen's own
    walking-position dict (game_state["player"]) into the ship's x/y as if
    it were the ship's space position - scattering the ship to wherever
    that (unrelated, much smaller-scale) interior coordinate happened to
    be instead of docking it at the landable. main.py now calls
    restore_possessions() + park_at() for station/moon loads instead."""

    def test_park_at_places_the_ship_exactly_on_the_landable(self):
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


class TestSpaceScreenHailing(unittest.TestCase):
    """K_h hailing (see SpaceScreen.handle_input/_start_hail) and NPC-
    initiated one-way hails (_check_one_way_hails) - exercised against the
    default story's real pilots.json/sol_alpha.json config: Kade Marsh
    (patrol_officer, OrbitRoutine - never ashore, and configured with both
    a one_way_hail and a branching hail_dialogue_tree) and Elena Voss
    (freighter_pilot, DockRoutine - can be ashore) are real fixtures here,
    not test doubles, so a config typo in either would fail these too."""

    def _target_ship(self, game_screen, pilot_name):
        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        for i, (_, obj) in enumerate(game_screen._filtered_targets()):
            if obj.person.name == pilot_name:
                game_screen.current_target = i
                return obj
        self.fail(f"{pilot_name} not found among targetable ships")

    def test_hailing_a_flying_pilot_opens_their_hail_dialogue(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        self._target_ship(game_screen, "Kade Marsh")
        game_screen._start_hail()
        self.assertIsNotNone(game_screen.active_dialogue)
        self.assertEqual(game_screen.active_dialogue.npc_name, "Kade Marsh")
        self.assertEqual(game_screen.active_dialogue.current_node, "start")

    def test_hailing_an_ashore_pilot_shows_a_busy_banner_instead(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        elena = self._target_ship(game_screen, "Elena Voss")
        elena.ashore = True
        game_screen._start_hail()
        self.assertIsNone(game_screen.active_dialogue)
        self.assertIn("docked", game_screen.hail_banner[0])

    def test_hailing_with_no_target_does_nothing(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.current_target = None
        game_screen._start_hail()
        self.assertIsNone(game_screen.active_dialogue)

    def test_one_way_hail_fires_once_in_range_and_sets_a_seen_flag(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.in_flight = True
        kade = self._target_ship(game_screen, "Kade Marsh")
        game_screen.player.x, game_screen.player.y = kade.x, kade.y  # distance 0 - well within range
        game_screen._check_one_way_hails()
        self.assertIsNotNone(game_screen.hail_banner)
        self.assertIn("Kade Marsh", game_screen.hail_banner[0])
        flags = game_screen.player.person.possessions.flags
        self.assertTrue(flags.get("one_way_hail_seen:Kade Marsh"))
        # Also logged (see Possessions.add_message) - the banner alone is
        # easy to miss, so it stays in the Messages pane too.
        message_log = game_screen.player.person.possessions.message_log
        self.assertEqual(message_log[0]["sender"], "Kade Marsh")

        game_screen.hail_banner = None
        game_screen._check_one_way_hails()
        self.assertIsNone(game_screen.hail_banner, "must not fire a second time for the same pilot")
        self.assertEqual(len(message_log), 1, "must not log a second time for the same pilot")

    def test_one_way_hail_is_suppressed_while_docked(self):
        """update_physics() keeps running in the background while the player
        is docked in an interior; a pilot hailing the cockpit shouldn't
        land while nobody's in it (see SpaceScreen.in_flight)."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.in_flight = False  # docked
        kade = self._target_ship(game_screen, "Kade Marsh")
        game_screen.player.x, game_screen.player.y = kade.x, kade.y
        game_screen._check_one_way_hails()
        self.assertIsNone(game_screen.hail_banner)
        flags = game_screen.player.person.possessions.flags
        self.assertFalse(flags.get("one_way_hail_seen:Kade Marsh"))
        self.assertEqual(game_screen.player.person.possessions.message_log, [])


class TestSpaceScreenStartConfig(unittest.TestCase):
    """story.json's "start" block + starting_mission_trigger - the player's
    state and world placement at the beginning of a brand-new game (see
    SpaceScreen._apply_start_config / begin_new_game). A loaded save is
    unaffected: restore_possessions() overwrites all of this."""

    def test_default_story_begins_shipless_in_the_station_interior(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        location, interior = game_screen.begin_new_game()
        self.assertEqual((location, interior), ("station", "default"))
        self.assertEqual(game_screen.player.person.possessions.owned_ships, [])
        self.assertEqual(game_screen.player.person.possessions.credits, 0)
        # trigger is "ship_purchase" - no mission before a ship is bought
        self.assertNotIn("first_flight", game_screen.player.person.possessions.missions)

    def test_apply_start_config_seeds_credits_ship_items_and_flags(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.start_config = {
            "credits": 4200, "ship": "shuttle",
            "items": {"data_chip": 2}, "outfits": ["cargo_expansion"],
            "flags": {"met_the_broker": True},
        }
        game_screen._apply_start_config()
        possessions = game_screen.player.person.possessions
        self.assertEqual(possessions.credits, 4200)
        self.assertEqual(possessions.owned_ships, ["shuttle"])
        self.assertEqual(possessions.items, {"data_chip": 2})
        self.assertEqual(possessions.owned_outfits, ["cargo_expansion"])
        self.assertTrue(possessions.flags.get("met_the_broker"))
        # ship stats were actually applied, not just recorded
        self.assertEqual(game_screen.player.ship.max_velocity,
                         utils.get_ship_type("default", "shuttle")["max_velocity"])

    def test_a_starting_ship_triggers_the_tutorial_on_new_game(self):
        """With no purchase to hook, begin_new_game() must fire the
        starting_mission itself when the story grants a ship."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.start_config = {"ship": "shuttle", "location": "space"}
        game_screen._apply_start_config()
        location, interior = game_screen.begin_new_game()
        self.assertEqual((location, interior), ("space", None))
        self.assertEqual(game_screen.player.person.possessions.missions.get("first_flight"), 0)

    def test_new_game_trigger_arms_the_mission_and_launch_starts_it(self):
        """A "new_game" trigger with a docked start still defers to the
        first launch (board_ship()) - so the opening toast/hail land in
        the cockpit, not the station the player begins in."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.starting_mission_trigger = "new_game"
        game_screen.begin_new_game()  # default start location is "station"
        possessions = game_screen.player.person.possessions
        self.assertNotIn("first_flight", possessions.missions)
        self.assertTrue(possessions.flags.get("starting_mission_armed"))
        game_screen.board_ship()
        self.assertEqual(possessions.missions.get("first_flight"), 0)


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


class TestSpaceScreenMissionIntegration(unittest.TestCase):
    """The default story's "first_flight" tutorial mission - real
    story.json ("starting_mission") + missions.json config, auto-started
    on first ship purchase and advanced by the generic gameplay-event
    flags SpaceScreen/PlayerController set (used_ships_target_mode/
    used_turn/used_thrust/braked_below_threshold/used_autopilot_on_ship/
    landed_on_landable/completed_jump) alongside "hailed_pilot:<name>"
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

    def test_starting_the_tutorial_makes_kade_escort_immediately(self):
        """first_flight's "on_start_flags" sets kade_escorting the moment
        the mission begins (on launch, board_ship()), so _sync_escorts pulls
        Kade into OrbitPlayerRoutine right away - not only once the player
        accepts his offer mid-conversation."""
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        self.assertTrue(possessions.flags.get("kade_escorting"))
        game_screen.update_physics()
        kade = next(s for state in game_screen.systems.values() for s in state.ai_ships if s.person.name == "Kade Marsh")
        self.assertTrue(kade.escorting)
        self.assertIsInstance(kade.routine, OrbitPlayerRoutine)

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

    def test_turning_advances_past_the_turning_stage(self):
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        possessions.missions["first_flight"] = 4  # skip straight to the turning stage

        keys = {k: False for k in (pygame_mock.K_LEFT, pygame_mock.K_a, pygame_mock.K_RIGHT, pygame_mock.K_d, pygame_mock.K_UP, pygame_mock.K_w, pygame_mock.K_DOWN, pygame_mock.K_s)}
        keys[pygame_mock.K_a] = True
        game_screen.player.handle_input(keys)
        game_screen.update_physics()
        self.assertTrue(possessions.flags.get("used_turn"))
        self.assertEqual(possessions.missions["first_flight"], 5)

    def test_thrusting_advances_past_the_flying_stage(self):
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        possessions.missions["first_flight"] = 5  # skip straight to the thrust stage

        game_screen.player.thrust = 0.2
        game_screen.update_physics()
        self.assertTrue(possessions.flags.get("used_thrust"))
        self.assertEqual(possessions.missions["first_flight"], 6)

    def test_engaging_autopilot_on_a_ship_sets_the_flag(self):
        game_screen = self._boarded_screen()
        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        game_screen.current_target = 0  # any AI ship in the default system
        target = game_screen._get_target_object()
        self.assertIsInstance(target, Character)

        game_screen.handle_input([SimpleNamespace(type=pygame_mock.KEYDOWN, key=pygame_mock.K_SPACE)])
        self.assertTrue(game_screen.player.person.possessions.flags.get("used_autopilot_on_ship"))

    def test_landing_sets_the_flag(self):
        game_screen = self._boarded_screen()
        game_screen._mark_landed()
        self.assertTrue(game_screen.player.person.possessions.flags.get("landed_on_landable"))

    def test_braking_below_threshold_sets_the_flag_and_advances_the_stage(self):
        """S/Down (point_to_reverse_velocity - see PlayerController.handle_input)
        sets "used_brake"; combined with "used_thrust" and a low enough
        speed, update_physics() sets "braked_below_threshold" - the flag
        the tutorial's braking stage completes on."""
        game_screen = self._boarded_screen()
        possessions = game_screen.player.person.possessions
        possessions.missions["first_flight"] = 6  # skip straight to the braking stage
        possessions.flags["used_thrust"] = True
        game_screen.player.velocity_x, game_screen.player.velocity_y = 0, 0  # already slow

        keys = {k: False for k in (pygame_mock.K_LEFT, pygame_mock.K_a, pygame_mock.K_RIGHT, pygame_mock.K_d, pygame_mock.K_UP, pygame_mock.K_w, pygame_mock.K_DOWN, pygame_mock.K_s)}
        keys[pygame_mock.K_s] = True
        game_screen.player.handle_input(keys)
        self.assertTrue(possessions.flags.get("used_brake"))

        game_screen.update_physics()
        self.assertTrue(possessions.flags.get("braked_below_threshold"))
        self.assertEqual(possessions.missions["first_flight"], 7)

    def test_accepting_kades_help_sets_flags_and_starts_the_escort(self):
        """Choosing "Sure, show me the ropes." in Kade's hail dialogue sets
        both accepted_kade_help (advances the mission past the
        conversation stage) and kade_escorting (see
        SpaceScreen._sync_escorts) - all from one dialogue option's
        "actions" list."""
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
        self.assertEqual(dialogue.current_node, "start")

        option = dialogue.current_options(possessions.flags)[0]
        self.assertEqual(option["label"], "Sure, show me the ropes.")
        for action in option_actions(option):
            apply_shared_actions(action, possessions, game_screen.missions_config)
        dialogue.advance(option)

        self.assertTrue(possessions.flags.get("accepted_kade_help"))
        self.assertTrue(possessions.flags.get("kade_escorting"))
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 3)
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
        possessions.flags["kade_escorting"] = True
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 3)
        self.assertTrue(kade_char.escorting)

        possessions.flags["viewed_mission_log"] = True
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 4)

        possessions.flags["used_turn"] = True
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 5)

        game_screen.player.thrust = 0.2
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 6)

        possessions.flags["used_brake"] = True
        game_screen.player.velocity_x, game_screen.player.velocity_y = 0, 0
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 7)

        game_screen.jump_state = {"phase": "travel", "heading": 0, "timer": 0, "destination": game_screen.system_id}
        game_screen._complete_jump()
        self.assertTrue(possessions.flags.get("completed_jump"))
        game_screen.update_physics()
        self.assertEqual(possessions.missions["first_flight"], 8)

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
        bartender = next(c.person for c in concourse.npcs if c.person.name == "Bram Solise")
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


class TestLocationScreenEconomy(unittest.TestCase):
    """Test LocationScreen's ship-ownership-gated exit and dialogue-action
    gating - the mechanisms behind the spaceport's disabled "Return to
    Ship" option and the salesman/loan-officer purchase flow."""

    def _make_screen(self, connected_locations=None, return_to_ship=True, credits=0, owned_ships=None, loans=None):
        possessions = Possessions(credits=credits, owned_ships=owned_ships or [], loans=loans or [])
        config = {"label": "Spaceport", "connected_locations": connected_locations or [], "return_to_ship": return_to_ship}
        return LocationScreen(config_data=config, world_width=800, world_height=600, player_possessions=possessions)

    def test_ship_unavailable_without_a_ship(self):
        screen = self._make_screen(return_to_ship=True)
        self.assertFalse(screen.ship_available)
        self.assertEqual(screen.get_available_exit_options(), [])
        self.assertEqual(screen.get_exit_disabled_reasons(), {"ship": "no ship docked here"})

    def test_ship_available_once_owned(self):
        screen = self._make_screen(return_to_ship=True, owned_ships=["shuttle"])
        self.assertTrue(screen.ship_available)
        self.assertEqual(screen.get_available_exit_options(), ["ship"])
        self.assertEqual(screen.get_exit_disabled_reasons(), {})

    def test_connected_location_exit_unaffected_by_ship_ownership(self):
        screen = self._make_screen(connected_locations=["default"], return_to_ship=False)
        self.assertEqual(screen.get_available_exit_options(), ["default"])
        self.assertEqual(screen.get_exit_disabled_reasons(), {})

    def test_buy_ship_blocked_when_unaffordable(self):
        screen = self._make_screen(credits=0)
        option = {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"}
        self.assertEqual(screen._option_blocked_reason(option), "not enough credits")

    def test_buy_ship_allowed_when_affordable(self):
        screen = self._make_screen(credits=1200)
        option = {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"}
        self.assertIsNone(screen._option_blocked_reason(option))
        screen._apply_dialogue_action("buy_ship:shuttle")
        self.assertEqual(screen.player.possessions.credits, 0)
        self.assertEqual(screen.player.possessions.owned_ships, ["shuttle"])

    def test_buy_ship_method_can_be_called_directly(self):
        """buy_ship() is the public entry point ShipBrowserMenu calls (via
        main.py's build_shop_menu) - _apply_dialogue_action's "buy_ship:"
        branch is just a thin wrapper around it, so both purchase paths
        share one mutation."""
        screen = self._make_screen(credits=1200)
        screen.buy_ship("shuttle")
        self.assertEqual(screen.player.possessions.credits, 0)
        self.assertEqual(screen.player.possessions.owned_ships, ["shuttle"])

    def test_buy_ship_calls_on_ship_purchased_callback(self):
        possessions = Possessions(credits=1200)
        config = {"label": "Spaceport"}
        purchased = []
        screen = LocationScreen(config_data=config, world_width=800, world_height=600, player_possessions=possessions, on_ship_purchased=purchased.append)
        screen._apply_dialogue_action("buy_ship:shuttle")
        self.assertEqual(purchased, ["shuttle"])

    def test_buy_ship_sets_the_bought_ship_gameplay_flags(self):
        possessions = Possessions(credits=1200)
        screen = LocationScreen(config_data={"label": "Spaceport"}, world_width=800, world_height=600, player_possessions=possessions)
        screen.buy_ship("shuttle")
        self.assertTrue(possessions.flags.get("bought_ship"))
        self.assertTrue(possessions.flags.get("bought_ship:shuttle"))

    def test_buy_ship_uninstalls_outfits_instead_of_carrying_them_to_the_new_ship(self):
        """Regression test: installed_outfits describes "whichever ship is
        flown", not a specific hull (see docs/SAVE_SYSTEM.md) - buying a new
        ship used to silently inherit whatever was mounted on the old one
        for free, since slot ids like "utility_1" are reused across ship
        types. The new ship must start bare, with the old outfit back in
        spares to reinstall."""
        possessions = Possessions(credits=4500, installed_outfits={"utility_1": "cargo_expansion"})
        config = {"label": "Spaceport"}
        screen = LocationScreen(config_data=config, world_width=800, world_height=600, player_possessions=possessions)
        screen.buy_ship("freighter")
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(possessions.owned_outfits, ["cargo_expansion"])

    def test_take_loan_blocked_if_already_taken(self):
        screen = self._make_screen(loans=[{"lender": "X", "principal": 1200}])
        option = {"label": "Take loan", "action": "take_loan"}
        self.assertEqual(screen._option_blocked_reason(option), "already have a loan")

    def test_take_loan_uses_story_json_lender_and_amount(self):
        """Lender name + amount come from story.json's "loan" block (the
        default story: Station Credit Union / 100,000cr), not a hardcoded
        literal - see LocationScreen._loan_terms."""
        screen = self._make_screen()
        screen._apply_dialogue_action("take_loan")
        self.assertEqual(screen.player.possessions.credits, 100_000)
        self.assertEqual(screen.player.possessions.loans,
                         [{"lender": "Station Credit Union", "principal": 100_000}])

    def test_take_loan_with_explicit_amount_overrides_the_default(self):
        """"take_loan:<amount>" grants exactly that many credits, keeping
        the story's configured lender."""
        screen = self._make_screen()
        screen._apply_dialogue_action("take_loan:2500")
        self.assertEqual(screen.player.possessions.credits, 2500)
        self.assertEqual(screen.player.possessions.loans,
                         [{"lender": "Station Credit Union", "principal": 2500}])

    def test_take_loan_sets_the_took_loan_gameplay_flag(self):
        screen = self._make_screen()
        screen._apply_dialogue_action("take_loan")
        self.assertTrue(screen.player.possessions.flags.get("took_loan"))

    def test_navigation_skips_blocked_dialogue_options(self):
        """Regression test: the cursor used to be able to move onto (and
        then Enter-confirm) a dialogue option that was drawn dim/blocked -
        e.g. cycling DOWN past an unaffordable ship onto a second
        unaffordable ship. _next_selectable_option must skip it."""
        screen = self._make_screen(credits=0)
        options = [
            {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"},
            {"label": "Patrol - 3500cr", "action": "buy_ship:patrol"},
            {"label": "Leave"},
        ]
        # Both ships are unaffordable at 0 credits - DOWN from "Leave"
        # should wrap straight back to "Leave" itself, never landing on
        # either blocked option.
        self.assertEqual(screen._next_selectable_option(options, 2, 1), 2)
        # First selectable when nothing is affordable is "Leave" (index 2).
        self.assertEqual(screen._first_selectable_option(options), 2)

    def test_navigation_lands_on_the_one_affordable_option(self):
        screen = self._make_screen(credits=1200)
        options = [
            {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"},
            {"label": "Patrol - 3500cr", "action": "buy_ship:patrol"},
            {"label": "Leave"},
        ]
        self.assertEqual(screen._first_selectable_option(options), 0)
        # DOWN from Shuttle should skip the unaffordable Patrol and land on Leave.
        self.assertEqual(screen._next_selectable_option(options, 0, 1), 2)


class TestSelectableListDisabledNavigation(unittest.TestCase):
    """Test SelectableList.handle_key()'s disabled_fn skip - the same
    "can't navigate onto a disabled entry" fix (used by ExitMenu, now the
    ChoiceDialog exit picker, and the outfitting picker)."""

    def test_skips_disabled_entry_when_moving_down(self):
        selectable = SelectableList(["a", "b", "c"], max_visible=3)
        selectable.selected = 0
        selectable.handle_key(pygame_mock.K_DOWN, disabled_fn=lambda item: "blocked" if item == "b" else None)
        self.assertEqual(selectable.current(), "c")

    def test_skips_disabled_entry_when_moving_up(self):
        selectable = SelectableList(["a", "b", "c"], max_visible=3)
        selectable.selected = 2
        selectable.handle_key(pygame_mock.K_UP, disabled_fn=lambda item: "blocked" if item == "b" else None)
        self.assertEqual(selectable.current(), "a")

    def test_all_disabled_does_not_hang(self):
        selectable = SelectableList(["a", "b"], max_visible=2)
        selectable.selected = 0
        selectable.handle_key(pygame_mock.K_DOWN, disabled_fn=lambda item: "blocked")
        # Never enters an infinite loop - capped at len(items) steps.


class TestSelectableListItemsShrink(unittest.TestCase):
    """Regression test: the save browser crashed (IndexError in current())
    when deleting the last-selected save shrank the list out from under a
    SelectableList whose `selected` index wasn't updated to match - e.g.
    deleting save 3 of 3 left `selected == 2` pointing past the new 2-item
    list. SaveBrowser's existing_saves setter reassigns `.list.items`
    directly (see game/ui/save_browser.py), so the fix has to live in
    SelectableList itself, not in whoever mutates it."""

    def test_current_does_not_crash_when_items_shrink_past_selected(self):
        selectable = SelectableList(["save1", "save2", "save3"], max_visible=5)
        selectable.selected = 2  # "save3" was selected
        selectable.items = ["save1", "save2"]  # save3 deleted - list shrinks
        self.assertEqual(selectable.current(), "save2")
        self.assertEqual(selectable.selected, 1)

    def test_current_returns_none_when_items_becomes_empty(self):
        selectable = SelectableList(["save1"], max_visible=5)
        selectable.selected = 0
        selectable.items = []  # the only save deleted
        self.assertIsNone(selectable.current())

    def test_draw_does_not_crash_when_items_shrink_past_selected(self):
        selectable = SelectableList(["save1", "save2", "save3"], max_visible=5)
        selectable.selected = 2
        selectable.items = ["save1", "save2"]
        selectable.draw(MagicMock(), MagicMock(), 0, 0, 20, 1.0)  # must not raise


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


class TestSaveDialogNewSaveKey(unittest.TestCase):
    """Regression test: pressing N to start a new save emits both a KEYDOWN
    and a TEXTINPUT("n") event in the same pygame frame. handle_input() used
    to process the KEYDOWN (switching into input_mode) and then the
    TEXTINPUT from the very same keypress, appending a stray "n" to the
    pre-populated save name. See game/ui/save_browser.py's _suppress_next_text."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_pressing_n_does_not_append_n_to_save_name(self):
        dialog = SaveBrowser("save", pilot_name="Test")
        dialog.list.items = ["existing_save"]
        dialog.input_mode = False
        name_before = dialog.save_name

        events = [
            self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_n),
            self._event(pygame_mock.TEXTINPUT, text="n"),
        ]
        dialog.handle_input(events)

        self.assertTrue(dialog.input_mode)
        self.assertEqual(dialog.save_name, name_before)

    def test_textinput_still_works_after_the_suppressed_one(self):
        dialog = SaveBrowser("save", pilot_name="Test")
        dialog.list.items = ["existing_save"]
        dialog.input_mode = False

        dialog.handle_input([
            self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_n),
            self._event(pygame_mock.TEXTINPUT, text="n"),
        ])
        name_after_n = dialog.save_name
        dialog.handle_input([self._event(pygame_mock.TEXTINPUT, text="x")])

        self.assertEqual(dialog.save_name, name_after_n + "x")


class TestSaveBrowserContract(unittest.TestCase):
    """The (action, payload) tuples main.py's load/pause branches switch on."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_load_mode_actions(self):
        b = SaveBrowser("load")
        b.list.items = ["save_a.json", "save_b.json"]
        self.assertEqual(b.handle_input([self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_RETURN)]), ("load", "save_a.json"))
        self.assertEqual(b.handle_input([self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_d)]), ("delete", "save_a.json"))
        self.assertEqual(b.handle_input([self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_ESCAPE)]), ("cancel", None))

    def test_save_mode_overwrite_vs_new(self):
        b = SaveBrowser("save", pilot_name="Kai")
        b.list.items = ["save_old.json"]
        b.input_mode = False
        self.assertEqual(b.handle_input([self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_RETURN)]), ("save", "save_old.json"))
        # N drops into text entry; Enter there returns the typed name.
        b.handle_input([self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_n)])
        self.assertTrue(b.input_mode)
        self.assertEqual(b.handle_input([self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_RETURN)]), ("save", b.save_name))

    def test_load_mode_has_no_new_save_key(self):
        b = SaveBrowser("load")
        b.list.items = ["save_a.json"]
        b.handle_input([self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_n)])
        self.assertFalse(b.input_mode)


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

    def test_sub_step_frames_accumulate_then_catch_up(self):
        """Two back-to-back 10 ms frames (< 1/60 s each) run 0 then 1 step;
        the leftover from the first isn't lost."""
        acc, n = utils.advance_accumulator(0.0, 0.010)
        self.assertEqual(n, 0)
        self.assertAlmostEqual(acc, 0.010, places=9)
        acc, n = utils.advance_accumulator(acc, 0.010)
        self.assertEqual(n, 1)
        self.assertAlmostEqual(acc, 0.020 - self.STEP, places=9)

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
        landable) from inside a sim step, step_world() must surface it so
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


class TestStationInteriorLayout(unittest.TestCase):
    """The default story's station interiors are each one connected polygon
    area with a single ship portal (the dormitory/corridor/concourse/
    spaceport/loan_office portal chain was collapsed - see
    docs/BACKLOG.md). Guards the authored floor plans: every NPC spawns on
    the walkable area, and a visiting pilot can path clear across it."""

    def _interior(self, system_id, landable_attr, key="default"):
        system = utils.load_json(f"config/stories/default/systems/{system_id}.json")
        game_screen = SpaceScreen(system, pilot_name="Test", story="default", system_id=system_id)
        return game_screen.get_interior_screen(getattr(game_screen, landable_attr), key)

    def test_alpha_station_is_one_interior_with_a_single_ship_portal(self):
        interior = self._interior("sol_alpha", "station")
        self.assertEqual(len(interior.portals), 1)
        self.assertTrue(interior.portals[0]["return_to_ship"])
        self.assertEqual(interior.get_exit_options(), ["ship"])

    def test_every_authored_interior_spawns_its_npcs_inside_the_walkable_area(self):
        for system_id, attr, key in [
            ("sol_alpha", "station", "default"),
            ("sol_alpha", "moon", "city"),
            ("keplers_reach", "station", "default"),
            ("keplers_reach", "moon", "city"),
        ]:
            interior = self._interior(system_id, attr, key)
            for character in interior.npcs:
                person = character.person
                self.assertTrue(
                    interior.can_move_to(person.x, person.y),
                    f"{system_id}/{key}: {person.name} at ({person.x},{person.y}) is outside every room",
                )

    def test_a_pilot_can_path_from_the_ship_portal_across_alpha_station(self):
        interior = self._interior("sol_alpha", "station")
        start = (interior.portals[0]["x"], interior.portals[0]["y"])
        bram = next(c.person for c in interior.npcs if c.person.name == "Bram Solise")
        goal = (bram.x, bram.y)
        path = interior.plan_path(start, goal)
        self.assertEqual(path[-1], goal)
        prev = start
        for point in path:
            steps = max(1, int(math.hypot(point[0] - prev[0], point[1] - prev[1]) / 6))
            for i in range(steps + 1):
                t = i / steps
                x, y = prev[0] + (point[0] - prev[0]) * t, prev[1] + (point[1] - prev[1]) * t
                self.assertTrue(interior.can_move_to(x, y), f"path leaves the walkable area at ({x:.0f},{y:.0f})")
            prev = point

    def test_old_station_save_key_resumes_at_the_ship_entry_interior(self):
        """An old save recorded station_location="dormitory" etc.; those
        keys are gone now. The load path never trusts that key - it
        re-derives the ship-entry room (Landable.get_ship_entry_key) and
        arrive_from("ship")s, so the player lands at the dock portal
        regardless of what the save said or where it left their body."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        self.assertIsNone(game_screen.get_interior_screen(game_screen.station, "dormitory"))
        key = game_screen.station.get_ship_entry_key()
        self.assertEqual(key, "default")
        interior = game_screen.get_interior_screen(game_screen.station, key)
        interior.restore_state({"player": {"x": 12345, "y": 999}, "possessions": {}})
        interior.arrive_from("ship")
        portal = interior.portal_for("ship")
        self.assertEqual((interior.player.x, interior.player.y), (portal["x"], portal["y"]))
        self.assertTrue(interior.can_move_to(interior.player.x, interior.player.y))


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


class TestSpaceScreenAudioCues(unittest.TestCase):
    """The two extra space-view SFX hooks: "confirm" on engaging autopilot,
    "blip" on changing/cycling the target. Exercised against the default
    story's real config, like TestSpaceScreenHailing."""

    def test_engaging_autopilot_plays_confirm(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.target_mode_index = TARGET_MODES.index("LANDABLES")
        game_screen.current_target = 0
        ev = SimpleNamespace(type=pygame_mock.KEYDOWN, key=pygame_mock.K_SPACE, mod=0)
        with patch("game.screens.space_screen.sound_board") as mock_board:
            game_screen.handle_input([ev])
            mock_board.play.assert_any_call("confirm")
        self.assertTrue(game_screen.player.autopilot_active)

    def test_cycling_target_mode_plays_blip(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        with patch("game.screens.space_screen.sound_board") as mock_board:
            game_screen._cycle_target_mode()
            mock_board.play.assert_called_once_with("blip")


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


if __name__ == "__main__":
    unittest.main()
