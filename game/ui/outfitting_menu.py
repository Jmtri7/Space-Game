"""Ship-outfitting menu: buy ship outfits and install/uninstall them into
the current ship's equipment slots. Opened via a "shop" config of type
"outfits" (see LocationScreen._build_local_character / main.py's
build_shop_menu), the same way ShopMenu/ShipBrowserMenu are."""
import math
import pygame
from game.constants import YELLOW, GRAY, GREEN, RED, WHITE
from game.utils import get_ui_scale, get_ui_offset, get_font, get_ship_outfit, get_ship_type, get_graphics_asset
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_ship_glyph, draw_selection_highlight
from game.ui.selectable_list import SelectableList

SLOT_COLORS = {
    "weapon": (200, 100, 100),
    "engine": (100, 150, 220),
    "shield": (100, 200, 180),
    "utility": (200, 180, 100),
}
SLOT_RADIUS = 14


class OutfittingMenu:
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
        self.buy_list = SelectableList(self.stock, max_visible=6)

        self.slots = get_ship_type(story, ship_type_id).get("slots", []) if ship_type_id else []
        self.focus_column = "slots"  # "slots" or "owned"
        self.slot_focus = 0
        self.owned_list = SelectableList(list(possessions.owned_outfits), max_visible=6)
        self.picker = None  # SelectableList of compatible outfits while choosing one for the focused slot

        # Drag-and-drop state (mouse). _slot_rects/_owned_item_rects are
        # filled in by draw() each frame (screen-space, same "cache during
        # draw, hit-test next frame" idiom SpaceScreen._hud_click_rects
        # uses) so handle_input's mouse events can hit-test against them.
        self.dragging_outfit = None
        self.drag_source = None  # ("owned",) or ("slot", slot_id)
        self.drag_pos = (0, 0)
        self.hover_slot = None
        self._slot_rects = {}
        self._owned_item_rects = []

    def _resolve(self, outfit_id):
        return get_ship_outfit(self.story, outfit_id)

    def _refresh_owned_list(self):
        self.owned_list.items = list(self.possessions.owned_outfits)

    def _compatible_owned_outfits(self, slot_type):
        return [oid for oid in self.possessions.owned_outfits if self._resolve(oid).get("slot_type") == slot_type]

    def _buy_disabled_reason(self, outfit_id):
        cost = self._resolve(outfit_id).get("cost", 0)
        if not self.possessions.can_afford(cost):
            return "not enough credits"
        return None

    def _buy_label(self, outfit_id):
        outfit = self._resolve(outfit_id)
        return f"{outfit.get('name', outfit_id)} ({outfit.get('slot_type', '?')}) - {outfit.get('cost', 0)}cr"

    def _owned_label(self, outfit_id):
        outfit = self._resolve(outfit_id)
        return f"{outfit.get('name', outfit_id)} ({outfit.get('slot_type', '?')})"

    def _buy_outfit(self, outfit_id):
        if self._buy_disabled_reason(outfit_id):
            return
        cost = self._resolve(outfit_id).get("cost", 0)
        self.possessions.spend(cost)
        self.possessions.add_outfit(outfit_id)
        self._refresh_owned_list()

    def _install(self, slot_id, outfit_id):
        self.possessions.install_outfit(slot_id, outfit_id)
        self._refresh_owned_list()
        if self.on_outfits_changed:
            self.on_outfits_changed()

    def _uninstall(self, slot_id):
        if self.possessions.uninstall_outfit(slot_id) is not None:
            self._refresh_owned_list()
            if self.on_outfits_changed:
                self.on_outfits_changed()

    def handle_input(self, events):
        for event in events:
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
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.tab = "buy" if self.tab == "install" else "install"
        elif self.tab == "buy":
            if key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self.buy_list.handle_key(key, disabled_fn=self._buy_disabled_reason)
            elif key == pygame.K_RETURN:
                outfit_id = self.buy_list.current()
                if outfit_id:
                    self._buy_outfit(outfit_id)
        else:  # install tab
            if key == pygame.K_TAB:
                self.focus_column = "owned" if self.focus_column == "slots" else "slots"
            elif key in (pygame.K_UP, pygame.K_w) and self.slots:
                if self.focus_column == "slots":
                    self.slot_focus = (self.slot_focus - 1) % len(self.slots)
                else:
                    self.owned_list.handle_key(pygame.K_UP)
            elif key in (pygame.K_DOWN, pygame.K_s) and self.slots:
                if self.focus_column == "slots":
                    self.slot_focus = (self.slot_focus + 1) % len(self.slots)
                else:
                    self.owned_list.handle_key(pygame.K_DOWN)
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
        for slot_id, rect in self._slot_rects.items():
            if rect.collidepoint(pos):
                outfit_id = self.possessions.installed_outfits.get(slot_id)
                if outfit_id:
                    self.dragging_outfit = outfit_id
                    self.drag_source = ("slot", slot_id)
                    self.drag_pos = pos
                return
        for outfit_id, rect in self._owned_item_rects:
            if rect.collidepoint(pos):
                self.dragging_outfit = outfit_id
                self.drag_source = ("owned",)
                self.drag_pos = pos
                return

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

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.08), int(offset_y + 600 * scale * 0.08), int(800 * scale * 0.84), int(600 * scale * 0.84))
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
        y += int(36 * scale)

        credits_text = font_info.render(f"Credits: {self.possessions.credits}", True, (255, 220, 100))
        surface.blit(credits_text, (panel_rect.centerx - credits_text.get_width() // 2, y))
        y += int(34 * scale)

        if self.tab == "buy":
            self.buy_list.draw(surface, font_text, panel_rect.centerx, y, int(30 * scale), scale,
                                label_fn=self._buy_label, disabled_fn=self._buy_disabled_reason)
        else:
            self._draw_install_tab(surface, panel_rect, y, scale, font_text, font_info)

        help_text = font_info.render("Left/Right: Buy/Install, ESC: close", True, (150, 150, 150))
        surface.blit(help_text, (panel_rect.x + int(20 * scale), panel_rect.bottom - int(30 * scale)))

        if self.dragging_outfit:
            drag_text = font_text.render(self._resolve(self.dragging_outfit).get("name", self.dragging_outfit), True, WHITE)
            surface.blit(drag_text, (self.drag_pos[0] - drag_text.get_width() // 2, self.drag_pos[1] - drag_text.get_height() // 2))

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
            label = self._resolve(installed_id).get("name", installed_id) if installed_id else f"({slot['type']})"
            label_text = font_info.render(label, True, WHITE if installed_id else GRAY)
            surface.blit(label_text, (rect.centerx - label_text.get_width() // 2, rect.bottom + int(4 * scale)))

        owned_x = panel_rect.x + panel_rect.width * 3 // 4
        owned_title = font_info.render("Spare Outfits", True, YELLOW if self.focus_column == "owned" else GRAY)
        surface.blit(owned_title, (owned_x - owned_title.get_width() // 2, y))

        self._refresh_owned_list()
        owned_list_top = y + int(36 * scale)
        line_height = int(30 * scale)
        self.owned_list.draw(surface, font_text, owned_x, owned_list_top, line_height, scale, label_fn=self._owned_label)

        self._owned_item_rects = []
        visible = self.owned_list.items[self.owned_list.scroll_offset:self.owned_list.scroll_offset + self.owned_list.max_visible]
        for i, outfit_id in enumerate(visible):
            label_text = font_text.render(self._owned_label(outfit_id), True, WHITE)
            row_y = owned_list_top + i * line_height
            rect = pygame.Rect(owned_x - label_text.get_width() // 2 - int(10 * scale), row_y - int(4 * scale), label_text.get_width() + int(20 * scale), label_text.get_height() + int(8 * scale))
            self._owned_item_rects.append((outfit_id, rect))

        if self.picker is not None:
            picker_rect = pygame.Rect(panel_rect.centerx - int(150 * scale), panel_rect.centery - int(100 * scale), int(300 * scale), int(200 * scale))
            draw_glass_panel(surface, picker_rect, scale)
            picker_title = font_info.render("Choose an outfit", True, YELLOW)
            surface.blit(picker_title, (picker_rect.centerx - picker_title.get_width() // 2, picker_rect.y + int(10 * scale)))
            self.picker.draw(surface, font_text, picker_rect.centerx, picker_rect.y + int(50 * scale), int(28 * scale), scale, label_fn=self._owned_label)
