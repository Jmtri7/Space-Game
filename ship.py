"""Base ship class with physics and rendering. Autopilot is a separate component."""
import pygame
import math
from constants import DARK_GRAY, YELLOW
from utils import get_scale, to_screen
from world_object import WorldObject
from autopilot import Autopilot


class Ship(WorldObject):
    """Base ship class with physics, rendering, and manual controls."""
    def __init__(self, x, y, space_drag=0, graphics=None):
        super().__init__(x, y, graphics=graphics)
        self.angle = 0
        self.velocity_x = 0
        self.velocity_y = 0
        self.thrust = 0
        self.acceleration_magnitude = 0.1
        self.max_velocity = 4.0
        self.rotation_speed = 5
        self.space_drag = space_drag
        self.autopilot = Autopilot(self)

    # --- Backward-compatible views onto the autopilot's state ---
    @property
    def autopilot_active(self):
        return self.autopilot.active

    @autopilot_active.setter
    def autopilot_active(self, value):
        self.autopilot.active = value

    @property
    def autopilot_target(self):
        return self.autopilot.target

    @autopilot_target.setter
    def autopilot_target(self, value):
        self.autopilot.target = value

    def engage_seek(self, target):
        """Engage autopilot to approach/land on `target`."""
        self.autopilot.engage_seek(target)

    def engage_orbit(self, center_x, center_y, radius):
        """Engage autopilot to continuously circle (center_x, center_y) at `radius`."""
        self.autopilot.engage_orbit(center_x, center_y, radius)

    def draw(self, surface, ship_size=None, color=None):
        """Draw ship using graphics asset, with fallback to defaults."""
        # Use graphics asset if available, otherwise use parameters
        if self.graphics:
            ship_size = self.graphics.get("size", ship_size or 15)
            color = tuple(self.graphics.get("color", color or DARK_GRAY))
            shape = self.graphics.get("shape", "triangle")
        else:
            ship_size = ship_size or 15
            color = color or DARK_GRAY

        scale = get_scale()

        # Get local points based on shape
        local_points = self._get_shape_points(ship_size, shape if self.graphics else "triangle")
        self._draw_rotated_polygon(surface, local_points, self.angle, color)

        if self.thrust > 0.05:
            self._draw_thrusters(surface, ship_size, scale)

    def _draw_thrusters(self, surface, ship_size, scale):
        """Draw a flame at each thruster mount point defined by the ship's graphics.

        Thruster positions are given as (x, y) fractions of ship_size, in the same
        local space as _get_shape_points (0,0 = center, +y = toward the back).
        Ships without a "thrusters" entry fall back to a single back-center mount.
        """
        thruster_points = self.graphics.get("thrusters", [(0, 0.6)])

        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        flame_length = self.thrust * 30
        thickness = max(2, int(round(4 * scale)))

        for tx, ty in thruster_points:
            lx, ly = tx * ship_size, ty * ship_size
            back_x = self.x + (lx * cos_a - ly * sin_a)
            back_y = self.y + (lx * sin_a + ly * cos_a)
            flame_x = back_x - sin_a * flame_length
            flame_y = back_y + cos_a * flame_length
            pygame.draw.line(surface, YELLOW, to_screen(back_x, back_y), to_screen(flame_x, flame_y), thickness)

    def _get_shape_points(self, size, shape):
        """Get local points for ship shape."""
        if shape == "rectangle":
            return [
                (0, -size * 0.7),
                (-size * 0.4, size * 0.7),
                (0, size * 0.5),
                (size * 0.4, size * 0.7),
            ]
        elif shape == "diamond":
            return [
                (0, -size),
                (-size * 0.5, 0),
                (0, size * 0.7),
                (size * 0.5, 0),
            ]
        else:  # triangle (default)
            return [
                (0, -size),
                (-size * 0.6, size * 0.6),
                (size * 0.6, size * 0.6),
            ]

    def turn_left(self):
        """Rotate ship left."""
        self.angle = (self.angle - self.rotation_speed) % 360

    def turn_right(self):
        """Rotate ship right."""
        self.angle = (self.angle + self.rotation_speed) % 360

    def increase_thrust(self, step=None):
        """Apply full thrust in current direction (constant acceleration)."""
        self.thrust = self.acceleration_magnitude

    def decrease_thrust(self, step=None):
        """Reduce thrust (coast to stop)."""
        self.thrust = 0

    def release_thrust(self):
        """Release thrust immediately."""
        self.thrust = 0

    def point_to_reverse_velocity(self):
        """Rotate ship to point opposite current velocity direction."""
        if self.velocity_x == 0 and self.velocity_y == 0:
            return  # No velocity, nothing to reverse
        # Calculate velocity angle
        velocity_angle = math.degrees(math.atan2(self.velocity_x, -self.velocity_y))
        # Point opposite: add 180 degrees
        target_angle = (velocity_angle + 180) % 360
        # Rotate ship toward target angle (using same rotation speed as normal rotation)
        current_angle = self.angle % 360
        angle_diff = target_angle - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360
        # Rotate one step toward target
        rotation_step = self.rotation_speed
        if angle_diff < -rotation_step:
            self.angle = (self.angle - rotation_step) % 360
        elif angle_diff > rotation_step:
            self.angle = (self.angle + rotation_step) % 360
        else:
            self.angle = target_angle

    def update(self):
        """Base physics update: apply thrust, velocity cap, and movement."""
        try:
            self.autopilot.update()
        except Exception as e:
            import traceback
            print(f"ERROR in autopilot update: {e}")
            traceback.print_exc()
            self.autopilot.disengage()

        rad = math.radians(self.angle)
        if self.thrust > 0.01:
            self.velocity_x += math.sin(rad) * self.thrust
            self.velocity_y -= math.cos(rad) * self.thrust

            speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)
            if speed > self.max_velocity:
                scale = self.max_velocity / speed
                self.velocity_x *= scale
                self.velocity_y *= scale

        # Apply space system drag
        if self.space_drag > 0:
            self.velocity_x *= self.space_drag
            self.velocity_y *= self.space_drag

        self.x += self.velocity_x
        self.y += self.velocity_y

        self.wrap_position()

    def predict_landing_trajectory(self, target, max_frames=500, sample_rate=5):
        """Predict landing trajectory and return waypoints for visualization.

        Returns list of (x, y) positions sampled every sample_rate frames.
        """
        return self.autopilot.predict_trajectory(target, max_frames, sample_rate)

    def predict_landing_position(self, target, max_frames=500):
        """Predict where ship will stop given current autopilot trajectory.

        Returns (final_x, final_y, distance_from_target).
        """
        return self.autopilot.predict_position(target, max_frames)
