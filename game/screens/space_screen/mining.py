"""SpaceScreen: mining — mixed into the class in screen.py."""
from game.screens.space_screen._defs import *  # noqa: F401,F403
from game.world.miner_routine import MinerRoutine, URGENT_DODGE_SEVERITY, EXIT_DODGE_SEVERITY
from game.world.asteroid_avoidance import steer_away_from_asteroids

# --- Ship-asteroid collision physics (see combat-and-mining.md's
# "Ship-asteroid collisions" section). Both "mass" values are size**this -
# an area-like stand-in, not a literal physical mass, tuned for feel rather
# than derived from anything - same spirit as Asteroid's own size-based
# health formula. ---
COLLISION_MASS_EXPONENT = 2
COLLISION_RESTITUTION = 0.55         # fraction of a full elastic bounce actually applied - a damped, absorbed hit rather than a billiard-ball bounce
SHIP_COLLISION_DAMAGE_COEFF = 0.03   # ship hull damage ~= asteroid.size * relative_speed**2 * this - quadratic in speed, so only a big and/or fast rock really hurts
ASTEROID_COLLISION_DAMAGE_COEFF = 1.0  # asteroid damage ~= (ship.size + 5) * relative_speed * this - big enough that most asteroids break up or explode on a real hit

# --- Opportunistic asteroid-clearing (every AI ship, any role - see
# extensibility.md's Q&A: this never steers, only fires when an asteroid
# happens to already be dead ahead of whatever heading the ship's own
# routine chose, so it can never fight autopilot/SeekMode for control). ---
CLEARING_RANGE = 200
CLEARING_CONE_DEG = 12

# --- Station point-defense laser (see combat-and-mining.md) ---
STATION_DEFENSE_RANGE = 650
STATION_DEFENSE_INTERVAL = 150   # frames between shots - slow, ~2.5s at 60fps
STATION_DEFENSE_DAMAGE = 55
STATION_DEFENSE_SPEED = 3
STATION_DEFENSE_SIZE = 9


def _collision_mass(size):
    return max(1.0, size) ** COLLISION_MASS_EXPONENT


def _lead_intercept(target_x, target_y, target_vx, target_vy, shooter_x, shooter_y, shot_speed):
    """Where a shot fired from (shooter_x, shooter_y) at constant speed
    `shot_speed` should aim to meet a target currently at (target_x,
    target_y) moving at constant (target_vx, target_vy) - the standard
    constant-velocity firing-solution intercept, not just "aim at where it
    is now" (which a slow shot at a moving target would usually miss).
    Solves |target_pos + target_vel*t - shooter_pos| = shot_speed*t for the
    smallest positive t and returns the predicted position at that time;
    falls back to the target's current position if no positive-time
    solution exists (e.g. it's already outrunning the shot)."""
    rx, ry = target_x - shooter_x, target_y - shooter_y
    a = target_vx * target_vx + target_vy * target_vy - shot_speed * shot_speed
    b = 2 * (rx * target_vx + ry * target_vy)
    c = rx * rx + ry * ry
    if abs(a) < 1e-6:
        t = -c / b if abs(b) > 1e-6 else -1
    else:
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            t = -1
        else:
            sqrt_disc = math.sqrt(discriminant)
            candidates = [r for r in ((-b + sqrt_disc) / (2 * a), (-b - sqrt_disc) / (2 * a)) if r > 0]
            t = min(candidates) if candidates else -1
    if t <= 0:
        return target_x, target_y
    return target_x + target_vx * t, target_y + target_vy * t


class _MiningMixin:

    def _check_projectile_asteroid_collision(self, projectile):
        """Check if projectile hits an asteroid; damage it and handle breakup/mining.

        Collision radius is asteroid.size (roughly the asteroid's own drawn
        radius - see Asteroid.draw, both the round-circle and jagged cases
        scale their silhouette off `size`) plus a small allowance for the
        projectile's own size, so a shot only registers within the rock's
        actual silhouette instead of a small fixed radius that barely
        covers a big asteroid's center. On overlap with more than one
        asteroid (rare, but possible where two drift close together) the
        one it's penetrated deepest into wins, not just whichever sorts
        first."""
        hit_asteroid = None
        best_penetration = -1
        for asteroid in self.asteroid_field.asteroids:
            collision_radius = asteroid.size + projectile.size
            dist = math.hypot(projectile.x - asteroid.x, projectile.y - asteroid.y)
            penetration = collision_radius - dist
            if penetration > best_penetration:
                best_penetration = penetration
                hit_asteroid = asteroid

        if hit_asteroid is None or best_penetration < 0:
            return False

        self._spawn_impact_explosion(projectile.x, projectile.y)
        sound_board.play("explosion_small")

        # Damage the asteroid
        if hit_asteroid.take_damage(projectile.damage):
            # Asteroid destroyed - a miner's own shot credits its ore
            # straight to that miner's hold (see _destroy_asteroid's
            # `destroyer` param) rather than leaving it as a drifting pickup
            # for it to then fly back over. Anyone else's shot (the player's,
            # some other NPC's opportunistic clearing shot, or the station's
            # point-defense) is handled by _destroy_asteroid's own rules.
            self._destroy_asteroid(hit_asteroid, destroyer=projectile.owner)

        return True

    def _spawn_impact_explosion(self, x, y):
        """Spark burst at a laser-asteroid impact point (see
        game/world/explosion.py) - fired every hit, not just a
        destroying/final one, so continuous fire against a big asteroid
        reads as a series of hits landing rather than nothing happening
        until it breaks."""
        self.explosions.append(Explosion(x, y))

    def _destroy_asteroid(self, asteroid, destroyer=None):
        """Handle asteroid destruction: spawn drifting ore debris, or
        fragments. `destroyer` is whoever/whatever landed the killing hit -
        `self.player`, an AI `Character`, the bare string `"station"` (point-
        defense, see _update_station_defense), or None:

        - The player: ore scatters as drifting debris the player has to fly
          over to collect (_update_ore_pickups) - same as always.
        - A miner (MinerRoutine) AI: its ore goes straight into its own
          cargo hold instead of drifting, since NPCs don't fly over/collect
          items from space.
        - Anything else (a non-miner AI's opportunistic clearing shot, the
          station's own point-defense, or unknown) - no ore at all. Letting
          NPCs/the station drop minable ore would just tempt the player to
          scoop up loot they didn't mine themselves."""
        sound_board.play("explosion_big")
        # Large asteroids break into smaller fragments
        if asteroid.size > 12:
            self._spawn_asteroid_fragments(asteroid)
        elif asteroid.asteroid_type:
            ore_amount = asteroid.asteroid_type.get("mine_yield", 10)
            if destroyer is self.player:
                # Scatter as drifting debris (see game/world/ore_pickup.py)
                # - only the player can fly over and collect it.
                self._spawn_ore_debris(asteroid.x, asteroid.y, asteroid.velocity_x, asteroid.velocity_y, ore_amount)
            elif isinstance(getattr(destroyer, "routine", None), MinerRoutine) and destroyer.ship:
                possessions = destroyer.person.possessions
                capacity_remaining = destroyer.ship.cargo_capacity - possessions.cargo_quantity_total()
                collected = max(0, min(ore_amount, capacity_remaining))
                if collected:
                    possessions.add_cargo("ore", collected)
            # else: no ore - a non-miner NPC or the station's point-defense
            # broke it, nothing drops.

        # Remove from field - this is tricky since it's managed by AsteroidField
        # We need to find and remove it from the appropriate chunk
        for chunk_asteroids in self.asteroid_field.chunk_asteroids.values():
            if asteroid in chunk_asteroids:
                chunk_asteroids.remove(asteroid)
                break

    def _spawn_asteroid_fragments(self, asteroid):
        """Break a large asteroid into smaller fragments flying apart."""
        fragment_count = random.randint(2, 4)
        fragment_size_min = asteroid.size * 0.4
        fragment_size_max = asteroid.size * 0.65

        for _ in range(fragment_count):
            frag_size = random.uniform(fragment_size_min, fragment_size_max)
            # Fragment velocity: add random outward velocity to base asteroid velocity
            angle_offset = random.uniform(0, 2 * math.pi)
            outward_speed = random.uniform(0.5, 2.0)
            frag_vel_x = asteroid.velocity_x + math.cos(angle_offset) * outward_speed
            frag_vel_y = asteroid.velocity_y + math.sin(angle_offset) * outward_speed

            fragment = Asteroid(
                asteroid.x, asteroid.y,
                velocity_x=frag_vel_x, velocity_y=frag_vel_y,
                size=frag_size, graphics=asteroid.graphics,
                asteroid_type=asteroid.asteroid_type
            )
            # Add fragment to an appropriate chunk
            cx = int(asteroid.x // 1200)  # CHUNK_SIZE from asteroid_field
            cy = int(asteroid.y // 1200)
            if (cx, cy) not in self.asteroid_field.chunk_asteroids:
                self.asteroid_field.chunk_asteroids[(cx, cy)] = []
            self.asteroid_field.chunk_asteroids[(cx, cy)].append(fragment)

        # Remove the original asteroid
        for chunk_asteroids in self.asteroid_field.chunk_asteroids.values():
            if asteroid in chunk_asteroids:
                chunk_asteroids.remove(asteroid)
                break

    def _spawn_ore_debris(self, x, y, base_velocity_x, base_velocity_y, total_amount):
        """Scatter total_amount of ore as 1-3 separate OrePickup chunks
        drifting outward from (x, y) - a debris field rather than one static
        pile, matching the fragments a destroyed asteroid already leaves
        behind. Each chunk's own drift (see OrePickup.__init__) is layered
        on top of the source asteroid's velocity, so debris from a fast-
        moving asteroid keeps some of that motion instead of snapping to a
        dead stop."""
        commodity = get_commodity(self.story, "ore")
        icon_shape = commodity.get("icon_shape", "crate")
        icon_color = tuple(commodity.get("icon_color", (150, 110, 80)))

        chunk_count = min(total_amount, random.randint(1, 3))
        base_share = total_amount // chunk_count
        remainder = total_amount - base_share * chunk_count
        for i in range(chunk_count):
            amount = base_share + (1 if i < remainder else 0)
            if amount <= 0:
                continue
            pickup = OrePickup(x, y, amount, commodity_id="ore", icon_shape=icon_shape, icon_color=icon_color)
            pickup.velocity_x += base_velocity_x
            pickup.velocity_y += base_velocity_y
            self.ore_pickups.append(pickup)

    def _update_ore_pickups(self):
        """Advance drifting ore chunks, expire old ones, and collect
        whatever the player has flown over. NPCs never pick up drifting
        items - a miner's own kills go straight to its hold instead (see
        `_destroy_asteroid`'s `destroyer` param), so only the player is a
        collector here. A pickup tops the collector's hold up to whatever
        fits (`capacity_remaining`), decrements its own `amount` by that
        much, and keeps drifting with the leftover rather than being all-or-
        nothing - so a chunk bigger than the remaining hold space isn't
        just left untouched."""
        collectors = [self.player]
        alive_pickups = []
        for pickup in self.ore_pickups:
            if not pickup.update():
                continue  # Expired - dispersed into nothing

            for mover in collectors:
                ship = mover.ship
                if not ship:
                    continue
                distance = pickup.get_distance(mover.x, mover.y)
                if distance >= PICKUP_RANGE + ship.size:
                    continue
                possessions = mover.person.possessions
                capacity_remaining = ship.cargo_capacity - possessions.cargo_quantity_total()
                if capacity_remaining <= 0:
                    if mover is self.player:
                        # In range but no room at all - flash a warning
                        # instead of silently ignoring it. _show_toast
                        # re-arms its own timer every call, so this stays up
                        # for as long as the player sits over the ore rather
                        # than flickering.
                        self._show_toast("CARGO FULL", RED)
                    continue
                collected = min(pickup.amount, capacity_remaining)
                possessions.add_cargo(pickup.commodity_id, collected)
                pickup.amount -= collected
                if mover is self.player:
                    # Generic gameplay-event flag (see PlayerController's
                    # "used_turn") - a "mine some ore" tutorial stage can use
                    # this as its complete_flag.
                    possessions.flags["collected_ore"] = True
                    self._show_toast(f"Collected {collected} ore", CYAN)
                    sound_board.play("pickup")
                break  # this pickup's claimed (fully or partially) for the frame - don't also offer the leftover to the next collector

            if pickup.amount > 0:
                alive_pickups.append(pickup)
        self.ore_pickups = alive_pickups

    def _resolve_ship_asteroid_hit(self, mover, asteroid):
        """`mover` is either self.player or an AI Character whose ship
        physically overlaps `asteroid`. Exchange momentum along the line of
        centers (a damped elastic collision - see COLLISION_RESTITUTION),
        separate the two so they don't keep re-overlapping next frame, then
        damage both sides off the resulting relative speed - see the
        SHIP_COLLISION_DAMAGE_COEFF/ASTEROID_COLLISION_DAMAGE_COEFF comments
        above for why the asteroid usually loses far worse than the ship
        does. A destroyed asteroid breaks up/drops ore exactly like one shot
        down (_destroy_asteroid); a destroyed ship explodes exactly like one
        shot down (_destroy_ship / _on_player_destroyed)."""
        ship = mover.ship
        dx = ship.x - asteroid.x
        dy = ship.y - asteroid.y
        dist = math.hypot(dx, dy)
        if dist < 0.01:
            dx, dy, dist = 1.0, 0.0, 1.0
        nx, ny = dx / dist, dy / dist

        rel_vx = ship.velocity_x - asteroid.velocity_x
        rel_vy = ship.velocity_y - asteroid.velocity_y
        relative_speed = math.hypot(rel_vx, rel_vy)

        ship_mass = _collision_mass(ship.size)
        asteroid_mass = _collision_mass(asteroid.size)
        total_mass = ship_mass + asteroid_mass
        rel_dot = rel_vx * nx + rel_vy * ny
        if rel_dot < 0:  # only exchange momentum while actually closing
            ship_impulse = (2 * asteroid_mass / total_mass) * rel_dot * COLLISION_RESTITUTION
            ship.velocity_x -= ship_impulse * nx
            ship.velocity_y -= ship_impulse * ny
            asteroid_impulse = (2 * ship_mass / total_mass) * (-rel_dot) * COLLISION_RESTITUTION
            asteroid.velocity_x += asteroid_impulse * nx
            asteroid.velocity_y += asteroid_impulse * ny

        overlap = (ship.size + asteroid.size) - dist
        if overlap > 0:
            ship.x += nx * overlap
            ship.y += ny * overlap

        self._spawn_impact_explosion(asteroid.x, asteroid.y)
        sound_board.play("impact")

        if asteroid.take_damage(ASTEROID_COLLISION_DAMAGE_COEFF * (ship.size + 5) * relative_speed):
            self._destroy_asteroid(asteroid, destroyer=mover)

        if ship.take_damage(SHIP_COLLISION_DAMAGE_COEFF * asteroid.size * relative_speed ** 2):
            if mover is self.player:
                self._on_player_destroyed()
            else:
                self._destroy_ship(mover)

    def _check_ship_asteroid_collisions(self):
        """The player (while actually flying, and not mid-jump) and every
        AI ship in the active system (not `ashore`, not mid-jump) that
        physically overlaps a live asteroid takes a momentum-transfer hit -
        see _resolve_ship_asteroid_hit. Asteroids are single-system scenery
        (AsteroidField only streams chunks for whichever system is active -
        see PHYSICS.md), so, like every other asteroid interaction, only
        self.asteroid_field is ever checked.

        A ship mid-jump (`self.jump_state` for the player, `character.jumping`
        for an AI pilot - see ExplorerRoutine/jump.py) is excluded outright:
        the jump animation drives its position directly at a speed and along
        a path that has nothing to do with normal flight, so a rock happening
        to sit on that line shouldn't stop (or even visibly affect) a ship
        that's supposed to be passing clean through on its way out of the
        system - the fiction is a jump drive, not a physical transit through
        local space."""
        if not self.asteroid_field.asteroids:
            return
        movers = [self.player] if self.in_flight and not self.game_over and not self.jump_state and self.player.ship else []
        movers += [s for s in self.ai_ships if s.ship and not s.ashore and not s.jumping]
        for mover in movers:
            ship = mover.ship
            hit = None
            best = -1
            for asteroid in self.asteroid_field.asteroids:
                r = ship.size + asteroid.size
                pen = r - math.hypot(ship.x - asteroid.x, ship.y - asteroid.y)
                if pen > best and pen >= 0:
                    best, hit = pen, asteroid
            if hit is not None:
                self._resolve_ship_asteroid_hit(mover, hit)

    def _update_ai_asteroid_dodge(self):
        """Every AI ship in the active system checks whether any nearby
        asteroid's predicted path is about to cross its own (a real
        closest-point-of-approach prediction, not just "something's
        nearby" - see game/world/asteroid_avoidance.py) and, if so, nudges
        itself clear while pursuing whatever its own routine has it doing.
        This is a velocity nudge, never a steering command, so it's safe to
        apply on top of *any* routine, autopilot-driven or not (see that
        module's own docstring for why). MinerRoutine already calls this
        itself (excluding its own hunted asteroid) with its own priority
        gate on firing/approach, so it's skipped here to avoid double-
        dodging the same frame. The resulting severity is stashed on the
        Character (`_dodge_severity`) so _update_ai_asteroid_clearing below
        can also stand down its opportunistic shot while a ship is mid-dodge."""
        asteroids = self.asteroid_field.asteroids
        for ship in self.ai_ships:
            if ship.ashore or not ship.ship or isinstance(ship.routine, MinerRoutine) or not asteroids:
                ship._dodge_severity = 0.0
                ship._dodging = False
                continue
            severity = steer_away_from_asteroids(ship, asteroids, urgency=getattr(ship, "dodge_urgency", 1.0))
            ship._dodge_severity = severity
            # Sticky, same hysteresis reasoning as MinerRoutine's own
            # _dodging flag (see miner_routine.py's EXIT_DODGE_SEVERITY
            # comment) - severity hovering right at the threshold shouldn't
            # flip whether a ship's opportunistic shot is standing down
            # every single frame.
            dodging = getattr(ship, "_dodging", False)
            ship._dodging = severity > EXIT_DODGE_SEVERITY if dodging else severity > URGENT_DODGE_SEVERITY

    def _update_ai_asteroid_clearing(self):
        """Any AI ship not already fighting the player, not mid-dodge (see
        `_dodging` above - trajectory safety comes first), and not a
        miner (MinerRoutine already actively hunts and shoots its own
        target), takes an opportunistic shot at an asteroid that happens to
        already be dead ahead and close. This never steers to line one up -
        doing so would fight whatever's actually driving the ship, autopilot
        included (see docs/AUTOPILOT_TESTING.md) - so it only ever fires
        when the ship's current heading, chosen entirely by its own
        routine, already lines up with a blocking rock."""
        asteroids = self.asteroid_field.asteroids
        if not asteroids:
            return
        for ship in self.ai_ships:
            if ship.ashore or not ship.ship or ship.in_combat or ship.firing or isinstance(ship.routine, MinerRoutine):
                continue
            if getattr(ship, "_dodging", False):
                continue
            nose_rad = math.radians(ship.angle)
            nose_x, nose_y = math.sin(nose_rad), -math.cos(nose_rad)
            for asteroid in asteroids:
                dx = asteroid.x - ship.x
                dy = asteroid.y - ship.y
                dist = math.hypot(dx, dy)
                if dist < 1 or dist > CLEARING_RANGE:
                    continue
                cos_bearing = max(-1.0, min(1.0, (dx * nose_x + dy * nose_y) / dist))
                if math.degrees(math.acos(cos_bearing)) < CLEARING_CONE_DEG:
                    ship.firing = True
                    break

    def _update_station_defense(self):
        """The active system's station periodically fires a slow, heavy
        shot at the nearest asteroid within STATION_DEFENSE_RANGE - a big,
        one/two-shot laser that keeps the belt clear right around the dock
        for everyone nearby, not just the player's own mining. Reuses the
        shared projectile pipeline with owner="station" (a plain string,
        not a Character) - combat.py's hostility gate on
        `_check_projectile_ship_collision` (`getattr(owner, "in_combat",
        False)`) always reads False for a bare string, so this shot can
        only ever land on an asteroid, never a ship. The shot is slow
        (STATION_DEFENSE_SPEED) relative to a drifting asteroid, so aiming
        straight at where the target is *now* would usually miss outright
        - see _lead_intercept for the actual aim solve."""
        state = self.systems[self.system_id]
        cooldown = getattr(state, "station_defense_cooldown", 0)
        if cooldown > 0:
            state.station_defense_cooldown = cooldown - 1
            return
        station = self.station
        nearest = None
        nearest_dist = STATION_DEFENSE_RANGE
        for asteroid in self.asteroid_field.asteroids:
            dist = math.hypot(asteroid.x - station.x, asteroid.y - station.y)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = asteroid
        if nearest is None:
            return
        aim_x, aim_y = _lead_intercept(
            nearest.x, nearest.y, nearest.velocity_x, nearest.velocity_y,
            station.x, station.y, STATION_DEFENSE_SPEED,
        )
        dx, dy = aim_x - station.x, aim_y - station.y
        aim_angle = math.degrees(math.atan2(dx, -dy))
        rad = math.radians(aim_angle)
        vx, vy = math.sin(rad) * STATION_DEFENSE_SPEED, -math.cos(rad) * STATION_DEFENSE_SPEED
        lifetime = int(STATION_DEFENSE_RANGE / STATION_DEFENSE_SPEED) + 30
        self.projectiles.append(Projectile(
            station.x, station.y, vx, vy, angle=aim_angle,
            icon_shape="blade", icon_color=(255, 90, 90),
            size=STATION_DEFENSE_SIZE, damage=STATION_DEFENSE_DAMAGE,
            lifetime=lifetime, owner="station",
        ))
        sound_board.play("laser")
        state.station_defense_cooldown = STATION_DEFENSE_INTERVAL
