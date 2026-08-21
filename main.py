import pygame
import sys
import math
import random

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
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
        self.angle = 0
        self.distance_from_station = 150
        self.orbit_angle = 0
        self.station_x = screen_width * 0.75
        self.station_y = screen_height * 0.3

    def update(self):
        self.orbit_angle = (self.orbit_angle + 0.5) % 360
        rad = math.radians(self.orbit_angle)
        self.x = self.station_x + math.cos(rad) * self.distance_from_station
        self.y = self.station_y + math.sin(rad) * self.distance_from_station
        self.angle = (self.orbit_angle + 90) % 360

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
            points.append((int(self.x + rotated_x), int(self.y + rotated_y)))

        pygame.draw.polygon(surface, (100, 200, 255), points)
        pygame.draw.circle(surface, (150, 220, 255), (int(self.x), int(self.y)), int(size * 0.25))

    def get_distance(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

class NPC:
    def __init__(self, x, y, behavior="wander"):
        self.x = x
        self.y = y
        self.behavior = behavior
        self.wander_time = 0
        self.wander_x = 0
        self.wander_y = 0

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
        pygame.draw.rect(surface, (255, 150, 150), (int(self.x - 4), int(self.y - 8), 8, 8))

class StationInterior:
    def __init__(self):
        self.player_x = screen_width // 2
        self.player_y = screen_height - 100
        self.room_width = screen_width
        self.room_height = screen_height
        self.bar_x = 150
        self.bar_y = 80

        self.bartender = NPC(self.bar_x, self.bar_y, "bar")
        self.wanderer = NPC(self.room_width // 2, self.room_height // 2, "wander")

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_l:
                    return "exit_station"
        return None

    def update(self):
        keys = pygame.key.get_pressed()
        speed = 3
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player_x -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player_x += speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player_y -= speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player_y += speed

        self.player_x = max(30, min(self.room_width - 30, self.player_x))
        self.player_y = max(30, min(self.room_height - 30, self.player_y))

        self.wanderer.update(self.room_width, self.room_height)

    def draw(self, surface):
        surface.fill((40, 40, 60))

        pygame.draw.rect(surface, (60, 60, 80), (0, 0, self.room_width, self.room_height), 3)

        pygame.draw.rect(surface, (100, 80, 40), (self.bar_x - 60, self.bar_y - 20, 120, 40))
        font = pygame.font.Font(None, int(20 * min(screen_width, screen_height) / 600.0))
        bar_text = font.render("BAR", True, (200, 200, 100))
        surface.blit(bar_text, (self.bar_x - 20, self.bar_y - 10))

        self.bartender.draw(surface)
        self.wanderer.draw(surface)

        pygame.draw.rect(surface, (0, 255, 0), (int(self.player_x - 6), int(self.player_y), 12, 16))
        pygame.draw.rect(surface, (100, 255, 100), (int(self.player_x - 4), int(self.player_y - 8), 8, 8))

        scale = min(screen_width, screen_height) / 600.0
        font_small = pygame.font.Font(None, int(16 * scale))
        help_text = font_small.render("WASD/Arrows to move, L/ESC to exit", True, (200, 200, 200))
        surface.blit(help_text, (10, 10))

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
        self.station = SpaceStation(screen_width * 0.75, screen_height * 0.3)
        self.ai_ship = AIShip(screen_width * 0.75, screen_height * 0.3 - 150)
        self.landing_text = 0

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
