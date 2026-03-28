#!/usr/bin/env python3

"""
Universal Handheld Emulator Provider for PKsinew
Supports most Linux handheld firmware automatically
"""

import os
import platform
import shlex
import signal
import subprocess
import pygame
from emulator_manager import EmulatorProvider
from settings import save_sinew_settings


class HandheldProvider(EmulatorProvider):

    active = True
    priority = 5
    is_script_launcher = True  # Tell emulator_session NOT to inject save paths

    claimed_distros = {
        "arkos",
        "amberelec",
        "muos",
        # rocknix/jelos handled by dedicated RocknixProvider
        # raspbian handled by dedicated RetroPieProvider
    }

    @property
    def supported_os(self):
        return ["linux"]

    def __init__(self, sinew_settings):
        self.settings = sinew_settings
        self.strategy = None
        self.roms_base = None  # Base ROMs directory (e.g., /roms or /storage/roms)
        self.roms_dir = None
        self.saves_dir = None

        # Skip Linux-specific setup on non-Linux platforms
        if platform.system().lower() != "linux":
            if "emulator_cache" not in self.settings:
                self.settings["emulator_cache"] = {}
            self.cache = self.settings["emulator_cache"]
            return

        # Initialize cache
        if "emulator_cache" not in self.settings:
            self.settings["emulator_cache"] = {}
        self.cache = self.settings["emulator_cache"]

    # ------------------------------------------------

    def _find_roms_base(self, candidate_paths):
        """
        Find the actual ROMs base directory from a list of candidates.
        Returns the first path that exists and contains at least one system directory.
        
        Args:
            candidate_paths: List of potential ROM base directories to check
            
        Returns:
            str: The validated ROMs base path, or None if not found
        """
        common_systems = ["gba", "nds", "gb", "gbc", "n64", "nes", "snes", "psx"]
        
        for base_path in candidate_paths:
            if not os.path.exists(base_path):
                continue
                
            # Check if this directory contains any common system folders
            try:
                entries = os.listdir(base_path)
                if any(system in entries for system in common_systems):
                    print(f"[HandheldProvider] Found ROMs at: {base_path}")
                    return base_path
            except (OSError, PermissionError):
                continue
                
        return None

    # ------------------------------------------------

    def _find_retroarch(self):
        """
        Find the RetroArch binary on the system.
        
        Returns:
            str: Path to retroarch binary, or None if not found
        """
        retroarch_paths = [
            "/usr/local/bin/retroarch",
            "/usr/bin/retroarch",
            "/opt/retroarch/bin/retroarch",
            "/usr/local/bin/retroarch32",
            "/home/ark/retroarch",
            "/opt/system/Tools/retroarch/retroarch",
        ]
        
        for path in retroarch_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        
        # Try which command
        try:
            result = subprocess.run(
                ["which", "retroarch"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        
        return None

    # ------------------------------------------------

    def _get_system_from_rom_path(self, rom_path):
        """
        Extract the system identifier from a ROM path.
        
        For multi-system support, the system is typically the parent directory
        of the ROM file. For example:
        - /roms/gba/pokemon.gba -> "gba"
        - /roms/nds/pokemon.nds -> "nds"
        - /roms/gb/pokemon.gb -> "gb"
        
        Returns:
            str: System identifier (e.g., "gba", "nds", "gb")
        """
        return os.path.basename(os.path.dirname(rom_path))

    # ------------------------------------------------

    def _get_joystick_guid(self):
        """Return the SDL GUID of the first joystick pygame currently has open."""
        try:
            if pygame.joystick.get_count() > 0:
                joy = pygame.joystick.Joystick(0)
                return joy.get_guid()
        except Exception as e:
            print(f"[HandheldProvider] Could not read joystick GUID: {e}")
        return None

    # ------------------------------------------------

    def _update_sinew_cache(self, key, value):
        """Helper to update persistent settings only when changed."""
        if self.cache.get(key) != value:
            self.cache[key] = value
            save_sinew_settings(self.settings)

    # ------------------------------------------------

    def probe(self, distro_id):
        if platform.system().lower() != "linux":
            return False

        # ArkOS
        if os.path.exists("/usr/bin/emulationstation"):
            # Check multiple possible ROM locations (internal + 2nd SD)
            arkos_candidates = [
                "/roms2",          # Secondary SD (primary check)
                "/roms",           # Internal/primary SD
                "/mnt/sdcard/roms" # Alternative secondary SD mount
            ]
            self.roms_base = self._find_roms_base(arkos_candidates)
            if self.roms_base:
                self.strategy = "arkos"
                self.roms_dir = os.path.join(self.roms_base, "gba")  # Default to GBA
                self.saves_dir = self.roms_dir
                
                # Find RetroArch binary
                self.retroarch_path = self._find_retroarch()
                if not self.retroarch_path:
                    print("[HandheldProvider] WARNING: RetroArch not found - external provider disabled")
                    return False
                    
                print(f"[HandheldProvider] Detected ArkOS")
                print(f"[HandheldProvider] RetroArch: {self.retroarch_path}")
                return True

        # AmberELEC
        amberelec_candidates = [
            "/roms2",             # Secondary SD (primary check)
            "/storage/roms2",     # Secondary SD alternative
            "/storage/roms",      # Internal storage
            "/roms"               # Alternative mount
        ]
        self.roms_base = self._find_roms_base(amberelec_candidates)
        if self.roms_base:
            self.strategy = "amberelec"
            self.roms_dir = os.path.join(self.roms_base, "gba")  # Default to GBA
            self.saves_dir = self.roms_dir
            print(f"[HandheldProvider] Detected AmberELEC")
            return True

        # muOS
        muos_candidates = [
            "/mnt/mmc/roms",      # Secondary SD (common muOS mount for 2nd card)
            "/mnt/sdcard2/roms",  # Alternative secondary mount
            "/mnt/sdcard/roms",   # Primary SD
            "/run/muos/storage/rom", # Alternative muOS path
            "/roms2"              # Generic secondary mount
        ]
        self.roms_base = self._find_roms_base(muos_candidates)
        if self.roms_base:
            self.strategy = "muos"
            self.roms_dir = os.path.join(self.roms_base, "gba")  # Default to GBA
            self.saves_dir = self.roms_dir
            print(f"[HandheldProvider] Detected muOS")
            return True

        return False

    # ------------------------------------------------

    def get_command(self, rom_path, core="auto", sav_path=None):
        """
        Build the emulator launch command for the given ROM.
        
        The system identifier (gba, nds, gb, etc.) is automatically extracted
        from the ROM's parent directory path.
        """
        system = self._get_system_from_rom_path(rom_path)
        print(f"[HandheldProvider] System detected: {system}")
        print(f"[HandheldProvider] ROM path: {rom_path}")
        print(f"[HandheldProvider] Save path: {sav_path}")

        # ArkOS / dARKos - call retroarch directly
        if self.strategy == "arkos":
            # Map system to RetroArch core
            core_map = {
                "gba": "mgba",
                "gbc": "gambatte",
                "gb": "gambatte",
                "nds": "desmume",
                "nes": "fceumm",
                "snes": "snes9x",
                "n64": "mupen64plus_next",
                "psx": "pcsx_rearmed"
            }
            core_name = core_map.get(system, "mgba")
            
            # RetroArch mGBA core uses .srm extension
            # Create a .srm symlink in the save directory if the save is .sav
            if sav_path and sav_path.endswith('.sav'):
                rom_base = os.path.splitext(os.path.basename(rom_path))[0]
                srm_path = os.path.join(os.path.dirname(sav_path), f"{rom_base}.srm")
                
                print(f"[HandheldProvider] Creating .srm symlink:")
                print(f"  Location: {srm_path}")
                print(f"  Target: {sav_path}")
                
                try:
                    # Remove old file/symlink if it exists
                    if os.path.islink(srm_path):
                        os.remove(srm_path)
                        print(f"[HandheldProvider] Removed old symlink")
                    elif os.path.exists(srm_path):
                        # If it's a real file, back it up before replacing
                        backup_path = f"{srm_path}.backup"
                        os.rename(srm_path, backup_path)
                        print(f"[HandheldProvider] Backed up existing .srm to {backup_path}")
                    
                    # Try symlink first
                    try:
                        os.symlink(sav_path, srm_path)
                        print(f"[HandheldProvider] ✓ Symlink created")
                    except (OSError, PermissionError) as e:
                        # If symlink fails, copy the file instead
                        print(f"[HandheldProvider] Symlink failed ({e}), copying file instead")
                        import shutil
                        shutil.copy2(sav_path, srm_path)
                        print(f"[HandheldProvider] ✓ Save file copied to .srm")
                except Exception as e:
                    print(f"[HandheldProvider] Failed to create .srm: {e}")
            
            # Check for core override config
            config_dir = "/home/ark/.config/retroarch/config"
            core_override = os.path.join(config_dir, f"{core_name}", f"{core_name}.cfg")
            
            # Create a minimal override config for this device
            override_config = f"/tmp/retroarch_sinew_{core_name}.cfg"
            try:
                with open(override_config, "w") as f:
                    # Use 'oga' video driver (specific to OGA/RG351 devices)
                    # Fallback chain: oga -> gl -> sdl2
                    f.write('video_driver = "oga"\n')
                    # Audio driver
                    f.write('audio_driver = "sdl2"\n')
                    # VSync for frame pacing
                    f.write('video_vsync = "true"\n')
                    # Rotation: 0 = normal (landscape)
                    f.write('video_rotation = "0"\n')
                    # Don't show menu on start
                    f.write('menu_driver = "null"\n')
                print(f"[HandheldProvider] Created override config: {override_config}")
            except Exception as e:
                print(f"[HandheldProvider] Failed to create override: {e}")
                override_config = None
            
            config_append = ""
            if override_config:
                config_append = f"--appendconfig {shlex.quote(override_config)} "
            
            if os.path.exists(core_override):
                config_append += f"--appendconfig {shlex.quote(core_override)} "
                print(f"[HandheldProvider] Using core override: {core_override}")
            
            # Full command with environment setup for KMS/DRM
            # Set SDL to use kmsdrm video driver (critical for handheld without X11)
            cmd = (
                f"HOME=/home/ark "
                f"SDL_VIDEODRIVER=kmsdrm "
                f"{self.retroarch_path} "
                f"{config_append}"
                f"-L /home/ark/.config/retroarch/cores/{core_name}_libretro.so "
                f"{shlex.quote(rom_path)}"
            )
            print(f"[HandheldProvider] ArkOS command: {cmd}")
            return ["sh", "-c", cmd]

        # AmberELEC
        if self.strategy == "amberelec":
            cmd = (
                f"/usr/bin/emulatorlauncher "
                f"{system} "
                f"{shlex.quote(rom_path)}"
            )
            print(f"[HandheldProvider] AmberELEC command: {cmd}")
            return ["sh", "-c", cmd]

        # muOS
        if self.strategy == "muos":
            cmd = (
                f"/usr/bin/muos-launch "
                f"{system} "
                f"{shlex.quote(rom_path)}"
            )
            print(f"[HandheldProvider] muOS command: {cmd}")
            return ["sh", "-c", cmd]

        return None

    # ------------------------------------------------

    def on_exit(self):
        """Called after emulator exits. Override for cleanup tasks."""
        pass

    def terminate(self, process):
        """
        Terminate the emulator process.
        Uses process group kill to ensure wrapper scripts and child processes are stopped.
        """
        if process:
            try:
                # Kill the entire process group (launcher script + emulator)
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)
                process.wait(timeout=0.5)
            except OSError as e:
                if e.errno != 3:  # Ignore "No such process"
                    print(f"[HandheldProvider] Terminate error: {e}")
            except Exception as e:
                print(f"[HandheldProvider] Terminate error: {e}")

        # Cleanup: ensure RetroArch is killed (common emulator backend)
        try:
            subprocess.run(["killall", "-9", "retroarch"], stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[HandheldProvider] Killall failed: {e}")

        self.on_exit()