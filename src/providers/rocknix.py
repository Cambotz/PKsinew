#!/usr/bin/env python3

"""
Rocknix Emulator Provider for PKsinew
"""

import os
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
        
        self.retroarch_cfg = "/storage/.config/retroarch/retroarch.cfg"
        self.roms_dir = "/storage/roms/gba"
        self.saves_dir = self.get_save_dir(self.roms_dir)
        
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
        if core == "auto":
            selected_core = self.cache.get("gba_core")
            selected_emu = self.cache.get("gba_emulator")
            
            if not selected_core or not selected_emu:
                selected_core, selected_emu = self._resolve_gba_config()
                self._update_sinew_cache("gba_core", selected_core)
                self._update_sinew_cache("gba_emulator", selected_emu)
        else:
            selected_core = core
            selected_emu = "retroarch"

        controller_str = f" -p1index 0 -p1guid {guid} "

        cmd = [
            "/usr/bin/runemu.sh",
            rom_path,
            "-Pgba",
            f"--core={selected_core}",
            f"--emulator={selected_emu}",
            f"--controllers={controller_str}"
        ]
        
        return cmd

    def _get_last_input_guid(self):
        path = "/storage/.emulationstation/es_last_input.cfg"
        if not os.path.exists(path): return None
        try:
            tree = ET.parse(path)
            node = tree.getroot().find('inputConfig')
            return node.get('deviceGUID') if node is not None else None
        except: return None

    def _get_retroarch_setting(self, setting_key):
        if not os.path.exists(self.retroarch_cfg):
            return None
        try:
            with open(self.retroarch_cfg, 'r') as f:
                for line in f:
                    # Match key = "value" or key = value
                    if line.startswith(setting_key):
                        value = line.split('=')[1].strip()
                        return value.replace('"', '')
        except Exception as e:
            print(f"[RocknixProvider] EXCEPTION reading RA config: {e}")
        return None

    def get_save_dir(self, rom_path):
        """
        Resolves the absolute path to the save folder based on RetroArch settings.
        """
        # Check if saves live with the ROMs
        in_content_dir = self._get_retroarch_setting("savefiles_in_content_dir")
        if in_content_dir == "true":
            return os.path.dirname(rom_path)

        # Get the base save directory
        base_save_dir = self._get_retroarch_setting("savefile_directory")
        
        # Handle default or empty values
        if not base_save_dir or base_save_dir.lower() == "default":
            # RetroArch default is usually the content dir if not specified
            return os.path.dirname(rom_path)

        # Expand home tilde if present (e.g., ~/.config -> /storage/.config)
        base_save_dir = os.path.expanduser(base_save_dir)

        # Check for sub-sorting by system (content)
        sort_by_content = self._get_retroarch_setting("sort_savefiles_by_content_enable")
        if sort_by_content == "true":
            return os.path.join(base_save_dir, "gba")

        return base_save_dir
        
    def get_save_path(self, rom_path):
        """
        Returns the absolute path to the .srm file for the given ROM.
        """
        save_dir = self.get_save_dir(rom_path)
        rom_name = os.path.splitext(os.path.basename(rom_path))[0]
        
        # RetroArch uses .srm by default for battery saves
        return os.path.join(save_dir, f"{rom_name}.srm")

    def _resolve_gba_config(self):
        paths = ["/storage/.emulationstation/es_systems.cfg", "/etc/emulationstation/es_systems.cfg"]
        for path in paths:
            if not os.path.exists(path): continue
            try:
                tree = ET.parse(path)
                for system in tree.getroot().findall('system'):
                    if system.find('name').text == 'gba':
                        for emu in system.findall('.//emulator'):
                            emu_name = emu.get('name')
                            for core in emu.findall('.//core'):
                                if core.get('default') == 'true':
                                    return core.text, emu_name
            except Exception as e:
                print(f"[RocknixProvider] EXCEPTION parsing system config: {e}")
        return "mgba", "retroarch"

    def _update_sinew_cache(self, key, value):
        """Helper to update persistent settings only when changed."""
        if self.cache.get(key) != value:
            self.cache[key] = value
            save_sinew_settings(self.settings)