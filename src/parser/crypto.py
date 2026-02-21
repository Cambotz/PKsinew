"""
Gen 3 Pokemon Save Parser - Crypto Module
Handles decryption and text encoding/decoding
"""

import struct
from .constants import PERMUTATIONS


def decrypt_pokemon_data(encrypted_data, personality, ot_id):
    """
    Decrypt the 48-byte Pokemon substructure data.
    
    Args:
        encrypted_data: 48 bytes of encrypted data
        personality: Pokemon's personality value (PID)
        ot_id: Original trainer ID (full 32-bit)
        
    Returns:
        bytearray: 48 bytes of decrypted data
    """
    key = personality ^ ot_id
    decrypted = bytearray()
    
    for i in range(0, 48, 4):
        encrypted_word = struct.unpack('<I', encrypted_data[i:i+4])[0]
        decrypted_word = encrypted_word ^ key
        decrypted.extend(struct.pack('<I', decrypted_word))
    
    return decrypted


def encrypt_pokemon_data(decrypted_data, personality, ot_id):
    """
    Encrypt the 48-byte Pokemon substructure data.
    
    Args:
        decrypted_data: 48 bytes of decrypted data
        personality: Pokemon's personality value (PID)
        ot_id: Original trainer ID (full 32-bit)
        
    Returns:
        bytearray: 48 bytes of encrypted data
    """
    # Encryption is the same as decryption (XOR is symmetric)
    return decrypt_pokemon_data(decrypted_data, personality, ot_id)


def get_block_order(personality):
    """
    Get the block order for a Pokemon based on personality.
    
    Args:
        personality: Pokemon's personality value
        
    Returns:
        list: [growth_pos, attacks_pos, evs_pos, misc_pos]
    """
    permutation_index = personality % 24
    return PERMUTATIONS[permutation_index]


def get_block_position(personality, block_type):
    """
    Get the position of a specific block type.
    
    Args:
        personality: Pokemon's personality value
        block_type: 0=Growth, 1=Attacks, 2=EVs, 3=Misc
        
    Returns:
        int: Position (0-3) of the block
    """
    block_order = get_block_order(personality)
    return block_order[block_type]


# ============================================================
# TEXT ENCODING/DECODING
# ============================================================

# Gen 3 character encoding table
GEN3_CHARSET = {
    # Uppercase letters (0xBB-0xD4)
    **{0xBB + i: chr(ord('A') + i) for i in range(26)},
    # Lowercase letters (0xD5-0xEE)
    **{0xD5 + i: chr(ord('a') + i) for i in range(26)},
    # Numbers (0xA1-0xAA)
    **{0xA1 + i: chr(ord('0') + i) for i in range(10)},
    # Special characters
    0x00: '',      # Terminator (alternative)
    0xAB: '!',
    0xAC: '?',
    0xAD: '.',
    0xAE: '-',
    0xB0: '…',     # Ellipsis
    0xB1: '"',     # Left double quote
    0xB2: '"',     # Right double quote
    0xB3: "'",     # Apostrophe
    0xB4: "'",     # Single quote
    0xB5: '♂',     # Male symbol
    0xB6: '♀',     # Female symbol
    0xB7: ',',
    0xB8: '/',
    0xBA: ':',
    0xFF: '',      # Terminator
    0x00: ' ',     # Space (sometimes)
}

# Reverse mapping for encoding
CHARSET_TO_GEN3 = {v: k for k, v in GEN3_CHARSET.items() if v}


def decode_gen3_text(data):
    """
    Decode Gen 3 text encoding to string.
    
    Args:
        data: bytes or bytearray of encoded text
        
    Returns:
        str: Decoded text
    """
    result = []
    
    for byte in data:
        if byte == 0xFF:  # Only 0xFF is the terminator
            break
        elif byte == 0x00:
            result.append(' ')  # 0x00 is space, not terminator
        elif byte == 0x01:
            result.append('あ')
        elif byte == 0x02:
            result.append('い')
        elif byte == 0x03:
            result.append('う')
        elif byte == 0x04:
            result.append('え')
        elif byte == 0x05:
            result.append('お')
        elif byte == 0x06:
            result.append('か')
        elif byte == 0x07:
            result.append('き')
        elif byte == 0x08:
            result.append('く')
        elif byte == 0x09:
            result.append('け')
        elif byte == 0x0A:
            result.append('こ')
        elif byte == 0x0B:
            result.append('さ')
        elif byte == 0x0C:
            result.append('し')
        elif byte == 0x0D:
            result.append('す')
        elif byte == 0x0E:
            result.append('せ')
        elif byte == 0x0F:
            result.append('そ')
        elif byte == 0x10:
            result.append('た')
        elif byte == 0x11:
            result.append('ち')
        elif byte == 0x12:
            result.append('つ')
        elif byte == 0x13:
            result.append('て')
        elif byte == 0x14:
            result.append('と')
        elif byte == 0x15:
            result.append('な')
        elif byte == 0x16:
            result.append('に')
        elif byte == 0x17:
            result.append('ぬ')
        elif byte == 0x18:
            result.append('ね')
        elif byte == 0x19:
            result.append('の')
        elif byte == 0x1A:
            result.append('は')
        elif byte == 0x1B:
            result.append('ひ')
        elif byte == 0x1C:
            result.append('ふ')
        elif byte == 0x1D:
            result.append('へ')
        elif byte == 0x1E:
            result.append('ほ')
        elif byte == 0x1F:
            result.append('ま')
        elif byte == 0x20:
            result.append('み')
        elif byte == 0x21:
            result.append('む')
        elif byte == 0x22:
            result.append('め')
        elif byte == 0x23:
            result.append('も')
        elif byte == 0x24:
            result.append('や')
        elif byte == 0x25:
            result.append('ゆ')
        elif byte == 0x26:
            result.append('よ')
        elif byte == 0x27:
            result.append('ら')
        elif byte == 0x28:
            result.append('り')
        elif byte == 0x29:
            result.append('る')
        elif byte == 0x2A:
            result.append('れ')
        elif byte == 0x2B:
            result.append('ろ')
        elif byte == 0x2C:
            result.append('わ')
        elif byte == 0x2D:
            result.append('を')
        elif byte == 0x2E:
            result.append('ん')
        elif byte == 0x2F:
            result.append('ぁ')
        elif byte == 0x30:
            result.append('ぃ')
        elif byte == 0x31:
            result.append('ぅ')
        elif byte == 0x32:
            result.append('ぇ')
        elif byte == 0x33:
            result.append('ぉ')
        elif byte == 0x34:
            result.append('ゃ')
        elif byte == 0x35:
            result.append('ゅ')
        elif byte == 0x36:
            result.append('ょ')
        elif byte == 0x37:
            result.append('が')
        elif byte == 0x38:
            result.append('ぎ')
        elif byte == 0x39:
            result.append('ぐ')
        elif byte == 0x3A:
            result.append('げ')
        elif byte == 0x3B:
            result.append('ご')
        elif byte == 0x3C:
            result.append('ざ')
        elif byte == 0x3D:
            result.append('じ')
        elif byte == 0x3E:
            result.append('ず')
        elif byte == 0x3F:
            result.append('ぜ')
        elif byte == 0x40:
            result.append('ぞ')
        elif byte == 0x41:
            result.append('だ')
        elif byte == 0x42:
            result.append('ぢ')
        elif byte == 0x43:
            result.append('づ')
        elif byte == 0x44:
            result.append('で')
        elif byte == 0x45:
            result.append('ど')
        elif byte == 0x46:
            result.append('ば')
        elif byte == 0x47:
            result.append('び')
        elif byte == 0x48:
            result.append('ぶ')
        elif byte == 0x49:
            result.append('べ')
        elif byte == 0x4A:
            result.append('ぼ')
        elif byte == 0x4B:
            result.append('ぱ')
        elif byte == 0x4C:
            result.append('ぴ')
        elif byte == 0x4D:
            result.append('ぷ')
        elif byte == 0x4E:
            result.append('ぺ')
        elif byte == 0x4F:
            result.append('ぽ')
        elif byte == 0x50:
            result.append('っ')
        elif byte == 0x51:
            result.append('ア')
        elif byte == 0x52:
            result.append('イ')
        elif byte == 0x53:
            result.append('ウ')
        elif byte == 0x54:
            result.append('エ')
        elif byte == 0x55:
            result.append('オ')
        elif byte == 0x56:
            result.append('カ')
        elif byte == 0x57:
            result.append('キ')
        elif byte == 0x58:
            result.append('ク')
        elif byte == 0x59:
            result.append('ケ')
        elif byte == 0x5A:
            result.append('コ')
        elif byte == 0x5B:
            result.append('サ')
        elif byte == 0x5C:
            result.append('シ')
        elif byte == 0x5D:
            result.append('ス')
        elif byte == 0x5E:
            result.append('セ')
        elif byte == 0x5F:
            result.append('ソ')
        elif byte == 0x60:
            result.append('タ')
        elif byte == 0x61:
            result.append('チ')
        elif byte == 0x62:
            result.append('ツ')
        elif byte == 0x63:
            result.append('テ')
        elif byte == 0x64:
            result.append('ト')
        elif byte == 0x65:
            result.append('ナ')
        elif byte == 0x66:
            result.append('ニ')
        elif byte == 0x67:
            result.append('ヌ')
        elif byte == 0x68:
            result.append('ネ')
        elif byte == 0x69:
            result.append('ノ')
        elif byte == 0x6A:
            result.append('ハ')
        elif byte == 0x6B:
            result.append('ヒ')
        elif byte == 0x6C:
            result.append('フ')
        elif byte == 0x6D:
            result.append('ヘ')
        elif byte == 0x6E:
            result.append('ホ')
        elif byte == 0x6F:
            result.append('マ')
        elif byte == 0x70:
            result.append('ミ')
        elif byte == 0x71:
            result.append('ム')
        elif byte == 0x72:
            result.append('メ')
        elif byte == 0x73:
            result.append('モ')
        elif byte == 0x74:
            result.append('ヤ')
        elif byte == 0x75:
            result.append('ユ')
        elif byte == 0x76:
            result.append('ヨ')
        elif byte == 0x77:
            result.append('ラ')
        elif byte == 0x78:
            result.append('リ')
        elif byte == 0x79:
            result.append('ル')
        elif byte == 0x7A:
            result.append('レ')
        elif byte == 0x7B:
            result.append('ロ')
        elif byte == 0x7C:
            result.append('ワ')
        elif byte == 0x7D:
            result.append('ヲ')
        elif byte == 0x7E:
            result.append('ン')
        elif byte == 0x7F:
            result.append('ァ')
        elif byte == 0x80:
            result.append('ィ')
        elif byte == 0x81:
            result.append('ゥ')
        elif byte == 0x82:
            result.append('ェ')
        elif byte == 0x83:
            result.append('ォ')
        elif byte == 0x84:
            result.append('ャ')
        elif byte == 0x85:
            result.append('ュ')
        elif byte == 0x86:
            result.append('ョ')
        elif byte == 0x87:
            result.append('ガ')
        elif byte == 0x88:
            result.append('ギ')
        elif byte == 0x89:
            result.append('グ')
        elif byte == 0x8A:
            result.append('ゲ')
        elif byte == 0x8B:
            result.append('ゴ')
        elif byte == 0x8C:
            result.append('ザ')
        elif byte == 0x8D:
            result.append('ジ')
        elif byte == 0x8E:
            result.append('ズ')
        elif byte == 0x8F:
            result.append('ゼ')
        elif byte == 0x90:
            result.append('ゾ')
        elif byte == 0x91:
            result.append('ダ')
        elif byte == 0x92:
            result.append('ヂ')
        elif byte == 0x93:
            result.append('ヅ')
        elif byte == 0x94:
            result.append('デ')
        elif byte == 0x95:
            result.append('ド')
        elif byte == 0x96:
            result.append('バ')
        elif byte == 0x97:
            result.append('ビ')
        elif byte == 0x98:
            result.append('ブ')
        elif byte == 0x99:
            result.append('ベ')
        elif byte == 0x9A:
            result.append('ボ')
        elif byte == 0x9B:
            result.append('パ')
        elif byte == 0x9C:
            result.append('ピ')
        elif byte == 0x9D:
            result.append('プ')
        elif byte == 0x9E:
            result.append('ペ')
        elif byte == 0x9F:
            result.append('ポ')
        elif byte == 0xA0:
            result.append('ッ')
        elif byte == 0xA1:
            result.append('０')
        elif byte == 0xA2:
            result.append('１')
        elif byte == 0xA3:
            result.append('２')
        elif byte == 0xA4:
            result.append('３')
        elif byte == 0xA5:
            result.append('４')
        elif byte == 0xA6:
            result.append('５')
        elif byte == 0xA7:
            result.append('６')
        elif byte == 0xA8:
            result.append('７')
        elif byte == 0xA9:
            result.append('８')
        elif byte == 0xAA:
            result.append('９')
        elif byte == 0xAB:
            result.append('!')
        elif byte == 0xAC:
            result.append('?')
        elif byte == 0xAD:
            result.append('。')
        elif byte == 0xAE:
            result.append('-') #font doesn't work with ー
        elif byte == 0xAF:
            result.append('・')
        elif byte == 0xB5:
            result.append('♂')
        elif byte == 0xB6:
            result.append('♀')
        elif byte == 0xBA:
            result.append('/')
        elif 0xBB <= byte <= 0xD4:
            result.append(chr(ord('A') + (byte - 0xBB)))
        elif 0xD5 <= byte <= 0xEE:
            result.append(chr(ord('a') + (byte - 0xD5)))
        else:
            # Unknown character - skip or use placeholder
            pass
    
    return ''.join(result) if result else "Unknown"


def encode_gen3_text(text, max_length=10, pad_byte=0xFF):
    """
    Encode a string to Gen 3 text encoding.
    
    Args:
        text: String to encode
        max_length: Maximum length (will be padded/truncated)
        pad_byte: Byte to use for padding (default 0xFF terminator)
        
    Returns:
        bytearray: Encoded text
    """
    result = bytearray()
    
    for char in text[:max_length]:
        if 'A' <= char <= 'Z':
            result.append(0xBB + (ord(char) - ord('A')))
        elif 'a' <= char <= 'z':
            result.append(0xD5 + (ord(char) - ord('a')))
        elif '0' <= char <= '9':
            result.append(0xA1 + (ord(char) - ord('0')))
        elif char == ' ':
            result.append(0x00)
        elif char == '!':
            result.append(0xAB)
        elif char == '?':
            result.append(0xAC)
        elif char == '.':
            result.append(0xAD)
        elif char == '-':
            result.append(0xAE)
        elif char == "'":
            result.append(0xB4)
        else:
            # Unknown character - use space
            result.append(0x00)
    
    # Pad to max_length
    while len(result) < max_length:
        result.append(pad_byte)
    
    return result


# ============================================================
# CHECKSUM
# ============================================================

def calculate_section_checksum(data, size):
    """
    Calculate checksum for a save section.
    
    Args:
        data: Section data
        size: Size of data to checksum
        
    Returns:
        int: 16-bit checksum
    """
    checksum = 0
    for i in range(0, size, 4):
        word = struct.unpack('<I', data[i:i+4])[0]
        checksum = (checksum + word) & 0xFFFFFFFF
    
    # Fold to 16 bits
    return ((checksum >> 16) + (checksum & 0xFFFF)) & 0xFFFF


def calculate_pokemon_checksum(decrypted_data):
    """
    Calculate checksum for Pokemon data (48 bytes).
    
    Args:
        decrypted_data: 48 bytes of decrypted Pokemon data
        
    Returns:
        int: 16-bit checksum
    """
    checksum = 0
    for i in range(0, 48, 2):
        word = struct.unpack('<H', decrypted_data[i:i+2])[0]
        checksum = (checksum + word) & 0xFFFF
    return checksum