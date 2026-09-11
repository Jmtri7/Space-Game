"""SpaceScreen: setup — mixed into the class in screen.py."""
from game.screens.space_screen._defs import *  # noqa: F401,F403


class _SetupMixin:

    def _build_asteroid_types(self, config):
        """Resolve a system's "asteroid_field.types" entries (each just a
        {"type": asteroid_types.json id, "weight": ..., "size_range": ...,
        "speed_range": ...}) into the fully-populated list AsteroidField
        expects - looking up each "type" id's shape/color/jaggedness/spin
        from the story's shared asteroid_types.json, same split as ship_type
        id -> ship_types.json for AI ships above. Falls back to a single
        default gray/round type if the system defines no "asteroid_field"
        block at all, so existing system configs keep working unchanged."""
        type_entries = config.get("asteroid_field", {}).get("types", [{"type": "gray_rock", "weight": 1}])
        types = []
        for entry in type_entries:
            resolved = {"graphics": get_asteroid_type(self.story, entry.get("type", "gray_rock")), "weight": entry.get("weight", 1)}
            if "size_range" in entry:
                resolved["size_range"] = entry["size_range"]
            if "speed_range" in entry:
                resolved["speed_range"] = entry["speed_range"]
            types.append(resolved)
        return types

    def _build_system_events(self, config):
        """Resolve a system's top-level "events" entries (each just a
        {"event": events.json id, "frequency": chance in [0,1] per chunk})
        into (type_cfg, chance) pairs for AsteroidField's independent bonus
        rolls - the "special_asteroid" kind only. See
        _build_pirate_ambush_configs for the "pirate_ambush" kind's own
        resolution/spawn path (a different "frequency" meaning - chance per
        system entry, not per chunk - so it can't share this method); any
        other/unknown kind is just skipped rather than guessed at. Mirrors
        _build_asteroid_types' id -> catalogue resolution, via
        get_system_event/events.json instead of get_asteroid_type/
        asteroid_types.json."""
        events = []
        for entry in config.get("events", []):
            event = get_system_event(self.story, entry.get("event", ""))
            if event.get("kind") != "special_asteroid":
                continue
            type_cfg = {
                "type": entry.get("event"),
                "graphics": event.get("graphics"),
                "mine_yield": event.get("mine_yield", 10),
            }
            if "size_range" in event:
                type_cfg["size_range"] = event["size_range"]
            if "speed_range" in event:
                type_cfg["speed_range"] = event["speed_range"]
            events.append((type_cfg, entry.get("frequency", 0.05)))
        return events

    def _build_pirate_ambush_configs(self, config):
        """Resolve a system's "events" entries of kind "pirate_ambush" into
        (event_def, chance) pairs for SpaceScreen._maybe_spawn_pirate_ambush
        (game/screens/space_screen/pirates.py) - here "frequency" is the
        chance, rolled once per system entry (not per AsteroidField chunk -
        see _build_system_events), that the encounter spawns. event_def is
        passed through mostly as-is (pilot/ship_type/faction ids, tribute,
        spawn_distance, timeout_seconds) - resolving the pilot/ship_type ids
        themselves happens lazily at spawn time, not here, same as
        ai_ships[] entries."""
        configs = []
        for entry in config.get("events", []):
            event = get_system_event(self.story, entry.get("event", ""))
            if event.get("kind") != "pirate_ambush":
                continue
            configs.append((event, entry.get("frequency", 0.05)))
        return configs

    def _build_system_state(self, system_id, config):
        """Build a SystemState (station/moon/central star/celestial bodies/
        AI ships) from one system's static config - called once per system
        the story defines (see self.systems), so every system exists and
        keeps simulating for the rest of the session, not just whichever
        one is active. Asteroid/star fields are built here too, but live on
        SystemState only as scenery kept alive between visits - see
        SystemState's docstring for why only the active system's copies
        ever get their own update() call."""
        space_drag = config.get("drag", 0)

        station_asset_id = config.get("station_asset", "station_alpha")
        moon_asset_id = config.get("moon_asset", "moon_silver")

        station_cfg = config.get("station", {})
        station_graphics = get_graphics_asset(self.story, "space_stations", station_asset_id)
        station = LandingSite(GAME_WIDTH * station_cfg.get("x", 0.75), GAME_HEIGHT * station_cfg.get("y", 0.3), graphics=station_graphics, interiors=station_cfg.get("interiors", {}), name=station_cfg.get("name", "Station"))

        moon_cfg = config.get("moon", {})
        moon_graphics = get_graphics_asset(self.story, "moons", moon_asset_id)
        moon = LandingSite(GAME_WIDTH * moon_cfg.get("x", 0.2), GAME_HEIGHT * moon_cfg.get("y", 0.4), graphics=moon_graphics, interiors=moon_cfg.get("interiors", {}), name=moon_cfg.get("name", "Moon"))

        # Central star (optional, drawn but not a landing site/targetable)
        central_star_cfg = config.get("central_star")
        central_star = CentralStar(GAME_WIDTH * central_star_cfg.get("x", 0.5), GAME_HEIGHT * central_star_cfg.get("y", 0.5), graphics=central_star_cfg) if central_star_cfg else None

        # Non-landing-site planets/ice balls/gas giants - just scenery to fly near,
        # never something you can dock at (see CelestialBody.hazardous, used
        # by the HUD's targeting note).
        celestial_bodies = [
            CelestialBody(GAME_WIDTH * body_cfg.get("x", 0.5), GAME_HEIGHT * body_cfg.get("y", 0.5), graphics=body_cfg)
            for body_cfg in config.get("celestial_bodies", [])
        ]

        state = SystemState(station, moon, central_star, celestial_bodies, ai_ships=[], space_drag=space_drag)
        state.system_id = system_id
        # See SpaceScreen._maybe_spawn_pirate_ambush (pirates.py) - rolled on
        # system (re-)entry, not here (a pirate should find the player
        # wherever they currently are, not spawn at construction time).
        state.pirate_ambush_configs = self._build_pirate_ambush_configs(config)
        state.star_field = StarField(seed=config.get("star_seed", 0))
        # No seed passed - unlike StarField, AsteroidField is meant to look
        # different every time (see its docstring), including the very
        # first chunks generated at game start, not just on revisit.
        state.asteroid_field = AsteroidField(
            types=self._build_asteroid_types(config),
            per_chunk_range=config.get("asteroid_field", {}).get("per_chunk_range", (1, 3)),
            events=self._build_system_events(config),
        )
        # Registered before AI ships are built below (not after) because
        # Character.__init__ runs its routine's start() synchronously -
        # ExplorerRoutine's needs to find this very system already in
        # self.systems the moment the first explorer is constructed.
        self.systems[system_id] = state

        # The full ai_ships config is kept on the SystemState so
        # _sync_conditional_ships() can add/drop flag-gated ships on
        # (re-)entry - see game/world/content_gate.py. Only entries eligible
        # right now are built here.
        state.ai_ship_configs = config.get("ai_ships", [])
        flags = self.player.person.possessions.flags
        reputation = self.player.person.possessions.reputation
        for ai_cfg in state.ai_ship_configs:
            if passes_content_gate(ai_cfg, flags, reputation):
                state.ai_ships.append(self._build_ai_ship(state, ai_cfg))

        return state

    def _build_ai_ship(self, state, ai_cfg):
        """One AI-pilot Character from an `ai_ships[]` config entry, in
        `state`'s system. Split out of _build_system_state so
        _sync_conditional_ships can spawn a flag-gated ship later too."""
        landing_site_lookup = {"station": state.station, "moon": state.moon}
        ship_type_id = ai_cfg.get("ship_type", "freighter")
        route = [landing_site_lookup[k] for k in ai_cfg.get("route", []) if k in landing_site_lookup]
        ai_ship = Character.for_ai_pilot(
            GAME_WIDTH * ai_cfg.get("x", 0.75),
            GAME_HEIGHT * ai_cfg.get("y", 0.1),
            ship_type=get_ship_type(self.story, ship_type_id),
            ship_type_id=ship_type_id,
            graphics=get_graphics_asset(self.story, "ships", ship_type_id),
            pilot=get_pilot(self.story, ai_cfg["pilot"]) if "pilot" in ai_cfg else None,
            route=route,
            get_interior_screen=self.get_interior_screen,
            space_drag=state.space_drag,
            outfit=get_graphics_asset(self.story, "outfits", self.default_outfit_id),
            systems=self.systems,
            system_id=state.system_id,
            faction=ai_cfg.get("faction"),
        )
        ai_ship._spawn_cfg = ai_cfg
        return ai_ship

    def _activate_system(self, system_id):
        """Point every per-system alias (station/moon/ai_ships/...) at the
        already-built SystemState for system_id - called at construction
        and again after a jump completes. Never rebuilds anything (every
        system is built once, in _build_system_state, and kept alive for
        the whole session), and never touches the player except to
        re-apply the destination's own space drag."""
        self.system_id = system_id
        self.system_config = self.system_configs[system_id]
        state = self.systems[system_id]
        self.player.ship.space_drag = state.space_drag
        # Match this system's flag/reputation-gated roster to the player's
        # current state before anything below reads state.ai_ships (the
        # targetable list, self.ai_ship). See _sync_conditional_ships.
        self._sync_conditional_ships()
        # After conditional ships (so a gated ship's removal/add this same
        # frame can't affect it) but before the aliasing below, so a newly
        # spawned pirate is included in self.ai_ships and this frame's
        # targetable_objects build. See pirates.py.
        self._maybe_spawn_pirate_ambush(state)

        self.station = state.station
        self.moon = state.moon
        self.central_star = state.central_star
        self.celestial_bodies = state.celestial_bodies
        self.star_field = state.star_field
        self.asteroid_field = state.asteroid_field
        self.ai_ships = state.ai_ships
        # Keep self.ai_ship for backwards compatibility (first ship if it exists)
        self.ai_ship = state.ai_ships[0] if state.ai_ships else None

        self.current_target = None
        self.target_mode_index = TARGET_MODES.index("LANDING SITES")
        self.targetable_objects = [
            (self.station.name, self.station),
            (self.moon.name, self.moon),
        ]
        if self.central_star:
            self.targetable_objects.append((self.central_star.name, self.central_star))
        for body in self.celestial_bodies:
            self.targetable_objects.append((body.name, body))
        # Add all AI ships to targetable objects. Pilot name is shown
        # separately in the HUD (Character.person.name), not folded into
        # this label, so it stays just the ship type.
        for i, ship in enumerate(self.ai_ships):
            self.targetable_objects.append((self._ship_target_label(ship, i), ship))

    def _apply_ship_type(self, ship_type_id):
        """Configure the player's real ship's stats/graphics to match
        ship_type_id - reapplies the same stat block __init__ applies from
        story.json's starting ship. Used both right after a purchase and
        (via restore_state) after loading a save, since __init__ always
        starts the player's placeholder Ship from story.json's default
        type - a save must re-equip whatever was actually last bought,
        or a save/load round-trip would silently revert to that default."""
        ship_type = get_ship_type(self.story, ship_type_id)
        graphics = get_graphics_asset(self.story, "ships", ship_type_id)
        self.player.ship.apply_ship_type(ship_type)
        self.player.ship.graphics = graphics
        # Re-apply installed outfits' stat modifiers on top of the fresh base
        # stats - covers both the purchase path (_on_ship_purchased) and the
        # load path (restore_possessions), since both funnel through here.
        installed = self.player.person.possessions.installed_outfits
        outfits = [get_ship_outfit(self.story, outfit_id) for outfit_id in installed.values()]
        self.player.ship.apply_outfits(outfits)

    def reapply_outfits(self):
        """Re-apply the current ship's installed outfit stat modifiers -
        call after any outfit equip/unequip (OutfittingMenu, via main.py's
        build_shop_menu) so thrust/velocity/cargo capacity update
        immediately instead of only on the next save/load. Just re-runs
        _apply_ship_type on whatever ship is currently flown, since that
        already re-reads installed_outfits every time (see there)."""
        active = self.player.person.possessions.active_ship()
        if active:
            self._apply_ship_type(active)

    def _apply_start_config(self):
        """Seed the player's Possessions from story.json's "start" block -
        starting credits, a starting ship, spare outfits, personal items,
        story flags, and faction standing (from each faction's
        factions.json starting_standing, plus start.reputation overrides).
        Runs unconditionally in __init__ (exactly like the
        placeholder ship is always built from story.json's default type):
        for a loaded save it's immediately overwritten by
        restore_possessions(); for a new game it is the actual starting
        state. Placement in the world and the tutorial hand-off happen
        separately in begin_new_game(), which main.py calls only for a
        fresh game."""
        start = self.start_config
        possessions = self.player.person.possessions
        possessions.credits = start.get("credits", possessions.credits)
        # Seed standing with every faction from its factions.json
        # starting_standing, then apply any story.json start.reputation
        # overrides. Runs unconditionally like the rest of this method; a
        # loaded save's restore_possessions() overwrites it right after.
        for faction_id, faction in get_factions(self.story).items():
            possessions.reputation.setdefault(faction_id, faction.get("starting_standing", 0))
        for faction_id, standing in start.get("reputation", {}).items():
            possessions.reputation[faction_id] = standing
        for item_id, qty in start.get("items", {}).items():
            possessions.add_item(item_id, qty)
        for outfit_id in start.get("outfits", []):
            possessions.add_outfit(outfit_id)
        for flag_name, value in start.get("flags", {}).items():
            possessions.flags[flag_name] = value
        starting_ship = start.get("ship")
        if starting_ship:
            possessions.add_ship(starting_ship)
            self._apply_ship_type(starting_ship)

    def begin_new_game(self):
        """One-time setup for a brand-new game (never a load): arm the
        story's tutorial mission if its trigger is "new_game" (or if the
        story handed the player a ship, so the "ship_purchase" trigger
        would never get a chance to). Returns (location, interior_key) for
        main.py - where to drop the player: ("space", None),
        ("station", <key>) or ("moon", <key>). Parks a starting ship at
        that landing_site so boarding out from the interior works the same as
        after a purchase."""
        start = self.start_config
        location = start.get("location", "station")
        interior = start.get("interior", "default")
        if self.starting_mission and (
            self.starting_mission_trigger == "new_game"
            or self.player.person.possessions.owned_ships
        ):
            if location == "space":
                self._start_tutorial_mission()
            else:
                # Starting docked - defer to the first launch (board_ship())
                # so the opening toast/hail land in the cockpit, not the bar.
                self.player.person.possessions.flags["starting_mission_armed"] = True
        if self.player.person.possessions.owned_ships:
            if location == "moon":
                self.park_at(self.moon)
            elif location == "station":
                self.park_at(self.station)
        return (location, None if location == "space" else interior)

    def _start_tutorial_mission(self):
        """Start story.json's starting_mission (a no-op if it's already
        active or completed, so a second trigger - buying another ship -
        never restarts it), announcing it with the same toast + first-stage
        message the purchase path uses."""
        if not self.starting_mission:
            return
        started = start_mission(self.missions_config, self.player.person.possessions, self.starting_mission)
        if started:
            title = self.missions_config.get(started[0], {}).get("title", started[0])
            self._show_toast(f"Mission started: {title}", GREEN)
        self._deliver_stage_message(started)

    def _on_ship_purchased(self, ship_type_id):
        """Configure the player's real ship to match a newly bought type,
        and park it right at the station - so it's "docked outside" exactly
        as a salesman's dialogue would say, ready the moment the player
        boards through the spaceport's exit. For a "ship_purchase" trigger
        this also *arms* the story's starting_mission - it doesn't start
        until the player actually launches (board_ship()), so the tutorial
        and Kade's opening hail don't fire while they're still standing in
        the shop having just bought the ship."""
        self._apply_ship_type(ship_type_id)
        self.park_at(self.station)
        possessions = self.player.person.possessions
        if (self.starting_mission_trigger == "ship_purchase" and self.starting_mission
                and self.starting_mission not in possessions.missions
                and self.starting_mission not in possessions.completed_missions):
            possessions.flags["starting_mission_armed"] = True

    def _on_ship_switched(self, ship_type_id):
        """Re-configure and re-park the player's real ship after the ship
        salesman's "Your Ships" tab makes a different owned hull active
        (see LocationScreen.switch_ship / Possessions.set_active_ship) -
        the same reconfigure + dock-outside step a purchase does, minus the
        credit spend and tutorial arming."""
        self._apply_ship_type(ship_type_id)
        self.park_at(self.station)
