"""Unit tests for game_physics module - pure physics calculations"""
import unittest
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import game_physics


class TestUpdateVelocity(unittest.TestCase):
    """Test velocity update with thrust and drag"""

    def test_thrust_accelerates(self):
        """Thrust should increase velocity"""
        vx, vy = game_physics.update_velocity(0, 0, thrust=0.3, angle=90)
        # At 90 degrees: vx = sin(90°) * 0.3 = 0.3, vy = -cos(90°) * 0.3 = 0
        self.assertGreater(abs(vx), 0.1)

    def test_no_thrust_applies_drag(self):
        """Without thrust, velocity should decrease via drag"""
        vx_new, vy_new = game_physics.update_velocity(1.0, 1.0, thrust=0, angle=0)
        # Both should be multiplied by drag (0.98)
        self.assertAlmostEqual(vx_new, 0.98, places=2)
        self.assertAlmostEqual(vy_new, 0.98, places=2)

    def test_velocity_capped(self):
        """Velocity should not exceed max_velocity"""
        vx, vy = game_physics.update_velocity(10, 0, thrust=0.3, angle=0, max_velocity=4.0)
        speed = math.sqrt(vx ** 2 + vy ** 2)
        self.assertLessEqual(speed, 4.0)

    def test_zero_thrust_zero_velocity_stays_zero(self):
        """No thrust, no velocity should result in zero"""
        vx, vy = game_physics.update_velocity(0, 0, thrust=0, angle=0)
        self.assertAlmostEqual(vx, 0)
        self.assertAlmostEqual(vy, 0)


class TestUpdatePosition(unittest.TestCase):
    """Test position update based on velocity"""

    def test_position_moves_with_velocity(self):
        """Position should change by velocity amount"""
        x, y = game_physics.update_position(100, 200, velocity_x=10, velocity_y=-5)
        self.assertEqual(x, 110)
        self.assertEqual(y, 195)

    def test_zero_velocity_no_movement(self):
        """Zero velocity should not change position"""
        x, y = game_physics.update_position(50, 50, velocity_x=0, velocity_y=0)
        self.assertEqual(x, 50)
        self.assertEqual(y, 50)


class TestWrapPosition(unittest.TestCase):
    """Test screen wrapping at boundaries"""

    def test_wrap_left_edge(self):
        """X < 0 should wrap to width"""
        x, y = game_physics.wrap_position(-10, 300)
        self.assertEqual(x, 800)
        self.assertEqual(y, 300)

    def test_wrap_right_edge(self):
        """X > width should wrap to 0"""
        x, y = game_physics.wrap_position(810, 300)
        self.assertEqual(x, 0)
        self.assertEqual(y, 300)

    def test_wrap_top_edge(self):
        """Y < 0 should wrap to height"""
        x, y = game_physics.wrap_position(400, -10)
        self.assertEqual(x, 400)
        self.assertEqual(y, 600)

    def test_wrap_bottom_edge(self):
        """Y > height should wrap to 0"""
        x, y = game_physics.wrap_position(400, 610)
        self.assertEqual(x, 400)
        self.assertEqual(y, 0)

    def test_no_wrap_in_bounds(self):
        """In-bounds positions should not change"""
        x, y = game_physics.wrap_position(400, 300)
        self.assertEqual(x, 400)
        self.assertEqual(y, 300)


class TestUpdateThrust(unittest.TestCase):
    """Test thrust control"""

    def test_accelerate_increases_thrust(self):
        """Accelerating should increase thrust"""
        thrust = game_physics.update_thrust(0.1, keys_accelerating=True, keys_decelerating=False)
        self.assertGreater(thrust, 0.1)

    def test_decelerate_decreases_thrust(self):
        """Not accelerating should decrease thrust"""
        thrust = game_physics.update_thrust(0.2, keys_accelerating=False, keys_decelerating=False)
        self.assertLess(thrust, 0.2)

    def test_thrust_capped_at_max(self):
        """Thrust should not exceed max"""
        thrust = game_physics.update_thrust(0.28, keys_accelerating=True, keys_decelerating=False, acceleration_magnitude=0.3)
        self.assertLessEqual(thrust, 0.3)

    def test_thrust_cannot_go_below_zero(self):
        """Thrust should not go negative"""
        thrust = game_physics.update_thrust(0.01, keys_accelerating=False, keys_decelerating=False, accel=0.02)
        self.assertGreaterEqual(thrust, 0)


class TestUpdateAngle(unittest.TestCase):
    """Test rotation/angle updates"""

    def test_left_rotation(self):
        """Turning left should decrease angle"""
        angle = game_physics.update_angle(90, keys_left=True, keys_right=False)
        self.assertEqual(angle, 85)

    def test_right_rotation(self):
        """Turning right should increase angle"""
        angle = game_physics.update_angle(90, keys_left=False, keys_right=True)
        self.assertEqual(angle, 95)

    def test_angle_wraps_360(self):
        """Angle > 360 should wrap"""
        angle = game_physics.update_angle(358, keys_left=False, keys_right=True)
        self.assertEqual(angle, 3)

    def test_angle_wraps_negative(self):
        """Angle < 0 should wrap"""
        angle = game_physics.update_angle(2, keys_left=True, keys_right=False)
        self.assertEqual(angle, 357)

    def test_both_directions_cancel(self):
        """Turning left and right simultaneously should have no effect"""
        angle = game_physics.update_angle(90, keys_left=True, keys_right=True)
        self.assertEqual(angle, 90)


class TestGetDistance(unittest.TestCase):
    """Test distance calculation"""

    def test_distance_same_point(self):
        """Distance from point to itself should be 0"""
        d = game_physics.get_distance(100, 100, 100, 100)
        self.assertAlmostEqual(d, 0)

    def test_distance_horizontal(self):
        """Horizontal distance"""
        d = game_physics.get_distance(0, 100, 30, 100)
        self.assertAlmostEqual(d, 30)

    def test_distance_vertical(self):
        """Vertical distance"""
        d = game_physics.get_distance(100, 0, 100, 40)
        self.assertAlmostEqual(d, 40)

    def test_distance_diagonal(self):
        """3-4-5 triangle"""
        d = game_physics.get_distance(0, 0, 3, 4)
        self.assertAlmostEqual(d, 5)


class TestCanLand(unittest.TestCase):
    """Test landing condition checks"""

    def test_can_land_within_distance_and_speed(self):
        """Should land when close and slow"""
        can_land = game_physics.can_land(400, 300, 400, 300, distance_threshold=100, speed_threshold=0.5)
        self.assertTrue(can_land)

    def test_cannot_land_too_far(self):
        """Should not land when too far away"""
        can_land = game_physics.can_land(400, 300, 600, 300, distance_threshold=100, speed_threshold=0.5)
        self.assertFalse(can_land)

    def test_cannot_land_too_fast(self):
        """Should not land when moving too fast"""
        can_land = game_physics.can_land(400, 300, 400, 300, distance_threshold=100, speed_threshold=0.5, velocity_x=1.0)
        self.assertFalse(can_land)

    def test_can_land_just_within_threshold(self):
        """Should land just within distance threshold"""
        can_land = game_physics.can_land(0, 0, 99.9, 0, distance_threshold=100, speed_threshold=0.5)
        self.assertTrue(can_land)


class TestRotatePoint(unittest.TestCase):
    """Test point rotation around center"""

    def test_rotate_0_degrees(self):
        """Rotating 0 degrees should not change point"""
        x, y = game_physics.rotate_point(100, 100, 50, 50, angle=0)
        self.assertAlmostEqual(x, 100, places=5)
        self.assertAlmostEqual(y, 100, places=5)

    def test_rotate_90_degrees(self):
        """Rotating 90 degrees around origin"""
        x, y = game_physics.rotate_point(10, 0, 0, 0, angle=90)
        # (10, 0) rotated 90° counter-clockwise = (0, 10)
        self.assertAlmostEqual(x, 0, places=5)
        self.assertAlmostEqual(y, 10, places=5)

    def test_rotate_around_point(self):
        """Rotating around non-origin point"""
        x, y = game_physics.rotate_point(60, 50, 50, 50, angle=90)
        # (60, 50) relative to (50, 50) is (10, 0)
        # Rotated 90° = (0, 10)
        # Back in world: (50, 60)
        self.assertAlmostEqual(x, 50, places=5)
        self.assertAlmostEqual(y, 60, places=5)


if __name__ == "__main__":
    unittest.main()
