# Building a Standalone Windows Build

`packaging\build_windows.bat` packages the game with [PyInstaller](https://pyinstaller.org/)
into a folder that runs on a Windows machine with no Python or pygame installed - just
double-click `SpaceGame.exe` inside it. Run it from the repo root, or from anywhere -
it always operates against the repo root (its own parent directory) regardless of where
it's invoked from.

```bash
packaging\build_windows.bat
```

Output: `build\dist\SpaceGame\` at the repo root (everything the script produces lives
under `build\` for hygiene, separate from the `packaging\` source files that build it).
Ship the whole `SpaceGame\` folder - `SpaceGame.exe` needs `config\`
sitting next to it, since the game loads story config from relative paths like
`config/stories/{story}/...` at runtime rather than anything bundled into the exe).
A `saves\` folder is created next to the exe the first time the player saves;
a `music_cache\` folder likewise, holding the procedurally-rendered background
tracks so they're only synthesized once per machine (safe to delete - it just
re-renders).

## Why `--onedir`, not `--onefile`

`--onefile` produces a single `.exe`, which sounds like the better fit for "double
Click to run" - but PyInstaller's onefile mode works by having that single exe extract
itself to a temp directory and launch a *second* process to actually run the app. That
handoff turned out to fail silently under `--windowed`: launched via `Start-Process`
(as opposed to running interactively from a terminal), the visible app window never
appeared and the embedded script never even started running - no error, because
`--windowed` has no console to print one to. A minimal pygame-window reproduction
confirmed it wasn't anything specific to this game's code, only the onefile+windowed
combination under that launch path.

`--onedir` doesn't have this problem: the exe *is* the real process, not a launcher for
one, so there's no handoff to fail. It ships as a folder instead of a single file, which
is the standard PyInstaller recommendation anyway - keep it that way rather than
switching back to `--onefile` unless something changes upstream.

## Updating the build

Re-run `packaging\build_windows.bat` after any code or config change - it always does a
clean rebuild (the whole `build\` directory, output and intermediate files alike, is
removed first) rather than reusing a stale one.

`pyinstaller` itself isn't a runtime dependency (see `requirements.txt`) - it's a build
tool, pinned separately in `packaging\requirements-dev.txt`. The batch script installs
it automatically if missing.
