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
| **T** | Cycle target mode: SHIPS (AI ships only) → LANDING SITES (station/moon only) → MISC (celestial bodies, star). Starts on LANDING SITES. |
| **Click** an object (in the world, or its blip on the minimap) | Target it directly - infers and switches target mode to match whatever was clicked |
| **Hover** a minimap blip | Show its name in a label by the cursor |
| **Mouse wheel** | Scroll the HUD pane under the cursor - the Message Log (bottom-left) or the targeting/info pane (top-right) when either has more than fits |
| **H** | Hail the targeted ship (requires a targeted AI ship - see Hailing below) |
| **Space** | Engage autopilot toward the targeted object (follows an AI ship, or approaches a landing site from any range) - the bottom status pane then shows "Approaching: `<name>`". Autopilot onto a station/moon docks automatically once it brings you to a stop in range - whichever way the autopilot decides it's arrived, no extra **L** press. |
| **L** | Land - on the targeted landing site if already in range, otherwise on whatever's nearby (never engages autopilot) |
| **M** | Open the star map |
| **J** | Jump to the selected star system (see Star Map below) |
| **P** | Open the Possessions menu (credits, owned ships, loans) |
| **N** | Open the Mission Log (see Mission Log below) |
| **C** | Show / hide the top-left Controls pane (starts hidden - just its title and this line) |
| **ESC** | Pause menu |

The top-left **Controls pane** starts collapsed to a two-liner; **C** expands
it to the full key list (and collapses it again). A long entry wraps onto a
second line rather than running off the panel. It's hidden entirely while a
menu or a conversation is open. Side HUD panes (Controls, minimap, info,
Message Log) are each capped at one fifth of the window width.

## Star Map (M)

| Control | Action |
|---------|--------|
| **Click** a system | Select it as the jump target |
| **Click + drag** empty space | Pan the map |
| **J** | Close the map and jump to the selected system |
| **M**, **ESC**, or the **Close Map** button (top-left) | Close the map (selection persists) |

The map is otherwise mouse-only. It opens centered on your current system,
with a "You
are here" tag next to it. A **Close Map** button (top-left) and the selected
system's station/moon panel (top-right) share the space view's HUD look. The selected
system is shown back in the space view as "Jump Target:" - it defaults to
(and resets to, after a jump) your current system, so it's never empty.
Pressing **J** (either on the map or back in the space view) starts the jump
if the target is a different system, or the current one while far enough
from its center (`JUMP_SELF_MIN_DISTANCE`); from too close to the center a
self-jump just flashes a brief "too close" notice instead.
Completing a jump flashes a brief "arrived at ..." toast in the space view.
Your thrusters draw as firing for the whole jump.

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
| **C** | Show / hide the top-left Controls pane |
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
title announces each new one; scroll the pane with the wheel while the
pointer is over it (the guided walkthrough has a step for this).

**Guided walkthrough:** on a fresh game you start on Alpha Station with no
ship. Sela Cordova, the concierge on the concourse, offers a tour that
walks you through the interior controls (moving, targeting, talking, the
Mission Log, Possessions, scrolling the Message Log), taking out a loan, and
buying your first ship - accept it (**T**, then "Yes, show me around") and she
trails you on foot, posting each step to the Message Log and Mission Log. It's the
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
| **C** | Show / hide the top-left Controls pane |
| **ESC** | Pause menu |

## Dialogue

The NPC conversation box is **mouse-only**, like every other modal:

| Control | Action |
|---------|--------|
| **Hover** an option | Highlights it |
| **Click** an option, or **Enter** on the highlighted one | Choose it - closes the conversation, advances to another node, or (for a few NPCs) buys a ship / takes a loan |
| **Click** the **X** (top-right of the box) | Leave the conversation |

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
| Hover / click an option, click the **X** | Same as Dialogue above, once a hail is open (mouse-only) |

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
screen on its own - a brief top-centre banner in a glass pane, the same look
as the rest of the HUD (mission toasts and the "too close to jump" warning
share that pane style and stack below it - see `draw_glow_message`), no
dialogue box, and it doesn't require a target - you still have to target and
hail them back (H) to actually have the conversation. A pilot's `one_way_hail`
has a `range` gating how close you must be; the tutorial's Kade Marsh uses a
very large range so his opening hail lands the moment you launch. The banner
only announces the
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
which way there's more). A new message snaps it back to the top and blinks
a **red dot** in the pane's top-right corner **three times**, with the UI
**ping** sounding once per blink, then goes quiet and dark
(`MESSAGE_ALERT_BLINKS` / `message_alert_state` in `ui_theme.py`). The
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
| **[** / **]**, **Left** / **Right**, or **Click** a tab | Switch between the Active and Completed tabs |
| **Mouse wheel**, **Up** / **Down**, **PageUp** / **PageDown**, **Home** / **End** | Scroll a report longer than the panel |

Read-only, opened from space, a station interior, or a moon interior, over
whichever screen it was opened from (same shape as the Possessions menu).
Two tabs: **Active** and **Completed**. Each mission's stages are **numbered**
(`1.`, `2.`, ...) and marked - an active mission shows the stages so far
completed (`[x]`) and its current stage (`->`), with stages you haven't
reached yet kept hidden until you unlock them; a completed mission shows
every stage done. A report taller than the fixed panel scrolls (blue
`^ more` / `v more` hints show when there's more). Opening the log also flips
the `viewed_mission_log` gameplay-event flag, so a mission stage can require
the player to actually check it (see `first_flight`).

Starting a mission, completing a stage, and finishing a mission each flash a
brief center-screen toast in the Space View (see `SpaceScreen._show_toast`) -
a stage-complete toast reads `Step N/M - see Mission Log (N)`. A story opts a new pilot into a mission automatically -
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
`person.escort_flag`/`OrbitPlayerRoutine`. In `first_flight`, Kade only
*starts* escorting (falls into orbit) once you close the "give me a second to
pull alongside" line - not the moment the mission begins.

`first_flight`'s stages: SHIPS target mode → target + hail Kade → accept his
help → **turn both ways** (left *and* right, `turned_both_ways`) → thrust →
brake → jump home → autopilot in and land. (Sela's station tour already
covers the Mission Log, so Kade no longer has a stage for it.)

## Menus

**Every menu and dialog is mouse-driven.** Actions are `draw_button` widgets
inside the panel - hover highlights, left-click presses. The keyboard does
**nothing** in a menu except: type into a text field (naming a pilot or a
new save), and **Enter**, which presses whichever button is currently
highlighted (or trades/confirms the selected grid item) - a shortcut for
confirming a choice already made with the mouse. Arrows, Tab, and letter
hotkeys do nothing. There is no dim hint line under the buttons any more - a
menu is meant to
be self-explanatory from its buttons and labels. Every menu has a visible
**Close** / **Cancel** / **Resume** / **Back** button. The exception to
"keyboard does nothing" is the four modals opened by a single key - the
**Pause menu** (ESC), the **Star Map** (M), **Possessions** (P), and the
**Mission Log** (N): each also closes on the key that opened it, so all four
close on **ESC** (the pause menu resumes; the overlays close). Handled in
`main.py`'s state machine (`_pressed_any`), not the menu classes. A
save/load sub-dialog stacked on the pause menu swallows ESC until it's
closed with its own button. No other modal has
ESC-to-close. No modal uses the top-left Controls pane (that belongs to the
space view and interiors); while a modal is open the base screen's Controls
pane and bottom status prompt are hidden. A four-button bar (the Save menu)
shrinks its buttons to stay inside the panel. Long reports and lists scroll
with the **mouse wheel** (or by clicking the `^ more` / `v more`
indicators).

The keys **P** / **N** / **M** / **L** *open* menus from the space
view or an interior (they're HUD controls, listed above). **P**, **N**, and
**M** also *close* the overlay they opened (as does **ESC**); once any other
menu is up, all four keys do nothing.

Two kinds (see DESIGN_PATTERNS.md's "Menu vs. Dialog"):

- a **menu** you dwell in and leave with its Close/Resume button -
  Possessions, Missions, Shop, Shipyard, Outfitting, Star Map, Save/Load,
  Pause, the main and story menus.
- a **dialog** shown *over* another modal that closes the moment you click
  one of its buttons - Yes/No confirmations, the pilot-name entry, the
  "where to?" and landing-spot pickers.

### Possessions Menu (open with P)
Read-only: credits, owned ships, loans, the current ship's live stats
(thrust/velocity/rotation/cargo usage - reflecting installed outfits),
cargo, personal items, and installed/spare ship outfits. Two columns; wheel
to scroll if it overflows. **P**, **ESC**, or the **Close** button
(top-right) closes it.

### Mission Log (open with N)
Two tabs - **Active** and **Completed** - clicked to switch. Each mission's
stages are **numbered** and marked `[x]` done / `->` current; unreached
stages stay hidden. Wheel (or click `^ more` / `v more`) to scroll. **N**,
**ESC**, or the **Close** button (top-right) closes it.

### Shop Menu (T, on an NPC with a shop)
| Control | Action |
|---------|--------|
| **Click** a Buy / Sell tab label | Switch tab |
| **Click** an item | Select it (updates the readout) |
| **Buy** / **Sell** button, **double-click** an item, or **Enter** | Buy/sell one unit of the selected item |
| **Mouse wheel** | Scroll the item grid |
| **Close** button (top-left) | Close |

Talking to an NPC configured with a `"shop"` (see a story's `systems/*.json`)
opens this instead of a conversation. Buy lists the shop's stock, priced from
`commodities.json`/`items.json`; Sell lists whatever you're currently
carrying in that category, at a fraction of its price. Both are a grid of
icons with the item's name and price (Buy) or quantity held and sell price
(Sell). A single click only selects - the green **Buy**/**Sell** button (or a
double-click) is what actually trades, so a stray click can't buy. A
commodities shop shows your ship's cargo hold usage and blocks purchases past
capacity; personal items aren't capacity-limited. A successful buy shows a
brief fading "Bought 1 `<item>`" confirmation. Ships and ship outfits get
their own dedicated menus.

### Shipyard Menu (T, on an NPC with a `"shop"` of type "ships")
| Control | Action |
|---------|--------|
| **Click** a ship | Select it (updates the live preview + stat readout) |
| **Buy** button, **double-click** a ship, or **Enter** | Open a Yes/No purchase confirmation |
| **Mouse wheel** | Scroll the ship grid |
| **Click** a **Yes** / **No** button | Confirm / cancel the pending purchase |
| **Close** button (top-left) | Close (when nothing is pending confirmation) |

Shows the shop's stock as a grid - each cell a static silhouette, name, cost,
and an "(own N)" note if you already have one. The selected cell also gets a
bigger live preview with a full stat readout. Selecting a ship never checks
affordability; only the **Buy** button / double-click does, and it opens a
Yes/No `ConfirmDialog` over the menu. A confirmed purchase shows a brief
fading "Bought 1 `<ship>`" confirmation.

### Outfitting Menu (T, on an NPC with a `"shop"` of type "outfits")
| Control | Action |
|---------|--------|
| **Click** a Buy / Install tab label | Switch tab |
| **Click** an outfit (Buy tab) | Select it |
| **Buy** button, **double-click** an outfit, or **Enter** (Buy tab) | Buy the selected outfit |
| **Mouse wheel** | Scroll the outfit grid |
| **Drag** a spare outfit onto a slot (Install tab) | Equip it |
| **Drag** an installed slot out to empty space (Install tab) | Unequip it |
| **Click** an empty slot (Install tab) | Open the compatible-spares picker |
| **Double-click** an occupied slot (Install tab) | Uninstall it back to spares |
| **Click** an outfit in the picker | Install it (click **Cancel** / off a row to dismiss) |
| **Close** button (top-left) | Close (dismisses an open picker first) |

Buy shows the shop's stock as a grid of icons; each cell shows how many you
own, its slot type, and whether your ship can fit one. Buying adds an outfit
to your spares (`owned_outfits`) - not equipped until installed on the
Install tab, where installing/uninstalling takes effect immediately (thrust,
velocity, rotation, cargo all update at once).

### Main Menu / Story Selector
Each row is a button (with its story blurb under it). The Story Selector adds
a **Back** button that returns to the Main Menu. Click a row to pick it.

### Save / Load Menus
| Control | Action |
|---------|--------|
| **Click** a save | Select it in the list |
| **Load** / **Overwrite** button, or **double-click** a save | Load / overwrite the selected save |
| **New Save** button | Switch to typing a new save name (save mode) |
| **Delete** button | Delete the selected save (opens a Yes/No confirm) |
| **Mouse wheel** | Scroll the save list |
| **Cancel** button | Close |
| *(name-entry sub-mode)* type / Backspace | Edit the save name - the only keyboard use in any menu |

Load and Save are one widget (`SaveBrowser`). Save names are shown **without**
the on-disk `save_` prefix or `.json` suffix. When typing a new name the
field is pre-filled with `<pilot> - <timestamp>` (so **Save** works with no
typing); the first keystroke clears it so you can type your own.

### Pause Menu
A column of buttons - **Resume** / **Save Game** / **Load Game** / **Quit to
Menu**. Click one. **Load Game** opens the same `SaveBrowser`; its **Cancel**
returns to the pause menu, and loading replaces the running game. (ESC opens
the pause menu from gameplay, but does not close it - use **Resume**.)

### Exit Menu (interior, when the entrance leads to more than one place)
| Control | Action |
|---------|--------|
| **Click** a destination button | Go there (a connected location, or "Return to Ship") |
| **Cancel** button | Stay put |

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
The UI **ping** plays on menu button presses, and three times (once per
blink of the Message Log's unread light) on an incoming message; **confirm**
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
- **ESC pauses** the game from the space view and interiors, and **ESC
  again resumes** from the pause menu; in the Star Map, Possessions, and
  Mission Log overlays it closes the overlay. Every other menu/dialog has
  no ESC binding (a save/load sub-dialog on top of the pause menu also
  swallows ESC - close it with its own button first)
- **Ctrl + M mutes/unmutes all audio** (handled globally in `main.py`, like the debug toggle)
- Every menu and dialog shows its actions as **buttons in its own panel**
  (click, or Tab/arrow + Enter); the top-left Controls pane is the space
  view's and interiors' only (see the Menus section)
