"""
Pokemon Generator for Sinew
Generates valid Gen 3 Pokemon byte data (80 bytes) from JSON recipes.
Replaces the need for pre-made .pks files that cannot be legally distributed.

Author: Sinew Development Team
"""

import struct
import random
import json
import os
from typing import Dict, List, Optional, Tuple, Union

# =============================================================================
# CONSTANTS
# =============================================================================

# Gen 3 text encoding (ASCII-like mapping for Pokemon names)
GEN3_CHAR_TABLE = {
    ' ': 0x00, 
    'あ': 0x01, 'い': 0x02, 'う': 0x03, 'え': 0x04, 'お': 0x05,
    'か': 0x06, 'き': 0x07, 'く': 0x08, 'け': 0x09, 'こ': 0x0A,
    'さ': 0x0B, 'し': 0x0C, 'す': 0x0D, 'せ': 0x0E, 'そ': 0x0F,
    'た': 0x10, 'ち': 0x11, 'つ': 0x12, 'て': 0x13, 'と': 0x14,
    'な': 0x15, 'に': 0x16, 'ぬ': 0x17, 'ね': 0x18, 'の': 0x19,
    'は': 0x1A, 'ひ': 0x1B, 'ふ': 0x1C, 'へ': 0x1D, 'ほ': 0x1E,
    'ま': 0x1F, 'み': 0x20, 'む': 0x21, 'め': 0x22, 'も': 0x23,
    'や': 0x24, 'ゆ': 0x25, 'よ': 0x26,
    'ら': 0x27, 'り': 0x28, 'る': 0x29, 'れ': 0x2A, 'ろ': 0x2B,
    'わ': 0x2C, 'を': 0x2D, 'ん': 0x2E,
    'ぁ': 0x2F, 'ぃ': 0x30, 'ぅ': 0x31, 'ぇ': 0x32, 'ぉ': 0x33,
    'ゃ': 0x34, 'ゅ': 0x35, 'ょ': 0x36,
    'が': 0x37, 'ぎ': 0x38, 'ぐ': 0x39, 'げ': 0x3A, 'ご': 0x3B,
    'ざ': 0x3C, 'じ': 0x3D, 'ず': 0x3E, 'ぜ': 0x3F,	'ぞ': 0x40,
    'だ': 0x41, 'ぢ': 0x42, 'づ': 0x43, 'で': 0x44, 'ど': 0x45,
    'ば': 0x46, 'び': 0x47, 'ぶ': 0x48, 'べ': 0x49, 'ぼ': 0x4A,
    'ぱ': 0x4B, 'ぴ': 0x4C, 'ぷ': 0x4D, 'ぺ': 0x4E, 'ぽ': 0x4F,
    'っ': 0x50,
    'ア': 0x51, 'イ': 0x52, 'ウ': 0x53, 'エ': 0x54, 'オ': 0x55,
    'カ': 0x56, 'キ': 0x57, 'ク': 0x58, 'ケ': 0x59, 'コ': 0x5A,
    'サ': 0x5B, 'シ': 0x5C, 'ス': 0x5D, 'セ': 0x5E, 'ソ': 0x5F,
    'タ': 0x60, 'チ': 0x61, 'ツ': 0x62, 'テ': 0x63, 'ト': 0x64,
    'ナ': 0x65, 'ニ': 0x66, 'ヌ': 0x67, 'ネ': 0x68, 'ノ': 0x69,
    'ハ': 0x6A, 'ヒ': 0x6B, 'フ': 0x6C, 'ヘ': 0x6D, 'ホ': 0x6E,
    'マ': 0x6F, 'ミ': 0x70, 'ム': 0x71, 'メ': 0x72, 'モ': 0x73,	
    'ヤ': 0x74, 'ユ': 0x75, 'ヨ': 0x76,	
    'ラ': 0x77, 'リ': 0x78, 'ル': 0x79, 'レ': 0x7A, 'ロ': 0x7B,
    'ワ': 0x7C, 'ヲ': 0x7D, 'ン': 0x7E,
    'ァ': 0x7F, 'ィ': 0x80, 'ゥ': 0x81, 'ェ': 0x82, 'ォ': 0x83,	
    'ャ': 0x84, 'ュ': 0x85, 'ョ': 0x86,
    'ガ': 0x87, 'ギ': 0x88, 'グ': 0x89, 'ゲ': 0x8A, 'ゴ':0x8B,
    'ザ': 0x8C, 'ジ': 0x8D, 'ズ': 0x8E, 'ゼ': 0x8F, 'ゾ':0x90,
    'ダ': 0x91, 'ヂ': 0x92, 'ヅ': 0x93, 'デ': 0x94, 'ド':0x95,
    'バ': 0x96, 'ビ': 0x97, 'ブ': 0x98, 'ベ': 0x99, 'ボ':0x9A,
    'パ': 0x9B, 'ピ': 0x9C, 'プ': 0x9D, 'ペ': 0x9E, 'ポ':0x9F,
    'ッ': 0xA0,
    '０': 0xA1, '１': 0xA2, '２': 0xA3, '３': 0xA4, '４': 0xA5,
    '５': 0xA6, '６': 0xA7, '７': 0xA8, '８': 0xA9, '９': 0xAA,
    '!': 0xAB, '?': 0xAC, '。': 0xAD, 'ー': 0xAE, '・': 0xAF,
    '♂': 0xB5, '♀': 0xB6, '/': 0xBA,
    'A': 0xBB, 'B': 0xBC, 'C': 0xBD, 'D': 0xBE, 'E': 0xBF,
    'F': 0xC0, 'G': 0xC1, 'H': 0xC2, 'I': 0xC3, 'J': 0xC4,
    'K': 0xC5, 'L': 0xC6, 'M': 0xC7, 'N': 0xC8, 'O': 0xC9,
    'P': 0xCA, 'Q': 0xCB, 'R': 0xCC, 'S': 0xCD, 'T': 0xCE,
    'U': 0xCF, 'V': 0xD0, 'W': 0xD1, 'X': 0xD2, 'Y': 0xD3,
    'Z': 0xD4, 'a': 0xD5, 'b': 0xD6, 'c': 0xD7, 'd': 0xD8,
    'e': 0xD9, 'f': 0xDA, 'g': 0xDB, 'h': 0xDC, 'i': 0xDD,
    'j': 0xDE, 'k': 0xDF, 'l': 0xE0, 'm': 0xE1, 'n': 0xE2,
    'o': 0xE3, 'p': 0xE4, 'q': 0xE5, 'r': 0xE6, 's': 0xE7,
    't': 0xE8, 'u': 0xE9, 'v': 0xEA, 'w': 0xEB, 'x': 0xEC,
    'y': 0xED, 'z': 0xEE, 
}

# Reverse lookup for decoding
GEN3_CHAR_DECODE = {v: k for k, v in GEN3_CHAR_TABLE.items()}

# Data block permutations based on PID % 24
PERMUTATIONS = [
    [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2],
    [0, 2, 3, 1], [0, 3, 2, 1], [1, 0, 2, 3], [1, 0, 3, 2],
    [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
    [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2],
    [2, 3, 0, 1], [3, 2, 0, 1], [1, 2, 3, 0], [1, 3, 2, 0],
    [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0]
]

# Nature names (index = nature ID)
NATURE_NAMES = [
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky"
]

# Species name to National Dex ID mapping
SPECIES_NAME_TO_ID = {
    # Gen 1
    "Bulbasaur": 1, "Ivysaur": 2, "Venusaur": 3, "Charmander": 4, "Charmeleon": 5,
    "Charizard": 6, "Squirtle": 7, "Wartortle": 8, "Blastoise": 9, "Caterpie": 10,
    "Metapod": 11, "Butterfree": 12, "Weedle": 13, "Kakuna": 14, "Beedrill": 15,
    "Pidgey": 16, "Pidgeotto": 17, "Pidgeot": 18, "Rattata": 19, "Raticate": 20,
    "Spearow": 21, "Fearow": 22, "Ekans": 23, "Arbok": 24, "Pikachu": 25,
    "Raichu": 26, "Sandshrew": 27, "Sandslash": 28, "Nidoran♀": 29, "Nidorina": 30,
    "Nidoqueen": 31, "Nidoran♂": 32, "Nidorino": 33, "Nidoking": 34, "Clefairy": 35,
    "Clefable": 36, "Vulpix": 37, "Ninetales": 38, "Jigglypuff": 39, "Wigglytuff": 40,
    "Zubat": 41, "Golbat": 42, "Oddish": 43, "Gloom": 44, "Vileplume": 45,
    "Paras": 46, "Parasect": 47, "Venonat": 48, "Venomoth": 49, "Diglett": 50,
    "Dugtrio": 51, "Meowth": 52, "Persian": 53, "Psyduck": 54, "Golduck": 55,
    "Mankey": 56, "Primeape": 57, "Growlithe": 58, "Arcanine": 59, "Poliwag": 60,
    "Poliwhirl": 61, "Poliwrath": 62, "Abra": 63, "Kadabra": 64, "Alakazam": 65,
    "Machop": 66, "Machoke": 67, "Machamp": 68, "Bellsprout": 69, "Weepinbell": 70,
    "Victreebel": 71, "Tentacool": 72, "Tentacruel": 73, "Geodude": 74, "Graveler": 75,
    "Golem": 76, "Ponyta": 77, "Rapidash": 78, "Slowpoke": 79, "Slowbro": 80,
    "Magnemite": 81, "Magneton": 82, "Farfetch'd": 83, "Doduo": 84, "Dodrio": 85,
    "Seel": 86, "Dewgong": 87, "Grimer": 88, "Muk": 89, "Shellder": 90,
    "Cloyster": 91, "Gastly": 92, "Haunter": 93, "Gengar": 94, "Onix": 95,
    "Drowzee": 96, "Hypno": 97, "Krabby": 98, "Kingler": 99, "Voltorb": 100,
    "Electrode": 101, "Exeggcute": 102, "Exeggutor": 103, "Cubone": 104, "Marowak": 105,
    "Hitmonlee": 106, "Hitmonchan": 107, "Lickitung": 108, "Koffing": 109, "Weezing": 110,
    "Rhyhorn": 111, "Rhydon": 112, "Chansey": 113, "Tangela": 114, "Kangaskhan": 115,
    "Horsea": 116, "Seadra": 117, "Goldeen": 118, "Seaking": 119, "Staryu": 120,
    "Starmie": 121, "Mr. Mime": 122, "Scyther": 123, "Jynx": 124, "Electabuzz": 125,
    "Magmar": 126, "Pinsir": 127, "Tauros": 128, "Magikarp": 129, "Gyarados": 130,
    "Lapras": 131, "Ditto": 132, "Eevee": 133, "Vaporeon": 134, "Jolteon": 135,
    "Flareon": 136, "Porygon": 137, "Omanyte": 138, "Omastar": 139, "Kabuto": 140,
    "Kabutops": 141, "Aerodactyl": 142, "Snorlax": 143, "Articuno": 144, "Zapdos": 145,
    "Moltres": 146, "Dratini": 147, "Dragonair": 148, "Dragonite": 149, "Mewtwo": 150,
    "Mew": 151,
    # Gen 2
    "Chikorita": 152, "Bayleef": 153, "Meganium": 154, "Cyndaquil": 155, "Quilava": 156,
    "Typhlosion": 157, "Totodile": 158, "Croconaw": 159, "Feraligatr": 160, "Sentret": 161,
    "Furret": 162, "Hoothoot": 163, "Noctowl": 164, "Ledyba": 165, "Ledian": 166,
    "Spinarak": 167, "Ariados": 168, "Crobat": 169, "Chinchou": 170, "Lanturn": 171,
    "Pichu": 172, "Cleffa": 173, "Igglybuff": 174, "Togepi": 175, "Togetic": 176,
    "Natu": 177, "Xatu": 178, "Mareep": 179, "Flaaffy": 180, "Ampharos": 181,
    "Bellossom": 182, "Marill": 183, "Azumarill": 184, "Sudowoodo": 185, "Politoed": 186,
    "Hoppip": 187, "Skiploom": 188, "Jumpluff": 189, "Aipom": 190, "Sunkern": 191,
    "Sunflora": 192, "Yanma": 193, "Wooper": 194, "Quagsire": 195, "Espeon": 196,
    "Umbreon": 197, "Murkrow": 198, "Slowking": 199, "Misdreavus": 200, "Unown": 201,
    "Wobbuffet": 202, "Girafarig": 203, "Pineco": 204, "Forretress": 205, "Dunsparce": 206,
    "Gligar": 207, "Steelix": 208, "Snubbull": 209, "Granbull": 210, "Qwilfish": 211,
    "Scizor": 212, "Shuckle": 213, "Heracross": 214, "Sneasel": 215, "Teddiursa": 216,
    "Ursaring": 217, "Slugma": 218, "Magcargo": 219, "Swinub": 220, "Piloswine": 221,
    "Corsola": 222, "Remoraid": 223, "Octillery": 224, "Delibird": 225, "Mantine": 226,
    "Skarmory": 227, "Houndour": 228, "Houndoom": 229, "Kingdra": 230, "Phanpy": 231,
    "Donphan": 232, "Porygon2": 233, "Stantler": 234, "Smeargle": 235, "Tyrogue": 236,
    "Hitmontop": 237, "Smoochum": 238, "Elekid": 239, "Magby": 240, "Miltank": 241,
    "Blissey": 242, "Raikou": 243, "Entei": 244, "Suicune": 245, "Larvitar": 246,
    "Pupitar": 247, "Tyranitar": 248, "Lugia": 249, "Ho-Oh": 250, "Ho-oh": 250,
    "Celebi": 251,
    # Gen 3
    "Treecko": 252, "Grovyle": 253, "Sceptile": 254, "Torchic": 255, "Combusken": 256,
    "Blaziken": 257, "Mudkip": 258, "Marshtomp": 259, "Swampert": 260, "Poochyena": 261,
    "Mightyena": 262, "Zigzagoon": 263, "Linoone": 264, "Wurmple": 265, "Silcoon": 266,
    "Beautifly": 267, "Cascoon": 268, "Dustox": 269, "Lotad": 270, "Lombre": 271,
    "Ludicolo": 272, "Seedot": 273, "Nuzleaf": 274, "Shiftry": 275, "Taillow": 276,
    "Swellow": 277, "Wingull": 278, "Pelipper": 279, "Ralts": 280, "Kirlia": 281,
    "Gardevoir": 282, "Surskit": 283, "Masquerain": 284, "Shroomish": 285, "Breloom": 286,
    "Slakoth": 287, "Vigoroth": 288, "Slaking": 289, "Nincada": 290, "Ninjask": 291,
    "Shedinja": 292, "Whismur": 293, "Loudred": 294, "Exploud": 295, "Makuhita": 296,
    "Hariyama": 297, "Azurill": 298, "Nosepass": 299, "Skitty": 300, "Delcatty": 301,
    "Sableye": 302, "Mawile": 303, "Aron": 304, "Lairon": 305, "Aggron": 306,
    "Meditite": 307, "Medicham": 308, "Electrike": 309, "Manectric": 310, "Plusle": 311,
    "Minun": 312, "Volbeat": 313, "Illumise": 314, "Roselia": 315, "Gulpin": 316,
    "Swalot": 317, "Carvanha": 318, "Sharpedo": 319, "Wailmer": 320, "Wailord": 321,
    "Numel": 322, "Camerupt": 323, "Torkoal": 324, "Spoink": 325, "Grumpig": 326,
    "Spinda": 327, "Trapinch": 328, "Vibrava": 329, "Flygon": 330, "Cacnea": 331,
    "Cacturne": 332, "Swablu": 333, "Altaria": 334, "Zangoose": 335, "Seviper": 336,
    "Lunatone": 337, "Solrock": 338, "Barboach": 339, "Whiscash": 340, "Corphish": 341,
    "Crawdaunt": 342, "Baltoy": 343, "Claydol": 344, "Lileep": 345, "Cradily": 346,
    "Anorith": 347, "Armaldo": 348, "Feebas": 349, "Milotic": 350, "Castform": 351,
    "Kecleon": 352, "Shuppet": 353, "Banette": 354, "Duskull": 355, "Dusclops": 356,
    "Tropius": 357, "Chimecho": 358, "Absol": 359, "Wynaut": 360, "Snorunt": 361,
    "Glalie": 362, "Spheal": 363, "Sealeo": 364, "Walrein": 365, "Clamperl": 366,
    "Huntail": 367, "Gorebyss": 368, "Relicanth": 369, "Luvdisc": 370, "Bagon": 371,
    "Shelgon": 372, "Salamence": 373, "Beldum": 374, "Metang": 375, "Metagross": 376,
    "Regirock": 377, "Regice": 378, "Registeel": 379, "Latias": 380, "Latios": 381,
    "Kyogre": 382, "Groudon": 383, "Rayquaza": 384, "Jirachi": 385, "Deoxys": 386,
}

# National to Internal species ID conversion (for Hoenn Pokemon)
NATIONAL_TO_INTERNAL = {
    252: 277, 253: 278, 254: 279, 255: 280, 256: 281, 257: 282, 258: 283, 259: 284,
    260: 285, 261: 286, 262: 287, 263: 288, 264: 289, 265: 290, 266: 291, 267: 292,
    268: 293, 269: 294, 270: 295, 271: 296, 272: 297, 273: 298, 274: 299, 275: 300,
    276: 304, 277: 305, 278: 309, 279: 310, 280: 392, 281: 393, 282: 394, 283: 311,
    284: 312, 285: 306, 286: 307, 287: 364, 288: 365, 289: 366, 290: 301, 291: 302,
    292: 303, 293: 370, 294: 371, 295: 372, 296: 335, 297: 336, 298: 350, 299: 320,
    300: 315, 301: 316, 302: 322, 303: 355, 304: 382, 305: 383, 306: 384, 307: 356,
    308: 357, 309: 337, 310: 338, 311: 353, 312: 354, 313: 386, 314: 387, 315: 363,
    316: 367, 317: 368, 318: 330, 319: 331, 320: 313, 321: 314, 322: 339, 323: 340,
    324: 321, 325: 351, 326: 352, 327: 308, 328: 332, 329: 333, 330: 334, 331: 344,
    332: 345, 333: 358, 334: 359, 335: 380, 336: 379, 337: 348, 338: 349, 339: 323,
    340: 324, 341: 326, 342: 327, 343: 318, 344: 319, 345: 388, 346: 389, 347: 390,
    348: 391, 349: 328, 350: 329, 351: 385, 352: 317, 353: 377, 354: 378, 355: 361,
    356: 362, 357: 369, 358: 411, 359: 376, 360: 360, 361: 346, 362: 347, 363: 341,
    364: 342, 365: 343, 366: 373, 367: 374, 368: 375, 369: 381, 370: 325, 371: 395,
    372: 396, 373: 397, 374: 398, 375: 399, 376: 400, 377: 401, 378: 402, 379: 403,
    380: 407, 381: 408, 382: 404, 383: 405, 384: 406, 385: 409, 386: 410,
}

# Move name to ID mapping (Gen 3 moves)
MOVE_NAME_TO_ID = {
    "Pound": 1, "Karate Chop": 2, "Double Slap": 3, "Comet Punch": 4, "Mega Punch": 5,
    "Pay Day": 6, "Fire Punch": 7, "Ice Punch": 8, "Thunder Punch": 9, "Scratch": 10,
    "Vice Grip": 11, "Guillotine": 12, "Razor Wind": 13, "Swords Dance": 14, "Cut": 15,
    "Gust": 16, "Wing Attack": 17, "Whirlwind": 18, "Fly": 19, "Bind": 20,
    "Slam": 21, "Vine Whip": 22, "Stomp": 23, "Double Kick": 24, "Mega Kick": 25,
    "Jump Kick": 26, "Rolling Kick": 27, "Sand Attack": 28, "Headbutt": 29, "Horn Attack": 30,
    "Fury Attack": 31, "Horn Drill": 32, "Tackle": 33, "Body Slam": 34, "Wrap": 35,
    "Take Down": 36, "Thrash": 37, "Double-Edge": 38, "Tail Whip": 39, "Poison Sting": 40,
    "Twineedle": 41, "Pin Missile": 42, "Leer": 43, "Bite": 44, "Growl": 45,
    "Roar": 46, "Sing": 47, "Supersonic": 48, "Sonic Boom": 49, "Disable": 50,
    "Acid": 51, "Ember": 52, "Flamethrower": 53, "Mist": 54, "Water Gun": 55,
    "Hydro Pump": 56, "Surf": 57, "Ice Beam": 58, "Blizzard": 59, "Psybeam": 60,
    "Bubble Beam": 61, "Aurora Beam": 62, "Hyper Beam": 63, "Peck": 64, "Drill Peck": 65,
    "Submission": 66, "Low Kick": 67, "Counter": 68, "Seismic Toss": 69, "Strength": 70,
    "Absorb": 71, "Mega Drain": 72, "Leech Seed": 73, "Growth": 74, "Razor Leaf": 75,
    "Solar Beam": 76, "Poison Powder": 77, "Stun Spore": 78, "Sleep Powder": 79, "Petal Dance": 80,
    "String Shot": 81, "Dragon Rage": 82, "Fire Spin": 83, "Thunder Shock": 84, "Thunderbolt": 85,
    "Thunder Wave": 86, "Thunder": 87, "Rock Throw": 88, "Earthquake": 89, "Fissure": 90,
    "Dig": 91, "Toxic": 92, "Confusion": 93, "Psychic": 94, "Hypnosis": 95,
    "Meditate": 96, "Agility": 97, "Quick Attack": 98, "Rage": 99, "Teleport": 100,
    "Night Shade": 101, "Mimic": 102, "Screech": 103, "Double Team": 104, "Recover": 105,
    "Harden": 106, "Minimize": 107, "Smokescreen": 108, "Confuse Ray": 109, "Withdraw": 110,
    "Defense Curl": 111, "Barrier": 112, "Light Screen": 113, "Haze": 114, "Reflect": 115,
    "Focus Energy": 116, "Bide": 117, "Metronome": 118, "Mirror Move": 119, "Self-Destruct": 120,
    "Egg Bomb": 121, "Lick": 122, "Smog": 123, "Sludge": 124, "Bone Club": 125,
    "Fire Blast": 126, "Waterfall": 127, "Clamp": 128, "Swift": 129, "Skull Bash": 130,
    "Spike Cannon": 131, "Constrict": 132, "Amnesia": 133, "Kinesis": 134, "Soft-Boiled": 135,
    "High Jump Kick": 136, "Glare": 137, "Dream Eater": 138, "Poison Gas": 139, "Barrage": 140,
    "Leech Life": 141, "Lovely Kiss": 142, "Sky Attack": 143, "Transform": 144, "Bubble": 145,
    "Dizzy Punch": 146, "Spore": 147, "Flash": 148, "Psywave": 149, "Splash": 150,
    "Acid Armor": 151, "Crabhammer": 152, "Explosion": 153, "Fury Swipes": 154, "Bonemerang": 155,
    "Rest": 156, "Rock Slide": 157, "Hyper Fang": 158, "Sharpen": 159, "Conversion": 160,
    "Tri Attack": 161, "Super Fang": 162, "Slash": 163, "Substitute": 164, "Struggle": 165,
    "Sketch": 166, "Triple Kick": 167, "Thief": 168, "Spider Web": 169, "Mind Reader": 170,
    "Nightmare": 171, "Flame Wheel": 172, "Snore": 173, "Curse": 174, "Flail": 175,
    "Conversion 2": 176, "Aeroblast": 177, "Cotton Spore": 178, "Reversal": 179, "Spite": 180,
    "Powder Snow": 181, "Protect": 182, "Mach Punch": 183, "Scary Face": 184, "Faint Attack": 185,
    "Sweet Kiss": 186, "Belly Drum": 187, "Sludge Bomb": 188, "Mud-Slap": 189, "Octazooka": 190,
    "Spikes": 191, "Zap Cannon": 192, "Foresight": 193, "Destiny Bond": 194, "Perish Song": 195,
    "Icy Wind": 196, "Detect": 197, "Bone Rush": 198, "Lock-On": 199, "Outrage": 200,
    "Sandstorm": 201, "Giga Drain": 202, "Endure": 203, "Charm": 204, "Rollout": 205,
    "False Swipe": 206, "Swagger": 207, "Milk Drink": 208, "Spark": 209, "Fury Cutter": 210,
    "Steel Wing": 211, "Mean Look": 212, "Attract": 213, "Sleep Talk": 214, "Heal Bell": 215,
    "Return": 216, "Present": 217, "Frustration": 218, "Safeguard": 219, "Pain Split": 220,
    "Sacred Fire": 221, "Magnitude": 222, "Dynamic Punch": 223, "Megahorn": 224, "Dragon Breath": 225,
    "Baton Pass": 226, "Encore": 227, "Pursuit": 228, "Rapid Spin": 229, "Sweet Scent": 230,
    "Iron Tail": 231, "Metal Claw": 232, "Vital Throw": 233, "Morning Sun": 234, "Synthesis": 235,
    "Moonlight": 236, "Hidden Power": 237, "Cross Chop": 238, "Twister": 239, "Rain Dance": 240,
    "Sunny Day": 241, "Crunch": 242, "Mirror Coat": 243, "Psych Up": 244, "Extreme Speed": 245,
    "Ancient Power": 246, "Shadow Ball": 247, "Future Sight": 248, "Rock Smash": 249, "Whirlpool": 250,
    "Beat Up": 251, "Fake Out": 252, "Uproar": 253, "Stockpile": 254, "Spit Up": 255,
    "Swallow": 256, "Heat Wave": 257, "Hail": 258, "Torment": 259, "Flatter": 260,
    "Will-O-Wisp": 261, "Memento": 262, "Facade": 263, "Focus Punch": 264, "Smelling Salts": 265,
    "Follow Me": 266, "Nature Power": 267, "Charge": 268, "Taunt": 269, "Helping Hand": 270,
    "Trick": 271, "Role Play": 272, "Wish": 273, "Assist": 274, "Ingrain": 275,
    "Superpower": 276, "Magic Coat": 277, "Recycle": 278, "Revenge": 279, "Brick Break": 280,
    "Yawn": 281, "Knock Off": 282, "Endeavor": 283, "Eruption": 284, "Skill Swap": 285,
    "Imprison": 286, "Refresh": 287, "Grudge": 288, "Snatch": 289, "Secret Power": 290,
    "Dive": 291, "Arm Thrust": 292, "Camouflage": 293, "Tail Glow": 294, "Luster Purge": 295,
    "Mist Ball": 296, "Feather Dance": 297, "Teeter Dance": 298, "Blaze Kick": 299, "Mud Sport": 300,
    "Ice Ball": 301, "Needle Arm": 302, "Slack Off": 303, "Hyper Voice": 304, "Poison Fang": 305,
    "Crush Claw": 306, "Blast Burn": 307, "Hydro Cannon": 308, "Meteor Mash": 309, "Astonish": 310,
    "Weather Ball": 311, "Aromatherapy": 312, "Fake Tears": 313, "Air Cutter": 314, "Overheat": 315,
    "Odor Sleuth": 316, "Rock Tomb": 317, "Silver Wind": 318, "Metal Sound": 319, "Grass Whistle": 320,
    "Tickle": 321, "Cosmic Power": 322, "Water Spout": 323, "Signal Beam": 324, "Shadow Punch": 325,
    "Extrasensory": 326, "Sky Uppercut": 327, "Sand Tomb": 328, "Sheer Cold": 329, "Muddy Water": 330,
    "Bullet Seed": 331, "Aerial Ace": 332, "Icicle Spear": 333, "Iron Defense": 334, "Block": 335,
    "Howl": 336, "Dragon Claw": 337, "Frenzy Plant": 338, "Bulk Up": 339, "Bounce": 340,
    "Mud Shot": 341, "Poison Tail": 342, "Covet": 343, "Volt Tackle": 344, "Magical Leaf": 345,
    "Water Sport": 346, "Calm Mind": 347, "Leaf Blade": 348, "Dragon Dance": 349, "Rock Blast": 350,
    "Shock Wave": 351, "Water Pulse": 352, "Doom Desire": 353, "Psycho Boost": 354,
}

# Item name to ID mapping
ITEM_NAME_TO_ID = {
    "None": 0, "Master Ball": 1, "Ultra Ball": 2, "Great Ball": 3, "Poké Ball": 4, "Poke Ball": 4,
    "Safari Ball": 5, "Net Ball": 6, "Dive Ball": 7, "Nest Ball": 8, "Repeat Ball": 9,
    "Timer Ball": 10, "Luxury Ball": 11, "Premier Ball": 12,
    "Oran Berry": 139, "Sitrus Berry": 142, "Lum Berry": 141, "Leppa Berry": 138,
    "Cheri Berry": 133, "Chesto Berry": 134, "Pecha Berry": 135, "Rawst Berry": 136,
    "Aspear Berry": 137, "Persim Berry": 140,
    "Leftovers": 200, "Shell Bell": 219, "Focus Band": 196, "King's Rock": 187,
    "Quick Claw": 183, "Bright Powder": 179, "Choice Band": 186,
    "Soul Dew": 191,  # Special Latios/Latias item
}

# Location name to ID mapping
LOCATION_NAME_TO_ID = {
    "Fateful Encounter": 255,
    "Faraway Island": 201,
    "Navel Rock": 211,
    "Birth Island": 200,
    "Altering Cave": 210,  # Emerald
    "Altering Cave RSE": 183,  # RSE
    "Sinew Labs": 255,  # Custom - use Fateful Encounter
    "Southern Island": 57,
    "Sky Pillar": 87,
    "Cave of Origin": 37,
}

# Species gender ratios (255 = genderless, 254 = always female, 0 = always male)
SPECIES_GENDER_RATIO = {
    # Genderless Pokemon
    81: 255, 82: 255, 100: 255, 101: 255, 120: 255, 121: 255, 132: 255, 137: 255,
    233: 255, 201: 255, 243: 255, 244: 255, 245: 255, 249: 255, 250: 255, 251: 255,
    343: 255, 344: 255, 374: 255, 375: 255, 376: 255, 377: 255, 378: 255, 379: 255,
    382: 255, 383: 255, 384: 255, 385: 255, 386: 255,
    # Mew, Celebi, Jirachi, Deoxys
    151: 255,
    # Always female
    29: 254, 30: 254, 31: 254, 113: 254, 115: 254, 124: 254, 238: 254, 241: 254, 242: 254, 314: 254,
    # Always male  
    32: 0, 33: 0, 34: 0, 106: 0, 107: 0, 128: 0, 236: 0, 237: 0, 313: 0,
}

# Default base friendships by species (most mythicals have 100)
SPECIES_BASE_FRIENDSHIP = {
    151: 100,  # Mew
    251: 100,  # Celebi
    385: 100,  # Jirachi
    386: 0,    # Deoxys
    249: 0,    # Lugia
    250: 0,    # Ho-Oh
}

# Experience growth rates
GROWTH_RATES = {
    "slow": {
        151: True, 249: True, 250: True, 251: True, 
        377: True, 378: True, 379: True, 380: True, 381: True,
        382: True, 383: True, 384: True, 385: True, 386: True,
    }
}

# Experience tables
EXP_SLOW = [
    0, 10, 33, 80, 156, 270, 428, 640, 911, 1250,
    1663, 2160, 2746, 3430, 4218, 5120, 6141, 7290, 8573, 10000,
    11576, 13310, 15208, 17280, 19531, 21970, 24603, 27440, 30486, 33750,
    37238, 40960, 44921, 49130, 53593, 58320, 63316, 68590, 74148, 80000,
    86151, 92610, 99383, 106480, 113906, 121670, 129778, 138240, 147061, 156250,
    165813, 175760, 186096, 196830, 207968, 219520, 231491, 243890, 256723,
    270000, 283726, 297910, 312558, 327680, 343281, 359370, 375953, 393040,
    410636, 428750, 447388, 466560, 486271, 506530, 527343, 548720, 570666,
    593190, 616298, 640000, 664301, 689210, 714733, 740880, 767656, 795070,
    823128, 851840, 881211, 911250, 941963, 973360, 1005446, 1038230, 1071718,
    1105920, 1140841, 1176490, 1212873, 1250000
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


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def encode_gen3_text(text: str, max_length: int = 10) -> bytes:
    """Encode a string to Gen 3 format with 0xFF terminator."""
    result = bytearray()
    for char in text[:max_length]:
        if char in GEN3_CHAR_TABLE:
            result.append(GEN3_CHAR_TABLE[char])
        else:
            # Skip unknown characters
            pass
    
    # Pad with 0xFF (terminator)
    while len(result) < max_length:
        result.append(0xFF)
    
    return bytes(result)


def get_species_id(species: Union[str, int]) -> int:
    """Convert species name or ID to internal ID."""
    if isinstance(species, int):
        national_id = species
    else:
        national_id = SPECIES_NAME_TO_ID.get(species, 0)
        if national_id == 0:
            # Try case-insensitive lookup
            for name, sid in SPECIES_NAME_TO_ID.items():
                if name.lower() == species.lower():
                    national_id = sid
                    break
    
    # Convert to internal ID if Hoenn Pokemon
    if national_id >= 252:
        return NATIONAL_TO_INTERNAL.get(national_id, national_id)
    return national_id


def get_move_id(move: Union[str, int]) -> int:
    """Convert move name or ID to move ID."""
    if isinstance(move, int):
        return move
    
    move_id = MOVE_NAME_TO_ID.get(move, 0)
    if move_id == 0:
        # Try case-insensitive lookup
        for name, mid in MOVE_NAME_TO_ID.items():
            if name.lower() == move.lower():
                return mid
    return move_id


def get_item_id(item: Union[str, int]) -> int:
    """Convert item name or ID to item ID."""
    if isinstance(item, int):
        return item
    
    item_id = ITEM_NAME_TO_ID.get(item, 0)
    if item_id == 0:
        # Try case-insensitive lookup
        for name, iid in ITEM_NAME_TO_ID.items():
            if name.lower() == item.lower():
                return iid
    return item_id


def get_location_id(location: Union[str, int]) -> int:
    """Convert location name or ID to location ID."""
    if isinstance(location, int):
        return location
    
    loc_id = LOCATION_NAME_TO_ID.get(location, 255)
    if loc_id == 255 and location not in LOCATION_NAME_TO_ID:
        # Try case-insensitive lookup
        for name, lid in LOCATION_NAME_TO_ID.items():
            if name.lower() == location.lower():
                return lid
    return loc_id


def get_nature_id(nature: Union[str, int]) -> int:
    """Convert nature name or ID to nature ID."""
    if isinstance(nature, int):
        return nature % 25
    
    if nature.upper() == "RANDOM":
        return random.randint(0, 24)
    
    for i, name in enumerate(NATURE_NAMES):
        if name.lower() == nature.lower():
            return i
    
    return 0  # Default to Hardy


def get_exp_for_level(species_id: int, level: int) -> int:
    """Get the experience needed for a given level."""
    national_id = species_id
    # Convert internal to national if needed
    if species_id >= 277:
        for nat, internal in NATIONAL_TO_INTERNAL.items():
            if internal == species_id:
                national_id = nat
                break
    
    # Check growth rate
    if national_id in GROWTH_RATES.get("slow", {}):
        table = EXP_SLOW
    else:
        table = EXP_MEDIUM_SLOW
    
    if level < 1:
        return 0
    if level > 100:
        level = 100
    
    return table[level - 1] if level <= len(table) else table[-1]


def generate_pid_for_nature_shiny(
    nature_id: int,
    trainer_id: int,
    secret_id: int,
    shiny: bool = False,
    gender_ratio: int = 127
) -> int:
    """
    Generate a PID that matches the desired nature and shiny status.
    
    For shiny: (TID ^ SID ^ PID_high ^ PID_low) < 8
    For nature: PID % 25 == nature_id
    """
    max_attempts = 10000
    
    for _ in range(max_attempts):
        # Generate random PID
        pid = random.randint(0, 0xFFFFFFFF)
        
        # Adjust for nature
        current_nature = pid % 25
        if current_nature != nature_id:
            # Adjust PID to match nature while keeping other properties
            adjustment = (nature_id - current_nature) % 25
            pid = (pid // 25) * 25 + nature_id
            if pid > 0xFFFFFFFF:
                pid -= 25
        
        # Check shiny status
        pid_low = pid & 0xFFFF
        pid_high = (pid >> 16) & 0xFFFF
        shiny_value = trainer_id ^ secret_id ^ pid_low ^ pid_high
        is_shiny = shiny_value < 8
        
        if shiny == is_shiny:
            return pid
        
        # If we need shiny but got non-shiny, try to make it shiny
        if shiny and not is_shiny:
            # Manipulate PID high to make shiny while preserving nature
            target_xor = random.randint(0, 7)
            new_pid_high = trainer_id ^ secret_id ^ pid_low ^ target_xor
            new_pid = (new_pid_high << 16) | pid_low
            
            # Check if nature is still correct
            if new_pid % 25 == nature_id:
                return new_pid
    
    # Fallback - just return a PID with correct nature
    base_pid = random.randint(0, 0xFFFFFFFF)
    return (base_pid // 25) * 25 + nature_id


def calculate_checksum(data: bytes) -> int:
    """Calculate 16-bit checksum of decrypted Pokemon data."""
    checksum = 0
    for i in range(0, len(data), 2):
        word = struct.unpack('<H', data[i:i+2])[0]
        checksum = (checksum + word) & 0xFFFF
    return checksum


def encrypt_pokemon_data(decrypted: bytes, pid: int, ot_id: int) -> bytes:
    """Encrypt the 48-byte Pokemon substructure data."""
    key = pid ^ ot_id
    encrypted = bytearray(len(decrypted))
    
    for i in range(0, len(decrypted), 4):
        chunk = struct.unpack('<I', decrypted[i:i+4])[0]
        encrypted_chunk = chunk ^ key
        struct.pack_into('<I', encrypted, i, encrypted_chunk)
    
    return bytes(encrypted)


# =============================================================================
# MAIN GENERATOR CLASS
# =============================================================================

class PokemonGenerator:
    """
    Generates valid Gen 3 Pokemon byte data from recipe specifications.
    """
    
    # Default trainer info for "Sinew" Pokemon
    DEFAULT_TRAINER_ID = 31337
    DEFAULT_SECRET_ID = 1337
    DEFAULT_TRAINER_NAME = "Sinew"
    
    def __init__(self):
        self.recipes = {}
        self._load_recipes()
    
    def _load_recipes(self):
        """Load recipes from rewards.json if available."""
        try:
            # Try multiple paths
            paths = [
                os.path.join(os.path.dirname(__file__), "data", "achievements", "rewards", "rewards.json"),
                os.path.join(os.path.dirname(__file__), "rewards.json"),
                "data/achievements/rewards/rewards.json",
                "rewards.json",
            ]
            
            for path in paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        data = json.load(f)
                        # Use achievement ID as key if present, otherwise use species name
                        # This prevents duplicate species from overwriting each other
                        self.recipes = {}
                        for r in data.get('rewards', []):
                            key = r.get('achievement') or r.get('species', '')
                            self.recipes[key] = r
                        print(f"[PokemonGenerator] Loaded {len(self.recipes)} recipes from {path}")
                        return
                        
        except Exception as e:
            print(f"[PokemonGenerator] Could not load recipes: {e}")
            self.recipes = {}
    
    def generate_pokemon(self, recipe: Dict) -> Tuple[bytes, Dict]:
        """
        Generate a Pokemon from a recipe specification.
        
        Args:
            recipe: Dict containing Pokemon specifications
            
        Returns:
            Tuple of (80-byte Pokemon data, parsed Pokemon dict)
        """
        # Extract recipe fields with defaults
        species_name = recipe.get('species', 'Mew')
        level = recipe.get('level', 5)
        nature_spec = recipe.get('nature', 'RANDOM')
        moves = recipe.get('moves', [])
        iv_spec = recipe.get('ivs', {'min': 0, 'max': 31})
        ot_name = recipe.get('ot', self.DEFAULT_TRAINER_NAME)
        met_location = recipe.get('met_location', 'Fateful Encounter')
        held_item = recipe.get('held_item', None)
        shiny = recipe.get('shiny', False)
        ball = recipe.get('ball', 'Poke Ball')
        gender = recipe.get('gender', 'RANDOM')
        ability_slot = recipe.get('ability', 0)  # 0 = slot 1, 1 = slot 2
        friendship = recipe.get('friendship', None)
        language = recipe.get('language', 'ENG')
        
        # Convert names to IDs
        species_id = get_species_id(species_name)
        if species_id == 0:
            raise ValueError(f"Unknown species: {species_name}")
        
        # Get national ID for lookups
        national_id = species_id
        if species_id >= 277:
            for nat, internal in NATIONAL_TO_INTERNAL.items():
                if internal == species_id:
                    national_id = nat
                    break
        
        nature_id = get_nature_id(nature_spec)
        location_id = get_location_id(met_location)
        ball_id = get_item_id(ball)
        if ball_id == 0:
            ball_id = 4  # Default to Poke Ball
        
        # Generate IVs
        iv_min = iv_spec.get('min', 0)
        iv_max = iv_spec.get('max', 31)
        ivs = {
            'hp': random.randint(iv_min, iv_max),
            'attack': random.randint(iv_min, iv_max),
            'defense': random.randint(iv_min, iv_max),
            'speed': random.randint(iv_min, iv_max),
            'sp_attack': random.randint(iv_min, iv_max),
            'sp_defense': random.randint(iv_min, iv_max),
        }
        
        # Generate trainer IDs
        trainer_id = self.DEFAULT_TRAINER_ID
        secret_id = self.DEFAULT_SECRET_ID
        ot_id = (secret_id << 16) | trainer_id
        
        # Generate PID with correct nature and shiny status
        gender_ratio = SPECIES_GENDER_RATIO.get(national_id, 127)
        pid = generate_pid_for_nature_shiny(nature_id, trainer_id, secret_id, shiny, gender_ratio)
        
        # Calculate experience for level
        exp = get_exp_for_level(species_id, level)
        
        # Get base friendship
        if friendship is None:
            friendship = SPECIES_BASE_FRIENDSHIP.get(national_id, 70)
        
        # Convert move names to IDs
        move_ids = []
        for move in moves[:4]:
            move_id = get_move_id(move)
            if move_id > 0:
                move_ids.append(move_id)
        
        # Pad to 4 moves
        while len(move_ids) < 4:
            move_ids.append(0)
        
        # Get held item ID
        held_item_id = get_item_id(held_item) if held_item else 0
        
        # Build the 80-byte Pokemon structure
        pokemon_bytes = self._build_pokemon_bytes(
            pid=pid,
            ot_id=ot_id,
            species_id=species_id,
            held_item_id=held_item_id,
            exp=exp,
            friendship=friendship,
            move_ids=move_ids,
            ivs=ivs,
            ability_slot=ability_slot,
            location_id=location_id,
            level=level,
            ball_id=ball_id,
            ot_name=ot_name,
            nickname=species_name.upper()[:10],
            language=language,
        )
        
        # Build parsed Pokemon dict for display (use NATIONAL ID for Sinew)
        pokemon_dict = {
            'species': national_id,  # National dex ID for sprite lookup
            'species_name': species_name,
            'nickname': species_name.upper()[:10],
            'level': level,
            'experience': exp,
            'nature': nature_id,
            'personality': pid,
            'ot_id': ot_id,
            'ot_name': ot_name,
            'ivs': ivs,
            'evs': {'hp': 0, 'attack': 0, 'defense': 0, 'speed': 0, 'sp_attack': 0, 'sp_defense': 0},
            'moves': [{'id': m, 'pp': 0} for m in move_ids if m > 0],
            'held_item': held_item_id,
            'met_location': location_id,
            'is_shiny': shiny,
            'friendship': friendship,
            'pokeball': ball_id,
            'ability_num': ability_slot,
            'raw_bytes': pokemon_bytes,
            'empty': False,
        }
        
        return pokemon_bytes, pokemon_dict
    
    def _build_pokemon_bytes(
        self,
        pid: int,
        ot_id: int,
        species_id: int,
        held_item_id: int,
        exp: int,
        friendship: int,
        move_ids: List[int],
        ivs: Dict[str, int],
        ability_slot: int,
        location_id: int,
        level: int,
        ball_id: int,
        ot_name: str,
        nickname: str,
        language: str = 'ENG',
    ) -> bytes:
        """
        Build the 80-byte Pokemon structure.
        
        Gen 3 Box Pokemon Structure (80 bytes):
        - 0-3: Personality Value (PID)
        - 4-7: Original Trainer ID (OT ID)
        - 8-17: Nickname (10 bytes)
        - 18-19: Language
        - 20-26: OT Name (7 bytes)
        - 27: Markings
        - 28-29: Checksum
        - 30-31: Padding
        - 32-79: Encrypted data (48 bytes - 4 substructures of 12 bytes each)
        """
        data = bytearray(80)
        
        # Header
        struct.pack_into('<I', data, 0, pid)      # PID
        struct.pack_into('<I', data, 4, ot_id)    # OT ID
        
        # Nickname (10 bytes, Gen 3 encoded)
        nickname_bytes = encode_gen3_text(nickname, 10)
        data[8:18] = nickname_bytes
        
        # Language (2 bytes)
        lang_codes = {'JPN': 0x0201, 'ENG': 0x0202, 'FRE': 0x0203, 'ITA': 0x0204, 'GER': 0x0205, 'SPA': 0x0207}
        lang_code = lang_codes.get(language.upper(), 0x0202)
        struct.pack_into('<H', data, 18, lang_code)
        
        # OT Name (7 bytes)
        ot_bytes = encode_gen3_text(ot_name, 7)
        data[20:27] = ot_bytes
        
        # Markings (1 byte) - none
        data[27] = 0
        
        # Build substructures (each 12 bytes)
        # G = Growth, A = Attacks, E = EVs/Condition, M = Misc
        
        # Growth substructure (12 bytes)
        growth = bytearray(12)
        struct.pack_into('<H', growth, 0, species_id)      # Species
        struct.pack_into('<H', growth, 2, held_item_id)    # Held item
        struct.pack_into('<I', growth, 4, exp)             # Experience
        growth[8] = 0                                       # PP bonuses
        growth[9] = friendship                              # Friendship
        growth[10] = 0                                      # Unknown
        growth[11] = 0                                      # Unknown
        
        # Attacks substructure (12 bytes)
        attacks = bytearray(12)
        for i, move_id in enumerate(move_ids[:4]):
            struct.pack_into('<H', attacks, i * 2, move_id)
        # PP values (4 bytes) - calculate based on moves
        # For simplicity, use max PP (will be recalculated when deposited)
        pp_values = [35, 35, 35, 35]  # Default PP
        for i in range(4):
            attacks[8 + i] = pp_values[i] if move_ids[i] > 0 else 0
        
        # EVs/Condition substructure (12 bytes)
        evs = bytearray(12)
        # EVs (6 bytes) - all 0 for newly generated Pokemon
        evs[0] = 0  # HP EV
        evs[1] = 0  # Attack EV
        evs[2] = 0  # Defense EV
        evs[3] = 0  # Speed EV
        evs[4] = 0  # Sp.Atk EV
        evs[5] = 0  # Sp.Def EV
        # Contest stats (6 bytes) - all 0
        evs[6:12] = bytes(6)
        
        # Misc substructure (12 bytes)
        misc = bytearray(12)
        misc[0] = 0                    # Pokerus
        misc[1] = location_id          # Met location
        
        # Origins info (2 bytes): met level (7 bits), game (4 bits), ball (4 bits), OT gender (1 bit)
        met_level = min(level, 100)
        game_of_origin = 1  # Emerald
        ot_gender = 0       # Male trainer
        origins = (met_level & 0x7F) | ((game_of_origin & 0xF) << 7) | ((ball_id & 0xF) << 11) | ((ot_gender & 0x1) << 15)
        struct.pack_into('<H', misc, 2, origins)
        
        # IV/Egg/Ability (4 bytes)
        iv_egg = 0
        iv_egg |= (ivs['hp'] & 0x1F)
        iv_egg |= (ivs['attack'] & 0x1F) << 5
        iv_egg |= (ivs['defense'] & 0x1F) << 10
        iv_egg |= (ivs['speed'] & 0x1F) << 15
        iv_egg |= (ivs['sp_attack'] & 0x1F) << 20
        iv_egg |= (ivs['sp_defense'] & 0x1F) << 25
        iv_egg |= (0 & 0x1) << 30              # Egg flag
        iv_egg |= (ability_slot & 0x1) << 31   # Ability slot
        struct.pack_into('<I', misc, 4, iv_egg)
        
        # Ribbons/Obedience (4 bytes)
        ribbons = 0
        struct.pack_into('<I', misc, 8, ribbons)
        
        # Arrange substructures based on PID
        perm_index = pid % 24
        order = PERMUTATIONS[perm_index]
        
        # Format: order[TYPE] = POSITION
        # order[0] = position where Growth goes, order[1] = position where Attacks goes, etc.
        substructs = [growth, attacks, evs, misc]  # indexed by type
        arranged = bytearray(48)
        for type_idx, position in enumerate(order):
            arranged[position * 12:(position + 1) * 12] = substructs[type_idx]
        
        # Calculate checksum before encryption
        checksum = calculate_checksum(bytes(arranged))
        struct.pack_into('<H', data, 28, checksum)
        
        # Padding
        struct.pack_into('<H', data, 30, 0)
        
        # Encrypt and store
        encrypted = encrypt_pokemon_data(bytes(arranged), pid, ot_id)
        data[32:80] = encrypted
        
        return bytes(data)
    
    def generate_for_achievement(self, achievement_id: str) -> Optional[Tuple[bytes, Dict]]:
        """Generate a Pokemon for a specific achievement reward."""
        # First try direct lookup (key is achievement ID)
        if achievement_id in self.recipes:
            return self.generate_pokemon(self.recipes[achievement_id])
        
        # Fallback: search through recipes
        for key, recipe in self.recipes.items():
            if recipe.get('achievement') == achievement_id:
                return self.generate_pokemon(recipe)
        
        return None
    
    def generate_for_echo(self, species_name: str) -> Optional[Tuple[bytes, Dict]]:
        """Generate a Pokemon for the Echo (Altering Cave) system."""
        # Find recipe by species name with echo delivery
        for species, recipe in self.recipes.items():
            if recipe.get('species', '').lower() == species_name.lower():
                if recipe.get('delivery') == 'echo':
                    return self.generate_pokemon(recipe)
        
        # If not found in recipes, try to generate a basic version
        if species_name in SPECIES_NAME_TO_ID:
            basic_recipe = {
                'species': species_name,
                'level': 30,
                'nature': 'RANDOM',
                'moves': [],
                'ivs': {'min': 0, 'max': 31},
                'ot': 'Sinew',
                'met_location': 'Altering Cave',
                'delivery': 'echo',
            }
            return self.generate_pokemon(basic_recipe)
        
        return None
    
    def get_echo_pokemon_list(self) -> List[Dict]:
        """Get list of available Echo Pokemon."""
        echo_pokemon = []
        for species, recipe in self.recipes.items():
            if recipe.get('delivery') == 'echo':
                national_id = SPECIES_NAME_TO_ID.get(recipe.get('species', ''), 0)
                echo_pokemon.append({
                    'species': national_id,
                    'name': recipe.get('species', ''),
                })
        return echo_pokemon


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

_generator_instance = None

def get_pokemon_generator() -> PokemonGenerator:
    """Get or create the singleton Pokemon generator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = PokemonGenerator()
    return _generator_instance


def generate_pokemon_from_recipe(recipe: Dict) -> Tuple[bytes, Dict]:
    """Generate a Pokemon from a recipe specification."""
    return get_pokemon_generator().generate_pokemon(recipe)


def generate_achievement_pokemon(achievement_id: str) -> Optional[Tuple[bytes, Dict]]:
    """Generate a Pokemon for an achievement reward."""
    return get_pokemon_generator().generate_for_achievement(achievement_id)


def generate_echo_pokemon(species_name: str) -> Optional[Tuple[bytes, Dict]]:
    """Generate a Pokemon for the Echo system."""
    return get_pokemon_generator().generate_for_echo(species_name)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    # Test generation
    gen = PokemonGenerator()
    
    test_recipe = {
        'species': 'Jirachi',
        'level': 5,
        'nature': 'RANDOM',
        'moves': ['Wish', 'Confusion', 'Rest'],
        'ivs': {'min': 0, 'max': 31},
        'ot': 'Sinew',
        'met_location': 'Fateful Encounter',
    }
    
    pokemon_bytes, pokemon_dict = gen.generate_pokemon(test_recipe)
    
    print(f"Generated {pokemon_dict['species_name']} (ID: {pokemon_dict['species']})")
    print(f"Level: {pokemon_dict['level']}")
    print(f"Nature: {NATURE_NAMES[pokemon_dict['nature']]}")
    print(f"Shiny: {pokemon_dict['is_shiny']}")
    print(f"IVs: {pokemon_dict['ivs']}")
    print(f"Raw bytes length: {len(pokemon_bytes)}")
    print(f"First 8 bytes (PID, OT_ID): {pokemon_bytes[:8].hex()}")