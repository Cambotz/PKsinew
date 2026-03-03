#!/usr/bin/env python3

"""RetroPie provider for PKsinew."""

import os
import platform
from emulator_manager import EmulatorProvider
from settings import save_sinew_settings


class RetroPieProvider(EmulatorProvider):
    """
    External emulator provider for RetroPie on Raspberry Pi.
    
    RetroPie uses RetroArch for most emulation with a custom launch system.
    This provider detects RetroPie installations and launches games through
    the runcommand.sh wrapper script.
    
    ROM and save file handling
    --------------------------
    The provider sets self.roms_dir and self.saves_dir to point at RetroPie's
    standard directory structure. The application reads these attributes and
    handles all ROM/save detection and pairing internally.
    """

    active = True

    @property
    def supported_os(self):
        """RetroPie runs on Linux (Raspberry Pi OS)."""
        return ["linux"]

    def __init__(self, sinew_settings):
        self.settings = sinew_settings

        # Only set paths on Linux to avoid errors on other platforms
        if platform.system().lower() != "linux":
            self.roms_dir = None
            self.saves_dir = None
            if "emulator_cache" not in self.settings:
                self.settings["emulator_cache"] = {}
            self.cache = self.settings["emulator_cache"]
            return

        # RetroPie standard paths
        # Check multiple possible locations
        possible_paths = [
            os.path.expanduser("~/RetroPie"),  # Current user's home
            "/home/pi/RetroPie",                # Default pi user
            "/root/RetroPie"                    # Root user
        ]
        
        self.retropie_path = None
        for path in possible_paths:
            if os.path.exists(path):
                self.retropie_path = path
                print(f"[RetroPieProvider] Found RetroPie at: {path}")
                break
        
        if not self.retropie_path:
            self.retropie_path = os.path.expanduser("~/RetroPie")  # Fallback
        
        self.roms_base = os.path.join(self.retropie_path, "roms")
        self.configs_base = os.path.expanduser("/opt/retropie/configs")
        
        # GBA-specific paths
        self.roms_dir = os.path.join(self.roms_base, "gba")
        
        # Check RetroArch config for save directory settings
        self.retroarch_cfg = os.path.join(self.configs_base, "gba", "retroarch.cfg")
        self.retroarch_global_cfg = os.path.join(self.configs_base, "all", "retroarch.cfg")
        
        # Determine saves directory from RetroArch configuration
        self.saves_dir = self._resolve_saves_directory()
        
        print(f"[RetroPieProvider] ROMs dir: {self.roms_dir}")
        print(f"[RetroPieProvider] Saves dir: {self.saves_dir}")

        # Initialize internal cache reference
        if "emulator_cache" not in self.settings:
            self.settings["emulator_cache"] = {}
        self.cache = self.settings["emulator_cache"]
        print(f"[RetroPieProvider] Cache loaded: {self.cache}")

    def probe(self, distro_id):
        """
        Return True if RetroPie is installed and configured for GBA.
        
        Checks for:
        - RetroPie directory structure
        - runcommand.sh launch script
        - GBA ROMs directory (must already exist)
        """
        # Check for RetroPie-specific paths
        retropie_exists = os.path.exists(self.retropie_path)
        runcommand_exists = os.path.exists("/opt/retropie/supplementary/runcommand/runcommand.sh")
        gba_dir_exists = os.path.exists(self.roms_dir)
        
        print(
            f"[RetroPieProvider] Probe - RetroPie: {retropie_exists}, "
            f"runcommand: {runcommand_exists}, GBA dir: {gba_dir_exists}"
        )
        
        # All three conditions must be met
        return retropie_exists and runcommand_exists and gba_dir_exists

    def _get_retroarch_setting(self, setting_key, config_path=None):
        """
        Read a setting from a RetroArch config file.
        
        Args:
            setting_key: The config key to read (e.g., 'savefile_directory')
            config_path: Path to config file (uses defaults if None)
        
        Returns:
            str: The setting value, or None if not found
        """
        # Try GBA-specific config first, then fall back to global
        configs_to_check = [self.retroarch_cfg, self.retroarch_global_cfg]
        if config_path:
            configs_to_check.insert(0, config_path)
        
        for cfg_path in configs_to_check:
            if not os.path.exists(cfg_path):
                continue
                
            try:
                with open(cfg_path, 'r') as f:
                    for line in f:
                        clean_line = line.strip()
                        # Skip comments and empty lines
                        if not clean_line or clean_line.startswith('#'):
                            continue
                        
                        if clean_line.startswith(setting_key):
                            parts = clean_line.split('=', 1)
                            if len(parts) > 1:
                                value = parts[1].strip().strip('"').strip("'")
                                print(f"[RetroPieProvider] Found {setting_key} = {value} in {cfg_path}")
                                return value
            except Exception as e:
                print(f"[RetroPieProvider] Error reading {cfg_path}: {e}")
        
        return None

    def _resolve_saves_directory(self):
        """
        Determine where save files are stored based on RetroArch configuration.
        
        RetroPie can store saves in several locations:
        - Same directory as ROMs (savefiles_in_content_dir = true)
        - Custom directory (savefile_directory setting)
        - Per-system subdirectories (sort_savefiles_by_content_enable = true)
        
        Returns:
            str: Absolute path to saves directory
        """
        # Check if saves are in the same directory as ROMs
        in_content_dir = self._get_retroarch_setting("savefiles_in_content_dir")
        if in_content_dir == "true":
            print("[RetroPieProvider] Saves stored with ROMs")
            return self.roms_dir
        
        # Get the base save directory
        base_save_dir = self._get_retroarch_setting("savefile_directory")
        
        # Handle default or empty values
        if not base_save_dir or base_save_dir.lower() == "default":
            print("[RetroPieProvider] Using default save location (with ROMs)")
            return self.roms_dir
        
        # Expand home tilde if present
        base_save_dir = os.path.expanduser(base_save_dir)
        
        # Check for per-system subdirectories
        sort_by_content = self._get_retroarch_setting("sort_savefiles_by_content_enable")
        if sort_by_content == "true":
            gba_saves = os.path.join(base_save_dir, "gba")
            print(f"[RetroPieProvider] Using per-system saves directory: {gba_saves}")
            return gba_saves
        
        print(f"[RetroPieProvider] Using base saves directory: {base_save_dir}")
        return base_save_dir

    def get_command(self, rom_path, core="auto"):
        """
        Return the command to launch a game through RetroPie's runcommand system.
        
        RetroPie uses runcommand.sh to handle emulator selection and configuration.
        The command format is:
        /opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ gba "rom_path"
        
        Args:
            rom_path: Absolute path to the ROM file
            core: Core selection (not used - RetroPie handles core selection)
        
        Returns:
            list: Command to launch the emulator
        """
        return [
            "/opt/retropie/supplementary/runcommand/runcommand.sh",
            "0",      # Video mode: 0 = default
            "_SYS_",  # System name token (RetroPie resolves this)
            "gba",    # System identifier
            rom_path
        ]

    def _update_sinew_cache(self, key, value):
        """Helper to update persistent settings only when changed."""
        if self.cache.get(key) != value:
            self.cache[key] = value
            save_sinew_settings(self.settings)

    def on_exit(self):
        """
        Called after the emulator exits.
        
        RetroPie's runcommand handles input restoration, so this is a no-op.
        """
        pass

    def terminate(self, process):
        """
        Terminate the emulator process.
        
        Args:
            process: The subprocess.Popen object for the emulator
        """
        if process:
            try:
                process.terminate()
                process.wait(timeout=2)
            except Exception as e:
                print(f"[RetroPieProvider] Terminate error: {e}")
        self.on_exit()