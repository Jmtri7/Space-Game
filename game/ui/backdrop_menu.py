"""`BackdropMenu` - a top-level list screen over the animated `MenuBackdrop`:
a title, then a centred column of **buttons** you click, each optionally with
a wrapped description line under it. A click returns the row's value. When
`allow_cancel` is set, a **Back** button is appended that returns `"cancel"`.
Mouse-only.

Replaces the old `Menu` (main menu: NEW / LOAD / QUIT) and `StorySelector`
(pick a campaign, each with a blurb).
"""
import pygame
import game.utils as utils
from game.constants import GRAY
from game.utils import get_font, _wrap_text
from game.ui.menu_base import MenuBase
from game.ui.menu_backdrop import MenuBackdrop
from game.ui.ui_theme import draw_glass_panel, draw_glow_title

ROW_ACCENT = (180, 205, 235)
BACK_ACCENT = (210, 210, 220)


class BackdropMenu(MenuBase):
    def __init__(self, title, rows, seed=None, allow_cancel=False):
        """`rows`: `[(value, label, description_or_None), ...]`."""
        self.title = title
        self.rows = list(rows)
        self.allow_cancel = allow_cancel
        self.button_index = 0
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
        rows_total = sum(_row_heights(m))
        panel_height = m["title_area"] + rows_total + bottom_pad

        # Long lists (Video Settings on a big display) can overrun the screen -
        # BackdropMenu doesn't scroll, so shrink the rows region to fit. Short
        # menus (main menu, story picker) never reach this.
        avail = utils.screen_height - 2 * m["panel_top"]
        if panel_height > avail and rows_total > 0:
            shrink = max(0.4, (avail - m["title_area"] - bottom_pad) / rows_total)
            m = dict(m, btn_height=max(1, int(m["btn_height"] * shrink)),
                     row_gap=int(m["row_gap"] * shrink),
                     desc_line_height=max(1, int(m["desc_line_height"] * shrink)))
            panel_height = m["title_area"] + sum(_row_heights(m)) + bottom_pad

        panel = pygame.Rect(0, 0, m["panel_width"], panel_height)
        panel.centerx = utils.screen_width // 2
        panel.top = m["panel_top"]

        btn_rects = []
        y = panel.top + m["title_area"]
        for v, _l, _d in all_rows:
            btn_rects.append(pygame.Rect(panel.centerx - m["box_width"] // 2, y, m["box_width"], m["btn_height"]))
            y += m["btn_height"] + len(desc_lines[v]) * m["desc_line_height"] + m["row_gap"]
        return m, desc_lines, panel, btn_rects

    def panel_rect(self, scale):
        return self._panel_and_rows()[2]

    def button_bar_rects(self, scale):
        return self._panel_and_rows()[3]

    # --- input -------------------------------------------------------
    def handle_input(self, events):
        for event in events:
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

        font_desc = get_font(int(20 * scale))
        for (value, _label, _desc), rect in zip(self._all_rows(), btn_rects):
            desc_y = rect.bottom + m["desc_line_height"] // 2
            for line in desc_lines[value]:
                dt = font_desc.render(line, True, GRAY)
                surface.blit(dt, dt.get_rect(center=(panel.centerx, desc_y)))
                desc_y += m["desc_line_height"]
        # The row buttons themselves are drawn by MenuBase.draw via button_bar_rects().
