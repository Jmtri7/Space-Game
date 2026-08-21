import pygame
import sys

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pygame Menu")
clock = pygame.time.Clock()

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
YELLOW = (255, 255, 0)

class Menu:
    def __init__(self):
        self.items = ["NEW", "LOAD", "QUIT"]
        self.selected_index = 0
        self.font_large = pygame.font.Font(None, 72)
        self.font_menu = pygame.font.Font(None, 48)

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
        return None

    def _check_click(self, pos):
        for i, item in enumerate(self.items):
            rect = self._get_item_rect(i)
            if rect.collidepoint(pos):
                self.selected_index = i
                return item.lower()
        return None

    def _get_item_rect(self, index):
        y_base = 200
        y_spacing = 80
        text = self.font_menu.render(self.items[index], True, WHITE)
        rect = text.get_rect(center=(SCREEN_WIDTH // 2 + 80, y_base + index * y_spacing))
        return rect

    def draw(self, surface):
        surface.fill(BLACK)

        title = self.font_large.render("MENU", True, WHITE)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

        y_base = 200
        y_spacing = 80

        for i, item in enumerate(self.items):
            color = YELLOW if i == self.selected_index else GRAY
            text = self.font_menu.render(item, True, color)
            y = y_base + i * y_spacing
            surface.blit(text, (SCREEN_WIDTH // 2 + 80, y))

            if i == self.selected_index:
                dot_radius = 12
                dot_x = SCREEN_WIDTH // 2 + 40
                pygame.draw.circle(surface, YELLOW, (dot_x, y + text.get_height() // 2), dot_radius)

def handle_selection(selection):
    if selection == "new":
        print("NEW GAME selected")
    elif selection == "load":
        print("LOAD GAME selected")
    elif selection == "quit":
        return False
    return True

def main():
    menu = Menu()
    running = True

    while running:
        events = pygame.event.get()
        selection = menu.handle_input(events)

        if selection == "quit":
            running = False
        elif selection:
            handle_selection(selection)

        menu.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
