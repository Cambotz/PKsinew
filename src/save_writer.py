"""
Gen 3 Save Writer Module
Handles writing Pokemon to save files for transfers between saves.
"""

import struct
import os
import shutil
from datetime import datetime


# =============================================================================
# CONSTANTS
# =============================================================================

# Section sizes (data portion, excluding footer)
SECTION_DATA_SIZE = 0xF80  # 3968 bytes
SECTION_TOTAL_SIZE = 0x1000  # 4096 bytes with footer

# PC Box constants
PC_BUFFER_SIZE = 33744  # Total PC data size
BOX_SIZE = 30  # Pokemon per box
POKEMON_PC_SIZE = 80  # Bytes per PC Pokemon
POKEMON_PARTY_SIZE = 100  # Bytes per Party Pokemon

# Section IDs that contain PC data (5-13)
PC_SECTION_IDS = [5, 6, 7, 8, 9, 10, 11, 12, 13]


# =============================================================================
# CHECKSUM CALCULATION
# =============================================================================

def calculate_section_checksum(section_data):
    """
    Calculate the checksum for a save section.
    
    Gen 3 uses a simple 32-bit sum of all 16-bit words in the section,
    then the result is folded to 16 bits.
    
    Args:
        section_data: The 3968 bytes of section data (not including footer)
        
    Returns:
        int: 16-bit checksum
    """
    checksum = 0
    
    # Sum all 16-bit words
    for i in range(0, len(section_data), 4):
        if i + 4 <= len(section_data):
            word = struct.unpack('<I', section_data[i:i+4])[0]
            checksum = (checksum + word) & 0xFFFFFFFF
    
    # Fold 32-bit sum to 16-bit
    checksum = ((checksum >> 16) + (checksum & 0xFFFF)) & 0xFFFF
    
    return checksum


def update_section_checksum(save_data, section_offset):
    """
    Recalculate and update the checksum for a section.
    
    Args:
        save_data: Mutable bytearray of save file
        section_offset: Offset to the section start
    """
    # Get section data (first 3968 bytes)
    section_data = save_data[section_offset:section_offset + SECTION_DATA_SIZE]
    
    # Calculate new checksum
    new_checksum = calculate_section_checksum(section_data)
    
    # Write checksum at offset 0xFF6 within section
    checksum_offset = section_offset + 0xFF6
    struct.pack_into('<H', save_data, checksum_offset, new_checksum)
    
    return new_checksum


# =============================================================================
# SECTION MANAGEMENT
# =============================================================================

def find_section_by_id(save_data, block_offset, section_id):
    """
    Find a section by its ID within a save block.
    
    Args:
        save_data: Save file data
        block_offset: Offset to save block (0x0000 or 0xE000)
        section_id: Section ID to find (0-13)
        
    Returns:
        int: Offset to section, or None if not found
    """
    for i in range(14):
        section_offset = block_offset + (i * SECTION_TOTAL_SIZE)
        # Section ID is at offset 0xFF4 within section
        sid = struct.unpack('<H', save_data[section_offset + 0xFF4:section_offset + 0xFF6])[0]
        if sid == section_id:
            return section_offset
    return None


def get_active_block(save_data):
    """
    Determine which save block (A or B) is active.
    
    Args:
        save_data: Save file data
        
    Returns:
        int: Offset to active block (0x0000 or 0xE000)
    """
    # Save index is at offset 0xFFC within each section
    # Check section 0 of each block
    
    # Block A (offset 0x0000)
    block_a_idx = struct.unpack('<I', save_data[0x0FFC:0x1000])[0]
    
    # Block B (offset 0xE000)
    block_b_idx = struct.unpack('<I', save_data[0xEFFC:0xF000])[0]
    
    # Higher save index = more recent = active
    if block_b_idx > block_a_idx:
        return 0xE000
    return 0x0000


# =============================================================================
# PC BOX WRITING
# =============================================================================

def get_pc_pokemon_offset(save_data, block_offset, box_number, slot_number, game_type='RSE'):
    """
    Calculate the offset to a specific Pokemon in PC storage.
    
    Args:
        save_data: Save file data
        block_offset: Offset to active save block
        box_number: Box number (1-14)
        slot_number: Slot within box (0-29)
        game_type: 'RSE' or 'FRLG'
        
    Returns:
        tuple: (section_offset, offset_within_section, pokemon_global_offset)
    """
    import sys
    
    # Validate inputs
    if box_number < 1 or box_number > 14:
        raise ValueError(f"Invalid box number: {box_number} (must be 1-14)")
    if slot_number < 0 or slot_number >= BOX_SIZE:
        raise ValueError(f"Invalid slot number: {slot_number} (must be 0-29)")
    
    # Validate save_data
    if save_data is None:
        raise ValueError("save_data is None")
    if len(save_data) < 0x20000:
        raise ValueError(f"save_data too small: {len(save_data)} bytes (expected at least 131072)")
    
    # Calculate global offset within PC buffer
    # Box names take first 126 bytes (9 bytes * 14 boxes)
    # Box wallpapers take next 14 bytes
    # Pokemon data starts at offset 4 in PC buffer
    pc_pokemon_start = 4
    
    box_index = box_number - 1
    pokemon_index = (box_index * BOX_SIZE) + slot_number
    pokemon_offset_in_pc = pc_pokemon_start + (pokemon_index * POKEMON_PC_SIZE)
    
    # PC data spans sections 5-13
    # Calculate which section and offset within section
    bytes_per_section = SECTION_DATA_SIZE
    
    # Section 5 starts PC data
    section_index = 5 + (pokemon_offset_in_pc // bytes_per_section)
    offset_in_section = pokemon_offset_in_pc % bytes_per_section
    
    # Validate section index is within expected range (5-13)
    if section_index < 5 or section_index > 13:
        raise ValueError(f"Calculated section {section_index} is out of PC range (5-13). Box={box_number}, Slot={slot_number}")
    
    # Find the section
    section_offset = find_section_by_id(save_data, block_offset, section_index)
    if section_offset is None:
        # Debug: List all section IDs found in this block
        found_sections = []
        for i in range(14):
            sec_off = block_offset + (i * SECTION_TOTAL_SIZE)
            try:
                sid = struct.unpack('<H', save_data[sec_off + 0xFF4:sec_off + 0xFF6])[0]
                found_sections.append(sid)
            except:
                found_sections.append(-1)
        
        raise ValueError(
            f"Could not find section {section_index} in save data.\n"
            f"  Box={box_number}, Slot={slot_number}, BlockOffset=0x{block_offset:X}\n"
            f"  Sections found: {found_sections}\n"
            f"  Save size: {len(save_data)} bytes"
        )
    
    global_offset = section_offset + offset_in_section
    
    return section_offset, offset_in_section, global_offset


def read_pokemon_from_pc(save_data, box_number, slot_number, game_type='RSE'):
    """
    Read a Pokemon from a PC box slot (for verification).
    
    Args:
        save_data: Save file data
        box_number: Box number (1-14)
        slot_number: Slot within box (0-29)
        game_type: 'RSE' or 'FRLG'
        
    Returns:
        bytes: 80 bytes of Pokemon data
    """
    block_offset = get_active_block(save_data)
    section_offset, offset_in_section, global_offset = get_pc_pokemon_offset(
        save_data, block_offset, box_number, slot_number, game_type
    )
    return bytes(save_data[global_offset:global_offset + POKEMON_PC_SIZE])


def write_pokemon_to_pc(save_data, box_number, slot_number, pokemon_bytes, game_type='RSE'):
    """
    Write a Pokemon to a PC box slot.
    
    Args:
        save_data: Mutable bytearray of save file
        box_number: Box number (1-14)
        slot_number: Slot within box (0-29)
        pokemon_bytes: 80 bytes of Pokemon data
        game_type: 'RSE' or 'FRLG'
        
    Returns:
        bool: True if successful
    """
    import sys
    print(f"[SaveWriter] write_pokemon_to_pc called", file=sys.stderr, flush=True)
    print(f"[SaveWriter]   box={box_number}, slot={slot_number}, game_type={game_type}", file=sys.stderr, flush=True)
    print(f"[SaveWriter]   pokemon_bytes type={type(pokemon_bytes)}, len={len(pokemon_bytes) if pokemon_bytes else 'None'}", file=sys.stderr, flush=True)
    
    if pokemon_bytes:
        print(f"[SaveWriter]   First 8 bytes: {pokemon_bytes[:8].hex()}", file=sys.stderr, flush=True)
    
    if len(pokemon_bytes) == POKEMON_PARTY_SIZE:
        # Convert party format to PC format (strip battle stats)
        pokemon_bytes = party_to_pc_bytes(pokemon_bytes)
    
    if len(pokemon_bytes) != POKEMON_PC_SIZE:
        raise ValueError(f"Pokemon data must be {POKEMON_PC_SIZE} bytes, got {len(pokemon_bytes)}")
    
    # Get active block
    block_offset = get_active_block(save_data)
    
    # Get the offset
    section_offset, offset_in_section, global_offset = get_pc_pokemon_offset(
        save_data, block_offset, box_number, slot_number, game_type
    )
    
    # Write the Pokemon data
    save_data[global_offset:global_offset + POKEMON_PC_SIZE] = pokemon_bytes
    
    import sys
    print(f"[SaveWriter]   Written to offset 0x{global_offset:X}", file=sys.stderr, flush=True)
    print(f"[SaveWriter]   Section offset: 0x{section_offset:X}, offset in section: 0x{offset_in_section:X}", file=sys.stderr, flush=True)
    
    # Verify write succeeded
    written_data = save_data[global_offset:global_offset + POKEMON_PC_SIZE]
    if written_data == pokemon_bytes:
        print(f"[SaveWriter]   ✓ Verified: data written correctly", file=sys.stderr, flush=True)
    else:
        print(f"[SaveWriter]   ✗ ERROR: Written data doesn't match!", file=sys.stderr, flush=True)
    
    # Update section checksum
    old_checksum = struct.unpack('<H', save_data[section_offset + 0xFF6:section_offset + 0xFF8])[0]
    update_section_checksum(save_data, section_offset)
    new_checksum = struct.unpack('<H', save_data[section_offset + 0xFF6:section_offset + 0xFF8])[0]
    print(f"[SaveWriter]   Checksum updated: 0x{old_checksum:04X} -> 0x{new_checksum:04X}", file=sys.stderr, flush=True)
    
    return True


def clear_pc_slot(save_data, box_number, slot_number, game_type='RSE'):
    """
    Clear a PC box slot (set to empty).
    
    Args:
        save_data: Mutable bytearray of save file
        box_number: Box number (1-14)
        slot_number: Slot within box (0-29)
        game_type: 'RSE' or 'FRLG'
        
    Returns:
        bool: True if successful
    """
    # Empty slot is all zeros
    empty_bytes = bytes(POKEMON_PC_SIZE)
    return write_pokemon_to_pc(save_data, box_number, slot_number, empty_bytes, game_type)


# =============================================================================
# PARTY WRITING
# =============================================================================

def get_party_pokemon_offset(save_data, block_offset, slot_number, game_type='RSE'):
    """
    Calculate the offset to a specific Pokemon in party.
    
    Args:
        save_data: Save file data
        block_offset: Offset to active save block
        slot_number: Slot in party (0-5)
        game_type: 'RSE' or 'FRLG'
        
    Returns:
        tuple: (section_offset, global_offset)
    """
    if slot_number < 0 or slot_number >= 6:
        raise ValueError(f"Invalid party slot: {slot_number} (must be 0-5)")
    
    # Party is in Section 1
    section_offset = find_section_by_id(save_data, block_offset, 1)
    if section_offset is None:
        raise ValueError("Could not find Section 1 (party data)")
    
    # Party offset within section depends on game
    if game_type in ['FRLG', 'FireRed', 'LeafGreen']:
        party_offset = 0x38
    else:  # RSE
        party_offset = 0x238
    
    # Party count is at party_offset, Pokemon data starts 4 bytes later
    pokemon_offset = section_offset + party_offset + 4 + (slot_number * POKEMON_PARTY_SIZE)
    
    return section_offset, pokemon_offset


# =============================================================================
# FORMAT CONVERSION
# =============================================================================

def party_to_pc_bytes(party_bytes):
    """
    Convert party Pokemon bytes (100) to PC format (80).
    Simply strips the 20 battle stat bytes at the end.
    
    Args:
        party_bytes: 100 bytes of party Pokemon data
        
    Returns:
        bytes: 80 bytes of PC Pokemon data
    """
    if len(party_bytes) != POKEMON_PARTY_SIZE:
        raise ValueError(f"Party data must be {POKEMON_PARTY_SIZE} bytes")
    return bytes(party_bytes[:POKEMON_PC_SIZE])


def pc_to_party_bytes(pc_bytes, level=1):
    """
    Convert PC Pokemon bytes (80) to party format (100).
    Adds placeholder battle stats (need to be calculated properly for actual use).
    
    Note: For a full implementation, battle stats should be calculated from
    base stats, IVs, EVs, nature, and level. For now, this adds zeroed stats.
    
    Args:
        pc_bytes: 80 bytes of PC Pokemon data
        level: Pokemon's level for stat calculation
        
    Returns:
        bytes: 100 bytes of party Pokemon data
    """
    if len(pc_bytes) != POKEMON_PC_SIZE:
        raise ValueError(f"PC data must be {POKEMON_PC_SIZE} bytes")
    
    # For now, just add 20 zero bytes for battle stats
    # A full implementation would calculate these properly
    party_bytes = bytearray(pc_bytes)
    
    # Battle stats structure (20 bytes):
    # 0x00: Status condition (4 bytes)
    # 0x04: Level (1 byte)
    # 0x05: Pokerus remaining (1 byte)  
    # 0x06: Current HP (2 bytes)
    # 0x08: Max HP (2 bytes)
    # 0x0A: Attack (2 bytes)
    # 0x0C: Defense (2 bytes)
    # 0x0E: Speed (2 bytes)
    # 0x10: Sp. Attack (2 bytes)
    # 0x12: Sp. Defense (2 bytes)
    
    battle_stats = bytearray(20)
    battle_stats[4] = level  # Set level
    
    party_bytes.extend(battle_stats)
    return bytes(party_bytes)


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def create_backup(filepath):
    """
    Create a backup of the save file.
    
    Args:
        filepath: Path to save file
        
    Returns:
        str: Path to backup file
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Save file not found: {filepath}")
    
    # Create backup with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    
    backup_filename = f"{name}_backup_{timestamp}{ext}"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    shutil.copy2(filepath, backup_path)
    print(f"Created backup: {backup_path}")
    
    return backup_path


def load_save_file(filepath):
    """
    Load a save file as a mutable bytearray.
    
    Args:
        filepath: Path to save file
        
    Returns:
        bytearray: Mutable save data
    """
    with open(filepath, 'rb') as f:
        return bytearray(f.read())


def write_save_file(filepath, save_data, create_backup_first=True):
    """
    Write save data to file.
    
    Args:
        filepath: Path to save file
        save_data: Save data (bytes or bytearray)
        create_backup_first: Whether to create a backup before writing
        
    Returns:
        bool: True if successful
    """
    if create_backup_first and os.path.exists(filepath):
        create_backup(filepath)
    
    with open(filepath, 'wb') as f:
        f.write(save_data)
    
    print(f"Save file written: {filepath}")
    return True


# =============================================================================
# HIGH-LEVEL TRANSFER FUNCTIONS
# =============================================================================

def find_first_empty_slot(save_data, game_type='RSE', start_box=1):
    """
    Find the first empty PC slot.
    
    Args:
        save_data: Save file data
        game_type: 'RSE' or 'FRLG'
        start_box: Box to start searching from (1-14)
        
    Returns:
        tuple: (box_number, slot_number) or None if all full
    """
    block_offset = get_active_block(save_data)
    
    for box in range(start_box, 15):
        for slot in range(BOX_SIZE):
            try:
                section_offset, offset_in_section, global_offset = get_pc_pokemon_offset(
                    save_data, block_offset, box, slot, game_type
                )
                
                # Check if slot is empty (personality = 0)
                personality = struct.unpack('<I', save_data[global_offset:global_offset + 4])[0]
                if personality == 0:
                    return (box, slot)
            except Exception:
                continue
    
    return None


def transfer_pokemon(source_pokemon, dest_save_data, dest_game_type='RSE', 
                     target_box=None, target_slot=None):
    """
    Transfer a Pokemon to a destination save.
    
    Args:
        source_pokemon: Pokemon dict with 'raw_bytes' key, or raw bytes directly
        dest_save_data: Mutable bytearray of destination save
        dest_game_type: Game type of destination save
        target_box: Specific box to place in (None = first empty)
        target_slot: Specific slot to place in (None = first empty)
        
    Returns:
        tuple: (success, box_number, slot_number, message)
    """
    # Get raw bytes
    if isinstance(source_pokemon, dict):
        raw_bytes = source_pokemon.get('raw_bytes')
        pokemon_name = source_pokemon.get('nickname') or source_pokemon.get('species_name', 'Pokemon')
    else:
        raw_bytes = source_pokemon
        pokemon_name = 'Pokemon'
    
    if raw_bytes is None:
        return (False, None, None, "No raw_bytes in Pokemon data")
    
    # Find target slot
    if target_box is None or target_slot is None:
        empty = find_first_empty_slot(dest_save_data, dest_game_type)
        if empty is None:
            return (False, None, None, "No empty PC slots available")
        target_box, target_slot = empty
    
    # Perform the write
    try:
        write_pokemon_to_pc(dest_save_data, target_box, target_slot, raw_bytes, dest_game_type)
        return (True, target_box, target_slot, 
                f"Transferred {pokemon_name} to Box {target_box}, Slot {target_slot + 1}")
    except Exception as e:
        return (False, None, None, f"Transfer failed: {str(e)}")


# =============================================================================
# VALIDATION
# =============================================================================

def validate_save_file(filepath):
    """
    Validate a save file.
    
    Args:
        filepath: Path to save file
        
    Returns:
        tuple: (is_valid, game_type, message)
    """
    if not os.path.exists(filepath):
        return (False, None, "File not found")
    
    file_size = os.path.getsize(filepath)
    
    # Gen 3 saves are 128KB or 64KB (some flashcarts)
    if file_size not in [0x20000, 0x10000]:
        return (False, None, f"Invalid file size: {file_size} bytes")
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Try to detect game type
    block_offset = get_active_block(data)
    section0 = find_section_by_id(data, block_offset, 0)
    
    if section0 is None:
        return (False, None, "Could not find Section 0")
    
    # Game code is at offset 0xAC in Section 0
    game_code = struct.unpack('<I', data[section0 + 0xAC:section0 + 0xB0])[0]
    
    if game_code == 0:
        game_type = 'RSE'
    elif game_code == 1:
        game_type = 'FRLG'
    else:
        game_type = 'Unknown'
    
    return (True, game_type, f"Valid {game_type} save file")


# =============================================================================
# POKEDEX WRITING
# =============================================================================

# Pokedex data size (49 bytes = 392 bits, enough for 386 Pokemon)
POKEDEX_SIZE = 49


def _detect_rse_subtype(save_data, section0_offset, section1_offset=None):
    """
    Detect whether a save is Ruby/Sapphire or Emerald.
    
    The key difference:
    - Emerald uses a security key at offset 0xAC that encrypts money/items
    - Ruby/Sapphire does NOT use encryption (0 at 0xAC, or Battle Tower data)
    
    Args:
        save_data: Save file data
        section0_offset: Offset to Section 0
        section1_offset: Offset to Section 1 (optional, for money validation)
        
    Returns:
        str: 'E' for Emerald, 'RS' for Ruby/Sapphire, or 'FRLG' if detected
    """
    # First check if this is FRLG (game code = 1 at 0xAC)
    game_code = struct.unpack('<I', save_data[section0_offset + 0xAC:section0_offset + 0xB0])[0]
    if game_code == 1:
        return 'FRLG'
    
    # Check security key at 0xAC
    security_key = struct.unpack('<I', save_data[section0_offset + 0xAC:section0_offset + 0xB0])[0]
    
    if security_key == 0:
        # No security key = Ruby/Sapphire
        print(f"[GameDetect] Ruby/Sapphire detected (security_key=0)")
        return 'RS'
    
    # Non-zero value - verify if it's a valid Emerald security key
    # by checking if it decrypts money to a valid range
    if section1_offset is not None:
        money_offset = section1_offset + 0x0490  # RSE money offset
        if money_offset + 4 <= len(save_data):
            money_encrypted = struct.unpack('<I', save_data[money_offset:money_offset + 4])[0]
            money_decrypted = money_encrypted ^ security_key
            
            if 0 <= money_decrypted <= 999999:
                # Valid decryption = Emerald
                print(f"[GameDetect] Emerald detected (security_key=0x{security_key:08X}, money={money_decrypted})")
                return 'E'
            else:
                # Invalid decryption = RS with non-zero data at 0xAC (Battle Tower etc)
                print(f"[GameDetect] Ruby/Sapphire detected (invalid key decryption: {money_decrypted})")
                return 'RS'
    
    # Can't verify - default to RS (safer, avoids wrong offset writes)
    print(f"[GameDetect] Defaulting to Ruby/Sapphire (couldn't verify security key)")
    return 'RS'

# According to Bulbapedia, Pokedex data is stored across MULTIPLE SECTIONS:
# https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)#Pokédex_data
#
# OWNED is in Section 0 at 0x28 for all games
# SEEN has THREE copies that must ALL match:
#   RS:   Section 0 @ 0x5C, Section 1 @ 0x938, Section 4 @ 0xC0C
#   E:    Section 0 @ 0x5C, Section 1 @ 0x988, Section 4 @ 0xCA4
#   FRLG: Section 0 @ 0x5C, Section 1 @ 0x5F8, Section 4 @ 0xB98


def set_pokedex_flag(save_data, species_national_dex, seen=True, caught=True, game_type='RSE'):
    """
    Set the seen and/or caught flags for a Pokemon species in the Pokedex.
    
    This updates ALL THREE seen bitfields across Sections 0, 1, and 4,
    which are ALL required for the in-game Pokedex UI to work.
    
    Args:
        save_data: Mutable bytearray of save file
        species_national_dex: National Pokedex number (1-386)
        seen: Whether to mark as seen
        caught: Whether to mark as caught/owned
        game_type: 'RSE', 'RS', 'E', or 'FRLG'
        
    Returns:
        bool: True if successful
    """
    if species_national_dex < 1 or species_national_dex > 386:
        print(f"[PokedexWriter] Invalid species number: {species_national_dex}")
        return False
    
    # Calculate bit position (0-indexed)
    byte_index = (species_national_dex - 1) // 8
    bit_index = (species_national_dex - 1) % 8
    bit_mask = 1 << bit_index
    
    # Get active block
    block_offset = get_active_block(save_data)
    
    # Find all needed sections
    section0_offset = find_section_by_id(save_data, block_offset, 0)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    section4_offset = find_section_by_id(save_data, block_offset, 4)
    
    if section0_offset is None:
        print("[PokedexWriter] Could not find Section 0")
        return False
    
    # Detect game type from save if not specified or generic
    detected_game = game_type
    if game_type in ('RSE', 'RS', 'E'):
        # Use helper to properly detect RS vs Emerald (they have different offsets!)
        detected_game = _detect_rse_subtype(save_data, section0_offset, section1_offset)
    
    print(f"[PokedexWriter] Game type: {detected_game}, Species: {species_national_dex}")
    
    # Determine offsets based on game
    # OWNED: Always Section 0 @ 0x28
    owned_offset = 0x28
    
    # SEEN A: Always Section 0 @ 0x5C
    seen_a_offset = 0x5C
    
    # SEEN B: Section 1, varies by game
    if detected_game == 'FRLG':
        seen_b_offset = 0x5F8
    elif detected_game == 'E':
        seen_b_offset = 0x988
    else:  # RS
        seen_b_offset = 0x938
    
    # SEEN C: Section 4, varies by game
    if detected_game == 'FRLG':
        seen_c_offset = 0xB98
    elif detected_game == 'E':
        seen_c_offset = 0xCA4
    else:  # RS
        seen_c_offset = 0xC0C
    
    modified_sections = set()
    
    # Set OWNED flag (Section 0)
    if caught:
        addr = section0_offset + owned_offset + byte_index
        if addr < len(save_data):
            old_val = save_data[addr]
            save_data[addr] |= bit_mask
            if save_data[addr] != old_val:
                modified_sections.add((0, section0_offset))
                print(f"[PokedexWriter] Set OWNED @ Section 0, offset 0x{owned_offset + byte_index:X}")
    
    # Set all SEEN flags
    if seen or caught:
        # SEEN A (Section 0)
        addr = section0_offset + seen_a_offset + byte_index
        if addr < len(save_data):
            old_val = save_data[addr]
            save_data[addr] |= bit_mask
            if save_data[addr] != old_val:
                modified_sections.add((0, section0_offset))
                print(f"[PokedexWriter] Set SEEN A @ Section 0, offset 0x{seen_a_offset + byte_index:X}")
        
        # SEEN B (Section 1)
        if section1_offset is not None:
            addr = section1_offset + seen_b_offset + byte_index
            if addr < len(save_data):
                old_val = save_data[addr]
                save_data[addr] |= bit_mask
                if save_data[addr] != old_val:
                    modified_sections.add((1, section1_offset))
                    print(f"[PokedexWriter] Set SEEN B @ Section 1, offset 0x{seen_b_offset + byte_index:X}")
        else:
            print("[PokedexWriter] WARNING: Could not find Section 1!")
        
        # SEEN C (Section 4)
        if section4_offset is not None:
            addr = section4_offset + seen_c_offset + byte_index
            if addr < len(save_data):
                old_val = save_data[addr]
                save_data[addr] |= bit_mask
                if save_data[addr] != old_val:
                    modified_sections.add((4, section4_offset))
                    print(f"[PokedexWriter] Set SEEN C @ Section 4, offset 0x{seen_c_offset + byte_index:X}")
        else:
            print("[PokedexWriter] WARNING: Could not find Section 4!")
    
    # Update checksums for all modified sections
    for section_id, section_offset in modified_sections:
        update_section_checksum(save_data, section_offset)
        print(f"[PokedexWriter] Updated Section {section_id} checksum")
    
    if modified_sections:
        print(f"[PokedexWriter] Successfully updated {len(modified_sections)} section(s)")
    
    return True


def unlock_national_pokedex(save_data, game_type='FRLG'):
    """
    Force unlock the National Pokedex in a save file.
    
    This is useful when transferring Pokemon with National Dex numbers > 151
    (for FRLG) or > 202 (for RSE) before the player has naturally unlocked
    the National Dex in-game.
    
    Args:
        save_data: Mutable bytearray of save file
        game_type: 'RSE', 'RS', 'E', or 'FRLG'
        
    Returns:
        bool: True if successful
    """
    block_offset = get_active_block(save_data)
    
    # Find needed sections
    section0_offset = find_section_by_id(save_data, block_offset, 0)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    section2_offset = find_section_by_id(save_data, block_offset, 2)
    
    if section0_offset is None:
        print("[PokedexWriter] Could not find Section 0")
        return False
    
    # Detect game type if generic
    detected_game = game_type
    if game_type in ('RSE', 'RS', 'E'):
        # Use helper to properly detect RS vs Emerald (they have different offsets!)
        detected_game = _detect_rse_subtype(save_data, section0_offset, section1_offset)
    
    modified_sections = set()
    
    if detected_game == 'FRLG':
        # FRLG National Dex unlock:
        # Field A: Section 0, offset 0x1B = 0xB9
        # Field B: Section 2, offset 0x68, bit 0 = 1
        # Field C: Section 2, offset 0x11C = 0x6258 (little-endian: 0x58, 0x62)
        
        # Field A
        addr_a = section0_offset + 0x1B
        if save_data[addr_a] != 0xB9:
            save_data[addr_a] = 0xB9
            modified_sections.add((0, section0_offset))
            print("[PokedexWriter] Set National Dex Field A (Section 0 @ 0x1B)")
        
        if section2_offset is not None:
            # Field B - set bit 0
            addr_b = section2_offset + 0x68
            if not (save_data[addr_b] & 0x01):
                save_data[addr_b] |= 0x01
                modified_sections.add((2, section2_offset))
                print("[PokedexWriter] Set National Dex Field B (Section 2 @ 0x68 bit 0)")
            
            # Field C
            addr_c = section2_offset + 0x11C
            current_c = struct.unpack('<H', save_data[addr_c:addr_c + 2])[0]
            if current_c != 0x6258:
                struct.pack_into('<H', save_data, addr_c, 0x6258)
                modified_sections.add((2, section2_offset))
                print("[PokedexWriter] Set National Dex Field C (Section 2 @ 0x11C)")
        else:
            print("[PokedexWriter] WARNING: Could not find Section 2 for FRLG National Dex")
    
    else:
        # RSE National Dex unlock:
        # Field A: Section 0, offset 0x19 = 0xDA, 0x01 (2 bytes, little-endian 0x01DA)
        # Field B: Section 2, offset 0x402 (E) or 0x3A6 (RS), bit 6 = 1
        # Field C: Section 2, offset 0x4A8 (E) or 0x44C (RS) = 0x0302 (little-endian: 0x02, 0x03)
        
        # Field A
        addr_a = section0_offset + 0x19
        current_a = struct.unpack('<H', save_data[addr_a:addr_a + 2])[0]
        if current_a != 0x01DA:
            struct.pack_into('<H', save_data, addr_a, 0x01DA)
            modified_sections.add((0, section0_offset))
            print("[PokedexWriter] Set National Dex Field A (Section 0 @ 0x19)")
        
        if section2_offset is not None:
            # Determine offsets based on RS vs E
            if detected_game == 'E':
                field_b_offset = 0x402
                field_c_offset = 0x4A8
            else:  # RS
                field_b_offset = 0x3A6
                field_c_offset = 0x44C
            
            # Field B - set bit 6
            addr_b = section2_offset + field_b_offset
            if not (save_data[addr_b] & 0x40):
                save_data[addr_b] |= 0x40
                modified_sections.add((2, section2_offset))
                print(f"[PokedexWriter] Set National Dex Field B (Section 2 @ 0x{field_b_offset:X} bit 6)")
            
            # Field C
            addr_c = section2_offset + field_c_offset
            current_c = struct.unpack('<H', save_data[addr_c:addr_c + 2])[0]
            if current_c != 0x0302:
                struct.pack_into('<H', save_data, addr_c, 0x0302)
                modified_sections.add((2, section2_offset))
                print(f"[PokedexWriter] Set National Dex Field C (Section 2 @ 0x{field_c_offset:X})")
        else:
            print("[PokedexWriter] WARNING: Could not find Section 2 for RSE National Dex")
    
    # Update checksums
    for section_id, section_offset in modified_sections:
        update_section_checksum(save_data, section_offset)
        print(f"[PokedexWriter] Updated Section {section_id} checksum")
    
    if modified_sections:
        print(f"[PokedexWriter] National Dex unlocked! ({len(modified_sections)} section(s) modified)")
        return True
    else:
        print("[PokedexWriter] National Dex was already unlocked")
        return True


def is_national_dex_unlocked(save_data, game_type='RSE'):
    """
    Check if the National Pokedex is unlocked in a save file.
    
    Args:
        save_data: Save file data
        game_type: 'RSE' or 'FRLG'
        
    Returns:
        bool: True if National Dex is unlocked
    """
    block_offset = get_active_block(save_data)
    section0_offset = find_section_by_id(save_data, block_offset, 0)
    
    if section0_offset is None:
        return False
    
    # Detect game type
    game_code = struct.unpack('<I', save_data[section0_offset + 0xAC:section0_offset + 0xB0])[0]
    
    if game_code == 1:  # FRLG
        # Check Field A
        return save_data[section0_offset + 0x1B] == 0xB9
    else:  # RSE
        # Check Field A
        val = struct.unpack('<H', save_data[section0_offset + 0x19:section0_offset + 0x1B])[0]
        return val == 0x01DA


def set_pokedex_flags_for_pokemon(save_data, pokemon_data, game_type='RSE'):
    """
    Set Pokedex flags for a Pokemon being transferred to this save.
    Marks the Pokemon as both seen and caught in the Pokedex.
    
    Note: For Pokemon outside the regional dex (>151 for FRLG, >202 for RSE),
    the flags will be set correctly but the Pokemon won't appear in the
    in-game Pokedex UI until the player naturally unlocks the National Dex.
    This is intentional to avoid breaking game progression.
    
    Args:
        save_data: Mutable bytearray of save file
        pokemon_data: Pokemon dict with 'species' key (national dex number)
                     or raw bytes (will extract species from bytes)
        game_type: 'RSE' or 'FRLG'
        
    Returns:
        bool: True if successful
    """
    # Get species number
    if isinstance(pokemon_data, dict):
        species = pokemon_data.get('species', 0)
        # Some Pokemon data stores species as internal index, need to convert
        # Check if we have a national_dex field
        if pokemon_data.get('national_dex'):
            species = pokemon_data['national_dex']
    else:
        # Extract species from raw bytes
        # Species is in the Growth substructure, which needs decryption
        # For simplicity, require dict with species already parsed
        print("[PokedexWriter] Raw bytes not supported, need parsed Pokemon dict")
        return False
    
    if species <= 0 or species > 386:
        print(f"[PokedexWriter] Invalid species: {species}")
        return False
    
    # Log if Pokemon is outside regional dex
    block_offset = get_active_block(save_data)
    section0_offset = find_section_by_id(save_data, block_offset, 0)
    if section0_offset:
        game_code = struct.unpack('<I', save_data[section0_offset + 0xAC:section0_offset + 0xB0])[0]
        is_frlg = (game_code == 1)
        
        if is_frlg and species > 151:
            print(f"[PokedexWriter] Species {species} is outside Kanto Dex - will appear after National Dex unlock")
        elif not is_frlg and species > 202:
            print(f"[PokedexWriter] Species {species} is outside Hoenn Dex - will appear after National Dex unlock")
    
    return set_pokedex_flag(save_data, species, seen=True, caught=True, game_type=game_type)


def get_pokedex_flags(save_data, species_national_dex, game_type='RSE'):
    """
    Get the seen and caught flags for a Pokemon species.
    
    Args:
        save_data: Save file data
        species_national_dex: National Pokedex number (1-386)
        game_type: 'RSE' or 'FRLG'
        
    Returns:
        dict: {'seen': bool, 'caught': bool} or None if error
    """
    if species_national_dex < 1 or species_national_dex > 386:
        return None
    
    # Calculate bit position
    byte_index = (species_national_dex - 1) // 8
    bit_index = (species_national_dex - 1) % 8
    bit_mask = 1 << bit_index
    
    # Get active block and find Section 0
    block_offset = get_active_block(save_data)
    section0_offset = find_section_by_id(save_data, block_offset, 0)
    
    if section0_offset is None:
        return None
    
    # Read OWNED flag from Section 0 @ 0x28
    owned_addr = section0_offset + 0x28 + byte_index
    caught = bool(save_data[owned_addr] & bit_mask) if owned_addr < len(save_data) else False
    
    # Read SEEN flag from Section 0 @ 0x5C (primary copy)
    seen_addr = section0_offset + 0x5C + byte_index
    seen = bool(save_data[seen_addr] & bit_mask) if seen_addr < len(save_data) else False
    
    return {'seen': seen, 'caught': caught}


def transfer_pokemon_with_pokedex(source_pokemon, dest_save_data, dest_game_type='RSE', 
                                   target_box=None, target_slot=None, update_pokedex=True):
    """
    Transfer a Pokemon to a destination save and optionally update the Pokedex.
    
    Args:
        source_pokemon: Pokemon dict with 'raw_bytes' and 'species' keys
        dest_save_data: Mutable bytearray of destination save
        dest_game_type: Game type of destination save
        target_box: Specific box to place in (None = first empty)
        target_slot: Specific slot to place in (None = first empty)
        update_pokedex: Whether to mark the Pokemon as seen/caught
        
    Returns:
        tuple: (success, box_number, slot_number, message)
    """
    # First do the transfer
    success, box_num, slot_num, message = transfer_pokemon(
        source_pokemon, dest_save_data, dest_game_type, target_box, target_slot
    )
    
    if not success:
        return (success, box_num, slot_num, message)
    
    # Update Pokedex if requested
    if update_pokedex and isinstance(source_pokemon, dict):
        species = source_pokemon.get('species', 0)
        # Try to get national dex number
        if source_pokemon.get('national_dex'):
            species = source_pokemon['national_dex']
        
        if species > 0 and species <= 386:
            pokedex_result = set_pokedex_flag(dest_save_data, species, seen=True, caught=True, game_type=dest_game_type)
            if pokedex_result:
                pokemon_name = source_pokemon.get('nickname') or source_pokemon.get('species_name', 'Pokemon')
                message += f" (Added #{species} to Pokedex)"
    
    return (success, box_num, slot_num, message)

# =============================================================================
# ITEM WRITING FUNCTIONS
# =============================================================================

# Item Pocket offsets
ITEM_POCKET_OFFSETS = {
    'FRLG': {
        'items': (0x0310, 42),
        'key_items': (0x03B8, 30),
        'pokeballs': (0x0430, 13),
        'tms_hms': (0x0464, 58),
        'berries': (0x054C, 43),
    },
    'RSE': {
        'items': (0x0560, 20),
        'key_items': (0x05B0, 20),
        'pokeballs': (0x0600, 16),
        'tms_hms': (0x0640, 64),
        'berries': (0x0740, 46),
    }
}

# Event Item IDs
EVENT_ITEMS = {
    'eon_ticket': {'id': 275, 'name': 'Eon Ticket', 'desc': 'Enables access to Southern Island (Latios/Latias)'},
    'aurora_ticket': {'id': 371, 'name': 'Aurora Ticket', 'desc': 'Enables access to Birth Island (Deoxys)'},
    'mystic_ticket': {'id': 370, 'name': 'Mystic Ticket', 'desc': 'Enables access to Navel Rock (Ho-Oh/Lugia)'},
    'old_sea_map': {'id': 376, 'name': 'Old Sea Map', 'desc': 'Enables access to Faraway Island (Mew)'},
}

# Game compatibility for event items
EVENT_ITEM_COMPATIBILITY = {
    'eon_ticket': ['Ruby', 'Sapphire', 'Emerald'],
    'aurora_ticket': ['FireRed', 'LeafGreen', 'Emerald'],
    'mystic_ticket': ['FireRed', 'LeafGreen', 'Emerald'],
    'old_sea_map': ['Emerald'],
}


def get_item_encryption_key(save_data, section1_offset, game_type=None):
    """
    Get the item encryption key.
    
    IMPORTANT: Different games store the key in different locations:
    - Ruby/Sapphire: No encryption (returns 0)
    - Emerald: Section 0 + 0x00AC (32-bit key, use lower 16 bits)
    - FRLG: Section 0 + 0x0F20 (32-bit key, use lower 16 bits)
    
    For backwards compatibility, if game_type is not specified, we try to detect
    based on the key value, but this may not be reliable.
    """
    # If game_type is explicitly RS, no encryption
    if game_type in ('RS', 'R', 'S', 'Ruby', 'Sapphire'):
        return 0
    
    # For FRLG and Emerald, we need Section 0, not Section 1
    # Find Section 0
    block_offset = get_active_block(save_data)
    section0_offset = find_section_by_id(save_data, block_offset, 0)
    
    if section0_offset is None:
        print("[ItemWriter] WARNING: Could not find Section 0 for encryption key")
        return 0
    
    if game_type in ('FRLG', 'FR', 'LG', 'FireRed', 'LeafGreen'):
        # FRLG: key at Section 0 + 0x0F20
        key_offset = section0_offset + 0x0F20
    elif game_type in ('E', 'Emerald'):
        # Emerald: key at Section 0 + 0x00AC
        key_offset = section0_offset + 0x00AC
    else:
        # Unknown game type - try FRLG offset first, then Emerald
        # This is a fallback for backwards compatibility
        key_frlg = struct.unpack('<I', save_data[section0_offset + 0x0F20:section0_offset + 0x0F24])[0]
        key_e = struct.unpack('<I', save_data[section0_offset + 0x00AC:section0_offset + 0x00B0])[0]
        
        # Use whichever is non-zero, preferring FRLG
        if key_frlg != 0:
            return key_frlg & 0xFFFF
        elif key_e != 0:
            return key_e & 0xFFFF
        return 0
    
    # Read 32-bit key and return lower 16 bits
    key_32bit = struct.unpack('<I', save_data[key_offset:key_offset + 4])[0]
    return key_32bit & 0xFFFF


def find_item_in_pocket(save_data, section1_offset, game_type, pocket_name, item_id):
    """
    Find an item in a specific pocket.
    Returns: int: Slot index if found, -1 if not found
    """
    # Normalize game type
    if game_type in ('E', 'RS', 'R', 'S', 'Emerald', 'Ruby', 'Sapphire'):
        game_type = 'RSE'
    elif game_type in ('FRLG', 'FR', 'LG', 'FireRed', 'LeafGreen'):
        game_type = 'FRLG'
    
    pocket_config = ITEM_POCKET_OFFSETS.get(game_type, ITEM_POCKET_OFFSETS['RSE'])
    if pocket_name not in pocket_config:
        return -1
    
    offset, max_slots = pocket_config[pocket_name]
    pocket_offset = section1_offset + offset
    
    for slot in range(max_slots):
        slot_offset = pocket_offset + (slot * 4)
        if slot_offset + 4 > len(save_data):
            break
        slot_item_id = struct.unpack('<H', save_data[slot_offset:slot_offset + 2])[0]
        if slot_item_id == item_id:
            return slot
    return -1


def find_empty_slot_in_pocket(save_data, section1_offset, game_type, pocket_name):
    """
    Find the first empty slot in a pocket.
    Returns: int: Slot index if found, -1 if pocket is full
    """
    # Normalize game type
    if game_type in ('E', 'RS', 'R', 'S', 'Emerald', 'Ruby', 'Sapphire'):
        game_type = 'RSE'
    elif game_type in ('FRLG', 'FR', 'LG', 'FireRed', 'LeafGreen'):
        game_type = 'FRLG'
    
    pocket_config = ITEM_POCKET_OFFSETS.get(game_type, ITEM_POCKET_OFFSETS['RSE'])
    if pocket_name not in pocket_config:
        return -1
    
    offset, max_slots = pocket_config[pocket_name]
    pocket_offset = section1_offset + offset
    
    for slot in range(max_slots):
        slot_offset = pocket_offset + (slot * 4)
        if slot_offset + 4 > len(save_data):
            break
        slot_item_id = struct.unpack('<H', save_data[slot_offset:slot_offset + 2])[0]
        if slot_item_id == 0:
            return slot
    return -1


def add_item_to_pocket(save_data, game_type, pocket_name, item_id, quantity=1):
    """
    Add an item to a specific pocket in the bag.
    If the item already exists, increases quantity (up to 999).
    
    NOTE: Ruby/Sapphire do NOT encrypt key items - they store raw quantities.
    Emerald and FRLG DO encrypt key items (and all other pockets).
    
    Returns: tuple: (success: bool, message: str)
    """
    # Normalize game type but remember if it's specifically RS (not Emerald)
    is_ruby_sapphire = game_type in ('RS', 'R', 'S', 'Ruby', 'Sapphire')
    
    if game_type in ('E', 'RS', 'R', 'S', 'Emerald', 'Ruby', 'Sapphire'):
        normalized_type = 'RSE'
    elif game_type in ('FRLG', 'FR', 'LG', 'FireRed', 'LeafGreen'):
        normalized_type = 'FRLG'
    else:
        normalized_type = game_type
    
    block_offset = get_active_block(save_data)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    
    if section1_offset is None:
        return (False, "Could not find Section 1")
    
    # Ruby/Sapphire do NOT encrypt key items - they store raw quantity values
    # Emerald and FRLG DO encrypt key items
    skip_encryption = (pocket_name == 'key_items' and is_ruby_sapphire)
    
    if skip_encryption:
        item_key = 0  # No encryption for RS key items
    else:
        item_key = get_item_encryption_key(save_data, section1_offset, game_type)
    
    pocket_config = ITEM_POCKET_OFFSETS.get(normalized_type, ITEM_POCKET_OFFSETS['RSE'])
    if pocket_name not in pocket_config:
        return (False, f"Invalid pocket: {pocket_name}")
    
    offset, max_slots = pocket_config[pocket_name]
    pocket_offset = section1_offset + offset
    
    existing_slot = find_item_in_pocket(save_data, section1_offset, normalized_type, pocket_name, item_id)
    
    if existing_slot >= 0:
        slot_offset = pocket_offset + (existing_slot * 4)
        raw_qty = struct.unpack('<H', save_data[slot_offset + 2:slot_offset + 4])[0]
        current_qty = raw_qty if skip_encryption else (raw_qty ^ item_key)
        new_qty = min(999, current_qty + quantity)
        new_qty_stored = new_qty if skip_encryption else (new_qty ^ item_key)
        struct.pack_into('<H', save_data, slot_offset + 2, new_qty_stored)
        print(f"[ItemWriter] Increased {item_id} quantity: {current_qty} -> {new_qty}")
    else:
        empty_slot = find_empty_slot_in_pocket(save_data, section1_offset, normalized_type, pocket_name)
        if empty_slot < 0:
            return (False, f"Pocket {pocket_name} is full!")
        slot_offset = pocket_offset + (empty_slot * 4)
        struct.pack_into('<H', save_data, slot_offset, item_id)
        qty_stored = quantity if skip_encryption else (quantity ^ item_key)
        struct.pack_into('<H', save_data, slot_offset + 2, qty_stored)
        print(f"[ItemWriter] Added item {item_id} x{quantity} to slot {empty_slot} (skip_encrypt={skip_encryption})")
    
    update_section_checksum(save_data, section1_offset)
    return (True, f"Added item {item_id} x{quantity}")


def add_event_item(save_data, game_type, game_name, event_key):
    """
    Add an event item to the save file's key items pocket.
    Also sets the enable flags so NPCs recognize the ticket.
    
    Returns: tuple: (success: bool, message: str)
    """
    if event_key not in EVENT_ITEMS:
        return (False, f"Unknown event: {event_key}")
    
    event_info = EVENT_ITEMS[event_key]
    item_id = event_info['id']
    item_name = event_info['name']
    
    compatible_games = EVENT_ITEM_COMPATIBILITY.get(event_key, [])
    if game_name not in compatible_games:
        return (False, f"{item_name} is not compatible with {game_name}")
    
    block_offset = get_active_block(save_data)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    
    if section1_offset is None:
        return (False, "Could not find Section 1")
    
    existing = find_item_in_pocket(save_data, section1_offset, game_type, 'key_items', item_id)
    if existing >= 0:
        return (False, f"You already have {item_name}!")
    
    # Add the item to key items pocket
    success, msg = add_item_to_pocket(save_data, game_type, 'key_items', item_id, quantity=1)
    
    if success:
        # Set the enable flags so NPCs recognize the ticket
        flag_success, flags_set = set_event_enable_flags(save_data, game_type, game_name, event_key)
        if flag_success and flags_set > 0:
            print(f"[EventItem] Added {item_name} and set {flags_set} enable flag(s)")
        elif flag_success:
            print(f"[EventItem] Added {item_name} (no enable flags defined for this game)")
        else:
            print(f"[EventItem] Added {item_name} but WARNING: failed to set enable flags")
        
        return (True, f"Received {item_name}!")
    else:
        return (False, msg)


def has_event_item(save_data, game_type, event_key):
    """
    Check if the save file has a specific event item.
    Returns: bool: True if the item is in the key items pocket
    """
    if event_key not in EVENT_ITEMS:
        return False
    
    item_id = EVENT_ITEMS[event_key]['id']
    
    block_offset = get_active_block(save_data)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    
    if section1_offset is None:
        return False
    
    return find_item_in_pocket(save_data, section1_offset, game_type, 'key_items', item_id) >= 0


def get_available_events_for_game(game_name):
    """
    Get list of event items available for a specific game.
    Returns: list: List of event keys available for this game
    """
    available = []
    for event_key, compatible_games in EVENT_ITEM_COMPATIBILITY.items():
        if game_name in compatible_games:
            available.append(event_key)
    return available


# =============================================================================
# FRLG EVENT PREREQUISITE CHECKS
# =============================================================================
# FireRed/LeafGreen have additional requirements for event items:
# - National Dex must be unlocked
# - Rainbow Pass must be obtained (required for Sevii Islands 4-7)

RAINBOW_PASS_ITEM_ID = 368  # Key item that unlocks Sevii Islands 4-7

# Flag IDs for National Dex unlock
NATIONAL_DEX_FLAGS = {
    'FRLG': 0x840,  # FLAG_SYS_NATIONAL_DEX in pokefirered
    'RSE': 0x860,   # FLAG_SYS_NATIONAL_DEX in pokeemerald (not used for gating, but available)
}


def has_national_dex(save_data, game_type, game_name=None):
    """
    Check if the National Dex has been unlocked.
    
    Args:
        save_data: Save file data
        game_type: 'RSE' or 'FRLG'
        game_name: Optional game name for accurate flag reading
        
    Returns:
        bool: True if National Dex is unlocked
    """
    block_offset = get_active_block(save_data)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    
    if section1_offset is None:
        return False
    
    flag_id = NATIONAL_DEX_FLAGS.get(game_type, NATIONAL_DEX_FLAGS['RSE'])
    return get_flag_value(save_data, section1_offset, game_type, flag_id, game_name)


def has_rainbow_pass(save_data, game_type):
    """
    Check if the Rainbow Pass has been obtained (FRLG only).
    The Rainbow Pass allows access to Sevii Islands 4-7.
    
    Args:
        save_data: Save file data
        game_type: 'RSE' or 'FRLG'
        
    Returns:
        bool: True if Rainbow Pass is in key items
    """
    if game_type != 'FRLG':
        return True  # Not required for RSE games
    
    block_offset = get_active_block(save_data)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    
    if section1_offset is None:
        return False
    
    return find_item_in_pocket(save_data, section1_offset, game_type, 'key_items', RAINBOW_PASS_ITEM_ID) >= 0


def check_frlg_event_prerequisites(save_data, game_type, game_name):
    """
    Check if FRLG event prerequisites are met.
    For FireRed/LeafGreen, events require:
    - National Dex unlocked
    - Rainbow Pass obtained
    
    Args:
        save_data: Save file data
        game_type: 'RSE' or 'FRLG'
        game_name: Full game name
        
    Returns:
        tuple: (all_met: bool, details: dict)
    """
    # RSE games don't have additional prerequisites
    if game_name not in ('FireRed', 'LeafGreen'):
        return (True, {'game': game_name, 'required': False})
    
    has_nat_dex = has_national_dex(save_data, game_type, game_name)
    has_pass = has_rainbow_pass(save_data, game_type)
    
    details = {
        'game': game_name,
        'required': True,
        'national_dex': has_nat_dex,
        'rainbow_pass': has_pass,
    }
    
    all_met = has_nat_dex and has_pass
    
    if not all_met:
        print(f"[EventPrereqs] FRLG prerequisites not met: National Dex={has_nat_dex}, Rainbow Pass={has_pass}")
    
    return (all_met, details)


# =============================================================================
# SINEW OT DETECTION FOR EVENT COMPLETION
# =============================================================================
# When checking if an event is "truly complete", we need to distinguish between:
# - Pokemon received as Sinew achievement rewards (OT = "SINEW")
# - Pokemon legitimately caught at the event location (OT = player's name)
#
# If the completion flag is set but the only Pokemon of that species has OT "SINEW",
# the player hasn't actually done the event - they just got the reward Pokemon.

SINEW_OT_NAME = "SINEW"

# Species IDs for event Pokemon (to avoid circular import with events_screen)
EVENT_POKEMON_IDS = {
    'eon_ticket': [380, 381],      # Latias, Latios
    'aurora_ticket': [386],         # Deoxys
    'mystic_ticket': [249, 250],    # Lugia, Ho-Oh
    'old_sea_map': [151],           # Mew
}


def find_pokemon_by_species(party, pc_pokemon, species_ids):
    """
    Find all Pokemon of specified species in party and PC.
    
    Args:
        party: List of party Pokemon dicts
        pc_pokemon: List of PC Pokemon dicts
        species_ids: List of species IDs to search for
        
    Returns:
        list: List of matching Pokemon dicts
    """
    matches = []
    
    # Search party
    for poke in party:
        if poke and not poke.get('empty', False):
            if poke.get('species') in species_ids:
                matches.append(poke)
    
    # Search PC
    for poke in pc_pokemon:
        if poke and not poke.get('empty', False):
            if poke.get('species') in species_ids:
                matches.append(poke)
    
    return matches


def has_non_sinew_pokemon(party, pc_pokemon, species_ids):
    """
    Check if any Pokemon of the specified species has an OT other than "SINEW".
    This indicates the player legitimately caught the Pokemon.
    
    Args:
        party: List of party Pokemon dicts
        pc_pokemon: List of PC Pokemon dicts
        species_ids: List of species IDs to check
        
    Returns:
        bool: True if at least one matching Pokemon has OT != "SINEW"
    """
    matches = find_pokemon_by_species(party, pc_pokemon, species_ids)
    
    for poke in matches:
        ot_name = poke.get('ot_name', '').strip().upper()
        if ot_name and ot_name != SINEW_OT_NAME:
            print(f"[SinewOT] Found species {poke.get('species')} with OT '{ot_name}' (not SINEW)")
            return True
    
    if matches:
        print(f"[SinewOT] Found {len(matches)} Pokemon of species {species_ids}, but all have OT='SINEW'")
    else:
        print(f"[SinewOT] No Pokemon found with species {species_ids}")
    
    return False


def is_event_truly_complete(save_data, game_type, game_name, event_key, party=None, pc_pokemon=None):
    """
    Check if an event is truly complete.
    
    SIMPLIFIED: We no longer track completion status for events.
    The events system's purpose is to give players access to event locations,
    and completion tracking was unreliable across different games/saves.
    
    Events will show as:
    - "Available" if player doesn't have the ticket
    - "Owned" if player has the ticket
    
    Args:
        save_data: Save file data (bytearray)
        game_type: 'RSE' or 'FRLG'
        game_name: Full game name ('Ruby', 'Emerald', 'FireRed', etc.)
        event_key: Event key ('eon_ticket', 'aurora_ticket', etc.)
        party: Optional list of party Pokemon dicts (unused)
        pc_pokemon: Optional list of PC Pokemon dicts (unused)
        
    Returns:
        dict: Always returns complete=False to show "Owned" instead of "Complete"
    """
    # Always return incomplete - we only track Available vs Owned now
    return {
        'complete': False,
        'flag_set': False,
        'has_legit_catch': False,
        'reason': 'Completion tracking disabled - events show as Available or Owned'
    }


# =============================================================================
# EVENT ENCOUNTER FLAGS - Track if legendary was caught/defeated at location
# =============================================================================

# Flag offsets within saveBlock1 for each game
# Ruby/Sapphire and Emerald have different internal structures
EVENT_FLAG_OFFSETS = {
    'RS': 0x1220,    # Ruby/Sapphire flags offset in saveBlock1
    'E': 0x1270,     # Emerald flags offset in saveBlock1
    'RSE': 0x1270,   # Fallback (Emerald offset) - for backwards compatibility
    'FRLG': 0x0EE0,  # FireRed/LeafGreen flags offset
}

# Event encounter flag IDs - these track if the Pokemon at the event location
# has been caught or defeated (prevents respawn)
# Flag IDs are from the game's decompilation projects (pokeemerald, pokefirered)

EVENT_ENCOUNTER_FLAGS = {
    # Emerald has all 4 events
    'Emerald': {
        'eon_ticket': [0x862],           # FLAG_DEFEATED_LATIAS_OR_LATIOS (Southern Island)
        'aurora_ticket': [0x86D],        # FLAG_DEFEATED_DEOXYS (Birth Island)
        'mystic_ticket': [0x86B, 0x86C], # FLAG_DEFEATED_HO_OH, FLAG_DEFEATED_LUGIA (Navel Rock)
        'old_sea_map': [0x86E],          # FLAG_DEFEATED_MEW (Faraway Island)
    },
    # Ruby/Sapphire only have Eon Ticket event
    # NOTE: R/S use 0x85A for completion - 0x860 is set just by arriving at island!
    # Verified by comparing Ruby (incomplete) vs Sapphire (complete) saves
    'Ruby': {
        'eon_ticket': [0x85A],           # FLAG_DEFEATED_LATIAS_OR_LATIOS (R/S actual completion flag)
    },
    'Sapphire': {
        'eon_ticket': [0x85A],           # FLAG_DEFEATED_LATIAS_OR_LATIOS (R/S actual completion flag)
    },
    # FireRed/LeafGreen have Aurora and Mystic Ticket events
    'FireRed': {
        'aurora_ticket': [0x290],        # FLAG_DEFEATED_DEOXYS (Birth Island)
        'mystic_ticket': [0x291, 0x292], # FLAG_DEFEATED_LUGIA, FLAG_DEFEATED_HO_OH (Navel Rock)
    },
    'LeafGreen': {
        'aurora_ticket': [0x290],        # FLAG_DEFEATED_DEOXYS
        'mystic_ticket': [0x291, 0x292], # FLAG_DEFEATED_LUGIA, FLAG_DEFEATED_HO_OH
    },
}

# =============================================================================
# EVENT ENABLE FLAGS - Must be set for NPCs to recognize tickets
# =============================================================================
# These flags tell the game that the player has received the event ticket
# through official distribution. Without these, NPCs won't offer ferry rides.
# Flag IDs from pokeemerald/pokefirered decompilation projects.

EVENT_ENABLE_FLAGS = {
    # Emerald enable flags (from Project Pokemon research)
    # Southern Island via Mixing Records: 2227 (0x8B3) - FLAG_SYS_HAS_EON_TICKET
    # Birth Island: 0314 (0x13A) + 2261 (0x8D5)
    # Navel Rock: 0315 (0x13B) + 2272 (0x8E0)
    # Faraway Island: 0316 (0x13C) + 2262 (0x8D6)
    'Emerald': {
        'eon_ticket': [0x8B3],              # FLAG_SYS_HAS_EON_TICKET (2227) - Southern Island
        'aurora_ticket': [0x13A, 0x8D5],    # Birth Island: 0314 + 2261
        'mystic_ticket': [0x13B, 0x8E0],    # Navel Rock: 0315 + 2272
        'old_sea_map': [0x13C, 0x8D6],      # Faraway Island: 0316 + 2262
    },
    # Ruby/Sapphire enable flags (from Project Pokemon research)
    # Receiving Eon Ticket from e-card: 2100 (0x834), 2124 (0x84C)
    # Southern Island from Norman: 2131 (0x853)
    'Ruby': {
        'eon_ticket': [0x853, 0x834, 0x84C],  # Southern Island (2131) + e-card flags (2100, 2124)
    },
    'Sapphire': {
        'eon_ticket': [0x853, 0x834, 0x84C],  # Southern Island (2131) + e-card flags (2100, 2124)
    },
    # FireRed/LeafGreen enable flags (from Project Pokemon research)
    # Mystic Ticket (Navel Rock): 2122 (0x84A) + 2123 (0x84B)
    # Aurora Ticket (Birth Island): Same flags work for both tickets
    'FireRed': {
        'aurora_ticket': [0x84A, 0x84B],  # 2122 + 2123 - enables Birth Island
        'mystic_ticket': [0x84A, 0x84B],  # 2122 + 2123 - enables Navel Rock
    },
    'LeafGreen': {
        'aurora_ticket': [0x84A, 0x84B],  # 2122 + 2123 - enables Birth Island
        'mystic_ticket': [0x84A, 0x84B],  # 2122 + 2123 - enables Navel Rock
    },
}


def get_flag_value(save_data, section1_offset, game_type, flag_id, game_name=None):
    """
    Read a single flag value from the save data.
    
    NOTE: Flags are stored in SaveBlock1 which spans multiple sections.
    This function handles the multi-section layout properly.
    
    Args:
        save_data: Save file data
        section1_offset: Offset to Section 1 (used to find the active block)
        game_type: 'RSE' or 'FRLG'
        flag_id: The flag ID to check
        game_name: Optional specific game name ('Ruby', 'Sapphire', 'Emerald', etc.)
        
    Returns:
        bool: True if flag is set, False otherwise
    """
    try:
        # Get flags base offset within SaveBlock1
        if game_name in ('Ruby', 'Sapphire'):
            flags_base = EVENT_FLAG_OFFSETS.get('RS', 0x1220)
        elif game_name == 'Emerald':
            flags_base = EVENT_FLAG_OFFSETS.get('E', 0x1270)
        elif game_type == 'FRLG':
            flags_base = EVENT_FLAG_OFFSETS.get('FRLG', 0x0EE0)
        else:
            flags_base = 0x1270  # Default to Emerald
        
        # Calculate offset within SaveBlock1
        saveblock1_offset = flags_base + (flag_id // 8)
        bit_position = flag_id % 8
        
        # SaveBlock1 spans sections 1-4, each section has 3968 bytes (0xF80) of data
        # (except section 4 which has 2000 bytes)
        SECTION_DATA_SIZE = 0xF80  # 3968 bytes per section
        
        # Determine which section this offset falls into
        section_num = saveblock1_offset // SECTION_DATA_SIZE  # 0=sec1, 1=sec2, etc.
        offset_in_section = saveblock1_offset % SECTION_DATA_SIZE
        
        # The actual section ID is section_num + 1 (since Section 0 is trainer data)
        target_section_id = section_num + 1
        
        # Find the physical offset of the target section
        block_offset = get_active_block(save_data)
        target_section_offset = find_section_by_id(save_data, block_offset, target_section_id)
        
        if target_section_offset is None:
            print(f"[FlagRead] Could not find Section {target_section_id}")
            return False
        
        # Read the flag byte
        byte_offset = target_section_offset + offset_in_section
        if byte_offset >= len(save_data):
            return False
        
        flag_byte = save_data[byte_offset]
        is_set = (flag_byte >> bit_position) & 1
        
        return bool(is_set)
        
    except Exception as e:
        print(f"[FlagRead] Error reading flag {flag_id}: {e}")
        return False


def set_flag_value(save_data, section1_offset, game_type, flag_id, value=True, game_name=None):
    """
    Set a single flag value in the save data.
    
    NOTE: Flags are stored in SaveBlock1 which spans multiple sections.
    This function handles the multi-section layout and updates the correct checksum.
    
    Args:
        save_data: Save file data (mutable bytearray)
        section1_offset: Offset to Section 1 (used to find the active block)
        game_type: 'RSE' or 'FRLG'
        flag_id: The flag ID to set
        value: True to set the flag, False to clear it
        game_name: Optional specific game name ('Ruby', 'Sapphire', 'Emerald', etc.)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get flags base offset within SaveBlock1
        if game_name in ('Ruby', 'Sapphire'):
            flags_base = EVENT_FLAG_OFFSETS.get('RS', 0x1220)
        elif game_name == 'Emerald':
            flags_base = EVENT_FLAG_OFFSETS.get('E', 0x1270)
        elif game_type == 'FRLG':
            flags_base = EVENT_FLAG_OFFSETS.get('FRLG', 0x0EE0)
        else:
            flags_base = 0x1270  # Default to Emerald
        
        # Calculate offset within SaveBlock1
        saveblock1_offset = flags_base + (flag_id // 8)
        bit_position = flag_id % 8
        
        # SaveBlock1 spans sections 1-4, each section has 3968 bytes (0xF80) of data
        SECTION_DATA_SIZE = 0xF80  # 3968 bytes per section
        
        # Determine which section this offset falls into
        section_num = saveblock1_offset // SECTION_DATA_SIZE  # 0=sec1, 1=sec2, etc.
        offset_in_section = saveblock1_offset % SECTION_DATA_SIZE
        
        # The actual section ID is section_num + 1 (since Section 0 is trainer data)
        target_section_id = section_num + 1
        
        # Find the physical offset of the target section
        block_offset = get_active_block(save_data)
        target_section_offset = find_section_by_id(save_data, block_offset, target_section_id)
        
        if target_section_offset is None:
            print(f"[FlagWrite] Could not find Section {target_section_id}")
            return False
        
        # Calculate the actual byte offset in the save file
        byte_offset = target_section_offset + offset_in_section
        
        if byte_offset >= len(save_data):
            print(f"[FlagWrite] Byte offset 0x{byte_offset:X} out of bounds")
            return False
        
        # Read current byte, modify the bit, write back
        current_byte = save_data[byte_offset]
        if value:
            new_byte = current_byte | (1 << bit_position)
        else:
            new_byte = current_byte & ~(1 << bit_position)
        
        save_data[byte_offset] = new_byte
        
        # Update the checksum for the section we just modified
        update_section_checksum(save_data, target_section_offset)
        
        print(f"[FlagWrite] Set flag 0x{flag_id:X} in Section {target_section_id} at offset 0x{offset_in_section:X}")
        return True
        
    except Exception as e:
        print(f"[FlagWrite] Error setting flag {flag_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def set_event_enable_flags(save_data, game_type, game_name, event_key):
    """
    Set all enable flags for an event ticket.
    These flags make NPCs recognize that the player has the event ticket.
    
    Args:
        save_data: Save file data (mutable bytearray)
        game_type: 'RSE' or 'FRLG'
        game_name: Full game name ('Ruby', 'Emerald', 'FireRed', etc.)
        event_key: Event key ('eon_ticket', 'aurora_ticket', etc.)
        
    Returns:
        tuple: (success: bool, flags_set: int)
    """
    # Get enable flags for this game/event
    game_flags = EVENT_ENABLE_FLAGS.get(game_name, {})
    enable_flags = game_flags.get(event_key, [])
    
    if not enable_flags:
        print(f"[FlagWriter] No enable flags defined for {event_key} in {game_name}")
        return (True, 0)  # Not an error, just no flags to set
    
    # Get Section 1 offset
    block_offset = get_active_block(save_data)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    
    if section1_offset is None:
        return (False, 0)
    
    # Set all enable flags
    flags_set = 0
    for flag_id in enable_flags:
        if set_flag_value(save_data, section1_offset, game_type, flag_id, True, game_name):
            flags_set += 1
    
    # Note: set_flag_value now handles checksum updates for each section it modifies
    
    print(f"[FlagWriter] Set {flags_set}/{len(enable_flags)} enable flags for {event_key}")
    return (True, flags_set)


def is_event_encounter_complete(save_data, game_type, game_name, event_key):
    """
    Check if an event encounter has been completed (Pokemon caught/defeated at location).
    
    For events with multiple Pokemon (Mystic Ticket has Ho-Oh AND Lugia),
    returns True only if ALL Pokemon have been caught/defeated.
    
    Args:
        save_data: Save file data
        game_type: 'RSE' or 'FRLG'
        game_name: Full game name ('Ruby', 'Emerald', 'FireRed', etc.)
        event_key: Event key ('eon_ticket', 'aurora_ticket', etc.)
        
    Returns:
        bool: True if all event Pokemon have been caught/defeated at their location
    """
    # Get flags for this game
    game_flags = EVENT_ENCOUNTER_FLAGS.get(game_name, {})
    event_flags = game_flags.get(event_key, [])
    
    if not event_flags:
        # No flags defined for this event/game combo
        return False
    
    # Get Section 1 offset
    block_offset = get_active_block(save_data)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    
    if section1_offset is None:
        return False
    
    # Check all flags for this event - ALL must be set for completion
    all_set = True
    for flag_id in event_flags:
        flag_set = get_flag_value(save_data, section1_offset, game_type, flag_id, game_name)
        if not flag_set:
            all_set = False
            break
    
    return all_set


def get_event_completion_status(save_data, game_type, game_name, event_key):
    """
    Get detailed completion status for an event.
    
    Returns:
        dict: {
            'complete': bool - All Pokemon caught/defeated
            'flags_checked': int - Number of flags checked
            'flags_set': int - Number of flags that are set
            'details': list - Per-flag status
        }
    """
    game_flags = EVENT_ENCOUNTER_FLAGS.get(game_name, {})
    event_flags = game_flags.get(event_key, [])
    
    result = {
        'complete': False,
        'flags_checked': len(event_flags),
        'flags_set': 0,
        'details': []
    }
    
    if not event_flags:
        return result
    
    block_offset = get_active_block(save_data)
    section1_offset = find_section_by_id(save_data, block_offset, 1)
    
    if section1_offset is None:
        return result
    
    for flag_id in event_flags:
        flag_set = get_flag_value(save_data, section1_offset, game_type, flag_id, game_name)
        result['details'].append({
            'flag_id': flag_id,
            'set': flag_set
        })
        if flag_set:
            result['flags_set'] += 1
    
    result['complete'] = (result['flags_set'] == result['flags_checked'])
    
    return result