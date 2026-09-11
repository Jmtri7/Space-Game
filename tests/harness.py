"""Shared test harness: mock pygame, fix sys.path, re-export every symbol
the split test modules need. Imported by each tests/test_*.py via
`from tests.harness import *`. Not collected by unittest discovery
(filename does not match test_*.py)."""
import sys
import os
import io
import math
import tempfile
import shutil
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock, PropertyMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock pygame before importing modules to avoid display requirements
pygame_mock = MagicMock()
pygame_mock.K_UP = 273
pygame_mock.K_DOWN = 274
pygame_mock.K_LEFT = 276
pygame_mock.K_RIGHT = 275
pygame_mock.K_w = 119
pygame_mock.K_s = 115
pygame_mock.K_a = 97
pygame_mock.K_d = 100

# Mock display.Info to avoid display issues
info_mock = MagicMock()
info_mock.current_w = 1920
info_mock.current_h = 1080
pygame_mock.display.Info.return_value = info_mock
pygame_mock.init = MagicMock()

sys.modules['pygame'] = pygame_mock

import game.utils as utils
from game.world.ship import Ship
from game.world.landing_site import LandingSite
from game.world.person import Person
from game.world.possessions import Possessions
from game.world.dialogue import Dialogue, option_actions, apply_shared_actions, shared_action_blocked_reason
from game.world.mission import start_mission, check_mission_progress, mission_status_lines, abandon_mission
from game.world.follow_player_routine import FollowPlayerRoutine
from game.ui.report_menu import ReportMenu, mission_report, possessions_report
from game.ui.ui_theme import (
    side_panel_max_width, center_panel_max_width, side_panel_width, hud_margin,
    message_alert_state, MESSAGE_ALERT_FRAMES, MESSAGE_ALERT_BLINKS, MESSAGE_ALERT_BLINK_FRAMES,
    fit_text,
)
from game.screens.location_screen import LocationScreen, normalize_room, normalize_decoration, point_in_polygon
from game.graphics.deck_grid import (clip_polygon_convex as _clip_polygon_convex, tessellate as _tessellate)
from game.world.dock_routine import DockRoutine, ROLE_EXIT_PREFERENCE, MAX_LATERAL_HOPS
from game.world.indoor_pathfinder import IndoorPathfinder, NavGrid
from game.world.character import Character
from game.world.orbit_player_routine import OrbitPlayerRoutine
from game.world.wander_routine import WanderRoutine
from game.world.system_state import SystemState
from game.world.asteroid_field import AsteroidField
from game.ui.selectable_list import SelectableList
from game.ui.save_browser import SaveBrowser
from game.ui.choice_dialog import ChoiceDialog
from game.ui.backdrop_menu import BackdropMenu
from game.ui.star_map import StarMap
from game.world.combat_routine import CombatRoutine, _signed_angle_delta
from game.world.content_gate import passes_content_gate, is_gated
from game.ui.ending_screen import EndingScreen, ending_report
from game.ui.confirm_dialog import ConfirmDialog
from game.ui.shop_menu import ShopMenu
from game.ui.ship_browser_menu import ShipBrowserMenu, _approximate_size_label
from game.ui.icon_grid import IconGrid
from game.ui.outfitting_menu import OutfittingMenu, SLOT_COLORS
from game.screens.space_screen import SpaceScreen, TARGET_MODES
from game.constants import GAME_WIDTH, GAME_HEIGHT, CAMERA_ZOOM_STEP
from main import build_save_game_state, warn_if_story_version_mismatch, _pressed_any




class _FakeFont:
    """Stand-in for pygame.font.Font in wrap-width tests - width is just
    character count, so expected wrap points are exact and don't depend on
    real font metrics (pygame is mocked in this whole test module anyway)."""
    def size(self, text):
        return (len(text), 10)


# Export everything (including _underscore helpers imported above) to
# `from tests.harness import *`.
__all__ = [_n for _n in dir() if not _n.startswith("__")]
