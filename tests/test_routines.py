"""Routines — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


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
        stop = LandingSite(0, 0, graphics={}, interiors={"city": city_config, "wilderness": wilderness_config})

        interior_cache = {}
        def get_interior_screen(landing_site, key):
            cache_key = (id(landing_site), key)
            if cache_key not in interior_cache:
                config = landing_site.interiors.get(key)
                if not config:
                    return None
                world_width, world_height = landing_site.interior_world_size
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
        stop = LandingSite(0, 0, graphics={}, interiors={"city": city_config, "wilderness": wilderness_config})

        interior_cache = {}
        def get_interior_screen(landing_site, key):
            cache_key = (id(landing_site), key)
            if cache_key not in interior_cache:
                config = landing_site.interiors.get(key)
                if not config:
                    return None
                world_width, world_height = landing_site.interior_world_size
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
        searching the interiors graph (LandingSite.interior_adjacency /
        get_ship_entry_key, resolved via TOWARD_SHIP), not wander into an
        unrelated dead end first."""
        hub_config = {"label": "Hub", "connected_locations": ["dead_end", "spaceport"], "return_to_ship": False, "npcs": []}
        dead_end_config = {"label": "Dead End", "connected_locations": ["hub"], "return_to_ship": False, "npcs": []}
        spaceport_config = {"label": "Spaceport", "connected_locations": ["hub"], "return_to_ship": True, "npcs": []}
        stop = LandingSite(0, 0, graphics={}, interiors={
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
        as its own return_to_ship is set (LandingSite.get_ship_entry_key).
        Routing has to key off that, not a literal string - this is the
        scenario that would have failed under the old hardcoded
        ROLE_EXIT_PREFERENCE = ["spaceport", "ship"]."""
        hub_config = {"label": "Hub", "connected_locations": ["docking_bay"], "return_to_ship": False, "npcs": []}
        docking_bay_config = {"label": "Docking Bay", "connected_locations": ["hub"], "return_to_ship": True, "npcs": []}
        stop = LandingSite(0, 0, graphics={}, interiors={"hub": hub_config, "docking_bay": docking_bay_config})
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
        elena_ship = next(s for s in game_screen.ai_ships if s.person.name == "Elae Vossae")
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
    """LocationScreen.plan_path() / IndoorPathfinder - the grid router that
    walks a visiting DockRoutine pilot across an interior's walkable area,
    around walls, concave notches, and building footprints. See
    TestDockRoutineRespectsWalls / TestDockRoutineRespectsBuildings for the
    full walking behavior this enables."""

    def _screen(self, rooms=None, structures=None, w=800, h=800):
        config = {"label": "Test", "culture": None}
        if rooms is not None:
            config["rooms"] = rooms
        if structures is not None:
            config["structures"] = structures
        screen = LocationScreen(config_data=config, world_width=w, world_height=h, story="default")
        if rooms is not None:
            screen.rooms = [normalize_room(r) for r in rooms]  # bypass culture-gated population
        return screen

    def _assert_walkable_path(self, screen, start, goal, path):
        self.assertEqual(path[-1], goal)
        prev = start
        for point in path:
            steps = max(1, int(math.hypot(point[0] - prev[0], point[1] - prev[1]) / 6))
            for i in range(steps + 1):
                t = i / steps
                x, y = prev[0] + (point[0] - prev[0]) * t, prev[1] + (point[1] - prev[1]) * t
                self.assertTrue(screen.can_move_to(x, y), f"Path leg {prev}->{point} leaves the walkable area at ({x:.0f},{y:.0f})")
            prev = point

    def test_same_area_returns_a_path_ending_at_goal(self):
        screen = self._screen(rooms=[{"rect": [0, 0, 400, 400]}])
        path = screen.plan_path((30, 30), (350, 350))
        self._assert_walkable_path(screen, (30, 30), (350, 350), path)

    def test_routes_around_a_concave_notch(self):
        # C-shaped area: a straight line from (60,60) to (60,540) is fine,
        # but (60,300)->(540,300) would cut straight through the notch.
        rooms = [
            {"rect": [40, 40, 60, 520]},    # left bar
            {"rect": [40, 40, 500, 60]},    # top bar
            {"rect": [40, 500, 500, 60]},   # bottom bar
        ]
        screen = self._screen(rooms=rooms, w=600, h=600)
        start, goal = (70, 300), (520, 520)
        path = screen.plan_path(start, goal)
        self._assert_walkable_path(screen, start, goal, path)

    def test_unreachable_goal_falls_back_to_the_direct_goal(self):
        screen = self._screen(rooms=[{"rect": [0, 0, 200, 200]}])
        self.assertEqual(screen.plan_path((10, 10), (5000, 5000)), [(5000, 5000)])

    def test_routes_around_a_building_footprint_with_no_rooms(self):
        # A moon interior: structures but no rooms. Start due north of the
        # bunker, goal due south - the direct line is straight through it.
        screen = self._screen(structures=[{"x": 500, "y": 500, "building_type": "drossholt_bunker"}], w=1600, h=1600)
        start, goal = (570, 400), (570, 700)
        path = screen.plan_path(start, goal)
        self._assert_walkable_path(screen, start, goal, path)


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
        screen.rooms = [normalize_room(r) for r in config["rooms"]]  # bypass culture-gated room population, see other tests
        screen.entrance_x, screen.entrance_y = 100, 100
        return screen

    def test_pilot_never_leaves_the_walkable_area_walking_an_l_shaped_room(self):
        location = self._make_l_shaped_screen()
        ai_ship = SimpleNamespace(pilot_person=Person(100, 100))
        routine = DockRoutine(route=[])
        routine._location = location
        routine._set_waypoints(ai_ship.pilot_person, (500, 500))  # the NPC, in the far corner of the L

        frames = 0
        while frames < 2000:
            if routine._step_toward(ai_ship.pilot_person):
                break
            self.assertTrue(
                location.can_move_to(ai_ship.pilot_person.x, ai_ship.pilot_person.y),
                f"Pilot left the walkable area at ({ai_ship.pilot_person.x}, {ai_ship.pilot_person.y})",
            )
            frames += 1
        else:
            self.fail("Pilot never arrived within 2000 frames")


class TestBuildingFootprintCollision(unittest.TestCase):
    """Regression test for the backlog's "Building collision missing"
    bug: player/NPCs used to be able to walk straight through a building's
    drawn silhouette, since can_move_to() only ever checked room walls or
    the open-world bounds. Uses a real building_type from the default
    story's building_types.json (drossholt_bunker), so this breaks if that
    config's shape/footprint fields are renamed. The footprint (see
    LocationScreen._building_footprint) is anchored so its front edge sits
    at the drawn silhouette's own base, not centred on the anchor point."""

    def _make_screen_with_bunker(self):
        config = {
            "label": "Test Yard",
            "structures": [{"x": 500, "y": 500, "building_type": "drossholt_bunker"}],
        }
        return LocationScreen(config_data=config, world_width=1600, world_height=1600, story="default")

    def _bunker_fp(self):
        return self._make_screen_with_bunker().building_footprints[0]

    def test_footprint_front_edge_sits_at_the_drawn_base(self):
        from game.screens.location_screen import _silhouette_local_bounds
        from game.utils import get_building_type
        _, _, _, base = _silhouette_local_bounds(get_building_type("default", "drossholt_bunker"))
        fx, fy, fw, fh = self._bunker_fp()
        # box back edge = base - depth; front edge = base + the small lip
        self.assertAlmostEqual(fy, 500 + base - 90)
        self.assertAlmostEqual(fy + fh, 500 + base + LocationScreen.FOOTPRINT_FRONT_LIP)
        self.assertEqual(fw, 140)

    def test_cannot_walk_into_the_footprint(self):
        location = self._make_screen_with_bunker()
        fx, fy, fw, fh = self._bunker_fp()
        self.assertFalse(location.can_move_to(fx + fw / 2, fy + fh / 2))  # dead center

    def test_can_walk_around_the_sides(self):
        location = self._make_screen_with_bunker()
        fx, fy, fw, fh = self._bunker_fp()
        self.assertTrue(location.can_move_to(fx - 20, fy + fh / 2))   # just left
        self.assertTrue(location.can_move_to(fx + fw + 20, fy + fh / 2))  # just right

    def test_can_walk_behind_it(self):
        """North of the building (smaller y) is open ground once past the
        footprint's near edge - this is what lets a character walk behind
        the building and be drawn behind it (see draw()'s y-sort), instead
        of the whole tall silhouette being solid all the way through."""
        location = self._make_screen_with_bunker()
        fx, fy, fw, fh = self._bunker_fp()
        self.assertTrue(location.can_move_to(fx + fw / 2, fy - 40))

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
        # Start directly north of the bunker, target directly south, so dx
        # is 0 for the entire direct line and the wall-slide fallback's
        # axis-only candidates never move the pilot on their own.
        target_x, target_y = 570, 700
        location = self._make_screen_with_bunker(target_x, target_y)
        person = Person(570, 400)
        routine = DockRoutine(route=[])
        routine._location = location
        routine._set_waypoints(person, (target_x, target_y))

        frames = 0
        while frames < 2000:
            if routine._step_toward(person):
                break
            self.assertTrue(
                location.can_move_to(person.x, person.y),
                f"Pilot walked into the building (or left the world) at ({person.x}, {person.y})",
            )
            frames += 1
        else:
            self.fail("Pilot never arrived within 2000 frames")
        # _step_toward's ARRIVAL_DISTANCE (10) means arrival can land up to
        # that far from the exact target, not pixel-perfect on it.
        self.assertLessEqual(math.hypot(person.x - target_x, person.y - target_y), 10)

    def test_step_toward_gives_up_a_leg_it_cannot_finish_instead_of_hanging(self):
        """Backlog "Petty Officer Lund gets stuck": a walk leg aimed at a
        spot the walker genuinely can't reach (target boxed in by the
        bunker footprint against a wall) used to spin _step_toward forever,
        freezing the pilot mid-route. It must now abandon the leg after
        STUCK_GIVEUP_FRAMES so the phase machine keeps moving."""
        from game.world.dock_routine import STUCK_GIVEUP_FRAMES
        config = {
            "label": "Boxed In",
            "rooms": [{"rect": [0, 0, 800, 800]}],
            # bunker hard against the west wall; target pinned in the
            # sliver between its footprint and the wall.
            "structures": [{"x": -40, "y": 400, "building_type": "drossholt_bunker"}],
        }
        location = LocationScreen(config_data=config, world_width=800, world_height=800, story="default")
        location.rooms = [normalize_room(r) for r in config["rooms"]]
        fx, fy, fw, fh = location.building_footprints[0]
        person = Person(400, 400)
        routine = DockRoutine(route=[])
        routine._location = location
        routine._set_waypoints(person, (max(0, fx) - 5, fy + fh / 2))  # unreachable pocket

        for frame in range(STUCK_GIVEUP_FRAMES + 400):
            if routine._step_toward(person):
                break
        else:
            self.fail("_step_toward never gave up - the pilot would hang forever")
        self.assertTrue(location.can_move_to(person.x, person.y))


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
        location.rooms = [normalize_room(r) for r in config["rooms"]]
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
        # Just north of the bunker's footprint, well within WANDER_RADIUS
        # of stepping into it.
        fx, fy, fw, fh = location.building_footprints[0]
        person = Person(fx + fw / 2, fy - 15)
        character = Character(person, role="resident", can_move_to=location.can_move_to)

        for _ in range(2000):
            character.routine.run(character)
            self.assertTrue(location.can_move_to(person.x, person.y))


class TestDepartRoutine(unittest.TestCase):
    """DepartRoutine walks a leaving local NPC to a point and then sets
    character.gone so LocationScreen.update_physics drops it. Used for a
    one-time character (the Grey Courier) via an NPC config's depart_flag."""

    def test_walks_to_the_target_then_marks_itself_gone(self):
        from game.world.depart_routine import DepartRoutine
        config = {"label": "Room", "rooms": [{"label": "R", "rect": [0, 0, 400, 200]}]}
        location = LocationScreen(config_data=config, world_width=600, world_height=400)
        person = Person(350, 100)
        character = Character(person, role="resident", can_move_to=location.can_move_to)
        character.set_routine(DepartRoutine((20, 100)))

        for _ in range(600):
            character.routine.run(character)
            if character.gone:
                break
        self.assertTrue(character.gone)
        self.assertLess(person.x, 40)

    def test_gives_up_and_vanishes_if_boxed_in(self):
        from game.world.depart_routine import DepartRoutine
        person = Person(100, 100)
        character = Character(person, role="resident", can_move_to=lambda x, y: False)
        character.set_routine(DepartRoutine((0, 0)))
        character.routine.run(character)
        self.assertTrue(character.gone)

    def test_departing_npc_is_removed_from_the_interior(self):
        config = {
            "label": "Ring", "rooms": [{"label": "R", "rect": [0, 0, 400, 200]}],
            "portals": [{"x": 10, "y": 100, "return_to_ship": True}],
            "npcs": [{"name": "Leaver", "x": 350, "y": 100, "depart_flag": "leaver_done"}],
        }
        location = LocationScreen(config_data=config, world_width=600, world_height=400)
        self.assertEqual([c.person.name for c in location.npcs], ["Leaver"])
        location.player.possessions.flags["leaver_done"] = True
        for _ in range(600):
            location.update_physics(player_present=True)
            if not location.npcs:
                break
        self.assertEqual(location.npcs, [])


class TestPersonStepToward(unittest.TestCase):
    """Person.step_toward - the one on-foot movement primitive shared by the
    player (LocationScreen._handle_movement), WanderRoutine, and DockRoutine."""

    def test_moves_a_full_step_toward_a_far_target(self):
        p = Person(0.0, 0.0)
        moved = p.step_toward(100.0, 0.0, 3.0, lambda x, y: True)
        self.assertTrue(moved)
        self.assertAlmostEqual(p.x, 3.0)
        self.assertAlmostEqual(p.y, 0.0)

    def test_diagonal_step_is_normalized_not_faster(self):
        p = Person(0.0, 0.0)
        p.step_toward(100.0, 100.0, 5.0, lambda x, y: True)
        self.assertAlmostEqual(math.hypot(p.x, p.y), 5.0)  # not 5*sqrt(2)

    def test_never_overshoots_a_near_target(self):
        p = Person(0.0, 0.0)
        p.step_toward(2.0, 0.0, 10.0, lambda x, y: True)
        self.assertAlmostEqual(p.x, 2.0)  # capped at the distance to the target

    def test_wall_slides_along_a_blocked_axis(self):
        p = Person(0.0, 0.0)
        # can't increase x past 0, but y is free - a step aimed up-right
        # should slide straight up instead of stopping.
        moved = p.step_toward(10.0, 10.0, 4.0, lambda x, y: x <= 0.0001)
        self.assertTrue(moved)
        self.assertAlmostEqual(p.x, 0.0)
        self.assertGreater(p.y, 0.0)

    def test_returns_false_and_does_not_move_when_fully_boxed_in(self):
        p = Person(5.0, 5.0)
        moved = p.step_toward(10.0, 10.0, 3.0, lambda x, y: False)
        self.assertFalse(moved)
        self.assertEqual((p.x, p.y), (5.0, 5.0))


class TestPersonWalkCycle(unittest.TestCase):
    """The leg walk animation: walk_phase advances with distance walked,
    walk_intensity ramps in while moving and eases back out on idle draw()
    frames, and a still Person stands in a neutral stance."""

    def test_walking_advances_phase_and_ramps_intensity(self):
        p = Person(0.0, 0.0)
        self.assertEqual(p.walk_phase, 0.0)
        self.assertEqual(p.walk_intensity, 0.0)
        p.step_toward(100.0, 0.0, 4.0, lambda x, y: True)
        self.assertGreater(p.walk_phase, 0.0)
        self.assertGreater(p.walk_intensity, 0.0)

    def test_phase_advance_scales_with_distance_below_the_cap(self):
        slow, fast = Person(0.0, 0.0), Person(0.0, 0.0)
        slow.step_toward(100.0, 0.0, 0.2, lambda x, y: True)
        fast.step_toward(100.0, 0.0, 0.4, lambda x, y: True)
        self.assertAlmostEqual(fast.walk_phase, slow.walk_phase * 2.0, places=5)

    def test_a_fast_walker_is_capped_to_a_brisk_cadence(self):
        # player / dock-pilot speed (~2 units/frame) must not spin the legs
        # faster than a stroller's - both land on WALK_MAX_STEP per frame.
        fast = Person(0.0, 0.0)
        fast.step_toward(100.0, 0.0, 5.0, lambda x, y: True)
        self.assertAlmostEqual(fast.walk_phase, Person.WALK_MAX_STEP, places=6)
        stroll = Person(0.0, 0.0)
        stroll.step_toward(100.0, 0.0, 0.5, lambda x, y: True)  # WanderRoutine
        self.assertLess(stroll.walk_phase, Person.WALK_MAX_STEP)

    def test_a_blocked_step_does_not_advance_the_cycle(self):
        p = Person(5.0, 5.0)
        p.step_toward(9.0, 9.0, 3.0, lambda x, y: False)
        self.assertEqual(p.walk_phase, 0.0)
        self.assertEqual(p.walk_intensity, 0.0)

    def test_idle_draw_frames_ease_the_animation_back_out(self):
        p = Person(0.0, 0.0)
        p.step_toward(100.0, 0.0, 4.0, lambda x, y: True)
        walking = p.walk_intensity
        p.draw(MagicMock())  # the frame we moved on - not idle, no decay yet
        self.assertEqual(p.walk_intensity, walking)
        p.draw(MagicMock())  # first genuinely idle frame - eases out
        self.assertLess(p.walk_intensity, walking)
        for _ in range(60):
            p.draw(MagicMock())
        self.assertEqual(p.walk_intensity, 0.0)

    def test_a_still_person_stands_in_a_neutral_stance(self):
        hip_dy, ankles = Person(0.0, 0.0)._leg_stance()
        self.assertEqual(hip_dy, 0.0)
        self.assertEqual(ankles, ((0.0, 0.0), (0.0, 0.0)))

    def test_a_still_person_adds_no_arm_swing(self):
        # the relaxed splay is baked into the figure geometry, not _arm_swing
        self.assertEqual(Person(0.0, 0.0)._arm_swing(), (0.0, 0.0))

    def test_the_arms_swing_opposite_each_other_and_counter_to_the_stride(self):
        p = Person(0.0, 0.0)
        p.step_toward(100.0, 0.0, 4.0, lambda x, y: True)
        p.walk_phase = math.pi / 2  # sin = 1 -> left leg fully forward
        p.walk_intensity = 1.0
        _, ((leg_dx_l, _), _) = p._leg_stance()
        arm_dx_l, arm_dx_r = p._arm_swing()
        self.assertGreater(leg_dx_l, 0.0)                     # left leg forward
        self.assertLess(arm_dx_l, 0.0)                        # left arm back (counter)
        self.assertGreater(arm_dx_r, 0.0)                     # right arm forward
        self.assertAlmostEqual(arm_dx_l, -arm_dx_r, places=6) # ...opposite each other

    def test_a_person_faces_the_way_it_last_walked(self):
        p = Person(0.0, 0.0)
        self.assertEqual(p.facing, 1)
        p.step_toward(-50.0, 0.0, 4.0, lambda x, y: True)
        self.assertEqual(p.facing, -1)
        p.step_toward(p.x, p.y + 99.0, 4.0, lambda x, y: True)  # straight up
        self.assertEqual(p.facing, -1)                        # unchanged
        p.step_toward(50.0, 0.0, 4.0, lambda x, y: True)
        self.assertEqual(p.facing, 1)

    def test_a_perfectly_diagonal_step_still_turns_to_face_it(self):
        # Regression: facing required abs(mvx) > abs(mvy) - strictly
        # sideways-dominant - so an exact 45-degree step (two arrow keys
        # held at once, e.g. Up+Left, or a WanderRoutine target straight
        # up-left/up-right) has mvx == mvy and never turned the figure at
        # all, even though it's walking left/right just as much as up/down.
        p = Person(0.0, 0.0)
        p.facing = 1
        p.step_toward(-50.0, 50.0, 4.0, lambda x, y: True)    # up-left, 45 degrees
        self.assertEqual(p.facing, -1)
        p.facing = -1
        p.step_toward(20.0, 200.0, 4.0, lambda x, y: True)    # mostly up, a little right
        self.assertEqual(p.facing, 1)
        p.facing = -1
        p.step_toward(50.0, -50.0, 4.0, lambda x, y: True)    # down-right, 45 degrees
        self.assertEqual(p.facing, 1)


class TestCharacterSetRoutine(unittest.TestCase):
    """Character.set_routine()/resolve_routine_class() - the mechanism
    behind temporarily overriding a character's routine (e.g. an escort
    pilot following the player - see person.escort_flag/
    SpaceScreen._sync_escorts) and restoring their normal role routine
    afterward."""

    def test_set_routine_starts_it_immediately(self):
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot={"name": "Kade Marsh", "role": "patrol_officer"}, route=[], get_interior_screen=None,
        )
        target = SimpleNamespace(x=100, y=0, get_distance=lambda x, y: 100)
        character.set_routine(OrbitPlayerRoutine(target))
        self.assertIsInstance(character.routine, OrbitPlayerRoutine)
        self.assertTrue(character.autopilot_active)  # start() engaged orbit

    def test_resolve_routine_class_matches_the_role_used_at_construction(self):
        from game.world.character import resolve_routine_class, ROLE_ROUTINES
        self.assertIs(resolve_routine_class("patrol_officer"), ROLE_ROUTINES["patrol_officer"])

    def test_explicit_routine_name_overrides_the_role_default(self):
        from game.world.character import resolve_routine_class, ROUTINE_REGISTRY
        # an unknown role would normally be IdleRoutine
        self.assertIs(
            resolve_routine_class("smuggler", routine_name="wander"),
            ROUTINE_REGISTRY["wander"],
        )

    def test_unknown_routine_name_falls_back_to_idle(self):
        from game.world.character import resolve_routine_class, IdleRoutine
        self.assertIs(resolve_routine_class("patrol_officer", routine_name="nonsense"), IdleRoutine)

    def test_pilot_config_routine_key_picks_the_routine(self):
        from game.world.wander_routine import WanderRoutine
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot={"name": "Rove", "role": "smuggler", "routine": "wander"},
            route=[], get_interior_screen=None,
        )
        self.assertIsInstance(character.routine, WanderRoutine)
        self.assertEqual(character.routine_name, "wander")

    def test_escorting_flag_defaults_to_false(self):
        character = Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot={"name": "Kade Marsh", "role": "patrol_officer"}, route=[], get_interior_screen=None,
        )
        self.assertFalse(character.escorting)


class TestOrbitPlayerRoutine(unittest.TestCase):
    """OrbitPlayerRoutine - keeps an escort circling a moving target
    (typically the player) at a fixed radius by re-engaging orbit mode
    every frame with the target's current position as the centre, so the
    circle tracks the target instead of the escort parking on top of it."""

    def _character(self):
        return Character.for_ai_pilot(
            0, 0, ship_type=None, ship_type_id="patrol", graphics=None,
            pilot={"name": "Kade Marsh", "role": "patrol_officer"}, route=[], get_interior_screen=None,
        )

    def test_start_engages_orbit_centred_on_the_target(self):
        character = self._character()
        target = SimpleNamespace(x=500, y=0, get_distance=lambda x, y: 500)
        OrbitPlayerRoutine(target).start(character)
        self.assertTrue(character.autopilot_active)
        mode = character.ship.autopilot._mode
        self.assertEqual((mode.center_x, mode.center_y), (500, 0))

    def test_run_moves_the_orbit_centre_to_follow_the_target(self):
        character = self._character()
        target = SimpleNamespace(x=500, y=0, get_distance=lambda x, y: 500)
        routine = OrbitPlayerRoutine(target)
        routine.start(character)
        target.x, target.y = 800, 200  # target flew somewhere else
        routine.run(character)
        mode = character.ship.autopilot._mode
        self.assertEqual((mode.center_x, mode.center_y), (800, 200))
        self.assertTrue(character.autopilot_active)


class TestExplorerRoutine(unittest.TestCase):
    """ExplorerRoutine migrates a Character between two SystemState.ai_ships
    lists and orbits something in whichever system it currently occupies -
    the mechanism the "Allow NPCs to jump between systems" backlog item and
    multi-system simulation both rely on."""

    @staticmethod
    def _make_system(offset_x, offset_y):
        station = LandingSite(offset_x, offset_y, graphics={}, interiors={})
        moon = LandingSite(offset_x + 500, offset_y, graphics={}, interiors={})
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


class TestCombatRoutine(unittest.TestCase):
    """CombatRoutine turns to face a target, closes to firing range, and
    sets character.firing while lined up - driving the ship through its
    low-level controls, never autopilot (see docs/AUTOPILOT_TESTING.md -
    this routine carries no SeekMode risk)."""

    def _character(self, x, y, angle=0):
        ship = Ship(x, y)
        ship.apply_ship_type({"size": 11, "max_thrust": 0.14, "max_velocity": 2.4, "rotation_speed": 3.5})
        ship.angle = angle
        return Character(Person(x, y, name="Bandit"), ship=ship)

    def test_turns_toward_the_target(self):
        char = self._character(0, 0, angle=0)     # facing up (+ -y)
        target = SimpleNamespace(x=0, y=500)      # directly below -> desired angle 180
        routine = CombatRoutine(target)
        routine.start(char)
        before = abs(_signed_angle_delta(char.ship.angle, 180))
        for _ in range(5):
            routine.run(char)
        after = abs(_signed_angle_delta(char.ship.angle, 180))
        self.assertLess(after, before)

    def test_fires_only_when_aligned_and_in_range(self):
        char = self._character(0, 0, angle=180)   # already facing the target
        routine = CombatRoutine(SimpleNamespace(x=0, y=300))  # in range, aligned
        routine.run(char)
        self.assertTrue(char.firing)
        routine2 = CombatRoutine(SimpleNamespace(x=0, y=5000))  # aligned but far
        routine2.run(char)
        self.assertFalse(char.firing)

    def test_start_drops_autopilot(self):
        char = self._character(0, 0)
        char.ship.engage_seek(SimpleNamespace(x=100, y=100))
        self.assertTrue(char.ship.autopilot_active)
        CombatRoutine(SimpleNamespace(x=0, y=100)).start(char)
        self.assertFalse(char.ship.autopilot_active)


if __name__ == "__main__":
    unittest.main()
