"""
Gen 3 Parser Extensions
Adds box name parsing and contest data parsing
"""

import struct


def decode_gen3_text(text_bytes):
    """Decode Gen 3 text encoding to string"""
    # Gen 3 character table (common characters)
    GEN3_CHARS = {
        0x00: ' ', 0xAB: '!', 0xAC: '?', 0xAD: '.', 0xAE: '-',
        0xB5: '♂', 0xB6: '♀', 0xBB: 'A', 0xBC: 'B', 0xBD: 'C',
        0xBE: 'D', 0xBF: 'E', 0xC0: 'F', 0xC1: 'G', 0xC2: 'H',
        0xC3: 'I', 0xC4: 'J', 0xC5: 'K', 0xC6: 'L', 0xC7: 'M',
        0xC8: 'N', 0xC9: 'O', 0xCA: 'P', 0xCB: 'Q', 0xCC: 'R',
        0xCD: 'S', 0xCE: 'T', 0xCF: 'U', 0xD0: 'V', 0xD1: 'W',
        0xD2: 'X', 0xD3: 'Y', 0xD4: 'Z', 0xD5: 'a', 0xD6: 'b',
        0xD7: 'c', 0xD8: 'd', 0xD9: 'e', 0xDA: 'f', 0xDB: 'g',
        0xDC: 'h', 0xDD: 'i', 0xDE: 'j', 0xDF: 'k', 0xE0: 'l',
        0xE1: 'm', 0xE2: 'n', 0xE3: 'o', 0xE4: 'p', 0xE5: 'q',
        0xE6: 'r', 0xE7: 's', 0xE8: 't', 0xE9: 'u', 0xEA: 'v',
        0xEB: 'w', 0xEC: 'x', 0xED: 'y', 0xEE: 'z', 0xF1: '0',
        0xF2: '1', 0xF3: '2', 0xF4: '3', 0xF5: '4', 0xF6: '5',
        0xF7: '6', 0xF8: '7', 0xF9: '8', 0xFA: '9', 0xFF: '',
    }
    
    result = []
    for byte in text_bytes:
        if byte == 0xFF:  # Terminator
            break
        char = GEN3_CHARS.get(byte, '')
        result.append(char)
    
    return ''.join(result).strip()


# Default box names for Gen 3
DEFAULT_BOX_NAMES = [
    "BOX 1", "BOX 2", "BOX 3", "BOX 4", "BOX 5",
    "BOX 6", "BOX 7", "BOX 8", "BOX 9", "BOX 10",
    "BOX 11", "BOX 12", "BOX 13", "BOX 14"
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
        section_data = data[offset:offset + size]
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
        
        name_bytes = pc_buffer[name_offset:name_offset + BOX_NAME_LENGTH]
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
        'cool': decrypted_data[evs_start + 6] if evs_start + 6 < len(decrypted_data) else 0,
        'beauty': decrypted_data[evs_start + 7] if evs_start + 7 < len(decrypted_data) else 0,
        'cute': decrypted_data[evs_start + 8] if evs_start + 8 < len(decrypted_data) else 0,
        'smart': decrypted_data[evs_start + 9] if evs_start + 9 < len(decrypted_data) else 0,
        'tough': decrypted_data[evs_start + 10] if evs_start + 10 < len(decrypted_data) else 0,
        'sheen': decrypted_data[evs_start + 11] if evs_start + 11 < len(decrypted_data) else 0,
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
    
    ribbon_data = struct.unpack('<I', decrypted_data[misc_start + 8:misc_start + 12])[0]
    
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
    
    RIBBON_RANKS = ['None', 'Normal', 'Super', 'Hyper', 'Master']
    
    return {
        'cool': RIBBON_RANKS[cool_ribbon] if cool_ribbon < len(RIBBON_RANKS) else 'None',
        'beauty': RIBBON_RANKS[beauty_ribbon] if beauty_ribbon < len(RIBBON_RANKS) else 'None',
        'cute': RIBBON_RANKS[cute_ribbon] if cute_ribbon < len(RIBBON_RANKS) else 'None',
        'smart': RIBBON_RANKS[smart_ribbon] if smart_ribbon < len(RIBBON_RANKS) else 'None',
        'tough': RIBBON_RANKS[tough_ribbon] if tough_ribbon < len(RIBBON_RANKS) else 'None',
        'champion': champion_ribbon,
        'winning': winning_ribbon,
        'victory': victory_ribbon,
        'artist': artist_ribbon,
        'effort': effort_ribbon,
    }


def get_obedience_level(badge_count, game_type='RSE'):
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
    if game_type == 'FRLG':
        # FireRed/LeafGreen
        OBEDIENCE_LEVELS = {
            0: 10,   # No badges
            1: 20,   # Boulder Badge
            2: 30,   # Cascade Badge
            3: 40,   # Thunder Badge
            4: 50,   # Rainbow Badge
            5: 60,   # Soul Badge
            6: 70,   # Marsh Badge
            7: 80,   # Volcano Badge
            8: 100,  # Earth Badge - all levels
        }
    else:
        # Ruby/Sapphire/Emerald
        OBEDIENCE_LEVELS = {
            0: 10,   # No badges
            1: 20,   # Stone Badge
            2: 30,   # Knuckle Badge
            3: 40,   # Dynamo Badge
            4: 50,   # Heat Badge
            5: 60,   # Balance Badge
            6: 70,   # Feather Badge
            7: 80,   # Mind Badge
            8: 100,  # Rain Badge - all levels
        }
    
    return OBEDIENCE_LEVELS.get(badge_count, 10)


def check_obedience(pokemon_level, badge_count, game_type='RSE'):
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