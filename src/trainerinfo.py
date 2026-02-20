"""
Trainer Info Screen with Controller Support
Displays trainer card information with gamepad navigation
"""

import pygame
import json
import config
import os
import inspect
from ui_components import Button
import ui_colors
from save_data_manager import get_manager
from controller import get_controller, NavigableList
from pygame import image

FONT_PATH = "fonts/Pokemon_GB.ttf"


# ====================================================================
# MODAL WRAPPER
# ====================================================================

class Modal:
    def __init__(self, w, h, font, prev_game_callback=None, next_game_callback=None, 
                 get_current_game_callback=None):
        self.width = w
        self.height = h
        self.font = font
        self.prev_game_callback = prev_game_callback
        self.next_game_callback = next_game_callback
        self.get_current_game_callback = get_current_game_callback
        self.screen = TrainerInfoScreen(w, h, prev_game_callback, next_game_callback, 
                                        get_current_game_callback)

    def update(self, events):
        self.screen.update(events)
        # Check if screen wants to close
        return not self.screen.should_close
    
    def handle_controller(self, ctrl):
        """Handle controller input"""
        return self.screen.handle_controller(ctrl)

    def draw(self, surf):
        # Draw background overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((50, 50, 50, 180))
        surf.blit(overlay, (0, 0))

        # Outer border
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, (0, 0, self.width, self.height), 2)

        # Draw the TrainerInfoScreen on the same surface
        self.screen.draw(surf)




# ====================================================================
# TRAINER INFO SCREEN
# ====================================================================

class TrainerInfoScreen:

    def __init__(self, w, h, prev_game_callback=None, next_game_callback=None, 
                 get_current_game_callback=None):
        self.w = w
        self.h = h
        self.should_close = False  # Flag for closing modal
        self.sub_modal = None  # Sub-modal (like Item Bag)
        
        # Game switching callbacks
        self.prev_game_callback = prev_game_callback
        self.next_game_callback = next_game_callback
        self.get_current_game_callback = get_current_game_callback
        
        # Game switch cooldown - time-based to span across frames
        # Set high to prevent repeat triggers during GIF loading
        self._last_game_switch_time = 0
        self._game_switch_cooldown_ms = 800  # 800ms cooldown (longer than controller repeat delay)

        # --- Load your font (larger sizes now) ---
        self.font_header = pygame.font.Font(FONT_PATH, 18)
        self.font_text   = pygame.font.Font(FONT_PATH, 14)
        self.font_small  = pygame.font.Font(FONT_PATH, 10)

        # Get save data manager
        self.manager = get_manager()
        
        # Get controller
        self.controller = get_controller()

        # --------------------------------------------------------
        # LAYOUT POSITIONS
        # --------------------------------------------------------

        # Header
        self.pos_title = (20, 15)
        self.pos_id = (w - 180, 15)

        # Trainer info section (left side)
        self.pos_name = (30, 70)
        self.pos_gender = (30, 95)
        self.pos_money = (30, 120)
        self.pos_pokedex = (30, 145)
        self.pos_time = (30, 170)

        # Badges section (bottom)
        self.badge_x = 30
        self.badge_y = h - 60
        self.badge_size = 35
        self.badge_gap = 10
        
        # Load badge sprites
        self.badge_sprites = self._load_badge_sprites()

        # Right side buttons (removed Pokedex - available from game screen)
        self.buttons = [
            Button("Party",    (0.55, 0.20, 0.30, 0.10), self.open_party),
            Button("Item Bag", (0.55, 0.32, 0.30, 0.10), self.open_item_bag),
            Button("Back",     (0.55, 0.44, 0.30, 0.10), self.go_back),
        ]
        
        # Button navigation
        self.button_nav = NavigableList(len(self.buttons), columns=1, wrap=True)
        self.selected_button = 0
    
    def _load_badge_sprites(self):
        """Load badge sprites based on game type (Kanto or Hoenn)"""
        badges = []
        
        # Determine which badges to load based on game type
        if self.manager.is_loaded():
            trainer_info = self.manager.get_trainer_info()
            game_type = trainer_info.get('game_type', 'RSE') if trainer_info else 'RSE'
        else:
            game_type = 'RSE'
        
        # Badge folder path - FRLG uses Kanto, RSE uses Hoenn
        if game_type == 'FRLG':
            badge_folder = os.path.join("data", "sprites", "badges", "kanto")
            # Kanto badge names (in order)
            badge_names = [
                "boulder", "cascade", "thunder", "rainbow",
                "soul", "marsh", "volcano", "earth"
            ]
        else:
            badge_folder = os.path.join("data", "sprites", "badges", "hoenn")
            # Hoenn badge names (in order)
            badge_names = [
                "stone", "knuckle", "dynamo", "heat",
                "balance", "feather", "mind", "rain"
            ]
        
        for name in badge_names:
            # Try common image extensions
            badge_path = None
            for ext in [".png", ".PNG", ".gif", ".GIF"]:
                test_path = os.path.join(badge_folder, f"{name}{ext}")
                if os.path.exists(test_path):
                    badge_path = test_path
                    break
            
            if badge_path:
                try:
                    sprite = pygame.image.load(badge_path).convert_alpha()
                    # Scale to badge_size
                    sprite = pygame.transform.scale(sprite, (self.badge_size, self.badge_size))
                    badges.append(sprite)
                except Exception as e:
                    badges.append(None)
            else:
                badges.append(None)
        
        return badges


    # --------------------------------------------------------
    # CONTROLLER SUPPORT
    # --------------------------------------------------------
    
    def handle_controller(self, ctrl):
        """
        Handle controller input for TrainerInfoScreen and any sub-modal.
        Works with modals that expect either 1 or 2 arguments.
        """
        consumed = False

        # --- If a sub-modal is open, send input to it first ---
        if self.sub_modal:
            if hasattr(self.sub_modal, 'handle_controller'):
                # Inspect the method signature
                sig = inspect.signature(self.sub_modal.handle_controller)
                if len(sig.parameters) == 1:
                    # Only expects ctrl
                    result = self.sub_modal.handle_controller(ctrl)
                else:
                    # Expects ctrl + current_time_ms
                    result = self.sub_modal.handle_controller(ctrl, pygame.time.get_ticks())

                consumed = True

            # B button closes sub-modal
            if ctrl.is_button_just_pressed('B'):
                ctrl.consume_button('B')
                self.sub_modal = None
                consumed = True

            return consumed  # All input consumed by sub-modal

        # --- Modal-level controls for TrainerInfoScreen itself ---
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            self.should_close = True
            return True

        # Left/Right to switch games (skip Sinew) - with time-based cooldown
        current_time = pygame.time.get_ticks()
        can_switch = (current_time - self._last_game_switch_time) >= self._game_switch_cooldown_ms
        
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            if can_switch and self.prev_game_callback:
                self._last_game_switch_time = current_time
                self.prev_game_callback()
                self._reload_data()
            return True
        
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            if can_switch and self.next_game_callback:
                self._last_game_switch_time = current_time
                self.next_game_callback()
                self._reload_data()
            return True

        # D-Pad up/down navigation
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            self.selected_button = (self.selected_button - 1) % len(self.buttons)
            return True
        
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            self.selected_button = (self.selected_button + 1) % len(self.buttons)
            return True

        # A button activates selected button
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if 0 <= self.selected_button < len(self.buttons):
                self.buttons[self.selected_button].callback()
            return True

        # Start button closes modal too
        if ctrl.is_button_just_pressed('START'):
            ctrl.consume_button('START')
            self.should_close = True
            return True

        return consumed
    
    def _reload_data(self):
        """Reload data after switching games"""
        # Re-get the manager (it should be updated after game switch)
        self.manager = get_manager()
        # Reload badge sprites for new game type
        self.badge_sprites = self._load_badge_sprites()


    # --------------------------------------------------------
    # LOAD TRAINER DATA FROM SAVE
    # --------------------------------------------------------

    def load_trainer_data(self):
        """Load trainer data from save file manager"""
        if not self.manager.is_loaded():
            # Fallback to default data
            return {
                "name": "Unknown",
                "id": "00000",
                "gender": "Unknown",
                "money": 0,
                "pokedex": "0/386",
                "time": "00:00:00"
            }
        
        # Get trainer info from parser
        trainer_info = self.manager.get_trainer_info()
        pokedex = self.manager.get_pokedex_count()
        play_time = self.manager.get_play_time()
        
        # Format data for display
        return {
            "name": trainer_info['name'] or "Unknown",
            "id": self.manager.format_trainer_id(show_secret=False),
            "gender": trainer_info['gender'],
            "money": trainer_info['money'],
            "pokedex": f"{pokedex['caught']}/386",  # Gen 3 has 386 Pokemon
            "time": f"{play_time['hours']:03d}:{play_time['minutes']:02d}:{play_time['seconds']:02d}"
        }


    # --------------------------------------------------------
    # BUTTON CALLBACKS
    # --------------------------------------------------------

    def open_party(self):
        """Open Party screen as sub-modal"""
        if not self.manager.is_loaded():
            print("No save file loaded")
            return

        import pygame
        import os
        from party_screen import PartyScreen

        party = self.manager.get_party() or []
        party_data = []

        for i in range(6):
            p = party[i] if i < len(party) else None

            if p is None or p.get("empty"):
                party_data.append(None)
                continue

            # ------------------------------
            # Load GEN3 sprite (PNG only)
            # ------------------------------
            sprite_path = self.manager.get_gen3_sprite_path(p)
            sprite_surf = None

            if sprite_path and os.path.exists(sprite_path):
                try:
                    sprite_surf = pygame.image.load(sprite_path).convert_alpha()
                except Exception as e:
                    print(f"Sprite load failed for {sprite_path}: {e}")

            # ------------------------------
            # Name / Level
            # ------------------------------
            name = (
                p.get("nickname")
                or p.get("species_name")
                or p.get("species")
                or "Unknown"
            )

            # ------------------------------
            # Build final dict
            # ------------------------------
            party_data.append({
                "name": name,
                "level": p.get("level", "?"),
                "types": p.get("types", []),
                "hp": p.get("current_hp", p.get("hp", 0)),  # Parser uses current_hp
                "max_hp": p.get("max_hp", 1),
                "sprite": sprite_surf,
                "raw": p   # pass-through original dict for extra details later
            })

        # Close callback
        def close_party():
            self.sub_modal = None

        # Determine game type
        trainer_info = self.manager.get_trainer_info()
        game_type = trainer_info.get('game_type', 'RSE') if trainer_info else 'RSE'

        # Create the PartyScreen
        self.sub_modal = PartyScreen(
            width=self.w,
            height=self.h,
            party_data=party_data,
            close_callback=close_party,
            manager=self.manager,
            game_type=game_type
        )

        print("Opened Party screen.")


    def open_item_bag(self):
        """Open item bag screen as sub-modal"""
        if self.manager.is_loaded():
            try:
                from Itembag import Modal as ItemBagModal
                self.sub_modal = ItemBagModal(self.w, self.h, self.font_text)
                print("Opening Item Bag modal")
            except ImportError as e:
                print(f"Could not import Item Bag: {e}")
        else:
            print("No save file loaded")
    
    def go_back(self):
        """Close trainer info and go back"""
        # Set a flag that the parent modal can check
        self.should_close = True


    # --------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------

    def update(self, events):
        # If sub-modal is open, update it
        if self.sub_modal:
            if hasattr(self.sub_modal, 'update'):
                result = self.sub_modal.update(events)
                # Check if sub-modal wants to close
                if hasattr(self.sub_modal, 'screen') and hasattr(self.sub_modal.screen, 'should_close'):
                    if self.sub_modal.screen.should_close:
                        self.sub_modal = None
            
            # Handle events for sub-modal
            for e in events:
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    self.sub_modal = None
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    if hasattr(self.sub_modal, 'handle_mouse'):
                        self.sub_modal.handle_mouse(e)
            return
        
        for e in events:
            for b in self.buttons:
                b.handle_event(e)
            
            # Keyboard navigation
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_UP:
                    self.selected_button = (self.selected_button - 1) % len(self.buttons)
                elif e.key == pygame.K_DOWN:
                    self.selected_button = (self.selected_button + 1) % len(self.buttons)
                elif e.key == pygame.K_RETURN:
                    if 0 <= self.selected_button < len(self.buttons):
                        self.buttons[self.selected_button].callback()
                elif e.key == pygame.K_ESCAPE:
                    self.should_close = True


    # --------------------------------------------------------
    # DRAW
    # --------------------------------------------------------

    def draw(self, surf):
        # Fill inside the border (transparent black to show overlay behind)
        # Don't fill solid - let the transparent overlay from Modal show through
        pass  # The Modal already draws the background

        # Load fresh trainer data each draw
        trainer = self.load_trainer_data()

        # HEADER
        surf.blit(self.font_header.render("TRAINER CARD", True, ui_colors.COLOR_TEXT), self.pos_title)

        id_surf = self.font_header.render(f"IDNo. {trainer['id']}", True, ui_colors.COLOR_TEXT)
        surf.blit(id_surf, self.pos_id)

        # INFO TEXT (left side)
        surf.blit(self.font_text.render(f"Name: {trainer['name']}", True, ui_colors.COLOR_TEXT), self.pos_name)
        surf.blit(self.font_text.render(f"Gender: {trainer['gender']}", True, ui_colors.COLOR_TEXT), self.pos_gender)
        surf.blit(self.font_text.render(f"Money: ${trainer['money']}", True, ui_colors.COLOR_TEXT), self.pos_money)
        surf.blit(self.font_text.render(f"Pokedex: {trainer['pokedex']}", True, ui_colors.COLOR_TEXT), self.pos_pokedex)
        surf.blit(self.font_text.render(f"Time: {trainer['time']}", True, ui_colors.COLOR_TEXT), self.pos_time)

        # BADGES (bottom)
        badges_earned = self.manager.get_badges() if self.manager.is_loaded() else [False] * 8
        for i in range(8):
            x = self.badge_x + i * (self.badge_size + self.badge_gap)
            
            # Draw badge slot background
            badge_surf = pygame.Surface((self.badge_size, self.badge_size), pygame.SRCALPHA)
            
            if badges_earned[i] and i < len(self.badge_sprites) and self.badge_sprites[i]:
                # Draw earned badge sprite
                surf.blit(self.badge_sprites[i], (x, self.badge_y))
            else:
                # Draw empty slot (darker, greyed out)
                pygame.draw.rect(badge_surf, (60, 60, 60, 180), (0, 0, self.badge_size, self.badge_size), border_radius=6)
                surf.blit(badge_surf, (x, self.badge_y))
            
            # Draw border around slot
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, (x, self.badge_y, self.badge_size, self.badge_size), 2, border_radius=6)

        # RIGHT BUTTONS - with controller selection indicator
        for i, b in enumerate(self.buttons):
            # Check if this button is selected by controller
            is_selected = (i == self.selected_button)
            
            # Draw selection indicator
            if is_selected:
                # Draw cursor arrow
                arrow_x = b.rect.x - 20
                arrow_y = b.rect.centery - 8
                arrow_surf = self.font_text.render(">", True, ui_colors.COLOR_HIGHLIGHT)
                surf.blit(arrow_surf, (arrow_x, arrow_y))
                
                # Draw highlight border
                highlight_rect = b.rect.inflate(4, 4)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 2)
            
            b.draw(surf, self.font_text)
        
        # Controller hints
        try:
            hints = "D-Pad: Navigate  A: Select  B: Back"
            hint_surf = self.font_small.render(hints, True, (120, 120, 120))
            surf.blit(hint_surf, (10, self.h - 15))
        except:
            pass
        
        # Draw sub-modal on top if open
        if self.sub_modal:
            if hasattr(self.sub_modal, 'draw'):
                self.sub_modal.draw(surf)