# Space Game Documentation

Navigation hub for architecture, design patterns, and implementation details.

## Core Documentation

- **[CLAUDE.md](../CLAUDE.md)** ← Start here for quick reference
- **[CONTROLS.md](CONTROLS.md)** — All keyboard bindings and player controls
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Class hierarchy, entity design, base classes
- **[PHYSICS.md](PHYSICS.md)** — Coordinate systems, movement, collision, frame timing & smooth-motion tradeoffs
- **[AUTOPILOT_TESTING.md](AUTOPILOT_TESTING.md)** ⚠️ — Required testing protocol before changing `SeekMode`/`OrbitMode`
- **[SAVE_SYSTEM.md](SAVE_SYSTEM.md)** — Persistence, state management, file format
- **[UI_FLOW.md](UI_FLOW.md)** — Menu state machine, screen transitions
- **[SOUND.md](SOUND.md)** — Runtime-synthesized audio (the sound board) and where sounds are triggered
- **[DESIGN_PATTERNS.md](DESIGN_PATTERNS.md)** — Reusable solutions and architectural decisions
- **[BACKLOG.md](BACKLOG.md)** — Running list of known bugs and planned features
- **[BUILD.md](BUILD.md)** — Packaging a standalone Windows build with PyInstaller

## Quick Links by Topic

### Adding New Features
1. Check [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) for applicable patterns
2. Refer to [ARCHITECTURE.md](ARCHITECTURE.md) for how to extend classes
3. Update relevant doc if implementing a new pattern
4. Suggest pattern additions if your solution could generalize

### Fixing Bugs
- Physics issues → [PHYSICS.md](PHYSICS.md)
- Autopilot/`SeekMode`/`OrbitMode` changes → [AUTOPILOT_TESTING.md](AUTOPILOT_TESTING.md) first, always
- State/save problems → [SAVE_SYSTEM.md](SAVE_SYSTEM.md)
- UI/menu bugs → [UI_FLOW.md](UI_FLOW.md)
- Coordinate system issues → [PHYSICS.md](PHYSICS.md#coordinate-system)
- Stutter / judder / motion smoothness → [PHYSICS.md](PHYSICS.md#frame-timing--smooth-motion--two-deliberate-tradeoffs), [UI_FLOW.md](UI_FLOW.md) (frame loop & vsync)

### Understanding the Codebase
Start with [ARCHITECTURE.md](ARCHITECTURE.md), then deep-dive into specific docs as needed.

## For Agents: Pattern Recognition & Contribution

When implementing a feature or fix:
1. **Recognize patterns**: If your solution could be reused, note it
2. **Check existing patterns**: See if DESIGN_PATTERNS.md has a solution you're recreating
3. **Suggest generalizations**: If you're copy-pasting logic or finding similar patterns, suggest adding to DESIGN_PATTERNS.md
4. **Propose updates**: Create a suggestion to add a pattern if it would improve future work

**Example suggestion flow:**
```
"I notice save/load logic uses a {getter, setter} pattern for state.
This could generalize to DESIGN_PATTERNS.md as 'State Persistence Pattern'
with clear steps for any future saveable component."
```

See [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md#contributing-patterns) for contribution guidelines.
