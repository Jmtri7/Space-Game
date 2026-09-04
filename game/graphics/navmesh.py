"""Interior navmesh: rasterise a floor plan minus obstacle footprints into a
walkable grid, pull out the traffic lanes (corridor centre-lines), and flag any
decoration whose hitbox sits on a lane without saying so on purpose.

Dependency-free (no pygame). The game's `indoor_pathfinder.NavGrid` builds the
same walkable raster for A*; this module adds the lane skeleton and the
build-time placement check the pipeline calls for.
"""
import math


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def _bounds(polys):
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


class NavRaster:
    """A walkable grid over an interior. `walkable[r][c]` is True where a cell
    centre lies in some room and in no obstacle footprint."""

    def __init__(self, rooms, portals, obstacles, cell):
        self.cell = cell
        mnx, mny, mxx, mxy = _bounds(rooms + portals)
        self.ox, self.oy = mnx - cell, mny - cell
        self.cols = int((mxx - mnx) / cell) + 3
        self.rows = int((mxy - mny) / cell) + 3
        floor = rooms + portals
        self.walkable = [[self._free(*self.centre(c, r), floor, obstacles)
                          for c in range(self.cols)] for r in range(self.rows)]

    def centre(self, c, r):
        return self.ox + (c + 0.5) * self.cell, self.oy + (r + 0.5) * self.cell

    def cell_at(self, x, y):
        return int((x - self.ox) / self.cell), int((y - self.oy) / self.cell)

    @staticmethod
    def _free(x, y, floor, obstacles):
        if not any(point_in_poly(x, y, f) for f in floor):
            return False
        return not any(point_in_poly(x, y, o) for o in obstacles)

    def distance_field(self):
        """Chamfer distance (in cells) from each walkable cell to the nearest
        blocked cell or the grid edge."""
        INF = 1e9
        d = [[0.0 if not self.walkable[r][c] else INF
              for c in range(self.cols)] for r in range(self.rows)]
        for r in range(self.rows):
            for c in range(self.cols):
                if d[r][c] == 0.0:
                    continue
                for dr, dc, w in ((-1, 0, 1), (0, -1, 1), (-1, -1, 1.414), (-1, 1, 1.414)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        d[r][c] = min(d[r][c], d[nr][nc] + w)
        for r in range(self.rows - 1, -1, -1):
            for c in range(self.cols - 1, -1, -1):
                if d[r][c] == 0.0:
                    continue
                for dr, dc, w in ((1, 0, 1), (0, 1, 1), (1, 1, 1.414), (1, -1, 1.414)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        d[r][c] = min(d[r][c], d[nr][nc] + w)
        return d

    def lanes(self, min_clear=1.5):
        """Cells on a corridor centre-line: walkable, at least `min_clear`
        cells from any wall, and a local ridge of the distance field (no
        8-neighbour is more than ~0.5 cell further from a wall)."""
        d = self.distance_field()
        out = set()
        for r in range(1, self.rows - 1):
            for c in range(1, self.cols - 1):
                if d[r][c] < min_clear:
                    continue
                if all(d[r][c] >= d[r + dr][c + dc] - 0.55
                       for dr in (-1, 0, 1) for dc in (-1, 0, 1)):
                    out.add((c, r))
        return out

    def lane_points(self, min_clear=1.5):
        return [self.centre(c, r) for c, r in self.lanes(min_clear)]


def check_placements(interior, decorations, collisions, cell=None):
    """Return a list of {decoration, at, on_lane, allowed} for every placement.
    `on_lane` is True if the placed hitbox overlaps a traffic lane; `allowed`
    is its collision file's `blocks_lane`. A blocker with on_lane and not
    allowed is a fault the atlas highlights."""
    rooms = [r["points"] for r in interior.get("rooms", [])]
    portals = [p["points"] for p in interior.get("portals", [])]
    cell = cell or max(2.0, min(_bounds(rooms)[2] - _bounds(rooms)[0],
                                _bounds(rooms)[3] - _bounds(rooms)[1]) / 60)

    def placed_footprint(pl):
        col = collisions.get(pl["decoration"])
        if not col:
            return None
        a = math.radians(pl.get("angle", 0))
        ca, sa = math.cos(a), math.sin(a)
        ox, oy = pl["at"]
        return [[ox + x * ca - y * sa, oy + x * sa + y * ca] for x, y in col["footprint"]]

    # Lanes are the through-routes of the bare floor. A placement "blocks a
    # lane" when its hitbox lands on one of those routes; whether that is a
    # fault is what its collision file's `blocks_lane` decides.
    raster = NavRaster(rooms, portals, [], cell)
    lane_cells = raster.lanes()

    result = []
    for pl in interior.get("placements", []):
        fp = placed_footprint(pl)
        allowed = bool(collisions.get(pl["decoration"], {}).get("blocks_lane"))
        on_lane = bool(fp) and any(point_in_poly(*raster.centre(c, r), fp) for c, r in lane_cells)
        result.append({"decoration": pl["decoration"], "at": pl["at"],
                       "on_lane": on_lane, "allowed": allowed,
                       "fault": on_lane and not allowed})
    return raster, lane_cells, result
