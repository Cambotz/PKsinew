#!/usr/bin/env python3

import os
from external_emulator import EmulatorProvider
from settings import save_sinew_settings

class TemplateProvider(EmulatorProvider):
    """
    Template for creating new External Emulator providers.
    Copy this file and rename the class and methods as needed.
    Set active = True when ready for use.
    """
    
    active = False

    @property
    def supported_os(self):
        # Return a list of platforms this provider works on
        # Options usually: ["linux", "windows", "darwin"]
        return ["linux"]

    def __init__(self, sinew_settings):
        self.settings = sinew_settings
        
        # These are read by main.py
        self.roms_dir = "/path/to/external/roms"
        self.saves_dir = "/path/to/external/saves"
        
        
        # Initialize internal cache reference
        if "emulator_cache" not in self.settings:
            self.settings["emulator_cache"] = {}
        self.cache = self.settings["emulator_cache"]

    def probe(self, distro_id):
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

    def get_save_path(self, rom_path):
        """
        Returns the absolute path to the expected save file.
        This is critical for the 'pull-back' logic after the game exits.
        """
        rom_name = os.path.splitext(os.path.basename(rom_path))[0]
        # Most external emulators use .srm or .sav
        return os.path.join(self.saves_dir, f"{rom_name}.srm")

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
        pass

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