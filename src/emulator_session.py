#!/usr/bin/env python3

"""
emulator_session.py - Game session lifecycle mixin for GameScreen

Orchestrates the full lifecycle of launching, running, pausing, and stopping
a game session from Sinew's perspective.  All emulator backend logic is
encapsulated in providers (providers/).  This mixin only handles session
bookkeeping: ROM resolution, provider dispatch, process watching, and UI.

Entry points called by GameScreen.update() / menu handlers:
  _launch_game()             — resolve ROM path and dispatch to active provider
  _stop_emulator()           — save SRAM, unload, return to Sinew menu
  _update_emulator()         — per-frame tick while an in-process session is active
  _draw_emulator()           — render the emulator surface (in-process providers only)

Supporting methods:
  _launch_via_provider()          — unified dispatch through EmulatorManager
  _on_emulator_provider_closed()  — background-thread callback on process exit
  _on_emulator_provider_toggled() — rebuild game list when toggle changes
  _show_return_loading_screen()   — brief "Returning to Sinew..." splash
"""

import builtins
import os
import threading
import time
from datetime import datetime

import pygame

from config import (
    DATA_DIR,
    FONT_PATH,
    ROMS_DIR,
)
from game_detection import (
    GAME_SAVE_ONLY,
    _rom_scan_cache,
)
from save_data_manager import get_manager


class EmulatorSessionMixin:
    """
    Mixin providing game session lifecycle management for GameScreen.

    Expects the host class to have (among others):
        self.emulator              emulator instance | None
        self.emulator_active       bool
        self.emulator_manager       EmulatorManager | None
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

        # If no save was found by _init_games, derive an expected path from the
        # provider's saves_dir (for external emulators) or ROMS_DIR (internal).
        # This ensures the external emulator writes to the right location and
        # Sinew can find the save when it reloads after the session ends.
        if not sav_path and rom_path:
            rom_basename = os.path.splitext(os.path.basename(rom_path))[0]
            provider = (
                self.emulator_manager.active_provider
                if self.emulator_manager
                else None
            )
            provider_saves_dir = getattr(provider, "saves_dir", None) if provider else None
            use_ext_files = self.settings.get("use_emulator_provider", False)
            if use_ext_files and provider_saves_dir:
                sav_path = os.path.join(provider_saves_dir, f"{rom_basename}.srm")
            else:
                from config import SAVES_DIR as _SAVES_DIR
                sav_path = os.path.join(_SAVES_DIR, f"{rom_basename}.sav")
            print(f"[Sinew] Derived save path: {sav_path}")

        if not rom_path or not os.path.exists(rom_path):
            if self.games[gname].get("availability") == GAME_SAVE_ONLY:
                self._show_notification(
                    f"{gname}: No ROM found",
                    "Place a matching .gba ROM in the roms/ folder",
                )
            else:
                print(f"ROM not found: {rom_path}")
            return

        # Dispatch through the provider system.
        if not self.emulator_manager or not self.emulator_manager.active_provider:
            # No provider — show error and revert to integrated
            from game_dialogs import ProviderErrorDialog
            from settings import save_sinew_settings_merged as _ssm
            import builtins

            def _revert():
                self.settings['use_emulator_provider'] = False
                builtins.SINEW_USE_EMULATOR_PROVIDER = False
                _ssm({'use_emulator_provider': False})
                try:
                    from emulator_manager import EmulatorManager
                    self.emulator_manager = EmulatorManager(use_external_providers=False)
                except Exception:
                    pass
                # Sync settings modal if open
                if hasattr(self, '_pending_settings_modal') and self._pending_settings_modal:
                    try:
                        self._pending_settings_modal.revert_provider_toggle(False)
                    except Exception:
                        pass
                self.modal_instance = None

            _pw, _ph = 400, 240
            self.modal_instance = ProviderErrorDialog(
                _pw, _ph, screen_size=(self.width, self.height),
                title="No Emulator Provider Found",
                lines=[
                    "No provider is available to launch this game.",
                    "",
                    "Switching to Sinew integrated mGBA.",
                ],
                on_accept=_revert,
            )
            return

        if not self._launch_via_provider(rom_path, sav_path):
            print("[Sinew] All providers failed — no emulator available.")

    # ------------------------------------------------------------------
    # External backend
    # ------------------------------------------------------------------

    def _launch_via_provider(self, rom_path, sav_path):
        """
        Dispatch a launch through the active EmulatorManager provider.

        Works for both in-process providers (is_integrated=True, e.g. mGBA)
        and subprocess providers (is_integrated=False, e.g. RetroArch).
        The provider owns all backend-specific logic; this method only handles
        common post-launch bookkeeping.

        For external (subprocess) providers, we wrap get_command() to inject
        --savefile <sav_path> into the RetroArch command line so the correct
        save is loaded regardless of RetroArch's default save directory config.

        Returns True on success, False on failure.
        """
        provider = self.emulator_manager.active_provider
        print(f"[Sinew] Launching {type(provider).__name__} — ROM: {os.path.basename(rom_path)}")
        if sav_path:
            print(f"[Sinew] Save: {sav_path}")

        # For external (subprocess) providers: wrap get_command to append
        # --savefile so RetroArch loads the exact save Sinew detected,
        # not whatever its config defaults to.
        _original_get_command = None
        if (
            sav_path
            and not getattr(provider, 'is_integrated', False)
            and os.path.exists(sav_path)
        ):
            _original_get_command = provider.get_command

            def _get_command_with_savefile(rom, core="auto"):
                cmd = _original_get_command(rom, core)
                if cmd:
                    # Insert --savefile before the ROM path (last arg)
                    cmd = cmd[:-1] + ["--savefile", sav_path, cmd[-1]]
                    print(f"[Sinew] Injected --savefile: {os.path.basename(sav_path)}")
                return cmd

            provider.get_command = _get_command_with_savefile

        try:
            success = self.emulator_manager.launch(
                rom_path, self.controller, sav_path=sav_path, game_screen=self
            )
        finally:
            # Always restore the original method
            if _original_get_command is not None:
                provider.get_command = _original_get_command
        if not success:
            print(f"[Sinew] Provider launch failed for {os.path.basename(rom_path)}")
            return False

        # In-process providers set emulator_active and stop music themselves
        # inside launch_integrated().  Subprocess providers need this mixin to
        # do it and to spin up a process-watcher thread.
        if not getattr(provider, 'is_integrated', False):
            self.emulator_active = True
            self._stop_menu_music()

            def _watch():
                try:
                    self.emulator_manager.process.wait()
                except Exception:
                    pass
                self._on_emulator_provider_closed()

            threading.Thread(target=_watch, daemon=True).start()

        return True

    def _on_emulator_provider_closed(self):
        """
        Called from a background thread when the external emulator process exits.
        Sets a flag; the main thread acts on it in update() where it is safe to
        touch pygame and save state.
        """
        self.emulator_active = False
        self._ext_emu_closed_needs_reload = True
        print("[EmulatorManager] Provider process closed")

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

    def _on_use_integrated_mgba(self):
        """
        Called from the mGBA tab's 'Use Integrated mGBA' toggle.

        Switches the active *emulator* to integrated mGBA without changing
        the file paths.  If external paths exist (provider had a roms_dir
        different from ROMS_DIR) we keep use_emulator_provider = True so
        the external ROMs/saves remain visible — we just run them through
        the built-in core instead of an external binary.

        The General tab 'Use External Providers' toggle is NOT flipped.
        The mGBA tab is rebuilt to show the integrated options.
        """
        from game_dialogs import ProviderSwitchDialog
        from config import ROMS_DIR, SAVES_DIR

        _pw, _ph = 400, 240

        # Determine whether external paths were in use
        info = (self.emulator_manager.get_provider_info()
                if self.emulator_manager else None)
        had_external_paths = bool(
            info and info.get("roms_dir") and info["roms_dir"] != ROMS_DIR
        )

        roms  = (info["roms_dir"] if had_external_paths else ROMS_DIR) if info else ROMS_DIR
        saves = (info["saves_dir"] or SAVES_DIR) if info else SAVES_DIR

        lines = [
            "Switching to Sinew integrated mGBA.",
        ]
        if had_external_paths:
            lines += [
                "External paths kept:",
                f"ROM paths:  {roms}",
                f"Save paths: {saves}",
            ]
        else:
            lines += [
                f"ROM paths:  {ROMS_DIR}",
                f"Save paths: {SAVES_DIR}",
            ]

        def _commit():
            import builtins
            from settings import save_sinew_settings_merged as _ssm
            try:
                from emulator_manager import EmulatorManager
                # Rebuild with external providers OFF (integrated only)
                new_manager = EmulatorManager(use_external_providers=False)
                self.emulator_manager = new_manager
            except Exception:
                pass

            # Keep use_emulator_provider ON if external paths exist — paths
            # haven't changed, only the emulator binary has.
            if not had_external_paths:
                self.settings['use_emulator_provider'] = False
                builtins.SINEW_USE_EMULATOR_PROVIDER = False
                _ssm({'use_emulator_provider': False, 'use_external_emulator': False})
            else:
                _ssm({'use_external_emulator': False})
            self.settings['use_external_emulator'] = False

            if hasattr(self, '_pending_settings_modal') and self._pending_settings_modal:
                try:
                    self._pending_settings_modal.revert_provider_toggle(
                        self.settings.get('use_emulator_provider', False)
                    )
                    self._pending_settings_modal.revert_emulator_toggle(False)
                except Exception:
                    pass
            self.modal_instance = None

        if hasattr(self, '_pending_settings_modal') and self._pending_settings_modal:
            self._pending_settings_modal = self._pending_settings_modal

        dialog = ProviderSwitchDialog(
            _pw, _ph, screen_size=(self.width, self.height),
            title="Switching to Integrated mGBA",
            lines=lines,
            on_accept=_commit,
        )
        if hasattr(self, 'modal_instance') and hasattr(self.modal_instance,
                                                        'revert_provider_toggle'):
            self._pending_settings_modal = self.modal_instance
        self.modal_instance = dialog

    def _on_external_files_toggled(self, enabled):
        """
        Toggle external file path scanning independently of the emulator binary.

        Saves use_emulator_provider and rescans games using either the active
        provider's roms_dir/saves_dir (when enabled) or Sinew's internal
        ROMS_DIR/SAVES_DIR (when disabled). Does NOT change which emulator
        binary (integrated vs external) is active.
        """
        import builtins
        from config import ROMS_DIR, SAVES_DIR, _save_scan_cache
        from settings import save_sinew_settings_merged as _ssm

        try:
            screen = pygame.display.get_surface()
        except Exception:
            screen = self._loading_screen

        self.settings['use_emulator_provider'] = enabled
        builtins.SINEW_USE_EMULATOR_PROVIDER = enabled
        _ssm({'use_emulator_provider': enabled})

        if hasattr(self, '_pending_settings_modal') and self._pending_settings_modal:
            try:
                self._pending_settings_modal.revert_provider_toggle(enabled)
            except Exception:
                pass

        if screen:
            msg = "Scanning external ROMs..." if enabled else "Scanning internal ROMs..."
            self._draw_loading_screen(screen, msg, 0, 2)

        _rom_scan_cache.clear()
        _save_scan_cache.clear()
        if hasattr(self, '_sinew_game_data_cache'):
            self._sinew_game_data_cache.clear()

        if screen:
            self._draw_loading_screen(screen, "Loading save data...", 1, 2)

        self._init_games()
        self.current_game = 0
        self.menu_index = 0

        if not self.is_on_sinew() and self.game_names:
            gname = self.game_names[self.current_game]
            sav_path = self.games[gname].get('sav')
            if sav_path and os.path.exists(sav_path):
                manager = get_manager()
                manager.load_save(sav_path, game_hint=gname)

        self.load_game_and_background()
        toggled = 'ON (external)' if enabled else 'OFF (internal)'
        print(f"[GameScreen] External Files toggled {toggled} -- emulator binary unchanged")

    def _on_emulator_provider_toggled(self, enabled):
        """Rebuild the game list when the user toggles the emulator provider setting.

        Shows a ProviderSwitchDialog before committing, and a ProviderErrorDialog
        if no external provider could be found (reverting the toggle automatically).

        Also handles two edge cases:
          - External ON but provider resolves to IntegratedMgba + no external paths
            → treat as toggle OFF, show "using integrated" notice
          - External ON but provider resolves to IntegratedMgba + external paths exist
            → treat as toggle ON with those paths
        """
        from game_dialogs import ProviderSwitchDialog, ProviderErrorDialog
        from config import ROMS_DIR, SAVES_DIR

        # Small centred popup — not full screen
        _pw, _ph = 400, 240

        try:
            screen = pygame.display.get_surface()
        except Exception:
            screen = self._loading_screen

        # Capture current provider info BEFORE building the new manager —
        # once we reinitialise with external off, the provider info is gone.
        current_info = (self.emulator_manager.get_provider_info()
                        if self.emulator_manager else None)

        # ----------------------------------------------------------------
        # Step 1 — build / reinitialise the EmulatorManager with the new flag
        # ----------------------------------------------------------------
        try:
            from emulator_manager import EmulatorManager
            new_manager = EmulatorManager(use_external_providers=enabled)
        except ImportError:
            new_manager = None

        # ----------------------------------------------------------------
        # Step 2 — analyse what we got and resolve edge cases
        # ----------------------------------------------------------------
        def _revert_ui(to_external):
            """Flip the settings UI toggle back without triggering the callback."""
            if self.modal_instance and hasattr(self.modal_instance, 'revert_provider_toggle'):
                self.modal_instance.revert_provider_toggle(to_external)

        if enabled:
            # --- Turning ON ---
            if new_manager and new_manager.active_provider:
                info = new_manager.get_provider_info()
                provider_name = info["name"]
                is_integrated = not info["is_external"]
                roms  = info["roms_dir"] or ROMS_DIR
                saves = info["saves_dir"] or SAVES_DIR
                has_external_paths = (
                    info["roms_dir"] and
                    info["roms_dir"] != ROMS_DIR and
                    os.path.exists(info["roms_dir"])
                )

                if is_integrated and not has_external_paths:
                    # Edge case A: no real external provider AND no external paths
                    # → silently treat as toggle OFF
                    dialog_title = "Using Integrated mGBA"
                    lines = [
                        "No external provider or paths found.",
                        "",
                        "Staying on Sinew integrated mGBA.",
                        f"ROM paths:  {ROMS_DIR}",
                        f"Save paths: {SAVES_DIR}",
                    ]
                    def _revert_to_integrated_a():
                        _revert_ui(False)
                        self._commit_provider_toggle(False, new_manager, screen)
                    dialog = ProviderSwitchDialog(_pw, _ph, screen_size=(self.width, self.height),
                        title=dialog_title, lines=lines,
                        on_accept=_revert_to_integrated_a,
                    )

                elif is_integrated and has_external_paths:
                    # Edge case B: integrated provider but external paths exist
                    # → treat as toggle ON (external paths, internal emulator)
                    # Override the provider paths to the external dirs
                    if hasattr(new_manager.active_provider, 'roms_dir'):
                        new_manager.active_provider.roms_dir = info["roms_dir"]
                    dialog_title = "Using External Paths"
                    lines = [
                        "Emulator:   Sinew integrated mGBA",
                        f"ROM paths:  {info['roms_dir']}",
                        f"Save paths: {saves}",
                    ]
                    dialog = ProviderSwitchDialog(_pw, _ph, screen_size=(self.width, self.height),
                        title=dialog_title, lines=lines,
                        on_accept=lambda: self._commit_provider_toggle(
                            True, new_manager, screen),
                    )

                elif not has_external_paths and not is_integrated:
                    # External provider found but its paths don't exist yet
                    # → switch provider but fall back to Sinew paths
                    if hasattr(new_manager.active_provider, 'roms_dir'):
                        new_manager.active_provider.roms_dir = ROMS_DIR
                    if hasattr(new_manager.active_provider, 'saves_dir'):
                        new_manager.active_provider.saves_dir = SAVES_DIR
                    dialog_title = "External Paths Not Found"
                    lines = [
                        f"Emulator:  {provider_name}",
                        f"Expected:  {info['roms_dir']}",
                        "",
                        "Paths not found — using Sinew paths.",
                        f"ROM paths:  {ROMS_DIR}",
                    ]
                    dialog = ProviderErrorDialog(_pw, _ph, screen_size=(self.width, self.height),
                        title=dialog_title, lines=lines,
                        on_accept=lambda: self._commit_provider_toggle(
                            True, new_manager, screen),
                    )

                else:
                    # Normal external provider with valid paths
                    dialog_title = "Switching to External Emulator"
                    lines = [
                        f"Emulator:  {provider_name}",
                        f"ROM paths:  {roms}",
                        f"Save paths: {saves}",
                    ]
                    dialog = ProviderSwitchDialog(_pw, _ph, screen_size=(self.width, self.height),
                        title=dialog_title, lines=lines,
                        on_accept=lambda: self._commit_provider_toggle(
                            True, new_manager, screen),
                    )

            else:
                # No provider at all — revert
                def _revert_no_provider():
                    _revert_ui(False)
                    import builtins
                    from settings import save_sinew_settings_merged as _ssm
                    self.settings['use_emulator_provider'] = False
                    builtins.SINEW_USE_EMULATOR_PROVIDER = False
                    _ssm({'use_emulator_provider': False})
                    try:
                        from emulator_manager import EmulatorManager as _EM
                        self.emulator_manager = _EM(use_external_providers=False)
                    except Exception:
                        pass
                    self.modal_instance = None

                dialog = ProviderErrorDialog(_pw, _ph, screen_size=(self.width, self.height),
                    title="No External Provider Found",
                    lines=[
                        "No compatible external emulator",
                        "was detected on this system.",
                        "",
                        "Reverting to Sinew integrated mGBA.",
                    ],
                    on_accept=_revert_no_provider,
                )

        else:
            # --- Turning OFF (switching back to integrated mGBA) ---
            had_external_paths = bool(
                current_info and
                current_info.get("roms_dir") and
                current_info["roms_dir"] != ROMS_DIR
            )

            if had_external_paths:
                path_label = "integrated (Sinew) files"
            else:
                path_label = "integrated (Sinew) files"

            lines = [
                "Switching to Sinew integrated mGBA.",
                f"Using: {path_label}",
                "",
                f"ROM paths:  {ROMS_DIR}",
                f"Save paths: {SAVES_DIR}",
            ]
            dialog = ProviderSwitchDialog(_pw, _ph, screen_size=(self.width, self.height),
                title="Switching to Integrated mGBA",
                lines=lines,
                on_accept=lambda: self._commit_provider_toggle(
                    False, new_manager, screen),
            )

        # ----------------------------------------------------------------
        # Step 3 — show the dialog as a modal overlay, keeping a ref to
        # the Settings modal so we can sync its toggles after accept
        # ----------------------------------------------------------------
        if hasattr(self.modal_instance, 'revert_provider_toggle'):
            self._pending_settings_modal = self.modal_instance
        else:
            self._pending_settings_modal = None
        self.modal_instance = dialog

    def _commit_provider_toggle(self, enabled, new_manager, screen):
        """
        Called after the user accepts a provider switch dialog.
        Applies the new manager, rescans games, reloads save data,
        and tells the settings modal to reflect the final state.
        """
        import builtins
        from config import ROMS_DIR, SAVES_DIR
        from settings import save_sinew_settings_merged as _ssm

        self.modal_instance = None

        # Apply the new manager
        self.emulator_manager = new_manager

        builtins.SINEW_USE_EMULATOR_PROVIDER = enabled
        self.settings['use_emulator_provider'] = enabled
        self.settings['use_external_emulator'] = enabled
        _ssm({'use_emulator_provider': enabled, 'use_external_emulator': enabled})

        if hasattr(self, '_pending_settings_modal') and self._pending_settings_modal:
            try:
                self._pending_settings_modal.revert_provider_toggle(enabled)
                self._pending_settings_modal.revert_emulator_toggle(enabled)
            except Exception:
                pass

        if screen:
            message = "Scanning external ROMs..." if enabled else "Scanning internal ROMs..."
            self._draw_loading_screen(screen, message, 0, 3)

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

        self.current_game = 0
        self.menu_index = 0

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
                        print(f"[EmulatorManager] Backed up {bname} -> "
                              f"{os.path.basename(backup_path)}")
                    except Exception as e:
                        print(f"[EmulatorManager] Backup failed for {gname}: {e}")

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

        self.load_game_and_background()

        toggled = 'ON' if enabled else 'OFF'
        print(f"[GameScreen] Emulator provider toggled {toggled}, games reloaded")

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