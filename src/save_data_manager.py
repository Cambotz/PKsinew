"""
Save Data Manager - Bridges Gen3 Parser to UI
Handles loading save files and providing data to UI screens

Updated to use modular parser package.
"""

import json
import os

# Import config for paths
from config import (
    GEN3_NORMAL_DIR,
    GEN8_ICONS_DIR,
    POKEMON_DB_PATH,
    get_egg_sprite_path,
    get_sprite_path,
)

# Import from modular parser package
try:
    from parser import Gen3SaveParser, get_item_name
    from parser.trainer import format_play_time, format_trainer_id

    PARSER_AVAILABLE = True
    MODULAR_PARSER = True
    # print("[SaveDataManager] Using modular parser package")
except ImportError:
    MODULAR_PARSER = False
    # Fallback if parser not in path - try monolithic parser
    try:
        from gen3_save_parser import Gen3SaveParser

        from item_names import get_item_name

        PARSER_AVAILABLE = True
        # print("[SaveDataManager] Using monolithic gen3_save_parser")

        def format_trainer_id(tid, sid, show_secret=False):
            if show_secret:
                return f"{tid:05d}-{sid:05d}"
            return f"{tid:05d}"

        def format_play_time(hours, minutes, seconds):
            return f"{hours:03d}:{minutes:02d}:{seconds:02d}"

    except ImportError:
        PARSER_AVAILABLE = False
        MODULAR_PARSER = False
        print("Warning: Parser not available!")


# Global cache for parsed saves (path -> parser instance)
_save_cache = {}

# Species name cache (loaded from pokemon_db.json)
_species_names = {}


def _load_species_names():
    """Load species names from pokemon_db.json"""
    if _species_names:
        return  # Already loaded

    if os.path.exists(POKEMON_DB_PATH):
        try:
            with open(POKEMON_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for value in data.items():
                if isinstance(value, dict) and "id" in value and "name" in value:
                    _species_names[value["id"]] = value["name"]
        except Exception as e:
            print(f"[SaveDataManager] Failed to load species names: {e}")


def get_species_name(species_id):
    """Get species name from ID"""
    _load_species_names()
    return _species_names.get(species_id, f"Pokemon #{species_id}")


def precache_save(save_path):
    """
    Pre-parse a save file and cache it.
    Returns True if successful, False otherwise.
    """

    if not save_path or not os.path.exists(save_path):
        return False

    # Already cached?
    if save_path in _save_cache:
        return True

    try:
        parser = Gen3SaveParser(save_path)
        if parser.loaded:
            _save_cache[save_path] = parser
            return True
    except Exception as e:
        print(f"Failed to precache {save_path}: {e}")

    return False


def get_cached_parser(save_path):
    """Get a cached parser instance, or None if not cached."""
    return _save_cache.get(save_path)


def clear_save_cache():
    """Clear the save cache."""
    global _save_cache
    _save_cache = {}


def invalidate_save_cache(save_path):
    """
    Remove a specific save from the cache.
    Used after modifying a save file to force re-parsing.

    Args:
        save_path: Path to the save file to invalidate
    """
    if save_path in _save_cache:
        del _save_cache[save_path]
        print(f"Invalidated cache for: {save_path}")


class SaveDataManager:
    """Manages save file data for UI screens"""

    def __init__(self):
        self.parser = None
        self.current_save_path = None
        self.loaded = False

    def load_save(self, save_path):
        """
        Load a save file. Uses cache if available.

        Args:
            save_path: Path to .sav file

        Returns:
            bool: True if successful
        """
        if not os.path.exists(save_path):
            print(f"Save file not found: {save_path}")
            return False

        try:
            # Check cache first
            cached = get_cached_parser(save_path)
            if cached:
                self.parser = cached
                self.loaded = True
                self.current_save_path = save_path
                return True

            # Not cached, parse fresh
            self.parser = Gen3SaveParser(save_path)
            self.loaded = self.parser.loaded

            if self.loaded:
                self.current_save_path = save_path
                # Add to cache for future use
                _save_cache[save_path] = self.parser
                return True
            else:
                print(f"Failed to parse: {save_path}")
                return False

        except Exception as e:
            print(f"Error loading save: {e}")
            import traceback

            traceback.print_exc()
            self.loaded = False
            return False

    def is_loaded(self):
        """Check if save file is loaded."""
        return self.loaded and self.parser is not None

    @property
    def save_path(self):
        """Get current save file path."""
        return self.current_save_path

    def reload(self):
        """
        Reload the current save file from disk.
        Useful after external modifications (like transfers).

        Returns:
            bool: True if successful
        """
        if not self.current_save_path:
            print("No save file to reload")
            return False

        # Clear from cache to force re-parse
        if self.current_save_path in _save_cache:
            del _save_cache[self.current_save_path]

        # Reload
        return self.load_save(self.current_save_path)

    # ==================== GAME INFO ====================

    def get_game_type(self):
        """Get game type ('FRLG' or 'RSE')."""
        if not self.is_loaded():
            return "RSE"
        return self.parser.game_type

    def get_game_name(self):
        """Get human-readable game name."""
        if not self.is_loaded():
            return "Unknown"
        return self.parser.game_name

    # ==================== TRAINER INFO ====================

    def get_trainer_info(self):
        """
        Get trainer card information.

        Returns:
            dict: {name, id, secret_id, money, gender, rival_name, game_code}
        """
        if not self.is_loaded():
            return None

        return {
            "name": self.parser.trainer_name,
            "id": self.parser.trainer_id,
            "secret_id": self.parser.secret_id,
            "money": self.parser.money,
            "gender": self.parser.gender,
            "rival_name": self.parser.rival_name,
            "game_code": self.parser.game_code,
            "game_type": self.parser.game_type,
            "game_name": self.parser.game_name,
        }

    def format_trainer_id(self, show_secret=False):
        """
        Format trainer ID for display.

        Args:
            show_secret: If True, show full 10-digit ID (public+secret)

        Returns:
            str: Formatted ID like "12345" or "12345-67890"
        """
        if not self.is_loaded():
            return "00000"

        return format_trainer_id(
            self.parser.trainer_id, self.parser.secret_id, show_secret
        )

    def get_badges(self):
        """
        Get badge status for all 8 gym badges.

        Returns:
            list: 8 booleans, True = badge earned, False = not earned
                  Index 0 = Badge 1, Index 7 = Badge 8
        """
        if not self.is_loaded():
            return [False] * 8

        try:
            data = self.parser.data
            section_offsets = self.parser.section_offsets
            game_type = self.parser.game_type

            section2_offset = section_offsets.get(2, 0)

            # RSE badge layout (verified against raw save data):
            #   byte0: Badge 1 = bit 7
            #   byte1: Badge 2 = bit 0, Badge 3 = bit 1, ... Badge 8 = bit 6
            # FRLG badge layout: all 8 badges in a single byte, bit 0 = Badge 1
            if game_type == "E":
                # All Emerald variants (International and Japanese):
                # Section 2 + 0x3FD, single byte, bit 7 = Stone (Badge 1) ... bit 0 = Rain (Badge 8)
                badge_byte = data[section2_offset + 0x3FD]
                badges = [bool((badge_byte >> (7 - i)) & 1) for i in range(8)]
            elif game_type in ("RS", "R", "S"):
                # Ruby/Sapphire: Section 2 + 0x3A0
                badge_offset = section2_offset + 0x3A0
                byte0 = data[badge_offset]
                byte1 = data[badge_offset + 1]
                badges = [bool((byte0 >> 7) & 1)]
                badges += [bool((byte1 >> i) & 1) for i in range(7)]
            else:  # FRLG
                # FireRed/LeafGreen: Section 2 + 0x64
                # All 8 badges in a single byte: Bit 0 = Boulder, Bit 7 = Earth
                badge_offset = section2_offset + 0x64
                badge_byte = data[badge_offset]
                badges = [bool((badge_byte >> i) & 1) for i in range(8)]

            return badges

        except Exception as e:
            print(f"[Badges] Error: {e}")
            import traceback

            traceback.print_exc()
            return [False] * 8

    def get_badge_count(self):
        """Get total number of badges earned."""
        return sum(self.get_badges())

    # ==================== PARTY ====================

    def _enrich_pokemon(self, pokemon):
        """Add species_name to a Pokemon dict"""
        if pokemon and not pokemon.get("empty") and "species" in pokemon:
            species_id = pokemon.get("species", 0)
            if species_id:
                pokemon["species_name"] = get_species_name(species_id)
        return pokemon

    def get_party(self):
        """
        Get party Pokemon.

        Returns:
            list: Up to 6 Pokemon dicts
        """
        if not self.is_loaded():
            return []
        party = self.parser.party_pokemon
        # Enrich with species names
        return [self._enrich_pokemon(p.copy() if p else p) for p in party]

    def get_party_size(self):
        """Get number of Pokemon in party."""
        return len(self.get_party())

    def get_party_slot(self, slot_index):
        """
        Get Pokemon at specific party slot (0-5).

        Returns:
            dict or None: Pokemon data or None if slot empty
        """
        party = self.get_party()
        if 0 <= slot_index < len(party):
            return party[slot_index]
        return None

    # ==================== PC BOXES ====================

    def get_box(self, box_number):
        """
        Get a specific PC box with all 30 slots.

        Args:
            box_number: Box number (1-14)

        Returns:
            list: 30 slot dicts (pokemon or empty slot markers)
        """
        if not self.is_loaded():
            return []
        box = self.parser.get_box(box_number)
        # Enrich with species names
        return [
            self._enrich_pokemon(p.copy() if p and not p.get("empty") else p)
            for p in box
        ]

    def get_all_boxes(self):
        """
        Get all 14 PC boxes.

        Returns:
            dict: {box_number: [30 slots]}
        """
        if not self.is_loaded():
            return {}
        return self.parser.get_all_boxes_structure()

    def get_box_summary(self):
        """
        Get summary stats for all boxes.

        Returns:
            dict: {box_number: {filled, empty, first_empty, etc}}
        """
        if not self.is_loaded():
            return {}
        return self.parser.get_box_summary()

    def get_pc_pokemon_count(self):
        """Get total number of Pokemon in PC."""
        if not self.is_loaded():
            return 0
        return len(self.parser.pc_boxes)

    # ==================== BAG / ITEMS ====================

    def get_bag(self):
        """
        Get bag contents (all pockets).

        Returns:
            dict: {items, key_items, pokeballs, tms_hms, berries}
        """
        if not self.is_loaded():
            return {
                "items": [],
                "key_items": [],
                "pokeballs": [],
                "tms_hms": [],
                "berries": [],
            }
        return self.parser.bag

    def get_pocket(self, pocket_name):
        """
        Get specific bag pocket.

        Args:
            pocket_name: 'items', 'key_items', 'pokeballs', 'tms_hms', 'berries'

        Returns:
            list: Items in pocket [{item_id, quantity, name}]
        """
        bag = self.get_bag()
        return bag.get(pocket_name, [])

    def get_items_with_names(self):
        """
        Get bag items with human-readable names.

        Returns:
            dict: {pocket_name: [{id, name, quantity}]}
        """
        if not self.is_loaded():
            return {}

        bag = self.get_bag()
        result = {}

        for pocket_name, items in bag.items():
            result[pocket_name] = [
                {
                    "id": item.get("item_id", 0),
                    "name": item.get("name") or get_item_name(item.get("item_id", 0)),
                    "quantity": item.get("quantity", 0),
                }
                for item in items
            ]

        return result

    def get_total_items(self):
        """Get total number of unique items across all pockets."""
        bag = self.get_bag()
        return sum(len(pocket) for pocket in bag.values())

    def get_money(self):
        """Get money amount."""
        if not self.is_loaded():
            return 0
        return self.parser.money

    # ==================== POKEMON DISPLAY ====================

    def format_pokemon_display(self, pokemon):
        """
        Format Pokemon for display.

        Args:
            pokemon: Pokemon dict from parser

        Returns:
            str: Display text like "PIKACHU Lv.25" or "Egg"
        """
        if not pokemon:
            return "Empty"

        if pokemon.get("empty"):
            return "Empty"

        if pokemon.get("egg"):
            return "Egg"

        name = pokemon.get("nickname") or pokemon.get("species_name") or "???"
        level = pokemon.get("level", 0)

        return f"{name.upper()} Lv.{level}"

    def is_pokemon_shiny(self, pokemon):
        """
        Check if a Pokemon is shiny.

        Args:
            pokemon: Pokemon dict

        Returns:
            bool: True if shiny
        """
        if not pokemon or pokemon.get("empty") or pokemon.get("egg"):
            return False

        personality = pokemon.get("personality", 0)
        ot_id = pokemon.get("ot_id", 0)

        if personality == 0 or ot_id == 0:
            return False

        # Extract trainer ID and secret ID from OT ID
        tid = ot_id & 0xFFFF
        sid = (ot_id >> 16) & 0xFFFF

        # Extract PID high and low
        pid_low = personality & 0xFFFF
        pid_high = (personality >> 16) & 0xFFFF

        # Calculate shiny value
        shiny_value = tid ^ sid ^ pid_low ^ pid_high

        # Pokemon is shiny if value < 8
        return shiny_value < 8

    def get_pokemon_nature(self, pokemon):
        """
        Get Pokemon's nature.

        Args:
            pokemon: Pokemon dict

        Returns:
            str: Nature name or "Unknown"
        """
        if not pokemon or pokemon.get("empty") or pokemon.get("egg"):
            return "Unknown"

        NATURE_NAMES = [
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

        personality = pokemon.get("personality", 0)
        nature_id = personality % 25

        if 0 <= nature_id < len(NATURE_NAMES):
            return NATURE_NAMES[nature_id]
        return "Unknown"

    def get_pokemon_sprite_path(self, pokemon, shiny=False, use_showdown=False):
        """
        Get sprite path for a Pokemon.

        Args:
            pokemon: Pokemon dict
            shiny: Whether to get shiny sprite (can also auto-detect)
            use_showdown: If True, use showdown sprites (GIF), else use gen3 sprites (PNG)

        Returns:
            str: Path to sprite image or None
        """
        if not pokemon or pokemon.get("empty"):
            return None

        # Handle eggs with special egg sprite
        if pokemon.get("egg"):
            if use_showdown:
                egg_path = get_egg_sprite_path("showdown")
            else:
                egg_path = get_egg_sprite_path("gen3")

            if os.path.exists(egg_path):
                return egg_path
            return None

        species = pokemon.get("species", 0)

        if species == 0:
            return None

        # Auto-detect shiny if not explicitly set
        if not shiny:
            shiny = self.is_pokemon_shiny(pokemon)

        # Construct sprite path based on type
        if use_showdown:
            sprite_path = get_sprite_path(species, shiny=shiny, sprite_type="showdown")
        else:
            sprite_path = get_sprite_path(species, shiny=shiny, sprite_type="gen3")

        # Debug output
        # print(f"[DEBUG] get_pokemon_sprite_path: {nickname} -> species={species} shiny={shiny} showdown={use_showdown} path={sprite_path} exists={os.path.exists(sprite_path)}", flush=True)

        if os.path.exists(sprite_path):
            return sprite_path

        return None

    def get_gen3_sprite_path(self, pokemon, shiny=None):
        """
        Convenience method to get gen3 sprite (PNG).

        Args:
            pokemon: Pokemon dict
            shiny: Whether to get shiny sprite (None = auto-detect)

        Returns:
            str: Path to PNG sprite or None
        """
        if shiny is None:
            shiny = self.is_pokemon_shiny(pokemon)
        return self.get_pokemon_sprite_path(pokemon, shiny=shiny, use_showdown=False)

    def get_showdown_sprite_path(self, pokemon, shiny=None):
        """
        Convenience method to get showdown sprite (GIF).

        Args:
            pokemon: Pokemon dict
            shiny: Whether to get shiny sprite (None = auto-detect)

        Returns:
            str: Path to GIF sprite or None
        """
        if shiny is None:
            shiny = self.is_pokemon_shiny(pokemon)
        return self.get_pokemon_sprite_path(pokemon, shiny=shiny, use_showdown=True)

    def get_gen8_icon_path(self, pokemon):
        """
        Get Gen8 icon path (small PNG icons for grid/party display).

        Args:
            pokemon: Pokemon dict

        Returns:
            str: Path to icon PNG or None
        """
        if not pokemon or pokemon.get("empty"):
            return None

        # Handle eggs
        if pokemon.get("egg"):
            # Try gen8 egg first
            egg_path = os.path.join(GEN8_ICONS_DIR, "egg.png")

            if os.path.exists(egg_path):
                return egg_path

            # Fallback to gen3 egg
            egg_path = os.path.join(GEN3_NORMAL_DIR, "egg.png")

            if os.path.exists(egg_path):
                return egg_path
            return None

        species = pokemon.get("species", 0)
        if species == 0:
            return None

        # Gen8 icons path
        icon_path = get_sprite_path(species, sprite_type="gen8")

        if os.path.exists(icon_path):
            return icon_path

        return None

    # ==================== STATISTICS ====================

    def get_pokedex_count(self):
        """
        Get Pokedex seen/caught counts from save file bitfields.

        Returns:
            dict: {seen: int, caught: int, max: int}
        """
        if not self.is_loaded():
            return {"seen": 0, "caught": 0, "max": 386}

        # Use the parser's pokedex reading which parses the actual bitfields
        return self.parser.get_pokedex_count()

    def get_pokedex_data(self):
        """
        Get full Pokedex data including lists of seen/caught Pokemon.

        Returns:
            dict: {
                'owned_count': int,
                'seen_count': int,
                'owned_list': list of National Dex numbers,
                'seen_list': list of National Dex numbers
            }
        """
        if not self.is_loaded():
            return {
                "owned_count": 0,
                "seen_count": 0,
                "owned_list": [],
                "seen_list": [],
            }

        return self.parser.get_pokedex()

    def get_play_time(self):
        """
        Get play time from save.

        Returns:
            dict: {hours: int, minutes: int, seconds: int}
        """
        if not self.is_loaded():
            return {"hours": 0, "minutes": 0, "seconds": 0}

        return {
            "hours": self.parser.play_hours,
            "minutes": self.parser.play_minutes,
            "seconds": self.parser.play_seconds,
        }

    def format_play_time(self):
        """
        Get formatted play time string.

        Returns:
            str: Formatted time like "123:45:30"
        """
        if not self.is_loaded():
            return "000:00:00"

        return format_play_time(
            self.parser.play_hours, self.parser.play_minutes, self.parser.play_seconds
        )

    # ==================== UTILITY ====================

    def get_save_info(self):
        """
        Get complete save file info for debugging.

        Returns:
            dict: All major save data
        """
        if not self.is_loaded():
            return None

        return {
            "file": self.current_save_path,
            "game_type": self.parser.game_type,
            "game_name": self.parser.game_name,
            "trainer": self.get_trainer_info(),
            "party_size": self.get_party_size(),
            "pc_pokemon": self.get_pc_pokemon_count(),
            "total_items": self.get_total_items(),
            "money": self.parser.money,
            "play_time": self.format_play_time(),
            "pokedex": self.get_pokedex_count(),
        }

    def validate_save(self):
        """
        Validate the save file.

        Returns:
            tuple: (is_valid, errors)
        """
        if not self.is_loaded():
            return False, ["No save file loaded"]
        return self.parser.validate()


# Global instance for easy access
_manager = SaveDataManager()


def get_manager():
    """Get the global SaveDataManager instance."""
    return _manager
