"""Space exploration game - main entry point and game loop."""
import pygame
import sys
import os
import time
import math
import game.constants as constants
import game.perf_metrics as perf_metrics
from game.constants import (
    GAME_WIDTH, GAME_HEIGHT, SAVE_DIR, FPS,
    DESKTOP_WIDTH, DESKTOP_HEIGHT, VIDEO_RESOLUTIONS
)
from game.utils import (
    load_save_file, create_save_file, set_camera_offset, set_screen_size, load_json, get_story,
    advance_accumulator, save_display_name, load_settings, save_settings
)
from game.world.player_controller import PlayerController
from game.audio.sound_board import sound_board
from game.audio.music import music
from game.screens.space_screen import SpaceScreen
from game.ui.backdrop_menu import BackdropMenu
from game.ui.pilot_name_dialog import PilotNameDialog
from game.ui.choice_dialog import ChoiceDialog
from game.ui.report_menu import ReportMenu, possessions_report, mission_report
from game.ui.shop_menu import ShopMenu
from game.ui.ship_browser_menu import ShipBrowserMenu
from game.ui.outfitting_menu import OutfittingMenu
from game.ui.pause_menu import PauseMenu
from game.ui.save_browser import SaveBrowser
from game.ui.confirm_dialog import ConfirmDialog
from game.ui.star_map import StarMap

# Initialize pygame and display
pygame.init()

# Windows' default timer granularity is ~15.6 ms, so a sleep-based frame
# limiter (clock.tick) overshoots and frame times jitter (visible as a
# pacing stutter on a camera pan). Ask for 1 ms granularity for the process
# lifetime so clock.tick actually holds the target, and hand it back on
# exit. Harmless / no-op off Windows.
if sys.platform == "win32":
    try:
        import ctypes
        import atexit
        ctypes.windll.winmm.timeBeginPeriod(1)
        atexit.register(ctypes.windll.winmm.timeEndPeriod, 1)
    except Exception:
        pass

# Set True by open_window() when a vsync'd display mode is actually pacing
# flips (measured, not just requested). When it is, the main loop leaves the
# frame rate to the vsync'd flip and clock.tick() only enforces a loose
# safety cap - a tight clock.tick(FPS) on top of vsync makes the sleep
# overshoot into the next vblank, stretching that frame to two refreshes
# (judder on a camera pan). When it's False, clock.tick(FPS) is the pacer.
vsync_display = False
VSYNC_SAFETY_FPS = FPS * 4


def _is_synced(surface):
    """Measure whether display.flip() is actually vblank-paced: a short burst
    of flips that comes back faster than ~200 FPS isn't syncing (vsync=1 is
    only a request - plenty of drivers ignore it for a windowed non-GL
    surface)."""
    t0 = time.perf_counter()
    for _ in range(24):
        surface.fill((0, 0, 0))
        pygame.display.flip()
    return 24 / max(time.perf_counter() - t0, 1e-6) < 200.0


NATIVE_RESOLUTION = (DESKTOP_WIDTH, DESKTOP_HEIGHT)

# Canonical display aspect ratios, for grouping resolutions in Video Settings.
# aspect_label() buckets a resolution to the closest of these (within 4%), so
# the two "21:9" panel sizes (2560x1080 = 2.370, 3440x1440 = 2.389) land in
# one group instead of two near-identical ones.
ASPECTS = [
    ("5:4", 5 / 4), ("4:3", 4 / 3), ("3:2", 3 / 2), ("16:10", 16 / 10),
    ("16:9", 16 / 9), ("21:9", 2560 / 1080), ("32:9", 32 / 9),
]


def resolution_fits(size):
    """True if `size` is no larger than the desktop in either axis."""
    return size[0] <= DESKTOP_WIDTH and size[1] <= DESKTOP_HEIGHT


def aspect_label(size):
    """The ASPECTS label closest to `size`'s width:height ratio (within 4%),
    else a reduced `"w:h"` string (an unusual panel gets its own group)."""
    r = size[0] / size[1]
    label, ratio = min(ASPECTS, key=lambda a: abs(a[1] - r))
    if abs(ratio - r) / r <= 0.04:
        return label
    g = math.gcd(int(size[0]), int(size[1]))
    return f"{size[0] // g}:{size[1] // g}"


NATIVE_ASPECT = aspect_label(NATIVE_RESOLUTION)


def resolutions_for_aspect(label):
    """Fitting VIDEO_RESOLUTIONS in aspect group `label`, plus the native
    desktop resolution when it belongs to `label`. Sorted small -> large."""
    picks = {r for r in VIDEO_RESOLUTIONS
             if resolution_fits(r) and aspect_label(r) == label}
    if NATIVE_ASPECT == label:
        picks.add(NATIVE_RESOLUTION)
    return sorted(picks, key=lambda s: (s[0], s[1]))


def available_aspects():
    """Aspect labels that have at least one fitting resolution - the native
    aspect first, then the rest in ASPECTS order."""
    labels = [lbl for lbl, _r in ASPECTS if resolutions_for_aspect(lbl)]
    if NATIVE_ASPECT in labels:
        labels.remove(NATIVE_ASPECT)
    return [NATIVE_ASPECT] + labels


def default_resolution():
    """Startup pick when nothing valid is saved: the monitor's native
    resolution."""
    return NATIVE_RESOLUTION


def load_resolution():
    """The saved video resolution if it still fits and is a known candidate
    (or the native resolution), else default_resolution()."""
    saved = load_settings().get("resolution")
    if isinstance(saved, (list, tuple)) and len(saved) == 2:
        candidate = (int(saved[0]), int(saved[1]))
        if resolution_fits(candidate) and (candidate in VIDEO_RESOLUTIONS
                                           or candidate == NATIVE_RESOLUTION):
            return candidate
    return default_resolution()


def open_window(size, measure_vsync=True):
    """Open the game window with a fixed SCALED logical surface of `size`.

    `SCALED` backs the window with a GPU renderer - the only way SDL2 vsyncs a
    non-OpenGL window on many drivers (this machine included); whether it
    actually engaged is measured into `vsync_display`. The logical surface
    stays `size` for the window's whole life: SDL scales it to whatever the
    user drags the window to and remaps mouse events, so the game needs no
    `VIDEORESIZE` handling at all. `SCALED`'s catch - the window can't be
    dragged below the logical size, and a second `set_mode()` on a live SCALED
    renderer fails - is why `size` is one of a few fixed `VIDEO_RESOLUTIONS`
    chosen in the main-menu Video Settings (and applied via a full display
    re-init, see `apply_resolution`), rather than something that tracks the
    window. Falls back to a plain resizable window (clock.tick paces, a pan
    may tear) if SCALED won't initialise.

    `measure_vsync=False` (used when re-applying a resolution) keeps the
    `vsync_display` the startup call already measured - the vsync capability
    is a property of the driver, not the resolution, and the measurement is a
    ~0.4 s burst of blank flips not worth repeating."""
    global vsync_display
    for flags in (pygame.RESIZABLE | pygame.SCALED, pygame.RESIZABLE):
        try:
            surface = pygame.display.set_mode(size, flags, vsync=1)
            break
        except pygame.error:
            surface = None
    if surface is None:
        surface = pygame.display.set_mode(size, pygame.RESIZABLE)
    if measure_vsync:
        vsync_display = _is_synced(surface)
    return surface


def apply_resolution(size):
    """Switch the SCALED logical resolution (from the Video Settings menu) and
    persist it. A live SCALED renderer can't be re-`set_mode()`'d, so the
    whole display is torn down and re-initialised - safe because this is only
    reachable from the main menu, where nothing holds a Surface reference."""
    global screen, logical_resolution
    pygame.display.quit()
    pygame.display.init()
    pygame.display.set_caption("Space Game")
    screen = open_window(size, measure_vsync=False)
    set_screen_size(*size)
    logical_resolution = tuple(size)
    settings = load_settings()
    settings["resolution"] = list(size)
    save_settings(settings)


logical_resolution = load_resolution()
screen = open_window(logical_resolution)
set_screen_size(*logical_resolution)
screen.fill((0, 0, 0))
pygame.display.flip()
pygame.display.set_caption("Space Game")
clock = pygame.time.Clock()


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
    return game_state, system_config_snapshot


def _pressed_any(events, *keys):
    """True if this frame's events contain a KEYDOWN for any of `keys`. Used
    so the overlay each key opens (M jump map, P possessions, N mission log)
    also closes on that same key, and any of them closes on ESC - these
    overlays are otherwise mouse-only (see docs/DESIGN_PATTERNS.md)."""
    return any(e.type == pygame.KEYDOWN and e.key in keys for e in events)


def build_shop_menu(possessions, story, shop_config, cargo_capacity, buy_ship_fn, on_outfits_changed):
    """Which menu class a "shop" config opens - ShipBrowserMenu for ships
    (needs a live preview and a purchase callback, not a flat price list),
    OutfittingMenu for ship outfits (needs the current ship's slots and a
    stats-refresh callback), ShopMenu for everything else (commodities/
    items). Centralized here since both the station and moon branches in
    main()'s state machine need the same dispatch."""
    shop_type = shop_config.get("type")
    if shop_type == "ships":
        return ShipBrowserMenu(possessions, story, shop_config, on_buy=buy_ship_fn)
    if shop_type == "outfits":
        ship_type_id = possessions.owned_ships[-1] if possessions.owned_ships else None
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


def warn_if_story_version_mismatch(story, saved_version):
    """Print a warning if a save's story_version doesn't match the current
    story.json's version - the story's config or this game's state-
    handling code may have changed since the save was made, in a way that
    changes what the saved state means (see CLAUDE.md's "Save Compatibility
    & Story Versioning" section). Never blocks loading - just surfaces the
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
    (see step_world / the accumulator loop in main())."""
    game_screen.player.park()
    if game_screen.landing_target == "station":
        ship_entry_key = game_screen.station.get_ship_entry_key()
        station_interior = game_screen.get_interior_screen(game_screen.station, ship_entry_key)
        if station_interior:
            station_interior.arrive_from("ship")
        return "station", station_interior, None
    if game_screen.landing_target == "moon":
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
    """The main menu (NEW / LOAD / VIDEO SETTINGS / QUIT) - rebuilt whenever the
    game returns to it so the LOAD row reflects the current save situation."""
    return BackdropMenu("GALAXY RISE", [
        ("new", "NEW", None),
        ("load", "LOAD", None),
        ("video", "VIDEO SETTINGS", None),
        ("quit", "QUIT", None),
    ])


def video_settings_menu(aspect):
    """Main-menu Video Settings for aspect group `aspect`: a top row that
    opens the aspect picker, then the fixed SCALED logical resolutions in that
    group (see open_window) - the active one marked "Current resolution", the
    native one "Native resolution". A resolution click applies it immediately
    (apply_resolution); Back returns to the main menu. Mouse-only."""
    aspect_desc = None if aspect == NATIVE_ASPECT else f"Your display is {NATIVE_ASPECT}"
    rows = [("aspect", f"Aspect ratio  ·  {aspect}", aspect_desc)]
    for w, h in resolutions_for_aspect(aspect):
        if (w, h) == logical_resolution:
            marker = "Current resolution"
        elif (w, h) == NATIVE_RESOLUTION:
            marker = "Native resolution"
        else:
            marker = None
        rows.append((f"{w}x{h}", f"{w} × {h}", marker))
    return BackdropMenu("VIDEO SETTINGS", rows, allow_cancel=True)


def video_aspect_menu(selected):
    """The aspect-ratio picker reached from Video Settings. One row per
    available_aspects() entry - the one in use marked "Selected", the
    monitor's own marked "Native" when it isn't the selected one. Picking one
    (or Back) returns to Video Settings with its resolution list refiltered."""
    rows = []
    for label in available_aspects():
        if label == selected:
            marker = "Selected"
        elif label == NATIVE_ASPECT:
            marker = "Native"
        else:
            marker = None
        rows.append((label, label, marker))
    return BackdropMenu("ASPECT RATIO", rows, allow_cancel=True)


def main():
    """Main game loop."""
    global screen
    try:
        # Build both music tracks (or load them from the on-disk cache)
        # during menu time, so neither has to render the first time it's
        # actually needed. pump(), called each frame below, drives this.
        music.prerender_all()
        menu = main_menu()
        story_selector = None
        game_screen = None
        station_interior = None
        moon_interior = None
        location_selector = None
        exit_menu = None
        exit_menu_landing_site = None  # game_screen.station or game_screen.moon - whichever this exit_menu is for
        exit_menu_return_screen = None  # "station" or "moon" - where ESC/cancel goes back to
        possessions_menu = None
        possessions_return_screen = None  # "game" / "station" / "moon" - where P/ESC closes back to
        mission_log = None
        missions_return_screen = None  # "game" / "station" / "moon" - where N/ESC closes back to
        shop_menu = None
        shop_return_screen = None  # "station" / "moon" - where ESC closes back to
        pilot_name_dialog = None
        pause_menu = PauseMenu()
        save_dialog = None
        delete_confirm_dialog = None
        overwrite_confirm_dialog = None
        load_menu = None
        load_return_screen = None  # "pause" when the Load menu was opened from the pause menu (ESC/load returns there), else None -> main menu
        star_map = None
        video_menu = None
        video_aspect = None  # aspect group being browsed in Video Settings
        current_screen = "menu"
        previous_screen = None
        running = True
        pilot_name = ""
        selected_story = "default"

        # Fixed-timestep accumulator (see docs/BACKLOG.md and step_world()).
        # Each iteration: read input once, drain this many real seconds of
        # elapsed time through step_world() in fixed 1/60 s chunks, render
        # once. accumulator carries the sub-step remainder between frames.
        sim_accumulator = 0.0
        prev_frame_start = time.perf_counter()

        while running:
            events = pygame.event.get()
            # With a vsync'd display the flip() itself paces the frame rate;
            # a tight clock.tick(FPS) on top of it just fights the vblank
            # (judder), so only a loose safety cap runs then. Without vsync,
            # the FPS cap is the only thing holding 60.
            clock.tick(VSYNC_SAFETY_FPS if vsync_display else FPS)
            # Frame-timing metrics (perf_metrics.metrics): started here, after
            # the clock.tick() FPS-cap sleep, so the sleep isn't charged to any
            # phase. Split into input / sim / render / present below; shown
            # bottom-left when DEBUG_MODE is on. See docs/UI_FLOW.md.
            t_frame_start = time.perf_counter()
            # Feed the accumulator the real elapsed time at full precision -
            # clock.tick()'s own return value is whole milliseconds, and that
            # quantization (16 vs 17 for a true 16.667 ms frame) is enough to
            # cost the sim a step here and there = stutter.
            real_dt = t_frame_start - prev_frame_start
            prev_frame_start = t_frame_start

            # Handle window close button globally (all screens automatically support it)
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break

            if not running:
                break

            # The window is freely resizable, but the SCALED logical surface is
            # fixed (see open_window): SDL scales it to the window and remaps
            # mouse coords, so VIDEORESIZE needs no handling. The logical size
            # only changes via the Video Settings menu (apply_resolution).
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKQUOTE:
                    constants.DEBUG_MODE = not constants.DEBUG_MODE
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_m and (event.mod & pygame.KMOD_CTRL):
                    # Global audio mute (Ctrl+M) - works on every screen, so
                    # it's handled here next to QUIT/DEBUG rather than in any
                    # one screen. Toggles both the SFX board and the music.
                    sound_board.muted = not sound_board.muted
                    music.toggle_mute()

            # ========================================================
            # PHASE 1 - input & screen transitions (once per iteration)
            # No update()/update_physics()/draw() here: simulation runs in
            # PHASE 2 (the accumulator), rendering in PHASE 3. A transition
            # requested here takes effect before PHASE 2, so the accumulator
            # never steps the screen the player just left.
            # ========================================================
            if current_screen == "menu":
                selection = menu.handle_input(events)
                if selection == "quit":
                    running = False
                elif selection == "new":
                    story_selector = BackdropMenu("SELECT STORY", story_menu_rows(), seed=4242, allow_cancel=True)
                    current_screen = "story_select"
                elif selection == "load":
                    load_menu = SaveBrowser("load")
                    current_screen = "load"
                elif selection == "video":
                    video_aspect = aspect_label(logical_resolution)
                    video_menu = video_settings_menu(video_aspect)
                    current_screen = "video_settings"

            elif current_screen == "video_settings":
                choice = video_menu.handle_input(events)
                if choice == "cancel":
                    current_screen = "menu"
                    menu = main_menu()
                elif choice == "aspect":
                    video_menu = video_aspect_menu(video_aspect)
                    current_screen = "video_aspect"
                elif choice:
                    w, h = (int(n) for n in choice.split("x"))
                    if (w, h) != logical_resolution:
                        apply_resolution((w, h))  # ~150ms display re-init; menu-only
                    video_aspect = aspect_label(logical_resolution)
                    video_menu = video_settings_menu(video_aspect)  # refresh markers

            elif current_screen == "video_aspect":
                choice = video_menu.handle_input(events)
                if choice:
                    if choice != "cancel":
                        video_aspect = choice
                    video_menu = video_settings_menu(video_aspect)
                    current_screen = "video_settings"

            elif current_screen == "story_select":
                story = story_selector.handle_input(events)
                if story and story != "cancel":
                    selected_story = story
                    pilot_name_dialog = PilotNameDialog()
                    current_screen = "pilot_name"
                elif story == "cancel":
                    current_screen = "menu"

            elif current_screen == "pilot_name":
                result = pilot_name_dialog.handle_input(events)
                if result and result != "cancel":
                    pilot_name = result
                    game_screen = SpaceScreen(pilot_name=pilot_name, story=selected_story)
                    # Where the new game begins is story.json's "start" block
                    # (defaults: ship-less, in the station's "default" interior) -
                    # begin_new_game() also fires the tutorial if its trigger
                    # is "new_game" / a starting ship was granted.
                    start_location, start_interior = game_screen.begin_new_game()
                    if start_location == "space":
                        current_screen = "game"
                    elif start_location == "moon":
                        moon_interior = game_screen.get_interior_screen(game_screen.moon, start_interior)
                        if moon_interior:
                            moon_interior.arrive_from("ship")
                        current_screen = "moon"
                    else:
                        station_interior = game_screen.get_interior_screen(game_screen.station, start_interior)
                        if station_interior:
                            station_interior.arrive_from("ship")
                        current_screen = "station"
                elif result == "cancel":
                    current_screen = "menu"

            elif current_screen == "load":
                if delete_confirm_dialog:
                    confirm_action, filename = delete_confirm_dialog.handle_input(events)
                    if confirm_action == "confirm":
                        try:
                            filepath = f"{SAVE_DIR}/{filename}"
                            if os.path.exists(filepath):
                                os.remove(filepath)
                        except:
                            pass
                        delete_confirm_dialog = None
                        load_menu = SaveBrowser("load")
                    elif confirm_action == "cancel":
                        delete_confirm_dialog = None
                    elif confirm_action == "quit":
                        running = False
                else:
                    action, filename = load_menu.handle_input(events)
                    if action == "load":
                        save_data = load_save_file(filename)
                        if save_data:
                            pilot_name = save_data.get("pilot_name", "")
                            game_state = save_data.get("game_state", {})
                            location = game_state.get("location", "space")
                            warn_if_story_version_mismatch(game_state.get("story", "default"), game_state.get("story_version"))

                            if location == "space":
                                game_screen = SpaceScreen(save_data.get("system", {}), pilot_name=pilot_name, story=game_state.get("story", "default"), system_id=game_state.get("system_id"))
                                game_screen.restore_state(game_state)
                                current_screen = "game"
                            elif location == "station":
                                game_screen = SpaceScreen(save_data.get("system", {}), pilot_name=pilot_name, story=game_state.get("story", "default"), system_id=game_state.get("system_id"))
                                # NOT restore_state() - game_state["player"]
                                # here is the LocationScreen's own walking
                                # position, not the ship's space position;
                                # feeding it to restore_state() scattered the
                                # ship to whatever that interior coordinate
                                # happened to be instead of docking it at the
                                # station. park_at() puts the ship where the
                                # fiction says it actually is - docked.
                                game_screen.restore_possessions(game_state)
                                game_screen.park_at(game_screen.station)
                                # Always resume in whichever interior the ship
                                # actually docks at, not whatever the save
                                # recorded in station_location (a now-removed
                                # key like "dormitory" for an old save) -
                                # matches landing fresh from space, below.
                                ship_entry_key = game_screen.station.get_ship_entry_key()
                                station_interior = game_screen.get_interior_screen(game_screen.station, ship_entry_key)
                                if station_interior:
                                    station_interior.restore_state(game_state)
                                    station_interior.arrive_from("ship")
                                current_screen = "station"
                            elif location == "moon":
                                game_screen = SpaceScreen(save_data.get("system", {}), pilot_name=pilot_name, story=game_state.get("story", "default"), system_id=game_state.get("system_id"))
                                game_screen.restore_possessions(game_state)  # see the station branch above for why not restore_state()
                                game_screen.park_at(game_screen.moon)
                                moon_location = game_state.get("moon_location", "city")
                                if moon_location not in game_screen.moon.interiors:
                                    moon_location = "city"
                                moon_interior = game_screen.get_interior_screen(game_screen.moon, moon_location)
                                if moon_interior:
                                    moon_interior.restore_state(game_state)
                                current_screen = "moon"
                            # A load fully replaces the running game, so the
                            # "opened from pause" link is spent either way.
                            load_return_screen = None
                    elif action == "delete":
                        delete_confirm_dialog = ConfirmDialog("Delete Save?", save_display_name(filename)[:50], context_data=filename)
                    elif action == "cancel":
                        if load_return_screen == "pause":
                            current_screen = "pause"
                            load_return_screen = None
                        else:
                            current_screen = "menu"
                            menu = main_menu()

            elif current_screen == "game":
                action = game_screen.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "pause":
                    previous_screen = "game"
                    current_screen = "pause"
                elif action == "land":
                    next_screen, si, ls = begin_landing(game_screen)
                    if next_screen == "station":
                        station_interior = si
                    elif next_screen == "select_location":
                        location_selector = ls
                    current_screen = next_screen
                elif action == "star_map":
                    star_map = StarMap(game_screen.story, game_screen.system_id, game_screen.selected_system_id)
                    current_screen = "star_map"
                elif action == "possessions":
                    possessions_menu = ReportMenu(*possessions_report(game_screen.player.person.possessions, game_screen.story, game_screen.player.ship))
                    possessions_return_screen = "game"
                    current_screen = "possessions"
                elif action == "missions":
                    mission_log = ReportMenu(*mission_report(game_screen.missions_config, game_screen.player.person.possessions))
                    missions_return_screen = "game"
                    current_screen = "missions"
                # Simulation (including the "an open hail freezes the world"
                # rule) runs in PHASE 2 via step_world().

            elif current_screen == "star_map":
                action = star_map.handle_input(events)
                if _pressed_any(events, pygame.K_m, pygame.K_ESCAPE):
                    action = "close"
                elif _pressed_any(events, pygame.K_j):
                    action = "jump"
                if action in ("close", "jump"):
                    game_screen.selected_system_id = star_map.selected_system_id
                    current_screen = "game"
                    if action == "jump":
                        # Same path as pressing J in the space view - validates
                        # the selection/distance and shows "too close" feedback
                        # for a self-jump from near the system centre.
                        game_screen.try_jump()
                # Unlike docking at the station/moon, opening the jump map
                # fully pauses the simulation (matches PauseMenu) - step_world()
                # does nothing for "star_map".

            elif current_screen == "station":
                action = station_interior.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "pause":
                    previous_screen = "station"
                    current_screen = "pause"
                elif action == "exit":
                    game_screen.board_ship()
                    current_screen = "game"
                elif action == "exit_menu":
                    exit_menu = ChoiceDialog("Where To?", exit_options(station_interior.get_exit_options(), game_screen.station.interiors, station_interior.get_exit_disabled_reasons()))
                    exit_menu_landing_site = game_screen.station
                    exit_menu_return_screen = "station"
                    current_screen = "exit_menu"
                elif action and action.startswith("exit_to:"):
                    origin_key = station_interior.interior_key
                    station_interior = game_screen.get_interior_screen(game_screen.station, action.split(":", 1)[1])
                    station_interior.arrive_from(origin_key)
                elif action == "possessions":
                    possessions_menu = ReportMenu(*possessions_report(station_interior.player.possessions, game_screen.story, game_screen.player.ship))
                    possessions_return_screen = "station"
                    current_screen = "possessions"
                elif action == "missions":
                    mission_log = ReportMenu(*mission_report(game_screen.missions_config, station_interior.player.possessions))
                    missions_return_screen = "station"
                    current_screen = "missions"
                elif action == "shop":
                    shop_menu = build_shop_menu(station_interior.player.possessions, game_screen.story, station_interior.active_shop, game_screen.player.ship.cargo_capacity, station_interior.buy_ship, game_screen.reapply_outfits)
                    shop_return_screen = "station"
                    current_screen = "shop"
                # Space physics stays running while docked, and the
                # "a conversation freezes the world" rule - both in
                # step_world() (PHASE 2).

            elif current_screen == "select_location":
                location_key = location_selector.handle_input(events)
                if location_key == "cancel":
                    current_screen = "game"
                elif location_key:
                    moon_interior = game_screen.get_interior_screen(game_screen.moon, location_key)
                    moon_interior.arrive_from("ship")
                    current_screen = "moon"

            elif current_screen == "exit_menu":
                choice = exit_menu.handle_input(events)
                if choice == "ship":
                    game_screen.board_ship()
                    current_screen = "game"
                elif choice == "cancel":
                    current_screen = exit_menu_return_screen
                elif choice:
                    is_station = exit_menu_landing_site is game_screen.station
                    origin_key = (station_interior if is_station else moon_interior).interior_key
                    interior = game_screen.get_interior_screen(exit_menu_landing_site, choice)
                    interior.arrive_from(origin_key)
                    if is_station:
                        station_interior = interior
                    else:
                        moon_interior = interior
                    current_screen = exit_menu_return_screen
                # A modal, like PauseMenu - the rest of the world (space
                # physics, other cached interiors) stays frozen while it's
                # open (step_world() does nothing for "exit_menu"). The
                # interior it sits over is redrawn each frame in PHASE 3.

            elif current_screen == "possessions":
                action = possessions_menu.handle_input(events)
                if _pressed_any(events, pygame.K_p, pygame.K_ESCAPE):
                    action = "close"
                if action == "close":
                    current_screen = possessions_return_screen
                # A modal menu, like PauseMenu - the world stays frozen
                # while it's open (step_world() does nothing here).

            elif current_screen == "missions":
                action = mission_log.handle_input(events)
                if _pressed_any(events, pygame.K_n, pygame.K_ESCAPE):
                    action = "close"
                if action == "close":
                    current_screen = missions_return_screen
                # Modal - world frozen (step_world() does nothing here).

            elif current_screen == "shop":
                action = shop_menu.handle_input(events)
                if action == "close":
                    current_screen = shop_return_screen
                # Modal - world frozen (step_world() does nothing here).

            elif current_screen == "moon":
                action = moon_interior.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "exit":
                    game_screen.board_ship()
                    current_screen = "game"
                elif action == "pause":
                    previous_screen = "moon"
                    current_screen = "pause"
                elif action == "exit_menu":
                    exit_menu = ChoiceDialog("Where To?", exit_options(moon_interior.get_exit_options(), game_screen.moon.interiors, moon_interior.get_exit_disabled_reasons()))
                    exit_menu_landing_site = game_screen.moon
                    exit_menu_return_screen = "moon"
                    current_screen = "exit_menu"
                elif action and action.startswith("exit_to:"):
                    origin_key = moon_interior.interior_key
                    moon_interior = game_screen.get_interior_screen(game_screen.moon, action.split(":", 1)[1])
                    moon_interior.arrive_from(origin_key)
                elif action == "possessions":
                    possessions_menu = ReportMenu(*possessions_report(moon_interior.player.possessions, game_screen.story, game_screen.player.ship))
                    possessions_return_screen = "moon"
                    current_screen = "possessions"
                elif action == "missions":
                    mission_log = ReportMenu(*mission_report(game_screen.missions_config, moon_interior.player.possessions))
                    missions_return_screen = "moon"
                    current_screen = "missions"
                elif action == "shop":
                    shop_menu = build_shop_menu(moon_interior.player.possessions, game_screen.story, moon_interior.active_shop, game_screen.player.ship.cargo_capacity, moon_interior.buy_ship, game_screen.reapply_outfits)
                    shop_return_screen = "moon"
                    current_screen = "shop"
                # Space physics stays running while on the moon, and the
                # "a conversation freezes the world" rule - both in
                # step_world() (PHASE 2).

            elif current_screen == "pause":
                dialog_was_open = bool(delete_confirm_dialog or overwrite_confirm_dialog or save_dialog)

                if delete_confirm_dialog:
                    dialog_action, filename = delete_confirm_dialog.handle_input(events)
                    if dialog_action == "confirm":
                        try:
                            filepath = f"{SAVE_DIR}/{filename}"
                            if os.path.exists(filepath):
                                os.remove(filepath)
                            pause_menu.success_timer = 120
                        except:
                            pass
                        delete_confirm_dialog = None
                        if save_dialog:
                            save_dialog.existing_saves = save_dialog._get_all_saves()
                    elif dialog_action == "cancel":
                        delete_confirm_dialog = None

                elif overwrite_confirm_dialog:
                    dialog_action, save_name = overwrite_confirm_dialog.handle_input(events)
                    if dialog_action == "confirm":
                        # Proceed with overwrite
                        save_description = save_name
                        if save_name.startswith("save_") and save_name.endswith(".json"):
                            save_description = save_name[5:-5]

                        # Delete old save
                        try:
                            filepath = f"{SAVE_DIR}/{save_name}"
                            if os.path.exists(filepath):
                                os.remove(filepath)
                        except:
                            pass

                        # Save new game
                        game_state, system_config_snapshot = build_save_game_state(game_screen, previous_screen, station_interior, moon_interior)
                        create_save_file(pilot_name, save_description, system_config_snapshot, {}, game_state)
                        pause_menu.success_timer = 120
                        overwrite_confirm_dialog = None
                    elif dialog_action == "cancel":
                        overwrite_confirm_dialog = None

                elif save_dialog:
                    dialog_action, save_name = save_dialog.handle_input(events)
                    if dialog_action == "save":
                        # Check if we're overwriting an existing save
                        is_overwriting = save_name in save_dialog.existing_saves
                        if is_overwriting:
                            # Show confirmation dialog for overwrite
                            overwrite_confirm_dialog = ConfirmDialog("Overwrite Save?", save_display_name(save_name)[:50], context_data=save_name)
                            save_dialog = None
                        else:
                            save_description = save_name
                            if not pilot_name and save_description:
                                pilot_name = save_description
                                if game_screen:
                                    game_screen.pilot_name = pilot_name
                                if station_interior:
                                    station_interior.pilot_name = pilot_name

                            # Save new game
                            game_state, system_config_snapshot = build_save_game_state(game_screen, previous_screen, station_interior, moon_interior)
                            create_save_file(pilot_name, save_description, system_config_snapshot, {}, game_state)
                            pause_menu.success_timer = 120
                            save_dialog = None
                    elif dialog_action == "cancel":
                        save_dialog = None
                    elif dialog_action == "delete":
                        delete_confirm_dialog = ConfirmDialog("Delete Save?", save_display_name(save_name)[:50], context_data=save_name)

                if not dialog_was_open:
                    action = pause_menu.handle_input(events)
                    if _pressed_any(events, pygame.K_ESCAPE):
                        # ESC opened the pause menu (from the space view / an
                        # interior) - pressing it again resumes, same toggle
                        # affordance the M/P/N overlays have. Only when no
                        # save/load sub-dialog is on top.
                        action = "resume"
                    if action == "resume":
                        current_screen = previous_screen
                    elif action == "save":
                        save_dialog = SaveBrowser("save", pilot_name=pilot_name)
                    elif action == "load":
                        load_menu = SaveBrowser("load")
                        load_return_screen = "pause"
                        current_screen = "load"
                    elif action == "quit":
                        current_screen = "menu"
                        menu = main_menu()

            # Background music follows the screen: the "menu" loop on the
            # menu/story/pilot/load screens, the sparser "ingame" loop
            # everywhere else. set_scene() is a cheap no-op when the track
            # isn't changing; pump() advances a track's incremental synthesis
            # by a few ms (a no-op once both tracks are built).
            music.set_scene(current_screen)
            music.pump()

            t_after_input = time.perf_counter()

            # ========================================================
            # PHASE 2 - fixed-timestep simulation
            # Drain the real time elapsed since the last frame in fixed
            # 1/60 s steps. On a machine holding 60 FPS this runs exactly
            # once (byte-identical to the old one-step-per-frame loop); it
            # only runs 2+ times to catch up after a slow frame, and is
            # clamped so it can't spiral. A step that itself triggers a
            # screen change (autopilot auto-land) stops the drain.
            # ========================================================
            sim_accumulator, n_steps = advance_accumulator(sim_accumulator, real_dt)
            for _ in range(n_steps):
                step_transition = step_world(current_screen, game_screen, station_interior, moon_interior)
                if step_transition == "land":
                    next_screen, si, ls = begin_landing(game_screen)
                    if next_screen == "station":
                        station_interior = si
                    elif next_screen == "select_location":
                        location_selector = ls
                    current_screen = next_screen
                    break

            t_after_sim = time.perf_counter()

            # ========================================================
            # PHASE 3 - render (once per iteration)
            # Draws whatever current_screen now is. Modal screens redraw
            # the frozen world/interior they sit over, then their overlay.
            # ========================================================
            if current_screen == "menu":
                menu.draw(screen)
            elif current_screen == "story_select":
                story_selector.draw(screen)
            elif current_screen == "pilot_name":
                pilot_name_dialog.draw(screen)
            elif current_screen == "load":
                load_menu.draw(screen)
                if delete_confirm_dialog:
                    delete_confirm_dialog.draw(screen)
            elif current_screen in ("video_settings", "video_aspect"):
                video_menu.draw(screen)
            elif current_screen == "game":
                game_screen.draw(screen)
            elif current_screen == "star_map":
                star_map.draw(screen)
            elif current_screen == "station":
                if station_interior:
                    station_interior.draw(screen)
            elif current_screen == "select_location":
                location_selector.draw(screen)
            elif current_screen == "exit_menu":
                # The exit ChoiceDialog only paints a centered panel, not a
                # full-screen fill, so the interior being left must be
                # redrawn under it every frame - otherwise the *previous*
                # frame's interior (e.g. the spaceport, NPCs and all) shows
                # through, looking like an NPC in two rooms at once.
                if exit_menu_return_screen == "station" and station_interior:
                    station_interior.draw(screen, draw_hud=False)
                elif exit_menu_return_screen == "moon" and moon_interior:
                    moon_interior.draw(screen, draw_hud=False)
                exit_menu.draw(screen)
            elif current_screen == "possessions":
                if possessions_return_screen == "game" and game_screen:
                    game_screen.draw(screen, draw_hud=False)
                elif possessions_return_screen == "station" and station_interior:
                    station_interior.draw(screen, draw_hud=False)
                elif possessions_return_screen == "moon" and moon_interior:
                    moon_interior.draw(screen, draw_hud=False)
                possessions_menu.draw(screen)
            elif current_screen == "missions":
                if missions_return_screen == "game" and game_screen:
                    game_screen.draw(screen, draw_hud=False)
                elif missions_return_screen == "station" and station_interior:
                    station_interior.draw(screen, draw_hud=False)
                elif missions_return_screen == "moon" and moon_interior:
                    moon_interior.draw(screen, draw_hud=False)
                mission_log.draw(screen)
            elif current_screen == "shop":
                if shop_return_screen == "station" and station_interior:
                    station_interior.draw(screen, draw_hud=False)
                elif shop_return_screen == "moon" and moon_interior:
                    moon_interior.draw(screen, draw_hud=False)
                shop_menu.draw(screen)
            elif current_screen == "moon":
                if moon_interior:
                    moon_interior.draw(screen)
            elif current_screen == "pause":
                pause_menu.update()  # render-side banner animation, not simulation
                # draw_hud=False since PauseMenu.draw() immediately fills
                # the whole screen black anyway - this is just to keep
                # camera-follow/animation state current, not for the HUD
                # to actually be seen.
                if previous_screen == "game" and game_screen:
                    game_screen.draw(screen, draw_hud=False)
                elif previous_screen == "station" and station_interior:
                    station_interior.draw(screen, draw_hud=False)
                pause_menu.draw(screen)
                if delete_confirm_dialog:
                    delete_confirm_dialog.draw(screen)
                elif overwrite_confirm_dialog:
                    overwrite_confirm_dialog.draw(screen)
                elif save_dialog:
                    save_dialog.draw(screen)

            # DEBUG-only perf panel, drawn over whatever screen is active.
            perf_metrics.draw_overlay(screen)
            t_after_render = time.perf_counter()

            pygame.display.flip()
            t_after_present = time.perf_counter()

            perf_metrics.metrics.record(
                {
                    "input": (t_after_input - t_frame_start) * 1000.0,
                    "sim": (t_after_sim - t_after_input) * 1000.0,
                    "render": (t_after_render - t_after_sim) * 1000.0,
                    "present": (t_after_present - t_after_render) * 1000.0,
                },
                n_steps,
                clock.get_fps(),
            )

        pygame.quit()
    except Exception as e:
        with open("error.txt", "w") as f:
            f.write(str(e))
            import traceback
            f.write("\n" + traceback.format_exc())
        pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
