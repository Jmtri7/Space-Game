"""Landable space objects (stations and celestial bodies)."""
import math
import pygame
import game.constants as constants
from game.constants import GREEN
from game.utils import get_scale, to_screen, load_json
from game.world.world_object import WorldObject


class Landable(WorldObject):
    """A landable object in the game world (space station or moon)."""
    def __init__(self, x, y, graphics=None, interiors=None, name=""):
        super().__init__(x, y, graphics=graphics)
        self.name = name
        self.interiors = interiors or {}
        # Live LocationScreen cache, keyed by interior key ("default" for
        # stations, "city"/"wilderness" for moons) - populated lazily by
        # SpaceScreen.get_interior_screen(). Kept here (not constructed
        # here) since Landable is a world object and shouldn't depend on
        # game.screens; this just lets the interior's state (NPCs, player
        # position within it) persist across visits instead of resetting
        # every time, and lets it keep simulating in the background while
        # the player is elsewhere.
        self.interior_screens = {}

        # Determine type: if graphics has rotation_speed or shape="hexapod/octagon", it's a station
        self.is_station = "rotation_speed" in self.graphics or self.graphics.get("shape") in ["hexapod", "octagon"]
        # Fixed logical size of this landable's interior LocationScreens -
        # a station's rooms are laid out at 1600x1200, a moon's at 1600x1600
        # (moons cover far more ground: outdoor structures/wander routines
        # need the room). Lives here, not re-derived from is_station at
        # every call site (main.py and DockRoutine both used to), so both
        # player and AI code just ask this landable. Only the no-"rooms"
        # fallback bounds actually read this - an authored interior with
        # "rooms" is bounded by the room polygons themselves (see
        # LocationScreen.can_move_to / plan_path).
        self.interior_world_size = (1600, 1200) if self.is_station else (1600, 1600)

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
            # Culture windows/lights - [lx, ly] points in the same absolute
            # local space as local_points, turning with the hull. Colour
            # falls back to the (culture-resolved) core glow. Same dark
            # near-hull outline ships use. A station with no "windows" entry
            # draws none, exactly as before.
            self.outline_color = tuple(self.graphics.get("outline_color", (20, 18, 25)))
            self.window_color = tuple(self.graphics.get("window_color", self.core_color))
            self.windows = self.graphics.get("windows", [])
            self.parts = self.graphics.get("parts", [])

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

    def get_ship_entry_key(self):
        """Which of self.interiors is the room a docked ship actually
        opens into - the one with a portal (or, for a single-room flat-
        "entrance" config, itself) marked return_to_ship. Landing (see
        SpaceScreen) and an AI pilot's DockRoutine should both always walk
        in here, not wherever a save/route happened to leave off - matches
        the fiction that walking out of your ship always puts you in the
        same docking-bay doorway. Lives here (not on SpaceScreen/Character)
        since it's purely a property of this landable's own interior
        layout - the player and AI shouldn't each need their own copy of
        the logic that figures it out. Falls back to "default" if nothing
        in self.interiors declares a return_to_ship path, so a story that
        never marks a room ship-facing keeps working as before."""
        for key, config in self.interiors.items():
            config = load_json(config) if isinstance(config, str) else config
            if not config:
                continue
            portals = config.get("portals")
            if portals:
                if any(p.get("return_to_ship") for p in portals):
                    return key
            elif config.get("return_to_ship", True):
                return key
        return "default"

    def interior_adjacency(self):
        """{interior_key: [connected interior keys]} for every interior in
        self.interiors - the graph of which rooms connect to which, read
        straight from each interior's own raw connected_locations
        (portals-list style: the union across all its portals). Lets a
        role's routine (DockRoutine) plan a multi-hop route to a specific
        room - e.g. wherever get_ship_entry_key() says the ship actually
        is - by searching this graph, instead of hardcoding the name of
        whichever room happens to lead there in one particular story."""
        graph = {}
        for key, config in self.interiors.items():
            config = load_json(config) if isinstance(config, str) else config
            if not config:
                continue
            portals = config.get("portals")
            if portals:
                graph[key] = [loc for portal in portals for loc in portal.get("connected_locations", [])]
            else:
                graph[key] = list(config.get("connected_locations", []))
        return graph

    def get_interior_labels(self):
        """Display label for each configured interior (station's "default",
        or a moon's "city"/"wilderness"), for the targeting HUD and any
        other place that needs to list what's inside this landable."""
        labels = []
        for key, interior_config in self.interiors.items():
            if isinstance(interior_config, dict):
                labels.append(interior_config.get("label", key))
            else:
                labels.append(key)
        return labels

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
        """Draw a rotating space station - all turning with self.rotation.

        A "parts" list is a complete multi-polygon silhouette pulled from the
        design atlas: when present it fully replaces the flat hull polygon, the
        circular "windows" dots, AND the plain core beacon (drawing any of those
        on top just shows the old shape bleeding past the new one - the atlas
        specimen already draws its own hub and any see-through gap). local_points
        stays authoritative for collision/size math, just not for drawing."""
        if self.parts:
            self._draw_parts(surface, self.parts, self.rotation, 1, self.color,
                             self.window_color, self.outline_color)
            return
        self._draw_rotated_polygon(surface, self.local_points, self.rotation, self.color, outline_color=self.outline_color)
        if self.windows:
            rad = math.radians(self.rotation)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            radius = max(1, int(round(self.size * 0.05 * scale)))
            for lx, ly in self.windows:
                wx = self.x + (lx * cos_a - ly * sin_a)
                wy = self.y + (lx * sin_a + ly * cos_a)
                pygame.draw.circle(surface, self.window_color, to_screen(wx, wy), radius)
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
