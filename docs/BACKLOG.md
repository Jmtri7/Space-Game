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
- [ ] Make conversation menus look visually consistent with the other menus.
- [x] Button overlapping in the shipyard menu. Fixed: `ui_theme.fit_text`
      ellipsises any grid-cell label to its cell width (shared by Shipyard /
      Shop / Outfitter Buy cells), so a long story-authored ship name can't
      spill into the neighbouring cell.
- [x] Shipyard ship-description text runs off the edge / drifts onto the Buy
      button. Fixed: `ShipBrowserMenu` now reserves the always-shown stat rows,
      gives the free-form description whatever vertical budget is left
      (ellipsised, never spilling), and hard-caps the readout above the
      fixed-position action button; compact stat labels + a smaller font.
      `OutfittingMenu._draw_stat_panel` got the same clamp.

## Navigation & Flight

- [ ] Jumping to system center — the mechanic and its tutorial both need work.
- [ ] Jump-target label wraps excessively.

## Missions, Dialogue & NPCs

- [ ] No mission-complete message when leaving the mission area — a mission that
      completes on leaving/returning surfaces no confirmation toast.
- [ ] Petra Voss should be positioned at the loan office desk.
- [ ] Check the tutorial text and the autopilot popup for accuracy.
- [~] Too many messages early in `the_long_silence` — the opening drowns the
      player in dialogue/toasts right off the bat. Trimmed the wordiest
      induction stage messages and cut the editorialising Standing narration
      (`gen_halcyon.py`). The induction itself is paced one message per action
      (`check_mission_progress` advances one stage/frame), so the remaining
      density is the concourse NPC greetings + ambient lines — needs a
      play-through to tune which NPCs should stay quiet until later.

## Economy & Trading

- [x] You can spend your loan on a laser cannon and then be stuck (no way to
      recover/pay it back). Fixed: `OutfittingMenu` gained a **Sell** tab
      (`SELL_MULTIPLIER` 0.5 of cost, spares only — uninstall first) backed by
      `Possessions.sell_outfit`. Also the `the_long_silence` starter loan was
      cut 100k → 12k.
- [x] Loan amount is too big — fine for testing now, but needs tuning down.
      `the_long_silence`: added a `story.json` `loan` block (lender / amount /
      max_active — see `LocationScreen._loan_terms`) set to 12,000 (courier is
      7,000), replacing the 100,000 engine default (`DEFAULT_LOAN_AMOUNT`).
      Other stories still use the default.

## Stations, Interiors & World Building

- [x] Characters added to a story don't show up in old saves. Fixed by Phase 4:
      NPC and AI-ship rosters are re-derived from config (filtered through
      `content_gate.passes_content_gate`) on every interior / system entry, never
      from the save — so a newly-added or flag-gated character appears in an old
      save once eligible. See `LocationScreen._apply_content_gates` /
      `SpaceScreen._sync_conditional_ships` and SAVE_SYSTEM.md. (Renaming an
      existing pilot still orphans its save-position entry — separate, narrower.)
- [ ] The concierge desk should sit right in front of the player on entry.

## Graphics & Rendering

- [ ] Visiting NPCs (e.g. NPCs that walk into a station interior) render with the
      player's own model instead of a distinct sprite.
- [ ] Pipe fence needs an outline.
- [ ] People sometimes still walk backwards (facing direction lags travel
      direction).
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
- [x] Show the active mission on the in-world HUD. (Space View status pane now
      shows the current act — story.json `acts` / `utils.current_act` — and the
      active mission title. Interior HUD still doesn't; low priority.)
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
- [ ] Weapon projectile variety — beams, bullets, missiles with distinct
      behaviours (not just reskins).
- [ ] Auto-aiming weapons / turrets — mounts that track the current target
      instead of only firing straight ahead.
- [ ] Only allow hitting non-hostile ships when the player has them explicitly
      targeted, to prevent accidental fire on neutrals.

## Ships & Customization

- [ ] Ship customization (paint/decals/name) — cosmetic, cheap, but makes "your
      ship" feel more personal. (Owning multiple ships and switching between
      them at the ship salesman's "Your Ships" tab now works — story `1.12.0`;
      per-ship stored outfit loadouts are still a gap, see SAVE_SYSTEM.md.)
- [~] Make all outfits usable (not just cosmetic/inert). `reinforced_hull` now
      actually adds `+max_health` (was speed-penalty only); `shield_capacitor`
      (+hull) and `sensor_array` (HUD scan of a target's faction/standing/hull)
      added and wired. Remaining inert/weak: afterburner vs ion_thruster
      overlap, cargo_expansion is fine. `Ship.apply_outfits` now also stacks a
      `max_health` `stat_modifier`.
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
- [ ] Improve station interior looks.

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
- [ ] Shoulder pads (character article).
- [ ] Shoulder spikes (character article).
- [ ] Antenna (character article).
- [ ] Better hair.
- [ ] Beacon lighting animation.
- [ ] Better jumping animation.
- [ ] Better jump graphics.
- [ ] More texture for interior grounds and ships.
- [ ] Render interpolation (lerp each drawable between its previous and
      current sim state on draw). Only worth it if >60 Hz smoothness becomes
      a real goal, or netcode arrives — the fixed-timestep loop currently
      drops a <0.1% sliver of sim time instead, which is fine for a
      single-player game. See [PHYSICS.md](PHYSICS.md) "Frame Timing &
      Smooth Motion".

## Sound & Music

- [ ] More music tracks and more sound effects.
- [ ] Asset modules for sounds — extend the config-module system to bundle
      shareable SFX / music packs (pairs with the shared graphics asset-modules
      item under Meta, Tooling & Performance).

## Meta, Tooling & Performance

- [ ] **Agent token optimisation — checked-in permission allowlist.** Add
      `.claude/settings.json` (checked in) with a generalised allowlist of safe
      read-only / dev commands so agents don't burn round-trips on permission
      prompts. `settings.local.json` currently holds ~70 hyper-specific one-off
      entries that collapse to ~20 patterns (`git status/diff/log`,
      `git add/commit/push/checkout/stash`, `python run_tests.py`,
      `python -m py_compile:*`, `python -c:*`, `python main.py`,
      `SDL_VIDEODRIVER=dummy python:*`, `taskkill:*` / `pkill -f:*`,
      `Get-Process python` / `Stop-Process:*`). Writing permission files is
      classifier-gated, so this needs a human (`/permissions` in an interactive
      terminal, or the `update-config` skill).
- [x] **Agent token optimisation — split `ARCHITECTURE.md` and
      `DESIGN_PATTERNS.md`** into a short hub + focused sub-pages. Done:
      `ARCHITECTURE.md` is now a hub (layout + conventions) → `docs/architecture/`
      {class-hierarchy, config-formats, combat-and-mining, extensibility}.md;
      `DESIGN_PATTERNS.md` is a hub (working principles) → `docs/patterns/`
      {rendering, movement, entities, ui-screens, persistence}.md. `docs/README.md`
      route table and the `CLAUDE.md` tree updated in the same commit.
- [ ] Story editor — a `config/editor.html`-style tool for authoring a story
      (systems, characters, missions, dialogue).
- [ ] Rename-articles option in the graphics editor.
- [ ] Colours, not materials — let the pipeline / editor pick plain colours
      instead of named materials.
- [ ] Check whether rendering is skipped when not applicable, or whether pygame
      already handles that.
- [ ] Guidance for agents on creating a new story from scratch, and on assisting a
      user who wants help creating one.
- [ ] Migrate the `default` story onto the design-JSON pipeline
      (docs/GRAPHICS_PIPELINE.md) so its art is regenerable again, then drop
      `person_figure.py` / `figure_signatures.py` and the old draw paths.
- [x] Shared asset modules via a search path. Shipped as the **config-module**
      system: `config/modules/{name}/` shared kits, opted into via `story.json`
      `"modules": [...]`, resolved by [`game/config_source.py`](../game/config_source.py)
      (story dir wins; modules may now depend on modules, flattened by
      `resolved_modules()`). `the_long_silence` uses `figures-human` / `audio-core`
      / `ships-core` / `common-goods` / `story-defaults` instead of vendoring the
      tree. Editor has a Workspace rail + new story/module buttons. Spec:
      [CONFIG_MODULES.md](CONFIG_MODULES.md). (Landed as `"modules"` rather than
      the originally-proposed `"extends"`; still one level in spirit but with
      module→module deps.)
