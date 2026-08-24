"""Dialog for saving games with name input and overwrite selection."""
import pygame
from datetime import datetime
from constants import WHITE, YELLOW, GRAY
from utils import (
    get_ui_scale, get_ui_offset, get_font, _center_text_x, _handle_scrolling_input,
    get_save_files, draw_dialog_box
)


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
            draw_dialog_box(surface, offset_x + 800 * scale * 0.1, offset_y + 600 * scale * 0.2, 800 * scale * 0.8, 600 * scale * 0.6)
            font_title = get_font(int(32 * scale))
            font_text = get_font(int(24 * scale))

            title = font_title.render("Save Name:", True, WHITE)
            surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + 600 * scale * 0.25)))

            # Show full filename with save_ prefix and .json extension
            full_filename = f"save_{self.save_name}.json"
            input_box = font_text.render(full_filename, True, YELLOW)
            surface.blit(input_box, (_center_text_x(surface, input_box, offset_x), int(offset_y + 600 * scale * 0.4)))

            help_text = font_text.render("Enter to save, ESC to cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.6)))
        else:
            draw_dialog_box(surface, offset_x + 800 * scale * 0.1, offset_y + 600 * scale * 0.15, 800 * scale * 0.8, 600 * scale * 0.7)
            font_title = get_font(int(32 * scale))
            font_text = get_font(int(20 * scale))

            title = font_title.render("Select Save to Overwrite", True, YELLOW)
            surface.blit(title, (_center_text_x(surface, title, offset_x), int(offset_y + 600 * scale * 0.2)))

            if self.scroll_offset > 0:
                up_indicator = font_text.render("↑ more", True, GRAY)
                surface.blit(up_indicator, (int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.33)))

            visible_saves = self.existing_saves[self.scroll_offset:self.scroll_offset + self.max_visible]
            for i, save in enumerate(visible_saves):
                is_selected = (self.scroll_offset + i == self.selected_existing)
                color = YELLOW if is_selected else GRAY
                text = font_text.render(save, True, color)
                text_x = int(offset_x + 800 * scale * 0.15)
                text_y = int(offset_y + 600 * scale * 0.35 + i * 35)
                surface.blit(text, (text_x, text_y))
                if is_selected:
                    box_rect = pygame.Rect(text_x - 5, text_y - 2, text.get_width() + 10, text.get_height() + 4)
                    pygame.draw.rect(surface, YELLOW, box_rect, 2)

            if self.scroll_offset + self.max_visible < len(self.existing_saves):
                down_indicator = font_text.render("↓ more", True, GRAY)
                surface.blit(down_indicator, (int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.35 + self.max_visible * 35)))

            help_text = font_text.render("Enter: overwrite, N: new save, D: delete, ESC: cancel", True, GRAY)
            surface.blit(help_text, (_center_text_x(surface, help_text, offset_x), int(offset_y + 600 * scale * 0.75)))
