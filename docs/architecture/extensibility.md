# Extensibility Points

The step-by-step recipes for adding to the game without fighting the
architecture. The classes referenced here are described in
[class-hierarchy.md](class-hierarchy.md); the config they read is in
[config-formats.md](config-formats.md).

## Adding a New Entity Type
1. Create a class extending `Ship`, `LandingSite`, or `Person` - or, for a new
   *character*, prefer a new `Routine` (see below) over a new class
2. Override `update()` and/or `draw()`
3. Add to `SpaceScreen` (or a location's NPC list)
4. Include in `get_state()`/`restore_state()` if saveable

## Adding a New Screen
1. Create a class with `handle_input()`, `draw()` (and `update()` if it needs one)
2. Add a `current_screen` string and branches in `main.py`'s loop: input in
   phase 1, drawing in phase 3, and — only if the screen has a live
   simulation — a case in `step_world()` for phase 2 (the fixed-timestep
   accumulator). A modal that freezes the world needs no `step_world()` case.
   See [UI_FLOW.md](../UI_FLOW.md#main-loop-fixed-timestep-three-phases).
3. Implement transitions via `handle_input()` return values

## Adding a New Role/Routine (AI pilot or NPC)
1. Create a `Routine` class (own file, one class per file) with
   `__init__(self, route)`, `start(self, character)`, `run(self, character)`
   - reach through `character.ship`-delegated methods (`engage_seek`, etc.)
   for ship-flying behavior, or `character.person.x/y` directly for local
   (no-ship) behavior - never both in the same routine
2. Register it in `ROUTINE_REGISTRY` (`game/world/character.py`) under a
   short config name, and/or wire a role default into `ROLE_ROUTINES`
3. Point a character at it: `"role": "<name>"` (role default) or
   `"routine": "<registry name>"` (explicit, wins over the role) on the
   relevant `pilots.json` entry (ship-flying) or the location config's
   `npcs[]` entry (local) - no other code changes needed

## Adding or Updating a Ship Type

See [config-formats.md](config-formats.md#adding-or-updating-a-ship-type) — it
is almost always a `ship_types.json` + `graphics.json` entry, no Python.
