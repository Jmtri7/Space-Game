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
- [x] `ESC` closes the NPC conversation box and the shop menus. Conversation /
      hail box: ESC closes it (Enter picks the highlighted option), handled in
      each screen's `handle_input`. Shop / shipyard / outfitter: ESC closes them
      (a nested purchase confirm or spares picker eats the ESC first), handled
      in `main.py`'s state machine like the key-opened modals. Menu classes stay
      mouse-only. See DESIGN_PATTERNS.md's "Menu vs. Dialog" and CONTROLS.md's
      "Menus".

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

- [~] Factions — combined with crime/war, would turn the sandbox into a living
      political map; cultures/roles already exist as a foundation.
      (Foundation shipped for the `the_long_silence` story: `factions.json`,
      `Possessions.reputation` (-100..+100, saved), `adjust_rep:` dialogue
      action + mission `on_start_rep`/`on_end_rep`, `requires_rep`/
      `requires_rep_below` option gates + faction `conditional_roots`, NPC/pilot
      `faction` tags, and a Standing section in the Possessions menu. Still to
      do: `relations`-matrix bloc ripples, hostility/combat from low standing
      (needs ship combat first), crime/war on top.)
- [~] Combat. (Ship-to-ship shipped in Phase 3: `Ship.health`/`take_damage`,
      `Projectile.owner`, `SpaceScreen._check_projectile_ship_collision`,
      `CombatRoutine` (hostile AI - drives the ship low-level, no autopilot),
      `_sync_hostiles` (rep `<= -40` or a `hostile_to_player:`/`faction_hostile:`
      flag), ship destruction + player recover-at-station. Still open: hostile
      target brackets/UI polish, weapon variety for AI, formations, boarding.)
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
- [x] Asteroid mining. (Done - any of 4 weapon outfits (laser cannon,
      pulse blaster, heavy cannon, scatter gun - each its own damage/fire
      rate/spread/projectile look) damages asteroids on a health pool sized
      off `size`; a large one breaks into smaller fragments, a small one
      scatters its ore as drifting pickups the player has to fly over (with
      cargo room) to collect, type-dependent via asteroid_types.json's
      mine_yield - sold at a quartermaster like any other commodity. See
      ARCHITECTURE.md's "Weapons & Asteroid Mining".)
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

- [x] Anti-aliasing via `pygame.gfxdraw` as a second AA option in Settings →
      Video. Done: `constants.AA_MODE` is now a 3-way `off` / `gfxdraw` /
      `supersample` (was the `SUPERSAMPLE_AA` bool), cycled from the Settings
      menu and saved as `settings.json` `aa_mode`. `game/aa_draw.py`'s
      `polygon()` / `circle()` are `pygame.draw` drop-ins that add a
      `gfxdraw` `aa*` outline in gfxdraw mode (with a plain-`pygame.draw`
      fallback for degenerate / off-screen shapes); the world/asset draw
      sites route their fills through them (`world_object.draw_parts` /
      `_draw_rotated_polygon`, `ship`, `landing_site`, `central_star`,
      `celestial_body`, `asteroid`, `person`, `location_screen` buildings /
      decorations / furniture). UI/HUD stay aliased in gfxdraw mode.
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
- [ ] Migrate the `default` story onto the design-JSON pipeline
      (docs/GRAPHICS_PIPELINE.md) so its art is regenerable again, then drop
      `person_figure.py` / `figure_signatures.py` and the old draw paths.
- [ ] Shared asset modules via an `extends` search path. Today `config/stories/{story}/`
      is fully self-contained and nothing is shared, so a new story that wants the
      design-JSON pipeline has to vendor the whole `graphics/` tree (the
      `the_long_silence` Phase 0 scaffold copied ~180 files from
      `graphics_pipeline_test`). Proposal: add `config/modules/` holding
      foundation-only packs (e.g. `pipeline_core` — bodies, faces, `rig_walk`,
      generic articles, `materials.json`, `palettes/`, `draw_order.json`, base
      ship stat bands, standard weapon outfits); `story.json` gets
      `extends: ["pipeline_core"]`; asset resolution checks the story dir first,
      then walks `extends`. Deliberately keep it one level (stories extend
      modules, modules extend nothing), story-dir-always-wins, and error on
      duplicate ids across modules rather than resolving by precedence. Saves stay
      self-contained (they already snapshot the active system); the existing
      SAVE_SYSTEM.md ⚠️ discipline still applies — a shared-module change that
      reinterprets a stored value bumps the *story's* version. Cost: every
      `load_json("config/stories/{story}/...")` call site goes through a resolver,
      and the editor / atlas tooling (`config/editor.html`, `pipeline_atlas.py`)
      plus `story_menu_rows()` must understand the search path. Pairs naturally
      with the `default`-onto-pipeline migration above — do both in one arc.
