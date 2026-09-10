# Shared imports + module constants for the space_screen package.
"""Main space exploration screen with ships and landing."""
import pygame
import math
import random
import game.constants as constants
from game.constants import (
    GAME_WIDTH, GAME_HEIGHT, CAMERA_ZOOM, CAMERA_ZOOM_MIN, CAMERA_ZOOM_MAX, CAMERA_ZOOM_STEP,
    BLACK, YELLOW, WHITE, GREEN, GRAY, CYAN, RED
)
from game.utils import (
    get_scale, get_offset, get_ui_scale, load_json, set_camera_offset, set_camera_angle,
    set_camera_zoom, set_camera_zoom_limits,
    draw_debug_marker, draw_target_brackets, get_font, to_world,
    get_ship_type, get_graphics_asset, get_pilot, get_star_systems, get_ship_outfit,
    get_asteroid_type, get_commodity, get_missions, get_story, get_factions,
    system_unlocked
)
import game.utils as utils
from game.perf_metrics import metrics as perf
from game.audio.sound_board import sound_board
from game.ui.ui_theme import draw_glass_panel, draw_glow_message, draw_controls_pane, draw_status_pane, draw_info_panel, draw_message_log, side_panel_width, hud_margin, MESSAGE_ALERT_FRAMES, message_alert_state
from game.screens.screen_base import ScreenBase
from game.screens.location_screen import LocationScreen
from game.world.player_controller import PlayerController
from game.world.projectile import Projectile, PROJECTILE_SPEED, PROJECTILE_SIZE, PROJECTILE_DAMAGE, PROJECTILE_LIFETIME
from game.world.asteroid import Asteroid
from game.world.explosion import Explosion
from game.world.ore_pickup import OrePickup, PICKUP_RANGE
from game.world.autopilot import has_arrived
from game.world.character import Character, resolve_routine_class
from game.world.orbit_player_routine import OrbitPlayerRoutine
from game.world.combat_routine import CombatRoutine
from game.world.content_gate import passes_content_gate, is_gated
from game.world.dialogue import option_actions, apply_shared_actions
from game.world.mission import start_mission, check_mission_progress
from game.world.landing_site import LandingSite
from game.world.starfield import StarField
from game.world.central_star import CentralStar
from game.world.celestial_body import CelestialBody
from game.world.asteroid_field import AsteroidField
from game.world.system_state import SystemState

# Hailing tuning
ONE_WAY_HAIL_RANGE = 500          # world units - how close an NPC-initiated hail can trigger from
ONE_WAY_HAIL_BANNER_FRAMES = 300  # ~5s at 60fps an incoming-hail banner stays up
HAIL_BUSY_BANNER_FRAMES = 150     # ~2.5s "no response" flash when hailing a docked/ashore pilot
HOSTILE_REP_THRESHOLD = -40       # faction standing at/below this turns its pilots hostile (see _sync_hostiles)

# How slow (units/frame) counts as "braked to a stop" for the generic
# "braked_below_threshold" gameplay-event flag (see update_physics) - a
# mission's braking-practice stage can use this as its complete_flag.
# story.json's "brake_slow_threshold" overrides this per story (see
# SpaceScreen.brake_slow_threshold).
BRAKE_SLOW_THRESHOLD = 0.3

# Jump mechanic tuning - defaults; story.json's "jump" block overrides
# travel_frames / speed / arrival_distance / self_min_distance per story
# (see SpaceScreen.jump_* instance attributes, which is what the jump code
# actually reads - these module names are only the fallback).
JUMP_TRAVEL_FRAMES = 150        # ~2.5s at 60fps of high-speed travel
JUMP_SPEED = 40                 # world units/frame while traveling
JUMP_ARRIVAL_DISTANCE = 1400    # world units from system center on arrival
JUMP_SELF_MIN_DISTANCE = 3200   # must be at least this far from center to jump "back" -
# roughly the point where the station/moon have scrolled off the edge of the
# minimap (MINIMAP_RANGE, plus their own offset from center), so "far enough
# to jump" lines up with "you can't see home on radar anymore". Not exact -
# the minimap's reach varies a little with window aspect - and doesn't need
# to be.

# ~4s at 60fps a transient toast (jump done, mission start/stage/finish) stays up
TOAST_FRAMES = 240
# MESSAGE_ALERT_FRAMES (how long the Message Log's "unread" light is active
# after a message) now lives in ui_theme alongside the blink/ping schedule -
# imported above.
SYSTEM_CENTER = (GAME_WIDTH / 2, GAME_HEIGHT / 2)

# Degrees per frame the view rotates while Q/E is held (see handle_input).
# Purely a camera/view setting - never touches ship heading or physics.
CAMERA_ROTATE_SPEED = 2

# Minimap tuning - its on-screen size now tracks the shared side-panel width
# (see ui_theme.side_panel_width); this is just the radar's world reach.
MINIMAP_RANGE = 2600   # world units from player (center) to the minimap's edge

# Targeting modes - cycled with Tab, filters what T/[/] can select.
# "MISC" covers everything that's neither a ship nor a landing site (celestial
# bodies, the central star). LANDING SITES is the default since finding and
# landing on the station is the first thing a new pilot needs to target.
TARGET_MODES = ["SHIPS", "LANDING SITES", "MISC"]
