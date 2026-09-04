"""Bridge from the design-JSON graphics pipeline (docs/GRAPHICS_PIPELINE.md)
to the game's runtime asset lookups.

A story that uses the pipeline keeps its geometry in
`config/stories/<story>/graphics/<kind>/<name>.json` and its *catalogue*
entries (`graphics.json`, `building_types.json`) point at a design instead of
inlining a `parts` list:

    "courier": { "design": "ships/courier", "size": 11, "rotation_speed": 0 }

`get_graphics_asset` / `get_building_type` call `attach_design()` here, which
runs the shared `expand()` once (cached) and drops the resulting flat parts
list onto the entry under `"parts"` - exactly the shape
`WorldObject.draw_parts` already draws. No bake step: the design JSON is still
the only source of geometry, expanded at load.
"""
import os
import functools

from game.graphics.expand import expand, expand_body, compose_worn, apply_walk


def _gdir(story):
    return os.path.join("config", "stories", story, "graphics")


@functools.lru_cache(maxsize=None)
def _load(story, *parts):
    import json
    path = os.path.join(_gdir(story), *parts)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _materials(story):
    return _load(story, "materials.json") or {}


def _palette(story, name):
    return _load(story, "palettes", name + ".json") or {}


@functools.lru_cache(maxsize=None)
def _expand_craft(story, ref, palette_name, lod, scale):
    """A ship or station design -> parts list. `scale` multiplies every
    coordinate: 1 for a ship (Ship.draw passes unit=size itself), the
    design's own `size` for a station (LandingSite.draw passes unit=1, so
    its parts are authored in absolute units - see graphics.json)."""
    kind, name = ref.split("/", 1)
    design = _load(story, kind, name + ".json")
    if design is None:
        return []
    pal = _palette(story, palette_name or design.get("palette", ""))
    s = design.get("size", 1) if scale else 1
    parts = expand(design, pal, _materials(story), lod=lod)
    out = []
    for p in parts:
        q = {k: v for k, v in p.items() if k in ("color", "opacity")}
        q["points"] = [[x * s, y * s] for x, y in p["points"]] if s != 1 else p["points"]
        out.append(q)
    return out


@functools.lru_cache(maxsize=None)
def _expand_decoration(story, ref, palette_name, lod):
    """A decoration design -> parts list in absolute local units
    (draw_parts uses unit=1 for buildings)."""
    kind, name = ref.split("/", 1)
    design = _load(story, kind, name + ".json")
    if design is None:
        return []
    pal = _palette(story, palette_name or design.get("palette", ""))
    parts = expand(design, pal, _materials(story), lod=lod)
    return [{k: v for k, v in p.items() if k in ("points", "color", "opacity")}
            for p in parts]


def attach_design(story, entry, kind="ships"):
    """If `entry` carries a `"design"` ref, expand it and attach `"parts"`.
    `kind` is the graphics.json category: "space_stations" parts are scaled
    to absolute units, "decorations" stay absolute, "ships" stay fractional.
    Returns the same dict (mutated). A no-op for a plain inline entry."""
    ref = entry.get("design")
    if not ref:
        return entry
    lod = entry.get("design_lod")
    pal = entry.get("design_palette")
    if kind == "decorations":
        entry["parts"] = list(_expand_decoration(story, ref, pal, lod))
    else:
        entry["parts"] = list(_expand_craft(story, ref, pal, lod, kind == "space_stations"))
    return entry


# --- Person bodies -------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _body_worn(story, body_name, set_name, palette_name):
    """(body_design, composed_parts) for a pipeline outfit: the body with its
    set's articles fitted and merged, ready for apply_walk / mirroring."""
    body = _load(story, "body", body_name + ".json")
    if body is None:
        return None, None
    mats = _materials(story)
    pal = _palette(story, palette_name)

    def load_asset(kind, nm):
        return _load(story, kind, nm + ".json")

    body_parts = expand_body(body, pal, mats, load=load_asset)
    arts = []
    if set_name:
        sd = _load(story, "sets", set_name + ".json") or {}
        for a in sd.get("articles", []):
            ad = _load(story, "articles", a + ".json")
            if ad:
                arts.append(expand(ad, pal, mats, body=body))
    worn = compose_worn(body, body_parts, *arts) if arts else body_parts
    return body, worn


def has_pipeline_body(outfit):
    return bool(outfit) and "body" in outfit


def body_frame(story, outfit, walk_t=None):
    """A flat parts list for a pipeline-bodied Person, optionally deformed to
    walk-cycle fraction `walk_t` in [0, 1). Coords are in body units
    (PLAYER_H tall, feet at y=0, y negative up, facing screen-left)."""
    body, worn = _body_worn(story, outfit.get("body"),
                            outfit.get("set"), outfit.get("palette", ""))
    if worn is None:
        return []
    if walk_t is None:
        return [dict(p) for p in worn]
    rig = _load(story, "body", (body.get("rig", {}).get("walk") or "rig_walk") + ".json")
    if not rig:
        return [dict(p) for p in worn]
    return apply_walk([dict(p) for p in worn], body, rig, walk_t)
