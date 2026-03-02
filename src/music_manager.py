#!/usr/bin/env python3

"""
music_manager.py - Menu music mixin for GameScreen

Manages the Sinew menu music lifecycle:
  - _init_menu_music   : locate the audio file and set initial state
  - _start_menu_music  : (re)initialise pygame.mixer and begin looping playback
  - _stop_menu_music   : halt playback and free the audio resource
  - _set_menu_music_muted : toggle mute, persist to settings, start/stop accordingly

Menu music plays while the user is in the Sinew menu and is stopped before
handing control back to the mGBA emulator so the emulator's own audio system
gets a clean mixer.
"""

import os

import pygame

from config import DATA_DIR, VOLUME_DEFAULT
from settings import load_sinew_settings, save_sinew_settings_merged as save_settings_file


class MusicManagerMixin:
    """
    Mixin providing menu music management for GameScreen.

    Expected instance attributes (set in GameScreen.__init__):
        self.settings        - dict loaded from sinew_settings.json
        self.emulator_active - bool, True while mGBA is running
        self._menu_music_path    - str | None  (set by _init_menu_music)
        self._menu_music_playing - bool        (set by _init_menu_music)
        self._menu_music_muted   - bool        (set by _init_menu_music)
    """

    def _init_menu_music(self):
        """Locate the menu music file and initialise playback state."""
        self._menu_music_path = os.path.join(DATA_DIR, "sounds", "SinewMenu.mp3")
        self._menu_music_playing = False
        self._menu_music_muted = self.settings.get("mute_menu_music", False)

        if not os.path.exists(self._menu_music_path):
            print(f"[Sinew] Menu music not found: {self._menu_music_path}")
            self._menu_music_path = None

    def _start_menu_music(self):
        """Start looping menu music (no-op if muted, missing, or already playing)."""
        if self._menu_music_path is None or self._menu_music_muted or self._menu_music_playing:
            return

        try:
            # Always reinitialise the mixer to Sinew's known-good settings.
            # The emulator may have left the mixer configured with the user's
            # custom buffer size.  A full quit/init cycle guarantees a clean
            # slate for menu music playback.
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
                    pygame.time.wait(50)
            except Exception:
                pass

            pygame.mixer.pre_init(frequency=32768, size=-16, channels=2, buffer=1024)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
            print(f"[Sinew] Mixer initialized for menu music: {pygame.mixer.get_init()}")

            pygame.mixer.music.load(self._menu_music_path)

            # Apply saved master volume (default 80 %)
            try:
                _vol = load_sinew_settings().get("master_volume", VOLUME_DEFAULT)
                pygame.mixer.music.set_volume(max(0.0, min(1.0, _vol / 100.0)))
            except Exception:
                pygame.mixer.music.set_volume(0.8)

            pygame.mixer.music.play(-1)  # loop indefinitely
            self._menu_music_playing = True
            print("[Sinew] Menu music started")
        except Exception as e:
            print(f"[Sinew] Could not start menu music: {e}")

    def _stop_menu_music(self):
        """Stop menu music and free the audio resource."""
        if not self._menu_music_playing:
            return

        try:
            pygame.mixer.music.stop()
            if hasattr(pygame.mixer.music, "unload"):
                pygame.mixer.music.unload()
            self._menu_music_playing = False
            # Brief delay to let the audio system settle before game audio takes over
            pygame.time.wait(30)
            print("[Sinew] Menu music stopped")
        except Exception as e:
            print(f"[Sinew] Could not stop menu music: {e}")

    def _set_menu_music_muted(self, muted):
        """Toggle mute state, persist to settings, and start/stop playback."""
        self._menu_music_muted = muted
        self.settings["mute_menu_music"] = muted
        save_settings_file(self.settings)

        if muted:
            self._stop_menu_music()
        else:
            # Only start if we're not currently inside the emulator
            if not self.emulator_active:
                self._start_menu_music()
