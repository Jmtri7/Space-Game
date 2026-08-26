"""Ship-buying menu with a live preview - opened by talking to an NPC whose
"shop" config has type "ships" (see LocationScreen._build_local_character),
replacing the old dialogue-tree "buy_ship:<id>" trick for any NPC that opts
into this instead."""
import pygame
from game.constants import YELLOW, GRAY, GREEN
from game.utils import get_ui_scale, get_ui_offset, get_font, get_ship_type, get_graphics_asset
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_ship_glyph
from game.ui.selectable_list import SelectableList
from game.ui.confirm_dialog import ConfirmDialog


class ShipBrowserMenu:
    """Left: a SelectableList of the shop's stock ship-type ids. Right: a
    live preview (ship glyph + stat readout) of whichever is selected.
    Enter opens a ConfirmDialog; confirming calls the injected on_buy
    callback (LocationScreen._buy_ship - see there for why LocationScreen
    owns the actual purchase mutation rather than this menu)."""

    def __init__(self, possessions, story, shop_config, on_buy):
        self.possessions = possessions
        self.story = story
        self.stock = list(shop_config.get("stock", []))
        self.on_buy = on_buy
        self.list = SelectableList(self.stock, max_visible=6)
        self.confirm = None  # ConfirmDialog while a purchase is pending confirmation

    def _disabled_reason(self, ship_type_id):
        cost = get_ship_type(self.story, ship_type_id).get("cost", 0)
        if not self.possessions.can_afford(cost):
            return "not enough credits"
        return None

    def handle_input(self, events):
        if self.confirm:
            action, ship_type_id = self.confirm.handle_input(events)
            if action == "confirm":
                self.on_buy(ship_type_id)
                self.confirm = None
            elif action == "cancel":
                self.confirm = None
            return None

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                return "close"
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self.list.handle_key(event.key, disabled_fn=self._disabled_reason)
            elif event.key == pygame.K_RETURN:
                ship_type_id = self.list.current()
                if ship_type_id and not self._disabled_reason(ship_type_id):
                    ship_type = get_ship_type(self.story, ship_type_id)
                    self.confirm = ConfirmDialog(
                        f"Buy {ship_type.get('name', ship_type_id)}?",
                        f"{ship_type.get('cost', 0)}cr",
                        context_data=ship_type_id,
                    )
        return None

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.1), int(offset_y + 600 * scale * 0.1), int(800 * scale * 0.8), int(600 * scale * 0.8))
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_info = get_font(int(20 * scale))
        font_text = get_font(int(22 * scale))

        y = panel_rect.y + int(20 * scale)
        y += draw_glow_title(surface, "Shipyard", font_title, panel_rect.centerx, y)
        y += int(10 * scale)

        credits_text = font_info.render(f"Credits: {self.possessions.credits}", True, (255, 220, 100))
        surface.blit(credits_text, (panel_rect.centerx - credits_text.get_width() // 2, y))
        list_top = y + int(40 * scale)

        list_x = panel_rect.x + panel_rect.width // 4
        preview_x = panel_rect.x + panel_rect.width * 3 // 4

        self.list.draw(surface, font_text, list_x, list_top, int(32 * scale), scale,
                        label_fn=lambda ship_type_id: get_ship_type(self.story, ship_type_id).get("name", ship_type_id),
                        disabled_fn=self._disabled_reason)

        selected_id = self.list.current()
        if selected_id:
            ship_type = get_ship_type(self.story, selected_id)
            graphics = get_graphics_asset(self.story, "ships", selected_id)
            preview_center_y = panel_rect.y + int(160 * scale)
            draw_ship_glyph(surface, preview_x, preview_center_y, int(45 * scale), graphics)

            stats = [
                ship_type.get("description", ""),
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

        help_text = font_info.render("Up/Down: select, Enter: buy, ESC: close", True, (150, 150, 150))
        surface.blit(help_text, (panel_rect.x + int(20 * scale), panel_rect.bottom - int(30 * scale)))

        if self.confirm:
            self.confirm.draw(surface)
