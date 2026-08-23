"""Moon location factories for city and wilderness areas."""
from location import Location


# Type aliases for Location instantiation - loads from story config
def MoonCity(pilot_name=""):
    """Create a moon city location."""
    return Location(config_file="config/stories/default/moon_city.json", world_width=1600, world_height=1600, pilot_name=pilot_name)


def MoonOutdoor(pilot_name=""):
    """Create a moon wilderness location."""
    return Location(config_file="config/stories/default/moon_wilderness.json", world_width=1600, world_height=1600, pilot_name=pilot_name)
