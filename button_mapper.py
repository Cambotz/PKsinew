"""
Sinew Button Mapper
Visual GBA-style button mapping screen with controller support
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
    """
    
    # Default button mappings (button name -> list of controller indices)
    DEFAULT_MAPPING = {
        'A': [0],
        'B': [1],
        'L': [4],
        'R': [5],
        'SELECT': [6],
        'START': [7],
        'DPAD_UP': ['hat_up', 'axis_y_neg'],
        'DPAD_DOWN': ['hat_down', 'axis_y_pos'],
        'DPAD_LEFT': ['hat_left', 'axis_x_neg'],
        'DPAD_RIGHT': ['hat_right', 'axis_x_pos'],
    }
    
    # Buttons available for rebinding (in Quick Setup order)
    BINDABLE_BUTTONS = ['A', 'B', 'L', 'R', 'START', 'SELECT']
    
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
        
        # Load or create mapping
        self.mapping = self._load_mapping()
        
        # Sync with controller's current mapping if available
        if self.controller:
            for btn in ['A', 'B', 'L', 'R', 'SELECT', 'START']:
                if btn in self.controller.button_map:
                    self.mapping[btn] = self.controller.button_map[btn].copy()
        
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
        """Load mapping from config file or use defaults"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get(self.CONFIG_KEY, self.DEFAULT_MAPPING.copy())
        except Exception as e:
            print(f"[ButtonMapper] Error loading config: {e}")
        return self.DEFAULT_MAPPING.copy()
    
    def _save_mapping(self):
        """Save mapping to config file"""
        try:
            # Load existing config or create new
            config = {}
            if os.path.exists(self.CONFIG_FILE):
                try:
                    with open(self.CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                except:
                    pass
            
            config[self.CONFIG_KEY] = self.mapping
            
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"[ButtonMapper] Saved config to {self.CONFIG_FILE}")
            return True
        except Exception as e:
            print(f"[ButtonMapper] Error saving config: {e}")
            return False
    
    def _apply_mapping_to_controller(self):
        """Apply current mapping to the controller manager"""
        if self.controller:
            # Update the controller's button_map with our mapping
            # Only for standard buttons (not D-pad which is handled separately)
            for btn in ['A', 'B', 'L', 'R', 'SELECT', 'START']:
                if btn in self.mapping:
                    val = self.mapping[btn]
                    # Ensure it's a list of integers
                    if isinstance(val, list):
                        self.controller.button_map[btn] = [v for v in val if isinstance(v, int)]
                    elif isinstance(val, int):
                        self.controller.button_map[btn] = [val]
            print("[ButtonMapper] Applied mapping to controller")
    
    def _get_binding_display(self, button_name):
        """Get display string for a button's current binding"""
        if button_name not in self.mapping:
            return "?"
        
        bindings = self.mapping[button_name]
        if not bindings:
            return "None"
        
        # For standard button bindings (integers)
        if isinstance(bindings[0], int):
            return f"Btn {bindings[0]}"
        
        # For D-pad (special strings)
        return "D-pad"
    
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
        """Start listening for a new binding"""
        if button_name.startswith('DPAD_'):
            # D-pad buttons can't be rebound in this version
            return
        
        self.listening = True
        self.listening_button = button_name
        self.listen_start_time = pygame.time.get_ticks()
        print(f"[ButtonMapper] Listening for new binding for {button_name}...")
    
    def _show_status(self, message, color=None):
        """Show a status message"""
        self.status_message = message
        self.status_time = pygame.time.get_ticks()
        self.status_color = color if color else COLOR_TEXT
    
    def _stop_listening(self, new_binding=None):
        """Stop listening and optionally apply new binding"""
        if new_binding is not None and self.listening_button:
            # Check for duplicates
            dup = self._is_duplicate_binding(new_binding, self.listening_button)
            if dup:
                print(f"[ButtonMapper] Button {new_binding} already bound to {dup}!")
                # Clear the duplicate binding
                self.mapping[dup] = []
                self._show_status(f"Cleared {dup} binding", (255, 180, 100))
            
            self.mapping[self.listening_button] = [new_binding]
            print(f"[ButtonMapper] Bound {self.listening_button} to button {new_binding}")
            self._show_status(f"{self.listening_button} -> Btn {new_binding}", (100, 255, 150))
        elif self.listening_button:
            # Timeout or cancelled
            self._show_status("Cancelled", (150, 150, 150))
        
        self.listening = False
        self.listening_button = None
        
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
        """Reset all mappings to default"""
        self.mapping = self.DEFAULT_MAPPING.copy()
        self._apply_mapping_to_controller()
        self._show_status("Reset to defaults", (100, 200, 255))
        print("[ButtonMapper] Reset to default mappings")
    
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
            
            # Listen for controller button presses when rebinding
            if self.listening and event.type == pygame.JOYBUTTONDOWN:
                self._stop_listening(event.button)
    
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
            # Activate button for rebinding
            btn = self.button_list[self.selected_index]
            if not btn.startswith('DPAD_'):
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
        
        # Draw GBA visual
        self._draw_gba(surf)
        
        # Draw screen content (status/instructions)
        self._draw_screen_content(surf)
        
        # Draw menu options
        self._draw_menu(surf)
        
        # Draw controller hints
        hints = "D-Pad: Navigate   A: Select   B: Back"
        if self.listening:
            hints = "Press a button to bind   B: Cancel"
        hint_surf = self.font_small.render(hints, True, (100, 100, 100))
        hint_rect = hint_surf.get_rect(centerx=self.width // 2, bottom=self.height - 8)
        surf.blit(hint_surf, hint_rect)
    
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
                if is_dpad:
                    text = ""  # No text for D-pad
                else:
                    binding = self._get_binding_display(btn_name)
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
            
            # Button name
            btn_text = f"Bind: {self.listening_button}"
            btn_surf = self.font_text.render(btn_text, True, (150, 200, 150))
            btn_rect = btn_surf.get_rect(centerx=self.screen_rect.centerx,
                                         centery=self.screen_rect.centery - 20)
            surf.blit(btn_surf, btn_rect)
            
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
            lines = ["Select button", "to rebind", "", "A: Bind", "D-Pad: Navigate"]
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