#!/usr/bin/env python3

"""
pause_combo.py - Pause combo mixin for GameScreen

Handles the mGBA ↔ Sinew pause combo feature:
  - While mGBA is RUNNING:  _check_emulator_pause_combo() detects the combo
    that triggers a pause-to-Sinew transition (delegates to emulator's own
    hold-timer logic via emulator.check_pause_combo()).
  - While mGBA is PAUSED (user is in the Sinew menu):
    _check_pause_combo_direct() / _is_controller_combo_held() poll pygame
    input directly (the emulator is idle) to detect the combo that resumes
    the game back into mGBA.
  - Helper methods for loading / reloading the combo setting from
    sinew_settings.json and formatting display strings for the UI.

These methods are collected here because they form a single cohesive feature
and none of them belong in mgba_emulator.py (which has its own parallel
implementation operating on emulator-internal joystick state).
"""

import pygame

from settings import load_sinew_settings as load_settings


class PauseComboMixin:
    """
    Mixin providing pause-combo handling for GameScreen.

    Expects the host class to have:
        self.emulator          - MgbaEmulator instance (or None)
        self.controller        - controller object with kb_nav_map / button_map
        self._pause_combo_setting - dict loaded by _load_pause_combo_setting()
    """

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------

    def _load_pause_combo_setting(self):
        """Load pause combo setting from sinew_settings.json."""
        self._pause_combo_setting = {"type": "combo", "buttons": ["START", "SELECT"]}
        try:
            settings = load_settings()
            if "pause_combo" in settings:
                self._pause_combo_setting = settings["pause_combo"]
                print(
                    f"[Sinew] Pause combo: {self._pause_combo_setting.get('name', 'START+SELECT')}"
                )
        except Exception as e:
            print(f"[Sinew] Could not load pause combo setting: {e}")

    def _reload_pause_combo_setting(self):
        """Reload pause combo setting (called when the user changes it in Settings)."""
        self._load_pause_combo_setting()

        # Also propagate to the emulator so its own check_pause_combo() stays in sync
        if self.emulator and hasattr(self.emulator, "_load_pause_combo_setting"):
            self.emulator._pause_combo_setting = (
                self.emulator._load_pause_combo_setting()
            )
            print("[Sinew] Reloaded pause combo in emulator")

    # ------------------------------------------------------------------
    # While mGBA is RUNNING — delegate to the emulator's hold-timer logic
    # ------------------------------------------------------------------

    def _check_emulator_pause_combo(self):
        """
        Check if the pause combo is triggered while mGBA is actively running.

        Delegates to MgbaEmulator.check_pause_combo(), which handles both
        the controller combo and the keyboard MENU key, including the ~0.5 s
        hold timer.

        Returns:
            bool: True if the combo fired
        """
        if self.emulator:
            return self.emulator.check_pause_combo()
        return False

    # ------------------------------------------------------------------
    # While mGBA is PAUSED — poll pygame directly (emulator is idle)
    # ------------------------------------------------------------------

    def _check_pause_combo_direct(self):
        """
        Check the pause combo while mGBA is paused and the user is in the
        Sinew menu.  Because the emulator is idle its check_pause_combo()
        cannot be used, so we poll pygame input directly.

        No hold timer — triggers immediately; debounce is handled by the
        caller.

        Returns:
            bool: True if the combo / key is currently pressed
        """
        setting = getattr(
            self,
            "_pause_combo_setting",
            {"type": "combo", "buttons": ["START", "SELECT"]},
        )
        combo_held = False

        # Check keyboard MENU key first
        keys = pygame.key.get_pressed()
        if self.controller and hasattr(self.controller, "kb_nav_map"):
            try:
                menu_keys = self.controller.kb_nav_map.get("MENU", [pygame.K_m])
                for menu_key in menu_keys:
                    if keys[menu_key]:
                        combo_held = True
                        print(
                            f"[Sinew] MENU key {pygame.key.name(menu_key)} "
                            f"detected in _check_pause_combo_direct"
                        )
                        break
            except Exception as e:
                print(f"[Sinew] Error checking MENU key: {e}")

        # If MENU not held, check controller combo
        if not combo_held:
            if setting.get("type") == "custom":
                # Custom single button
                custom_btn = setting.get("button")
                if custom_btn is not None:
                    try:
                        if pygame.joystick.get_count() > 0:
                            joy = pygame.joystick.Joystick(0)
                            joy.init()
                            if custom_btn < joy.get_numbuttons():
                                combo_held = joy.get_button(custom_btn)
                    except Exception:
                        pass
            else:
                # Button combo
                required_buttons = setting.get("buttons", ["START", "SELECT"])
                buttons_held = {}

                # Check keyboard (START / SELECT mappings)
                if "START" in required_buttons:
                    buttons_held["START"] = keys[pygame.K_RETURN]
                if "SELECT" in required_buttons:
                    buttons_held["SELECT"] = keys[pygame.K_BACKSPACE]

                # Check controller
                try:
                    if pygame.joystick.get_count() > 0:
                        joy = pygame.joystick.Joystick(0)
                        joy.init()
                        num_buttons = joy.get_numbuttons()

                        for btn_name in required_buttons:
                            btn_indices = (
                                [7]
                                if btn_name == "START"
                                else [6] if btn_name == "SELECT" else []
                            )

                            if self.controller and hasattr(self.controller, "button_map"):
                                btn_indices = self.controller.button_map.get(
                                    btn_name, btn_indices
                                )

                            for idx in btn_indices:
                                if isinstance(idx, int) and idx < num_buttons:
                                    if joy.get_button(idx):
                                        buttons_held[btn_name] = True
                except Exception:
                    pass

                combo_held = all(
                    buttons_held.get(btn, False) for btn in required_buttons
                )

        return combo_held

    def _is_controller_combo_held(self):
        """
        Check if the pause combo is currently held on the controller only
        (no keyboard check).  Used while mGBA is paused to decide when to
        reset the release-flag debounce.

        Returns:
            bool: True if the controller combo is held
        """
        setting = getattr(
            self,
            "_pause_combo_setting",
            {"type": "combo", "buttons": ["START", "SELECT"]},
        )

        try:
            if pygame.joystick.get_count() > 0:
                joy = pygame.joystick.Joystick(0)
                joy.init()
                num_buttons = joy.get_numbuttons()

                if setting.get("type") == "custom":
                    custom_btn = setting.get("button")
                    if custom_btn is not None and custom_btn < num_buttons:
                        return joy.get_button(custom_btn)
                else:
                    required_buttons = setting.get("buttons", ["START", "SELECT"])
                    buttons_held = {}

                    for btn_name in required_buttons:
                        btn_indices = (
                            [7]
                            if btn_name == "START"
                            else [6] if btn_name == "SELECT" else []
                        )

                        if self.controller and hasattr(self.controller, "button_map"):
                            btn_indices = self.controller.button_map.get(
                                btn_name, btn_indices
                            )

                        for idx in btn_indices:
                            if isinstance(idx, int) and idx < num_buttons:
                                if joy.get_button(idx):
                                    buttons_held[btn_name] = True
                                    break

                    return all(
                        buttons_held.get(btn, False) for btn in required_buttons
                    )
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _get_pause_combo_name(self):
        """Get the display name of the current pause combo (e.g. 'START+SELECT')."""
        setting = self._pause_combo_setting
        if setting.get("type") == "custom":
            return f"Button {setting.get('button', '?')}"
        buttons = setting.get("buttons", ["START", "SELECT"])
        return "+".join(buttons)

    def _get_pause_combo_hint_text(self, action="resume"):
        """Return a UI hint string such as 'Hold START+SELECT to resume'."""
        return f"Hold {self._get_pause_combo_name()} to {action}"
