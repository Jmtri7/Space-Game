"""Grid A* pathfinding across a LocationScreen's walkable area.

DockRoutine walks a visiting pilot to an NPC on the far side of an interior.
Walking straight at the target and wall-sliding (see DockRoutine._step_toward
/ LocationScreen.can_move_to) works within an open room but strands the pilot
permanently against a wall whenever the direct line leaves the walkable area
- a different room reachable only around an L-bend, a building sitting
between here and there, or (now that station interiors are one big
connected area of arbitrary polygons) a concave notch in the floor plan.

This treats the whole interior as a uniform grid: every cell centre is
walkable or not according to a caller-supplied predicate (LocationScreen.
can_move_to, which already folds in room polygons and building footprints),
A* finds a cell path, and a string-pull pass collapses it back to the few
turning points that matter. One predicate, one grid - concave rooms,
overlapping rooms, and footprints are all just "cell not walkable" with no
special cases.

The old version built a graph of axis-aligned room rects and routed through
their shared edges; that could not survive non-rectangular or concave rooms,
so it was replaced wholesale. Callers still get the same contract: a list of
waypoints ending at `goal`, falling back to the direct `[goal]` when no
route exists (DockRoutine keeps wall-sliding every leg as the safety net for
that fallback).

`LocationScreen.plan_path` builds one `NavGrid` per interior (lazily, then
cached - the walkable area never changes during play) and calls
`find_path` for each replan.
"""
import heapq
import math

# Diagonal moves cost this much more than orthogonal ones (sqrt 2), so A*
# prefers a straight run over a staircase of the same cell count.
DIAG_COST = math.sqrt(2)


class NavGrid:
    """A frozen walkability raster of one interior: which cell centres are
    walkable, plus the geometry to map between world space and cells."""

    def __init__(self, walkable_fn, bounds, cell):
        self.min_x, self.min_y, max_x, max_y = bounds
        self.cell = cell
        self.cols = max(1, int((max_x - self.min_x) / cell))
        self.rows = max(1, int((max_y - self.min_y) / cell))
        self.walkable_fn = walkable_fn
        self.walkable = [
            [walkable_fn(*self.cell_center(c, r)) for c in range(self.cols)]
            for r in range(self.rows)
        ]

    def cell_center(self, c, r):
        return (self.min_x + (c + 0.5) * self.cell, self.min_y + (r + 0.5) * self.cell)

    def _to_cell(self, point):
        c = int((point[0] - self.min_x) / self.cell)
        r = int((point[1] - self.min_y) / self.cell)
        return (min(max(c, 0), self.cols - 1), min(max(r, 0), self.rows - 1))

    def _snap(self, c0, r0):
        """Nearest walkable (col, row) to a given one, spiralling outward -
        pulls a start/goal that landed on a wall cell onto the navigable
        area before A* runs."""
        if self.walkable[r0][c0]:
            return (c0, r0)
        for radius in range(1, max(self.cols, self.rows)):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if max(abs(dr), abs(dc)) != radius:
                        continue
                    c, r = c0 + dc, r0 + dr
                    if 0 <= c < self.cols and 0 <= r < self.rows and self.walkable[r][c]:
                        return (c, r)
        return None


class IndoorPathfinder:
    """Stateless grid planner over a `NavGrid`."""

    @classmethod
    def find_path(cls, grid, start, goal):
        """Waypoints (world-space, ending at `goal`) from `start` to `goal`
        across `grid`. Returns `[goal]` unchanged when the goal isn't in the
        walkable area at all, when either endpoint has no reachable walkable
        cell, or when A* finds no path between them - the caller wall-slides
        that direct leg as its safety net."""
        if not grid.walkable_fn(*goal):
            return [goal]
        start_cell = grid._snap(*grid._to_cell(start))
        goal_cell = grid._snap(*grid._to_cell(goal))
        if start_cell is None or goal_cell is None:
            return [goal]

        cell_path = cls._astar(grid, start_cell, goal_cell)
        if cell_path is None:
            return [goal]

        points = [start] + [grid.cell_center(c, r) for c, r in cell_path[1:-1]] + [goal]
        return cls._string_pull(points, grid.walkable_fn, grid.cell)

    @staticmethod
    def _astar(grid, start, goal):
        walkable, cols, rows = grid.walkable, grid.cols, grid.rows

        def neighbors(c, r):
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nc, nr = c + dc, r + dr
                if not (0 <= nc < cols and 0 <= nr < rows) or not walkable[nr][nc]:
                    continue
                if dc and dr and not (walkable[r][nc] and walkable[nr][c]):
                    continue  # don't cut a diagonal through a wall corner
                yield (nc, nr), (DIAG_COST if dc and dr else 1.0)

        def h(node):
            return math.hypot(node[0] - goal[0], node[1] - goal[1])

        open_heap = [(h(start), 0.0, start)]
        came_from = {start: None}
        best = {start: 0.0}
        while open_heap:
            _, g, node = heapq.heappop(open_heap)
            if node == goal:
                path = [node]
                while came_from[path[-1]] is not None:
                    path.append(came_from[path[-1]])
                path.reverse()
                return path
            if g > best.get(node, float("inf")):
                continue
            for nxt, step in neighbors(*node):
                ng = g + step
                if ng < best.get(nxt, float("inf")):
                    best[nxt] = ng
                    came_from[nxt] = node
                    heapq.heappush(open_heap, (ng + h(nxt), ng, nxt))
        return None

    @classmethod
    def _string_pull(cls, points, walkable_fn, cell):
        """Drop every waypoint that can be skipped because the segment past
        it is still fully walkable - turns a cell-by-cell staircase back
        into the handful of corners a person would actually walk. `points`
        starts with the real `start`; the returned list excludes it."""
        if len(points) <= 2:
            return points[1:]
        pulled = [points[0]]
        anchor = 0
        for i in range(1, len(points) - 1):
            if not cls._segment_walkable(points[anchor], points[i + 1], walkable_fn, cell):
                pulled.append(points[i])
                anchor = i
        pulled.append(points[-1])
        return pulled[1:]

    @staticmethod
    def _segment_walkable(a, b, walkable_fn, cell):
        """Whether every sample along a-b (spaced ~cell/3) is walkable. The
        spacing is deliberately finer than the grid: a diagonal leg can
        graze the corner of a footprint or wall between two coarser samples,
        and the string-pull that calls this would then hand a walker a
        waypoint it can't actually reach in a straight line."""
        dist = math.hypot(b[0] - a[0], b[1] - a[1])
        steps = max(1, int(dist / (cell / 3)))
        for i in range(steps + 1):
            t = i / steps
            if not walkable_fn(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t):
                return False
        return True
