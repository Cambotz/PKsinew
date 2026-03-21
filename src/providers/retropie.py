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
    This provider launches RetroArch directly with configuration overrides
    to ensure correct frame timing.
    
    ROM and save file handling
    --------------------------
    The provider sets self.roms_dir and self.saves_dir to point at RetroPie's
    standard directory structure. The application reads these attributes and
    handles all ROM/save detection and pairing internally.
    """

    active = True
    is_desktop_retropie = True  # Tells EmulatorManager to quit display for RetroArch
    is_script_launcher = True  # Skip emulator_session save path injection (we handle it internally)
    claimed_distros: set = set()  # Probe-based detection — RetroPie runs on 'debian' (Pi OS) or 'raspbian' (older)

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
        # Build list of possible RetroPie locations dynamically
        possible_paths = []
        
        # 1. Current user's home directory
        possible_paths.append(os.path.expanduser("~/RetroPie"))
        
        # 2. Scan /home for all user directories with RetroPie
        if os.path.exists("/home"):
            try:
                for user in os.listdir("/home"):
                    user_retropie = os.path.join("/home", user, "RetroPie")
                    if user_retropie not in possible_paths:
                        possible_paths.append(user_retropie)
            except (PermissionError, OSError):
                pass  # Can't read /home, skip scanning
        
        # 3. Root user (if not already added)
        root_retropie = "/root/RetroPie"
        if root_retropie not in possible_paths:
            possible_paths.append(root_retropie)
        
        self.retropie_path = None
        self.roms_dir = None
        
        # First pass: prioritize paths with GBA directory already set up
        for path in possible_paths:
            if os.path.exists(path):
                gba_path = os.path.join(path, "roms", "gba")
                if os.path.exists(gba_path):
                    self.retropie_path = path
                    self.roms_dir = gba_path
                    print(f"[RetroPieProvider] Found RetroPie with GBA at: {path}")
                    break
        
        # Second pass: if no GBA found, use first RetroPie directory
        if not self.retropie_path:
            for path in possible_paths:
                if os.path.exists(path):
                    self.retropie_path = path
                    self.roms_dir = os.path.join(path, "roms", "gba")
                    print(f"[RetroPieProvider] Found RetroPie at: {path} (no GBA dir yet)")
                    break
        
        # Fallback if nothing found
        if not self.retropie_path:
            self.retropie_path = os.path.expanduser("~/RetroPie")
            self.roms_dir = os.path.join(self.retropie_path, "roms", "gba")
        
        self.roms_base = os.path.join(self.retropie_path, "roms")
        self.configs_base = os.path.expanduser("/opt/retropie/configs")
        
        # Check RetroArch config for save directory settings
        self.retroarch_cfg = os.path.join(self.configs_base, "gba", "retroarch.cfg")
        self.retroarch_global_cfg = os.path.join(self.configs_base, "all", "retroarch.cfg")
        
        # runcommand.sh path (for reference)
        self.runcommand_path = "/opt/retropie/supplementary/runcommand/runcommand.sh"
        
        # Determine saves directory from RetroArch configuration
        self.saves_dir = self._resolve_saves_directory()
        
        print(f"[RetroPieProvider] ROMs dir: {self.roms_dir}")
        print(f"[RetroPieProvider] Saves dir: {self.saves_dir}")

        # Initialize internal cache reference
        if "emulator_cache" not in self.settings:
            self.settings["emulator_cache"] = {}
        self.cache = self.settings["emulator_cache"]

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
        runcommand_exists = os.path.exists(self.runcommand_path)
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
            return self.roms_dir
        
        # Get the base save directory
        base_save_dir = self._get_retroarch_setting("savefile_directory")
        
        # Handle default or empty values
        if not base_save_dir or base_save_dir.lower() == "default":
            return self.roms_dir
        
        # Expand home tilde if present
        base_save_dir = os.path.expanduser(base_save_dir)
        
        # Check for per-system subdirectories
        sort_by_content = self._get_retroarch_setting("sort_savefiles_by_content_enable")
        if sort_by_content == "true":
            return os.path.join(base_save_dir, "gba")
        
        return base_save_dir

    def _get_system_from_rom_path(self, rom_path):
        """
        Extract the system identifier from a ROM path.
        
        Returns:
            str: System identifier (e.g., "gba", "nds", "gb")
        """
        return os.path.basename(os.path.dirname(rom_path))

    def get_command(self, rom_path, core="auto", sav_path=None):
        """
        Return the command to launch RetroArch directly.
        
        Uses configuration overrides to ensure proper frame timing:
        - SDL2 audio driver (handles device sharing better than ALSA)
        - VSync enabled as primary frame limiter
        - Threaded video disabled so vsync actually blocks
        
        If sav_path is provided, forces RetroArch to use that specific save file.
        
        Automatically detects the system from ROM path and selects the appropriate core.
        
        Args:
            rom_path: Absolute path to the ROM file
            core: Core selection (not used - auto-detected from system)
            sav_path: Optional absolute path to a specific save file to use
        
        Returns:
            list: Command to launch the emulator
        """
        # Detect system from ROM path
        system = self._get_system_from_rom_path(rom_path)
        
        # Map system to RetroArch core
        # RetroPie stores cores in /opt/retropie/libretrocores/lr-{core}/
        core_map = {
            "gba": "mgba",           # Game Boy Advance
            "gb": "gambatte",        # Game Boy / Game Boy Color
            "gbc": "gambatte",       # Game Boy Color
            "nds": "desmume",        # Nintendo DS
            "nes": "fceumm",         # NES
            "snes": "snes9x",        # SNES
            "n64": "mupen64plus",    # N64
            "psx": "pcsx_rearmed",   # PlayStation 1
        }
        
        selected_core = core_map.get(system, "mgba")  # Default to mGBA
        core_path = f"/opt/retropie/libretrocores/lr-{selected_core}/{selected_core}_libretro.so"
        
        print(f"[RetroPieProvider] System: {system}, Core: {selected_core}")
        
        # Find RetroArch binary
        retroarch_bin = "/opt/retropie/emulators/retroarch/bin/retroarch"
        if not os.path.exists(retroarch_bin):
            print(f"[RetroPieProvider] ERROR: RetroArch not found at {retroarch_bin}")
            return None
        
        # Check core exists
        if not os.path.exists(core_path):
            print(f"[RetroPieProvider] ERROR: Core not found at {core_path}")
            return None
        
        # Get RetroArch config (try system-specific first, then global)
        retroarch_config = os.path.join(self.configs_base, system, "retroarch.cfg")
        if not os.path.exists(retroarch_config):
            retroarch_config = self.retroarch_global_cfg
        
        # Log the save path if one was provided
        if sav_path:
            print(f"[RetroPieProvider] Using save path: {sav_path}")
        else:
            print(f"[RetroPieProvider] No save path provided - RetroArch will use default location")
        
        # Create temporary override config for proper frame timing + save paths
        override_config = "/dev/shm/retroarch_sinew_override.cfg"
        try:
            with open(override_config, "w") as f:
                # Audio - use SDL2 which handles device sharing better
                f.write('audio_driver = "sdl2"\n')
                f.write('audio_sync = "true"\n')
                f.write('audio_latency = "64"\n')
                
                # Video/VSync - primary frame limiter
                f.write('video_vsync = "true"\n')
                f.write('video_swap_interval = "1"\n')
                f.write('video_threaded = "false"\n')
                f.write('vrr_runloop_enable = "false"\n')
                f.write('video_frame_delay = "0"\n')
                f.write('video_frame_delay_auto = "false"\n')
                f.write('video_hard_sync = "false"\n')
                f.write('video_max_swapchain_images = "3"\n')
                
                # Disable fast forward
                f.write('fastforward_ratio = "0.000000"\n')
                f.write('input_toggle_fast_forward = "nul"\n')
                f.write('input_hold_fast_forward = "nul"\n')
                
                # Fullscreen
                f.write('video_fullscreen = "true"\n')
                
                # Only override save path if a specific save file was provided
                # Otherwise, let RetroArch use its configured default behavior
                if sav_path:
                    f.write(f'savefile_path = "{sav_path}"\n')
                    print(f"[RetroPieProvider] Forcing specific save file: {sav_path}")
                
        except Exception as e:
            print(f"[RetroPieProvider] Warning: Could not write override config: {e}")
            override_config = None
        
        # Build command
        cmd = [
            retroarch_bin,
            "-L", core_path,
            "--config", retroarch_config,
        ]
        
        if override_config:
            cmd.extend(["--appendconfig", override_config])
        
        cmd.append(rom_path)
        
        return cmd

    def _update_sinew_cache(self, key, value):
        """Helper to update persistent settings only when changed."""
        if self.cache.get(key) != value:
            self.cache[key] = value
            save_sinew_settings(self.settings)

    def on_exit(self):
        """Called after the emulator exits. Clean up temporary config file."""
        override_config = "/dev/shm/retroarch_sinew_override.cfg"
        try:
            if os.path.exists(override_config):
                os.remove(override_config)
        except Exception:
            pass

    def terminate(self, process):
        """Terminate the emulator process."""
        if process:
            try:
                process.terminate()
                process.wait(timeout=2)
            except Exception as e:
                print(f"[RetroPieProvider] Terminate error: {e}")
        self.on_exit()