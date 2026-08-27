"""Read-only overview of a player's credits, ships, loans, cargo, personal
items, and ship outfits."""
import pygame
from game.utils import get_ui_scale, get_ui_offset, get_font, get_ship_type, get_ship_outfit, get_commodity, get_item
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_controls_pane, modal_panel_rect


class PossessionsMenu:
    """Read-only overview of everything the player owns - opened with P from
    anywhere (space, station, or moon). `ship` is the player's live Ship
    (PlayerController.ship) - optional so this can still be constructed
    without one (e.g. in a test), in which case the "Current Ship" section
    is just skipped rather than showing stale/placeholder stats."""
    def __init__(self, possessions, story="default", ship=None):
        self.possessions = possessions
        self.story = story
        self.ship = ship

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                return "close"
        return None

    def _draw_section(self, surface, font_section, font_text, x, y, line_height, scale, title, lines):
        """Draw one "Title" + indented bullet-line block, "- None" when
        `lines` is empty - the layout every section here shares. Returns
        the y position just after it."""
        title_text = font_section.render(title, True, (200, 220, 255))
        surface.blit(title_text, (x, y))
        y += line_height
        if lines:
            for line, color in lines:
                text = font_text.render(f"- {line}", True, color)
                surface.blit(text, (x + int(15 * scale), y))
                y += line_height
        else:
            none_text = font_text.render("- None", True, (150, 150, 150))
            surface.blit(none_text, (x + int(15 * scale), y))
            y += line_height
        return y + line_height

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = modal_panel_rect(scale, 0.08, 0.84, 0.84)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_section = get_font(int(23 * scale))
        font_text = get_font(int(19 * scale))

        draw_glow_title(surface, "Possessions", font_title, panel_rect.centerx, panel_rect.y + int(24 * scale))

        line_height = int(26 * scale)
        left_x = panel_rect.x + int(30 * scale)
        right_x = panel_rect.centerx + int(20 * scale)
        top_y = panel_rect.y + int(80 * scale)

        # Left column: credits, owned ships, loans, current ship stats.
        y = top_y
        credits_text = font_section.render(f"Credits: {self.possessions.credits}", True, (255, 220, 100))
        surface.blit(credits_text, (left_x, y))
        y += line_height * 2

        ship_lines = [(get_ship_type(self.story, sid).get("name", sid), (220, 220, 220)) for sid in self.possessions.owned_ships]
        y = self._draw_section(surface, font_section, font_text, left_x, y, line_height, scale, "Owned Ships", ship_lines)

        loan_lines = [(f"{loan['lender']}: {loan['principal']}cr", (220, 180, 180)) for loan in self.possessions.loans]
        y = self._draw_section(surface, font_section, font_text, left_x, y, line_height, scale, "Loans", loan_lines)

        if self.ship and self.possessions.owned_ships:
            ship_type_id = self.possessions.owned_ships[-1]
            ship_name = get_ship_type(self.story, ship_type_id).get("name", ship_type_id)
            stat_lines = [
                (f"Thrust: {self.ship.acceleration_magnitude:.2f}", (220, 220, 220)),
                (f"Max Velocity: {self.ship.max_velocity:.2f}", (220, 220, 220)),
                (f"Rotation: {self.ship.rotation_speed}", (220, 220, 220)),
                (f"Cargo: {self.possessions.cargo_quantity_total()}/{self.ship.cargo_capacity}", (220, 220, 220)),
            ]
            self._draw_section(surface, font_section, font_text, left_x, y, line_height, scale, f"Current Ship ({ship_name})", stat_lines)

        # Right column: cargo, personal items, installed and spare outfits.
        y = top_y
        cargo_lines = [(f"{get_commodity(self.story, cid).get('name', cid)} x{qty}", (200, 230, 200)) for cid, qty in self.possessions.cargo.items()]
        y = self._draw_section(surface, font_section, font_text, right_x, y, line_height, scale, "Cargo", cargo_lines)

        item_lines = [(f"{get_item(self.story, iid).get('name', iid)} x{qty}", (200, 230, 200)) for iid, qty in self.possessions.items.items()]
        y = self._draw_section(surface, font_section, font_text, right_x, y, line_height, scale, "Items", item_lines)

        installed_lines = [(f"{slot_id}: {get_ship_outfit(self.story, oid).get('name', oid)}", (220, 200, 255)) for slot_id, oid in self.possessions.installed_outfits.items()]
        y = self._draw_section(surface, font_section, font_text, right_x, y, line_height, scale, "Installed Outfits", installed_lines)

        spare_lines = [(get_ship_outfit(self.story, oid).get("name", oid), (220, 200, 255)) for oid in self.possessions.owned_outfits]
        self._draw_section(surface, font_section, font_text, right_x, y, line_height, scale, "Spare Outfits", spare_lines)

        # Top-left Controls pane - same spot/style as the base screen's own
        # (see LocationScreen.draw's draw_hud=False / SpaceScreen's), which
        # this menu is always shown on top of.
        margin = int(10 * scale)
        draw_controls_pane(surface, margin, margin, "Controls", [("P/ESC", "Close")], scale)
