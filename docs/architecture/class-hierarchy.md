# Class Hierarchy & Entity Design

Class hierarchy, composition relationships, and the runtime entity model. The
short project layout, shared helpers, and the WorldObject principle live in the
[ARCHITECTURE.md](../ARCHITECTURE.md) hub; config formats are in
[config-formats.md](config-formats.md).

## Class Hierarchy

### World Objects (Position + Drawing)
```
WorldObject (base — x, y, graphics, get_distance(), _draw_rotated_polygon())
├── Ship (physics, rotation; owns an Autopilot via composition)
└── LandingSite (space station or moon — config decides which)

Person (base — x, y, draw(), get_distance(), owns a Possessions)
```
There is no `AIShip`/`NPC` subclass anymore - every non-player character
(ship-flying or not) is a `Character` (`game/world/character.py`), which
*composes* a `Person` and, optionally, a `Ship` - it never inherits `Ship`,
exactly like `PlayerController` already didn't. A `Character` with no ship
(any station/moon NPC) is just a body with a role; one with a ship (an AI
pilot) is that same body plus the ship it flies. See "Character: AI Pilots
& NPCs" below.

Every `Person` — the player's own body (`PlayerCharacter`/`PlayerController.person`),
every `Character`'s `person`, and an AI pilot's `Character.person` — owns a
`Possessions` (credits, owned ships, loans) by composition, not just the
player. The player's one real `Possessions` object is shared by reference
across `SpaceScreen` and every `LocationScreen` (see
`SpaceScreen.get_interior_screen`'s `player_possessions` injection) so a
purchase in one location is instantly visible everywhere else.

`PlayerController` does **not** subclass `Ship` — it *owns* one (composition) and
exposes `x`/`y`/`velocity_x`/`velocity_y`/`angle`/`autopilot_active`/`autopilot_target`
as delegating properties for backward compatibility, plus `handle_input()` for
WASD/arrow control. `Character` mirrors this exact property list (only
meaningful when it has a ship) so both duck-type as a flyable ship the same
way for `SpaceScreen`/autopilot code.

### Screens (State Machine)
```
ScreenBase (implicit interface: handle_input/update/draw/get_state/restore_state)
├── SpaceScreen     — flight & exploration (owns player, AI ships, station, moon)
└── LocationScreen  — generic interior/exterior location, config-driven
                       (used for BOTH the station interior and moon locations)
```
Menus and dialogs don't extend `ScreenBase`. They extend `MenuBase`
(`game/ui/menu_base.py`) or its subclass `DialogBase`. Neither draws a
Controls pane - every modal shows its actions as `draw_button` widgets in
its own panel (mouse + Tab/arrow + Enter). A **menu** you dwell in
(`BackdropMenu`, `PauseMenu`, `SaveBrowser`, `ShopMenu`, `OutfittingMenu`,
`ShipBrowserMenu`, `ReportMenu`, `StarMap`); a **dialog** closes on any pick
(`ConfirmDialog`, `PilotNameDialog`, `ChoiceDialog`). Each implements
`handle_input()` + `draw_content()` + `buttons()` + `panel_rect()`, driven
directly by the main loop. `BackdropMenu` covers the old `Menu`/`StorySelector`;
`ChoiceDialog` the old `LocationSelector`/`ExitMenu`; `ReportMenu` (+ a
builder fn) the old `PossessionsMenu`/`MissionLog`; `SaveBrowser(mode=...)`
the old `LoadMenu`/`SaveDialog`. See [DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md)'s
"Menu vs. Dialog" and [UI_FLOW.md](../UI_FLOW.md) for the full state machine.

### Supporting Classes
- `StarField` — Procedural star generation with seeded randomness
- `Dialogue` — Conversation tree used by any character with a `person.dialogue`
  (or `person.hail_dialogue` - see Character below): nodes of text + options,
  each option either advancing to another node, closing (`"next": null`), or
  carrying one or more actions (`"action": "..."` or `"actions": [...]`, see
  `option_actions()`) applied via `apply_shared_actions()` (`"set_flag:<name>"`,
  `"give_item:<id>"`, `"spend_credits:<amount>"`, `"adjust_rep:<faction>:<delta>"`,
  `"light_beacon:<system_id>"`, `"set_exclusive_flag:<group>:<name>"` (sets one
  `<group>:*` flag, clears the rest - a one-time allegiance / fork choice),
  `"end_story:<id>"` (sets `story_over` + `ending:<id>`; `main.py` hands off to
  the `EndingScreen`) - generic, work from any screen) and/or, for a few commerce-flavored station NPCs,
  `LocationScreen._apply_dialogue_action()`'s own `"buy_ship:<id>"`/
  `"take_loan"` against the player's `Possessions`, or `"open_shop"` (an NPC
  that carries *both* a `dialogue_tree` and a `shop` opens the conversation on
  T - not the store directly - and an `"open_shop"` option in the tree closes
  it and switches to that NPC's store; see `LocationScreen.handle_input` /
  `_choose_dialogue_option` / `person.shop_via_dialogue`). An option can also carry
  `"requires_flag"`/`"requires_not_flag"` (a `Possessions.flags` name) -
  `current_options(flags, reputation)` drops it from the list entirely until
  that condition is met, for a conversation option that shouldn't be hinted at
  before then. `"requires_rep"` / `"requires_rep_below"` (`"<faction>:<n>"`) gate
  an option on faction standing the same way. `"conditional_roots"` lets a fresh
  conversation open on a different node once a flag is set or a faction standing
  is reached (`resolve_root(flags, reputation)`) - e.g. a friendlier greeting
  after a past kindness, a colder one for an enemy faction. `Dialogue.from_flat()` builds
  the simple one-node shape most NPCs still use. See [CONTROLS.md](../CONTROLS.md)'s
  Dialogue and Hailing sections.
- `Possessions` — credits/owned ships/loans/cargo/items, `flags`
  (`{name: True}` story-progress markers Dialogue's `requires_flag`/
  `conditional_roots`/`"set_flag:"` read and write - see above),
  `reputation` (`{faction_id: int}`, -100..+100 - the player's standing with
  each `factions.json` faction; `adjust_reputation()` clamps, `reputation_with()`
  defaults absent factions to 0; set by `"adjust_rep:"` / mission
  `on_start_rep`/`on_end_rep`, read by Dialogue's `requires_rep` and the
  Possessions report's Standing section),
  `missions`/`completed_missions` (mission/stage progress - see below), and
  `message_log` (received one-way hails, newest first - `add_message()`
  inserts at the front, capped at `MESSAGE_LOG_MAX` - rendered by the
  Space View's bottom-left **Message Log** pane, `ui_theme.draw_message_log()`,
  which has a fixed max height and mouse-wheel scrolling
  (`SpaceScreen.message_log_scroll`) for the overflow - as does the
  top-right targeting/info pane, `draw_info_panel()` /
  `SpaceScreen.info_panel_scroll`),
  composed onto every `Person`
- `game/world/mission.py` (functions, not a class - an intentional One Class
  Per File exception, see "Project Layout & File Conventions" in the hub) —
  mission/stage tracking:
  `start_mission()` begins a mission (config from `missions.json`, via
  `get_missions()`) at its first stage on `Possessions.missions`;
  `check_mission_progress()` (called every frame from
  `SpaceScreen.update_physics()`) advances a stage once its
  `"complete_flag"` is set in `Possessions.flags` - the *same* flag
  vocabulary Dialogue's `requires_flag`/`"set_flag:"` use, so a stage can
  be completed by a dialogue choice or a gameplay event alike - and moves
  a mission into `completed_missions` once its last stage completes.
  `start_mission()` sets every flag in the mission's `"on_start_flags"`
  list (mirror of `"on_end_flags"` - e.g. `first_flight` sets
  `"kade_escorting"` so Kade falls in alongside the player the instant the
  tutorial begins, not only once they accept his offer).
  `abandon_mission()` (wired up as the `"abandon_mission:<id>"` dialogue
  action - see `apply_shared_actions`) drops a mission without completing
  it, for a dialogue option letting the player decline. Both finishing and
  abandoning run `_on_mission_end()`: clears the mission's `"escort_flag"`
  (see `person.escort_flag` above) and sets every flag in its
  `"on_end_flags"` list (e.g. so a re-hailed pilot's `conditional_roots`
  can stop re-offering the same mission). A stage can also carry a
  `"one_way_message"` (`{"sender": ..., "text": ...}`) - not delivered by
  this module (kept pygame/UI-free on purpose), but `start_mission()`/
  `check_mission_progress()` return which `(mission_id, stage_index)`
  pairs just became active so `SpaceScreen._deliver_stage_message()` can
  look up and post each one via `_post_message()` (shared with
  `_check_one_way_hails()`'s proximity-triggered hails - both show a
  transient banner and log to `Possessions.message_log`).
  `mission_status_lines()` is the display data the mission `ReportMenu`
  (`report_menu.mission_report()`, opened with N) renders - it shows
  completed and current stages only, hiding stages the player hasn't reached
  yet. `SpaceScreen` also flashes a
  transient toast (`_show_toast()`, distinct from `_post_message()` - no
  Messages-log entry) on mission start, stage completion, and mission
  finish, alongside the jump-completion toast - all rendered by
  `ui_theme.draw_glow_message()` in a glass pane (shared with the one-way
  hail banner and the "too close to jump" warning; the toast stacks below
  whichever banner is showing). `story.json`'s `"starting_mission"` names which
  mission (if any) auto-starts; `"starting_mission_trigger"` picks when -
  `"ship_purchase"` (default, the first time a pilot buys a ship) or
  `"new_game"` (as a fresh game starts). Either way, if the player is
  docked at that moment the mission is only *armed*
  (`_on_ship_purchased()` / `begin_new_game()` set a
  `"starting_mission_armed"` flag); it actually starts - toast, first
  one-way hail, escort - on the next launch (`SpaceScreen.board_ship()`,
  called from main.py's interior->space transitions and every `update()`
  frame), so the opening beats land in the cockpit rather than the
  station bar. A story that grants a starting ship (`story.json`'s
  `"start"` block) gets `"new_game"` behaviour automatically since no
  purchase happens. `SpaceScreen`/`PlayerController`/`LocationScreen` also
  set a fixed set of generic, story-agnostic **gameplay-event flags** so a
  story's missions.json can use them as `"complete_flag"`s with no code
  change - this is the vocabulary a new tutorial is limited to:

  | flag | set when | set by |
  |---|---|---|
  | `used_turn` | rotate the ship (either direction) | `PlayerController` |
  | `turned_left` / `turned_right` / `turned_both_ways` | rotate left / right / both since the flags were last cleared | `PlayerController` |
  | `used_brake` | press brake/reverse | `PlayerController` |
  | `used_thrust` | thrust forward | `SpaceScreen.update_physics` |
  | `braked_below_threshold` | speed drops below `brake_slow_threshold` after thrust+brake | `SpaceScreen.update_physics` |
  | `used_ships_target_mode` | cycle targeting to SHIPS | `SpaceScreen._cycle_target_mode` |
  | `used_autopilot_on_ship` | engage autopilot toward a ship | `SpaceScreen` |
  | `landed_on_landing_site` | land at a station/moon | `SpaceScreen._check_landing` |
  | `completed_jump` | finish a jump (any destination, self-jump included) | `SpaceScreen._complete_jump` |
  | `jumped_to:<system_id>` | finish a jump into that specific system | `SpaceScreen._complete_jump` |
  | `viewed_mission_log` | open the Mission Log (3) | `SpaceScreen` |
  | `hailed_pilot:<name>` | hail a specific pilot | `SpaceScreen._start_hail` |
  | `bought_ship` / `bought_ship:<type>` | buy a ship (either purchase path) | `LocationScreen.buy_ship` |
  | `boarded_ship` | actually launch into space (docked → flying) - use this, not `bought_ship`, for a "board your ship" step that must wait for the undock | `SpaceScreen.board_ship` |
  | `took_loan` | take a loan | `LocationScreen._apply_dialogue_action` |

  Dialogue can also set arbitrary flags with `"set_flag:<name>"`, so a
  conversation choice is the escape hatch for any event not in this list.
  Several of these latch permanently once the player has ever
  done the thing, so a step in a mission that walks through them one at a
  time (`first_flight`) sets `"reset_on_activation": true`:
  `_reset_stage_flags()` then forces that stage's `"complete_flag"` (plus
  any names in its optional `"reset_flags"` list - for a step whose
  completion is derived from a *different* latching flag, like the braking
  step's `used_brake`) back to `False` the moment that stage becomes
  active (all such stages at `start_mission()`, the newly-active one again
  on each advance), so the step can't be satisfied by an action taken
  before it was the current instruction. Only opt in a step that latches
  or that the player can trip early by accident (opening the Mission Log,
  landing) - never one completed by a one-off deliberate choice (hailing a
  pilot, accepting an offer): a hail freezes mission progress, so "hail
  Kade" and "accept his offer" can both land before the next
  `check_mission_progress()`, and resetting the later flag as its stage
  activates would strand the mission. A mission-level
  `"reset_stage_flags_on_activation": true` is the per-stage default for
  any stage that doesn't say. See [CONTROLS.md](../CONTROLS.md)'s Mission Log section
  and `config/stories/default/missions.json`'s `"first_flight"` for a
  worked example.
- `Autopilot` — flight computer owned by a `Ship` (see Ship Class section below)
- `CentralStar` — ambient `WorldObject` (non-interactive, can't be landed on)
- `Asteroid` — ambient `WorldObject`, but not purely decorative: it can be
  shot and mined (see [combat-and-mining.md](combat-and-mining.md))
- `game/perf_metrics.py` — `PerfMetrics` + a shared `metrics` instance and
  `draw_overlay()` (module-level, same shared-instance rationale as
  `utils.Camera`). `main.py`'s loop calls `metrics.record()` once per frame
  with per-phase timings; `with metrics.span("...")` times hot sub-sections
  in `SpaceScreen`/`LocationScreen`. Recording is always on; the bottom-left
  overlay is drawn only when `constants.DEBUG_MODE`. See
  [UI_FLOW.md](../UI_FLOW.md#frame-timing-metrics).
- `game/audio/sound_board.py` — `SoundBoard` + a shared `sound_board` instance
  (same shared-instance rationale as `metrics`). Runtime-synthesized UI/
  notification sounds (no asset files); `sound_board.play("ping")` on every
  menu button press and received message, `"blip"` on target cycling, `"confirm"`
  on engaging autopilot. Silent no-op when the mixer can't start.
- `game/audio/music.py` — `MusicPlayer` + a shared `music` instance. Two
  procedurally generated seamless ambient loops (`menu` / `ingame`), rendered
  on a background thread. `main.py` calls `music.set_scene(current_screen)`
  each frame; it crossfades between the two. **Ctrl+M** (global, in `main.py`)
  mutes both modules. See [SOUND.md](../SOUND.md).

## Ship Class: Movement & Rotation

**Base Class: `Ship(WorldObject)`**
- Stores: `x`, `y`, `angle`, `velocity_x`, `velocity_y`, `thrust`, `space_drag`
- Physics: `acceleration_magnitude`, `max_velocity`, `rotation_speed`
- Owns an `Autopilot` (see below) via `self.autopilot = Autopilot(self)`
- Methods:
  - `draw(surface, ship_size, color)` — rotated polygon (via `_draw_rotated_polygon`) + thruster flames
  - `update()` — runs `self.autopilot.update()`, then thrust/drag/velocity-cap physics
    (the world is open/unbounded — no screen-wrapping; see [PHYSICS.md](../PHYSICS.md))
  - `engage_seek(target)` / `engage_orbit(center_x, center_y, radius)` — thin pass-throughs
    to the owned `Autopilot`
  - `autopilot_active` / `autopilot_target` — backward-compatible properties mirroring
    `self.autopilot.active` / `self.autopilot.target`

**Component: `Autopilot`** (in `autopilot.py`, one per `Ship`, composition not inheritance)
- Two standardized modes: `"seek"` (approach `target`, arrive once close and slow enough —
  the unified controller that redirects AND decelerates simultaneously) and `"orbit"`
  (continuously circle a fixed point at a fixed radius; never arrives)
- Talks to its ship only through kinematic reads and `turn_left()`/`turn_right()`/
  `increase_thrust()`/`release_thrust()` — see [PHYSICS.md](../PHYSICS.md) for the controller math

**Wrapper: `PlayerController`**
- Owns a `Ship` instance, translates WASD/arrow keys into `turn_left()`/`turn_right()`/
  `increase_thrust()`/`point_to_reverse_velocity()`/`release_thrust()`
- Blocks input while `autopilot_active` is true
- Applies `ship_type` stats (`max_thrust`/`max_velocity`/`rotation_speed`) to its `Ship`
  at construction, same as `Character.for_ai_pilot()` does

**Composition: `Character`** (`game/world/character.py`) — see the full
section below; the AI-pilot equivalent of `PlayerController`. Built via
`Character.for_ai_pilot(...)`, which reads `acceleration_magnitude` (from
`ship_type`'s `max_thrust`), `max_velocity`, `rotation_speed` from a
`ship_type` dict (see `config/stories/{story}/ship_types.json`), falling
back to defaults if none given. Its `update()` never touches ship physics
directly — it runs the role's routine each frame (a config `"routine"` key
naming a `ROUTINE_REGISTRY` entry wins outright; else `FACTION_ROUTINE_OVERRIDES`,
then `ROLE_ROUTINES` keyed by the pilot's role, then `IdleRoutine`),
which calls `engage_seek()`/`engage_orbit()` (delegated to the owned
`Ship`), then `self.ship.update()` runs the real `Ship`/`Autopilot` physics.

For adding a ship type, see [config-formats.md](config-formats.md#adding-or-updating-a-ship-type).
Only subclass `Ship` when you need genuinely new *behavior*, not new stats -
and prefer composing one onto a `Character`/`PlayerController`-style wrapper
(as both already do) over subclassing it at all.

## Person Class: Bodies & Drawing

**Base Class: `Person`**
- Stores position, appearance, an `outfit`, and a `Possessions`
- Implements `draw(surface)` — a face-on foot-to-head stack (two boots, two
  legs, a tapering torso with an arm per shoulder, a head), with the outfit's
  colors and accessory pieces drawn over the shared body shape (see below).
  The silhouette + every accessory piece is **data** in
  `game/world/person_figure.py` (frozen hand-maintained source — see
  [DESIGN_ATLAS.md](../DESIGN_ATLAS.md)); `draw()` resolves colour tokens per
  outfit, applies the walk transform per animation group, and blits — it has
  no body geometry of its own. A story whose `outfits` entry names a pipeline
  body (`{body, set, palette}`) instead renders through
  `game/graphics/story_assets.py` + `expand()` — see
  [GRAPHICS_PIPELINE.md](../GRAPHICS_PIPELINE.md).
- Provides `get_distance(x, y)` for interaction checks
- Owns the shared **walk cycle**: `step_toward()` → `_advance_walk()` advances
  `walk_phase` by the distance walked and ramps `walk_intensity`; `draw()`
  eases `walk_intensity` back to 0 on idle frames, so the legs swing/lift and
  the body bobs while any of the player / `WanderRoutine` / `DockRoutine` is
  moving them, then settle to a neutral stance. `WALK_*` constants tune it.

`outfit` is a resolved `graphics.json` "outfits" asset (see
`get_graphics_asset(story, "outfits", outfit_id)`), same pattern as ship/
station graphics. The player and AI pilots wear the story's
`default_outfit` (`"space_suit"`); a station/moon NPC wears whatever its
config's `"outfit"` field names, falling back to `default_outfit`. The
default story ships ~34 outfits in `graphics.json` — culture standards
(`vherathi_hardsuit`, `drossholt_coveralls`, …), role suits
(`flight_suit`, `security`, `mechanic`, `bartender`, `medic`, …), and
decorated variants (`marshal`, `vherathi_honor_guard`, `merchant_prince`,
…).

Every outfit key is just a color. `helmet_color` / `suit_color` /
`boot_color` / `leg_color` / `sleeve_color` recolor the base body (helmet
optional; `leg_color` defaults to a darker shade of the suit, `sleeve_color`
to the suit). Optional accessory keys each switch on one layered figure
piece (`fig.ACC[key]`): behind the body — `backpack_color`, `spike_color`
shoulder spikes, `antenna_color`; over the torso — `chest_plate_color`,
`sash_color` diagonal band, `collar_color`, `belt_color` + shaded buckle,
`shoulder_color` pauldrons, `badge_color` chest diamond; `visor_color` is a
face band that replaces the eyes. An absent key just skips that piece, so a
bare `Person` shows plain body colors and **a new decorated outfit is still
only a `graphics.json` entry — no drawing-code changes.**

`Person` itself has no behavior/role concept - that lives on `Character`
(see below), which owns a `Person` rather than subclassing it. Local NPCs
are built by `LocationScreen._build_local_character()`: a `Person` (with a
`Dialogue` attached), wrapped in a `Character` with `ship=None`.

## Character: AI Pilots & NPCs

**Class: `Character`** (`game/world/character.py`) - composes a `person`
(`Person`, always) and an optional `ship` (`Ship`, only for AI pilots), plus
a `role` string and the `Routine` that role picks. This is the *one*
mechanism behind every non-player character in the game:

- **AI ship pilots** (`ship` set): built via `Character.for_ai_pilot(...)`
  from `SpaceScreen._build_system_state()`. Role comes from `pilots.json`
  (`freighter_pilot`, `patrol_officer`, `explorer`, ...). Also gets a second,
  separate `person.hail_dialogue` (a `Dialogue`, from `pilots.json`'s
  `"hail_dialogue_tree"`/`"hail_greeting"`/`"hail_dialogue_options"`, falling
  back to their ground `personality` line otherwise) for `SpaceScreen`'s "H"
  hail control - a pilot mid-flight is a different context than the same
  person walking around a concourse, so the two can read completely
  differently. `person.one_way_hail` (optional, from `pilots.json`) is a
  pilot who hails the player first, once, on proximity - see
  `SpaceScreen._check_one_way_hails()` and [CONTROLS.md](../CONTROLS.md)'s Hailing
  section. `person.escort_flag` (optional, from `pilots.json`) names a
  `Possessions.flags` entry that puts this pilot into `OrbitPlayerRoutine`
  (`orbit_player_routine.py` - continuously re-`engage_orbit()`s around a
  moving target, typically the player, so the escort circles nearby rather
  than parking on top of them) instead of their normal role routine for as long
  as that flag is set, and back via `Character.set_routine()` +
  `resolve_routine_class(role, faction)` once it's cleared - see
  `SpaceScreen._sync_escorts()`. A mission can set/clear that flag itself
  (see `Mission` below) to have an NPC escort the player for its duration,
  e.g. Kade Marsh walking the player through `first_flight`.
- **Station/moon NPCs** (`ship=None`): built inline by `LocationScreen`.
  Role comes from each `npcs[]` entry's `"role"` in the location's config
  (`bartender`, `guard`, `resident`, ...), defaulting to `"resident"` if
  omitted. An entry can also carry `"escort_flag"` (interior mirror of the
  pilot key above - `LocationScreen._sync_npc_escorts()` swaps the NPC into
  `FollowPlayerRoutine` while the flag is set) and `"ambient"`
  (`{"message", "range"}` - a line the NPC drops into the shared Message
  Log once, on proximity, via `LocationScreen._check_npc_ambient()`, the
  on-foot counterpart to a pilot's `one_way_hail` - only checked for the
  interior the player is actually standing in (`update_physics(player_present=True)`,
  set by `update()`), since a docking AI pilot can build+cache any
  system's station interior in the background and its ambient NPCs would
  otherwise greet the player against a default spawn position). A dialogue option's
  `"start_mission:<id>"` / `"abandon_mission:<id>"` action (see
  `apply_shared_actions`) lets an NPC kick off or drop a mission - e.g.
  Sela Cordova offering the `station_tour` walkthrough.

`ROLE_ROUTINES` (in `character.py`) maps every role, ship-flying or not, to
a `Routine` class - the same table, the same lookup, regardless of whether
that routine flies a ship or just moves a body around a room:

| Routine | File | Needs a ship? | Used by |
|---|---|---|---|
| `DockRoutine` | `dock_routine.py` | Yes | `freighter_pilot` - fly to a stop, walk in, talk, walk out, repeat |
| `ShuttleRoutine` | `shuttle_routine.py` | Yes | `trader_captain` - ping-pong stops, instant turnaround |
| `OrbitRoutine` | `orbit_routine.py` | Yes | `patrol_officer` - circle a fixed point forever |
| `ExplorerRoutine` | `explorer_routine.py` | Yes | `explorer` - jump to a random *other* system, orbit something there a while, repeat |
| `IdleRoutine` | `idle_routine.py` | No | default for any role with no entry - never moves |
| `WanderRoutine` | `wander_routine.py` | No | `resident`/`traveler`/`roommate` - amble near spawn |
| `StationaryRoutine` | `stationary_routine.py` | No | `bartender`/`guard`/`ship_salesman`/`loan_officer` - stand still |
| `OrbitPlayerRoutine` | `orbit_player_routine.py` | Yes | Not in this table/`ROLE_ROUTINES` - a scripted, temporary override via `Character.set_routine()` (see `person.escort_flag` above), not a role pick; circles a moving target at a fixed radius |
| `CombatRoutine` | `combat_routine.py` | Yes | Not in this table/`ROLE_ROUTINES` - a scripted override via `Character.set_routine()`, swapped in by `SpaceScreen._sync_hostiles()` when a pilot turns hostile (see [combat-and-mining.md](combat-and-mining.md)). Drives the ship low-level (no autopilot); sets `character.firing` |
| `FollowPlayerRoutine` | `follow_player_routine.py` | No | Not in this table/`ROLE_ROUTINES` - the on-foot counterpart to `OrbitPlayerRoutine`; a scripted override that trails a moving target (the player) at a polite distance, wall-sliding via `character.can_move_to`. Driven by an interior NPC config's `"escort_flag"` through `LocationScreen._sync_npc_escorts()` (the mirror of `SpaceScreen._sync_escorts()`) - e.g. Sela Cordova walking the player through Alpha Station for the `station_tour` mission |

Every `Routine` implements the same two methods regardless of which table
row it's in: `start(character)` (once, at construction) and
`run(character)` (every frame). A ship-flying routine calls
`character.engage_seek(...)`/`character.autopilot_active` (delegated to
`character.ship`); a local routine only ever touches `character.person.x/y`
directly - never both, since a `Character` only ever gets one *kind* of
routine (whichever its role maps to).

`Character.update()` runs the routine, then (only if `self.ship` is set)
steps the ship's physics and mirrors `person.x/y` to it - unless
`self.ashore` is `True`, meaning `DockRoutine` currently has the person
walking around a station/moon interior independent of the (parked) ship.

`ExplorerRoutine` needs `character.systems` (the same `system_id ->
SystemState` dict `SpaceScreen` owns, passed straight through by
`Character.for_ai_pilot(systems=..., system_id=...)`) and
`character.system_id` (which system's `SystemState.ai_ships` list
currently holds it) to travel: "jumping" is just removing itself from one
system's list and appending to another's, then repositioning - see
`explorer_routine.py` and "Multi-System Simulation" below for why that's
enough (every system reuses the same game-space coordinates, and only the
active one is ever drawn/given a camera).

## LandingSite: Stations & Moons

**Class: `LandingSite(WorldObject)`**
- One class, two visual modes — decided at construction by inspecting `graphics`:
  `is_station = "rotation_speed" in graphics or graphics.get("shape") in ["hexapod", "octagon"]`
- Station mode: rotates (`rotation_speed`), drawn as a polygon with a glowing core
- Moon mode: static circle with craters
- `landing_distance` — how close the player must get (and how slow) to land
- `interiors` — dict of location keys → interior config (file path or inline dict),
  consumed by `LocationScreen` when the player lands

The interior config format and interior geometry rules are in
[config-formats.md](config-formats.md#interior-layout).

## SpaceScreen Responsibility

**`SpaceScreen` contains:**
- `PlayerController` (controlled entity, the only thing not scoped to one system)
- `self.systems`: `system_id -> SystemState` for *every* system the story
  defines (see "Multi-System Simulation" below) - `self.station`, `.moon`,
  `.ai_ships`, `.central_star`, `.celestial_bodies`, `.star_field`, and
  `.asteroid_field` are just aliases onto `self.systems[self.system_id]`'s
  own objects, kept in sync by `_activate_system()`

**`SpaceScreen` provides:**
- `update()` — advance all entity physics, recenter camera, auto-land when autopilot arrives
- `draw()` — render entities, target brackets/label/arrow, HUD
- `handle_input()` — targeting (T), landing/autopilot engage (L), pause (ESC)
- `get_state()` / `restore_state()` — capture/restore player + every AI ship
  in every system for save [see SAVE_SYSTEM.md](../SAVE_SYSTEM.md)

**Why this design:**
- Clear separation of concerns
- Easy to pause/resume game state
- Simple to add new entity types (extend and add to update/draw)

## Multi-System Simulation

**Class: `SystemState`** (`game/world/system_state.py`) - one system's
`station`, `moon`, `central_star`, `celestial_bodies`, and `ai_ships`.
`SpaceScreen._build_system_state()` builds one for every system the story
defines (`get_star_systems()` scans `config/stories/{story}/systems/*.json`)
at construction, and `self.systems` keeps every one of them alive - and
ticking - for the rest of the session, not just whichever system is
currently active:

- `SpaceScreen.update_physics()` calls `SystemState.update_physics()` for
  *every* system each frame (station/moon rotation, celestial bodies, AI
  ship pilots) - so a freighter's route or a patrol's orbit keeps advancing
  in a system the player has jumped away from, exactly like
  `main.py`'s `update_background_locations()` already did for a station/
  moon interior's NPCs.
- `AsteroidField`/`StarField` are the one exception - both live on
  `SystemState` (so a revisited system doesn't reset its scenery) but only
  the *active* system's copies get an `update()` call, since both are
  purely decorative and driven by the camera (`AsteroidField.update()`
  reads `utils.camera_offset_x/y` to decide which chunks to spawn), which
  only ever reflects the active system.
- Jumping (`SpaceScreen._complete_jump()`) never rebuilds anything anymore
  - it just calls `_activate_system(destination_id)`, which re-points every
  alias above at the destination's already-built, already-simulating
  `SystemState`.
- `ExplorerRoutine` is the one thing that moves a `Character` *between*
  systems - it removes the character from its current system's
  `SystemState.ai_ships` and appends it to another's (see "Character: AI
  Pilots & NPCs" above). This is enough on its own because every system
  reuses the same game-space coordinate range (`GAME_WIDTH`/`GAME_HEIGHT`),
  and only the system whose objects are currently aliased onto
  `SpaceScreen` is ever drawn or given a camera - a `Character` sitting in
  a different system's list is simply inert and invisible until the player
  actually jumps there.

## State Machine: Screen Flow

```
BackdropMenu(main) → BackdropMenu(story) → PilotNameDialog → LocationScreen (station)
                                              ↓ (one connected interior: walk to the loan officer, then the
                                                 ship dealer; L at the dock portal boards)  ↓ (save)
                                          SpaceScreen ←→ SaveBrowser
                                              ↓ (land: L)
                            LocationScreen (station) ←→ PauseMenu

SpaceScreen → ChoiceDialog (landing spot) → LocationScreen (moon: city ←→ wilderness, L) ←→ PauseMenu
```
A default-story station is a **single** `LocationScreen` — one connected
walkable area with just one portal (the ship dock). Multi-interior landing sites
(the moon's city/wilderness, or another story's station) still work: each
interior is its own cached `LocationScreen` and `portals` wire them together.
A new pilot never sees `SpaceScreen` at all until they own a ship - see
`main.py`'s `"pilot_name"` handler and `LocationScreen.ship_available`.

**State transitions via return values:**
- `handle_input()` returns an action string
- Main loop (`main.py`) interprets it and transitions `current_screen`
- See [UI_FLOW.md](../UI_FLOW.md) for the full diagram and every state

## Design Decisions

**Why `WorldObject` as a base for `Ship` & `LandingSite`?**
- DRY: both needed position, `get_distance()`, and rotate-and-draw-polygon logic
- Added when the arrow-around-ship HUD feature surfaced the duplication directly

**Why one generic `LocationScreen` instead of separate station/moon classes?**
- Station interior, moon city, and moon wilderness are all "walk around, talk to
  NPCs, exit near the entrance" — the only difference is config data
- New locations are added by writing JSON, not new Python classes (see the
  Data-Driven Configuration pattern in [DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md))

**Why `get_state()`/`restore_state()` on every screen?**
- Centralized state capture for save/load
- Clear contract for what needs persistence
- Easy to extend when adding new saveable objects

**Why an open world instead of screen-wrapping?**
- Ships used to teleport at `GAME_WIDTH`/`GAME_HEIGHT` edges (torus topology); this was
  removed in favor of a genuinely unbounded world
- `StarField`/`AsteroidField` generate their content procedurally per-chunk as the
  camera approaches, and forget chunks once far behind it — so exploring indefinitely
  keeps finding new stars/asteroids without pre-generating (or wrapping) a fixed-size
  field, and without unbounded memory growth. `StarField` reseeds each chunk
  deterministically by position so backtracking looks the same; `AsteroidField`
  deliberately does not, so a chunk you leave and come back to has different asteroids
  (see `AsteroidField`'s docstring in `asteroid_field.py` and PHYSICS.md).

See [DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md) for reusable solutions across the codebase.
