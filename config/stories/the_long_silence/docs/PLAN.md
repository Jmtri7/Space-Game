# "The Long Silence" — build checklist

A multi-phase plan to ship this multi-system story plus the core-engine
features it needs that don't exist yet.

**The full narrative — systems, factions, acts, the reason for the Silence, and
the three endings — lives in [STORY.md](STORY.md). This file is only the build
checklist.** One-line premise: the Relay (jump-beacon network) went dark 200
years ago and is switching itself back on, system by system, from an old core;
the player flies ahead of that signal, re-contacting cultures that grew strange
in isolation, while four cross-system factions fight over what reconnection
means. Ends on a three-way fork: restore the Relay, sever it, or break only its
hub.

Five systems: **Halcyon** (start, Harbor Authority) → **Kiln** (Ninefold
Combine) → **Verdance** (the Drift) → **Ossuary** (the Vigil) → **The Span**
(the Wardens, the hub). Free carriers are a faction, not a system.

Legend: `[ ]` todo  ·  `[~]` in progress  ·  `[x]` done. Keep this file honest
as work lands (same rule as the rest of `docs/`).

---

## Engine gaps this story exposes

| # | Gap | Why the story needs it | Size |
|---|-----|------------------------|------|
| A | Faction + reputation system | 4 factions gating missions, prices, hostility. Cultures are cosmetic; flags can't hold numeric standing. | Large |
| B | Relay / beacon jump-gating | Systems must unlock progressively; jump is any-to-any today. | Small |
| C | Ship-to-ship combat & hostility | Weapons only hit asteroids; ships have no health/hostility/destruction. | Large |
| D | Flag-conditional world content | AI rosters, station NPCs, decorations are static; systems must visibly react. | Medium |
| E | Arc framework + exclusive choices + ending screen | Missions are linear stage indices; game has no win state. | Medium |
| F | Story dispatch / inbox comms | Faction handlers giving cross-system orders, not an NPC in the room. | Medium |
| G | Save-compat for evolving rosters | Known bug: new characters don't appear in old saves; renaming a pilot orphans its save entry. | Small |

Nice-to-have, not blocking: per-faction buy/sell multipliers, derelict/boardable
ships, enterable city buildings, a world-clock for time pressure.

---

## Phase 0 — Scaffolding  ✅ done

Stub/placeholder only — no per-culture art yet. Art is borrowed from the
**`graphics_pipeline_test`** story (the design-JSON pipeline — see
docs/GRAPHICS_PIPELINE.md), so Phase 6 builds forward on that pipeline rather
than migrating off the frozen `default` art.

- [x] Create `config/stories/the_long_silence/` + `story.json` (v0.1.0) + `docs/` (`PLAN.md`, `STORY.md`)
- [x] Borrow the pipeline art set from `graphics_pipeline_test`: `graphics.json`, `graphics/` (whole design-JSON tree), `ship_types.json`, `building_types.json`
- [x] Keep the art-agnostic config from `default`: `pilots.json`, `missions.json`, `commodities.json`, `items.json`, `ship_outfits.json`, `asteroid_types.json`
- [x] Six `cultures.json` entries — palette + `theme` + `naming` prose (Harbor Authority, Ninefold Combine, the Drift, the Vigil, the Wardens, free carriers); `orbital_std` / `regolith_std` kept as `(placeholder)` so the borrowed pipeline `building_types` resolve their culture colours
- [x] Five stub `systems/*.json` (`halcyon`, `kiln`, `verdance`, `ossuary`, `the_span`) with `star_map_position` along the Relay spine, a culture-tagged station interior each (`trade_ring` / `regolith_moon` / `courier` art, `ck_*` outfits, `pipeline_*` furniture), a moon, 2–3 AI ships. Halcyon carries the real starter loop (loan officer + ship dealer + outfitter).
- [x] Smoke test: story boots headless, pipeline `expand()` resolves the borrowed station/ship, all five systems build + simulate, every station & moon interior builds and ticks, portals walkable, Halcyon tutorial loop walkable, `run_tests.py` green (459)
- [ ] Register the story in the top-level `docs/` tree (BACKLOG "new story" item) — deferred until the story is real enough to document there

### Known placeholder debt to clear in later phases
- Every system uses the same borrowed `trade_ring` station, `regolith_moon` moon, `courier` hull, and grey `pipeline_*` / regolith furniture — replaced per-culture in Phase 6.1–6.6 (6.0 stands up the pipeline foundation).
- Station interiors are plain circle rooms, not the pipeline's ring-arc concourse geometry — real floor plans come with each 6.x slice.
- `missions.json` is still the `default` story's file (inert — `story.json` sets no `starting_mission`). Replaced in Phase 6+.
- No `starting_mission`, so no tutorial yet. Halcyon's anchor mission (Phase 6.1) becomes it.
- `default_outfit` is `ck_flight_femme` (a borrowed pipeline set) — revisit when the player body/outfit story is designed.

## Phase 1 — Faction & reputation system (gap A)  ✅ done

- [x] `factions.json`: id, name, `home_system`, `color`, `starting_standing`, `relations` matrix (relations stored for Phase 7 bloc ripples; not yet applied)
- [x] `Possessions.reputation` `{faction_id: int}` (-100..+100) + `adjust_reputation()` (clamped) + `reputation_with()` — in `__init__` / `get_state()` / `restore_from()` / `from_state()`
- [x] `utils.get_factions()` / `get_faction()` loaders
- [x] Dialogue: `adjust_rep:<faction>:<delta>` action; `requires_rep` / `requires_rep_below` (`"<faction>:<n>"`) option gates; `conditional_roots` faction entries (`{"faction","min","node"}`). `current_options` / `resolve_root` / `choose` / `draw` take `reputation`
- [x] Mission `on_start_rep` / `on_end_rep` (`{faction: delta}`)
- [x] Reputation seeded in `_apply_start_config` from `starting_standing` + `start.reputation`
- [x] Tag local NPCs (`_build_local_character`) + AI pilots (`for_ai_pilot`, system `ai_ships[].faction`) with `faction`
- [x] "Standing" section in `possessions_report` (P menu) — band + signed number, shown only if the story has factions
- [x] the_long_silence: `factions.json` (6 factions), stub NPCs/pilots tagged, demo rep dialogue (Halcyon Controller Vane, Ossuary Keeper Aramis), `story.json` `0.1.0` → `0.2.0`
- [x] Tests: reputation persistence + clamp, `adjust_rep` action, `requires_rep` / `requires_rep_below` gates, faction `conditional_roots`, mission `on_*_rep` (467 pass, +8)
- [x] Docs: SAVE_SYSTEM.md (new `reputation` key + version-bump rule), ARCHITECTURE.md (factions.json, Possessions field, Dialogue gates), CONTROLS.md (Standing section)

**Not in Phase 1** (deferred to where they're actually needed): `relations` ripple logic → Phase 7; hostility from low standing → Phase 3; a dedicated Reputation screen/keybinding (the P-menu section is enough for now).

## Phase 2 — Relay / beacon jump-gating (gap B)

- [ ] `systems/*.json`: `locked: true` + `unlock_flag: "beacon_<id>_lit"`
- [ ] `StarMap` + jump-target picker: locked systems dim / "NO SIGNAL", refuse selection until flag set
- [ ] `light_beacon:<system>` dialogue/mission action — sets unlock flag + posts a galaxy-wide message
- [ ] Wire each system's anchor mission `on_end_flag` to light the next beacon
- [ ] Docs: CONTROLS.md (star map), ARCHITECTURE.md (system fields), UI_FLOW.md if the picker changes

## Phase 3 — Ship-to-ship combat & hostility (gap C)

- [ ] `Ship.health` / `max_health` from `ship_types.json`; `take_damage()`; destruction → `Explosion` + optional loot; remove from `SystemState.ai_ships`
- [ ] `SpaceScreen._check_projectile_ship_collision` (player hittable too)
- [ ] Hostility model: `Character` hostile when `reputation[faction] < threshold` or a flag says so
- [ ] `CombatRoutine` (new, registered in `ROUTINE_REGISTRY`) — seek player + fire
- [ ] Player death handling (min: respawn at last station, lose cargo)
- [ ] **Autopilot regression:** `CombatRoutine` uses `engage_seek` — run the AUTOPILOT_TESTING.md battery, warn the user up front
- [ ] **Save:** ship health persistence; bump story version
- [ ] Docs: ARCHITECTURE.md ("Weapons & Combat"), PHYSICS.md if seek changes, AUTOPILOT_TESTING.md sign-off

## Phase 4 — Flag-conditional world content (gaps D + G)

- [ ] `ai_ships[]` and interior `npcs[]` entries may carry `requires_flag` / `requires_not_flag` / `requires_rep…`; filter in `_build_system_state()` / `_build_local_character()`
- [ ] Same for `decorations` / `structures`
- [ ] Re-evaluate on system (re-)entry, not just new game
- [ ] Fix / document "new characters don't appear in old saves" (gap G) here
- [ ] Docs: ARCHITECTURE.md (system + interior config), SAVE_SYSTEM.md (roster re-derivation)

## Phase 5 — Arc framework, exclusive choices, ending (gap E)

- [ ] `story.json` `acts[]` with an `advance_flag`; current-act line on the HUD
- [ ] `set_exclusive_flag:<group>:<flag>` action — sets one flag in a group, bars the rest
- [ ] `EndingScreen` (menu family) + `"ending"` `current_screen` + `end_story:<id>` action; epilogue keyed to reputation + exclusive flags; returns to main menu
- [ ] Docs: UI_FLOW.md (new screen + transition), ARCHITECTURE.md (`acts`), SAVE_SYSTEM.md (act/ending flags)

## Phase 6 — Content: Act I "Contact" (the five systems)

Split into a shared foundation plus one **vertical slice per system**. Each
slice 6.1–6.5 is independently bootable and demoable: that system gets its real
art, floor plans, NPC roster, pilots, and an anchor mission that lights the next
beacon. Do them in narrative order (Halcyon first — it becomes the tutorial).

Per-slice asset budget (rough): culture palette + `theme`, ~4 ship graphics,
~8 building types, ~8 person outfits, 1 station + 1 moon, 1–2 interior floor
plans, 5–8 NPCs (each revealing a feature or a faction stance), 5–8 pilots with
routines + hail dialogue, 1 anchor mission. Whole-story totals: ~6–7 cultures,
8–10 ship *types*, 20–30 ship *graphics*, 40–55 building types, 40–60 outfits,
30–45 pilots, ~200 asset defs — dominated by buildings and outfits, most of
which are article/palette reuse rather than new shapes.

### 6.0 — Pipeline foundation (once, no culture content)
- [ ] Prune the borrowed `graphics_pipeline_test` set down to what this story keeps (bodies, faces, `rig_walk`, generic articles, shared furniture/decoration/collision, `draw_order`, `materials`, `palettes`)
- [ ] Base ship *stat* blocks (8–10 gameplay-distinct hulls) in `ship_types.json` — currently just the borrowed `courier`
- [ ] Base commodity + ship-outfit set (Phase 3 combat gear folds in here) — currently the borrowed `default` files
- [ ] Own the `graphics.json` catalogue (station/ship/moon/outfit entries) instead of the verbatim borrow

### 6.1 — Halcyon / Harbor Authority
- [ ] Real station + moon art; Hub Control floor plan; ~4 ships, ~8 buildings, ~8 outfits
- [ ] NPC roster + 5–8 pilots, faction-tagged
- [ ] Anchor mission = the tutorial: controls → loan → ship → first jump → light Beacon 2 (Kiln)
- [ ] `story.json`: set `starting_mission` + trigger

### 6.2 — Kiln / Ninefold Combine
- [ ] Deep-mine station + mine-moon art; contract-law culture floor plan
- [ ] NPCs + pilots; anchor mission ends hostile-leaning, lights Beacon 3 (Verdance)

### 6.3 — Verdance / the Drift
- [ ] Cloud-city + agri-ring art; consensus-assembly interior
- [ ] NPCs + pilots; anchor mission (the assembly can't decide), lights Beacon 4 (Ossuary)

### 6.4 — Ossuary / the Vigil
- [ ] Name-Wall / archive interior; grave-moon
- [ ] NPCs + pilots; anchor mission delivers the true history + the warning

### 6.5 — The Span / the Wardens (Act I stub)
- [ ] Minimal Warden interior + exterior art; system stays **beacon-locked** until Act II
- [ ] Just enough to exist on the star map as "NO SIGNAL"

### 6.6 — Free carriers pass
- [ ] Faction-tag the existing wandering pilots across all five systems; carrier berth dressing; 2–3 carrier-specific ship graphics

## Phase 7 — Content: Act II "Pressure"

- [ ] Faction-handler NPCs + dispatch comms (gap F): cargo / refugee runs, escort contracts, recon
- [ ] Kiln mobilisation — conditional hostile pilots in Verdance (needs Phases C + D)
- [ ] Reputation swings from mission choices; `set_exclusive_flag` locks in a patron faction
- [ ] Mid-act gate: standing with ≥1 faction lights the Span beacon

## Phase 8 — Content: Act III "The Span" + endings

- [ ] The Span interior: Warden NPCs, the archive terminal, the shutdown reveal
- [ ] Three `end_story` branches wired to the fork; reputation checks decide availability + epilogue tone
- [ ] `EndingScreen` epilogue text: per system, per ending

## Phase 9 — Playtest, balance, save discipline

- [ ] Full playthrough of each ending path
- [ ] Economy / loan tuning (BACKLOG: loan too big; laser-cannon soft-lock)
- [ ] Combat balance pass; autopilot battery re-run
- [ ] Final `story.json` version bump; SAVE_SYSTEM.md worked example of an old save vs. the finished story
- [ ] Move completed BACKLOG items to done (factions, combat, escort contracts, win state)

---

## Dependency order

```
Phase 0
  ├─ Phase 1 (factions) ─┬─ Phase 3 (combat needs faction hostility)
  │                      ├─ Phase 4 (conditional content)
  │                      └─ Phase 5 (exclusive choices, endings)
  ├─ Phase 2 (beacons) ─── independent, small
  └─ gap G — folded into Phase 4; decide the approach during Phase 1

Engine Phases 1–5 gate the content that relies on them. Phase 6 system /
interior / art work for Act I can run in parallel with engine work — it only
needs Phase 0.
```
