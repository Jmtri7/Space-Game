"""Player ship controller."""
import pygame
from game.constants import DARK_GRAY
from game.world.ship import Ship
from game.world.person import Person


class PlayerController:
    """Controls the player's ship - owns the ship and handles input.

    Also owns a Person representing the player themselves, aboard the ship
    while flying (mirrored to the ship's position each frame, not drawn
    separately - see LocationScreen/PlayerCharacter for the player's walking
    body once they land)."""
    def __init__(self, x, y, space_drag=0, graphics=None, ship_type=None, pilot_name="", outfit=None):
        self.ship = Ship(x, y, space_drag=space_drag, graphics=graphics)
        self.person = Person(x, y, name=pilot_name, outfit=outfit)
        if ship_type:
            self.ship.acceleration_magnitude = ship_type.get("max_thrust", self.ship.acceleration_magnitude)
            self.ship.max_velocity = ship_type.get("max_velocity", self.ship.max_velocity)
            self.ship.rotation_speed = ship_type.get("rotation_speed", self.ship.rotation_speed)

    def handle_input(self, keys):
        """Handle player keyboard input (blocked during autopilot)."""
        if self.ship.autopilot_active:
            return

        # Rotation controls
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.ship.turn_left()
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.ship.turn_right()

        # Thrust controls
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.ship.increase_thrust()
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            # Point ship toward opposite velocity (brake/reverse)
            self.ship.point_to_reverse_velocity()
        else:
            self.ship.release_thrust()

    def update(self):
        """Update ship physics, and keep the pilot's Person aboard it."""
        self.ship.update()
        self.person.x = self.ship.x
        self.person.y = self.ship.y

    def draw(self, surface):
        """Draw ship."""
        self.ship.draw(surface, ship_size=15, color=DARK_GRAY)

    def park(self):
        """Come to a full stop - landed/docked."""
        self.ship.park()

    # Delegation properties for backward compatibility
    @property
    def x(self):
        return self.ship.x

    @x.setter
    def x(self, value):
        self.ship.x = value

    @property
    def y(self):
        return self.ship.y

    @y.setter
    def y(self, value):
        self.ship.y = value

    @property
    def velocity_x(self):
        return self.ship.velocity_x

    @velocity_x.setter
    def velocity_x(self, value):
        self.ship.velocity_x = value

    @property
    def velocity_y(self):
        return self.ship.velocity_y

    @velocity_y.setter
    def velocity_y(self, value):
        self.ship.velocity_y = value

    @property
    def angle(self):
        return self.ship.angle

    @angle.setter
    def angle(self, value):
        self.ship.angle = value

    @property
    def thrust(self):
        return self.ship.thrust

    @thrust.setter
    def thrust(self, value):
        self.ship.thrust = value

    @property
    def autopilot_active(self):
        return self.ship.autopilot_active

    @autopilot_active.setter
    def autopilot_active(self, value):
        self.ship.autopilot_active = value

    @property
    def autopilot_target(self):
        return self.ship.autopilot_target

    @autopilot_target.setter
    def autopilot_target(self, value):
        self.ship.autopilot_target = value

    def engage_seek(self, target):
        """Delegate to ship's standardized seek-autopilot mode."""
        self.ship.engage_seek(target)

    def get_distance(self, target_x, target_y):
        return self.ship.get_distance(target_x, target_y)
