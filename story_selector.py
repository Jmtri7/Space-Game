"""Screen for selecting which story/campaign to play."""
import pygame
import os
import utils
from constants import BLACK, WHITE, YELLOW, GRAY
from utils import get_font, get_centered_x, render_help_text, handle_menu_navigation, load_json


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
                    # Load story description
                    story_config = load_json(os.path.join(item_path, "story.json"))
                    self.story_descriptions[item] = story_config.get("description", "")

        self.selected_index = 0

    def handle_input(self, events):
        """Handle input and return selected story or 'cancel'."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Use menu navigation helper
                new_index = handle_menu_navigation(event, self.selected_index, len(self.stories))
                if new_index is not None:
                    self.selected_index = new_index
                elif event.key == pygame.K_RETURN:
                    return self.stories[self.selected_index]
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
        return None

    def draw(self, surface):
        """Draw story selection screen."""
        surface.fill(BLACK)
        scale = min(utils.screen_width, utils.screen_height) / 600.0

        # Title
        font_large = get_font(int(72 * scale))
        title = font_large.render("SELECT STORY", True, WHITE)
        title_rect = title.get_rect(center=(utils.screen_width // 2, int(100 * scale)))
        surface.blit(title, title_rect)

        # Story options
        font_menu = get_font(int(48 * scale))
        font_desc = get_font(int(24 * scale))
        y_base = int(250 * scale)
        y_spacing = int(120 * scale)

        for i, story in enumerate(self.stories):
            color = YELLOW if i == self.selected_index else WHITE
            # Capitalize story name
            display_name = story.replace("_", " ").title()
            text = font_menu.render(display_name, True, color)
            text_x = get_centered_x(text.get_width())
            text_y = y_base + i * y_spacing
            surface.blit(text, (text_x, text_y))

            # Draw description below story name
            description = self.story_descriptions.get(story, "")
            if description:
                desc_text = font_desc.render(description, True, GRAY)
                desc_x = get_centered_x(desc_text.get_width())
                desc_y = text_y + int(50 * scale)
                surface.blit(desc_text, (desc_x, desc_y))

            if i == self.selected_index:
                box_rect = pygame.Rect(text_x - 10, text_y - 5, text.get_width() + 20, text.get_height() + 10)
                pygame.draw.rect(surface, YELLOW, box_rect, 3)

        # Help text
        render_help_text(surface, "UP/DOWN: select, ENTER: play, ESC: cancel", utils.screen_height - int(50 * scale))
