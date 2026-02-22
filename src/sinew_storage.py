"""
Sinew Storage System
Cross-game Pokemon storage that persists outside of individual save files.
Features:
- 120 slots per box (vs 30 in game saves)
- 20 boxes total (2400 Pokemon capacity)
- Automatic backups
- Safe atomic writes
"""

import os
import json
import shutil
import base64
from datetime import datetime

from config import EXT_DIR, SAVES_DIR

# Storage paths
STORAGE_DIR = os.path.join(EXT_DIR, "saves", "sinew")
STORAGE_FILE = os.path.join(STORAGE_DIR, "sinew_storage.json")
BACKUP_FILE = os.path.join(STORAGE_DIR, "sinew_storage_backup.json")
TEMP_FILE = os.path.join(STORAGE_DIR, "sinew_storage_temp.json")

# Storage configuration
NUM_BOXES = 20
SLOTS_PER_BOX = 120
DEFAULT_BOX_NAMES = [f"Storage {i+1}" for i in range(NUM_BOXES)]


class SinewStorage:
    """
    Manages Sinew's cross-game Pokemon storage.
    
    Storage format:
    {
        "version": 1,
        "last_modified": "ISO timestamp",
        "boxes": [
            {
                "name": "Storage 1",
                "slots": [pokemon_dict or null, ...]  # 120 slots
            },
            ...
        ]
    }
    """
    
    # Class-level version counter - increments when ANY instance modifies data
    # Used by PC Box to detect when it needs to refresh its cache
    _data_version = 0
    
    def __init__(self):
        self.data = None
        self.loaded = False
        self._ensure_storage_dir()
        self.load()
    
    @classmethod
    def get_data_version(cls):
        """Get current data version for cache invalidation"""
        return cls._data_version
    
    @classmethod
    def _increment_version(cls):
        """Increment data version after modifications"""
        cls._data_version += 1
    
    def _ensure_storage_dir(self):
        """Ensure storage directory exists"""
        os.makedirs(STORAGE_DIR, exist_ok=True)
    
    def _create_empty_storage(self):
        """Create empty storage structure"""
        return {
            "version": 1,
            "last_modified": datetime.now().isoformat(),
            "boxes": [
                {
                    "name": DEFAULT_BOX_NAMES[i],
                    "slots": [None] * SLOTS_PER_BOX
                }
                for i in range(NUM_BOXES)
            ]
        }
    
    def load(self):
        """Load storage from file, create if doesn't exist"""
        try:
            if os.path.exists(STORAGE_FILE):
                with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                
                # Validate structure
                if not self._validate_structure():
                    print("[SinewStorage] Invalid storage structure, creating new")
                    self.data = self._create_empty_storage()
                    self.save()
                
                self.loaded = True
                pokemon_count = self.get_total_pokemon_count()
                print(f"[SinewStorage] Loaded: {pokemon_count} Pokemon in storage")
            else:
                # Create new storage
                self.data = self._create_empty_storage()
                self.save()
                self.loaded = True
                print("[SinewStorage] Created new storage file")
        except Exception as e:
            print(f"[SinewStorage] Error loading: {e}")
            # Try to load from backup
            if os.path.exists(BACKUP_FILE):
                try:
                    print("[SinewStorage] Attempting to load from backup...")
                    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
                        self.data = json.load(f)
                    self.loaded = True
                    self.save()  # Save to main file
                    print("[SinewStorage] Restored from backup")
                except Exception as e2:
                    print(f"[SinewStorage] Backup also failed: {e2}")
                    self.data = self._create_empty_storage()
                    self.save()
                    self.loaded = True
            else:
                self.data = self._create_empty_storage()
                self.save()
                self.loaded = True
    
    def _validate_structure(self):
        """Validate storage structure"""
        if not isinstance(self.data, dict):
            return False
        if "version" not in self.data:
            return False
        if "boxes" not in self.data:
            return False
        if not isinstance(self.data["boxes"], list):
            return False
        
        # Ensure we have correct number of boxes
        while len(self.data["boxes"]) < NUM_BOXES:
            idx = len(self.data["boxes"])
            self.data["boxes"].append({
                "name": DEFAULT_BOX_NAMES[idx] if idx < len(DEFAULT_BOX_NAMES) else f"Storage {idx+1}",
                "slots": [None] * SLOTS_PER_BOX
            })
        
        # Validate each box
        for box in self.data["boxes"]:
            if not isinstance(box, dict):
                return False
            if "slots" not in box:
                box["slots"] = [None] * SLOTS_PER_BOX
            if "name" not in box:
                box["name"] = "Unnamed"
            # Ensure slots list is correct length
            while len(box["slots"]) < SLOTS_PER_BOX:
                box["slots"].append(None)
            if len(box["slots"]) > SLOTS_PER_BOX:
                box["slots"] = box["slots"][:SLOTS_PER_BOX]
        
        return True
    
    def save(self):
        """Save storage to file with atomic write and backup"""
        if not self.data:
            return False
        
        try:
            self._ensure_storage_dir()
            
            # Update timestamp
            self.data["last_modified"] = datetime.now().isoformat()
            
            # Create backup of existing file
            if os.path.exists(STORAGE_FILE):
                try:
                    shutil.copy2(STORAGE_FILE, BACKUP_FILE)
                except Exception as e:
                    print(f"[SinewStorage] Backup failed: {e}")
            
            # Write to temp file first (atomic write)
            with open(TEMP_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            # Rename temp to actual file
            if os.path.exists(STORAGE_FILE):
                os.remove(STORAGE_FILE)
            os.rename(TEMP_FILE, STORAGE_FILE)
            
            # Increment version counter so PC Box knows to refresh
            self._increment_version()
            
            return True
        except Exception as e:
            print(f"[SinewStorage] Error saving: {e}")
            # Clean up temp file if it exists
            if os.path.exists(TEMP_FILE):
                try:
                    os.remove(TEMP_FILE)
                except:
                    pass
            return False
    
    def is_loaded(self):
        """Check if storage is loaded"""
        return self.loaded and self.data is not None
    
    def get_box(self, box_number):
        """
        Get a specific box (1-indexed).
        
        Args:
            box_number: Box number (1 to NUM_BOXES)
            
        Returns:
            list: 120 slots (Pokemon dicts or None for empty)
        """
        if not self.is_loaded():
            return [None] * SLOTS_PER_BOX
        
        idx = box_number - 1
        if 0 <= idx < len(self.data["boxes"]):
            slots = self.data["boxes"][idx]["slots"]
            # Return copies with raw_bytes decoded
            result = []
            for p in slots:
                if p:
                    pokemon_copy = p.copy()
                    # Decode raw_bytes from base64 string
                    if 'raw_bytes_b64' in pokemon_copy:
                        pokemon_copy['raw_bytes'] = base64.b64decode(pokemon_copy['raw_bytes_b64'])
                        del pokemon_copy['raw_bytes_b64']
                    result.append(pokemon_copy)
                else:
                    result.append(None)
            return result
        return [None] * SLOTS_PER_BOX
    
    def get_box_name(self, box_number):
        """Get name of a specific box"""
        if not self.is_loaded():
            return f"Storage {box_number}"
        
        idx = box_number - 1
        if 0 <= idx < len(self.data["boxes"]):
            return self.data["boxes"][idx].get("name", f"Storage {box_number}")
        return f"Storage {box_number}"
    
    def set_box_name(self, box_number, name):
        """Set name of a specific box"""
        if not self.is_loaded():
            return False
        
        idx = box_number - 1
        if 0 <= idx < len(self.data["boxes"]):
            self.data["boxes"][idx]["name"] = name
            return self.save()
        return False
    
    def get_pokemon_at(self, box_number, slot):
        """
        Get Pokemon at specific location.
        
        Args:
            box_number: Box number (1-indexed)
            slot: Slot index (0-indexed, 0-119)
            
        Returns:
            dict or None: Pokemon data or None if empty
        """
        if not self.is_loaded():
            return None
        
        idx = box_number - 1
        if 0 <= idx < len(self.data["boxes"]):
            slots = self.data["boxes"][idx]["slots"]
            if 0 <= slot < len(slots):
                p = slots[slot]
                if p:
                    pokemon_copy = p.copy()
                    # Decode raw_bytes from base64 string
                    if 'raw_bytes_b64' in pokemon_copy:
                        pokemon_copy['raw_bytes'] = base64.b64decode(pokemon_copy['raw_bytes_b64'])
                        del pokemon_copy['raw_bytes_b64']
                    return pokemon_copy
        return None
    
    def set_pokemon_at(self, box_number, slot, pokemon):
        """
        Place Pokemon at specific location.
        
        Args:
            box_number: Box number (1-indexed)
            slot: Slot index (0-indexed, 0-119)
            pokemon: Pokemon dict or None to clear slot
            
        Returns:
            bool: Success
        """
        if not self.is_loaded():
            return False
        
        idx = box_number - 1
        if 0 <= idx < len(self.data["boxes"]):
            slots = self.data["boxes"][idx]["slots"]
            if 0 <= slot < len(slots):
                # Store a copy with raw_bytes encoded as base64
                if pokemon:
                    pokemon_copy = pokemon.copy()
                    # Encode raw_bytes to base64 string for JSON storage
                    if 'raw_bytes' in pokemon_copy and isinstance(pokemon_copy['raw_bytes'], bytes):
                        pokemon_copy['raw_bytes_b64'] = base64.b64encode(pokemon_copy['raw_bytes']).decode('ascii')
                        del pokemon_copy['raw_bytes']
                    self.data["boxes"][idx]["slots"][slot] = pokemon_copy
                else:
                    self.data["boxes"][idx]["slots"][slot] = None
                return self.save()
        return False
    
    def clear_slot(self, box_number, slot):
        """Clear a specific slot"""
        return self.set_pokemon_at(box_number, slot, None)
    
    def find_first_empty_slot(self, box_number=None):
        """
        Find first empty slot.
        
        Args:
            box_number: If specified, search only this box. Otherwise search all.
            
        Returns:
            tuple: (box_number, slot_index) or None if no empty slots
        """
        if not self.is_loaded():
            return None
        
        if box_number is not None:
            idx = box_number - 1
            if 0 <= idx < len(self.data["boxes"]):
                slots = self.data["boxes"][idx]["slots"]
                for i, p in enumerate(slots):
                    if p is None:
                        return (box_number, i)
            return None
        
        # Search all boxes
        for box_idx, box in enumerate(self.data["boxes"]):
            for slot_idx, p in enumerate(box["slots"]):
                if p is None:
                    return (box_idx + 1, slot_idx)
        return None
    
    def deposit_pokemon(self, pokemon, box_number=None):
        """
        Deposit a Pokemon into storage.
        
        Args:
            pokemon: Pokemon dict to deposit
            box_number: Optional specific box (will find first empty slot)
            
        Returns:
            tuple: (box_number, slot) where deposited, or None if full
        """
        location = self.find_first_empty_slot(box_number)
        if location:
            box, slot = location
            if self.set_pokemon_at(box, slot, pokemon):
                return location
        return None
    
    def withdraw_pokemon(self, box_number, slot):
        """
        Withdraw a Pokemon from storage (removes it).
        
        Args:
            box_number: Box number (1-indexed)
            slot: Slot index (0-indexed)
            
        Returns:
            dict: Pokemon data, or None if slot was empty
        """
        pokemon = self.get_pokemon_at(box_number, slot)
        if pokemon:
            self.clear_slot(box_number, slot)
            return pokemon
        return None
    
    def move_pokemon(self, from_box, from_slot, to_box, to_slot):
        """
        Move a Pokemon within storage.
        
        Args:
            from_box, from_slot: Source location
            to_box, to_slot: Destination location
            
        Returns:
            bool: Success
        """
        pokemon = self.get_pokemon_at(from_box, from_slot)
        if not pokemon:
            return False
        
        # Get existing Pokemon at destination (for swap)
        dest_pokemon = self.get_pokemon_at(to_box, to_slot)
        
        # Set destination
        if not self.set_pokemon_at(to_box, to_slot, pokemon):
            return False
        
        # Set source (swap or clear)
        if dest_pokemon:
            self.set_pokemon_at(from_box, from_slot, dest_pokemon)
        else:
            self.clear_slot(from_box, from_slot)
        
        return True
    
    def get_box_count(self):
        """Get number of boxes"""
        return NUM_BOXES
    
    def get_slots_per_box(self):
        """Get number of slots per box"""
        return SLOTS_PER_BOX
    
    def get_total_pokemon_count(self):
        """Get total number of Pokemon in storage"""
        if not self.is_loaded():
            return 0
        
        count = 0
        for box in self.data["boxes"]:
            for p in box["slots"]:
                if p is not None:
                    count += 1
        return count
    
    def get_box_pokemon_count(self, box_number):
        """Get number of Pokemon in a specific box"""
        if not self.is_loaded():
            return 0
        
        idx = box_number - 1
        if 0 <= idx < len(self.data["boxes"]):
            return sum(1 for p in self.data["boxes"][idx]["slots"] if p is not None)
        return 0


# Global singleton instance
_sinew_storage = None


def get_sinew_storage():
    """Get the global SinewStorage instance"""
    global _sinew_storage
    if _sinew_storage is None:
        _sinew_storage = SinewStorage()
    return _sinew_storage


def reload_sinew_storage():
    """Force reload of Sinew storage"""
    global _sinew_storage
    _sinew_storage = SinewStorage()
    return _sinew_storage