"""Base class for NPCs and other characters in the game."""
import math
import game.aa_draw as aa
from game.utils import to_screen, get_scale, screen_affine
from game.world.possessions import Possessions
from game.world import person_figure as fig
from game.world.figure_signatures import SIGNATURE


def _face_cy(parts):
    """Centre-y of the head oval - the largest polygon in a face part list."""
    face = max((p for p in parts if "points" in p), key=lambda p: len(p["points"]))
    return sum(y for _, y in face["points"]) / len(face["points"])


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
        # boot_color/leg_color/sleeve_color, any of which may be absent.
        # None/{} means bare body, no outfit. The body silhouette itself is
        # shared across everyone: frozen data in game/world/person_figure.py
        # (see docs/DESIGN_ATLAS.md). An outfit recolours
        # that figure and switches on optional accessory pieces - each just
        # another colour key (helmet_color, shoulder_color, spike_color,
        # collar_color, chest_plate_color, sash_color, belt_color,
        # badge_color, backpack_color, antenna_color, visor_color; see
        # fig.ACC and draw()). So a new decorated outfit is still just a new
        # graphics.json entry, no drawing code needed.
        self.outfit = outfit or {}

        # Walk-cycle state (see WALK_* constants and _advance_walk). Every
        # Person animates the same way whether the player, a WanderRoutine
        # NPC, or a DockRoutine pilot is driving step_toward.
        self.walk_phase = 0.0
        self.walk_intensity = 0.0
        self._walked_this_frame = False
        # token -> resolved (r, g, b), filled lazily in _fig_color. The outfit
        # is effectively immutable for a Person, so a colour only resolves once.
        self._color_cache = {}
        # Which way the body faces: +1 = right (screen +x), -1 = left. Set from
        # the last horizontal step in step_toward and kept when standing still,
        # so the figure is always drawn facing the way it last walked. draw()
        # mirrors every figure-space x about self.x when this is -1.
        self.facing = 1

    # self.x/self.y is the ground position a character stands at (matches
    # where collision / arrival-distance checks treat them as being), not
    # their head. The body silhouette + every accessory piece live in
    # person_figure.py in these same units - centre-line at x, feet at y, y
    # negative going up - split into animation `group`s (body / arm_l /
    # arm_r / hand_l / hand_r / leg_l / leg_r / boot_l / boot_r). The legs
    # and arms carry the walk cycle; the arms swing opposite each other,
    # counter to the stride (see _leg_stance / _arm_swing and _place).
    #
    # For the side-on read, the left-side groups are drawn as the FAR limbs
    # (behind the torso, a shade darker) and the right-side groups as the NEAR
    # limbs (in front). Combined with self.facing that gives a figure that
    # struts left or right rather than facing the camera.
    LEG_HEIGHT = 10.5       # walk-cycle knob: notional hip-to-ankle length
    HIP_OVERLAP = 1.5       # (paired with LEG_HEIGHT for the stride amplitude)
    ARM_LENGTH = 11.0       # walk-cycle knob: notional shoulder-to-wrist length

    # The far limbs (the left-side groups) draw behind the torso, the near
    # limbs (right-side) in front - the small resting arm splay is baked into
    # the figure geometry in person_figure.py, not applied here.
    _BACK_GROUPS = frozenset(("arm_l", "hand_l", "leg_l", "boot_l"))
    _FRONT_GROUPS = frozenset(("arm_r", "hand_r", "leg_r", "boot_r"))

    SKIN_COLOR = (225, 180, 145)   # figure "skin" token; head/hands are shaded from this
    EYE_COLOR = (40, 30, 30)
    # Near-black silhouette tone, baked into the figure's own outline shapes
    # (each shape ships with a slightly larger copy behind it - strokeless,
    # the same rule the atlases use); matches ships' default outline_color.
    OUTLINE_COLOR = (20, 18, 25)

    # Walk cycle. walk_phase advances with the distance actually walked
    # (step_toward -> _advance_walk); walk_intensity ramps in on movement
    # and eases back out in draw() when it stops, so the legs settle to a
    # neutral stance instead of freezing mid-stride. Amplitudes are in
    # game-space units, except WALK_STRIDE_DEG (leg swing about the hip).
    WALK_PACE = 0.7             # radians of walk_phase per game-unit walked
    WALK_MAX_STEP = 0.36       # cap on phase advance per move - a fast walker
                              # (player / dock pilot at ~2.0 u/frame) would
                              # otherwise blur; a stroller (WanderRoutine at
                              # 0.5 u/frame) stays below the cap unchanged
    WALK_LIFT = 1.7          # peak rise of the swinging leg's boot
    WALK_STRIDE_DEG = 6       # peak fore/aft swing of each leg about the hip
    WALK_ARM_DEG = 9         # peak fore/aft arm swing about the shoulder
    WALK_BOB = 0.6           # body rise as a foot passes under
    WALK_INTENSITY_GAIN = 0.34  # per moving frame, up to 1.0
    WALK_INTENSITY_DECAY = 0.82  # per idle frame, back toward 0

    # How far a helmeted face sits below a bare one - the visor is extracted
    # at the bare-head position, so it's nudged down onto a helmeted face.
    # The head is an oval polygon now (the largest part in each list); the ears
    # (bare only) are far smaller, so pick by vertex count and take its centre.
    _HELM_FACE_DY = round(
        _face_cy(fig.HELMET_FACE) - _face_cy(fig.BARE_HEAD), 3)

    @staticmethod
    def _shade(color, amount):
        """Nudge a color's channels by amount (+lighter/-darker), clamped."""
        return tuple(max(0, min(255, c + amount)) for c in color)

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

    def _arm_swing(self):
        """Per-frame fore/aft wrist offset (dx) for the left (far) arm then the
        right (near) arm. The two swing *opposite* each other and counter to
        the stride - the natural human gait - about the shoulder (the offset
        ramps in from 0 at the shoulder to full at the wrist, see _place).
        Returns (0, 0) at a standstill; the relaxed splay of the rest pose is
        baked into the arm geometry, not added here."""
        amt = self.walk_intensity
        if not amt:
            return 0.0, 0.0
        swing = math.sin(self.walk_phase)
        sw = math.sin(math.radians(swing * self.WALK_ARM_DEG * amt)) * self.ARM_LENGTH
        # left/far arm trails the leading (left) leg; right/near arm leads
        return -sw, sw

    def _advance_walk(self, distance):
        """Advance the walk cycle by the distance just walked and ramp the
        animation in; draw() eases it back out once movement stops. Lives on
        Person (not the movement callers) so the player, WanderRoutine and
        DockRoutine all animate identically off the one primitive."""
        if distance <= 0:
            return
        advance = min(distance * self.WALK_PACE, self.WALK_MAX_STEP)
        self.walk_phase = (self.walk_phase + advance) % (2 * math.pi)
        self.walk_intensity = min(1.0, self.walk_intensity + self.WALK_INTENSITY_GAIN)
        self._walked_this_frame = True

    # ---- Body rendering ------------------------------------------------
    _MID_LEG_Y = (fig.LEG_HIP_Y + fig.LEG_ANKLE_Y) * 0.5
    _ARM_SPAN_Y = fig.ARM_WRIST_Y - fig.ARM_SHOULDER_Y

    @staticmethod
    def _hex(s):
        return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))

    def _fig_color(self, tok):
        """Resolve a figure colour token against this Person's outfit (cached)."""
        c = self._color_cache.get(tok)
        if c is None:
            c = self._color_cache[tok] = self._resolve_fig_color(tok)
        return c

    def _resolve_fig_color(self, tok):
        o = self.outfit
        if isinstance(tok, str) and tok.startswith("#"):
            return self._hex(tok)               # signature pieces carry literal colours
        if tok == "outline":
            return self.OUTLINE_COLOR
        if tok == "suit":
            return o.get("suit_color", self.SKIN_COLOR)
        if tok == "sleeve":
            return o.get("sleeve_color", o.get("suit_color", self.SKIN_COLOR))
        if tok == "leg":
            return o.get("leg_color", self._shade(o.get("suit_color", self.SKIN_COLOR), -22))
        if tok == "boot":
            return o.get("boot_color", self._shade(self.SKIN_COLOR, -35))
        if tok == "skin_hi":
            return self._shade(self.SKIN_COLOR, 30)
        if tok == "skin":
            return self.SKIN_COLOR
        if tok == "skin_lo":
            return self._shade(self.SKIN_COLOR, -35)
        if tok == "eye":
            return self.EYE_COLOR
        if tok == "buckle":
            belt = o.get("belt_color")
            return self._shade(belt, 45) if belt else (122, 122, 132)
        return o.get(tok, (150, 150, 150))   # accessory colour keys (gated in draw)

    @staticmethod
    def _groups(parts, groups):
        """The subset of a part list whose animation group is in `groups`."""
        return [p for p in parts if p.get("group", "body") in groups]

    def _place(self, gx, gy, group, stance, arm):
        """Figure-space point (game units, feet at origin) -> world point,
        with the walk-cycle transform for its animation group applied and the
        whole figure mirrored about self.x for its facing. The baked figure
        faces screen-left, so facing +1 (right) is the mirrored one."""
        f = -self.facing
        gx *= f
        hip_dy, ((adx_l, ady_l), (adx_r, ady_r)) = stance
        if group == "body":
            return self.x + gx, self.y + gy + hip_dy
        if group in ("leg_l", "leg_r"):
            adx, ady = (adx_l, ady_l) if group == "leg_l" else (adx_r, ady_r)
            if gy <= self._MID_LEG_Y:            # hip end - rides the body
                return self.x + gx, self.y + gy + hip_dy
            return self.x + gx + adx * f, self.y + gy + ady   # ankle end - swings
        if group in ("boot_l", "boot_r"):
            adx, ady = (adx_l, ady_l) if group == "boot_l" else (adx_r, ady_r)
            return self.x + gx + adx * f, self.y + gy + ady
        if group in ("arm_l", "hand_l", "arm_r", "hand_r"):
            adx = arm[0] if group.endswith("_l") else arm[1]
            t = min(1.0, max(0.0, (gy - fig.ARM_SHOULDER_Y) / self._ARM_SPAN_Y))
            return self.x + gx + adx * f * t, self.y + gy + hip_dy
        return self.x + gx, self.y + gy

    def _emit(self, surface, parts, stance, arm, scale, dy=0.0):
        # A Person is only ever drawn in an (unrotated) interior, so the affine
        # fast path (one multiply-add per figure point) is essentially always
        # taken; the to_screen branch is the fallback for a rotated view.
        place = self._place
        polygon, circle = aa.polygon, aa.circle
        aff = screen_affine()
        if aff:
            a, tx, ty = aff
            for p in parts:
                col = self._fig_color(p["color"])
                grp = p.get("group", "body")     # signature parts ride the torso
                if "points" in p:
                    pts = []
                    for gx, gy in p["points"]:
                        wx, wy = place(gx, gy + dy, grp, stance, arm)
                        pts.append((round(wx * a + tx), round(wy * a + ty)))
                    if len(pts) >= 3:
                        polygon(surface, col, pts)
                else:
                    cx, cy, r = p["circle"]
                    wx, wy = place(cx, cy + dy, grp, stance, arm)
                    circle(surface, col, (round(wx * a + tx), round(wy * a + ty)),
                           max(1, int(r * scale)))
            return
        for p in parts:
            col = self._fig_color(p["color"])
            grp = p.get("group", "body")
            if "points" in p:
                pts = [to_screen(*place(gx, gy + dy, grp, stance, arm)) for gx, gy in p["points"]]
                if len(pts) >= 3:
                    polygon(surface, col, pts)
            else:
                cx, cy, r = p["circle"]
                circle(surface, col, to_screen(*place(cx, cy + dy, grp, stance, arm)),
                       max(1, int(r * scale)))

    def _draw_pipeline_body(self, surface):
        """Draw a Person whose outfit names a design-pipeline body
        (docs/GRAPHICS_PIPELINE.md): the body + its set's articles, expanded
        once and deformed to the walk cycle. Colours are already resolved to
        [r, g, b] by expand(); groups are irrelevant here - the list is drawn
        back to front as returned. The body faces screen-left, so facing +1
        mirrors x about self.x, exactly like the baked figure."""
        from game.graphics import story_assets
        story = self.outfit.get("_story")
        rest = story_assets.body_frame(story, self.outfit, None)
        if not rest:
            return
        k = min(1.0, self.walk_intensity)
        if k > 0.02:
            t = (self.walk_phase / (2 * math.pi)) % 1.0
            full = story_assets.body_frame(story, self.outfit, t)
            parts = [dict(fp, points=[[rx + (fx - rx) * k, ry + (fy - ry) * k]
                                      for (rx, ry), (fx, fy) in zip(rp["points"], fp["points"])])
                     for rp, fp in zip(rest, full)]
        else:
            parts = rest
        f = -self.facing
        aff = screen_affine()
        polygon = aa.polygon
        for p in parts:
            pts = p.get("points")
            if not pts or len(pts) < 3:
                continue
            col = p["color"]
            col = self._hex(col) if isinstance(col, str) else tuple(col)
            if aff:
                a, tx, ty = aff
                proj = [(round((self.x + gx * f) * a + tx), round((self.y + gy) * a + ty))
                        for gx, gy in pts]
            else:
                proj = [to_screen(self.x + gx * f, self.y + gy) for gx, gy in pts]
            polygon(surface, col, proj)

    def draw(self, surface):
        scale = get_scale()

        if self.outfit.get("body"):
            if self._walked_this_frame:
                self._walked_this_frame = False
            elif self.walk_intensity:
                self.walk_intensity *= self.WALK_INTENSITY_DECAY
                if self.walk_intensity < 0.01:
                    self.walk_intensity = 0.0
            self._draw_pipeline_body(surface)
            return

        # Walk cycle: _advance_walk ramps walk_intensity in while moving;
        # ease it back out on any frame we didn't move. draw() is the one
        # per-frame hook every Person (player and NPC) shares.
        if self._walked_this_frame:
            self._walked_this_frame = False
        elif self.walk_intensity:
            self.walk_intensity *= self.WALK_INTENSITY_DECAY
            if self.walk_intensity < 0.01:
                self.walk_intensity = 0.0

        stance = self._leg_stance()
        arm = self._arm_swing()
        o = self.outfit
        helmeted = "helmet_color" in o

        def emit(parts, dy=0.0):
            self._emit(surface, parts, stance, arm, scale, dy)

        # Culture / role signature (eye-bubble helm, patch-plates, tool belt,
        # ...): "pre" behind the body, "post" over it. Opted in by the outfit's
        # "signature" key; see game/world/figure_signatures.py.
        sig = SIGNATURE.get(o.get("signature"))

        # Behind the body: backpack, shoulder spikes, helmet antenna.
        for key in ("backpack_color", "spike_color", "antenna_color"):
            if key in o:
                emit(fig.ACC[key])
        if sig and sig["pre"]:
            emit(sig["pre"])

        # Far arm + far leg first, behind the torso.
        emit(self._groups(fig.BASE, self._BACK_GROUPS))

        # Torso (+ neck).
        emit(self._groups(fig.BASE, ("body",)))

        # Helmet ring sits behind the front torso pieces; the face it frames
        # is drawn later, over them.
        if helmeted:
            emit(fig.HELMET_RING)

        # Layered over the torso: chest plate -> sash -> collar -> belt.
        for key in ("chest_plate_color", "sash_color", "collar_color", "belt_color"):
            if key in o:
                emit(fig.ACC[key])

        # Near arm + near leg, in front of the torso, then the pauldrons over
        # the (near) arm top.
        emit(self._groups(fig.BASE, self._FRONT_GROUPS))
        if "shoulder_color" in o:
            emit(fig.ACC["shoulder_color"])

        # The face, then the visor (over the eyes) or the eyes.
        emit(fig.HELMET_FACE if helmeted else fig.BARE_HEAD)
        if "visor_color" in o:
            emit(fig.ACC["visor_color"], dy=self._HELM_FACE_DY if helmeted else 0.0)
        else:
            emit(fig.EYES_HELM if helmeted else fig.EYES_BARE)

        if "badge_color" in o:
            emit(fig.ACC["badge_color"])

        if sig and sig["post"]:
            emit(sig["post"])

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
                mvx, mvy = cand_x - self.x, cand_y - self.y
                if abs(mvx) > abs(mvy):         # face the way we're walking when
                    self.facing = 1 if mvx > 0 else -1   # it's mostly sideways; keep it when we stop
                self.x, self.y = cand_x, cand_y
                self._advance_walk(moved)
                return True
        return False
