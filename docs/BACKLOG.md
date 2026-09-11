# Backlog

Known bugs and planned features that aren't fixed/implemented yet. This is a running
list, not a spec — add to it whenever you notice something. Once an item is
*completely* done, delete it outright rather than leaving a checked-off `[x]` entry;
the commit history is the record of what shipped. Only keep a `[~]` entry when work
is partially done and the remaining gap is worth tracking. If you're an agent fixing
one of these, mention it in the commit message so this file and the commit history
stay in sync.

Top-level split is **Bugs vs. Features**. Within each, items are grouped by the type of
gameplay they belong to, so related work is easy to find together. A gameplay category
only appears under a section if it currently has items there. Items specific to the
`the_long_silence` story live in their own section at the bottom.

# Bugs

## Controls & UI

- [ ] Make conversation menus look visually consistent with the other menus.
- [ ] Bug: talking to a shopkeeper opens the shop after the conversation (shop
      should not auto-open on dialogue end).

## Navigation & Flight

- [ ] Jumping to system center — the mechanic and its tutorial both need work.
- [ ] Arrow / indicator should point at the current target when indoors.

# Features

## Controls & UI

- [ ] Quick save.
- [ ] Active mission selector with arrows — let the player cycle which mission is
      the active/tracked one.
- [ ] Consider mouse-based movement/control support.
- [ ] Allow arrow keys to change meny selections.

## Navigation & Flight

- [ ] Add a border to the edge of the star map where no systems can be.
- [ ] Star map zoom.

## Missions, Dialogue & NPCs

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
- [ ] Mounted outfit graphics (visually show equipped outfits on the ship).
- [ ] Graphic for ship thrusters so they're visible when turned off.

## Economy & Trading

- [ ] Sell all button.
- [ ] Picking up and dropping items.
- [ ] More ways to make money.
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

## Exploration & World Content

- [ ] Animals.
- [ ] Hunting.
- [ ] Procedurally generated outdoor areas, with a way to find the exit — biggest
      single expansion of explorable space beyond stations.
- [ ] Planet descriptions (icy, rocky, gas giant, etc.).
- [ ] Reasons to visit hazardous worlds.
- [x] Events and procedural generation as you travel around systems — first
      slice shipped: the `system-events` module + a system's `"events"`
      config block (see architecture/config-formats.md's "System events"),
      with one `"special_asteroid"` kind (`rich_ore_vein`) so far. Still
      open: wreck/derelict-ship/anomaly/wormhole event kinds, each of which
      needs its own spawn path since they don't fit the per-chunk asteroid
      model this first kind reuses (see combat-and-mining.md).

## Graphics & Visual Polish

- [ ] Shoulder pads (character article).
- [ ] Shoulder spikes (character article).
- [ ] Antenna (character article).
- [ ] Better hair.
- [ ] Beacon lighting animation.
- [ ] Better jumping animation.

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
- [ ] Story editor — a `config/editor.html`-style tool for authoring a story
      (systems, characters, missions, dialogue).
- [ ] Rename-articles option in the graphics editor.
- [ ] Colours, not materials — let the pipeline / editor pick plain colours
      instead of named materials.
- [ ] Check whether rendering is skipped when not applicable, or whether pygame
      already handles that.
- [x] Guidance for agents on creating a new story from scratch, and on assisting a
      user who wants help creating one. See [STORY_DESIGN.md](STORY_DESIGN.md)
      (2026-09-11, distilled from building `the_whisper_line`).
- [ ] Migrate the `default` story onto the design-JSON pipeline
      (docs/GRAPHICS_PIPELINE.md) so its art is regenerable again, then drop
      `person_figure.py` / `figure_signatures.py` and the old draw paths.

# The Long Silence (story-specific)

## Structure & pacing

- [~] Too many messages early — the opening drowns the player in dialogue/toasts
      right off the bat. Trimmed the wordiest induction stage messages and cut the
      editorialising Standing narration (`gen_halcyon.py`). The induction itself is
      paced one message per action (`check_mission_progress` advances one
      stage/frame), so the remaining density is the concourse NPC greetings +
      ambient lines — needs a play-through to tune which NPCs should stay quiet
      until later.
- [ ] Combine the tutorial with the story (one onboarding flow, not two).
- [ ] Story is too short — too much walking and talking, not enough activities.
- [ ] Nobody teaches you how to land or use autopilot.
- [ ] No message when skipping the tutorial and visiting Kiln.
- [ ] Hub opens but the mission text still says to go back to Verdance.

## Dialogue & briefing

- [ ] Sella's description of jumping to Kiln is mixed with a description of
      jumping back to system center.
- [ ] You should be briefed on what to do when contacting the Combine.
- [ ] Factor Tol doesn't explain where he is.
- [ ] Factor Tol doesn't explain where to witness your mark.
- [ ] Can you open the sealed manifest? (unclear / no affordance)
- [ ] Highcanopy: you get a message with directions to Tam but none to get to
      Osei.
- [ ] Reasons to visit the undergarden aren't given.
- [ ] Keeper Aramis messages immediately (should be delayed / triggered).
- [ ] Dialogue can be confusing — especially the name-wall accounts and the story
      of the beacons.
- [ ] Too many messages after returning to Factor Tol — you get ~4 at once:
      "Beacon relit Verdance", "Kiln relit / signal has reached Kiln",
      "Free carriers — you have been lighting the beacons, carry for us when you
      can", "Load's aboard to ossuary" (relief down the line may start too soon).
- [ ] Too many messages after the vote — "Ossuary beacon relit", "Vigil keeper —
      what the beacons were for, you have read part of the wall now", "Notice of
      closure — the Combine has voted, the Kiln lane is closing and its patrols
      are cleared to turn back", "There's a carrier crew still on the ground at
      Combine Hold — their hull's impounded and the lane's closing around them".

## World geography & placement

- [ ] Tam is placed to the SW but should be to the NW.
- [ ] Hit box too big on the Highcanopy lamp.
- [ ] Make the name wall actually visible.

## Missions & triggers

- [ ] Visiting Ossuary without intentionally talking to the free carriers still
      gives you a message about Sister Edda's people taking it from the hold —
      did landing complete a mission it shouldn't have?

## Art

- [ ] Floor designs should differ for Authority vs. Combine. Also jaggies in the
      floor patterns.
