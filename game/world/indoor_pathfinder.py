"""Waypoint pathfinding through a LocationScreen's rooms.

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
"""
from collections import deque


class IndoorPathfinder:
    """Stateless: builds a list of waypoints from one point to another
    through a set of rooms (see LocationScreen.rooms)."""

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
    def find_path(cls, rooms, start, goal):
        """Waypoints (ending with `goal` itself) to walk from `start` to
        `goal` through `rooms`. Falls back to the direct [goal] path -
        exactly the old straight-line behavior - when either point isn't in
        any room, they're already in the same room, or no route exists
        between their rooms; callers should keep wall-sliding on every leg
        regardless, as a safety net for that fallback case."""
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
