"""
Sinew Themes Screen
Browse and apply visual themes
"""

import pygame
import json
import os
import ui_colors
from controller import get_controller, NavigableList

try:
    from theme_manager import (
        get_available_themes, apply_theme, get_current_theme,
        save_theme_preference, get_theme_preview
    )
    THEME_MANAGER_AVAILABLE = True
except ImportError:
    THEME_MANAGER_AVAILABLE = False
    print("[ThemesScreen] Warning: theme_manager not available")

# Try to import achievements for theme locking
try:
    from achievements_data import get_theme_unlock_requirements, get_achievement_name_by_id
    from achievements import get_achievement_manager
    ACHIEVEMENTS_AVAILABLE = True
except ImportError:
    ACHIEVEMENTS_AVAILABLE = False
    print("[ThemesScreen] Warning: achievements not available - all themes unlocked")


class ThemesScreen:
    """Theme selection screen with live preview"""
    
    def __init__(self, width, height, close_callback=None):
        self.width = width
        self.height = height
        self.visible = True
        self.close_callback = close_callback
        self.controller = get_controller()
        
        # Fonts
        try:
            self.font_header = pygame.font.Font("fonts/Pokemon_GB.ttf", 18)
            self.font_text = pygame.font.Font("fonts/Pokemon_GB.ttf", 12)
            self.font_small = pygame.font.Font("fonts/Pokemon_GB.ttf", 10)
        except:
            self.font_header = pygame.font.SysFont(None, 24)
            self.font_text = pygame.font.SysFont(None, 18)
            self.font_small = pygame.font.SysFont(None, 14)
        
        # Load available themes
        if THEME_MANAGER_AVAILABLE:
            self.themes = get_available_themes()
            self.current_theme = get_current_theme()
        else:
            self.themes = ["Dark"]
            self.current_theme = "Dark"
        
        # Load theme unlock requirements
        self.theme_requirements = {}
        self.unlocked_themes = set()
        self._load_theme_unlock_status()
        
        # Navigation
        self.selected_index = 0
        # Set selected to current theme
        if self.current_theme in self.themes:
            self.selected_index = self.themes.index(self.current_theme)
        
        self.scroll_offset = 0
        self.themes_per_page = 5
        
        # Preview cache
        self.preview_cache = {}
        
        # Lock message
        self._lock_message = None
        self._lock_message_time = 0
    
    def _load_theme_unlock_status(self):
        """Load which themes are locked/unlocked"""
        # Get theme requirements from achievements
        if ACHIEVEMENTS_AVAILABLE:
            self.theme_requirements = get_theme_unlock_requirements()
        else:
            self.theme_requirements = {}
        
        # Load manually unlocked themes from settings
        try:
            settings_path = os.path.join(os.path.dirname(__file__), "sinew_settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    self.unlocked_themes = set(settings.get("unlocked_themes", []))
        except Exception as e:
            print(f"[ThemesScreen] Error loading unlocked themes: {e}")
            self.unlocked_themes = set()
    
    def _is_theme_locked(self, theme_name):
        """Check if a theme is locked"""
        # Convert theme name to filename
        theme_filename = f"{theme_name}.json"
        
        # Find matching requirement (case-insensitive)
        matching_req = None
        for req_filename in self.theme_requirements:
            if req_filename.lower() == theme_filename.lower():
                matching_req = req_filename
                break
        
        # If theme doesn't have requirements, it's unlocked
        if matching_req is None:
            return False
        
        # If manually unlocked (via reward claim), it's unlocked
        # Check case-insensitively
        for unlocked in self.unlocked_themes:
            if unlocked.lower() == theme_filename.lower():
                return False
        
        # Check if the required achievement is unlocked
        if ACHIEVEMENTS_AVAILABLE:
            required_ach_id = self.theme_requirements[matching_req]
            manager = get_achievement_manager()
            
            if manager:
                # Handle pattern-based requirements (like *_021)
                if required_ach_id.startswith("*"):
                    suffix = required_ach_id[1:]
                    # Check if ANY game has this achievement unlocked
                    from achievements_data import GAMES, GAME_PREFIX
                    for game in GAMES:
                        prefix = GAME_PREFIX.get(game, game.upper()[:4])
                        full_id = f"{prefix}{suffix}"
                        if manager.is_unlocked(full_id):
                            return False
                    return True
                else:
                    # Direct ID check - theme is locked if achievement is NOT unlocked
                    is_ach_unlocked = manager.is_unlocked(required_ach_id)
                    return not is_ach_unlocked
        
        # Default to unlocked if we can't check
        return False
    
    def _get_unlock_hint(self, theme_name):
        """Get the unlock hint for a locked theme"""
        theme_filename = f"{theme_name}.json"
        
        # Find matching requirement (case-insensitive)
        matching_req = None
        for req_filename in self.theme_requirements:
            if req_filename.lower() == theme_filename.lower():
                matching_req = req_filename
                break
        
        if matching_req is None:
            return None
        
        required_ach_id = self.theme_requirements[matching_req]
        
        if ACHIEVEMENTS_AVAILABLE:
            ach_name = get_achievement_name_by_id(required_ach_id)
            return f"Unlock: {ach_name}"
        
        return "Achievement required"
    
    def _has_unlock_requirement(self, theme_name):
        """Check if a theme has an unlock requirement (case-insensitive)"""
        theme_filename = f"{theme_name}.json"
        for req_filename in self.theme_requirements:
            if req_filename.lower() == theme_filename.lower():
                return True
        return False
    
    def _wrap_text(self, text, font, max_width):
        """Wrap text to fit within max_width, returning list of lines"""
        words = text.split(' ')
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            test_width = font.size(test_line)[0]
            
            if test_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text]
    
    def _get_preview(self, theme_name):
        """Get cached theme preview colors"""
        if theme_name not in self.preview_cache:
            if THEME_MANAGER_AVAILABLE:
                self.preview_cache[theme_name] = get_theme_preview(theme_name)
            else:
                self.preview_cache[theme_name] = None
        return self.preview_cache[theme_name]
    
    def _apply_selected_theme(self):
        """Apply the currently selected theme"""
        theme_name = self.themes[self.selected_index]
        
        # Check if theme is locked
        if self._is_theme_locked(theme_name):
            hint = self._get_unlock_hint(theme_name)
            self._lock_message = hint or "Theme is locked!"
            self._lock_message_time = pygame.time.get_ticks()
            print(f"[ThemesScreen] Cannot apply locked theme: {theme_name}")
            return False
        
        if THEME_MANAGER_AVAILABLE:
            if apply_theme(theme_name):
                self.current_theme = theme_name
                save_theme_preference(theme_name)
                print(f"[ThemesScreen] Applied theme: {theme_name}")
                return True
        
        return False
    
    def on_back(self):
        """Close the screen"""
        self.visible = False
        if self.close_callback:
            self.close_callback()
    
    def handle_controller(self, ctrl):
        """Handle controller input"""
        consumed = False
        
        # Navigate themes
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            if self.selected_index > 0:
                self.selected_index -= 1
                # Auto-scroll
                if self.selected_index < self.scroll_offset:
                    self.scroll_offset = self.selected_index
            consumed = True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            if self.selected_index < len(self.themes) - 1:
                self.selected_index += 1
                # Auto-scroll
                if self.selected_index >= self.scroll_offset + self.themes_per_page:
                    self.scroll_offset = self.selected_index - self.themes_per_page + 1
            consumed = True
        
        # Page scroll with L/R
        if ctrl.is_button_just_pressed('L'):
            ctrl.consume_button('L')
            self.selected_index = max(0, self.selected_index - self.themes_per_page)
            self.scroll_offset = max(0, self.scroll_offset - self.themes_per_page)
            consumed = True
        
        if ctrl.is_button_just_pressed('R'):
            ctrl.consume_button('R')
            max_idx = len(self.themes) - 1
            self.selected_index = min(max_idx, self.selected_index + self.themes_per_page)
            max_scroll = max(0, len(self.themes) - self.themes_per_page)
            self.scroll_offset = min(max_scroll, self.scroll_offset + self.themes_per_page)
            consumed = True
        
        # Apply theme with A
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            self._apply_selected_theme()
            consumed = True
        
        # Close with B
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            self.on_back()
            consumed = True
        
        return consumed
    
    def handle_events(self, events):
        """Handle pygame events"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.on_back()
                elif event.key == pygame.K_UP:
                    if self.selected_index > 0:
                        self.selected_index -= 1
                        if self.selected_index < self.scroll_offset:
                            self.scroll_offset = self.selected_index
                elif event.key == pygame.K_DOWN:
                    if self.selected_index < len(self.themes) - 1:
                        self.selected_index += 1
                        if self.selected_index >= self.scroll_offset + self.themes_per_page:
                            self.scroll_offset = self.selected_index - self.themes_per_page + 1
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self._apply_selected_theme()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Scroll up
                    self.scroll_offset = max(0, self.scroll_offset - 1)
                elif event.button == 5:  # Scroll down
                    max_scroll = max(0, len(self.themes) - self.themes_per_page)
                    self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
    
    def update(self, events):
        """Update the screen"""
        self.handle_events(events)
        return self.visible
    
    def draw(self, surf):
        """Draw the themes screen"""
        # Use current ui_colors values (they update when theme is applied)
        bg_color = ui_colors.COLOR_BG
        text_color = ui_colors.COLOR_TEXT
        border_color = ui_colors.COLOR_BORDER
        
        # Derive dimmed color from theme
        dimmed_color = tuple(max(0, c - 60) for c in text_color)
        
        # Background
        surf.fill(bg_color)
        pygame.draw.rect(surf, border_color, (0, 0, self.width, self.height), 2)
        
        # Title
        title = self.font_header.render("Themes", True, text_color)
        surf.blit(title, (20, 15))
        
        # Current theme indicator
        current_text = f"Current: {self.current_theme}"
        current_surf = self.font_small.render(current_text, True, dimmed_color)
        surf.blit(current_surf, (self.width - current_surf.get_width() - 20, 20))
        
        # Theme list
        y_start = 50
        item_height = 45
        list_width = self.width // 2 - 20
        
        visible_themes = self.themes[self.scroll_offset:self.scroll_offset + self.themes_per_page]
        
        for i, theme_name in enumerate(visible_themes):
            actual_index = self.scroll_offset + i
            y = y_start + i * item_height
            is_selected = (actual_index == self.selected_index)
            is_current = (theme_name == self.current_theme)
            is_locked = self._is_theme_locked(theme_name)
            
            # Theme item background
            item_rect = pygame.Rect(15, y, list_width, item_height - 5)
            
            if is_locked:
                # Darker background for locked themes
                bg = tuple(max(0, c - 30) for c in ui_colors.COLOR_BUTTON)
            elif is_current:
                # Green tint for current - derive from SUCCESS color
                bg = tuple(max(0, c - 60) for c in ui_colors.COLOR_SUCCESS)
            elif is_selected:
                bg = ui_colors.COLOR_BUTTON_HOVER
            else:
                bg = ui_colors.COLOR_BUTTON
            
            pygame.draw.rect(surf, bg, item_rect, border_radius=4)
            
            # Selection border
            if is_selected:
                border = (150, 100, 100) if is_locked else ui_colors.COLOR_HIGHLIGHT
                pygame.draw.rect(surf, border, item_rect, 2, border_radius=4)
                # Cursor
                cursor_color = (150, 100, 100) if is_locked else ui_colors.COLOR_HIGHLIGHT
                cursor = self.font_text.render(">", True, cursor_color)
                surf.blit(cursor, (5, y + 12))
            elif is_current:
                pygame.draw.rect(surf, ui_colors.COLOR_SUCCESS, item_rect, 2, border_radius=4)
            else:
                pygame.draw.rect(surf, border_color, item_rect, 1, border_radius=4)
            
            # Theme name (dimmed if locked)
            if is_locked:
                name_color = (100, 100, 100)
            elif is_selected:
                name_color = ui_colors.COLOR_HIGHLIGHT
            else:
                name_color = text_color
            name_surf = self.font_text.render(theme_name, True, name_color)
            surf.blit(name_surf, (35, y + 8))
            
            # Lock indicator or checkmark (use text instead of emoji)
            if is_locked:
                lock_surf = self.font_small.render("[X]", True, (150, 100, 100))
                surf.blit(lock_surf, (item_rect.right - 30, y + 12))
            elif is_current:
                check_surf = self.font_text.render("*", True, ui_colors.COLOR_SUCCESS)
                surf.blit(check_surf, (item_rect.right - 25, y + 8))
        
        # Preview panel (right side)
        preview_x = self.width // 2 + 10
        preview_width = self.width // 2 - 25
        preview_rect = pygame.Rect(preview_x, y_start, preview_width, self.height - y_start - 40)
        
        # Get preview colors for selected theme
        selected_theme = self.themes[self.selected_index]
        preview = self._get_preview(selected_theme)
        
        if preview:
            # Draw preview panel with theme colors
            preview_bg = tuple(preview.get('COLOR_BG', [40, 40, 60]))
            preview_border = tuple(preview.get('COLOR_BORDER', [100, 100, 150]))
            preview_text = tuple(preview.get('COLOR_TEXT', [200, 200, 200]))
            preview_button = tuple(preview.get('COLOR_BUTTON', [60, 60, 100]))
            preview_header = tuple(preview.get('COLOR_HEADER', [30, 30, 60]))
            
            # Background
            pygame.draw.rect(surf, preview_bg, preview_rect, border_radius=4)
            pygame.draw.rect(surf, preview_border, preview_rect, 2, border_radius=4)
            
            # Preview header
            header_rect = pygame.Rect(preview_x + 5, y_start + 5, preview_width - 10, 25)
            pygame.draw.rect(surf, preview_header, header_rect, border_radius=3)
            
            header_text = self.font_small.render("Preview", True, preview_text)
            surf.blit(header_text, (preview_x + 10, y_start + 10))
            
            # Preview content
            content_y = y_start + 40
            
            # Sample text
            sample_text = self.font_small.render("Sample Text", True, preview_text)
            surf.blit(sample_text, (preview_x + 15, content_y))
            
            # Sample button
            btn_rect = pygame.Rect(preview_x + 15, content_y + 25, 100, 25)
            pygame.draw.rect(surf, preview_button, btn_rect, border_radius=3)
            pygame.draw.rect(surf, preview_border, btn_rect, 1, border_radius=3)
            btn_text = self.font_small.render("Button", True, preview_text)
            btn_text_rect = btn_text.get_rect(center=btn_rect.center)
            surf.blit(btn_text, btn_text_rect)
            
            # Color swatches
            swatch_y = content_y + 60
            swatch_size = 20
            swatch_gap = 5
            
            colors_to_show = [
                ('BG', preview_bg),
                ('Header', preview_header),
                ('Text', preview_text),
                ('Border', preview_border),
                ('Button', preview_button),
            ]
            
            for j, (name, color) in enumerate(colors_to_show):
                sx = preview_x + 15 + j * (swatch_size + swatch_gap + 2)
                swatch_rect = pygame.Rect(sx, swatch_y, swatch_size, swatch_size)
                pygame.draw.rect(surf, color, swatch_rect)
                pygame.draw.rect(surf, dimmed_color, swatch_rect, 1)
            
            # Unlock requirement info (below swatches)
            unlock_y = swatch_y + swatch_size + 15
            
            if self._has_unlock_requirement(selected_theme):
                # This theme has an unlock requirement
                is_theme_locked = self._is_theme_locked(selected_theme)
                hint = self._get_unlock_hint(selected_theme)
                
                if hint:
                    max_width = preview_width - 30
                    if is_theme_locked:
                        # Show how to unlock (locked)
                        lines = self._wrap_text("LOCKED - " + hint, self.font_small, max_width)
                        text_color = (180, 120, 120)
                    else:
                        # Show how it was unlocked (unlocked)
                        lines = self._wrap_text(hint + " (Unlocked)", self.font_small, max_width)
                        text_color = (120, 180, 120)
                    
                    for i, line in enumerate(lines):
                        line_surf = self.font_small.render(line, True, text_color)
                        surf.blit(line_surf, (preview_x + 15, unlock_y + i * 14))
        else:
            # No preview available
            pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, preview_rect, border_radius=4)
            pygame.draw.rect(surf, border_color, preview_rect, 1, border_radius=4)
            
            no_preview = self.font_text.render("No Preview", True, dimmed_color)
            no_preview_rect = no_preview.get_rect(center=preview_rect.center)
            surf.blit(no_preview, no_preview_rect)
            
            # Still show unlock info even without preview
            unlock_y = preview_rect.bottom - 60
            
            if self._has_unlock_requirement(selected_theme):
                is_theme_locked = self._is_theme_locked(selected_theme)
                hint = self._get_unlock_hint(selected_theme)
                
                if hint:
                    max_width = preview_width - 30
                    if is_theme_locked:
                        lines = self._wrap_text("LOCKED - " + hint, self.font_small, max_width)
                        text_color = (180, 120, 120)
                    else:
                        lines = self._wrap_text(hint + " (Unlocked)", self.font_small, max_width)
                        text_color = (120, 180, 120)
                    
                    for i, line in enumerate(lines):
                        line_surf = self.font_small.render(line, True, text_color)
                        surf.blit(line_surf, (preview_x + 15, unlock_y + i * 14))
        
        # Scroll indicators
        if len(self.themes) > self.themes_per_page:
            if self.scroll_offset > 0:
                up_arrow = self.font_text.render("^", True, ui_colors.COLOR_SUCCESS)
                surf.blit(up_arrow, (list_width // 2, y_start - 15))
            
            if self.scroll_offset < len(self.themes) - self.themes_per_page:
                down_arrow = self.font_text.render("v", True, ui_colors.COLOR_SUCCESS)
                surf.blit(down_arrow, (list_width // 2, y_start + self.themes_per_page * item_height - 5))
        
        # Lock message (if recently shown)
        current_time = pygame.time.get_ticks()
        if self._lock_message and current_time - self._lock_message_time < 2000:
            # Draw message box
            msg_surf = self.font_small.render(self._lock_message, True, (255, 200, 200))
            msg_rect = msg_surf.get_rect(centerx=self.width // 2, bottom=self.height - 30)
            
            # Background
            bg_rect = msg_rect.inflate(20, 10)
            pygame.draw.rect(surf, (80, 40, 40), bg_rect, border_radius=4)
            pygame.draw.rect(surf, (150, 80, 80), bg_rect, 2, border_radius=4)
            
            surf.blit(msg_surf, msg_rect)
        
        # Controller hints
        hints = "D-Pad: Navigate   A: Apply Theme   B: Back"
        hint_surf = self.font_small.render(hints, True, dimmed_color)
        hint_rect = hint_surf.get_rect(centerx=self.width // 2, bottom=self.height - 8)
        surf.blit(hint_surf, hint_rect)


# Modal wrapper for compatibility
class Modal:
    """Modal wrapper for themes screen"""
    
    def __init__(self, w, h, font=None, close_callback=None):
        self.width = w
        self.height = h
        self.font = font
        self.screen = ThemesScreen(w, h, close_callback=close_callback)
        self.visible = True
    
    def update(self, events):
        self.screen.handle_events(events)
        self.visible = self.screen.visible
        return self.visible
    
    def handle_controller(self, ctrl):
        return self.screen.handle_controller(ctrl)
    
    def draw(self, surf):
        self.screen.draw(surf)