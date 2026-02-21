"""
Gen 3 Pokemon Save Parser - Pokemon Module
Handles parsing of party and PC Pokemon
"""

import struct
from .constants import (
    PERMUTATIONS, BLOCK_GROWTH, BLOCK_ATTACKS, BLOCK_EVS, BLOCK_MISC,
    INTERNAL_TO_NATIONAL, convert_species_to_national, is_valid_species,
    calculate_level_from_exp
)
from .crypto import decrypt_pokemon_data, decode_gen3_text


def parse_party_pokemon(data, offset):
    """
    Parse a party Pokemon (100 bytes).
    
    Args:
        data: Save file data
        offset: Offset to Pokemon data
        
    Returns:
        dict: Pokemon data or None if empty/invalid
    """
    try:
        personality = struct.unpack('<I', data[offset:offset + 4])[0]
        if personality == 0:
            return None
        
        ot_id = struct.unpack('<I', data[offset + 4:offset + 8])[0]
        nickname_bytes = data[offset + 0x08:offset + 0x12]
        nickname = decode_gen3_text(nickname_bytes)
        
        # OT name is at offset 0x14, 7 bytes
        ot_name_bytes = data[offset + 0x14:offset + 0x1B]
        ot_name = decode_gen3_text(ot_name_bytes)
        
        # Decrypt the 48-byte substructure
        encrypted_data = data[offset + 0x20:offset + 0x50]
        decrypted_data = decrypt_pokemon_data(encrypted_data, personality, ot_id)
        
        # Get block positions from permutation
        # PERMUTATIONS[index][TYPE] = POSITION
        permutation_index = personality % 24
        block_order = PERMUTATIONS[permutation_index]
        
        # Read Growth block (type 0)
        growth_position = block_order[BLOCK_GROWTH]
        growth_start = growth_position * 12
        raw_species = struct.unpack('<H', decrypted_data[growth_start:growth_start + 2])[0]
        held_item = struct.unpack('<H', decrypted_data[growth_start + 2:growth_start + 4])[0]
        experience = struct.unpack('<I', decrypted_data[growth_start + 4:growth_start + 8])[0]
        
        # Read Misc block early to check egg flag before filtering
        misc_position = block_order[BLOCK_MISC]
        misc_start = misc_position * 12
        pokerus = decrypted_data[misc_start]
        met_location = decrypted_data[misc_start + 1]
        origins_info = struct.unpack('<H', decrypted_data[misc_start + 2:misc_start + 4])[0]
        iv_egg_ability = struct.unpack('<I', decrypted_data[misc_start + 4:misc_start + 8])[0]
        is_egg = bool(iv_egg_ability & 0x40000000)
        
        # Filter out invalid/phantom Pokemon (check raw internal species ID)
        # But allow eggs through even if species looks odd
        if not is_egg and not is_valid_species(raw_species):
            return None
        
        # Convert internal species to National Dex
        species = convert_species_to_national(raw_species)
        
        # Debug: show species conversion
        if raw_species != species:
            print(f"[Party] Species conversion: {raw_species} -> {species} ({nickname})")
        
        # Read Attacks block (type 1)
        attacks_position = block_order[BLOCK_ATTACKS]
        attacks_start = attacks_position * 12
        moves = [
            struct.unpack('<H', decrypted_data[attacks_start:attacks_start + 2])[0],
            struct.unpack('<H', decrypted_data[attacks_start + 2:attacks_start + 4])[0],
            struct.unpack('<H', decrypted_data[attacks_start + 4:attacks_start + 6])[0],
            struct.unpack('<H', decrypted_data[attacks_start + 6:attacks_start + 8])[0],
        ]
        pp = [
            decrypted_data[attacks_start + 8],
            decrypted_data[attacks_start + 9],
            decrypted_data[attacks_start + 10],
            decrypted_data[attacks_start + 11],
        ]
        
        # Read EVs block (type 2)
        evs_position = block_order[BLOCK_EVS]
        evs_start = evs_position * 12
        evs = {
            'hp': decrypted_data[evs_start],
            'attack': decrypted_data[evs_start + 1],
            'defense': decrypted_data[evs_start + 2],
            'speed': decrypted_data[evs_start + 3],
            'sp_attack': decrypted_data[evs_start + 4],
            'sp_defense': decrypted_data[evs_start + 5],
        }
        
        # Parse IVs (misc block already read earlier for egg check)
        ivs = {
            'hp': iv_egg_ability & 0x1F,
            'attack': (iv_egg_ability >> 5) & 0x1F,
            'defense': (iv_egg_ability >> 10) & 0x1F,
            'speed': (iv_egg_ability >> 15) & 0x1F,
            'sp_attack': (iv_egg_ability >> 20) & 0x1F,
            'sp_defense': (iv_egg_ability >> 25) & 0x1F,
        }
        
        # Ability flag is bit 31 (0 = first ability, 1 = second ability)
        ability_bit = bool(iv_egg_ability & 0x80000000)
        
        # Party Pokemon have unencrypted battle stats at offset 0x50
        stored_level = data[offset + 0x54] if offset + 0x54 < len(data) else 0
        current_hp = struct.unpack('<H', data[offset + 0x56:offset + 0x58])[0]
        max_hp = struct.unpack('<H', data[offset + 0x58:offset + 0x5A])[0]
        attack = struct.unpack('<H', data[offset + 0x5A:offset + 0x5C])[0]
        defense = struct.unpack('<H', data[offset + 0x5C:offset + 0x5E])[0]
        speed = struct.unpack('<H', data[offset + 0x5E:offset + 0x60])[0]
        sp_attack = struct.unpack('<H', data[offset + 0x60:offset + 0x62])[0]
        sp_defense = struct.unpack('<H', data[offset + 0x62:offset + 0x64])[0]
        
        # Use stored level if valid
        if stored_level > 0 and stored_level <= 100:
            level = stored_level
        else:
            level = calculate_level_from_exp(experience, species)
        
        return {
            'personality': personality,
            'ot_id': ot_id,
            'ot_name': ot_name,
            'species': species,
            'level': level,
            'nickname': nickname,
            'held_item': held_item,
            'experience': experience,
            'moves': moves,
            'pp': pp,
            'evs': evs,
            'ivs': ivs,
            'pokerus': pokerus,
            'met_location': met_location,
            'current_hp': current_hp,
            'max_hp': max_hp,
            'attack': attack,
            'defense': defense,
            'speed': speed,
            'sp_attack': sp_attack,
            'sp_defense': sp_defense,
            'egg': is_egg,
            'ability_bit': ability_bit,
            'raw_bytes': bytes(data[offset:offset + 0x50]),  # First 80 bytes for PC storage
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def parse_pc_pokemon(pokemon_bytes):
    """
    Parse a PC Pokemon (80 bytes).
    
    Args:
        pokemon_bytes: 80 bytes of Pokemon data
        
    Returns:
        dict: Pokemon data or None if empty/invalid
    """
    try:
        personality = struct.unpack('<I', pokemon_bytes[0:4])[0]
        if personality == 0 or personality == 0xFFFFFFFF:
            return None
        
        ot_id = struct.unpack('<I', pokemon_bytes[4:8])[0]
        nickname_bytes = pokemon_bytes[0x08:0x12]
        nickname = decode_gen3_text(nickname_bytes)
        
        # OT name is at offset 0x14, 7 bytes
        ot_name_bytes = pokemon_bytes[0x14:0x1B]
        ot_name = decode_gen3_text(ot_name_bytes)
        
        # Decrypt the 48-byte substructure
        encrypted_data = pokemon_bytes[0x20:0x50]
        decrypted_data = decrypt_pokemon_data(encrypted_data, personality, ot_id)
        
        # Get block positions from permutation
        permutation_index = personality % 24
        block_order = PERMUTATIONS[permutation_index]
        
        # Read Growth block (type 0)
        growth_position = block_order[BLOCK_GROWTH]
        growth_start = growth_position * 12
        raw_species = struct.unpack('<H', decrypted_data[growth_start:growth_start + 2])[0]
        held_item = struct.unpack('<H', decrypted_data[growth_start + 2:growth_start + 4])[0]
        experience = struct.unpack('<I', decrypted_data[growth_start + 4:growth_start + 8])[0]
        
        # Read Misc block early to check egg flag before filtering
        misc_position = block_order[BLOCK_MISC]
        misc_start = misc_position * 12
        pokerus = decrypted_data[misc_start]
        met_location = decrypted_data[misc_start + 1]
        origins_info = struct.unpack('<H', decrypted_data[misc_start + 2:misc_start + 4])[0]
        iv_egg_ability = struct.unpack('<I', decrypted_data[misc_start + 4:misc_start + 8])[0]
        is_egg = bool(iv_egg_ability & 0x40000000)
        
        # Filter out invalid/phantom Pokemon (check raw internal species ID)
        # But allow eggs through even if species looks odd
        if not is_egg and not is_valid_species(raw_species):
            return None
        
        # Convert internal species to National Dex
        species = convert_species_to_national(raw_species)
        
        # Debug: show species conversion for PC Pokemon
        if raw_species != species:
            print(f"[PC] Species conversion: {raw_species} -> {species} ({nickname})")
        
        # Read Attacks block (type 1) for moves
        attacks_position = block_order[BLOCK_ATTACKS]
        attacks_start = attacks_position * 12
        moves = [
            struct.unpack('<H', decrypted_data[attacks_start:attacks_start + 2])[0],
            struct.unpack('<H', decrypted_data[attacks_start + 2:attacks_start + 4])[0],
            struct.unpack('<H', decrypted_data[attacks_start + 4:attacks_start + 6])[0],
            struct.unpack('<H', decrypted_data[attacks_start + 6:attacks_start + 8])[0],
        ]
        pp = [
            decrypted_data[attacks_start + 8],
            decrypted_data[attacks_start + 9],
            decrypted_data[attacks_start + 10],
            decrypted_data[attacks_start + 11],
        ]
        
        # Read EVs block (type 2)
        evs_position = block_order[BLOCK_EVS]
        evs_start = evs_position * 12
        evs = {
            'hp': decrypted_data[evs_start],
            'attack': decrypted_data[evs_start + 1],
            'defense': decrypted_data[evs_start + 2],
            'speed': decrypted_data[evs_start + 3],
            'sp_attack': decrypted_data[evs_start + 4],
            'sp_defense': decrypted_data[evs_start + 5],
        }
        
        # Parse IVs (misc block already read earlier for egg check)
        ivs = {
            'hp': iv_egg_ability & 0x1F,
            'attack': (iv_egg_ability >> 5) & 0x1F,
            'defense': (iv_egg_ability >> 10) & 0x1F,
            'speed': (iv_egg_ability >> 15) & 0x1F,
            'sp_attack': (iv_egg_ability >> 20) & 0x1F,
            'sp_defense': (iv_egg_ability >> 25) & 0x1F,
        }
        
        # Ability flag is bit 31 (0 = first ability, 1 = second ability)
        ability_bit = bool(iv_egg_ability & 0x80000000)
        
        # Calculate level
        level = calculate_level_from_exp(experience, species)
        
        return {
            'personality': personality,
            'ot_id': ot_id,
            'ot_name': ot_name,
            'species': species,
            'level': level,
            'nickname': nickname,
            'held_item': held_item,
            'experience': experience,
            'moves': moves,
            'pp': pp,
            'evs': evs,
            'ivs': ivs,
            'pokerus': pokerus,
            'met_location': met_location,
            'egg': is_egg,
            'ability_bit': ability_bit,
            'raw_bytes': bytes(pokemon_bytes),  # Store original 80 bytes for transfers
            # PC Pokemon don't have battle stats
            'current_hp': None,
            'max_hp': None,
            'attack': None,
            'defense': None,
            'speed': None,
            'sp_attack': None,
            'sp_defense': None,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def parse_party(data, section1_offset, game_type='RSE'):
    """
    Parse all party Pokemon.
    
    Args:
        data: Save file data
        section1_offset: Offset to Section 1
        game_type: 'FRLG' or 'RSE'
        
    Returns:
        list: List of Pokemon dicts
    """
    from .constants import OFFSETS_FRLG, OFFSETS_RSE
    
    offsets = OFFSETS_FRLG if game_type == 'FRLG' else OFFSETS_RSE
    
    # Read team size
    team_size_offset = section1_offset + offsets['team_size']
    team_size = struct.unpack('<I', data[team_size_offset:team_size_offset + 4])[0]
    
    print(f"[pokemon.py] game_type={game_type}, team_size_offset=0x{offsets['team_size']:X}, team_size={team_size}")
    
    if team_size > 6:
        print(f"[pokemon.py] Warning: team_size > 6, setting to 0")
        team_size = 0
    
    party = []
    team_data_offset = section1_offset + offsets['team_data']
    
    print(f"[pokemon.py] team_data_offset=0x{offsets['team_data']:X} (absolute: 0x{team_data_offset:X})")
    
    for i in range(team_size):
        pokemon_offset = team_data_offset + (i * 100)
        pokemon = parse_party_pokemon(data, pokemon_offset)
        if pokemon:
            party.append(pokemon)
    
    return party


def parse_pc_boxes(data, section_offsets):
    """
    Parse all PC box Pokemon.
    
    PC storage spans sections 5-13 as a contiguous array of 420 Pokemon.
    
    Args:
        data: Save file data
        section_offsets: Dict mapping section ID to offset
        
    Returns:
        list: List of Pokemon dicts with box_number and box_slot
    """
    # Build contiguous PC buffer from sections 5-13
    pc_buffer = bytearray()
    
    for section_id in range(5, 14):
        if section_id not in section_offsets:
            print(f"Warning: Section {section_id} not found!")
            continue
        
        offset = section_offsets[section_id]
        
        # Sections 5-12 have 3968 bytes, section 13 has 2000 bytes
        size = 3968 if section_id <= 12 else 2000
        section_data = data[offset:offset + size]
        pc_buffer.extend(section_data)
    
    # Parse 420 Pokemon (14 boxes Ã— 30 slots)
    # Skip first 4 bytes (current box number)
    pc_pokemon = []
    pokemon_start = 4
    pokemon_size = 80
    
    for index in range(420):
        offset = pokemon_start + (index * pokemon_size)
        
        if offset + pokemon_size > len(pc_buffer):
            break
        
        pokemon_bytes = pc_buffer[offset:offset + pokemon_size]
        pokemon = parse_pc_pokemon(pokemon_bytes)
        
        if pokemon:
            # Calculate box and slot (1-indexed)
            pokemon['box_number'] = (index // 30) + 1
            pokemon['box_slot'] = (index % 30) + 1
            pc_pokemon.append(pokemon)
    
    return pc_pokemon


def get_box_structure(pc_pokemon, box_number):
    """
    Get complete structure of a specific box including empty slots.
    
    Args:
        pc_pokemon: List of all PC Pokemon
        box_number: Box number (1-14)
        
    Returns:
        list: 30 slot dicts
    """
    slots = []
    
    for slot_num in range(1, 31):
        # Find Pokemon in this slot
        found = None
        for poke in pc_pokemon:
            if poke.get('box_number') == box_number and poke.get('box_slot') == slot_num:
                found = poke.copy()
                break
        
        if found:
            found['slot'] = slot_num
            found['empty'] = False
            slots.append(found)
        else:
            slots.append({
                'empty': True,
                'box_number': box_number,
                'slot': slot_num,
                'egg': False
            })
    
    return slots