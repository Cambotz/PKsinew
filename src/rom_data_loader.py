#!/usr/bin/env python3
"""
ROM Data Loader for Sinew
Loads extracted ROM data (species, moves, etc.) with caching.

Usage:
    from rom_data_loader import get_move_pp, get_species_abilities, get_species_gender_ratio
    
    pp = get_move_pp("emerald", 1)  # Pound = 35
    abilities = get_species_abilities("emerald", 151)  # Mew
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple

# Import from config
try:
    from config import ROM_DATA_EMERALD, ROM_DATA_RUBY, ROM_DATA_SAPPHIRE, ROM_DATA_FIRERED, ROM_DATA_LEAFGREEN
except ImportError:
    # Fallback for testing
    ROM_DATA_EMERALD = "dist/data/rom_data/gen3/emerald"
    ROM_DATA_RUBY = "dist/data/rom_data/gen3/ruby"
    ROM_DATA_SAPPHIRE = "dist/data/rom_data/gen3/sapphire"
    ROM_DATA_FIRERED = "dist/data/rom_data/gen3/firered"
    ROM_DATA_LEAFGREEN = "dist/data/rom_data/gen3/leafgreen"

# Game name to path mapping
GAME_DATA_PATHS = {
    "emerald": ROM_DATA_EMERALD,
    "ruby": ROM_DATA_RUBY,
    "sapphire": ROM_DATA_SAPPHIRE,
    "firered": ROM_DATA_FIRERED,
    "leafgreen": ROM_DATA_LEAFGREEN,
}

# Cache for loaded data (per game)
_CACHE = {
    "moves": {},      # {"emerald": {...}, "ruby": {...}}
    "species": {},    # {"emerald": {...}, "ruby": {...}}
}


def _get_game_data_path(game_name: str) -> Optional[Path]:
    """Get data path for a game."""
    game_lower = game_name.lower()
    if game_lower not in GAME_DATA_PATHS:
        return None
    return Path(GAME_DATA_PATHS[game_lower])


def _load_json_file(filepath: Path) -> Optional[dict]:
    """Load JSON file with error handling."""
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _get_moves_data(game_name: str) -> Optional[dict]:
    """Load moves data for a game (cached)."""
    game_lower = game_name.lower()
    
    # Check cache
    if game_lower in _CACHE["moves"]:
        return _CACHE["moves"][game_lower]
    
    # Load from file
    data_path = _get_game_data_path(game_lower)
    if not data_path:
        return None
    
    moves_file = data_path / "moves.json"
    moves_data = _load_json_file(moves_file)
    
    if moves_data:
        _CACHE["moves"][game_lower] = moves_data
    
    return moves_data


def _get_species_data(game_name: str) -> Optional[dict]:
    """Load species data for a game (cached)."""
    game_lower = game_name.lower()
    
    # Check cache
    if game_lower in _CACHE["species"]:
        return _CACHE["species"][game_lower]
    
    # Load from file
    data_path = _get_game_data_path(game_lower)
    if not data_path:
        return None
    
    species_file = data_path / "species.json"
    species_data = _load_json_file(species_file)
    
    if species_data:
        _CACHE["species"][game_lower] = species_data
    
    return species_data


# ===== PUBLIC API =====

def get_move_pp(game_name: str, move_id: int) -> int:
    """
    Get base PP for a move.
    
    Args:
        game_name: "emerald", "ruby", "sapphire", "firered", "leafgreen"
        move_id: Move ID (1-354)
    
    Returns:
        Base PP value, or 10 as fallback
    """
    moves_data = _get_moves_data(game_name)
    if not moves_data:
        return 10  # Fallback
    
    move_str = str(move_id)
    if move_str not in moves_data.get("moves", {}):
        return 10
    
    return moves_data["moves"][move_str].get("base_pp", 10)


def get_move_data(game_name: str, move_id: int) -> Optional[dict]:
    """
    Get full move data.
    
    Returns:
        {
            "id": 1,
            "name": "Pound",
            "base_pp": 35,
            "base_power": 40,
            "accuracy": 100,
            "type": 0,
            ...
        }
    """
    moves_data = _get_moves_data(game_name)
    if not moves_data:
        return None
    
    return moves_data.get("moves", {}).get(str(move_id))


def get_species_abilities(game_name: str, species_id: int) -> List[Tuple[int, int]]:
    """
    Get abilities for a species.
    
    Returns:
        List of (slot, ability_id) tuples
        Example: [(0, 28), (1, 0)] means slot 0 = ability 28, slot 1 = none
    """
    species_data = _get_species_data(game_name)
    if not species_data:
        return [(0, 0)]  # Fallback
    
    species = species_data.get("species", {}).get(str(species_id))
    if not species:
        return [(0, 0)]
    
    abilities = species.get("abilities", [])
    result = []
    
    for ability in abilities:
        if ability is None:
            continue
        slot = ability.get("slot", 0)
        ability_id = ability.get("id", 0)
        result.append((slot, ability_id))
    
    return result if result else [(0, 0)]


def get_species_gender_ratio(game_name: str, species_id: int) -> int:
    """
    Get gender ratio for a species.
    
    Returns:
        0-254 = Female ratio (254 = 100% female)
        255 = Genderless
    """
    species_data = _get_species_data(game_name)
    if not species_data:
        return 127  # Fallback: 50/50
    
    species = species_data.get("species", {}).get(str(species_id))
    if not species:
        return 127
    
    return species.get("gender_ratio", 127)


def get_species_friendship(game_name: str, species_id: int) -> int:
    """Get base friendship for a species."""
    species_data = _get_species_data(game_name)
    if not species_data:
        return 70  # Fallback
    
    species = species_data.get("species", {}).get(str(species_id))
    if not species:
        return 70
    
    return species.get("base_friendship", 70)


def get_species_data(game_name: str, species_id: int) -> Optional[dict]:
    """
    Get full species data.
    
    Returns:
        {
            "internal_id": 151,
            "name": "Mew",
            "base_stats": {...},
            "abilities": [...],
            "gender_ratio": 255,
            ...
        }
    """
    species_data = _get_species_data(game_name)
    if not species_data:
        return None
    
    return species_data.get("species", {}).get(str(species_id))


# ===== VALIDATION =====

def is_rom_data_available(game_name: str) -> bool:
    """Check if ROM data is available for a game."""
    data_path = _get_game_data_path(game_name)
    if not data_path:
        return False
    
    return (data_path / "moves.json").exists() and (data_path / "species.json").exists()


if __name__ == "__main__":
    # Test the loader
    print("Testing ROM Data Loader...")
    print()
    
    # Test move PP
    print("Move PP:")
    print(f"  Pound (1): {get_move_pp('emerald', 1)}")
    print(f"  Transform (144): {get_move_pp('emerald', 144)}")
    print(f"  Mega Punch (5): {get_move_pp('emerald', 5)}")
    print(f"  Metronome (118): {get_move_pp('emerald', 118)}")
    print()
    
    # Test species abilities
    print("Species abilities:")
    abilities = get_species_abilities('emerald', 151)  # Mew
    print(f"  Mew: {abilities}")
    print()
    
    # Test gender ratio
    print("Gender ratios:")
    print(f"  Mew: {get_species_gender_ratio('emerald', 151)} (255 = genderless)")
    print()
    
    # Test availability
    print(f"ROM data available for Emerald: {is_rom_data_available('emerald')}")
