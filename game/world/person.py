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
    # them as being).
    BODY_WIDTH = 12
    BODY_HEIGHT = 16
    SHIRT_FRACTION = 0.6  # top portion of the body that's shirt vs legs
    BOOT_FRACTION = 0.4  # bottom portion of the legs that's boots, when suited
    ARM_WIDTH = 3
    ARM_HEIGHT = 10
    NECK_WIDTH = 4
    NECK_HEIGHT = 3
    HEAD_RADIUS = 5
    HELMET_RADIUS = 6

    SHIRT_COLOR = (150, 110, 70)
    LEGS_COLOR = (100, 70, 45)
    SKIN_COLOR = (230, 180, 140)

    def draw(self, surface):
        scale = get_scale()
        body_top = self.y - self.BODY_HEIGHT
        shirt_height = self.BODY_HEIGHT * self.SHIRT_FRACTION
        legs_top = body_top + shirt_height
        legs_height = self.BODY_HEIGHT - shirt_height
        neck_top = body_top - self.NECK_HEIGHT
        head_center_y = neck_top - self.HEAD_RADIUS

        # An outfit overrides the shared body's colors and adds a helmet;
        # bare (self.outfit == {}) falls back to the plain body colors.
        suit_color = self.outfit.get("suit_color", self.SHIRT_COLOR)
        boot_color = self.outfit.get("boot_color", self.LEGS_COLOR)
        helmet_color = self.outfit.get("helmet_color")

        # Legs (boots at the bottom, if suited), then arms flanking the
        # torso, then the shirt on top - simple rects/circles throughout,
        # just enough shapes to read as a person rather than a single block.
        if helmet_color:
            boot_height = legs_height * self.BOOT_FRACTION
            pygame.draw.rect(surface, suit_color, (*to_screen(self.x - self.BODY_WIDTH / 2, legs_top), to_screen_x(self.BODY_WIDTH), to_screen_y(legs_height - boot_height)))
            pygame.draw.rect(surface, boot_color, (*to_screen(self.x - self.BODY_WIDTH / 2, legs_top + legs_height - boot_height), to_screen_x(self.BODY_WIDTH), to_screen_y(boot_height)))
        else:
            pygame.draw.rect(surface, boot_color, (*to_screen(self.x - self.BODY_WIDTH / 2, legs_top), to_screen_x(self.BODY_WIDTH), to_screen_y(legs_height)))
        pygame.draw.rect(surface, suit_color, (*to_screen(self.x - self.BODY_WIDTH / 2 - self.ARM_WIDTH, body_top), to_screen_x(self.ARM_WIDTH), to_screen_y(self.ARM_HEIGHT)))
        pygame.draw.rect(surface, suit_color, (*to_screen(self.x + self.BODY_WIDTH / 2, body_top), to_screen_x(self.ARM_WIDTH), to_screen_y(self.ARM_HEIGHT)))
        pygame.draw.rect(surface, suit_color, (*to_screen(self.x - self.BODY_WIDTH / 2, body_top), to_screen_x(self.BODY_WIDTH), to_screen_y(shirt_height)))
        # A sealed helmet covers the neck too (suit_color collar); bare-headed
        # shows a strip of skin between shirt and head instead.
        pygame.draw.rect(surface, suit_color if helmet_color else self.SKIN_COLOR, (*to_screen(self.x - self.NECK_WIDTH / 2, neck_top), to_screen_x(self.NECK_WIDTH), to_screen_y(self.NECK_HEIGHT)))
        if helmet_color:
            pygame.draw.circle(surface, helmet_color, to_screen(self.x, head_center_y), max(1, int(self.HELMET_RADIUS * scale)))
        pygame.draw.circle(surface, self.SKIN_COLOR, to_screen(self.x, head_center_y), max(1, int(self.HEAD_RADIUS * scale)))

    def get_distance(self, px, py):
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)
