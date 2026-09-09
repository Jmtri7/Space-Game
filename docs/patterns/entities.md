# Patterns: Entity Modelling

Base classes, composition over inheritance, and the role→routine registry — how
this game builds every character without a class explosion. Hub + working
principles: [DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md).

---

## Pattern: Base Class for Reusable Entity Logic

**Problem:** Multiple entity types (`Ship`, `LandingSite`) duplicate position/
distance/rotate-and-draw-polygon logic.

**Solution:** Extract shared logic into a base class (`WorldObject`), same
idea as any base class — see `game/world/world_object.py`.

**Use case:** Multiple entity types sharing core *physical-object*
functionality (position, drawing).

---

## Pattern: Compose, Don't Inherit, for "Who Flies It"

**Problem:** The player, AI ship pilots, and station/moon NPCs all need a
walking-around body (`Person`); only some of them also fly a `Ship`. An
earlier version of this game gave AI ships their own `Ship` subclass
(`AIShip(Ship)`) with a `Person` bolted on the side - which put the player
and AI pilots in *opposite* class shapes (`PlayerController` owns a `Ship`;
`AIShip` **is** one), and gave NPCs (no ship at all) no relationship to
either.

**Solution:** Nobody inherits `Ship`. `PlayerController` and `Character`
(`game/world/character.py`) both *compose* one - `self.ship` - alongside a
`self.person` (`Person`), with delegating properties (`x`/`y`/`velocity_x`/
`angle`/`engage_seek()`/...) so the rest of the game can duck-type either
one as a flyable ship without caring which it is. A `Character` with
`ship=None` (any station/moon NPC) is just a body with a role - not a
degenerate case, the normal one.

```python
class Character:
    def __init__(self, person, ship=None, role=None, ...):
        self.person = person
        self.ship = ship            # None for a local NPC
        self.routine = ROLE_ROUTINES.get(role, IdleRoutine)(route)

    @property
    def x(self):
        return self.ship.x          # only ever called when self.ship is set
    # ... same delegating-property set PlayerController already has

    def update(self):
        self.routine.run(self)
        if self.ship:
            self.ship.update()
```

**Why this works:**
- One ownership shape (compose a `Ship`+`Person`) for every character,
  instead of two incompatible ones
- A routine (see the next pattern) never needs to know or check whether its
  `Character` has a ship - it just calls the methods its own kind of
  behavior needs, and a `Character` only ever gets *one* kind of routine
- Adding a new kind of character (a shopkeeper, a second kind of ship) never
  means picking a base class to inherit - just which pieces to compose

**Use case:** Any time two-or-more entity "roles" overlap partially (some
fly, some don't; some have dialogue, some don't) - composition lets each
piece (body, ship, role) vary independently instead of forcing every
combination into its own subclass.

---

## Pattern: Role → Routine Registry

**Problem:** "What does this character do on its own" (fly a route, dock
and walk around, wander a room, stand still) needs to vary by role/job, for
*every* character, not just ship-flying ones - without an `if role ==
"..."` chain re-checked every frame.

**Solution:** A dict from role string to a `Routine` class, all implementing
the same two-method interface, looked up once at construction:

```python
ROLE_ROUTINES = {
    "freighter_pilot": DockRoutine,     # ship-flying
    "patrol_officer": OrbitRoutine,     # ship-flying
    "bartender": StationaryRoutine,     # local, no ship
    "resident": WanderRoutine,          # local, no ship
}

class Character:
    def __init__(self, person, ship=None, role=None, route=None, ...):
        self.routine = ROLE_ROUTINES.get(role, IdleRoutine)(route or [])
        self.routine.start(self)

    def update(self):
        self.routine.run(self)
        ...
```

Every `Routine` (`start(character)`, `run(character)`) lives in its own
file (see `game/world/dock_routine.py`, `wander_routine.py`, etc.) and reads
either `character.ship`'s delegated methods or `character.person.x/y`
directly - never both, since a role only ever maps to one kind.

**Why this works:**
- Adding a new job is data (`"role": "..."` in config) + one small class +
  one registry entry - never a new `if` branch in an existing `update()`
- The exact same mechanism serves AI ship pilots and local NPCs, so a
  future "walks to work then flies home" role isn't a special case, just a
  routine that does both

**Use case:** Any entity whose autonomous behavior should be chosen by a
config-driven category (job, faction, difficulty tier) rather than its
Python class.
