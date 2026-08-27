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
a couple of seconds, so it happens on a background thread - the game starts
silent for a moment, then the track fades in when its buffer is ready.

One shared instance, `music`. `main.py` calls `music.set_scene(current_screen)`
once per frame; the player crossfades between the two tracks as the game moves
between menus and play. Silent no-op if the mixer can't start.
"""
import math
import os
import threading
from array import array

import pygame

from game.audio.sound_board import _wave_sample

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


def render_ambient_loop(spec, sample_rate=DEFAULT_SAMPLE_RATE):
    """Render an ambient chord-cycle recipe to an interleaved-stereo
    `array('h')` that loops seamlessly.

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

    for ci, chord in enumerate(chords):
        center = (ci + 0.5) * seg
        voices = [_snap_frequency(root * _semitone_ratio(s), loop) for s in chord]
        if add_bass:
            voices.append(_snap_frequency(root * _semitone_ratio(chord[0]) / 2.0, loop))
        if shimmer:
            voices.append((_snap_frequency(root * _semitone_ratio(chord[0]) * 4.0, loop), 0.12))
        for i in range(n):
            t = i / sample_rate
            d = abs(t - center)
            d = min(d, loop - d)          # circular distance, so chord 0's
            if d >= half_window:          # window wraps past the loop point
                continue
            env = 0.5 + 0.5 * math.cos(math.pi * d / half_window)
            acc = 0.0
            for v in voices:
                f, gain = v if isinstance(v, tuple) else (v, 1.0)
                acc += gain * _wave_sample(wave, two_pi * f * t)
                acc += 0.5 * gain * _wave_sample(wave, two_pi * f * detune * t)
            buf[i] += env * acc

    # Slow tremolo over the whole bed (snapped rate -> loops cleanly).
    for i in range(n):
        t = i / sample_rate
        buf[i] *= 1.0 - lfo_depth * (0.5 - 0.5 * math.cos(two_pi * lfo_rate * t))

    peak = max((abs(v) for v in buf), default=0.0)
    norm = (peak_target * 32767) / peak if peak > 1e-9 else 0.0

    # Haas-effect stereo width: right channel is the same signal a few ms
    # late (wrapped, so the loop stays seamless).
    delay = int(sample_rate * 0.011)
    samples = array("h")
    for i in range(n):
        left = int(max(-1.0, min(1.0, buf[i] * norm / 32767)) * 32767)
        right = int(max(-1.0, min(1.0, buf[i - delay] * norm / 32767)) * 32767)
        samples.append(left)
        samples.append(right)
    return samples


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
    """Owns the reserved music channel and the two rendered loops. Tracks are
    rendered lazily on a background thread the first time they're needed."""

    def __init__(self, menu_volume=0.5, ingame_volume=0.38):
        self.enabled = False
        self.muted = False
        self._volumes = {"menu": menu_volume, "ingame": ingame_volume}
        self._recipes = {"menu": MENU_TRACK, "ingame": INGAME_TRACK}
        self._rendered = {}
        self._pending = set()
        self._lock = threading.Lock()
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

    # --- playback ---------------------------------------------------
    def _play(self, track):
        sound = self._rendered.get(track)
        if sound is not None:
            self._start(sound, track)
            return
        # Not rendered yet - kick off a background render; _render_worker
        # starts it when done if it's still the wanted track.
        with self._lock:
            if track in self._pending:
                return
            self._pending.add(track)
        threading.Thread(target=self._render_worker, args=(track,), daemon=True).start()

    def _render_worker(self, track):
        try:
            samples = render_ambient_loop(self._recipes[track])
            sound = pygame.mixer.Sound(buffer=samples.tobytes())
        except Exception:
            with self._lock:
                self._pending.discard(track)
            return
        with self._lock:
            self._rendered[track] = sound
            self._pending.discard(track)
        if self._current == track:
            self._start(sound, track)

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
