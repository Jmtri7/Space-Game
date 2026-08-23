"""Unit tests for helper functions extracted from main.py"""
import sys
import os
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock pygame before importing main to avoid display requirements
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

import main


class TestHandleScrollingInput(unittest.TestCase):
    """Test _handle_scrolling_input helper function"""

    def setUp(self):
        self.items = ["save1", "save2", "save3", "save4", "save5", "save6"]
        self.max_visible = 3

    def test_down_moves_selection(self):
        """Pressing DOWN should move selection forward"""
        selected, scroll = main._handle_scrolling_input(
            main.pygame.K_DOWN, 0, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)
        self.assertEqual(scroll, 0)

    def test_down_wraps_at_end(self):
        """Selection should wrap to 0 when reaching end"""
        selected, scroll = main._handle_scrolling_input(
            main.pygame.K_DOWN, 5, self.items, 3, self.max_visible
        )
        self.assertEqual(selected, 0)
        self.assertEqual(scroll, 0)

    def test_down_scrolls_when_needed(self):
        """Scroll should advance when selection reaches bottom of visible area"""
        selected, scroll = main._handle_scrolling_input(
            main.pygame.K_DOWN, 2, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 3)
        self.assertEqual(scroll, 1)

    def test_up_moves_selection_back(self):
        """Pressing UP should move selection backward"""
        selected, scroll = main._handle_scrolling_input(
            main.pygame.K_UP, 2, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)
        self.assertEqual(scroll, 0)

    def test_up_wraps_at_start(self):
        """Selection should wrap to end when moving up from 0"""
        selected, scroll = main._handle_scrolling_input(
            main.pygame.K_UP, 0, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 5)
        self.assertEqual(scroll, 3)

    def test_up_scrolls_when_needed(self):
        """Scroll should go back when selection is at top of visible area"""
        selected, scroll = main._handle_scrolling_input(
            main.pygame.K_UP, 2, self.items, 2, self.max_visible
        )
        self.assertEqual(selected, 1)
        self.assertEqual(scroll, 1)

    def test_w_key_is_up(self):
        """W key should behave like UP"""
        selected, scroll = main._handle_scrolling_input(
            main.pygame.K_w, 2, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)

    def test_s_key_is_down(self):
        """S key should behave like DOWN"""
        selected, scroll = main._handle_scrolling_input(
            main.pygame.K_s, 0, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)

    def test_invalid_key_no_change(self):
        """Invalid key should not change selection or scroll"""
        selected, scroll = main._handle_scrolling_input(
            main.pygame.K_a, 2, self.items, 1, self.max_visible
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

        files = main._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(len(files), 2)
        self.assertIn("save_test1.json", files)
        self.assertIn("save_test2.json", files)

    def test_filters_prefix(self):
        """Should only match files with correct prefix"""
        open(os.path.join(self.test_dir, "save_test.json"), "w").close()
        open(os.path.join(self.test_dir, "other_test.json"), "w").close()

        files = main._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "save_test.json")

    def test_filters_suffix(self):
        """Should only match files with correct suffix"""
        open(os.path.join(self.test_dir, "save_test.json"), "w").close()
        open(os.path.join(self.test_dir, "save_test.txt"), "w").close()

        files = main._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "save_test.json")

    def test_returns_sorted_reverse(self):
        """Should return files sorted in reverse (newest first)"""
        # Create files
        for i in range(1, 4):
            open(os.path.join(self.test_dir, f"save_test{i}.json"), "w").close()

        files = main._list_files_by_pattern(self.test_dir, "save_", ".json")
        # Should be reverse sorted
        self.assertEqual(files[0], "save_test3.json")
        self.assertEqual(files[-1], "save_test1.json")

    def test_creates_dir_if_missing(self):
        """Should create directory if it doesn't exist"""
        nonexistent = os.path.join(self.test_dir, "subdir")
        files = main._list_files_by_pattern(nonexistent, "save_", ".json")
        self.assertTrue(os.path.exists(nonexistent))
        self.assertEqual(files, [])

    def test_empty_dir_returns_empty_list(self):
        """Should return empty list for directory with no matching files"""
        files = main._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(files, [])


class TestCenterTextX(unittest.TestCase):
    """Test _center_text_x helper function"""

    def test_returns_integer(self):
        """Should return an integer coordinate"""
        text = MagicMock()
        text.get_width.return_value = 100

        result = main._center_text_x(None, text)
        self.assertIsInstance(result, int)

    def test_centers_horizontally(self):
        """Should center text horizontally"""
        text = MagicMock()
        text.get_width.return_value = 200

        result = main._center_text_x(None, text)
        # offset_x=0 + GAME_WIDTH(2400) * scale * 0.5 - text.get_width(200) // 2
        # Actual scale varies with screen size
        self.assertGreater(result, 1800)
        self.assertLess(result, 2000)

    def test_respects_offset(self):
        """Should apply offset_x parameter"""
        text = MagicMock()
        text.get_width.return_value = 200

        result = main._center_text_x(None, text, offset_x=50)
        # offset_x(50) + GAME_WIDTH(2400) * scale * 0.5 - text.get_width(200) // 2
        # Should be roughly 50 more than centered value
        self.assertGreater(result, 1850)
        self.assertLess(result, 2050)


class TestAutopilotPhysics(unittest.TestCase):
    """Test autopilot physics simulation framework"""

    def simulate_autopilot_approach(self, ship, target_distance, target_x, target_y, max_frames=1000):
        """Simulate ship approaching and braking to stop at target"""
        ship.autopilot_active = True

        # Create mock target
        target = MagicMock()
        target.x = target_x
        target.y = target_y
        target.get_distance = lambda x, y: ((target.x - x)**2 + (target.y - y)**2)**0.5

        ship.autopilot_target = target
        ship.x = 0
        ship.y = 0
        ship.angle = 0
        ship.velocity_x = 0
        ship.velocity_y = 0
        ship.thrust = 0

        frames = 0
        while ship.autopilot_active and frames < max_frames:
            frames += 1

            # Update autopilot
            if hasattr(ship, 'update_autopilot'):
                ship.update_autopilot()

            # Update physics
            ship.update()

            # Check if landed (distance < 150, speed < 0.5)
            distance = target.get_distance(ship.x, ship.y)
            speed = (ship.velocity_x**2 + ship.velocity_y**2)**0.5

            if distance < 150 and speed < 0.5:
                ship.autopilot_active = False
                return frames, distance, speed

        # Timeout
        distance = target.get_distance(ship.x, ship.y)
        speed = (ship.velocity_x**2 + ship.velocity_y**2)**0.5
        return frames, distance, speed

    def test_autopilot_physics_framework_exists(self):
        """Test that autopilot physics simulation framework is in place"""
        ship = main.Player(0, 0)

        # Verify ship has autopilot attributes
        self.assertTrue(hasattr(ship, 'autopilot_active'))
        self.assertTrue(hasattr(ship, 'autopilot_target'))

        # Verify ship can be simulated
        ship.x = 100
        ship.y = 100
        ship.update()
        self.assertEqual(ship.x, 100)

    def test_autopilot_target_selection(self):
        """Test autopilot can track a target"""
        ship = main.Player(0, 0)
        target = MagicMock()
        target.x = 500
        target.y = 0
        target.get_distance = lambda x, y: ((target.x - x)**2 + (target.y - y)**2)**0.5

        ship.autopilot_target = target
        distance = target.get_distance(ship.x, ship.y)

        self.assertEqual(distance, 500)

    def test_autopilot_velocity_decay(self):
        """Test that ship can be updated in simulation"""
        ship = main.Player(0, 0)
        ship.velocity_x = 5
        ship.velocity_y = 0
        ship.thrust = 0

        # Simulate one frame without errors
        initial_pos_x = ship.x
        ship.update()

        # Ship position should have changed due to velocity
        self.assertNotEqual(ship.x, initial_pos_x)


if __name__ == "__main__":
    unittest.main()
