"""Screen for selecting which story/campaign to play."""
import math
import os
import pygame
import utils
from constants import WHITE, GRAY
from utils import get_font, render_help_text, handle_menu_navigation, load_json
from menu_backdrop import MenuBackdrop
from ui_theme import draw_glass_panel, draw_glow_title, draw_selection_highlight

TITLE = "SELECT STORY"


class StorySelector:
    """Screen for selecting which story/campaign to play."""
    def __init__(self):
        # Scan for available stories
        stories_dir = "config/stories"
        self.stories = []
        self.story_descriptions = {}
        if os.path.exists(stories_dir):
            for item in sorted(os.listdir(stories_dir)):
                item_path = os.path.join(stories_dir, item)
                if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "story.json")):
                    self.stories.append(item)
                    story_config = load_json(os.path.join(item_path, "story.json"))
                    self.story_descriptions[item] = story_config.get("description", "")

        self.selected_index = 0
        # Different seed than the main menu so the two screens' star fields
        # don't look identical when the player moves between them.
        self.backdrop = MenuBackdrop(seed=4242)

    def handle_input(self, events):
        """Handle input and return selected story or 'cancel'."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                new_index = handle_menu_navigation(event, self.selected_index, len(self.stories))
                if new_index is not None:
                    self.selected_index = new_index
                elif event.key == pygame.K_RETURN:
                    return self.stories[self.selected_index]
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
        return None

    def _layout(self):
        """Shared geometry for the panel and story rows, sized to fit every
        story so the panel outline never clips the last one."""
        scale = min(utils.screen_width, utils.screen_height) / 600.0
        panel_width = int(560 * scale)
        panel_top = int(20 * scale)
        title_area = int(90 * scale)
        row_spacing = int(100 * scale)
        row_count = max(1, len(self.stories))
        panel_height = title_area + row_count * row_spacing + int(20 * scale)

        panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
        panel_rect.centerx = utils.screen_width // 2
        panel_rect.top = panel_top

        y_base = panel_rect.top + title_area + row_spacing // 2
        return scale, panel_rect, y_base, row_spacing

    def draw(self, surface):
        """Draw story selection screen."""
        self.backdrop.draw(surface)
        scale, panel_rect, y_base, row_spacing = self._layout()
        draw_glass_panel(surface, panel_rect, scale)
        draw_glow_title(surface, TITLE, get_font(int(48 * scale)), panel_rect.centerx, panel_rect.top + int(18 * scale))

        font_menu = get_font(int(38 * scale))
        font_desc = get_font(int(20 * scale))
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250.0)

        for i, story in enumerate(self.stories):
            is_selected = i == self.selected_index
            row_center_y = y_base + i * row_spacing

            box_width = panel_rect.width - int(40 * scale)
            row_rect = pygame.Rect(0, 0, box_width, int(row_spacing * 0.8))
            row_rect.center = (panel_rect.centerx, row_center_y)
            if is_selected:
                draw_selection_highlight(surface, row_rect, scale, pulse)

            display_name = story.replace("_", " ").title()
            text = font_menu.render(display_name, True, WHITE if is_selected else GRAY)
            text_rect = text.get_rect(center=(panel_rect.centerx, row_center_y - int(14 * scale)))
            surface.blit(text, text_rect)

            description = self.story_descriptions.get(story, "")
            if description:
                desc_text = font_desc.render(description, True, GRAY)
                desc_rect = desc_text.get_rect(center=(panel_rect.centerx, row_center_y + int(20 * scale)))
                surface.blit(desc_text, desc_rect)

        render_help_text(surface, "Up/Down: select, Enter: play, ESC: cancel")
