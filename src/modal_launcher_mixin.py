#!/usr/bin/env python3

"""
modal_launcher_mixin.py — Menu dispatch logic.
"""

import os

from pc_box import PCBox
from trainerinfo import Modal as TrainerInfoModal
from achievements import Modal as AchievementsModal
from settings import Settings
from db_builder_screen import DBBuilder
from PokedexModal import PokedexModal
from export_modal import ExportModal
from events_screen import EventsModal
from game_dialogs import PlaceholderModal
from save_data_manager import get_manager


class ModalLauncherMixin:
    """Mixin that provides the _open_menu dispatcher."""

    def _open_menu(self, name):
        """Open a menu item"""
        if name == "Launch Game":
            self._launch_game()
            return

        if name == "Save File Only":
            # No ROM available - show informational notification, do nothing else
            gname = self.game_names[self.current_game]
            self._show_notification(
                f"{gname}: No ROM found",
                "Place a matching .gba ROM in the roms/ folder",
            )
            return

        if name == "Resume Game":
            # Resume the currently paused game
            if self.emulator and self.emulator.loaded:
                self._stop_menu_music()  # Stop menu music when resuming game
                self.emulator.resume()
                self.emulator_active = True
                # Switch to emulator resolution
                if self.scaler:
                    self.scaler.set_virtual_resolution(240, 160)
                print("[Sinew] Resuming game via menu")
            return

        if name == "Stop Game":
            # Stop the currently running game
            self._stop_game()
            return

        if name == "Quit Sinew":
            # Quit the application
            self._quit_sinew()
            return

        if name.startswith("Playing:"):
            # Show notification about currently playing game
            running_game = self._get_running_game_name()
            self._show_notification(
                f"Currently playing: {running_game}",
                self._get_pause_combo_hint_text("return"),
            )
            return

        modal_w = self.width - 30
        modal_h = self.height - 30

        # Ensure current save is loaded from correct path before opening save-dependent modals
        # This is critical when external emu toggle changes - path may have changed
        if name in ["Pokedex", "PC Box", "Trainer Info"]:
            self._ensure_current_save_loaded()

        if name == "Pokedex" and PokedexModal:
            # Check if database exists first
            if not self._check_database():
                return

            try:
                # Always collect save paths for potential combined mode
                all_save_paths = []
                for gname, gdata in self.games.items():
                    if gname != "Sinew":
                        sav = gdata.get("sav")
                        if sav and os.path.exists(sav):
                            all_save_paths.append(sav)

                # Check if we're on Sinew (combined mode)
                if self.is_on_sinew():
                    # Combined mode - merged view from all saves
                    self.modal_instance = PokedexModal(
                        close_callback=self._close_modal,
                        get_current_game_callback=self.get_current_game_name,
                        set_game_callback=self._set_game_by_name,
                        prev_game_callback=lambda: self._change_game_include_sinew(-1),
                        next_game_callback=lambda: self._change_game_include_sinew(1),
                        combined_mode=True,
                        all_save_paths=all_save_paths,
                        width=self.width,
                        height=self.height,
                    )
                else:
                    # Single game mode - use current save via manager
                    # Still pass all_save_paths so user can switch to combined mode
                    self.modal_instance = PokedexModal(
                        close_callback=self._close_modal,
                        get_current_game_callback=self.get_current_game_name,
                        set_game_callback=self._set_game_by_name,
                        prev_game_callback=lambda: self._change_game_include_sinew(-1),
                        next_game_callback=lambda: self._change_game_include_sinew(1),
                        save_data_manager=get_manager(),
                        all_save_paths=all_save_paths,
                        width=self.width,
                        height=self.height,
                    )
            except FileNotFoundError:
                self._show_db_warning(
                    "Pokemon database not found",
                    "Build the database first to use the Pokedex.",
                )
                return
        elif name == "PC Box" and PCBox:
            # Pass the combined reload callbacks so modal arrows update everything
            # Include Sinew in the cycle - it has its own storage
            self.modal_instance = PCBox(
                modal_w,
                modal_h,
                self.font,
                close_callback=self._close_modal,
                prev_game_callback=lambda: self._change_game_include_sinew(-1),
                next_game_callback=lambda: self._change_game_include_sinew(1),
                get_current_game_callback=self.get_current_game_name,
                is_game_running_callback=self._get_running_game_name,
                reload_save_callback=self._reload_save_for_game,
                resume_game_callback=self._resume_game_from_modal,
            )
        elif name == "Trainer Info" and TrainerInfoModal:
            self.modal_instance = TrainerInfoModal(
                modal_w,
                modal_h,
                self.font,
                prev_game_callback=lambda: self._change_game_skip_sinew_no_debounce(-1),
                next_game_callback=lambda: self._change_game_skip_sinew_no_debounce(1),
                get_current_game_callback=self.get_current_game_name,
            )
        elif name == "Achievements" and AchievementsModal:
            self.modal_instance = AchievementsModal(
                modal_w,
                modal_h,
                self.font,
                get_current_game_callback=self.get_current_game_name,
            )
        elif name == "Settings" and Settings:
            self.modal_instance = Settings(
                modal_w,
                modal_h,
                self.font,
                close_callback=self._close_modal,
                music_mute_callback=self._set_menu_music_muted,
                fullscreen_callback=self._set_fullscreen,
                swap_ab_callback=self._set_swap_ab,
                db_builder_callback=self._open_db_builder,
                scaler=self.scaler,
                reload_combo_callback=self._reload_pause_combo_setting,
                emulator_provider_callback=self._on_emulator_provider_toggled,
            )
        elif name == "Export" and ExportModal:
            current_game = self.get_current_game_name()
            self.modal_instance = ExportModal(
                modal_w,
                modal_h,
                game_name=current_game,
                close_callback=self._close_modal,
            )
        elif name == "Events" and EventsModal:
            # Events modal - for claiming mystery event items
            # Pass the current game name from the game screen (determined by filename)
            current_game_name = self.get_current_game_name()
            self.modal_instance = EventsModal(
                modal_w,
                modal_h,
                self.font,
                on_close=self._close_modal,
                on_event_claimed=self._on_event_claimed,
                game_name=current_game_name,
            )
        elif name == "DB Builder" and DBBuilder:
            self.modal_instance = DBBuilder(
                modal_w, modal_h, close_callback=self._close_modal
            )
        else:
            # Placeholder modal
            self.modal_instance = PlaceholderModal(
                name, modal_w, modal_h, self.font, self._close_modal
            )
