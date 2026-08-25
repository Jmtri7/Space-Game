"""Configurable location for station, moon city, and moon wilderness."""
import pygame
import math
import game.constants as constants
from game.constants import GAME_WIDTH, GAME_HEIGHT, WHITE
from game.utils import get_scale, load_json, to_screen, draw_debug_marker, draw_target_brackets, get_ui_scale, get_ui_offset, set_camera_offset, get_building_type, get_culture, get_ship_type
from game.screens.screen_base import ScreenBase
from game.world.character import Character
from game.world.person import Person
from game.world.dialogue import Dialogue
from game.world.player_character import PlayerCharacter


class LocationScreen(ScreenBase):
    """Configurable location for station, moon city, and moon wilderness. Loads layout and NPCs from config."""
    def __init__(self, config_file=None, config_data=None, world_width=1600, world_height=1600, pilot_name="", story="default", player_possessions=None, on_ship_purchased=None):
        self.story = story  # which story's config/building_types.json etc. to resolve against
        # Load config from file or use inline data
        if config_data is not None:
            self.config = config_data
            self.config_file = None
        else:
            self.config_file = config_file
            self.config = load_json(config_file) or {}
        entrance_cfg = self.config.get("entrance", {})
        start_x = entrance_cfg.get("x", world_width // 2)
        start_y = entrance_cfg.get("y", world_height - 80)

        # Initialize ScreenBase
        super().__init__(pilot_name=pilot_name)

        # Initialize walkable area properties
        # player_possessions, if given, is the player's one real Possessions
        # object (see SpaceScreen.get_interior_screen) - shared by reference
        # so a purchase made here is instantly visible everywhere else the
        # player's possessions are read (space HUD, other interiors, saves).
        # Falls back to a fresh empty one (via Person's own default) when
        # constructed standalone, e.g. in tests.
        self.player = PlayerCharacter(start_x, start_y, name=pilot_name, possessions=player_possessions)
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
        self.speed = 3
        self.entrance_x = start_x  # Where player enters
        self.entrance_y = start_y
        self.entrance_range = 50  # How close to entrance to exit

        # Where the entrance leads: any sibling interior keys (within the
        # same landable's "interiors" dict) reachable on foot from here,
        # plus whether leaving also offers "back to the ship" at all. A
        # location with no connected_locations and the return_to_ship
        # default of True behaves exactly as before - a single, immediate
        # exit back to space.
        self.connected_locations = self.config.get("connected_locations", [])
        self.return_to_ship = self.config.get("return_to_ship", True)

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
        self.npcs_config = self.config.get("npcs", [])
        self.npcs = [self._build_local_character(cfg) for cfg in self.npcs_config]
        self.current_npc_target = None  # For T key targeting
        self.active_dialogue = None  # Set to an NPC's Dialogue while talking

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
        person = Person(cfg.get("x", 0), cfg.get("y", 0), name=cfg.get("name", "NPC"))
        dialogue_tree = cfg.get("dialogue_tree")
        if dialogue_tree:
            person.dialogue = Dialogue(person.name, dialogue_tree["nodes"], root=dialogue_tree.get("root", "start"))
        else:
            person.dialogue = Dialogue.from_flat(person.name, cfg.get("greeting", "Hello!"), cfg.get("dialogue_options") or ["Talk", "Leave"])
        return Character(person, role=cfg.get("role", "resident"))

    def get_exit_options(self):
        """Ordered destinations available through this location's exit:
        each connected_locations key (in config order), then "ship" last
        if return_to_ship allows it. Used both to drive the player's exit
        menu and by AI routines (see DockRoutine) choosing where to go
        next - same list, same meaning, for both."""
        options = list(self.connected_locations)
        if self.return_to_ship:
            options.append("ship")
        return options

    @property
    def ship_available(self):
        """Whether the player actually has a ship to board right now - not
        just whether this location's exit is configured to offer one.
        False until a "buy_ship:" dialogue action has run (see
        _apply_dialogue_action)."""
        return bool(self.player.possessions.owned_ships)

    def get_available_exit_options(self):
        """get_exit_options() minus "ship" when there's no ship to actually
        board yet - used to decide whether L can exit immediately or needs
        to open ExitMenu so the player can see *why* nothing happened."""
        options = self.get_exit_options()
        if not self.ship_available:
            options = [option for option in options if option != "ship"]
        return options

    def get_exit_disabled_reasons(self):
        """{key: reason} for exit options this location's config offers but
        aren't usable right now - currently just "ship" with no ship owned
        yet. Passed to ExitMenu so it's shown, dim, instead of silently
        missing."""
        if "ship" in self.get_exit_options() and not self.ship_available:
            return {"ship": "no ship docked here"}
        return {}

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
            ship_type_id = action.split(":", 1)[1]
            cost = get_ship_type(self.story, ship_type_id).get("cost", 0)
            self.player.possessions.spend(cost)
            self.player.possessions.add_ship(ship_type_id)
            if self.on_ship_purchased:
                self.on_ship_purchased(ship_type_id)
        elif action == "take_loan":
            loan_amount = get_ship_type(self.story, "shuttle").get("cost", 0)
            self.player.possessions.take_loan("Station Credit Union", loan_amount)

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
        anyone the player can target/talk to with T/Enter. self.npcs holds
        Character wrappers (see _build_local_character); self.visitors are
        already bare Person objects (the *same* Character.person a visiting
        pilot's AIShip-successor tracks in SpaceScreen.ai_ships - never
        wrapped a second time here)."""
        return [character.person for character in self.npcs] + self.visitors

    def _cycle_npc_target(self, direction=1):
        """Cycle through targetable NPCs and visiting pilots - direction=1
        for T/], -1 for [."""
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

        # Draw structures from config
        for structure in self.structures:
            building_type_id = structure.get("building_type")
            if building_type_id:
                self._draw_culture_building(surface, structure, building_type_id, scale)
                continue

            struct_type = structure.get("type", "rect")
            color = tuple(structure.get("color", [150, 150, 150]))

            if struct_type == "rect":
                x, y, w, h = structure["x"], structure["y"], structure["width"], structure["height"]
                x1, y1 = to_screen(x, y)
                x2, y2 = to_screen(x + w, y + h)
                pygame.draw.rect(surface, color, (x1, y1, x2 - x1, y2 - y1))

            elif struct_type == "circle":
                x, y, r = structure["x"], structure["y"], structure.get("radius", 50)
                cx, cy = to_screen(x, y)
                pygame.draw.circle(surface, color, (cx, cy), max(1, int(r * scale)))

            elif struct_type == "polygon":
                points = [(p["x"], p["y"]) for p in structure["points"]]
                screen_points = [to_screen(x, y) for x, y in points]
                pygame.draw.polygon(surface, color, screen_points)

        # Draw windows/details from config
        for detail in self.config.get("details", []):
            detail_type = detail.get("type", "window")
            color = tuple(detail.get("color", [255, 255, 0]))

            if detail_type == "window":
                sx, sy, ex, ey, spacing = detail["start_x"], detail["start_y"], detail["end_x"], detail["end_y"], detail.get("spacing", 50)
                for x in range(sx, ex, spacing):
                    for y in range(sy, ey, spacing):
                        px, py = to_screen(x, y)
                        pygame.draw.rect(surface, color, (px, py, 15, 15))

        # Draw NPCs
        for character in self.npcs:
            character.person.draw(surface)

        # Draw visiting AI pilots (see self.visitors)
        for visitor in self.visitors:
            visitor.draw(surface)

        # Highlight and label the targeted NPC
        target_npc = self._get_npc_target()
        if target_npc:
            draw_target_brackets(surface, target_npc.x, target_npc.y, size=25)

        # Draw entrance marker - a flat floor ring rather than a tall ball,
        # so a character standing on it (feet at its center) doesn't get
        # visually swallowed by it.
        ex, ey = to_screen(self.entrance_x, self.entrance_y)
        pad_w, pad_h = max(2, int(28 * scale)), max(1, int(10 * scale))
        pad_rect = pygame.Rect(0, 0, pad_w, pad_h)
        pad_rect.center = (ex, ey)
        pygame.draw.ellipse(surface, (100, 255, 150), pad_rect)
        pygame.draw.ellipse(surface, (0, 255, 100), pad_rect, max(1, int(2 * scale)))

        # Draw player
        self.player.draw(surface)

        # Debug markers
        if constants.DEBUG_MODE:
            draw_debug_marker(surface, self.player.x, self.player.y, 10)
            for character in self.npcs:
                draw_debug_marker(surface, character.person.x, character.person.y, 8)
            for visitor in self.visitors:
                draw_debug_marker(surface, visitor.x, visitor.y, 8)

        # Draw UI
        ui_scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()
        self.draw_ui_text(surface, self.ui_label, scale=ui_scale)
        if target_npc:
            font_target = pygame.font.Font(None, int(20 * ui_scale))
            target_text = font_target.render(f"Target: {target_npc.name}", True, (100, 255, 100))
            surface.blit(target_text, (int(offset_x + 20), int(offset_y + 45)))

        font_credits = pygame.font.Font(None, int(24 * ui_scale))
        credits_text = font_credits.render(f"Credits: {self.player.possessions.credits}", True, (255, 220, 100))
        surface.blit(credits_text, (int(offset_x + surface.get_width() - credits_text.get_width() - 20), int(offset_y + 20)))

        font_help = pygame.font.Font(None, int(16 * ui_scale))
        help_text = font_help.render("WASD: move, T/[/]: target NPC, Enter: talk, L: exit, P: possessions, ESC: pause", True, WHITE)
        help_x = int(offset_x + surface.get_width() // 2 - help_text.get_width() // 2)
        help_y = int(offset_y + surface.get_height() - 30)
        surface.blit(help_text, (help_x, help_y))

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

    def handle_input(self, events):
        """Override for area-specific input (dialogue, etc.)"""
        for event in events:
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
                # Only allow exit if near entrance
                dist_to_entrance = math.sqrt((self.player.x - self.entrance_x) ** 2 + (self.player.y - self.entrance_y) ** 2)
                if dist_to_entrance <= self.entrance_range:
                    options = self.get_exit_options()
                    available = self.get_available_exit_options()
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
            elif event.key in (pygame.K_t, pygame.K_RIGHTBRACKET):
                self._cycle_npc_target(1)
            elif event.key == pygame.K_LEFTBRACKET:
                self._cycle_npc_target(-1)
            elif event.key == pygame.K_RETURN:
                target_npc = self._get_npc_target()
                if target_npc:
                    # Always start a fresh conversation at the root node -
                    # otherwise leaving mid-tree (ESC) and talking again
                    # would silently resume wherever it was left off.
                    target_npc.dialogue.current_node = target_npc.dialogue.root
                    target_npc.dialogue.selected_option = self._first_selectable_option(target_npc.dialogue.current_options())
                    self.active_dialogue = target_npc.dialogue
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
        if can_move_func:
            can_move = can_move_func(new_x, new_y)
        elif self.rooms:
            can_move = any(fx < new_x < fx + fw and fy < new_y < fy + fh for fx, fy, fw, fh in (room["rect"] for room in self.rooms))
        else:
            can_move = (0 < new_x < self.world_width and 0 < new_y < self.world_height)

        if can_move:
            self.player.x = new_x
            self.player.y = new_y

    def update_camera(self):
        """Update global camera to follow player"""
        set_camera_offset(self.player.x - GAME_WIDTH // 2, self.player.y - GAME_HEIGHT // 2)

    def draw_ui_text(self, surface, text, scale=None):
        """Draw UI text that stays on screen (not camera-affected)"""
        if scale is None:
            scale = get_ui_scale()
        offset_x, offset_y = get_ui_offset()
        font = pygame.font.Font(None, int(24 * scale))
        ui_text = font.render(text, True, WHITE)
        surface.blit(ui_text, (int(offset_x + 20), int(offset_y + 20)))

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
