"""`SoundBoard` - a small synthesizer for the game's UI/notification sounds.

There are no audio asset files in this project (see docs/BUILD.md - only
`config/` ships next to the exe), and adding a `.wav`/`.ogg` pipeline just for
a couple of blips isn't worth it. Instead every sound here is *computer
generated* at startup: a "recipe" is a list of tone layers (frequency,
duration, waveform, amplitude envelope), `render_waveform()` mixes them into a
raw 16-bit PCM buffer with pure-Python math (no numpy - it isn't a
dependency, see requirements.txt), and `pygame.mixer.Sound(buffer=...)` wraps
that. Rendered Sounds are cached after first play.

One shared instance, `sound_board`, is created at import time (mirroring
`game.perf_metrics.metrics`) - import it with
`from game.audio.sound_board import sound_board` and call `sound_board.play(
"ping")`. Everything degrades to a silent no-op if the mixer can't start (no
audio device, `SDL_AUDIODRIVER` unset on a headless box), so callers never
have to guard the call.

The board currently defines: `ping` (message received / menu button pressed),
`blip`, `confirm`, `deny`, `alert`, four weapon-fire sounds - `laser`
(baseline), `blaster` (pulse_blaster), `cannon` (heavy_cannon), `scatter`
(scatter_gun), one per ship_outfits.json weapon (see
SpaceScreen._update_weapon_fire) - `impact` (any of them hitting an
asteroid, see SpaceScreen._check_projectile_asteroid_collision), and
`pickup` (collecting drifting ore, see SpaceScreen._update_ore_pickups).
Add more with `define()`.
"""
import math
import os
import random
from array import array

import pygame

SAMPLE_RATE = 44100      # Hz - requested mixer rate; the real rate is read back
                         # from pygame.mixer.get_init() and rendered to match
MAX_AMPLITUDE = 32767    # signed 16-bit full scale
NORMALIZE_PEAK = 0.85    # render each sound so its loudest sample sits here,
                         # for consistent perceived loudness across recipes
ANTI_CLICK_SECONDS = 0.003  # linear fade at the very start/end of every buffer,
                            # so a non-zero first/last sample doesn't pop


def _wave_sample(wave, phase):
    """One sample of a unit-amplitude `wave` at `phase` radians."""
    if wave == "square":
        return 1.0 if math.sin(phase) >= 0.0 else -1.0
    if wave == "saw":
        frac = (phase / (2.0 * math.pi)) % 1.0
        return 2.0 * frac - 1.0
    if wave == "triangle":
        frac = (phase / (2.0 * math.pi)) % 1.0
        return 4.0 * abs(frac - 0.5) - 1.0
    if wave == "noise":
        return random.uniform(-1.0, 1.0)
    return math.sin(phase)  # "sine" and anything unrecognized


def _layer_envelope(t, attack, decay, sustain):
    """Amplitude multiplier at time `t` (seconds into the layer): a short
    linear `attack` ramp up to 1.0, then an exponential fall toward
    `sustain` with time-constant `decay`. This gives the plucked/"ping"
    character - fast in, smooth exponential tail out."""
    if t < attack:
        return t / attack
    return sustain + (1.0 - sustain) * math.exp(-(t - attack) / decay)


def render_waveform(layers, sample_rate=SAMPLE_RATE, channels=2):
    """Mix `layers` into an `array('h')` of interleaved signed-16-bit PCM.

    Each layer is a dict:
      freq     - tone frequency in Hz (required)
      freq_end - if set, freq glides linearly to this by the end of the
                 layer's dur (default: freq, i.e. no sweep) - the classic
                 sci-fi laser "pew" is a fast downward sweep, e.g.
                 freq=1800/freq_end=300
      dur     - layer length in seconds (required)
      wave    - "sine" (default) | "square" | "saw" | "triangle" | "noise"
      amp     - pre-normalization weight for this layer (default 1.0)
      attack  - linear fade-in seconds (default 0.004)
      decay   - exponential decay time-constant seconds (default 0.09)
      sustain - floor the decay approaches, 0..1 (default 0.0)
      delay   - seconds to wait before this layer starts (default 0.0),
                for two-note "ping"s and repeated "alert" beeps

    Pure Python and pygame-free so it's unit-testable on its own.
    """
    total = max((float(l.get("delay", 0.0)) + float(l["dur"]) for l in layers), default=0.0)
    n = max(1, int(sample_rate * total))
    buf = [0.0] * n

    for layer in layers:
        freq_start = float(layer["freq"])
        freq_end = float(layer.get("freq_end", freq_start))
        wave = layer.get("wave", "sine")
        amp = float(layer.get("amp", 1.0))
        attack = max(float(layer.get("attack", 0.004)), 1e-5)
        decay = max(float(layer.get("decay", 0.09)), 1e-5)
        sustain = max(0.0, min(1.0, float(layer.get("sustain", 0.0))))
        start = int(sample_rate * float(layer.get("delay", 0.0)))
        length = max(1, int(sample_rate * float(layer["dur"])))
        # Phase is accumulated sample-by-sample (rather than a single
        # step * i formula) so freq can glide linearly from freq_start to
        # freq_end over the layer - a constant freq (freq_end == freq_start,
        # the common case) accumulates the same constant step every sample,
        # so this is equivalent to the old formula whenever there's no sweep.
        phase = 0.0

        for i in range(length):
            idx = start + i
            if idx >= n:
                break
            frac = i / length
            instantaneous_freq = freq_start + (freq_end - freq_start) * frac
            phase += 2.0 * math.pi * instantaneous_freq / sample_rate
            env = _layer_envelope(i / sample_rate, attack, decay, sustain)
            buf[idx] += amp * env * _wave_sample(wave, phase)

    peak = max((abs(v) for v in buf), default=0.0)
    norm = (NORMALIZE_PEAK / peak) if peak > 1e-9 else 0.0
    fade = min(n // 2, max(1, int(sample_rate * ANTI_CLICK_SECONDS)))

    samples = array("h")
    for i, v in enumerate(buf):
        s = v * norm
        if i < fade:
            s *= i / fade
        elif i > n - 1 - fade:
            s *= (n - 1 - i) / fade
        value = int(max(-1.0, min(1.0, s)) * MAX_AMPLITUDE)
        for _ in range(max(1, channels)):
            samples.append(value)
    return samples


class SoundBoard:
    """Owns the mixer handle, the recipe table, and the rendered-Sound cache.

    `enabled` is False whenever the mixer failed to start; every public
    method is then a no-op, so `sound_board.play(...)` is always safe to
    call unconditionally.
    """

    def __init__(self, master_volume=0.55):
        self.master_volume = master_volume
        self.muted = False
        self.enabled = False
        self._recipes = {}
        self._recipe_volumes = {}  # name -> 0..1 baseline gain, applied on top
                                   # of master_volume (see define/play). Lets a
                                   # recipe sit quieter than the rest without
                                   # fighting render_waveform's per-sound peak
                                   # normalization, which would otherwise pull
                                   # any single-layer sound back up to the same
                                   # loudness regardless of its layer "amp".
        self._rendered = {}
        self._freq = SAMPLE_RATE
        self._channels = 2
        self._init_mixer()
        self._register_default_board()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
                except pygame.error:
                    # No real device - fall back to SDL's dummy driver so
                    # Sound objects still construct (silently) rather than
                    # the whole board going dark.
                    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
                    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            got = pygame.mixer.get_init()
            if got:
                try:
                    self._freq = int(got[0]) or SAMPLE_RATE
                    self._channels = int(got[2]) or 2
                except (TypeError, ValueError):
                    self._freq, self._channels = SAMPLE_RATE, 2
                self.enabled = True
        except (pygame.error, AttributeError):
            self.enabled = False

    def define(self, name, layers, volume=1.0):
        """Register (or replace) a sound recipe - see `render_waveform` for
        the layer format. `volume` (0..1) is a per-recipe baseline gain
        applied under master_volume on every play (use it to make one
        sound quieter than the board as a whole - layer "amp" alone can't,
        the renderer normalizes each sound to the same peak). Drops any
        cached render of the same name."""
        self._recipes[name] = layers
        self._recipe_volumes[name] = max(0.0, min(1.0, volume))
        self._rendered.pop(name, None)

    def has(self, name):
        return name in self._recipes

    def play(self, name, volume=1.0):
        """Play a registered sound. Silent no-op if the board is disabled or
        `name` isn't defined. `volume` (0..1) scales it under master_volume."""
        if not self.enabled or self.muted:
            return
        sound = self._rendered.get(name)
        if sound is None:
            recipe = self._recipes.get(name)
            if not recipe:
                return
            try:
                samples = render_waveform(recipe, self._freq, self._channels)
                sound = pygame.mixer.Sound(buffer=samples.tobytes())
            except (pygame.error, ValueError, TypeError):
                return
            self._rendered[name] = sound
        try:
            gain = self.master_volume * volume * self._recipe_volumes.get(name, 1.0)
            sound.set_volume(max(0.0, min(1.0, gain)))
            sound.play()
        except pygame.error:
            pass

    def _register_default_board(self):
        # "ping" - a bright, friendly two-note confirmation blip. Fired on
        # every menu button press and whenever a one-way message arrives
        # (see game/ui/menu_base.py and SpaceScreen._post_message).
        self.define("ping", [
            {"freq": 1244.51, "dur": 0.10, "wave": "sine", "attack": 0.004, "decay": 0.055, "amp": 0.9},
            {"freq": 1864.66, "dur": 0.17, "wave": "sine", "attack": 0.004, "decay": 0.11, "amp": 0.55, "delay": 0.035},
        ])
        # "blip" - a single short square-wave tick (cursor moves, minor
        # acks). Deliberately well below the rest of the board: it fires on
        # every target-cycle keypress (T/[/] in the Space View, [/] in an
        # interior), so at full loudness it grates.
        self.define("blip", [
            {"freq": 880.0, "dur": 0.05, "wave": "square", "attack": 0.002, "decay": 0.028, "amp": 0.35},
        ], volume=0.4)
        # "confirm" - a rising perfect-fifth chime for a completed action.
        self.define("confirm", [
            {"freq": 659.26, "dur": 0.10, "wave": "sine", "decay": 0.07, "amp": 0.8},
            {"freq": 987.77, "dur": 0.16, "wave": "sine", "decay": 0.11, "amp": 0.7, "delay": 0.075},
        ])
        # "deny" - a low, slightly detuned sawtooth buzz for a rejected action.
        self.define("deny", [
            {"freq": 220.0, "dur": 0.18, "wave": "saw", "decay": 0.13, "amp": 0.5},
            {"freq": 208.0, "dur": 0.18, "wave": "saw", "decay": 0.13, "amp": 0.4, "delay": 0.015},
        ])
        # "alert" - two identical high triangle beeps, for attention-grabbing
        # events (unused by default; here so the board is a board).
        self.define("alert", [
            {"freq": 1568.0, "dur": 0.09, "wave": "triangle", "decay": 0.07, "amp": 0.7},
            {"freq": 1568.0, "dur": 0.09, "wave": "triangle", "decay": 0.07, "amp": 0.7, "delay": 0.13},
        ])
        # "laser" - the classic sci-fi "pew": a fast downward frequency
        # sweep (freq -> freq_end, see render_waveform) on a square wave for
        # bite, layered with a quieter saw an octave down for body. Short
        # (0.09s) and quiet by default (volume=0.5) since SpaceScreen fires
        # it on a cooldown while X is held (see weapon_fire_rate) - it needs
        # to read as a rapid-fire cannon, not one sound per shot fighting
        # the last one's tail.
        self.define("laser", [
            {"freq": 1800.0, "freq_end": 300.0, "dur": 0.09, "wave": "square", "attack": 0.002, "decay": 0.05, "amp": 0.6},
            {"freq": 900.0, "freq_end": 150.0, "dur": 0.09, "wave": "saw", "attack": 0.002, "decay": 0.05, "amp": 0.3},
        ], volume=0.5)
        # "impact" - a laser hitting an asteroid: a quick noise crackle (the
        # spark burst, see game/world/explosion.py) over a low thud for
        # weight. Short and quiet (volume=0.4) since it can fire once per
        # laser tick against a durable asteroid - a rapid staccato of hits,
        # not one sound overpowering the next.
        self.define("impact", [
            {"freq": 3200.0, "dur": 0.05, "wave": "noise", "attack": 0.001, "decay": 0.025, "amp": 0.5},
            {"freq": 110.0, "freq_end": 60.0, "dur": 0.07, "wave": "triangle", "attack": 0.001, "decay": 0.04, "amp": 0.45},
        ], volume=0.4)
        # "blaster" - pulse_blaster's fire sound: thinner and higher than
        # "laser", and shorter (0.05s vs 0.09s) to match its much faster
        # fire_rate - it needs to read as a rapid chatter, not a machine-gun
        # of overlapping "laser"s.
        self.define("blaster", [
            {"freq": 2600.0, "freq_end": 1100.0, "dur": 0.05, "wave": "square", "attack": 0.001, "decay": 0.03, "amp": 0.55},
        ], volume=0.4)
        # "cannon" - heavy_cannon's fire sound: a deep punchy thud (low
        # triangle sweep) plus a short noise crack for the muzzle blast -
        # the polar opposite of "blaster", matching its slow fire_rate and
        # heavy single-hit damage.
        self.define("cannon", [
            {"freq": 180.0, "freq_end": 45.0, "dur": 0.16, "wave": "triangle", "attack": 0.002, "decay": 0.09, "amp": 0.8},
            {"freq": 2200.0, "dur": 0.04, "wave": "noise", "attack": 0.001, "decay": 0.02, "amp": 0.35},
        ], volume=0.6)
        # "scatter" - scatter_gun's fire sound: three quick overlapping
        # noise cracks (tiny delays) reading as one wide blast, echoing its
        # multi-pellet spread rather than one clean tone.
        self.define("scatter", [
            {"freq": 2000.0, "dur": 0.06, "wave": "noise", "attack": 0.001, "decay": 0.035, "amp": 0.5},
            {"freq": 1500.0, "dur": 0.06, "wave": "noise", "attack": 0.001, "decay": 0.035, "amp": 0.4, "delay": 0.012},
            {"freq": 250.0, "freq_end": 90.0, "dur": 0.08, "wave": "triangle", "attack": 0.001, "decay": 0.05, "amp": 0.45},
        ], volume=0.5)
        # "pickup" - collecting a drifting ore chunk (see
        # game/world/ore_pickup.py / SpaceScreen._update_ore_pickups): a
        # quick two-note upward sparkle, distinct from "confirm"'s slower
        # perfect-fifth chime so cargo collection reads as its own thing.
        self.define("pickup", [
            {"freq": 880.0, "dur": 0.07, "wave": "sine", "attack": 0.003, "decay": 0.05, "amp": 0.7},
            {"freq": 1318.51, "dur": 0.11, "wave": "sine", "attack": 0.003, "decay": 0.08, "amp": 0.6, "delay": 0.045},
        ], volume=0.5)


# Shared instance - see module docstring.
sound_board = SoundBoard()
