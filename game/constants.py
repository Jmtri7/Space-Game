"""Game constants, colors, and configuration."""
import pygame

# Initialize pygame
pygame.init()

# World dimensions
GAME_WIDTH = 2400
GAME_HEIGHT = 1800
CAMERA_ZOOM = 3.0  # Zoom to keep objects at same visual scale despite larger world
SAVE_DIR = "saves"

# On-foot walking speed (world units/frame), inside a station/moon
# interior - shared by LocationScreen (the player) and DockRoutine (an AI
# pilot walking to/from their ship) so both move at the same pace. Lives
# here, not duplicated as a literal in each, since game/world (DockRoutine)
# can't import game/screens (LocationScreen) the other way around.
WALKING_SPEED = 2.5

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
RED = (255, 60, 60)

# Debug mode
DEBUG_MODE = False  # Press ` (backtick) to toggle

# UI constants
FONT_SIZE = 20
SMALL_FONT_SIZE = 16
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 40
