"""
Save Editor Manager
Handles save file loading, parsing, and display operations
"""

import os
import sys
import subprocess
import config

# Import the save parser (with path handling)
parser_found = False
for location in config.PARSER_LOCATIONS:
    if os.path.exists(os.path.join(location, 'gen3_save_parser.py')):
        sys.path.insert(0, location)
        parser_found = True
        break

if not parser_found:
    raise ImportError("Parser files not found! Check parser directory location.")

from gen3_save_parser import Gen3SaveParser
from item_names import get_item_name


class SaveEditorManager:
    """Manages save file operations"""
    
    def __init__(self):
        self.loaded_save = None
        self.save_info_text = ""
    
    def list_save_files(self):
        """
        List all save files in the saves directory
        
        Returns:
            List of dicts with save file info
        """
        if not os.path.exists(config.SAVES_PATH):
            return []
        
        saves = []
        for file in os.listdir(config.SAVES_PATH):
            if file.lower().endswith(('.sav', '.srm', '.bin', '.sa1', '.sa2')):
                fp = os.path.join(config.SAVES_PATH, file)
                size = os.path.getsize(fp)
                with open(fp, 'rb') as f:
                    first = f.read(16)
                    is_empty = (first == b'\xff' * 16)
                saves.append({'name': file, 'size': size, 'empty': is_empty})
        
        return saves
    
    def load_save_file(self, filename):
        """
        Load and parse a save file
        
        Args:
            filename: Name of the save file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        path = os.path.join(config.SAVES_PATH, filename)
        parser = Gen3SaveParser(path)
        
        if parser.load():
            self.loaded_save = parser
            self._build_save_info_text(filename, parser)
            return True, "Save loaded successfully!"
        else:
            self.save_info_text = f"Failed to load: {filename}\nMake sure this is a Gen3 save file."
            return False, "Failed to load save file"
    
    def _build_save_info_text(self, filename, parser):
        """Build the save info display text"""
        info = parser.get_trainer_info()
        party = parser.get_party_data()
        
        self.save_info_text = f"=== SAVE FILE INFO ===\n"
        self.save_info_text += f"File: {filename}\n"
        self.save_info_text += f"File Size: {len(parser.data)} bytes\n\n"
        self.save_info_text += f"Trainer Name: {info.get('name', 'Unknown')}\n"
        self.save_info_text += f"Gender: {info.get('gender', 'Unknown')}\n"
        self.save_info_text += f"Rival Name: {info.get('rival_name', 'Unknown')}\n"
        self.save_info_text += f"Trainer ID: {info.get('id', 0):05d}\n"
        self.save_info_text += f"Secret ID: {info.get('secret_id', 0):05d}\n"
        self.save_info_text += f"Money: ${info.get('money', 0):,}\n\n"
        self.save_info_text += f"Party Pokemon: {len(party)}\n\n"
        
        if party:
            self.save_info_text += "=== PARTY ===\n"
            for i, poke in enumerate(party):
                species_id = poke.get('species', 0)
                species_name = poke.get('nickname') or poke.get('species_name') or f"#{species_id}"
                level = poke.get('level', '?')
                current_hp = poke.get('current_hp', 0)
                max_hp = poke.get('max_hp', 0)
                self.save_info_text += f"{i+1}. {species_name} Lv.{level} HP:{current_hp}/{max_hp}\n"
    
    def get_bag_display_text(self):
        """
        Generate bag contents display text
        
        Returns:
            String of formatted bag contents
        """
        if not self.loaded_save:
            return "No save file loaded"
        
        bag = self.loaded_save.get_bag()
        trainer = self.loaded_save.get_trainer_info()
        
        # Collect all unique items
        all_items = {}
        for pocket_key in ['items', 'key_items', 'pokeballs', 'tms_hms', 'berries']:
            if bag.get(pocket_key):
                for item in bag[pocket_key]:
                    item_id = item['item_id']
                    if item_id not in all_items:
                        all_items[item_id] = {
                            'name': get_item_name(item_id),
                            'quantity': item['quantity']
                        }
        
        # Build display
        bag_text = f"=== {trainer['name']}'s BAG ===\n"
        bag_text += f"Money: ${trainer['money']:,}\n\n"
        
        if not all_items:
            return bag_text + "Bag is empty.\n"
        
        # Categorize items
        categories = self._categorize_items(all_items)
        
        # Display each category
        for category_name, items in categories.items():
            if items:
                bag_text += f"=== {category_name.upper()} ({len(items)}) ===\n"
                for name, qty in sorted(items):
                    bag_text += f"  {name:30s} x{qty:3d}\n"
                bag_text += "\n"
        
        bag_text += f"{'='*40}\n"
        bag_text += f"Total: {len(all_items)} unique items\n"
        
        return bag_text
    
    def _categorize_items(self, all_items):
        """Categorize items by type"""
        categories = {
            'Medicine': [],
            'Poké Balls': [],
            'Key Items': [],
            'TMs': [],
            'HMs': [],
            'Berries': [],
            'Other': []
        }
        
        medicine_ids = [13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,44,45]
        
        for item_id, item_data in all_items.items():
            name = item_data['name']
            qty = item_data['quantity']
            
            # Categorize by ID ranges
            if 1 <= item_id <= 12:
                categories['Poké Balls'].append((name, qty))
            elif 289 <= item_id <= 338:
                categories['TMs'].append((name, qty))
            elif 339 <= item_id <= 346:
                categories['HMs'].append((name, qty))
            elif 133 <= item_id <= 175:
                categories['Berries'].append((name, qty))
            elif item_id in medicine_ids or 'Potion' in name or 'Heal' in name or 'Revive' in name:
                categories['Medicine'].append((name, qty))
            elif item_id >= 259:
                categories['Key Items'].append((name, qty))
            else:
                categories['Other'].append((name, qty))
        
        return categories
    
    def get_pc_boxes_display_text(self):
        """
        Generate PC boxes display text
        
        Returns:
            String of formatted PC box contents
        """
        if not self.loaded_save:
            return "No save file loaded"
        
        trainer = self.loaded_save.get_trainer_info()
        party = self.loaded_save.get_party_data()
        
        # Try to get complete box structure
        try:
            all_boxes = self.loaded_save.get_all_boxes_structure()
            has_structure = True
        except AttributeError:
            pc_boxes = self.loaded_save.get_pc_boxes()
            has_structure = False
        
        # Start building display
        box_text = f"=== {trainer['name']}'s PC BOXES ===\n\n"
        
        # Party summary
        box_text += f"PARTY ({len(party)} Pokémon):\n"
        if party:
            for i, poke in enumerate(party, 1):
                if poke.get('egg'):
                    box_text += f"  {i}. Egg\n"
                else:
                    nickname = poke.get('nickname', '???')
                    species = poke.get('species', 0)
                    level = poke.get('level', 0)
                    box_text += f"  {i}. {nickname:12s} #{species:03d} Lv.{level:3d}\n"
        else:
            box_text += "  (empty)\n"
        
        box_text += "\n" + "="*50 + "\n\n"
        
        # Display boxes
        if has_structure:
            box_text += self._format_boxes_with_structure(all_boxes)
        else:
            box_text += self._format_boxes_legacy(pc_boxes)
        
        return box_text
    
    def _format_boxes_with_structure(self, all_boxes):
        """Format box display with full structure"""
        text = ""
        for box_num in range(1, 15):
            box_slots = all_boxes[box_num]
            filled_count = sum(1 for slot in box_slots if not slot.get('empty', False))
            
            text += f"BOX {box_num:2d} ({filled_count}/30 filled):\n"
            
            for slot in box_slots:
                slot_num = slot.get('slot', slot.get('box_slot', '?'))
                
                if slot.get('empty'):
                    text += f"  Slot {slot_num:2d}: [EMPTY]\n"
                elif slot.get('egg'):
                    text += f"  Slot {slot_num:2d}: Egg\n"
                else:
                    nickname = slot.get('nickname', '???')
                    species = slot.get('species', 0)
                    level = slot.get('level', 0)
                    text += f"  Slot {slot_num:2d}: {nickname:12s} #{species:03d} Lv.{level:3d}\n"
            
            text += "\n"
        
        return text
    
    def _format_boxes_legacy(self, pc_boxes):
        """Format box display using legacy method"""
        if not pc_boxes:
            return "No Pokémon in PC storage.\n"
        
        text = ""
        boxes_dict = {}
        for poke in pc_boxes:
            box_num = poke.get('box_number', 0)
            if box_num not in boxes_dict:
                boxes_dict[box_num] = []
            boxes_dict[box_num].append(poke)
        
        for box_num in sorted(boxes_dict.keys()):
            box_pokemon = boxes_dict[box_num]
            text += f"=== BOX {box_num + 1} ({len(box_pokemon)} Pokémon) ===\n"
            
            box_pokemon.sort(key=lambda p: p.get('box_slot', 0))
            
            for poke in box_pokemon:
                slot = poke.get('box_slot', 0)
                nickname = poke.get('nickname', '???')
                species = poke.get('species', 0)
                level = poke.get('level', 0)
                text += f"  Slot {slot:2d}: {nickname:10s} (#{species:03d}) Lv.{level:3d}\n"
            
            text += "\n"
        
        return text
    
    def get_loaded_save(self):
        """Get the currently loaded save parser"""
        return self.loaded_save
    
    def get_save_info_text(self):
        """Get the save info display text"""
        return self.save_info_text


def launch_rom(game_name):
    """
    Launch a ROM in mGBA
    
    Args:
        game_name: Name of the game (must be in ROM_PATHS)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if game_name not in config.ROM_PATHS:
        return False, f"Game {game_name} not found in ROM paths"
    
    rom_path = config.ROM_PATHS[game_name]
    
    if not os.path.exists(rom_path):
        return False, f"ROM not found: {rom_path}"
    
    if not os.path.exists(config.MGBA_PATH):
        return False, f"mGBA not found: {config.MGBA_PATH}"
    
    try:
        subprocess.Popen([config.MGBA_PATH, rom_path])
        return True, f"Launched {game_name}"
    except Exception as e:
        return False, f"Failed to launch: {str(e)}"