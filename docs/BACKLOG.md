# Backlog

Known bugs and planned features that aren't fixed/implemented yet. This is a running
list, not a spec — add to it whenever you notice something, and check an item off (or
delete it) once it's actually fixed/shipped. If you're an agent fixing one of these,
mention it in the commit message so this file and the commit history stay in sync.

Top-level split is **Bugs vs. Features**. Within each, items are grouped by the type of
gameplay they belong to, so related work is easy to find together. A gameplay category
only appears under a section if it currently has items there.

# Bugs

## Missions, Dialogue & NPCs

- [ ] Target isn't officially cleared when an NPC exits the interior, so a new
      target isn't chosen when walking close again.

## Ships & Customization

- [ ] Gap: what happens when you buy a second ship? (multiple owned ships behavior
      is undefined — see the feature item under Ships & Customization.)

## Economy & Trading

- [ ] You can spend your loan on a laser cannon and then be stuck (no way to
      recover/pay it back).

## Stations, Interiors & World Building

- [ ] Characters added to a story don't show up in old saves.

# Features

## Controls & UI

- [ ] Quick save.
- [ ] Minimap: click a target to select it.
- [ ] Make the player icon on the minimap more obvious than the others.
- [ ] Hover text on the minimap when the mouse is over a point, showing what it is.
- [ ] Make credits amount display consistent with other UI texts.
- [ ] Some selling-menu controls (like the ship menu) don't mention that you can use
      the mouse.
- [ ] Consider mouse-based movement/control support.
- [x] Rotate camera. (Q/E in the Space View - view-only rotation, resets on landing.)

## Navigation & Flight

- [ ] Indicate when reaching the edge of the star map.
- [ ] Star map zoom.
- [ ] System minimap (local-system view during flight, distinct from the interstellar
      star map).

## Missions, Dialogue & NPCs

- [ ] NPCs in interior locations (station interiors, etc.) should be able to display
      messages on screen too, not just NPCs hailing from space.
- [ ] Mission Log: split into two tabs, Active and Completed, so finished
      missions have their own place instead of being mixed into the same list
      as in-progress ones (`report_menu.mission_report()` already gets both from
      `mission_status_lines()`).
- [ ] Tutorial mission for taking out a loan and buying a ship.
- [ ] Relationships.
- [ ] More roles.
- [ ] No useless NPCs — each one should reveal something about the game's features or
      story.
- [ ] NPCs stop wandering if the player moves close to or targets them.
- [ ] Derelict ships / distress beacons — a drifting AI ship with no pilot response
      you can board, loot, or tow; combines the existing AI ship, interior, and
      item-pickup ideas into one encounter type.
- [ ] Escort/wingman contracts — hire or be hired to fly alongside another AI ship
      to a destination; reuses existing autopilot and multi-AI-ship work.

## Combat, Crime & Factions

- [ ] Factions — combined with crime/war, would turn the sandbox into a living
      political map; cultures/roles already exist as a foundation.
- [ ] Combat.
- [ ] Crime — see factions.
- [ ] War — see factions.
- [ ] Bounty hunting board — a station terminal listing wanted ships/NPCs with a
      reward, feeding off factions/crime once those exist.
- [ ] AI ships flying in formations.

## Ships & Customization

- [ ] Multiple owned ships.
- [ ] Ship customization (paint/decals/name) — cosmetic, cheap, but makes "your
      ship" feel more personal, especially once multiple owned ships exist.
- [ ] Make all outfits usable (not just cosmetic/inert).
- [ ] Mounted outfit graphics (visually show equipped outfits on the ship).
- [ ] Graphic for ship thrusters so they're visible when turned off.

## Economy & Trading

- [ ] Sell all button.
- [ ] Picking up and dropping items.
- [ ] Asteroid mining — pairs naturally with the existing asteroid fields and
      "different asteroid types" idea; gives the economy a real gameplay loop instead
      of just trading.
- [ ] More ways to make money.
- [ ] Make some commodities usable for various purposes (not just tradeable).
- [ ] Distinct buy and sell multipliers per good, dependent on various factors
      (supply/demand, faction, location, etc.).
- [ ] Black-market smuggling runs — contraband cargo that's profitable but triggers
      scans/hails from patrol ships if caught; a light crime mechanic that doesn't
      need the full Crime system first.

## Stations, Interiors & World Building

- [ ] Cultural station interiors; round rooms.
- [ ] Better station interior designs (e.g. dorm rooms are currently just short
      halls).
- [ ] Enterable buildings in cities.
- [ ] More interior decorations, like roads.
- [ ] Cultural and role-based clothing for people (space_suit is the only outfit so
      far - see graphics.json's "outfits" section and Person.outfit).
- [ ] More systems with unique concepts.

## Exploration & World Content

- [ ] Options for star/asteroid seeds.
- [ ] Animals.
- [ ] Hunting.
- [ ] Procedurally generated outdoor areas, with a way to find the exit — biggest
      single expansion of explorable space beyond stations.
- [ ] Planet descriptions (icy, rocky, gas giant, etc.).
- [ ] Reasons to visit hazardous worlds.
- [ ] Events and procedural generation as you travel around systems.

## Graphics & Visual Polish

- [ ] Better jumping animation.
- [ ] Better jump graphics.
- [ ] More texture for interior grounds and ships.

## Meta, Tooling & Performance

- [ ] Add metrics for game performance.
- [ ] Check whether rendering is skipped when not applicable, or whether pygame
      already handles that.
- [ ] Guidance for agents on creating a new story from scratch, and on assisting a
      user who wants help creating one.
- [ ] **Frame-rate-independent simulation via a fixed-timestep accumulator**
      (decouple update rate from render rate). Details below.

### Fixed-timestep accumulator (decouple sim from render)

**Problem.** The main loop (`main.py`) runs exactly one simulation step and one
render per iteration, capped at 60 by `clock.tick(FPS)`. All physics constants are
"per frame", not "per second": drag `velocity *= 0.98` each frame
(`game/world/ship.py`), thrust ramp `0..0.3` per frame, rotation `5°`/frame, max
velocity `4.0` units/frame, and every countdown timer decrements by 1 per frame. So
whenever the frame rate drops below 60 (weak machine, heavy scene, a single janky
frame), the *simulation itself slows down* - a ship coasts a shorter distance, the
autopilot brakes differently, toasts linger longer in wall-clock time. The game is
frame-rate dependent.

**Chosen solution: fixed-timestep accumulator** (Glenn Fiedler, "Fix Your
Timestep"). NOT variable `dt`, and NOT an uncapped update loop - see "Rejected
alternatives" below for why.

```
STEP = 1.0 / 60.0          # fixed sim step, seconds
MAX_STEPS_PER_FRAME = 5    # spiral-of-death clamp

accumulator += real_dt     # real_dt from clock.tick(FPS) / 1000.0, or clock.get_time()/1000.0
steps = 0
while accumulator >= STEP and steps < MAX_STEPS_PER_FRAME:
    world_step()           # everything that currently happens once per loop iteration
    accumulator -= STEP
    steps += 1
if steps == MAX_STEPS_PER_FRAME:
    accumulator = 0.0      # give up catching up; don't let the loop fall infinitely behind
render()                   # once per iteration, still capped at 60 by clock.tick(FPS)
```

**Keep `STEP` at exactly 1/60 and do NOT convert any physics constant.** The whole
point of this approach: the constants are already calibrated to a 1/60 s step, so if
`STEP == 1/60` the math is byte-identical to today. On any machine holding 60 FPS the
loop runs `world_step()` exactly once per render, same as now. The accumulator only
changes behavior when the machine *can't* keep up: it then runs 2-3 sim steps per
render (sim stays correct, rendering gets choppy) instead of running one slow step
(sim goes wrong). This is purely a robustness win for slow frames; it is not a
gameplay change and not a "use real dt" change.

**What "decouple" means here.** Sim and render rates stop being 1:1 - per loop
iteration, render runs once, `world_step()` runs 0..5 times depending on accumulated
wall-clock. It does NOT make them concurrent/threaded (the loop stays
single-threaded and sequential: drain accumulator, then render, same iteration), and
it does NOT make rendering smoother on its own - that needs render interpolation, a
separate optional follow-up (see below).

#### Implementation steps

1. **Consolidate the per-frame simulation into one entry point.** Right now each
   `current_screen` branch in `main.py`'s `while running:` loop hand-rolls its own
   `update()` / `update_physics()` / `update_background_locations()` / `draw()`
   sequence (see the `"game"`, `"station"`, `"moon"` branches especially, plus the
   modal branches that call `draw(..., draw_hud=False)` on a frozen world). Extract
   the *simulation* half of each branch into a single function - e.g.
   `step_world(current_screen, game_screen, station_interior, moon_interior, ...)` -
   that does exactly what that branch currently does for simulation and nothing for
   rendering. The modal branches (`pause`, `possessions`, `missions`, `shop`,
   `exit_menu`, `star_map`, `select_location`, and any `active_dialogue`) already
   freeze the world - `step_world` does nothing for those, matching today.
2. **Restructure the loop** as: `events` -> per-branch `handle_input` (unchanged,
   still once per iteration - input is tied to render/event cadence, not sim steps)
   -> accumulator `while` loop calling `step_world` -> per-branch `draw` (unchanged)
   -> `pygame.display.flip()` -> `clock.tick(FPS)`. The branch dispatch currently
   does input+sim+draw together; split it so input and draw stay per-iteration but
   sim goes through the accumulator.
3. **`handle_input` returning a screen transition** (e.g. `"land"`, `"pause"`,
   `"exit"`) must still take effect immediately that iteration - don't run sim steps
   for the old screen after a transition was requested. Simplest: compute the
   transition from `handle_input` first, apply it, then run the accumulator for the
   (possibly new) `current_screen`. Watch `SpaceScreen.update()`'s own return value
   `"land"` (autopilot auto-land, `space_screen.py:1138`) - that fires from *inside*
   the sim step, so `step_world` needs to propagate it out of the accumulator loop
   and break.
4. **`real_dt` source:** `clock.tick(FPS)` already returns milliseconds since the
   last call - use its return value (`dt_ms = clock.tick(FPS); accumulator += dt_ms /
   1000.0`). Clamp `real_dt` to something sane (e.g. `min(real_dt, 0.25)`) before
   adding, so a debugger pause or asset-load hitch doesn't dump 10 seconds into the
   accumulator.
5. **Autopilot validation is mandatory.** `game/world/autopilot.py`'s `SeekMode` /
   `OrbitMode` / `_predict_braking_distance()` now run 0, 1, or 2+ times between
   renders where they always ran exactly once. Per `docs/AUTOPILOT_TESTING.md` and
   `CLAUDE.md`, run the full documented battery (headless simulation, all three ship
   types from `ship_types.json`, both at-rest and pre-existing-velocity scenarios)
   and confirm no oscillation / overshoot / early-braking regression before calling
   this done. `tests/test_helpers.py::TestAutopilotPhysics` drives `ship.update()` in
   a headless loop - it should still pass unchanged (fixed `STEP` = deterministic),
   and is the first thing to check.
6. **Per-frame timers become per-step timers** - audit every `*_timer -= 1` /
   countdown and confirm it still lives inside `world_step()` (so it decrements per
   sim step, keeping its 1/60 s meaning) and not in render code. Known list:
   `SpaceScreen.jump_message_timer`, `hail_banner_timer`, `message_alert_timer`,
   `toast_timer` (note: `toast_timer` deliberately counts down in `update()` not
   `update_physics()` - see `space_screen.py:1156`), `landing_text`;
   `PauseMenu.success_timer`; any animation counters in `LocationScreen` / NPC
   wander. Menu/dialog animations (`pause_menu.update()` etc.) are driven from the
   render side and can stay there - they're not simulation.
7. **Save compatibility:** stored velocities are units/frame. As long as `STEP`
   stays 1/60 their meaning is unchanged and no save migration or `story_version`
   bump is needed. If a future change ever makes `STEP` configurable or moves to
   units/second, that DOES change what an existing save's stored velocity means -
   flag it per `CLAUDE.md`'s "Save Compatibility & Story Versioning" section and bump
   the story version.
8. **Tests:** add a test that the accumulator runs the expected number of steps for
   a given elapsed time (including the `MAX_STEPS_PER_FRAME` clamp and the `real_dt`
   clamp), in `tests/test_helpers.py`. Keep it pure - factor the accumulator into a
   small helper (`advance_accumulator(accumulator, dt) -> (new_accumulator, n_steps)`
   or similar) rather than testing the whole loop.

#### Optional follow-up (separate backlog item, not this one): render interpolation

The accumulator alone doesn't make motion smoother - `draw()` still paints the
latest sim state, so if sim and render are both ~60 it looks exactly like today, and
if sim runs behind you get choppy (not smooth) rendering. To render smoothly at
>60 Hz you'd store previous + current position on each drawable and interpolate by
`accumulator / STEP` at draw time. This adds real complexity (every `WorldObject`
needs prev/curr state, and anything reading position for gameplay must read curr,
not the interpolated value). Do it only if smoothness on high-refresh displays
actually matters - it's independent of the frame-rate-independence fix above.

#### Rejected alternatives (don't do these)

- **Variable `dt` ("update as fast as possible, real dt")** - requires
  time-parameterizing every constant (`v *= pow(drag_per_sec, dt)`, per-second
  thrust/rotation/max-vel, per-second timers), and makes the autopilot's kinematic
  braking prediction diverge from the actual integration under a varying step - the
  exact code with the worst regression history in the project. Also breaks
  determinism, so the headless autopilot tests would need a separate fixed-`dt`
  path. High risk, and the destination most physics games settle on is the fixed
  accumulator anyway.
- **Uncapped update loop** - burns a full CPU core computing sim substeps nobody
  renders. Variable `dt` is for running *fewer* steps on a slow machine, not
  unbounded steps on a fast one.
- **Threading sim and render** - pygame + GIL + snapshot/lock handoff complexity,
  no real payoff for a 2D game this size.
