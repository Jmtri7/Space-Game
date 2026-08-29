# Autopilot & Physics Routine Testing

## ⚠️ Before you touch `game/world/autopilot.py`

`SeekMode` and `OrbitMode` look like a few dozen lines of simple trig. They are not simple.
Multiple past attempts to improve this code *looked* correct in a manual playtest, passed the
standard battery, got committed - and still had a real, sometimes severe bug that only showed
up in specific geometric scenarios: a particular approach angle, a ship already moving at speed
when it engaged, a specific ship's rotation stat. One bug (a ship stopping 361 units off to the
side of its target) survived an entire session of "it looks fine" testing because nobody had
tried engaging autopilot while already moving perpendicular to the target. Most recently, a
two-step redesign (gating the braking commit on along-track velocity, then adding a turn-radius
speed cap on top of that) passed the standard battery and got committed, and *still* had to be
reverted - it only showed up once someone re-ran the numbers broken out per ship instead of
trusting a patrol-focused headline result. See "Rejected approaches" below for the detail.

**Rule: any change to `SeekMode`, `OrbitMode`, or the shared helpers they call
(`point_and_thrust`, `turn_toward`, `predict_braking_distance_from_stop`, `retrograde_angle`,
`velocity_components`, `opposing_angle`) must be validated against the battery below before
it gets committed - not just flown once in the live game, and not just checked for one ship
type.** A change that "feels better" when you fly it manually, or that improves patrol's
numbers, can still be a net regression for freighter or shuttle, or in a scenario range the
battery you happened to run doesn't reach. This has bitten the project more than once even with
someone actively looking for it.

If someone asks you to change autopilot behavior, tell them up front that it's a routine with a
history of subtle regressions and that you'll validate with the standard battery - broken out
per ship, not just aggregated - before calling it done. This doc is what that means in practice.

## The protocol

1. **Before changing anything**, run the current code through the battery (below) and record
   the numbers, per ship type. This is your baseline.
2. **Make the change.**
3. **Re-run the exact same battery.** Compare against the baseline explicitly, per ship, number
   to number - not "it seems fine," and not just the ship type the change was aimed at. A fix
   for one ship's problem can quietly cost another ship real performance; that has already
   happened here.
4. A change is acceptable only if it doesn't regress the baseline *for any ship*, *or* the
   regression is an explicit, understood trade-off you can name (e.g. "freighter now takes ~4%
   longer on average, but zero trials fail outright, was 3/312 before"). Silently absorbing a
   worse number because the headline metric improved is exactly how several past regressions
   survived initial testing.
5. **If a design idea fails, say so in a code comment**, not just in chat history. Several ideas
   have failed here for non-obvious reasons (see "Rejected approaches" below) - the comments in
   `autopilot.py` recording *why* are there specifically so nobody re-tries them blind next time.
6. Run `python run_tests.py` and do a live restart per the project's standing workflow before
   considering it done. The automated tests don't cover this (see "What the battery covers that
   `test_helpers.py` doesn't" below) - they're a floor, not a substitute for the battery.

## Real ship stats - don't guess these

Pull current values from `config/stories/{story}/ship_types.json` every time. Do not reuse
numbers from memory or an earlier conversation. This has bitten the project directly before: an
entire round of "validated" sweeps used an invented `patrol` preset `(accel=0.25, max_v=5.5,
rot=7)` instead of the real one `(0.35, 5.0, 7)` - close enough to look plausible, wrong enough
to hide real failures. The real stats as of this writing:

| Ship type | max_thrust (accel) | max_velocity | rotation_speed | Actually runs SeekMode in-game? |
|---|---|---|---|---|
| `shuttle` | 0.12 | 2.0 | 4 | Yes - the player's ship (`story.json`'s `player_type`) |
| `freighter` / `drossholt_freighter` | 0.1 | 2.0 | 1 | Yes - `DockRoutine`/`ShuttleRoutine` |
| `patrol` / `drossholt_patrol` | 0.35 | 5.0 | 7 | Not currently - `patrol_officer` role uses `OrbitMode`, never `engage_seek` |

Test all three anyway. "Not currently reachable" changes fast (the user has already said patrol
will likely become player-playable, and patrol AI may want to land someday) - don't use
unreachability as an excuse to skip validating it, only as context for how much a given
regression matters *right now*. It also doesn't mean patrol testing can be skipped for other
reasons: patrol's fast speed and tight turn rate make it the ship type most likely to expose a
new bug even though it isn't reachable in normal play yet.

## The standard battery

Headless simulation, not the live window - construct real `Ship`/`LandingSite` objects and drive
`.update()` in a loop. This is the only way to run hundreds of scenario permutations; doing it
by hand in the live game is not practical and won't catch angle-specific bugs.

### Scenario set (SeekMode)

1. **At-rest matrix**: ship starts at velocity zero, at each of several distances × several
   angles from the target. (Session default: 11 distances from 100-1800, 12-24 angles across
   360°.) This is the scenario every version of this code has actually been tested against -
   necessary but *not sufficient*, since velocity is always naturally aligned with the target
   by the time braking matters.
2. **Pre-existing-velocity matrix**: ship starts already moving, at various speeds (as a
   fraction of `max_velocity`) and various angles *relative to the direction to the target*
   (not relative to the approach direction) - 30° through 180° off-target in the session's
   sweep. This is the one that's easy to skip and the one that matters: it's what actually
   happens when a player flies past something and then targets it, or when any ship's
   `engage_seek` gets called while it's mid-maneuver from something else. **Do not ship an
   autopilot change without this matrix** - the worst bugs found in this file only show up here.
3. **Combined sweep**: cross the two above (varying approach angle *and* initial velocity angle
   *and* speed fraction together) for full coverage - this is what caught a genuinely rare
   failure case (a slow-turning ship at ~120° velocity offset settling into a stable
   oscillation) that neither matrix alone surfaced.
4. **Close-range pursuit sweep**: a separate, tighter-radius matrix (80-150 units - inside the
   standard pre-existing-velocity matrix's minimum distance) exists specifically because a
   fast, tight-turning ship close to a target it's still moving past at an angle can enter a
   stable pursuit-curve loop - always turning toward the target's current bearing, never
   tightly enough to close the gap - that the wider-radius matrices don't reach. See "Rejected
   approaches" below for the regression this sweep caught.

Run every matrix broken out **per ship type**, not aggregated - see "Rejected approaches" for
why an aggregated or single-ship-type number let a real regression through undetected.

### Scenario set (OrbitMode)

Time-to-stabilize instead of time-to-land: start the ship somewhere off the target radius,
`engage_orbit`, and track the orbit radius over a sliding window (session default: 60 frames)
until it stops varying by more than a few percent. Record that frame count *and* the settled
radius - `OrbitMode` intentionally settles a bit wider than the configured radius (a faster
ship needs a wider turn at a fixed rotation rate), so "stabilizes" means "stops changing," not
"matches the configured value." Also run a long-horizon check (several thousand frames) to
confirm it doesn't drift or diverge once settled - this mode has no arrival condition, so a
slow divergence would otherwise go unnoticed.

### Metrics to record every time

- **Time to finish** (SeekMode: frames until `autopilot_active` goes False) **or time to
  stabilize** (OrbitMode: frames until the radius window test above passes) - mean, median,
  max, across the battery.
- **Overshoot**: track the minimum distance-to-target seen so far each frame; flag a trial if
  distance later increases more than ~5 units while still within ~30% of the target's
  `landing_distance`. Report both the count of trials that trigger this and the max magnitude.
- **Turnarounds**: count of trials where a sticky "committed" flag (e.g. `SeekMode.braking`)
  flips back off mid-flight - visible in-game as the ship reversing course. Report both how
  many trials have at least one, and the total count summed across all trials (a trial can
  turn around more than once).
- **Jitter / direction reversals**: count frames where the turn direction (left vs. right)
  flips sign. A nonzero count clustered right near arrival almost always means some decision
  is being recomputed fresh every frame instead of held sticky - see "The sticky-decision
  pitfall" below before you go looking for any other cause. A single trial with a reversal
  count far above the rest of the battery (tens instead of single digits) is exactly this bug -
  see "Rejected approaches" for a real example.
- **Failure rate**: run with a generous but bounded frame cap (well above `MAX_SEEK_FRAMES`,
  e.g. 8000) and count any trial that hits the cap without `autopilot_active` going False, plus
  any that "land" but leave the ship far from center or still moving fast (a reasonable
  threshold: final distance > 20 units, or final speed > 0.05).
- **First-stop miss, decomposed into along-track vs. lateral**: aggregate "final distance"
  numbers can hide a bad first attempt that a later un-stick/re-approach cycle happens to
  correct - which is exactly what a player sees as "sometimes it stops off to the side,
  sometimes it stops short," even when the *eventual* landing looks fine in the aggregate data.
  To see it: track the first frame where speed drops below `ARRIVAL_SPEED_THRESHOLD` after
  having genuinely been in flight (not the trivial at-rest frame 0), take the miss vector (ship
  position minus target position) at that frame, and project it onto the straight line from the
  scenario's start position to the target: the along-axis component is how far short (negative)
  or overshot (positive) the first stop was; the perpendicular component is how far off to the
  side. This decomposition is what originally surfaced a spin-stall bug whose aggregate
  "final distance" numbers looked completely fine - only the *first* stop showed the wasted
  detour that got there. The fix for that bug (skip the alignment-gated "would braking help"
  check once speed drops below `ARRIVAL_SPEED_THRESHOLD`) is built into the current code - see
  the version-history entry below.

### What the battery covers that `test_helpers.py` doesn't

`tests/test_helpers.py`'s `TestAutopilotPhysics` locks in exactly one scenario per ship type
(a single start distance, at rest, along one axis) as a fast regression guard for CI/pre-
commit - useful, but nowhere near the coverage above. Treat it as a smoke test, not evidence
that a change is safe. Extend it if a new scenario ever turns out to matter enough to guard
permanently (e.g. if a future change is specifically about the pre-existing-velocity case,
consider adding one such case there) - but the full battery is what you actually validate
against before committing.

## The sticky-decision pitfall

This bit the project more than once, in the same shape every time:

1. A decision is recomputed fresh every frame (e.g. "should I be braking right now?").
2. Right at the decision's own threshold, tiny frame-to-frame changes (discretization,
   floating-point noise) flip the answer back and forth.
3. Each flip swings the ship's commanded heading to something wildly different (e.g.
   retrograde vs. pointed at the target - nearly opposite directions), so the ship spends many
   frames re-turning instead of ever holding a heading long enough to actually thrust.
4. Fix: make the flag sticky - once it flips true, hold it true until some *other*, explicit
   condition clears it (arrival, an un-stick bailout, a fresh commitment starting over) -
   never just "recompute the same threshold check every frame."

The second time this happened, it was a nested instance of the *same* bug: the outer
`self.braking` flag was already sticky, but a new decision made *inside* the braking branch
(`self.cross_track_done`) wasn't, and it flickered on the exact same class of noise. A later,
now-reverted attempt hit it a third time in a completely different spot - a proposed speed cap
compared directly against a live per-frame value instead of being folded into the existing
sticky commit. If you add any new decision point anywhere in this file, ask whether it needs
its own stickiness before you ship it - don't wait to rediscover this by tracing a failing
trial.

## Rejected approaches (don't re-try these blind)

Recorded here and in code comments in `autopilot.py`:

- **Widening the thrust-alignment gate during braking** (thrusting before fully turned to
  face retrograde, to shorten the coast phase). Made things worse: thrust that far off pure
  retrograde has a real sideways component that needs correcting afterward - net slower at
  45°, unstable at 60° (reintroduced overshoot), and outright failed to converge at 90° in one
  trial. The alignment gate stayed at the original 10° used everywhere else.
- **Lowering the braking safety buffer below 1.0** to make the slow-turning freighter
  correct faster. Reduces freighter's remaining turnarounds, but reintroduces real overshoot
  for other ship types and starts stranding ships outright past ~0.9. Not worth it for how far
  it goes.
- **Replacing the whole approach/brake split with one continuous "chase the velocity you'd
  need to arrive at zero speed" law** (the same style of redesign that worked well for
  `OrbitMode` in an earlier session). Failed completely in prototype - every single at-rest
  baseline trial ran out an 8000-frame budget without landing. Suspected cause: a pure
  proportional law with real turn-lag feeding back into a continuously-shifting target
  velocity limit-cycles instead of converging, but this was never proven, just observed. Never
  touched `autopilot.py` - caught in prototype before it got anywhere near a commit.
- **Throttling approach speed by `sqrt(2·a·distance)`** using the ship's *total* speed. Broke
  catastrophically for the pre-existing-velocity matrix (final distances up to 15,000 units)
  because a ship carrying a large *sideways* speed component looks "already too fast" by this
  check even though it's making zero progress toward the target, so it never thrusts to
  correct course at all. If you build a speed-based throttle, gate it on the *along-track*
  velocity component specifically, not total speed.
- **Using the angle between current and desired velocity for `CROSS_TRACK_KILL_THRESHOLD`**,
  instead of the cross-track velocity's raw magnitude. Tested at 5/10/20/30 degrees - even the
  loosest still left 17/48 angled trials bad (magnitude-based gets 0/648 on the larger
  equivalent sweep), and the tightest (5 degrees) was outright catastrophic: freighter's
  at-rest mean time nearly tripled (829.6 -> 2204.6 frames) with a 672-unit overshoot, patrol
  spiked to a 7692-unit miss. Same root problem as the throttle above: an angle can't tell a
  meaningful sideways drift at real speed apart from noise at near-zero speed (the same
  `retrograde_angle` instability the low-speed bailout works around elsewhere - see
  `SeekMode.update()`), so it's systematically wrong in exactly the regime where this decision
  matters most. Magnitude has no such ambiguity - it directly measures the physical quantity
  that matters (how much sideways motion actually remains), independent of scale.
- **Gating the braking commit on along-track speed instead of total speed, then adding a
  turn-radius speed cap on top of that** - a two-step redesign that got as far as being
  implemented, validated against the standard battery, and committed (twice), before being
  reverted. The along-track gate did fix a real, narrow problem (freighter's lateral miss at
  first stop: mean 25.1 -> 20.5 units, max 458.7 -> 308.1, in the standard battery) - but
  re-running the numbers broken out **per ship type** on both the standard battery and a
  dedicated close-range pursuit sweep (see the battery's scenario list above) showed it
  regressed almost everything else, for every ship, not just the one it was aimed at: freighter's
  max direction-reversal count per trial went from 5 to 20 (4x more jitter), freighter started
  hitting the `MAX_SEEK_FRAMES` watchdog at all (never did before), freighter's overshoot-event
  count rose (69/312 -> 80/312), shuttle's close-range overshoot-event count rose over 13x
  (4/216 -> 53/216), and - the one that was actually noticed first - patrol gained a genuinely
  new failure mode close to a target (0/216 bad -> 16/216 bad), a pursuit-curve stall that
  simply didn't exist before this change. The turn-radius cap added on top fixed that specific
  patrol regression back to 0/216 bad, but didn't recover the rest, and didn't even keep the
  along-track gate's one real win: with the cap in place, freighter's lateral miss (25.5/458.7)
  landed right back where it started. Two separate lessons here: (1) the cap's *first*
  implementation - an independent per-frame `speed > turn_cap` check - hit the sticky-decision
  pitfall again in a new spot (56 direction reversals in one traced trial, from `distance`
  itself oscillating a few units per frame while the ship circled) before being refolded into
  the existing sticky commit; (2) even after fixing that, the net result across the whole
  redesign was still a regression once measured honestly per ship instead of trusting the
  ship-specific number the change was aimed at improving. If freighter's lateral-miss magnitude
  ever needs revisiting, start from the current (reverted-to) baseline, not from resurrecting
  this line of changes wholesale.

## Version history and how to revert surgically

Changes to this file should touch *only* `SeekMode`'s `update()` method and its immediately
adjacent helpers/constants - never `ship.py`, `player_controller.py`, `character.py`, or any
screen. That keeps reverting to a known-good version a single-file operation:

```bash
git show <commit>:game/world/autopilot.py > game/world/autopilot.py
python run_tests.py   # confirm it's still green, then restart the game per the standing workflow
```

| Name | Commit | Summary |
|---|---|---|
| **V1** — Two-Phase Braking, Immediate Low-Speed Bailout (current) | `996c092` | Once committed to braking, decomposes velocity into along-track/cross-track components and nulls the cross-track part first (sticky, one check per commitment) before switching to a pure retrograde burn - fixes a ship stopping well off to the side of its target when velocity wasn't already pointed at the target on commit. Also skips the alignment-gated "would braking still help" check once speed drops below `ARRIVAL_SPEED_THRESHOLD`, going straight to accept-or-resume instead - fixes a spin-stall where `retrograde_angle`'s noise on a near-zero velocity vector could leave a ship spinning in place for a long stretch (traced case: ~150 wasted frames) before either escaping by chance or hitting the `MAX_SEEK_FRAMES` watchdog. This is a restore of an earlier, already-validated point in this file's history (previously tagged "V4" under a longer naming scheme that has since been retired - see "Rejected approaches" above for why the two versions that superseded it were reverted). Full battery and a dedicated close-range pursuit sweep, all three ship types, 0 bad trials either way; `run_tests.py` 21/21. |

Earlier naming (`V1`-`V6b`) tracked a longer sequence of attempts and is no longer preserved
here as a table - the lessons from that history that are still worth keeping are folded into
"Rejected approaches" above instead. If you need the raw commit history beyond what's recorded
there, `git log -- game/world/autopilot.py` is authoritative.

## If you change this next

- Run the protocol above. Don't skip the pre-existing-velocity matrix or the close-range
  pursuit sweep even if the change seems purely about the at-rest case - the worst regressions
  in this file's history didn't look related to velocity-on-engage or close range until traced.
- Run every matrix **broken out per ship type**, not aggregated, and don't stop at the ship
  type the change was aimed at - the most recent regression here was only caught because
  someone re-checked the "unaffected" ship types instead of taking that on faith.
- Update the version-history table with a new row, commit hash, and one-line summary once a
  change actually supersedes the current baseline.
- Add a per-ship, metric-by-metric comparison (old vs. new, every ship type, every metric from
  the protocol) if the change touches `SeekMode` - the ship-by-ship format is what's caught
  every non-obvious trade-off in this file so far; a single aggregated number has repeatedly
  hidden one.
- If an idea fails, add it to "Rejected approaches" with *why*, even if it embarrasses the
  attempt - that's the whole point of the section.
