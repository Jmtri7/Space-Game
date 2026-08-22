import pygame
import sys
import math
import random
import json
import os
from datetime import datetime

pygame.init()

GAME_WIDTH = 800
GAME_HEIGHT = 600
SAVE_DIR = "saves"

# Camera offset for following player
camera_offset_x = 0
camera_offset_y = 0

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

def get_scale():
    return min(screen_width / GAME_WIDTH, screen_height / GAME_HEIGHT)

def get_offset():
    scale = get_scale()
    offset_x = (screen_width - GAME_WIDTH * scale) / 2
    offset_y = (screen_height - GAME_HEIGHT * scale) / 2
    return (offset_x, offset_y)

def to_screen(x, y):
    scale = get_scale()
    offset_x, offset_y = get_offset()
    # Apply camera offset
    x_camera = x - camera_offset_x
    y_camera = y - camera_offset_y
    return (int(round(x_camera * scale + offset_x)), int(round(y_camera * scale + offset_y)))

def to_screen_x(x):
    scale = get_scale()
    return int(round(x * scale))

def to_screen_y(y):
    scale = get_scale()
    return int(round(y * scale))

def load_json(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        return None

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def _list_files_by_pattern(directory, prefix, suffix):
    files = []
    if not os.path.exists(directory):
        os.makedirs(directory)
    try:
        for file in os.listdir(directory):
            if file.startswith(prefix) and file.endswith(suffix):
                files.append(file)
    except:
        pass
    return sorted(files, reverse=True)

def get_save_files():
    return _list_files_by_pattern(SAVE_DIR, "save_", ".json")

def create_save_file(pilot_name, name, system_data, station_data, game_state=None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_data = {
        "pilot_name": pilot_name,
        "name": name,
        "timestamp": timestamp,
        "system": system_data,
        "station": station_data,
        "game_state": game_state or {}
    }
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    filename = f"{SAVE_DIR}/save_{pilot_name}_{timestamp}.json"
    save_json(filename, save_data)
    return filename

def load_save_file(filename):
    filepath = f"{SAVE_DIR}/{filename}"
    return load_json(filepath)

def _handle_scrolling_input(key, selected, items, scroll_offset, max_visible):
    if key in (pygame.K_UP, pygame.K_w):
        selected -= 1
        if selected < 0:
            selected = len(items) - 1
            scroll_offset = max(0, len(items) - max_visible)
        elif selected < scroll_offset:
            scroll_offset -= 1
    elif key in (pygame.K_DOWN, pygame.K_s):
        selected += 1
        if selected >= len(items):
            selected = 0
            scroll_offset = 0
        elif selected >= scroll_offset + max_visible:
            scroll_offset += 1
    return selected, scroll_offset

def _center_text_x(surface, text, offset_x=0):
    scale = get_scale()
    return int(offset_x + GAME_WIDTH * scale * 0.5 - text.get_width() // 2)

class SaveDialog:
    def __init__(self, pilot_name=""):
        self.pilot_name = pilot_name
        # Pre-populate with default save name
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.save_name = f"{pilot_name} - {timestamp}" if pilot_name else timestamp
        self.success_timer = 0
        self.existing_saves = self._get_all_saves()
        self.selected_existing = 0 if self.existing_saves else None
        self.input_mode = not self.existing_saves
        self.scroll_offset = 0
        self.max_visible = 5

    def _get_all_saves(self):
        return _list_files_by_pattern(SAVE_DIR, "save_", ".json")

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.input_mode:
                    if event.key == pygame.K_RETURN and self.save_name:
                        self.success_timer = 120
                        return ("save", self.save_name)
                    elif event.key == pygame.K_BACKSPACE:
                        self.save_name = self.save_name[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        return ("cancel", None)
                else:
                    if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                        if self.selected_existing is not None:
                            self.selected_existing, self.scroll_offset = _handle_scrolling_input(
                                event.key, self.selected_existing, self.existing_saves,
                                self.scroll_offset, self.max_visible)
                    elif event.key == pygame.K_RETURN and self.selected_existing is not None:
                        return ("save", self.existing_saves[self.selected_existing])
                    elif event.key == pygame.K_d and self.selected_existing is not None:
                        return ("delete", self.existing_saves[self.selected_existing])
                    elif event.key == pygame.K_ESCAPE:
                        return ("cancel", None)
                    elif event.key == pygame.K_n:
                        self.input_mode = True
                        self.save_name = ""
            elif event.type == pygame.TEXTINPUT:
                if self.input_mode and len(self.save_name) < 30:
                    self.save_name += event.text
        return (None, None)

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        if self.input_mode:
            pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.1), int(offset_y + GAME_HEIGHT * scale * 0.2), int(GAME_WIDTH * scale * 0.8), int(GAME_HEIGHT * scale * 0.6)))
            font_title = pygame.font.Font(None, int(32 * scale))
            font_text = pygame.font.Font(None, int(24 * scale))

            title = font_title.render("Enter Pilot Name:", True, WHITE)
            surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.25)))

            input_box = font_text.render(self.save_name + "|", True, YELLOW)
            surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.4)))

            help_text = font_text.render("Enter to save, ESC to cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.6)))
        else:
            pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.1), int(offset_y + GAME_HEIGHT * scale * 0.15), int(GAME_WIDTH * scale * 0.8), int(GAME_HEIGHT * scale * 0.7)))
            font_title = pygame.font.Font(None, int(32 * scale))
            font_text = pygame.font.Font(None, int(20 * scale))

            title = font_title.render("Select Save to Overwrite", True, YELLOW)
            surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.2)))

            if self.scroll_offset > 0:
                up_indicator = font_text.render("↑ more", True, GRAY)
                surface.blit(up_indicator, (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.33)))

            visible_saves = self.existing_saves[self.scroll_offset:self.scroll_offset + self.max_visible]
            for i, save in enumerate(visible_saves):
                is_selected = (self.scroll_offset + i == self.selected_existing)
                color = YELLOW if is_selected else GRAY
                text = font_text.render(save, True, color)
                text_x = int(offset_x + GAME_WIDTH * scale * 0.15)
                text_y = int(offset_y + GAME_HEIGHT * scale * 0.35 + i * 35)
                surface.blit(text, (text_x, text_y))
                if is_selected:
                    box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                    pygame.draw.rect(surface, YELLOW, box_rect, 2)

            if self.scroll_offset + self.max_visible < len(self.existing_saves):
                down_indicator = font_text.render("↓ more", True, GRAY)
                surface.blit(down_indicator, (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.35 + self.max_visible * 35)))

            help_text = font_text.render("Enter: overwrite, N: new save, D: delete, ESC: cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.75)))

class DeleteConfirmDialog:
    def __init__(self, save_filename):
        self.save_filename = save_filename
        self.confirm_text = ""

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and self.confirm_text.lower() == "confirm":
                    return ("delete", self.save_filename)
                elif event.key == pygame.K_BACKSPACE:
                    self.confirm_text = self.confirm_text[:-1]
                elif event.key == pygame.K_ESCAPE:
                    return ("cancel", None)
            elif event.type == pygame.TEXTINPUT:
                if len(self.confirm_text) < 30:
                    self.confirm_text += event.text
        return (None, None)

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.1), int(offset_y + GAME_HEIGHT * scale * 0.2), int(GAME_WIDTH * scale * 0.8), int(GAME_HEIGHT * scale * 0.6)))
        font_title = pygame.font.Font(None, int(32 * scale))
        font_text = pygame.font.Font(None, int(24 * scale))

        title = font_title.render("Delete Save?", True, WHITE)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.25)))

        filename_text = font_text.render(self.save_filename[:50], True, YELLOW)
        surface.blit(filename_text, (_center_text_x(surface, filename_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.35)))

        confirm_prompt = font_text.render('Type "confirm" to delete:', True, GRAY)
        surface.blit(confirm_prompt, (_center_text_x(surface, confirm_prompt, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.45)))

        input_box = font_text.render(self.confirm_text + "|", True, YELLOW)
        surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.55)))

        help_text = font_text.render("Enter to confirm, ESC to cancel", True, GRAY)
        surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.7)))

class LoadMenu:
    def __init__(self):
        self.saves = get_save_files()
        self.selected = 0
        self.scroll_offset = 0
        self.max_visible = 5

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return ("quit", None)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                    self.selected, self.scroll_offset = _handle_scrolling_input(
                        event.key, self.selected, self.saves, self.scroll_offset, self.max_visible)
                elif event.key == pygame.K_RETURN and self.saves:
                    return ("load", self.saves[self.selected])
                elif event.key == pygame.K_ESCAPE:
                    return ("cancel", None)
        return (None, None)

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.1), int(offset_y + GAME_HEIGHT * scale * 0.2), int(GAME_WIDTH * scale * 0.8), int(GAME_HEIGHT * scale * 0.6)))

        font_title = pygame.font.Font(None, int(40 * scale))
        font_save = pygame.font.Font(None, int(24 * scale))

        title = font_title.render("Load Game", True, YELLOW)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.25)))

        if not self.saves:
            no_saves = font_save.render("No saves found", True, GRAY)
            surface.blit(no_saves, (_center_text_x(surface, no_saves, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.5)))
        else:
            if self.scroll_offset > 0:
                up_indicator = font_save.render("↑ more", True, GRAY)
                surface.blit(up_indicator, (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.33)))

            visible_saves = self.saves[self.scroll_offset:self.scroll_offset + self.max_visible]
            for i, save in enumerate(visible_saves):
                is_selected = (self.scroll_offset + i == self.selected)
                color = YELLOW if is_selected else GRAY
                text = font_save.render(save, True, color)
                text_x = int(offset_x + GAME_WIDTH * scale * 0.15)
                text_y = int(offset_y + GAME_HEIGHT * scale * 0.35 + i * 40)
                surface.blit(text, (text_x, text_y))
                if is_selected:
                    box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                    pygame.draw.rect(surface, YELLOW, box_rect, 2)

            if self.scroll_offset + self.max_visible < len(self.saves):
                down_indicator = font_save.render("↓ more", True, GRAY)
                surface.blit(down_indicator, (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.35 + self.max_visible * 40)))

class PauseMenu:
    def __init__(self):
        self.options = ["Resume", "Save Game", "Quit to Menu"]
        self.selected = 0
        self.success_timer = 0

    def update(self):
        if self.success_timer > 0:
            self.success_timer -= 1

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "resume"
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.selected = (self.selected - 1) % len(self.options)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.selected = (self.selected + 1) % len(self.options)
                elif event.key == pygame.K_RETURN:
                    if self.selected == 0:
                        return "resume"
                    elif self.selected == 1:
                        return "save"
                    elif self.selected == 2:
                        return "quit"
        return None

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (0, 0, 0), (0, 0, screen_width, screen_height))
        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.2), int(offset_y + GAME_HEIGHT * scale * 0.3), int(GAME_WIDTH * scale * 0.6), int(GAME_HEIGHT * scale * 0.4)))

        font_title = pygame.font.Font(None, int(48 * scale))
        font_option = pygame.font.Font(None, int(32 * scale))

        title = font_title.render("PAUSED", True, YELLOW)
        surface.blit(title, (int(offset_x + GAME_WIDTH * scale // 2 - title.get_width() // 2), int(offset_y + GAME_HEIGHT * scale * 0.35)))

        for i, option in enumerate(self.options):
            color = YELLOW if i == self.selected else GRAY
            text = font_option.render(option, True, color)
            text_x = int(offset_x + GAME_WIDTH * scale // 2 - text.get_width() // 2)
            text_y = int(offset_y + GAME_HEIGHT * scale * 0.5 + i * 50)
            surface.blit(text, (text_x, text_y))
            if i == self.selected:
                box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                pygame.draw.rect(surface, YELLOW, box_rect, 2)

        if self.success_timer > 0:
            font_success = pygame.font.Font(None, int(32 * scale))
            success_text = font_success.render("Saved!", True, (0, 255, 0))
            surface.blit(success_text, (int(offset_x + GAME_WIDTH * scale * 0.5 - success_text.get_width() // 2), int(offset_y + GAME_HEIGHT * scale * 0.15)))

class Ship:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 0
        self.velocity_x = 0
        self.velocity_y = 0
        self.thrust = 0
        self.max_thrust = 0.3
        self.max_velocity = 4.0
        self.drag = 0.98
        self.rotation_speed = 5

    def draw_ship(self, surface, ship_size=15, color=DARK_GRAY):
        scale = get_scale()
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
            points.append(to_screen(self.x + rotated_x, self.y + rotated_y))

        pygame.draw.polygon(surface, color, points)

        if self.thrust > 0.05:
            flame_length = self.thrust * 30
            mid_back_x = (local_points[1][0] + local_points[2][0]) / 2
            mid_back_y = (local_points[1][1] + local_points[2][1]) / 2
            back_x = self.x + (mid_back_x * cos_a - mid_back_y * sin_a)
            back_y = self.y + (mid_back_x * sin_a + mid_back_y * cos_a)
            flame_x = back_x - sin_a * flame_length
            flame_y = back_y + cos_a * flame_length
            pygame.draw.line(surface, YELLOW, to_screen(back_x, back_y), to_screen(flame_x, flame_y), max(1, int(2 * scale)))

    def wrap_position(self):
        if self.x < 0:
            self.x = GAME_WIDTH
        elif self.x > GAME_WIDTH:
            self.x = 0
        if self.y < 0:
            self.y = GAME_HEIGHT
        elif self.y > GAME_HEIGHT:
            self.y = 0

class Player(Ship):
    def __init__(self, x, y):
        super().__init__(x, y)

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

        self.wrap_position()

    def draw(self, surface):
        self.draw_ship(surface, ship_size=15, color=DARK_GRAY)

class AIShip(Ship):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.angle = random.randint(0, 360)
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

        self.wrap_position()

    def draw(self, surface):
        self.draw_ship(surface, ship_size=12, color=(150, 150, 200))

class SpaceStation:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rotation = 0

    def update(self):
        self.rotation = (self.rotation + 0.5) % 360

    def draw(self, surface):
        scale = get_scale()
        size = 40
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
            points.append(to_screen(self.x + rotated_x, self.y + rotated_y))

        pygame.draw.polygon(surface, (100, 200, 255), points)
        pygame.draw.circle(surface, (150, 220, 255), to_screen(self.x, self.y), max(1, int(round(size * 0.25 * scale))))

    def get_distance(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

class Person:
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
    def __init__(self, x, y, behavior="wander", name="NPC", greeting="Hello!", dialogue_options=None):
        super().__init__(x, y)
        self.behavior = behavior
        self.name = name
        self.greeting = greeting
        self.dialogue_options = dialogue_options or ["Talk", "Leave"]
        self.dialogue = Dialogue(name, [greeting], self.dialogue_options)

class WalkableArea:
    """Base class for all walkable/explorable areas with camera system"""
    def __init__(self, start_x=GAME_WIDTH // 2, start_y=GAME_HEIGHT // 2, world_width=1600, world_height=1600):
        self.player_x = start_x
        self.player_y = start_y
        self.world_width = world_width
        self.world_height = world_height
        self.pilot_name = ""
        self.speed = 3

    def handle_input(self, events):
        """Override for area-specific input (dialogue, etc.)"""
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_l:
                    return "exit"
                elif event.key == pygame.K_ESCAPE:
                    return "pause"
        return None

    def _handle_movement(self, keys, can_move_func=None):
        """Generalized movement input handling"""
        new_x = self.player_x
        new_y = self.player_y

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_y += self.speed
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            new_x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            new_x += self.speed

        # Check bounds
        if can_move_func:
            can_move = can_move_func(new_x, new_y)
        else:
            can_move = (0 < new_x < self.world_width and 0 < new_y < self.world_height)

        if can_move:
            self.player_x = new_x
            self.player_y = new_y

    def update_camera(self):
        """Update global camera to follow player"""
        global camera_offset_x, camera_offset_y
        camera_offset_x = self.player_x - GAME_WIDTH // 2
        camera_offset_y = self.player_y - GAME_HEIGHT // 2

    def draw_ui_text(self, surface, text, scale=None):
        """Draw UI text that stays on screen (not camera-affected)"""
        if scale is None:
            scale = get_scale()
        offset_x, offset_y = get_offset()
        font = pygame.font.Font(None, int(24 * scale))
        ui_text = font.render(text, True, WHITE)
        surface.blit(ui_text, (int(offset_x + 20), int(offset_y + 20)))

    def update(self):
        """Override in subclass"""
        pass

    def draw(self, surface):
        """Override in subclass"""
        pass

class StationInterior(WalkableArea):
    def __init__(self, station_config=None, pilot_name=""):
        super().__init__(start_x=GAME_WIDTH // 2, start_y=GAME_HEIGHT - 80, world_width=GAME_WIDTH, world_height=GAME_HEIGHT)
        self.pilot_name = pilot_name
        self.room_width = GAME_WIDTH
        self.room_height = GAME_HEIGHT

        self.station_config = station_config or load_json("config/station_interior.json") or {}

        hallway_cfg = self.station_config.get("hallway", {})
        self.hallway_narrow_width = hallway_cfg.get("narrow_width", 80)
        self.hallway_wide_width = hallway_cfg.get("wide_width", 200)
        self.hallway_x = GAME_WIDTH // 2 - self.hallway_narrow_width // 2
        self.hallway_transition_y = int(GAME_HEIGHT * hallway_cfg.get("transition_y", 0.5))

        bar_cfg = self.station_config.get("bar", {})
        self.bar_x = int(GAME_WIDTH * bar_cfg.get("x", 0.5))
        self.bar_y = int(GAME_HEIGHT * bar_cfg.get("y", 0.15))

        door_cfg = self.station_config.get("door", {})
        self.door_x = int(GAME_WIDTH * door_cfg.get("x", 0.5))
        self.door_y = int(GAME_HEIGHT * door_cfg.get("y", 0.9))

        npcs_cfg = self.station_config.get("npcs", [])
        npc0 = npcs_cfg[0] if len(npcs_cfg) > 0 else {}
        npc1 = npcs_cfg[1] if len(npcs_cfg) > 1 else {}
        npc2 = npcs_cfg[2] if len(npcs_cfg) > 2 else {}

        self.bartender = NPC(self.bar_x, self.bar_y, "bar", npc0.get("name", "Bartender"), npc0.get("greeting", "What'll it be?"), npc0.get("dialogue_options", ["Talk", "Leave"]))
        self.wanderer = NPC(self.room_width // 2, self.hallway_transition_y - 100, "wander", npc1.get("name", "Traveler"), npc1.get("greeting", "Safe travels!"), npc1.get("dialogue_options", ["Thanks", "Leave"]))
        self.door_guard = NPC(self.door_x, self.door_y, "bar", npc2.get("name", "Guard"), npc2.get("greeting", "Welcome to the station."), npc2.get("dialogue_options", ["Thanks", "Leave"]))

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
                        return "pause"
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
            hallway_wide_x = GAME_WIDTH // 2 - self.hallway_wide_width // 2
            return (x >= hallway_wide_x + 10 and x <= hallway_wide_x + self.hallway_wide_width - 10 and y >= 30)

    def _is_in_valid_area(self, x, y):
        if self._is_in_hallway(x, y):
            return True
        bar_left = self.bar_x - 100
        bar_right = self.bar_x + 100
        bar_top = 50
        bar_bottom = self.hallway_transition_y - 50
        return (x >= bar_left and x <= bar_right and y >= bar_top and y <= bar_bottom)

    def update(self):
        if self.current_dialogue:
            return

        keys = pygame.key.get_pressed()
        self._handle_movement(keys, self._is_in_valid_area)
        self.player_y = max(30, min(self.room_height - 30, self.player_y))
        self.update_camera()

        self.wanderer.wander_time -= 1
        if self.wanderer.wander_time <= 0:
            self.wanderer.wander_x = (random.random() - 0.5) * 2
            self.wanderer.wander_y = (random.random() - 0.5) * 2
            self.wanderer.wander_time = random.randint(60, 180)

        new_wander_x = self.wanderer.x + self.wanderer.wander_x
        new_wander_y = self.wanderer.y + self.wanderer.wander_y

        if self._is_in_valid_area(new_wander_x, new_wander_y):
            self.wanderer.x = new_wander_x
            self.wanderer.y = new_wander_y

        self.nearby_npc = None
        for npc in [self.bartender, self.wanderer, self.door_guard]:
            if npc.get_distance(self.player_x, self.player_y) < 50:
                self.nearby_npc = npc
                break

    def draw(self, surface):
        surface.fill((30, 30, 50))

        scale = get_scale()
        hallway_wide_x = GAME_WIDTH // 2 - self.hallway_wide_width // 2
        hallway_wide_width = self.hallway_wide_width

        pygame.draw.rect(surface, (50, 50, 70), (*to_screen(hallway_wide_x, 0), to_screen_x(hallway_wide_width), to_screen_y(self.hallway_transition_y)))
        pygame.draw.rect(surface, (50, 50, 70), (*to_screen(self.hallway_x, self.hallway_transition_y), to_screen_x(self.hallway_narrow_width), to_screen_y(self.room_height - self.hallway_transition_y)))

        pygame.draw.rect(surface, (60, 60, 80), (*to_screen(0, 0), to_screen_x(self.room_width), to_screen_y(self.room_height)), 3)

        pygame.draw.line(surface, (80, 80, 100), to_screen(hallway_wide_x, 0), to_screen(self.hallway_x, self.hallway_transition_y), 2)
        pygame.draw.line(surface, (80, 80, 100), to_screen(hallway_wide_x + hallway_wide_width, 0), to_screen(self.hallway_x + self.hallway_narrow_width, self.hallway_transition_y), 2)

        pygame.draw.rect(surface, (100, 80, 40), (*to_screen(self.bar_x - 60, self.bar_y - 20), to_screen_x(120), to_screen_y(40)))
        font = pygame.font.Font(None, int(20 * scale))
        bar_text = font.render("BAR", True, (200, 200, 100))
        surface.blit(bar_text, to_screen(self.bar_x - 20, self.bar_y - 10))

        self.bartender.draw(surface)
        self.wanderer.draw(surface)
        self.door_guard.draw(surface)

        pygame.draw.rect(surface, (0, 255, 0), (*to_screen(self.player_x - 6, self.player_y), to_screen_x(12), to_screen_y(16)))
        pygame.draw.circle(surface, (100, 255, 100), to_screen(self.player_x, self.player_y - 10), max(1, int(5 * scale)))

        offset_x, offset_y = get_offset()
        font_small = pygame.font.Font(None, int(16 * scale))
        help_text = font_small.render("WASD/Arrows to move, L to exit, ESC for menu", True, (200, 200, 200))
        surface.blit(help_text, (int(offset_x + 10), int(offset_y + 10)))

        if self.nearby_npc and not self.current_dialogue:
            talk_text = font_small.render("Press T to talk", True, (255, 255, 0))
            surface.blit(talk_text, to_screen(self.nearby_npc.x - 30, self.nearby_npc.y - 30))

        if self.current_dialogue:
            self.current_dialogue.draw(surface, scale)

        offset_x, offset_y = get_offset()
        border_rect = (int(offset_x), int(offset_y), int(GAME_WIDTH * scale), int(GAME_HEIGHT * scale))
        pygame.draw.rect(surface, (100, 100, 100), border_rect, 2)

class StarField:
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

class MoonCity(WalkableArea):
    def __init__(self, config=None, pilot_name=""):
        super().__init__(start_x=GAME_WIDTH // 2, start_y=GAME_HEIGHT - 80, world_width=1600, world_height=1600)
        self.pilot_name = pilot_name
        self.city_config = config or load_json("config/moon_city.json") or {}
        self.buildings = self.city_config.get("buildings", [])
        self.windows = self.city_config.get("windows", [])

    def update(self):
        keys = pygame.key.get_pressed()
        self._handle_movement(keys)
        self.update_camera()

    def draw(self, surface):
        surface.fill((50, 50, 70))

        # Draw buildings from config
        for building in self.buildings:
            bx, by, bw, bh = building["x"], building["y"], building["width"], building["height"]
            color = tuple(building.get("color", [150, 150, 150]))
            x1, y1 = to_screen(bx, by)
            x2, y2 = to_screen(bx + bw, by + bh)
            pygame.draw.rect(surface, color, (x1, y1, x2 - x1, y2 - y1))

        # Draw windows from config
        for window in self.windows:
            sx, sy, ex, ey, spacing = window["start_x"], window["start_y"], window["end_x"], window["end_y"], window["spacing"]
            for bx in range(sx, ex, spacing):
                for by in range(sy, ey, spacing):
                    x, y = to_screen(bx, by)
                    pygame.draw.rect(surface, YELLOW, (x, y, 15, 15))

        # Draw player
        px, py = to_screen(self.player_x, self.player_y)
        pygame.draw.rect(surface, (200, 100, 100), (px - 6, py, 12, 16))
        pygame.draw.circle(surface, (255, 150, 150), (px, py - 10), 5)

        # Draw UI
        self.draw_ui_text(surface, "Moon City | Press L to leave")

class MoonOutdoor(WalkableArea):
    def __init__(self, config=None, pilot_name=""):
        super().__init__(start_x=GAME_WIDTH // 2, start_y=GAME_HEIGHT - 80, world_width=1600, world_height=1600)
        self.pilot_name = pilot_name
        self.wilderness_config = config or load_json("config/moon_wilderness.json") or {}
        self.craters = self.wilderness_config.get("craters", [])
        self.rocks = self.wilderness_config.get("rocks", [])

    def update(self):
        keys = pygame.key.get_pressed()
        self._handle_movement(keys)
        self.update_camera()

    def draw(self, surface):
        # Draw moon terrain
        surface.fill((80, 80, 100))

        scale = get_scale()

        # Draw craters from config
        for crater in self.craters:
            cx, cy, r = crater["x"], crater["y"], crater.get("radius", 50)
            crater_x, crater_y = to_screen(cx, cy)
            pygame.draw.circle(surface, (60, 60, 80), (crater_x, crater_y), max(1, int(r * scale)))
            pygame.draw.circle(surface, (70, 70, 90), (crater_x, crater_y), max(1, int((r - 5) * scale)))

        # Draw rocks from config
        for rock in self.rocks:
            rx, ry = rock["x"], rock["y"]
            rock_x, rock_y = to_screen(rx, ry)
            size = int(30 * scale)
            pygame.draw.polygon(surface, (120, 120, 140), [(rock_x, rock_y), (rock_x + size, rock_y + size//2), (rock_x + size - 10, rock_y + size + 5), (rock_x - 10, rock_y + size)])

        # Draw player
        px, py = to_screen(self.player_x, self.player_y)
        pygame.draw.rect(surface, (200, 100, 100), (px - 6, py, 12, 16))
        pygame.draw.circle(surface, (255, 150, 150), (px, py - 10), 5)

        # Draw UI
        self.draw_ui_text(surface, "Moon Wilderness | Press L to leave")

class Moon:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.phase = 0

    def update(self):
        self.phase = (self.phase + 0.1) % 360

    def draw(self, surface):
        scale = get_scale()
        size = 30
        color = (200, 200, 200)
        pygame.draw.circle(surface, color, to_screen(self.x, self.y), max(1, int(round(size * scale))))
        # Draw craters
        pygame.draw.circle(surface, (150, 150, 150), to_screen(self.x - 8, self.y - 5), max(1, int(4 * scale)))
        pygame.draw.circle(surface, (150, 150, 150), to_screen(self.x + 10, self.y + 8), max(1, int(5 * scale)))

    def get_distance(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

class PilotNameDialog:
    def __init__(self):
        self.pilot_name = ""

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and self.pilot_name:
                    return self.pilot_name
                elif event.key == pygame.K_BACKSPACE:
                    self.pilot_name = self.pilot_name[:-1]
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
            elif event.type == pygame.TEXTINPUT:
                if len(self.pilot_name) < 30:
                    self.pilot_name += event.text
        return None

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.25), int(GAME_WIDTH * scale * 0.7), int(GAME_HEIGHT * scale * 0.5)))

        font_title = pygame.font.Font(None, int(40 * scale))
        font_text = pygame.font.Font(None, int(28 * scale))

        title = font_title.render("New Game", True, YELLOW)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.3)))

        prompt = font_text.render("Enter Pilot Name:", True, WHITE)
        surface.blit(prompt, (_center_text_x(surface, prompt, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.4)))

        input_box = font_text.render(self.pilot_name + "|", True, YELLOW)
        surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.5)))

        help_text = font_text.render("Enter to start, ESC to cancel", True, GRAY)
        surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.65)))

class LocationSelector:
    def __init__(self):
        self.locations = ["Moon City", "Wilderness"]
        self.selected = 0

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.selected = (self.selected - 1) % len(self.locations)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.selected = (self.selected + 1) % len(self.locations)
                elif event.key == pygame.K_RETURN:
                    return self.locations[self.selected]
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
        return None

    def draw(self, surface):
        scale = get_scale()
        offset_x, offset_y = get_offset()

        pygame.draw.rect(surface, (40, 40, 60), (int(offset_x + GAME_WIDTH * scale * 0.15), int(offset_y + GAME_HEIGHT * scale * 0.25), int(GAME_WIDTH * scale * 0.7), int(GAME_HEIGHT * scale * 0.5)))

        font_title = pygame.font.Font(None, int(40 * scale))
        font_text = pygame.font.Font(None, int(28 * scale))

        title = font_title.render("Landing Location", True, YELLOW)
        surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + GAME_HEIGHT * scale * 0.3)))

        for i, location in enumerate(self.locations):
            color = YELLOW if i == self.selected else GRAY
            text = font_text.render(location, True, color)
            text_x = int(offset_x + GAME_WIDTH * scale * 0.3)
            text_y = int(offset_y + GAME_HEIGHT * scale * 0.45 + i * 40)
            surface.blit(text, (text_x, text_y))
            if i == self.selected:
                box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                pygame.draw.rect(surface, YELLOW, box_rect, 2)

class GameScreen:
    def __init__(self, system_config=None, pilot_name=""):
        self.player = Player(GAME_WIDTH // 2, GAME_HEIGHT // 2)
        self.star_field = StarField()
        self.system_config = system_config or load_json("config/space_system.json") or {}
        self.pilot_name = pilot_name

        station_cfg = self.system_config.get("station", {})
        self.station = SpaceStation(GAME_WIDTH * station_cfg.get("x", 0.75), GAME_HEIGHT * station_cfg.get("y", 0.3))

        moon_cfg = self.system_config.get("moon", {})
        self.moon = Moon(GAME_WIDTH * moon_cfg.get("x", 0.2), GAME_HEIGHT * moon_cfg.get("y", 0.4))

        ai_cfg = self.system_config.get("ai_ships", [{}])[0]
        self.ai_ship = AIShip(GAME_WIDTH * ai_cfg.get("x", 0.75), GAME_HEIGHT * ai_cfg.get("y", 0.1))
        self.landing_text = 0
        self.landing_target = None
        self.camera_x = 0
        self.camera_y = 0

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "pause"
                elif event.key == pygame.K_l:
                    landing_target = self._check_landing()
                    if landing_target:
                        self.landing_target = landing_target
                        return "land"
        return None

    def _update_positions(self):
        self.station.x = screen_width * 0.75
        self.station.y = screen_height * 0.3
        self.ai_ship.x = screen_width * 0.75
        self.ai_ship.y = screen_height * 0.3 - 150

    def _check_landing(self):
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)

        station_distance = self.station.get_distance(self.player.x, self.player.y)
        if station_distance < 100 and speed < 0.5:
            return "station"

        moon_distance = self.moon.get_distance(self.player.x, self.player.y)
        if moon_distance < 100 and speed < 0.5:
            return "moon"

        return None

    def _can_land_at_station(self):
        distance = self.station.get_distance(self.player.x, self.player.y)
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
        return distance < 100 and speed < 0.5

    def _to_screen_camera(self, x, y):
        """Convert world coordinates to screen coordinates using camera offset"""
        world_x = x - self.camera_x
        world_y = y - self.camera_y
        return to_screen(world_x, world_y)

    def update(self):
        global camera_offset_x, camera_offset_y

        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        self.player.update()
        self.station.update()
        self.moon.update()
        self.ai_ship.update()

        # Update camera to follow player
        camera_offset_x = self.player.x - GAME_WIDTH // 2
        camera_offset_y = self.player.y - GAME_HEIGHT // 2

        if self._check_landing():
            self.landing_text = 60
        else:
            self.landing_text = max(0, self.landing_text - 1)

    def draw(self, surface):
        surface.fill(BLACK)
        self.star_field.draw(surface)
        self.station.draw(surface)
        self.moon.draw(surface)
        self.ai_ship.draw(surface)
        self.player.draw(surface)

        if self.landing_text > 0:
            scale = get_scale()
            font = pygame.font.Font(None, int(24 * scale))
            land_text = font.render("Press L to land", True, YELLOW)
            offset_x, offset_y = get_offset()
            land_x = int(offset_x + GAME_WIDTH * scale // 2 - land_text.get_width() // 2)
            land_y = int(offset_y + GAME_HEIGHT * scale - 60)
            surface.blit(land_text, (land_x, land_y))

        scale = get_scale()
        offset_x, offset_y = get_offset()
        border_rect = (int(offset_x), int(offset_y), int(GAME_WIDTH * scale), int(GAME_HEIGHT * scale))
        pygame.draw.rect(surface, (100, 100, 100), border_rect, 2)

    def get_state(self):
        return {
            "player": {
                "x": self.player.x,
                "y": self.player.y,
                "angle": self.player.angle,
                "velocity_x": self.player.velocity_x,
                "velocity_y": self.player.velocity_y,
                "thrust": self.player.thrust
            },
            "ai_ship": {
                "x": self.ai_ship.x,
                "y": self.ai_ship.y,
                "angle": self.ai_ship.angle,
                "velocity_x": self.ai_ship.velocity_x,
                "velocity_y": self.ai_ship.velocity_y,
                "thrust": self.ai_ship.thrust
            }
        }

    def restore_state(self, state):
        if not state:
            return
        if "player" in state:
            player_state = state["player"]
            self.player.x = player_state.get("x", self.player.x)
            self.player.y = player_state.get("y", self.player.y)
            self.player.angle = player_state.get("angle", self.player.angle)
            self.player.velocity_x = player_state.get("velocity_x", self.player.velocity_x)
            self.player.velocity_y = player_state.get("velocity_y", self.player.velocity_y)
            self.player.thrust = player_state.get("thrust", self.player.thrust)
        if "ai_ship" in state:
            ai_state = state["ai_ship"]
            self.ai_ship.x = ai_state.get("x", self.ai_ship.x)
            self.ai_ship.y = ai_state.get("y", self.ai_ship.y)
            self.ai_ship.angle = ai_state.get("angle", self.ai_ship.angle)
            self.ai_ship.velocity_x = ai_state.get("velocity_x", self.ai_ship.velocity_x)
            self.ai_ship.velocity_y = ai_state.get("velocity_y", self.ai_ship.velocity_y)
            self.ai_ship.thrust = ai_state.get("thrust", self.ai_ship.thrust)

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
            text_x = int(screen_width // 2 + 80 * scale)
            surface.blit(text, (text_x, y))

            if i == self.selected_index:
                box_rect = pygame.Rect(text_x - 5, y - 2, text.get_width() + 10, text.get_height() + 4)
                pygame.draw.rect(surface, YELLOW, box_rect, 2)
                dot_radius = int(12 * scale)
                dot_x = int(screen_width // 2 + 40 * scale)
                pygame.draw.circle(surface, YELLOW, (dot_x, y + text.get_height() // 2), dot_radius)

def main():
    global screen_width, screen_height, screen
    try:
        menu = Menu()
        game_screen = None
        station_interior = None
        moon_interior = None
        location_selector = None
        pilot_name_dialog = None
        pause_menu = PauseMenu()
        save_dialog = None
        delete_confirm_dialog = None
        load_menu = None
        current_screen = "menu"
        previous_screen = None
        running = True
        pilot_name = ""

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
                    pilot_name_dialog = PilotNameDialog()
                    current_screen = "pilot_name"
                elif selection == "load":
                    load_menu = LoadMenu()
                    current_screen = "load"
                menu.draw(screen)

            elif current_screen == "pilot_name":
                result = pilot_name_dialog.handle_input(events)
                if result and result != "cancel":
                    pilot_name = result
                    game_screen = GameScreen(pilot_name=pilot_name)
                    current_screen = "game"
                elif result == "cancel":
                    current_screen = "menu"
                pilot_name_dialog.draw(screen)

            elif current_screen == "load":
                action, filename = load_menu.handle_input(events)
                if action == "load":
                    save_data = load_save_file(filename)
                    if save_data:
                        pilot_name = save_data.get("pilot_name", "")
                        game_state = save_data.get("game_state", {})
                        location = game_state.get("location", "space")

                        if location == "space":
                            game_screen = GameScreen(save_data.get("system", {}), pilot_name=pilot_name)
                            game_screen.restore_state(game_state)
                            current_screen = "game"
                        elif location == "station":
                            game_screen = GameScreen(save_data.get("system", {}), pilot_name=pilot_name)
                            game_screen.restore_state(game_state)
                            station_interior = StationInterior(pilot_name=pilot_name)
                            current_screen = "station"
                        elif location == "moon":
                            game_screen = GameScreen(save_data.get("system", {}), pilot_name=pilot_name)
                            game_screen.restore_state(game_state)
                            moon_location = game_state.get("moon_location", "city")
                            if moon_location == "city":
                                moon_interior = MoonCity(pilot_name=pilot_name)
                            else:
                                moon_interior = MoonOutdoor(pilot_name=pilot_name)
                            current_screen = "moon"
                elif action == "cancel":
                    current_screen = "menu"
                    menu = Menu()
                load_menu.draw(screen)

            elif current_screen == "game":
                action = game_screen.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "pause":
                    previous_screen = "game"
                    current_screen = "pause"
                elif action == "land":
                    if game_screen.landing_target == "station":
                        station_interior = StationInterior(pilot_name=pilot_name)
                        current_screen = "station"
                    elif game_screen.landing_target == "moon":
                        location_selector = LocationSelector()
                        current_screen = "select_location"
                game_screen.update()
                game_screen.draw(screen)

            elif current_screen == "station":
                action = station_interior.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "pause":
                    previous_screen = "station"
                    current_screen = "pause"
                elif action == "exit":
                    current_screen = "game"
                if station_interior:
                    station_interior.update()
                    station_interior.draw(screen)

            elif current_screen == "select_location":
                location = location_selector.handle_input(events)
                if location == "Moon City":
                    moon_interior = MoonCity(pilot_name=pilot_name)
                    current_screen = "moon"
                elif location == "Wilderness":
                    moon_interior = MoonOutdoor(pilot_name=pilot_name)
                    current_screen = "moon"
                elif location == "cancel":
                    current_screen = "game"
                location_selector.draw(screen)

            elif current_screen == "moon":
                action = moon_interior.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "exit":
                    current_screen = "game"
                elif action == "pause":
                    previous_screen = "moon"
                    current_screen = "pause"
                if moon_interior:
                    moon_interior.update()
                    moon_interior.draw(screen)

            elif current_screen == "pause":
                pause_menu.update()

                if delete_confirm_dialog:
                    dialog_action, filename = delete_confirm_dialog.handle_input(events)
                    if dialog_action == "delete":
                        try:
                            filepath = f"{SAVE_DIR}/{filename}"
                            if os.path.exists(filepath):
                                os.remove(filepath)
                            pause_menu.success_timer = 120
                        except:
                            pass
                        delete_confirm_dialog = None
                        if save_dialog:
                            save_dialog.existing_saves = save_dialog._get_all_saves()
                    elif dialog_action == "cancel":
                        delete_confirm_dialog = None

                elif save_dialog:
                    dialog_action, save_name = save_dialog.handle_input(events)
                    if dialog_action == "save":
                        # Check if we're overwriting an existing save
                        is_overwriting = save_name in save_dialog.existing_saves
                        if is_overwriting:
                            # Delete the old save file
                            try:
                                filepath = f"{SAVE_DIR}/{save_name}"
                                if os.path.exists(filepath):
                                    os.remove(filepath)
                            except:
                                pass

                        if not pilot_name and save_name and not is_overwriting:
                            pilot_name = save_name
                            if game_screen:
                                game_screen.pilot_name = pilot_name
                            if station_interior:
                                station_interior.pilot_name = pilot_name

                        # Extract description from save_name (before the timestamp)
                        save_description = save_name.split(" - ")[0] if " - " in save_name else save_name

                        # Add location state for restoration
                        game_state = {}
                        if game_screen:
                            game_state = game_screen.get_state()
                            game_state["location"] = "space"
                        elif station_interior:
                            game_state["location"] = "station"
                        elif moon_interior:
                            game_state["location"] = "moon"
                            if isinstance(moon_interior, MoonCity):
                                game_state["moon_location"] = "city"
                            else:
                                game_state["moon_location"] = "wilderness"

                        if game_screen:
                            create_save_file(pilot_name, save_description, game_screen.system_config, {}, game_state)
                        elif station_interior:
                            create_save_file(pilot_name, save_description, station_interior.station_config, {}, game_state)
                        elif moon_interior:
                            create_save_file(pilot_name, save_description, {}, {}, game_state)
                        pause_menu.success_timer = 120
                        save_dialog = None
                    elif dialog_action == "delete":
                        delete_confirm_dialog = DeleteConfirmDialog(save_name)
                    elif dialog_action == "cancel":
                        save_dialog = None

                if not save_dialog and not delete_confirm_dialog:
                    action = pause_menu.handle_input(events)
                    if action == "resume":
                        current_screen = previous_screen
                    elif action == "save":
                        save_dialog = SaveDialog(pilot_name=pilot_name)
                    elif action == "quit":
                        current_screen = "menu"
                        menu = Menu()

                if previous_screen == "game" and game_screen:
                    game_screen.draw(screen)
                elif previous_screen == "station" and station_interior:
                    station_interior.draw(screen)

                pause_menu.draw(screen)

                if delete_confirm_dialog:
                    delete_confirm_dialog.draw(screen)
                elif save_dialog:
                    save_dialog.draw(screen)

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
