"""Dialog for saving games with name input and overwrite selection."""
import math
import pygame
from datetime import datetime
from constants import WHITE, YELLOW, GRAY
from utils import (
    get_ui_scale, get_ui_offset, get_font, _center_text_x, _handle_scrolling_input,
    get_save_files
)
from ui_theme import draw_glass_panel, draw_glow_title, draw_selection_highlight


class SaveDialog:
    """Dialog for saving games with name input and overwrite selection."""
    def __init__(self, pilot_name=""):
        self.pilot_name = pilot_name
        # Pre-populate with default save name
        timestamp = datetime.now().strftime("%Y-%m-%d %H%M")
        self.save_name = f"{pilot_name} - {timestamp}" if pilot_name else timestamp
        self.success_timer = 0
        self.existing_saves = self._get_all_saves()
        self.selected_existing = 0 if self.existing_saves else None
        self.input_mode = not self.existing_saves
        self.scroll_offset = 0
        self.max_visible = 5

    def _get_all_saves(self):
        return get_save_files()

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
                        if self.selected_existing is not None:
                            self.selected_existing, self.scroll_offset = _handle_scrolling_input(
                                event.key, self.selected_existing, self.existing_saves,
                                self.scroll_offset, self.max_visible)
                    elif event.key == pygame.K_RETURN and self.selected_existing is not None:
                        return ("save", self.existing_saves[self.selected_existing])
                    elif event.key == pygame.K_d and self.selected_existing is not None:
                        return ("delete", self.existing_saves[self.selected_existing])
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

            if self.scroll_offset > 0:
                up_indicator = font_text.render("↑ more", True, GRAY)
                surface.blit(up_indicator, (int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.33)))

            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)
            visible_saves = self.existing_saves[self.scroll_offset:self.scroll_offset + self.max_visible]
            for i, save in enumerate(visible_saves):
                is_selected = (self.scroll_offset + i == self.selected_existing)
                color = YELLOW if is_selected else GRAY
                text = font_text.render(save, True, color)
                text_x = _center_text_x(surface, text, offset_x)
                text_y = int(offset_y + 600 * scale * 0.35 + i * 35)
                if is_selected:
                    box_rect = pygame.Rect(text_x - 10, text_y - 4, text.get_width() + 20, text.get_height() + 8)
                    draw_selection_highlight(surface, box_rect, scale, pulse)
                surface.blit(text, (text_x, text_y))

            if self.scroll_offset + self.max_visible < len(self.existing_saves):
                down_indicator = font_text.render("↓ more", True, GRAY)
                surface.blit(down_indicator, (int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.35 + self.max_visible * 35)))

            help_text = font_text.render("Enter: overwrite, N: new save, D: delete, ESC: cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.75)))
