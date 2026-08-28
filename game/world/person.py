"""Base class for NPCs and other characters in the game."""
import pygame
import math
from game.utils import to_screen, to_screen_x, to_screen_y, get_scale
from game.world.possessions import Possessions


class Person:
    """Base class for anyone with a position and a body - the player's own
    walking self (see PlayerCharacter), NPCs, and a ship's pilot all share
    this identity regardless of whether they currently have a ship."""
    def __init__(self, x, y, name="", possessions=None, outfit=None):
        self.x = x
        self.y = y
        self.name = name
        # Every character - player, NPC, or AI pilot - owns their own
        # credits/ships/loans, not just the player. Most NPCs never touch
        # this, but it means "who owns what" is never a player-only concept.
        self.possessions = possessions or Possessions()
        # A resolved graphics.json "outfits" asset (see get_graphics_asset),
        # drawn over the shared body below - helmet_color/suit_color/
        # boot_color/leg_color, any of which may be absent. None/{} means
        # bare body, no outfit. The body shape itself stays shared across
        # everyone for now; an outfit recolors it, adds a helmet, and can
        # bolt on optional accessory pieces - each just another color key
        # (shoulder_color, spike_color, collar_color, chest_plate_color,
        # sash_color, belt_color, badge_color, backpack_color,
        # antenna_color, visor_color; see draw() and _draw_*_accessories).
        # So a new decorated outfit is still just a new graphics.json
        # entry, no drawing code needed.
        self.outfit = outfit or {}

        # Walk-cycle state (see WALK_* constants and _advance_walk). Every
        # Person animates the same way whether the player, a WanderRoutine
        # NPC, or a DockRoutine pilot is driving step_toward.
        self.walk_phase = 0.0
        self.walk_intensity = 0.0
        self._walked_this_frame = False

    # Body proportions, all measured up from the feet (self.x/self.y is the
    # ground position a character is standing at, not their head or
    # shoulders - matches where collision/arrival distance checks treat
    # them as being). The bare body is a face-on foot-to-head stack - two
    # boots, two tapering legs rising to a hip line, a tapering rounded-
    # shoulder torso polygon, and a head circle - shaded from one skin tone
    # as if lit from above (head lightest, boots darkest). An outfit (see
    # self.outfit) recolors the shapes and adds a thick helmet ring around
    # the head, but never changes this shape - see draw(). The legs also
    # carry the walk cycle (WALK_* below, driven by step_toward).
    BOOT_RADIUS_X = 2.6      # boot oval - wider than tall, like the old foot
    BOOT_RADIUS_Y = 1.9
    LEG_HEIGHT = 11        # hip line down to the ankle (boot centre) at rest
    LEG_HALF_WIDTH = 1.7
    LEG_SEPARATION = 2.8   # each leg's centre, out from the body centreline
    HIP_OVERLAP = 1.5       # how far the leg tops tuck up under the torso base
    BODY_HEIGHT = 11         # torso height, shoulders to hip line
    SHOULDER_HALF_WIDTH = 7  # torso half-width at the (rounded) shoulders
    BASE_HALF_WIDTH = 4.5    # torso half-width at the base - covers the leg tops
    SHOULDER_RADIUS = 3.5    # rounding radius of each shoulder corner
    SHOULDER_SEGMENTS = 4    # polygon segments approximating each shoulder's curve
    HEAD_RADIUS = 5.5        # slightly large, so it overlaps the shoulders below
    HEAD_OVERLAP = 0.1       # how far the head sinks between the shoulders
    HELMET_THICKNESS = 2.4   # ring width of a helmet outside the face, when outfitted
    HELMET_FACE_COVER = 1.3  # how far a helmet's inner rim also creeps in over the face
    EYE_RADIUS = 0.8
    EYE_OFFSET_X = 2.2       # each eye's distance from center
    EYE_OFFSET_Y = 0.5       # slightly below head center

    SKIN_COLOR = (225, 180, 145)  # torso tone; head/legs/boots are shaded from this
    EYE_COLOR = (40, 30, 30)

    # Walk cycle. walk_phase advances with the distance actually walked
    # (step_toward -> _advance_walk); walk_intensity ramps in on movement
    # and eases back out in draw() when it stops, so the legs settle to a
    # neutral stance instead of freezing mid-stride. Amplitudes are in
    # game-space units, except WALK_STRIDE_DEG (leg swing about the hip).
    WALK_PACE = 0.7             # radians of walk_phase per game-unit walked
    WALK_LIFT = 2.6           # peak rise of the swinging leg's boot
    WALK_STRIDE_DEG = 6       # peak fore/aft swing of each leg about the hip
    WALK_BOB = 0.8           # body rise as a foot passes under
    WALK_INTENSITY_GAIN = 0.34  # per moving frame, up to 1.0
    WALK_INTENSITY_DECAY = 0.82  # per idle frame, back toward 0

    # Same technique as WorldObject._draw_rotated_polygon uses for ships: a
    # dark silhouette drawn slightly larger, underneath each shape, so the
    # body reads as distinct from similarly-toned ground/terrain instead of
    # blending into it (see docs/BACKLOG.md's helmet-vs-ground item). Same
    # near-black tone as ships' default outline_color for visual consistency.
    OUTLINE_COLOR = (20, 18, 25)
    OUTLINE_WIDTH = 2  # screen pixels

    @staticmethod
    def _shade(color, amount):
        """Nudge a color's channels by amount (+lighter/-darker), clamped."""
        return tuple(max(0, min(255, c + amount)) for c in color)

    def _shoulder_arc(self, cx, cy, start_deg, end_deg, radius):
        """Points tracing one rounded shoulder corner, center (cx, cy),
        sweeping from start_deg to end_deg (0=right, 90=down, 180=left,
        270=up - screen convention, y grows downward)."""
        points = []
        for i in range(self.SHOULDER_SEGMENTS + 1):
            t = start_deg + (end_deg - start_deg) * i / self.SHOULDER_SEGMENTS
            rad = math.radians(t)
            points.append((cx + radius * math.cos(rad), cy + radius * math.sin(rad)))
        return points

    def _torso_points(self, body_top_y, body_bottom_y, margin=0):
        """The symmetric, round-shouldered, tapering torso polygon: left
        shoulder arc, right shoulder arc, then straight down to the (base,
        narrower) bottom corners - which sit hidden behind the leg tops, so
        they don't need rounding too.

        margin (game-space units) grows every dimension outward, for tracing
        an outline silhouette rather than the torso itself - see OUTLINE_COLOR."""
        shoulder_half_width = self.SHOULDER_HALF_WIDTH + margin
        base_half_width = self.BASE_HALF_WIDTH + margin
        shoulder_radius = self.SHOULDER_RADIUS + margin
        top_y = body_top_y - margin
        bottom_y = body_bottom_y + margin
        left_center = (self.x - shoulder_half_width + shoulder_radius, top_y + shoulder_radius)
        right_center = (self.x + shoulder_half_width - shoulder_radius, top_y + shoulder_radius)
        points = self._shoulder_arc(*left_center, 180, 270, shoulder_radius)
        points += self._shoulder_arc(*right_center, 270, 360, shoulder_radius)
        points.append((self.x + base_half_width, bottom_y))
        points.append((self.x - base_half_width, bottom_y))
        return points

    def _leg_stance(self):
        """Per-frame walk-cycle offsets: (hip_dy, ((ankle_dx, ankle_dy) for
        the left leg then the right)). At walk_intensity 0 everything is 0 -
        a plain standing stance. The left leg leads the stride while
        sin(walk_phase) > 0, the right leg while it's < 0; the body rises a
        little each time a foot passes under it (twice per stride)."""
        swing = math.sin(self.walk_phase)
        amt = self.walk_intensity
        if not amt:
            return 0.0, ((0.0, 0.0), (0.0, 0.0))
        leg_len = self.LEG_HEIGHT + self.HIP_OVERLAP
        lift_l = max(0.0, swing) * self.WALK_LIFT * amt
        lift_r = max(0.0, -swing) * self.WALK_LIFT * amt
        dx_l = math.sin(math.radians(swing * self.WALK_STRIDE_DEG * amt)) * leg_len
        hip_dy = -abs(swing) * self.WALK_BOB * amt
        return hip_dy, ((dx_l, -lift_l), (-dx_l, -lift_r))

    def _leg_quad(self, center_x, hip_y, ankle_x, ankle_y, half_width):
        """Four points of one leg: a slightly tapered quad from the hip
        (tucked up under the torso base) down to the ankle."""
        return [
            (center_x - half_width, hip_y - self.HIP_OVERLAP),
            (center_x + half_width, hip_y - self.HIP_OVERLAP),
            (ankle_x + half_width * 0.82, ankle_y),
            (ankle_x - half_width * 0.82, ankle_y),
        ]

    def _advance_walk(self, distance):
        """Advance the walk cycle by the distance just walked and ramp the
        animation in; draw() eases it back out once movement stops. Lives on
        Person (not the movement callers) so the player, WanderRoutine and
        DockRoutine all animate identically off the one primitive."""
        if distance <= 0:
            return
        self.walk_phase = (self.walk_phase + distance * self.WALK_PACE) % (2 * math.pi)
        self.walk_intensity = min(1.0, self.walk_intensity + self.WALK_INTENSITY_GAIN)
        self._walked_this_frame = True

    def draw(self, surface):
        scale = get_scale()

        # Walk cycle: _advance_walk ramps walk_intensity in while moving;
        # ease it back out on any frame we didn't move. draw() is the one
        # per-frame hook every Person (player and NPC) shares, and the cost
        # is a single multiply for a purely cosmetic settle.
        if self._walked_this_frame:
            self._walked_this_frame = False
        elif self.walk_intensity:
            self.walk_intensity *= self.WALK_INTENSITY_DECAY
            if self.walk_intensity < 0.01:
                self.walk_intensity = 0.0

        hip_dy, ankle_offsets = self._leg_stance()

        ground_y = self.y
        body_bottom_y = ground_y - self.LEG_HEIGHT + hip_dy   # the hip line
        body_top_y = body_bottom_y - self.BODY_HEIGHT
        head_center_y = body_top_y - self.HEAD_RADIUS + self.HEAD_OVERLAP

        # An outfit recolors the shapes exactly as-is (no shape change) and
        # adds a helmet ring; bare (self.outfit == {}) falls back to shaded
        # skin tones. leg_color defaults to a darker shade of the suit.
        boot_color = self.outfit.get("boot_color", self._shade(self.SKIN_COLOR, -35))
        torso_color = self.outfit.get("suit_color", self.SKIN_COLOR)
        leg_color = self.outfit.get("leg_color", self._shade(torso_color, -22))
        helmet_color = self.outfit.get("helmet_color")
        head_color = self._shade(self.SKIN_COLOR, 30)
        # A helmet's inner rim overlaps the face a little, so the exposed
        # head reads smaller than a bare one (see HELMET_FACE_COVER).
        face_radius = self.HEAD_RADIUS - (self.HELMET_FACE_COVER if helmet_color else 0)

        margin = self.OUTLINE_WIDTH / scale

        # Accessories that sit *behind* the body (backpack, shoulder
        # spikes, helmet antenna) - drawn first so the body overlaps them.
        self._draw_back_accessories(surface, body_top_y, body_bottom_y, head_center_y, scale)

        # Legs + boots, drawn before the torso so its base covers the leg
        # tops. Each leg swings about the hip; the boot rides its ankle.
        for center_x, (ankle_dx, ankle_dy) in zip(
            (self.x - self.LEG_SEPARATION, self.x + self.LEG_SEPARATION), ankle_offsets
        ):
            ankle_x = center_x + ankle_dx
            ankle_y = ground_y + ankle_dy
            self._fill_poly(surface, self._leg_quad(center_x, body_bottom_y, ankle_x, ankle_y, self.LEG_HALF_WIDTH + margin), self.OUTLINE_COLOR, border_px=0)
            self._fill_poly(surface, self._leg_quad(center_x, body_bottom_y, ankle_x, ankle_y, self.LEG_HALF_WIDTH), leg_color, border_px=0)
            boot_top_y = ankle_y - 2 * self.BOOT_RADIUS_Y
            pygame.draw.ellipse(surface, self.OUTLINE_COLOR, (*to_screen(ankle_x - self.BOOT_RADIUS_X - margin, boot_top_y - margin), to_screen_x((self.BOOT_RADIUS_X + margin) * 2), to_screen_y((self.BOOT_RADIUS_Y + margin) * 2)))
            pygame.draw.ellipse(surface, boot_color, (*to_screen(ankle_x - self.BOOT_RADIUS_X, boot_top_y), to_screen_x(self.BOOT_RADIUS_X * 2), to_screen_y(self.BOOT_RADIUS_Y * 2)))

        outline_torso_points = [to_screen(px, py) for px, py in self._torso_points(body_top_y, body_bottom_y, margin=margin)]
        pygame.draw.polygon(surface, self.OUTLINE_COLOR, outline_torso_points)
        torso_points = [to_screen(px, py) for px, py in self._torso_points(body_top_y, body_bottom_y)]
        pygame.draw.polygon(surface, torso_color, torso_points)

        if helmet_color:
            pygame.draw.circle(surface, self.OUTLINE_COLOR, to_screen(self.x, head_center_y), max(1, int((self.HEAD_RADIUS + self.HELMET_THICKNESS + margin) * scale)))
            pygame.draw.circle(surface, helmet_color, to_screen(self.x, head_center_y), max(1, int((self.HEAD_RADIUS + self.HELMET_THICKNESS) * scale)))
        else:
            pygame.draw.circle(surface, self.OUTLINE_COLOR, to_screen(self.x, head_center_y), max(1, int((self.HEAD_RADIUS + margin) * scale)))

        # Accessories layered *over* the torso (pauldrons, chest plate,
        # sash, belt, collar, badge), under the head drawn next.
        self._draw_front_accessories(surface, body_top_y, body_bottom_y, scale)

        pygame.draw.circle(surface, head_color, to_screen(self.x, head_center_y), max(1, int(face_radius * scale)))
        if self.outfit.get("visor_color"):
            self._draw_visor(surface, head_center_y)
        else:
            eye_y = head_center_y + self.EYE_OFFSET_Y
            eye_radius_px = max(1, int(self.EYE_RADIUS * scale))
            pygame.draw.circle(surface, self.EYE_COLOR, to_screen(self.x - self.EYE_OFFSET_X, eye_y), eye_radius_px)
            pygame.draw.circle(surface, self.EYE_COLOR, to_screen(self.x + self.EYE_OFFSET_X, eye_y), eye_radius_px)

    # ---- Outfit accessory pieces ---------------------------------------
    # Each piece is one optional color key on self.outfit (see __init__);
    # an absent key just skips that piece, so a decorated outfit stays a
    # pure graphics.json entry. Shapes are traced in the same game-space
    # units as the body constants and get a thin OUTLINE_COLOR border (the
    # body itself uses an oversized dark silhouette instead, but a stroke
    # reads fine at accessory scale).
    _ACCESSORY_BORDER = 2  # screen px

    def _fill_poly(self, surface, points, color, border_px=_ACCESSORY_BORDER):
        screen_points = [to_screen(px, py) for px, py in points]
        pygame.draw.polygon(surface, color, screen_points)
        if border_px:
            pygame.draw.polygon(surface, self.OUTLINE_COLOR, screen_points, border_px)

    def _fill_circle(self, surface, cx, cy, radius, color, scale, border_px=_ACCESSORY_BORDER):
        center = to_screen(cx, cy)
        radius_px = max(1, int(radius * scale))
        pygame.draw.circle(surface, color, center, radius_px)
        if border_px:
            pygame.draw.circle(surface, self.OUTLINE_COLOR, center, radius_px, border_px)

    def _draw_back_accessories(self, surface, body_top_y, body_bottom_y, head_center_y, scale):
        outfit = self.outfit
        sw = self.SHOULDER_HALF_WIDTH

        backpack_color = outfit.get("backpack_color")
        if backpack_color:
            w = sw * 1.05
            self._fill_poly(surface, [
                (self.x - w, body_top_y - 1.5), (self.x + w, body_top_y - 1.5),
                (self.x + w, body_bottom_y + 1.0), (self.x - w, body_bottom_y + 1.0),
            ], backpack_color)

        spike_color = outfit.get("spike_color")
        if spike_color:
            for side in (-1, 1):
                base_x = self.x + side * (sw - 1)
                self._fill_poly(surface, [
                    (base_x - 1.7, body_top_y + 1.5), (base_x + 1.7, body_top_y + 1.5),
                    (base_x + side * 4.5, body_top_y - 6.0),
                ], spike_color)

        antenna_color = outfit.get("antenna_color")
        if antenna_color and outfit.get("helmet_color"):
            r = self.HEAD_RADIUS + self.HELMET_THICKNESS
            base = (self.x + r * 0.55, head_center_y - r * 0.55)
            tip = (self.x + r * 0.95, head_center_y - r * 2.0)
            pygame.draw.line(surface, self.OUTLINE_COLOR, to_screen(*base), to_screen(*tip), self._ACCESSORY_BORDER + 2)
            pygame.draw.line(surface, antenna_color, to_screen(*base), to_screen(*tip), self._ACCESSORY_BORDER)
            self._fill_circle(surface, tip[0], tip[1], 1.3, antenna_color, scale)

    def _draw_front_accessories(self, surface, body_top_y, body_bottom_y, scale):
        outfit = self.outfit
        x = self.x
        sw = self.SHOULDER_HALF_WIDTH
        bw = self.BASE_HALF_WIDTH
        torso_h = body_bottom_y - body_top_y

        chest_color = outfit.get("chest_plate_color")
        if chest_color:
            top = body_top_y + 1.5
            bot = body_top_y + torso_h * 0.62
            self._fill_poly(surface, [
                (x - sw * 0.72, top), (x + sw * 0.72, top),
                (x + bw * 1.05, bot), (x - bw * 1.05, bot),
            ], chest_color)

        sash_color = outfit.get("sash_color")
        if sash_color:
            ax, ay = x - sw, body_top_y + 0.5
            bx, by = x + bw, body_bottom_y - 0.5
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy) or 1
            nx, ny = -dy / length * 1.7, dx / length * 1.7
            self._fill_poly(surface, [
                (ax + nx, ay + ny), (ax - nx, ay - ny),
                (bx - nx, by - ny), (bx + nx, by + ny),
            ], sash_color)

        belt_color = outfit.get("belt_color")
        if belt_color:
            top = body_bottom_y - 3.0
            bot = body_bottom_y - 0.5
            self._fill_poly(surface, [
                (x - bw - 0.8, top), (x + bw + 0.8, top),
                (x + bw + 0.8, bot), (x - bw - 0.8, bot),
            ], belt_color)
            buckle = self._shade(belt_color, 45)
            mid = (top + bot) / 2
            self._fill_poly(surface, [
                (x - 1.1, mid - 1.1), (x + 1.1, mid - 1.1),
                (x + 1.1, mid + 1.1), (x - 1.1, mid + 1.1),
            ], buckle, border_px=1)

        collar_color = outfit.get("collar_color")
        if collar_color:
            top = body_top_y - 0.6
            bot = body_top_y + 2.4
            self._fill_poly(surface, [
                (x - sw * 0.62, top), (x + sw * 0.62, top),
                (x + sw * 0.70, bot), (x - sw * 0.70, bot),
            ], collar_color)

        shoulder_color = outfit.get("shoulder_color")
        if shoulder_color:
            for sx in (x - sw - 1.2, x + sw + 1.2):
                self._fill_circle(surface, sx, body_top_y + 1.8, 2.9, shoulder_color, scale)

        badge_color = outfit.get("badge_color")
        if badge_color:
            bx, by = x + 2.4, body_top_y + torso_h * 0.32
            s = 1.8
            self._fill_poly(surface, [
                (bx, by - s), (bx + s, by), (bx, by + s), (bx - s, by),
            ], badge_color, border_px=1)

    def _draw_visor(self, surface, head_center_y):
        x = self.x
        w = self.HEAD_RADIUS * 1.5
        top = head_center_y - 1.7
        bot = head_center_y + 1.9
        self._fill_poly(surface, [
            (x - w, top), (x + w, top),
            (x + w * 0.88, bot), (x - w * 0.88, bot),
        ], self.outfit["visor_color"])

    def get_distance(self, px, py):
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)

    def step_toward(self, target_x, target_y, speed, can_move_to):
        """Move up to `speed` game-units toward (target_x, target_y),
        wall-sliding off anything `can_move_to(x, y)` rejects: try the full
        step, then the x component alone, then the y component alone, so a
        wall or corner deflects the walk instead of stopping it dead.
        Returns True if the body actually moved.

        The single on-foot movement primitive - the player
        (`LocationScreen._handle_movement`), wandering NPCs (`WanderRoutine`),
        and dock-errand pilots (`DockRoutine`) all walk through this, so they
        share one notion of walls, corners, and (normalized) diagonal speed.
        Distance is capped at the remaining distance to the target, so
        arriving never overshoots."""
        dx, dy = target_x - self.x, target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-9:
            return False
        step = min(speed, dist)
        step_x, step_y = dx / dist * step, dy / dist * step
        for cand_x, cand_y in (
            (self.x + step_x, self.y + step_y),
            (self.x + step_x, self.y),
            (self.x, self.y + step_y),
        ):
            if (cand_x, cand_y) != (self.x, self.y) and can_move_to(cand_x, cand_y):
                moved = math.hypot(cand_x - self.x, cand_y - self.y)
                self.x, self.y = cand_x, cand_y
                self._advance_walk(moved)
                return True
        return False
