# Sound

All game audio is **computer generated at runtime** - there are no `.wav`/`.ogg`
asset files, matching the "only `config/` ships next to the exe" rule in
[BUILD.md](BUILD.md). Synthesis lives in
[`game/audio/sound_board.py`](../game/audio/sound_board.py).

## The sound board

One shared instance, `sound_board`, is created at import time (same pattern as
`game.perf_metrics.metrics`):

```python
from game.audio.sound_board import sound_board
sound_board.play("ping")          # optional: play("ping", volume=0.5)
```

`play()` is **always safe to call unconditionally** - if the mixer can't start
(no audio device, headless CI), `sound_board.enabled` is `False` and every
method is a silent no-op. No caller guards the call.

### How a sound is defined

A recipe is a list of **tone layers**; `render_waveform()` mixes them into a raw
16-bit PCM buffer with pure-Python math (no numpy - not a dependency) and
`pygame.mixer.Sound(buffer=...)` wraps it. Rendered Sounds are cached after
first play.

```python
sound_board.define("chime", [
    {"freq": 660, "dur": 0.10, "wave": "sine", "decay": 0.07, "amp": 0.8},
    {"freq": 990, "dur": 0.16, "wave": "sine", "decay": 0.11, "amp": 0.7, "delay": 0.075},
])
```

Per-layer keys: `freq` (Hz), `freq_end` (Hz, optional - the layer glides
linearly from `freq` to `freq_end` over its `dur`; omit for a constant tone -
this is what gives `laser` its descending "pew"), `dur` (s), `wave`
(`sine`/`square`/`saw`/`triangle`/`noise`), `amp`, `attack` (linear fade-in s),
`decay` (exponential decay time-constant s), `sustain` (0..1 decay floor),
`delay` (s before the layer starts). Each rendered sound is peak-normalized and
gets a ~3 ms anti-click fade at both ends.

Because every sound is normalized to the same peak, a layer's `amp` only sets
its balance *within* a recipe - it can't make a whole sound quieter than the
board. For that, pass `define(name, layers, volume=<0..1>)`: a per-recipe gain
applied under `master_volume` on every `play()` (the target-cycle `blip` uses
this to sit well below the rest).

### The default board

| Name | Character | Triggered by |
|------|-----------|--------------|
| `ping` | bright two-note blip | **every menu/dialog button press**, and **one-way messages** — three times per message, once per blink of the Message Log's unread light (see `ui_theme.message_alert_state`) |
| `blip` | single square-wave tick (mixed quiet, `volume=0.4`) | **cycling or clicking a target** — `[` / `]` / `T` in the space view, `[` / `]` / click in an interior |
| `confirm` | rising perfect-fifth chime | **engaging autopilot** (Space, space view) |
| `deny` | low detuned sawtooth buzz | (available; unused by default) |
| `alert` | two high triangle beeps | (available; unused by default) |
| `laser` | square-wave "pew" - fast downward `freq_end` sweep, layered with a quieter saw an octave down (mixed quiet, `volume=0.5`) | **firing the laser cannon** — holding **X** in the space view, see `SpaceScreen._update_weapon_fire` |

## Wiring

- **Menu buttons:** `MenuBase._button_pressed()` in
  [`game/ui/menu_base.py`](../game/ui/menu_base.py) - every button press
  (keyboard Enter and mouse click alike) funnels through it, so one hook covers
  every menu and dialog. Button *navigation* (arrows/Tab) is silent.
- **Messages:** driven off the unread-light timer, not the message post
  itself - each screen's `update()` (active screen only) plays `ping` once
  per blink, `MESSAGE_ALERT_BLINKS` times, via `ui_theme.message_alert_state()`.
  `SpaceScreen._post_message()` / `LocationScreen._refresh_messages()` just
  (re)start that timer. Covers proximity one-way hails
  (`_check_one_way_hails`), mission-stage messages (`_deliver_stage_message`),
  and interior-NPC lines (`_post_local_message`).
- **Targeting / autopilot:** `_cycle_target`, `_cycle_target_mode`,
  `_select_target_at` and the `K_SPACE` branch in
  [`game/screens/space_screen.py`](../game/screens/space_screen.py);
  `_cycle_npc_target` / `_select_person_target_at` in
  [`game/screens/location_screen.py`](../game/screens/location_screen.py).
- **Weapon fire:** `SpaceScreen._update_weapon_fire()` - called every frame
  **X** is held (rate-limited by `weapon_fire_cooldown`/`weapon_fire_rate`,
  not once per keypress, so holding the key fires repeatedly rather than once).

`master_volume` (default `0.55`) on the `SoundBoard` scales everything.
`sound_board.muted` (toggled by **Ctrl+M**, see below) silences it.

## Background music

[`game/audio/music.py`](../game/audio/music.py) - `MusicPlayer` + shared
`music` instance. Two procedurally generated ambient loops:

| Track | Feel | Plays on |
|-------|------|----------|
| `menu` | slow, contemplative — a 24 s four-chord pad cycle (Am9 → Fmaj7 → Cmaj7 → Gadd9), detuned sine voices, sub bass, faint shimmer | main menu, story select, pilot name, load |
| `ingame` | sparser and quieter — a 28 s two-chord drift (Gsus2 ↔ Em add9), slower LFO, no shimmer, lower normalization | everything else (space, interiors, star map, pause, shops…) |

The loop is **seamless**: every frequency is snapped so it completes a whole
number of cycles per loop, the chord windows wrap circularly, and the LFO
rate is snapped too - so it plays with `loops=-1` and no seam.

That render is a few seconds of pure-Python math. It is done **incrementally
on the main thread**: `_ambient_loop_frames()` is a generator that `yield`s
~every 512 samples, and `MusicPlayer.pump()` (called once per frame from
`main.py`) drives it forward by a small time budget per frame -
`RENDER_BUDGET_MS` (~4 ms) on a menu, `INGAME_RENDER_BUDGET_MS` (~1.5 ms)
during gameplay, where a busy frame plus a full budget can tip past the
vblank. So a track takes ~10-20 s of real time to build, stays silent until
then, and fades in when done - but no single frame ever pays more than a few
ms, and
there is **no worker thread** (an earlier threaded version stuttered the 60
FPS loop badly on Windows - GIL contention the throttle/priority tricks
couldn't fully hide - showing up as a "freeze then skip forward" in the menu
backdrop and right after entering a station). `render_ambient_loop()` drains
the same generator in one call for tests and any synchronous use.

Two things keep that build cost off the player's back entirely:

- **`music.prerender_all()`** (called once at startup) queues *both* tracks,
  so `pump()` builds them during menu idle time instead of the first time
  each is needed. `pump()` advances the track you currently want first.
- **Disk cache.** A finished render is written to `MUSIC_CACHE_DIR/`
  (`music_cache/`, gitignored) as raw PCM, filename keyed by a hash of the
  recipe + sample rate + a format version. On every later launch `pump()`
  loads that ~2 MB file (chunked across frames) instead of synthesizing -
  so only the very first launch on a machine pays the render cost. Edit a
  recipe and the key stops matching, so it re-renders automatically; a
  missing / truncated / wrong-length file is ignored and re-rendered.

`main.py` calls `music.set_scene(current_screen)` and `music.pump()` once per
frame; `MusicPlayer` crossfades (2 s) when the mapped track changes. The loop
uses a dedicated high mixer channel (`MUSIC_CHANNEL = 15`, with the pool
widened to 16) so SFX `Sound.play()` auto-allocation never collides with it.

## Mute

**Ctrl + M** (handled globally in `main.py`, next to the QUIT / debug-toggle
handlers) flips both `sound_board.muted` and `music.muted` - works on every
screen.
