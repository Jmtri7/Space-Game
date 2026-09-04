"""Frame-timing metrics for the main loop: how long each rendered frame
takes and where that time goes.

One shared instance (`metrics`, created at the bottom of this file) is fed
by `main.py`'s loop once per iteration and read by the DEBUG overlay
(`draw_overlay()`). This mirrors the shared-instance pattern `game/utils.py`
uses for `Camera` - a single module-level object reachable through helpers -
which is why this module holds a class *and* module-level functions (an
intentional One Class Per File exception, see docs/ARCHITECTURE.md's "Project
Layout & File Conventions"; `ui_theme.py` is an exception for the same reason).

**Cost:** `record()` is a handful of float subtractions and deque appends,
and each `span()` is two `perf_counter()` calls - cheap enough to run
unconditionally. Only the on-screen overlay is gated on
`constants.DEBUG_MODE`.
"""
import collections
import contextlib
import time

import pygame

import game.constants as constants
import game.utils as utils
from game.utils import get_font, get_ui_scale

# Rolling window, in frames, that every average/peak is computed over.
# 120 == ~2 s at 60 FPS: long enough to smooth per-frame jitter, short
# enough to react to a real regression while you're looking at it.
WINDOW = 120

# The phases one loop iteration is split into, in loop order. `main.py`
# times each with perf_counter deltas and passes them to record(); the
# overlay lists them in this order. Their times sum to "frame" (the total
# measured work per iteration, excluding the clock.tick() FPS-cap sleep).
PHASES = ("input", "sim", "render", "present")

# How many of the hottest named spans (see span()) the overlay lists.
TOP_SPANS = 6


class PerfMetrics:
    """Rolling frame-time statistics. Fed once per frame via record(); the
    finer-grained sub-sections are timed with the span() context manager
    from anywhere in the codebase and folded in by the next record()."""

    def __init__(self, window=WINDOW):
        self.window = window
        self._frame = collections.deque(maxlen=window)          # total work, ms
        self._phases = {p: collections.deque(maxlen=window) for p in PHASES}
        self._steps = collections.deque(maxlen=window)          # sim steps / frame
        self._spans = {}                                        # name -> deque(ms)
        self._cur_spans = {}                                    # name -> ms this frame
        self._fps = 0.0

    @contextlib.contextmanager
    def span(self, name):
        """Time a named sub-section and add it to this frame's bucket
        `name` (accumulating if the same name is entered more than once in
        a frame). The bucket is rolled into its window by the next
        record(). Keep spans with the same prefix non-overlapping if you
        want their buckets to sum cleanly - a nested span double-counts
        into its own bucket by design."""
        start = time.perf_counter()
        try:
            yield
        finally:
            ms = (time.perf_counter() - start) * 1000.0
            self._cur_spans[name] = self._cur_spans.get(name, 0.0) + ms

    def record(self, phase_ms, n_steps, fps):
        """Called once per loop iteration from main.py.

        phase_ms: {phase_name: milliseconds} for the PHASES above.
        n_steps:  fixed sim steps run this frame (see advance_accumulator) -
                  >1 means the machine fell behind and ran catch-up steps.
        fps:      pygame Clock.get_fps() (its own ~10-frame rolling average).
        """
        total = 0.0
        for p in PHASES:
            v = phase_ms.get(p, 0.0)
            self._phases[p].append(v)
            total += v
        self._frame.append(total)
        self._steps.append(n_steps)
        self._fps = fps

        # Roll each span bucket into its window. A span that didn't fire
        # this frame still records 0.0 so its average decays instead of
        # freezing at its last value.
        for name in set(self._spans) | set(self._cur_spans):
            self._spans.setdefault(name, collections.deque(maxlen=self.window))
            self._spans[name].append(self._cur_spans.get(name, 0.0))
        self._cur_spans = {}

    @staticmethod
    def _avg(d):
        return sum(d) / len(d) if d else 0.0

    def _stat(self, d):
        return self._avg(d), (max(d) if d else 0.0)

    def hot_spans(self, limit=TOP_SPANS):
        """(name, avg_ms, peak_ms) for the slowest tracked spans, worst
        average first."""
        rows = [(name, *self._stat(samples)) for name, samples in self._spans.items()]
        rows.sort(key=lambda r: r[1], reverse=True)
        return rows[:limit]

    def summary_lines(self):
        """List of display strings for the DEBUG overlay."""
        budget = 1000.0 / constants.FPS
        frame_avg, frame_peak = self._stat(self._frame)
        steps_avg, steps_peak = self._stat(self._steps)

        lines = [
            "PERF  (` toggles debug)",
            f"FPS {self._fps:5.1f}   budget {budget:.2f} ms/frame",
            f"frame    avg {frame_avg:6.2f}  peak {frame_peak:6.2f} ms",
        ]
        for p in PHASES:
            avg, peak = self._stat(self._phases[p])
            lines.append(f" {p:<8}avg {avg:6.2f}  peak {peak:6.2f} ms")
        lines.append(f"sim steps/frame  avg {steps_avg:.2f}  peak {int(steps_peak)}")

        hot = self.hot_spans()
        if hot:
            lines.append("- hot spans (avg / peak ms) -")
            for name, avg, peak in hot:
                lines.append(f" {name:<20}{avg:6.2f} / {peak:6.2f}")
        return lines


metrics = PerfMetrics()


def draw_overlay(surface, zoom=None, zoom_kind=None):
    """Bottom-left translucent panel of `metrics`, drawn by `main.py` after
    the active screen's own draw() so it appears on every screen. No-op
    unless `constants.DEBUG_MODE` (toggled with the backtick key).

    zoom / zoom_kind: the active view's camera zoom factor and its kind
    ("space" or "interior"), appended as one extra line when known - None on
    a screen with no camera (menus, dialogs). main.py passes these in since
    it's the one place that already knows which screen instance just drew;
    zoom is an instantaneous camera value, not a frame-timing rolling stat,
    so it bypasses PerfMetrics.record()/span() rather than being folded in."""
    if not constants.DEBUG_MODE:
        return

    ui_scale = get_ui_scale()
    font = get_font(int(15 * ui_scale))
    pad = int(8 * ui_scale)
    line_h = font.get_linesize()

    lines = metrics.summary_lines()
    if zoom is not None:
        lines.append(f"{zoom_kind} zoom  {zoom:.2f}x")

    rendered = [font.render(text, True, (0, 255, 0)) for text in lines]
    width = max((s.get_width() for s in rendered), default=0) + pad * 2
    height = line_h * len(rendered) + pad * 2

    margin = int(10 * ui_scale)
    x = margin
    y = max(margin, utils.screen_height - margin - height)

    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((8, 10, 20, 210))
    pygame.draw.rect(panel, (120, 120, 145), panel.get_rect(), width=1)
    surface.blit(panel, (x, y))

    ty = y + pad
    for s in rendered:
        surface.blit(s, (x + pad, ty))
        ty += line_h
