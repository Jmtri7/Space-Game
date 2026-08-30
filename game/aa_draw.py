"""Anti-aliasing draw helpers, dispatched on `constants.AA_MODE`.

`AA_MODE == "gfxdraw"` draws the shape through `pygame.gfxdraw` and lays a
matching antialiased outline (`aapolygon` / `aacircle`) over it, so a
primitive's silhouette edge is smoothed where it meets whatever is behind it.
`"off"` and `"supersample"` both fall straight through to `pygame.draw`
(supersampling is done wholesale in `main.py`'s PHASE 3, so the per-primitive
path stays plain for it).

`polygon()` and `circle()` are drop-in replacements for `pygame.draw.polygon`
/ `pygame.draw.circle`, including the trailing `width` argument (0 = filled,
>0 = stroke of that thickness). Every helper falls back to plain `pygame.draw`
on anything gfxdraw can't handle - a degenerate shape, coordinates outside its
int16 working range (well off-screen), or an internal error - so a call site
can adopt one unconditionally.

Only world/asset draw sites route through here (see the callers in
`game/world/` and `game/screens/location_screen.py`); menus and the HUD keep
using `pygame.draw` directly. `pygame.gfxdraw` is imported explicitly because
`import pygame` does not pull it in.
"""
import pygame
try:
    import pygame.gfxdraw  # not pulled in by `import pygame`
except (ImportError, ModuleNotFoundError):
    pass  # e.g. the tests' pygame stub - gfxdraw mode is inert there anyway

import game.constants as constants

# pygame.gfxdraw works in signed 16-bit coordinates; a shape reaching well
# past the window (a big ship half off-screen, a zoomed-in room polygon) can
# wrap. pygame.draw clips cleanly, so bail to it beyond this bound.
_GFX_COORD_LIMIT = 30000

# pygame.error is a real exception class at runtime; under the tests' pygame
# stub it's a MagicMock, which can't appear in an `except` tuple - fall back
# to Exception there.
_PYGAME_ERROR = pygame.error if isinstance(getattr(pygame, "error", None), type) else Exception
_GFX_ERRORS = (ValueError, OverflowError, TypeError, IndexError, _PYGAME_ERROR)


def _gfx_active():
    return constants.AA_MODE == "gfxdraw"


def _color(c):
    """gfxdraw wants a plain 3- or 4-tuple of ints."""
    t = tuple(int(v) for v in c)
    return t if len(t) in (3, 4) else t[:3]


def _fits(values):
    return all(-_GFX_COORD_LIMIT <= v <= _GFX_COORD_LIMIT for v in values)


def polygon(surface, color, points, width=0):
    """`pygame.draw.polygon(surface, color, points, width)` with an
    antialiased edge in gfxdraw mode."""
    if _gfx_active() and len(points) >= 3:
        ipts = [(round(x), round(y)) for x, y in points]
        if _fits(v for p in ipts for v in p):
            try:
                col = _color(color)
                if width:
                    pygame.draw.polygon(surface, color, points, width)
                else:
                    pygame.gfxdraw.filled_polygon(surface, ipts, col)
                pygame.gfxdraw.aapolygon(surface, ipts, col)
                return
            except _GFX_ERRORS:
                pass
    pygame.draw.polygon(surface, color, points, width)


def circle(surface, color, center, radius, width=0):
    """`pygame.draw.circle(surface, color, center, radius, width)` with an
    antialiased rim in gfxdraw mode."""
    r = int(radius)
    if _gfx_active() and r >= 1:
        cx, cy = round(center[0]), round(center[1])
        if _fits((cx, cy, r)):
            try:
                col = _color(color)
                if width:
                    pygame.draw.circle(surface, color, center, radius, width)
                else:
                    pygame.gfxdraw.filled_circle(surface, cx, cy, r, col)
                pygame.gfxdraw.aacircle(surface, cx, cy, r, col)
                return
            except _GFX_ERRORS:
                pass
    pygame.draw.circle(surface, color, center, radius, width)
