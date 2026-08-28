"""Game constants, colors, and configuration."""
import pygame

# Initialize pygame
pygame.init()

# World dimensions
GAME_WIDTH = 2400
GAME_HEIGHT = 1800
CAMERA_ZOOM = 3.0  # Zoom to keep objects at same visual scale despite larger world
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
SCREEN_WIDTH = info.current_w - 50  # Account for taskbar (~40px) and window title bar (~30px)
SCREEN_HEIGHT = info.current_h - 100
FPS = 60

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

# UI constants
FONT_SIZE = 20
SMALL_FONT_SIZE = 16
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 40
