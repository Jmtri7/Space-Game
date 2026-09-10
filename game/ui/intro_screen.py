"""The post-story-selection intro screen.

Shown by main.py between the pilot-name dialog and the first playable screen,
for any story whose story.json carries an `"intro"` block
(`{"title": ..., "body": [paragraph, ...]}`). Mirrors EndingScreen: a
`ReportMenu` - the same full-panel scrolling text frame - with one **Begin**
button instead of Close. `intro_report()` pulls the paragraphs from the story
and substitutes `{pilot}` with the name the player just entered, so the
opening addresses them directly.
"""
import pygame

from game.constants import WHITE
from game.ui.report_menu import ReportMenu, SCROLL_HINT_COLOR
from game.utils import get_story, get_ui_scale, get_font
from game.ui.ui_theme import draw_glass_panel, draw_glow_title

BODY_COLOR = (215, 215, 215)


def has_intro(story):
    """True when this story defines an `"intro"` block with at least one
    paragraph - main.py only routes through IntroScreen when it does."""
    intro = get_story(story).get("intro", {})
    body = intro.get("body", [])
    if isinstance(body, str):
        body = [body]
    return bool(body)


def intro_report(story, pilot_name):
    """`(title, columns)` for a one-column `ReportMenu` - the story's intro
    title and paragraphs, with `{pilot}` filled in."""
    intro = get_story(story).get("intro", {})
    title = intro.get("title", get_story(story).get("name", "A New Game"))
    body = intro.get("body", [])
    if isinstance(body, str):
        body = [body]
    paras = [(para.replace("{pilot}", pilot_name or "pilot"), BODY_COLOR)
             for para in body]
    return title, [[("", paras)]]


class IntroScreen(ReportMenu):
    """A `ReportMenu` whose only action starts the game. Unlike the base
    report frame (Close top-right), the **Begin** button sits bottom-centre
    and the scroll hints are centred just inside the top/bottom margins, with
    the body text inset to leave room for them."""

    def buttons(self):
        return [("begin", "Begin", WHITE, False)]

    def button_bar_rects(self, scale):
        panel = self.panel_rect(scale)
        cy = panel.bottom - int(38 * scale)
        return self.button_row_rects(panel.centerx, cy, 1, scale,
                                     max_width=panel.width - int(32 * scale))

    def draw_content(self, surface):
        scale = get_ui_scale()
        panel_rect = self.panel_rect(scale)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_section = get_font(int(22 * scale))
        font_text = get_font(int(18 * scale))
        line_height = int(25 * scale)

        draw_glow_title(surface, self.title, font_title,
                        panel_rect.centerx, panel_rect.y + int(24 * scale))

        # Fixed gutters: one text line under the title for the "^ more" hint,
        # and above the bottom for the "v more" hint sitting just over the
        # Begin button. The body is laid out between them so a hint never
        # overdraws a line.
        hint_h = line_height
        btn_top = self.button_bar_rects(scale)[0].top
        top_base = panel_rect.y + int(80 * scale)
        top_y = top_base + hint_h
        bottom_y = btn_top - int(12 * scale) - hint_h

        x = panel_rect.x + int(30 * scale)
        col_wrap = panel_rect.right - int(30 * scale) - x

        visible = max(1, (bottom_y - top_y) // line_height)
        rows = self._flatten(self._active_columns()[0], font_text,
                             col_wrap - int(32 * scale))
        self._max_scroll = max(0, len(rows) - visible)
        self.scroll = max(0, min(self.scroll, self._max_scroll))

        y = top_y
        for text, color, indent, is_heading in rows[self.scroll:self.scroll + visible]:
            if text:
                font = font_section if is_heading else font_text
                surface.blit(font.render(text, True, color), (x + int(indent * scale), y))
            y += line_height

        self._scroll_up_rect = self._scroll_down_rect = None
        if self._max_scroll > 0:
            if self.scroll > 0:
                img = font_text.render("^ more  (scroll or click)", True, SCROLL_HINT_COLOR)
                pos = (panel_rect.centerx - img.get_width() // 2, top_base)
                surface.blit(img, pos)
                self._scroll_up_rect = pygame.Rect(pos[0], pos[1], img.get_width(), img.get_height())
            if self.scroll < self._max_scroll:
                img = font_text.render("v more  (scroll or click)", True, SCROLL_HINT_COLOR)
                pos = (panel_rect.centerx - img.get_width() // 2, bottom_y + int(4 * scale))
                surface.blit(img, pos)
                self._scroll_down_rect = pygame.Rect(pos[0], pos[1], img.get_width(), img.get_height())
