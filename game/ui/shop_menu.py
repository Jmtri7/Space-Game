"""Buy/sell menu for commodities and personal items - a generic shop screen
opened by talking to an NPC whose config has a "shop" key (see
LocationScreen._build_local_character). Ships and ship outfits get their own
purpose-built menus (ShipBrowserMenu, OutfittingMenu) since they need more
than a flat price list - this one covers the two simple, stackable
categories."""
import pygame
from game.constants import YELLOW, GRAY, GREEN
from game.utils import get_ui_scale, get_ui_offset, get_font, get_commodity, get_item
from game.ui.ui_theme import draw_glass_panel, draw_glow_title
from game.ui.selectable_list import SelectableList

DEFAULT_SELL_MULTIPLIER = 0.6


class ShopMenu:
    """Buy tab lists the shop's configured stock, priced via
    get_commodity()/get_item(); Sell tab lists whatever the player currently
    holds in this shop's category, priced at base_price * sell_multiplier.
    One unit is bought/sold per Enter press - no bulk-quantity UI, matching
    how nothing else in this game batches a purchase either."""

    def __init__(self, possessions, story, shop_config, cargo_capacity=0):
        self.possessions = possessions
        self.story = story
        self.category = shop_config.get("type", "items")  # "commodities" or "items"
        self.stock = list(shop_config.get("stock", []))
        self.sell_multiplier = shop_config.get("sell_multiplier", DEFAULT_SELL_MULTIPLIER)
        self.cargo_capacity = cargo_capacity
        self.mode = "buy"  # "buy" or "sell"
        self.buy_list = SelectableList(self.stock, max_visible=6)
        self.sell_list = SelectableList(self._owned_ids(), max_visible=6)

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

    def _label(self, item_id):
        name = self._resolve(item_id).get("name", item_id)
        if self.mode == "buy":
            price = self._resolve(item_id).get("base_price", 0)
            return f"{name} - {price}cr"
        held = self.possessions.cargo if self.category == "commodities" else self.possessions.items
        qty = held.get(item_id, 0)
        sell_price = int(self._resolve(item_id).get("base_price", 0) * self.sell_multiplier)
        return f"{name} x{qty} - {sell_price}cr each"

    def handle_input(self, events):
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                return "close"
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self.mode = "sell" if self.mode == "buy" else "buy"
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                disabled_fn = self._buy_disabled_reason if self.mode == "buy" else None
                self._current_list().handle_key(event.key, disabled_fn=disabled_fn)
            elif event.key == pygame.K_RETURN:
                item_id = self._current_list().current()
                if item_id:
                    self._transact(item_id)
        return None

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
        else:
            sell_price = int(self._resolve(item_id).get("base_price", 0) * self.sell_multiplier)
            self.possessions.earn(sell_price)
            if self.category == "commodities":
                self.possessions.remove_cargo(item_id, 1)
            else:
                self.possessions.remove_item(item_id, 1)

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.12), int(offset_y + 600 * scale * 0.1), int(800 * scale * 0.76), int(600 * scale * 0.8))
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_info = get_font(int(20 * scale))
        font_text = get_font(int(22 * scale))

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
        y += int(40 * scale)

        self._current_list().draw(surface, font_text, panel_rect.centerx, y, int(32 * scale), scale,
                                   label_fn=self._label,
                                   disabled_fn=self._buy_disabled_reason if self.mode == "buy" else None)

        help_text = font_info.render("Left/Right: Buy/Sell, Enter: transact 1, ESC: close", True, (150, 150, 150))
        surface.blit(help_text, (panel_rect.x + int(20 * scale), panel_rect.bottom - int(30 * scale)))
