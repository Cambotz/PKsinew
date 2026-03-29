#!/usr/bin/env python3

"""
save_load_mixin.py — save file loading and reloading helpers for GameScreen.

All methods delegate to SaveDataManager (save_data_manager.py).
"""

import os

from save_data_manager import get_manager


class SaveLoadMixin:
    """Mixin providing save-file load/reload helpers to GameScreen."""

    def _load_current_save(self):
        """Load save file for current game (skip for Sinew)
        Uses find_save_file() to get the newest save across all formats."""
        gname = self.game_names[self.current_game]

        if self.is_on_sinew():
            return

        # Get ROM path to determine save basename
        rom_path = self.games[gname].get("rom")
        if not rom_path:
            # No ROM, try cached sav path as fallback
            sav_path = self.games[gname].get("sav")
            if sav_path and os.path.exists(sav_path):
                manager = get_manager()
                manager.load_save(sav_path, game_hint=gname if gname != "Sinew" else None)
            else:
                get_manager().unload()
            return
        
        # Import find_save_file from emulator_session
        from emulator_session import find_save_file
        
        # Determine save directory
        rom_base = os.path.splitext(os.path.basename(rom_path))[0]
        use_ext = self.settings.get("use_emulator_provider", False)
        if use_ext and hasattr(self, 'emulator_manager') and self.emulator_manager:
            provider = self.emulator_manager.active_provider
            save_dir = getattr(provider, "saves_dir", None) if provider else None
        else:
            save_dir = None
        
        if not save_dir:
            from config import SAVES_DIR
            save_dir = SAVES_DIR
        
        # Find newest save file
        sav_path = find_save_file(rom_base, save_dir)

        if sav_path and os.path.exists(sav_path):
            manager = get_manager()
            manager.load_save(sav_path, game_hint=gname if gname != "Sinew" else None)
            # Update cached path
            self.games[gname]["sav"] = sav_path
        else:
            if rom_path is not None:
                print(f"Save file not found for: {rom_base}")
            # Clear stale data so screens show empty/default state
            get_manager().unload()

    def _reload_save_for_game(self, game_name):
        """Reload save for a specific game if it's currently active"""
        if game_name not in self.games:
            return False

        # If this is the current game, reload immediately
        current_game_name = self.game_names[self.current_game]
        if current_game_name == game_name:
            sav_path = self.games[game_name].get("sav")
            if sav_path and os.path.exists(sav_path):
                manager = get_manager()
                # Use load_save to ensure we use the CURRENT path from self.games
                # This is critical for external emu toggle - path may have changed
                manager.load_save(sav_path, game_hint=game_name)

        return True

    def _ensure_current_save_loaded(self):
        """
        Ensure SaveDataManager has the current game's save loaded from the correct path.
        Called before opening modals that display save data (Pokedex, Trainer Info, PC Box).
        Uses find_save_file() to get the newest save across all formats.
        """
        if self.is_on_sinew():
            return  # Sinew mode doesn't use SaveDataManager

        gname = self.game_names[self.current_game]
        rom_path = self.games[gname].get("rom")
        
        if not rom_path:
            # No ROM, try cached sav path as fallback
            sav_path = self.games[gname].get("sav")
        else:
            # Import find_save_file from emulator_session
            from emulator_session import find_save_file
            
            # Determine save directory
            rom_base = os.path.splitext(os.path.basename(rom_path))[0]
            use_ext = self.settings.get("use_emulator_provider", False)
            if use_ext and hasattr(self, 'emulator_manager') and self.emulator_manager:
                provider = self.emulator_manager.active_provider
                save_dir = getattr(provider, "saves_dir", None) if provider else None
            else:
                save_dir = None
            
            if not save_dir:
                from config import SAVES_DIR
                save_dir = SAVES_DIR
            
            # Find newest save file
            sav_path = find_save_file(rom_base, save_dir)
            
            # Update cached path
            if sav_path:
                self.games[gname]["sav"] = sav_path

        if sav_path and os.path.exists(sav_path):
            manager = get_manager()

            # Check if manager has the CURRENT path loaded
            # If not (or if path changed), load it
            if manager.current_save_path != sav_path:
                print(f"[SaveLoad] Loading save from current location: {sav_path}")
                manager.load_save(sav_path, game_hint=gname)
            elif manager.loaded:
                # Same path, but force reload to get fresh data from disk
                print(f"[SaveLoad] Reloading save from: {sav_path}")
                manager.reload()
        else:
            # No save file for current game - unload stale data
            manager = get_manager()
            if manager.loaded:
                manager.unload()

    def _force_reload_current_save(self):
        """Force reload save file for current game, clearing cache.
        Used when returning from emulator to ensure fresh data.
        Uses find_save_file() to get the newest save across all formats."""
        gname = self.game_names[self.current_game]

        if self.is_on_sinew():
            return

        # Get ROM path to determine save basename
        rom_path = self.games[gname].get("rom")
        if not rom_path:
            return
        
        # Import find_save_file from emulator_session
        from emulator_session import find_save_file
        
        # Determine save directory (same logic as emulator_session)
        rom_base = os.path.splitext(os.path.basename(rom_path))[0]
        
        # Check if using external provider
        use_ext = self.settings.get("use_emulator_provider", False)
        if use_ext and hasattr(self, 'emulator_manager') and self.emulator_manager:
            provider = self.emulator_manager.active_provider
            save_dir = getattr(provider, "saves_dir", None) if provider else None
        else:
            save_dir = None
        
        # Fallback to internal saves directory
        if not save_dir:
            from config import SAVES_DIR
            save_dir = SAVES_DIR
        
        # Find newest save file across all formats
        sav_path = find_save_file(rom_base, save_dir)
        
        if sav_path and os.path.exists(sav_path):
            manager = get_manager()
            # Evict cache entry for this path so we get fresh bytes from disk
            from save_data_manager import _save_cache
            if sav_path in _save_cache:
                del _save_cache[sav_path]
            # Load the newest save file
            manager.load_save(sav_path, game_hint=gname)
            print(f"[Sinew] Force reloaded save for {gname}: {sav_path}")
            
            # Update the cached path in self.games so other code uses correct path
            self.games[gname]["sav"] = sav_path