"""Utility functions for rendering, file I/O, and coordinate conversion."""
import json
import os
import pygame
import game.constants as constants
from game.constants import (
    GAME_WIDTH, GAME_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT,
    CAMERA_ZOOM, SAVE_DIR, GREEN
)

class Camera:
    """Owns the camera's world offset and the window's screen size, and
    derives every scale/coordinate conversion from them. Replaces what used
    to be bare module-level globals (camera_offset_x/y, screen_width/height)
    mutated directly by anyone who imported this module - that state now
    lives here, only reachable through these methods and the module-level
    functions below that delegate to a single shared instance."""
    def __init__(self, screen_width, screen_height):
        self.offset_x = 0
        self.offset_y = 0
        self.screen_width = screen_width
        self.screen_height = screen_height

    def set_offset(self, x, y):
        self.offset_x = x
        self.offset_y = y

    def set_screen_size(self, width, height):
        self.screen_width = width
        self.screen_height = height

    def get_scale(self):
        """Get rendering scale based on window size."""
        return min(self.screen_width / GAME_WIDTH, self.screen_height / GAME_HEIGHT) * CAMERA_ZOOM

    def get_world_offset(self):
        """Get rendering offset to center game world."""
        scale = self.get_scale()
        offset_x = (self.screen_width - GAME_WIDTH * scale) / 2
        offset_y = (self.screen_height - GAME_HEIGHT * scale) / 2
        return (offset_x, offset_y)

    def to_screen(self, x, y):
        """Convert world coordinates to screen coordinates."""
        scale = self.get_scale()
        offset_x, offset_y = self.get_world_offset()
        x_camera = x - self.offset_x
        y_camera = y - self.offset_y
        return (int(round(x_camera * scale + offset_x)), int(round(y_camera * scale + offset_y)))

    def to_world(self, sx, sy):
        """Convert screen coordinates back to world coordinates - the
        inverse of to_screen(), used to resolve a mouse click's screen
        position to the world position it points at (e.g. click-to-target)."""
        scale = self.get_scale()
        offset_x, offset_y = self.get_world_offset()
        return ((sx - offset_x) / scale + self.offset_x, (sy - offset_y) / scale + self.offset_y)

    def to_screen_x(self, x):
        """Convert world X coordinate to screen space."""
        return int(round(x * self.get_scale()))

    def to_screen_y(self, y):
        """Convert world Y coordinate to screen space."""
        return int(round(y * self.get_scale()))

    def get_ui_scale(self):
        """Get scale for UI elements - based only on window size, not camera zoom."""
        return min(self.screen_width / 800, self.screen_height / 600)

    def get_ui_offset(self):
        """Get offset for UI elements - centers UI on screen."""
        ui_scale = self.get_ui_scale()
        offset_x = (self.screen_width - 800 * ui_scale) / 2
        offset_y = (self.screen_height - 600 * ui_scale) / 2
        return (offset_x, offset_y)

    def get_centered_x(self, text_width):
        """Get X coordinate to center text horizontally on screen."""
        return self.screen_width // 2 - text_width // 2

    def get_centered_y(self, text_height):
        """Get Y coordinate to center text vertically on screen."""
        return self.screen_height // 2 - text_height // 2


_camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)


def __getattr__(name):
    """Read-only passthrough so the many call sites that read
    `utils.screen_width`/`screen_height`/`camera_offset_x`/`camera_offset_y`
    as bare module attributes keep working unchanged, while the state
    itself now genuinely lives inside the Camera instance above rather than
    as directly-mutable module globals. See PEP 562."""
    if name == "screen_width":
        return _camera.screen_width
    if name == "screen_height":
        return _camera.screen_height
    if name == "camera_offset_x":
        return _camera.offset_x
    if name == "camera_offset_y":
        return _camera.offset_y
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def set_camera_offset(x, y):
    """Update the camera's world offset."""
    _camera.set_offset(x, y)


def set_screen_size(width, height):
    """Update the camera's screen dimensions."""
    _camera.set_screen_size(width, height)


def get_scale():
    """Get rendering scale based on window size."""
    return _camera.get_scale()


def get_offset():
    """Get rendering offset to center game world."""
    return _camera.get_world_offset()


def to_screen(x, y):
    """Convert world coordinates to screen coordinates."""
    return _camera.to_screen(x, y)


def to_world(x, y):
    """Convert screen coordinates back to world coordinates (inverse of to_screen)."""
    return _camera.to_world(x, y)


def to_screen_x(x):
    """Convert world X coordinate to screen space."""
    return _camera.to_screen_x(x)


def to_screen_y(y):
    """Convert world Y coordinate to screen space."""
    return _camera.to_screen_y(y)


def get_ui_scale():
    """Get scale for UI elements - based only on window size, not camera zoom."""
    return _camera.get_ui_scale()


def get_ui_offset():
    """Get offset for UI elements - centers UI on screen."""
    return _camera.get_ui_offset()


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
    return _camera.get_centered_x(text_width)


def get_centered_y(text_height):
    """Get Y coordinate to center text vertically on screen."""
    return _camera.get_centered_y(text_height)


def render_help_text(surface, text, y_pos=None, color=(150, 150, 150)):
    """Render help text at bottom of screen or at specified Y position."""
    from game.constants import GRAY
    color = color or GRAY
    font = get_font(int(16 * get_ui_scale()))
    help_text = font.render(text, True, color)
    if y_pos is None:
        y_pos = _camera.screen_height - 30
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


def load_json(filename):
    """Load JSON file, return None if error."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def save_json(filename, data):
    """Save data to JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_ship_type(story, ship_type_id):
    """Load ship type properties from config/stories/{story}/ship_types.json."""
    ship_types = load_json(f"config/stories/{story}/ship_types.json") or {}
    return ship_types.get(ship_type_id, {})


def get_asteroid_type(story, asteroid_type_id):
    """Load asteroid type properties (shape/color/jaggedness/spin) from
    config/stories/{story}/asteroid_types.json. Mirrors get_ship_type -
    a shared per-story table of visual/physical identities, while which
    types appear in a given system (and at what size/frequency) is a
    per-system choice (see systems/*.json's "asteroid_field" block)."""
    asteroid_types = load_json(f"config/stories/{story}/asteroid_types.json") or {}
    return asteroid_types.get(asteroid_type_id, {})


def get_culture(story, culture_id):
    """Load culture properties (material palette, design theme) from
    config/stories/{story}/cultures.json."""
    cultures = load_json(f"config/stories/{story}/cultures.json") or {}
    return cultures.get(culture_id, {})


def _resolve_culture_palette(story, asset):
    """Fill in color/core_color/window_color/thrust_color from the asset's
    culture, if it declares one and doesn't already set them explicitly.
    Lets ships, stations, and buildings share one culture's material palette
    (metal for hull, glass for windows/core, a distinct glow for thrust)
    instead of hardcoding colors per asset.
    """
    culture_id = asset.get("culture")
    if culture_id:
        culture = get_culture(story, culture_id)
        for asset_key, culture_key in (
            ("color", "metal_color"),
            ("core_color", "glass_color"),
            ("window_color", "glass_color"),
            ("thrust_color", "thrust_color"),
        ):
            value = culture.get(culture_key)
            if value is not None:
                asset.setdefault(asset_key, value)
    return asset


def get_graphics_asset(story, asset_type, asset_id):
    """Load graphics asset from config/stories/{story}/graphics.json, with culture colors resolved."""
    graphics = load_json(f"config/stories/{story}/graphics.json") or {}
    asset_category = graphics.get(asset_type, {})
    asset = dict(asset_category.get(asset_id, {}))
    return _resolve_culture_palette(story, asset)


def get_building_type(story, building_type_id):
    """Load building type properties from config/stories/{story}/building_types.json,
    with culture colors resolved."""
    building_types = load_json(f"config/stories/{story}/building_types.json") or {}
    asset = dict(building_types.get(building_type_id, {}))
    return _resolve_culture_palette(story, asset)


def get_pilot(story, pilot_id):
    """Load pilot properties (name, faction, role, personality) from
    config/stories/{story}/pilots.json."""
    pilots = load_json(f"config/stories/{story}/pilots.json") or {}
    return pilots.get(pilot_id, {})


def get_ship_outfit(story, outfit_id):
    """Load ship outfit properties from config/stories/{story}/ship_outfits.json.
    Distinct from graphics.json's "outfits" section (Person's cosmetic
    space-suit asset) - this is ship equipment (weapons/engines/shields/utility)."""
    ship_outfits = load_json(f"config/stories/{story}/ship_outfits.json") or {}
    return ship_outfits.get(outfit_id, {})


def get_commodity(story, commodity_id):
    """Load commodity properties from config/stories/{story}/commodities.json."""
    commodities = load_json(f"config/stories/{story}/commodities.json") or {}
    return commodities.get(commodity_id, {})


def get_item(story, item_id):
    """Load personal item properties from config/stories/{story}/items.json."""
    items = load_json(f"config/stories/{story}/items.json") or {}
    return items.get(item_id, {})


def get_star_systems(story):
    """Discover every star system belonging to one story, by scanning
    config/stories/{story}/systems/*.json. Systems only exist within a single
    story - the Jump mechanic can move a ship between systems in its own
    story, never into a different story (stories are wholly separate saves).

    Returns {system_id: {"name": ..., "star_map_position": {"x": ..., "y": ...},
    "station_name": ..., "moon_name": ...}}. This is the single source of
    truth for the galaxy star map - no separate registry to keep in sync,
    since each system file already declares its own name/position/contents.
    """
    systems = {}
    systems_dir = f"config/stories/{story}/systems"
    if not os.path.exists(systems_dir):
        return systems
    for filename in os.listdir(systems_dir):
        if not filename.endswith(".json"):
            continue
        system_id = filename[:-len(".json")]
        data = load_json(os.path.join(systems_dir, filename))
        if data:
            systems[system_id] = {
                "name": data.get("name", system_id),
                "star_map_position": data.get("star_map_position", {"x": 0, "y": 0}),
                "station_name": data.get("station", {}).get("name", "Station"),
                "moon_name": data.get("moon", {}).get("name", "Moon"),
            }
    return systems


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
    """Create and save a game save file.

    The default save name only has minute resolution, so two new saves made
    within the same minute would otherwise collide on the same filename and
    the second save would silently clobber the first. If `name` is already
    taken, append " (2)", " (3)", etc. until it isn't. Callers that intend to
    overwrite an existing save (the pause menu's overwrite-confirm flow)
    delete the old file first, so this never fires for a real overwrite.
    """
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    unique_name = name
    suffix = 2
    while os.path.exists(f"{SAVE_DIR}/save_{unique_name}.json"):
        unique_name = f"{name} ({suffix})"
        suffix += 1
    save_data = {
        "pilot_name": pilot_name,
        "name": unique_name,
        "system": system_data,
        "station": station_data,
        "game_state": game_state or {}
    }
    filename = f"{SAVE_DIR}/save_{unique_name}.json"
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
    """Get X position to center text horizontally on screen.

    Uses the UI-space scale (window dimensions, not the space camera's zoom) -
    for menus/dialogs, pair this with get_ui_offset(), not get_offset().
    """
    ui_scale = get_ui_scale()
    return int(offset_x + 800 * ui_scale * 0.5 - text.get_width() // 2)


def _wrap_text(font, text, max_width):
    """Word-wrap text into lines that each fit within max_width - shared by
    anything drawing free-form config text (story descriptions, dialogue) so
    it never runs past its box instead of hand-rolling this per screen."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
