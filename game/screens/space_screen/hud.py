"""SpaceScreen: hud — mixed into the class in screen.py."""
from game.screens.space_screen._defs import *  # noqa: F401,F403
from game.ui.report_menu import REP_BANDS


def _standing_band(standing):
    """(label, color) for a numeric faction standing - the same bands the
    Possessions "Standing" section uses (report_menu.REP_BANDS)."""
    for ceiling, label, color in REP_BANDS:
        if standing < ceiling:
            return label, color
    return f"{standing:+d}", (190, 190, 190)


class _HudMixin:

    def _player_has_scanner(self):
        """True when a "scan": true outfit (Sensor Array) is installed on the
        flown ship - see ships-core/ship_outfits.json. Gates the extra
        faction / standing / hull lines in the targeting panel."""
        possessions = self.player.person.possessions
        return any(
            get_ship_outfit(self.story, oid).get("scan")
            for oid in possessions.installed_outfits.values()
        )

    def _draw_target_arrow(self, surface, target):
        """Draw an arrow on an imaginary circle around the player's ship, pointing toward the target."""
        dx, dy = target.x - self.player.x, target.y - self.player.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance == 0:
            return

        # Normalize direction, then rotate it into screen space so the arrow
        # points the right way when the view is rotated (Q/E).
        dir_x, dir_y = utils.rotate_camera_vector(dx / distance, dy / distance)

        ui_scale = get_ui_scale()
        ship_x, ship_y = utils.to_screen(self.player.x, self.player.y)

        # Position on the circle around the ship, on the side facing the target
        radius = 45 * ui_scale
        arrow_x = ship_x + dir_x * radius
        arrow_y = ship_y + dir_y * radius

        # Arrow head points in direction of target
        arrow_size = 10 * ui_scale
        tip_x = arrow_x + dir_x * arrow_size
        tip_y = arrow_y + dir_y * arrow_size

        # Arrow tail points opposite
        tail_x = arrow_x - dir_x * arrow_size
        tail_y = arrow_y - dir_y * arrow_size

        # Perpendicular for arrow wings
        perp_x = -dir_y
        perp_y = dir_x

        # Draw arrow as triangle
        wing_size = 4 * ui_scale
        wing1_x = tail_x + perp_x * wing_size
        wing1_y = tail_y + perp_y * wing_size
        wing2_x = tail_x - perp_x * wing_size
        wing2_y = tail_y - perp_y * wing_size

        points = [(tip_x, tip_y), (wing1_x, wing1_y), (wing2_x, wing2_y)]
        pygame.draw.polygon(surface, GREEN, points)

    def _draw_minimap(self, surface, target_obj):
        """Local radar in the top-right corner: player stays centered, every
        other system object is plotted as a point at its true relative
        position/color, scaled down to MINIMAP_RANGE world units per half-
        height. Objects beyond that range simply don't appear - this is a
        local radar, not the galaxy-scale StarMap (M key), so it never needs
        to pan/zoom. Returns its rect so the HUD can stack the info panel
        below it.
        """
        ui_scale = get_ui_scale()
        # Fills the full side-panel width (see side_panel_width) so it shares
        # both vertical edges with the info panel stacked below it. Height is
        # capped at 40% of the window so the info panel always has room -
        # on a wide window that makes the radar a wide-ish rectangle rather
        # than a square, which is fine for a local radar (you just see more
        # to the sides than fore/aft).
        width = side_panel_width(ui_scale)
        height = min(width, int(utils.screen_height * 0.4))
        margin = hud_margin(ui_scale)
        rect = pygame.Rect(0, 0, width, height)
        rect.topright = (utils.screen_width - margin, margin)

        draw_glass_panel(surface, rect, ui_scale)

        px_per_unit = (height / 2) / MINIMAP_RANGE

        def project(x, y):
            # Rotate with the view (Q/E) so a blip stays in the same screen
            # direction as the object it marks.
            dx, dy = utils.rotate_camera_vector(x - self.player.x, y - self.player.y)
            return rect.centerx + dx * px_per_unit, rect.centery + dy * px_per_unit

        # (object, dot color, dot radius in px) - central star/celestial
        # bodies only included if this system actually has them.
        points = []
        if self.central_star:
            points.append((self.central_star, (255, 220, 80), 3))
        points.append((self.station, WHITE, 3))
        points.append((self.moon, (180, 180, 200), 3))
        for body in self.celestial_bodies:
            points.append((body, (100, 160, 255), 2))
        for ai_ship in self.ai_ships:
            points.append((ai_ship, GREEN, 2))

        # Rebuilt every frame (blips move) - (screen_x, screen_y, hit_radius,
        # obj) for each on-radar point, consumed by _minimap_blip_at for
        # hover text and click-to-target (see handle_input).
        self._minimap_blips = []
        for obj, color, radius in points:
            sx, sy = project(obj.x, obj.y)
            if rect.left <= sx <= rect.right and rect.top <= sy <= rect.bottom:
                r = max(1, int(radius * ui_scale))
                pygame.draw.circle(surface, color, (int(sx), int(sy)), r)
                if obj is target_obj:
                    pygame.draw.circle(surface, YELLOW, (int(sx), int(sy)), r + int(4 * ui_scale), 1)
                # Generous minimum hit area so tightly clustered blips (and
                # the 2px celestial/ship dots) are still easy to click/hover.
                hit_r = max(r + int(4 * ui_scale), int(9 * ui_scale))
                self._minimap_blips.append((sx, sy, hit_r, obj))

        # Player is always exactly centered, drawn last so it stays on top.
        pygame.draw.circle(surface, CYAN, rect.center, max(2, int(3 * ui_scale)))

        font_label = get_font(int(20 * ui_scale))
        label = font_label.render("System Map", True, GRAY)
        surface.blit(label, (rect.x + int(6 * ui_scale), rect.y + int(4 * ui_scale)))

        # Hover readout - the name of whatever blip the pointer is over,
        # following the cursor but clamped inside the panel. Drawn last so it
        # sits above the blips. (The click-to-target half lives in
        # handle_input.)
        hover_obj = self._minimap_blip_at(pygame.mouse.get_pos())
        if hover_obj is not None:
            self._draw_minimap_tooltip(surface, rect, ui_scale, hover_obj)

        self._minimap_rect = rect
        return rect

    def _draw_minimap_tooltip(self, surface, rect, ui_scale, obj):
        """Small label box near the cursor naming the hovered minimap blip
        (see _draw_minimap). Clamped to stay wholly inside `rect`."""
        font = get_font(int(18 * ui_scale))
        text = font.render(self._minimap_label(obj), True, WHITE)
        pad = int(5 * ui_scale)
        mx, my = pygame.mouse.get_pos()
        box = pygame.Rect(0, 0, text.get_width() + pad * 2, text.get_height() + pad * 2)
        box.topleft = (mx + int(12 * ui_scale), my + int(12 * ui_scale))
        box.right = min(box.right, rect.right - pad)
        box.left = max(box.left, rect.left + pad)
        box.bottom = min(box.bottom, rect.bottom - pad)
        box.top = max(box.top, rect.top + pad)
        bg = pygame.Surface(box.size, pygame.SRCALPHA)
        bg.fill((20, 30, 40, 225))
        surface.blit(bg, box.topleft)
        pygame.draw.rect(surface, (120, 140, 160), box, 1)
        surface.blit(text, (box.x + pad, box.y + pad))
        return box

    def _draw_hud(self, surface, target_obj, draw_hud=True):
        """Ship status, targeting, jump-target, help, and status-message
        overlays - styled with the same glass-panel look as the menus
        (ui_theme.py) instead of each being its own ad-hoc text blit.

        Anchored directly to the real screen edges (0/screen_width/
        screen_height), not get_ui_offset() - that offset centers the
        menus' fixed 800x600 virtual canvas within the window, which this
        full-viewport HUD isn't confined to. Adding it while right/bottom-
        anchoring (screen_width - x) pushed panels past the real edge,
        which is why the jump target panel was rendering off-screen.
        """
        ui_scale = get_ui_scale()
        margin = int(10 * ui_scale)

        # --- Top-right: minimap, then targeting info (incl. jump target)
        # stacked directly below it.
        minimap_rect = self._draw_minimap(surface, target_obj)

        # Always every line (placeholder "None" for the target rather than
        # omitting it) so the panel doesn't resize or appear/disappear as
        # targeting and jump selection change - only colors change. Lines
        # are (label, value, value_color) two-tone pairs (see
        # draw_info_panel) so the labels read distinctly from the values.
        target_name = self._get_target_name()
        mode_label = TARGET_MODES[self.target_mode_index]

        # selected_system_id is never None (see __init__) - it defaults to
        # the current system, so this always names somewhere. Jump Target
        # leads the pane: it's the one readout that's meaningful even with
        # nothing targeted.
        systems = get_star_systems(self.story)
        selected_name = systems.get(self.selected_system_id, {}).get("name", self.selected_system_id)
        jump_value = selected_name + (" (current)" if self.selected_system_id == self.system_id else "")

        lines = [
            ("Jump Target:", jump_value, CYAN, "block"),
            ("Targeting Mode:", mode_label, WHITE, "block"),
        ]
        if target_obj and target_name:
            lines.append(("Target:", target_name, GREEN))
            # Ships show their pilot; landing sites (station/moon) list what's
            # inside them so the player can see where they'll end up before
            # committing to land; other bodies show a hazard note if any -
            # these are mutually exclusive categories of targetable_objects.
            if isinstance(target_obj, Character):
                pilot_name = target_obj.person.name
                if pilot_name:
                    lines.append(("  Pilot:", pilot_name, WHITE))
                # Sensor Array (a "scan" outfit) reads the target's
                # allegiance and condition; without one the panel stays at
                # just type + pilot.
                if self._player_has_scanner():
                    possessions = self.player.person.possessions
                    faction_id = target_obj.faction
                    if faction_id:
                        faction_name = get_factions(self.story).get(faction_id, {}).get("name", faction_id)
                        band, band_color = _standing_band(possessions.reputation_with(faction_id))
                        lines.append(("  Faction:", faction_name, WHITE))
                        lines.append(("  Standing:", band, band_color))
                    else:
                        lines.append(("  Faction:", "Unaligned", GRAY))
                    ship = getattr(target_obj, "ship", None)
                    if ship and getattr(ship, "max_health", 0):
                        pct = max(0, round(100 * ship.health / ship.max_health))
                        hull_color = GREEN if pct >= 66 else (YELLOW if pct >= 33 else (235, 120, 110))
                        lines.append(("  Hull:", f"{pct}%", hull_color))
            elif isinstance(target_obj, LandingSite):
                lines.append(("  Locations:", GRAY))
                for label in target_obj.get_interior_labels():
                    lines.append((f"    - {label}", GRAY))
            elif getattr(target_obj, "hazardous", False):
                lines.append(("  Hazardous - not a landing site", YELLOW))
        else:
            lines.append(("Target:", "None", GRAY))

        info_rect, info_max_scroll = draw_info_panel(surface, lines, ui_scale, (utils.screen_width - margin, minimap_rect.bottom + margin), scroll=self.info_panel_scroll)
        self.info_panel_scroll = max(0, min(self.info_panel_scroll, info_max_scroll))
        self._info_panel_rect = info_rect

        # --- Top-left: control-help pane (shared design with LocationScreen's -
        # see draw_controls_pane). Hidden (draw_hud=False) while a modal menu
        # is up, and while a hail conversation has focus (it's mouse-only -
        # click an option or the X). C collapses it to a two-liner.
        controls_rect = None
        if draw_hud and not self.active_dialogue:
            # Controls with a persistent bottom-status prompt of their own
            # (F autopilot, G land, R hail, V jump) are deliberately left off
            # this pane - the on-screen prompt already says how, when it applies.
            # Self-explanatory mouse actions (wheel to scroll/zoom, click/hover
            # a blip) are left off too.
            help_items = [
                ("ESC", "Pause"),
                ("A / D", "Turn"),
                ("W", "Thrust"),
                ("S", "Reverse heading"),
                ("Z / X", "Rotate view"),
                ("T", "Target mode"),
                ("Q / E", "Cycle target"),
                ("Space", "Fire"),
                ("1", "Star map"),
                ("2", "Possessions"),
                ("3", "Mission log"),
            ]
            controls_rect = draw_controls_pane(surface, margin, margin, "Controls", help_items, ui_scale,
                                               collapsed=self.controls_collapsed)

        # --- Top-center: transient popups, each in its own glass pane (see
        # draw_glow_message), stacked downward so they can never overlap -
        # the "too close to jump" warning / an incoming hail banner (only
        # one of those is ever up at once) plus the mission/jump toast,
        # which can coexist with a hail (a mission stage advancing delivers
        # both its one_way_message banner and a "stage complete" toast the
        # same frame).
        popups = []
        if self.jump_message_timer > 0:
            popups.append((self.jump_message, YELLOW, (60, 45, 10)))
        elif self.hail_banner_timer > 0 and self.hail_banner:
            popups.append((self.hail_banner[0], self.hail_banner[1], (20, 30, 40)))
        if self.toast_timer > 0 and self.toast_text:
            popups.append((self.toast_text, self.toast_color, (20, 30, 40)))

        font_popup = get_font(int(20 * ui_scale))
        popup_y = margin + int(10 * ui_scale)
        for text, color, shadow in popups:
            popup_rect = draw_glow_message(
                surface, text, font_popup, utils.screen_width // 2, popup_y,
                color=color, shadow_color=shadow,
            )
            popup_y = popup_rect.bottom + int(8 * ui_scale)

        # --- Bottom-center: current status. Being mid-jump or having
        # autopilot engaged are exclusive committed states (almost any key
        # cancels/doesn't apply), but the land/jump/autopilot *availability*
        # prompts are independent of each other and can all be true at
        # once, so they stack as separate lines in one panel instead of
        # being mutually exclusive. Skipped entirely while active_dialogue
        # is set, same reason as the controls-pane swap above.
        status_rect = None
        if draw_hud and not self.active_dialogue:
            status_lines = []
            if self.jump_state:
                status_text = "Aligning for jump..." if self.jump_state["phase"] == "align" else "JUMPING..."
                status_lines = [(status_text, GREEN)]
            elif self.player.autopilot_active:
                status_lines = [("Autopilot engaged - press any key to cancel", GREEN)]
                if self.player.autopilot_target is not None:
                    status_lines.append((f"Approaching: {self._approaching_label(self.player.autopilot_target)}", GREEN))
            else:
                speed = math.hypot(self.player.velocity_x, self.player.velocity_y)
                if self.landing_text > 0:
                    status_lines.append(("Press G to Land", GREEN))
                elif speed >= 0.4 and (
                    self.station.get_distance(self.player.x, self.player.y) < self.station.landing_distance
                    or self.moon.get_distance(self.player.x, self.player.y) < self.moon.landing_distance
                ):
                    status_lines.append(("Slow down to land", RED))
                # Jump Target is never None now (see __init__). A jump to a
                # *different* system is always allowed; a jump back to the
                # current one needs distance from center first (see try_jump/
                # JUMP_SELF_MIN_DISTANCE), so only prompt for it once that's
                # actually true.
                if self.selected_system_id != self.system_id:
                    status_lines.append(("Press V to Jump", GREEN))
                elif self._drifted_from_center():
                    status_lines.append(("Drifting far from the system - open the Star Map (1) and jump (V) back", YELLOW))
                if target_obj:
                    status_lines.append(("Press F for Autopilot", GREEN))
                if isinstance(target_obj, Character):
                    status_lines.append((f"Press R to Hail {target_obj.person.name or 'Target'}", GREEN))

            ship = self.player.ship
            if ship and ship.health < ship.max_health:
                pct = max(0, int(100 * ship.health / ship.max_health))
                status_lines.append((f"Hull: {pct}%", RED if pct < 34 else YELLOW))

            # Current act + active mission, so the story context is always
            # on screen (see utils.current_act, story.json's "acts").
            possessions = self.player.person.possessions
            act = utils.current_act(self.story, possessions.flags)
            if act.get("name"):
                status_lines.append((f"Act: {act['name']}", CYAN))
            for mission_id in possessions.missions:
                title = self.missions_config.get(mission_id, {}).get("title")
                if title:
                    status_lines.append((f"Mission: {title}", CYAN))
                break

            status_rect = draw_status_pane(surface, status_lines, ui_scale)

        # --- Bottom-left: received one-way messages (see
        # _check_one_way_hails/Possessions.add_message) - easy to miss as
        # just a transient banner, so they also collect here until there's
        # something to actually look back at. Skipped along with the rest
        # of the HUD while a modal menu/hail dialogue has focus.
        message_log_rect = None
        if draw_hud and not self.active_dialogue:
            messages = [(m["sender"], m["text"]) for m in self.player.person.possessions.message_log]
            message_log_rect, message_log_max_scroll = draw_message_log(surface, messages, ui_scale, self.message_log_scroll, alert=message_alert_state(self.message_alert_timer)[0])
            # Clamp now that the real wrapped-line count is known (window
            # resize or a shrinking log can leave the stored offset too big).
            self.message_log_scroll = max(0, min(self.message_log_scroll, message_log_max_scroll))
            self._message_log_max_scroll = message_log_max_scroll
        self._message_log_rect = message_log_rect

        # Cached for handle_input()'s mouse-click targeting, so a click on
        # any of these panels doesn't also register as a click-to-target in
        # the world behind them (see _hud_click_rects' own comment).
        self._hud_click_rects = [rect for rect in (minimap_rect, info_rect, controls_rect, status_rect, message_log_rect) if rect]
