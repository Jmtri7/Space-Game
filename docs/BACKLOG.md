# Backlog

Known bugs and planned features that aren't fixed/implemented yet. This is a running
list, not a spec — add to it whenever you notice something, and check an item off (or
delete it) once it's actually fixed/shipped. If you're an agent fixing one of these,
mention it in the commit message so this file and the commit history stay in sync.

Items marked ⭐ were flagged by the user as ones they'd noticed clearly/hit directly
(vs. general ideas) — treat them as slightly higher-confidence reports, not necessarily
higher priority.

## Bugs

- [ ] ⭐ Building collision missing — player/NPCs can walk through buildings.
- [ ] ⭐ NPC facing/heading is ambiguous — hard to tell which direction an NPC is
      oriented or about to move.
- [ ] ⭐ Helmet graphic is the same shade of gray as the ground, hard to distinguish.
- [ ] ⭐ Flaky test: the "should still be moving" background AI-ship test in
      `tests/test_helpers.py` intermittently fails because the routine driving that
      ship (likely `ExplorerRoutine` in `game/world/routine.py`) can produce a
      zero-net-movement frame by chance. Determine whether the zero-movement frame
      is legitimate (fix the test to check across multiple frames) or a routine bug
      (fix the routine). Rerun `python run_tests.py` 10+ times after the fix to
      confirm the flake is gone.

## Features / Ideas

- [ ] Quick save.
- [ ] AI walking pathfinding for wandering NPCs (WanderRoutine) — DockRoutine's visiting
      pilots already route between rooms via `IndoorPathfinder` (see game/world/
      indoor_pathfinder.py); WanderRoutine still just picks a random point in a radius
      with no wall-awareness at all, so a wanderer can still walk into (or get stuck
      against) a wall.
- [ ] Cultural station interiors; round rooms.
- [ ] Options for star/asteroid seeds.
- [ ] Add metrics for game performance.
- [ ] Check whether rendering is skipped when not applicable, or whether pygame already handles that.
- [ ] Indicate when reaching the edge of the star map.
- [ ] Star map zoom.
- [ ] Animals.
- [ ] Hailing other ships.
- [ ] Better jumping animation.
- [ ] Different asteroid types and quantities.
- [ ] Unified buying/selling menus for ships, ship outfitting, and personal items.
- [ ] Better station interior designs (e.g. dorm rooms are currently just short halls).
- [ ] Buying and selling ships and items.
- [ ] Enterable buildings in cities.
- [ ] Missions and conversations with consequences.
- [ ] Picking up and dropping items.
- [ ] More texture for interior grounds and ships.
- [ ] Cultural and role-based clothing for people (space_suit is the only outfit so far - see graphics.json's "outfits" section and Person.outfit).
- [ ] More systems with unique concepts.
- [ ] Better jump graphics.
- [ ] Asteroid mining.
- [ ] Hunting.
- [ ] Procedurally generated outdoor areas, with a way to find the exit.
- [ ] Unlockable conversation options.
- [ ] Relationships.
- [ ] Factions.
- [ ] Combat.
- [ ] Crime.
- [ ] War.
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
