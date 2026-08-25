# Space Game Controls

All interactive controls and their bindings. **Update this document when adding or changing any control**.

## Space View (Default)

| Control | Action |
|---------|--------|
| **W** or **↑** | Thrust forward |
| **A** or **←** | Rotate left |
| **D** or **→** | Rotate right |
| **S** or **↓** | Turn to face opposite velocity (reverse heading) |
| **T** or **]** | Cycle forward through targetable objects (station, moon, AI ship, celestial bodies, star) |
| **[** | Cycle backward through targetable objects |
| **L** | Land on targeted object or nearby (when in range) |
| **M** | Open the star map |
| **J** | Jump to the selected star system (see Star Map below) |
| **ESC** | Pause menu |

## Star Map (M)

| Control | Action |
|---------|--------|
| **Click** a system | Select it as the jump target |
| **Click + drag** empty space | Pan the map |
| **M** or **ESC** | Close the map (selection persists) |

Opens centered on your current system. The selected system (if any) is shown
back in the space view as "Jump Target:", and pressing **J** there starts the
jump if the target is a different system, or the current one while far enough
from its center.

## Station Interior

| Control | Action |
|---------|--------|
| **W/A/S/D** or **Arrow Keys** | Move around |
| **T** or **]** | Cycle forward through targetable NPCs |
| **[** | Cycle backward through targetable NPCs |
| **Enter** | Talk to targeted NPC |
| **L** | Exit near the entrance - returns to space directly if that's the only option, otherwise opens the Exit Menu below |
| **ESC** | Pause menu |

## Moon Interior (City & Wilderness)

| Control | Action |
|---------|--------|
| **W/A/S/D** or **Arrow Keys** | Move around |
| **T** or **]** / **[** | Cycle through targetable NPCs, forward/backward (City only) |
| **Enter** | Talk to targeted NPC |
| **L** | Exit near the entrance - returns to space directly if that's the only option, otherwise opens the Exit Menu below |
| **ESC** | Pause menu |

## Menus

### Main Menu
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Navigate options |
| **Enter** | Select option |
| **ESC** | Cancel (only on submenus) |

### Save/Load Dialogs
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Navigate saves |
| **Enter** | Select/save |
| **N** | Create new save (save dialog) |
| **D** | Delete selected save |
| **ESC** | Cancel |

### Pause Menu
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Navigate options |
| **Enter** | Select option |
| **ESC** | Resume game |

### Exit Menu (interior location, when the entrance leads to more than one place)
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Navigate destinations |
| **Enter** | Go to selected destination (a connected location, or "Return to Ship") |
| **ESC** | Cancel, stay put |

Shown instead of leaving immediately when a location's config lists
`connected_locations` (other interiors reachable on foot from this one,
e.g. Moon City ↔ Wilderness) and/or sets `return_to_ship`. AI pilots
(see `DockRoutine`) pick a destination from the same option list
automatically, based on their role, instead of getting this menu.

## Debug Controls

| Control | Action |
|---------|--------|
| **`** (backtick) | Toggle debug mode (shows entity position markers) |

Debug mode displays green X marks at the world coordinates of all entities:
- Space view: player ship, station, moon, AI ship
- Interiors: player, NPCs

Use this to diagnose coordinate and positioning issues.

## Notes

- **Arrow keys and WASD are interchangeable** for movement and navigation
- **ESC always pauses** the game (from any screen)
- All menus show help text at the bottom with available actions
