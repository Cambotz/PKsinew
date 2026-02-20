"""
Item Bag UI Screen with Controller Support
Displays items parsed from Gen 3 save file
"""

import pygame
import ui_colors
from ui_components import Button
from save_data_manager import get_manager
from controller import get_controller, NavigableList

FONT_PATH = "fonts/pokemon_GB.ttf"


class Modal:
    """Modal wrapper for item bag"""
    
    def __init__(self, w, h, font):
        self.width = w
        self.height = h
        self.font = font
        self.screen = ItemBagScreen(w, h)

    def update(self, events):
        self.screen.update(events)
        return not self.screen.should_close
    
    def handle_controller(self, ctrl):
        """Handle controller input"""
        return self.screen.handle_controller(ctrl)

    def draw(self, surf):
        # Outer modal background
        pygame.draw.rect(surf, (20, 20, 40), (0, 0, self.width, self.height))
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, (0, 0, self.width, self.height), 3)
        
        # Inner border
        pygame.draw.rect(surf, (70, 70, 90),
                         (6, 6, self.width - 12, self.height - 12), 2)
        
        self.screen.draw(surf)


class ItemBagScreen:
    """Item bag display screen with controller support"""
    
    POCKET_NAMES = {
        'items': 'Items',
        'key_items': 'Key Items',
        'pokeballs': 'Poke Balls',
        'tms_hms': 'TMs & HMs',
        'berries': 'Berries'
    }
    
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.should_close = False
        
        # Fonts
        self.font_header = pygame.font.Font(FONT_PATH, 16)
        self.font_text = pygame.font.Font(FONT_PATH, 10)
        self.font_small = pygame.font.Font(FONT_PATH, 8)
        
        # Get save data
        self.manager = get_manager()
        
        # Get controller
        self.controller = get_controller()
        
        # Current pocket selection
        self.pocket_order = ['items', 'key_items', 'pokeballs', 'tms_hms', 'berries']
        self.current_pocket_index = 0
        self.scroll_offset = 0
        
        # Navigation state
        self.pocket_nav = NavigableList(len(self.pocket_order), columns=5, wrap=True)
        
        # Focus mode: 'pockets' or 'items'
        self.focus_mode = 'items'  # Start focused on item list
        
        # UI Layout
        self.pocket_buttons = []
        self.create_pocket_buttons()
        
        # Scrolling - calculate how many items actually fit
        # List area is from y=90 to h-40 (bottom margin for hints)
        # Item height is 20 + 2 gap = 22 pixels per item
        # With 8px top padding inside the box
        list_height = self.h - 130 - 16  # subtract padding
        item_total_height = 22  # 20 height + 2 gap
        self.items_per_page = max(1, list_height // item_total_height)
        self.selected_item_index = 0
        
        # Item list navigation
        self.item_nav = NavigableList(1, columns=1, wrap=False)  # Will update count
        self._update_item_nav()
    
    def _update_item_nav(self):
        """Update item navigation list based on current pocket"""
        items = self.get_current_pocket_items()
        count = max(1, len(items))
        self.item_nav.set_count(count)
    
    def create_pocket_buttons(self):
        """Create buttons for pocket selection"""
        button_width = 0.17  # Slightly narrower to fit all 5 buttons
        button_height = 0.08
        start_x = 0.02
        start_y = 0.02
        gap = 0.008  # Smaller gap
        
        for i, pocket_key in enumerate(self.pocket_order):
            btn = Button(
                self.POCKET_NAMES[pocket_key],
                rel_rect=(start_x + i * (button_width + gap), start_y, button_width, button_height),
                callback=lambda idx=i: self.select_pocket(idx)
            )
            self.pocket_buttons.append(btn)
    
    def select_pocket(self, index):
        """Select a pocket"""
        self.current_pocket_index = index
        self.scroll_offset = 0
        self.selected_item_index = 0
        self.pocket_nav.set_selected(index)
        self._update_item_nav()
    
    def get_current_pocket_items(self):
        """Get items in currently selected pocket"""
        if not self.manager.is_loaded():
            return []
        
        pocket_key = self.pocket_order[self.current_pocket_index]
        items_with_names = self.manager.get_items_with_names()
        return items_with_names.get(pocket_key, [])
    
    def scroll_up(self):
        """Scroll item list up"""
        self.scroll_offset = max(0, self.scroll_offset - 1)
    
    def scroll_down(self):
        """Scroll item list down"""
        items = self.get_current_pocket_items()
        max_scroll = max(0, len(items) - self.items_per_page)
        self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
    
    def handle_controller(self, ctrl):
        """
        Handle controller input
        
        Args:
            ctrl: ControllerManager instance
            
        Returns:
            bool: True if input was consumed
        """
        consumed = False
        
        # B button closes modal
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            self.should_close = True
            return True
        
        # L/R for pocket switching
        if ctrl.is_button_just_pressed('L'):
            ctrl.consume_button('L')
            new_idx = (self.current_pocket_index - 1) % len(self.pocket_order)
            self.select_pocket(new_idx)
            return True
        
        if ctrl.is_button_just_pressed('R'):
            ctrl.consume_button('R')
            new_idx = (self.current_pocket_index + 1) % len(self.pocket_order)
            self.select_pocket(new_idx)
            return True
        
        # D-pad navigation
        if self.focus_mode == 'pockets':
            consumed = self._handle_pocket_controller(ctrl)
        else:  # focus_mode == 'items'
            consumed = self._handle_items_controller(ctrl)
        
        return consumed
    
    def _handle_pocket_controller(self, ctrl):
        """Handle controller when focused on pocket tabs"""
        consumed = False
        
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            new_idx = (self.current_pocket_index - 1) % len(self.pocket_order)
            self.select_pocket(new_idx)
            consumed = True
        
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            new_idx = (self.current_pocket_index + 1) % len(self.pocket_order)
            self.select_pocket(new_idx)
            consumed = True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            self.focus_mode = 'items'
            consumed = True
        
        # A button switches to items
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            self.focus_mode = 'items'
            consumed = True
        
        return consumed
    
    def _handle_items_controller(self, ctrl):
        """Handle controller when focused on item list"""
        consumed = False
        items = self.get_current_pocket_items()
        
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            if self.selected_item_index > 0:
                self.selected_item_index -= 1
                # Auto-scroll if selection goes above visible area
                if self.selected_item_index < self.scroll_offset:
                    self.scroll_offset = self.selected_item_index
            elif self.selected_item_index == 0:
                # Switch to pocket tabs
                self.focus_mode = 'pockets'
            consumed = True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            if self.selected_item_index < len(items) - 1:
                self.selected_item_index += 1
                # Auto-scroll if selection goes below visible area
                # Scroll when selected item is at or past the last visible position
                last_visible = self.scroll_offset + self.items_per_page - 1
                if self.selected_item_index > last_visible:
                    self.scroll_offset = self.selected_item_index - self.items_per_page + 1
            consumed = True
        
        # Left/Right changes pocket even when in item list
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            new_idx = (self.current_pocket_index - 1) % len(self.pocket_order)
            self.select_pocket(new_idx)
            consumed = True
        
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            new_idx = (self.current_pocket_index + 1) % len(self.pocket_order)
            self.select_pocket(new_idx)
            consumed = True
        
        # A button could be used to select item (for future features)
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if items and 0 <= self.selected_item_index < len(items):
                item = items[self.selected_item_index]
                print(f"Selected item: {item['name']} x{item['quantity']}")
            consumed = True
        
        return consumed
    
    def update(self, events):
        """Handle events"""
        for event in events:
            # Handle pocket buttons
            for btn in self.pocket_buttons:
                btn.handle_event(event)
            
            # Keyboard controls
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    items = self.get_current_pocket_items()
                    if self.selected_item_index > 0:
                        self.selected_item_index -= 1
                        # Auto-scroll to keep selection visible
                        if self.selected_item_index < self.scroll_offset:
                            self.scroll_offset = self.selected_item_index
                elif event.key == pygame.K_DOWN:
                    items = self.get_current_pocket_items()
                    if self.selected_item_index < len(items) - 1:
                        self.selected_item_index += 1
                        # Auto-scroll to keep selection visible
                        last_visible = self.scroll_offset + self.items_per_page - 1
                        if self.selected_item_index > last_visible:
                            self.scroll_offset = self.selected_item_index - self.items_per_page + 1
                elif event.key == pygame.K_LEFT:
                    self.select_pocket((self.current_pocket_index - 1) % len(self.pocket_order))
                elif event.key == pygame.K_RIGHT:
                    self.select_pocket((self.current_pocket_index + 1) % len(self.pocket_order))
                elif event.key == pygame.K_ESCAPE:
                    self.should_close = True
            
            # Mouse wheel scrolling (scrolls view but doesn't change selection)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Scroll up
                    self.scroll_up()
                    # Keep selection in view
                    if self.selected_item_index >= self.scroll_offset + self.items_per_page:
                        self.selected_item_index = self.scroll_offset + self.items_per_page - 1
                elif event.button == 5:  # Scroll down
                    self.scroll_down()
                    # Keep selection in view
                    if self.selected_item_index < self.scroll_offset:
                        self.selected_item_index = self.scroll_offset
    
    def draw(self, surf):
        """Draw the item bag screen"""
        # Background
        surf.fill((30, 30, 40))
        
        # Draw pocket buttons
        for i, btn in enumerate(self.pocket_buttons):
            # Highlight selected pocket
            if i == self.current_pocket_index:
                # Draw highlight behind button
                highlight_rect = btn.rect.inflate(4, 4)
                highlight_color = ui_colors.COLOR_HIGHLIGHT if self.focus_mode == 'pockets' else (100, 150, 200)
                pygame.draw.rect(surf, highlight_color, highlight_rect, 3)
            btn.draw(surf, self.font_small)
        
        # Current pocket title
        pocket_key = self.pocket_order[self.current_pocket_index]
        title_text = self.POCKET_NAMES[pocket_key]
        title_surf = self.font_header.render(title_text, True, ui_colors.COLOR_TEXT)
        surf.blit(title_surf, (20, 60))
        
        # Item list area
        list_area = pygame.Rect(20, 90, self.w - 40, self.h - 130)
        pygame.draw.rect(surf, (40, 40, 50), list_area)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, list_area, 2)
        
        # Draw items
        items = self.get_current_pocket_items()
        
        if not items:
            # No items message
            no_items_surf = self.font_text.render("No items in this pocket", True, (150, 150, 150))
            no_items_rect = no_items_surf.get_rect(center=list_area.center)
            surf.blit(no_items_surf, no_items_rect)
        else:
            # Set clipping region to keep items inside the box
            # Shrink by border width to avoid drawing over border
            clip_rect = pygame.Rect(list_area.x + 3, list_area.y + 3, 
                                    list_area.width - 6, list_area.height - 6)
            surf.set_clip(clip_rect)
            
            # Draw visible items
            y_pos = list_area.y + 8
            item_height = 20
            
            visible_items = items[self.scroll_offset:self.scroll_offset + self.items_per_page]
            
            for i, item in enumerate(visible_items):
                actual_index = self.scroll_offset + i
                
                # Item background (alternating colors)
                item_rect = pygame.Rect(list_area.x + 5, y_pos, list_area.width - 10, item_height)
                
                # Check if this item is selected
                is_selected = (actual_index == self.selected_item_index and self.focus_mode == 'items')
                
                if is_selected:
                    bg_color = (80, 120, 180)  # Highlight color
                else:
                    bg_color = (50, 50, 60) if i % 2 == 0 else (45, 45, 55)
                
                pygame.draw.rect(surf, bg_color, item_rect)
                
                # Draw selection cursor
                if is_selected:
                    pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, item_rect, 2)
                    # Draw arrow indicator
                    arrow_surf = self.font_text.render(">", True, ui_colors.COLOR_HIGHLIGHT)
                    surf.blit(arrow_surf, (item_rect.x - 12, item_rect.y + 3))
                
                # Item name
                name_surf = self.font_text.render(item['name'][:25], True, ui_colors.COLOR_TEXT)
                surf.blit(name_surf, (item_rect.x + 5, item_rect.y + 3))
                
                # Item quantity
                qty_text = f"x{item['quantity']}"
                qty_surf = self.font_text.render(qty_text, True, (200, 200, 100))
                qty_rect = qty_surf.get_rect(right=item_rect.right - 5, centery=item_rect.centery)
                surf.blit(qty_surf, qty_rect)
                
                y_pos += item_height + 2
            
            # Reset clipping region
            surf.set_clip(None)
            
            # Redraw border on top (in case items were partially clipped)
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, list_area, 2)
            
            # Scroll indicator (drawn outside clip area)
            if len(items) > self.items_per_page:
                scroll_text = f"{self.scroll_offset + 1}-{min(self.scroll_offset + self.items_per_page, len(items))} of {len(items)}"
                scroll_surf = self.font_small.render(scroll_text, True, (150, 150, 150))
                surf.blit(scroll_surf, (list_area.right - 80, list_area.bottom + 5))
                
                # Draw scroll arrows inside the box area
                if self.scroll_offset > 0:
                    # Up arrow available
                    up_arrow = self.font_text.render("^", True, (100, 255, 100))
                    surf.blit(up_arrow, (list_area.right - 20, list_area.y + 5))
                
                if self.scroll_offset < len(items) - self.items_per_page:
                    # Down arrow available
                    down_arrow = self.font_text.render("v", True, (100, 255, 100))
                    surf.blit(down_arrow, (list_area.right - 20, list_area.bottom - 20))
        
        # Controller hints at bottom
        try:
            hints = "L/R: Pocket  D-Pad: Navigate  B: Back"
            instr_surf = self.font_small.render(hints, True, (120, 120, 120))
            instr_rect = instr_surf.get_rect(centerx=self.w // 2, bottom=self.h - 5)
            surf.blit(instr_surf, instr_rect)
        except:
            pass