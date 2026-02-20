"""
Gen 3 Pokemon Save Parser - Items Module
Handles parsing of bag items and inventory
"""

import struct
from .constants import OFFSETS_FRLG, OFFSETS_RS, OFFSETS_E


# Item name database
ITEM_NAMES = {
    0: "None",
    1: "Master Ball", 2: "Ultra Ball", 3: "Great Ball", 4: "Poké Ball",
    5: "Safari Ball", 6: "Net Ball", 7: "Dive Ball", 8: "Nest Ball",
    9: "Repeat Ball", 10: "Timer Ball", 11: "Luxury Ball", 12: "Premier Ball",
    13: "Potion", 14: "Antidote", 15: "Burn Heal", 16: "Ice Heal",
    17: "Awakening", 18: "Paralyze Heal", 19: "Full Restore", 20: "Max Potion",
    21: "Hyper Potion", 22: "Super Potion", 23: "Full Heal", 24: "Revive",
    25: "Max Revive", 26: "Fresh Water", 27: "Soda Pop", 28: "Lemonade",
    29: "Moomoo Milk", 30: "Energy Powder", 31: "Energy Root", 32: "Heal Powder",
    33: "Revival Herb", 34: "Ether", 35: "Max Ether", 36: "Elixir",
    37: "Max Elixir", 38: "Lava Cookie", 39: "Blue Flute", 40: "Yellow Flute",
    41: "Red Flute", 42: "Black Flute", 43: "White Flute", 44: "Berry Juice",
    45: "Sacred Ash", 46: "Shoal Salt", 47: "Shoal Shell",
    48: "Red Shard", 49: "Blue Shard", 50: "Yellow Shard", 51: "Green Shard",
    63: "HP Up", 64: "Protein", 65: "Iron", 66: "Carbos",
    67: "Calcium", 68: "Rare Candy", 69: "PP Up", 70: "Zinc", 71: "PP Max",
    73: "Guard Spec.", 74: "Dire Hit", 75: "X Attack", 76: "X Defense",
    77: "X Speed", 78: "X Accuracy", 79: "X Sp. Atk", 80: "Poké Doll",
    81: "Fluffy Tail", 83: "Super Repel", 84: "Max Repel",
    85: "Escape Rope", 86: "Repel",
    93: "Sun Stone", 94: "Moon Stone", 95: "Fire Stone",
    96: "Thunder Stone", 97: "Water Stone", 98: "Leaf Stone",
    103: "Tiny Mushroom", 104: "Big Mushroom", 106: "Pearl", 107: "Big Pearl",
    108: "Stardust", 109: "Star Piece", 110: "Nugget", 111: "Heart Scale",
    121: "Orange Mail", 122: "Harbor Mail", 123: "Glitter Mail", 124: "Mech Mail",
    125: "Wood Mail", 126: "Wave Mail", 127: "Bead Mail", 128: "Shadow Mail",
    129: "Tropic Mail", 130: "Dream Mail", 131: "Fab Mail", 132: "Retro Mail",
    133: "Cheri Berry", 134: "Chesto Berry", 135: "Pecha Berry",
    136: "Rawst Berry", 137: "Aspear Berry", 138: "Leppa Berry",
    139: "Oran Berry", 140: "Persim Berry", 141: "Lum Berry", 142: "Sitrus Berry",
    143: "Figy Berry", 144: "Wiki Berry", 145: "Mago Berry", 146: "Aguav Berry",
    147: "Iapapa Berry", 148: "Razz Berry", 149: "Bluk Berry", 150: "Nanab Berry",
    151: "Wepear Berry", 152: "Pinap Berry", 153: "Pomeg Berry", 154: "Kelpsy Berry",
    155: "Qualot Berry", 156: "Hondew Berry", 157: "Grepa Berry", 158: "Tamato Berry",
    159: "Cornn Berry", 160: "Magost Berry", 161: "Rabuta Berry", 162: "Nomel Berry",
    163: "Spelon Berry", 164: "Pamtre Berry", 165: "Watmel Berry", 166: "Durin Berry",
    167: "Belue Berry", 168: "Liechi Berry", 169: "Ganlon Berry", 170: "Salac Berry",
    171: "Petaya Berry", 172: "Apicot Berry", 173: "Lansat Berry", 174: "Starf Berry",
    175: "Enigma Berry",
    179: "Bright Powder", 180: "White Herb", 181: "Macho Brace",
    182: "Exp. Share", 183: "Quick Claw", 184: "Soothe Bell", 185: "Mental Herb",
    186: "Choice Band", 187: "King's Rock", 188: "SilverPowder", 189: "Amulet Coin",
    190: "Cleanse Tag", 191: "Soul Dew", 192: "Deep Sea Tooth", 193: "Deep Sea Scale",
    194: "Smoke Ball", 195: "Everstone", 196: "Focus Band", 197: "Lucky Egg",
    198: "Scope Lens", 199: "Metal Coat", 200: "Leftovers", 201: "Dragon Scale",
    202: "Light Ball", 203: "Soft Sand", 204: "Hard Stone", 205: "Miracle Seed",
    206: "Black Glasses", 207: "Black Belt", 208: "Magnet", 209: "Mystic Water",
    210: "Sharp Beak", 211: "Poison Barb", 212: "Never-Melt Ice", 213: "Spell Tag",
    214: "Twisted Spoon", 215: "Charcoal", 216: "Dragon Fang", 217: "Silk Scarf",
    218: "Up-Grade", 219: "Shell Bell", 220: "Sea Incense", 221: "Lax Incense",
    222: "Lucky Punch", 223: "Metal Powder", 224: "Thick Club", 225: "Stick",
    254: "Red Scarf", 255: "Blue Scarf", 256: "Pink Scarf", 257: "Green Scarf",
    258: "Yellow Scarf",
    # Key Items
    259: "Mach Bike", 260: "Coin Case", 261: "Itemfinder", 262: "Old Rod",
    263: "Good Rod", 264: "Super Rod", 265: "S.S. Ticket", 266: "Contest Pass",
    268: "Wailmer Pail", 269: "Devon Parts", 270: "Soot Sack", 271: "Basement Key",
    272: "Acro Bike", 273: "Pokéblock Case", 274: "Letter", 275: "Eon Ticket",
    276: "Red Orb", 277: "Blue Orb", 278: "Scanner", 279: "Go-Goggles",
    280: "Meteorite", 281: "Key to Room 1", 282: "Key to Room 2", 283: "Key to Room 4",
    284: "Key to Room 6", 285: "Storage Key", 286: "Root Fossil", 287: "Claw Fossil",
    288: "Devon Scope",
    # TMs with move names
    289: "TM01 Focus Punch", 290: "TM02 Dragon Claw", 291: "TM03 Water Pulse",
    292: "TM04 Calm Mind", 293: "TM05 Roar", 294: "TM06 Toxic",
    295: "TM07 Hail", 296: "TM08 Bulk Up", 297: "TM09 Bullet Seed",
    298: "TM10 Hidden Power", 299: "TM11 Sunny Day", 300: "TM12 Taunt",
    301: "TM13 Ice Beam", 302: "TM14 Blizzard", 303: "TM15 Hyper Beam",
    304: "TM16 Light Screen", 305: "TM17 Protect", 306: "TM18 Rain Dance",
    307: "TM19 Giga Drain", 308: "TM20 Safeguard", 309: "TM21 Frustration",
    310: "TM22 Solar Beam", 311: "TM23 Iron Tail", 312: "TM24 Thunderbolt",
    313: "TM25 Thunder", 314: "TM26 Earthquake", 315: "TM27 Return",
    316: "TM28 Dig", 317: "TM29 Psychic", 318: "TM30 Shadow Ball",
    319: "TM31 Brick Break", 320: "TM32 Double Team", 321: "TM33 Reflect",
    322: "TM34 Shock Wave", 323: "TM35 Flamethrower", 324: "TM36 Sludge Bomb",
    325: "TM37 Sandstorm", 326: "TM38 Fire Blast", 327: "TM39 Rock Tomb",
    328: "TM40 Aerial Ace", 329: "TM41 Torment", 330: "TM42 Facade",
    331: "TM43 Secret Power", 332: "TM44 Rest", 333: "TM45 Attract",
    334: "TM46 Thief", 335: "TM47 Steel Wing", 336: "TM48 Skill Swap",
    337: "TM49 Snatch", 338: "TM50 Overheat",
    # HMs with move names
    339: "HM01 Cut", 340: "HM02 Fly", 341: "HM03 Surf", 342: "HM04 Strength",
    343: "HM05 Flash", 344: "HM06 Rock Smash", 345: "HM07 Waterfall", 346: "HM08 Dive",
    # FRLG Key Items
    349: "Parcel", 350: "Poké Flute", 351: "Secret Key", 352: "Bike Voucher",
    353: "Gold Teeth", 354: "Old Amber", 355: "Card Key", 356: "Lift Key",
    357: "Helix Fossil", 358: "Dome Fossil", 359: "Silph Scope", 360: "Bicycle",
    361: "Town Map", 362: "VS Seeker", 363: "Fame Checker", 364: "TM Case",
    365: "Berry Pouch", 366: "Teachy TV", 367: "Tri-Pass", 368: "Rainbow Pass",
    369: "Tea", 370: "MysticTicket", 371: "AuroraTicket", 372: "Powder Jar",
    373: "Ruby", 374: "Sapphire", 375: "Magma Emblem", 376: "Old Sea Map",
}


def get_item_name(item_id):
    """Get item name from ID."""
    return ITEM_NAMES.get(item_id, f"Item #{item_id}")


def parse_item_pocket(data, offset, max_slots, encryption_key):
    """
    Parse a single bag pocket.
    
    Args:
        data: Save file data
        offset: Absolute offset to pocket
        max_slots: Maximum item slots in pocket
        encryption_key: XOR key for quantity decryption (32-bit, use lower 16 bits)
        
    Returns:
        list: List of {item_id, quantity} dicts
    """
    items = []
    
    # Use only lower 16 bits of encryption key for item quantities
    key_16bit = encryption_key & 0xFFFF
    
    for slot in range(max_slots):
        item_offset = offset + (slot * 4)
        
        if item_offset + 4 > len(data):
            break
        
        # Item ID is NOT encrypted
        item_id = struct.unpack('<H', data[item_offset:item_offset + 2])[0]
        
        # Quantity IS encrypted (XOR with lower 16 bits of key)
        qty_encrypted = struct.unpack('<H', data[item_offset + 2:item_offset + 4])[0]
        
        if encryption_key != 0:
            quantity = qty_encrypted ^ key_16bit
        else:
            quantity = qty_encrypted
        
        # Skip empty slots
        if item_id == 0 or item_id == 0xFFFF:
            continue
        
        # Validate
        if 1 <= item_id <= 376 and 1 <= quantity <= 999:
            items.append({
                'item_id': item_id,
                'quantity': quantity,
                'name': get_item_name(item_id),
            })
        elif item_id != 0:
            # Debug: show items that failed validation
            print(f"[Items] Rejected: id={item_id}, qty_enc={qty_encrypted}, qty_dec={quantity}, key16={key_16bit}")
    
    return items


def parse_bag(data, section1_offset, game_type='RS', section_offsets=None):
    """
    Parse all bag pockets.
    
    Args:
        data: Save file data
        section1_offset: Offset to Section 1
        game_type: 'FRLG', 'RS', or 'E'
        section_offsets: Dict mapping section IDs to their offsets (needed for E/FRLG key)
        
    Returns:
        dict: {pocket_name: [items]}
    """
    # Get correct offsets for game type
    if game_type == 'FRLG':
        offsets = OFFSETS_FRLG
    elif game_type == 'E':
        offsets = OFFSETS_E
    else:  # RS
        offsets = OFFSETS_RS
    
    # Get encryption key based on game type
    encryption_key = 0  # Default for RS (no encryption)
    
    key_section = offsets.get('security_key_section')
    key_offset = offsets.get('security_key_offset')
    
    if key_section is not None and key_offset is not None and section_offsets:
        # E or FRLG - key is in Section 0
        if key_section in section_offsets:
            abs_key_offset = section_offsets[key_section] + key_offset
            if abs_key_offset + 4 <= len(data):
                encryption_key = struct.unpack('<I', data[abs_key_offset:abs_key_offset + 4])[0]
                key_16bit = encryption_key & 0xFFFF
                print(f"[Items] game_type={game_type}, key from Section {key_section} + 0x{key_offset:04X}")
                print(f"[Items] Full key={encryption_key} (0x{encryption_key:08X}), Lower 16 bits={key_16bit} (0x{key_16bit:04X})")
    else:
        print(f"[Items] game_type={game_type}, no encryption (key=0)")
    
    # Debug: show pocket offsets being used
    print(f"[Items] Pocket offsets for {game_type}:")
    print(f"[Items]   items: 0x{offsets['items']:04X} ({offsets['item_slots']['items']} slots)")
    print(f"[Items]   key_items: 0x{offsets['key_items']:04X} ({offsets['item_slots']['key_items']} slots)")
    print(f"[Items]   pokeballs: 0x{offsets['pokeballs']:04X} ({offsets['item_slots']['pokeballs']} slots)")
    print(f"[Items]   tms_hms: 0x{offsets['tms_hms']:04X} ({offsets['item_slots']['tms_hms']} slots)")
    print(f"[Items]   berries: 0x{offsets['berries']:04X} ({offsets['item_slots']['berries']} slots)")
    
    bag = {}
    
    pocket_names = ['items', 'key_items', 'pokeballs', 'tms_hms', 'berries']
    
    for pocket_name in pocket_names:
        pocket_offset = section1_offset + offsets[pocket_name]
        max_slots = offsets['item_slots'][pocket_name]
        
        # Ruby/Sapphire (RS) do NOT encrypt key items - they store raw quantity values
        # Emerald and FRLG DO encrypt key items
        # Only skip encryption for key_items in RS (which has encryption_key = 0 anyway)
        if pocket_name == 'key_items' and game_type == 'RS':
            pocket_key = 0
        else:
            pocket_key = encryption_key
        
        pocket_items = parse_item_pocket(data, pocket_offset, max_slots, pocket_key)
        bag[pocket_name] = pocket_items
        
        if pocket_items:
            print(f"[Items] {pocket_name}: {len(pocket_items)} items found")
    
    total = sum(len(p) for p in bag.values())
    print(f"[Items] Total items across all pockets: {total}")
    
    return bag


def parse_money(data, section1_offset, game_type='RS', section_offsets=None):
    """
    Parse money from save.
    
    Args:
        data: Save file data
        section1_offset: Offset to Section 1
        game_type: 'FRLG', 'RS', or 'E'
        section_offsets: Dict mapping section IDs to their offsets (needed for E/FRLG key)
        
    Returns:
        int: Money amount
    """
    # Get correct offsets for game type
    if game_type == 'FRLG':
        offsets = OFFSETS_FRLG
    elif game_type == 'E':
        offsets = OFFSETS_E
    else:  # RS
        offsets = OFFSETS_RS
    
    money_offset = section1_offset + offsets['money']
    
    # Get encryption key based on game type
    encryption_key = 0  # Default for RS (no encryption)
    
    key_section = offsets.get('security_key_section')
    key_offset = offsets.get('security_key_offset')
    
    if key_section is not None and key_offset is not None and section_offsets:
        # E or FRLG - key is in Section 0
        if key_section in section_offsets:
            abs_key_offset = section_offsets[key_section] + key_offset
            if abs_key_offset + 4 <= len(data):
                encryption_key = struct.unpack('<I', data[abs_key_offset:abs_key_offset + 4])[0]
    
    # Money is 4 bytes
    money_encrypted = struct.unpack('<I', data[money_offset:money_offset + 4])[0]
    
    if encryption_key == 0:
        # No encryption (RS)
        money = money_encrypted
        print(f"[Money] game_type={game_type}, raw value={money} (no encryption)")
    else:
        # E or FRLG - XOR with full 32-bit key
        money = money_encrypted ^ encryption_key
        print(f"[Money] game_type={game_type}, encrypted={money_encrypted}, key={encryption_key}, decrypted={money}")
    
    # Validate
    if money > 999999:
        print(f"[Money] Value {money} exceeds max, capping to 999999")
        money = 999999
    
    return money


def get_bag_summary(bag):
    """
    Get summary of bag contents.
    
    Args:
        bag: Parsed bag dict
        
    Returns:
        dict: Summary statistics
    """
    return {
        'items': len(bag.get('items', [])),
        'key_items': len(bag.get('key_items', [])),
        'pokeballs': len(bag.get('pokeballs', [])),
        'tms_hms': len(bag.get('tms_hms', [])),
        'berries': len(bag.get('berries', [])),
        'total': sum(len(pocket) for pocket in bag.values()),
    }


def categorize_item(item_id):
    """
    Categorize an item by its ID.
    
    Args:
        item_id: Item ID
        
    Returns:
        str: Category name
    """
    if 1 <= item_id <= 12:
        return 'Poké Balls'
    elif 13 <= item_id <= 62:
        return 'Medicine'
    elif 63 <= item_id <= 71:
        return 'Vitamins'
    elif 93 <= item_id <= 98:
        return 'Evolution Stones'
    elif 133 <= item_id <= 175:
        return 'Berries'
    elif 179 <= item_id <= 258:
        return 'Hold Items'
    elif 289 <= item_id <= 338:
        return 'TMs'
    elif 339 <= item_id <= 346:
        return 'HMs'
    elif item_id >= 259:
        return 'Key Items'
    else:
        return 'Other'