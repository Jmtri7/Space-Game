"""Space exploration game - main entry point and game loop."""
import pygame
import sys
import os
import game.constants as constants
from game.constants import (
    GAME_WIDTH, GAME_HEIGHT, SAVE_DIR, SCREEN_WIDTH, SCREEN_HEIGHT, FPS
)
from game.utils import (
    load_save_file, create_save_file, set_camera_offset, set_screen_size, load_json
)
from game.world.player_controller import PlayerController
from game.screens.space_screen import SpaceScreen
from game.ui.menu import Menu
from game.ui.pilot_name_dialog import PilotNameDialog
from game.ui.location_selector import LocationSelector
from game.ui.exit_menu import ExitMenu
from game.ui.possessions_menu import PossessionsMenu
from game.ui.shop_menu import ShopMenu
from game.ui.ship_browser_menu import ShipBrowserMenu
from game.ui.outfitting_menu import OutfittingMenu
from game.ui.pause_menu import PauseMenu
from game.ui.save_dialog import SaveDialog
from game.ui.confirm_dialog import ConfirmDialog
from game.ui.load_menu import LoadMenu
from game.ui.story_selector import StorySelector
from game.ui.star_map import StarMap

# Initialize pygame and display
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
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


def warn_if_story_version_mismatch(story, saved_version):
    """Print a warning if a save's story_version doesn't match the current
    story.json's version - the story's config or this game's state-
    handling code may have changed since the save was made, in a way that
    changes what the saved state means (see CLAUDE.md's "Save Compatibility
    & Story Versioning" section). Never blocks loading - just surfaces the
    risk so a stale save behaving oddly isn't a total mystery."""
    current_version = (load_json(f"config/stories/{story}/story.json") or {}).get("version", "0.0.0")
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
        for landable in (system_state.station, system_state.moon):
            for interior in landable.interior_screens.values():
                if interior is not active_location:
                    interior.update_physics()


def main():
    """Main game loop."""
    global screen
    try:
        menu = Menu()
        story_selector = None
        game_screen = None
        station_interior = None
        moon_interior = None
        location_selector = None
        exit_menu = None
        exit_menu_landable = None  # game_screen.station or game_screen.moon - whichever this exit_menu is for
        exit_menu_return_screen = None  # "station" or "moon" - where ESC/cancel goes back to
        possessions_menu = None
        possessions_return_screen = None  # "game" / "station" / "moon" - where P/ESC closes back to
        shop_menu = None
        shop_return_screen = None  # "station" / "moon" - where ESC closes back to
        pilot_name_dialog = None
        pause_menu = PauseMenu()
        save_dialog = None
        delete_confirm_dialog = None
        overwrite_confirm_dialog = None
        load_menu = None
        star_map = None
        current_screen = "menu"
        previous_screen = None
        running = True
        pilot_name = ""
        selected_story = "default"

        while running:
            events = pygame.event.get()

            # Handle window close button globally (all screens automatically support it)
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break

            if not running:
                break

            for event in events:
                if event.type == pygame.VIDEORESIZE:
                    new_width, new_height = event.size
                    set_screen_size(new_width, new_height)
                    screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKQUOTE:
                    constants.DEBUG_MODE = not constants.DEBUG_MODE

            if current_screen == "menu":
                selection = menu.handle_input(events)
                if selection == "quit":
                    running = False
                elif selection == "new":
                    story_selector = StorySelector()
                    current_screen = "story_select"
                elif selection == "load":
                    load_menu = LoadMenu()
                    current_screen = "load"
                menu.draw(screen)

            elif current_screen == "story_select":
                story = story_selector.handle_input(events)
                if story and story != "cancel":
                    selected_story = story
                    pilot_name_dialog = PilotNameDialog()
                    current_screen = "pilot_name"
                elif story == "cancel":
                    current_screen = "menu"
                story_selector.draw(screen)

            elif current_screen == "pilot_name":
                result = pilot_name_dialog.handle_input(events)
                if result and result != "cancel":
                    pilot_name = result
                    game_screen = SpaceScreen(pilot_name=pilot_name, story=selected_story)
                    # New pilots start ship-less, in their dormitory room -
                    # not out in space with a ship already assigned.
                    station_interior = game_screen.get_interior_screen(game_screen.station, "dormitory")
                    current_screen = "station"
                elif result == "cancel":
                    current_screen = "menu"
                pilot_name_dialog.draw(screen)

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
                        load_menu = LoadMenu()
                    elif confirm_action == "cancel":
                        delete_confirm_dialog = None
                    elif confirm_action == "quit":
                        running = False
                    load_menu.draw(screen)
                    if delete_confirm_dialog:
                        delete_confirm_dialog.draw(screen)
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
                                # Always resume in whichever room the ship
                                # actually docks at, not wherever the save
                                # happened to record (e.g. a dormitory) -
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
                    elif action == "delete":
                        delete_confirm_dialog = ConfirmDialog("Delete Save?", filename[:50], context_data=filename)
                    elif action == "cancel":
                        current_screen = "menu"
                        menu = Menu()
                    load_menu.draw(screen)

            elif current_screen == "game":
                action = game_screen.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "pause":
                    previous_screen = "game"
                    current_screen = "pause"
                elif action == "land":
                    game_screen.player.park()
                    if game_screen.landing_target == "station":
                        ship_entry_key = game_screen.station.get_ship_entry_key()
                        station_interior = game_screen.get_interior_screen(game_screen.station, ship_entry_key)
                        if station_interior:
                            station_interior.arrive_from("ship")
                        current_screen = "station"
                    elif game_screen.landing_target == "moon":
                        location_selector = LocationSelector(game_screen.moon.interiors)
                        current_screen = "select_location"
                elif action == "star_map":
                    star_map = StarMap(game_screen.story, game_screen.system_id, game_screen.selected_system_id)
                    current_screen = "star_map"
                elif action == "possessions":
                    possessions_menu = PossessionsMenu(game_screen.player.person.possessions, story=game_screen.story)
                    possessions_return_screen = "game"
                    current_screen = "possessions"
                game_screen.update()
                game_screen.draw(screen)
                update_background_locations(game_screen, None)

            elif current_screen == "star_map":
                action = star_map.handle_input(events)
                if action == "close":
                    game_screen.selected_system_id = star_map.selected_system_id
                    current_screen = "game"
                # Unlike docking at the station/moon, opening the jump map
                # fully pauses the simulation (matches PauseMenu) - no
                # update_physics()/update_background_locations() here.
                star_map.draw(screen)

            elif current_screen == "station":
                action = station_interior.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "pause":
                    previous_screen = "station"
                    current_screen = "pause"
                elif action == "exit":
                    current_screen = "game"
                elif action == "exit_menu":
                    exit_menu = ExitMenu(station_interior.get_exit_options(), game_screen.station.interiors, disabled_reasons=station_interior.get_exit_disabled_reasons())
                    exit_menu_landable = game_screen.station
                    exit_menu_return_screen = "station"
                    current_screen = "exit_menu"
                elif action and action.startswith("exit_to:"):
                    origin_key = station_interior.interior_key
                    station_interior = game_screen.get_interior_screen(game_screen.station, action.split(":", 1)[1])
                    station_interior.arrive_from(origin_key)
                elif action == "possessions":
                    possessions_menu = PossessionsMenu(station_interior.player.possessions, story=game_screen.story)
                    possessions_return_screen = "station"
                    current_screen = "possessions"
                elif action == "shop":
                    shop_menu = build_shop_menu(station_interior.player.possessions, game_screen.story, station_interior.active_shop, game_screen.player.ship.cargo_capacity, station_interior.buy_ship, game_screen.reapply_outfits)
                    shop_return_screen = "station"
                    current_screen = "shop"
                # Keep space physics updated while docked (but not camera) -
                # except while a conversation is open, which should pause
                # the rest of the world like any other modal menu (matches
                # ExitMenu/PossessionsMenu/PauseMenu).
                talking = bool(station_interior and station_interior.active_dialogue)
                if game_screen and not talking:
                    game_screen.update_physics()
                if station_interior:
                    station_interior.update()
                    station_interior.draw(screen)
                if not talking:
                    update_background_locations(game_screen, station_interior)

            elif current_screen == "select_location":
                location_key = location_selector.handle_input(events)
                if location_key and location_key in location_selector.interior_configs:
                    moon_interior = game_screen.get_interior_screen(game_screen.moon, location_key)
                    moon_interior.arrive_from("ship")
                    current_screen = "moon"
                elif location_key == "cancel":
                    current_screen = "game"
                location_selector.draw(screen)

            elif current_screen == "exit_menu":
                choice = exit_menu.handle_input(events)
                if choice == "ship":
                    current_screen = "game"
                elif choice == "cancel":
                    current_screen = exit_menu_return_screen
                elif choice:
                    is_station = exit_menu_landable is game_screen.station
                    origin_key = (station_interior if is_station else moon_interior).interior_key
                    interior = game_screen.get_interior_screen(exit_menu_landable, choice)
                    interior.arrive_from(origin_key)
                    if is_station:
                        station_interior = interior
                    else:
                        moon_interior = interior
                    current_screen = exit_menu_return_screen
                # A modal menu, like PauseMenu - the rest of the world
                # (space physics, other cached interiors) stays frozen
                # while it's open. Redraw whichever interior it was opened
                # over first - ExitMenu only paints a centered panel, not a
                # full-screen fill, so skipping this left the *previous*
                # frame's interior (e.g. the spaceport, Dax Renner and all)
                # visible behind the menu instead of the one actually being
                # left, which looked exactly like an NPC in two rooms at once.
                if exit_menu_return_screen == "station" and station_interior:
                    station_interior.draw(screen)
                elif exit_menu_return_screen == "moon" and moon_interior:
                    moon_interior.draw(screen)
                exit_menu.draw(screen)

            elif current_screen == "possessions":
                action = possessions_menu.handle_input(events)
                if action == "close":
                    current_screen = possessions_return_screen
                # A modal menu, like PauseMenu - the world stays frozen
                # while it's open. Draw whichever screen this was opened
                # over, then the overlay on top - same idea as PauseMenu below.
                if possessions_return_screen == "game" and game_screen:
                    game_screen.draw(screen)
                elif possessions_return_screen == "station" and station_interior:
                    station_interior.draw(screen)
                elif possessions_return_screen == "moon" and moon_interior:
                    moon_interior.draw(screen)
                possessions_menu.draw(screen)

            elif current_screen == "shop":
                action = shop_menu.handle_input(events)
                if action == "close":
                    current_screen = shop_return_screen
                # A modal menu, like PossessionsMenu/ExitMenu - the world
                # stays frozen while it's open. Draw whichever screen this
                # was opened over, then the overlay on top.
                if shop_return_screen == "station" and station_interior:
                    station_interior.draw(screen)
                elif shop_return_screen == "moon" and moon_interior:
                    moon_interior.draw(screen)
                shop_menu.draw(screen)

            elif current_screen == "moon":
                action = moon_interior.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "exit":
                    current_screen = "game"
                elif action == "pause":
                    previous_screen = "moon"
                    current_screen = "pause"
                elif action == "exit_menu":
                    exit_menu = ExitMenu(moon_interior.get_exit_options(), game_screen.moon.interiors, disabled_reasons=moon_interior.get_exit_disabled_reasons())
                    exit_menu_landable = game_screen.moon
                    exit_menu_return_screen = "moon"
                    current_screen = "exit_menu"
                elif action and action.startswith("exit_to:"):
                    origin_key = moon_interior.interior_key
                    moon_interior = game_screen.get_interior_screen(game_screen.moon, action.split(":", 1)[1])
                    moon_interior.arrive_from(origin_key)
                elif action == "possessions":
                    possessions_menu = PossessionsMenu(moon_interior.player.possessions, story=game_screen.story)
                    possessions_return_screen = "moon"
                    current_screen = "possessions"
                elif action == "shop":
                    shop_menu = build_shop_menu(moon_interior.player.possessions, game_screen.story, moon_interior.active_shop, game_screen.player.ship.cargo_capacity, moon_interior.buy_ship, game_screen.reapply_outfits)
                    shop_return_screen = "moon"
                    current_screen = "shop"
                # Keep space physics updated while on moon (but not camera) -
                # except while a conversation is open, which should pause
                # the rest of the world like any other modal menu.
                talking = bool(moon_interior and moon_interior.active_dialogue)
                if game_screen and not talking:
                    game_screen.update_physics()
                if moon_interior:
                    moon_interior.update()
                    moon_interior.draw(screen)
                if not talking:
                    update_background_locations(game_screen, moon_interior)

            elif current_screen == "pause":
                pause_menu.update()
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
                            overwrite_confirm_dialog = ConfirmDialog("Overwrite Save?", save_name[:50], context_data=save_name)
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
                        delete_confirm_dialog = ConfirmDialog("Delete Save?", save_name[:50], context_data=save_name)

                if not dialog_was_open:
                    action = pause_menu.handle_input(events)
                    if action == "resume":
                        current_screen = previous_screen
                    elif action == "save":
                        save_dialog = SaveDialog(pilot_name=pilot_name)
                    elif action == "quit":
                        current_screen = "menu"
                        menu = Menu()

                if previous_screen == "game" and game_screen:
                    game_screen.draw(screen)
                elif previous_screen == "station" and station_interior:
                    station_interior.draw(screen)

                pause_menu.draw(screen)

                if delete_confirm_dialog:
                    delete_confirm_dialog.draw(screen)
                elif overwrite_confirm_dialog:
                    overwrite_confirm_dialog.draw(screen)
                elif save_dialog:
                    save_dialog.draw(screen)

            pygame.display.flip()
            clock.tick(FPS)

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
