"""
Sinew UI Components with Controller Support
Reusable UI elements for the application
"""

import pygame
import ui_colors
import config


class Button:
    """Standard button with hover effects and controller selection support"""
    
    def __init__(self, text, rel_rect, callback):
        """
        Args:
            text: Button label text
            rel_rect: Relative rectangle (x, y, w, h) as ratios of screen size (0.0-1.0)
            callback: Function to call when clicked
        """
        self.rel_rect = rel_rect
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.callback = callback
        self.text = text
        self.hover = False
        self.enabled = True
        self.controller_selected = False  # For controller navigation
        self.update_rect()

    def update_rect(self):
        """Update absolute rect based on window size"""
        x = int(self.rel_rect[0] * config.WINDOW_WIDTH)
        y = int(self.rel_rect[1] * config.WINDOW_HEIGHT)
        w = int(self.rel_rect[2] * config.WINDOW_WIDTH)
        h = int(self.rel_rect[3] * config.WINDOW_HEIGHT)
        self.rect = pygame.Rect(x, y, w, h)
    
    def set_controller_selected(self, selected):
        """Set whether this button is selected by controller"""
        self.controller_selected = selected

    def draw(self, surf, font, controller_selected=None):
        """
        Draw the button on the surface
        
        Args:
            surf: Surface to draw on
            font: Font to use for text
            controller_selected: Override controller selection state
        """
        mouse = pygame.mouse.get_pos()
        self.hover = self.rect.collidepoint(mouse) and self.enabled
        
        # Check if controller selected (either from parameter or internal state)
        is_controller_selected = controller_selected if controller_selected is not None else self.controller_selected

        if not self.enabled:
            color = (10, 10, 20)
            txt_color = (60, 60, 80)
            border_color = (40, 40, 60)
        elif is_controller_selected:
            # Controller selection highlight
            color = ui_colors.COLOR_BUTTON_HOVER
            txt_color = ui_colors.COLOR_HOVER_TEXT
            border_color = ui_colors.COLOR_HIGHLIGHT  # Cyan for controller
        elif self.hover:
            color = ui_colors.COLOR_BUTTON_HOVER
            txt_color = ui_colors.COLOR_HOVER_TEXT
            border_color = ui_colors.COLOR_BORDER
        else:
            color = ui_colors.COLOR_BUTTON
            txt_color = ui_colors.COLOR_TEXT
            border_color = ui_colors.COLOR_BORDER

        pygame.draw.rect(surf, color, self.rect)
        pygame.draw.rect(surf, border_color, self.rect, 2 if not is_controller_selected else 3)
        txt_surf = font.render(self.text, True, txt_color)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surf.blit(txt_surf, txt_rect)

    def handle_event(self, event):
        """Handle mouse events. Returns True if button was clicked."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False
    
    def activate(self):
        """Activate the button (call callback) - useful for controller"""
        if self.enabled:
            self.callback()
            return True
        return False


class TextDisplay:
    """Scrollable text display area with controller support"""
    
    def __init__(self, rel_rect):
        """
        Args:
            rel_rect: Relative rectangle (x, y, w, h) as ratios of screen size
        """
        self.rel_rect = rel_rect
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.lines = []
        self.scroll = 0
        self.update_rect()

    def update_rect(self):
        """Update absolute rect based on window size"""
        x = int(self.rel_rect[0] * config.WINDOW_WIDTH)
        y = int(self.rel_rect[1] * config.WINDOW_HEIGHT)
        w = int(self.rel_rect[2] * config.WINDOW_WIDTH)
        h = int(self.rel_rect[3] * config.WINDOW_HEIGHT)
        self.rect = pygame.Rect(x, y, w, h)

    def set_text(self, text):
        """Set the text content"""
        self.lines = text.split('\n')
        self.scroll = 0

    def draw(self, surf, font):
        """Draw the text display on the surface"""
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, self.rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.rect, 2)
        surf.set_clip(self.rect)
        line_height = font.get_linesize()
        y = self.rect.y + 5 - self.scroll
        for line in self.lines:
            if y > self.rect.bottom:
                break
            if y + line_height > self.rect.y:
                txt = font.render(line, True, ui_colors.COLOR_TEXT)
                surf.blit(txt, (self.rect.x + 5, y))
            y += line_height
        surf.set_clip(None)

    def handle_scroll(self, event):
        """Handle mouse wheel scrolling"""
        if not self.rect.collidepoint(pygame.mouse.get_pos()):
            return
        if event.button == 4:  # Scroll up
            self.scroll = max(0, self.scroll - 20)
        elif event.button == 5:  # Scroll down
            max_scroll = max(0, len(self.lines) * self.get_line_height() - self.rect.height + 10)
            self.scroll = min(self.scroll + 20, max_scroll)
    
    def scroll_up(self, amount=20):
        """Scroll up (for controller support)"""
        self.scroll = max(0, self.scroll - amount)
    
    def scroll_down(self, amount=20):
        """Scroll down (for controller support)"""
        max_scroll = max(0, len(self.lines) * self.get_line_height() - self.rect.height + 10)
        self.scroll = min(self.scroll + amount, max_scroll)
    
    def get_line_height(self):
        """Get line height (you'll need to pass font to this class or make it configurable)"""
        return 16  # Approximate, should be passed in


class SaveFileButton:
    """Button for selecting a save file with controller support"""
    
    def __init__(self, save_info, y_pos, tiny_font):
        """
        Args:
            save_info: Dict with 'name', 'size', 'empty' keys
            y_pos: Y position for the button
            tiny_font: Font to use for rendering
        """
        self.save_info = save_info
        self.rect = pygame.Rect(10, y_pos, config.WINDOW_WIDTH - 20, 22)
        self.hover = False
        self.tiny_font = tiny_font
        self.controller_selected = False

    def draw(self, surf, controller_selected=None):
        """Draw the save file button"""
        mouse = pygame.mouse.get_pos()
        is_empty = self.save_info['empty']
        self.hover = self.rect.collidepoint(mouse) and not is_empty
        
        # Check if controller selected
        is_controller_selected = controller_selected if controller_selected is not None else self.controller_selected
        
        if is_empty:
            color = (40, 20, 20)
            border = (100, 50, 50)
        elif is_controller_selected:
            color = ui_colors.COLOR_BUTTON_HOVER
            border = ui_colors.COLOR_HIGHLIGHT  # Cyan for controller
        elif self.hover:
            color = ui_colors.COLOR_BUTTON_HOVER
            border = ui_colors.COLOR_BORDER
        else:
            color = ui_colors.COLOR_BUTTON
            border = ui_colors.COLOR_BORDER
        
        pygame.draw.rect(surf, color, self.rect)
        pygame.draw.rect(surf, border, self.rect, 2 if is_controller_selected else 1)
        
        size_kb = self.save_info['size'] / 1024
        txt = f"{self.save_info['name']} ({size_kb:.1f}KB)"
        if is_empty:
            txt += " [EMPTY]"
        
        col = ui_colors.COLOR_HOVER_TEXT if (self.hover or is_controller_selected) else ui_colors.COLOR_TEXT
        if is_empty:
            col = (150, 80, 80)
        
        surf.blit(self.tiny_font.render(txt, True, col), (self.rect.x + 5, self.rect.y + 3))

    def handle_event(self, event):
        """Handle mouse events. Returns True if clicked."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class ButtonGroup:
    """Helper class for managing a group of buttons with controller navigation"""
    
    def __init__(self, buttons, columns=1, wrap=True):
        """
        Args:
            buttons: List of Button objects
            columns: Number of columns for grid navigation
            wrap: Whether to wrap around edges
        """
        self.buttons = buttons
        self.columns = columns
        self.wrap = wrap
        self.selected_index = 0
        
        if buttons:
            self.buttons[0].set_controller_selected(True)
    
    def navigate(self, direction):
        """
        Navigate in a direction
        
        Args:
            direction: 'up', 'down', 'left', 'right'
            
        Returns:
            bool: True if selection changed
        """
        if not self.buttons:
            return False
        
        old_index = self.selected_index
        rows = (len(self.buttons) + self.columns - 1) // self.columns
        
        if direction == 'up':
            new_idx = self.selected_index - self.columns
            if new_idx >= 0:
                self.selected_index = new_idx
            elif self.wrap:
                col = self.selected_index % self.columns
                last_row_start = (rows - 1) * self.columns
                self.selected_index = min(last_row_start + col, len(self.buttons) - 1)
        
        elif direction == 'down':
            new_idx = self.selected_index + self.columns
            if new_idx < len(self.buttons):
                self.selected_index = new_idx
            elif self.wrap:
                col = self.selected_index % self.columns
                self.selected_index = min(col, len(self.buttons) - 1)
        
        elif direction == 'left':
            if self.selected_index % self.columns > 0:
                self.selected_index -= 1
            elif self.wrap:
                row_end = min((self.selected_index // self.columns + 1) * self.columns - 1, len(self.buttons) - 1)
                self.selected_index = row_end
        
        elif direction == 'right':
            if self.selected_index % self.columns < self.columns - 1 and self.selected_index + 1 < len(self.buttons):
                self.selected_index += 1
            elif self.wrap:
                row_start = (self.selected_index // self.columns) * self.columns
                self.selected_index = row_start
        
        # Update button selection states
        if old_index != self.selected_index:
            self.buttons[old_index].set_controller_selected(False)
            self.buttons[self.selected_index].set_controller_selected(True)
            return True
        
        return False
    
    def get_selected_button(self):
        """Get the currently selected button"""
        if self.buttons and 0 <= self.selected_index < len(self.buttons):
            return self.buttons[self.selected_index]
        return None
    
    def activate_selected(self):
        """Activate the currently selected button"""
        button = self.get_selected_button()
        if button:
            return button.activate()
        return False
    
    def set_selected(self, index):
        """Set the selected button index"""
        if 0 <= index < len(self.buttons):
            if self.buttons:
                self.buttons[self.selected_index].set_controller_selected(False)
            self.selected_index = index
            self.buttons[self.selected_index].set_controller_selected(True)
    
    def draw_all(self, surf, font):
        """Draw all buttons in the group"""
        for button in self.buttons:
            button.draw(surf, font)


def draw_wrapped_text(surf, text, x, y, max_width, font_obj, color, line_height=None):
    """
    Draw word-wrapped text on a surface
    
    Args:
        surf: Surface to draw on
        text: Text to draw
        x, y: Starting position
        max_width: Maximum width before wrapping
        font_obj: Pygame font object
        color: Text color
        line_height: Optional custom line height
        
    Returns:
        y position after last line
    """
    if line_height is None:
        line_height = font_obj.get_linesize()
    words = text.split(' ')
    line = ''
    cur_y = y
    for word in words:
        test = (line + ' ' + word).strip()
        w = font_obj.size(test)[0]
        if w <= max_width:
            line = test
        else:
            txt_surf = font_obj.render(line, True, color)
            surf.blit(txt_surf, (x, cur_y))
            cur_y += line_height
            line = word
    if line:
        txt_surf = font_obj.render(line, True, color)
        surf.blit(txt_surf, (x, cur_y))
    return cur_y + line_height


def scale_surface_preserve_aspect(surface, max_w, max_h):
    """
    Scale a surface to fit within max dimensions while preserving aspect ratio
    
    Args:
        surface: Pygame surface to scale
        max_w, max_h: Maximum width and height
        
    Returns:
        Scaled surface or None
    """
    if not surface:
        return None
    w, h = surface.get_size()
    if w == 0 or h == 0:
        return surface
    scale = min(max_w / w, max_h / h, 1.0)  # Don't upscale
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return pygame.transform.smoothscale(surface, (new_w, new_h))


def draw_controller_hint(surf, text, x, y, font=None):
    """
    Draw a controller hint text
    
    Args:
        surf: Surface to draw on
        text: Hint text (e.g., "A: Select  B: Back")
        x, y: Position
        font: Optional font (will create small font if None)
    """
    if font is None:
        try:
            font = pygame.font.Font("fonts/Pokemon_GB.ttf", 8)
        except:
            font = pygame.font.SysFont(None, 12)
    
    hint_surf = font.render(text, True, (120, 120, 120))
    surf.blit(hint_surf, (x, y))