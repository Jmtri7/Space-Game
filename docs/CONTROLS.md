# Space Game Controls

All interactive controls and their bindings. **Update this document when adding or changing any control**.

## Space View (Default)

| Control | Action |
|---------|--------|
| **W** or **↑** | Thrust forward |
| **A** or **←** | Rotate left |
| **D** or **→** | Rotate right |
| **S** or **↓** | Turn to face opposite velocity (reverse heading) |
| **Q** / **E** | Rotate the view left / right (camera only - does not touch ship heading or physics; held, like turning). Held view rotation, reset to north-up whenever you land. Not saved. |
| **]** | Cycle forward through targetable objects in the current target mode |
| **[** | Cycle backward through targetable objects in the current target mode |
| **T** | Cycle target mode: SHIPS (AI ships only) → LANDABLES (station/moon only) → MISC (celestial bodies, star). Starts on LANDABLES. |
| **Click** an object | Target it directly - infers and switches target mode to match whatever was clicked |
| **Mouse wheel** | Scroll the HUD pane under the cursor - the Message Log (bottom-left) or the targeting/info pane (top-right) when either has more than fits |
| **H** | Hail the targeted ship (requires a targeted AI ship - see Hailing below) |
| **Space** | Engage autopilot toward the targeted object (follows an AI ship, or approaches a landable from any range) - the bottom status pane then shows "Approaching: `<name>`". Autopilot onto a station/moon now docks automatically on arrival (no extra **L** press). |
| **L** | Land - on the targeted landable if already in range, otherwise on whatever's nearby (never engages autopilot) |
| **M** | Open the star map |
| **J** | Jump to the selected star system (see Star Map below) |
| **P** | Open the Possessions menu (credits, owned ships, loans) |
| **N** | Open the Mission Log (see Mission Log below) |
| **ESC** | Pause menu |

## Star Map (M)

| Control | Action |
|---------|--------|
| **Click** a system | Select it as the jump target |
| **Click + drag** empty space | Pan the map |
| **W/A/S/D** or **Arrow Keys** | Scroll the map |
| **M** or **ESC** | Close the map (selection persists) |

Opens centered on your current system, with a "You are here" tag next to it.
A **Close Map** button (top-left), a control hint (bottom), and the selected
system's station/moon panel (top-right) share the space view's HUD look. The selected
system is shown back in the space view as "Jump Target:" - it defaults to
(and resets to, after a jump) your current system, so it's never empty.
Pressing **J** starts the jump if the target is a different system, or the
current one while far enough from its center (`JUMP_SELF_MIN_DISTANCE`).
Completing a jump flashes a brief "arrived at ..." toast in the space view.

## Station Interior

| Control | Action |
|---------|--------|
| **W/A/S/D** or **Arrow Keys** | Move around |
| **]** | Cycle forward through targetable NPCs (for viewing info at a distance - see below) |
| **[** | Cycle backward through targetable NPCs |
| **Click** a person | Target them directly |
| **T** | Talk to the closest NPC/pilot in range - always the nearest one, regardless of any manually cycled/clicked target |
| **L** | Use the portal you're standing on - boards your ship (or opens the Exit Menu below if the portal leads more than one place, or shows why you can't leave yet) |
| **P** | Open the Possessions menu (credits, owned ships, loans) |
| **N** | Open the Mission Log (see Mission Log below) |
| **Mouse wheel** | Scroll the Message Log (bottom-left) when it has more than fits |
| **ESC** | Pause menu |

A default-story station is one connected interior with a single ship portal
in the dock area - walk to the loan officer and ship dealer, then **L** at
the dock to board. Moons still have separate `city` and `wilderness` areas
joined by a portal. See [ARCHITECTURE.md](ARCHITECTURE.md).

The **Message Log** pane (bottom-left, same one as the Space View) shows up
in interiors too - an NPC can drop a line into it unprompted when you get
close (a config `"ambient"` message), and a mission guide's step-by-step
instructions arrive there as you go. A short banner under the location
title announces each new one; scroll the pane with the wheel.

**Guided walkthrough:** on a fresh game you start on Alpha Station with no
ship. Sela Cordova, the concierge on the concourse, offers a tour that
walks you through the interior controls, taking out a loan, and buying your
first ship - accept it (**T**, then "Yes, show me around") and she trails
you on foot, posting each step to the Message Log and Mission Log. It's the
on-foot counterpart to Kade Marsh's flying lesson once you launch.

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
| **N** | Open the Mission Log (see Mission Log below) |
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

Some options are also conditional - they don't just show dim, they don't
appear in the list *at all* until a story flag is set (`requires_flag`), or
disappear once one is (`requires_not_flag`), so a conversation can offer
something new later without ever hinting at it before then. A whole
conversation can also open differently depending on a flag
(`conditional_roots`) - e.g. the bartender greets you differently after
you've bought him a round once. See `game/world/dialogue.py`.

## Hailing

| Control | Action |
|---------|--------|
| **H** (Space View) | Hail the currently targeted ship |
| **W/↑** or **S/↓**, **Enter**, **ESC** | Same as Dialogue above, once a hail is open |

Hailing reuses the exact same conversation UI as talking to someone
face-to-face, but requires a targeted AI ship first (SHIPS target mode -
see the Space View table above) - there's no hailing without a target.
While a hail conversation is open the whole simulation is paused (your
ship, AI traffic, autopilot, mission timers, cached interiors) - it lifts
the moment the conversation closes, the same as the Pause Menu or the
jump map.
Whenever a ship is targeted, the bottom status pane shows a
"Press H to Hail `<name>`" prompt (it is not in the top-left Controls
pane, since it only applies with a target selected).
A pilot answers differently depending on where they actually are: their
**hail** conversation (this section) is a separate, ship-context
conversation from the one they'd give you face-to-face if you boarded
their ship and talked to them in person (e.g. a docked freighter pilot
walking around the station) - a pilot can be configured with entirely
different dialogue for each. Hailing a pilot who's currently ashore
(docked and walking around a station/moon interior, not actually in their
ship right now) doesn't open a conversation at all - just a brief
"no response" message, since there's no one aboard to answer.

Some pilots also hail *you* first: a one-way transmission that pops up on
screen on its own once you fly close enough - a brief top-centre banner in
a glass pane, the same look as the rest of the HUD (mission toasts and the
"too close to jump" warning share that pane style and stack below it - see
`draw_glow_message`), no dialogue box, and it doesn't require a target - you still have to target and hail them back
(H) to actually have the conversation. The banner only announces the
transmission ("Incoming transmission - `<sender>` (see Messages)") - the
message body itself is in the Message Log pane (below), not the banner.
Each pilot's one-way hail (if they have one) only ever fires once. See
`pilots.json`'s `"hail_dialogue_tree"`/`"one_way_hail"` and
`game/world/character.py`'s `Character.for_ai_pilot`.

That one-way banner is easy to miss if you're looking elsewhere when it
fires, and doesn't carry the message text anyway, so every message is
recorded in the **Message Log** pane, bottom-left of the Space View -
every one-way message ever received, newest at the top, as
"`Sender: message`". It only appears once at least one message has arrived
(nothing to show before then) and stays up permanently (not a timer). The
pane has a fixed maximum height (`MESSAGE_LOG_VISIBLE_LINES`); once the
backlog is longer than that, scroll it with the **mouse wheel** while the
pointer is over it (blue `^ newer (scroll)` / `v older (scroll)` hints show
which way there's more). A new message snaps it back to the top and lights
a **blinking red dot** in the pane's top-right corner for ~10 seconds
(`MESSAGE_ALERT_FRAMES`) so an arrival is hard to miss. The
top-right targeting/info pane scrolls the same way when a target's readout
(e.g. a station's full location list) is longer than
`INFO_PANEL_VISIBLE_LINES`. See `Possessions.message_log`/`add_message()`
and `ui_theme.draw_message_log()` / `draw_info_panel()`.

Space View also shows a persistent hint in the bottom status pane once
you've drifted far enough from the system's center that jumping back is
possible ("Drifting far from the system - open the Star Map (M) and jump
(J) back") - the same distance a self-jump back to this system already
requires (`JUMP_SELF_MIN_DISTANCE`), so the hint and the mechanic it
points at always agree.

## Mission Log (N)

| Control | Action |
|---------|--------|
| **N**, **ESC**, or the **Close** button (top-right) | Close |

Read-only, opened from space, a station interior, or a moon interior, over
whichever screen it was opened from (same shape as the Possessions menu).
Lists every mission that's ever been started: an active mission shows its
stages so far completed (`[x]`) and its current stage (`->`) - stages you
haven't reached yet stay hidden until you unlock them; a finished mission
shows every stage done, marked "(Complete)". Opening the log also flips the
`viewed_mission_log` gameplay-event flag, so a mission stage can require the
player to actually check it (see `first_flight`).

Starting a mission, completing a stage, and finishing a mission each flash a
brief center-screen toast in the Space View (see `SpaceScreen._show_toast`). A story opts a new pilot into a mission automatically -
by default the first time they buy a ship, or at new-game start if
`story.json`'s `"starting_mission_trigger"` is `"new_game"` (`"starting_mission"` names it). Either way it holds until the player
next launches into space (so the opening toast and hail land in the
cockpit, not while they're still in the station) - see
`config/stories/default/missions.json`'s `"first_flight"` for a worked
example, which an NPC hailing you (Kade Marsh - see Hailing above) kicks
off once you're flying. See `game/world/mission.py` for how a stage's `"complete_flag"` ties
into the same `Possessions.flags` a conversation option can set (see
Dialogue above) - a mission stage can be completed by a dialogue choice, a
gameplay event (targeting/turning/thrusting/braking/landing/jumping/buying
a ship/taking a loan - see ARCHITECTURE.md for the full gameplay-event flag
list), or anything else that sets a flag. A mission can also let the player decline
it partway through (Kade offers to walk you through it - saying no ends
the mission there instead of completing it), and can have an NPC pilot
escort you for its duration - circling your ship at a fixed radius -
returning to their normal routine once it ends - see ARCHITECTURE.md's
`person.escort_flag`/`OrbitPlayerRoutine`.

## Menus

Every full-screen modal shows its actions as **buttons inside its own
panel** - click them, or Tab / arrow to move button focus and Enter to
press. No modal uses the top-left Controls pane (that belongs to the space
view and interiors); a one-line dim hint under the buttons covers anything
that isn't a button (browsing a grid, dragging an outfit, panning the map).
While a modal is open the base screen's Controls pane and bottom status
prompt ("Press T to talk to X") are hidden.

Two kinds (see DESIGN_PATTERNS.md's "Menu vs. Dialog"):

- a **menu** you navigate and leave explicitly - Possessions, Missions,
  Shop, Shipyard, Outfitting, Star Map, Save/Load, Pause, the main and story
  menus. Acting inside it doesn't close it; a Close/Resume button or ESC
  does.
- a **dialog** shown *over* another modal that closes the moment you pick a
  button - Yes/No confirmations, the pilot-name entry, the "where to?" and
  landing-spot pickers.

### Possessions Menu (P)
| Control | Action |
|---------|--------|
| **P**, **ESC**, or the **Close** button (top-right) | Close |

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
| **ESC** or the **Close** button (top-left) | Close |

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
| **ESC** or the **Close** button (top-left) | Close (when nothing is pending confirmation) |

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
Enter does that. The confirmation is a dialog (Left/Right + Enter, Y/N/ESC
shortcuts, or click a button) shown over the menu with its own Yes/No
buttons, until you resolve it. A confirmed purchase shows a brief fading
"Bought 1 `<ship>`" confirmation.
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
| **ESC** or the **Close** button (top-left) | Close (cancels an open install picker first, if one is open) |

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
pressing Enter on an empty slot), the hint line switches to just the
picker's own controls (Up/Down, Enter, ESC) and the Close button is
inactive - the Buy/Install tab's normal controls don't apply until the
picker is dismissed.

Install shows a diagram of the current ship's slots - an occupied slot draws
that outfit's own icon inside it (plus its name below) - next to a grid of
your spare (uninstalled) outfits, each shown as an icon with its name/slot
type. Installing/uninstalling takes effect immediately - thrust, max
velocity, rotation, and cargo capacity all update right away, not just after
a reload.

### Main Menu / Story Selector
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Move between the option buttons |
| **Enter** or **Click** | Select (NEW / LOAD / QUIT, or a story) |
| **ESC** | (Story Selector only) back to Main Menu |

Both are the same widget (`BackdropMenu`) - each row is a button with the
story's blurb under it; a hint line sits at the panel's bottom.

### Save/Load Menus
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** or **Click** a save | Select a save in the list |
| **Enter**, or the **Load** / **Overwrite** button | Load / overwrite the selected save |
| **N** or the **New Save** button | Switch to typing a new save name (save mode) |
| **D** or the **Delete** button | Delete the selected save |
| **ESC** or the **Cancel** button | Close |

Load and Save are one widget (`SaveBrowser`, `mode="load"` / `"save"`); the
verbs are buttons along the panel bottom. Deleting a save opens a Yes/No
confirmation dialog over it.

### Pause Menu
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Move between the buttons |
| **Enter** or **Click** | Resume / Save Game / Load Game / Quit to Menu |
| **ESC** | Resume game |

**Load Game** opens the same `SaveBrowser` as the Main Menu; cancelling it
(ESC) returns to the pause menu, and loading a save replaces the running
game.

### Exit Menu (interior location, when the entrance leads to more than one place)
| Control | Action |
|---------|--------|
| **W/↑** or **S/↓** | Move between destination buttons |
| **Enter** or **Click** | Go to that destination (a connected location, or "Return to Ship") |
| **ESC** | Cancel, stay put |

A dialog (`ChoiceDialog`) - each destination is a button in its own panel,
unavailable ones dimmed. Shown instead of leaving immediately when a
location's config lists `connected_locations` (other interiors reachable on
foot from this one, e.g. Moon City ↔ Wilderness) and/or sets
`return_to_ship`. AI pilots
(see `DockRoutine`) pick a destination from the same option list
automatically, based on their role, instead of getting this menu.

## Audio

| Control | Action |
|---------|--------|
| **Ctrl + M** | Mute / unmute all audio (SFX + background music) — works on every screen |

All sound is synthesized at runtime (no asset files) — see [SOUND.md](SOUND.md).
The UI **ping** plays on menu button presses and incoming messages; **confirm**
on engaging autopilot (Space); **blip** on cycling/clicking a target (`[` `]`
`T`, click) - mixed deliberately quiet since it fires on every target
keypress. Two ambient background tracks (menu / in-game) fade in and cross-
fade as you move between menus and play.

## Debug Controls

| Control | Action |
|---------|--------|
| **`** (backtick) | Toggle debug mode (entity position markers + the perf panel) |

Debug mode displays green X marks at the world coordinates of all entities:
- Space view: player ship, station, moon, AI ship
- Interiors: player, NPCs

Use this to diagnose coordinate and positioning issues.

It also draws the **performance panel** in the bottom-left corner: FPS vs. the
16.67 ms frame budget, per-phase timing for the main loop (input / sim / render
/ present), catch-up sim steps per frame, and the slowest tracked sub-sections
("hot spans" - e.g. `render.starfield`, `sim.ai_ships`). All figures are rolling
averages and peaks over the last ~2 seconds. See
[UI_FLOW.md](UI_FLOW.md#main-loop-fixed-timestep-three-phases) and
`game/perf_metrics.py`.

## Notes

- **Arrow keys and WASD are interchangeable** for movement and navigation
- **ESC always pauses** the game (from any screen)
- **Ctrl + M mutes/unmutes all audio** (handled globally in `main.py`, like the debug toggle)
- Every menu and dialog shows its actions as **buttons in its own panel**
  (click, or Tab/arrow + Enter); the top-left Controls pane is the space
  view's and interiors' only (see the Menus section)
