"""
Gen 3 Pokemon Save Parser - Save Structure Module
Handles save file sections, validation, and game detection
"""

import struct

# Section sizes for each section ID
SECTION_SIZES = {
    0: 3884,  # Trainer info
    1: 3968,  # Team/Items
    2: 3968,  # Game state
    3: 3968,  # Misc data
    4: 3848,  # Rival info
    5: 3968,  # PC buffer A
    6: 3968,  # PC buffer B
    7: 3968,  # PC buffer C
    8: 3968,  # PC buffer D
    9: 3968,  # PC buffer E
    10: 3968,  # PC buffer F
    11: 3968,  # PC buffer G
    12: 3968,  # PC buffer H
    13: 2000,  # PC buffer I
}


def find_active_save_slot(data):
    """
    Find the most recent valid save slot (A or B).

    Gen 3 saves have two slots at 0x0000 and 0xE000.
    The one with the higher save index is more recent.

    Args:
        data: Save file data

    Returns:
        int: Base offset of active save slot (0x0000 or 0xE000)
    """
    # Save index is stored at offset 0x0FFC within each slot
    try:
        save_index_a = struct.unpack("<I", data[0x0FFC:0x1000])[0]
        save_index_b = struct.unpack("<I", data[0xEFFC:0xF000])[0]

        # Handle wraparound (save index is 32-bit)
        # If difference is huge, one has wrapped
        if save_index_a > save_index_b:
            if (save_index_a - save_index_b) > 0x80000000:
                return 0xE000  # B wrapped around, B is newer
            return 0x0000  # A is newer
        else:
            if (save_index_b - save_index_a) > 0x80000000:
                return 0x0000  # A wrapped around, A is newer
            return 0xE000  # B is newer

    except Exception:
        return 0x0000  # Default to slot A


def is_blank_save(data):
    """
    Check if save file is blank (uninitialized).

    Gen3 saves have section IDs at offset 0xFF4 within each 0x1000 byte section.
    A blank save has 0xFFFF at this location. Since Gen3 has two save slots,
    the save is only truly blank if BOTH slots are blank.

    Args:
        data: Save file data

    Returns:
        bool: True if save is blank/uninitialized
    """
    if len(data) < 0x1000:
        return True

    # Check section ID at offset 0xFF4 in first section of Slot A (offset 0x0000)
    section_id_a = data[0xFF4] | (data[0xFF5] << 8)
    slot_a_valid = 0 <= section_id_a <= 13

    # Check Slot B at 0xE000
    slot_b_valid = False
    if len(data) >= 0xF000:
        section_id_b = data[0xEFF4] | (data[0xEFF5] << 8)
        slot_b_valid = 0 <= section_id_b <= 13

    # Save is only blank if NEITHER slot is valid
    if not slot_a_valid and not slot_b_valid:
        return True

    return False


def build_section_map(data, base_offset):
    """
    Build a map of section IDs to their offsets.

    Each save slot has 14 sections of 0x1000 bytes each.
    The section ID is stored at offset 0xFF4 within each section.

    Args:
        data: Save file data
        base_offset: Base offset of save slot

    Returns:
        dict: {section_id: absolute_offset}
    """
    # Check for blank save first
    if is_blank_save(data):
        print("[SectionMap] ERROR: Save file is blank/uninitialized (all 0xFF or 0x00)")
        return {}

    section_offsets = {}

    for section_index in range(14):
        section_offset = base_offset + (section_index * 0x1000)

        # Section ID is at offset 0xFF4 within the section
        try:
            section_id = struct.unpack(
                "<H", data[section_offset + 0xFF4 : section_offset + 0xFF6]
            )[0]

            # Validate section ID is in valid range (0-13)
            if 0 <= section_id <= 13:
                section_offsets[section_id] = section_offset
            else:
                print(
                    f"[SectionMap] Warning: Invalid section ID {section_id} at index {section_index}"
                )
        except Exception as e:
            print(f"[SectionMap] Error reading section {section_index}: {e}")

    # Debug: Check if we got all sections
    if len(section_offsets) < 14:
        print(f"[SectionMap] Warning: Only found {len(section_offsets)}/14 sections")
        missing = [i for i in range(14) if i not in section_offsets]
        print(f"[SectionMap] Missing sections: {missing}")

    return section_offsets


def validate_section_checksum(data, section_offset, section_id):
    """
    Validate a section's checksum.

    Args:
        data: Save file data
        section_offset: Offset to section
        section_id: Section ID (for size lookup)

    Returns:
        bool: True if checksum is valid
    """
    size = SECTION_SIZES.get(section_id, 3968)

    # Calculate checksum over section data
    checksum = 0
    for i in range(0, size, 4):
        word = struct.unpack("<I", data[section_offset + i : section_offset + i + 4])[0]
        checksum = (checksum + word) & 0xFFFFFFFF

    # Fold to 16 bits
    calculated = ((checksum >> 16) + (checksum & 0xFFFF)) & 0xFFFF

    # Stored checksum is at offset 0xFF6
    stored = struct.unpack("<H", data[section_offset + 0xFF6 : section_offset + 0xFF8])[
        0
    ]

    return calculated == stored


# Game type lookup used when a hint is provided (e.g. from ROM header detection)
_HINT_TO_GAME_TYPE = {
    "FireRed":   ("FRLG", "FireRed"),
    "LeafGreen": ("FRLG", "LeafGreen"),
    "Ruby":      ("RS",   "Ruby"),
    "Sapphire":  ("RS",   "Sapphire"),
    "Emerald":   ("E",    "Emerald"),
}


def detect_game_type(data, section_offsets, game_hint=None):
    """
    Detect whether the save is from FRLG, Ruby/Sapphire, or Emerald.

    When a ROM is present, game_hint should always be supplied (derived from the
    ROM header check in config.read_rom_header_code). This bypasses heuristics
    entirely and gives a guaranteed correct result, including for ROM hacks.

    When no ROM is available (save-only mode), game_hint is None and detection
    falls back to save-data heuristics:
      1. Game code field at Section 0 + 0x0AC:
           == 1  -> FRLG
           == 0  -> Ruby/Sapphire (no Battle Tower data)
      2. Emerald-exclusive data region (Section 0 + 0x890 to 0xF2C):
           any non-zero byte -> Emerald
           all zero          -> Ruby/Sapphire

    Args:
        data: Save file data
        section_offsets: Dict mapping section ID to offset
        game_hint: Game name from ROM header detection, e.g. "Emerald" (optional)

    Returns:
        tuple: (game_type, game_name)
            game_type: 'FRLG', 'RS', 'E', or 'INVALID'
            game_name: Human-readable game name
    """
    # Check for blank/corrupted save
    if not section_offsets or len(section_offsets) == 0:
        print("[GameDetect] ERROR: No valid sections found - save file is blank or corrupted")
        return "INVALID", "Invalid/Blank Save"

    # --- Fast path: trust the ROM header if caller provided it ---
    if game_hint and game_hint in _HINT_TO_GAME_TYPE:
        game_type, game_name = _HINT_TO_GAME_TYPE[game_hint]
        print(f"[GameDetect] Using ROM header hint: {game_hint} -> {game_type}")
        return game_type, game_name

    # --- Save-only fallback: heuristic detection ---
    if 0 not in section_offsets:
        print("[GameDetect] Warning: Section 0 not found!")

    section0_offset = section_offsets.get(0, 0)

    # Check the Game Code field at Section 0 + 0x0AC (Bulbapedia nomenclature).
    # FRLG always writes 1 here. RSE games write their security key (Emerald)
    # or leave it as Battle Tower data / 0 (Ruby/Sapphire).
    gamecode_offset = section0_offset + 0x0AC
    gamecode_value = 0
    if gamecode_offset + 4 <= len(data):
        gamecode_value = struct.unpack("<I", data[gamecode_offset : gamecode_offset + 4])[0]

    if gamecode_value == 1:
        print("[GameDetect] FireRed/LeafGreen detected: Game Code value was 1")
        return "FRLG", "FireRed/LeafGreen"

    if gamecode_value == 0:
        print("[GameDetect] Ruby/Sapphire detected: Game Code value was 0")
        return "RS", "Ruby/Sapphire"

    # Non-zero, non-1 value: either Emerald security key or RS Battle Tower data.
    # Bytes past 0x890 in Section 0 (up to the section footer at 0xF2C) are
    # Emerald-exclusive trainer data. If any byte is non-zero it's Emerald.
    emerald_only_data = data[section0_offset + 0x890 : section0_offset + 0xF2C]
    for byte in emerald_only_data:
        if byte != 0:
            print("[GameDetect] Emerald detected: trainer data present past 0x890")
            return "E", "Emerald"

    print("[GameDetect] Ruby/Sapphire detected: no trainer data past 0x890")
    return "RS", "Ruby/Sapphire"


def _validate_pokemon_at_offset(data, offset):
    """
    Validate that there's a real Pokemon at the given offset.

    Args:
        data: Save file data
        offset: Offset to Pokemon data

    Returns:
        bool: True if valid Pokemon data
    """
    try:
        personality = struct.unpack("<I", data[offset : offset + 4])[0]
        ot_id = struct.unpack("<I", data[offset + 4 : offset + 8])[0]

        if personality == 0 or personality == 0xFFFFFFFF:
            return False

        # Decrypt the data
        encrypted_data = data[offset + 0x20 : offset + 0x50]
        key = personality ^ ot_id

        decrypted = bytearray()
        for i in range(0, 48, 4):
            word = struct.unpack("<I", encrypted_data[i : i + 4])[0]
            decrypted.extend(struct.pack("<I", word ^ key))

        PERMUTATIONS = [
            [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2],
            [0, 2, 3, 1], [0, 3, 2, 1], [1, 0, 2, 3], [1, 0, 3, 2],
            [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
            [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2],
            [2, 3, 0, 1], [3, 2, 0, 1], [1, 2, 3, 0], [1, 3, 2, 0],
            [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0],
        ]

        perm_idx = personality % 24
        block_order = PERMUTATIONS[perm_idx]

        growth_pos = block_order[0]
        growth_start = growth_pos * 12

        species = struct.unpack("<H", decrypted[growth_start : growth_start + 2])[0]
        experience = struct.unpack("<I", decrypted[growth_start + 4 : growth_start + 8])[0]

        species_valid = (1 <= species <= 251) or (277 <= species <= 411)
        exp_valid = experience < 2000000

        return species_valid and exp_valid

    except Exception:
        return False


def get_save_info(data):
    """
    Get basic information about the save file.

    Args:
        data: Save file data

    Returns:
        dict: Save file information
    """
    if len(data) < 0x20000:
        return {"valid": False, "error": "Save file too small"}

    if is_blank_save(data):
        return {"valid": False, "error": "Save file is blank/uninitialized"}

    base_offset = find_active_save_slot(data)
    section_offsets = build_section_map(data, base_offset)
    game_type, game_name = detect_game_type(data, section_offsets)

    if game_type == "INVALID":
        return {"valid": False, "error": "Could not detect game type - save may be corrupted"}

    save_index = struct.unpack("<I", data[base_offset + 0x0FFC : base_offset + 0x1000])[0]

    return {
        "valid": True,
        "base_offset": base_offset,
        "save_index": save_index,
        "game_type": game_type,
        "game_name": game_name,
        "section_offsets": section_offsets,
        "slot": "A" if base_offset == 0 else "B",
    }


def validate_save(data):
    """
    Validate the save file structure.

    Args:
        data: Save file data

    Returns:
        dict: Validation results
    """
    results = {"valid": True, "errors": [], "warnings": []}

    if len(data) < 0x20000:
        results["valid"] = False
        results["errors"].append(
            f"Save file too small: {len(data)} bytes (expected 131072)"
        )
        return results

    base_offset = find_active_save_slot(data)
    section_offsets = build_section_map(data, base_offset)

    for section_id in range(14):
        if section_id not in section_offsets:
            results["warnings"].append(f"Missing section {section_id}")

    for section_id, offset in section_offsets.items():
        if not validate_section_checksum(data, offset, section_id):
            results["warnings"].append(f"Section {section_id} checksum mismatch")

    return results