# Space Game Controls

All interactive controls and their bindings. **Update this document when adding or changing any control**.

## Space View (Default)

| Control | Action |
|---------|--------|
| **W** or **↑** | Thrust forward |
| **A** or **←** | Rotate left |
| **D** or **→** | Rotate right |
| **S** or **↓** | Turn to face opposite velocity (reverse heading) |
| **]** | Cycle forward through targetable objects in the current target mode |
| **[** | Cycle backward through targetable objects in the current target mode |
| **T** | Cycle target mode: SHIPS (AI ships only) → LANDABLES (station/moon only) → MISC (celestial bodies, star). Starts on LANDABLES. |
| **Click** an object | Target it directly - infers and switches target mode to match whatever was clicked |
| **Space** | Engage autopilot toward the targeted object (follows an AI ship, or approaches a landable from any range) |
| **L** | Land - on the targeted landable if already in range, otherwise on whatever's nearby (never engages autopilot) |
| **M** | Open the star map |
| **J** | Jump to the selected star system (see Star Map below) |
| **P** | Open the Possessions menu (credits, owned ships, loans) |
| **ESC** | Pause menu |

## Star Map (M)

| Control | Action |
|---------|--------|
| **Click** a system | Select it as the jump target |
| **Click + drag** empty space | Pan the map |
| **W/A/S/D** or **Arrow Keys** | Scroll the map |
| **M** or **ESC** | Close the map (selection persists) |

Opens centered on your current system, with a "You are here" tag next to it.
A Controls pane (top-left) and the selected system's station/moon panel
(top-right) share the same look as the space view's HUD. The selected
system (if any) is shown back in the space view as "Jump Target:", and
pressing **J** there starts the jump if the target is a different system, or
the current one while far enough from its center.

## Station Interior

| Control | Action |
|---------|--------|
| **W/A/S/D** or **Arrow Keys** | Move around |
| **]** | Cycle forward through targetable NPCs |
| **[** | Cycle backward through targetable NPCs |
| **Click** a person | Target them directly |
| **T** | Talk to targeted NPC (must be in range) |
| **L** | Exit near the entrance - returns to space directly if that's the only option, otherwise opens the Exit Menu below |
| **P** | Open the Possessions menu (credits, owned ships, loans) |
| **ESC** | Pause menu |

Station interiors include the dormitory, corridor, concourse ("default"),
spaceport, and loan office - see [ARCHITECTURE.md](ARCHITECTURE.md) for how
they're connected.

## Moon Interior (City & Wilderness)

| Control | Action |
|---------|--------|
| **W/A/S/D** or **Arrow Keys** | Move around |
| **]** / **[** | Cycle through targetable NPCs, forward/backward (City only) |
| **Click** a person | Target them directly |
| **T** | Talk to targeted NPC (must be in range) |
| **L** | Exit near the entrance - returns to space directly if that's the only option, otherwise opens the Exit Menu below |
| **P** | Open the Possessions menu (credits, owned ships, loans) |
| **ESC** | Pause menu |

## Dialogue

| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Navigate options |
| **Enter** | Choose selected option - closes the conversation, advances to another node, or (for a few NPCs) buys a ship / takes a loan |
| **ESC** | Close the conversation immediately |

Most NPCs offer a flat greeting plus a couple of closing options ("Thanks" /
"Leave"). A few (e.g. the Bartender, the spaceport's ship salesman, the loan
officer) run a real branching conversation - some options lead to another
line of dialogue instead of closing, and some perform an action (buying a
ship, taking a loan) that's shown dim with a reason instead of selectable
when you can't currently take it (not enough credits, already have a loan).
See `game/world/dialogue.py`.

## Menus

### Possessions Menu (P)
| Control | Action |
|---------|--------|
| **P** or **ESC** | Close |

Read-only: credits, owned ships, loans, the current ship's live stats
(thrust/velocity/rotation/cargo usage - reflecting installed outfits),
cargo, personal items, and installed/spare ship outfits. Opens from space,
a station interior, or a moon interior, over whichever screen it was
opened from.

### Shop Menu (T, on an NPC with a shop)
| Control | Action |
|---------|--------|
| **←/→** or **Tab** | Switch between Buy and Sell |
| **W/↑** or **S/↓** | Navigate the item list |
| **Enter** | Buy/sell one unit of the selected item |
| **ESC** | Close |

Talking to an NPC configured with a `"shop"` (see a story's `systems/*.json`)
opens this instead of a conversation. Buy lists the shop's stock, priced from
`commodities.json`/`items.json`; Sell lists whatever you're currently
carrying in that category, at a fraction of its price. A commodities shop
also shows your ship's cargo hold usage, and blocks purchases past capacity.
Personal items aren't capacity-limited. Ships and ship outfits get their own
dedicated menus rather than this one.

### Shipyard Menu (T, on an NPC with a `"shop"` of type "ships")
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Navigate ship list |
| **Enter** | Confirm purchase (opens a Yes/No confirmation) |
| **Y** / **N** or **ESC** | Confirm / cancel the pending purchase |
| **ESC** | Close (when nothing is pending confirmation) |

Shows the shop's stock ship types with a live preview and stat readout
(thrust, max velocity, rotation, cargo capacity, cost) for whichever is
selected. Replaces the old dialogue-tree ship purchase for any NPC whose
config uses a `"shop"` block instead of a `dialogue_tree` with
`buy_ship:<id>` options (the spaceport's ship salesman now works this way).

### Outfitting Menu (T, on an NPC with a `"shop"` of type "outfits")
| Control | Action |
|---------|--------|
| **←/→** | Switch between Buy and Install |
| **Mouse drag** (Install tab) | Drag a spare outfit onto a slot to equip it, or drag an installed slot back out to unequip |
| **Tab** (Install tab) | Switch keyboard focus between the slot diagram and the spare-outfits list |
| **W/↑** or **S/↓** | Navigate the focused column, or a list |
| **Enter** on an empty focused slot | Open a list of compatible spare outfits to install |
| **Enter** on an occupied focused slot | Uninstall it back to spares |
| **Enter** (Buy tab) | Buy the selected outfit |
| **ESC** | Close (cancels an open install picker first, if one is open) |

Buy adds outfits to your spares (`owned_outfits`) - they aren't equipped
until installed into a matching slot type (weapon/engine/shield/utility) on
the Install tab's diagram of your current ship. Installing/uninstalling
takes effect immediately - thrust, max velocity, rotation, and cargo
capacity all update right away, not just after a reload.

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
