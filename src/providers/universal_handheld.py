#!/usr/bin/env python3

"""
Universal Handheld Emulator Provider for PKSinew
Supports most Linux handheld firmware automatically
"""

import os
import platform
import shlex
from emulator_manager import EmulatorProvider


class HandheldProvider(EmulatorProvider):

    active = True
    priority = 5

    claimed_distros = {
        "rocknix",
        "jelos",
        "arkos",
        "amberelec",
        "muos",
        "raspbian"
    }

    @property
    def supported_os(self):
        return ["linux"]

    def __init__(self, sinew_settings):

        self.settings = sinew_settings
        self.strategy = None
        self.roms_dir = None
        self.saves_dir = None

    # ------------------------------------------------

    def probe(self, distro_id):

        if platform.system().lower() != "linux":
            return False

        # ROCKNIX / JELOS
        if os.path.exists("/usr/bin/runemu.sh"):
            self.strategy = "rocknix"
            self.roms_dir = os.path.expanduser("~/roms")
            self.saves_dir = self.roms_dir
            return True

        # ArkOS
        if os.path.exists("/usr/bin/emulationstation") and os.path.exists("/roms"):
            self.strategy = "arkos"
            self.roms_dir = "/roms"
            self.saves_dir = self.roms_dir
            return True

        # AmberELEC
        if os.path.exists("/storage/roms"):
            self.strategy = "amberelec"
            self.roms_dir = "/storage/roms"
            self.saves_dir = self.roms_dir
            return True

        # muOS
        if os.path.exists("/mnt/sdcard/roms"):
            self.strategy = "muos"
            self.roms_dir = "/mnt/sdcard/roms"
            self.saves_dir = self.roms_dir
            return True

        # RetroPie
        if os.path.exists("/home/pi/RetroPie/roms"):
            self.strategy = "retropie"
            self.roms_dir = "/home/pi/RetroPie/roms"
            self.saves_dir = self.roms_dir
            return True

        return False

    # ------------------------------------------------

    def get_command(self, rom_path, core="auto"):

        system = os.path.basename(os.path.dirname(rom_path))

        # ROCKNIX / JELOS
        if self.strategy == "rocknix":

            cmd = (
                f"/usr/bin/runemu.sh {shlex.quote(rom_path)} "
                f"-P{system}"
            )

            return ["sh", "-c", cmd]

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

        # RetroPie
        if self.strategy == "retropie":

            cmd = (
                f"/opt/retropie/supplementary/runcommand/runcommand.sh "
                f"0 _SYS_ {system} {shlex.quote(rom_path)}"
            )

            return ["sh", "-c", cmd]

        return None

    # ------------------------------------------------

    def terminate(self, process):

        if process:
            try:
                process.terminate()
            except Exception:
                pass