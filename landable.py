"""Landable space objects (stations and celestial bodies)."""
import pygame
import constants
from constants import GREEN
from utils import get_scale, to_screen
from world_object import WorldObject


class Landable(WorldObject):
    """A landable object in the game world (space station or moon)."""
    def __init__(self, x, y, graphics=None, interiors=None):
        super().__init__(x, y, graphics=graphics)
        self.interiors = interiors or {}

        # Determine type: if graphics has rotation_speed or shape="hexapod/octagon", it's a station
        self.is_station = "rotation_speed" in self.graphics or self.graphics.get("shape") in ["hexapod", "octagon"]

        # Common properties
        self.size = self.graphics.get("size", 40 if self.is_station else 30)
        self.color = tuple(self.graphics.get("color", [100, 200, 255] if self.is_station else [200, 200, 200]))
        self.landing_distance = self.graphics.get("landing_distance", self.size * 3.5)

        # Station-specific properties
        if self.is_station:
            self.rotation = 0
            self.core_color = tuple(self.graphics.get("core_color", [150, 220, 255]))
            self.rotation_speed = self.graphics.get("rotation_speed", 0.5)
            self.local_points = self.graphics.get("local_points", self._default_station_points())

        # Moon-specific properties
        else:
            self.phase = 0
            self.crater_color = tuple(self.graphics.get("crater_color", [150, 150, 150]))
            self.craters = self.graphics.get("craters", [])

    def _default_station_points(self):
        """Default hexapod shape for stations."""
        size = self.size
        return [
            (0, -size * 0.8),
            (size * 0.4, -size * 0.3),
            (size * 0.5, size * 0.3),
            (size * 0.2, size * 0.6),
            (-size * 0.2, size * 0.6),
            (-size * 0.5, size * 0.3),
            (-size * 0.4, -size * 0.3),
        ]

    def update(self):
        """Update animation state."""
        if self.is_station:
            self.rotation = (self.rotation + self.rotation_speed) % 360
        else:
            self.phase = (self.phase + 0.1) % 360

    def draw(self, surface):
        """Draw the landable object."""
        scale = get_scale()

        if self.is_station:
            self._draw_station(surface, scale)
        else:
            self._draw_moon(surface, scale)

        # Debug: draw landing radius circle
        if constants.DEBUG_MODE:
            landing_radius_screen = int(self.landing_distance * scale)
            pygame.draw.circle(surface, GREEN, to_screen(self.x, self.y), landing_radius_screen, 1)

    def _draw_station(self, surface, scale):
        """Draw a rotating space station."""
        self._draw_rotated_polygon(surface, self.local_points, self.rotation, self.color)
        pygame.draw.circle(surface, self.core_color, to_screen(self.x, self.y), max(1, int(round(self.size * 0.25 * scale))))

    def _draw_moon(self, surface, scale):
        """Draw a celestial moon with craters."""
        pygame.draw.circle(surface, self.color, to_screen(self.x, self.y), max(1, int(round(self.size * scale))))
        # Draw craters
        for crater in self.craters:
            crater_x = self.x + crater.get("x", 0)
            crater_y = self.y + crater.get("y", 0)
            crater_radius = crater.get("radius", 4)
            pygame.draw.circle(surface, self.crater_color, to_screen(crater_x, crater_y), max(1, int(crater_radius * scale)))
