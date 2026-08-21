import pygame
import sys

try:
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Test")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
except Exception as e:
    with open("error.txt", "w") as f:
        f.write(str(e))
    sys.exit(1)
