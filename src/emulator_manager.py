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
        for provider in self.providers:
            if self.current_os in provider.supported_os:
                if provider.probe(self.distro_id):
                    self.active_provider = provider
                    print(f"[EmulatorManager] Initialized {type(provider).__name__}")
                    break

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
                if not self._exit_handled:
                    self._exit_handled = True
                    self.active_provider.on_exit()
                    controller_manager.resume()

            threading.Thread(target=wait_for_exit, daemon=True).start()

            return True
        except Exception as e:
            print(f"[EmulatorManager] Launch Error: {e}")
            controller_manager.resume()
            return False

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
