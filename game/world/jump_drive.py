"""Shared align-then-blast jump animation, stepped one frame at a time on
any ship's own kinematics (angle/velocity/position) - the same mechanic
SpaceScreen drives the player's ship through by hand in _update_jump/
_begin_jump, extracted here so ExplorerRoutine's AI ships can look
identical while jumping between systems instead of just teleporting.

Deliberately owns only the align/travel phase progression, not what happens
on arrival: system membership, placement, and re-engaging autopilot are all
caller-specific (SpaceScreen swaps its active system and lands the player on
the destination's outskirts; ExplorerRoutine moves a Character between two
SystemState.ai_ships lists and drops it onto an orbit circle) - call
update() every frame and act once is_complete() is True.
"""
import math

JUMP_TRAVEL_FRAMES = 150   # ~2.5s at 60fps of high-speed travel
JUMP_SPEED = 40            # world units/frame while traveling


class JumpDrive:
    def __init__(self, heading, travel_frames=JUMP_TRAVEL_FRAMES, speed=JUMP_SPEED):
        self.heading = heading % 360
        self.phase = "align"
        self.timer = 0
        self.travel_frames = travel_frames
        self.speed = speed

    @property
    def traveling(self):
        return self.phase == "travel"

    def is_complete(self):
        return self.phase == "travel" and self.timer >= self.travel_frames

    def update(self, ship):
        """Advance one frame: rotate to heading, then blast forward at self.speed."""
        if self.phase == "align":
            current_angle = ship.angle % 360
            diff = (self.heading - current_angle + 180) % 360 - 180
            step = ship.rotation_speed * 3  # snappier than normal turning, for a punchy feel
            if abs(diff) <= step:
                ship.angle = self.heading
                self.phase = "travel"
            else:
                ship.angle = (ship.angle + step * (1 if diff > 0 else -1)) % 360
        else:
            rad = math.radians(ship.angle)
            ship.velocity_x = math.sin(rad) * self.speed
            ship.velocity_y = -math.cos(rad) * self.speed
            ship.x += ship.velocity_x
            ship.y += ship.velocity_y
            self.timer += 1
