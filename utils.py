"""Utility functions for rendering, file I/O, and coordinate conversion."""
import json
import os
import pygame
import constants
from constants import (
    GAME_WIDTH, GAME_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT,
    CAMERA_ZOOM, SAVE_DIR, GREEN
)

# Global camera offset
camera_offset_x = 0
camera_offset_y = 0
screen_width = SCREEN_WIDTH
screen_height = SCREEN_HEIGHT


def set_camera_offset(x, y):
    """Update global camera offset."""
    global camera_offset_x, camera_offset_y
    camera_offset_x = x
    camera_offset_y = y


def set_screen_size(width, height):
    """Update global screen dimensions."""
    global screen_width, screen_height
    screen_width = width
    screen_height = height


def get_scale():
    """Get rendering scale based on window size."""
    return min(screen_width / GAME_WIDTH, screen_height / GAME_HEIGHT) * CAMERA_ZOOM


def get_offset():
    """Get rendering offset to center game world."""
    scale = get_scale()
    offset_x = (screen_width - GAME_WIDTH * scale) / 2
    offset_y = (screen_height - GAME_HEIGHT * scale) / 2
    return (offset_x, offset_y)


def to_screen(x, y):
    """Convert world coordinates to screen coordinates."""
    scale = get_scale()
    offset_x, offset_y = get_offset()
    x_camera = x - camera_offset_x
    y_camera = y - camera_offset_y
    return (int(round(x_camera * scale + offset_x)), int(round(y_camera * scale + offset_y)))


def to_screen_x(x):
    """Convert world X coordinate to screen space."""
    scale = get_scale()
    return int(round(x * scale))


def to_screen_y(y):
    """Convert world Y coordinate to screen space."""
    scale = get_scale()
    return int(round(y * scale))


def get_ui_scale():
    """Get scale for UI elements - based only on window size, not camera zoom."""
    return min(screen_width / 800, screen_height / 600)


def get_ui_offset():
    """Get offset for UI elements - centers UI on screen."""
    ui_scale = get_ui_scale()
    offset_x = (screen_width - 800 * ui_scale) / 2
    offset_y = (screen_height - 600 * ui_scale) / 2
    return (offset_x, offset_y)


# Font cache for efficient font reuse
_font_cache = {}

def get_font(size, bold=False):
    """Get or create a cached font to avoid recreating fonts every frame."""
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(None, int(size))
    return _font_cache[key]


def get_centered_x(text_width):
    """Get X coordinate to center text horizontally on screen."""
    return screen_width // 2 - text_width // 2


def get_centered_y(text_height):
    """Get Y coordinate to center text vertically on screen."""
    return screen_height // 2 - text_height // 2


def render_help_text(surface, text, y_pos=None, color=(150, 150, 150)):
    """Render help text at bottom of screen or at specified Y position."""
    from constants import GRAY
    color = color or GRAY
    font = get_font(int(16 * get_ui_scale()))
    help_text = font.render(text, True, color)
    if y_pos is None:
        y_pos = screen_height - 30
    x = get_centered_x(help_text.get_width())
    surface.blit(help_text, (x, int(y_pos)))


def handle_menu_navigation(event, current_index, list_length):
    """Handle UP/DOWN arrow key navigation for menus. Returns new index or None if unchanged."""
    if not event or event.type != pygame.KEYDOWN or list_length == 0:
        return None
    if event.key == pygame.K_UP or event.key == pygame.K_w:
        return (current_index - 1) % list_length
    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
        return (current_index + 1) % list_length
    return None


def draw_dialog_box(surface, x, y, width, height, color=(40, 40, 60), border_color=(100, 100, 100)):
    """Draw a dialog box background with border."""
    pygame.draw.rect(surface, color, (int(x), int(y), int(width), int(height)))
    pygame.draw.rect(surface, border_color, (int(x), int(y), int(width), int(height)), 2)


def load_json(filename):
    """Load JSON file, return None if error."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        return None


def save_json(filename, data):
    """Save data to JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


def get_ship_type(ship_type_id):
    """Load ship type properties from config/ship_types.json."""
    ship_types = load_json("config/ship_types.json") or {}
    return ship_types.get(ship_type_id, {})


def get_graphics_asset(asset_type, asset_id):
    """Load graphics asset from config/graphics.json."""
    graphics = load_json("config/graphics.json") or {}
    asset_category = graphics.get(asset_type, {})
    return asset_category.get(asset_id, {})


def _list_files_by_pattern(directory, prefix, suffix):
    """List files matching pattern, sorted reverse alphabetically."""
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
    """Get list of save files."""
    return _list_files_by_pattern(SAVE_DIR, "save_", ".json")


def create_save_file(pilot_name, name, system_data, station_data, game_state=None):
    """Create and save a game save file."""
    save_data = {
        "pilot_name": pilot_name,
        "name": name,
        "system": system_data,
        "station": station_data,
        "game_state": game_state or {}
    }
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    filename = f"{SAVE_DIR}/save_{name}.json"
    save_json(filename, save_data)
    return filename


def load_save_file(filename):
    """Load a save file."""
    filepath = f"{SAVE_DIR}/{filename}"
    return load_json(filepath)


def delete_save_file(filename):
    """Delete a save file."""
    try:
        os.remove(filename)
        return True
    except:
        return False


def draw_debug_marker(surface, x, y, size=8):
    """Draw a green X at world coordinates to show entity position."""
    if not constants.DEBUG_MODE:
        return
    screen_x, screen_y = to_screen(x, y)
    half = size // 2
    pygame.draw.line(surface, GREEN, (screen_x - half, screen_y - half), (screen_x + half, screen_y + half), 1)
    pygame.draw.line(surface, GREEN, (screen_x - half, screen_y + half), (screen_x + half, screen_y - half), 1)


def draw_target_brackets(surface, x, y, size=40, thickness=2):
    """Draw corner brackets around a targeted object at world coordinates."""
    screen_x, screen_y = to_screen(x, y)
    quarter = size // 4

    pygame.draw.line(surface, GREEN, (screen_x - size, screen_y - size), (screen_x - quarter, screen_y - size), thickness)
    pygame.draw.line(surface, GREEN, (screen_x - size, screen_y - size), (screen_x - size, screen_y - quarter), thickness)

    pygame.draw.line(surface, GREEN, (screen_x + size, screen_y - size), (screen_x + quarter, screen_y - size), thickness)
    pygame.draw.line(surface, GREEN, (screen_x + size, screen_y - size), (screen_x + size, screen_y - quarter), thickness)

    pygame.draw.line(surface, GREEN, (screen_x - size, screen_y + size), (screen_x - quarter, screen_y + size), thickness)
    pygame.draw.line(surface, GREEN, (screen_x - size, screen_y + size), (screen_x - size, screen_y + quarter), thickness)

    pygame.draw.line(surface, GREEN, (screen_x + size, screen_y + size), (screen_x + quarter, screen_y + size), thickness)
    pygame.draw.line(surface, GREEN, (screen_x + size, screen_y + size), (screen_x + size, screen_y + quarter), thickness)


def draw_landing_prediction(surface, x, y):
    """Draw predicted landing position as a yellow circle."""
    if not constants.DEBUG_MODE:
        return
    screen_x, screen_y = to_screen(x, y)
    pygame.draw.circle(surface, (255, 200, 0), (screen_x, screen_y), 8, 2)


def draw_landing_trajectory(surface, waypoints):
    """Draw predicted trajectory as connected waypoints."""
    if not constants.DEBUG_MODE or not waypoints or len(waypoints) < 2:
        return

    screen_points = [to_screen(x, y) for x, y in waypoints]

    # Draw line connecting waypoints
    pygame.draw.lines(surface, (255, 200, 0), screen_points, 1)

    # Draw waypoint circles
    for point in screen_points:
        pygame.draw.circle(surface, (200, 150, 0), point, 3, 1)


def _handle_scrolling_input(key, selected, items, scroll_offset, max_visible):
    """Handle up/down navigation in scrollable lists."""
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
    """Get X position to center text horizontally on screen."""
    scale = get_scale()
    return int(offset_x + GAME_WIDTH * scale * 0.5 - text.get_width() // 2)
