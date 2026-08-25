"""A character - a body (Person), optionally flying a ship, whose role
picks the Routine that decides what they do with either. Composes a Ship
rather than inheriting one, exactly like PlayerController does for the
player - so every character in the game (player, AI ship pilots, and
station/moon NPCs) owns its ship and person the same way; NPCs just happen
to have no ship."""
import random
from game.world.ship import Ship
from game.world.person import Person
from game.world.dialogue import Dialogue
from game.world.possessions import Possessions
from game.world.dock_routine import DockRoutine
from game.world.shuttle_routine import ShuttleRoutine
from game.world.orbit_routine import OrbitRoutine
from game.world.idle_routine import IdleRoutine
from game.world.wander_routine import WanderRoutine
from game.world.stationary_routine import StationaryRoutine

# Starting credits for an AI pilot's Possessions - flavor/future-proofing
# (nothing spends this yet), not tuned gameplay balance.
AI_PILOT_STARTING_CREDITS = 500

# Default routine per role - which Routine strategy a character runs each
# frame, whether that means flying a ship (DockRoutine/ShuttleRoutine/
# OrbitRoutine) or just existing in a room (WanderRoutine/StationaryRoutine).
# Roles with no entry here just get IdleRoutine (never moves on its own).
ROLE_ROUTINES = {
    "freighter_pilot": DockRoutine,
    "trader_captain": ShuttleRoutine,
    "patrol_officer": OrbitRoutine,
    "bartender": StationaryRoutine,
    "guard": StationaryRoutine,
    "ship_salesman": StationaryRoutine,
    "loan_officer": StationaryRoutine,
    "traveler": WanderRoutine,
    "roommate": WanderRoutine,
    "resident": WanderRoutine,  # default/catch-all local role
}

# Faction-specific overrides, checked before the role default above - lets a
# faction fly a role differently (e.g. a militarized trade faction patrolling
# instead of shuttling). Empty for now; both ship roles currently in use only
# belong to one faction each.
FACTION_ROUTINE_OVERRIDES = {}


class Character:
    """Someone with a role that determines their routine - a body (Person),
    optionally a ship they fly, and a Routine chosen by role that decides
    what they do with either. The player is not one of these (see
    PlayerController); this is for every AI-driven character - ship pilots
    and non-piloting station/moon residents alike."""
    def __init__(self, person, ship=None, role=None, faction=None, route=None, get_interior_screen=None, ship_type_id=None):
        self.person = person
        self.ship = ship
        self.role = role
        self.route = route or []
        # Lets a routine (DockRoutine) find/create a stop's interior
        # LocationScreen without this module importing anything from
        # game.screens, which this codebase keeps strictly one-directional
        # (screens depend on world, not the reverse). Only ever set (and
        # only ever used) for ship-flying characters - a local NPC never
        # needs to "find" the location it's already standing in.
        self.get_interior_screen = get_interior_screen
        self.ship_type_id = ship_type_id
        # Only meaningful when self.ship is set: False = aboard and
        # mirrored to the ship's position each frame; True = a routine
        # (DockRoutine) has them walking around a station/moon interior
        # instead, independent of the (parked) ship.
        self.ashore = False

        routine_cls = FACTION_ROUTINE_OVERRIDES.get((faction, role), ROLE_ROUTINES.get(role, IdleRoutine))
        self.routine = routine_cls(self.route)
        self.routine.start(self)

    @classmethod
    def for_ai_pilot(cls, x, y, ship_type, ship_type_id, graphics, pilot, route, get_interior_screen, space_drag=0):
        """Build the Character for an AI-flown ship: a Ship configured from
        ship_type, a Person seeded with the pilot's starting credits/ship
        and flavor dialogue, and the role-driven routine that flies it."""
        ship = Ship(x, y, space_drag=space_drag, graphics=graphics)
        ship.angle = random.randint(0, 360)
        if ship_type:
            ship.acceleration_magnitude = ship_type.get("max_thrust", 0.15)
            ship.max_velocity = ship_type.get("max_velocity", 4.0)
            ship.rotation_speed = ship_type.get("rotation_speed", 5)

        pilot = pilot or {}
        # Linked to an economy like any other character (see Person) - they
        # already "own" the ship they're flying, and start with some
        # walking-around money, even though nothing spends it yet.
        person = Person(x, y, name=pilot.get("name", ""), possessions=Possessions(credits=AI_PILOT_STARTING_CREDITS, owned_ships=[ship_type_id]))
        # Lets the player target/talk to this pilot while they're walking
        # around a station/moon interior (see LocationScreen.visitors) the
        # same way they would an NPC - flavored from the pilot's own
        # personality line in pilots.json rather than a generic greeting.
        person.dialogue = Dialogue.from_flat(pilot.get("name", "Pilot"), pilot.get("personality", "..."), ["Nod", "Leave"])

        return cls(person, ship=ship, role=pilot.get("role"), faction=pilot.get("faction"), route=route, get_interior_screen=get_interior_screen, ship_type_id=ship_type_id)

    def update(self):
        """Let the role's routine advance, then run standard ship autopilot/
        physics, then keep the person aboard - unless they're ashore
        (DockRoutine), in which case it's walking them instead. Shipless
        characters (NPCs) just run their routine, which moves person.x/y
        directly (see WanderRoutine)."""
        self.routine.run(self)
        if self.ship:
            self.ship.update()
            if not self.ashore:
                self.person.x = self.ship.x
                self.person.y = self.ship.y

    def draw(self, surface):
        """Draw the ship - only meaningful for a character that has one;
        the person walking around a location is drawn separately by
        LocationScreen via character.person.draw()."""
        self.ship.draw(surface)

    # --- Ship-duck-type passthrough, mirroring PlayerController's own
    # property list - only ever called when self.ship is set (a shipless
    # character, e.g. any NPC, is never asked to behave like a ship). ---
    @property
    def x(self):
        return self.ship.x

    @x.setter
    def x(self, value):
        self.ship.x = value

    @property
    def y(self):
        return self.ship.y

    @y.setter
    def y(self, value):
        self.ship.y = value

    @property
    def velocity_x(self):
        return self.ship.velocity_x

    @velocity_x.setter
    def velocity_x(self, value):
        self.ship.velocity_x = value

    @property
    def velocity_y(self):
        return self.ship.velocity_y

    @velocity_y.setter
    def velocity_y(self, value):
        self.ship.velocity_y = value

    @property
    def angle(self):
        return self.ship.angle

    @angle.setter
    def angle(self, value):
        self.ship.angle = value

    @property
    def thrust(self):
        return self.ship.thrust

    @thrust.setter
    def thrust(self, value):
        self.ship.thrust = value

    @property
    def autopilot_active(self):
        return self.ship.autopilot_active

    @autopilot_active.setter
    def autopilot_active(self, value):
        self.ship.autopilot_active = value

    @property
    def autopilot_target(self):
        return self.ship.autopilot_target

    @autopilot_target.setter
    def autopilot_target(self, value):
        self.ship.autopilot_target = value

    def engage_seek(self, target):
        self.ship.engage_seek(target)

    def engage_orbit(self, center_x, center_y, radius):
        self.ship.engage_orbit(center_x, center_y, radius)

    def get_distance(self, target_x, target_y):
        return self.ship.get_distance(target_x, target_y)

    def park(self):
        self.ship.park()
