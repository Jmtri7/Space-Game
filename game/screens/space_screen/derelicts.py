"""SpaceScreen: derelict-ship events — mixed into the class in screen.py.

The "derelict_ship" system-event kind (see docs/architecture/combat-and-mining.md's
"System events" and events.json's "kind") - a static, unpiloted wreck the
player has to actually go find (spawned safely off-screen and off-minimap,
see _derelict_spawn_distance) and board with G once close and slow enough.
Deliberately pure scenery until boarded: no Character, no routine, no
ai_fire, nothing that lets any existing NPC/AI/combat system notice it (the
same "not scenery any NPC interacts with" rule miner_routine.py already
applies to drifting ore - see game/world/derelict_ship.py's own docstring).

Rolled on system (re-)entry and periodically thereafter while the player
lingers, exactly like "pirate_ambush" (see pirates.py's module docstring for
why a lingering player still needs to keep getting rerolled) - only one
derelict is ever tracked at a time (self.derelict, None when inactive), the
same "a lone wreck is the whole premise" simplicity precedent pirate_ambush
already sets, and it's forgotten (not saved) across a save/load exactly like
that ambush's own spawn state - see SAVE_SYSTEM.md. The one exception is a
rescue outcome's "hitching a ride" state, which lives on Possessions.flags
and so *is* covered by an ordinary save automatically (see _mark_landed()).

Three outcomes ("outcome" on the resolved events.json entry - see
config-formats.md's "System events" section for the full shape):
- "loot": boarding opens a small generated walkable interior (reused
  get_interior_screen/LocationScreen machinery, not a new rendering system -
  see _build_loot_interior_config) with a few "container" NPCs whose
  dialogue hands over credits/cargo/items once each; exiting despawns the
  wreck permanently.
- "rescue": boarding doesn't open an interior at all (the fiction is
  "someone boards your ship", not the reverse) - it immediately sets a
  "hitching_passenger" flag + that passenger's own payout, and despawns the
  wreck; the payout is credited the next time the player docks at an
  inhabited station or moon (see _mark_landed()).
- "trap": boarding triggers an explosion (cosmetic burst + a flat hull-damage
  hit, see DERELICT_TRAP_DEFAULT_DAMAGE) and immediately spawns a hostile
  pirate nearby via the same construction pirate_ambush's own hostile spawn
  uses, already-hostile (no hail/toll negotiation - the wreck itself was the
  trick) - then despawns.
"""
import math
from game.screens.space_screen._defs import *  # noqa: F401,F403
from game.world.derelict_ship import DerelictShip
from game.world.smoke_trail import SmokeTrail

DEFAULT_DERELICT_RECHECK_SECONDS = 60  # matches pirates.py's DEFAULT_RECHECK_SECONDS

# Spawn-direction bias: a derelict tends to spawn roughly ahead of the
# player's current heading of travel rather than at a uniformly random
# bearing, so flying in a straight line has a real chance of running into
# one instead of it always being equally likely to be spawned behind you.
# Only applies while actually moving faster than DERELICT_SPAWN_BIAS_MIN_SPEED
# (a ship sitting still/drifting has no "direction of travel" to bias
# toward, so falls back to a fully random bearing). The bias is a cone, not
# a fixed line dead ahead - DERELICT_SPAWN_BIAS_CONE_DEG either side of the
# player's velocity heading - so it still feels like "out there somewhere
# ahead", not a scripted beacon glued to the exact heading.
DERELICT_SPAWN_BIAS_MIN_SPEED = 0.3
DERELICT_SPAWN_BIAS_CONE_DEG = 35

# Targeting range: a derelict can't be cycled/clicked as a target until the
# player is within this many world units of it (see targeting.py's
# _in_target_range) - large enough to matter tactically (spot it and close
# in) but clearly finite, same spirit as mining.py's STATION_DEFENSE_RANGE
# (650) and PICKUP_RANGE, just scaled up for something meant to be found
# from much further off. Deliberately smaller than a derelict's own spawn
# distance (see _derelict_spawn_distance) - it spawns out past both
# targeting AND minimap range, so a player has to close in before either
# opens up.
DERELICT_TARGET_RANGE = 1800

# Boarding gate (G) - close and slow, mirroring the same "distance <
# landing_distance and speed < 0.4" idiom SpaceScreen._check_landing already
# uses for station/moon docking, and MinerRoutine's own close-range brake
# threshold (PREFERRED_SPEED_CAP) for the same "can't be moving fast and
# still dock cleanly" reasoning.
DERELICT_BOARD_RANGE = 70
DERELICT_BOARD_SPEED_CAP = 0.4

# A trap's explosion deals a flat burst of hull damage on top of spawning
# the hostile pirate - comparable to a single weak weapon hit (see
# projectile.py's PROJECTILE_DAMAGE), not something that alone threatens a
# healthy hull; the real danger is the pirate. A story's event entry can
# override via "explosion_damage".
DERELICT_TRAP_DEFAULT_DAMAGE = 12


class _DerelictsMixin:

    def _derelict_spawn_distance(self):
        """How far from the player a freshly-rolled derelict spawns - just
        outside the render view at this story's minimum zoom (so zooming out
        fully still can't reveal it pop into view) AND just outside minimap
        detection range (MINIMAP_RANGE), whichever is bigger, plus a small
        buffer. At minimum zoom the Space View shows a GAME_WIDTH x
        GAME_HEIGHT world rectangle scaled by 1/camera_zoom_min around the
        player - half its diagonal is the furthest a corner of that
        rectangle can reach, so anything spawned beyond it is guaranteed
        off-screen regardless of window aspect ratio (approximate across
        aspect ratios, same "doesn't need to be exact" tolerance
        JUMP_SELF_MIN_DISTANCE's own comment already accepts)."""
        half_diagonal = 0.5 * math.hypot(GAME_WIDTH, GAME_HEIGHT) / self.camera_zoom_min
        return max(half_diagonal, MINIMAP_RANGE) + 150

    def _derelict_spawn_angle(self):
        """The bearing (radians) a freshly-rolled derelict spawns at - biased
        toward the player's current direction of travel (see
        DERELICT_SPAWN_BIAS_CONE_DEG's comment) so flying in a straight line
        tends to actually run into one, rather than every bearing being
        equally likely regardless of where the player's headed. Falls back
        to a fully random bearing while too slow for "direction of travel"
        to mean anything (sitting still, drifting near zero speed)."""
        speed = math.hypot(self.player.velocity_x, self.player.velocity_y)
        if speed < DERELICT_SPAWN_BIAS_MIN_SPEED:
            return random.uniform(0, 2 * math.pi)
        travel_angle = math.atan2(self.player.velocity_y, self.player.velocity_x)
        cone = math.radians(DERELICT_SPAWN_BIAS_CONE_DEG)
        return travel_angle + random.uniform(-cone, cone)

    def _maybe_spawn_derelict(self, state):
        """Roll a system's "derelict_ship" event configs (see
        setup.py._build_derelict_configs) - called on system (re-)entry and
        periodically thereafter while the player lingers, exactly mirroring
        _maybe_spawn_pirate_ambush (see pirates.py's own docstring for the
        full reasoning, identical here)."""
        configs = getattr(state, "derelict_configs", None)
        if configs:
            interval = min(event.get("interval_seconds", DEFAULT_DERELICT_RECHECK_SECONDS) for (_, event), _ in configs)
            self.derelict_recheck_timer = int(interval * constants.FPS)
        if self.derelict is not None:
            return
        for (event_id, event), chance in configs or []:
            if random.random() >= chance:
                continue
            self._spawn_derelict(state, event_id, event)
            return  # one at a time, same reasoning as pirate_ambush

    def _update_periodic_derelict(self):
        """Reroll the active system's derelict odds on a timer while the
        player is actually flying in it - mirrors
        _update_periodic_pirate_ambush exactly (see its own docstring)."""
        if not self.in_flight:
            return
        state = self.systems.get(self.system_id)
        if state is None or not getattr(state, "derelict_configs", None):
            return
        self.derelict_recheck_timer -= 1
        if self.derelict_recheck_timer <= 0:
            self._maybe_spawn_derelict(state)

    def _spawn_derelict(self, state, event_id, event):
        """Build the DerelictShip + its SmokeTrail at a random angle,
        _derelict_spawn_distance() world-units from the player's current
        position (mirrors _spawn_pirate_ambush's placement, just at a much
        larger, off-screen/off-minimap distance - see the module docstring),
        and make it targetable (MISC bucket - see targeting.py's
        _filtered_targets, which already buckets anything that's neither a
        Character nor a LandingSite there with no change needed)."""
        ship_type_id = event.get("ship_type", "courier")
        graphics = get_graphics_asset(self.story, "ships", ship_type_id)
        distance = self._derelict_spawn_distance()
        angle = self._derelict_spawn_angle()
        x = self.player.x + math.cos(angle) * distance
        y = self.player.y + math.sin(angle) * distance
        wreck = DerelictShip(x, y, event_id, event, graphics=graphics)
        wreck.target_range = DERELICT_TARGET_RANGE
        smoke = SmokeTrail(x, y)
        self.derelict = {
            "system_id": state.system_id,
            "object": wreck,
            "smoke": smoke,
            "event_id": event_id,
        }
        self.targetable_objects.append((wreck.name, wreck))

    def _despawn_derelict(self, resolved=True):
        """Stop tracking the active derelict (and drop it from
        targetable_objects/current_target) - called once its outcome
        resolves (loot exhausted, rescue picked up, trap sprung) or when the
        player jumps out of its system (see jump.py's _complete_jump,
        mirroring _despawn_pirate_ambush there). `resolved` is only for
        future callers that might want to distinguish the two; both paths
        behave identically today since a derelict carries no state worth
        preserving either way (see the module docstring's save-system note).
        """
        encounter = self.derelict
        if encounter is None:
            return
        wreck = encounter["object"]
        target = self._get_target_object()
        self.targetable_objects = [e for e in self.targetable_objects if e[1] is not wreck]
        if target is wreck:
            self.current_target = None
        self.derelict = None

    def _update_derelict(self):
        """Advance the active derelict's smoke trail - called every flying
        frame from update_physics, active system only (a derelict is
        single-system scenery exactly like AsteroidField/StarField - see
        SystemState's docstring)."""
        encounter = self.derelict
        if encounter is None or not self.in_flight or encounter["system_id"] != self.system_id:
            return
        encounter["smoke"].update()

    def _in_derelict_board_range(self, wreck):
        """True if the player is close enough and slow enough to board
        `wreck` right now - the same "distance < X and speed < 0.4" gate
        _check_landing() uses for station/moon docking."""
        distance = wreck.get_distance(self.player.x, self.player.y)
        speed = math.hypot(self.player.velocity_x, self.player.velocity_y)
        return distance < DERELICT_BOARD_RANGE and speed < DERELICT_BOARD_SPEED_CAP

    def _try_board_derelict(self, wreck):
        """Board `wreck` (the current target) if in range/slow enough -
        called from handle_input's Action.LAND branch. Returns "land" if the
        caller should hand off to main.py's landing pipeline (loot outcome
        only - see loop_helpers.begin_landing's "derelict" branch), or None
        if boarding didn't happen (out of range/too fast - a toast explains
        why - handled instantly, e.g. rescue/trap)."""
        if self.derelict is None or self.derelict["object"] is not wreck:
            return None
        if not self._in_derelict_board_range(wreck):
            self._show_toast("Too far or moving too fast to board", YELLOW)
            return None
        outcome = wreck.outcome
        self.player.park()
        if outcome == "loot":
            # A throwaway LandingSite wrapper purely so get_interior_screen
            # (which expects a landing_site's .interiors/.interior_screens/
            # .interior_world_size, not a bespoke interface) can be reused
            # unchanged for a derelict's generated interior - see
            # _build_loot_interior_config and loop_helpers.begin_landing's
            # "derelict" branch. Built lazily here (not at spawn time) since
            # most derelicts are never boarded.
            landing_site = LandingSite(wreck.x, wreck.y, graphics={"size": wreck.size},
                                        interiors={"default": self._build_loot_interior_config(wreck)},
                                        name=wreck.name)
            self.derelict["landing_site"] = landing_site
            self.landing_target = "derelict"
            self._mark_landed()
            return "land"
        elif outcome == "rescue":
            self._resolve_derelict_rescue(wreck)
            return None
        elif outcome == "trap":
            self._resolve_derelict_trap(wreck)
            return None
        return None

    def _resolve_derelict_rescue(self, wreck):
        """"Someone boards your ship" - no interior needed (see the module
        docstring). Records a hitching-passenger flag + their own payout
        (Possessions.flags, so an ordinary save covers it - see
        SAVE_SYSTEM.md) and despawns the wreck. Paid out the next time the
        player docks at an inhabited station/moon - see _mark_landed()."""
        event = wreck.event_def
        lo, hi = event.get("payout_range", [100, 300])
        payout = random.randint(int(lo), int(hi))
        flags = self.player.person.possessions.flags
        flags["hitching_passenger"] = wreck.event_id
        flags[f"rescue_payout:{wreck.event_id}"] = payout
        self._show_toast(f"{wreck.name}: a stranded pilot climbs aboard.", CYAN)
        self._despawn_derelict()

    def _resolve_derelict_trap(self, wreck):
        """Boarding was the trigger: a cosmetic explosion (+ a flat hull-
        damage burst - see DERELICT_TRAP_DEFAULT_DAMAGE) and an immediately-
        hostile pirate spawned nearby, built exactly like
        pirates.py._spawn_pirate_ambush's hostile spawn except already
        hostile (no hail/toll negotiation - the wreck itself was the con,
        there's nothing left to negotiate)."""
        event = wreck.event_def
        self.explosions.append(Explosion(wreck.x, wreck.y))
        sound_board.play("impact")
        damage = event.get("explosion_damage", DERELICT_TRAP_DEFAULT_DAMAGE)
        if self.player.ship:
            self.player.ship.health = max(0, self.player.ship.health - damage)
        state = self.systems.get(self.system_id)
        pilot_id = event.get("pirate_pilot")
        ship_type_id = event.get("pirate_ship_type", "raider_skiff")
        pilot = get_pilot(self.story, pilot_id) if pilot_id else None
        angle = random.uniform(0, 2 * math.pi)
        px = self.player.x + math.cos(angle) * 250
        py = self.player.y + math.sin(angle) * 250
        pirate = Character.for_ai_pilot(
            px, py,
            ship_type=get_ship_type(self.story, ship_type_id),
            ship_type_id=ship_type_id,
            graphics=get_graphics_asset(self.story, "ships", ship_type_id),
            pilot=pilot,
            route=[],
            get_interior_screen=self.get_interior_screen,
            space_drag=state.space_drag if state else 0,
            outfit=get_graphics_asset(self.story, "outfits", self.default_outfit_id),
            systems=self.systems,
            system_id=self.system_id,
        )
        if state is not None:
            state.ai_ships.append(pirate)
        name = pirate.person.name or "Raider"
        # Straight to hostile - no toll/hail negotiation, see docstring.
        # _sync_hostiles() picks this flag up next frame like any other.
        self.player.person.possessions.flags[f"hostile_to_player:{name}"] = True
        self._show_toast(f"It's a trap! {name} opens fire!", (255, 120, 120))
        self._despawn_derelict()

    def _build_loot_interior_config(self, wreck):
        """A minimal generated walkable interior for a "loot" derelict - one
        small room, a single return_to_ship portal (reusing the exact
        interior/portal machinery every station/moon interior already uses -
        see LandingSite.get_ship_entry_key / config-formats.md's interior
        geometry section), and one "container" NPC per loot table entry
        (credits + each cargo/item drop, so finding several things means
        searching several containers rather than one big payout). Each
        container's dialogue hands its reward over exactly once (a
        per-container "searched" flag gates a repeat) via the shared
        "earn_credits:"/"loot_cargo:" dialogue actions (game/world/dialogue.py) -
        no new interior mechanic, just NPC dialogue like any other."""
        event = wreck.event_def
        loot = event.get("loot", {})
        credits_lo, credits_hi = loot.get("credits_range", [0, 0])
        credits = random.randint(int(credits_lo), int(credits_hi)) if credits_hi > 0 else 0

        # Each container is an ordinary NPC (dialogue/T-to-talk keeps working
        # unchanged) but rendered as a static item glyph instead of a walking
        # figure - see Person._draw_icon / "icon_shape"+"icon_color" on an
        # npc config entry (config-formats.md's "Interior geometry" section).
        # Shape/color are just flavor per container kind, reusing the same
        # procedural glyphs shop items/ore pickups already draw with
        # ui_theme.draw_item_icon - "gem" (gold) for the credit stash, "crate"
        # (its default) for a cargo drop, "vial" for a personal effect.
        npcs = []
        containers = []
        if credits > 0:
            containers.append(("Credit Stash", [f"earn_credits:{credits}"], f"A hidden stash - {credits} credits, still good.", "gem", (235, 200, 90)))
        for drop in loot.get("cargo", []):
            qty_lo, qty_hi = drop.get("qty_range", [1, 1])
            qty = random.randint(int(qty_lo), int(qty_hi))
            commodity = drop.get("commodity", "ore")
            containers.append((f"{commodity.title()} Crate", [f"loot_cargo:{commodity}:{qty}"], f"{qty} units of {commodity}, still sealed.", "crate", (150, 110, 80)))
        for item_id in loot.get("items", []):
            containers.append((item_id.replace("_", " ").title(), [f"give_item:{item_id}"], "A salvaged personal effect.", "vial", (140, 200, 190)))

        for i, (label, actions, text, icon_shape, icon_color) in enumerate(containers):
            flag = f"derelict_{wreck.event_id}_searched_{i}"
            npcs.append({
                "name": label,
                "x": 300 + (i % 3) * 120,
                "y": 260 + (i // 3) * 120,
                "role": "loot_point",
                "icon_shape": icon_shape,
                "icon_color": icon_color,
                "dialogue_tree": {
                    "root": "start",
                    "conditional_roots": [{"flag": flag, "node": "empty"}],
                    "nodes": {
                        "start": {
                            "text": text,
                            "options": [
                                {"label": "Take it.", "next": None, "actions": actions + [f"set_flag:{flag}"]},
                                {"label": "Leave it.", "next": None},
                            ],
                        },
                        "empty": {
                            "text": "Already searched. Nothing left here.",
                            "options": [{"label": "...", "next": None}],
                        },
                    },
                },
            })

        return {
            "label": wreck.name,
            # "derelict_hull" (config/modules/system-events/cultures.json) is
            # what actually makes this read as a hull interior rather than
            # open space: a "culture" is what makes LocationScreen honour the
            # "rooms" list at all and paint a floor_color polygon for it (see
            # config-formats.md's "Interior geometry" section) - with no
            # culture the room polygon below is silently dropped and the
            # walkable area falls back to the flat-background bounds, so the
            # player and every container NPC appeared to stand in the
            # starfield with nothing under them. space_backdrop stays on
            # (dead hull breached to the void beyond this one lit deck), now
            # combined with a visible dim/damaged-metal floor underneath it,
            # matching how the orbital-std "concourse" interior pairs the two.
            "space_backdrop": True,
            "culture": "derelict_hull",
            "portals": [{"x": -20, "y": 310, "connected_locations": [], "return_to_ship": True}],
            "rooms": [{"label": "Hold", "polygon": [[-20, 200], [420, 200], [420, 500], [-20, 500]]}],
            "npcs": npcs,
        }

    def exit_derelict(self):
        """The player walked out of a boarded "loot" derelict's interior
        back to their ship (main.py's "derelict" screen state's own "exit"
        action - mirrors board_ship(), then permanently despawns the wreck,
        exactly like the "walk the interior, then it's gone" outcome the
        brief calls for (nothing left to find twice)."""
        self.board_ship()
        if self.derelict is not None:
            self._show_toast(f"{self.derelict['object'].name} stripped clean.", CYAN)
            self._despawn_derelict()
