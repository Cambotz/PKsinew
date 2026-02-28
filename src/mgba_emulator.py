#!/usr/bin/env python3

"""
mgba_emulator.py - mGBA libretro core wrapper for Sinew
Integrates GBA emulation into the Sinew Pokemon save manager
"""

import ctypes
import os
import platform
import threading
from collections import deque
from ctypes import (
    CFUNCTYPE,
    POINTER,
    byref,
    c_bool,
    c_char_p,
    c_int16,
    c_size_t,
    c_uint16,
    c_uint32,
    c_void_p,
    cast,
    create_string_buffer,
)

import numpy as np
import pygame

from config import (
    CORES_DIR, SAVES_DIR, SYSTEM_DIR, SETTINGS_FILE, ROMS_DIR, MGBA_CORE_PATH,
    AUDIO_BUFFER_DEFAULT, AUDIO_BUFFER_DEFAULT_ARM, AUDIO_QUEUE_DEPTH_DEFAULT,
    AUDIO_BUFFER_OPTIONS, AUDIO_QUEUE_OPTIONS,
    VOLUME_DEFAULT,
)


def _get_default_cores_dir():
    """Get the default cores directory (absolute path)."""
    return CORES_DIR


def _get_default_saves_dir():
    """Get the default saves directory (absolute path)."""
    return SAVES_DIR


def _get_default_system_dir():
    """Get the default system directory (absolute path)."""
    return SYSTEM_DIR


def get_platform_core_extension():
    """
    Get the correct libretro core file extension for the current platform.

    Returns:
        str: File extension ('.dll', '.so', or '.dylib')
    """
    system = platform.system().lower()
    if system == "windows":
        return ".dll"
    elif system == "linux":
        return ".so"
    elif system == "darwin":  # macOS
        return ".dylib"
    else:
        # Default to .so for unknown Unix-like systems
        return ".so"


def get_platform_info():
    """
    Get detailed platform and architecture information.

    Returns:
        tuple: (os_name, arch_name, extension)
            os_name: 'windows', 'linux', or 'macos'
            arch_name: 'x64', 'x86', 'arm64', or 'arm32'
            extension: '.dll', '.so', or '.dylib'
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Determine OS name
    if system == "windows":
        os_name = "windows"
        ext = ".dll"
    elif system == "darwin":
        os_name = "macos"
        ext = ".dylib"
    else:  # Linux and others
        os_name = "linux"
        ext = ".so"

    # Determine architecture
    if machine in ("amd64", "x86_64"):
        arch_name = "x64"
    elif machine in ("i386", "i686", "x86"):
        arch_name = "x86"
    elif machine in ("aarch64", "arm64"):
        arch_name = "arm64"
    elif machine in ("armv7l", "armv6l", "arm"):
        arch_name = "arm32"
    else:
        # Default fallback based on pointer size
        import struct

        if struct.calcsize("P") == 8:
            arch_name = "x64"
        else:
            arch_name = "x86"
        print(f"[MgbaEmulator] Unknown machine type '{machine}', assuming {arch_name}")

    return os_name, arch_name, ext


def is_linux_arm():
    """
    Return True when running on a Linux ARM device (arm32 or arm64).
    Used to select optimized audio buffer settings for low-power handhelds.
    """
    os_name, arch_name, _ = get_platform_info()
    return os_name == "linux" and arch_name in ("arm32", "arm64")


def get_audio_settings():
    """
    Return (buffer_size, max_queue_depth) tuned for the current platform,
    with optional user overrides from sinew_settings.json.

    Priority: user override > platform default.
    """
    import json

    # Platform defaults
    if is_linux_arm():
        default_buf = AUDIO_BUFFER_DEFAULT_ARM
    else:
        default_buf = AUDIO_BUFFER_DEFAULT
    default_depth = AUDIO_QUEUE_DEPTH_DEFAULT

    # Try loading user overrides
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            buf = data.get("mgba_audio_buffer", default_buf)
            depth = data.get("mgba_audio_queue_depth", default_depth)
            # Validate against allowed options
            if buf not in AUDIO_BUFFER_OPTIONS:
                buf = default_buf
            if depth not in AUDIO_QUEUE_OPTIONS:
                depth = default_depth
            return int(buf), int(depth)
    except Exception as e:
        print(f"[MgbaEmulator] Could not load audio settings override: {e}")

    return default_buf, default_depth


def get_audio_platform_defaults():
    """Return the platform defaults (ignoring user overrides) for fallback."""
    if is_linux_arm():
        return AUDIO_BUFFER_DEFAULT_ARM, AUDIO_QUEUE_DEPTH_DEFAULT
    return AUDIO_BUFFER_DEFAULT, AUDIO_QUEUE_DEPTH_DEFAULT


def get_core_filename():
    """
    Get the platform-specific core filename.

    Returns:
        str: Core filename (e.g., 'mgba_libretro_linux_arm64.so')
    """
    os_name, arch_name, ext = get_platform_info()
    return f"mgba_libretro_{os_name}_{arch_name}{ext}"


def get_default_core_path(cores_dir=None):
    """
    Get the default mGBA libretro core path for the current platform.

    Args:
        cores_dir: Directory containing core files (default: from config or "cores")

    Returns:
        str: Full path to the core file
    """
    if cores_dir is None:
        cores_dir = _get_default_cores_dir()
    elif not os.path.isabs(cores_dir):
        cores_dir = os.path.abspath(cores_dir)

    core_name = get_core_filename()
    return os.path.join(cores_dir, core_name)


def find_core_path(core_path=None, cores_dir=None):
    """
    Find the correct core path, handling cross-platform detection.

    Looks for cores named: mgba_libretro_{os}_{arch}.{ext}
    Examples:
        - mgba_libretro_windows_x64.dll
        - mgba_libretro_linux_arm64.so
        - mgba_libretro_macos_arm64.dylib

    Args:
        core_path: Explicit path to core file (optional)
        cores_dir: Directory to search for cores if core_path not provided

    Returns:
        str: Path to the core file

    Raises:
        FileNotFoundError: If no suitable core file is found
    """
    # Get absolute cores_dir
    if cores_dir is None:
        cores_dir = _get_default_cores_dir()
    elif not os.path.isabs(cores_dir):
        cores_dir = os.path.abspath(cores_dir)

    os_name, arch_name, ext = get_platform_info()
    expected_filename = get_core_filename()

    # If explicit path provided
    if core_path:
        # Check if the exact path exists
        if os.path.exists(core_path):
            return core_path

        # Maybe they provided a path with wrong extension for this OS
        # Try swapping the extension
        base_path = os.path.splitext(core_path)[0]
        platform_path = base_path + ext
        if os.path.exists(platform_path):
            print(f"[MgbaEmulator] Using platform-appropriate core: {platform_path}")
            return platform_path

        # Try in cores directory with just the filename
        filename = os.path.basename(core_path)
        base_filename = os.path.splitext(filename)[0]
        cores_path = os.path.join(cores_dir, base_filename + ext)
        if os.path.exists(cores_path):
            print(f"[MgbaEmulator] Found core in cores directory: {cores_path}")
            return cores_path

    # Auto-detect core in cores directory
    default_path = get_default_core_path(cores_dir)
    if os.path.exists(default_path):
        print(f"[MgbaEmulator] Auto-detected core: {default_path}")
        return default_path

    # Search for any mgba core matching our platform in the directory
    if os.path.isdir(cores_dir):
        # First, look for platform-specific core
        for filename in os.listdir(cores_dir):
            if filename.startswith("mgba") and filename.endswith(ext):
                # Check if it matches our OS
                if f"_{os_name}_" in filename:
                    found_path = os.path.join(cores_dir, filename)
                    print(f"[MgbaEmulator] Found alternative core: {found_path}")
                    return found_path

        # Fallback: any core with matching extension
        for filename in os.listdir(cores_dir):
            if filename.startswith("mgba") and filename.endswith(ext):
                found_path = os.path.join(cores_dir, filename)
                print(f"[MgbaEmulator] Found fallback core: {found_path}")
                return found_path

    # Nothing found - raise error with helpful message
    raise FileNotFoundError(
        f"mGBA libretro core not found.\n"
        f"Platform: {os_name} ({arch_name})\n"
        f"Expected: {expected_filename}\n"
        f"Looked in: {cores_dir}\n"
        f"Please download the correct core for your platform."
    )


# ---------------- LIBRETRO CONSTANTS ----------------
# Environment commands
RETRO_ENVIRONMENT_GET_CAN_DUPE = 3
RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY = 9
RETRO_ENVIRONMENT_SET_PIXEL_FORMAT = 10
RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS = 11
RETRO_ENVIRONMENT_GET_VARIABLE = 15
RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE = 17
RETRO_ENVIRONMENT_GET_LOG_INTERFACE = 27
RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY = 31
RETRO_ENVIRONMENT_SET_CONTROLLER_INFO = 35
RETRO_ENVIRONMENT_SET_MEMORY_MAPS = 36
RETRO_ENVIRONMENT_GET_LANGUAGE = 39
RETRO_ENVIRONMENT_GET_INPUT_BITMASKS = 52
RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION = 53
RETRO_ENVIRONMENT_SET_CORE_OPTIONS = 54
RETRO_ENVIRONMENT_SET_CORE_OPTIONS_INTL = 55
RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2 = 67
RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2_INTL = 68
RETRO_ENVIRONMENT_GET_MESSAGE_INTERFACE_VERSION = 59

# Pixel formats
RETRO_PIXEL_FORMAT_0RGB1555 = 0
RETRO_PIXEL_FORMAT_XRGB8888 = 1
RETRO_PIXEL_FORMAT_RGB565 = 2

# Joypad buttons (SNES-style layout)
RETRO_DEVICE_ID_JOYPAD_B = 0
RETRO_DEVICE_ID_JOYPAD_Y = 1
RETRO_DEVICE_ID_JOYPAD_SELECT = 2
RETRO_DEVICE_ID_JOYPAD_START = 3
RETRO_DEVICE_ID_JOYPAD_UP = 4
RETRO_DEVICE_ID_JOYPAD_DOWN = 5
RETRO_DEVICE_ID_JOYPAD_LEFT = 6
RETRO_DEVICE_ID_JOYPAD_RIGHT = 7
RETRO_DEVICE_ID_JOYPAD_A = 8
RETRO_DEVICE_ID_JOYPAD_X = 9
RETRO_DEVICE_ID_JOYPAD_L = 10
RETRO_DEVICE_ID_JOYPAD_R = 11

RETRO_DEVICE_JOYPAD = 1
RETRO_MEMORY_SAVE_RAM = 0


# ---------------- LIBRETRO STRUCTS ----------------
class retro_game_info(ctypes.Structure):
    _fields_ = [
        ("path", c_char_p),
        ("data", c_void_p),
        ("size", c_size_t),
        ("meta", c_char_p),
    ]


class retro_system_info(ctypes.Structure):
    _fields_ = [
        ("library_name", c_char_p),
        ("library_version", c_char_p),
        ("valid_extensions", c_char_p),
        ("need_fullpath", c_bool),
        ("block_extract", c_bool),
    ]


class retro_game_geometry(ctypes.Structure):
    _fields_ = [
        ("base_width", c_uint32),
        ("base_height", c_uint32),
        ("max_width", c_uint32),
        ("max_height", c_uint32),
        ("aspect_ratio", ctypes.c_float),
    ]


class retro_system_timing(ctypes.Structure):
    _fields_ = [
        ("fps", ctypes.c_double),
        ("sample_rate", ctypes.c_double),
    ]


class retro_system_av_info(ctypes.Structure):
    _fields_ = [
        ("geometry", retro_game_geometry),
        ("timing", retro_system_timing),
    ]


class retro_variable(ctypes.Structure):
    _fields_ = [
        ("key", c_char_p),
        ("value", c_char_p),
    ]


# Callback types
ENV_CB = CFUNCTYPE(c_bool, c_uint32, c_void_p)
VIDEO_CB = CFUNCTYPE(None, c_void_p, c_uint32, c_uint32, c_size_t)
AUDIO_SAMPLE_CB = CFUNCTYPE(None, c_int16, c_int16)
AUDIO_BATCH_CB = CFUNCTYPE(c_size_t, POINTER(c_int16), c_size_t)
POLL_CB = CFUNCTYPE(None)
STATE_CB = CFUNCTYPE(c_int16, c_uint32, c_uint32, c_uint32, c_uint32)


class MgbaEmulator:
    """
    mGBA libretro core wrapper for embedding GBA emulation in Sinew.

    Automatically detects the correct libretro core for the current platform:
    - Windows: mgba_libretro.dll
    - Linux: mgba_libretro.so
    - macOS: mgba_libretro.dylib

    Usage:
        # Auto-detect core (recommended)
        emu = MgbaEmulator()

        # Or specify explicitly
        emu = MgbaEmulator(core_path="cores/mgba_libretro.dll")

        emu.load_rom("roms/Emerald.gba", "saves/Emerald.sav")

        # In game loop:
        while running:
            if not emu.paused:
                emu.run_frame()

            surface = emu.get_surface()
            screen.blit(surface, (x, y))

            # Check for pause combo (Start + Select held)
            if emu.check_pause_combo():
                emu.toggle_pause()
    """

    # GBA native resolution
    WIDTH = 240
    HEIGHT = 160

    def __init__(self, core_path=None, save_dir=None, system_dir=None, cores_dir=None):
        """
        Initialize the emulator.

        Args:
            core_path: Path to mgba_libretro core file (auto-detected if None)
            save_dir: Directory for save files (default: from config)
            system_dir: Directory for BIOS files (default: from config)
            cores_dir: Directory containing libretro cores (default: from config)
        """
        # Force SDL to use stereo audio (2 channels)
        # This prevents pygame from defaulting to 8 channels on some systems
        os.environ.setdefault('SDL_AUDIO_CHANNELS', '2')
        
        # Use config defaults if not specified
        if cores_dir is None:
            cores_dir = _get_default_cores_dir()
        if save_dir is None:
            save_dir = _get_default_saves_dir()
        if system_dir is None:
            system_dir = _get_default_system_dir()

        # Auto-detect or validate core path based on platform
        self.core_path = find_core_path(core_path, cores_dir)
        self.save_dir = os.path.abspath(save_dir)
        self.system_dir = os.path.abspath(system_dir)

        # Log platform info
        os_name, arch_name, ext = get_platform_info()
        print(f"[MgbaEmulator] Platform: {os_name} {arch_name}")
        print(f"[MgbaEmulator] Expected core: {get_core_filename()}")
        print(f"[MgbaEmulator] Core path: {self.core_path}")

        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(self.system_dir, exist_ok=True)

        # Clean up any leftover temp ROM files from previous crashes
        try:
            from config import cleanup_temp_roms
            cleanup_temp_roms()
        except Exception as e:
            print(f"[MgbaEmulator] Initial temp cleanup failed: {e}")

        # State
        self.loaded = False
        self.paused = False
        self._fast_forward_multiplier = 1  # 1 = normal speed; 2-10 = fast-forward
        self.rom_path = None
        self.save_path = None
        self.sram_loaded_valid = False  # Track if we loaded a valid save

        # Framebuffer
        self.pixel_format = RETRO_PIXEL_FORMAT_RGB565
        self.framebuffer = np.zeros((self.HEIGHT, self.WIDTH, 3), dtype=np.uint8)
        self._raw_framebuf_size = self.HEIGHT * 1024 * 4
        self._raw_framebuf = (ctypes.c_uint8 * self._raw_framebuf_size)()
        self._raw_framebuf_ptr = ctypes.cast(self._raw_framebuf, c_void_p)
        self._frame_meta = {"width": 0, "height": 0, "pitch": 0}
        self._frame_ready = False

        # Audio — buffer and queue depth tuned per platform
        _audio_buf, _audio_queue_depth = get_audio_settings()
        self.audio_queue = deque(maxlen=_audio_queue_depth)
        self._audio_lock = threading.Lock()
        self._audio_channel = None
        self._audio_thread = None
        self._audio_running = False

        # Deferred audio setting changes (applied on next _init_audio / _reinit_audio,
        # NOT immediately — avoids killing Sinew's menu music mixer while paused).
        self._pending_audio_buffer = None
        self._pending_audio_queue_depth = None
        # Set to True if _init_audio / _reinit_audio had to fall back to defaults.
        # Settings UI can poll this to snap sliders back.
        self.audio_settings_reverted = False
        
        # DIAGNOSTIC: Periodic audio state logging
        self._last_audio_diagnostic_time = 0
        self._diagnostic_interval = 5.0  # seconds
        self._audio_batches_received = 0

        # Volume / mute — loaded from settings, applied to channel after init
        self._mgba_muted = False
        self._master_volume = VOLUME_DEFAULT  # 0-100
        self._load_volume_settings()

        # Input state
        self._key_state = None
        self._joystick = None
        self._start_held_frames = 0
        self._select_held_frames = 0
        self._pause_combo_frames = 30  # Hold for ~0.5 seconds

        # Controller button mapping (GBA button -> controller button index)
        # These map libretro button IDs to physical controller button indices
        self._gamepad_map = {
            RETRO_DEVICE_ID_JOYPAD_A: 0,
            RETRO_DEVICE_ID_JOYPAD_B: 1,
            RETRO_DEVICE_ID_JOYPAD_START: 7,
            RETRO_DEVICE_ID_JOYPAD_SELECT: 6,
            RETRO_DEVICE_ID_JOYPAD_L: 4,
            RETRO_DEVICE_ID_JOYPAD_R: 5,
        }

        # Load saved controller config
        self._load_controller_config()
        self._load_keyboard_config()

        # Load pause combo setting
        self._pause_combo_setting = self._load_pause_combo_setting()

        # Load fast-forward speed (applied when toggle is ON at launch)
        self._load_fast_forward_setting()

        # Keep callbacks alive
        self._keep_alive = []

        # Directory buffers (must stay alive)
        self._save_dir_buf = create_string_buffer(self.save_dir.encode("utf-8"))
        self._system_dir_buf = create_string_buffer(self.system_dir.encode("utf-8"))

        # Load the core
        self._load_core()

    def _load_controller_config(self):
        """Load saved controller configuration from sinew_settings.json.

        This is the USER OVERRIDE layer — it runs after _init_joystick() has
        already applied SDL_GAMECONTROLLERCONFIG or controller_profiles, so any
        mapping saved here by the user (via ButtonMapper) always wins.

        Loads both face button mappings and d-pad bindings (hat remaps,
        button-based dpad, axis-based dpad) so the emulator respects the
        same config as the Sinew UI.
        """
        import json

        config_file = SETTINGS_FILE

        # D-pad config: hat direction -> (axis, expected_value)
        # Default: standard hat convention
        self._dpad_hat_map = {
            RETRO_DEVICE_ID_JOYPAD_UP: ("y", 1),
            RETRO_DEVICE_ID_JOYPAD_DOWN: ("y", -1),
            RETRO_DEVICE_ID_JOYPAD_LEFT: ("x", -1),
            RETRO_DEVICE_ID_JOYPAD_RIGHT: ("x", 1),
        }
        # D-pad as buttons: retro_id -> controller button index (or None)
        self._dpad_button_map = {
            RETRO_DEVICE_ID_JOYPAD_UP: None,
            RETRO_DEVICE_ID_JOYPAD_DOWN: None,
            RETRO_DEVICE_ID_JOYPAD_LEFT: None,
            RETRO_DEVICE_ID_JOYPAD_RIGHT: None,
        }
        # D-pad axis pairs to check: list of (x_axis, y_axis)
        self._dpad_axis_pairs = [(0, 1)]

        try:
            if not os.path.exists(config_file):
                # No settings file yet — _init_joystick already applied the best
                # available mapping (SDL config or controller_profiles).
                # Re-apply profile so d-pad state is also initialised correctly.
                self._apply_profile_from_joystick()
                return

            with open(config_file, "r") as f:
                settings_data = json.load(f)

            if "controller_mapping" not in settings_data:
                # Settings exist but user hasn't saved a controller mapping yet.
                # Fall back to controller_profiles so d-pad is set up properly.
                self._apply_profile_from_joystick()
                return

            # --- User-saved mapping: overrides SDL config and profile ---
            saved_map = settings_data["controller_mapping"]

            # Map our button names to libretro IDs
            name_to_retro = {
                "A":      RETRO_DEVICE_ID_JOYPAD_A,
                "B":      RETRO_DEVICE_ID_JOYPAD_B,
                "L":      RETRO_DEVICE_ID_JOYPAD_L,
                "R":      RETRO_DEVICE_ID_JOYPAD_R,
                "START":  RETRO_DEVICE_ID_JOYPAD_START,
                "SELECT": RETRO_DEVICE_ID_JOYPAD_SELECT,
            }

            for btn_name, retro_id in name_to_retro.items():
                if btn_name in saved_map:
                    val = saved_map[btn_name]
                    # Get the first integer value from the list
                    if isinstance(val, list) and len(val) > 0:
                        if isinstance(val[0], int):
                            self._gamepad_map[retro_id] = val[0]
                    elif isinstance(val, int):
                        self._gamepad_map[retro_id] = val

            # Load d-pad bindings (structured dict format from ButtonMapper)
            dpad_name_to_retro = {
                "DPAD_UP":    RETRO_DEVICE_ID_JOYPAD_UP,
                "DPAD_DOWN":  RETRO_DEVICE_ID_JOYPAD_DOWN,
                "DPAD_LEFT":  RETRO_DEVICE_ID_JOYPAD_LEFT,
                "DPAD_RIGHT": RETRO_DEVICE_ID_JOYPAD_RIGHT,
            }

            has_dpad_bindings = False
            for dpad_key, retro_id in dpad_name_to_retro.items():
                binding = saved_map.get(dpad_key)
                if not isinstance(binding, dict):
                    continue

                has_dpad_bindings = True
                source = binding.get("source", "")

                if source == "hat":
                    axis  = binding.get("axis", "y")
                    value = binding.get("value", 0)
                    self._dpad_hat_map[retro_id] = (axis, value)

                elif source == "button":
                    btn_idx = binding.get("button")
                    if btn_idx is not None:
                        self._dpad_button_map[retro_id] = btn_idx
                        # Disable hat for this direction since it's button-based
                        self._dpad_hat_map[retro_id] = None

                elif source == "axis":
                    axis_idx  = binding.get("axis_index", 0)
                    direction = binding.get("direction", 0)
                    if not hasattr(self, "_dpad_axis_bindings"):
                        self._dpad_axis_bindings = {}
                    self._dpad_axis_bindings[retro_id] = (axis_idx, direction)
                    self._dpad_hat_map[retro_id] = None

            if has_dpad_bindings:
                print(f"[MgbaEmulator] Loaded d-pad bindings: hat={self._dpad_hat_map}")

            print(
                f"[MgbaEmulator] Loaded saved controller mapping: "
                f"START={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_START)}, "
                f"SELECT={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_SELECT)}, "
                f"A={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_A)}, "
                f"B={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_B)}"
            )
        except Exception as e:
            print(f"[MgbaEmulator] Error loading controller config: {e}")

    def refresh_controller_config(self):
        """Reload controller configuration (call after button mapping changes)."""
        self._load_controller_config()
        self._load_keyboard_config()

    def _load_keyboard_config(self):
        """Load keyboard-to-GBA button map from sinew_settings.json.

        Stored under the key 'keyboard_emulator_map' as a dict mapping
        button names ('A','B','UP','DOWN','LEFT','RIGHT','L','R','START','SELECT')
        to pygame key constants (integers).  Supports a list of keys per button
        for multi-key bindings.

        Also loads the MENU key from keyboard_nav_map for pause/menu functionality.

        Falls back to built-in defaults for any missing entries.
        """
        import json

        # Built-in defaults
        DEFAULT_KB = {
            RETRO_DEVICE_ID_JOYPAD_A: [pygame.K_z],
            RETRO_DEVICE_ID_JOYPAD_B: [pygame.K_x],
            RETRO_DEVICE_ID_JOYPAD_SELECT: [pygame.K_BACKSPACE],
            RETRO_DEVICE_ID_JOYPAD_START: [pygame.K_RETURN],
            RETRO_DEVICE_ID_JOYPAD_UP: [pygame.K_UP, pygame.K_w],
            RETRO_DEVICE_ID_JOYPAD_DOWN: [pygame.K_DOWN, pygame.K_s],
            RETRO_DEVICE_ID_JOYPAD_LEFT: [pygame.K_LEFT, pygame.K_a],
            RETRO_DEVICE_ID_JOYPAD_RIGHT: [pygame.K_RIGHT, pygame.K_d],
            RETRO_DEVICE_ID_JOYPAD_L: [pygame.K_q],
            RETRO_DEVICE_ID_JOYPAD_R: [pygame.K_e],
        }

        # Button name -> retro ID mapping for settings lookup
        NAME_TO_RETRO = {
            "A": RETRO_DEVICE_ID_JOYPAD_A,
            "B": RETRO_DEVICE_ID_JOYPAD_B,
            "SELECT": RETRO_DEVICE_ID_JOYPAD_SELECT,
            "START": RETRO_DEVICE_ID_JOYPAD_START,
            "UP": RETRO_DEVICE_ID_JOYPAD_UP,
            "DOWN": RETRO_DEVICE_ID_JOYPAD_DOWN,
            "LEFT": RETRO_DEVICE_ID_JOYPAD_LEFT,
            "RIGHT": RETRO_DEVICE_ID_JOYPAD_RIGHT,
            "L": RETRO_DEVICE_ID_JOYPAD_L,
            "R": RETRO_DEVICE_ID_JOYPAD_R,
        }

        # Start from defaults
        self._kb_map = dict(DEFAULT_KB)
        
        # Default MENU key
        self._menu_keys = [pygame.K_m]

        config_file = SETTINGS_FILE

        try:
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    settings_data = json.load(f)

                # Load emulator keyboard map
                saved = settings_data.get("keyboard_emulator_map", {})
                for btn_name, retro_id in NAME_TO_RETRO.items():
                    if btn_name in saved:
                        val = saved[btn_name]
                        if isinstance(val, list):
                            self._kb_map[retro_id] = [
                                v for v in val if isinstance(v, int)
                            ]
                        elif isinstance(val, int):
                            self._kb_map[retro_id] = [val]

                if saved:
                    print(f"[MgbaEmulator] Loaded keyboard map from {config_file}")
                
                # Load MENU key from navigation map
                nav_map = settings_data.get("keyboard_nav_map", {})
                if "MENU" in nav_map:
                    val = nav_map["MENU"]
                    if isinstance(val, list):
                        self._menu_keys = [v for v in val if isinstance(v, int)]
                    elif isinstance(val, int):
                        self._menu_keys = [val]
                    print(f"[MgbaEmulator] Loaded MENU key(s): {self._menu_keys}")
        except Exception as e:
            print(f"[MgbaEmulator] Error loading keyboard config: {e}")

    def reload_keyboard_config(self):
        """Reload keyboard map (call after user changes key bindings)."""
        self._load_keyboard_config()

    def _load_core(self):
        """Load and initialize the libretro core."""
        if not os.path.exists(self.core_path):
            raise FileNotFoundError(f"Core not found: {self.core_path}")

        self.lib = ctypes.CDLL(self.core_path)

        # Set up function signatures
        self.lib.retro_get_memory_data.argtypes = [c_uint32]
        self.lib.retro_get_memory_data.restype = c_void_p
        self.lib.retro_get_memory_size.argtypes = [c_uint32]
        self.lib.retro_get_memory_size.restype = c_size_t
        self.lib.retro_reset.argtypes = []
        self.lib.retro_reset.restype = None
        self.lib.retro_get_system_info.argtypes = [POINTER(retro_system_info)]
        self.lib.retro_get_system_info.restype = None
        self.lib.retro_get_system_av_info.argtypes = [POINTER(retro_system_av_info)]
        self.lib.retro_get_system_av_info.restype = None

        # Create callbacks
        self._create_callbacks()

        # Register callbacks
        self.lib.retro_set_environment(self._cb_env)
        self.lib.retro_set_video_refresh(self._cb_video)
        self.lib.retro_set_audio_sample(self._cb_audio_sample)
        self.lib.retro_set_audio_sample_batch(self._cb_audio_batch)
        self.lib.retro_set_input_poll(self._cb_poll)
        self.lib.retro_set_input_state(self._cb_state)

        # Initialize core
        self.lib.retro_init()

        # Get system info
        sys_info = retro_system_info()
        self.lib.retro_get_system_info(byref(sys_info))
        self.core_name = sys_info.library_name.decode()
        self.core_version = sys_info.library_version.decode()
        print(f"[MgbaEmulator] Loaded {self.core_name} v{self.core_version}")

    def _create_callbacks(self):
        """Create and store libretro callbacks."""

        # Environment callback
        def environment(cmd, data):
            return self._handle_environment(cmd, data)

        self._cb_env = ENV_CB(environment)
        self._keep_alive.append(self._cb_env)

        # Video callback
        def video_refresh(data_ptr, width, height, pitch):
            if not data_ptr:
                return
            try:
                bytes_to_copy = min(int(height * pitch), self._raw_framebuf_size)
                ctypes.memmove(self._raw_framebuf_ptr, data_ptr, bytes_to_copy)
                self._frame_meta["width"] = int(width)
                self._frame_meta["height"] = int(height)
                self._frame_meta["pitch"] = int(pitch)
                self._frame_ready = True
            except Exception as e:
                print(f"[MgbaEmulator] Video error: {e}")

        self._cb_video = VIDEO_CB(video_refresh)
        self._keep_alive.append(self._cb_video)

        # Audio callbacks
        def audio_sample(left, right):
            pass

        self._cb_audio_sample = AUDIO_SAMPLE_CB(audio_sample)
        self._keep_alive.append(self._cb_audio_sample)

        # Track if we've logged the first batch
        _audio_batch_count = [0]
        
        def audio_batch(ptr, frames):
            try:
                frames = int(frames)
                if frames == 0:
                    return 0
                arr = np.ctypeslib.as_array(ptr, shape=(frames * 2,)).copy()
                arr = arr.reshape(-1, 2)
                
                # DIAGNOSTIC: Log first audio batch from mGBA core
                if _audio_batch_count[0] == 0:
                    print(f"[MgbaEmulator] ╔══════════════════════════════════════════════════════")
                    print(f"[MgbaEmulator] ║ FIRST AUDIO BATCH FROM mGBA CORE")
                    print(f"[MgbaEmulator] ╠══════════════════════════════════════════════════════")
                    print(f"[MgbaEmulator] ║ Frames received:  {frames}")
                    print(f"[MgbaEmulator] ║ Array shape:      {arr.shape}")
                    print(f"[MgbaEmulator] ║ Array dtype:      {arr.dtype}")
                    print(f"[MgbaEmulator] ║ Sample range:     [{arr.min()}, {arr.max()}]")
                    print(f"[MgbaEmulator] ║ Queue size:       {len(self.audio_queue)}/{self.audio_queue.maxlen}")
                    print(f"[MgbaEmulator] ║ mGBA is generating audio ✅")
                    print(f"[MgbaEmulator] ╚══════════════════════════════════════════════════════")
                
                _audio_batch_count[0] += 1
                self._audio_batches_received += 1
                
                with self._audio_lock:
                    self.audio_queue.append(arr)
                return frames
            except Exception as e:
                print(f"[MgbaEmulator] ╔══════════════════════════════════════════════════════")
                print(f"[MgbaEmulator] ║ AUDIO BATCH CALLBACK ERROR")
                print(f"[MgbaEmulator] ╠══════════════════════════════════════════════════════")
                print(f"[MgbaEmulator] ║ Error: {e}")
                print(f"[MgbaEmulator] ║ Frames: {frames}")
                print(f"[MgbaEmulator] ╚══════════════════════════════════════════════════════")
                import traceback
                traceback.print_exc()
                return 0

        self._cb_audio_batch = AUDIO_BATCH_CB(audio_batch)
        self._keep_alive.append(self._cb_audio_batch)

        # Input callbacks
        def input_poll():
            pygame.event.pump()
            self._key_state = pygame.key.get_pressed()

        self._cb_poll = POLL_CB(input_poll)
        self._keep_alive.append(self._cb_poll)

        def input_state(port, device, index, button_id):
            return self._handle_input(port, device, index, button_id)

        self._cb_state = STATE_CB(input_state)
        self._keep_alive.append(self._cb_state)

    def _handle_environment(self, cmd, data):
        """Handle libretro environment callbacks."""

        if cmd == RETRO_ENVIRONMENT_GET_CAN_DUPE:
            if data:
                cast(data, POINTER(c_bool))[0] = True
            return True

        if cmd == RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
            if data:
                cast(data, POINTER(c_char_p))[0] = ctypes.addressof(
                    self._system_dir_buf
                )
            return True

        if cmd == RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
            if data:
                self.pixel_format = cast(data, POINTER(c_uint32))[0]
            return True

        if cmd == RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:
            return True

        if cmd == RETRO_ENVIRONMENT_GET_VARIABLE:
            return False

        if cmd == RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
            if data:
                cast(data, POINTER(c_bool))[0] = False
            return True

        if cmd == RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
            if data:
                cast(data, POINTER(c_char_p))[0] = ctypes.addressof(self._save_dir_buf)
            return True

        if cmd == RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
            return False

        if cmd == RETRO_ENVIRONMENT_SET_CONTROLLER_INFO:
            return True

        if cmd == RETRO_ENVIRONMENT_GET_LANGUAGE:
            if data:
                cast(data, POINTER(c_uint32))[0] = 0
            return True

        if cmd == RETRO_ENVIRONMENT_GET_INPUT_BITMASKS:
            return False

        if cmd == RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION:
            if data:
                cast(data, POINTER(c_uint32))[0] = 0
            return True

        if cmd in (
            RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2,
            RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2_INTL,
            RETRO_ENVIRONMENT_SET_CORE_OPTIONS,
            RETRO_ENVIRONMENT_SET_CORE_OPTIONS_INTL,
        ):
            return True

        if cmd == RETRO_ENVIRONMENT_GET_MESSAGE_INTERFACE_VERSION:
            if data:
                cast(data, POINTER(c_uint32))[0] = 0
            return True

        if cmd == RETRO_ENVIRONMENT_SET_MEMORY_MAPS:
            return True

        return False

    def _handle_input(self, port, device, index, button_id):
        """Handle input state queries from the core."""
        if port != 0 or device != RETRO_DEVICE_JOYPAD:
            return 0

        if self._key_state is None:
            return 0

        # Use the loaded keyboard map (populated in _load_keyboard_config).
        # Falls back to built-in defaults if not yet loaded.
        kb_map = getattr(self, "_kb_map", None) or {
            RETRO_DEVICE_ID_JOYPAD_A: pygame.K_z,
            RETRO_DEVICE_ID_JOYPAD_B: pygame.K_x,
            RETRO_DEVICE_ID_JOYPAD_SELECT: pygame.K_BACKSPACE,
            RETRO_DEVICE_ID_JOYPAD_START: pygame.K_RETURN,
            RETRO_DEVICE_ID_JOYPAD_UP: pygame.K_UP,
            RETRO_DEVICE_ID_JOYPAD_DOWN: pygame.K_DOWN,
            RETRO_DEVICE_ID_JOYPAD_LEFT: pygame.K_LEFT,
            RETRO_DEVICE_ID_JOYPAD_RIGHT: pygame.K_RIGHT,
            RETRO_DEVICE_ID_JOYPAD_L: pygame.K_a,
            RETRO_DEVICE_ID_JOYPAD_R: pygame.K_s,
        }

        # Support multiple keys per button (list) or a single key (int)
        if button_id in kb_map:
            mapped = kb_map[button_id]
            keys_to_check = mapped if isinstance(mapped, list) else [mapped]
            for k in keys_to_check:
                if self._key_state[k]:
                    return 1

        # Check gamepad
        if self._joystick:
            try:
                # D-pad via hat (using configured hat map)
                if self._joystick.get_numhats() > 0:
                    hx, hy = self._joystick.get_hat(0)
                    hat_config = self._dpad_hat_map.get(button_id)
                    if hat_config is not None:
                        axis, expected_value = hat_config
                        if axis == "x" and hx == expected_value:
                            return 1
                        elif axis == "y" and hy == expected_value:
                            return 1

                # D-pad via buttons (for controllers with button-based dpads)
                dpad_btn = self._dpad_button_map.get(button_id)
                if dpad_btn is not None:
                    num_buttons = self._joystick.get_numbuttons()
                    if dpad_btn < num_buttons and self._joystick.get_button(dpad_btn):
                        return 1

                # D-pad via specific axis bindings (from remapping)
                axis_bindings = getattr(self, "_dpad_axis_bindings", {})
                axis_binding = axis_bindings.get(button_id)
                if axis_binding is not None:
                    axis_idx, expected_dir = axis_binding
                    if axis_idx < self._joystick.get_numaxes():
                        val = self._joystick.get_axis(axis_idx)
                        if expected_dir > 0 and val > 0.5:
                            return 1
                        elif expected_dir < 0 and val < -0.5:
                            return 1

                # Face/shoulder buttons - use configured mapping
                num_buttons = self._joystick.get_numbuttons()

                if button_id in self._gamepad_map:
                    btn = self._gamepad_map[button_id]
                    if btn < num_buttons and self._joystick.get_button(btn):
                        return 1

                # Analog stick (always axes 0,1 for left stick navigation)
                if self._joystick.get_numaxes() >= 2:
                    lx = self._joystick.get_axis(0)
                    ly = self._joystick.get_axis(1)
                    deadzone = 0.5

                    if button_id == RETRO_DEVICE_ID_JOYPAD_LEFT and lx < -deadzone:
                        return 1
                    if button_id == RETRO_DEVICE_ID_JOYPAD_RIGHT and lx > deadzone:
                        return 1
                    if button_id == RETRO_DEVICE_ID_JOYPAD_UP and ly < -deadzone:
                        return 1
                    if button_id == RETRO_DEVICE_ID_JOYPAD_DOWN and ly > deadzone:
                        return 1
            except Exception:
                pass

        return 0

    def load_rom(self, rom_path, save_path=None):
        """
        Load a ROM file. Supports both .gba and .zip files.

        Args:
            rom_path: Path to the GBA ROM (.gba or .zip)
            save_path: Optional path to save file (auto-derived if not provided)
        """
        if not os.path.exists(rom_path):
            raise FileNotFoundError(f"ROM not found: {rom_path}")

        # Store original path for display purposes
        self.rom_path = os.path.abspath(rom_path)
        
        # Handle .zip files - extract to temp
        actual_rom_path = self.rom_path
        if rom_path.lower().endswith('.zip'):
            from config import extract_zip_to_temp
            actual_rom_path = extract_zip_to_temp(rom_path)
            if actual_rom_path is None:
                raise RuntimeError(f"Failed to extract ROM from zip: {rom_path}")
            print(f"[MgbaEmulator] Using extracted ROM: {actual_rom_path}")

        # Derive save path from ORIGINAL filename (not extracted temp name)
        if save_path:
            self.save_path = os.path.abspath(save_path)
        else:
            rom_basename = os.path.splitext(os.path.basename(rom_path))[0]
            self.save_path = os.path.join(self.save_dir, f"{rom_basename}.sav")

        # Load the ROM using the actual (extracted or direct) path
        game = retro_game_info(
            path=actual_rom_path.encode("utf-8"), data=None, size=0, meta=None
        )

        if not self.lib.retro_load_game(byref(game)):
            raise RuntimeError(f"Failed to load ROM: {rom_path}")

        # Get AV info
        av_info = retro_system_av_info()
        self.lib.retro_get_system_av_info(byref(av_info))
        self.fps = av_info.timing.fps
        
        # mGBA libretro core reports sample rate as 65536, but actual GBA audio
        # output is 32768 Hz. Using the reported rate causes audio issues.
        # Force to correct GBA sample rate regardless of what core reports.
        self.sample_rate = 32768
        
        reported_rate = int(av_info.timing.sample_rate)
        print(f"[MgbaEmulator] Loaded: {os.path.basename(rom_path)}")
        print(f"[MgbaEmulator] FPS: {self.fps:.2f}, Sample rate: {self.sample_rate} (core reported: {reported_rate})")

        # Load SRAM
        self._load_sram()

        # Initialize audio
        self._init_audio()

        # Initialize joystick
        self._init_joystick()

        self.loaded = True

    def _init_joystick(self):
        """Initialize joystick and resolve button mapping.

        Priority (highest to lowest):
          1. SDL_GAMECONTROLLERCONFIG env var — set by PortMaster's control.txt /
             get_controls for the exact device we're running on.  Most accurate.
          2. controller_profiles database — our hand-curated + GameControllerDB
             fallback for non-PortMaster launches (desktop, direct run, etc.).
          3. Hardcoded defaults in _gamepad_map — last resort.

        Saved user overrides in sinew_settings.json (controller_mapping) are
        applied afterwards by _load_controller_config(), which runs at the end
        of __init__ and again on every resume(), so they always win.
        """
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            return

        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()
        print(f"[MgbaEmulator] Controller: {self._joystick.get_name()}")

        # --- Priority 1: PortMaster SDL_GAMECONTROLLERCONFIG ---
        sdl_config = os.environ.get("SDL_GAMECONTROLLERCONFIG", "").strip()
        if sdl_config:
            applied = self._apply_sdl_controller_config(sdl_config)
            if applied:
                return  # SDL config is authoritative — skip profile lookup

        # --- Priority 2: controller_profiles database ---
        self._apply_profile_from_joystick()

    def _apply_sdl_controller_config(self, config_string):
        """Parse SDL_GAMECONTROLLERCONFIG and apply button indices to _gamepad_map.

        PortMaster sources control.txt and calls get_controls which populates
        $sdl_controllerconfig with the correct SDL2 mapping for this specific
        device.  We parse it here so the emulator uses the same indices SDL2
        would use, without needing to switch to the GameController API.

        SDL format (one or more newline-separated lines):
            GUID,Name,a:b0,b:b1,back:b8,start:b9,leftshoulder:b4,...

        Returns True if at least one button was successfully mapped.
        """
        # SDL logical name -> libretro button ID
        sdl_to_retro = {
            "a":             RETRO_DEVICE_ID_JOYPAD_A,
            "b":             RETRO_DEVICE_ID_JOYPAD_B,
            "x":             RETRO_DEVICE_ID_JOYPAD_X,
            "y":             RETRO_DEVICE_ID_JOYPAD_Y,
            "start":         RETRO_DEVICE_ID_JOYPAD_START,
            "back":          RETRO_DEVICE_ID_JOYPAD_SELECT,   # SDL calls Select "back"
            "leftshoulder":  RETRO_DEVICE_ID_JOYPAD_L,
            "rightshoulder": RETRO_DEVICE_ID_JOYPAD_R,
        }

        # SDL d-pad logical names -> libretro direction IDs
        sdl_dpad_to_retro = {
            "dpup":    RETRO_DEVICE_ID_JOYPAD_UP,
            "dpdown":  RETRO_DEVICE_ID_JOYPAD_DOWN,
            "dpleft":  RETRO_DEVICE_ID_JOYPAD_LEFT,
            "dpright": RETRO_DEVICE_ID_JOYPAD_RIGHT,
        }

        our_name = self._joystick.get_name().lower()
        best_entry = None

        # Find the best matching entry for our controller
        lines = [l.strip() for l in config_string.splitlines()
                 if l.strip() and not l.strip().startswith("#")]

        for line in lines:
            parts = line.split(",", 2)
            if len(parts) < 3:
                continue
            entry_name = parts[1].lower()
            if entry_name in our_name or our_name in entry_name:
                best_entry = line
                break

        # If no name match, use the only entry (common case — one mapping per device)
        if best_entry is None and len(lines) == 1:
            best_entry = lines[0]

        if best_entry is None:
            print("[MgbaEmulator] SDL_GAMECONTROLLERCONFIG set but no matching entry found")
            return False

        mapped_count = 0
        parts = best_entry.split(",")

        for part in parts[2:]:  # skip GUID and name fields
            part = part.strip()
            if ":" not in part:
                continue
            key, val = part.split(":", 1)
            key = key.strip()
            val = val.strip().rstrip(",")

            # --- Face / shoulder / start / select buttons ---
            if key in sdl_to_retro and val.startswith("b"):
                try:
                    btn_idx = int(val[1:])
                    self._gamepad_map[sdl_to_retro[key]] = btn_idx
                    mapped_count += 1
                except ValueError:
                    pass

            # --- D-pad: button-based (e.g. dpup:b11) ---
            elif key in sdl_dpad_to_retro and val.startswith("b"):
                try:
                    btn_idx = int(val[1:])
                    retro_id = sdl_dpad_to_retro[key]
                    self._dpad_button_map[retro_id] = btn_idx
                    self._dpad_hat_map[retro_id] = None   # disable hat for this dir
                    mapped_count += 1
                except ValueError:
                    pass

            # --- D-pad: hat-based (e.g. dpup:h0.1) ---
            elif key in sdl_dpad_to_retro and val.startswith("h"):
                try:
                    # h<hat>.<mask>  e.g. h0.1=up, h0.4=down, h0.8=left, h0.2=right
                    hat_part = val[1:]
                    _hat_idx, mask_str = hat_part.split(".")
                    mask = int(mask_str)
                    retro_id = sdl_dpad_to_retro[key]
                    # Convert hat mask to our (axis, value) convention
                    hat_conv = {1: ("y", 1), 4: ("y", -1), 8: ("x", -1), 2: ("x", 1)}
                    if mask in hat_conv:
                        self._dpad_hat_map[retro_id] = hat_conv[mask]
                        mapped_count += 1
                except (ValueError, KeyError):
                    pass

            # --- D-pad: axis-based (e.g. dpup:-a1, dpdown:+a1) ---
            elif key in sdl_dpad_to_retro and ("a" in val):
                try:
                    sign = -1 if val.startswith("-") else 1
                    axis_str = val.lstrip("+-").lstrip("a")
                    axis_idx = int(axis_str)
                    retro_id = sdl_dpad_to_retro[key]
                    if not hasattr(self, "_dpad_axis_bindings"):
                        self._dpad_axis_bindings = {}
                    self._dpad_axis_bindings[retro_id] = (axis_idx, sign)
                    self._dpad_hat_map[retro_id] = None
                    mapped_count += 1
                except ValueError:
                    pass

        if mapped_count > 0:
            print(
                f"[MgbaEmulator] SDL_GAMECONTROLLERCONFIG applied ({mapped_count} bindings): "
                f"START={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_START)}, "
                f"SELECT={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_SELECT)}, "
                f"A={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_A)}, "
                f"B={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_B)}"
            )
        return mapped_count > 0

    def _apply_profile_from_joystick(self):
        """Resolve button mapping from controller_profiles when SDL config is absent.

        This covers non-PortMaster launches: desktop testing, direct execution,
        Windows/macOS builds.  Uses the same controller_profiles.resolve_mapping()
        logic as the Sinew UI controller so they stay in sync.
        """
        if not self._joystick:
            return

        try:
            from controller_profiles import resolve_mapping
        except ImportError:
            print("[MgbaEmulator] controller_profiles not available, using defaults")
            return

        name = self._joystick.get_name()
        guid = None
        try:
            guid = self._joystick.get_guid()
        except (AttributeError, Exception):
            pass

        num_buttons = self._joystick.get_numbuttons()
        num_axes    = self._joystick.get_numaxes()
        num_hats    = self._joystick.get_numhats()

        result  = resolve_mapping(name, guid, num_buttons, num_axes, num_hats)
        mapping = result.get("mapping", {})

        name_to_retro = {
            "A":      RETRO_DEVICE_ID_JOYPAD_A,
            "B":      RETRO_DEVICE_ID_JOYPAD_B,
            "X":      RETRO_DEVICE_ID_JOYPAD_X,
            "Y":      RETRO_DEVICE_ID_JOYPAD_Y,
            "L":      RETRO_DEVICE_ID_JOYPAD_L,
            "R":      RETRO_DEVICE_ID_JOYPAD_R,
            "START":  RETRO_DEVICE_ID_JOYPAD_START,
            "SELECT": RETRO_DEVICE_ID_JOYPAD_SELECT,
        }

        mapped_count = 0
        for btn_name, retro_id in name_to_retro.items():
            if btn_name in mapping:
                val = mapping[btn_name]
                idx = val[0] if isinstance(val, list) else val
                if isinstance(idx, int):
                    self._gamepad_map[retro_id] = idx
                    mapped_count += 1

        # Apply d-pad config from profile if present
        dpad_buttons = mapping.get("_dpad_buttons")
        if dpad_buttons and isinstance(dpad_buttons, dict):
            dir_to_retro = {
                "up":    RETRO_DEVICE_ID_JOYPAD_UP,
                "down":  RETRO_DEVICE_ID_JOYPAD_DOWN,
                "left":  RETRO_DEVICE_ID_JOYPAD_LEFT,
                "right": RETRO_DEVICE_ID_JOYPAD_RIGHT,
            }
            for direction, retro_id in dir_to_retro.items():
                if direction in dpad_buttons:
                    val = dpad_buttons[direction]
                    idx = val[0] if isinstance(val, list) else val
                    if isinstance(idx, int):
                        self._dpad_button_map[retro_id] = idx
                        self._dpad_hat_map[retro_id] = None

        dpad_axes = mapping.get("_dpad_axes")
        if dpad_axes and isinstance(dpad_axes, list):
            self._dpad_axis_pairs = [
                (pair[0], pair[1])
                for pair in dpad_axes
                if isinstance(pair, (list, tuple)) and len(pair) == 2
            ]

        print(
            f"[MgbaEmulator] Profile '{result['description']}' ({result['match_type']}): "
            f"START={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_START)}, "
            f"SELECT={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_SELECT)}, "
            f"A={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_A)}, "
            f"B={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_B)}"
        )

    def _init_audio(self):
        """Initialize audio playback."""
        try:
            # Stop any existing audio thread first
            self._audio_running = False
            if self._audio_thread and self._audio_thread.is_alive():
                try:
                    self._audio_thread.join(timeout=0.5)
                except Exception:
                    pass
            self._audio_thread = None

            # Clear audio queue
            with self._audio_lock:
                self.audio_queue.clear()

            # Quit existing mixer if running
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
                    pygame.time.wait(50)  # Small delay to let audio system settle
            except Exception:
                pass

            # Consume any pending settings from the Settings UI, else use saved/defaults
            audio_buffer, audio_queue_depth = self._consume_pending_audio_settings()

            # Resize the deque to the (possibly new) queue depth
            old_items = list(self.audio_queue)
            self.audio_queue = deque(old_items, maxlen=audio_queue_depth)

            print(
                f"[MgbaEmulator] Audio init: buffer={audio_buffer}, "
                f"queue_depth={audio_queue_depth} "
                f"(platform: {'linux_arm' if is_linux_arm() else 'default'})"
            )

            # Try to initialize mixer with multiple attempts
            max_attempts = 3
            init_ok = False
            for attempt in range(max_attempts):
                try:
                    # Simple, direct mixer init - let SDL handle the details
                    pygame.mixer.init(
                        frequency=self.sample_rate,
                        size=-16,
                        channels=2,  # STEREO - critical for emulator audio
                        buffer=audio_buffer,
                    )

                    # Verify it actually initialized
                    init_info = pygame.mixer.get_init()
                    if init_info:
                        print(f"[MgbaEmulator] Mixer initialized: {init_info}")
                        
                        # DIAGNOSTIC: Log detailed audio state
                        freq, fmt, ch = init_info
                        print(f"[MgbaEmulator] ╔══════════════════════════════════════════════════════")
                        print(f"[MgbaEmulator] ║ AUDIO DIAGNOSTICS")
                        print(f"[MgbaEmulator] ╠══════════════════════════════════════════════════════")
                        print(f"[MgbaEmulator] ║ Mixer Frequency:  {freq} Hz {'✅ CORRECT' if freq == 32768 else '❌ WRONG (should be 32768)'}")
                        print(f"[MgbaEmulator] ║ Sample Format:    {fmt} {'✅' if fmt == -16 else '❌'}")
                        print(f"[MgbaEmulator] ║ Audio Channels:   {ch} {'✅ STEREO' if ch == 2 else '❌ WRONG (should be 2 for stereo)'}")
                        print(f"[MgbaEmulator] ║ Buffer Size:      {audio_buffer} samples")
                        print(f"[MgbaEmulator] ║ Queue Depth:      {audio_queue_depth} chunks")
                        print(f"[MgbaEmulator] ║ SDL Audio Driver: {os.environ.get('SDL_AUDIODRIVER', 'auto')}")
                        
                        # Check if pygame can actually play sounds
                        try:
                            num_channels = pygame.mixer.get_num_channels()
                            print(f"[MgbaEmulator] ║ Mixer Channels:   {num_channels} available")
                        except:
                            pass
                        
                        # Log platform audio info
                        import platform
                        print(f"[MgbaEmulator] ║ OS:               {platform.system()} {platform.release()}")
                        
                        # Try to detect if system audio is working
                        try:
                            import ctypes
                            # Check if master volume is accessible (Windows only)
                            if platform.system() == 'Windows':
                                try:
                                    # This is a rough check - not reading actual volume
                                    print(f"[MgbaEmulator] ║ Windows Audio:    System audio APIs accessible")
                                except:
                                    print(f"[MgbaEmulator] ║ Windows Audio:    Cannot access system audio")
                        except:
                            pass
                        
                        print(f"[MgbaEmulator] ╚══════════════════════════════════════════════════════")
                        
                        init_ok = True
                        break
                    else:
                        print(
                            f"[MgbaEmulator] Mixer init returned None, attempt {attempt+1}/{max_attempts}"
                        )
                        pygame.time.wait(100)
                except Exception as e:
                    print(
                        f"[MgbaEmulator] Mixer init attempt {attempt+1}/{max_attempts} failed: {e}"
                    )
                    pygame.time.wait(100)

            if not init_ok:
                # Try falling back to platform defaults before giving up
                default_buf, default_depth = get_audio_platform_defaults()
                if audio_buffer != default_buf or audio_queue_depth != default_depth:
                    print(f"[MgbaEmulator] Falling back to platform defaults: buffer={default_buf}, depth={default_depth}")
                    self._save_audio_settings_to_file(default_buf, default_depth)
                    self.audio_settings_reverted = True
                    audio_buffer = default_buf
                    self.audio_queue = deque(maxlen=default_depth)
                    try:
                        pygame.mixer.init(
                            frequency=self.sample_rate,
                            size=-16,
                            channels=2,
                            buffer=default_buf,
                        )
                        init_info = pygame.mixer.get_init()
                        if init_info:
                            print(f"[MgbaEmulator] Mixer initialized on fallback: {init_info}")
                            init_ok = True
                    except Exception as e2:
                        print(f"[MgbaEmulator] Fallback mixer init also failed: {e2}")

            if not init_ok:
                print("[MgbaEmulator] WARNING: All mixer init attempts failed!")
                return

            # Make sure we have enough channels and reserve one for emulator
            pygame.mixer.set_num_channels(8)
            self._audio_channel = pygame.mixer.Channel(7)

            # Verify channel is valid and set volume
            if self._audio_channel:
                self._apply_channel_volume()
                print(
                    f"[MgbaEmulator] Audio channel reserved: {self._audio_channel}, "
                    f"volume: {self._get_effective_volume():.2f}"
                )
            else:
                print("[MgbaEmulator] WARNING: Failed to get audio channel!")
                return

            # Start audio thread
            self._audio_running = True
            self._audio_thread = threading.Thread(
                target=self._audio_thread_func, daemon=True
            )
            self._audio_thread.start()

            # Track what buffer we initialised with so _reinit_audio can
            # detect changes made via Settings while paused.
            self._last_audio_buffer = audio_buffer

            # Log device and audio configuration
            self._log_audio_device_info()

        except Exception as e:
            print(f"[MgbaEmulator] Audio init failed: {e}")
            import traceback

            traceback.print_exc()

    def _audio_thread_func(self):
        """Background thread to feed audio to pygame.

        IMPORTANT: This thread must NEVER call ``pygame.mixer.init()`` or
        ``pygame.mixer.quit()``.  Mixer lifecycle is managed exclusively by
        ``_init_audio()`` and ``_reinit_audio()`` on the main thread.
        Touching it from here causes race conditions with Sinew's menu music.
        """
        print("[MgbaEmulator] ╔══════════════════════════════════════════════════════")
        print("[MgbaEmulator] ║ AUDIO THREAD STARTED")
        print("[MgbaEmulator] ╠══════════════════════════════════════════════════════")
        print(f"[MgbaEmulator] ║ Thread ID:        {threading.get_ident()}")
        print(f"[MgbaEmulator] ║ Mixer state:      {pygame.mixer.get_init()}")
        print(f"[MgbaEmulator] ║ Channel assigned: {self._audio_channel}")
        print(f"[MgbaEmulator] ║ Queue max size:   {self.audio_queue.maxlen}")
        print(f"[MgbaEmulator] ║ Paused:           {self.paused}")
        print("[MgbaEmulator] ╚══════════════════════════════════════════════════════")
        
        error_count = 0
        chunks_played = 0
        # How many chunks to keep buffered at most before dropping stale audio.
        MAX_QUEUE_DEPTH = self.audio_queue.maxlen or 4

        while self._audio_running:
            try:
                # Skip if paused — Sinew owns the mixer while we're paused
                if self.paused:
                    pygame.time.wait(10)
                    continue

                # If mixer is gone, just wait — _reinit_audio will fix it on resume
                if not pygame.mixer.get_init():
                    pygame.time.wait(50)
                    continue

                # Check if channel is ready for more audio
                if self._audio_channel:
                    try:
                        is_busy = self._audio_channel.get_busy()
                        queue_status = self._audio_channel.get_queue()
                    except Exception:
                        # Channel may be invalid if mixer was recycled
                        pygame.time.wait(10)
                        continue

                    # Can accept more audio if: not busy, or busy but queue is empty
                    can_accept = (not is_busy) or (is_busy and queue_status is None)

                    if can_accept:
                        chunk = None
                        with self._audio_lock:
                            # Latency guard: if the queue has backed up beyond our
                            # threshold, drop the oldest chunks to re-sync audio.
                            # This prevents latency from accumulating over long sessions.
                            queue_len = len(self.audio_queue)
                            if queue_len > MAX_QUEUE_DEPTH:
                                dropped = queue_len - MAX_QUEUE_DEPTH
                                for _ in range(dropped):
                                    self.audio_queue.popleft()
                                print(
                                    f"[MgbaEmulator] Audio latency correction: dropped {dropped} stale chunks"
                                )
                            if self.audio_queue:
                                chunk = self.audio_queue.popleft()

                        if chunk is not None and len(chunk) > 0:
                            try:
                                sound = pygame.sndarray.make_sound(chunk)
                                
                                # DIAGNOSTIC: Log first successful audio chunk
                                if chunks_played == 0:
                                    print(f"[MgbaEmulator] ╔══════════════════════════════════════════════════════")
                                    print(f"[MgbaEmulator] ║ FIRST AUDIO CHUNK")
                                    print(f"[MgbaEmulator] ╠══════════════════════════════════════════════════════")
                                    print(f"[MgbaEmulator] ║ Chunk shape:      {chunk.shape}")
                                    print(f"[MgbaEmulator] ║ Chunk dtype:      {chunk.dtype}")
                                    print(f"[MgbaEmulator] ║ Sound obj:        {sound}")
                                    print(f"[MgbaEmulator] ║ Sound length:     {sound.get_length():.3f}s")
                                    print(f"[MgbaEmulator] ║ Channel busy:     {is_busy}")
                                    print(f"[MgbaEmulator] ║ Channel volume:   {self._audio_channel.get_volume():.2f}")
                                    try:
                                        # Try to get actual system volume (Windows specific)
                                        mixer_vol = pygame.mixer.music.get_volume()
                                        print(f"[MgbaEmulator] ║ Mixer volume:     {mixer_vol:.2f}")
                                    except:
                                        pass
                                    print(f"[MgbaEmulator] ║ Audio will play:  {'YES - channel.play()' if not is_busy else 'YES - channel.queue()'}")
                                    print(f"[MgbaEmulator] ╚══════════════════════════════════════════════════════")

                                # If channel is not busy, use play() to start it
                                # If channel is busy but queue is empty, use queue() to line up next
                                if not is_busy:
                                    self._audio_channel.play(sound)
                                else:
                                    self._audio_channel.queue(sound)

                                chunks_played += 1
                                
                                # Log milestone chunks
                                if chunks_played in [10, 100, 1000]:
                                    print(f"[MgbaEmulator] Audio thread: {chunks_played} chunks played successfully")
                                
                                error_count = 0  # Reset on success
                            except Exception as e:
                                error_count += 1
                                if error_count < 5:
                                    print(f"[MgbaEmulator] ╔══════════════════════════════════════════════════════")
                                    print(f"[MgbaEmulator] ║ AUDIO PLAYBACK ERROR #{error_count}")
                                    print(f"[MgbaEmulator] ╠══════════════════════════════════════════════════════")
                                    print(f"[MgbaEmulator] ║ Error: {e}")
                                    print(f"[MgbaEmulator] ║ Chunk shape: {chunk.shape if chunk is not None else 'None'}")
                                    print(f"[MgbaEmulator] ║ Mixer state: {pygame.mixer.get_init()}")
                                    print(f"[MgbaEmulator] ║ Channel valid: {self._audio_channel is not None}")
                                    print(f"[MgbaEmulator] ╚══════════════════════════════════════════════════════")
                                    import traceback
                                    traceback.print_exc()

                pygame.time.wait(1)
            except Exception as e:
                error_count += 1
                if error_count < 5:
                    print(f"[MgbaEmulator] Audio thread error: {e}")
                pygame.time.wait(10)
        print("[MgbaEmulator] Audio thread stopped")

    def _load_sram(self):
        """Load SRAM from save file."""
        self.sram_loaded_valid = False  # Reset flag

        sram_ptr = self.lib.retro_get_memory_data(RETRO_MEMORY_SAVE_RAM)
        sram_size = self.lib.retro_get_memory_size(RETRO_MEMORY_SAVE_RAM)

        if not sram_ptr or sram_size == 0:
            print("[MgbaEmulator] No SRAM for this game")
            return False

        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "rb") as f:
                    data = f.read()

                # Validate save using section ID check (same as parser)
                # Gen3 has two save slots - check both
                # Section ID at offset 0xFF4 should be 0-13 for valid saves
                slot_a_valid = False
                slot_b_valid = False

                if len(data) >= 0xFF6:
                    section_id_a = data[0xFF4] | (data[0xFF5] << 8)
                    slot_a_valid = 0 <= section_id_a <= 13

                if len(data) >= 0xF000:
                    section_id_b = data[0xEFF4] | (data[0xEFF5] << 8)
                    slot_b_valid = 0 <= section_id_b <= 13

                if not slot_a_valid and not slot_b_valid:
                    print(
                        "[MgbaEmulator] Warning: Save file appears blank (no valid slots)"
                    )
                    print(
                        "[MgbaEmulator] You can start a new game, existing save won't be overwritten"
                    )
                    return False

                copy_size = min(len(data), sram_size)
                ctypes.memmove(sram_ptr, data, copy_size)

                slot_info = []
                if slot_a_valid:
                    slot_info.append("A")
                if slot_b_valid:
                    slot_info.append("B")
                print(
                    f"[MgbaEmulator] Loaded save: {os.path.basename(self.save_path)} ({copy_size} bytes, valid slots: {','.join(slot_info)})"
                )

                # Reset core to re-read save
                self.lib.retro_reset()
                self.sram_loaded_valid = True  # Mark as valid
                return True
            except Exception as e:
                print(f"[MgbaEmulator] Failed to load save: {e}")
                return False
        else:
            print(f"[MgbaEmulator] No save file found at {self.save_path}")
            return False

    def save_sram(self):
        """Save SRAM to file. Returns False if save would be blank."""
        if not self.loaded:
            print("[MgbaEmulator] Cannot save - no ROM loaded")
            return False

        sram_ptr = self.lib.retro_get_memory_data(RETRO_MEMORY_SAVE_RAM)
        sram_size = self.lib.retro_get_memory_size(RETRO_MEMORY_SAVE_RAM)

        if not sram_ptr or sram_size == 0:
            print("[MgbaEmulator] No SRAM available")
            return False

        try:
            sram_data = (ctypes.c_uint8 * sram_size)()
            ctypes.memmove(sram_data, sram_ptr, sram_size)
            data_bytes = bytes(sram_data)

            # CRITICAL: Validate save using section ID check
            # Gen3 has two save slots - at least one must be valid
            slot_a_valid = False
            slot_b_valid = False

            if len(data_bytes) >= 0xFF6:
                section_id_a = data_bytes[0xFF4] | (data_bytes[0xFF5] << 8)
                slot_a_valid = 0 <= section_id_a <= 13

            if len(data_bytes) >= 0xF000:
                section_id_b = data_bytes[0xEFF4] | (data_bytes[0xEFF5] << 8)
                slot_b_valid = 0 <= section_id_b <= 13

            if not slot_a_valid and not slot_b_valid:
                print(
                    f"[MgbaEmulator] BLOCKED: Would write blank save (no valid slots) to {os.path.basename(self.save_path)}"
                )
                return False

            with open(self.save_path, "wb") as f:
                f.write(data_bytes)

            print(f"[MgbaEmulator] Saved: {os.path.basename(self.save_path)}")
            return True
        except Exception as e:
            print(f"[MgbaEmulator] Save failed: {e}")
            return False

    def run_frame(self):
        """Run one frame of emulation (multiplied for fast-forward)."""
        if not self.loaded or self.paused:
            return

        # DIAGNOSTIC: Periodic audio status check
        import time
        current_time = time.time()
        if current_time - self._last_audio_diagnostic_time >= self._diagnostic_interval:
            self._last_audio_diagnostic_time = current_time
            thread_alive = self._audio_thread and self._audio_thread.is_alive()
            queue_size = len(self.audio_queue)
            print(f"[MgbaEmulator] ▶ Audio Status: thread={'RUNNING ✅' if thread_alive else 'STOPPED ❌'}, "
                  f"batches_received={self._audio_batches_received}, "
                  f"queue={queue_size}/{self.audio_queue.maxlen}, "
                  f"channel={'OK' if self._audio_channel else 'NONE'}, "
                  f"paused={self.paused}")

        multiplier = self._fast_forward_multiplier
        for i in range(multiplier):
            self.lib.retro_run()
        # Process video once per display frame regardless of multiplier
        self._process_video()

    def set_fast_forward(self, multiplier):
        """Set fast-forward multiplier. Pass 1 to return to normal speed."""
        self._fast_forward_multiplier = max(1, int(multiplier))
        label = "Off" if self._fast_forward_multiplier == 1 else f"{self._fast_forward_multiplier}x"
        print(f"[MgbaEmulator] Fast-forward: {label}")

    # ---- Audio buffer / queue tuning ----

    def set_audio_settings(self, buffer_size, queue_depth):
        """Stage new audio buffer / queue depth for next audio init.

        The values are NOT applied immediately because calling
        ``pygame.mixer.quit()`` while Sinew's menu music is playing would
        kill it.  Instead the values are stored and picked up the next time
        ``_init_audio()`` or ``_reinit_audio()`` runs (i.e. on game launch
        or resume).

        Returns True always — actual failure is handled at apply-time.
        """
        self._pending_audio_buffer = int(buffer_size)
        self._pending_audio_queue_depth = int(queue_depth)
        print(
            f"[MgbaEmulator] Audio settings staged: buffer={buffer_size}, "
            f"queue_depth={queue_depth} (applied on next audio init)"
        )
        return True

    def _consume_pending_audio_settings(self):
        """If new audio params have been staged, return (buf, depth) and clear.
        Otherwise return the current saved settings."""
        if self._pending_audio_buffer is not None:
            buf = self._pending_audio_buffer
            depth = self._pending_audio_queue_depth or get_audio_settings()[1]
            self._pending_audio_buffer = None
            self._pending_audio_queue_depth = None
            print(f"[MgbaEmulator] Consuming staged audio settings: buffer={buf}, depth={depth}")
            return buf, depth
        return get_audio_settings()

    @staticmethod
    def _save_audio_settings_to_file(buffer_size, queue_depth):
        """Persist audio buffer/queue to sinew_settings.json."""
        import json
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            data["mgba_audio_buffer"] = buffer_size
            data["mgba_audio_queue_depth"] = queue_depth
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[MgbaEmulator] Failed to persist audio settings: {e}")

    def _log_audio_device_info(self):
        """Log the current audio device, buffer size and queue depth."""
        try:
            mixer_info = pygame.mixer.get_init()
            freq, fmt, ch = mixer_info if mixer_info else (0, 0, 0)
            buf, depth = get_audio_settings()
            driver = os.environ.get("SDL_AUDIODRIVER", "auto")
            device_name = "unknown"
            if self._joystick:
                device_name = self._joystick.get_name()
            print(
                f"[MgbaEmulator] Audio device info: driver={driver}, "
                f"mixer=({freq}Hz, fmt={fmt}, ch={ch}), "
                f"buffer={buf}, queue_depth={depth}, "
                f"controller={device_name}"
            )
        except Exception as e:
            print(f"[MgbaEmulator] Could not log audio device info: {e}")

    # ---- Volume / mute ----

    def _load_volume_settings(self):
        """Load master volume and mGBA mute from sinew_settings.json."""
        import json
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                self._master_volume = data.get("master_volume", VOLUME_DEFAULT)
                self._mgba_muted = data.get("mgba_muted", False)
        except Exception as e:
            print(f"[MgbaEmulator] Could not load volume settings: {e}")

    def _get_effective_volume(self):
        """Return 0.0–1.0 for the audio channel, accounting for master + mute."""
        if self._mgba_muted:
            return 0.0
        return max(0.0, min(1.0, self._master_volume / 100.0))

    def set_master_volume(self, volume_int):
        """Set master volume (0–100). Applies immediately to audio channel."""
        self._master_volume = max(0, min(100, int(volume_int)))
        self._apply_channel_volume()
        paused_note = ' (paused - will apply on resume)' if self.paused else ''
        print(f"[MgbaEmulator] Master volume: {self._master_volume}%{paused_note}")

    def set_mgba_muted(self, muted):
        """Mute/unmute emulator audio only. Applies immediately."""
        self._mgba_muted = bool(muted)
        self._apply_channel_volume()
        status = 'ON' if muted else 'OFF'
        paused_note = ' (paused - will apply on resume)' if self.paused else ''
        print(f"[MgbaEmulator] mGBA mute: {status}{paused_note}")

    def _apply_channel_volume(self):
        """Push the effective volume to the pygame channel.
        
        Only applies volume if emulator is not paused and channel is valid.
        During pause, Sinew owns the mixer and our channel may be invalid.
        Volume will be reapplied automatically on resume via _reinit_audio().
        """
        vol = self._get_effective_volume()
        
        # Skip if paused - our channel may be invalid while Sinew owns the mixer
        if self.paused:
            return
            
        if self._audio_channel:
            try:
                self._audio_channel.set_volume(vol)
            except Exception:
                pass

    def _load_fast_forward_setting(self):
        """Load and apply saved fast-forward state from sinew_settings.json on startup."""
        import json

        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                enabled = data.get("mgba_fastforward_enabled", False)
                speed = data.get("mgba_fastforward_speed", 2)
                self._fast_forward_multiplier = max(1, int(speed)) if enabled else 1
                if self._fast_forward_multiplier > 1:
                    print(f"[MgbaEmulator] Fast-forward loaded: {self._fast_forward_multiplier}x")
        except Exception as e:
            print(f"[MgbaEmulator] Could not load fast-forward setting: {e}")

    def _process_video(self):
        """Process video frame from core."""
        if not self._frame_ready:
            return

        self._frame_ready = False
        w = self._frame_meta["width"]
        h = self._frame_meta["height"]
        pitch = self._frame_meta["pitch"]

        if w == 0 or h == 0 or pitch == 0:
            return

        try:
            if self.pixel_format == RETRO_PIXEL_FORMAT_RGB565:
                row_pixels = pitch // 2
                src_ptr = cast(self._raw_framebuf_ptr, POINTER(c_uint16))
                fb16 = np.ctypeslib.as_array(src_ptr, shape=(h * row_pixels,))
                fb16 = fb16.reshape(h, row_pixels)[:, :w]

                r = ((fb16 >> 11) & 0x1F).astype(np.uint8)
                g = ((fb16 >> 5) & 0x3F).astype(np.uint8)
                b = (fb16 & 0x1F).astype(np.uint8)

                r = (r << 3) | (r >> 2)
                g = (g << 2) | (g >> 4)
                b = (b << 3) | (b >> 2)

                self.framebuffer[:h, :w] = np.dstack((r, g, b))

            elif self.pixel_format == RETRO_PIXEL_FORMAT_XRGB8888:
                row_pixels = pitch // 4
                src_ptr = cast(self._raw_framebuf_ptr, POINTER(c_uint32))
                fb32 = np.ctypeslib.as_array(src_ptr, shape=(h * row_pixels,))
                fb32 = fb32.reshape(h, row_pixels)[:, :w]

                r = ((fb32 >> 16) & 0xFF).astype(np.uint8)
                g = ((fb32 >> 8) & 0xFF).astype(np.uint8)
                b = (fb32 & 0xFF).astype(np.uint8)

                self.framebuffer[:h, :w] = np.dstack((r, g, b))
        except Exception as e:
            print(f"[MgbaEmulator] Frame processing error: {e}")

    def get_surface(self, scale=1):
        """
        Get the current frame as a pygame Surface.

        Args:
            scale: Scale factor (1 = native 240x160)

        Returns:
            pygame.Surface
        """
        surf = pygame.surfarray.make_surface(self.framebuffer.swapaxes(0, 1))

        if scale != 1:
            new_size = (self.WIDTH * scale, self.HEIGHT * scale)
            surf = pygame.transform.scale(surf, new_size)

        return surf

    def _load_pause_combo_setting(self):
        """Load pause combo setting from sinew_settings.json"""
        import json

        default = {"type": "combo", "buttons": ["START", "SELECT"]}

        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    if "pause_combo" in settings:
                        return settings["pause_combo"]
        except Exception:
            pass
        return default

    def check_pause_combo(self):
        """
        Check if the configured pause combo is held (controller combo OR keyboard MENU key).
        No hold timer - triggers immediately to avoid user frustration.
        Debounce is handled by the caller.

        Returns:
            bool: True if combo/key is currently pressed
        """
        if self._key_state is None:
            return False

        setting = getattr(
            self,
            "_pause_combo_setting",
            {"type": "combo", "buttons": ["START", "SELECT"]},
        )
        combo_held = False

        # Check if keyboard MENU key is pressed (loaded from keyboard_nav_map)
        # Default is pygame.K_m, but user can remap it
        try:
            # Try to get MENU key binding from keyboard nav map
            menu_keys = getattr(self, "_menu_keys", [pygame.K_m])
            for key in menu_keys:
                if self._key_state[key]:
                    combo_held = True
                    break
        except Exception:
            pass

        # If MENU key not pressed, check configured controller combo
        if not combo_held:
            if setting.get("type") == "custom":
                # Custom single button
                custom_btn = setting.get("button")
                if custom_btn is not None and self._joystick:
                    try:
                        if custom_btn < self._joystick.get_numbuttons():
                            combo_held = self._joystick.get_button(custom_btn)
                    except Exception:
                        pass
            else:
                # Button combo
                required_buttons = setting.get("buttons", ["START", "SELECT"])
                buttons_held = {}

                # Check keyboard
                if "START" in required_buttons:
                    buttons_held["START"] = self._key_state[pygame.K_RETURN]
                if "SELECT" in required_buttons:
                    buttons_held["SELECT"] = self._key_state[pygame.K_BACKSPACE]

                # Check gamepad
                if self._joystick:
                    try:
                        num_buttons = self._joystick.get_numbuttons()

                        # Map button names to gamepad indices.
                        # No magic-number fallbacks — _gamepad_map was already
                        # populated by _init_joystick (SDL config / profile / defaults).
                        btn_map = {
                            "START":  self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_START),
                            "SELECT": self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_SELECT),
                            "L":      self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_L),
                            "R":      self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_R),
                        }

                        for btn_name in required_buttons:
                            btn_idx = btn_map.get(btn_name)
                            if btn_idx is not None and btn_idx < num_buttons:
                                if self._joystick.get_button(btn_idx):
                                    buttons_held[btn_name] = True
                    except Exception:
                        pass

                # Check if all required buttons are held
                combo_held = all(buttons_held.get(btn, False) for btn in required_buttons)

        return combo_held

    def toggle_pause(self):
        """Toggle pause state."""
        self.paused = not self.paused
        if self.paused:
            print("[MgbaEmulator] Paused - returning to Sinew")
            self.save_sram()  # Auto-save when pausing
        else:
            print("[MgbaEmulator] Resumed")

    def pause(self):
        """Pause emulation.

        Stops the audio thread so it cannot interfere with Sinew's mixer
        when menu music starts.  The thread is restarted on resume().
        """
        if not self.paused:
            self.paused = True
            self.save_sram()

            # Stop audio thread — Sinew is about to own the mixer
            self._audio_running = False
            if self._audio_thread and self._audio_thread.is_alive():
                try:
                    self._audio_thread.join(timeout=0.5)
                except Exception:
                    pass
            self._audio_thread = None

            # Clear stale audio data
            with self._audio_lock:
                self.audio_queue.clear()

            print("[MgbaEmulator] Paused")

    def resume(self):
        """Resume emulation."""
        if self.paused:
            print(
                f"[MgbaEmulator] Resuming... loaded={self.loaded}, paused={self.paused}"
            )

            # Reload controller config in case it changed while paused
            self._load_controller_config()

            # Reinitialize audio (it may have been disrupted while paused)
            self._reinit_audio()

            self.paused = False
            print(f"[MgbaEmulator] Resumed - paused now={self.paused}")

    def _reinit_audio(self):
        """Ensure audio is working after pause/resume.

        If the user changed audio buffer / queue depth from the Settings
        screen while paused, those values are consumed here so the mixer
        is reinitialised with the new params.  If the new params fail the
        mixer, we fall back to platform defaults gracefully.
        """
        try:
            # Consume any pending audio setting changes
            audio_buffer, audio_queue_depth = self._consume_pending_audio_settings()

            # Resize the deque if depth changed
            if self.audio_queue.maxlen != audio_queue_depth:
                self.audio_queue = deque(maxlen=audio_queue_depth)
                print(f"[MgbaEmulator] Queue depth resized to {audio_queue_depth}")

            # Clear stale audio data
            with self._audio_lock:
                queue_size = len(self.audio_queue)
                self.audio_queue.clear()
                if queue_size > 0:
                    print(
                        f"[MgbaEmulator] Cleared {queue_size} audio chunks from queue"
                    )

            # Reload volume/mute in case they changed while paused
            self._load_volume_settings()

            # Get expected sample rate
            sample_rate = getattr(self, "sample_rate", 32768)

            # Check if mixer is initialized at the correct frequency
            mixer_init = pygame.mixer.get_init()
            needs_full_reinit = False

            if not mixer_init:
                needs_full_reinit = True
                print(
                    f"[MgbaEmulator] Mixer not initialized, will init at {sample_rate}Hz"
                )
            elif mixer_init[0] != sample_rate:
                needs_full_reinit = True
                print(
                    f"[MgbaEmulator] Mixer frequency mismatch: {mixer_init[0]} vs {sample_rate}"
                )
            # Also reinit if the user changed the buffer size
            elif mixer_init and hasattr(self, '_last_audio_buffer') and self._last_audio_buffer != audio_buffer:
                needs_full_reinit = True
                print(
                    f"[MgbaEmulator] Buffer size changed: {self._last_audio_buffer} -> {audio_buffer}"
                )

            if needs_full_reinit:
                # Stop audio thread first
                self._audio_running = False
                if self._audio_thread and self._audio_thread.is_alive():
                    try:
                        self._audio_thread.join(timeout=0.5)
                    except Exception:
                        pass
                self._audio_thread = None

                # Reinitialize mixer completely
                try:
                    pygame.mixer.quit()
                    pygame.time.wait(100)
                except Exception:
                    pass

                try:
                    pygame.mixer.init(
                        frequency=sample_rate,
                        size=-16,
                        channels=2,
                        buffer=audio_buffer,
                    )
                except Exception as e:
                    print(f"[MgbaEmulator] Mixer reinit failed with buffer={audio_buffer}: {e}")
                    # Fallback to platform defaults
                    default_buf, default_depth = get_audio_platform_defaults()
                    print(f"[MgbaEmulator] Falling back to defaults: buffer={default_buf}")
                    self._save_audio_settings_to_file(default_buf, default_depth)
                    self.audio_settings_reverted = True
                    audio_buffer = default_buf
                    self.audio_queue = deque(maxlen=default_depth)
                    pygame.mixer.init(
                        frequency=sample_rate,
                        size=-16,
                        channels=2,
                        buffer=default_buf,
                    )

                self._last_audio_buffer = audio_buffer
                pygame.mixer.set_num_channels(8)
                print(f"[MgbaEmulator] Mixer reinitialized: {pygame.mixer.get_init()}")

                # Get fresh channel and start new thread
                self._audio_channel = pygame.mixer.Channel(7)
                self._apply_channel_volume()

                self._audio_running = True
                self._audio_thread = threading.Thread(
                    target=self._audio_thread_func, daemon=True
                )
                self._audio_thread.start()
                print("[MgbaEmulator] Audio thread started fresh")
            else:
                # Mixer is fine - just refresh channel reference and ensure thread is running
                pygame.mixer.set_num_channels(8)
                self._audio_channel = pygame.mixer.Channel(7)
                self._apply_channel_volume()

                # Make sure audio thread is running
                if self._audio_thread is None or not self._audio_thread.is_alive():
                    self._audio_running = True
                    self._audio_thread = threading.Thread(
                        target=self._audio_thread_func, daemon=True
                    )
                    self._audio_thread.start()
                    print("[MgbaEmulator] Audio thread restarted")
                # else thread is already running, it will resume automatically when paused=False

            # Log device info after reinit
            self._log_audio_device_info()

        except Exception as e:
            print(f"[MgbaEmulator] Audio reinit error: {e}")
            import traceback

            traceback.print_exc()

    def reset(self):
        """Reset the emulation."""
        if self.loaded:
            self.lib.retro_reset()
            print("[MgbaEmulator] Reset")

    def unload(self):
        """Unload the current ROM and save."""
        if self.loaded:
            try:
                self.save_sram()
            except Exception as e:
                print(f"[MgbaEmulator] Save during unload failed: {e}")

            # Stop audio thread before unloading
            self._audio_running = False
            if self._audio_thread and self._audio_thread.is_alive():
                try:
                    self._audio_thread.join(timeout=0.5)
                except Exception:
                    pass
            self._audio_thread = None

            try:
                self.lib.retro_unload_game()
            except Exception as e:
                print(f"[MgbaEmulator] Unload failed: {e}")

            self.loaded = False
            self.paused = False  # Reset pause state for next game
            self.rom_path = None  # Clear ROM path
            print("[MgbaEmulator] Unloaded")

    def shutdown(self):
        """Shutdown the emulator completely."""
        # Stop audio thread first
        self._audio_running = False
        if self._audio_thread and self._audio_thread.is_alive():
            try:
                self._audio_thread.join(timeout=1.0)
            except Exception:
                pass

        # Save and unload game
        if self.loaded:
            try:
                self.save_sram()
            except Exception as e:
                print(f"[MgbaEmulator] Save during shutdown failed: {e}")

            try:
                self.lib.retro_unload_game()
            except Exception as e:
                print(f"[MgbaEmulator] Unload during shutdown failed: {e}")

            self.loaded = False

        # Deinit core
        try:
            self.lib.retro_deinit()
        except Exception as e:
            print(f"[MgbaEmulator] Deinit failed: {e}")

        # Clean up temporary extracted ROM files
        try:
            from config import cleanup_temp_roms
            cleanup_temp_roms()
        except Exception as e:
            print(f"[MgbaEmulator] Temp ROM cleanup failed: {e}")

        print("[MgbaEmulator] Shutdown complete")


# Convenience function for quick testing
def test_emulator():
    """Test the emulator standalone."""
    pygame.init()

    SCALE = 3
    screen = pygame.display.set_mode((240 * SCALE, 160 * SCALE))
    pygame.display.set_caption("mGBA Test")
    clock = pygame.time.Clock()

    # Auto-detect core based on platform (uses config paths by default)
    emu = MgbaEmulator()

    rom_path = os.path.join(ROMS_DIR, "Emerald.gba")

    emu.load_rom(rom_path)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_F5:
                    emu.save_sram()

        # Check pause combo
        if emu.check_pause_combo():
            emu.toggle_pause()

        if not emu.paused:
            emu.run_frame()

        # Draw
        surf = emu.get_surface(scale=SCALE)
        screen.blit(surf, (0, 0))

        if emu.paused:
            # Draw pause indicator
            font = pygame.font.Font(None, 36)
            text = font.render(
                "PAUSED - Hold Start+Select to resume", True, (255, 255, 0)
            )
            rect = text.get_rect(center=(120 * SCALE, 80 * SCALE))
            screen.blit(text, rect)

        pygame.display.flip()
        clock.tick(emu.fps if emu.loaded else 60)

    emu.shutdown()
    pygame.quit()


if __name__ == "__main__":
    test_emulator()