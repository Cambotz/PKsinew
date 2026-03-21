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
        if os.path.exists("/usr/bin/emulationstation") and os.path.exists("/roms"):
            self.strategy = "arkos"
            self.roms_base = "/roms"
            self.roms_dir = "/roms/gba"  # Default to GBA for now
            self.saves_dir = self.roms_dir
            print(f"[HandheldProvider] Detected ArkOS")
            return True

        # AmberELEC
        if os.path.exists("/storage/roms"):
            self.strategy = "amberelec"
            self.roms_base = "/storage/roms"
            self.roms_dir = "/storage/roms/gba"  # Default to GBA for now
            self.saves_dir = self.roms_dir
            print(f"[HandheldProvider] Detected AmberELEC")
            return True

        # muOS
        if os.path.exists("/mnt/sdcard/roms"):
            self.strategy = "muos"
            self.roms_base = "/mnt/sdcard/roms"
            self.roms_dir = "/mnt/sdcard/roms/gba"  # Default to GBA for now
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
