# Space Game

A pygame-based space exploration game — procedurally generated star fields, AI
ships, station/moon interiors with NPCs, physics-based flight, and a full
save/load system.

## Documentation protocol

**All project knowledge lives in `docs/`, organised as a tree you navigate on
demand. Don't read it all up front — start at the index and follow the one
branch that matches the work in front of you.**

```
CLAUDE.md  (you are here — the protocol)
└── docs/README.md   (the index — routes you to the right document by task)
    ├── ARCHITECTURE.md   — structure, class hierarchy, file conventions, config formats
    ├── CONTROLS.md       — every keyboard binding + the trail to follow when you add one
    ├── PHYSICS.md        — coordinates, movement, collision, frame-timing tradeoffs
    ├── AUTOPILOT_TESTING.md ⚠️ — mandatory validation before any autopilot change
    ├── SAVE_SYSTEM.md    ⚠️ — save format, story/save split, story versioning
    ├── UI_FLOW.md        — screen state machine, modals, the fixed-timestep loop, perf panel
    ├── DESIGN_PATTERNS.md — reusable patterns + working principles
    ├── DESIGN_ATLAS.md   — the asset-mockup HTML pages and the SVG→parts pipeline
    ├── SOUND.md          — runtime-synthesized SFX and music
    ├── WORKFLOW.md       — edit → restart → test → commit loop, testing, commit format
    ├── BUILD.md          — PyInstaller Windows packaging
    └── BACKLOG.md        — running bug / feature list
```

**Before starting any task, open [docs/README.md](docs/README.md) and follow it
to the relevant document.** Each document owns one area in depth and is the
source of truth for it; follow the links between documents as the work crosses
areas.

**Two rules that bind:**

1. **Keep the docs honest.** When you change how something works, update the
   document that owns it in the *same* commit.
2. **Some areas have a regression history** (autopilot, save compatibility,
   the frame budget). Their docs tell you to validate a change a specific way,
   and to warn the user up front, before calling it done. That guidance is not
   optional.

## Running the game

```bash
python main.py
```

Run from the repo root. Always kill and restart a running instance after a code
change — see [docs/WORKFLOW.md](docs/WORKFLOW.md).
