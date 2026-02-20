import pygame

class Scaler:
    """
    Handles resolution scaling and fullscreen for the game.
    Uses SDL's hardware scaling (pygame.SCALED) for GPU-accelerated rendering.
    """
    
    # Common resolution presets (16:9 and 4:3 friendly)
    RESOLUTION_PRESETS = [
        (640, 480),    # 4:3 - Original
        (800, 600),    # 4:3
        (1024, 768),   # 4:3
        (1280, 720),   # 16:9 HD
        (1280, 960),   # 4:3
        (1600, 900),   # 16:9
        (1920, 1080),  # 16:9 Full HD
        (2560, 1440),  # 16:9 QHD
    ]
    
    def __init__(self, virtual_width=240, virtual_height=160, 
                 window_width=720, window_height=480, 
                 fullscreen=False, integer_scaling=False):
        """
        Initialize the scaler.
        
        Args:
            virtual_width: Internal game resolution width (never changes)
            virtual_height: Internal game resolution height (never changes)
            window_width: Initial window width (used for software scaling fallback)
            window_height: Initial window height (used for software scaling fallback)
            fullscreen: Start in fullscreen mode
            integer_scaling: Only scale by whole numbers (pixel-perfect)
        """
        # Virtual game resolution (fixed - this is what the game renders at)
        self.virtual_width = virtual_width
        self.virtual_height = virtual_height
        
        # Store default virtual resolution for restoring after emulator
        self._default_virtual_width = virtual_width
        self._default_virtual_height = virtual_height
        
        # Window size for software scaling fallback
        self.window_width = window_width
        self.window_height = window_height
        
        # Settings
        self.fullscreen = fullscreen
        self.integer_scaling = integer_scaling
        
        # Store windowed size for returning from fullscreen
        self._windowed_width = window_width
        self._windowed_height = window_height
        
        # Hardware vs software scaling
        self.use_hardware_scaling = True
        
        # Create window
        self._create_window()
        
        # Compute scaling for mouse coordinate conversion
        self.update_scale()
    
    def _create_window(self):
        """Create or recreate the display window"""
        if self.use_hardware_scaling:
            self._create_window_hardware()
        else:
            self._create_window_software()
    
    def _create_window_hardware(self):
        """Create window with hardware (GPU) scaling via pygame.SCALED"""
        # Build flags
        flags = pygame.SCALED | pygame.RESIZABLE
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
        
        # Render at virtual resolution - SDL handles scaling via GPU
        self.window = pygame.display.set_mode(
            (self.virtual_width, self.virtual_height),
            flags
        )
        
        # With SCALED, the virtual surface IS the window
        self.virtual_surface = self.window
        
        # Get actual display size for reference
        display_info = pygame.display.Info()
        if self.fullscreen:
            self.window_width = display_info.current_w
            self.window_height = display_info.current_h
        
        pygame.display.set_caption("Sinew")
        print(f"[Scaler] Hardware scaling: {self.virtual_width}x{self.virtual_height} -> "
              f"{'fullscreen' if self.fullscreen else 'windowed'}")
    
    def _create_window_software(self):
        """Create window with software scaling (fallback)"""
        if self.fullscreen:
            display_info = pygame.display.Info()
            desktop_w = display_info.current_w
            desktop_h = display_info.current_h
            
            modes = pygame.display.list_modes()
            if modes and modes != -1:
                desktop_w, desktop_h = modes[0]
            
            self.window = pygame.display.set_mode(
                (desktop_w, desktop_h),
                pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
            )
            
            actual_size = self.window.get_size()
            self.window_width = actual_size[0] if actual_size[0] > 0 else desktop_w
            self.window_height = actual_size[1] if actual_size[1] > 0 else desktop_h
        else:
            self.window = pygame.display.set_mode(
                (self.window_width, self.window_height),
                pygame.RESIZABLE
            )
        
        # Create separate virtual surface for software scaling
        self.virtual_surface = pygame.Surface((self.virtual_width, self.virtual_height))
        
        pygame.display.set_caption("Sinew")
        print(f"[Scaler] Software scaling: {self.window_width}x{self.window_height}")
    
    def update_scale(self):
        """Calculate scale factor for mouse coordinate conversion"""
        # For hardware scaling, get the actual window size
        if self.use_hardware_scaling:
            try:
                actual_surface = pygame.display.get_surface()
                if actual_surface:
                    # With SCALED, get_surface returns virtual size
                    # We need the actual window size for mouse scaling
                    display_info = pygame.display.Info()
                    self.window_width = display_info.current_w if self.fullscreen else self._windowed_width
                    self.window_height = display_info.current_h if self.fullscreen else self._windowed_height
            except:
                pass
        
        self.scale_x = self.window_width / self.virtual_width
        self.scale_y = self.window_height / self.virtual_height
        self.scale = min(self.scale_x, self.scale_y)
        
        if self.integer_scaling and self.scale >= 1:
            self.scale = int(self.scale)
        
        self.scaled_width = int(self.virtual_width * self.scale)
        self.scaled_height = int(self.virtual_height * self.scale)
        
        self.offset_x = (self.window_width - self.scaled_width) // 2
        self.offset_y = (self.window_height - self.scaled_height) // 2
        
        print(f"[Scaler] Scale: {self.scale:.2f}, Offset: ({self.offset_x}, {self.offset_y})")
    
    def handle_resize(self, new_width, new_height):
        """Handle window resize event"""
        if not self.fullscreen:
            self.window_width = new_width
            self.window_height = new_height
            self._windowed_width = new_width
            self._windowed_height = new_height
            
            if not self.use_hardware_scaling:
                self.window = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
            
            self.update_scale()
    
    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode"""
        self.fullscreen = not self.fullscreen
        
        if not self.fullscreen:
            self.window_width = self._windowed_width
            self.window_height = self._windowed_height
        
        if self.use_hardware_scaling:
            # For hardware scaling, we need to recreate with proper flags
            # pygame.display.toggle_fullscreen() doesn't work reliably with SCALED
            try:
                # Quit display subsystem and reinitialize
                pygame.display.quit()
                pygame.display.init()
                self._create_window_hardware()
            except pygame.error as e:
                print(f"[Scaler] Hardware toggle failed: {e}, falling back to software")
                self.use_hardware_scaling = False
                pygame.display.quit()
                pygame.display.init()
                self._create_window_software()
        else:
            self._create_window_software()
        
        self.update_scale()
        
        print(f"[Scaler] Toggled to {'fullscreen' if self.fullscreen else 'windowed'}")
        return self.fullscreen
    
    def set_fullscreen(self, enabled):
        """Set fullscreen mode explicitly"""
        if enabled != self.fullscreen:
            self.toggle_fullscreen()
    
    def set_resolution(self, width, height):
        """Set window resolution (only applies in windowed mode)"""
        if not self.fullscreen:
            self.window_width = width
            self.window_height = height
            self._windowed_width = width
            self._windowed_height = height
            
            if not self.use_hardware_scaling:
                self.window = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            
            self.update_scale()
    
    def set_integer_scaling(self, enabled):
        """Enable/disable integer scaling"""
        self.integer_scaling = enabled
        self.update_scale()
    
    def set_virtual_resolution(self, width, height):
        """
        Change the virtual resolution and recreate the display.
        Used to switch between menu resolution (480x320) and
        emulator resolution (240x160) for direct GPU scaling.
        """
        if width == self.virtual_width and height == self.virtual_height:
            return  # No change needed
        
        self.virtual_width = width
        self.virtual_height = height
        
        # Recreate the display at the new virtual resolution
        if self.use_hardware_scaling:
            try:
                pygame.display.quit()
                pygame.display.init()
                self._create_window_hardware()
            except pygame.error as e:
                print(f"[Scaler] Virtual resolution switch failed: {e}, falling back to software")
                self.use_hardware_scaling = False
                pygame.display.quit()
                pygame.display.init()
                self._create_window_software()
        else:
            self._create_window_software()
        
        self.update_scale()
        print(f"[Scaler] Virtual resolution set to {width}x{height}")
    
    def restore_virtual_resolution(self):
        """Restore the default virtual resolution (e.g., after emulator exits)."""
        self.set_virtual_resolution(self._default_virtual_width, self._default_virtual_height)
    
    def scale_mouse(self, pos):
        """Convert window mouse coordinates to virtual surface coordinates"""
        if self.use_hardware_scaling:
            # With pygame.SCALED, coordinates are already in virtual space
            return pos
        
        x, y = pos
        x = (x - self.offset_x) / self.scale
        y = (y - self.offset_y) / self.scale
        return int(x), int(y)
    
    def is_mouse_in_bounds(self, pos):
        """Check if mouse position is within the game area"""
        if self.use_hardware_scaling:
            x, y = pos
            return 0 <= x < self.virtual_width and 0 <= y < self.virtual_height
        
        x, y = pos
        return (self.offset_x <= x < self.offset_x + self.scaled_width and
                self.offset_y <= y < self.offset_y + self.scaled_height)
    
    def scale_mouse_clamped(self, pos):
        """Convert mouse coordinates, clamped to virtual surface bounds"""
        x, y = self.scale_mouse(pos)
        x = max(0, min(self.virtual_width - 1, x))
        y = max(0, min(self.virtual_height - 1, y))
        return x, y
    
    def blit_scaled(self):
        """Draw virtual surface to window, scaled"""
        if self.use_hardware_scaling:
            # Hardware scaling - just flip, SDL handles the rest
            pygame.display.flip()
            return
        
        # Software scaling fallback
        display_surface = pygame.display.get_surface()
        if display_surface is None:
            display_surface = self.window
        
        if self.integer_scaling:
            scaled_surface = pygame.transform.scale(
                self.virtual_surface,
                (self.scaled_width, self.scaled_height)
            )
        else:
            scaled_surface = pygame.transform.smoothscale(
                self.virtual_surface,
                (self.scaled_width, self.scaled_height)
            )
        
        display_surface.fill((0, 0, 0))
        display_surface.blit(scaled_surface, (self.offset_x, self.offset_y))
        pygame.display.flip()
    
    def get_surface(self):
        """Get the virtual surface to render to"""
        return self.virtual_surface
    
    def get_resolution_presets(self):
        """Get list of available resolution presets that fit the current display"""
        display_info = pygame.display.Info()
        max_w, max_h = display_info.current_w, display_info.current_h
        
        margin = 100
        available = [(w, h) for w, h in self.RESOLUTION_PRESETS 
                     if w <= max_w - margin and h <= max_h - margin]
        return available
    
    def get_current_resolution(self):
        """Get current window resolution"""
        return (self.window_width, self.window_height)
    
    def get_virtual_resolution(self):
        """Get the internal game resolution"""
        return (self.virtual_width, self.virtual_height)
    
    def get_settings(self):
        """Get current settings as a dict (for saving)"""
        return {
            'window_width': self._windowed_width,
            'window_height': self._windowed_height,
            'fullscreen': self.fullscreen,
            'integer_scaling': self.integer_scaling,
            'hardware_scaling': self.use_hardware_scaling,
        }
    
    def load_settings(self, settings):
        """Load settings from a dict"""
        if 'integer_scaling' in settings:
            self.integer_scaling = settings['integer_scaling']
        if 'hardware_scaling' in settings:
            self.use_hardware_scaling = settings.get('hardware_scaling', True)
        if 'fullscreen' in settings:
            self.fullscreen = settings['fullscreen']
        if 'window_width' in settings and 'window_height' in settings:
            self._windowed_width = settings['window_width']
            self._windowed_height = settings['window_height']
            if not self.fullscreen:
                self.window_width = self._windowed_width
                self.window_height = self._windowed_height
        
        self._create_window()
        self.update_scale()