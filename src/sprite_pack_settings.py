#!/usr/bin/env python3

"""
sprite_pack_settings.py — UI for managing sprite pack preferences

Shows:
- Currently selected global pack
- Per-game sprite pack overrides
- Available packs with download status
- Allows setting global and per-game preferences
"""

import pygame
import ui_colors
from sprite_pack_manager import get_sprite_pack_manager
from ui_scale import ui, scaled_font


class SpritePackSettingsModal:
    """Modal dialog for sprite pack preferences"""
    
    def __init__(self, width, height, close_callback=None, get_current_game_callback=None):
        self.width = width
        self.height = height
        self.close_callback = close_callback
        self.get_current_game_callback = get_current_game_callback
        
        self.font = scaled_font(12)
        self.font_small = scaled_font(10)
        self.font_title = scaled_font(14)
        
        # Get sprite pack manager
        self.manager = get_sprite_pack_manager()
        
        # UI state
        self.scroll_offset = 0
        self.selected_pack_index = 0
        
        # Get list of downloaded packs
        self.packs = self.manager.get_downloaded_packs()
        
        # Find current global pack in list
        global_pack_id = self.manager.preferences.get("global_pack", "gen3_emerald")
        for i, pack in enumerate(self.packs):
            if pack.pack_id == global_pack_id:
                self.selected_pack_index = i
                break
    
    def handle_input(self, event):
        """Handle keyboard/controller input"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_BACKSPACE:
                if self.close_callback:
                    self.close_callback()
                return True
            
            elif event.key == pygame.K_UP:
                self.selected_pack_index = max(0, self.selected_pack_index - 1)
                return True
            
            elif event.key == pygame.K_DOWN:
                self.selected_pack_index = min(len(self.packs) - 1, self.selected_pack_index + 1)
                return True
            
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                # Set selected pack as global default
                if 0 <= self.selected_pack_index < len(self.packs):
                    pack = self.packs[self.selected_pack_index]
                    self.manager.set_global_pack(pack.pack_id)
                return True
            
            elif event.key == pygame.K_g:
                # Set for current game (if we have game context)
                if self.get_current_game_callback and 0 <= self.selected_pack_index < len(self.packs):
                    game_name = self.get_current_game_callback()
                    if game_name:
                        pack = self.packs[self.selected_pack_index]
                        self.manager.set_game_pack(game_name, pack.pack_id)
                return True
            
            elif event.key == pygame.K_c:
                # Clear per-game override for current game
                if self.get_current_game_callback:
                    game_name = self.get_current_game_callback()
                    if game_name:
                        self.manager.clear_game_pack(game_name)
                return True
        
        return False
    
    def draw(self, surf):
        """Draw the sprite pack settings modal"""
        # Semi-transparent background
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))
        
        # Main panel
        panel_w = min(600, self.width - 40)
        panel_h = min(500, self.height - 40)
        panel_x = (self.width - panel_w) // 2
        panel_y = (self.height - panel_h) // 2
        
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        
        # Panel background
        pygame.draw.rect(surf, ui_colors.COLOR_BG, panel_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, panel_rect, 2)
        
        # Title
        title_text = self.font_title.render("Sprite Pack Settings", True, ui_colors.COLOR_TEXT)
        title_x = panel_x + (panel_w - title_text.get_width()) // 2
        surf.blit(title_text, (title_x, panel_y + 10))
        
        # Current settings section
        y_offset = panel_y + 45
        
        # Global pack
        global_pack_id = self.manager.preferences.get("global_pack", "gen3_emerald")
        global_pack = self.manager.get_pack(global_pack_id)
        global_name = global_pack.display_name if global_pack else "None"
        
        label = self.font.render(f"Global Default: {global_name}", True, ui_colors.COLOR_TEXT)
        surf.blit(label, (panel_x + 20, y_offset))
        y_offset += 25
        
        # Current game pack (if applicable)
        if self.get_current_game_callback:
            game_name = self.get_current_game_callback()
            if game_name:
                game_pack = self.manager.get_pack_for_game(game_name)
                game_pack_name = game_pack.display_name if game_pack else "None"
                
                # Check if it's using a per-game override
                per_game_override = self.manager.preferences.get("per_game", {}).get(game_name)
                override_marker = " (override)" if per_game_override else " (using global)"
                
                label = self.font.render(f"{game_name}: {game_pack_name}{override_marker}", True, ui_colors.COLOR_TEXT)
                surf.blit(label, (panel_x + 20, y_offset))
                y_offset += 30
        
        # Separator
        pygame.draw.line(surf, ui_colors.COLOR_BORDER, 
                        (panel_x + 20, y_offset), 
                        (panel_x + panel_w - 20, y_offset), 2)
        y_offset += 15
        
        # Available packs list
        label = self.font.render("Available Packs (Downloaded):", True, ui_colors.COLOR_TEXT)
        surf.blit(label, (panel_x + 20, y_offset))
        y_offset += 25
        
        # Draw pack list
        list_rect = pygame.Rect(panel_x + 20, y_offset, panel_w - 40, panel_h - (y_offset - panel_y) - 60)
        
        for i, pack in enumerate(self.packs):
            if y_offset >= panel_y + panel_h - 60:
                break
            
            # Highlight selected
            is_selected = (i == self.selected_pack_index)
            
            if is_selected:
                highlight_rect = pygame.Rect(list_rect.x, y_offset - 2, list_rect.width, 22)
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, highlight_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, highlight_rect, 1)
            
            # Pack name and sprite count
            pack_text = f"{pack.display_name} ({pack.get_sprite_count()}/386)"
            if pack.is_custom:
                pack_text = "⭐ " + pack_text
            
            color = ui_colors.COLOR_TEXT_HIGHLIGHT if is_selected else ui_colors.COLOR_TEXT
            text = self.font_small.render(pack_text, True, color)
            surf.blit(text, (list_rect.x + 5, y_offset))
            
            y_offset += 24
        
        # Instructions
        y_offset = panel_y + panel_h - 50
        instructions = [
            "↑↓: Select   ENTER: Set as Global   G: Set for Current Game   C: Clear Override   ESC: Close"
        ]
        
        for instruction in instructions:
            text = self.font_small.render(instruction, True, ui_colors.COLOR_TEXT_DIM)
            text_x = panel_x + (panel_w - text.get_width()) // 2
            surf.blit(text, (text_x, y_offset))
            y_offset += 15