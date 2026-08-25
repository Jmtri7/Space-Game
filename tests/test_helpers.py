"""Unit tests for helper functions extracted from main.py"""
import sys
import os
import io
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
from game.world.character import Character
from game.ui.selectable_list import SelectableList
from game.screens.space_screen import SpaceScreen
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

    def test_unconfigured_role_always_returns_to_ship(self):
        """A role with no ROLE_EXIT_PREFERENCE entry falls back to
        DEFAULT_EXIT_PREFERENCE - reboards immediately, exactly like every
        pilot did before connected_locations existed."""
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(get_exit_options=lambda: ["wilderness", "ship"])
        ai_ship = self._make_ai_ship(role="patrol_officer")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_configured_role_prefers_connected_location(self):
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(get_exit_options=lambda: ["wilderness", "ship"])
        ai_ship = self._make_ai_ship(role="freighter_pilot")
        self.assertEqual(ROLE_EXIT_PREFERENCE["freighter_pilot"][0], "wilderness")
        self.assertEqual(routine._choose_exit(ai_ship), "wilderness")

    def test_already_visited_location_is_skipped(self):
        """Regression test: a role preferring both connected locations
        must not pick one it already visited this stop, or it would
        ping-pong between them forever and never reboard."""
        routine = DockRoutine(route=[])
        routine._location = SimpleNamespace(get_exit_options=lambda: ["city", "ship"])
        routine._visited_this_stop = {"city"}
        ai_ship = self._make_ai_ship(role="freighter_pilot")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_full_stop_visits_every_connected_location_then_reboards(self):
        """End-to-end regression test for the ping-pong bug: a freighter
        pilot landing at a stop with two locations that each connect back
        to the other should visit both once, then reboard - never loop
        forever - using the real phase machine (run()), not a
        reimplementation of it."""
        city_config = {"label": "City", "connected_locations": ["wilderness"], "npcs": []}
        wilderness_config = {"label": "Wilderness", "connected_locations": ["city"], "npcs": []}
        stop = Landable(0, 0, graphics={}, interiors={"city": city_config, "wilderness": wilderness_config})

        interior_cache = {}
        def get_interior_screen(landable, key, world_width, world_height):
            cache_key = (id(landable), key)
            if cache_key not in interior_cache:
                config = landable.interiors.get(key)
                if not config:
                    return None
                interior_cache[cache_key] = LocationScreen(config_data=config, world_width=world_width, world_height=world_height)
            return interior_cache[cache_key]

        ai_ship = SimpleNamespace(
            role="freighter_pilot",
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
        def get_interior_screen(landable, key, world_width, world_height):
            cache_key = (id(landable), key)
            if cache_key not in interior_cache:
                config = landable.interiors.get(key)
                if not config:
                    return None
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
        whichever connected location the role's preference names, not
        wander into an unrelated dead end first."""
        hub = SimpleNamespace(get_exit_options=lambda: ["dead_end", "spaceport"])
        docks = SimpleNamespace(get_exit_options=lambda: ["hub", "ship"])
        routine = DockRoutine(route=[])
        routine._location = hub
        routine._visited_this_stop = {"hub"}
        ai_ship = self._make_ai_ship(role="freighter_pilot")

        self.assertIn("spaceport", ROLE_EXIT_PREFERENCE["freighter_pilot"])
        choice = routine._choose_exit(ai_ship)
        self.assertEqual(choice, "spaceport", "Should route toward the preferred middle node, not the dead end")

        routine._location = docks
        routine._visited_this_stop.add("spaceport")
        self.assertEqual(routine._choose_exit(ai_ship), "ship")

    def test_safety_cap_forces_reboard_when_ship_is_never_reachable(self):
        """If nothing ever leads to "ship" (a misconfigured or future
        role/graph combination this feature hasn't been tuned for), the
        MAX_LATERAL_HOPS cap must still force a reboard rather than wander
        forever - this is what actually caught the corridor<->dormitory
        ping-pong during development, before ROLE_EXIT_PREFERENCE routed
        freighter_pilot through the spaceport."""
        room_a = SimpleNamespace(get_exit_options=lambda: ["room_b"])
        room_b = SimpleNamespace(get_exit_options=lambda: ["room_a"])
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
        station_interior = game_screen.get_interior_screen(game_screen.station, "default", 800, 600)
        game_state, system_config_snapshot = build_save_game_state(game_screen, "station", station_interior, None)
        self.assertEqual(game_state["location"], "station")
        self.assertEqual(game_state["story"], "default")
        self.assertEqual(game_state["system_id"], "keplers_reach")
        self.assertEqual(system_config_snapshot, {})

    def test_moon_save_keeps_story_and_system_id(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="keplers_reach")
        moon_interior = game_screen.get_interior_screen(game_screen.moon, "wilderness", 1600, 1600)
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
        city_interior = game_screen.get_interior_screen(game_screen.moon, "city", 1600, 1600)
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
        self.assertEqual(game_screen.story_version, "1.0.0")

    def test_build_save_game_state_records_story_version(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_state, _ = build_save_game_state(game_screen, "game", None, None)
        self.assertEqual(game_state["story_version"], "1.0.0")

    def test_matching_version_prints_no_warning(self):
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", "1.0.0")
        self.assertEqual(captured.getvalue(), "")

    def test_mismatched_version_warns(self):
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            warn_if_story_version_mismatch("default", "0.9.0")
        self.assertIn("0.9.0", captured.getvalue())
        self.assertIn("1.0.0", captured.getvalue())

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
        spaceport = game_screen.get_interior_screen(game_screen.station, "spaceport", 800, 600)
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
        spaceport = game_screen.get_interior_screen(game_screen.station, "spaceport", 800, 600)
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

    def test_buy_ship_calls_on_ship_purchased_callback(self):
        possessions = Possessions(credits=1200)
        config = {"label": "Spaceport"}
        purchased = []
        screen = LocationScreen(config_data=config, world_width=800, world_height=600, player_possessions=possessions, on_ship_purchased=purchased.append)
        screen._apply_dialogue_action("buy_ship:shuttle")
        self.assertEqual(purchased, ["shuttle"])

    def test_take_loan_blocked_if_already_taken(self):
        screen = self._make_screen(loans=[{"lender": "X", "principal": 1200}])
        option = {"label": "Take loan", "action": "take_loan"}
        self.assertEqual(screen._option_blocked_reason(option), "already have a loan")

    def test_take_loan_grants_shuttle_cost(self):
        screen = self._make_screen()
        screen._apply_dialogue_action("take_loan")
        self.assertEqual(screen.player.possessions.credits, 1200)
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


if __name__ == "__main__":
    unittest.main()
