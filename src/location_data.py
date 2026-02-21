# Gen 3 Met Location Data
# Complete location database based on internal index numbers
# Source: Bulbapedia - List of locations by index number in Generation III

# =============================================================================
# RSE LOCATIONS (0x00-0x57, recognized by RS and E)
# =============================================================================
RSE_LOCATIONS = {
    0: "Littleroot Town",
    1: "Oldale Town",
    2: "Dewford Town",
    3: "Lavaridge Town",
    4: "Fallarbor Town",
    5: "Verdanturf Town",
    6: "Pacifidlog Town",
    7: "Petalburg City",
    8: "Slateport City",
    9: "Mauville City",
    10: "Rustboro City",
    11: "Fortree City",
    12: "Lilycove City",
    13: "Mossdeep City",
    14: "Sootopolis City",
    15: "Ever Grande City",
    16: "Route 101",
    17: "Route 102",
    18: "Route 103",
    19: "Route 104",
    20: "Route 105",
    21: "Route 106",
    22: "Route 107",
    23: "Route 108",
    24: "Route 109",
    25: "Route 110",
    26: "Route 111",
    27: "Route 112",
    28: "Route 113",
    29: "Route 114",
    30: "Route 115",
    31: "Route 116",
    32: "Route 117",
    33: "Route 118",
    34: "Route 119",
    35: "Route 120",
    36: "Route 121",
    37: "Route 122",
    38: "Route 123",
    39: "Route 124",
    40: "Route 125",
    41: "Route 126",
    42: "Route 127",
    43: "Route 128",
    44: "Route 129",
    45: "Route 130",
    46: "Route 131",
    47: "Route 132",
    48: "Route 133",
    49: "Route 134",
    50: "Underwater (Route 124)",
    51: "Underwater (Route 126)",
    52: "Underwater (Route 127)",
    53: "Underwater (Route 128)",
    54: "Underwater (Sootopolis)",
    55: "Granite Cave",
    56: "Mt. Chimney",
    57: "Safari Zone",
    58: "Battle Frontier",  # Battle Tower in RS
    59: "Petalburg Woods",
    60: "Rusturf Tunnel",
    61: "Abandoned Ship",
    62: "New Mauville",
    63: "Meteor Falls",
    64: "Meteor Falls",
    65: "Mt. Pyre",
    66: "Hideout",  # Aqua/Magma Hideout
    67: "Shoal Cave",
    68: "Seafloor Cavern",
    69: "Underwater (Seafloor)",
    70: "Victory Road",
    71: "Mirage Island",
    72: "Cave of Origin",
    73: "Southern Island",
    74: "Fiery Path",
    75: "Fiery Path",
    76: "Jagged Pass",
    77: "Jagged Pass",
    78: "Sealed Chamber",
    79: "Underwater (Route 134)",
    80: "Scorched Slab",
    81: "Island Cave",
    82: "Desert Ruins",
    83: "Ancient Tomb",
    84: "Inside of Truck",
    85: "Sky Pillar",
    86: "Secret Base",
    87: "Ferry",
}

# =============================================================================
# FRLG LOCATIONS (0x58-0xC4, recognized by FRLG and E)
# =============================================================================
FRLG_LOCATIONS = {
    88: "Pallet Town",
    89: "Viridian City",
    90: "Pewter City",
    91: "Cerulean City",
    92: "Lavender Town",
    93: "Vermilion City",
    94: "Celadon City",
    95: "Fuchsia City",
    96: "Cinnabar Island",
    97: "Indigo Plateau",
    98: "Saffron City",
    99: "Route 4 (Pokemon Center)",
    100: "Route 10 (Pokemon Center)",
    101: "Route 1",
    102: "Route 2",
    103: "Route 3",
    104: "Route 4",
    105: "Route 5",
    106: "Route 6",
    107: "Route 7",
    108: "Route 8",
    109: "Route 9",
    110: "Route 10",
    111: "Route 11",
    112: "Route 12",
    113: "Route 13",
    114: "Route 14",
    115: "Route 15",
    116: "Route 16",
    117: "Route 17",
    118: "Route 18",
    119: "Route 19",
    120: "Route 20",
    121: "Route 21",
    122: "Route 22",
    123: "Route 23",
    124: "Route 24",
    125: "Route 25",
    126: "Viridian Forest",
    127: "Mt. Moon",
    128: "S.S. Anne",
    129: "Underground Path (5-6)",
    130: "Underground Path (7-8)",
    131: "Diglett's Cave",
    132: "Victory Road",
    133: "Rocket Hideout",
    134: "Silph Co.",
    135: "Pokemon Mansion",
    136: "Safari Zone",
    137: "Pokemon League",
    138: "Rock Tunnel",
    139: "Seafoam Islands",
    140: "Pokemon Tower",
    141: "Cerulean Cave",
    142: "Power Plant",
    143: "One Island",
    144: "Two Island",
    145: "Three Island",
    146: "Four Island",
    147: "Five Island",
    148: "Seven Island",
    149: "Six Island",
    150: "Kindle Road",
    151: "Treasure Beach",
    152: "Cape Brink",
    153: "Bond Bridge",
    154: "Three Isle Port",
    155: "Sevii Isle 6",
    156: "Sevii Isle 7",
    157: "Sevii Isle 8",
    158: "Sevii Isle 9",
    159: "Resort Gorgeous",
    160: "Water Labyrinth",
    161: "Five Isle Meadow",
    162: "Memorial Pillar",
    163: "Outcast Island",
    164: "Green Path",
    165: "Water Path",
    166: "Ruin Valley",
    167: "Trainer Tower",
    168: "Canyon Entrance",
    169: "Sevault Canyon",
    170: "Tanoby Ruins",
    171: "Sevii Isle 22",
    172: "Sevii Isle 23",
    173: "Sevii Isle 24",
    174: "Navel Rock",
    175: "Mt. Ember",
    176: "Berry Forest",
    177: "Icefall Cave",
    178: "Rocket Warehouse",
    179: "Trainer Tower",
    180: "Dotted Hole",
    181: "Lost Cave",
    182: "Pattern Bush",
    183: "Altering Cave",
    184: "Tanoby Chambers",
    185: "Three Isle Path",
    186: "Tanoby Key",
    187: "Birth Island",
    188: "Monean Chamber",
    189: "Liptoo Chamber",
    190: "Weepth Chamber",
    191: "Dilford Chamber",
    192: "Scufib Chamber",
    193: "Rixy Chamber",
    194: "Viapois Chamber",
    195: "Ember Spa",
    196: "Celadon Dept.",  # Pokemon Center 2F
}

# =============================================================================
# EMERALD EXCLUSIVE LOCATIONS (0xC5-0xD4, only recognized by E)
# =============================================================================
EMERALD_LOCATIONS = {
    197: "Aqua Hideout",
    198: "Magma Hideout",
    199: "Mirage Tower",
    200: "Birth Island",
    201: "Faraway Island",
    202: "Artisan Cave",
    203: "Marine Cave",
    204: "Underwater (Marine Cave)",
    205: "Terra Cave",
    206: "Underwater (Route 105)",
    207: "Underwater (Route 125)",
    208: "Underwater (Route 129)",
    209: "Desert Underpass",
    210: "Altering Cave",
    211: "Navel Rock",
    212: "Trainer Hill",
}

# =============================================================================
# SPECIAL LOCATION INDICES (recognized by all games)
# =============================================================================
SPECIAL_LOCATIONS = {
    253: "Fateful Encounter",  # Gift eggs (before hatching)
    254: "In-game Trade",
    255: "Fateful Encounter",  # Event distributions / Distant land
}

# =============================================================================
# COLOSSEUM/XD POKEMON
# Pokemon from Colosseum or XD have location IDs that don't map to GBA locations
# They display as "Distant land" when viewed in GBA games
# Range 213-252 is unused in GBA games
# =============================================================================
COLO_XD_RANGE = range(213, 253)

# =============================================================================
# COMBINED LOOKUP
# =============================================================================
ALL_LOCATIONS = {}
ALL_LOCATIONS.update(RSE_LOCATIONS)
ALL_LOCATIONS.update(FRLG_LOCATIONS)
ALL_LOCATIONS.update(EMERALD_LOCATIONS)
ALL_LOCATIONS.update(SPECIAL_LOCATIONS)


def get_location_name(location_id, game_type='RSE'):
    """
    Get location name from ID.
    
    Args:
        location_id: Location ID from save data (0-255)
        game_type: 'RSE', 'FRLG', or 'Emerald'
        
    Returns:
        str: Location name
    """
    # Handle special cases first
    if location_id in SPECIAL_LOCATIONS:
        return SPECIAL_LOCATIONS[location_id]
    
    # Handle Colosseum/XD range (213-252) - these Pokemon show as "Distant land"
    if location_id in COLO_XD_RANGE:
        return "Distant Land"
    
    # RSE range (0-87)
    if location_id <= 87:
        if location_id in RSE_LOCATIONS:
            return RSE_LOCATIONS[location_id]
    
    # FRLG range (88-196)
    elif 88 <= location_id <= 196:
        if location_id in FRLG_LOCATIONS:
            return FRLG_LOCATIONS[location_id]
    
    # Emerald exclusive range (197-212)
    elif 197 <= location_id <= 212:
        if location_id in EMERALD_LOCATIONS:
            return EMERALD_LOCATIONS[location_id]
    
    # Try combined lookup as fallback
    if location_id in ALL_LOCATIONS:
        return ALL_LOCATIONS[location_id]
    
    # Unknown location - shouldn't happen with valid Pokemon
    return f"Location {location_id}"


def get_location_name_for_display(location_id, game_type='RSE'):
    """
    Get a nicely formatted location name for display.
    Handles edge cases and provides cleaner output.
    
    Args:
        location_id: Location ID from save data
        game_type: 'RSE', 'FRLG', or 'Emerald'
        
    Returns:
        str: Formatted location name
    """
    name = get_location_name(location_id, game_type)
    
    # Clean up some display names
    if name == "Fateful Encounter":
        return "Fateful Encounter"
    if name == "In-game Trade":
        return "Trade"
    if "(Pokemon Center)" in name:
        return name.replace(" (Pokemon Center)", "")
    
    return name


# For backwards compatibility - map old indices to new ones
# This helps if any code was using the old incorrect indices
def get_rse_location(old_index):
    """
    Convert old RSE location index to name.
    The old database had offset issues - this provides compatibility.
    """
    return get_location_name(old_index, 'RSE')


def get_frlg_location(old_index):
    """
    Convert old FRLG location index to name.
    """
    return get_location_name(old_index, 'FRLG')