#!/usr/bin/env python3

"""
db_check_mixin.py — Sprite/database existence checks and DB builder launcher.

Now sprite-pack aware: checks the currently selected global sprite pack.
"""

import os

from config import DATA_DIR
from db_builder_screen import DBBuilder
from game_dialogs import DBWarningPopup
from sprite_pack_manager import get_sprite_pack_manager

# Consider pack "usable" if it has at least 100 sprites
# (supports Gen 1 packs with 151, and partial packs)
REQUIRED_SPRITE_COUNT = 100


class DBCheckMixin:
    """Mixin that provides database-check helpers and the DB-builder launcher."""

    def _open_db_builder(self):
        """Open the database builder screen (called from Settings)."""
        self._close_modal()

        modal_w = self.width - 40
        modal_h = self.height - 40

        if DBBuilder:
            self.modal_instance = DBBuilder(
                modal_w, modal_h, close_callback=self._close_modal
            )
        else:
            print("[Sinew] DBBuilder not available")

    def _check_database(self) -> bool:
        """
        Check whether the currently selected sprite pack is usable.

        Returns True only when the active pack has at least
        REQUIRED_SPRITE_COUNT sprites (100+, supports Gen 1 packs).
        """
        # Get the currently active global sprite pack
        manager = get_sprite_pack_manager()
        global_pack_id = manager.preferences.get("global_pack", "gen3_emerald")
        pack = manager.get_pack(global_pack_id)
        
        if not pack:
            print(f"[Sinew] No sprite pack selected")
            self._show_db_warning(
                "No sprite pack",
                "No sprite pack is selected. Open the DB Builder to download sprites.",
            )
            return False
        
        sprite_dir = pack.normal_dir
        
        if not os.path.isdir(sprite_dir):
            print(f"[Sinew] Sprite directory not found: {sprite_dir}")
            self._show_db_warning(
                "Sprites not found",
                f"Sprite pack '{pack.display_name}' not found. Download it in the DB Builder.",
            )
            return False

        # Use the pack's built-in sprite count method (handles both PNG and GIF)
        sprite_count = pack.get_sprite_count()

        if sprite_count < REQUIRED_SPRITE_COUNT:
            print(
                f"[Sinew] Sprite pack incomplete: {sprite_count}/{REQUIRED_SPRITE_COUNT}"
            )
            self._show_db_warning(
                "Sprite pack incomplete",
                f"Pack '{pack.display_name}' has {sprite_count} sprites. "
                "At least 100 are required. Download more in the DB Builder.",
            )
            return False

        print(f"[Sinew] Sprite check OK: {sprite_count} sprites in '{pack.display_name}'")
        return True

    def _show_db_warning(self, title: str, message: str):
        """Show a warning popup about missing/incomplete sprites."""
        modal_w = self.width - 80
        modal_h = 180
        self.modal_instance = DBWarningPopup(
            modal_w,
            modal_h,
            title,
            message,
            build_callback=self._open_db_builder_from_warning,
            close_callback=self._close_modal,
            screen_size=(self.width, self.height),
        )

    def _open_db_builder_from_warning(self):
        """Open DB builder from the warning popup."""
        self._close_modal()

        modal_w = self.width - 40
        modal_h = self.height - 40

        if DBBuilder:
            self.modal_instance = DBBuilder(
                modal_w, modal_h, close_callback=self._close_modal
            )