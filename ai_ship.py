"""AI ship with autonomous behavior."""
import math
import random
from constants import DARK_GRAY
from ship import Ship


class AIShip(Ship):
    """Autonomous AI ship with wandering behavior."""
    def __init__(self, x, y, space_drag=0, ship_type=None, ship_type_id="trader"):
        super().__init__(x, y, space_drag=space_drag)
        self.ship_type_id = ship_type_id
        self.angle = random.randint(0, 360)

        # Apply ship type properties if provided
        if ship_type:
            self.max_thrust = ship_type.get("max_thrust", 0.15)
            self.max_velocity = ship_type.get("max_velocity", 4.0)
            self.rotation_speed = ship_type.get("rotation_speed", 5)
            self.ship_color = ship_type.get("color", DARK_GRAY)
            self.ship_size = ship_type.get("size", 12)
        else:
            self.max_thrust = 0.15
            self.ship_color = DARK_GRAY
            self.ship_size = 12

        self.state = "accelerate"
        self.state_timer = 0

    def update(self):
        """Update AI ship with autonomous behavior."""
        self.state_timer -= 1

        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)

        if self.state == "accelerate":
            if self.state_timer <= 0:
                self.state = "brake"
                self.state_timer = random.randint(30, 60)
            else:
                self.thrust = self.max_thrust
                self.angle = (self.angle + random.uniform(-1, 1)) % 360

        elif self.state == "brake":
            if speed < 0.15:
                self.state = "accelerate"
                self.state_timer = random.randint(40, 80)
                self.angle = random.uniform(0, 360)
                self.thrust = 0
                self.velocity_x *= 0.95
                self.velocity_y *= 0.95
            else:
                velocity_angle = math.degrees(math.atan2(self.velocity_x, -self.velocity_y)) % 360
                target_angle = (velocity_angle + 180) % 360
                angle_diff = (target_angle - self.angle) % 360
                if angle_diff > 180:
                    angle_diff -= 360

                if abs(angle_diff) > 2:
                    self.angle = (self.angle + angle_diff * 0.1) % 360
                self.thrust = self.max_thrust

        rad = math.radians(self.angle)
        if self.thrust > 0.01:
            self.velocity_x += math.sin(rad) * self.thrust
            self.velocity_y -= math.cos(rad) * self.thrust

        # Apply space system drag
        if self.space_drag > 0:
            self.velocity_x *= self.space_drag
            self.velocity_y *= self.space_drag

        self.x += self.velocity_x
        self.y += self.velocity_y

        self.wrap_position()

    def draw(self, surface):
        """Draw AI ship with ship type size and color."""
        super().draw(surface, ship_size=self.ship_size, color=tuple(self.ship_color))
