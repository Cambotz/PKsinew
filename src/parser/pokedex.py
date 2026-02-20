"""
Gen 3 Pokemon Save Parser - Pokedex Module
Handles parsing Pokedex seen/caught bitfields from save data
"""

from .constants import OFFSETS_RS, OFFSETS_E, OFFSETS_FRLG


# Hoenn Regional Dex to National Dex mapping (202 Pokemon)
# Index 0 = Hoenn #1 (Treecko), Index 201 = Hoenn #202 (Deoxys)
# This includes all Pokemon obtainable in RSE, not just Gen 3 natives
HOENN_TO_NATIONAL = [
    # Hoenn #001-010
    252, 253, 254,    # Treecko, Grovyle, Sceptile
    255, 256, 257,    # Torchic, Combusken, Blaziken
    258, 259, 260,    # Mudkip, Marshtomp, Swampert
    261,              # Poochyena
    # Hoenn #011-020
    262,              # Mightyena
    263, 264,         # Zigzagoon, Linoone
    265, 266, 267,    # Wurmple, Silcoon, Beautifly
    268, 269,         # Cascoon, Dustox
    270, 271,         # Lotad, Lombre
    # Hoenn #021-030
    272,              # Ludicolo
    273, 274, 275,    # Seedot, Nuzleaf, Shiftry
    276, 277,         # Taillow, Swellow
    278, 279,         # Wingull, Pelipper
    280, 281,         # Ralts, Kirlia
    # Hoenn #031-040
    282,              # Gardevoir
    283, 284,         # Surskit, Masquerain
    285, 286,         # Shroomish, Breloom
    287, 288, 289,    # Slakoth, Vigoroth, Slaking
    63, 64, 65,       # Abra, Kadabra, Alakazam (Gen 1)
    # Hoenn #041-050
    290, 291, 292,    # Nincada, Ninjask, Shedinja
    293, 294, 295,    # Whismur, Loudred, Exploud
    296, 297,         # Makuhita, Hariyama
    118, 119,         # Goldeen, Seaking (Gen 1)
    # Hoenn #051-060
    129, 130,         # Magikarp, Gyarados (Gen 1)
    298,              # Azurill
    183, 184,         # Marill, Azumarill (Gen 2)
    74, 75, 76,       # Geodude, Graveler, Golem (Gen 1)
    299,              # Nosepass
    # Hoenn #061-070
    300, 301,         # Skitty, Delcatty
    41, 42,           # Zubat, Golbat (Gen 1)
    169,              # Crobat (Gen 2)
    72, 73,           # Tentacool, Tentacruel (Gen 1)
    302, 303,         # Sableye, Mawile
    304, 305,         # Aron, Lairon
    # Hoenn #071-080
    306,              # Aggron
    66, 67, 68,       # Machop, Machoke, Machamp (Gen 1)
    307, 308,         # Meditite, Medicham
    309, 310,         # Electrike, Manectric
    311, 312,         # Plusle, Minun
    # Hoenn #081-090
    81, 82,           # Magnemite, Magneton (Gen 1)
    100, 101,         # Voltorb, Electrode (Gen 1)
    313, 314,         # Volbeat, Illumise
    43, 44, 45,       # Oddish, Gloom, Vileplume (Gen 1)
    182,              # Bellossom (Gen 2)
    # Hoenn #091-100
    84, 85,           # Doduo, Dodrio (Gen 1)
    315,              # Roselia
    316, 317,         # Gulpin, Swalot
    318, 319,         # Carvanha, Sharpedo
    320, 321,         # Wailmer, Wailord
    # Hoenn #101-110
    322, 323,         # Numel, Camerupt
    218, 219,         # Slugma, Magcargo (Gen 2)
    324,              # Torkoal
    88, 89,           # Grimer, Muk (Gen 1)
    109, 110,         # Koffing, Weezing (Gen 1)
    325, 326,         # Spoink, Grumpig
    # Hoenn #111-120
    27, 28,           # Sandshrew, Sandslash (Gen 1)
    327,              # Spinda
    227,              # Skarmory (Gen 2)
    328, 329, 330,    # Trapinch, Vibrava, Flygon
    331, 332,         # Cacnea, Cacturne
    # Hoenn #121-130
    333, 334,         # Swablu, Altaria
    335, 336,         # Zangoose, Seviper
    337, 338,         # Lunatone, Solrock
    339, 340,         # Barboach, Whiscash
    341, 342,         # Corphish, Crawdaunt
    # Hoenn #131-140
    343, 344,         # Baltoy, Claydol
    345, 346,         # Lileep, Cradily
    347, 348,         # Anorith, Armaldo
    174,              # Igglybuff (Gen 2)
    39, 40,           # Jigglypuff, Wigglytuff (Gen 1)
    349, 350,         # Feebas, Milotic
    # Hoenn #141-150
    351,              # Castform
    120, 121,         # Staryu, Starmie (Gen 1)
    352,              # Kecleon
    353, 354,         # Shuppet, Banette
    355, 356,         # Duskull, Dusclops
    357,              # Tropius
    # Hoenn #151-160
    358,              # Chimecho
    359,              # Absol
    37, 38,           # Vulpix, Ninetales (Gen 1)
    172,              # Pichu (Gen 2)
    25, 26,           # Pikachu, Raichu (Gen 1)
    54, 55,           # Psyduck, Golduck (Gen 1)
    360,              # Wynaut
    # Hoenn #161-170
    202,              # Wobbuffet (Gen 2)
    177, 178,         # Natu, Xatu (Gen 2)
    203,              # Girafarig (Gen 2)
    231, 232,         # Phanpy, Donphan (Gen 2)
    127,              # Pinsir (Gen 1)
    214,              # Heracross (Gen 2)
    111, 112,         # Rhyhorn, Rhydon (Gen 1)
    # Hoenn #171-180
    361, 362,         # Snorunt, Glalie
    363, 364, 365,    # Spheal, Sealeo, Walrein
    366, 367, 368,    # Clamperl, Huntail, Gorebyss
    369,              # Relicanth
    222,              # Corsola (Gen 2)
    # Hoenn #181-190
    170, 171,         # Chinchou, Lanturn (Gen 2)
    370,              # Luvdisc
    116, 117,         # Horsea, Seadra (Gen 1)
    230,              # Kingdra (Gen 2)
    371, 372, 373,    # Bagon, Shelgon, Salamence
    374, 375,         # Beldum, Metang
    # Hoenn #191-202
    376,              # Metagross
    377, 378, 379,    # Regirock, Regice, Registeel
    380, 381,         # Latias, Latios
    382, 383, 384,    # Kyogre, Groudon, Rayquaza
    385, 386          # Jirachi, Deoxys
]

# Create reverse lookup: National -> Hoenn (for quick checks)
NATIONAL_TO_HOENN = {nat: hoenn + 1 for hoenn, nat in enumerate(HOENN_TO_NATIONAL)}


def count_bits_set(data_bytes):
    """Count number of bits set to 1 in a byte array."""
    count = 0
    for byte in data_bytes:
        count += bin(byte).count('1')
    return count


def get_pokemon_from_bitfield(data_bytes, max_pokemon=386):
    """
    Get list of Pokemon (National Dex numbers) that are marked in bitfield.
    
    Args:
        data_bytes: 49 bytes of bitfield data
        max_pokemon: Maximum Pokemon to check (386 for Gen 3)
        
    Returns:
        list: National Dex numbers of marked Pokemon
    """
    pokemon_list = []
    
    for poke_num in range(max_pokemon):
        # Pokemon are 0-indexed in the bitfield
        byte_index = poke_num >> 3  # Divide by 8
        bit_index = poke_num & 7     # Mod 8
        
        if byte_index < len(data_bytes):
            if data_bytes[byte_index] & (1 << bit_index):
                # Pokemon are 1-indexed in National Dex
                pokemon_list.append(poke_num + 1)
    
    return pokemon_list


def filter_hoenn_pokemon(national_list):
    """
    Filter a list of National Dex numbers to only include Hoenn Dex Pokemon.
    
    Args:
        national_list: List of National Dex numbers
        
    Returns:
        list: Only the National Dex numbers that are in the Hoenn Dex
    """
    hoenn_set = set(HOENN_TO_NATIONAL)
    return [n for n in national_list if n in hoenn_set]


def parse_pokedex(data, section0_offset, game_type='RS'):
    """
    Parse Pokedex seen and owned data from save file.
    
    Args:
        data: bytearray of full save data
        section0_offset: Offset to Section 0 in save data
        game_type: 'RS', 'E', or 'FRLG'
        
    Returns:
        dict: {
            'owned_count': int,
            'seen_count': int,
            'owned_list': list of National Dex numbers,
            'seen_list': list of National Dex numbers,
            'hoenn_owned_count': int (RSE only),
            'hoenn_seen_count': int (RSE only)
        }
    """
    # Get correct offsets for game type
    if game_type == 'FRLG':
        offsets = OFFSETS_FRLG
    elif game_type == 'E':
        offsets = OFFSETS_E
    else:  # RS
        offsets = OFFSETS_RS
    
    # Pokedex offsets are in Section 0
    OWNED_OFFSET = offsets.get('pokedex_owned', 0x0028)
    SEEN_OFFSET = offsets.get('pokedex_seen', 0x005C)
    BITFIELD_SIZE = 49  # 49 bytes = 392 bits (covers 386 Pokemon)
    
    result = {
        'owned_count': 0,
        'seen_count': 0,
        'owned_list': [],
        'seen_list': [],
        'hoenn_owned_count': 0,
        'hoenn_seen_count': 0
    }
    
    try:
        # Read owned bitfield
        owned_start = section0_offset + OWNED_OFFSET
        owned_end = owned_start + BITFIELD_SIZE
        
        if owned_end <= len(data):
            owned_bytes = data[owned_start:owned_end]
            result['owned_list'] = get_pokemon_from_bitfield(owned_bytes)
            result['owned_count'] = len(result['owned_list'])
        
        # Read seen bitfield
        seen_start = section0_offset + SEEN_OFFSET
        seen_end = seen_start + BITFIELD_SIZE
        
        if seen_end <= len(data):
            seen_bytes = data[seen_start:seen_end]
            result['seen_list'] = get_pokemon_from_bitfield(seen_bytes)
            result['seen_count'] = len(result['seen_list'])
        
        # For RSE games, also calculate Hoenn Dex counts
        if game_type in ('RS', 'E'):
            hoenn_owned = filter_hoenn_pokemon(result['owned_list'])
            hoenn_seen = filter_hoenn_pokemon(result['seen_list'])
            result['hoenn_owned_count'] = len(hoenn_owned)
            result['hoenn_seen_count'] = len(hoenn_seen)
            
    except Exception as e:
        print(f"[Pokedex] Error parsing: {e}")
        import traceback
        traceback.print_exc()
    
    return result