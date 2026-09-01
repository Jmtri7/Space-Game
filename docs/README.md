# Space Game — Documentation

This is the **index**. Its only job is to route you to the right document.
Find your task, open the document it points to, and follow the links inside
that document as the work crosses areas. You should not need to read every doc.

## Route by task

| If you're going to… | Start here | Also relevant |
|---|---|---|
| Understand the codebase — class layout, file conventions, config formats | [ARCHITECTURE.md](ARCHITECTURE.md) | [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) |
| Add or change a keyboard control | [CONTROLS.md](CONTROLS.md) | [UI_FLOW.md](UI_FLOW.md) |
| Change `SeekMode` / `OrbitMode` / autopilot or its helpers | [AUTOPILOT_TESTING.md](AUTOPILOT_TESTING.md) ⚠️ | [PHYSICS.md](PHYSICS.md) |
| Touch ship movement, drag, rotation, coordinates, collision | [PHYSICS.md](PHYSICS.md) | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Change anything a save file depends on | [SAVE_SYSTEM.md](SAVE_SYSTEM.md) ⚠️ | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Add or modify a menu, dialog, or screen transition | [UI_FLOW.md](UI_FLOW.md) | [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) |
| Work on frame timing / performance / the perf panel | [UI_FLOW.md](UI_FLOW.md#frame-timing-metrics) | [PHYSICS.md](PHYSICS.md#frame-timing--smooth-motion--two-deliberate-tradeoffs) |
| Add or edit sound / music | [SOUND.md](SOUND.md) | |
| Create or edit a design atlas (asset mockups) | [DESIGN_ATLAS.md](DESIGN_ATLAS.md) | |
| Add an entity, screen, role/routine, or ship type | [ARCHITECTURE.md](ARCHITECTURE.md#extensibility-points) | [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) |
| Generalise a repeated solution into a reusable pattern | [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) | |
| Run tests, restart the game, write a commit message | [WORKFLOW.md](WORKFLOW.md) | |
| Package a standalone Windows build | [BUILD.md](BUILD.md) | |
| Check known bugs / planned features | [BACKLOG.md](BACKLOG.md) | |

## The documents

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — project file layout and the One
  Class Per File rule, class hierarchy, entity/composition patterns,
  `story.json` / system / interior / config formats, `utils.py` helpers,
  extensibility points. **Source of truth for structure.**
- **[CONTROLS.md](CONTROLS.md)** — every keyboard binding, per screen, and the
  documentation trail to follow when you add or change one.
- **[PHYSICS.md](PHYSICS.md)** — game-space vs. screen-space, movement / drag /
  rotation math, the chunk-streamed unbounded world, the two frame-timing /
  smooth-motion tradeoffs, common physics bugs.
- **[AUTOPILOT_TESTING.md](AUTOPILOT_TESTING.md)** ⚠️ — the mandatory
  validation battery before any change to `SeekMode` / `OrbitMode` / their
  helpers. Real, repeated regression history — read it before touching
  `game/world/autopilot.py`.
- **[SAVE_SYSTEM.md](SAVE_SYSTEM.md)** ⚠️ — save file format, state
  capture/restore, the story/save split, story versioning, and exactly when a
  change must warn the user before it's made.
- **[UI_FLOW.md](UI_FLOW.md)** — the screen state machine, every modal, the
  fixed-timestep three-phase main loop, and the always-on frame-timing metrics
  (plus the agent guidance for staying under the 16.67 ms budget).
- **[DESIGN_PATTERNS.md](DESIGN_PATTERNS.md)** — reusable patterns discovered
  during development; the working principles (cross-cutting concerns,
  generalisation strategy); how to contribute a new pattern.
- **[DESIGN_ATLAS.md](DESIGN_ATLAS.md)** — the committed HTML asset-mockup
  pages: when to make one, how to keep it honest, the SVG→`parts`
  extraction tooling, and the hard technical rules for the pages.
- **[SOUND.md](SOUND.md)** — the runtime sound board and procedurally generated
  background music (no asset files).
- **[WORKFLOW.md](WORKFLOW.md)** — the edit → restart → test → commit loop,
  automated and manual testing, when to add a test, commit message convention.
- **[BUILD.md](BUILD.md)** — packaging a standalone Windows build with
  PyInstaller.
- **[BACKLOG.md](BACKLOG.md)** — running list of known bugs and planned
  features; add to it whenever you notice something.
