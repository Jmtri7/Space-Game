# Weapons, Combat & Asteroid Mining

Weapon outfits, ship-to-ship combat, provocation/hostility, and asteroid
breakup/mining. Ship stats and the `Character`/`Routine` model these build on
are in [class-hierarchy.md](class-hierarchy.md); outfit config lives in each
story's `ship_outfits.json` / `asteroid_types.json`.

**Weapon outfits:** every ship type carries at least one `"weapon"` slot in
its `ship_types.json` `slots` list (see "`ship_types.json`" fields and the
Outfitting section below). A weapon outfit (`ship_outfits.json`, `slot_type:
"weapon"`) is a full stat bundle, not just cosmetic: `damage`, `fire_rate`
(cooldown frames between shots), `projectile_speed`, `projectile_size`,
`projectile_lifetime` (frames before a shot despawns - its effective range),
`inaccuracy` (degrees of random per-shot aim wobble), `pellet_spread`
(degrees - the fixed fan arc `projectile_count` pellets spread across, a
*separate* stat from `inaccuracy`), `projectile_count`, plus its own
`icon_shape`/`icon_color` and `fire_sound`. The story ships four -
`laser_cannon` (balanced baseline), `pulse_blaster` (fast/weak/imprecise -
`inaccuracy` but no `pellet_spread`), `heavy_cannon` (slow single heavy
slug, longest `projectile_lifetime`), `scatter_gun` (`pellet_spread` fan of
5, each pellet also carrying a little `inaccuracy`) - but adding a fifth is
pure config, no code (a story can also add its own via a story-scoped
`ship_outfits.json`, merged over the shared catalogue like any other
`story_catalogue` file - `mining_101`'s `rapid_laser` is one: fast fire
rate, a long-lived green projectile, and heavy `inaccuracy` (20°)). The Outfitter menu's stats preview
(`OutfittingMenu._draw_stat_panel`, shown live for whichever outfit is
selected/focused in both its Buy and Install tabs) reads every one of these
fields directly, so a new weapon's full readout - Fire Rate converted to
shots/sec, Projectile Range converted to seconds, Inaccuracy as "±n.n°" or
"None (precise)", Pellet Spread only shown when `projectile_count > 1` -
appears with no UI changes needed either.

**Non-weapon outfits** (`slot_type` `engine` / `utility` / `shield`) act
entirely through a `stat_modifiers` dict that `Ship.apply_outfits` stacks
additively onto the hull's base stats, then floors: `max_thrust`,
`max_velocity`, `rotation_speed`, `cargo_capacity`, and `max_health` (extra
effective hull - the fraction of current health is preserved when it applies,
so equipping mid-flight tops the bar up proportionally). `ships-core`
(the shared outfit module) carries `afterburner` / `ion_thruster` (engine),
`cargo_expansion` / `reinforced_hull` (utility, the latter now also `+max_health`),
`shield_capacitor` (utility, `+35 max_health`, no speed cost), and
`sensor_array` (utility, `"scan": true`). A `scan` outfit installed on the
flown ship adds the target's **faction / standing / hull %** to the Space
View targeting panel (`_HudMixin._player_has_scanner`); without one the panel
shows just ship type + pilot.

**Firing:** holding **SPACE** in the Space View
(`SpaceScreen._update_weapon_fire`, rate-limited by
`weapon_fire_cooldown`/the equipped weapon's own `fire_rate` so holding the
key fires repeatedly rather than once - and deliberately excluded from the
"any keypress cancels autopilot" rule below, so firing doesn't abort a run
to the station) resolves the flown ship's actual loadout via
`SpaceScreen._equipped_weapon_stats` - the outfit installed in its first
weapon slot, each field falling back individually to `laser_cannon`'s value
so a partial config still works. A hull that *has* weapon slots but none
installed fires nothing (`_equipped_weapon_stats` returns `None`, SPACE is a
no-op); only the slot-less legacy placeholder ship falls back to
`laser_cannon` entirely so it can still fire *something*. `projectile_count == 1` fires one shot,
randomly offset within `inaccuracy` degrees if the weapon has any
(`pulse_blaster`); `projectile_count > 1` fans that many pellets evenly
across the `pellet_spread` arc, each pellet *also* independently offset by
`inaccuracy` (`scatter_gun` sets both - a wide fan of individually-imprecise
pellets), rather than a rigid comb. Each shot spawns a `Projectile`
(`game/world/projectile.py`) from the ship's nose, inheriting the ship's own
velocity, sized/coloured/shaped/lifetimed after the firing weapon's own
`projectile_size`/`icon_shape`/`icon_color`/`projectile_lifetime` and
carries that weapon's own `damage`. The drawn icon is rotated to the shot's
*actual resultant travel direction* - `atan2` of its final velocity vector
(ship velocity + firing velocity combined), not the raw aim angle (a
rotation-capable `angle` param on `ui_theme.draw_item_icon`) - so a shot
fired while the ship is drifting sideways visibly points where it's really
going, not just where it was aimed, and always matches its weapon's own
Outfitter-menu icon.

**F engages autopilot** (moved off SPACE so the two controls don't
collide - see `handle_input`'s `K_f` branch and [CONTROLS.md](../CONTROLS.md)).

**Ship-to-ship combat.** Every `Ship` has `health` / `max_health`
(`ship_types.json`'s `"max_health"`, else `max(20, size*2.5)`; `take_damage()`
returns True on destruction; `park()` repairs to full - landing is the only
repair). Every `Projectile` carries an `owner` (`"player"` or an AI
`Character`). `SpaceScreen._check_projectile_ship_collision` (run per shot in
`_update_projectiles`, alongside the asteroid check): a `"player"`-owned shot
hits any AI ship in the active system, an AI-owned shot hits only the player,
and a shot never hits its own owner. `_fire_weapon(shooter, stats, aim_angle,
owner)` is the shared spawn path - the player calls it from
`_update_weapon_fire` (SPACE) with `_equipped_weapon_stats()`, hostile AI from
`_update_ai_weapon_fire` with the weaker `_ai_weapon_stats()` (laser baseline,
half fire rate), rate-limited per pilot by `character.ai_fire_cooldown`.

**Hostility gating on hit, not just on fire.** `_check_projectile_ship_collision`
only lets a player-fired shot connect with an AI ship that's already hostile
(`ship.in_combat`) or is the player's *current target*
(`SpaceScreen._get_target_object()`) - a shot that grazes some other,
un-targeted, peaceable ship (a miner, a passing freighter) passes harmlessly
through instead of provoking it by accident; deliberately targeting a ship
(T, or clicking it) and then shooting still provokes it normally. Symmetrically,
an AI-fired shot only ever lands on the player if its own owner Character is
still `in_combat` at the moment of impact - a belt-and-braces check alongside
`character.firing` already only ever being set by `CombatRoutine`, in case a
shot is still mid-flight the instant its owner stops being hostile.

**Provocation.** `_provoke(ship)` runs whenever a player shot lands on an AI
ship: once per pilot it sets that ship's `hostile_to_player:<name>` flag (so it
fights back next frame and the grudge persists in the save) and docks a one-time
−10 from its faction's standing - so shooting up enough of a faction's ships
crosses `HOSTILE_REP_THRESHOLD` and turns the whole faction hostile. A nameless
ship goes straight into `CombatRoutine` instead (no flag key to persist).

**Hostility** is a routine swap, mirroring `_sync_escorts`:
`SpaceScreen._sync_hostiles` (every frame) puts a pilot into `CombatRoutine`
(`game/world/combat_routine.py` - turn to face the player, close to
~`PREFERRED_RANGE`, set `character.firing` while lined up and in range) when
its faction standing is `<= HOSTILE_REP_THRESHOLD` (-40), or a
`hostile_to_player:<name>` / `faction_hostile:<faction>` flag is set - and back
to its role routine otherwise (`character.in_combat` tracks which, like
`escorting`). **`CombatRoutine` drives the ship through its low-level controls
(`turn_left`/`increase_thrust`/…) exactly as `PlayerController` does - it never
touches `autopilot.py` / `SeekMode`, so it carries none of the
[AUTOPILOT_TESTING.md](../AUTOPILOT_TESTING.md) regression risk.** Like
`OrbitPlayerRoutine` it's a scripted override, not in `ROLE_ROUTINES` /
`ROUTINE_REGISTRY`.

**Destruction.** `_destroy_ship(character)` - explosions + sound, remove from
its `SystemState.ai_ships` (the target pointer re-syncs via `_validate_target`).
`_on_player_destroyed()` - explode in place, then **end the run**: no Rescue
Service respawn. It sets `SpaceScreen.game_over` (plus the cargo total that
went down with the ship, for the summary), which `update()` turns into a
`"game_over"` return next frame - `main.py` hands that off to the Game Over
screen (reusing the `"ending"` state/screen - see
[UI_FLOW.md](../UI_FLOW.md)'s EndingScreen section) and then the main menu.
Checked once per frame after `_update_projectiles` (not inline in the
collision, which would clobber the alive-projectile list).

**Asteroid damage:** `Asteroid` (`game/world/asteroid.py`) carries a
`health` pool (`max(3, size * 1.1 * health_multiplier)` - deliberately low so
a rock breaks up in a few hits, `health_multiplier` an optional per-type
`asteroid_field.types` field defaulting to 1.0 - e.g. `mining_101`'s belts
set `0.25` on every type to make its rocks break even faster) and
`take_damage()`. Asteroids draw through `WorldObject._draw_shaded_polygon`
(shared with any other world object that wants a lit, curved look) - a base
fill plus a light and a dark crescent band hugging whichever stretch of the
silhouette ring faces toward/away from a fixed light direction, each band's
inner edge corner-cut (Chaikin) so it reads as a smooth curve rather than
flat facets, the same "silhouette edge pulled inward by a tapered depth
profile" idea `expand.py`'s `_crescent` uses for character/article shading,
simplified since an asteroid's ring is convex enough to skip the interior
ray-casting that pipeline needs for concave body regions.
`SpaceScreen._check_projectile_asteroid_collision` checks every live
projectile each frame against `AsteroidField.asteroids`; the collision
radius is `asteroid.size + projectile.size` (roughly the asteroid's own
drawn radius - both the round-circle and jagged draw paths scale off
`size`, see `Asteroid.draw`), not a fixed hitbox, so aiming reliably lands
on a big asteroid's edge and not just dead-center. Every hit (not just a
destroying one) spawns a spark-burst `Explosion` (`game/world/explosion.py`
- a brief, purely cosmetic particle effect, not a `WorldObject`, tracked in
`SpaceScreen.explosions`) and plays the `"impact"` sound (see
[SOUND.md](../SOUND.md)) - the same for every weapon; only the fire sound differs
per-weapon.

**Breakup / mining, on an asteroid's health reaching zero**
(`SpaceScreen._destroy_asteroid`):
- **size > 12** (a "large" asteroid): breaks into 2-4 smaller `Asteroid`
  fragments (`_spawn_asteroid_fragments`) flung outward from the impact
  point, each inheriting the parent's `asteroid_type` (so a fragment is
  still minable/breakable in its own right, recursively, down to the small
  case below).
- **size ≤ 12** (a "small" asteroid): destroyed outright, dropping
  `asteroid_type["mine_yield"]` units of `"ore"` - **but only who destroyed
  it decides whether that ore ever exists** (`_destroy_asteroid`'s
  `destroyer` param, passed through from whichever projectile/collision hit
  killed it):
  - the **player**: scatters as 1-3 drifting `OrePickup` chunks
    (`game/world/ore_pickup.py`, `SpaceScreen._spawn_ore_debris`) rather
    than crediting cargo directly - see "Ore pickups" below.
  - an AI **miner** (`MinerRoutine`): credited straight into that miner's
    own cargo hold (capacity-capped), no pickup spawned at all - see the
    Miner AI section's "Selling" note.
  - **anyone/anything else** - a non-miner AI's opportunistic clearing shot
    (`_update_ai_asteroid_clearing`), or the station's own point-defense
    (`_update_station_defense`) - **drops no ore whatsoever**. Letting an
    NPC or the station's own gun hand the player free-floating ore would
    undercut mining as something the player actually has to do themselves.

  `mine_yield` is per-type config (`asteroid_types.json`, alongside
  `shape`/`color`/jaggedness), so different rock types can be worth
  different amounts.

**Ore pickups:** an `OrePickup` drifts at a slow constant velocity (plus a
share of the destroyed asteroid's own velocity) and slowly tumbles, purely
cosmetic flourishes; it expires after `LIFETIME_FRAMES` (~60s) if never
collected, fading out over its last `FADE_FRAMES`, so a heavily-mined field
doesn't accumulate debris without bound. Each frame,
`SpaceScreen._update_ore_pickups` checks every live pickup against the
player's distance (`PICKUP_RANGE + ship.size`) and the ship's remaining
cargo room (`ship.cargo_capacity - Possessions.cargo_quantity_total()`) -
collection tops the hold up to whatever fits, decrements the chunk's own
`amount` by that much, and leaves it drifting with the leftover rather than
being all-or-nothing, so a chunk bigger than the remaining hold space isn't
just left untouched. A partially- or fully-collected chunk calls
`Possessions.add_cargo`, shows a toast, and plays the `"pickup"` sound
(SOUND.md); a completely full hold instead flashes a "CARGO FULL" warning.
Hovering a drifting pickup in the main view shows a small name/quantity
label (`_HudMixin._draw_world_hover_tooltip`, `hud.py`) - the same hit-test-
under-cursor idea `_draw_minimap_tooltip` uses for minimap blips, just in
world space via `utils.to_screen`.

**Debug asteroid health readout.** With `constants.DEBUG_MODE` on, that same
world hover tooltip switches targets: hovering an asteroid instead of an ore
pickup shows `HP <current> / <max>` (`_HudMixin._hovered_asteroid`, hit-
tested against the asteroid's own drawn radius, `size * utils.get_scale()`).
It's a diagnostic-only readout - normal play never shows asteroid health
directly - useful for eyeballing whether a story's `health_multiplier`
tuning (above) lands where intended.

Mined ore sells like any other commodity, at a quartermaster's `"shop":
{"type": "commodities"}` (see `config/stories/default/commodities.json`'s
`"ore"` entry) - no separate mining-specific economy code.

Asteroids, fragments, and ore pickups are all pure scenery for save
purposes: none of `AsteroidField`, anything it spawns, `Explosion`, or
`OrePickup` is captured by `SpaceScreen.get_state()`/`restore_state()` (see
SAVE_SYSTEM.md) - only the ore that's actually been collected into
`Possessions.cargo` is. A save/load or system jump while a debris field is
still drifting simply forgets it - the same choice already made for
`AsteroidField` itself.

**System events (`events.json`, the `system-events` module).** A story
opts a system into rare, chance-driven content by listing entries in that
system's config `"events"` array - see config-formats.md's "System events"
section for the exact shape. Two kinds so far:

- `"special_asteroid"`: a distinct-looking, higher-`mine_yield` `Asteroid`
  variant (`config/modules/system-events/events.json`'s `rich_ore_vein` is
  the one shipped so far) that `SpaceScreen._build_system_events`
  (`game/screens/space_screen/setup.py`) resolves into an extra
  `(type_cfg, chance)` entry on `AsteroidField.events` - rolled
  independently per chunk, on top of (not competing against) the system's
  normal `types` draws, so a rare variant stays rare regardless of
  `per_chunk_range`. Mined exactly like any other asteroid - same
  breakup/ore-drop path above, just a bigger payout.
- `"pirate_ambush"` (`game/screens/space_screen/pirates.py`): a lone
  hostile AI ship. `_build_pirate_ambush_configs` (setup.py) resolves a
  system's `pirate_ambush`-kind entries into `(event_def, chance)` pairs
  kept on `SystemState.pirate_ambush_configs`;
  `SpaceScreen._maybe_spawn_pirate_ambush` rolls them on system **entry**
  (`_activate_system`, not per chunk - a different `"frequency"` meaning
  than `special_asteroid`'s) and again every `event_def`'s own
  `"interval_seconds"` (default 60s) while the player keeps flying in that
  system without leaving (`_update_periodic_pirate_ambush`, called every
  flying frame from `update_physics` - a no-op while docked) - so parking
  in a belt to mine for a long stretch doesn't mean permanent safety after
  the first roll misses. `_maybe_spawn_pirate_ambush` (re)arms
  `self.pirate_ambush_recheck_timer` every time it runs, hit or miss, off
  whichever configured interval is shortest; on a hit it builds the pilot
  exactly like `_build_ai_ship` but positioned `spawn_distance` world-units
  from
  the player at a random angle rather than a fixed system-config fraction.
  Only one ambush is ever tracked at a time (`SpaceScreen.pirate_ambush`,
  `None` when inactive). From there the encounter runs on existing
  machinery, not new mechanics: the pilot's own `pilots.json`
  `"one_way_hail"` delivers the warning the moment the player's in range
  (`_check_one_way_hails`, see the Hailing section); hailing back opens its
  `hail_dialogue_tree`, whose "pay" option combines `spend_credits:<n>`
  (blocked if unaffordable, same as any dialogue option) with
  `set_flag:pirate_tribute_paid:<name>`, and whose "refuse" option sets
  `hostile_to_player:<name>` directly; `_update_pirate_ambush` (called every
  frame from `update_physics`) watches for the paid flag to despawn the
  ship (`_despawn_pirate_ambush` - removed from `ai_ships`, no explosion,
  same removal pattern as `_destroy_ship` minus the kill), and counts its
  own `timeout` down to set that same `hostile_to_player:<name>` flag if
  the player never hails or refuses in time - but only once the player has
  actually heard the toll demand (`one_way_hail_seen:<name>`, set by
  `_check_one_way_hails` in the Hailing section): `update_physics` runs even
  while docked, so without this gate a player who lingered in the station
  after system entry could undock to find the timer already expired and the
  pirate hostile before ever hearing the threat. Going hostile - refusal,
  timeout, or a story setting the flag some other way - needs no
  pirate-specific combat code at all: it's the exact flag `_sync_hostiles`
  already watches for any pilot, so `CombatRoutine` and
  `_update_ai_weapon_fire` just pick it up. Jumping out of the system the
  ambush is in also calls `_despawn_pirate_ambush` (`jump.py`'s
  `_complete_jump`, before `_activate_system` swaps systems) - an
  unresolved pirate doesn't linger, frozen, for a later visit to stumble
  into; a self-jump (recentering within the same system) leaves it alone.
  A system config additionally sets `"hazard": "pirates"` to flag itself on
  the star map (`StarMap.draw_content`) - static flavor, independent of
  whether an ambush has actually rolled this session (see
  config-formats.md's `systems/*.json` field list).

- `"derelict_ship"` (`game/screens/space_screen/derelicts.py`): a static,
  unpiloted wreck the player finds and boards with **G** - rolled on system
  entry and periodically thereafter, same per-system-entry cadence as
  `pirate_ambush` (`_maybe_spawn_derelict`/`_update_periodic_derelict`
  mirror `_maybe_spawn_pirate_ambush`/`_update_periodic_pirate_ambush`
  exactly). Spawned far enough out to be guaranteed off-screen (even at
  minimum zoom) and outside minimap range - `_derelict_spawn_distance()` -
  so the player has to actually explore toward it rather than have it
  appear in view. The bearing itself (`_derelict_spawn_angle()`) is biased
  toward the player's current direction of travel - a cone
  `DERELICT_SPAWN_BIAS_CONE_DEG` wide either side of the velocity heading -
  rather than uniformly random, so flying in a straight line has a real
  chance of running into one instead of every bearing being equally likely
  regardless of where the player's actually headed; falls back to a fully
  random bearing below `DERELICT_SPAWN_BIAS_MIN_SPEED` (sitting still has no
  "direction of travel" to bias toward). Renders as a `DerelictShip`
  (`game/world/derelict_ship.py` - a `Ship` subclass reusing its
  graphics-driven draw, just dimmed and frozen at a fixed angle: no
  Character, no routine, no `ai_fire`, invisible to every existing NPC/AI/
  combat system) with a looping `SmokeTrail` (`game/world/smoke_trail.py`,
  distinct from the one-shot spark-burst `Explosion` above) for as long as
  it's unresolved. Can't be targeted (E/Q/T cycling, or click) until the
  player is within `DERELICT_TARGET_RANGE` - see `targeting.py`'s
  `_in_target_range`, a general per-object `target_range` gate - and
  boarding itself needs a close `DERELICT_BOARD_RANGE` +
  `DERELICT_BOARD_SPEED_CAP` gate, the same "close and slow" idiom
  `_check_landing()` already uses for station/moon docking. Three
  `"outcome"`s (config-formats.md's "System events" section has the full
  field list per outcome): `"loot"` opens a small generated walkable
  interior (reusing `get_interior_screen`/`LocationScreen`, not a new
  rendering path) whose NPC "containers" hand over credits/cargo/items via
  ordinary dialogue actions, then despawns permanently on exit; `"rescue"`
  resolves instantly (no interior) into a `Possessions.flags`-driven
  "hitching passenger" paid off at the next station/moon docking;
  `"trap"` resolves instantly into a cosmetic explosion + flat hull damage
  and an already-hostile pirate spawned exactly like this section's own
  hostile-spawn construction, no hail/toll negotiation. Not persisted
  across save/load (like `pirate_ambush`'s own spawn state) - see
  SAVE_SYSTEM.md; the rescue outcome's hitching-passenger flag is the one
  exception, and it needs no special handling since it's plain
  `Possessions.flags` state, already covered by an ordinary save.

Future event kinds (scannable anomalies, wormholes to disconnected systems)
belong in the same catalogue, each adding its own resolution branch in
setup.py and its own spawn path, since they won't all fit the
per-chunk-asteroid, per-system-entry-ambush, or per-system-entry-derelict
shapes these first three kinds reuse.

## Ship-asteroid collisions

Any ship (the player, while actually flying, or an AI ship not `ashore`)
that physically overlaps a live asteroid in the active system takes a
momentum-transfer hit - `SpaceScreen._check_ship_asteroid_collisions()`
(`mining.py`, called every frame from `update_physics`, right after
`self.asteroid_field.update()`), deepest-penetration asteroid wins per ship,
same pattern as the projectile checks above. **A ship mid-jump is excluded
outright** (`self.jump_state` for the player, `character.jumping` for an AI
pilot - see `ExplorerRoutine`/`jump.py`): the jump animation drives its
position directly, along a path that has nothing to do with normal flight,
so the fiction is a jump drive passing clean through local space, not a
physical transit an asteroid could actually be in the way of.
`_resolve_ship_asteroid_hit`:

- **Momentum**: a damped elastic collision along the line of centers - both
  "masses" are `max(1, size) ** 2` (an area-like stand-in, not a literal
  physical mass - same "tuned for feel, not derived" spirit as `Asteroid`'s
  own size-based health formula), and only `COLLISION_RESTITUTION` (0.55) of
  a full elastic bounce is actually applied, so it reads as a solid, damped
  impact rather than a billiard-ball bounce. Only exchanges momentum while
  the two are actually closing (`rel_dot < 0`) - two objects drifting apart
  after a graze don't get an extra kick.
- **Separation**: pushes the ship back along the collision normal by however
  much it's still overlapping, so the same pair can't keep re-colliding
  every frame while stuck together.
- **Damage**: `ship_damage = SHIP_COLLISION_DAMAGE_COEFF * asteroid.size *
  relative_speed ** 2` (quadratic in speed - a slow graze barely scratches
  the hull; a big and/or fast rock hurts a lot) vs. `asteroid_damage =
  ASTEROID_COLLISION_DAMAGE_COEFF * (ship.size + 5) * relative_speed` (linear,
  but scaled high enough that most real hits break the asteroid up or destroy
  it outright - same `take_damage()`/`_destroy_asteroid()` path a projectile
  hit uses, so breakup/ore-drop behaves identically either way). A destroyed
  ship goes through the normal `_destroy_ship`/`_on_player_destroyed` path;
  `update_physics`'s later `player.ship.health <= 0` check is guarded on
  `not self.game_over` so a collision-killed player isn't destroyed twice.

## Asteroid dodging and opportunistic clearing

`game/world/asteroid_avoidance.py`'s `steer_away_from_asteroids(character,
asteroids, ignore=None, urgency=1.0)` is a shared per-frame velocity nudge,
deliberately **outside** `autopilot.py` - it never issues a turn/thrust
command or touches `SeekMode`/`OrbitMode`, so unlike a change to autopilot
itself it carries none of the regression risk
[AUTOPILOT_TESTING.md](../AUTOPILOT_TESTING.md) requires validating (the
same reasoning that already keeps `CombatRoutine` off that surface). It
finds the single most urgent threat via `find_asteroid_threat` - a real
**closest-point-of-approach prediction** (both the ship and the asteroid
extrapolated at their current constant velocity, not just "is something
close right now"), so a fast asteroid still far away but on a genuine
collision course gets reacted to before it's already on top of the ship,
while one that's merely nearby but already past its closest approach and
opening up again is left alone (an earlier version of this scored the
"already past, separating" case as maximally urgent purely because its
clamped time-to-approach was zero - a real bug: it livelocked a miner that
had drifted near, but away from, any modestly close rock, since it read as
permanently under imminent threat). The nudge itself is safe to layer on
top of *any* routine, whether its ship is autopilot-driven (`SeekMode`
re-corrects for it next frame, the same way it already copes with space
drag) or hand-flown low-level (`CombatRoutine`, `MinerRoutine` just add it
to their own turn/thrust commands that same frame). `urgency` (0..1, a
pilot's own `dodge_urgency` - see `pilots.json`, default 1.0) scales how
hard a personality reacts; `character.dodge_urgency` is set once at
construction (`Character.for_ai_pilot`). The function also **returns the
threat's severity** (0 if nothing threatened), so a caller can gate its own
behavior on it - `MinerRoutine` suppresses firing and approach entirely
above `URGENT_DODGE_SEVERITY`, and `_update_ai_asteroid_clearing` (below)
stands down a ship's opportunistic shot the same way - trajectory safety
takes priority over both hunting and clearing, every frame, for every AI.

It also **sticks to whichever asteroid it last locked onto**
(`DODGE_LOCK_FRAMES`, ~45 frames) rather than re-picking "the single most
urgent one" fresh every frame - the lock lives on the `Character` itself
(`_dodge_lock`/`_dodge_lock_timer`), invisible to callers. This is the same
"sticky-decision pitfall" lesson [AUTOPILOT_TESTING.md](../AUTOPILOT_TESTING.md)
documents for `autopilot.py`, applying just as much here: without it, two
comparably-threatening asteroids on either side of a ship can flip which
one "wins" from frame to frame, and each flip swings the dodge push to a
near-opposite direction - the net effect over many frames is the pushes
mostly cancel and the ship barely moves, which is exactly what "the miner
just sits there" looks like from outside. Locking onto one threat and
committing to dodging it keeps every push pointed roughly the same way
long enough to actually clear the danger zone.

`SpaceScreen._update_ai_asteroid_dodge()` (called every frame from
`update_physics`, active system only) applies this to every AI ship not
`ashore` and not currently running `MinerRoutine` (which already calls it
itself, excluding its own hunted target - see below - so it isn't double-
applied).

`SpaceScreen._update_ai_asteroid_clearing()` is the "some AI will blow up
asteroids in their way" behavior, for every AI ship (any role, any
personality) that isn't already fighting the player (`in_combat`), isn't
currently mid-dodge (`_dodge_severity` above `URGENT_DODGE_SEVERITY` - see
below), and isn't running `MinerRoutine` (which hunts and shoots
deliberately, not opportunistically). It **never steers** - doing so would
fight whatever's actually driving that ship's heading, autopilot included -
so it only ever sets `character.firing` when an asteroid already happens to
be dead ahead (within `CLEARING_CONE_DEG`) and close (`CLEARING_RANGE`) of
the ship's *current* heading, whatever chose it. The shot itself flows
through the exact same `_update_ai_weapon_fire` / `_fire_weapon` pipeline
hostile AI already uses (`character.firing` + `character.ai_fire_cooldown`),
and lands on the asteroid via the ordinary projectile-asteroid check
(unconditional on `owner`, see above) regardless of who fired it.

`_update_ai_asteroid_dodge()` stashes each ship's dodge severity for that
frame on `Character._dodge_severity` (a duck attribute, 0 when nothing
threatens) precisely so `_update_ai_asteroid_clearing` - which runs right
after it - can check it: trajectory safety always outranks taking an
opportunistic shot.

## Miner AI

`MinerRoutine` (`game/world/miner_routine.py`, role `"miner"`) hunts
asteroids in its home system, sells the ore, and repeats - the mining
counterpart to `DockRoutine`'s fly/walk/talk/fly loop. Phases: `"hunting"` ->
`"returning"` -> `"walking_in"` -> `"selling"` -> `"walking_out"` -> back to
`"hunting"`.

- **Hunting**: picks the nearest asteroid within `ENGAGE_RANGE` **and**
  `HOME_TETHER_RANGE` of the home station, excluding any asteroid already
  claimed by another miner or on this miner's own avoid list (see
  "Territory claiming" below), as its target, and drives
  low-level toward it - `turn_left`/`turn_right`/`increase_thrust`/
  `release_thrust`, `character.firing` when aligned and in range - exactly
  like `CombatRoutine`, and for the same reason: a moving, shrinking target
  you have to destroy isn't what `SeekMode`/arrival semantics are for, and
  staying off the autopilot surface entirely means none of
  [AUTOPILOT_TESTING.md](../AUTOPILOT_TESTING.md)'s validation burden
  applies. Once close (`PREFERRED_RANGE * 1.5`) but still carrying too much
  speed (`PREFERRED_SPEED_CAP`) to actually hold position there, it brakes
  (`_brake()`) instead of continuing to steer straight at the target's
  current bearing - without this, momentum carries the ship past the
  target every pass and it just circles forever, the same close-range
  pursuit-curve failure [AUTOPILOT_TESTING.md](../AUTOPILOT_TESTING.md)
  documents for `SeekMode`, and one that reads to a player as "the miner's
  stuck in place" since the loop is small and net displacement stays near
  zero even though the ship is moving fast. If the current target ends up
  more than `ABANDON_RANGE` away - not destroyed, just knocked or dodged
  far off course (easy with a dense field: a ship-asteroid collision can
  fling a ship well off its original heading) - it's dropped and re-picked,
  rather than chasing the same distant target forever in an ever-so-slowly-
  converging straight line (being merely "still in the loaded asteroid
  list" says nothing about how far *this ship* has since ended up from it).
  Similarly, if the *same* target survives `CHASE_TIMEOUT_FRAMES` (~15s) of
  continuous active hunting without ever being destroyed - it may simply be
  drifting in a direction that keeps interrupting every approach (dodge
  pushes, a collision at just the wrong moment) even though it's nominally
  much slower than the ship - it's abandoned and put on this miner's own
  `AVOID_COOLDOWN_FRAMES` (~10s) blacklist, so it doesn't just immediately
  re-pick the exact same rock next frame while something else nearby goes
  unmined. **Every frame, before any of that**: `steer_away_from_asteroids
  (..., ignore=<hunted target>)` checks whether some *other* asteroid's
  predicted path is about to cross this ship's own; above
  `URGENT_DODGE_SEVERITY` the hunt is suppressed outright that frame
  (`character.firing = False`, thrust released) so the dodge nudge acts
  uncontested - trajectory safety comes before pressing the attack, not
  just alongside it. Both this gate and the close-range braking one above
  it are **sticky with hysteresis**, not recomputed bare every frame
  (`self._dodging` / `self._braking_close`): once triggered, each holds
  until severity/speed drops back below a *lower* exit threshold
  (`EXIT_DODGE_SEVERITY` / `EXIT_SPEED_CAP`), not just back below the entry
  one. Without the gap between the two thresholds, a value hovering right
  at the boundary flips the decision every frame, and each flip swings the
  ship between "turn toward the target" and "turn away" - exactly the
  sticky-decision pitfall [AUTOPILOT_TESTING.md](../AUTOPILOT_TESTING.md)
  documents for `autopilot.py`, showing up here as a miner that looks like
  it can't decide whether to chase an asteroid or flee it, flickering
  between the two instead of committing to either. If nothing's left to hunt and the ship has drifted
  past the home tether, it heads back to the station anyway rather than
  idling in deep space waiting for a rock that may never come. Once cargo
  (`character.person.possessions.cargo_quantity_total()` vs.
  `character.ship.cargo_capacity`) is full, switches to `"returning"`.
- **Returning**: the same dodge-first, low-level turn/thrust steering,
  aimed at the home station instead; once close and slow enough, parks
  (`ship.park()`) and either walks in (below) or, if the station has no
  walkable interior configured, sells immediately in place. Closing on a
  *stationary* goal (unlike chasing a combat target, where drifting past at
  speed doesn't matter) also needs to actually shed velocity - a plain
  "thrust while pointed at the goal" controller never does that on its own,
  it just orbits, endlessly overshooting - so once close enough that
  arriving means braking, not closing further, the routine switches to
  `_brake()`: turn to face retrograde and thrust against the ship's own
  velocity, gated on actually being close to retrograde first (the same
  alignment-gate idea `autopilot.py`'s own braking uses - thrusting while
  still mid-turn would just keep redirecting velocity in a circle at a
  roughly constant speed instead of shedding it). `_brake()` is also what
  stops a miner that's run out of targets from just coasting forever on
  whatever velocity it last had (space has no drag by default - see
  PHYSICS.md).
- **Docking**: reuses `get_interior_screen`/`LocationScreen.plan_path`/
  `Person.step_toward`/`portal_for` exactly like `DockRoutine` - walks to
  whichever NPC in the interior has `role == "quartermaster"`, pauses
  `SELL_FRAMES` (~1.5s), sells, walks back out, reboards. Its `_step_toward`
  carries the same stuck-recovery `DockRoutine._step_toward` does (a
  re-plan, then a give-up-the-leg bailout), duplicated rather than shared
  since the two routines otherwise have nothing in common.
- **Selling**: `Possessions.earn(qty * CREDITS_PER_ORE)` +
  `Possessions.remove_cargo("ore", qty)` directly on the miner's own
  `person.possessions` - a flat, config-free AI-to-AI conversion (no
  `commodities.json`/`sell_multiplier` lookup, no UI, no sound), the same
  "flavor economy, nothing spends it yet" precedent
  `Character.AI_PILOT_STARTING_CREDITS` already set.

A `pilots.json` entry needs `"role": "miner"` (or `"routine": "miner"`) and
the pilot's ship needs a weapon slot + real `cargo_capacity` (see
`mining_101`'s `mining_skiff` ship type and `prospector` pilot for a worked
example - deliberately slow (`max_thrust`/`max_velocity`/`rotation_speed`
all well below the story's `courier`) with a huge hold (`cargo_capacity`
70, nearly 3x the courier's), the fiction being a hull built around cargo
space rather than speed; `MinerRoutine`'s own pursuit geometry
(`PREFERRED_RANGE`/`FIRING_CONE_DEG`) is loosened accordingly - a
sluggish-turning ship needs a wider stand-off and a looser alignment
window than `CombatRoutine`'s tighter numbers, or it just orbits its
target without ever landing a shot, the same close-range pursuit-curve
failure mode [AUTOPILOT_TESTING.md](../AUTOPILOT_TESTING.md) documents for
`SeekMode`) - `_build_ai_ship`'s `route` (an `ai_ships[]` entry's `"route":
["station"]`) becomes `MinerRoutine`'s single sell destination. Asteroids
are single-system scenery (`AsteroidField` only streams chunks for whichever
system is camera-driven - see PHYSICS.md), so a miner finds nothing to hunt
in a system the player isn't currently visiting; it just idles until the
player arrives.

**Territory claiming.** `SystemState.claimed_asteroids` (a plain set of live
`Asteroid` references, one per system, not persisted - asteroids aren't
saveable scenery either) tracks which asteroid each `MinerRoutine` in that
system currently has as its own target. `_pick_target` excludes anything
already in that set before choosing, and `_claim`/`_release_claim` keep it
in sync with `self.target_asteroid` (claimed the moment a target is picked,
released whenever it's given up - destroyed, out of range, abandoned, or
timed out - and on cargo-full/reboard as a safety net). With several miners
sharing one belt, this is what keeps them spreading out onto different
rocks instead of every one of them converging on whichever single asteroid
happens to be nearest to all of them.

## Station point-defense

Every system's station fires a slow, heavy shot at the nearest asteroid
within `STATION_DEFENSE_RANGE` (650 units) every `STATION_DEFENSE_INTERVAL`
(150 frames, ~2.5s) - `SpaceScreen._update_station_defense()`, called every
frame from `update_physics` for the active system only (asteroids are
single-system scenery, same reasoning as everywhere else in this doc). The
cooldown lives on `SystemState.station_defense_cooldown`, not `SpaceScreen`,
so each system's station keeps its own independent timer. The shot is a
plain `Projectile` with `owner="station"` (a bare string, not a Character) -
`_check_projectile_ship_collision`'s hostility gate (`getattr(owner,
"in_combat", False)`) always reads `False` for a string, so a station's shot
can only ever land on an asteroid via the ordinary (owner-unconditional)
projectile-asteroid check; it can never hit a ship, hostile or otherwise.
`STATION_DEFENSE_DAMAGE` (55) is high enough to one- or two-shot most
asteroids outright - the station keeps the belt clear right around the dock
for anyone nearby, not just whatever the player happens to be mining.

The shot is slow (`STATION_DEFENSE_SPEED`, 3 units/frame) relative to a
drifting asteroid, so aiming straight at the target's *current* position
would often miss outright by the time the shot arrives - `_lead_intercept`
(mining.py) solves the standard constant-velocity firing solution instead:
given the asteroid's current position/velocity and the shot's own speed, it
finds the smallest positive `t` where `|asteroid_pos + asteroid_vel*t -
station_pos| = shot_speed*t` (a quadratic in `t`) and aims at the predicted
position at that time, falling back to the asteroid's current position if
no positive-time solution exists (e.g. it's already outrunning the shot).
