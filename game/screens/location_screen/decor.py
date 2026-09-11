"""LocationScreen: decor — mixed into the class in screen.py."""
from game.screens.location_screen._defs import *  # noqa: F401,F403


class _DecorMixin:

    def _draw_decorations(self, surface, layer):
        """Draw every decoration on `layer` ("wall" or "floor"). Filled when
        width == 0, stroked otherwise; a "line" shape is always stroked."""
        scale = get_scale()
        for deco in self.decorations:
            if deco["layer"] != layer:
                continue
            screen_pts = [to_screen(px, py) for px, py in deco["points"]]
            width = max(1, int(deco["width"] * scale)) if deco["width"] else 0
            if deco["shape"] == "line" or width:
                if len(screen_pts) >= 2:
                    pygame.draw.lines(surface, deco["color"], deco["shape"] != "line", screen_pts, max(1, int((deco["width"] or 1) * scale)))
            elif len(screen_pts) >= 3:
                aa.polygon(surface, deco["color"], screen_pts)

    def _build_culture_decorations(self, culture):
        """Expand this culture's optional "interior_decoration" generator
        against every room polygon into concrete decoration dicts (see
        normalize_decoration). Keeps a Vherathi station's rooms edged with
        light-veins and a Drossholt one's with riveted seams without every
        interior having to author them by hand. Unknown generator -> no-op."""
        spec = culture.get("interior_decoration")
        if not spec:
            return []
        generator = spec.get("generator")
        out = []
        if generator == "edge_veins":
            inset, color, width = spec.get("inset", 8), spec.get("color", [120, 255, 200]), spec.get("width", 2)
            for room in self.rooms:
                ring = _inset_polygon(room["polygon"], inset)
                if len(ring) >= 3:
                    out.append(normalize_decoration({"shape": "line", "layer": "floor", "points": ring + ring[:1], "color": color, "width": width}))
        elif generator == "seam_rivets":
            spacing, color, width = spec.get("spacing", 46), spec.get("color", [210, 180, 140]), spec.get("width", 3)
            tick = spec.get("length", 10)
            for room in self.rooms:
                for segment in _edge_ticks(room["polygon"], spacing, tick):
                    out.append(normalize_decoration({"shape": "line", "layer": "floor", "points": segment, "color": color, "width": width}))
        return out

    def _build_floor_pattern(self):
        """Expand the interior's optional "floor_pattern" spec into a cached
        list of (world-space polygon, rgb) tiles that fill every room. Spec is
        either an inline dict or a string naming a
        `graphics/floor_patterns/<name>.json` asset (resolved through the
        story's modules - see game/graphics/story_assets.py):
          {"pattern": "hex"|"square"|"triangle"|"rhombus",  # default "hex"
           "tile": <world units, default ~2x player height>,
           "gap": <shrink each tile toward its centre, default 2>,
           "colors": [[r,g,b], ...]}   # optional; else 3 shades off the culture
        Tiles cycle through the shade list by lattice parity, so the floor
        reads as laid panels in the culture's own colours."""
        spec = self.config.get("floor_pattern")
        if isinstance(spec, str):
            spec = get_floor_pattern(self.story, spec)
        if not spec or not self.rooms:
            return []
        kind = spec.get("pattern", "hex")
        size = float(spec.get("tile", constants.PLAYER_H * 2.0))
        gap = float(spec.get("gap", 2.0))
        if spec.get("colors"):
            shades = [_clamp_rgb(c) for c in spec["colors"]]
        else:
            base = self.floor_color or tuple(self.bg_color)
            accent = self.wall_trim_color or _scale_rgb(base, 1.3)
            shades = [tuple(base), _mix_rgb(base, accent, 0.45), _scale_rgb(base, 0.8)]
        tiles = []
        for room in self.rooms:
            for cell in _tessellate(room["polygon"], kind, size, gap):
                pts = cell["points"]
                if len(pts) >= 3:
                    wp = [(float(x), float(y)) for x, y in pts]
                    xs = [p[0] for p in wp]
                    ys = [p[1] for p in wp]
                    tiles.append((wp, shades[cell["shade"] % len(shades)],
                                  (min(xs), min(ys), max(xs), max(ys))))
        return tiles
