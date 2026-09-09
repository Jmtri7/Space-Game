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

from game.config_source import story_path, story_catalogue
from game.graphics.expand import expand, expand_body, compose_worn, apply_walk


@functools.lru_cache(maxsize=None)
def _load(story, *parts):
    """One graphics-pipeline file (`graphics/<parts>`), resolved through the
    story's shared modules (see game/config_source.py) - the story's own copy
    wins, else the first module that provides it. None if nobody does."""
    import json
    path = story_path(story, "graphics", *parts)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _materials(story):
    """The story's material table merged over its modules' - so a story can
    add or restyle a material a shared figure kit defines without copying the
    whole file. (Catalogue-merged, unlike the first-hit `_load`.)"""
    return story_catalogue(story, os.path.join("graphics", "materials.json"))


def _draw_order(story):
    """The story's worn-figure draw order (`graphics/draw_order.json`'s
    `order`): body section names interleaved with garment tags. None if the
    story hasn't got one - compose_worn then falls back to the body's sections."""
    return (_load(story, "draw_order.json") or {}).get("order")


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


@functools.lru_cache(maxsize=None)
def _design_view(story, ref):
    """A design's `"view"` ("elevation" for an upright billboard, else None)."""
    kind, name = ref.split("/", 1)
    return (_load(story, kind, name + ".json") or {}).get("view")


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
        view = _design_view(story, ref)
        if view:
            entry["view"] = view          # "elevation" -> LocationScreen billboards it
    else:
        entry["parts"] = list(_expand_craft(story, ref, pal, lod, kind == "space_stations"))
    return entry


# --- Person bodies -------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _body_worn(story, body_name, set_name, palette_name, extra_articles=()):
    """(body_design, composed_parts) for a pipeline outfit: the body with its
    set's articles plus any `extra_articles` (equipped at runtime - see
    Person.equip_article) fitted and merged, ready for apply_walk / mirroring.
    `extra_articles` must be a tuple (hashable) so this stays cacheable."""
    body = _load(story, "body", body_name + ".json")
    if body is None:
        return None, None
    mats = _materials(story)
    pal = _palette(story, palette_name)

    def load_asset(kind, nm):
        return _load(story, kind, nm + ".json")

    body_parts = expand_body(body, pal, mats, load=load_asset)
    names = []
    if set_name:
        sd = _load(story, "sets", set_name + ".json") or {}
        names += sd.get("articles", [])
    names += list(extra_articles)

    # resolve each name to (geometry design, item overrides); an id may be an
    # item (items/<id>.json - a shared geometry with its own colour/shade) or a
    # bare article id.
    resolved = []
    for a in names:
        it = _load(story, "items", a + ".json")
        if it and it.get("geometry"):
            ad = _load(story, "articles", it["geometry"] + ".json")
            kw = dict(color=it.get("color"), shade=it.get("shade"),
                      parts=it.get("parts"))
            geom_id = it["geometry"]
        else:
            ad, kw, geom_id = _load(story, "articles", a + ".json"), {}, a
        if ad:
            resolved.append((ad, kw, geom_id))

    def _is_hair(ad, gid):
        return ad.get("slot") == "hair" or gid.startswith("hair_")

    # a headgear article may declare `"hides_hair": true` - a raised hood, a
    # sealed helmet - which drops every hairstyle from the outfit.
    hide_hair = any(ad.get("hides_hair") for ad, _, _ in resolved)

    # compose_worn stacks every part by the story's draw order (body sections +
    # garment tags); a region with no tag sits at its animation group. Within a
    # slot the set's article list order breaks ties (later article on top).
    arts = [expand(ad, pal, mats, body=body, **kw)
            for ad, kw, gid in resolved
            if not (_is_hair(ad, gid) and hide_hair)]
    worn = (compose_worn(body, body_parts, *arts, order=_draw_order(story))
            if arts else body_parts)
    return body, worn


def has_pipeline_body(outfit):
    return bool(outfit) and "body" in outfit


WALK_BUCKETS = 24  # walk-cycle poses cached per outfit (see worn_frame)


@functools.lru_cache(maxsize=1024)
def _worn_frame_cached(story, body_name, set_name, palette_name, extra_articles, walk_bucket):
    """Cached flat parts list for one outfit at one walk-cycle bucket
    (`walk_bucket` None = rest pose, else 0..WALK_BUCKETS-1). The dict objects
    are shared - callers must treat them read-only (Person._draw_pipeline_body
    projects and lerps into fresh dicts, never mutates these)."""
    body, worn = _body_worn(story, body_name, set_name, palette_name, extra_articles)
    if worn is None:
        return ()
    if walk_bucket is None:
        return tuple(worn)
    rig = _load(story, "body", (body.get("rig", {}).get("walk") or "rig_walk") + ".json")
    if not rig:
        return tuple(worn)
    return tuple(apply_walk([dict(p) for p in worn], body, rig, walk_bucket / WALK_BUCKETS))


def worn_frame(story, outfit, walk_t=None):
    """Read-only cached parts list for a pipeline-bodied Person. `walk_t` in
    [0, 1) is quantised to WALK_BUCKETS poses so a walking figure hits the
    cache instead of re-running apply_walk (per-part trig) every frame. The
    hot render path (Person._draw_pipeline_body) uses this; body_frame()
    stays the mutable-copy API for tools/tests."""
    bucket = None if walk_t is None else round(walk_t * WALK_BUCKETS) % WALK_BUCKETS
    return _worn_frame_cached(story, outfit.get("body"), outfit.get("set"),
                              outfit.get("palette", ""),
                              tuple(outfit.get("extra_articles", ())), bucket)


def body_frame(story, outfit, walk_t=None):
    """A fresh (mutable) flat parts list for a pipeline-bodied Person,
    optionally deformed to walk-cycle fraction `walk_t` in [0, 1). Coords are
    in body units (PLAYER_H tall, feet at y=0, y negative up, facing
    screen-left). For the per-frame render path use worn_frame()."""
    body, worn = _body_worn(story, outfit.get("body"), outfit.get("set"),
                            outfit.get("palette", ""),
                            tuple(outfit.get("extra_articles", ())))
    if worn is None:
        return []
    if walk_t is None:
        return [dict(p) for p in worn]
    rig = _load(story, "body", (body.get("rig", {}).get("walk") or "rig_walk") + ".json")
    if not rig:
        return [dict(p) for p in worn]
    return apply_walk([dict(p) for p in worn], body, rig, walk_t)
