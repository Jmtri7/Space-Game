"""Dialog for saving games with name input and overwrite selection."""
import pygame
from datetime import datetime
from constants import WHITE, YELLOW, GRAY
from utils import get_ui_scale, get_ui_offset, get_font, _center_text_x, get_save_files
from ui_theme import draw_glass_panel, draw_glow_title
from selectable_list import SelectableList


class SaveDialog:
    """Dialog for saving games with name input and overwrite selection."""
    def __init__(self, pilot_name=""):
        self.pilot_name = pilot_name
        # Pre-populate with default save name
        timestamp = datetime.now().strftime("%Y-%m-%d %H%M")
        self.save_name = f"{pilot_name} - {timestamp}" if pilot_name else timestamp
        self.success_timer = 0
        self.list = SelectableList(self._get_all_saves(), max_visible=5)
        self.input_mode = not self.list.items

    def _get_all_saves(self):
        return get_save_files()

    # Kept for external callers (main.py) that refresh the save list after a delete.
    @property
    def existing_saves(self):
        return self.list.items

    @existing_saves.setter
    def existing_saves(self, value):
        self.list.items = value

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.input_mode:
                    if event.key == pygame.K_RETURN and self.save_name:
                        self.success_timer = 120
                        return ("save", self.save_name)
                    elif event.key == pygame.K_BACKSPACE:
                        self.save_name = self.save_name[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        return ("cancel", None)
                else:
                    if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                        self.list.handle_key(event.key)
                    elif event.key == pygame.K_RETURN and self.list.current():
                        return ("save", self.list.current())
                    elif event.key == pygame.K_d and self.list.current():
                        return ("delete", self.list.current())
                    elif event.key == pygame.K_ESCAPE:
                        return ("cancel", None)
                    elif event.key == pygame.K_n:
                        self.input_mode = True
                        # Keep the pre-populated save name (don't clear it)
            elif event.type == pygame.TEXTINPUT:
                if self.input_mode and len(self.save_name) < 30:
                    self.save_name += event.text
        return (None, None)

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        if self.input_mode:
            panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.1), int(offset_y + 600 * scale * 0.2), int(800 * scale * 0.8), int(600 * scale * 0.6))
            draw_glass_panel(surface, panel_rect, scale)
            font_title = get_font(int(32 * scale))
            font_text = get_font(int(24 * scale))

            draw_glow_title(surface, "Save Name:", font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.25), color=WHITE, shadow_color=(30, 30, 30))

            # Show full filename with save_ prefix and .json extension
            full_filename = f"save_{self.save_name}.json"
            input_box = font_text.render(full_filename, True, YELLOW)
            surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + 600 * scale * 0.4)))

            help_text = font_text.render("Enter to save, ESC to cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.6)))
        else:
            panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.1), int(offset_y + 600 * scale * 0.15), int(800 * scale * 0.8), int(600 * scale * 0.7))
            draw_glass_panel(surface, panel_rect, scale)
            font_title = get_font(int(32 * scale))
            font_text = get_font(int(20 * scale))

            draw_glow_title(surface, "Select Save to Overwrite", font_title, panel_rect.centerx, int(offset_y + 600 * scale * 0.2))

            self.list.draw(surface, font_text, panel_rect.centerx, int(offset_y + 600 * scale * 0.35), int(35 * scale), scale)

            help_text = font_text.render("Enter: overwrite, N: new save, D: delete, ESC: cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.75)))
