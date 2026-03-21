"""
Pokemon Gen 2 (Gold/Silver/Crystal) Save File Data Tables

This module contains all the data tables and constants needed to parse Gen 2 saves.
Reuses some Gen 1 tables where applicable (character encoding, base types, etc.)
"""

# ═════════════════════════════════════════════════════════════════════════════
# CHARACTER ENCODING
# ═════════════════════════════════════════════════════════════════════════════

# Gen 2 uses same character encoding as Gen 1
GEN2_CHAR_TABLE = {
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
    0x7F:" ",  # padding space
    # Digits
    0xF6:"0",  0xF7:"1",  0xF8:"2",  0xF9:"3",  0xFA:"4",
    0xFB:"5",  0xFC:"6",  0xFD:"7",  0xFE:"8",  0xFF:"9",
}

# ═════════════════════════════════════════════════════════════════════════════
# TYPE TABLE
# ═════════════════════════════════════════════════════════════════════════════

# Base type table (Gen 1 types 0x00-0x09, 0x14-0x1B)
# Gen 2 adds Dark (0x11) and Steel (0x12)
GEN2_TYPES = {
    0x00: "Normal",   0x01: "Fighting", 0x02: "Flying",   0x03: "Poison",
    0x04: "Ground",   0x05: "Rock",     0x07: "Bug",      0x08: "Ghost",
    0x14: "Fire",     0x15: "Water",    0x16: "Grass",    0x17: "Electric",
    0x18: "Psychic",  0x19: "Ice",      0x1A: "Dragon",   
    0x11: "Dark",     0x12: "Steel",    # New in Gen 2
}

# ═════════════════════════════════════════════════════════════════════════════
# GEN 2 SPECIES (Internal Index)
# ═════════════════════════════════════════════════════════════════════════════

# Gen 2 internal species index (0x01-0xFB for 251 Pokemon)
# Based on: https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_index_number_(Generation_II)

GEN2_INTERNAL_SPECIES = {
    # Gen 1 Pokemon (mostly same as Gen 1, some reordered)
    0x01: "Bulbasaur",   0x02: "Ivysaur",     0x03: "Venusaur",    0x04: "Charmander",
    0x05: "Charmeleon",  0x06: "Charizard",   0x07: "Squirtle",    0x08: "Wartortle",
    0x09: "Blastoise",   0x0A: "Caterpie",    0x0B: "Metapod",     0x0C: "Butterfree",
    0x0D: "Weedle",      0x0E: "Kakuna",      0x0F: "Beedrill",    0x10: "Pidgey",
    0x11: "Pidgeotto",   0x12: "Pidgeot",     0x13: "Rattata",     0x14: "Raticate",
    0x15: "Spearow",     0x16: "Fearow",      0x17: "Ekans",       0x18: "Arbok",
    0x19: "Pikachu",     0x1A: "Raichu",      0x1B: "Sandshrew",   0x1C: "Sandslash",
    0x1D: "Nidoran♀",    0x1E: "Nidorina",    0x1F: "Nidoqueen",   0x20: "Nidoran♂",
    0x21: "Nidorino",    0x22: "Nidoking",    0x23: "Clefairy",    0x24: "Clefable",
    0x25: "Vulpix",      0x26: "Ninetales",   0x27: "Jigglypuff",  0x28: "Wigglytuff",
    0x29: "Zubat",       0x2A: "Golbat",      0x2B: "Oddish",      0x2C: "Gloom",
    0x2D: "Vileplume",   0x2E: "Paras",       0x2F: "Parasect",    0x30: "Venonat",
    0x31: "Venomoth",    0x32: "Diglett",     0x33: "Dugtrio",     0x34: "Meowth",
    0x35: "Persian",     0x36: "Psyduck",     0x37: "Golduck",     0x38: "Mankey",
    0x39: "Primeape",    0x3A: "Growlithe",   0x3B: "Arcanine",    0x3C: "Poliwag",
    0x3D: "Poliwhirl",   0x3E: "Poliwrath",   0x3F: "Abra",        0x40: "Kadabra",
    0x41: "Alakazam",    0x42: "Machop",      0x43: "Machoke",     0x44: "Machamp",
    0x45: "Bellsprout",  0x46: "Weepinbell",  0x47: "Victreebel",  0x48: "Tentacool",
    0x49: "Tentacruel",  0x4A: "Geodude",     0x4B: "Graveler",    0x4C: "Golem",
    0x4D: "Ponyta",      0x4E: "Rapidash",    0x4F: "Slowpoke",    0x50: "Slowbro",
    0x51: "Magnemite",   0x52: "Magneton",    0x53: "Farfetch'd",  0x54: "Doduo",
    0x55: "Dodrio",      0x56: "Seel",        0x57: "Dewgong",     0x58: "Grimer",
    0x59: "Muk",         0x5A: "Shellder",    0x5B: "Cloyster",    0x5C: "Gastly",
    0x5D: "Haunter",     0x5E: "Gengar",      0x5F: "Onix",        0x60: "Drowzee",
    0x61: "Hypno",       0x62: "Krabby",      0x63: "Kingler",     0x64: "Voltorb",
    0x65: "Electrode",   0x66: "Exeggcute",   0x67: "Exeggutor",   0x68: "Cubone",
    0x69: "Marowak",     0x6A: "Hitmonlee",   0x6B: "Hitmonchan",  0x6C: "Lickitung",
    0x6D: "Koffing",     0x6E: "Weezing",     0x6F: "Rhyhorn",     0x70: "Rhydon",
    0x71: "Chansey",     0x72: "Tangela",     0x73: "Kangaskhan",  0x74: "Horsea",
    0x75: "Seadra",      0x76: "Goldeen",     0x77: "Seaking",     0x78: "Staryu",
    0x79: "Starmie",     0x7A: "Mr. Mime",    0x7B: "Scyther",     0x7C: "Jynx",
    0x7D: "Electabuzz",  0x7E: "Magmar",      0x7F: "Pinsir",      0x80: "Tauros",
    0x81: "Magikarp",    0x82: "Gyarados",    0x83: "Lapras",      0x84: "Ditto",
    0x85: "Eevee",       0x86: "Vaporeon",    0x87: "Jolteon",     0x88: "Flareon",
    0x89: "Porygon",     0x8A: "Omanyte",     0x8B: "Omastar",     0x8C: "Kabuto",
    0x8D: "Kabutops",    0x8E: "Aerodactyl",  0x8F: "Snorlax",     0x90: "Articuno",
    0x91: "Zapdos",      0x92: "Moltres",     0x93: "Dratini",     0x94: "Dragonair",
    0x95: "Dragonite",   0x96: "Mewtwo",      0x97: "Mew",
    
    # Gen 2 Pokemon (Johto - National Dex #152-251)
    0x98: "Chikorita",   0x99: "Bayleef",     0x9A: "Meganium",    0x9B: "Cyndaquil",
    0x9C: "Quilava",     0x9D: "Typhlosion",  0x9E: "Totodile",    0x9F: "Croconaw",
    0xA0: "Feraligatr",  0xA1: "Sentret",     0xA2: "Furret",      0xA3: "Hoothoot",
    0xA4: "Noctowl",     0xA5: "Ledyba",      0xA6: "Ledian",      0xA7: "Spinarak",
    0xA8: "Ariados",     0xA9: "Crobat",      0xAA: "Chinchou",    0xAB: "Lanturn",
    0xAC: "Pichu",       0xAD: "Cleffa",      0xAE: "Igglybuff",   0xAF: "Togepi",
    0xB0: "Togetic",     0xB1: "Natu",        0xB2: "Xatu",        0xB3: "Mareep",
    0xB4: "Flaaffy",     0xB5: "Ampharos",    0xB6: "Bellossom",   0xB7: "Marill",
    0xB8: "Azumarill",   0xB9: "Sudowoodo",   0xBA: "Politoed",    0xBB: "Hoppip",
    0xBC: "Skiploom",    0xBD: "Jumpluff",    0xBE: "Aipom",       0xBF: "Sunkern",
    0xC0: "Sunflora",    0xC1: "Yanma",       0xC2: "Wooper",      0xC3: "Quagsire",
    0xC4: "Espeon",      0xC5: "Umbreon",     0xC6: "Murkrow",     0xC7: "Slowking",
    0xC8: "Misdreavus",  0xC9: "Unown",       0xCA: "Wobbuffet",   0xCB: "Girafarig",
    0xCC: "Pineco",      0xCD: "Forretress",  0xCE: "Dunsparce",   0xCF: "Gligar",
    0xD0: "Steelix",     0xD1: "Snubbull",    0xD2: "Granbull",    0xD3: "Qwilfish",
    0xD4: "Scizor",      0xD5: "Shuckle",     0xD6: "Heracross",   0xD7: "Sneasel",
    0xD8: "Teddiursa",   0xD9: "Ursaring",    0xDA: "Slugma",      0xDB: "Magcargo",
    0xDC: "Swinub",      0xDD: "Piloswine",   0xDE: "Corsola",     0xDF: "Remoraid",
    0xE0: "Octillery",   0xE1: "Delibird",    0xE2: "Mantine",     0xE3: "Skarmory",
    0xE4: "Houndour",    0xE5: "Houndoom",    0xE6: "Kingdra",     0xE7: "Phanpy",
    0xE8: "Donphan",     0xE9: "Porygon2",    0xEA: "Stantler",    0xEB: "Smeargle",
    0xEC: "Tyrogue",     0xED: "Hitmontop",   0xEE: "Smoochum",    0xEF: "Elekid",
    0xF0: "Magby",       0xF1: "Miltank",     0xF2: "Blissey",     0xF3: "Raikou",
    0xF4: "Entei",       0xF5: "Suicune",     0xF6: "Larvitar",    0xF7: "Pupitar",
    0xF8: "Tyranitar",   0xF9: "Lugia",       0xFA: "Ho-Oh",       0xFB: "Celebi",
}

# ═════════════════════════════════════════════════════════════════════════════
# GEN 2 MOVES
# ═════════════════════════════════════════════════════════════════════════════

# Gen 2 has 251 moves (165 from Gen 1 + 86 new moves)
# Move ID → (Name, Max PP)

GEN2_MOVES = {
    0x00: ("—", 0),
    # Gen 1 Moves (0x01-0xA5)
    0x01: ("Pound", 35),           0x02: ("Karate Chop", 25),    0x03: ("Double Slap", 10),
    0x04: ("Comet Punch", 15),     0x05: ("Mega Punch", 20),     0x06: ("Pay Day", 20),
    0x07: ("Fire Punch", 15),      0x08: ("Ice Punch", 15),      0x09: ("Thunder Punch", 15),
    0x0A: ("Scratch", 35),         0x0B: ("Vice Grip", 30),      0x0C: ("Guillotine", 5),
    0x0D: ("Razor Wind", 10),      0x0E: ("Swords Dance", 30),   0x0F: ("Cut", 30),
    0x10: ("Gust", 35),            0x11: ("Wing Attack", 35),    0x12: ("Whirlwind", 20),
    0x13: ("Fly", 15),             0x14: ("Bind", 20),           0x15: ("Slam", 20),
    0x16: ("Vine Whip", 10),       0x17: ("Stomp", 20),          0x18: ("Double Kick", 30),
    0x19: ("Mega Kick", 5),        0x1A: ("Jump Kick", 25),      0x1B: ("Rolling Kick", 15),
    0x1C: ("Sand Attack", 15),     0x1D: ("Headbutt", 15),       0x1E: ("Horn Attack", 25),
    0x1F: ("Fury Attack", 20),     0x20: ("Horn Drill", 5),      0x21: ("Tackle", 35),
    0x22: ("Body Slam", 15),       0x23: ("Wrap", 20),           0x24: ("Take Down", 20),
    0x25: ("Thrash", 20),          0x26: ("Double-Edge", 15),    0x27: ("Tail Whip", 30),
    0x28: ("Poison Sting", 35),    0x29: ("Twineedle", 20),      0x2A: ("Pin Missile", 20),
    0x2B: ("Leer", 30),            0x2C: ("Bite", 25),           0x2D: ("Growl", 40),
    0x2E: ("Roar", 20),            0x2F: ("Sing", 15),           0x30: ("Supersonic", 20),
    0x31: ("Sonic Boom", 20),      0x32: ("Disable", 20),        0x33: ("Acid", 30),
    0x34: ("Ember", 25),           0x35: ("Flamethrower", 15),   0x36: ("Mist", 30),
    0x37: ("Water Gun", 25),       0x38: ("Hydro Pump", 5),      0x39: ("Surf", 15),
    0x3A: ("Ice Beam", 10),        0x3B: ("Blizzard", 5),        0x3C: ("Psybeam", 20),
    0x3D: ("Bubble Beam", 20),     0x3E: ("Aurora Beam", 20),    0x3F: ("Hyper Beam", 5),
    0x40: ("Peck", 35),            0x41: ("Drill Peck", 20),     0x42: ("Submission", 25),
    0x43: ("Low Kick", 20),        0x44: ("Counter", 20),        0x45: ("Seismic Toss", 20),
    0x46: ("Strength", 15),        0x47: ("Absorb", 20),         0x48: ("Mega Drain", 10),
    0x49: ("Leech Seed", 10),      0x4A: ("Growth", 40),         0x4B: ("Razor Leaf", 25),
    0x4C: ("Solar Beam", 10),      0x4D: ("Poison Powder", 35),  0x4E: ("Stun Spore", 30),
    0x4F: ("Sleep Powder", 15),    0x50: ("Petal Dance", 20),    0x51: ("String Shot", 40),
    0x52: ("Dragon Rage", 10),     0x53: ("Fire Spin", 15),      0x54: ("Thunder Shock", 30),
    0x55: ("Thunderbolt", 15),     0x56: ("Thunder Wave", 20),   0x57: ("Thunder", 10),
    0x58: ("Rock Throw", 15),      0x59: ("Earthquake", 10),     0x5A: ("Fissure", 5),
    0x5B: ("Dig", 10),             0x5C: ("Toxic", 10),          0x5D: ("Confusion", 25),
    0x5E: ("Psychic", 10),         0x5F: ("Hypnosis", 20),       0x60: ("Meditate", 40),
    0x61: ("Agility", 30),         0x62: ("Quick Attack", 30),   0x63: ("Rage", 20),
    0x64: ("Teleport", 20),        0x65: ("Night Shade", 15),    0x66: ("Mimic", 10),
    0x67: ("Screech", 40),         0x68: ("Double Team", 15),    0x69: ("Recover", 20),
    0x6A: ("Harden", 30),          0x6B: ("Minimize", 20),       0x6C: ("Smokescreen", 20),
    0x6D: ("Confuse Ray", 10),     0x6E: ("Withdraw", 40),       0x6F: ("Defense Curl", 40),
    0x70: ("Barrier", 30),         0x71: ("Light Screen", 30),   0x72: ("Haze", 30),
    0x73: ("Reflect", 20),         0x74: ("Focus Energy", 30),   0x75: ("Bide", 10),
    0x76: ("Metronome", 10),       0x77: ("Mirror Move", 20),    0x78: ("Self-Destruct", 5),
    0x79: ("Egg Bomb", 10),        0x7A: ("Lick", 30),           0x7B: ("Smog", 20),
    0x7C: ("Sludge", 20),          0x7D: ("Bone Club", 20),      0x7E: ("Fire Blast", 5),
    0x7F: ("Waterfall", 15),       0x80: ("Clamp", 10),          0x81: ("Swift", 20),
    0x82: ("Skull Bash", 15),      0x83: ("Spike Cannon", 15),   0x84: ("Constrict", 35),
    0x85: ("Amnesia", 20),         0x86: ("Kinesis", 15),        0x87: ("Soft-Boiled", 10),
    0x88: ("High Jump Kick", 20),  0x89: ("Glare", 30),          0x8A: ("Dream Eater", 15),
    0x8B: ("Poison Gas", 40),      0x8C: ("Barrage", 20),        0x8D: ("Leech Life", 15),
    0x8E: ("Lovely Kiss", 10),     0x8F: ("Sky Attack", 5),      0x90: ("Transform", 10),
    0x91: ("Bubble", 30),          0x92: ("Dizzy Punch", 10),    0x93: ("Spore", 15),
    0x94: ("Flash", 20),           0x95: ("Psywave", 15),        0x96: ("Splash", 40),
    0x97: ("Acid Armor", 40),      0x98: ("Crabhammer", 10),     0x99: ("Explosion", 5),
    0x9A: ("Fury Swipes", 15),     0x9B: ("Bonemerang", 10),     0x9C: ("Rest", 10),
    0x9D: ("Rock Slide", 10),      0x9E: ("Hyper Fang", 15),     0x9F: ("Sharpen", 30),
    0xA0: ("Conversion", 30),      0xA1: ("Tri Attack", 10),     0xA2: ("Super Fang", 10),
    0xA3: ("Slash", 20),           0xA4: ("Substitute", 10),     0xA5: ("Struggle", 1),
    
    # Gen 2 New Moves (0xA6-0xFB)
    0xA6: ("Sketch", 1),           0xA7: ("Triple Kick", 10),    0xA8: ("Thief", 10),
    0xA9: ("Spider Web", 10),      0xAA: ("Mind Reader", 5),     0xAB: ("Nightmare", 15),
    0xAC: ("Flame Wheel", 25),     0xAD: ("Snore", 15),          0xAE: ("Curse", 10),
    0xAF: ("Flail", 15),           0xB0: ("Conversion 2", 30),   0xB1: ("Aeroblast", 5),
    0xB2: ("Cotton Spore", 40),    0xB3: ("Reversal", 15),       0xB4: ("Spite", 10),
    0xB5: ("Powder Snow", 25),     0xB6: ("Protect", 10),        0xB7: ("Mach Punch", 30),
    0xB8: ("Scary Face", 10),      0xB9: ("Faint Attack", 20),   0xBA: ("Sweet Kiss", 10),
    0xBB: ("Belly Drum", 10),      0xBC: ("Sludge Bomb", 10),    0xBD: ("Mud-Slap", 10),
    0xBE: ("Octazooka", 10),       0xBF: ("Spikes", 20),         0xC0: ("Zap Cannon", 5),
    0xC1: ("Foresight", 40),       0xC2: ("Destiny Bond", 5),    0xC3: ("Perish Song", 5),
    0xC4: ("Icy Wind", 15),        0xC5: ("Detect", 5),          0xC6: ("Bone Rush", 10),
    0xC7: ("Lock-On", 5),          0xC8: ("Outrage", 15),        0xC9: ("Sandstorm", 10),
    0xCA: ("Giga Drain", 5),       0xCB: ("Endure", 10),         0xCC: ("Charm", 20),
    0xCD: ("Rollout", 20),         0xCE: ("False Swipe", 40),    0xCF: ("Swagger", 15),
    0xD0: ("Milk Drink", 10),      0xD1: ("Spark", 20),          0xD2: ("Fury Cutter", 20),
    0xD3: ("Steel Wing", 25),      0xD4: ("Mean Look", 5),       0xD5: ("Attract", 15),
    0xD6: ("Sleep Talk", 10),      0xD7: ("Heal Bell", 5),       0xD8: ("Return", 20),
    0xD9: ("Present", 15),         0xDA: ("Frustration", 20),    0xDB: ("Safeguard", 25),
    0xDC: ("Pain Split", 20),      0xDD: ("Sacred Fire", 5),     0xDE: ("Magnitude", 30),
    0xDF: ("Dynamic Punch", 5),    0xE0: ("Megahorn", 10),       0xE1: ("Dragon Breath", 20),
    0xE2: ("Baton Pass", 40),      0xE3: ("Encore", 5),          0xE4: ("Pursuit", 20),
    0xE5: ("Rapid Spin", 40),      0xE6: ("Sweet Scent", 20),    0xE7: ("Iron Tail", 15),
    0xE8: ("Metal Claw", 35),      0xE9: ("Vital Throw", 10),    0xEA: ("Morning Sun", 5),
    0xEB: ("Synthesis", 5),        0xEC: ("Moonlight", 5),       0xED: ("Hidden Power", 15),
    0xEE: ("Cross Chop", 5),       0xEF: ("Twister", 20),        0xF0: ("Rain Dance", 5),
    0xF1: ("Sunny Day", 5),        0xF2: ("Crunch", 15),         0xF3: ("Mirror Coat", 20),
    0xF4: ("Psych Up", 10),        0xF5: ("Extreme Speed", 5),   0xF6: ("Ancient Power", 5),
    0xF7: ("Shadow Ball", 15),     0xF8: ("Future Sight", 15),   0xF9: ("Rock Smash", 15),
    0xFA: ("Whirlpool", 15),       0xFB: ("Beat Up", 10),
}

def get_move_max_pp(move_id: int) -> int:
    """Get max PP for a move."""
    if move_id in GEN2_MOVES:
        return GEN2_MOVES[move_id][1]
    return 0

def get_move_name(move_id: int) -> str:
    """Get move name."""
    if move_id in GEN2_MOVES:
        return GEN2_MOVES[move_id][0]
    return f"Move#{move_id:02X}"

# ═════════════════════════════════════════════════════════════════════════════
# GEN 2 ITEMS  
# ═════════════════════════════════════════════════════════════════════════════

# Gen 2 items (including new berries, held items, etc.)
GEN2_ITEMS = {
    0x00: None,  # No item
    # Poké Balls
    0x01: "Master Ball",    0x02: "Ultra Ball",     0x03: "Great Ball",     0x04: "Poké Ball",
    0x05: "Town Map",       0x06: "Bicycle",        0x07: "Moon Stone",     0x08: "Antidote",
    0x09: "Burn Heal",      0x0A: "Ice Heal",       0x0B: "Awakening",      0x0C: "Parlyz Heal",
    0x0D: "Full Restore",   0x0E: "Max Potion",     0x0F: "Hyper Potion",   0x10: "Super Potion",
    0x11: "Potion",         0x12: "Escape Rope",    0x13: "Repel",          0x14: "Max Elixir",
    0x15: "Fire Stone",     0x16: "Thunderstone",   0x17: "Water Stone",    0x18: "HP Up",
    0x19: "Protein",        0x1A: "Iron",           0x1B: "Carbos",         0x1C: "Lucky Punch",
    0x1D: "Calcium",        0x1E: "Rare Candy",     0x1F: "X Accuracy",     0x20: "Leaf Stone",
    0x21: "Metal Powder",   0x22: "Nugget",         0x23: "Poké Doll",      0x24: "Full Heal",
    0x25: "Revive",         0x26: "Max Revive",     0x27: "Guard Spec.",    0x28: "Super Repel",
    0x29: "Max Repel",      0x2A: "Dire Hit",       0x2B: "Fresh Water",    0x2C: "Soda Pop",
    0x2D: "Lemonade",       0x2E: "X Attack",       0x2F: "X Defend",       0x30: "X Speed",
    0x31: "X Special",      0x32: "Coin Case",      0x33: "Itemfinder",     0x34: "Exp. Share",
    0x35: "Old Rod",        0x36: "Good Rod",       0x37: "Silver Leaf",    0x38: "Super Rod",
    0x39: "PP Up",          0x3A: "Ether",          0x3B: "Max Ether",      0x3C: "Elixir",
    0x3D: "Red Scale",      0x3E: "SecretPotion",   0x3F: "S.S. Ticket",    0x40: "Mystery Egg",
    0x41: "Clear Bell",     0x42: "Silver Wing",    0x43: "Moomoo Milk",    0x44: "Quick Claw",
    0x45: "Psn Cure Berry", 0x46: "Gold Leaf",      0x47: "Soft Sand",      0x48: "Sharp Beak",
    0x49: "Prz Cure Berry", 0x4A: "Burnt Berry",    0x4B: "Ice Berry",      0x4C: "Poison Barb",
    0x4D: "King's Rock",    0x4E: "Bitter Berry",   0x4F: "Mint Berry",     0x50: "Red Apricorn",
    0x51: "TinyMushroom",   0x52: "Big Mushroom",   0x53: "SilverPowder",   0x54: "Blu Apricorn",
    0x55: "Amulet Coin",    0x56: "Ylw Apricorn",   0x57: "Grn Apricorn",   0x58: "Cleanse Tag",
    0x59: "Mystic Water",   0x5A: "TwistedSpoon",   0x5B: "Wht Apricorn",   0x5C: "Blackbelt",
    0x5D: "Blk Apricorn",   0x5E: "Pnk Apricorn",   0x5F: "BlackGlasses",   0x60: "SlowpokeTail",
    0x61: "Pink Bow",       0x62: "Stick",          0x63: "Smoke Ball",     0x64: "NeverMeltIce",
    0x65: "Magnet",         0x66: "Miracle Berry",  0x67: "Pearl",          0x68: "Big Pearl",
    0x69: "Everstone",      0x6A: "Spell Tag",      0x6B: "Ragecandybar",   0x6C: "GS Ball",
    0x6D: "Blue Card",      0x6E: "Miracle Seed",   0x6F: "Thick Club",     0x70: "Focus Band",
    0x71: "EnergyPowder",   0x72: "Energy Root",    0x73: "Heal Powder",    0x74: "Revival Herb",
    0x75: "Hard Stone",     0x76: "Lucky Egg",      0x77: "Card Key",       0x78: "Machine Part",
    0x79: "Egg Ticket",     0x7A: "Lost Item",      0x7B: "Stardust",       0x7C: "Star Piece",
    0x7D: "Basement Key",   0x7E: "Pass",           0x7F: "Charcoal",       0x80: "Berry Juice",
    0x81: "Scope Lens",     0x82: "Metal Coat",     0x83: "Dragon Fang",    0x84: "Leftovers",
    0x85: "Mystery Berry",  0x86: "Dragon Scale",   0x87: "Berserk Gene",   0x88: "Sacred Ash",
    0x89: "Heavy Ball",     0x8A: "Flower Mail",    0x8B: "Level Ball",     0x8C: "Lure Ball",
    0x8D: "Fast Ball",      0x8E: "Light Ball",     0x8F: "Friend Ball",    0x90: "Moon Ball",
    0x91: "Love Ball",      0x92: "Normal Box",     0x93: "Gorgeous Box",   0x94: "Sun Stone",
    0x95: "Polkadot Bow",   0x96: "Up-Grade",       0x97: "Berry",          0x98: "Gold Berry",
    0x99: "Squirt Bottle",  0x9A: "Park Ball",      0x9B: "Rainbow Wing",   0x9C: "Brick Piece",
    0x9D: "Surf Mail",      0x9E: "Litebluemail",   0x9F: "Portraitmail",   0xA0: "Lovely Mail",
    0xA1: "Eon Mail",       0xA2: "Morph Mail",     0xA3: "Bluesky Mail",   0xA4: "Music Mail",
    0xA5: "Mirage Mail",    0xAA: "TM01",           0xAB: "TM02",           0xAC: "TM03",
    0xAD: "TM04",           0xBD: "TM05",           0xBE: "TM06",           0xBF: "TM07",
    0xC0: "TM08",           0xC1: "TM09",           0xC2: "TM10",           0xC3: "TM11",
    0xC4: "TM12",           0xC5: "TM13",           0xC6: "TM14",           0xC7: "TM15",
    0xC8: "TM16",           0xC9: "TM17",           0xCA: "TM18",           0xCB: "TM19",
    0xCC: "TM20",           0xCD: "TM21",           0xCE: "TM22",           0xCF: "TM23",
    0xD0: "TM24",           0xD1: "TM25",           0xD2: "TM26",           0xD3: "TM27",
    0xD4: "TM28",           0xD5: "TM29",           0xD6: "TM30",           0xD7: "TM31",
    0xD8: "TM32",           0xD9: "TM33",           0xDA: "TM34",           0xDB: "TM35",
    0xDC: "TM36",           0xDD: "TM37",           0xDE: "TM38",           0xDF: "TM39",
    0xE0: "TM40",           0xE1: "TM41",           0xE2: "TM42",           0xE3: "TM43",
    0xE4: "TM44",           0xE5: "TM45",           0xE6: "TM46",           0xE7: "TM47",
    0xE8: "TM48",           0xE9: "TM49",           0xEA: "TM50",           0xF3: "HM01",
    0xF4: "HM02",           0xF5: "HM03",           0xF6: "HM04",           0xF7: "HM05",
    0xF8: "HM06",           0xF9: "HM07",
}

def get_item_name(item_id: int) -> str:
    """Get item name."""
    if item_id == 0:
        return None
    return GEN2_ITEMS.get(item_id, f"Item#{item_id:02X}")

# ═════════════════════════════════════════════════════════════════════════════
# GEN 2 POKEBALL TYPES
# ═════════════════════════════════════════════════════════════════════════════

GEN2_BALLS = {
    0x00: "—",
    0x01: "Poké Ball",
    0x02: "Great Ball",
    0x03: "Ultra Ball",
    0x04: "Master Ball",
    0x05: "Safari Ball",
    0x06: "Level Ball",
    0x07: "Lure Ball",
    0x08: "Moon Ball",
    0x09: "Friend Ball",
    0x0A: "Fast Ball",
    0x0B: "Heavy Ball",
    0x0C: "Love Ball",
    0x0D: "Park Ball",
}

# ═════════════════════════════════════════════════════════════════════════════
# GEN 2 SAVE STRUCTURE OFFSETS
# ═════════════════════════════════════════════════════════════════════════════

# Gen 2 save file structure (32,816 bytes total):
# 0x0000-0x1FFF: Bank 0 (8 KB) - SRAM bank 0
# 0x2000-0x3FFF: Bank 1 (8 KB) - Main save data
# 0x4000-0x5FFF: Bank 2 (8 KB) - PC Box 1-7
# 0x6000-0x7FFF: Bank 3 (8 KB) - PC Box 8-14
# 0x8000-0x802F: Extra data (48 bytes)

# Main save offsets (relative to 0x2000)
GEN2_SAVE_OFFSETS = {
    # Trainer info
    "player_id":     (0x2009, 2),   # Big-endian
    "player_name":   (0x200B, 11),  # Null-terminated
    "rival_name":    (0x2021, 11),  # Null-terminated
    "money":         (0x23DB, 3),   # BCD encoded
    "playtime_h":    (0x2053, 2),   # Hours (big-endian)
    "playtime_m":    (0x2055, 1),   # Minutes
    "playtime_s":    (0x2056, 1),   # Seconds
    "badges_johto":  (0x23E4, 1),   # Bit flags for Johto badges
    "badges_kanto":  (0x23E5, 1),   # Bit flags for Kanto badges
    
    # Pokedex (251 Pokemon)
    "pokedex_owned": (0x2A4C, 32),  # 251 bits = 32 bytes
    "pokedex_seen":  (0x2A6C, 32),  # 251 bits = 32 bytes
    
    # Party
    "party_count":   (0x288A, 1),
    "party_species": (0x288B, 7),   # Species IDs (6 + terminator 0xFF)
    "party_data":    (0x2892, 288), # 6 × 48 bytes (0x2892 + 0x120 = 0x29B2)
    "party_ot":      (0x29B2, 66),  # 6 × 11 bytes
    "party_names":   (0x29F4, 66),  # 6 × 11 bytes
    
    # Current box number
    "current_box":   (0x2724, 1),   # 0-13 (14 boxes)
    
    # Crystal-specific (optional fields)
    "player_gender": (0x3E3D, 1),   # 0x00=Male, 0x01=Female (Crystal only)
}

# Crystal-specific save offsets (different from Gold/Silver)
GEN2_CRYSTAL_OFFSETS = {
    # Most offsets are same as Gold/Silver, but party is different!
    "player_id":     (0x2009, 2),
    "player_name":   (0x200B, 11),
    "rival_name":    (0x2021, 11),
    "money":         (0x23DB, 3),
    "playtime_h":    (0x2053, 2),
    "playtime_m":    (0x2055, 1),
    "playtime_s":    (0x2056, 1),
    "badges_johto":  (0x23E4, 1),
    "badges_kanto":  (0x23E5, 1),
    "pokedex_owned": (0x2A4C, 32),
    "pokedex_seen":  (0x2A6C, 32),
    "current_box":   (0x2724, 1),
    "player_gender": (0x3E3D, 1),
    
    # CRYSTAL-SPECIFIC PARTY OFFSETS (DIFFERENT FROM GOLD/SILVER!)
    "party_count":   (0x2865, 1),
    "party_species": (0x2866, 7),
    "party_data":    (0x286D, 288),  # 6 × 48 bytes (starts right after species list + 0xFF term)
    "party_ot":      (0x29ED, 66),   # 6 × 11 bytes
    "party_names":   (0x2A2F, 66),   # 6 × 11 bytes
}

def get_player_gender(data: bytes, is_crystal: bool) -> str:
    """Get player gender (Crystal only)."""
    if not is_crystal:
        return "Male"  # Gold/Silver only have male protagonist
    
    offset, _ = GEN2_CRYSTAL_OFFSETS["player_gender"]
    gender_byte = data[offset]
    return "Female" if gender_byte == 0x01 else "Male"


# PC Box storage
# Box structure: count (1) + species (21 with 0xFF terminator) + data (20 × 32) + OT (20 × 11) + nicknames (20 × 11)
# Each box = 1 + 21 + 640 + 220 + 220 + 2 (padding) = 1104 bytes

GEN2_BOX_SIZE = 1104

def get_gen2_box_offset(box_number: int) -> int:
    """
    Get the offset for a Gen 2 PC box (1-14).
    
    Boxes 1-7:  Bank 2 (0x4000-0x5FFF)
    Boxes 8-14: Bank 3 (0x6000-0x7FFF)
    """
    if not 1 <= box_number <= 14:
        raise ValueError(f"Box number must be 1-14, got {box_number}")
    
    if box_number <= 7:
        # Boxes 1-7 in bank 2
        return 0x4000 + (box_number - 1) * GEN2_BOX_SIZE
    else:
        # Boxes 8-14 in bank 3
        return 0x6000 + (box_number - 8) * GEN2_BOX_SIZE

# ═════════════════════════════════════════════════════════════════════════════
# GEN 2 POKEMON STRUCTURE
# ═════════════════════════════════════════════════════════════════════════════

# Gen 2 Box Pokemon: 32 bytes
# Gen 2 Party Pokemon: 48 bytes (box data + party-only fields)

GEN2_BOX_POKEMON_STRUCT = {
    "species":       (0x00, 1),   # Species ID
    "held_item":     (0x01, 1),   # Held item ID
    "move1":         (0x02, 1),   # Move 1 ID
    "move2":         (0x03, 1),   # Move 2 ID
    "move3":         (0x04, 1),   # Move 3 ID
    "move4":         (0x05, 1),   # Move 4 ID
    "ot_id":         (0x06, 2),   # Original Trainer ID (big-endian)
    "exp":           (0x08, 3),   # Experience points (24-bit big-endian)
    "hp_ev":         (0x0B, 2),   # HP Effort Value (big-endian)
    "attack_ev":     (0x0D, 2),   # Attack EV (big-endian)
    "defense_ev":    (0x0F, 2),   # Defense EV (big-endian)
    "speed_ev":      (0x11, 2),   # Speed EV (big-endian)
    "special_ev":    (0x13, 2),   # Special EV (big-endian) - affects both SpA and SpD
    "dvs":           (0x15, 2),   # DVs (Atk/Def/Spd/Spc, 4 bits each, big-endian)
    "move1_pp":      (0x17, 1),   # Move 1 PP
    "move2_pp":      (0x18, 1),   # Move 2 PP
    "move3_pp":      (0x19, 1),   # Move 3 PP
    "move4_pp":      (0x1A, 1),   # Move 4 PP
    "friendship":    (0x1B, 1),   # Friendship/Happiness
    "pokerus":       (0x1C, 1),   # Pokérus status
    "caught_data":   (0x1D, 2),   # Caught info (big-endian)
    "level":         (0x1F, 1),   # Current level
}

# Gen 2 Party Pokemon: 48 bytes (32 bytes box data + 16 bytes party-only)
GEN2_PARTY_POKEMON_STRUCT = {
    # First 32 bytes: same as box structure (0x00-0x1F)
    **GEN2_BOX_POKEMON_STRUCT,
    
    # Party-only data (0x20-0x2F)
    "status":        (0x20, 1),   # Status condition
    "unused1":       (0x21, 1),   # Unused
    "hp_current":    (0x22, 2),   # Current HP (big-endian)
    "hp_max":        (0x24, 2),   # Max HP (big-endian)
    "attack":        (0x26, 2),   # Attack stat (big-endian)
    "defense":       (0x28, 2),   # Defense stat (big-endian)
    "speed":         (0x2A, 2),   # Speed stat (big-endian)
    "sp_attack":     (0x2C, 2),   # Special Attack stat (big-endian)
    "sp_defense":    (0x2E, 2),   # Special Defense stat (big-endian)
}

# Caught data bit layout (16 bits):
# Bits 0-3:   Time of day (0=Morning, 1=Day, 2=Night)
# Bits 4-7:   Level met (0-63, actual level = value)
# Bits 8-11:  Location met (partial, see location byte)
# Bits 12-15: Ball type (see GEN2_BALLS)

# Pokerus byte:
# Upper 4 bits: Strain (0x0-0xF, 0 = not infected)
# Lower 4 bits: Days remaining (0x0-0xF, 0 = cured)

# ═════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def is_shiny(attack_dv: int, defense_dv: int, speed_dv: int, special_dv: int) -> bool:
    """
    Check if Pokemon is shiny based on DVs.
    
    Shiny condition in Gen 2:
    - Defense DV = 10 (0xA)
    - Speed DV = 10 (0xA) 
    - Special DV = 10 (0xA)
    - Attack DV = 2, 3, 6, 7, 10, 11, 14, or 15 (low bit must match Speed)
    """
    if defense_dv == 10 and speed_dv == 10 and special_dv == 10:
        # Attack DV must be 2, 3, 6, 7, 10, 11, 14, or 15
        return attack_dv in [2, 3, 6, 7, 10, 11, 14, 15]
    return False

def get_gender(species_id: int, attack_dv: int) -> str:
    """
    Determine gender from Attack DV and species.
    
    Gender threshold varies by species:
    - Always Male: threshold = 0 (e.g., Nidoran♂, Tauros)
    - Always Female: threshold = 254 (e.g., Nidoran♀, Chansey)
    - 87.5% M: threshold = 31
    - 75% M: threshold = 63
    - 50% M: threshold = 127
    - 25% M: threshold = 191
    - Genderless: threshold = 255 (e.g., Magnemite, Voltorb)
    
    Gender = Male if Attack DV >= threshold, else Female
    """
    # TODO: Map species to gender thresholds
    # For now, generic 50/50
    return "M" if attack_dv >= 8 else "F"

def get_unown_form(attack_dv: int, defense_dv: int, speed_dv: int, special_dv: int) -> str:
    """
    Calculate Unown letter form from DVs.
    
    Form = ((Atk DV & 0x6) << 5) | ((Def DV & 0x6) << 3) | ((Spd DV & 0x6) << 1) | (Spc DV & 0x6)
    Result / 10 = letter (0=A, 1=B, ... 25=Z)
    """
    form_value = (
        ((attack_dv & 0x6) << 5) |
        ((defense_dv & 0x6) << 3) |
        ((speed_dv & 0x6) << 1) |
        (special_dv & 0x6)
    )
    letter_index = form_value // 10
    if 0 <= letter_index <= 25:
        return chr(ord('A') + letter_index)
    return '?'

# ═════════════════════════════════════════════════════════════════════════════
# GROWTH RATES & EXP CURVES
# ═════════════════════════════════════════════════════════════════════════════

# Gen 2 uses same 4 growth rates as Gen 1
# Can reuse GEN1_EXP_CURVES and GEN1_SPECIES_GROWTH with Gen 2 species added

# TODO: Map Gen 2 species to growth rates

# Map species ID to growth rate
GEN2_SPECIES_GROWTH = {
    # Most Pokemon use medium_fast (1,000,000 EXP)
    # Starters and their evolutions use medium_slow (1,059,860 EXP)
}

# Gender threshold by species
# Gender = Male if Attack DV >= threshold, else Female
GEN2_GENDER_RATIO = {
    # Always Male: threshold = 0
    # Always Female: threshold = 254
    # Genderless: threshold = 255
    # Default: 127 (50/50 split)
}

def get_gender_threshold(species_id: int) -> int:
    """Get gender threshold for a species. Default is 127 (50/50)."""
    return GEN2_GENDER_RATIO.get(species_id, 127)