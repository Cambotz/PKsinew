#!/usr/bin/env python3

"""
Controller Support Module for Sinew
Handles gamepad/joystick input with standard button mappings

Button Mapping (Xbox-style, adaptable):
- DPAD: Navigation
- A: Confirm/Select
- B: Back/Cancel
- Start: Menu/Pause
- Select: Secondary menu
- L/R: Page navigation (shoulder buttons)

Auto-Detection:
When a controller is connected, the system will:
1. Check for a saved per-controller profile (keyed by controller name)
2. Match against the built-in known controller database
3. Fall back to legacy flat mapping from settings
4. Default to Xbox-style layout
"""

from enum import IntEnum

import pygame

from config import SETTINGS_FILE


class ControllerButton(IntEnum):
    """Standard button indices - can be remapped"""

    A = 0
    B = 1
    X = 2
    Y = 3
    L = 4
    R = 5
    SELECT = 6
    START = 7
    # Some controllers have different mappings
    L_ALT = 9  # Alternative L button index
    R_ALT = 10  # Alternative R button index


class ControllerAxis(IntEnum):
    """Standard axis indices"""

    LEFT_X = 0
    LEFT_Y = 1
    RIGHT_X = 2
    RIGHT_Y = 3
    # D-pad as axes (some controllers)
    DPAD_X = 4
    DPAD_Y = 5


class ControllerEvent:
    """Represents a controller input event"""

    def __init__(self, event_type, button=None, direction=None):
        self.type = event_type  # 'button', 'dpad'
        self.button = button  # ControllerButton or None
        self.direction = direction  # 'up', 'down', 'left', 'right' or None

    def __repr__(self):
        return f"ControllerEvent({self.type}, button={self.button}, direction={self.direction})"


class ControllerManager:
    """
    Manages controller input for the game

    Provides:
    - Controller detection and auto-configuration via profiles
    - Button press/release tracking
    - D-pad direction handling
    - Analog stick to digital conversion
    - Event generation compatible with game screens
    """

    # Dead zone for analog sticks
    AXIS_DEADZONE = 0.5

    # Repeat delay for held buttons (in milliseconds)
    REPEAT_DELAY_INITIAL = 400
    REPEAT_DELAY_SUBSEQUENT = 100

    # Debounce time for connect/disconnect events (in milliseconds)
    HOTPLUG_DEBOUNCE_MS = 3000  # 3 seconds to handle flaky controllers

    def __init__(self):
        """Initialize controller manager"""
        self.controllers = []
        self.active_controller = None
        self.connected = False

        # Active profile info (set by auto-detection)
        self.active_profile_id = None
        self.active_profile_description = None
        self.active_profile_match_type = None

        # Hotplug debouncing
        self._last_hotplug_time = 0
        self._hotplug_pending = False
        self._is_refreshing = False  # Prevent re-entry

        # Button state tracking
        self.button_states = {}
        self.button_held_time = {}
        self.button_repeat_ready = {}

        directions = ["up", "down", "left", "right"]
        self.dpad_states = dict.fromkeys(directions, False)
        self.dpad_held_time = dict.fromkeys(directions, 0)
        self.dpad_repeat_ready = dict.fromkeys(directions, False)
        self.dpad_consumed = dict.fromkeys(directions, False)
        self.button_consumed = {}

        self.button_map = {k: [v] for k, v in zip(
            ["A", "B", "X", "Y", "L", "R", "SELECT", "START"],
            range(8),
            strict=False
        )}

        # Store original A/B for swap functionality
        self._original_a = [0]
        self._original_b = [1]
        self._swap_ab = False

        # HAT (D-pad) mapping - cardinal directions only.
        # Maps (hat_x, hat_y) tuples to direction strings.
        # Diagonals are decomposed into cardinals by _get_dpad_from_hat().
        # This dict is rebuilt by ButtonMapper._update_hat_map() when
        # the user remaps d-pad directions.
        self.hat_map = {(0, 1): "up", (0, -1): "down", (-1, 0): "left", (1, 0): "right"}

        self.dpad_button_map = dict.fromkeys(directions, None)

        # D-pad / stick axis indices
        # Some controllers use axes other than 0/1 for the left stick or d-pad.
        # These are the axis pairs we'll poll for directional input.
        # Format: list of (x_axis_index, y_axis_index) tuples to check.
        self.dpad_axis_pairs = [(0, 1)]

        # Keyboard navigation map for Sinew UI (separate from emulator keys).
        # Each action maps to a list of pygame key constants so multiple keys
        # (e.g. arrows AND WASD) can trigger the same direction simultaneously.
        self.kb_nav_map = dict(zip(
            ["up", "down", "left", "right", "A", "B", "L", "R", "MENU"],
            [[pygame.K_UP, pygame.K_w], [pygame.K_DOWN, pygame.K_s], [pygame.K_LEFT, pygame.K_a], [pygame.K_RIGHT, pygame.K_d],
             [pygame.K_RETURN, pygame.K_z], [pygame.K_ESCAPE, pygame.K_x], [pygame.K_PAGEUP, pygame.K_q], [pygame.K_PAGEDOWN, pygame.K_e], [pygame.K_m]],
            strict=False
        ))

        # Load keyboard nav bindings from settings (does NOT load controller
        # mapping — that's handled by auto-detection in _scan_controllers)
        self._load_keyboard_config()

        self._init_controllers()

    def _load_keyboard_config(self):
        """Load keyboard navigation and swap_ab settings from sinew_settings.json.

        Controller button mapping is NOT loaded here — it's resolved per-controller
        by the auto-detection system in _apply_profile_for_controller().
        """
        import json
        import os

        config_file = SETTINGS_FILE

        try:
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    config = json.load(f)

                # Load keyboard navigation map
                if "keyboard_nav_map" in config:
                    saved_kb = config["keyboard_nav_map"]
                    for action in self.kb_nav_map:
                        if action in saved_kb:
                            val = saved_kb[action]
                            if isinstance(val, list):
                                self.kb_nav_map[action] = [
                                    v for v in val if isinstance(v, int)
                                ]
                    print(f"[Controller] Loaded keyboard nav map from {config_file}")

                # Load swap_ab setting
                swap_ab = config.get("swap_ab", False)
                if swap_ab:
                    self._pending_swap_ab = True
                else:
                    self._pending_swap_ab = False
        except Exception as e:
            print(f"[Controller] Error loading keyboard config: {e}")
            self._pending_swap_ab = False

    def _apply_profile_for_controller(self, joy):
        """
        Auto-detect and apply the correct button mapping for a controller.
        """
        self.dpad_button_map = {"up": [], "down": [], "left": [], "right": []}
        self.dpad_axis_pairs = []

        try:
            from controller_profiles import resolve_mapping, save_controller_profile
        except ImportError:
            print("[Controller] controller_profiles module not found, using defaults")
            self._store_originals_and_swap()
            return

        name = joy.get_name()
        guid = None
        try:
            guid = joy.get_guid()
        except (AttributeError, pygame.error):
            pass

        num_buttons = joy.get_numbuttons()
        num_axes = joy.get_numaxes()
        num_hats = joy.get_numhats()

        # Resolve the best mapping from database or saves
        result = resolve_mapping(name, guid, num_buttons, num_axes, num_hats)
        mapping = result.get("mapping", {})

        # Capture hardware
        self._original_a = mapping.get("A", [0])
        self._original_b = mapping.get("B", [1])

        # Apply standard buttons
        for btn in ["A", "B", "X", "Y", "L", "R", "SELECT", "START"]:
            if btn in mapping:
                val = mapping[btn]
                if isinstance(val, list):
                    self.button_map[btn] = [v for v in val if isinstance(v, int)]
                elif isinstance(val, int):
                    self.button_map[btn] = [val]

        # Store profile info for UI/Logging
        self.active_profile_id = result.get("id", "unknown")
        self.active_profile_description = result.get("description", "Unknown")
        self.active_profile_match_type = result.get("match_type", "default")

        print(
            f"[Controller] Profile: {self.active_profile_description} "
            f"({self.active_profile_match_type}) "
            f"A={self.button_map.get('A')}, B={self.button_map.get('B')}"
        )

        # D-Pad Logic
        dpad_config = mapping.get("_dpad_buttons")
        dpad_axes = mapping.get("_dpad_axes")

        if dpad_config and isinstance(dpad_config, dict):
            # Profile defines D-pad as Buttons
            for direction in ["up", "down", "left", "right"]:
                if direction in dpad_config:
                    val = dpad_config[direction]
                    if isinstance(val, list):
                        self.dpad_button_map[direction] = [v for v in val if isinstance(v, int)]
                    elif isinstance(val, int):
                        self.dpad_button_map[direction] = [val]
            print(f"[Controller] D-pad locked to profile buttons: {self.dpad_button_map}")

        elif dpad_axes and isinstance(dpad_axes, list):
            # Profile defines D-pad as Axes
            self.dpad_axis_pairs = [
                (pair[0], pair[1])
                for pair in dpad_axes
                if isinstance(pair, (list, tuple)) and len(pair) == 2
            ]
            print(f"[Controller] D-pad locked to profile axes: {self.dpad_axis_pairs}")

        elif num_hats == 0:
            # No profile D-pad and no hardware hats -> Auto-detect
            self._auto_detect_dpad(joy)

        # If we guessed the D-pad, save it so it's "Locked" for next time
        if result["match_type"] in ("name", "guid", "heuristic"):
            from controller_profiles import load_saved_profile
            if not load_saved_profile(name, guid):
                if any(v is not None for v in self.dpad_button_map.values()):
                    mapping["_dpad_buttons"] = self.dpad_button_map
                elif self.dpad_axis_pairs:
                    mapping["_dpad_axes"] = self.dpad_axis_pairs
                
                save_controller_profile(name, mapping, self.active_profile_id, guid)

        # Apply swap a/b if needed
        self._store_originals_and_swap()

    def refresh_controller_config(self):
        """
        Refresh controller configuration.
        
        Re-applies the controller profile to ensure D-pad and button mappings
        are current. Useful after returning from emulator where controller state
        might have diverged.
        """
        if self.active_controller and self.connected:
            print("[Controller] Refreshing controller configuration...")
            self._apply_profile_for_controller(self.active_controller)
            # Also reload keyboard nav map in case settings changed
            self._load_keyboard_config()
        else:
            print("[Controller] No active controller to refresh")

    def _store_originals_and_swap(self):
        """Store original A/B values and apply swap based on current preference."""
        # Only capture originals if they aren't already set 
        # This prevents 'A' and 'B' from getting mixed up during a resume/re-init
        if not hasattr(self, "_original_a") or not self._original_a:
            self._original_a = self.button_map.get("A", [0])[:]
            self._original_b = self.button_map.get("B", [1])[:]

        # Check the preference
        should_swap = getattr(self, "_swap_ab", False) or getattr(self, "_pending_swap_ab", False)

        if should_swap:
            # Explicitly set to the opposite of the hardware
            self.button_map["A"] = self._original_b[:]
            self.button_map["B"] = self._original_a[:]
            self._swap_ab = True
            print(f"[Controller] Applied A/B Swap: A={self.button_map['A']} B={self.button_map['B']}")
        else:
            # Reset to the hardware
            self.button_map["A"] = self._original_a[:]
            self.button_map["B"] = self._original_b[:]
            self._swap_ab = False

    def _auto_detect_dpad(self, joy):
        """Auto-detect how the d-pad is reported on this controller.

        Called during scan when the profile doesn't specify d-pad config.
        Sets up dpad_button_map and dpad_axis_pairs as needed.

        D-pad detection strategy:
        - If controller has hats: hat-based d-pad is already handled, no extra work
        - If controller has 0 hats but many buttons: likely button-based d-pad
          (common on cheap USB pads and some DirectInput controllers)
        - If controller has extra axes beyond the sticks: might be axis-based d-pad
          (axes 4/5, 6/7, etc.)

        We can't know the exact button indices without user interaction, so for
        button-based d-pads we use common conventions. The user can always
        remap via Quick Setup if these guesses are wrong.
        """
        try:
            num_hats = joy.get_numhats()
            num_buttons = joy.get_numbuttons()
            num_axes = joy.get_numaxes()
        except pygame.error:
            return

        has_hat = num_hats > 0

        if has_hat:
            # Hat-based d-pad is already handled by _get_dpad_from_hat().
            # Also add axes 0,1 for left stick (already the default).
            # If there are extra axes that could be a second d-pad, add them.
            if num_axes >= 6:
                # Some controllers put d-pad on axes 4,5 (e.g. some PS3 adapters)
                if (0, 1) not in self.dpad_axis_pairs:
                    self.dpad_axis_pairs = [(0, 1)]
                # Don't add 4,5 by default since those are often triggers
            return

        # No hat — d-pad might be reported as buttons or axes

        # Check for button-based d-pad
        # Common patterns for controllers with 0 hats:
        # - High button indices (11-14 or 12-15) are d-pad directions
        # - Or buttons right after the face/shoulder buttons
        if num_buttons >= 12:
            # Very common: buttons 11,12,13,14 = up,down,left,right
            # Used by many generic USB pads and some PS3 adapters without hat
            # Also common: 12,13,14,15 on controllers with more buttons
            # We'll try the most common pattern

            # Check if the highest 4 buttons are likely d-pad
            # (they shouldn't already be mapped to face buttons)
            mapped_buttons = set()
            for indices in self.button_map.values():
                mapped_buttons.update(indices)

            # Try common d-pad button ranges
            for base in [11, 12, num_buttons - 4]:
                candidates = list(range(base, base + 4))
                if all(c < num_buttons for c in candidates):
                    overlap = mapped_buttons.intersection(candidates)
                    if not overlap:
                        self.dpad_button_map = {
                            "up": [candidates[0]],
                            "down": [candidates[1]],
                            "left": [candidates[2]],
                            "right": [candidates[3]],
                        }

                        # Don't use hat if we use buttons
                        self.dpad_axis_pairs = []

                        print(
                            f"[Controller] Auto-detected button d-pad: "
                            f"U={candidates[0]} D={candidates[1]} "
                            f"L={candidates[2]} R={candidates[3]}"
                        )
                        return

        # Check for axis-based d-pad on non-standard axes
        if num_axes >= 4:
            # Always include axes 0,1 (left stick)
            pairs = [(0, 1)]

            # If there are axes 4,5 or 6,7 that could be a d-pad
            if num_axes >= 6:
                pairs.append((4, 5))
            if num_axes >= 8:
                pairs.append((6, 7))

            if len(pairs) > 1:
                self.dpad_axis_pairs = pairs
                print(f"[Controller] Checking axis pairs for d-pad: {pairs}")

    def reload_kb_nav_map(self):
        """Reload keyboard navigation map from settings (call after user changes bindings)."""
        self._load_keyboard_config()
        print("[Controller] Reloaded keyboard nav map")

    def set_swap_ab(self, enabled):
        """Swap A and B button mappings"""
        if enabled == self._swap_ab:
            return  # No change needed

        self._swap_ab = enabled

        if enabled:
            # Swap A and B
            self.button_map["A"] = self._original_b[:]
            self.button_map["B"] = self._original_a[:]
        else:
            # Restore original
            self.button_map["A"] = self._original_a[:]
            self.button_map["B"] = self._original_b[:]

        print(
            f"[Controller] A/B swap {'enabled' if enabled else 'disabled'}: A={self.button_map['A']}, B={self.button_map['B']}"
        )

    def _init_controllers(self):
        """Initialize pygame joystick subsystem and detect controllers"""
        pygame.joystick.init()
        self._scan_controllers()

    def _scan_controllers(self):
        """Scan for connected controllers and auto-detect profiles"""
        self.controllers = []

        try:
            count = pygame.joystick.get_count()
        except pygame.error:
            count = 0

        for i in range(count):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
                
                # Reject devices with no buttons/axes (like your event0 haptics)
                # Reject common system devices by name
                name = joy.get_name().lower()
                is_system_device = any(x in name for x in ["haptics", "pwrkey", "resin", "headset"])
                
                if joy.get_numbuttons() > 0 and joy.get_numaxes() > 0 and not is_system_device:
                    self.controllers.append(joy)
                    print(f"Validated Controller {i}: {joy.get_name()}")
                    print(f"  Buttons: {joy.get_numbuttons()} | Axes: {joy.get_numaxes()}")
                else:
                    print(f"Skipping non-gamepad device {i}: {joy.get_name()}")
                    joy.quit()

            except pygame.error as e:
                print(f"Error initializing controller {i}: {e}")

        if self.controllers:
            self.active_controller = self.controllers[0]
            self.connected = True
            print(f"Active controller: {self.active_controller.get_name()}")
            self._apply_profile_for_controller(self.active_controller)
        else:
            self.active_controller = None
            self.connected = False
            self.active_profile_id = None
            self.active_profile_description = None
            self.active_profile_match_type = None

    def refresh_controllers(self):
        """Refresh controller list (call when hotplugging)"""
        # Prevent re-entry
        if self._is_refreshing:
            return

        self._is_refreshing = True
        try:
            # Don't quit/reinit if we already have a working controller
            if self.active_controller and self.connected:
                try:
                    # Test if controller is still valid
                    _ = self.active_controller.get_numbuttons()
                    # Controller still works, don't refresh
                    self._is_refreshing = False
                    return
                except pygame.error:
                    # Controller invalid, need to refresh
                    pass

            pygame.joystick.quit()
            pygame.joystick.init()
            self._scan_controllers()
        finally:
            self._is_refreshing = False

    def is_connected(self):
        """Check if a controller is connected"""
        return self.connected and self.active_controller is not None

    def get_controller_name(self):
        """Get name of active controller"""
        if self.active_controller:
            return self.active_controller.get_name()
        return "No Controller"

    def get_controller_guid(self):
        """Get SDL GUID of active controller (if available)"""
        if self.active_controller:
            try:
                return self.active_controller.get_guid()
            except (AttributeError, pygame.error):
                pass
        return None

    def get_profile_info(self):
        """
        Get info about the currently active controller profile.

        Returns:
            dict with "id", "description", "match_type" or None if no controller
        """
        if not self.connected:
            return None
        return {
            "id": self.active_profile_id,
            "description": self.active_profile_description,
            "match_type": self.active_profile_match_type,
        }

    def _is_button_pressed(self, button_name):
        """Check if a named button is currently pressed"""
        if not self.active_controller:
            return False

        try:
            indices = self.button_map.get(button_name, [])
            for idx in indices:
                if idx < self.active_controller.get_numbuttons():
                    if self.active_controller.get_button(idx):
                        return True
        except pygame.error:
            # Controller became invalid
            return False
        return False

    def _get_dpad_from_hat(self):
        """Get D-pad state from HAT input using the hat_map dict.

        The hat_map maps (hx, hy) tuples to direction strings.
        This is rebuilt by ButtonMapper when the user remaps d-pad directions,
        so it always reflects the current configuration.

        For diagonals we always decompose into cardinal components so both
        axes register (e.g. pressing up-right sets both 'up' and 'right').
        """
        directions = {"up": False, "down": False, "left": False, "right": False}

        if not self.active_controller:
            return directions

        try:
            if self.active_controller.get_numhats() > 0:
                hat = self.active_controller.get_hat(0)

                if hat == (0, 0):
                    return directions

                # Always check cardinal components independently so diagonals
                # register both axes (e.g. up-right → up AND right).
                if hat[0] != 0:
                    d = self.hat_map.get((hat[0], 0))
                    if d:
                        directions[d] = True
                if hat[1] != 0:
                    d = self.hat_map.get((0, hat[1]))
                    if d:
                        directions[d] = True
        except pygame.error:
            pass

        return directions

    def _get_dpad_from_axes(self):
        """Get D-pad state from analog stick(s).

        Checks all axis pairs in self.dpad_axis_pairs so controllers that
        report the d-pad or left stick on non-standard axes are supported.
        """
        directions = {"up": False, "down": False, "left": False, "right": False}

        if not self.active_controller:
            return directions

        try:
            num_axes = self.active_controller.get_numaxes()
            for x_idx, y_idx in self.dpad_axis_pairs:
                if x_idx < num_axes and y_idx < num_axes:
                    x_val = self.active_controller.get_axis(x_idx)
                    y_val = self.active_controller.get_axis(y_idx)

                    if x_val < -self.AXIS_DEADZONE:
                        directions["left"] = True
                    elif x_val > self.AXIS_DEADZONE:
                        directions["right"] = True

                    if y_val < -self.AXIS_DEADZONE:
                        directions["up"] = True
                    elif y_val > self.AXIS_DEADZONE:
                        directions["down"] = True
        except pygame.error:
            # Controller became invalid
            pass

        return directions

    def _get_dpad_from_buttons(self):
        """Get D-pad state from button-based d-pad.

        Some controllers report the d-pad as four regular buttons instead
        of a hat or axes. This checks the dpad_button_map config.
        """
        directions = {"up": False, "down": False, "left": False, "right": False}

        if not self.active_controller:
            return directions

        try:
            num_buttons = self.active_controller.get_numbuttons()
            for direction, indices in self.dpad_button_map.items():
                if indices is not None:
                    for idx in indices:
                        if idx < num_buttons and self.active_controller.get_button(idx):
                            directions[direction] = True
                            break
        except pygame.error:
            pass

        return directions

    def update(self, dt):
        """
        Update controller state and handle button repeat.
        Also polls keyboard for navigation so WASD/arrows drive the same
        dpad_states and button_repeat_ready as a physical controller.

        Args:
            dt: Delta time in milliseconds
        """
        # Check for pending controller refresh
        self._do_pending_refresh()

        # --- Keyboard navigation ---
        # Read keyboard state once and merge into dpad/button states.
        # This runs regardless of whether a gamepad is connected so
        # keyboard-only users get full navigation support.
        kb = pygame.key.get_pressed()

        self._kb_dpad_pressed = {k: any(kb[i] for i in v) for k, v in self.kb_nav_map.items() if k in self.dpad_states}
        self._kb_btn_pressed = {k: any(kb[i] for i in v) for k, v in self.kb_nav_map.items() if k in ["A", "B", "L", "R"]}

        # --- Gamepad state ---
        if self.active_controller:
            # Verify controller is still valid
            try:
                _ = self.active_controller.get_numbuttons()
            except pygame.error:
                self.active_controller = None
                self.connected = False
                self._schedule_refresh()

        # Update D-pad states (combine HAT, analog, button-dpad, and keyboard)
        # All three gamepad sources now respect configured mappings:
        # - _get_dpad_from_hat() uses hat_map (rebuilt when user remaps)
        # - _get_dpad_from_axes() uses dpad_axis_pairs
        # - _get_dpad_from_buttons() uses dpad_button_map
        no_dirs = dict.fromkeys(self.dpad_states, False)

        if self.active_controller:
            hat_dirs = self._get_dpad_from_hat()
            btn_dirs = self._get_dpad_from_buttons()

            # If button-based d-pad is active, completely ignore axes
            if any(self.dpad_button_map.values()):
                axis_dirs = dict.fromkeys(self.dpad_states, False)
            else:
                axis_dirs = self._get_dpad_from_axes()
        else:
            hat_dirs = no_dirs
            axis_dirs = no_dirs
            btn_dirs = no_dirs

        kb_dpad = getattr(self, "_kb_dpad_pressed", {})

        for direction in self.dpad_states:
            was_pressed = self.dpad_states[direction]
            is_pressed = hat_dirs[direction] or axis_dirs[direction] or btn_dirs[direction] or kb_dpad.get(direction, False)
            if is_pressed:
                if not was_pressed:
                    self.dpad_held_time[direction] = 0
                    if not self.dpad_consumed[direction]:
                        self.dpad_repeat_ready[direction] = True
                else:
                    self.dpad_held_time[direction] += dt
                    if self.dpad_held_time[direction] >= self.REPEAT_DELAY_INITIAL and not self.dpad_consumed[direction]:
                        repeat_time = self.dpad_held_time[direction] - self.REPEAT_DELAY_INITIAL
                        if repeat_time % self.REPEAT_DELAY_SUBSEQUENT < dt:
                            self.dpad_repeat_ready[direction] = True
            else:
                self.dpad_held_time[direction] = 0
                self.dpad_repeat_ready[direction] = False
                self.dpad_consumed[direction] = False
            self.dpad_states[direction] = is_pressed

        # Update button states (gamepad + keyboard)
        kb_btn = getattr(self, "_kb_btn_pressed", {})
        for button_name in self.button_map:
            was_pressed = self.button_states.get(button_name, False)
            gp_pressed = self._is_button_pressed(button_name)
            kb_pressed = kb_btn.get(button_name, False)
            is_pressed = gp_pressed or kb_pressed
            if is_pressed:
                if not was_pressed:
                    self.button_held_time[button_name] = 0
                    if not self.button_consumed.get(button_name, False):
                        self.button_repeat_ready[button_name] = True
                else:
                    self.button_held_time[button_name] = self.button_held_time.get(button_name, 0) + dt
            else:
                self.button_held_time[button_name] = 0
                self.button_repeat_ready[button_name] = False
                self.button_consumed[button_name] = False
            self.button_states[button_name] = is_pressed

    def get_nav_keys(self):
        """Return the set of pygame key constants currently handled by
        the keyboard navigation map.  Useful for filtering KEYDOWN events
        so they aren't processed twice (once via controller polling and
        once via raw event handling)."""
        keys = set()
        for key_list in self.kb_nav_map.values():
            for k in key_list:
                if isinstance(k, int):
                    keys.add(k)
        return keys

    def filter_kb_events(self, events):
        """Return a copy of *events* with KEYDOWN / KEYUP events removed
        for any key that the controller's keyboard-nav map already handles.

        Call this from the main loop **after** controller.update() so that
        screens which have both handle_controller() and handle_event()
        don't double-process the same keypress.

        Non-keyboard events and keyboard events for unmapped keys (F11,
        Alt, etc.) pass through unchanged.

        Set ``kb_filter_enabled = False`` to temporarily pass all events
        through unfiltered (e.g. while a key-capture screen is active).
        """
        if not getattr(self, "kb_filter_enabled", True):
            return events
        nav_keys = self.get_nav_keys()
        filtered = []
        for event in events:
            if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                if getattr(event, "key", None) in nav_keys:
                    continue  # drop — controller already handled it
            filtered.append(event)
        return filtered

    def process_event(self, event):
        """
        Process a pygame event and return controller events if applicable

        Args:
            event: pygame event

        Returns:
            list: List of ControllerEvent objects
        """
        events = []
        current_time = pygame.time.get_ticks()

        # Handle controller connect/disconnect with debouncing
        if event.type == pygame.JOYDEVICEADDED:
            # Only act if we don't have a working controller
            if not self.connected or not self.active_controller:
                if current_time - self._last_hotplug_time > self.HOTPLUG_DEBOUNCE_MS:
                    print("Controller connected!")
                    self._last_hotplug_time = current_time
                    self._schedule_refresh()
            # else: ignore, we already have a controller

        elif event.type == pygame.JOYDEVICEREMOVED:
            # Only act if this affects our active controller
            if current_time - self._last_hotplug_time > self.HOTPLUG_DEBOUNCE_MS:
                # Check if our controller is still valid
                if self.active_controller:
                    try:
                        _ = self.active_controller.get_numbuttons()
                        # Still valid, ignore the event
                    except pygame.error:
                        print("Controller disconnected!")
                        self._last_hotplug_time = current_time
                        self._schedule_refresh()

        # Handle button press
        elif event.type == pygame.JOYBUTTONDOWN:
            # Check if this button is a d-pad button first
            dpad_dir = self._get_dpad_direction_for_button(event.button)
            if dpad_dir:
                events.append(ControllerEvent("dpad", direction=dpad_dir))
            else:
                button_name = self._get_button_name(event.button)
                if button_name:
                    events.append(ControllerEvent("button", button=button_name))

        # Handle HAT (D-pad) press - decompose diagonals into cardinals
        elif event.type == pygame.JOYHATMOTION:
            hx, hy = event.value
            if hx != 0:
                direction = self.hat_map.get((hx, 0))
                if direction:
                    events.append(ControllerEvent("dpad", direction=direction))
            if hy != 0:
                direction = self.hat_map.get((0, hy))
                if direction:
                    events.append(ControllerEvent("dpad", direction=direction))

        # Handle axis motion (for D-pad simulation)
        elif event.type == pygame.JOYAXISMOTION:
            if any(self.dpad_button_map.values()):
                return events
            # Check if this axis is part of any configured d-pad axis pair
            for x_idx, y_idx in self.dpad_axis_pairs:
                if event.axis == x_idx:
                    if event.value < -self.AXIS_DEADZONE:
                        events.append(ControllerEvent("dpad", direction="left"))
                    elif event.value > self.AXIS_DEADZONE:
                        events.append(ControllerEvent("dpad", direction="right"))
                    break
                elif event.axis == y_idx:
                    if event.value < -self.AXIS_DEADZONE:
                        events.append(ControllerEvent("dpad", direction="up"))
                    elif event.value > self.AXIS_DEADZONE:
                        events.append(ControllerEvent("dpad", direction="down"))
                    break

        return events

    def _schedule_refresh(self):
        """Schedule a controller refresh (debounced)"""
        self._hotplug_pending = True

    def _do_pending_refresh(self):
        """Perform pending controller refresh if debounce time has passed"""
        if self._hotplug_pending:
            current_time = pygame.time.get_ticks()
            if current_time - self._last_hotplug_time > self.HOTPLUG_DEBOUNCE_MS:
                self._hotplug_pending = False
                self.refresh_controllers()

    def _get_button_name(self, button_index):
        """Get button name from index"""
        for name, indices in self.button_map.items():
            if button_index in indices:
                return name
        return None

    def _get_dpad_direction_for_button(self, button_index):
        """Check if a button index is mapped as a d-pad direction.

        Returns:
            Direction string ('up', 'down', 'left', 'right') or None
        """
        for direction, indices in self.dpad_button_map.items():
            if indices is not None and button_index in indices:
                return direction
        return None

    def get_pressed_buttons(self):
        """Get list of currently pressed button names"""
        return [name for name, pressed in self.button_states.items() if pressed]

    def get_dpad_direction(self):
        """
        Get current D-pad direction

        Returns:
            tuple: (x, y) where x is -1/0/1 for left/none/right
                   and y is -1/0/1 for up/none/down
        """
        x = 0
        y = 0

        if self.dpad_states["left"]:
            x = -1
        elif self.dpad_states["right"]:
            x = 1

        if self.dpad_states["up"]:
            y = -1
        elif self.dpad_states["down"]:
            y = 1

        return (x, y)

    def is_button_just_pressed(self, button_name):
        """Check if button was just pressed this frame"""
        return self.button_repeat_ready.get(button_name, False)

    def is_dpad_just_pressed(self, direction):
        """Check if D-pad direction was just pressed this frame"""
        return self.dpad_repeat_ready.get(direction, False)

    def consume_button(self, button_name):
        """Consume a button press (prevent repeat until released)"""
        self.button_repeat_ready[button_name] = False
        self.button_consumed[button_name] = True

    def consume_dpad(self, direction):
        """Consume a D-pad press (prevent repeat until released)"""
        self.dpad_repeat_ready[direction] = False
        self.dpad_consumed[direction] = True

    def to_keyboard_events(self):
        """
        Convert controller state to keyboard-like events for compatibility

        Returns:
            list: pygame.event.Event objects simulating keyboard input
        """
        events = []

        # D-pad to arrow keys
        if self.is_dpad_just_pressed("up"):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
            self.consume_dpad("up")
        if self.is_dpad_just_pressed("down"):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
            self.consume_dpad("down")
        if self.is_dpad_just_pressed("left"):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
            self.consume_dpad("left")
        if self.is_dpad_just_pressed("right"):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
            self.consume_dpad("right")

        # A button to Enter/Return
        if self.is_button_just_pressed("A"):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.consume_button("A")

        # B button to Escape
        if self.is_button_just_pressed("B"):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            self.consume_button("B")

        # Start button to Escape (menu)
        if self.is_button_just_pressed("START"):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            self.consume_button("START")

        # L/R to Page Up/Down
        if self.is_button_just_pressed("L"):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP))
            self.consume_button("L")
        if self.is_button_just_pressed("R"):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN))
            self.consume_button("R")

        return events

    def pause(self):
        """Releases the joystick hardware and silences input processing."""
        print("[Controller] Pausing input for external emulator...")
        self.connected = False
        # Physically shut down the joystick subsystem
        pygame.joystick.quit() 
        # Clear states so buttons aren't 'stuck' when we return
        self.button_states = {k: False for k in self.button_states}
        self.dpad_states = {k: False for k in self.dpad_states}

    def resume(self):
        """Re-init hardware and rebuild mappings."""
        current_swap_state = getattr(self, "_swap_ab", False)
        self._init_controllers()
        self.set_swap_ab(current_swap_state)
        print(f"[Controller] Resume complete. Swap restored to: {current_swap_state}")


class NavigableList:
    """
    Helper class for controller-navigable lists/grids

    Tracks selection index and handles wrap-around
    """

    def __init__(self, items, columns=1, wrap=True):
        """
        Initialize navigable list

        Args:
            items: List of items or item count
            columns: Number of columns (1 for vertical list)
            wrap: Whether to wrap around edges
        """
        self.count = len(items) if hasattr(items, "__len__") else items
        self.columns = columns
        self.wrap = wrap
        self.selected = 0

    def navigate(self, direction):
        """
        Navigate in a direction

        Args:
            direction: 'up', 'down', 'left', 'right'

        Returns:
            bool: True if selection changed
        """
        old_selected = self.selected
        rows = (self.count + self.columns - 1) // self.columns

        if direction == "up":
            new_idx = self.selected - self.columns
            if new_idx >= 0:
                self.selected = new_idx
            elif self.wrap:
                # Wrap to bottom
                col = self.selected % self.columns
                last_row_start = (rows - 1) * self.columns
                self.selected = min(last_row_start + col, self.count - 1)

        elif direction == "down":
            new_idx = self.selected + self.columns
            if new_idx < self.count:
                self.selected = new_idx
            elif self.wrap:
                # Wrap to top
                col = self.selected % self.columns
                self.selected = min(col, self.count - 1)

        elif direction == "left":
            if self.selected % self.columns > 0:
                self.selected -= 1
            elif self.wrap:
                # Wrap to end of row
                row_end = min(
                    (self.selected // self.columns + 1) * self.columns - 1,
                    self.count - 1,
                )
                self.selected = row_end

        elif direction == "right":
            if (
                self.selected % self.columns < self.columns - 1
                and self.selected + 1 < self.count
            ):
                self.selected += 1
            elif self.wrap:
                # Wrap to start of row
                row_start = (self.selected // self.columns) * self.columns
                self.selected = row_start

        return self.selected != old_selected

    def set_count(self, count):
        """Update item count"""
        self.count = count
        if self.selected >= count:
            self.selected = max(0, count - 1)

    def get_selected(self):
        """Get selected index"""
        return self.selected

    def set_selected(self, index):
        """Set selected index"""
        if 0 <= index < self.count:
            self.selected = index


# Global controller instance
_controller = None


def get_controller():
    """Get the global controller manager instance"""
    global _controller
    if _controller is None:
        _controller = ControllerManager()
    return _controller


def init_controller():
    """Initialize the global controller"""
    global _controller
    _controller = ControllerManager()
    return _controller