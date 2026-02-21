"""
Gen 3 Pokemon Save Parser - Trainer Module
Handles parsing of trainer information
"""

import struct
from .crypto import decode_gen3_text


def parse_trainer_info(data, section0_offset):
    """
    Parse trainer information from Section 0.
    
    Args:
        data: Save file data
        section0_offset: Offset to Section 0
        
    Returns:
        dict: Trainer information
    """
    try:
        # Trainer name (7 bytes at offset 0x00)
        name_bytes = data[section0_offset:section0_offset + 7]
        trainer_name = decode_gen3_text(name_bytes)
        
        # Gender (1 byte at offset 0x08)
        gender_byte = data[section0_offset + 0x08]
        gender = "Female" if gender_byte == 1 else "Male"
        
        # Trainer ID (2 bytes at offset 0x0A)
        trainer_id = struct.unpack('<H', data[section0_offset + 0x0A:section0_offset + 0x0C])[0]
        
        # Secret ID (2 bytes at offset 0x0C)
        secret_id = struct.unpack('<H', data[section0_offset + 0x0C:section0_offset + 0x0E])[0]
        
        # Play time (at offset 0x0E)
        play_hours = struct.unpack('<H', data[section0_offset + 0x0E:section0_offset + 0x10])[0]
        play_minutes = data[section0_offset + 0x10]
        play_seconds = data[section0_offset + 0x11]
        play_frames = data[section0_offset + 0x12]
        
        # Game code (4 bytes at offset 0x0AF8) - helps identify game version
        game_code = struct.unpack('<I', data[section0_offset + 0x0AF8:section0_offset + 0x0AFC])[0]
        
        # Security key (4 bytes at offset 0x0AF8) - used for item encryption in FRLG
        security_key = game_code
        
        # Rival name (7 bytes at offset 0x0A98) - only in FRLG
        rival_bytes = data[section0_offset + 0x0A98:section0_offset + 0x0A98 + 7]
        rival_name = decode_gen3_text(rival_bytes)
        if len(rival_name) < 2:
            rival_name = ""
        
        return {
            'name': trainer_name,
            'gender': gender,
            'trainer_id': trainer_id,
            'secret_id': secret_id,
            'play_hours': play_hours,
            'play_minutes': play_minutes,
            'play_seconds': play_seconds,
            'play_frames': play_frames,
            'game_code': game_code,
            'security_key': security_key,
            'rival_name': rival_name,
        }
        
    except Exception as e:
        print(f"Error parsing trainer info: {e}")
        return {
            'name': "Unknown",
            'gender': "Unknown",
            'trainer_id': 0,
            'secret_id': 0,
            'play_hours': 0,
            'play_minutes': 0,
            'play_seconds': 0,
            'play_frames': 0,
            'game_code': 0,
            'security_key': 0,
            'rival_name': "",
        }


def format_trainer_id(trainer_id, secret_id=None, show_secret=False):
    """
    Format trainer ID for display.
    
    Args:
        trainer_id: Public trainer ID
        secret_id: Secret trainer ID (optional)
        show_secret: Whether to show secret ID
        
    Returns:
        str: Formatted ID string
    """
    public = str(trainer_id).zfill(5)
    
    if show_secret and secret_id is not None:
        secret = str(secret_id).zfill(5)
        return f"{public}-{secret}"
    
    return public


def format_play_time(hours, minutes, seconds):
    """
    Format play time for display.
    
    Args:
        hours: Play hours
        minutes: Play minutes
        seconds: Play seconds
        
    Returns:
        str: Formatted time string
    """
    return f"{hours:03d}:{minutes:02d}:{seconds:02d}"


def is_shiny(personality, trainer_id, secret_id):
    """
    Check if a Pokemon is shiny based on its values.
    
    Args:
        personality: Pokemon's personality value
        trainer_id: Trainer's public ID
        secret_id: Trainer's secret ID
        
    Returns:
        bool: True if shiny
    """
    # Extract PID high and low
    pid_low = personality & 0xFFFF
    pid_high = (personality >> 16) & 0xFFFF
    
    # Calculate shiny value
    shiny_value = trainer_id ^ secret_id ^ pid_low ^ pid_high
    
    # Pokemon is shiny if value < 8
    return shiny_value < 8


def get_pokemon_nature(personality):
    """
    Get Pokemon's nature from personality value.
    
    Args:
        personality: Pokemon's personality value
        
    Returns:
        int: Nature ID (0-24)
    """
    return personality % 25


def get_pokemon_gender(personality, species_gender_ratio):
    """
    Get Pokemon's gender from personality value.
    
    Args:
        personality: Pokemon's personality value
        species_gender_ratio: Species' gender ratio (0-254, 255=genderless)
        
    Returns:
        str: 'Male', 'Female', or 'Genderless'
    """
    if species_gender_ratio == 255:
        return 'Genderless'
    if species_gender_ratio == 254:
        return 'Female'
    if species_gender_ratio == 0:
        return 'Male'
    
    # Compare low byte of personality with gender threshold
    p_gender = personality & 0xFF
    if p_gender < species_gender_ratio:
        return 'Female'
    return 'Male'


# Nature names
NATURE_NAMES = [
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky"
]

# Nature stat modifications: [+stat, -stat] (None = neutral)
# Stats: 0=HP, 1=Atk, 2=Def, 3=Speed, 4=SpAtk, 5=SpDef
NATURE_MODIFIERS = {
    0: (None, None),   # Hardy
    1: (1, 2),         # Lonely (+Atk, -Def)
    2: (1, 3),         # Brave (+Atk, -Speed)
    3: (1, 4),         # Adamant (+Atk, -SpAtk)
    4: (1, 5),         # Naughty (+Atk, -SpDef)
    5: (2, 1),         # Bold (+Def, -Atk)
    6: (None, None),   # Docile
    7: (2, 3),         # Relaxed (+Def, -Speed)
    8: (2, 4),         # Impish (+Def, -SpAtk)
    9: (2, 5),         # Lax (+Def, -SpDef)
    10: (3, 1),        # Timid (+Speed, -Atk)
    11: (3, 2),        # Hasty (+Speed, -Def)
    12: (None, None),  # Serious
    13: (3, 4),        # Jolly (+Speed, -SpAtk)
    14: (3, 5),        # Naive (+Speed, -SpDef)
    15: (4, 1),        # Modest (+SpAtk, -Atk)
    16: (4, 2),        # Mild (+SpAtk, -Def)
    17: (4, 3),        # Quiet (+SpAtk, -Speed)
    18: (None, None),  # Bashful
    19: (4, 5),        # Rash (+SpAtk, -SpDef)
    20: (5, 1),        # Calm (+SpDef, -Atk)
    21: (5, 2),        # Gentle (+SpDef, -Def)
    22: (5, 3),        # Sassy (+SpDef, -Speed)
    23: (5, 4),        # Careful (+SpDef, -SpAtk)
    24: (None, None),  # Quirky
}


def get_nature_name(nature_id):
    """Get nature name from ID."""
    if 0 <= nature_id < len(NATURE_NAMES):
        return NATURE_NAMES[nature_id]
    return "Unknown"


def get_nature_modifiers(nature_id):
    """Get nature stat modifiers."""
    return NATURE_MODIFIERS.get(nature_id, (None, None))
