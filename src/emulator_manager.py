#!/usr/bin/env python3

"""
emulator_manager.py — Provider-based emulator dispatcher.

Routes ROM launches to whichever provider is available on the current platform.
Providers in the providers/ folder handle platform-specific launch logic
(e.g. providers/rocknix.py for ROCKNIX firmware, providers/integrated_mgba.py
for the built-in mGBA core).  New platforms can be supported by adding a
provider file.
"""

import os
import platform
import inspect
import subprocess
import threading
import time
import pygame
from abc import ABC, abstractmethod

from settings import load_sinew_settings

# --- Provider Interface ---

class EmulatorProvider(ABC):
    @property
    @abstractmethod
    def supported_os(self):
        """Return a list of OS name strings this provider supports (e.g. ['linux'])."""
        pass

    @abstractmethod
    def get_command(self, rom_path, core="auto"):
        """Return the shell command list used to launch the emulator for the given ROM path."""
        pass

    @abstractmethod
    def probe(self, distro_id):
        """Return True if this provider is available and active on the current system."""
        pass

    @abstractmethod
    def terminate(self, process):
        """Terminate the given emulator subprocess."""
        pass

    @abstractmethod
    def on_exit(self):
        """Called by the exit-watcher thread when the emulator process ends cleanly."""
        pass

# --- Import providers ---
from providers import *

# --- Main EmulatorManager Controller ---

class EmulatorManager:
    def __init__(self, use_external_providers=True):
        self.process = None
        self.active_provider = None
        self.is_running = False
        self.use_external_providers = use_external_providers
        self.current_os = platform.system().lower()
        self.distro_id = self._get_linux_distro() if self.current_os == "linux" else None

        # Load settings
        current_settings = load_sinew_settings()

        # Register Providers — when use_external_providers is False, skip
        # non-integrated providers so only the built-in mGBA fallback is used.
        # Sort so integrated providers (fallbacks) are always probed last.
        import providers
        self.providers = sorted(
            [
                cls(current_settings)
                for name, cls in inspect.getmembers(providers, inspect.isclass)
                if issubclass(cls, EmulatorProvider)
                and cls is not EmulatorProvider
                and getattr(cls, 'active', False)
                and (use_external_providers or getattr(cls, 'is_integrated', False))
            ],
            key=lambda p: (1 if getattr(p, 'is_integrated', False) else 0)
        )

        self._detect_environment()

    def _get_linux_distro(self):
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r") as f:
                distro_id = None
                os_name = None
                for line in f:
                    if line.startswith('ID='):
                        distro_id = line.split('=')[1].strip().replace('"', '').lower()
                    elif line.startswith('OS_NAME='):
                        os_name = line.split('=')[1].strip().replace('"', '').lower()
                return distro_id or os_name or "generic"
        return "generic"

    def _detect_environment(self):
        if not self.providers:
            print("[EmulatorManager] No providers registered (all have active = False).")
            return

        for provider in self.providers:
            name = type(provider).__name__
            if self.current_os not in provider.supported_os:
                print(
                    f"[EmulatorManager] Skipping {name}:"
                    f" supports {provider.supported_os}, current OS is '{self.current_os}'"
                )
                continue
            if provider.probe(self.distro_id):
                self.active_provider = provider
                print(f"[EmulatorManager] Initialized {name}")
                return
            print(f"[EmulatorManager] {name} probe failed.")

        print("[EmulatorManager] No provider matched this environment.")

    def launch(self, rom_path, controller_manager, core="auto", sav_path=None, game_screen=None):
        """Launch the emulator via the active provider; pauses input and returns True on success."""
        if not self.active_provider:
            print("[EmulatorManager] No provider found. Launch aborted.")
            return False

        # In-process provider (e.g. integrated mGBA) — delegate directly.
        if getattr(self.active_provider, 'is_integrated', False):
            try:
                self.active_provider.launch_integrated(rom_path, sav_path, game_screen)
                return True
            except Exception as e:
                print(f"[EmulatorManager] Integrated launch error: {e}")
                return False

        cmd = self.active_provider.get_command(rom_path, core)
        if not cmd:
            return False

        # Release the hardware
        controller_manager.pause()
        
        # Store whether we fully quit the display (needed for handheld reinit)
        display_was_quit = False
        
        # Smart display handling:
        # - ROCKNIX/JELOS/ArkOS (embedded): Must quit display to release GPU
        # - AYN Thor (full desktop Linux): Iconify for dual-screen support
        # - Desktop: Iconify to minimize
        try:
            from config import IS_HANDHELD
            
            # Detect if we're on embedded firmware
            # ROCKNIX uses Wayland but is still embedded (no full desktop)
            is_embedded_firmware = False
            if IS_HANDHELD:
                # Check 1: RetroPie (treat like embedded - needs display quit)
                if os.path.exists('/opt/retropie/supplementary/runcommand/runcommand.sh'):
                    is_embedded_firmware = True
                    print(f"[EmulatorManager] RetroPie detected - using embedded mode")
                # Check 2: ROCKNIX specifically (has ES but no full DE)
                elif os.path.exists('/usr/bin/emulationstation') and not os.path.exists('/usr/bin/gnome-shell'):
                    is_embedded_firmware = True
                    print(f"[EmulatorManager] Embedded CFW detected (EmulationStation without desktop)")
                # Check 3: Known CFW markers
                elif any(os.path.exists(p) for p in [
                    '/etc/rocknix', '/usr/share/rocknix', '/storage/.config/rocknix',
                    '/etc/jelos', '/etc/arkos', '/etc/batocera'
                ]):
                    is_embedded_firmware = True
                    print(f"[EmulatorManager] CFW detected via markers")
                # Check 4: KMSDRM/fbdev drivers
                elif os.environ.get('SDL_VIDEODRIVER', '').lower() in ('kmsdrm', 'directfb', 'fbcon'):
                    is_embedded_firmware = True
                    print(f"[EmulatorManager] KMSDRM/fbdev driver detected")
            
            if is_embedded_firmware:
                # Embedded CFW: quit display to release GPU
                pygame.display.quit()
                display_was_quit = True
                print("[EmulatorManager] Display quit for embedded handheld")
            else:
                # Full Linux or desktop: iconify
                pygame.display.iconify()
                print("[EmulatorManager] Display iconified")
        except Exception as e:
            print(f"[EmulatorManager] Display handling warning: {e}")
            # Safe fallback
            pygame.display.iconify()

        # Revert LD_LIBRARY_PATH for the system tools
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = env.get("LD_LIBRARY_PATH_ORIG", "/usr/lib:/lib")

        try:
            # Launch the external emulator
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True
            )
            self.is_running = True
            self._exit_handled = False

            # Automatically resume input when the process dies
            def wait_for_exit():
                self.process.wait()
                print("[EmulatorManager] Subprocess ended. Resuming Sinew controls...")
                self.is_running = False
                
                # Reinit display if we quit it for embedded handheld
                if display_was_quit:
                    try:
                        pygame.display.init()
                        print("[EmulatorManager] Display reinitialized")
                    except Exception as e:
                        print(f"[EmulatorManager] Display reinit error: {e}")
                
                if not self._exit_handled:
                    self._exit_handled = True
                    self.active_provider.on_exit()
                    controller_manager.resume()
                    self._restore_window()

            threading.Thread(target=wait_for_exit, daemon=True).start()

            return True
        except Exception as e:
            print(f"[EmulatorManager] Launch Error: {e}")
            controller_manager.resume()
            return False

    def _restore_window(self):
        """Restore and focus the Sinew window after the external emulator closes."""
        # Give the OS a moment to fully clean up the emulator window.
        time.sleep(0.3)
        if platform.system().lower() == "windows":
            try:
                import ctypes
                hwnd = pygame.display.get_wm_info().get("window")
                if hwnd:
                    SW_RESTORE = 9
                    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    print("[EmulatorManager] Window restored.")
            except Exception as e:
                print(f"[EmulatorManager] Window restore failed: {e}")
        else:
            # On Linux/macOS pygame.VIDEORESIZE or a display event will
            # bring the window back; posting VIDEOEXPOSE nudges a redraw.
            pygame.event.post(pygame.event.Event(pygame.VIDEOEXPOSE))

    def check_status(self):
        """Return True if the emulator subprocess is still running, False if it has exited."""
        if self.process is None:
            return False
        status = self.process.poll()
        if status is not None:
            print(f"[EmulatorManager] Process exited with code: {status}")
            self.process = None
            return False
        return True

    def terminate(self):
        """Terminate the currently active emulator process via the active provider."""
        if self.process and self.active_provider:
            print(f"[EmulatorManager] Delegating termination to {type(self.active_provider).__name__}")
            self._exit_handled = True
            self.active_provider.terminate(self.process)
            self.process = None
            self.is_running = False