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
BRAKING_SAFETY_BUFFER = 1.0       # multiplier on predict_braking_distance_from_stop's raw estimate - used to
# be 1.1, meant as a safety margin against the model underestimating. It
# never worked as one: the margin only inflated *when should_brake commits*,
# not the actual turn+decel maneuver that runs afterward (governed purely by
# rotation_speed/acceleration_magnitude), so the maneuver always consumed
# only the raw estimate and left the buffered portion completely unspent -
# the ship parked short by roughly that amount instead of gaining any real
# margin. Confirmed independent of landing_distance (identical shortfall
# regardless of target size) and directly responsible for the "brakes, stops
# short, has to turn around and creep the rest of the way" pattern. 1.0
# eliminates it (0 turnarounds for the player's own ship, shuttle) without
# reintroducing overshoot; pushing below 1.0 does reduce the slow-turning
# freighter's remaining turnarounds further but starts causing real overshoot
# and even stranding past ~0.9 - not worth that risk for how far it goes.
# Alignment needed before thrust fires while braking (see point_and_thrust).
# Tried widening this past the 10 degrees used everywhere else, on the
# theory that thrust could start partway through the turn-to-face-backward
# instead of waiting for it to finish and save some of that coast time.
# Simulation disproved it: thrust fired that far off pure retrograde has a
# real sideways component too, which needs correcting afterward - net
# slower (45 degrees), then unstable (60 introduced overshoot, 90 outright
# failed to converge in one trial). 10 stays the tightest and fastest.
BRAKE_ALIGNMENT_THRESHOLD_DEG = 10
STALL_BAILOUT_FACTOR = 1.5        # see SeekMode's "would increase speed" bailout
# Below this, the sideways (cross-track) component of velocity is treated as
# already gone - see SeekMode's cross-track-kill phase. Values from 0.7 up
# through at least 2.0 all tested identically (this only matters right at
# the noise floor); much lower (0.15) caused the phase to flicker on/off on
# harmless discretization jitter near zero, which - before that flicker was
# made sticky below - cost real frames swinging the heading back and forth
# for no reason.
CROSS_TRACK_KILL_THRESHOLD = 0.7
# Turn-radius speed cap: a fast, slow-turning ship (patrol) that's still
# carrying a lot of speed at an angle when it gets close to the target can
# enter a stable pursuit-curve loop instead of converging - always turning
# toward the target's current bearing but never tightly enough to actually
# close on it, so it just circles at a fixed range forever (classic
# pursuit-curve failure: the angular tracking rate required exceeds the
# ship's turn rate). distance * radians(rotation_speed) is roughly how far
# the ship's own turn rate could still redirect it per frame at the current
# range - above that (scaled by the margin below), it's carrying more speed
# than it can still correct with, so Step 2 treats it as a braking case
# instead of continuing to accelerate toward the target.
#
# First attempt compared speed to this cap directly as its own fresh check
# in Step 3, every frame. Broke the same way "The sticky-decision pitfall"
# (see AUTOPILOT_TESTING.md) describes: right at the cap boundary, distance
# itself oscillates a few units per frame (the ship is mid-circle), so the
# raw comparison flickered true/false and swung the heading between
# retrograde and point-at-target every single frame - 56 direction
# reversals in one traced trial, worse than the bug it was meant to fix.
# Folding it into Step 2's commit decision instead - already sticky - fixed
# it: 0/216 bad in a dedicated close-range pursuit sweep (was 16/216 under
# the along-track-gated commit alone, patrol only), no new jitter, and
# faster to land besides (mean 126.7 frames vs. 340.4) since it stops
# circling instead of grinding out MAX_SEEK_FRAMES.
APPROACH_TURN_SPEED_MARGIN = 0.5
# Watchdog: force an arrival after this many frames of active seeking,
# regardless of precision. Found one narrow case (a slow-turning ship with
# velocity ~120 degrees off-target at close range) where the un-stick/
# re-commit cycle settles into a stable loop that never quite lines up
# "close" and "slow" on the same frame - a preexisting risk in that cycle,
# not something introduced by the misalignment gate above (reproduces at
# every gate value tried, including with the gate disabled). Better to
# park somewhere imprecise than fly forever; comfortably above the
# slowest normal landing observed in testing (freighter, under 2000
# frames) while still bounding worst case to ~50 seconds instead of never.
MAX_SEEK_FRAMES = 3000


def has_arrived(ship, target):
    """Whether ship is close and slow enough to a target to call it
    "arrived" - the single source of truth for that, shared by SeekMode's
    own arrival check and SpaceScreen's landing-screen transition, so the
    two can't drift out of sync the way they did before this existed: the
    screen-level check used to use its own looser distance/speed numbers,
    so it would win the race and trigger docking well before the ship
    actually braked down to SeekMode's tighter, intended stopping point."""
    distance = target.get_distance(ship.x, ship.y)
    speed = math.sqrt(ship.velocity_x ** 2 + ship.velocity_y ** 2)
    landing_distance = getattr(target, 'landing_distance', 100)
    arrival_tolerance = max(ARRIVAL_DISTANCE_FLOOR, landing_distance * ARRIVAL_DISTANCE_FRACTION)
    return distance < arrival_tolerance and speed < ARRIVAL_SPEED_THRESHOLD


def turn_toward(ship, angle_rad, alignment_threshold_deg=10):
    """Rotate the ship one step toward angle_rad (radians). Returns True
    once the ship is aligned with it within alignment_threshold_deg."""
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

    return abs(angle_diff) < alignment_threshold_deg


def point_and_thrust(ship, accel_angle_rad, alignment_threshold_deg=10):
    """Point ship in acceleration direction and apply thrust once aligned."""
    if turn_toward(ship, accel_angle_rad, alignment_threshold_deg):
        ship.increase_thrust()
    else:
        ship.release_thrust()


def opposing_angle(vx, vy):
    """Direction that opposes a given vector - thrusting this way cancels
    it. Used both for a full retrograde burn (see retrograde_angle) and, on
    its own, to cancel just the cross-track component of velocity in
    SeekMode's cross-track-kill phase."""
    vector_angle = math.atan2(vx, -vy)
    return (vector_angle + math.pi) % (2 * math.pi)


def retrograde_angle(ship):
    """Direction directly opposite the ship's current velocity - a pure
    braking burn.

    An earlier version blended in some redirect-toward-target (30%) on top
    of this, meant to correct for velocity that had drifted off the line to
    the target. In practice it did the opposite: since the ship's heading
    already tracks the target closely by the time braking starts (Step 3's
    non-braking approach continuously points at the target), that 30% pull
    fought the braking heading it was supposed to reach every frame instead
    of ever settling on it, so alignment (and thus real thrust) kept getting
    delayed - long enough that the ship coasted straight through the target
    before finally braking, then had to loop back around. Pure retrograde
    matches what predict_braking_distance_from_stop already assumes (turn
    to face away from travel, then reverse-thrust) and, confirmed by
    simulation across a spread of approach angles/distances, stops in a
    straight line with no pass-by at all *when velocity is already pointed
    roughly at the target* - see SeekMode's cross-track-kill phase for what
    handles it when that's not true.
    """
    return opposing_angle(ship.velocity_x, ship.velocity_y)


def velocity_components(ship, target, distance):
    """Split the ship's velocity into (along, perp_x, perp_y) relative to
    the straight line to target: along is the signed speed closing on the
    target (positive = approaching), and (perp_x, perp_y) is whatever
    velocity is left once that's removed - the sideways drift a pure
    retrograde burn can't fix because it isn't pointed anywhere near
    target."""
    if distance < 1e-6:
        return 0.0, 0.0, 0.0
    ux, uy = (target.x - ship.x) / distance, (target.y - ship.y) / distance
    along = ship.velocity_x * ux + ship.velocity_y * uy
    perp_x = ship.velocity_x - along * ux
    perp_y = ship.velocity_y - along * uy
    return along, perp_x, perp_y


def predict_braking_distance_from_stop(ship, current_speed):
    """Predict distance needed to stop from current_speed.

    Assumes: turn 180 degrees while coasting, then apply reverse thrust until stopped.
    (Tried using the ship's actual current heading instead of a flat 180 -
    had zero effect in practice, since the moment this is re-evaluated after
    an un-stick is always right as the ship finishes turning to face the
    *target* to accelerate again, which by definition leaves it ~180 degrees
    from retrograde regardless of how that heading was computed. Reverted -
    not worth the extra complexity for no measured benefit.)
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

    return total_distance * BRAKING_SAFETY_BUFFER


class SeekMode:
    """Approach `target` and arrive once close and slow enough - the unified
    controller that redirects AND decelerates simultaneously."""
    def __init__(self, target):
        self.target = target
        # Sticky once True - see Step 2's comment for why this can't just be
        # recomputed fresh every frame.
        self.braking = False
        # Sticky once True (only meaningful while braking) - see Step 2a.
        self.cross_track_done = True
        self.frames = 0  # see MAX_SEEK_FRAMES

    def update(self, autopilot):
        """Approach self.target, redirecting and decelerating simultaneously."""
        ship = autopilot.ship
        target = self.target
        distance = target.get_distance(ship.x, ship.y)
        speed = math.sqrt(ship.velocity_x ** 2 + ship.velocity_y ** 2)

        # Step 1: Landing/arrival condition check (see has_arrived - tight
        # enough that the autopilot keeps braking all the way in to (near)
        # the landable's exact middle, not just its generous manual-landing
        # radius, floored so it stays reachable for slow/sluggish ships).
        # The watchdog is checked alongside it: a real arrival is always
        # preferred, but past MAX_SEEK_FRAMES, stop wherever we are rather
        # than risk looping forever (see MAX_SEEK_FRAMES).
        self.frames += 1
        if has_arrived(ship, target) or self.frames > MAX_SEEK_FRAMES:
            # Arrival, not just a disengage - come to a full stop so the ship
            # doesn't keep drifting on whatever residual speed was left.
            ship.park()
            autopilot.disengage()
            return

        # Step 2: Decide acceleration strategy. Once committed to braking,
        # stay committed for the rest of this approach rather than
        # recomputing the condition fresh every frame - right near arrival,
        # small frame-to-frame changes in distance/speed made it flicker
        # true/false repeatedly (predicted stopping distance and actual
        # distance both shrinking in step, straddling each other), and each
        # flip swings the heading between retrograde and point-at-target -
        # nearly opposite directions once the ship's basically sitting still
        # in front of the target. That whipsawed the nose back and forth for
        # dozens of frames with the engine off, instead of ever holding a
        # heading long enough to actually thrust.
        #
        # Gated on along-track speed (the component actually closing on the
        # target), not total speed - predict_braking_distance_from_stop's
        # whole model assumes the speed it's given is usefully pointed at
        # the target, which isn't true when most of it is sideways drift.
        # Committing off total speed there let the ship commit to an early,
        # expensive cross-track correction it didn't have the along-track
        # progress to afford yet, instead of just letting the normal
        # point-at-target approach build real closing speed first.
        # Second commit trigger, alongside the braking-distance one above:
        # speed exceeding what this ship's own turn rate could still redirect
        # at the current range (see APPROACH_TURN_SPEED_MARGIN) - catches a
        # fast, slow-turning ship stuck circling the target instead of
        # closing on it.
        if not self.braking:
            along, _, _ = velocity_components(ship, target, distance)
            along_speed = max(0, along)
            braking_distance = predict_braking_distance_from_stop(ship, along_speed)
            turn_cap = distance * math.radians(ship.rotation_speed) * APPROACH_TURN_SPEED_MARGIN
            self.braking = (distance <= braking_distance and along_speed > ARRIVAL_SPEED_THRESHOLD) or speed > turn_cap
            if self.braking:
                self.cross_track_done = False  # fresh commit - give it one cross-track check
        should_brake = self.braking

        # Step 2a: cross-track kill. Retrograde thrust only cancels
        # whatever velocity currently exists - if most of it is sideways
        # (e.g. the ship was already moving fast in some unrelated
        # direction when it targeted the landable), braking immediately
        # just freezes that sideways drift in place instead of correcting
        # it, stopping the ship well off to the side on the very first
        # attempt (up to ~360 units off, measured). Null the cross-track
        # component first so the retrograde burn below is left with
        # velocity that's actually pointed at the target - the same
        # straight-line stop it was already proven to deliver.
        #
        # Sticky per commitment (self.cross_track_done), same reasoning as
        # self.braking above: recomputed fresh every frame, tiny
        # discretization jitter right at CROSS_TRACK_KILL_THRESHOLD flickers
        # this on and off, each flip costing a full heading swing for no
        # reason. One check per commitment is enough - if it passes, this
        # phase never runs again until the next fresh commit (e.g. after an
        # un-stick).
        if should_brake and not self.cross_track_done:
            along, perp_x, perp_y = velocity_components(ship, target, distance)
            if math.hypot(perp_x, perp_y) > CROSS_TRACK_KILL_THRESHOLD:
                point_and_thrust(ship, opposing_angle(perp_x, perp_y), BRAKE_ALIGNMENT_THRESHOLD_DEG)
                return
            self.cross_track_done = True

        # Step 2b: Check if braking would actually decelerate us
        if should_brake:
            # Below has_arrived's own speed threshold, retrograde_angle is
            # unreliable (atan2 of a near-zero vector barely means anything),
            # and there's not much velocity left worth precisely cancelling
            # anyway - decide accept-or-resume immediately instead of first
            # requiring alignment to a target that can jitter unpredictably
            # at speeds this low. Without this, a ship could spin in place
            # for a long stretch: neither the thrust-would-help check below
            # nor the bailout it guards can run without "aligned" being true
            # first, and at speeds this low "aligned" might not happen again
            # for a while by chance (measured: ~150 wasted frames in one
            # traced case, spinning with the engine off and no progress).
            if speed < ARRIVAL_SPEED_THRESHOLD:
                if self._accept_or_resume(ship, autopilot, target, distance):
                    return
                should_brake = self.braking
            else:
                # Simulate one frame to check if we'd actually slow down
                accel_angle = retrograde_angle(ship)

                # Check if aligned enough to thrust
                accel_angle_deg = math.degrees(accel_angle)
                current_angle = ship.angle % 360
                target_angle_norm = accel_angle_deg % 360
                angle_diff = target_angle_norm - current_angle
                if angle_diff > 180:
                    angle_diff -= 360
                elif angle_diff < -180:
                    angle_diff += 360

                aligned = abs(angle_diff) < BRAKE_ALIGNMENT_THRESHOLD_DEG
                if aligned:
                    # Simulate thrust application
                    rad = math.radians(ship.angle)
                    test_vx = ship.velocity_x + math.sin(rad) * ship.acceleration_magnitude
                    test_vy = ship.velocity_y - math.cos(rad) * ship.acceleration_magnitude
                    test_speed = math.sqrt(test_vx ** 2 + test_vy ** 2)

                    # Speed would increase instead of decrease - retrograde
                    # thrust isn't productive anymore.
                    if test_speed > speed:
                        if self._accept_or_resume(ship, autopilot, target, distance):
                            return
                        should_brake = self.braking

        # Step 3: Calculate optimal acceleration direction
        if should_brake:
            # Wider alignment threshold than the approach phase - see
            # BRAKE_ALIGNMENT_THRESHOLD_DEG.
            point_and_thrust(ship, retrograde_angle(ship), BRAKE_ALIGNMENT_THRESHOLD_DEG)
            return

        # Point toward target and accelerate
        dx, dy = target.x - ship.x, target.y - ship.y
        point_and_thrust(ship, math.atan2(dx, -dy))

    def _accept_or_resume(self, ship, autopilot, target, distance):
        """Called once braking has stopped being productive at low speed
        (see Step 2b). Close enough to the target, that's functionally an
        arrival - park and stop. Farther out, un-commit from braking rather
        than parking mid-flight, so the ship resumes closing the remaining
        distance instead of getting stranded there forever (sticky
        self.braking would otherwise never reconsider once it stalls out
        like this). Returns True if it parked (caller should return
        immediately); False if it un-stuck (caller should keep going using
        the now-updated self.braking)."""
        landing_distance = getattr(target, 'landing_distance', 100)
        close_enough = max(ARRIVAL_DISTANCE_FLOOR, landing_distance * ARRIVAL_DISTANCE_FRACTION) * STALL_BAILOUT_FACTOR
        if distance < close_enough:
            ship.park()
            autopilot.disengage()
            return True
        self.braking = False
        return False


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
