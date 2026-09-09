"""Resolve a story's config through the shared modules it opts into.

Every config path in the game used to be a hardcoded
``f"config/stories/{story}/..."`` - nothing was shared between stories. A
story's ``story.json`` may now carry::

    "modules": ["figures-human", "ships-core", "audio-core"]

Each name is a directory under ``config/modules/<name>/`` whose subtree
mirrors a story's own (``graphics/body/*.json``, ``ship_types.json``,
``audio.json``, ...). This module is the single place that knows the search
order:

* :func:`story_path` - for **per-name files** (the graphics pipeline:
  ``graphics/<kind>/<name>.json``, palettes, sets, bodies, articles). Checks
  the story directory first, then each module in the order the story lists
  them, and returns the first path that exists. Falls back to the story path
  when nothing matches, so "file absent" behaves exactly as before.

* :func:`story_catalogue` - for the **flat ``{id: entry}`` JSON files**
  (``graphics.json``, ``cultures.json``, ``commodities.json``,
  ``ship_types.json``, ...). Every module's dict is merged *under* the
  story's, entry by entry, so a story overrides or extends a shared entry
  without copying the rest. Earlier modules win over later ones; the story
  always wins.

This is a deliberately function-only module (see the one-class-per-file rule
in docs/architecture/*). It must not import :mod:`game.utils` at module load
time - ``utils`` imports *this* - so the couple of ``load_json`` calls below
are lazy.
"""
import copy
import os

MODULES_DIR = os.path.join("config", "modules")


def _story_dir(story):
    return os.path.join("config", "stories", story)


def _load_json(path, cache=True):
    import game.utils as utils
    return utils.load_json(path, cache=cache)


def story_modules(story):
    """The ordered list of shared-module names a story opts into
    (``story.json``'s ``"modules"``), or ``[]``. Earlier entries take
    precedence over later ones."""
    story_json = _load_json(os.path.join(_story_dir(story), "story.json")) or {}
    mods = story_json.get("modules") or []
    return [m for m in mods if isinstance(m, str)]


def _search_roots(story):
    """Directories to look in for a story's config, most-specific first:
    the story itself, then each declared module."""
    roots = [_story_dir(story)]
    roots += [os.path.join(MODULES_DIR, m) for m in story_modules(story)]
    return roots


def story_path(story, *relparts):
    """Absolute-ish path to a per-name config file, resolved through the
    story's modules. Returns the first of ``story/<rel>`` then
    ``modules/<m>/<rel>`` that exists on disk; if none do, returns the story
    path unchanged (so a missing file is still a missing file at the place
    callers expect)."""
    rel = os.path.join(*relparts)
    for root in _search_roots(story):
        candidate = os.path.join(root, rel)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(_story_dir(story), rel)


def _deep_merge_under(base, overlay):
    """Return ``overlay`` layered on top of ``base``: keys in ``overlay``
    win, nested dicts merge recursively, everything else is replaced. Neither
    argument is mutated."""
    out = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge_under(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


_catalogue_cache = {}


def _clear_cache():
    """Drop the merged-catalogue cache - paired with
    ``utils.clear_json_cache()`` (which calls this) for tests that rewrite a
    config file mid-run."""
    _catalogue_cache.clear()


def story_catalogue(story, filename):
    """Load one flat ``{id: entry}`` config file for a story, merged with the
    same file from each of its modules. The story's own entries win; among
    modules, earlier in the ``modules`` list wins. Missing files contribute
    nothing. Result is cached (keyed by story + filename) and shared - treat
    it read-only, exactly like ``load_json``'s cached dicts (callers that
    mutate already ``dict(...)``-copy the entry first)."""
    key = (story, filename)
    if key in _catalogue_cache:
        return _catalogue_cache[key]

    merged = {}
    # Modules low-to-high priority first (so a later pass overwrites an
    # earlier one), then the story on top. _search_roots is high-to-low, so
    # walk it in reverse.
    for root in reversed(_search_roots(story)):
        data = _load_json(os.path.join(root, filename))
        if isinstance(data, dict):
            merged = _deep_merge_under(merged, data)

    _catalogue_cache[key] = merged
    return merged


def module_versions(story):
    """``{module_name: version}`` from each module's ``module.json``
    (``"version"`` field, default ``"0"``). Used by the save-load story
    version check so a save records what shared modules it was built
    against."""
    out = {}
    for name in story_modules(story):
        meta = _load_json(os.path.join(MODULES_DIR, name, "module.json")) or {}
        out[name] = str(meta.get("version", "0"))
    return out
