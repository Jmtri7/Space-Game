"""`MusicPlayer` - procedurally generated ambient background tracks.

Like `game.audio.sound_board`, nothing here is an asset file: each track is a
short chord-cycle recipe that `render_ambient_loop()` turns into a seamless
stereo loop with pure-Python additive synthesis (detuned sine "pad" voices,
a raised-cosine crossfade between chords, a slow tremolo LFO, a sub-octave
bass). The loop is seamless because every frequency is snapped so it completes
a whole number of cycles per loop and the chord windows wrap circularly - so
it can just be played with `loops=-1`, no fade seam.

Two tracks are defined: `menu` (slow, contemplative) and `ingame` (sparser and
quieter, meant to sit under gameplay). Rendering ~20 s of audio in Python takes
a couple of seconds; that work is done **incrementally on the main thread** -
`music.pump()` (called once per frame) advances the in-progress render by a
few ms at a time, so it never blocks a frame and never fights the GIL from a
worker thread. `main.py` also calls `music.prerender_all()` at startup so both
tracks build during menu idle time rather than the first time each is needed.

A finished track is **cached to disk** (`MUSIC_CACHE_DIR`, keyed by the recipe)
the first time it's built, so on every later launch `pump()` just loads a ~2 MB
file in a frame or two instead of synthesizing. Delete the cache dir to force a
re-render (also happens automatically when a recipe changes - the key won't
match).

One shared instance, `music`. `main.py` calls `music.set_scene(current_screen)`
and `music.pump()` once per frame; the player crossfades between the two tracks
as the game moves between menus and play. Silent no-op if the mixer can't start.
"""
import hashlib
import json
import math
import os
import time
from array import array

import pygame

from game.audio.sound_board import _wave_sample
from game.constants import MUSIC_CACHE_DIR

MUSIC_CHANNEL = 15      # dedicated mixer channel for the background loop, up
                        # high so Sound.play()'s auto-allocation (which fills
                        # from 0) never lands on it under normal SFX volume
DEFAULT_SAMPLE_RATE = 22050   # music doesn't need 44.1 kHz; halving it halves
                              # the render time


def _snap_frequency(freq, loop_seconds):
    """Nudge `freq` to the nearest value that completes a whole number of
    cycles in `loop_seconds`, so the loop point has no phase discontinuity.
    At loop_seconds=20 the grid is 0.05 Hz - inaudible."""
    cycles = max(1, round(freq * loop_seconds))
    return cycles / loop_seconds


def _semitone_ratio(semitones):
    return 2.0 ** (semitones / 12.0)


def _ambient_loop_frames(spec, sample_rate=DEFAULT_SAMPLE_RATE):
    """Generator behind `render_ambient_loop`: renders `spec` to a seamless
    interleaved-stereo `array('h')`, `yield`-ing ~every 512 samples so a
    caller can spread this multi-second pure-Python work across many game
    frames (see `MusicPlayer.pump`) instead of blocking or fighting the GIL
    from a thread. The finished array is the generator's return value
    (`StopIteration.value`); `render_ambient_loop` just drains it.

    spec keys:
      loop       - loop length in seconds
      root       - root frequency in Hz (e.g. 110.0 = A2)
      chords     - list of chords, each a list of semitone offsets from root;
                   the cycle is split into equal slices, one per chord, each
                   with a raised-cosine window overlapping its neighbours 50%
      wave       - voice waveform (default "sine")
      detune_cents - a second osc per voice, detuned this much, for slow
                   beating/width (default 7.0)
      bass       - add a sine one octave below each chord's root (default True)
      lfo_rate   - tremolo rate in Hz (default 0.06)
      lfo_depth  - tremolo depth 0..1 (default 0.22)
      shimmer    - add a faint high sine two octaves above root (default False)
      peak       - normalization target, 0..1 (default 0.72)
    """
    loop = float(spec["loop"])
    root = float(spec["root"])
    chords = spec["chords"]
    wave = spec.get("wave", "sine")
    detune = 2.0 ** (float(spec.get("detune_cents", 7.0)) / 1200.0)
    add_bass = spec.get("bass", True)
    lfo_rate = _snap_frequency(spec.get("lfo_rate", 0.06), loop)
    lfo_depth = float(spec.get("lfo_depth", 0.22))
    shimmer = spec.get("shimmer", False)
    peak_target = float(spec.get("peak", 0.72))

    n = max(1, int(sample_rate * loop))
    buf = [0.0] * n
    two_pi = 2.0 * math.pi
    seg = loop / len(chords)
    half_window = seg  # 50% overlap -> windows sum to ~constant
    win = int(half_window * sample_rate)  # window half-width, in samples
    sin, cos, pi = math.sin, math.cos, math.pi
    fast_sine = (wave == "sine")          # both real tracks; skips the
                                          # _wave_sample call + waveform
                                          # dispatch ~20M times per render

    for ci, chord in enumerate(chords):
        center_i = int((ci + 0.5) * seg * sample_rate)
        # Flatten each voice (and its detuned partner) to (angular step per
        # sample, gain), so the inner loop is just `sin(w * i) * g`.
        steps = []
        raw = [(root * _semitone_ratio(s), 1.0) for s in chord]
        if add_bass:
            raw.append((root * _semitone_ratio(chord[0]) / 2.0, 1.0))
        if shimmer:
            raw.append((root * _semitone_ratio(chord[0]) * 4.0, 0.12))
        for freq, gain in raw:
            f = _snap_frequency(freq, loop)
            steps.append((two_pi * f / sample_rate, gain))
            steps.append((two_pi * f * detune / sample_rate, 0.5 * gain))

        # Only the samples actually inside this chord's raised-cosine window
        # (wrapping past the loop point), instead of scanning all n and
        # `continue`-ing the rest.
        for off in range(-win, win + 1):
            d = abs(off) / sample_rate
            if d >= half_window:
                continue
            i = (center_i + off) % n
            env = 0.5 + 0.5 * cos(pi * d / half_window)
            acc = 0.0
            if fast_sine:
                for w, g in steps:
                    acc += g * sin(w * i)
            else:
                for w, g in steps:
                    acc += g * _wave_sample(wave, w * i)
            buf[i] += env * acc
            if off & 0x1FF == 0:
                yield

    # Slow tremolo over the whole bed (snapped rate -> loops cleanly).
    for i in range(n):
        t = i / sample_rate
        buf[i] *= 1.0 - lfo_depth * (0.5 - 0.5 * cos(two_pi * lfo_rate * t))
        if i & 0x1FF == 0:
            yield

    peak = max((abs(v) for v in buf), default=0.0)
    norm = (peak_target * 32767) / peak if peak > 1e-9 else 0.0

    # Haas-effect stereo width: right channel is the same signal a few ms
    # late (wrapped, so the loop stays seamless).
    delay = int(sample_rate * 0.011)
    samples = array("h")
    for i in range(n):
        left = int(max(-1.0, min(1.0, buf[i] * norm / 32767)) * 32767)
        right = int(max(-1.0, min(1.0, buf[i - delay] * norm / 32767)) * 32767)
        if i & 0x1FF == 0:
            yield
        samples.append(left)
        samples.append(right)
    return samples


def render_ambient_loop(spec, sample_rate=DEFAULT_SAMPLE_RATE):
    """Render `spec` to a seamless interleaved-stereo `array('h')` in one
    call - drains `_ambient_loop_frames`. Used by tests and anywhere the
    multi-second cost is acceptable up front; the game renders incrementally
    (see `MusicPlayer.pump`) instead."""
    gen = _ambient_loop_frames(spec, sample_rate)
    try:
        while True:
            next(gen)
    except StopIteration as done:
        return done.value


# Bump when the PCM format or synthesis changes in a way that should
# invalidate every on-disk cache regardless of recipe (the recipe itself is
# already part of the key).
_CACHE_VERSION = 1


def _expected_sample_count(spec):
    """Length a correctly-rendered `array('h')` for `spec` must have:
    interleaved stereo, so 2 * (sample_rate * loop)."""
    return 2 * max(1, int(DEFAULT_SAMPLE_RATE * float(spec["loop"])))


def _cache_path(track, spec):
    """Where `track`'s rendered PCM lives on disk - filename carries a hash
    of the recipe (+ format version + sample rate), so an edited recipe
    simply misses and re-renders instead of loading a stale loop."""
    blob = json.dumps([_CACHE_VERSION, DEFAULT_SAMPLE_RATE, spec], sort_keys=True)
    key = hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]
    return os.path.join(MUSIC_CACHE_DIR, f"{track}_{key}.raw")


def _cache_loader(path, expected_len):
    """Generator shaped like `_ambient_loop_frames` (yields periodically,
    then returns an `array('h')`) that loads a cached render instead of
    synthesizing it - so `MusicPlayer.pump` drives both the same way and even
    the ~2 MB read is spread across frames. Returns None (-> the caller
    re-renders) on any read error or a wrong-length / truncated file."""
    chunks = []
    try:
        with open(path, "rb") as f:
            while True:
                block = f.read(262144)
                if not block:
                    break
                chunks.append(block)
                yield
    except OSError:
        return None
    samples = array("h")
    try:
        samples.frombytes(b"".join(chunks))
    except ValueError:
        return None
    return samples if len(samples) == expected_len else None


def _write_cache(track, spec, samples):
    """Persist a freshly-rendered track. Best-effort: a failure here just
    means it gets re-rendered next launch. Atomic (tmp + replace) so a
    crash mid-write can't leave a half file that later loads as garbage.
    No-op if the file is already there."""
    try:
        path = _cache_path(track, spec)
        if os.path.exists(path):
            return
        os.makedirs(MUSIC_CACHE_DIR, exist_ok=True)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "wb") as f:
            f.write(samples.tobytes())
        os.replace(tmp, path)
    except OSError:
        pass


MENU_TRACK = {
    "loop": 24.0,
    "root": 110.0,          # A2
    # Am9  -> Fmaj7(9) -> Cmaj7  -> Gadd9/E  : slow, unresolved, wistful
    "chords": [
        [0, 7, 12, 15, 19, 26],
        [-4, 3, 8, 12, 17, 22],
        [3, 10, 15, 19, 22, 27],
        [-2, 5, 10, 14, 19, 24],
    ],
    "wave": "sine",
    "detune_cents": 8.0,
    "lfo_rate": 0.055,
    "lfo_depth": 0.28,
    "shimmer": True,
    "peak": 0.74,
}

INGAME_TRACK = {
    "loop": 28.0,
    "root": 98.0,           # G2 - a touch lower, calmer
    # Two chords only, very slow drift: Gsus2  <->  Em(add9). Sparse.
    "chords": [
        [0, 7, 14, 19],
        [-3, 4, 9, 16],
    ],
    "wave": "sine",
    "detune_cents": 5.0,
    "lfo_rate": 0.035,
    "lfo_depth": 0.18,
    "shimmer": False,
    "peak": 0.5,            # sits well under the SFX and gameplay
}

MENU_SCENES = {"menu", "story_select", "pilot_name", "load"}


class MusicPlayer:
    """Owns the reserved music channel and the two rendered loops.

    A track's ~2-3 s of pure-Python synthesis is done **incrementally on the
    main thread** - `pump()`, called once per frame, advances the in-progress
    render by a small time budget (a few ms), so it never blocks a frame and
    never fights the GIL from a background thread (both of which showed up as
    a "freeze then skip forward" stutter). The track just stays silent for
    the ~10-15 s it takes to build, then fades in - which is the intended
    behaviour anyway."""

    RENDER_BUDGET_MS = 4.0   # synthesis work permitted per pump() / per frame

    def __init__(self, menu_volume=0.5, ingame_volume=0.38):
        self.enabled = False
        self.muted = False
        self._volumes = {"menu": menu_volume, "ingame": ingame_volume}
        self._recipes = {"menu": MENU_TRACK, "ingame": INGAME_TRACK}
        self._rendered = {}
        self._renders = {}        # track -> in-progress _ambient_loop_frames generator
        self._channel = None
        self._current = None      # track name the player wants playing now
        try:
            if pygame.mixer.get_init():
                # Widen the channel pool so the music channel sits well clear
                # of Sound.play()'s auto-allocated SFX channels.
                try:
                    if int(pygame.mixer.get_num_channels()) <= MUSIC_CHANNEL:
                        pygame.mixer.set_num_channels(MUSIC_CHANNEL + 1)
                except Exception:
                    pass
                self.enabled = True
        except Exception:
            self.enabled = False

    # --- scene driving ------------------------------------------------
    def set_scene(self, screen_name):
        """Map a `main.py` screen name to a track and switch if it changed."""
        if not self.enabled:
            return
        track = "menu" if screen_name in MENU_SCENES else "ingame"
        if track != self._current:
            self._current = track
            self._play(track)

    def toggle_mute(self):
        self.muted = not self.muted
        if not self.enabled or self._channel is None:
            return
        if self.muted:
            self._channel.set_volume(0.0)
        elif self._current:
            self._channel.set_volume(self._volumes.get(self._current, 0.4))

    def prerender_all(self):
        """Queue an (incremental) build of every track now, so both are
        rendered - or, after the first launch on a machine, loaded from the
        disk cache - during menu idle time instead of the first time each is
        actually needed. Call once at startup. No-op if music is disabled."""
        if not self.enabled:
            return
        for track in self._recipes:
            self._ensure_render(track)

    def pump(self):
        """Advance the in-progress track renders by up to RENDER_BUDGET_MS of
        work total. Call once per frame from the main loop (cheap no-op when
        there's nothing rendering). The track the player currently wants is
        advanced first; a finished render is cached to disk, wrapped in a
        Sound, and started if it's still the wanted track."""
        if not self.enabled or not self._renders:
            return
        deadline = time.perf_counter() + self.RENDER_BUDGET_MS / 1000.0
        # Current track first, so what's actually about to be heard finishes
        # before a track that's only being pre-warmed for later.
        for track in sorted(self._renders, key=lambda t: t != self._current):
            gen = self._renders.get(track)
            if gen is None:
                continue
            try:
                while time.perf_counter() < deadline:
                    next(gen)
            except StopIteration as done:
                self._renders.pop(track, None)
                self._on_render_done(track, done.value)
            except Exception:
                self._renders.pop(track, None)

    def _on_render_done(self, track, samples):
        """A track's generator finished. `samples` is the rendered PCM, or
        None when a cache load found the file missing/corrupt - in which case
        fall back to a real synthesis."""
        if samples is None:
            self._renders[track] = _ambient_loop_frames(self._recipes[track])
            return
        _write_cache(track, self._recipes[track], samples)
        try:
            sound = pygame.mixer.Sound(buffer=samples.tobytes())
        except Exception:
            return
        self._rendered[track] = sound
        if self._current == track:
            self._start(sound, track)

    # --- playback ---------------------------------------------------
    def _ensure_render(self, track):
        """Make sure `track` is rendered, being rendered, or queued: load it
        from the disk cache if present (via a one-step loader generator so
        the read still respects pump()'s time budget), else queue a real
        incremental synthesis."""
        if track in self._rendered or track in self._renders:
            return
        spec = self._recipes[track]
        path = _cache_path(track, spec)
        if os.path.exists(path):
            self._renders[track] = _cache_loader(path, _expected_sample_count(spec))
        else:
            self._renders[track] = _ambient_loop_frames(spec)

    def _play(self, track):
        sound = self._rendered.get(track)
        if sound is not None:
            self._start(sound, track)
        else:
            self._ensure_render(track)

    def _start(self, sound, track):
        try:
            if self._channel is None:
                self._channel = pygame.mixer.Channel(MUSIC_CHANNEL)
            vol = 0.0 if self.muted else self._volumes.get(track, 0.4)
            sound.set_volume(vol)
            # fade_ms crossfades: Channel.play replaces whatever was on the
            # channel, fading the new loop up over 2 s.
            self._channel.play(sound, loops=-1, fade_ms=2000)
        except Exception:
            pass

    def stop(self, fade_ms=800):
        if self.enabled and self._channel is not None:
            try:
                self._channel.fadeout(fade_ms)
            except Exception:
                pass
        self._current = None


music = MusicPlayer()
