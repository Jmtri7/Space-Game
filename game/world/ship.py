"""Base ship class with physics and rendering. Autopilot is a separate component."""
import pygame
import math
from game.constants import DARK_GRAY, YELLOW
from game.utils import get_scale, to_screen
from game.world.world_object import WorldObject
from game.world.autopilot import Autopilot


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

    @property
    def size(self):
        """World-space radius draw() actually renders at - graphics-provided
        size if this ship has graphics, else the same 15-unit default draw()
        falls back to. Mirrors draw()'s own ship_size resolution so callers
        (e.g. target brackets) can size themselves to fit without
        duplicating that fallback logic."""
        return self.graphics.get("size", 15) if self.graphics else 15

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

        # Get local points: an explicit "local_points" list (fractions of
        # ship_size) always wins, for fully custom silhouettes; otherwise
        # fall back to a named built-in shape.
        local_points = self._get_shape_points(ship_size, shape if self.graphics else "triangle")
        outline_color = tuple(self.graphics.get("outline_color", (20, 18, 25)))
        self._draw_rotated_polygon(surface, local_points, self.angle, color, outline_color=outline_color)
        self._draw_windows(surface, ship_size)

        if self.thrust > 0.05:
            self._draw_thrusters(surface, ship_size)

    def _draw_windows(self, surface, ship_size):
        """Draw small viewport/window details at each configured window point.

        Window positions are (x, y) fractions of ship_size, same local space as
        thrusters. Ships with no "windows" entry simply draw none (unchanged look).
        """
        window_points = self.graphics.get("windows", [])
        if not window_points:
            return

        window_color = tuple(self.graphics.get("window_color", (200, 230, 255)))
        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        radius = max(1, int(round(ship_size * 0.12 * get_scale())))

        for wx, wy in window_points:
            lx, ly = wx * ship_size, wy * ship_size
            world_x = self.x + (lx * cos_a - ly * sin_a)
            world_y = self.y + (lx * sin_a + ly * cos_a)
            pygame.draw.circle(surface, window_color, to_screen(world_x, world_y), radius)

    def _draw_thrusters(self, surface, ship_size):
        """Draw a triangular flame, pointed backward, at each thruster mount point.

        Thruster positions are given as (x, y) fractions of ship_size, in the same
        local space as _get_shape_points (0,0 = center, +y = toward the back).
        Ships without a "thrusters" entry fall back to a single back-center mount.
        The triangle's base sits at the hull mount point; its apex points backward
        (opposite the ship's facing), like a small exhaust cone. Width (fraction of
        ship_size) and max length (world units, at full thrust) are both tunable
        per ship via the "thruster_width"/"thruster_length" graphics fields.
        """
        thruster_points = self.graphics.get("thrusters", [(0, 0.6)])
        thruster_width = self.graphics.get("thruster_width", 0.15)
        thruster_length = self.graphics.get("thruster_length", 38)
        thrust_color = tuple(self.graphics.get("thrust_color", YELLOW))

        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        flame_length = self.thrust * thruster_length
        half_width = max(2, ship_size * thruster_width)

        # World-space unit vectors for this ship's current heading: "backward"
        # (opposite the nose) and "right" (perpendicular, for the flame's base).
        back_x_dir, back_y_dir = -sin_a, cos_a
        right_x_dir, right_y_dir = cos_a, sin_a

        for tx, ty in thruster_points:
            lx, ly = tx * ship_size, ty * ship_size
            mount_x = self.x + (lx * cos_a - ly * sin_a)
            mount_y = self.y + (lx * sin_a + ly * cos_a)

            tip_x = mount_x + back_x_dir * flame_length
            tip_y = mount_y + back_y_dir * flame_length
            base_left = to_screen(mount_x + right_x_dir * half_width, mount_y + right_y_dir * half_width)
            base_right = to_screen(mount_x - right_x_dir * half_width, mount_y - right_y_dir * half_width)

            pygame.draw.polygon(surface, thrust_color, [to_screen(tip_x, tip_y), base_left, base_right])

    def _get_shape_points(self, size, shape):
        """Get local points for ship shape.

        If the graphics asset defines "local_points" (a list of (x, y)
        fractions of size, same local space as thrusters/windows), that
        fully custom silhouette is used instead of a named built-in shape -
        lets any ship type define its own hull outline purely via config.
        """
        if "local_points" in self.graphics:
            return [(lx * size, ly * size) for lx, ly in self.graphics["local_points"]]

        if shape == "rectangle":
            return [
                (-size * 0.5, -size * 0.6),
                (size * 0.5, -size * 0.6),
                (size * 0.5, size * 0.6),
                (-size * 0.5, size * 0.6),
            ]
        elif shape == "diamond":
            return [
                (0, -size),
                (-size * 0.5, 0),
                (0, size * 0.7),
                (size * 0.5, 0),
            ]
        elif shape == "long_rectangle":
            return [
                (-size * 0.3, -size),
                (size * 0.3, -size),
                (size * 0.3, size),
                (-size * 0.3, size),
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

    def park(self):
        """Come to a full stop and release thrust - landed/docked, not just
        autopilot-disengaged, so the ship doesn't keep drifting."""
        self.velocity_x = 0
        self.velocity_y = 0
        self.release_thrust()

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
