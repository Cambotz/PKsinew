#!/usr/bin/env python3

"""
emulator_session.py - Game session lifecycle mixin for GameScreen

Orchestrates the full lifecycle of launching, running, pausing, and stopping
a game session from Sinew's perspective.  Two backends are supported:

  Integrated  — MgbaEmulator  (mgba_emulator.py)
                libretro/mGBA core running inside the Sinew process.

  External    — ExternalEmulator  (external_emulator.py)
                A provider-based launcher that hands off to a system emulator
                and watches the process for exit.

Entry points called by GameScreen.update() / menu handlers:
  _launch_game()             — decide which backend to use and start a session
  _stop_emulator()           — save SRAM, unload, return to Sinew menu
  _update_emulator()         — per-frame tick while a session is active
  _draw_emulator()           — render the emulator surface (integrated only)

Supporting methods:
  _launch_integrated_emulator()   — initialise + load ROM into MgbaEmulator
  _launch_external_emulator()     — hand off to ExternalEmulator provider
  _on_external_emulator_closed()  — background-thread callback on process exit
  _on_external_emu_toggled()      — rebuild game list when toggle changes
  _show_return_loading_screen()   — brief "Returning to Sinew…" splash
"""

import builtins
import os
import threading
import time
from datetime import datetime

import pygame

from config import (
    CORES_DIR,
    DATA_DIR,
    FONT_PATH,
    MGBA_CORE_PATH,
    ROMS_DIR,
    SAVES_DIR,
    SYSTEM_DIR,
)
from game_detection import (
    GAME_SAVE_ONLY,
    _rom_scan_cache,
)
from save_data_manager import get_manager

try:
    from mgba_emulator import MgbaEmulator
    EMULATOR_AVAILABLE = True
except ImportError:
    MgbaEmulator = None
    EMULATOR_AVAILABLE = False


class EmulatorSessionMixin:
    """
    Mixin providing game session lifecycle management for GameScreen.

    Expects the host class to have (among others):
        self.emulator              MgbaEmulator | None
        self.emulator_active       bool
        self.external_emu          ExternalEmulator | None
        self.scaler                scaler object | None
        self.controller            controller object | None
        self.settings              dict
        self.games / self.game_names / self.current_game
        self._emulator_pause_combo_released  bool
        self._ext_emu_closed_needs_reload    bool

    Also calls other GameScreen / mixin methods:
        self._stop_menu_music() / self._start_menu_music()
        self._show_notification() / self._get_pause_combo_hint_text()
        self._check_emulator_pause_combo() / self._check_achievements_for_current_game()
        self._force_reload_current_save() / self._reload_settings_from_disk()
        self._draw_loading_screen() / self.load_game_and_background()
        self.is_on_sinew()
    """

    # ------------------------------------------------------------------
    # Top-level launch dispatcher
    # ------------------------------------------------------------------

    def _launch_game(self):
        """Launch the current game ROM via whichever backend is appropriate."""
        if self.is_on_sinew():
            print("Sinew is a combined view - no game to launch")
            return

        # Already running a game?
        if self.emulator and self.emulator.loaded:
            running_game = "Unknown"
            if self.emulator.rom_path:
                running_game = os.path.splitext(
                    os.path.basename(self.emulator.rom_path)
                )[0]
            self._show_notification(
                f"Currently playing: {running_game}",
                self._get_pause_combo_hint_text("return"),
            )
            return

        gname = self.game_names[self.current_game]
        rom_path = self.games[gname].get("rom")
        sav_path = self.games[gname].get("sav")

        if not rom_path or not os.path.exists(rom_path):
            if self.games[gname].get("availability") == GAME_SAVE_ONLY:
                self._show_notification(
                    f"{gname}: No ROM found",
                    "Place a matching .gba ROM in the roms/ folder",
                )
            else:
                print(f"ROM not found: {rom_path}")
            return

        use_external = getattr(builtins, "SINEW_USE_EXTERNAL_EMULATOR", False)

        if (
            use_external
            and self.external_emu
            and self.external_emu.active_provider
        ):
            if self._launch_external_emulator(rom_path, sav_path):
                return
            print("[ExternalEmu] External emulator failed — falling back to integrated mGBA")

        if EMULATOR_AVAILABLE and MgbaEmulator:
            try:
                self._launch_integrated_emulator(rom_path, sav_path)
            except Exception as e:
                print(f"Integrated emulator failed: {e}")
                print("No compatible emulator core found for this platform.")

    # ------------------------------------------------------------------
    # External backend
    # ------------------------------------------------------------------

    def _launch_external_emulator(self, rom_path, sav_path):
        """
        Launch via ExternalEmulator provider.

        Save strategy: sav_path already points to the external emulator's save
        directory (set by _init_games when the external-emu toggle is ON).
        No copying needed — Sinew and the external emulator share the same file.

        Returns True on success, False on failure.
        """
        provider = self.external_emu.active_provider
        print(
            f"[ExternalEmu] Launching {type(provider).__name__} — ROM: {os.path.basename(rom_path)}"
        )
        if sav_path:
            print(f"[ExternalEmu] Save: {sav_path}")

        success = self.external_emu.launch(rom_path, self.controller)
        if not success:
            print(
                f"[ExternalEmu] External emulator launch failed for {os.path.basename(rom_path)}"
            )
            return False

        self.emulator_active = True
        self._stop_menu_music()

        def _watch():
            try:
                self.external_emu.process.wait()
            except Exception:
                pass
            self._on_external_emulator_closed()

        threading.Thread(target=_watch, daemon=True).start()
        return True

    def _on_external_emulator_closed(self):
        """
        Called from a background thread when the external emulator process exits.
        Sets a flag; the main thread acts on it in update() where it is safe to
        touch pygame and save state.
        """
        self.emulator_active = False
        self._ext_emu_closed_needs_reload = True
        print("[ExternalEmu] External emulator closed")

    # ------------------------------------------------------------------
    # Integrated backend
    # ------------------------------------------------------------------

    def _launch_integrated_emulator(self, rom_path, sav_path):
        """Initialise MgbaEmulator (if needed) and load the ROM."""
        if self.emulator is None:
            self.emulator = MgbaEmulator(
                core_path=MGBA_CORE_PATH,
                save_dir=SAVES_DIR,
                system_dir=SYSTEM_DIR,
                cores_dir=CORES_DIR,
            )

        self.emulator.load_rom(rom_path, sav_path)
        builtins.SINEW_EMULATOR = self.emulator
        self.emulator_active = True
        self._emulator_pause_combo_released = True
        self._stop_menu_music()

        if self.scaler:
            self.scaler.set_virtual_resolution(240, 160)

        print(f"[Sinew] Launched: {os.path.basename(rom_path)}")

    # ------------------------------------------------------------------
    # Stop / cleanup
    # ------------------------------------------------------------------

    def _show_return_loading_screen(self, message="Returning to Sinew..."):
        """Brief splash screen shown while transitioning back to the Sinew menu."""
        try:
            screen = pygame.display.get_surface()
        except Exception:
            screen = self._loading_screen
        if screen is None:
            return

        screen.fill((30, 30, 40))

        title = self.font.render("Sinew", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 3)))

        msg = self.font.render(message, True, (200, 200, 200))
        screen.blit(msg, msg.get_rect(center=(self.width // 2, self.height // 2)))

        bar_width = int(self.width * 0.6)
        bar_height = 20
        bar_x = (self.width - bar_width) // 2
        bar_y = int(self.height * 0.6)
        pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, (100, 200, 100), (bar_x, bar_y, bar_width // 2, bar_height))
        pygame.draw.rect(screen, (100, 100, 120), (bar_x, bar_y, bar_width, bar_height), 2)

        if self.scaler:
            self.scaler.blit_scaled()
        else:
            pygame.display.flip()

    def _stop_emulator(self):
        """Save SRAM, unload the integrated emulator, and return to the Sinew menu."""
        builtins.SINEW_EMULATOR = None
        if self.emulator:
            if self.emulator.paused:
                self.emulator.resume()
            self.emulator.save_sram()
            self.emulator.unload()
        self.emulator_active = False

        # Restore keyboard filter in case a KeyboardMapper left it off
        if self.controller and hasattr(self.controller, "kb_filter_enabled"):
            self.controller.kb_filter_enabled = True

        self._emulator_pause_combo_released = True

        if self.scaler:
            self.scaler.restore_virtual_resolution()
        self._show_return_loading_screen("Returning to Sinew...")

        self._reload_settings_from_disk()
        self.load_game_and_background()
        self._start_menu_music()
        print("[Sinew] Returned from game")

    # ------------------------------------------------------------------
    # Per-frame update (integrated emulator only)
    # ------------------------------------------------------------------

    def _update_emulator(self, events, dt):
        """
        Per-frame tick while the integrated emulator is active.

        Returns:
            bool: True to keep running, False if the user quit.
        """
        for event in events:
            if event.type == pygame.QUIT:
                self._stop_emulator()
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                self.emulator.save_sram()

        if not self.emulator.paused:
            self.emulator.run_frame()
        else:
            print(
                f"[Sinew] WARNING: emulator.paused={self.emulator.paused} but"
                f" emulator_active={self.emulator_active}"
            )

        combo_held = self._check_emulator_pause_combo()

        if combo_held and self._emulator_pause_combo_released:
            self._emulator_pause_combo_released = False

            if self.emulator.paused:
                # Resume game
                self._stop_menu_music()
                self.emulator.resume()
                if self.scaler:
                    self.scaler.set_virtual_resolution(240, 160)
                print("[Sinew] Resuming game")
            else:
                # Pause and return to Sinew menu
                self.emulator.pause()
                self.emulator_active = False
                if self.scaler:
                    self.scaler.restore_virtual_resolution()
                self._show_return_loading_screen("Returning to Sinew...")

                # Reload controller config for Sinew UI navigation
                if self.controller and hasattr(self.controller, "refresh_controller_config"):
                    try:
                        self.controller.refresh_controller_config()
                        print("[Sinew] Reloaded controller config after pausing")
                    except Exception as e:
                        print(f"[Sinew] Error reloading controller config: {e}")

                self._reload_settings_from_disk()

                # Re-apply swap_ab — refresh_controller_config may have reset it
                swap_ab = self.settings.get("swap_ab", False)
                if swap_ab and self.controller and hasattr(self.controller, "set_swap_ab"):
                    self.controller.set_swap_ab(True)
                    print("[Sinew] Re-applied swap_ab for menu navigation after controller refresh")

                self._force_reload_current_save()
                self._check_achievements_for_current_game()
                self._start_menu_music()
                print("[Sinew] Paused - returned to Sinew menu")

        elif not combo_held:
            self._emulator_pause_combo_released = True

        return True

    # ------------------------------------------------------------------
    # External emulator toggle handler
    # ------------------------------------------------------------------

    def _on_external_emu_toggled(self, enabled):
        """Rebuild the game list when the user toggles the external emulator setting."""
        try:
            screen = pygame.display.get_surface()
        except Exception:
            screen = self._loading_screen

        if screen:
            message = "Scanning external ROMs..." if enabled else "Scanning internal ROMs..."
            self._draw_loading_screen(screen, message, 0, 3)

        if enabled and not self.external_emu:
            try:
                from external_emulator import ExternalEmulator
                self.external_emu = ExternalEmulator()
                if self.external_emu.active_provider:
                    print(
                        f"[ExternalEmu] Provider initialized: {type(
                            self.external_emu.active_provider).__name__}"
                    )
                else:
                    print("[ExternalEmu] No provider matched this environment")
            except ImportError:
                print(
                    "[ExternalEmu] external_emulator.py not found — external emulator unavailable")

        from config import _save_scan_cache
        _rom_scan_cache.clear()
        _save_scan_cache.clear()
        print("[GameScreen] Cleared ROM and save caches for directory rescan")

        if hasattr(self, "_sinew_game_data_cache"):
            self._sinew_game_data_cache.clear()
            print("[GameScreen] Cleared achievement cache for directory rescan")

        if screen:
            self._draw_loading_screen(screen, "Scanning ROMs and saves...", 1, 3)

        self._init_games()

        # Back up external saves before Sinew starts reading/writing them
        if enabled and self.games:
            from config import BACKUPS_DIR
            import shutil
            os.makedirs(BACKUPS_DIR, exist_ok=True)
            for gname, gdata in self.games.items():
                sav = gdata.get("sav")
                if sav and os.path.exists(sav):
                    try:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        bname = os.path.basename(sav)
                        name, ext = os.path.splitext(bname)
                        backup_path = os.path.join(
                            BACKUPS_DIR, f"{name}_ext_backup_{ts}{ext}"
                        )
                        shutil.copy2(sav, backup_path)
                        print(f"[ExternalEmu] Backed up {bname} -> {os.path.basename(backup_path)}")
                    except Exception as e:
                        print(f"[ExternalEmu] Backup failed for {gname}: {e}")

        if screen:
            self._draw_loading_screen(screen, "Loading save data...", 2, 3)

        # Force SaveDataManager to reload from the new save path
        if (
            not self.is_on_sinew()
            and self.game_names
            and 0 <= self.current_game < len(self.game_names)
        ):
            gname = self.game_names[self.current_game]
            sav_path = self.games[gname].get("sav")
            if sav_path and os.path.exists(sav_path):
                manager = get_manager()
                manager.load_save(sav_path, game_hint=gname)
                print(f"[GameScreen] Loaded save from new location: {sav_path}")

        if screen:
            self._draw_loading_screen(screen, "Done!", 3, 3)
            pygame.time.wait(200)

        if not self.is_on_sinew():
            self.load_game_and_background()

        toggled = 'ON' if enabled else 'OFF'
        print(f"[GameScreen] External emulator toggled {toggled}, games reloaded")

    # ------------------------------------------------------------------
    # Draw (integrated emulator only)
    # ------------------------------------------------------------------

    def _draw_emulator(self, surf):
        """Blit the emulator frame; draw a pause overlay when mGBA is paused."""
        emu_surf = self.emulator.get_surface(scale=1)
        surf.blit(emu_surf, (0, 0))

        if self.emulator.paused:
            sw, sh = surf.get_size()
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surf.blit(overlay, (0, 0))

            try:
                pause_font = pygame.font.Font(FONT_PATH, 8)
            except Exception:
                pause_font = self.font

            pause_text = pause_font.render("PAUSED", True, (255, 255, 0))
            hint_text = pause_font.render(
                self._get_pause_combo_hint_text(), True, (200, 200, 200)
            )
            surf.blit(pause_text, pause_text.get_rect(center=(sw // 2, sh // 2 - 12)))
            surf.blit(hint_text, hint_text.get_rect(center=(sw // 2, sh // 2 + 12)))

    def _stop_game(self):
        """Stop the currently running game."""
        if self.emulator and self.emulator.loaded:
            game_name = self._get_running_game_name() or "game"
            try:
                self.emulator.save_sram()  # Save before stopping
                self.emulator.unload()
            except Exception as e:
                print(f"[Sinew] Error stopping game: {e}")
            self.emulator_active = False
            # Restore menu virtual resolution
            if self.scaler:
                self.scaler.restore_virtual_resolution()
            # Reset menu index to point at "Launch Game" for quick restart
            self.menu_index = 0
            self._show_notification(f"Stopped: {game_name}", "Game saved")
            print(f"[Sinew] Stopped game: {game_name}")

    def _quit_sinew(self):
        """Quit the Sinew application."""
        print("[Sinew] Quit requested")
        if self.emulator:
            try:
                if self.emulator.loaded:
                    self.emulator.save_sram()
                self.emulator.shutdown()
            except Exception as e:
                print(f"[Sinew] Error during shutdown: {e}")
            self.emulator = None
            self.emulator_active = False
        self.should_close = True
