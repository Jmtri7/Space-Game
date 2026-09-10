# Deepening Act II & Act III — `the_long_silence`

> **Status:** ✅ ALL PHASES SHIPPED. Phase 1 `e85846f` / `0.13.0`; Phase 2 `0.14.0`;
> Phase 3 `0.15.0`; Phase 4 `0.16.0`; Phase 5 `0.17.0`. Act II & Act III now play through
> with combat, an escort, a reputation fork, the gated Choir sequence, and flag-keyed
> epilogues. Remaining work is playtest/balance (PLAN.md Phase 9).

## For the implementing agent — how to work this

- **Everything is content/config through the generators.** One small `game/ui/ending_screen.py`
  change in Phase 5b is the only engine edit; flag it clearly if you find you need another.
- **Generators** live in `config/stories/the_long_silence/docs/gen/`. Run order:
  `gen_halcyon → gen_kiln → gen_verdance → gen_ossuary → gen_span → gen_carriers → gen_act2`
  (last). Each `gen_<system>.py` **owns** its `systems/<id>.json` outright. `dispatches.json`
  and `endings.json` are **hand-maintained** (no generator).
- **After any `gen_*` re-run:** `git checkout HEAD -- config/stories/the_long_silence/graphics/articles/`
  — ~15 hand-polished article files revert on a full chain run otherwise. Everything else
  regenerates byte-identical.
- **`story.json` `version`** is set by `gen_halcyon.py` — bump it once per shipped phase and note
  it in the commit. New flags are all additive; old saves default them `False`, which is the
  correct pre-Act-II / pre-fork state.
- **Test baseline: 544 pass** (`python run_tests.py`). Each phase adds 3–8 targeted tests.
- **Commit + push each phase to `main` directly** (the PR rule is bypassed for this repo).
- There is often unrelated uncommitted work in the tree (sound, UI). Stage only your own files.

## Context

Act I plays end to end. Phases 7/8 landed the engine spine for the rest: the dispatch/inbox
system, two one-shot Act II courier missions, a Combine blockade over Verdance, the bespoke
Warden wardrobe, and a Hub Zero interior with the First Warden's three-way ending fork plus an
Archivist presenting the three shutdown-reason logs.

But the middle and end are **thin**. Act II ("Pressure" — STORY.md's "region deciding whether to
have a war") was the Ossuary anchor mission plus two courier runs that left no story trace, no
combat, no escort, no forking choice. Act III is a single room — you could walk into Hub Zero and
pick an ending cold, with no scene about *what is relighting the beacons* (STORY.md's central
question). This plan deepens both acts.

**Decisions taken:**
- **Signal origin stays a mystery, but the game reflects the player's own archive reading back at
  them.** Which of the three shutdown logs the player *lingers on* in the Archive shapes which
  reading of the signal the Core Voice leads with; the player leaves believing one, recorded as a
  `signal:*` flag. No canonical answer in the fiction.
- **The ending fork is gated** behind a new Act III mission (`the_core_choir`): read the archive →
  hear the Core → report to the First Warden. Her dialogue tree is restructured; the ending tests
  move to the gated node.
- **Full scope: Phases 1–5**, including the Ring Segment Four moon interior and the ~8-line
  `ending_screen.py` change for flag-keyed epilogue lines.

### Ground truth from exploration
- **Patron pledges already exist for four factions** — `harbor_authority` (Vane, Halcyon),
  `ninefold_combine` (`kiln.json`), `the_drift` (Sela, `verdance.json`), `the_vigil` (Aramis,
  `ossuary.json`), each on a `{"faction":<id>,"min":25,"node":"warm"}` conditional root; option
  gated `requires_not_flag: patron:<id>` doing `set_exclusive_flag:patron:<id>` +
  `adjust_rep:<id>:8`. **Only `free_carrier` has none** — that is the whole pledge gap (Phase 3c).
- **Escorts do NOT follow through a jump.** `_sync_escorts` only re-routines `ai_ship` objects
  already in the *active* system's `ai_ships`. Working pattern: a `requires_flag`-gated
  `ai_ships[]` entry for the escort in **every system it must appear in** (same flag), spawned on
  entry by `_sync_conditional_ships` — exactly like the `combine_mobilised` blockade pair.
- Dispatch gate keys (`content_gate` vocab: `requires_flag` / `requires_not_flag` / `requires_rep`
  / `requires_rep_below`) are **single-valued** — no AND of two `requires_flag` on one entry.
  Chain a sequence on `dispatch:<id>` or on story-progress flags that land in order.
- Dispatch throttle `DISPATCH_SPACING_FRAMES = 450` (~7.5 s); first eligible dispatch on a frame
  delivers immediately, the rest one per 450 frames; on load everything currently eligible is
  silently marked received.
- `ending_report` picks the faction line **only** by final standing band (`_band`: `<-25`
  hostile, `<25` neutral, else allied). No flag input until Phase 5b.
- Missions are strictly linear (monotonic int stage index, one advance per frame, no branch/skip).
  Generic stage `complete_flag`s with zero code: `jumped_to:<sys>`, `completed_jump`,
  `landed_on_landing_site`, `boarded_ship`, `hailed_pilot:<ExactName>`, plus interior
  `walked_interior` / `talked_to_npc` / `targeted_person` / `viewed_*`. No mining/"docked" flag.
- `reset_on_activation` on a stage: only for latching / accidentally-trippable flags (movement,
  menus, landing). NOT for deliberate one-offs (a hail, a dialogue accept) — resetting those
  strands the mission.

---

## Phase 1 — Act II reactivity plumbing  ✅ SHIPPED (`e85846f`, story `0.13.0`)

Landed as planned, with two deviations:
- The reactivation-front chain gates on **story-progress flags** (`beacon_ossuary_lit` /
  `act_span` / `jumped_to:the_span`), not `dispatch:<id>` + a second flag — `content_gate` can't
  AND two `requires_flag`, and these flags already come in story order.
- `vigil_warned` is always set by the time Keeper Aramis reaches his `done` node, so his line is
  **enriched unconditionally** rather than via a (dead) `conditional_roots` entry.

What shipped:
- **1a** — `carrier_relief_run` → `on_end_flags: ["relief_run_done"]`; `combine_evacuation` →
  `["evac_run_done"]` (`gen_act2.py`).
- **1b** — removed the duplicate `the_drift` key in `endings.json` `restore.faction_epilogue`.
- **1c** — new dispatches `relay_front_verdance` / `relay_front_ossuary` / `relay_front_span`
  (`dispatches.json`), each gated on the next system's unlock/act flag.
- **1d** — `conditional_roots` reactions wired for `authority_briefed` (Records Keeper Amsel,
  `gen_halcyon`), `carrier_contact` + `relay_front_kiln_seen` (the Verdance & Kiln carrier berth
  NPCs, `gen_carriers` via a new `BERTH_REACT` table), `span_hailed` (Warden of the Fourth
  Segment, `gen_span`), `vigil_warned` (Keeper Aramis `done` text, `gen_ossuary`).
- Tests +3 (`tests/test_dispatch.py::TestLongSilenceActTwoPlumbing`,
  `tests/test_missions.py` ending-matrix guard).

`read_hub_archive` (the sixth once-dead flag) is deliberately left for Phase 4.

---

## Phase 2 — Act II escort mission: the refugee barge (`escort_barge`)  ✅ SHIPPED (`0.14.0`)

Shipped as planned. Mission title **"Forty Families"**; pilot **Barge-mother Sethe**
(`barge_sethe`, `escort_flag: barge_under_escort`, `freighter_pilot` so she shuttles when not
escorting); the gated `Refugee Barge Highcanopy-Nine` `ai_ship` (`requires_flag:
barge_under_escort`) is appended to **both** Verdance (`gen_verdance.py`) and Ossuary
(`gen_ossuary.py`); offer dispatch **`drift_convoy_call`** (`gen` — hand `dispatches.json`,
gated `combine_mobilised` + `requires_rep: the_drift:6`). Stages: hail Sethe → jump to Ossuary →
land at the Name-Wall → jump back to Verdance. `on_end_rep {the_drift: 6, free_carrier: 4}`.
Tests +4 (`tests/test_missions.py::TestLongSilenceDeepening`).

Escort a Drift refugee barge Verdance → Ossuary past the Combine blockade; offered by dispatch
once the Combine has mobilised.

### New pilot — `gen_verdance.py` (`pilots.update`)
```
"barge_sethe": {
  "name": "Barge-mother Sethe", "faction": "the_drift", "role": "freighter_pilot",
  "escort_flag": "barge_under_escort",
  "personality": "Forty Drift families in the hold and no intention of arguing about it.",
  "hail_greeting": "Refugee barge Highcanopy-Nine, bound for Ossuary. We're slow and full. Stay close."
}
```

### Gated `ai_ships[]` in BOTH Verdance and Ossuary (escorts don't survive jumps)
Identical entry appended to `VERDANCE["ai_ships"]` (`gen_verdance.py`) and the Ossuary system
`ai_ships` (`gen_ossuary.py`):
```
{"name": "Refugee Barge Highcanopy-Nine", "x": 0.5, "y": 0.4,
 "ship_type": "drift_hauler", "pilot": "barge_sethe", "faction": "the_drift",
 "route": ["station", "moon"], "requires_flag": "barge_under_escort"}
```
Only the active system's ships tick/draw, so the two copies never both act. `_sync_hostiles`
skips `ship.escorting`, so the barge is safe while escorted and never fights.

### Mission — `docs/gen/gen_act2.py` (`ACT2` dict)

| # | text | complete_flag | reset | one_way_message sender |
|---|---|---|---|---|
| 0 | Meet the barge at Highcanopy and signal ready. | `hailed_pilot:Barge-mother Sethe` | — | Sela of Highcanopy |
| 1 | Hold escort to Ossuary — jump when the barge is with you. | `jumped_to:ossuary` | ✓ | Barge-mother Sethe |
| 2 | See the barge down at the Name-Wall. | `landed_on_landing_site` | ✓ | Barge-mother Sethe |
| 3 | Report back to the Drift — jump to Verdance. | `jumped_to:verdance` | ✓ | Sela of Highcanopy |

Mission keys: `escort_flag: "barge_under_escort"`, `on_start_flags: ["barge_under_escort"]`,
`on_end_flags: ["escort_barge_done"]`, `on_end_rep: {"the_drift": 6, "free_carrier": 4}`.
Stage 0's `hailed_pilot:` string must exactly match the pilot `name`.

### Escort-flag lifecycle (no engine change)
start_mission → `on_start_flags` sets `barge_under_escort` → next `_sync_conditional_ships`
(entry/launch) spawns the barge → `_sync_escorts` → `OrbitPlayerRoutine` → mission completes →
`_on_mission_end` auto-clears `escort_flag` → next `_sync_conditional_ships` culls the barge.
Abandon runs the same `_on_mission_end` — safe.

### Offer dispatch (hand, `dispatches.json`)
```
"drift_convoy_call": {
  "sender": "The Drift - Sela of Highcanopy",
  "subject": "A convoy, if you'll fly it",
  "body": "Forty families want out of the ring before the Combine finishes closing the lane. Fly cover to Ossuary and we will not forget it.",
  "requires_flag": "combine_mobilised",
  "requires_rep": "the_drift:6",
  "on_receive_flags": ["drift_convoy_offered"],
  "start_mission": "escort_barge"
}
```
Gate `combine_mobilised` (not `act_pressure`) → lands ≥1 spacing interval after the mobilisation beat.

### Files
`gen_verdance.py` (pilot + Verdance ai_ship), `gen_ossuary.py` (Ossuary ai_ship),
`gen_act2.py` (mission), `dispatches.json` (hand), `story.json` bump.

### Risks
- Two barge objects share a name — cosmetic; scope any uniqueness test per-system.
- Blockade turns hostile mid-escort if Combine standing already `<= -40` — intended pressure;
  escort is exempt, player can be shot.
- Player jumps before hailing Sethe → stage 1's `reset_on_activation` re-clears the latched
  `jumped_to:ossuary`; they jump again. Acceptable; stage-1 message explains it.
- Note: a recent commit gave `courier_pilot` a `ShuttleRoutine` (not idle) — the barge uses
  `freighter_pilot` + a `route`, so it moves normally when not escorting; confirm it settles
  into `OrbitPlayerRoutine` cleanly on flag-set.

---

## Phase 3 — Act II recon mission + reputation fork + carrier pledge  ✅ SHIPPED (`0.15.0`)

Shipped as planned. Mission **`front_recon`** ("Reading the Front", `gen_act2.py`) — 4 linear
stages (jump Kiln → pull the record off **Assay-clerk Dorn** at Combine Hold → jump Verdance →
deliver), `on_start_flags: ["front_recon_active"]` gating Dorn's hand-over option instead of the
(latching, useless) `jumped_to:kiln`. Fork: a delivery option on **Records Keeper Amsel**
(`front_to_authority`, +10 Authority / −4 Vigil), **Sela of Highcanopy** (`front_to_drift`, +10
Drift / +4 carrier), **Keeper Aramis** (`front_to_vigil`, +10 Vigil / −4 Authority), each on the
node the player actually lands on (`start`+`briefed` / `done`+`warm` / `done`+`warm`), gated
`front_recon_have_record` + `requires_not_flag: front_recon_delivered`. Fifth pledge
(`patron:free_carrier`) added to the **Verdance carrier berth NPC** via a `BERTH_PLEDGE` case in
`gen_carriers.py`'s berth builder (warm root + pledge option). Offer dispatch
**`carrier_recon_call`** (hand, gated `dispatch:carrier_open_hand`). Tests +5.

> **Note (pre-existing):** the Drift/Vigil `warm` pledge roots sit *after* their
> `<anchor>_done` flag root in `conditional_roots`, so a post-anchor player never lands on
> `warm` — the fork options were added to the `done` nodes too for that reason. Worth a
> dedicated fix (reorder faction roots first) but out of this phase's scope.

Carry the Kiln beacon's handshake logs, then choose who to hand them to.

### 3a. Mission `front_recon` — `gen_act2.py` (linear spine; fork is in the delivery dialogue)

| # | text | complete_flag | reset |
|---|---|---|---|
| 0 | Read the front's approach at the Kiln relay — jump to Kiln. | `jumped_to:kiln` | ✓ |
| 1 | Pull the beacon's own logs — land at Combine Hold, then talk to the pad clerk. | `front_recon_have_record` | — |
| 2 | Get the record to someone who'll act on it — jump to Verdance. | `jumped_to:verdance` | ✓ |
| 3 | Deliver the intelligence. | `front_recon_delivered` | — |

Keys: `on_end_flags: ["front_recon_done"]`. Stage 1's flag is set by a short dialogue on an
existing Combine Hold NPC (a pad clerk / Tallykeeper): option `action: set_flag:front_recon_have_record`,
gated `requires_flag: jumped_to:kiln` (so it only appears during the mission window). Stage 3's
`one_way_message` from "Relay Network": *"Three parties want this — the Authority at Hub Control,
the Drift at Highcanopy, the Vigil at the Name-Wall. Choose."*

### 3b. Forking delivery — three existing NPCs, no new ones
Add one delivery option to **Records Keeper Amsel** (Hub Control), **Sela** (Highcanopy),
**Keeper Aramis** (Name-Wall) — each already on a tree; put the option on the node the player
actually lands on post-anchor (`done` / `warm`). All gated
`requires_flag: front_recon_have_record` + `requires_not_flag: front_recon_delivered`:

| deliver to | actions |
|---|---|
| Authority (Amsel) | `set_flag:front_recon_delivered`, `set_flag:front_to_authority`, `adjust_rep:harbor_authority:10`, `adjust_rep:the_vigil:-4` |
| Drift (Sela) | `set_flag:front_recon_delivered`, `set_flag:front_to_drift`, `adjust_rep:the_drift:10`, `adjust_rep:free_carrier:4` |
| Vigil (Aramis) | `set_flag:front_recon_delivered`, `set_flag:front_to_vigil`, `adjust_rep:the_vigil:10`, `adjust_rep:harbor_authority:-4` |

`front_recon_delivered` completes stage 3. Keep `front_to_*` as plain flags (not
`set_exclusive_flag:patron:*` — delivering intel is not a lifetime pledge). They feed the Core
Voice colour (Phase 4) and ending epilogues (Phase 5b).

### 3c. The missing carrier pledge
Add the fifth pledge to the **carrier berth NPC at Highcanopy** (`gen_carriers.py` — the Verdance
berth NPC "Carrier off the Slip"; it already has a `dialogue_tree` from Phase 1d's `BERTH_REACT`).
Extend that tree to mirror the other four pledges:
```
conditional_roots (add): {"faction": "free_carrier", "min": 25, "node": "warm"}
warm node option (requires_not_flag: patron:free_carrier):
  "Pledge the carriers your lane." -> actions:
     ["set_exclusive_flag:patron:free_carrier", "adjust_rep:free_carrier:8"]
```
`set_exclusive_flag` keeps all five `patron:*` mutually exclusive; the First Warden's existing
`hold_middle` gate (`requires_not_flag: patron:harbor_authority`) is unaffected by a new sibling.
The Phase-1d `BERTH_REACT` builder in `gen_carriers.py` needs a per-system special case for
Verdance to emit the extra `conditional_roots` entry + `warm`/`pledged` nodes.

### Files
`gen_act2.py`; `dispatches.json` (hand — `front_recon` offer gated
`requires_flag: dispatch:carrier_open_hand`, NOT `act_pressure`); `gen_kiln.py` (pad-clerk
option); `gen_halcyon.py` (Amsel), `gen_verdance.py` (Sela), `gen_carriers.py` (Verdance berth
NPC → full pledge tree); `gen_ossuary.py` (Aramis); `story.json` bump.

### Risk
Natural dispatch stagger after this: `carrier_open_hand` (immediate on `act_pressure`) →
`combine_mobilises` (+450 f) → `drift_convoy_call` (+450 f after `combine_mobilised`) →
`front_recon` offer (+450 f after `dispatch:carrier_open_hand`).

---

## Phase 4 — Act III "Choir sequence" (`the_core_choir`)  ✅ SHIPPED (`0.16.0`)

Shipped as planned, all in `gen_span.py`:
- **4a** — the Archivist's three log "Enough." leaves now
  `set_exclusive_flag:archive:{quarantine,scorched,accident}` + `set_flag:read_hub_archive`;
  the top-level skip keeps just `read_hub_archive` (Core Voice then opens flat).
- **4b** — new NPC **the Core Voice** (`x:950,y:360`, `warden_official_masc`, in the Core Choir
  disc by the First Warden). Three readings — `person` / `ai` / `script` — cross-linked; `"Enough"`
  on any → `set_exclusive_flag:signal:<x>` + `set_flag:heard_the_signal`. `conditional_roots`
  lead: `archive:quarantine→ai`, `archive:scorched→person`, `archive:accident→script`, none→`start`.
- **4c** — mission **`the_core_choir`** (`missions` merge in `gen_span.py`): read Archive
  (stage 0, `reset_on_activation`) → hear the Core (`heard_the_signal`) → report
  (`core_choir_reported`). `on_start_flags:["core_choir_started"]`, `on_end_flags:["core_choir_done"]`,
  `on_start_rep:{the_wardens:3}`.
- **4d** — First Warden restructured: old `start` (the fork) → **`choose`**, keeping its
  `hold_middle` gates; new `start` directs you to the Archive/Choir and carries the
  `start_mission:the_core_choir` option (gated `requires_not_flag: core_choir_started`) plus a
  "tell her what you heard" option (`requires_flag: heard_the_signal` +
  `requires_not_flag: core_choir_done`) → `set_flag:core_choir_reported`, `next: choose`.
  `conditional_roots: [{"flag": "core_choir_done", "node": "choose"}]` opens straight on the fork
  after. The `confirm_*` "Wait." options now return to `choose`, not `start`.

No engine change; the ending tests don't drive the tree (they check `endings.json` / `ending_report`
only) so no retarget was needed. Tests +6.

Gate the ending fork behind: read the archive → hear the Core → report to the First Warden.
The signal origin is a mystery the game **reflects back** — the shutdown log the player lingers
on shapes which reading the Core Voice leads with.

### 4a. Rework the Archivist so each log is trackable — `gen_span.py` `HZ_NPCS`
Change each log node's **"Enough."** leaf from `set_flag:read_hub_archive` to:
```
"actions": ["set_exclusive_flag:archive:quarantine", "set_flag:read_hub_archive"]
```
(and `archive:scorched` / `archive:accident` on the other two nodes). The top-level `start`
"Enough." (skipped every log) keeps just `set_flag:read_hub_archive`. `set_exclusive_flag`
means whichever log you're reading when you stop becomes the single `archive:<reason>` flag.

### 4b. New NPC — the Core Voice, `gen_span.py` `HZ_NPCS`
In the Core Choir disc (near the First Warden, e.g. `x: 950, y: 360`), existing Warden outfit,
no new art. Deliberately parallel to the Archivist — three readings of *who is relighting the
beacons*, none confirmed:

- **person** — someone who lived through the shutdown, or their line, finishing it by hand.
  Someone who could be asked why. The console will not confirm it.
- **ai** — the Hub woke enough of its own mind to decide it should not be dark, and used the
  Wardens as its hands. Is it still the thing that was shut down?
- **script** — a 200-year-old restart routine reached its next scheduled step. Every meaning is
  ours, not its. The reading the Choir likes least.

`conditional_roots` leads on the reading that matches the archive log the player lingered on:

| archive flag | Core Voice opens on | (fiction link) |
|---|---|---|
| `archive:quarantine` | `ai` node first | the containment system itself, waking |
| `archive:scorched` | `person` node first | a combatant's line, completing the last order |
| `archive:accident` | `script` node first | the cascade had no author; neither does the restart |
| *(none — skipped)* | `start`, all three flat | player picks freely |

Optional extra `conditional_roots` colour on `front_to_authority` / `front_to_drift` /
`front_to_vigil` (one line each).

Every node cross-links to the other two; **"Enough."** on any of them:
```
"actions": ["set_exclusive_flag:signal:person" | "signal:ai" | "signal:script", "set_flag:heard_the_signal"]
```
So the player leaves believing exactly one, recorded as `signal:<x>`.

### 4c. Mission `the_core_choir` — `gen_span.py` (add a `missions` merge, like `gen_verdance.py`)

| # | text | complete_flag | reset | one_way_message |
|---|---|---|---|---|
| 0 | Read the Hub's own account of the shutdown — the Archivist, the Hub Archive. | `read_hub_archive` | ✓ | First Warden |
| 1 | Walk the Core Choir and hear what is relighting the beacons. | `heard_the_signal` | — | First Warden |
| 2 | Return to the First Warden. | `core_choir_reported` | — | First Warden |

Keys: `on_start_flags: ["core_choir_started"]`, `on_end_flags: ["core_choir_done"]`,
`on_start_rep: {"the_wardens": 3}`. Stage 0 `reset_on_activation` forces a fresh read in
Act III (the archive is Act-III-only anyway — the Span is locked until `beacon_the_span_lit`).

### 4d. Restructure the First Warden — `gen_span.py` `HZ_NPCS`
- Rename current `start` (the fork) → `choose`. **Keep** its `hold_middle` gates
  (`requires_rep: the_vigil:10`, `requires_not_flag: patron:harbor_authority`).
- New `start`: directs you to the Archivist, then the Core, then back. One option "Understood"
  → `action: start_mission:the_core_choir`, gated `requires_not_flag: core_choir_started` +
  `requires_not_flag: core_choir_done`.
- Second `start` option, `requires_flag: heard_the_signal` + `requires_not_flag: core_choir_done`
  → "Tell her what you heard" → `action: set_flag:core_choir_reported` (completes stage 2).
  Text can branch on `signal:*` via a follow-up node or `conditional_roots`.
- `conditional_roots: [{"flag": "core_choir_done", "node": "choose"}]` — after the sequence she
  opens straight on the fork.

### New flags & consumers (Phase 4)
`archive:{quarantine,scorched,accident}` → Core Voice root selection.
`read_hub_archive` → **now consumed** (mission stage 0).
`heard_the_signal` → mission stage 1 + First Warden second option.
`signal:{person,ai,script}` → First Warden line + ending epilogues (5b).
`core_choir_started` / `core_choir_reported` / `core_choir_done` → First Warden gating; `core_choir_done` opens `choose`.

### Files
`gen_span.py` (Archivist rework, Core Voice NPC, `the_core_choir` mission + merge, First Warden
restructure); `story.json` bump; **`tests/test_space_screen.py::TestActsAndEndings`** (they drive
the fork directly — retarget to the `choose` node or set `core_choir_done` first);
`tests/test_location_screen.py` layout test (new NPC on walkable floor, reachable from the ship portal).

### Risks
- First Warden restructure breaks the ending tests — land the test update in the same change.
- `start_mission` from dialogue does **not** deliver stage 0's `one_way_message` — the First
  Warden's `start` text carries the instruction instead.
- Hub Zero NPC count grows; First Warden and Core Voice both sit in the Core Choir disc — keep
  them from overlapping and re-run the layout test.

---

## Phase 5 — Ring Segment Four + flag-keyed ending epilogues  ✅ SHIPPED (`0.17.0`)

- **5a** — `core_moon()` in `gen_span.py`: Segment Four is now 4 rooms (Floor / salvage bay /
  Choir-hands' quarters / under the Signal-Mast) and 5 NPCs — Segment Warden Threa-kin (reacts
  to `signal:person|ai|script`, and `core_choir_done`), Core-hand Vess, Salvage-hand Bree,
  **Choir-hand Aud** (disagrees with whichever reading the player chose), Parts carrier Nend.
  The "run `hub_parts` out here" errand is a Threa-kin line + the existing Signal-Tender shop —
  no mission.
- **5b** — `ending_report()` (`game/ui/ending_screen.py`): a `faction_epilogue[<f>]` may carry
  `"flag:<name>"` keys; the first whose flag is set wins over the standing band. `endings.json`
  gained one `flag:` line per faction/ending where it earns its place — `front_to_*` in
  `restore`/`hold_middle`, `signal:*` for the Wardens in `sever`/`hold_middle`,
  `front_to_vigil` for the Vigil in `sever`. The three band keys are untouched.
- Tests +4 (Segment Four reachability, Threa-kin reactions, `flag:` line beats band, the
  full-matrix guard still holds).

---
### (original plan below)

### 5a. Flesh Ring Segment Four (content only, `gen_span.py` `core_moon()`)
Today: one `rect(220,260,1380,1100)` room, 2 flat NPCs (Segment Warden Threa-kin, Core-hand Vess).
- Split into 3–4 rooms using the existing `warden_hall` / `warden_housing` structures as dividers.
- Add 2–3 NPCs (a salvage-crew hand; a Choir-hand who *disagrees* with the reading the player
  chose; a parts carrier) — reuse Warden / carrier outfits, no new art.
- Give **Threa-kin** a `conditional_roots` branch on `signal:person` / `signal:ai` / `signal:script`
  (and/or `core_choir_done`) — the Wardens reacting to what the outsider decided the Hub is.
- Optional errand: "bring `hub_parts` to Segment Four" — handled entirely by the Signal-Tender's
  existing commodities shop (Hub Zero) + a Threa-kin acknowledgement line. No mission.

### 5b. Flag-keyed faction epilogue lines (~8 lines, `game/ui/ending_screen.py`)
In `ending_report()`, after `band` is chosen for a faction:
```python
entry = faction_epilogue.get(faction_id, {})
text = None
for key, val in entry.items():
    if key.startswith("flag:") and possessions.flags.get(key[5:]):
        text = val
        break
if text is None:
    text = entry.get(band)
```
A `faction_epilogue[<faction>]` may now carry `"flag:<name>": "<line>"` keys that win over band
keys when the flag is set. `_band` and every existing entry keep working. No save impact.

Then in `endings.json`, add flag lines keyed on the Phase-3/4 flags, e.g.:
- `restore.faction_epilogue.harbor_authority` → `"flag:front_to_authority": "runs the hub on intelligence you carried to them by hand, and credits you in the founding record."`
- `sever.faction_epilogue.the_wardens` → `"flag:signal:person": "let you break the core, because the one who woke it asked them to."`
- `hold_middle.faction_epilogue.the_wardens` → `"flag:signal:script": "tend a broken Hub a routine woke, and have stopped asking it why."`

Keep **at most one `flag:` key per faction per ending** (first-in-file wins). The
`test_every_ending_covers_every_faction_and_band` guard added in Phase 1 still expects the three
band keys present — `flag:` keys are additive, don't remove a band key.

### Files
`gen_span.py` (Segment Four); `game/ui/ending_screen.py` (5b); `endings.json` (hand, 5b);
`story.json` bump; `tests/test_space_screen.py::TestActsAndEndings` (assert a `flag:` line wins
when its flag is set, band line otherwise); layout test for Segment Four.

---

## Phase ordering

1. **Phase 1** ✅ — done.
2. **Phase 2** — depends only on `combine_mobilised` (exists). Independent of everything else.
3. **Phase 3** — its `front_to_*` flags feed 4 and 5b. Before 4.
4. **Phase 4** — soft dep on 3 (colour only). Riskiest edit (First Warden) — land it with the
   ending-test update.
5. **Phase 5** — 5a any time after 4; 5b any time (only `ending_screen.py` + `endings.json`).

Reorderable: 2 any time. Fixed: 3 before 4 (flags).

---

## Verification (per phase, from repo root)

1. **Regenerate + tests:**
   ```
   for g in halcyon kiln verdance ossuary span carriers act2; do \
     python config/stories/the_long_silence/docs/gen/gen_$g.py; done
   git checkout HEAD -- config/stories/the_long_silence/graphics/articles/
   python run_tests.py       # 544 baseline + your new asserts
   ```

2. **Headless checks** (`SDL_VIDEODRIVER=dummy python -c "…"`), using `tests.harness`:
   - Phase 2: Verdance state with `barge_under_escort` → `_sync_conditional_ships` spawns the
     barge, `_sync_escorts` gives it `OrbitPlayerRoutine`; clear the flag, re-sync → gone.
   - Phase 3: run `front_recon` to stage 3, set `front_recon_have_record`, open all three
     delivery NPCs → exactly one delivery option each; choose one → right flags + rep + complete.
   - Phase 4: force `act_span` + `beacon_the_span_lit`, enter Hub Zero → First Warden opens on
     `start` (not the fork); read `archive:scorched` via the Archivist; Core Voice opens on the
     `person` node; "Enough" sets `signal:person`; report back → re-enter → First Warden opens on
     `choose` with the fork; all three `end_story:*` still fire.
   - Phase 5b: `ending_report` with `ending:restore` + `flag:front_to_authority` → the flag line;
     without it → the band line.

3. **Interior-walk checks:** new NPCs on walkable floor, reachable from the ship portal —
   `tests/test_location_screen.py::TestLongSilenceStationLayouts` + `SDL_VIDEODRIVER=dummy`
   nav-grid build.

4. **Play-through (manual, per phase):**
   - II: finish the Drift assembly → confirm dispatches arrive spaced; the front chain trickles
     as you move outward; trigger `combine_mobilised`, fly the barge escort through the blockade,
     land at Ossuary, return; run `front_recon` and deliver to each party from separate saves.
   - III: arrive at the Span → Archivist (linger on one log) → Core Voice (opens on the matching
     reading) → report → fork opens → each ending fires; verify the chosen `signal:*` /
     `front_to_*` line shows in the epilogue.

5. **Docs in the same commits:** this file's Status line + phase markers;
   `config/stories/the_long_silence/docs/PLAN.md` Phase 7/8; `docs/architecture/config-formats.md`
   if the dispatch/mission vocab grows; `docs/SAVE_SYSTEM.md` for any new flag *category*; the
   `the-long-silence-story` memory file.
