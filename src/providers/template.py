#!/usr/bin/env python3

"""Template provider for creating new external emulator providers."""

import os
from emulator_manager import EmulatorProvider
from settings import save_sinew_settings

class TemplateProvider(EmulatorProvider):
    """
    Template for creating new External Emulator providers.
    Copy this file and rename the class and methods as needed.
    Set active = True when ready for use.

    ROM and save file handling
    --------------------------
    The provider does NOT need to scan, filter, or resolve ROM/save files.
    The application (game_nav_mixin.py) reads `provider.roms_dir` and
    `provider.saves_dir` via getattr() and passes them to `detect_games_with_dirs`,
    which handles all extension matching and pairing internally.

    Your only responsibility is to set `self.roms_dir` and `self.saves_dir`
    to the correct directories during __init__ or probe().
    """

    active = False

    @property
    def supported_os(self):
        # Return a list of platforms this provider works on
        # Options usually: ["linux", "windows", "darwin"]
        return ["linux"]

    def __init__(self, sinew_settings):
        self.settings = sinew_settings

        # The application reads these two attributes directly via getattr().
        # Point them at the directories where the emulator stores ROMs and saves.
        # The application will scan both directories itself — do not pre-filter
        # or resolve individual file paths here; just supply the directories.
        self.roms_dir = "/path/to/external/roms"
        self.saves_dir = "/path/to/external/saves"


        # Initialize internal cache reference
        if "emulator_cache" not in self.settings:
            self.settings["emulator_cache"] = {}
        self.cache = self.settings["emulator_cache"]

    def probe(self, distro_id) -> bool:
        """
        Logic to determine if this provider should be active.
        distro_id is passed from the main controller (e.g., 'rocknix').
        """
        # Example: check for a specific OS name and a required binary
        # if distro_id == "my_os_name":
        #     return os.path.exists("/path/to/launcher")
        return False

    def get_command(self, rom_path, core="auto"):
        """
        Return the list of strings representing the shell command
        to launch the emulator.
        """

        return None

    def _update_sinew_cache(self, key, value):
        """Helper to update persistent settings only when changed."""
        if self.cache.get(key) != value:
            self.cache[key] = value
            save_sinew_settings(self.settings)

    def on_exit(self):
        """
        Called after the emulator exits, either naturally or via terminate().
        Use this to restart any input handlers (e.g. gptokeyb).
        """

    def terminate(self, process):
        """
        Called when Sinew needs to forcefully close the emulator.
        Should kill the process and call self.on_exit().
        """
        if process:
            try:
                process.terminate()
                process.wait(timeout=2)
            except Exception as e:
                print(f"[TemplateProvider] Terminate error: {e}")
        self.on_exit()
