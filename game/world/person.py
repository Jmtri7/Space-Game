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
        # boot_color, any of which may be absent. None/{} means bare body,
        # no outfit. The body shape itself stays shared across everyone for
        # now; outfits only override its colors and add a helmet, so a new
        # outfit is just a new graphics.json entry, no drawing code needed.
        self.outfit = outfit or {}

    # Body proportions, all measured up from the feet (self.x/self.y is the
    # ground position a character is standing at, not their head or
    # shoulders - matches where collision/arrival distance checks treat
    # them as being). The bare body is just three shapes - a foot oval, a
    # tapering rounded-shoulder torso polygon, and a head circle - shaded
    # from one skin tone as if lit from above (head lightest, feet
    # darkest). An outfit (see self.outfit) recolors the oval/polygon and
    # adds a thick helmet ring around the head, but never changes this
    # shape - see draw().
    FOOT_RADIUS_X = 5.5      # feet oval - wider than tall
    FOOT_RADIUS_Y = 4
    FOOT_OVERLAP = 2         # how far the torso sinks into the top of the feet oval
    BODY_HEIGHT = 13         # torso height, shoulders to (pre-overlap) base
    SHOULDER_HALF_WIDTH = 7  # torso half-width at the (rounded) shoulders
    BASE_HALF_WIDTH = 4.5    # torso half-width at the base - a bit less than the feet oval
    SHOULDER_RADIUS = 3.5    # rounding radius of each shoulder corner
    SHOULDER_SEGMENTS = 4    # polygon segments approximating each shoulder's curve
    HEAD_RADIUS = 5.5        # slightly large, so it overlaps the shoulders below
    HEAD_OVERLAP = 0.1       # how far the head sinks between the shoulders
    HELMET_THICKNESS = 3.5   # ring width of a helmet, when outfitted
    EYE_RADIUS = 0.8
    EYE_OFFSET_X = 2.2       # each eye's distance from center
    EYE_OFFSET_Y = 0.5       # slightly below head center

    SKIN_COLOR = (225, 180, 145)  # torso tone; head/feet are shaded from this
    EYE_COLOR = (40, 30, 30)

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
        narrower) bottom corners - which sit hidden under the feet oval's
        overlap, so they don't need rounding too.

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

    def draw(self, surface):
        scale = get_scale()
        feet_top_y = self.y - self.FOOT_RADIUS_Y * 2
        body_bottom_y = feet_top_y + self.FOOT_OVERLAP
        body_top_y = body_bottom_y - self.BODY_HEIGHT
        head_center_y = body_top_y - self.HEAD_RADIUS + self.HEAD_OVERLAP

        # An outfit recolors the feet/torso shapes exactly as-is (no shape
        # change) and adds a helmet ring; bare (self.outfit == {}) falls
        # back to the shaded skin tones.
        feet_color = self.outfit.get("boot_color", self._shade(self.SKIN_COLOR, -35))
        torso_color = self.outfit.get("suit_color", self.SKIN_COLOR)
        helmet_color = self.outfit.get("helmet_color")
        head_color = self._shade(self.SKIN_COLOR, 30)

        margin = self.OUTLINE_WIDTH / scale

        pygame.draw.ellipse(surface, self.OUTLINE_COLOR, (*to_screen(self.x - self.FOOT_RADIUS_X - margin, feet_top_y - margin), to_screen_x((self.FOOT_RADIUS_X + margin) * 2), to_screen_y((self.FOOT_RADIUS_Y + margin) * 2)))
        pygame.draw.ellipse(surface, feet_color, (*to_screen(self.x - self.FOOT_RADIUS_X, feet_top_y), to_screen_x(self.FOOT_RADIUS_X * 2), to_screen_y(self.FOOT_RADIUS_Y * 2)))

        outline_torso_points = [to_screen(px, py) for px, py in self._torso_points(body_top_y, body_bottom_y, margin=margin)]
        pygame.draw.polygon(surface, self.OUTLINE_COLOR, outline_torso_points)
        torso_points = [to_screen(px, py) for px, py in self._torso_points(body_top_y, body_bottom_y)]
        pygame.draw.polygon(surface, torso_color, torso_points)

        if helmet_color:
            pygame.draw.circle(surface, self.OUTLINE_COLOR, to_screen(self.x, head_center_y), max(1, int((self.HEAD_RADIUS + self.HELMET_THICKNESS + margin) * scale)))
            pygame.draw.circle(surface, helmet_color, to_screen(self.x, head_center_y), max(1, int((self.HEAD_RADIUS + self.HELMET_THICKNESS) * scale)))
        else:
            pygame.draw.circle(surface, self.OUTLINE_COLOR, to_screen(self.x, head_center_y), max(1, int((self.HEAD_RADIUS + margin) * scale)))
        pygame.draw.circle(surface, head_color, to_screen(self.x, head_center_y), max(1, int(self.HEAD_RADIUS * scale)))
        eye_y = head_center_y + self.EYE_OFFSET_Y
        eye_radius_px = max(1, int(self.EYE_RADIUS * scale))
        pygame.draw.circle(surface, self.EYE_COLOR, to_screen(self.x - self.EYE_OFFSET_X, eye_y), eye_radius_px)
        pygame.draw.circle(surface, self.EYE_COLOR, to_screen(self.x + self.EYE_OFFSET_X, eye_y), eye_radius_px)

    def get_distance(self, px, py):
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)
