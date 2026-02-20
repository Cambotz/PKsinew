# PokedexModal.py
import os
import pygame
import json
from ui_components import Button

# Import ui_colors module for dynamic theme support
import ui_colors

# Constants
INNER_GAP = 8
H_PADDING = 8
TOPBOT_PAD = 20
RIGHT_TOP_PAD = 4
ITEM_HEIGHT_DEFAULT = 24
SPRITE_FOLDER = os.path.join("data", "sprites", "gen3", "normal")
POKEMON_JSON = os.path.join("data", "pokemon_db.json")
DEFAULT_SCREEN = (640, 480)
FADE_ALPHA = 100

# Game icon filenames (order matters for display)
GAME_NAMES = ["Ruby", "Sapphire", "Emerald", "FireRed", "LeafGreen"]
GAME_ICON_FILES = {
    "Ruby": "ruby.png",
    "Sapphire": "sapphire.png",
    "Emerald": "emerald.png",
    "FireRed": "firered.png",
    "LeafGreen": "leafgreen.png",
}

class PokedexModal:
    def __init__(self, parent=None, pokedex_name="National Dex", json_path=POKEMON_JSON,
                 close_callback=None, get_current_game_callback=None, set_game_callback=None,
                 prev_game_callback=None, next_game_callback=None, save_data_manager=None,
                 combined_mode=False, all_save_paths=None, width=None, height=None):
        self.parent = parent
        self.pokedex_name = pokedex_name
        self.open = True
        self.close_callback = close_callback
        self.focus_mode = 'list'  # 'game_button' or 'list'

        # Save data manager for seen/caught status
        self.save_data_manager = save_data_manager
        self.seen_set = set()
        self.owned_set = set()
        
        # Combined mode - merge data from all saves (Sinew mode)
        self.combined_mode = combined_mode
        self.all_save_paths = all_save_paths or []
        
        # Per-game ownership tracking for combined mode
        # Dict mapping game_name -> set of owned pokemon IDs
        self.per_game_owned = {}
        # Dict mapping game_name -> set of seen pokemon IDs
        self.per_game_seen = {}
        
        # Detail view state
        self.showing_detail = False

        # Callbacks for game navigation
        self.get_current_game_callback = get_current_game_callback
        self.prev_game_callback = prev_game_callback
        self.next_game_callback = next_game_callback
        self.set_game_callback = set_game_callback

        # Load Pokemon data
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Pokemon DB not found: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle different JSON formats
        def get_pokemon_id(entry, key=None):
            """Extract pokemon ID from entry, checking various possible field names"""
            if isinstance(entry, dict):
                # Try common id field names
                for field in ['id', 'national_dex', 'dex_number', 'number', 'dex', 'national']:
                    if field in entry:
                        return entry[field]
                # If dict key was passed, use it
                if key is not None:
                    try:
                        return int(key)
                    except (ValueError, TypeError):
                        pass
            return 0
        
        if isinstance(data, dict):
            # Dict format - keys might be the IDs
            pokemon_list = []
            for key, entry in data.items():
                if isinstance(entry, dict):
                    entry_copy = entry.copy()
                    if 'id' not in entry_copy:
                        entry_copy['id'] = get_pokemon_id(entry, key)
                    if 'name' not in entry_copy:
                        entry_copy['name'] = str(key)
                    # Only add Pokemon with valid IDs (1-386 for Gen 3)
                    if 1 <= entry_copy.get('id', 0) <= 386:
                        pokemon_list.append(entry_copy)
            self.pokemon_data = sorted(pokemon_list, key=lambda x: x.get('id', 0))
        else:
            # List format
            pokemon_list = []
            for i, entry in enumerate(data):
                if isinstance(entry, dict):
                    entry_copy = entry.copy()
                    if 'id' not in entry_copy:
                        entry_copy['id'] = get_pokemon_id(entry) or (i + 1)
                    # Only add Pokemon with valid IDs
                    if 1 <= entry_copy.get('id', 0) <= 386:
                        pokemon_list.append(entry_copy)
                else:
                    if i >= 0:  # Skip index 0 which would be #0
                        pokemon_list.append({'id': i + 1, 'name': str(entry)})
            self.pokemon_data = sorted(pokemon_list, key=lambda x: x.get('id', 0))
        
        self.total = len(self.pokemon_data)

        # Screen size - use passed dimensions or fallback to display surface
        if width is not None and height is not None:
            self.screen_w, self.screen_h = width, height
        else:
            dsurf = pygame.display.get_surface()
            self.screen_w, self.screen_h = dsurf.get_size() if dsurf else DEFAULT_SCREEN

        # Fonts - scale based on screen height
        font_size = max(8, int(self.screen_h * 0.04))
        title_font_size = max(10, int(self.screen_h * 0.05))
        try:
            self.font = pygame.font.Font("fonts/Pokemon_GB.ttf", font_size)
            self.title_font = pygame.font.Font("fonts/Pokemon_GB.ttf", title_font_size)
        except Exception:
            self.font = pygame.font.SysFont(None, font_size)
            self.title_font = pygame.font.SysFont(None, title_font_size)

        # Sprite and list settings - scale item height based on screen
        self.item_height = max(16, int(self.screen_h * 0.065))
        self.selected_index = 0
        self.list_scroll = 0
        self.visible_items = 1
        self.gap = 8

        # Initialize top buttons
        self.left_game_arrow = Button("<", rel_rect=(0,0,0,0), callback=lambda: self.change_game(-1))
        self.game_button = Button(self.get_current_game(), rel_rect=(0,0,0,0), callback=lambda: print(f"Current game: {self.get_current_game()}"))
        self.right_game_arrow = Button(">", rel_rect=(0,0,0,0), callback=lambda: self.change_game(1))

        # Sprite caches
        self.sel_width = self.sel_height = self.small_width = self.small_height = 0
        self.sprite_cache = [None] * self.total
        self.sprite_cache_full = [None] * self.total
        self.sprite_cache_small = [None] * self.total

        # Layout
        self.calculate_layout()
        self.center_left_columns_vertically()
        self._load_and_presize_sprites()
        self._load_pokedex_data()
        
        # Load pokeball icon for caught Pokemon - try multiple paths
        self.pokeball_icon = None
        pokeball_size = max(14, int(self.screen_h * 0.045))  # Slightly larger base size
        pokeball_paths = [
            os.path.join("data", "sprites", "items", "poke-ball.png"),  # Correct path with hyphen
            os.path.join("data", "sprites", "items", "pokeball.png"),
            os.path.join("data", "sprites", "items", "poke_ball.png"),
            os.path.join("data", "sprites", "ball", "pokeball.png"),
            os.path.join("data", "items", "pokeball.png"),
        ]
        for ppath in pokeball_paths:
            if os.path.exists(ppath):
                try:
                    self.pokeball_icon = pygame.image.load(ppath).convert_alpha()
                    # Use scale (not smoothscale) for crisp pixel art
                    self.pokeball_icon = pygame.transform.scale(self.pokeball_icon, (pokeball_size, pokeball_size))
                    print(f"[Pokedex] Loaded pokeball icon from: {ppath}")
                    break
                except Exception as e:
                    print(f"[Pokedex] Failed to load {ppath}: {e}")
        
        # Create a simple pokeball fallback if no icon found
        if self.pokeball_icon is None:
            print("[Pokedex] Creating fallback pokeball icon")
            self.pokeball_icon = pygame.Surface((pokeball_size, pokeball_size), pygame.SRCALPHA)
            center = pokeball_size // 2
            radius = pokeball_size // 2 - 1
            pygame.draw.circle(self.pokeball_icon, (255, 80, 80), (center, center), radius)  # Red top
            pygame.draw.circle(self.pokeball_icon, (255, 255, 255), (center, center), radius, 1)  # White outline
            pygame.draw.rect(self.pokeball_icon, (40, 40, 40), (1, center - 1, pokeball_size - 2, 2))  # Center line
            pygame.draw.circle(self.pokeball_icon, (255, 255, 255), (center, center), max(2, pokeball_size // 5))  # Center button
        
        # Load masterball icon for "caught in all games"
        self.masterball_icon = None
        masterball_paths = [
            os.path.join("data", "sprites", "icons", "master-ball.png"),
            os.path.join("data", "sprites", "items", "master-ball.png"),
            os.path.join("data", "sprites", "items", "masterball.png"),
        ]
        for mpath in masterball_paths:
            if os.path.exists(mpath):
                try:
                    self.masterball_icon = pygame.image.load(mpath).convert_alpha()
                    # Use scale (not smoothscale) for crisp pixel art
                    self.masterball_icon = pygame.transform.scale(self.masterball_icon, (pokeball_size, pokeball_size))
                    print(f"[Pokedex] Loaded masterball icon from: {mpath}")
                    break
                except Exception as e:
                    print(f"[Pokedex] Failed to load masterball {mpath}: {e}")
        
        # Load eye icon for "seen but not caught"
        self.eye_icon = None
        eye_paths = [
            os.path.join("data", "sprites", "icons", "eye.png"),
            os.path.join("data", "sprites", "items", "eye.png"),
        ]
        for epath in eye_paths:
            if os.path.exists(epath):
                try:
                    self.eye_icon = pygame.image.load(epath).convert_alpha()
                    # Use smoothscale for eye icon (looks better anti-aliased)
                    self.eye_icon = pygame.transform.smoothscale(self.eye_icon, (pokeball_size, pokeball_size))
                    print(f"[Pokedex] Loaded eye icon from: {epath}")
                    break
                except Exception as e:
                    print(f"[Pokedex] Failed to load eye {epath}: {e}")
        
        # Load game icons for combined mode display
        self.game_icons = {}
        game_icon_size = max(18, int(self.screen_h * 0.055))  # Slightly larger than pokeball
        self.game_icon_size = game_icon_size
        icon_dir = os.path.join("data", "sprites", "icons")
        
        for game_name, icon_file in GAME_ICON_FILES.items():
            icon_path = os.path.join(icon_dir, icon_file)
            if os.path.exists(icon_path):
                try:
                    icon = pygame.image.load(icon_path).convert_alpha()
                    # Use smoothscale for game icons (they look better anti-aliased)
                    icon = pygame.transform.smoothscale(icon, (game_icon_size, game_icon_size))
                    self.game_icons[game_name] = icon
                    print(f"[Pokedex] Loaded game icon: {game_name}")
                except Exception as e:
                    print(f"[Pokedex] Failed to load game icon {icon_path}: {e}")

    # -----------------------
    # Layout & resizing
    # -----------------------
    def calculate_layout(self):
        PADDING = 8
        RIGHT_PAD = 40
        BOTTOM_PAD = 40

        usable_width = self.screen_w - PADDING - RIGHT_PAD
        left_col_ratio = 0.28
        right_col_width = usable_width - 2 * int(usable_width * left_col_ratio) - INNER_GAP * 2

        self.info_w = int(usable_width * left_col_ratio) + 2
        self.sprite_w = int(usable_width * left_col_ratio) + 2
        self.list_w = right_col_width - 4

        x_info = PADDING
        x_sprite = x_info + self.info_w + INNER_GAP
        x_list = x_sprite + self.sprite_w + INNER_GAP

        # Left columns
        top_button_height = int(0.08 * self.screen_h)
        button_gap = PADDING
        left_bottom_pad = BOTTOM_PAD
        left_content_h = self.screen_h - top_button_height - button_gap - left_bottom_pad - PADDING
        left_top = top_button_height + button_gap + PADDING

        self.stats_rect = pygame.Rect(x_info, left_top, self.info_w, left_content_h)
        self.sprite_rect = pygame.Rect(x_sprite, left_top, self.sprite_w, left_content_h)

        # Right column
        right_top = PADDING
        right_bottom = self.screen_h - BOTTOM_PAD
        self.list_rect = pygame.Rect(x_list, right_top, self.screen_w - x_list - RIGHT_PAD, right_bottom - right_top)

        # Top buttons across left 2 columns
        left_two_width = self.stats_rect.width + INNER_GAP + self.sprite_rect.width
        left_two_x = self.stats_rect.left
        top_buttons_y = self.list_rect.top
        BUTTON_PAD = 8
        main_button_width = int(left_two_width * 0.7)
        arrow_width = int((left_two_width - main_button_width - 2 * BUTTON_PAD) / 2)

        self.left_game_arrow.rect = pygame.Rect(left_two_x, top_buttons_y, arrow_width, top_button_height)
        self.game_button.rect = pygame.Rect(left_two_x + arrow_width + BUTTON_PAD, top_buttons_y, main_button_width, top_button_height)
        self.right_game_arrow.rect = pygame.Rect(left_two_x + arrow_width + BUTTON_PAD + main_button_width + BUTTON_PAD, top_buttons_y, arrow_width, top_button_height)

        # Sprite sizes
        self.sel_height = max(64, self.sprite_rect.height // 2)
        self.sel_width = max(64, int(self.sprite_rect.width * 0.9))
        self.small_height = max(32, self.sel_height // 2)
        self.small_width = max(32, self.sel_width // 2)
        self.gap = max(-4, self.sel_height // -8)

        self.visible_items = max(1, self.list_rect.height // self.item_height)

    def center_left_columns_vertically(self):
        top = min(self.stats_rect.top, self.sprite_rect.top)
        bottom = max(self.stats_rect.bottom, self.sprite_rect.bottom)
        combined_height = bottom - top
        new_top = (self.screen_h - combined_height) // 2
        offset = new_top - top
        self.stats_rect.y += offset
        self.sprite_rect.y += offset

    # -----------------------
    # Sprite management
    # -----------------------
    def _load_and_presize_sprites(self):
        for i, p in enumerate(self.pokemon_data):
            poke_id = p.get('id', i + 1)
            path = os.path.join(SPRITE_FOLDER, f"{poke_id:03d}.png")
            img = pygame.image.load(path).convert_alpha() if os.path.exists(path) else None
            self.sprite_cache[i] = img

            if img:
                self.sprite_cache_full[i] = self._scale_preserve_aspect(img, self.sel_width, self.sel_height)
                self.sprite_cache_small[i] = self._scale_preserve_aspect(img, self.small_width, self.small_height)
            else:
                self.sprite_cache_full[i] = pygame.Surface((self.sel_width, self.sel_height), pygame.SRCALPHA)
                self.sprite_cache_small[i] = pygame.Surface((self.small_width, self.small_height), pygame.SRCALPHA)

    def _scale_preserve_aspect(self, surf_img, target_w, target_h):
        iw, ih = surf_img.get_size()
        if iw == 0 or ih == 0:
            return pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        ratio = min(target_w / iw, target_h / ih)
        return pygame.transform.smoothscale(surf_img, (max(1, int(iw*ratio)), max(1, int(ih*ratio))))

    def get_sprite(self, index):
        return self.sprite_cache[index] if 0 <= index < self.total else None

    def _load_pokedex_data(self):
        """Load seen/owned data from save data manager or combine from all saves"""
        self.seen_set = set()
        self.owned_set = set()
        
        # Combined mode - load from all save files (Sinew)
        if self.combined_mode and self.all_save_paths:
            self._load_combined_pokedex()
            return
        
        # Single save mode
        if self.save_data_manager and self.save_data_manager.is_loaded():
            try:
                # Use the save_data_manager's get_pokedex_data method
                pokedex = self.save_data_manager.get_pokedex_data()
                self.seen_set = set(pokedex.get('seen_list', []))
                self.owned_set = set(pokedex.get('owned_list', []))
                print(f"[PokedexModal] Loaded: {len(self.seen_set)} seen, {len(self.owned_set)} owned")
            except Exception as e:
                print(f"[PokedexModal] Error loading pokedex data: {e}")
    
    def _load_combined_pokedex(self):
        """Load and merge pokedex data from all save files (Sinew mode)"""
        from save_data_manager import get_cached_parser, precache_save
        
        # Reset per-game tracking
        self.per_game_owned = {}
        self.per_game_seen = {}
        
        for save_path in self.all_save_paths:
            if not save_path or not os.path.exists(save_path):
                continue
            
            try:
                # Extract game name from save path
                game_name = self._get_game_name_from_path(save_path)
                
                # Use cached parser if available
                parser = get_cached_parser(save_path)
                if not parser:
                    precache_save(save_path)
                    parser = get_cached_parser(save_path)
                
                if parser and parser.loaded:
                    pokedex = parser.get_pokedex()
                    seen_list = pokedex.get('seen_list', [])
                    owned_list = pokedex.get('owned_list', [])
                    
                    # Merge into combined sets
                    self.seen_set.update(seen_list)
                    self.owned_set.update(owned_list)
                    
                    # Track per-game ownership and seen
                    if game_name:
                        self.per_game_owned[game_name] = set(owned_list)
                        self.per_game_seen[game_name] = set(seen_list)
                        print(f"[PokedexModal] {game_name}: {len(seen_list)} seen, {len(owned_list)} owned")
            except Exception as e:
                print(f"[PokedexModal] Error loading {save_path}: {e}")
        
        print(f"[PokedexModal] Combined: {len(self.seen_set)} seen, {len(self.owned_set)} owned")
        print(f"[PokedexModal] Games with data: {list(self.per_game_owned.keys())}")
    
    def _get_game_name_from_path(self, save_path):
        """Extract game name from save file path"""
        if not save_path:
            return None
        
        # Get filename without extension
        filename = os.path.basename(save_path).lower()
        
        # Check for game keywords
        if "ruby" in filename and "omega" not in filename:
            return "Ruby"
        elif "sapphire" in filename and "alpha" not in filename:
            return "Sapphire"
        elif "emerald" in filename:
            return "Emerald"
        elif "firered" in filename or "fire red" in filename or "fire_red" in filename:
            return "FireRed"
        elif "leafgreen" in filename or "leaf green" in filename or "leaf_green" in filename:
            return "LeafGreen"
        
        return None
    
    def is_caught_in_all_games(self, pokemon_id):
        """Check if Pokemon is caught in all 5 games"""
        if not self.per_game_owned:
            return False
        
        # Must be caught in all 5 games (strict requirement)
        for game_name in GAME_NAMES:
            if game_name not in self.per_game_owned:
                return False  # Missing save data for this game
            if pokemon_id not in self.per_game_owned[game_name]:
                return False  # Not caught in this game
        
        return True
    
    def is_seen_in_all_games(self, pokemon_id):
        """Check if Pokemon is seen in all 5 games"""
        if not self.per_game_seen:
            return False
        
        # Must be seen in all 5 games (strict requirement)
        for game_name in GAME_NAMES:
            if game_name not in self.per_game_seen:
                return False  # Missing save data for this game
            if pokemon_id not in self.per_game_seen[game_name]:
                return False  # Not seen in this game
        
        return True
    
    def get_games_with_pokemon(self, pokemon_id):
        """Get list of game names where this Pokemon is caught"""
        games = []
        for game_name in GAME_NAMES:
            if game_name in self.per_game_owned:
                if pokemon_id in self.per_game_owned[game_name]:
                    games.append(game_name)
        return games
    
    def get_games_where_seen(self, pokemon_id):
        """Get list of game names where this Pokemon is seen (but not caught)"""
        games = []
        for game_name in GAME_NAMES:
            if game_name in self.per_game_seen:
                # Seen but NOT caught in this game
                is_seen = pokemon_id in self.per_game_seen[game_name]
                is_caught = game_name in self.per_game_owned and pokemon_id in self.per_game_owned[game_name]
                if is_seen and not is_caught:
                    games.append(game_name)
        return games

    def is_pokemon_seen(self, national_dex_num):
        """Check if Pokemon has been seen"""
        return national_dex_num in self.seen_set

    def is_pokemon_owned(self, national_dex_num):
        """Check if Pokemon has been caught/owned"""
        return national_dex_num in self.owned_set

    # ------------------- Game Navigation -------------------
    def change_game(self, direction):
        """Change to prev/next game using callbacks"""
        old_game = self.get_current_game()
        
        if direction == -1 and self.prev_game_callback:
            self.prev_game_callback()
        elif direction == 1 and self.next_game_callback:
            self.next_game_callback()
        
        new_game = self.get_current_game()
        self.update_game_button_text()
        
        # Check if we switched to/from Sinew (combined mode)
        is_now_sinew = (new_game == "Sinew")
        was_sinew = self.combined_mode
        
        if is_now_sinew and not was_sinew:
            # Switched TO Sinew - enable combined mode
            print(f"[PokedexModal] Switching to combined mode (Sinew)")
            self.combined_mode = True
            self.refresh_data()
        elif not is_now_sinew and was_sinew:
            # Switched FROM Sinew to a game - disable combined mode
            print(f"[PokedexModal] Switching from combined mode to {new_game}")
            self.combined_mode = False
            from save_data_manager import get_manager
            self.save_data_manager = get_manager()
            self.refresh_data()
        elif not is_now_sinew and new_game != old_game:
            # Switched between games (not Sinew)
            print(f"[PokedexModal] Switching from {old_game} to {new_game}")
            from save_data_manager import get_manager
            self.save_data_manager = get_manager()
            self.refresh_data()


    def refresh_data(self):
        """Reload or reset Pokedex data after changing game/save"""
        self.selected_index = 0
        self.list_scroll = 0
        self._load_pokedex_data()

    def get_current_game(self):
        """Return current game name via callback"""
        if self.get_current_game_callback:
            return self.get_current_game_callback()
        return "Unknown"
    def _get_regional_label(self):
        """Return correct regional dex label based on current game"""
        game = self.get_current_game()
        if game in ("FireRed", "LeafGreen"):
            return "Kanto"
        return "Hoenn"
    def _get_regional_dex_range(self):
        """Return (label, min_id, max_id) for the current game's regional dex"""
        game = self.get_current_game()

        if game in ("FireRed", "LeafGreen"):
            return "Kanto", 1, 151

        # Ruby / Sapphire / Emerald
        return "Hoenn", 1, 202

    def update_game_button_text(self):
        self.game_button.text = self.get_current_game()

    # -----------------------
    # Mouse input handling
    # -----------------------
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.left_game_arrow.rect.collidepoint(event.pos):
                self.change_game(-1)
            elif self.right_game_arrow.rect.collidepoint(event.pos):
                self.change_game(1)
            elif self.game_button.rect.collidepoint(event.pos):
                print(f"Current game: {self.get_current_game()}")

    # -----------------------
    # Controller handling
    # -----------------------
    def handle_controller(self, ctrl=None):
        if ctrl is None:
            return False
        consumed = False

        # Handle detail view first
        if self.showing_detail:
            if ctrl.is_button_just_pressed("B") or ctrl.is_button_just_pressed("A"):
                ctrl.consume_button("B")
                ctrl.consume_button("A")
                self.showing_detail = False
                return True
            # Up/Down navigation in detail view - skip to next/prev SEEN pokemon
            if ctrl.is_dpad_just_pressed("up"):
                ctrl.consume_dpad("up")
                self._move_to_prev_seen()
                return True
            if ctrl.is_dpad_just_pressed("down"):
                ctrl.consume_dpad("down")
                self._move_to_next_seen()
                return True
            return True  # Consume all other input while in detail view

        # Close modal (only when not in detail view)
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.open = False
            if self.close_callback:
                self.close_callback()
            if self.parent:
                self.parent.sub_modal = None
            return True

        # Focus navigation
        if self.focus_mode == 'list':
            if ctrl.is_dpad_just_pressed("up"):
                ctrl.consume_dpad("up"); self.move_selection(-1); consumed = True
            if ctrl.is_dpad_just_pressed("down"):
                ctrl.consume_dpad("down"); self.move_selection(1); consumed = True
            if ctrl.is_button_just_pressed("L"):
                ctrl.consume_button("L"); self.move_selection(-10); consumed = True
            if ctrl.is_button_just_pressed("R"):
                ctrl.consume_button("R"); self.move_selection(10); consumed = True
            if ctrl.is_dpad_just_pressed("left"):
                ctrl.consume_dpad("left")
                self.focus_mode = 'game_button'
                consumed = True
            # A button opens detail view for seen Pokemon
            if ctrl.is_button_just_pressed("A"):
                ctrl.consume_button("A")
                poke_id = self.pokemon_data[self.selected_index].get('id', self.selected_index + 1)
                if self.is_pokemon_seen(poke_id):
                    self.showing_detail = True
                consumed = True

        elif self.focus_mode == 'game_button':
            consumed |= self._handle_game_button_controller(ctrl)

        return consumed

    def _handle_game_button_controller(self, ctrl):
        consumed = False

        # Change saves
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            self.change_game(-1)
            consumed = True
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            self.change_game(1)
            consumed = True

        # Activate game button
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            print(f"Current game: {self.get_current_game()}")
            consumed = True

        # Allow leaving button focus
        if ctrl.is_dpad_just_pressed('down') or ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('down')
            ctrl.consume_dpad('up')
            self.focus_mode = 'list'
            consumed = True

        return consumed

    # -----------------------
    # Selection and scrolling
    # -----------------------
    def move_selection(self, delta):
        self.selected_index = max(0, min(self.total-1, self.selected_index + delta))
        self.update_scroll()
    
    def _move_to_next_seen(self):
        """Move to next seen Pokemon (for detail view navigation)"""
        start = self.selected_index
        for i in range(1, self.total):
            next_idx = (start + i) % self.total
            poke_id = self.pokemon_data[next_idx].get('id', next_idx + 1)
            if self.is_pokemon_seen(poke_id):
                self.selected_index = next_idx
                self.update_scroll()
                return
    
    def _move_to_prev_seen(self):
        """Move to previous seen Pokemon (for detail view navigation)"""
        start = self.selected_index
        for i in range(1, self.total):
            prev_idx = (start - i) % self.total
            poke_id = self.pokemon_data[prev_idx].get('id', prev_idx + 1)
            if self.is_pokemon_seen(poke_id):
                self.selected_index = prev_idx
                self.update_scroll()
                return

    def update_scroll(self):
        self.visible_items = max(1, self.list_rect.height // self.item_height)
        center_slot = self.visible_items // 2
        scroll = self.selected_index - center_slot
        scroll = max(0, min(scroll, max(0, self.total - self.visible_items)))
        self.list_scroll = scroll

    # -----------------------
    # Rendering
    # -----------------------
    def draw_text(self, surf, text, pos, align="topleft", font=None, color=ui_colors.COLOR_TEXT):
        f = font or self.font
        rtext = f.render(str(text), True, color)
        rect = rtext.get_rect()
        setattr(rect, align, pos)
        surf.blit(rtext, rect)
        return rect

    def render(self, surf):
        surf.fill(ui_colors.COLOR_BG)

        # Draw top buttons
        button_bg = ui_colors.COLOR_BUTTON_HOVER if self.focus_mode == "game_button" else ui_colors.COLOR_BUTTON

        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, self.left_game_arrow.rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.left_game_arrow.rect, 2)
        self.draw_text(surf, "<", self.left_game_arrow.rect.center, align="center")

        pygame.draw.rect(surf, button_bg, self.game_button.rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.game_button.rect, 2)
        self.draw_text(surf, self.game_button.text, self.game_button.rect.center, align="center")

        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, self.right_game_arrow.rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.right_game_arrow.rect, 2)
        self.draw_text(surf, ">", self.right_game_arrow.rect.center, align="center")

        if self.focus_mode == "game_button":
            highlight_rect = self.game_button.rect.inflate(4, 4)
            pygame.draw.rect(surf, (0, 255, 255), highlight_rect, 3)

        # Stats column
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, self.stats_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.stats_rect, 2)
        pad = 4
        left_x = self.stats_rect.left + pad
        right_x = self.stats_rect.right - pad
        y = self.stats_rect.top + pad

        self.draw_text(surf, "SEEN", (self.stats_rect.centerx, y), align="midtop")
        y += self.item_height

        def draw_label_value(label, value, y_pos):
            self.draw_text(surf, label, (left_x, y_pos + self.item_height // 2), align="midleft")
            self.draw_text(surf, str(value), (right_x, y_pos + self.item_height // 2), align="midright")

        # Calculate actual seen/owned counts
        # Regional dex depends on game (Hoenn or Kanto)
        regional_label, regional_min, regional_max = self._get_regional_dex_range()

        regional_seen = sum(1 for dex in self.seen_set if regional_min <= dex <= regional_max)
        regional_own = sum(1 for dex in self.owned_set if regional_min <= dex <= regional_max)

        national_seen = len(self.seen_set)
        national_own = len(self.owned_set)

        regional_label = self._get_regional_label() + ":"

        draw_label_value(f"{regional_label}:", regional_seen, y); y += self.item_height
        draw_label_value("National:", national_seen, y); y += self.item_height + (self.item_height // 2)

        self.draw_text(surf, "OWN", (self.stats_rect.centerx, y), align="midtop")
        y += self.item_height

        draw_label_value(f"{regional_label}:", regional_own, y); y += self.item_height
        draw_label_value("National:", national_own, y); y += self.item_height


        # Game icons section (combined mode only)
        if self.combined_mode and self.game_icons:
            # Get current Pokemon ID for ownership check
            poke = self.pokemon_data[self.selected_index]
            current_poke_id = poke.get('id', self.selected_index + 1)
            games_with_pokemon = self.get_games_with_pokemon(current_poke_id)
            games_where_seen = self.get_games_where_seen(current_poke_id)
            
            # Add spacing before icons
            y += self.item_height // 2
            
            # Calculate icon layout - 5 icons in a row
            icon_size = min(self.game_icon_size, (self.stats_rect.width - 20) // 5 - 4)
            icon_spacing = icon_size + 4
            total_width = len(GAME_NAMES) * icon_spacing - 4
            start_x = self.stats_rect.centerx - total_width // 2
            
            for i, game_name in enumerate(GAME_NAMES):
                icon_x = start_x + i * icon_spacing + icon_size // 2
                
                if game_name in self.game_icons:
                    icon = self.game_icons[game_name]
                    # Use smoothscale for game icons (they look better anti-aliased)
                    scaled_icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
                    
                    # Dim if no save data for this game
                    if game_name not in self.per_game_owned:
                        scaled_icon.set_alpha(60)
                    
                    icon_rect = scaled_icon.get_rect(midtop=(icon_x, y))
                    surf.blit(scaled_icon, icon_rect)
                    
                    # Draw pokeball under icon if caught, or eye if seen but not caught
                    # Use same size as list icons
                    ball_y = y + icon_size + 2
                    if game_name in games_with_pokemon:
                        # Caught - show pokeball (full size)
                        ball_rect = self.pokeball_icon.get_rect(midtop=(icon_x, ball_y))
                        surf.blit(self.pokeball_icon, ball_rect)
                    elif game_name in games_where_seen and self.eye_icon:
                        # Seen but not caught - show eye (full size)
                        eye_rect = self.eye_icon.get_rect(midtop=(icon_x, ball_y))
                        surf.blit(self.eye_icon, eye_rect)

        # Sprite column
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, self.sprite_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.sprite_rect, 2)
        cx, cy = self.sprite_rect.center
        prev_idx, sel_idx, next_idx = self.selected_index-1, self.selected_index, self.selected_index+1

        def get_display_sprite(idx, cache, apply_seen_check=True):
            """Get sprite, applying silhouette if not seen"""
            if idx < 0 or idx >= self.total:
                return None
            sprite = cache[idx]
            if sprite is None:
                return None
            
            # Check if this Pokemon has been seen
            poke_id = self.pokemon_data[idx].get('id', idx + 1)
            is_seen = self.is_pokemon_seen(poke_id)
            
            if apply_seen_check and not is_seen:
                # Create silhouette (all black) for unseen Pokemon
                silhouette = sprite.copy()
                silhouette.fill((0, 0, 0), special_flags=pygame.BLEND_RGB_MIN)
                return silhouette
            return sprite.copy()

        if 0 <= prev_idx < self.total:
            s_prev = get_display_sprite(prev_idx, self.sprite_cache_small)
            if s_prev:
                s_prev.set_alpha(FADE_ALPHA)
                pr = s_prev.get_rect(center=(cx, cy - (self.sel_height//2 + self.small_height//2 + self.gap)))
                surf.blit(s_prev, pr)
        if 0 <= sel_idx < self.total:
            s_sel = get_display_sprite(sel_idx, self.sprite_cache_full)
            if s_sel:
                sr = s_sel.get_rect(center=(cx, cy))
                surf.blit(s_sel, sr)
        if 0 <= next_idx < self.total:
            s_next = get_display_sprite(next_idx, self.sprite_cache_small)
            if s_next:
                s_next.set_alpha(FADE_ALPHA)
                nr = s_next.get_rect(center=(cx, cy + (self.sel_height//2 + self.small_height//2 + self.gap)))
                surf.blit(s_next, nr)

        # Right list column
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, self.list_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.list_rect, 2)

        self.visible_items = max(1, self.list_rect.height // self.item_height)
        self.update_scroll()
        first_index, last_index = self.list_scroll, min(self.total, self.list_scroll + self.visible_items)
        center_slot = self.visible_items // 2
        selected_slot_y = self.list_rect.top + center_slot * self.item_height
        y_offset = selected_slot_y - (self.selected_index - first_index) * self.item_height

        prev_clip = surf.get_clip()
        surf.set_clip(self.list_rect)

        for i in range(first_index, last_index):
            item_rect = pygame.Rect(self.list_rect.left + pad, y_offset, self.list_rect.width - 2*pad, self.item_height)
            if i == self.selected_index and self.focus_mode == "list":
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON_HOVER, item_rect)
            poke = self.pokemon_data[i]
            poke_id = poke.get('id', i + 1)
            poke_name = poke.get('name', f"Pokemon {poke_id}")
            
            # Check seen/owned status
            is_seen = self.is_pokemon_seen(poke_id)
            is_owned = self.is_pokemon_owned(poke_id)
            
            # Display name or ??????? based on seen status
            if is_seen:
                text = f"#{poke_id:03d} {poke_name}"
            else:
                text = f"#{poke_id:03d} ???????"
            
            # Draw text on left
            text_x = item_rect.left + pad
            self.draw_text(surf, text, (text_x, item_rect.centery), align="midleft")
            
            # Draw status icon on the RIGHT side
            if self.combined_mode:
                # Combined/Sinew mode: masterball if caught in ALL 5, eye if seen in ALL 5
                if self.masterball_icon and self.is_caught_in_all_games(poke_id):
                    icon_rect = self.masterball_icon.get_rect(midright=(item_rect.right - pad, item_rect.centery))
                    surf.blit(self.masterball_icon, icon_rect)
                elif self.eye_icon and self.is_seen_in_all_games(poke_id):
                    icon_rect = self.eye_icon.get_rect(midright=(item_rect.right - pad, item_rect.centery))
                    surf.blit(self.eye_icon, icon_rect)
            else:
                # Single game mode: pokeball if caught, eye if seen but not caught
                if is_owned and self.pokeball_icon:
                    icon_rect = self.pokeball_icon.get_rect(midright=(item_rect.right - pad, item_rect.centery))
                    surf.blit(self.pokeball_icon, icon_rect)
                elif is_seen and not is_owned and self.eye_icon:
                    icon_rect = self.eye_icon.get_rect(midright=(item_rect.right - pad, item_rect.centery))
                    surf.blit(self.eye_icon, icon_rect)
            
            y_offset += self.item_height

        surf.set_clip(prev_clip)
        
        # Draw detail overlay if showing
        if self.showing_detail:
            self._draw_detail_view(surf)
    
    def _draw_detail_view(self, surf):
        """Draw Pokemon detail overlay - centered quadrant layout"""
        poke = self.pokemon_data[self.selected_index]
        poke_id = poke.get('id', self.selected_index + 1)
        poke_name = poke.get('name', f"Pokemon {poke_id}")
        
        # Check if owned (only show full details if caught)
        is_owned = self.is_pokemon_owned(poke_id)
        
        # Use the actual surface size, not display size
        surf_w, surf_h = surf.get_size()
        
        # Semi-transparent overlay
        overlay = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))
        
        # Detail box - fit within surface with margins
        margin_x = 8
        margin_y = 4
        box_w = surf_w - margin_x * 2
        box_h = surf_h - margin_y * 2
        box_x = margin_x
        box_y = margin_y
        
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, (box_x, box_y, box_w, box_h))
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, (box_x, box_y, box_w, box_h), 2)
        
        center_x = box_x + box_w // 2
        
        # ===== TOP SECTION - Sprite =====
        sprite = self.sprite_cache_full[self.selected_index]
        sprite_y = box_y + int(box_h * 0.18)
        if sprite:
            # Scale sprite relative to box size (max ~22% of box height)
            orig_w, orig_h = sprite.get_size()
            max_sprite_size = int(box_h * 0.22)
            scale_factor = min(max_sprite_size / orig_w, max_sprite_size / orig_h)
            new_w, new_h = int(orig_w * scale_factor), int(orig_h * scale_factor)
            scaled_sprite = pygame.transform.scale(sprite, (new_w, new_h))
            sprite_rect = scaled_sprite.get_rect(center=(center_x, sprite_y))
            surf.blit(scaled_sprite, sprite_rect)
        
        # ===== NAME (centered below sprite) =====
        title = f"#{poke_id:03d} {poke_name}"
        name_y = sprite_y + int(box_h * 0.13)
        self.draw_text(surf, title, (center_x, name_y), align="midtop", font=self.title_font)
        
        # ===== STATS ROW - HT/WT centered in left half, Type centered in right half =====
        stats_y = name_y + int(box_h * 0.07)
        left_quarter_x = box_x + box_w // 4  # Center of left half
        right_quarter_x = box_x + (box_w * 3) // 4  # Center of right half
        
        # Height & Weight (stacked, aligned, centered in left half)
        if is_owned:
            height = poke.get('height', '???')
            if isinstance(height, (int, float)):
                height = f"{height/10:.1f} m"
            weight = poke.get('weight', '???')
            if isinstance(weight, (int, float)):
                weight = f"{weight/10:.1f} kg"
        else:
            height = "????"
            weight = "????"
        
        # Draw HT and WT with aligned colons - scale offset based on box width
        label_offset = int(box_w * 0.06)
        line_spacing = int(box_h * 0.045)
        
        self.draw_text(surf, "HT:", (left_quarter_x - label_offset, stats_y), align="midtop")
        self.draw_text(surf, height, (left_quarter_x + label_offset, stats_y), align="midtop")
        self.draw_text(surf, "WT:", (left_quarter_x - label_offset, stats_y + line_spacing), align="midtop")
        self.draw_text(surf, weight, (left_quarter_x + label_offset, stats_y + line_spacing), align="midtop")
        
        # Type (centered in right half, moved down to align better)
        if is_owned:
            types = poke.get('types', poke.get('type', []))
            if isinstance(types, list) and types:
                type_str = "/".join(str(t).capitalize() for t in types)
            elif isinstance(types, str):
                type_str = types.capitalize()
            else:
                type_str = "???"
        else:
            type_str = "????"
        self.draw_text(surf, f"Type: {type_str}", (right_quarter_x, stats_y + line_spacing // 2), align="midtop")
        
        # ===== DESCRIPTION (middle section) =====
        desc_y_start = stats_y + line_spacing * 2 + int(box_h * 0.06)
        desc_line_height = int(box_h * 0.05)
        
        if is_owned:
            desc = poke.get('description', poke.get('flavor_text', ''))
            if desc:
                desc_lines = self._wrap_text(desc, box_w - 20)
                desc_y = desc_y_start
                for line in desc_lines[:3]:
                    self.draw_text(surf, line, (center_x, desc_y), align="midtop")
                    desc_y += desc_line_height
        else:
            # Show placeholder for unseen data
            self.draw_text(surf, "Catch this Pokemon to", (center_x, desc_y_start), align="midtop")
            self.draw_text(surf, "see more information.", (center_x, desc_y_start + desc_line_height), align="midtop")
        
        # ===== GAME ICONS at bottom (combined mode only) =====
        if self.combined_mode and self.game_icons:
            # Position icons above the navigation hint
            pokeball_height = self.pokeball_icon.get_height() if self.pokeball_icon else 16
            games_y = box_y + box_h - int(box_h * 0.12) - self.game_icon_size - pokeball_height - 4
            
            # Calculate total width of all icons
            icon_spacing = self.game_icon_size + 8
            total_icons = len(GAME_NAMES)
            total_width = total_icons * icon_spacing - 8
            start_x = center_x - total_width // 2
            
            # Get which games have this Pokemon caught/seen
            games_with_pokemon = self.get_games_with_pokemon(poke_id)
            games_where_seen = self.get_games_where_seen(poke_id)
            
            for i, game_name in enumerate(GAME_NAMES):
                icon_x = start_x + i * icon_spacing
                
                # Draw game icon (dimmed if not in that game's dex)
                if game_name in self.game_icons:
                    icon = self.game_icons[game_name]
                    
                    # Dim the icon if we don't have save data for this game
                    if game_name not in self.per_game_owned:
                        # Create dimmed version
                        dimmed = icon.copy()
                        dimmed.set_alpha(80)
                        icon_rect = dimmed.get_rect(midtop=(icon_x, games_y))
                        surf.blit(dimmed, icon_rect)
                    else:
                        icon_rect = icon.get_rect(midtop=(icon_x, games_y))
                        surf.blit(icon, icon_rect)
                    
                    # Draw pokeball under icon if caught, or eye if seen but not caught
                    ball_y = games_y + self.game_icon_size + 2
                    if game_name in games_with_pokemon:
                        # Caught - show pokeball (full size)
                        ball_rect = self.pokeball_icon.get_rect(midtop=(icon_x, ball_y))
                        surf.blit(self.pokeball_icon, ball_rect)
                    elif game_name in games_where_seen and self.eye_icon:
                        # Seen but not caught - show eye (full size)
                        eye_rect = self.eye_icon.get_rect(midtop=(icon_x, ball_y))
                        surf.blit(self.eye_icon, eye_rect)
        
        # ===== NAVIGATION HINT (bottom) =====
        hint = "Up/Down: Navigate  B: Close"
        self.draw_text(surf, hint, (center_x, box_y + box_h - int(box_h * 0.02)), 
                      align="midbottom", color=(120, 120, 120))
    
    def _wrap_text(self, text, max_width):
        """Simple word wrap for description text"""
        words = text.replace('\n', ' ').replace('\f', ' ').split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_surf = self.font.render(test_line, True, ui_colors.COLOR_TEXT)
            if test_surf.get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        return lines

    def draw(self, surf):
        self.render(surf)