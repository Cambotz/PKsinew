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
"""

import pygame
from enum import IntEnum, auto


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
    L_ALT = 9   # Alternative L button index
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
        self.button = button    # ControllerButton or None
        self.direction = direction  # 'up', 'down', 'left', 'right' or None
    
    def __repr__(self):
        return f"ControllerEvent({self.type}, button={self.button}, direction={self.direction})"


class ControllerManager:
    """
    Manages controller input for the game
    
    Provides:
    - Controller detection and initialization
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
        
        # Hotplug debouncing
        self._last_hotplug_time = 0
        self._hotplug_pending = False
        self._is_refreshing = False  # Prevent re-entry
        
        # Button state tracking
        self.button_states = {}
        self.button_held_time = {}
        self.button_repeat_ready = {}
        
        # D-pad state (as buttons or axes)
        self.dpad_states = {
            'up': False,
            'down': False,
            'left': False,
            'right': False
        }
        self.dpad_held_time = {
            'up': 0,
            'down': 0,
            'left': 0,
            'right': 0
        }
        self.dpad_repeat_ready = {
            'up': False,
            'down': False,
            'left': False,
            'right': False
        }
        
        # Button mapping for Xbox controllers
        # Xbox Elite 2: A=0, B=1, X=2, Y=3, LB=4, RB=5, Back/View=6, Start/Menu=7
        self.button_map = {
            'A': [0],           # A button
            'B': [1],           # B button
            'X': [2],           # X button
            'Y': [3],           # Y button
            'L': [4],           # Left shoulder (LB)
            'R': [5],           # Right shoulder (RB)
            'SELECT': [6],      # Select/Back/View
            'START': [7],       # Start/Menu
        }
        
        # Store original A/B for swap functionality
        self._original_a = [0]
        self._original_b = [1]
        self._swap_ab = False
        
        # HAT (D-pad) mapping
        self.hat_map = {
            (0, 1): 'up',
            (0, -1): 'down',
            (-1, 0): 'left',
            (1, 0): 'right',
            (1, 1): 'up',      # Diagonal up-right
            (-1, 1): 'up',     # Diagonal up-left
            (1, -1): 'down',   # Diagonal down-right
            (-1, -1): 'down',  # Diagonal down-left
        }
        
        # Load saved button mappings
        self._load_config()
        
        self._init_controllers()
    
    def _load_config(self):
        """Load saved controller configuration from sinew_settings.json"""
        import json
        import os
        
        config_file = "sinew_settings.json"
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Apply saved button mappings
                if 'controller_mapping' in config:
                    saved_map = config['controller_mapping']
                    for btn in ['A', 'B', 'L', 'R', 'SELECT', 'START']:
                        if btn in saved_map:
                            val = saved_map[btn]
                            # Ensure it's a list of integers
                            if isinstance(val, list):
                                self.button_map[btn] = [v for v in val if isinstance(v, int)]
                            elif isinstance(val, int):
                                self.button_map[btn] = [val]
                    print(f"[Controller] Loaded saved mappings from {config_file}")
                
                # Load swap_ab setting from same file
                swap_ab = config.get("swap_ab", False)
                if swap_ab:
                    # Store originals first
                    self._original_a = self.button_map['A'][:]
                    self._original_b = self.button_map['B'][:]
                    self.set_swap_ab(True)
                    return
        except Exception as e:
            print(f"[Controller] Error loading config: {e}")
        
        # Store original A/B after loading custom mappings
        self._original_a = self.button_map['A'][:]
        self._original_b = self.button_map['B'][:]
    
    def set_swap_ab(self, enabled):
        """Swap A and B button mappings"""
        if enabled == self._swap_ab:
            return  # No change needed
        
        self._swap_ab = enabled
        
        if enabled:
            # Swap A and B
            self.button_map['A'] = self._original_b[:]
            self.button_map['B'] = self._original_a[:]
        else:
            # Restore original
            self.button_map['A'] = self._original_a[:]
            self.button_map['B'] = self._original_b[:]
        
        print(f"[Controller] A/B swap {'enabled' if enabled else 'disabled'}: A={self.button_map['A']}, B={self.button_map['B']}")
    
    def _init_controllers(self):
        """Initialize pygame joystick subsystem and detect controllers"""
        pygame.joystick.init()
        self._scan_controllers()
    
    def _scan_controllers(self):
        """Scan for connected controllers"""
        self.controllers = []
        
        try:
            count = pygame.joystick.get_count()
        except pygame.error:
            count = 0
        
        for i in range(count):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
                self.controllers.append(joy)
                print(f"Controller {i}: {joy.get_name()}")
                print(f"  Buttons: {joy.get_numbuttons()}")
                print(f"  Axes: {joy.get_numaxes()}")
                print(f"  Hats: {joy.get_numhats()}")
            except pygame.error as e:
                print(f"Error initializing controller {i}: {e}")
        
        if self.controllers:
            self.active_controller = self.controllers[0]
            self.connected = True
            print(f"Active controller: {self.active_controller.get_name()}")
        else:
            self.active_controller = None
            self.connected = False
            # Don't print "No controllers" on every scan to reduce spam
    
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
        """Get D-pad state from HAT input"""
        directions = {'up': False, 'down': False, 'left': False, 'right': False}
        
        if not self.active_controller:
            return directions
        
        try:
            if self.active_controller.get_numhats() > 0:
                hat = self.active_controller.get_hat(0)
                
                # Horizontal
                if hat[0] < 0:
                    directions['left'] = True
                elif hat[0] > 0:
                    directions['right'] = True
                
                # Vertical (hat Y is inverted in pygame)
                if hat[1] > 0:
                    directions['up'] = True
                elif hat[1] < 0:
                    directions['down'] = True
        except pygame.error:
            # Controller became invalid
            pass
        
        return directions
    
    def _get_dpad_from_axes(self):
        """Get D-pad state from analog stick"""
        directions = {'up': False, 'down': False, 'left': False, 'right': False}
        
        if not self.active_controller:
            return directions
        
        try:
            if self.active_controller.get_numaxes() >= 2:
                x_axis = self.active_controller.get_axis(0)
                y_axis = self.active_controller.get_axis(1)
                
                if x_axis < -self.AXIS_DEADZONE:
                    directions['left'] = True
                elif x_axis > self.AXIS_DEADZONE:
                    directions['right'] = True
                
                if y_axis < -self.AXIS_DEADZONE:
                    directions['up'] = True
                elif y_axis > self.AXIS_DEADZONE:
                    directions['down'] = True
        except pygame.error:
            # Controller became invalid
            pass
        
        return directions
    
    def update(self, dt):
        """
        Update controller state and handle button repeat
        
        Args:
            dt: Delta time in milliseconds
        """
        # Check for pending controller refresh
        self._do_pending_refresh()
        
        if not self.active_controller:
            return
        
        # Verify controller is still valid
        try:
            _ = self.active_controller.get_numbuttons()
        except pygame.error:
            # Controller became invalid
            self.active_controller = None
            self.connected = False
            self._schedule_refresh()
            return
        
        # Update D-pad states (combine HAT and analog)
        hat_dirs = self._get_dpad_from_hat()
        axis_dirs = self._get_dpad_from_axes()
        
        for direction in ['up', 'down', 'left', 'right']:
            was_pressed = self.dpad_states[direction]
            is_pressed = hat_dirs[direction] or axis_dirs[direction]
            
            if is_pressed:
                if not was_pressed:
                    # Just pressed
                    self.dpad_held_time[direction] = 0
                    self.dpad_repeat_ready[direction] = True
                else:
                    # Still held
                    self.dpad_held_time[direction] += dt
                    
                    if self.dpad_held_time[direction] >= self.REPEAT_DELAY_INITIAL:
                        # Enable repeat after initial delay
                        repeat_time = self.dpad_held_time[direction] - self.REPEAT_DELAY_INITIAL
                        if repeat_time % self.REPEAT_DELAY_SUBSEQUENT < dt:
                            self.dpad_repeat_ready[direction] = True
            else:
                self.dpad_held_time[direction] = 0
                self.dpad_repeat_ready[direction] = False
            
            self.dpad_states[direction] = is_pressed
        
        # Update button states
        for button_name in self.button_map:
            was_pressed = self.button_states.get(button_name, False)
            is_pressed = self._is_button_pressed(button_name)
            
            if is_pressed:
                if not was_pressed:
                    self.button_held_time[button_name] = 0
                    self.button_repeat_ready[button_name] = True
                else:
                    self.button_held_time[button_name] = self.button_held_time.get(button_name, 0) + dt
            else:
                self.button_held_time[button_name] = 0
                self.button_repeat_ready[button_name] = False
            
            self.button_states[button_name] = is_pressed
    
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
            button_name = self._get_button_name(event.button)
            if button_name:
                events.append(ControllerEvent('button', button=button_name))
        
        # Handle HAT (D-pad) press
        elif event.type == pygame.JOYHATMOTION:
            direction = self.hat_map.get(event.value)
            if direction:
                events.append(ControllerEvent('dpad', direction=direction))
        
        # Handle axis motion (for D-pad simulation)
        elif event.type == pygame.JOYAXISMOTION:
            if event.axis in (0, 1):  # Left stick
                if event.axis == 0:  # X axis
                    if event.value < -self.AXIS_DEADZONE:
                        events.append(ControllerEvent('dpad', direction='left'))
                    elif event.value > self.AXIS_DEADZONE:
                        events.append(ControllerEvent('dpad', direction='right'))
                elif event.axis == 1:  # Y axis
                    if event.value < -self.AXIS_DEADZONE:
                        events.append(ControllerEvent('dpad', direction='up'))
                    elif event.value > self.AXIS_DEADZONE:
                        events.append(ControllerEvent('dpad', direction='down'))
        
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
        
        if self.dpad_states['left']:
            x = -1
        elif self.dpad_states['right']:
            x = 1
        
        if self.dpad_states['up']:
            y = -1
        elif self.dpad_states['down']:
            y = 1
        
        return (x, y)
    
    def is_button_just_pressed(self, button_name):
        """Check if button was just pressed this frame"""
        return self.button_repeat_ready.get(button_name, False)
    
    def is_dpad_just_pressed(self, direction):
        """Check if D-pad direction was just pressed this frame"""
        return self.dpad_repeat_ready.get(direction, False)
    
    def consume_button(self, button_name):
        """Consume a button press (prevent repeat)"""
        self.button_repeat_ready[button_name] = False
    
    def consume_dpad(self, direction):
        """Consume a D-pad press (prevent repeat)"""
        self.dpad_repeat_ready[direction] = False
    
    def to_keyboard_events(self):
        """
        Convert controller state to keyboard-like events for compatibility
        
        Returns:
            list: pygame.event.Event objects simulating keyboard input
        """
        events = []
        
        # D-pad to arrow keys
        if self.is_dpad_just_pressed('up'):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
            self.consume_dpad('up')
        if self.is_dpad_just_pressed('down'):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
            self.consume_dpad('down')
        if self.is_dpad_just_pressed('left'):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
            self.consume_dpad('left')
        if self.is_dpad_just_pressed('right'):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
            self.consume_dpad('right')
        
        # A button to Enter/Return
        if self.is_button_just_pressed('A'):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.consume_button('A')
        
        # B button to Escape
        if self.is_button_just_pressed('B'):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            self.consume_button('B')
        
        # Start button to Escape (menu)
        if self.is_button_just_pressed('START'):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            self.consume_button('START')
        
        # L/R to Page Up/Down
        if self.is_button_just_pressed('L'):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP))
            self.consume_button('L')
        if self.is_button_just_pressed('R'):
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN))
            self.consume_button('R')
        
        return events


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
        self.count = len(items) if hasattr(items, '__len__') else items
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
        
        if direction == 'up':
            new_idx = self.selected - self.columns
            if new_idx >= 0:
                self.selected = new_idx
            elif self.wrap:
                # Wrap to bottom
                col = self.selected % self.columns
                last_row_start = (rows - 1) * self.columns
                self.selected = min(last_row_start + col, self.count - 1)
        
        elif direction == 'down':
            new_idx = self.selected + self.columns
            if new_idx < self.count:
                self.selected = new_idx
            elif self.wrap:
                # Wrap to top
                col = self.selected % self.columns
                self.selected = min(col, self.count - 1)
        
        elif direction == 'left':
            if self.selected % self.columns > 0:
                self.selected -= 1
            elif self.wrap:
                # Wrap to end of row
                row_end = min((self.selected // self.columns + 1) * self.columns - 1, self.count - 1)
                self.selected = row_end
        
        elif direction == 'right':
            if self.selected % self.columns < self.columns - 1 and self.selected + 1 < self.count:
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