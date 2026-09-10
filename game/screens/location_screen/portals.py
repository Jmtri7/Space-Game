"""LocationScreen: portals — mixed into the class in screen.py."""
from game.screens.location_screen._defs import *  # noqa: F401,F403


class _PortalsMixin:

    def _resolve_portal(self, portal):
        """Which portal get_exit_options() and friends should act on when
        the caller didn't pass one explicitly: whichever portal G was just
        pressed next to (_active_portal, set by handle_input - main.py
        calls these after the fact, once ExitMenu is already up), falling
        back to whatever the player is currently standing next to (for
        direct calls, e.g. from tests), and finally this location's first
        portal (so these never crash even called with no portal in range -
        e.g. a fresh LocationScreen in a test, which starts standing
        exactly on its own first portal anyway)."""
        return portal or self._active_portal or self._nearby_portal() or self.portals[0]

    def get_exit_options(self, portal=None):
        """Ordered destinations available through one portal (see
        self.portals - defaults to _resolve_portal()): each of its
        connected_locations keys (in config order), then "ship" last if
        that portal's return_to_ship allows it. Used both to drive the
        player's exit menu and by AI routines (see DockRoutine) choosing
        where to go next - same list, same meaning, for both."""
        portal = self._resolve_portal(portal)
        options = list(portal["connected_locations"])
        if portal["return_to_ship"]:
            options.append("ship")
        return options

    def all_exit_options(self):
        """Every destination reachable from this location via *any* of its
        portals (see self.portals), deduplicated but order-preserving.
        Unlike get_exit_options(), which is scoped to one specific portal
        (the player is always standing at a particular one when G opens
        the exit menu), this is for DockRoutine: an AI pilot decides where
        to go next while still talking to an NPC, nowhere near a portal
        yet, so it needs to know what's reachable at all before walking to
        whichever portal actually leads there (see portal_for)."""
        options = []
        for portal in self.portals:
            for option in self.get_exit_options(portal):
                if option not in options:
                    options.append(option)
        return options

    @property
    def ship_available(self):
        """Whether the player actually has a ship to board right now - not
        just whether this location's exit is configured to offer one.
        False until a "buy_ship:" dialogue action has run (see
        _apply_dialogue_action)."""
        return bool(self.player.possessions.owned_ships)

    def get_available_exit_options(self, portal=None):
        """get_exit_options() minus "ship" when there's no ship to actually
        board yet - used to decide whether G can exit immediately or needs
        to open ExitMenu so the player can see *why* nothing happened."""
        options = self.get_exit_options(portal)
        if not self.ship_available:
            options = [option for option in options if option != "ship"]
        return options

    def get_exit_disabled_reasons(self, portal=None):
        """{key: reason} for exit options this location's config offers but
        aren't usable right now - currently just "ship" with no ship owned
        yet. Passed to ExitMenu so it's shown, dim, instead of silently
        missing."""
        if "ship" in self.get_exit_options(portal) and not self.ship_available:
            return {"ship": "no ship docked here"}
        return {}

    def portal_for(self, key):
        """The portal (see self.portals) associated with `key` - either a
        connected location's interior key, or "ship" for a portal that
        leads back to the ship. Used both to find where to arrive when
        entering from `key` (see arrive_from, and DockRoutine's own use for
        AI pilots) and where to walk to when heading toward `key` - the
        same physical portal serves both directions of one connection.
        Falls back to this location's first/primary portal when no portal
        singles out `key` (a fresh arrival with no "from" context passes
        key=None, which never matches any portal on purpose)."""
        for portal in self.portals:
            if key == "ship" and portal["return_to_ship"]:
                return portal
            if key in portal["connected_locations"]:
                return portal
        return self.portals[0]

    def arrive_from(self, origin_key):
        """Place the player at whichever portal leads back to origin_key
        (an interior key, or "ship") - called whenever the player enters
        this (persistent, cached) location via a portal transition, so they
        appear next to the door they actually walked through instead of
        wherever they happened to be left the last time they visited this
        location."""
        # Re-evaluate flag/reputation-conditional content against the
        # player's current state - this cached LocationScreen may have been
        # built (or last entered) before a beacon was lit or a faction
        # turned. See _apply_content_gates / game/world/content_gate.py.
        self._apply_content_gates()
        portal = self.portal_for(origin_key)
        self.player.x, self.player.y = portal["x"], portal["y"]

    def _display_name(self, key):
        """Human-readable label for a connected_locations key or "ship" -
        used to label portals in-world (see _portal_label) now that a
        single-destination portal no longer opens a menu that would
        otherwise be the only place its destination's name showed up.
        Prefers the sibling interior's own configured "label" (see
        self.location_labels, built by SpaceScreen.get_interior_screen),
        falling back to a prettified version of the key itself (e.g.
        "loan_office" -> "Loan Office") when there's no sibling label to
        borrow - e.g. "ship", or a LocationScreen built standalone."""
        if key == "ship":
            return "Ship"
        return self.location_labels.get(key) or key.replace("_", " ").title()

    def _portal_label(self, portal):
        """Display text for one portal: the destination(s) it leads to,
        joined with "/" for a portal that offers more than one (a menu
        still opens for those - the label is just a preview of what's in
        it, same as a single-destination portal's label is now the only
        preview it gets since G skips straight past its menu)."""
        names = [self._display_name(key) for key in portal["connected_locations"]]
        if portal["return_to_ship"]:
            names.append(self._display_name("ship"))
        return " / ".join(names)

    def _nearby_portal(self):
        """Whichever portal (see self.portals) the player is currently
        close enough to use, or None - the nearest one, if somehow more
        than one is in range at once (portals are laid out with enough
        space between them that this shouldn't normally happen)."""
        in_range = [p for p in self.portals if math.sqrt((self.player.x - p["x"]) ** 2 + (self.player.y - p["y"]) ** 2) <= self.entrance_range]
        if not in_range:
            return None
        return min(in_range, key=lambda p: (self.player.x - p["x"]) ** 2 + (self.player.y - p["y"]) ** 2)

    def _option_blocked_reason(self, option):
        """Why any of a dialogue option's action(s) (see option_actions)
        can't be taken right now, or None if all are fine. Options with no
        action are never blocked."""
        for action in option_actions(option):
            reason = shared_action_blocked_reason(action, self.player.possessions)
            if reason:
                return reason
            if action.startswith("buy_ship:"):
                ship_type_id = action.split(":", 1)[1]
                cost = get_ship_type(self.story, ship_type_id).get("cost", 0)
                if not self.player.possessions.can_afford(cost):
                    return "not enough credits"
            elif action == "take_loan" or action.startswith("take_loan:"):
                _, _, max_active = self._loan_terms(action)
                if len(self.player.possessions.loans) >= max_active:
                    return "already have a loan" if max_active == 1 else "loan limit reached"
        return None
