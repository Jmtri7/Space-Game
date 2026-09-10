"""Location Screen — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


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


class TestNormalizeRoom(unittest.TestCase):
    """normalize_room() folds every authored room shape (rect / polygon /
    circle) to a single {"polygon": [...], "label": ...} the rest of
    LocationScreen handles uniformly."""

    def test_rect_becomes_a_four_vertex_polygon(self):
        room = normalize_room({"rect": [10, 20, 100, 50], "label": "Bay"})
        self.assertEqual(room["label"], "Bay")
        self.assertEqual(room["polygon"], [(10, 20), (110, 20), (110, 70), (10, 70)])

    def test_polygon_is_kept_as_given(self):
        room = normalize_room({"polygon": [[0, 0], [10, 0], [5, 8]]})
        self.assertEqual(room["polygon"], [(0.0, 0.0), (10.0, 0.0), (5.0, 8.0)])

    def test_circle_becomes_a_regular_polygon(self):
        room = normalize_room({"shape": "circle", "center": [100, 100], "radius": 40, "sides": 6})
        self.assertEqual(len(room["polygon"]), 6)
        for x, y in room["polygon"]:
            self.assertAlmostEqual(math.hypot(x - 100, y - 100), 40, places=5)


class TestPointInPolygon(unittest.TestCase):
    def test_concave_notch_is_outside(self):
        # A C-shape: outer square 0..100 with a notch cut from the right side.
        poly = [(0, 0), (100, 0), (100, 40), (40, 40), (40, 60), (100, 60), (100, 100), (0, 100)]
        self.assertTrue(point_in_polygon(20, 50, poly))    # in the solid left bar
        self.assertFalse(point_in_polygon(70, 50, poly))   # in the notch
        self.assertTrue(point_in_polygon(70, 20, poly))    # above the notch, still solid

    def test_point_on_an_edge_counts_as_inside(self):
        poly = [(0, 0), (100, 0), (100, 100), (0, 100)]
        self.assertTrue(point_in_polygon(100, 50, poly))   # exactly on the right edge


class TestDeckGridDecoration(unittest.TestCase):
    """_clip_segment_convex / _grid_segments - the geometry behind the
    'deck_grid' culture floor decoration."""

    SQUARE = [(0, 0), (100, 0), (100, 100), (0, 100)]

    def test_clip_keeps_the_span_inside_the_polygon(self):
        a, b = _clip_segment_convex((50, -20), (50, 130), self.SQUARE)
        self.assertAlmostEqual(a[1], 0)
        self.assertAlmostEqual(b[1], 100)
        self.assertEqual((a[0], b[0]), (50, 50))

    def test_clip_returns_none_for_a_segment_that_misses(self):
        self.assertIsNone(_clip_segment_convex((200, -20), (200, 130), self.SQUARE))

    def test_clip_respects_a_diagonal_trapezoid_edge(self):
        # concourse-style wedge: the left edge slopes in toward the top
        wedge = [(0, 100), (100, 100), (70, 0), (30, 0)]
        clip = _clip_segment_convex((20, -5), (20, 105), wedge)
        self.assertIsNotNone(clip)
        (ax, ay), (bx, by) = clip
        # entry is on the sloped edge, above the floor line, not at y=0
        self.assertGreater(min(ay, by), 0)
        self.assertAlmostEqual(max(ay, by), 100)

    def test_grid_segments_all_lie_within_the_room(self):
        wedge = [(0, 100), (100, 100), (70, 0), (30, 0)]
        segs = _grid_segments(wedge, 15)
        self.assertGreater(len(segs), 4)
        for (ax, ay), (bx, by) in segs:
            for x, y in ((ax, ay), (bx, by)):
                self.assertTrue(point_in_polygon(x, y, wedge),
                                f"grid endpoint ({x:.1f},{y:.1f}) outside the room")


class TestFloorTessellation(unittest.TestCase):
    """clip_polygon_convex / tessellate - the geometry behind the interior
    'floor_pattern' tiled floor."""

    SQUARE = [(0, 0), (200, 0), (200, 200), (0, 200)]

    def test_clip_polygon_trims_an_overhanging_tile(self):
        tile = [(150, 150), (350, 150), (350, 350), (150, 350)]  # pokes out top-right
        out = _clip_polygon_convex(tile, self.SQUARE)
        self.assertGreaterEqual(len(out), 3)
        for x, y in out:
            self.assertLessEqual(x, 200 + 1e-6)
            self.assertLessEqual(y, 200 + 1e-6)

    def test_clip_polygon_drops_a_tile_fully_outside(self):
        tile = [(300, 300), (400, 300), (400, 400), (300, 400)]
        self.assertLess(len(_clip_polygon_convex(tile, self.SQUARE)), 3)

    def test_every_tile_kind_fills_the_room_and_stays_inside(self):
        for kind in ("square", "hex", "triangle", "rhombus"):
            tiles = _tessellate(self.SQUARE, kind, 40)
            self.assertGreater(len(tiles), 8, kind)
            area = 0.0
            for t in tiles:
                pts = t["points"]
                self.assertIn(t["shade"], (0, 1, 2))
                for x, y in pts:
                    self.assertTrue(-0.5 <= x <= 200.5 and -0.5 <= y <= 200.5,
                                    f"{kind} tile vertex ({x:.1f},{y:.1f}) outside the room")
                # shoelace
                a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                        for i in range(len(pts)))
                area += abs(a) / 2
            # tiles tile the room: total area is close to the room's 40000
            self.assertGreater(area, 40000 * 0.9, kind)
            self.assertLess(area, 40000 * 1.02, kind)


class TestStationWindowsAndCulture(unittest.TestCase):
    """Stations resolve their palette from their culture (like ships/
    buildings) and draw a light at each "windows" point, turning with the
    hull - see LandingSite._draw_station."""

    def test_station_alpha_inherits_the_vherathi_palette(self):
        g = utils.get_graphics_asset("default", "space_stations", "station_alpha")
        self.assertEqual(tuple(g["color"]), (72, 48, 96))          # vherathi metal_color
        self.assertEqual(tuple(g["core_color"]), (120, 255, 200))  # vherathi glass_color

    def test_station_delta_inherits_the_drossholt_glass_not_a_hardcode(self):
        g = utils.get_graphics_asset("default", "space_stations", "station_delta")
        self.assertEqual(tuple(g["core_color"]), (255, 200, 80))   # drossholt glass_color

    def test_a_windowed_station_with_no_parts_draws_one_light_per_window_plus_core(self):
        # Station shapes go through game.aa_draw (aa.circle / aa.polygon).
        with patch("game.world.landing_site.aa") as mock_aa:
            g = {"rotation_speed": 0.5, "size": 30,
                 "local_points": [[-10, -10], [10, -10], [10, 10], [-10, 10]],
                 "windows": [[0, -5], [0, 5], [5, 0]]}
            LandingSite(0, 0, graphics=g)._draw_station(MagicMock(), 1.0)
            self.assertEqual(mock_aa.circle.call_count, len(g["windows"]) + 1)

    def test_a_parts_station_skips_the_flat_hull_window_dots_and_core(self):
        """A "parts" silhouette from the atlas is the whole drawn station - it
        already includes the hull, the viewports, its own hub/core, and any
        see-through gap. _draw_station must not also stroke the flat
        local_points polygon, scatter window circles, or stamp the plain core
        beacon on top (each just shows the old shape bleeding past the new
        one). Everything is delegated to draw_parts."""
        with patch("game.world.landing_site.aa") as mock_aa, \
             patch("game.world.landing_site.pygame") as mock_pygame:
            g = utils.get_graphics_asset("default", "space_stations", "station_alpha")
            self.assertTrue(g.get("parts"))
            LandingSite(0, 0, graphics=g)._draw_station(MagicMock(), 1.0)
            mock_aa.polygon.assert_not_called()
            mock_aa.circle.assert_not_called()
            mock_pygame.draw.polygon.assert_not_called()
            mock_pygame.draw.circle.assert_not_called()

    def test_a_station_with_no_windows_draws_only_the_core(self):
        with patch("game.world.landing_site.aa") as mock_aa:
            LandingSite(0, 0, graphics={"rotation_speed": 0.5, "size": 30})._draw_station(MagicMock(), 1.0)
            self.assertEqual(mock_aa.circle.call_count, 1)


class TestLocationScreenDrawDoesNoPerFrameFontConstruction(unittest.TestCase):
    """Regression: LocationScreen.draw() built two `pygame.font.Font(None, ...)`
    objects every frame (room-label + portal-label fonts). Each construction
    opens pygame's bundled default-font file, and on Windows that file open
    has a fat latency tail (real-time AV scan) - the sporadic ~0.5 s freeze
    while walking around a station. Fonts must come from the cached
    `get_font()` helper, so a steady-state frame constructs none."""

    def test_per_frame_draw_paths_use_the_cached_get_font_helper(self):
        import inspect
        from game.screens import location_screen
        from game.world import dialogue as dialogue_mod
        from game.ui import star_map

        for label, fn in (
            ("LocationScreen.draw", location_screen.LocationScreen.draw),
            ("Dialogue.draw", dialogue_mod.Dialogue.draw),
            ("StarMap.draw_content", star_map.StarMap.draw_content),
        ):
            src = inspect.getsource(fn)
            self.assertNotIn(
                "pygame.font.Font", src,
                f"{label} constructs a font every frame - route it through utils.get_font() "
                f"so a slow (AV-scanned) font-file open can't stall the frame",
            )

    def test_config_getters_are_cached_so_the_draw_loop_reads_no_files(self):
        """Regression: LocationScreen.draw() resolves a building_type per
        structure (twice - draw + depth sort) plus a culture; each re-opened
        and re-parsed the whole JSON off disk. On a busy station (35
        structures) that was ~10 ms/frame = the 30 FPS interior. utils.load_json
        caches config reads, so the second resolve of anything opens no file."""
        import builtins
        utils.clear_json_cache()
        for fn in (lambda: utils.get_building_type("default", "vherathi_lamp"),
                   lambda: utils.get_culture("default", "vherathi"),
                   lambda: utils.get_graphics_asset("default", "ships", "shuttle"),
                   lambda: utils.get_ship_type("default", "shuttle")):
            fn()  # warm
            real_open = builtins.open
            opens = []
            with patch("builtins.open", side_effect=lambda *a, **k: opens.append(a[0]) or real_open(*a, **k)):
                fn()
            self.assertEqual(opens, [], f"a repeat config resolve re-opened {opens}")


class TestLocationScreenClickTargeting(unittest.TestCase):
    """Test LocationScreen._select_person_target_at() - click-to-target for
    NPCs/visitors on foot, the interior counterpart to SpaceScreen's own
    click-to-target over ships/landing sites."""

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


class TestLocationScreenTouchingRoomBoundary(unittest.TestCase):
    """Regression test: two touching rooms (e.g. Entrance Hall y:300-600 and
    Bar y:0-300, sharing the line y=300) both used strict "<" bounds, so a
    step that landed exactly on the shared boundary was invalid in *both*
    rooms at once - an invisible wall stranding the player one step short.
    point_in_polygon now counts an on-edge point as inside, so a step
    landing exactly on the seam is valid in at least one room."""

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
        screen.rooms = [normalize_room(r) for r in config["rooms"]]
        return screen

    def test_can_cross_from_hall_into_bar_at_every_starting_y(self):
        screen = self._make_two_room_screen()
        keys = {pygame_mock.K_UP: True, pygame_mock.K_w: False, pygame_mock.K_DOWN: False, pygame_mock.K_s: False, pygame_mock.K_LEFT: False, pygame_mock.K_a: False, pygame_mock.K_RIGHT: False, pygame_mock.K_d: False}
        max_steps = int((400 - 200) / screen.speed) + 5   # enough to walk from y=399 well past y=300
        for start_y in range(301, 400):
            screen.player.x, screen.player.y = 400, start_y
            for _ in range(max_steps):
                screen._handle_movement(keys)
                if screen.player.y <= 250:
                    break
            self.assertLessEqual(screen.player.y, 300, f"Got stuck at y={screen.player.y} starting from y={start_y}")


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

    def test_buy_ship_sets_the_bought_ship_gameplay_flags(self):
        possessions = Possessions(credits=1200)
        screen = LocationScreen(config_data={"label": "Spaceport"}, world_width=800, world_height=600, player_possessions=possessions)
        screen.buy_ship("shuttle")
        self.assertTrue(possessions.flags.get("bought_ship"))
        self.assertTrue(possessions.flags.get("bought_ship:shuttle"))

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

    def test_take_loan_uses_story_json_lender_and_amount(self):
        """Lender name + amount come from story.json's "loan" block (the
        default story: Concord Lending / 100,000cr), not a hardcoded
        literal - see LocationScreen._loan_terms."""
        screen = self._make_screen()
        screen._apply_dialogue_action("take_loan")
        self.assertEqual(screen.player.possessions.credits, 100_000)
        self.assertEqual(screen.player.possessions.loans,
                         [{"lender": "Concord Lending", "principal": 100_000}])

    def test_take_loan_with_explicit_amount_overrides_the_default(self):
        """"take_loan:<amount>" grants exactly that many credits, keeping
        the story's configured lender."""
        screen = self._make_screen()
        screen._apply_dialogue_action("take_loan:2500")
        self.assertEqual(screen.player.possessions.credits, 2500)
        self.assertEqual(screen.player.possessions.loans,
                         [{"lender": "Concord Lending", "principal": 2500}])

    def test_take_loan_sets_the_took_loan_gameplay_flag(self):
        screen = self._make_screen()
        screen._apply_dialogue_action("take_loan")
        self.assertTrue(screen.player.possessions.flags.get("took_loan"))

    def test_first_selectable_option_skips_blocked_ones_for_the_initial_hover(self):
        screen = self._make_screen(credits=0)
        options = [
            {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"},
            {"label": "Patrol - 3500cr", "action": "buy_ship:patrol"},
            {"label": "Leave"},
        ]
        self.assertEqual(screen._first_selectable_option(options), 2)  # only "Leave" is takeable
        self.assertEqual(self._make_screen(credits=1200)._first_selectable_option(options), 0)

    def test_clicking_a_blocked_dialogue_option_does_nothing(self):
        """Regression: a dim/blocked option (e.g. an unaffordable ship)
        must not be actionable, whether cursored onto or clicked."""
        screen = self._make_screen(credits=0)
        nodes = {"start": {"text": "hi", "options": [
            {"label": "Shuttle - 1200cr", "action": "buy_ship:shuttle"},
            {"label": "Leave", "next": None},
        ]}}
        screen.active_dialogue = Dialogue("Dax", nodes)
        screen._choose_dialogue_option(0)  # the unaffordable ship
        self.assertIsNotNone(screen.active_dialogue)  # still open, nothing bought
        screen._choose_dialogue_option(1)  # "Leave"
        self.assertIsNone(screen.active_dialogue)


class TestStationInteriorLayout(unittest.TestCase):
    """The default story's station interiors are each one connected polygon
    area with a single ship portal (the dormitory/corridor/concourse/
    spaceport/loan_office portal chain was collapsed - see
    docs/BACKLOG.md). Guards the authored floor plans: every NPC spawns on
    the walkable area, and a visiting pilot can path clear across it."""

    def _interior(self, system_id, landing_site_attr, key="default"):
        system = utils.load_json(f"config/stories/default/systems/{system_id}.json")
        game_screen = SpaceScreen(system, pilot_name="Test", story="default", system_id=system_id)
        return game_screen.get_interior_screen(getattr(game_screen, landing_site_attr), key)

    def test_alpha_station_is_one_interior_with_a_single_ship_portal(self):
        interior = self._interior("sol_alpha", "station")
        self.assertEqual(len(interior.portals), 1)
        self.assertTrue(interior.portals[0]["return_to_ship"])
        self.assertEqual(interior.get_exit_options(), ["ship"])

    def test_every_authored_interior_spawns_its_npcs_inside_the_walkable_area(self):
        for system_id, attr, key in [
            ("sol_alpha", "station", "default"),
            ("sol_alpha", "moon", "city"),
            ("keplers_reach", "station", "default"),
            ("keplers_reach", "moon", "city"),
            ("procyon_gate", "station", "default"),
            ("procyon_gate", "moon", "city"),
        ]:
            interior = self._interior(system_id, attr, key)
            for character in interior.npcs:
                person = character.person
                self.assertTrue(
                    interior.can_move_to(person.x, person.y),
                    f"{system_id}/{key}: {person.name} at ({person.x},{person.y}) is outside every room",
                )

    def test_a_pilot_can_path_from_the_ship_portal_across_alpha_station(self):
        interior = self._interior("sol_alpha", "station")
        start = (interior.portals[0]["x"], interior.portals[0]["y"])
        bram = next(c.person for c in interior.npcs if c.person.name == "Brahn Ossilis")
        goal = (bram.x, bram.y)
        path = interior.plan_path(start, goal)
        self.assertEqual(path[-1], goal)
        prev = start
        for point in path:
            steps = max(1, int(math.hypot(point[0] - prev[0], point[1] - prev[1]) / 6))
            for i in range(steps + 1):
                t = i / steps
                x, y = prev[0] + (point[0] - prev[0]) * t, prev[1] + (point[1] - prev[1]) * t
                self.assertTrue(interior.can_move_to(x, y), f"path leaves the walkable area at ({x:.0f},{y:.0f})")
            prev = point

    def test_old_station_save_key_resumes_at_the_ship_entry_interior(self):
        """An old save recorded station_location="dormitory" etc.; those
        keys are gone now. The load path never trusts that key - it
        re-derives the ship-entry room (LandingSite.get_ship_entry_key) and
        arrive_from("ship")s, so the player lands at the dock portal
        regardless of what the save said or where it left their body."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        self.assertIsNone(game_screen.get_interior_screen(game_screen.station, "dormitory"))
        key = game_screen.station.get_ship_entry_key()
        self.assertEqual(key, "default")
        interior = game_screen.get_interior_screen(game_screen.station, key)
        interior.restore_state({"player": {"x": 12345, "y": 999}, "possessions": {}})
        interior.arrive_from("ship")
        portal = interior.portal_for("ship")
        self.assertEqual((interior.player.x, interior.player.y), (portal["x"], portal["y"]))
        self.assertTrue(interior.can_move_to(interior.player.x, interior.player.y))


if __name__ == "__main__":
    unittest.main()
