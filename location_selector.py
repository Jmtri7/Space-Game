"""Dialog for selecting moon landing location."""
import pygame
from constants import GAME_WIDTH, GAME_HEIGHT, YELLOW, GRAY
from utils import get_scale, get_offset, _center_text_x


class LocationSelector:
    """Dialog for selecting moon landing location."""
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
