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

Per-layer keys: `freq` (Hz), `dur` (s), `wave`
(`sine`/`square`/`saw`/`triangle`/`noise`), `amp`, `attack` (linear fade-in s),
`decay` (exponential decay time-constant s), `sustain` (0..1 decay floor),
`delay` (s before the layer starts). Each rendered sound is peak-normalized and
gets a ~3 ms anti-click fade at both ends.

### The default board

| Name | Character | Triggered by |
|------|-----------|--------------|
| `ping` | bright two-note blip | **every menu/dialog button press**, and **every one-way message received** |
| `blip` | single square-wave tick | **cycling or clicking a target** — `[` / `]` / `T` in the space view, `[` / `]` / click in an interior |
| `confirm` | rising perfect-fifth chime | **engaging autopilot** (Space, space view) |
| `deny` | low detuned sawtooth buzz | (available; unused by default) |
| `alert` | two high triangle beeps | (available; unused by default) |

## Wiring

- **Menu buttons:** `MenuBase._button_pressed()` in
  [`game/ui/menu_base.py`](../game/ui/menu_base.py) - every button press
  (keyboard Enter and mouse click alike) funnels through it, so one hook covers
  every menu and dialog. Button *navigation* (arrows/Tab) is silent.
- **Messages:** `SpaceScreen._post_message()` in
  [`game/screens/space_screen.py`](../game/screens/space_screen.py) - covers
  both proximity one-way hails (`_check_one_way_hails`) and mission-stage
  messages (`_deliver_stage_message`).
- **Targeting / autopilot:** `_cycle_target`, `_cycle_target_mode`,
  `_select_target_at` and the `K_SPACE` branch in
  [`game/screens/space_screen.py`](../game/screens/space_screen.py);
  `_cycle_npc_target` / `_select_person_target_at` in
  [`game/screens/location_screen.py`](../game/screens/location_screen.py).

`master_volume` (default `0.55`) on the `SoundBoard` scales everything.
`sound_board.muted` (toggled by **Ctrl+M**, see below) silences it.

## Background music

[`game/audio/music.py`](../game/audio/music.py) - `MusicPlayer` + shared
`music` instance. Two procedurally generated ambient loops:

| Track | Feel | Plays on |
|-------|------|----------|
| `menu` | slow, contemplative — a 24 s four-chord pad cycle (Am9 → Fmaj7 → Cmaj7 → Gadd9), detuned sine voices, sub bass, faint shimmer | main menu, story select, pilot name, load |
| `ingame` | sparser and quieter — a 28 s two-chord drift (Gsus2 ↔ Em add9), slower LFO, no shimmer, lower normalization | everything else (space, interiors, star map, pause, shops…) |

`render_ambient_loop()` builds a **seamless** loop: every frequency is snapped
so it completes a whole number of cycles per loop, the chord windows wrap
circularly, and the LFO rate is snapped too - so it plays with `loops=-1` and
no seam. It's synthesized on a **background thread** (~2-3 s each) so startup
isn't blocked; the track fades in when ready.

`main.py` calls `music.set_scene(current_screen)` once per frame;
`MusicPlayer` crossfades (2 s) when the mapped track changes. The loop uses a
dedicated high mixer channel (`MUSIC_CHANNEL = 15`, with the pool widened to
16) so SFX `Sound.play()` auto-allocation never collides with it.

## Mute

**Ctrl + M** (handled globally in `main.py`, next to the QUIT / debug-toggle
handlers) flips both `sound_board.muted` and `music.muted` - works on every
screen.
