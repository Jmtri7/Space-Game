"""Read-only overview of a player's credits, owned ships, and loans."""
import pygame
from game.utils import get_ui_scale, get_ui_offset, get_font, get_ship_type
from game.ui.ui_theme import draw_glass_panel, draw_glow_title


class PossessionsMenu:
    """Read-only overview of the player's credits, owned ships, and loans -
    opened with P from anywhere (space, station, or moon)."""
    def __init__(self, possessions, story="default"):
        self.possessions = possessions
        self.story = story

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                return "close"
        return None

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.15), int(offset_y + 600 * scale * 0.15), int(800 * scale * 0.7), int(600 * scale * 0.7))
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(36 * scale))
        font_section = get_font(int(24 * scale))
        font_text = get_font(int(20 * scale))

        draw_glow_title(surface, "Possessions", font_title, panel_rect.centerx, panel_rect.y + int(40 * scale))

        line_height = int(28 * scale)
        x = panel_rect.x + int(30 * scale)
        y = panel_rect.y + int(90 * scale)

        credits_text = font_section.render(f"Credits: {self.possessions.credits}", True, (255, 220, 100))
        surface.blit(credits_text, (x, y))
        y += line_height * 2

        ships_title = font_section.render("Owned Ships", True, (200, 220, 255))
        surface.blit(ships_title, (x, y))
        y += line_height
        if self.possessions.owned_ships:
            for ship_type_id in self.possessions.owned_ships:
                ship_type = get_ship_type(self.story, ship_type_id)
                name = ship_type.get("name", ship_type_id)
                line = font_text.render(f"- {name}", True, (220, 220, 220))
                surface.blit(line, (x + int(15 * scale), y))
                y += line_height
        else:
            none_text = font_text.render("- None", True, (150, 150, 150))
            surface.blit(none_text, (x + int(15 * scale), y))
            y += line_height
        y += line_height

        loans_title = font_section.render("Loans", True, (200, 220, 255))
        surface.blit(loans_title, (x, y))
        y += line_height
        if self.possessions.loans:
            for loan in self.possessions.loans:
                line = font_text.render(f"- {loan['lender']}: {loan['principal']}cr", True, (220, 180, 180))
                surface.blit(line, (x + int(15 * scale), y))
                y += line_height
        else:
            none_text = font_text.render("- None", True, (150, 150, 150))
            surface.blit(none_text, (x + int(15 * scale), y))
            y += line_height

        close_text = font_text.render("P or ESC: close", True, (150, 150, 150))
        surface.blit(close_text, (panel_rect.x + int(20 * scale), panel_rect.bottom - int(30 * scale)))
