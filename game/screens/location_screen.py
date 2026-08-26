"""Configurable location for station, moon city, and moon wilderness."""
import pygame
import math
import game.constants as constants
from game.constants import GAME_WIDTH, GAME_HEIGHT, WHITE, YELLOW, GREEN, GRAY
from game.utils import get_scale, load_json, to_screen, to_world, draw_debug_marker, draw_target_brackets, get_ui_scale, get_font, set_camera_offset, get_building_type, get_culture, get_ship_type, get_graphics_asset
import game.utils as utils
from game.ui.ui_theme import draw_controls_pane, draw_status_pane, draw_info_panel, draw_glass_panel
from game.screens.screen_base import ScreenBase
from game.world.character import Character
from game.world.person import Person
from game.world.dialogue import Dialogue
from game.world.player_character import PlayerCharacter


# Bumped way up from the old "shuttle's cost" amount for testing, so a loan
# alone can cover any ship/outfit combo without grinding for credits first.
# Revisit before treating this as real game balance.
TESTING_LOAN_AMOUNT = 100_000


class LocationScreen(ScreenBase):
    """Configurable location for station, moon city, and moon wilderness. Loads layout and NPCs from config."""

    # Game-space units above a person's feet (self.y) their floating name/
    # role label is anchored to - clears the head/helmet drawn by Person.draw().
    LABEL_HEIGHT_ABOVE = 38

    def __init__(self, config_file=None, config_data=None, world_width=1600, world_height=1600, pilot_name="", story="default", player_possessions=None, on_ship_purchased=None, location_labels=None):
        self.story = story  # which story's config/building_types.json etc. to resolve against
        # {interior_key: display label} for every sibling interior at the
        # same landable (see SpaceScreen.get_interior_screen) - used only to
        # render portal labels (see _display_name/_portal_label), so a
        # LocationScreen built without one (e.g. directly in a test) just
        # falls back to prettified keys instead of failing.
        self.location_labels = location_labels or {}
        # Load config from file or use inline data
        if config_data is not None:
            self.config = config_data
            self.config_file = None
        else:
            self.config_file = config_file
            self.config = load_json(config_file) or {}

        # Portals: each is {"x", "y", "connected_locations", "return_to_ship"} -
        # one per physical doorway out of this location, so a junction with
        # several real destinations gets several distinct portals instead of
        # one spot serving all of them (see docs/BACKLOG.md's "Multiple
        # exits with different options" and portal_for()/arrive_from()
        # below for why: so stepping back through the specific portal you
        # arrived from always leads back the way you came, instead of
        # re-presenting every destination this location has). A config with
        # just one exit keeps using the older flat "entrance"/
        # "connected_locations"/"return_to_ship" keys, normalized into a
        # single-item list here so the rest of the class never needs to
        # know which style a given config used.
        portals_cfg = self.config.get("portals")
        if portals_cfg:
            self.portals = [
                {
                    "x": portal["x"], "y": portal["y"],
                    "connected_locations": portal.get("connected_locations", []),
                    "return_to_ship": portal.get("return_to_ship", False),
                }
                for portal in portals_cfg
            ]
        else:
            entrance_cfg = self.config.get("entrance", {})
            self.portals = [{
                "x": entrance_cfg.get("x", world_width // 2),
                "y": entrance_cfg.get("y", world_height - 80),
                "connected_locations": self.config.get("connected_locations", []),
                "return_to_ship": self.config.get("return_to_ship", True),
            }]
        start_x, start_y = self.portals[0]["x"], self.portals[0]["y"]

        # Initialize ScreenBase
        super().__init__(pilot_name=pilot_name)

        # Initialize walkable area properties
        # player_possessions, if given, is the player's one real Possessions
        # object (see SpaceScreen.get_interior_screen) - shared by reference
        # so a purchase made here is instantly visible everywhere else the
        # player's possessions are read (space HUD, other interiors, saves).
        # Falls back to a fresh empty one (via Person's own default) when
        # constructed standalone, e.g. in tests.
        self.player = PlayerCharacter(start_x, start_y, name=pilot_name, possessions=player_possessions, outfit=get_graphics_asset(self.story, "outfits", "space_suit"))
        # Called with a ship_type_id right after a successful "buy_ship:"
        # dialogue action - lets SpaceScreen (which owns the real flyable
        # ship) configure it, without LocationScreen importing game.screens
        # (see get_interior_screen callable injection on AIShip for the
        # same one-directional-dependency idiom).
        self.on_ship_purchased = on_ship_purchased
        # Which key in the landable's interiors dict this is (e.g.
        # "dormitory", "default") - set by SpaceScreen.get_interior_screen;
        # None when constructed standalone (e.g. in tests).
        self.interior_key = None
        self.world_width = world_width
        self.world_height = world_height
        self.speed = constants.WALKING_SPEED
        self.entrance_range = 35  # How close to a portal to use it
        self.talk_range = 60  # How close to an NPC/pilot to start a conversation
        # Cached by handle_input() when L opens the exit menu, so
        # get_exit_options()/get_available_exit_options()/
        # get_exit_disabled_reasons() (called later, from main.py, once the
        # menu is already up) act on the same portal the player actually
        # pressed L next to - the player can't move while the menu is open,
        # but this avoids relying on that indirectly.
        self._active_portal = None

        # Get display properties
        self.ui_label = self.config.get("label", "Location")
        self.bg_color = tuple(self.config.get("background_color", [50, 50, 70]))

        # A "culture" on the interior itself (independent of any exterior asset lookup)
        # walls become the culture's wall_color and the walkable area is one or more
        # inset rooms in floor_color, so the room reads distinctly from its walls
        # instead of one flat fill. Locations with no culture keep the old
        # flat-background behavior (movement bounded by the full world rect).
        self.culture_id = self.config.get("culture")
        # Each room is {"rect": (x, y, w, h), "label": str or None} in world space.
        # A station interior with a "rooms" list gets one rect per room/hallway
        # (movement is allowed anywhere in their union, so a hallway rect between
        # two room rects reads as a corridor connecting them); one without falls
        # back to a single margin-inset rect, same as before rooms existed.
        self.rooms = []
        self.floor_color = None
        if self.culture_id:
            culture = get_culture(self.story, self.culture_id)
            self.bg_color = tuple(culture.get("wall_color", self.bg_color))
            self.floor_color = tuple(culture.get("floor_color", self.bg_color))
            rooms_cfg = self.config.get("rooms")
            if rooms_cfg:
                self.rooms = [{"rect": tuple(room["rect"]), "label": room.get("label")} for room in rooms_cfg]
            else:
                margin = self.config.get("wall_margin", 60)
                self.rooms = [{"rect": (margin, margin, world_width - 2 * margin, world_height - 2 * margin), "label": None}]

        # Load structures (buildings, craters, rocks, etc.)
        self.structures = self.config.get("structures", [])
        # Ground-level collision boxes for the buildings among those
        # structures (decorative terrain like moon rocks has no
        # building_type and contributes none) - see _building_footprint()
        # for why this is deliberately smaller than each building's full
        # drawn silhouette.
        self.building_footprints = [fp for fp in (self._building_footprint(s) for s in self.structures) if fp]
        self.npcs_config = self.config.get("npcs", [])
        self.npcs = [self._build_local_character(cfg) for cfg in self.npcs_config]
        self.current_npc_target = None  # For T key targeting
        self.active_dialogue = None  # Set to an NPC's Dialogue while talking
        self.active_shop = None  # Set to an NPC's shop config when "shop" is returned from handle_input
        # HUD panel rects from the most recently drawn frame - see draw()'s
        # own comment on where this is populated; empty until the first
        # draw() call (e.g. a LocationScreen used in a test without ever
        # drawing), so a click can't be wrongly excluded before then.
        self._hud_click_rects = []

        # AI pilots (Person, not NPC - no dialogue/behavior, just a body)
        # currently walking around inside this interior on a docking errand
        # (see DockRoutine). Not targetable/talkable, just visible - so the
        # player can actually see a freighter pilot they're sharing the
        # room with, even while docked at a different station than the
        # player happens to be standing in.
        self.visitors = []

    def _build_local_character(self, cfg):
        """Build one config-driven local resident: a Person (with a
        Dialogue - a real tree if the config provides one, otherwise the
        flat greeting+options shape) wrapped in a Character with no ship.
        Their role picks the routine that decides whether they wander or
        stay put (see game/world/character.py's ROLE_ROUTINES) - the same
        role->routine mechanism AI ship pilots use, just never flying
        anything."""
        # "outfit" is per-NPC-config, defaulting to space_suit like everyone
        # else - lets a future NPC config opt into a different graphics.json
        # outfit entry without any drawing-code changes.
        person = Person(cfg.get("x", 0), cfg.get("y", 0), name=cfg.get("name", "NPC"), outfit=get_graphics_asset(self.story, "outfits", cfg.get("outfit", "space_suit")))
        dialogue_tree = cfg.get("dialogue_tree")
        if dialogue_tree:
            person.dialogue = Dialogue(person.name, dialogue_tree["nodes"], root=dialogue_tree.get("root", "start"))
        else:
            person.dialogue = Dialogue.from_flat(person.name, cfg.get("greeting", "Hello!"), cfg.get("dialogue_options") or ["Talk", "Leave"])
        # A "shop" config key (see ShopMenu/ShipBrowserMenu/OutfittingMenu)
        # opens a purpose-built buy/sell screen instead of dialogue when T is
        # pressed - None for every NPC that's just flavor/dialogue.
        person.shop = cfg.get("shop")
        return Character(person, role=cfg.get("role", "resident"), can_move_to=self.can_move_to)

    def _resolve_portal(self, portal):
        """Which portal get_exit_options() and friends should act on when
        the caller didn't pass one explicitly: whichever portal L was just
        pressed next to (_active_portal, set by handle_input - main.py
        calls these after the fact, once ExitMenu is already up), falling
        back to whatever the player is currently standing next to (for
        direct calls, e.g. from tests), and finally this location's first
        portal (so these never crash even called with no portal in range -
        e.g. a fresh LocationScreen in a test, which starts standing
        exactly on its own first portal anyway)."""
        return portal or self._active_portal or self._nearby_portal() or self.portals[0]

    def get_exit_options(self, portal=None):
        """Ordered destinations available through one portal (see
        self.portals - defaults to _resolve_portal()): each of its
        connected_locations keys (in config order), then "ship" last if
        that portal's return_to_ship allows it. Used both to drive the
        player's exit menu and by AI routines (see DockRoutine) choosing
        where to go next - same list, same meaning, for both."""
        portal = self._resolve_portal(portal)
        options = list(portal["connected_locations"])
        if portal["return_to_ship"]:
            options.append("ship")
        return options

    def all_exit_options(self):
        """Every destination reachable from this location via *any* of its
        portals (see self.portals), deduplicated but order-preserving.
        Unlike get_exit_options(), which is scoped to one specific portal
        (the player is always standing at a particular one when L opens
        the exit menu), this is for DockRoutine: an AI pilot decides where
        to go next while still talking to an NPC, nowhere near a portal
        yet, so it needs to know what's reachable at all before walking to
        whichever portal actually leads there (see portal_for)."""
        options = []
        for portal in self.portals:
            for option in self.get_exit_options(portal):
                if option not in options:
                    options.append(option)
        return options

    @property
    def ship_available(self):
        """Whether the player actually has a ship to board right now - not
        just whether this location's exit is configured to offer one.
        False until a "buy_ship:" dialogue action has run (see
        _apply_dialogue_action)."""
        return bool(self.player.possessions.owned_ships)

    def get_available_exit_options(self, portal=None):
        """get_exit_options() minus "ship" when there's no ship to actually
        board yet - used to decide whether L can exit immediately or needs
        to open ExitMenu so the player can see *why* nothing happened."""
        options = self.get_exit_options(portal)
        if not self.ship_available:
            options = [option for option in options if option != "ship"]
        return options

    def get_exit_disabled_reasons(self, portal=None):
        """{key: reason} for exit options this location's config offers but
        aren't usable right now - currently just "ship" with no ship owned
        yet. Passed to ExitMenu so it's shown, dim, instead of silently
        missing."""
        if "ship" in self.get_exit_options(portal) and not self.ship_available:
            return {"ship": "no ship docked here"}
        return {}

    def portal_for(self, key):
        """The portal (see self.portals) associated with `key` - either a
        connected location's interior key, or "ship" for a portal that
        leads back to the ship. Used both to find where to arrive when
        entering from `key` (see arrive_from, and DockRoutine's own use for
        AI pilots) and where to walk to when heading toward `key` - the
        same physical portal serves both directions of one connection.
        Falls back to this location's first/primary portal when no portal
        singles out `key` (a fresh arrival with no "from" context passes
        key=None, which never matches any portal on purpose)."""
        for portal in self.portals:
            if key == "ship" and portal["return_to_ship"]:
                return portal
            if key in portal["connected_locations"]:
                return portal
        return self.portals[0]

    def arrive_from(self, origin_key):
        """Place the player at whichever portal leads back to origin_key
        (an interior key, or "ship") - called whenever the player enters
        this (persistent, cached) location via a portal transition, so they
        appear next to the door they actually walked through instead of
        wherever they happened to be left the last time they visited this
        location."""
        portal = self.portal_for(origin_key)
        self.player.x, self.player.y = portal["x"], portal["y"]

    def _display_name(self, key):
        """Human-readable label for a connected_locations key or "ship" -
        used to label portals in-world (see _portal_label) now that a
        single-destination portal no longer opens a menu that would
        otherwise be the only place its destination's name showed up.
        Prefers the sibling interior's own configured "label" (see
        self.location_labels, built by SpaceScreen.get_interior_screen),
        falling back to a prettified version of the key itself (e.g.
        "loan_office" -> "Loan Office") when there's no sibling label to
        borrow - e.g. "ship", or a LocationScreen built standalone."""
        if key == "ship":
            return "Ship"
        return self.location_labels.get(key) or key.replace("_", " ").title()

    def _portal_label(self, portal):
        """Display text for one portal: the destination(s) it leads to,
        joined with "/" for a portal that offers more than one (a menu
        still opens for those - the label is just a preview of what's in
        it, same as a single-destination portal's label is now the only
        preview it gets since L skips straight past its menu)."""
        names = [self._display_name(key) for key in portal["connected_locations"]]
        if portal["return_to_ship"]:
            names.append(self._display_name("ship"))
        return " / ".join(names)

    def _nearby_portal(self):
        """Whichever portal (see self.portals) the player is currently
        close enough to use, or None - the nearest one, if somehow more
        than one is in range at once (portals are laid out with enough
        space between them that this shouldn't normally happen)."""
        in_range = [p for p in self.portals if math.sqrt((self.player.x - p["x"]) ** 2 + (self.player.y - p["y"]) ** 2) <= self.entrance_range]
        if not in_range:
            return None
        return min(in_range, key=lambda p: (self.player.x - p["x"]) ** 2 + (self.player.y - p["y"]) ** 2)

    def _option_blocked_reason(self, option):
        """Why a dialogue option's "action" can't be taken right now, or
        None if it's fine. Options with no action are never blocked."""
        action = option.get("action")
        if not action:
            return None
        if action.startswith("buy_ship:"):
            ship_type_id = action.split(":", 1)[1]
            cost = get_ship_type(self.story, ship_type_id).get("cost", 0)
            if not self.player.possessions.can_afford(cost):
                return "not enough credits"
        elif action == "take_loan" and self.player.possessions.loans:
            return "already have a loan"
        return None

    def _apply_dialogue_action(self, action):
        """Perform the game-state effect of a dialogue option's "action"
        tag - called once it's confirmed not blocked (see
        _option_blocked_reason), right before Dialogue.choose() advances to
        the option's response node."""
        if action.startswith("buy_ship:"):
            self.buy_ship(action.split(":", 1)[1])
        elif action == "take_loan":
            self.player.possessions.take_loan("Station Credit Union", TESTING_LOAN_AMOUNT)

    def buy_ship(self, ship_type_id):
        """Spend credits, add the ship to possessions, and let SpaceScreen
        (which owns the real flyable ship) configure it - shared by the
        dialogue-driven "buy_ship:" action and ShipBrowserMenu (via main.py's
        build_shop_menu), so both purchase paths perform the exact same
        mutation.

        Uninstalls whatever's currently equipped first: installed_outfits
        describes "whichever ship is flown" rather than a specific hull
        (see docs/SAVE_SYSTEM.md), so without this a new ship would
        silently inherit the old one's mounted outfits for free just
        because their slot ids happen to match - it should start bare,
        with those outfits back in your spares to reinstall."""
        cost = get_ship_type(self.story, ship_type_id).get("cost", 0)
        self.player.possessions.spend(cost)
        self.player.possessions.uninstall_all_outfits()
        self.player.possessions.add_ship(ship_type_id)
        if self.on_ship_purchased:
            self.on_ship_purchased(ship_type_id)

    def _first_selectable_option(self, options):
        """Index of the first option _option_blocked_reason doesn't block -
        used whenever the selection needs to (re)start (opening a
        conversation, arriving at a new node) so it's never pre-highlighted
        on an option the player can't actually take."""
        for i, option in enumerate(options):
            if not self._option_blocked_reason(option):
                return i
        return 0  # every option blocked - nothing better to land on

    def _next_selectable_option(self, options, current, direction):
        """Index reached by moving `current` by `direction` (+1/-1, with
        wraparound), skipping any option _option_blocked_reason blocks -
        the cursor should never be able to land on (and thus Enter-confirm)
        one, matching how a blocked option is drawn (dim, not selectable)."""
        index = current
        for _ in range(len(options)):
            index = (index + direction) % len(options)
            if not self._option_blocked_reason(options[index]):
                return index
        return current  # every option blocked - stay put

    def _targetable_people(self):
        """NPCs plus any visiting AI pilots currently in this location -
        anyone the player can target with []/talk to with T. self.npcs holds
        Character wrappers (see _build_local_character); self.visitors are
        already bare Person objects (the *same* Character.person a visiting
        pilot's AIShip-successor tracks in SpaceScreen.ai_ships - never
        wrapped a second time here)."""
        return [character.person for character in self.npcs] + self.visitors

    def _cycle_npc_target(self, direction=1):
        """Cycle through targetable NPCs and visiting pilots - direction=1
        for ], -1 for [."""
        people = self._targetable_people()
        if not people:
            return
        if self.current_npc_target is None:
            self.current_npc_target = 0
        else:
            self.current_npc_target = (self.current_npc_target + direction) % len(people)

    def _get_npc_target(self):
        """Get the currently targeted NPC or visiting pilot, if any."""
        people = self._targetable_people()
        if self.current_npc_target is None or self.current_npc_target >= len(people):
            return None
        return people[self.current_npc_target]

    def _select_person_target_at(self, world_x, world_y):
        """Target whichever targetable person (see _targetable_people)
        world_x/world_y falls within (closest one wins on overlap) - the
        click-to-target counterpart to cycling with []. Mirrors
        SpaceScreen._select_target_at, but over people on foot instead of
        ships/landables, and with a fixed click radius since Person has no
        drawn "size" of its own."""
        people = self._targetable_people()
        best_index, best_dist = None, None
        for i, person in enumerate(people):
            distance = person.get_distance(world_x, world_y)
            if distance <= 32 and (best_dist is None or distance < best_dist):
                best_index, best_dist = i, distance
        if best_index is not None:
            self.current_npc_target = best_index

    def _closest_person_in_range(self):
        """The closest targetable person within talk_range of the player, or
        None. This is deliberately independent of current_npc_target/
        _get_npc_target (manual []/click targeting) - walking up to someone
        no longer targets them, it just makes them talkable: T always talks
        to whoever this returns, and draw() labels their name/role above
        their head, regardless of what (if anything) is manually targeted."""
        in_range = [person for person in self._targetable_people() if person.get_distance(self.player.x, self.player.y) <= self.talk_range]
        if not in_range:
            return None
        return min(in_range, key=lambda person: person.get_distance(self.player.x, self.player.y))

    def _role_label(self, person):
        """Human-readable role for a name/role label (e.g. "outfitter" ->
        "Outfitter"), or None if this person has no role (e.g. the player -
        see Character.__init__, which is the only place person.role is set)."""
        role = getattr(person, "role", None)
        return role.replace("_", " ").title() if role else None

    def _draw_person_label(self, surface, person, ui_scale):
        """Floating name (and role, if any) centered just above person's
        head - used both for whoever's currently close enough to talk to
        (see _closest_person_in_range) and for a manually cycled/clicked
        target, so "who is this" is answered in-world without needing to
        check the info panel."""
        anchor_x, anchor_y = to_screen(person.x, person.y - self.LABEL_HEIGHT_ABOVE)
        bottom_y = anchor_y
        role_label = self._role_label(person)
        if role_label:
            font_role = get_font(int(13 * ui_scale))
            # Not GRAY (100,100,100) - too low-contrast to read at this
            # small size against the varied floor/wall colors behind it.
            role_surf = font_role.render(role_label, True, (210, 210, 225))
            role_rect = role_surf.get_rect(midbottom=(anchor_x, bottom_y))
            surface.blit(role_surf, role_rect)
            bottom_y = role_rect.top - 1
        font_name = get_font(int(16 * ui_scale))
        name_surf = font_name.render(person.name, True, WHITE)
        name_rect = name_surf.get_rect(midbottom=(anchor_x, bottom_y))
        surface.blit(name_surf, name_rect)

    def update(self):
        """Full update for the active/foreground location: player movement,
        camera, and NPCs. Only call this for whichever location the player
        is actually standing in right now - use update_physics() instead
        for every other cached location, so it keeps simulating in the
        background without moving the player's body (they're not there)
        or fighting the camera for whichever screen actually is active."""
        if not self.active_dialogue:
            keys = pygame.key.get_pressed()
            self._handle_movement(keys)
        self.update_camera()
        self.update_physics()

    def update_physics(self):
        """Advance just the NPCs - safe to call on a location that isn't
        the active screen. Paused while a conversation is open here
        (active_dialogue) - talking to one NPC shouldn't leave every other
        NPC in the room still visibly wandering around, any more than the
        player's own movement does. Other cached locations never have a
        conversation open, so this only ever actually pauses the active one."""
        if self.active_dialogue:
            return
        for character in self.npcs:
            character.update()

    def draw(self, surface):
        """Draw location from config."""
        surface.fill(self.bg_color)
        scale = get_scale()

        # Walkable floor - one rect per room/hallway in the culture's floor_color,
        # so each reads as distinct from the surrounding wall_color fill
        for room in self.rooms:
            fx, fy, fw, fh = room["rect"]
            x1, y1 = to_screen(fx, fy)
            x2, y2 = to_screen(fx + fw, fy + fh)
            pygame.draw.rect(surface, self.floor_color, (x1, y1, x2 - x1, y2 - y1))
        if self.rooms:
            font_room_label = pygame.font.Font(None, max(10, int(16 * scale)))
            for room in self.rooms:
                if not room["label"]:
                    continue
                fx, fy, fw, fh = room["rect"]
                label_pos = to_screen(fx + 10, fy + 8)
                label_surf = font_room_label.render(room["label"], True, (200, 200, 210))
                surface.blit(label_surf, label_pos)

        # Draw windows/details from config - flat wall decoration, drawn
        # before structures/people so it never has to compete for depth.
        for detail in self.config.get("details", []):
            detail_type = detail.get("type", "window")
            color = tuple(detail.get("color", [255, 255, 0]))

            if detail_type == "window":
                sx, sy, ex, ey, spacing = detail["start_x"], detail["start_y"], detail["end_x"], detail["end_y"], detail.get("spacing", 50)
                for x in range(sx, ex, spacing):
                    for y in range(sy, ey, spacing):
                        px, py = to_screen(x, y)
                        pygame.draw.rect(surface, color, (px, py, 15, 15))

        # Portal pads - flat floor rings, one per doorway out of this
        # location (see self.portals). Ground-level decoration, not a 3D
        # object with height, so it's drawn here with the floor/windows -
        # unconditionally *before* the structures/NPCs/player depth-sorted
        # pass below - rather than in that pass, so a portal never visually
        # sits on top of someone standing on it just because their feet
        # happen to have a lower Y (a portal at the *bottom* of a room, a
        # very common layout, would otherwise almost always win that sort
        # against anyone standing on it). Brightens once the player is
        # close enough for L to actually use it, so proximity isn't a
        # guessing game.
        active_portal = self._nearby_portal()
        font_portal_label = pygame.font.Font(None, max(10, int(15 * scale)))
        for portal in self.portals:
            px, py = to_screen(portal["x"], portal["y"])
            pad_w, pad_h = max(2, int(28 * scale)), max(1, int(10 * scale))
            pad_rect = pygame.Rect(0, 0, pad_w, pad_h)
            pad_rect.center = (px, py)
            is_active = portal is active_portal
            fill_color = (180, 255, 210) if is_active else (100, 255, 150)
            ring_color = YELLOW if is_active else (0, 255, 100)
            pygame.draw.ellipse(surface, fill_color, pad_rect)
            pygame.draw.ellipse(surface, ring_color, pad_rect, max(1, int(2 * scale)))

            # Destination label, always visible (not just in range) - same
            # idea as room labels above - so a single-destination portal's
            # menu-free L press is never a guess about where it leads.
            label_surf = font_portal_label.render(self._portal_label(portal), True, ring_color)
            label_rect = label_surf.get_rect(midtop=(px, pad_rect.bottom + 2))
            surface.blit(label_surf, label_rect)

        # Structures, NPCs, visiting pilots, and the player all have real
        # height and can occlude one another, so they're drawn together in
        # a single back-to-front pass (painter's algorithm) sorted by each
        # one's own ground-level depth, rather than as separate fixed
        # layers - otherwise a person standing "in front of" a tall
        # building (closer to the camera, larger depth) would still be
        # drawn behind it just because structures used to be one earlier,
        # unconditional loop.
        drawables = [(self._structure_depth(structure), self._make_structure_drawer(structure, scale)) for structure in self.structures]
        drawables += [(character.person.y, character.person.draw) for character in self.npcs]
        drawables += [(visitor.y, visitor.draw) for visitor in self.visitors]
        drawables.append((self.player.y, self.player.draw))
        drawables.sort(key=lambda item: item[0])
        for _, draw_fn in drawables:
            draw_fn(surface)

        # Highlight the manually targeted NPC (see _cycle_npc_target/
        # _select_person_target_at - unrelated to who's talkable right now)
        # and float a name/role label over both it and whoever's closest
        # enough to actually talk to (see _closest_person_in_range) - the
        # same person, most of the time, but not always (e.g. you cycled
        # target to someone across the room).
        target_npc = self._get_npc_target()
        closest_npc = self._closest_person_in_range()
        if target_npc:
            draw_target_brackets(surface, target_npc.x, target_npc.y, size=25)
        label_ui_scale = get_ui_scale()
        labeled = set()
        if closest_npc:
            self._draw_person_label(surface, closest_npc, label_ui_scale)
            labeled.add(id(closest_npc))
        if target_npc and id(target_npc) not in labeled:
            self._draw_person_label(surface, target_npc, label_ui_scale)

        # Debug markers
        if constants.DEBUG_MODE:
            draw_debug_marker(surface, self.player.x, self.player.y, 10)
            for character in self.npcs:
                draw_debug_marker(surface, character.person.x, character.person.y, 8)
            for visitor in self.visitors:
                draw_debug_marker(surface, visitor.x, visitor.y, 8)
            for fx, fy, fw, fh in self.building_footprints:
                x1, y1 = to_screen(fx, fy)
                x2, y2 = to_screen(fx + fw, fy + fh)
                pygame.draw.rect(surface, GREEN, (x1, y1, x2 - x1, y2 - y1), 1)

        # Draw UI
        ui_scale = get_ui_scale()
        control_margin = int(10 * ui_scale)

        # Top-center title pane - same glass-panel look as the Controls/
        # status panes, anchored to the real screen edge like they are.
        font_label = get_font(int(24 * ui_scale))
        label_text = font_label.render(self.ui_label, True, WHITE)
        label_pad_x, label_pad_y = int(16 * ui_scale), int(8 * ui_scale)
        label_rect = pygame.Rect(0, 0, label_text.get_width() + label_pad_x * 2, label_text.get_height() + label_pad_y * 2)
        label_rect.midtop = (utils.screen_width // 2, control_margin)
        draw_glass_panel(surface, label_rect, ui_scale)
        surface.blit(label_text, (label_rect.centerx - label_text.get_width() // 2, label_rect.y + label_pad_y))

        # Top-right targeting/credits pane (see draw_info_panel) - same
        # design as SpaceScreen's own info panel, minus the speed/mode
        # lines that don't apply while on foot.
        info_lines = [(f"Credits: {self.player.possessions.credits}", (255, 220, 100))]
        if target_npc:
            distance = target_npc.get_distance(self.player.x, self.player.y)
            info_lines.append(("Target:", GREEN))
            info_lines.append((f"  Distance: {distance:.0f}", GREEN))
            info_lines.append((f"  {target_npc.name}", GREEN))
            target_role = self._role_label(target_npc)
            if target_role:
                info_lines.append((f"  {target_role}", GREEN))
        else:
            info_lines.append(("Target: None", GRAY))
        info_rect = draw_info_panel(surface, info_lines, ui_scale, (utils.screen_width - control_margin, control_margin))

        # Top-left control-reference pane - same design as SpaceScreen's
        # (see draw_controls_pane), with the controls that apply here.
        # Anchored to the real screen corner (not get_ui_offset()'s
        # letterboxed 800x600 canvas), matching SpaceScreen's own pane.
        help_items = [
            ("ESC", "Pause"),
            ("WASD/Arrows", "Move"),
            ("]", "Next Target"),
            ("[", "Previous Target"),
            ("Click", "Target Person"),
            ("P", "View Possessions"),
        ]
        controls_rect = draw_controls_pane(surface, control_margin, control_margin, "Controls", help_items, ui_scale)

        # Bottom-center status pane (see draw_status_pane) - entrance and
        # talk prompts are independent of each other and can both be true
        # at once, so they stack as separate lines in one panel.
        status_lines = []
        if active_portal:
            status_lines.append(("Press L to enter portal", GREEN))
        if closest_npc:
            status_lines.append((f"Press T to talk to {closest_npc.name}", GREEN))
        status_rect = draw_status_pane(surface, status_lines, ui_scale)

        # Cached for handle_input()'s mouse-click targeting, so a click on
        # any of these panels doesn't also register as a click-to-target in
        # the world behind them (see SpaceScreen._hud_click_rects).
        self._hud_click_rects = [rect for rect in (label_rect, info_rect, controls_rect, status_rect) if rect]

        # Draw active dialogue box on top of everything
        if self.active_dialogue:
            self.active_dialogue.draw(surface, ui_scale, status_fn=self._option_blocked_reason)

    def _draw_culture_building(self, surface, structure, building_type_id, scale):
        """Draw a building whose hull/window colors come from its type's culture -
        fully config-driven metal (hull) + glass (windows) material palette.

        `structure` supplies only position ("x"/"y"); shape, size, and window
        layout all come from the building_type. Anchor point varies by shape:
        "rect" uses top-left (matching the generic rect structures above),
        "circle" uses center, "polygon" is whatever the type's local_points
        were authored relative to (typically ground level).
        """
        building_type = get_building_type(self.story, building_type_id)
        metal_color = tuple(building_type.get("color", (150, 150, 150)))
        glass_color = tuple(building_type.get("window_color", (255, 255, 0)))
        anchor_x, anchor_y = structure["x"], structure["y"]
        shape = building_type.get("shape", "rect")

        if shape == "circle":
            radius = building_type.get("radius", 50)
            cx, cy = to_screen(anchor_x, anchor_y)
            pygame.draw.circle(surface, metal_color, (cx, cy), max(1, int(radius * scale)))
        elif shape == "polygon":
            local_points = building_type.get("local_points", [])
            screen_points = [to_screen(anchor_x + lx, anchor_y + ly) for lx, ly in local_points]
            if len(screen_points) >= 3:
                pygame.draw.polygon(surface, metal_color, screen_points)
        else:  # rect
            width = building_type.get("width", 100)
            height = building_type.get("height", 100)
            x1, y1 = to_screen(anchor_x, anchor_y)
            x2, y2 = to_screen(anchor_x + width, anchor_y + height)
            pygame.draw.rect(surface, metal_color, (x1, y1, x2 - x1, y2 - y1))

        window_shape = building_type.get("window_shape", "rect")
        window_size = building_type.get("window_size", 12)
        half = max(1, int(window_size * scale / 2))
        for wx, wy in building_type.get("windows", []):
            px, py = to_screen(anchor_x + wx, anchor_y + wy)
            if window_shape == "circle":
                pygame.draw.circle(surface, glass_color, (px, py), half)
            else:
                pygame.draw.rect(surface, glass_color, (px - half, py - half, half * 2, half * 2))

    def _building_footprint(self, structure):
        """World-space collision box (fx, fy, fw, fh) for one structure, or
        None if it isn't a building (decorative circle/rect/polygon terrain,
        e.g. moon rocks/craters, has no "building_type") or its building_type
        configures no "footprint".

        Deliberately just the base, not the full drawn silhouette: a tall
        spire's upper floors are pure occluding art (a 2D building is drawn
        "extruded" upward from ground level via negative local y - see
        _draw_culture_building), so making the whole visual height solid
        would block a player from ever standing near the far side even
        though the painter's-algorithm sort in draw() already draws them
        behind it correctly. Sized and anchored from building_type's own
        "footprint" (roughly square/city-block, not a sliver spanning the
        building's full height) rather than derived from width/height,
        since e.g. drossholt_tower is only 80 wide but 220 tall - a footprint
        that thin would make its base nearly impossible to walk around.

        Anchor point matches _structure_depth's/_draw_culture_building's own
        per-shape convention: "rect" is authored top-left, so ground level is
        its bottom edge (anchor + height); "circle"/"polygon" are authored
        with ground level at the anchor itself.
        """
        building_type_id = structure.get("building_type")
        if not building_type_id:
            return None
        building_type = get_building_type(self.story, building_type_id)
        footprint = building_type.get("footprint")
        if not footprint:
            return None
        fw, fd = footprint.get("width", 100), footprint.get("depth", 100)
        if building_type.get("shape", "rect") == "rect":
            ground_x = structure["x"] + building_type.get("width", 100) / 2
            ground_y = structure["y"] + building_type.get("height", 100)
        else:  # circle: center is ground level; polygon: authored at ground level
            ground_x, ground_y = structure["x"], structure["y"]
        return (ground_x - fw / 2, ground_y - fd / 2, fw, fd)

    def _structure_depth(self, structure):
        """Y-sort key for a structure: the ground-level depth a walking
        person's own y (feet position) should be compared against in
        draw()'s back-to-front pass, so tall features occlude correctly
        against whoever's standing in front of or behind them."""
        building_type_id = structure.get("building_type")
        if building_type_id:
            building_type = get_building_type(self.story, building_type_id)
            if building_type.get("shape", "rect") == "rect":
                return structure["y"] + building_type.get("height", 100)
            return structure["y"]  # circle: center; polygon: ground-level anchor

        struct_type = structure.get("type", "rect")
        if struct_type == "rect":
            return structure["y"] + structure["height"]
        if struct_type == "polygon":
            return max(p["y"] for p in structure["points"])
        return structure["y"]  # circle

    def _make_structure_drawer(self, structure, scale):
        """Bind one structure's draw call so draw() can sort it alongside
        NPCs/visitors/the player and invoke it in back-to-front order."""
        building_type_id = structure.get("building_type")
        if building_type_id:
            return lambda surface: self._draw_culture_building(surface, structure, building_type_id, scale)

        struct_type = structure.get("type", "rect")
        color = tuple(structure.get("color", [150, 150, 150]))

        if struct_type == "rect":
            x, y, w, h = structure["x"], structure["y"], structure["width"], structure["height"]

            def draw_rect(surface):
                x1, y1 = to_screen(x, y)
                x2, y2 = to_screen(x + w, y + h)
                pygame.draw.rect(surface, color, (x1, y1, x2 - x1, y2 - y1))
            return draw_rect

        if struct_type == "circle":
            x, y, r = structure["x"], structure["y"], structure.get("radius", 50)

            def draw_circle(surface):
                cx, cy = to_screen(x, y)
                pygame.draw.circle(surface, color, (cx, cy), max(1, int(r * scale)))
            return draw_circle

        if struct_type == "polygon":
            points = [(p["x"], p["y"]) for p in structure["points"]]

            def draw_polygon(surface):
                screen_points = [to_screen(px, py) for px, py in points]
                pygame.draw.polygon(surface, color, screen_points)
            return draw_polygon

        return lambda surface: None

    def handle_input(self, events):
        """Override for area-specific input (dialogue, etc.)"""
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.active_dialogue and not any(rect.collidepoint(event.pos) for rect in self._hud_click_rects):
                    self._select_person_target_at(*to_world(*event.pos))
                continue

            if event.type != pygame.KEYDOWN:
                continue

            if self.active_dialogue:
                # While talking, input drives the dialogue box instead of movement
                options = self.active_dialogue.current_options()
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.active_dialogue.selected_option = self._next_selectable_option(options, self.active_dialogue.selected_option, -1)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.active_dialogue.selected_option = self._next_selectable_option(options, self.active_dialogue.selected_option, 1)
                elif event.key == pygame.K_RETURN:
                    option = options[self.active_dialogue.selected_option]
                    if not self._option_blocked_reason(option):
                        action = option.get("action")
                        if action:
                            self._apply_dialogue_action(action)
                        if self.active_dialogue.choose(self.active_dialogue.selected_option):
                            self.active_dialogue = None
                        else:
                            self.active_dialogue.selected_option = self._first_selectable_option(self.active_dialogue.current_options())
                elif event.key == pygame.K_ESCAPE:
                    self.active_dialogue = None
                continue

            if event.key == pygame.K_l:
                # Only allow exit if near a portal (see self.portals) -
                # whichever one is closest, if the player somehow got two
                # in range at once.
                portal = self._nearby_portal()
                if portal:
                    self._active_portal = portal
                    options = self.get_exit_options(portal)
                    available = self.get_available_exit_options(portal)
                    if options and len(available) == len(options) and len(options) == 1:
                        # Exactly one destination, and it's actually usable
                        # right now - go straight there.
                        return "exit" if options[0] == "ship" else f"exit_to:{options[0]}"
                    elif options:
                        # More than one destination, or the only one isn't
                        # usable yet (e.g. no ship docked) - open the menu
                        # either way, so an unusable option is still visible
                        # with its reason instead of L silently doing nothing.
                        return "exit_menu"
            elif event.key == pygame.K_RIGHTBRACKET:
                self._cycle_npc_target(1)
            elif event.key == pygame.K_LEFTBRACKET:
                self._cycle_npc_target(-1)
            elif event.key == pygame.K_t:
                # T always talks to whoever's closest in range (see
                # _closest_person_in_range) - independent of any manually
                # cycled/clicked target (current_npc_target), which is only
                # for viewing info at a distance now.
                nearest = self._closest_person_in_range()
                if nearest:
                    # getattr, not nearest.shop: a visiting AI pilot (see
                    # Character.for_ai_pilot) never gets a .shop attribute at
                    # all, unlike a local NPC (_build_local_character) - only
                    # the latter can ever be a shop.
                    if getattr(nearest, "shop", None):
                        self.active_shop = nearest.shop
                        return "shop"
                    # Always start a fresh conversation at the root node -
                    # otherwise leaving mid-tree (ESC) and talking again
                    # would silently resume wherever it was left off.
                    nearest.dialogue.current_node = nearest.dialogue.root
                    nearest.dialogue.selected_option = self._first_selectable_option(nearest.dialogue.current_options())
                    self.active_dialogue = nearest.dialogue
            elif event.key == pygame.K_p:
                return "possessions"
            elif event.key == pygame.K_ESCAPE:
                return "pause"
        return None

    def _handle_movement(self, keys, can_move_func=None):
        """Generalized movement input handling"""
        new_x = self.player.x
        new_y = self.player.y

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_y += self.speed
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            new_x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            new_x += self.speed

        # Check bounds
        can_move = can_move_func(new_x, new_y) if can_move_func else self.can_move_to(new_x, new_y)

        if can_move:
            self.player.x = new_x
            self.player.y = new_y

    def can_move_to(self, x, y):
        """Whether (x, y) is inside this location's walkable area - the
        default bounds check _handle_movement uses for the player, exposed
        so anyone else moving a body around this location (e.g. DockRoutine
        walking a visiting pilot to an NPC) can respect the same walls
        instead of clipping straight through them."""
        if any(fx <= x <= fx + fw and fy <= y <= fy + fh for fx, fy, fw, fh in self.building_footprints):
            return False
        if self.rooms:
            # Inclusive bounds (<=), not strict (<) - two touching rooms
            # (e.g. Entrance Hall/Bar sharing the line y=300) must both
            # accept landing exactly on that shared boundary, or a step
            # that lands exactly there (all coordinates here are integers
            # and speed is a fixed 3, so this isn't a rare float fluke -
            # roughly a third of all positions hit it) is invalid in both
            # rooms at once and whoever's moving gets stuck one step short
            # of an invisible wall, unable to cross at all.
            return any(fx <= x <= fx + fw and fy <= y <= fy + fh for fx, fy, fw, fh in (room["rect"] for room in self.rooms))
        return 0 < x < self.world_width and 0 < y < self.world_height

    def update_camera(self):
        """Update global camera to follow player"""
        set_camera_offset(self.player.x - GAME_WIDTH // 2, self.player.y - GAME_HEIGHT // 2)

    def get_state(self):
        """Save player position state for locations"""
        return {
            "player": {
                "x": self.player.x,
                "y": self.player.y
            },
            "possessions": self.player.possessions.get_state(),
        }

    def restore_state(self, state):
        """Restore player position state for locations"""
        if not state:
            return
        if "player" in state:
            player_state = state["player"]
            self.player.x = player_state.get("x", self.player.x)
            self.player.y = player_state.get("y", self.player.y)
        if "possessions" in state:
            self.player.possessions.restore_from(state["possessions"])
