"""LocationScreen: structures — mixed into the class in screen.py."""
from game.screens.location_screen._defs import *  # noqa: F401,F403


class _StructuresMixin:

    def _draw_culture_building(self, surface, structure, building_type_id, scale):
        """Draw a building whose hull/window colors come from its type's culture -
        fully config-driven metal (hull) + glass (windows) material palette.

        `structure` supplies only position ("x"/"y"); shape, size, and window
        layout all come from the building_type. Anchor point varies by shape:
        "rect" uses top-left (matching the generic rect structures above),
        "circle" uses center, "polygon" is whatever the type's local_points
        were authored relative to (typically ground level).
        """
        building_type = get_building_type(self.story, building_type_id)
        metal_color = tuple(building_type.get("color", (150, 150, 150)))
        glass_color = tuple(building_type.get("window_color", (255, 255, 0)))
        # A near-black outline on every hull shape so furniture and buildings
        # read as distinct objects instead of melting into the floor / each
        # other (they're all drawn in the same culture metal_color). Scales
        # with zoom but never vanishes.
        outline_color = (12, 10, 16)
        outline_w = max(1, int(round(2 * scale)))
        anchor_x, anchor_y = structure["x"], structure["y"]
        shape = building_type.get("shape", "rect")

        # A "parts" list (multi-polygon detail - see the design atlases and
        # WorldObject.draw_parts) replaces the single base shape when present;
        # windows still layer on top. The top-level shape/dims stay only for
        # the footprint/depth math (see _building_footprint/_structure_depth).
        parts = building_type.get("parts")
        if parts:
            draw_parts(surface, parts, anchor_x, anchor_y, 0, 1, metal_color, glass_color)
        elif shape == "circle":
            radius = building_type.get("radius", 50)
            cx, cy = to_screen(anchor_x, anchor_y)
            r = max(1, int(radius * scale))
            aa.circle(surface, metal_color, (cx, cy), r)
            aa.circle(surface, outline_color, (cx, cy), r, outline_w)
        elif shape == "polygon":
            local_points = building_type.get("local_points", [])
            screen_points = [to_screen(anchor_x + lx, anchor_y + ly) for lx, ly in local_points]
            if len(screen_points) >= 3:
                aa.polygon(surface, metal_color, screen_points)
                aa.polygon(surface, outline_color, screen_points, outline_w)
        else:  # rect
            width = building_type.get("width", 100)
            height = building_type.get("height", 100)
            x1, y1 = to_screen(anchor_x, anchor_y)
            x2, y2 = to_screen(anchor_x + width, anchor_y + height)
            rect = (x1, y1, x2 - x1, y2 - y1)
            pygame.draw.rect(surface, metal_color, rect)
            pygame.draw.rect(surface, outline_color, rect, outline_w)

        # A "parts" silhouette is complete (its own lit viewports are already
        # in the list) - drawing the legacy "windows" dots on top of it just
        # shows the old shape bleeding past the new one, exactly as the ship /
        # station paths avoid (see ship.py / landing_site.py _draw_station).
        window_shape = building_type.get("window_shape", "rect")
        window_size = building_type.get("window_size", 12)
        half = max(1, int(window_size * scale / 2))
        for wx, wy in ([] if parts else building_type.get("windows", [])):
            px, py = to_screen(anchor_x + wx, anchor_y + wy)
            if window_shape == "circle":
                aa.circle(surface, glass_color, (px, py), half)
            else:
                pygame.draw.rect(surface, glass_color, (px - half, py - half, half * 2, half * 2))

    def _building_footprint(self, structure):
        """World-space collision box (fx, fy, fw, fh) for one structure, or
        None if it isn't a building (decorative circle/rect/polygon terrain,
        e.g. moon rocks/craters, has no "building_type") or its building_type
        configures no "footprint".

        Deliberately just the base, not the full drawn silhouette: a tall
        spire's upper floors are pure occluding art (a 2D building is drawn
        "extruded" upward from ground level via negative local y - see
        _draw_culture_building), so making the whole visual height solid
        would block a player from ever standing near the far side even
        though the painter's-algorithm sort in draw() already draws them
        behind it correctly. Sized from building_type's own "footprint"
        (roughly square/city-block, not a sliver spanning the building's
        full height) rather than derived from width/height, since e.g.
        drossholt_tower is only 80 wide but 220 tall - a footprint that thin
        would make its base nearly impossible to walk around.

        The box is anchored so its **back edge** sits `depth` behind the
        drawn silhouette's own bottom edge and its front edge sits at that
        bottom edge (plus FOOTPRINT_FRONT_LIP) - not centred on the anchor
        point, which for several `parts`/`local_points` furniture pieces
        (the resin bench, lounge pod, concierge desk) is well above where
        the art actually meets the floor, leaving a slab of collision
        hanging in the open floor in front of the object. The silhouette's
        bottom/centre come from `local_points` (polygon), `width`/`height`
        (rect, authored top-left) or `radius` (circle, authored centred).
        """
        building_type_id = structure.get("building_type")
        if not building_type_id:
            return None
        building_type = get_building_type(self.story, building_type_id)
        footprint = building_type.get("footprint")
        if not footprint:
            return None
        fw, fd = footprint.get("width", 100), footprint.get("depth", 100)
        sx, sy = structure["x"], structure["y"]
        min_x, _, max_x, max_y = _silhouette_local_bounds(building_type)
        base_cx = sx + (min_x + max_x) / 2
        base_y = sy + max_y
        # An elevation billboard's base line IS its floor contact - the box
        # ends there, no front lip (there's no drawn front face to clip into).
        lip = 0 if building_type.get("view") == "elevation" else self.FOOTPRINT_FRONT_LIP
        return (base_cx - fw / 2, base_y - fd, fw, fd + lip)

    def _structure_depth(self, structure):
        """Y-sort key for a structure: the ground-level depth a walking
        person's own y (feet position) should be compared against in
        draw()'s back-to-front pass, so tall features occlude correctly
        against whoever's standing in front of or behind them."""
        building_type_id = structure.get("building_type")
        if building_type_id:
            building_type = get_building_type(self.story, building_type_id)
            if building_type.get("parts"):
                # sort by where the real geometry meets the floor (max local y):
                # ~0 for an elevation billboard, ~+depth for a top-down piece.
                return structure["y"] + _silhouette_local_bounds(building_type)[3]
            if building_type.get("shape", "rect") == "rect":
                return structure["y"] + building_type.get("height", 100)
            return structure["y"]  # circle: center; polygon: ground-level anchor

        struct_type = structure.get("type", "rect")
        if struct_type == "rect":
            return structure["y"] + structure["height"]
        if struct_type == "polygon":
            return max(p["y"] for p in structure["points"])
        return structure["y"]  # circle

    def _structure_world_bounds(self, structure):
        """(min_x, min_y, max_x, max_y) of a structure's drawn silhouette in
        world space - for the draw() viewport cull. Tall elevation buildings
        get their real (negative-y) extent so a spire whose base is just off
        the bottom of the screen still counts as visible."""
        x, y = structure["x"], structure["y"]
        bt_id = structure.get("building_type")
        if bt_id:
            lx0, ly0, lx1, ly1 = _silhouette_local_bounds_for(self.story, bt_id)
            return (x + lx0, y + ly0, x + lx1, y + ly1)
        t = structure.get("type", "rect")
        if t == "rect":
            return (x, y, x + structure.get("width", 100), y + structure.get("height", 100))
        if t == "circle":
            r = structure.get("radius", 50)
            return (x - r, y - r, x + r, y + r)
        if t == "polygon" and structure.get("points"):
            xs = [p["x"] for p in structure["points"]]
            ys = [p["y"] for p in structure["points"]]
            return (min(xs), min(ys), max(xs), max(ys))
        return (x - 60, y - 60, x + 60, y + 60)

    def _make_structure_drawer(self, structure, scale):
        """Bind one structure's draw call so draw() can sort it alongside
        NPCs/visitors/the player and invoke it in back-to-front order."""
        building_type_id = structure.get("building_type")
        if building_type_id:
            return lambda surface: self._draw_culture_building(surface, structure, building_type_id, scale)

        struct_type = structure.get("type", "rect")
        color = tuple(structure.get("color", [150, 150, 150]))

        if struct_type == "rect":
            x, y, w, h = structure["x"], structure["y"], structure["width"], structure["height"]

            def draw_rect(surface):
                x1, y1 = to_screen(x, y)
                x2, y2 = to_screen(x + w, y + h)
                pygame.draw.rect(surface, color, (x1, y1, x2 - x1, y2 - y1))
            return draw_rect

        if struct_type == "circle":
            x, y, r = structure["x"], structure["y"], structure.get("radius", 50)

            def draw_circle(surface):
                cx, cy = to_screen(x, y)
                aa.circle(surface, color, (cx, cy), max(1, int(r * scale)))
            return draw_circle

        if struct_type == "polygon":
            points = [(p["x"], p["y"]) for p in structure["points"]]

            def draw_polygon(surface):
                screen_points = [to_screen(px, py) for px, py in points]
                aa.polygon(surface, color, screen_points)
            return draw_polygon

        return lambda surface: None
