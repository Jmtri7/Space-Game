"""`SaveBrowser` - the list of save files, in two modes:

- `mode="load"`: click a save to select it, then Load or Delete (or
  double-click to load).
- `mode="save"`: click an existing save then Overwrite, or **New Save** to
  type a name. A brand-new game with no saves opens straight in name-entry.

Mouse-only except for typing a save name. Save names are shown without the
`save_` prefix or `.json` suffix that live on disk (see `save_display_name`);
`self.list.items` still holds the real filenames, which is what the
`(action, payload)` tuple returns - action is `"load"` / `"save"` /
`"delete"` / `"cancel"` / `None`.
"""
import pygame
from datetime import datetime
from game.constants import WHITE, YELLOW, GRAY
from game.utils import get_ui_scale, get_ui_offset, get_font, _center_text_x, get_save_files, save_display_name
from game.ui.menu_base import MenuBase
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, modal_panel_rect
from game.ui.selectable_list import SelectableList

ACT_ACCENT = (150, 200, 255)
DELETE_ACCENT = (230, 160, 150)
NEUTRAL_ACCENT = (210, 210, 220)


class SaveBrowser(MenuBase):
    def __init__(self, mode, pilot_name=""):
        assert mode in ("load", "save")
        self.mode = mode
        self.pilot_name = pilot_name
        self.list = SelectableList(get_save_files(), max_visible=5)
        self.button_index = 0

        timestamp = datetime.now().strftime("%Y-%m-%d %H%M")
        self.save_name = f"{pilot_name} - {timestamp}" if pilot_name else timestamp
        self.input_mode = mode == "save" and not self.list.items
        # The pre-filled name is usable as-is (mouse-only: just click Save);
        # the first real keystroke clears it so the player types their own.
        self._name_pristine = True
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

    # --- buttons ----------------------------------------------------
    def buttons(self):
        if self.input_mode:
            return [("save", "Save", ACT_ACCENT, not self.save_name),
                    ("cancel", "Cancel", NEUTRAL_ACCENT, False)]
        has = bool(self.list.items)
        if self.mode == "load":
            return [("act", "Load", ACT_ACCENT, not has),
                    ("delete", "Delete", DELETE_ACCENT, not has),
                    ("cancel", "Cancel", NEUTRAL_ACCENT, False)]
        return [("act", "Overwrite", ACT_ACCENT, not has),
                ("new", "New Save", NEUTRAL_ACCENT, False),
                ("delete", "Delete", DELETE_ACCENT, not has),
                ("cancel", "Cancel", NEUTRAL_ACCENT, False)]

    def panel_rect(self, scale):
        return modal_panel_rect(scale, 0.2, 0.8, 0.6) if self.input_mode else modal_panel_rect(scale, 0.15, 0.8, 0.7)

    def button_bar_rects(self, scale):
        panel = self.panel_rect(scale)
        cy = panel.bottom - int(38 * scale)
        return self.button_row_rects(panel.centerx, cy, len(self.buttons()), scale, btn_w=132, gap=14,
                                     max_width=panel.width - int(32 * scale))

    # --- input ----------------------------------------------------
    def _enter_input_mode(self):
        self.input_mode = True
        self.button_index = 0
        self._name_pristine = True
        pygame.key.set_repeat(400, 40)

    def _press(self, button_id):
        if button_id == "act" and self.list.current():
            return (self.mode, self.list.current())
        if button_id == "delete" and self.list.current():
            return ("delete", self.list.current())
        if button_id == "cancel":
            pygame.key.set_repeat()
            return ("cancel", None)
        if button_id == "save" and self.save_name:
            pygame.key.set_repeat()
            return ("save", self.save_name)
        if button_id == "new":
            self._enter_input_mode()
        return None

    def handle_input(self, events):
        for event in events:
            # The keyboard is only ever used to type into the name field.
            if self.input_mode and event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                if self._name_pristine:
                    self.save_name = ""
                    self._name_pristine = False
                self.save_name = self.save_name[:-1]
            elif self.input_mode and event.type == pygame.TEXTINPUT:
                if self._name_pristine:
                    self.save_name = ""
                    self._name_pristine = False
                if len(self.save_name) < 30:
                    self.save_name += event.text
            elif event.type == pygame.MOUSEWHEEL and not self.input_mode:
                self.list.scroll(-event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1 and not self.input_mode:
                idx = self.list.index_at(event.pos)
                if idx is not None:
                    double = self._is_double_click(event.pos)
                    self.list.selected = idx
                    if double:
                        # Double-click a save = its primary verb (Load in
                        # load mode, Overwrite in save mode).
                        return (self.mode, self.list.current())
            pressed = self._press(self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale())))
            if pressed is not None:
                return pressed
        return (None, None)

    # --- rendering ------------------------------------------------
    def draw_content(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()
        panel_rect = self.panel_rect(scale)
        draw_glass_panel(surface, panel_rect, scale)

        if self.input_mode:
            font_title = get_font(int(32 * scale))
            font_text = get_font(int(24 * scale))
            draw_glow_title(surface, "Name this save:", font_title, panel_rect.centerx,
                            int(offset_y + 600 * scale * 0.25), color=WHITE, shadow_color=(30, 30, 30))
            input_box = font_text.render(self.save_name + "|", True, YELLOW)
            surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + 600 * scale * 0.42)))
            return

        title = "Load Game" if self.mode == "load" else "Select Save to Overwrite"
        font_title = get_font(int(36 * scale))
        font_text = get_font(int(22 * scale))
        draw_glow_title(surface, title, font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.2))
        if not self.list.items:
            no_saves = font_text.render("No saves found", True, GRAY)
            surface.blit(no_saves, (_center_text_x(surface, no_saves, offset_x), int(offset_y + 600 * scale * 0.5)))
        else:
            self.list.draw(surface, font_text, panel_rect.centerx, int(offset_y + 600 * scale * 0.32),
                           int(38 * scale), scale, label_fn=save_display_name)
