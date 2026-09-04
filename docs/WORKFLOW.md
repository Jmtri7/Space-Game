# Development Workflow

The edit → restart → test → commit loop, plus testing and commit conventions.

## Running the game

```bash
cd C:\Users\Play\Documents\Projects\space-game
python main.py
```

## After each feature addition or code change

1. **Kill any running game instance** — close all pygame windows from previous
   runs. Do this **unprompted** after every code change; new code is not picked
   up by an already-running instance.
   ```bash
   taskkill /f /im python.exe 2>nul || true
   ```

2. **Run automated tests** (recommended):
   ```bash
   python run_tests.py
   ```

3. **Start the game fresh** so the new code loads:
   ```bash
   python main.py
   ```

4. **Test in-game** — verify the feature/fix works by interacting with it.
   In-game testing catches issues automated tests miss.

5. **Commit** with a clear message (see convention below). Regular commits
   create a good history and let you revert.

**Example loop:** edit `ship.py` to improve autopilot braking → kill running
game → start fresh → target station and land → verify smooth braking without
overshoot → commit "Improve: Refine autopilot braking distance calculation".

## Testing

### Manual checklist

- [ ] Game starts without errors
- [ ] Menu shows LOAD option after first save
- [ ] Player can move and rotate smoothly
- [ ] Momentum works (coasting after thrust off)
- [ ] Can land on station (L key within range)
- [ ] Can walk in station interior
- [ ] Save/load preserves position and velocity
- [ ] Scrolling works in save/load menus (5+ saves)
- [ ] Window resizing scales graphics smoothly
- [ ] AI ship appears and moves autonomously

### Automated tests

```bash
python run_tests.py
```

Discovers `tests/test_*.py`. Current coverage lives in `tests/test_helpers.py`:

- **Helper functions** — `_handle_scrolling_input()`, `_list_files_by_pattern()`,
  `_center_text_x()`.
- **Autopilot physics** (`TestAutopilotPhysics`) — drives a real `Ship` through
  `engage_seek()` + `ship.update()` toward a real `LandingSite`, one case per
  `ship_types.json` preset, asserting it lands, arrives close, stops, and
  doesn't oscillate. This is a **smoke test**, not a substitute for the
  [AUTOPILOT_TESTING.md](AUTOPILOT_TESTING.md) battery.
- **Interior layout** (`TestStationInteriorLayout`) — walks a real path across
  Alpha Station and fails if a furniture/structure placement pinches it shut.
- **Story-version mismatch warning** — see SAVE_SYSTEM.md's "Save Compatibility
  Discipline".

### When to add a test

1. **Before fixing a bug** — write a test that reproduces it, then fix it, so it
   never regresses.
2. **After extracting a helper function** — add unit tests in the same commit.
3. **For critical paths** — save/load, physics, input handling.

Keep the bar practical: test regressions you've actually seen or critical
paths. **Don't test UI rendering** or pygame drawing. Prefer testing a new pure
physics helper as a method on the class that owns it (the way
`TestAutopilotPhysics` does), rather than a standalone physics module.

**How:** add the case to `tests/test_helpers.py` in the appropriate class, run
`python run_tests.py`, commit the test with the feature/fix.

## Commit message convention

```
[Feature/Fix] Brief description

- Bullet points of changes
- One per line

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

Prefixes seen in history: `Feature:`, `Fix:`, `Improve:`, `controls:` (when a
keyboard binding changed — see [CONTROLS.md](CONTROLS.md)), `pipeline:` (asset
pipeline / design JSON — see [GRAPHICS_PIPELINE.md](GRAPHICS_PIPELINE.md)).

Only commit or push when the user asks.
