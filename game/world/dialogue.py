"""Dialogue system for NPC interaction - a small conversation tree."""
import pygame
from game import constants
from game.utils import _wrap_text, get_font
from game.world.mission import abandon_mission, start_mission


def _copy_to_clipboard(text):
    """Best-effort clipboard copy for the DEBUG_MODE dialogue inspector -
    tries pygame.scrap, then the platform clipboard command. Silent no-op
    if none are available."""
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        pygame.scrap.put_text(text)
        return True
    except Exception:
        pass
    import subprocess
    import sys
    cmd = {"win32": ["clip"], "darwin": ["pbcopy"]}.get(sys.platform, ["xclip", "-selection", "clipboard"])
    try:
        subprocess.run(cmd, input=text.encode("utf-8"), check=True)
        return True
    except Exception:
        return False


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


def apply_shared_actions(action, possessions, missions_config=None, story=None):
    """Handle the dialogue actions generic enough to mean the same thing
    regardless of which screen is driving the conversation - LocationScreen's
    station/moon conversations, or SpaceScreen's ship hails:
    - "set_flag:<name>" - record a story-progress flag (possessions.flags)
    - "give_item:<id>" - add one of item_id to the player's personal
      inventory (possessions.items)
    - "spend_credits:<amount>" - a flat credit cost, for a consequence that
      isn't buying a specific ship/outfit (see "buy_ship:"/shop menus for
      those)
    - "adjust_rep:<faction>:<delta>" - shift the player's standing with a
      cross-system faction (possessions.reputation, clamped +-100). delta is
      a signed integer ("adjust_rep:the_vigil:8", "adjust_rep:ninefold_combine:-12").
      Faction ids come from config/stories/{story}/factions.json.
    - "light_beacon:<system_id>" - relight a locked star system's jump
      beacon: sets that system's "unlock_flag" (from its systems/*.json;
      falls back to "beacon_<system_id>_lit"). Needs `story` to resolve the
      flag name; a no-op without it. SpaceScreen posts a galaxy-wide
      "beacon relit" message the frame the flag flips - see
      SpaceScreen._check_beacons().
    - "abandon_mission:<id>" - let the player decline an active mission
      (e.g. "no thanks" to an NPC's offer) - see game/world/mission.py's
      abandon_mission(). Needs missions_config to look up that mission's
      escort_flag/on_end_flags cleanup; a no-op if the caller didn't pass
      one.
    - "set_exclusive_flag:<group>:<name>" - set flag "<group>:<name>" and
      clear every other "<group>:*" flag, for a one-time mutually-exclusive
      choice (a faction allegiance, an ending). Options then gate on
      "requires_flag": "<group>:<name>".
    - "end_story:<id>" - end the game: sets "story_over" plus "ending:<id>".
      main.py notices the flag and shows the EndingScreen (see
      utils.get_endings / game/ui/ending_screen.py), then returns to the
      main menu.
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
    if action.startswith("adjust_rep:"):
        _, faction_id, delta = action.split(":", 2)
        possessions.adjust_reputation(faction_id, int(delta))
        return True
    if action.startswith("light_beacon:"):
        system_id = action.split(":", 1)[1]
        flag = f"beacon_{system_id}_lit"
        if story is not None:
            from game.utils import get_star_systems
            flag = get_star_systems(story).get(system_id, {}).get("unlock_flag") or flag
        possessions.flags[flag] = True
        return True
    if action.startswith("set_exclusive_flag:"):
        _, group, name = action.split(":", 2)
        for key in [k for k in possessions.flags if k.startswith(group + ":")]:
            possessions.flags[key] = False
        possessions.flags[f"{group}:{name}"] = True
        return True
    if action.startswith("end_story:"):
        possessions.flags["story_over"] = True
        possessions.flags[f"ending:{action.split(':', 1)[1]}"] = True
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


def _rep_ok(spec, reputation, want_at_least):
    """Evaluate a "requires_rep"/"requires_rep_below" spec ("<faction>:<n>")
    against a {faction_id: standing} dict. want_at_least True means the
    "requires_rep" sense (standing >= n); False means "requires_rep_below"
    (standing < n). A faction absent from `reputation` counts as 0."""
    faction_id, threshold = spec.split(":", 1)
    standing = (reputation or {}).get(faction_id, 0)
    return standing >= int(threshold) if want_at_least else standing < int(threshold)


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

    An option can also carry a gate - "requires_flag"/"requires_not_flag"
    (a Possessions.flags name) or "requires_rep"/"requires_rep_below"
    ("<faction>:<n>", i.e. standing >= n / standing < n) - and
    current_options() drops it from the list entirely (not just dims it,
    unlike an unaffordable/already-blocked action - see status_fn below)
    until that condition is met, for a conversation option that shouldn't
    even be hinted at yet. An option's "action" can be "set_flag:<name>" or
    "adjust_rep:<faction>:<delta>" (see apply_shared_actions above) to
    unlock one of these later, alongside the "buy_ship:"/"take_loan"
    actions LocationScreen understands.

    `conditional_roots` (optional) is a list of entries tried in order,
    each keyed on a set flag (`{"flag": name, "node": id}`) or a faction
    standing (`{"faction": id, "min": n, "node": id}`) - resolve_root()
    returns the first match's node, letting a conversation open on a
    different greeting (a friendlier one after a past kindness, a colder
    one for an enemy faction) without the caller needing to know why."""
    def __init__(self, npc_name, nodes, root="start", conditional_roots=None, pilot_name="pilot"):
        self.npc_name = npc_name
        self.nodes = nodes
        self.root = root
        self.conditional_roots = conditional_roots or []
        self.pilot_name = pilot_name or "pilot"
        self.current_node = root
        self.selected_option = 0  # the option the pointer is hovering
        # Screen-space hit rects, refreshed by draw() each frame - the
        # conversation box is mouse-only (click an option, or the ✕ to
        # leave). See LocationScreen / SpaceScreen handle_input.
        self._option_rects = []   # [(visible_index, pygame.Rect), ...]
        self._close_rect = None
        self._debug_rect = None   # DEBUG_MODE: the clickable node-id line

    @classmethod
    def from_flat(cls, npc_name, greeting, options, pilot_name="pilot"):
        """Build a single-node Dialogue from the old flat greeting+options
        shape - every option just closes the conversation. Keeps every NPC
        config that only sets "greeting"/"dialogue_options" working
        unchanged."""
        return cls(npc_name, {
            "start": {
                "text": greeting,
                "options": [{"label": option, "next": None} for option in options],
            },
        }, pilot_name=pilot_name)

    def resolve_root(self, flags=None, reputation=None):
        """Which node a fresh conversation should open on: the first
        matching conditional_roots entry's node, else the plain root. Call
        this (not self.root directly) whenever a conversation restarts from
        the top, so earlier story state can change the greeting without the
        caller needing to know why.

        An entry matches on either a set flag (`{"flag": name, "node": id}`)
        or a faction standing (`{"faction": id, "min": n, "node": id}` -
        standing >= n; use a negative `min` for a "cold enough" greeting).
        Entries are tried in order."""
        flags = flags or {}
        reputation = reputation or {}
        for entry in self.conditional_roots:
            if "flag" in entry:
                if flags.get(entry["flag"]):
                    return entry["node"]
            elif "faction" in entry:
                if reputation.get(entry["faction"], 0) >= entry.get("min", 1):
                    return entry["node"]
        return self.root

    def current_text(self):
        """The current node's text, with "{pilot}" substituted for the
        player's entered name (see __init__'s pilot_name) - lets dialogue
        JSON address the player by name the same way story.json's intro
        text does (game/ui/intro_screen.py)."""
        return self.nodes[self.current_node]["text"].replace("{pilot}", self.pilot_name)

    def current_options(self, flags=None, reputation=None):
        """Options at the current node, minus any whose gate isn't met:
        - "requires_flag" / "requires_not_flag" - a Possessions.flags name
        - "requires_rep" / "requires_rep_below" - "<faction>:<n>", meaning
          standing >= n / standing < n (faction absent counts as 0)
        `flags` and `reputation` default to {} (every conditional option
        hidden) rather than requiring every call site to pass them - a
        Dialogue with no conditional options behaves the same either way."""
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
            rep_req = option.get("requires_rep")
            rep_below = option.get("requires_rep_below")
            if rep_req and not _rep_ok(rep_req, reputation, want_at_least=True):
                continue
            if rep_below and not _rep_ok(rep_below, reputation, want_at_least=False):
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

    def option_at(self, pos):
        """Visible-option index under a screen point (from the last draw()),
        or None."""
        for index, rect in self._option_rects:
            if rect.collidepoint(pos):
                return index
        return None

    def close_at(self, pos):
        """True when `pos` is on the box's ✕ close control."""
        return self._close_rect is not None and self._close_rect.collidepoint(pos)

    def debug_click_at(self, pos):
        """DEBUG_MODE only: when `pos` is on the debug node-id line drawn at
        the bottom of the box, copy the current node (id, text, options) to
        the clipboard and return True. Screens check this before their own
        option/close hit-testing. Always False when DEBUG_MODE is off (the
        rect isn't drawn)."""
        if self._debug_rect is not None and self._debug_rect.collidepoint(pos):
            _copy_to_clipboard(self._debug_dump())
            return True
        return False

    def _debug_dump(self):
        """Plain-text dump of the current node for the DEBUG_MODE inspector."""
        node = self.nodes.get(self.current_node, {})
        lines = [f'{self.npc_name} / node "{self.current_node}"', "", node.get("text", ""), ""]
        for option in node.get("options", []):
            dest = "(close)" if option.get("next") is None else f'-> {option["next"]}'
            actions = option_actions(option)
            tail = f"   [{', '.join(actions)}]" if actions else ""
            lines.append(f'  - {option.get("label", "?")}  {dest}{tail}')
        return "\n".join(lines)

    def choose(self, index, flags=None, reputation=None):
        """Convenience wrapper for callers with no actions to apply first
        (see the tests, and from_flat's plain closing options) - resolves
        `index` against current_options(flags, reputation) and calls
        advance() on it. A caller that also runs the option's own actions
        (see option_actions) should resolve the option once and call
        advance() directly instead of this, per advance()'s own docstring."""
        return self.advance(self.current_options(flags, reputation)[index])

    def draw(self, surface, scale, status_fn=None, flags=None, reputation=None):
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
        options_height = len(self.current_options(flags, reputation)) * option_line_height
        content_height = header_height + text_block_height + options_top_gap + options_height + footer_height
        box_height = max(int(250 * scale), content_height)

        box_x = screen_w // 2 - box_width // 2
        box_y = screen_h // 2 - box_height // 2

        pygame.draw.rect(surface, (40, 40, 60), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(surface, (100, 150, 200), (box_x, box_y, box_width, box_height), 3)

        title = font_title.render(self.npc_name, True, (200, 200, 255))
        surface.blit(title, (box_x + text_x_margin, box_y + 10))

        # ✕ close control, top-right of the box (mouse-only exit).
        close_surf = font_title.render("X", True, (220, 180, 180))
        close_pos = (box_x + box_width - text_x_margin - close_surf.get_width(), box_y + 10)
        surface.blit(close_surf, close_pos)
        self._close_rect = pygame.Rect(close_pos[0] - int(6 * scale), close_pos[1] - int(4 * scale),
                                       close_surf.get_width() + int(12 * scale), close_surf.get_height() + int(8 * scale))

        text_y = box_y + header_height - int(10 * scale)
        for line in text_lines:
            line_surf = font_text.render(line, True, (200, 200, 200))
            surface.blit(line_surf, (box_x + text_x_margin, text_y))
            text_y += text_line_height

        self._option_rects = []
        options_top = box_y + header_height + text_block_height + options_top_gap
        for i, option in enumerate(self.current_options(flags, reputation)):
            reason = status_fn(option) if status_fn else None
            row_y = options_top + i * option_line_height
            if reason:
                color = (120, 70, 70)
                label = f"{option['label']} ({reason})"
            else:
                color = (255, 255, 0) if i == self.selected_option else (150, 150, 150)
                label = option['label']
                self._option_rects.append((i, pygame.Rect(
                    box_x + text_x_margin, row_y - int(3 * scale),
                    box_width - text_x_margin * 2, option_line_height)))
            text = font_text.render(("> " if not reason and i == self.selected_option else "  ") + label, True, color)
            surface.blit(text, (box_x + text_x_margin + int(10 * scale), row_y))

        # DEBUG_MODE: a clickable line showing which node this is - click it
        # to copy the node (id / text / options) to the clipboard.
        self._debug_rect = None
        if constants.DEBUG_MODE:
            dbg = font_text.render(f"[debug] {self.npc_name} / {self.current_node}  (click to copy)", True, (110, 160, 130))
            dbg_pos = (box_x + text_x_margin, box_y + box_height - int(24 * scale))
            surface.blit(dbg, dbg_pos)
            self._debug_rect = pygame.Rect(dbg_pos[0] - 4, dbg_pos[1] - 2, dbg.get_width() + 8, dbg.get_height() + 4)
