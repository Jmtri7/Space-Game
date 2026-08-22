"""
Pure physics calculations decoupled from Pygame rendering.
All functions are pure (no side effects, deterministic output).
"""
import math

# Physics constants
DRAG = 0.98
MAX_VELOCITY = 4.0
MAX_THRUST = 0.3
THRUST_ACCELERATION = 0.02
ROTATION_SPEED = 5.0
GAME_WIDTH = 800
GAME_HEIGHT = 600


def update_velocity(velocity_x, velocity_y, thrust, angle, drag=DRAG, max_velocity=MAX_VELOCITY):
    """
    Update velocity based on thrust and drag.

    Args:
        velocity_x, velocity_y: Current velocity components
        thrust: Thrust magnitude (0.0 to MAX_THRUST)
        angle: Ship facing angle in degrees
        drag: Friction multiplier (default 0.98)
        max_velocity: Speed cap (default 4.0)

    Returns:
        (new_velocity_x, new_velocity_y)
    """
    # Apply thrust
    rad = math.radians(angle)
    new_vx = velocity_x + math.sin(rad) * thrust
    new_vy = velocity_y - math.cos(rad) * thrust

    # Apply drag
    new_vx *= drag
    new_vy *= drag

    # Cap speed
    speed = math.sqrt(new_vx ** 2 + new_vy ** 2)
    if speed > max_velocity:
        scale = max_velocity / speed
        new_vx *= scale
        new_vy *= scale

    return new_vx, new_vy


def update_position(x, y, velocity_x, velocity_y):
    """
    Update position based on velocity.

    Returns:
        (new_x, new_y)
    """
    return x + velocity_x, y + velocity_y


def wrap_position(x, y, width=GAME_WIDTH, height=GAME_HEIGHT):
    """
    Wrap position at screen edges (torus topology).

    Returns:
        (new_x, new_y)
    """
    if x < 0:
        x = width
    elif x > width:
        x = 0

    if y < 0:
        y = height
    elif y > height:
        y = 0

    return x, y


def update_thrust(thrust, keys_accelerating, keys_decelerating, max_thrust=MAX_THRUST, accel=THRUST_ACCELERATION):
    """
    Update thrust based on input keys.

    Args:
        thrust: Current thrust magnitude
        keys_accelerating: Boolean, true if thrust keys pressed
        keys_decelerating: Boolean, true if brake keys pressed
        max_thrust: Maximum thrust magnitude
        accel: Acceleration per frame

    Returns:
        new_thrust
    """
    if keys_accelerating:
        thrust = min(thrust + accel, max_thrust)
    else:
        thrust = max(thrust - accel, 0)

    return thrust


def update_angle(angle, keys_left, keys_right, rotation_speed=ROTATION_SPEED):
    """
    Update ship facing angle based on input keys.

    Args:
        angle: Current angle in degrees
        keys_left: Boolean, true if turning left
        keys_right: Boolean, true if turning right
        rotation_speed: Degrees per frame

    Returns:
        new_angle (0-360)
    """
    if keys_left:
        angle -= rotation_speed
    if keys_right:
        angle += rotation_speed

    # Keep angle in 0-360 range
    angle = angle % 360
    return angle


def get_distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def can_land(player_x, player_y, station_x, station_y, distance_threshold=100, speed_threshold=0.5, velocity_x=0, velocity_y=0):
    """
    Check if player can land at station.

    Args:
        player_x, player_y: Player position
        station_x, station_y: Station position
        distance_threshold: Maximum distance to land
        speed_threshold: Maximum speed to land
        velocity_x, velocity_y: Player velocity

    Returns:
        Boolean, true if landing is possible
    """
    distance = get_distance(player_x, player_y, station_x, station_y)
    speed = math.sqrt(velocity_x ** 2 + velocity_y ** 2)
    return distance < distance_threshold and speed < speed_threshold


def rotate_point(x, y, center_x, center_y, angle):
    """
    Rotate a point around a center by angle (in degrees).

    Returns:
        (rotated_x, rotated_y)
    """
    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    # Translate to origin
    lx = x - center_x
    ly = y - center_y

    # Rotate
    rotated_x = lx * cos_a - ly * sin_a
    rotated_y = lx * sin_a + ly * cos_a

    # Translate back
    return center_x + rotated_x, center_y + rotated_y
