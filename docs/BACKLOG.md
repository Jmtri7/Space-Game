# Backlog

Known bugs and planned features that aren't fixed/implemented yet. This is a running
list, not a spec — add to it whenever you notice something, and check an item off (or
delete it) once it's actually fixed/shipped. If you're an agent fixing one of these,
mention it in the commit message so this file and the commit history stay in sync.

Items marked ⭐ were flagged by the user as ones they'd noticed clearly/hit directly
(vs. general ideas) — treat them as slightly higher-confidence reports, not necessarily
higher priority.

## Bugs

- [ ] ⭐ Overwriting a save returns to the menu with a "saved" message, but creating a new save doesn't.
- [ ] ⭐ Saving while jumping and then loading gets you stuck in the jump temporarily.
- [ ] ⭐ Can talk to people from far away (no proximity check on dialogue).
- [ ] Credits are shown in the middle of the targeting info (overlapping/misplaced UI).
- [ ] Exit menus don't tell how to close them.
- [ ] Weird characters in Elena Voss's dialogue.
- [ ] No indication of when you're close enough to use an exit.
- [ ] Interior features should draw back-to-front (currently wrong draw order/layering).
- [ ] Able to turn while jumping (should probably be locked out).
- [ ] Targeting square should re-size / re-position to fit its target.
- [ ] Gas giant ring is drawn entirely behind the planet (should show in front on the near side).
- [ ] Empty main load menu doesn't tell how to close it.

## Features / Ideas

- [ ] Should single-destination exits still require choosing? Current answer: yes.
- [ ] Quick save.
- [ ] AI walking pathfinding.
- [ ] Cultural station interiors; round rooms.
- [ ] Options for star/asteroid seeds.
- [ ] Add metrics for game performance.
- [ ] Check whether rendering is skipped when not applicable, or whether pygame already handles that.
- [ ] Make sure all systems are simulated (not just the current one).
- [ ] Allow NPCs to jump between systems.
- [ ] Indicate when reaching the edge of the star map.
- [ ] Star map zoom.
- [ ] Animals.
- [ ] Hailing other ships.
- [ ] Better jumping animation.
- [ ] Different asteroid types and quantities.
- [ ] Better people graphics.
- [ ] Unified buying/selling menus for ships, ship outfitting, and personal items.
- [ ] Better station interior designs (e.g. dorm rooms are currently just short halls).
- [ ] Multiple exits with different options.
- [ ] Buying and selling ships and items.
- [ ] Enterable buildings in cities.
- [ ] Missions and conversations with consequences.
- [ ] Picking up and dropping items.
- [ ] More texture for interior grounds and ships.
- [ ] Cultural and role-based clothing for people.
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
