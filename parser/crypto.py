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
        if byte == 0xFF or byte == 0x00:
            break
        elif 0xBB <= byte <= 0xD4:
            result.append(chr(ord('A') + (byte - 0xBB)))
        elif 0xD5 <= byte <= 0xEE:
            result.append(chr(ord('a') + (byte - 0xD5)))
        elif 0xA1 <= byte <= 0xAA:
            result.append(chr(ord('0') + (byte - 0xA1)))
        elif byte == 0xAB:
            result.append('!')
        elif byte == 0xAC:
            result.append('?')
        elif byte == 0xAD:
            result.append('.')
        elif byte == 0xAE:
            result.append('-')
        elif byte == 0xB4:
            result.append("'")
        elif byte == 0xB5:
            result.append('♂')
        elif byte == 0xB6:
            result.append('♀')
        elif byte == 0x00:
            result.append(' ')
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
