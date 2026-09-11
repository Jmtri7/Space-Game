"""Pure-ish helpers for main()'s state machine — save-state assembly, the
menu/dialog builders each screen transition needs, the story-version warnings,
background-interior simulation, and step_world() (the fixed-timestep sim half).

Split out of main.py so that file is just the loop. Nothing here touches the
display/window/vsync state that lives in main.py; these are called from the
loop, not the reverse. main.py re-exports every name here (`from
game.app.loop_helpers import *`) so `main.<name>` keeps resolving.
"""
import os
import sys
import pygame

from game.utils import load_json, get_story
from game.ui.choice_dialog import ChoiceDialog
from game.ui.shop_menu import ShopMenu
from game.ui.ship_browser_menu import ShipBrowserMenu
from game.ui.outfitting_menu import OutfittingMenu
from game.ui.backdrop_menu import BackdropMenu


def build_save_game_state(game_screen, previous_screen, station_interior, moon_interior):
    """Build the (game_state, system_config_snapshot) pair for
    create_save_file(), from whichever screen was active when Save was
    chosen. Centralized here (used by both the overwrite and new-save
    branches in the pause menu) specifically so "story"/"system_id" always
    land on the *final* dict - each call site used to set them on an empty
    dict and then immediately discard it by reassigning game_state from
    get_state() for a station/moon save, so a save made anywhere but open
    space silently forgot which system it was in and always reloaded into
    the story's starting one."""
    if previous_screen == "moon":
        game_state = moon_interior.get_state()
        game_state["location"] = "moon"
        # interior_key (set by SpaceScreen.get_interior_screen) is which
        # key this actually is in the moon's own interiors config - not a
        # guess from its label text, which used to misdetect any city
        # interior whose label didn't literally contain the word "city"
        # (e.g. Kepler's Reach's "Rust Moon Settlement") as "wilderness".
        game_state["moon_location"] = moon_interior.interior_key or "city"
        system_config_snapshot = {}
    elif previous_screen == "station":
        game_state = station_interior.get_state()
        game_state["location"] = "station"
        game_state["station_location"] = station_interior.interior_key or "default"
        system_config_snapshot = {}
    else:  # previous_screen == "game" or None
        game_state = game_screen.get_state()
        game_state["location"] = "space"
        system_config_snapshot = game_screen.system_config

    if game_screen:
        game_state["story"] = game_screen.story
        game_state["system_id"] = game_screen.system_id
        game_state["story_version"] = game_screen.story_version
        game_state["module_versions"] = game_screen.module_versions
    return game_state, system_config_snapshot


def _pressed_any(events, *keys):
    """True if this frame's events contain a KEYDOWN for any of `keys`. Used
    so the overlay each key opens (M jump map, P possessions, N mission log)
    also closes on that same key, and any of them closes on ESC - these
    overlays are otherwise mouse-only (see docs/DESIGN_PATTERNS.md)."""
    return any(e.type == pygame.KEYDOWN and e.key in keys for e in events)


def build_shop_menu(possessions, story, shop_config, cargo_capacity, buy_ship_fn, on_outfits_changed, switch_ship_fn=None):
    """Which menu class a "shop" config opens - ShipBrowserMenu for ships
    (needs a live preview, a purchase callback, and a switch-active-hull
    callback), OutfittingMenu for ship outfits (needs the current ship's
    slots and a stats-refresh callback), ShopMenu for everything else
    (commodities/items). Centralized here since both the station and moon
    branches in main()'s state machine need the same dispatch."""
    shop_type = shop_config.get("type")
    if shop_type == "ships":
        return ShipBrowserMenu(possessions, story, shop_config, on_buy=buy_ship_fn, on_switch=switch_ship_fn)
    if shop_type == "outfits":
        ship_type_id = possessions.active_ship()
        return OutfittingMenu(possessions, story, shop_config, ship_type_id, on_outfits_changed=on_outfits_changed)
    return ShopMenu(possessions, story, shop_config, cargo_capacity=cargo_capacity)


def story_menu_rows():
    """`(value, label, description)` rows for the `BackdropMenu` story picker -
    scans config/stories/*/story.json (same as the old StorySelector did)."""
    rows = []
    stories_dir = "config/stories"
    if os.path.isdir(stories_dir):
        for item in sorted(os.listdir(stories_dir)):
            story_json = os.path.join(stories_dir, item, "story.json")
            if os.path.isfile(story_json):
                description = (load_json(story_json) or {}).get("description", "")
                rows.append((item, item.replace("_", " ").title(), description))
    return rows


def landing_location_options(interiors):
    """`(key, label, None)` options for the `ChoiceDialog` moon-landing picker."""
    options = []
    for key, config in interiors.items():
        label = config.get("label", key.capitalize()) if isinstance(config, dict) else key.capitalize()
        options.append((key, label, None))
    return options


def exit_options(option_keys, interiors, disabled_reasons):
    """`(key, label, disabled_reason)` options for the `ChoiceDialog` exit picker."""
    out = []
    for key in option_keys:
        if key == "ship":
            label = "Return to Ship"
        else:
            config = interiors.get(key)
            label = config.get("label", key.capitalize()) if isinstance(config, dict) else key.capitalize()
        out.append((key, label, disabled_reasons.get(key)))
    return out


def warn_if_module_version_mismatch(story, saved_modules):
    """Warn (never block) when a shared module the story now uses is at a
    different version than the save recorded - the same staleness signal as
    the story version, for config a story pulls in from config/modules/
    (see docs/CONFIG_MODULES.md)."""
    from game.config_source import module_versions
    current = module_versions(story)
    saved_modules = saved_modules or {}
    for name, cur in current.items():
        was = saved_modules.get(name)
        if was is not None and was != cur:
            print(f"WARNING: this save used shared module '{name}' version {was}, but it is now at version {cur} - saved state that depends on it may load differently.", file=sys.stderr)


def warn_if_story_version_mismatch(story, saved_version):
    """Print a warning if a save's story_version doesn't match the current
    story.json's version - the story's config or this game's state-
    handling code may have changed since the save was made, in a way that
    changes what the saved state means (see docs/SAVE_SYSTEM.md's "Save
    Compatibility Discipline"). Never blocks loading - just surfaces the
    risk so a stale save behaving oddly isn't a total mystery."""
    current_version = get_story(story).get("version", "0.0.0")
    if saved_version is None:
        print(f"WARNING: this save predates story versioning (story '{story}' is now at version {current_version}) - it may not load correctly if the story's config or save format has changed since.", file=sys.stderr)
    elif saved_version != current_version:
        print(f"WARNING: this save was made with story '{story}' version {saved_version}, but the current version is {current_version} - it may not load correctly if the story's config or save format has changed.", file=sys.stderr)


def update_background_locations(game_screen, active_location):
    """Keep every cached station/moon interior's NPCs simulating even while
    the player isn't there - active_location (whichever LocationScreen the
    player is actually standing in right now, or None if they're in space)
    is skipped here since it already gets a full update() from its own
    branch below, including player movement and the camera.

    Spans every system the story defines (see SpaceScreen.systems), not
    just the one currently active - a station/moon interior in a system the
    player isn't even in right now still keeps its NPCs simulating, exactly
    like game_screen.update_physics() already does for AI ships in space."""
    if not game_screen:
        return
    for system_state in game_screen.systems.values():
        for landing_site in (system_state.station, system_state.moon):
            for interior in landing_site.interior_screens.values():
                if interior is not active_location:
                    interior.update_physics()


def begin_landing(game_screen):
    """Bring the player's ship to rest and build the screen it's landing
    into, from `game_screen.landing_target` (already set to "station" /
    "moon" by whatever decided to land). Returns
    `(next_screen, station_interior_or_None, location_selector_or_None)` -
    the caller assigns only the field matching `next_screen` so the other
    cached interior isn't clobbered.

    Shared by two call sites: the L-key "land" action from
    `SpaceScreen.handle_input`, and the autopilot auto-land that
    `SpaceScreen.update()` returns "land" for from *inside* a sim step
    (see step_world / the accumulator loop in main()).

    A system's `station`/`moon` config is optional (see
    config-formats.md's systems/*.json note) - a system that skips one gets
    a placeholder `LandingSite` with no `interiors` at all, just so physics/
    targeting/drawing/save-restore never need a None check. That
    placeholder is a legitimate thing to fly near or target, but there is
    nothing to land *in* - checked here, before `park()`, so approaching
    one is a silent no-op (a toast, ship keeps flying) instead of a
    "station"/"select_location" transition into an interior that doesn't
    exist (main.py's screen branches assume a real one)."""
    if game_screen.landing_target == "station":
        if not game_screen.station.interiors:
            game_screen._show_toast(f"{game_screen.station.name} - nothing to land in")
            return "game", None, None
        game_screen.player.park()
        ship_entry_key = game_screen.station.get_ship_entry_key()
        station_interior = game_screen.get_interior_screen(game_screen.station, ship_entry_key)
        station_interior.arrive_from("ship")
        return "station", station_interior, None
    if game_screen.landing_target == "moon":
        if not game_screen.moon.interiors:
            game_screen._show_toast(f"{game_screen.moon.name} - nothing to land in")
            return "game", None, None
        game_screen.player.park()
        location_selector = ChoiceDialog(
            "Landing Location", landing_location_options(game_screen.moon.interiors))
        return "select_location", None, location_selector
    return "game", None, None


def step_world(current_screen, game_screen, station_interior, moon_interior):
    """Advance the simulation by exactly one fixed SIM_STEP (1/60 s) for the
    active screen, and nothing for rendering.

    This is the "simulation half" of what each `while running:` branch in
    main() used to do inline once per iteration - physics, NPC updates,
    background-location updates, and the per-step countdown timers that
    live inside those update() methods. The main loop runs it 0..N times
    per rendered frame via advance_accumulator(), so the sim keeps correct
    wall-clock pace no matter the frame rate; input and draw stay once per
    frame in their own phases.

    Screens that freeze the world - every menu/dialog, the star map, pause,
    and any screen with an open conversation (`active_dialogue`) - do
    nothing here, exactly as the old loop did nothing for them.

    Returns "land" when the step itself triggers a screen change (autopilot
    auto-land from within `SpaceScreen.update()`), else None; the caller
    applies that transition and stops draining the accumulator."""
    if current_screen == "game":
        if game_screen and not game_screen.active_dialogue:
            transition = game_screen.update()
            update_background_locations(game_screen, None)
            if transition == "land":
                return "land"
    elif current_screen == "station":
        talking = bool(station_interior and station_interior.active_dialogue)
        if game_screen and not talking:
            game_screen.update_physics()
        if station_interior:
            station_interior.update()
        if not talking:
            update_background_locations(game_screen, station_interior)
    elif current_screen == "moon":
        talking = bool(moon_interior and moon_interior.active_dialogue)
        if game_screen and not talking:
            game_screen.update_physics()
        if moon_interior:
            moon_interior.update()
        if not talking:
            update_background_locations(game_screen, moon_interior)
    return None


def main_menu():
    """The main menu (NEW / LOAD / SETTINGS / QUIT) - rebuilt whenever the
    game returns to it so the LOAD row reflects the current save situation."""
    return BackdropMenu("GALAXY RISE", [
        ("new", "NEW", None),
        ("load", "LOAD", None),
        ("settings", "SETTINGS", None),
        ("quit", "QUIT", None),
    ])

