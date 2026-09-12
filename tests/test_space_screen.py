"""Space Screen — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401
from game.screens.space_screen._defs import MESSAGE_SPACING_FRAMES


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
        explorer = next(s for s in game_screen.systems["sol_alpha"].ai_ships if s.person.name == "Junae Valis")
        # Simulate it having wandered off to the other system already.
        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"
        explorer.x, explorer.y = 4242, 1337

        state = game_screen.get_state()
        self.assertEqual(state["ai_ships"]["Junae Valis"]["system_id"], "keplers_reach")

        fresh = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        fresh.restore_state(state)

        self.assertNotIn(explorer.person.name, [s.person.name for s in fresh.systems["sol_alpha"].ai_ships])
        restored = next(s for s in fresh.systems["keplers_reach"].ai_ships if s.person.name == "Junae Valis")
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
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Junae Valis")

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
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Junae Valis")

        game_screen.player.engage_seek(explorer)
        self.assertTrue(game_screen.player.autopilot_active)

        # Simulate the ship having jumped away, the way ExplorerRoutine._migrate does.
        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"

        game_screen.update_physics()

        self.assertFalse(game_screen.player.autopilot_active, "Autopilot should disengage once its target is gone")
        self.assertIsNone(game_screen.player.autopilot_target)

    def test_cycling_ships_still_reaches_every_ship_after_one_jumps_away(self):
        """Regression: a departed explorer's stale tuple stayed in
        _filtered_targets() (targetable_objects is built once per
        _activate_system and never pruned), so cycling wrapped onto a ghost
        that _validate_target cleared a frame later. Juno Vale is last in
        Sol Alpha's ship list, so once she jumped away, pressing "[" from
        the first ship wrapped straight onto her and bounced back - never
        landing on Kade Marsh in between. "]" happened to reach Kade on the
        step before the ghost, which is why only "[" looked broken."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Junae Valis")

        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"

        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        game_screen.update_physics()  # prunes the departed ship (see _validate_target)

        names = [obj.person.name for _, obj in game_screen._filtered_targets()]
        self.assertNotIn("Junae Valis", names, "Departed ship should drop out of the target list")
        self.assertEqual(set(names), {"Elae Vossae", "Kade Marsh"})

        for direction in (-1, 1):  # "[" and "]"
            seen = set()
            game_screen.current_target = None
            for _ in range(len(names) * 2):
                game_screen._cycle_target(direction)
                self.assertIsNotNone(game_screen._get_target_object())
                game_screen._validate_target()
                still_targeted = game_screen._get_target_object()
                self.assertIsNotNone(
                    still_targeted,
                    f"Cycling with direction {direction} landed on a ship that immediately got cleared")
                seen.add(still_targeted.person.name)
            self.assertEqual(seen, {"Elae Vossae", "Kade Marsh"})

    def test_a_ship_that_jumps_back_becomes_targetable_again(self):
        """_validate_target re-adds an AI ship that's returned to this
        system (ExplorerRoutine can jump back to where it started) so it
        doesn't stay untargetable until the next _activate_system."""
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        explorer = next(s for s in game_screen.ai_ships if s.person.name == "Junae Valis")
        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")

        game_screen.systems["sol_alpha"].ai_ships.remove(explorer)
        game_screen.systems["keplers_reach"].ai_ships.append(explorer)
        explorer.system_id = "keplers_reach"
        game_screen.update_physics()
        self.assertNotIn("Junae Valis", [o.person.name for _, o in game_screen._filtered_targets()])

        game_screen.systems["keplers_reach"].ai_ships.remove(explorer)
        game_screen.systems["sol_alpha"].ai_ships.append(explorer)
        explorer.system_id = "sol_alpha"
        game_screen.update_physics()
        self.assertIn("Junae Valis", [o.person.name for _, o in game_screen._filtered_targets()])


class TestJumpDrive(unittest.TestCase):
    """try_jump() (shared by K_J in the space view and J on the Star Map, via
    main.py) and the force_thrusters draw flag it sets for the jump's duration."""

    def test_try_jump_to_another_system_begins_a_jump_and_fires_thrusters(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        game_screen.selected_system_id = "keplers_reach"
        game_screen.try_jump()
        self.assertIsNotNone(game_screen.jump_state)
        self.assertTrue(game_screen.player.ship.force_thrusters,
                        "Thrusters must draw as active for the whole jump")

    def test_completing_a_jump_clears_force_thrusters(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        game_screen.selected_system_id = "keplers_reach"
        game_screen.try_jump()
        for _ in range(4000):
            if game_screen.jump_state is None:
                break
            game_screen._update_jump()
        self.assertIsNone(game_screen.jump_state)
        self.assertEqual(game_screen.system_id, "keplers_reach")
        self.assertFalse(game_screen.player.ship.force_thrusters)

    def test_self_jump_from_near_the_centre_is_refused(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default", system_id="sol_alpha")
        cx, cy = GAME_WIDTH / 2, GAME_HEIGHT / 2
        game_screen.player.x, game_screen.player.y = cx, cy
        game_screen.selected_system_id = game_screen.system_id
        game_screen.try_jump()
        self.assertIsNone(game_screen.jump_state, "Too close to centre - no jump")
        self.assertGreater(game_screen.jump_message_timer, 0, "Shows the 'too close' notice")


class TestShipHealth(unittest.TestCase):
    """Ship.health / take_damage / park-repair, and apply_ship_type's
    max_health (from ship_types.json's "max_health", else size-derived) -
    the hull model behind ship-to-ship combat (see docs/ARCHITECTURE.md's
    Weapons & Combat)."""

    def test_take_damage_reports_destruction_at_zero(self):
        s = Ship(0, 0)
        s.max_health = s.health = 10
        self.assertFalse(s.take_damage(4))
        self.assertEqual(s.health, 6)
        self.assertTrue(s.take_damage(6))

    def test_park_repairs_to_full(self):
        s = Ship(0, 0)
        s.max_health = 20
        s.health = 3
        s.park()
        self.assertEqual(s.health, 20)

    def test_apply_ship_type_takes_max_health_or_derives_from_size(self):
        explicit = Ship(0, 0)
        explicit.apply_ship_type({"size": 10, "max_health": 55})
        self.assertEqual(explicit.max_health, 55)
        derived = Ship(0, 0)
        derived.apply_ship_type({"size": 20})  # max(20, 20*2.5) == 50
        self.assertEqual(derived.max_health, 50)

    def test_apply_ship_type_preserves_the_current_damage_fraction(self):
        s = Ship(0, 0)
        s.apply_ship_type({"size": 20})   # max_health 50
        s.health = 25                      # half hull
        s.apply_ship_type({"size": 20, "max_health": 80})
        self.assertEqual(s.health, 40)     # still half

    def test_apply_outfits_max_health_modifier_raises_the_hull(self):
        s = Ship(0, 0)
        s.apply_ship_type({"size": 20})   # max_health 50
        s.apply_outfits([{"stat_modifiers": {"max_health": 35}}])   # shield capacitor
        self.assertEqual(s.max_health, 85)
        self.assertEqual(s.health, 85)    # was at full, stays at full

    def test_apply_outfits_max_health_keeps_the_damage_fraction(self):
        s = Ship(0, 0)
        s.apply_ship_type({"size": 20})   # max_health 50
        s.health = 25                     # half hull
        s.apply_outfits([{"stat_modifiers": {"max_health": 50}}])
        self.assertEqual(s.max_health, 100)
        self.assertEqual(s.health, 50)    # still half


class TestShipCombat(unittest.TestCase):
    """Ship-to-ship combat: _sync_hostiles swaps a low-standing pilot into
    CombatRoutine and back, player fire destroys an AI ship, AI fire damages
    the player, and a destroyed player recovers at the station (cargo lost).
    Uses the_long_silence (its outer factions can drop below the hostile
    threshold)."""

    def _combat_screen(self):
        gs = SpaceScreen(pilot_name="T", story="the_long_silence", system_id="halcyon")
        gs.in_flight = True
        gs._apply_ship_type("courier")
        gs.player.x, gs.player.y = 1200, 1000
        hostile = gs.systems["halcyon"].ai_ships[0]
        hostile.faction = "ninefold_combine"
        hostile.person.name = "Bandit"
        hostile.ship.x, hostile.ship.y = 1200, 1350
        hostile.ship.velocity_x = hostile.ship.velocity_y = 0
        return gs, hostile

    def test_sync_hostiles_engages_below_threshold_and_stands_down_above(self):
        gs, hostile = self._combat_screen()
        gs.player.person.possessions.reputation["ninefold_combine"] = -60
        gs._sync_hostiles()
        self.assertTrue(hostile.in_combat)
        self.assertIsInstance(hostile.routine, CombatRoutine)
        gs.player.person.possessions.reputation["ninefold_combine"] = 0
        gs._sync_hostiles()
        self.assertFalse(hostile.in_combat)
        self.assertNotIsInstance(hostile.routine, CombatRoutine)

    def test_a_per_pilot_flag_also_makes_a_ship_hostile(self):
        gs, hostile = self._combat_screen()
        gs.player.person.possessions.flags["hostile_to_player:Bandit"] = True
        gs._sync_hostiles()
        self.assertTrue(hostile.in_combat)

    def test_shooting_an_untargeted_neutral_ship_passes_through_harmlessly(self):
        from game.world.projectile import Projectile
        gs, victim = self._combat_screen()   # faction ninefold_combine, standing 0
        pos = gs.player.person.possessions
        self.assertFalse(victim.in_combat)
        # Not hostile and not the player's current target - the shot must
        # pass through rather than land and provoke it (see combat.py's
        # hostility gate on _check_projectile_ship_collision).
        gs.projectiles.append(Projectile(victim.ship.x, victim.ship.y, 0, 0, damage=3, owner="player"))
        gs._update_projectiles()
        self.assertFalse(pos.flags.get("hostile_to_player:Bandit"))
        self.assertEqual(victim.ship.health, victim.ship.max_health)

    def test_shooting_a_targeted_neutral_ship_provokes_it_and_dents_faction_standing(self):
        from game.world.projectile import Projectile
        gs, victim = self._combat_screen()   # faction ninefold_combine, standing 0
        pos = gs.player.person.possessions
        self.assertFalse(victim.in_combat)
        gs._select_target(victim)  # deliberately targeted, so a shot can still land pre-hostility
        gs.projectiles.append(Projectile(victim.ship.x, victim.ship.y, 0, 0, damage=3, owner="player"))
        gs._update_projectiles()
        self.assertTrue(pos.flags.get("hostile_to_player:Bandit"))
        self.assertEqual(pos.reputation_with("ninefold_combine"), -10)  # one-time hit
        gs._sync_hostiles()
        self.assertIsInstance(victim.routine, CombatRoutine)
        # more hits on the same ship don't keep dropping standing
        for _ in range(4):
            gs.projectiles.append(Projectile(victim.ship.x, victim.ship.y, 0, 0, damage=1, owner="player"))
            gs._update_projectiles()
        self.assertEqual(pos.reputation_with("ninefold_combine"), -10)

    def test_player_fired_shots_damage_and_destroy_a_hostile_ship(self):
        from game.world.projectile import Projectile
        gs, hostile = self._combat_screen()
        hostile.in_combat = True  # already hostile - a player shot lands without needing to be targeted first
        hostile.ship.health = hostile.ship.max_health
        while hostile in gs.systems["halcyon"].ai_ships:
            gs.projectiles.append(Projectile(hostile.ship.x, hostile.ship.y, 0, 0, damage=6, owner="player"))
            gs._update_projectiles()
            if hostile.ship.health < -100:
                self.fail("hostile never removed from the roster")
        self.assertNotIn(hostile, gs.systems["halcyon"].ai_ships)

    def test_an_ai_fired_shot_damages_the_player_and_never_its_owner(self):
        from game.world.projectile import Projectile
        gs, hostile = self._combat_screen()
        hostile.in_combat = True  # only a hostile pilot's shots can land on the player
        full = gs.player.ship.health
        # A shot sitting on the player, fired by the AI - hits the player.
        gs.projectiles.append(Projectile(gs.player.x, gs.player.y, 0, 0, damage=5, owner=hostile))
        gs._update_projectiles()
        self.assertEqual(gs.player.ship.health, full - 5)
        # A shot sitting on its own AI owner - never hits it.
        h0 = hostile.ship.health
        gs.projectiles.append(Projectile(hostile.ship.x, hostile.ship.y, 0, 0, damage=5, owner=hostile))
        gs._update_projectiles()
        self.assertEqual(hostile.ship.health, h0)

    def test_destroyed_player_ends_the_run_instead_of_respawning(self):
        gs, hostile = self._combat_screen()
        gs.player.person.possessions.add_cargo("ore", 7)
        gs.player.ship.health = 1
        gs._on_player_destroyed()
        # No Rescue Service respawn - the run just ends, flagged for
        # main.py's SpaceScreen.update() -> "game_over" -> Game Over screen
        # handoff (see docs/UI_FLOW.md's EndingScreen section).
        self.assertTrue(gs.game_over)
        self.assertEqual(gs.game_over_cargo_lost, 7)
        self.assertEqual(gs.player.person.possessions.cargo_quantity_total(), 7)

    def test_update_returns_game_over_the_frame_the_hull_fails(self):
        from game.world.projectile import Projectile
        gs, hostile = self._combat_screen()
        # gs.update() runs _sync_hostiles() every frame, which would
        # immediately flip a directly-set hostile.in_combat back off since
        # nothing else marks this pilot hostile - set the persistent flag
        # instead, so it survives that resync and the shot can land.
        gs.player.person.possessions.flags["hostile_to_player:Bandit"] = True
        gs.player.ship.health = 1
        gs.projectiles.append(Projectile(gs.player.x, gs.player.y, 0, 0, damage=5, owner=hostile))
        self.assertEqual(gs.update(), "game_over")

    def test_ai_and_player_ship_health_round_trip_through_save(self):
        gs, hostile = self._combat_screen()
        gs.player.ship.health = 12.5
        hostile.ship.health = 8
        state = gs.get_state()
        self.assertEqual(state["player"]["health"], 12.5)
        target_name = hostile.person.name  # renamed to "Bandit" by _combat_screen
        gs2 = SpaceScreen(pilot_name="T", story="the_long_silence", system_id="halcyon")
        # match gs's renamed roster so the by-name save lookup resolves
        gs2.systems["halcyon"].ai_ships[0].person.name = target_name
        gs2._apply_ship_type("courier")
        gs2.restore_state(state)
        self.assertEqual(gs2.player.ship.health, 12.5)
        restored_hostile = next(a for a in gs2.systems["halcyon"].ai_ships if a.person.name == target_name)
        self.assertEqual(restored_hostile.ship.health, 8)


class TestSpaceScreenShipTypePersistence(unittest.TestCase):
    """Regression test: SpaceScreen.__init__() always starts the player's
    Ship from story.json's default player_type - after buying a ship and
    saving, loading the save (a fresh SpaceScreen + restore_state()) used
    to silently revert the player back to that story default instead of
    whatever they'd actually bought, even though Possessions itself
    restored correctly."""

    def test_restore_state_reequips_the_last_purchased_ship(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        spaceport = game_screen.get_interior_screen(game_screen.station, "default")
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
        spaceport = game_screen.get_interior_screen(game_screen.station, "default")
        spaceport._apply_dialogue_action("buy_ship:shuttle")

        docked_state = spaceport.get_state()  # {"player": {...}, "possessions": {...}} - no ai_ships key

        fresh = SpaceScreen(pilot_name="Test", story="default")
        fresh.restore_possessions(docked_state)
        self.assertEqual(fresh.player.ship.graphics.get("size"), 10)


class TestSpaceScreenHailing(unittest.TestCase):
    """R-key hailing (see SpaceScreen.handle_input/_start_hail) and NPC-
    initiated one-way hails (_check_one_way_hails) - exercised against the
    default story's real pilots.json/sol_alpha.json config: Kade Marsh
    (patrol_officer, OrbitRoutine - never ashore, and configured with both
    a one_way_hail and a branching hail_dialogue_tree) and Elena Voss
    (freighter_pilot, DockRoutine - can be ashore) are real fixtures here,
    not test doubles, so a config typo in either would fail these too."""

    def _target_ship(self, game_screen, pilot_name):
        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        for i, (_, obj) in enumerate(game_screen._filtered_targets()):
            if obj.person.name == pilot_name:
                game_screen.current_target = i
                return obj
        self.fail(f"{pilot_name} not found among targetable ships")

    def test_hailing_a_flying_pilot_opens_their_hail_dialogue(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        self._target_ship(game_screen, "Kade Marsh")
        game_screen._start_hail()
        self.assertIsNotNone(game_screen.active_dialogue)
        self.assertEqual(game_screen.active_dialogue.npc_name, "Kade Marsh")
        self.assertEqual(game_screen.active_dialogue.current_node, "start")

    def test_hailing_an_ashore_pilot_shows_a_busy_banner_instead(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        elena = self._target_ship(game_screen, "Elae Vossae")
        elena.ashore = True
        game_screen._start_hail()
        self.assertIsNone(game_screen.active_dialogue)
        self.assertIn("docked", game_screen.hail_banner[0])

    def test_hailing_with_no_target_does_nothing(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.current_target = None
        game_screen._start_hail()
        self.assertIsNone(game_screen.active_dialogue)

    def test_one_way_hail_fires_once_in_range_and_sets_a_seen_flag(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.in_flight = True
        kade = self._target_ship(game_screen, "Kade Marsh")
        game_screen.player.x, game_screen.player.y = kade.x, kade.y  # distance 0 - well within range
        game_screen._check_one_way_hails()
        self.assertIsNotNone(game_screen.hail_banner)
        self.assertIn("Kade Marsh", game_screen.hail_banner[0])
        flags = game_screen.player.person.possessions.flags
        self.assertTrue(flags.get("one_way_hail_seen:Kade Marsh"))
        # Also logged (see Possessions.add_message) - the banner alone is
        # easy to miss, so it stays in the Messages pane too.
        message_log = game_screen.player.person.possessions.message_log
        self.assertEqual(message_log[0]["sender"], "Kade Marsh")

        game_screen.hail_banner = None
        game_screen._check_one_way_hails()
        self.assertIsNone(game_screen.hail_banner, "must not fire a second time for the same pilot")
        self.assertEqual(len(message_log), 1, "must not log a second time for the same pilot")

    def test_one_way_hail_is_suppressed_while_docked(self):
        """update_physics() keeps running in the background while the player
        is docked in an interior; a pilot hailing the cockpit shouldn't
        land while nobody's in it (see SpaceScreen.in_flight)."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.in_flight = False  # docked
        kade = self._target_ship(game_screen, "Kade Marsh")
        game_screen.player.x, game_screen.player.y = kade.x, kade.y
        game_screen._check_one_way_hails()
        self.assertIsNone(game_screen.hail_banner)
        flags = game_screen.player.person.possessions.flags
        self.assertFalse(flags.get("one_way_hail_seen:Kade Marsh"))
        self.assertEqual(game_screen.player.person.possessions.message_log, [])


class TestSpaceScreenMinimapTargeting(unittest.TestCase):
    """Minimap click-to-target + hover text (see SpaceScreen._select_target /
    _minimap_blip_at / _minimap_label, and the minimap branch in
    handle_input). Exercised against the default story's real sol_alpha
    config, so station/moon/pilot fixtures are real, not doubles."""

    def _first_ship(self, game_screen):
        self.assertTrue(game_screen.ai_ships, "sol_alpha should have AI ships")
        return game_screen.ai_ships[0]

    def test_select_target_switches_mode_and_points_at_the_object(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.target_mode_index = TARGET_MODES.index("LANDING SITES")
        ship = self._first_ship(game_screen)
        game_screen._select_target(ship)
        self.assertEqual(TARGET_MODES[game_screen.target_mode_index], "SHIPS")
        self.assertIs(game_screen._get_target_object(), ship)

    def test_select_target_on_a_landing_site_switches_to_landing_sites_mode(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.target_mode_index = TARGET_MODES.index("SHIPS")
        game_screen._select_target(game_screen.moon)
        self.assertEqual(TARGET_MODES[game_screen.target_mode_index], "LANDING SITES")
        self.assertIs(game_screen._get_target_object(), game_screen.moon)

    def test_minimap_blip_at_returns_the_closest_blip_within_its_hit_radius(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        ship = self._first_ship(game_screen)
        # (screen_x, screen_y, hit_radius, obj) - the shape _draw_minimap builds.
        game_screen._minimap_blips = [
            (100, 100, 10, game_screen.station),
            (105, 100, 10, ship),
        ]
        self.assertIs(game_screen._minimap_blip_at((104, 100)), ship)
        self.assertIs(game_screen._minimap_blip_at((97, 100)), game_screen.station)
        self.assertIsNone(game_screen._minimap_blip_at((500, 500)))

    def test_minimap_label_names_the_object_and_pilot(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        self.assertEqual(game_screen._minimap_label(game_screen.station), game_screen.station.name)
        ship = self._first_ship(game_screen)
        label = game_screen._minimap_label(ship)
        self.assertIn(ship.person.name, label)


class TestSpaceScreenStartConfig(unittest.TestCase):
    """story.json's "start" block + starting_mission_trigger - the player's
    state and world placement at the beginning of a brand-new game (see
    SpaceScreen._apply_start_config / begin_new_game). A loaded save is
    unaffected: restore_possessions() overwrites all of this."""

    def test_default_story_begins_shipless_in_the_station_interior(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        location, interior = game_screen.begin_new_game()
        self.assertEqual((location, interior), ("station", "default"))
        self.assertEqual(game_screen.player.person.possessions.owned_ships, [])
        self.assertEqual(game_screen.player.person.possessions.credits, 0)
        # trigger is "ship_purchase" - no mission before a ship is bought
        self.assertNotIn("first_flight", game_screen.player.person.possessions.missions)

    def test_apply_start_config_seeds_credits_ship_items_and_flags(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.start_config = {
            "credits": 4200, "ship": "shuttle",
            "items": {"data_chip": 2}, "outfits": ["cargo_expansion"],
            "flags": {"met_the_broker": True},
        }
        game_screen._apply_start_config()
        possessions = game_screen.player.person.possessions
        self.assertEqual(possessions.credits, 4200)
        self.assertEqual(possessions.owned_ships, ["shuttle"])
        self.assertEqual(possessions.items, {"data_chip": 2})
        self.assertEqual(possessions.owned_outfits, ["cargo_expansion"])
        self.assertTrue(possessions.flags.get("met_the_broker"))
        # ship stats were actually applied, not just recorded
        self.assertEqual(game_screen.player.ship.max_velocity,
                         utils.get_ship_type("default", "shuttle")["max_velocity"])

    def test_a_starting_ship_triggers_the_tutorial_on_new_game(self):
        """With no purchase to hook, begin_new_game() must fire the
        starting_mission itself when the story grants a ship."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.start_config = {"ship": "shuttle", "location": "space"}
        game_screen._apply_start_config()
        location, interior = game_screen.begin_new_game()
        self.assertEqual((location, interior), ("space", None))
        self.assertEqual(game_screen.player.person.possessions.missions.get("first_flight"), 0)

    def test_new_game_trigger_arms_the_mission_and_launch_starts_it(self):
        """A "new_game" trigger with a docked start still defers to the
        first launch (board_ship()) - so the opening toast/hail land in
        the cockpit, not the station the player begins in."""
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.starting_mission_trigger = "new_game"
        game_screen.begin_new_game()  # default start location is "station"
        possessions = game_screen.player.person.possessions
        self.assertNotIn("first_flight", possessions.missions)
        self.assertTrue(possessions.flags.get("starting_mission_armed"))
        game_screen.board_ship()
        self.assertEqual(possessions.missions.get("first_flight"), 0)


class TestSpaceScreenAudioCues(unittest.TestCase):
    """The two extra space-view SFX hooks: "confirm" on engaging autopilot,
    "blip" on changing/cycling the target. Exercised against the default
    story's real config, like TestSpaceScreenHailing."""

    def test_engaging_autopilot_plays_confirm(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.target_mode_index = TARGET_MODES.index("LANDING SITES")
        game_screen.current_target = 0
        ev = SimpleNamespace(type=pygame_mock.KEYDOWN, key=pygame_mock.K_f, mod=0)
        with patch("game.audio.sound_board.sound_board.play") as mock_play:
            game_screen.handle_input([ev])
            mock_play.assert_any_call("confirm")
        self.assertTrue(game_screen.player.autopilot_active)

    def test_cycling_target_mode_plays_blip(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        with patch("game.audio.sound_board.sound_board.play") as mock_play:
            game_screen._cycle_target_mode()
            mock_play.assert_called_once_with("blip")

    def test_unread_message_pings_exactly_three_times_per_loop_until_clicked(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        # Silence the other per-frame message sources so we count only the
        # alert's own pings.
        game_screen.ai_ships = []
        game_screen.missions_config = {}
        with patch("game.audio.sound_board.sound_board.play") as mock_play:
            game_screen._post_message("Kade Marsh", "Come in.")
            for _ in range(MESSAGE_ALERT_FRAMES + 10):
                game_screen.update()
            pings = [c for c in mock_play.call_args_list if c.args == ("ping",)]
        # Unlike a finite alert, an unread message is pinned (see
        # _unread_alert_pinned) - the cycle re-arms instead of stopping
        # after MESSAGE_ALERT_BLINKS, so a 4th ping has already started.
        self.assertEqual(len(pings), 4)
        self.assertGreater(game_screen.message_alert_timer, 0)
        self.assertTrue(game_screen._unread_alert_pinned)

    def test_a_burst_of_messages_spaces_out_instead_of_landing_at_once(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.ai_ships = []
        game_screen.missions_config = {}
        log = game_screen.player.person.possessions.message_log
        for i in range(4):
            game_screen._post_message("Relay", f"m{i}")
        # only the first lands immediately; the rest are held back
        self.assertEqual([m["text"] for m in log], ["m0"])
        self.assertEqual(len(game_screen._message_queue), 3)
        # half a spacing interval later: still nothing new
        for _ in range(MESSAGE_SPACING_FRAMES // 2):
            game_screen.update()
        self.assertEqual(len(log), 1)
        # run well past four intervals: all drained, in order, newest first
        for _ in range(MESSAGE_SPACING_FRAMES * 4 + 5):
            game_screen.update()
        self.assertEqual([m["text"] for m in log], ["m3", "m2", "m1", "m0"])
        self.assertEqual(game_screen._message_queue, [])

    def test_an_isolated_later_message_is_not_delayed(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.ai_ships = []
        game_screen.missions_config = {}
        log = game_screen.player.person.possessions.message_log
        game_screen._post_message("Relay", "first")
        for _ in range(MESSAGE_SPACING_FRAMES + 5):
            game_screen.update()
        game_screen._post_message("Relay", "second")
        self.assertEqual([m["text"] for m in log], ["second", "first"])

    def test_any_message_alert_keeps_looping_until_clicked(self):
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.ai_ships = []
        game_screen.missions_config = {}
        game_screen._post_message("Relay", "Beacon relit.")
        self.assertTrue(game_screen._unread_alert_pinned)
        # Run well past where the old fixed 3-blink alert would have gone
        # quiet (message_alert_state returns (False, ...) once frames_remaining
        # hits 0) - a pinned alert re-arms instead of stopping.
        for _ in range(MESSAGE_ALERT_FRAMES * 3):
            game_screen.update()
        self.assertGreater(game_screen.message_alert_timer, 0)
        self.assertTrue(game_screen._unread_alert_pinned)

    def test_clicking_the_messages_pane_silences_the_alert(self):
        import pygame as mocked_pygame
        game_screen = SpaceScreen(pilot_name="Test", story="default")
        game_screen.ai_ships = []
        game_screen.missions_config = {}
        game_screen._post_message("Elian Marr", "Something's wrong.")
        game_screen._message_log_rect = SimpleNamespace(collidepoint=lambda p: True)
        event = SimpleNamespace(type=mocked_pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 510))
        game_screen.handle_input([event])
        self.assertFalse(game_screen._unread_alert_pinned)
        self.assertEqual(game_screen.message_alert_timer, 0)
        for _ in range(MESSAGE_ALERT_FRAMES * 2):
            game_screen.update()
        self.assertEqual(game_screen.message_alert_timer, 0)


class TestPirateAmbushPeriodicReroll(unittest.TestCase):
    """The lone_pirate "pirate_ambush" event (mining_101's deep_belt) rolls
    on system entry and then again every interval_seconds while the player
    keeps flying there - see game/screens/space_screen/pirates.py."""

    def _screen(self):
        game_screen = SpaceScreen(pilot_name="Test", story="mining_101", system_id="deep_belt")
        game_screen.in_flight = True
        return game_screen

    def test_entry_arms_the_recheck_timer_off_the_configured_interval(self):
        from game import constants
        game_screen = self._screen()
        state = game_screen.systems["deep_belt"]
        interval = min(e.get("interval_seconds", 60) for e, _ in state.pirate_ambush_configs)
        self.assertEqual(game_screen.pirate_ambush_recheck_timer, int(interval * constants.FPS))

    def test_periodic_recheck_rerolls_and_rearms_after_a_miss(self):
        game_screen = self._screen()
        # Construction itself already rolled the entry chance (unpatched,
        # real odds) - pin the pre-recheck state so this test's own miss
        # isn't masked by that earlier, unrelated roll.
        game_screen.pirate_ambush = None
        game_screen.pirate_ambush_recheck_timer = 1
        with patch("random.random", return_value=1.0):  # guaranteed miss
            game_screen._update_periodic_pirate_ambush()
        self.assertIsNone(game_screen.pirate_ambush)
        self.assertGreater(game_screen.pirate_ambush_recheck_timer, 0)  # rearmed regardless

    def test_periodic_recheck_can_spawn_a_fresh_ambush_after_the_first_resolved(self):
        game_screen = self._screen()
        game_screen.pirate_ambush = None  # first encounter already resolved
        game_screen.pirate_ambush_recheck_timer = 1
        with patch("random.random", return_value=0.0):  # guaranteed hit
            game_screen._update_periodic_pirate_ambush()
        self.assertIsNotNone(game_screen.pirate_ambush)

    def test_no_recheck_while_docked(self):
        game_screen = self._screen()
        game_screen.in_flight = False
        game_screen.pirate_ambush_recheck_timer = 1
        game_screen._update_periodic_pirate_ambush()
        self.assertEqual(game_screen.pirate_ambush_recheck_timer, 1)  # untouched


class TestDerelictShipEvents(unittest.TestCase):
    """The "derelict_ship" system-event kind (mining_101's prospect_belt) -
    see game/screens/space_screen/derelicts.py."""

    def _screen(self):
        game_screen = SpaceScreen(pilot_name="Test", story="mining_101", system_id="prospect_belt")
        game_screen.in_flight = True
        return game_screen

    def test_entry_arms_the_recheck_timer_off_the_configured_interval(self):
        from game import constants
        game_screen = self._screen()
        state = game_screen.systems["prospect_belt"]
        interval = min(e.get("interval_seconds", 60) for (_, e), _ in state.derelict_configs)
        self.assertEqual(game_screen.derelict_recheck_timer, int(interval * constants.FPS))

    def test_periodic_recheck_rerolls_and_rearms_after_a_miss(self):
        game_screen = self._screen()
        game_screen.derelict = None
        game_screen.derelict_recheck_timer = 1
        with patch("random.random", return_value=1.0):  # guaranteed miss
            game_screen._update_periodic_derelict()
        self.assertIsNone(game_screen.derelict)
        self.assertGreater(game_screen.derelict_recheck_timer, 0)  # rearmed regardless

    def test_periodic_recheck_can_spawn_a_fresh_derelict_after_the_first_resolved(self):
        game_screen = self._screen()
        game_screen.derelict = None
        game_screen.derelict_recheck_timer = 1
        with patch("random.random", return_value=0.0):  # guaranteed hit
            game_screen._update_periodic_derelict()
        self.assertIsNotNone(game_screen.derelict)

    def test_no_recheck_while_docked(self):
        game_screen = self._screen()
        game_screen.in_flight = False
        game_screen.derelict_recheck_timer = 1
        game_screen._update_periodic_derelict()
        self.assertEqual(game_screen.derelict_recheck_timer, 1)  # untouched

    def test_spawn_places_the_wreck_beyond_both_render_view_and_minimap_range(self):
        """The whole point of _derelict_spawn_distance: a fresh derelict must
        never land on-screen (even at minimum zoom) or inside minimap
        detection range - see the module docstring's reasoning."""
        import math
        from game.screens.space_screen._defs import GAME_WIDTH, GAME_HEIGHT, MINIMAP_RANGE
        game_screen = self._screen()
        state = game_screen.systems["prospect_belt"]
        game_screen.derelict = None
        (event_id, event), _ = state.derelict_configs[0]
        with patch("random.random", return_value=0.0):
            game_screen._spawn_derelict(state, event_id, event)
        wreck = game_screen.derelict["object"]
        distance = math.hypot(wreck.x - game_screen.player.x, wreck.y - game_screen.player.y)
        half_diagonal = 0.5 * math.hypot(GAME_WIDTH, GAME_HEIGHT) / game_screen.camera_zoom_min
        self.assertGreater(distance, half_diagonal)
        self.assertGreater(distance, MINIMAP_RANGE)

    def test_derelict_is_not_selectable_until_in_target_range(self):
        """Targeting-range gate (targeting.py._in_target_range) - a derelict
        spawns far outside DERELICT_TARGET_RANGE, so it must not appear in
        the MISC target-mode cycle until the player closes the distance."""
        from game.screens.space_screen.derelicts import DERELICT_TARGET_RANGE
        game_screen = self._screen()
        state = game_screen.systems["prospect_belt"]
        game_screen.derelict = None
        (event_id, event), _ = state.derelict_configs[0]
        with patch("random.random", return_value=0.0):
            game_screen._spawn_derelict(state, event_id, event)
        wreck = game_screen.derelict["object"]
        game_screen.target_mode_index = TARGET_MODES.index("MISC")
        self.assertNotIn(wreck, [obj for _, obj in game_screen._filtered_targets()])

        # Move the wreck within range (cheaper than actually flying there) -
        # it should now be a selectable MISC target.
        wreck.x = game_screen.player.x + DERELICT_TARGET_RANGE * 0.5
        wreck.y = game_screen.player.y
        self.assertIn(wreck, [obj for _, obj in game_screen._filtered_targets()])

    def test_rescue_outcome_sets_a_hitching_passenger_flag_and_despawns(self):
        game_screen = self._screen()
        state = game_screen.systems["prospect_belt"]
        event = {"kind": "derelict_ship", "outcome": "rescue", "name": "Stranded Skiff",
                 "ship_type": "mining_skiff", "payout_range": [200, 200]}
        with patch("random.random", return_value=0.0):
            game_screen._spawn_derelict(state, "stranded_skiff", event)
        wreck = game_screen.derelict["object"]
        game_screen._resolve_derelict_rescue(wreck)
        flags = game_screen.player.person.possessions.flags
        self.assertEqual(flags.get("hitching_passenger"), "stranded_skiff")
        self.assertEqual(flags.get("rescue_payout:stranded_skiff"), 200)
        self.assertIsNone(game_screen.derelict)

    def test_docking_pays_out_and_clears_the_hitching_passenger(self):
        game_screen = self._screen()
        possessions = game_screen.player.person.possessions
        possessions.flags["hitching_passenger"] = "stranded_skiff"
        possessions.flags["rescue_payout:stranded_skiff"] = 250
        credits_before = possessions.credits
        game_screen.landing_target = "station"
        game_screen._mark_landed()
        self.assertEqual(possessions.credits, credits_before + 250)
        self.assertFalse(possessions.flags.get("hitching_passenger"))
        self.assertNotIn("rescue_payout:stranded_skiff", possessions.flags)

    def test_trap_outcome_spawns_an_already_hostile_pirate(self):
        game_screen = self._screen()
        state = game_screen.systems["prospect_belt"]
        event = {"kind": "derelict_ship", "outcome": "trap", "name": "Suspicious Wreck",
                 "ship_type": "raider_skiff", "pirate_ship_type": "raider_skiff",
                 "pirate_pilot": "wreck_raider", "explosion_damage": 5}
        with patch("random.random", return_value=0.0):
            game_screen._spawn_derelict(state, "suspect_wreck", event)
        wreck = game_screen.derelict["object"]
        health_before = game_screen.player.ship.health
        game_screen._resolve_derelict_trap(wreck)
        self.assertLess(game_screen.player.ship.health, health_before)
        spawned = next((s for s in state.ai_ships if s.person.name == "Scrap-tooth"), None)
        self.assertIsNotNone(spawned, "trap should spawn the configured pirate pilot")
        self.assertTrue(game_screen.player.person.possessions.flags.get("hostile_to_player:Scrap-tooth"))
        self.assertIsNone(game_screen.derelict)

    def test_loot_interior_has_a_culture_so_its_room_actually_renders(self):
        """Regression: a "rooms" list with no "culture" is silently dropped
        by LocationScreen (self.rooms stays [] and self.floor_color stays
        None - see game/screens/location_screen/screen.py) - the generated
        interior looked like open space with nothing to stand on until a
        culture was added. See config/modules/system-events/cultures.json's
        "derelict_hull"."""
        game_screen = self._screen()
        state = game_screen.systems["prospect_belt"]
        event = {"kind": "derelict_ship", "outcome": "loot", "name": "Adrift Hauler",
                 "ship_type": "courier", "loot": {"credits_range": [100, 100]}}
        with patch("random.random", return_value=0.0):
            game_screen._spawn_derelict(state, "adrift_hauler", event)
        wreck = game_screen.derelict["object"]
        interior_config = game_screen._build_loot_interior_config(wreck)
        self.assertEqual(interior_config.get("culture"), "derelict_hull")
        self.assertTrue(interior_config.get("rooms"))

        # Actually building a LocationScreen from it should resolve a real
        # floor_color and a non-empty walkable room, not the None/[] that a
        # culture-less config left it with.
        location_screen = game_screen.get_interior_screen(
            LandingSite(wreck.x, wreck.y, graphics={"size": wreck.size},
                        interiors={"default": interior_config}, name=wreck.name),
            "default",
        )
        self.assertIsNotNone(location_screen.floor_color)
        self.assertTrue(location_screen.rooms)

    def test_loot_containers_render_as_item_icons_not_walking_figures(self):
        """A loot container is an ordinary NPC/Character (dialogue and
        T-to-talk range keep working) but must look like an object, not a
        person - see Person.icon_shape/_draw_icon."""
        game_screen = self._screen()
        state = game_screen.systems["prospect_belt"]
        event = {"kind": "derelict_ship", "outcome": "loot", "name": "Adrift Hauler",
                 "ship_type": "courier",
                 "loot": {"credits_range": [50, 50], "cargo": [{"commodity": "ore", "qty_range": [5, 5]}],
                          "items": ["salvaged_part"]}}
        with patch("random.random", return_value=0.0):
            game_screen._spawn_derelict(state, "adrift_hauler", event)
        wreck = game_screen.derelict["object"]
        interior_config = game_screen._build_loot_interior_config(wreck)
        npcs_cfg = interior_config["npcs"]
        self.assertEqual(len(npcs_cfg), 3)  # credit stash + one cargo crate + one item
        for npc_cfg in npcs_cfg:
            self.assertTrue(npc_cfg.get("icon_shape"), f"{npc_cfg['name']} should have an icon_shape")
            self.assertTrue(npc_cfg.get("icon_color"), f"{npc_cfg['name']} should have an icon_color")

        location_screen = game_screen.get_interior_screen(
            LandingSite(wreck.x, wreck.y, graphics={"size": wreck.size},
                        interiors={"default": interior_config}, name=wreck.name),
            "default",
        )
        self.assertEqual(len(location_screen.npcs), 3)
        for character in location_screen.npcs:
            self.assertEqual(character.person.icon_shape, character.person.icon_shape)  # sanity: attr exists
            self.assertIsNotNone(character.person.icon_shape)


if __name__ == "__main__":
    unittest.main()
