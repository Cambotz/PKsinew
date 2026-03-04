#!/usr/bin/env python3

"""
Gen 3 Parser Extensions
Adds box name parsing and contest data parsing
"""

import struct


def decode_gen3_text(text_bytes):
    """Decode Gen 3 text encoding to string"""
    # Gen 3 byte->char table (Western/English encoding, based on Bulbapedia)
    GEN3_CHARS = {
        0x00: " ",
        # Hiragana (0x01-0x50)
        0x01: "あ", 0x02: "い", 0x03: "う", 0x04: "え", 0x05: "お",
        0x06: "か", 0x07: "き", 0x08: "く", 0x09: "け", 0x0A: "こ",
        0x0B: "さ", 0x0C: "し", 0x0D: "す", 0x0E: "せ", 0x0F: "そ",
        0x10: "た", 0x11: "ち", 0x12: "つ", 0x13: "て", 0x14: "と",
        0x15: "な", 0x16: "に", 0x17: "ぬ", 0x18: "ね", 0x19: "の",
        0x1A: "は", 0x1B: "ひ", 0x1C: "ふ", 0x1D: "へ", 0x1E: "ほ",
        0x1F: "ま", 0x20: "み", 0x21: "む", 0x22: "め", 0x23: "も",
        0x24: "や", 0x25: "ゆ", 0x26: "よ",
        0x27: "ら", 0x28: "り", 0x29: "る", 0x2A: "れ", 0x2B: "ろ",
        0x2C: "わ", 0x2D: "を", 0x2E: "ん",
        0x2F: "ぁ", 0x30: "ぃ", 0x31: "ぅ", 0x32: "ぇ", 0x33: "ぉ",
        0x34: "ゃ", 0x35: "ゅ", 0x36: "ょ",
        0x37: "が", 0x38: "ぎ", 0x39: "ぐ", 0x3A: "げ", 0x3B: "ご",
        0x3C: "ざ", 0x3D: "じ", 0x3E: "ず", 0x3F: "ぜ", 0x40: "ぞ",
        0x41: "だ", 0x42: "ぢ", 0x43: "づ", 0x44: "で", 0x45: "ど",
        0x46: "ば", 0x47: "び", 0x48: "ぶ", 0x49: "べ", 0x4A: "ぼ",
        0x4B: "ぱ", 0x4C: "ぴ", 0x4D: "ぷ", 0x4E: "ぺ", 0x4F: "ぽ",
        0x50: "っ",
        # Katakana (0x51-0xA0)
        0x51: "ア", 0x52: "イ", 0x53: "ウ", 0x54: "エ", 0x55: "オ",
        0x56: "カ", 0x57: "キ", 0x58: "ク", 0x59: "ケ", 0x5A: "コ",
        0x5B: "サ", 0x5C: "シ", 0x5D: "ス", 0x5E: "セ", 0x5F: "ソ",
        0x60: "タ", 0x61: "チ", 0x62: "ツ", 0x63: "テ", 0x64: "ト",
        0x65: "ナ", 0x66: "ニ", 0x67: "ヌ", 0x68: "ネ", 0x69: "ノ",
        0x6A: "ハ", 0x6B: "ヒ", 0x6C: "フ", 0x6D: "ヘ", 0x6E: "ホ",
        0x6F: "マ", 0x70: "ミ", 0x71: "ム", 0x72: "メ", 0x73: "モ",
        0x74: "ヤ", 0x75: "ユ", 0x76: "ヨ",
        0x77: "ラ", 0x78: "リ", 0x79: "ル", 0x7A: "レ", 0x7B: "ロ",
        0x7C: "ワ", 0x7D: "ヲ", 0x7E: "ン",
        0x7F: "ァ", 0x80: "ィ", 0x81: "ゥ", 0x82: "ェ", 0x83: "ォ",
        0x84: "ャ", 0x85: "ュ", 0x86: "ョ",
        0x87: "ガ", 0x88: "ギ", 0x89: "グ", 0x8A: "ゲ", 0x8B: "ゴ",
        0x8C: "ザ", 0x8D: "ジ", 0x8E: "ズ", 0x8F: "ゼ", 0x90: "ゾ",
        0x91: "ダ", 0x92: "ヂ", 0x93: "ヅ", 0x94: "デ", 0x95: "ド",
        0x96: "バ", 0x97: "ビ", 0x98: "ブ", 0x99: "ベ", 0x9A: "ボ",
        0x9B: "パ", 0x9C: "ピ", 0x9D: "プ", 0x9E: "ペ", 0x9F: "ポ",
        0xA0: "ッ",
        # Numbers (0xA1-0xAA) - ASCII digits in Western encoding
        0xA1: "0", 0xA2: "1", 0xA3: "2", 0xA4: "3", 0xA5: "4",
        0xA6: "5", 0xA7: "6", 0xA8: "7", 0xA9: "8", 0xAA: "9",
        # Punctuation and symbols
        0xAB: "!", 0xAC: "?", 0xAD: ".", 0xAE: "-", 0xAF: "·",
        0xB0: "…",   # ellipsis
        0xB1: "“",   # left double quote
        0xB2: "”",   # right double quote
        0xB3: "‘",   # left single quote
        0xB4: "’",   # right single quote / apostrophe
        0xB5: "♂", 0xB6: "♀",  # male, female
        0xB7: "$",        # Pokemon Dollar
        0xB8: ",", 0xB9: "×", 0xBA: "/",
        # Uppercase letters (0xBB-0xD4)
        **{0xBB + i: chr(ord("A") + i) for i in range(26)},
        # Lowercase letters (0xD5-0xEE)
        **{0xD5 + i: chr(ord("a") + i) for i in range(26)},
        # Extra symbols
        0xEF: "►",   # filled right-pointing arrow
        0xF0: ":",
    }

    result = []
    for byte in text_bytes:
        if byte == 0xFF:  # Terminator
            break
        char = GEN3_CHARS.get(byte, "")
        result.append(char)

    return "".join(result).strip()


# Default box names for Gen 3
DEFAULT_BOX_NAMES = [
    "BOX 1",
    "BOX 2",
    "BOX 3",
    "BOX 4",
    "BOX 5",
    "BOX 6",
    "BOX 7",
    "BOX 8",
    "BOX 9",
    "BOX 10",
    "BOX 11",
    "BOX 12",
    "BOX 13",
    "BOX 14",
]


def parse_box_names(data, section_offsets):
    """
    Parse PC box names from save data.

    Box names are stored in the PC buffer after all Pokemon data.
    PC buffer layout:
    - Offset 0x0000: Current box (4 bytes)
    - Offset 0x0004: 420 Pokemon × 80 bytes = 33600 bytes
    - Offset 0x8344: Box names (14 boxes × 9 bytes = 126 bytes)
    - Offset 0x83C2: Box wallpapers (14 bytes)

    Args:
        data: Save file data
        section_offsets: Dict mapping section ID to offset

    Returns:
        list: 14 box names (strings)
    """
    # Build contiguous PC buffer from sections 5-13
    pc_buffer = bytearray()

    for section_id in range(5, 14):
        if section_id not in section_offsets:
            return DEFAULT_BOX_NAMES.copy()

        offset = section_offsets[section_id]
        size = 3968 if section_id <= 12 else 2000
        section_data = data[offset : offset + size]
        pc_buffer.extend(section_data)

    # Box names start at offset 0x8344 in the PC buffer
    # 4 (current box) + 420*80 (pokemon) = 33604 = 0x8344
    BOX_NAMES_OFFSET = 0x8344
    BOX_NAME_LENGTH = 9  # 8 chars + terminator

    box_names = []

    for box_num in range(14):
        name_offset = BOX_NAMES_OFFSET + (box_num * BOX_NAME_LENGTH)

        if name_offset + BOX_NAME_LENGTH > len(pc_buffer):
            box_names.append(f"BOX {box_num + 1}")
            continue

        name_bytes = pc_buffer[name_offset : name_offset + BOX_NAME_LENGTH]
        name = decode_gen3_text(name_bytes)

        # Use default if empty or invalid
        if not name or len(name.strip()) == 0:
            name = f"BOX {box_num + 1}"

        box_names.append(name)

    return box_names


def parse_contest_stats(decrypted_data, evs_start):
    """
    Parse contest stats from the EVs block.

    Contest stats are stored in the EVs block at bytes 6-11:
    - Byte 6: Coolness
    - Byte 7: Beauty
    - Byte 8: Cuteness
    - Byte 9: Smartness
    - Byte 10: Toughness
    - Byte 11: Feel (Sheen)

    Args:
        decrypted_data: Decrypted 48-byte Pokemon substructure
        evs_start: Start offset of EVs block

    Returns:
        dict: Contest stats
    """
    return {
        "cool": (
            decrypted_data[evs_start + 6] if evs_start + 6 < len(decrypted_data) else 0
        ),
        "beauty": (
            decrypted_data[evs_start + 7] if evs_start + 7 < len(decrypted_data) else 0
        ),
        "cute": (
            decrypted_data[evs_start + 8] if evs_start + 8 < len(decrypted_data) else 0
        ),
        "smart": (
            decrypted_data[evs_start + 9] if evs_start + 9 < len(decrypted_data) else 0
        ),
        "tough": (
            decrypted_data[evs_start + 10]
            if evs_start + 10 < len(decrypted_data)
            else 0
        ),
        "sheen": (
            decrypted_data[evs_start + 11]
            if evs_start + 11 < len(decrypted_data)
            else 0
        ),
    }


def parse_ribbons(decrypted_data, misc_start):
    """
    Parse ribbon data from the Misc block.

    Ribbons are stored in bytes 8-11 of the Misc block as bit flags.

    Args:
        decrypted_data: Decrypted 48-byte Pokemon substructure
        misc_start: Start offset of Misc block

    Returns:
        dict: Ribbon flags
    """
    if misc_start + 11 >= len(decrypted_data):
        return {}

    ribbon_data = struct.unpack("<I", decrypted_data[misc_start + 8 : misc_start + 12])[
        0
    ]

    # Contest ribbons (3 bits each for rank: None/Normal/Super/Hyper/Master)
    cool_ribbon = ribbon_data & 0x7
    beauty_ribbon = (ribbon_data >> 3) & 0x7
    cute_ribbon = (ribbon_data >> 6) & 0x7
    smart_ribbon = (ribbon_data >> 9) & 0x7
    tough_ribbon = (ribbon_data >> 12) & 0x7

    # Champion ribbon is bit 15
    champion_ribbon = bool(ribbon_data & 0x8000)

    # Winning ribbon is bit 16
    winning_ribbon = bool(ribbon_data & 0x10000)

    # Victory ribbon is bit 17
    victory_ribbon = bool(ribbon_data & 0x20000)

    # Artist ribbon is bit 18
    artist_ribbon = bool(ribbon_data & 0x40000)

    # Effort ribbon is bit 19
    effort_ribbon = bool(ribbon_data & 0x80000)

    RIBBON_RANKS = ["None", "Normal", "Super", "Hyper", "Master"]

    return {
        "cool": (
            RIBBON_RANKS[cool_ribbon] if cool_ribbon < len(RIBBON_RANKS) else "None"
        ),
        "beauty": (
            RIBBON_RANKS[beauty_ribbon] if beauty_ribbon < len(RIBBON_RANKS) else "None"
        ),
        "cute": (
            RIBBON_RANKS[cute_ribbon] if cute_ribbon < len(RIBBON_RANKS) else "None"
        ),
        "smart": (
            RIBBON_RANKS[smart_ribbon] if smart_ribbon < len(RIBBON_RANKS) else "None"
        ),
        "tough": (
            RIBBON_RANKS[tough_ribbon] if tough_ribbon < len(RIBBON_RANKS) else "None"
        ),
        "champion": champion_ribbon,
        "winning": winning_ribbon,
        "victory": victory_ribbon,
        "artist": artist_ribbon,
        "effort": effort_ribbon,
    }


def get_obedience_level(badge_count, game_type="RSE"):
    """
    Get the maximum level a Pokemon will obey based on badge count.

    Args:
        badge_count: Number of badges (0-8)
        game_type: 'RSE' or 'FRLG'

    Returns:
        int: Maximum obedient level
    """
    # Obedience levels by badge count
    # Traded Pokemon won't obey if their level exceeds this
    if game_type == "FRLG":
        # FireRed/LeafGreen
        OBEDIENCE_LEVELS = {
            0: 10,  # No badges
            1: 20,  # Boulder Badge
            2: 30,  # Cascade Badge
            3: 40,  # Thunder Badge
            4: 50,  # Rainbow Badge
            5: 60,  # Soul Badge
            6: 70,  # Marsh Badge
            7: 80,  # Volcano Badge
            8: 100,  # Earth Badge - all levels
        }
    else:
        # Ruby/Sapphire/Emerald
        OBEDIENCE_LEVELS = {
            0: 10,  # No badges
            1: 20,  # Stone Badge
            2: 30,  # Knuckle Badge
            3: 40,  # Dynamo Badge
            4: 50,  # Heat Badge
            5: 60,  # Balance Badge
            6: 70,  # Feather Badge
            7: 80,  # Mind Badge
            8: 100,  # Rain Badge - all levels
        }

    return OBEDIENCE_LEVELS.get(badge_count, 10)


def check_obedience(pokemon_level, badge_count, game_type="RSE"):
    """
    Check if a Pokemon will obey based on level and badges.

    Args:
        pokemon_level: Level of the Pokemon
        badge_count: Number of badges trainer has
        game_type: 'RSE' or 'FRLG'

    Returns:
        tuple: (will_obey: bool, max_level: int)
    """
    max_level = get_obedience_level(badge_count, game_type)
    will_obey = pokemon_level <= max_level
    return will_obey, max_level