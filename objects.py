"""Game objects: stations, NPCs, celestial bodies, star field, and walkable areas."""
import pygame
import math
import random
from constants import (
    GAME_WIDTH, GAME_HEIGHT, YELLOW, WHITE, GREEN, DEBUG_MODE
)
from utils import (
    get_scale, to_screen, to_screen_x, to_screen_y, get_offset, load_json,
    draw_debug_marker, draw_target_brackets, get_ui_scale, get_ui_offset
)


class SpaceStation:
    """A rotating space station in the game world."""
    def __init__(self, x, y, graphics=None):
        self.x = x
        self.y = y
        self.rotation = 0

        # Load graphics from config or use defaults
        if graphics:
            self.size = graphics.get("size", 40)
            self.color = tuple(graphics.get("color", [100, 200, 255]))
            self.core_color = tuple(graphics.get("core_color", [150, 220, 255]))
            self.rotation_speed = graphics.get("rotation_speed", 0.5)
            self.local_points = graphics.get("local_points", self._default_points())
            self.landing_distance = graphics.get("landing_distance", self.size * 3.5)
        else:
            self.size = 40
            self.color = (100, 200, 255)
            self.core_color = (150, 220, 255)
            self.rotation_speed = 0.5
            self.local_points = self._default_points()
            self.landing_distance = 140

    def _default_points(self):
        """Default hexapod shape."""
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
        self.rotation = (self.rotation + self.rotation_speed) % 360

    def draw(self, surface):
        scale = get_scale()
        rad = math.radians(self.rotation)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        points = []
        for lx, ly in self.local_points:
            rotated_x = lx * cos_a - ly * sin_a
            rotated_y = lx * sin_a + ly * cos_a
            points.append(to_screen(self.x + rotated_x, self.y + rotated_y))

        pygame.draw.polygon(surface, self.color, points)
        pygame.draw.circle(surface, self.core_color, to_screen(self.x, self.y), max(1, int(round(self.size * 0.25 * scale))))

    def get_distance(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)


class Person:
    """Base class for NPCs and other characters in the game."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.wander_time = 0
        self.wander_x = 0
        self.wander_y = 0

    def draw(self, surface):
        scale = get_scale()
        pygame.draw.rect(surface, (200, 100, 100), (*to_screen(self.x - 6, self.y), to_screen_x(12), to_screen_y(16)))
        pygame.draw.circle(surface, (255, 150, 150), to_screen(self.x, self.y - 6), max(1, int(5 * scale)))

    def get_distance(self, px, py):
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)


class Dialogue:
    """Dialogue box for NPC interaction."""
    def __init__(self, npc_name, greetings, options):
        self.npc_name = npc_name
        self.greetings = greetings
        self.options = options
        self.selected_option = 0

    def draw(self, surface, scale):
        font_title = pygame.font.Font(None, int(24 * scale))
        font_text = pygame.font.Font(None, int(18 * scale))

        screen_w = surface.get_width()
        screen_h = surface.get_height()
        box_width = int(400 * scale)
        box_height = int(250 * scale)
        box_x = screen_w // 2 - box_width // 2
        box_y = screen_h // 2 - box_height // 2

        pygame.draw.rect(surface, (40, 40, 60), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(surface, (100, 150, 200), (box_x, box_y, box_width, box_height), 3)

        title = font_title.render(self.npc_name, True, (200, 200, 255))
        surface.blit(title, (box_x + 20, box_y + 10))

        greeting = font_text.render(self.greetings[0], True, (200, 200, 200))
        surface.blit(greeting, (box_x + 20, box_y + 40))

        for i, option in enumerate(self.options):
            color = (255, 255, 0) if i == self.selected_option else (150, 150, 150)
            text = font_text.render(f"> {option}", True, color)
            surface.blit(text, (box_x + 30, box_y + 100 + i * 30))

        close_text = font_text.render("Press ESC to close", True, (150, 150, 150))
        surface.blit(close_text, (box_x + 20, box_y + box_height - 30))


class NPC(Person):
    """Non-player character with dialogue and behavior."""
    def __init__(self, x, y, behavior="wander", name="NPC", greeting="Hello!", dialogue_options=None):
        super().__init__(x, y)
        self.behavior = behavior
        self.name = name
        self.greeting = greeting
        self.dialogue_options = dialogue_options or ["Talk", "Leave"]
        self.dialogue = Dialogue(name, [greeting], self.dialogue_options)


class StarField:
    """Procedurally generated star field background."""
    def __init__(self, num_stars=200):
        self.num_stars = num_stars
        self.stars = []
        self.generate_stars()

    def generate_stars(self):
        self.stars = []
        random.seed(42)
        for _ in range(self.num_stars):
            x = random.randint(0, GAME_WIDTH)
            y = random.randint(0, GAME_HEIGHT)
            brightness = random.randint(100, 255)
            self.stars.append((x, y, brightness))

    def draw(self, surface):
        for x, y, brightness in self.stars:
            pygame.draw.circle(surface, (brightness, brightness, brightness), to_screen(x, y), 1)


class Moon:
    """A celestial moon object in space."""
    def __init__(self, x, y, graphics=None):
        self.x = x
        self.y = y
        self.phase = 0

        # Load graphics from config or use defaults
        if graphics:
            self.size = graphics.get("size", 30)
            self.color = tuple(graphics.get("color", [200, 200, 200]))
            self.crater_color = tuple(graphics.get("crater_color", [150, 150, 150]))
            self.craters = graphics.get("craters", [])
            self.landing_distance = graphics.get("landing_distance", self.size * 3.5)
        else:
            self.size = 30
            self.color = (200, 200, 200)
            self.crater_color = (150, 150, 150)
            self.craters = [
                {"x": -8, "y": -5, "radius": 4},
                {"x": 10, "y": 8, "radius": 5}
            ]
            self.landing_distance = 105

    def update(self):
        self.phase = (self.phase + 0.1) % 360

    def draw(self, surface):
        scale = get_scale()
        pygame.draw.circle(surface, self.color, to_screen(self.x, self.y), max(1, int(round(self.size * scale))))
        # Draw craters
        for crater in self.craters:
            crater_x = self.x + crater.get("x", 0)
            crater_y = self.y + crater.get("y", 0)
            crater_radius = crater.get("radius", 4)
            pygame.draw.circle(surface, self.crater_color, to_screen(crater_x, crater_y), max(1, int(crater_radius * scale)))

    def get_distance(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)
