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

## Phase 2 — Relay / beacon jump-gating (gap B)  ✅ done

- [x] `systems/*.json`: `locked: true` + `unlock_flag`; `utils.system_unlocked()`; `get_star_systems()` projection carries `locked` / `unlock_flag`
- [x] `SpaceScreen.try_jump` refuses a locked destination with a "No signal from ..." notice (`jump_message` generalised from the fixed "too close" string)
- [x] `StarMap` takes `flags`; locked systems drawn dim with a **NO SIGNAL** tag, unpickable (`_system_at` returns None), a locked initial selection falls back to the current system
- [x] `light_beacon:<system_id>` shared dialogue action (resolves the system's `unlock_flag`, or `beacon_<id>_lit`); `apply_shared_actions` gained a `story` arg
- [x] `SpaceScreen._check_beacons()` posts a galaxy-wide "Beacon relit: ..." message the frame a beacon flag flips (seeded on first call so a loaded save stays quiet)
- [x] the_long_silence: Halcyon unlocked; Kiln/Verdance/Ossuary/The Span `locked` with `beacon_*_lit` flags. Scaffold chain traversable: Controller Vane lights Kiln, each outer host lights the next (Keeper Aramis lights the Span). `story.json` `0.2.0` → `0.3.0`.
- [x] Tests: `system_unlocked`, `light_beacon` action, try_jump gating, StarMap locked behaviour, `_check_beacons` message (475 pass, +8)
- [x] Docs: ARCHITECTURE.md (system fields + `get_star_systems` projection), CONTROLS.md (Star Map NO SIGNAL), SAVE_SYSTEM.md (reachability derived from saved flags), dialogue.py

**Deferred:** anchor missions lighting the next beacon via `on_end_flags` — the hook works today (`on_end_flags: ["beacon_<x>_lit"]`); the missions themselves are Phase 6. The scaffold uses host dialogue in the meantime.

## Phase 3 — Ship-to-ship combat & hostility (gap C)  ✅ done

- [x] `Ship.health` / `max_health` (`ship_types.json` `"max_health"`, else size-derived), `take_damage()`, `park()` repairs to full
- [x] `Projectile.owner`; `_fire_weapon(shooter, stats, aim, owner)` shared by player (SPACE) and AI; `_ai_weapon_stats` (laser baseline, half rate); `_update_ai_weapon_fire` (per-pilot `ai_fire_cooldown`)
- [x] `SpaceScreen._check_projectile_ship_collision` — player shot hits any AI, AI shot hits only the player, never own owner
- [x] `_destroy_ship` (explosions + roster removal, target re-syncs via `_validate_target`); `_on_player_destroyed` (explode → recover at station, full repair, **cargo lost**, message) — checked once/frame after `_update_projectiles`, not inline
- [x] `CombatRoutine` (`combat_routine.py`) — turn to face, close to `PREFERRED_RANGE`, set `character.firing`. **Drives the ship low-level, never `engage_seek`/autopilot** — a scripted override like `OrbitPlayerRoutine`, not in `ROUTINE_REGISTRY` (deviates from the plan's wording, matches the established pattern)
- [x] `_sync_hostiles` (every frame, all systems) — `CombatRoutine` when faction standing `<= -40` (`HOSTILE_REP_THRESHOLD`) or a `hostile_to_player:<name>` / `faction_hostile:<faction>` flag; back to the role routine otherwise; `character.in_combat` tracks it
- [x] HUD **Hull: N%** in the status pane when damaged
- [x] **No autopilot change** — the full AUTOPILOT_TESTING.md battery doesn't apply (see its Scope note). Validated: `run_tests.py` (incl. `TestAutopilotPhysics`) + a 2000-frame headless pursuit sim vs. a circling target (bounded distance, no NaN, no runaway)
- [x] **Save:** player + per-AI-ship `health` (additive; old saves load full; clamped `[1, max_health]`). `story.json` `0.3.0` → `0.4.0`
- [x] the_long_silence: Factor Tol's "The Authority is opening this system with or without your consent" (`adjust_rep:ninefold_combine:-50`) drops Kiln below the threshold and its pilots attack
- [x] **Follow-up (playtest fixes):** `_provoke` — a player shot on any neutral AI ship makes *that* ship fight back (persisted `hostile_to_player:<name>` flag) and costs −10 with its faction, so sustained aggression turns the whole faction hostile via the normal threshold. Scaffold `pilots.json` rewritten to 11 faction-tagged patrol/hauler pilots, and every scaffold `ai_ships` entry given a `["station","moon"]` route — system traffic actually moves now instead of sitting idle (patrol pilots had no route → `OrbitRoutine` no-op; `courier_pilot`/`mining_foreman` roles fall back to `IdleRoutine`).
- [x] Tests: +14 (489) — `TestShipHealth`, `TestCombatRoutine`, `TestShipCombat` (hostility swap, provocation, collision ownership, destruction, player recovery, health save round-trip)
- [x] Docs: ARCHITECTURE.md ("Weapons, Combat & Asteroid Mining" + routine table + provocation), SAVE_SYSTEM.md, AUTOPILOT_TESTING.md (scope note), CONTROLS.md, BACKLOG.md

**Deferred:** hostile-ship target brackets / red HUD, AI weapon variety, formations, boarding/derelicts, loot drops on kill.

## Phase 4 — Flag-conditional world content (gaps D + G)  ✅ done

- [x] `game/world/content_gate.py` — `passes_content_gate(entry, flags, reputation)` / `is_gated(entry)`. Keys: `requires_flag` / `requires_not_flag` / `requires_rep` / `requires_rep_below` (`"<faction>:<n>"`), same vocab as `Dialogue`'s option gate. An entry with no key always passes.
- [x] `ai_ships[]` gated: `_build_system_state` builds only eligible ships (+ `state.ai_ship_configs` / `state.system_id` / `ship._spawn_cfg`); `_build_ai_ship` extracted; `_sync_conditional_ships` adds/drops gated ships on `_activate_system` (re-entry) and `board_ship` (launch) — not per-frame, so nothing pops in in front of the player
- [x] interior `npcs[]` + `structures[]` gated: `LocationScreen._apply_content_gates` (re-run from `arrive_from`) rebuilds `self.npcs` / `self.structures` / `self.building_footprints` and invalidates the nav grid. Cosmetic `decorations` not gated (deferred — culture-pack interaction is fiddly, low value)
- [x] **Gap G fixed:** rosters are re-derived from config on entry, never from the save, so a character added to a story (or gated behind a now-set flag) appears in an old save
- [x] the_long_silence (`0.4.0` → `0.5.0`): a "Displaced traveller" NPC at Hub Control (`requires_flag: beacon_verdance_lit`), a "Combine Raider" ship over Verdance (`requires_rep_below: ninefold_combine:-20`, pilot `raska`). Story description de-scaffolded.
- [x] Tests: +7 (499) — `TestContentGate`, `TestConditionalWorldContent` (gated NPC/structure on `arrive_from`, gated ship on `_sync_conditional_ships`)
- [x] Docs: ARCHITECTURE.md (system + interior config + the gate mechanism), SAVE_SYSTEM.md (roster re-derivation, gap G), BACKLOG.md (bug closed)

**Deferred:** gating cosmetic `decorations`; a mid-flight re-sync (currently only on entry/launch — a flag set by an in-space event won't change the roster until the next dock+launch or jump).

## Phase 5 — Arc framework, exclusive choices, ending (gap E)  ✅ done

- [x] `story.json` `acts[]` (`id` / `name` / `advance_flag`); `utils.current_act`; Space View HUD status pane shows the current act + active mission title (closes BACKLOG "show active mission on HUD")
- [x] `set_exclusive_flag:<group>:<name>` action — sets `<group>:<name>`, clears every other `<group>:*`
- [x] `end_story:<id>` action → `story_over` + `ending:<id>` flags; `utils.resolve_ending`; `main.py` checks it each frame and switches to `"ending"`
- [x] `EndingScreen` (`ReportMenu` subclass, one "Return to Menu" button) + `ending_report(story, id, possessions)` — title + epilogue paragraphs + one line per faction chosen by final standing band. `endings.json` per story. `ReportMenu.handle_input` generalised to return any button id.
- [x] the_long_silence (`0.5.0` → `0.6.0`): `acts` (I Contact / II Pressure / III The Span, advanced by lighting Verdance's / the Span's beacon); `endings.json` (restore / sever / hold_middle, ~3 epilogue paras + 6 factions × 2–3 bands each); First Warden at the Span offers the 3-way fork (`hold_middle` gated on Vigil standing ≥ 10 and not having pledged the Authority); `set_exclusive_flag:patron:*` pledges at Controller Vane (Authority) and Keeper Aramis (Vigil)
- [x] Tests: +6 (505) — `TestActsAndEndings`
- [x] Docs: UI_FLOW.md (`"ending"` state), ARCHITECTURE.md (`acts`, `endings.json`, new actions), SAVE_SYSTEM.md (act/ending/exclusive flags), BACKLOG.md

**Deferred:** interior HUD act line; a per-act HUD colour/framing; richer ending art (it's plain scrolling text).

## Phase 6 — Content: Act I "Contact" (the five systems)  ✅ done

All six slices landed (6.0 foundation + 6.1–6.6). Act I plays end to end:
Halcyon → Kiln → Verdance → Ossuary → (Span opens in Act II), every system with
authored culture art, a real floor plan + roster, a bespoke wardrobe, an anchor
mission, and free carriers present throughout. Each slice is regenerated by its
own `docs/gen/gen_<system>.py` (run order in `docs/gen/README.md`). Remaining
polish is tracked per-slice below and in Phase 7+.

Split into a shared foundation plus one **vertical slice per system**. Each
slice 6.1–6.5 is independently bootable and demoable: that system gets its real
art, floor plans, NPC roster, pilots, and an anchor mission that lights the next
beacon. Do them in narrative order (Halcyon first — it becomes the tutorial).

Per-slice asset budget (rough): culture palette + `theme`, ~4 ship graphics,
~8 building types, **1 culture wardrobe** (see below), 1 station + 1 moon, 1–2
interior floor plans, 5–8 NPCs (each revealing a feature or a faction stance),
5–8 pilots with routines + hail dialogue, 1 anchor mission. Whole-story totals:
~6–7 cultures, 8–10 ship *types*, 20–30 ship *graphics*, 40–55 building types,
~5 culture wardrobes, 30–45 pilots, ~200 asset defs — dominated by buildings.

**Culture wardrobe (bespoke articles, not palette recolors).** Each slice
authors real garment geometry for its culture — new `graphics/articles/` +
`graphics/items/` + culture-specific `graphics/sets/` — not just a `<pfx>_dress`
palette over the borrowed `ck_*` sets. Budget per culture is ~4 garment sets by
*role*, and same-role NPCs share the same set or a close variant:
- an **official / command** uniform (the faction's identity garment)
- a **security / enforcement** kit
- a **work / dock** kit
- **civilian** dress (1–2 variants)
Femme/masc cuts of each via the body `regions[].geometry.{masc,femme}` +
`fits:` machinery. Distinct silhouette per culture is the point — Authority
pressed tailoring vs Combine hardwear vs Drift layered soft goods, etc. Reuse
across cultures is fine only where the fiction supports it (e.g. free-carrier
flight rigs).

### 6.0 — Foundation + per-culture asset stubs  ✅ done
- [x] `commodities.json` — 9 thematic goods; per-system quartermaster stock. (`0.6.0` → `0.7.0`)
- [x] **Distinct per-culture stubs for every graphic asset** (`0.7.0` → `0.8.0`, generators `gen_assets.py` + `retag_assets.py` in scratchpad):
  - `graphics/palettes/<pfx>.json` + `<pfx>_dress.json` — 12 palettes, **real colours** derived from `cultures.json`
  - `graphics/ships/<pfx>_{courier,hauler,patrol}.json` — 18 ship designs + `ship_types.json` stat blocks (per ARCHITECTURE bands) + `graphics.json` entries
  - `graphics/stations/<pfx>_station.json` — 6 station designs + catalogue entries
  - `graphics.json` `moons` — 6 per-culture moons (real culture-tinted colour)
  - `graphics/buildings/<pfx>_{hall,housing,spire}.json` — 18 building designs + `building_types.json` entries (furniture stays the 5 shared `pipeline_*` types)
  - `graphics.json` `outfits` — 60 per-culture outfit entries (5 roles × femme/masc). **First pass only** reuses the shared `ck_*` article sets with a `<pfx>_dress` palette; each slice 6.1–6.6 replaces its culture's entries with a bespoke wardrobe (real articles + culture `sets`, ~4 garment sets by role — see the culture-wardrobe note above).
  - **Each design file carries a written `identity` brief** from that culture's theme + a "geometry is a placeholder copy — reshape" note
  - `systems/*.json` retagged to reference the per-culture ids (station/moon/ship/building/outfit); ship dealers sell culture-appropriate lineups
- [ ] Own `ship_outfits.json` (still the borrowed `default` 8 — a decent base; add a shield + scanner later)
- [ ] Prune / own the borrowed `graphics_pipeline_test` foundation (bodies, faces, `rig_walk`, articles, `draw_order`, `materials`) — cosmetic, do alongside a real slice

### What 6.1–6.6 now is
The stubs exist; each slice **shapes the placeholder geometry** for one culture (ships, station, 3 buildings) toward its `identity` brief, **authors that culture's bespoke wardrobe** (real garment articles + culture `sets`, ~4 sets by role — replacing the first-pass `<pfx>_dress` palette recolors), plus that system's real interior floor plan, NPC roster depth, hail dialogue, and an anchor mission. Each gets its own `docs/gen/gen_<system>.py` on the `gen_halcyon.py` model (see `docs/gen/README.md`).

### 6.1 — Halcyon / Harbor Authority  ✅ done — `docs/gen/gen_halcyon.py`, story `0.9.1`
- [x] **First-pass Authority ship designs** — `authority_{courier,hauler,patrol}` authored as real design JSON: rectilinear hulls, guidance chevrons, ranked window bands, chrome-and-navy palette (not the placeholder courier copy). `graphics.json` `thrusters`/`local_points` patched to match.
- [x] **`authority_station`** — a rectilinear cross-hub with a control block, four docking arms, a signal mast (not the octagon ring).
- [x] **`authority_{hall,housing,spire}`** — elevation buildings: colonnaded civic hall, ranked-window housing slab, three-tier control spire with a scan-lamp. Footprints updated.
- [x] `authority_dress` palette tuned to pressed navy + chrome.
- [x] **Bespoke Authority wardrobe** — five identity articles (`authority_chevron_tab` — the throat guidance chevron every kit carries; `authority_shoulder_boards` — squared chrome; `authority_service_cap` — peaked, chevron badge; `authority_brassard` — warden's arm band; `authority_duty_belt` — chevron buckle) + five culture `sets/authority_{command,security,dock,flight,civilian}.json` combining them with navy-recoloured base garments. The ten `authority_*` outfit entries now point at these sets (body still picks the masc/femme cut). Articles are free-drawn (no body fitting) — a fitting/tailoring pass is a later polish.
- [x] **Hub Control floor plan** — a west-east Approach Concourse spine with five overlapping bays (Records Hall, Control Gallery, The Berth, Lender's Office, Quartermaster's Dock), a central `authority_spire` landmark, ranked colonnade, `deck_grid` floor. Fully walkable; all NPCs reachable from the dock.
- [x] **Full NPC roster** (11, one flag-gated): Induction Officer Sella, Controller Vane, Signal Officer Doss (loan), Harbor-Master Crane (ships), Approach Warden Lund (outfits), Quartermaster Ellin (commodities), Deck-hand Rusk, Barkeep Ottre, Records Keeper Amsel, Deck Mechanic Prit, Displaced traveller (`requires_flag: beacon_verdance_lit`). Real dialogue trees on the key ones (Vane's `patron:` pledge, Amsel's shutdown-record hint, Ottre's faction gossip). Moon "Watch Station" gets 3 more.
- [x] **Anchor tutorial — "Harbor Authority Induction"** (`missions.json`, 12 stages): walk / target / talk / mission-log / possessions → loan → ship → board → turn / thrust / brake → **jump to Kiln** (`jumped_to:kiln`, a new generic gameplay-event flag). Started by Sella's dialogue (her `ambient` line prompts a new pilot); `on_start_flags` lights Kiln's beacon; Vane has a fallback for players who skip it.
- [x] **Halcyon pilots** — `ackley` (Controller Ackley, patrol), `pell` (Approach Officer Pell, courier), `lund` (Freight-Warden Lund), `voss` (Hauler Voss, relief), `rell` (Rell, free carrier) fleshed out in `pilots.json` with personality + hail lines; `halcyon.json` now flies five AI ships (2 patrol/courier, 2 hauler, 1 carrier). Other systems keep the Phase 3/4 scaffold roster until their slice.

### 6.2 — Kiln / Ninefold Combine  ✅ done — `docs/gen/gen_kiln.py`
- [x] Combine ships (heavy iron ingots), the blast-hub "Combine Hold" station, mine-moon, 3 blast-block buildings — all authored design JSON.
- [x] Combine Hold floor plan (concourse + Contract Hall / Assay Office / Ledger Dock / Ration Store / Cutters' Rest), 10-NPC roster + Shaft VII headworks roster, hail dialogue.
- [x] **Combine wardrobe** — `combine_{ration_plate,blast_pauldrons,hazard_bib,contract_seal,deep_hood}` + 5 `sets/combine_*.json` (command / security / dock / flight / civilian). The ration plate is the identity mark every kit carries.
- [x] Anchor mission **"combine_contract"** (6 stages, hostile-leaning — sign a contract, carry a sealed manifest to Shaft VII and back; `on_end_flags` lights Verdance). Factor Tol's threat branch → -45 rep.
- [x] Combine pilots (tolvic / raska / corran / molt); 4 AI ships in-system.

### 6.3 — Verdance / the Drift  ✅ done — `docs/gen/gen_verdance.py`
- [x] Drift ships (rounded pod hulls), the "Highcanopy" leaf-ring station, cloud-moon, 3 planted buildings — authored design JSON.
- [x] Highcanopy floor plan (Canopy Walk + Rolling Assembly / Seed Store / Ferry Slip / Water Office / Canopy Rest), 9-NPC roster + Undergarden roster, dialogue.
- [x] **Drift wardrobe** — `drift_{speaker_sash,leaf_mantle,grower_apron,woven_collar,militia_band}` + 5 `sets/drift_*.json`. Security is just the militia band over civilian dress (no uniform).
- [x] Anchor mission **"the_drift_assembly"** (4 stages, welcoming — gather three neighbours' views in person to force a vote; `on_end_flags` lights Ossuary + `act_pressure`).
- [x] Drift pilots (sella / nim / ost); 3 AI ships + the conditional Combine raider.

### 6.4 — Ossuary / the Vigil  ✅ done — `docs/gen/gen_ossuary.py`
- [x] Vigil ships (narrow vertical spears), the "Name-Wall" monolith station, grave-moon, 3 austere name-wall buildings — authored design JSON.
- [x] the Name-Wall floor plan (the Long Vigil + Long Vault / Reading Cells / Vault of the First Decade / Spare Stores / Refectory), 10-NPC roster + grave-yard roster.
- [x] **Vigil wardrobe** — `vigil_{mourning_stole,name_pendant,keeper_cowl,ash_sash,grave_apron}` + 5 `sets/vigil_*.json`. The stole + name-pendant are worn by every member, every day.
- [x] Anchor mission **"the_vigil_record"** (4 stages — read three sections of the wall + the inner Vault; the reason for the Silence stays a deliberate dialogue reveal (quarantine / scorched-earth / accident); `on_end_flags` lights the Span + `act_span`).
- [x] Vigil pilots (vane_watch / oskal / aen); 3 AI ships.

### 6.5 — The Span / the Wardens (Act I stub)  ✅ done — `docs/gen/gen_span.py`
- [x] Warden exterior/interior art authored: monumental smooth alloy hulls + teal core + hand-bolted salvage; "Hub Zero" broken-ring-arc station; ring-segment moon; 3 monumental arch buildings.
- [x] Minimal Hub Zero interior (5 rooms, 4 NPCs) carrying the **ending fork** (First Warden — restore / sever / hold-the-middle, each with a confirm step).
- [x] System stays **`locked` / `beacon_the_span_lit`** through Act I (star map "NO SIGNAL"); opens mid-Act II via `act_span` + standing.
- [x] Warden bespoke wardrobe **deferred to Act II** (the `warden_*` outfits stay a tuned `warden_dress` recolour); Warden pilots (segment_warden / threa) fleshed.

### 6.6 — Free carriers pass  ✅ done — `docs/gen/gen_carriers.py` (runs last)
- [x] Three patchwork carrier ship designs (`carrier_{courier,hauler,patrol}` — welded mismatched modules, cargo lashing, hand-painted name); light patched-depot buildings.
- [x] **Carrier wardrobe** — `carrier_{patch_vest,lash_belt,name_tag,deck_bib,run_band}` + 5 `sets/carrier_*.json`. Patchwork by design — the one wardrobe meant to read as scavenged across cultures.
- [x] A `free_carrier` AI ship + a berth NPC + berth dressing dropped into **every** system's station interior (idempotent, keyed by name); carrier pilot roster fleshed (rell/Ferro, ash, dume, sable).

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
