"""Unit tests for helper functions extracted from main.py"""
import sys
import os
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
pygame_mock.K_w = 119
pygame_mock.K_s = 115
pygame_mock.K_a = 97

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
from game.screens.location_screen import LocationScreen
from game.world.dock_routine import DockRoutine, ROLE_EXIT_PREFERENCE


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
        return SimpleNamespace(pilot={"role": role}, pilot_person=Person(0, 0))

    def test_unconfigured_role_always_returns_to_ship(self):
        """A role with no ROLE_EXIT_PREFERENCE entry falls back to
        DEFAULT_EXIT_PREFERENCE - reboards immediately, exactly like every
        pilot did before connected_locations existed."""
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(get_exit_options=lambda: ["wilderness", "ship"])
        ai_ship = self._make_ai_ship(role="patrol_officer")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_configured_role_prefers_connected_location(self):
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(get_exit_options=lambda: ["wilderness", "ship"])
        ai_ship = self._make_ai_ship(role="freighter_pilot")
        self.assertEqual(ROLE_EXIT_PREFERENCE["freighter_pilot"][0], "wilderness")
        self.assertEqual(routine._choose_exit(ai_ship), "wilderness")

    def test_already_visited_location_is_skipped(self):
        """Regression test: a role preferring both connected locations
        must not pick one it already visited this stop, or it would
        ping-pong between them forever and never reboard."""
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(get_exit_options=lambda: ["city", "ship"])
        routine._visited_this_stop = {"city"}
        ai_ship = self._make_ai_ship(role="freighter_pilot")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_full_stop_visits_every_connected_location_then_reboards(self):
        """End-to-end regression test for the ping-pong bug: a freighter
        pilot landing at a stop with two locations that each connect back
        to the other should visit both once, then reboard - never loop
        forever - using the real phase machine (run()), not a
        reimplementation of it."""
        city_config = {"label": "City", "connected_locations": ["wilderness"], "npcs": []}
        wilderness_config = {"label": "Wilderness", "connected_locations": ["city"], "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={"city": city_config, "wilderness": wilderness_config})

        interior_cache = {}
        def get_interior_screen(landable, key, world_width, world_height):
            cache_key = (id(landable), key)
            if cache_key not in interior_cache:
                config = landable.interiors.get(key)
                if not config:
                    return None
                interior_cache[cache_key] = LocationScreen(config_data=config, world_width=world_width, world_height=world_height)
            return interior_cache[cache_key]

        ai_ship = SimpleNamespace(
            pilot={"role": "freighter_pilot"},
            pilot_person=Person(0, 0),
            pilot_ashore=False,
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
        self.assertFalse(ai_ship.pilot_ashore)


if __name__ == "__main__":
    unittest.main()
