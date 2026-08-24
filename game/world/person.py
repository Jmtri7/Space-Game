"""Base class for NPCs and other characters in the game."""
import pygame
import math
from game.utils import to_screen, to_screen_x, to_screen_y, get_scale


class Person:
    """Base class for anyone with a position and a body - the player's own
    walking self (see PlayerCharacter), NPCs, and a ship's pilot all share
    this identity regardless of whether they currently have a ship."""
    def __init__(self, x, y, name=""):
        self.x = x
        self.y = y
        self.name = name

    # Body proportions, all measured up from the feet (self.x/self.y is the
    # ground position a character is standing at, not their head or
    # shoulders - matches where collision/arrival distance checks treat
    # them as being).
    BODY_WIDTH = 12
    BODY_HEIGHT = 16
    SHIRT_FRACTION = 0.6  # top portion of the body that's shirt vs legs
    ARM_WIDTH = 3
    ARM_HEIGHT = 10
    NECK_WIDTH = 4
    NECK_HEIGHT = 3
    HEAD_RADIUS = 5

    SHIRT_COLOR = (200, 100, 100)
    LEGS_COLOR = (110, 85, 105)
    SKIN_COLOR = (255, 150, 150)

    def draw(self, surface):
        scale = get_scale()
        body_top = self.y - self.BODY_HEIGHT
        shirt_height = self.BODY_HEIGHT * self.SHIRT_FRACTION
        legs_top = body_top + shirt_height
        neck_top = body_top - self.NECK_HEIGHT
        head_center_y = neck_top - self.HEAD_RADIUS

        # Legs, then arms flanking the torso, then the shirt on top - simple
        # rects/circle throughout, just enough shapes to read as a person
        # rather than a single block.
        pygame.draw.rect(surface, self.LEGS_COLOR, (*to_screen(self.x - self.BODY_WIDTH / 2, legs_top), to_screen_x(self.BODY_WIDTH), to_screen_y(self.BODY_HEIGHT - shirt_height)))
        pygame.draw.rect(surface, self.SHIRT_COLOR, (*to_screen(self.x - self.BODY_WIDTH / 2 - self.ARM_WIDTH, body_top), to_screen_x(self.ARM_WIDTH), to_screen_y(self.ARM_HEIGHT)))
        pygame.draw.rect(surface, self.SHIRT_COLOR, (*to_screen(self.x + self.BODY_WIDTH / 2, body_top), to_screen_x(self.ARM_WIDTH), to_screen_y(self.ARM_HEIGHT)))
        pygame.draw.rect(surface, self.SHIRT_COLOR, (*to_screen(self.x - self.BODY_WIDTH / 2, body_top), to_screen_x(self.BODY_WIDTH), to_screen_y(shirt_height)))
        pygame.draw.rect(surface, self.SKIN_COLOR, (*to_screen(self.x - self.NECK_WIDTH / 2, neck_top), to_screen_x(self.NECK_WIDTH), to_screen_y(self.NECK_HEIGHT)))
        pygame.draw.circle(surface, self.SKIN_COLOR, to_screen(self.x, head_center_y), max(1, int(self.HEAD_RADIUS * scale)))

    def get_distance(self, px, py):
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)
