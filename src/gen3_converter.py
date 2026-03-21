#!/usr/bin/env python3

"""
Gen 3 Pokemon Converter
Converts between Gen 3 save format and Universal Pokemon Object.

Handles:
  - Gen 3 → UniversalPokemon (parsing)
  - UniversalPokemon → Gen 3 (writing)
  - Species ID conversion (internal ↔ national)
  - PID generation and validation
  - Checksum calculation

Author: Sinew Development Team
"""

import struct
import sys
from typing import Dict, Tuple, Optional

from universal_pokemon import (
    UniversalPokemon, MoveSlot, IVSet, EVSet, StatSet, ContestStats
)

# Import from your existing parser
PARSER_AVAILABLE = False
try:
    from parser.crypto import (
        decrypt_pokemon_data, encrypt_pokemon_data,
        decode_gen3_text, encode_gen3_text,
        get_block_order, calculate_pokemon_checksum
    )
    from parser.constants import (
        convert_species_to_national, convert_species_to_internal,
        INTERNAL_TO_NATIONAL
    )
    from parser.trainer import is_shiny, get_pokemon_nature
    PARSER_AVAILABLE = True
except ImportError:
    print("[Gen3Converter] Warning: Could not import parser modules, using fallbacks")
    
    # Fallback: Internal (game storage) to National Dex mapping
    # Species 1-251 map directly (Gen 1-2), 252+ are Gen 3 with scrambled internal IDs
    INTERNAL_TO_NATIONAL = {
        277: 252, 278: 253, 279: 254, 280: 255, 281: 256, 282: 257, 283: 258, 284: 259,
        285: 260, 286: 261, 287: 262, 288: 263, 289: 264, 290: 265, 291: 266, 292: 267,
        293: 268, 294: 269, 295: 270, 296: 271, 297: 272, 298: 273, 299: 274, 300: 275,
        301: 290, 302: 291, 303: 292, 304: 276, 305: 277, 306: 285, 307: 286, 308: 327,
        309: 278, 310: 279, 311: 283, 312: 284, 313: 320, 314: 321, 315: 300, 316: 301,
        317: 352, 318: 343, 319: 344, 320: 299, 321: 324, 322: 302, 323: 339, 324: 340,
        325: 370, 326: 341, 327: 342, 328: 349, 329: 350, 330: 318, 331: 319, 332: 328,
        333: 329, 334: 330, 335: 296, 336: 297, 337: 309, 338: 310, 339: 322, 340: 323,
        341: 363, 342: 364, 343: 365, 344: 331, 345: 332, 346: 361, 347: 362, 348: 337,
        349: 338, 350: 298, 351: 325, 352: 326, 353: 311, 354: 312, 355: 303, 356: 307,
        357: 308, 358: 333, 359: 334, 360: 360, 361: 355, 362: 356, 363: 315, 364: 287,
        365: 288, 366: 289, 367: 316, 368: 317, 369: 357, 370: 293, 371: 294, 372: 295,
        373: 366, 374: 367, 375: 368, 376: 359, 377: 353, 378: 354, 379: 336, 380: 335,
        381: 369, 382: 304, 383: 305, 384: 306, 385: 351, 386: 313, 387: 314, 388: 345,
        389: 346, 390: 347, 391: 348, 392: 280, 393: 281, 394: 282, 395: 371, 396: 372,
        397: 373, 398: 374, 399: 375, 400: 376, 401: 377, 402: 378, 403: 379, 404: 382,
        405: 383, 406: 384, 407: 380, 408: 381, 409: 385, 410: 386, 411: 358,
    }
    NATIONAL_TO_INTERNAL = {v: k for k, v in INTERNAL_TO_NATIONAL.items()}
    
    def convert_species_to_national(internal_species: int) -> int:
        """Convert internal species ID to National Dex number."""
        if internal_species in INTERNAL_TO_NATIONAL:
            return INTERNAL_TO_NATIONAL[internal_species]
        # Gen 1-2 Pokemon use same ID
        if 1 <= internal_species <= 251:
            return internal_species
        return internal_species  # Unknown, return as-is
    
    def convert_species_to_internal(national_species: int) -> int:
        """Convert National Dex number to internal species ID."""
        if national_species in NATIONAL_TO_INTERNAL:
            return NATIONAL_TO_INTERNAL[national_species]
        # Gen 1-2 Pokemon use same ID
        if 1 <= national_species <= 251:
            return national_species
        return national_species  # Unknown, return as-is
    
    # Fallback crypto functions if parser not available
    PERMUTATIONS = [
        [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2],
        [0, 2, 3, 1], [0, 3, 2, 1], [1, 0, 2, 3], [1, 0, 3, 2],
        [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
        [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2],
        [2, 3, 0, 1], [3, 2, 0, 1], [1, 2, 3, 0], [1, 3, 2, 0],
        [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0],
    ]
    
    def get_block_order(pid: int) -> list:
        """Get block permutation order from PID."""
        return PERMUTATIONS[pid % 24]
    
    def decrypt_pokemon_data(data: bytes, key: int) -> bytes:
        """XOR decrypt Pokemon data."""
        result = bytearray(len(data))
        for i in range(0, len(data), 4):
            chunk = struct.unpack("<I", data[i:i+4])[0]
            decrypted = chunk ^ key
            result[i:i+4] = struct.pack("<I", decrypted)
        return bytes(result)
    
    def encrypt_pokemon_data(data: bytes, key: int) -> bytes:
        """XOR encrypt Pokemon data."""
        return decrypt_pokemon_data(data, key)  # XOR is symmetric
    
    def calculate_pokemon_checksum(data: bytes) -> int:
        """Calculate Gen 3 Pokemon checksum."""
        checksum = 0
        for i in range(0, len(data), 2):
            checksum = (checksum + struct.unpack("<H", data[i:i+2])[0]) & 0xFFFF
        return checksum
    
    # Gen 3 character encoding table
    GEN3_CHAR_MAP = {
        0x00: ' ', 0xBB: 'A', 0xBC: 'B', 0xBD: 'C', 0xBE: 'D', 0xBF: 'E',
        0xC0: 'F', 0xC1: 'G', 0xC2: 'H', 0xC3: 'I', 0xC4: 'J', 0xC5: 'K',
        0xC6: 'L', 0xC7: 'M', 0xC8: 'N', 0xC9: 'O', 0xCA: 'P', 0xCB: 'Q',
        0xCC: 'R', 0xCD: 'S', 0xCE: 'T', 0xCF: 'U', 0xD0: 'V', 0xD1: 'W',
        0xD2: 'X', 0xD3: 'Y', 0xD4: 'Z', 0xD5: 'a', 0xD6: 'b', 0xD7: 'c',
        0xD8: 'd', 0xD9: 'e', 0xDA: 'f', 0xDB: 'g', 0xDC: 'h', 0xDD: 'i',
        0xDE: 'j', 0xDF: 'k', 0xE0: 'l', 0xE1: 'm', 0xE2: 'n', 0xE3: 'o',
        0xE4: 'p', 0xE5: 'q', 0xE6: 'r', 0xE7: 's', 0xE8: 't', 0xE9: 'u',
        0xEA: 'v', 0xEB: 'w', 0xEC: 'x', 0xED: 'y', 0xEE: 'z', 0xA1: '0',
        0xA2: '1', 0xA3: '2', 0xA4: '3', 0xA5: '4', 0xA6: '5', 0xA7: '6',
        0xA8: '7', 0xA9: '8', 0xAA: '9', 0xAB: '!', 0xAC: '?', 0xAD: '.',
        0xAE: '-', 0xB8: '♂', 0xB9: '♀', 0xFF: '\0',
    }
    CHAR_TO_GEN3 = {v: k for k, v in GEN3_CHAR_MAP.items()}
    
    def decode_gen3_text(data: bytes, max_len: int = 10) -> str:
        """Decode Gen 3 text."""
        result = []
        for i, byte in enumerate(data[:max_len]):
            if byte == 0xFF:
                break
            result.append(GEN3_CHAR_MAP.get(byte, '?'))
        return ''.join(result).rstrip()
    
    def encode_gen3_text(text: str, length: int) -> bytes:
        """Encode text to Gen 3 format."""
        result = bytearray(length)
        for i, char in enumerate(text[:length]):
            result[i] = CHAR_TO_GEN3.get(char, 0x00)
        # Fill rest with 0xFF
        for i in range(len(text), length):
            result[i] = 0xFF
        return bytes(result)
    
    def is_shiny(pid: int, tid: int, sid: int) -> bool:
        """Check if Pokemon is shiny."""
        p1 = (pid >> 16) & 0xFFFF
        p2 = pid & 0xFFFF
        return (p1 ^ p2 ^ tid ^ sid) < 8
    
    def get_pokemon_nature(pid: int) -> int:
        """Get nature from PID."""
        return pid % 25


# =============================================================================
# GEN 3 MOVE DATA
# =============================================================================

# Gen 3 Move ID to Base PP mapping
# Extracted directly from Pokemon Emerald ROM (offset 0x31C898 + 0x04)
# This is Gen 3 specific - other generations may have different values!
GEN3_MOVE_PP = {
    1: 35, 2: 25, 3: 10, 4: 15, 5: 20, 6: 20, 7: 15, 8: 15, 9: 15, 10: 35,
    11: 30, 12: 5, 13: 10, 14: 30, 15: 30, 16: 35, 17: 35, 18: 20, 19: 15, 20: 20,
    21: 20, 22: 10, 23: 20, 24: 30, 25: 5, 26: 25, 27: 15, 28: 15, 29: 15, 30: 25,
    31: 20, 32: 5, 33: 35, 34: 15, 35: 20, 36: 20, 37: 20, 38: 15, 39: 30, 40: 35,
    41: 20, 42: 20, 43: 30, 44: 25, 45: 40, 46: 20, 47: 15, 48: 20, 49: 20, 50: 20,
    51: 30, 52: 25, 53: 15, 54: 30, 55: 25, 56: 5, 57: 15, 58: 10, 59: 5, 60: 20,
    61: 20, 62: 20, 63: 5, 64: 35, 65: 20, 66: 25, 67: 20, 68: 20, 69: 20, 70: 15,
    71: 20, 72: 10, 73: 10, 74: 40, 75: 25, 76: 10, 77: 35, 78: 30, 79: 15, 80: 20,
    81: 40, 82: 10, 83: 15, 84: 30, 85: 15, 86: 20, 87: 10, 88: 15, 89: 10, 90: 5,
    91: 10, 92: 10, 93: 25, 94: 10, 95: 20, 96: 40, 97: 30, 98: 30, 99: 20, 100: 20,
    101: 15, 102: 10, 103: 40, 104: 15, 105: 20, 106: 30, 107: 20, 108: 20, 109: 10, 110: 40,
    111: 40, 112: 30, 113: 30, 114: 30, 115: 20, 116: 30, 117: 10, 118: 10, 119: 20, 120: 5,
    121: 10, 122: 30, 123: 20, 124: 20, 125: 20, 126: 5, 127: 15, 128: 10, 129: 20, 130: 15,
    131: 15, 132: 35, 133: 20, 134: 15, 135: 10, 136: 20, 137: 30, 138: 15, 139: 40, 140: 20,
    141: 15, 142: 10, 143: 5, 144: 10, 145: 30, 146: 10, 147: 15, 148: 20, 149: 15, 150: 40,
    151: 40, 152: 10, 153: 5, 154: 15, 155: 10, 156: 10, 157: 10, 158: 15, 159: 30, 160: 30,
    161: 10, 162: 10, 163: 20, 164: 10, 165: 1, 166: 1, 167: 10, 168: 10, 169: 10, 170: 5,
    171: 15, 172: 25, 173: 15, 174: 10, 175: 15, 176: 30, 177: 5, 178: 40, 179: 15, 180: 10,
    181: 25, 182: 10, 183: 30, 184: 10, 185: 20, 186: 10, 187: 10, 188: 10, 189: 10, 190: 10,
    191: 20, 192: 5, 193: 40, 194: 5, 195: 5, 196: 15, 197: 5, 198: 10, 199: 5, 200: 15,
    201: 10, 202: 5, 203: 10, 204: 20, 205: 20, 206: 40, 207: 15, 208: 10, 209: 20, 210: 20,
    211: 25, 212: 5, 213: 15, 214: 10, 215: 5, 216: 20, 217: 15, 218: 20, 219: 25, 220: 20,
    221: 5, 222: 30, 223: 5, 224: 10, 225: 20, 226: 40, 227: 5, 228: 20, 229: 40, 230: 20,
    231: 15, 232: 35, 233: 10, 234: 5, 235: 5, 236: 5, 237: 15, 238: 5, 239: 20, 240: 5,
    241: 5, 242: 15, 243: 20, 244: 10, 245: 5, 246: 5, 247: 15, 248: 15, 249: 15, 250: 15,
    251: 10, 252: 10, 253: 10, 254: 10, 255: 10, 256: 10, 257: 10, 258: 10, 259: 15, 260: 15,
    261: 15, 262: 10, 263: 20, 264: 20, 265: 10, 266: 20, 267: 20, 268: 20, 269: 20, 270: 20,
    271: 10, 272: 10, 273: 10, 274: 20, 275: 20, 276: 5, 277: 15, 278: 10, 279: 10, 280: 15,
    281: 10, 282: 20, 283: 5, 284: 5, 285: 10, 286: 10, 287: 20, 288: 5, 289: 10, 290: 20,
    291: 10, 292: 20, 293: 20, 294: 20, 295: 5, 296: 5, 297: 15, 298: 20, 299: 10, 300: 15,
    301: 20, 302: 15, 303: 10, 304: 10, 305: 15, 306: 10, 307: 5, 308: 5, 309: 10, 310: 15,
    311: 10, 312: 5, 313: 20, 314: 25, 315: 5, 316: 40, 317: 10, 318: 5, 319: 40, 320: 15,
    321: 20, 322: 20, 323: 5, 324: 15, 325: 20, 326: 30, 327: 15, 328: 15, 329: 5, 330: 10,
    331: 30, 332: 20, 333: 30, 334: 15, 335: 5, 336: 40, 337: 15, 338: 5, 339: 20, 340: 5,
    341: 15, 342: 25, 343: 40, 344: 15, 345: 20, 346: 15, 347: 20, 348: 15, 349: 20, 350: 10,
    351: 20, 352: 20, 353: 5, 354: 5,
}


# Game name to Gen 3 origin code (stored in misc substructure origins field bits 7-10)
# Values per PKHeX GameVersion enum
GAME_ORIGIN_CODES = {
    "ruby":      1,
    "sapphire":  2,
    "firered":   4,
    "leafgreen": 5,
    "emerald":   8,
}

# Reverse: origin code -> display name
ORIGIN_CODE_TO_NAME = {v: k.title() for k, v in GAME_ORIGIN_CODES.items()}
# e.g. {1: "Ruby", 2: "Sapphire", 4: "Firered", 5: "Leafgreen", 8: "Emerald"}
# Fix capitalisation for multi-word names
ORIGIN_CODE_TO_NAME[4] = "FireRed"
ORIGIN_CODE_TO_NAME[5] = "LeafGreen"

# Keyword map for fuzzy matching full game name strings
# e.g. "Pokemon FireRed Version" -> "firered" -> 4
# Order matters: specific names before short ones to avoid false matches
_GAME_NAME_KEYWORDS = [
    ("firered",    "firered"),
    ("fire red",   "firered"),
    ("leafgreen",  "leafgreen"),
    ("leaf green", "leafgreen"),
    ("emerald",    "emerald"),
    ("sapphire",   "sapphire"),
    ("ruby",       "ruby"),
]

def game_name_to_origin_code(game_name: str) -> int:
    """
    Convert a game name string to its Gen 3 origin code.
    Handles full strings like 'Pokemon FireRed Version' and short forms like 'firered'.
    """
    lowered = game_name.lower()
    _SHORT = set(GAME_ORIGIN_CODES.keys())
    if lowered in _SHORT:
        return GAME_ORIGIN_CODES[lowered]
    for keyword, key in _GAME_NAME_KEYWORDS:
        if keyword in lowered:
            return GAME_ORIGIN_CODES[key]
    return GAME_ORIGIN_CODES["emerald"]  # Default

def origin_code_to_game_name(code: int) -> str:
    """Convert a Gen 3 origin code back to a display name."""
    return ORIGIN_CODE_TO_NAME.get(code, "Unknown")


def get_gen3_base_pp(move_id: int, game: str = "emerald") -> int:
    """
    Get base PP for a Gen 3 move from ROM data.
    
    Args:
        move_id: Move ID (1-354 for Gen 3)
        game: Game name ("emerald", "ruby", "sapphire", "firered", "leafgreen")
        
    Returns:
        Base PP value (defaults to 10 if unknown)
    """
    try:
        from rom_data_loader import get_move_pp
        return get_move_pp(game, move_id)
    except (ImportError, Exception):
        # Fallback to hardcoded table if ROM data not available
        return GEN3_MOVE_PP.get(move_id, 10)


# =============================================================================
# GEN 3 → UNIVERSAL POKEMON
# =============================================================================

def gen3_to_universal(pokemon_bytes: bytes, game_name: str = "Emerald") -> UniversalPokemon:
    """
    Convert Gen 3 Pokemon bytes (80 or 100 bytes) to Universal Pokemon Object.
    
    Args:
        pokemon_bytes: 80 bytes (PC format) or 100 bytes (party format)
        game_name: Game of origin (e.g., "Emerald", "FireRed", "Ruby")
        
    Returns:
        UniversalPokemon: Converted Pokemon object
    """
    if len(pokemon_bytes) not in (80, 100):
        raise ValueError(f"Invalid Pokemon data length: {len(pokemon_bytes)}")
    
    # Read unencrypted header (first 32 bytes)
    pid = struct.unpack("<I", pokemon_bytes[0:4])[0]
    ot_id = struct.unpack("<I", pokemon_bytes[4:8])[0]
    
    # Split OT ID into TID and SID
    tid = ot_id & 0xFFFF
    sid = (ot_id >> 16) & 0xFFFF
    
    # Decode nickname (10 bytes)
    nickname_bytes = pokemon_bytes[8:18]
    nickname = decode_gen3_text(nickname_bytes)
    
    # Language (2 bytes)
    language = struct.unpack("<H", pokemon_bytes[18:20])[0]
    
    # OT Name (7 bytes)
    ot_name_bytes = pokemon_bytes[20:27]
    ot_name = decode_gen3_text(ot_name_bytes)
    
    # Markings (1 byte)
    markings = pokemon_bytes[27]
    
    # Checksum (2 bytes) - stored but we'll recalculate for validation
    stored_checksum = struct.unpack("<H", pokemon_bytes[28:30])[0]
    
    # Decrypt the 48-byte encrypted section
    encrypted_data = pokemon_bytes[32:80]
    
    # Handle both parser signature (data, pid, ot_id) and fallback signature (data, key)
    try:
        if PARSER_AVAILABLE:
            decrypted_data = decrypt_pokemon_data(encrypted_data, pid, ot_id)
        else:
            key = pid ^ ot_id
            decrypted_data = decrypt_pokemon_data(encrypted_data, key)
    except TypeError:
        # Fallback if signature mismatch
        key = pid ^ ot_id
        decrypted_data = decrypt_pokemon_data(encrypted_data, key)
    
    # Verify checksum
    calculated_checksum = calculate_pokemon_checksum(decrypted_data)
    if calculated_checksum != stored_checksum:
        print(f"[Gen3Converter] Warning: Checksum mismatch "
              f"(stored=0x{stored_checksum:04X}, calculated=0x{calculated_checksum:04X})")
    
    # Get block order from PID
    block_order = get_block_order(pid)
    
    # Parse substructures based on block order
    # Block types: 0=Growth, 1=Attacks, 2=EVs, 3=Misc
    # block_order is a SOURCE MAP: block_order[position] = block_type
    # We need to FIND which position contains each block type
    
    # Find positions of each block type
    growth_pos = block_order[0]  # Growth block position
    attacks_pos = block_order[1]  # Attacks block position
    evs_pos = block_order[2]  # EVs block position
    misc_pos = block_order[3]  # Misc block position
    
    # --- Growth Block (12 bytes) ---
    growth_offset = growth_pos * 12
    growth_block = decrypted_data[growth_offset:growth_offset + 12]
    
    species_internal = struct.unpack("<H", growth_block[0:2])[0]
    species_national = convert_species_to_national(species_internal)
    held_item = struct.unpack("<H", growth_block[2:4])[0]
    experience = struct.unpack("<I", growth_block[4:8])[0]
    pp_bonuses = growth_block[8]
    friendship = growth_block[9]
    
    # --- Attacks Block (12 bytes) ---
    attacks_offset = attacks_pos * 12
    attacks_block = decrypted_data[attacks_offset:attacks_offset + 12]
    
    moves = []
    for i in range(4):
        move_id = struct.unpack("<H", attacks_block[i*2:i*2+2])[0]
        pp_raw = attacks_block[8 + i]
        # PP byte format: lower 6 bits = current PP (bits 0-5)
        # In PC format, upper 2 bits may contain garbage or duplicate PP Up data
        # Always mask to get clean PP value
        pp = pp_raw & 0x3F  # Extract lower 6 bits only
        # PP-ups stored in pp_bonuses (2 bits per move)
        pp_ups = (pp_bonuses >> (i * 2)) & 0x3
        
        if move_id > 0:
            moves.append(MoveSlot(move_id=move_id, pp=pp, pp_ups=pp_ups))
        else:
            moves.append(None)
    
    # --- EVs/Condition Block (12 bytes) ---
    evs_offset = evs_pos * 12
    evs_block = decrypted_data[evs_offset:evs_offset + 12]
    
    evs = EVSet(
        hp=evs_block[0],
        attack=evs_block[1],
        defense=evs_block[2],
        speed=evs_block[3],
        sp_attack=evs_block[4],
        sp_defense=evs_block[5]
    )
    
    contest = ContestStats(
        cool=evs_block[6],
        beauty=evs_block[7],
        cute=evs_block[8],
        smart=evs_block[9],
        tough=evs_block[10],
        sheen=evs_block[11]
    )
    
    # --- Misc Block (12 bytes) ---
    misc_offset = misc_pos * 12
    misc_block = decrypted_data[misc_offset:misc_offset + 12]
    
    pokerus = misc_block[0]
    met_location = misc_block[1]
    
    # Origins info (2 bytes at offset 2-3)
    origins = struct.unpack("<H", misc_block[2:4])[0]
    met_level = origins & 0x7F
    game_of_origin = (origins >> 7) & 0xF
    pokeball = (origins >> 11) & 0xF
    ot_gender = (origins >> 15) & 0x1
    
    # IVs, Egg, Ability packed in 4 bytes at offset 4-7
    iv_egg_ability = struct.unpack("<I", misc_block[4:8])[0]
    
    ivs = IVSet(
        hp=(iv_egg_ability >> 0) & 0x1F,
        attack=(iv_egg_ability >> 5) & 0x1F,
        defense=(iv_egg_ability >> 10) & 0x1F,
        speed=(iv_egg_ability >> 15) & 0x1F,
        sp_attack=(iv_egg_ability >> 20) & 0x1F,
        sp_defense=(iv_egg_ability >> 25) & 0x1F
    )
    
    is_egg = bool((iv_egg_ability >> 30) & 0x1)
    ability_slot = (iv_egg_ability >> 31) & 0x1
    
    # Ribbons (4 bytes at offset 8-11)
    ribbons_data = struct.unpack("<I", misc_block[8:12])[0]
    ribbons = []
    for i in range(32):
        if ribbons_data & (1 << i):
            ribbons.append(i)
    
    # Derive nature and gender from PID
    nature = get_pokemon_nature(pid)
    
    # Gender calculation (requires species gender ratio - we'll leave as None for now)
    # This should be calculated by looking up species data
    gender = None
    
    # Check if shiny
    is_shiny_flag = is_shiny(pid, tid, sid)
    
    # Parse battle stats if party format (100 bytes)
    current_hp = 0
    stats = StatSet()
    status_condition = 0
    
    if len(pokemon_bytes) == 100:
        # Battle stats start at offset 80
        status_condition = struct.unpack("<I", pokemon_bytes[80:84])[0]
        level = struct.unpack("<B", pokemon_bytes[84:85])[0]
        current_hp = struct.unpack("<H", pokemon_bytes[88:90])[0]
        
        stats = StatSet(
            hp=struct.unpack("<H", pokemon_bytes[90:92])[0],
            attack=struct.unpack("<H", pokemon_bytes[92:94])[0],
            defense=struct.unpack("<H", pokemon_bytes[94:96])[0],
            speed=struct.unpack("<H", pokemon_bytes[96:98])[0],
            sp_attack=struct.unpack("<H", pokemon_bytes[98:100])[0],
            sp_defense=struct.unpack("<H", pokemon_bytes[100:102])[0] if len(pokemon_bytes) >= 102 else 0
        )
    else:
        # PC format - level must be calculated from experience
        # For now, we'll estimate it
        level = _estimate_level_from_exp(species_national, experience)
    
    # Build Universal Pokemon Object
    pokemon = UniversalPokemon(
        # Identity
        species=species_national,
        form=None,  # Gen 3 forms are mostly handled via species ID
        nickname=nickname,
        language=language,
        gender=gender,
        is_egg=is_egg,
        is_shiny=is_shiny_flag,
        
        # Trainer
        ot_name=ot_name,
        tid=tid,
        sid=sid,
        ot_gender=ot_gender,
        
        # Growth
        level=level,
        experience=experience,
        friendship=friendship,
        
        # Battle
        nature=nature,
        ability=None,  # Need species data to determine actual ability
        ability_slot=ability_slot,
        held_item=held_item if held_item > 0 else None,
        
        # Genetics
        pid=pid,
        ivs=ivs,
        evs=evs,
        
        # Moves
        moves=moves,
        
        # Stats
        stats=stats,
        current_hp=current_hp,
        
        # Status
        status_condition=status_condition,
        pokerus=pokerus,
        
        # Encounter
        met_location=met_location if met_location > 0 else None,
        met_level=met_level if met_level > 0 else None,
        met_game=game_name,
        pokeball=pokeball if pokeball > 0 else None,
        
        # Cosmetic
        markings=markings,
        ribbons=ribbons,
        contest_stats=contest,
        
        # Metadata
        origin_generation=3,
        # Derive origin_game from the actual code in the bytes, fall back to game_name param
        origin_game=origin_code_to_game_name(game_of_origin) if game_of_origin != 0 else game_name,
        
        # Raw data (preserve original bytes for lossless conversion)
        raw_data={
            "gen3_original_bytes": pokemon_bytes.hex(),
            "species_internal": species_internal,
            "game_of_origin_code": game_of_origin,
            "pp_bonuses": pp_bonuses,
        }
    )
    
    return pokemon


# =============================================================================
# UNIVERSAL POKEMON → GEN 3
# =============================================================================

def universal_to_gen3(pokemon: UniversalPokemon, format: str = "pc") -> bytes:
    """
    Convert Universal Pokemon Object to Gen 3 bytes.
    
    Args:
        pokemon: UniversalPokemon object
        format: "pc" (80 bytes) or "party" (100 bytes)
        
    Returns:
        bytes: Gen 3 Pokemon data
    """
    if format not in ("pc", "party"):
        raise ValueError(f"Invalid format: {format} (must be 'pc' or 'party')")
    
    # Validate we have minimum required data
    if pokemon.pid is None:
        raise ValueError("Cannot convert to Gen 3 without PID")
    if pokemon.species == 0:
        raise ValueError("Cannot convert to Gen 3 without species")
    
    # Convert national to internal species ID
    species_internal = convert_species_to_internal(pokemon.species)
    
    # Build 80-byte Pokemon structure
    data = bytearray(80 if format == "pc" else 100)
    
    # Reconstruct OT ID from TID and SID
    ot_id = (pokemon.tid & 0xFFFF) | ((pokemon.sid or 0) << 16)
    
    # --- Header (32 bytes) ---
    struct.pack_into("<I", data, 0, pokemon.pid)
    struct.pack_into("<I", data, 4, ot_id)
    
    # Nickname
    nickname_bytes = encode_gen3_text(pokemon.nickname, 10)
    data[8:18] = nickname_bytes
    
    # Language
    struct.pack_into("<H", data, 18, pokemon.language)
    
    # OT Name
    ot_bytes = encode_gen3_text(pokemon.ot_name, 7)
    data[20:27] = ot_bytes
    
    # Markings
    data[27] = pokemon.markings
    
    # Checksum placeholder (will calculate later)
    # data[28:30] = checksum
    
    # --- Build Substructures (48 bytes) ---
    
    # Growth block (12 bytes)
    growth = bytearray(12)
    struct.pack_into("<H", growth, 0, species_internal)
    struct.pack_into("<H", growth, 2, pokemon.held_item or 0)
    struct.pack_into("<I", growth, 4, pokemon.experience)
    
    # PP bonuses (2 bits per move)
    pp_bonuses = 0
    for i, move in enumerate(pokemon.moves[:4]):
        if move:
            pp_bonuses |= (move.pp_ups & 0x3) << (i * 2)
    growth[8] = pp_bonuses
    growth[9] = pokemon.friendship
    
    # Attacks block (12 bytes)
    attacks = bytearray(12)
    for i in range(4):
        move = pokemon.moves[i] if i < len(pokemon.moves) else None
        if move:
            struct.pack_into("<H", attacks, i * 2, move.move_id)
            # Write PP cleanly - mask to ensure only lower 6 bits used
            # If PP not set in UPO, use Gen 3 base PP for the move
            if move.pp is None or move.pp == 0:
                pp_value = get_gen3_base_pp(move.move_id)
            else:
                pp_value = move.pp
            attacks[8 + i] = pp_value & 0x3F
        else:
            struct.pack_into("<H", attacks, i * 2, 0)
            attacks[8 + i] = 0
    
    # EVs/Condition block (12 bytes)
    evs_block = bytearray(12)
    evs_block[0] = pokemon.evs.hp
    evs_block[1] = pokemon.evs.attack
    evs_block[2] = pokemon.evs.defense
    evs_block[3] = pokemon.evs.speed
    evs_block[4] = pokemon.evs.sp_attack
    evs_block[5] = pokemon.evs.sp_defense
    
    evs_block[6] = pokemon.contest_stats.cool
    evs_block[7] = pokemon.contest_stats.beauty
    evs_block[8] = pokemon.contest_stats.cute
    evs_block[9] = pokemon.contest_stats.smart
    evs_block[10] = pokemon.contest_stats.tough
    evs_block[11] = pokemon.contest_stats.sheen
    
    # Misc block (12 bytes)
    misc = bytearray(12)
    misc[0] = pokemon.pokerus
    misc[1] = pokemon.met_location or 0
    
    # Origins info
    origins = (
        (pokemon.met_level or 0) |
        (pokemon.raw_data.get("game_of_origin_code", 0) << 7) |
        ((pokemon.pokeball or 0) << 11) |
        ((pokemon.ot_gender or 0) << 15)
    )
    struct.pack_into("<H", misc, 2, origins)
    
    # IVs, Egg, Ability
    # CRITICAL: Ability slot MUST match PID lowest bit in Gen 3
    # Always derive from PID, ignore pokemon.ability_slot (which might be None or wrong)
    ability_slot_from_pid = pokemon.pid & 1
    
    iv_egg_ability = (
        (pokemon.ivs.hp & 0x1F) |
        ((pokemon.ivs.attack & 0x1F) << 5) |
        ((pokemon.ivs.defense & 0x1F) << 10) |
        ((pokemon.ivs.speed & 0x1F) << 15) |
        ((pokemon.ivs.sp_attack & 0x1F) << 20) |
        ((pokemon.ivs.sp_defense & 0x1F) << 25) |
        ((1 if pokemon.is_egg else 0) << 30) |
        (ability_slot_from_pid << 31)
    )
    struct.pack_into("<I", misc, 4, iv_egg_ability)
    
    # Ribbons
    ribbons_value = 0
    for ribbon_id in pokemon.ribbons:
        if 0 <= ribbon_id < 32:
            ribbons_value |= (1 << ribbon_id)
    struct.pack_into("<I", misc, 8, ribbons_value)
    
    # --- Arrange blocks according to PID ---
    block_order = get_block_order(pokemon.pid)
    blocks = [growth, attacks, evs_block, misc]
    
    # Create ordered decrypted data
    # block_order format: block_order[TYPE] = POSITION
    # So block_order[0] tells us which position Growth goes to
    decrypted = bytearray(48)
    for block_type, position in enumerate(block_order):
        decrypted[position*12:(position+1)*12] = blocks[block_type]
    
    # Calculate checksum BEFORE encryption
    checksum = calculate_pokemon_checksum(bytes(decrypted))
    struct.pack_into("<H", data, 28, checksum)
    
    # Encrypt the data
    # Handle both parser signature (data, pid, ot_id) and fallback signature (data, key)
    try:
        if PARSER_AVAILABLE:
            encrypted = encrypt_pokemon_data(bytes(decrypted), pokemon.pid, ot_id)
        else:
            key = pokemon.pid ^ ot_id
            encrypted = encrypt_pokemon_data(bytes(decrypted), key)
    except TypeError:
        key = pokemon.pid ^ ot_id
        encrypted = encrypt_pokemon_data(bytes(decrypted), key)
    data[32:80] = encrypted
    
    # --- Add party stats if party format ---
    if format == "party":
        struct.pack_into("<I", data, 80, pokemon.status_condition)
        struct.pack_into("<B", data, 84, pokemon.level)
        struct.pack_into("<B", data, 85, pokemon.pokerus)  # Duplicate pokerus
        struct.pack_into("<H", data, 86, pokemon.current_hp)
        struct.pack_into("<H", data, 88, pokemon.stats.hp)
        struct.pack_into("<H", data, 90, pokemon.stats.attack)
        struct.pack_into("<H", data, 92, pokemon.stats.defense)
        struct.pack_into("<H", data, 94, pokemon.stats.speed)
        struct.pack_into("<H", data, 96, pokemon.stats.sp_attack)
        struct.pack_into("<H", data, 98, pokemon.stats.sp_defense)
    
    return bytes(data)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _estimate_level_from_exp(species: int, experience: int) -> int:
    """
    Estimate level from experience (simplified).
    
    For accurate calculation, you'd need to import EXP_TABLES from parser.constants
    and use calculate_level_from_exp.
    
    Args:
        species: National Dex number
        experience: Experience points
        
    Returns:
        int: Estimated level (1-100)
    """
    # Very rough estimate (assumes Medium Fast growth rate)
    if experience == 0:
        return 1
    if experience >= 1000000:
        return 100
    
    # Simple polynomial approximation
    level = int((experience / 10000) ** 0.33 * 10)
    return max(1, min(100, level))


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Round-trip conversion
    print("=== Gen 3 Converter Test ===\n")
    
    # Create a test Pokemon
    test_pokemon = UniversalPokemon(
        species=25,  # Pikachu
        nickname="PIKACHU",
        level=50,
        experience=125000,
        tid=12345,
        sid=54321,
        pid=0x12345678,
        ot_name="ASH",
        nature=3,
        ivs=IVSet(hp=31, attack=25, defense=20, sp_attack=30, sp_defense=28, speed=31),
        evs=EVSet(attack=252, speed=252, sp_attack=4),
        friendship=255,
        origin_generation=3,
        origin_game="Emerald"
    )
    
    test_pokemon.moves[0] = MoveSlot(move_id=85, pp=15, pp_ups=3)  # Thunderbolt
    
    print("Original Pokemon:")
    print(f"  Species: {test_pokemon.species}")
    print(f"  Level: {test_pokemon.level}")
    print(f"  PID: 0x{test_pokemon.pid:08X}")
    print(f"  Nature: {test_pokemon.nature}")
    
    # Convert to Gen 3
    print("\nConverting to Gen 3 bytes...")
    gen3_bytes = universal_to_gen3(test_pokemon, format="pc")
    print(f"  Generated {len(gen3_bytes)} bytes")
    print(f"  First 8 bytes (PID + OT_ID): {gen3_bytes[:8].hex()}")
    
    # Convert back
    print("\nConverting back to Universal...")
    recovered = gen3_to_universal(gen3_bytes, "Emerald")
    print(f"  Species: {recovered.species}")
    print(f"  Level: {recovered.level}")
    print(f"  PID: 0x{recovered.pid:08X}")
    print(f"  Nature: {recovered.nature}")
    
    # Validate
    errors = recovered.validate_consistency()
    print(f"\nValidation: {'PASS' if not errors else 'FAIL'}")
    if errors:
        for error in errors:
            print(f"  - {error}")