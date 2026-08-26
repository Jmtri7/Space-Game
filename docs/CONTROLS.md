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
| **]** | Cycle forward through targetable NPCs (for viewing info at a distance - see below) |
| **[** | Cycle backward through targetable NPCs |
| **Click** a person | Target them directly |
| **T** | Talk to the closest NPC/pilot in range - always the nearest one, regardless of any manually cycled/clicked target |
| **L** | Exit near the entrance - returns to space directly if that's the only option, otherwise opens the Exit Menu below |
| **P** | Open the Possessions menu (credits, owned ships, loans) |
| **ESC** | Pause menu |

Station interiors include the dormitory, corridor, concourse ("default"),
spaceport, and loan office - see [ARCHITECTURE.md](ARCHITECTURE.md) for how
they're connected.

### NPC Targeting vs. Talking

Walking within range of someone no longer targets them - it just makes them
talkable. Whoever's currently closest to the player (within `talk_range`)
gets their name and role floated above their head, and the bottom status
pane shows "Press T to talk to `<name>`"; that prompt disappears entirely
when no one's close enough (there's no "approach target to talk" message
anymore). **T always talks to that closest person.**

`]`/`[`/click-targeting (see the table above) is a separate, purely
informational selection - it highlights whoever you've picked with bracket
corners and shows their name/role in the top-right info panel, even from
across the room, but has no effect on what T does. It's for looking someone
up at a distance, not for choosing who to talk to.

## Moon Interior (City & Wilderness)

| Control | Action |
|---------|--------|
| **W/A/S/D** or **Arrow Keys** | Move around |
| **]** / **[** | Cycle through targetable NPCs, forward/backward (City only, for viewing info at a distance - see above) |
| **Click** a person | Target them directly |
| **T** | Talk to the closest NPC/pilot in range - see "NPC Targeting vs. Talking" above |
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
| **Tab** or **Click** a tab | Switch between Buy and Sell |
| **Arrow keys**, **W/S**, or **Click** an item | Browse the item grid (click just selects, same as browsing) |
| **Enter** | Buy/sell one unit of the selected item |
| **ESC** | Close |

Talking to an NPC configured with a `"shop"` (see a story's `systems/*.json`)
opens this instead of a conversation. Buy lists the shop's stock, priced from
`commodities.json`/`items.json`; Sell lists whatever you're currently
carrying in that category, at a fraction of its price. Both are shown as a
grid of icons with the item's name and its price (Buy) or quantity held and
sell price (Sell) - see `icon_shape`/`icon_color` in those two config files;
an item with neither just gets a plain default crate icon. Browsing the grid
(by arrow key or by clicking an item) is never blocked by affordability, and
never transacts by itself - only Enter (the actual purchase) does. A
commodities shop also shows your ship's cargo hold usage, and blocks
purchases past capacity. Personal items aren't capacity-limited. A successful
buy shows a brief fading "Bought 1 `<item>`" pill-shaped confirmation near
the bottom of the panel. Ships and ship outfits get their own dedicated
menus rather than this one.

### Shipyard Menu (T, on an NPC with a `"shop"` of type "ships")
| Control | Action |
|---------|--------|
| **Arrow keys**, **W/S**, or **Click** a ship | Browse the ship grid (click just selects/previews) |
| **Enter** | Open a Yes/No purchase confirmation for the selected ship |
| **Y** / **N** or **ESC** | Confirm / cancel the pending purchase |
| **ESC** | Close (when nothing is pending confirmation) |

Shows the shop's stock ship types as a grid - each cell a static silhouette,
name, cost, and (if you already own one) an "(own N)" note. Whichever cell is
selected also gets a bigger live preview off to the side, with a full stat
readout (how many you already own, thrust, max velocity, rotation, cargo
capacity, an "Approximate Size" bucketed from the ship's `graphics.json`
`size`, and cost). Unlike the grid's static icons, that preview slowly
rotates and cycles its thrusters on/off, and draws window portholes when the
ship type's graphics define any (see `windows` in `graphics.json`'s ship
entries). Browsing the grid (arrow keys or clicking a ship) is never blocked
by affordability and never opens the purchase confirmation by itself - only
Enter does that; the confirmation is still Yes/No/ESC only, no click. While
it's open, this menu's own "Arrows/Click: browse..." help line is hidden -
only the confirmation's own Y/N/ESC help applies until you resolve it. A
confirmed purchase shows a brief fading "Bought 1 `<ship>`" confirmation.
Replaces the old dialogue-tree ship purchase for any NPC whose config uses a
`"shop"` block instead of a `dialogue_tree` with `buy_ship:<id>` options (the
spaceport's ship salesman now works this way).

### Outfitting Menu (T, on an NPC with a `"shop"` of type "outfits")
| Control | Action |
|---------|--------|
| **Tab** or **Click** a tab | Switch between Buy and Install |
| **Arrow keys**, **W/S**, or **Click** an outfit (Buy tab) | Browse the outfit grid (click just selects) |
| **Enter** (Buy tab) | Buy the selected outfit |
| **Mouse drag** (Install tab) | Drag a spare outfit onto a slot to equip it, or drag an installed slot back out to unequip |
| **Click** a slot or spare outfit (Install tab, no drag) | Move keyboard focus there without installing/uninstalling |
| **Left/Right** (Install tab) | Switch keyboard focus between the slot diagram and the spare-outfits grid |
| **W/↑** or **S/↓** (Install tab) | Navigate the focused column |
| **Enter** on an empty focused slot | Open a list of compatible spare outfits to install |
| **Enter** on an occupied focused slot | Uninstall it back to spares |
| **ESC** | Close (cancels an open install picker first, if one is open) |

Buy shows the shop's stock as a grid of icons - a weapon/engine/shield/
utility outfit gets a default icon for its slot type unless its own config
sets an `icon_shape`/`icon_color` (see `SLOT_ICON_SHAPES` in
`game/ui/outfitting_menu.py`). Each cell also shows how many you already own
(spares plus whatever's currently installed), which slot type it uses, and
whether your current ship can actually fit one - "Fits your ship", "Equipped"
(you already have one mounted), "Doesn't fit your ship" (no slot of that
type), or "No ship yet" if you don't own a ship at all. Browsing (arrow keys
or clicking an outfit) is never blocked by affordability and never buys by
itself; only Enter does. Buying adds outfits to your spares
(`owned_outfits`) - they aren't equipped until installed into a matching
slot type on the Install tab. A successful buy shows a brief fading
"Bought 1 `<outfit>`" confirmation.

While the Install tab's compatible-outfit picker popup is open (after
pressing Enter on an empty slot), this menu's help text switches to just the
picker's own controls (Up/Down, Enter, ESC) - the Buy/Install tab's normal
controls don't apply until the picker is dismissed.

Install shows a diagram of the current ship's slots - an occupied slot draws
that outfit's own icon inside it (plus its name below) - next to a grid of
your spare (uninstalled) outfits, each shown as an icon with its name/slot
type. Installing/uninstalling takes effect immediately - thrust, max
velocity, rotation, and cargo capacity all update right away, not just after
a reload.

### Main Menu
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Navigate options |
| **Enter** | Select option |
| **Click** an option | Select it |

### Story Selector
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Select a story |
| **Enter** | Play the selected story |
| **ESC** | Cancel, back to Main Menu |

Both the Main Menu and Story Selector show their controls in the same
top-left Controls pane every other screen uses (see `draw_controls_pane` in
`game/ui/ui_theme.py`) rather than a single line of help text at the bottom.

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
