#!/usr/bin/env python3

"""
Rocknix Emulator Provider for PKsinew
"""

import os
import subprocess
import signal
import shlex
import xml.etree.ElementTree as ET
from external_emulator import EmulatorProvider 
from settings import save_sinew_settings

class RocknixProvider(EmulatorProvider):
    active = True
    @property
    def supported_os(self):
        return ["linux"]

    def __init__(self, sinew_settings):
        self.settings = sinew_settings
        
        self.system_db = os.path.expanduser("~/.config/system/configs/system.cfg")
        self.es_systems_db = os.path.expanduser("~/.emulationstation/es_systems.cfg")
        self.retroarch_cfg = os.path.expanduser("~/.config/retroarch/retroarch.cfg")
        self.roms_dir = os.path.expanduser("~/roms/gba")
        
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
        is_rocknix = (distro_id == "rocknix")
        script_exists = os.path.exists("/usr/bin/runemu.sh")
        print(f"[RocknixProvider] Probe - Distro: {distro_id} (Match: {is_rocknix}), Script: {script_exists}")
        return is_rocknix and script_exists

    def get_command(self, rom_path, core="auto"):
        """
        Return the list of strings representing the shell command 
        to launch the emulator.
        """
        
        # Controller GUID
        guid = self.cache.get("p1_guid")
        if not guid:
            guid = self._get_last_input_guid()
            if guid:
                self._update_sinew_cache("p1_guid", guid)
        
        if not guid:
            print("[ExternalEmu] ABORT: No Controller GUID found.")
            return None

        # Resolve Core/Emu
        parsed_core, parsed_emu = self._resolve_gba_config()
        if parsed_core:
            selected_core = parsed_core
            self._update_sinew_cache("gba_core", parsed_core)
        else:
            selected_core = self.cache.get("gba_core")

        if parsed_emu:
            selected_emu = parsed_emu
            self._update_sinew_cache("gba_emulator", parsed_emu)
        else:
            selected_emu = self.cache.get("gba_emulator")

        controller_str = f" -p1index 0 -p1guid {guid} "

        emu_cmd = f"/usr/bin/runemu.sh {shlex.quote(rom_path)} -Pgba --core={selected_core} --emulator={selected_emu} --controllers={shlex.quote(controller_str)}"
        return ["sh", "-c", emu_cmd]

    def _get_last_input_guid(self):
        path = os.path.expanduser("~/.emulationstation/es_last_input.cfg")
        if not os.path.exists(path):
            return None
        try:
            tree = ET.parse(path)
            node = tree.getroot().find('inputConfig')
            if node is not None:
                return node.get('deviceGUID')
            else:
                return None
        except Exception:
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

    def _resolve_gba_config(self):
        """Resolve the GBA core/emulator"""
        core = None
        emu = None
        print(f"[RocknixProvider] Resolving GBA config from {self.system_db}")
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
                        if k == "gba.core":
                            core = v
                            print(f"[RocknixProvider] Found system.cfg core: {core}")
                        elif k == "gba.emulator":
                            emu = v
                            print(f"[RocknixProvider] Found system.cfg emulator: {emu}")
            except Exception as e:
                print(f"[RocknixProvider] EXCEPTION reading system.cfg: {e}")

        if core and emu:
            print(f"[RocknixProvider] Using system.cfg config: {core}/{emu}")
            return core, emu
        elif core:
            print(f"[RocknixProvider] Using system.cfg core with fallback emulator: {core}/retroarch")
            return core, "retroarch"

        # Fallback to ES defaults
        print("[RocknixProvider] Falling back to ES defaults")
        result = self._resolve_es_default()
        if result is None:
            print("[RocknixProvider] ERROR: No GBA core/emulator defined, cannot launch.")
            return None, None
        print(f"[RocknixProvider] Using ES default config: {result[0]}/{result[1]}")
        return result


    def _resolve_es_default(self):
        """Fallback for GBA if system.cfg has no core/emulator defined."""

        if not os.path.exists(self.es_systems_db):
            print(f"[RocknixProvider] ES config not found: {self.es_systems_db}")
            return None
        try:
            print(f"[RocknixProvider] Parsing ES config: {self.es_systems_db}")
            tree = ET.parse(self.es_systems_db)
            for system in tree.getroot().findall("system"):
                name_node = system.find("name")
                if name_node is None:
                    continue
                if name_node.text.lower() != "gba":
                    continue
                print(f"[RocknixProvider] Found GBA system in {self.es_systems_db}")
                for emu in system.findall(".//emulator"):
                    emu_name = emu.get("name")
                    for core in emu.findall(".//core"):
                        if core.get("default") == "true":
                            print(f"[RocknixProvider] Found default core: {core.text}, emulator: {emu_name}")
                            return core.text, emu_name
        except Exception as e:
            print(f"[RocknixProvider] EXCEPTION parsing ES config {self.es_systems_db}: {e}")

        # No valid core/emulator found
        print("[RocknixProvider] No default GBA core/emulator found in ES configs")
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