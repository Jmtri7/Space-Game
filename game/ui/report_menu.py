"""`ReportMenu` - a read-only, full-panel text report you open with a hotkey
and close with ESC or that same key. One or two columns of headed sections;
each section is a heading plus indented `(line, color)` rows.

Replaces `PossessionsMenu` (P - credits/ships/loans/cargo/outfits, two
columns) and `MissionLog` (N - mission stages with `[x]` / `->` markers, one
column). The content lives in the module-level builder functions
`possessions_report()` / `mission_report()`; `ReportMenu` is just the frame.
"""
import pygame
from game.constants import WHITE
from game.utils import (get_ui_scale, get_font, get_ship_type, get_ship_outfit,
                        get_commodity, get_item)
from game.ui.menu_base import MenuBase
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, modal_panel_rect
from game.world.mission import mission_status_lines

HEADING_COLOR = (200, 220, 255)
DIM = (150, 150, 150)


class ReportMenu(MenuBase):
    def __init__(self, title, columns, hotkey=None, hotkey_label=None):
        """`columns`: a list of 1 or 2 columns; each column is a list of
        `(heading, [(line, color), ...])` sections (a falsy heading draws no
        heading line). `hotkey`/`hotkey_label`: an extra key that closes the
        report and how to name it in the Controls pane (ESC always closes)."""
        self.title = title
        self.columns = columns
        self.hotkey = hotkey
        self.hotkey_label = hotkey_label

    def help_items(self):
        label = f"{self.hotkey_label}/ESC" if self.hotkey_label else "ESC"
        return [(label, "Close")]

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or (self.hotkey and event.key == self.hotkey):
                    return "close"
        return None

    def draw_content(self, surface):
        scale = get_ui_scale()
        panel_rect = modal_panel_rect(scale, 0.08, 0.84, 0.84)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_section = get_font(int(22 * scale))
        font_text = get_font(int(18 * scale))
        line_height = int(25 * scale)

        draw_glow_title(surface, self.title, font_title, panel_rect.centerx, panel_rect.y + int(24 * scale))

        top_y = panel_rect.y + int(80 * scale)
        xs = [panel_rect.x + int(30 * scale)]
        if len(self.columns) > 1:
            xs.append(panel_rect.centerx + int(20 * scale))

        for column, x in zip(self.columns, xs):
            y = top_y
            for heading, lines in column:
                if heading:
                    surface.blit(font_section.render(heading, True, HEADING_COLOR), (x, y))
                    y += line_height
                for line, color in lines:
                    surface.blit(font_text.render(line, True, color), (x + int(15 * scale), y))
                    y += line_height
                y += line_height // 2


def possessions_report(possessions, story="default", ship=None):
    """`(title, columns, hotkey, hotkey_label)` for a `ReportMenu` showing
    everything the player owns - moved out of the old `PossessionsMenu.draw`."""
    left = []
    left.append(("", [(f"Credits: {possessions.credits}", (255, 220, 100))]))

    ship_lines = [(get_ship_type(story, sid).get("name", sid), (220, 220, 220)) for sid in possessions.owned_ships]
    left.append(("Owned Ships", ship_lines or [("- None", DIM)]))

    loan_lines = [(f"{loan['lender']}: {loan['principal']}cr", (220, 180, 180)) for loan in possessions.loans]
    left.append(("Loans", loan_lines or [("- None", DIM)]))

    if ship and possessions.owned_ships:
        ship_name = get_ship_type(story, possessions.owned_ships[-1]).get("name", possessions.owned_ships[-1])
        left.append((f"Current Ship ({ship_name})", [
            (f"Thrust: {ship.acceleration_magnitude:.2f}", (220, 220, 220)),
            (f"Max Velocity: {ship.max_velocity:.2f}", (220, 220, 220)),
            (f"Rotation: {ship.rotation_speed}", (220, 220, 220)),
            (f"Cargo: {possessions.cargo_quantity_total()}/{ship.cargo_capacity}", (220, 220, 220)),
        ]))

    right = []
    cargo_lines = [(f"{get_commodity(story, cid).get('name', cid)} x{qty}", (200, 230, 200)) for cid, qty in possessions.cargo.items()]
    right.append(("Cargo", cargo_lines or [("- None", DIM)]))

    item_lines = [(f"{get_item(story, iid).get('name', iid)} x{qty}", (200, 230, 200)) for iid, qty in possessions.items.items()]
    right.append(("Items", item_lines or [("- None", DIM)]))

    installed_lines = [(f"{slot_id}: {get_ship_outfit(story, oid).get('name', oid)}", (220, 200, 255)) for slot_id, oid in possessions.installed_outfits.items()]
    right.append(("Installed Outfits", installed_lines or [("- None", DIM)]))

    spare_lines = [(get_ship_outfit(story, oid).get("name", oid), (220, 200, 255)) for oid in possessions.owned_outfits]
    right.append(("Spare Outfits", spare_lines or [("- None", DIM)]))

    return "Possessions", [left, right], pygame.K_p, "P"


def mission_report(missions_config, possessions):
    """`(title, columns, hotkey, hotkey_label)` for a `ReportMenu` of mission
    progress - moved out of the old `MissionLog.draw` (markers and all)."""
    entries = mission_status_lines(missions_config, possessions)
    sections = []
    if not entries:
        sections.append(("", [("No missions yet.", DIM)]))
    for title, stage_texts, current_index in entries:
        lines = []
        for i, text in enumerate(stage_texts):
            if current_index is None or i < current_index:
                marker, color = "[x]", (150, 200, 150)
            elif i == current_index:
                marker, color = "->", (255, 255, 150)
            else:
                break
            lines.append((f"{marker} {text}", color))
        sections.append((title, lines))
    return "Mission Log", [sections], pygame.K_n, "N"
