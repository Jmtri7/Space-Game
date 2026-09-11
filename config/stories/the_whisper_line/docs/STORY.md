# The Whisper Line

A short, linear 3-system story. A stranger bursts a data file to the
player's communicator from a long-missing friend (Elian Marr) and flees;
the file is a trail, decoding one segment at a time, that leads out past
the last beacon to Elian and a first-contact choice.

## Graphics

Re-uses existing art wholesale — no new assets:

- **Modules:** `orbital-std` (the `courier` ship, `trade_ring` station,
  `regolith_moon`, `orbital_std`/`regolith_std` cultures, the settlement
  building set — extracted 2026-09-11 from `graphics_pipeline_test`, which
  also lists it now), `figures-human` (bodies, wardrobe), `audio-core`,
  `ships-core`, `common-goods`, `story-defaults`. See
  [CONFIG_MODULES.md](../../../../docs/CONFIG_MODULES.md).
- Station interiors reuse the octagonal concourse polygon set from
  `graphics_pipeline_test/systems/proving_ground.json`; moon interiors reuse
  its Yard Flat plaza set.

## Structure

Player starts docked at **Kestrel Reach** with a `courier` and 3000 cr
(`story.json` `start`). No shop/loan onboarding — straight into the note.

| System | Gate | Key beats |
|---|---|---|
| `kestrel` | start | The Grey Courier NPC (NW-N arc, `facing: west`, `requires_not_flag` + `depart_flag` both `met_courier`) bursts the file (`the_note` item, in-fiction "Elian's Transmission") to the player's communicator via a handheld relay and `start_mission:follow_the_note`; ending the conversation sets `met_courier`, so they walk to the dock and vanish (`DepartRoutine`). The file is explicitly locked stage-by-stage (the courier's own line) — that's the in-fiction reason it decodes one segment at a time as the mission advances, delivered as Message Log entries, rather than being read whole in one dialogue page. Deck Officer Aru has a post-handover `conditional_root`. |
| `tessellate` | `unlock_flag: reach_tessellate` (set by `follow_the_note` `on_start_flags`), `unlock_silent` | Archivist Senna on the relay station gives the survey backstory, sets `met_archivist` + `reach_verge` (+ a `star_chart` item). |
| `verge` | `unlock_flag: reach_verge` (set by Senna) | Elian Marr on the moon. First node sets `found_elian` (completes the mission). Then a 2-way fork: `end_story:wake` / `end_story:let_sleep` → `endings.json`. |

Every system also carries a second body (Cinder Flat, Sift, Verge Marker) as
a one-NPC flavour stop alongside the one the mission actually sends you to —
purely a design choice, not an engine requirement (a system may omit either
body; see config-formats.md's systems/*.json note).

## Mission `follow_the_note`

Linear, 5 stages: `boarded_ship` → `jumped_to:tessellate` → `met_archivist`
→ `jumped_to:verge` → `found_elian`. Deliberately **not** gated on
`landed_on_landing_site` for the Tessellate/Verge docking beats — that flag
fires for *any* station/moon in the active system, so with an optional
second body in each system it would falsely complete on landing at the
wrong one; each landing stage is merged into the NPC stage that follows it
instead. Each stage's `one_way_message` is the next segment of the
transmission. `on_end_flags: note_arc_done`.

## Acts

`note` → `trail` (`met_archivist`) → `edge` — HUD label only.

## If you extend this

- No `factions.json` / `pilots.json` / `commodities.json` — add them if you
  introduce reputation, AI pilots, or trade.
- `endings.json` has no `faction_epilogue` (no factions). Add per-faction
  lines there if factions arrive.
- Bump `story.json` `version` on any change that changes what a save's flags
  mean (see [SAVE_SYSTEM.md](../../../../docs/SAVE_SYSTEM.md)).
