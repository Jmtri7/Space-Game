"""Dialogue system for NPC interaction - a small conversation tree."""
import pygame
from game.utils import _wrap_text, get_font
from game.world.mission import abandon_mission, start_mission


def option_actions(option):
    """Normalize a dialogue option's effect(s) into a list. Most options
    carry at most one "action" string (e.g. "buy_ship:shuttle",
    "take_loan"), but a consequence-flavored option can need more than one
    effect at once - charge some credits, hand over a keepsake item, *and*
    record that it happened, all from choosing one line - so an "actions"
    list is also allowed. Returns [] for a plain navigation/closing option
    that has neither key."""
    if "actions" in option:
        return option["actions"]
    if "action" in option:
        return [option["action"]]
    return []


def apply_shared_actions(action, possessions, missions_config=None):
    """Handle the dialogue actions generic enough to mean the same thing
    regardless of which screen is driving the conversation - LocationScreen's
    station/moon conversations, or SpaceScreen's ship hails:
    - "set_flag:<name>" - record a story-progress flag (possessions.flags)
    - "give_item:<id>" - add one of item_id to the player's personal
      inventory (possessions.items)
    - "spend_credits:<amount>" - a flat credit cost, for a consequence that
      isn't buying a specific ship/outfit (see "buy_ship:"/shop menus for
      those)
    - "abandon_mission:<id>" - let the player decline an active mission
      (e.g. "no thanks" to an NPC's offer) - see game/world/mission.py's
      abandon_mission(). Needs missions_config to look up that mission's
      escort_flag/on_end_flags cleanup; a no-op if the caller didn't pass
      one.
    - "start_mission:<id>" - begin a mission from a dialogue choice (e.g.
      accepting a station guide's offer to walk you through the place),
      instead of it only being kick-started by story.json's
      starting_mission. Needs missions_config; a no-op without it, or if
      the mission is already active/completed (see start_mission()). The
      first stage's one_way_message is *not* delivered here (this returns
      only a bool) - author stage 0 with no message, or as one the guide's
      own dialogue text already covers.
    Returns True if it handled the action, so a caller with its own extra,
    screen-specific actions (LocationScreen's "buy_ship:"/"take_loan", which
    need more than just `possessions` - see there) can try this first and
    fall through to those otherwise."""
    if action.startswith("set_flag:"):
        possessions.flags[action.split(":", 1)[1]] = True
        return True
    if action.startswith("give_item:"):
        possessions.add_item(action.split(":", 1)[1], 1)
        return True
    if action.startswith("spend_credits:"):
        possessions.spend(int(action.split(":", 1)[1]))
        return True
    if action.startswith("abandon_mission:"):
        if missions_config is not None:
            abandon_mission(missions_config, possessions, action.split(":", 1)[1])
        return True
    if action.startswith("start_mission:"):
        if missions_config is not None:
            start_mission(missions_config, possessions, action.split(":", 1)[1])
        return True
    return False


def shared_action_blocked_reason(action, possessions):
    """Why a shared action (see apply_shared_actions) can't be taken right
    now, or None if it's fine. Only "spend_credits:" ever blocks (can't
    afford it) - set_flag/give_item have no precondition of their own."""
    if action.startswith("spend_credits:"):
        cost = int(action.split(":", 1)[1])
        if not possessions.can_afford(cost):
            return "not enough credits"
    return None


class Dialogue:
    """A conversation tree: each node has text and a list of options, each
    option leading to another node ("next") or closing the conversation
    ("next": None). Most NPCs only need a single node with closing options -
    see from_flat() - but a node's "next" can point anywhere in the tree,
    including back to itself or an earlier node, for real branching
    conversations.

    An option can also carry "requires_flag"/"requires_not_flag" (a flag
    name from Possessions.flags) - current_options() drops it from the list
    entirely (not just dims it, unlike an unaffordable/already-blocked
    action - see status_fn below) until that condition is met, for a
    conversation option that shouldn't even be hinted at yet. An option's
    "action" can be "set_flag:<name>" (see apply_flag_action above) to
    unlock one of these later, alongside the existing "buy_ship:"/
    "take_loan" actions LocationScreen understands.

    `conditional_roots` (optional) is a list of {"flag": name, "node": id}
    - resolve_root() picks the first entry whose flag is set, letting a
    conversation open on a different greeting node once some flag is set
    (e.g. a friendlier greeting after a past kindness) without needing the
    caller to know why."""
    def __init__(self, npc_name, nodes, root="start", conditional_roots=None):
        self.npc_name = npc_name
        self.nodes = nodes
        self.root = root
        self.conditional_roots = conditional_roots or []
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

    def resolve_root(self, flags=None):
        """Which node a fresh conversation should open on: the first
        conditional_roots entry whose flag is set in `flags`, else the
        plain root. Call this (not self.root directly) whenever a
        conversation restarts from the top, so a story flag set earlier can
        change the greeting without the caller needing to know why."""
        flags = flags or {}
        for entry in self.conditional_roots:
            if flags.get(entry["flag"]):
                return entry["node"]
        return self.root

    def current_text(self):
        return self.nodes[self.current_node]["text"]

    def current_options(self, flags=None):
        """Options at the current node, minus any whose requires_flag/
        requires_not_flag condition isn't met. flags defaults to {} (every
        conditional option hidden) rather than requiring every call site to
        pass one - a Dialogue with no conditional options behaves exactly
        as before either way."""
        flags = flags or {}
        options = self.nodes[self.current_node]["options"]
        visible = []
        for option in options:
            requires = option.get("requires_flag")
            requires_not = option.get("requires_not_flag")
            if requires and not flags.get(requires):
                continue
            if requires_not and flags.get(requires_not):
                continue
            visible.append(option)
        return visible

    def advance(self, option):
        """Act on an already-resolved option dict (see current_options) -
        the option itself, not an index, so a caller that applied the
        option's own actions (see option_actions/apply_shared_actions)
        before calling this isn't tripped up by an action that changes
        flags current_options(flags) itself depends on (e.g. an option
        hidden by requires_not_flag on the very flag its own "set_flag:"
        action sets - re-deriving the filtered list *after* that action
        ran would silently shift every following index). Returns True if
        the conversation should close (a "next" of None - a closing option
        like "Leave"), otherwise advances to that option's node and
        returns False."""
        next_node = option.get("next")
        if next_node is None:
            return True
        self.current_node = next_node
        self.selected_option = 0
        return False

    def choose(self, index, flags=None):
        """Convenience wrapper for callers with no actions to apply first
        (see the tests, and from_flat's plain closing options) - resolves
        `index` against current_options(flags) and calls advance() on it.
        A caller that also runs the option's own actions (see
        option_actions) should resolve the option once and call advance()
        directly instead of this, per advance()'s own docstring."""
        return self.advance(self.current_options(flags)[index])

    def draw(self, surface, scale, status_fn=None, flags=None):
        """status_fn(option) -> reason string or None. Options with a
        reason are drawn dim with the reason appended, instead of the
        normal selected/unselected colors - used for actions the player
        can't currently take (can't afford, already have a loan, etc.)."""
        font_title = get_font(int(24 * scale))
        font_text = get_font(int(18 * scale))

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
        options_height = len(self.current_options(flags)) * option_line_height
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
        for i, option in enumerate(self.current_options(flags)):
            reason = status_fn(option) if status_fn else None
            if reason:
                color = (120, 70, 70)
                label = f"> {option['label']} ({reason})"
            else:
                color = (255, 255, 0) if i == self.selected_option else (150, 150, 150)
                label = f"> {option['label']}"
            text = font_text.render(label, True, color)
            surface.blit(text, (box_x + text_x_margin + int(10 * scale), options_top + i * option_line_height))
