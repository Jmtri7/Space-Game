"""What a character owns - credits, ships, and loans. Composed onto every
Person (player, NPCs, AI pilots) rather than bolted onto the player alone,
so any character can be linked to an economy even if most never use it."""


class Possessions:
    """Credits and owned ships a character has."""
    def __init__(self, credits=0, owned_ships=None, loans=None):
        self.credits = credits
        self.owned_ships = owned_ships or []  # list of ship_type_id strings
        self.loans = loans or []  # list of {"lender": str, "principal": int}

    def can_afford(self, amount):
        return self.credits >= amount

    def spend(self, amount):
        self.credits -= amount

    def add_ship(self, ship_type_id):
        self.owned_ships.append(ship_type_id)

    def take_loan(self, lender, amount):
        self.loans.append({"lender": lender, "principal": amount})
        self.credits += amount

    def restore_from(self, state):
        """Overwrite this object's fields in place from a save's state dict
        - never replaces the object itself, so every character/screen
        holding a reference to it (see SpaceScreen.get_interior_screen)
        keeps pointing at the same, now-updated, Possessions."""
        if not state:
            return
        self.credits = state.get("credits", self.credits)
        self.owned_ships = list(state.get("owned_ships", self.owned_ships))
        self.loans = [dict(loan) for loan in state.get("loans", self.loans)]

    def get_state(self):
        return {
            "credits": self.credits,
            "owned_ships": list(self.owned_ships),
            "loans": [dict(loan) for loan in self.loans],
        }

    @classmethod
    def from_state(cls, state):
        if not state:
            return cls()
        return cls(
            credits=state.get("credits", 0),
            owned_ships=list(state.get("owned_ships", [])),
            loans=[dict(loan) for loan in state.get("loans", [])],
        )
