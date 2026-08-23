"""Ship classes: Ship (base), PlayerController, and AIShip."""
import pygame
import math
import random
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
        """Update autopilot using kinematic prediction."""
        if not self.autopilot_active or not self.autopilot_target:
            return

        target = self.autopilot_target
        distance = target.get_distance(self.x, self.y)
        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        # Distance vector to target
        dx = target.x - self.x
        dy = target.y - self.y

        # Calculate angle in ship coordinates
        angle_to_target = math.atan2(dx, -dy)
        angle_to_target_deg = math.degrees(angle_to_target)

        # Predict braking distance using kinematic simulation
        braking_distance = self._predict_braking_distance(angle_to_target_deg, speed)

        if distance > braking_distance:
            # APPROACH PHASE: fly toward target
            self._autopilot_approach(angle_to_target_deg)
        else:
            # BRAKING PHASE: turn around and reverse thrust
            self._autopilot_brake(angle_to_target_deg)

    def _predict_braking_distance(self, target_angle_deg, current_speed):
        """Predict total distance needed to brake from current state using kinematics."""
        # Simulate rotation to opposite angle
        reverse_angle = (target_angle_deg + 180) % 360
        current_angle = self.angle % 360

        angle_diff = reverse_angle - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Time to rotate 180° (5°/frame rotation speed)
        rotation_frames = max(1, int(abs(angle_diff) / 5.0))

        # Simulate movement during rotation (constant velocity, no thrust)
        distance_during_rotation = current_speed * rotation_frames

        # Simulate deceleration after rotation
        v = current_speed
        decel_distance = 0
        frames_to_stop = 0

        # Apply drag-adjusted deceleration math
        if v > 0.1:
            if self.space_drag > 0:
                frames_to_stop = int(v / (self.max_thrust * (1 - self.space_drag)))
            else:
                frames_to_stop = int(v / self.max_thrust) + 2

            # Estimate distance during deceleration (average velocity method)
            decel_distance = (v / 2.0) * frames_to_stop

        total_distance = distance_during_rotation + decel_distance

        # Add small safety buffer for margin of error
        return total_distance * 1.1

    def _autopilot_approach(self, target_angle_deg):
        """Approach phase: conservative early deceleration to prevent overshooting."""
        if not self.autopilot_target:
            return

        target = self.autopilot_target
        distance = target.get_distance(self.x, self.y)
        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        # Point ship toward target
        current_angle = self.angle % 360
        target_angle = target_angle_deg % 360

        angle_diff = target_angle - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Rotate toward target
        rotation_step = 5
        if angle_diff < -rotation_step:
            self.angle = (self.angle - rotation_step) % 360
        elif angle_diff > rotation_step:
            self.angle = (self.angle + rotation_step) % 360
        else:
            self.angle = target_angle

        aligned = abs(angle_diff) < 15
        thrust_step = self.max_thrust * 0.08

        if aligned:
            if distance < 200:
                self.thrust = max(self.thrust - thrust_step * 2, 0)
            else:
                self.thrust = min(self.thrust + thrust_step, self.max_thrust)
        else:
            self.thrust = 0

    def _autopilot_brake(self, target_angle_deg):
        """Braking phase: rotate to face away from target, then apply reverse thrust."""
        target = self.autopilot_target
        distance = target.get_distance(self.x, self.y)
        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        # Point ship AWAY from target (opposite direction)
        reverse_angle = (target_angle_deg + 180) % 360
        current_angle = self.angle % 360

        angle_diff = reverse_angle - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Phase 1: Rotate to face away from target
        rotation_step = 5
        if abs(angle_diff) > rotation_step:
            if angle_diff < 0:
                self.angle = (self.angle - rotation_step) % 360
            else:
                self.angle = (self.angle + rotation_step) % 360
            self.thrust = 0
        else:
            # Phase 2: Facing away from target - apply precise reverse thrust
            self.angle = reverse_angle

            if speed < 0.15:
                self.thrust = 0
            else:
                min_distance = max(10, distance - 5)
                required_decel = (speed * speed) / (2 * min_distance)

                if self.space_drag > 0:
                    required_decel *= (1 - self.space_drag)

                self.thrust = min(self.max_thrust, required_decel)
                self.thrust = max(self.max_thrust * 0.2, self.thrust)


class PlayerController:
    """Controls the player's ship - owns the ship and handles input."""
    def __init__(self, x, y, space_drag=0):
        self.ship = Ship(x, y, space_drag=space_drag)

    def handle_input(self, keys):
        """Handle player keyboard input (blocked during autopilot)."""
        if self.ship.autopilot_active:
            return

        # Rotation controls
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.ship.turn_left()
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.ship.turn_right()

        # Thrust controls
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.ship.increase_thrust()
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            # Point ship toward opposite velocity (brake/reverse)
            self.ship.point_to_reverse_velocity()
        else:
            # Release thrust immediately
            self.ship.thrust = 0

    def update(self):
        """Update ship physics."""
        self.ship.update()

    def draw(self, surface):
        """Draw ship."""
        self.ship.draw(surface, ship_size=15, color=DARK_GRAY)

    # Delegation properties for backward compatibility
    @property
    def x(self):
        return self.ship.x

    @x.setter
    def x(self, value):
        self.ship.x = value

    @property
    def y(self):
        return self.ship.y

    @y.setter
    def y(self, value):
        self.ship.y = value

    @property
    def velocity_x(self):
        return self.ship.velocity_x

    @velocity_x.setter
    def velocity_x(self, value):
        self.ship.velocity_x = value

    @property
    def velocity_y(self):
        return self.ship.velocity_y

    @velocity_y.setter
    def velocity_y(self, value):
        self.ship.velocity_y = value

    @property
    def angle(self):
        return self.ship.angle

    @angle.setter
    def angle(self, value):
        self.ship.angle = value

    @property
    def autopilot_active(self):
        return self.ship.autopilot_active

    @autopilot_active.setter
    def autopilot_active(self, value):
        self.ship.autopilot_active = value

    @property
    def autopilot_target(self):
        return self.ship.autopilot_target

    @autopilot_target.setter
    def autopilot_target(self, value):
        self.ship.autopilot_target = value


class AIShip(Ship):
    """Autonomous AI ship with wandering behavior."""
    def __init__(self, x, y, space_drag=0, ship_type=None, ship_type_id="trader"):
        super().__init__(x, y, space_drag=space_drag)
        self.ship_type_id = ship_type_id
        self.angle = random.randint(0, 360)

        # Apply ship type properties if provided
        if ship_type:
            self.max_thrust = ship_type.get("max_thrust", 0.15)
            self.max_velocity = ship_type.get("max_velocity", 4.0)
            self.rotation_speed = ship_type.get("rotation_speed", 5)
            self.ship_color = ship_type.get("color", DARK_GRAY)
            self.ship_size = ship_type.get("size", 12)
        else:
            self.max_thrust = 0.15
            self.ship_color = DARK_GRAY
            self.ship_size = 12

        self.state = "accelerate"
        self.state_timer = 0

    def update(self):
        """Update AI ship with autonomous behavior."""
        self.state_timer -= 1

        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        if self.state == "accelerate":
            if self.state_timer <= 0:
                self.state = "brake"
                self.state_timer = random.randint(30, 60)
            else:
                self.thrust = self.max_thrust
                self.angle = (self.angle + random.uniform(-1, 1)) % 360

        elif self.state == "brake":
            if speed < 0.15:
                self.state = "accelerate"
                self.state_timer = random.randint(40, 80)
                self.angle = random.uniform(0, 360)
                self.thrust = 0
                self.velocity_x *= 0.95
                self.velocity_y *= 0.95
            else:
                velocity_angle = math.degrees(math.atan2(self.velocity_x, -self.velocity_y)) % 360
                target_angle = (velocity_angle + 180) % 360
                angle_diff = (target_angle - self.angle) % 360
                if angle_diff > 180:
                    angle_diff -= 360

                if abs(angle_diff) > 2:
                    self.angle = (self.angle + angle_diff * 0.1) % 360
                self.thrust = self.max_thrust

        rad = math.radians(self.angle)
        if self.thrust > 0.01:
            self.velocity_x += math.sin(rad) * self.thrust
            self.velocity_y -= math.cos(rad) * self.thrust

        # Apply space system drag
        if self.space_drag > 0:
            self.velocity_x *= self.space_drag
            self.velocity_y *= self.space_drag

        self.x += self.velocity_x
        self.y += self.velocity_y

        self.wrap_position()

    def draw(self, surface):
        """Draw AI ship with ship type size and color."""
        super().draw(surface, ship_size=self.ship_size, color=tuple(self.ship_color))
