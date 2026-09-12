"""Everything about one star system that must keep existing independently of
whether the player is currently in it."""


class SystemState:
    """A system's station, moon, decorative scenery, and AI ships - built
    once (see SpaceScreen.systems) and kept alive for the rest of the
    session, so a system the player has jumped away from keeps ticking in
    the background instead of being discarded and rebuilt from scratch on
    return. The asteroid field and star field are deliberately NOT tracked
    here: both are purely decorative, driven by the camera (see
    AsteroidField._visible_chunk_range), and never visible or interactive
    while their system isn't the one actually being rendered - only the
    active system's copies need touching each frame (see
    SpaceScreen.update_physics), so SpaceScreen keeps those two itself."""
    def __init__(self, station, moon, central_star, celestial_bodies, ai_ships, space_drag=0):
        self.station = station
        self.moon = moon
        self.central_star = central_star
        self.celestial_bodies = celestial_bodies
        self.ai_ships = ai_ships
        self.space_drag = space_drag  # reapplied to the player's ship on activation (see SpaceScreen._activate_system)
        # Set by SpaceScreen._build_system_state: this system's id, and its
        # full (unfiltered) ai_ships config - the latter so
        # _sync_conditional_ships() can add/drop flag-gated ships on
        # (re-)entry (see game/world/content_gate.py). ai_ships above holds
        # only the ships eligible right now.
        self.system_id = None
        self.ai_ship_configs = []
        # Countdown to this system's station's next point-defense shot (see
        # SpaceScreen._update_station_defense) - lives here, not on
        # SpaceScreen, so each system's station keeps its own independent
        # cooldown/timing.
        self.station_defense_cooldown = 0
        # Which live Asteroid objects a MinerRoutine pilot in this system
        # has already picked as its hunting target (see miner_routine.py's
        # _claim/_release_claim) - lets several miners in the same belt
        # split up instead of dogpiling the same rock. A plain set of
        # Asteroid references, not persisted (asteroids themselves aren't
        # saveable scenery either - see SAVE_SYSTEM.md).
        self.claimed_asteroids = set()

    def update_physics(self):
        """Advance this system's station/moon rotation, celestial bodies,
        and AI ship pilots by one frame. Camera-independent, so this is
        safe to call every frame for every system regardless of which one
        the player currently occupies.

        Iterates a snapshot of ai_ships, not the live list - an
        ExplorerRoutine mid-update can remove its own character from this
        very list (see ExplorerRoutine._migrate), and mutating a list while
        iterating it would silently skip whichever ship ends up shifted
        into the removed slot."""
        self.station.update()
        self.moon.update()
        for body in self.celestial_bodies:
            body.update()
        for ai_ship in list(self.ai_ships):
            ai_ship.update()

    def orbit_targets(self):
        """Every landing site / celestial object in this system that something
        could plausibly orbit - used by ExplorerRoutine to pick a random
        destination once it arrives."""
        targets = [self.station, self.moon]
        if self.central_star:
            targets.append(self.central_star)
        targets.extend(self.celestial_bodies)
        return targets
