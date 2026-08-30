# Backlog

Known bugs and planned features that aren't fixed/implemented yet. This is a running
list, not a spec — add to it whenever you notice something, and check an item off (or
delete it) once it's actually fixed/shipped. If you're an agent fixing one of these,
mention it in the commit message so this file and the commit history stay in sync.

Top-level split is **Bugs vs. Features**. Within each, items are grouped by the type of
gameplay they belong to, so related work is easy to find together. A gameplay category
only appears under a section if it currently has items there.

# Bugs

## Controls & UI

- [ ] Say "messages", not "comms", everywhere in the UI.
- [ ] Button overlapping in the shipyard menu.
- [ ] Shipyard ship-description text runs off the edge of the menu panel.

## Navigation & Flight

- [ ] Jumping to system center — the mechanic and its tutorial both need work.
- [ ] Jump-target label wraps excessively.

## Missions, Dialogue & NPCs

- [ ] No mission-complete message when leaving the mission area — a mission that
      completes on leaving/returning surfaces no confirmation toast.
- [ ] Petra Voss should be positioned at the loan office desk.

## Economy & Trading

- [ ] You can spend your loan on a laser cannon and then be stuck (no way to
      recover/pay it back).
- [ ] Loan amount is too big — fine for testing now, but needs tuning down.

## Stations, Interiors & World Building

- [ ] Characters added to a story don't show up in old saves.
- [ ] The concierge desk should sit right in front of the player on entry.

## Graphics & Rendering

- [ ] Visiting NPCs (e.g. NPCs that walk into a station interior) render with the
      player's own model instead of a distinct sprite.
- [ ] Pipe fence needs an outline.
- [ ] Faint shimmer of the world when panning (running left/right in an
      interior, flying in space): the camera scrolls a non-integer number of
      screen pixels per frame and `to_screen`'s pixel rounding renders it as
      an irregular 3-3-3-4 cadence. Subtle at 60 FPS vsync'd; frame *pacing*
      (the bigger stutter) is fixed. Real fix needs sub-pixel rendering. See
      [PHYSICS.md](PHYSICS.md) "Frame Timing & Smooth Motion" for the
      writeup and options.

# Features

## Controls & UI

- [ ] Quick save.
- [ ] Make the player icon on the minimap more obvious than the others.
- [ ] Some selling-menu controls (like the ship menu) don't mention that you can use
      the mouse.
- [ ] Consider mouse-based movement/control support.
- [ ] Show the active mission on the in-world HUD.
- [ ] Controls should be usable without moving the hand off WASD / arrow keys —
      avoid bindings that force the player to reposition their hand.
- [ ] Allow arrow keys to change meny selections.
- [ ] `ESC` should close the NPC conversation box and the shop menus (deliberate
      change to the mouse-only-modal / no-ESC-to-close rule in CLAUDE.md).

## Navigation & Flight

- [ ] Add a border to the edge of the star map where no systems can be.
- [ ] Star map zoom.
- [ ] Correct Kade Marshes grammar about "Fly it to yourself".

## Missions, Dialogue & NPCs

- [ ] Tutorial for turning the camera — phrasing like "Hold S until your ship
      stops turning".
- [ ] Tutorial for jumping to another system (see also: jumping to system center
      needs work, under Bugs → Navigation & Flight).
- [ ] Relationships.
- [ ] More roles.
- [ ] No useless NPCs — each one should reveal something about the game's features or
      story.
- [ ] NPCs stop wandering if the player moves close to or targets them.
- [ ] Derelict ships / distress beacons — a drifting AI ship with no pilot response
      you can board, loot, or tow; combines the existing AI ship, interior, and
      item-pickup ideas into one encounter type.
- [ ] Escort/wingman contracts — hire or be hired to fly alongside another AI ship
      to a destination; reuses existing autopilot and multi-AI-ship work.

## Combat, Crime & Factions

- [ ] Factions — combined with crime/war, would turn the sandbox into a living
      political map; cultures/roles already exist as a foundation.
- [ ] Combat.
- [ ] Crime — see factions.
- [ ] War — see factions.
- [ ] Bounty hunting board — a station terminal listing wanted ships/NPCs with a
      reward, feeding off factions/crime once those exist.
- [ ] AI ships flying in formations.

## Ships & Customization

- [ ] Ship customization (paint/decals/name) — cosmetic, cheap, but makes "your
      ship" feel more personal. (Owning multiple ships and switching between
      them at the ship salesman's "Your Ships" tab now works — story `1.12.0`;
      per-ship stored outfit loadouts are still a gap, see SAVE_SYSTEM.md.)
- [ ] Make all outfits usable (not just cosmetic/inert).
- [ ] Outfitter should explain how to install outfits and what each outfit does.
- [ ] Mounted outfit graphics (visually show equipped outfits on the ship).
- [ ] Graphic for ship thrusters so they're visible when turned off.

## Economy & Trading

- [ ] Sell all button.
- [ ] Picking up and dropping items.
- [ ] Asteroid mining — pairs naturally with the existing asteroid fields and
      "different asteroid types" idea; gives the economy a real gameplay loop instead
      of just trading.
- [ ] More ways to make money.
- [ ] Ilsa Farrow should sell things — give her a shop/merchant role.
- [ ] Make some commodities usable for various purposes (not just tradeable).
- [ ] Distinct buy and sell multipliers per good, dependent on various factors
      (supply/demand, faction, location, etc.).
- [ ] Black-market smuggling runs — contraband cargo that's profitable but triggers
      scans/hails from patrol ships if caught; a light crime mechanic that doesn't
      need the full Crime system first.

## Stations, Interiors & World Building

- [ ] Enterable buildings in cities.
- [~] More interior decorations, like roads. (Decoration system done -
      per-interior `decorations` floor/wall decals + per-culture packs; moon
      cities have road decals. Room for more content.)
- [ ] More systems with unique concepts.
- [ ] Add more systems (more of them overall, beyond the unique-concepts item).
- [ ] Black backgrounds on all stations? — evaluate a consistent black backdrop
      for station interiors.

## Exploration & World Content

- [ ] Animals.
- [ ] Hunting.
- [ ] Procedurally generated outdoor areas, with a way to find the exit — biggest
      single expansion of explorable space beyond stations.
- [ ] Planet descriptions (icy, rocky, gas giant, etc.).
- [ ] Reasons to visit hazardous worlds.
- [ ] Events and procedural generation as you travel around systems.

## Graphics & Visual Polish

- [ ] Anti-aliasing via `pygame.gfxdraw` as a second AA option in Settings →
      Video, alongside the existing supersample toggle (`constants.SUPERSAMPLE_AA`
      / the 2×-then-smoothscale path in `main.py`'s PHASE 3). Supersampling is
      universal but costs ~4× fill + a downscale every frame; `gfxdraw`
      (`aacircle` / `aapolygon` / `aaellipse`, plus filled shape + `aa` outline)
      is far cheaper but has to be applied per-primitive at each draw site. Would
      likely be a per-shape helper (draw filled + aa outline) that ship/outfit/
      building/decoration rendering opts into. Make the Settings toggle a
      3-way choice (Off / gfxdraw / Supersample ×2) once it exists.
- [ ] More texture for interior grounds and ships.
- [ ] Render interpolation (lerp each drawable between its previous and
      current sim state on draw). Only worth it if >60 Hz smoothness becomes
      a real goal, or netcode arrives — the fixed-timestep loop currently
      drops a <0.1% sliver of sim time instead, which is fine for a
      single-player game. See [PHYSICS.md](PHYSICS.md) "Frame Timing &
      Smooth Motion".

## Meta, Tooling & Performance

- [ ] Check whether rendering is skipped when not applicable, or whether pygame
      already handles that.
- [ ] Verify the graphics extractor actually writes extracted graphics into the
      config JSON.
- [ ] Guidance for agents on creating a new story from scratch, and on assisting a
      user who wants help creating one.
