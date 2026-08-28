"""`ReportMenu` - a read-only, full-panel text report. Mouse-only: the
top-right **Close** button closes it. One or two columns of headed sections;
each section is a heading plus indented `(line, color)` rows.

Long reports **scroll** - the panel height is fixed, so content past it is
reached with the mouse wheel or by clicking the `▲ more` / `▼ more`
indicators. A report can also be **tabbed** (`tabs=[(label, columns), ...]`):
the mission log uses this to split Active from Completed missions, switched
by clicking a tab.

Replaces `PossessionsMenu` (credits/ships/loans/cargo/outfits, two columns)
and `MissionLog` (numbered mission stages with `[x]` / `->` markers, one
column, Active/Completed tabs). The content lives in the module-level builder
functions `possessions_report()` / `mission_report()`; `ReportMenu` is just
the frame.
"""
import pygame
from game.constants import WHITE, GRAY
from game.utils import (get_ui_scale, get_font, get_ship_type, get_ship_outfit,
                        get_commodity, get_item, _wrap_text)
from game.ui.menu_base import MenuBase
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, modal_panel_rect
from game.world.mission import mission_status_lines

HEADING_COLOR = (200, 220, 255)
DIM = (150, 150, 150)
SCROLL_HINT_COLOR = (120, 200, 255)
TAB_ACTIVE = (255, 255, 150)
TAB_INACTIVE = (150, 160, 180)


class ReportMenu(MenuBase):
    def __init__(self, title, columns, tabs=None):
        """`columns`: a list of 1 or 2 columns; each column is a list of
        `(heading, [(line, color), ...])` sections (a falsy heading draws no
        heading line). `tabs`: optional `[(tab_label, columns), ...]` - when
        given, `columns` is ignored and the active tab's columns are shown
        with a tab bar. Mouse-only: click the Close button, click a tab,
        wheel or click the arrows to scroll."""
        self.title = title
        self.columns = columns
        self.tabs = tabs
        self.tab_index = 0
        self.button_index = 0
        self.scroll = 0
        self._max_scroll = 0
        self._scroll_up_rect = None
        self._scroll_down_rect = None

    # --- content selection -------------------------------------------
    def _active_columns(self):
        return self.tabs[self.tab_index][1] if self.tabs else self.columns

    def _select_tab(self, index):
        if self.tabs:
            self.tab_index = index % len(self.tabs)
            self.scroll = 0

    # --- frame -------------------------------------------------------
    def buttons(self):
        return [("close", "Close", WHITE, False)]

    def panel_rect(self, scale):
        return modal_panel_rect(scale, 0.08, 0.84, 0.84)

    def button_bar_rects(self, scale):
        panel = self.panel_rect(scale)
        w, h, m = int(140 * scale), int(38 * scale), int(16 * scale)
        return [pygame.Rect(panel.right - w - m, panel.y + m, w, h)]

    def _tab_bar_rects(self, scale):
        """Rect per tab label, laid out as a left-aligned row just under the
        title - shared by draw (highlight) and input (click)."""
        if not self.tabs:
            return []
        panel = self.panel_rect(scale)
        font = get_font(int(20 * scale))
        x = panel.x + int(30 * scale)
        y = panel.y + int(66 * scale)
        gap = int(22 * scale)
        pad = int(10 * scale)
        rects = []
        for label, _cols in self.tabs:
            tw = font.size(label)[0]
            rects.append(pygame.Rect(x, y, tw + pad * 2, int(30 * scale)))
            x += tw + pad * 2 + gap
        return rects

    # --- input -----------------------------------------------------
    def handle_input(self, events):
        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                self.scroll = max(0, min(self._max_scroll, self.scroll - event.y))
            elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
                if self._scroll_up_rect and self._scroll_up_rect.collidepoint(event.pos):
                    self.scroll = max(0, self.scroll - 6)
                elif self._scroll_down_rect and self._scroll_down_rect.collidepoint(event.pos):
                    self.scroll = min(self._max_scroll, self.scroll + 6)
                elif self.tabs:
                    for i, rect in enumerate(self._tab_bar_rects(get_ui_scale())):
                        if rect.collidepoint(event.pos):
                            self._select_tab(i)
            if self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale())) == "close":
                return "close"
        return None

    # --- rendering ------------------------------------------------
    def _flatten(self, column, font_text, wrap_width):
        """One column's sections -> a flat list of
        `(text, color, indent, is_heading)` rows, long lines word-wrapped and
        a blank spacer row between sections."""
        rows = []
        for heading, lines in column:
            if heading:
                rows.append((heading, HEADING_COLOR, 0, True))
            for line, color in lines:
                wrapped = _wrap_text(font_text, line, wrap_width) or [""]
                for j, wl in enumerate(wrapped):
                    rows.append((wl, color, 15 if j == 0 else 32, False))
            rows.append(("", None, 0, False))
        return rows

    def draw_content(self, surface):
        scale = get_ui_scale()
        panel_rect = self.panel_rect(scale)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_tab = get_font(int(20 * scale))
        font_section = get_font(int(22 * scale))
        font_text = get_font(int(18 * scale))
        line_height = int(25 * scale)

        draw_glow_title(surface, self.title, font_title, panel_rect.centerx, panel_rect.y + int(24 * scale))

        top_y = panel_rect.y + int(80 * scale)
        if self.tabs:
            for i, (rect, (label, _cols)) in enumerate(zip(self._tab_bar_rects(scale), self.tabs)):
                active = i == self.tab_index
                if active:
                    pygame.draw.rect(surface, (60, 70, 100), rect, border_radius=int(6 * scale))
                surface.blit(font_tab.render(label, True, TAB_ACTIVE if active else TAB_INACTIVE),
                             (rect.x + int(10 * scale), rect.y + int(3 * scale)))
            top_y = panel_rect.y + int(112 * scale)

        columns = self._active_columns()
        xs = [panel_rect.x + int(30 * scale)]
        if len(columns) > 1:
            xs.append(panel_rect.centerx + int(20 * scale))
            col_wrap = panel_rect.centerx - int(20 * scale) - xs[0]
        else:
            col_wrap = panel_rect.right - int(30 * scale) - xs[0]

        bottom_y = panel_rect.bottom - int(30 * scale)
        visible = max(1, (bottom_y - top_y) // line_height)

        cols_rows = [self._flatten(col, font_text, col_wrap - int(32 * scale)) for col in columns]
        total = max((len(r) for r in cols_rows), default=0)
        self._max_scroll = max(0, total - visible)
        self.scroll = max(0, min(self.scroll, self._max_scroll))

        for rows, x in zip(cols_rows, xs):
            y = top_y
            for text, color, indent, is_heading in rows[self.scroll:self.scroll + visible]:
                if text:
                    font = font_section if is_heading else font_text
                    surface.blit(font.render(text, True, color), (x + int(indent * scale), y))
                y += line_height

        self._scroll_up_rect = self._scroll_down_rect = None
        if self._max_scroll > 0:
            arrow_x = panel_rect.right - int(170 * scale)
            if self.scroll > 0:
                up = font_text.render("^ more  (scroll or click)", True, SCROLL_HINT_COLOR)
                pos = (arrow_x, top_y - int(2 * scale))
                surface.blit(up, pos)
                self._scroll_up_rect = pygame.Rect(pos[0], pos[1], up.get_width(), up.get_height())
            if self.scroll < self._max_scroll:
                down = font_text.render("v more  (scroll or click)", True, SCROLL_HINT_COLOR)
                pos = (arrow_x, bottom_y - int(2 * scale))
                surface.blit(down, pos)
                self._scroll_down_rect = pygame.Rect(pos[0], pos[1], down.get_width(), down.get_height())


def possessions_report(possessions, story="default", ship=None):
    """`(title, columns)` for a `ReportMenu` showing everything the player
    owns - moved out of the old `PossessionsMenu.draw`."""
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

    return "Possessions", [left, right]


def _mission_sections(entries, completed):
    """`(title, stage_texts, current_index)` entries -> `ReportMenu` sections,
    with stages numbered (`1.`, `2.`, ...) and marked `[x]` done / `->`
    current. `completed` picks which side: active missions (an int current
    index) or finished ones (`current_index is None`)."""
    sections = []
    for title, stage_texts, current_index in entries:
        if completed != (current_index is None):
            continue
        title = title.replace(" (Complete)", "")
        lines = []
        for i, text in enumerate(stage_texts):
            if current_index is None or i < current_index:
                marker, color = "[x]", (150, 200, 150)
            elif i == current_index:
                marker, color = "->", (255, 255, 150)
            else:
                break  # don't reveal steps the player hasn't reached yet
            lines.append((f"{marker} {i + 1}. {text}", color))
        sections.append((title, lines))
    return sections


def mission_report(missions_config, possessions):
    """`(title, columns, tabs)` for a tabbed `ReportMenu` of mission
    progress - Active and Completed missions on separate tabs, each stage
    numbered and marked (moved out of the old `MissionLog.draw`)."""
    entries = mission_status_lines(missions_config, possessions)
    active = _mission_sections(entries, completed=False) or [("", [("No active missions.", DIM)])]
    done = _mission_sections(entries, completed=True) or [("", [("No completed missions yet.", DIM)])]
    tabs = [("Active", [active]), ("Completed", [done])]
    return "Mission Log", [active], tabs
