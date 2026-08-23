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
        """Update autopilot - approach and brake to land with zero velocity at target."""
        if not self.autopilot_active or not self.autopilot_target:
            return

        target = self.autopilot_target
        distance = target.get_distance(self.x, self.y)
        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        # Check if we've landed (nearly stopped and very close)
        if distance < 10 and speed < 0.1:
            self.autopilot_active = False
            self.release_thrust()
            return

        # Distance vector to target
        dx = target.x - self.x
        dy = target.y - self.y

        # Calculate angle in ship coordinates
        angle_to_target = math.atan2(dx, -dy)
        angle_to_target_deg = math.degrees(angle_to_target)

        # Predict braking distance (how far we'll travel during the entire braking sequence)
        braking_distance = self._predict_braking_distance(angle_to_target_deg, speed)

        if distance > braking_distance:
            # APPROACH PHASE: fly toward target
            self._autopilot_approach(angle_to_target_deg)
        else:
            # BRAKING PHASE: reverse thrust to stop at target
            self._autopilot_brake(angle_to_target_deg)

    def _predict_braking_distance(self, target_angle_deg, current_speed):
        """Predict total distance needed to brake from current speed to zero at target.

        Simulates:
        1. Time to rotate to face opposite direction (coast at current speed)
        2. Time to decelerate from current speed to near-zero with reverse thrust
        """
        if current_speed < 0.05:
            return 0  # Already nearly stopped

        # Calculate angle we need to face (opposite of approach direction)
        reverse_angle = (target_angle_deg + 180) % 360
        current_angle = self.angle % 360

        angle_diff = reverse_angle - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Time to rotate to reverse angle (coasting at current speed)
        rotation_frames = max(1, int(abs(angle_diff) / self.rotation_speed))
        distance_during_rotation = current_speed * rotation_frames

        # Time to decelerate from current_speed to near-zero with max reverse thrust
        # Velocity decreases by (max_thrust - space_drag effect) per frame
        v = current_speed
        decel_frames = 0
        decel_distance = 0

        # Simulate deceleration frame by frame for accuracy
        while v > 0.05 and decel_frames < 500:
            # Apply reverse thrust (decrease velocity)
            decel_per_frame = self.max_thrust
            if self.space_drag > 0:
                decel_per_frame = self.max_thrust * (1 - self.space_drag)

            # Average velocity during this frame
            v_avg = (v + max(0, v - decel_per_frame)) / 2.0
            decel_distance += v_avg

            v = max(0, v - decel_per_frame)
            decel_frames += 1

        total_distance = distance_during_rotation + decel_distance

        # Add small safety buffer (10%)
        return total_distance * 1.1

    def _autopilot_approach(self, target_angle_deg):
        """Approach phase: fly toward target while maintaining alignment."""
        if not self.autopilot_target:
            return

        # Point ship toward target
        current_angle = self.angle % 360
        target_angle = target_angle_deg % 360

        angle_diff = target_angle - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Rotate toward target (using turn_left/turn_right)
        if angle_diff < -self.rotation_speed:
            self.turn_left()
        elif angle_diff > self.rotation_speed:
            self.turn_right()

        # If aligned with target, thrust toward it
        aligned = abs(angle_diff) < 10
        if aligned:
            self.increase_thrust(step=0.01)
        else:
            self.release_thrust()

    def _autopilot_brake(self, target_angle_deg):
        """Braking phase: rotate to face opposite direction, then apply reverse thrust to stop at target.

        Uses reverse thrust (increase_thrust while facing opposite direction) to decelerate.
        """
        target = self.autopilot_target
        distance = target.get_distance(self.x, self.y)
        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        # Calculate the direction opposite to target approach
        reverse_angle = (target_angle_deg + 180) % 360
        current_angle = self.angle % 360

        angle_diff = reverse_angle - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Phase 1: Rotate to face away from target (coasting with no thrust)
        if abs(angle_diff) > self.rotation_speed:
            self.turn_left() if angle_diff < 0 else self.turn_right()
            self.release_thrust()
        else:
            # Phase 2: Facing opposite direction - apply reverse thrust to decelerate
            if speed < 0.1:
                # Nearly stopped, shut down and land
                self.release_thrust()
            else:
                # Apply reverse thrust (thrust while facing opposite direction)
                # Modulate thrust based on distance to ensure smooth deceleration
                remaining_decel_distance = self._predict_braking_distance(target_angle_deg, speed)
                if distance < remaining_decel_distance * 0.5:
                    # Very close, maximum reverse thrust
                    self.increase_thrust(step=self.max_thrust)
                else:
                    # Normal braking
                    self.increase_thrust(step=0.015)
