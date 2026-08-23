"""Interior of a space station with NPCs and dialogue."""
import pygame
import math
import random
import constants
from constants import GAME_WIDTH, GAME_HEIGHT, WHITE, GREEN
from utils import (
    get_scale, get_offset, load_json, draw_debug_marker, draw_target_brackets,
    to_screen, to_screen_x, to_screen_y
)
from location import Location
from npc import NPC


class StationInterior(Location):
    """Interior of a space station with NPCs and dialogue. Loads from config/station_interior.json."""
    def __init__(self, station_config=None, pilot_name=""):
        # Load config from story directory
        config_file = "config/stories/default/station_interior.json"
        self.station_config = station_config or load_json(config_file) or {}

        super().__init__(config_file=config_file, world_width=GAME_WIDTH, world_height=GAME_HEIGHT, pilot_name=pilot_name)

        self.room_width = GAME_WIDTH
        self.room_height = GAME_HEIGHT

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

        # Load entrance from config
        entrance_cfg = self.station_config.get("entrance", {})
        self.entrance_x = int(GAME_WIDTH * entrance_cfg.get("x", 0.5))
        self.entrance_y = int(GAME_HEIGHT * entrance_cfg.get("y", 0.85))
        self.player_x = self.entrance_x
        self.player_y = self.entrance_y

        self.bartender = NPC(self.bar_x, self.bar_y, "bar", npc0.get("name", "Bartender"), npc0.get("greeting", "What'll it be?"), npc0.get("dialogue_options", ["Talk", "Leave"]))
        self.wanderer = NPC(self.room_width // 2, self.hallway_transition_y - 100, "wander", npc1.get("name", "Traveler"), npc1.get("greeting", "Safe travels!"), npc1.get("dialogue_options", ["Thanks", "Leave"]))
        self.door_guard = NPC(self.door_x, self.door_y, "bar", npc2.get("name", "Guard"), npc2.get("greeting", "Welcome to the station."), npc2.get("dialogue_options", ["Thanks", "Leave"]))

        self.npcs = [
            (self.bartender.name, self.bartender),
            (self.wanderer.name, self.wanderer),
            (self.door_guard.name, self.door_guard),
        ]

        self.current_dialogue = None
        self.nearby_npc = None
        self.current_target = None  # For T key targeting

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
                    # Only allow exit if near entrance
                    dist_to_entrance = math.sqrt((self.player_x - self.entrance_x) ** 2 + (self.player_y - self.entrance_y) ** 2)
                    if dist_to_entrance <= self.entrance_range:
                        return "exit"
                elif event.key == pygame.K_t:
                    self._cycle_target()
                elif event.key == pygame.K_RETURN:
                    if self.current_target is not None:
                        self.current_dialogue = self.npcs[self.current_target][1].dialogue
                    elif self.nearby_npc and not self.current_dialogue:
                        self.current_dialogue = self.nearby_npc.dialogue
                    elif self.current_dialogue:
                        self.current_dialogue = None
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

    def _cycle_target(self):
        """Cycle through targetable NPCs"""
        if not self.npcs:
            return
        if self.current_target is None:
            self.current_target = 0
        else:
            self.current_target = (self.current_target + 1) % len(self.npcs)

    def _get_target_npc(self):
        """Get the currently targeted NPC"""
        if self.current_target is None or self.current_target >= len(self.npcs):
            return None
        return self.npcs[self.current_target][1]

    def _handle_dialogue_click(self, mouse_pos):
        scale = get_scale()
        screen_w = pygame.display.get_surface().get_width()
        screen_h = pygame.display.get_surface().get_height()
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

        # Debug marker for player position
        if constants.DEBUG_MODE:
            draw_debug_marker(surface, self.player_x, self.player_y, 10)
            draw_debug_marker(surface, self.bartender.x, self.bartender.y, 8)
            draw_debug_marker(surface, self.wanderer.x, self.wanderer.y, 8)
            draw_debug_marker(surface, self.door_guard.x, self.door_guard.y, 8)

        # Draw target brackets and label
        target_npc = self._get_target_npc()
        if target_npc:
            draw_target_brackets(surface, target_npc.x, target_npc.y)
            offset_x, offset_y = get_offset()
            font_target = pygame.font.Font(None, int(16 * scale))
            target_text = font_target.render(f"Target: {target_npc.name}", True, GREEN)
            surface.blit(target_text, (int(offset_x + 10), int(offset_y + 30)))

        offset_x, offset_y = get_offset()
        font_small = pygame.font.Font(None, int(16 * scale))
        help_text = font_small.render("WASD/Arrows to move, T to target, Enter to talk, L to exit, ESC for menu", True, (200, 200, 200))
        surface.blit(help_text, (int(offset_x + 10), int(offset_y + 10)))

        if self.nearby_npc and not self.current_dialogue:
            talk_text = font_small.render("Press T to talk", True, (255, 255, 0))
            surface.blit(talk_text, to_screen(self.nearby_npc.x - 30, self.nearby_npc.y - 30))

        if self.current_dialogue:
            self.current_dialogue.draw(surface, scale)

        offset_x, offset_y = get_offset()
        border_rect = (int(offset_x), int(offset_y), int(GAME_WIDTH * scale), int(GAME_HEIGHT * scale))
        pygame.draw.rect(surface, (100, 100, 100), border_rect, 2)
