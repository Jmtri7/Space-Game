"""Dialogue system for NPC interaction."""
import pygame


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
