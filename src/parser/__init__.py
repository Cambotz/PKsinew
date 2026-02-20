"""
Gen 3 Pokemon Save Parser Package

A modular parser for Generation 3 Pokemon save files.
Supports: FireRed, LeafGreen, Ruby, Sapphire, Emerald

Usage:
    from parser import Gen3SaveParser
    
    parser = Gen3SaveParser("path/to/save.sav")
    if parser.loaded:
        print(f"Trainer: {parser.trainer_name}")
        print(f"Party: {len(parser.party_pokemon)} Pokemon")
"""

# Main parser class
from .gen3_parser import Gen3SaveParser

# Constants (commonly used)
from .constants import (
    PERMUTATIONS,
    INTERNAL_TO_NATIONAL,
    NATIONAL_TO_INTERNAL,
    convert_species_to_national,
    convert_species_to_internal,
    is_valid_species,
    calculate_level_from_exp,
    get_growth_rate,
    EXP_TABLES,
    OFFSETS_FRLG,
    OFFSETS_RS,
    OFFSETS_E,
    OFFSETS_RSE,  # Legacy alias for OFFSETS_RS
)

# Crypto utilities
from .crypto import (
    decrypt_pokemon_data,
    encrypt_pokemon_data,
    decode_gen3_text,
    encode_gen3_text,
    get_block_order,
    get_block_position,
)

# Pokemon parsing
from .pokemon import (
    parse_party_pokemon,
    parse_pc_pokemon,
    parse_party,
    parse_pc_boxes,
    get_box_structure,
)

# Trainer utilities
from .trainer import (
    parse_trainer_info,
    format_trainer_id,
    format_play_time,
    is_shiny,
    get_pokemon_nature,
    get_nature_name,
    NATURE_NAMES,
)

# Item utilities
from .items import (
    parse_bag,
    parse_money,
    get_item_name,
    get_bag_summary,
    ITEM_NAMES,
)

# Save structure
from .save_structure import (
    find_active_save_slot,
    build_section_map,
    detect_game_type,
    get_save_info,
    validate_save,
)

# Pokedex
from .pokedex import (
    parse_pokedex,
    get_pokemon_from_bitfield,
    count_bits_set,
)

# Version
__version__ = "2.1.0"
__author__ = "Cameron"

# For backwards compatibility, also export as Gen3SaveParser
__all__ = [
    'Gen3SaveParser',
    'PERMUTATIONS',
    'INTERNAL_TO_NATIONAL',
    'convert_species_to_national',
    'is_valid_species',
    'calculate_level_from_exp',
    'decode_gen3_text',
    'encode_gen3_text',
    'parse_party_pokemon',
    'parse_pc_pokemon',
    'get_item_name',
    'is_shiny',
    'get_nature_name',
    'parse_pokedex',
]
