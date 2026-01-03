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
    if box_number < 1 or box_number > 14:
        raise ValueError(f"Invalid box number: {box_number} (must be 1-14)")
    if slot_number < 0 or slot_number >= BOX_SIZE:
        raise ValueError(f"Invalid slot number: {slot_number} (must be 0-29)")
    
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
    
    # Find the section
    section_offset = find_section_by_id(save_data, block_offset, section_index)
    if section_offset is None:
        raise ValueError(f"Could not find section {section_index}")
    
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
    if game_type in ('RSE', 'RS'):
        # Check game code at Section 0 offset 0xAC
        game_code = struct.unpack('<I', save_data[section0_offset + 0xAC:section0_offset + 0xB0])[0]
        if game_code == 1:
            detected_game = 'FRLG'
        else:
            # Try to detect Emerald vs RS by checking security key location
            # Emerald has security key at 0xAC, RS doesn't use encryption
            # For safety, default to Emerald offsets (most common)
            detected_game = 'E'
    
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
    section2_offset = find_section_by_id(save_data, block_offset, 2)
    
    if section0_offset is None:
        print("[PokedexWriter] Could not find Section 0")
        return False
    
    # Detect game type if generic
    detected_game = game_type
    if game_type in ('RSE', 'RS'):
        game_code = struct.unpack('<I', save_data[section0_offset + 0xAC:section0_offset + 0xB0])[0]
        if game_code == 1:
            detected_game = 'FRLG'
        else:
            detected_game = 'E'
    
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