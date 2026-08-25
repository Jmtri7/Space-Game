# Autopilot & Physics Routine Testing

## ⚠️ Before you touch `game/world/autopilot.py`

`SeekMode` and `OrbitMode` look like a few dozen lines of simple trig. They are not simple.
Every version documented below *looked* correct in a manual playtest and still had a real,
sometimes severe bug that only showed up in specific geometric scenarios - a particular
approach angle, a ship already moving at speed when it engaged, a specific ship's rotation
stat. One bug (a ship stopping 361 units off to the side of its target) survived an entire
session of "it looks fine" testing because nobody had tried engaging autopilot while already
moving perpendicular to the target.

**Rule: any change to `SeekMode`, `OrbitMode`, or the shared helpers they call
(`point_and_thrust`, `turn_toward`, `predict_braking_distance_from_stop`, `retrograde_angle`,
`velocity_components`, `opposing_angle`) must be validated against the battery below before
it gets committed - not just flown once in the live game.** A change that "feels better" when
you fly it manually can still be a net regression across the scenarios you didn't happen to
try. This has already happened twice (see the V3 write-up below) even with someone actively
looking for it.

If someone asks you to change autopilot behavior, tell them up front that it's a routine with
a history of subtle regressions and that you'll validate with the standard battery before
calling it done - this doc is what that means in practice.

## The protocol

1. **Before changing anything**, run the current code through the battery (below) and record
   the numbers. This is your baseline.
2. **Make the change.**
3. **Re-run the exact same battery.** Compare against the baseline explicitly - number to
   number, not "it seems fine."
4. A change is acceptable only if it doesn't regress the baseline, *or* the regression is an
   explicit, understood trade-off you can name (e.g. "freighter now takes ~4% longer on
   average, but zero trials fail outright, was 3/312 before"). Silently absorbing a worse
   number because the headline metric improved is exactly how the buffer bug and the
   perpendicular-velocity bug both survived past initial testing.
5. **If a design idea fails, say so in a code comment**, not just in chat history. Multiple
   ideas this session failed for non-obvious reasons (see "Rejected approaches" below) - the
   comments in `autopilot.py` recording *why* are there specifically so nobody re-tries them
   blind next time.
6. Run `python run_tests.py` and do a live restart per the project's standing workflow before
   considering it done. The automated tests don't cover this (see "What the battery covers
   that `test_helpers.py` doesn't" below) - they're a floor, not a substitute for the battery.

## Real ship stats - don't guess these

Pull current values from `config/stories/{story}/ship_types.json` every time. Do not reuse
numbers from memory or an earlier conversation. This bit us directly this session: an entire
round of "validated" sweeps used an invented `patrol` preset `(accel=0.25, max_v=5.5, rot=7)`
instead of the real one `(0.35, 5.0, 7)` - close enough to look plausible, wrong enough to
hide real failures. The real stats as of this writing:

| Ship type | max_thrust (accel) | max_velocity | rotation_speed | Actually runs SeekMode in-game? |
|---|---|---|---|---|
| `shuttle` | 0.12 | 2.0 | 4 | Yes - the player's ship (`story.json`'s `player_type`) |
| `freighter` / `drossholt_freighter` | 0.1 | 2.0 | 1 | Yes - `DockRoutine`/`ShuttleRoutine` |
| `patrol` / `drossholt_patrol` | 0.35 | 5.0 | 7 | Not currently - `patrol_officer` role uses `OrbitMode`, never `engage_seek` |

Test all three anyway. "Not currently reachable" changes fast (the user has already said
patrol will likely become player-playable, and patrol AI may want to land someday) - don't
use unreachability as an excuse to skip validating it, only as context for how much a given
regression matters *right now*.

## The standard battery

Headless simulation, not the live window - construct real `Ship`/`Landable` objects and drive
`.update()` in a loop. This is the only way to run hundreds of scenario permutations; doing it
by hand in the live game is not practical and won't catch angle-specific bugs.

### Scenario set (SeekMode)

1. **At-rest matrix**: ship starts at velocity zero, at each of several distances × several
   angles from the target. (Session default: 11 distances from 100-1800, 12-24 angles across
   360°.) This is the scenario every prior version of this code was actually tested against -
   necessary but *not sufficient*, since velocity is always naturally aligned with the target
   by the time braking matters.
2. **Pre-existing-velocity matrix**: ship starts already moving, at various speeds (as a
   fraction of `max_velocity`) and various angles *relative to the direction to the target*
   (not relative to the approach direction) - 30° through 180° off-target in the session's
   sweep. This is the one that's easy to skip and the one that matters: it's what actually
   happens when a player flies past something and then targets it, or when any ship's
   `engage_seek` gets called while it's mid-maneuver from something else. **Do not ship an
   autopilot change without this matrix** - both the "stops off to the side" bug and the
   trade-offs in the V3 write-up below only show up here.
3. **Combined sweep**: cross the two above (varying approach angle *and* initial velocity
   angle *and* speed fraction together) for full coverage - this is what caught the one
   genuinely rare failure case (a slow-turning ship at ~120° velocity offset settling into a
   stable oscillation) that neither matrix alone surfaced.

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
  pitfall" below before you go looking for any other cause.
- **Failure rate**: run with a generous but bounded frame cap (the session used 8000, well
  above `MAX_SEEK_FRAMES`) and count any trial that hits the cap without `autopilot_active`
  going False, plus any that "land" but leave the ship far from center or still moving fast
  (session threshold: final distance > 20 units, or final speed > 0.05).
- **First-stop miss, decomposed into along-track vs. lateral**: aggregate "final distance"
  numbers can hide a bad first attempt that a later un-stick/re-approach cycle happens to
  correct - which is exactly what a player sees as "sometimes it stops off to the side,
  sometimes it stops short," even when the *eventual* landing looks fine in the aggregate
  data. To see it: track the first frame where speed drops below `ARRIVAL_SPEED_THRESHOLD`
  after having genuinely been in flight (not the trivial at-rest frame 0), take the miss
  vector (ship position minus target position) at that frame, and project it onto the
  straight line from the scenario's start position to the target: the along-axis component is
  how far short (negative) or overshot (positive) the first stop was: the perpendicular
  component is how far off to the side. This is what found the V4 spin-stall - the aggregate
  "final distance" numbers for that scenario looked fine (V3 already converged eventually),
  and only decomposing the *first* stop surfaced the wasted detour that got there.

### What the battery covers that `test_helpers.py` doesn't

`tests/test_helpers.py`'s `TestAutopilotPhysics` locks in exactly one scenario per ship type
(a single start distance, at rest, along one axis) as a fast regression guard for CI/pre-
commit - useful, but nowhere near the coverage above. Treat it as a smoke test, not evidence
that a change is safe. Extend it if a new scenario ever turns out to matter enough to guard
permanently (e.g. if a future change is specifically about the pre-existing-velocity case,
consider adding one such case there) - but the full battery is what you actually validate
against before committing.

## The sticky-decision pitfall

This bit the project twice in one day, in the same shape both times:

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
(`self.cross_track_done`) wasn't, and it flickered on the exact same class of noise. If you
add any new decision point inside an already-sticky branch, ask whether it needs its own
stickiness before you ship it - don't wait to rediscover this by tracing a failing trial.

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
  `retrograde_angle` instability V4 works around elsewhere), so it's systematically wrong in
  exactly the regime where this decision matters most. Magnitude has no such ambiguity - it
  directly measures the physical quantity that matters (how much sideways motion actually
  remains), independent of scale.
- **Turn-radius speed cap as its own independent per-frame check in Step 3** (V6b's first
  draft), instead of folding it into Step 2's existing sticky commit. Same shape as the
  sticky-decision pitfall above, just in a new spot: right at the cap boundary, `distance`
  itself oscillates a few units per frame while the ship is mid-circle, so the raw
  `speed > turn_cap` comparison flickered true/false and swung the heading between retrograde
  and point-at-target every single frame - 56 direction reversals in one traced trial (patrol,
  100-unit range, 60-degree velocity offset, max speed), worse than the pursuit-curve stall it
  was meant to fix. The eventual fix reused the already-sticky `self.braking` flag instead of
  adding a second, independently-flippable decision - see "The sticky-decision pitfall" above:
  *any* new decision point needs to ask this question before shipping, not just the first one
  that got bitten by it.

## Version history and how to revert surgically

Every version below changed *only* `game/world/autopilot.py`, and within it, only
`SeekMode`'s `update()` method and its immediately adjacent helpers/constants - never
`ship.py`, `player_controller.py`, `ai_ship.py`, or any screen. That means reverting to a
known-good version is always a single-file operation:

```bash
git show <commit>:game/world/autopilot.py > game/world/autopilot.py
python run_tests.py   # confirm it's still green, then restart the game per the standing workflow
```

| Name | Commit | Summary |
|---|---|---|
| Pre-session | `98818fe` and earlier | Blended retrograde: 70% opposite-velocity + 30% redirect-toward-target while braking. Never converged cleanly - fought its own heading every frame. |
| **V1** — Sticky Pure Retrograde, No Buffer | `2c14277` | Pure retrograde burn (no redirect blend) once committed, *sticky* commitment (doesn't re-evaluate should-I-brake every frame), no safety buffer on the braking-distance estimate. Fixed the old blend's flip-flopping and a separate "brakes early, stops short" bug. Still vulnerable to stopping off to the side if velocity wasn't already pointed at the target when it committed. |
| **V2** — Alignment-Gated Retrograde Braking | `f1a289c` | V1 + won't commit to a retrograde burn until velocity is already within 45° of the target direction; lets the normal point-at-target approach cancel any sideways drift first. Fixes the "stops off to the side" bug by *waiting it out*. |
| **V3** — Two-Phase (Cross-Track then Retrograde) Braking | `ed4cfe1` | Replaces V2's wait-and-see gate with an active correction: decomposes velocity into along-track/cross-track components on commit, burns to null the cross-track part first (sticky, one check per commitment), *then* switches to the proven pure-retrograde burn. Fixes the same bug by *actively correcting* instead of waiting. |
| **V4** — Two-Phase Braking, Immediate Low-Speed Bailout | `4a51a2e` | V3 + skips the alignment-gated "would braking still help" check once speed drops below `ARRIVAL_SPEED_THRESHOLD`, going straight to accept-or-resume instead. Fixes a spin-stall: below that speed, `retrograde_angle` is noisy (atan2 of a near-zero vector), and both the thrust-would-help check and the un-stick bailout it guards required alignment first - so a ship could spin chasing a jittering target for a long stretch (measured: ~150 wasted frames in one traced case) before either escaping by chance or hitting the `MAX_SEEK_FRAMES` watchdog. |
| **V5** — Along-Track-Gated Commit | `db07c2e` | Gates the braking commit decision (`predict_braking_distance_from_stop`'s input) on along-track speed - the component actually closing on the target - instead of total speed. Total speed dominated by sideways drift made the model commit to braking on a schedule that assumed all of it was useful, leaving cross-track-kill to correct almost an entire velocity vector from a standing start. Root-cause fix for "stops off to the side": freighter's mean lateral miss at first stop dropped from 96.2 to 58.6 units (max 582.1 -> 422.3), patrol's worst along-track shortfall from 313.6 to 8.6. One accepted regression: 3/648 in the wide angled sweep (all patrol at 100-unit point-blank range) land ~78 units off instead of within tolerance - patrol doesn't currently run this code in real gameplay. |
| **V6b** — Turn-Radius-Gated Commit (current) | `538e921` | Adds a second Step 2 commit trigger alongside V5's along-track one: speed exceeding `distance * radians(rotation_speed) * 0.5`, a rough gauge of how far the ship's own turn rate could still redirect it at the current range. Fixes a pursuit-curve failure unique to patrol: a fast, slow-turning ship close to the target but still carrying speed at an angle could get stuck always turning toward the target's current bearing without ever closing the gap - a stable circling loop, not a bug that resolves itself given more frames. Close-range pursuit sweep (216 trials, 80-150 unit range): patrol's bad-trial rate 16/216 -> 0/216, mean landing time 340.4 -> 126.7 frames. Shuttle unaffected (never reaches its own cap in testing). Freighter: genuine mixed trade-off, not a clean win - mean/overshoot-count improve slightly, but max lateral miss at first stop grows (308.1 -> 458.7) since its very slow turn rate (1 deg/frame) gives it a tiny cap that now commits it to braking earlier than the along-track model alone would have; still 0/312 failures either way. A first attempt implemented the same cap as an independent per-frame check in Step 3 instead of folding it into Step 2's sticky commit - see "Rejected approaches" below. |

## V2 vs. V3, in detail

Descriptive names above are what to call these in conversation - "V2"/"V3" alone won't mean
anything once more versions exist. Numbers below are from the full combined battery (at-rest
+ pre-existing-velocity matrices, 312 trials per ship per version: 132 at-rest scenarios × 11
distances × 12 angles, plus 180 pre-existing-velocity scenarios × 5 distances × 3 approach
angles × 6 velocity-offset angles × 2 speed fractions), all three real ship stats, all
autopilot-relevant metrics from the protocol above.

| Ship | Version | Mean frames | Median | Max frames* | Overshoot rate | Max overshoot | Trials w/ ≥1 turnaround | Total turnarounds | Max direction reversals | Failed/bad |
|---|---|---|---|---|---|---|---|---|---|---|
| shuttle | V2 | 345.5 | 278 | 957 | 0% (0/312) | 0.0 | 30/312 | 30 | 1 | 0 |
| shuttle | V3 | 345.5 | 278 | 957 | 0% (0/312) | 0.0 | 30/312 | 30 | 1 | 0 |
| freighter | V2 | 872.9 | 809 | 3000* | 21.2% (66/312) | 18.0 | 286/312 | 380 | 15 | 0 |
| freighter | V3 | 904.0 | 849.5 | 3000* | 22.8% (71/312) | 17.0 | 286/312 | 440 | 16 | 0 |
| patrol | V2 | 203.2 | 157 | 3000* | 15.1% (47/312) | 8.0 | 162/312 | 162 | 3 | 3 |
| patrol | V3 | 176.9 | 161 | 401 | 17.3% (54/312) | 8.0 | 165/312 | 171 | 3 | **0** |

\* 3000 = `MAX_SEEK_FRAMES` watchdog engaged for at least one trial (forced an imprecise but
bounded stop rather than looping); patrol under V3 never needs it (max 401).

**Reading this honestly, not just picking the flattering number for each:**

- **Shuttle** (the player's own ship): completely unaffected either way - identical numbers
  across every metric. Its velocity is already aligned with the target by the time braking
  matters in every scenario tested here, so the cross-track phase never has anything to do.
- **Patrol**: V3 is a clean win - faster on average (177 vs. 203 frames), never needs the
  frame watchdog (max 401 vs. 3000), and zero failed trials (was 3/312 under V2).
- **Freighter**: a genuine, non-flattering trade-off, not a clean win. V3 is ~4% slower on
  average (904 vs. 873 frames), has a slightly *higher* overshoot rate (71 vs. 66 trials, out
  of 312), and needs more total turnaround cycles (440 vs. 380) - the extra cross-track-kill
  phase costs real time for a ship with a 1°/frame rotation speed, since *any* extra
  reorientation is expensive for it. Overshoot magnitude and failure count are unchanged (0
  either way). This is the ship type to watch if a future change tries to "improve" this
  further - it's already the hardest case, by a wide margin (compare its turnaround/reversal
  counts to shuttle's).

A narrower, angled-only sweep run earlier in the same session (no at-rest scenarios, 648
trials total across all three ships, looser bad-thresholds) showed V3 at 0/648 bad vs. V2's
12/648 - a more flattering picture than the comprehensive table above, entirely because that
sweep under-represents the at-rest and moderate-velocity cases where freighter's V3 costs show
up. This is itself the lesson: **battery composition changes the story - always compare
against the same battery, and prefer the more comprehensive one when the numbers disagree.**

## V4 vs. V5 vs. V6b on close range - no version dominates every metric, and it's not patrol-only

A dedicated close-range pursuit sweep (216 trials/ship: distances 80-150, 3 approach angles, 6
velocity-offset angles, 3 speed fractions - see `battery.py`-style scenario generation, not yet
folded into an automated test) exists specifically because the standard battery's minimum
pre-existing-velocity distance (200) doesn't reach the regime patrol's pursuit-curve stall lives
in. An earlier draft of this section only tabulated patrol and claimed shuttle/freighter were
"unaffected" - that was wrong; all three ships show the same shape, just less severely than
patrol's headline 16/216 bad:

| Ship | Version | Mean frames | Max frames | Bad | Overshoot events | Lateral miss (mean/max) |
|---|---|---|---|---|---|---|
| shuttle | V4 | **156.7** | 223 | 0/216 | **4/216** | 34.3 / 130.3 |
| shuttle | V5 | 163.4 | 223 | 0/216 | 53/216 | 31.2 / 100.8 |
| shuttle | V6b | 163.3 | 223 | 0/216 | 53/216 | 31.3 / 100.8 |
| freighter | V4 | **504.3** | **1166** | 0/216 | **91/216** | 105.0 / 417.3 |
| freighter | V5 | 625.7 | 2376 | 0/216 | 127/216 | 109.0 / 413.5 |
| freighter | V6b | 542.8 | 2376 | 0/216 | 104/216 | 109.4 / 417.3 |
| patrol | V3 | 121.1 | 209 | 0/216 | 61/216 | 37.5 / 178.4 |
| patrol | V4 | **107.4** | **197** | 0/216 | **56/216** | 38.4 / 183.9 |
| patrol | V5 | 340.4 | 3001* | **16/216** | 112/216 | 33.3 / 178.1 |
| patrol | V6b | 126.7 | 249 | 0/216 | 91/216 | 40.0 / 185.0 |

\* watchdog engaged - patrol V5 is the only row in this sweep that ever needs it.

**Read plainly: V4 is the best performer in this sweep for every ship, on every column.** V5's
along-track-gated commit (which fixed the broader "stops off to the side" lateral-miss problem
documented above, at moderate range) made close-range overshoot events *worse across the board*
- not just patrol's pursuit-curve stall (16/216 bad, something neither V3 nor V4 had at all):
shuttle's overshoot-event rate jumps over 13x (4/216 -> 53/216), freighter's mean frames get 24%
slower (504.3 -> 625.7). V6b's turn-radius cap patches patrol's specific bad-trial regression
back to 0/216 and recovers freighter's mean partway (625.7 -> 542.8), but touches shuttle's
overshoot regression not at all (53/216 either way) and doesn't fully recover freighter's either
(104/216 vs. V4's 91/216). None of this crosses into "bad" for shuttle/freighter in any version
(0/216 throughout) - which is exactly why it stayed invisible until this table was actually
built out per-ship instead of assumed.

No version tested so far has V4's close-range tightness *and* V5's lateral-miss fix *and* zero
regressions everywhere at once. If close-range patrol performance ever matters enough in real
gameplay to chase further (it doesn't reachably today - see the ship-stats table above), that
gap is the next thing to close, not a regression to silently accept.

## If you change this next

- Run the protocol above. Don't skip the pre-existing-velocity matrix even if the change
  seems purely about the at-rest case - it's caught the two most severe bugs in this file's
  history and neither looked related to velocity-on-engage until traced.
- Update the version history table with a new row, commit hash, and one-line summary.
- Add a row to (or a new table beside) the V2-vs-V3 comparison table if the change touches
  `SeekMode` - keep the ship-by-ship, metric-by-metric format so regressions and trade-offs
  stay visible instead of getting summarized away.
- If an idea fails, add it to "Rejected approaches" with *why*, even if it embarrasses the
  attempt - that's the whole point of the section.
