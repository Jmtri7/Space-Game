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

    def __init__(self, possessions, story, shop_config, on_buy):
        self.possessions = possessions
        self.story = story
        self.stock = list(shop_config.get("stock", []))
        self.on_buy = on_buy
        self.grid = IconGrid(self.stock, columns=GRID_COLUMNS, max_rows=GRID_ROWS)
        self.confirm = None  # ConfirmDialog while a purchase is pending confirmation
        # Transient "Bought 1 X" confirmation (see draw_purchase_message) -
        # message_timer counts down once per draw() call while > 0, since
        # nothing calls a ShipBrowserMenu.update() each frame.
        self.message = None
        self.message_timer = 0

    def _disabled_reason(self, ship_type_id):
        cost = get_ship_type(self.story, ship_type_id).get("cost", 0)
        if not self.possessions.can_afford(cost):
            return "not enough credits"
        return None

    def _owned_count(self, ship_type_id):
        return self.possessions.owned_ships.count(ship_type_id)

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
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Click only selects (and updates the live preview) - it
                # used to also open the buy confirmation immediately, but
                # that made a stray click too easy to mistake for "buy".
                # Enter (still) opens the confirmation.
                index = self.grid.index_at(event.pos)
                if index is not None:
                    self.grid.selected = index
                continue
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                return "close"
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_LEFT, pygame.K_RIGHT):
                # No disabled_fn: the preview is tied to this same cursor,
                # so skipping unaffordable ships during navigation would
                # make them unpreviewable whenever at least one ship IS
                # affordable. Browsing stays free; only Enter checks
                # affordability.
                self.grid.handle_key(event.key)
            elif event.key == pygame.K_RETURN:
                self._open_confirm(self.grid.current())
        return None

    def _open_confirm(self, ship_type_id):
        """Open the Yes/No purchase confirmation for ship_type_id - shared
        by Enter and a grid click, same as clicking a Menu item is
        equivalent to selecting it then pressing Enter."""
        if ship_type_id and not self._disabled_reason(ship_type_id):
            ship_type = get_ship_type(self.story, ship_type_id)
            self.confirm = ConfirmDialog(
                f"Buy {ship_type.get('name', ship_type_id)}?",
                f"{ship_type.get('cost', 0)}cr",
                context_data=ship_type_id,
            )

    def help_items(self):
        return [("Arrows/Click", "Browse"), ("Enter", "Buy"), ("ESC", "Close")]

    def active_popup(self):
        return self.confirm

    def draw_content(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = modal_panel_rect(scale, 0.1, 0.8, 0.8)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_info = get_font(int(20 * scale))

        y = panel_rect.y + int(20 * scale)
        y += draw_glow_title(surface, "Shipyard", font_title, panel_rect.centerx, y)
        y += int(10 * scale)

        credits_text = font_info.render(f"Credits: {self.possessions.credits}", True, (255, 220, 100))
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

        selected_id = self.grid.current()
        if selected_id:
            ship_type = get_ship_type(self.story, selected_id)
            graphics = get_graphics_asset(self.story, "ships", selected_id)
            preview_center_y = panel_rect.y + int(160 * scale)
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

            stats = [
                ship_type.get("description", ""),
                f"Owned: {self._owned_count(selected_id)}",
                f"Approximate Size: {_approximate_size_label(graphics)}",
                f"Thrust: {ship_type.get('max_thrust', 0)}",
                f"Max Velocity: {ship_type.get('max_velocity', 0)}",
                f"Rotation: {ship_type.get('rotation_speed', 0)}",
                f"Cargo Capacity: {ship_type.get('cargo_capacity', 0)}",
                f"Cost: {ship_type.get('cost', 0)}cr",
            ]
            stat_y = preview_center_y + int(70 * scale)
            for line in stats:
                text = font_info.render(line, True, GRAY if line != stats[-1] else YELLOW)
                surface.blit(text, (preview_x - text.get_width() // 2, stat_y))
                stat_y += int(26 * scale)

        # The Controls pane (top-left) and, while a purchase ConfirmDialog is
        # up, deferring to it instead are both handled by MenuBase.draw via
        # help_items()/active_popup().
        if self.message_timer > 0:
            self.message_timer -= 1
            draw_purchase_message(surface, self.message, self.message_timer, panel_rect.centerx, panel_rect.bottom - int(36 * scale), scale)

    def _draw_cell(self, surface, rect, ship_type_id, is_selected, reason, scale):
        """cell_draw_fn for the ship IconGrid - a static silhouette (no
        rotation/thrust, unlike the animated preview on the right), the
        ship's name, and its cost."""
        ship_type = get_ship_type(self.story, ship_type_id)
        graphics = get_graphics_asset(self.story, "ships", ship_type_id)
        icon_fn = functools.partial(draw_ship_glyph, graphics=graphics)
        owned = self._owned_count(ship_type_id)
        detail = f"{ship_type.get('cost', 0)}cr" + (f"  (own {owned})" if owned else "")
        draw_shop_cell(surface, rect, is_selected, reason, icon_fn, ship_type.get("name", ship_type_id), detail, scale)
