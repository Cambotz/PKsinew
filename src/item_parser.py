#!/usr/bin/env python3

"""
Gen 3 Item Parser Module - Multi-Game Support

Handles parsing of bag items from Gen 3 save files.
Supports: Ruby, Sapphire, Emerald, FireRed, LeafGreen

IMPORTANT: Ruby/Sapphire and Emerald have DIFFERENT pocket offsets and slot
counts because Emerald expanded item/key-item pockets from 20 → 30 slots,
which shifts every pocket after them.  Treating them as one "RSE" group
causes reads/writes to land at wrong offsets for Emerald saves.

Offset reference (Section 1, relative to section data start):
    Pocket       Ruby/Sapphire        Emerald            FireRed/LeafGreen
    ──────────   ──────────────       ──────────────     ──────────────────
    Items        0x0560  (20 slots)   0x0560 (30 slots)  0x0310  (42 slots)
    Key Items    0x05B0  (20 slots)   0x05D8 (30 slots)  0x03B8  (30 slots)
    Poké Balls   0x0600  (16 slots)   0x0650 (16 slots)  0x0430  (13 slots)
    TMs/HMs      0x0640  (64 slots)   0x0690 (64 slots)  0x0464  (58 slots)
    Berries      0x0740  (46 slots)   0x0790 (46 slots)  0x054C  (43 slots)

Encryption:
    Ruby/Sapphire:  NO encryption (security key is 0)
    Emerald:        32-bit key at Section 0 + 0x00AC  (lower 16 bits for items)
    FireRed/LG:     32-bit key at Section 0 + 0x0F20  (lower 16 bits for items)

Money offset (Section 1):
    Ruby/Sapphire:  0x0490  (raw, no encryption)
    Emerald:        0x0490  (XOR with 32-bit security key)
    FireRed/LG:     0x0290  (XOR with 32-bit security key)

Sources: PKHeX (SAV3RS.cs, SAV3E.cs, SAV3FRLG.cs), pokeemerald/pokeruby decompilations
"""

import struct

# ─────────────────────────────────────────────────────────────────────
# POCKET CONFIGURATIONS (per game group)
# ─────────────────────────────────────────────────────────────────────
# Each entry:  (section1_relative_offset, pocket_name, max_slots)

POCKET_CONFIGS = {
    # ── Ruby / Sapphire ──────────────────────────────────────────────
    "RS": {
        "name": "Ruby/Sapphire",
        "offsets": [
            (0x0560, "items",     20),
            (0x05B0, "key_items", 20),
            (0x0600, "pokeballs", 16),
            (0x0640, "tms_hms",   64),
            (0x0740, "berries",   46),
        ],
        "money_offset": 0x0490,
        "has_encryption": False,   # RS does NOT encrypt items/money
    },

    # ── Emerald ──────────────────────────────────────────────────────
    "E": {
        "name": "Emerald",
        "offsets": [
            (0x0560, "items",     30),  # 30 slots (not 20!)
            (0x05D8, "key_items", 30),  # shifted because items pocket is larger
            (0x0650, "pokeballs", 16),
            (0x0690, "tms_hms",   64),
            (0x0790, "berries",   46),
        ],
        "money_offset": 0x0490,
        "has_encryption": True,    # Emerald encrypts with security key
    },

    # ── FireRed / LeafGreen ──────────────────────────────────────────
    "FRLG": {
        "name": "FireRed/LeafGreen",
        "offsets": [
            (0x0310, "items",     42),
            (0x03B8, "key_items", 30),
            (0x0430, "pokeballs", 13),
            (0x0464, "tms_hms",   58),
            (0x054C, "berries",   43),
        ],
        "money_offset": 0x0290,
        "has_encryption": True,    # FRLG encrypts with security key
    },
}

# ── Backward-compat alias ────────────────────────────────────────────
# Old code that passes game_type="RSE" will get RS offsets (the safer
# default — RS pockets are smaller so we won't read past them).
POCKET_CONFIGS["RSE"] = POCKET_CONFIGS["RS"]


def _normalize_game_type(game_type):
    """
    Normalize any game-type string into one of the canonical keys:
    'RS', 'E', or 'FRLG'.

    Accepts: 'RS', 'R', 'S', 'Ruby', 'Sapphire',
             'E', 'Emerald',
             'FRLG', 'FR', 'LG', 'FireRed', 'LeafGreen',
             'RSE' (legacy — maps to RS)
    """
    if game_type in ("RS", "R", "S", "Ruby", "Sapphire"):
        return "RS"
    if game_type in ("E", "Emerald"):
        return "E"
    if game_type in ("FRLG", "FR", "LG", "FireRed", "LeafGreen"):
        return "FRLG"
    if game_type == "RSE":
        # Legacy callers — default to RS (safe: smaller pockets)
        return "RS"
    # Unknown — fall back to FRLG (the original default)
    return "FRLG"


class ItemParser:
    """Parser for bag items in Gen 3 saves"""

    def __init__(self, data, section1_offset, game_type="auto"):
        """
        Initialize item parser.

        Args:
            data: bytearray of save file data
            section1_offset: Offset to Section 1 in the save data
            game_type: 'RS', 'E', 'FRLG', or 'auto' to auto-detect.
                       Legacy values 'RSE', 'Ruby', 'Emerald', etc. are accepted.
        """
        self.data = data
        self.section1_offset = section1_offset

        # Detect or normalize game type
        if game_type == "auto":
            self.game_type = self._detect_game_type()
        else:
            self.game_type = _normalize_game_type(game_type)

        # Get pocket configuration
        self.pocket_config = POCKET_CONFIGS.get(
            self.game_type, POCKET_CONFIGS["FRLG"]
        )

        # Resolve encryption key
        if self.pocket_config["has_encryption"]:
            # Encrypted games: key is at Section 1 + 0x0294 (lower 16 bits)
            self.item_key = struct.unpack(
                "<H", data[section1_offset + 0x0294 : section1_offset + 0x0296]
            )[0]
        else:
            # Ruby/Sapphire: no encryption
            self.item_key = 0

        self.bag = {
            "items": [],
            "key_items": [],
            "pokeballs": [],
            "tms_hms": [],
            "berries": [],
        }

    def _detect_game_type(self):
        """
        Auto-detect whether this is FR/LG, Emerald, or Ruby/Sapphire.

        Detection strategy (mirrors save_structure.detect_game_type):
        1. Check FRLG key-items area for FRLG-exclusive item IDs
        2. Check for Emerald vs RS by reading the security key at the
           RS/E key-items offset — Emerald has a non-zero security key
           at Section 0+0xAC, while RS does not.
        3. Fall back to RS if nothing else matches.

        Returns:
            str: 'FRLG', 'E', or 'RS'
        """
        # ── Step 1: Try FRLG ────────────────────────────────────────
        frlg_key_offset = self.section1_offset + 0x03B8
        for slot in range(10):
            item_offset = frlg_key_offset + (slot * 4)
            if item_offset + 2 <= len(self.data):
                item_id = struct.unpack(
                    "<H", self.data[item_offset : item_offset + 2]
                )[0]
                # FRLG-exclusive items (Teachy TV, Fame Checker, etc.)
                if item_id in (361, 362, 363, 364, 365, 366, 367, 368):
                    return "FRLG"

        # ── Step 2: Distinguish Emerald from RS ─────────────────────
        # Emerald stores its security key at Section 0 + 0x00AC.
        # RS stores 0 there (no encryption).  The item encryption key
        # at Section 1 + 0x0294 is also non-zero for Emerald.
        enc_key = struct.unpack(
            "<H",
            self.data[
                self.section1_offset + 0x0294 : self.section1_offset + 0x0296
            ],
        )[0]
        if enc_key != 0:
            # Non-zero encryption key → Emerald (RS has key=0)
            return "E"

        # ── Step 3: Check RSE key-items area for RS-specific items ──
        rse_key_offset = self.section1_offset + 0x05B0
        for slot in range(10):
            item_offset = rse_key_offset + (slot * 4)
            if item_offset + 2 <= len(self.data):
                item_id = struct.unpack(
                    "<H", self.data[item_offset : item_offset + 2]
                )[0]
                # RS/E-exclusive items
                if item_id in (265, 266, 268, 269, 270):
                    return "RS"

        # Default to RS (safest: smaller pockets, no encryption)
        return "RS"

    def parse_bag(self):
        """Parse bag items from Section 1"""
        try:
            for pocket_offset, pocket_name, max_slots in self.pocket_config["offsets"]:
                abs_offset = self.section1_offset + pocket_offset

                # RS does not encrypt key items (raw quantities)
                # Emerald and FRLG DO encrypt key items
                if pocket_name == "key_items" and self.game_type == "RS":
                    pocket_key = 0
                else:
                    pocket_key = self.item_key

                items = self._parse_pocket(abs_offset, max_slots, pocket_key)
                self.bag[pocket_name] = items

        except Exception as e:
            print(f"Error parsing bag: {e}")
            import traceback
            traceback.print_exc()

    def _parse_pocket(self, offset, max_slots, encryption_key=None):
        """
        Parse a single item pocket.

        Args:
            offset: Absolute offset to pocket start
            max_slots: Maximum number of item slots in this pocket
            encryption_key: XOR key for quantity decryption (None uses self.item_key)

        Returns:
            list: List of dicts with 'item_id' and 'quantity'
        """
        if encryption_key is None:
            encryption_key = self.item_key

        items = []

        for slot in range(max_slots):
            item_offset = offset + (slot * 4)

            if item_offset + 4 > len(self.data):
                break

            # Read item ID (NOT encrypted) and encrypted quantity
            item_id = struct.unpack(
                "<H", self.data[item_offset : item_offset + 2]
            )[0]
            qty_encrypted = struct.unpack(
                "<H", self.data[item_offset + 2 : item_offset + 4]
            )[0]

            # Skip empty slots
            if item_id in (0, 0xFFFF):
                continue

            # Decrypt quantity using XOR with encryption key
            if encryption_key != 0:
                quantity = qty_encrypted ^ encryption_key
            else:
                quantity = qty_encrypted

            # Validate item
            if 1 <= item_id <= 376 and 1 <= quantity <= 999:
                items.append({"item_id": item_id, "quantity": quantity})

        return items

    def get_bag(self):
        """Get the parsed bag data"""
        return self.bag

    def get_game_type(self):
        """Get detected game type"""
        return self.game_type

    def get_game_name(self):
        """Get human-readable game name"""
        return self.pocket_config["name"]

    def get_bag_summary(self):
        """Get summary of bag contents"""
        return {
            "game_type": self.game_type,
            "game_name": self.get_game_name(),
            "items": len(self.bag["items"]),
            "key_items": len(self.bag["key_items"]),
            "pokeballs": len(self.bag["pokeballs"]),
            "tms_hms": len(self.bag["tms_hms"]),
            "berries": len(self.bag["berries"]),
            "total": sum(
                len(self.bag[k])
                for k in ("items", "key_items", "pokeballs", "tms_hms", "berries")
            ),
        }

    def get_money(self):
        """
        Get decrypted money value.

        Money location and encryption varies by game:
            RS:   Section 1 + 0x0490, no encryption
            E:    Section 1 + 0x0490, XOR with 32-bit security key
            FRLG: Section 1 + 0x0290, XOR with 32-bit security key

        Returns:
            int: Money amount (0-999999)
        """
        try:
            money_rel = self.pocket_config["money_offset"]
            money_offset = self.section1_offset + money_rel

            if money_offset + 4 > len(self.data):
                return 0

            money_raw = struct.unpack(
                "<I", self.data[money_offset : money_offset + 4]
            )[0]

            if self.pocket_config["has_encryption"]:
                # For encrypted games, XOR with full 32-bit key
                # (the 32-bit key extends the 16-bit item_key)
                key_32 = struct.unpack(
                    "<I",
                    self.data[
                        self.section1_offset + 0x0294
                        : self.section1_offset + 0x0298
                    ],
                )[0]
                money = money_raw ^ key_32
            else:
                # RS: no encryption
                money = money_raw

            if 0 <= money <= 999999:
                return money
        except Exception:
            pass
        return 0


def parse_bag_from_section(data, section1_offset, game_type="auto"):
    """
    Convenience function to parse bag without creating ItemParser object.

    Args:
        data: bytearray of save file data
        section1_offset: Offset to Section 1
        game_type: 'RS', 'E', 'FRLG', or 'auto' to auto-detect.
                   Legacy values like 'RSE' are accepted.

    Returns:
        dict: Bag data with all 5 pockets and money
    """
    parser = ItemParser(data, section1_offset, game_type=game_type)
    parser.parse_bag()
    return {
        "bag": parser.get_bag(),
        "money": parser.get_money(),
        "game_type": parser.get_game_type(),
    }