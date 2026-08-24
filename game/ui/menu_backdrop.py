"""Animated star system background shared by menu-style screens (main menu,
story selector) - a star, an orbiting planet, a spinning station, and a ship
flying an elliptical patrol route."""
import math
import random
import pygame
import game.utils as utils

STAR_COLOR = (255, 214, 120)
PLANET_LIT_COLOR = (90, 140, 200)
PLANET_SHADOW_COLOR = (35, 55, 85)
STATION_COLOR = (190, 195, 205)
STATION_ACCENT = (255, 210, 90)
SHIP_HULL_COLOR = (210, 70, 70)
SHIP_OUTLINE_COLOR = (30, 15, 15)
SHIP_THRUST_COLOR = (110, 200, 255)


class MenuBackdrop:
    """Procedurally generated, animated star system rendered behind menu UI.

    Stars are generated once from a seed so each screen's field is stable
    across frames; everything else animates from pygame's clock, so no
    per-frame update() call is needed - just draw() each frame.
    """
    def __init__(self, seed=1337, star_count=160):
        self._stars = self._generate_stars(seed, star_count)

    def _generate_stars(self, seed, count):
        """Stars as screen-fraction positions so they hold their layout
        across window resizes without regenerating."""
        rng = random.Random(seed)
        stars = []
        for _ in range(count):
            fx = rng.random()
            fy = rng.random()
            brightness = rng.randint(90, 255)
            radius = rng.choice((1, 1, 1, 2))
            twinkle_phase = rng.uniform(0, math.tau)
            stars.append((fx, fy, brightness, radius, twinkle_phase))
        return stars

    def draw(self, surface):
        surface.fill((0, 0, 0))
        t = pygame.time.get_ticks() / 1000.0
        w, h = utils.screen_width, utils.screen_height
        self._draw_stars(surface, t, w, h)

        # Keep the star system off to one side so it stays visible around a
        # centered menu panel instead of being fully hidden behind it.
        center = (w * 0.78, h * 0.30)
        span = min(w, h)

        star_radius = max(14, int(span * 0.032))
        self._draw_star(surface, center, star_radius, t)

        planet_pos = self._orbit_point(center, span * 0.20, span * 0.09, t * 0.12, 0.0)
        self._draw_planet(surface, planet_pos, max(9, int(span * 0.022)))

        station_pos = self._orbit_point(center, span * 0.13, span * 0.06, -t * 0.30, 1.8)
        self._draw_station(surface, station_pos, max(9, int(span * 0.02)), t)

        ship_rx, ship_ry = span * 0.55, span * 0.24
        ship_center = (w * 0.42, h * 0.78)
        ship_angle = t * 0.45
        ship_pos = self._orbit_point(ship_center, ship_rx, ship_ry, ship_angle, 0.0)
        heading = math.degrees(math.atan2(math.cos(ship_angle) * ship_ry, -math.sin(ship_angle) * ship_rx))
        self._draw_ship(surface, ship_pos, heading, max(8, int(span * 0.016)))

    def _orbit_point(self, center, radius_x, radius_y, angle, phase):
        a = angle + phase
        return (center[0] + math.cos(a) * radius_x, center[1] + math.sin(a) * radius_y)

    def _draw_stars(self, surface, t, w, h):
        for fx, fy, brightness, radius, phase in self._stars:
            twinkle = 0.6 + 0.4 * math.sin(t * 1.5 + phase)
            b = max(0, min(255, int(brightness * twinkle)))
            pos = (int(fx * w), int(fy * h))
            pygame.draw.circle(surface, (b, b, b), pos, radius)

    def _draw_star(self, surface, center, radius, t):
        pulse = 1.0 + 0.06 * math.sin(t * 1.2)
        c = (int(center[0]), int(center[1]))
        for i, alpha_scale in ((3, 0.15), (2, 0.28), (1.4, 0.5)):
            glow_r = int(radius * i * pulse)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            glow_color = (*STAR_COLOR, int(255 * alpha_scale))
            pygame.draw.circle(glow_surf, glow_color, (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (c[0] - glow_r, c[1] - glow_r), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, STAR_COLOR, c, int(radius * pulse))

    def _draw_planet(self, surface, pos, radius):
        c = (int(pos[0]), int(pos[1]))
        pygame.draw.circle(surface, PLANET_LIT_COLOR, c, radius)
        shadow_rect = pygame.Rect(c[0] - radius, c[1] - radius, radius * 2, radius * 2)
        shadow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(shadow_surf, (*PLANET_SHADOW_COLOR, 210), (radius, radius), radius)
        surface.blit(shadow_surf, shadow_rect, area=pygame.Rect(0, 0, radius, radius * 2))
        pygame.draw.ellipse(
            surface, (200, 200, 200, 90),
            (c[0] - radius * 1.6, c[1] - radius * 0.28, radius * 3.2, radius * 0.56), 1
        )

    def _draw_station(self, surface, pos, size, t):
        spin = t * 40  # degrees/sec
        c = pos
        spokes = 4
        for i in range(spokes):
            angle = math.radians(spin + i * (360 / spokes))
            dx, dy = math.cos(angle) * size, math.sin(angle) * size
            pygame.draw.line(surface, STATION_COLOR, c, (c[0] + dx, c[1] + dy), max(1, int(size * 0.12)))
        pygame.draw.circle(surface, STATION_COLOR, (int(c[0]), int(c[1])), max(2, int(size * 0.32)))
        pygame.draw.circle(surface, STATION_ACCENT, (int(c[0]), int(c[1])), max(1, int(size * 0.14)))
        ring_points = []
        for i in range(spokes):
            angle = math.radians(spin + i * (360 / spokes) + 45)
            ring_points.append((c[0] + math.cos(angle) * size * 1.05, c[1] + math.sin(angle) * size * 1.05))
        pygame.draw.polygon(surface, STATION_COLOR, ring_points, 1)

    def _draw_ship(self, surface, pos, heading_deg, size):
        rad = math.radians(heading_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        local_points = [(size, 0), (-size * 0.7, size * 0.6), (-size * 0.35, 0), (-size * 0.7, -size * 0.6)]
        points = []
        for lx, ly in local_points:
            rx = lx * cos_a - ly * sin_a
            ry = lx * sin_a + ly * cos_a
            points.append((pos[0] + rx, pos[1] + ry))
        pygame.draw.polygon(surface, SHIP_HULL_COLOR, points)
        pygame.draw.polygon(surface, SHIP_OUTLINE_COLOR, points, 1)

        flame_len = size * (0.8 + 0.3 * math.sin(pygame.time.get_ticks() / 60.0))
        flame_local = [(-size * 0.35, size * 0.22), (-size * 0.35 - flame_len, 0), (-size * 0.35, -size * 0.22)]
        flame_points = []
        for lx, ly in flame_local:
            rx = lx * cos_a - ly * sin_a
            ry = lx * sin_a + ly * cos_a
            flame_points.append((pos[0] + rx, pos[1] + ry))
        pygame.draw.polygon(surface, SHIP_THRUST_COLOR, flame_points)
