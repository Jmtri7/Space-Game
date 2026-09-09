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
| Add or change a graphic asset (ship, station, body, outfit, decoration, interior) | [GRAPHICS_PIPELINE.md](GRAPHICS_PIPELINE.md) | [DESIGN_ATLAS.md](DESIGN_ATLAS.md) for the frozen `default`-story art |
| Work in the `config/editor.html` vertex editor | [GRAPHICS_EDITOR.md](GRAPHICS_EDITOR.md) | [GRAPHICS_PIPELINE.md](GRAPHICS_PIPELINE.md) |
| Add an entity, screen, role/routine, or ship type | [ARCHITECTURE.md](ARCHITECTURE.md#extensibility-points) | [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) |
| Generalise a repeated solution into a reusable pattern | [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) | |
| Run tests, restart the game, write a commit message | [WORKFLOW.md](WORKFLOW.md) | |
| Package a standalone Windows build | [BUILD.md](BUILD.md) | |
| Check known bugs / planned features | [BACKLOG.md](BACKLOG.md) | |

Each document owns one area in depth and is the source of truth for it. Open
only the one your task needs; follow its internal links as the work crosses
areas. ⚠️ marks docs with a regression history whose validation steps are
mandatory.
