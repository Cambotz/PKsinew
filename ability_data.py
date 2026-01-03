# Gen 3 Ability Data
# Pokemon abilities for Ruby/Sapphire/Emerald/FireRed/LeafGreen

ABILITY_NAMES = {
    0: "---",
    1: "Stench",
    2: "Drizzle",
    3: "Speed Boost",
    4: "Battle Armor",
    5: "Sturdy",
    6: "Damp",
    7: "Limber",
    8: "Sand Veil",
    9: "Static",
    10: "Volt Absorb",
    11: "Water Absorb",
    12: "Oblivious",
    13: "Cloud Nine",
    14: "Compound Eyes",
    15: "Insomnia",
    16: "Color Change",
    17: "Immunity",
    18: "Flash Fire",
    19: "Shield Dust",
    20: "Own Tempo",
    21: "Suction Cups",
    22: "Intimidate",
    23: "Shadow Tag",
    24: "Rough Skin",
    25: "Wonder Guard",
    26: "Levitate",
    27: "Effect Spore",
    28: "Synchronize",
    29: "Clear Body",
    30: "Natural Cure",
    31: "Lightning Rod",
    32: "Serene Grace",
    33: "Swift Swim",
    34: "Chlorophyll",
    35: "Illuminate",
    36: "Trace",
    37: "Huge Power",
    38: "Poison Point",
    39: "Inner Focus",
    40: "Magma Armor",
    41: "Water Veil",
    42: "Magnet Pull",
    43: "Soundproof",
    44: "Rain Dish",
    45: "Sand Stream",
    46: "Pressure",
    47: "Thick Fat",
    48: "Early Bird",
    49: "Flame Body",
    50: "Run Away",
    51: "Keen Eye",
    52: "Hyper Cutter",
    53: "Pickup",
    54: "Truant",
    55: "Hustle",
    56: "Cute Charm",
    57: "Plus",
    58: "Minus",
    59: "Forecast",
    60: "Sticky Hold",
    61: "Shed Skin",
    62: "Guts",
    63: "Marvel Scale",
    64: "Liquid Ooze",
    65: "Overgrow",
    66: "Blaze",
    67: "Torrent",
    68: "Swarm",
    69: "Rock Head",
    70: "Drought",
    71: "Arena Trap",
    72: "Vital Spirit",
    73: "White Smoke",
    74: "Pure Power",
    75: "Shell Armor",
    76: "Air Lock",
}

# Pokemon species to ability mapping
# Format: species_id: (ability1, ability2) - ability2 can be None if only one ability
POKEMON_ABILITIES = {
    # Gen 1
    1: (65, None),      # Bulbasaur - Overgrow
    2: (65, None),      # Ivysaur - Overgrow
    3: (65, None),      # Venusaur - Overgrow
    4: (66, None),      # Charmander - Blaze
    5: (66, None),      # Charmeleon - Blaze
    6: (66, None),      # Charizard - Blaze
    7: (67, None),      # Squirtle - Torrent
    8: (67, None),      # Wartortle - Torrent
    9: (67, None),      # Blastoise - Torrent
    10: (19, None),     # Caterpie - Shield Dust
    11: (61, None),     # Metapod - Shed Skin
    12: (14, None),     # Butterfree - Compound Eyes
    13: (19, None),     # Weedle - Shield Dust
    14: (61, None),     # Kakuna - Shed Skin
    15: (68, None),     # Beedrill - Swarm
    16: (51, None),     # Pidgey - Keen Eye
    17: (51, None),     # Pidgeotto - Keen Eye
    18: (51, None),     # Pidgeot - Keen Eye
    19: (50, 62),       # Rattata - Run Away / Guts
    20: (50, 62),       # Raticate - Run Away / Guts
    21: (51, None),     # Spearow - Keen Eye
    22: (51, None),     # Fearow - Keen Eye
    23: (22, 61),       # Ekans - Intimidate / Shed Skin
    24: (22, 61),       # Arbok - Intimidate / Shed Skin
    25: (9, None),      # Pikachu - Static
    26: (9, None),      # Raichu - Static
    27: (8, None),      # Sandshrew - Sand Veil
    28: (8, None),      # Sandslash - Sand Veil
    29: (38, None),     # Nidoran F - Poison Point
    30: (38, None),     # Nidorina - Poison Point
    31: (38, None),     # Nidoqueen - Poison Point
    32: (38, None),     # Nidoran M - Poison Point
    33: (38, None),     # Nidorino - Poison Point
    34: (38, None),     # Nidoking - Poison Point
    35: (56, None),     # Clefairy - Cute Charm
    36: (56, None),     # Clefable - Cute Charm
    37: (18, None),     # Vulpix - Flash Fire
    38: (18, None),     # Ninetales - Flash Fire
    39: (56, None),     # Jigglypuff - Cute Charm
    40: (56, None),     # Wigglytuff - Cute Charm
    41: (39, None),     # Zubat - Inner Focus
    42: (39, None),     # Golbat - Inner Focus
    43: (34, None),     # Oddish - Chlorophyll
    44: (34, None),     # Gloom - Chlorophyll
    45: (34, None),     # Vileplume - Chlorophyll
    46: (27, None),     # Paras - Effect Spore
    47: (27, None),     # Parasect - Effect Spore
    48: (14, None),     # Venonat - Compound Eyes
    49: (19, None),     # Venomoth - Shield Dust
    50: (8, 71),        # Diglett - Sand Veil / Arena Trap
    51: (8, 71),        # Dugtrio - Sand Veil / Arena Trap
    52: (53, 7),        # Meowth - Pickup / Limber
    53: (7, None),      # Persian - Limber
    54: (6, 13),        # Psyduck - Damp / Cloud Nine
    55: (6, 13),        # Golduck - Damp / Cloud Nine
    56: (72, None),     # Mankey - Vital Spirit
    57: (72, None),     # Primeape - Vital Spirit
    58: (22, 18),       # Growlithe - Intimidate / Flash Fire
    59: (22, 18),       # Arcanine - Intimidate / Flash Fire
    60: (11, 6),        # Poliwag - Water Absorb / Damp
    61: (11, 6),        # Poliwhirl - Water Absorb / Damp
    62: (11, 6),        # Poliwrath - Water Absorb / Damp
    63: (28, 39),       # Abra - Synchronize / Inner Focus
    64: (28, 39),       # Kadabra - Synchronize / Inner Focus
    65: (28, 39),       # Alakazam - Synchronize / Inner Focus
    66: (62, None),     # Machop - Guts
    67: (62, None),     # Machoke - Guts
    68: (62, None),     # Machamp - Guts
    69: (34, None),     # Bellsprout - Chlorophyll
    70: (34, None),     # Weepinbell - Chlorophyll
    71: (34, None),     # Victreebel - Chlorophyll
    72: (29, 64),       # Tentacool - Clear Body / Liquid Ooze
    73: (29, 64),       # Tentacruel - Clear Body / Liquid Ooze
    74: (69, 5),        # Geodude - Rock Head / Sturdy
    75: (69, 5),        # Graveler - Rock Head / Sturdy
    76: (69, 5),        # Golem - Rock Head / Sturdy
    77: (50, 18),       # Ponyta - Run Away / Flash Fire
    78: (50, 18),       # Rapidash - Run Away / Flash Fire
    79: (12, 20),       # Slowpoke - Oblivious / Own Tempo
    80: (12, 20),       # Slowbro - Oblivious / Own Tempo
    81: (42, 5),        # Magnemite - Magnet Pull / Sturdy
    82: (42, 5),        # Magneton - Magnet Pull / Sturdy
    83: (51, 39),       # Farfetch'd - Keen Eye / Inner Focus
    84: (50, 48),       # Doduo - Run Away / Early Bird
    85: (50, 48),       # Dodrio - Run Away / Early Bird
    86: (47, None),     # Seel - Thick Fat
    87: (47, None),     # Dewgong - Thick Fat
    88: (1, 60),        # Grimer - Stench / Sticky Hold
    89: (1, 60),        # Muk - Stench / Sticky Hold
    90: (75, None),     # Shellder - Shell Armor
    91: (75, None),     # Cloyster - Shell Armor
    92: (26, None),     # Gastly - Levitate
    93: (26, None),     # Haunter - Levitate
    94: (26, None),     # Gengar - Levitate
    95: (69, 5),        # Onix - Rock Head / Sturdy
    96: (15, None),     # Drowzee - Insomnia
    97: (15, None),     # Hypno - Insomnia
    98: (52, 75),       # Krabby - Hyper Cutter / Shell Armor
    99: (52, 75),       # Kingler - Hyper Cutter / Shell Armor
    100: (43, 9),       # Voltorb - Soundproof / Static
    101: (43, 9),       # Electrode - Soundproof / Static
    102: (34, None),    # Exeggcute - Chlorophyll
    103: (34, None),    # Exeggutor - Chlorophyll
    104: (69, 31),      # Cubone - Rock Head / Lightning Rod
    105: (69, 31),      # Marowak - Rock Head / Lightning Rod
    106: (7, None),     # Hitmonlee - Limber
    107: (51, None),    # Hitmonchan - Keen Eye
    108: (12, 20),      # Lickitung - Oblivious / Own Tempo
    109: (26, None),    # Koffing - Levitate
    110: (26, None),    # Weezing - Levitate
    111: (31, 69),      # Rhyhorn - Lightning Rod / Rock Head
    112: (31, 69),      # Rhydon - Lightning Rod / Rock Head
    113: (30, 32),      # Chansey - Natural Cure / Serene Grace
    114: (34, None),    # Tangela - Chlorophyll
    115: (48, None),    # Kangaskhan - Early Bird
    116: (33, None),    # Horsea - Swift Swim
    117: (38, None),    # Seadra - Poison Point
    118: (33, 41),      # Goldeen - Swift Swim / Water Veil
    119: (33, 41),      # Seaking - Swift Swim / Water Veil
    120: (35, 30),      # Staryu - Illuminate / Natural Cure
    121: (35, 30),      # Starmie - Illuminate / Natural Cure
    122: (43, None),    # Mr. Mime - Soundproof
    123: (68, None),    # Scyther - Swarm
    124: (12, None),    # Jynx - Oblivious
    125: (9, None),     # Electabuzz - Static
    126: (49, None),    # Magmar - Flame Body
    127: (52, None),    # Pinsir - Hyper Cutter
    128: (22, None),    # Tauros - Intimidate
    129: (33, None),    # Magikarp - Swift Swim
    130: (22, None),    # Gyarados - Intimidate
    131: (11, 75),      # Lapras - Water Absorb / Shell Armor
    132: (7, None),     # Ditto - Limber
    133: (50, None),    # Eevee - Run Away
    134: (11, None),    # Vaporeon - Water Absorb
    135: (10, None),    # Jolteon - Volt Absorb
    136: (18, None),    # Flareon - Flash Fire
    137: (36, None),    # Porygon - Trace
    138: (33, 75),      # Omanyte - Swift Swim / Shell Armor
    139: (33, 75),      # Omastar - Swift Swim / Shell Armor
    140: (33, 4),       # Kabuto - Swift Swim / Battle Armor
    141: (33, 4),       # Kabutops - Swift Swim / Battle Armor
    142: (69, 46),      # Aerodactyl - Rock Head / Pressure
    143: (17, 47),      # Snorlax - Immunity / Thick Fat
    144: (46, None),    # Articuno - Pressure
    145: (46, None),    # Zapdos - Pressure
    146: (46, None),    # Moltres - Pressure
    147: (61, None),    # Dratini - Shed Skin
    148: (61, None),    # Dragonair - Shed Skin
    149: (39, None),    # Dragonite - Inner Focus
    150: (46, None),    # Mewtwo - Pressure
    151: (28, None),    # Mew - Synchronize
    
    # Gen 2
    152: (65, None),    # Chikorita - Overgrow
    153: (65, None),    # Bayleef - Overgrow
    154: (65, None),    # Meganium - Overgrow
    155: (66, None),    # Cyndaquil - Blaze
    156: (66, None),    # Quilava - Blaze
    157: (66, None),    # Typhlosion - Blaze
    158: (67, None),    # Totodile - Torrent
    159: (67, None),    # Croconaw - Torrent
    160: (67, None),    # Feraligatr - Torrent
    161: (50, 51),      # Sentret - Run Away / Keen Eye
    162: (50, 51),      # Furret - Run Away / Keen Eye
    163: (15, 51),      # Hoothoot - Insomnia / Keen Eye
    164: (15, 51),      # Noctowl - Insomnia / Keen Eye
    165: (68, 48),      # Ledyba - Swarm / Early Bird
    166: (68, 48),      # Ledian - Swarm / Early Bird
    167: (68, 15),      # Spinarak - Swarm / Insomnia
    168: (68, 15),      # Ariados - Swarm / Insomnia
    169: (39, None),    # Crobat - Inner Focus
    170: (10, 35),      # Chinchou - Volt Absorb / Illuminate
    171: (10, 35),      # Lanturn - Volt Absorb / Illuminate
    172: (9, None),     # Pichu - Static
    173: (56, None),    # Cleffa - Cute Charm
    174: (56, None),    # Igglybuff - Cute Charm
    175: (55, 32),      # Togepi - Hustle / Serene Grace
    176: (55, 32),      # Togetic - Hustle / Serene Grace
    177: (28, 48),      # Natu - Synchronize / Early Bird
    178: (28, 48),      # Xatu - Synchronize / Early Bird
    179: (9, None),     # Mareep - Static
    180: (9, None),     # Flaaffy - Static
    181: (9, None),     # Ampharos - Static
    182: (34, None),    # Bellossom - Chlorophyll
    183: (47, 37),      # Marill - Thick Fat / Huge Power
    184: (47, 37),      # Azumarill - Thick Fat / Huge Power
    185: (5, 69),       # Sudowoodo - Sturdy / Rock Head
    186: (11, 6),       # Politoed - Water Absorb / Damp
    187: (34, None),    # Hoppip - Chlorophyll
    188: (34, None),    # Skiploom - Chlorophyll
    189: (34, None),    # Jumpluff - Chlorophyll
    190: (50, 53),      # Aipom - Run Away / Pickup
    191: (34, None),    # Sunkern - Chlorophyll
    192: (34, None),    # Sunflora - Chlorophyll
    193: (3, 14),       # Yanma - Speed Boost / Compound Eyes
    194: (6, 11),       # Wooper - Damp / Water Absorb
    195: (6, 11),       # Quagsire - Damp / Water Absorb
    196: (28, None),    # Espeon - Synchronize
    197: (28, None),    # Umbreon - Synchronize
    198: (15, None),    # Murkrow - Insomnia
    199: (12, 20),      # Slowking - Oblivious / Own Tempo
    200: (26, None),    # Misdreavus - Levitate
    201: (26, None),    # Unown - Levitate
    202: (23, None),    # Wobbuffet - Shadow Tag
    203: (39, 48),      # Girafarig - Inner Focus / Early Bird
    204: (5, None),     # Pineco - Sturdy
    205: (5, None),     # Forretress - Sturdy
    206: (32, 50),      # Dunsparce - Serene Grace / Run Away
    207: (52, 8),       # Gligar - Hyper Cutter / Sand Veil
    208: (69, 5),       # Steelix - Rock Head / Sturdy
    209: (22, 50),      # Snubbull - Intimidate / Run Away
    210: (22, None),    # Granbull - Intimidate
    211: (38, 33),      # Qwilfish - Poison Point / Swift Swim
    212: (68, None),    # Scizor - Swarm
    213: (5, None),     # Shuckle - Sturdy
    214: (68, 62),      # Heracross - Swarm / Guts
    215: (39, 51),      # Sneasel - Inner Focus / Keen Eye
    216: (53, None),    # Teddiursa - Pickup
    217: (62, None),    # Ursaring - Guts
    218: (49, 18),      # Slugma - Magma Armor / Flame Body
    219: (49, 18),      # Magcargo - Magma Armor / Flame Body
    220: (12, None),    # Swinub - Oblivious
    221: (12, None),    # Piloswine - Oblivious
    222: (55, 30),      # Corsola - Hustle / Natural Cure
    223: (55, None),    # Remoraid - Hustle
    224: (21, None),    # Octillery - Suction Cups
    225: (72, 55),      # Delibird - Vital Spirit / Hustle
    226: (33, 11),      # Mantine - Swift Swim / Water Absorb
    227: (51, 5),       # Skarmory - Keen Eye / Sturdy
    228: (48, 18),      # Houndour - Early Bird / Flash Fire
    229: (48, 18),      # Houndoom - Early Bird / Flash Fire
    230: (33, None),    # Kingdra - Swift Swim
    231: (53, None),    # Phanpy - Pickup
    232: (5, None),     # Donphan - Sturdy
    233: (36, None),    # Porygon2 - Trace
    234: (22, None),    # Stantler - Intimidate
    235: (20, None),    # Smeargle - Own Tempo
    236: (62, None),    # Tyrogue - Guts
    237: (22, None),    # Hitmontop - Intimidate
    238: (12, None),    # Smoochum - Oblivious
    239: (9, None),     # Elekid - Static
    240: (49, None),    # Magby - Flame Body
    241: (47, None),    # Miltank - Thick Fat
    242: (30, 32),      # Blissey - Natural Cure / Serene Grace
    243: (46, None),    # Raikou - Pressure
    244: (46, None),    # Entei - Pressure
    245: (46, None),    # Suicune - Pressure
    246: (62, None),    # Larvitar - Guts
    247: (61, None),    # Pupitar - Shed Skin
    248: (45, None),    # Tyranitar - Sand Stream
    249: (46, None),    # Lugia - Pressure
    250: (46, None),    # Ho-Oh - Pressure
    251: (30, None),    # Celebi - Natural Cure
    
    # Gen 3
    252: (65, None),    # Treecko - Overgrow
    253: (65, None),    # Grovyle - Overgrow
    254: (65, None),    # Sceptile - Overgrow
    255: (66, None),    # Torchic - Blaze
    256: (66, None),    # Combusken - Blaze
    257: (66, None),    # Blaziken - Blaze
    258: (67, None),    # Mudkip - Torrent
    259: (67, None),    # Marshtomp - Torrent
    260: (67, None),    # Swampert - Torrent
    261: (50, None),    # Poochyena - Run Away
    262: (22, None),    # Mightyena - Intimidate
    263: (53, None),    # Zigzagoon - Pickup
    264: (53, None),    # Linoone - Pickup
    265: (19, None),    # Wurmple - Shield Dust
    266: (61, None),    # Silcoon - Shed Skin
    267: (68, None),    # Beautifly - Swarm
    268: (61, None),    # Cascoon - Shed Skin
    269: (19, None),    # Dustox - Shield Dust
    270: (33, 44),      # Lotad - Swift Swim / Rain Dish
    271: (33, 44),      # Lombre - Swift Swim / Rain Dish
    272: (33, 44),      # Ludicolo - Swift Swim / Rain Dish
    273: (34, 48),      # Seedot - Chlorophyll / Early Bird
    274: (34, 48),      # Nuzleaf - Chlorophyll / Early Bird
    275: (34, 48),      # Shiftry - Chlorophyll / Early Bird
    276: (62, None),    # Taillow - Guts
    277: (62, None),    # Swellow - Guts
    278: (51, None),    # Wingull - Keen Eye
    279: (51, None),    # Pelipper - Keen Eye
    280: (28, 36),      # Ralts - Synchronize / Trace
    281: (28, 36),      # Kirlia - Synchronize / Trace
    282: (28, 36),      # Gardevoir - Synchronize / Trace
    283: (33, None),    # Surskit - Swift Swim
    284: (22, None),    # Masquerain - Intimidate
    285: (27, None),    # Shroomish - Effect Spore
    286: (27, None),    # Breloom - Effect Spore
    287: (54, None),    # Slakoth - Truant
    288: (72, None),    # Vigoroth - Vital Spirit
    289: (54, None),    # Slaking - Truant
    290: (14, None),    # Nincada - Compound Eyes
    291: (3, None),     # Ninjask - Speed Boost
    292: (25, None),    # Shedinja - Wonder Guard
    293: (43, None),    # Whismur - Soundproof
    294: (43, None),    # Loudred - Soundproof
    295: (43, None),    # Exploud - Soundproof
    296: (47, 62),      # Makuhita - Thick Fat / Guts
    297: (47, 62),      # Hariyama - Thick Fat / Guts
    298: (47, 37),      # Azurill - Thick Fat / Huge Power
    299: (5, 42),       # Nosepass - Sturdy / Magnet Pull
    300: (56, None),    # Skitty - Cute Charm
    301: (56, None),    # Delcatty - Cute Charm
    302: (51, None),    # Sableye - Keen Eye
    303: (52, 22),      # Mawile - Hyper Cutter / Intimidate
    304: (5, 69),       # Aron - Sturdy / Rock Head
    305: (5, 69),       # Lairon - Sturdy / Rock Head
    306: (5, 69),       # Aggron - Sturdy / Rock Head
    307: (74, None),    # Meditite - Pure Power
    308: (74, None),    # Medicham - Pure Power
    309: (9, 31),       # Electrike - Static / Lightning Rod
    310: (9, 31),       # Manectric - Static / Lightning Rod
    311: (57, None),    # Plusle - Plus
    312: (58, None),    # Minun - Minus
    313: (35, 68),      # Volbeat - Illuminate / Swarm
    314: (12, None),    # Illumise - Oblivious
    315: (30, 38),      # Roselia - Natural Cure / Poison Point
    316: (64, 60),      # Gulpin - Liquid Ooze / Sticky Hold
    317: (64, 60),      # Swalot - Liquid Ooze / Sticky Hold
    318: (24, None),    # Carvanha - Rough Skin
    319: (24, None),    # Sharpedo - Rough Skin
    320: (11, 12),      # Wailmer - Water Veil / Oblivious
    321: (11, 12),      # Wailord - Water Veil / Oblivious
    322: (12, None),    # Numel - Oblivious
    323: (40, None),    # Camerupt - Magma Armor
    324: (73, None),    # Torkoal - White Smoke
    325: (47, 20),      # Spoink - Thick Fat / Own Tempo
    326: (47, 20),      # Grumpig - Thick Fat / Own Tempo
    327: (20, None),    # Spinda - Own Tempo
    328: (52, 71),      # Trapinch - Hyper Cutter / Arena Trap
    329: (26, None),    # Vibrava - Levitate
    330: (26, None),    # Flygon - Levitate
    331: (8, None),     # Cacnea - Sand Veil
    332: (8, None),     # Cacturne - Sand Veil
    333: (30, None),    # Swablu - Natural Cure
    334: (30, None),    # Altaria - Natural Cure
    335: (17, None),    # Zangoose - Immunity
    336: (61, None),    # Seviper - Shed Skin
    337: (26, None),    # Lunatone - Levitate
    338: (26, None),    # Solrock - Levitate
    339: (12, None),    # Barboach - Oblivious
    340: (12, None),    # Whiscash - Oblivious
    341: (52, 75),      # Corphish - Hyper Cutter / Shell Armor
    342: (52, 75),      # Crawdaunt - Hyper Cutter / Shell Armor
    343: (26, None),    # Baltoy - Levitate
    344: (26, None),    # Claydol - Levitate
    345: (21, None),    # Lileep - Suction Cups
    346: (21, None),    # Cradily - Suction Cups
    347: (4, None),     # Anorith - Battle Armor
    348: (4, None),     # Armaldo - Battle Armor
    349: (33, None),    # Feebas - Swift Swim
    350: (63, None),    # Milotic - Marvel Scale
    351: (59, None),    # Castform - Forecast
    352: (16, None),    # Kecleon - Color Change
    353: (15, None),    # Shuppet - Insomnia
    354: (15, None),    # Banette - Insomnia
    355: (26, None),    # Duskull - Levitate
    356: (46, None),    # Dusclops - Pressure
    357: (34, None),    # Tropius - Chlorophyll
    358: (26, None),    # Chimecho - Levitate
    359: (46, None),    # Absol - Pressure
    360: (23, None),    # Wynaut - Shadow Tag
    361: (39, None),    # Snorunt - Inner Focus
    362: (39, None),    # Glalie - Inner Focus
    363: (47, None),    # Spheal - Thick Fat
    364: (47, None),    # Sealeo - Thick Fat
    365: (47, None),    # Walrein - Thick Fat
    366: (75, None),    # Clamperl - Shell Armor
    367: (33, None),    # Huntail - Swift Swim
    368: (33, None),    # Gorebyss - Swift Swim
    369: (33, 69),      # Relicanth - Swift Swim / Rock Head
    370: (33, None),    # Luvdisc - Swift Swim
    371: (69, None),    # Bagon - Rock Head
    372: (69, None),    # Shelgon - Rock Head
    373: (22, None),    # Salamence - Intimidate
    374: (29, None),    # Beldum - Clear Body
    375: (29, None),    # Metang - Clear Body
    376: (29, None),    # Metagross - Clear Body
    377: (29, None),    # Regirock - Clear Body
    378: (29, None),    # Regice - Clear Body
    379: (29, None),    # Registeel - Clear Body
    380: (26, None),    # Latias - Levitate
    381: (26, None),    # Latios - Levitate
    382: (2, None),     # Kyogre - Drizzle
    383: (70, None),    # Groudon - Drought
    384: (76, None),    # Rayquaza - Air Lock
    385: (32, None),    # Jirachi - Serene Grace
    386: (46, None),    # Deoxys - Pressure
}


def get_ability_name(ability_id):
    """Get ability name from ID"""
    return ABILITY_NAMES.get(ability_id, f"Ability #{ability_id}")


def get_pokemon_abilities(species_id):
    """
    Get abilities for a Pokemon species.
    
    Returns:
        tuple: (ability1_id, ability2_id) - ability2 may be None
    """
    return POKEMON_ABILITIES.get(species_id, (0, None))


# Gen 3 Ability Descriptions
ABILITY_DESCRIPTIONS = {
    0: "",
    1: "May cause foe to flinch.",  # Stench
    2: "Summons rain in battle.",  # Drizzle
    3: "Boosts Speed each turn.",  # Speed Boost
    4: "Blocks critical hits.",  # Battle Armor
    5: "Negates 1-hit KO moves.",  # Sturdy
    6: "Prevents self-destruct.",  # Damp
    7: "Prevents paralysis.",  # Limber
    8: "Ups evasion in sandstorm.",  # Sand Veil
    9: "May paralyze on contact.",  # Static
    10: "Absorbs Electric moves.",  # Volt Absorb
    11: "Absorbs Water moves.",  # Water Absorb
    12: "Prevents attraction.",  # Oblivious
    13: "Negates weather effects.",  # Cloud Nine
    14: "Boosts move accuracy.",  # Compound Eyes
    15: "Prevents sleep.",  # Insomnia
    16: "Changes type to foe's move.",  # Color Change
    17: "Prevents poisoning.",  # Immunity
    18: "Powers up if hit by Fire.",  # Flash Fire
    19: "Blocks move side effects.",  # Shield Dust
    20: "Prevents confusion.",  # Own Tempo
    21: "Negates forced switch.",  # Suction Cups
    22: "Lowers foe's Attack.",  # Intimidate
    23: "Prevents foe's escape.",  # Shadow Tag
    24: "Damages foe on contact.",  # Rough Skin
    25: "Only super-effective hit.",  # Wonder Guard
    26: "Not hit by Ground moves.",  # Levitate
    27: "May poison/paralyze/sleep.",  # Effect Spore
    28: "Passes on status to foe.",  # Synchronize
    29: "Prevents stat reduction.",  # Clear Body
    30: "Heals status on switch.",  # Natural Cure
    31: "Draws Electric moves.",  # Lightning Rod
    32: "Boosts move side effects.",  # Serene Grace
    33: "Ups Speed in rain.",  # Swift Swim
    34: "Ups Speed in sunshine.",  # Chlorophyll
    35: "Raises encounter rate.",  # Illuminate
    36: "Copies foe's ability.",  # Trace
    37: "Doubles Attack stat.",  # Huge Power
    38: "May poison on contact.",  # Poison Point
    39: "Prevents flinching.",  # Inner Focus
    40: "Prevents freezing.",  # Magma Armor
    41: "Prevents burns.",  # Water Veil
    42: "Traps Steel-types.",  # Magnet Pull
    43: "Blocks sound moves.",  # Soundproof
    44: "Heals HP in rain.",  # Rain Dish
    45: "Summons sandstorm.",  # Sand Stream
    46: "Ups foe's PP usage.",  # Pressure
    47: "Resists Fire and Ice.",  # Thick Fat
    48: "Wakes up quickly.",  # Early Bird
    49: "May burn on contact.",  # Flame Body
    50: "Always flees wild battles.",  # Run Away
    51: "Prevents accuracy loss.",  # Keen Eye
    52: "Prevents Attack drops.",  # Hyper Cutter
    53: "May pick up items.",  # Pickup
    54: "Can't attack every turn.",  # Truant
    55: "Ups Attack, cuts accuracy.",  # Hustle
    56: "May attract on contact.",  # Cute Charm
    57: "Ups Sp.Atk if Plus nearby.",  # Plus
    58: "Ups Sp.Atk if Minus nearby.",  # Minus
    59: "Changes with weather.",  # Forecast
    60: "Prevents item theft.",  # Sticky Hold
    61: "May heal own status.",  # Shed Skin
    62: "Ups Attack if statused.",  # Guts
    63: "Ups Defense if statused.",  # Marvel Scale
    64: "Damages HP-draining foe.",  # Liquid Ooze
    65: "Ups Grass moves in pinch.",  # Overgrow
    66: "Ups Fire moves in pinch.",  # Blaze
    67: "Ups Water moves in pinch.",  # Torrent
    68: "Ups Bug moves in pinch.",  # Swarm
    69: "Prevents recoil damage.",  # Rock Head
    70: "Summons sunshine.",  # Drought
    71: "Prevents foe's escape.",  # Arena Trap
    72: "Prevents sleep.",  # Vital Spirit
    73: "Prevents stat reduction.",  # White Smoke
    74: "Doubles Attack stat.",  # Pure Power
    75: "Blocks critical hits.",  # Shell Armor
    76: "Heals in sunshine.",  # Air Lock (actually Cacophony in Gen3)
    77: "Negates weather effects.",  # Air Lock
}


def get_ability_description(ability_id):
    """Get ability description from ID."""
    return ABILITY_DESCRIPTIONS.get(ability_id, "")


def get_pokemon_ability_name(species_id, ability_bit):
    """
    Get the actual ability name for a Pokemon based on species and ability bit.
    
    Args:
        species_id: Pokemon species ID
        ability_bit: 0 for ability 1, 1 for ability 2
        
    Returns:
        str: Ability name
    """
    abilities = get_pokemon_abilities(species_id)
    
    if ability_bit and abilities[1] is not None:
        return get_ability_name(abilities[1])
    else:
        return get_ability_name(abilities[0])


def get_pokemon_ability_id(species_id, ability_bit):
    """
    Get the actual ability ID for a Pokemon based on species and ability bit.
    
    Args:
        species_id: Pokemon species ID
        ability_bit: 0 for ability 1, 1 for ability 2
        
    Returns:
        int: Ability ID
    """
    abilities = get_pokemon_abilities(species_id)
    
    if ability_bit and abilities[1] is not None:
        return abilities[1]
    else:
        return abilities[0]