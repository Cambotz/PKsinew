#!/usr/bin/env python3

"""
ui_pcbox_input.py — Controller and mouse input mixin for PCBox.

Extracted from pc_box.py. Provides PCBoxInputMixin.

Usage
-----
    class PCBox(PCBoxDrawMixin, PCBoxInputMixin):
        ...

The mixin calls data/state methods that remain in PCBox proper
(e.g. self.prev_box(), self.next_box(), self.toggle_party_panel(),
self._start_move_mode(), self._open_summary(), etc.).
"""

import builtins


try:
    from pokemon_summary import PokemonSummary
    _SUMMARY_AVAILABLE = True
except ImportError:
    PokemonSummary = None
    _SUMMARY_AVAILABLE = False


class PCBoxInputMixin:
    """Mixin providing all controller and mouse input handling for PCBox."""

    # ------------------------------------------------------------------ #
    #  Top-level controller dispatch                                       #
    # ------------------------------------------------------------------ #

    def handle_controller(self, ctrl):
        """
        Handle controller input for PC Box

        Navigation layout:
        - Top row: [Game Button] (left/right changes game)
        - Second row: [Box Button] (left/right changes box)
        - Main area: Left side has [Party][Close], right side has [6x5 Grid]
        - Party panel: Overlays when open

        Args:
            ctrl: ControllerManager instance

        Returns:
            bool: True if input was consumed
        """
        consumed = False

        # Handle sub_modal first (summary screen takes priority)
        if self.sub_modal:
            if hasattr(self.sub_modal, "handle_controller"):
                self.sub_modal.handle_controller(ctrl)
            return True  # Consume all input while sub_modal is open

        # Handle evolution dialog (takes priority)
        if self.evolution_dialog_open:
            return self._handle_evolution_controller(ctrl)

        # Handle Altering Cave dialog/spinner (takes priority)
        if self.altering_cave_dialog_open:
            return self._handle_altering_cave_controller(ctrl)

        # Handle confirmation dialog first (takes priority)
        if self.confirmation_dialog_open:
            return self._handle_confirmation_controller(ctrl)

        # Handle options menu
        if self.options_menu_open:
            return self._handle_options_menu_controller(ctrl)

        # B button behavior
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            if self.move_mode:
                # Cancel move mode
                self._cancel_move_mode()
            elif self.party_panel_open:
                self.toggle_party_panel()
            else:
                self.close_callback()
            return True

        # Pause combo to resume game (if game is paused)
        try:
            if self._check_pause_combo(ctrl):
                # Only trigger once - check if we already triggered
                if not getattr(self, "_resume_combo_triggered", False):
                    self._resume_combo_triggered = True
                    if self.resume_game_callback:
                        # Consume the buttons used in the combo
                        setting = self._pause_combo_setting
                        if setting.get("type") == "combo":
                            for btn in setting.get("buttons", []):
                                ctrl.consume_button(btn)
                        print("[PCBox] Pause combo - calling resume callback")
                        self.resume_game_callback()
                        return True
            else:
                # Reset trigger flag when combo released
                self._resume_combo_triggered = False
        except Exception as e:
            print(f"[PCBox] Pause combo check error: {e}")

        # L/R shoulder buttons for box navigation (always available)
        if ctrl.is_button_just_pressed("L"):
            ctrl.consume_button("L")
            self.prev_box()
            return True

        if ctrl.is_button_just_pressed("R"):
            ctrl.consume_button("R")
            self.next_box()
            return True

        # Handle based on current focus mode
        if self.party_panel_open:
            consumed = self._handle_party_controller(ctrl)
        elif self.focus_mode == "grid":
            consumed = self._handle_grid_controller(ctrl)
        elif self.focus_mode == "game_button":
            consumed = self._handle_game_button_controller(ctrl)
        elif self.focus_mode == "box_button":
            consumed = self._handle_box_button_controller(ctrl)
        elif self.focus_mode == "side_buttons":
            consumed = self._handle_side_buttons_controller(ctrl)
        elif self.focus_mode == "undo_button":
            # Safety check: if undo is no longer available, redirect to grid
            if not self.undo_available:
                self.focus_mode = "grid"
                consumed = self._handle_grid_controller(ctrl)
            else:
                consumed = self._handle_undo_button_controller(ctrl)

        return consumed

    # ------------------------------------------------------------------ #
    #  Dialog controllers                                                  #
    # ------------------------------------------------------------------ #

    def _handle_options_menu_controller(self, ctrl):
        """Handle controller input for options menu"""
        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            self.options_menu_selected = (self.options_menu_selected - 1) % len(
                self.options_menu_items
            )
            return True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            self.options_menu_selected = (self.options_menu_selected + 1) % len(
                self.options_menu_items
            )
            return True

        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            selected_option = self.options_menu_items[self.options_menu_selected]
            self._execute_options_menu(selected_option)
            return True

        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.options_menu_open = False
            return True

        return True

    def _handle_confirmation_controller(self, ctrl):
        """Handle controller input for confirmation dialog"""
        if ctrl.is_dpad_just_pressed("left") or ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("left")
            ctrl.consume_dpad("right")
            self.confirmation_selected = 1 - self.confirmation_selected  # Toggle 0/1
            return True

        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            if self.confirmation_selected == 0:  # Yes
                if self.confirmation_dialog_callback:
                    self.confirmation_dialog_callback()
            self.confirmation_dialog_open = False
            self.confirmation_dialog_callback = None
            return True

        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.confirmation_dialog_open = False
            self.confirmation_dialog_callback = None
            return True

        return True

    # ------------------------------------------------------------------ #
    #  Focus-mode controllers                                              #
    # ------------------------------------------------------------------ #

    def _handle_grid_controller(self, ctrl):
        """Handle controller input when grid is focused"""
        consumed = False
        current_idx = self.grid_nav.get_selected()
        current_col = current_idx % 6
        current_row = current_idx // 6

        # D-pad navigation
        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            if current_row == 0:
                # At top row
                if self.sinew_mode and self.sinew_scroll_offset > 0:
                    # Scroll up in Sinew mode
                    self.scroll_sinew_up()
                else:
                    # Move to box button
                    self.focus_mode = "box_button"
            else:
                self.grid_nav.navigate("up")
                self._update_grid_selection()
            consumed = True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            if current_row < 4:  # Not at bottom row
                self.grid_nav.navigate("down")
                self._update_grid_selection()
            elif self.sinew_mode:
                # At bottom row in Sinew mode - try to scroll down
                self.scroll_sinew_down()
            consumed = True

        if ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_dpad("left")
            if current_col == 0:
                # At left edge - move to undo button if available, else side buttons
                if self.undo_available:
                    self.focus_mode = "undo_button"
                else:
                    self.focus_mode = "side_buttons"
                    if self.sinew_mode:
                        self.side_button_index = 1  # Close
                    else:
                        self.side_button_index = 0  # Party
            else:
                self.grid_nav.navigate("left")
                self._update_grid_selection()
            consumed = True

        if ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("right")
            if current_col < 5:  # Not at right edge
                self.grid_nav.navigate("right")
                self._update_grid_selection()
            consumed = True

        # L/R buttons for fast scrolling in Sinew mode
        if self.sinew_mode:
            if ctrl.is_button_just_pressed("L"):
                ctrl.consume_button("L")
                # Scroll up 5 rows
                for _ in range(5):
                    if not self.scroll_sinew_up():
                        break
                consumed = True

            if ctrl.is_button_just_pressed("R"):
                ctrl.consume_button("R")
                # Scroll down 5 rows
                for _ in range(5):
                    if not self.scroll_sinew_down():
                        break
                consumed = True

        # A button selects Pokemon
        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            self._select_grid_pokemon()
            consumed = True

        # SELECT button in dev mode: export Pokemon
        if ctrl.is_button_just_pressed("SELECT"):
            ctrl.consume_button("SELECT")
            dev_mode = getattr(builtins, "SINEW_DEV_MODE", False)
            print(
                f"[PCBox] SELECT pressed - dev_mode={dev_mode}, "
                f"selected={self.selected_pokemon is not None}"
            )
            if dev_mode and self.selected_pokemon:
                self._export_pokemon_for_achievement()
            elif not self.sinew_mode:
                self.toggle_party_panel()
            consumed = True

        # START button opens party panel (only for non-Sinew mode)
        if ctrl.is_button_just_pressed("START"):
            ctrl.consume_button("START")
            if not self.sinew_mode:  # Sinew has no party
                self.toggle_party_panel()
            consumed = True

        return consumed

    def _handle_game_button_controller(self, ctrl):
        """Handle controller when game button is focused"""
        consumed = False

        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            # Stay on game button (nothing above)
            consumed = True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            # Move to box button
            self.focus_mode = "box_button"
            consumed = True

        if ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_dpad("left")
            # Change to previous game
            self.change_game(-1)
            consumed = True

        if ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("right")
            # Change to next game
            self.change_game(1)
            consumed = True

        # A button does nothing special on game button
        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            consumed = True

        return consumed

    def _handle_box_button_controller(self, ctrl):
        """Handle controller when box button is focused"""
        consumed = False

        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            # Move to game button
            self.focus_mode = "game_button"
            consumed = True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            # Move to grid (top row)
            self.focus_mode = "grid"
            # Set grid selection to top row, middle-ish
            self.grid_nav.set_selected(2)  # Column 2 of row 0
            self._update_grid_selection()
            consumed = True

        if ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_dpad("left")
            # Change to previous box
            self.prev_box()
            consumed = True

        if ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("right")
            # Change to next box
            self.next_box()
            consumed = True

        # A button does nothing special on box button
        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            consumed = True

        return consumed

    def _handle_side_buttons_controller(self, ctrl):
        """Handle controller when side buttons (Party/Close) are focused"""
        consumed = False

        # Button indices: 0 = Party, 1 = Close
        min_button = 1 if self.sinew_mode else 0
        max_button = 1

        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            if self.side_button_index > min_button:
                self.side_button_index -= 1
            consumed = True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            if self.side_button_index < max_button:
                self.side_button_index += 1
            consumed = True

        if ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_dpad("left")
            # Stay on side buttons (nothing to the left)
            consumed = True

        if ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("right")
            # Move to undo button if available, otherwise to grid
            if self.undo_available:
                self.focus_mode = "undo_button"
            else:
                self.focus_mode = "grid"
                current_grid = self.grid_nav.get_selected()
                new_row = min(2, current_grid // 6)
                self.grid_nav.set_selected(new_row * 6)
                self._update_grid_selection()
            consumed = True

        # A button activates the selected button
        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            if self.side_button_index == 0 and not self.sinew_mode:
                self.toggle_party_panel()
            elif self.side_button_index == 1:
                self.close_callback()
            consumed = True

        return consumed

    def _handle_undo_button_controller(self, ctrl):
        """Handle controller when undo button is focused"""
        consumed = False

        if ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_dpad("left")
            # Move to side buttons
            self.focus_mode = "side_buttons"
            self.side_button_index = 1 if self.sinew_mode else 0
            consumed = True

        if ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("right")
            # Move to grid
            self.focus_mode = "grid"
            current_grid = self.grid_nav.get_selected()
            new_row = min(2, current_grid // 6)
            self.grid_nav.set_selected(new_row * 6)
            self._update_grid_selection()
            consumed = True

        if ctrl.is_dpad_just_pressed("up") or ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("up")
            ctrl.consume_dpad("down")
            # No vertical movement on undo button
            consumed = True

        # A button executes undo
        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            self._execute_undo()
            # After undo, button disappears - move to grid
            if not self.undo_available:
                self.focus_mode = "grid"
            consumed = True

        # B button goes back to grid
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.focus_mode = "grid"
            consumed = True

        return consumed

    def _handle_party_controller(self, ctrl):
        """Handle controller input when party panel is focused"""
        consumed = False

        # D-pad navigation for party slots
        # Layout: 1 big slot on left, 5 smaller slots on right
        # We'll treat it as a 2-column grid
        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            if self.party_selected > 0:
                if self.party_selected == 1:
                    # From first right slot to left slot
                    self.party_selected = 0
                elif self.party_selected > 1:
                    # Move up in right column
                    self.party_selected -= 1
                self._update_party_selection()
            consumed = True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            if self.party_selected == 0:
                # From left slot to first right slot
                self.party_selected = 1
            elif self.party_selected < 5:
                self.party_selected += 1
            self._update_party_selection()
            consumed = True

        if ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_dpad("left")
            if self.party_selected > 0:
                self.party_selected = 0
                self._update_party_selection()
            consumed = True

        if ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("right")
            if self.party_selected == 0:
                # From left slot to right column
                self.party_selected = 1
                self._update_party_selection()
            else:
                # Already in right column - close party panel and go to grid
                self.toggle_party_panel()
                self.focus = "grid"
            consumed = True

        # A button selects party Pokemon
        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            self._select_party_pokemon()
            consumed = True

        # SELECT button in dev mode: export Pokemon
        if ctrl.is_button_just_pressed("SELECT"):
            ctrl.consume_button("SELECT")
            if getattr(builtins, "SINEW_DEV_MODE", False) and self.selected_pokemon:
                self._export_pokemon_for_achievement()
            consumed = True

        return consumed

    # ------------------------------------------------------------------ #
    #  Grid / party selection helpers                                      #
    # ------------------------------------------------------------------ #

    def _update_grid_selection(self):
        """Update selected Pokemon based on grid navigation"""
        grid_index = self.grid_nav.get_selected()
        poke = self.get_pokemon_at_grid_slot(grid_index)
        if poke and not poke.get("empty"):
            self.selected_pokemon = poke
        else:
            # Clear selection when over empty slot
            self.selected_pokemon = None

    def _select_grid_pokemon(self):
        """Select Pokemon at current grid position - opens options menu or places if in move mode"""
        grid_index = self.grid_nav.get_selected()
        poke = self.get_pokemon_at_grid_slot(grid_index)

        if self.move_mode:
            # In move mode - try to place Pokemon here
            self._attempt_place_pokemon("box", self.box_index + 1, grid_index)
        elif poke and not poke.get("empty"):
            self.selected_pokemon = poke

            # Check for Altering Cave Zubat (special interaction)
            is_ac_zubat = self._is_altering_cave_zubat(poke)

            if is_ac_zubat:
                # Determine location info for this Pokemon
                if self.is_sinew_storage():
                    # Sinew storage: (box, slot) - need actual slot index accounting for scroll
                    actual_slot = grid_index + (self.sinew_scroll_offset * 6)
                    location = (self.box_index, actual_slot)
                    print(
                        f"[PCBox] AC Zubat location (Sinew): box_index={self.box_index}, "
                        f"actual_slot={actual_slot}"
                    )
                else:
                    # Game save: (save_path, box, slot)
                    # Check if the current game is running - can't modify save while game is active
                    if self._is_current_game_running():
                        self._show_warning(
                            "Game is running!\nStop game first\nto use Echo"
                        )
                        print(
                            "[PCBox] Blocked Altering Cave exchange - game is running"
                        )
                        return

                    save_path = self._get_current_save_path()
                    location = (save_path, self.box_index, grid_index)
                    print(
                        f"[PCBox] AC Zubat location (Game): box_index={self.box_index}, "
                        f"grid_index={grid_index}"
                    )

                self._show_altering_cave_dialog(poke, location)
                return

            # Open options menu for this Pokemon
            if self.undo_available:
                self.options_menu_items = [
                    "MOVE",
                    "SUMMARY",
                    "RELEASE",
                    "UNDO",
                    "CANCEL",
                ]
            else:
                self.options_menu_items = ["MOVE", "SUMMARY", "RELEASE", "CANCEL"]
            self.options_menu_open = True
            self.options_menu_selected = 0
            print(f"Options for: {self.manager.format_pokemon_display(poke)}")

    def _update_party_selection(self):
        """Update selected Pokemon based on party navigation"""
        if self.party_selected < len(self.party_data):
            poke = self.party_data[self.party_selected]
            self.selected_pokemon = poke
        else:
            # Clear selection when over empty party slot
            self.selected_pokemon = None

    def _select_party_pokemon(self):
        """Select Pokemon from party panel - opens options menu or places if in move mode"""
        if self.party_selected < len(self.party_data):
            poke = self.party_data[self.party_selected]

            if self.move_mode:
                # Can't place in party for now (party transfers more complex)
                print("Cannot place Pokemon in party - use PC boxes")
                return
            if poke and not poke.get("empty"):
                self.selected_pokemon = poke

                # Check for Altering Cave Zubat (special interaction)
                # Note: Party Pokemon can't be exchanged since they're in active use
                # Just show normal options for party

                # Open options menu for this Pokemon (no RELEASE for party)
                if self.undo_available:
                    self.options_menu_items = ["MOVE", "SUMMARY", "UNDO", "CANCEL"]
                else:
                    self.options_menu_items = ["MOVE", "SUMMARY", "CANCEL"]
                self.options_menu_open = True
                self.options_menu_selected = 0
                print(f"Options for party: {self.manager.format_pokemon_display(poke)}")

    # ------------------------------------------------------------------ #
    #  Options menu execution                                              #
    # ------------------------------------------------------------------ #

    def _execute_options_menu(self, option):
        """Execute the selected option from options menu"""
        self.options_menu_open = False

        if option == "MOVE":
            self._start_move_mode()
        elif option == "SUMMARY":
            self._open_summary()
        elif option == "RELEASE":
            self._confirm_release_pokemon()
        elif option == "UNDO":
            self._execute_undo()
        elif option == "CANCEL":
            pass  # Just close menu

    def _open_summary(self):
        """Open Pokemon summary screen"""
        if self.selected_pokemon and _SUMMARY_AVAILABLE and PokemonSummary:

            def close_summary():
                self.sub_modal = None

            # Determine game type from current game name
            game_name = (
                self.get_current_game() if self.get_current_game_callback else "Emerald"
            )
            if game_name in ("FireRed", "LeafGreen"):
                game_type = "FRLG"
            else:
                game_type = "RSE"

            # Create navigation callbacks based on whether we're viewing party or box
            if self.party_panel_open:
                # Navigating party Pokemon
                prev_callback = self._get_prev_party_pokemon
                next_callback = self._get_next_party_pokemon
            else:
                # Navigating box Pokemon
                prev_callback = self._get_prev_box_pokemon
                next_callback = self._get_next_box_pokemon

            self.sub_modal = PokemonSummary(
                pokemon=self.selected_pokemon,
                width=self.width,
                height=self.height,
                font=self.font,
                close_callback=close_summary,
                manager=self.manager,
                game_type=game_type,
                prev_pokemon_callback=prev_callback,
                next_pokemon_callback=next_callback,
            )
            print(
                f"[PCBox] Opening summary for: {self.selected_pokemon.get('nickname', 'Pokemon')}"
            )
        elif self.selected_pokemon:
            print(
                f"[PCBox] Summary not available for: "
                f"{self.selected_pokemon.get('nickname', 'Pokemon')}"
            )

    def _confirm_release_pokemon(self):
        """Show confirmation dialog before releasing Pokemon"""
        if not self.selected_pokemon:
            return

        pokemon_name = self.selected_pokemon.get(
            "nickname"
        ) or self.selected_pokemon.get("species_name", "Pokemon")

        # Store the release target info
        if self.party_panel_open:
            self._release_target = {"type": "party", "slot": self.party_selected}
        else:
            self._release_target = {
                "type": "sinew" if self.sinew_mode else "box",
                "box": self.box_index + 1,
                "slot": self.grid_nav.get_selected(),
            }

        # Show confirmation dialog
        self.confirmation_dialog_open = True
        self.confirmation_dialog_message = (
            f"Release {pokemon_name}?\nThis cannot be undone!"
        )
        self.confirmation_dialog_callback = self._do_release_pokemon
        self.confirmation_selected = 1  # Default to No for safety

    def _do_release_pokemon(self):
        """Actually release the Pokemon after confirmation"""
        if not hasattr(self, "_release_target") or not self._release_target:
            print("[PCBox] No release target set")
            return

        target = self._release_target
        self._release_target = None

        try:
            if target["type"] == "party":
                # Cannot release from party in PC box screen
                print("[PCBox] Cannot release party Pokemon from PC screen")
                self._show_warning("Cannot release party Pokemon here")
                return

            if target["type"] == "sinew":
                # Release from Sinew storage
                if self.sinew_storage:
                    box_num = target["box"]
                    slot_idx = target["slot"]

                    # Adjust for scrolling
                    if self.sinew_scroll_offset > 0:
                        adjusted_slot = slot_idx + (self.sinew_scroll_offset * 6)
                    else:
                        adjusted_slot = slot_idx

                    # Store for undo BEFORE clearing
                    released_pokemon = (
                        self.selected_pokemon.copy() if self.selected_pokemon else None
                    )
                    if released_pokemon:
                        self.undo_action = {
                            "type": "release",
                            "pokemon_data": released_pokemon,
                            "location": {
                                "type": "sinew",
                                "box": box_num,
                                "slot": adjusted_slot,
                            },
                        }
                        self.undo_available = True

                    self.sinew_storage.clear_slot(box_num, adjusted_slot)
                    print(
                        f"[PCBox] Released Pokemon from Sinew "
                        f"Box {box_num}, Slot {adjusted_slot + 1}"
                    )

                    # Refresh display
                    self._refresh_current_box()
                    self.selected_pokemon = None
                else:
                    print("[PCBox] Sinew storage not available")

            elif target["type"] == "box":
                # Release from game PC box
                try:
                    from save_writer import clear_pc_slot, write_save_file

                    game_name = (
                        self.get_current_game()
                        if self.get_current_game_callback
                        else None
                    )
                    if not game_name:
                        print("[PCBox] No game selected for release")
                        return

                    # Get save data from parser
                    if not self.manager or not self.manager.parser:
                        print("[PCBox] No save data available")
                        return

                    save_data = self.manager.parser.data
                    save_path = self.manager.current_save_path
                    if not save_data or not save_path:
                        print("[PCBox] No save data available")
                        return

                    # Determine game type
                    if game_name in ("FireRed", "LeafGreen"):
                        game_type = "FRLG"
                    else:
                        game_type = "RSE"

                    box_num = target["box"]
                    slot_idx = target["slot"]

                    # Store for undo BEFORE clearing
                    released_pokemon = (
                        self.selected_pokemon.copy() if self.selected_pokemon else None
                    )
                    if released_pokemon:
                        self.undo_action = {
                            "type": "release",
                            "pokemon_data": released_pokemon,
                            "location": {
                                "type": "box",
                                "box": box_num,
                                "slot": slot_idx,
                                "game": game_name,
                                "save_path": save_path,
                            },
                        }
                        self.undo_available = True

                    # Clear the slot
                    success = clear_pc_slot(save_data, box_num, slot_idx, game_type)

                    if success:
                        # Save the changes using write_save_file
                        write_save_file(save_path, save_data, create_backup_first=True)
                        # Reload the save to refresh cache
                        self.manager.reload()
                        print(
                            f"[PCBox] Released Pokemon from Box {box_num}, Slot {slot_idx + 1}"
                        )

                        # Refresh display
                        self._refresh_current_box()
                        self.selected_pokemon = None
                    else:
                        print("[PCBox] Failed to clear PC slot")
                        # Clear undo if release failed
                        self.undo_available = False
                        self.undo_action = None

                except ImportError:
                    print("[PCBox] save_writer module not available")
                except Exception as e:
                    print(f"[PCBox] Error releasing from PC: {e}")
                    import traceback

                    traceback.print_exc()

        except Exception as e:
            print(f"[PCBox] Error releasing Pokemon: {e}")
            import traceback

            traceback.print_exc()

    def _refresh_current_box(self):
        """Refresh the current box data after a change"""
        if self.sinew_mode:
            if self.sinew_storage and self.sinew_storage.is_loaded():
                self.current_box_data = self.sinew_storage.get_box(self.box_index + 1)
        else:
            if self.manager:
                self.current_box_data = self.manager.get_box(self.box_index + 1)

        # Clear sprite cache for this box to force reload
        self.sprite_cache.clear()

    def _execute_undo(self):
        """Undo the last action"""
        if not self.undo_available or not self.undo_action:
            self._show_warning("Nothing to undo")
            return

        action = self.undo_action
        action_type = action.get("type")

        # Import save_writer functions at top level for all branches
        from save_writer import clear_pc_slot, write_pokemon_to_pc, write_save_file, load_save_file

        try:
            if action_type == "release":
                # Undo release - restore the Pokemon
                pokemon_data = action.get("pokemon_data")
                location = action.get(
                    "location"
                )  # {'type': 'sinew'/'box', 'box': int, 'slot': int}

                if location["type"] == "sinew" and self.sinew_storage:
                    self.sinew_storage.set_pokemon_at(
                        location["box"], location["slot"], pokemon_data
                    )
                    self._show_warning("Undo: Pokemon restored!")
                    self._refresh_current_box()
                elif location["type"] == "box":
                    # Restore to game PC
                    save_path = location.get("save_path")
                    raw_bytes = pokemon_data.get("raw_bytes")

                    if save_path and raw_bytes:
                        save_data = load_save_file(save_path)
                        game_type = (
                            "FRLG"
                            if location.get("game") in ("FireRed", "LeafGreen")
                            else "RSE"
                        )
                        write_pokemon_to_pc(
                            save_data,
                            location["box"],
                            location["slot"],
                            raw_bytes,
                            game_type,
                        )
                        write_save_file(save_path, save_data, create_backup_first=True)

                        # Reload manager
                        if self.manager:
                            self.manager.reload()

                        self._show_warning("Undo: Pokemon restored!")
                        self._refresh_current_box()

                print("[PCBox] Undo release successful")

            elif action_type == "move":
                move_type = action.get("move_type")
                pokemon = action.get("pokemon")
                source = action.get("source")
                dest = action.get("dest")

                if move_type == "sinew_to_sinew":
                    # Undo Sinew internal move - swap back
                    source_pokemon = action.get("source_pokemon")
                    dest_pokemon = action.get(
                        "dest_pokemon"
                    )  # Was the pokemon that got displaced (or None)

                    if self.sinew_storage:
                        # Put source pokemon back to source
                        self.sinew_storage.set_pokemon_at(
                            source["box"], source["slot"], source_pokemon
                        )
                        # Put dest pokemon back to dest (or clear if was empty)
                        if dest_pokemon:
                            self.sinew_storage.set_pokemon_at(
                                dest["box"], dest["slot"], dest_pokemon
                            )
                        else:
                            self.sinew_storage.clear_slot(dest["box"], dest["slot"])

                        self._show_warning("Undo: Move reversed!")
                        self._refresh_current_box()
                        print("[PCBox] Undo sinew_to_sinew successful")

                elif move_type == "game_to_sinew":
                    # Undo deposit: clear Sinew, restore to game save
                    raw_bytes = pokemon.get("raw_bytes")

                    if self.sinew_storage and raw_bytes and source.get("save_path"):
                        # 1. Clear from Sinew
                        self.sinew_storage.clear_slot(dest["box"], dest["slot"])

                        # 2. Restore to game save
                        save_path = source.get("save_path")
                        game_type = (
                            "FRLG"
                            if source.get("game") in ("FireRed", "LeafGreen")
                            else "RSE"
                        )
                        save_data = load_save_file(save_path)
                        write_pokemon_to_pc(
                            save_data,
                            source["box"],
                            source["slot"],
                            raw_bytes,
                            game_type,
                        )
                        write_save_file(save_path, save_data, create_backup_first=True)

                        # 3. Reload manager
                        if self.manager:
                            self.manager.reload()

                        self._show_warning("Undo: Move reversed!")
                        self._refresh_current_box()
                        print("[PCBox] Undo game_to_sinew successful")

                elif move_type == "sinew_to_game":
                    # Undo withdrawal: restore to Sinew, clear from game save

                    if self.sinew_storage and pokemon and dest.get("save_path"):
                        # 1. Restore to Sinew
                        self.sinew_storage.set_pokemon_at(
                            source["box"], source["slot"], pokemon
                        )

                        # 2. Clear from game save
                        save_path = dest.get("save_path")
                        game_type = dest.get("game_type", "RSE")
                        save_data = load_save_file(save_path)
                        clear_pc_slot(save_data, dest["box"], dest["slot"], game_type)
                        write_save_file(save_path, save_data, create_backup_first=True)

                        # 3. Reload manager
                        if self.manager:
                            self.manager.reload()

                        self._show_warning("Undo: Move reversed!")
                        self._refresh_current_box()
                        print("[PCBox] Undo sinew_to_game successful")

                elif move_type == "game_to_game":
                    # Undo game-to-game transfer
                    raw_bytes = pokemon.get("raw_bytes")

                    if raw_bytes and source.get("save_path") and dest.get("save_path"):
                        # 1. Clear from destination game
                        dest_save_data = load_save_file(dest["save_path"])
                        clear_pc_slot(
                            dest_save_data,
                            dest["box"],
                            dest["slot"],
                            dest.get("game_type", "RSE"),
                        )
                        write_save_file(
                            dest["save_path"], dest_save_data, create_backup_first=True
                        )

                        # 2. Restore to source game
                        source_save_data = load_save_file(source["save_path"])
                        write_pokemon_to_pc(
                            source_save_data,
                            source["box"],
                            source["slot"],
                            raw_bytes,
                            source.get("game_type", "RSE"),
                        )
                        write_save_file(
                            source["save_path"],
                            source_save_data,
                            create_backup_first=True,
                        )

                        # 3. Reload manager
                        if self.manager:
                            self.manager.reload()

                        self._show_warning("Undo: Move reversed!")
                        self._refresh_current_box()
                        print("[PCBox] Undo game_to_game successful")

            # Clear undo state after successful undo
            self.undo_available = False
            self.undo_action = None

        except Exception as e:
            print(f"[PCBox] Undo failed: {e}")
            import traceback

            traceback.print_exc()
            self._show_warning("Undo failed!")

    # ------------------------------------------------------------------ #
    #  Summary navigation helpers                                          #
    # ------------------------------------------------------------------ #

    def _get_prev_party_pokemon(self):
        """Get previous Pokemon in party for summary navigation"""
        if not self.party_data:
            return None

        # Find current index
        start_idx = self.party_selected

        # Search backwards for non-empty slot
        for i in range(1, len(self.party_data) + 1):
            idx = (start_idx - i) % len(self.party_data)
            poke = self.party_data[idx] if idx < len(self.party_data) else None
            if poke and not poke.get("empty"):
                self.party_selected = idx
                self.selected_pokemon = poke
                return poke
        return None

    def _get_next_party_pokemon(self):
        """Get next Pokemon in party for summary navigation"""
        if not self.party_data:
            return None

        # Find current index
        start_idx = self.party_selected

        # Search forwards for non-empty slot
        for i in range(1, len(self.party_data) + 1):
            idx = (start_idx + i) % len(self.party_data)
            poke = self.party_data[idx] if idx < len(self.party_data) else None
            if poke and not poke.get("empty"):
                self.party_selected = idx
                self.selected_pokemon = poke
                return poke
        return None

    def _get_prev_box_pokemon(self):
        """Get previous Pokemon in current box for summary navigation"""
        if not self.current_box_data:
            return None

        start_idx = self.grid_nav.get_selected()

        # Search backwards for non-empty slot
        for i in range(1, 31):
            idx = (start_idx - i) % 30
            poke = (
                self.current_box_data[idx] if idx < len(self.current_box_data) else None
            )
            if poke and not poke.get("empty"):
                self.grid_nav.selected = idx
                self.selected_pokemon = poke
                return poke
        return None

    def _get_next_box_pokemon(self):
        """Get next Pokemon in current box for summary navigation"""
        if not self.current_box_data:
            return None

        start_idx = self.grid_nav.get_selected()

        # Search forwards for non-empty slot
        for i in range(1, 31):
            idx = (start_idx + i) % 30
            poke = (
                self.current_box_data[idx] if idx < len(self.current_box_data) else None
            )
            if poke and not poke.get("empty"):
                self.grid_nav.selected = idx
                self.selected_pokemon = poke
                return poke
        return None
