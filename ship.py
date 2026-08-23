"""Base ship class with physics and autopilot."""
import pygame
import math
from constants import DARK_GRAY, YELLOW, GAME_WIDTH, GAME_HEIGHT
from utils import get_scale, to_screen


class Ship:
    """Base ship class with physics and autopilot."""
    def __init__(self, x, y, space_drag=0):
        self.x = x
        self.y = y
        self.angle = 0
        self.velocity_x = 0
        self.velocity_y = 0
        self.thrust = 0
        self.max_thrust = 0.3
        self.max_velocity = 4.0
        self.rotation_speed = 5
        self.autopilot_active = False
        self.autopilot_target = None
        self.space_drag = space_drag

    def draw(self, surface, ship_size=15, color=DARK_GRAY):
        """Draw ship as rotated polygon with thrust flame."""
        scale = get_scale()
        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        local_points = [
            (0, -ship_size),
            (-ship_size * 0.6, ship_size * 0.6),
            (ship_size * 0.6, ship_size * 0.6),
        ]

        points = []
        for lx, ly in local_points:
            rotated_x = lx * cos_a - ly * sin_a
            rotated_y = lx * sin_a + ly * cos_a
            points.append(to_screen(self.x + rotated_x, self.y + rotated_y))

        pygame.draw.polygon(surface, color, points)

        if self.thrust > 0.05:
            flame_length = self.thrust * 30
            mid_back_x = (local_points[1][0] + local_points[2][0]) / 2
            mid_back_y = (local_points[1][1] + local_points[2][1]) / 2
            back_x = self.x + (mid_back_x * cos_a - mid_back_y * sin_a)
            back_y = self.y + (mid_back_x * sin_a + mid_back_y * cos_a)
            flame_x = back_x - sin_a * flame_length
            flame_y = back_y + cos_a * flame_length
            pygame.draw.line(surface, YELLOW, to_screen(back_x, back_y), to_screen(flame_x, flame_y), max(1, int(2 * scale)))

    def wrap_position(self):
        """Wrap position at screen edges (torus topology)."""
        if self.x < 0:
            self.x = GAME_WIDTH
        elif self.x > GAME_WIDTH:
            self.x = 0
        if self.y < 0:
            self.y = GAME_HEIGHT
        elif self.y > GAME_HEIGHT:
            self.y = 0

    def turn_left(self):
        """Rotate ship left."""
        self.angle = (self.angle - self.rotation_speed) % 360

    def turn_right(self):
        """Rotate ship right."""
        self.angle = (self.angle + self.rotation_speed) % 360

    def increase_thrust(self, step=0.02):
        """Apply thrust in current direction."""
        self.thrust = min(self.thrust + step, self.max_thrust)

    def decrease_thrust(self, step=0.02):
        """Reduce thrust (coast to stop)."""
        self.thrust = max(self.thrust - step, 0)

    def release_thrust(self):
        """Release thrust immediately (no gradual coast)."""
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
        self.update_autopilot()

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

    def update_autopilot(self):
        """Update autopilot - apply thrust perpendicular to velocity toward target until velocity points at target."""
        if not self.autopilot_active or not self.autopilot_target:
            return

        target = self.autopilot_target

        # Distance vector from ship to target
        dx = target.x - self.x
        dy = target.y - self.y

        # Check if velocity is already pointing toward target using dot product
        dot_product = dx * self.velocity_x + dy * self.velocity_y

        if dot_product > 0:
            # Velocity is pointing toward target, disengage autopilot
            self.autopilot_active = False
            self.release_thrust()
            return

        # Calculate most efficient thrust direction: perpendicular to velocity, toward target
        self._autopilot_redirect_velocity(dx, dy)

    def _autopilot_redirect_velocity(self, target_dx, target_dy):
        """Apply thrust perpendicular to velocity to efficiently redirect it toward target.

        Most efficient direction: perpendicular to current velocity, toward target.
        """
        # Current velocity vector
        vx = self.velocity_x
        vy = self.velocity_y

        # Speed to determine which perpendicular direction
        speed_sq = vx * vx + vy * vy

        if speed_sq < 0.01:
            # Nearly stopped, point toward target and thrust
            target_angle = math.atan2(target_dx, -target_dy)
            target_angle_deg = math.degrees(target_angle)
        else:
            # Calculate perpendicular directions to velocity (left and right)
            # Perpendicular to (vx, vy) is (-vy, vx) and (vy, -vx)
            perp_left_x = -vy
            perp_left_y = vx
            perp_right_x = vy
            perp_right_y = -vx

            # Check which perpendicular direction is more aligned with target
            dot_left = target_dx * perp_left_x + target_dy * perp_left_y
            dot_right = target_dx * perp_right_x + target_dy * perp_right_y

            # Choose the perpendicular that points more toward target
            if dot_left > dot_right:
                target_angle = math.atan2(perp_left_x, -perp_left_y)
            else:
                target_angle = math.atan2(perp_right_x, -perp_right_y)

            target_angle_deg = math.degrees(target_angle)

        # Rotate ship to face optimal thrust direction
        current_angle = self.angle % 360
        target_angle_norm = target_angle_deg % 360

        angle_diff = target_angle_norm - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Rotate toward optimal direction
        if angle_diff < -self.rotation_speed:
            self.turn_left()
        elif angle_diff > self.rotation_speed:
            self.turn_right()

        # If aligned with optimal direction, apply thrust
        aligned = abs(angle_diff) < 10
        if aligned:
            self.increase_thrust(step=0.01)
        else:
            self.release_thrust()
