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
    """Test autopilot arrives at target with precise position and velocity"""

    def simulate_autopilot_to_landing(self, ship, target_x, target_y, max_frames=2000):
        """Simulate ship autopilot from start to landing, return final state"""
        ship.autopilot_active = True

        # Create mock target with get_distance method
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
        landed = False
        while ship.autopilot_active and frames < max_frames:
            frames += 1

            # Update autopilot control logic
            if hasattr(ship, 'update_autopilot'):
                ship.update_autopilot()

            # Update physics
            ship.update()

            # Check if landed (distance < 150, speed < 0.5)
            distance = target.get_distance(ship.x, ship.y)
            speed = (ship.velocity_x**2 + ship.velocity_y**2)**0.5

            if distance < 150 and speed < 0.5:
                ship.autopilot_active = False
                landed = True
                break

        # Return final state
        distance = target.get_distance(ship.x, ship.y)
        speed = (ship.velocity_x**2 + ship.velocity_y**2)**0.5
        return {
            'landed': landed,
            'frames': frames,
            'distance': distance,
            'speed': speed,
            'x': ship.x,
            'y': ship.y
        }

    def test_autopilot_explorer_lands_precisely(self):
        """Explorer should arrive at target close with low velocity, both simultaneously"""
        ship = main.Player(0, 0)
        ship.max_thrust = 0.3
        ship.max_velocity = 4.0
        ship.drag = 0.98
        ship.rotation_speed = 5

        result = self.simulate_autopilot_to_landing(ship, 500, 0)

        self.assertTrue(result['landed'], f"Autopilot failed to land (frames: {result['frames']})")
        # Verify arrives close to target (< 120 units - precise landing, not just within 150)
        self.assertLess(result['distance'], 120,
                        f"Explorer distance {result['distance']:.1f} - should arrive very close to target")
        # Verify very low velocity at arrival (< 0.5 confirmed by game landing logic)
        self.assertLess(result['speed'], 0.5,
                        f"Explorer velocity {result['speed']:.3f} - should be nearly stopped")
        # Both conditions met simultaneously at landing frame
        self.assertAlmostEqual(result['speed'], 0.4, delta=0.15,
                               msg="Velocity should be precisely controlled at landing")

    def test_autopilot_courier_lands_precisely(self):
        """Fast courier should arrive at target close with low velocity, both simultaneously"""
        ship = main.Player(0, 0)
        ship.max_thrust = 0.5
        ship.max_velocity = 6.5
        ship.drag = 0.99
        ship.rotation_speed = 9

        result = self.simulate_autopilot_to_landing(ship, 400, 0)

        self.assertTrue(result['landed'], f"Autopilot failed to land (frames: {result['frames']})")
        # Verify arrives close to target (< 120 units)
        self.assertLess(result['distance'], 120,
                        f"Courier distance {result['distance']:.1f} - should arrive very close to target")
        # Verify very low velocity at arrival
        self.assertLess(result['speed'], 0.5,
                        f"Courier velocity {result['speed']:.3f} - should be nearly stopped")

    def test_autopilot_hauler_lands_precisely(self):
        """Slow hauler should arrive at target close with low velocity, both simultaneously"""
        ship = main.Player(0, 0)
        ship.max_thrust = 0.15
        ship.max_velocity = 2.5
        ship.drag = 0.95
        ship.rotation_speed = 2

        result = self.simulate_autopilot_to_landing(ship, 300, 0)

        self.assertTrue(result['landed'], f"Autopilot failed to land (frames: {result['frames']})")
        # Verify arrives close to target (< 120 units)
        self.assertLess(result['distance'], 120,
                        f"Hauler distance {result['distance']:.1f} - should arrive very close to target")
        # Verify very low velocity at arrival
        self.assertLess(result['speed'], 0.5,
                        f"Hauler velocity {result['speed']:.3f} - should be nearly stopped")


if __name__ == "__main__":
    unittest.main()
