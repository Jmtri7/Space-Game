"""UI — split from the former 6376-line tests/test_helpers.py.
Shared setup (pygame mock, imports, _FakeFont) lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from tests.harness import _FakeFont  # noqa: F401


class TestMenuDialogClassification(unittest.TestCase):
    """The menu-vs-dialog split (see game/ui/menu_base.py): both hide the
    Controls pane and drive their actions with buttons; a dialog additionally
    closes on any pick."""

    def test_is_dialog_flags(self):
        self.assertFalse(ReportMenu("x", [[]]).is_dialog)
        self.assertFalse(BackdropMenu("x", [("a", "A", None)]).is_dialog)
        self.assertTrue(ChoiceDialog("x", [("a", "A", None)]).is_dialog)
        self.assertTrue(ConfirmDialog("x", "y").is_dialog)

    def test_no_modal_renders_a_controls_pane(self):
        # help_items() was the Controls-pane hook - it's gone from every modal.
        for modal in (ReportMenu("x", [[]]), BackdropMenu("x", [("a", "A", None)]),
                      ChoiceDialog("x", [("a", "A", None)]), ConfirmDialog("x", "y")):
            self.assertFalse(hasattr(modal, "help_items"))

    def test_every_modal_exposes_buttons(self):
        self.assertTrue(ReportMenu("x", [[]]).buttons())
        self.assertTrue(BackdropMenu("x", [("a", "A", None)]).buttons())
        self.assertTrue(ChoiceDialog("x", [("a", "A", None)]).buttons())
        self.assertTrue(ConfirmDialog("x", "y").buttons())


class TestChoiceDialog(unittest.TestCase):
    """ChoiceDialog (was LocationSelector + ExitMenu): mouse-only - every
    option plus an always-present Cancel are buttons; a disabled option
    can't be committed; the keyboard does nothing."""

    def _key(self, key):
        return SimpleNamespace(type=pygame_mock.KEYDOWN, key=key)

    def test_options_plus_cancel_are_all_buttons(self):
        dialog = ChoiceDialog("Where To?", [("bar", "Bar", None), ("dorm", "Dormitory", None)])
        self.assertEqual([b[0] for b in dialog.buttons()], ["bar", "dorm", "cancel"])

    def test_disabled_option_is_marked_disabled(self):
        dialog = ChoiceDialog("Where To?", [("ship", "Return to Ship", "no ship owned"), ("bar", "Bar", None)])
        by_id = {b[0]: b for b in dialog.buttons()}
        self.assertTrue(by_id["ship"][3])   # disabled
        self.assertFalse(by_id["bar"][3])
        self.assertFalse(by_id["cancel"][3])

    def test_only_enter_does_anything_on_the_keyboard(self):
        dialog = ChoiceDialog("Where To?", [("bar", "Bar", None), ("dorm", "Dorm", None)])
        for key in (pygame_mock.K_ESCAPE, pygame_mock.K_DOWN, pygame_mock.K_UP, pygame_mock.K_TAB):
            self.assertIsNone(dialog.handle_input([self._key(key)]))
        # Enter presses the highlighted button (starts on the first enabled option)
        self.assertEqual(dialog.handle_input([self._key(pygame_mock.K_RETURN)]), "bar")


class TestBackdropMenu(unittest.TestCase):
    """BackdropMenu (was Menu + StorySelector): mouse-only - each row is a
    button, and a Back button is appended when `allow_cancel`."""

    def _key(self, key):
        return SimpleNamespace(type=pygame_mock.KEYDOWN, key=key)

    def test_rows_are_buttons_and_back_appears_only_when_allowed(self):
        plain = BackdropMenu("MAIN", [("new", "NEW", None), ("quit", "QUIT", None)])
        self.assertEqual([b[0] for b in plain.buttons()], ["new", "quit"])
        cancelable = BackdropMenu("STORY", [("a", "A", None)], allow_cancel=True)
        self.assertEqual([b[0] for b in cancelable.buttons()], ["a", "cancel"])
        self.assertEqual(cancelable.buttons()[-1][1], "Back")

    def test_only_enter_does_anything_on_the_keyboard(self):
        menu = BackdropMenu("MAIN", [("new", "NEW", None), ("quit", "QUIT", None)], allow_cancel=True)
        for key in (pygame_mock.K_ESCAPE, pygame_mock.K_DOWN, pygame_mock.K_UP):
            self.assertIsNone(menu.handle_input([self._key(key)]))
        self.assertEqual(menu.handle_input([self._key(pygame_mock.K_RETURN)]), "new")  # highlighted row


class TestShopMenu(unittest.TestCase):
    """Test ShopMenu's buy/sell logic against the real "default" story's
    commodities.json/items.json (ore costs 12cr, repair_kit costs 150cr) -
    same convention as other config-dependent tests that pin to real story
    data rather than reimplementing get_commodity()/get_item() with a fake.
    Only the transaction/navigation logic is tested here, not draw() - see
    docs/WORKFLOW.md's "don't test UI rendering" and the fact that no other full
    menu class (ReportMenu, ConfirmDialog, ChoiceDialog) has a draw() test
    either."""

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

    def test_clicking_a_tab_label_toggles_buy_sell_mode(self):
        shop = ShopMenu(Possessions(), "default", {"type": "commodities", "stock": ["ore"]})
        self.assertEqual(shop.mode, "buy")
        shop._sell_tab_rect = SimpleNamespace(collidepoint=lambda p: True)
        shop._buy_tab_rect = SimpleNamespace(collidepoint=lambda p: False)
        shop._handle_click((0, 0))
        self.assertEqual(shop.mode, "sell")

    def test_wheel_scrolls_the_grid_without_changing_mode(self):
        shop = ShopMenu(Possessions(), "default", {"type": "commodities", "stock": ["ore", "medicine", "fuel_cells", "water", "ice"]})
        import pygame as mocked_pygame
        shop.handle_input([self._event(mocked_pygame.MOUSEWHEEL, y=-1)])
        self.assertEqual(shop.mode, "buy")
        self.assertNotEqual(shop.buy_list.selected, 0)

    def test_escape_and_tab_do_nothing_enter_trades_the_selection(self):
        import pygame as mocked_pygame
        possessions = Possessions(credits=100)
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        for key in (mocked_pygame.K_ESCAPE, mocked_pygame.K_TAB):
            self.assertIsNone(shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=key)]))
        self.assertEqual(possessions.cargo, {})
        # Enter trades the highlighted grid item, not the button bar.
        shop.handle_input([self._event(mocked_pygame.KEYDOWN, key=mocked_pygame.K_RETURN)])
        self.assertEqual(possessions.cargo, {"ore": 1})

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

    def test_buy_button_press_transacts_the_selected_item(self):
        possessions = Possessions(credits=100)
        shop = ShopMenu(possessions, "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        shop._transact(shop._current_list().current())  # what pressing Buy / double-clicking does
        self.assertEqual(possessions.cargo, {"ore": 1})

    def test_panel_exposes_a_buy_button_that_reflects_affordability(self):
        rich = ShopMenu(Possessions(credits=100), "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        ids = [b[0] for b in rich.buttons()]
        self.assertIn("buy", ids)
        self.assertFalse(dict((b[0], b[3]) for b in rich.buttons())["buy"])  # affordable -> enabled
        broke = ShopMenu(Possessions(credits=0), "default", {"type": "commodities", "stock": ["ore"]}, cargo_capacity=10)
        self.assertTrue(dict((b[0], b[3]) for b in broke.buttons())["buy"])  # can't afford -> disabled

    def test_panel_buy_button_becomes_a_sell_button_on_the_sell_tab(self):
        shop = ShopMenu(Possessions(cargo={"ore": 1}), "default", {"type": "commodities", "stock": ["ore"]})
        shop.mode = "sell"
        self.assertIn("sell", [b[0] for b in shop.buttons()])
        self.assertEqual([b[1] for b in shop.buttons() if b[0] == "sell"], ["Sell"])


class TestShipBrowserMenu(unittest.TestCase):
    """Test ShipBrowserMenu against the real "default" story's ship_types.json
    (shuttle costs 1200cr) - the on_buy callback is the injection point that
    lets this menu perform the same mutation as LocationScreen.buy_ship()
    without owning Possessions/on_ship_purchased itself."""

    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_open_confirm_shows_a_dialog_instead_of_buying_immediately(self):
        bought = []
        possessions = Possessions(credits=1200)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle"]}, on_buy=bought.append)
        menu._activate(menu.grid.selected)  # what the Buy button / double-click does
        self.assertIsNotNone(menu.confirm)
        self.assertEqual(bought, [])  # not yet - still waiting on confirmation
        self.assertEqual(possessions.credits, 1200)

    def test_confirming_calls_on_buy_with_the_selected_ship_type(self):
        bought = []
        menu = ShipBrowserMenu(Possessions(credits=1200), "default", {"stock": ["shuttle"]}, on_buy=bought.append)
        menu._activate(menu.grid.selected)
        self.assertEqual(menu.confirm.context_data, "shuttle")
        # the confirm dialog resolves "Yes"
        menu.confirm = SimpleNamespace(handle_input=lambda evs: ("confirm", "shuttle"))
        menu.handle_input([self._event(pygame_mock.MOUSEBUTTONDOWN, button=1, pos=(0, 0))])
        self.assertEqual(bought, ["shuttle"])
        self.assertIsNone(menu.confirm)

    def test_cannot_afford_blocks_the_confirm_from_opening(self):
        bought = []
        possessions = Possessions(credits=0)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle"]}, on_buy=bought.append)
        menu._activate(menu.grid.selected)
        self.assertIsNone(menu.confirm)
        self.assertEqual(bought, [])

    def test_your_ships_tab_switches_the_active_hull(self):
        switched = []
        possessions = Possessions(owned_ships=["shuttle", "freighter"])  # active = index 1
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle", "freighter"]},
                               on_buy=lambda x: None, on_switch=switched.append)
        menu._set_mode("owned")
        self.assertEqual([b[0] for b in menu.buttons()], ["close", "action", "toggle"])
        menu.grid.selected = 0  # the shuttle
        menu._activate(0)
        self.assertEqual(switched, [0])

    def test_your_ships_tab_hidden_without_an_on_switch_callback(self):
        menu = ShipBrowserMenu(Possessions(owned_ships=["shuttle"]), "default",
                               {"stock": ["shuttle"]}, on_buy=lambda x: None)
        self.assertNotIn("toggle", [b[0] for b in menu.buttons()])

    def test_keyboard_does_nothing(self):
        import pygame as mocked_pygame
        menu = ShipBrowserMenu(Possessions(), "default", {"stock": ["shuttle"]}, on_buy=lambda x: None)
        for key in (mocked_pygame.K_ESCAPE, mocked_pygame.K_RETURN, mocked_pygame.K_DOWN):
            self.assertIsNone(menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=key)]))
        self.assertIsNone(menu.confirm)

    def test_wheel_scrolls_without_skipping_unaffordable_ships(self):
        """shuttle costs 1200cr, freighter costs 4500cr - affording the
        shuttle only must not block scrolling onto/previewing the freighter."""
        import pygame as mocked_pygame
        possessions = Possessions(credits=1200)
        menu = ShipBrowserMenu(possessions, "default", {"stock": ["shuttle", "freighter"]}, on_buy=lambda x: None)
        self.assertEqual(menu.grid.current(), "shuttle")
        menu.handle_input([self._event(mocked_pygame.MOUSEWHEEL, y=-1)])
        self.assertEqual(menu.grid.current(), "freighter")

    def test_panel_exposes_a_buy_button_gated_on_affordability(self):
        rich = ShipBrowserMenu(Possessions(credits=5000), "default", {"stock": ["shuttle"]}, on_buy=lambda x: None)
        self.assertEqual(dict((b[0], b[3]) for b in rich.buttons()).get("action"), False)
        broke = ShipBrowserMenu(Possessions(credits=0), "default", {"stock": ["shuttle"]}, on_buy=lambda x: None)
        self.assertTrue(dict((b[0], b[3]) for b in broke.buttons())["action"])


class TestFitText(unittest.TestCase):
    """ui_theme.fit_text - trims a label with a trailing ellipsis until it
    renders within a width, so a long story-authored ship/outfit name can
    never spill into the neighbouring grid cell (see draw_shop_cell)."""

    def test_short_text_is_returned_unchanged(self):
        self.assertEqual(fit_text(_FakeFont(), "Courier", 100), "Courier")

    def test_long_text_is_ellipsised_to_fit(self):
        out = fit_text(_FakeFont(), "Authority Courier XL", 12)  # _FakeFont: 1px/char
        self.assertTrue(out.endswith("…"))
        self.assertLessEqual(_FakeFont().size(out)[0], 12)

    def test_non_positive_width_is_a_noop(self):
        self.assertEqual(fit_text(_FakeFont(), "anything", 0), "anything")


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
    drop itself isn't tested here - see docs/WORKFLOW.md's "don't test UI
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

    def _click_slot(self, menu, slot_id):
        menu._slot_rects = {slot_id: SimpleNamespace(collidepoint=lambda pos: True)}
        menu._handle_mouse_down((5, 5))

    def test_clicking_an_empty_slot_opens_picker_filtered_to_compatible_outfits(self):
        possessions = Possessions(owned_outfits=["laser_cannon", "afterburner"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        menu.tab = "install"
        weapon_slot = next(s["id"] for s in menu.slots if s["type"] == "weapon")
        menu.slot_focus = next(i for i, s in enumerate(menu.slots) if s["id"] == weapon_slot)
        self._click_slot(menu, weapon_slot)
        self.assertIsNotNone(menu.picker)
        self.assertEqual(menu.picker.items, ["laser_cannon"])

    def test_picker_click_installs_and_calls_outfits_changed_callback(self):
        changed = []
        possessions = Possessions(owned_outfits=["laser_cannon"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol", on_outfits_changed=lambda: changed.append(True))
        weapon_slot = next(s["id"] for s in menu.slots if s["type"] == "weapon")
        menu.slot_focus = next(i for i, s in enumerate(menu.slots) if s["id"] == weapon_slot)
        menu.tab = "install"
        self._click_slot(menu, weapon_slot)
        menu.picker._row_rects = [(0, SimpleNamespace(collidepoint=lambda pos: True))]
        menu._handle_mouse_down((5, 5))
        self.assertEqual(possessions.installed_outfits, {weapon_slot: "laser_cannon"})
        self.assertEqual(possessions.owned_outfits, [])
        self.assertEqual(changed, [True])

    def test_uninstall_returns_the_outfit_and_calls_callback(self):
        changed = []
        possessions = Possessions(installed_outfits={"weapon_1": "laser_cannon"})
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol", on_outfits_changed=lambda: changed.append(True))
        menu._uninstall("weapon_1")  # what dragging a slot out / double-clicking it does
        self.assertEqual(possessions.installed_outfits, {})
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])
        self.assertEqual(changed, [True])

    def test_clicking_an_empty_slot_with_no_compatible_outfits_does_not_open_picker(self):
        possessions = Possessions(owned_outfits=["afterburner"])  # engine, not weapon
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        menu.tab = "install"
        weapon_slot = next(s["id"] for s in menu.slots if s["type"] == "weapon")
        self._click_slot(menu, weapon_slot)
        self.assertIsNone(menu.picker)

    def test_buying_an_outfit_spends_credits_and_adds_to_owned(self):
        possessions = Possessions(credits=1000)
        menu = OutfittingMenu(possessions, "default", {"stock": ["laser_cannon"]}, None)
        menu._buy_outfit("laser_cannon")
        self.assertEqual(possessions.credits, 200)  # 1000 - 800cr
        self.assertEqual(possessions.owned_outfits, ["laser_cannon"])

    def test_wheel_scrolls_the_buy_grid_without_skipping_unaffordable_outfits(self):
        import pygame as mocked_pygame
        possessions = Possessions(credits=800)
        menu = OutfittingMenu(possessions, "default", {"stock": ["laser_cannon", "afterburner", "ion_thruster", "cargo_expansion"]}, None)
        self.assertEqual(menu.buy_grid.current(), "laser_cannon")
        menu.handle_input([self._event(mocked_pygame.MOUSEWHEEL, y=-1)])
        self.assertNotEqual(menu.buy_grid.current(), "laser_cannon")

    def test_icon_for_defaults_to_slot_type_when_outfit_has_no_icon_shape(self):
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, None)
        # afterburner (engine slot) carries no icon_shape/icon_color of its
        # own in ship_outfits.json, so this exercises the SLOT_ICON_SHAPES/
        # SLOT_COLORS fallback - see test_icon_for_uses_the_outfits_own_
        # config_when_set below for the explicit-config path (laser_cannon).
        icon_shape, icon_color = menu._icon_for("afterburner")
        self.assertEqual(icon_shape, "flame")
        self.assertEqual(icon_color, SLOT_COLORS["engine"])

    def test_icon_for_uses_the_outfits_own_config_when_set(self):
        # laser_cannon sets an explicit icon_shape/icon_color in
        # ship_outfits.json (so a fired projectile's glyph - see
        # game/world/projectile.py - visibly matches its Outfitter icon)
        # rather than falling back to the generic per-slot-type default.
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, None)
        icon_shape, icon_color = menu._icon_for("laser_cannon")
        self.assertEqual(icon_shape, "blade")
        self.assertEqual(icon_color, [100, 200, 255])

    def test_clicking_the_owned_grid_moves_focus_there(self):
        menu = OutfittingMenu(Possessions(owned_outfits=["laser_cannon"]), "default", {"stock": []}, "patrol")
        menu.tab = "install"
        menu._slot_rects = {}
        menu.owned_grid.last_rects = {0: SimpleNamespace(collidepoint=lambda pos: True)}
        menu._handle_mouse_down((5, 5))
        self.assertEqual(menu.focus_column, "owned")

    def test_clicking_a_tab_label_switches_buy_install(self):
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, "patrol")
        self.assertEqual(menu.tab, "install")
        menu._buy_tab_rect = SimpleNamespace(collidepoint=lambda pos: True)
        menu._install_tab_rect = SimpleNamespace(collidepoint=lambda pos: False)
        menu._handle_mouse_down((5, 5))
        self.assertEqual(menu.tab, "buy")

    def test_no_ship_defaults_to_buy_tab(self):
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, None)
        self.assertEqual(menu.tab, "buy")
        self.assertEqual(menu.slots, [])

    def test_keyboard_does_nothing_and_close_is_a_button(self):
        import pygame as mocked_pygame
        menu = OutfittingMenu(Possessions(), "default", {"stock": []}, "patrol")
        for key in (mocked_pygame.K_ESCAPE, mocked_pygame.K_RETURN, mocked_pygame.K_TAB):
            self.assertIsNone(menu.handle_input([self._event(mocked_pygame.KEYDOWN, key=key)]))
        self.assertIn("close", [b[0] for b in menu.buttons()])

    def test_buy_tab_has_a_buy_button_the_install_tab_does_not(self):
        menu = OutfittingMenu(Possessions(credits=1000), "default", {"stock": ["laser_cannon"]}, "patrol")
        menu.tab = "buy"
        self.assertIn("buy", [b[0] for b in menu.buttons()])
        menu.tab = "install"
        self.assertNotIn("buy", [b[0] for b in menu.buttons()])

    def test_clicking_an_empty_slot_opens_the_picker(self):
        possessions = Possessions(owned_outfits=["laser_cannon"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        menu.tab = "install"
        weapon_slot = next(s["id"] for s in menu.slots if s["type"] == "weapon")
        menu._slot_rects = {weapon_slot: SimpleNamespace(collidepoint=lambda pos: True)}
        menu._handle_mouse_down((5, 5))
        self.assertIsNotNone(menu.picker)
        self.assertEqual(menu.picker.items, ["laser_cannon"])

    def test_clicking_a_picker_row_installs_that_outfit(self):
        possessions = Possessions(owned_outfits=["laser_cannon"])
        menu = OutfittingMenu(possessions, "default", {"stock": []}, "patrol")
        menu.tab = "install"
        menu.slot_focus = next(i for i, s in enumerate(menu.slots) if s["type"] == "weapon")
        menu.picker = SelectableList(["laser_cannon"], max_visible=6)
        menu.picker._row_rects = [(0, SimpleNamespace(collidepoint=lambda pos: True))]
        menu._handle_mouse_down((5, 5))
        self.assertIsNone(menu.picker)
        self.assertEqual(possessions.installed_outfits, {menu.slots[menu.slot_focus]["id"]: "laser_cannon"})


class TestPilotNameDialog(unittest.TestCase):
    def _event(self, type_, **kwargs):
        return SimpleNamespace(type=type_, **kwargs)

    def test_name_is_prefilled_so_start_is_enabled_for_a_mouse_only_player(self):
        from game.ui.pilot_name_dialog import PilotNameDialog
        dialog = PilotNameDialog()
        self.assertTrue(dialog.pilot_name)
        self.assertFalse(dict((b[0], b[3]) for b in dialog.buttons())["start"])  # not disabled

    def test_first_keystroke_replaces_the_default_then_appends(self):
        import pygame as mocked_pygame
        from game.ui.pilot_name_dialog import PilotNameDialog
        dialog = PilotNameDialog()
        dialog.handle_input([self._event(mocked_pygame.TEXTINPUT, text="A")])
        self.assertEqual(dialog.pilot_name, "A")
        dialog.handle_input([self._event(mocked_pygame.TEXTINPUT, text="b")])
        self.assertEqual(dialog.pilot_name, "Ab")


class TestWrapText(unittest.TestCase):
    """Test utils._wrap_text() - shared by BackdropMenu and Dialogue (see
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


class TestHudZoneWidths(unittest.TestCase):
    """side_panel_max_width()/center_panel_max_width() (see
    docs/DESIGN_PATTERNS.md's "HUD Zone Width Discipline") - the two
    numbers every side/center HUD panel (draw_status_pane, draw_info_panel,
    draw_message_log, draw_controls_pane, draw_glow_message, the minimap)
    caps itself to, derived from the real window width rather than
    ui_scale so they can't drift out of sync with the window's actual
    shape (a wide-but-short window scales ui_scale from height alone -
    see their own docstrings)."""

    def setUp(self):
        self._original_size = (utils.screen_width, utils.screen_height)

    def tearDown(self):
        utils.set_screen_size(*self._original_size)

    def test_side_is_one_fifth_of_screen_width(self):
        utils.set_screen_size(1859, 1024)  # the reported bug's window size
        self.assertEqual(side_panel_max_width(), 1859 // 5)

    def test_center_zone_stays_clear_of_the_side_zones(self):
        utils.set_screen_size(1859, 1024)
        ui_scale = utils.get_ui_scale()
        self.assertLess(center_panel_max_width(ui_scale), 1859 / 2)
        self.assertEqual(center_panel_max_width(ui_scale), 1859 // 2 - 2 * hud_margin(ui_scale))
        # A centred pane this wide never reaches the line where a side pane begins.
        centre_right_edge = 1859 / 2 + center_panel_max_width(ui_scale) / 2
        side_line = 1859 - side_panel_max_width()  # right side pane's inner edge
        self.assertLess(centre_right_edge, side_line)

    def test_zones_track_window_width_directly_not_ui_scale(self):
        """The whole point: on a wide-but-short window, ui_scale is capped
        by height (get_ui_scale() = min(w/800, h/600)), not width - the
        zone widths must still track the real (wide) screen_width, not
        that scale factor, or a panel sized from ui_scale alone could
        still overflow its zone."""
        utils.set_screen_size(1859, 1024)
        ui_scale = utils.get_ui_scale()
        self.assertLess(ui_scale, 1859 / 800, "fixture must reproduce the height-capped case")
        self.assertEqual(side_panel_max_width(), 1859 // 5)

    def test_side_panel_width_fills_the_zone_from_margin_to_the_line(self):
        """An edge-anchored pane at hud_margin() from the edge, this wide,
        has its inner edge exactly on the side-zone line."""
        utils.set_screen_size(1859, 1024)
        ui_scale = utils.get_ui_scale()
        self.assertEqual(hud_margin(ui_scale) + side_panel_width(ui_scale), side_panel_max_width())

    def test_side_panel_width_stays_positive_on_a_tiny_window(self):
        utils.set_screen_size(200, 200)
        self.assertGreaterEqual(side_panel_width(utils.get_ui_scale()), 1)


class TestSelectableListDisabledNavigation(unittest.TestCase):
    """Test SelectableList.handle_key()'s disabled_fn skip - the same
    "can't navigate onto a disabled entry" fix (used by ExitMenu, now the
    ChoiceDialog exit picker, and the outfitting picker)."""

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
    """Regression test: the save browser crashed (IndexError in current())
    when deleting the last-selected save shrank the list out from under a
    SelectableList whose `selected` index wasn't updated to match - e.g.
    deleting save 3 of 3 left `selected == 2` pointing past the new 2-item
    list. SaveBrowser's existing_saves setter reassigns `.list.items`
    directly (see game/ui/save_browser.py), so the fix has to live in
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


class TestSettingsMenu(unittest.TestCase):
    """main.py's Settings menu: the Video tab's rows and the anti-aliasing
    row label tracking constants.AA_MODE."""

    def setUp(self):
        import game.constants as constants
        self._prev_aa = constants.AA_MODE
        self.addCleanup(setattr, constants, "AA_MODE", self._prev_aa)

    def test_video_tab_has_aa_row_first_then_aspect_and_resolutions(self):
        import main
        menu = main.settings_menu("16:9")
        self.assertEqual(menu.tabs, ("Video", main.SETTINGS_TABS))
        values = [v for v, _l, _d in menu.rows]
        self.assertEqual(values[0], "aa_cycle")
        self.assertIn("aspect", values)

    def test_aa_row_label_follows_the_mode(self):
        import main
        import game.constants as constants

        constants.AA_MODE = "off"
        off = main.settings_menu("16:9").rows[0][1]
        constants.AA_MODE = "gfxdraw"
        gfx = main.settings_menu("16:9").rows[0][1]
        constants.AA_MODE = "supersample"
        ss = main.settings_menu("16:9").rows[0][1]
        self.assertIn("Off", off)
        self.assertIn("gfxdraw", gfx)
        self.assertIn("x2", ss.lower())

    def test_every_aa_mode_has_a_label(self):
        import game.constants as constants
        for mode in constants.AA_MODES:
            self.assertIn(mode, constants.AA_MODE_LABELS)


if __name__ == "__main__":
    unittest.main()
