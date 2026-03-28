#!/usr/bin/env python3

"""
Rocknix Emulator Provider for PKsinew
"""

import os
import subprocess
import signal
import shlex
import platform
import xml.etree.ElementTree as ET
import pygame
from emulator_manager import EmulatorProvider
from settings import save_sinew_settings

class RocknixProvider(EmulatorProvider):
    active = True
    priority = 10  # Check before DesktopRetroarch (which has priority=0 by default)
    claimed_distros = {"rocknix", "jelos"}  # jelos = former ROCKNIX name

    @property
    def supported_os(self):
        return ["linux"]

    def __init__(self, sinew_settings):
        self.settings = sinew_settings

        # Skip all Linux-specific setup when running on a different OS.
        # probe() will return False regardless; this just avoids noisy output
        # and path expansions that make no sense on Windows/macOS.
        if platform.system().lower() != "linux":
            self.roms_dir = None
            self.saves_dir = None
            if "emulator_cache" not in self.settings:
                self.settings["emulator_cache"] = {}
            self.cache = self.settings["emulator_cache"]
            return

        self.system_db = os.path.expanduser("~/.config/system/configs/system.cfg")
        self.es_systems_db = os.path.expanduser("~/.emulationstation/es_systems.cfg")
        self.retroarch_cfg = os.path.expanduser("~/.config/retroarch/retroarch.cfg")
        self.roms_base = os.path.expanduser("~/roms")  # Base ROMs directory
        self.roms_dir = os.path.expanduser("~/roms/gba")  # Default to GBA for now

        # Determine saves directory from RetroArch settings
        # Check if saves live with the ROMs
        in_content_dir = self._get_retroarch_setting("savefiles_in_content_dir")
        if in_content_dir == "true":
            # Saves are in the same directory as ROMs
            self.saves_dir = self.roms_dir
        else:
            # Get the base save directory from RetroArch config
            base_save_dir = self._get_retroarch_setting("savefile_directory")

            # Handle default or empty values
            if not base_save_dir or base_save_dir.lower() == "default":
                # RetroArch default is the content dir
                self.saves_dir = self.roms_dir
            else:
                # Expand home tilde if present
                base_save_dir = os.path.expanduser(base_save_dir)

                # Check for sub-sorting by system
                sort_by_content = self._get_retroarch_setting("sort_savefiles_by_content_enable")
                if sort_by_content == "true":
                    self.saves_dir = os.path.join(base_save_dir, "gba")
                else:
                    self.saves_dir = base_save_dir

        print(f"[RocknixProvider] ROMs dir: {self.roms_dir}")
        print(f"[RocknixProvider] Saves dir: {self.saves_dir}")

        # Initialize internal cache reference
        if "emulator_cache" not in self.settings:
            self.settings["emulator_cache"] = {}
        self.cache = self.settings["emulator_cache"]
        print(f"[RocknixProvider] Cache loaded: {self.cache}")

    def probe(self, distro_id):
        is_rocknix = distro_id in self.claimed_distros
        script_exists = os.path.exists("/usr/bin/runemu.sh")
        print(
            f"[RocknixProvider] Probe - Distro: {distro_id}"
            f" (Match: {is_rocknix}), Script: {script_exists}"
        )
        return is_rocknix and script_exists

    def _get_system_from_rom_path(self, rom_path):
        """
        Extract the system identifier from a ROM path.
        
        Returns:
            str: System identifier (e.g., "gba", "nds", "gb")
        """
        return os.path.basename(os.path.dirname(rom_path))

    def _resolve_system_config(self, system):
        """
        Resolve the core/emulator for a given system.
        
        Args:
            system: System identifier (e.g., "gba", "nds", "gb")
        
        Returns:
            tuple: (core, emulator) or (None, None) if not found
        """
        core = None
        emu = None
        
        # Try system.cfg first
        if os.path.exists(self.system_db):
            try:
                with open(self.system_db, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        if k == f"{system}.core":
                            core = v
                            print(f"[RocknixProvider] Found {system} core: {core}")
                        elif k == f"{system}.emulator":
                            emu = v
                            print(f"[RocknixProvider] Found {system} emulator: {emu}")
            except Exception as e:
                print(f"[RocknixProvider] EXCEPTION reading system.cfg: {e}")

        if core and emu:
            return core, emu
        elif core:
            return core, "retroarch"

        # Fallback to ES defaults
        return self._resolve_es_default_for_system(system)

    def _resolve_es_default_for_system(self, system):
        """
        Get the default core/emulator for a system from EmulationStation config.
        
        Args:
            system: System identifier (e.g., "gba", "nds", "gb")
        
        Returns:
            tuple: (core, emulator) or (None, None) if not found
        """
        if not os.path.exists(self.es_systems_db):
            return None, None
        
        try:
            tree = ET.parse(self.es_systems_db)
            for sys_elem in tree.getroot().findall("system"):
                name_node = sys_elem.find("name")
                if name_node is None or name_node.text.lower() != system.lower():
                    continue
                    
                for emu in sys_elem.findall(".//emulator"):
                    emu_name = emu.get("name")
                    for core in emu.findall(".//core"):
                        if core.get("default") == "true":
                            print(
                                f"[RocknixProvider] Found default {system} core: "
                                f"{core.text}, emulator: {emu_name}"
                            )
                            return core.text, emu_name
        except Exception as e:
            print(f"[RocknixProvider] EXCEPTION parsing ES config: {e}")
        
        return None, None

    def get_command(self, rom_path, core="auto", sav_path=None):
        """
        Return the list of strings representing the shell command
        to launch the emulator.
        
        Automatically detects the system from the ROM path and resolves
        the appropriate core/emulator configuration.
        """
        # Detect system from ROM path
        system = self._get_system_from_rom_path(rom_path)
        print(f"[RocknixProvider] Detected system: {system}")

        # RetroArch mGBA core uses .srm extension
        # Create a .srm symlink/copy if the save is .sav
        if sav_path and sav_path.endswith('.sav'):
            rom_base = os.path.splitext(os.path.basename(rom_path))[0]
            srm_path = os.path.join(os.path.dirname(sav_path), f"{rom_base}.srm")
            
            print(f"[RocknixProvider] Creating .srm symlink:")
            print(f"  Location: {srm_path}")
            print(f"  Target: {sav_path}")
            
            try:
                # Remove old file/symlink if it exists
                if os.path.islink(srm_path):
                    os.remove(srm_path)
                    print(f"[RocknixProvider] Removed old symlink")
                elif os.path.exists(srm_path):
                    # If it's a real file, back it up before replacing
                    backup_path = f"{srm_path}.backup"
                    os.rename(srm_path, backup_path)
                    print(f"[RocknixProvider] Backed up existing .srm to {backup_path}")
                
                # Try symlink first
                try:
                    os.symlink(sav_path, srm_path)
                    print(f"[RocknixProvider] ✓ Symlink created")
                except (OSError, PermissionError) as e:
                    # If symlink fails, copy the file instead
                    print(f"[RocknixProvider] Symlink failed ({e}), copying file instead")
                    import shutil
                    shutil.copy2(sav_path, srm_path)
                    print(f"[RocknixProvider] ✓ Save file copied to .srm")
            except Exception as e:
                print(f"[RocknixProvider] Failed to create .srm: {e}")

        # Controller GUID — read directly from the joystick pygame already has open.
        guid = self.cache.get("p1_guid")
        if not guid:
            guid = self._get_joystick_guid()
            if guid:
                self._update_sinew_cache("p1_guid", guid)

        if not guid:
            print("[RocknixProvider] ABORT: No Controller GUID found.")
            return None

        # Resolve Core/Emu for this system
        cache_key_core = f"{system}_core"
        cache_key_emu = f"{system}_emulator"
        
        parsed_core, parsed_emu = self._resolve_system_config(system)
        if parsed_core:
            selected_core = parsed_core
            self._update_sinew_cache(cache_key_core, parsed_core)
        else:
            selected_core = self.cache.get(cache_key_core)

        if parsed_emu:
            selected_emu = parsed_emu
            self._update_sinew_cache(cache_key_emu, parsed_emu)
        else:
            selected_emu = self.cache.get(cache_key_emu)

        if not selected_core or not selected_emu:
            print(f"[RocknixProvider] ERROR: No core/emulator found for {system}")
            return None

        controller_str = f" -p1index 0 -p1guid {guid} "

        emu_cmd = f"/usr/bin/runemu.sh {shlex.quote(rom_path)} -P{system} --core={selected_core} --emulator={selected_emu} --controllers={shlex.quote(controller_str)}"  # pylint: disable=line-too-long  # noqa: E501
        return ["sh", "-c", emu_cmd]

    def _get_joystick_guid(self):
        """Return the SDL GUID of the first joystick pygame currently has open."""
        try:
            if pygame.joystick.get_count() > 0:
                joy = pygame.joystick.Joystick(0)
                return joy.get_guid()
        except Exception as e:
            print(f"[RocknixProvider] Could not read joystick GUID: {e}")
        return None

    def _get_retroarch_setting(self, setting_key):
        if not os.path.exists(self.retroarch_cfg):
            return None
        try:
            with open(self.retroarch_cfg, 'r') as f:
                for line in f:
                    clean_line = line.strip()
                    if clean_line.startswith(setting_key):
                        parts = clean_line.split('=', 1)
                        if len(parts) > 1:
                            value = parts[1].strip().strip('"').strip("'")
                            return value
        except Exception as e:
            print(f"[RocknixProvider] EXCEPTION reading RA config: {e}")
        return None

    def _update_sinew_cache(self, key, value):
        """Helper to update persistent settings only when changed."""
        if self.cache.get(key) != value:
            self.cache[key] = value
            save_sinew_settings(self.settings)

    def on_exit(self):
        pass

    def terminate(self, process):
        if process:
            try:
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)
                process.wait(timeout=0.5)
            except OSError as e:
                if e.errno != 3:
                    print(f"[RocknixProvider] Terminate error: {e}")
        try:
            subprocess.run(["killall", "-9", "retroarch"], stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[RocknixProvider] Killall failed: {e}")
        self.on_exit()