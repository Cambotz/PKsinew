"""
Gen 3 Pokemon Save Parser - Main Module
Facade class that ties all parser modules together
"""

from .constants import calculate_level_from_exp, convert_species_to_national
from .items import get_bag_summary, parse_bag, parse_money
from .pokedex import parse_pokedex
from .pokemon import get_box_structure, parse_party, parse_pc_boxes
from .save_structure import (
    build_section_map,
    detect_game_type,
    find_active_save_slot,
    get_save_info,
    validate_save,
)
from .trainer import format_play_time, format_trainer_id, parse_trainer_info


class Gen3SaveParser:
    """
    Parser for Gen 3 Pokemon save files.

    Supports: FireRed, LeafGreen, Ruby, Sapphire, Emerald
    """

    def __init__(self, save_path=None):
        """
        Initialize parser.

        Args:
            save_path: Path to save file (optional, can call load() later)
        """
        self.save_path = save_path
        self.data = None
        self.loaded = False

        # Parsed data
        self.base_offset = 0
        self.section_offsets = {}
        self.game_type = "RSE"
        self.game_name = "Unknown"

        # Cached parsed results
        self._trainer_info = None
        self._party = None
        self._pc_boxes = None
        self._bag = None
        self._money = None
        self._pokedex = None

        if save_path:
            self.load(save_path)

    def load(self, save_path=None):
        """
        Load and parse a save file.

        Args:
            save_path: Path to save file (uses self.save_path if None)

        Returns:
            bool: True if successful
        """
        if save_path:
            self.save_path = save_path

        if not self.save_path:
            print("No save path specified")
            return False

        try:
            with open(self.save_path, "rb") as f:
                self.data = bytearray(f.read())

            if len(self.data) < 0x20000:
                print(f"Save file too small: {len(self.data)} bytes")
                return False

            # Parse save structure
            self.base_offset = find_active_save_slot(self.data)
            self.section_offsets = build_section_map(self.data, self.base_offset)
            self.game_type, self.game_name = detect_game_type(
                self.data, self.section_offsets
            )

            # Check for invalid/blank save
            if self.game_type == "INVALID":
                print("[Parser] ERROR: Save file is blank or corrupted")
                self.loaded = False
                return False

            # Debug output
            print(f"[Parser] Save slot: {'A' if self.base_offset == 0 else 'B'}")
            print(f"[Parser] Game detected: {self.game_type} ({self.game_name})")
            print(f"[Parser] Section 1 offset: 0x{self.section_offsets.get(1, 0):X}")

            # Clear cached data
            self._trainer_info = None
            self._party = None
            self._pc_boxes = None
            self._bag = None
            self._money = None
            self._pokedex = None

            self.loaded = True
            print(f"[Parser] Loaded: {self.save_path}")
            return True

        except Exception as e:
            print(f"Error loading save: {e}")
            import traceback

            traceback.print_exc()
            self.loaded = False
            return False

    # ==================== TRAINER INFO ====================

    def get_trainer_info(self):
        """
        Get trainer information.

        Returns:
            dict: Trainer info (name, id, gender, etc.)
        """
        if not self.loaded:
            return None

        if self._trainer_info is None:
            section0 = self.section_offsets.get(0, 0)
            self._trainer_info = parse_trainer_info(self.data, section0)

        return self._trainer_info

    @property
    def trainer_name(self):
        """Get trainer name."""
        info = self.get_trainer_info()
        return info["name"] if info else "Unknown"

    @property
    def trainer_id(self):
        """Get public trainer ID."""
        info = self.get_trainer_info()
        return info["trainer_id"] if info else 0

    @property
    def secret_id(self):
        """Get secret trainer ID."""
        info = self.get_trainer_info()
        return info["secret_id"] if info else 0

    @property
    def gender(self):
        """Get trainer gender."""
        info = self.get_trainer_info()
        return info["gender"] if info else "Unknown"

    @property
    def rival_name(self):
        """Get rival name (FRLG only)."""
        info = self.get_trainer_info()
        return info.get("rival_name", "") if info else ""

    @property
    def play_hours(self):
        """Get play time hours."""
        info = self.get_trainer_info()
        return info["play_hours"] if info else 0

    @property
    def play_minutes(self):
        """Get play time minutes."""
        info = self.get_trainer_info()
        return info["play_minutes"] if info else 0

    @property
    def play_seconds(self):
        """Get play time seconds."""
        info = self.get_trainer_info()
        return info["play_seconds"] if info else 0

    @property
    def game_code(self):
        """Get game code."""
        info = self.get_trainer_info()
        return info.get("game_code", 0) if info else 0

    # ==================== PARTY ====================

    def get_party(self):
        """
        Get party Pokemon.

        Returns:
            list: List of Pokemon dicts
        """
        if not self.loaded:
            return []

        if self._party is None:
            section1 = self.section_offsets.get(1, 0)
            print(
                f"[Parser] Parsing party with game_type={self.game_type}, section1=0x{section1:X}"
            )
            self._party = parse_party(self.data, section1, self.game_type)
            print(f"[Parser] Found {len(self._party)} party Pokemon")
            for i, poke in enumerate(self._party):
                print(
                    f"[Parser]   {i+1}. #{poke.get('species', 0):03d} {poke.get('nickname', '???')} Lv.{poke.get('level', 0)}"
                )

        return self._party

    def get_party_data(self):
        """Alias for get_party() for compatibility."""
        return self.get_party()

    @property
    def party_pokemon(self):
        """Get party Pokemon list."""
        return self.get_party()

    # ==================== PC BOXES ====================

    def get_pc_boxes(self):
        """
        Get all PC box Pokemon (raw list).

        Returns:
            list: List of Pokemon dicts with box_number and box_slot
        """
        if not self.loaded:
            return []

        if self._pc_boxes is None:
            self._pc_boxes = parse_pc_boxes(self.data, self.section_offsets)

        return self._pc_boxes

    @property
    def pc_boxes(self):
        """Get PC boxes list."""
        return self.get_pc_boxes()

    def get_box(self, box_number):
        """
        Get a specific box with all 30 slots.

        Args:
            box_number: Box number (1-14)

        Returns:
            list: 30 slot dicts
        """
        return get_box_structure(self.get_pc_boxes(), box_number)

    def get_box_structure(self, box_number):
        """Alias for get_box() for compatibility."""
        return self.get_box(box_number)

    def get_all_boxes_structure(self):
        """
        Get all 14 boxes with slot structure.

        Returns:
            dict: {box_number: [30 slots]}
        """
        all_boxes = {}
        for box_num in range(1, 15):
            all_boxes[box_num] = self.get_box(box_num)
        return all_boxes

    def get_box_summary(self):
        """
        Get summary of all boxes.

        Returns:
            dict: Box statistics
        """
        summary = {}
        for box_num in range(1, 15):
            box_slots = self.get_box(box_num)
            filled = sum(1 for slot in box_slots if not slot.get("empty", False))
            empty = 30 - filled
            empty_slots = [
                slot["slot"] for slot in box_slots if slot.get("empty", False)
            ]

            summary[box_num] = {
                "total_slots": 30,
                "filled": filled,
                "empty": empty,
                "empty_slots": empty_slots,
                "first_empty": empty_slots[0] if empty_slots else None,
            }

        return summary

    def get_pc_summary(self):
        """
        Get PC storage summary.

        Returns:
            dict: Total Pokemon count and per-box counts
        """
        pc_pokemon = self.get_pc_boxes()
        total = len(pc_pokemon)

        boxes = {}
        for poke in pc_pokemon:
            box_num = poke.get("box_number", 0)
            boxes[box_num] = boxes.get(box_num, 0) + 1

        return {"total_pokemon": total, "boxes": boxes}

    # ==================== BAG / ITEMS ====================

    def get_bag(self):
        """
        Get bag contents.

        Returns:
            dict: {pocket_name: [items]}
        """
        if not self.loaded:
            return {
                "items": [],
                "key_items": [],
                "pokeballs": [],
                "tms_hms": [],
                "berries": [],
            }

        if self._bag is None:
            section1 = self.section_offsets.get(1, 0)
            self._bag = parse_bag(
                self.data, section1, self.game_type, self.section_offsets
            )

        return self._bag

    @property
    def money(self):
        """Get money amount."""
        if not self.loaded:
            return 0

        if self._money is None:
            section1 = self.section_offsets.get(1, 0)
            self._money = parse_money(
                self.data, section1, self.game_type, self.section_offsets
            )

        return self._money

    @property
    def bag(self):
        """Get bag contents."""
        return self.get_bag()

    # ==================== POKEDEX ====================

    def get_pokedex(self):
        """
        Get Pokedex data from save file.

        Returns:
            dict: {owned_count, seen_count, owned_list, seen_list}
        """
        if not self.loaded:
            return {
                "owned_count": 0,
                "seen_count": 0,
                "owned_list": [],
                "seen_list": [],
            }

        if self._pokedex is None:
            section0 = self.section_offsets.get(0, 0)
            self._pokedex = parse_pokedex(self.data, section0, self.game_type)

        return self._pokedex

    def get_pokedex_count(self):
        """
        Get Pokedex seen/caught counts (National Dex).

        Returns:
            dict: {seen: int, caught: int, max: int}
        """
        pokedex = self.get_pokedex()

        # Always return National Dex counts for trainer info display
        return {
            "seen": pokedex["seen_count"],
            "caught": pokedex["owned_count"],
            "max": 386,
        }

    # ==================== UTILITY ====================

    def validate(self):
        """
        Validate the save file.

        Returns:
            tuple: (is_valid, errors)
        """
        if not self.data:
            return False, ["No save file loaded"]
        return validate_save(self.data)

    def get_save_info(self):
        """
        Get save file information.

        Returns:
            dict: Save info
        """
        if not self.data:
            return {"valid": False, "error": "No save file loaded"}
        return get_save_info(self.data)

    def format_pokemon_display(self, pokemon):
        """
        Format Pokemon for display.

        Args:
            pokemon: Pokemon dict

        Returns:
            str: Display text
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
