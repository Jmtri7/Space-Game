"""Headless render of one interior to a PNG for layout/collision review.

    python scripts/render_interior.py sol_alpha station default out.png

Draws the interior exactly as LocationScreen.draw() would (floor, decorations,
structures, portals), then overlays every building footprint in GREEN and,
for reference, each structure's anchor point in MAGENTA and its building_type
label. Use it to eyeball items like "footprint extends too far below the
graphic" and "overlapping decorations" without launching the game.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

import game.constants as constants  # noqa: E402
from game.constants import GAME_WIDTH, GAME_HEIGHT  # noqa: E402
from game.utils import (  # noqa: E402
    load_json, set_screen_size, set_camera_offset, set_camera_zoom,
    set_camera_zoom_limits, set_camera_angle, to_screen, get_font,
)
from game.screens.location_screen import LocationScreen  # noqa: E402


def render(story, system_id, site, interior_key, out_path):
    system = load_json(f"config/stories/{story}/systems/{system_id}.json")
    site_cfg = system[site]
    interiors = site_cfg["interiors"]
    cfg = interiors[interior_key]
    is_station = site == "station"
    w, h = (1600, 1600) if is_station else (2400, 1800)

    pygame.init()
    pygame.display.set_mode((1, 1))
    surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))

    screen = LocationScreen(config_data=cfg, world_width=w, world_height=h, story=story)
    screen.interior_key = interior_key

    # optional focus: FOCUS="cx,cy,zoom" env var
    focus = os.environ.get("FOCUS")
    if focus:
        cx, cy, zoom = (float(v) for v in focus.split(","))
    else:
        cx, cy, zoom = GAME_WIDTH / 2, GAME_HEIGHT / 2, 1.0

    set_screen_size(GAME_WIDTH, GAME_HEIGHT)
    set_camera_angle(0)
    set_camera_offset(cx - GAME_WIDTH / 2, cy - GAME_HEIGHT / 2)
    screen.camera_zoom_min = zoom
    screen.camera_zoom_max = zoom
    screen.camera_zoom = zoom
    set_camera_zoom_limits(zoom, zoom)
    set_camera_zoom(zoom)

    constants.DEBUG_MODE = True
    # move the player well out of frame so it doesn't clutter the shot
    screen.player.x, screen.player.y = -9999, -9999
    screen.draw(surface, draw_hud=False)

    # structure anchors + type labels
    font = get_font(13)
    for s in screen.structures:
        bt = s.get("building_type", s.get("type", "?"))
        sx, sy = to_screen(s["x"], s["y"])
        pygame.draw.circle(surface, (255, 0, 255), (sx, sy), 4)
        surface.blit(font.render(bt, True, (255, 0, 255)), (sx + 5, sy - 6))

    pygame.image.save(surface, out_path)
    print(f"wrote {out_path}  ({len(screen.structures)} structures, "
          f"{len(screen.building_footprints)} footprints)")


if __name__ == "__main__":
    # python scripts/render_interior.py <system_id> <site> <interior_key> <out.png>
    render("default", sys.argv[1], sys.argv[2], sys.argv[3],
           sys.argv[4] if len(sys.argv) > 4 else "interior.png")
