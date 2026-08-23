# Space Game Controls

All interactive controls and their bindings. **Update this document when adding or changing any control**.

## Space View (Default)

| Control | Action |
|---------|--------|
| **W** or **↑** | Thrust forward |
| **A** or **←** | Rotate left |
| **D** or **→** | Rotate right |
| **S** or **↓** | Reduce thrust (coast) |
| **L** | Land on nearby station or moon (when in range) |
| **ESC** | Pause menu |

## Station Interior

| Control | Action |
|---------|--------|
| **W/A/S/D** or **Arrow Keys** | Move around |
| **T** | Talk to nearby NPC |
| **L** | Exit station, return to space |
| **ESC** | Pause menu |

## Moon Interior (City & Wilderness)

| Control | Action |
|---------|--------|
| **W/A/S/D** or **Arrow Keys** | Move around |
| **T** | Talk to nearby NPC (City only) |
| **L** | Exit moon, return to space |
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
