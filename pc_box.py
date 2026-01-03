"""
PC Box UI with Controller Support
Displays Pokemon PC storage with gamepad navigation
Supports Sinew cross-game storage with 120 slots per box
"""

import pygame
import ui_colors
from ui_components import Button
from pygame.locals import *
import os
from save_data_manager import get_manager
from gif_sprite_handler import get_sprite_cache

# Try to import achievements
try:
    from achievements import get_achievement_manager, get_achievement_notification
    ACHIEVEMENTS_AVAILABLE = True
except ImportError:
    get_achievement_manager = None
    get_achievement_notification = None
    ACHIEVEMENTS_AVAILABLE = False
    print("[PCBox] achievements not available")

# Try to import Sinew storage
try:
    from sinew_storage import get_sinew_storage
    SINEW_STORAGE_AVAILABLE = True
except ImportError:
    get_sinew_storage = None
    SINEW_STORAGE_AVAILABLE = False
    print("[PCBox] sinew_storage not available")

# Try to import trade evolution system
try:
    from trade_evolution import can_evolve_by_trade, apply_evolution, evolve_raw_pokemon_bytes
    TRADE_EVOLUTION_AVAILABLE = True
except ImportError:
    can_evolve_by_trade = None
    apply_evolution = None
    evolve_raw_pokemon_bytes = None
    TRADE_EVOLUTION_AVAILABLE = False
    print("[PCBox] trade_evolution not available")

# Try to import PokemonSummary
try:
    from pokemon_summary import PokemonSummary
    SUMMARY_AVAILABLE = True
except ImportError:
    PokemonSummary = None
    SUMMARY_AVAILABLE = False
    print("[PCBox] PokemonSummary not available")
from controller import get_controller, NavigableList

# Try to import save_writer for move functionality
try:
    from save_writer import (
        load_save_file, write_save_file, write_pokemon_to_pc, 
        clear_pc_slot
    )
    SAVE_WRITER_AVAILABLE = True
except ImportError:
    SAVE_WRITER_AVAILABLE = False
    print("[PCBox] save_writer not available - move functionality disabled")

# Try to import Altering Cave data for the Echoes feature
try:
    from achievements_data import (
        ALTERING_CAVE_LOCATIONS, ALTERING_CAVE_ZUBAT_SPECIES, 
        ALTERING_CAVE_POKEMON
    )
    ALTERING_CAVE_AVAILABLE = True
except ImportError:
    ALTERING_CAVE_LOCATIONS = (183, 210)
    ALTERING_CAVE_ZUBAT_SPECIES = 41
    ALTERING_CAVE_POKEMON = []
    ALTERING_CAVE_AVAILABLE = False
    print("[PCBox] Altering Cave data not available - using defaults")


class PCBox:
    def __init__(self, width, height, font, close_callback,
                 prev_game_callback=None, next_game_callback=None,
                 get_current_game_callback=None,
                 party_slot_scale=1.0, party_slot_x_offset=0,
                 is_game_running_callback=None,
                 reload_save_callback=None,
                 resume_game_callback=None):
        self.width = width
        self.height = height
        self.font = font
        self.close_callback = close_callback
        self.prev_game_callback = prev_game_callback
        self.next_game_callback = next_game_callback
        self.get_current_game_callback = get_current_game_callback
        self.is_game_running_callback = is_game_running_callback
        self.reload_save_callback = reload_save_callback
        self.resume_game_callback = resume_game_callback
        self.party_slot_scale = 1.2
        self.party_slot_x_offset = party_slot_x_offset
        
        # Load pause combo setting
        self._pause_combo_setting = self._load_pause_combo_setting()

        self.box_index = 0  # 0-13 for boxes 1-14 (or 0-19 for Sinew)
        self.selected_pokemon = None
        self.sub_modal = None  # For summary screen
        self.current_sprite_image = None
        self.current_gif_sprite = None  # For animated showdown sprites
        
        # Get save data manager
        self.manager = get_manager()
        
        # Get Sinew storage (cross-game storage)
        self.sinew_storage = get_sinew_storage() if SINEW_STORAGE_AVAILABLE else None
        
        # Check if we're on Sinew (cross-game mode)
        self.sinew_mode = self._is_sinew_mode()
        
        # Sinew mode has 120 slots per box with scrolling
        self.sinew_scroll_offset = 0  # Scroll offset for Sinew's 120-slot boxes
        self.sinew_visible_rows = 5   # Number of visible rows at a time
        self.sinew_total_rows = 20    # 120 slots / 6 columns = 20 rows
        
        # Get sprite cache
        self.sprite_cache = get_sprite_cache()
        
        # Get controller
        self.controller = get_controller()
        
        # Box names - use different names for Sinew vs regular games
        if self.sinew_mode:
            self.box_names = [f"STORAGE {i+1}" for i in range(20)]
            self.max_boxes = 20
        else:
            self.box_names = [f"BOX {i+1}" for i in range(14)]
            self.max_boxes = 14
        
        # Load current box data
        self.current_box_data = []
        self.party_data = []
        self.refresh_data()

        # ------------------- Navigation State -------------------
        # Grid navigation - different for Sinew mode
        if self.sinew_mode:
            # Sinew: 6 columns x 5 visible rows = 30 visible slots (of 120 total)
            self.grid_nav = NavigableList(30, columns=6, wrap=False)
        else:
            # Regular: 6 columns x 5 rows = 30 slots
            self.grid_nav = NavigableList(30, columns=6, wrap=False)
        self.grid_selected = 0  # Currently selected grid slot
        
        # Party navigation (6 slots)
        self.party_nav = NavigableList(6, columns=2, wrap=True)
        self.party_selected = 0
        
        # Focus state: 'grid', 'party', 'game_button', 'box_button', 'side_buttons', 'undo_button'
        self.focus_mode = 'grid'
        
        # Side button navigation (Party, Close)
        self.side_button_index = 0  # 0 = Party, 1 = Close

        # ------------------- Options Menu State -------------------
        self.options_menu_open = False
        self.options_menu_items = ['MOVE', 'SUMMARY', 'RELEASE', 'CANCEL']
        self.options_menu_selected = 0
        
        # ------------------- Move Mode State -------------------
        self.move_mode = False  # True when holding a Pokemon to move
        self.moving_pokemon = None  # Pokemon data being moved
        self.moving_pokemon_source = None  # {'type': 'box'/'party', 'box': int, 'slot': int, 'game': str}
        self.moving_sprite = None  # Sprite surface for the Pokemon being moved
        
        # ------------------- Confirmation Dialog State -------------------
        self.confirmation_dialog_open = False
        self.confirmation_dialog_message = ""
        self.confirmation_dialog_callback = None
        self.confirmation_selected = 0  # 0 = Yes, 1 = No
        
        # ------------------- Evolution Dialog State -------------------
        self.evolution_dialog_open = False
        self.evolution_dialog_pokemon = None  # Pokemon that can evolve
        self.evolution_dialog_info = None  # Evolution info from can_evolve_by_trade
        self.evolution_dialog_location = None  # (box, slot) in Sinew storage
        self.evolution_selected = 0  # 0 = Evolve, 1 = Stop
        
        # ------------------- Altering Cave "Echoes" Feature -------------------
        # When a Zubat caught in Altering Cave is clicked, show special dialog
        self.altering_cave_dialog_open = False
        self.altering_cave_zubat = None  # The Zubat pokemon data
        self.altering_cave_location = None  # (box, slot) or (save_path, box, slot)
        self.altering_cave_selected = 0  # 0 = Yes, 1 = No
        
        # Slot machine state for Altering Cave reward
        self.altering_cave_spinner_active = False
        self.altering_cave_spinner_speed = 0  # Current spin speed
        self.altering_cave_spinner_offset = 0.0  # Vertical offset for animation
        self.altering_cave_spinner_result = None  # The Pokemon that was selected
        self.altering_cave_spinner_stopped = False
        self.altering_cave_spinner_show_result = False
        self.altering_cave_result_timer = 0
        self.altering_cave_target_offset = 0  # Target offset to land on result
        self.altering_cave_remaining = []  # Cached list of remaining Pokemon
        
        # Pulse animation for Altering Cave Zubats
        self._altering_cave_pulse_timer = 0
        
        # ------------------- Warning Message State -------------------
        self.warning_message = None
        
        # ------------------- Undo State -------------------
        self.undo_available = False
        self.undo_action = None  # {'type': 'move'/'release', 'data': {...}}
        self.warning_message_timer = 0
        self.warning_message_duration = 120  # frames (2 seconds at 60fps)

        # ------------------- Sprite Area -------------------
        self.sprite_area = pygame.Rect(
            0.02 * width, 0.03 * height, 0.28 * width, 0.45 * height
        )

        # ------------------- Top Buttons -------------------
        self.party_button = Button("Party", rel_rect=(0.02, 0.69, 0.26, 0.09),
                                   callback=self.toggle_party_panel)
        self.close_button = Button("Close", rel_rect=(0.02, 0.79, 0.26, 0.09),
                                   callback=self.close_callback)
        
        # Undo button rect - set dynamically during draw when undo is available
        self.undo_button_rect = None

        self.left_game_arrow = Button("<", rel_rect=(0.31, 0.02, 0.04, 0.09),
                                      callback=lambda: self.change_game(-1))
        self.game_button = Button(self.get_current_game(), rel_rect=(0.36, 0.02, 0.50, 0.09),
                                  callback=lambda: print(f"Current game: {self.get_current_game()}"))
        self.right_game_arrow = Button(">", rel_rect=(0.87, 0.02, 0.04, 0.09),
                                       callback=lambda: self.change_game(1))

        self.left_box_arrow = Button("<", rel_rect=(0.31, 0.12, 0.04, 0.09), callback=self.prev_box)
        self.box_button = Button(self.get_box_name(self.box_index), rel_rect=(0.36, 0.12, 0.50, 0.09),
                                 callback=lambda: print(f"Box {self.box_index+1} clicked"))
        self.right_box_arrow = Button(">", rel_rect=(0.87, 0.12, 0.04, 0.09), callback=self.next_box)

        # ------------------- Info Area -------------------
        self.info_area = pygame.Rect(
            self.sprite_area.x,
            self.party_button.rect.y - 0.27 * height,
            self.sprite_area.width,
            0.25 * height
        )

        # ------------------- Grid -------------------
        self.grid_cols = 6
        self.grid_rows = 5
        self.grid_rect = pygame.Rect(
            self.sprite_area.right + 0.02 * width,
            0.28 * height,
            width - (self.sprite_area.right + 0.04 * width),
            0.65 * height
        )

        # ------------------- Party Panel -------------------
        self.party_panel_open = False
        self.party_panel_target_y = 0
        self.party_panel_rect = pygame.Rect(
            self.sprite_area.right,  # start at sprite area right
            -height,                 # start off-screen
            (width - self.sprite_area.right) * 0.55,  # half of remaining screen
            height
        )
        self.party_panel_speed = 15

    # ------------------- Controller Support -------------------
    
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
            if hasattr(self.sub_modal, 'handle_controller'):
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
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
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
                if not getattr(self, '_resume_combo_triggered', False):
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
        if ctrl.is_button_just_pressed('L'):
            ctrl.consume_button('L')
            self.prev_box()
            return True
        
        if ctrl.is_button_just_pressed('R'):
            ctrl.consume_button('R')
            self.next_box()
            return True
        
        # Handle based on current focus mode
        if self.party_panel_open:
            consumed = self._handle_party_controller(ctrl)
        elif self.focus_mode == 'grid':
            consumed = self._handle_grid_controller(ctrl)
        elif self.focus_mode == 'game_button':
            consumed = self._handle_game_button_controller(ctrl)
        elif self.focus_mode == 'box_button':
            consumed = self._handle_box_button_controller(ctrl)
        elif self.focus_mode == 'side_buttons':
            consumed = self._handle_side_buttons_controller(ctrl)
        elif self.focus_mode == 'undo_button':
            # Safety check: if undo is no longer available, redirect to grid
            if not self.undo_available:
                self.focus_mode = 'grid'
                consumed = self._handle_grid_controller(ctrl)
            else:
                consumed = self._handle_undo_button_controller(ctrl)
        
        return consumed
    
    def _handle_options_menu_controller(self, ctrl):
        """Handle controller input for options menu"""
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            self.options_menu_selected = (self.options_menu_selected - 1) % len(self.options_menu_items)
            return True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            self.options_menu_selected = (self.options_menu_selected + 1) % len(self.options_menu_items)
            return True
        
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            selected_option = self.options_menu_items[self.options_menu_selected]
            self._execute_options_menu(selected_option)
            return True
        
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            self.options_menu_open = False
            return True
        
        return True
    
    def _handle_confirmation_controller(self, ctrl):
        """Handle controller input for confirmation dialog"""
        if ctrl.is_dpad_just_pressed('left') or ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('left')
            ctrl.consume_dpad('right')
            self.confirmation_selected = 1 - self.confirmation_selected  # Toggle 0/1
            return True
        
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if self.confirmation_selected == 0:  # Yes
                if self.confirmation_dialog_callback:
                    self.confirmation_dialog_callback()
            self.confirmation_dialog_open = False
            self.confirmation_dialog_callback = None
            return True
        
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            self.confirmation_dialog_open = False
            self.confirmation_dialog_callback = None
            return True
        
        return True
    
    def _handle_grid_controller(self, ctrl):
        """Handle controller input when grid is focused"""
        consumed = False
        current_idx = self.grid_nav.get_selected()
        current_col = current_idx % 6
        current_row = current_idx // 6
        
        # D-pad navigation
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            if current_row == 0:
                # At top row
                if self.sinew_mode and self.sinew_scroll_offset > 0:
                    # Scroll up in Sinew mode
                    self.scroll_sinew_up()
                else:
                    # Move to box button
                    self.focus_mode = 'box_button'
            else:
                self.grid_nav.navigate('up')
                self._update_grid_selection()
            consumed = True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            if current_row < 4:  # Not at bottom row
                self.grid_nav.navigate('down')
                self._update_grid_selection()
            elif self.sinew_mode:
                # At bottom row in Sinew mode - try to scroll down
                self.scroll_sinew_down()
            consumed = True
        
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            if current_col == 0:
                # At left edge - move to undo button if available, else side buttons
                if self.undo_available:
                    self.focus_mode = 'undo_button'
                else:
                    self.focus_mode = 'side_buttons'
                    if self.sinew_mode:
                        self.side_button_index = 1  # Close
                    else:
                        self.side_button_index = 0  # Party
            else:
                self.grid_nav.navigate('left')
                self._update_grid_selection()
            consumed = True
        
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            if current_col < 5:  # Not at right edge
                self.grid_nav.navigate('right')
                self._update_grid_selection()
            consumed = True
        
        # L/R buttons for fast scrolling in Sinew mode
        if self.sinew_mode:
            if ctrl.is_button_just_pressed('L'):
                ctrl.consume_button('L')
                # Scroll up 5 rows
                for _ in range(5):
                    if not self.scroll_sinew_up():
                        break
                consumed = True
            
            if ctrl.is_button_just_pressed('R'):
                ctrl.consume_button('R')
                # Scroll down 5 rows
                for _ in range(5):
                    if not self.scroll_sinew_down():
                        break
                consumed = True
        
        # A button selects Pokemon
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            self._select_grid_pokemon()
            consumed = True
        
        # SELECT button in dev mode: export Pokemon
        if ctrl.is_button_just_pressed('SELECT'):
            ctrl.consume_button('SELECT')
            # Check for dev mode
            import builtins
            dev_mode = getattr(builtins, 'SINEW_DEV_MODE', False)
            print(f"[PCBox] SELECT pressed - dev_mode={dev_mode}, selected={self.selected_pokemon is not None}")
            if dev_mode and self.selected_pokemon:
                self._export_pokemon_for_achievement()
            elif not self.sinew_mode:
                self.toggle_party_panel()
            consumed = True
        
        # START button opens party panel (only for non-Sinew mode)
        if ctrl.is_button_just_pressed('START'):
            ctrl.consume_button('START')
            if not self.sinew_mode:  # Sinew has no party
                self.toggle_party_panel()
            consumed = True
        
        return consumed
    
    def _handle_game_button_controller(self, ctrl):
        """Handle controller when game button is focused"""
        consumed = False
        
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            # Stay on game button (nothing above)
            consumed = True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            # Move to box button
            self.focus_mode = 'box_button'
            consumed = True
        
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            # Change to previous game
            self.change_game(-1)
            consumed = True
        
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            # Change to next game
            self.change_game(1)
            consumed = True
        
        # A button does nothing special on game button
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            consumed = True
        
        return consumed
    
    def _handle_box_button_controller(self, ctrl):
        """Handle controller when box button is focused"""
        consumed = False
        
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            # Move to game button
            self.focus_mode = 'game_button'
            consumed = True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            # Move to grid (top row)
            self.focus_mode = 'grid'
            # Set grid selection to top row, middle-ish
            self.grid_nav.set_selected(2)  # Column 2 of row 0
            self._update_grid_selection()
            consumed = True
        
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            # Change to previous box
            self.prev_box()
            consumed = True
        
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            # Change to next box
            self.next_box()
            consumed = True
        
        # A button does nothing special on box button
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            consumed = True
        
        return consumed
    
    def _handle_side_buttons_controller(self, ctrl):
        """Handle controller when side buttons (Party/Close) are focused"""
        consumed = False
        
        # Button indices: 0 = Party, 1 = Close
        min_button = 1 if self.sinew_mode else 0
        max_button = 1
        
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            if self.side_button_index > min_button:
                self.side_button_index -= 1
            consumed = True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            if self.side_button_index < max_button:
                self.side_button_index += 1
            consumed = True
        
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            # Stay on side buttons (nothing to the left)
            consumed = True
        
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            # Move to undo button if available, otherwise to grid
            if self.undo_available:
                self.focus_mode = 'undo_button'
            else:
                self.focus_mode = 'grid'
                current_grid = self.grid_nav.get_selected()
                new_row = min(2, current_grid // 6)
                self.grid_nav.set_selected(new_row * 6)
                self._update_grid_selection()
            consumed = True
        
        # A button activates the selected button
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if self.side_button_index == 0 and not self.sinew_mode:
                self.toggle_party_panel()
            elif self.side_button_index == 1:
                self.close_callback()
            consumed = True
        
        return consumed
    
    def _handle_undo_button_controller(self, ctrl):
        """Handle controller when undo button is focused"""
        consumed = False
        
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            # Move to side buttons
            self.focus_mode = 'side_buttons'
            self.side_button_index = 1 if self.sinew_mode else 0
            consumed = True
        
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            # Move to grid
            self.focus_mode = 'grid'
            current_grid = self.grid_nav.get_selected()
            new_row = min(2, current_grid // 6)
            self.grid_nav.set_selected(new_row * 6)
            self._update_grid_selection()
            consumed = True
        
        if ctrl.is_dpad_just_pressed('up') or ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('up')
            ctrl.consume_dpad('down')
            # No vertical movement on undo button
            consumed = True
        
        # A button executes undo
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            self._execute_undo()
            # After undo, button disappears - move to grid
            if not self.undo_available:
                self.focus_mode = 'grid'
            consumed = True
        
        # B button goes back to grid
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            self.focus_mode = 'grid'
            consumed = True
        
        return consumed
    
    def _handle_party_controller(self, ctrl):
        """Handle controller input when party panel is focused"""
        consumed = False
        
        # D-pad navigation for party slots
        # Layout: 1 big slot on left, 5 smaller slots on right
        # We'll treat it as a 2-column grid
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            if self.party_selected > 0:
                if self.party_selected == 1:
                    # From first right slot to left slot
                    self.party_selected = 0
                elif self.party_selected > 1:
                    # Move up in right column
                    self.party_selected -= 1
                self._update_party_selection()
            consumed = True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            if self.party_selected == 0:
                # From left slot to first right slot
                self.party_selected = 1
            elif self.party_selected < 5:
                self.party_selected += 1
            self._update_party_selection()
            consumed = True
        
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            if self.party_selected > 0:
                self.party_selected = 0
                self._update_party_selection()
            consumed = True
        
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            if self.party_selected == 0:
                # From left slot to right column
                self.party_selected = 1
                self._update_party_selection()
            else:
                # Already in right column - close party panel and go to grid
                self.toggle_party_panel()
                self.focus = 'grid'
            consumed = True
        
        # A button selects party Pokemon
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            self._select_party_pokemon()
            consumed = True
        
        # SELECT button in dev mode: export Pokemon
        if ctrl.is_button_just_pressed('SELECT'):
            ctrl.consume_button('SELECT')
            import builtins
            if getattr(builtins, 'SINEW_DEV_MODE', False) and self.selected_pokemon:
                self._export_pokemon_for_achievement()
            consumed = True
        
        return consumed
    
    def _update_grid_selection(self):
        """Update selected Pokemon based on grid navigation"""
        grid_index = self.grid_nav.get_selected()
        poke = self.get_pokemon_at_grid_slot(grid_index)
        if poke and not poke.get('empty'):
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
            self._attempt_place_pokemon('box', self.box_index + 1, grid_index)
        elif poke and not poke.get('empty'):
            self.selected_pokemon = poke
            
            # Check for Altering Cave Zubat (special interaction)
            is_ac_zubat = self._is_altering_cave_zubat(poke)
            
            if is_ac_zubat:
                # Determine location info for this Pokemon
                if self.is_sinew_storage():
                    # Sinew storage: (box, slot) - need actual slot index accounting for scroll
                    actual_slot = grid_index + (self.sinew_scroll_offset * 6)
                    location = (self.box_index, actual_slot)
                    print(f"[PCBox] AC Zubat location (Sinew): box_index={self.box_index}, actual_slot={actual_slot}")
                else:
                    # Game save: (save_path, box, slot)
                    save_path = self._get_current_save_path()
                    location = (save_path, self.box_index, grid_index)
                    print(f"[PCBox] AC Zubat location (Game): box_index={self.box_index}, grid_index={grid_index}")
                
                self._show_altering_cave_dialog(poke, location)
                return
            
            # Open options menu for this Pokemon
            if self.undo_available:
                self.options_menu_items = ['MOVE', 'SUMMARY', 'RELEASE', 'UNDO', 'CANCEL']
            else:
                self.options_menu_items = ['MOVE', 'SUMMARY', 'RELEASE', 'CANCEL']
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
            elif poke and not poke.get('empty'):
                self.selected_pokemon = poke
                
                # Check for Altering Cave Zubat (special interaction)
                # Note: Party Pokemon can't be exchanged since they're in active use
                # Just show normal options for party
                
                # Open options menu for this Pokemon (no RELEASE for party)
                if self.undo_available:
                    self.options_menu_items = ['MOVE', 'SUMMARY', 'UNDO', 'CANCEL']
                else:
                    self.options_menu_items = ['MOVE', 'SUMMARY', 'CANCEL']
                self.options_menu_open = True
                self.options_menu_selected = 0
                print(f"Options for party: {self.manager.format_pokemon_display(poke)}")

    # ------------------- Options Menu -------------------
    
    def _execute_options_menu(self, option):
        """Execute the selected option from options menu"""
        self.options_menu_open = False
        
        if option == 'MOVE':
            self._start_move_mode()
        elif option == 'SUMMARY':
            self._open_summary()
        elif option == 'RELEASE':
            self._confirm_release_pokemon()
        elif option == 'UNDO':
            self._execute_undo()
        elif option == 'CANCEL':
            pass  # Just close menu
    
    def _open_summary(self):
        """Open Pokemon summary screen"""
        if self.selected_pokemon and SUMMARY_AVAILABLE and PokemonSummary:
            def close_summary():
                self.sub_modal = None
            
            # Determine game type from current game name
            game_name = self.get_current_game() if self.get_current_game_callback else "Emerald"
            if game_name in ('FireRed', 'LeafGreen'):
                game_type = 'FRLG'
            else:
                game_type = 'RSE'
            
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
                next_pokemon_callback=next_callback
            )
            print(f"[PCBox] Opening summary for: {self.selected_pokemon.get('nickname', 'Pokemon')}")
        elif self.selected_pokemon:
            print(f"[PCBox] Summary not available for: {self.selected_pokemon.get('nickname', 'Pokemon')}")
    
    def _confirm_release_pokemon(self):
        """Show confirmation dialog before releasing Pokemon"""
        if not self.selected_pokemon:
            return
        
        pokemon_name = self.selected_pokemon.get('nickname') or self.selected_pokemon.get('species_name', 'Pokemon')
        
        # Store the release target info
        if self.party_panel_open:
            self._release_target = {
                'type': 'party',
                'slot': self.party_selected
            }
        else:
            self._release_target = {
                'type': 'sinew' if self.sinew_mode else 'box',
                'box': self.box_index + 1,
                'slot': self.grid_nav.get_selected()
            }
        
        # Show confirmation dialog
        self.confirmation_dialog_open = True
        self.confirmation_dialog_message = f"Release {pokemon_name}?\nThis cannot be undone!"
        self.confirmation_dialog_callback = self._do_release_pokemon
        self.confirmation_selected = 1  # Default to No for safety
    
    def _do_release_pokemon(self):
        """Actually release the Pokemon after confirmation"""
        if not hasattr(self, '_release_target') or not self._release_target:
            print("[PCBox] No release target set")
            return
        
        target = self._release_target
        self._release_target = None
        
        try:
            if target['type'] == 'party':
                # Cannot release from party in PC box screen
                print("[PCBox] Cannot release party Pokemon from PC screen")
                self._show_warning("Cannot release party Pokemon here")
                return
            
            elif target['type'] == 'sinew':
                # Release from Sinew storage
                if self.sinew_storage:
                    box_num = target['box']
                    slot_idx = target['slot']
                    
                    # Adjust for scrolling
                    if self.sinew_scroll_offset > 0:
                        adjusted_slot = slot_idx + (self.sinew_scroll_offset * 6)
                    else:
                        adjusted_slot = slot_idx
                    
                    # Store for undo BEFORE clearing
                    released_pokemon = self.selected_pokemon.copy() if self.selected_pokemon else None
                    if released_pokemon:
                        self.undo_action = {
                            'type': 'release',
                            'pokemon_data': released_pokemon,
                            'location': {
                                'type': 'sinew',
                                'box': box_num,
                                'slot': adjusted_slot
                            }
                        }
                        self.undo_available = True
                    
                    self.sinew_storage.clear_slot(box_num, adjusted_slot)
                    print(f"[PCBox] Released Pokemon from Sinew Box {box_num}, Slot {adjusted_slot + 1}")
                    
                    # Refresh display
                    self._refresh_current_box()
                    self.selected_pokemon = None
                else:
                    print("[PCBox] Sinew storage not available")
            
            elif target['type'] == 'box':
                # Release from game PC box
                try:
                    from save_writer import clear_pc_slot, write_save_file
                    
                    game_name = self.get_current_game() if self.get_current_game_callback else None
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
                    if game_name in ('FireRed', 'LeafGreen'):
                        game_type = 'FRLG'
                    else:
                        game_type = 'RSE'
                    
                    box_num = target['box']
                    slot_idx = target['slot']
                    
                    # Store for undo BEFORE clearing
                    released_pokemon = self.selected_pokemon.copy() if self.selected_pokemon else None
                    if released_pokemon:
                        self.undo_action = {
                            'type': 'release',
                            'pokemon_data': released_pokemon,
                            'location': {
                                'type': 'box',
                                'box': box_num,
                                'slot': slot_idx,
                                'game': game_name,
                                'save_path': save_path
                            }
                        }
                        self.undo_available = True
                    
                    # Clear the slot
                    success = clear_pc_slot(save_data, box_num, slot_idx, game_type)
                    
                    if success:
                        # Save the changes using write_save_file
                        write_save_file(save_path, save_data, create_backup_first=True)
                        # Reload the save to refresh cache
                        self.manager.reload()
                        print(f"[PCBox] Released Pokemon from Box {box_num}, Slot {slot_idx + 1}")
                        
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
        action_type = action.get('type')
        
        # Import save_writer functions at top level for all branches
        from save_writer import write_pokemon_to_pc, write_save_file, clear_pc_slot
        
        try:
            if action_type == 'release':
                # Undo release - restore the Pokemon
                pokemon_data = action.get('pokemon_data')
                location = action.get('location')  # {'type': 'sinew'/'box', 'box': int, 'slot': int}
                
                if location['type'] == 'sinew' and self.sinew_storage:
                    self.sinew_storage.set_pokemon_at(location['box'], location['slot'], pokemon_data)
                    self._show_warning("Undo: Pokemon restored!")
                    self._refresh_current_box()
                elif location['type'] == 'box':
                    # Restore to game PC
                    save_path = location.get('save_path')
                    raw_bytes = pokemon_data.get('raw_bytes')
                    
                    if save_path and raw_bytes:
                        save_data = load_save_file(save_path)
                        game_type = 'FRLG' if location.get('game') in ('FireRed', 'LeafGreen') else 'RSE'
                        write_pokemon_to_pc(save_data, location['box'], location['slot'], raw_bytes, game_type)
                        write_save_file(save_path, save_data, create_backup_first=True)
                        
                        # Reload manager
                        if self.manager:
                            self.manager.reload()
                        
                        self._show_warning("Undo: Pokemon restored!")
                        self._refresh_current_box()
                
                print(f"[PCBox] Undo release successful")
                
            elif action_type == 'move':
                move_type = action.get('move_type')
                pokemon = action.get('pokemon')
                source = action.get('source')
                dest = action.get('dest')
                
                if move_type == 'sinew_to_sinew':
                    # Undo Sinew internal move - swap back
                    source_pokemon = action.get('source_pokemon')
                    dest_pokemon = action.get('dest_pokemon')  # Was the pokemon that got displaced (or None)
                    
                    if self.sinew_storage:
                        # Put source pokemon back to source
                        self.sinew_storage.set_pokemon_at(source['box'], source['slot'], source_pokemon)
                        # Put dest pokemon back to dest (or clear if was empty)
                        if dest_pokemon:
                            self.sinew_storage.set_pokemon_at(dest['box'], dest['slot'], dest_pokemon)
                        else:
                            self.sinew_storage.clear_slot(dest['box'], dest['slot'])
                        
                        self._show_warning("Undo: Move reversed!")
                        self._refresh_current_box()
                        print(f"[PCBox] Undo sinew_to_sinew successful")
                
                elif move_type == 'game_to_sinew':
                    # Undo deposit: clear Sinew, restore to game save
                    raw_bytes = pokemon.get('raw_bytes')
                    
                    if self.sinew_storage and raw_bytes and source.get('save_path'):
                        # 1. Clear from Sinew
                        self.sinew_storage.clear_slot(dest['box'], dest['slot'])
                        
                        # 2. Restore to game save
                        save_path = source.get('save_path')
                        game_type = 'FRLG' if source.get('game') in ('FireRed', 'LeafGreen') else 'RSE'
                        save_data = load_save_file(save_path)
                        write_pokemon_to_pc(save_data, source['box'], source['slot'], raw_bytes, game_type)
                        write_save_file(save_path, save_data, create_backup_first=True)
                        
                        # 3. Reload manager
                        if self.manager:
                            self.manager.reload()
                        
                        self._show_warning("Undo: Move reversed!")
                        self._refresh_current_box()
                        print(f"[PCBox] Undo game_to_sinew successful")
                
                elif move_type == 'sinew_to_game':
                    # Undo withdrawal: restore to Sinew, clear from game save
                    
                    if self.sinew_storage and pokemon and dest.get('save_path'):
                        # 1. Restore to Sinew
                        self.sinew_storage.set_pokemon_at(source['box'], source['slot'], pokemon)
                        
                        # 2. Clear from game save
                        save_path = dest.get('save_path')
                        game_type = dest.get('game_type', 'RSE')
                        save_data = load_save_file(save_path)
                        clear_pc_slot(save_data, dest['box'], dest['slot'], game_type)
                        write_save_file(save_path, save_data, create_backup_first=True)
                        
                        # 3. Reload manager
                        if self.manager:
                            self.manager.reload()
                        
                        self._show_warning("Undo: Move reversed!")
                        self._refresh_current_box()
                        print(f"[PCBox] Undo sinew_to_game successful")
                
                elif move_type == 'game_to_game':
                    # Undo game-to-game transfer
                    raw_bytes = pokemon.get('raw_bytes')
                    
                    if raw_bytes and source.get('save_path') and dest.get('save_path'):
                        # 1. Clear from destination game
                        dest_save_data = load_save_file(dest['save_path'])
                        clear_pc_slot(dest_save_data, dest['box'], dest['slot'], dest.get('game_type', 'RSE'))
                        write_save_file(dest['save_path'], dest_save_data, create_backup_first=True)
                        
                        # 2. Restore to source game
                        source_save_data = load_save_file(source['save_path'])
                        write_pokemon_to_pc(source_save_data, source['box'], source['slot'], raw_bytes, source.get('game_type', 'RSE'))
                        write_save_file(source['save_path'], source_save_data, create_backup_first=True)
                        
                        # 3. Reload manager
                        if self.manager:
                            self.manager.reload()
                        
                        self._show_warning("Undo: Move reversed!")
                        self._refresh_current_box()
                        print(f"[PCBox] Undo game_to_game successful")
            
            # Clear undo state after successful undo
            self.undo_available = False
            self.undo_action = None
            
        except Exception as e:
            print(f"[PCBox] Undo failed: {e}")
            import traceback
            traceback.print_exc()
            self._show_warning(f"Undo failed!")
    
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
            if poke and not poke.get('empty'):
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
            if poke and not poke.get('empty'):
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
            poke = self.current_box_data[idx] if idx < len(self.current_box_data) else None
            if poke and not poke.get('empty'):
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
            poke = self.current_box_data[idx] if idx < len(self.current_box_data) else None
            if poke and not poke.get('empty'):
                self.grid_nav.selected = idx
                self.selected_pokemon = poke
                return poke
        return None

    # ------------------- Move Mode -------------------
    
    def _is_current_game_running(self):
        """Check if the currently displayed game is the one running in the emulator"""
        if self.is_game_running_callback:
            running_game = self.is_game_running_callback()
            if running_game:
                current_game = self.get_current_game()
                # Compare game names (strip extension and compare)
                return running_game.lower() == current_game.lower()
        return False
    
    def _show_warning(self, message):
        """Show a warning message popup"""
        self.warning_message = message
        self.warning_message_timer = self.warning_message_duration
    
    def _track_sinew_achievement(self, deposit=False, transfer=False, is_shiny=False):
        """Track Sinew-related achievement progress"""
        if not ACHIEVEMENTS_AVAILABLE or not get_achievement_manager:
            return
        
        try:
            manager = get_achievement_manager()
            
            # Update stats
            if deposit:
                manager.increment_stat("sinew_deposits", 1)
            if transfer:
                manager.increment_stat("sinew_transfers", 1)
            if is_shiny:
                manager.increment_stat("sinew_shinies", 1)
            
            # Get current counts for checking
            total_pokemon = 0
            total_shinies = 0
            
            if self.sinew_storage:
                total_pokemon = self.sinew_storage.get_total_pokemon_count()
                # Count shinies in storage
                for box_num in range(1, 21):  # 20 boxes
                    box_data = self.sinew_storage.get_box(box_num)
                    if box_data:
                        for poke in box_data:
                            if poke and not poke.get('empty') and poke.get('is_shiny'):
                                total_shinies += 1
            
            transfer_count = manager.get_stat("sinew_transfers", 0)
            
            # Check for Sinew storage achievements (Dirty Dex is checked separately via combined pokedex)
            newly_unlocked = manager.check_sinew_achievements(
                sinew_storage_count=total_pokemon,
                transfer_count=transfer_count,
                shiny_count=total_shinies
            )
            
            if newly_unlocked:
                print(f"[PCBox] Unlocked {len(newly_unlocked)} Sinew achievements!")
                
        except Exception as e:
            print(f"[PCBox] Achievement tracking error: {e}")
    
    def _export_pokemon_for_achievement(self):
        """Export the selected Pokemon as a .pks file for achievement rewards (DEV MODE ONLY)"""
        import sys
        
        print(f"[PCBox] *** DEV: Export triggered ***", file=sys.stderr, flush=True)
        
        if not self.selected_pokemon:
            print(f"[PCBox] *** DEV: No Pokemon selected! ***", file=sys.stderr, flush=True)
            self._show_warning("No Pokemon selected!")
            return
        
        pokemon = self.selected_pokemon
        print(f"[PCBox] *** DEV: Exporting {pokemon.get('species_name', 'Unknown')} ***", file=sys.stderr, flush=True)
        
        # Check for raw bytes - this is essential for .pks export
        raw_bytes = pokemon.get('raw_bytes')
        if not raw_bytes:
            print(f"[PCBox] *** DEV: No raw bytes available - cannot export! ***", file=sys.stderr, flush=True)
            self._show_warning("No raw bytes!\nCannot export")
            return
        
        # Convert to bytes if needed
        if isinstance(raw_bytes, list):
            raw_bytes = bytes(raw_bytes)
        elif isinstance(raw_bytes, bytearray):
            raw_bytes = bytes(raw_bytes)
        
        if len(raw_bytes) < 80:
            print(f"[PCBox] *** DEV: Raw bytes too short ({len(raw_bytes)} bytes) ***", file=sys.stderr, flush=True)
            self._show_warning(f"Invalid data!\nOnly {len(raw_bytes)} bytes")
            return
        
        # Get Pokemon name for filename
        species_name = pokemon.get('species_name', 'Unknown')
        
        # Clean name for filename (remove special chars)
        safe_name = ''.join(c for c in species_name if c.isalnum() or c in ' _-').strip()
        if not safe_name:
            safe_name = f"Pokemon_{pokemon.get('species', 0)}"
        
        # Create rewards directory - use path relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        rewards_dir = os.path.join(script_dir, "data", "achievements", "rewards")
        print(f"[PCBox] *** DEV: Rewards dir: {rewards_dir} ***", file=sys.stderr, flush=True)
        
        try:
            os.makedirs(rewards_dir, exist_ok=True)
            print(f"[PCBox] *** DEV: Directory created/exists ***", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[PCBox] *** DEV: Failed to create dir: {e} ***", file=sys.stderr, flush=True)
            self._show_warning(f"Dir create failed!\n{str(e)[:20]}")
            return
        
        # Generate unique filename
        base_filename = f"{safe_name}.pks"
        filepath = os.path.join(rewards_dir, base_filename)
        
        # If file exists, add a number
        counter = 1
        while os.path.exists(filepath):
            base_filename = f"{safe_name}_{counter}.pks"
            filepath = os.path.join(rewards_dir, base_filename)
            counter += 1
        
        print(f"[PCBox] *** DEV: Writing to {filepath} ***", file=sys.stderr, flush=True)
        
        try:
            # Write raw bytes directly (80 bytes for PC Pokemon, 100 for party)
            # Use first 80 bytes for .pks format
            pks_data = raw_bytes[:80]
            
            with open(filepath, 'wb') as f:
                f.write(pks_data)
            
            print(f"[PCBox] *** DEV: SUCCESS! Exported {len(pks_data)} bytes to {filepath} ***", file=sys.stderr, flush=True)
            self._show_warning(f"Exported!\n{base_filename}")
            
        except Exception as e:
            print(f"[PCBox] *** DEV: Export failed: {e} ***", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            self._show_warning(f"Export failed!\n{str(e)[:20]}")
    
    def _show_evolution_dialog(self, pokemon_data, evolution_info, box, slot):
        """Show the trade evolution dialog for Sinew storage"""
        self.evolution_dialog_open = True
        self.evolution_dialog_pokemon = pokemon_data
        self.evolution_dialog_info = evolution_info
        self.evolution_dialog_location = (box, slot)
        self.evolution_dialog_save_path = None  # None = Sinew storage
        self.evolution_dialog_game = 'Sinew'
        self.evolution_selected = 0  # Default to "Evolve"
    
    def _show_evolution_dialog_game(self, pokemon_data, evolution_info, box, slot, save_path, game_name):
        """Show the trade evolution dialog for game save"""
        self.evolution_dialog_open = True
        self.evolution_dialog_pokemon = pokemon_data
        self.evolution_dialog_info = evolution_info
        self.evolution_dialog_location = (box, slot)
        self.evolution_dialog_save_path = save_path  # Path to game save
        self.evolution_dialog_game = game_name
        self.evolution_selected = 0  # Default to "Evolve"
    
    def _handle_evolution_controller(self, ctrl):
        """Handle controller input for evolution dialog"""
        if ctrl.is_dpad_just_pressed('left') or ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('left')
            ctrl.consume_dpad('right')
            self.evolution_selected = 1 - self.evolution_selected  # Toggle 0/1
            return True
        
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if self.evolution_selected == 0:  # Evolve
                self._execute_evolution()
            self.evolution_dialog_open = False
            return True
        
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            # B cancels evolution (same as selecting "Stop")
            self.evolution_dialog_open = False
            return True
        
        return True
    
    def _handle_altering_cave_controller(self, ctrl):
        """Handle controller input for Altering Cave dialog/spinner"""
        # Update spinner animation
        if self.altering_cave_spinner_active:
            self._update_altering_cave_spinner(16)  # Assume ~16ms per frame
            
            if self.altering_cave_spinner_show_result:
                # Waiting for A button to confirm result
                if ctrl.is_button_just_pressed('A'):
                    ctrl.consume_button('A')
                    self._complete_altering_cave_exchange()
                    return True
            
            # Can't cancel spinner once started
            return True
        
        # Dialog navigation (Yes/No)
        if ctrl.is_dpad_just_pressed('left') or ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('left')
            ctrl.consume_dpad('right')
            self.altering_cave_selected = 1 - self.altering_cave_selected  # Toggle 0/1
            return True
        
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if self.altering_cave_selected == 0:  # Yes - start spinner
                self._start_altering_cave_spinner()
            else:  # No - close dialog
                self._close_altering_cave_dialog()
            return True
        
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            # B cancels (same as No)
            self._close_altering_cave_dialog()
            return True
        
        return True
    
    def _execute_evolution(self):
        """Execute the trade evolution"""
        import sys
        
        if not self.evolution_dialog_pokemon or not self.evolution_dialog_info or not self.evolution_dialog_location:
            return
        
        box, slot = self.evolution_dialog_location
        evolution_info = self.evolution_dialog_info
        save_path = getattr(self, 'evolution_dialog_save_path', None)
        
        print(f"\n[PCBox] ===== TRADE EVOLUTION =====", file=sys.stderr, flush=True)
        print(f"[PCBox] {evolution_info['from_name']} -> {evolution_info['to_name']}", file=sys.stderr, flush=True)
        
        try:
            if save_path is None:
                # Evolution in Sinew storage
                self._execute_sinew_evolution(box, slot, evolution_info)
            else:
                # Evolution in game save
                self._execute_game_evolution(box, slot, save_path, evolution_info)
            
            print(f"[PCBox] Evolution complete!", file=sys.stderr, flush=True)
            print(f"[PCBox] ===== EVOLUTION DONE =====\n", file=sys.stderr, flush=True)
            
            # Track evolution for achievements
            try:
                from achievements import get_achievement_manager
                manager = get_achievement_manager()
                if manager:
                    manager.increment_stat("sinew_evolutions", 1)
                    evolutions = manager.get_stat("sinew_evolutions", 0)
                    print(f"[PCBox] Sinew evolutions: {evolutions}")
                    
                    # Check for evolution achievements
                    manager.check_sinew_achievements(evolution_count=evolutions)
            except Exception as e:
                print(f"[PCBox] Evolution tracking error: {e}")
            
            # Refresh display
            self.refresh_data()
            
        except Exception as e:
            print(f"[PCBox] Evolution FAILED: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            self._show_warning(f"Evolution failed!\n{str(e)[:30]}")
    
    def _execute_sinew_evolution(self, box, slot, evolution_info):
        """Execute evolution for Pokemon in Sinew storage"""
        # Get the Pokemon from storage
        pokemon = self.sinew_storage.get_pokemon_at(box, slot)
        if not pokemon:
            raise ValueError("Pokemon not found in storage")
        
        # Check if nickname should be updated (nickname == old species name)
        current_nickname = pokemon.get('nickname', '')
        old_species_name = evolution_info.get('from_name', '')
        new_species_name = evolution_info.get('to_name', '')
        
        # Determine if nickname is default (matches species name)
        nickname_is_default = (
            not current_nickname or 
            current_nickname.upper() == old_species_name.upper() or
            current_nickname.upper().strip() == old_species_name.upper().strip()
        )
        
        # Apply evolution
        if apply_evolution:
            pokemon = apply_evolution(pokemon, evolution_info)
        else:
            # Manual evolution if apply_evolution not available
            pokemon['species'] = evolution_info['evolves_to']
            pokemon['species_name'] = new_species_name
            if evolution_info.get('consumes_item'):
                pokemon['held_item'] = 0
        
        # Update nickname if it was default (matched the old species name)
        if nickname_is_default and new_species_name:
            pokemon['nickname'] = new_species_name.upper()
            print(f"[PCBox] Updated Sinew Pokemon nickname to {new_species_name.upper()}")
            
            # Also update raw_bytes if present
            if pokemon.get('raw_bytes'):
                pokemon['raw_bytes'] = self._update_nickname_in_bytes(
                    pokemon['raw_bytes'], 
                    new_species_name
                )
        
        # Save back to storage
        if not self.sinew_storage.set_pokemon_at(box, slot, pokemon):
            raise ValueError("Failed to save evolved Pokemon")
    
    def _execute_game_evolution(self, box, slot, save_path, evolution_info):
        """Execute evolution for Pokemon in a game save"""
        import sys
        
        # Get the raw_bytes from the evolution dialog pokemon
        raw_bytes = self.evolution_dialog_pokemon.get('raw_bytes')
        if not raw_bytes:
            raise ValueError("No raw_bytes available for evolution")
        
        # Check if nickname should be updated (nickname == old species name)
        current_nickname = self.evolution_dialog_pokemon.get('nickname', '')
        old_species_name = evolution_info.get('from_name', '')
        new_species_name = evolution_info.get('to_name', '')
        
        # Determine if nickname is default (matches species name)
        # Compare case-insensitively since game may store names differently
        nickname_is_default = (
            not current_nickname or 
            current_nickname.upper() == old_species_name.upper() or
            current_nickname.upper().strip() == old_species_name.upper().strip()
        )
        
        # Evolve the raw Pokemon data
        if evolve_raw_pokemon_bytes:
            evolved_bytes = evolve_raw_pokemon_bytes(
                raw_bytes,
                evolution_info['evolves_to'],
                evolution_info.get('consumes_item', False)
            )
        else:
            raise ValueError("evolve_raw_pokemon_bytes not available")
        
        # Update nickname in evolved bytes if it was default
        if nickname_is_default and new_species_name:
            evolved_bytes = self._update_nickname_in_bytes(evolved_bytes, new_species_name)
            print(f"[PCBox] Updated nickname to {new_species_name}", file=sys.stderr, flush=True)
        
        # Determine game type
        game_type = 'RSE'
        if 'Fire' in save_path or 'Leaf' in save_path or 'fire' in save_path or 'leaf' in save_path:
            game_type = 'FRLG'
        
        # Load save, write evolved Pokemon, save
        save_data = load_save_file(save_path)
        write_pokemon_to_pc(save_data, box, slot, evolved_bytes, game_type)
        
        # Update Pokedex for the evolved species
        try:
            from save_writer import set_pokedex_flags_for_pokemon
            evolved_pokemon = {'species': evolution_info['evolves_to'], 'species_name': new_species_name}
            set_pokedex_flags_for_pokemon(save_data, evolved_pokemon, game_type=game_type)
            print(f"[PCBox] Updated Pokedex for evolved species #{evolution_info['evolves_to']} ({new_species_name})", file=sys.stderr, flush=True)
        except Exception as dex_err:
            print(f"[PCBox] Pokedex update for evolution skipped: {dex_err}", file=sys.stderr, flush=True)
        
        write_save_file(save_path, save_data, create_backup_first=True)
        
        print(f"[PCBox] Evolution saved to {save_path}", file=sys.stderr, flush=True)
    
    def _update_nickname_in_bytes(self, pokemon_bytes, new_nickname):
        """
        Update the nickname in Pokemon raw bytes.
        Nickname is stored at offset 0x08, 10 bytes, Gen 3 encoding.
        """
        pokemon_bytes = bytearray(pokemon_bytes)
        
        # Gen 3 character encoding (uppercase)
        GEN3_ENCODE = {
            'A': 0xBB, 'B': 0xBC, 'C': 0xBD, 'D': 0xBE, 'E': 0xBF,
            'F': 0xC0, 'G': 0xC1, 'H': 0xC2, 'I': 0xC3, 'J': 0xC4,
            'K': 0xC5, 'L': 0xC6, 'M': 0xC7, 'N': 0xC8, 'O': 0xC9,
            'P': 0xCA, 'Q': 0xCB, 'R': 0xCC, 'S': 0xCD, 'T': 0xCE,
            'U': 0xCF, 'V': 0xD0, 'W': 0xD1, 'X': 0xD2, 'Y': 0xD3,
            'Z': 0xD4, 'a': 0xD5, 'b': 0xD6, 'c': 0xD7, 'd': 0xD8,
            'e': 0xD9, 'f': 0xDA, 'g': 0xDB, 'h': 0xDC, 'i': 0xDD,
            'j': 0xDE, 'k': 0xDF, 'l': 0xE0, 'm': 0xE1, 'n': 0xE2,
            'o': 0xE3, 'p': 0xE4, 'q': 0xE5, 'r': 0xE6, 's': 0xE7,
            't': 0xE8, 'u': 0xE9, 'v': 0xEA, 'w': 0xEB, 'x': 0xEC,
            'y': 0xED, 'z': 0xEE, ' ': 0x00, '.': 0xAD, '-': 0xAE,
            '0': 0xF1, '1': 0xF2, '2': 0xF3, '3': 0xF4, '4': 0xF5,
            '5': 0xF6, '6': 0xF7, '7': 0xF8, '8': 0xF9, '9': 0xFA,
            '!': 0xAB, '?': 0xAC, '♂': 0xB5, '♀': 0xB6,
        }
        
        # Encode the new nickname (max 10 chars, uppercase for species names)
        encoded = []
        name_upper = new_nickname.upper()[:10]
        for char in name_upper:
            if char in GEN3_ENCODE:
                encoded.append(GEN3_ENCODE[char])
            else:
                encoded.append(0x00)  # Space for unknown chars
        
        # Pad with 0xFF (terminator) to fill 10 bytes
        while len(encoded) < 10:
            encoded.append(0xFF)
        
        # Write to offset 0x08 (nickname position)
        for i, byte in enumerate(encoded):
            pokemon_bytes[0x08 + i] = byte
        
        return bytes(pokemon_bytes)
    
    def _start_move_mode(self):
        """Start move mode with currently selected Pokemon"""
        if not self.selected_pokemon:
            return
        
        # Block moving eggs
        if self.selected_pokemon.get('egg'):
            self._show_warning("Cannot move eggs!")
            return
        
        # Sinew mode doesn't need save writer for internal moves
        if not self.sinew_mode and not SAVE_WRITER_AVAILABLE:
            print("Save writer not available - cannot move Pokemon")
            return
        
        # Check if current game is running - block moves from/to active game (not for Sinew)
        if not self.sinew_mode and self._is_current_game_running():
            self._show_warning("Game is running!\nStop game to move Pokemon")
            return
        
        self.move_mode = True
        self.moving_pokemon = self.selected_pokemon
        
        # Store source location with save path
        grid_index = self.grid_nav.get_selected()
        current_game = self.get_current_game()
        
        if self.sinew_mode:
            # Sinew storage - calculate actual slot with scroll offset
            actual_slot = grid_index + (self.sinew_scroll_offset * 6)
            self.moving_pokemon_source = {
                'type': 'box',
                'box': self.box_index + 1,
                'slot': actual_slot,
                'game': 'Sinew',
                'save_path': None
            }
        elif self.party_panel_open:
            # Party moves are complex - require in-game withdrawal first
            self._show_warning("Cannot move from party.\nWithdraw to PC in-game first.")
            return
        else:
            current_save_path = getattr(self.manager, 'current_save_path', None)
            self.moving_pokemon_source = {
                'type': 'box',
                'box': self.box_index + 1,
                'slot': grid_index,
                'game': current_game,
                'save_path': current_save_path
            }
        
        import sys
        pokemon_name = self.moving_pokemon.get('nickname') or 'Pokemon'
        print(f"[PCBox] Picked up {pokemon_name} from {current_game}", file=sys.stderr, flush=True)
        
        # Load sprite for the moving Pokemon
        self._load_moving_sprite()
        
        pokemon_name = self.moving_pokemon.get('nickname') or self.moving_pokemon.get('species_name', 'Pokemon')
        print(f"Move mode: Picked up {pokemon_name}")
    
    def _load_moving_sprite(self):
        """Load the sprite for the Pokemon being moved"""
        if not self.moving_pokemon:
            self.moving_sprite = None
            return
        
        # Get sprite path - use helper method that works for both game and Sinew Pokemon
        sprite_path = self._get_pokemon_sprite_path(self.moving_pokemon)
        
        if sprite_path and os.path.exists(sprite_path):
            try:
                self.moving_sprite = pygame.image.load(sprite_path).convert_alpha()
                # Scale to reasonable size for cursor
                self.moving_sprite = pygame.transform.scale(self.moving_sprite, (40, 40))
            except Exception as e:
                print(f"Failed to load moving sprite: {e}")
                self.moving_sprite = None
        else:
            self.moving_sprite = None
    
    def _get_pokemon_sprite_path(self, pokemon):
        """Get sprite path for a Pokemon (works for both game and Sinew storage Pokemon)"""
        if not pokemon or pokemon.get('empty'):
            return None
        
        # Handle eggs
        if pokemon.get('egg'):
            egg_path = "data/sprites/gen3/normal/egg.png"
            if os.path.exists(egg_path):
                return egg_path
            return None
        
        species = pokemon.get('species', 0)
        if species == 0:
            return None
        
        # Check if shiny
        shiny = self._is_pokemon_shiny(pokemon)
        
        # Format species number as 3-digit string
        species_str = str(species).zfill(3)
        
        # Build sprite path
        sprite_folder = "data/sprites/gen3/shiny" if shiny else "data/sprites/gen3/normal"
        sprite_path = f"{sprite_folder}/{species_str}.png"
        
        if os.path.exists(sprite_path):
            return sprite_path
        return None
    
    def _is_pokemon_shiny(self, pokemon):
        """Check if a Pokemon is shiny"""
        if not pokemon or pokemon.get('empty') or pokemon.get('egg'):
            return False
        
        personality = pokemon.get('personality', 0)
        ot_id = pokemon.get('ot_id', 0)
        
        if personality == 0 or ot_id == 0:
            return False
        
        # Extract trainer ID and secret ID
        tid = ot_id & 0xFFFF
        sid = (ot_id >> 16) & 0xFFFF
        
        # Extract PID high and low
        pid_low = personality & 0xFFFF
        pid_high = (personality >> 16) & 0xFFFF
        
        # Calculate shiny value
        shiny_value = tid ^ sid ^ pid_low ^ pid_high
        
        return shiny_value < 8
    
    def _cancel_move_mode(self):
        """Cancel move mode and put Pokemon back"""
        self.move_mode = False
        self.moving_pokemon = None
        self.moving_pokemon_source = None
        self.moving_sprite = None
        print("Move cancelled")
    
    def _execute_sinew_move(self, dest_type, dest_box, dest_slot):
        """Execute a move within Sinew storage"""
        import sys
        
        if not self.sinew_storage or not self.moving_pokemon:
            self._cancel_move_mode()
            return
        
        # Get source info
        source_box = self.moving_pokemon_source.get('box', 1)
        source_slot = self.moving_pokemon_source.get('slot', 0)
        
        # Calculate actual destination slot (accounting for scroll)
        actual_dest_slot = dest_slot + (self.sinew_scroll_offset * 6)
        
        # Get destination box (1-indexed)
        dest_box_num = self.box_index + 1
        
        print(f"[PCBox] Sinew move: Box {source_box} Slot {source_slot} -> Box {dest_box_num} Slot {actual_dest_slot}", 
              file=sys.stderr, flush=True)
        
        # Check if destination is empty and store for undo
        dest_poke = self.sinew_storage.get_pokemon_at(dest_box_num, actual_dest_slot)
        source_poke_copy = self.moving_pokemon.copy() if self.moving_pokemon else None
        dest_poke_copy = dest_poke.copy() if dest_poke else None
        
        if dest_poke is not None:
            # Slot occupied - swap
            print(f"[PCBox] Swapping Pokemon", file=sys.stderr, flush=True)
        
        # Perform the move
        if self.sinew_storage.move_pokemon(source_box, source_slot, dest_box_num, actual_dest_slot):
            print(f"[PCBox] Sinew move successful", file=sys.stderr, flush=True)
            
            # Store undo action
            self.undo_action = {
                'type': 'move',
                'move_type': 'sinew_to_sinew',
                'source': {'box': source_box, 'slot': source_slot},
                'dest': {'box': dest_box_num, 'slot': actual_dest_slot},
                'source_pokemon': source_poke_copy,
                'dest_pokemon': dest_poke_copy  # None if was empty, or the swapped Pokemon
            }
            self.undo_available = True
            
            self.refresh_data()
            # Track achievement progress after move
            self._track_sinew_achievement()
        else:
            print(f"[PCBox] Sinew move failed", file=sys.stderr, flush=True)
        
        self._cancel_move_mode()
    
    def _attempt_game_to_sinew_move(self, dest_type, dest_box, dest_slot):
        """Attempt to deposit Pokemon from a game save into Sinew storage"""
        import sys
        
        if not self.sinew_storage:
            self._show_warning("Sinew storage\nnot available!")
            self._cancel_move_mode()
            return
        
        # Check if source game is running
        source_game = self.moving_pokemon_source.get('game', '')
        if self.is_game_running_callback:
            running_game = self.is_game_running_callback()
            if running_game and source_game in running_game:
                self._show_warning("Source game is running!\nStop game first")
                self._cancel_move_mode()
                return
        
        # Check if we have raw_bytes
        if not self.moving_pokemon.get('raw_bytes'):
            self._show_warning("Pokemon data missing!\nCannot transfer")
            self._cancel_move_mode()
            return
        
        # Calculate actual destination slot (accounting for scroll)
        actual_dest_slot = dest_slot + (self.sinew_scroll_offset * 6)
        dest_box_num = self.box_index + 1
        
        # Check if destination slot is empty
        dest_poke = self.sinew_storage.get_pokemon_at(dest_box_num, actual_dest_slot)
        if dest_poke is not None:
            self._show_warning("Slot is occupied!\nChoose an empty slot")
            return
        
        # Show confirmation
        pokemon_name = self.moving_pokemon.get('nickname') or self.moving_pokemon.get('species_name', 'Pokemon')
        source = self.moving_pokemon_source
        
        if source['type'] == 'box':
            source_loc = f"Box {source['box']}, Slot {source['slot'] + 1}"
        else:
            source_loc = f"Party Slot {source['slot'] + 1}"
        
        message = f"Deposit {pokemon_name}\nfrom {source['game']}\n{source_loc}\nto Sinew Storage {dest_box_num}?"
        
        # Store destination info
        self.pending_move_dest = {
            'type': 'sinew',
            'box': dest_box_num,
            'slot': actual_dest_slot,
            'game': 'Sinew'
        }
        
        # Show confirmation dialog
        self.confirmation_dialog_message = message
        self.confirmation_dialog_open = True
        self.confirmation_selected = 0
        self.confirmation_dialog_callback = self._execute_game_to_sinew_move
    
    def _execute_game_to_sinew_move(self):
        """Execute the deposit from game to Sinew storage"""
        import sys
        
        if not self.moving_pokemon or not self.moving_pokemon_source or not hasattr(self, 'pending_move_dest'):
            self._cancel_move_mode()
            return
        
        source = self.moving_pokemon_source
        dest = self.pending_move_dest
        
        print(f"\n[PCBox] ===== DEPOSIT TO SINEW =====", file=sys.stderr, flush=True)
        print(f"[PCBox] From: {source['game']} {source['type']} {source.get('box', 'N/A')}, slot {source.get('slot')}", file=sys.stderr, flush=True)
        print(f"[PCBox] To: Sinew Storage {dest['box']}, slot {dest['slot']}", file=sys.stderr, flush=True)
        
        # Store for undo BEFORE making changes
        pokemon_copy = self.moving_pokemon.copy()
        
        try:
            # 1. Store Pokemon in Sinew storage (including raw_bytes for later withdrawal)
            pokemon_data = self.moving_pokemon.copy()
            
            if not self.sinew_storage.set_pokemon_at(dest['box'], dest['slot'], pokemon_data):
                raise ValueError("Failed to store in Sinew storage")
            
            print(f"[PCBox] Stored in Sinew storage", file=sys.stderr, flush=True)
            
            # 2. Clear source slot in game save
            source_save_path = source.get('save_path')
            if source_save_path and source['type'] == 'box':
                source_game_type = 'FRLG' if source['game'] and ('Fire' in source['game'] or 'Leaf' in source['game']) else 'RSE'
                source_save_data = load_save_file(source_save_path)
                clear_pc_slot(source_save_data, source['box'], source['slot'], source_game_type)
                write_save_file(source_save_path, source_save_data, create_backup_first=True)
                print(f"[PCBox] Cleared source slot in {source['game']}", file=sys.stderr, flush=True)
            
            # Store undo action
            self.undo_action = {
                'type': 'move',
                'move_type': 'game_to_sinew',
                'source': {
                    'type': source['type'],
                    'box': source.get('box'),
                    'slot': source.get('slot'),
                    'game': source.get('game'),
                    'save_path': source_save_path
                },
                'dest': {'box': dest['box'], 'slot': dest['slot']},
                'pokemon': pokemon_copy
            }
            self.undo_available = True
            
            # 3. Check for trade evolution
            if TRADE_EVOLUTION_AVAILABLE and can_evolve_by_trade:
                species_id = pokemon_data.get('species', 0)
                held_item = pokemon_data.get('held_item', 0)
                evolution_info = can_evolve_by_trade(species_id, held_item)
                
                if evolution_info:
                    # Pokemon can evolve! Show evolution dialog
                    print(f"[PCBox] Trade evolution available: {evolution_info['from_name']} -> {evolution_info['to_name']}", file=sys.stderr, flush=True)
                    self._show_evolution_dialog(pokemon_data, evolution_info, dest['box'], dest['slot'])
            
            # 4. Refresh display
            self.refresh_data()
            
            pokemon_name = self.moving_pokemon.get('nickname') or 'Pokemon'
            print(f"[PCBox] Deposit complete: {pokemon_name}", file=sys.stderr, flush=True)
            print(f"[PCBox] ===== DEPOSIT DONE =====\n", file=sys.stderr, flush=True)
            
            # 5. Track achievement progress
            self._track_sinew_achievement(deposit=True, is_shiny=pokemon_data.get('is_shiny', False))
            
        except Exception as e:
            print(f"[PCBox] Deposit FAILED: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            self._show_warning(f"Deposit failed!\n{str(e)[:30]}")
        
        finally:
            self._cancel_move_mode()
            if hasattr(self, 'pending_move_dest'):
                del self.pending_move_dest
    
    def _attempt_sinew_to_game_move(self, dest_type, dest_box, dest_slot):
        """Attempt to withdraw Pokemon from Sinew storage to a game save"""
        import sys
        
        # Check if destination game is running
        dest_game = self.get_current_game()
        if self.is_game_running_callback:
            running_game = self.is_game_running_callback()
            if running_game and dest_game in running_game:
                self._show_warning("Destination game\nis running!\nStop game first")
                self._cancel_move_mode()
                return
        
        # Check if we have raw_bytes for the transfer
        if not self.moving_pokemon.get('raw_bytes'):
            self._show_warning("Pokemon data missing!\nCannot transfer")
            self._cancel_move_mode()
            return
        
        # Check if destination slot is empty
        dest_poke = self.get_pokemon_at_grid_slot(dest_slot)
        if dest_poke and not dest_poke.get('empty'):
            self._show_warning("Slot is occupied!\nChoose an empty slot")
            return
        
        # Get destination save path
        current_save_path = getattr(self.manager, 'current_save_path', None)
        if not current_save_path:
            self._show_warning("No save file loaded!")
            self._cancel_move_mode()
            return
        
        # Check obedience warning
        obedience_warning = None
        pokemon_level = self.moving_pokemon.get('level', 1)
        
        dest_badge_count = 0
        if self.manager.is_loaded() and hasattr(self.manager, 'get_badges'):
            badges = self.manager.get_badges()
            if badges:
                dest_badge_count = sum(1 for b in badges if b)
        
        dest_game_type = 'FRLG' if dest_game and ('Fire' in dest_game or 'Leaf' in dest_game) else 'RSE'
        
        obedience_levels = {0: 10, 1: 20, 2: 30, 3: 40, 4: 50, 5: 60, 6: 70, 7: 80, 8: 100}
        max_level = obedience_levels.get(dest_badge_count, 10)
        
        if pokemon_level > max_level:
            pokemon_name = self.moving_pokemon.get('nickname') or self.moving_pokemon.get('species_name', 'Pokemon')
            obedience_warning = f"WARNING: {pokemon_name} (Lv.{pokemon_level})\nmay not obey!\n{dest_game} has {dest_badge_count} badge(s)\n(max Lv.{max_level})"
        
        # Store destination info
        self.pending_move_dest = {
            'type': dest_type,
            'box': self.box_index + 1,
            'slot': dest_slot,
            'game': dest_game,
            'save_path': current_save_path,
            'game_type': dest_game_type
        }
        
        # Build confirmation message
        pokemon_name = self.moving_pokemon.get('nickname') or self.moving_pokemon.get('species_name', 'Pokemon')
        source = self.moving_pokemon_source
        
        message = f"Withdraw {pokemon_name}\nfrom Sinew Storage\nto {dest_game}\nBox {self.box_index + 1}, Slot {dest_slot + 1}?"
        
        # Show confirmation dialog
        if obedience_warning:
            self.confirmation_dialog_message = obedience_warning + "\n\nMove anyway?"
        else:
            self.confirmation_dialog_message = message
        
        self.confirmation_dialog_open = True
        self.confirmation_selected = 0
        self.confirmation_dialog_callback = self._execute_sinew_to_game_move
    
    def _execute_sinew_to_game_move(self):
        """Execute the withdrawal from Sinew storage to game save"""
        import sys
        
        if not self.moving_pokemon or not self.moving_pokemon_source or not hasattr(self, 'pending_move_dest'):
            self._cancel_move_mode()
            return
        
        source = self.moving_pokemon_source
        dest = self.pending_move_dest
        
        print(f"\n[PCBox] ===== WITHDRAW FROM SINEW =====", file=sys.stderr, flush=True)
        print(f"[PCBox] From: Sinew Storage {source['box']}, slot {source['slot']}", file=sys.stderr, flush=True)
        print(f"[PCBox] To: {dest['game']} box {dest['box']}, slot {dest['slot']}", file=sys.stderr, flush=True)
        
        # Store for undo BEFORE making changes
        pokemon_copy = self.moving_pokemon.copy()
        
        try:
            raw_bytes = self.moving_pokemon.get('raw_bytes')
            if not raw_bytes:
                raise ValueError("No raw_bytes in Pokemon data")
            
            dest_save_path = dest.get('save_path')
            dest_game_type = dest.get('game_type', 'RSE')
            
            if not dest_save_path:
                raise ValueError("No destination save path")
            
            # 1. Write Pokemon to destination game save
            dest_save_data = load_save_file(dest_save_path)
            write_pokemon_to_pc(dest_save_data, dest['box'], dest['slot'], raw_bytes, dest_game_type)
            
            # 1b. Update Pokedex - mark this Pokemon as seen and caught
            # Note: Pokemon outside regional dex won't show until player unlocks National Dex
            try:
                from save_writer import set_pokedex_flags_for_pokemon
                result = set_pokedex_flags_for_pokemon(dest_save_data, self.moving_pokemon, game_type=dest_game_type)
                if result:
                    pokemon_name = self.moving_pokemon.get('species_name', 'Pokemon')
                    species = self.moving_pokemon.get('species', 0)
                    print(f"[PCBox] Updated Pokedex: #{species} ({pokemon_name}) marked as seen/caught", file=sys.stderr, flush=True)
            except Exception as dex_err:
                print(f"[PCBox] Pokedex update skipped: {dex_err}", file=sys.stderr, flush=True)
            
            write_save_file(dest_save_path, dest_save_data, create_backup_first=True)
            
            print(f"[PCBox] Written to {dest['game']}", file=sys.stderr, flush=True)
            
            # 2. Clear source slot in Sinew storage
            if self.sinew_storage:
                self.sinew_storage.clear_slot(source['box'], source['slot'])
                print(f"[PCBox] Cleared Sinew storage slot", file=sys.stderr, flush=True)
            
            # Store undo action
            self.undo_action = {
                'type': 'move',
                'move_type': 'sinew_to_game',
                'source': {'box': source['box'], 'slot': source['slot']},
                'dest': {
                    'box': dest['box'],
                    'slot': dest['slot'],
                    'game': dest.get('game'),
                    'save_path': dest_save_path,
                    'game_type': dest_game_type
                },
                'pokemon': pokemon_copy
            }
            self.undo_available = True
            
            # 3. Check for trade evolution (Sinew -> Game counts as a "trade")
            evolution_triggered = False
            if TRADE_EVOLUTION_AVAILABLE and can_evolve_by_trade:
                species_id = pokemon_copy.get('species', 0)
                held_item = pokemon_copy.get('held_item', 0)
                print(f"[PCBox] Evolution check: species={species_id}, held_item={held_item}", file=sys.stderr, flush=True)
                evolution_info = can_evolve_by_trade(species_id, held_item)
                
                if evolution_info:
                    # Pokemon can evolve! Show evolution dialog for the game save
                    print(f"[PCBox] Trade evolution available: {evolution_info['from_name']} -> {evolution_info['to_name']}", file=sys.stderr, flush=True)
                    self._show_evolution_dialog_game(
                        pokemon_copy, 
                        evolution_info, 
                        dest['box'], 
                        dest['slot'],
                        dest_save_path,
                        dest.get('game', 'Game')
                    )
                    evolution_triggered = True
                else:
                    print(f"[PCBox] No evolution available for species {species_id}", file=sys.stderr, flush=True)
            
            # 4. Force reload destination save
            from parser.gen3_parser import Gen3SaveParser
            fresh_parser = Gen3SaveParser(dest_save_path)
            self.manager.parser = fresh_parser
            self.manager.loaded = fresh_parser.loaded
            self.manager.current_save_path = dest_save_path
            
            # 4. Refresh display
            self.current_box_data = []
            self.party_data = []
            self.selected_pokemon = None
            self.refresh_data()
            
            pokemon_name = self.moving_pokemon.get('nickname') or 'Pokemon'
            print(f"[PCBox] Withdraw complete: {pokemon_name}", file=sys.stderr, flush=True)
            print(f"[PCBox] ===== WITHDRAW DONE =====\n", file=sys.stderr, flush=True)
            
            # 5. Track achievement progress (transfer from Sinew to game)
            self._track_sinew_achievement(transfer=True)
            
        except Exception as e:
            print(f"[PCBox] Withdraw FAILED: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            self._show_warning(f"Withdraw failed!\n{str(e)[:30]}")
        
        finally:
            self._cancel_move_mode()
            if hasattr(self, 'pending_move_dest'):
                del self.pending_move_dest
    
    def _attempt_place_pokemon(self, dest_type, dest_box, dest_slot):
        """Attempt to place the moving Pokemon at destination"""
        if not self.move_mode or not self.moving_pokemon:
            return
        
        # Check if we're in Sinew mode or source is from Sinew
        source_is_sinew = self.moving_pokemon_source.get('game') == 'Sinew'
        dest_is_sinew = self.sinew_mode
        
        # Handle Sinew storage moves
        if source_is_sinew or dest_is_sinew:
            if source_is_sinew and dest_is_sinew:
                # Move within Sinew storage
                self._execute_sinew_move(dest_type, dest_box, dest_slot)
            elif source_is_sinew and not dest_is_sinew:
                # Sinew -> Game (withdraw from Sinew to game save)
                self._attempt_sinew_to_game_move(dest_type, dest_box, dest_slot)
            else:
                # Game -> Sinew (deposit from game save to Sinew)
                self._attempt_game_to_sinew_move(dest_type, dest_box, dest_slot)
            return
        
        # Check if destination game is running - block moves to active game
        if self._is_current_game_running():
            self._show_warning("Game is running!\nStop game to move Pokemon")
            return
        
        # Check if destination slot is empty
        if dest_type == 'box':
            dest_poke = self.get_pokemon_at_grid_slot(dest_slot)
            if dest_poke and not dest_poke.get('empty'):
                # Slot is occupied - can't place here
                print("Slot is occupied - choose an empty slot")
                return
        
        # Check if we have raw_bytes for the transfer
        if not self.moving_pokemon.get('raw_bytes'):
            print("Error: Pokemon data missing raw_bytes - cannot transfer")
            self._cancel_move_mode()
            return
        
        # Check obedience if moving to a different game
        obedience_warning = None
        source_game = self.moving_pokemon_source.get('game', '???')
        dest_game = self.get_current_game()
        
        if source_game != dest_game:
            pokemon_level = self.moving_pokemon.get('level', 1)
            
            # Get destination trainer's badge count using manager.get_badges()
            dest_badge_count = 0
            if self.manager.is_loaded() and hasattr(self.manager, 'get_badges'):
                badges = self.manager.get_badges()
                if badges:
                    dest_badge_count = sum(1 for b in badges if b)
            
            # Determine game type for obedience calculation
            dest_game_type = 'RSE'
            if dest_game and ('Fire' in dest_game or 'Leaf' in dest_game):
                dest_game_type = 'FRLG'
            
            # Calculate max obedient level based on badges
            obedience_levels = {
                0: 10, 1: 20, 2: 30, 3: 40, 4: 50, 5: 60, 6: 70, 7: 80, 8: 100
            }
            max_level = obedience_levels.get(dest_badge_count, 10)
            
            if pokemon_level > max_level:
                pokemon_name = self.moving_pokemon.get('nickname') or self.moving_pokemon.get('species_name', 'Pokemon')
                obedience_warning = f"WARNING: {pokemon_name} (Lv.{pokemon_level})\nmay not obey!\n{dest_game} trainer has\n{dest_badge_count} badge(s) (max Lv.{max_level})"
        
        # Get the current save path for destination
        current_save_path = getattr(self.manager, 'current_save_path', None)
        
        # Store destination info for confirmation
        self.pending_move_dest = {
            'type': dest_type,
            'box': dest_box,
            'slot': dest_slot,
            'game': self.get_current_game(),
            'save_path': current_save_path
        }
        
        # Build confirmation message
        pokemon_name = self.moving_pokemon.get('nickname') or self.moving_pokemon.get('species_name', 'Pokemon')
        
        if self.moving_pokemon_source['type'] == 'box':
            source_loc = f"Box {self.moving_pokemon_source['box']}, Slot {self.moving_pokemon_source['slot'] + 1}"
        else:
            source_loc = f"Party Slot {self.moving_pokemon_source['slot'] + 1}"
        
        dest_loc = f"Box {dest_box}, Slot {dest_slot + 1}"
        
        if obedience_warning:
            # Show warning with Move Anyway / Cancel options
            self.confirmation_dialog_message = obedience_warning + "\n\nMove anyway?"
        elif source_game != dest_game:
            self.confirmation_dialog_message = f"Move {pokemon_name}\nfrom {source_game} {source_loc}\nto {dest_game} {dest_loc}?"
        else:
            self.confirmation_dialog_message = f"Move {pokemon_name}\nfrom {source_loc}\nto {dest_loc}?"
        
        self.confirmation_dialog_open = True
        self.confirmation_selected = 0
        self.confirmation_dialog_callback = self._execute_move
    
    def _execute_move(self):
        """Execute the confirmed move operation"""
        import sys
        
        if not self.moving_pokemon or not self.moving_pokemon_source or not hasattr(self, 'pending_move_dest'):
            print("Error: Missing move data", file=sys.stderr, flush=True)
            self._cancel_move_mode()
            return
        
        source = self.moving_pokemon_source
        dest = self.pending_move_dest
        
        print(f"\n[PCBox] ===== EXECUTING TRANSFER =====", file=sys.stderr, flush=True)
        print(f"[PCBox] From: {source['game']} box {source.get('box')}, slot {source.get('slot')}", file=sys.stderr, flush=True)
        print(f"[PCBox] To: {dest['game']} box {dest['box']}, slot {dest['slot']}", file=sys.stderr, flush=True)
        
        # Store for undo BEFORE making changes
        pokemon_copy = self.moving_pokemon.copy()
        
        try:
            raw_bytes = self.moving_pokemon.get('raw_bytes')
            if not raw_bytes:
                raise ValueError("No raw_bytes in Pokemon data")
            
            dest_game_type = 'FRLG' if dest['game'] and ('Fire' in dest['game'] or 'Leaf' in dest['game']) else 'RSE'
            source_game_type = 'FRLG' if source['game'] and ('Fire' in source['game'] or 'Leaf' in source['game']) else 'RSE'
            
            dest_save_path = dest.get('save_path')
            source_save_path = source.get('save_path')
            
            if not dest_save_path or not source_save_path:
                raise ValueError(f"Missing save paths: dest={dest_save_path}, source={source_save_path}")
            
            # 1. Write Pokemon to destination
            dest_save_data = load_save_file(dest_save_path)
            write_pokemon_to_pc(dest_save_data, dest['box'], dest['slot'], raw_bytes, dest_game_type)
            
            # 1b. Update Pokedex in destination game - mark this Pokemon as seen and caught
            # Note: Pokemon outside regional dex won't show until player unlocks National Dex
            try:
                from save_writer import set_pokedex_flags_for_pokemon
                result = set_pokedex_flags_for_pokemon(dest_save_data, self.moving_pokemon, game_type=dest_game_type)
                if result:
                    pokemon_name = self.moving_pokemon.get('species_name', 'Pokemon')
                    species = self.moving_pokemon.get('species', 0)
                    print(f"[PCBox] Updated Pokedex: #{species} ({pokemon_name}) marked as seen/caught in {dest['game']}", file=sys.stderr, flush=True)
            except Exception as dex_err:
                print(f"[PCBox] Pokedex update skipped: {dex_err}", file=sys.stderr, flush=True)
            
            # 2. Handle source clearing
            if source_save_path == dest_save_path:
                # Same file
                if source['type'] == 'box':
                    clear_pc_slot(dest_save_data, source['box'], source['slot'], dest_game_type)
                write_save_file(dest_save_path, dest_save_data, create_backup_first=True)
            else:
                # Different files
                write_save_file(dest_save_path, dest_save_data, create_backup_first=True)
                
                if source['type'] == 'box':
                    source_save_data = load_save_file(source_save_path)
                    clear_pc_slot(source_save_data, source['box'], source['slot'], source_game_type)
                    write_save_file(source_save_path, source_save_data, create_backup_first=True)
            
            # Store undo action
            self.undo_action = {
                'type': 'move',
                'move_type': 'game_to_game',
                'source': {
                    'type': source['type'],
                    'box': source.get('box'),
                    'slot': source.get('slot'),
                    'game': source.get('game'),
                    'save_path': source_save_path,
                    'game_type': source_game_type
                },
                'dest': {
                    'box': dest['box'],
                    'slot': dest['slot'],
                    'game': dest.get('game'),
                    'save_path': dest_save_path,
                    'game_type': dest_game_type
                },
                'pokemon': pokemon_copy
            }
            self.undo_available = True
            
            print(f"[PCBox] Files written successfully", file=sys.stderr, flush=True)
            
            # 3. Force reload current save with fresh parser
            from parser.gen3_parser import Gen3SaveParser
            fresh_parser = Gen3SaveParser(dest_save_path)
            self.manager.parser = fresh_parser
            self.manager.loaded = fresh_parser.loaded
            self.manager.current_save_path = dest_save_path
            print(f"[PCBox] Created fresh parser", file=sys.stderr, flush=True)
            
            # 4. Clear UI cache and refresh
            self.current_box_data = []
            self.party_data = []
            self.selected_pokemon = None
            self.refresh_data()
            
            pokemon_name = self.moving_pokemon.get('nickname') or 'Pokemon'
            print(f"[PCBox] Transfer complete: {pokemon_name}", file=sys.stderr, flush=True)
            print(f"[PCBox] ===== TRANSFER DONE =====\n", file=sys.stderr, flush=True)
            
            # Check for trade evolution (only when moving between different games)
            if source['game'] != dest['game'] and TRADE_EVOLUTION_AVAILABLE and can_evolve_by_trade:
                species_id = self.moving_pokemon.get('species', 0)
                held_item = self.moving_pokemon.get('held_item', 0)
                evolution_info = can_evolve_by_trade(species_id, held_item)
                
                if evolution_info:
                    # Pokemon can evolve! Show evolution dialog
                    print(f"[PCBox] Trade evolution available: {evolution_info['from_name']} -> {evolution_info['to_name']}", file=sys.stderr, flush=True)
                    # Store location info for game save evolution
                    self._show_evolution_dialog_game(
                        self.moving_pokemon, 
                        evolution_info, 
                        dest['box'], 
                        dest['slot'],
                        dest['save_path'],
                        dest['game']
                    )
            
        except Exception as e:
            print(f"[PCBox] Transfer FAILED: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
        
        finally:
            self._cancel_move_mode()
            if hasattr(self, 'pending_move_dest'):
                del self.pending_move_dest

    # ------------------- Pause Combo -------------------
    
    def _load_pause_combo_setting(self):
        """Load pause combo setting from sinew_settings.json"""
        import json
        default = {"type": "combo", "buttons": ["START", "SELECT"]}
        try:
            if os.path.exists("sinew_settings.json"):
                with open("sinew_settings.json", "r") as f:
                    settings = json.load(f)
                    if "pause_combo" in settings:
                        return settings["pause_combo"]
        except:
            pass
        return default
    
    def _check_pause_combo(self, ctrl):
        """Check if the configured pause combo is held"""
        # Reload setting each time to pick up changes
        setting = self._load_pause_combo_setting()
        
        if setting.get("type") == "custom":
            # Custom single button - check via joystick directly
            custom_btn = setting.get("button")
            if custom_btn is not None:
                try:
                    import pygame
                    if pygame.joystick.get_count() > 0:
                        joy = pygame.joystick.Joystick(0)
                        joy.init()
                        if custom_btn < joy.get_numbuttons():
                            return joy.get_button(custom_btn)
                except:
                    pass
            return False
        else:
            # Button combo - check all required buttons
            required_buttons = setting.get("buttons", ["START", "SELECT"])
            try:
                for btn_name in required_buttons:
                    if not ctrl._is_button_pressed(btn_name):
                        return False
                return True
            except:
                return False

    # ------------------- Data Management -------------------
    
    def _is_sinew_mode(self):
        """Check if we're currently viewing Sinew (cross-game storage)"""
        if self.get_current_game_callback:
            current_game = self.get_current_game_callback()
            return current_game == "Sinew"
        return False
    
    def is_sinew_storage(self):
        """Public method to check if currently in Sinew storage mode"""
        return self.sinew_mode
    
    def _get_current_save_path(self):
        """Get the save file path for the current game (non-Sinew)"""
        if self.manager and hasattr(self.manager, 'current_save_path'):
            return self.manager.current_save_path
        return None
    
    def _update_sinew_mode(self):
        """Update Sinew mode state after game change"""
        was_sinew = self.sinew_mode
        self.sinew_mode = self._is_sinew_mode()
        
        if self.sinew_mode != was_sinew:
            # Mode changed, reset state
            self.box_index = 0
            self.sinew_scroll_offset = 0
            self.grid_selected = 0
            self.grid_nav = NavigableList(30, columns=6, wrap=False)
            
            # Update box names
            if self.sinew_mode:
                self.box_names = [f"STORAGE {i+1}" for i in range(20)]
                self.max_boxes = 20
            else:
                self.box_names = [f"BOX {i+1}" for i in range(14)]
                self.max_boxes = 14
    
    def get_box_name(self, box_index):
        """Get the name for a specific box"""
        if self.sinew_mode:
            return f"STORAGE {box_index + 1}"
        return f"BOX {box_index + 1}"
    
    def refresh_data(self):
        """Refresh Pokemon data from save file or Sinew storage"""
        import sys
        
        # Update Sinew mode status
        self._update_sinew_mode()
        
        if self.sinew_mode:
            # Load from Sinew storage
            if self.sinew_storage and self.sinew_storage.is_loaded():
                self.current_box_data = self.sinew_storage.get_box(self.box_index + 1)
                self.party_data = []  # Sinew has no party
                
                # Enrich Pokemon data with species names if missing
                for poke in self.current_box_data:
                    if poke and not poke.get('species_name'):
                        self._enrich_pokemon_data(poke)
                
                pokemon_count = sum(1 for p in self.current_box_data if p is not None)
                print(f"[PCBox] Sinew Storage {self.box_index + 1}: {pokemon_count} Pokemon", file=sys.stderr, flush=True)
            else:
                self.current_box_data = [None] * 120
                self.party_data = []
                print(f"[PCBox] Sinew storage not loaded!", file=sys.stderr, flush=True)
        else:
            # Load from game save - ALWAYS reload from disk to catch external changes
            save_path = getattr(self.manager, 'current_save_path', None)
            if save_path and os.path.exists(save_path):
                # Force fresh load from disk
                try:
                    from parser.gen3_parser import Gen3SaveParser
                    fresh_parser = Gen3SaveParser(save_path)
                    self.manager.parser = fresh_parser
                    self.manager.loaded = fresh_parser.loaded
                    print(f"[PCBox] Reloaded save from disk: {save_path}", file=sys.stderr, flush=True)
                except Exception as e:
                    print(f"[PCBox] Error reloading save: {e}", file=sys.stderr, flush=True)
            
            if self.manager.is_loaded():
                # Get current box (boxes are 1-14, our index is 0-13)
                self.current_box_data = self.manager.get_box(self.box_index + 1)
                self.party_data = self.manager.get_party()
                
                # Count actual Pokemon (not empty slots)
                pokemon_count = sum(1 for p in self.current_box_data if p and p.get('species', 0) > 0)
                print(f"[PCBox] Box {self.box_index + 1}: {pokemon_count} Pokemon", file=sys.stderr, flush=True)
            else:
                self.current_box_data = []
                self.party_data = []
                print(f"[PCBox] Manager not loaded!", file=sys.stderr, flush=True)
    
    def _enrich_pokemon_data(self, pokemon):
        """Add species_name to Pokemon data if missing"""
        if not pokemon or pokemon.get('species_name'):
            return
        
        species_id = pokemon.get('species', 0)
        if species_id == 0:
            return
        
        # Try to get species name from DB
        try:
            import json
            db_path = "data/pokemon_db.json"
            if os.path.exists(db_path):
                with open(db_path, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                
                species_key = str(species_id).zfill(3)
                if species_key in db:
                    pokemon['species_name'] = db[species_key].get('name', f'#{species_id}')
                else:
                    pokemon['species_name'] = f'#{species_id}'
        except:
            pokemon['species_name'] = f'#{species_id}'
    
    def get_pokemon_at_grid_slot(self, grid_index):
        """
        Get Pokemon at a specific grid slot.
        For Sinew mode, accounts for scroll offset.
        
        Args:
            grid_index: Visual grid slot (0-29)
            
        Returns:
            dict or None: Pokemon data or empty slot marker
        """
        if self.sinew_mode:
            # Account for scroll offset in Sinew mode
            actual_index = grid_index + (self.sinew_scroll_offset * 6)  # 6 columns
            if 0 <= actual_index < len(self.current_box_data):
                return self.current_box_data[actual_index]
            return None
        else:
            if 0 <= grid_index < len(self.current_box_data):
                return self.current_box_data[grid_index]
        return None

    # ------------------- Box Navigation -------------------
    def prev_box(self):
        max_boxes = 20 if self.sinew_mode else 14
        self.box_index = (self.box_index - 1) % max_boxes
        self.box_button.text = self.get_box_name(self.box_index)
        self.sinew_scroll_offset = 0  # Reset scroll when changing boxes
        self.refresh_data()
        self.selected_pokemon = None

    def next_box(self):
        max_boxes = 20 if self.sinew_mode else 14
        self.box_index = (self.box_index + 1) % max_boxes
        self.box_button.text = self.get_box_name(self.box_index)
        self.sinew_scroll_offset = 0  # Reset scroll when changing boxes
        self.refresh_data()
        self.selected_pokemon = None
    
    def scroll_sinew_up(self):
        """Scroll Sinew storage view up"""
        if self.sinew_mode and self.sinew_scroll_offset > 0:
            self.sinew_scroll_offset -= 1
            return True
        return False
    
    def scroll_sinew_down(self):
        """Scroll Sinew storage view down"""
        if self.sinew_mode:
            max_scroll = self.sinew_total_rows - self.sinew_visible_rows
            if self.sinew_scroll_offset < max_scroll:
                self.sinew_scroll_offset += 1
                return True
        return False
    
    # ------------------- Game Navigation -------------------
    def change_game(self, delta):
        """Change the current game and reload save data"""
        import sys
        print(f"\n[PCBox] ===== GAME SWITCH =====", file=sys.stderr, flush=True)
        
        # Call gamescreen to switch games
        if self.prev_game_callback and delta < 0:
            self.prev_game_callback()
        elif self.next_game_callback and delta > 0:
            self.next_game_callback()
        
        # Get the new game name and check if we're in Sinew mode
        new_game = self.get_current_game()
        print(f"[PCBox] Switched to: {new_game}", file=sys.stderr, flush=True)
        
        # Check if we switched to/from Sinew mode
        was_sinew = self.sinew_mode
        self.sinew_mode = (new_game == "Sinew")
        
        if self.sinew_mode:
            # Sinew mode - use Sinew storage
            print(f"[PCBox] Sinew mode activated - using Sinew storage", file=sys.stderr, flush=True)
            # Reset scroll and box when entering Sinew mode
            if not was_sinew:
                self.box_index = 0
                self.sinew_scroll_offset = 0
                self.box_names = [f"STORAGE {i+1}" for i in range(20)]
                self.max_boxes = 20
        else:
            # Regular game mode - load save file
            new_path = getattr(self.manager, 'current_save_path', None)
            print(f"[PCBox] Save path: {new_path}", file=sys.stderr, flush=True)
            
            # FORCE fresh reload from disk
            if new_path:
                import os
                print(f"[PCBox] File mtime: {os.path.getmtime(new_path)}", file=sys.stderr, flush=True)
                
                # Create a completely fresh parser that reads from disk
                from parser.gen3_parser import Gen3SaveParser
                fresh_parser = Gen3SaveParser(new_path)
                
                # Replace the manager's parser
                self.manager.parser = fresh_parser
                self.manager.loaded = fresh_parser.loaded
                self.manager.current_save_path = new_path
                
                print(f"[PCBox] Created fresh parser", file=sys.stderr, flush=True)
            
            # Reset box index when leaving Sinew mode
            if was_sinew:
                self.box_index = 0
                self.box_names = [f"BOX {i+1}" for i in range(14)]
                self.max_boxes = 14
        
        # Clear ALL cached data
        self.current_box_data = []
        self.party_data = []
        self.selected_pokemon = None
        self.sinew_scroll_offset = 0
        
        # Get fresh data from the newly loaded parser or Sinew storage
        self.refresh_data()
        
        # Update UI
        self.update_game_button_text()
        self.box_button.text = self.get_box_name(self.box_index)
        print(f"[PCBox] ===== SWITCH DONE =====\n", file=sys.stderr, flush=True)
    
    def get_current_game(self):
        """Get the current game name"""
        if self.get_current_game_callback:
            return self.get_current_game_callback()
        return "Unknown"
    
    def is_current_game_running(self):
        """Check if the currently displayed game is running in the emulator"""
        if self.is_game_running_callback:
            running_game = self.is_game_running_callback()
            if running_game:
                current_game = self.get_current_game()
                return running_game == current_game
        return False
    
    def update_game_button_text(self):
        """Update the game button to show current game"""
        self.game_button.text = self.get_current_game()

    # ------------------- Sprite -------------------
    def set_sprite(self, path):
        if not path or not os.path.exists(path):
            self.current_sprite_image = None
            return
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.smoothscale(img, (int(self.sprite_area.width - 4),
                                                 int(self.sprite_area.height - 4)))
        self.current_sprite_image = img

    # ------------------- Party Panel -------------------
    def toggle_party_panel(self):
        # Sinew mode has no party
        if self.sinew_mode:
            return
        
        self.party_panel_open = not self.party_panel_open
        if self.party_panel_open:
            self.party_panel_target_y = 0
            self.party_selected = 0  # Reset party selection
            self._update_party_selection()  # Update display to show first party Pokemon
        else:
            self.party_panel_target_y = -self.height

    # ------------------- Mouse Handling -------------------
    def handle_mouse(self, event):
        consumed = False
        # Always check party and close buttons
        for btn in [self.party_button, self.close_button]:
            btn.handle_event(event)
            if btn.rect.collidepoint(pygame.mouse.get_pos()):
                consumed = True

        # Only allow interactions inside party panel if open
        if self.party_panel_open:
            panel_slots = self.get_party_slot_rects()
            if event.type == MOUSEBUTTONDOWN:
                for i, slot in enumerate(panel_slots):
                    if slot.collidepoint(event.pos):
                        if i < len(self.party_data):
                            poke = self.party_data[i]
                            # Select this party Pokemon
                            self.selected_pokemon = poke
                            self.party_selected = i
                        consumed = True

        # Only allow main grid/buttons if panel is closed
        if not self.party_panel_open:
            for btn in [self.left_game_arrow, self.game_button, self.right_game_arrow,
                        self.left_box_arrow, self.box_button, self.right_box_arrow]:
                btn.handle_event(event)
                if btn.rect.collidepoint(pygame.mouse.get_pos()):
                    consumed = True
            
            # Handle grid clicks
            if event.type == MOUSEBUTTONDOWN:
                grid_rects = self.get_grid_rects()
                for i, rect in enumerate(grid_rects):
                    if rect.collidepoint(event.pos):
                        poke = self.get_pokemon_at_grid_slot(i)
                        self.grid_nav.set_selected(i)  # Update grid nav state
                        if poke and not poke.get('empty'):
                            self.selected_pokemon = poke
                            print(f"Selected box Pokemon: {self.manager.format_pokemon_display(poke)}")
                        consumed = True
                        break

        return consumed

    def get_party_slot_rects(self, inner_y=None, inner_height=None):
        slot_margin = 8
        panel_rect = self.party_panel_rect
        inner_y = inner_y or panel_rect.y
        inner_height = inner_height or panel_rect.height

        # Compute a base size using the panel width/height
        base_w = (panel_rect.width - slot_margin * 4) / 3          # width for left + right slots
        base_h = (inner_height - slot_margin * 6) / 6             # height for 6 slots
        slot_size = min(base_w, base_h) * self.party_slot_scale   # make square and apply scale

        panel_cy = inner_y + inner_height / 2

        # ------------------- Left Big Slot -------------------
        left_slot_rect = pygame.Rect(
            panel_rect.x + slot_margin + self.party_slot_x_offset,
            panel_cy - slot_size / 2,
            slot_size,
            slot_size
        )

        # ------------------- Right 5 Slots -------------------
        right_slots = []
        right_x = left_slot_rect.right + slot_margin
        total_right_h = 5 * slot_size + 4 * slot_margin
        start_y = panel_cy - total_right_h / 2

        for i in range(5):
            slot = pygame.Rect(
                right_x,
                start_y + i * (slot_size + slot_margin),
                slot_size,
                slot_size
            )
            right_slots.append(slot)

        return [left_slot_rect] + right_slots

    def get_grid_rects(self):
        """Get all grid cell rectangles for the current box"""
        # Compute cell size
        cell_w = (self.grid_rect.width - (self.grid_cols - 1)) / self.grid_cols
        cell_h = (self.grid_rect.height - (self.grid_rows - 1)) / self.grid_rows
        cell_size = min(cell_w, cell_h) * 1.1

        total_width = self.grid_cols * cell_size + (self.grid_cols - 1)
        grid_start_x = self.box_button.rect.centerx - total_width / 2
        grid_start_y = self.grid_rect.y - 10

        rects = []
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                rect = pygame.Rect(
                    grid_start_x + c * (cell_size + 1),
                    grid_start_y + r * (cell_size + 1),
                    cell_size, cell_size
                )
                rects.append(rect)
        
        return rects

    # ------------------- Draw ROM Hack Overlay -------------------
    def _draw_rom_hack_overlay(self, surf, rect, size='small'):
        """
        Draw ROM hack indicator overlay on a slot
        
        Args:
            surf: Surface to draw on
            rect: Rectangle of the slot
            size: 'small' for grid/party slots, 'large' for main sprite area
        """
        try:
            # Red semi-transparent overlay
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill((180, 0, 0, 100))
            surf.blit(overlay, rect.topleft)
            
            if size == 'small':
                # "HACK" text for small slots
                tiny_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 6)
                hack_text = tiny_font.render("HACK", True, (255, 100, 100))
                hack_rect = hack_text.get_rect(centerx=rect.centerx, bottom=rect.bottom - 2)
                surf.blit(hack_text, hack_rect)
            else:
                # "ROM HACK" banner for large display
                banner_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 10)
                hack_text = banner_font.render("ROM HACK", True, (255, 80, 80))
                hack_rect = hack_text.get_rect(centerx=rect.centerx, top=rect.top + 5)
                
                # Draw background for text
                bg_rect = hack_rect.inflate(10, 4)
                pygame.draw.rect(surf, (60, 0, 0), bg_rect)
                pygame.draw.rect(surf, (255, 80, 80), bg_rect, 1)
                surf.blit(hack_text, hack_rect)
        except:
            pass

    # ------------------- Draw Grid -------------------
    def draw_grid(self, surf):
        """Draw the PC box grid with Pokemon data"""
        
        rects = self.get_grid_rects()
        grid_selected_idx = self.grid_nav.get_selected()
        
        for i, rect in enumerate(rects):
            poke = self.get_pokemon_at_grid_slot(i)
            
            # Determine if this is the selected Pokemon
            is_selected = (poke and self.selected_pokemon and 
                          poke.get('species') == self.selected_pokemon.get('species') and
                          poke.get('personality') == self.selected_pokemon.get('personality'))
            
            # Check if this slot is controller-selected
            is_controller_selected = (i == grid_selected_idx and not self.party_panel_open)
            
            # Base color for slot (use theme button color with transparency)
            if poke and not poke.get('empty'):
                # Occupied slot - slightly brighter
                r, g, b = ui_colors.COLOR_BUTTON_HOVER[:3] if len(ui_colors.COLOR_BUTTON_HOVER) >= 3 else (80, 80, 100)
                base_color = (r, g, b, 180)
            else:
                # Empty slot - dimmer
                r, g, b = ui_colors.COLOR_BUTTON[:3] if len(ui_colors.COLOR_BUTTON) >= 3 else (60, 60, 60)
                base_color = (r, g, b, 180)
            
            # Draw slot background with transparency
            slot_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(slot_surf, base_color, (0, 0, rect.width, rect.height))
            surf.blit(slot_surf, rect.topleft)
            
            # Draw border
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, rect, 1)
            
            # Highlight controller-selected slot
            if is_controller_selected:
                # Draw highlight cursor border
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, rect, 3)
            
            # Highlight selected Pokemon (when A is pressed) - keep yellow for distinction
            if is_selected and not is_controller_selected:
                # Draw bright highlight border (yellow to distinguish from cursor)
                pygame.draw.rect(surf, (255, 255, 100), rect, 3)
            
            # Draw pulsing border for Altering Cave Zubats (mystical purple pulse)
            if poke and not poke.get('empty') and self._is_altering_cave_zubat(poke):
                pulse_color = self._get_altering_cave_pulse_color()
                pygame.draw.rect(surf, pulse_color, rect, 2)
            
            # Draw Pokemon sprite (gen3 PNG) if available
            if poke and not poke.get('empty') and not poke.get('egg'):
                
                # Use helper method that works for both game and Sinew Pokemon
                sprite_path = self._get_pokemon_sprite_path(poke)
                
                if sprite_path and os.path.exists(sprite_path):
                    try:
                        sprite = pygame.image.load(sprite_path).convert_alpha()
                        # Scale sprite to fit in cell (leave small margin)
                        cell_size = min(rect.width, rect.height)
                        sprite_size = int(cell_size * 0.8)
                        sprite = pygame.transform.smoothscale(sprite, (sprite_size, sprite_size))
                        sprite_rect = sprite.get_rect(center=rect.center)
                        surf.blit(sprite, sprite_rect)
                    except:
                        pass  # If sprite fails to load, just show colored cell
                
                # Draw ROM HACK overlay for Pokemon from ROM hacks
                if poke.get('rom_hack'):
                    self._draw_rom_hack_overlay(surf, rect, size='small')
            
            # For eggs, draw egg sprite
            elif poke and poke.get('egg'):
                # Try to load egg sprite
                egg_path = "data/sprites/gen3/normal/egg.png"
                if os.path.exists(egg_path):
                    try:
                        egg_sprite = pygame.image.load(egg_path).convert_alpha()
                        # Scale egg sprite to fit in cell
                        cell_size = min(rect.width, rect.height)
                        sprite_size = int(cell_size * 0.8)
                        egg_sprite = pygame.transform.smoothscale(egg_sprite, (sprite_size, sprite_size))
                        sprite_rect = egg_sprite.get_rect(center=rect.center)
                        surf.blit(egg_sprite, sprite_rect)
                    except:
                        # Fallback to text if sprite fails
                        try:
                            tiny_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 8)
                            text = "EGG"
                            text_surf = tiny_font.render(text, True, ui_colors.COLOR_TEXT)
                            text_rect = text_surf.get_rect(center=rect.center)
                            surf.blit(text_surf, text_rect)
                        except:
                            pass
                else:
                    # No egg sprite, show text
                    try:
                        tiny_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 8)
                        text = "EGG"
                        text_surf = tiny_font.render(text, True, ui_colors.COLOR_TEXT)
                        text_rect = text_surf.get_rect(center=rect.center)
                        surf.blit(text_surf, text_rect)
                    except:
                        pass
        
        # Draw scrollbar for Sinew mode
        if self.sinew_mode:
            self._draw_sinew_scrollbar(surf)
    
    def _draw_sinew_scrollbar(self, surf):
        """Draw scrollbar for Sinew storage's 120-slot boxes"""
        # Scrollbar position - inside right edge of grid
        scrollbar_width = 12
        scrollbar_x = self.grid_rect.right - scrollbar_width - 3
        scrollbar_y = self.grid_rect.top + 2
        scrollbar_height = self.grid_rect.height - 4
        
        # Background track
        track_rect = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)
        pygame.draw.rect(surf, (40, 40, 50, 200), track_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, track_rect, 1)
        
        # Calculate thumb size and position
        # Total rows = 20, visible rows = 5
        max_scroll = self.sinew_total_rows - self.sinew_visible_rows  # 15
        if max_scroll > 0:
            thumb_height = max(30, scrollbar_height * self.sinew_visible_rows // self.sinew_total_rows)
            thumb_travel = scrollbar_height - thumb_height
            thumb_y = scrollbar_y + int(thumb_travel * self.sinew_scroll_offset / max_scroll)
            
            # Draw thumb
            thumb_rect = pygame.Rect(scrollbar_x + 1, thumb_y, scrollbar_width - 2, thumb_height)
            pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, thumb_rect)
            pygame.draw.rect(surf, ui_colors.COLOR_HOVER_TEXT, thumb_rect, 1)
        
        # Draw row indicator text below grid
        try:
            tiny_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 8)
            start_row = self.sinew_scroll_offset + 1
            end_row = min(self.sinew_scroll_offset + self.sinew_visible_rows, self.sinew_total_rows)
            indicator_text = f"Rows {start_row}-{end_row}/{self.sinew_total_rows}"
            text_surf = tiny_font.render(indicator_text, True, ui_colors.COLOR_TEXT)
            text_rect = text_surf.get_rect(right=self.grid_rect.right, top=self.grid_rect.bottom + 3)
            surf.blit(text_surf, text_rect)
        except:
            pass

    # ------------------- Draw -------------------
    def draw(self, surf, dt=16):
        """
        Draw the PC box screen
        
        Args:
            surf: Surface to draw on
            dt: Delta time in milliseconds (for GIF animation)
        """
        
        # Background overlay (darken using theme BG color)
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        r, g, b = ui_colors.COLOR_BG[:3] if len(ui_colors.COLOR_BG) >= 3 else (50, 50, 50)
        overlay.fill((r, g, b, 180))
        surf.blit(overlay, (0,0))

        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, (0,0,self.width,self.height),2)
        
        # Draw "Game Running" warning banner if this game is being emulated
        warning_banner_height = 0
        if self.is_current_game_running():
            warning_banner_height = 25
            # Draw warning banner at top
            banner_rect = pygame.Rect(0, 0, self.width, warning_banner_height)
            # Dark error background using theme
            er, eg, eb = ui_colors.COLOR_ERROR[:3] if len(ui_colors.COLOR_ERROR) >= 3 else (255, 80, 80)
            pygame.draw.rect(surf, (er//3, eg//3, eb//3), banner_rect)
            pygame.draw.rect(surf, ui_colors.COLOR_ERROR, banner_rect, 1)
            
            try:
                warning_font = pygame.font.Font(None, 18)
                warning_text = f"âš  {self.get_current_game()} is running - transfers disabled"
                text_surf = warning_font.render(warning_text, True, ui_colors.COLOR_ERROR)
                text_rect = text_surf.get_rect(center=(self.width // 2, warning_banner_height // 2))
                surf.blit(text_surf, text_rect)
            except:
                pass

        # Sprite area - semi-transparent background to match grid
        sprite_bg = pygame.Surface((self.sprite_area.width, self.sprite_area.height), pygame.SRCALPHA)
        
        # Determine background color based on selection (using theme colors)
        if self.selected_pokemon and not self.selected_pokemon.get('empty'):
            # Pokemon/egg selected - brighter
            r, g, b = ui_colors.COLOR_BUTTON_HOVER[:3] if len(ui_colors.COLOR_BUTTON_HOVER) >= 3 else (80, 80, 100)
            bg_color = (r, g, b, 180)
        else:
            # Nothing selected - dimmer
            r, g, b = ui_colors.COLOR_BUTTON[:3] if len(ui_colors.COLOR_BUTTON) >= 3 else (60, 60, 60)
            bg_color = (r, g, b, 180)
        
        pygame.draw.rect(sprite_bg, bg_color, (0, 0, self.sprite_area.width, self.sprite_area.height))
        surf.blit(sprite_bg, self.sprite_area.topleft)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.sprite_area, 2)
        
        # Show selected Pokemon sprite if available
        if self.selected_pokemon and not self.selected_pokemon.get('empty'):
            # Check if it's an egg
            if self.selected_pokemon.get('egg'):
                # Show egg sprite (try PNG, then GIF)
                egg_png_path = "data/sprites/gen3/normal/egg.png"
                egg_gif_path = "data/sprites/showdown/normal/egg.gif"
                
                # Try gen3 PNG first
                if os.path.exists(egg_png_path):
                    try:
                        egg_sprite = pygame.image.load(egg_png_path).convert_alpha()
                        sprite_width = int(self.sprite_area.width * 0.9)
                        sprite_height = int(self.sprite_area.height * 0.9)
                        egg_sprite = pygame.transform.smoothscale(egg_sprite, (sprite_width, sprite_height))
                        rect = egg_sprite.get_rect(center=self.sprite_area.center)
                        surf.blit(egg_sprite, rect.topleft)
                    except:
                        pass
                # Fallback to showdown GIF
                elif os.path.exists(egg_gif_path):
                    sprite_width = int(self.sprite_area.width * 0.9)
                    sprite_height = int(self.sprite_area.height * 0.9)
                    
                    gif_sprite = self.sprite_cache.get_gif_sprite(
                        egg_gif_path,
                        size=(sprite_width, sprite_height)
                    )
                    
                    if gif_sprite and gif_sprite.loaded:
                        gif_sprite.update(dt)
                        gif_sprite.draw(surf, self.sprite_area)
                        self.current_gif_sprite = gif_sprite
            else:
                # Regular Pokemon - use GEN3 sprite (PNG) for the big display
                sprite_path = self._get_pokemon_sprite_path(self.selected_pokemon)
                if sprite_path and os.path.exists(sprite_path):
                    try:
                        # Load PNG sprite
                        poke_sprite = pygame.image.load(sprite_path).convert_alpha()
                        # Scale to fit display area
                        sprite_width = int(self.sprite_area.width * 0.9)
                        sprite_height = int(self.sprite_area.height * 0.9)
                        poke_sprite = pygame.transform.smoothscale(poke_sprite, (sprite_width, sprite_height))
                        rect = poke_sprite.get_rect(center=self.sprite_area.center)
                        surf.blit(poke_sprite, rect.topleft)
                    except:
                        # Fallback to cached image if loading fails
                        if self.current_sprite_image:
                            rect = self.current_sprite_image.get_rect(center=self.sprite_area.center)
                            surf.blit(self.current_sprite_image, rect.topleft)
                elif self.current_sprite_image:
                    rect = self.current_sprite_image.get_rect(center=self.sprite_area.center)
                    surf.blit(self.current_sprite_image, rect.topleft)
                
                # Draw ROM HACK overlay for Pokemon from ROM hacks
                if self.selected_pokemon.get('rom_hack'):
                    self._draw_rom_hack_overlay(surf, self.sprite_area, size='large')

        # Info area - show selected Pokemon info (semi-transparent like grid)
        info_bg = pygame.Surface((self.info_area.width, self.info_area.height), pygame.SRCALPHA)
        
        # Use same background color logic as sprite area (using theme colors)
        if self.selected_pokemon and not self.selected_pokemon.get('empty'):
            r, g, b = ui_colors.COLOR_BUTTON_HOVER[:3] if len(ui_colors.COLOR_BUTTON_HOVER) >= 3 else (80, 80, 100)
            info_bg_color = (r, g, b, 180)
        else:
            r, g, b = ui_colors.COLOR_BUTTON[:3] if len(ui_colors.COLOR_BUTTON) >= 3 else (60, 60, 60)
            info_bg_color = (r, g, b, 180)
        
        pygame.draw.rect(info_bg, info_bg_color, (0, 0, self.info_area.width, self.info_area.height))
        surf.blit(info_bg, self.info_area.topleft)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.info_area, 2)
        
        if self.selected_pokemon and not self.selected_pokemon.get('empty'):
            # Create slightly bigger font for info text
            try:
                info_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 14)
            except:
                info_font = self.font
            
            # Format name and info
            if self.selected_pokemon.get('egg'):
                lines = ["EGG"]
            else:
                nickname = self.selected_pokemon.get('nickname', '').strip()
                species_name = self.selected_pokemon.get('species_name', '').strip()
                level = self.selected_pokemon.get('level', 0)
                
                lines = []
                
                # If has nickname AND it's different from species name
                if nickname and species_name and nickname.upper() != species_name.upper():
                    lines.append(nickname)
                    lines.append(f"({species_name})")
                    lines.append(f"Lv.{level}")
                elif nickname:
                    lines.append(nickname)
                    lines.append(f"Lv.{level}")
                elif species_name:
                    lines.append(species_name)
                    lines.append(f"Lv.{level}")
                else:
                    lines.append("???")
                    lines.append(f"Lv.{level}")
            
            # Draw text lines with wrapping inside the info box
            try:
                padding = 8
                y_offset = self.info_area.y + padding
                line_height = 16
                
                for line in lines:
                    # Ensure text fits in the box width
                    max_width = self.info_area.width - (padding * 2)
                    
                    # Simple text wrapping - truncate if too long
                    text_surf = info_font.render(line, True, ui_colors.COLOR_TEXT)
                    
                    # If text is too wide, try to fit it
                    if text_surf.get_width() > max_width:
                        # Truncate with ellipsis
                        while len(line) > 3 and text_surf.get_width() > max_width:
                            line = line[:-1]
                            text_surf = info_font.render(line + "...", True, ui_colors.COLOR_TEXT)
                    
                    # Center horizontally in info area
                    text_x = self.info_area.x + (self.info_area.width - text_surf.get_width()) // 2
                    
                    # Make sure we don't overflow the box
                    if y_offset + line_height <= self.info_area.bottom - padding:
                        surf.blit(text_surf, (text_x, y_offset))
                        y_offset += line_height
                    else:
                        break  # Stop if we run out of space
            except Exception as e:
                pass
        elif self.sinew_mode:
            # Show Sinew storage stats when no Pokemon selected
            try:
                info_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 10)
                padding = 8
                y_offset = self.info_area.y + padding
                line_height = 14
                
                # Get storage stats
                if self.sinew_storage:
                    total_pokemon = self.sinew_storage.get_total_pokemon_count()
                    box_pokemon = self.sinew_storage.get_box_pokemon_count(self.box_index + 1)
                    max_capacity = 20 * 120  # 20 boxes * 120 slots
                    
                    lines = [
                        "SINEW STORAGE",
                        "",
                        f"This Box: {box_pokemon}/120",
                        f"Total: {total_pokemon}",
                        f"Capacity: {max_capacity}"
                    ]
                else:
                    lines = ["SINEW STORAGE", "", "Not loaded"]
                
                for line in lines:
                    if line == "":
                        y_offset += 4
                        continue
                    text_surf = info_font.render(line, True, ui_colors.COLOR_TEXT)
                    text_x = self.info_area.x + (self.info_area.width - text_surf.get_width()) // 2
                    if y_offset + line_height <= self.info_area.bottom - padding:
                        surf.blit(text_surf, (text_x, y_offset))
                        y_offset += line_height
            except:
                pass

        # ------------------- Draw Top Buttons -------------------
        # Draw Game button row (without highlighting arrows - they're not navigable)
        self.left_game_arrow.draw(surf, self.font)
        self.right_game_arrow.draw(surf, self.font)
        
        # Highlight game button if focused
        if self.focus_mode == 'game_button':
            highlight_rect = self.game_button.rect.inflate(4, 4)
            pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 3)
        self.game_button.draw(surf, self.font)
        
        # Draw Box button row
        self.left_box_arrow.draw(surf, self.font)
        self.right_box_arrow.draw(surf, self.font)
        
        # Highlight box button if focused
        if self.focus_mode == 'box_button':
            highlight_rect = self.box_button.rect.inflate(4, 4)
            pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 3)
        self.box_button.draw(surf, self.font)
        
        # Draw side buttons with focus indicators
        # Party button - disabled in Sinew mode
        if self.sinew_mode:
            # Draw disabled party button (dimmed theme colors)
            disabled_rect = self.party_button.rect
            r, g, b = ui_colors.COLOR_BUTTON[:3] if len(ui_colors.COLOR_BUTTON) >= 3 else (40, 40, 45)
            pygame.draw.rect(surf, (r//2, g//2, b//2), disabled_rect)
            pygame.draw.rect(surf, (r, g, b), disabled_rect, 2)
            try:
                btn_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 10)
                text = "No Party"
                # Dimmed text color
                tr, tg, tb = ui_colors.COLOR_TEXT[:3] if len(ui_colors.COLOR_TEXT) >= 3 else (80, 80, 90)
                text_surf = btn_font.render(text, True, (tr//2, tg//2, tb//2))
                text_rect = text_surf.get_rect(center=disabled_rect.center)
                surf.blit(text_surf, text_rect)
            except:
                pass
        else:
            if self.focus_mode == 'side_buttons' and self.side_button_index == 0:
                highlight_rect = self.party_button.rect.inflate(4, 4)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 3)
            self.party_button.draw(surf, self.font)
        
        # Close button (always at index 1 now)
        if self.focus_mode == 'side_buttons' and self.side_button_index == 1:
            highlight_rect = self.close_button.rect.inflate(4, 4)
            pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 3)
        self.close_button.draw(surf, self.font)
        
        # ------------------- Draw Undo Button (centered between sprite and grid) -------------------
        if self.undo_available:
            # Get top-left grid cell position
            grid_rects = self.get_grid_rects()
            if grid_rects:
                top_left_cell = grid_rects[0]
                
                # Calculate gap between sprite area and grid
                gap = top_left_cell.left - self.sprite_area.right
                
                # Position: centered in the gap, vertically aligned with top-left cell
                undo_size = 28
                undo_x = self.sprite_area.right + (gap - undo_size) // 2
                undo_y = top_left_cell.centery - undo_size // 2
                undo_rect = pygame.Rect(undo_x, undo_y, undo_size, undo_size)
                
                # Store rect for click detection
                self.undo_button_rect = undo_rect
                
                # Draw button background using theme colors
                is_undo_focused = (self.focus_mode == 'undo_button')
                if is_undo_focused:
                    pygame.draw.rect(surf, ui_colors.COLOR_BUTTON_HOVER, undo_rect)
                    pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, undo_rect, 3)
                else:
                    pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, undo_rect)
                    pygame.draw.rect(surf, ui_colors.COLOR_BORDER, undo_rect, 2)
                
                # Draw "U" text
                try:
                    undo_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 14)
                    u_surf = undo_font.render("U", True, ui_colors.COLOR_TEXT)
                    u_rect = u_surf.get_rect(center=undo_rect.center)
                    surf.blit(u_surf, u_rect)
                except:
                    pass
            else:
                self.undo_button_rect = None
        else:
            self.undo_button_rect = None

        # ------------------- Draw Grid -------------------
        self.draw_grid(surf)
        
        # ------------------- Draw Controller Hints -------------------
        try:
            hint_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 8)
            if self.sinew_mode:
                hints = "L/R: Scroll  A: Select  B: Back"
            elif self.party_panel_open:
                hints = "D-Pad: Move  A: Select  B: Close"
            else:
                hints = "L/R: Box  A: Select  B: Back"
            # Use dimmed theme text color
            tr, tg, tb = ui_colors.COLOR_TEXT[:3] if len(ui_colors.COLOR_TEXT) >= 3 else (120, 120, 120)
            hint_surf = hint_font.render(hints, True, (tr//2, tg//2, tb//2))
            surf.blit(hint_surf, (10, self.height - 15))
        except:
            pass

        # ------------------- Draw Party Panel -------------------
        # Smooth animation
        if self.party_panel_open and self.party_panel_rect.y < self.party_panel_target_y:
            self.party_panel_rect.y += self.party_panel_speed
            if self.party_panel_rect.y > self.party_panel_target_y:
                self.party_panel_rect.y = self.party_panel_target_y
        elif not self.party_panel_open and self.party_panel_rect.y > self.party_panel_target_y:
            self.party_panel_rect.y -= self.party_panel_speed
            if self.party_panel_rect.y < self.party_panel_target_y:
                self.party_panel_rect.y = self.party_panel_target_y

        if self.party_panel_rect.y > -self.height:
            # Make panel thinner (~40% smaller)
            panel_width = self.party_panel_rect.width * 0.7
            panel_rect = pygame.Rect(self.party_panel_rect.x, self.party_panel_rect.y, panel_width, self.party_panel_rect.height)

            # Top/bottom padding
            top_pad = 10
            bottom_pad = 10
            inner_height = panel_rect.height - top_pad - bottom_pad
            inner_y = panel_rect.y + top_pad

            # Draw solid background (same color as buttons)
            panel_bg = pygame.Surface((panel_rect.width, panel_rect.height))
            panel_bg.fill(ui_colors.COLOR_BUTTON)  # Match button color
            surf.blit(panel_bg, (panel_rect.x, panel_rect.y))

            # Draw border
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, panel_rect, 2)

            # Draw slots inside inner area with party data
            slots = self.get_party_slot_rects(inner_y=inner_y, inner_height=inner_height)
            for i, slot in enumerate(slots):
                # Get Pokemon if exists
                poke = self.party_data[i] if i < len(self.party_data) else None
                
                # Determine if this is the selected Pokemon
                is_selected = (poke and self.selected_pokemon and 
                              poke.get('species') == self.selected_pokemon.get('species') and
                              poke.get('personality') == self.selected_pokemon.get('personality'))
                
                # Check if this slot is controller-selected
                is_controller_selected = (i == self.party_selected and self.party_panel_open)
                
                # Base color for slot using theme colors
                if poke:
                    # Occupied slot - brighter
                    r, g, b = ui_colors.COLOR_BUTTON_HOVER[:3] if len(ui_colors.COLOR_BUTTON_HOVER) >= 3 else (80, 80, 100)
                    base_color = (r, g, b, 180)
                else:
                    # Empty slot - dimmer
                    r, g, b = ui_colors.COLOR_BUTTON[:3] if len(ui_colors.COLOR_BUTTON) >= 3 else (60, 60, 60)
                    base_color = (r, g, b, 180)
                
                # Draw slot background with transparency
                slot_surf = pygame.Surface((slot.width, slot.height), pygame.SRCALPHA)
                pygame.draw.rect(slot_surf, base_color, (0, 0, slot.width, slot.height))
                surf.blit(slot_surf, slot.topleft)
                
                # Draw border
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, slot, 2)
                
                # Highlight controller-selected slot
                if is_controller_selected:
                    pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, slot, 3)
                
                # Highlight selected Pokemon (yellow to distinguish from cursor)
                if is_selected and not is_controller_selected:
                    # Draw bright highlight border
                    pygame.draw.rect(surf, (255, 255, 100), slot, 3)
                
                # Draw Pokemon sprite (gen3) if available
                if poke:
                    
                    if not poke.get('egg'):
                        # Try to draw sprite - use helper that works for both game and Sinew
                        sprite_path = self._get_pokemon_sprite_path(poke)
                        if sprite_path and os.path.exists(sprite_path):
                            try:
                                sprite = self.sprite_cache.get_png_sprite(sprite_path, size=None)
                                if sprite:
                                    # Scale to fit slot with margin
                                    sprite_size = int(min(slot.width, slot.height) * 0.7)
                                    sprite = pygame.transform.smoothscale(sprite, (sprite_size, sprite_size))
                                    sprite_rect = sprite.get_rect(center=slot.center)
                                    surf.blit(sprite, sprite_rect)
                            except:
                                pass  # If sprite fails, fall back to text
                            
                            # Draw ROM HACK overlay for Pokemon from ROM hacks
                            if poke.get('rom_hack'):
                                self._draw_rom_hack_overlay(surf, slot, size='small')
                        else:
                            # No sprite, draw text instead
                            try:
                                text = self.manager.format_pokemon_display(poke)
                                tiny_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 10)
                                text_surf = tiny_font.render(text[:8], True, ui_colors.COLOR_TEXT)
                                text_rect = text_surf.get_rect(center=slot.center)
                                surf.blit(text_surf, text_rect)
                            except:
                                pass
                    else:
                        # Draw egg sprite for eggs
                        egg_path = "data/sprites/gen3/normal/egg.png"
                        if os.path.exists(egg_path):
                            try:
                                egg_sprite = self.sprite_cache.get_png_sprite(egg_path, size=None)
                                if egg_sprite:
                                    # Scale to fit slot with margin
                                    sprite_size = int(min(slot.width, slot.height) * 0.7)
                                    egg_sprite = pygame.transform.smoothscale(egg_sprite, (sprite_size, sprite_size))
                                    sprite_rect = egg_sprite.get_rect(center=slot.center)
                                    surf.blit(egg_sprite, sprite_rect)
                                else:
                                    raise Exception("Sprite cache failed")
                            except:
                                # Fallback to text if sprite fails
                                try:
                                    tiny_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 10)
                                    text_surf = tiny_font.render("EGG", True, ui_colors.COLOR_TEXT)
                                    text_rect = text_surf.get_rect(center=slot.center)
                                    surf.blit(text_surf, text_rect)
                                except:
                                    pass
                        else:
                            # No egg sprite, show text
                            try:
                                tiny_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 10)
                                text_surf = tiny_font.render("EGG", True, ui_colors.COLOR_TEXT)
                                text_rect = text_surf.get_rect(center=slot.center)
                                surf.blit(text_surf, text_rect)
                            except:
                                pass
        # Draw options menu overlay (on top of everything)
        self._draw_move_mode_overlay(surf)
        self._draw_options_menu(surf)
        self._draw_confirmation_dialog(surf)
        self._draw_evolution_dialog(surf)
        self._draw_altering_cave_dialog(surf)
        self._draw_warning_message(surf)
        
        # Draw sub_modal (summary screen) on top of everything
        if self.sub_modal:
            if hasattr(self.sub_modal, 'draw'):
                self.sub_modal.draw(surf)
    
    # ------------------- Overlay Drawing -------------------
    
    def _draw_move_mode_overlay(self, surf):
        """Draw the moving Pokemon sprite following cursor/selection"""
        if not self.move_mode or not self.moving_sprite:
            return
        
        # Draw "MOVE MODE" indicator at bottom
        try:
            font = pygame.font.Font("fonts/Pokemon_GB.ttf", 12)
            mode_text = font.render("MOVE MODE - Select empty slot", True, (255, 255, 100))
            text_rect = mode_text.get_rect(centerx=self.width // 2, bottom=self.height - 10)
            
            # Background for text
            bg_rect = text_rect.inflate(20, 10)
            pygame.draw.rect(surf, (0, 0, 0, 200), bg_rect)
            pygame.draw.rect(surf, (255, 255, 100), bg_rect, 2)
            surf.blit(mode_text, text_rect)
        except:
            pass
        
        # Draw sprite at current grid selection
        grid_index = self.grid_nav.get_selected()
        col = grid_index % self.grid_cols
        row = grid_index // self.grid_cols
        
        cell_w = self.grid_rect.width // self.grid_cols
        cell_h = self.grid_rect.height // self.grid_rows
        
        x = self.grid_rect.x + col * cell_w + cell_w // 2
        y = self.grid_rect.y + row * cell_h + cell_h // 2
        
        # Draw the sprite with slight offset and transparency effect
        sprite_rect = self.moving_sprite.get_rect(center=(x, y - 10))
        
        # Draw shadow
        shadow = pygame.Surface((40, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), (0, 0, 40, 20))
        surf.blit(shadow, (sprite_rect.centerx - 20, sprite_rect.bottom - 5))
        
        # Draw sprite
        surf.blit(self.moving_sprite, sprite_rect)
    
    def _draw_options_menu(self, surf):
        """Draw the options menu overlay"""
        if not self.options_menu_open:
            return
        
        
        # Menu dimensions
        menu_width = 120
        menu_height = len(self.options_menu_items) * 30 + 20
        menu_x = self.width // 2 - menu_width // 2
        menu_y = self.height // 2 - menu_height // 2
        
        # Draw menu background using theme colors
        menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, menu_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, menu_rect, 3)
        
        # Draw menu items
        try:
            font = pygame.font.Font("fonts/Pokemon_GB.ttf", 14)
            
            for i, item in enumerate(self.options_menu_items):
                item_y = menu_y + 15 + i * 30
                
                # Highlight selected item
                if i == self.options_menu_selected:
                    highlight_rect = pygame.Rect(menu_x + 5, item_y - 5, menu_width - 10, 28)
                    pygame.draw.rect(surf, ui_colors.COLOR_BUTTON_HOVER, highlight_rect)
                    pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 2)
                    
                    # Draw cursor
                    cursor = font.render(">", True, ui_colors.COLOR_HIGHLIGHT)
                    surf.blit(cursor, (menu_x + 10, item_y))
                
                # Draw item text
                text = font.render(item, True, ui_colors.COLOR_TEXT)
                surf.blit(text, (menu_x + 30, item_y))
        except:
            pass
    
    def _draw_confirmation_dialog(self, surf):
        """Draw the confirmation dialog overlay"""
        if not self.confirmation_dialog_open:
            return
        
        
        # Darken background
        dark_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 150))
        surf.blit(dark_overlay, (0, 0))
        
        # Dialog dimensions
        dialog_width = 300
        dialog_height = 140
        dialog_x = self.width // 2 - dialog_width // 2
        dialog_y = self.height // 2 - dialog_height // 2
        
        # Draw dialog background using theme colors
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, dialog_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, dialog_rect, 3)
        
        try:
            font = pygame.font.Font("fonts/Pokemon_GB.ttf", 12)
            small_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 14)
            
            # Draw message (multiline)
            lines = self.confirmation_dialog_message.split('\n')
            for i, line in enumerate(lines):
                text = font.render(line, True, ui_colors.COLOR_TEXT)
                text_rect = text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 15 + i * 20)
                surf.blit(text, text_rect)
            
            # Draw Yes/No buttons
            button_y = dialog_y + dialog_height - 40
            yes_x = dialog_x + dialog_width // 4
            no_x = dialog_x + 3 * dialog_width // 4
            
            # Yes button
            yes_rect = pygame.Rect(yes_x - 40, button_y - 5, 80, 30)
            if self.confirmation_selected == 0:
                pygame.draw.rect(surf, ui_colors.COLOR_SUCCESS, yes_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, yes_rect, 2)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, yes_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, yes_rect, 2)
            yes_text = small_font.render("YES", True, ui_colors.COLOR_TEXT)
            yes_text_rect = yes_text.get_rect(center=yes_rect.center)
            surf.blit(yes_text, yes_text_rect)
            
            # No button
            no_rect = pygame.Rect(no_x - 40, button_y - 5, 80, 30)
            if self.confirmation_selected == 1:
                pygame.draw.rect(surf, ui_colors.COLOR_ERROR, no_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, no_rect, 2)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, no_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, no_rect, 2)
            no_text = small_font.render("NO", True, ui_colors.COLOR_TEXT)
            no_text_rect = no_text.get_rect(center=no_rect.center)
            surf.blit(no_text, no_text_rect)
        except:
            pass
    
    def _draw_evolution_dialog(self, surf):
        """Draw the trade evolution dialog overlay"""
        if not self.evolution_dialog_open or not self.evolution_dialog_info:
            return
        
        
        # Darken background
        dark_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 180))
        surf.blit(dark_overlay, (0, 0))
        
        # Dialog dimensions
        dialog_width = 340
        dialog_height = 160
        dialog_x = self.width // 2 - dialog_width // 2
        dialog_y = self.height // 2 - dialog_height // 2
        
        # Draw dialog background using theme colors
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, dialog_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, dialog_rect, 3)
        
        try:
            font = pygame.font.Font("fonts/Pokemon_GB.ttf", 12)
            title_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 14)
            small_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 14)
            
            evo_info = self.evolution_dialog_info
            pokemon = self.evolution_dialog_pokemon
            
            # Get Pokemon name (nickname or species name)
            pokemon_name = pokemon.get('nickname') or evo_info['from_name']
            
            # Title
            title_text = title_font.render("What?", True, ui_colors.COLOR_HOVER_TEXT)
            title_rect = title_text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 12)
            surf.blit(title_text, title_rect)
            
            # Evolution message
            msg1 = f"{pokemon_name} is evolving!"
            msg1_text = font.render(msg1, True, ui_colors.COLOR_TEXT)
            msg1_rect = msg1_text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 40)
            surf.blit(msg1_text, msg1_rect)
            
            # Arrow and evolution target
            arrow_text = font.render(f"-> {evo_info['to_name']}", True, ui_colors.COLOR_SUCCESS)
            arrow_rect = arrow_text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 62)
            surf.blit(arrow_text, arrow_rect)
            
            # Item consumption message (if applicable)
            if evo_info.get('consumes_item') and evo_info.get('item_name'):
                item_msg = f"({evo_info['item_name']} will be used)"
                # Dimmed text
                tr, tg, tb = ui_colors.COLOR_TEXT[:3] if len(ui_colors.COLOR_TEXT) >= 3 else (180, 180, 180)
                item_text = font.render(item_msg, True, (tr*2//3, tg*2//3, tb*2//3))
                item_rect = item_text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 84)
                surf.blit(item_text, item_rect)
            
            # Draw Evolve/Stop buttons
            button_y = dialog_y + dialog_height - 40
            evolve_x = dialog_x + dialog_width // 4
            stop_x = dialog_x + 3 * dialog_width // 4
            
            # Evolve button
            evolve_rect = pygame.Rect(evolve_x - 50, button_y - 5, 100, 30)
            if self.evolution_selected == 0:
                pygame.draw.rect(surf, ui_colors.COLOR_SUCCESS, evolve_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, evolve_rect, 2)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, evolve_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, evolve_rect, 2)
            evolve_text = small_font.render("EVOLVE", True, ui_colors.COLOR_TEXT)
            evolve_text_rect = evolve_text.get_rect(center=evolve_rect.center)
            surf.blit(evolve_text, evolve_text_rect)
            
            # Stop button
            stop_rect = pygame.Rect(stop_x - 50, button_y - 5, 100, 30)
            if self.evolution_selected == 1:
                pygame.draw.rect(surf, ui_colors.COLOR_ERROR, stop_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, stop_rect, 2)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, stop_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, stop_rect, 2)
            stop_text = small_font.render("STOP", True, ui_colors.COLOR_TEXT)
            stop_text_rect = stop_text.get_rect(center=stop_rect.center)
            surf.blit(stop_text, stop_text_rect)
        except Exception as e:
            print(f"[PCBox] Error drawing evolution dialog: {e}")
    
    # ------------------- Altering Cave "Echoes" Feature -------------------
    
    def _is_altering_cave_zubat(self, pokemon):
        """
        Check if a Pokemon is a Zubat caught in Altering Cave.
        These special Zubats can be exchanged for the never-released Altering Cave Pokemon.
        
        Returns:
            bool: True if this is an Altering Cave Zubat eligible for exchange
        """
        if not pokemon or pokemon.get('empty') or pokemon.get('egg'):
            return False
        
        # Check species (must be Zubat = 41)
        species = pokemon.get('species', 0)
        if species != ALTERING_CAVE_ZUBAT_SPECIES:
            return False
        
        # Check met_location (must be Altering Cave - 183 or 210)
        met_location = pokemon.get('met_location', 0)
        
        if met_location not in ALTERING_CAVE_LOCATIONS:
            return False
        
        # Check if Altering Cave feature is complete
        if ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
            manager = get_achievement_manager()
            if manager and manager.is_altering_cave_complete():
                return False  # All 7 Pokemon already claimed
        
        return True
    
    def _show_altering_cave_dialog(self, pokemon, location_info):
        """
        Show the Altering Cave confirmation dialog.
        
        Args:
            pokemon: The Zubat Pokemon data
            location_info: Tuple of (box, slot) for Sinew, or (save_path, box, slot) for game
        """
        self.altering_cave_dialog_open = True
        self.altering_cave_zubat = pokemon
        self.altering_cave_location = location_info
        self.altering_cave_selected = 0  # Default to "Yes"
        
        # Debug output
        if len(location_info) == 2:
            box, slot = location_info
            print(f"[PCBox] Altering Cave dialog - Sinew: box_index={box} (Box {box+1}), slot={slot}")
        else:
            save_path, box, slot = location_info
            print(f"[PCBox] Altering Cave dialog - Game: box_index={box} (Box {box+1}), slot={slot}, current self.box_index={self.box_index}")
    
    def _close_altering_cave_dialog(self):
        """Close the Altering Cave dialog without doing anything."""
        self.altering_cave_dialog_open = False
        self.altering_cave_zubat = None
        self.altering_cave_location = None
    
    def _start_altering_cave_spinner(self):
        """Start the slot machine spinner for Altering Cave Pokemon."""
        # Get remaining Pokemon that can be won
        if ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
            manager = get_achievement_manager()
            remaining = manager.get_altering_cave_remaining()
        else:
            remaining = ALTERING_CAVE_POKEMON.copy()
        
        if not remaining:
            self.warning_message = "All Altering Cave Pokemon already claimed!"
            self.warning_message_timer = self.warning_message_duration
            self._close_altering_cave_dialog()
            return
        
        self.altering_cave_spinner_active = True
        self.altering_cave_spinner_speed = 25.0  # Initial speed
        self.altering_cave_spinner_offset = 0.0
        self.altering_cave_spinner_stopped = False
        self.altering_cave_spinner_show_result = False
        self.altering_cave_spinner_result = None
        self.altering_cave_remaining = remaining  # Store for drawing
        
        # Pre-select result and calculate target offset to land on it
        import random
        result_index = random.randint(0, len(remaining) - 1)
        self.altering_cave_spinner_result = remaining[result_index]
        
        # Calculate target offset so spinner lands on this Pokemon
        # Item height is 56 (matches drawing code), we want the result centered
        item_height = 56
        # Add some full rotations (3-5 spins) plus offset to land on result
        full_rotations = random.randint(3, 5) * len(remaining) * item_height
        target_offset = full_rotations + (result_index * item_height)
        self.altering_cave_target_offset = target_offset
        
        print(f"[PCBox] Altering Cave spinner started - result will be: {self.altering_cave_spinner_result['name']} (index {result_index})")
    
    def _update_altering_cave_spinner(self, dt):
        """Update the spinner animation."""
        if not self.altering_cave_spinner_active:
            return
        
        if self.altering_cave_spinner_show_result:
            # Waiting for player to acknowledge result
            return
        
        if self.altering_cave_spinner_stopped:
            # Already stopped, waiting for result timer
            return
        
        # Calculate remaining distance to target
        remaining_distance = self.altering_cave_target_offset - self.altering_cave_spinner_offset
        
        if remaining_distance <= 0:
            # Reached target - snap to exact position
            self.altering_cave_spinner_offset = self.altering_cave_target_offset
            self.altering_cave_spinner_speed = 0
            self.altering_cave_spinner_stopped = True
            self.altering_cave_result_timer = 45  # Delay before showing result text
            return
        
        # Ease out - slow down as we approach target
        # Speed is proportional to remaining distance, with a minimum
        if remaining_distance < 200:
            self.altering_cave_spinner_speed = max(1.0, remaining_distance / 15)
        elif remaining_distance < 500:
            self.altering_cave_spinner_speed = max(3.0, remaining_distance / 30)
        else:
            self.altering_cave_spinner_speed = min(25.0, remaining_distance / 40)
        
        # Update offset based on speed
        self.altering_cave_spinner_offset += self.altering_cave_spinner_speed * (dt / 16.0)
    
    def _complete_altering_cave_exchange(self):
        """
        Complete the Altering Cave exchange - replace Zubat with won Pokemon.
        """
        if not self.altering_cave_spinner_result or not self.altering_cave_location:
            return
        
        result_pokemon = self.altering_cave_spinner_result
        
        # Load the .pks file for the won Pokemon
        rewards_path = os.path.join("data", "achievements", "rewards")
        pks_path = os.path.join(rewards_path, result_pokemon['file'])
        
        if not os.path.exists(pks_path):
            print(f"[PCBox] ERROR: Reward file not found: {pks_path}")
            self.warning_message = f"Error: {result_pokemon['name']} file not found!"
            self.warning_message_timer = self.warning_message_duration
            self._close_altering_cave_spinner()
            return
        
        try:
            # Read the .pks file
            with open(pks_path, 'rb') as f:
                pks_data = f.read()
            
            print(f"[PCBox] Loaded {result_pokemon['name']} pks file: {len(pks_data)} bytes")
            
            # Parse the .pks data into a Pokemon dict
            pokemon_dict = None
            try:
                from pokemon import parse_pc_pokemon
                pokemon_dict = parse_pc_pokemon(pks_data)
                pokemon_dict['raw_bytes'] = pks_data  # Keep raw bytes for storage
                print(f"[PCBox] Parsed Pokemon: species={pokemon_dict.get('species')}, name={pokemon_dict.get('species_name')}")
            except Exception as e:
                print(f"[PCBox] Could not parse pks file: {e}")
                pokemon_dict = {
                    'species': result_pokemon['species'],
                    'nickname': result_pokemon['name'].upper(),
                    'species_name': result_pokemon['name'],
                    'raw_bytes': pks_data
                }
            
            # Determine location type
            location = self.altering_cave_location
            print(f"[PCBox] Exchange location tuple: {location}")
            
            if len(location) == 2:
                # Sinew storage: (box, slot) - box is 0-indexed, slot is actual slot index
                box, slot = location
                print(f"[PCBox] Sinew mode: box_index={box} (Box {box+1}), slot={slot}")
                if SINEW_STORAGE_AVAILABLE and get_sinew_storage:
                    storage = get_sinew_storage()
                    # set_pokemon_at expects 1-indexed box number
                    success = storage.set_pokemon_at(box + 1, slot, pokemon_dict)
                    if success:
                        print(f"[PCBox] SUCCESS: Replaced Zubat with {result_pokemon['name']} in Sinew box {box+1} slot {slot}")
                    else:
                        print(f"[PCBox] ERROR: Failed to store in Sinew storage")
                        self.warning_message = "Error saving to Sinew storage!"
                        self.warning_message_timer = self.warning_message_duration
            else:
                # Game save: (save_path, box, slot) - box is 0-indexed
                save_path, box, slot = location
                print(f"[PCBox] Game save mode: box_index={box} (will write to Box {box+1}), slot={slot}")
                if SAVE_WRITER_AVAILABLE:
                    save_data = load_save_file(save_path)
                    if save_data:
                        # write_pokemon_to_pc expects 1-indexed box (1-14), 0-indexed slot
                        print(f"[PCBox] Calling write_pokemon_to_pc(save_data, box={box+1}, slot={slot}, ...)")
                        write_pokemon_to_pc(save_data, box + 1, slot, pks_data)
                        write_save_file(save_path, save_data)
                        print(f"[PCBox] SUCCESS: Replaced Zubat with {result_pokemon['name']} in game box {box+1} slot {slot}")
                    else:
                        print(f"[PCBox] ERROR: Could not load save file")
                        self.warning_message = "Error loading save file!"
                        self.warning_message_timer = self.warning_message_duration
            
            # Mark this Pokemon as claimed in achievements
            if ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
                manager = get_achievement_manager()
                manager.claim_altering_cave_pokemon(result_pokemon['species'])
            
            # Show success message
            self.warning_message = f"Obtained {result_pokemon['name']}!"
            self.warning_message_timer = self.warning_message_duration * 2  # Show longer
            
            # Refresh display
            self.refresh_data()
            
        except Exception as e:
            print(f"[PCBox] Error completing Altering Cave exchange: {e}")
            import traceback
            traceback.print_exc()
            self.warning_message = "Error during exchange!"
            self.warning_message_timer = self.warning_message_duration
        
        self._close_altering_cave_spinner()
    
    def _close_altering_cave_spinner(self):
        """Close the spinner and reset state."""
        self.altering_cave_spinner_active = False
        self.altering_cave_spinner_result = None
        self.altering_cave_spinner_stopped = False
        self.altering_cave_spinner_show_result = False
        self.altering_cave_target_offset = 0
        self.altering_cave_remaining = []
        self.altering_cave_dialog_open = False
        self.altering_cave_zubat = None
        self.altering_cave_location = None
    
    def _draw_altering_cave_dialog(self, surf):
        """Draw the Altering Cave confirmation dialog or spinner."""
        # Update pulse timer
        self._altering_cave_pulse_timer = (self._altering_cave_pulse_timer + 1) % 60
        
        if not self.altering_cave_dialog_open:
            return
        
        if self.altering_cave_spinner_active:
            self._draw_altering_cave_spinner(surf)
            return
        
        # Darken background
        dark_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 180))
        surf.blit(dark_overlay, (0, 0))
        
        # Dialog dimensions
        dialog_width = 380
        dialog_height = 180
        dialog_x = self.width // 2 - dialog_width // 2
        dialog_y = self.height // 2 - dialog_height // 2
        
        # Draw dialog background with mystical purple tint
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        # Purple-ish background
        pygame.draw.rect(surf, (40, 30, 60), dialog_rect)
        pygame.draw.rect(surf, (150, 100, 200), dialog_rect, 3)
        
        try:
            font = pygame.font.Font("fonts/Pokemon_GB.ttf", 11)
            title_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 13)
            small_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 12)
            
            # Title with wavy effect
            title_text = title_font.render("~ Echoes ~", True, (200, 150, 255))
            title_rect = title_text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 12)
            surf.blit(title_text, title_rect)
            
            # Message lines
            msg1 = "This Zubat from Altering Cave"
            msg2 = "carries echoes of what never was..."
            msg3 = "Care to try your luck?"
            
            msg1_text = font.render(msg1, True, (220, 220, 255))
            msg1_rect = msg1_text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 45)
            surf.blit(msg1_text, msg1_rect)
            
            msg2_text = font.render(msg2, True, (180, 180, 220))
            msg2_rect = msg2_text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 65)
            surf.blit(msg2_text, msg2_rect)
            
            msg3_text = font.render(msg3, True, (255, 255, 200))
            msg3_rect = msg3_text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 95)
            surf.blit(msg3_text, msg3_rect)
            
            # Progress indicator
            if ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
                manager = get_achievement_manager()
                claimed = len(manager.get_altering_cave_claimed())
                progress_text = font.render(f"({claimed}/7 discovered)", True, (150, 150, 180))
                progress_rect = progress_text.get_rect(centerx=dialog_x + dialog_width // 2, top=dialog_y + 115)
                surf.blit(progress_text, progress_rect)
            
            # Draw Yes/No buttons
            button_y = dialog_y + dialog_height - 40
            yes_x = dialog_x + dialog_width // 4
            no_x = dialog_x + 3 * dialog_width // 4
            
            # Yes button
            yes_rect = pygame.Rect(yes_x - 50, button_y - 5, 100, 30)
            if self.altering_cave_selected == 0:
                pygame.draw.rect(surf, (100, 80, 180), yes_rect)
                pygame.draw.rect(surf, (200, 150, 255), yes_rect, 2)
            else:
                pygame.draw.rect(surf, (50, 40, 80), yes_rect)
                pygame.draw.rect(surf, (100, 80, 150), yes_rect, 2)
            yes_text = small_font.render("YES", True, (255, 255, 255))
            yes_text_rect = yes_text.get_rect(center=yes_rect.center)
            surf.blit(yes_text, yes_text_rect)
            
            # No button
            no_rect = pygame.Rect(no_x - 50, button_y - 5, 100, 30)
            if self.altering_cave_selected == 1:
                pygame.draw.rect(surf, (80, 60, 60), no_rect)
                pygame.draw.rect(surf, (180, 100, 100), no_rect, 2)
            else:
                pygame.draw.rect(surf, (50, 40, 50), no_rect)
                pygame.draw.rect(surf, (100, 80, 100), no_rect, 2)
            no_text = small_font.render("NO", True, (255, 255, 255))
            no_text_rect = no_text.get_rect(center=no_rect.center)
            surf.blit(no_text, no_text_rect)
        except Exception as e:
            print(f"[PCBox] Error drawing Altering Cave dialog: {e}")
    
    def _draw_altering_cave_spinner(self, surf):
        """Draw the slot machine spinner for Altering Cave Pokemon."""
        # Darken background
        dark_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 200))
        surf.blit(dark_overlay, (0, 0))
        
        # Spinner dimensions - more compact to fit screen
        spinner_width = 220
        spinner_height = 260
        spinner_x = self.width // 2 - spinner_width // 2
        spinner_y = self.height // 2 - spinner_height // 2 + 10  # Slight offset down
        
        # Ensure it doesn't go off screen
        spinner_y = max(10, spinner_y)
        
        # Draw spinner frame (slot machine style)
        frame_rect = pygame.Rect(spinner_x, spinner_y, spinner_width, spinner_height)
        pygame.draw.rect(surf, (30, 20, 50), frame_rect)
        pygame.draw.rect(surf, (150, 100, 200), frame_rect, 3)
        
        try:
            title_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 10)
            font = pygame.font.Font("fonts/Pokemon_GB.ttf", 9)
            
            # Title - inside the frame
            title = title_font.render("WHAT NEVER WAS", True, (200, 150, 255))
            title_rect = title.get_rect(centerx=spinner_x + spinner_width // 2, top=spinner_y + 10)
            surf.blit(title, title_rect)
            
            # Reel window (center area where Pokemon scroll)
            window_width = 140
            window_height = 140
            window_x = spinner_x + (spinner_width - window_width) // 2
            window_y = spinner_y + 35
            window_rect = pygame.Rect(window_x, window_y, window_width, window_height)
            
            # Window background
            pygame.draw.rect(surf, (20, 15, 35), window_rect)
            pygame.draw.rect(surf, (100, 70, 150), window_rect, 2)
            
            # Get Pokemon list for display
            remaining = getattr(self, 'altering_cave_remaining', [])
            if not remaining:
                if ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
                    manager = get_achievement_manager()
                    remaining = manager.get_altering_cave_remaining()
                else:
                    remaining = ALTERING_CAVE_POKEMON.copy()
            
            if remaining:
                item_height = 56  # Height per Pokemon sprite
                total_height = len(remaining) * item_height
                
                # Wrap offset for continuous scrolling
                wrapped_offset = self.altering_cave_spinner_offset % total_height
                
                center_y = window_y + window_height // 2
                
                # Create a clipping surface for the window
                clip_surf = pygame.Surface((window_width - 4, window_height - 4), pygame.SRCALPHA)
                clip_surf.fill((20, 15, 35, 255))  # Match window background
                
                # Draw enough Pokemon to fill the window
                for i in range(-3, 5):
                    # Calculate which Pokemon index this is
                    poke_index = int((wrapped_offset // item_height) + i) % len(remaining)
                    poke = remaining[poke_index]
                    
                    # Calculate y position relative to clip surface
                    base_y = (window_height - 4) // 2 + (i * item_height)
                    offset_in_item = wrapped_offset % item_height
                    y_pos = base_y - offset_in_item
                    
                    # Get sprite - try multiple paths
                    species_id = poke['species']
                    species_str = str(species_id).zfill(3)
                    
                    sprite = None
                    sprite_paths = [
                        f"data/sprites/gen3/normal/{species_str}.png",
                        f"data/sprites/gen3/{species_str}.png",
                        f"sprites/gen3/normal/{species_str}.png",
                    ]
                    
                    for sprite_path in sprite_paths:
                        if os.path.exists(sprite_path):
                            try:
                                sprite = pygame.image.load(sprite_path).convert_alpha()
                                # Scale to 48x48
                                sprite = pygame.transform.scale(sprite, (48, 48))
                                break
                            except Exception as e:
                                continue
                    
                    if sprite:
                        sprite_rect = sprite.get_rect(center=((window_width - 4) // 2, int(y_pos)))
                        clip_surf.blit(sprite, sprite_rect)
                    else:
                        # Fallback: draw Pokemon name
                        name_text = font.render(poke['name'], True, (200, 200, 255))
                        name_rect = name_text.get_rect(center=((window_width - 4) // 2, int(y_pos)))
                        clip_surf.blit(name_text, name_rect)
                
                # Blit the clipped surface
                surf.blit(clip_surf, (window_x + 2, window_y + 2))
                
                # Draw selection indicator arrows on sides
                indicator_y = center_y
                # Left arrow
                arrow_points_l = [
                    (window_x - 12, indicator_y),
                    (window_x - 4, indicator_y - 8),
                    (window_x - 4, indicator_y + 8)
                ]
                pygame.draw.polygon(surf, (255, 200, 100), arrow_points_l)
                # Right arrow
                arrow_points_r = [
                    (window_x + window_width + 12, indicator_y),
                    (window_x + window_width + 4, indicator_y - 8),
                    (window_x + window_width + 4, indicator_y + 8)
                ]
                pygame.draw.polygon(surf, (255, 200, 100), arrow_points_r)
                
                # Horizontal lines above and below center slot
                line_color = (255, 200, 100)
                pygame.draw.line(surf, line_color, 
                               (window_x + 3, indicator_y - item_height // 2), 
                               (window_x + window_width - 3, indicator_y - item_height // 2), 2)
                pygame.draw.line(surf, line_color, 
                               (window_x + 3, indicator_y + item_height // 2), 
                               (window_x + window_width - 3, indicator_y + item_height // 2), 2)
            
            # Status text area
            if self.altering_cave_spinner_stopped:
                if self.altering_cave_result_timer > 0:
                    self.altering_cave_result_timer -= 1
                elif not self.altering_cave_spinner_show_result:
                    self.altering_cave_spinner_show_result = True
            
            status_y = spinner_y + spinner_height - 65
            
            if self.altering_cave_spinner_show_result and self.altering_cave_spinner_result:
                # Show result with sprite
                result = self.altering_cave_spinner_result
                result_name = result['name']
                
                # Draw result Pokemon name
                result_text = title_font.render(f"{result_name}!", True, (100, 255, 100))
                result_rect = result_text.get_rect(centerx=spinner_x + spinner_width // 2, top=status_y)
                surf.blit(result_text, result_rect)
                
                # Press A prompt
                prompt_text = font.render("Press A", True, (200, 200, 200))
                prompt_rect = prompt_text.get_rect(centerx=spinner_x + spinner_width // 2, top=status_y + 20)
                surf.blit(prompt_text, prompt_rect)
            elif self.altering_cave_spinner_speed > 0:
                spin_text = font.render("Spinning...", True, (255, 255, 200))
                spin_rect = spin_text.get_rect(centerx=spinner_x + spinner_width // 2, top=status_y + 10)
                surf.blit(spin_text, spin_rect)
            elif not self.altering_cave_spinner_stopped:
                wait_text = font.render("...", True, (200, 200, 200))
                wait_rect = wait_text.get_rect(centerx=spinner_x + spinner_width // 2, top=status_y + 10)
                surf.blit(wait_text, wait_rect)
                
        except Exception as e:
            print(f"[PCBox] Error drawing spinner: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_altering_cave_pulse_color(self):
        """Get the current pulse color for Altering Cave Zubat borders."""
        # Oscillate between purple shades
        t = self._altering_cave_pulse_timer / 60.0
        import math
        pulse = (math.sin(t * math.pi * 2) + 1) / 2  # 0 to 1
        
        r = int(100 + pulse * 100)  # 100-200
        g = int(50 + pulse * 50)    # 50-100
        b = int(150 + pulse * 105)  # 150-255
        
        return (r, g, b)
    
    def _draw_warning_message(self, surf):
        """Draw warning message popup"""
        if not self.warning_message or self.warning_message_timer <= 0:
            self.warning_message = None
            return
        
        
        # Decrement timer
        self.warning_message_timer -= 1
        
        # Calculate fade out for last 30 frames
        alpha = 255
        if self.warning_message_timer < 30:
            alpha = int(255 * (self.warning_message_timer / 30))
        
        # Warning box dimensions
        warning_width = 280
        lines = self.warning_message.split('\n')
        warning_height = 30 + len(lines) * 22
        warning_x = self.width // 2 - warning_width // 2
        warning_y = self.height // 2 - warning_height // 2
        
        # Create semi-transparent surface
        warning_surf = pygame.Surface((warning_width, warning_height), pygame.SRCALPHA)
        
        # Draw warning background using theme error colors
        er, eg, eb = ui_colors.COLOR_ERROR[:3] if len(ui_colors.COLOR_ERROR) >= 3 else (255, 80, 80)
        pygame.draw.rect(warning_surf, (er//3, eg//3, eb//3, alpha), (0, 0, warning_width, warning_height))
        pygame.draw.rect(warning_surf, (er, eg, eb, alpha), (0, 0, warning_width, warning_height), 3)
        
        try:
            font = pygame.font.Font("fonts/Pokemon_GB.ttf", 12)
            
            # Draw warning text
            for i, line in enumerate(lines):
                text = font.render(line, True, ui_colors.COLOR_ERROR)
                text.set_alpha(alpha)
                text_rect = text.get_rect(centerx=warning_width // 2, top=15 + i * 22)
                warning_surf.blit(text, text_rect)
        except:
            pass
        
        surf.blit(warning_surf, (warning_x, warning_y))