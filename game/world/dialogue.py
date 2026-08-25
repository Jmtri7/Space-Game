"""Dialogue system for NPC interaction - a small conversation tree."""
import pygame
from game.utils import _wrap_text


class Dialogue:
    """A conversation tree: each node has text and a list of options, each
    option leading to another node ("next") or closing the conversation
    ("next": None). Most NPCs only need a single node with closing options -
    see from_flat() - but a node's "next" can point anywhere in the tree,
    including back to itself or an earlier node, for real branching
    conversations."""
    def __init__(self, npc_name, nodes, root="start"):
        self.npc_name = npc_name
        self.nodes = nodes
        self.root = root
        self.current_node = root
        self.selected_option = 0

    @classmethod
    def from_flat(cls, npc_name, greeting, options):
        """Build a single-node Dialogue from the old flat greeting+options
        shape - every option just closes the conversation. Keeps every NPC
        config that only sets "greeting"/"dialogue_options" working
        unchanged."""
        return cls(npc_name, {
            "start": {
                "text": greeting,
                "options": [{"label": option, "next": None} for option in options],
            },
        })

    def current_text(self):
        return self.nodes[self.current_node]["text"]

    def current_options(self):
        return self.nodes[self.current_node]["options"]

    def choose(self, index):
        """Act on option `index` at the current node. Returns True if the
        conversation should close (a "next" of None - a closing option like
        "Leave"), otherwise advances to that option's node and returns
        False."""
        option = self.current_options()[index]
        next_node = option.get("next")
        if next_node is None:
            return True
        self.current_node = next_node
        self.selected_option = 0
        return False

    def draw(self, surface, scale, status_fn=None):
        """status_fn(option) -> reason string or None. Options with a
        reason are drawn dim with the reason appended, instead of the
        normal selected/unselected colors - used for actions the player
        can't currently take (can't afford, already have a loan, etc.)."""
        font_title = pygame.font.Font(None, int(24 * scale))
        font_text = pygame.font.Font(None, int(18 * scale))

        screen_w = surface.get_width()
        screen_h = surface.get_height()
        box_width = int(400 * scale)
        text_x_margin = int(20 * scale)
        text_line_height = int(20 * scale)
        option_line_height = int(30 * scale)

        # Word-wrap the node's text to the box's width - long lines (like a
        # multi-sentence NPC response) used to just run straight off the
        # box's right edge instead of wrapping.
        text_lines = _wrap_text(font_text, self.current_text(), box_width - text_x_margin * 2)
        text_block_height = len(text_lines) * text_line_height

        # Box grows to fit however many lines the text and options actually
        # need, instead of a fixed height that could clip either one.
        header_height = int(50 * scale)
        options_top_gap = int(20 * scale)
        footer_height = int(40 * scale)
        options_height = len(self.current_options()) * option_line_height
        content_height = header_height + text_block_height + options_top_gap + options_height + footer_height
        box_height = max(int(250 * scale), content_height)

        box_x = screen_w // 2 - box_width // 2
        box_y = screen_h // 2 - box_height // 2

        pygame.draw.rect(surface, (40, 40, 60), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(surface, (100, 150, 200), (box_x, box_y, box_width, box_height), 3)

        title = font_title.render(self.npc_name, True, (200, 200, 255))
        surface.blit(title, (box_x + text_x_margin, box_y + 10))

        text_y = box_y + header_height - int(10 * scale)
        for line in text_lines:
            line_surf = font_text.render(line, True, (200, 200, 200))
            surface.blit(line_surf, (box_x + text_x_margin, text_y))
            text_y += text_line_height

        options_top = box_y + header_height + text_block_height + options_top_gap
        for i, option in enumerate(self.current_options()):
            reason = status_fn(option) if status_fn else None
            if reason:
                color = (120, 70, 70)
                label = f"> {option['label']} ({reason})"
            else:
                color = (255, 255, 0) if i == self.selected_option else (150, 150, 150)
                label = f"> {option['label']}"
            text = font_text.render(label, True, color)
            surface.blit(text, (box_x + text_x_margin + int(10 * scale), options_top + i * option_line_height))

        close_text = font_text.render("Press ESC to close", True, (150, 150, 150))
        surface.blit(close_text, (box_x + text_x_margin, box_y + box_height - int(30 * scale)))
