"""Space exploration game - main entry point and game loop."""
import pygame
import sys
import os
from constants import (
    GAME_WIDTH, GAME_HEIGHT, SAVE_DIR, SCREEN_WIDTH, SCREEN_HEIGHT, FPS
)
from utils import (
    load_save_file, create_save_file, set_camera_offset, set_screen_size,
    DEBUG_MODE
)
from ship import PlayerController, AIShip
from objects import SpaceStation, Moon
from screens import (
    GameScreen, StationInterior, MoonCity, MoonOutdoor,
    Menu, PilotNameDialog, LocationSelector, PauseMenu,
    SaveDialog, DeleteConfirmDialog, OverwriteConfirmDialog, LoadMenu
)

# Initialize pygame and display
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
screen.fill((0, 0, 0))
pygame.display.flip()
pygame.display.set_caption("Space Game")
clock = pygame.time.Clock()


def main():
    """Main game loop."""
    global screen, DEBUG_MODE
    try:
        menu = Menu()
        game_screen = None
        station_interior = None
        moon_interior = None
        location_selector = None
        pilot_name_dialog = None
        pause_menu = PauseMenu()
        save_dialog = None
        delete_confirm_dialog = None
        overwrite_confirm_dialog = None
        load_menu = None
        current_screen = "menu"
        previous_screen = None
        running = True
        pilot_name = ""

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
                    if game_screen:
                        game_screen.star_field.generate_stars()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKQUOTE:
                    DEBUG_MODE = not DEBUG_MODE

            if current_screen == "menu":
                selection = menu.handle_input(events)
                if selection == "quit":
                    running = False
                elif selection == "new":
                    pilot_name_dialog = PilotNameDialog()
                    current_screen = "pilot_name"
                elif selection == "load":
                    load_menu = LoadMenu()
                    current_screen = "load"
                menu.draw(screen)

            elif current_screen == "pilot_name":
                result = pilot_name_dialog.handle_input(events)
                if result and result != "cancel":
                    pilot_name = result
                    game_screen = GameScreen(pilot_name=pilot_name)
                    current_screen = "game"
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
                                game_screen = GameScreen(save_data.get("system", {}), pilot_name=pilot_name)
                                game_screen.restore_state(game_state)
                                current_screen = "game"
                            elif location == "station":
                                game_screen = GameScreen(save_data.get("system", {}), pilot_name=pilot_name)
                                game_screen.restore_state(game_state)
                                station_interior = StationInterior(pilot_name=pilot_name)
                                station_interior.restore_state(game_state)
                                current_screen = "station"
                            elif location == "moon":
                                game_screen = GameScreen(save_data.get("system", {}), pilot_name=pilot_name)
                                game_screen.restore_state(game_state)
                                moon_location = game_state.get("moon_location", "city")
                                if moon_location == "city":
                                    moon_interior = MoonCity(pilot_name=pilot_name)
                                else:
                                    moon_interior = MoonOutdoor(pilot_name=pilot_name)
                                moon_interior.restore_state(game_state)
                                current_screen = "moon"
                    elif action == "delete":
                        delete_confirm_dialog = DeleteConfirmDialog(filename)
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
                    # Park the ship: zero velocity, keep current position
                    game_screen.player.velocity_x = 0
                    game_screen.player.velocity_y = 0
                    if game_screen.landing_target == "station":
                        station_interior = StationInterior(pilot_name=pilot_name)
                        current_screen = "station"
                    elif game_screen.landing_target == "moon":
                        location_selector = LocationSelector()
                        current_screen = "select_location"
                game_screen.update()
                game_screen.draw(screen)

            elif current_screen == "station":
                action = station_interior.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "pause":
                    previous_screen = "station"
                    current_screen = "pause"
                elif action == "exit":
                    current_screen = "game"
                # Keep space physics updated while docked (but not camera)
                if game_screen:
                    game_screen.update_physics()
                if station_interior:
                    station_interior.update()
                    station_interior.draw(screen)

            elif current_screen == "select_location":
                location = location_selector.handle_input(events)
                if location == "Moon City":
                    moon_interior = MoonCity(pilot_name=pilot_name)
                    current_screen = "moon"
                elif location == "Wilderness":
                    moon_interior = MoonOutdoor(pilot_name=pilot_name)
                    current_screen = "moon"
                elif location == "cancel":
                    current_screen = "game"
                location_selector.draw(screen)

            elif current_screen == "moon":
                action = moon_interior.handle_input(events)
                if action == "quit":
                    running = False
                elif action == "exit":
                    current_screen = "game"
                elif action == "pause":
                    previous_screen = "moon"
                    current_screen = "pause"
                # Keep space physics updated while on moon (but not camera)
                if game_screen:
                    game_screen.update_physics()
                if moon_interior:
                    moon_interior.update()
                    moon_interior.draw(screen)

            elif current_screen == "pause":
                pause_menu.update()

                if delete_confirm_dialog:
                    dialog_action, filename = delete_confirm_dialog.handle_input(events)
                    if dialog_action == "delete":
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
                        if previous_screen == "moon":
                            game_state = moon_interior.get_state()
                            game_state["location"] = "moon"
                            if isinstance(moon_interior, MoonCity):
                                game_state["moon_location"] = "city"
                            else:
                                game_state["moon_location"] = "wilderness"
                            create_save_file(pilot_name, save_description, {}, {}, game_state)
                        elif previous_screen == "station":
                            game_state = station_interior.get_state()
                            game_state["location"] = "station"
                            create_save_file(pilot_name, save_description, station_interior.station_config, {}, game_state)
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
                            overwrite_confirm_dialog = OverwriteConfirmDialog(save_name)
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
                            if previous_screen == "moon":
                                game_state = moon_interior.get_state()
                                game_state["location"] = "moon"
                                if isinstance(moon_interior, MoonCity):
                                    game_state["moon_location"] = "city"
                                else:
                                    game_state["moon_location"] = "wilderness"
                                create_save_file(pilot_name, save_description, {}, {}, game_state)
                            elif previous_screen == "station":
                                game_state = station_interior.get_state()
                                game_state["location"] = "station"
                                create_save_file(pilot_name, save_description, station_interior.station_config, {}, game_state)
                            else:  # previous_screen == "game" or None
                                game_state = game_screen.get_state()
                                game_state["location"] = "space"
                                create_save_file(pilot_name, save_description, game_screen.system_config, {}, game_state)
                            pause_menu.success_timer = 120
                            save_dialog = None
                    elif dialog_action == "cancel":
                        save_dialog = None
                    elif dialog_action == "delete":
                        delete_confirm_dialog = DeleteConfirmDialog(save_name)

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
