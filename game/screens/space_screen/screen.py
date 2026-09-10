"""SpaceScreen — core lifecycle, input, the fixed-step update, draw and
save/restore. Cohesive method clusters live in sibling mixin modules."""
from game.screens.space_screen._defs import *  # noqa: F401,F403
from game.screens.space_screen.setup import _SetupMixin
from game.screens.space_screen.targeting import _TargetingMixin
from game.screens.space_screen.hud import _HudMixin
from game.screens.space_screen.hailing import _HailingMixin
from game.screens.space_screen.npc_sync import _NpcSyncMixin
from game.screens.space_screen.jump import _JumpMixin
from game.screens.space_screen.combat import _CombatMixin
from game.screens.space_screen.mining import _MiningMixin


class SpaceScreen(_SetupMixin, _TargetingMixin, _HudMixin, _HailingMixin, _NpcSyncMixin, _JumpMixin, _CombatMixin, _MiningMixin, ScreenBase):
    """Main space exploration screen with ships and landing."""
    def __init__(self, system_config=None, pilot_name="", story="default", system_id=None):
        super().__init__(pilot_name=pilot_name)
        self.story = story  # fixed for the whole playthrough - stories are wholly separate

        # Adopt this story's audio kit: the shared audio-core module plus any
        # story-local audio.json overrides (see docs/SOUND.md). SpaceScreen is
        # the single chokepoint every new-game and load path passes through.
        from game.audio.music import music
        sound_board.apply_story(story)
        music.apply_story(story)

        # Load story metadata (player ship type, starting system, etc)
        story_meta = get_story(story)
        self.system_id = system_id or story_meta.get("starting_system", "default")
        # Recorded into every save (see main.py's build_save_game_state) so
        # a save always knows which version of the story it was made
        # against - bump story.json's "version" whenever a change to that
        # story's config or this game's state-handling code would make an
        # existing save behave differently once reloaded (see
        # docs/SAVE_SYSTEM.md's "Save Compatibility Discipline").
        self.story_version = story_meta.get("version", "0.0.0")
        from game.config_source import module_versions
        self.module_versions = module_versions(story)  # shared modules the
        # story opts into, recorded into saves so a load can warn when one
        # changed under an existing save (docs/CONFIG_MODULES.md)
        # Static mission definitions for this story (title + ordered stages -
        # see game/world/mission.py); which mission(s) a player actually has
        # active/completed is state on their own Possessions, not here.
        self.missions_config = get_missions(story)
        # Which mission (if any) automatically starts as the player enters
        # the game - config-driven so a story can opt into (or change, or
        # omit) a tutorial mission without touching this class. None = no
        # auto-started mission.
        self.starting_mission = story_meta.get("starting_mission")
        # When that mission fires: "ship_purchase" (default - the first time
        # the player buys a ship, see _on_ship_purchased) or "new_game" (the
        # moment a fresh game begins, see begin_new_game). A story that hands
        # the player a starting ship gets "new_game" behaviour automatically,
        # since no purchase ever happens.
        self.starting_mission_trigger = story_meta.get("starting_mission_trigger", "ship_purchase")
        # story.json's "start" block: the player's state at the beginning of
        # a brand-new game - starting credits/ship/spare outfits/personal
        # items/story flags, plus where in the world they begin ("location":
        # "station"/"moon"/"space", "interior": which interior key). Applied
        # by _apply_start_config() (state) + begin_new_game() (placement);
        # a loaded save overwrites all of this via restore_possessions().
        self.start_config = story_meta.get("start", {})
        # graphics.json "outfits" id worn by the player and every AI pilot
        # (station/moon NPCs pick their own per-config, see LocationScreen).
        self.default_outfit_id = story_meta.get("default_outfit", "space_suit")
        # World-render magnification for this story (UI scale is unaffected).
        # Global camera state - safe to set here since a session is only
        # ever in one story, and only a live SpaceScreen renders the world.
        # camera_zoom is the live, player-adjustable level (mouse wheel over
        # open space, see handle_input); it starts at the story default and
        # is clamped to [min, max]. Remembered for the session and captured
        # by get_state(); interiors keep their own separate level.
        self.camera_zoom_min = story_meta.get("camera_zoom_min", CAMERA_ZOOM_MIN)
        self.camera_zoom_max = story_meta.get("camera_zoom_max", CAMERA_ZOOM_MAX)
        self.camera_zoom = self._clamp_zoom(story_meta.get("camera_zoom", CAMERA_ZOOM))
        set_camera_zoom_limits(self.camera_zoom_min, self.camera_zoom_max)
        set_camera_zoom(self.camera_zoom)
        # Per-story tuning overrides (module-level names above are the
        # defaults / JumpDrive's own fallback).
        self.brake_slow_threshold = story_meta.get("brake_slow_threshold", BRAKE_SLOW_THRESHOLD)
        jump_cfg = story_meta.get("jump", {})
        self.jump_travel_frames = jump_cfg.get("travel_frames", JUMP_TRAVEL_FRAMES)
        self.jump_speed = jump_cfg.get("speed", JUMP_SPEED)
        self.jump_arrival_distance = jump_cfg.get("arrival_distance", JUMP_ARRIVAL_DISTANCE)
        self.jump_self_min_distance = jump_cfg.get("self_min_distance", JUMP_SELF_MIN_DISTANCE)

        # Load config for the current system within this story
        self.system_config = system_config or load_json(f"config/stories/{story}/systems/{self.system_id}.json") or {}

        # Get space system drag (default 0 = no drag)
        space_drag = self.system_config.get("drag", 0)

        # Placeholder ship stats/graphics for self.player before any ship is
        # actually owned - PlayerController always needs a Ship object to
        # exist, but a new pilot starts on foot in the station with none, and
        # this placeholder is never flown or even rendered until one is
        # bought (see _apply_ship_type()/_on_ship_purchased(), which
        # reconfigure it for real at that point). "player_type" should
        # normally stay null for that reason - a non-null value here does
        # NOT actually grant the player a starting ship (LocationScreen.
        # ship_available is driven entirely by Possessions.owned_ships,
        # which starts empty regardless), it would just be misleading
        # placeholder stats nobody sees.
        player_ship_type_id = story_meta.get("ships", {}).get("player_type")
        player_ship_type = get_ship_type(self.story, player_ship_type_id) if player_ship_type_id else None
        player_graphics = get_graphics_asset(self.story, "ships", player_ship_type_id) if player_ship_type_id else None

        # Spawn away from map center by default, since that's where a central
        # star (if the system has one) usually sits.
        player_start_cfg = self.system_config.get("player_start", {})
        player_x = GAME_WIDTH * player_start_cfg.get("x", 0.4)
        player_y = GAME_HEIGHT * player_start_cfg.get("y", 0.35)
        self.player = PlayerController(player_x, player_y, space_drag=space_drag, graphics=player_graphics, ship_type=player_ship_type, pilot_name=pilot_name, outfit=get_graphics_asset(self.story, "outfits", self.default_outfit_id))
        self._apply_start_config()

        # Every system this story defines gets built and kept simulating for
        # the whole session - not just whichever one the player currently
        # occupies (see SystemState, update_physics() below, and main.py's
        # update_background_locations(), which now walks every system's
        # cached interiors the same way it already did for the current
        # one). get_star_systems() discovers them all from
        # config/stories/{story}/systems/*.json; self.system_id is added
        # explicitly in case a save/story references one that scan somehow
        # missed, so activating it below can never KeyError.
        self.systems = {}
        self.system_configs = {}
        system_ids = set(get_star_systems(self.story).keys())
        system_ids.add(self.system_id)
        for sid in system_ids:
            config = self.system_config if sid == self.system_id else (load_json(f"config/stories/{story}/systems/{sid}.json") or {})
            self.system_configs[sid] = config
            self.systems[sid] = self._build_system_state(sid, config)
        self._activate_system(self.system_id)

        self.landing_text = 0
        self.landing_target = None
        self.camera_x = 0
        self.camera_y = 0
        # View rotation (degrees) applied to the whole Space View, driven by
        # Q/E. Player-preference view state only - not saved, not game state,
        # and reset to north-up (0) by interiors when the player lands.
        self.camera_angle = 0
        # Star map selection, for the Jump mechanic - never None: defaults to
        # (and resets to, after a jump) the current system, so "Jump Target"
        # always names somewhere and J is always meaningful.
        self.selected_system_id = self.system_id
        # True once the player is actually out flying (set by board_ship() /
        # every update() frame, cleared by park_at() and _mark_landed()).
        # update_physics() also runs in the background while the player is
        # docked in an interior - things that should only happen in the
        # cockpit (this story's starting_mission firing, an NPC's proximity
        # one-way hail) gate on this so they don't go off mid-conversation
        # in a station bar. See _on_ship_purchased / _check_one_way_hails.
        self.in_flight = False
        # Set by _on_ship_purchased when the starting_mission trigger is
        # "ship_purchase": the mission is armed here but only actually
        # started once the player launches (board_ship()), so the tutorial
        # toast and Kade's opening hail don't land while they're still
        # walking around the station having just bought the ship. Lives on
        # possessions.flags so it survives a save made in that gap.
        self.jump_state = None  # None, or a dict tracking the jump animation
        self.jump_message_timer = 0  # Transient jump-blocked feedback (see jump_message)
        self.jump_message = "Too close to jump - move away from center first"
        self._lit_beacons = None  # seeded on first _check_beacons(); then tracks beacon flips
        # Transient center-screen toast (see _show_toast) - jump completion,
        # mission started / stage completed / mission finished.
        self.toast_text = None
        self.toast_color = CYAN
        self.toast_timer = 0
        self.active_dialogue = None  # Set to a hailed pilot's Dialogue while a hail is open (see handle_input's K_h)
        self.hail_banner = None  # (text, color) for a transient hail-related message (see below)
        self.hail_banner_timer = 0
        # Projectiles (weapon shots) currently in flight
        self.projectiles = []
        # Fire rate limiting (frames between shots when holding X) - the
        # cooldown length itself comes from whatever weapon's actually
        # equipped (see _equipped_weapon_stats's "fire_rate"), so this is
        # just the countdown, not a fixed rate.
        self.weapon_fire_cooldown = 0
        # Spark-burst effects (see game/world/explosion.py) - one per weapon
        # hit on an asteroid, purely cosmetic (not saved, not collidable).
        self.explosions = []
        # Drifting mined-ore chunks (see game/world/ore_pickup.py) - spawned
        # when a small asteroid is destroyed, collected by flying over them
        # with cargo room. Not saved, same as asteroids/explosions/
        # projectiles - see OrePickup's own docstring.
        self.ore_pickups = []
        # HUD panel rects from the most recently drawn frame - a mouse click
        # on one of them (minimap, info panel, controls, status) shouldn't
        # also be interpreted as a click-to-target in the world behind it.
        # One frame stale by construction (draw() runs after handle_input()
        # each loop), which is fine since these panels don't move frame to
        # frame.
        self._hud_click_rects = []
        # Minimap panel rect + the plotted blips (screen_x, screen_y,
        # hit_radius, obj) from the last drawn frame, so handle_input() can
        # click-to-target a blip and _draw_minimap() can show hover text for
        # whichever one the pointer is over (see _minimap_blip_at). One frame
        # stale, same as _hud_click_rects.
        self._minimap_rect = None
        self._minimap_blips = []
        # Mouse-wheel scroll offsets (in lines) for the two scrollable HUD
        # side panes - the bottom-left Message Log and the top-right
        # targeting/info pane - plus each pane's rect from the last drawn
        # frame, for wheel hit-testing (see handle_input / _draw_hud). The
        # message scroll resets to 0 (newest) whenever one arrives
        # (_post_message).
        self.message_log_scroll = 0
        self._message_log_rect = None
        # Set by _draw_hud from draw_message_log's return each frame - see the
        # matching field/usage in LocationScreen (drives the
        # "scrolled_message_log" tutorial flag).
        self._message_log_max_scroll = 0
        self.info_panel_scroll = 0
        self._info_panel_rect = None
        # Frames left on the Message Log's blinking red "new message" light
        # (see MESSAGE_ALERT_FRAMES / _post_message / draw_message_log), and
        # how many of the MESSAGE_ALERT_BLINKS pings have sounded for the
        # current alert (reset in _post_message, advanced in update()).
        self.message_alert_timer = 0
        self._message_alert_pings_played = 0

    def get_interior_screen(self, landing_site, key):
        """Return the persistent LocationScreen for one of landing_site's
        interiors (key = "default" for a station, "city"/"wilderness" for
        the moon), creating and caching it on landing_site.interior_screens the
        first time it's visited. Later visits reuse the same instance, so
        NPCs and the player's position within it persist instead of
        resetting every time - and it can keep simulating in the
        background (see update_physics() calls in main.py) while the
        player is elsewhere. Returns None if the interior isn't configured.
        Sized from landing_site.interior_world_size, not a caller-supplied
        width/height - every call site used to pass the same 800x600/
        1600x1600 pair derived from is_station itself; asking the landing_site
        keeps that in one place.
        """
        world_width, world_height = landing_site.interior_world_size
        if key in landing_site.interior_screens:
            return landing_site.interior_screens[key]

        interior_config = landing_site.interiors.get(key)
        if not interior_config:
            return None

        # Display name for every sibling interior this location's portals
        # might connect to (see LocationScreen._display_name) - built from
        # landing_site.interiors directly rather than lazily inside
        # LocationScreen, since that dict (and any config files it points
        # to) belongs to the landing_site, not to any one interior within it.
        location_labels = {}
        for sibling_key, sibling_config in landing_site.interiors.items():
            sibling_config = load_json(sibling_config) if isinstance(sibling_config, str) else sibling_config
            location_labels[sibling_key] = (sibling_config or {}).get("label", sibling_key)

        if isinstance(interior_config, str):
            screen = LocationScreen(config_file=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story, player_possessions=self.player.person.possessions, on_ship_purchased=self._on_ship_purchased, on_ship_switched=self._on_ship_switched, location_labels=location_labels)
        else:
            screen = LocationScreen(config_data=interior_config, world_width=world_width, world_height=world_height, pilot_name=self.pilot_name, story=self.story, player_possessions=self.player.person.possessions, on_ship_purchased=self._on_ship_purchased, on_ship_switched=self._on_ship_switched, location_labels=location_labels)
        # Which interiors key this is (e.g. "default" for a station,
        # "city"/"wilderness" for a moon) - recorded into a save as
        # station_location / moon_location (see main.py's
        # build_save_game_state; only moon_location is honoured on load).
        screen.interior_key = key
        landing_site.interior_screens[key] = screen
        return screen

    def board_ship(self):
        """The player has launched from a docked interior back into space
        (main.py's interior -> game transitions call this; update() also
        calls it every flight frame as a catch-all for save-load-into-space
        and any missed transition). Marks the ship in flight and starts a
        starting_mission that _on_ship_purchased armed but deferred until
        launch - idempotent, safe to call every frame."""
        if not self.in_flight:
            # Real docked -> flying transition (not the per-frame catch-all
            # re-call): re-sync the active system's flag-gated roster, since
            # the player may have changed a flag / their standing while
            # docked. See _sync_conditional_ships.
            self._sync_conditional_ships()
        self.in_flight = True
        if self.player.person.possessions.flags.get("starting_mission_armed"):
            self.player.person.possessions.flags["starting_mission_armed"] = False
            self._start_tutorial_mission()

    def park_at(self, landing_site):
        """Position the player's ship at `landing_site`'s own space position
        and stop it - used both right after a purchase and when loading
        directly into a station/moon save (no actual flight/landing
        happened this session, so the ship has to be placed there
        explicitly rather than restored from a save - see
        restore_possessions() and main.py's load handling)."""
        self.player.x, self.player.y = landing_site.x, landing_site.y
        self.player.park()
        self.in_flight = False

    def _clamp_zoom(self, zoom):
        """Keep a zoom level within this story's Space View range."""
        return max(self.camera_zoom_min, min(self.camera_zoom_max, zoom))

    def handle_input(self, events):
        keys = pygame.key.get_pressed()
        # Manual rotation/thrust are locked out during a jump - _update_jump()
        # drives the ship's angle (align phase) and reads it straight back
        # into velocity every frame (travel phase, see _update_jump()), so a
        # held turn key during travel would otherwise silently steer the
        # jump off its heading instead of it being a fixed, committed course.
        # Also locked out while a hail is open (self.active_dialogue) - same
        # reason LocationScreen pauses movement for its own active_dialogue.
        if not self.jump_state and not self.active_dialogue:
            self.player.handle_input(keys)
            # Fire the equipped weapon continuously while SPACE is held -
            # polled every frame (not a KEYDOWN branch below) so holding it
            # fires repeatedly at the weapon's own fire_rate, rather than
            # once per physical press. Autopilot now lives on F (see K_f
            # below) - SPACE used to do both (a tap engaged autopilot,
            # which is why so many docstrings elsewhere still say
            # "K_SPACE" when they mean "the autopilot-engage key").
            if keys[pygame.K_SPACE]:
                self._update_weapon_fire()

        # Rotate the view (Q/E) - held, like ship turning. Allowed even
        # mid-jump (it's only the camera), blocked only while a hail has
        # input focus, same as flight controls.
        if not self.active_dialogue:
            if keys[pygame.K_q]:
                self.camera_angle = (self.camera_angle - CAMERA_ROTATE_SPEED) % 360
            if keys[pygame.K_e]:
                self.camera_angle = (self.camera_angle + CAMERA_ROTATE_SPEED) % 360

        for event in events:
            # An open hail swallows all other input: hover highlights an
            # option, a click or Enter picks it, the ✕ or ESC closes it.
            if self.active_dialogue:
                if event.type == pygame.MOUSEMOTION:
                    hovered = self.active_dialogue.option_at(event.pos)
                    if hovered is not None:
                        self.active_dialogue.selected_option = hovered
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.active_dialogue.close_at(event.pos):
                        self.active_dialogue = None
                    else:
                        picked = self.active_dialogue.option_at(event.pos)
                        if picked is not None:
                            self._choose_hail_option(picked)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self._choose_hail_option(self.active_dialogue.selected_option)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.active_dialogue = None
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # A click on the minimap targets the blip under the pointer
                # (if any - a click on empty radar does nothing); a click
                # anywhere in the world that isn't on a HUD panel targets
                # whatever object was clicked directly.
                if self._minimap_rect and self._minimap_rect.collidepoint(event.pos):
                    blip_obj = self._minimap_blip_at(event.pos)
                    if blip_obj is not None:
                        self._select_target(blip_obj)
                elif not any(rect.collidepoint(event.pos) for rect in self._hud_click_rects):
                    self._select_target_at(*to_world(*event.pos))
                continue

            if event.type == pygame.MOUSEWHEEL:
                # Scroll whichever scrollable side pane the pointer is over -
                # the Message Log (bottom-left) or the targeting/info pane
                # (top-right). Wheel up (event.y > 0) moves toward the top;
                # the upper bound is clamped against max_scroll in _draw_hud
                # once each pane's real line count is known.
                mouse_pos = pygame.mouse.get_pos()
                if self._message_log_rect and self._message_log_rect.collidepoint(mouse_pos):
                    self.message_log_scroll = max(0, self.message_log_scroll - event.y)
                    if self._message_log_max_scroll > 0:
                        self.player.person.possessions.flags["scrolled_message_log"] = True
                elif self._info_panel_rect and self._info_panel_rect.collidepoint(mouse_pos):
                    self.info_panel_scroll = max(0, self.info_panel_scroll - event.y)
                elif not any(rect.collidepoint(mouse_pos) for rect in self._hud_click_rects):
                    # Wheel over open space zooms the world view (wheel up =
                    # zoom in), clamped to this story's Space View range. The
                    # level is pushed to the shared camera in update().
                    self.camera_zoom = self._clamp_zoom(
                        self.camera_zoom + event.y * CAMERA_ZOOM_STEP)
                continue

            if event.type != pygame.KEYDOWN:
                continue

            # Cancel autopilot on any key press (except ESC which handles
            # pause, Q/E which only rotate the view - not a flight input -
            # and SPACE, which fires the equipped weapon rather than
            # steering, so shooting at an asteroid doesn't abort a run to
            # the station)
            if self.player.autopilot_active and event.key not in (pygame.K_ESCAPE, pygame.K_q, pygame.K_e, pygame.K_SPACE):
                self.player.autopilot_active = False
                self.player.autopilot_target = None
                return None

            if event.key == pygame.K_ESCAPE:
                return "pause"
            elif event.key == pygame.K_RIGHTBRACKET:
                self._cycle_target(1)
            elif event.key == pygame.K_LEFTBRACKET:
                self._cycle_target(-1)
            elif event.key == pygame.K_t:
                self._cycle_target_mode()
            elif event.key == pygame.K_h:
                self._start_hail()
            elif event.key == pygame.K_l:
                # Land only - never engages autopilot (see K_f below
                # for that). If a landing site is targeted and already in
                # range, land on it directly; otherwise fall back to a
                # pure proximity check, which also covers an AI ship
                # being targeted or nothing being targeted at all.
                target_obj = self._get_target_object()
                if target_obj and self.current_target is not None and not isinstance(target_obj, Character):
                    distance = target_obj.get_distance(self.player.x, self.player.y)
                    speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
                    if distance < target_obj.landing_distance and speed < 0.4:
                        if target_obj == self.station:
                            self.landing_target = "station"
                            self._mark_landed()
                            return "land"
                        elif target_obj == self.moon:
                            self.landing_target = "moon"
                            self._mark_landed()
                            return "land"
                landing_target = self._check_landing()
                if landing_target:
                    self.landing_target = landing_target
                    self._mark_landed()
                    return "land"
            elif event.key == pygame.K_f:
                # Engage autopilot toward the current target - follows an
                # AI ship, or approaches a landing site from any range (L
                # only lands once you're already close). SPACE now fires
                # the equipped weapon (polled continuously above, not a
                # KEYDOWN branch) - autopilot moved here so the two don't
                # collide on one key.
                target_obj = self._get_target_object()
                if target_obj and self.current_target is not None:
                    self.player.engage_seek(target_obj)
                    sound_board.play("confirm")
                    if isinstance(target_obj, Character):
                        # Generic gameplay-event flag (see the docstring on
                        # the "Hailing tuning" flags above) - any story's
                        # missions.json can use this as a stage's
                        # complete_flag without this class knowing about
                        # missions at all.
                        self.player.person.possessions.flags["used_autopilot_on_ship"] = True
            elif event.key == pygame.K_m and not self.jump_state:
                return "star_map"
            elif event.key == pygame.K_j and not self.jump_state:
                self.try_jump()
            elif event.key == pygame.K_p:
                return "possessions"
            elif event.key == pygame.K_n:
                # Generic gameplay-event flag (see K_f's comment) - a
                # mission stage can use "viewed_mission_log" as its
                # complete_flag (see missions.json's first_flight).
                self.player.person.possessions.flags["viewed_mission_log"] = True
                return "missions"
            elif event.key == pygame.K_c:
                self._toggle_controls()
        return None

    def _mark_landed(self):
        """Set the generic "landed_on_landing_site" gameplay-event flag -
        called from every path that actually lands the ship (manual L,
        and update()'s auto-land-on-autopilot-arrival). See K_f's own
        comment above for why this lives on Possessions.flags rather than
        a SpaceScreen-only field."""
        self.player.person.possessions.flags["landed_on_landing_site"] = True
        self.in_flight = False  # main.py is about to swap to the interior screen

    def _check_landing(self):
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)

        station_distance = self.station.get_distance(self.player.x, self.player.y)
        if station_distance < self.station.landing_distance and speed < 0.4:
            return "station"

        moon_distance = self.moon.get_distance(self.player.x, self.player.y)
        if moon_distance < self.moon.landing_distance and speed < 0.4:
            return "moon"

        return None

    def update_physics(self):
        """Update physics without camera - used when space is background.

        Every system this story defines gets its station/moon/celestial
        bodies/AI ships advanced every frame - not just self.system_id, the
        one actually being flown in right now (see SystemState) - so
        traffic elsewhere keeps moving and NPCs at a station/moon the
        player isn't currently visiting keep going about their routine
        (main.py's update_background_locations() already does the
        equivalent for cached interiors). The asteroid/star fields are the
        one exception, kept to just the active system - both are pure,
        camera-driven decoration (see SystemState's docstring)."""
        with perf.span("sim.player"):
            if self.jump_state:
                self._update_jump()
            else:
                self.player.update()
        flags = self.player.person.possessions.flags
        if self.player.thrust > 0:
            # Generic gameplay-event flag - see K_f's comment above on
            # why these live on Possessions.flags instead of a
            # SpaceScreen-only field.
            flags["used_thrust"] = True
        # Only meaningful once thrust and the brake control have both been
        # used at least once - otherwise a ship that simply never got
        # moving would trivially satisfy "speed below threshold" without
        # any actual braking having happened.
        speed = math.sqrt(self.player.velocity_x ** 2 + self.player.velocity_y ** 2)
        if flags.get("used_thrust") and flags.get("used_brake") and speed < self.brake_slow_threshold:
            flags["braked_below_threshold"] = True
        self._sync_hostiles()
        with perf.span("sim.ai_ships"):
            for state in self.systems.values():
                state.update_physics()
            self.asteroid_field.update()
        with perf.span("sim.projectiles"):
            self._update_ai_weapon_fire()
            self._update_projectiles()
            if self.player.ship and self.player.ship.health <= 0:
                self._on_player_destroyed()
            self.explosions = [e for e in self.explosions if e.update()]
            self._update_ore_pickups()
        # Update weapon fire cooldown
        if self.weapon_fire_cooldown > 0:
            self.weapon_fire_cooldown -= 1
        if self.jump_message_timer > 0:
            self.jump_message_timer -= 1
        if self.hail_banner_timer > 0:
            self.hail_banner_timer -= 1
        if self.message_alert_timer > 0:
            self.message_alert_timer -= 1
        self._check_one_way_hails()
        self._check_beacons()
        self._validate_target()
        # Mission progress before _sync_escorts() - a mission finishing
        # this exact frame clears its escort_flag (see mission.py's
        # _on_mission_end), and escort sync needs to see that same-frame
        # rather than escorting for one extra frame after the tutorial's
        # already over.
        with perf.span("sim.missions"):
            possessions = self.player.person.possessions
            completed_before = set(possessions.completed_missions)
            for advanced_stage in check_mission_progress(self.missions_config, possessions):
                self._deliver_stage_message(advanced_stage)
                mission_id, stage_index = advanced_stage
                total = len(self.missions_config.get(mission_id, {}).get("stages", []))
                self._show_toast(f"Step {stage_index + 1}/{total} - see Mission Log (N)", GREEN)
            for mission_id in possessions.completed_missions:
                if mission_id not in completed_before:
                    title = self.missions_config.get(mission_id, {}).get("title", mission_id)
                    self._show_toast(f"Mission complete: {title}", YELLOW)
            self._sync_escorts()

    def update(self):
        """Full update including camera - only called when space is active screen"""
        # This screen only runs update() (rather than the background-only
        # update_physics()) while the player is actually flying it, so it's
        # also the catch-all "in flight now" hook - covers loading a save
        # straight into space, where no board_ship() transition fired.
        self.board_ship()
        # Auto-land when the autopilot brings the ship in. Two checks bracket
        # update_physics(): the pre-check catches has_arrived() being true at
        # the top of the frame (the tight distance/speed SeekMode itself uses
        # to stop, so we don't "give up" braking early with residual speed);
        # the post-check catches SeekMode disengaging *inside* update_physics()
        # - via its own arrival or its looser stall-bailout stop - and
        # finishing near enough to land. `pending` carries the target across
        # update_physics(), which clears autopilot_target once it disengages.
        pending = self.player.autopilot_target if (
            self.player.autopilot_active and self.player.autopilot_target in (self.station, self.moon)) else None

        if self.player.autopilot_active and self.player.autopilot_target and has_arrived(self.player, self.player.autopilot_target):
            target = self.player.autopilot_target
            self.player.park()
            self.player.autopilot_active = False
            self.player.autopilot_target = None
            # Only try to land on landing sites, not ships
            if target == self.station:
                self.landing_target = "station"
                self._mark_landed()
                return "land"
            elif target == self.moon:
                self.landing_target = "moon"
                self._mark_landed()
                return "land"

        self.update_physics()

        # The autopilot disengaged itself this frame (SeekMode's own arrival /
        # stall-bailout inside update_physics(), which uses a looser stop than
        # has_arrived()) - if it left us stopped within landing range of the
        # landing site it was seeking, finish the landing rather than leave the
        # ship parked-but-not-landed for the player to press L.
        if pending is not None and not self.player.autopilot_active:
            speed = math.hypot(self.player.velocity_x, self.player.velocity_y)
            if self.player.get_distance(pending.x, pending.y) < pending.landing_distance and speed < 0.4:
                self.player.park()
                self.landing_target = "station" if pending == self.station else "moon"
                self._mark_landed()
                return "land"

        # Toast counts down only here, not in update_physics() - so one
        # raised while docked (update_physics() still runs in the background
        # then) is still on screen when the player launches back into space.
        if self.toast_timer > 0:
            self.toast_timer -= 1

        # The unread-message ping sounds once per blink of the Message Log
        # light, exactly MESSAGE_ALERT_BLINKS times. Driven here (active
        # screen only, like the toast) rather than in update_physics(), which
        # also runs for background interiors - the alert timer itself still
        # counts down there. The while loop catches up if a slow frame ran
        # several sim steps at once.
        _, pings_due = message_alert_state(self.message_alert_timer)
        while self._message_alert_pings_played < pings_due:
            sound_board.play("ping")
            self._message_alert_pings_played += 1

        # Update camera to follow player, at the current view rotation and
        # zoom. Re-asserted every active frame (an interior leaves its own
        # zoom + limits on the shared camera when the player lands).
        set_camera_offset(self.player.x - GAME_WIDTH // 2, self.player.y - GAME_HEIGHT // 2)
        set_camera_angle(self.camera_angle)
        set_camera_zoom_limits(self.camera_zoom_min, self.camera_zoom_max)
        set_camera_zoom(self.camera_zoom)

        if self.jump_state:
            return  # skip landing checks entirely while jumping

        if self._check_landing():
            self.landing_text = 60
        else:
            self.landing_text = max(0, self.landing_text - 1)

    def draw(self, surface, draw_hud=True):
        """draw_hud=False skips the top-left Controls pane and bottom
        status pane - see LocationScreen.draw's docstring for why (used
        the same way here, when this screen is only being redrawn as the
        backdrop for a modal menu on top of it)."""
        # Re-assert the view rotation and zoom here too, not just in update()
        # - when this screen is only a backdrop for a modal (pause menu,
        # possessions, etc.) update() isn't called, but the stored camera
        # angle/zoom could have been left changed by another screen in between.
        set_camera_angle(self.camera_angle)
        set_camera_zoom_limits(self.camera_zoom_min, self.camera_zoom_max)
        set_camera_zoom(self.camera_zoom)
        surface.fill(BLACK)
        with perf.span("render.starfield"):
            self.star_field.draw(surface)
        with perf.span("render.world"):
            if self.central_star:
                self.central_star.draw(surface)
            for body in self.celestial_bodies:
                body.draw(surface)
            self.station.draw(surface)
            self.moon.draw(surface)
            self.asteroid_field.draw(surface)
            for pickup in self.ore_pickups:
                pickup.draw(surface)
            for projectile in self.projectiles:
                projectile.draw(surface)
            for explosion in self.explosions:
                explosion.draw(surface)
            for ai_ship in self.ai_ships:
                ai_ship.draw(surface)
            self.player.draw(surface)

        # Debug markers for entity positions
        if constants.DEBUG_MODE:
            draw_debug_marker(surface, self.player.x, self.player.y, 10)
            draw_debug_marker(surface, self.station.x, self.station.y, 10)
            draw_debug_marker(surface, self.moon.x, self.moon.y, 10)
            for ai_ship in self.ai_ships:
                draw_debug_marker(surface, ai_ship.x, ai_ship.y, 8)
            for asteroid in self.asteroid_field.asteroids:
                draw_debug_marker(surface, asteroid.x, asteroid.y, 6)

        # Target brackets/arrow are drawn over the world; everything else is
        # the HUD overlay (status panels, messages, help text).
        target_obj = self._get_target_object()
        if target_obj:
            draw_target_brackets(surface, target_obj.x, target_obj.y, size=self._target_bracket_size(target_obj))
            self._draw_target_arrow(surface, target_obj)

        scale = get_scale()
        offset_x, offset_y = get_offset()
        border_rect = (int(offset_x), int(offset_y), int(GAME_WIDTH * scale), int(GAME_HEIGHT * scale))
        pygame.draw.rect(surface, (100, 100, 100), border_rect, 2)

        with perf.span("render.hud"):
            self._draw_hud(surface, target_obj, draw_hud=draw_hud)

        # Active hail conversation, drawn last so it sits on top of the HUD
        # too - same reason LocationScreen draws active_dialogue last.
        if self.active_dialogue:
            self.active_dialogue.draw(surface, get_ui_scale(), flags=self.player.person.possessions.flags, reputation=self.player.person.possessions.reputation)

    def get_state(self):
        state = {
            "player": {
                "x": self.player.x,
                "y": self.player.y,
                "angle": self.player.angle,
                "velocity_x": self.player.velocity_x,
                "velocity_y": self.player.velocity_y,
                "thrust": self.player.thrust,
                "health": self.player.ship.health if self.player.ship else None,
            },
            "possessions": self.player.person.possessions.get_state(),
            # Player's remembered Space View zoom level (mouse wheel). Clamped
            # back into range on restore in case the story's limits changed.
            "camera_zoom": self.camera_zoom,
        }
        if self.jump_state:
            state["jump_state"] = dict(self.jump_state)
        # Every AI ship in every system (not just self.system_id) - keyed by
        # pilot name rather than a per-system list index, since a
        # ExplorerRoutine-driven pilot can migrate to a different system
        # between saves, which a positional index can't survive (the list
        # it "belongs to" at load time may not be the one it was saved
        # from, and may not even be the same length). Ships with no pilot
        # name (ai_ships config entries with no "pilot" key) aren't
        # individually saveable this way and are skipped - same as never
        # being restorable at all before this, just now explicit about it.
        ai_ships = {}
        for sid, sys_state in self.systems.items():
            for ai_ship in sys_state.ai_ships:
                if not ai_ship.person.name:
                    continue
                ai_ships[ai_ship.person.name] = {
                    "system_id": sid,
                    "x": ai_ship.x,
                    "y": ai_ship.y,
                    "angle": ai_ship.angle,
                    "velocity_x": ai_ship.velocity_x,
                    "velocity_y": ai_ship.velocity_y,
                    "thrust": ai_ship.thrust,
                    "health": ai_ship.ship.health,
                }
        if ai_ships:
            state["ai_ships"] = ai_ships
        return state

    def restore_possessions(self, state):
        """Restore just the player's possessions (and re-equip whichever
        ship type that implies). Split out from restore_state() because
        state["player"] means something different depending on where a
        save was made: for a "space" save it's the ship's own position/
        velocity (handled by restore_state()); for a "station"/"moon" save
        it's the *LocationScreen's* walking position instead - a totally
        different coordinate space that main.py must never feed to the
        ship-position half of restore_state() (see park_at(), used
        alongside this one for station/moon loads)."""
        if not state or "possessions" not in state:
            return
        self.player.person.possessions.restore_from(state["possessions"])
        # __init__ always starts the player's Ship from story.json's
        # default type, regardless of what was actually bought before
        # saving - re-equip whichever ship was active (see
        # Possessions.active_ship()), or the ship visibly reverts to
        # that default (e.g. showing a Patrol when a Shuttle was
        # actually being flown) even though possessions itself is correct.
        active = self.player.person.possessions.active_ship()
        if active:
            self._apply_ship_type(active)

    def restore_state(self, state):
        """Full restore for a "space" save - ship position/velocity,
        possessions, and every AI ship. Do NOT use this for a "station"/
        "moon" save; use restore_possessions() + park_at() instead (see
        restore_possessions() for why)."""
        if not state:
            return
        if "camera_zoom" in state:
            self.camera_zoom = self._clamp_zoom(state["camera_zoom"])
        if "player" in state:
            player_state = state["player"]
            self.player.x = player_state.get("x", self.player.x)
            self.player.y = player_state.get("y", self.player.y)
            self.player.angle = player_state.get("angle", self.player.angle)
            self.player.velocity_x = player_state.get("velocity_x", self.player.velocity_x)
            self.player.velocity_y = player_state.get("velocity_y", self.player.velocity_y)
            self.player.thrust = player_state.get("thrust", self.player.thrust)
        saved_jump = state.get("jump_state")
        # Resume an in-progress jump exactly where it left off, rather than
        # leaving the huge jump-speed velocity above with no jump_state to
        # ever bring it back down - previously the ship was left flying at
        # JUMP_SPEED indefinitely (space has no drag), uncontrollable until
        # the player applied thrust and the velocity cap silently clamped it.
        self.jump_state = dict(saved_jump) if saved_jump else None
        self.restore_possessions(state)
        # After restore_possessions/_apply_ship_type has set the real
        # max_health for the owned hull - a mid-flight save can carry a
        # damaged hull (older saves have no "health"; ship stays full).
        if "player" in state and self.player.ship and state["player"].get("health") is not None:
            self.player.ship.health = max(1, min(state["player"]["health"], self.player.ship.max_health))
        # Restore every AI ship in every system, keyed by pilot name (see
        # get_state()) - older saves stored this as a plain per-system list
        # instead (isinstance check below), which this deliberately does
        # NOT try to interpret: there's no reliable way to match its
        # entries back to today's ships once any of them may have migrated
        # between systems, so an old-format save just leaves every AI ship
        # at its freshly-built default rather than guessing wrong.
        saved_ai_ships = state.get("ai_ships")
        if isinstance(saved_ai_ships, dict):
            migrations = []
            for sid, sys_state in self.systems.items():
                for ai_ship in sys_state.ai_ships:
                    saved = saved_ai_ships.get(ai_ship.person.name)
                    if not saved:
                        continue
                    ai_ship.x = saved.get("x", ai_ship.x)
                    ai_ship.y = saved.get("y", ai_ship.y)
                    ai_ship.angle = saved.get("angle", ai_ship.angle)
                    ai_ship.velocity_x = saved.get("velocity_x", ai_ship.velocity_x)
                    ai_ship.velocity_y = saved.get("velocity_y", ai_ship.velocity_y)
                    ai_ship.thrust = saved.get("thrust", ai_ship.thrust)
                    if saved.get("health") is not None:
                        ai_ship.ship.health = max(1, min(saved["health"], ai_ship.ship.max_health))
                    dest_sid = saved.get("system_id", sid)
                    if dest_sid != sid and dest_sid in self.systems:
                        migrations.append((ai_ship, sys_state, dest_sid))
            # Applied after the scan above, not during it - moving a ship
            # out of sys_state.ai_ships while that same list is mid-iteration
            # would skip whichever ship shifts into the removed slot.
            for ai_ship, origin_state, dest_sid in migrations:
                origin_state.ai_ships.remove(ai_ship)
                self.systems[dest_sid].ai_ships.append(ai_ship)
                ai_ship.system_id = dest_sid
