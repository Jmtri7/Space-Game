"""Waypoint pathfinding through a LocationScreen's rooms and around its
building footprints.

DockRoutine used to walk a visiting pilot straight at their destination
(wall-sliding along the way - see LocationScreen.can_move_to), which works
fine within one room but can strand a pilot permanently against a wall when
the destination is in a different room that isn't reachable by a straight
line at all (e.g. two rooms joined by an L-shaped corridor) - every
candidate step in _step_toward's wall-slide fails at once, so the pilot
never moves again. This treats a location's rooms as a graph - two rooms
are adjacent if their rects overlap or share an edge - and routes through
the shared boundary of each room along the way, so every leg of the
resulting path stays inside one (rectangular, therefore convex) room and a
straight line can always complete it.

A city/wilderness location has no rooms at all (just one open area) but
does have building footprints (LocationScreen.building_footprints) sitting
in the middle of it - the same stuck failure mode shows up walking straight
at a building with the destination directly behind it (wall-sliding has no
sideways component to try when the direct line has zero x or y offset).
find_path's optional `obstacles` routes each room-to-room leg around any
footprint it crosses, via a visibility graph over the footprints' (slightly
inflated) corners - the standard shortest-path construction for routing
around convex rectangular obstacles.
"""
import math
import heapq
from collections import deque

# How far outside a building's true footprint a corner waypoint sits, and
# how far a "does this leg cross this rect" check inflates the rect by -
# keeps a path that grazes a corner from being considered blocked by the
# very obstacle it's routing around.
OBSTACLE_MARGIN = 6


class IndoorPathfinder:
    """Stateless: builds a list of waypoints from one point to another
    through a set of rooms (see LocationScreen.rooms), detouring around any
    obstacles (see LocationScreen.building_footprints) along the way."""

    @staticmethod
    def _room_at(rooms, x, y):
        for index, room in enumerate(rooms):
            rx, ry, rw, rh = room["rect"]
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return index
        return None

    @staticmethod
    def _adjacent(rect_a, rect_b):
        """Whether two room rects overlap or share an edge - a zero-width
        overlap on one axis still counts as long as the other axis actually
        overlaps (a shared wall segment, not just a shared corner point)."""
        ax, ay, aw, ah = rect_a
        bx, by, bw, bh = rect_b
        overlap_x = min(ax + aw, bx + bw) - max(ax, bx)
        overlap_y = min(ay + ah, by + bh) - max(ay, by)
        return overlap_x >= 0 and overlap_y >= 0 and (overlap_x > 0 or overlap_y > 0)

    @staticmethod
    def _overlap_point(rect_a, rect_b):
        """A point inside the shared boundary of two adjacent rects - the
        midpoint of the overlapping range on each axis, which always lands
        inside both rects since it's the intersection of their ranges."""
        ax, ay, aw, ah = rect_a
        bx, by, bw, bh = rect_b
        x0, x1 = max(ax, bx), min(ax + aw, bx + bw)
        y0, y1 = max(ay, by), min(ay + ah, by + bh)
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    @classmethod
    def find_path(cls, rooms, start, goal, obstacles=None):
        """Waypoints (ending with `goal` itself) to walk from `start` to
        `goal` through `rooms`, then detoured around any `obstacles` (see
        LocationScreen.building_footprints) blocking a leg. Falls back to
        the direct [goal] path - exactly the old straight-line behavior -
        when either point isn't in any room, they're already in the same
        room, or no route exists between their rooms; callers should keep
        wall-sliding on every leg regardless, as a safety net for that
        fallback case."""
        room_waypoints = cls._room_path(rooms, start, goal)
        if not obstacles:
            return room_waypoints

        waypoints = []
        current = start
        for point in room_waypoints:
            waypoints.extend(cls._route_around_obstacles(current, point, obstacles))
            current = point
        return waypoints

    @classmethod
    def _room_path(cls, rooms, start, goal):
        start_room = cls._room_at(rooms, *start)
        goal_room = cls._room_at(rooms, *goal)
        if start_room is None or goal_room is None or start_room == goal_room:
            return [goal]

        came_from = {start_room: None}
        queue = deque([start_room])
        while queue:
            current = queue.popleft()
            if current == goal_room:
                break
            for index, room in enumerate(rooms):
                if index not in came_from and cls._adjacent(rooms[current]["rect"], room["rect"]):
                    came_from[index] = current
                    queue.append(index)

        if goal_room not in came_from:
            return [goal]

        room_path = [goal_room]
        while came_from[room_path[-1]] is not None:
            room_path.append(came_from[room_path[-1]])
        room_path.reverse()

        waypoints = [cls._overlap_point(rooms[a]["rect"], rooms[b]["rect"]) for a, b in zip(room_path, room_path[1:])]
        waypoints.append(goal)
        return waypoints

    @staticmethod
    def _segment_crosses_rect(p1, p2, rect, margin=OBSTACLE_MARGIN):
        """Whether the segment p1-p2 passes through the interior of `rect`
        inflated by `margin` on every side - Liang-Barsky line clipping.
        A segment that only touches the inflated rect's boundary (e.g. it
        ends exactly on one of its corners) is NOT considered crossing, so
        an obstacle's own corner waypoints never block the legs that lead
        to/from them."""
        rx, ry, rw, rh = rect
        x0, y0, x1, y1 = rx - margin, ry - margin, rx + rw + margin, ry + rh + margin
        (px, py), (qx, qy) = p1, p2
        dx, dy = qx - px, qy - py
        t0, t1 = 0.0, 1.0
        for p, q in ((-dx, px - x0), (dx, x1 - px), (-dy, py - y0), (dy, y1 - py)):
            if p == 0:
                # The segment doesn't move along this axis at all, so q==0
                # means it runs exactly along this bound (e.g. two corners
                # of the same obstacle, along one of its own edges) rather
                # than through the interior - reject that too, not just
                # q<0, or every edge between an obstacle's own corners
                # would look "blocked" by the very obstacle they route
                # around.
                if q <= 0:
                    return False
            else:
                r = q / p
                if p < 0:
                    if r > t1:
                        return False
                    t0 = max(t0, r)
                else:
                    if r < t0:
                        return False
                    t1 = min(t1, r)
        return t0 < t1 - 1e-9

    @classmethod
    def _route_around_obstacles(cls, start, goal, obstacles):
        """Shortest path from `start` to `goal` that doesn't cross any
        `obstacles`, via a visibility graph over each obstacle's (inflated)
        corners - the standard construction for routing around convex
        rectangular obstacles. Skips the graph entirely (just [goal]) when
        the direct line is already clear, which is the common case."""
        if not any(cls._segment_crosses_rect(start, goal, rect) for rect in obstacles):
            return [goal]

        nodes = [start, goal]
        for rx, ry, rw, rh in obstacles:
            x0, y0 = rx - OBSTACLE_MARGIN, ry - OBSTACLE_MARGIN
            x1, y1 = rx + rw + OBSTACLE_MARGIN, ry + rh + OBSTACLE_MARGIN
            nodes.extend([(x0, y0), (x1, y0), (x0, y1), (x1, y1)])

        def visible(i, j):
            return not any(cls._segment_crosses_rect(nodes[i], nodes[j], rect) for rect in obstacles)

        goal_index = 1
        dist = {0: 0.0}
        prev = {}
        visited = set()
        heap = [(0.0, 0)]
        while heap:
            d, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)
            if u == goal_index:
                break
            for v in range(len(nodes)):
                if v == u or v in visited or not visible(u, v):
                    continue
                nd = d + math.hypot(nodes[v][0] - nodes[u][0], nodes[v][1] - nodes[u][1])
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))

        if goal_index not in prev:
            return [goal]  # no clear route through the corners either - direct fallback, same as the room case

        path_indices = [goal_index]
        while path_indices[-1] != 0:
            path_indices.append(prev[path_indices[-1]])
        path_indices.reverse()
        return [nodes[i] for i in path_indices[1:]]
