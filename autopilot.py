"""Standardized autopilot flight computer, owned by a single Ship."""
import math


class Autopilot:
    """Autopilot for one Ship. Two modes:

    - "seek": approach `target` and arrive once close and slow enough - the
      unified controller that redirects AND decelerates simultaneously.
    - "orbit": continuously circle a fixed point at a fixed radius; never arrives.

    Reads the ship's kinematic state and stats, and drives it only through
    its public control methods (turn_left/turn_right/increase_thrust/release_thrust).
    """
    def __init__(self, ship):
        self.ship = ship
        self.active = False
        self.mode = "seek"
        self.target = None
        self.orbit_center_x = 0
        self.orbit_center_y = 0
        self.orbit_radius = 0
        self.orbit_angle = 0

    def engage_seek(self, target):
        """Engage seek mode: approach `target`, arriving once close and slow enough."""
        self.mode = "seek"
        self.target = target
        self.active = True

    def engage_orbit(self, center_x, center_y, radius):
        """Engage orbit mode: continuously circle (center_x, center_y) at `radius`."""
        self.mode = "orbit"
        self.orbit_center_x = center_x
        self.orbit_center_y = center_y
        self.orbit_radius = radius
        # Start from the angle the ship is already at, so it eases onto the
        # circle instead of jumping to an arbitrary point on it.
        self.orbit_angle = math.atan2(self.ship.y - center_y, self.ship.x - center_x)
        self.target = None
        self.active = True

    def disengage(self):
        """Turn off autopilot and release thrust."""
        self.active = False
        self.target = None
        self.ship.release_thrust()

    def update(self):
        """Advance autopilot by one frame. Dispatches to the engaged mode."""
        if not self.active:
            return

        if self.mode == "orbit":
            self._update_orbit()
            return

        if not self.target:
            return

        self._update_seek()

    def _update_seek(self):
        """Approach self.target, redirecting and decelerating simultaneously."""
        ship = self.ship
        target = self.target
        distance = target.get_distance(ship.x, ship.y)
        speed = math.sqrt(ship.velocity_x ** 2 + ship.velocity_y ** 2)

        # Step 1: Landing/arrival condition check
        # Use landing_distance if available (for landables), otherwise use default close distance (for ships)
        landing_distance = getattr(target, 'landing_distance', 100)
        if distance < landing_distance and speed < 0.4:
            self.disengage()
            return

        # Step 2: Decide acceleration strategy
        braking_distance = self._predict_braking_distance_from_stop(speed)
        should_brake = distance <= braking_distance and speed > 0.1

        # Step 2b: Check if braking would actually decelerate us
        if should_brake:
            # Simulate one frame to check if we'd actually slow down
            dx, dy = target.x - ship.x, target.y - ship.y
            target_angle_rad = math.atan2(dx, -dy)
            accel_angle = self._calculate_brake_redirect_angle(target_angle_rad)

            # Check if aligned enough to thrust
            accel_angle_deg = math.degrees(accel_angle)
            current_angle = ship.angle % 360
            target_angle_norm = accel_angle_deg % 360
            angle_diff = target_angle_norm - current_angle
            if angle_diff > 180:
                angle_diff -= 360
            elif angle_diff < -180:
                angle_diff += 360

            aligned = abs(angle_diff) < 10
            if aligned:
                # Simulate thrust application
                rad = math.radians(ship.angle)
                test_vx = ship.velocity_x + math.sin(rad) * ship.acceleration_magnitude
                test_vy = ship.velocity_y - math.cos(rad) * ship.acceleration_magnitude
                test_speed = math.sqrt(test_vx ** 2 + test_vy ** 2)

                # Stop braking if speed would increase instead of decrease
                if test_speed > speed:
                    self.disengage()
                    return

        # Step 3: Calculate optimal acceleration direction
        dx, dy = target.x - ship.x, target.y - ship.y
        target_angle = math.atan2(dx, -dy)

        if should_brake:
            # Blend toward slowing down while redirecting to target
            accel_angle = self._calculate_brake_redirect_angle(target_angle)
        else:
            # Point toward target and accelerate
            accel_angle = target_angle

        # Step 4: Point and thrust in that direction
        self._point_and_thrust(accel_angle)

    def _update_orbit(self):
        """Chase a point that continuously sweeps around the orbit circle.

        No braking phase: the chased point never stops moving, so the ship
        just keeps pointing at it and thrusting - settling into a steady
        pursuit curve around the circle rather than a discrete arrival.
        """
        if self.orbit_radius <= 0:
            self.ship.release_thrust()
            return

        # How fast the chased point sweeps the circle, in radians/frame - tuned
        # comfortably under max_velocity so the ship can actually keep pace.
        linear_speed = 0.6 * self.ship.max_velocity
        angular_speed = linear_speed / self.orbit_radius
        self.orbit_angle = (self.orbit_angle + angular_speed) % (2 * math.pi)

        waypoint_x = self.orbit_center_x + self.orbit_radius * math.cos(self.orbit_angle)
        waypoint_y = self.orbit_center_y + self.orbit_radius * math.sin(self.orbit_angle)

        dx, dy = waypoint_x - self.ship.x, waypoint_y - self.ship.y
        target_angle = math.atan2(dx, -dy)
        self._point_and_thrust(target_angle)

    def _predict_braking_distance_from_stop(self, current_speed):
        """Predict distance needed to stop from current_speed.

        Assumes: turn 180 degrees while coasting, then apply reverse thrust until stopped.
        """
        ship = self.ship
        if current_speed < 0.1:
            return 0

        # Time to turn 180 degrees (coasting at current speed)
        turn_frames = 180 / ship.rotation_speed
        distance_during_turn = current_speed * turn_frames

        # Time to decelerate from current_speed to zero with full reverse thrust
        decel_per_frame = ship.acceleration_magnitude
        if ship.space_drag > 0:
            decel_per_frame = ship.acceleration_magnitude * (1 - ship.space_drag)

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
        ship = self.ship
        # Calculate velocity angle
        velocity_angle = math.atan2(ship.velocity_x, -ship.velocity_y)

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

    def _point_and_thrust(self, accel_angle_rad):
        """Point ship in acceleration direction and apply thrust once aligned."""
        ship = self.ship
        accel_angle_deg = math.degrees(accel_angle_rad)
        current_angle = ship.angle % 360
        target_angle_norm = accel_angle_deg % 360

        angle_diff = target_angle_norm - current_angle
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360

        # Rotate toward acceleration direction
        if angle_diff < -ship.rotation_speed:
            ship.turn_left()
        elif angle_diff > ship.rotation_speed:
            ship.turn_right()

        # If aligned with acceleration direction, apply thrust
        aligned = abs(angle_diff) < 10
        if aligned:
            ship.increase_thrust()
        else:
            ship.release_thrust()
