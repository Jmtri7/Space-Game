"""Weapon projectile fired from the player's ship."""
import math
from game.utils import to_screen, get_scale
from game.world.world_object import WorldObject
from game.ui.ui_theme import draw_item_icon


# Fallbacks for any field a caller doesn't pass through (or a weapon outfit's
# config omits) - all match ship_outfits.json's "laser_cannon", so a
# projectile fired with no weapon-specific config still looks/behaves like
# the baseline weapon rather than something broken. See
# SpaceScreen._equipped_weapon_stats, which resolves the actual per-weapon
# values from whatever's installed (damage/speed/size/icon all vary per
# weapon outfit - see ship_outfits.json's pulse_blaster/heavy_cannon/
# scatter_gun for the range).
PROJECTILE_SPEED = 15  # world units/frame
PROJECTILE_SIZE = 3    # world units - drawn glyph's radius, before scale
PROJECTILE_LIFETIME = 200  # frames before despawn
PROJECTILE_DAMAGE = 3
DEFAULT_ICON_SHAPE = "blade"
DEFAULT_ICON_COLOR = (100, 200, 255)


class Projectile(WorldObject):
    """A weapon projectile fired by the player ship. Travels in a straight
    line and despawns after a set lifetime or on collision. Drawn as the
    firing weapon outfit's own shop icon (see ui_theme.draw_item_icon),
    rotated to face its direction of travel and sized off the outfit's own
    `projectile_size` - so a projectile visibly matches whatever's actually
    mounted in the weapon slot (icon, size, damage all per-weapon) rather
    than a single hardcoded look."""
    def __init__(self, x, y, velocity_x, velocity_y, angle=0,
                 icon_shape=DEFAULT_ICON_SHAPE, icon_color=DEFAULT_ICON_COLOR,
                 size=PROJECTILE_SIZE, damage=PROJECTILE_DAMAGE, lifetime=PROJECTILE_LIFETIME):
        super().__init__(x, y)
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.angle = angle  # degrees, same convention as Ship.angle (0 = facing "up")
        self.icon_shape = icon_shape
        self.icon_color = icon_color
        self.size = size
        self.lifetime = lifetime
        self.damage = damage

    def update(self):
        """Move projectile; return False if expired."""
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.lifetime -= 1
        return self.lifetime > 0

    def draw(self, surface):
        """Draw the weapon's own icon glyph, rotated to face travel direction."""
        scale = get_scale()
        screen_x, screen_y = to_screen(self.x, self.y)
        icon_size = max(2, int(round(self.size * scale)))
        draw_item_icon(surface, screen_x, screen_y, icon_size, self.icon_shape, self.icon_color,
                        angle=math.radians(self.angle))
