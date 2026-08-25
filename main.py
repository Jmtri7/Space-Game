"""Space exploration game - main entry point and game loop."""
import pygame
import sys
import os
import game.constants as constants
from game.constants import (
    GAME_WIDTH, GAME_HEIGHT, SAVE_DIR, SCREEN_WIDTH, SCREEN_HEIGHT, FPS
)
from game.utils import (
    load_save_file, create_save_file, set_camera_offset, set_screen_size
)
from game.world.player_controller import PlayerController
from game.screens.space_screen import SpaceScreen
from game.ui.menu import Menu
from game.ui.pilot_name_dialog import PilotNameDialog
from game.ui.location_selector import LocationSelector
from game.ui.exit_menu import ExitMenu
from game.ui.possessions_menu import PossessionsMenu
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


def update_background_locations(game_screen, active_location):
    """Keep every cached station/moon interior's NPCs simulating even while
    the player isn't there - active_location (whichever LocationScreen the
    player is actually standing in right now, or None if they're in space)
    is skipped here since it already gets a full update() from its own
    branch below, including player movement and the camera."""
    if not game_screen:
        return
    for landable in (game_screen.station, game_screen.moon):
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
                    station_interior = game_screen.get_interior_screen(game_screen.station, "dormitory", 800, 600)
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

                            if location == "space":
                                game_screen = SpaceScreen(save_data.get("system", {}), pilot_name=pilot_name, story=game_state.get("story", "default"), system_id=game_state.get("system_id"))
                                game_screen.restore_state(game_state)
                                current_screen = "game"
                            elif location == "station":
                                game_screen = SpaceScreen(save_data.get("system", {}), pilot_name=pilot_name, story=game_state.get("story", "default"), system_id=game_state.get("system_id"))
                                game_screen.restore_state(game_state)
                                station_location = game_state.get("station_location", "default")
                                if station_location not in game_screen.station.interiors:
                                    station_location = "default"
                                station_interior = game_screen.get_interior_screen(game_screen.station, station_location, 800, 600)
                                if station_interior:
                                    station_interior.restore_state(game_state)
                                current_screen = "station"
                            elif location == "moon":
                                game_screen = SpaceScreen(save_data.get("system", {}), pilot_name=pilot_name, story=game_state.get("story", "default"), system_id=game_state.get("system_id"))
                                game_screen.restore_state(game_state)
                                moon_location = game_state.get("moon_location", "city")
                                if moon_location not in game_screen.moon.interiors:
                                    moon_location = "city"
                                moon_interior = game_screen.get_interior_screen(game_screen.moon, moon_location, 1600, 1600)
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
                        station_interior = game_screen.get_interior_screen(game_screen.station, "default", 800, 600)
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
                # Keep space physics updated in the background (ships keep moving)
                if game_screen:
                    game_screen.update_physics()
                star_map.draw(screen)
                update_background_locations(game_screen, None)

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
                    station_interior = game_screen.get_interior_screen(game_screen.station, action.split(":", 1)[1], 800, 600)
                elif action == "possessions":
                    possessions_menu = PossessionsMenu(station_interior.player.possessions, story=game_screen.story)
                    possessions_return_screen = "station"
                    current_screen = "possessions"
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
                    moon_interior = game_screen.get_interior_screen(game_screen.moon, location_key, 1600, 1600)
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
                    world_width, world_height = (800, 600) if is_station else (1600, 1600)
                    interior = game_screen.get_interior_screen(exit_menu_landable, choice, world_width, world_height)
                    if is_station:
                        station_interior = interior
                    else:
                        moon_interior = interior
                    current_screen = exit_menu_return_screen
                # A modal menu, like PauseMenu - the rest of the world
                # (space physics, other cached interiors) stays frozen
                # while it's open.
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
                    moon_interior = game_screen.get_interior_screen(game_screen.moon, action.split(":", 1)[1], 1600, 1600)
                elif action == "possessions":
                    possessions_menu = PossessionsMenu(moon_interior.player.possessions, story=game_screen.story)
                    possessions_return_screen = "moon"
                    current_screen = "possessions"
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
                        game_state = {}
                        if game_screen:
                            game_state["story"] = game_screen.story
                            game_state["system_id"] = game_screen.system_id
                        if previous_screen == "moon":
                            game_state = moon_interior.get_state()
                            game_state["location"] = "moon"
                            # Determine moon location type from config file path or label
                            if moon_interior.config_file and "moon_city" in moon_interior.config_file:
                                game_state["moon_location"] = "city"
                            elif moon_interior.config.get("label", "").lower().find("city") >= 0:
                                game_state["moon_location"] = "city"
                            else:
                                game_state["moon_location"] = "wilderness"
                            create_save_file(pilot_name, save_description, {}, {}, game_state)
                        elif previous_screen == "station":
                            game_state = station_interior.get_state()
                            game_state["location"] = "station"
                            game_state["station_location"] = station_interior.interior_key or "default"
                            create_save_file(pilot_name, save_description, {}, {}, game_state)
                        else:  # previous_screen == "game" or None
                            game_state = game_screen.get_state()
                            game_state["location"] = "space"
                            create_save_file(pilot_name, save_description, game_screen.system_config, {}, game_state)
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
                            game_state = {}
                            if game_screen:
                                game_state["story"] = game_screen.story
                                game_state["system_id"] = game_screen.system_id
                            if previous_screen == "moon":
                                game_state = moon_interior.get_state()
                                game_state["location"] = "moon"
                                # Determine moon location type from config file path or label
                                if moon_interior.config_file and "moon_city" in moon_interior.config_file:
                                    game_state["moon_location"] = "city"
                                elif moon_interior.config.get("label", "").lower().find("city") >= 0:
                                    game_state["moon_location"] = "city"
                                else:
                                    game_state["moon_location"] = "wilderness"
                                create_save_file(pilot_name, save_description, {}, {}, game_state)
                            elif previous_screen == "station":
                                game_state = station_interior.get_state()
                                game_state["location"] = "station"
                                game_state["station_location"] = station_interior.interior_key or "default"
                                create_save_file(pilot_name, save_description, {}, {}, game_state)
                            else:  # previous_screen == "game" or None
                                game_state = game_screen.get_state()
                                game_state["location"] = "space"
                                create_save_file(pilot_name, save_description, game_screen.system_config, {}, game_state)
                            pause_menu.success_timer = 120
                            save_dialog = None
                    elif dialog_action == "cancel":
                        save_dialog = None
                    elif dialog_action == "delete":
                        delete_confirm_dialog = ConfirmDialog("Delete Save?", save_name[:50], context_data=save_name)

                if not save_dialog and not delete_confirm_dialog and not overwrite_confirm_dialog:
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
