"""LocationScreen: movement — mixed into the class in screen.py."""
from game.screens.location_screen._defs import *  # noqa: F401,F403


class _MovementMixin:

    def _handle_movement(self, keys, can_move_func=None):
        """Turn the held direction keys into one call to the shared on-foot
        movement primitive (Person.step_toward), so the player walks with the
        same walls/corners/diagonal handling as wandering NPCs and dock
        pilots. step_toward normalizes the step, so a diagonal is no longer
        1.41x faster than a cardinal, and it wall-slides instead of stopping
        dead against an angled wall."""
        dir_x = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dir_y = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if not dir_x and not dir_y:
            return
        can_move = can_move_func or self.can_move_to
        # Aim one full step away in the input direction; step_toward caps the
        # move at that distance and normalizes, so holding two keys isn't faster.
        moved = self.player.step_toward(
            self.player.x + dir_x * self.speed,
            self.player.y + dir_y * self.speed,
            self.speed,
            can_move,
        )
        if moved:
            # Generic gameplay-event flag (see PlayerController's "used_turn") -
            # lets a tutorial stage use "walked_interior" as its complete_flag.
            self.player.possessions.flags["walked_interior"] = True

    def can_move_to(self, x, y):
        """Whether (x, y) is inside this location's walkable area - the
        default bounds check _handle_movement uses for the player, exposed
        so anyone else moving a body around this location (e.g. DockRoutine
        walking a visiting pilot to an NPC, and plan_path's nav grid) can
        respect the same walls instead of clipping straight through them."""
        if any(fx <= x <= fx + fw and fy <= y <= fy + fh for fx, fy, fw, fh in self.building_footprints):
            return False
        if self.rooms:
            # Union of the room polygons - overlapping polygons read as one
            # connected space, and point_in_polygon counts a point on any
            # edge as inside so a step landing exactly on the seam between
            # two rooms is never invalid in both at once. The bbox test is a
            # cheap reject before the per-vertex ray cast (the nav grid runs
            # this thousands of times when it builds).
            for room in self.rooms:
                bx0, by0, bx1, by1 = room["bounds"]
                if bx0 <= x <= bx1 and by0 <= y <= by1 and point_in_polygon(x, y, room["polygon"]):
                    return True
            return False
        return 0 < x < self.world_width and 0 < y < self.world_height

    def plan_path(self, start, goal):
        """Waypoints (ending at `goal`) to walk from `start` to `goal`
        through this location's walkable area, routing around walls,
        concave notches, and building footprints via a grid A* (see
        IndoorPathfinder). Used by DockRoutine to move a visiting pilot;
        callers keep wall-sliding each leg as a safety net for the direct
        [goal] fallback this returns when no route exists.

        The nav grid is built once (the walkable area never changes during
        play) and cached - `can_move_to` is the walkability oracle, so
        rooms, overlaps, and footprints all come along for free."""
        if not self.rooms and not self.building_footprints:
            return [goal]  # nothing to route around - a straight line is always fine
        if self._nav_grid is None:
            with perf.span("sim.nav_build"):
                if self.rooms:
                    xs = [p[0] for room in self.rooms for p in room["polygon"]]
                    ys = [p[1] for room in self.rooms for p in room["polygon"]]
                    bounds = (min(xs), min(ys), max(xs), max(ys))
                else:
                    bounds = (0, 0, self.world_width, self.world_height)
                self._nav_grid = NavGrid(self.can_move_to, bounds, NAV_CELL)
        return IndoorPathfinder.find_path(self._nav_grid, start, goal)

    def _clamp_zoom(self, zoom):
        """Keep a zoom level within this interior's allowed range."""
        return max(self.camera_zoom_min, min(self.camera_zoom_max, zoom))

    def update_camera(self):
        """Update global camera to follow player, framed on their vertical
        center rather than their feet (self.player.y is the ground position
        - see person.py; y is negative going up, so half PLAYER_H is
        subtracted to lift the frame to mid-figure)."""
        set_camera_offset(self.player.x - GAME_WIDTH // 2,
                           self.player.y - constants.PLAYER_H / 2 - GAME_HEIGHT // 2)
        # Interiors are always north-up - clear any view rotation the Space
        # View (Q/E) left on the shared camera. The zoom range is the
        # interior's own, separate from the Space View's.
        set_camera_angle(0)
        set_camera_zoom_limits(self.camera_zoom_min, self.camera_zoom_max)
        set_camera_zoom(self.camera_zoom)
