"""
Database Builder Screen
Shows a terminal-like output box for building/rebuilding the Pokemon database
"""

import os
import sys
import subprocess
import threading
import pygame
import ui_colors
from controller import get_controller, NavigableList

# Import config for paths
try:
    import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


class DBBuilderScreen:
    """Screen for building/rebuilding the Pokemon database with live output"""
    
    def __init__(self, width, height, close_callback=None):
        self.width = width
        self.height = height
        self.visible = True
        self.close_callback = close_callback
        self.controller = get_controller()
        
        # Fonts
        try:
            font_path = config.FONT_PATH if CONFIG_AVAILABLE else "fonts/Pokemon_GB.ttf"
            self.font_header = pygame.font.Font(font_path, 16)
            self.font_terminal = pygame.font.Font(font_path, 10)
            self.font_button = pygame.font.Font(font_path, 10)
        except:
            self.font_header = pygame.font.SysFont("Consolas", 20)
            self.font_terminal = pygame.font.SysFont("Consolas", 12)
            self.font_button = pygame.font.SysFont("Consolas", 12)
        
        # Terminal output lines
        self.terminal_lines = []
        self.max_lines = 100  # Keep last 100 lines
        self.scroll_offset = 0  # For scrolling through output
        
        # Build state
        self.is_building = False
        self.build_thread = None
        self.build_process = None
        
        # UI state - buttons stacked vertically on the right
        self.selected_button = 0
        self.buttons = ["Build Pokemon DB", "Build Wallpapers", "Back"]
        
        # Debounce for clicks
        self._last_click_time = 0
        self._click_debounce_ms = 300  # 300ms debounce
        
        # Add initial message
        self._add_line("Database & Asset Builder")
        self._add_line("=" * 35)
        self._add_line("")
        self._add_line("Build Pokemon DB:")
        self._add_line("  Downloads Pokemon data and")
        self._add_line("  sprites from PokeAPI.")
        self._add_line("")
        self._add_line("Build Wallpapers:")
        self._add_line("  Generates title wallpapers")
        self._add_line("  for each game.")
        self._add_line("")
    
    def _add_line(self, text):
        """Add a line to the terminal output"""
        # Split long lines
        max_chars = 38  # Reduced for narrower terminal
        while len(text) > max_chars:
            self.terminal_lines.append(text[:max_chars])
            text = text[max_chars:]
        self.terminal_lines.append(text)
        
        # Trim to max lines
        if len(self.terminal_lines) > self.max_lines:
            self.terminal_lines = self.terminal_lines[-self.max_lines:]
        
        # Auto-scroll to bottom
        self._scroll_to_bottom()
    
    def _scroll_to_bottom(self):
        """Scroll to show the latest output"""
        visible_lines = self._get_visible_line_count()
        if len(self.terminal_lines) > visible_lines:
            self.scroll_offset = len(self.terminal_lines) - visible_lines
        else:
            self.scroll_offset = 0
    
    def _get_visible_line_count(self):
        """Calculate how many lines fit in the terminal area"""
        terminal_height = self.height - 70  # Header + padding
        line_height = 14
        return max(1, terminal_height // line_height)
    
    def _start_build(self):
        """Start the database build process in a background thread"""
        if self.is_building:
            return
        
        self.is_building = True
        self.terminal_lines = []
        self._add_line("Starting database build...")
        self._add_line("")
        
        # Start build in background thread
        self.build_thread = threading.Thread(target=self._run_build, daemon=True)
        self.build_thread.start()
    
    def _run_build(self):
        """Run the build process and capture output"""
        try:
            # Use config.BASE_DIR if available, otherwise fall back to cwd
            if CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
                project_root = config.BASE_DIR
            else:
                project_root = os.getcwd()
            script_path = os.path.join(project_root, "DBbuilder.py")
            
            self._add_line(f"CWD: {project_root}")
            
            if not os.path.exists(script_path):
                self._add_line("ERROR: DBbuilder.py not found!")
                self.is_building = False
                return
            
            self._add_line(f"Running: DBbuilder.py")
            self._add_line("")
            
            # Windows-specific: prevent console window from appearing
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            # Run from project root so relative paths work
            self.build_process = subprocess.Popen(
                [sys.executable, "-u", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=False,
                cwd=project_root,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            # Read output line by line
            while True:
                line = self.build_process.stdout.readline()
                if not line and self.build_process.poll() is not None:
                    break
                if line:
                    self._add_line(line.rstrip())
            
            self.build_process.wait()
            
            self._add_line("")
            if self.build_process.returncode == 0:
                self._add_line("=" * 35)
                self._add_line("Build completed successfully!")
            else:
                self._add_line(f"Exit code: {self.build_process.returncode}")
            
        except Exception as e:
            self._add_line(f"ERROR: {e}")
            import traceback
            for line in traceback.format_exc().split('\n'):
                self._add_line(line)
        finally:
            self.is_building = False
            self.build_process = None
    
    def _start_wallpaper_build(self):
        """Start the wallpaper generation in a background thread"""
        if self.is_building:
            return
        
        self.is_building = True
        self.terminal_lines = []
        self._add_line("Starting wallpaper generation...")
        self._add_line("")
        
        # Start build in background thread
        self.build_thread = threading.Thread(target=self._run_wallpaper_build, daemon=True)
        self.build_thread.start()
    
    def _run_wallpaper_build(self):
        """Run wallgen.py and capture output"""
        try:
            # Use config.BASE_DIR if available, otherwise fall back to cwd
            if CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
                project_root = config.BASE_DIR
            else:
                project_root = os.getcwd()
            script_path = os.path.join(project_root, "wallgen.py")
            
            self._add_line(f"CWD: {project_root}")
            
            if not os.path.exists(script_path):
                self._add_line("ERROR: wallgen.py not found!")
                self.is_building = False
                return
            
            # Check if font exists
            if CONFIG_AVAILABLE and hasattr(config, 'FONT_SOLID_PATH'):
                font_path = config.FONT_SOLID_PATH
            else:
                font_path = os.path.join(project_root, "fonts", "Pokemon Solid.ttf")
            if not os.path.exists(font_path):
                self._add_line(f"WARNING: Font not found:")
                self._add_line(f"  {font_path}")
            
            self._add_line(f"Running: wallgen.py")
            self._add_line("")
            
            # Windows-specific: prevent console window from appearing
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            # Run from project root so relative paths work
            self.build_process = subprocess.Popen(
                [sys.executable, "-u", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=False,
                cwd=project_root,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            # Read output line by line
            while True:
                line = self.build_process.stdout.readline()
                if not line and self.build_process.poll() is not None:
                    break
                if line:
                    self._add_line(line.rstrip())
            
            self.build_process.wait()
            
            self._add_line("")
            if self.build_process.returncode == 0:
                self._add_line("=" * 35)
                self._add_line("Wallpapers generated!")
            else:
                self._add_line(f"Exit code: {self.build_process.returncode}")
            
        except Exception as e:
            self._add_line(f"ERROR: {e}")
            import traceback
            for line in traceback.format_exc().split('\n'):
                self._add_line(line)
        finally:
            self.is_building = False
            self.build_process = None
    
    def _cancel_build(self):
        """Cancel the current build if running"""
        if self.build_process and self.is_building:
            try:
                self.build_process.terminate()
                self.build_process.kill()  # Force kill if terminate doesn't work
                self._add_line("")
                self._add_line("Cancelled by user.")
                self.is_building = False
            except Exception as e:
                self._add_line(f"Error cancelling: {e}")
    
    def handle_events(self, events):
        """Handle pygame events"""
        current_time = pygame.time.get_ticks()
        
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.is_building:
                        self._cancel_build()
                    else:
                        self._close()
                elif event.key == pygame.K_RETURN:
                    # Debounce keyboard too
                    if current_time - self._last_click_time > self._click_debounce_ms:
                        self._last_click_time = current_time
                        self._activate_button()
                elif event.key == pygame.K_UP:
                    self.selected_button = max(0, self.selected_button - 1)
                elif event.key == pygame.K_DOWN:
                    self.selected_button = min(len(self.buttons) - 1, self.selected_button + 1)
                elif event.key == pygame.K_LEFT:
                    # Scroll up
                    self.scroll_offset = max(0, self.scroll_offset - 1)
                elif event.key == pygame.K_RIGHT:
                    # Scroll down
                    max_scroll = max(0, len(self.terminal_lines) - self._get_visible_line_count())
                    self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Debounce check
                    if current_time - self._last_click_time < self._click_debounce_ms:
                        continue
                    
                    # Check button clicks
                    button_rects = self._get_button_rects()
                    for i, rect in enumerate(button_rects):
                        if rect.collidepoint(event.pos):
                            self._last_click_time = current_time
                            self.selected_button = i
                            self._activate_button()
                            break
    
    def _get_button_rects(self):
        """Get the rectangles for each button (stacked vertically on right side)"""
        button_width = 110
        button_height = 28
        button_spacing = 8
        button_x = self.width - button_width - 15
        start_y = 55
        
        rects = []
        for i in range(len(self.buttons)):
            btn_y = start_y + i * (button_height + button_spacing)
            rects.append(pygame.Rect(button_x, btn_y, button_width, button_height))
        return rects
    
    def handle_controller(self, ctrl):
        """Handle controller input"""
        if not ctrl:
            return
        
        current_time = pygame.time.get_ticks()
        
        # D-pad for button selection (up/down) and scrolling (left/right)
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            self.selected_button = max(0, self.selected_button - 1)
        elif ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            self.selected_button = min(len(self.buttons) - 1, self.selected_button + 1)
        elif ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            self.scroll_offset = max(0, self.scroll_offset - 3)
        elif ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            max_scroll = max(0, len(self.terminal_lines) - self._get_visible_line_count())
            self.scroll_offset = min(max_scroll, self.scroll_offset + 3)
        
        # A to activate (with debounce)
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if current_time - self._last_click_time > self._click_debounce_ms:
                self._last_click_time = current_time
                self._activate_button()
        
        # B to go back
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            if self.is_building:
                self._cancel_build()
            else:
                self._close()
    
    def _activate_button(self):
        """Activate the selected button"""
        if self.selected_button == 0:
            # Build Pokemon DB button (or Cancel when building)
            if self.is_building:
                self._cancel_build()
            else:
                self._start_build()
        elif self.selected_button == 1:
            # Build Wallpapers button
            if self.is_building:
                self._cancel_build()
            else:
                self._start_wallpaper_build()
        else:
            # Back button
            if self.is_building:
                self._cancel_build()
            self._close()
    
    def _close(self):
        """Close this screen"""
        self.visible = False
        if self.close_callback:
            self.close_callback()
    
    def draw(self, surface):
        """Draw the DB builder screen"""
        # Background
        surface.fill(ui_colors.COLOR_BG)
        
        # Header
        header_rect = pygame.Rect(0, 0, self.width, 40)
        pygame.draw.rect(surface, ui_colors.COLOR_HEADER, header_rect)
        
        title = self.font_header.render("Database Builder", True, ui_colors.COLOR_TEXT)
        title_rect = title.get_rect(midleft=(15, 20))
        surface.blit(title, title_rect)
        
        # Building indicator in header (right side)
        if self.is_building:
            dots = "." * ((pygame.time.get_ticks() // 500) % 4)
            status = self.font_button.render(f"Working{dots}", True, ui_colors.COLOR_HIGHLIGHT)
            status_rect = status.get_rect(midright=(self.width - 15, 20))
            surface.blit(status, status_rect)
        
        # Get button rects for layout
        button_rects = self._get_button_rects()
        button_area_left = button_rects[0].left - 10
        
        # Terminal area - left side, leaving room for buttons on right
        terminal_rect = pygame.Rect(10, 50, button_area_left - 20, self.height - 60)
        pygame.draw.rect(surface, (20, 20, 30), terminal_rect)
        pygame.draw.rect(surface, ui_colors.COLOR_BORDER, terminal_rect, 2)
        
        # Draw terminal lines
        visible_lines = self._get_visible_line_count()
        y = terminal_rect.top + 5
        line_height = 14
        
        start_idx = self.scroll_offset
        end_idx = min(start_idx + visible_lines, len(self.terminal_lines))
        
        for i in range(start_idx, end_idx):
            line = self.terminal_lines[i]
            
            # Color code different line types
            if line.startswith("ERROR") or "FAILED" in line or "Error" in line or "Traceback" in line:
                color = ui_colors.COLOR_ERROR
            elif line.startswith("[") and "]" in line:
                # Progress lines like [001] Bulbasaur
                color = ui_colors.COLOR_SUCCESS
            elif line.startswith("[OK]"):
                # Wallpaper success lines
                color = ui_colors.COLOR_SUCCESS
            elif "=" in line and len(line) > 20:
                color = ui_colors.COLOR_HIGHLIGHT
            elif "All wallpapers generated" in line:
                color = ui_colors.COLOR_SUCCESS
            elif line.startswith("WARNING"):
                color = (255, 200, 100)  # Yellow/orange for warnings
            else:
                color = ui_colors.COLOR_TEXT
            
            text_surf = self.font_terminal.render(line, True, color)
            surface.blit(text_surf, (terminal_rect.left + 8, y))
            y += line_height
        
        # Scroll indicator
        if len(self.terminal_lines) > visible_lines:
            # Draw scroll bar
            scrollbar_height = terminal_rect.height - 10
            thumb_height = max(20, scrollbar_height * visible_lines // len(self.terminal_lines))
            max_scroll = len(self.terminal_lines) - visible_lines
            thumb_y = terminal_rect.top + 5
            if max_scroll > 0:
                thumb_y += int((scrollbar_height - thumb_height) * self.scroll_offset / max_scroll)
            
            scrollbar_x = terminal_rect.right - 12
            pygame.draw.rect(surface, (40, 40, 50), (scrollbar_x, terminal_rect.top + 5, 8, scrollbar_height))
            pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, (scrollbar_x, thumb_y, 8, thumb_height))
        
        # Draw buttons (stacked vertically on right)
        for i, btn_text in enumerate(self.buttons):
            btn_rect = button_rects[i]
            
            # Highlight selected button
            if i == self.selected_button:
                pygame.draw.rect(surface, ui_colors.COLOR_BUTTON_HOVER, btn_rect)
                pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, btn_rect, 3)
            else:
                pygame.draw.rect(surface, ui_colors.COLOR_BUTTON, btn_rect)
                pygame.draw.rect(surface, ui_colors.COLOR_BORDER, btn_rect, 2)
            
            # Button text - show Cancel if building
            display_text = btn_text
            if self.is_building and i < 2:  # First two buttons become Cancel
                display_text = "Cancel"
            
            text_surf = self.font_button.render(display_text, True, ui_colors.COLOR_TEXT)
            text_rect = text_surf.get_rect(center=btn_rect.center)
            surface.blit(text_surf, text_rect)
        
        # Hint text at bottom
        hint_y = self.height - 18
        hint_text = "A: Select  B: Back  L/R: Scroll"
        hint_surf = self.font_button.render(hint_text, True, (100, 100, 120))
        hint_rect = hint_surf.get_rect(center=(self.width // 2, hint_y))
        surface.blit(hint_surf, hint_rect)


# Wrapper class for compatibility with modal system
class DBBuilder:
    """Modal wrapper for DBBuilderScreen"""
    
    def __init__(self, width, height, close_callback=None):
        self.screen = DBBuilderScreen(width, height, close_callback)
        self.visible = True
    
    def update(self, events):
        self.screen.handle_events(events)
        self.visible = self.screen.visible
        return self.visible
    
    def handle_controller(self, ctrl):
        self.screen.handle_controller(ctrl)
    
    def draw(self, surface):
        self.screen.draw(surface)


# Alias
Modal = DBBuilder