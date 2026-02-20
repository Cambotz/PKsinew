"""
Gen 3 Item Parser Module - Multi-Game Support

Handles parsing of bag items from Gen 3 save files
Supports: Ruby, Sapphire, Emerald, FireRed, LeafGreen
"""

import struct


# Pocket configurations for different games
POCKET_CONFIGS = {
    'FRLG': {  # FireRed / LeafGreen
        'name': 'FireRed/LeafGreen',
        'offsets': [
            (0x0310, 'items', 42),
            (0x03B8, 'key_items', 30),
            (0x0430, 'pokeballs', 13),
            (0x0464, 'tms_hms', 58),
            (0x054C, 'berries', 43),
        ]
    },
    'RSE': {  # Ruby / Sapphire / Emerald
        'name': 'Ruby/Sapphire/Emerald',
        'offsets': [
            (0x0560, 'items', 20),
            (0x05B0, 'key_items', 20),
            (0x0600, 'pokeballs', 16),
            (0x0640, 'tms_hms', 64),
            (0x0740, 'berries', 46),
        ]
    }
}


class ItemParser:
    """Parser for bag items in Gen 3 saves"""
    
    def __init__(self, data, section1_offset, game_type='auto'):
        """
        Initialize item parser
        
        Args:
            data: bytearray of save file data
            section1_offset: Offset to Section 1 in the save data
            game_type: 'FRLG', 'RSE', or 'auto' to auto-detect
        """
        self.data = data
        self.section1_offset = section1_offset
        
        # Item encryption key is at Section 1 + 0x0294
        self.item_key = struct.unpack('<H', data[section1_offset + 0x0294:section1_offset + 0x0296])[0]
        
        # Detect game type if auto
        if game_type == 'auto':
            self.game_type = self._detect_game_type()
        else:
            self.game_type = game_type
        
        # Get pocket configuration
        self.pocket_config = POCKET_CONFIGS.get(self.game_type, POCKET_CONFIGS['FRLG'])
        
        self.bag = {
            'items': [],
            'key_items': [],
            'pokeballs': [],
            'tms_hms': [],
            'berries': []
        }
    
    def _detect_game_type(self):
        """
        Auto-detect whether this is FR/LG or R/S/E
        
        Returns:
            str: 'FRLG' or 'RSE'
        """
        # FireRed/LeafGreen have specific key items that don't exist in R/S/E
        # Check for Teachy TV (ID 366) or Fame Checker (ID 363) in key items area
        
        # Try FRLG key items offset
        frlg_key_offset = self.section1_offset + 0x03B8
        for slot in range(10):
            item_offset = frlg_key_offset + (slot * 4)
            if item_offset + 2 <= len(self.data):
                item_id = struct.unpack('<H', self.data[item_offset:item_offset+2])[0]
                # Items exclusive to FRLG
                if item_id in [361, 362, 363, 364, 365, 366, 367, 368]:  # FRLG-specific items
                    return 'FRLG'
        
        # Try RSE key items offset
        rse_key_offset = self.section1_offset + 0x05B0
        for slot in range(10):
            item_offset = rse_key_offset + (slot * 4)
            if item_offset + 2 <= len(self.data):
                item_id = struct.unpack('<H', self.data[item_offset:item_offset+2])[0]
                # Items exclusive to RSE
                if item_id in [265, 266, 268, 269, 270]:  # RSE-specific items
                    return 'RSE'
        
        # Default to FRLG if can't detect
        return 'FRLG'
    
    def parse_bag(self):
        """Parse bag items from Section 1"""
        try:
            for pocket_offset, pocket_name, max_slots in self.pocket_config['offsets']:
                abs_offset = self.section1_offset + pocket_offset
                items = self._parse_pocket(abs_offset, max_slots)
                self.bag[pocket_name] = items
            
        except Exception as e:
            print(f"Error parsing bag: {e}")
            import traceback
            traceback.print_exc()
    
    def _parse_pocket(self, offset, max_slots):
        """
        Parse a single item pocket
        
        Args:
            offset: Absolute offset to pocket start
            max_slots: Maximum number of item slots in this pocket
            
        Returns:
            list: List of dicts with 'item_id' and 'quantity'
        """
        items = []
        
        for slot in range(max_slots):
            item_offset = offset + (slot * 4)
            
            if item_offset + 4 > len(self.data):
                break
            
            # Read item ID (NOT encrypted) and encrypted quantity
            item_id = struct.unpack('<H', self.data[item_offset:item_offset+2])[0]
            qty_encrypted = struct.unpack('<H', self.data[item_offset+2:item_offset+4])[0]
            
            # Skip empty slots
            if item_id == 0 or item_id == 0xFFFF:
                continue
            
            # Decrypt quantity using XOR with item encryption key
            quantity = qty_encrypted ^ self.item_key
            
            # Validate item
            if 1 <= item_id <= 376 and 1 <= quantity <= 999:
                items.append({
                    'item_id': item_id,
                    'quantity': quantity
                })
        
        return items
    
    def get_bag(self):
        """Get the parsed bag data"""
        return self.bag
    
    def get_game_type(self):
        """Get detected game type"""
        return self.game_type
    
    def get_game_name(self):
        """Get human-readable game name"""
        return self.pocket_config['name']
    
    def get_bag_summary(self):
        """Get summary of bag contents"""
        return {
            'game_type': self.game_type,
            'game_name': self.get_game_name(),
            'items': len(self.bag['items']),
            'key_items': len(self.bag['key_items']),
            'pokeballs': len(self.bag['pokeballs']),
            'tms_hms': len(self.bag['tms_hms']),
            'berries': len(self.bag['berries']),
            'total': sum([
                len(self.bag['items']),
                len(self.bag['key_items']),
                len(self.bag['pokeballs']),
                len(self.bag['tms_hms']),
                len(self.bag['berries'])
            ])
        }
    
    def get_money(self):
        """
        Get decrypted money value
        
        Money is stored at Section 1 + 0x0290 (4 bytes)
        Only the LOWER 16 bits are encrypted (XOR with item key)
        
        Returns:
            int: Money amount (0-999999)
        """
        try:
            money_offset = self.section1_offset + 0x0290
            if money_offset + 4 <= len(self.data):
                money_encrypted = struct.unpack('<I', self.data[money_offset:money_offset + 4])[0]
                # Only decrypt the lower 16 bits
                money_lower = money_encrypted & 0xFFFF
                money = money_lower ^ self.item_key
                if 0 <= money <= 999999:
                    return money
        except:
            pass
        return 0


def parse_bag_from_section(data, section1_offset):
    """
    Convenience function to parse bag without creating ItemParser object
    
    Args:
        data: bytearray of save file data
        section1_offset: Offset to Section 1
        
    Returns:
        dict: Bag data with all 5 pockets and money
    """
    parser = ItemParser(data, section1_offset)
    parser.parse_bag()
    return {
        'bag': parser.get_bag(),
        'money': parser.get_money(),
        'game_type': parser.get_game_type()
    }