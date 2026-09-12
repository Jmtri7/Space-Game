"""Mission-computer terminal - opened by talking to an NPC whose "shop"
config has type "mission_board" (see LocationScreen._build_local_character,
same "shop" config-driven dispatch every other purpose-built menu uses -
see game/app/loop_helpers.py's build_shop_menu). Lists a handful of
randomly generated missions (game/world/generated_mission.py); Accept
commits one into Possessions.generated_missions."""
import pygame
from game.constants import GRAY
from game.utils import get_ui_scale, get_font, _wrap_text
from game.ui.ui_theme import draw_glass_panel, draw_glow_title, draw_purchase_message, modal_panel_rect, PURCHASE_MESSAGE_FRAMES
from game.ui.selectable_list import SelectableList
from game.ui.menu_base import MenuBase
from game.world.generated_mission import generate_missions, accept_mission

KIND_COLOR = {"haul": (150, 210, 255), "bounty": (255, 150, 150), "scan": (200, 170, 255)}


class MissionBoardMenu(MenuBase):
    def __init__(self, possessions, story, cargo_capacity, system_id, offer_count=3):
        self.possessions = possessions
        self.story = story
        self.system_id = system_id
        self.cargo_capacity = cargo_capacity
        # Offers are rolled once per visit (opening the terminal), not
        # re-rolled every draw - so the list doesn't shuffle out from under
        # a player who's mid-read. Re-opening the terminal rolls a fresh set.
        self.offers = generate_missions(story, cargo_capacity, system_id, count=offer_count)
        self.list = SelectableList(self.offers, max_visible=5)
        self.message = None
        self.message_timer = 0

    def _already_active(self, offer):
        """True if an identical-looking offer is already an active
        generated mission - a light guard against accepting the same haul
        twice from one visit (each Accept re-rolls nothing, so the offer
        stays in the list after being taken unless removed)."""
        return any(m.get("title") == offer.get("title") and m is not offer
                   for m in self.possessions.generated_missions.values())

    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self._accept(self.list.current())
                continue
            pressed = self.handle_button_event(event, lambda: self.button_bar_rects(get_ui_scale()))
            if pressed == "close":
                return "close"
            if pressed == "accept":
                self._accept(self.list.current())
                continue
            if event.type == pygame.MOUSEWHEEL:
                self.list.scroll(-event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                index = self.list.index_at(event.pos)
                if index is not None:
                    self.list.selected = index
        return None

    def _accept(self, offer):
        if not offer or self._already_active(offer):
            return
        accept_mission(self.possessions, offer)
        self.offers.remove(offer)
        self.list.items = self.offers
        self.message = f"Accepted: {offer['title']}"
        self.message_timer = PURCHASE_MESSAGE_FRAMES

    def buttons(self):
        offer = self.list.current()
        disabled = not offer
        return [("close", "Close", (235, 235, 240), False), ("accept", "Accept", (150, 220, 160), disabled)]

    def panel_rect(self, scale):
        return modal_panel_rect(scale, 0.12, 0.7, 0.76)

    def button_bar_rects(self, scale):
        panel = self.panel_rect(scale)
        w, h, m = int(120 * scale), int(38 * scale), int(16 * scale)
        close_rect = pygame.Rect(panel.x + m, panel.y + m, w, h)
        aw = int(150 * scale)
        action_rect = pygame.Rect(panel.centerx - aw // 2, panel.bottom - int(58 * scale), aw, int(42 * scale))
        return [close_rect, action_rect]

    def draw_content(self, surface):
        scale = get_ui_scale()
        panel_rect = self.panel_rect(scale)
        draw_glass_panel(surface, panel_rect, scale)

        font_title = get_font(int(34 * scale))
        font_label = get_font(int(20 * scale))
        font_desc = get_font(int(16 * scale))

        y = panel_rect.y + int(20 * scale)
        y += draw_glow_title(surface, "Mission Computer", font_title, panel_rect.centerx, y)
        y += int(6 * scale)

        if not self.offers:
            empty = font_label.render("No missions posted right now.", True, GRAY)
            surface.blit(empty, (panel_rect.centerx - empty.get_width() // 2, y + int(20 * scale)))
        else:
            line_height = int(28 * scale)
            self.list.draw(surface, font_label, panel_rect.centerx, y + int(20 * scale), line_height, scale,
                            label_fn=lambda m: f"[{m['kind'].upper()}] {m['title']}  -  {m.get('reward', 0)}cr")

            # Description of the currently selected offer, wrapped, below the list.
            offer = self.list.current()
            if offer:
                desc_y = y + int(20 * scale) + self.list.max_visible * line_height + int(20 * scale)
                color = KIND_COLOR.get(offer.get("kind"), GRAY)
                kind_text = font_desc.render(offer["kind"].upper(), True, color)
                surface.blit(kind_text, (panel_rect.centerx - kind_text.get_width() // 2, desc_y))
                desc_y += int(22 * scale)
                wrap_width = panel_rect.width - int(80 * scale)
                for line in _wrap_text(font_desc, offer.get("description", ""), wrap_width) or []:
                    text = font_desc.render(line, True, GRAY)
                    surface.blit(text, (panel_rect.centerx - text.get_width() // 2, desc_y))
                    desc_y += int(20 * scale)

        if self.message_timer > 0:
            self.message_timer -= 1
            draw_purchase_message(surface, self.message, self.message_timer, panel_rect.centerx, panel_rect.bottom - int(100 * scale), scale)
