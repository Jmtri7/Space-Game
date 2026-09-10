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
    advance_accumulator, save_display_name, load_settings, save_settings, resolve_ending
)
from game.world.player_controller import PlayerController
from game.audio.sound_board import sound_board
from game.audio.music import music
from game.screens.space_screen import SpaceScreen
from game.ui.backdrop_menu import BackdropMenu
from game.ui.pilot_name_dialog import PilotNameDialog
from game.ui.intro_screen import IntroScreen, intro_report, has_intro
from game.ui.choice_dialog import ChoiceDialog
from game.ui.report_menu import ReportMenu, possessions_report, mission_report
from game.ui.ending_screen import EndingScreen, ending_report
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
    chosen in Settings -> Video (and applied via a full display
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


# Supersample-AA offscreen buffer (Settings -> Video). When
# constants.AA_MODE == "supersample", PHASE 3 renders the whole frame here at
# 2x the logical resolution and smoothscales it down onto `screen`. Lazily
# (re)allocated to match the current logical size and dropped whenever the
# resolution changes. The "gfxdraw" AA mode needs no buffer - it's
# per-primitive in game/aa_draw.py.
_hires_surface = None


def _hires_target(size):
    global _hires_surface
    if _hires_surface is None or _hires_surface.get_size() != tuple(size):
        _hires_surface = pygame.Surface(size).convert()
    return _hires_surface


def _invalidate_hires_surface():
    global _hires_surface
    _hires_surface = None


def apply_resolution(size):
    """Switch the SCALED logical resolution (from the Settings menu) and
    persist it. A live SCALED renderer can't be re-`set_mode()`'d, so the
    whole display is torn down and re-initialised. Safe even though Settings
    is now reachable mid-game from the pause menu: no screen or world object
    holds a persistent Surface (every draw() builds its scratch surfaces
    fresh each frame), and the one long-lived buffer, `_hires_surface`, is
    dropped here."""
    global screen, logical_resolution
    pygame.display.quit()
    pygame.display.init()
    pygame.display.set_caption("Space Game")
    screen = open_window(size, measure_vsync=False)
    set_screen_size(*size)
    logical_resolution = tuple(size)
    _invalidate_hires_surface()
    settings = load_settings()
    settings["resolution"] = list(size)
    save_settings(settings)


logical_resolution = load_resolution()
_saved_settings = load_settings()
if _saved_settings.get("aa_mode") in constants.AA_MODES:
    constants.AA_MODE = _saved_settings["aa_mode"]
elif _saved_settings.get("supersample_aa"):        # pre-"aa_mode" settings.json
    constants.AA_MODE = "supersample"
screen = open_window(logical_resolution)
set_screen_size(*logical_resolution)
screen.fill((0, 0, 0))
pygame.display.flip()
pygame.display.set_caption("Space Game")
clock = pygame.time.Clock()


# main()'s loop helpers live in their own module now; re-exported so any
# `main.<helper>` reference (tests, saved habits) still resolves.
from game.app.loop_helpers import (  # noqa: E402
    build_save_game_state, _pressed_any, build_shop_menu, story_menu_rows,
    landing_location_options, exit_options, warn_if_module_version_mismatch,
    warn_if_story_version_mismatch, update_background_locations, begin_landing,
    step_world, main_menu,
)

# Tabs shown by the Settings menu, in order. "Video" is the only one for now;
# add a label here and a matching branch in settings_menu() to grow it.
SETTINGS_TABS = ["Video"]


def settings_menu(aspect, tab="Video"):
    """The Settings menu (main menu -> SETTINGS, or the pause menu). A tab
    strip over the active tab's rows, then **Back**. Mouse-only.

    **Video** tab: an **Anti-aliasing** row that cycles constants.AA_MODE
    (Off / gfxdraw / Supersampling x2 - see game/aa_draw.py and main()'s
    PHASE 3 render path), a row that opens the aspect-ratio picker, then the
    fixed SCALED logical resolutions in `aspect` (see open_window) - the
    active one marked "Current resolution", the native one "Native
    resolution". A resolution click applies it immediately
    (apply_resolution)."""
    rows = []
    if tab == "Video":
        aa = constants.AA_MODE_LABELS.get(constants.AA_MODE, "Off")
        rows.append(("aa_cycle", f"Anti-aliasing  ·  {aa}",
                     "Click to cycle. gfxdraw smooths ship / station / building / "
                     "figure edges cheaply. Supersampling x2 renders the whole "
                     "frame at 2x and downscales - smoother everywhere (UI too) "
                     "but costs GPU time each frame."))
        aspect_desc = None if aspect == NATIVE_ASPECT else f"Your display is {NATIVE_ASPECT}"
        rows.append(("aspect", f"Aspect ratio  ·  {aspect}", aspect_desc))
        for w, h in resolutions_for_aspect(aspect):
            if (w, h) == logical_resolution:
                marker = "Current resolution"
            elif (w, h) == NATIVE_RESOLUTION:
                marker = "Native resolution"
            else:
                marker = None
            rows.append((f"{w}x{h}", f"{w} × {h}", marker))
    return BackdropMenu("SETTINGS", rows, allow_cancel=True, tabs=(tab, SETTINGS_TABS))


def video_aspect_menu(selected):
    """The aspect-ratio picker reached from Settings -> Video. One row per
    available_aspects() entry - the one in use marked "Selected", the
    monitor's own marked "Native" when it isn't the selected one. Picking one
    (or Back) returns to Settings with its resolution list refiltered."""
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
        ending_menu = None
        intro_menu = None
        intro_next_screen = None  # target screen once the intro's Begin is pressed
        shop_return_screen = None  # "station" / "moon" - where ESC closes back to
        pilot_name_dialog = None
        pause_menu = PauseMenu()
        save_dialog = None
        delete_confirm_dialog = None
        overwrite_confirm_dialog = None
        load_menu = None
        load_return_screen = None  # "pause" when the Load menu was opened from the pause menu (ESC/load returns there), else None -> main menu
        star_map = None
        star_map_return_screen = None  # "game" / "station" / "moon" - where 1/ESC closes back to (jump only works from "game")
        video_menu = None
        video_aspect = None  # aspect group being browsed in Settings -> Video
        settings_return_screen = None  # "pause" if Settings was opened from the pause menu, else -> main menu
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
            # only changes via Settings -> Video (apply_resolution).
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
                elif selection == "settings":
                    video_aspect = aspect_label(logical_resolution)
                    video_menu = settings_menu(video_aspect)
                    settings_return_screen = None
                    current_screen = "settings"

            elif current_screen == "settings":
                choice = video_menu.handle_input(events)
                if choice == "cancel":
                    if settings_return_screen == "pause":
                        current_screen = "pause"
                    else:
                        current_screen = "menu"
                        menu = main_menu()
                elif choice and choice.startswith("tab:"):
                    pass  # "Video" is the only tab today - selecting it is a no-op
                elif choice == "aa_cycle":
                    _i = constants.AA_MODES.index(constants.AA_MODE) if constants.AA_MODE in constants.AA_MODES else 0
                    constants.AA_MODE = constants.AA_MODES[(_i + 1) % len(constants.AA_MODES)]
                    _settings = load_settings()
                    _settings["aa_mode"] = constants.AA_MODE
                    _settings.pop("supersample_aa", None)  # superseded by aa_mode
                    save_settings(_settings)
                    _invalidate_hires_surface()
                    video_menu = settings_menu(video_aspect)  # refresh the AA label
                elif choice == "aspect":
                    video_menu = video_aspect_menu(video_aspect)
                    current_screen = "settings_aspect"
                elif choice:
                    w, h = (int(n) for n in choice.split("x"))
                    if (w, h) != logical_resolution:
                        apply_resolution((w, h))  # ~150ms display re-init; menu-only
                    video_aspect = aspect_label(logical_resolution)
                    video_menu = settings_menu(video_aspect)  # refresh markers

            elif current_screen == "settings_aspect":
                choice = video_menu.handle_input(events)
                if choice:
                    if choice != "cancel":
                        video_aspect = choice
                    video_menu = settings_menu(video_aspect)
                    current_screen = "settings"

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
                    # Stories with an "intro" block get a scrolling opening
                    # crawl before the world appears; Begin drops through to
                    # the start screen resolved above.
                    if has_intro(selected_story):
                        intro_menu = IntroScreen(*intro_report(selected_story, pilot_name))
                        intro_next_screen = current_screen
                        current_screen = "intro"
                elif result == "cancel":
                    current_screen = "menu"

            elif current_screen == "intro":
                action = intro_menu.handle_input(events)
                if action == "begin" or _pressed_any(events, pygame.K_ESCAPE, pygame.K_RETURN):
                    current_screen = intro_next_screen
                    intro_menu = None

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
                            warn_if_module_version_mismatch(game_state.get("story", "default"), game_state.get("module_versions"))

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
                    star_map = StarMap(game_screen.story, game_screen.system_id, game_screen.selected_system_id,
                                       flags=game_screen.player.person.possessions.flags)
                    star_map_return_screen = "game"
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
                if _pressed_any(events, pygame.K_1, pygame.K_ESCAPE):
                    action = "close"
                elif _pressed_any(events, pygame.K_v):
                    action = "jump"
                if action in ("close", "jump"):
                    game_screen.selected_system_id = star_map.selected_system_id
                    current_screen = star_map_return_screen or "game"
                    # Jumping only makes sense from the cockpit - from a
                    # station/moon interior the map is view-and-select only
                    # (the selection still persists for when you next launch).
                    if action == "jump" and star_map_return_screen == "game":
                        # Same path as pressing 2 in the space view - validates
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
                elif action == "star_map":
                    star_map = StarMap(game_screen.story, game_screen.system_id, game_screen.selected_system_id,
                                       flags=station_interior.player.possessions.flags)
                    star_map_return_screen = "station"
                    current_screen = "star_map"
                elif action == "shop":
                    shop_menu = build_shop_menu(station_interior.player.possessions, game_screen.story, station_interior.active_shop, game_screen.player.ship.cargo_capacity, station_interior.buy_ship, game_screen.reapply_outfits, station_interior.switch_ship)
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
                if _pressed_any(events, pygame.K_2, pygame.K_ESCAPE):
                    action = "close"
                if action == "close":
                    current_screen = possessions_return_screen
                # A modal menu, like PauseMenu - the world stays frozen
                # while it's open (step_world() does nothing here).

            elif current_screen == "missions":
                action = mission_log.handle_input(events)
                if _pressed_any(events, pygame.K_3, pygame.K_ESCAPE):
                    action = "close"
                if action == "close":
                    current_screen = missions_return_screen
                # Modal - world frozen (step_world() does nothing here).

            elif current_screen == "shop":
                action = shop_menu.handle_input(events)
                # ESC closes the shop / outfitter / shipyard (opened with T,
                # so there's no opening key to toggle - see the key-opened
                # modals' _pressed_any handling above and CONTROLS.md's
                # Menus note). A nested sub-widget - the shipyard's purchase
                # ConfirmDialog, or the outfitter's compatible-spares picker
                # - eats the ESC as its own cancel first (both are otherwise
                # mouse-only).
                if _pressed_any(events, pygame.K_ESCAPE):
                    if getattr(shop_menu, "confirm", None) is not None:
                        shop_menu.confirm = None
                    elif getattr(shop_menu, "picker", None) is not None:
                        shop_menu.picker = None
                    elif action != "close":
                        action = "close"
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
                elif action == "star_map":
                    star_map = StarMap(game_screen.story, game_screen.system_id, game_screen.selected_system_id,
                                       flags=moon_interior.player.possessions.flags)
                    star_map_return_screen = "moon"
                    current_screen = "star_map"
                elif action == "shop":
                    shop_menu = build_shop_menu(moon_interior.player.possessions, game_screen.story, moon_interior.active_shop, game_screen.player.ship.cargo_capacity, moon_interior.buy_ship, game_screen.reapply_outfits, moon_interior.switch_ship)
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
                    elif action == "settings":
                        video_aspect = aspect_label(logical_resolution)
                        video_menu = settings_menu(video_aspect)
                        settings_return_screen = "pause"
                        current_screen = "settings"
                    elif action == "quit":
                        current_screen = "menu"
                        menu = main_menu()

            elif current_screen == "ending":
                action = ending_menu.handle_input(events)
                if action == "menu" or _pressed_any(events, pygame.K_ESCAPE, pygame.K_RETURN):
                    current_screen = "menu"
                    menu = main_menu()
                # Modal - the world is over (step_world does nothing here).

            # An "end_story:<id>" dialogue action (see game/world/dialogue.py)
            # set the story_over / ending:<id> flags this frame - hand off to
            # the epilogue screen. Checked once, centrally, since the action
            # can fire from a station conversation or a ship hail alike.
            if game_screen is not None and current_screen in ("game", "station", "moon"):
                ending_id = resolve_ending(game_screen.player.person.possessions.flags)
                if ending_id is not None:
                    ending_menu = EndingScreen(*ending_report(
                        game_screen.story, ending_id, game_screen.player.person.possessions))
                    current_screen = "ending"

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
            #
            # AA_MODE == "supersample" (Settings -> Video): the frame is drawn
            # to a 2x-logical offscreen surface (`dst`) with the reported
            # screen size temporarily doubled - everything is resolution
            # independent (utils.to_screen / get_ui_scale derive from the
            # screen size), so this just renders bigger - then smoothscaled
            # back down onto `screen`. Input handling (PHASE 1) always runs at
            # the logical size, so hit-testing is unaffected. Other modes ->
            # `dst` is `screen` and the wrapper is a no-op ("gfxdraw" mode does
            # its AA per-primitive in game/aa_draw.py; "off" does nothing).
            # ========================================================
            _ss_aa = constants.AA_MODE == "supersample"
            if _ss_aa:
                _lw, _lh = screen.get_size()
                dst = _hires_target((_lw * 2, _lh * 2))
                set_screen_size(_lw * 2, _lh * 2)
            else:
                dst = screen

            if current_screen == "menu":
                menu.draw(dst)
            elif current_screen == "story_select":
                story_selector.draw(dst)
            elif current_screen == "pilot_name":
                pilot_name_dialog.draw(dst)
            elif current_screen == "intro":
                dst.fill((6, 8, 16))
                intro_menu.draw(dst)
            elif current_screen == "load":
                load_menu.draw(dst)
                if delete_confirm_dialog:
                    delete_confirm_dialog.draw(dst)
            elif current_screen in ("settings", "settings_aspect"):
                video_menu.draw(dst)
            elif current_screen == "game":
                game_screen.draw(dst)
            elif current_screen == "star_map":
                star_map.draw(dst)
            elif current_screen == "station":
                if station_interior:
                    station_interior.draw(dst)
            elif current_screen == "select_location":
                location_selector.draw(dst)
            elif current_screen == "exit_menu":
                # The exit ChoiceDialog only paints a centered panel, not a
                # full-screen fill, so the interior being left must be
                # redrawn under it every frame - otherwise the *previous*
                # frame's interior (e.g. the spaceport, NPCs and all) shows
                # through, looking like an NPC in two rooms at once.
                if exit_menu_return_screen == "station" and station_interior:
                    station_interior.draw(dst, draw_hud=False)
                elif exit_menu_return_screen == "moon" and moon_interior:
                    moon_interior.draw(dst, draw_hud=False)
                exit_menu.draw(dst)
            elif current_screen == "possessions":
                if possessions_return_screen == "game" and game_screen:
                    game_screen.draw(dst, draw_hud=False)
                elif possessions_return_screen == "station" and station_interior:
                    station_interior.draw(dst, draw_hud=False)
                elif possessions_return_screen == "moon" and moon_interior:
                    moon_interior.draw(dst, draw_hud=False)
                possessions_menu.draw(dst)
            elif current_screen == "missions":
                if missions_return_screen == "game" and game_screen:
                    game_screen.draw(dst, draw_hud=False)
                elif missions_return_screen == "station" and station_interior:
                    station_interior.draw(dst, draw_hud=False)
                elif missions_return_screen == "moon" and moon_interior:
                    moon_interior.draw(dst, draw_hud=False)
                mission_log.draw(dst)
            elif current_screen == "shop":
                if shop_return_screen == "station" and station_interior:
                    station_interior.draw(dst, draw_hud=False)
                elif shop_return_screen == "moon" and moon_interior:
                    moon_interior.draw(dst, draw_hud=False)
                shop_menu.draw(dst)
            elif current_screen == "ending":
                dst.fill((6, 8, 16))
                ending_menu.draw(dst)
            elif current_screen == "moon":
                if moon_interior:
                    moon_interior.draw(dst)
            elif current_screen == "pause":
                pause_menu.update()  # render-side banner animation, not simulation
                # draw_hud=False since PauseMenu.draw() immediately fills
                # the whole screen black anyway - this is just to keep
                # camera-follow/animation state current, not for the HUD
                # to actually be seen.
                if previous_screen == "game" and game_screen:
                    game_screen.draw(dst, draw_hud=False)
                elif previous_screen == "station" and station_interior:
                    station_interior.draw(dst, draw_hud=False)
                pause_menu.draw(dst)
                if delete_confirm_dialog:
                    delete_confirm_dialog.draw(dst)
                elif overwrite_confirm_dialog:
                    overwrite_confirm_dialog.draw(dst)
                elif save_dialog:
                    save_dialog.draw(dst)

            if _ss_aa:
                with perf_metrics.metrics.span("render.supersample"):
                    pygame.transform.smoothscale(dst, screen.get_size(), screen)
                set_screen_size(*screen.get_size())

            # DEBUG-only perf panel, drawn over whatever screen is active.
            # Zoom is read off whichever screen instance actually drew this
            # frame - "pause"/"missions"/"shop" draw a Space/interior screen
            # behind their own overlay, so resolve through those the same
            # way the draw branches above do.
            _zoom_screen = current_screen
            if _zoom_screen == "pause":
                _zoom_screen = previous_screen
            elif _zoom_screen == "missions":
                _zoom_screen = missions_return_screen
            elif _zoom_screen == "shop":
                _zoom_screen = shop_return_screen
            _zoom, _zoom_kind = None, None
            if _zoom_screen == "game" and game_screen:
                _zoom, _zoom_kind = game_screen.camera_zoom, "space"
            elif _zoom_screen == "station" and station_interior:
                _zoom, _zoom_kind = station_interior.camera_zoom, "interior"
            elif _zoom_screen == "moon" and moon_interior:
                _zoom, _zoom_kind = moon_interior.camera_zoom, "interior"
            perf_metrics.draw_overlay(screen, zoom=_zoom, zoom_kind=_zoom_kind)
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
