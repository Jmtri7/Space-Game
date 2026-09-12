# Story Design: Process & Pitfalls

How to build a new story — the workflow, and the mistakes worth avoiding
before you make them. Config *shapes* are documented in
[architecture/config-formats.md](architecture/config-formats.md); this is
the process doc + the pitfall list, distilled from building
[`the_whisper_line`](../config/stories/the_whisper_line/docs/STORY.md).

## Process

1. **Read [ARCHITECTURE.md](ARCHITECTURE.md)** and follow it to
   [architecture/config-formats.md](architecture/config-formats.md) (every
   config shape) and [architecture/extensibility.md](architecture/extensibility.md)
   (if the story needs new Python, not just JSON — it usually doesn't).
2. **Pick a reference story to build from**, don't start blank:
   - `mining_101` or `the_whisper_line` — a minimal skeleton (one or a
     few systems, reusing the shared modules' art wholesale). Good starting
     point for a short, small-cast story.
   - `the_long_silence` — the full-featured example (factions, reputation,
     dispatches, an ending fork, per-culture art). Good reference for any
     mechanic you're about to reach for the first time.
3. **Reuse art before drawing any.** See [CONFIG_MODULES.md](CONFIG_MODULES.md)
   — list an existing module (`figures-human` for bodies/wardrobe;
   `orbital-std` for a ready ship/station/moon/building set) rather than
   authoring `graphics.json`/`cultures.json`/etc. from scratch. If you *do*
   end up duplicating another story's catalogue file, that's a sign it
   should be a new module instead (see "Extend a module" below) — earlier
   modules like `ships-core`/`common-goods` exist for exactly that reason.
4. **Write the smallest playable slice first** — one system, the opening
   beat, a save-to-load loop — and get it running before authoring the
   rest. `python main.py`, pick the story from the menu, actually play it.
5. **After every content change:** validate the JSON, run
   `python run_tests.py`, kill and restart the game
   ([WORKFLOW.md](WORKFLOW.md)) — every time, unprompted.
6. **Script the mission arc instead of only playing it.** Manually walking
   a 5+ stage mission every time you tweak one line is slow and easy to
   half-check. A quick Python snippet that starts the mission and sets each
   `complete_flag` in order (see `game.world.mission.start_mission` /
   `check_mission_progress`) catches a stuck stage or a message that never
   fires in seconds. Playing through is still how you check it *feels*
   right — do both, script for correctness, play for feel.
7. **Turn on DEBUG_MODE** (backtick) while testing dialogue-heavy scenes —
   an open conversation box shows `[debug] <NPC> / <node id>` and clicking
   it copies that node (text + every option + destination + actions) to the
   clipboard, useful for pasting a node's exact state into a bug report or
   back into the JSON. See [CONTROLS.md](CONTROLS.md).

## Pitfalls

**An NPC can spawn in a non-walkable spot.** A "ring" interior (the
octagonal concourse shape the `orbital-std` module provides) is a thin
walkable band around a hollow, unreachable center — a coordinate that looks
reasonable on paper can land inside that hole. Check any NPC position you didn't copy from a proven layout against
`LocationScreen.can_move_to(x, y)` before you're done.

**An NPC wanders by default.** Role `"resident"` (the usual fallback) gets
`WanderRoutine`. Set `"routine": "stationary"` for an NPC meant to hold one
spot, and `"facing"` (`"west"`/`"east"`/`"left"`/`"right"`) for which way
they should face while standing still. For an NPC that should leave the
scene for good after a story beat, `"depart_flag"` (paired with
`requires_not_flag` on the same flag) walks them to the nearest portal and
removes them — see [architecture/class-hierarchy.md](architecture/class-hierarchy.md)'s
routine table.

**A system doesn't need both a station and a moon.** Either is optional —
the engine only builds a placeholder for a missing one so physics/
targeting/drawing never need a None check, and landing on that placeholder
is a graceful no-op (a toast). Don't add filler content just to avoid a
crash; add a second body only when it's something you actually want there.

**`star_map_position` is pixel-scale, not small integers.** Values like
`(0,0)/(1,-1)/(2,-2)` render on top of each other and can't be clicked
apart. Space systems on the order of 150–300 units apart (see any of
`the_long_silence`'s `systems/*.json`).

**Dialogue text has no line-break support.** `Dialogue`'s word-wrap only
splits on spaces — an embedded `\n` renders literally, not as a break.
Write dialogue text as flowing prose; the conversation box auto-grows to
fit however many wrapped lines it needs, so long text is fine, multi-
paragraph formatting isn't.

**A mission started from an NPC's own dialogue (`"start_mission:<id>"`) now
delivers its first stage's message** (fixed 2026-09-11 —
`LocationScreen._deliver_stage_message`, mirroring `SpaceScreen`'s). Before
relying on that, double-check the *first* message in a chain that begins
from dialogue rather than `story.json`'s `starting_mission` actually shows
up — it's the one message with the least direct test coverage since it's
triggered from inside a conversation, not a gameplay event.

**Don't stack multiple one-way messages on the same beat.** One player
action should trigger at most one Message Log entry — see
[UI_FLOW.md](UI_FLOW.md)'s "Guideline for content authors" and
[architecture/config-formats.md](architecture/config-formats.md)'s dispatch
section. The shared queue (`_post_message`/`_pump_message_queue`,
`MESSAGE_SPACING_FRAMES` ≈ 7.5s) exists to space out genuinely independent
events landing on the same frame (a beacon relighting as a dispatch
arrives), not as a design tool for pacing a burst you wrote on purpose —
gate each dispatch/stage message on the specific progress point it belongs
to instead of hanging several on one early flag. This is easy to violate
without noticing since each message reads fine in isolation in the JSON;
it's only obvious as a pile-up in an actual playthrough. `the_long_silence`
shipped with several of these ("~4 at once" after returning to Factor Tol,
another after the vote — see [BACKLOG.md](BACKLOG.md)'s Structure & pacing
section) — script the mission arc (see step 6 above) and *also* play through
the trigger points, watching for more than one banner/ping in quick
succession.

**A generic gameplay-event flag isn't per-site.** `landed_on_landing_site`
(and similarly generic flags — see the table in
[architecture/class-hierarchy.md](architecture/class-hierarchy.md)) fires
for *any* station/moon in the active system, not a specific one. If a
system has more than one landable body, never use a generic flag as a
mission `complete_flag` for "land at the *right* one" — gate on something
that can only happen there instead (an NPC dialogue flag is usually
simplest), or fold the landing instruction into the stage that flag
protects rather than giving it its own stage.

## Extend a module

Found yourself copying another story's `graphics.json`/`cultures.json`/
`ship_types.json`/`building_types.json` (or any other flat catalogue —
see the table in [CONFIG_MODULES.md](CONFIG_MODULES.md)) instead of listing
it? Extract it into `config/modules/<name>/` and have both stories list it —
see that doc's "Adding a module / extending sharing" recipe. `orbital-std`
(courier ship + trade_ring station + regolith_moon + the two pipeline-test
cultures) is a worked example, extracted once a second story needed the
exact same look.
