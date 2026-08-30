"""Pull specimen <svg> blocks out of an already-built atlas HTML by
aria-label substring, so the per-culture split atlases can reuse the
current (shipped, extracted-to-parts) ship / station / building / decoration
/ layout art without re-drawing it.

grab(src, "issue cutter") -> the <svg>...</svg> string, grid def re-inserted
so it renders standalone.
"""
import pathlib
import re

_HERE = pathlib.Path(__file__).parent
_CACHE = {}
_GRIDDEF = ('<defs><pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse">'
            '<circle cx="1.5" cy="1.5" r="1" fill="#ffffff" fill-opacity="0.05"/></pattern></defs>')


def _html(src):
    if src not in _CACHE:
        _CACHE[src] = (_HERE / src).read_text(encoding="utf-8")
    return _CACHE[src]


def grab(src, label, viewbox=None):
    """First <svg> in `src` whose aria-label contains `label` (case-insensitive).
    Re-inserts the grid <defs> right after the opening tag. Raises if not found."""
    for m in re.finditer(r'<svg\b[^>]*aria-label="([^"]*)"[\s\S]*?</svg>', _html(src)):
        if label.lower() in m.group(1).lower():
            svg = m.group(0)
            svg = re.sub(r'(<svg\b[^>]*>)', r'\1' + _GRIDDEF, svg, count=1)
            if viewbox:
                svg = re.sub(r'viewBox="[^"]*"', f'viewBox="{viewbox}"', svg, count=1)
            return svg
    raise KeyError(f"no plate matching {label!r} in {src}")


def grab_all(src, *labels):
    return [grab(src, l) for l in labels]
