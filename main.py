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

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "menu"
        return None

    def update(self):
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        self.player.update()

    def draw(self, surface):
        surface.fill(BLACK)
        self.star_field.draw(surface)
        self.player.draw(surface)

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
                game_screen.update()
                game_screen.draw(screen)

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
