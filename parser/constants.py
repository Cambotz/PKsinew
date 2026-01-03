"""
Gen 3 Pokemon Save Parser - Constants
All lookup tables, offsets, and configuration values
"""

# ============================================================
# DATA BLOCK PERMUTATIONS
# ============================================================
# Pokemon data has 4 encrypted 12-byte blocks that are shuffled
# based on personality % 24. 
# Format: PERMUTATIONS[index][TYPE] = POSITION
# Types: 0=Growth, 1=Attacks, 2=EVs, 3=Misc

PERMUTATIONS = [
    [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2],
    [0, 2, 3, 1], [0, 3, 2, 1], [1, 0, 2, 3], [1, 0, 3, 2],
    [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
    [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2],
    [2, 3, 0, 1], [3, 2, 0, 1], [1, 2, 3, 0], [1, 3, 2, 0],
    [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0]
]

# Block type indices
BLOCK_GROWTH = 0
BLOCK_ATTACKS = 1
BLOCK_EVS = 2
BLOCK_MISC = 3


# ============================================================
# SPECIES CONVERSION
# ============================================================
# Gen 3 uses different internal IDs for Hoenn Pokemon (252-386)
# Kanto/Johto (1-251): Internal = National
# Hoenn (252-386): Internal 277-411 maps to National 252-386 (scrambled order!)

INTERNAL_TO_NATIONAL = {
    277: 252,  # Treecko
    278: 253,  # Grovyle
    279: 254,  # Sceptile
    280: 255,  # Torchic
    281: 256,  # Combusken
    282: 257,  # Blaziken
    283: 258,  # Mudkip
    284: 259,  # Marshtomp
    285: 260,  # Swampert
    286: 261,  # Poochyena
    287: 262,  # Mightyena
    288: 263,  # Zigzagoon
    289: 264,  # Linoone
    290: 265,  # Wurmple
    291: 266,  # Silcoon
    292: 267,  # Beautifly
    293: 268,  # Cascoon
    294: 269,  # Dustox
    295: 270,  # Lotad
    296: 271,  # Lombre
    297: 272,  # Ludicolo
    298: 273,  # Seedot
    299: 274,  # Nuzleaf
    300: 275,  # Shiftry
    301: 290,  # Nincada
    302: 291,  # Ninjask
    303: 292,  # Shedinja
    304: 276,  # Taillow
    305: 277,  # Swellow
    306: 285,  # Shroomish
    307: 286,  # Breloom
    308: 327,  # Spinda
    309: 278,  # Wingull
    310: 279,  # Pelipper
    311: 283,  # Surskit
    312: 284,  # Masquerain
    313: 320,  # Wailmer
    314: 321,  # Wailord
    315: 300,  # Skitty
    316: 301,  # Delcatty
    317: 352,  # Kecleon
    318: 343,  # Baltoy
    319: 344,  # Claydol
    320: 299,  # Nosepass
    321: 324,  # Torkoal
    322: 302,  # Sableye
    323: 339,  # Barboach
    324: 340,  # Whiscash
    325: 370,  # Luvdisc
    326: 341,  # Corphish
    327: 342,  # Crawdaunt
    328: 349,  # Feebas
    329: 350,  # Milotic
    330: 318,  # Carvanha
    331: 319,  # Sharpedo
    332: 328,  # Trapinch
    333: 329,  # Vibrava
    334: 330,  # Flygon
    335: 296,  # Makuhita
    336: 297,  # Hariyama
    337: 309,  # Electrike
    338: 310,  # Manectric
    339: 322,  # Numel
    340: 323,  # Camerupt
    341: 363,  # Spheal
    342: 364,  # Sealeo
    343: 365,  # Walrein
    344: 331,  # Cacnea
    345: 332,  # Cacturne
    346: 361,  # Snorunt
    347: 362,  # Glalie
    348: 337,  # Lunatone
    349: 338,  # Solrock
    350: 298,  # Azurill
    351: 325,  # Spoink
    352: 326,  # Grumpig
    353: 311,  # Plusle
    354: 312,  # Minun
    355: 303,  # Mawile
    356: 307,  # Meditite
    357: 308,  # Medicham
    358: 333,  # Swablu
    359: 334,  # Altaria
    360: 360,  # Wynaut
    361: 355,  # Duskull
    362: 356,  # Dusclops
    363: 315,  # Roselia
    364: 287,  # Slakoth
    365: 288,  # Vigoroth
    366: 289,  # Slaking
    367: 316,  # Gulpin
    368: 317,  # Swalot
    369: 357,  # Tropius
    370: 293,  # Whismur
    371: 294,  # Loudred
    372: 295,  # Exploud
    373: 366,  # Clamperl
    374: 367,  # Huntail
    375: 368,  # Gorebyss
    376: 359,  # Absol
    377: 353,  # Shuppet
    378: 354,  # Banette
    379: 336,  # Seviper
    380: 335,  # Zangoose
    381: 369,  # Relicanth
    382: 304,  # Aron
    383: 305,  # Lairon
    384: 306,  # Aggron
    385: 351,  # Castform
    386: 313,  # Volbeat
    387: 314,  # Illumise
    388: 345,  # Lileep
    389: 346,  # Cradily
    390: 347,  # Anorith
    391: 348,  # Armaldo
    392: 280,  # Ralts
    393: 281,  # Kirlia
    394: 282,  # Gardevoir
    395: 371,  # Bagon
    396: 372,  # Shelgon
    397: 373,  # Salamence
    398: 374,  # Beldum
    399: 375,  # Metang
    400: 376,  # Metagross
    401: 377,  # Regirock
    402: 378,  # Regice
    403: 379,  # Registeel
    404: 382,  # Kyogre
    405: 383,  # Groudon
    406: 384,  # Rayquaza
    407: 380,  # Latias
    408: 381,  # Latios
    409: 385,  # Jirachi
    410: 386,  # Deoxys
    411: 358,  # Chimecho
}

# Reverse mapping (National to Internal) for writing saves
NATIONAL_TO_INTERNAL = {v: k for k, v in INTERNAL_TO_NATIONAL.items()}


# ============================================================
# GAME-SPECIFIC OFFSETS
# ============================================================
# Section 1 offsets differ between game versions

OFFSETS_FRLG = {
    'team_size': 0x0034,
    'team_data': 0x0038,
    'money': 0x0290,
    'security_key_section': 0,      # Key is in Section 0
    'security_key_offset': 0x0F20,  # Offset within Section 0
    'items': 0x0310,
    'key_items': 0x03B8,
    'pokeballs': 0x0430,
    'tms_hms': 0x0464,
    'berries': 0x054C,
    'item_slots': {
        'items': 42,
        'key_items': 30,
        'pokeballs': 13,
        'tms_hms': 58,
        'berries': 43,
    },
    # Pokedex offsets (Section 0)
    'pokedex_owned': 0x0028,  # 49 bytes bitfield
    'pokedex_seen': 0x005C,   # 49 bytes bitfield
}

# Ruby and Sapphire - NO item/money encryption, DIFFERENT offsets from Emerald!
# RS has smaller pockets (20 items vs 30), so subsequent pockets start EARLIER
OFFSETS_RS = {
    'team_size': 0x0234,
    'team_data': 0x0238,
    'money': 0x0490,
    'security_key_section': None,   # RS does NOT use encryption!
    'security_key_offset': None,
    # RS pocket offsets - smaller pockets mean earlier offsets than Emerald
    # Items: 0x0560, 20 slots (80 bytes) → ends at 0x05B0
    # Key Items: 0x05B0, 20 slots (80 bytes) → ends at 0x0600
    # Pokeballs: 0x0600, 16 slots (64 bytes) → ends at 0x0640
    # TMs: 0x0640, 64 slots (256 bytes) → ends at 0x0740
    # Berries: 0x0740, 46 slots
    'items': 0x0560,
    'key_items': 0x05B0,
    'pokeballs': 0x0600,
    'tms_hms': 0x0640,
    'berries': 0x0740,
    'item_slots': {
        'items': 20,       # RS has 20 item slots
        'key_items': 20,   # RS has 20 key item slots
        'pokeballs': 16,
        'tms_hms': 64,
        'berries': 46,
    },
    # Pokedex offsets (Section 0)
    'pokedex_owned': 0x0028,  # 49 bytes bitfield
    'pokedex_seen': 0x005C,   # 49 bytes bitfield
}

# Emerald - has encryption but key location differs from FRLG
# Emerald has LARGER pockets (30 items vs 20), so subsequent pockets start LATER than RS
OFFSETS_E = {
    'team_size': 0x0234,
    'team_data': 0x0238,
    'money': 0x0490,
    'security_key_section': 0,      # Key is in Section 0
    'security_key_offset': 0x00AC,  # Offset within Section 0
    # Emerald pocket offsets - larger pockets mean later offsets than RS
    # Items: 0x0560, 30 slots (120 bytes) → ends at 0x05D8
    # Key Items: 0x05D8, 30 slots (120 bytes) → ends at 0x0650
    # Pokeballs: 0x0650, 16 slots (64 bytes) → ends at 0x0690
    # TMs: 0x0690, 64 slots (256 bytes) → ends at 0x0790
    # Berries: 0x0790, 46 slots
    'items': 0x0560,
    'key_items': 0x05D8,
    'pokeballs': 0x0650,
    'tms_hms': 0x0690,
    'berries': 0x0790,
    'item_slots': {
        'items': 30,       # Emerald has 30 item slots (RS has 20)
        'key_items': 30,   # Emerald has 30 key item slots (RS has 20)
        'pokeballs': 16,
        'tms_hms': 64,
        'berries': 46,
    },
    # Pokedex offsets (Section 0)
    'pokedex_owned': 0x0028,  # 49 bytes bitfield
    'pokedex_seen': 0x005C,   # 49 bytes bitfield
}

# Legacy alias for backward compatibility
OFFSETS_RSE = OFFSETS_RS  # Default to RS (will be overridden by game detection)


# ============================================================
# EXPERIENCE TABLES
# ============================================================

EXP_FAST = [
    0, 6, 21, 51, 100, 172, 274, 409, 583, 800,
    1064, 1382, 1757, 2195, 2700, 3276, 3924, 4649, 5457, 6350,
    7328, 8398, 9563, 10827, 12191, 13660, 15238, 16929, 18737, 20675,
    22735, 24923, 27240, 29698, 32291, 35024, 37900, 40921, 44089, 47414,
    50891, 54523, 58312, 62260, 66367, 70638, 75075, 79682, 84460, 89411,
    94539, 99846, 105335, 111018, 116887, 122945, 129194, 135636, 142274, 149110,
    156146, 163384, 170827, 178477, 186336, 194406, 202690, 211190, 219909, 228849,
    238013, 247402, 257020, 266869, 276951, 287268, 297824, 308620, 319658, 330941,
    342471, 354250, 366280, 378563, 391102, 403898, 416955, 430274, 443859, 457711,
    471833, 486227, 500895, 515840, 531064, 546570, 562360, 578437, 594803, 611460,
    628410
]

EXP_MEDIUM_FAST = [
    0, 8, 27, 64, 125, 216, 343, 512, 729, 1000,
    1331, 1728, 2197, 2744, 3375, 4096, 4913, 5832, 6859, 8000,
    9261, 10648, 12167, 13824, 15625, 17576, 19683, 21952, 24389, 27000,
    29791, 32768, 35937, 39304, 42875, 46656, 50653, 54872, 59319, 64000,
    68921, 74088, 79507, 85184, 91125, 97336, 103823, 110592, 117649, 125000,
    132651, 140608, 148877, 157464, 166375, 175616, 185193, 195112, 205379, 216000,
    226981, 238328, 250047, 262144, 274625, 287496, 300763, 314432, 328509, 343000,
    357911, 373248, 389017, 405224, 421875, 438976, 456533, 474552, 493039, 512000,
    531441, 551368, 571787, 592704, 614125, 636056, 658503, 681472, 704969, 729000,
    753571, 778688, 804357, 830584, 857375, 884736, 912673, 941192, 970299, 1000000
]

EXP_MEDIUM_SLOW = [
    0, 9, 57, 96, 135, 179, 236, 314, 419, 560,
    742, 973, 1261, 1612, 2035, 2535, 3120, 3798, 4575, 5460,
    6458, 7577, 8825, 10208, 11735, 13411, 15244, 17242, 19411, 21760,
    24294, 27021, 29949, 33084, 36435, 40007, 43808, 47846, 52127, 56660,
    61450, 66505, 71833, 77440, 83335, 89523, 96012, 102810, 109923, 117360,
    125126, 133229, 141677, 150476, 159635, 169159, 179056, 189334, 199999, 211060,
    222522, 234393, 246681, 259392, 272535, 286115, 300140, 314618, 329555, 344960,
    360838, 377197, 394045, 411388, 429235, 447591, 466464, 485862, 505791, 526260,
    547274, 568841, 590969, 613664, 636935, 660787, 685228, 710266, 735907, 762160,
    789030, 816525, 844653, 873420, 902835, 932903, 963632, 995030, 1027103, 1059860
]

EXP_SLOW = [
    0, 10, 33, 80, 156, 270, 428, 640, 911, 1250,
    1663, 2160, 2746, 3430, 4218, 5120, 6141, 7290, 8573, 10000,
    11576, 13310, 15208, 17280, 19531, 21970, 24603, 27440, 30486, 33750,
    37238, 40960, 44921, 49130, 53593, 58320, 63316, 68590, 74148, 80000,
    86151, 92610, 99383, 106480, 113906, 121670, 129778, 138240, 147061, 156250,
    165813, 175760, 186096, 196830, 207968, 219520, 231491, 243890, 256723,
    270000, 283726, 297910, 312558, 327680, 343281, 359370, 375953, 393040,
    410636, 428750, 447388, 466560, 486271, 506530, 527343, 548720, 570666,
    593190, 616298, 714733, 740880, 767656, 795070, 823128, 851840, 881211,
    911250, 941963, 973360, 1005446, 1038230, 1071718, 1105920, 1140841, 1176490, 
    1212873, 1250000
]

EXP_ERRATIC = [
    0, 15, 52, 122, 237, 406, 637, 942, 1326, 1800,
    2369, 3041, 3822, 4719, 5737, 6881, 8155, 9564, 11111, 12800,
    14632, 16610, 18737, 21012, 23437, 26012, 28737, 31610, 34632, 37800,
    41111, 44564, 48155, 51881, 55737, 59719, 63822, 68041, 72369, 76800,
    81326, 85942, 90637, 95406, 100237, 105122, 110052, 115015, 120001, 125000,
    131324, 137795, 144410, 151165, 158056, 165079, 172229, 179503, 186894, 194400,
    202013, 209728, 217540, 225443, 233431, 241496, 249633, 257834, 267406, 276458,
    286328, 296358, 305767, 316074, 326531, 336255, 346965, 357812, 367807, 378880,
    390077, 400293, 411686, 423190, 433572, 445175, 457001, 469056, 481343, 493864,
    506625, 519631, 532879, 546378, 560123, 574128, 588388, 602914, 617710, 632785,
    648135, 663774, 679706, 695942, 712497, 729384, 746610, 764190, 782140, 800476
]

EXP_FLUCTUATING = [
    0, 4, 13, 32, 65, 112, 178, 276, 393, 540,
    745, 967, 1230, 1591, 1957, 2457, 3046, 3732, 4526, 5440,
    6482, 7666, 9003, 10506, 12187, 14060, 16050, 18174, 20434, 22844,
    25399, 28105, 30966, 33986, 37166, 40511, 44023, 47706, 51566, 55605,
    59827, 64238, 68844, 73647, 78653, 83867, 89302, 94965, 100363, 105905,
    111622, 117537, 123671, 130037, 136646, 143512, 150649, 158069, 165786, 173813,
    182162, 190846, 199879, 209274, 219044, 229203, 239764, 250741, 262148, 273999,
    286308, 299089, 312356, 326123, 340404, 355215, 370569, 386482, 402968, 420043,
    437721, 456017, 474946, 494523, 514764, 535684, 557298, 579621, 602668, 626455,
    651000, 676317, 702423, 729332, 757062, 785627, 815046, 845333, 876506, 908580
]

EXP_TABLES = {
    "fast": EXP_FAST,
    "medium_fast": EXP_MEDIUM_FAST,
    "medium_slow": EXP_MEDIUM_SLOW,
    "slow": EXP_SLOW,
    "erratic": EXP_ERRATIC,
    "fluctuating": EXP_FLUCTUATING
}


# ============================================================
# SPECIES GROWTH RATES
# ============================================================
# Maps species (National Dex) to growth rate

GROWTH_RATE_SPECIES = {
    "erratic": {
        285, 286, 290, 291, 292, 296, 297, 313, 314, 316,
        317, 320, 321, 333, 334, 335, 336, 341, 342, 345,
        346, 347, 348, 349, 350, 366, 367, 368
    },
    "fast": {
        35, 36, 39, 40, 113, 165, 166, 167, 168, 173, 60,
        174, 175, 176, 183, 184, 190, 200, 209, 210, 222,
        225, 235, 242, 298, 300, 301, 303, 325, 326, 327,
        337, 338, 353, 354, 355, 356, 358, 370
    },
    "medium_fast": {
        10, 11, 12, 13, 14, 15, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 37, 38, 41, 42,
        46, 47, 48, 49, 50, 51, 52, 53, 54, 55,
        56, 57, 77, 78, 79, 80, 81, 82, 83, 84,
        85, 86, 87, 88, 89, 95, 96, 97, 98, 99,
        100, 101, 104, 105, 106, 107, 108, 114, 115, 116,
        117, 118, 119, 122, 123, 124, 125, 126, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 161, 162,
        163, 164, 169, 172, 177, 178, 185, 193, 194, 195,
        196, 197, 199, 201, 202, 203, 204, 205, 206, 208,
        211, 212, 216, 217, 218, 219, 223, 224, 230, 231,
        232, 233, 236, 237, 238, 239, 240, 261, 262, 263,
        264, 265, 266, 267, 268, 269, 278, 279, 283, 284,
        299, 307, 308, 311, 312, 322, 323, 324, 339, 340,
        343, 344, 351, 360, 361, 362
    },
    "medium_slow": {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 16,
        17, 18, 29, 30, 31, 32, 33, 34, 43, 44,
        45, 61, 62, 63, 64, 65, 66, 67, 68,
        69, 70, 71, 74, 75, 76, 92, 93, 94, 151,
        152, 153, 154, 155, 156, 157, 158, 159, 160, 179,
        180, 181, 182, 186, 187, 188, 189, 191, 192, 198,
        207, 213, 215, 251, 252, 253, 254, 255, 256, 257,
        258, 259, 260, 270, 271, 272, 273, 274, 275, 276,
        277, 293, 294, 295, 302, 315, 328, 329, 330, 331,
        332, 352, 359, 363, 364, 365
    },
    "slow": {
        58, 59, 72, 73, 90, 91, 102, 103, 111, 112, 144,
        120, 121, 127, 128, 129, 130, 131, 142, 143,
        145, 146, 147, 148, 149, 150, 170, 171, 214, 220,
        221, 226, 227, 228, 229, 234, 241, 243, 244, 245,
        246, 247, 248, 249, 250, 280, 281, 282, 287, 288,
        289, 304, 305, 306, 309, 310, 318, 319, 357, 369,
        371, 372, 373, 374, 375, 376, 377, 378, 379, 380,
        381, 382, 383, 384, 385, 386
    },
    "fluctuating": set()  # No Gen 3 Pokemon use this
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def convert_species_to_national(internal_species):
    """Convert internal species ID to National Dex number."""
    if 1 <= internal_species <= 251:
        return internal_species
    if internal_species in INTERNAL_TO_NATIONAL:
        return INTERNAL_TO_NATIONAL[internal_species]
    return internal_species


def convert_species_to_internal(national_species):
    """Convert National Dex number to internal species ID."""
    if 1 <= national_species <= 251:
        return national_species
    if national_species in NATIONAL_TO_INTERNAL:
        return NATIONAL_TO_INTERNAL[national_species]
    return national_species


def is_valid_species(internal_species):
    """Check if an internal species ID is valid for Gen 3."""
    return (1 <= internal_species <= 251) or (277 <= internal_species <= 411)


def get_growth_rate(species):
    """Get growth rate name for a species (National Dex)."""
    for rate, species_set in GROWTH_RATE_SPECIES.items():
        if species in species_set:
            return rate
    return "medium_fast"  # Default


def get_exp_for_level(species, level):
    """Get minimum EXP needed for a given level."""
    rate = get_growth_rate(species)
    table = EXP_TABLES.get(rate, EXP_MEDIUM_FAST)
    if level < 1:
        return 0
    if level > 100:
        level = 100
    return table[level - 1] if level <= len(table) else table[-1]


def calculate_level_from_exp(exp, species):
    """Calculate level from experience points."""
    rate = get_growth_rate(species)
    table = EXP_TABLES.get(rate, EXP_MEDIUM_FAST)
    
    for level in range(1, 101):
        if level >= len(table):
            return 100
        if exp < table[level]:
            return level
    return 100