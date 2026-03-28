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
    
    Save file format sync (CRITICAL for RetroArch-based emulators)
    ---------------------------------------------------------------
    PKsinew uses .sav files, but RetroArch cores use .srm files.
    
    YOU MUST implement this two-way sync in your provider:
    
    1. In get_command(): Create .sav → .srm (symlink or copy)
    2. In on_exit(): Copy .srm → .sav (if not a symlink)
    
    See the example code in get_command() and on_exit() below.
    Failure to implement this will cause saves to NOT persist!
    """

    active = False

    # List the OS/firmware distro IDs this provider exclusively targets.
    # These are matched against the 'ID=' field in /etc/os-release (lowercased).
    #
    # Examples:
    #   claimed_distros = {"rocknix", "jelos"}   # ROCKNIX / former JELOS firmware
    #   claimed_distros = {"raspbian"}            # Raspberry Pi OS (RetroPie)
    #   claimed_distros = {"muos"}                # muOS handheld firmware
    #   claimed_distros = set()                   # Generic fallback — always scanned
    #
    # When claimed_distros is non-empty and the current distro_id matches,
    # EmulatorManager fast-paths directly to this provider and skips all others.
    # probe() is still called as a sanity check (e.g. required binaries present).
    # Leave as set() if this provider should work on any distro via probe() scan
    # (e.g. a generic desktop provider).
    claimed_distros: set = set()

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
        
        # Track save paths for sync-back after emulator exits
        # (Required for RetroArch-based emulators that use .srm instead of .sav)
        self._last_sav_path = None
        self._last_srm_path = None

    def probe(self, distro_id) -> bool:
        """
        Sanity check — called after a claimed_distros fast-path match, or during
        the full provider scan if claimed_distros is empty.

        Return True only if this provider is genuinely usable on the current system.
        Typically checks for required binaries, directories, or config files.

        distro_id: lowercased 'ID=' value from /etc/os-release, or None on non-Linux.
        """
        # Example: verify the firmware launcher binary actually exists
        # if distro_id in self.claimed_distros:
        #     return os.path.exists("/path/to/launcher")
        return False

    def get_command(self, rom_path, core="auto", sav_path=None):
        """
        Return the list of strings representing the shell command
        to launch the emulator.
        
        Args:
            rom_path: Absolute path to the ROM file
            core: Core selection (often auto-detected or ignored)
            sav_path: Optional absolute path to PKsinew's .sav file
        
        Returns:
            list: Command to launch the emulator, or None if unable
        """
        
        # IMPORTANT: RetroArch-based emulators use .srm instead of .sav
        # If your emulator uses RetroArch, you MUST create a .srm symlink/copy:
        #
        # if sav_path and sav_path.endswith('.sav'):
        #     rom_base = os.path.splitext(os.path.basename(rom_path))[0]
        #     srm_path = os.path.join(os.path.dirname(sav_path), f"{rom_base}.srm")
        #     
        #     # Track paths for sync-back on exit
        #     self._last_sav_path = sav_path
        #     self._last_srm_path = srm_path
        #     
        #     try:
        #         # Remove old file/symlink if it exists
        #         if os.path.islink(srm_path):
        #             os.remove(srm_path)
        #         elif os.path.exists(srm_path):
        #             backup_path = f"{srm_path}.backup"
        #             os.rename(srm_path, backup_path)
        #         
        #         # Try symlink first (preferred - auto-syncs)
        #         try:
        #             os.symlink(sav_path, srm_path)
        #         except (OSError, PermissionError):
        #             # If symlink fails, copy the file instead
        #             import shutil
        #             shutil.copy2(sav_path, srm_path)
        #     except Exception as e:
        #         print(f"[TemplateProvider] Failed to create .srm: {e}")
        
        return None

    def _update_sinew_cache(self, key, value):
        """Helper to update persistent settings only when changed."""
        if self.cache.get(key) != value:
            self.cache[key] = value
            save_sinew_settings(self.settings)

    def on_exit(self):
        """
        Called after the emulator exits, either naturally or via terminate().
        
        IMPORTANT: If using RetroArch, sync .srm back to .sav here!
        This ensures saves made in the emulator persist in PKsinew.
        """
        # Sync save file back (for RetroArch-based emulators)
        if self._last_sav_path and self._last_srm_path:
            try:
                if os.path.exists(self._last_srm_path):
                    # If it's a symlink, the .sav is already updated
                    if os.path.islink(self._last_srm_path):
                        print(f"[TemplateProvider] Save synced via symlink")
                    else:
                        # Copy .srm back to .sav
                        import shutil
                        shutil.copy2(self._last_srm_path, self._last_sav_path)
                        print(f"[TemplateProvider] ✓ Synced .srm → .sav")
            except Exception as e:
                print(f"[TemplateProvider] Failed to sync save: {e}")
            finally:
                # Clear tracked paths
                self._last_sav_path = None
                self._last_srm_path = None
        
        # Additional cleanup (e.g., restart input handlers like gptokeyb)
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