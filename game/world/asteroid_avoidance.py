"""Shared per-frame asteroid dodge nudge for any ship-flying Character.

Deliberately outside autopilot.py: it never touches SeekMode/OrbitMode or
issues turn/thrust commands, so it carries none of the regression risk
docs/AUTOPILOT_TESTING.md requires validating for changes to that file (the
same reasoning that keeps CombatRoutine off the autopilot surface). Instead
it applies a direct velocity nudge away from whatever asteroid's predicted
path most threatens to cross this ship's own - SeekMode/OrbitMode re-correct
for it next frame like they would for space drag - and low-level routines
(CombatRoutine, MinerRoutine) simply add it on top of their own turn/thrust
commands.

The threat check is a real closest-point-of-approach prediction (constant-
velocity extrapolation of both the ship and the asteroid), not just "is
something close right now" - so a fast asteroid still far away but on a
collision course gets reacted to before it's already on top of the ship,
and one that's merely nearby but drifting apart is left alone.
"""
import math

HORIZON_FRAMES = 150     # how far ahead (frames, ~2.5s at 60fps) to predict a crossing
CLEARANCE_PAD = 14       # extra buffer beyond asteroid.size + ship.size aimed for
DODGE_STRENGTH = 0.22    # fraction of max_velocity applied as a lateral push per frame, at closest range

# Once a ship commits to dodging one particular asteroid, keep dodging that
# same one for this many frames (as long as it's still actually a threat)
# before ever reconsidering which asteroid is "most urgent" - the sticky-
# decision fix documented in docs/AUTOPILOT_TESTING.md's "sticky-decision
# pitfall" applies just as much here: recomputing "which asteroid is worst"
# fresh every single frame lets two comparably-threatening rocks on either
# side of the ship flip which one "wins" from frame to frame, and each flip
# swings the dodge push to a near-opposite direction - the net effect over
# many frames is the pushes mostly cancel and the ship barely moves at all,
# which reads to a player as "the ship just sits there." Locking onto one
# threat and committing to dodging it (only reconsidering once it stops
# threatening, or the lock timer runs out) keeps every push pointed roughly
# the same way long enough to actually clear the danger zone.
DODGE_LOCK_FRAMES = 45


def _closest_approach(ship, asteroid):
    """(raw_time_to_closest_approach, clamped_time, predicted_separation_at
    the clamped time) - both ship and asteroid extrapolated at their
    current constant velocity, the standard closest-point-of-approach
    calculation. `raw_time` is left unclamped (and can be negative) so a
    caller can tell "closest approach is coming up" (>=0) apart from
    "closest approach already happened, we're now separating" (<0) - the
    clamped `time`/`separation` pair alone can't distinguish those, since
    both clamp to "right now" at zero. `time` itself is clamped to
    [0, HORIZON_FRAMES] (never negative, never further out than this
    function bothers predicting)."""
    dx = asteroid.x - ship.x
    dy = asteroid.y - ship.y
    rvx = asteroid.velocity_x - ship.velocity_x
    rvy = asteroid.velocity_y - ship.velocity_y
    rel_speed_sq = rvx * rvx + rvy * rvy
    raw_t = 0.0 if rel_speed_sq < 1e-6 else -(dx * rvx + dy * rvy) / rel_speed_sq
    t = max(0.0, min(HORIZON_FRAMES, raw_t))
    return raw_t, t, math.hypot(dx + rvx * t, dy + rvy * t)


def _threat_severity(ship, asteroid):
    """(time_to_closest_approach, severity in (0, 1]) if `asteroid`
    currently threatens `ship`'s predicted path, else None. Severity blends
    how tight the predicted miss margin is with how soon it happens while
    still approaching (raw_t >= 0); once past closest approach and
    separating (raw_t < 0) only the current overlap matters - see
    find_asteroid_threat's docstring for why that split exists (an earlier
    version conflated the two and livelocked ships near, but moving away
    from, any modestly close rock)."""
    clearance = asteroid.size + ship.size + CLEARANCE_PAD
    raw_t, t, min_sep = _closest_approach(ship, asteroid)
    if min_sep > clearance:
        return None
    margin_severity = 1.0 - min_sep / clearance if clearance > 0 else 1.0
    if raw_t >= 0:
        time_severity = 1.0 - t / HORIZON_FRAMES
        severity = max(0.05, min(1.0, (margin_severity + time_severity) / 2))
    else:
        severity = max(0.0, min(1.0, margin_severity))
    if severity <= 0:
        return None
    return t, severity


def find_asteroid_threat(character, asteroids, ignore=None):
    """The most urgent asteroid whose path threatens `character`'s ship, as
    (asteroid, time_to_closest_approach, severity) - severity in (0, 1].
    None if nothing on the list threatens. `ignore` skips one asteroid
    entirely (e.g. a miner's own hunted target, which it's supposed to be
    closing on, not dodging)."""
    ship = character.ship
    if not ship:
        return None
    best = None
    best_severity = -1.0
    for asteroid in asteroids:
        if asteroid is ignore:
            continue
        scored = _threat_severity(ship, asteroid)
        if scored is None:
            continue
        t, severity = scored
        if severity > best_severity:
            best_severity = severity
            best = (asteroid, t, severity)
    return best


def steer_away_from_asteroids(character, asteroids, ignore=None, urgency=1.0):
    """Nudge `character`'s ship velocity away from a threatening asteroid
    (skipping `ignore`). `urgency` (0..1, a pilot's own dodge_urgency - see
    pilots.json) scales how hard this personality reacts; 0 disables
    dodging entirely for a pilot who'd rather barrel through. Returns the
    threat's severity (0 if nothing threatened) so a caller can also gate
    its own behavior on it - e.g. a miner suppressing this frame's shot
    while it's busy getting clear of something about to cross its path.

    Sticks to whichever asteroid it last locked onto (see DODGE_LOCK_FRAMES)
    for at least a few frames rather than re-picking "the single most
    urgent one" fresh every frame - the lock itself lives on `character`
    (`_dodge_lock`/`_dodge_lock_timer`), so this is safe to call every
    frame for the same Character without the caller managing any state."""
    ship = character.ship
    if not ship or urgency <= 0:
        return 0.0

    locked = getattr(character, "_dodge_lock", None)
    lock_timer = getattr(character, "_dodge_lock_timer", 0)
    threat = None
    if locked is not None and locked is not ignore and locked in asteroids and lock_timer > 0:
        scored = _threat_severity(ship, locked)
        if scored is not None:
            t, severity = scored
            threat = (locked, t, severity)

    if threat is None:
        threat = find_asteroid_threat(character, asteroids, ignore=ignore)
        character._dodge_lock = threat[0] if threat else None
        character._dodge_lock_timer = DODGE_LOCK_FRAMES if threat else 0
    else:
        character._dodge_lock_timer = lock_timer - 1

    if threat is None:
        return 0.0
    asteroid, _, severity = threat

    dx = asteroid.x - ship.x
    dy = asteroid.y - ship.y
    dist = math.hypot(dx, dy)
    if dist < 0.01:
        dx, dy, dist = 1.0, 0.0, 1.0
    push = ship.max_velocity * DODGE_STRENGTH * severity * urgency
    nx, ny = -dx / dist, -dy / dist
    ship.velocity_x += nx * push
    ship.velocity_y += ny * push
    speed = math.hypot(ship.velocity_x, ship.velocity_y)
    if speed > ship.max_velocity:
        scale = ship.max_velocity / speed
        ship.velocity_x *= scale
        ship.velocity_y *= scale
    return severity
