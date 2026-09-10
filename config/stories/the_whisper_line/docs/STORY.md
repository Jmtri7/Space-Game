# The Whisper Line

A short, linear 3-system story. A stranger hands the player a note from a
long-missing friend (Elian Marr) and flees; the note is a trail that leads
out past the last beacon to Elian and a first-contact choice.

## Graphics

Re-uses existing art wholesale — no new assets:

- **Modules:** `figures-human` (bodies, wardrobe, the `courier` ship design,
  the `trade_ring` station design, the regolith settlement buildings),
  `audio-core`, `ships-core`, `common-goods`, `story-defaults`.
- **Catalogues copied verbatim from `graphics_pipeline_test`:** `graphics.json`,
  `cultures.json` (`orbital_std`, `regolith_std`), `building_types.json`,
  `ship_types.json` (`courier`). If those diverge upstream, re-copy or promote
  to a module.
- Station interiors reuse the octagonal concourse polygon set from
  `graphics_pipeline_test/systems/proving_ground.json`; moon interiors reuse
  its Yard Flat plaza set.

## Structure

Player starts docked at **Kestrel Reach** with a `courier` and 3000 cr
(`story.json` `start`). No shop/loan onboarding — straight into the note.

| System | Gate | Key beats |
|---|---|---|
| `kestrel` | start | The Grey Courier NPC (NW-N arc, `facing: west`, `requires_not_flag` + `depart_flag` both `met_courier`) hands over `the_note` and `start_mission:follow_the_note`; the "End Conversation" option on the note-contents node sets `met_courier`, so they walk to the dock and vanish (`DepartRoutine`). The note's full text is read in-dialogue. Deck Officer Aru has a post-handover `conditional_root`. |
| `tessellate` | `unlock_flag: reach_tessellate` (set by `follow_the_note` `on_start_flags`), `unlock_silent` | Archivist Senna on the relay station gives the survey backstory, sets `met_archivist` + `reach_verge` (+ a `star_chart` item). |
| `verge` | `unlock_flag: reach_verge` (set by Senna) | Elian Marr on the moon. First node sets `found_elian` (completes the mission). Then a 2-way fork: `end_story:wake` / `end_story:let_sleep` → `endings.json`. |

Every system carries both a station **and** a moon with a real (if minimal)
interior — the engine synthesises a phantom `LandingSite` with empty
`interiors` for any missing one, and landing on that crashes
(`main.py` "station" branch calls `station_interior.handle_input` on `None`).
The "extra" bodies (Cinder Flat, Sift, Verge Marker) are one-NPC flavour stops.

## Mission `follow_the_note`

Linear, 7 stages, all driven by generic gameplay-event flags
(`boarded_ship`, `jumped_to:<sys>`, `landed_on_landing_site`) plus the two
dialogue flags `met_archivist` / `found_elian`. Each stage's
`one_way_message` is the next line of the note. `on_end_flags: note_arc_done`.

## Acts

`note` → `trail` (`met_archivist`) → `edge` — HUD label only.

## If you extend this

- No `factions.json` / `pilots.json` / `commodities.json` — add them if you
  introduce reputation, AI pilots, or trade.
- `endings.json` has no `faction_epilogue` (no factions). Add per-faction
  lines there if factions arrive.
- Bump `story.json` `version` on any change that changes what a save's flags
  mean (see [SAVE_SYSTEM.md](../../../../docs/SAVE_SYSTEM.md)).
