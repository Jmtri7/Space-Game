"""Standardized autopilot flight computer, owned by a single Ship.

Movement modes are Strategy objects (SeekMode, OrbitMode) rather than a
string flag branched on in update() every frame - engaging a mode swaps in
the strategy object once, and Autopilot.update() just delegates to it
polymorphically.
"""
import math

# Seek-mode arrival tuning: how close (as a fraction of the target's own
# landing_distance, floored so slow ships can still reach it) and how slow
# the ship must be to call it "landed" and disengage. See SeekMode.update().
ARRIVAL_DISTANCE_FRACTION = 0.15
ARRIVAL_DISTANCE_FLOOR = 8
ARRIVAL_SPEED_THRESHOLD = 0.1


def turn_toward(ship, angle_rad):
    """Rotate the ship one step toward angle_rad (radians). Returns True
    once the ship is aligned with it within 10 degrees."""
    angle_deg = math.degrees(angle_rad)
    current_angle = ship.angle % 360
    target_angle_norm = angle_deg % 360

    angle_diff = target_angle_norm - current_angle
    if angle_diff > 180:
        angle_diff -= 360
    elif angle_diff < -180:
        angle_diff += 360

    if angle_diff < -ship.rotation_speed:
        ship.turn_left()
    elif angle_diff > ship.rotation_speed:
        ship.turn_right()

    return abs(angle_diff) < 10


def point_and_thrust(ship, accel_angle_rad):
    """Point ship in acceleration direction and apply thrust once aligned."""
    if turn_toward(ship, accel_angle_rad):
        ship.increase_thrust()
    else:
        ship.release_thrust()


def predict_braking_distance_from_stop(ship, current_speed):
    """Predict distance needed to stop from current_speed.

    Assumes: turn 180 degrees while coasting, then apply reverse thrust until stopped.
    """
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


def calculate_brake_redirect_angle(ship, target_angle_rad):
    """Calculate acceleration direction that blends braking (opposite velocity) with redirect (toward target).

    When braking: accelerate in direction that has both:
    - Component opposite to velocity (to slow down)
    - Component toward target (to redirect)
    """
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


class SeekMode:
    """Approach `target` and arrive once close and slow enough - the unified
    controller that redirects AND decelerates simultaneously."""
    def __init__(self, target):
        self.target = target

    def update(self, autopilot):
        """Approach self.target, redirecting and decelerating simultaneously."""
        ship = autopilot.ship
        target = self.target
        distance = target.get_distance(ship.x, ship.y)
        speed = math.sqrt(ship.velocity_x ** 2 + ship.velocity_y ** 2)

        # Step 1: Landing/arrival condition check
        # landing_distance is how close a *manual* landing (L key) is allowed
        # from - generous, since it's sized to the landable itself. Arriving
        # anywhere in that whole radius and calling it "landed" left the
        # autopilot stopping visibly off-center (25-50 units out, in testing).
        # Use a much tighter fraction of it instead, so the autopilot keeps
        # braking all the way in to (near) the landable's exact middle,
        # floored so it stays reachable for slow/sluggish ships.
        landing_distance = getattr(target, 'landing_distance', 100)
        arrival_tolerance = max(ARRIVAL_DISTANCE_FLOOR, landing_distance * ARRIVAL_DISTANCE_FRACTION)
        if distance < arrival_tolerance and speed < ARRIVAL_SPEED_THRESHOLD:
            # Arrival, not just a disengage - come to a full stop so the ship
            # doesn't keep drifting on whatever residual speed was left.
            ship.park()
            autopilot.disengage()
            return

        # Step 2: Decide acceleration strategy
        braking_distance = predict_braking_distance_from_stop(ship, speed)
        should_brake = distance <= braking_distance and speed > ARRIVAL_SPEED_THRESHOLD

        # Step 2b: Check if braking would actually decelerate us
        if should_brake:
            # Simulate one frame to check if we'd actually slow down
            dx, dy = target.x - ship.x, target.y - ship.y
            target_angle_rad = math.atan2(dx, -dy)
            accel_angle = calculate_brake_redirect_angle(ship, target_angle_rad)

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

                # Stop braking if speed would increase instead of decrease.
                # This only fires once already within braking_distance of the
                # target (should_brake), so it's functionally an arrival too
                # (confirmed by simulation: fires around ~2 units out at low
                # residual speed) - park so it doesn't drift on whatever
                # speed was left when braking stopped being productive.
                if test_speed > speed:
                    ship.park()
                    autopilot.disengage()
                    return

        # Step 3: Calculate optimal acceleration direction
        dx, dy = target.x - ship.x, target.y - ship.y
        target_angle = math.atan2(dx, -dy)

        if should_brake:
            # Blend toward slowing down while redirecting to target
            accel_angle = calculate_brake_redirect_angle(ship, target_angle)
        else:
            # Point toward target and accelerate
            accel_angle = target_angle

        # Step 4: Point and thrust in that direction
        point_and_thrust(ship, accel_angle)


class OrbitMode:
    """Continuously circle a fixed point at a fixed radius; never arrives.

    Steers along the tangent of the orbit circle at the ship's current
    position, nudged slightly toward/away from the target radius, and never
    brakes - just always thrusts once aligned.

    Earlier versions chased a point that swept the circle on its own clock,
    independent of the ship's actual position, and capped speed by braking
    (turning to face backward and firing reverse thrust) whenever going too
    fast. Both produced visible "struggling": the swept point disagreeing
    with wherever the ship actually was caused constant small heading
    corrections, and braking meant periodically turning away from the
    direction of travel.

    Steering from the ship's own live position instead means heading is
    just the tangent direction (which barely changes frame to frame) plus a
    small proportional pull back toward the target radius. Without an
    artificial speed cap the ship settles at max_velocity, but that's fine:
    the tangent+pull heading is a self-correcting centripetal steer (same
    idea as a car steering into a curve), so it naturally converges to a
    stable circle at whatever speed it's going, rather than needing to
    actively regulate speed at all. The settled circle ends up a bit larger
    than radius (a faster ship needs a wider turn to hold a circle with a
    fixed turn rate) - harmless, since it's still centered on the same
    landables and just orbits them with more clearance.
    """
    def __init__(self, center_x, center_y, radius):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius

    def update(self, autopilot):
        ship = autopilot.ship
        if self.radius <= 0:
            ship.release_thrust()
            return

        dx = ship.x - self.center_x
        dy = ship.y - self.center_y
        current_radius = math.hypot(dx, dy) or 1

        # Tangent direction (perpendicular to the radius vector) is the
        # heading that traces the circle. Blend in a small pull toward the
        # target radius, scaled by how far off the current radius is, so
        # drift gets corrected gradually instead of by re-chasing a point.
        tangent_dx, tangent_dy = -dy, dx
        radius_error = (current_radius - self.radius) / self.radius
        pull = max(-0.5, min(0.5, radius_error))
        combined_dx = tangent_dx - dx * pull
        combined_dy = tangent_dy - dy * pull
        target_angle = math.atan2(combined_dx, -combined_dy)

        if turn_toward(ship, target_angle):
            ship.increase_thrust()
        else:
            ship.release_thrust()


class Autopilot:
    """Autopilot for one Ship. Owns the currently engaged movement mode (a
    SeekMode or OrbitMode strategy object, or None) and delegates to it each
    frame.

    Reads the ship's kinematic state and stats, and drives it only through
    its public control methods (turn_left/turn_right/increase_thrust/release_thrust).
    """
    def __init__(self, ship):
        self.ship = ship
        self.active = False
        self.target = None  # current seek target, if any - kept readable/settable
        # directly (e.g. SpaceScreen clears it when the player cancels autopilot)
        self._mode = None

    def engage_seek(self, target):
        """Engage seek mode: approach `target`, arriving once close and slow enough."""
        self.target = target
        self._mode = SeekMode(target)
        self.active = True

    def engage_orbit(self, center_x, center_y, radius):
        """Engage orbit mode: continuously circle (center_x, center_y) at `radius`."""
        self.target = None
        self._mode = OrbitMode(center_x, center_y, radius)
        self.active = True

    def disengage(self):
        """Turn off autopilot and release thrust."""
        self.active = False
        self.target = None
        self._mode = None
        self.ship.release_thrust()

    def update(self):
        """Advance autopilot by one frame - delegates to the engaged mode."""
        if not self.active or self._mode is None:
            return
        self._mode.update(self)
