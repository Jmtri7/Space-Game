import pygame
import sys
import math
import random

pygame.init()

info = pygame.display.Info()
SCREEN_WIDTH = min(info.current_w - 100, 1600)
SCREEN_HEIGHT = min(info.current_h - 100, 900)
FPS = 60

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Space Game")
clock = pygame.time.Clock()

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
YELLOW = (255, 255, 0)
DARK_GRAY = (60, 60, 60)

screen_width = SCREEN_WIDTH
screen_height = SCREEN_HEIGHT

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 0
        self.thrust = 0
        self.velocity_x = 0
        self.velocity_y = 0
        self.rotation_speed = 5
        self.max_thrust = 0.3
        self.max_velocity = 4.0
        self.drag = 0.98

    def handle_input(self, keys):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.angle = (self.angle - self.rotation_speed) % 360
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.angle = (self.angle + self.rotation_speed) % 360
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.thrust = min(self.thrust + 0.02, self.max_thrust)
        else:
            self.thrust = max(self.thrust - 0.02, 0)

    def update(self):
        rad = math.radians(self.angle)
        if self.thrust > 0.01:
            self.velocity_x += math.sin(rad) * self.thrust
            self.velocity_y -= math.cos(rad) * self.thrust

            speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)
            if speed > self.max_velocity:
                scale = self.max_velocity / speed
                self.velocity_x *= scale
                self.velocity_y *= scale

            self.velocity_x *= self.drag
            self.velocity_y *= self.drag

        self.x += self.velocity_x
        self.y += self.velocity_y

        if self.x < 0:
            self.x = screen_width
        elif self.x > screen_width:
            self.x = 0
        if self.y < 0:
            self.y = screen_height
        elif self.y > screen_height:
            self.y = 0

    def draw(self, surface):
        scale = min(screen_width, screen_height) / 600.0
        ship_size = 15 * scale
        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        local_points = [
            (0, -ship_size),
            (-ship_size * 0.6, ship_size * 0.6),
            (ship_size * 0.6, ship_size * 0.6),
        ]

        points = []
        for lx, ly in local_points:
            rotated_x = lx * cos_a - ly * sin_a
            rotated_y = lx * sin_a + ly * cos_a
            points.append((int(self.x + rotated_x), int(self.y + rotated_y)))

        pygame.draw.polygon(surface, DARK_GRAY, points)

        if self.thrust > 0.05:
            flame_length = self.thrust * 30 * scale
            back_x = (points[1][0] + points[2][0]) / 2
            back_y = (points[1][1] + points[2][1]) / 2
            back_point = (int(back_x), int(back_y))
            flame_x = int(back_point[0] - sin_a * flame_length)
            flame_y = int(back_point[1] + cos_a * flame_length)
            pygame.draw.line(surface, YELLOW, back_point, (flame_x, flame_y), max(1, int(2 * scale)))

class AIShip:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = random.randint(0, 360)
        self.velocity_x = 0
        self.velocity_y = 0
        self.thrust = 0
        self.thrust_timer = 0
        self.max_thrust = 0.15
        self.drag = 0.99
        self.state = "accelerate"
        self.state_timer = 0

    def update(self):
        self.state_timer -= 1

        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        if self.state == "accelerate":
            if self.state_timer <= 0:
                self.state = "brake"
                self.state_timer = random.randint(30, 60)
            else:
                self.thrust = self.max_thrust
                self.angle = (self.angle + random.uniform(-1, 1)) % 360

        elif self.state == "brake":
            if speed < 0.15:
                self.state = "accelerate"
                self.state_timer = random.randint(40, 80)
                self.angle = random.uniform(0, 360)
                self.thrust = 0
                self.velocity_x *= 0.95
                self.velocity_y *= 0.95
            else:
                velocity_angle = math.degrees(math.atan2(self.velocity_x, -self.velocity_y)) % 360
                target_angle = (velocity_angle + 180) % 360
                angle_diff = (target_angle - self.angle) % 360
                if angle_diff > 180:
                    angle_diff -= 360

                if abs(angle_diff) > 2:
                    self.angle = (self.angle + angle_diff * 0.1) % 360
                self.thrust = self.max_thrust

        rad = math.radians(self.angle)
        if self.thrust > 0.01:
            self.velocity_x += math.sin(rad) * self.thrust
            self.velocity_y -= math.cos(rad) * self.thrust
            self.velocity_x *= self.drag
            self.velocity_y *= self.drag

        self.x += self.velocity_x
        self.y += self.velocity_y

        if self.x < 0:
            self.x = screen_width
        elif self.x > screen_width:
            self.x = 0
        if self.y < 0:
            self.y = screen_height
        elif self.y > screen_height:
            self.y = 0

    def draw(self, surface):
        scale = min(screen_width, screen_height) / 600.0
        ship_size = 12 * scale
        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        local_points = [
            (0, -ship_size),
            (-ship_size * 0.6, ship_size * 0.6),
            (ship_size * 0.6, ship_size * 0.6),
        ]

        points = []
        for lx, ly in local_points:
            rotated_x = lx * cos_a - ly * sin_a
            rotated_y = lx * sin_a + ly * cos_a
            points.append((int(self.x + rotated_x), int(self.y + rotated_y)))

        pygame.draw.polygon(surface, (150, 150, 200), points)

        if self.thrust > 0.05:
            flame_length = self.thrust * 20 * scale
            back_x = (points[1][0] + points[2][0]) / 2
            back_y = (points[1][1] + points[2][1]) / 2
            flame_x = int(back_x - sin_a * flame_length)
            flame_y = int(back_y + cos_a * flame_length)
            pygame.draw.line(surface, (200, 150, 0), (int(back_x), int(back_y)), (flame_x, flame_y), max(1, int(scale)))

class SpaceStation:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rotation = 0

    def update(self):
        self.rotation = (self.rotation + 0.5) % 360

    def draw(self, surface):
        scale = min(screen_width, screen_height) / 600.0
        size = 40 * scale
        rad = math.radians(self.rotation)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        local_points = [
            (0, -size * 0.8),
            (size * 0.4, -size * 0.3),
            (size * 0.5, size * 0.3),
            (size * 0.2, size * 0.6),
            (-size * 0.2, size * 0.6),
            (-size * 0.5, size * 0.3),
            (-size * 0.4, -size * 0.3),
        ]

        points = []
        for lx, ly in local_points:
            rotated_x = lx * cos_a - ly * sin_a
            rotated_y = lx * sin_a + ly * cos_a
            points.append((int(round(self.x + rotated_x)), int(round(self.y + rotated_y))))

        pygame.draw.polygon(surface, (100, 200, 255), points)
        pygame.draw.circle(surface, (150, 220, 255), (int(round(self.x)), int(round(self.y))), max(1, int(round(size * 0.25))))

    def get_distance(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

class Dialogue:
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

class NPC:
    def __init__(self, x, y, behavior="wander", name="NPC", greeting="Hello!", dialogue_options=None):
        self.x = x
        self.y = y
        self.behavior = behavior
        self.wander_time = 0
        self.wander_x = 0
        self.wander_y = 0
        self.name = name
        self.greeting = greeting
        self.dialogue_options = dialogue_options or ["Talk", "Leave"]
        self.dialogue = Dialogue(name, [greeting], self.dialogue_options)

    def update(self, room_width, room_height):
        if self.behavior == "wander":
            self.wander_time -= 1
            if self.wander_time <= 0:
                self.wander_x = (random.random() - 0.5) * 2
                self.wander_y = (random.random() - 0.5) * 2
                self.wander_time = random.randint(60, 180)

            self.x += self.wander_x
            self.y += self.wander_y

            self.x = max(50, min(room_width - 50, self.x))
            self.y = max(50, min(room_height - 50, self.y))

    def draw(self, surface):
        pygame.draw.rect(surface, (200, 100, 100), (int(self.x - 6), int(self.y), 12, 16))
        pygame.draw.circle(surface, (255, 150, 150), (int(self.x), int(self.y - 10)), 5)

    def get_distance(self, px, py):
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)

class StationInterior:
    def __init__(self):
        self.room_width = screen_width
        self.room_height = screen_height
        self.player_x = screen_width // 2
        self.player_y = screen_height - 80

        self.hallway_narrow_width = 80
        self.hallway_wide_width = 200
        self.hallway_x = screen_width // 2 - self.hallway_narrow_width // 2
        self.hallway_transition_y = screen_height // 2

        self.bar_x = screen_width // 2
        self.bar_y = 100
        self.door_x = screen_width // 2
        self.door_y = screen_height - 50

        self.bartender = NPC(self.bar_x, self.bar_y, "bar", "Bartender", "What'll it be?", ["Order drink", "Leave"])
        self.wanderer = NPC(self.room_width // 2, self.hallway_transition_y - 100, "wander", "Traveler", "Safe travels!", ["Thanks", "Leave"])
        self.door_guard = NPC(self.door_x, self.door_y, "bar", "Guard", "Welcome to the station.", ["Thanks", "Leave"])

        self.current_dialogue = None
        self.nearby_npc = None

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.current_dialogue:
                        self.current_dialogue = None
                    else:
                        return "exit_station"
                elif event.key == pygame.K_l:
                    return "exit_station"
                elif event.key == pygame.K_t and self.nearby_npc:
                    self.current_dialogue = self.nearby_npc.dialogue
                elif self.current_dialogue:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.current_dialogue.selected_option = (self.current_dialogue.selected_option - 1) % len(self.current_dialogue.options)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.current_dialogue.selected_option = (self.current_dialogue.selected_option + 1) % len(self.current_dialogue.options)
                    elif event.key == pygame.K_RETURN:
                        self.current_dialogue = None
            elif event.type == pygame.MOUSEBUTTONDOWN and self.current_dialogue:
                self._handle_dialogue_click(pygame.mouse.get_pos())
        return None

    def _handle_dialogue_click(self, mouse_pos):
        scale = min(screen_width, screen_height) / 600.0
        screen_w = screen_width
        screen_h = screen_height
        box_width = int(400 * scale)
        box_height = int(250 * scale)
        box_x = screen_w // 2 - box_width // 2
        box_y = screen_h // 2 - box_height // 2

        for i in range(len(self.current_dialogue.options)):
            option_y = box_y + 100 + i * int(30 * scale)
            if (mouse_pos[1] > option_y and mouse_pos[1] < option_y + int(25 * scale)):
                self.current_dialogue = None
                return

    def _is_in_hallway(self, x, y):
        if y > self.hallway_transition_y:
            return (x >= self.hallway_x + 10 and x <= self.hallway_x + self.hallway_narrow_width - 10 and y <= self.room_height - 30)
        else:
            hallway_wide_x = screen_width // 2 - self.hallway_wide_width // 2
            return (x >= hallway_wide_x + 10 and x <= hallway_wide_x + self.hallway_wide_width - 10 and y >= 30)

    def update(self):
        if self.current_dialogue:
            return

        keys = pygame.key.get_pressed()
        speed = 3
        new_x = self.player_x
        new_y = self.player_y

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            new_x -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            new_x += speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_y -= speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_y += speed

        if self._is_in_hallway(new_x, new_y):
            self.player_x = new_x
            self.player_y = new_y

        self.player_y = max(30, min(self.room_height - 30, self.player_y))

        self.wanderer.wander_time -= 1
        if self.wanderer.wander_time <= 0:
            self.wanderer.wander_x = (random.random() - 0.5) * 2
            self.wanderer.wander_y = (random.random() - 0.5) * 2
            self.wanderer.wander_time = random.randint(60, 180)

        new_wander_x = self.wanderer.x + self.wanderer.wander_x
        new_wander_y = self.wanderer.y + self.wanderer.wander_y

        if self._is_in_hallway(new_wander_x, new_wander_y):
            self.wanderer.x = new_wander_x
            self.wanderer.y = new_wander_y

        self.bartender.wander_time = float('inf')
        self.door_guard.wander_time = float('inf')

        self.nearby_npc = None
        for npc in [self.bartender, self.wanderer, self.door_guard]:
            if npc.get_distance(self.player_x, self.player_y) < 50:
                self.nearby_npc = npc
                break

    def draw(self, surface):
        surface.fill((30, 30, 50))

        hallway_wide_x = screen_width // 2 - self.hallway_wide_width // 2
        hallway_wide_width = self.hallway_wide_width

        pygame.draw.rect(surface, (50, 50, 70), (hallway_wide_x, 0, hallway_wide_width, self.hallway_transition_y))
        pygame.draw.rect(surface, (50, 50, 70), (self.hallway_x, self.hallway_transition_y, self.hallway_narrow_width, self.room_height - self.hallway_transition_y))

        pygame.draw.rect(surface, (60, 60, 80), (0, 0, self.room_width, self.room_height), 3)

        pygame.draw.line(surface, (80, 80, 100), (hallway_wide_x, 0), (self.hallway_x, self.hallway_transition_y), 2)
        pygame.draw.line(surface, (80, 80, 100), (hallway_wide_x + hallway_wide_width, 0), (self.hallway_x + self.hallway_narrow_width, self.hallway_transition_y), 2)

        pygame.draw.rect(surface, (100, 80, 40), (self.bar_x - 60, self.bar_y - 20, 120, 40))
        scale = min(screen_width, screen_height) / 600.0
        font = pygame.font.Font(None, int(20 * scale))
        bar_text = font.render("BAR", True, (200, 200, 100))
        surface.blit(bar_text, (self.bar_x - 20, self.bar_y - 10))

        self.bartender.draw(surface)
        self.wanderer.draw(surface)
        self.door_guard.draw(surface)

        pygame.draw.rect(surface, (0, 255, 0), (int(self.player_x - 6), int(self.player_y), 12, 16))
        pygame.draw.circle(surface, (100, 255, 100), (int(self.player_x), int(self.player_y - 10)), 5)

        font_small = pygame.font.Font(None, int(16 * scale))
        help_text = font_small.render("WASD/Arrows to move, L/ESC to exit", True, (200, 200, 200))
        surface.blit(help_text, (10, 10))

        if self.nearby_npc and not self.current_dialogue:
            talk_text = font_small.render("Press T to talk", True, (255, 255, 0))
            surface.blit(talk_text, (int(self.nearby_npc.x - 30), int(self.nearby_npc.y - 30)))

        if self.current_dialogue:
            self.current_dialogue.draw(surface, scale)

class StarField:
    def __init__(self, num_stars=200):
        self.num_stars = num_stars
        self.stars = []
        self.generate_stars()

    def generate_stars(self):
        self.stars = []
        random.seed(42)
        for _ in range(self.num_stars):
            x = random.randint(0, screen_width)
            y = random.randint(0, screen_height)
            brightness = random.randint(100, 255)
            self.stars.append((x, y, brightness))

    def draw(self, surface):
        for x, y, brightness in self.stars:
            pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), 1)

class GameScreen:
    def __init__(self):
        self.player = Player(screen_width // 2, screen_height // 2)
        self.star_field = StarField()
        self.station = SpaceStation(0, 0)
        self.ai_ship = AIShip(0, 0)
        self.landing_text = 0
        self._update_positions()

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "menu"
                elif event.key == pygame.K_l:
                    if self._can_land():
                        return "land"
        return None

    def _update_positions(self):
        self.station.x = screen_width * 0.75
        self.station.y = screen_height * 0.3
        self.ai_ship.x = screen_width * 0.75
        self.ai_ship.y = screen_height * 0.3 - 150

    def _can_land(self):
        distance = self.station.get_distance(self.player.x, self.player.y)
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
        return distance < 100 and speed < 0.5

    def update(self):
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        self.player.update()
        self.station.update()
        self.ai_ship.update()

        if self._can_land():
            self.landing_text = 60
        else:
            self.landing_text = max(0, self.landing_text - 1)

    def draw(self, surface):
        surface.fill(BLACK)
        self.star_field.draw(surface)
        self.station.draw(surface)
        self.ai_ship.draw(surface)
        self.player.draw(surface)

        if self.landing_text > 0:
            scale = min(screen_width, screen_height) / 600.0
            font = pygame.font.Font(None, int(24 * scale))
            land_text = font.render("Press L to land", True, YELLOW)
            surface.blit(land_text, (screen_width // 2 - land_text.get_width() // 2, screen_height - 60))

class Menu:
    def __init__(self):
        self.items = ["NEW", "LOAD", "QUIT"]
        self.selected_index = 0

    def _get_fonts(self):
        scale = min(screen_width, screen_height) / 600.0
        font_large = pygame.font.Font(None, int(72 * scale))
        font_menu = pygame.font.Font(None, int(48 * scale))
        return font_large, font_menu

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_index = (self.selected_index - 1) % len(self.items)
                elif event.key == pygame.K_DOWN:
                    self.selected_index = (self.selected_index + 1) % len(self.items)
                elif event.key == pygame.K_RETURN:
                    return self.items[self.selected_index].lower()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                return self._check_click(pygame.mouse.get_pos())
            elif event.type == pygame.MOUSEMOTION:
                self._update_selector_from_mouse(pygame.mouse.get_pos())
        return None

    def _update_selector_from_mouse(self, pos):
        for i in range(len(self.items)):
            rect = self._get_item_rect(i)
            if rect.collidepoint(pos):
                self.selected_index = i
                break

    def _check_click(self, pos):
        for i, item in enumerate(self.items):
            rect = self._get_item_rect(i)
            if rect.collidepoint(pos):
                self.selected_index = i
                return item.lower()
        return None

    def _get_item_rect(self, index):
        scale = min(screen_width, screen_height) / 600.0
        y_base = int(200 * scale)
        y_spacing = int(80 * scale)
        _, font_menu = self._get_fonts()
        text = font_menu.render(self.items[index], True, WHITE)
        rect = text.get_rect(center=(int(screen_width // 2 + 80 * scale), y_base + index * y_spacing))
        return rect

    def draw(self, surface):
        surface.fill(BLACK)

        scale = min(screen_width, screen_height) / 600.0
        font_large, font_menu = self._get_fonts()

        title = font_large.render("MENU", True, WHITE)
        surface.blit(title, (screen_width // 2 - title.get_width() // 2, int(50 * scale)))

        y_base = int(200 * scale)
        y_spacing = int(80 * scale)

        for i, item in enumerate(self.items):
            color = YELLOW if i == self.selected_index else GRAY
            text = font_menu.render(item, True, color)
            y = y_base + i * y_spacing
            surface.blit(text, (int(screen_width // 2 + 80 * scale), y))

            if i == self.selected_index:
                dot_radius = int(12 * scale)
                dot_x = int(screen_width // 2 + 40 * scale)
                pygame.draw.circle(surface, YELLOW, (dot_x, y + text.get_height() // 2), dot_radius)

def main():
    global screen_width, screen_height, screen
    try:
        menu = Menu()
        game_screen = None
        station_interior = None
        current_screen = "menu"
        running = True

        while running:
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.VIDEORESIZE:
                    screen_width, screen_height = event.size
                    screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
                    if game_screen:
                        game_screen.star_field.generate_stars()
                        game_screen._update_positions()

            if current_screen == "menu":
                selection = menu.handle_input(events)
                if selection == "quit":
                    running = False
                elif selection == "new":
                    game_screen = GameScreen()
                    current_screen = "game"
                menu.draw(screen)

            elif current_screen == "game":
                action = game_screen.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "menu":
                    current_screen = "menu"
                    game_screen = None
                elif action == "land":
                    station_interior = StationInterior()
                    current_screen = "station"
                game_screen.update()
                game_screen.draw(screen)

            elif current_screen == "station":
                action = station_interior.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "exit_station":
                    current_screen = "game"
                    station_interior = None
                if station_interior:
                    station_interior.update()
                    station_interior.draw(screen)

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
    except Exception as e:
        with open("error.txt", "w") as f:
            f.write(str(e))
            import traceback
            f.write("\n" + traceback.format_exc())
        pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
