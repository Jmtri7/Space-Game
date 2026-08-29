# Backlog

Known bugs and planned features that aren't fixed/implemented yet. This is a running
list, not a spec — add to it whenever you notice something, and check an item off (or
delete it) once it's actually fixed/shipped. If you're an agent fixing one of these,
mention it in the commit message so this file and the commit history stay in sync.

Top-level split is **Bugs vs. Features**. Within each, items are grouped by the type of
gameplay they belong to, so related work is easy to find together. A gameplay category
only appears under a section if it currently has items there.

# Bugs

## Missions, Dialogue & NPCs

- [ ] Target isn't officially cleared when an NPC exits the interior, so a new
      target isn't chosen when walking close again.
- [ ] No mission-complete message when leaving the mission area — a mission that
      completes on leaving/returning surfaces no confirmation toast.

## Ships & Customization

- [ ] Gap: what happens when you buy a second ship? (multiple owned ships behavior
      is undefined — see the feature item under Ships & Customization.)

## Economy & Trading

- [ ] You can spend your loan on a laser cannon and then be stuck (no way to
      recover/pay it back).
- [ ] Loan amount is too big — fine for testing now, but needs tuning down.

## Stations, Interiors & World Building

- [ ] Characters added to a story don't show up in old saves.

## Graphics & Rendering

- [ ] Visiting NPCs (e.g. NPCs that walk into a station interior) render with the
      player's own model instead of a distinct sprite.
- [ ] Building collision footprint extends too far below the building graphic.
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
- [x] Minimap: click a target to select it. (`SpaceScreen._select_target` /
      the minimap branch in `handle_input` - a click on a blip targets it,
      inferring the target mode.)
- [ ] Make the player icon on the minimap more obvious than the others.
- [x] Hover text on the minimap when the mouse is over a point, showing what it
      is. (`_draw_minimap_tooltip` / `_minimap_blip_at` / `_minimap_label`.)
- [ ] Make credits amount display consistent with other UI texts.
- [ ] Some selling-menu controls (like the ship menu) don't mention that you can use
      the mouse.
- [ ] Consider mouse-based movement/control support.
- [ ] Show the active mission on the in-world HUD.
- [ ] Controls should be usable without moving the hand off WASD / arrow keys —
      avoid bindings that force the player to reposition their hand.

## Navigation & Flight

- [ ] Indicate when reaching the edge of the star map.
- [ ] Star map zoom.
- [ ] System minimap (local-system view during flight, distinct from the interstellar
      star map).

## Missions, Dialogue & NPCs

- [ ] NPCs in interior locations (station interiors, etc.) should be able to display
      messages on screen too, not just NPCs hailing from space.
- [ ] Mission Log: split into two tabs, Active and Completed, so finished
      missions have their own place instead of being mixed into the same list
      as in-progress ones (`report_menu.mission_report()` already gets both from
      `mission_status_lines()`).
- [ ] Tutorial mission for taking out a loan and buying a ship. (Engine
      support done: `took_loan` / `bought_ship` / `bought_ship:<type>`
      gameplay-event flags - just needs the missions.json stages written.)
- [ ] Tutorial for turning the camera.
- [ ] Tutorial for jumping to another system.
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

- [ ] Multiple owned ships.
- [ ] Ship customization (paint/decals/name) — cosmetic, cheap, but makes "your
      ship" feel more personal, especially once multiple owned ships exist.
- [ ] Make all outfits usable (not just cosmetic/inert).
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

- [x] Cultural station interiors; round rooms. (Interiors are polygon `rooms` -
      `{"shape":"circle"}` N-gons, concave polygons, `{"rect"}` - unioned into
      one walkable area; each `culture` drives wall/floor/trim colour plus an
      `interior_decoration` generator. See `normalize_room` in
      `location_screen.py`.)
- [x] Better station interior designs. Each default-story station is now one
      connected area (dormitory/corridor/concourse/spaceport/loan_office
      collapsed to a single interior with one ship portal).
- [ ] Enterable buildings in cities.
- [~] More interior decorations, like roads. (Decoration system done -
      per-interior `decorations` floor/wall decals + per-culture packs; moon
      cities have road decals. Room for more content.)
- [ ] Cultural and role-based clothing for people (space_suit is the only outfit so
      far - see graphics.json's "outfits" section and Person.outfit).
- [ ] More systems with unique concepts.

## Exploration & World Content

- [ ] Options for star/asteroid seeds.
- [ ] Animals.
- [ ] Hunting.
- [ ] Procedurally generated outdoor areas, with a way to find the exit — biggest
      single expansion of explorable space beyond stations.
- [ ] Planet descriptions (icy, rocky, gas giant, etc.).
- [ ] Reasons to visit hazardous worlds.
- [ ] Events and procedural generation as you travel around systems.

## Graphics & Visual Polish

- [ ] Better jumping animation.
- [ ] Better jump graphics.
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
- [ ] Guidance for agents on creating a new story from scratch, and on assisting a
      user who wants help creating one.
