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
pure config, no code. The Outfitter menu's stats preview
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
so a partial config still works, and falling back to `laser_cannon` entirely
if the slot is empty (a new pilot's placeholder ship has no outfits yet, but
should still fire *something*). `projectile_count == 1` fires one shot,
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
`_on_player_destroyed()` - explode in place, then recover at the current
system's station: full repair, zero velocity, **cargo lost**, a "Rescue
Service" message. Checked once per frame after `_update_projectiles` (not inline
in the collision, which would clobber the alive-projectile list).

**Asteroid damage:** `Asteroid` (`game/world/asteroid.py`) carries a
`health` pool (`max(5, size * 2)`) and `take_damage()`.
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
- **size ≤ 12** (a "small" asteroid): destroyed outright, scattering
  `asteroid_type["mine_yield"]` units of `"ore"` as 1-3 drifting
  `OrePickup` chunks (`game/world/ore_pickup.py`,
  `SpaceScreen._spawn_ore_debris`) rather than crediting cargo directly -
  see "Ore pickups" below. `mine_yield` is per-type config
  (`asteroid_types.json`, alongside `shape`/`color`/jaggedness), so
  different rock types can be worth different amounts.

**Ore pickups:** an `OrePickup` drifts at a slow constant velocity (plus a
share of the destroyed asteroid's own velocity) and slowly tumbles, purely
cosmetic flourishes; it expires after `LIFETIME_FRAMES` (~60s) if never
collected, fading out over its last `FADE_FRAMES`, so a heavily-mined field
doesn't accumulate debris without bound. Each frame,
`SpaceScreen._update_ore_pickups` checks every live pickup against the
player's distance (`PICKUP_RANGE + ship.size`) and the ship's remaining
cargo room (`ship.cargo_capacity - Possessions.cargo_quantity_total()`) -
collection is all-or-nothing (the *entire* chunk's amount has to fit) rather
than a partial top-up, so a full hold just leaves it drifting instead of
partially draining it. A successful pickup calls `Possessions.add_cargo`,
shows a toast, and plays the `"pickup"` sound (SOUND.md).

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
