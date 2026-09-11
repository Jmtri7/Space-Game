"""LocationScreen: commerce — mixed into the class in screen.py."""
from game.screens.location_screen._defs import *  # noqa: F401,F403


class _CommerceMixin:

    def _loan_terms(self, action):
        """(lender, amount, max_active) for a "take_loan" or
        "take_loan:<amount>" dialogue action. Lender, default amount, and
        how many loans a player may hold at once all come from story.json's
        "loan" block; an explicit "take_loan:<amount>" overrides just the
        amount (e.g. a smaller loan offered by a different NPC)."""
        loan_cfg = get_story(self.story).get("loan", {})
        lender = loan_cfg.get("lender", "Credit Union")
        amount = loan_cfg.get("amount", DEFAULT_LOAN_AMOUNT)
        max_active = loan_cfg.get("max_active", 1)
        if ":" in action:
            amount = int(action.split(":", 1)[1])
        return lender, amount, max_active

    def _apply_dialogue_action(self, action):
        """Perform the game-state effect of one dialogue option action tag -
        called once the option's full action list is confirmed not blocked
        (see _option_blocked_reason), right before Dialogue.choose()
        advances to the option's response node."""
        if action.startswith("start_mission:"):
            # apply_shared_actions' own "start_mission:" never delivers the
            # new stage's one_way_message (an NPC's own dialogue usually
            # covers it - see its docstring). Handled here instead so an
            # NPC-started mission's stage 0 still reaches the Message Log,
            # e.g. the Grey Courier's handover posting the note's first
            # segment the moment the conversation closes.
            started = start_mission(self.missions_config, self.player.possessions, action.split(":", 1)[1])
            self._deliver_stage_message(started)
            return
        if apply_shared_actions(action, self.player.possessions, self.missions_config, story=self.story):
            return
        if action.startswith("buy_ship:"):
            self.buy_ship(action.split(":", 1)[1])
        elif action == "take_loan" or action.startswith("take_loan:"):
            lender, amount, _ = self._loan_terms(action)
            self.player.possessions.take_loan(lender, amount)
            # Generic gameplay-event flag (see PlayerController's "used_turn")
            # - a "take out a loan" tutorial stage can use it as a complete_flag.
            self.player.possessions.flags["took_loan"] = True

    def buy_ship(self, ship_type_id):
        """Spend credits, add the ship to possessions, and let SpaceScreen
        (which owns the real flyable ship) configure it - shared by the
        dialogue-driven "buy_ship:" action and ShipBrowserMenu (via main.py's
        build_shop_menu), so both purchase paths perform the exact same
        mutation.

        Uninstalls whatever's currently equipped first: installed_outfits
        describes "whichever ship is flown" rather than a specific hull
        (see docs/SAVE_SYSTEM.md), so without this a new ship would
        silently inherit the old one's mounted outfits for free just
        because their slot ids happen to match - it should start bare,
        with those outfits back in your spares to reinstall."""
        cost = get_ship_type(self.story, ship_type_id).get("cost", 0)
        self.player.possessions.spend(cost)
        self.player.possessions.uninstall_all_outfits()
        self.player.possessions.add_ship(ship_type_id)
        # Generic gameplay-event flags (see PlayerController's "used_turn") -
        # a "buy your first ship" tutorial stage can use either as its
        # complete_flag. Set on both purchase paths since both funnel here.
        self.player.possessions.flags["bought_ship"] = True
        self.player.possessions.flags[f"bought_ship:{ship_type_id}"] = True
        if self.on_ship_purchased:
            self.on_ship_purchased(ship_type_id)

    def switch_ship(self, index):
        """Make owned_ships[index] the active hull (see
        Possessions.set_active_ship) - driven by ShipBrowserMenu's "Your
        Ships" tab. Uninstalls outfits for the same reason buy_ship() does
        (installed_outfits tracks "whichever ship is flown", not a hull),
        then lets SpaceScreen reconfigure and re-dock the real ship."""
        possessions = self.player.possessions
        if not 0 <= index < len(possessions.owned_ships) or index == possessions.active_ship_index:
            return
        possessions.uninstall_all_outfits()
        possessions.set_active_ship(index)
        if self.on_ship_switched:
            self.on_ship_switched(possessions.active_ship())
