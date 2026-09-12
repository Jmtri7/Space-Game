"""Routine: hunt asteroids in the home system, blow them up, gather the
ore, and periodically fly back to the home station to sell the haul before
heading out again - the mining counterpart to DockRoutine's fly/walk/talk/
fly loop.

Approach-and-attack against an asteroid (a moving, shrinking target you
must destroy, not arrive at and park on) is driven low-level - turn_left/
turn_right/increase_thrust/release_thrust, character.firing - exactly like
CombatRoutine, and never touches engage_seek/SeekMode, so it carries none
of the autopilot regression risk documented in docs/AUTOPILOT_TESTING.md.
Docking at the station reuses the same walk-in/walk-out/interior machinery
DockRoutine already validates (get_interior_screen, plan_path,
Person.step_toward), just for a single fixed stop with a scripted "sell to
the quartermaster" pause instead of open-ended dialogue.
"""
import math
from game.constants import WALKING_SPEED
from game.world.asteroid_avoidance import steer_away_from_asteroids

WALK_SPEED = WALKING_SPEED
ARRIVAL_DISTANCE = 10
SELL_FRAMES = 90          # ~1.5s standing at the quartermaster per visit

ENGAGE_RANGE = 900        # only ever considers asteroids this close to the ship - never chases one off the map
ABANDON_RANGE = 1400      # drop the current target outright once it's drifted (or the ship's been knocked) this far apart - see _run_hunting
HOME_TETHER_RANGE = 1400  # never picks a target this far from the home station either - chasing rock after rock shouldn't be able to wander a miner arbitrarily far from home
PREFERRED_RANGE = 160     # stop closing once this near a hunted asteroid - a wider stand-off than a nimble combat ship needs, since a slow-turning hull (see mining_skiff's stats) can't correct a close overshoot quickly
PREFERRED_SPEED_CAP = 0.5   # enter close-range braking above this speed - see the braking branch in _run_hunting
EXIT_SPEED_CAP = 0.25       # ...and don't leave it again until below this - a lower exit threshold than the entry one (hysteresis), so speed hovering right at PREFERRED_SPEED_CAP can't flip the decision every frame (see self._braking_close)
FIRING_RANGE = 260
FIRING_CONE_DEG = 16      # looser than CombatRoutine's - a sluggish-turning ship needs a wider window to ever actually land in, not just line up for an instant between corrections
THRUST_CONE_DEG = 30

CHASE_TIMEOUT_FRAMES = 900  # ~15s - give up on a target that's survived this long being actively hunted (see _run_hunting's timeout check) rather than chase it forever
AVOID_COOLDOWN_FRAMES = 600 # ~10s a just-abandoned target stays off this miner's own pick list, so it doesn't just immediately re-pick the same one next frame

# A predicted-collision severity (see asteroid_avoidance.find_asteroid_threat)
# above this suppresses this frame's hunt/approach entirely - trajectory
# safety comes before pressing the attack. EXIT_DODGE_SEVERITY is the lower
# threshold severity must drop back below before dodging actually stops
# (hysteresis, via self._dodging) - without the gap between the two, a
# severity hovering right at URGENT_DODGE_SEVERITY flips the "hunt or dodge"
# decision every frame, and each flip swings the ship between "turn toward
# the target" and "turn away from a threat" - the same sticky-decision
# pitfall docs/AUTOPILOT_TESTING.md documents for autopilot.py, and what
# reads to a player as the ship chasing an asteroid, then suddenly veering
# off, over and over, never committing to either.
URGENT_DODGE_SEVERITY = 0.35
EXIT_DODGE_SEVERITY = 0.15

DOCK_ARRIVAL_DISTANCE = 60
DOCK_ARRIVAL_SPEED = 0.5

# Flat credits per unit of ore sold - an AI-to-AI transaction with nobody
# watching, so this deliberately doesn't touch commodities.json/the
# player's market (see Character.AI_PILOT_STARTING_CREDITS for the same
# "flavor economy, not real yet" precedent).
CREDITS_PER_ORE = 20

# Stuck-recovery for a walk leg - same idea/constants as DockRoutine's own
# (see its docstring), duplicated here rather than shared since the two
# routines otherwise have nothing else in common.
STUCK_STEP_EPSILON = 0.4
STUCK_REPLAN_FRAMES = 45
STUCK_GIVEUP_FRAMES = 150


def _signed_angle_delta(from_deg, to_deg):
    """Shortest signed rotation (degrees, -180..180) from from_deg to to_deg."""
    return (to_deg - from_deg + 180) % 360 - 180


BRAKE_SPEED_THRESHOLD = 0.15  # below this, not worth the fuss of braking further


def _brake(ship):
    """Turn to face retrograde and thrust against the ship's own velocity
    until it's essentially stopped - thrust is gated on actually being
    close to retrograde first (mirrors autopilot.py's own alignment-gated
    braking), since thrusting while still mid-turn would just keep
    redirecting velocity in a circle at a roughly constant speed rather
    than shedding it. Used whenever this routine has nowhere in particular
    to go this frame (no hunting target, or closing in to dock) - without
    this, a ship that ran out of targets would just coast on whatever
    velocity it last had, indefinitely, since space has no drag by
    default (see PHYSICS.md)."""
    speed = math.hypot(ship.velocity_x, ship.velocity_y)
    if speed < BRAKE_SPEED_THRESHOLD:
        ship.release_thrust()
        return
    velocity_angle = math.degrees(math.atan2(ship.velocity_x, -ship.velocity_y))
    retrograde_deg = (velocity_angle + 180) % 360
    diff = _signed_angle_delta(ship.angle, retrograde_deg)
    ship.point_to_reverse_velocity()
    if abs(diff) < THRUST_CONE_DEG:
        ship.increase_thrust()
    else:
        ship.release_thrust()


class MinerRoutine:
    """Phases: "hunting" (seek out and destroy asteroids, dodging any
    other nearby one, until cargo is full) -> "returning" (fly to the home
    station) -> "walking_in" -> "selling" -> "walking_out" -> back to
    "hunting"."""
    def __init__(self, route):
        self.station = route[0] if route else None
        self.phase = "hunting"
        self.target_asteroid = None
        self._location = None
        self._waypoints = []
        self._goal = None
        self._sell_timer = 0
        self._stuck_frames = 0
        self._replanned_while_stuck = False
        self._chase_timer = 0     # frames spent actively hunting the current target - see CHASE_TIMEOUT_FRAMES
        self._avoid = {}          # {Asteroid: frames_remaining} - targets this miner just gave up on, temporarily excluded from its own re-pick (see AVOID_COOLDOWN_FRAMES)
        self._dodging = False     # sticky "am I currently suppressing the hunt to dodge" state - see URGENT_DODGE_SEVERITY/EXIT_DODGE_SEVERITY
        self._braking_close = False  # sticky "am I currently braking near my target" state - see PREFERRED_SPEED_CAP/EXIT_SPEED_CAP

    def start(self, character):
        character.firing = False
        if character.ship:
            # Drop any autopilot mode so ship.update() runs plain physics on
            # the controls this routine sets - mirrors CombatRoutine.start().
            character.ship.autopilot.disengage()

    def run(self, character):
        ship = character.ship
        if not ship:
            return
        if self.phase == "hunting":
            self._run_hunting(character)
        elif self.phase == "returning":
            self._run_returning(character)
        elif self.phase == "walking_in":
            if self._step_toward(character.person):
                self._sell(character)
                self.phase = "selling"
                self._sell_timer = SELL_FRAMES
        elif self.phase == "selling":
            self._sell_timer -= 1
            if self._sell_timer <= 0:
                exit_portal = self._location.portal_for("ship")
                self._set_waypoints(character.person, (exit_portal["x"], exit_portal["y"]))
                self.phase = "walking_out"
        elif self.phase == "walking_out":
            if self._step_toward(character.person):
                self._reboard(character)

    # --- Hunting: find, close on, and shoot a target asteroid; dodge every other one ---

    def _nearby_asteroids(self, character):
        """This character's home system's live asteroid list - empty
        (harmlessly) for any system that isn't currently active, since
        AsteroidField only streams in chunks while it's being camera-driven
        (see AsteroidField.update/PHYSICS.md) - a miner just finds nothing
        to hunt until the player actually visits its system."""
        if not character.systems or character.system_id not in character.systems:
            return []
        field = getattr(character.systems[character.system_id], "asteroid_field", None)
        return field.asteroids if field else []

    def _system_state(self, character):
        if not character.systems or character.system_id not in character.systems:
            return None
        return character.systems[character.system_id]

    def _claim(self, character, asteroid):
        """Mark `asteroid` as this miner's own hunting target in the shared
        per-system claim set (see SystemState.claimed_asteroids), so
        another miner's _pick_target skips it - several miners in the same
        belt split up onto different rocks instead of dogpiling whichever
        one happens to be nearest to all of them."""
        state = self._system_state(character)
        if state is not None:
            state.claimed_asteroids.add(asteroid)

    def _release_claim(self, character):
        """Give up this miner's claim on whatever it was last hunting, if
        any - safe to call unconditionally (a no-op if nothing was claimed,
        or the asteroid's already gone)."""
        state = self._system_state(character)
        if state is not None:
            state.claimed_asteroids.discard(self.target_asteroid)

    def _run_hunting(self, character):
        ship = character.ship
        possessions = character.person.possessions
        asteroids = self._nearby_asteroids(character)
        self._tick_avoid()

        if possessions.cargo_quantity_total() >= ship.cargo_capacity and self.station is not None:
            self._release_claim(character)
            self.target_asteroid = None
            character.firing = False
            ship.release_thrust()
            self.phase = "returning"
            return

        if self.target_asteroid not in asteroids:
            self._release_claim(character)
            self.target_asteroid = self._pick_target(character, ship, asteroids)
            self._chase_timer = 0
        elif math.hypot(self.target_asteroid.x - ship.x, self.target_asteroid.y - ship.y) > ABANDON_RANGE:
            # Still technically "in" the loaded asteroid list (that check
            # alone only means it hasn't been unloaded or destroyed - it
            # says nothing about how far *this ship* has ended up from it),
            # but far enough now that continuing the chase makes no sense -
            # a big collision impulse or a string of dodge pushes can send
            # a ship well off its original course, and without this it
            # would otherwise fly toward the same distant target forever,
            # in an ever-so-slowly-converging straight line, rather than
            # picking something reachable nearby. Abandon and re-pick
            # (or fall through to the tether/idle handling below).
            self._release_claim(character)
            self.target_asteroid = self._pick_target(character, ship, asteroids)
            self._chase_timer = 0
        else:
            # Reached only when the target is still live, in range, and
            # non-None (the "not in asteroids" branch above already catches
            # None - nothing is ever "in" that list).
            self._chase_timer += 1
            if self._chase_timer > CHASE_TIMEOUT_FRAMES:
                # Been hunting the same rock for a long time without ever
                # landing the kill - it might just be drifting faster than
                # this ship can reliably close on (or dodge/collision
                # pushes keep interrupting the approach at just the wrong
                # moment). Either way, chasing it forever isn't productive -
                # give it a cooldown (see AVOID_COOLDOWN_FRAMES) so this
                # same miner doesn't just immediately re-pick it, and go
                # find something else.
                self._avoid[self.target_asteroid] = AVOID_COOLDOWN_FRAMES
                self._release_claim(character)
                self.target_asteroid = None
                self._chase_timer = 0
                character.firing = False
                ship.release_thrust()
                return

        # Trajectory safety comes first, every frame, before anything about
        # actually hunting: check whether any *other* asteroid's predicted
        # path is about to cross this ship's own (the hunted target itself
        # is excluded - closing on it is the point). A real threat both
        # nudges the ship clear and suppresses this frame's approach/fire
        # entirely, so the miner isn't still pressing the attack with one
        # hand while getting clipped by a rock with the other.
        urgency = getattr(character, "dodge_urgency", 1.0)
        severity = steer_away_from_asteroids(character, asteroids, ignore=self.target_asteroid, urgency=urgency)
        # Sticky, not recomputed bare each frame: once dodging starts, it
        # holds until severity drops below the lower EXIT_DODGE_SEVERITY,
        # not just back below the entry threshold - see that constant's own
        # comment for why (severity hovering right at the boundary would
        # otherwise flip this every frame).
        self._dodging = severity > EXIT_DODGE_SEVERITY if self._dodging else severity > URGENT_DODGE_SEVERITY
        if self._dodging:
            character.firing = False
            ship.release_thrust()
            return

        if self.target_asteroid is None:
            character.firing = False
            if self.station is not None and math.hypot(ship.x - self.station.x, ship.y - self.station.y) > HOME_TETHER_RANGE:
                # Nothing left to hunt out here and we've drifted well past
                # the home tether - head back rather than idle in deep
                # space waiting for a rock that may never come.
                self.phase = "returning"
            else:
                _brake(ship)
            return

        target = self.target_asteroid
        dx = target.x - ship.x
        dy = target.y - ship.y
        dist = math.hypot(dx, dy)
        speed = math.hypot(ship.velocity_x, ship.velocity_y)

        # Same sticky treatment as the dodge gate above: entering close-range
        # braking at PREFERRED_SPEED_CAP but only leaving it again once below
        # the lower EXIT_SPEED_CAP, so speed bleeding off gradually through
        # that band can't flip "brake" / "chase" back and forth every frame.
        self._braking_close = (
            speed > EXIT_SPEED_CAP and dist < PREFERRED_RANGE * 3 if self._braking_close
            else dist < PREFERRED_RANGE * 1.5 and speed > PREFERRED_SPEED_CAP
        )
        if self._braking_close:
            # Close to the target but still carrying too much speed to hold
            # position here - shed it (retrograde brake) instead of
            # thrusting straight past and into an endless pursuit-curve
            # orbit, the same close-range failure mode
            # docs/AUTOPILOT_TESTING.md documents for SeekMode's own
            # braking (see _brake()). Without this, "turn toward the
            # target's current bearing" alone never converges once
            # momentum carries the ship past it every pass - it just
            # circles forever, which at a glance reads as the ship being
            # stuck in place. Firing is skipped this frame since braking
            # points the nose away from the target.
            _brake(ship)
            character.firing = False
            return

        desired_deg = math.degrees(math.atan2(dx, -dy)) % 360
        diff = _signed_angle_delta(ship.angle, desired_deg)

        deadband = ship.rotation_speed * 0.5
        if diff > deadband:
            ship.turn_right()
        elif diff < -deadband:
            ship.turn_left()

        if abs(diff) < THRUST_CONE_DEG and dist > PREFERRED_RANGE:
            ship.increase_thrust()
        else:
            ship.release_thrust()

        character.firing = abs(diff) < FIRING_CONE_DEG and dist < FIRING_RANGE

    def _tick_avoid(self):
        for asteroid in list(self._avoid):
            remaining = self._avoid[asteroid] - 1
            if remaining <= 0:
                del self._avoid[asteroid]
            else:
                self._avoid[asteroid] = remaining

    def _pick_target(self, character, ship, asteroids):
        """Nearest asteroid within range that isn't already claimed by
        another miner (see _claim/SystemState.claimed_asteroids - lets
        several miners in the same belt split up instead of dogpiling one
        rock) and isn't on this miner's own recent-avoid list (see
        AVOID_COOLDOWN_FRAMES). Claims whatever it picks."""
        state = self._system_state(character)
        claimed = state.claimed_asteroids if state is not None else ()
        candidates = [
            a for a in asteroids
            if math.hypot(a.x - ship.x, a.y - ship.y) < ENGAGE_RANGE
            and a not in claimed and a not in self._avoid
        ]
        if self.station is not None:
            candidates = [a for a in candidates if math.hypot(a.x - self.station.x, a.y - self.station.y) < HOME_TETHER_RANGE]
        if not candidates:
            return None
        target = min(candidates, key=lambda a: math.hypot(a.x - ship.x, a.y - ship.y))
        self._claim(character, target)
        return target

    # --- Returning: fly back to the home station, still dodging along the way ---

    def _run_returning(self, character):
        """Low-level flight to the station, same shape as CombatRoutine's
        pursuit - but unlike closing on a combat target (where drifting
        past at speed doesn't matter), actually arriving requires shedding
        velocity too, which a plain "thrust while pointed at the goal"
        controller never does on its own (it just orbits, endlessly
        overshooting - see the docking braking phase below for the fix)."""
        ship = character.ship
        station = self.station
        asteroids = self._nearby_asteroids(character)
        urgency = getattr(character, "dodge_urgency", 1.0)
        severity = steer_away_from_asteroids(character, asteroids, urgency=urgency)
        self._dodging = severity > EXIT_DODGE_SEVERITY if self._dodging else severity > URGENT_DODGE_SEVERITY
        if self._dodging:
            # Something's about to cross the flight path home - let the
            # dodge nudge above do its work uncontested this frame instead
            # of fighting it with thrust toward the station.
            ship.release_thrust()
            return

        dx = station.x - ship.x
        dy = station.y - ship.y
        dist = math.hypot(dx, dy)
        speed = math.hypot(ship.velocity_x, ship.velocity_y)

        if dist < DOCK_ARRIVAL_DISTANCE and speed < DOCK_ARRIVAL_SPEED:
            self._begin_docking(character)
            return

        if dist < DOCK_ARRIVAL_DISTANCE * 3 and speed > DOCK_ARRIVAL_SPEED:
            # Close enough that arriving now means braking, not closing
            # further - see _brake().
            _brake(ship)
        else:
            desired_deg = math.degrees(math.atan2(dx, -dy)) % 360
            diff = _signed_angle_delta(ship.angle, desired_deg)
            deadband = ship.rotation_speed * 0.5
            if diff > deadband:
                ship.turn_right()
            elif diff < -deadband:
                ship.turn_left()
            if abs(diff) < THRUST_CONE_DEG:
                ship.increase_thrust()
            else:
                ship.release_thrust()

    # --- Docking: walk in, sell, walk out (see DockRoutine for the pattern this mirrors) ---

    def _begin_docking(self, character):
        ship = character.ship
        ship.park()
        station = self.station
        key = station.get_ship_entry_key()
        location = character.get_interior_screen(station, key) if character.get_interior_screen else None
        if location is None:
            # No walkable interior configured for this stop - sell in place
            # and go straight back out, same fallback DockRoutine uses.
            self._sell(character)
            self.phase = "hunting"
            return
        character.ashore = True
        self._location = location
        portal = location.portal_for(None)
        character.person.x, character.person.y = portal["x"], portal["y"]
        location.visitors.append(character.person)

        quartermaster = next((npc for npc in location.npcs if npc.person.role == "quartermaster"), None)
        goal = (quartermaster.person.x, quartermaster.person.y) if quartermaster else (character.person.x, character.person.y)
        self._set_waypoints(character.person, goal)
        self.phase = "walking_in"

    def _sell(self, character):
        """Convert whatever ore is in the hold into credits - see
        CREDITS_PER_ORE's own comment for why this is a flat AI-only
        conversion rather than a real commodities.json/sell_multiplier
        lookup."""
        possessions = character.person.possessions
        qty = possessions.cargo.get("ore", 0)
        if qty > 0:
            possessions.remove_cargo("ore", qty)
            possessions.earn(qty * CREDITS_PER_ORE)

    def _set_waypoints(self, person, goal):
        self._goal = goal
        self._waypoints = self._location.plan_path((person.x, person.y), goal)
        self._stuck_frames = 0
        self._replanned_while_stuck = False

    def _step_toward(self, person):
        """Move person one step toward the next waypoint - identical shape
        to DockRoutine._step_toward, including its stuck-recovery, so a
        miner can't freeze mid-walk the same way a dock-visiting pilot
        used to (see DockRoutine's own docstring)."""
        while self._waypoints:
            target_x, target_y = self._waypoints[0]
            if math.hypot(target_x - person.x, target_y - person.y) <= ARRIVAL_DISTANCE:
                self._waypoints.pop(0)
                continue
            speed = getattr(self._location, "speed", WALK_SPEED)
            x0, y0 = person.x, person.y
            person.step_toward(target_x, target_y, speed, self._location.can_move_to)
            if math.hypot(person.x - x0, person.y - y0) >= STUCK_STEP_EPSILON:
                self._stuck_frames = 0
                return False
            self._stuck_frames += 1
            if self._stuck_frames == STUCK_REPLAN_FRAMES and not self._replanned_while_stuck:
                self._replanned_while_stuck = True
                self._waypoints = self._location.plan_path((person.x, person.y), self._goal or (target_x, target_y))
            elif self._stuck_frames >= STUCK_GIVEUP_FRAMES:
                self._waypoints = []
                return True
            return False
        return True

    def _reboard(self, character):
        if self._location is not None and character.person in self._location.visitors:
            self._location.visitors.remove(character.person)
        character.ashore = False
        self._location = None
        self._release_claim(character)  # safety net - should already be None/unclaimed by the time cargo went full
        self.target_asteroid = None
        self.phase = "hunting"
