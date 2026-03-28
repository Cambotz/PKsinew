#!/usr/bin/env python3

"""
Universal Handheld Emulator Provider for PKSinew
Supports most Linux handheld firmware automatically
"""

import os
import platform
import shlex
import signal
import subprocess
from emulator_manager import EmulatorProvider


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
                print(f"[HandheldProvider] Detected ArkOS")
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

        # ArkOS
        if self.strategy == "arkos":
            cmd = (
                f"/usr/bin/emulatorlauncher "
                f"{system} "
                f"{shlex.quote(rom_path)}"
            )
            return ["sh", "-c", cmd]

        # AmberELEC
        if self.strategy == "amberelec":
            cmd = (
                f"/usr/bin/emulatorlauncher "
                f"{system} "
                f"{shlex.quote(rom_path)}"
            )
            return ["sh", "-c", cmd]

        # muOS
        if self.strategy == "muos":
            cmd = (
                f"/usr/bin/muos-launch "
                f"{system} "
                f"{shlex.quote(rom_path)}"
            )
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