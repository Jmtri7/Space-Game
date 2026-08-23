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
        """Update autopilot - point at target, accelerate, brake when close enough.

        Base case: handles stopped ship (velocity ≈ 0).
        Shuts off when landing conditions met: distance < 150, speed < 0.5
        """
        if not self.autopilot_active or not self.autopilot_target:
            return

        target = self.autopilot_target
        distance = target.get_distance(self.x, self.y)
        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        # Distance vector from ship to target
        dx = target.x - self.x
        dy = target.y - self.y

        # Calculate angle to target
        target_angle = math.atan2(dx, -dy)
        target_angle_deg = math.degrees(target_angle)

        # Landing condition: distance < 150, speed < 0.5 (same as GameScreen)
        if distance < 150 and speed < 0.5:
            self.autopilot_active = False
            self.release_thrust()
            return

        # Predict how far we'll travel during braking (turn + decelerate)
        braking_distance = self._predict_braking_distance_from_stop(speed)

        # If within braking distance, start braking (turn around and reverse thrust)
        if distance <= braking_distance and speed > 0.1:
            self._autopilot_brake(target_angle_deg)
        else:
            # Point at target and accelerate
            self._autopilot_point_and_accelerate(target_angle_deg)

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

    def _autopilot_point_and_accelerate(self, target_angle_deg):
        """Point directly at target and accelerate toward it."""
        current_angle = self.angle % 360
        target_angle_norm = target_angle_deg % 360

        angle_diff = target_angle_norm - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Rotate toward target
        if angle_diff < -self.rotation_speed:
            self.turn_left()
        elif angle_diff > self.rotation_speed:
            self.turn_right()

        # If aligned with target, apply thrust
        aligned = abs(angle_diff) < 10
        if aligned:
            self.increase_thrust()
        else:
            self.release_thrust()

    def _autopilot_brake(self, target_angle_deg):
        """Braking phase: turn around (face away) and apply reverse thrust."""
        target = self.autopilot_target
        distance = target.get_distance(self.x, self.y)

        # Calculate angle facing away from target
        reverse_angle = (target_angle_deg + 180) % 360
        current_angle = self.angle % 360

        angle_diff = reverse_angle - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Phase 1: Turn around (rotate to face away)
        if abs(angle_diff) > self.rotation_speed:
            if angle_diff < 0:
                self.turn_left()
            else:
                self.turn_right()
            self.release_thrust()
        else:
            # Phase 2: Facing away - apply reverse thrust to decelerate
            speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

            # Calculate deceleration per frame
            decel_per_frame = self.acceleration_magnitude
            if self.space_drag > 0:
                decel_per_frame = self.acceleration_magnitude * (1 - self.space_drag)

            # Stop thrust if one more frame would make velocity negative (reverse direction)
            if speed <= decel_per_frame:
                self.release_thrust()
                # Landing condition: distance < 150, speed < 0.5 (same as GameScreen)
                if distance < 150 and speed < 0.5:
                    self.autopilot_active = False
            else:
                self.increase_thrust()
