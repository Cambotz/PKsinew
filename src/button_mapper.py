"""
Sinew Button Mapper
Visual GBA-style button mapping screen with controller support

Now integrates with the controller_profiles system:
- Shows the detected profile name on the GBA screen
- Saves mappings per-controller (keyed by controller name)
- "Reset to Default" resets to the auto-detected profile, not just Xbox
"""

import pygame
import json
import os
from ui_colors import *


class ButtonMapper:
    """
    Button mapping screen with GBA visual layout
    
    Features:
    - Visual GBA representation showing current mappings
    - Individual button rebinding with 5-second timeout
    - Quick Setup mode for sequential rebinding
    - Duplicate binding prevention
    - Per-controller profile saving via controller_profiles
    """
    
    # Default button mappings (button name -> binding value)
    # Face/shoulder buttons: list of controller button indices [int, ...]
    # D-pad: dict with source type and values
    DEFAULT_MAPPING = {
        'A': [0],
        'B': [1],
        'L': [4],
        'R': [5],
        'SELECT': [6],
        'START': [7],
        'DPAD_UP': {'source': 'hat', 'hat': 0, 'axis': 'y', 'value': 1},
        'DPAD_DOWN': {'source': 'hat', 'hat': 0, 'axis': 'y', 'value': -1},
        'DPAD_LEFT': {'source': 'hat', 'hat': 0, 'axis': 'x', 'value': -1},
        'DPAD_RIGHT': {'source': 'hat', 'hat': 0, 'axis': 'x', 'value': 1},
    }
    
    # Buttons available for rebinding (in Quick Setup order)
    # D-pad directions are included so users can fix mixed-up dpads
    BINDABLE_BUTTONS = ['DPAD_UP', 'DPAD_DOWN', 'DPAD_LEFT', 'DPAD_RIGHT',
                        'A', 'B', 'L', 'R', 'START', 'SELECT']
    
    # Friendly names for Quick Setup prompts
    BUTTON_DISPLAY_NAMES = {
        'DPAD_UP': 'D-Pad Up',
        'DPAD_DOWN': 'D-Pad Down',
        'DPAD_LEFT': 'D-Pad Left',
        'DPAD_RIGHT': 'D-Pad Right',
        'A': 'A (Confirm)',
        'B': 'B (Back)',
        'L': 'L Shoulder',
        'R': 'R Shoulder',
        'START': 'Start',
        'SELECT': 'Select',
    }
    
    # Button positions on the GBA visual (relative to GBA rect)
    # Format: button_name -> (x_ratio, y_ratio) from top-left of GBA
    BUTTON_POSITIONS = {
        'DPAD_UP':    (0.18, 0.32),
        'DPAD_DOWN':  (0.18, 0.52),
        'DPAD_LEFT':  (0.10, 0.42),
        'DPAD_RIGHT': (0.26, 0.42),
        'A':          (0.82, 0.35),  # Right button
        'B':          (0.72, 0.50),  # Left button (classic GBA layout)
        'L':          (0.12, 0.08),
        'R':          (0.88, 0.08),
        'SELECT':     (0.38, 0.70),
        'START':      (0.52, 0.70),
    }
    
    # Button display sizes (width, height) as ratios of GBA width
    BUTTON_SIZES = {
        'DPAD_UP':    (0.07, 0.09),
        'DPAD_DOWN':  (0.07, 0.09),
        'DPAD_LEFT':  (0.09, 0.07),
        'DPAD_RIGHT': (0.09, 0.07),
        'A':          (0.09, 0.09),
        'B':          (0.09, 0.09),
        'L':          (0.14, 0.05),
        'R':          (0.14, 0.05),
        'SELECT':     (0.09, 0.04),
        'START':      (0.09, 0.04),
    }
    
    CONFIG_FILE = "sinew_settings.json"
    CONFIG_KEY = "controller_mapping"
    
    def __init__(self, width, height, close_callback=None, controller=None):
        self.width = width
        self.height = height
        self.close_callback = close_callback
        self.controller = controller
        self.visible = True
        
        # Fonts
        try:
            self.font_header = pygame.font.Font("fonts/Pokemon_GB.ttf", 16)
            self.font_text = pygame.font.Font("fonts/Pokemon_GB.ttf", 11)
            self.font_small = pygame.font.Font("fonts/Pokemon_GB.ttf", 9)
            self.font_tiny = pygame.font.Font("fonts/Pokemon_GB.ttf", 7)
        except:
            self.font_header = pygame.font.SysFont(None, 22)
            self.font_text = pygame.font.SysFont(None, 16)
            self.font_small = pygame.font.SysFont(None, 14)
            self.font_tiny = pygame.font.SysFont(None, 11)
        
        # Get profile info from controller manager (if available)
        self._profile_info = None
        self._controller_name = None
        self._controller_guid = None
        if self.controller:
            self._profile_info = self.controller.get_profile_info()
            self._controller_name = self.controller.get_controller_name()
            self._controller_guid = self.controller.get_controller_guid()
        
        # Get the detected profile's base mapping for "Reset to Default"
        self._detected_default_mapping = self._get_detected_default()
        
        # Load or create mapping - start from the controller's CURRENT mapping
        # (which was set by auto-detection) rather than loading from file separately
        self.mapping = self._load_mapping()
        
        # Sync with controller's current mapping if available
        if self.controller:
            for btn in ['A', 'B', 'L', 'R', 'SELECT', 'START']:
                if btn in self.controller.button_map:
                    self.mapping[btn] = self.controller.button_map[btn].copy()
            
            # Try to load saved dpad bindings from per-controller profile
            self._sync_dpad_from_profile()
        
        # Navigation
        self.button_list = list(self.BUTTON_POSITIONS.keys())
        self.selected_index = 0
        self.menu_items = ['Quick Setup', 'Reset to Default', 'Save & Close']
        self.menu_selected = -1  # -1 = buttons selected, 0+ = menu selected
        self.in_menu = False
        
        # Rebinding state
        self.listening = False
        self.listening_button = None
        self.listen_start_time = 0
        self.listen_timeout = 5.0  # seconds
        
        # Quick setup state
        self.quick_setup_active = False
        self.quick_setup_index = 0
        
        # Status message (shows bind success, duplicates cleared, etc.)
        self.status_message = ""
        self.status_time = 0
        self.status_duration = 2.0  # seconds to show message
        self.status_color = COLOR_TEXT
        
        # Calculate GBA visual rect (centered, sized to leave room for menu)
        gba_width = int(width * 0.80)
        gba_height = int(gba_width * 0.50)  # GBA aspect ratio
        self.gba_rect = pygame.Rect(
            (width - gba_width) // 2,
            40,
            gba_width,
            gba_height
        )
        
        # Screen area (the "display" part of the GBA)
        screen_margin = 0.08
        self.screen_rect = pygame.Rect(
            self.gba_rect.x + int(gba_width * 0.30),
            self.gba_rect.y + int(gba_height * 0.15),
            int(gba_width * 0.40),
            int(gba_height * 0.55)
        )
        
        # Pre-calculate button rects
        self._calculate_button_rects()
        
        # Menu position - ensure it fits on screen with room for hints
        self.menu_y = self.gba_rect.bottom + 8
        # Calculate if menu would go off screen (3 items * 26px + hints)
        menu_bottom = self.menu_y + (len(self.menu_items) * 26) + 25
        if menu_bottom > height:
            # Push menu up
            self.menu_y = height - (len(self.menu_items) * 26) - 28
    
    def _get_detected_default(self):
        """Get the auto-detected profile mapping as the 'default' for reset.
        
        If the controller_profiles module is available and a profile was detected,
        use that. Otherwise fall back to the hardcoded DEFAULT_MAPPING.
        """
        try:
            from controller_profiles import identify_controller
            if self.controller and self.controller.is_connected():
                name = self.controller.get_controller_name()
                guid = self.controller.get_controller_guid()
                joy = self.controller.active_controller
                result = identify_controller(
                    name, guid,
                    joy.get_numbuttons(),
                    joy.get_numaxes(),
                    joy.get_numhats()
                )
                if result and result.get("mapping"):
                    # Merge with DEFAULT_MAPPING to keep DPAD entries
                    merged = dict(self.DEFAULT_MAPPING)
                    merged.update(result["mapping"])
                    return merged
        except Exception as e:
            print(f"[ButtonMapper] Could not get detected default: {e}")
        
        return dict(self.DEFAULT_MAPPING)
    
    def _sync_dpad_from_profile(self):
        """Load saved d-pad bindings from per-controller profile.
        
        The controller_profiles system stores d-pad bindings as
        _dpad_bindings in the mapping dict. Load these back so
        the ButtonMapper displays the correct current bindings.
        """
        try:
            from controller_profiles import load_saved_profile
            if self._controller_name:
                saved = load_saved_profile(self._controller_name, self._controller_guid)
                if saved and isinstance(saved, dict):
                    mapping = saved.get("mapping", {})
                    dpad_bindings = mapping.get("_dpad_bindings", {})
                    if dpad_bindings:
                        for dpad_key in ['DPAD_UP', 'DPAD_DOWN', 'DPAD_LEFT', 'DPAD_RIGHT']:
                            if dpad_key in dpad_bindings:
                                self.mapping[dpad_key] = dpad_bindings[dpad_key]
                        print(f"[ButtonMapper] Loaded saved d-pad bindings")
                        return
        except Exception as e:
            print(f"[ButtonMapper] Could not load dpad from profile: {e}")
        
        # Also check legacy flat mapping for dpad bindings
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    legacy = data.get(self.CONFIG_KEY, {})
                    for dpad_key in ['DPAD_UP', 'DPAD_DOWN', 'DPAD_LEFT', 'DPAD_RIGHT']:
                        if dpad_key in legacy and isinstance(legacy[dpad_key], dict):
                            self.mapping[dpad_key] = legacy[dpad_key]
        except Exception:
            pass
    
    def _calculate_button_rects(self):
        """Pre-calculate button rectangles on the GBA visual"""
        self.button_rects = {}
        gba_w = self.gba_rect.width
        gba_h = self.gba_rect.height
        
        for btn_name, (x_ratio, y_ratio) in self.BUTTON_POSITIONS.items():
            w_ratio, h_ratio = self.BUTTON_SIZES[btn_name]
            
            w = int(gba_w * w_ratio)
            h = int(gba_h * h_ratio)
            x = self.gba_rect.x + int(gba_w * x_ratio) - w // 2
            y = self.gba_rect.y + int(gba_h * y_ratio) - h // 2
            
            self.button_rects[btn_name] = pygame.Rect(x, y, w, h)
    
    def _load_mapping(self):
        """Load mapping from config file or use defaults.
        
        Merges loaded mapping with DEFAULT_MAPPING to ensure all entries
        (including new DPAD_ entries) exist even when loading from an
        older config that doesn't have them.
        """
        mapping = dict(self.DEFAULT_MAPPING)
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    saved = data.get(self.CONFIG_KEY, {})
                    if saved:
                        mapping.update(saved)
        except Exception as e:
            print(f"[ButtonMapper] Error loading config: {e}")
        return mapping
    
    def _save_mapping(self):
        """Save mapping to config file AND to per-controller profile"""
        try:
            # Load existing config or create new
            config = {}
            if os.path.exists(self.CONFIG_FILE):
                try:
                    with open(self.CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                except:
                    pass
            
            # Save to legacy flat key for backward compatibility
            config[self.CONFIG_KEY] = self.mapping
            
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"[ButtonMapper] Saved config to {self.CONFIG_FILE}")
            
            # Also save per-controller profile if we know which controller this is
            if self._controller_name and self._controller_name != "No Controller":
                try:
                    from controller_profiles import save_controller_profile
                    # Extract button mappings AND d-pad config
                    btn_mapping = {}
                    for btn in ['A', 'B', 'X', 'Y', 'L', 'R', 'SELECT', 'START']:
                        if btn in self.mapping:
                            btn_mapping[btn] = self.mapping[btn]
                    
                    # Include d-pad bindings as special keys
                    dpad_buttons = {}
                    dpad_axes = []
                    has_dpad_config = False
                    
                    for dpad_key in ['DPAD_UP', 'DPAD_DOWN', 'DPAD_LEFT', 'DPAD_RIGHT']:
                        binding = self.mapping.get(dpad_key)
                        if isinstance(binding, dict):
                            has_dpad_config = True
                            direction = dpad_key.replace('DPAD_', '').lower()
                            source = binding.get('source', '')
                            
                            if source == 'button':
                                btn_idx = binding.get('button')
                                if btn_idx is not None:
                                    dpad_buttons[direction] = [btn_idx]
                            elif source == 'axis':
                                axis_idx = binding.get('axis_index', 0)
                                # Add axis pair
                                if direction in ('left', 'right'):
                                    pair = (axis_idx, axis_idx + 1 if axis_idx % 2 == 0 else axis_idx)
                                else:
                                    pair = (axis_idx - 1 if axis_idx % 2 == 1 else axis_idx, axis_idx)
                                if list(pair) not in dpad_axes:
                                    dpad_axes.append(list(pair))
                    
                    if has_dpad_config:
                        if dpad_buttons:
                            btn_mapping['_dpad_buttons'] = dpad_buttons
                        if dpad_axes:
                            btn_mapping['_dpad_axes'] = dpad_axes
                        # Also save the full dpad binding dicts for reload
                        btn_mapping['_dpad_bindings'] = {}
                        for dpad_key in ['DPAD_UP', 'DPAD_DOWN', 'DPAD_LEFT', 'DPAD_RIGHT']:
                            if isinstance(self.mapping.get(dpad_key), dict):
                                btn_mapping['_dpad_bindings'][dpad_key] = self.mapping[dpad_key]
                    
                    profile_id = "custom"
                    if self._profile_info:
                        profile_id = self._profile_info.get("id", "custom")
                    
                    save_controller_profile(
                        self._controller_name,
                        btn_mapping,
                        profile_id,
                        self._controller_guid
                    )
                except ImportError:
                    pass  # controller_profiles not available, legacy save is fine
            
            return True
        except Exception as e:
            print(f"[ButtonMapper] Error saving config: {e}")
            return False
    
    def _apply_mapping_to_controller(self):
        """Apply current mapping to the controller manager"""
        if not self.controller:
            return
        
        # Apply face/shoulder button mappings
        for btn in ['A', 'B', 'L', 'R', 'SELECT', 'START']:
            if btn in self.mapping:
                val = self.mapping[btn]
                if isinstance(val, list):
                    self.controller.button_map[btn] = [v for v in val if isinstance(v, int)]
                elif isinstance(val, int):
                    self.controller.button_map[btn] = [val]
        
        # Apply d-pad bindings
        # Reset dpad config first
        self.controller.dpad_button_map = {
            'up': None, 'down': None, 'left': None, 'right': None
        }
        # Keep axes 0,1 as the base analog stick pair
        custom_axis_pairs = set()
        custom_axis_pairs.add((0, 1))
        
        # Track which hat axes are used so we know if hat is still relevant
        has_hat_binding = False
        
        dpad_directions = {
            'DPAD_UP': 'up', 'DPAD_DOWN': 'down',
            'DPAD_LEFT': 'left', 'DPAD_RIGHT': 'right'
        }
        
        for dpad_key, direction in dpad_directions.items():
            binding = self.mapping.get(dpad_key)
            if not binding or not isinstance(binding, dict):
                continue
            
            source = binding.get('source', '')
            
            if source == 'button':
                btn_idx = binding.get('button')
                if btn_idx is not None:
                    self.controller.dpad_button_map[direction] = [btn_idx]
            
            elif source == 'axis':
                axis_idx = binding.get('axis_index', 0)
                d = binding.get('direction', 0)
                # Figure out axis pair: even index is X, odd is Y
                # Or just add this specific axis to the check list
                if direction in ('left', 'right'):
                    # This axis is an X axis; pair it with the next one
                    pair_y = axis_idx + 1 if axis_idx % 2 == 0 else axis_idx
                    pair_x = axis_idx
                    custom_axis_pairs.add((pair_x, pair_y))
                else:
                    # This axis is a Y axis; pair it with the previous one
                    pair_x = axis_idx - 1 if axis_idx % 2 == 1 else axis_idx
                    pair_y = axis_idx
                    custom_axis_pairs.add((pair_x, pair_y))
            
            elif source == 'hat':
                has_hat_binding = True
                # Hat bindings are handled natively by the hat_map in controller.py
                # We may need to update hat_map if the user remapped directions
                hat_idx = binding.get('hat', 0)
                axis = binding.get('axis', '')
                value = binding.get('value', 0)
        
        # Update axis pairs if custom axes were configured
        self.controller.dpad_axis_pairs = list(custom_axis_pairs)
        
        # If user remapped hat directions, update the hat_map
        if has_hat_binding:
            self._update_hat_map()
        
        print(f"[ButtonMapper] Applied mapping to controller "
              f"(dpad_buttons={self.controller.dpad_button_map}, "
              f"axis_pairs={self.controller.dpad_axis_pairs})")
    
    def _update_hat_map(self):
        """Rebuild the controller's hat_map based on current dpad bindings.
        
        This handles the case where a user remapped d-pad directions to fix
        a mixed-up hat (e.g. Xbox Series X with inverted Y).
        
        For any direction NOT explicitly rebound as a hat source, we keep
        the default hat mapping so those directions continue to work.
        """
        if not self.controller:
            return
        
        # Remember which directions are explicitly mapped to hat sources
        hat_bound_directions = set()
        hat_entries = {}
        
        dpad_directions = {
            'DPAD_UP': 'up', 'DPAD_DOWN': 'down',
            'DPAD_LEFT': 'left', 'DPAD_RIGHT': 'right'
        }
        
        for dpad_key, direction in dpad_directions.items():
            binding = self.mapping.get(dpad_key)
            if not binding or not isinstance(binding, dict):
                continue
            if binding.get('source') != 'hat':
                continue
            
            hat_bound_directions.add(direction)
            axis = binding.get('axis', '')
            value = binding.get('value', 0)
            
            if axis == 'x':
                hat_entries[(value, 0)] = direction
            else:  # y
                hat_entries[(0, value)] = direction
        
        if not hat_entries:
            return  # No hat bindings, don't touch the hat_map
        
        # For unbound directions, use the default hat convention
        DEFAULT_HAT_DIR = {
            'up':    (0, 1),
            'down':  (0, -1),
            'left':  (-1, 0),
            'right': (1, 0),
        }
        for direction, hat_tuple in DEFAULT_HAT_DIR.items():
            if direction not in hat_bound_directions:
                # Keep the default mapping for this direction
                hat_entries[hat_tuple] = direction
        
        self.controller.hat_map = hat_entries
        print(f"[ButtonMapper] Updated hat_map: {hat_entries}")
    
    def _get_binding_display(self, button_name):
        """Get display string for a button's current binding"""
        if button_name not in self.mapping:
            return "?"
        
        binding = self.mapping[button_name]
        if not binding:
            return "None"
        
        # D-pad structured binding (dict)
        if isinstance(binding, dict):
            source = binding.get('source', '')
            if source == 'hat':
                axis = binding.get('axis', '?')
                value = binding.get('value', 0)
                if axis == 'x':
                    return "Hat" + ("+" if value > 0 else "-")
                else:
                    return "Hat" + ("+" if value > 0 else "-")
            elif source == 'axis':
                idx = binding.get('axis_index', 0)
                d = binding.get('direction', 0)
                return f"Ax{idx}" + ("+" if d > 0 else "-")
            elif source == 'button':
                return f"Btn {binding.get('button', '?')}"
            return "Custom"
        
        # Standard button bindings (list of integers)
        if isinstance(binding, list):
            if not binding:
                return "None"
            if isinstance(binding[0], int):
                return f"Btn {binding[0]}"
            # Legacy string entries
            return "D-pad"
        
        return "?"
    
    def _is_duplicate_binding(self, button_index, exclude_button=None):
        """Check if a button index is already bound to another action"""
        for btn_name, bindings in self.mapping.items():
            if btn_name == exclude_button:
                continue
            if btn_name.startswith('DPAD_'):
                continue  # Skip D-pad checks
            if isinstance(bindings, list) and button_index in bindings:
                return btn_name
        return None
    
    def _start_listening(self, button_name):
        """Start listening for a new binding.
        
        For face/shoulder buttons: listens for JOYBUTTONDOWN
        For d-pad directions: listens for JOYBUTTONDOWN, JOYHATMOTION, or JOYAXISMOTION
        """
        self.listening = True
        self.listening_button = button_name
        self.listening_is_dpad = button_name.startswith('DPAD_')
        self.listen_start_time = pygame.time.get_ticks()
        display_name = self.BUTTON_DISPLAY_NAMES.get(button_name, button_name)
        print(f"[ButtonMapper] Listening for new binding for {display_name}...")
    
    def _show_status(self, message, color=None):
        """Show a status message"""
        self.status_message = message
        self.status_time = pygame.time.get_ticks()
        self.status_color = color if color else COLOR_TEXT
    
    def _stop_listening(self, new_binding=None):
        """Stop listening and optionally apply new binding.
        
        Args:
            new_binding: For face buttons: int (button index)
                        For d-pad: dict with source info e.g.
                          {'source': 'hat', 'hat': 0, 'axis': 'y', 'value': 1}
                          {'source': 'axis', 'axis_index': 1, 'direction': -1}
                          {'source': 'button', 'button': 11}
                        None = cancelled/timeout
        """
        if new_binding is not None and self.listening_button:
            is_dpad = self.listening_button.startswith('DPAD_')
            
            if is_dpad and isinstance(new_binding, dict):
                # D-pad binding
                self.mapping[self.listening_button] = new_binding
                display = self._get_binding_display(self.listening_button)
                direction_name = self.listening_button.replace('DPAD_', '')
                self._show_status(f"{direction_name} -> {display}", (100, 255, 150))
                print(f"[ButtonMapper] Bound {self.listening_button} to {new_binding}")
            elif not is_dpad and isinstance(new_binding, int):
                # Regular button binding
                dup = self._is_duplicate_binding(new_binding, self.listening_button)
                if dup:
                    print(f"[ButtonMapper] Button {new_binding} already bound to {dup}!")
                    self.mapping[dup] = []
                    self._show_status(f"Cleared {dup} binding", (255, 180, 100))
                
                self.mapping[self.listening_button] = [new_binding]
                print(f"[ButtonMapper] Bound {self.listening_button} to button {new_binding}")
                self._show_status(f"{self.listening_button} -> Btn {new_binding}", (100, 255, 150))
            elif is_dpad and isinstance(new_binding, int):
                # User pressed a regular button while binding a d-pad direction
                # Bind it as a button-based d-pad
                self.mapping[self.listening_button] = {'source': 'button', 'button': new_binding}
                self._show_status(f"{self.listening_button.replace('DPAD_', '')} -> Btn {new_binding}", (100, 255, 150))
                print(f"[ButtonMapper] Bound {self.listening_button} to button {new_binding}")
            else:
                self._show_status("Cancelled", (150, 150, 150))
        elif self.listening_button:
            # Timeout or cancelled
            self._show_status("Cancelled", (150, 150, 150))
        
        self.listening = False
        self.listening_button = None
        self.listening_is_dpad = False
        
        # If in quick setup, advance to next button
        if self.quick_setup_active:
            self._advance_quick_setup()
    
    def _advance_quick_setup(self):
        """Advance to next button in quick setup"""
        self.quick_setup_index += 1
        
        if self.quick_setup_index >= len(self.BINDABLE_BUTTONS):
            # Quick setup complete
            self.quick_setup_active = False
            self.quick_setup_index = 0
            self._show_status("Setup complete!", (100, 255, 150))
            print("[ButtonMapper] Quick Setup complete!")
        else:
            # Start listening for next button
            next_btn = self.BINDABLE_BUTTONS[self.quick_setup_index]
            # Find this button in our button_list for visual selection
            if next_btn in self.button_list:
                self.selected_index = self.button_list.index(next_btn)
            self._start_listening(next_btn)
    
    def _start_quick_setup(self):
        """Start quick setup mode"""
        self.quick_setup_active = True
        self.quick_setup_index = 0
        self.in_menu = False
        self.menu_selected = -1
        
        # Select first bindable button
        first_btn = self.BINDABLE_BUTTONS[0]
        if first_btn in self.button_list:
            self.selected_index = self.button_list.index(first_btn)
        
        self._start_listening(first_btn)
    
    def _reset_to_default(self):
        """Reset all mappings to the auto-detected profile defaults"""
        self.mapping = dict(self._detected_default_mapping)
        self._apply_mapping_to_controller()
        
        profile_name = "defaults"
        if self._profile_info and self._profile_info.get("description"):
            profile_name = self._profile_info["description"]
        
        self._show_status(f"Reset: {profile_name}", (100, 200, 255))
        print(f"[ButtonMapper] Reset to detected defaults ({profile_name})")
    
    def on_close(self):
        """Handle closing the mapper"""
        self._save_mapping()
        self._apply_mapping_to_controller()
        self.visible = False
        if self.close_callback:
            self.close_callback()
    
    def handle_events(self, events):
        """Handle pygame events"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.listening:
                    # Cancel with Escape
                    if event.key == pygame.K_ESCAPE:
                        if self.quick_setup_active:
                            self.quick_setup_active = False
                        self._stop_listening()
                else:
                    if event.key == pygame.K_ESCAPE:
                        self.on_close()
                    elif event.key == pygame.K_UP:
                        self._navigate('up')
                    elif event.key == pygame.K_DOWN:
                        self._navigate('down')
                    elif event.key == pygame.K_LEFT:
                        self._navigate('left')
                    elif event.key == pygame.K_RIGHT:
                        self._navigate('right')
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self._activate()
            
            # Listen for controller input when rebinding
            if self.listening:
                # Grace period: ignore input for first 200ms after starting to listen.
                # This prevents the hat/axis that was used to navigate to the DPAD_
                # button from immediately triggering a binding.
                grace_ms = 200
                elapsed_ms = pygame.time.get_ticks() - self.listen_start_time
                if elapsed_ms < grace_ms:
                    continue
                
                if event.type == pygame.JOYBUTTONDOWN:
                    if getattr(self, 'listening_is_dpad', False):
                        # Binding a d-pad direction — a button press means button-based dpad
                        self._stop_listening(event.button)
                    else:
                        # Binding a face/shoulder button
                        self._stop_listening(event.button)
                
                elif event.type == pygame.JOYHATMOTION and getattr(self, 'listening_is_dpad', False):
                    # Hat motion while binding a d-pad direction
                    hx, hy = event.value
                    if hx != 0 or hy != 0:
                        # Determine which axis and value
                        if abs(hx) >= abs(hy) and hx != 0:
                            binding = {'source': 'hat', 'hat': event.hat,
                                      'axis': 'x', 'value': 1 if hx > 0 else -1}
                        else:
                            binding = {'source': 'hat', 'hat': event.hat,
                                      'axis': 'y', 'value': 1 if hy > 0 else -1}
                        self._stop_listening(binding)
                
                elif event.type == pygame.JOYAXISMOTION and getattr(self, 'listening_is_dpad', False):
                    # Axis motion while binding a d-pad direction
                    AXIS_THRESHOLD = 0.6
                    if abs(event.value) > AXIS_THRESHOLD:
                        binding = {'source': 'axis', 'axis_index': event.axis,
                                  'direction': 1 if event.value > 0 else -1}
                        self._stop_listening(binding)
    
    def handle_controller(self, ctrl):
        """Handle controller input"""
        if self.listening:
            # When listening, we handle raw pygame events in handle_events
            # Don't process controller manager button presses here to avoid
            # cancelling when the user is trying to bind B button
            
            # Only check for timeout
            elapsed = (pygame.time.get_ticks() - self.listen_start_time) / 1000.0
            if elapsed >= self.listen_timeout:
                if self.quick_setup_active:
                    # Skip this button in quick setup
                    self._stop_listening()
                else:
                    self._stop_listening()
            
            # Note: We don't check for B to cancel here anymore
            # Cancel can be done via keyboard ESC in handle_events
            # This prevents B from being detected as "cancel" when trying to bind it
            return True
        
        # Navigation
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            self._navigate('up')
        elif ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            self._navigate('down')
        elif ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            self._navigate('left')
        elif ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            self._navigate('right')
        
        # Activate
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            self._activate()
        
        # Close
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            self.on_close()
        
        return True
    
    def _navigate(self, direction):
        """Navigate button selection"""
        if self.in_menu:
            # Navigate menu
            if direction == 'up':
                if self.menu_selected > 0:
                    self.menu_selected -= 1
                else:
                    self.in_menu = False
                    self.menu_selected = -1
            elif direction == 'down':
                if self.menu_selected < len(self.menu_items) - 1:
                    self.menu_selected += 1
        else:
            # Navigate buttons on GBA
            current_btn = self.button_list[self.selected_index]
            current_rect = self.button_rects[current_btn]
            cx, cy = current_rect.center
            
            # Find nearest button in the given direction
            best_btn = None
            best_dist = float('inf')
            
            for i, btn in enumerate(self.button_list):
                if i == self.selected_index:
                    continue
                
                rect = self.button_rects[btn]
                bx, by = rect.center
                
                # Check if this button is in the right direction
                valid = False
                if direction == 'up' and by < cy - 5:
                    valid = True
                elif direction == 'down' and by > cy + 5:
                    valid = True
                elif direction == 'left' and bx < cx - 5:
                    valid = True
                elif direction == 'right' and bx > cx + 5:
                    valid = True
                
                if valid:
                    dist = abs(bx - cx) + abs(by - cy)
                    if dist < best_dist:
                        best_dist = dist
                        best_btn = i
            
            if best_btn is not None:
                self.selected_index = best_btn
            elif direction == 'down':
                # No button below, go to menu
                self.in_menu = True
                self.menu_selected = 0
    
    def _activate(self):
        """Activate current selection"""
        if self.in_menu:
            item = self.menu_items[self.menu_selected]
            if item == 'Quick Setup':
                self._start_quick_setup()
            elif item == 'Reset to Default':
                self._reset_to_default()
            elif item == 'Save & Close':
                self.on_close()
        else:
            # Activate button for rebinding (all buttons including d-pad)
            btn = self.button_list[self.selected_index]
            self._start_listening(btn)
    
    def update(self, events):
        """Update the mapper"""
        self.handle_events(events)
        return self.visible
    
    def draw(self, surf):
        """Draw the button mapper screen"""
        # Background with overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.fill(COLOR_BG)
        surf.blit(overlay, (0, 0))
        
        # Border
        pygame.draw.rect(surf, COLOR_BORDER, (0, 0, self.width, self.height), 2)
        
        # Title
        title = "Button Mapping"
        if self.quick_setup_active:
            title = "Quick Setup"
        title_surf = self.font_header.render(title, True, COLOR_HIGHLIGHT)
        title_rect = title_surf.get_rect(centerx=self.width // 2, top=12)
        surf.blit(title_surf, title_rect)
        
        # Show detected profile info below title
        self._draw_profile_info(surf, title_rect.bottom + 2)
        
        # Draw GBA visual
        self._draw_gba(surf)
        
        # Draw screen content (status/instructions)
        self._draw_screen_content(surf)
        
        # Draw menu options
        self._draw_menu(surf)
        
        # Draw controller hints
        hints = "D-Pad/Arrows: Navigate  A/Enter: Bind  B/Esc: Back"
        if self.listening:
            if getattr(self, 'listening_is_dpad', False):
                hints = "Move hat/stick or press btn  ESC: Cancel"
            else:
                hints = "Press a button to bind   ESC: Cancel"
        hint_surf = self.font_small.render(hints, True, (100, 100, 100))
        hint_rect = hint_surf.get_rect(centerx=self.width // 2, bottom=self.height - 8)
        surf.blit(hint_surf, hint_rect)
    
    def _draw_profile_info(self, surf, y):
        """Draw the detected controller profile info"""
        if self._profile_info and self._profile_info.get("description"):
            desc = self._profile_info["description"]
            match = self._profile_info.get("match_type", "")
            
            # Color-code by match quality
            if match == "saved":
                color = (100, 200, 100)  # Green for saved/custom
                label = f"{desc}"
            elif match in ("guid", "name"):
                color = (100, 180, 255)  # Blue for auto-detected
                label = f"Detected: {desc}"
            elif match == "legacy":
                color = (200, 180, 100)  # Amber for legacy
                label = "Custom Mapping"
            else:
                color = (150, 150, 150)  # Grey for unknown/heuristic
                label = f"{desc}"
            
            info_surf = self.font_tiny.render(label, True, color)
            info_rect = info_surf.get_rect(centerx=self.width // 2, top=y)
            surf.blit(info_surf, info_rect)
        elif self._controller_name and self._controller_name != "No Controller":
            # No profile info but controller is connected
            info_surf = self.font_tiny.render(self._controller_name, True, (150, 150, 150))
            info_rect = info_surf.get_rect(centerx=self.width // 2, top=y)
            surf.blit(info_surf, info_rect)
    
    def _draw_gba(self, surf):
        """Draw the GBA visual with buttons"""
        # GBA body
        pygame.draw.rect(surf, (45, 35, 60), self.gba_rect, border_radius=12)
        pygame.draw.rect(surf, (70, 55, 90), self.gba_rect, 3, border_radius=12)
        
        # Screen bezel
        bezel_rect = self.screen_rect.inflate(8, 8)
        pygame.draw.rect(surf, (30, 25, 40), bezel_rect, border_radius=4)
        pygame.draw.rect(surf, (20, 40, 30), self.screen_rect, border_radius=2)
        
        # Speaker grills (right side decorative)
        for i in range(4):
            grill_y = self.gba_rect.y + self.gba_rect.height * 0.25 + i * 8
            grill_rect = pygame.Rect(
                self.gba_rect.right - 35,
                grill_y,
                20, 3
            )
            pygame.draw.rect(surf, (35, 28, 45), grill_rect, border_radius=1)
        
        # Draw D-pad center
        dpad_center_x = self.gba_rect.x + int(self.gba_rect.width * 0.18)
        dpad_center_y = self.gba_rect.y + int(self.gba_rect.height * 0.42)
        dpad_size = int(self.gba_rect.width * 0.07)
        
        # D-pad cross background
        pygame.draw.rect(surf, (25, 20, 35), 
                        (dpad_center_x - dpad_size, dpad_center_y - dpad_size//3,
                         dpad_size * 2, dpad_size * 0.66), border_radius=2)
        pygame.draw.rect(surf, (25, 20, 35),
                        (dpad_center_x - dpad_size//3, dpad_center_y - dpad_size,
                         dpad_size * 0.66, dpad_size * 2), border_radius=2)
        
        # Draw each button
        for btn_name, rect in self.button_rects.items():
            is_selected = (not self.in_menu and 
                          self.button_list[self.selected_index] == btn_name)
            is_listening = (self.listening and self.listening_button == btn_name)
            is_dpad = btn_name.startswith('DPAD_')
            
            # Button colors
            if is_listening:
                bg_color = (80, 60, 20)  # Amber when listening
                border_color = (255, 200, 50)
            elif is_selected:
                bg_color = (40, 60, 80)
                border_color = COLOR_HIGHLIGHT
            else:
                bg_color = (35, 30, 45) if is_dpad else (50, 40, 60)
                border_color = (60, 50, 70)
            
            # Different shapes for different buttons
            if btn_name in ('A', 'B'):
                # Circular buttons
                pygame.draw.circle(surf, bg_color, rect.center, rect.width // 2)
                pygame.draw.circle(surf, border_color, rect.center, rect.width // 2, 2)
            elif btn_name in ('L', 'R'):
                # Shoulder buttons (rounded rectangle)
                pygame.draw.rect(surf, bg_color, rect, border_radius=6)
                pygame.draw.rect(surf, border_color, rect, 2, border_radius=6)
            elif btn_name in ('START', 'SELECT'):
                # Small oval buttons
                pygame.draw.rect(surf, bg_color, rect, border_radius=4)
                pygame.draw.rect(surf, border_color, rect, 2, border_radius=4)
            else:
                # D-pad buttons (already drawn as cross)
                if is_selected or is_listening:
                    pygame.draw.rect(surf, bg_color, rect.inflate(2, 2), border_radius=2)
                    pygame.draw.rect(surf, border_color, rect.inflate(2, 2), 2, border_radius=2)
            
            # Draw binding text
            if is_listening:
                elapsed = (pygame.time.get_ticks() - self.listen_start_time) / 1000.0
                remaining = max(0, self.listen_timeout - elapsed)
                text = f"{remaining:.1f}"
                text_color = (255, 200, 50)
            else:
                binding = self._get_binding_display(btn_name)
                if is_dpad and binding in ("Hat+", "Hat-"):
                    text = ""  # Default hat binding, no need to show
                else:
                    text = binding
                text_color = COLOR_HIGHLIGHT if is_selected else COLOR_TEXT
            
            if text:
                text_surf = self.font_tiny.render(text, True, text_color)
                text_rect = text_surf.get_rect(center=rect.center)
                surf.blit(text_surf, text_rect)
            
            # Draw button label below/beside
            if not is_dpad:
                label_text = btn_name
                if btn_name == 'SELECT':
                    label_text = 'SEL'
                elif btn_name == 'START':
                    label_text = 'STA'
                
                label_surf = self.font_tiny.render(label_text, True, (100, 90, 110))
                if btn_name in ('L', 'R'):
                    label_rect = label_surf.get_rect(centerx=rect.centerx, top=rect.bottom + 2)
                elif btn_name in ('A', 'B'):
                    label_rect = label_surf.get_rect(centerx=rect.centerx, top=rect.bottom + 3)
                else:
                    label_rect = label_surf.get_rect(centerx=rect.centerx, bottom=rect.top - 2)
                surf.blit(label_surf, label_rect)
    
    def _draw_screen_content(self, surf):
        """Draw content in the GBA's screen area"""
        # Check if status message should be shown
        show_status = False
        if self.status_message:
            elapsed = (pygame.time.get_ticks() - self.status_time) / 1000.0
            if elapsed < self.status_duration:
                show_status = True
            else:
                self.status_message = ""
        
        if self.listening:
            # Countdown display
            elapsed = (pygame.time.get_ticks() - self.listen_start_time) / 1000.0
            remaining = max(0, self.listen_timeout - elapsed)
            
            # Button name (friendly)
            display_name = self.BUTTON_DISPLAY_NAMES.get(
                self.listening_button, self.listening_button)
            btn_text = f"Bind: {display_name}"
            btn_surf = self.font_text.render(btn_text, True, (150, 200, 150))
            btn_rect = btn_surf.get_rect(centerx=self.screen_rect.centerx,
                                         centery=self.screen_rect.centery - 25)
            surf.blit(btn_surf, btn_rect)
            
            # Hint for what inputs are accepted
            if getattr(self, 'listening_is_dpad', False):
                hint = "Hat/Stick/Btn"
            else:
                hint = "Press button"
            hint_surf = self.font_tiny.render(hint, True, (130, 150, 130))
            hint_rect = hint_surf.get_rect(centerx=self.screen_rect.centerx,
                                           centery=self.screen_rect.centery - 10)
            surf.blit(hint_surf, hint_rect)
            
            # Countdown
            count_text = f"{remaining:.1f}s"
            count_surf = self.font_header.render(count_text, True, (255, 200, 50))
            count_rect = count_surf.get_rect(centerx=self.screen_rect.centerx,
                                             centery=self.screen_rect.centery + 5)
            surf.blit(count_surf, count_rect)
            
            # ESC hint
            esc_surf = self.font_tiny.render("ESC: Cancel", True, (120, 120, 120))
            esc_rect = esc_surf.get_rect(centerx=self.screen_rect.centerx,
                                         centery=self.screen_rect.centery + 25)
            surf.blit(esc_surf, esc_rect)
            
            # Progress bar
            bar_width = self.screen_rect.width - 20
            bar_height = 6
            bar_x = self.screen_rect.x + 10
            bar_y = self.screen_rect.bottom - 15
            
            # Background
            pygame.draw.rect(surf, (40, 35, 50),
                           (bar_x, bar_y, bar_width, bar_height), border_radius=3)
            # Fill
            fill_width = int(bar_width * (remaining / self.listen_timeout))
            if fill_width > 0:
                pygame.draw.rect(surf, (255, 200, 50),
                               (bar_x, bar_y, fill_width, bar_height), border_radius=3)
        
        elif show_status:
            # Show status message
            status_surf = self.font_text.render(self.status_message, True, self.status_color)
            status_rect = status_surf.get_rect(centerx=self.screen_rect.centerx,
                                               centery=self.screen_rect.centery)
            surf.blit(status_surf, status_rect)
        
        elif self.quick_setup_active:
            # Quick setup progress
            progress = f"{self.quick_setup_index + 1}/{len(self.BINDABLE_BUTTONS)}"
            prog_surf = self.font_small.render(progress, True, (100, 150, 100))
            prog_rect = prog_surf.get_rect(centerx=self.screen_rect.centerx,
                                           centery=self.screen_rect.centery)
            surf.blit(prog_surf, prog_rect)
        
        else:
            # Instructions
            lines = ["Select button", "to rebind", "", "A: Bind  B: Close", "All buttons", "rebindable"]
            y = self.screen_rect.y + 8
            for line in lines:
                if line:
                    line_surf = self.font_tiny.render(line, True, (100, 130, 100))
                    line_rect = line_surf.get_rect(centerx=self.screen_rect.centerx, top=y)
                    surf.blit(line_surf, line_rect)
                y += 12
    
    def _draw_menu(self, surf):
        """Draw menu options below GBA"""
        menu_x = self.width // 2 - 100
        y = self.menu_y
        
        for i, item in enumerate(self.menu_items):
            is_selected = self.in_menu and self.menu_selected == i
            
            # Background
            item_rect = pygame.Rect(menu_x, y, 200, 22)
            if is_selected:
                pygame.draw.rect(surf, (40, 55, 75), item_rect, border_radius=4)
                pygame.draw.rect(surf, COLOR_HIGHLIGHT, item_rect, 2, border_radius=4)
                text_color = COLOR_HIGHLIGHT
            else:
                pygame.draw.rect(surf, (30, 35, 45), item_rect, border_radius=4)
                text_color = COLOR_TEXT
            
            # Text
            text_surf = self.font_text.render(item, True, text_color)
            text_rect = text_surf.get_rect(center=item_rect.center)
            surf.blit(text_surf, text_rect)
            
            y += 26


# For integration with Settings
class ButtonMapperModal:
    """Wrapper for Settings integration"""
    
    def __init__(self, width, height, close_callback=None, controller=None):
        self.mapper = ButtonMapper(width, height, close_callback, controller)
        self.visible = True
    
    def update(self, events):
        result = self.mapper.update(events)
        self.visible = self.mapper.visible
        return result
    
    def handle_controller(self, ctrl):
        return self.mapper.handle_controller(ctrl)
    
    def draw(self, surf):
        self.mapper.draw(surf)