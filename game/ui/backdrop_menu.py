"""`BackdropMenu` - a top-level list screen over the animated `MenuBackdrop`:
a title, an optional row of **tab** buttons, then a centred column of
**buttons** you click, each optionally with a wrapped description line under
it. A click returns the row's value. A tab click returns `"tab:<label>"`.
When `allow_cancel` is set, a **Back** button is appended that returns
`"cancel"`. Mouse-only.

Replaces the old `Menu` (main menu: NEW / LOAD / QUIT) and `StorySelector`
(pick a campaign, each with a blurb).
"""
import pygame
import game.utils as utils
from game.constants import GRAY
from game.utils import get_font, _wrap_text
from game.ui.menu_base import MenuBase
from game.ui.menu_backdrop import MenuBackdrop
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_button

ROW_ACCENT = (180, 205, 235)
BACK_ACCENT = (210, 210, 220)
TAB_ACCENT = (170, 220, 210)


class BackdropMenu(MenuBase):
    def __init__(self, title, rows, seed=None, allow_cancel=False, tabs=None):
        """`rows`: `[(value, label, description_or_None), ...]`.

        `tabs`: `(active_label, [label, ...])` to draw a tab strip under the
        title - clicking a tab returns `"tab:<label>"`; the caller rebuilds
        the menu for the new tab. `None` for no tabs."""
        self.title = title
        self.rows = list(rows)
        self.allow_cancel = allow_cancel
        self.tabs = tabs
        self.button_index = 0
        self.tab_index = 0
        self.backdrop = MenuBackdrop(seed=seed) if seed is not None else MenuBackdrop()

    def _all_rows(self):
        rows = [(v, l, d) for v, l, d in self.rows]
        if self.allow_cancel:
            rows.append(("cancel", "Back", None))
        return rows

    def buttons(self):
        return [(value, label, BACK_ACCENT if value == "cancel" else ROW_ACCENT, False)
                for value, label, _desc in self._all_rows()]

    # --- layout -------------------------------------------------------
    def _metrics(self):
        scale = min(utils.screen_width, utils.screen_height) / 600.0
        return {
            "scale": scale,
            "panel_width": int(560 * scale),
            "panel_top": int(20 * scale),
            "title_area": int(96 * scale),
            "tab_area": int(48 * scale) if self.tabs else 0,
            "btn_height": int(46 * scale),
            "desc_line_height": int(22 * scale),
            "row_gap": int(16 * scale),
            "box_width": int(520 * scale),
        }

    def _desc_lines(self, m):
        font_desc = get_font(int(20 * m["scale"]))
        return {v: (_wrap_text(font_desc, d, m["box_width"] - int(20 * m["scale"])) if d else [])
                for v, _l, d in self._all_rows()}

    def _panel_and_rows(self):
        m = self._metrics()
        desc_lines = self._desc_lines(m)
        all_rows = self._all_rows()

        def _row_heights(mm):
            return [mm["btn_height"] + len(desc_lines[v]) * mm["desc_line_height"] + mm["row_gap"]
                    for v, _l, _d in all_rows]

        bottom_pad = int(28 * m["scale"])
        head = m["title_area"] + m["tab_area"]
        rows_total = sum(_row_heights(m))
        panel_height = head + rows_total + bottom_pad

        # Long lists (Video Settings on a big display) can overrun the screen -
        # BackdropMenu doesn't scroll, so shrink the rows region to fit. Short
        # menus (main menu, story picker) never reach this.
        avail = utils.screen_height - 2 * m["panel_top"]
        if panel_height > avail and rows_total > 0:
            shrink = max(0.4, (avail - head - bottom_pad) / rows_total)
            m = dict(m, btn_height=max(1, int(m["btn_height"] * shrink)),
                     row_gap=int(m["row_gap"] * shrink),
                     desc_line_height=max(1, int(m["desc_line_height"] * shrink)))
            panel_height = head + sum(_row_heights(m)) + bottom_pad

        panel = pygame.Rect(0, 0, m["panel_width"], panel_height)
        panel.centerx = utils.screen_width // 2
        panel.top = m["panel_top"]

        btn_rects = []
        y = panel.top + head
        for v, _l, _d in all_rows:
            btn_rects.append(pygame.Rect(panel.centerx - m["box_width"] // 2, y, m["box_width"], m["btn_height"]))
            y += m["btn_height"] + len(desc_lines[v]) * m["desc_line_height"] + m["row_gap"]
        return m, desc_lines, panel, btn_rects

    def panel_rect(self, scale):
        return self._panel_and_rows()[2]

    def button_bar_rects(self, scale):
        return self._panel_and_rows()[3]

    def _tab_rects(self):
        """Centred row of tab buttons, sitting in the reserved `tab_area`
        band between the title and the first row. `[]` when there are no tabs."""
        if not self.tabs:
            return []
        m, _desc, panel, _btns = self._panel_and_rows()
        _active, labels = self.tabs
        cy = panel.top + m["title_area"] + m["tab_area"] // 2
        return self.button_row_rects(panel.centerx, cy, len(labels), m["scale"],
                                     btn_w=150, btn_h=34, gap=10,
                                     max_width=m["box_width"])

    # --- input -------------------------------------------------------
    def handle_input(self, events):
        for event in events:
            if self.tabs and event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                _active, labels = self.tabs
                for i, rect in enumerate(self._tab_rects()):
                    if rect.collidepoint(event.pos):
                        self.tab_index = i
                        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
                            return self._button_pressed(f"tab:{labels[i]}")
            pressed = self.handle_button_event(event, lambda: self._panel_and_rows()[3])
            if pressed is not None:
                return pressed
        return None

    # --- rendering --------------------------------------------------
    def draw_content(self, surface):
        self.backdrop.draw(surface)
        m, desc_lines, panel, btn_rects = self._panel_and_rows()
        scale = m["scale"]
        draw_glass_panel(surface, panel, scale)
        draw_glow_title(surface, self.title, get_font(int(50 * scale)), panel.centerx, panel.top + int(18 * scale))

        if self.tabs:
            active, labels = self.tabs
            tab_font = get_font(int(18 * scale))
            for i, (label, rect) in enumerate(zip(labels, self._tab_rects())):
                draw_button(surface, rect, label, tab_font, scale,
                            selected=(label == active or i == self.tab_index),
                            accent=TAB_ACCENT)

        font_desc = get_font(int(20 * scale))
        for (value, _label, _desc), rect in zip(self._all_rows(), btn_rects):
            desc_y = rect.bottom + m["desc_line_height"] // 2
            for line in desc_lines[value]:
                dt = font_desc.render(line, True, GRAY)
                surface.blit(dt, dt.get_rect(center=(panel.centerx, desc_y)))
                desc_y += m["desc_line_height"]
        # The row buttons themselves are drawn by MenuBase.draw via button_bar_rects().
