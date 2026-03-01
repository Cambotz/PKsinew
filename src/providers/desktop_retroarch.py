#!/usr/bin/env python3

"""
desktop_retroarch.py

Desktop provider for RetroArch on Linux, macOS, and Windows.

Linux   — checks for the 'retroarch' package binary, then the Flatpak
          org.libretro.Retroarch (preference is configurable).
macOS   — checks for 'retroarch' in PATH (Homebrew / manual install),
          then the RetroArch.app bundle in /Applications.
Windows — checks for 'retroarch.exe' in PATH, then the common default
          install locations under %APPDATA% and Program Files.

On all platforms the retroarch.cfg is parsed for the cores and saves
directories.  Falls back to Sinew defaults when config values are missing
or point to non-existent directories.
"""

import os
import platform
import signal
import subprocess
import sys
from enum import StrEnum

from config import ROMS_DIR, SAVES_DIR
from external_emulator import EmulatorProvider
from settings import save_sinew_settings


class InstallationType(StrEnum):
    """Preferred installation type for RetroArch discovery."""
    PACKAGE  = "package"   # system package / Homebrew / PATH binary
    FLATPAK  = "flatpak"   # Linux Flatpak only
    APP      = "app"       # macOS .app bundle
    PORTABLE = "portable"  # Windows portable / installer paths


_CURRENT_OS = platform.system().lower()   # "linux" | "darwin" | "windows"


class DesktopRetroarch(EmulatorProvider):
    """
    Cross-platform RetroArch provider for Linux, macOS, and Windows desktops.
    Discovers the RetroArch binary, reads retroarch.cfg, and resolves
    the best available GBA core for launch.
    """

    active = True

    @property
    def supported_os(self):
        return ["linux", "darwin", "windows"]

    def __init__(
        self,
        sinew_settings,
        preferred_installation: InstallationType = InstallationType.PACKAGE,
    ):
        self.settings = sinew_settings
        self.pref_inst = preferred_installation

        self.retroarch_command: list[str] | None = None
        self.config_path: str | None = None
        self.core_path: str | None = None
        self.saves_dir: str = SAVES_DIR
        self.roms_dir: str = ROMS_DIR

        # Initialize internal cache reference
        if "emulator_cache" not in self.settings:
            self.settings["emulator_cache"] = {}
        self.cache = self.settings["emulator_cache"]

    # ------------------------------------------------------------------
    # EmulatorProvider interface
    # ------------------------------------------------------------------

    def probe(self, distro_id) -> bool:
        """Return True if RetroArch is installed and configured on this system."""
        print(f"[DesktopRetroarch] Probing on {_CURRENT_OS} (pref: {self.pref_inst})")
        self.retroarch_command = self._find_installation()

        if self.retroarch_command is None:
            print("[DesktopRetroarch] RetroArch binary not found in PATH or known locations.")
            print("[DesktopRetroarch] Add retroarch to PATH or install it to a default location.")
            return False

        print(f"[DesktopRetroarch] Found RetroArch: {' '.join(self.retroarch_command)}")

        config_path = self._find_config()
        if not config_path:
            print("[DesktopRetroarch] No retroarch.cfg found in any expected location.")
            return False

        print(f"[DesktopRetroarch] Config: {config_path}")
        self.config_path = config_path
        if not self._parse_config(config_path):
            return False

        print(f"[DesktopRetroarch] Cores dir: {self.core_path}")
        print(f"[DesktopRetroarch] Saves dir: {self.saves_dir}")

        # ROMs directory: RetroArch has no single roms_dir in its config.
        # Use retroarch_roms_dir from cache if set (user-editable), otherwise
        # auto-detect and seed the cache key so the user can edit it later.
        custom_roms = self.cache.get("retroarch_roms_dir", "")
        if custom_roms and os.path.isdir(custom_roms):
            self.roms_dir = custom_roms
        else:
            if self.retroarch_command:
                exe_dir = os.path.dirname(self.retroarch_command[0])
                roms_candidate = os.path.join(exe_dir, "roms")
                if os.path.isdir(roms_candidate):
                    self.roms_dir = roms_candidate
                # else: keep ROMS_DIR default set in __init__
            # Seed the key so it's visible in sinew_settings.json for editing.
            # Only written when not already present — never overwrites user edits.
            if not custom_roms:
                self._update_sinew_cache("retroarch_roms_dir", self.roms_dir)

        print(f"[DesktopRetroarch] ROMs dir: {self.roms_dir}")

        # Persist other resolved paths (informational, not user-editable).
        self._update_sinew_cache("retroarch_resolved_exe", self.retroarch_command[0])
        self._update_sinew_cache("retroarch_resolved_config", self.config_path)
        self._update_sinew_cache("retroarch_resolved_cores", self.core_path)
        self._update_sinew_cache("retroarch_resolved_saves", self.saves_dir)
        self._update_sinew_cache("retroarch_resolved_saves", self.saves_dir)

        return True

    def get_command(self, rom_path, core="auto"):
        """Return the shell command list to launch RetroArch with the given ROM."""
        core_file = self._find_core_file(core)
        if not core_file:
            print("[DesktopRetroarch] No compatible GBA core found.")
            return None

        # retroarch -L /path/to/core.<ext> /path/to/rom.gba
        return self.retroarch_command + ["-L", core_file, rom_path]

    def on_exit(self):
        """Called when the emulator exits cleanly."""
        print("[DesktopRetroarch] Emulator exited.")

    def terminate(self, process):
        """Terminate the RetroArch process and call on_exit."""
        if process:
            try:
                if _CURRENT_OS == "windows":
                    # Windows does not support POSIX signals; use terminate()
                    process.terminate()
                else:
                    process.send_signal(signal.SIGTERM)
                process.wait(timeout=3)
            except Exception as e:
                print(f"[DesktopRetroarch] Terminate error: {e}")
                try:
                    process.kill()
                except Exception:
                    pass
        self.on_exit()

    # ------------------------------------------------------------------
    # Installation discovery
    # ------------------------------------------------------------------

    def _find_installation(self) -> list[str] | None:
        """Dispatch to the platform-appropriate finder, respecting preference."""
        if _CURRENT_OS == "linux":
            return self._find_linux()
        if _CURRENT_OS == "darwin":
            return self._find_macos()
        if _CURRENT_OS == "windows":
            return self._find_windows()
        return None

    def _find_linux(self) -> list[str] | None:
        """Check for the retroarch package binary then the Flatpak."""
        if self.pref_inst == InstallationType.FLATPAK:
            result = self._find_flatpak()
            if result:
                return result
            print("[DesktopRetroarch] Flatpak org.libretro.Retroarch not found, trying PATH.")
            return self._find_binary("retroarch")
        result = self._find_binary("retroarch")
        if result:
            return result
        print("[DesktopRetroarch] 'retroarch' not in PATH, trying Flatpak.")
        return self._find_flatpak()

    def _find_macos(self) -> list[str] | None:
        """Check for 'retroarch' in PATH (Homebrew), then the .app bundle."""
        if self.pref_inst == InstallationType.APP:
            result = self._find_macos_app()
            if result:
                return result
            print("[DesktopRetroarch] RetroArch.app not found in /Applications, trying PATH.")
            return self._find_binary("retroarch")
        result = self._find_binary("retroarch")
        if result:
            return result
        print("[DesktopRetroarch] 'retroarch' not in PATH, trying /Applications/RetroArch.app.")
        return self._find_macos_app()

    def _find_windows(self) -> list[str] | None:
        """Check for 'retroarch.exe' in PATH then common install directories."""
        path_result = self._find_binary("retroarch.exe")
        if path_result:
            return path_result

        candidates = []
        appdata = os.environ.get("APPDATA", "")
        programfiles = os.environ.get("ProgramFiles", r"C:\Program Files")
        programfiles_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

        if appdata:
            candidates.append(os.path.join(appdata, "RetroArch", "retroarch.exe"))
        candidates += [
            os.path.join(programfiles, "RetroArch", "retroarch.exe"),
            os.path.join(programfiles_x86, "RetroArch", "retroarch.exe"),
            r"C:\RetroArch-Win64\retroarch.exe",
        ]

        for candidate in candidates:
            if os.path.isfile(candidate):
                return [candidate]
            print(f"[DesktopRetroarch] Not found: {candidate}")
        return None

    def _find_binary(self, name: str) -> list[str] | None:
        """Return [path] if `name` resolves to an executable via PATH."""
        # On Windows use where.exe explicitly — 'where' is a PowerShell alias
        # for Where-Object and will not resolve executables when spawned via
        # subprocess.
        cmd = "where.exe" if _CURRENT_OS == "windows" else "which"
        try:
            result = subprocess.run(
                [cmd, name], capture_output=True, text=True, check=False
            )
            path = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
            if path and os.path.isfile(path):
                return [path]
        except FileNotFoundError:
            pass
        return None

    def _find_flatpak(self) -> list[str] | None:
        """Return the Flatpak run command if org.libretro.Retroarch is installed."""
        try:
            result = subprocess.run(
                ["flatpak", "info", "org.libretro.Retroarch"],
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                return ["flatpak", "run", "org.libretro.Retroarch"]
        except FileNotFoundError:
            pass
        return None

    def _find_macos_app(self) -> list[str] | None:
        """Return the command for the RetroArch.app bundle if it exists."""
        app_path = "/Applications/RetroArch.app/Contents/MacOS/RetroArch"
        if os.path.isfile(app_path):
            return [app_path]
        return None

    # ------------------------------------------------------------------
    # Config discovery & parsing
    # ------------------------------------------------------------------

    def _find_config(self) -> str | None:
        """Return the path to retroarch.cfg for the current platform, or None."""
        candidates: list[str] = []

        if _CURRENT_OS == "linux":
            xdg_home = os.environ.get("XDG_CONFIG_HOME", "")
            if xdg_home:
                candidates.append(os.path.join(xdg_home, "retroarch", "retroarch.cfg"))
            candidates += [
                os.path.expanduser("~/.config/retroarch/retroarch.cfg"),
                "/etc/retroarch.cfg",
            ]

        elif _CURRENT_OS == "darwin":
            candidates += [
                os.path.expanduser(
                    "~/Library/Application Support/RetroArch/retroarch.cfg"
                ),
                os.path.expanduser("~/.config/retroarch/retroarch.cfg"),
            ]

        elif _CURRENT_OS == "windows":
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                candidates.append(
                    os.path.join(appdata, "RetroArch", "retroarch.cfg")
                )
            # Portable install: retroarch.cfg next to the exe
            if self.retroarch_command:
                exe_dir = os.path.dirname(self.retroarch_command[0])
                candidates.append(os.path.join(exe_dir, "retroarch.cfg"))

        for path in candidates:
            if os.path.isfile(path):
                return path
        return None

    def _parse_config(self, config_path: str) -> bool:
        """
        Read retroarch.cfg and populate self.core_path / self.saves_dir.
        Returns False if the cores directory cannot be determined.

        RetroArch portable installs (common on Windows) store paths relative to
        the executable directory using the prefix ':\\' or ':/' — e.g. ':\\cores'.
        These are resolved against the directory containing the retroarch binary.
        """
        exe_dir = (
            os.path.dirname(self.retroarch_command[0])
            if self.retroarch_command
            else ""
        )

        def _resolve(value: str) -> str:
            """Expand RetroArch portable-relative paths and home tildes."""
            value = value.strip().strip('"')
            # RetroArch portable prefix: starts with ':/' or ':\'
            if value.startswith(":/") or value.startswith(":\\"):
                return os.path.join(exe_dir, value[2:].lstrip("/\\")) if exe_dir else value
            return os.path.expanduser(value)

        try:
            with open(config_path, "r") as fh:
                lines = fh.readlines()

            config: dict[str, str] = {}
            for line in lines:
                if " = " in line:
                    key, _, val = line.partition(" = ")
                    config[key.strip()] = _resolve(val)

            if "libretro_directory" in config:
                value = config["libretro_directory"]
                if os.path.isdir(value):
                    self.core_path = value
                else:
                    print("[DesktopRetroarch] Cores directory not found:", value)

            if "savefile_directory" in config:
                base = config["savefile_directory"]
                sort_by_content = config.get("sort_savefiles_by_content_enable", "false")
                if os.path.isdir(base):
                    # Apply per-system subdirectory if configured
                    if sort_by_content == "true":
                        gba_subdir = os.path.join(base, "gba")
                        self.saves_dir = gba_subdir if os.path.isdir(gba_subdir) else base
                    else:
                        self.saves_dir = base
                else:
                    print(
                        "[DesktopRetroarch] Saves directory not found,"
                        " using Sinew default."
                    )
                    self.saves_dir = SAVES_DIR
            else:
                print("[DesktopRetroarch] savefile_directory not set in config.")

        except OSError as e:
            print(f"[DesktopRetroarch] Error reading config: {e}")
            return False

        if not self.core_path:
            print("[DesktopRetroarch] Cores directory missing.")
            return False

        return True

    # ------------------------------------------------------------------
    # Core discovery
    # ------------------------------------------------------------------

    def _find_core_file(self, preferred_core="auto") -> str | None:
        """
        Return the full path to the best available GBA core file.
        Priority: mgba > vbam > vba_next > gpsp.
        Core extension is platform-dependent: .so (Linux), .dylib (macOS), .dll (Windows).
        If preferred_core matches one of the found cores, that is used instead.
        """
        if not self.core_path:
            return None

        ext_map = {"linux": ".so", "darwin": ".dylib", "windows": ".dll"}
        core_ext = ext_map.get(_CURRENT_OS, ".so")

        priority = ["mgba", "vbam", "vba_next", "gpsp"]
        found: dict[str, str] = {}

        try:
            for fname in os.listdir(self.core_path):
                if not fname.lower().endswith(core_ext):
                    continue
                lower = fname.lower()
                for key in priority:
                    if key in lower and key not in found:
                        found[key] = os.path.join(self.core_path, fname)
        except OSError as e:
            print(f"[DesktopRetroarch] Error listing cores: {e}")
            return None

        if not found:
            return None

        if preferred_core != "auto" and preferred_core in found:
            return found[preferred_core]

        for key in priority:
            if key in found:
                return found[key]

        return None

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _update_sinew_cache(self, key, value):
        """Helper to update persistent settings only when changed."""
        if self.cache.get(key) != value:
            self.cache[key] = value
            save_sinew_settings(self.settings)
