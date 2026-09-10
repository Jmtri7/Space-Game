"""SpaceScreen: jump — mixed into the class in screen.py."""
from game.screens.space_screen._defs import *  # noqa: F401,F403


class _JumpMixin:

    def _drifted_from_center(self):
        """Whether the player has flown far enough from this system's
        center that jumping back (open the Star Map, select this system,
        J) is both possible and worth calling out - see _draw_hud's
        status-pane hint. Uses the exact same threshold try_jump already
        requires for a self-jump back to this system, so the hint and the
        mechanic it's pointing at agree by construction."""
        cx, cy = SYSTEM_CENTER
        return math.sqrt((self.player.x - cx) ** 2 + (self.player.y - cy) ** 2) >= self.jump_self_min_distance

    def try_jump(self):
        """Validate the current star map selection/distance, then start a jump
        if valid. Called both by the jump key (2) in the space view and by main.py when the
        player presses 2 to leave the Star Map with a destination selected."""
        if not self.selected_system_id:
            return
        systems = get_star_systems(self.story)
        dest_cfg = systems.get(self.selected_system_id, {})
        if not system_unlocked(dest_cfg, self.player.person.possessions.flags):
            self.jump_message = f"No signal from {dest_cfg.get('name', self.selected_system_id)} - the beacon is dark"
            self.jump_message_timer = 90
            return
        cx, cy = SYSTEM_CENTER
        distance_from_center = math.sqrt((self.player.x - cx) ** 2 + (self.player.y - cy) ** 2)
        if self.selected_system_id == self.system_id and distance_from_center < self.jump_self_min_distance:
            self.jump_message = "Too close to jump - move away from center first"
            self.jump_message_timer = 90  # brief "too close to jump" feedback
            return
        self._begin_jump()

    def _begin_jump(self):
        """Point the ship toward the destination system and begin the jump animation."""
        systems = get_star_systems(self.story)
        origin = systems.get(self.system_id)
        destination = systems.get(self.selected_system_id)
        if not origin or not destination:
            return

        if self.selected_system_id == self.system_id:
            # Self-jump ("jump home" to re-centre after drifting) - there's no
            # star-map direction, so aim the ship straight at the system
            # centre from wherever it currently is. It then travels toward
            # centre and arrives on the near side facing inward (see
            # _complete_jump).
            cx, cy = SYSTEM_CENTER
            dx, dy = cx - self.player.x, cy - self.player.y
            if dx == 0 and dy == 0:
                dx = 1
        else:
            origin_pos = origin["star_map_position"]
            dest_pos = destination["star_map_position"]
            dx = dest_pos["x"] - origin_pos["x"]
            dy = dest_pos["y"] - origin_pos["y"]
            if dx == 0 and dy == 0:
                dx = 1  # degenerate guard: two systems at the same map position

        heading = math.degrees(math.atan2(dx, -dy)) % 360

        self.player.autopilot_active = False
        self.player.autopilot_target = None
        self.player.thrust = 0
        self.player.ship.force_thrusters = True  # cleared in _complete_jump
        self.jump_state = {
            "phase": "align",
            "heading": heading,
            "timer": 0,
            "destination": self.selected_system_id,
        }

    def _update_jump(self):
        """Advance the jump animation by one frame: rotate to heading, then blast forward."""
        js = self.jump_state
        ship = self.player.ship

        if js["phase"] == "align":
            target_angle = js["heading"] % 360
            current_angle = ship.angle % 360
            diff = (target_angle - current_angle + 180) % 360 - 180
            step = ship.rotation_speed * 3  # snappier than normal turning, for a punchy feel
            if abs(diff) <= step:
                ship.angle = target_angle
                js["phase"] = "travel"
                js["timer"] = 0
                sound_board.play("jump_engage")  # drive spools up over the travel phase
            else:
                ship.angle = (ship.angle + step * (1 if diff > 0 else -1)) % 360

        elif js["phase"] == "travel":
            rad = math.radians(ship.angle)
            ship.velocity_x = math.sin(rad) * self.jump_speed
            ship.velocity_y = -math.cos(rad) * self.jump_speed
            ship.x += ship.velocity_x
            ship.y += ship.velocity_y
            js["timer"] += 1
            if js["timer"] >= self.jump_travel_frames:
                self._complete_jump()

    def _complete_jump(self):
        """Finish the jump: swap systems (within this story) if the destination differs,
        then arrive on the outskirts."""
        js = self.jump_state
        heading_rad = math.radians(js["heading"])
        destination = js["destination"]

        if destination != self.system_id:
            self._activate_system(destination)

        center_x, center_y = SYSTEM_CENTER
        arrival_x = center_x - math.sin(heading_rad) * self.jump_arrival_distance
        arrival_y = center_y + math.cos(heading_rad) * self.jump_arrival_distance

        ship = self.player.ship
        ship.x, ship.y = arrival_x, arrival_y
        ship.angle = js["heading"] % 360
        # Arrive coasting at the ship's own top speed - no faster (the base
        # physics only caps velocity while thrusting, so an over-max arrival
        # speed would otherwise persist until the player next thrusts).
        arrival_speed = ship.max_velocity
        ship.velocity_x = math.sin(heading_rad) * arrival_speed
        ship.velocity_y = -math.cos(heading_rad) * arrival_speed
        ship.thrust = 0
        ship.force_thrusters = False

        self.jump_state = None
        sound_board.play("jump_boom")  # sonic-boom crack on arrival
        # Reset the jump target to wherever we just arrived (never None) -
        # matches __init__ and keeps "Jump Target" meaningful.
        self.selected_system_id = self.system_id
        arrival_name = get_star_systems(self.story).get(self.system_id, {}).get("name", self.system_id)
        self._show_toast(f"Jump complete - arrived at {arrival_name}", CYAN)
        # Generic gameplay-event flags - see K_f's comment above on why
        # these live on Possessions.flags instead of a SpaceScreen-only
        # field. "completed_jump" fires for any jump (a self-jump home
        # counts); "jumped_to:<system_id>" is the per-destination form, for
        # a mission step like "jump to Kiln".
        self.player.person.possessions.flags["completed_jump"] = True
        self.player.person.possessions.flags[f"jumped_to:{self.system_id}"] = True
