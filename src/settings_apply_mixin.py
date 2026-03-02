#!/usr/bin/env python3

"""
settings_apply_mixin.py — settings application helpers for GameScreen.

Handles applying fullscreen, A/B swap, and
reloading all settings from disk when returning from emulator.
"""

import builtins

from settings import load_sinew_settings as load_settings
from settings import save_sinew_settings_merged as save_settings_file


class SettingsApplyMixin:
    """Mixin providing settings-apply helpers to GameScreen."""

    def _set_fullscreen(self, enabled):
        """Set fullscreen mode and save to settings"""
        self.settings["fullscreen"] = enabled
        save_settings_file(self.settings)

        if self.scaler:
            self.scaler.set_fullscreen(enabled)
            print(f"[Sinew] Fullscreen {'enabled' if enabled else 'disabled'}")

    def _set_swap_ab(self, enabled):
        """Set A/B button swap and save to settings"""
        self.settings["swap_ab"] = enabled
        save_settings_file(self.settings)

        # Update controller mapping
        if self.controller:
            self.controller.set_swap_ab(enabled)

        # Update emulator mapping if active (both gamepad and keyboard maps)
        if self.emulator:
            try:
                # Libretro joypad constants (stable; no import needed)
                RETRO_DEVICE_ID_JOYPAD_A = 8
                RETRO_DEVICE_ID_JOYPAD_B = 0

                # --- Gamepad button map ---
                gmap = getattr(self.emulator, "_gamepad_map", None)
                if gmap is not None:
                    if not hasattr(self.emulator, "_original_a_btn"):
                        self.emulator._original_a_btn = gmap.get(
                            RETRO_DEVICE_ID_JOYPAD_A, 0
                        )
                        self.emulator._original_b_btn = gmap.get(
                            RETRO_DEVICE_ID_JOYPAD_B, 1
                        )
                    if enabled:
                        gmap[RETRO_DEVICE_ID_JOYPAD_A] = self.emulator._original_b_btn
                        gmap[RETRO_DEVICE_ID_JOYPAD_B] = self.emulator._original_a_btn
                    else:
                        gmap[RETRO_DEVICE_ID_JOYPAD_A] = self.emulator._original_a_btn
                        gmap[RETRO_DEVICE_ID_JOYPAD_B] = self.emulator._original_b_btn
                    print(
                        f"[Sinew] Emulator gamepad A/B:"
                        f" A→btn{gmap[RETRO_DEVICE_ID_JOYPAD_A]},"
                        f" B→btn{gmap[RETRO_DEVICE_ID_JOYPAD_B]}"
                    )

                # --- Keyboard map ---
                kb_map = getattr(self.emulator, "_kb_map", None)
                if kb_map is not None:
                    if not hasattr(self.emulator, "_original_a_keys"):
                        self.emulator._original_a_keys = kb_map.get(
                            RETRO_DEVICE_ID_JOYPAD_A, []
                        )
                        self.emulator._original_b_keys = kb_map.get(
                            RETRO_DEVICE_ID_JOYPAD_B, []
                        )
                    if enabled:
                        kb_map[RETRO_DEVICE_ID_JOYPAD_A] = (
                            self.emulator._original_b_keys
                        )
                        kb_map[RETRO_DEVICE_ID_JOYPAD_B] = (
                            self.emulator._original_a_keys
                        )
                    else:
                        kb_map[RETRO_DEVICE_ID_JOYPAD_A] = (
                            self.emulator._original_a_keys
                        )
                        kb_map[RETRO_DEVICE_ID_JOYPAD_B] = (
                            self.emulator._original_b_keys
                        )
                    print(
                        f"[Sinew] Emulator kb A/B:"
                        f" A→{kb_map.get(RETRO_DEVICE_ID_JOYPAD_A)},"
                        f" B→{kb_map.get(RETRO_DEVICE_ID_JOYPAD_B)}"
                    )

            except Exception as e:
                print(f"[Sinew] Could not update emulator A/B swap: {e}")

        print(f"[Sinew] A/B swap {'enabled' if enabled else 'disabled'}")

    def _reload_settings_from_disk(self):
        """
        Reload all settings from disk and reapply them.
        Called when returning from emulator to ensure settings changes
        made in Settings modal are applied.
        """
        try:
            # Reload settings from file
            self.settings = load_settings()
            print("[Sinew] Reloaded settings from disk")

            # Reapply settings that affect current state
            self._menu_music_muted = self.settings.get("mute_menu_music", False)

            use_external = self.settings.get("use_emulator_provider", False)
            if hasattr(builtins, "SINEW_USE_EMULATOR_PROVIDER"):
                builtins.SINEW_USE_EMULATOR_PROVIDER = use_external

            dev_mode = self.settings.get("dev_mode", False)
            if hasattr(builtins, "SINEW_DEV_MODE"):
                builtins.SINEW_DEV_MODE = dev_mode

            swap_ab = self.settings.get("swap_ab", False)

            if self.controller and hasattr(self.controller, "set_swap_ab"):
                self.controller.set_swap_ab(swap_ab)

            # Also update emulator mapping if emulator is loaded
            if self.emulator:
                try:
                    # Libretro joypad constants (stable; no import needed)
                    RETRO_DEVICE_ID_JOYPAD_A = 8
                    RETRO_DEVICE_ID_JOYPAD_B = 0

                    gmap = getattr(self.emulator, "_gamepad_map", None)
                    if gmap is not None:
                        # Apply swap based on setting - use absolute values
                        if swap_ab:
                            gmap[RETRO_DEVICE_ID_JOYPAD_A] = 1  # B button
                            gmap[RETRO_DEVICE_ID_JOYPAD_B] = 0  # A button
                        else:
                            gmap[RETRO_DEVICE_ID_JOYPAD_A] = 0  # A button
                            gmap[RETRO_DEVICE_ID_JOYPAD_B] = 1  # B button
                except Exception:
                    pass

            print(
                f"[Sinew] Applied settings:"
                f" music_muted={self._menu_music_muted},"
                f" emulator_provider={use_external}, swap_ab={swap_ab}"
            )

        except Exception as e:
            print(f"[Sinew] Error reloading settings: {e}")
            import traceback

            traceback.print_exc()
