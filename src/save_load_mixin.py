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
        """Load save file for current game (skip for Sinew)"""
        gname = self.game_names[self.current_game]

        if self.is_on_sinew():
            return

        sav_path = self.games[gname].get("sav")

        if sav_path and os.path.exists(sav_path):
            manager = get_manager()
            manager.load_save(sav_path, game_hint=gname if gname != "Sinew" else None)
        else:
            if sav_path is not None:
                print(f"Save file not found: {sav_path}")
            # Clear stale data so screens show empty/default state
            # instead of the previously loaded game's data
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

        This is critical when external emulator toggle changes - self.games[gname]["sav"]
        updates to the new path, but SaveDataManager might still have old path cached.
        """
        if self.is_on_sinew():
            return  # Sinew mode doesn't use SaveDataManager

        gname = self.game_names[self.current_game]
        sav_path = self.games[gname].get("sav")

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
        Always loads from self.games[gname]['sav'] so the external-emulator
        save path is respected rather than whatever path the manager last used."""
        gname = self.game_names[self.current_game]

        if self.is_on_sinew():
            return

        sav_path = self.games[gname].get("sav")

        if sav_path and os.path.exists(sav_path):
            manager = get_manager()
            # Evict cache entry for this path so we get fresh bytes from disk
            from save_data_manager import _save_cache
            if sav_path in _save_cache:
                del _save_cache[sav_path]
            # Always call load_save with the current path — this handles both the
            # normal case and the external-emulator case where the path may have
            # changed since the manager last loaded.
            manager.load_save(sav_path, game_hint=gname)
            print(f"[Sinew] Force reloaded save for {gname}: {sav_path}")
