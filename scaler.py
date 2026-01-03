import pygame

class Scaler:
    """
    Handles resolution scaling and fullscreen for the game.
    All game rendering happens on virtual_surface at a fixed resolution,
    then gets scaled to fit the actual window.
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
            window_width: Initial window width
            window_height: Initial window height
            fullscreen: Start in fullscreen mode
            integer_scaling: Only scale by whole numbers (pixel-perfect but may have larger letterbox)
        """
        # Virtual game resolution (fixed - this is what the game renders at)
        self.virtual_width = virtual_width
        self.virtual_height = virtual_height
        
        # Actual window resolution
        self.window_width = window_width
        self.window_height = window_height
        
        # Settings
        self.fullscreen = fullscreen
        self.integer_scaling = integer_scaling
        
        # Store windowed size for returning from fullscreen
        self._windowed_width = window_width
        self._windowed_height = window_height
        
        # Create virtual surface (game renders here)
        self.virtual_surface = pygame.Surface((virtual_width, virtual_height))
        
        # Create window
        self._create_window()
        
        # Compute scaling
        self.update_scale()
    
    def _create_window(self):
        """Create or recreate the display window"""
        if self.fullscreen:
            # Get native desktop resolution before changing modes
            # Try multiple methods to ensure we get the right size
            display_info = pygame.display.Info()
            desktop_w = display_info.current_w
            desktop_h = display_info.current_h
            
            # Try to get list of available fullscreen modes
            modes = pygame.display.list_modes()
            if modes and modes != -1:
                # Use the largest available mode (first in list)
                desktop_w, desktop_h = modes[0]
            
            # Set fullscreen with explicit resolution
            self.window = pygame.display.set_mode(
                (desktop_w, desktop_h),
                pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
            )
            
            # Update our tracked dimensions to match actual fullscreen size
            actual_size = self.window.get_size()
            self.window_width = actual_size[0] if actual_size[0] > 0 else desktop_w
            self.window_height = actual_size[1] if actual_size[1] > 0 else desktop_h
            
            print(f"[Scaler] Fullscreen: {self.window_width}x{self.window_height}")
        else:
            self.window = pygame.display.set_mode(
                (self.window_width, self.window_height),
                pygame.RESIZABLE
            )
            print(f"[Scaler] Windowed: {self.window_width}x{self.window_height}")
        
        pygame.display.set_caption("Sinew")
    
    def update_scale(self):
        """Calculate scale factor to preserve aspect ratio"""
        self.scale_x = self.window_width / self.virtual_width
        self.scale_y = self.window_height / self.virtual_height
        self.scale = min(self.scale_x, self.scale_y)
        
        # Integer scaling for pixel-perfect rendering
        if self.integer_scaling and self.scale >= 1:
            self.scale = int(self.scale)
        
        # Calculate scaled dimensions
        self.scaled_width = int(self.virtual_width * self.scale)
        self.scaled_height = int(self.virtual_height * self.scale)
        
        # Letterbox offsets (center the game in the window)
        self.offset_x = (self.window_width - self.scaled_width) // 2
        self.offset_y = (self.window_height - self.scaled_height) // 2
        
        print(f"[Scaler] Scale: {self.scale:.2f}, Scaled size: {self.scaled_width}x{self.scaled_height}, Offset: ({self.offset_x}, {self.offset_y})")
    
    def handle_resize(self, new_width, new_height):
        """Handle window resize event"""
        if not self.fullscreen:
            self.window_width = new_width
            self.window_height = new_height
            self._windowed_width = new_width
            self._windowed_height = new_height
            self.window = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
            self.update_scale()
    
    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode"""
        self.fullscreen = not self.fullscreen
        
        if not self.fullscreen:
            # Restore windowed size
            self.window_width = self._windowed_width
            self.window_height = self._windowed_height
        
        self._create_window()
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
            self.window = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            self.update_scale()
    
    def set_integer_scaling(self, enabled):
        """Enable/disable integer scaling"""
        self.integer_scaling = enabled
        self.update_scale()
    
    def scale_mouse(self, pos):
        """Convert window mouse coordinates to virtual surface coordinates"""
        x, y = pos
        x = (x - self.offset_x) / self.scale
        y = (y - self.offset_y) / self.scale
        return int(x), int(y)
    
    def is_mouse_in_bounds(self, pos):
        """Check if mouse position (window coords) is within the game area"""
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
        """Draw virtual surface to window, scaled with letterbox"""
        # Get current display surface (in case it changed)
        display_surface = pygame.display.get_surface()
        if display_surface is None:
            display_surface = self.window
        
        # Choose scaling method based on settings
        if self.integer_scaling:
            # Use nearest neighbor for crisp pixels
            scaled_surface = pygame.transform.scale(
                self.virtual_surface,
                (self.scaled_width, self.scaled_height)
            )
        else:
            # Use smooth scaling for better appearance at non-integer scales
            scaled_surface = pygame.transform.smoothscale(
                self.virtual_surface,
                (self.scaled_width, self.scaled_height)
            )
        
        # Clear window (letterbox bars will be black)
        display_surface.fill((0, 0, 0))
        
        # Draw scaled game surface centered in window
        display_surface.blit(scaled_surface, (self.offset_x, self.offset_y))
        
        # Update display
        pygame.display.flip()
    
    def get_surface(self):
        """Get the virtual surface to render to"""
        return self.virtual_surface
    
    def get_resolution_presets(self):
        """Get list of available resolution presets that fit the current display"""
        display_info = pygame.display.Info()
        max_w, max_h = display_info.current_w, display_info.current_h
        
        # Filter presets that fit on screen (with some margin for window decorations)
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
        }
    
    def load_settings(self, settings):
        """Load settings from a dict"""
        if 'integer_scaling' in settings:
            self.integer_scaling = settings['integer_scaling']
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