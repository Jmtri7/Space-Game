"""Headless render of one pipeline asset to a PNG, using the real draw path
(Ship.draw / LandingSite.draw / Person.draw) - not an approximation. This is
the tool the culture-design gates in docs/CULTURE_DESIGN.md render with.

    python scripts/render_pipeline_asset.py ship <story> <ship_type_id> out.png
    python scripts/render_pipeline_asset.py station <story> <space_station_id> out.png
    python scripts/render_pipeline_asset.py outfit <story> <outfit_id> out.png [angle]

`ship`/`station` render at angle 0 (nose up) by default - pass a 4th arg
(ship) to rotate. `outfit` renders standing still (no walk cycle).
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from game.constants import GAME_WIDTH, GAME_HEIGHT  # noqa: E402
from game.utils import (  # noqa: E402
    get_graphics_asset, get_ship_type, set_screen_size, set_camera_offset,
    set_camera_zoom, set_camera_zoom_limits, set_camera_angle, to_screen,
)
from game.world.ship import Ship  # noqa: E402
from game.world.landing_site import LandingSite  # noqa: E402
from game.world.person import Person  # noqa: E402
from game.world.world_object import draw_parts  # noqa: E402
from game.graphics.expand import expand, expand_body, compose_worn  # noqa: E402
from game.graphics.story_assets import _load, _palette, _materials  # noqa: E402


def _setup_camera(cx, cy, zoom):
    """Same fixed GAME_WIDTH/GAME_HEIGHT logical surface + camera setup as
    scripts/render_interior.py - the camera's scale math is derived from
    those constants, not the surface size, so this must match."""
    pygame.init()
    pygame.display.set_mode((1, 1))
    set_screen_size(GAME_WIDTH, GAME_HEIGHT)
    set_camera_angle(0)
    set_camera_offset(cx - GAME_WIDTH / 2, cy - GAME_HEIGHT / 2)
    set_camera_zoom_limits(zoom, zoom)
    set_camera_zoom(zoom)
    return pygame.Surface((GAME_WIDTH, GAME_HEIGHT))


def render_ship(story, ship_type_id, out_path, angle=0):
    graphics = get_graphics_asset(story, "ships", ship_type_id)
    ship_type = get_ship_type(story, ship_type_id)
    surface = _setup_camera(0, 0, 6.0)
    surface.fill((28, 28, 32))
    ship = Ship(0, 0, graphics=graphics)
    ship.apply_ship_type(ship_type)
    ship.angle = angle
    ship.force_thrusters = True   # show the thruster flame too
    ship.draw(surface)
    pygame.image.save(surface, out_path)
    print(f"wrote {out_path}")


def render_station(story, station_id, out_path):
    graphics = get_graphics_asset(story, "space_stations", station_id)
    surface = _setup_camera(0, 0, 3.0)
    surface.fill((28, 28, 32))
    site = LandingSite(0, 0, graphics=graphics, name=station_id)
    site.draw(surface)
    pygame.image.save(surface, out_path)
    print(f"wrote {out_path}")


def render_article(story, article_id, out_path, body_name="human_masc"):
    """One bespoke article on the bare body, both cuts side by side isn't
    done here (call twice, once per body_name) - the article gate wants to
    see the piece's own silhouette contribution, not a full dressed look."""
    body_design = _load(story, "body", body_name + ".json")
    order = (_load(story, "draw_order.json") or {}).get("order")
    materials = _materials(story)
    body_pal = _palette(story, "civilian")
    body_parts = expand_body(body_design, body_pal, materials)
    article_design = _load(story, "articles", article_id + ".json")
    article_pal = _palette(story, article_design.get("palette", "civilian"))
    article_parts = expand(article_design, article_pal, materials, body=body_design)
    parts = compose_worn(body_design, body_parts, article_parts, order=order)
    surface = _setup_camera(0, -15, 10.0)
    surface.fill((28, 28, 32))
    draw_parts(surface, parts, 0, 0, 0, 1, "#888888", "#88ccff")
    pygame.image.save(surface, out_path)
    print(f"wrote {out_path}")


def render_outfit(story, outfit_id, out_path, facing=1):
    asset = get_graphics_asset(story, "outfits", outfit_id)
    surface = _setup_camera(0, -15, 10.0)
    surface.fill((28, 28, 32))
    p = Person(0, 0, name=outfit_id, outfit=asset)
    p.facing = -1 if facing < 0 else 1
    p.draw(surface)
    pygame.image.save(surface, out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    kind = sys.argv[1]
    story = sys.argv[2]
    asset_id = sys.argv[3]
    out = sys.argv[4] if len(sys.argv) > 4 else f"{asset_id}.png"
    extra = float(sys.argv[5]) if len(sys.argv) > 5 else 0
    if kind == "ship":
        render_ship(story, asset_id, out, angle=extra)
    elif kind == "station":
        render_station(story, asset_id, out)
    elif kind == "outfit":
        render_outfit(story, asset_id, out, facing=extra)
    elif kind == "article":
        render_article(story, asset_id, out, body_name="human_femme" if extra else "human_masc")
    else:
        raise SystemExit(f"unknown kind {kind!r} - use ship/station/outfit/article")
