"""Read-only overview of the player's mission/stage progress - which stage
each active mission is on, and which missions have finished every stage."""
import pygame
from game.utils import get_ui_scale, get_ui_offset, get_font
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_controls_pane
from game.world.mission import mission_status_lines


class MissionLog:
    """Opened with N from anywhere (space, station, or moon) - mirrors
    PossessionsMenu's read-only, no-interaction-besides-closing shape."""
    def __init__(self, missions_config, possessions):
        self.missions_config = missions_config
        self.possessions = possessions

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_n):
                return "close"
        return None

    def draw(self, surface):
        scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()

        panel_rect = pygame.Rect(int(offset_x + 800 * scale * 0.08), int(offset_y + 600 * scale * 0.08), int(800 * scale * 0.84), int(600 * scale * 0.84))
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_section = get_font(int(22 * scale))
        font_text = get_font(int(17 * scale))

        draw_glow_title(surface, "Mission Log", font_title, panel_rect.centerx, panel_rect.y + int(24 * scale))

        entries = mission_status_lines(self.missions_config, self.possessions)
        line_height = int(24 * scale)
        x = panel_rect.x + int(30 * scale)
        y = panel_rect.y + int(80 * scale)

        if not entries:
            none_text = font_text.render("No missions yet.", True, (150, 150, 150))
            surface.blit(none_text, (x, y))

        # Plain ASCII markers, not unicode glyphs (checkmarks/arrows have
        # shown up unrenderable on some fonts before - see git history).
        for title, stage_texts, current_index in entries:
            title_surf = font_section.render(title, True, (200, 220, 255))
            surface.blit(title_surf, (x, y))
            y += line_height
            for i, text in enumerate(stage_texts):
                if current_index is None or i < current_index:
                    marker, color = "[x]", (150, 200, 150)
                elif i == current_index:
                    marker, color = "->", (255, 255, 150)
                else:
                    marker, color = "[ ]", (150, 150, 150)
                line_surf = font_text.render(f"{marker} {text}", True, color)
                surface.blit(line_surf, (x + int(15 * scale), y))
                y += line_height
            y += line_height // 2

        margin = int(10 * scale)
        draw_controls_pane(surface, margin, margin, "Controls", [("N/ESC", "Close")], scale)
