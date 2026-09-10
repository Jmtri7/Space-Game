"""Possessions — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


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


class TestPossessionsFlags(unittest.TestCase):
    """flags (story-progress markers - see Dialogue's requires_flag/
    conditional_roots and the "set_flag:" dialogue action) round-trips
    through get_state()/restore_from()/from_state() like every other
    Possessions field - see docs/SAVE_SYSTEM.md."""

    def test_flags_round_trip_through_get_state_and_restore_from(self):
        possessions = Possessions()
        possessions.flags["hailed_kade"] = True
        state = possessions.get_state()
        self.assertEqual(state["flags"], {"hailed_kade": True})

        restored = Possessions()
        restored.restore_from(state)
        self.assertEqual(restored.flags, {"hailed_kade": True})

    def test_from_state_defaults_to_empty_flags_for_a_pre_existing_save(self):
        """A save made before this feature existed has no "flags" key at
        all - from_state()/restore_from() must default to {} rather than
        raising."""
        possessions = Possessions.from_state({"credits": 10})
        self.assertEqual(possessions.flags, {})


class TestPossessionsReputation(unittest.TestCase):
    """reputation ({faction_id: standing}, -100..+100 - see
    config/stories/{story}/factions.json and Dialogue's requires_rep /
    conditional_roots faction gate) round-trips like every other
    Possessions field, and adjust_reputation() clamps - see
    docs/SAVE_SYSTEM.md."""

    def test_reputation_with_defaults_to_zero(self):
        self.assertEqual(Possessions().reputation_with("the_vigil"), 0)

    def test_adjust_reputation_accumulates_and_clamps(self):
        p = Possessions()
        self.assertEqual(p.adjust_reputation("the_vigil", 30), 30)
        self.assertEqual(p.adjust_reputation("the_vigil", 30), 60)
        self.assertEqual(p.adjust_reputation("the_vigil", 999), 100)
        self.assertEqual(p.adjust_reputation("the_vigil", -999), -100)

    def test_reputation_round_trips_through_get_state_and_restore_from(self):
        p = Possessions()
        p.adjust_reputation("harbor_authority", 12)
        state = p.get_state()
        self.assertEqual(state["reputation"], {"harbor_authority": 12})
        restored = Possessions()
        restored.restore_from(state)
        self.assertEqual(restored.reputation, {"harbor_authority": 12})
        self.assertEqual(Possessions.from_state(state).reputation, {"harbor_authority": 12})

    def test_from_state_defaults_to_empty_reputation_for_a_pre_existing_save(self):
        self.assertEqual(Possessions.from_state({"credits": 10}).reputation, {})


class TestMessageAlertSchedule(unittest.TestCase):
    """message_alert_state() drives the Message Log's unread light + ping:
    exactly MESSAGE_ALERT_BLINKS blinks, one ping at the start of each, then
    quiet and dark (replaced a ~10s wall-clock flash with a single ping)."""

    def _run(self):
        """Every (blink_on, pings_due) the way a screen sees it: timer set to
        FRAMES, then decremented once per sim step until it hits 0."""
        out = []
        timer = MESSAGE_ALERT_FRAMES
        while timer > 0:
            timer -= 1
            out.append(message_alert_state(timer))
        out.append(message_alert_state(timer))  # the frame timer is 0
        return out

    def test_exactly_three_pings_one_per_blink(self):
        states = self._run()
        # pings_due is monotonic and ends at exactly MESSAGE_ALERT_BLINKS
        pings = [p for _, p in states]
        self.assertEqual(pings, sorted(pings))
        self.assertEqual(pings[-1], MESSAGE_ALERT_BLINKS)
        self.assertEqual(max(pings), 3)

    def test_each_ping_lands_while_the_light_is_on(self):
        # The frame pings_due first reaches N, the light must be lit - that's
        # what "in sync with the light" means.
        seen = 0
        for blink_on, pings_due in self._run():
            if pings_due > seen:
                self.assertTrue(blink_on, f"ping {pings_due} fired with the light off")
                seen = pings_due

    def test_light_blinks_then_goes_dark(self):
        states = self._run()
        # It actually toggles (some on, some off) during the alert...
        self.assertIn(True, [b for b, _ in states])
        self.assertIn(False, [b for b, _ in states])
        # ...and is dark once the timer is spent.
        self.assertEqual(message_alert_state(0), (False, MESSAGE_ALERT_BLINKS))
        self.assertEqual(message_alert_state(-5), (False, MESSAGE_ALERT_BLINKS))

    def test_frame_rate_hitch_still_totals_three(self):
        # A slow frame that jumps the timer straight past the end still only
        # ever asks for MESSAGE_ALERT_BLINKS pings total.
        _, pings_due = message_alert_state(1)
        self.assertLessEqual(pings_due, MESSAGE_ALERT_BLINKS)
        self.assertEqual(message_alert_state(0)[1], MESSAGE_ALERT_BLINKS)


class TestPossessionsMessageLog(unittest.TestCase):
    """message_log (the Space View's bottom-left Messages pane's history -
    see ui_theme.draw_message_log and SpaceScreen._check_one_way_hails) -
    add_message()'s newest-first/capped behavior, and the usual save
    round-trip."""

    def test_add_message_inserts_newest_first(self):
        possessions = Possessions()
        possessions.add_message("Kade Marsh", "Identify yourself.")
        possessions.add_message("Elena Voss", "Hello there.")
        self.assertEqual(possessions.message_log[0], {"sender": "Elena Voss", "text": "Hello there."})
        self.assertEqual(possessions.message_log[1], {"sender": "Kade Marsh", "text": "Identify yourself."})

    def test_add_message_caps_the_log_length(self):
        possessions = Possessions()
        for i in range(30):
            possessions.add_message("Someone", f"message {i}")
        self.assertEqual(len(possessions.message_log), 20)
        self.assertEqual(possessions.message_log[0]["text"], "message 29")  # newest kept

    def test_message_log_round_trips_through_get_state_and_restore_from(self):
        possessions = Possessions()
        possessions.add_message("Kade Marsh", "Identify yourself.")
        state = possessions.get_state()
        self.assertEqual(state["message_log"], [{"sender": "Kade Marsh", "text": "Identify yourself."}])

        restored = Possessions()
        restored.restore_from(state)
        self.assertEqual(restored.message_log, [{"sender": "Kade Marsh", "text": "Identify yourself."}])

    def test_from_state_defaults_to_no_messages_for_a_pre_existing_save(self):
        possessions = Possessions.from_state({"credits": 10})
        self.assertEqual(possessions.message_log, [])


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

    def test_sell_outfit_removes_a_spare_and_credits_the_price(self):
        possessions = Possessions(credits=100, owned_outfits=["laser_cannon", "laser_cannon"])
        self.assertTrue(possessions.sell_outfit("laser_cannon", 400))
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])
        self.assertEqual(possessions.credits, 500)

    def test_sell_outfit_is_a_noop_when_the_outfit_is_installed_not_a_spare(self):
        possessions = Possessions(credits=100, owned_outfits=["afterburner"])
        possessions.install_outfit("engine_1", "afterburner")
        self.assertFalse(possessions.sell_outfit("afterburner", 400))
        self.assertEqual(possessions.credits, 100)

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


if __name__ == "__main__":
    unittest.main()
