"""SpaceScreen: mining — mixed into the class in screen.py."""
from game.screens.space_screen._defs import *  # noqa: F401,F403


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
        sound_board.play("impact")

        # Damage the asteroid
        if hit_asteroid.take_damage(projectile.damage):
            # Asteroid destroyed
            self._destroy_asteroid(hit_asteroid)

        return True

    def _spawn_impact_explosion(self, x, y):
        """Spark burst at a laser-asteroid impact point (see
        game/world/explosion.py) - fired every hit, not just a
        destroying/final one, so continuous fire against a big asteroid
        reads as a series of hits landing rather than nothing happening
        until it breaks."""
        self.explosions.append(Explosion(x, y))

    def _destroy_asteroid(self, asteroid):
        """Handle asteroid destruction: spawn drifting ore debris, or fragments."""
        # Large asteroids break into smaller fragments
        if asteroid.size > 12:
            self._spawn_asteroid_fragments(asteroid)
        else:
            # Small asteroids scatter their ore as drifting debris (see
            # game/world/ore_pickup.py) - the player has to fly over it with
            # cargo room to actually collect it (_update_ore_pickups), not
            # credited to cargo on the kill directly.
            if asteroid.asteroid_type:
                ore_amount = asteroid.asteroid_type.get("mine_yield", 10)
                self._spawn_ore_debris(asteroid.x, asteroid.y, asteroid.velocity_x, asteroid.velocity_y, ore_amount)

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
        whatever the player has flown over and has cargo room for. A
        pickup is all-or-nothing (needs the player's ship to have room for
        its *entire* amount) rather than a partial top-up - simpler to
        reason about than a chunk that's half-collected and still drifting."""
        possessions = self.player.person.possessions
        ship = self.player.ship
        alive_pickups = []
        for pickup in self.ore_pickups:
            if not pickup.update():
                continue  # Expired - dispersed into nothing

            distance = pickup.get_distance(self.player.x, self.player.y)
            if ship and distance < PICKUP_RANGE + ship.size:
                capacity_remaining = ship.cargo_capacity - possessions.cargo_quantity_total()
                if pickup.amount <= capacity_remaining:
                    possessions.add_cargo(pickup.commodity_id, pickup.amount)
                    # Generic gameplay-event flag (see PlayerController's
                    # "used_turn") - a "mine some ore" tutorial stage can use
                    # this as its complete_flag.
                    possessions.flags["collected_ore"] = True
                    self._show_toast(f"Collected {pickup.amount} ore", CYAN)
                    sound_board.play("pickup")
                    continue  # Collected - drop it, don't keep drifting

            alive_pickups.append(pickup)
        self.ore_pickups = alive_pickups
