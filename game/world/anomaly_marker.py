"""Visual marker for a mission-computer scan-anomaly target (see
game/world/generated_mission.py) - a pulsing glow orb drawn at the
anomaly's coordinate while its system is the one currently in view.
Purely decorative: SpaceScreen draws one fresh each frame straight from
the active scan missions in Possessions.generated_missions, so there's no
instance to own or update - never part of save/load, same as OrePickup's
own drift/AsteroidField's asteroids."""
import math
import pygame
from game.utils import to_screen, get_scale

BASE_COLOR = (170, 130, 255)   # violet - reads as "anomaly", distinct from
                                # any commodity/outfit icon color in play
PULSE_SPEED = 0.05             # radians/tick - independent of frame rate
CORE_RADIUS = 6                # world units, before scale/pulse


def draw_anomaly_marker(surface, x, y, ticks):
    """Draw one pulsing glow orb at world (x, y). `ticks`
    (pygame.time.get_ticks()) is passed in rather than read here so every
    anomaly visible this frame pulses in lock-step instead of drifting out
    of phase against each other."""
    scale = get_scale()
    screen_x, screen_y = to_screen(x, y)
    pulse = 0.6 + 0.4 * math.sin(ticks * PULSE_SPEED)
    core_r = max(2, int(round(CORE_RADIUS * scale * (0.8 + 0.2 * pulse))))
    glow_r = max(core_r + 1, int(core_r * (2.6 + 1.0 * pulse)))

    # Soft halo: a few nested translucent rings on their own alpha surface,
    # fattest/brightest in the middle - the same "layered alpha circles"
    # idea CentralStar's glow uses, just faded through more steps and
    # animated instead of a single static halo.
    glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
    for i, mult in enumerate((1.0, 0.65, 0.35)):
        r = max(1, int(glow_r * mult))
        alpha = max(0, int(80 * pulse * (1 - i * 0.25)))
        pygame.draw.circle(glow_surf, (*BASE_COLOR, alpha), (glow_r, glow_r), r)
    surface.blit(glow_surf, (screen_x - glow_r, screen_y - glow_r))

    bright_core = tuple(min(255, int(c * 1.3)) for c in BASE_COLOR)
    pygame.draw.circle(surface, bright_core, (screen_x, screen_y), core_r)
    pygame.draw.circle(surface, (255, 255, 255), (screen_x, screen_y), max(1, core_r // 2))
