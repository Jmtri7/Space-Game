"""SpaceScreen: combat — mixed into the class in screen.py."""
from game.screens.space_screen._defs import *  # noqa: F401,F403


class _CombatMixin:

    def _equipped_weapon_stats(self):
        """Full stat dict for whatever's installed in the flown ship's first
        weapon slot, or None when the flown hull has weapon slots but none
        of them is filled (an unarmed ship fires nothing). The slot-less
        legacy placeholder ship falls back to the laser cannon's own config
        so it can still fire something. Every field falls back individually
        to the laser cannon so a partial weapon config still resolves to a
        real weapon's config, never a partial or missing one. `.get(key, laser_cannon's value)` per-field
        (not a whole-dict fallback) so a weapon outfit that only overrides
        some fields still inherits sane defaults for the rest.

        `inaccuracy` (degrees) is per-shot random aim wobble, applied to
        every pellet a weapon fires (a precise weapon sets it to 0);
        `pellet_spread` (degrees) is the fixed fan arc `projectile_count`
        pellets are evenly distributed across, independent of inaccuracy -
        the two are separate stats so a weapon can be single-shot-but-
        imprecise (pulse_blaster), multi-pellet-in-a-fan (scatter_gun), or
        (in principle) both at once. See ship_outfits.json's
        laser_cannon/pulse_blaster/heavy_cannon/scatter_gun for the range
        this spans."""
        possessions = self.player.person.possessions
        ship_type_id = possessions.active_ship()
        weapon_outfit_id = None
        if ship_type_id:
            ship_type = get_ship_type(self.story, ship_type_id)
            weapon_slots = [s for s in ship_type.get("slots", []) if s.get("type") == "weapon"]
            for slot in weapon_slots:
                installed = possessions.installed_outfits.get(slot["id"])
                if installed:
                    weapon_outfit_id = installed
                    break
            if weapon_slots and not weapon_outfit_id:
                # A real hull with weapon slots but nothing installed fires
                # nothing - only the slot-less legacy placeholder ship (below)
                # gets the free laser_cannon.
                return None
        baseline = get_ship_outfit(self.story, "laser_cannon")
        outfit = get_ship_outfit(self.story, weapon_outfit_id or "laser_cannon")
        return {
            "icon_shape": outfit.get("icon_shape", baseline.get("icon_shape", "blade")),
            "icon_color": tuple(outfit.get("icon_color", baseline.get("icon_color", (100, 200, 255)))),
            "damage": outfit.get("damage", baseline.get("damage", PROJECTILE_DAMAGE)),
            "fire_rate": outfit.get("fire_rate", baseline.get("fire_rate", 18)),
            "projectile_speed": outfit.get("projectile_speed", baseline.get("projectile_speed", PROJECTILE_SPEED)),
            "projectile_size": outfit.get("projectile_size", baseline.get("projectile_size", PROJECTILE_SIZE)),
            "projectile_lifetime": outfit.get("projectile_lifetime", baseline.get("projectile_lifetime", PROJECTILE_LIFETIME)),
            "inaccuracy": outfit.get("inaccuracy", baseline.get("inaccuracy", 0)),
            "pellet_spread": outfit.get("pellet_spread", baseline.get("pellet_spread", 0)),
            "projectile_count": max(1, outfit.get("projectile_count", baseline.get("projectile_count", 1))),
            "fire_sound": outfit.get("fire_sound", baseline.get("fire_sound", "laser")),
        }

    def _fire_weapon(self, shooter, stats, aim_angle, owner):
        """Spawn this shot's projectile(s) from `shooter` (anything with
        live x/y/velocity_x/velocity_y and a `.ship`) toward `aim_angle`
        (degrees), tagged with `owner` ("player" or an AI Character). One
        shot for a single-pellet weapon (randomly offset within
        `inaccuracy` degrees, if any), or `projectile_count` pellets fanned
        evenly across `pellet_spread` degrees - each also independently
        offset by `inaccuracy` - for a shotgun-style one. Shared by the
        player (SPACE) and hostile AI (CombatRoutine); plays the fire
        sound. Returns nothing - the caller owns cooldown bookkeeping."""
        count = stats["projectile_count"]
        inaccuracy = stats["inaccuracy"]
        pellet_spread = stats["pellet_spread"]
        nose = shooter.ship.size

        def wobble():
            return random.uniform(-inaccuracy / 2, inaccuracy / 2) if inaccuracy else 0

        if count == 1:
            fire_angles = [aim_angle + wobble()]
        else:
            fire_angles = [
                aim_angle - pellet_spread / 2 + pellet_spread * i / (count - 1) + wobble()
                for i in range(count)
            ]

        for fire_angle in fire_angles:
            rad = math.radians(fire_angle)
            px = shooter.x + math.sin(rad) * nose
            py = shooter.y - math.cos(rad) * nose
            vx = shooter.velocity_x + math.sin(rad) * stats["projectile_speed"]
            vy = shooter.velocity_y - math.cos(rad) * stats["projectile_speed"]
            # Orient the drawn icon to the shot's actual resultant travel
            # direction (velocity vector), not the raw aim angle - see the
            # long note this replaced; the two differ once the ship's own
            # velocity is folded in.
            travel_angle = math.degrees(math.atan2(vx, -vy))
            self.projectiles.append(Projectile(
                px, py, vx, vy, angle=travel_angle,
                icon_shape=stats["icon_shape"], icon_color=stats["icon_color"],
                size=stats["projectile_size"], damage=stats["damage"],
                lifetime=stats["projectile_lifetime"], owner=owner,
            ))
        sound_board.play(stats["fire_sound"])

    def _update_weapon_fire(self):
        """Player weapon fire (SPACE held) - fires the equipped weapon if
        its cooldown allows and the flown ship actually has one installed."""
        if self.weapon_fire_cooldown > 0 or not self.player.ship:
            return
        stats = self._equipped_weapon_stats()
        if stats is None:
            return
        self._fire_weapon(self.player, stats, self.player.angle, owner="player")
        self.weapon_fire_cooldown = stats["fire_rate"]

    def _ai_weapon_stats(self):
        """The weapon a hostile AI ship fires - the story's laser_cannon
        baseline, at a slower fire rate so a dogfight with the player isn't
        a one-sided wall of fire. Field-for-field like
        _equipped_weapon_stats so _fire_weapon reads it identically."""
        w = get_ship_outfit(self.story, "laser_cannon")
        return {
            "icon_shape": w.get("icon_shape", "blade"),
            "icon_color": tuple(w.get("icon_color", (255, 130, 110))),
            "damage": w.get("damage", PROJECTILE_DAMAGE),
            "fire_rate": max(30, int(w.get("fire_rate", 18) * 2)),
            "projectile_speed": w.get("projectile_speed", PROJECTILE_SPEED),
            "projectile_size": w.get("projectile_size", PROJECTILE_SIZE),
            "projectile_lifetime": w.get("projectile_lifetime", PROJECTILE_LIFETIME),
            "inaccuracy": max(4, w.get("inaccuracy", 0)),
            "pellet_spread": 0,
            "projectile_count": 1,
            "fire_sound": w.get("fire_sound", "laser"),
        }

    def _update_ai_weapon_fire(self):
        """Let each hostile AI ship in the active system (CombatRoutine set
        character.firing this frame) shoot at the player, rate-limited by
        its own per-character cooldown. Skipped while docked (not in_flight)
        - a parked ship isn't in the fight."""
        if not self.in_flight:
            return
        stats = self._ai_weapon_stats()
        for ship in self.ai_ships:
            cd = getattr(ship, "ai_fire_cooldown", 0)
            if cd > 0:
                ship.ai_fire_cooldown = cd - 1
                continue
            if getattr(ship, "firing", False) and not ship.ashore and ship.ship:
                self._fire_weapon(ship, stats, ship.angle, owner=ship)
                ship.ai_fire_cooldown = stats["fire_rate"]

    def _update_projectiles(self):
        """Update all projectiles; handle collisions with asteroids and ships."""
        alive_projectiles = []
        for projectile in self.projectiles:
            if not projectile.update():
                continue  # Projectile expired
            if self._check_projectile_asteroid_collision(projectile):
                continue  # destroyed on impact
            if self._check_projectile_ship_collision(projectile):
                continue
            alive_projectiles.append(projectile)

        self.projectiles = alive_projectiles

    def _check_projectile_ship_collision(self, projectile):
        """A player-fired shot hits any AI ship in the active system; an
        AI-fired shot hits the player. A shot never hits its own owner.
        Returns True (and applies damage / destruction) if it connected."""
        if projectile.owner == "player":
            hit = None
            best = -1
            for ship in self.ai_ships:
                if ship.ashore or not ship.ship:
                    continue
                r = ship.ship.size + projectile.size
                pen = r - math.hypot(projectile.x - ship.x, projectile.y - ship.y)
                if pen > best and pen >= 0:
                    best, hit = pen, ship
            if hit is None:
                return False
            self._spawn_impact_explosion(projectile.x, projectile.y)
            sound_board.play("impact")
            self._provoke(hit)
            if hit.ship.take_damage(projectile.damage):
                self._destroy_ship(hit)
            return True
        elif projectile.owner is not None:
            # AI-fired: only the player is a target.
            if not self.in_flight or not self.player.ship:
                return False
            r = self.player.ship.size + projectile.size
            if math.hypot(projectile.x - self.player.x, projectile.y - self.player.y) > r:
                return False
            self._spawn_impact_explosion(projectile.x, projectile.y)
            sound_board.play("impact")
            # Death is handled after _update_projectiles returns (see
            # update_physics) - _on_player_destroyed reassigns
            # self.projectiles, which this method's caller would then
            # clobber with its own alive-list if done inline.
            self.player.ship.take_damage(projectile.damage)
            return True
        return False

    def _destroy_ship(self, character):
        """Blow up a defeated AI ship: a cluster of explosions, the impact
        sound, and removal from its system's roster. Clears any escort /
        combat state so nothing keeps referencing it."""
        for _ in range(3):
            self.explosions.append(Explosion(
                character.x + random.uniform(-12, 12),
                character.y + random.uniform(-12, 12)))
        sound_board.play("impact")
        self._show_toast(f"{character.person.name or 'Hostile'} destroyed", (255, 180, 120))
        character.escorting = False
        character.in_combat = False
        character.firing = False
        for state in self.systems.values():
            if character in state.ai_ships:
                state.ai_ships.remove(character)
                break
        # current_target (an index into _filtered_targets) is re-synced by
        # _validate_target() next frame, which already handles a targeted
        # ship disappearing.

    def _on_player_destroyed(self):
        """The player's hull hit zero. Blow up in place, then recover to
        this system's station: full repair, zero velocity, cargo lost."""
        for _ in range(4):
            self.explosions.append(Explosion(
                self.player.x + random.uniform(-14, 14),
                self.player.y + random.uniform(-14, 14)))
        sound_board.play("impact")
        possessions = self.player.person.possessions
        lost = possessions.cargo_quantity_total()
        possessions.cargo = {}
        self.projectiles = [p for p in self.projectiles if p.owner == "player"]
        self.player.ship.autopilot.disengage()
        self.jump_state = None
        self.park_at(self.station)
        self.player.ship.health = self.player.ship.max_health
        station_name = getattr(self.station, "name", "the station")
        extra = f" Cargo lost ({lost})." if lost else ""
        self._post_message("Rescue Service", f"Your ship was destroyed. Hull recovered and repaired at {station_name}.{extra}")
