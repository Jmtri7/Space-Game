"""What a character owns - credits, ships, and loans. Composed onto every
Person (player, NPCs, AI pilots) rather than bolted onto the player alone,
so any character can be linked to an economy even if most never use it."""


class Possessions:
    """Credits, owned ships, cargo, personal items, and ship outfits a
    character has.

    Ship outfits are a distinct concept from Person.outfit (the cosmetic
    space-suit asset in graphics.json) - these are ship equipment (weapons,
    engines, shields, utility modules). owned_outfits is the spare-parts
    list (bought but not installed); installed_outfits is a
    {slot_id: outfit_id} map describing the loadout of whichever ship is
    currently flown. There's no per-ship-instance loadout tracking - see
    docs/SAVE_SYSTEM.md for why that's deliberately out of scope for now.

    Cargo capacity (mass) only ever applies to `cargo` - `items` (personal
    inventory) and `owned_outfits` (spare ship parts) aren't capacity-limited.
    Capacity itself lives on the ship (Ship.cargo_capacity), not here, so
    this class stays config-free per the story/save split.

    `flags` is a flat {name: True} set of story-progress markers - which
    conversation branches have been unlocked, which one-way hails have
    already fired, which minor world-state consequences have happened. See
    Dialogue's "requires_flag"/"requires_not_flag"/"conditional_roots" and
    the "set_flag:<name>" dialogue action (game/world/dialogue.py) for how
    conversations read and write these. Lives here (rather than a separate
    shared object) because Possessions is already the one piece of player
    state shared by reference across SpaceScreen and every LocationScreen,
    and already flows through save/load - a flag set while talking to a
    station NPC needs to be visible when hailing a ship in space later, and
    vice versa."""
    def __init__(self, credits=0, owned_ships=None, loans=None,
                 owned_outfits=None, installed_outfits=None, cargo=None, items=None, flags=None):
        self.credits = credits
        self.owned_ships = owned_ships or []  # list of ship_type_id strings
        self.loans = loans or []  # list of {"lender": str, "principal": int}
        self.owned_outfits = owned_outfits or []  # list of outfit_id strings, uninstalled
        self.installed_outfits = installed_outfits or {}  # {slot_id: outfit_id}
        self.cargo = cargo or {}  # {commodity_id: quantity}
        self.items = items or {}  # {item_id: quantity}
        self.flags = flags or {}  # {flag_name: True}

    def can_afford(self, amount):
        return self.credits >= amount

    def spend(self, amount):
        self.credits -= amount

    def earn(self, amount):
        self.credits += amount

    def add_ship(self, ship_type_id):
        self.owned_ships.append(ship_type_id)

    def take_loan(self, lender, amount):
        self.loans.append({"lender": lender, "principal": amount})
        self.credits += amount

    def cargo_quantity_total(self):
        return sum(self.cargo.values())

    def add_cargo(self, commodity_id, qty):
        self.cargo[commodity_id] = self.cargo.get(commodity_id, 0) + qty

    def remove_cargo(self, commodity_id, qty):
        remaining = self.cargo.get(commodity_id, 0) - qty
        if remaining > 0:
            self.cargo[commodity_id] = remaining
        else:
            self.cargo.pop(commodity_id, None)

    def add_item(self, item_id, qty):
        self.items[item_id] = self.items.get(item_id, 0) + qty

    def remove_item(self, item_id, qty):
        remaining = self.items.get(item_id, 0) - qty
        if remaining > 0:
            self.items[item_id] = remaining
        else:
            self.items.pop(item_id, None)

    def add_outfit(self, outfit_id):
        self.owned_outfits.append(outfit_id)

    def install_outfit(self, slot_id, outfit_id):
        """Move outfit_id from owned_outfits into slot_id. If the slot was
        already occupied, the bumped outfit goes back to owned_outfits and
        its id is returned (None if the slot was empty)."""
        self.owned_outfits.remove(outfit_id)
        bumped = self.installed_outfits.get(slot_id)
        self.installed_outfits[slot_id] = outfit_id
        if bumped is not None:
            self.owned_outfits.append(bumped)
        return bumped

    def uninstall_outfit(self, slot_id):
        """Move whatever's installed in slot_id back to owned_outfits.
        Returns the outfit id, or None if the slot was empty."""
        outfit_id = self.installed_outfits.pop(slot_id, None)
        if outfit_id is not None:
            self.owned_outfits.append(outfit_id)
        return outfit_id

    def uninstall_all_outfits(self):
        """Move every currently-installed outfit back to owned_outfits and
        clear installed_outfits - call this whenever the active ship
        changes (buying a new one). installed_outfits describes "whichever
        ship is currently flown", not a specific hull (see
        docs/SAVE_SYSTEM.md) - slot ids like "utility_1" are reused across
        ship types, so without this a newly bought ship would inherit
        whatever was mounted on the old one for free, rather than starting
        bare with those outfits back in your spares to reinstall."""
        self.owned_outfits.extend(self.installed_outfits.values())
        self.installed_outfits = {}

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
        self.owned_outfits = list(state.get("owned_outfits", self.owned_outfits))
        self.installed_outfits = dict(state.get("installed_outfits", self.installed_outfits))
        self.cargo = dict(state.get("cargo", self.cargo))
        self.items = dict(state.get("items", self.items))
        self.flags = dict(state.get("flags", self.flags))

    def get_state(self):
        return {
            "credits": self.credits,
            "owned_ships": list(self.owned_ships),
            "loans": [dict(loan) for loan in self.loans],
            "owned_outfits": list(self.owned_outfits),
            "installed_outfits": dict(self.installed_outfits),
            "cargo": dict(self.cargo),
            "items": dict(self.items),
            "flags": dict(self.flags),
        }

    @classmethod
    def from_state(cls, state):
        if not state:
            return cls()
        return cls(
            credits=state.get("credits", 0),
            owned_ships=list(state.get("owned_ships", [])),
            loans=[dict(loan) for loan in state.get("loans", [])],
            owned_outfits=list(state.get("owned_outfits", [])),
            installed_outfits=dict(state.get("installed_outfits", {})),
            cargo=dict(state.get("cargo", {})),
            items=dict(state.get("items", {})),
            flags=dict(state.get("flags", {})),
        )
