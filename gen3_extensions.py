"""
Gen 3 Parser Extensions
Adds box name parsing and contest data parsing
"""

import struct


def decode_gen3_text(text_bytes):
    """Decode Gen 3 text encoding to string"""
    # Gen 3 character table (common characters)
    GEN3_CHARS = {
    ' ': 0x00, 
    'あ': 0x01, 'い': 0x02, 'う': 0x03, 'え': 0x04, 'お': 0x05,
    'か': 0x06, 'き': 0x07, 'く': 0x08, 'け': 0x09, 'こ': 0x0A,
    'さ': 0x0B, 'し': 0x0C, 'す': 0x0D, 'せ': 0x0E, 'そ': 0x0F,
    'た': 0x10, 'ち': 0x11, 'つ': 0x12, 'て': 0x13, 'と': 0x14,
    'な': 0x15, 'に': 0x16, 'ぬ': 0x17, 'ね': 0x18, 'の': 0x19,
    'は': 0x1A, 'ひ': 0x1B, 'ふ': 0x1C, 'へ': 0x1D, 'ほ': 0x1E,
    'ま': 0x1F, 'み': 0x20, 'む': 0x21, 'め': 0x22, 'も': 0x23,
    'や': 0x24, 'ゆ': 0x25, 'よ': 0x26,
    'ら': 0x27, 'り': 0x28, 'る': 0x29, 'れ': 0x2A, 'ろ': 0x2B,
    'わ': 0x2C, 'を': 0x2D, 'ん': 0x2E,
    'ぁ': 0x2F, 'ぃ': 0x30, 'ぅ': 0x31, 'ぇ': 0x32, 'ぉ': 0x33,
    'ゃ': 0x34, 'ゅ': 0x35, 'ょ': 0x36,
    'が': 0x37, 'ぎ': 0x38, 'ぐ': 0x39, 'げ': 0x3A, 'ご': 0x3B,
    'ざ': 0x3C, 'じ': 0x3D, 'ず': 0x3E, 'ぜ': 0x3F,	'ぞ': 0x40,
    'だ': 0x41, 'ぢ': 0x42, 'づ': 0x43, 'で': 0x44, 'ど': 0x45,
    'ば': 0x46, 'び': 0x47, 'ぶ': 0x48, 'べ': 0x49, 'ぼ': 0x4A,
    'ぱ': 0x4B, 'ぴ': 0x4C, 'ぷ': 0x4D, 'ぺ': 0x4E, 'ぽ': 0x4F,
    'っ': 0x50,
    'ア': 0x51, 'イ': 0x52, 'ウ': 0x53, 'エ': 0x54, 'オ': 0x55,
    'カ': 0x56, 'キ': 0x57, 'ク': 0x58, 'ケ': 0x59, 'コ': 0x5A,
    'サ': 0x5B, 'シ': 0x5C, 'ス': 0x5D, 'セ': 0x5E, 'ソ': 0x5F,
    'タ': 0x60, 'チ': 0x61, 'ツ': 0x62, 'テ': 0x63, 'ト': 0x64,
    'ナ': 0x65, 'ニ': 0x66, 'ヌ': 0x67, 'ネ': 0x68, 'ノ': 0x69,
    'ハ': 0x6A, 'ヒ': 0x6B, 'フ': 0x6C, 'ヘ': 0x6D, 'ホ': 0x6E,
    'マ': 0x6F, 'ミ': 0x70, 'ム': 0x71, 'メ': 0x72, 'モ': 0x73,	
    'ヤ': 0x74, 'ユ': 0x75, 'ヨ': 0x76,	
    'ラ': 0x77, 'リ': 0x78, 'ル': 0x79, 'レ': 0x7A, 'ロ': 0x7B,
    'ワ': 0x7C, 'ヲ': 0x7D, 'ン': 0x7E,
    'ァ': 0x7F, 'ィ': 0x80, 'ゥ': 0x81, 'ェ': 0x82, 'ォ': 0x83,	
    'ャ': 0x84, 'ュ': 0x85, 'ョ': 0x86,
    'ガ': 0x87, 'ギ': 0x88, 'グ': 0x89, 'ゲ': 0x8A, 'ゴ':0x8B,
    'ザ': 0x8C, 'ジ': 0x8D, 'ズ': 0x8E, 'ゼ': 0x8F, 'ゾ':0x90,
    'ダ': 0x91, 'ヂ': 0x92, 'ヅ': 0x93, 'デ': 0x94, 'ド':0x95,
    'バ': 0x96, 'ビ': 0x97, 'ブ': 0x98, 'ベ': 0x99, 'ボ':0x9A,
    'パ': 0x9B, 'ピ': 0x9C, 'プ': 0x9D, 'ペ': 0x9E, 'ポ':0x9F,
    'ッ': 0xA0,
    '０': 0xA1, '１': 0xA2, '２': 0xA3, '３': 0xA4, '４': 0xA5,
    '５': 0xA6, '６': 0xA7, '７': 0xA8, '８': 0xA9, '９': 0xAA,
    '!': 0xAB, '?': 0xAC, '。': 0xAD, 'ー': 0xAE, '・': 0xAF,
    '♂': 0xB5, '♀': 0xB6, '/': 0xBA,
    'A': 0xBB, 'B': 0xBC, 'C': 0xBD, 'D': 0xBE, 'E': 0xBF,
    'F': 0xC0, 'G': 0xC1, 'H': 0xC2, 'I': 0xC3, 'J': 0xC4,
    'K': 0xC5, 'L': 0xC6, 'M': 0xC7, 'N': 0xC8, 'O': 0xC9,
    'P': 0xCA, 'Q': 0xCB, 'R': 0xCC, 'S': 0xCD, 'T': 0xCE,
    'U': 0xCF, 'V': 0xD0, 'W': 0xD1, 'X': 0xD2, 'Y': 0xD3,
    'Z': 0xD4, 'a': 0xD5, 'b': 0xD6, 'c': 0xD7, 'd': 0xD8,
    'e': 0xD9, 'f': 0xDA, 'g': 0xDB, 'h': 0xDC, 'i': 0xDD,
    'j': 0xDE, 'k': 0xDF, 'l': 0xE0, 'm': 0xE1, 'n': 0xE2,
    'o': 0xE3, 'p': 0xE4, 'q': 0xE5, 'r': 0xE6, 's': 0xE7,
    't': 0xE8, 'u': 0xE9, 'v': 0xEA, 'w': 0xEB, 'x': 0xEC,
    'y': 0xED, 'z': 0xEE, 
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