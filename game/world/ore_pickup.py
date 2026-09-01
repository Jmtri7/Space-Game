"""Drifting cargo debris left behind when a mined asteroid is destroyed -
the player has to fly over it (with room in the hold) to actually collect
it, rather than mining crediting cargo instantly on the kill. See
SpaceScreen._destroy_asteroid (spawns these) and
SpaceScreen._update_ore_pickups (drift/lifetime/collection)."""
import math
import random
from game.utils import to_screen, get_scale
from game.world.world_object import WorldObject
from game.ui.ui_theme import draw_item_icon

DRIFT_SPEED_RANGE = (0.15, 0.5)   # world units/frame - slow, so it stays
                                   # reachable rather than outrunning the field
LIFETIME_FRAMES = 3600            # ~60s at 60fps before an uncollected chunk
                                   # disperses, so a heavily-mined field doesn't
                                   # accumulate debris without bound
FADE_FRAMES = 90                  # ~1.5s fade-out at the end of its lifetime
PICKUP_RANGE = 22                 # world units from ship center that counts as "flown over"
SPIN_SPEED = 1.4                  # degrees/frame - slow tumble, purely cosmetic


class OrePickup(WorldObject):
    """A chunk of `amount` units of `commodity_id`, drifting at a constant
    slow velocity from where an asteroid it was mined from broke apart.
    Purely additive state - never captured by SpaceScreen.get_state()/
    restore_state() (see SAVE_SYSTEM.md), same as AsteroidField itself, so a
    save doesn't need to know about in-flight debris."""
    def __init__(self, x, y, amount, commodity_id="ore", icon_shape="crate", icon_color=(150, 110, 80), rng=None):
        super().__init__(x, y)
        rng = rng or random
        heading = rng.uniform(0, 2 * math.pi)
        speed = rng.uniform(*DRIFT_SPEED_RANGE)
        self.velocity_x = math.cos(heading) * speed
        self.velocity_y = math.sin(heading) * speed
        self.amount = amount
        self.commodity_id = commodity_id
        self.icon_shape = icon_shape
        self.icon_color = icon_color
        self.angle = rng.uniform(0, 360)
        self.spin_speed = rng.choice([-1, 1]) * SPIN_SPEED
        self.age = 0

    def update(self):
        """Drift and age; returns False once its lifetime has fully elapsed."""
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.angle = (self.angle + self.spin_speed) % 360
        self.age += 1
        return self.age < LIFETIME_FRAMES

    def draw(self, surface):
        scale = get_scale()
        screen_x, screen_y = to_screen(self.x, self.y)
        remaining = LIFETIME_FRAMES - self.age
        fade = min(1.0, remaining / FADE_FRAMES) if remaining < FADE_FRAMES else 1.0
        # Gentle pulse (independent of fade) so a drifting pickup reads as
        # "alive" against a starfield instead of a static dot.
        pulse = 0.85 + 0.15 * math.sin(self.age * 0.08)
        icon_size = max(2, int(round(4 * pulse * scale)))
        color = tuple(int(c * fade) for c in self.icon_color)
        draw_item_icon(surface, screen_x, screen_y, icon_size, self.icon_shape, color,
                        angle=math.radians(self.angle))
