#!/usr/bin/env python3

"""
sprite_pack_manager.py — Manages multiple sprite packs and per-game sprite preferences.

Each sprite pack lives in its own folder:
  data/sprites/packs/{pack_id}/normal/
  data/sprites/packs/{pack_id}/shiny/

Integrates with sprite_pack_selector.py for official PokeAPI packs.

User can:
  - Download official sprite packs from PokeAPI
  - Drop custom packs into the folder
  - Select different packs per game
  - Switch active pack globally
"""

import json
import os
from typing import Dict, Optional, List

from config import SPRITES_DIR, DATA_DIR, PACKS_DIR

# Import official pack definitions
try:
    from sprite_pack_selector import SPRITE_PACKS, SPRITE_PACK_BY_ID
except ImportError:
    SPRITE_PACKS = []
    SPRITE_PACK_BY_ID = {}

# Preferences file
PACK_PREFERENCES_FILE = os.path.join(DATA_DIR, "sprite_pack_preferences.json")

# Create packs directory if it doesn't exist
os.makedirs(PACKS_DIR, exist_ok=True)


class SpritePackInfo:
    """Information about a sprite pack"""
    
    def __init__(self, pack_id: str, pack_dir: str, is_custom: bool = False, official_def: Optional[Dict] = None):
        self.pack_id = pack_id
        self.pack_dir = pack_dir
        self.normal_dir = os.path.join(pack_dir, "normal")
        self.shiny_dir = os.path.join(pack_dir, "shiny")
        self.is_custom = is_custom
        self.official_def = official_def  # Reference to sprite_pack_selector definition
        
        # Try to load metadata
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict:
        """Load pack metadata from pack.json if it exists, or from official definition"""
        metadata_path = os.path.join(self.pack_dir, "pack.json")
        
        # Try loading from pack.json first
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Use official definition if available
        if self.official_def:
            return {
                "name": self.official_def.get("display_name", self.pack_id),
                "description": self.official_def.get("description", "Official sprite pack"),
                "has_shiny": self.official_def.get("has_shiny", False),
                "file_ext": self.official_def.get("file_ext", "png"),
                "author": "PokeAPI",
                "custom": False,
                "note": self.official_def.get("note"),
            }
        
        # Default metadata for custom packs without pack.json
        return {
            "name": self.pack_id.replace("_", " ").title(),
            "description": "Custom sprite pack",
            "has_shiny": os.path.isdir(self.shiny_dir),
            "file_ext": self._detect_file_ext(),
            "author": "Unknown",
            "custom": True,
        }
    
    def _detect_file_ext(self) -> str:
        """Auto-detect file extension by checking what exists in normal dir"""
        if not os.path.isdir(self.normal_dir):
            return "png"
        
        # Count each extension type
        png_count = 0
        gif_count = 0
        
        for fname in os.listdir(self.normal_dir):
            if fname[:-4].isdigit() and len(fname[:-4]) == 3:
                if fname.endswith('.png'):
                    png_count += 1
                elif fname.endswith('.gif'):
                    gif_count += 1
        
        # Return the most common extension
        if gif_count > png_count:
            return "gif"
        elif png_count > 0:
            return "png"
        
        # Fallback: check for Pikachu specifically
        for ext in ["gif", "png"]:
            if os.path.exists(os.path.join(self.normal_dir, f"025.{ext}")):
                return ext
        
        return "png"
    
    def get_sample_sprite_path(self) -> Optional[str]:
        """Get path to Pikachu sprite for preview (025.gif or 025.png)"""
        ext = self.metadata.get("file_ext", "png")
        sample_path = os.path.join(self.normal_dir, f"025.{ext}")
        
        if os.path.exists(sample_path):
            return sample_path
        
        # Fallback to any extension
        for ext in ["gif", "png"]:
            fallback = os.path.join(self.normal_dir, f"025.{ext}")
            if os.path.exists(fallback):
                return fallback
        
        return None
    
    def is_downloaded(self) -> bool:
        """Check if pack is downloaded (has at least 100 sprites - supports Gen 1 packs)"""
        if not os.path.isdir(self.normal_dir):
            return False
        
        # Count both PNG and GIF files to be safe
        count = 0
        for f in os.listdir(self.normal_dir):
            # Check if it's a numbered sprite (001.png, 025.gif, etc.)
            if f[:-4].isdigit() and len(f[:-4]) == 3:
                if f.endswith('.png') or f.endswith('.gif'):
                    count += 1
        
        return count >= 100  # Accept Gen 1 packs (151) and any pack with 100+
    
    def get_sprite_count(self) -> int:
        """Get count of downloaded sprites"""
        if not os.path.isdir(self.normal_dir):
            return 0
        
        # Count both PNG and GIF files to be safe
        count = 0
        for f in os.listdir(self.normal_dir):
            # Check if it's a numbered sprite (001.png, 025.gif, etc.)
            if f[:-4].isdigit() and len(f[:-4]) == 3:
                if f.endswith('.png') or f.endswith('.gif'):
                    count += 1
        
        return count
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        return self.metadata.get("name", self.pack_id)
    
    @property
    def description(self) -> str:
        """Get description for UI"""
        return self.metadata.get("description", "")
    
    @property
    def author(self) -> str:
        """Get author name"""
        return self.metadata.get("author", "Unknown")
    
    @property
    def has_shiny(self) -> bool:
        """Check if pack includes shiny sprites"""
        return self.metadata.get("has_shiny", False)
    
    @property
    def note(self) -> Optional[str]:
        """Get optional note about the pack"""
        return self.metadata.get("note")


class SpritePackManager:
    """Manages sprite packs and preferences"""
    
    def __init__(self):
        self.packs: Dict[str, SpritePackInfo] = {}
        self.preferences = self._load_preferences()
        self._scan_packs()
    
    def _load_preferences(self) -> Dict:
        """Load sprite pack preferences from JSON"""
        if os.path.exists(PACK_PREFERENCES_FILE):
            try:
                with open(PACK_PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default preferences
        return {
            "global_pack": "gen3_emerald",  # Default pack
            "per_game": {},  # {"Ruby": "gen3_ruby", "Emerald": "gen3_emerald", ...}
        }
    
    def _save_preferences(self):
        """Save preferences to JSON"""
        try:
            with open(PACK_PREFERENCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            print(f"[SpritePackManager] Failed to save preferences: {e}")
    
    def _scan_packs(self):
        """Scan packs directory for official and custom packs"""
        
        # First, register all official packs from sprite_pack_selector
        # These may or may not be downloaded yet
        for official_pack in SPRITE_PACKS:
            pack_id = official_pack["id"]
            pack_path = os.path.join(PACKS_DIR, pack_id)
            
            # Create SpritePackInfo with official definition
            pack_info = SpritePackInfo(
                pack_id, 
                pack_path, 
                is_custom=False,
                official_def=official_pack
            )
            self.packs[pack_id] = pack_info
        
        # Then scan for any custom packs (directories not in official list)
        if os.path.isdir(PACKS_DIR):
            for pack_name in os.listdir(PACKS_DIR):
                # Skip if already registered as official pack
                if pack_name in self.packs:
                    continue
                
                pack_path = os.path.join(PACKS_DIR, pack_name)
                
                # Must be a directory with a normal subfolder
                if not os.path.isdir(pack_path):
                    continue
                
                normal_dir = os.path.join(pack_path, "normal")
                if not os.path.isdir(normal_dir):
                    continue
                
                # Register as custom pack
                pack_info = SpritePackInfo(pack_name, pack_path, is_custom=True)
                self.packs[pack_name] = pack_info
    
    def get_pack(self, pack_id: str) -> Optional[SpritePackInfo]:
        """Get sprite pack by ID"""
        return self.packs.get(pack_id)
    
    def get_all_packs(self) -> List[SpritePackInfo]:
        """Get all available sprite packs (both downloaded and not downloaded)"""
        return list(self.packs.values())
    
    def get_downloaded_packs(self) -> List[SpritePackInfo]:
        """Get only packs that are actually downloaded"""
        return [p for p in self.packs.values() if p.is_downloaded()]
    
    def get_official_packs(self) -> List[SpritePackInfo]:
        """Get only official sprite packs"""
        return [p for p in self.packs.values() if not p.is_custom]
    
    def get_custom_packs(self) -> List[SpritePackInfo]:
        """Get only custom sprite packs"""
        return [p for p in self.packs.values() if p.is_custom]
    
    def get_pack_for_game(self, game_name: str) -> SpritePackInfo:
        """Get the sprite pack to use for a specific game"""
        # Check per-game preference first
        pack_id = self.preferences.get("per_game", {}).get(game_name)
        
        if pack_id and pack_id in self.packs:
            pack = self.packs[pack_id]
            # Only use if downloaded
            if pack.is_downloaded():
                return pack
        
        # Fall back to global pack
        global_pack_id = self.preferences.get("global_pack", "gen3_emerald")
        
        if global_pack_id in self.packs:
            pack = self.packs[global_pack_id]
            if pack.is_downloaded():
                return pack
        
        # Last resort: return first downloaded pack
        downloaded = self.get_downloaded_packs()
        if downloaded:
            return downloaded[0]
        
        # No packs downloaded - return the default pack even if not downloaded
        # (This will cause sprite loading to fail but at least won't crash)
        if global_pack_id in self.packs:
            return self.packs[global_pack_id]
        
        # Absolute last resort
        if self.packs:
            return list(self.packs.values())[0]
        
        return None
    
    def set_global_pack(self, pack_id: str):
        """Set the global default sprite pack"""
        if pack_id in self.packs:
            self.preferences["global_pack"] = pack_id
            self._save_preferences()
    
    def set_game_pack(self, game_name: str, pack_id: str):
        """Set sprite pack for a specific game"""
        if pack_id in self.packs:
            if "per_game" not in self.preferences:
                self.preferences["per_game"] = {}
            
            self.preferences["per_game"][game_name] = pack_id
            self._save_preferences()
    
    def clear_game_pack(self, game_name: str):
        """Clear game-specific pack (use global default)"""
        if "per_game" in self.preferences:
            self.preferences["per_game"].pop(game_name, None)
            self._save_preferences()
    
    def get_sprite_path(self, pack_id: str, pokemon_id: int, shiny: bool = False) -> Optional[str]:
        """Get sprite path for a Pokemon in a specific pack"""
        pack = self.get_pack(pack_id)
        if not pack:
            return None
        
        sprite_dir = pack.shiny_dir if shiny else pack.normal_dir
        ext = pack.metadata.get("file_ext", "png")
        sprite_path = os.path.join(sprite_dir, f"{pokemon_id:03d}.{ext}")
        
        return sprite_path if os.path.exists(sprite_path) else None
    
    def refresh(self):
        """Rescan packs directory"""
        self.packs.clear()
        self._scan_packs()


# Global instance
_manager = None


def get_sprite_pack_manager() -> SpritePackManager:
    """Get the global sprite pack manager instance"""
    global _manager
    if _manager is None:
        _manager = SpritePackManager()
    return _manager