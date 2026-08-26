"""Unit tests for helper functions extracted from main.py"""
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
pygame_mock.K_w = 119
pygame_mock.K_s = 115
pygame_mock.K_a = 97

# Mock display.Info to avoid display issues
info_mock = MagicMock()
info_mock.current_w = 1920
info_mock.current_h = 1080
pygame_mock.display.Info.return_value = info_mock
pygame_mock.init = MagicMock()

sys.modules['pygame'] = pygame_mock

import game.utils as utils
from game.world.ship import Ship
from game.world.landable import Landable
from game.world.person import Person
from game.world.possessions import Possessions
from game.world.dialogue import Dialogue
from game.screens.location_screen import LocationScreen
from game.world.dock_routine import DockRoutine, ROLE_EXIT_PREFERENCE, MAX_LATERAL_HOPS
from game.world.indoor_pathfinder import IndoorPathfinder
from game.world.character import Character
from game.world.wander_routine import WanderRoutine
from game.world.system_state import SystemState
from game.ui.selectable_list import SelectableList
from game.ui.save_dialog import SaveDialog
from game.ui.shop_menu import ShopMenu
from game.ui.ship_browser_menu import ShipBrowserMenu, _approximate_size_label
from game.ui.icon_grid import IconGrid
from game.ui.outfitting_menu import OutfittingMenu, SLOT_COLORS
from game.screens.space_screen import SpaceScreen, TARGET_MODES
from main import build_save_game_state, warn_if_story_version_mismatch


class TestHandleScrollingInput(unittest.TestCase):
    """Test _handle_scrolling_input helper function"""

    def setUp(self):
        self.items = ["save1", "save2", "save3", "save4", "save5", "save6"]
        self.max_visible = 3

    def test_down_moves_selection(self):
        """Pressing DOWN should move selection forward"""
        selected, scroll = utils._handle_scrolling_input(
            274, 0, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)
        self.assertEqual(scroll, 0)

    def test_down_wraps_at_end(self):
        """Selection should wrap to 0 when reaching end"""
        selected, scroll = utils._handle_scrolling_input(
            274, 5, self.items, 3, self.max_visible
        )
        self.assertEqual(selected, 0)
        self.assertEqual(scroll, 0)

    def test_down_scrolls_when_needed(self):
        """Scroll should advance when selection reaches bottom of visible area"""
        selected, scroll = utils._handle_scrolling_input(
            274, 2, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 3)
        self.assertEqual(scroll, 1)

    def test_up_moves_selection_back(self):
        """Pressing UP should move selection backward"""
        selected, scroll = utils._handle_scrolling_input(
            273, 2, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)
        self.assertEqual(scroll, 0)

    def test_up_wraps_at_start(self):
        """Selection should wrap to end when moving up from 0"""
        selected, scroll = utils._handle_scrolling_input(
            273, 0, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 5)
        self.assertEqual(scroll, 3)

    def test_up_scrolls_when_needed(self):
        """Scroll should go back when selection is at top of visible area"""
        selected, scroll = utils._handle_scrolling_input(
            273, 2, self.items, 2, self.max_visible
        )
        self.assertEqual(selected, 1)
        self.assertEqual(scroll, 1)

    def test_w_key_is_up(self):
        """W key should behave like UP"""
        selected, scroll = utils._handle_scrolling_input(
            119, 2, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)

    def test_s_key_is_down(self):
        """S key should behave like DOWN"""
        selected, scroll = utils._handle_scrolling_input(
            115, 0, self.items, 0, self.max_visible
        )
        self.assertEqual(selected, 1)

    def test_invalid_key_no_change(self):
        """Invalid key should not change selection or scroll"""
        selected, scroll = utils._handle_scrolling_input(
            97, 2, self.items, 1, self.max_visible
        )
        self.assertEqual(selected, 2)
        self.assertEqual(scroll, 1)


class TestListFilesByPattern(unittest.TestCase):
    """Test _list_files_by_pattern helper function"""

    def setUp(self):
        """Create temporary directory for testing"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.test_dir)

    def test_lists_matching_files(self):
        """Should list files matching prefix and suffix"""
        open(os.path.join(self.test_dir, "save_test1.json"), "w").close()
        open(os.path.join(self.test_dir, "save_test2.json"), "w").close()

        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(len(files), 2)
        self.assertIn("save_test1.json", files)
        self.assertIn("save_test2.json", files)

    def test_filters_prefix(self):
        """Should only match files with correct prefix"""
        open(os.path.join(self.test_dir, "save_test.json"), "w").close()
        open(os.path.join(self.test_dir, "other_test.json"), "w").close()

        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "save_test.json")

    def test_filters_suffix(self):
        """Should only match files with correct suffix"""
        open(os.path.join(self.test_dir, "save_test.json"), "w").close()
        open(os.path.join(self.test_dir, "save_test.txt"), "w").close()

        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "save_test.json")

    def test_returns_sorted_reverse(self):
        """Should return files sorted in reverse (newest first)"""
        # Create files
        for i in range(1, 4):
            open(os.path.join(self.test_dir, f"save_test{i}.json"), "w").close()

        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        # Should be reverse sorted
        self.assertEqual(files[0], "save_test3.json")
        self.assertEqual(files[-1], "save_test1.json")

    def test_creates_dir_if_missing(self):
        """Should create directory if it doesn't exist"""
        nonexistent = os.path.join(self.test_dir, "subdir")
        files = utils._list_files_by_pattern(nonexistent, "save_", ".json")
        self.assertTrue(os.path.exists(nonexistent))
        self.assertEqual(files, [])

    def test_empty_dir_returns_empty_list(self):
        """Should return empty list for directory with no matching files"""
        files = utils._list_files_by_pattern(self.test_dir, "save_", ".json")
        self.assertEqual(files, [])


class TestCenterTextX(unittest.TestCase):
    """Test _center_text_x helper function"""

    def test_returns_integer(self):
        """Should return an integer coordinate"""
        text = MagicMock()
        text.get_width.return_value = 100

        result = utils._center_text_x(None, text)
        self.assertIsInstance(result, int)

    def test_centers_horizontally(self):
        """Should center text within the UI's 800-unit-wide space (not
        GAME_WIDTH - _center_text_x uses get_ui_scale(), a separate scale
        for menus/dialogs, independent of the space camera's zoom)"""
        text = MagicMock()
        text.get_width.return_value = 200

        result = utils._center_text_x(None, text)
        ui_scale = utils.get_ui_scale()
        expected = int(800 * ui_scale * 0.5 - 200 // 2)
        self.assertEqual(result, expected)

    def test_respects_offset(self):
        """Should shift the centered position by offset_x"""
        text = MagicMock()
        text.get_width.return_value = 200

        result = utils._center_text_x(None, text, offset_x=50)
        ui_scale = utils.get_ui_scale()
        expected = int(50 + 800 * ui_scale * 0.5 - 200 // 2)
        self.assertEqual(result, expected)


class TestAutopilotPhysics(unittest.TestCase):
    """Test seek-mode autopilot arrives at a landable with precise position
    and velocity, using the real Ship/Autopilot/Landable classes and the
    same engage_seek() + ship.update() flow the game itself drives - not a
    reimplementation of the landing condition, so this can't drift out of
    sync with autopilot.py's actual disengage logic."""

    def simulate_autopilot_to_landing(self, ship, target_x, target_y, landing_distance=100, max_frames=2000):
        """Simulate ship autopilot from start to landing using real game physics"""
        target = Landable(target_x, target_y, graphics={"landing_distance": landing_distance})
        ship.x = 0
        ship.y = 0
        ship.angle = 0
        ship.velocity_x = 0
        ship.velocity_y = 0
        ship.thrust = 0
        ship.engage_seek(target)

        frames = 0
        min_distance = float('inf')
        oscillated = False  # Did ship overshoot then come back?

        while ship.autopilot_active and frames < max_frames:
            frames += 1
            ship.update()  # advances autopilot internally, exactly as the game does

            distance = target.get_distance(ship.x, ship.y)

            # Track closest approach and detect oscillation
            if distance < min_distance:
                min_distance = distance
            elif distance > min_distance + 50 and min_distance < landing_distance + 50:
                # Ship got close, then moved away significantly = oscillation
                oscillated = True

        # autopilot_active going False (via Autopilot.disengage()) is the
        # game's own signal that it landed - not a separate distance/speed
        # check re-guessed here.
        landed = not ship.autopilot_active
        distance = target.get_distance(ship.x, ship.y)
        speed = (ship.velocity_x ** 2 + ship.velocity_y ** 2) ** 0.5
        return {
            'landed': landed,
            'frames': frames,
            'distance': distance,
            'speed': speed,
            'min_distance': min_distance,
            'oscillated': oscillated,
        }

    def test_autopilot_shuttle_lands_precisely(self):
        """Shuttle (config/stories/default/ship_types.json stats) lands once, no oscillation"""
        ship = Ship(0, 0)
        ship.acceleration_magnitude = 0.12
        ship.max_velocity = 2.0
        ship.rotation_speed = 4

        result = self.simulate_autopilot_to_landing(ship, 500, 0)

        self.assertTrue(result['landed'], f"Autopilot failed to land (frames: {result['frames']})")
        self.assertLess(result['distance'], 20,
                        f"Shuttle distance {result['distance']:.1f} - should arrive close to the landable's center")
        self.assertEqual(result['speed'], 0,
                        f"Shuttle velocity {result['speed']:.3f} - should be fully parked (zero velocity)")
        self.assertFalse(result['oscillated'],
                        f"Shuttle oscillated - ship should come to stop once, not bounce")

    def test_autopilot_freighter_lands_precisely(self):
        """Freighter (config/stories/default/ship_types.json stats) lands once, no oscillation"""
        ship = Ship(0, 0)
        ship.acceleration_magnitude = 0.1
        ship.max_velocity = 2.0
        ship.rotation_speed = 1

        result = self.simulate_autopilot_to_landing(ship, 400, 0)

        self.assertTrue(result['landed'], f"Autopilot failed to land (frames: {result['frames']})")
        self.assertLess(result['distance'], 20,
                        f"Freighter distance {result['distance']:.1f} - should arrive close to the landable's center")
        self.assertEqual(result['speed'], 0,
                        f"Freighter velocity {result['speed']:.3f} - should be fully parked (zero velocity)")
        self.assertFalse(result['oscillated'],
                        f"Freighter oscillated - ship should come to stop once, not bounce")

    def test_autopilot_patrol_lands_precisely(self):
        """Patrol (config/stories/default/ship_types.json stats) lands once, no oscillation"""
        ship = Ship(0, 0)
        ship.acceleration_magnitude = 0.35
        ship.max_velocity = 5.0
        ship.rotation_speed = 7

        result = self.simulate_autopilot_to_landing(ship, 300, 0)

        self.assertTrue(result['landed'], f"Autopilot failed to land (frames: {result['frames']})")
        self.assertLess(result['distance'], 20,
                        f"Patrol distance {result['distance']:.1f} - should arrive close to the landable's center")
        self.assertEqual(result['speed'], 0,
                        f"Patrol velocity {result['speed']:.3f} - should be fully parked (zero velocity)")
        self.assertFalse(result['oscillated'],
                        f"Patrol oscillated - ship should come to stop once, not bounce")


class TestLocationExitOptions(unittest.TestCase):
    """Test LocationScreen.get_exit_options() - the config-driven list of
    where an interior's exit leads (connected_locations plus "ship"),
    consumed by both the player's exit menu and DockRoutine's AI choice."""

    def test_no_config_defaults_to_ship_only(self):
        """A location with no connected_locations/return_to_ship in its
        config behaves exactly like before this feature existed - a single
        immediate exit back to the ship."""
        screen = LocationScreen(config_data={"label": "Station"}, world_width=800, world_height=600)
        self.assertEqual(screen.get_exit_options(), ["ship"])

    def test_connected_locations_come_before_ship(self):
        screen = LocationScreen(config_data={
            "label": "City", "connected_locations": ["wilderness"],
        }, world_width=1600, world_height=1600)
        self.assertEqual(screen.get_exit_options(), ["wilderness", "ship"])

    def test_return_to_ship_false_omits_ship(self):
        screen = LocationScreen(config_data={
            "label": "Wilderness", "connected_locations": ["city"], "return_to_ship": False,
        }, world_width=1600, world_height=1600)
        self.assertEqual(screen.get_exit_options(), ["city"])


class TestDockRoutineExitChoice(unittest.TestCase):
    """Test DockRoutine._choose_exit() - the AI-pilot equivalent of the
    player's exit menu, driven by ROLE_EXIT_PREFERENCE instead of a
    keypress."""

    def _make_ai_ship(self, role):
        return SimpleNamespace(role=role, person=Person(0, 0))

    def _register_test_role(self, role, preference):
        """Register a throwaway role -> preference entry in the real
        ROLE_EXIT_PREFERENCE dict for the duration of one test, so
        "does a role that prefers multiple connected locations behave
        correctly" can be tested as a general mechanism, independent of
        whatever the real game's freighter_pilot preference happens to be
        tuned to right now (see the "wilderness" flavor removed after it
        caused a visiting pilot to visibly glitch in and out of an empty
        room - the mechanism itself was never the problem)."""
        ROLE_EXIT_PREFERENCE[role] = preference
        self.addCleanup(ROLE_EXIT_PREFERENCE.pop, role, None)

    def test_unconfigured_role_always_returns_to_ship(self):
        """A role with no ROLE_EXIT_PREFERENCE entry falls back to
        DEFAULT_EXIT_PREFERENCE - reboards immediately, exactly like every
        pilot did before connected_locations existed."""
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(all_exit_options=lambda: ["wilderness", "ship"])
        ai_ship = self._make_ai_ship(role="patrol_officer")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_configured_role_prefers_connected_location(self):
        self._register_test_role("test_multi_stop_role", ["wilderness", "ship"])
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(all_exit_options=lambda: ["wilderness", "ship"])
        ai_ship = self._make_ai_ship(role="test_multi_stop_role")
        self.assertEqual(routine._choose_exit(ai_ship), "wilderness")

    def test_already_visited_location_is_skipped(self):
        """Regression test: a role preferring both connected locations
        must not pick one it already visited this stop, or it would
        ping-pong between them forever and never reboard."""
        self._register_test_role("test_multi_stop_role", ["city", "ship"])
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(all_exit_options=lambda: ["city", "ship"])
        routine._visited_this_stop = {"city"}
        ai_ship = self._make_ai_ship(role="test_multi_stop_role")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_full_stop_visits_every_connected_location_then_reboards(self):
        """End-to-end regression test for the ping-pong bug: a pilot whose
        role prefers both of two locations that each connect back to the
        other should visit both once, then reboard - never loop forever -
        using the real phase machine (run()), not a reimplementation of it.
        Uses a throwaway test role rather than the real freighter_pilot
        (see _register_test_role) - whether the mechanism terminates
        correctly shouldn't depend on the game's current flavor tuning."""
        self._register_test_role("test_multi_stop_role", ["wilderness", "city", "ship"])
        city_config = {"label": "City", "connected_locations": ["wilderness"], "npcs": []}
        wilderness_config = {"label": "Wilderness", "connected_locations": ["city"], "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={"city": city_config, "wilderness": wilderness_config})

        interior_cache = {}
        def get_interior_screen(landable, key):
            cache_key = (id(landable), key)
            if cache_key not in interior_cache:
                config = landable.interiors.get(key)
                if not config:
                    return None
                world_width, world_height = landable.interior_world_size
                interior_cache[cache_key] = LocationScreen(config_data=config, world_width=world_width, world_height=world_height)
            return interior_cache[cache_key]

        ai_ship = SimpleNamespace(
            role="test_multi_stop_role",
            person=Person(0, 0),
            ashore=False,
            get_interior_screen=get_interior_screen,
            autopilot_active=False,
            engage_seek=lambda target: None,
        )

        routine = DockRoutine(route=[stop])
        routine._begin_walking_in(ai_ship)

        # _visited_this_stop is cleared by _reboard() once the routine
        # actually leaves (so the *next* stop starts with a clean slate) -
        # so the only way to observe "did it visit both first" is to
        # accumulate it frame by frame, not just check its state after
        # the loop exits.
        frames = 0
        visited_history = set()
        while routine.phase != "flying" and frames < 2000:
            visited_history |= routine._visited_this_stop
            routine.run(ai_ship)
            frames += 1

        self.assertEqual(routine.phase, "flying", "Routine got stuck instead of reboarding")
        self.assertEqual(visited_history, {"city", "wilderness"},
                          "Should have visited both connected locations before leaving")
        self.assertFalse(ai_ship.ashore)

    def test_full_stop_with_a_real_character_not_a_fake(self):
        """Same scenario as test_full_stop_visits_every_connected_location_
        then_reboards, but built through the real Character.for_ai_pilot()
        factory (real Ship, real Person, real Possessions/Dialogue) instead
        of a SimpleNamespace fake - proves the composed Character actually
        duck-types as a ship (engage_seek/autopilot_active) and as a body
        (person.x/y) well enough for DockRoutine to drive both ends of it."""
        city_config = {"label": "City", "connected_locations": ["wilderness"], "npcs": []}
        wilderness_config = {"label": "Wilderness", "connected_locations": ["city"], "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={"city": city_config, "wilderness": wilderness_config})

        interior_cache = {}
        def get_interior_screen(landable, key):
            cache_key = (id(landable), key)
            if cache_key not in interior_cache:
                config = landable.interiors.get(key)
                if not config:
                    return None
                world_width, world_height = landable.interior_world_size
                interior_cache[cache_key] = LocationScreen(config_data=config, world_width=world_width, world_height=world_height)
            return interior_cache[cache_key]

        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="freighter",
            graphics=None, pilot={"name": "Elena Voss", "role": "freighter_pilot"},
            route=[stop], get_interior_screen=get_interior_screen,
        )
        self.assertIsInstance(character.routine, DockRoutine)
        character.routine.route = [stop]
        character.routine._route_index = 0
        character.routine._begin_walking_in(character)

        frames = 0
        while character.routine.phase != "flying" and frames < 2000:
            character.routine.run(character)
            frames += 1

        self.assertEqual(character.routine.phase, "flying", "Routine got stuck instead of reboarding")
        self.assertFalse(character.ashore)
        # The ship itself never moved (it's parked, waiting) - only the
        # person walked around on foot.
        self.assertEqual((character.ship.x, character.ship.y), (0, 0))

    def test_multi_hop_graph_routes_through_a_middle_node_to_ship(self):
        """Regression test for the station's concourse/spaceport layout:
        "ship" isn't directly reachable from the room a freighter lands in
        (only the spaceport offers it), so the routine must hop through
        whichever connected location actually leads to the ship - found by
        searching the interiors graph (Landable.interior_adjacency /
        get_ship_entry_key, resolved via TOWARD_SHIP), not wander into an
        unrelated dead end first."""
        hub_config = {"label": "Hub", "connected_locations": ["dead_end", "spaceport"], "return_to_ship": False, "npcs": []}
        dead_end_config = {"label": "Dead End", "connected_locations": ["hub"], "return_to_ship": False, "npcs": []}
        spaceport_config = {"label": "Spaceport", "connected_locations": ["hub"], "return_to_ship": True, "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={
            "hub": hub_config, "dead_end": dead_end_config, "spaceport": spaceport_config,
        })
        routine = DockRoutine(route=[stop])
        routine._location = SimpleNamespace(interior_key="hub", all_exit_options=lambda: ["dead_end", "spaceport"])
        routine._visited_this_stop = {"hub"}
        ai_ship = self._make_ai_ship(role="freighter_pilot")

        choice = routine._choose_exit(ai_ship)
        self.assertEqual(choice, "spaceport", "Should route toward the room that leads to the ship, not the dead end")

        routine._location = SimpleNamespace(interior_key="spaceport", all_exit_options=lambda: ["hub", "ship"])
        routine._visited_this_stop.add("spaceport")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_routes_to_the_ship_room_regardless_of_its_name(self):
        """The room that leads back to the ship isn't necessarily called
        "spaceport" - a different station could name it anything, as long
        as its own return_to_ship is set (Landable.get_ship_entry_key).
        Routing has to key off that, not a literal string - this is the
        scenario that would have failed under the old hardcoded
        ROLE_EXIT_PREFERENCE = ["spaceport", "ship"]."""
        hub_config = {"label": "Hub", "connected_locations": ["docking_bay"], "return_to_ship": False, "npcs": []}
        docking_bay_config = {"label": "Docking Bay", "connected_locations": ["hub"], "return_to_ship": True, "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={"hub": hub_config, "docking_bay": docking_bay_config})
        routine = DockRoutine(route=[stop])
        routine._location = SimpleNamespace(interior_key="hub", all_exit_options=lambda: ["docking_bay"])
        routine._visited_this_stop = {"hub"}
        ai_ship = self._make_ai_ship(role="freighter_pilot")

        self.assertEqual(routine._choose_exit(ai_ship), "docking_bay")

    def test_safety_cap_forces_reboard_when_ship_is_never_reachable(self):
        """If nothing ever leads to "ship" (a misconfigured or future
        role/graph combination this feature hasn't been tuned for), the
        MAX_LATERAL_HOPS cap must still force a reboard rather than wander
        forever - this is what actually caught the corridor<->dormitory
        ping-pong during development, before ROLE_EXIT_PREFERENCE routed
        freighter_pilot through the spaceport."""
        room_a = SimpleNamespace(all_exit_options=lambda: ["room_b"])
        room_b = SimpleNamespace(all_exit_options=lambda: ["room_a"])
        rooms = {"room_a": room_a, "room_b": room_b}

        routine = DockRoutine(route=[])
        routine._location = room_a
        routine._visited_this_stop = {"room_a"}
        ai_ship = self._make_ai_ship(role="patrol_officer")  # no ROLE_EXIT_PREFERENCE entry

        current_key = "room_a"
        for _ in range(MAX_LATERAL_HOPS + 5):
            choice = routine._choose_exit(ai_ship)
            if choice == "ship":
                break
            current_key = choice
            routine._location = rooms[current_key]
            routine._visited_this_stop.add(current_key)
        else:
            self.fail(f"never forced a reboard within {MAX_LATERAL_HOPS + 5} hops")
        self.assertLessEqual(len(routine._visited_this_stop), MAX_LATERAL_HOPS + 1)


class TestFreighterPilotDoesNotDetourIntoEmptyWilderness(unittest.TestCase):
    """Regression test: freighter_pilot's exit preference used to include
    "wilderness", so a freighter landing at the moon would visit city, then
    detour into wilderness (which has no NPC at all) just to stand at its
    entrance for a few seconds before reboarding. If the player happened to
    be looking at wilderness at that moment (having landed there themselves
    while the pilot was in city), the pilot appeared to glitch into
    existence at the entrance and vanish moments later. The real game's
    ROLE_EXIT_PREFERENCE must never route freighter_pilot into wilderness."""

    def test_elena_voss_visits_only_city_then_reboards(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        elena_ship = next(s for s in game_screen.ai_ships if s.person.name == "Elena Voss")
        routine = elena_ship.routine
        routine.route = [game_screen.moon]
        routine._route_index = 0
        routine._begin_walking_in(elena_ship)

        visited_wilderness = False
        frames = 0
        while routine.phase != "flying" and frames < 3000:
            if routine._location is not None and routine._location.interior_key == "wilderness":
                visited_wilderness = True
            routine.run(elena_ship)
            frames += 1

        self.assertEqual(routine.phase, "flying")
        self.assertFalse(visited_wilderness, "Freighter pilot should never detour into the empty wilderness")


class TestIndoorPathfinder(unittest.TestCase):
    """IndoorPathfinder.find_path() - the room-graph router DockRoutine uses
    (see TestDockRoutineRespectsWalls below for the full walking behavior
    this enables)."""

    def test_same_room_returns_direct_goal(self):
        rooms = [{"rect": (0, 0, 200, 200), "label": None}]
        self.assertEqual(IndoorPathfinder.find_path(rooms, (10, 10), (150, 150)), [(150, 150)])

    def test_two_adjacent_rooms_routes_through_the_overlap(self):
        # An L: "Vertical" is x[50,150] y[50,550], "Horizontal" is
        # x[50,550] y[450,550] - they overlap in the x[50,150] y[450,550]
        # square, so the route should pass through its center.
        rooms = [
            {"rect": (50, 50, 100, 500), "label": "Vertical"},
            {"rect": (50, 450, 500, 100), "label": "Horizontal"},
        ]
        path = IndoorPathfinder.find_path(rooms, (100, 100), (500, 500))
        self.assertEqual(path, [(100, 500), (500, 500)])

    def test_three_room_chain_routes_through_each_doorway(self):
        rooms = [
            {"rect": (0, 0, 100, 100), "label": "A"},
            {"rect": (100, 0, 100, 100), "label": "B"},   # shares the x=100 edge with A
            {"rect": (200, 0, 100, 100), "label": "C"},   # shares the x=200 edge with B
        ]
        path = IndoorPathfinder.find_path(rooms, (10, 10), (290, 90))
        self.assertEqual(path, [(100, 50), (200, 50), (290, 90)])

    def test_unreachable_room_falls_back_to_the_direct_goal(self):
        rooms = [
            {"rect": (0, 0, 50, 50), "label": "A"},
            {"rect": (1000, 1000, 50, 50), "label": "B"},  # not adjacent to A at all
        ]
        path = IndoorPathfinder.find_path(rooms, (10, 10), (1010, 1010))
        self.assertEqual(path, [(1010, 1010)])

    def test_point_outside_any_room_falls_back_to_the_direct_goal(self):
        rooms = [{"rect": (0, 0, 50, 50), "label": "A"}]
        path = IndoorPathfinder.find_path(rooms, (5000, 5000), (10, 10))
        self.assertEqual(path, [(10, 10)])

    def test_clear_obstacle_does_not_add_waypoints(self):
        """An obstacle nowhere near the straight line shouldn't perturb the
        path at all - the common case (most walks don't pass near a
        building)."""
        rooms = [{"rect": (0, 0, 1000, 1000), "label": None}]
        obstacles = [(0, 0, 50, 50)]  # far from the (100,100)->(150,150) line
        path = IndoorPathfinder.find_path(rooms, (100, 100), (150, 150), obstacles)
        self.assertEqual(path, [(150, 150)])

    def test_routes_around_a_blocking_obstacle(self):
        """A rect square in the middle of a straight line - the resulting
        path must actually reach the goal without any leg crossing the
        obstacle (checked the same way IndoorPathfinder itself decides
        whether a leg is blocked)."""
        rooms = [{"rect": (0, 0, 1000, 1000), "label": None}]
        obstacles = [(400, 400, 200, 200)]  # centered on the direct line
        start, goal = (300, 500), (700, 500)
        path = IndoorPathfinder.find_path(rooms, start, goal, obstacles)
        self.assertEqual(path[-1], goal)
        points = [start] + path
        for p1, p2 in zip(points, points[1:]):
            self.assertFalse(
                IndoorPathfinder._segment_crosses_rect(p1, p2, obstacles[0]),
                f"Leg {p1}->{p2} still crosses the obstacle",
            )

    def test_routes_around_an_obstacle_directly_between_start_and_goal_on_one_axis(self):
        """The failure case that actually stranded pilots: the goal is
        directly north/south (or east/west) of the start with an obstacle
        square in between, so a straight-line walk's wall-slide has no
        sideways component to try at all. Must still find a real detour."""
        rooms = [{"rect": (0, 0, 1000, 1000), "label": None}]
        obstacles = [(450, 450, 100, 100)]
        start, goal = (500, 300), (500, 700)  # same x as the obstacle's center - dx is 0 the whole way
        path = IndoorPathfinder.find_path(rooms, start, goal, obstacles)
        self.assertEqual(path[-1], goal)
        points = [start] + path
        for p1, p2 in zip(points, points[1:]):
            self.assertFalse(IndoorPathfinder._segment_crosses_rect(p1, p2, obstacles[0]))


class TestDockRoutineRespectsWalls(unittest.TestCase):
    """Regression test: DockRoutine._step_toward() moved a visiting pilot
    in a dead-straight line toward their destination with no collision
    checking at all, unlike the player's own movement - reproducibly
    visible with Kepler's Reach's real station config (confirmed by
    simulating the old unconstrained formula: the pilot spent real frames
    outside every valid room on the way to the bartender). Fixed by giving
    _step_toward the same LocationScreen.can_move_to() wall-sliding check
    the player's movement already uses."""

    def _make_l_shaped_screen(self):
        """Two rooms forming an L: a straight line from the entrance to
        the NPC crosses empty space outside both, but a route that goes
        down the vertical corridor then across the horizontal one stays
        inside the union the whole way - exactly what wall-sliding should
        produce and straight-line movement can't."""
        config = {
            "label": "L-Shaped Test Room", "culture": None,
            "rooms": [
                {"label": "Vertical", "rect": [50, 50, 100, 500]},
                {"label": "Horizontal", "rect": [50, 450, 500, 100]},
            ],
            "npcs": [{"name": "Target", "x": 500, "y": 500, "role": "resident"}],
        }
        screen = LocationScreen(config_data=config, world_width=600, world_height=600)
        screen.rooms = config["rooms"]  # bypass culture-gated room population, see other tests
        screen.entrance_x, screen.entrance_y = 100, 100
        return screen

    def test_pilot_never_leaves_the_walkable_area_walking_an_l_shaped_room(self):
        location = self._make_l_shaped_screen()
        ai_ship = SimpleNamespace(pilot_person=Person(100, 100))
        routine = DockRoutine(route=[])
        routine._location = location
        routine._set_waypoints(ai_ship.pilot_person, (500, 500))  # the NPC, in the far corner of the L

        frames = 0
        while frames < 500:
            if routine._step_toward(ai_ship.pilot_person):
                break
            self.assertTrue(
                location.can_move_to(ai_ship.pilot_person.x, ai_ship.pilot_person.y),
                f"Pilot left the walkable area at ({ai_ship.pilot_person.x}, {ai_ship.pilot_person.y})",
            )
            frames += 1
        else:
            self.fail("Pilot never arrived within 500 frames")


class TestBuildingFootprintCollision(unittest.TestCase):
    """Regression test for the backlog's "Building collision missing"
    bug: player/NPCs used to be able to walk straight through a building's
    drawn silhouette, since can_move_to() only ever checked room walls or
    the open-world bounds. Uses a real building_type from the default
    story's building_types.json (drossholt_bunker: 140x90, anchored
    top-left, so its footprint - see LocationScreen._building_footprint -
    sits at world x:500-640, y:545-635) rather than a synthetic one, so
    this breaks if that config's shape/footprint fields are renamed."""

    def _make_screen_with_bunker(self):
        config = {
            "label": "Test Yard",
            "structures": [{"x": 500, "y": 500, "building_type": "drossholt_bunker"}],
        }
        return LocationScreen(config_data=config, world_width=1600, world_height=1600, story="default")

    def test_footprint_is_computed_from_the_building_type(self):
        location = self._make_screen_with_bunker()
        self.assertEqual(location.building_footprints, [(500.0, 545.0, 140, 90)])

    def test_cannot_walk_into_the_footprint(self):
        location = self._make_screen_with_bunker()
        self.assertFalse(location.can_move_to(570, 590))  # dead center of the bunker

    def test_can_walk_around_the_sides(self):
        location = self._make_screen_with_bunker()
        self.assertTrue(location.can_move_to(480, 590))  # just left of the footprint
        self.assertTrue(location.can_move_to(660, 590))  # just right of the footprint

    def test_can_walk_behind_it(self):
        """North of the building (smaller y) is open ground once past the
        footprint's near edge - this is what lets a character walk behind
        the building and be drawn behind it (see draw()'s y-sort), instead
        of the whole tall silhouette being solid all the way through."""
        location = self._make_screen_with_bunker()
        self.assertTrue(location.can_move_to(570, 400))

    def test_decorative_structures_with_no_building_type_have_no_footprint(self):
        config = {
            "label": "Test Wilderness",
            "structures": [{"type": "circle", "x": 500, "y": 500, "radius": 50}],
        }
        location = LocationScreen(config_data=config, world_width=1600, world_height=1600, story="default")
        self.assertEqual(location.building_footprints, [])
        self.assertTrue(location.can_move_to(500, 500))


class TestDockRoutineRespectsBuildings(unittest.TestCase):
    """Regression test for the same stuck failure mode
    TestDockRoutineRespectsWalls covers for room walls, but triggered by a
    building instead: a moon's city/wilderness interior has structures (see
    LocationScreen.building_footprints) but no rooms at all, so the room
    graph IndoorPathfinder builds never learns about them on its own -
    without also routing around obstacles, a pilot walking straight at an
    NPC on the far side of a building got stuck exactly like Elena Voss used
    to (worst case here: the NPC is directly north/south of the pilot, so
    the wall-slide fallback's axis-only candidates are pure no-ops and never
    move the pilot at all). Uses the real drossholt_bunker building_type
    (see TestBuildingFootprintCollision), not a synthetic one."""

    def _make_screen_with_bunker(self, target_x, target_y):
        config = {
            "label": "Test Yard",
            "structures": [{"x": 500, "y": 500, "building_type": "drossholt_bunker"}],
            "npcs": [{"name": "Target", "x": target_x, "y": target_y, "role": "resident"}],
        }
        return LocationScreen(config_data=config, world_width=1600, world_height=1600, story="default")

    def test_pilot_routes_around_the_building_instead_of_getting_stuck(self):
        # Bunker footprint is x:500-640, y:545-635 (see
        # TestBuildingFootprintCollision) - start directly north of it,
        # target directly south, so dx is 0 for the entire direct line.
        target_x, target_y = 570, 700
        location = self._make_screen_with_bunker(target_x, target_y)
        person = Person(570, 400)
        routine = DockRoutine(route=[])
        routine._location = location
        routine._set_waypoints(person, (target_x, target_y))

        frames = 0
        while frames < 500:
            if routine._step_toward(person):
                break
            self.assertTrue(
                location.can_move_to(person.x, person.y),
                f"Pilot walked into the building (or left the world) at ({person.x}, {person.y})",
            )
            frames += 1
        else:
            self.fail("Pilot never arrived within 500 frames")
        # _step_toward's ARRIVAL_DISTANCE (10) means arrival can land up to
        # that far from the exact target, not pixel-perfect on it.
        self.assertLessEqual(math.hypot(person.x - target_x, person.y - target_y), 10)


class TestWanderRoutineRespectsWalls(unittest.TestCase):
    """WanderRoutine used to move a wandering NPC (resident/roommate/
    traveler role) with zero collision checking at all, unlike DockRoutine's
    visiting pilots - it could wander through a wall or a building. Fixed by
    giving it the same LocationScreen.can_move_to() check (via
    Character.can_move_to, injected by LocationScreen._build_local_character
    - see game/world/character.py), wall-sliding the same way DockRoutine's
    _step_toward does."""

    def test_never_leaves_the_walkable_area_over_many_wander_cycles(self):
        # A single small room - WANDER_RADIUS (40) reaches well past every
        # wall from the center, so without wall-awareness the wanderer would
        # cross one almost immediately.
        config = {
            "label": "Tiny Room", "culture": None,
            "rooms": [{"label": "Room", "rect": [100, 100, 60, 60]}],
        }
        location = LocationScreen(config_data=config, world_width=300, world_height=300)
        location.rooms = config["rooms"]
        person = Person(130, 130)
        character = Character(person, role="resident", can_move_to=location.can_move_to)

        for _ in range(2000):
            character.routine.run(character)
            self.assertTrue(
                location.can_move_to(person.x, person.y),
                f"Wanderer left the walkable area at ({person.x}, {person.y})",
            )

    def test_never_enters_a_building_footprint(self):
        config = {
            "label": "Test Yard",
            "structures": [{"x": 500, "y": 500, "building_type": "drossholt_bunker"}],
        }
        location = LocationScreen(config_data=config, world_width=1600, world_height=1600, story="default")
        # Right against the bunker's near (north) edge, well within
        # WANDER_RADIUS of stepping into it.
        person = Person(570, 540)
        character = Character(person, role="resident", can_move_to=location.can_move_to)

        for _ in range(2000):
            character.routine.run(character)
            self.assertTrue(location.can_move_to(person.x, person.y))


class TestPossessions(unittest.TestCase):
    """Test Possessions - credits/ships/loans, composed onto every Person
    (see game/world/person.py), not just the player."""

    def test_starts_empty(self):
        possessions = Possessions()
        self.assertEqual(possessions.credits, 0)
        self.assertEqual(possessions.owned_ships, [])
        self.assertEqual(possessions.loans, [])

    def test_can_afford_and_spend(self):
        possessions = Possessions(credits=1200)
        self.assertTrue(possessions.can_afford(1200))
        self.assertFalse(possessions.can_afford(1201))
        possessions.spend(1200)
        self.assertEqual(possessions.credits, 0)
        possessions.earn(500)
        self.assertEqual(possessions.credits, 500)

    def test_add_ship(self):
        possessions = Possessions()
        possessions.add_ship("shuttle")
        self.assertEqual(possessions.owned_ships, ["shuttle"])

    def test_take_loan_adds_credits_and_records_loan(self):
        possessions = Possessions()
        possessions.take_loan("Station Credit Union", 1200)
        self.assertEqual(possessions.credits, 1200)
        self.assertEqual(possessions.loans, [{"lender": "Station Credit Union", "principal": 1200}])

    def test_get_state_roundtrips_through_from_state(self):
        possessions = Possessions(credits=300, owned_ships=["shuttle"], loans=[{"lender": "X", "principal": 100}])
        restored = Possessions.from_state(possessions.get_state())
        self.assertEqual(restored.credits, 300)
        self.assertEqual(restored.owned_ships, ["shuttle"])
        self.assertEqual(restored.loans, [{"lender": "X", "principal": 100}])

    def test_restore_from_mutates_in_place(self):
        """restore_from() must update the existing object, not replace it -
        every screen holding a reference to the player's one Possessions
        (see SpaceScreen.get_interior_screen) depends on that identity
        staying the same across a load."""
        possessions = Possessions(credits=50)
        same_object = possessions
        possessions.restore_from({"credits": 900, "owned_ships": ["patrol"], "loans": []})
        self.assertIs(possessions, same_object)
        self.assertEqual(possessions.credits, 900)
        self.assertEqual(possessions.owned_ships, ["patrol"])


class TestPossessionsInventory(unittest.TestCase):
    """Test Possessions' cargo/items/outfit tracking - added alongside the
    inventory/buying-selling/outfitting feature. Cargo capacity itself lives
    on Ship, not here (Possessions stays config-free per the story/save
    split), so these tests only cover the plain-data bookkeeping."""

    def test_cargo_add_and_remove(self):
        possessions = Possessions()
        possessions.add_cargo("ore", 5)
        possessions.add_cargo("ore", 3)
        self.assertEqual(possessions.cargo["ore"], 8)
        self.assertEqual(possessions.cargo_quantity_total(), 8)
        possessions.remove_cargo("ore", 3)
        self.assertEqual(possessions.cargo["ore"], 5)

    def test_remove_cargo_down_to_zero_drops_the_key(self):
        possessions = Possessions()
        possessions.add_cargo("ore", 5)
        possessions.remove_cargo("ore", 5)
        self.assertNotIn("ore", possessions.cargo)

    def test_items_are_independent_of_cargo(self):
        possessions = Possessions()
        possessions.add_item("repair_kit", 1)
        possessions.add_cargo("ore", 5)
        self.assertEqual(possessions.items, {"repair_kit": 1})
        self.assertEqual(possessions.cargo, {"ore": 5})

    def test_add_outfit_and_install(self):
        possessions = Possessions()
        possessions.add_outfit("laser_cannon")
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])
        possessions.install_outfit("weapon_1", "laser_cannon")
        self.assertEqual(possessions.owned_outfits, [])
        self.assertEqual(possessions.installed_outfits, {"weapon_1": "laser_cannon"})

    def test_installing_into_an_occupied_slot_bumps_the_old_outfit_back_to_owned(self):
        possessions = Possessions(owned_outfits=["laser_cannon", "afterburner"])
        possessions.install_outfit("weapon_1", "laser_cannon")
        bumped = possessions.install_outfit("weapon_1", "afterburner")
        self.assertEqual(bumped, "laser_cannon")
        self.assertEqual(possessions.installed_outfits, {"weapon_1": "afterburner"})
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])

    def test_uninstall_outfit_returns_it_to_owned(self):
        possessions = Possessions(installed_outfits={"weapon_1": "laser_cannon"})
        removed = possessions.uninstall_outfit("weapon_1")
        self.assertEqual(removed, "laser_cannon")
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])

    def test_uninstall_empty_slot_is_a_noop(self):
        possessions = Possessions()
        self.assertIsNone(possessions.uninstall_outfit("weapon_1"))
        self.assertEqual(possessions.owned_outfits, [])

    def test_uninstall_all_outfits_moves_everything_back_to_owned(self):
        possessions = Possessions(
            owned_outfits=["reinforced_hull"],
            installed_outfits={"weapon_1": "laser_cannon", "utility_1": "cargo_expansion"},
        )
        possessions.uninstall_all_outfits()
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(sorted(possessions.owned_outfits), ["cargo_expansion", "laser_cannon", "reinforced_hull"])

    def test_uninstall_all_outfits_is_a_noop_with_nothing_installed(self):
        possessions = Possessions(owned_outfits=["laser_cannon"])
        possessions.uninstall_all_outfits()
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])

    def test_inventory_fields_roundtrip_through_save_state(self):
        possessions = Possessions(
            owned_outfits=["afterburner"],
            installed_outfits={"weapon_1": "laser_cannon"},
            cargo={"ore": 5},
            items={"repair_kit": 1},
        )
        restored = Possessions.from_state(possessions.get_state())
        self.assertEqual(restored.owned_outfits, ["afterburner"])
        self.assertEqual(restored.installed_outfits, {"weapon_1": "laser_cannon"})
        self.assertEqual(restored.cargo, {"ore": 5})
        self.assertEqual(restored.items, {"repair_kit": 1})

    def test_restore_from_defaults_missing_inventory_keys_for_old_saves(self):
        """A save made before this feature existed has no cargo/items/outfit
        keys at all - restoring it must not error, and should leave a
        freshly-constructed Possessions' empty defaults in place."""
        possessions = Possessions()
        possessions.restore_from({"credits": 500, "owned_ships": ["shuttle"], "loans": []})
        self.assertEqual(possessions.cargo, {})
        self.assertEqual(possessions.items, {})
        self.assertEqual(possessions.owned_outfits, [])
        self.assertEqual(possessions.installed_outfits, {})


class TestShipOutfits(unittest.TestCase):
    """Test Ship.apply_outfits() - stat modifiers stack additively on top of
    apply_ship_type()'s base stats, and never zero out a stat an outfit
    doesn't mention (same contract apply_ship_type itself documents)."""

    def test_apply_outfits_with_no_outfits_leaves_base_stats_unchanged(self):
        ship = Ship(0, 0)
        ship.apply_ship_type({"max_thrust": 0.1, "max_velocity": 2.0, "rotation_speed": 4})
        ship.apply_outfits([])
        self.assertEqual(ship.acceleration_magnitude, 0.1)
        self.assertEqual(ship.max_velocity, 2.0)
        self.assertEqual(ship.rotation_speed, 4)

    def test_single_outfit_modifier_stacks_onto_base_stat(self):
        ship = Ship(0, 0)
        ship.apply_ship_type({"max_thrust": 0.1, "max_velocity": 2.0, "rotation_speed": 4})
        ship.apply_outfits([{"stat_modifiers": {"max_velocity": 1.5}}])
        self.assertAlmostEqual(ship.max_velocity, 3.5)
        self.assertEqual(ship.acceleration_magnitude, 0.1)  # unmentioned stat untouched

    def test_multiple_outfits_stack_together(self):
        ship = Ship(0, 0)
        ship.apply_ship_type({"max_thrust": 0.1, "max_velocity": 2.0, "rotation_speed": 4})
        ship.apply_outfits([
            {"stat_modifiers": {"max_velocity": 1.5, "max_thrust": 0.05}},
            {"stat_modifiers": {"rotation_speed": -1}},
        ])
        self.assertAlmostEqual(ship.max_velocity, 3.5)
        self.assertAlmostEqual(ship.acceleration_magnitude, 0.15)
        self.assertEqual(ship.rotation_speed, 3)

    def test_cargo_capacity_set_by_ship_type_and_boosted_by_outfits(self):
        ship = Ship(0, 0)
        ship.apply_ship_type({"cargo_capacity": 10})
        ship.apply_outfits([{"stat_modifiers": {"cargo_capacity": 20}}])
        self.assertEqual(ship.cargo_capacity, 30)

    def test_stacked_negative_modifiers_are_clamped_to_a_safe_floor_not_zero(self):
        """Regression test: the freighter's base rotation_speed (1) plus a
        Cargo Expansion Module's -1 rotation modifier landed on exactly 0 -
        a ship that could never turn at all. Same floor applies to thrust/
        velocity/cargo so no stat can go to zero or negative from stacking."""
        ship = Ship(0, 0)
        ship.apply_ship_type({"max_thrust": 0.1, "max_velocity": 2.0, "rotation_speed": 1, "cargo_capacity": 80})
        ship.apply_outfits([{"stat_modifiers": {"rotation_speed": -1, "max_velocity": -3, "max_thrust": -1, "cargo_capacity": -100}}])
        self.assertGreater(ship.rotation_speed, 0)
        self.assertGreater(ship.max_velocity, 0)
        self.assertGreater(ship.acceleration_magnitude, 0)
        self.assertEqual(ship.cargo_capacity, 0)  # cargo has no "must always move a bit" floor, just can't go negative


class TestShopMenu(unittest.TestCase):
    """Test ShopMenu's buy/sell logic against the real "default" story's
    commodities.json/items.json (ore costs 12cr, repair_kit costs 150cr) -
    same convention as other config-dependent tests that pin to real story
    data rather than reimplementing get_commodity()/get_item() with a fake.
    Only the transaction/navigation logic is tested here, not draw() - see
    CLAUDE.md's "don't test UI rendering" and the fact that no other full
    menu class (PossessionsMenu, ConfirmDialog, LocationSelector) has a
    draw() test either."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_buying_a_commodity_spends_credits_and_adds_cargo(self):
        possessions = Possessions(credits=100)
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        shop._transact("ore")
        self.assertEqual(possessions.credits, 88)
        self.assertEqual(possessions.cargo, {"ore": 1})

    def test_buying_without_enough_credits_is_a_noop(self):
        possessions = Possessions(credits=5)
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        shop._transact("ore")
        self.assertEqual(possessions.credits, 5)
        self.assertEqual(possessions.cargo, {})

    def test_buying_a_commodity_at_full_cargo_capacity_is_a_noop(self):
        possessions = Possessions(credits=100, cargo={"ore": 10})
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        shop._transact("ore")
        self.assertEqual(possessions.credits, 100)  # unchanged - purchase blocked
        self.assertEqual(possessions.cargo, {"ore": 10})

    def test_selling_a_commodity_earns_credits_at_the_sell_multiplier(self):
        possessions = Possessions(credits=0, cargo={"ore": 3})
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"], "sell_multiplier": 0.5}, cargo_capacity=10)
        shop.mode = "sell"
        shop._transact("ore")
        self.assertEqual(possessions.credits, 6)  # 12cr base_price * 0.5
        self.assertEqual(possessions.cargo, {"ore": 2})

    def test_items_are_not_capacity_limited(self):
        possessions = Possessions(credits=200)
        shop = ShopMenu(possessions, "default", {"type": "items", "stock": ["repair_kit"]}, cargo_capacity=0)
        shop._transact("repair_kit")
        self.assertEqual(possessions.credits, 50)
        self.assertEqual(possessions.items, {"repair_kit": 1})

    def test_tab_toggles_buy_sell_mode(self):
        possessions = Possessions()
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]})
        self.assertEqual(shop.mode, "buy")
        import pygame as mocked_pygame
        shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_TAB)])
        self.assertEqual(shop.mode, "sell")
        shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_TAB)])
        self.assertEqual(shop.mode, "buy")

    def test_left_right_browse_the_grid_without_changing_mode(self):
        """Left/Right/Up/Down navigate the icon grid now (see IconGrid) -
        they used to toggle Buy/Sell, which Tab does instead."""
        possessions = Possessions()
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore", "medicine", "fuel_cells"]})
        import pygame as mocked_pygame
        shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RIGHT)])
        self.assertEqual(shop.mode, "buy")
        self.assertEqual(shop.buy_list.current(), "medicine")

    def test_escape_closes(self):
        import pygame as mocked_pygame
        shop = ShopMenu(Possessions(), "default", {"type": "commodities", "stock": ["ore"]})
        result = shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_ESCAPE)])
        self.assertEqual(result, "close")

    def test_empty_stock_shop_can_still_sell_owned_cargo_at_a_premium(self):
        """A shop with an empty "stock" (e.g. sol_alpha.json's Ilsa Farrow,
        who only buys - see docs/BACKLOG.md-adjacent trade-loop design) has
        nothing on the Buy tab, but the Sell tab isn't driven by "stock" at
        all - it always lists whatever's in possessions.cargo, so a
        buy-nothing/sell-only shop still works and can price above the
        commodity's own base_price to make a return trip profitable."""
        possessions = Possessions(credits=0, cargo={"ore": 2})
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": [], "sell_multiplier": 1.2})
        self.assertIsNone(shop.buy_list.current())  # nothing to buy
        shop.mode = "sell"
        self.assertEqual(shop.sell_list.items, ["ore"])
        shop._transact("ore")
        self.assertEqual(possessions.credits, 14)  # 12cr base_price * 1.2, truncated
        self.assertEqual(possessions.cargo, {"ore": 1})

    def test_enter_transacts_the_selected_item(self):
        import pygame as mocked_pygame
        possessions = Possessions(credits=100)
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertEqual(possessions.cargo, {"ore": 1})


class TestShipBrowserMenu(unittest.TestCase):
    """Test ShipBrowserMenu against the real "default" story's ship_types.json
    (shuttle costs 1200cr) - the on_buy callback is the injection point that
    lets this menu perform the same mutation as LocationScreen.buy_ship()
    without owning Possessions/on_ship_purchased itself."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_enter_opens_a_confirm_dialog_instead_of_buying_immediately(self):
        import pygame as mocked_pygame
        bought = []
        possessions = Possessions(credits=1200)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle"]}, on_buy=bought.append)
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertIsNotNone(menu.confirm)
        self.assertEqual(bought, [])  # not yet - still waiting on confirmation
        self.assertEqual(possessions.credits, 1200)

    def test_confirming_calls_on_buy_with_the_selected_ship_type(self):
        import pygame as mocked_pygame
        bought = []
        possessions = Possessions(credits=1200)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle"]}, on_buy=bought.append)
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_y)])
        self.assertEqual(bought, ["shuttle"])
        self.assertIsNone(menu.confirm)

    def test_cannot_afford_blocks_enter_from_opening_confirm(self):
        import pygame as mocked_pygame
        bought = []
        possessions = Possessions(credits=0)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle"]}, on_buy=bought.append)
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertIsNone(menu.confirm)
        self.assertEqual(bought, [])

    def test_escape_closes(self):
        import pygame as mocked_pygame
        menu = ShipBrowserMenu(Possessions(), "default", {"stock": ["shuttle"]}, on_buy=lambda x: None)
        result = menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_ESCAPE)])
        self.assertEqual(result, "close")

    def test_navigation_does_not_skip_unaffordable_ships(self):
        """Regression test: the preview used to be tied to a cursor that
        skipped over unaffordable ships whenever at least one WAS
        affordable, so you couldn't preview (or even see) a ship you
        couldn't yet buy. shuttle costs 1200cr, freighter costs 4500cr -
        affording the shuttle only must not block navigating onto/
        previewing the freighter."""
        import pygame as mocked_pygame
        possessions = Possessions(credits=1200)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle", "freighter"]}, on_buy=lambda x: None)
        self.assertEqual(menu.grid.current(), "shuttle")
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_DOWN)])
        self.assertEqual(menu.grid.current(), "freighter")


class TestApproximateSizeLabel(unittest.TestCase):
    """Test the Shipyard preview's "Approximate Size" bucketing - a plain
    world-units number (graphics.json's "size") means little to a player,
    so it's shown as a coarse label instead."""

    def test_small_ship(self):
        self.assertEqual(_approximate_size_label({"size": 10}), "Small")  # shuttle

    def test_medium_ship_at_the_small_boundary(self):
        self.assertEqual(_approximate_size_label({"size": 15}), "Medium")

    def test_large_ship(self):
        self.assertEqual(_approximate_size_label({"size": 35}), "Large")  # freighter

    def test_massive_ship_above_every_threshold(self):
        self.assertEqual(_approximate_size_label({"size": 100}), "Massive")

    def test_missing_size_falls_back_to_the_default_of_15(self):
        self.assertEqual(_approximate_size_label({}), "Medium")


class TestIconGrid(unittest.TestCase):
    """Test IconGrid's row-major navigation - the grid layout ShopMenu uses
    for its buy/sell lists (see docs/BACKLOG.md's icon-grid item)."""

    def test_right_and_left_wrap_across_row_boundaries(self):
        grid = IconGrid(["a", "b", "c", "d"], columns=2, max_rows=2)
        grid.selected = 1  # "b", end of row 0
        grid.handle_key(pygame_mock.K_RIGHT)
        self.assertEqual(grid.current(), "c")  # wraps onto row 1
        grid.handle_key(pygame_mock.K_LEFT)
        self.assertEqual(grid.current(), "b")

    def test_left_from_first_item_wraps_to_last(self):
        grid = IconGrid(["a", "b", "c"], columns=2, max_rows=2)
        grid.selected = 0
        grid.handle_key(pygame_mock.K_LEFT)
        self.assertEqual(grid.current(), "c")

    def test_down_jumps_a_full_row_and_clamps_on_a_ragged_last_row(self):
        grid = IconGrid(["a", "b", "c"], columns=2, max_rows=2)  # row 1 has only "c"
        grid.selected = 1  # "b"
        grid.handle_key(pygame_mock.K_DOWN)
        self.assertEqual(grid.current(), "c")  # clamped, not wrapped past the end

    def test_up_from_top_row_clamps_to_first_row(self):
        grid = IconGrid(["a", "b", "c", "d"], columns=2, max_rows=2)
        grid.selected = 1  # "b", already top row
        grid.handle_key(pygame_mock.K_UP)
        self.assertEqual(grid.current(), "b")  # candidate index negative - clamps in place

    def test_current_returns_none_when_empty(self):
        grid = IconGrid([], columns=3, max_rows=2)
        self.assertIsNone(grid.current())
        grid.handle_key(pygame_mock.K_RIGHT)  # must not raise


class TestOutfittingMenu(unittest.TestCase):
    """Test OutfittingMenu's keyboard-driven equip/unequip and slot/type
    filtering against the real "default" story's patrol ship type (slots:
    weapon_1/weapon, utility_1/utility) and ship_outfits.json (laser_cannon/
    weapon, afterburner/engine, cargo_expansion/utility). Mouse drag-and-
    drop itself isn't tested here - see CLAUDE.md's "don't test UI
    rendering" and the plan's note that the underlying Possessions.
    install_outfit/uninstall_outfit swap logic is already covered by
    TestPossessionsInventory; this class only covers the menu's own
    slot-focus/filtering/callback logic."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_compatible_owned_outfits_filters_by_slot_type(self):
        possessions = Possessions(owned_outfits=["laser_cannon", "afterburner"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        self.assertEqual(menu._compatible_owned_outfits("weapon"), ["laser_cannon"])
        self.assertEqual(menu._compatible_owned_outfits("engine"), ["afterburner"])
        self.assertEqual(menu._compatible_owned_outfits("shield"), [])

    def test_enter_on_empty_slot_opens_picker_filtered_to_compatible_outfits(self):
        import pygame as mocked_pygame
        possessions = Possessions(owned_outfits=["laser_cannon", "afterburner"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        menu.slot_focus = 0  # weapon_1, per ship_types.json's patrol entry
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertIsNotNone(menu.picker)
        self.assertEqual(menu.picker.items, ["laser_cannon"])

    def test_picker_enter_installs_and_calls_outfits_changed_callback(self):
        import pygame as mocked_pygame
        changed = []
        possessions = Possessions(owned_outfits=["laser_cannon"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol", on_outfits_changed=lambda: changed.append(True))
        menu.slot_focus = 0
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertEqual(possessions.installed_outfits, {"weapon_1": "laser_cannon"})
        self.assertEqual(possessions.owned_outfits, [])
        self.assertEqual(changed, [True])

    def test_enter_on_occupied_slot_uninstalls_and_calls_callback(self):
        import pygame as mocked_pygame
        changed = []
        possessions = Possessions(installed_outfits={"weapon_1": "laser_cannon"})
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol", on_outfits_changed=lambda: changed.append(True))
        menu.slot_focus = 0
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])
        self.assertEqual(changed, [True])

    def test_enter_on_empty_slot_with_no_compatible_outfits_does_not_open_picker(self):
        import pygame as mocked_pygame
        possessions = Possessions(owned_outfits=["afterburner"])  # engine, not weapon
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        menu.slot_focus = 0  # weapon_1
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertIsNone(menu.picker)

    def test_buying_an_outfit_spends_credits_and_adds_to_owned(self):
        possessions = Possessions(credits=1000)
        menu = OutfittingMenu(possessions, "default", {"stock": ["laser_cannon"]}, None)
        menu._buy_outfit("laser_cannon")
        self.assertEqual(possessions.credits, 200)  # 1000 - 800cr
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])

    def test_buy_grid_navigation_does_not_skip_unaffordable_outfits(self):
        """laser_cannon costs 800cr, afterburner costs 1500cr - affording
        only the cannon must not block browsing onto the afterburner (same
        preview-vs-selection fix as ShopMenu/ShipBrowserMenu)."""
        import pygame as mocked_pygame
        possessions = Possessions(credits=800)
        menu = OutfittingMenu(possessions, "default", {"stock": ["laser_cannon", "afterburner"]}, None)
        self.assertEqual(menu.buy_grid.current(), "laser_cannon")
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RIGHT)])
        self.assertEqual(menu.buy_grid.current(), "afterburner")

    def test_icon_for_defaults_to_slot_type_when_outfit_has_no_icon_shape(self):
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, None)
        icon_shape, icon_color = menu._icon_for("laser_cannon")  # weapon slot, no icon_shape in config
        self.assertEqual(icon_shape, "blade")
        self.assertEqual(icon_color, SLOT_COLORS["weapon"])

    def test_left_right_switches_focus_column(self):
        """Left/Right switches slot-diagram-vs-owned-list focus on the
        Install tab now (Tab moved to the top-level Buy/Install switch, to
        free Left/Right for the Buy tab's icon grid navigation)."""
        import pygame as mocked_pygame
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, "patrol")
        self.assertEqual(menu.focus_column, "slots")
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_LEFT)])
        self.assertEqual(menu.focus_column, "owned")

    def test_tab_switches_buy_install_tab(self):
        import pygame as mocked_pygame
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, "patrol")
        self.assertEqual(menu.tab, "install")
        menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_TAB)])
        self.assertEqual(menu.tab, "buy")

    def test_no_ship_defaults_to_buy_tab(self):
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, None)
        self.assertEqual(menu.tab, "buy")
        self.assertEqual(menu.slots, [])

    def test_escape_closes(self):
        import pygame as mocked_pygame
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, "patrol")
        result = menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_ESCAPE)])
        self.assertEqual(result, "close")


class TestDialogue(unittest.TestCase):
    """Test Dialogue's conversation tree - both the backward-compatible
    flat shape (from_flat) and real branching."""

    def test_from_flat_every_option_closes(self):
        """Matches the old flat greeting+options behavior exactly - any
        option chosen just ends the conversation."""
        dialogue = Dialogue.from_flat("Guard", "Welcome.", ["Thanks", "Leave"])
        self.assertEqual(dialogue.current_text(), "Welcome.")
        self.assertEqual([o["label"] for o in dialogue.current_options()], ["Thanks", "Leave"])
        self.assertTrue(dialogue.choose(0))
        self.assertTrue(dialogue.choose(1))

    def test_tree_advances_to_next_node(self):
        dialogue = Dialogue("Bartender", {
            "start": {"text": "What'll it be?", "options": [
                {"label": "Order a drink", "next": "drink"},
                {"label": "Leave", "next": None},
            ]},
            "drink": {"text": "Cheers.", "options": [
                {"label": "Thanks", "next": None},
            ]},
        })
        closed = dialogue.choose(0)
        self.assertFalse(closed)
        self.assertEqual(dialogue.current_node, "drink")
        self.assertEqual(dialogue.current_text(), "Cheers.")
        self.assertTrue(dialogue.choose(0))

    def test_tree_can_loop_back_to_an_earlier_node(self):
        dialogue = Dialogue("Bartender", {
            "start": {"text": "What'll it be?", "options": [{"label": "Chat", "next": "chat"}]},
            "chat": {"text": "...", "options": [{"label": "Back", "next": "start"}]},
        })
        dialogue.choose(0)
        dialogue.choose(0)
        self.assertEqual(dialogue.current_node, "start")


class _FakeFont:
    """Stand-in for pygame.font.Font in wrap-width tests - width is just
    character count, so expected wrap points are exact and don't depend on
    real font metrics (pygame is mocked in this whole test module anyway)."""
    def size(self, text):
        return (len(text), 10)


class TestWrapText(unittest.TestCase):
    """Test utils._wrap_text() - shared by StorySelector and Dialogue (see
    Dialogue.draw()) so long NPC lines wrap inside their box instead of
    running off the edge."""

    def test_short_text_stays_one_line(self):
        self.assertEqual(utils._wrap_text(_FakeFont(), "Hello there", 100), ["Hello there"])

    def test_wraps_at_max_width(self):
        lines = utils._wrap_text(_FakeFont(), "one two three four", 8)
        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(len(line), 8)
        self.assertEqual(" ".join(lines), "one two three four")

    def test_single_long_word_is_not_split(self):
        """A word longer than max_width on its own still isn't broken mid-word."""
        self.assertEqual(utils._wrap_text(_FakeFont(), "supercalifragilistic", 5), ["supercalifragilistic"])


class TestCharacterAIPilotDialogue(unittest.TestCase):
    """Regression test: talking to a visiting AI pilot (e.g. Elena Voss)
    while docked crashed the game - the pilot's Dialogue was once built
    with the old flat (name, [greeting], options) constructor after
    Dialogue became a tree, so current_text() indexed a list with a string
    key and raised. Character.for_ai_pilot() is the sole builder now."""

    def test_pilot_dialogue_is_usable(self):
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="freighter", graphics=None,
            pilot={"name": "Elena Voss", "personality": "Blunt and unhurried."},
            route=[], get_interior_screen=None,
        )
        dialogue = character.person.dialogue
        self.assertEqual(dialogue.current_text(), "Blunt and unhurried.")
        self.assertEqual([o["label"] for o in dialogue.current_options()], ["Nod", "Leave"])
        self.assertTrue(dialogue.choose(0))


class TestExplorerRoutine(unittest.TestCase):
    """ExplorerRoutine migrates a Character between two SystemState.ai_ships
    lists and orbits something in whichever system it currently occupies -
    the mechanism the "Allow NPCs to jump between systems" backlog item and
    multi-system simulation both rely on."""

    @staticmethod
    def _make_system(offset_x, offset_y):
        station = Landable(offset_x, offset_y, graphics={}, interiors={})
        moon = Landable(offset_x + 500, offset_y, graphics={}, interiors={})
        return SystemState(station, moon, central_star=None, celestial_bodies=[], ai_ships=[])

    def test_starts_by_orbiting_something_in_its_home_system(self):
        systems = {"a": self._make_system(0, 0), "b": self._make_system(1000, 1000)}
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="shuttle", graphics=None,
            pilot={"name": "Juno Vale", "role": "explorer"}, route=[],
            get_interior_screen=None, systems=systems, system_id="a",
        )
        systems["a"].ai_ships.append(character)  # mimics _build_system_state's own append after construction

        self.assertEqual(character.system_id, "a")
        self.assertTrue(character.autopilot_active, "Should already be orbiting something in its home system")

    def test_migrates_to_another_system_once_its_timer_expires(self):
        systems = {"a": self._make_system(0, 0), "b": self._make_system(1000, 1000)}
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="shuttle", graphics=None,
            pilot={"name": "Juno Vale", "role": "explorer"}, route=[],
            get_interior_screen=None, systems=systems, system_id="a",
        )
        systems["a"].ai_ships.append(character)

        character.routine._timer = 1  # force the next update() to start a jump
        # Migration now only happens once the jump animation finishes (align,
        # bounded by 180deg / (rotation_speed*3) <= 12 frames at the default
        # rotation_speed of 5, then JUMP_TRAVEL_FRAMES=150) - 200 comfortably
        # clears that regardless of the animation's random heading.
        for _ in range(200):
            character.update()
            if character.system_id == "b":
                break

        self.assertEqual(character.system_id, "b", "Only system 'b' exists as an 'other' system to jump to")
        self.assertNotIn(character, systems["a"].ai_ships)
        self.assertIn(character, systems["b"].ai_ships)
        self.assertTrue(character.autopilot_active, "Should be orbiting something in the new system")
        self.assertFalse(character.jumping, "Jump animation should have finished")

    def test_jump_plays_an_align_and_travel_animation_before_migrating(self):
        """Regression: ExplorerRoutine used to migrate the Character the
        instant its timer expired - a silent teleport, with no visible
        transition. It should now wind up and fly off the same way the
        player's own jump does (see JumpDrive): staying put in the origin
        system, autopilot off and ship-driven, for the animation's
        duration before it actually migrates."""
        systems = {"a": self._make_system(0, 0), "b": self._make_system(1000, 1000)}
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="shuttle", graphics=None,
            pilot={"name": "Juno Vale", "role": "explorer"}, route=[],
            get_interior_screen=None, systems=systems, system_id="a",
        )
        systems["a"].ai_ships.append(character)

        character.routine._timer = 1
        character.update()  # begins the jump this frame

        self.assertTrue(character.jumping)
        self.assertFalse(character.autopilot_active, "Autopilot must be off so it can't fight the jump heading")
        self.assertEqual(character.system_id, "a", "Still in the origin system mid-animation")
        self.assertIn(character, systems["a"].ai_ships)

        for _ in range(200):
            character.update()
            if not character.jumping:
                break

        self.assertFalse(character.jumping)
        self.assertEqual(character.system_id, "b")

    def test_single_system_story_just_keeps_orbiting_at_home(self):
        """No "other" system to jump to - should orbit again in the same
        system rather than erroring or vanishing from every list."""
        systems = {"a": self._make_system(0, 0)}
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="shuttle", graphics=None,
            pilot={"name": "Juno Vale", "role": "explorer"}, route=[],
            get_interior_screen=None, systems=systems, system_id="a",
        )
        systems["a"].ai_ships.append(character)

        character.routine._timer = 1
        character.routine.run(character)

        self.assertEqual(character.system_id, "a")
        self.assertIn(character, systems["a"].ai_ships)
        self.assertEqual(len(systems["a"].ai_ships), 1, "Must not be duplicated into the list")


class TestMultiSystemSimulation(unittest.TestCase):
    """Regression coverage for simulating every system a story defines, not
    just whichever one the player currently occupies (see SystemState and
    SpaceScreen.systems) - previously, a system the player wasn't in didn't
    exist as live objects at all until re-visited, which reset its AI ships
    back to their config-file spawn points every time."""

    def test_background_system_ai_ships_keep_moving(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        background_ship = game_screen.systems["keplers_reach"].ai_ships[0]
        before = (background_ship.x, background_ship.y)

        # ai_ships[0] here is a drossholt_freighter (rotation_speed 1 deg/frame -
        # see ship_types.json), and Character.for_ai_pilot gives every AI ship a
        # random starting facing (character.py). SeekMode doesn't thrust until
        # it's turned within 10 degrees of its target heading, so a worst-case
        # starting angle (~180 degrees off) needs up to 171 frames of pure
        # turning before the ship moves at all - confirmed by sweeping every
        # starting angle 0-360 against this same rotation_speed. 120 frames
        # made this flaky (~1 in 4) purely on the random starting angle; 250
        # comfortably clears the proven worst case.
        for _ in range(250):
            game_screen.update_physics()

        self.assertNotEqual((background_ship.x, background_ship.y), before,
                             "AI ship in a system the player isn't in should still be moving")

    def test_jumping_does_not_rebuild_the_destination_system(self):
        """Jumping used to reload the destination system's config from
        scratch (_load_system_content), discarding any progress its AI
        ships had already made while simulating in the background."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        destination_state = game_screen.systems["keplers_reach"]
        for _ in range(120):
            game_screen.update_physics()
        moved_position = (destination_state.ai_ships[0].x, destination_state.ai_ships[0].y)

        game_screen.selected_system_id = "keplers_reach"
        game_screen._begin_jump()
        game_screen._complete_jump()

        self.assertIs(game_screen.systems["keplers_reach"], destination_state,
                       "Must reuse the same SystemState, not rebuild a fresh one")
        self.assertEqual((game_screen.ai_ships[0].x, game_screen.ai_ships[0].y), moved_position)

    def test_save_restore_round_trip_survives_a_migrated_ai_ship(self):
        """get_state()/restore_state() key ai_ships by pilot name and record
        which system each is in (see SAVE_SYSTEM.md) specifically so an
        ExplorerRoutine-driven pilot's system can round-trip through a save
        - a plain per-system list index can't survive it moving lists."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.systems["sol_alpha"].ai_ships if s.person.name == "Juno Vale")
        # Simulate it having wandered off to the other system already.
        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"
        explorer.x, explorer.y = 4242, 1337

        state = game_screen.get_state()
        self.assertEqual(state["ai_ships"]["Juno Vale"]["system_id"], "keplers_reach")

        fresh = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        fresh.restore_state(state)

        self.assertNotIn(explorer.person.name, [s.person.name for s in fresh.systems["sol_alpha"].ai_ships])
        restored = next(s for s in fresh.systems["keplers_reach"].ai_ships if s.person.name == "Juno Vale")
        self.assertEqual((restored.x, restored.y), (4242, 1337))
        self.assertEqual(restored.system_id, "keplers_reach")

    def test_targeting_a_ship_that_jumps_away_clears_the_target(self):
        """Regression: a targeted AI ship migrating to another system (see
        ExplorerRoutine._migrate) used to leave the target selected -
        targetable_objects (built once per _activate_system) still held
        the stale tuple referencing it, and that Character keeps updating
        every frame regardless of which system it's in (see
        SystemState.update_physics), so the brackets/arrow kept tracking
        its position in whatever system it jumped to - a totally
        unrelated part of the same game-space coordinates. Losing the
        ship should clear the target instead of following it there."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Juno Vale")

        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        filtered = game_screen._filtered_targets()
        game_screen.current_target = next(i for i, (_, obj) in enumerate(filtered) if obj is explorer)
        self.assertIs(game_screen._get_target_object(), explorer)

        # Simulate the ship having jumped away, the way ExplorerRoutine._migrate does.
        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"

        game_screen.update_physics()

        self.assertIsNone(game_screen.current_target, "Target should be lost once the ship leaves this system")
        self.assertIsNone(game_screen._get_target_object())

    def test_autopilot_seeking_a_ship_that_jumps_away_disengages(self):
        """Regression: engaging autopilot on an AI ship (engage_seek, the
        'G' key) sets player.autopilot_target independently of
        current_target/targetable_objects - clearing current_target alone
        (see test above) left the player's autopilot still committed to
        chasing that Character's position in whatever system it jumped to."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Juno Vale")

        game_screen.player.engage_seek(explorer)
        self.assertTrue(game_screen.player.autopilot_active)

        # Simulate the ship having jumped away, the way ExplorerRoutine._migrate does.
        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"

        game_screen.update_physics()

        self.assertFalse(game_screen.player.autopilot_active, "Autopilot should disengage once its target is gone")
        self.assertIsNone(game_screen.player.autopilot_target)


class TestLocationScreenPausesDuringDialogue(unittest.TestCase):
    """Regression test: every other NPC in the room kept wandering around
    even while the player was mid-conversation with one of them - only the
    player's own movement paused. update_physics() must freeze every NPC
    in the location while active_dialogue is open, not just the one being
    talked to."""

    def test_npcs_freeze_while_a_dialogue_is_open(self):
        config = {
            "label": "Test Room",
            "npcs": [
                {"name": "Talker", "x": 100, "y": 100, "role": "resident"},
                {"name": "Bystander", "x": 200, "y": 200, "role": "resident"},
            ],
        }
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        talker = next(character for character in screen.npcs if character.person.name == "Talker")
        bystander = next(character for character in screen.npcs if character.person.name == "Bystander")

        screen.active_dialogue = talker.person.dialogue
        before = (bystander.person.x, bystander.person.y)
        for _ in range(50):
            screen.update_physics()
        self.assertEqual((bystander.person.x, bystander.person.y), before)

    def test_npcs_move_normally_with_no_dialogue_open(self):
        config = {
            "label": "Test Room",
            "npcs": [{"name": "Wanderer", "x": 100, "y": 100, "role": "resident"}],
        }
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        wanderer = screen.npcs[0].person
        before = (wanderer.x, wanderer.y)
        for _ in range(200):
            screen.update_physics()
        self.assertNotEqual((wanderer.x, wanderer.y), before)


class TestLocationScreenClickTargeting(unittest.TestCase):
    """Test LocationScreen._select_person_target_at() - click-to-target for
    NPCs/visitors on foot, the interior counterpart to SpaceScreen's own
    click-to-target over ships/landables."""

    def _make_screen(self):
        config = {
            "label": "Test Room",
            "npcs": [
                {"name": "Near", "x": 100, "y": 100, "role": "resident"},
                {"name": "Far", "x": 500, "y": 500, "role": "resident"},
            ],
        }
        return LocationScreen(config_data=config, world_width=800, world_height=600)

    def test_click_on_a_person_targets_them(self):
        screen = self._make_screen()
        screen._select_person_target_at(105, 100)
        self.assertEqual(screen._get_npc_target().name, "Near")

    def test_click_on_empty_space_leaves_target_unset(self):
        screen = self._make_screen()
        screen._select_person_target_at(300, 300)
        self.assertIsNone(screen._get_npc_target())

    def test_closest_person_wins_when_two_are_both_in_click_range(self):
        config = {
            "label": "Test Room",
            "npcs": [
                {"name": "Closer", "x": 100, "y": 100, "role": "resident"},
                {"name": "Farther", "x": 120, "y": 100, "role": "resident"},
            ],
        }
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        screen._select_person_target_at(105, 100)
        self.assertEqual(screen._get_npc_target().name, "Closer")

    def test_click_replaces_an_existing_target(self):
        screen = self._make_screen()
        screen._select_person_target_at(105, 100)
        self.assertEqual(screen._get_npc_target().name, "Near")
        screen._select_person_target_at(505, 500)
        self.assertEqual(screen._get_npc_target().name, "Far")


class TestBuildSaveGameState(unittest.TestCase):
    """Regression test: a save made while docked at a station/moon (in
    ANY system other than the story's starting one) used to always reload
    into the starting system - game_state["story"]/["system_id"] were set
    on an empty dict, then immediately discarded when the station/moon
    branch reassigned game_state from get_state(). build_save_game_state()
    centralizes this so story/system_id always land on the dict actually
    passed to create_save_file()."""

    def test_station_save_keeps_story_and_system_id(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        station_interior = game_screen.get_interior_screen(game_screen.station, "default")
        game_state, system_config_snapshot = build_save_game_state(game_screen, "station", station_interior, None)
        self.assertEqual(game_state["location"], "station")
        self.assertEqual(game_state["story"], "default")
        self.assertEqual(game_state["system_id"], "keplers_reach")
        self.assertEqual(system_config_snapshot, {})

    def test_moon_save_keeps_story_and_system_id(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        moon_interior = game_screen.get_interior_screen(game_screen.moon, "wilderness")
        game_state, system_config_snapshot = build_save_game_state(game_screen, "moon", None, moon_interior)
        self.assertEqual(game_state["location"], "moon")
        self.assertEqual(game_state["moon_location"], "wilderness")
        self.assertEqual(game_state["story"], "default")
        self.assertEqual(game_state["system_id"], "keplers_reach")

    def test_moon_save_uses_interior_key_not_label_text(self):
        """Regression test: moon_location used to be guessed from whether
        the interior's own label text contained the word "city" - Kepler's
        Reach's city interior is labeled "Rust Moon Settlement", which
        doesn't, so saving there was misdetected as "wilderness" and
        loading put the player in the wrong moon location entirely."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        city_interior = game_screen.get_interior_screen(game_screen.moon, "city")
        self.assertNotIn("city", city_interior.ui_label.lower())  # the actual label has no "city" in it
        game_state, _ = build_save_game_state(game_screen, "moon", None, city_interior)
        self.assertEqual(game_state["moon_location"], "city")

    def test_space_save_keeps_story_system_id_and_system_config(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        game_state, system_config_snapshot = build_save_game_state(game_screen, "game", None, None)
        self.assertEqual(game_state["location"], "space")
        self.assertEqual(game_state["system_id"], "keplers_reach")
        self.assertIs(system_config_snapshot, game_screen.system_config)


class TestStoryVersioning(unittest.TestCase):
    """Test story_version round-tripping through a save and the load-time
    mismatch warning (see CLAUDE.md's "Save Compatibility & Story
    Versioning" section) - never blocks loading, just surfaces the risk
    that a save's story config or this game's state-handling code has
    changed since the save was made."""

    def test_space_screen_reads_story_version_from_story_json(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        self.assertEqual(game_screen.story_version, "1.1.0")

    def test_build_save_game_state_records_story_version(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_state, _ = build_save_game_state(game_screen, "game", None, None)
        self.assertEqual(game_state["story_version"], "1.1.0")

    def test_matching_version_prints_no_warning(self):
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", "1.1.0")
        self.assertEqual(captured.getvalue(), "")

    def test_mismatched_version_warns(self):
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", "0.9.0")
        self.assertIn("0.9.0", captured.getvalue())
        self.assertIn("1.1.0", captured.getvalue())

    def test_missing_version_warns(self):
        """A save made before story versioning existed has no
        story_version key at all - still worth flagging, not silently
        treated as compatible."""
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", None)
        self.assertNotEqual(captured.getvalue(), "")


class TestLocationScreenTouchingRoomBoundary(unittest.TestCase):
    """Regression test: two touching rooms (e.g. Entrance Hall y:300-600 and
    Bar y:0-300, sharing the line y=300) both used strict "<" bounds, so a
    step that landed exactly on the shared boundary was invalid in *both*
    rooms at once - an invisible wall stranding the player one step short,
    for roughly a third of all positions (everything is integer-valued and
    speed is a fixed 3, so this isn't a rare float-precision fluke)."""

    def _make_two_room_screen(self):
        config = {
            "label": "Test", "culture": None,
            "rooms": [
                {"label": "Hall", "rect": [360, 300, 80, 300]},
                {"label": "Bar", "rect": [300, 0, 200, 300]},
            ],
            "npcs": [],
        }
        screen = LocationScreen(config_data=config, world_width=800, world_height=600)
        # rooms only populate when a culture is set (see LocationScreen.__init__) -
        # set them directly to exercise the bounds check in isolation.
        screen.rooms = config["rooms"]
        return screen

    def test_can_cross_from_hall_into_bar_at_every_starting_y(self):
        screen = self._make_two_room_screen()
        for start_y in range(301, 400):
            screen.player.x, screen.player.y = 400, start_y
            for _ in range(60):
                keys = {pygame_mock.K_UP: True, pygame_mock.K_w: False, pygame_mock.K_DOWN: False, pygame_mock.K_s: False, pygame_mock.K_LEFT: False, pygame_mock.K_a: False, pygame_mock.K_RIGHT: False, pygame_mock.K_d: False}
                screen._handle_movement(keys)
                if screen.player.y <= 250:
                    break
            self.assertLessEqual(screen.player.y, 300, f"Got stuck at y={screen.player.y} starting from y={start_y}")


class TestSpaceScreenShipTypePersistence(unittest.TestCase):
    """Regression test: SpaceScreen.__init__() always starts the player's
    Ship from story.json's default player_type - after buying a ship and
    saving, loading the save (a fresh SpaceScreen + restore_state()) used
    to silently revert the player back to that story default instead of
    whatever they'd actually bought, even though Possessions itself
    restored correctly."""

    def test_restore_state_reequips_the_last_purchased_ship(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        spaceport = game_screen.get_interior_screen(game_screen.station, "spaceport")
        spaceport._apply_dialogue_action("buy_ship:shuttle")
        self.assertEqual(game_screen.player.ship.graphics.get("size"), 10)  # shuttle's configured size

        state = game_screen.get_state()

        fresh = SpaceScreen(pilot_name="Test", story="default")
        fresh.restore_state(state)
        self.assertEqual(fresh.player.ship.graphics.get("size"), 10,
                          "Loading a save must re-equip the bought ship, not story.json's starting default")

    def test_restore_possessions_from_a_docked_location_save_also_reequips(self):
        """The station/moon load path calls restore_possessions() (not
        restore_state() - see its docstring for why: state["player"] there
        is the LocationScreen's own walking position, not the ship's space
        position) - it must still pick up "possessions" and re-equip
        accordingly."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        spaceport = game_screen.get_interior_screen(game_screen.station, "spaceport")
        spaceport._apply_dialogue_action("buy_ship:shuttle")

        docked_state = spaceport.get_state()  # {"player": {...}, "possessions": {...}} - no ai_ships key

        fresh = SpaceScreen(pilot_name="Test", story="default")
        fresh.restore_possessions(docked_state)
        self.assertEqual(fresh.player.ship.graphics.get("size"), 10)


class TestSpaceScreenParkAt(unittest.TestCase):
    """Regression test: loading directly into a station/moon save used to
    call the full restore_state(), which fed the LocationScreen's own
    walking-position dict (game_state["player"]) into the ship's x/y as if
    it were the ship's space position - scattering the ship to wherever
    that (unrelated, much smaller-scale) interior coordinate happened to
    be instead of docking it at the landable. main.py now calls
    restore_possessions() + park_at() for station/moon loads instead."""

    def test_park_at_places_the_ship_exactly_on_the_landable(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        game_screen.park_at(game_screen.moon)
        self.assertEqual((game_screen.player.x, game_screen.player.y), (game_screen.moon.x, game_screen.moon.y))
        self.assertEqual((game_screen.player.velocity_x, game_screen.player.velocity_y), (0, 0))

    def test_restore_possessions_does_not_touch_ship_position(self):
        """The whole point of the split: restore_possessions() must never
        read a "player" key at all, so a caller can safely follow it with
        park_at() without the interior's walking-position dict clobbering
        the ship's space position first."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        original_position = (game_screen.player.x, game_screen.player.y)
        # An interior-shaped state - x/y here mean a LocationScreen's local
        # walking position, wildly different scale from ship space coords.
        interior_shaped_state = {"player": {"x": 800, "y": 800}, "possessions": {"credits": 500, "owned_ships": [], "loans": []}}
        game_screen.restore_possessions(interior_shaped_state)
        self.assertEqual((game_screen.player.x, game_screen.player.y), original_position)
        self.assertEqual(game_screen.player.person.possessions.credits, 500)


class TestLocationScreenEconomy(unittest.TestCase):
    """Test LocationScreen's ship-ownership-gated exit and dialogue-action
    gating - the mechanisms behind the spaceport's disabled "Return to
    Ship" option and the salesman/loan-officer purchase flow."""

    def _make_screen(self, connected_locations=None, return_to_ship=True, credits=0, owned_ships=None, loans=None):
        possessions = Possessions(credits=credits, owned_ships=owned_ships or [], loans=loans or [])
        config = {"label": "Spaceport", "connected_locations": connected_locations or [], "return_to_ship": return_to_ship}
        return LocationScreen(config_data=config, world_width=800, world_height=600, player_possessions=possessions)

    def test_ship_unavailable_without_a_ship(self):
        screen = self._make_screen(return_to_ship=True)
        self.assertFalse(screen.ship_available)
        self.assertEqual(screen.get_available_exit_options(), [])
        self.assertEqual(screen.get_exit_disabled_reasons(), {"ship": "no ship docked here"})

    def test_ship_available_once_owned(self):
        screen = self._make_screen(return_to_ship=True, owned_ships=["shuttle"])
        self.assertTrue(screen.ship_available)
        self.assertEqual(screen.get_available_exit_options(), ["ship"])
        self.assertEqual(screen.get_exit_disabled_reasons(), {})

    def test_connected_location_exit_unaffected_by_ship_ownership(self):
        screen = self._make_screen(connected_locations=["default"], return_to_ship=False)
        self.assertEqual(screen.get_available_exit_options(), ["default"])
        self.assertEqual(screen.get_exit_disabled_reasons(), {})

    def test_buy_ship_blocked_when_unaffordable(self):
        screen = self._make_screen(credits=0)
        option = {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"}
        self.assertEqual(screen._option_blocked_reason(option), "not enough credits")

    def test_buy_ship_allowed_when_affordable(self):
        screen = self._make_screen(credits=1200)
        option = {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"}
        self.assertIsNone(screen._option_blocked_reason(option))
        screen._apply_dialogue_action("buy_ship:shuttle")
        self.assertEqual(screen.player.possessions.credits, 0)
        self.assertEqual(screen.player.possessions.owned_ships, ["shuttle"])

    def test_buy_ship_method_can_be_called_directly(self):
        """buy_ship() is the public entry point ShipBrowserMenu calls (via
        main.py's build_shop_menu) - _apply_dialogue_action's "buy_ship:"
        branch is just a thin wrapper around it, so both purchase paths
        share one mutation."""
        screen = self._make_screen(credits=1200)
        screen.buy_ship("shuttle")
        self.assertEqual(screen.player.possessions.credits, 0)
        self.assertEqual(screen.player.possessions.owned_ships, ["shuttle"])

    def test_buy_ship_calls_on_ship_purchased_callback(self):
        possessions = Possessions(credits=1200)
        config = {"label": "Spaceport"}
        purchased = []
        screen = LocationScreen(config_data=config, world_width=800, world_height=600, player_possessions=possessions, on_ship_purchased=purchased.append)
        screen._apply_dialogue_action("buy_ship:shuttle")
        self.assertEqual(purchased, ["shuttle"])

    def test_buy_ship_uninstalls_outfits_instead_of_carrying_them_to_the_new_ship(self):
        """Regression test: installed_outfits describes "whichever ship is
        flown", not a specific hull (see docs/SAVE_SYSTEM.md) - buying a new
        ship used to silently inherit whatever was mounted on the old one
        for free, since slot ids like "utility_1" are reused across ship
        types. The new ship must start bare, with the old outfit back in
        spares to reinstall."""
        possessions = Possessions(credits=4500, installed_outfits={"utility_1": "cargo_expansion"})
        config = {"label": "Spaceport"}
        screen = LocationScreen(config_data=config, world_width=800, world_height=600, player_possessions=possessions)
        screen.buy_ship("freighter")
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(possessions.owned_outfits, ["cargo_expansion"])

    def test_take_loan_blocked_if_already_taken(self):
        screen = self._make_screen(loans=[{"lender": "X", "principal": 1200}])
        option = {"label": "Take loan", "action": "take_loan"}
        self.assertEqual(screen._option_blocked_reason(option), "already have a loan")

    def test_take_loan_grants_the_testing_loan_amount(self):
        """Loan amount is bumped to 100,000cr for testing (was tied to the
        shuttle's cost) - see LocationScreen.TESTING_LOAN_AMOUNT."""
        screen = self._make_screen()
        screen._apply_dialogue_action("take_loan")
        self.assertEqual(screen.player.possessions.credits, 100_000)
        self.assertEqual(len(screen.player.possessions.loans), 1)

    def test_navigation_skips_blocked_dialogue_options(self):
        """Regression test: the cursor used to be able to move onto (and
        then Enter-confirm) a dialogue option that was drawn dim/blocked -
        e.g. cycling DOWN past an unaffordable ship onto a second
        unaffordable ship. _next_selectable_option must skip it."""
        screen = self._make_screen(credits=0)
        options = [
            {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"},
            {"label": "Patrol - 3500cr", "action": "buy_ship:patrol"},
            {"label": "Leave"},
        ]
        # Both ships are unaffordable at 0 credits - DOWN from "Leave"
        # should wrap straight back to "Leave" itself, never landing on
        # either blocked option.
        self.assertEqual(screen._next_selectable_option(options, 2, 1), 2)
        # First selectable when nothing is affordable is "Leave" (index 2).
        self.assertEqual(screen._first_selectable_option(options), 2)

    def test_navigation_lands_on_the_one_affordable_option(self):
        screen = self._make_screen(credits=1200)
        options = [
            {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"},
            {"label": "Patrol - 3500cr", "action": "buy_ship:patrol"},
            {"label": "Leave"},
        ]
        self.assertEqual(screen._first_selectable_option(options), 0)
        # DOWN from Shuttle should skip the unaffordable Patrol and land on Leave.
        self.assertEqual(screen._next_selectable_option(options, 0, 1), 2)


class TestSelectableListDisabledNavigation(unittest.TestCase):
    """Test SelectableList.handle_key()'s disabled_fn skip - the same
    "can't navigate onto a disabled entry" fix applied to ExitMenu."""

    def test_skips_disabled_entry_when_moving_down(self):
        selectable = SelectableList(["a", "b", "c"], max_visible=3)
        selectable.selected = 0
        selectable.handle_key(pygame_mock.K_DOWN, disabled_fn=lambda item: "blocked" if item == "b" else None)
        self.assertEqual(selectable.current(), "c")

    def test_skips_disabled_entry_when_moving_up(self):
        selectable = SelectableList(["a", "b", "c"], max_visible=3)
        selectable.selected = 2
        selectable.handle_key(pygame_mock.K_UP, disabled_fn=lambda item: "blocked" if item == "b" else None)
        self.assertEqual(selectable.current(), "a")

    def test_all_disabled_does_not_hang(self):
        selectable = SelectableList(["a", "b"], max_visible=2)
        selectable.selected = 0
        selectable.handle_key(pygame_mock.K_DOWN, disabled_fn=lambda item: "blocked")
        # Never enters an infinite loop - capped at len(items) steps.


class TestSelectableListItemsShrink(unittest.TestCase):
    """Regression test: SaveDialog crashed (IndexError in current()) when
    deleting the last-selected save shrank the list out from under a
    SelectableList whose `selected` index wasn't updated to match - e.g.
    deleting save 3 of 3 left `selected == 2` pointing past the new 2-item
    list. SaveDialog's existing_saves setter reassigns `.list.items`
    directly (see game/ui/save_dialog.py), so the fix has to live in
    SelectableList itself, not in whoever mutates it."""

    def test_current_does_not_crash_when_items_shrink_past_selected(self):
        selectable = SelectableList(["save1", "save2", "save3"], max_visible=5)
        selectable.selected = 2  # "save3" was selected
        selectable.items = ["save1", "save2"]  # save3 deleted - list shrinks
        self.assertEqual(selectable.current(), "save2")
        self.assertEqual(selectable.selected, 1)

    def test_current_returns_none_when_items_becomes_empty(self):
        selectable = SelectableList(["save1"], max_visible=5)
        selectable.selected = 0
        selectable.items = []  # the only save deleted
        self.assertIsNone(selectable.current())

    def test_draw_does_not_crash_when_items_shrink_past_selected(self):
        selectable = SelectableList(["save1", "save2", "save3"], max_visible=5)
        selectable.selected = 2
        selectable.items = ["save1", "save2"]
        selectable.draw(MagicMock(), MagicMock(), 0, 0, 20, 1.0)  # must not raise


class TestCreateSaveFileNameCollision(unittest.TestCase):
    """Regression test: the pre-populated save name only has minute
    resolution, so two new saves made within the same minute used to collide
    on the same filename and the second silently clobbered the first.
    create_save_file() should now append " (2)", " (3)", etc. instead."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch.object(utils, "SAVE_DIR", self.test_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_second_save_with_same_name_gets_suffixed(self):
        path1 = utils.create_save_file("Pilot", "2026-08-25 1430", {}, {})
        path2 = utils.create_save_file("Pilot", "2026-08-25 1430", {}, {})

        self.assertNotEqual(path1, path2)
        self.assertTrue(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))
        self.assertIn("(2)", path2)

    def test_third_save_with_same_name_increments_again(self):
        utils.create_save_file("Pilot", "clash", {}, {})
        utils.create_save_file("Pilot", "clash", {}, {})
        path3 = utils.create_save_file("Pilot", "clash", {}, {})

        self.assertIn("(3)", path3)

    def test_unique_name_is_not_suffixed(self):
        path = utils.create_save_file("Pilot", "unique_name", {}, {})
        self.assertTrue(path.endswith("save_unique_name.json"))

    def test_overwrite_flow_is_unaffected_since_old_file_is_deleted_first(self):
        """Mirrors main.py's overwrite path: delete the old file, then
        create_save_file() with the same name reuses it rather than
        appending a suffix."""
        path1 = utils.create_save_file("Pilot", "existing", {}, {})
        os.remove(path1)
        path2 = utils.create_save_file("Pilot", "existing", {}, {})
        self.assertEqual(path1, path2)


class TestSaveDialogNewSaveKey(unittest.TestCase):
    """Regression test: pressing N to start a new save emits both a KEYDOWN
    and a TEXTINPUT("n") event in the same pygame frame. handle_input() used
    to process the KEYDOWN (switching into input_mode) and then the
    TEXTINPUT from the very same keypress, appending a stray "n" to the
    pre-populated save name. See game/ui/save_dialog.py's _suppress_next_text."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_pressing_n_does_not_append_n_to_save_name(self):
        dialog = SaveDialog(pilot_name="Test")
        dialog.list.items = ["existing_save"]
        dialog.input_mode = False
        name_before = dialog.save_name

        events = [
            self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_n),
            self._event(pygame_mock.TEXTINPUT, text="n"),
        ]
        dialog.handle_input(events)

        self.assertTrue(dialog.input_mode)
        self.assertEqual(dialog.save_name, name_before)

    def test_textinput_still_works_after_the_suppressed_one(self):
        dialog = SaveDialog(pilot_name="Test")
        dialog.list.items = ["existing_save"]
        dialog.input_mode = False

        dialog.handle_input([
            self._event(pygame_mock.KEYDOWN, key=pygame_mock.K_n),
            self._event(pygame_mock.TEXTINPUT, text="n"),
        ])
        name_after_n = dialog.save_name
        dialog.handle_input([self._event(pygame_mock.TEXTINPUT, text="x")])

        self.assertEqual(dialog.save_name, name_after_n + "x")


if __name__ == "__main__":
    unittest.main()
