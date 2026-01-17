"""
Events Screen - Event Item Distribution System
Allows players who have become Champion (8 badges) to obtain event items
that unlock legendary Pokemon encounters.
"""

import pygame
import os
import json
import ui_colors
from save_data_manager import get_manager
from controller import get_controller

FONT_PATH = "fonts/Pokemon_GB.ttf"

# Event item definitions
EVENT_ITEMS = {
    'eon_ticket': {
        'id': 275,
        'name': 'Eon Ticket',
        'desc': 'A ticket for the ferry to Southern Island.',
        'pokemon': 'Latios/Latias',
        'pokemon_ids': [380, 381],  # Latias, Latios
        'compatible': ['Ruby', 'Sapphire', 'Emerald'],
        'icon_color': (100, 150, 255),  # Blue
    },
    'aurora_ticket': {
        'id': 371,
        'name': 'Aurora Ticket',
        'desc': 'A ticket for the ferry to Birth Island.',
        'pokemon': 'Deoxys',
        'pokemon_ids': [386],  # Deoxys
        'compatible': ['FireRed', 'LeafGreen', 'Emerald'],
        'icon_color': (255, 150, 200),  # Pink
    },
    'mystic_ticket': {
        'id': 370,
        'name': 'Mystic Ticket',
        'desc': 'A ticket for the ferry to Navel Rock.',
        'pokemon': 'Ho-Oh & Lugia',
        'pokemon_ids': [249, 250],  # Lugia, Ho-Oh
        'compatible': ['FireRed', 'LeafGreen', 'Emerald'],
        'icon_color': (255, 200, 100),  # Gold
    },
    'old_sea_map': {
        'id': 376,
        'name': 'Old Sea Map',
        'desc': 'A faded sea chart to a faraway island.',
        'pokemon': 'Mew',
        'pokemon_ids': [151],  # Mew
        'compatible': ['Emerald'],
        'icon_color': (150, 255, 150),  # Green
    },
}

# Order for display
EVENT_ORDER = ['eon_ticket', 'aurora_ticket', 'mystic_ticket', 'old_sea_map']


class EventsModal:
    """Modal wrapper for events screen"""
    
    def __init__(self, w, h, font, on_close=None, on_event_claimed=None, game_name=None):
        self.width = w
        self.height = h
        self.font = font
        self.on_close = on_close
        self.on_event_claimed = on_event_claimed
        self.screen = EventsScreen(w, h, on_event_claimed=on_event_claimed, game_name=game_name)
    
    def update(self, events):
        self.screen.update(events)
        return not self.screen.should_close
    
    def handle_controller(self, ctrl):
        return self.screen.handle_controller(ctrl)
    
    def draw(self, surf):
        self.screen.draw(surf)


class EventsScreen:
    """Events screen for claiming event items"""
    
    def __init__(self, w, h, on_event_claimed=None, game_name=None):
        self.w = w
        self.h = h
        self.should_close = False
        self.on_event_claimed = on_event_claimed
        
        # Fonts
        try:
            self.font_header = pygame.font.Font(FONT_PATH, 14)
            self.font_text = pygame.font.Font(FONT_PATH, 10)
            self.font_small = pygame.font.Font(FONT_PATH, 8)
        except:
            self.font_header = pygame.font.SysFont(None, 20)
            self.font_text = pygame.font.SysFont(None, 16)
            self.font_small = pygame.font.SysFont(None, 12)
        
        # Get save manager and controller
        self.manager = get_manager()
        self.controller = get_controller()
        
        # Use provided game name (from main screen) or fallback to detection
        self.game_name = game_name if game_name else self._get_game_name()
        self.game_type = self._get_game_type()
        
        print(f"[Events] Game: {self.game_name} (type: {self.game_type})")
        
        # Filter available events for current game
        self.available_events = self._get_available_events()
        
        # Cache completion and ownership status (checked once, not every frame)
        self._completion_cache = {}
        self._ownership_cache = {}
        self._refresh_status_cache()
        
        # Navigation state
        self.selected_index = 0
        
        # Message display
        self.message = None
        self.message_time = 0
        self.message_duration = 3000  # 3 seconds
        
        # Confirmation dialog state
        self.confirming = False
        self.confirm_event_key = None
        
        # Load claimed events tracker
        self.claimed_events = self._load_claimed_events()
    
    def _get_game_name(self):
        """Fallback game name detection from parser (used if not passed from main)"""
        if not self.manager or not self.manager.is_loaded():
            return None
        
        try:
            if hasattr(self.manager, 'parser'):
                raw_name = getattr(self.manager.parser, 'game_name', None)
                if raw_name and raw_name in ['Ruby', 'Sapphire', 'Emerald', 'FireRed', 'LeafGreen']:
                    return raw_name
        except:
            pass
        
        return None
    
    def _get_game_type(self):
        """Get the game type (RSE or FRLG) based on game name"""
        if self.game_name in ('FireRed', 'LeafGreen'):
            return 'FRLG'
        return 'RSE'  # Ruby, Sapphire, Emerald all use RSE format
    
    def _is_compatible_save(self, loaded_game):
        """Check if the loaded save is compatible with the expected game.
        
        The parser returns paired names like 'Ruby/Sapphire' or 'FireRed/LeafGreen'
        because it can't distinguish between paired games. This method handles that.
        
        Args:
            loaded_game: The game name returned by parser.game_name
            
        Returns:
            bool: True if the loaded save is compatible with self.game_name
        """
        if not loaded_game or not self.game_name:
            return False
        
        # Exact match
        if loaded_game == self.game_name:
            return True
        
        # Handle paired game names from parser
        paired_games = {
            'Ruby/Sapphire': ['Ruby', 'Sapphire'],
            'FireRed/LeafGreen': ['FireRed', 'LeafGreen'],
        }
        
        for paired_name, games in paired_games.items():
            if loaded_game == paired_name and self.game_name in games:
                return True
        
        # Emerald is its own thing
        if loaded_game == 'Emerald' and self.game_name == 'Emerald':
            return True
        
        return False
    
    def _get_available_events(self):
        """Get list of events available for current game"""
        if not self.game_name:
            print(f"[Events] No game name detected, no events available")
            return []
        
        available = []
        for event_key in EVENT_ORDER:
            event_info = EVENT_ITEMS[event_key]
            if self.game_name in event_info['compatible']:
                available.append(event_key)
        
        if available:
            print(f"[Events] Available events for {self.game_name}: {available}")
        
        return available
    
    def _refresh_status_cache(self):
        """Refresh the cached completion and ownership status for all events."""
        self._completion_cache = {}
        self._ownership_cache = {}
        
        for event_key in self.available_events:
            self._ownership_cache[event_key] = self._check_has_item(event_key)
            self._completion_cache[event_key] = self._check_event_complete(event_key)
        
        # Log status once
        for event_key in self.available_events:
            owned = self._ownership_cache.get(event_key, False)
            complete = self._completion_cache.get(event_key, False)
            status = "COMPLETE" if complete else ("OWNED" if owned else "Available")
            print(f"[Events] {event_key}: {status}")
    
    def _check_has_item(self, event_key):
        """Actually check if save has the item (called once for caching)."""
        if not self.manager or not self.manager.is_loaded():
            return False
        
        try:
            # Verify the loaded save matches the expected game
            # Parser returns "Ruby/Sapphire" or "FireRed/LeafGreen" for paired games
            loaded_game = getattr(self.manager.parser, 'game_name', None)
            if not self._is_compatible_save(loaded_game):
                print(f"[Events] WARNING: Expected {self.game_name} but manager has {loaded_game} loaded - cannot check item ownership")
                return False
            
            from save_writer import has_event_item
            return has_event_item(self.manager.parser.data, self.game_type, event_key)
        except Exception as e:
            print(f"[Events] Error checking item: {e}")
            return False
    
    def _check_event_complete(self, event_key):
        """Check if event is truly complete using Sinew OT verification.
        
        Returns True only if:
        1. The event encounter flag is set (Pokemon caught/defeated at location)
        2. The player has the Pokemon with OT != "SINEW" (not just from achievement rewards)
        
        This prevents events from showing as "complete" just because the player
        received the Pokemon as an achievement reward.
        """
        if not self.manager or not self.manager.is_loaded():
            return False
        
        try:
            from save_writer import is_event_truly_complete
            
            # CRITICAL: Verify the loaded save matches the expected game
            # Parser returns "Ruby/Sapphire" or "FireRed/LeafGreen" for paired games
            loaded_game = getattr(self.manager.parser, 'game_name', None)
            if not self._is_compatible_save(loaded_game):
                print(f"[Events] WARNING: Expected {self.game_name} but manager has {loaded_game} loaded - cannot check completion")
                return False
            
            # Get party and PC data for OT checking
            party = []
            pc_pokemon = []
            
            try:
                party = self.manager.get_party() or []
            except Exception as e:
                print(f"[Events] Could not get party: {e}")
            
            # Get PC Pokemon using get_box() method (same as main.py)
            try:
                if hasattr(self.manager, 'get_box'):
                    for box_num in range(1, 15):
                        box = self.manager.get_box(box_num)
                        if box:
                            for p in box:
                                if p and not p.get('empty'):
                                    pc_pokemon.append(p)
            except Exception as e:
                print(f"[Events] Could not get PC Pokemon: {e}")
            
            result = is_event_truly_complete(
                self.manager.parser.data,
                self.game_type,
                self.game_name,
                event_key,
                party=party,
                pc_pokemon=pc_pokemon
            )
            
            print(f"[Events] {event_key} completion: {result}")
            return result.get('complete', False)
            
        except Exception as e:
            print(f"[Events] Error checking event completion: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_claimed_events(self):
        """Load which events have been claimed from sinew_data.json"""
        try:
            data_path = os.path.join("data", "sinew_data.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    data = json.load(f)
                    return data.get('events_claimed', {})
        except Exception as e:
            print(f"[Events] Error loading claimed events: {e}")
        
        return {}
    
    def _save_claimed_events(self):
        """Save claimed events to sinew_data.json"""
        try:
            data_path = os.path.join("data", "sinew_data.json")
            
            # Load existing data
            data = {}
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    data = json.load(f)
            
            # Update events claimed
            data['events_claimed'] = self.claimed_events
            
            # Ensure data directory exists
            os.makedirs(os.path.dirname(data_path), exist_ok=True)
            
            # Write back
            with open(data_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"[Events] Saved claimed events")
        except Exception as e:
            print(f"[Events] Error saving claimed events: {e}")
    
    def _has_item_in_save(self, event_key):
        """Check if the current save already has this event item (uses cache)."""
        return self._ownership_cache.get(event_key, False)
    
    def _is_event_complete(self, event_key):
        """Check if the event has been completed (uses cache)."""
        return self._completion_cache.get(event_key, False)
    
    def _claim_event(self, event_key):
        """Claim an event item and add it to the current save"""
        if not self.manager or not self.manager.is_loaded():
            self._show_message("No save file loaded!", (255, 100, 100))
            return False
        
        try:
            from save_writer import add_event_item, write_save_file
            
            # Verify the loaded save matches the expected game
            # Parser returns "Ruby/Sapphire" or "FireRed/LeafGreen" for paired games
            loaded_game = getattr(self.manager.parser, 'game_name', None)
            if not self._is_compatible_save(loaded_game):
                self._show_message(f"Wrong save loaded! ({loaded_game})", (255, 100, 100))
                return False
            
            event_info = EVENT_ITEMS[event_key]
            
            # Check if already has item - this is the only thing that blocks claiming
            if self._has_item_in_save(event_key):
                self._show_message(f"Already have {event_info['name']}!", (255, 200, 100))
                return False
            
            # Add the item to save data
            success, msg = add_event_item(
                self.manager.parser.data,
                self.game_type,
                self.game_name,
                event_key
            )
            
            if success:
                # Write the modified save
                write_save_file(self.manager.save_path, self.manager.parser.data, create_backup_first=True)
                
                # Mark as claimed globally
                self.claimed_events[event_key] = True
                self._save_claimed_events()
                
                # Trigger callback for achievement tracking
                if self.on_event_claimed:
                    self.on_event_claimed(event_key)
                
                self._show_message(f"Received {event_info['name']}!", (100, 255, 100))
                
                # Refresh cache since we now own the item
                self._ownership_cache[event_key] = True
                
                return True
            else:
                self._show_message(msg, (255, 100, 100))
                return False
            
        except Exception as e:
            print(f"[Events] Error claiming event: {e}")
            import traceback
            traceback.print_exc()
            self._show_message(f"Error: {str(e)[:30]}", (255, 100, 100))
            return False
    
    def _show_message(self, text, color=(255, 255, 255)):
        """Show a temporary message"""
        self.message = (text, color)
        self.message_time = pygame.time.get_ticks()
    
    def handle_controller(self, ctrl):
        """Handle controller input"""
        consumed = False
        
        # Handle confirmation dialog
        if self.confirming:
            if ctrl.is_button_just_pressed('A'):
                ctrl.consume_button('A')
                self._claim_event(self.confirm_event_key)
                self.confirming = False
                self.confirm_event_key = None
                consumed = True
            elif ctrl.is_button_just_pressed('B'):
                ctrl.consume_button('B')
                self.confirming = False
                self.confirm_event_key = None
                consumed = True
            return consumed
        
        # Normal navigation
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            if len(self.available_events) > 0:
                self.selected_index = (self.selected_index - 1) % len(self.available_events)
            consumed = True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            if len(self.available_events) > 0:
                self.selected_index = (self.selected_index + 1) % len(self.available_events)
            consumed = True
        
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if len(self.available_events) > 0:
                event_key = self.available_events[self.selected_index]
                event_info = EVENT_ITEMS[event_key]
                
                # Only block if already have the ticket item
                if self._has_item_in_save(event_key):
                    self._show_message("Already in your Key Items!", (255, 200, 100))
                else:
                    # Show confirmation - allow claiming even if Pokemon already caught
                    self.confirming = True
                    self.confirm_event_key = event_key
            consumed = True
        
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            self.should_close = True
            consumed = True
        
        return consumed
    
    def update(self, events):
        """Handle pygame events"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.confirming:
                        self.confirming = False
                        self.confirm_event_key = None
                    else:
                        self.should_close = True
    
    def draw(self, surf):
        """Draw the events screen"""
        # Background
        surf.fill((30, 30, 45))
        
        # Title
        title = "Mystery Events"
        title_surf = self.font_header.render(title, True, (255, 215, 0))
        surf.blit(title_surf, (self.w // 2 - title_surf.get_width() // 2, 8))
        
        # Subtitle with game name
        if self.game_name:
            subtitle = f"Playing: {self.game_name}"
            sub_surf = self.font_small.render(subtitle, True, (150, 150, 150))
            surf.blit(sub_surf, (self.w // 2 - sub_surf.get_width() // 2, 26))
        
        # No events available message
        if len(self.available_events) == 0:
            no_events_text = "No events available for this game"
            no_events_surf = self.font_text.render(no_events_text, True, (200, 200, 200))
            surf.blit(no_events_surf, (self.w // 2 - no_events_surf.get_width() // 2, self.h // 2))
        else:
            # Draw event list
            self._draw_event_list(surf)
        
        # Draw confirmation dialog if active
        if self.confirming and self.confirm_event_key:
            self._draw_confirmation(surf)
        
        # Draw message if active
        current_time = pygame.time.get_ticks()
        if self.message and current_time - self.message_time < self.message_duration:
            self._draw_message(surf)
        
        # Controller hints - very bottom, small and dimmed
        if self.confirming:
            hints = "A:Confirm  B:Cancel"
        else:
            hints = "D-Pad:Select  A:Claim  B:Back"
        hint_surf = self.font_small.render(hints, True, (80, 80, 80))
        surf.blit(hint_surf, (self.w // 2 - hint_surf.get_width() // 2, self.h - 14))
    
    def _draw_event_list(self, surf):
        """Draw the list of available events"""
        list_y = 42
        item_height = 52
        max_visible = 4  # Max items that fit
        
        for i, event_key in enumerate(self.available_events):
            if i >= max_visible:
                break
            
            event_info = EVENT_ITEMS[event_key]
            y = list_y + (i * item_height)
            
            # Item box
            item_rect = pygame.Rect(12, y, self.w - 24, item_height - 3)
            
            # Selection highlight
            is_selected = (i == self.selected_index)
            if is_selected:
                pygame.draw.rect(surf, (60, 70, 100), item_rect, border_radius=5)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, item_rect, 2, border_radius=5)
            else:
                pygame.draw.rect(surf, (40, 45, 60), item_rect, border_radius=5)
                pygame.draw.rect(surf, (60, 60, 80), item_rect, 1, border_radius=5)
            
            # Icon/color indicator
            icon_rect = pygame.Rect(item_rect.x + 5, item_rect.y + 5, 36, 36)
            pygame.draw.rect(surf, event_info['icon_color'], icon_rect, border_radius=5)
            
            # Check status
            has_item = self._has_item_in_save(event_key)
            is_complete = self._is_event_complete(event_key)
            
            # Name
            if is_complete:
                name_color = (100, 200, 100)  # Green for complete
            elif has_item:
                name_color = (255, 200, 100)  # Yellow/orange for owned but incomplete
            else:
                name_color = (255, 255, 255)  # White for available
            name_surf = self.font_text.render(event_info['name'], True, name_color)
            surf.blit(name_surf, (item_rect.x + 48, item_rect.y + 4))
            
            # Status badge - right side, colored appropriately
            if is_complete:
                status = "COMPLETE"
                status_color = (100, 255, 100)  # Bright green
            elif has_item:
                status = "INCOMPLETE"
                status_color = (255, 100, 100)  # Red - has ticket but hasn't caught Pokemon
            else:
                status = "Available"
                status_color = (200, 200, 100)  # Yellow
            status_surf = self.font_small.render(status, True, status_color)
            surf.blit(status_surf, (item_rect.right - status_surf.get_width() - 6, item_rect.y + 6))
            
            # Pokemon unlocked
            pokemon_text = f"Unlocks: {event_info['pokemon']}"
            pokemon_surf = self.font_small.render(pokemon_text, True, (180, 180, 180))
            surf.blit(pokemon_surf, (item_rect.x + 48, item_rect.y + 20))
            
            # Description (truncate if too long)
            desc = event_info['desc']
            if len(desc) > 45:
                desc = desc[:42] + "..."
            desc_surf = self.font_small.render(desc, True, (120, 120, 120))
            surf.blit(desc_surf, (item_rect.x + 48, item_rect.y + 34))
    
    def _draw_confirmation(self, surf):
        """Draw confirmation dialog"""
        event_info = EVENT_ITEMS.get(self.confirm_event_key, {})
        
        # Overlay
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))
        
        # Dialog box
        dialog_w = 260
        dialog_h = 90
        dialog_x = (self.w - dialog_w) // 2
        dialog_y = (self.h - dialog_h) // 2
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        
        pygame.draw.rect(surf, (40, 45, 60), dialog_rect, border_radius=8)
        pygame.draw.rect(surf, (255, 215, 0), dialog_rect, 3, border_radius=8)
        
        # Title
        title = f"Receive {event_info.get('name', 'Item')}?"
        title_surf = self.font_text.render(title, True, (255, 255, 255))
        surf.blit(title_surf, (dialog_x + dialog_w // 2 - title_surf.get_width() // 2, dialog_y + 12))
        
        # Warning text
        warn_text = "Item will be added to Key Items"
        warn_surf = self.font_small.render(warn_text, True, (180, 180, 180))
        surf.blit(warn_surf, (dialog_x + dialog_w // 2 - warn_surf.get_width() // 2, dialog_y + 38))
        
        # Buttons hint
        btn_text = "A = Yes   B = No"
        btn_surf = self.font_small.render(btn_text, True, (150, 200, 150))
        surf.blit(btn_surf, (dialog_x + dialog_w // 2 - btn_surf.get_width() // 2, dialog_y + 62))
    
    def _draw_message(self, surf):
        """Draw temporary message"""
        if not self.message:
            return
        
        text, color = self.message
        
        # Message box positioned above footer
        msg_surf = self.font_text.render(text, True, color)
        msg_rect = msg_surf.get_rect(centerx=self.w // 2, bottom=self.h - 22)
        
        # Background
        bg_rect = msg_rect.inflate(16, 8)
        pygame.draw.rect(surf, (40, 40, 50), bg_rect, border_radius=4)
        pygame.draw.rect(surf, color, bg_rect, 2, border_radius=4)
        
        surf.blit(msg_surf, msg_rect)


# =============================================================================
# INTEGRATION HELPER
# =============================================================================

def is_events_unlocked(manager=None):
    """
    Check if the Events menu should be unlocked for current game.
    Requires: Player is Champion (8 badges) in the current save.
    
    For FRLG games, also requires:
    - National Dex unlocked
    - Rainbow Pass obtained
    
    Note: The full unlock also requires the Endgame Access achievement
    to be claimed, which is checked in main.py
    
    Args:
        manager: SaveDataManager instance (uses get_manager() if None)
        
    Returns:
        bool: True if current save meets requirements
    """
    if manager is None:
        manager = get_manager()
    
    if not manager or not manager.is_loaded():
        return False
    
    try:
        badges = manager.get_badges()
        badge_count = sum(1 for b in badges if b)
        
        if badge_count < 8:
            return False
        
        # For FRLG, check additional prerequisites
        game_name = getattr(manager.parser, 'game_name', None)
        if game_name in ('FireRed', 'LeafGreen'):
            try:
                from save_writer import check_frlg_event_prerequisites
                prereqs_met, details = check_frlg_event_prerequisites(
                    manager.parser.data,
                    'FRLG',
                    game_name
                )
                if not prereqs_met:
                    print(f"[Events] FRLG prerequisites not met: {details}")
                    return False
            except Exception as e:
                print(f"[Events] Error checking FRLG prerequisites: {e}")
                # Default to NOT allowing access if we can't verify prerequisites
                return False
        
        return True
        
    except Exception as e:
        print(f"[Events] Error checking badge count: {e}")
        return False


def get_events_unlock_status(manager=None):
    """
    Get detailed unlock status for Events menu.
    
    Args:
        manager: SaveDataManager instance (uses get_manager() if None)
        
    Returns:
        dict: {
            'unlocked': bool,
            'badge_count': int,
            'is_champion': bool,
            'game_name': str or None,
            'frlg_prereqs': dict or None (for FRLG games)
        }
    """
    if manager is None:
        manager = get_manager()
    
    status = {
        'unlocked': False,
        'badge_count': 0,
        'is_champion': False,
        'game_name': None,
        'frlg_prereqs': None
    }
    
    if not manager or not manager.is_loaded():
        return status
    
    try:
        badges = manager.get_badges()
        status['badge_count'] = sum(1 for b in badges if b)
        status['is_champion'] = status['badge_count'] >= 8
        status['game_name'] = getattr(manager.parser, 'game_name', None)
        
        if not status['is_champion']:
            return status
        
        # For FRLG, check additional prerequisites
        if status['game_name'] in ('FireRed', 'LeafGreen'):
            try:
                from save_writer import check_frlg_event_prerequisites
                prereqs_met, details = check_frlg_event_prerequisites(
                    manager.parser.data,
                    'FRLG',
                    status['game_name']
                )
                status['frlg_prereqs'] = details
                status['unlocked'] = prereqs_met
            except Exception as e:
                print(f"[Events] Error checking FRLG prerequisites: {e}")
                status['unlocked'] = True  # Default to allowing
        else:
            status['unlocked'] = True
            
    except Exception as e:
        print(f"[Events] Error getting unlock status: {e}")
    
    return status

def check_frlg_prerequisites(manager=None):
    """
    Check if FRLG-specific event prerequisites are met.
    This is a helper function for main.py to call.
    
    For FireRed/LeafGreen, events require:
    - National Dex unlocked
    - Rainbow Pass obtained
    
    For RSE games, always returns True.
    
    Args:
        manager: SaveDataManager instance (uses get_manager() if None)
        
    Returns:
        tuple: (met: bool, details: dict or None)
    """
    if manager is None:
        manager = get_manager()
    
    if not manager or not manager.is_loaded():
        return (False, {'error': 'No save loaded'})
    
    try:
        game_name = getattr(manager.parser, 'game_name', None)
        
        # RSE games don't have additional prerequisites
        if game_name not in ('FireRed', 'LeafGreen'):
            return (True, {'game': game_name, 'required': False})
        
        # Check FRLG prerequisites
        from save_writer import check_frlg_event_prerequisites
        return check_frlg_event_prerequisites(
            manager.parser.data,
            'FRLG',
            game_name
        )
    except Exception as e:
        print(f"[Events] Error checking FRLG prerequisites: {e}")
        return (False, {'error': str(e)})