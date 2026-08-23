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
        self.acceleration_magnitude = 0.3
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
        """Update autopilot - unified approach that redirects AND decelerates simultaneously.

        Chooses acceleration direction that:
        1. Points toward target (to redirect velocity)
        2. Points opposite to velocity (to slow down)
        The blend depends on proximity and speed.
        """
        if not self.autopilot_active or not self.autopilot_target:
            return

        target = self.autopilot_target
        distance = target.get_distance(self.x, self.y)
        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        # Step 1: Landing condition check
        landing_distance = self.autopilot_target.landing_distance
        if distance < landing_distance and speed < 0.5:
            self.autopilot_active = False
            self.release_thrust()
            return

        # Step 2: Decide acceleration strategy
        braking_distance = self._predict_braking_distance_from_stop(speed)
        should_brake = distance <= braking_distance and speed > 0.1

        # Step 2b: Predictive braking - check if next iteration speed would be below landing threshold
        if should_brake:
            decel_per_frame = self.acceleration_magnitude
            if self.space_drag > 0:
                decel_per_frame = self.acceleration_magnitude * (1 - self.space_drag)

            next_speed = speed - decel_per_frame

            # Stop braking if next iteration would reach landing speed (< 0.5)
            if next_speed < 0.5:
                self.autopilot_active = False
                self.release_thrust()
                return

        # Step 3: Calculate optimal acceleration direction
        dx = target.x - self.x
        dy = target.y - self.y
        target_angle = math.atan2(dx, -dy)

        if should_brake:
            # Blend toward slowing down while redirecting to target
            accel_angle = self._calculate_brake_redirect_angle(target_angle)
        else:
            # Point toward target and accelerate
            accel_angle = target_angle

        # Step 4: Point and thrust in that direction
        self._autopilot_point_and_thrust(accel_angle)

    def _predict_braking_distance_from_stop(self, current_speed):
        """Predict distance needed to stop from current speed.

        Assumes: turn 180 degrees while coasting, then apply reverse thrust until stopped.
        """
        if current_speed < 0.1:
            return 0

        # Time to turn 180 degrees (coasting at current speed)
        turn_frames = 180 / self.rotation_speed
        distance_during_turn = current_speed * turn_frames

        # Time to decelerate from current_speed to zero with full reverse thrust
        decel_per_frame = self.acceleration_magnitude
        if self.space_drag > 0:
            decel_per_frame = self.acceleration_magnitude * (1 - self.space_drag)

        decel_frames = 0
        distance_during_decel = 0
        v = current_speed

        # Simulate deceleration frame by frame
        while v > 0.05 and decel_frames < 500:
            v_avg = (v + max(0, v - decel_per_frame)) / 2.0
            distance_during_decel += v_avg
            v = max(0, v - decel_per_frame)
            decel_frames += 1

        total_distance = distance_during_turn + distance_during_decel

        # Add 10% safety buffer
        return total_distance * 1.1

    def _calculate_brake_redirect_angle(self, target_angle_rad):
        """Calculate acceleration direction that blends braking (opposite velocity) with redirect (toward target).

        When braking: accelerate in direction that has both:
        - Component opposite to velocity (to slow down)
        - Component toward target (to redirect)
        """
        # Calculate velocity angle
        velocity_angle = math.atan2(self.velocity_x, -self.velocity_y)

        # Calculate reverse velocity angle (opposite direction)
        reverse_velocity_angle = (velocity_angle + math.pi) % (2 * math.pi)

        # Blend between reverse velocity direction and target direction
        # This creates a direction that both brakes and redirects
        angle_diff = target_angle_rad - reverse_velocity_angle
        # Normalize angle difference
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi

        # Blend: 70% reverse velocity (brake), 30% target (redirect)
        blended_angle = reverse_velocity_angle + angle_diff * 0.3

        return blended_angle

    def _autopilot_point_and_thrust(self, accel_angle_rad):
        """Point ship in acceleration direction and apply thrust."""
        accel_angle_deg = math.degrees(accel_angle_rad)
        current_angle = self.angle % 360
        target_angle_norm = accel_angle_deg % 360

        angle_diff = target_angle_norm - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Rotate toward acceleration direction
        if angle_diff < -self.rotation_speed:
            self.turn_left()
        elif angle_diff > self.rotation_speed:
            self.turn_right()

        # If aligned with acceleration direction, apply thrust
        aligned = abs(angle_diff) < 10
        if aligned:
            self.increase_thrust()
        else:
            self.release_thrust()
