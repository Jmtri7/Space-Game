"""Ship-buying menu with a live preview - opened by talking to an NPC whose
"shop" config has type "ships" (see LocationScreen._build_local_character),
replacing the old dialogue-tree "buy_ship:<id>" trick for any NPC that opts
into this instead."""
import functools
import pygame
from game.constants import YELLOW, GRAY
from game.utils import get_ui_scale, get_ui_offset, get_font, get_ship_type, get_graphics_asset
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_ship_glyph, draw_shop_cell, draw_purchase_message, modal_panel_rect, PURCHASE_MESSAGE_FRAMES
from game.ui.icon_grid import IconGrid
from game.ui.confirm_dialog import ConfirmDialog
from game.ui.menu_base import MenuBase

GRID_COLUMNS = 2
GRID_ROWS = 3

# Thresholds (world "size" units, from graphics.json) for the preview's
# "Approximate Size" stat - a plain number in world units means little to a
# player, so it's bucketed into a coarse, human label instead.
SIZE_LABELS = [(15, "Small"), (25, "Medium"), (40, "Large")]
DEFAULT_SIZE_LABEL = "Massive"


def _approximate_size_label(graphics):
    size = graphics.get("size", 15)
    for threshold, label in SIZE_LABELS:
        if size < threshold:
            return label
    return DEFAULT_SIZE_LABEL


class ShipBrowserMenu(MenuBase):
    """Left: an icon grid of the shop's stock ship types, each cell a
    static (unrotated, no thrust) silhouette with name and cost. Right: a
    live preview - the same glyph, but slowly spinning with its thrusters
    cycling on/off - plus a stat readout, for whichever grid cell is
    selected. Enter opens a ConfirmDialog; confirming calls the injected
    on_buy callback (LocationScreen._buy_ship - see there for why
    LocationScreen owns the actual purchase mutation rather than this
    menu)."""

    def __init__(self, possessions, story, shop_config, on_buy, on_switch=None):
        self.possessions = possessions
        self.story = story
        self.stock = list(shop_config.get("stock", []))
        self.on_buy = on_buy
        # Switch which owned hull is flown (see LocationScreen.switch_ship).
        # None -> the "Your Ships" tab is hidden (e.g. a test builds the
        # menu without it).
        self.on_switch = on_switch
        # "buy" = the shop's stock; "owned" = the player's own hulls, with a
        # "Fly this" button instead of "Buy".
        self.mode = "buy"
        self.grid = IconGrid(self.stock, columns=GRID_COLUMNS, max_rows=GRID_ROWS)
        self.confirm = None  # ConfirmDialog while a purchase is pending confirmation
        # Transient "Bought 1 X" confirmation (see draw_purchase_message) -
        # message_timer counts down once per draw() call while > 0, since
        # nothing calls a ShipBrowserMenu.update() each frame.
        self.message = None
        self.message_timer = 0

    def _owned_mode(self):
        return self.mode == "owned"

    def _current_list(self):
        """Grid items: stock ship-type ids in "buy" mode; owned-ship *slot
        indices* in "owned" mode (so two of the same hull are still two
        distinct, individually-selectable cells)."""
        if self._owned_mode():
            return list(range(len(self.possessions.owned_ships)))
        return self.stock

    def _id_of(self, item):
        """ship_type_id for a grid item (an id already, or an owned-ships index)."""
        if isinstance(item, int):
            return self.possessions.owned_ships[item]
        return item

    def _active_index(self):
        """Which owned-ships slot is being flown - the stored index, or the
        last ship when it's unset (matches Possessions.active_ship())."""
        i = self.possessions.active_ship_index
        n = len(self.possessions.owned_ships)
        return i if (i is not None and 0 <= i < n) else (n - 1 if n else -1)

    def _set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        self.grid = IconGrid(self._current_list(), columns=GRID_COLUMNS, max_rows=GRID_ROWS)
        if self._owned_mode() and self._active_index() >= 0:
            self.grid.selected = self._active_index()
        self.confirm = None

    def _disabled_reason(self, item):
        if self._owned_mode():
            return None
        cost = get_ship_type(self.story, item).get("cost", 0)
        if not self.possessions.can_afford(cost):
            return "not enough credits"
        return None

    def _owned_count(self, ship_type_id):
        return self.possessions.owned_ships.count(ship_type_id)

    def _format_slots(self, slots):
        """Format slot list as a readable summary like 'W1 E1 U2'."""
        if not slots:
            return "None"
        counts = {}
        for slot in slots:
            slot_type = slot.get("type", "utility")
            counts[slot_type] = counts.get(slot_type, 0) + 1
        # Order: weapon, engine, utility
        order = ["weapon", "engine", "utility"]
        parts = []
        for slot_type in order:
            if slot_type in counts:
                abbrev = slot_type[0].upper()
                parts.append(f"{abbrev}{counts[slot_type]}")
        return " ".join(parts) if parts else "None"

    def handle_input(self, events):
        if self.confirm:
            action, ship_type_id = self.confirm.handle_input(events)
            if action == "confirm":
                self.on_buy(ship_type_id)
                self.message = f"Bought 1 {get_ship_type(self.story, ship_type_id).get('name', ship_type_id)}"
                self.message_timer = PURCHASE_MESSAGE_FRAMES
                self.confirm = None
            elif action == "cancel":
                self.confirm = None
            return None

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self._activate(self.grid.selected)  # Enter = the selected ship
                continue
            pressed = self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale()))
            if pressed == "close":
                return "close"
            if pressed == "toggle":
                self._set_mode("buy" if self._owned_mode() else "owned")
                continue
            if pressed == "action":
                self._activate(self.grid.selected)
                continue
            if event.type == pygame.MOUSEWHEEL:
                self.grid.scroll(-event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # A single click only selects (and updates the live
                # preview); a double-click acts on it (buy / fly), the
                # same as the action button - so a stray click can't
                # buy a ship or swap the one you're flying.
                double = self._is_double_click(event.pos)
                index = self.grid.index_at(event.pos)
                if index is not None:
                    self.grid.selected = index
                    if double:
                        self._activate(index)
        return None

    def _activate(self, index):
        """The action button / Enter / double-click: in "buy" mode open the
        purchase confirmation for the selected stock ship; in "owned" mode
        switch to flying the selected owned hull."""
        items = self._current_list()
        if not 0 <= index < len(items):
            return
        if self._owned_mode():
            if self.on_switch and index != self._active_index():
                name = get_ship_type(self.story, self._id_of(items[index])).get("name", "ship")
                self.on_switch(index)
                self.message = f"Now flying your {name}"
                self.message_timer = PURCHASE_MESSAGE_FRAMES
            return
        ship_type_id = items[index]
        if ship_type_id and not self._disabled_reason(ship_type_id):
            ship_type = get_ship_type(self.story, ship_type_id)
            self.confirm = ConfirmDialog(
                f"Buy {ship_type.get('name', ship_type_id)}?",
                f"{ship_type.get('cost', 0)}cr",
                context_data=ship_type_id,
            )

    def buttons(self):
        items = self._current_list()
        if self._owned_mode():
            disabled = not items or self.grid.selected == self._active_index()
            action = ("action", "Fly this", (150, 220, 160), disabled)
        else:
            ship_id = self.grid.current()
            disabled = not ship_id or bool(self._disabled_reason(ship_id))
            action = ("action", "Buy", (150, 220, 160), disabled)
        rows = [("close", "Close", (235, 235, 240), False), action]
        if self.on_switch:
            label = "Shop" if self._owned_mode() else "Your Ships"
            rows.append(("toggle", label, (200, 210, 235), not self.possessions.owned_ships))
        return rows

    def panel_rect(self, scale):
        return modal_panel_rect(scale, 0.1, 0.8, 0.8)

    def button_bar_rects(self, scale):
        panel = self.panel_rect(scale)
        w, h, m = int(120 * scale), int(38 * scale), int(16 * scale)
        close_rect = pygame.Rect(panel.x + m, panel.y + m, w, h)
        aw = int(150 * scale)
        action_rect = pygame.Rect(panel.centerx - aw // 2, panel.bottom - int(58 * scale), aw, int(42 * scale))
        rects = [close_rect, action_rect]
        if self.on_switch:
            tw = int(150 * scale)
            rects.append(pygame.Rect(panel.right - m - tw, panel.y + m, tw, h))
        return rects

    def active_popup(self):
        return self.confirm

    def draw_content(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = self.panel_rect(scale)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_info = get_font(int(20 * scale))

        y = panel_rect.y + int(20 * scale)
        y += draw_glow_title(surface, "Your Ships" if self._owned_mode() else "Shipyard",
                             font_title, panel_rect.centerx, y)
        y += int(10 * scale)

        if self._owned_mode():
            sub = "Pick a hull and press Fly this to switch to it."
        else:
            sub = f"Credits: {self.possessions.credits}"
        credits_text = font_info.render(sub, True, (255, 220, 100))
        surface.blit(credits_text, (panel_rect.centerx - credits_text.get_width() // 2, y))
        grid_top = y + int(40 * scale)

        gap = int(14 * scale)
        grid_area_width = int(panel_rect.width * 0.42)
        cell_width = (grid_area_width - gap * (GRID_COLUMNS - 1)) // GRID_COLUMNS
        cell_height = int(120 * scale)
        grid_left = panel_rect.x + int(30 * scale)

        draw_cell = functools.partial(self._draw_cell, scale=scale)
        self.grid.draw(surface, (grid_left, grid_top), cell_width, cell_height, gap, draw_cell,
                        disabled_fn=self._disabled_reason)

        preview_x = panel_rect.x + panel_rect.width * 3 // 4

        selected_item = self.grid.current()
        if selected_item is not None:
            selected_id = self._id_of(selected_item)
            ship_type = get_ship_type(self.story, selected_id)
            graphics = get_graphics_asset(self.story, "ships", selected_id)
            preview_center_y = panel_rect.y + int(140 * scale)
            # Slowly spin the preview and cycle its thrusters on/off so a
            # browsed ship's silhouette, windows, and engine mounts are all
            # visible without needing to buy it first. Driven off the clock
            # (like draw_selection_highlight's pulse) rather than per-frame
            # state, so this menu doesn't need its own update() method.
            # The grid icons stay static (angle=0, thrust=0, draw_ship_
            # glyph's defaults) so they read as a stable shop shelf - only
            # this one live preview animates.
            ticks = pygame.time.get_ticks()
            preview_angle = (ticks / 30) % 360
            preview_thrust = 1.0 if (ticks // 1000) % 2 == 0 else 0.0
            draw_ship_glyph(surface, preview_x, preview_center_y, int(45 * scale), graphics,
                             angle=preview_angle, thrust=preview_thrust)

            if self._owned_mode():
                head = "CURRENTLY FLYING" if self.grid.selected == self._active_index() else "Owned hull"
            else:
                head = f"Owned: {self._owned_count(selected_id)}"
            slots = ship_type.get("slots", [])
            slot_summary = self._format_slots(slots)
            stats = [
                ship_type.get("description", ""),
                head,
                f"Approximate Size: {_approximate_size_label(graphics)}",
                f"Thrust: {ship_type.get('max_thrust', 0)}",
                f"Max Velocity: {ship_type.get('max_velocity', 0)}",
                f"Rotation: {ship_type.get('rotation_speed', 0)}",
                f"Cargo Capacity: {ship_type.get('cargo_capacity', 0)}",
                f"Slots: {slot_summary}",
                f"Cost: {ship_type.get('cost', 0)}cr",
            ]
            stat_y = preview_center_y + int(62 * scale)
            for line in stats:
                text = font_info.render(line, True, GRAY if line != stats[-1] else YELLOW)
                surface.blit(text, (preview_x - text.get_width() // 2, stat_y))
                stat_y += int(23 * scale)

        # The Close/Buy buttons, and deferring to the purchase ConfirmDialog
        # while it's up, are handled by MenuBase.draw via buttons()/active_popup().
        if self.message_timer > 0:
            self.message_timer -= 1
            draw_purchase_message(surface, self.message, self.message_timer, panel_rect.centerx, panel_rect.bottom - int(100 * scale), scale)

    def _draw_cell(self, surface, rect, item, is_selected, reason, scale):
        """cell_draw_fn for the ship IconGrid - a static silhouette (no
        rotation/thrust, unlike the animated preview on the right), the
        ship's name, and its cost (buy mode) or fly/owned status (owned mode)."""
        ship_type_id = self._id_of(item)
        ship_type = get_ship_type(self.story, ship_type_id)
        graphics = get_graphics_asset(self.story, "ships", ship_type_id)
        icon_fn = functools.partial(draw_ship_glyph, graphics=graphics)
        if self._owned_mode():
            detail = "flying" if item == self._active_index() else "owned"
        else:
            owned = self._owned_count(ship_type_id)
            detail = f"{ship_type.get('cost', 0)}cr" + (f"  (own {owned})" if owned else "")
        draw_shop_cell(surface, rect, is_selected, reason, icon_fn, ship_type.get("name", ship_type_id), detail, scale)
