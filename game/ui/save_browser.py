"""`SaveBrowser` - the scrollable list of save files, in two modes:

- `mode="load"`: pick a save to load, or delete one.
- `mode="save"`: either type a new save name (input submode) or pick an
  existing save to overwrite; `N` switches from the list to input.

Replaces `LoadMenu` and `SaveDialog` - both were a `SelectableList` over
`get_save_files()` with slightly different verbs. `handle_input` returns
`(action, payload)` where action is `"load"` / `"save"` / `"delete"` /
`"cancel"` / `None`.
"""
import pygame
from datetime import datetime
from game.constants import WHITE, YELLOW, GRAY
from game.utils import get_ui_scale, get_ui_offset, get_font, _center_text_x, get_save_files
from game.ui.menu_base import MenuBase
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, modal_panel_rect
from game.ui.selectable_list import SelectableList


class SaveBrowser(MenuBase):
    def __init__(self, mode, pilot_name=""):
        assert mode in ("load", "save")
        self.mode = mode
        self.pilot_name = pilot_name
        self.list = SelectableList(get_save_files(), max_visible=5)

        timestamp = datetime.now().strftime("%Y-%m-%d %H%M")
        self.save_name = f"{pilot_name} - {timestamp}" if pilot_name else timestamp
        # Start straight in text-entry when saving with nothing to overwrite.
        self.input_mode = mode == "save" and not self.list.items
        self._suppress_next_text = False
        if self.input_mode:
            pygame.key.set_repeat(400, 40)

    # Kept for main.py, which refreshes the list after a delete.
    def _get_all_saves(self):
        return get_save_files()

    @property
    def existing_saves(self):
        return self.list.items

    @existing_saves.setter
    def existing_saves(self, value):
        self.list.items = value

    def help_items(self):
        if self.input_mode:
            return [("Enter", "Save"), ("ESC", "Cancel")]
        if not self.list.items:
            return [("ESC", "Cancel")]
        if self.mode == "load":
            return [("Enter", "Load"), ("D", "Delete"), ("ESC", "Cancel")]
        return [("Enter", "Overwrite"), ("N", "New save"), ("D", "Delete"), ("ESC", "Cancel")]

    # --- input --------------------------------------------------------
    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                result = self._handle_key(event)
                if result is not None:
                    return result
            elif event.type == pygame.TEXTINPUT and self.input_mode:
                if self._suppress_next_text:
                    self._suppress_next_text = False
                elif len(self.save_name) < 30:
                    self.save_name += event.text
        return (None, None)

    def _handle_key(self, event):
        if self.input_mode:
            if event.key == pygame.K_RETURN and self.save_name:
                pygame.key.set_repeat()
                return ("save", self.save_name)
            if event.key == pygame.K_BACKSPACE:
                self.save_name = self.save_name[:-1]
            elif event.key == pygame.K_ESCAPE:
                pygame.key.set_repeat()
                return ("cancel", None)
            return None

        if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            self.list.handle_key(event.key)
        elif event.key == pygame.K_RETURN and self.list.current():
            return (self.mode, self.list.current())  # "load" or "save" (overwrite)
        elif event.key == pygame.K_d and self.list.current():
            return ("delete", self.list.current())
        elif event.key == pygame.K_ESCAPE:
            return ("cancel", None)
        elif event.key == pygame.K_n and self.mode == "save":
            self.input_mode = True
            self._suppress_next_text = True  # pygame also emits TEXTINPUT("n")
            pygame.key.set_repeat(400, 40)
        return None

    # --- rendering ----------------------------------------------------
    def draw_content(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        if self.input_mode:
            panel_rect = modal_panel_rect(scale, 0.2, 0.8, 0.6)
            draw_glass_panel(surface, panel_rect, scale)
            font_title = get_font(int(32 * scale))
            font_text = get_font(int(24 * scale))
            draw_glow_title(surface, "Save Name:", font_title, panel_rect.centerx,
                            int(offset_y + 600 * scale * 0.25), color=WHITE, shadow_color=(30, 30, 30))
            full_filename = f"save_{self.save_name}.json"
            input_box = font_text.render(full_filename, True, YELLOW)
            surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + 600 * scale * 0.4)))
            return

        title = "Load Game" if self.mode == "load" else "Select Save to Overwrite"
        panel_rect = modal_panel_rect(scale, 0.15, 0.8, 0.7)
        draw_glass_panel(surface, panel_rect, scale)
        font_title = get_font(int(36 * scale))
        font_text = get_font(int(22 * scale))
        draw_glow_title(surface, title, font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.2))

        if not self.list.items:
            no_saves = font_text.render("No saves found", True, GRAY)
            surface.blit(no_saves, (_center_text_x(surface, no_saves, offset_x), int(offset_y + 600 * scale * 0.5)))
        else:
            self.list.draw(surface, font_text, panel_rect.centerx, int(offset_y + 600 * scale * 0.35), int(38 * scale), scale)
