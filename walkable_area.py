"""Base class for all walkable/explorable areas with camera system."""
import pygame
import math
from constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from utils import get_scale, get_ui_scale, get_ui_offset, set_camera_offset
from screen_base import ScreenBase


class WalkableArea(ScreenBase):
    """Base class for all walkable/explorable areas with camera system"""
    def __init__(self, start_x=GAME_WIDTH // 2, start_y=GAME_HEIGHT // 2, world_width=1600, world_height=1600, pilot_name=""):
        super().__init__(pilot_name=pilot_name)
        self.player_x = start_x
        self.player_y = start_y
        self.world_width = world_width
        self.world_height = world_height
        self.speed = 3
        self.entrance_x = start_x  # Where player enters
        self.entrance_y = start_y
        self.entrance_range = 50  # How close to entrance to exit

    def handle_input(self, events):
        """Override for area-specific input (dialogue, etc.)"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_l:
                    # Only allow exit if near entrance
                    dist_to_entrance = math.sqrt((self.player_x - self.entrance_x) ** 2 + (self.player_y - self.entrance_y) ** 2)
                    if dist_to_entrance <= self.entrance_range:
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
        set_camera_offset(self.player_x - GAME_WIDTH // 2, self.player_y - GAME_HEIGHT // 2)

    def draw_ui_text(self, surface, text, scale=None):
        """Draw UI text that stays on screen (not camera-affected)"""
        if scale is None:
            scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()
        font = pygame.font.Font(None, int(24 * scale))
        ui_text = font.render(text, True, WHITE)
        surface.blit(ui_text, (int(offset_x + 20), int(offset_y + 20)))

    def update(self):
        """Override in subclass"""
        pass

    def draw(self, surface):
        """Override in subclass"""
        pass

    def get_state(self):
        """Save player position state for walkable areas"""
        return {
            "player": {
                "x": self.player_x,
                "y": self.player_y
            }
        }

    def restore_state(self, state):
        """Restore player position state for walkable areas"""
        if not state or "player" not in state:
            return
        player_state = state["player"]
        self.player_x = player_state.get("x", self.player_x)
        self.player_y = player_state.get("y", self.player_y)
