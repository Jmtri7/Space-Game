# Backlog

Known bugs and planned features that aren't fixed/implemented yet. This is a running
list, not a spec — add to it whenever you notice something, and check an item off (or
delete it) once it's actually fixed/shipped. If you're an agent fixing one of these,
mention it in the commit message so this file and the commit history stay in sync.

Items marked ⭐ were flagged by the user as notable in some way — either a bug they'd
noticed clearly/hit directly, or a feature specifically called out in discussion (vs.
general ideas) — treat them as slightly higher-confidence/interest, not necessarily
higher priority.

## Features / Ideas

- [ ] Quick save.
- [ ] Cultural station interiors; round rooms.
- [ ] Options for star/asteroid seeds.
- [ ] Add metrics for game performance.
- [ ] Check whether rendering is skipped when not applicable, or whether pygame already handles that.
- [ ] Indicate when reaching the edge of the star map.
- [ ] Star map zoom.
- [ ] Animals.
- [ ] ⭐ Hailing other ships — cheap to build, big personality payoff (bounty threats, distress calls, trade offers) once ships aren't just physics objects.
- [ ] Better jumping animation.
- [ ] Different asteroid types and quantities.
- [ ] Better station interior designs (e.g. dorm rooms are currently just short halls).
- [ ] Enterable buildings in cities.
- [ ] ⭐ Missions and conversations with consequences — dialogue trees already exist, so branching stakes is a natural next layer.
- [ ] Picking up and dropping items.
- [ ] More texture for interior grounds and ships.
- [ ] Cultural and role-based clothing for people (space_suit is the only outfit so far - see graphics.json's "outfits" section and Person.outfit).
- [ ] More systems with unique concepts.
- [ ] Better jump graphics.
- [ ] ⭐ Asteroid mining — pairs naturally with the existing asteroid fields and "different asteroid types" idea; gives the economy a real gameplay loop instead of just trading.
- [ ] Hunting.
- [ ] ⭐ Procedurally generated outdoor areas, with a way to find the exit — biggest single expansion of explorable space beyond stations.
- [ ] ⭐ Unlockable conversation options — ties into missions/consequences above.
- [ ] Relationships.
- [ ] ⭐ Factions — combined with crime/war, would turn the sandbox into a living political map; cultures/roles already exist as a foundation.
- [ ] Combat.
- [ ] ⭐ Crime — see factions.
- [ ] ⭐ War — see factions.
- [ ] More roles.
- [ ] More ways to make money.
- [ ] More interior decorations, like roads.
- [ ] Multiple owned ships.
- [ ] Guidance for agents on creating a new story from scratch, and on assisting a user who wants help creating one.
- [ ] Planet descriptions (icy, rocky, gas giant, etc.).
- [ ] Reasons to visit hazardous worlds.
- [ ] Events and procedural generation as you travel around systems.
- [ ] System minimap (local-system view during flight, distinct from the interstellar star map).
- [ ] Minimap: bigger title text.
- [ ] Minimap: click a target to select it.
- [ ] Autopilot should indicate what it's currently doing (e.g. "approaching", "braking").
- [ ] Conversations should show help text (e.g. "Enter: continue, ESC: exit") like other menus.
- [ ] No useless NPCs — each one should reveal something about the game's features or story.
- [ ] Consider mouse-based movement/control support.
- [ ] NPCs stop wandering if the player moves close to or targets them.
- [ ] Jump completed message.
- [ ] Advice/hint to jump if the player drifts too far from the system.
- [ ] ⭐ Derelict ships / distress beacons — a drifting AI ship with no pilot response you can board, loot, or tow; combines the existing AI ship, interior, and item-pickup ideas into one encounter type.
- [ ] ⭐ Bounty hunting board — a station terminal listing wanted ships/NPCs with a reward, feeding off factions/crime once those exist.
- [ ] ⭐ Escort/wingman contracts — hire or be hired to fly alongside another AI ship to a destination; reuses existing autopilot and multi-AI-ship work.
- [ ] ⭐ Black-market smuggling runs — contraband cargo that's profitable but triggers scans/hails from patrol ships if caught; a light crime mechanic that doesn't need the full Crime system first.
- [ ] ⭐ Ship customization (paint/decals/name) — cosmetic, cheap, but makes "your ship" feel more personal, especially once multiple owned ships exist.
- [ ] ⭐ AI ships flying in formations.
- [ ] Bug: you can spend your loan on a laser cannon and then be stuck (no way to recover/pay it back).
- [ ] Bug/gap: what happens when you buy a second ship? (multiple owned ships behavior is undefined — see existing "Multiple owned ships" item.)
- [ ] Rotate camera.
- [ ] Graphic for ship thrusters so they're visible when turned off.
- [ ] Mounted outfit graphics (visually show equipped outfits on the ship).
- [ ] Make all outfits usable (not just cosmetic/inert).
- [ ] Make some commodities usable for various purposes (not just tradeable).
- [ ] Bug: characters added to a story don't show up in old saves.
- [ ] Distinct buy and sell multipliers per good, dependent on various factors (supply/demand, faction, location, etc.).
