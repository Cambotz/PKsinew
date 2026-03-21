#!/usr/bin/env python3
"""
gen1_parser.py — Pokémon Red/Blue/Yellow Save Data Tables

Provides:
  - GEN1_INTERNAL_SPECIES  : internal species ID → name
  - GEN1_NATIONAL_DEX      : National Dex number → name
  - GEN1_MOVES             : move ID → name
  - GEN1_MOVE_MAX_PP       : move ID → base PP
  - GEN1_TYPES             : type byte → name
  - GEN1_CHAR_TABLE        : Game Boy character encoding
  - POKEMON_BASE_STATS     : species name → {HP,Attack,Defense,Speed,Special}
  - GEN1_ITEMS             : item ID → name
  - GEN1_POKEMON_STRUCT    : offset map for the 44-byte party block
"""

# ─────────────────────────────────────────────────────────────────────────────
# Internal Species Table  (species byte → name)
# Gen 1 uses a scrambled internal ID, NOT the National Dex number.
# ─────────────────────────────────────────────────────────────────────────────
GEN1_INTERNAL_SPECIES = {
    0x01: "Rhydon",      0x02: "Kangaskhan",  0x03: "Nidoran♂",  0x04: "Clefairy",
    0x05: "Spearow",     0x06: "Voltorb",     0x07: "Nidoking",  0x08: "Slowbro",
    0x09: "Ivysaur",     0x0A: "Exeggutor",   0x0B: "Lickitung", 0x0C: "Exeggcute",
    0x0D: "Grimer",      0x0E: "Gengar",      0x0F: "Nidoran♀",  0x10: "Nidoqueen",
    0x11: "Cubone",      0x12: "Rhyhorn",     0x13: "Lapras",    0x14: "Arcanine",
    0x15: "Mew",         0x16: "Gyarados",    0x17: "Shellder",  0x18: "Tentacool",
    0x19: "Gastly",      0x1A: "Scyther",     0x1B: "Staryu",    0x1C: "Blastoise",
    0x1D: "Pinsir",      0x1E: "Tangela",
    0x21: "Growlithe",   0x22: "Onix",        0x23: "Fearow",    0x24: "Pidgey",
    0x25: "Slowpoke",    0x26: "Kadabra",     0x27: "Graveler",  0x28: "Chansey",
    0x29: "Machoke",     0x2A: "Mr. Mime",    0x2B: "Hitmonlee", 0x2C: "Hitmonchan",
    0x2D: "Arbok",       0x2E: "Parasect",    0x2F: "Psyduck",   0x30: "Drowzee",
    0x31: "Golem",       0x33: "Magmar",      0x35: "Electabuzz",0x36: "Magneton",
    0x37: "Koffing",     0x39: "Mankey",      0x3A: "Seel",      0x3B: "Diglett",
    0x3C: "Tauros",      0x40: "Farfetch'd",  0x41: "Venonat",   0x42: "Dragonite",
    0x46: "Doduo",       0x47: "Poliwag",     0x48: "Jynx",      0x49: "Moltres",
    0x4A: "Articuno",    0x4B: "Zapdos",      0x4C: "Ditto",     0x4D: "Meowth",
    0x4E: "Krabby",      0x52: "Vulpix",      0x53: "Ninetales", 0x54: "Pikachu",
    0x55: "Raichu",      0x58: "Dratini",     0x59: "Dragonair", 0x5A: "Kabuto",
    0x5B: "Kabutops",    0x5C: "Horsea",      0x5D: "Seadra",    0x60: "Sandshrew",
    0x61: "Sandslash",   0x62: "Omanyte",     0x63: "Omastar",   0x64: "Jigglypuff",
    0x65: "Wigglytuff",  0x66: "Eevee",       0x67: "Flareon",   0x68: "Jolteon",
    0x69: "Vaporeon",    0x6A: "Machop",      0x6B: "Zubat",     0x6C: "Ekans",
    0x6D: "Paras",       0x6E: "Poliwhirl",   0x6F: "Poliwrath", 0x70: "Weedle",
    0x71: "Kakuna",      0x72: "Beedrill",    0x74: "Dodrio",    0x75: "Primeape",
    0x76: "Dugtrio",     0x77: "Venomoth",    0x78: "Dewgong",   0x7B: "Caterpie",
    0x7C: "Metapod",     0x7D: "Butterfree",  0x7E: "Machamp",   0x80: "Golduck",
    0x81: "Hypno",       0x82: "Golbat",      0x83: "Mewtwo",    0x84: "Snorlax",
    0x85: "Magikarp",    0x88: "Muk",         0x8A: "Kingler",   0x8B: "Cloyster",
    0x8D: "Electrode",   0x8E: "Clefable",    0x8F: "Weezing",   0x90: "Persian",
    0x91: "Marowak",     0x93: "Haunter",     0x94: "Abra",      0x95: "Alakazam",
    0x96: "Pidgeotto",   0x97: "Pidgeot",     0x98: "Starmie",   0x99: "Bulbasaur",
    0x9A: "Venusaur",    0x9B: "Tentacruel",  0x9D: "Goldeen",   0x9E: "Seaking",
    0xA3: "Ponyta",      0xA4: "Rapidash",    0xA5: "Rattata",   0xA6: "Raticate",
    0xA7: "Nidorino",    0xA8: "Nidorina",    0xA9: "Geodude",   0xAA: "Porygon",
    0xAB: "Aerodactyl",  0xAD: "Magnemite",   0xB0: "Charmander",0xB2: "Charmeleon",
    0xB4: "Charizard",   0xB1: "Squirtle",    0xB3: "Wartortle", 0xB5: "Blastoise",
    0xB6: "Horsea",      0xB7: "Seadra",      0xB8: "Sandshrew", 0xB9: "Oddish",      # Red/Blue
    0xBA: "Sandslash",   0xBB: "Gloom",       0xBC: "Vileplume", 0xBD: "Scyther",     # Red/Blue
    0xBE: "Victreebel",  0xBF: "Electabuzz",                                          # Red/Blue
}

# ─────────────────────────────────────────────────────────────────────────────
# Yellow Version Notes
# ─────────────────────────────────────────────────────────────────────────────
# Yellow uses the SAME internal species IDs as Red/Blue.
# There are NO species mapping differences between Gen 1 versions.
# All three games (Red/Blue/Yellow) share the same species index.
#
# The confusion may come from:
# - Different Pokemon availability/locations in Yellow
# - Pikachu as starter instead of Gen 1 starters
# - Some Pokemon sprites look different in Yellow
# 
# But the internal species ID → species name mapping is IDENTICAL across all Gen 1.
# ─────────────────────────────────────────────────────────────────────────────

def get_gen1_species(species_id: int, is_yellow: bool = False) -> str:
    """Get species name from internal ID. Yellow uses same mapping as Red/Blue."""
    return GEN1_INTERNAL_SPECIES.get(species_id, f"??#{species_id:02X}")

# Build reverse map: name → internal ID (useful for writing)
GEN1_SPECIES_BY_NAME = {v: k for k, v in GEN1_INTERNAL_SPECIES.items()}

# ─────────────────────────────────────────────────────────────────────────────
# National Dex  (dex number → name)
# ─────────────────────────────────────────────────────────────────────────────
GEN1_NATIONAL_DEX = {
    1: "Bulbasaur",   2: "Ivysaur",    3: "Venusaur",   4: "Charmander", 5: "Charmeleon",
    6: "Charizard",   7: "Squirtle",   8: "Wartortle",  9: "Blastoise",  10: "Caterpie",
    11: "Metapod",    12: "Butterfree",13: "Weedle",    14: "Kakuna",    15: "Beedrill",
    16: "Pidgey",     17: "Pidgeotto", 18: "Pidgeot",   19: "Rattata",   20: "Raticate",
    21: "Spearow",    22: "Fearow",    23: "Ekans",     24: "Arbok",     25: "Pikachu",
    26: "Raichu",     27: "Sandshrew", 28: "Sandslash", 29: "Nidoran♀",  30: "Nidorina",
    31: "Nidoqueen",  32: "Nidoran♂",  33: "Nidorino",  34: "Nidoking",  35: "Clefairy",
    36: "Clefable",   37: "Vulpix",    38: "Ninetales", 39: "Jigglypuff",40: "Wigglytuff",
    41: "Zubat",      42: "Golbat",    43: "Oddish",    44: "Gloom",     45: "Vileplume",
    46: "Paras",      47: "Parasect",  48: "Venonat",   49: "Venomoth",  50: "Diglett",
    51: "Dugtrio",    52: "Meowth",    53: "Persian",   54: "Psyduck",   55: "Golduck",
    56: "Mankey",     57: "Primeape",  58: "Growlithe", 59: "Arcanine",  60: "Poliwag",
    61: "Poliwhirl",  62: "Poliwrath", 63: "Abra",      64: "Kadabra",   65: "Alakazam",
    66: "Machop",     67: "Machoke",   68: "Machamp",   69: "Bellsprout",70: "Weepinbell",
    71: "Victreebel", 72: "Tentacool", 73: "Tentacruel",74: "Geodude",   75: "Graveler",
    76: "Golem",      77: "Ponyta",    78: "Rapidash",  79: "Slowpoke",  80: "Slowbro",
    81: "Magnemite",  82: "Magneton",  83: "Farfetch'd",84: "Doduo",     85: "Dodrio",
    86: "Seel",       87: "Dewgong",   88: "Grimer",    89: "Muk",       90: "Shellder",
    91: "Cloyster",   92: "Gastly",    93: "Haunter",   94: "Gengar",    95: "Onix",
    96: "Drowzee",    97: "Hypno",     98: "Krabby",    99: "Kingler",  100: "Voltorb",
   101: "Electrode", 102: "Exeggcute",103: "Exeggutor",104: "Cubone",  105: "Marowak",
   106: "Hitmonlee", 107: "Hitmonchan",108:"Lickitung", 109: "Koffing", 110: "Weezing",
   111: "Rhyhorn",   112: "Rhydon",   113: "Chansey",  114: "Tangela", 115: "Kangaskhan",
   116: "Horsea",    117: "Seadra",   118: "Goldeen",  119: "Seaking", 120: "Staryu",
   121: "Starmie",   122: "Mr. Mime", 123: "Scyther",  124: "Jynx",    125: "Electabuzz",
   126: "Magmar",    127: "Pinsir",   128: "Tauros",   129: "Magikarp",130: "Gyarados",
   131: "Lapras",    132: "Ditto",    133: "Eevee",    134: "Vaporeon",135: "Jolteon",
   136: "Flareon",   137: "Porygon",  138: "Omanyte",  139: "Omastar", 140: "Kabuto",
   141: "Kabutops",  142: "Aerodactyl",143:"Snorlax",  144: "Articuno",145: "Zapdos",
   146: "Moltres",   147: "Dratini",  148: "Dragonair",149: "Dragonite",150: "Mewtwo",
   151: "Mew",
}

# Reverse: name → dex number
GEN1_DEX_BY_NAME = {v: k for k, v in GEN1_NATIONAL_DEX.items()}

# ─────────────────────────────────────────────────────────────────────────────
# Move list  (move ID → name)
# ─────────────────────────────────────────────────────────────────────────────
GEN1_MOVES = {
    0: "—",
    1: "Pound",       2: "Karate Chop",    3: "Double Slap",  4: "Comet Punch",
    5: "Mega Punch",  6: "Pay Day",        7: "Fire Punch",   8: "Ice Punch",
    9: "ThunderPunch",10: "Scratch",       11: "ViceGrip",    12: "Guillotine",
   13: "Razor Wind",  14: "Swords Dance",  15: "Cut",         16: "Gust",
   17: "Wing Attack", 18: "Whirlwind",     19: "Fly",         20: "Bind",
   21: "Slam",        22: "Vine Whip",     23: "Stomp",       24: "Double Kick",
   25: "Mega Kick",   26: "Jump Kick",     27: "Rolling Kick",28: "Sand Attack",
   29: "Headbutt",    30: "Horn Attack",   31: "Fury Attack", 32: "Horn Drill",
   33: "Tackle",      34: "Body Slam",     35: "Wrap",        36: "Take Down",
   37: "Thrash",      38: "Double-Edge",   39: "Tail Whip",   40: "Poison Sting",
   41: "Twineedle",   42: "Pin Missile",   43: "Leer",        44: "Bite",
   45: "Growl",       46: "Roar",          47: "Sing",        48: "Supersonic",
   49: "Sonic Boom",  50: "Disable",       51: "Acid",        52: "Ember",
   53: "Flamethrower",54: "Mist",          55: "Water Gun",   56: "Hydro Pump",
   57: "Surf",        58: "Ice Beam",      59: "Blizzard",    60: "Psybeam",
   61: "BubbleBeam",  62: "Aurora Beam",   63: "Hyper Beam",  64: "Peck",
   65: "Drill Peck",  66: "Submission",    67: "Low Kick",    68: "Counter",
   69: "Seismic Toss",70: "Strength",      71: "Absorb",      72: "Mega Drain",
   73: "Leech Seed",  74: "Growth",        75: "Razor Leaf",  76: "SolarBeam",
   77: "PoisonPowder",78: "Stun Spore",    79: "Sleep Powder",80: "Petal Dance",
   81: "String Shot", 82: "Dragon Rage",   83: "Fire Spin",   84: "ThunderShock",
   85: "Thunderbolt", 86: "Thunder Wave",  87: "Thunder",     88: "Rock Throw",
   89: "Earthquake",  90: "Fissure",       91: "Dig",         92: "Toxic",
   93: "Confusion",   94: "Psychic",       95: "Hypnosis",    96: "Meditate",
   97: "Agility",     98: "Quick Attack",  99: "Rage",       100: "Teleport",
  101: "Night Shade",102: "Mimic",        103: "Screech",    104: "Double Team",
  105: "Recover",    106: "Harden",       107: "Minimize",   108: "Smokescreen",
  109: "Confuse Ray",110: "Withdraw",     111: "Defense Curl",112:"Barrier",
  113: "Light Screen",114:"Haze",         115: "Reflect",    116: "Focus Energy",
  117: "Bide",       118: "Metronome",    119: "Mirror Move",120: "Self-Destruct",
  121: "Egg Bomb",   122: "Lick",         123: "Smog",       124: "Sludge",
  125: "Bone Club",  126: "Fire Blast",   127: "Waterfall",  128: "Clamp",
  129: "Swift",      130: "Skull Bash",   131: "Spike Cannon",132:"Constrict",
  133: "Amnesia",    134: "Kinesis",      135: "Soft-Boiled",136: "Hi Jump Kick",
  137: "Glare",      138: "Dream Eater",  139: "Poison Gas", 140: "Barrage",
  141: "Leech Life", 142: "Lovely Kiss",  143: "Sky Attack",  144: "Transform",
  145: "Bubble",     146: "Dizzy Punch",  147: "Spore",      148: "Flash",
  149: "Psywave",    150: "Splash",       151: "Acid Armor",  152: "Crabhammer",
  153: "Explosion",  154: "Fury Swipes",  155: "Bonemerang",  156: "Rest",
  157: "Rock Slide", 158: "Hyper Fang",   159: "Sharpen",    160: "Conversion",
  161: "Tri Attack", 162: "Super Fang",   163: "Slash",      164: "Substitute",
  165: "Struggle",
}

# ─────────────────────────────────────────────────────────────────────────────
# Move base PP  (move ID → max PP before PP Ups)
# ─────────────────────────────────────────────────────────────────────────────
GEN1_MOVE_MAX_PP = {
    0:  0,   1: 35,   2: 25,   3: 10,   4: 15,   5: 20,   6: 20,   7: 15,
    8: 15,   9: 15,  10: 35,  11: 30,  12:  5,  13: 10,  14: 30,  15: 30,
   16: 35,  17: 35,  18: 20,  19: 15,  20: 20,  21: 20,  22: 25,  23: 20,
   24: 30,  25:  5,  26: 25,  27: 15,  28: 15,  29: 15,  30: 25,  31: 20,
   32:  5,  33: 35,  34: 15,  35: 20,  36: 20,  37: 10,  38: 15,  39: 30,
   40: 35,  41: 20,  42: 20,  43: 30,  44: 25,  45: 40,  46: 20,  47: 15,
   48: 20,  49: 20,  50: 20,  51: 30,  52: 25,  53: 15,  54: 30,  55: 25,
   56:  5,  57: 15,  58: 10,  59:  5,  60: 20,  61: 20,  62: 20,  63:  5,
   64: 35,  65: 20,  66: 25,  67: 20,  68: 20,  69: 20,  70: 15,  71: 25,
   72: 10,  73: 10,  74: 40,  75: 25,  76: 10,  77: 35,  78: 30,  79: 15,
   80: 20,  81: 40,  82: 10,  83: 15,  84: 30,  85: 15,  86: 20,  87: 10,
   88: 15,  89: 10,  90:  5,  91: 10,  92: 10,  93: 25,  94: 10,  95: 20,
   96: 40,  97: 30,  98: 30,  99: 20, 100: 20, 101: 15, 102: 10, 103: 40,
  104: 15, 105: 20, 106: 30, 107: 20, 108: 20, 109: 10, 110: 40, 111: 40,
  112: 30, 113: 30, 114: 30, 115: 20, 116: 30, 117: 10, 118: 10, 119: 20,
  120:  5, 121: 10, 122: 30, 123: 20, 124: 20, 125: 20, 126:  5, 127: 15,
  128: 10, 129: 20, 130: 15, 131: 15, 132: 35, 133: 20, 134: 15, 135: 10,
  136: 20, 137: 30, 138: 15, 139: 40, 140: 15, 141: 15, 142: 10, 143:  5,
  144:  1, 145: 30, 146: 10, 147: 15, 148: 20, 149: 15, 150: 40, 151: 20,
  152: 10, 153:  5, 154: 15, 155: 10, 156: 10, 157: 10, 158: 15, 159: 30,
  160: 30, 161: 10, 162: 10, 163: 20, 164: 10, 165:  1,
}

# ─────────────────────────────────────────────────────────────────────────────
# Types  (type byte → name)
# ─────────────────────────────────────────────────────────────────────────────
GEN1_TYPES = {
    0: "Normal",   1: "Fighting", 2: "Flying",   3: "Poison",
    4: "Ground",   5: "Rock",     7: "Bug",       8: "Ghost",
   20: "Fire",    21: "Water",   22: "Grass",    23: "Electric",
   24: "Psychic", 25: "Ice",     26: "Dragon",
}

# ─────────────────────────────────────────────────────────────────────────────
# Character encoding  (Game Boy byte → Unicode character)
# Terminator 0x50 is handled in decode_string(); not stored here.
# ─────────────────────────────────────────────────────────────────────────────
GEN1_CHAR_TABLE = {
    0x80:"A", 0x81:"B", 0x82:"C", 0x83:"D", 0x84:"E", 0x85:"F", 0x86:"G", 0x87:"H",
    0x88:"I", 0x89:"J", 0x8A:"K", 0x8B:"L", 0x8C:"M", 0x8D:"N", 0x8E:"O", 0x8F:"P",
    0x90:"Q", 0x91:"R", 0x92:"S", 0x93:"T", 0x94:"U", 0x95:"V", 0x96:"W", 0x97:"X",
    0x98:"Y", 0x99:"Z",
    0xA0:"a", 0xA1:"b", 0xA2:"c", 0xA3:"d", 0xA4:"e", 0xA5:"f", 0xA6:"g", 0xA7:"h",
    0xA8:"i", 0xA9:"j", 0xAA:"k", 0xAB:"l", 0xAC:"m", 0xAD:"n", 0xAE:"o", 0xAF:"p",
    0xB0:"q", 0xB1:"r", 0xB2:"s", 0xB3:"t", 0xB4:"u", 0xB5:"v", 0xB6:"w", 0xB7:"x",
    0xB8:"y", 0xB9:"z",
    # Punctuation / symbols
    0xE0:" ",  0xE1:"♂",  0xE2:"♀",  0xF2:".",  0xEF:"'",
    0x7F:" ",  # padding space used in some names
    # Digits
    0xF6:"0",  0xF7:"1",  0xF8:"2",  0xF9:"3",  0xFA:"4",
    0xFB:"5",  0xFC:"6",  0xFD:"7",  0xFE:"8",  0xFF:"9",  # 0xFF is also used as list terminator in some contexts
}

# Reverse map for encoding strings back into save data
GEN1_CHAR_ENCODE = {v: k for k, v in GEN1_CHAR_TABLE.items() if v != " " or k == 0xE0}

# ─────────────────────────────────────────────────────────────────────────────
# Item list  (item ID → name)
# ─────────────────────────────────────────────────────────────────────────────
GEN1_ITEMS = {
    0x00: "Nothing",
    0x01: "Master Ball",    0x02: "Ultra Ball",     0x03: "Great Ball",
    0x04: "Poké Ball",      0x05: "Town Map",        0x06: "Bicycle",
    0x08: "Safari Ball",    0x09: "Pokédex",         0x0A: "Moon Stone",
    0x0B: "Antidote",       0x0C: "Burn Heal",       0x0D: "Ice Heal",
    0x0E: "Awakening",      0x0F: "Parlyz Heal",     0x10: "Full Restore",
    0x11: "Max Potion",     0x12: "Hyper Potion",    0x13: "Super Potion",
    0x14: "Potion",         0x15: "Boulder Badge",   0x16: "Cascade Badge",
    0x17: "Thunder Badge",  0x18: "Rainbow Badge",   0x19: "Soul Badge",
    0x1A: "Marsh Badge",    0x1B: "Volcano Badge",   0x1C: "Earth Badge",
    0x1D: "Escape Rope",    0x1E: "Repel",           0x1F: "Old Amber",
    0x20: "Fire Stone",     0x21: "Thunder Stone",   0x22: "Water Stone",
    0x23: "HP Up",          0x24: "Protein",         0x25: "Iron",
    0x26: "Carbos",         0x27: "Calcium",         0x28: "Rare Candy",
    0x29: "Dome Fossil",    0x2A: "Helix Fossil",    0x2B: "Secret Key",
    0x2D: "Bike Voucher",   0x2E: "X Accuracy",      0x2F: "Leaf Stone",
    0x30: "Card Key",       0x31: "Nugget",          0x32: "PP Up",
    0x33: "Poké Doll",      0x34: "Full Heal",       0x35: "Revive",
    0x36: "Max Revive",     0x37: "Guard Spec.",     0x38: "Super Repel",
    0x39: "Max Repel",      0x3A: "Dire Hit",        0x3B: "Coin",
    0x3C: "Fresh Water",    0x3D: "Soda Pop",        0x3E: "Lemonade",
    0x3F: "S.S. Ticket",    0x40: "Gold Teeth",      0x41: "X Attack",
    0x42: "X Defend",       0x43: "X Speed",         0x44: "X Special",
    0x45: "Coin Case",      0x46: "Oak's Parcel",    0x47: "Itemfinder",
    0x48: "Super Rod",      0x49: "Good Rod",        0x4A: "Old Rod",
    0x4B: "Silph Scope",    0x4C: "Poké Flute",      0x4D: "Lift Key",
    0x4E: "Exp.All",        0x4F: "Old Rod",
    0x50: "HM01 Cut",       0x51: "HM02 Fly",        0x52: "HM03 Surf",
    0x53: "HM04 Strength",  0x54: "HM05 Flash",
    0x55: "TM01",  0x56: "TM02",  0x57: "TM03",  0x58: "TM04",  0x59: "TM05",
    0x5A: "TM06",  0x5B: "TM07",  0x5C: "TM08",  0x5D: "TM09",  0x5E: "TM10",
    0x5F: "TM11",  0x60: "TM12",  0x61: "TM13",  0x62: "TM14",  0x63: "TM15",
    0x64: "TM16",  0x65: "TM17",  0x66: "TM18",  0x67: "TM19",  0x68: "TM20",
    0x69: "TM21",  0x6A: "TM22",  0x6B: "TM23",  0x6C: "TM24",  0x6D: "TM25",
    0x6E: "TM26",  0x6F: "TM27",  0x70: "TM28",  0x71: "TM29",  0x72: "TM30",
    0x73: "TM31",  0x74: "TM32",  0x75: "TM33",  0x76: "TM34",  0x77: "TM35",
    0x78: "TM36",  0x79: "TM37",  0x7A: "TM38",  0x7B: "TM39",  0x7C: "TM40",
    0x7D: "TM41",  0x7E: "TM42",  0x7F: "TM43",  0x80: "TM44",  0x81: "TM45",
    0x82: "TM46",  0x83: "TM47",  0x84: "TM48",  0x85: "TM49",  0x86: "TM50",
    0xC4: "Sacred Ash",  0xC5: "Heavy Ball",  0xC6: "Flower Mail",
    0xC8: "Level Ball",  0xD7: "Lure Ball",   0xDF: "Fast Ball",  0xFA: "Park Ball",
}

# ─────────────────────────────────────────────────────────────────────────────
# Pokémon base stats  (species name → {HP, Attack, Defense, Speed, Special})
# Gen 1 has a single Special stat shared between SpAtk and SpDef.
# ─────────────────────────────────────────────────────────────────────────────
POKEMON_BASE_STATS = {
    "Bulbasaur":   {"HP": 45, "Attack": 49, "Defense": 49, "Speed": 45, "Special": 65},
    "Ivysaur":     {"HP": 60, "Attack": 62, "Defense": 63, "Speed": 60, "Special": 80},
    "Venusaur":    {"HP": 80, "Attack": 82, "Defense": 83, "Speed": 80, "Special": 100},
    "Charmander":  {"HP": 39, "Attack": 52, "Defense": 43, "Speed": 65, "Special": 50},
    "Charmeleon":  {"HP": 58, "Attack": 64, "Defense": 58, "Speed": 80, "Special": 65},
    "Charizard":   {"HP": 78, "Attack": 84, "Defense": 78, "Speed": 100,"Special": 85},
    "Squirtle":    {"HP": 44, "Attack": 48, "Defense": 65, "Speed": 43, "Special": 50},
    "Wartortle":   {"HP": 59, "Attack": 63, "Defense": 80, "Speed": 58, "Special": 65},
    "Blastoise":   {"HP": 79, "Attack": 83, "Defense": 100,"Speed": 78, "Special": 85},
    "Caterpie":    {"HP": 45, "Attack": 30, "Defense": 35, "Speed": 45, "Special": 20},
    "Metapod":     {"HP": 50, "Attack": 20, "Defense": 55, "Speed": 30, "Special": 25},
    "Butterfree":  {"HP": 60, "Attack": 45, "Defense": 50, "Speed": 70, "Special": 80},
    "Weedle":      {"HP": 40, "Attack": 35, "Defense": 30, "Speed": 50, "Special": 20},
    "Kakuna":      {"HP": 45, "Attack": 25, "Defense": 50, "Speed": 35, "Special": 25},
    "Beedrill":    {"HP": 65, "Attack": 90, "Defense": 40, "Speed": 75, "Special": 45},
    "Pidgey":      {"HP": 40, "Attack": 45, "Defense": 40, "Speed": 56, "Special": 35},
    "Pidgeotto":   {"HP": 63, "Attack": 60, "Defense": 55, "Speed": 71, "Special": 50},
    "Pidgeot":     {"HP": 83, "Attack": 80, "Defense": 75, "Speed": 91, "Special": 70},
    "Rattata":     {"HP": 30, "Attack": 56, "Defense": 35, "Speed": 72, "Special": 25},
    "Raticate":    {"HP": 55, "Attack": 81, "Defense": 60, "Speed": 97, "Special": 50},
    "Spearow":     {"HP": 40, "Attack": 60, "Defense": 30, "Speed": 70, "Special": 31},
    "Fearow":      {"HP": 65, "Attack": 90, "Defense": 65, "Speed": 100,"Special": 61},
    "Ekans":       {"HP": 35, "Attack": 60, "Defense": 44, "Speed": 55, "Special": 40},
    "Arbok":       {"HP": 60, "Attack": 85, "Defense": 69, "Speed": 80, "Special": 65},
    "Pikachu":     {"HP": 35, "Attack": 55, "Defense": 30, "Speed": 90, "Special": 50},
    "Raichu":      {"HP": 60, "Attack": 90, "Defense": 55, "Speed": 100,"Special": 90},
    "Sandshrew":   {"HP": 50, "Attack": 75, "Defense": 85, "Speed": 40, "Special": 30},
    "Sandslash":   {"HP": 75, "Attack": 100,"Defense": 110,"Speed": 65, "Special": 55},
    "Nidoran♀":    {"HP": 55, "Attack": 47, "Defense": 52, "Speed": 41, "Special": 40},
    "Nidorina":    {"HP": 70, "Attack": 62, "Defense": 67, "Speed": 56, "Special": 55},
    "Nidoqueen":   {"HP": 90, "Attack": 92, "Defense": 87, "Speed": 76, "Special": 75},
    "Nidoran♂":    {"HP": 46, "Attack": 57, "Defense": 40, "Speed": 50, "Special": 40},
    "Nidorino":    {"HP": 61, "Attack": 72, "Defense": 57, "Speed": 65, "Special": 55},
    "Nidoking":    {"HP": 81, "Attack": 102,"Defense": 77, "Speed": 85, "Special": 85},
    "Clefairy":    {"HP": 70, "Attack": 45, "Defense": 48, "Speed": 35, "Special": 60},
    "Clefable":    {"HP": 95, "Attack": 70, "Defense": 73, "Speed": 60, "Special": 85},
    "Vulpix":      {"HP": 38, "Attack": 41, "Defense": 40, "Speed": 65, "Special": 65},
    "Ninetales":   {"HP": 73, "Attack": 76, "Defense": 75, "Speed": 100,"Special": 100},
    "Jigglypuff":  {"HP":115, "Attack": 45, "Defense": 20, "Speed": 20, "Special": 25},
    "Wigglytuff":  {"HP":140, "Attack": 70, "Defense": 45, "Speed": 45, "Special": 50},
    "Zubat":       {"HP": 40, "Attack": 45, "Defense": 35, "Speed": 55, "Special": 40},
    "Golbat":      {"HP": 75, "Attack": 80, "Defense": 70, "Speed": 90, "Special": 75},
    "Oddish":      {"HP": 45, "Attack": 50, "Defense": 55, "Speed": 30, "Special": 75},
    "Gloom":       {"HP": 60, "Attack": 65, "Defense": 70, "Speed": 40, "Special": 85},
    "Vileplume":   {"HP": 75, "Attack": 80, "Defense": 85, "Speed": 50, "Special": 100},
    "Paras":       {"HP": 35, "Attack": 70, "Defense": 55, "Speed": 25, "Special": 55},
    "Parasect":    {"HP": 60, "Attack": 95, "Defense": 80, "Speed": 30, "Special": 80},
    "Venonat":     {"HP": 60, "Attack": 55, "Defense": 50, "Speed": 45, "Special": 40},
    "Venomoth":    {"HP": 70, "Attack": 65, "Defense": 60, "Speed": 90, "Special": 90},
    "Diglett":     {"HP": 10, "Attack": 55, "Defense": 25, "Speed": 95, "Special": 35},
    "Dugtrio":     {"HP": 35, "Attack": 80, "Defense": 50, "Speed": 120,"Special": 70},
    "Meowth":      {"HP": 40, "Attack": 45, "Defense": 35, "Speed": 90, "Special": 40},
    "Persian":     {"HP": 65, "Attack": 70, "Defense": 60, "Speed": 115,"Special": 65},
    "Psyduck":     {"HP": 50, "Attack": 52, "Defense": 48, "Speed": 55, "Special": 50},
    "Golduck":     {"HP": 80, "Attack": 82, "Defense": 78, "Speed": 85, "Special": 80},
    "Mankey":      {"HP": 40, "Attack": 80, "Defense": 35, "Speed": 70, "Special": 35},
    "Primeape":    {"HP": 65, "Attack": 105,"Defense": 60, "Speed": 95, "Special": 60},
    "Growlithe":   {"HP": 55, "Attack": 70, "Defense": 45, "Speed": 60, "Special": 50},
    "Arcanine":    {"HP": 90, "Attack": 110,"Defense": 80, "Speed": 95, "Special": 80},
    "Poliwag":     {"HP": 40, "Attack": 50, "Defense": 40, "Speed": 90, "Special": 40},
    "Poliwhirl":   {"HP": 65, "Attack": 65, "Defense": 65, "Speed": 90, "Special": 50},
    "Poliwrath":   {"HP": 90, "Attack": 85, "Defense": 95, "Speed": 70, "Special": 70},
    "Abra":        {"HP": 25, "Attack": 20, "Defense": 15, "Speed": 90, "Special": 105},
    "Kadabra":     {"HP": 40, "Attack": 35, "Defense": 30, "Speed": 105,"Special": 120},
    "Alakazam":    {"HP": 55, "Attack": 50, "Defense": 45, "Speed": 120,"Special": 135},
    "Machop":      {"HP": 70, "Attack": 80, "Defense": 50, "Speed": 35, "Special": 35},
    "Machoke":     {"HP": 80, "Attack": 100,"Defense": 70, "Speed": 45, "Special": 50},
    "Machamp":     {"HP": 90, "Attack": 130,"Defense": 80, "Speed": 55, "Special": 65},
    "Bellsprout":  {"HP": 50, "Attack": 75, "Defense": 35, "Speed": 40, "Special": 70},
    "Weepinbell":  {"HP": 65, "Attack": 90, "Defense": 50, "Speed": 55, "Special": 85},
    "Victreebel":  {"HP": 80, "Attack": 105,"Defense": 65, "Speed": 70, "Special": 100},
    "Tentacool":   {"HP": 40, "Attack": 40, "Defense": 35, "Speed": 70, "Special": 100},
    "Tentacruel":  {"HP": 80, "Attack": 70, "Defense": 65, "Speed": 100,"Special": 120},
    "Geodude":     {"HP": 40, "Attack": 80, "Defense": 100,"Speed": 20, "Special": 30},
    "Graveler":    {"HP": 55, "Attack": 95, "Defense": 115,"Speed": 35, "Special": 45},
    "Golem":       {"HP": 80, "Attack": 110,"Defense": 130,"Speed": 45, "Special": 55},
    "Ponyta":      {"HP": 50, "Attack": 85, "Defense": 55, "Speed": 90, "Special": 65},
    "Rapidash":    {"HP": 65, "Attack": 100,"Defense": 70, "Speed": 105,"Special": 80},
    "Slowpoke":    {"HP": 90, "Attack": 65, "Defense": 65, "Speed": 15, "Special": 40},
    "Slowbro":     {"HP": 95, "Attack": 75, "Defense": 110,"Speed": 30, "Special": 80},
    "Magnemite":   {"HP": 25, "Attack": 35, "Defense": 70, "Speed": 45, "Special": 95},
    "Magneton":    {"HP": 50, "Attack": 60, "Defense": 95, "Speed": 70, "Special": 120},
    "Farfetch'd":  {"HP": 52, "Attack": 65, "Defense": 55, "Speed": 60, "Special": 58},
    "Doduo":       {"HP": 35, "Attack": 85, "Defense": 45, "Speed": 75, "Special": 35},
    "Dodrio":      {"HP": 60, "Attack": 110,"Defense": 70, "Speed": 100,"Special": 60},
    "Seel":        {"HP": 65, "Attack": 45, "Defense": 55, "Speed": 45, "Special": 70},
    "Dewgong":     {"HP": 90, "Attack": 70, "Defense": 80, "Speed": 70, "Special": 95},
    "Grimer":      {"HP": 80, "Attack": 80, "Defense": 50, "Speed": 25, "Special": 40},
    "Muk":         {"HP": 105,"Attack": 105,"Defense": 75, "Speed": 50, "Special": 65},
    "Shellder":    {"HP": 30, "Attack": 65, "Defense": 100,"Speed": 40, "Special": 45},
    "Cloyster":    {"HP": 50, "Attack": 95, "Defense": 180,"Speed": 70, "Special": 70},
    "Gastly":      {"HP": 30, "Attack": 35, "Defense": 30, "Speed": 80, "Special": 100},
    "Haunter":     {"HP": 45, "Attack": 50, "Defense": 45, "Speed": 95, "Special": 115},
    "Gengar":      {"HP": 60, "Attack": 65, "Defense": 60, "Speed": 110,"Special": 130},
    "Onix":        {"HP": 35, "Attack": 45, "Defense": 160,"Speed": 70, "Special": 30},
    "Drowzee":     {"HP": 60, "Attack": 48, "Defense": 45, "Speed": 42, "Special": 90},
    "Hypno":       {"HP": 85, "Attack": 73, "Defense": 70, "Speed": 67, "Special": 115},
    "Krabby":      {"HP": 30, "Attack": 105,"Defense": 90, "Speed": 50, "Special": 25},
    "Kingler":     {"HP": 55, "Attack": 130,"Defense": 115,"Speed": 75, "Special": 50},
    "Voltorb":     {"HP": 40, "Attack": 30, "Defense": 50, "Speed": 100,"Special": 55},
    "Electrode":   {"HP": 60, "Attack": 50, "Defense": 70, "Speed": 150,"Special": 80},
    "Exeggcute":   {"HP": 60, "Attack": 40, "Defense": 80, "Speed": 40, "Special": 60},
    "Exeggutor":   {"HP": 95, "Attack": 95, "Defense": 85, "Speed": 55, "Special": 125},
    "Cubone":      {"HP": 50, "Attack": 50, "Defense": 95, "Speed": 35, "Special": 40},
    "Marowak":     {"HP": 60, "Attack": 80, "Defense": 110,"Speed": 45, "Special": 50},
    "Hitmonlee":   {"HP": 50, "Attack": 120,"Defense": 53, "Speed": 87, "Special": 35},
    "Hitmonchan":  {"HP": 50, "Attack": 105,"Defense": 79, "Speed": 76, "Special": 35},
    "Lickitung":   {"HP": 90, "Attack": 55, "Defense": 75, "Speed": 30, "Special": 60},
    "Koffing":     {"HP": 40, "Attack": 65, "Defense": 95, "Speed": 35, "Special": 60},
    "Weezing":     {"HP": 65, "Attack": 90, "Defense": 120,"Speed": 60, "Special": 85},
    "Rhyhorn":     {"HP": 80, "Attack": 85, "Defense": 95, "Speed": 25, "Special": 30},
    "Rhydon":      {"HP": 105,"Attack": 130,"Defense": 120,"Speed": 40, "Special": 45},
    "Chansey":     {"HP": 250,"Attack": 5,  "Defense": 5,  "Speed": 50, "Special": 105},
    "Tangela":     {"HP": 65, "Attack": 55, "Defense": 115,"Speed": 60, "Special": 100},
    "Kangaskhan":  {"HP": 105,"Attack": 95, "Defense": 80, "Speed": 90, "Special": 40},
    "Horsea":      {"HP": 30, "Attack": 40, "Defense": 70, "Speed": 60, "Special": 70},
    "Seadra":      {"HP": 55, "Attack": 65, "Defense": 95, "Speed": 85, "Special": 95},
    "Goldeen":     {"HP": 45, "Attack": 67, "Defense": 60, "Speed": 63, "Special": 50},
    "Seaking":     {"HP": 80, "Attack": 92, "Defense": 65, "Speed": 68, "Special": 80},
    "Staryu":      {"HP": 30, "Attack": 45, "Defense": 55, "Speed": 85, "Special": 70},
    "Starmie":     {"HP": 60, "Attack": 75, "Defense": 85, "Speed": 115,"Special": 100},
    "Mr. Mime":    {"HP": 40, "Attack": 45, "Defense": 65, "Speed": 90, "Special": 100},
    "Scyther":     {"HP": 70, "Attack": 110,"Defense": 80, "Speed": 105,"Special": 55},
    "Jynx":        {"HP": 65, "Attack": 50, "Defense": 35, "Speed": 95, "Special": 95},
    "Electabuzz":  {"HP": 65, "Attack": 83, "Defense": 57, "Speed": 105,"Special": 85},
    "Magmar":      {"HP": 65, "Attack": 95, "Defense": 57, "Speed": 93, "Special": 85},
    "Pinsir":      {"HP": 65, "Attack": 125,"Defense": 100,"Speed": 85, "Special": 55},
    "Tauros":      {"HP": 75, "Attack": 100,"Defense": 95, "Speed": 110,"Special": 70},
    "Magikarp":    {"HP": 20, "Attack": 10, "Defense": 55, "Speed": 80, "Special": 20},
    "Gyarados":    {"HP": 95, "Attack": 125,"Defense": 79, "Speed": 81, "Special": 100},
    "Lapras":      {"HP": 130,"Attack": 85, "Defense": 80, "Speed": 60, "Special": 95},
    "Ditto":       {"HP": 48, "Attack": 48, "Defense": 48, "Speed": 48, "Special": 48},
    "Eevee":       {"HP": 55, "Attack": 55, "Defense": 50, "Speed": 55, "Special": 65},
    "Vaporeon":    {"HP": 130,"Attack": 65, "Defense": 60, "Speed": 65, "Special": 110},
    "Jolteon":     {"HP": 65, "Attack": 65, "Defense": 60, "Speed": 130,"Special": 110},
    "Flareon":     {"HP": 65, "Attack": 130,"Defense": 60, "Speed": 65, "Special": 95},
    "Porygon":     {"HP": 65, "Attack": 60, "Defense": 70, "Speed": 40, "Special": 75},
    "Omanyte":     {"HP": 35, "Attack": 40, "Defense": 100,"Speed": 35, "Special": 90},
    "Omastar":     {"HP": 70, "Attack": 60, "Defense": 125,"Speed": 55, "Special": 115},
    "Kabuto":      {"HP": 30, "Attack": 80, "Defense": 90, "Speed": 55, "Special": 45},
    "Kabutops":    {"HP": 60, "Attack": 115,"Defense": 105,"Speed": 80, "Special": 70},
    "Aerodactyl":  {"HP": 80, "Attack": 105,"Defense": 65, "Speed": 130,"Special": 60},
    "Snorlax":     {"HP": 160,"Attack": 110,"Defense": 65, "Speed": 30, "Special": 65},
    "Articuno":    {"HP": 90, "Attack": 85, "Defense": 100,"Speed": 85, "Special": 125},
    "Zapdos":      {"HP": 90, "Attack": 90, "Defense": 85, "Speed": 100,"Special": 125},
    "Moltres":     {"HP": 90, "Attack": 100,"Defense": 90, "Speed": 90, "Special": 125},
    "Dratini":     {"HP": 41, "Attack": 64, "Defense": 45, "Speed": 50, "Special": 50},
    "Dragonair":   {"HP": 61, "Attack": 84, "Defense": 65, "Speed": 70, "Special": 70},
    "Dragonite":   {"HP": 91, "Attack": 134,"Defense": 95, "Speed": 80, "Special": 100},
    "Mewtwo":      {"HP": 106,"Attack": 110,"Defense": 90, "Speed": 130,"Special": 154},
    "Mew":         {"HP": 100,"Attack": 100,"Defense": 100,"Speed": 100,"Special": 100},
}

# ─────────────────────────────────────────────────────────────────────────────
# Pokémon struct layout  (44-byte party block)
#
# CRITICAL: Mixed endianness!
#   - Box data (0x00-0x1F): BIG-ENDIAN (HP, OT ID, EXP, EVs, DVs)
#   - Party stats (0x21-0x2A): LITTLE-ENDIAN (max HP, attack, defense, speed, special)
#
# The first 28 bytes (0x00–0x1B) are the "box" subset, used when Pokémon are
# in a PC box (33-byte box block, which adds 5 bytes of PP data at 0x1C-0x20).
# The remaining 16 bytes (0x20–0x2B) are the party-only extension.
# ─────────────────────────────────────────────────────────────────────────────
GEN1_POKEMON_STRUCT = {
    # ── Box block (offsets 0x00–0x1B) ──────────────────────────────────────
    "species":     (0x00, 1),   # Internal species ID
    "current_hp":  (0x01, 2),   # Current HP (big-endian)
    "status":      (0x03, 1),   # Status condition byte
    "type1":       (0x04, 1),   # Primary type
    "type2":       (0x05, 1),   # Secondary type
    "catch_rate":  (0x06, 1),   # Base catch rate (also held-item slot in Yellow)
    "move1":       (0x08, 1),   # Move 1 index (CORRECTED from 0x07)
    "move2":       (0x09, 1),   # Move 2 index (CORRECTED from 0x08)
    "move3":       (0x0A, 1),   # Move 3 index (CORRECTED from 0x09)
    "move4":       (0x0B, 1),   # Move 4 index (CORRECTED from 0x0A)
    "ot_id":       (0x0C, 2),   # Original Trainer ID (big-endian, CORRECTED from 0x0B)
    "exp":         (0x0E, 3),   # Experience points (big-endian, CORRECTED from 0x0D)
    "hp_ev":       (0x11, 2),   # HP Effort Value (big-endian, CORRECTED from 0x10)
    "atk_ev":      (0x13, 2),   # Attack EV (CORRECTED from 0x12)
    "def_ev":      (0x15, 2),   # Defense EV (CORRECTED from 0x14)
    "spd_ev":      (0x17, 2),   # Speed EV (CORRECTED from 0x16)
    "spc_ev":      (0x19, 2),   # Special EV (CORRECTED from 0x18)
    "dvs":         (0x1B, 2),   # DV word: [15:12]=Atk [11:8]=Def [7:4]=Spd [3:0]=Spc (CORRECTED from 0x1A)
    #                             HP DV is derived: bit0 of Atk/Def/Spd/Spc DVs
    # ── Box block continuation: PP (0x1D–0x20) ─────────────────────────────
    "pp1":         (0x1D, 1),   # bits[7:6] = PP Ups applied, bits[5:0] = current PP (CORRECTED from 0x1C)
    "pp2":         (0x1E, 1),   # (CORRECTED from 0x1D)
    "pp3":         (0x1F, 1),   # (CORRECTED from 0x1E)
    "pp4":         (0x20, 1),   # (CORRECTED from 0x1F)
    # ── Party-only extension (0x20–0x2B) ───────────────────────────────────
    "level":       (0x21, 1),   # Level (party copy; +1 from documented offset)
    "max_hp":      (0x22, 2),   # Max HP stat (big-endian)
    "attack":      (0x24, 2),   # Attack stat
    "defense":     (0x26, 2),   # Defense stat
    "speed":       (0x28, 2),   # Speed stat
    "special":     (0x2A, 2),   # Special stat
}

# ─────────────────────────────────────────────────────────────────────────────
# EXP Curves (level 1-100 EXP requirements for each growth rate)
# ─────────────────────────────────────────────────────────────────────────────
GEN1_EXP_CURVES = {
    "fast": [0, 6, 21, 51, 100, 172, 274, 409, 583, 800, 1064, 1382, 1757, 2195, 2700, 3276, 3930, 4665, 5487, 6400, 7408, 8518, 9733, 11059, 12500, 14060, 15746, 17561, 19511, 21600, 23832, 26214, 28749, 31443, 34300, 37324, 40522, 43897, 47455, 51200, 55136, 59270, 63605, 68147, 72900, 77868, 83058, 88473, 94119, 100000, 106120, 112486, 119101, 125971, 133100, 140492, 148154, 156089, 164303, 172800, 181584, 190662, 200037, 209715, 219700, 229996, 240610, 251545, 262807, 274400, 286328, 298598, 311213, 324179, 337500, 351180, 365226, 379641, 394431, 409600, 425152, 441094, 457429, 474163, 491300, 508844, 526802, 545177, 563975, 583200, 602856, 622950, 643485, 664467, 685900, 707788, 730138, 752953, 776239, 800000],
    "medium_fast": [1, 8, 27, 64, 125, 216, 343, 512, 729, 1000, 1331, 1728, 2197, 2744, 3375, 4096, 4913, 5832, 6859, 8000, 9261, 10648, 12167, 13824, 15625, 17576, 19683, 21952, 24389, 27000, 29791, 32768, 35937, 39304, 42875, 46656, 50653, 54872, 59319, 64000, 68921, 74088, 79507, 85184, 91125, 97336, 103823, 110592, 117649, 125000, 132651, 140608, 148877, 157464, 166375, 175616, 185193, 195112, 205379, 216000, 226981, 238328, 250047, 262144, 274625, 287496, 300763, 314432, 328509, 343000, 357911, 373248, 389017, 405224, 421875, 438976, 456533, 474552, 493039, 512000, 531441, 551368, 571787, 592704, 614125, 636056, 658503, 681472, 704969, 729000, 753571, 778688, 804357, 830584, 857375, 884736, 912673, 941192, 970299, 1000000],
    "medium_slow": [-53, 9, 57, 96, 135, 179, 236, 314, 419, 560, 742, 973, 1261, 1612, 2035, 2535, 3120, 3798, 4575, 5460, 6458, 7577, 8825, 10208, 11735, 13411, 15244, 17242, 19411, 21760, 24294, 27021, 29949, 33084, 36435, 40007, 43808, 47846, 52127, 56660, 61450, 66505, 71833, 77440, 83335, 89523, 96012, 102810, 109923, 117360, 125126, 133229, 141677, 150476, 159635, 169159, 179056, 189334, 199999, 211060, 222522, 234393, 246681, 259392, 272535, 286115, 300140, 314618, 329555, 344960, 360838, 377197, 394045, 411388, 429235, 447591, 466464, 485862, 505791, 526260, 547274, 568841, 590969, 613664, 636935, 660787, 685228, 710266, 735907, 762160, 789030, 816525, 844653, 873420, 902835, 932903, 963632, 995030, 1027103, 1059860],
    "slow": [1, 10, 33, 80, 156, 270, 428, 640, 911, 1250, 1663, 2160, 2746, 3430, 4218, 5120, 6141, 7290, 8573, 10000, 11576, 13310, 15208, 17280, 19531, 21970, 24603, 27440, 30486, 33750, 37238, 40960, 44921, 49130, 53593, 58320, 63316, 68590, 74148, 80000, 86151, 92610, 99383, 106480, 113906, 121670, 129778, 138240, 147061, 156250, 165813, 175760, 186096, 196830, 207968, 219520, 231491, 243890, 256723, 270000, 283726, 297910, 312558, 327680, 343281, 359370, 375953, 393040, 410636, 428750, 447388, 466560, 486271, 506530, 527343, 548720, 570666, 593190, 616298, 640000, 664301, 689210, 714733, 740880, 767656, 795070, 823128, 851840, 881211, 911250, 941963, 973360, 1005446, 1038230, 1071718, 1105920, 1140841, 1176490, 1212873, 1250000],
}

# ─────────────────────────────────────────────────────────────────────────────
# Save-file layout  (Red/Blue — 32 KiB, no SRAM bank switching)
# ─────────────────────────────────────────────────────────────────────────────
GEN1_SAVE_OFFSETS = {
    # Trainer info
    "player_name":   (0x2598, 11),  # 11-byte, 0x50-terminated
    "pokedex_owned": (0x25A3, 19),  # 19 bytes × 8 bits = 152 flags (dex #1 = bit 0 of byte 0)
    "pokedex_seen":  (0x25B6, 19),
    "bag_count":     (0x25C9,  1),  # Number of items in bag
    "bag_items":     (0x25CA, 40),  # Up to 20 × (item_id, quantity) pairs, terminated by 0xFF
    "money":         (0x25F3,  3),  # BCD-encoded (e.g. 0x01 0x23 0x45 = ₽12345)
    "rival_name":    (0x25F6, 11),
    "badges":        (0x2602,  1),  # Bit flags, bit 0 = Boulder Badge
    "trainer_id":    (0x2605,  2),  # Big-endian
    "playtime_h":    (0x2CED,  1),  # Hours
    "playtime_m":    (0x2CEE,  1),  # Minutes
    "playtime_s":    (0x2CEF,  1),  # Seconds
    "playtime_f":    (0x2CF0,  1),  # Frames (not normally displayed)
    # Party
    "party_count":   (0x2F2C,  1),
    "party_species": (0x2F2D,  7),  # Species list + 0xFF terminator
    "party_data":    (0x2F34,264),  # 6 × 44 bytes
    "party_ot":      (0x303C, 66),  # 6 × 11 bytes
    "party_names":   (0x307E, 66),  # 6 × 11 bytes (CORRECTED from 0x3086)
    # PC Boxes (all 12 stored in .sav file)
    "current_box":   (0x284C,  1),  # Which box is active (0-11)
}

# Box storage: Each box = 1 (count) + 21 (species) + 660 (data) + 220 (OT) + 220 (names) = 1122 bytes
GEN1_BOX_SIZE = 1122

# Boxes 1-6 (Bank 2, offset 0x4000)
GEN1_BOXES_BANK2_START = 0x4000
# Boxes 7-12 (Bank 3, offset 0x6000)
GEN1_BOXES_BANK3_START = 0x6000

def get_box_offset(box_number: int) -> int:
    """Get the offset for a box (1-12)."""
    if not 1 <= box_number <= 12:
        raise ValueError(f"Box number must be 1-12, got {box_number}")
    
    if box_number <= 6:
        # Boxes 1-6 in Bank 2
        return GEN1_BOXES_BANK2_START + (box_number - 1) * GEN1_BOX_SIZE
    else:
        # Boxes 7-12 in Bank 3
        return GEN1_BOXES_BANK3_START + (box_number - 7) * GEN1_BOX_SIZE

GEN1_SPECIES_GROWTH = {
    "Bulbasaur": "medium_slow",
    "Ivysaur": "medium_slow",
    "Venusaur": "medium_slow",

    "Charmander": "medium_slow",
    "Charmeleon": "medium_slow",
    "Charizard": "medium_slow",

    "Squirtle": "medium_slow",
    "Wartortle": "medium_slow",
    "Blastoise": "medium_slow",

    "Caterpie": "medium_fast",
    "Metapod": "medium_fast",
    "Butterfree": "medium_fast",

    "Weedle": "medium_fast",
    "Kakuna": "medium_fast",
    "Beedrill": "medium_fast",

    "Pidgey": "medium_slow",
    "Pidgeotto": "medium_slow",
    "Pidgeot": "medium_slow",

    "Rattata": "medium_fast",
    "Raticate": "medium_fast",

    "Spearow": "medium_fast",
    "Fearow": "medium_fast",

    "Ekans": "medium_fast",
    "Arbok": "medium_fast",

    "Pikachu": "medium_fast",
    "Raichu": "medium_fast",

    "Sandshrew": "medium_fast",
    "Sandslash": "medium_fast",

    "Nidoran♀": "medium_slow",
    "Nidorina": "medium_slow",
    "Nidoqueen": "medium_slow",

    "Nidoran♂": "medium_slow",
    "Nidorino": "medium_slow",
    "Nidoking": "medium_slow",

    "Clefairy": "fast",
    "Clefable": "fast",

    "Vulpix": "medium_fast",
    "Ninetales": "medium_fast",

    "Jigglypuff": "fast",
    "Wigglytuff": "fast",

    "Zubat": "medium_fast",
    "Golbat": "medium_fast",

    "Oddish": "medium_slow",
    "Gloom": "medium_slow",
    "Vileplume": "medium_slow",

    "Paras": "medium_fast",
    "Parasect": "medium_fast",

    "Venonat": "medium_fast",
    "Venomoth": "medium_fast",

    "Diglett": "medium_fast",
    "Dugtrio": "medium_fast",

    "Meowth": "medium_fast",
    "Persian": "medium_fast",

    "Psyduck": "medium_fast",
    "Golduck": "medium_fast",

    "Mankey": "medium_fast",
    "Primeape": "medium_fast",

    "Growlithe": "slow",
    "Arcanine": "slow",

    "Poliwag": "medium_slow",
    "Poliwhirl": "medium_slow",
    "Poliwrath": "medium_slow",

    "Abra": "medium_slow",
    "Kadabra": "medium_slow",
    "Alakazam": "medium_slow",

    "Machop": "medium_slow",
    "Machoke": "medium_slow",
    "Machamp": "medium_slow",

    "Bellsprout": "medium_slow",
    "Weepinbell": "medium_slow",
    "Victreebel": "medium_slow",

    "Tentacool": "slow",
    "Tentacruel": "slow",

    "Geodude": "medium_slow",
    "Graveler": "medium_slow",
    "Golem": "medium_slow",

    "Ponyta": "medium_fast",
    "Rapidash": "medium_fast",

    "Slowpoke": "medium_fast",
    "Slowbro": "medium_fast",

    "Magnemite": "medium_fast",
    "Magneton": "medium_fast",

    "Farfetch'd": "medium_fast",

    "Doduo": "medium_fast",
    "Dodrio": "medium_fast",

    "Seel": "medium_fast",
    "Dewgong": "medium_fast",

    "Grimer": "medium_fast",
    "Muk": "medium_fast",

    "Shellder": "slow",
    "Cloyster": "slow",

    "Gastly": "medium_slow",
    "Haunter": "medium_slow",
    "Gengar": "medium_slow",

    "Onix": "medium_fast",

    "Drowzee": "medium_fast",
    "Hypno": "medium_fast",

    "Krabby": "medium_fast",
    "Kingler": "medium_fast",

    "Voltorb": "medium_fast",
    "Electrode": "medium_fast",

    "Exeggcute": "slow",
    "Exeggutor": "slow",

    "Cubone": "medium_fast",
    "Marowak": "medium_fast",

    "Hitmonlee": "medium_fast",
    "Hitmonchan": "medium_fast",

    "Lickitung": "medium_fast",

    "Koffing": "medium_fast",
    "Weezing": "medium_fast",

    "Rhyhorn": "slow",
    "Rhydon": "slow",

    "Chansey": "fast",

    "Tangela": "medium_fast",

    "Kangaskhan": "medium_fast",

    "Horsea": "medium_fast",
    "Seadra": "medium_fast",

    "Goldeen": "medium_fast",
    "Seaking": "medium_fast",

    "Staryu": "slow",
    "Starmie": "slow",

    "Mr. Mime": "medium_fast",

    "Scyther": "medium_fast",

    "Jynx": "medium_fast",

    "Electabuzz": "medium_fast",

    "Magmar": "medium_fast",

    "Pinsir": "slow",

    "Tauros": "slow",

    "Magikarp": "slow",
    "Gyarados": "slow",

    "Lapras": "slow",

    "Ditto": "medium_fast",

    "Eevee": "medium_fast",
    "Vaporeon": "medium_fast",
    "Jolteon": "medium_fast",
    "Flareon": "medium_fast",

    "Porygon": "medium_fast",

    "Omanyte": "medium_fast",
    "Omastar": "medium_fast",

    "Kabuto": "medium_fast",
    "Kabutops": "medium_fast",

    "Aerodactyl": "slow",

    "Snorlax": "slow",

    "Articuno": "slow",
    "Zapdos": "slow",
    "Moltres": "slow",

    "Dratini": "slow",
    "Dragonair": "slow",
    "Dragonite": "slow",

    "Mewtwo": "slow",

    "Mew": "medium_slow",
}

BADGE_NAMES = [
    "Boulder", "Cascade", "Thunder", "Rainbow",
    "Soul",    "Marsh",   "Volcano", "Earth",
]