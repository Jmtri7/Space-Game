"""Game constants, colors, and configuration."""
import pygame

# Initialize pygame
pygame.init()

# World dimensions
GAME_WIDTH = 2400
GAME_HEIGHT = 1800
CAMERA_ZOOM = 3.0  # Zoom to keep objects at same visual scale despite larger world
# Player-adjustable world zoom (mouse wheel over open space - see
# SpaceScreen/LocationScreen.handle_input). CAMERA_ZOOM above is the default
# starting level; these bound how far the wheel can push it. The Space View
# and interiors keep independent ranges so a story can let you pull way back
# in open space while keeping a station framed tight - each is overridable
# per story (story.json's "camera_zoom"/"camera_zoom_min"/"camera_zoom_max"
# and "interior_camera_zoom"/"interior_camera_zoom_min"/"..._max"). The live
# level is remembered per context for the session and captured in the save.
CAMERA_ZOOM_MIN = 2.0
CAMERA_ZOOM_MAX = 9.0
INTERIOR_CAMERA_ZOOM = 3.0
INTERIOR_CAMERA_ZOOM_MIN = 2.0
INTERIOR_CAMERA_ZOOM_MAX = 9.0
CAMERA_ZOOM_STEP = 0.25  # zoom change per mouse-wheel notch
SAVE_DIR = "saves"
# Where MusicPlayer caches its procedurally-rendered tracks so they only
# have to be synthesized once per machine (see game/audio/music.py).
MUSIC_CACHE_DIR = "music_cache"

# On-foot walking speed (world units per 1/60 s sim-step), inside a
# station/moon interior - shared by LocationScreen (the player) and
# DockRoutine (an AI pilot walking to/from their ship) so both move at the
# same pace. Lives here, not duplicated as a literal in each, since
# game/world (DockRoutine) can't import game/screens (LocationScreen) the
# other way around. A story's story.json "walking_speed" overrides it.
WALKING_SPEED = 2.0

# Grid resolution (world units) for interior navigation - the walkability
# grid LocationScreen.plan_path builds once per interior and runs A* over
# to route visiting AI pilots (DockRoutine) around walls/footprints. Small
# enough to thread the narrowest authored corridor, large enough that a
# whole station/moon interior is only a few thousand cells.
NAV_CELL = 24

# Display setup
info = pygame.display.Info()
DESKTOP_WIDTH = info.current_w
DESKTOP_HEIGHT = info.current_h
SCREEN_WIDTH = info.current_w - 50  # Account for taskbar (~40px) and window title bar (~30px)
SCREEN_HEIGHT = info.current_h - 100
FPS = 60

# Resolution candidates for Settings -> Video. The chosen one is
# the fixed SCALED logical surface (main.open_window): the game renders at it
# and SDL scales that to the actual window, so it also sets the smallest the
# window can be dragged. The menu groups these by aspect ratio - the player
# picks an aspect (their display's by default) and then a resolution within
# it; only entries that fit the desktop are offered, and the native desktop
# resolution is always available under its own aspect. See main.py's
# ASPECTS / aspect_label / resolutions_for_aspect / available_aspects.
VIDEO_RESOLUTIONS = [
    (1024, 768), (1280, 960), (1400, 1050), (1600, 1200), (2048, 1536),    # 4:3
    (1280, 1024),                                                          # 5:4
    (2160, 1440), (2256, 1504),                                            # 3:2
    (1280, 800), (1440, 900), (1680, 1050), (1920, 1200), (2560, 1600),    # 16:10
    (1280, 720), (1366, 768), (1600, 900), (1920, 1080),
    (2560, 1440), (3200, 1800), (3840, 2160),                              # 16:9
    (2560, 1080), (3440, 1440), (3840, 1600), (5120, 2160),                # 21:9
    (3840, 1080), (5120, 1440),                                            # 32:9
]

# Fixed-timestep simulation (see docs/BACKLOG.md "Fixed-timestep accumulator").
# The main loop drains an accumulator of real elapsed time in fixed SIM_STEP
# chunks, running the simulation the right number of times for the wall clock
# regardless of frame rate, while rendering stays once per frame.
#
# SIM_STEP MUST stay exactly 1/60: every physics constant in the game
# (drag 0.98/frame, thrust ramp, 5deg/frame rotation, per-frame countdown
# timers) is already calibrated to a 1/60 s step, so at this value the math is
# byte-identical to the old one-step-per-frame loop on any machine holding 60
# FPS. It only diverges when a machine can't keep up, and then it runs 2-3 sim
# steps per render (sim stays correct, rendering gets choppy) instead of one
# slow step (sim goes wrong). Changing SIM_STEP - or moving to units/second -
# would change what an existing save's stored velocities mean; see CLAUDE.md's
# "Save Compatibility & Story Versioning" section before doing that.
SIM_STEP = 1.0 / 60.0
MAX_STEPS_PER_FRAME = 5   # spiral-of-death clamp: give up catching up past this
MAX_FRAME_TIME = 0.25     # clamp real elapsed before it feeds the accumulator,
                          # so a debugger pause / asset-load hitch can't dump
                          # seconds of catch-up into the sim at once

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

# Anti-aliasing mode (Settings -> Video). One of AA_MODES:
#   "off"         - straight pygame.draw, hard edges
#   "gfxdraw"     - per-primitive AA via game/aa_draw.py: a gfxdraw filled
#                   shape plus a matching aa outline at each world draw site
#                   (ships, stations, buildings, people, ...). Cheap - no
#                   offscreen buffer - but only reaches the call sites routed
#                   through aa_draw, and UI/HUD stay aliased.
#   "supersample" - main.py's PHASE 3 renders the whole frame to a 2x-logical
#                   offscreen surface and smoothscales it down. Universal
#                   (everything, UI included) but ~4x fill + a downscale per
#                   frame.
# Loaded from settings.json ("aa_mode") at startup, cycled in the Settings
# menu. Off by default.
AA_MODE = "off"
AA_MODES = ("off", "gfxdraw", "supersample")
AA_MODE_LABELS = {"off": "Off", "gfxdraw": "gfxdraw", "supersample": "Supersampling x2"}

# UI constants
FONT_SIZE = 20
SMALL_FONT_SIZE = 16
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 40
