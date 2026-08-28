"""Buy/sell menu for commodities and personal items - a generic shop screen
opened by talking to an NPC whose config has a "shop" key (see
LocationScreen._build_local_character). Ships and ship outfits get their own
purpose-built menus (ShipBrowserMenu, OutfittingMenu) since they need more
than a flat price list - this one covers the two simple, stackable
categories."""
import functools
import pygame
from game.constants import YELLOW, GRAY
from game.utils import get_ui_scale, get_ui_offset, get_font, get_commodity, get_item
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_item_icon, draw_shop_cell, draw_purchase_message, modal_panel_rect, PURCHASE_MESSAGE_FRAMES
from game.ui.icon_grid import IconGrid
from game.ui.menu_base import MenuBase

DEFAULT_SELL_MULTIPLIER = 0.6
GRID_COLUMNS = 3
GRID_ROWS = 2


class ShopMenu(MenuBase):
    """Buy tab lists the shop's configured stock, priced via
    get_commodity()/get_item(); Sell tab lists whatever the player currently
    holds in this shop's category, priced at base_price * sell_multiplier.
    One unit is bought/sold per Enter press - no bulk-quantity UI, matching
    how nothing else in this game batches a purchase either. Both tabs are
    drawn as a grid of icons (name, price, and the vendor's/player's
    quantity) rather than a plain text list."""

    def __init__(self, possessions, story, shop_config, cargo_capacity=0):
        self.possessions = possessions
        self.story = story
        self.category = shop_config.get("type", "items")  # "commodities" or "items"
        self.stock = list(shop_config.get("stock", []))
        self.sell_multiplier = shop_config.get("sell_multiplier", DEFAULT_SELL_MULTIPLIER)
        self.cargo_capacity = cargo_capacity
        self.mode = "buy"  # "buy" or "sell"
        self.buy_list = IconGrid(self.stock, columns=GRID_COLUMNS, max_rows=GRID_ROWS)
        self.sell_list = IconGrid(self._owned_ids(), columns=GRID_COLUMNS, max_rows=GRID_ROWS)
        # Transient "Bought 1 X" confirmation (see draw_purchase_message) -
        # message_timer counts down once per draw() call while > 0, since
        # nothing calls a ShopMenu.update() each frame (see main.py's screen
        # loop - only handle_input()/draw() are called on the active shop).
        self.message = None
        self.message_timer = 0
        # Screen-space rects for the Buy/Sell tab labels, cached by draw()
        # each frame (same "cache during draw, hit-test next frame" idiom
        # OutfittingMenu's _slot_rects uses) so handle_input's mouse click
        # can tell whether a tab label was clicked.
        self._buy_tab_rect = None
        self._sell_tab_rect = None

    def _resolve(self, item_id):
        return get_commodity(self.story, item_id) if self.category == "commodities" else get_item(self.story, item_id)

    def _owned_ids(self):
        held = self.possessions.cargo if self.category == "commodities" else self.possessions.items
        return list(held.keys())

    def _current_list(self):
        if self.mode == "sell":
            self.sell_list.items = self._owned_ids()
        return self.buy_list if self.mode == "buy" else self.sell_list

    def _buy_disabled_reason(self, item_id):
        price = self._resolve(item_id).get("base_price", 0)
        if not self.possessions.can_afford(price):
            return "not enough credits"
        if self.category == "commodities" and self.possessions.cargo_quantity_total() + 1 > self.cargo_capacity:
            return "cargo full"
        return None

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                # Enter trades the selected grid item (a selection is always
                # highlighted) - the button-bar Enter would otherwise just
                # press Close.
                item_id = self._current_list().current()
                if item_id and not (self.mode == "buy" and self._buy_disabled_reason(item_id)):
                    self._transact(item_id)
                continue
            pressed = self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale()))
            if pressed == "close":
                return "close"
            if pressed in ("buy", "sell"):
                item_id = self._current_list().current()
                if item_id:
                    self._transact(item_id)
                continue
            if event.type == pygame.MOUSEWHEEL:
                self._current_list().scroll(-event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                double = self._is_double_click(event.pos)
                grid = self._current_list()
                on_item = grid.index_at(event.pos) is not None
                self._handle_click(event.pos)
                # Double-click an item = transact it; a single click still
                # just selects, so a stray click can't buy.
                if double and on_item and grid.current():
                    self._transact(grid.current())
        return None

    def _handle_click(self, pos):
        """A click on a tab label switches tab; a click on a grid cell
        selects it (a double-click transacts it - see handle_input)."""
        if self._buy_tab_rect and self._buy_tab_rect.collidepoint(pos):
            self.mode = "buy"
            return
        if self._sell_tab_rect and self._sell_tab_rect.collidepoint(pos):
            self.mode = "sell"
            return
        grid = self._current_list()
        index = grid.index_at(pos)
        if index is not None:
            grid.selected = index

    def _transact(self, item_id):
        if self.mode == "buy":
            if self._buy_disabled_reason(item_id):
                return
            price = self._resolve(item_id).get("base_price", 0)
            self.possessions.spend(price)
            if self.category == "commodities":
                self.possessions.add_cargo(item_id, 1)
            else:
                self.possessions.add_item(item_id, 1)
            self.message = f"Bought 1 {self._resolve(item_id).get('name', item_id)}"
            self.message_timer = PURCHASE_MESSAGE_FRAMES
        else:
            sell_price = int(self._resolve(item_id).get("base_price", 0) * self.sell_multiplier)
            self.possessions.earn(sell_price)
            if self.category == "commodities":
                self.possessions.remove_cargo(item_id, 1)
            else:
                self.possessions.remove_item(item_id, 1)

    def buttons(self):
        item_id = self._current_list().current()
        if self.mode == "buy":
            disabled = not item_id or bool(self._buy_disabled_reason(item_id))
            action = ("buy", "Buy", (150, 220, 160), disabled)
        else:
            disabled = not item_id
            action = ("sell", "Sell", (235, 205, 150), disabled)
        return [("close", "Close", (235, 235, 240), False), action]

    def panel_rect(self, scale):
        return modal_panel_rect(scale, 0.1, 0.76, 0.8)

    def button_bar_rects(self, scale):
        panel = self.panel_rect(scale)
        w, h, m = int(120 * scale), int(38 * scale), int(16 * scale)
        close_rect = pygame.Rect(panel.x + m, panel.y + m, w, h)
        aw = int(150 * scale)
        action_rect = pygame.Rect(panel.centerx - aw // 2, panel.bottom - int(58 * scale), aw, int(42 * scale))
        return [close_rect, action_rect]

    def draw_content(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = self.panel_rect(scale)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_info = get_font(int(20 * scale))

        title = "Commodities" if self.category == "commodities" else "General Store"
        y = panel_rect.y + int(20 * scale)
        y += draw_glow_title(surface, title, font_title, panel_rect.centerx, y)
        y += int(10 * scale)

        info_bits = [f"Credits: {self.possessions.credits}"]
        if self.category == "commodities":
            info_bits.append(f"Cargo: {self.possessions.cargo_quantity_total()}/{self.cargo_capacity}")
        info_text = font_info.render("   ".join(info_bits), True, (255, 220, 100))
        surface.blit(info_text, (panel_rect.centerx - info_text.get_width() // 2, y))
        y += int(30 * scale)

        buy_color = YELLOW if self.mode == "buy" else GRAY
        sell_color = YELLOW if self.mode == "sell" else GRAY
        tabs_text = font_info.render("Buy", True, buy_color)
        tabs_text2 = font_info.render(" / Sell", True, sell_color)
        tabs_x = panel_rect.centerx - (tabs_text.get_width() + tabs_text2.get_width()) // 2
        surface.blit(tabs_text, (tabs_x, y))
        surface.blit(tabs_text2, (tabs_x + tabs_text.get_width(), y))
        self._buy_tab_rect = pygame.Rect(tabs_x, y, tabs_text.get_width(), tabs_text.get_height())
        self._sell_tab_rect = pygame.Rect(tabs_x + tabs_text.get_width(), y, tabs_text2.get_width(), tabs_text2.get_height())
        y += int(36 * scale)

        grid = self._current_list()
        if grid.has_more_above:
            up_indicator = font_info.render("^ more", True, GRAY)
            surface.blit(up_indicator, (panel_rect.centerx - up_indicator.get_width() // 2, y))
        y += int(18 * scale)

        gap = int(14 * scale)
        cell_width = (panel_rect.width - int(60 * scale) - gap * (GRID_COLUMNS - 1)) // GRID_COLUMNS
        cell_height = int(130 * scale)
        grid_left = panel_rect.centerx - (cell_width * GRID_COLUMNS + gap * (GRID_COLUMNS - 1)) // 2

        draw_cell = functools.partial(self._draw_cell, scale=scale)
        grid.draw(surface, (grid_left, y), cell_width, cell_height, gap, draw_cell,
                  disabled_fn=self._buy_disabled_reason if self.mode == "buy" else None)

        grid_bottom = y + cell_height * GRID_ROWS + gap * (GRID_ROWS - 1)
        if grid.has_more_below:
            down_indicator = font_info.render("v more", True, GRAY)
            surface.blit(down_indicator, (panel_rect.centerx - down_indicator.get_width() // 2, grid_bottom + int(4 * scale)))

        if self.message_timer > 0:
            self.message_timer -= 1
            draw_purchase_message(surface, self.message, self.message_timer, panel_rect.centerx, panel_rect.bottom - int(100 * scale), scale)

    def _draw_cell(self, surface, rect, item_id, is_selected, reason, scale):
        """cell_draw_fn for the buy/sell IconGrid - an icon, the item's
        name, and a price/quantity line. The price always stays visible
        even when `reason` is set (e.g. "not enough credits") - it used to
        be replaced by the reason entirely, so a commodity you couldn't
        afford didn't show its price at all."""
        item = self._resolve(item_id)
        icon_fn = functools.partial(draw_item_icon, icon_shape=item.get("icon_shape"), icon_color=item.get("icon_color"))

        if self.mode == "buy":
            detail = f"{item.get('base_price', 0)}cr"
        else:
            held = self.possessions.cargo if self.category == "commodities" else self.possessions.items
            qty = held.get(item_id, 0)
            sell_price = int(item.get("base_price", 0) * self.sell_multiplier)
            detail = f"x{qty} - {sell_price}cr"

        draw_shop_cell(surface, rect, is_selected, reason, icon_fn, item.get("name", item_id), detail, scale)
