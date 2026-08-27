"""Ship-outfitting menu: buy ship outfits and install/uninstall them into
the current ship's equipment slots. Opened via a "shop" config of type
"outfits" (see LocationScreen._build_local_character / main.py's
build_shop_menu), the same way ShopMenu/ShipBrowserMenu are."""
import functools
import math
import pygame
from game.constants import YELLOW, GRAY, GREEN, WHITE
from game.utils import get_ui_scale, get_ui_offset, get_font, get_ship_outfit, get_ship_type, get_graphics_asset
from game.ui.ui_theme import (
    draw_glass_panel, draw_glow_title, draw_ship_glyph, draw_selection_highlight, draw_item_icon,
    draw_purchase_message, modal_panel_rect, PURCHASE_MESSAGE_FRAMES, DISABLED_TEXT_COLOR,
)
from game.ui.selectable_list import SelectableList
from game.ui.icon_grid import IconGrid
from game.ui.menu_base import MenuBase

SLOT_COLORS = {
    "weapon": (200, 100, 100),
    "engine": (100, 150, 220),
    "shield": (100, 200, 180),
    "utility": (200, 180, 100),
}
# Default icon glyph per slot type, used unless an outfit's own config sets
# an explicit "icon_shape" - so every outfit gets a sane, on-theme icon for
# free, and a story can still override individual outfits later.
SLOT_ICON_SHAPES = {
    "weapon": "blade",
    "engine": "flame",
    "shield": "shield",
    "utility": "gear",
}
SLOT_RADIUS = 14
GRID_COLUMNS = 3
GRID_ROWS = 2


class OutfittingMenu(MenuBase):
    """Buy tab: same buy-list pattern as ShopMenu, but purchasing adds to
    possessions.owned_outfits (spare, uninstalled) instead of equipping
    directly. Install tab: a diagram of the current ship's slots (from
    ship_types.json) plus a list of owned-but-uninstalled outfits - drag one
    onto a slot to equip (mouse), or use the keyboard fallback (Tab to
    switch focus between the slots/owned columns, arrows to move within a
    column, Enter to act). Equip/uninstall calls on_outfits_changed so the
    flown ship's stats update immediately (see SpaceScreen.reapply_outfits)
    instead of only on the next save/load."""

    def __init__(self, possessions, story, shop_config, ship_type_id, on_outfits_changed=None):
        self.possessions = possessions
        self.story = story
        self.stock = list(shop_config.get("stock", []))
        self.ship_type_id = ship_type_id
        self.on_outfits_changed = on_outfits_changed

        self.tab = "install" if ship_type_id else "buy"  # nothing to install without a ship
        self.buy_grid = IconGrid(self.stock, columns=GRID_COLUMNS, max_rows=GRID_ROWS)

        self.slots = get_ship_type(story, ship_type_id).get("slots", []) if ship_type_id else []
        self.focus_column = "slots"  # "slots" or "owned"
        self.slot_focus = 0
        # A single-column IconGrid rather than SelectableList - reads as a
        # small grid of icons (matching the Buy tab) instead of plain text
        # rows, while keeping Up/Down navigation identical to a 1D list
        # (see docs/DESIGN_PATTERNS.md's "2D Grid Sibling" - columns=1 just
        # means Left/Right, which this menu never sends it, never comes up).
        self.owned_grid = IconGrid(list(possessions.owned_outfits), columns=1, max_rows=6)
        self.picker = None  # SelectableList of compatible outfits while choosing one for the focused slot

        # Drag-and-drop state (mouse). _slot_rects is filled in by draw()
        # each frame (screen-space, same "cache during draw, hit-test next
        # frame" idiom SpaceScreen._hud_click_rects uses); owned_grid keeps
        # its own equivalent cache (see IconGrid.last_rects/index_at).
        self.dragging_outfit = None
        self.drag_source = None  # ("owned",) or ("slot", slot_id)
        self.drag_pos = (0, 0)
        self.hover_slot = None
        self._slot_rects = {}
        # Screen-space rects for the Buy/Install tab labels, cached by
        # draw() each frame - same idiom as _slot_rects, lets a click tell
        # whether a tab label was hit before falling through to grid/slot
        # hit-testing.
        self._buy_tab_rect = None
        self._install_tab_rect = None
        # Transient "Bought 1 X" confirmation (see draw_purchase_message) -
        # message_timer counts down once per draw() call while > 0, since
        # nothing calls an OutfittingMenu.update() each frame.
        self.message = None
        self.message_timer = 0

    def _resolve(self, outfit_id):
        return get_ship_outfit(self.story, outfit_id)

    def _refresh_owned_grid(self):
        self.owned_grid.items = list(self.possessions.owned_outfits)

    def _compatible_owned_outfits(self, slot_type):
        return [oid for oid in self.possessions.owned_outfits if self._resolve(oid).get("slot_type") == slot_type]

    def _buy_disabled_reason(self, outfit_id):
        cost = self._resolve(outfit_id).get("cost", 0)
        if not self.possessions.can_afford(cost):
            return "not enough credits"
        return None

    def _owned_count(self, outfit_id):
        """Total units of outfit_id this character owns - spares
        (owned_outfits) plus however many are currently installed on the
        flown ship - so buying a second one you already have equipped still
        reads as "Own: 2", not "Own: 0"."""
        spare = self.possessions.owned_outfits.count(outfit_id)
        installed = list(self.possessions.installed_outfits.values()).count(outfit_id)
        return spare + installed

    def _fit_status(self, outfit_id, slot_type):
        """(text, color) describing whether outfit_id fits the ship
        currently being outfitted, for the Buy tab's cell - independent of
        _buy_disabled_reason (affordability), since an outfit can be fully
        affordable and still not fit any slot this ship has."""
        if not self.ship_type_id:
            return "No ship yet", GRAY
        matching_slots = [slot for slot in self.slots if slot["type"] == slot_type]
        if not matching_slots:
            return "Doesn't fit your ship", DISABLED_TEXT_COLOR
        if any(self.possessions.installed_outfits.get(slot["id"]) == outfit_id for slot in matching_slots):
            return "Equipped", GREEN
        return "Fits your ship", (140, 220, 140)

    def _icon_for(self, outfit_id):
        """(icon_shape, icon_color) for an outfit - its own config wins if
        set, otherwise a default keyed by slot_type (see SLOT_ICON_SHAPES/
        SLOT_COLORS), so every outfit gets a sane on-theme icon without
        needing per-outfit config."""
        outfit = self._resolve(outfit_id)
        slot_type = outfit.get("slot_type")
        icon_shape = outfit.get("icon_shape", SLOT_ICON_SHAPES.get(slot_type))
        icon_color = outfit.get("icon_color", SLOT_COLORS.get(slot_type))
        return icon_shape, icon_color

    def _owned_label(self, outfit_id):
        outfit = self._resolve(outfit_id)
        return f"{outfit.get('name', outfit_id)} ({outfit.get('slot_type', '?')})"

    def _draw_owned_cell(self, surface, rect, outfit_id, is_selected, reason, scale):
        """cell_draw_fn for owned_grid (see IconGrid.draw) - an icon plus
        name/slot-type label per row, replacing the old plain-text
        SelectableList so a spare outfit reads (and drags) the same visual
        way whether it's in a slot or still in this list."""
        is_focused_here = is_selected and self.focus_column == "owned"
        if is_focused_here:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)
            draw_selection_highlight(surface, rect, scale, pulse)
        icon_shape, icon_color = self._icon_for(outfit_id)
        icon_size = int(rect.height * 0.38)
        icon_cx = rect.x + int(rect.height * 0.5)
        draw_item_icon(surface, icon_cx, rect.centery, icon_size, icon_shape, icon_color)
        font = get_font(int(16 * scale))
        label = font.render(self._owned_label(outfit_id), True, WHITE if is_focused_here else GRAY)
        surface.blit(label, (rect.x + int(rect.height * 0.9), rect.centery - label.get_height() // 2))

    def _buy_outfit(self, outfit_id):
        if self._buy_disabled_reason(outfit_id):
            return
        cost = self._resolve(outfit_id).get("cost", 0)
        self.possessions.spend(cost)
        self.possessions.add_outfit(outfit_id)
        self._refresh_owned_grid()
        self.message = f"Bought 1 {self._resolve(outfit_id).get('name', outfit_id)}"
        self.message_timer = PURCHASE_MESSAGE_FRAMES

    def _install(self, slot_id, outfit_id):
        self.possessions.install_outfit(slot_id, outfit_id)
        self._refresh_owned_grid()
        if self.on_outfits_changed:
            self.on_outfits_changed()

    def _uninstall(self, slot_id):
        if self.possessions.uninstall_outfit(slot_id) is not None:
            self._refresh_owned_grid()
            if self.on_outfits_changed:
                self.on_outfits_changed()

    def handle_input(self, events):
        for event in events:
            if self.picker is None and self.handle_button_click(event, lambda: self._button_rects(get_ui_scale())) == "close":
                return "close"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_mouse_down(event.pos)
            elif event.type == pygame.MOUSEMOTION and self.dragging_outfit:
                self.drag_pos = event.pos
                self.hover_slot = self._slot_at(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_outfit:
                self._handle_drop(event.pos)
            elif event.type == pygame.KEYDOWN:
                result = self._handle_key(event.key)
                if result:
                    return result
        return None

    def _handle_key(self, key):
        if self.picker is not None:
            if key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self.picker.handle_key(key)
            elif key == pygame.K_RETURN:
                outfit_id = self.picker.current()
                if outfit_id:
                    self._install(self.slots[self.slot_focus]["id"], outfit_id)
                self.picker = None
            elif key == pygame.K_ESCAPE:
                self.picker = None
            return None

        if key == pygame.K_ESCAPE:
            return "close"
        elif key == pygame.K_TAB:
            self.tab = "buy" if self.tab == "install" else "install"
        elif self.tab == "buy":
            if key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_LEFT, pygame.K_RIGHT):
                # No disabled_fn: browsing the grid stays free even over
                # outfits you can't currently afford - only Enter is
                # gated, same reasoning as ShopMenu/ShipBrowserMenu.
                self.buy_grid.handle_key(key)
            elif key == pygame.K_RETURN:
                outfit_id = self.buy_grid.current()
                if outfit_id:
                    self._buy_outfit(outfit_id)
        else:  # install tab
            if key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.focus_column = "owned" if self.focus_column == "slots" else "slots"
            elif key in (pygame.K_UP, pygame.K_w) and self.slots:
                if self.focus_column == "slots":
                    self.slot_focus = (self.slot_focus - 1) % len(self.slots)
                else:
                    self.owned_grid.handle_key(pygame.K_UP)
            elif key in (pygame.K_DOWN, pygame.K_s) and self.slots:
                if self.focus_column == "slots":
                    self.slot_focus = (self.slot_focus + 1) % len(self.slots)
                else:
                    self.owned_grid.handle_key(pygame.K_DOWN)
            elif key == pygame.K_RETURN and self.focus_column == "slots" and self.slots:
                slot = self.slots[self.slot_focus]
                installed = self.possessions.installed_outfits.get(slot["id"])
                if installed:
                    self._uninstall(slot["id"])
                else:
                    compatible = self._compatible_owned_outfits(slot["type"])
                    if compatible:
                        self.picker = SelectableList(compatible, max_visible=6)
        return None

    def _slot_at(self, pos):
        for slot_id, rect in self._slot_rects.items():
            if rect.collidepoint(pos):
                return slot_id
        return None

    def _handle_mouse_down(self, pos):
        """Click routing for both tabs: tab labels always work first; a
        picker popup (keyboard/ESC only) swallows clicks underneath it so
        one doesn't accidentally start a drag through it; the Buy grid
        clicks-to-buy (mirroring Enter); the Install tab's slots/owned grid
        both move keyboard focus to whatever was clicked and - if it's
        occupied - start a drag, so a plain click-and-release just selects
        (matches _handle_drop's "dropped back where it came from" no-op)
        while a click-and-drag installs/uninstalls."""
        if self._buy_tab_rect and self._buy_tab_rect.collidepoint(pos):
            self.tab = "buy"
            return
        if self._install_tab_rect and self._install_tab_rect.collidepoint(pos):
            self.tab = "install"
            return
        if self.picker is not None:
            return

        if self.tab == "buy":
            # Click only selects, same as arrow-key browsing - it used to
            # also buy immediately, but that made a stray click too easy
            # to mistake for a purchase. Enter (still) buys the selection.
            index = self.buy_grid.index_at(pos)
            if index is not None:
                self.buy_grid.selected = index
            return

        for i, slot in enumerate(self.slots):
            rect = self._slot_rects.get(slot["id"])
            if rect and rect.collidepoint(pos):
                self.focus_column = "slots"
                self.slot_focus = i
                outfit_id = self.possessions.installed_outfits.get(slot["id"])
                if outfit_id:
                    self.dragging_outfit = outfit_id
                    self.drag_source = ("slot", slot["id"])
                    self.drag_pos = pos
                return
        index = self.owned_grid.index_at(pos)
        if index is not None:
            self.focus_column = "owned"
            self.owned_grid.selected = index
            outfit_id = self.owned_grid.items[index]
            self.dragging_outfit = outfit_id
            self.drag_source = ("owned",)
            self.drag_pos = pos

    def _handle_drop(self, pos):
        outfit_id = self.dragging_outfit
        target_slot = self._slot_at(pos)
        if target_slot is not None and self.drag_source == ("slot", target_slot):
            pass  # dropped back into the slot it came from - no-op
        elif target_slot is not None:
            slot = next(s for s in self.slots if s["id"] == target_slot)
            if slot["type"] == self._resolve(outfit_id).get("slot_type"):
                if self.drag_source[0] == "slot":
                    self.possessions.uninstall_outfit(self.drag_source[1])
                self._install(target_slot, outfit_id)
        elif self.drag_source[0] == "slot":
            self._uninstall(self.drag_source[1])
        # dropped somewhere else (e.g. back on the owned list, or empty
        # space) - nothing to do, state never changed so nothing snaps back.
        self.dragging_outfit = None
        self.drag_source = None
        self.hover_slot = None

    def draw_content(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        # Taller than a plain price-list panel would need - the Buy tab's
        # cells now carry owned-count/slot/fit info on top of name+cost
        # (see _draw_buy_cell). Help text lives in the top-left Controls
        # pane now (see draw()'s end), not in this panel, so it no longer
        # needs extra room at the bottom for that.
        panel_rect = self.panel_rect(scale)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(32 * scale))
        font_info = get_font(int(20 * scale))
        font_text = get_font(int(22 * scale))

        y = panel_rect.y + int(16 * scale)
        y += draw_glow_title(surface, "Outfitter", font_title, panel_rect.centerx, y)

        buy_color = YELLOW if self.tab == "buy" else GRAY
        install_color = YELLOW if self.tab == "install" else GRAY
        tabs_text = font_info.render("Buy", True, buy_color)
        tabs_text2 = font_info.render(" / Install", True, install_color)
        tabs_x = panel_rect.centerx - (tabs_text.get_width() + tabs_text2.get_width()) // 2
        surface.blit(tabs_text, (tabs_x, y))
        surface.blit(tabs_text2, (tabs_x + tabs_text.get_width(), y))
        self._buy_tab_rect = pygame.Rect(tabs_x, y, tabs_text.get_width(), tabs_text.get_height())
        self._install_tab_rect = pygame.Rect(tabs_x + tabs_text.get_width(), y, tabs_text2.get_width(), tabs_text2.get_height())
        y += int(36 * scale)

        credits_text = font_info.render(f"Credits: {self.possessions.credits}", True, (255, 220, 100))
        surface.blit(credits_text, (panel_rect.centerx - credits_text.get_width() // 2, y))
        y += int(34 * scale)

        if self.tab == "buy":
            self._draw_buy_tab(surface, panel_rect, y, scale, font_info)
        else:
            self._draw_install_tab(surface, panel_rect, y, scale, font_text, font_info)

        # The Close button + hint line are drawn by MenuBase.draw via
        # buttons()/hint_text().
        if self.message_timer > 0:
            self.message_timer -= 1
            draw_purchase_message(surface, self.message, self.message_timer, panel_rect.centerx, panel_rect.bottom - int(58 * scale), scale)

        if self.dragging_outfit:
            drag_text = font_text.render(self._resolve(self.dragging_outfit).get("name", self.dragging_outfit), True, WHITE)
            surface.blit(drag_text, (self.drag_pos[0] - drag_text.get_width() // 2, self.drag_pos[1] - drag_text.get_height() // 2))

    def buttons(self):
        return [("close", "Close", (235, 235, 240), False)]

    def panel_rect(self, scale):
        return modal_panel_rect(scale, 0.08, 0.84, 0.84)

    def _button_rects(self, scale):
        panel = self.panel_rect(scale)
        w, h, m = int(120 * scale), int(38 * scale), int(16 * scale)
        return [pygame.Rect(panel.x + m, panel.y + m, w, h)]

    def button_bar_rects(self, scale):
        return self._button_rects(scale)

    def hint_text(self):
        """Condensed control reminder under the panel, tab-dependent - the
        Install tab has both a drag-and-drop and a keyboard path."""
        if self.picker is not None:
            return "Up/Down + Enter to install into the slot  ·  ESC to cancel"
        if self.tab == "buy":
            return "Tab: switch tab  ·  arrows/click: browse  ·  Enter: buy  ·  ESC: close"
        return ("Tab: switch tab  ·  drag a spare onto a slot to install  ·  "
                "Left/Right + Up/Down + Enter also work  ·  ESC: close")

    def _draw_buy_tab(self, surface, panel_rect, y, scale, font_info):
        grid = self.buy_grid
        if grid.has_more_above:
            up_indicator = font_info.render("^ more", True, GRAY)
            surface.blit(up_indicator, (panel_rect.centerx - up_indicator.get_width() // 2, y))
        y += int(18 * scale)

        gap = int(14 * scale)
        cell_width = (panel_rect.width - int(60 * scale) - gap * (GRID_COLUMNS - 1)) // GRID_COLUMNS
        cell_height = int(148 * scale)
        grid_left = panel_rect.centerx - (cell_width * GRID_COLUMNS + gap * (GRID_COLUMNS - 1)) // 2

        draw_cell = functools.partial(self._draw_buy_cell, scale=scale)
        grid.draw(surface, (grid_left, y), cell_width, cell_height, gap, draw_cell, disabled_fn=self._buy_disabled_reason)

        grid_bottom = y + cell_height * GRID_ROWS + gap * (GRID_ROWS - 1)
        if grid.has_more_below:
            down_indicator = font_info.render("v more", True, GRAY)
            surface.blit(down_indicator, (panel_rect.centerx - down_indicator.get_width() // 2, grid_bottom + int(4 * scale)))

    def _draw_buy_cell(self, surface, rect, outfit_id, is_selected, reason, scale):
        """Bespoke cell layout (not the shared ui_theme.draw_shop_cell) -
        outfits need more info per cell than a plain price: how many you
        already own (spares + installed), which slot type they use, and
        whether your current ship can actually fit one."""
        outfit = self._resolve(outfit_id)
        icon_shape, icon_color = self._icon_for(outfit_id)

        if is_selected:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)
            draw_selection_highlight(surface, rect, scale, pulse)

        icon_cy = rect.y + int(rect.height * 0.15)
        icon_size = int(rect.height * 0.12)
        draw_item_icon(surface, rect.centerx, icon_cy, icon_size, icon_shape, icon_color)

        font_name = get_font(int(18 * scale))
        font_detail = get_font(int(14 * scale))
        name_color = DISABLED_TEXT_COLOR if reason else (WHITE if is_selected else GRAY)
        cost_color = DISABLED_TEXT_COLOR if reason else YELLOW

        name_text = font_name.render(outfit.get("name", outfit_id), True, name_color)
        surface.blit(name_text, (rect.centerx - name_text.get_width() // 2, rect.y + int(rect.height * 0.28)))

        cost_text = font_detail.render(f"{outfit.get('cost', 0)}cr", True, cost_color)
        surface.blit(cost_text, (rect.centerx - cost_text.get_width() // 2, rect.y + int(rect.height * 0.44)))

        slot_type = outfit.get("slot_type", "?")
        own_text = font_detail.render(f"Own: {self._owned_count(outfit_id)}   Slot: {slot_type}", True, GRAY)
        surface.blit(own_text, (rect.centerx - own_text.get_width() // 2, rect.y + int(rect.height * 0.58)))

        fit_text, fit_color = self._fit_status(outfit_id, slot_type)
        fit_rendered = font_detail.render(fit_text, True, DISABLED_TEXT_COLOR if reason else fit_color)
        surface.blit(fit_rendered, (rect.centerx - fit_rendered.get_width() // 2, rect.y + int(rect.height * 0.72)))

        if reason:
            reason_text = font_detail.render(f"({reason})", True, DISABLED_TEXT_COLOR)
            surface.blit(reason_text, (rect.centerx - reason_text.get_width() // 2, rect.y + int(rect.height * 0.87)))

    def _draw_install_tab(self, surface, panel_rect, y, scale, font_text, font_info):
        if not self.ship_type_id:
            no_ship_text = font_text.render("No ship to outfit yet.", True, GRAY)
            surface.blit(no_ship_text, (panel_rect.centerx - no_ship_text.get_width() // 2, y))
            return

        diagram_cx = panel_rect.x + panel_rect.width * 3 // 8
        diagram_cy = y + int(150 * scale)
        graphics = get_graphics_asset(self.story, "ships", self.ship_type_id)
        draw_ship_glyph(surface, diagram_cx, diagram_cy, int(45 * scale), graphics)

        self._slot_rects = {}
        for i, slot in enumerate(self.slots):
            slot_x = diagram_cx + int((slot.get("x", 0.5) - 0.5) * 140 * scale)
            slot_y = diagram_cy + int((slot.get("y", 0.5) - 0.5) * 140 * scale)
            radius = int(SLOT_RADIUS * scale)
            rect = pygame.Rect(slot_x - radius, slot_y - radius, radius * 2, radius * 2)
            self._slot_rects[slot["id"]] = rect

            color = SLOT_COLORS.get(slot["type"], GRAY)
            is_focused = (self.focus_column == "slots" and i == self.slot_focus)
            is_hover = (self.hover_slot == slot["id"])
            width = 0 if is_hover else 2
            pygame.draw.circle(surface, color, rect.center, radius, width)
            if is_focused:
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)
                draw_selection_highlight(surface, rect.inflate(int(6 * scale), int(6 * scale)), scale, pulse)

            installed_id = self.possessions.installed_outfits.get(slot["id"])
            if installed_id:
                icon_shape, icon_color = self._icon_for(installed_id)
                draw_item_icon(surface, rect.centerx, rect.centery, int(radius * 0.7), icon_shape, icon_color)
                label = self._resolve(installed_id).get("name", installed_id)
            else:
                label = f"({slot['type']})"
            label_text = font_info.render(label, True, WHITE if installed_id else GRAY)
            surface.blit(label_text, (rect.centerx - label_text.get_width() // 2, rect.bottom + int(4 * scale)))

        owned_x = panel_rect.x + panel_rect.width * 3 // 4
        owned_title = font_info.render("Spare Outfits", True, YELLOW if self.focus_column == "owned" else GRAY)
        surface.blit(owned_title, (owned_x - owned_title.get_width() // 2, y))

        self._refresh_owned_grid()
        owned_grid_top = y + int(36 * scale)
        gap = int(8 * scale)
        cell_width = int(min(220 * scale, panel_rect.width * 0.22))
        cell_height = int(34 * scale)
        if self.owned_grid.has_more_above:
            up_indicator = font_info.render("^ more", True, GRAY)
            surface.blit(up_indicator, (owned_x - up_indicator.get_width() // 2, owned_grid_top))
            owned_grid_top += int(18 * scale)
        draw_owned_cell = functools.partial(self._draw_owned_cell, scale=scale)
        self.owned_grid.draw(surface, (owned_x - cell_width // 2, owned_grid_top), cell_width, cell_height, gap, draw_owned_cell)
        owned_grid_bottom = owned_grid_top + cell_height * self.owned_grid.max_rows + gap * (self.owned_grid.max_rows - 1)
        if self.owned_grid.has_more_below:
            down_indicator = font_info.render("v more", True, GRAY)
            surface.blit(down_indicator, (owned_x - down_indicator.get_width() // 2, owned_grid_bottom + int(4 * scale)))

        if self.picker is not None:
            picker_rect = pygame.Rect(panel_rect.centerx - int(150 * scale), panel_rect.centery - int(100 * scale), int(300 * scale), int(200 * scale))
            draw_glass_panel(surface, picker_rect, scale)
            picker_title = font_info.render("Choose an outfit", True, YELLOW)
            surface.blit(picker_title, (picker_rect.centerx - picker_title.get_width() // 2, picker_rect.y + int(10 * scale)))
            self.picker.draw(surface, font_text, picker_rect.centerx, picker_rect.y + int(50 * scale), int(28 * scale), scale, label_fn=self._owned_label)
