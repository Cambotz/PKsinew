"""
Pokemon Summary Screen - Emerald Style
3 tabs: Info (with stats), Moves, Contest (RSE only)
"""

import json
import os

import pygame

# Import config for paths
try:
    import config

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

try:
    import ui_colors
except ImportError:
    # Fallback module with default colors
    class ui_colors:
        COLOR_BG = (30, 30, 30)
        COLOR_TEXT = (255, 255, 255)
        COLOR_BUTTON = (60, 60, 60)
        COLOR_BORDER = (200, 200, 200)
        COLOR_HIGHLIGHT = (100, 100, 255)


# Pokemon type colors
TYPE_COLORS = {
    "normal": (168, 168, 120),
    "fire": (240, 128, 48),
    "water": (104, 144, 240),
    "electric": (248, 208, 48),
    "grass": (120, 200, 80),
    "ice": (152, 216, 216),
    "fighting": (192, 48, 40),
    "poison": (160, 64, 160),
    "ground": (224, 192, 104),
    "flying": (168, 144, 240),
    "psychic": (248, 88, 136),
    "bug": (168, 184, 32),
    "rock": (184, 160, 56),
    "ghost": (112, 88, 152),
    "dragon": (112, 56, 248),
    "dark": (112, 88, 72),
    "steel": (184, 184, 208),
    "fairy": (238, 153, 172),
}

# Import move data
try:
    from move_data import get_move_info, get_move_name

    MOVE_DATA_AVAILABLE = True
except ImportError:
    MOVE_DATA_AVAILABLE = False

    def get_move_name(move_id):
        return f"Move #{move_id}" if move_id > 0 else "---"

    def get_move_info(move_id):
        return (get_move_name(move_id), "normal", 0, 0, 0)


# Import ability data
try:
    from ability_data import (
        get_ability_description,
        get_ability_name,
        get_pokemon_abilities,
        get_pokemon_ability_id,
        get_pokemon_ability_name,
    )

    ABILITY_DATA_AVAILABLE = True
except ImportError:
    ABILITY_DATA_AVAILABLE = False

    def get_ability_name(ability_id):
        return f"Ability #{ability_id}"

    def get_pokemon_ability_name(species_id, ability_bit):
        return "Slot 2" if ability_bit else "Slot 1"

    def get_pokemon_abilities(species_id):
        return (0, None)

    def get_ability_description(ability_id):
        return ""

    def get_pokemon_ability_id(species_id, ability_bit):
        return 0


# Import location data
try:
    from location_data import get_location_name

    LOCATION_DATA_AVAILABLE = True
except ImportError:
    LOCATION_DATA_AVAILABLE = False

    def get_location_name(location_id, game_type="RSE"):
        return f"Location {location_id}"


# Import item data
try:
    from item_names import get_item_name

    ITEM_DATA_AVAILABLE = True
except ImportError:
    ITEM_DATA_AVAILABLE = False

    def get_item_name(item_id):
        return f"Item {item_id}" if item_id > 0 else "None"


def extract_missing_data(pokemon):
    """
    Extract missing fields (met_location, contest_stats) from raw_bytes if available.
    Gen3 Pokemon structure uses encrypted 48-byte substructure with 4 blocks.

    Args:
        pokemon: Pokemon dict that may have raw_bytes

    Returns:
        dict: Updated pokemon dict with extracted data
    """
    if not pokemon or pokemon.get("empty"):
        return pokemon

    raw_bytes = pokemon.get("raw_bytes")
    if not raw_bytes or len(raw_bytes) < 80:
        return pokemon

    try:
        import struct

        # Get personality value and OT ID for decryption
        personality = struct.unpack("<I", raw_bytes[0:4])[0]
        ot_id = struct.unpack("<I", raw_bytes[4:8])[0]

        # Decrypt the 48-byte substructure
        encrypted = raw_bytes[32:80]
        decryption_key = personality ^ ot_id

        decrypted = bytearray(48)
        for i in range(0, 48, 4):
            chunk = struct.unpack("<I", encrypted[i : i + 4])[0]
            decrypted[i : i + 4] = struct.pack("<I", chunk ^ decryption_key)

        # Determine block order from personality value
        ORDER = [
            [0, 1, 2, 3],
            [0, 1, 3, 2],
            [0, 2, 1, 3],
            [0, 3, 1, 2],
            [0, 2, 3, 1],
            [0, 3, 2, 1],
            [1, 0, 2, 3],
            [1, 0, 3, 2],
            [2, 0, 1, 3],
            [3, 0, 1, 2],
            [2, 0, 3, 1],
            [3, 0, 2, 1],
            [1, 2, 0, 3],
            [1, 3, 0, 2],
            [2, 1, 0, 3],
            [3, 1, 0, 2],
            [2, 3, 0, 1],
            [3, 2, 0, 1],
            [1, 2, 3, 0],
            [1, 3, 2, 0],
            [2, 1, 3, 0],
            [3, 1, 2, 0],
            [2, 3, 1, 0],
            [3, 2, 1, 0],
        ]

        order_idx = personality % 24
        order = ORDER[order_idx]

        # Find block positions (each block is 12 bytes)
        # Block types: 0=Growth, 1=Attacks, 2=EVs, 3=Misc
        evs_pos = order.index(2) * 12
        misc_pos = order.index(3) * 12

        # Extract contest stats from EVs block (bytes 6-11)
        if not pokemon.get("contest_stats"):
            pokemon["contest_stats"] = {
                "cool": decrypted[evs_pos + 6],
                "beauty": decrypted[evs_pos + 7],
                "cute": decrypted[evs_pos + 8],
                "smart": decrypted[evs_pos + 9],
                "tough": decrypted[evs_pos + 10],
                "sheen": decrypted[evs_pos + 11],
            }

        # Extract met location from Misc block (byte 1)
        if not pokemon.get("met_location") or pokemon.get("met_location") == 0:
            pokemon["met_location"] = decrypted[misc_pos + 1]

        # Extract origins info from Misc block (bytes 2-3)
        origins = struct.unpack("<H", decrypted[misc_pos + 2 : misc_pos + 4])[0]
        if not pokemon.get("met_level"):
            pokemon["met_level"] = origins & 0x7F  # bits 0-6

    except Exception as e:
        # If extraction fails, just return pokemon as-is
        print(f"[PokemonSummary] Could not extract data from raw_bytes: {e}")

    return pokemon


# Base stats cache (loaded from pokemon_db.json)
_base_stats_cache = {}


def _load_base_stats():
    """Load base stats from pokemon_db.json"""
    if _base_stats_cache:
        return

    # Use config for path if available
    if CONFIG_AVAILABLE and hasattr(config, "POKEMON_DB_PATH"):
        db_path = config.POKEMON_DB_PATH
    elif CONFIG_AVAILABLE and hasattr(config, "BASE_DIR"):
        db_path = os.path.join(config.BASE_DIR, "data", "pokemon_db.json")
    else:
        db_path = "data/pokemon_db.json"

    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for value in data.items():
                if isinstance(value, dict) and "id" in value and "stats" in value:
                    _base_stats_cache[value["id"]] = value["stats"]
        except Exception as e:
            print(f"[PokemonSummary] Failed to load base stats: {e}")


def get_base_stats(species_id):
    """Get base stats for a species"""
    _load_base_stats()
    return _base_stats_cache.get(species_id, {})


def calculate_hp(base_hp, iv_hp, ev_hp, level):
    """
    Calculate HP stat using Gen 3 formula.
    HP = floor(((IV * 2 + Base + floor(EV/4)) * Level) / 100) + Level + 10
    """
    if base_hp == 0:
        return 1
    hp = ((iv_hp + 2 * base_hp + (ev_hp // 4)) * level) // 100 + level + 10
    return max(1, hp)


def calculate_stat(base, iv, ev, level, nature_multiplier=1.0):
    """
    Calculate a non-HP stat using Gen 3 formula.
    Stat = floor((floor(((IV * 2 + Base + floor(EV/4)) * Level) / 100) + 5) * Nature)
    """
    if base == 0:
        return 1
    stat = ((iv + 2 * base + (ev // 4)) * level) // 100 + 5
    stat = int(stat * nature_multiplier)
    return max(1, stat)


# Nature stat effects (+10% / -10%)
NATURE_EFFECTS = {
    "hardy": (None, None),
    "lonely": ("attack", "defense"),
    "brave": ("attack", "speed"),
    "adamant": ("attack", "sp_attack"),
    "naughty": ("attack", "sp_defense"),
    "bold": ("defense", "attack"),
    "docile": (None, None),
    "relaxed": ("defense", "speed"),
    "impish": ("defense", "sp_attack"),
    "lax": ("defense", "sp_defense"),
    "timid": ("speed", "attack"),
    "hasty": ("speed", "defense"),
    "serious": (None, None),
    "jolly": ("speed", "sp_attack"),
    "naive": ("speed", "sp_defense"),
    "modest": ("sp_attack", "attack"),
    "mild": ("sp_attack", "defense"),
    "quiet": ("sp_attack", "speed"),
    "bashful": (None, None),
    "rash": ("sp_attack", "sp_defense"),
    "calm": ("sp_defense", "attack"),
    "gentle": ("sp_defense", "defense"),
    "sassy": ("sp_defense", "speed"),
    "careful": ("sp_defense", "sp_attack"),
    "quirky": (None, None),
}

# Move data - basic Gen 3 moves (we'd need a full database for this)
# For now, just display move IDs and what info we have
MOVE_NAMES = {}  # Will be loaded from file if available


class PokemonOptionsMenu:
    """Popup menu when selecting a Pokemon (Summary, Move, etc.)"""

    def __init__(
        self,
        pokemon,
        x,
        y,
        font,
        close_callback,
        summary_callback=None,
        move_callback=None,
        item_callback=None,
        game_type="RSE",
    ):
        self.pokemon = pokemon
        self.x = x
        self.y = y
        self.font = font
        self.close_callback = close_callback
        self.summary_callback = summary_callback
        self.move_callback = move_callback
        self.item_callback = item_callback
        self.game_type = game_type

        # Menu options
        self.options = ["SUMMARY", "MOVE", "ITEM", "CANCEL"]
        self.selected_index = 0

        # Calculate size
        self.item_height = 28
        self.width = 120
        self.height = len(self.options) * self.item_height + 16

        # Adjust position to stay on screen
        self.rect = pygame.Rect(x, y, self.width, self.height)

    def handle_controller(self, ctrl):
        """Handle controller input"""
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.close_callback()
            return True

        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            self.selected_index = (self.selected_index - 1) % len(self.options)
            return True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            self.selected_index = (self.selected_index + 1) % len(self.options)
            return True

        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            self._select_option()
            return True

        return False

    def _select_option(self):
        """Execute the selected option"""
        option = self.options[self.selected_index]

        if option == "SUMMARY" and self.summary_callback:
            self.summary_callback(self.pokemon)
        elif option == "MOVE" and self.move_callback:
            self.move_callback(self.pokemon)
        elif option == "ITEM" and self.item_callback:
            self.item_callback(self.pokemon)
        elif option == "CANCEL":
            self.close_callback()
        else:
            self.close_callback()

    def draw(self, surf):
        """Draw the options menu"""
        # Background
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, self.rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.rect, 2)

        # Draw options
        for i, option in enumerate(self.options):
            y = self.rect.top + 8 + i * self.item_height

            # Highlight selected
            if i == self.selected_index:
                highlight_rect = pygame.Rect(
                    self.rect.left + 4, y - 2, self.width - 8, self.item_height - 4
                )
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect)

            # Draw text
            text_surf = self.font.render(option, True, ui_colors.COLOR_TEXT)
            text_rect = text_surf.get_rect(
                midleft=(self.rect.left + 12, y + self.item_height // 2 - 2)
            )
            surf.blit(text_surf, text_rect)


class PokemonSummary:
    """
    Pokemon Summary Screen with 3 tabs (Emerald style)
    - INFO: Pokemon info + stats combined
    - MOVES: Battle moves
    - CONTEST: Contest moves (RSE only, hidden for FRLG)
    """

    TAB_INFO = 0
    TAB_MOVES = 1
    TAB_CONTEST = 2

    def __init__(
        self,
        pokemon,
        width,
        height,
        font,
        close_callback,
        manager=None,
        game_type="RSE",
        prev_pokemon_callback=None,
        next_pokemon_callback=None,
    ):
        # Extract any missing data from raw_bytes (met_location, contest_stats)
        self.pokemon = extract_missing_data(pokemon.copy() if pokemon else pokemon)
        self.width = width
        self.height = height
        self.font = font
        self.close_callback = close_callback
        self.manager = manager
        self.game_type = game_type  # 'RSE' or 'FRLG'
        self.prev_pokemon_callback = prev_pokemon_callback
        self.next_pokemon_callback = next_pokemon_callback

        # Current tab
        self.current_tab = self.TAB_INFO

        # Tab names - 3 tabs now (INFO combines with SKILLS)
        if game_type == "FRLG":
            self.tabs = ["INFO", "MOVES"]
        else:
            self.tabs = ["INFO", "MOVES", "CONTEST"]

        # Font sizes for refresh
        self.small_font_size = 12
        self.title_font_size = 14

        # Initialize fonts
        self._refresh_fonts()

        # Load sprite
        self.sprite = None
        self._load_sprite()

        # Calculate layout
        self.tab_height = 30
        self.content_rect = pygame.Rect(
            0, self.tab_height, width, height - self.tab_height
        )

    def _refresh_fonts(self):
        """Refresh fonts using current theme settings"""
        self.small_font = ui_colors.get_font(self.small_font_size)
        self.title_font = ui_colors.get_font(self.title_font_size)

    def _load_sprite(self):
        """Load Pokemon sprite - try multiple sources"""
        self.sprite = None

        if not self.pokemon:
            return

        # Method 1: Use manager's get_gen3_sprite_path
        if self.manager:
            try:
                sprite_path = self.manager.get_gen3_sprite_path(self.pokemon)
                print(
                    f"[DEBUG] _load_sprite: manager.get_gen3_sprite_path returned {sprite_path} for pokemon {self.pokemon}"
                )
                if sprite_path and os.path.exists(sprite_path):
                    self.sprite = pygame.image.load(sprite_path).convert_alpha()
                    self.sprite = pygame.transform.scale(self.sprite, (96, 96))
                    return
            except Exception as e:
                print(f"[PokemonSummary] Manager sprite load failed: {e}")

        # Method 2: Try to load directly from species ID
        species = self.pokemon.get("species", 0)
        if not species:
            # Also try 'species_id' or 'national_dex'
            species = self.pokemon.get("species_id", 0) or self.pokemon.get(
                "national_dex", 0
            )

        if species and species > 0:
            sprite_paths = [config.get_sprite_path(species, sprite_type="gen3")]

            for path in sprite_paths:
                if os.path.exists(path):
                    try:
                        self.sprite = pygame.image.load(path).convert_alpha()
                        self.sprite = pygame.transform.scale(self.sprite, (96, 96))
                        return
                    except Exception:
                        pass

        # Method 3: Check if sprite was passed in pokemon data directly
        if self.pokemon.get("sprite"):
            try:
                sprite = self.pokemon.get("sprite")
                if isinstance(sprite, pygame.Surface):
                    self.sprite = pygame.transform.scale(sprite, (96, 96))
                    return
            except Exception:
                pass

        # Method 4: Try raw dict's sprite_path if available
        raw = self.pokemon.get("raw", {})
        if raw:
            species = raw.get("species", 0)
            if species and species > 0:
                # Use config if available
                if CONFIG_AVAILABLE and hasattr(config, "get_sprite_path"):
                    sprite_paths = [config.get_sprite_path(species, sprite_type="gen3")]
                elif CONFIG_AVAILABLE and hasattr(config, "GEN3_NORMAL_DIR"):
                    sprite_paths = [
                        os.path.join(config.GEN3_NORMAL_DIR, f"{species:03d}.png")
                    ]
                else:
                    sprite_paths = [
                        f"data/sprites/gen3/normal/{species:03d}.png",
                        f"data/sprites/gen3/normal/{species}.png",
                        f"data/sprites/gen3/{species}.png",
                    ]
                for path in sprite_paths:
                    if os.path.exists(path):
                        try:
                            self.sprite = pygame.image.load(path).convert_alpha()
                            self.sprite = pygame.transform.scale(self.sprite, (96, 96))
                            return
                        except Exception:
                            pass

        # Method 5: If all else fails, print debug info
        print(
            f"[PokemonSummary] Could not load sprite. Pokemon data keys: {list(self.pokemon.keys())}"
        )
        print(
            f"[PokemonSummary] Species value: {self.pokemon.get('species', 'MISSING')}"
        )

    def handle_controller(self, ctrl):
        """Handle controller input"""
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.close_callback()
            return True

        # Up/Down to switch Pokemon
        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            if self.prev_pokemon_callback:
                new_pokemon = self.prev_pokemon_callback()
                if new_pokemon:
                    self.set_pokemon(new_pokemon)
            return True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            if self.next_pokemon_callback:
                new_pokemon = self.next_pokemon_callback()
                if new_pokemon:
                    self.set_pokemon(new_pokemon)
            return True

        # Tab navigation with L/R or left/right
        if ctrl.is_button_just_pressed("L") or ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_button("L")
            ctrl.consume_dpad("left")
            self.current_tab = (self.current_tab - 1) % len(self.tabs)
            return True

        if ctrl.is_button_just_pressed("R") or ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_button("R")
            ctrl.consume_dpad("right")
            self.current_tab = (self.current_tab + 1) % len(self.tabs)
            return True

        return False

    def set_pokemon(self, pokemon):
        """Update the displayed Pokemon and reload sprite"""
        self.pokemon = extract_missing_data(pokemon.copy() if pokemon else pokemon)
        self._load_sprite()

    def draw(self, surf):
        """Draw the summary screen"""
        # Refresh fonts in case theme changed
        self._refresh_fonts()

        surf.fill(ui_colors.COLOR_BG)

        # Draw tabs
        self._draw_tabs(surf)

        # Draw content based on current tab
        if self.current_tab == self.TAB_INFO:
            self._draw_info_page(surf)
        elif self.current_tab == self.TAB_MOVES:
            self._draw_moves_page(surf)
        elif self.current_tab == self.TAB_CONTEST:
            self._draw_contest_page(surf)

        # Draw border
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, surf.get_rect(), 2)

    def _draw_tabs(self, surf):
        """Draw the tab bar"""
        tab_width = self.width // len(self.tabs)

        for i, tab_name in enumerate(self.tabs):
            x = i * tab_width
            rect = pygame.Rect(x, 0, tab_width, self.tab_height)

            # Highlight current tab
            if i == self.current_tab:
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, rect)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, rect)

            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, rect, 1)

            # Tab text
            text = self.small_font.render(tab_name, True, ui_colors.COLOR_TEXT)
            text_rect = text.get_rect(center=rect.center)
            surf.blit(text, text_rect)

    def _draw_info_page(self, surf):
        """Draw the INFO tab - combined Pokemon info and stats"""
        pad = 8
        y = self.tab_height + pad

        # Get Pokemon data
        species_id = self.pokemon.get("species", 0) or 0
        species_name = self.pokemon.get("species_name", "???")
        nickname = self.pokemon.get("nickname", "").strip()
        dex_num = species_id
        level = self.pokemon.get("level", 1) or 1

        display_name = (
            nickname if nickname and nickname != species_name else species_name
        )

        ivs = self.pokemon.get("ivs", {}) or {}
        evs = self.pokemon.get("evs", {}) or {}
        base_stats = get_base_stats(species_id)

        # ===== TOP ROW: Sprite + Basic Info (left) | OT/ID/ITEM/MET (right) =====
        # Sprite (left side)
        sprite_size = 80
        sprite_box = pygame.Rect(pad, y, sprite_size, sprite_size)
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, sprite_box)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, sprite_box, 1)

        if self.sprite:
            scaled_sprite = pygame.transform.scale(
                self.sprite, (sprite_size - 4, sprite_size - 4)
            )
            sprite_rect = scaled_sprite.get_rect(center=sprite_box.center)
            surf.blit(scaled_sprite, sprite_rect)

        # Basic info (middle - next to sprite)
        info_x = sprite_box.right + pad
        info_y = y

        # Name - BIGGER font
        name_text = self.font.render(
            display_name.upper()[:10], True, ui_colors.COLOR_TEXT
        )
        surf.blit(name_text, (info_x, info_y))

        # No. and Lv on same line
        info_y += 22
        dex_text = self.small_font.render(f"No.{dex_num:03d}", True, (180, 180, 180))
        level_text = self.small_font.render(f"Lv.{level}", True, ui_colors.COLOR_TEXT)
        surf.blit(dex_text, (info_x, info_y))
        surf.blit(level_text, (info_x + 55, info_y))

        # Nature
        info_y += 16
        nature = self.pokemon.get("nature", 0)
        personality = self.pokemon.get("personality", 0)
        if isinstance(nature, int):
            nature_names = [
                "Hardy",
                "Lonely",
                "Brave",
                "Adamant",
                "Naughty",
                "Bold",
                "Docile",
                "Relaxed",
                "Impish",
                "Lax",
                "Timid",
                "Hasty",
                "Serious",
                "Jolly",
                "Naive",
                "Modest",
                "Mild",
                "Quiet",
                "Bashful",
                "Rash",
                "Calm",
                "Gentle",
                "Sassy",
                "Careful",
                "Quirky",
            ]
            nature = nature_names[personality % 25]
        nature_text = self.small_font.render(f"{nature}", True, ui_colors.COLOR_TEXT)
        surf.blit(nature_text, (info_x, info_y))

        # EXP (below nature, next to sprite)
        info_y += 16
        exp = self.pokemon.get("experience", 0) or 0
        exp_str = str(exp) if exp < 100000 else f"{exp//1000}k"
        exp_text = self.small_font.render(f"EXP:{exp_str}", True, (180, 180, 180))
        surf.blit(exp_text, (info_x, info_y))

        # OT / ID / ITEM / MET (right column - at 66% across)
        right_col_x = int(self.width * 0.66)
        right_y = y

        ot_name = self.pokemon.get("ot_name", "???") or "???"
        # Gen 3 stores TID and SID as a combined 32-bit ot_id value
        # TID is lower 16 bits, SID is upper 16 bits
        ot_id = self.pokemon.get("ot_id", 0) or 0
        tid = ot_id & 0xFFFF  # Lower 16 bits
        sid = (ot_id >> 16) & 0xFFFF  # Upper 16 bits
        held_item = self.pokemon.get("held_item", 0) or 0
        met_location = self.pokemon.get("met_location", 0) or 0

        # OT
        ot_text = self.small_font.render(f"OT:{ot_name[:6]}", True, (180, 180, 180))
        surf.blit(ot_text, (right_col_x, right_y))
        right_y += 14

        # ID (TID/SID format for Gen 3)
        id_text = self.small_font.render(
            f"ID:{tid:05d}/{sid:05d}", True, (180, 180, 180)
        )
        surf.blit(id_text, (right_col_x, right_y))
        right_y += 14

        # Item (if held) - show name
        if held_item > 0:
            item_name = get_item_name(held_item)
            # Truncate long names
            if len(item_name) > 12:
                item_name = item_name[:11] + "."
            item_text = self.small_font.render(item_name, True, (180, 180, 180))
            surf.blit(item_text, (right_col_x, right_y))
        right_y += 14

        # Met location
        if self.pokemon.get("egg"):
            met_text = self.small_font.render("Egg", True, (180, 180, 180))
        elif met_location is not None:  # Changed from > 0 to handle location 0
            location_name = get_location_name(met_location, self.game_type)
            # Truncate long location names
            if len(location_name) > 12:
                location_name = location_name[:11] + "."
            met_text = self.small_font.render(location_name, True, (180, 180, 180))
        else:
            met_text = self.small_font.render("Unknown", True, (180, 180, 180))
        surf.blit(met_text, (right_col_x, right_y))

        y = sprite_box.bottom + pad

        # ===== HP BAR =====
        hp = self.pokemon.get("current_hp")
        max_hp = self.pokemon.get("max_hp")

        if max_hp is None or max_hp == 0:
            base_hp = base_stats.get("hp", 50)
            iv_hp = ivs.get("hp", 0) or 0
            ev_hp = evs.get("hp", 0) or 0
            max_hp = calculate_hp(base_hp, iv_hp, ev_hp, level)
            hp = max_hp

        if hp is None:
            hp = max_hp

        # HP label and value on same line ABOVE bar
        hp_label = self.small_font.render("HP", True, ui_colors.COLOR_TEXT)
        hp_value = self.small_font.render(f"{hp}/{max_hp}", True, ui_colors.COLOR_TEXT)
        surf.blit(hp_label, (pad, y))
        surf.blit(hp_value, (pad + 25, y))
        y += 16  # Move down for the bar

        # HP bar - fills from left to right, empties from right to left
        bar_width = self.width - pad * 2
        bar_height = 8
        bar_rect = pygame.Rect(pad, y, bar_width, bar_height)
        pygame.draw.rect(surf, (50, 50, 50), bar_rect)

        hp_ratio = hp / max_hp if max_hp > 0 else 1.0
        if hp_ratio > 0.5:
            hp_color = (0, 200, 0)
        elif hp_ratio > 0.2:
            hp_color = (255, 200, 0)
        else:
            hp_color = (255, 50, 50)

        # Fill from left side based on ratio
        fill_width = int(bar_width * hp_ratio)
        pygame.draw.rect(surf, hp_color, (pad, y, fill_width, bar_height))
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, bar_rect, 1)
        y += bar_height + 10

        # ===== STATS (Left column) | ABILITY (Right column) =====
        col1_x = pad
        col2_x = self.width // 2 + 10

        # All stats in left column - aligned
        stats_list = [
            ("attack", "ATK", "attack"),
            ("defense", "DEF", "defense"),
            ("sp_attack", "SP.A", "special-attack"),
            ("sp_defense", "SP.D", "special-defense"),
            ("speed", "SPD", "speed"),
        ]

        stat_val_x = col1_x + 45  # Aligned position for stat values
        iv_ev_x = col1_x + 80  # Aligned position for IV/EV

        stats_y = y
        for stat_key, stat_name, base_key in stats_list:
            iv = ivs.get(stat_key, 0) or 0
            ev = evs.get(stat_key, 0) or 0

            stat_val = self.pokemon.get(stat_key) or self.pokemon.get("stats", {}).get(
                stat_key, 0
            )
            if stat_val is None or stat_val == 0:
                base = base_stats.get(base_key, 50)
                stat_val = calculate_stat(base, iv, ev, level)

            # Stat name (left aligned)
            stat_label = self.small_font.render(
                f"{stat_name}:", True, ui_colors.COLOR_TEXT
            )
            surf.blit(stat_label, (col1_x, stats_y))

            # Stat value (right aligned to fixed position)
            stat_val_text = self.small_font.render(
                f"{stat_val:3d}", True, ui_colors.COLOR_TEXT
            )
            surf.blit(stat_val_text, (stat_val_x, stats_y))

            # IV/EV
            iv_ev_text = self.small_font.render(
                f"{iv:2d}/{ev:3d}", True, (120, 120, 120)
            )
            surf.blit(iv_ev_text, (iv_ev_x, stats_y))

            stats_y += 15

        # Right column: Ability with description
        right_y = y

        # Ability
        ability_bit = self.pokemon.get("ability_bit", 0) or 0
        ability_name = get_pokemon_ability_name(species_id, ability_bit)
        ability_id = get_pokemon_ability_id(species_id, ability_bit)
        ability_desc = get_ability_description(ability_id)

        ability_label = self.small_font.render("ABILITY:", True, (180, 180, 180))
        surf.blit(ability_label, (col2_x, right_y))
        right_y += 14

        ability_text = self.small_font.render(
            f"{ability_name}", True, ui_colors.COLOR_TEXT
        )
        surf.blit(ability_text, (col2_x, right_y))
        right_y += 16

        # Ability description - wrap if needed
        if ability_desc:
            # Split description into lines if too long
            max_desc_width = self.width - col2_x - pad
            words = ability_desc.split()
            lines = []
            current_line = ""

            for word in words:
                test_line = current_line + " " + word if current_line else word
                test_surf = self.small_font.render(test_line, True, (150, 150, 150))
                if test_surf.get_width() <= max_desc_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            # Draw description lines
            for line in lines[:2]:  # Max 2 lines
                desc_text = self.small_font.render(line, True, (150, 150, 150))
                surf.blit(desc_text, (col2_x, right_y))
                right_y += 13

    def _draw_moves_page(self, surf):
        """Draw the MOVES tab - battle moves"""
        pad = 12
        y = self.tab_height + pad

        # Get moves - can be list of IDs or list of dicts
        moves_raw = self.pokemon.get("moves", []) or []
        pp_raw = self.pokemon.get("pp", []) or []

        # Normalize to list of dicts with 'id' and 'pp'
        moves = []
        for i in range(4):
            if i < len(moves_raw):
                move_data = moves_raw[i]
                if isinstance(move_data, dict):
                    # Already a dict
                    moves.append(move_data)
                else:
                    # It's just an ID, get PP from pp list
                    pp_val = pp_raw[i] if i < len(pp_raw) else 0
                    moves.append({"id": move_data, "pp": pp_val})
            else:
                moves.append(None)

        # Draw title
        title = self.title_font.render("KNOWN MOVES", True, ui_colors.COLOR_TEXT)
        surf.blit(title, (pad, y))
        y += 24

        # Draw each move
        move_height = 50

        for i in range(4):
            move_rect = pygame.Rect(pad, y, self.width - pad * 2, move_height - 4)
            pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, move_rect)
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, move_rect, 1)

            move = moves[i]
            if move and move.get("id", 0) > 0:
                move_id = move.get("id", 0) or 0
                move_pp = move.get("pp", 0) or 0

                # Get move info
                move_name, move_type, power, accuracy, max_pp = get_move_info(move_id)

                # If PP is 0 or not set, assume full PP (for boxed Pokemon)
                if move_pp == 0 and max_pp > 0:
                    move_pp = max_pp

                # Move name
                name_text = self.small_font.render(
                    move_name.upper(), True, ui_colors.COLOR_TEXT
                )
                surf.blit(name_text, (move_rect.left + 8, move_rect.top + 4))

                # Move type badge
                type_color = TYPE_COLORS.get(move_type, (128, 128, 128))
                type_rect = pygame.Rect(move_rect.left + 8, move_rect.top + 22, 50, 14)
                pygame.draw.rect(surf, type_color, type_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, type_rect, 1)
                type_text = self.small_font.render(
                    move_type.upper()[:5], True, (255, 255, 255)
                )
                type_text_rect = type_text.get_rect(center=type_rect.center)
                surf.blit(type_text, type_text_rect)

                # Power/Accuracy
                if power > 0:
                    pow_text = self.small_font.render(
                        f"POW:{power}", True, (180, 180, 180)
                    )
                    surf.blit(pow_text, (move_rect.left + 70, move_rect.top + 22))

                # PP
                pp_text = self.small_font.render(
                    f"PP {move_pp}/{max_pp}", True, (180, 180, 180)
                )
                surf.blit(pp_text, (move_rect.right - 70, move_rect.top + 4))
            else:
                # Empty move slot
                empty_text = self.small_font.render("---", True, (100, 100, 100))
                surf.blit(empty_text, (move_rect.left + 8, move_rect.top + 12))

            y += move_height

    def _draw_contest_page(self, surf):
        """Draw the CONTEST tab - contest stats (RSE only)"""
        pad = 12
        y = self.tab_height + pad

        # Title
        title = self.title_font.render("CONTEST STATS", True, ui_colors.COLOR_TEXT)
        surf.blit(title, (pad, y))
        y += 28

        # Get contest stats from pokemon data
        contest_stats = self.pokemon.get("contest_stats", {})
        if not contest_stats:
            # Try raw dict
            raw = self.pokemon.get("raw", {})
            contest_stats = raw.get("contest_stats", {})

        # Contest conditions with their stat keys
        conditions = [
            ("COOL", "cool", (255, 100, 100)),
            ("BEAUTY", "beauty", (100, 100, 255)),
            ("CUTE", "cute", (255, 150, 200)),
            ("SMART", "smart", (100, 255, 100)),
            ("TOUGH", "tough", (255, 200, 100)),
        ]

        for cond_name, cond_key, cond_color in conditions:
            # Get value (0-255)
            value = contest_stats.get(cond_key, 0)

            # Label
            label = self.small_font.render(cond_name, True, ui_colors.COLOR_TEXT)
            surf.blit(label, (pad, y))

            # Bar background
            bar_x = pad + 70
            bar_width = self.width - bar_x - pad - 40
            bar_rect = pygame.Rect(bar_x, y + 2, bar_width, 12)
            pygame.draw.rect(surf, (50, 50, 50), bar_rect)
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, bar_rect, 1)

            # Fill bar based on value (0-255)
            if value > 0:
                fill_width = int((value / 255) * bar_width)
                pygame.draw.rect(surf, cond_color, (bar_x, y + 2, fill_width, 12))

            # Value text
            value_text = self.small_font.render(str(value), True, ui_colors.COLOR_TEXT)
            surf.blit(value_text, (bar_x + bar_width + 8, y))

            y += 24

        y += 8

        # Sheen (Feel)
        sheen_value = contest_stats.get("sheen", 0)
        sheen_label = self.small_font.render("SHEEN", True, ui_colors.COLOR_TEXT)
        surf.blit(sheen_label, (pad, y))

        # Sheen bar
        bar_x = pad + 70
        bar_width = self.width - bar_x - pad - 40
        bar_rect = pygame.Rect(bar_x, y + 2, bar_width, 12)
        pygame.draw.rect(surf, (50, 50, 50), bar_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, bar_rect, 1)

        if sheen_value > 0:
            fill_width = int((sheen_value / 255) * bar_width)
            pygame.draw.rect(surf, (255, 255, 100), (bar_x, y + 2, fill_width, 12))

        # Sheen value text
        sheen_text = self.small_font.render(
            str(sheen_value), True, ui_colors.COLOR_TEXT
        )
        surf.blit(sheen_text, (bar_x + bar_width + 8, y))

        y += 32

        # Ribbons section - only show earned ribbons
        ribbons = self.pokemon.get("ribbons", {})
        if not ribbons:
            raw = self.pokemon.get("raw", {})
            ribbons = raw.get("ribbons", {})

        # Collect earned ribbons
        earned_ribbons = []

        # Contest ribbons with ranks
        ribbon_data = [
            ("cool", "C", (255, 100, 100)),
            ("beauty", "B", (100, 100, 255)),
            ("cute", "U", (255, 150, 200)),
            ("smart", "S", (100, 255, 100)),
            ("tough", "T", (255, 200, 100)),
        ]

        for rkey, rname, rcolor in ribbon_data:
            rank = ribbons.get(rkey, "None")
            if rank != "None":
                earned_ribbons.append((rname, rcolor))

        # Special ribbons
        special_ribbons_data = [
            ("champion", "★", (255, 215, 0)),
            ("winning", "W", (150, 255, 150)),
            ("victory", "V", (200, 150, 255)),
        ]

        for rkey, symbol, rcolor in special_ribbons_data:
            if ribbons.get(rkey, False):
                earned_ribbons.append((symbol, rcolor))

        # Only draw ribbon section if there are earned ribbons
        if earned_ribbons:
            ribbon_y = self.height - 32

            # Draw section background
            ribbon_bg = pygame.Rect(pad, ribbon_y - 4, self.width - pad * 2, 28)
            pygame.draw.rect(surf, (30, 30, 35), ribbon_bg)
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, ribbon_bg, 1)

            ribbon_title = self.small_font.render("RIBBONS", True, (150, 150, 150))
            surf.blit(ribbon_title, (pad + 4, ribbon_y - 2))

            badge_x = pad + 60
            badge_y = ribbon_y + 2
            badge_size = 18
            badge_spacing = 22

            for symbol, rcolor in earned_ribbons:
                badge_rect = pygame.Rect(badge_x, badge_y, badge_size, badge_size)

                # Draw colored badge
                pygame.draw.rect(surf, rcolor, badge_rect)
                pygame.draw.rect(surf, (255, 255, 255), badge_rect, 1)

                # Draw symbol in center
                symbol_text = self.small_font.render(symbol, True, (255, 255, 255))
                symbol_rect = symbol_text.get_rect(center=badge_rect.center)
                surf.blit(symbol_text, symbol_rect)

                badge_x += badge_spacing
