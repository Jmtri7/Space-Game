"""LocationScreen — core lifecycle, input, the fixed-step update, draw and
save/restore. Cohesive method clusters live in sibling mixin modules."""
from game.screens.location_screen._defs import *  # noqa: F401,F403
from game.screens.location_screen.portals import _PortalsMixin
from game.screens.location_screen.commerce import _CommerceMixin
from game.screens.location_screen.dialogue import _DialogueMixin
from game.screens.location_screen.targeting import _TargetingMixin
from game.screens.location_screen.npcs import _NpcsMixin
from game.screens.location_screen.decor import _DecorMixin
from game.screens.location_screen.structures import _StructuresMixin
from game.screens.location_screen.movement import _MovementMixin


class LocationScreen(_PortalsMixin, _CommerceMixin, _DialogueMixin, _TargetingMixin, _NpcsMixin, _DecorMixin, _StructuresMixin, _MovementMixin, ScreenBase):
    """Configurable location for station, moon city, and moon wilderness. Loads layout and NPCs from config."""

    # Game-space units above a person's feet (self.y) their floating name/
    # role label is anchored to - clears the head/helmet drawn by Person.draw().
    LABEL_HEIGHT_ABOVE = 42

    def __init__(self, config_file=None, config_data=None, world_width=1600, world_height=1600, pilot_name="", story="default", player_possessions=None, on_ship_purchased=None, on_ship_switched=None, location_labels=None):
        self.story = story  # which story's config/building_types.json etc. to resolve against
        # {interior_key: display label} for every sibling interior at the
        # same landing site (see SpaceScreen.get_interior_screen) - used only to
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
        # graphics.json "outfits" id the player's walking body wears, and
        # the fallback for any NPC that doesn't name its own (see
        # _build_local_character) - story.json's "default_outfit".
        self.default_outfit_id = get_story(story).get("default_outfit", "space_suit")
        self.player = PlayerCharacter(start_x, start_y, name=pilot_name, possessions=player_possessions, outfit=get_graphics_asset(self.story, "outfits", self.default_outfit_id))
        # Called with a ship_type_id right after a successful "buy_ship:"
        # dialogue action - lets SpaceScreen (which owns the real flyable
        # ship) configure it, without LocationScreen importing game.screens
        # (see get_interior_screen callable injection on AIShip for the
        # same one-directional-dependency idiom).
        self.on_ship_purchased = on_ship_purchased
        # Same one-directional hook as on_ship_purchased, for the ship
        # salesman's "Your Ships" tab switching which owned hull is flown
        # (see switch_ship).
        self.on_ship_switched = on_ship_switched
        # Which key in the landing site's interiors dict this is (e.g.
        # "dormitory", "default") - set by SpaceScreen.get_interior_screen;
        # None when constructed standalone (e.g. in tests).
        self.interior_key = None
        self.world_width = world_width
        self.world_height = world_height
        # On-foot pace, shared by the player and any AI pilot walking a
        # dock errand in this interior (DockRoutine reads self._location.speed
        # off this) - story.json's "walking_speed" overrides the default so
        # both always match.
        self.speed = get_story(story).get("walking_speed", constants.WALKING_SPEED)
        # Player-adjustable interior zoom (mouse wheel over open floor, see
        # handle_input). Its own range, independent of the Space View's -
        # story.json's "interior_camera_zoom"/"..._min"/"..._max" override the
        # constants. Remembered for the session and captured by get_state();
        # pushed to the shared camera by update_camera()/draw().
        _story_meta = get_story(story)
        self.camera_zoom_min = _story_meta.get("interior_camera_zoom_min", constants.INTERIOR_CAMERA_ZOOM_MIN)
        self.camera_zoom_max = _story_meta.get("interior_camera_zoom_max", constants.INTERIOR_CAMERA_ZOOM_MAX)
        self.camera_zoom = self._clamp_zoom(_story_meta.get("interior_camera_zoom", constants.INTERIOR_CAMERA_ZOOM))
        self.entrance_range = 35  # How close to a portal to use it
        self.talk_range = 60  # How close to an NPC/pilot to start a conversation
        # Cached by handle_input() when G opens the exit menu, so
        # get_exit_options()/get_available_exit_options()/
        # get_exit_disabled_reasons() (called later, from main.py, once the
        # menu is already up) act on the same portal the player actually
        # pressed G next to - the player can't move while the menu is open,
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
        # "seamless": true drops everything that visually chops the floor into
        # separate rooms - the room-name labels and the culture's
        # edge-emphasising interior_decoration (edge_veins / seam_rivets) - so
        # overlapping room polygons read as one open deck. Pair with
        # "space_backdrop" + a "floor_pattern" for a concourse that floats,
        # tiled, against the Space View starfield.
        self.seamless = bool(self.config.get("seamless"))
        # Each room is {"polygon": [(x, y), ...], "label": str or None} in world
        # space (see normalize_room - "rect" and "circle" configs are folded to
        # polygons on the way in). Movement is allowed anywhere in the union of
        # the room polygons, so overlapping polygons read as one connected
        # space and the whole station interior is a single walkable area. An
        # interior with no "rooms" list falls back to one margin-inset
        # rectangle, same as before rooms existed.
        self.rooms = []
        self.floor_color = None
        self.wall_trim_color = None
        # Cosmetic floor/wall decals (see normalize_decoration) - explicit
        # per-interior ones always, plus a per-culture generated pack layered
        # underneath them (see _build_culture_decorations).
        self.decorations = [normalize_decoration(d) for d in self.config.get("decorations", [])]
        # Lazily-built walkability raster for plan_path() - the walkable area
        # never changes during play, so it's built once on first use and kept.
        self._nav_grid = None
        if self.culture_id:
            culture = get_culture(self.story, self.culture_id)
            # An explicit background_color wins (a moon settlement keeps its
            # regolith grey); otherwise the wall fill is the culture's
            # resin-dark wall_color, so an enclosed station reads as walls.
            if "background_color" not in self.config:
                self.bg_color = tuple(culture.get("wall_color", self.bg_color))
            self.floor_color = tuple(culture.get("floor_color", self.bg_color))
            self.wall_trim_color = tuple(culture["wall_trim_color"]) if culture.get("wall_trim_color") else tuple(int(c * 0.6) for c in self.floor_color)
            rooms_cfg = self.config.get("rooms")
            if rooms_cfg:
                self.rooms = [normalize_room(room) for room in rooms_cfg]
            else:
                margin = self.config.get("wall_margin", 60)
                self.rooms = [normalize_room({"rect": [margin, margin, world_width - 2 * margin, world_height - 2 * margin]})]
            if not self.seamless:
                self.decorations = self._build_culture_decorations(culture) + self.decorations
        # Tessellated floor tiles (see _build_floor_pattern) - independent of a
        # culture, driven by the interior's optional "floor_pattern" spec.
        self._floor_tiles = self._build_floor_pattern()

        # Opt-in: render the interior over the space starfield instead of a
        # flat wall fill - a station concourse open to the void, its lit decks
        # floating against the same background as the Space View. Floor
        # polygons paint over the stars, so only the gaps between rooms show
        # through.
        self.star_field = StarField(
            seed=self.config.get("star_seed", 0),
            # A concourse over the void wants a visibly starry backdrop but not
            # a dense one - at min interior zoom the whole floor plan is on
            # screen and every star is a per-frame circle draw.
            stars_per_chunk_range=tuple(self.config.get("star_density", (26, 44))),
        ) if self.config.get("space_backdrop") else None

        # Static mission definitions for this story (missions.json) - needed
        # so a dialogue "start_mission:" / "abandon_mission:" action (see
        # apply_shared_actions) can look one up, e.g. a station guide's
        # offer to walk the player through the place. {} for a story with
        # no missions.json.
        self.missions_config = get_missions(story)
        # Full, unfiltered config for the flag/reputation-conditional
        # content (see game/world/content_gate.py). _apply_content_gates()
        # derives self.structures / self.building_footprints / self.npcs
        # from these against the player's current flags+standing, and is
        # re-run on every interior (re-)entry (arrive_from) so a beacon lit
        # or a faction mobilised actually changes what's here.
        self._structures_config = self.config.get("structures", [])
        self._npcs_config = self.config.get("npcs", [])
        self._apply_content_gates()
        self.current_npc_target = None  # For T key targeting
        self.active_dialogue = None  # Set to an NPC's Dialogue while talking
        self.active_shop = None  # Set to an NPC's shop config when "shop" is returned from handle_input
        self._pending_shop = None  # An NPC's shop stashed while their dialogue is open, for an "open_shop" option to hand off to
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

        # --- Message Log (shared with the Space View) ----------------------
        # possessions.message_log is one shared list (see Possessions) -
        # mission-stage messages and pilot hails written to it while flying
        # show up here too, and interior NPCs can add to it directly (see
        # _post_local_message / an NPC config's "ambient"). _refresh_messages()
        # watches it each frame and raises the banner + unread light when it
        # grows; the bottom-left panel (draw_message_log) renders it exactly
        # as SpaceScreen does.
        self._seen_message_count = len(self.player.possessions.message_log)
        self.message_log_scroll = 0
        self.message_alert_timer = 0
        # How many of the MESSAGE_ALERT_BLINKS unread pings have sounded for
        # the current alert - reset in _refresh_messages, advanced in update()
        # (active screen only; the timer itself counts down in update_physics).
        self._message_alert_pings_played = 0
        # True while there's an unread message (see _post_local_message)
        # the player hasn't clicked away yet - see
        # SpaceScreen._unread_alert_pinned's own comment (shared design; the
        # two screens keep independent state since a message can arrive
        # while either is the one on screen).
        self._unread_alert_pinned = False
        self.message_banner = None
        self.message_banner_timer = 0
        self._message_log_rect = None
        # Set by draw() each frame from draw_message_log's return - how many
        # lines the log can scroll past its visible window right now. Used by
        # handle_input to only count a wheel-scroll toward the
        # "scrolled_message_log" tutorial flag when there was actually
        # something to scroll.
        self._message_log_max_scroll = 0

    def _apply_content_gates(self):
        """(Re)derive the flag/reputation-conditional content from the raw
        config against the player's *current* flags + standing - the NPC
        roster, the solid structures, and their collision footprints (which
        invalidates the lazily-built nav grid so plan_path re-rasterises).
        Run once at construction and again on every interior (re-)entry via
        arrive_from(), so a beacon lit / faction mobilised between visits
        actually changes what's in the room. See game/world/content_gate.py.
        Cosmetic `decorations` are not gated (purely visual decals); an
        NPC/structure with no conditional key is unaffected either way."""
        flags = self.player.possessions.flags
        reputation = self.player.possessions.reputation
        self.structures = [s for s in self._structures_config
                           if passes_content_gate(s, flags, reputation)]
        # Ground-level collision boxes for the buildings among those
        # structures (decorative terrain like moon rocks has no
        # building_type and contributes none) - see _building_footprint().
        self.building_footprints = [fp for fp in (self._building_footprint(s) for s in self.structures) if fp]
        # Precompute each structure's Y-sort depth and world-space bounding box
        # once, sorted back-to-front - draw() then only re-binds a drawer for
        # the structures whose box is on screen (was: _structure_depth +
        # _silhouette_local_bounds for every structure every frame).
        self._structure_meta = sorted(
            ((self._structure_depth(s), s, self._structure_world_bounds(s)) for s in self.structures),
            key=lambda t: t[0])
        self._nav_grid = None
        self.npcs = [self._build_local_character(cfg) for cfg in self._npcs_config
                     if passes_content_gate(cfg, flags, reputation)]

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
        self.update_physics(player_present=True)

        # Unread-message ping: once per blink of the Message Log light,
        # driven only from the active screen (update_physics runs for
        # background interiors too, and just counts the timer down). Held
        # while active_dialogue is open - talking to an NPC shouldn't have
        # the Messages pane beeping over the conversation (it isn't even
        # drawn then - see draw()'s own `not self.active_dialogue` gate);
        # _message_alert_pings_played simply falls behind pings_due and
        # catches back up, at most MESSAGE_ALERT_BLINKS pings, once the
        # conversation closes. The while loop otherwise catches up across a
        # slow frame's extra sim steps.
        if not self.active_dialogue:
            _, pings_due = message_alert_state(self.message_alert_timer)
            while self._message_alert_pings_played < pings_due:
                sound_board.play("ping")
                self._message_alert_pings_played += 1

    def update_physics(self, player_present=False):
        """Advance just the NPCs - safe to call on a location that isn't
        the active screen. Paused while a conversation is open here
        (active_dialogue) - talking to one NPC shouldn't leave every other
        NPC in the room still visibly wandering around, any more than the
        player's own movement does. Other cached locations never have a
        conversation open, so this only ever actually pauses the active one.

        Message-log housekeeping runs even mid-conversation (so a message
        that lands while a dialogue is open still lights the unread light
        and is caught the moment it closes) - only NPC movement and the
        escort/ambient checks pause.

        player_present is True only for the interior the player is actually
        standing in (see update()). An NPC's proximity "ambient" line is
        checked against the player's body position, so for a background
        interior the player has never set foot in - which a docking AI
        pilot can cause to be built and cached at any time - it would fire
        against a default spawn position and wrongly post to the shared
        Message Log. It's gated on player_present so it can't."""
        self._refresh_messages()
        if self.message_alert_timer > 0:
            self.message_alert_timer -= 1
        elif self._unread_alert_pinned:
            # An unread message: loop the blink/ping cycle instead of
            # letting it go quiet - see self._unread_alert_pinned's own
            # comment. Cleared only by clicking the Messages pane.
            self.message_alert_timer = MESSAGE_ALERT_FRAMES
            self._message_alert_pings_played = 0
        if self.message_banner_timer > 0:
            self.message_banner_timer -= 1
        if self.active_dialogue:
            return
        self._sync_npc_escorts()
        if player_present:
            self._check_npc_ambient()
        with perf.span("sim.npcs"):
            for character in self.npcs:
                character.update()
        # Drop any NPC that finished walking off (DepartRoutine sets .gone
        # once it reaches its exit point) - see an NPC config's "depart_flag".
        if any(c.gone for c in self.npcs):
            self.npcs = [c for c in self.npcs if not c.gone]
            self.current_npc_target = None

    def draw(self, surface, draw_hud=True):
        """Draw location from config. draw_hud=False skips the top-left
        Controls pane and bottom status pane (e.g. "Press T to talk to
        X") - used when this location is only being redrawn as the
        backdrop for a modal menu on top of it (shop/possessions/exit
        menu - see main.py), whose own controls pane takes that same
        top-left spot instead, and whose "Press T"-style status prompt
        would otherwise be both wrong (not actually pressable right now)
        and visually colliding with the menu's own bottom help text."""
        # Interiors are always north-up, even when only drawn as a modal
        # backdrop (update()/update_camera() may not have run since the
        # Space View last rotated / re-zoomed the shared camera).
        set_camera_angle(0)
        set_camera_zoom_limits(self.camera_zoom_min, self.camera_zoom_max)
        set_camera_zoom(self.camera_zoom)
        if self.star_field is not None:
            surface.fill(BLACK)
            with perf.span("render.starfield"):
                self.star_field.draw(surface)
        else:
            surface.fill(self.bg_color)
        scale = get_scale()

        # World rect on screen (+margin) - one calc a frame, shared by the
        # floor-tile cull, the structure cull, and the NPC cull below. The
        # margin keeps a tall spire / a figure's head from popping at the edge.
        _vb_x0, _vb_y0, _vb_x1, _vb_y1 = utils.visible_world_bounds(constants.PLAYER_H * 3)

        def _bbox_visible(b):
            return not (b[2] < _vb_x0 or b[0] > _vb_x1 or b[3] < _vb_y0 or b[1] > _vb_y1)

        with perf.span("render.location_floor"):
            # Wall-layer decorations sit on the wall fill, behind the floor
            # (the floor polygons paint over anything that spills onto them).
            self._draw_decorations(surface, "wall")

            # Walkable floor - one polygon per room in the culture's floor_color,
            # so each reads as distinct from the surrounding wall_color fill.
            for room in self.rooms:
                screen_pts = [to_screen(px, py) for px, py in room["polygon"]]
                if len(screen_pts) >= 3:
                    pygame.draw.polygon(surface, self.floor_color, screen_pts)

            # Tessellated floor tiles (interior "floor_pattern") - laid over the
            # flat floor fill, under the line decorations and everyone. Plain
            # (non-AA) fills: the tiles abut edge-to-edge, so an AA fringe would
            # only open hairline seams. Culled to the view rect - at interior
            # zoom only a handful of a concourse's few-hundred tiles are ever
            # on screen.
            for world_pts, color, bbox in self._floor_tiles:
                if not _bbox_visible(bbox):
                    continue
                tile_pts = [to_screen(px, py) for px, py in world_pts]
                if len(tile_pts) >= 3:
                    pygame.draw.polygon(surface, color, tile_pts)

            # Floor-layer decorations: on top of the floor, under everyone.
            self._draw_decorations(surface, "floor")

            if self.rooms and not self.seamless:
                font_room_label = get_font(max(10, int(16 * scale)))
                for room in self.rooms:
                    if not room["label"]:
                        continue
                    min_x, min_y, _, _ = _polygon_bounds(room["polygon"])
                    label_pos = to_screen(min_x + 10, min_y + 8)
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
        # close enough for G to actually use it, so proximity isn't a
        # guessing game.
        active_portal = self._nearby_portal()
        font_portal_label = get_font(max(10, int(15 * scale)))
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
            # menu-free G press is never a guess about where it leads.
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
        with perf.span("render.location_entities"):
            # Cull NPCs/visitors outside the camera view before drawing -
            # a pipeline-bodied NPC's walk-cycle deformation
            # (story_assets.body_frame -> apply_walk) is real per-vertex
            # Python trig work, a structure's parts list is a stack of
            # aa.polygon calls, and a busy interior / big concourse holds far
            # more of both than are ever on screen at once at interior zoom.
            # Structures cull by their precomputed world bbox (_structure_meta,
            # already depth-sorted); NPCs/visitors by their feet. The player is
            # never culled (the camera follows them).
            def _in_view(x, y):
                return _vb_x0 <= x <= _vb_x1 and _vb_y0 <= y <= _vb_y1

            drawables = [(depth, self._make_structure_drawer(structure, scale))
                         for depth, structure, bbox in self._structure_meta
                         if _bbox_visible(bbox)]
            drawables += [(character.person.y, character.person.draw) for character in self.npcs
                          if _in_view(character.person.x, character.person.y)]
            drawables += [(visitor.y, visitor.draw) for visitor in self.visitors
                          if _in_view(visitor.x, visitor.y)]
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
        # status panes, and held within the centre-half zone (see
        # center_panel_max_width / docs/DESIGN_PATTERNS.md) like every other
        # centre-anchored HUD element.
        font_label = get_font(int(24 * ui_scale))
        label_text = font_label.render(self.ui_label, True, WHITE)
        label_pad_x, label_pad_y = int(16 * ui_scale), int(8 * ui_scale)
        label_width = min(label_text.get_width() + label_pad_x * 2, center_panel_max_width(ui_scale))
        label_rect = pygame.Rect(0, 0, label_width, label_text.get_height() + label_pad_y * 2)
        label_rect.midtop = (utils.screen_width // 2, control_margin)
        draw_glass_panel(surface, label_rect, ui_scale)
        surface.blit(label_text, (label_rect.centerx - label_text.get_width() // 2, label_rect.y + label_pad_y))

        # Top-center transient banner, directly under the title pane -
        # announces a message that just landed in the Message Log (a mission
        # step from a guide, an NPC's unprompted line - see
        # _refresh_messages). The body itself is in the bottom-left panel;
        # this is just the "look down there" nudge, mirroring SpaceScreen's
        # incoming-hail banner.
        if draw_hud and not self.active_dialogue and self.message_banner_timer > 0 and self.message_banner:
            draw_glow_message(
                surface, self.message_banner[0], get_font(int(20 * ui_scale)),
                utils.screen_width // 2, label_rect.bottom + int(10 * ui_scale),
                color=self.message_banner[1], shadow_color=(20, 30, 40),
            )

        # Top-right targeting pane (see draw_info_panel) - same design and
        # (label, value, value_color) two-tone lines as SpaceScreen's own
        # info panel, minus the jump-target / mode lines that don't apply
        # while on foot.
        if target_npc:
            info_lines = [("Target:", target_npc.name, GREEN)]
            target_role = self._role_label(target_npc)
            if target_role:
                info_lines.append(("  Role:", target_role, WHITE))
        else:
            info_lines = [("Target:", "None", GRAY)]
        info_rect, _ = draw_info_panel(surface, info_lines, ui_scale, (utils.screen_width - control_margin, control_margin))

        # Top-left control-reference pane - same design as SpaceScreen's
        # (see draw_controls_pane). Hidden (draw_hud=False) while a modal
        # menu is up, and while a conversation has focus (it's mouse-only -
        # click an option or the X). C collapses it to a two-liner.
        controls_rect = None
        if draw_hud and not self.active_dialogue:
            # T (talk) and G (board / exit) are left off - each shows its own
            # bottom-status prompt ("Press T to talk to ...", "Press G to enter
            # portal") whenever it actually applies. Self-explanatory mouse
            # actions (wheel to scroll/zoom) are left off too.
            help_items = [
                (primary_label(Action.PAUSE), "Pause"),
                ("WASD / Arrows", "Walk"),
                (combo(Action.CYCLE_TARGET_BACKWARD, Action.CYCLE_TARGET_FORWARD), "Cycle target"),
                (primary_label(Action.STAR_MAP), "Star map"),
                (primary_label(Action.POSSESSIONS), "Possessions"),
                (primary_label(Action.MISSION_LOG), "Mission log"),
            ]
            controls_rect = draw_controls_pane(surface, control_margin, control_margin, "Controls", help_items, ui_scale,
                                               collapsed=self.controls_collapsed)

        # Bottom-center status pane (see draw_status_pane) - entrance and
        # talk prompts are independent of each other and can both be true
        # at once, so they stack as separate lines in one panel. Skipped
        # (draw_hud=False, or while active_dialogue is set) for the same
        # reason as the Controls pane above - "Press T to talk" isn't
        # actually actionable while a modal menu or conversation has input
        # focus.
        status_rect = None
        if draw_hud and not self.active_dialogue:
            status_lines = []
            if active_portal:
                status_lines.append((f"Press {primary_label(Action.USE_PORTAL)} to enter portal", GREEN))
            if closest_npc:
                status_lines.append((f"Press {primary_label(Action.TALK)} to talk to {closest_npc.name}", GREEN))
            status_rect = draw_status_pane(surface, status_lines, ui_scale)

        # Bottom-left Message Log - the same shared history the Space View
        # shows (see draw_message_log / Possessions.message_log), so a
        # mission step or an NPC's line the player got while docked is still
        # there to read. Skipped along with the rest of the HUD while a
        # modal menu / conversation has focus.
        message_log_rect = None
        if draw_hud and not self.active_dialogue:
            messages = [(m["sender"], m["text"]) for m in self.player.possessions.message_log]
            # Fill the gap down to the screen edge below wherever the
            # Controls pane (drawn above) currently ends - so the log grows
            # or shrinks as that pane expands/collapses (C toggles it).
            log_max_height = utils.screen_height - control_margin - (controls_rect.bottom + control_margin) if controls_rect else None
            message_log_rect, message_log_max_scroll = draw_message_log(
                surface, messages, ui_scale, self.message_log_scroll,
                alert=message_alert_state(self.message_alert_timer)[0], pinned=self._unread_alert_pinned,
                max_height=log_max_height)
            self.message_log_scroll = max(0, min(self.message_log_scroll, message_log_max_scroll))
            self._message_log_max_scroll = message_log_max_scroll
        self._message_log_rect = message_log_rect

        # Cached for handle_input()'s mouse-click targeting, so a click on
        # any of these panels doesn't also register as a click-to-target in
        # the world behind them (see SpaceScreen._hud_click_rects).
        self._hud_click_rects = [rect for rect in (label_rect, info_rect, controls_rect, status_rect, message_log_rect) if rect]

        # Draw active dialogue box on top of everything
        if self.active_dialogue:
            self.active_dialogue.draw(surface, ui_scale, status_fn=self._option_blocked_reason, flags=self.player.possessions.flags, reputation=self.player.possessions.reputation)

    # World units the collision box is allowed to poke past the drawn base
    # of a building/furniture piece on the near (camera) side - a small lip
    # so a person can't walk their feet visually into the object's front
    # face, without the box floating in open floor below the graphic.
    FOOTPRINT_FRONT_LIP = 8

    def handle_input(self, events):
        """Override for area-specific input (dialogue, etc.)"""
        for event in events:
            # A conversation swallows all other input while open: hover
            # highlights an option, a click or Enter picks it, the ✕ or ESC
            # closes it.
            if self.active_dialogue:
                if event.type == pygame.MOUSEMOTION:
                    hovered = self.active_dialogue.option_at(event.pos)
                    if hovered is not None:
                        self.active_dialogue.selected_option = hovered
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.active_dialogue.debug_click_at(event.pos):
                        pass
                    elif self.active_dialogue.close_at(event.pos):
                        self.active_dialogue = None
                    else:
                        picked = self.active_dialogue.option_at(event.pos)
                        if picked is not None:
                            result = self._choose_dialogue_option(picked)
                            if result:
                                return result
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    result = self._choose_dialogue_option(self.active_dialogue.selected_option)
                    if result:
                        return result
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.active_dialogue = None
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # A click on the Messages pane acknowledges an unread
                # message - see self._unread_alert_pinned's own comment -
                # silencing the looping blink/ping immediately rather than
                # waiting for the current cycle to finish.
                if self._message_log_rect and self._message_log_rect.collidepoint(event.pos):
                    self._unread_alert_pinned = False
                    self.message_alert_timer = 0
                    continue
                if not any(rect.collidepoint(event.pos) for rect in self._hud_click_rects):
                    self._select_person_target_at(*to_world(*event.pos))
                continue

            if event.type == pygame.MOUSEWHEEL:
                # Scroll the Message Log (bottom-left) when the pointer is
                # over it - mirrors SpaceScreen's own wheel handling. Wheel
                # up (event.y > 0) moves toward the newest entry; the upper
                # bound is clamped against max_scroll in draw().
                mouse_pos = pygame.mouse.get_pos()
                if self._message_log_rect and self._message_log_rect.collidepoint(mouse_pos):
                    self.message_log_scroll = max(0, self.message_log_scroll - event.y)
                    # Generic gameplay-event flag (mirrors "walked_interior" /
                    # "targeted_person") - lets a tutorial stage use
                    # "scrolled_message_log" as its complete_flag. Only counts
                    # when the log actually had a backlog to scroll.
                    if self._message_log_max_scroll > 0:
                        self.player.possessions.flags["scrolled_message_log"] = True
                elif not any(rect.collidepoint(mouse_pos) for rect in self._hud_click_rects):
                    # Wheel over open floor zooms the interior view (wheel up
                    # = zoom in), clamped to this interior's own range. Pushed
                    # to the shared camera by update_camera().
                    self.camera_zoom = self._clamp_zoom(
                        self.camera_zoom + event.y * constants.CAMERA_ZOOM_STEP)
                continue

            if event.type != pygame.KEYDOWN:
                continue

            if is_action(event.key, Action.USE_PORTAL):
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
                        # with its reason instead of G silently doing nothing.
                        return "exit_menu"
            elif is_action(event.key, Action.CYCLE_TARGET_FORWARD):
                self._cycle_npc_target(1)
            elif is_action(event.key, Action.CYCLE_TARGET_BACKWARD):
                self._cycle_npc_target(-1)
            elif is_action(event.key, Action.STAR_MAP):
                return "star_map"
            elif is_action(event.key, Action.TALK):
                # T always talks to whoever's closest in range (see
                # _closest_person_in_range) - independent of any manually
                # cycled/clicked target (current_npc_target), which is only
                # for viewing info at a distance now.
                nearest = self._closest_person_in_range()
                if nearest:
                    # Generic gameplay-event flag - lets a tutorial stage
                    # use "talked_to_npc" as its complete_flag. Set for a
                    # shop NPC too (opening a store still counts as walking
                    # up and pressing T).
                    self.player.possessions.flags["talked_to_npc"] = True
                    # getattr, not nearest.shop: a visiting AI pilot (see
                    # Character.for_ai_pilot) never gets a .shop attribute at
                    # all, unlike a local NPC (_build_local_character) - only
                    # the latter can ever be a shop.
                    # An NPC with both a real dialogue tree and a shop
                    # (shop_via_dialogue) opens the conversation first - the
                    # tree carries an "open_shop" option that hands off to the
                    # store. A shop NPC with only the flat greeting fallback
                    # still opens its store straight away.
                    if getattr(nearest, "shop", None) and not getattr(nearest, "shop_via_dialogue", False):
                        self.active_shop = nearest.shop
                        return "shop"
                    self._pending_shop = getattr(nearest, "shop", None)
                    # Always start a fresh conversation at the root node -
                    # otherwise leaving mid-tree (ESC) and talking again
                    # would silently resume wherever it was left off.
                    # resolve_root() (not .root directly) lets a story flag
                    # set earlier open on a different greeting node - see
                    # Dialogue.conditional_roots.
                    nearest.dialogue.current_node = nearest.dialogue.resolve_root(self.player.possessions.flags, self.player.possessions.reputation)
                    nearest.dialogue.selected_option = self._first_selectable_option(nearest.dialogue.current_options(self.player.possessions.flags, self.player.possessions.reputation))
                    self.active_dialogue = nearest.dialogue
            elif is_action(event.key, Action.POSSESSIONS):
                # Generic gameplay-event flag - lets a tutorial stage use
                # "viewed_possessions" as its complete_flag; mirrors MISSION_LOG below.
                self.player.possessions.flags["viewed_possessions"] = True
                return "possessions"
            elif is_action(event.key, Action.MISSION_LOG):
                # Generic gameplay-event flag - lets a mission stage use
                # "viewed_mission_log" as its complete_flag (see
                # missions.json's first_flight); mirrors SpaceScreen's MISSION_LOG.
                self.player.possessions.flags["viewed_mission_log"] = True
                return "missions"
            elif is_action(event.key, Action.TOGGLE_CONTROLS):
                self._toggle_controls()
            elif is_action(event.key, Action.PAUSE):
                return "pause"
        return None

    def get_state(self):
        """Save player position state for locations"""
        return {
            "player": {
                "x": self.player.x,
                "y": self.player.y
            },
            "possessions": self.player.possessions.get_state(),
            # Player's remembered interior zoom level (mouse wheel). Clamped
            # back into range on restore in case the story's limits changed.
            "camera_zoom": self.camera_zoom,
        }

    def restore_state(self, state):
        """Restore player position state for locations"""
        if not state:
            return
        if "camera_zoom" in state:
            self.camera_zoom = self._clamp_zoom(state["camera_zoom"])
        if "player" in state:
            player_state = state["player"]
            self.player.x = player_state.get("x", self.player.x)
            self.player.y = player_state.get("y", self.player.y)
            # A saved position can land outside this interior's walkable
            # area if the floor plan was rescaled/reshaped since the save
            # was made (see docs/SAVE_SYSTEM.md's save-compat notes) - snap to the
            # primary portal rather than leaving the player wedged in a
            # wall with no way to move.
            if not self.can_move_to(self.player.x, self.player.y):
                self.player.x, self.player.y = self.portals[0]["x"], self.portals[0]["y"]
        if "possessions" in state:
            self.player.possessions.restore_from(state["possessions"])
        self._seen_message_count = len(self.player.possessions.message_log)
