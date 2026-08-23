"""Game constants, colors, and configuration."""
import pygame

# Initialize pygame
pygame.init()

# World dimensions
GAME_WIDTH = 2400
GAME_HEIGHT = 1800
CAMERA_ZOOM = 3.0  # Zoom to keep objects at same visual scale despite larger world
SAVE_DIR = "saves"

# Display setup
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w - 50  # Account for taskbar (~40px) and window title bar (~30px)
SCREEN_HEIGHT = info.current_h - 100
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
YELLOW = (255, 255, 0)
DARK_GRAY = (60, 60, 60)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)

# Debug mode
DEBUG_MODE = False  # Press ` (backtick) to toggle

# UI constants
FONT_SIZE = 20
SMALL_FONT_SIZE = 16
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 40
