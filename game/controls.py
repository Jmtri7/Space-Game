"""Central registry of core-engine keyboard bindings.

Every gameplay key (Space View, station/moon interiors, dialogue/hailing,
debug) is named here once and mapped to its pygame key code(s). Code that
checks input imports `Action` and calls `pressed()`/`is_action()` instead of
comparing against `pygame.K_*` directly; UI text that names a key calls
`label()`/`combo()` instead of hardcoding the letter - so remapping a key
here is enough to keep both correct. See docs/CONTROLS.md.

Menu-internal keys (Enter/ESC-to-close/arrow list navigation/text entry) are
conventions, not rebindable gameplay controls, and are left out of this
registry - see docs/CONTROLS.md's "Menus" section.
"""
import pygame


class Action:
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    THRUST = "thrust"
    REVERSE = "reverse"
    ROTATE_VIEW_RIGHT = "rotate_view_right"  # Z
    ROTATE_VIEW_LEFT = "rotate_view_left"  # X
    CYCLE_TARGET_FORWARD = "cycle_target_forward"  # E
    CYCLE_TARGET_BACKWARD = "cycle_target_backward"  # Q
    CYCLE_TARGET_MODE = "cycle_target_mode"  # T (Space View)
    TALK = "talk"  # T (interiors)
    HAIL = "hail"  # R
    FIRE = "fire"  # Space
    AUTOPILOT = "autopilot"  # F
    LAND = "land"  # G (Space View)
    USE_PORTAL = "use_portal"  # G (interiors)
    STAR_MAP = "star_map"  # 1
    POSSESSIONS = "possessions"  # 2
    MISSION_LOG = "mission_log"  # 3
    JUMP = "jump"  # V
    TOGGLE_CONTROLS = "toggle_controls"  # C
    PAUSE = "pause"  # ESC
    MUTE = "mute"  # Ctrl+M
    DEBUG_TOGGLE = "debug_toggle"  # `


# Action -> tuple of pygame key codes that trigger it. First entry is the
# "primary" key used when only one label makes sense in UI text.
KEYBINDS = {
    Action.TURN_LEFT: (pygame.K_a, pygame.K_LEFT),
    Action.TURN_RIGHT: (pygame.K_d, pygame.K_RIGHT),
    Action.THRUST: (pygame.K_w, pygame.K_UP),
    Action.REVERSE: (pygame.K_s, pygame.K_DOWN),
    Action.ROTATE_VIEW_RIGHT: (pygame.K_z,),
    Action.ROTATE_VIEW_LEFT: (pygame.K_x,),
    Action.CYCLE_TARGET_FORWARD: (pygame.K_e,),
    Action.CYCLE_TARGET_BACKWARD: (pygame.K_q,),
    Action.CYCLE_TARGET_MODE: (pygame.K_t,),
    Action.TALK: (pygame.K_t,),
    Action.HAIL: (pygame.K_r,),
    Action.FIRE: (pygame.K_SPACE,),
    Action.AUTOPILOT: (pygame.K_f,),
    Action.LAND: (pygame.K_g,),
    Action.USE_PORTAL: (pygame.K_g,),
    Action.STAR_MAP: (pygame.K_1,),
    Action.POSSESSIONS: (pygame.K_2,),
    Action.MISSION_LOG: (pygame.K_3,),
    Action.JUMP: (pygame.K_v,),
    Action.TOGGLE_CONTROLS: (pygame.K_c,),
    Action.PAUSE: (pygame.K_ESCAPE,),
    Action.MUTE: (pygame.K_m,),
    Action.DEBUG_TOGGLE: (pygame.K_BACKQUOTE,),
}

# Display labels for keys pygame.key.name() would render awkwardly.
_KEY_LABELS = {
    pygame.K_UP: "↑",
    pygame.K_DOWN: "↓",
    pygame.K_LEFT: "←",
    pygame.K_RIGHT: "→",
    pygame.K_SPACE: "Space",
    pygame.K_ESCAPE: "ESC",
    pygame.K_RETURN: "Enter",
    pygame.K_BACKQUOTE: "`",
}


def key_label(key):
    """Display label for a single pygame key code."""
    return _KEY_LABELS.get(key, pygame.key.name(key).upper())


def keys_for(action):
    return KEYBINDS[action]


def pressed(keys, action):
    """True if any key bound to `action` is currently held (`keys` is
    pygame.key.get_pressed()'s array)."""
    return any(keys[k] for k in KEYBINDS[action])

def pressed_dir(keys, negative_action, positive_action):
    """Convenience for axis-style input, e.g. turn/move: -1 / 0 / +1."""
    return pressed(keys, positive_action) - pressed(keys, negative_action)


def is_action(event_key, action):
    """True if a KEYDOWN's event.key matches `action`."""
    return event_key in KEYBINDS[action]


def matches_any(event_key, *actions):
    return any(is_action(event_key, action) for action in actions)


def label(action):
    """Display label for an action's bound key(s), e.g. 'A / ←'."""
    return " / ".join(key_label(k) for k in KEYBINDS[action])


def primary_label(action):
    """Display label for just an action's first/primary key, e.g. 'W'."""
    return key_label(KEYBINDS[action][0])


def combo(*actions, sep=" / "):
    """Join the primary label of each action, e.g. combo(CYCLE_TARGET_BACKWARD,
    CYCLE_TARGET_FORWARD) -> 'Q / E'."""
    return sep.join(primary_label(action) for action in actions)
