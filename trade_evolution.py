"""
Trade Evolution System for Sinew
Handles Pokemon that evolve through trading in the main games.
In Sinew, these evolutions trigger when depositing Pokemon into Sinew Storage
or when transferring between different game saves.
"""

import struct

# Trade evolution data
# Format: species_id: {
#     "evolves_to": target_species_id,
#     "item_required": item_id or None,
#     "item_name": display name or None
# }

TRADE_EVOLUTIONS = {
    # Trade only (no item required)
    64: {  # Kadabra
        "evolves_to": 65,  # Alakazam
        "from_name": "Kadabra",
        "to_name": "Alakazam",
        "item_required": None,
        "item_name": None
    },
    67: {  # Machoke
        "evolves_to": 68,  # Machamp
        "from_name": "Machoke",
        "to_name": "Machamp",
        "item_required": None,
        "item_name": None
    },
    75: {  # Graveler
        "evolves_to": 76,  # Golem
        "from_name": "Graveler",
        "to_name": "Golem",
        "item_required": None,
        "item_name": None
    },
    93: {  # Haunter
        "evolves_to": 94,  # Gengar
        "from_name": "Haunter",
        "to_name": "Gengar",
        "item_required": None,
        "item_name": None
    },
    
    # Trade with held item
    61: {  # Poliwhirl + King's Rock
        "evolves_to": 186,  # Politoed
        "from_name": "Poliwhirl",
        "to_name": "Politoed",
        "item_required": 187,
        "item_name": "King's Rock"
    },
    79: {  # Slowpoke + King's Rock
        "evolves_to": 199,  # Slowking
        "from_name": "Slowpoke",
        "to_name": "Slowking",
        "item_required": 187,
        "item_name": "King's Rock"
    },
    95: {  # Onix + Metal Coat
        "evolves_to": 208,  # Steelix
        "from_name": "Onix",
        "to_name": "Steelix",
        "item_required": 199,
        "item_name": "Metal Coat"
    },
    123: {  # Scyther + Metal Coat
        "evolves_to": 212,  # Scizor
        "from_name": "Scyther",
        "to_name": "Scizor",
        "item_required": 199,
        "item_name": "Metal Coat"
    },
    117: {  # Seadra + Dragon Scale
        "evolves_to": 230,  # Kingdra
        "from_name": "Seadra",
        "to_name": "Kingdra",
        "item_required": 201,
        "item_name": "Dragon Scale"
    },
    137: {  # Porygon + Up-Grade
        "evolves_to": 233,  # Porygon2
        "from_name": "Porygon",
        "to_name": "Porygon2",
        "item_required": 218,
        "item_name": "Up-Grade"
    },
    366: {  # Clamperl - has two possible evolutions
        "evolves_to": None,  # Determined by item
        "from_name": "Clamperl",
        "to_name": None,
        "item_required": "special",  # Special handling
        "item_name": None,
        "item_evolutions": {
            192: {"evolves_to": 367, "to_name": "Huntail", "item_name": "Deep Sea Tooth"},
            193: {"evolves_to": 368, "to_name": "Gorebyss", "item_name": "Deep Sea Scale"}
        }
    }
}


def can_evolve_by_trade(species_id, held_item_id=0):
    """
    Check if a Pokemon can evolve through trade.
    
    Args:
        species_id: Pokemon's species ID
        held_item_id: ID of held item (0 if none)
    
    Returns:
        dict with evolution info if can evolve, None otherwise
        {
            "evolves_to": target species ID,
            "from_name": current species name,
            "to_name": evolved species name,
            "consumes_item": True/False,
            "item_name": name of consumed item or None
        }
    """
    if species_id not in TRADE_EVOLUTIONS:
        return None
    
    evo_data = TRADE_EVOLUTIONS[species_id]
    
    # Special case: Clamperl with multiple evolution paths
    if evo_data.get("item_required") == "special":
        if held_item_id in evo_data.get("item_evolutions", {}):
            item_evo = evo_data["item_evolutions"][held_item_id]
            return {
                "evolves_to": item_evo["evolves_to"],
                "from_name": evo_data["from_name"],
                "to_name": item_evo["to_name"],
                "consumes_item": True,
                "item_name": item_evo["item_name"]
            }
        return None
    
    # Standard trade evolution
    required_item = evo_data.get("item_required")
    
    if required_item is None:
        # No item required - can evolve
        return {
            "evolves_to": evo_data["evolves_to"],
            "from_name": evo_data["from_name"],
            "to_name": evo_data["to_name"],
            "consumes_item": False,
            "item_name": None
        }
    elif required_item == held_item_id:
        # Has correct item - can evolve
        return {
            "evolves_to": evo_data["evolves_to"],
            "from_name": evo_data["from_name"],
            "to_name": evo_data["to_name"],
            "consumes_item": True,
            "item_name": evo_data["item_name"]
        }
    
    return None


def get_evolution_info(species_id):
    """
    Get evolution info for a species (for display purposes).
    
    Returns:
        dict with evolution requirements or None
    """
    if species_id not in TRADE_EVOLUTIONS:
        return None
    
    return TRADE_EVOLUTIONS[species_id].copy()


def apply_evolution(pokemon_data, evolution_info):
    """
    Apply evolution to Pokemon data dict.
    
    Args:
        pokemon_data: Pokemon dict to modify (modified in place)
        evolution_info: Evolution info from can_evolve_by_trade()
    
    Returns:
        Modified pokemon_data
    """
    if not evolution_info:
        return pokemon_data
    
    # Update species
    pokemon_data['species'] = evolution_info['evolves_to']
    pokemon_data['species_name'] = evolution_info['to_name']
    
    # Remove held item if it was consumed
    if evolution_info.get('consumes_item'):
        pokemon_data['held_item'] = 0
    
    # If we have raw_bytes, try to update them too
    if 'raw_bytes' in pokemon_data and pokemon_data['raw_bytes']:
        try:
            pokemon_data['raw_bytes'] = evolve_raw_pokemon_bytes(
                pokemon_data['raw_bytes'],
                evolution_info['evolves_to'],
                evolution_info.get('consumes_item', False)
            )
        except Exception as e:
            print(f"[TradeEvolution] Warning: Could not update raw_bytes: {e}")
    
    return pokemon_data


# =============================================================================
# Gen 3 Pokemon Data Structure Manipulation
# =============================================================================

def _get_substructure_order(personality):
    """
    Get the order of substructures based on personality value.
    Gen 3 Pokemon data has 4 substructures that are ordered based on personality % 24.
    
    Returns list of substructure indices: [Growth, Attacks, EVs/Condition, Misc]
    The value returned indicates which position each type is in.
    """
    orders = [
        [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2], [0, 2, 3, 1], [0, 3, 2, 1],
        [1, 0, 2, 3], [1, 0, 3, 2], [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
        [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2], [2, 3, 0, 1], [3, 2, 0, 1],
        [1, 2, 3, 0], [1, 3, 2, 0], [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0]
    ]
    return orders[personality % 24]


def _decrypt_pokemon_data(encrypted_data, personality, ot_id):
    """
    Decrypt the 48-byte Pokemon substructure data.
    XORs each 4-byte chunk with (personality XOR ot_id).
    """
    key = personality ^ ot_id
    decrypted = bytearray(len(encrypted_data))
    
    for i in range(0, len(encrypted_data), 4):
        chunk = struct.unpack('<I', encrypted_data[i:i+4])[0]
        decrypted_chunk = chunk ^ key
        struct.pack_into('<I', decrypted, i, decrypted_chunk)
    
    return bytes(decrypted)


def _encrypt_pokemon_data(decrypted_data, personality, ot_id):
    """
    Encrypt the 48-byte Pokemon substructure data.
    Same operation as decrypt (XOR is symmetric).
    """
    return _decrypt_pokemon_data(decrypted_data, personality, ot_id)


def _calculate_pokemon_checksum(decrypted_data):
    """
    Calculate the 16-bit checksum for Pokemon data.
    Sum of all 16-bit words in the decrypted data.
    """
    checksum = 0
    for i in range(0, len(decrypted_data), 2):
        word = struct.unpack('<H', decrypted_data[i:i+2])[0]
        checksum = (checksum + word) & 0xFFFF
    return checksum


def evolve_raw_pokemon_bytes(raw_bytes, new_species_id, consume_item=False):
    """
    Modify raw Pokemon bytes to change species (evolution).
    
    Gen 3 Pokemon structure (80 bytes for PC, 100 for party):
    - 0-3: Personality Value (4 bytes)
    - 4-7: OT ID (4 bytes)  
    - 8-17: Nickname (10 bytes)
    - 18-19: Language (2 bytes)
    - 20-26: OT Name (7 bytes)
    - 27: Markings (1 byte)
    - 28-29: Checksum (2 bytes)
    - 30-31: Padding (2 bytes)
    - 32-79: Encrypted data (48 bytes) - 4 substructures of 12 bytes each
    
    Substructure G (Growth): Species (2), Item (2), Experience (4), PP Bonuses (1), Friendship (1), Unknown (2)
    
    Args:
        raw_bytes: Original 80-byte Pokemon data
        new_species_id: Target species ID
        consume_item: Whether to clear the held item
        
    Returns:
        Modified raw_bytes
    """
    if len(raw_bytes) < 80:
        raise ValueError(f"Raw bytes too short: {len(raw_bytes)}")
    
    data = bytearray(raw_bytes)
    
    # Read personality and OT ID
    personality = struct.unpack('<I', data[0:4])[0]
    ot_id = struct.unpack('<I', data[4:8])[0]
    
    # Get substructure order
    order = _get_substructure_order(personality)
    
    # Decrypt the 48-byte data section
    encrypted_data = bytes(data[32:80])
    decrypted = bytearray(_decrypt_pokemon_data(encrypted_data, personality, ot_id))
    
    # Find Growth substructure (type 0)
    growth_position = order.index(0)
    growth_offset = growth_position * 12
    
    # Modify species (first 2 bytes of Growth)
    struct.pack_into('<H', decrypted, growth_offset, new_species_id)
    
    # Optionally clear held item (bytes 2-3 of Growth)
    if consume_item:
        struct.pack_into('<H', decrypted, growth_offset + 2, 0)
    
    # Recalculate checksum
    new_checksum = _calculate_pokemon_checksum(bytes(decrypted))
    struct.pack_into('<H', data, 28, new_checksum)
    
    # Re-encrypt and write back
    encrypted = _encrypt_pokemon_data(bytes(decrypted), personality, ot_id)
    data[32:80] = encrypted
    
    return bytes(data)