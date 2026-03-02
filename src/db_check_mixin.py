#!/usr/bin/env python3

"""
db_check_mixin.py — database existence/completeness checks and DB builder launcher.
"""

import json
import os

from config import DATA_DIR
from db_builder_screen import DBBuilder
from game_dialogs import DBWarningPopup


class DBCheckMixin:
    """Mixin that provides database-check helpers and the DB-builder launcher."""

    def _open_db_builder(self):
        """Open the database builder screen (called from Settings)"""
        # Close current modal (Settings) and open DB Builder
        self._close_modal()

        # Get modal dimensions
        modal_w = self.width - 40
        modal_h = self.height - 40

        # Open DB Builder
        if DBBuilder:
            self.modal_instance = DBBuilder(
                modal_w, modal_h, close_callback=self._close_modal
            )
        else:
            print("[Sinew] DBBuilder not available")

    def _check_database(self):
        """Check if the Pokemon database exists and is complete"""
        db_path = os.path.join(DATA_DIR, "pokemon_db.json")
        # Check if database file exists
        if not os.path.exists(db_path):
            print(f"[Sinew] Pokemon database not found: {db_path}")
            self._show_db_warning(
                "Pokemon database not found",
                "The database needs to be built before you can use all features.",
            )
            return False

        # Check if database has all Pokemon (386 for Gen 3)
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db = json.load(f)

            # Count Pokemon entries (keys that are 3-digit numbers)
            pokemon_count = sum(
                1 for key in db.keys() if key.isdigit() and len(key) == 3
            )

            if pokemon_count < 386:
                print(f"[Sinew] Pokemon database incomplete: {pokemon_count}/386")
                self._show_db_warning(
                    "Pokemon database incomplete",
                    f"Only {pokemon_count}/386 Pokemon found. Build the database to get all data.",
                )
                return False

            print(f"[Sinew] Pokemon database OK: {pokemon_count} Pokemon")
            return True

        except Exception as e:
            print(f"[Sinew] Error checking database: {e}")
            self._show_db_warning("Database error", f"Could not read database: {e}")
            return False

    def _show_db_warning(self, title, message):
        """Show a warning popup about the database"""
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
        """Open DB builder from the warning popup"""
        self._close_modal()

        modal_w = self.width - 40
        modal_h = self.height - 40

        if DBBuilder:
            self.modal_instance = DBBuilder(
                modal_w, modal_h, close_callback=self._close_modal
            )
