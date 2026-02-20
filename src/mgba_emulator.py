# mgba_emulator.py - mGBA libretro core wrapper for Sinew
# Integrates GBA emulation into the Sinew Pokemon save manager

import ctypes
from ctypes import (c_void_p, c_char_p, c_uint32, c_uint16, c_bool, c_int16,
                    c_size_t, POINTER, CFUNCTYPE, create_string_buffer, cast, byref)
import pygame
import numpy as np
import os
import platform
import threading
import time
from collections import deque

# Import config for absolute paths
try:
    import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


def _get_default_cores_dir():
    """Get the default cores directory (absolute path)."""
    if CONFIG_AVAILABLE and hasattr(config, 'CORES_DIR'):
        return config.CORES_DIR
    elif CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
        return os.path.join(config.BASE_DIR, "cores")
    else:
        return os.path.abspath("cores")


def _get_default_saves_dir():
    """Get the default saves directory (absolute path)."""
    if CONFIG_AVAILABLE and hasattr(config, 'SAVES_DIR'):
        return config.SAVES_DIR
    elif CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
        return os.path.join(config.BASE_DIR, "saves")
    else:
        return os.path.abspath("saves")


def _get_default_system_dir():
    """Get the default system directory (absolute path)."""
    if CONFIG_AVAILABLE and hasattr(config, 'SYSTEM_DIR'):
        return config.SYSTEM_DIR
    elif CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
        return os.path.join(config.BASE_DIR, "system")
    else:
        return os.path.abspath("system")


def get_platform_core_extension():
    """
    Get the correct libretro core file extension for the current platform.
    
    Returns:
        str: File extension ('.dll', '.so', or '.dylib')
    """
    system = platform.system().lower()
    if system == 'windows':
        return '.dll'
    elif system == 'linux':
        return '.so'
    elif system == 'darwin':  # macOS
        return '.dylib'
    else:
        # Default to .so for unknown Unix-like systems
        return '.so'


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
    if system == 'windows':
        os_name = 'windows'
        ext = '.dll'
    elif system == 'darwin':
        os_name = 'macos'
        ext = '.dylib'
    else:  # Linux and others
        os_name = 'linux'
        ext = '.so'
    
    # Determine architecture
    if machine in ('amd64', 'x86_64'):
        arch_name = 'x64'
    elif machine in ('i386', 'i686', 'x86'):
        arch_name = 'x86'
    elif machine in ('aarch64', 'arm64'):
        arch_name = 'arm64'
    elif machine in ('armv7l', 'armv6l', 'arm'):
        arch_name = 'arm32'
    else:
        # Default fallback based on pointer size
        import struct
        if struct.calcsize('P') == 8:
            arch_name = 'x64'
        else:
            arch_name = 'x86'
        print(f"[MgbaEmulator] Unknown machine type '{machine}', assuming {arch_name}")
    
    return os_name, arch_name, ext


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
        # Make relative path absolute
        if CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
            cores_dir = os.path.join(config.BASE_DIR, cores_dir)
        else:
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
        if CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
            cores_dir = os.path.join(config.BASE_DIR, cores_dir)
        else:
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
            if filename.startswith('mgba') and filename.endswith(ext):
                # Check if it matches our OS
                if f"_{os_name}_" in filename:
                    found_path = os.path.join(cores_dir, filename)
                    print(f"[MgbaEmulator] Found alternative core: {found_path}")
                    return found_path
        
        # Fallback: any core with matching extension
        for filename in os.listdir(cores_dir):
            if filename.startswith('mgba') and filename.endswith(ext):
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
        
        # State
        self.loaded = False
        self.paused = False
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
        
        # Audio
        self.audio_queue = deque(maxlen=32)
        self._audio_lock = threading.Lock()
        self._audio_channel = None
        self._audio_thread = None
        self._audio_running = False
        
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
        
        # Keep callbacks alive
        self._keep_alive = []
        
        # Directory buffers (must stay alive)
        self._save_dir_buf = create_string_buffer(self.save_dir.encode("utf-8"))
        self._system_dir_buf = create_string_buffer(self.system_dir.encode("utf-8"))
        
        # Load the core
        self._load_core()
    
    def _load_controller_config(self):
        """Load saved controller configuration from sinew_settings.json.
        
        Loads both face button mappings and d-pad bindings (hat remaps,
        button-based dpad, axis-based dpad) so the emulator respects the
        same config as the Sinew UI.
        """
        import json
        
        # Get absolute path for settings file
        if CONFIG_AVAILABLE and hasattr(config, 'SETTINGS_FILE'):
            config_file = config.SETTINGS_FILE
        elif CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
            config_file = os.path.join(config.BASE_DIR, "sinew_settings.json")
        else:
            config_file = "sinew_settings.json"
        
        # D-pad config: hat direction -> (hat_component_index, expected_value)
        # Default: standard hat convention
        self._dpad_hat_map = {
            RETRO_DEVICE_ID_JOYPAD_UP:    ('y', 1),
            RETRO_DEVICE_ID_JOYPAD_DOWN:  ('y', -1),
            RETRO_DEVICE_ID_JOYPAD_LEFT:  ('x', -1),
            RETRO_DEVICE_ID_JOYPAD_RIGHT: ('x', 1),
        }
        # D-pad as buttons: retro_id -> controller button index (or None)
        self._dpad_button_map = {
            RETRO_DEVICE_ID_JOYPAD_UP:    None,
            RETRO_DEVICE_ID_JOYPAD_DOWN:  None,
            RETRO_DEVICE_ID_JOYPAD_LEFT:  None,
            RETRO_DEVICE_ID_JOYPAD_RIGHT: None,
        }
        # D-pad axis pairs to check: list of (x_axis, y_axis)
        self._dpad_axis_pairs = [(0, 1)]
        
        try:
            if not os.path.exists(config_file):
                return
            
            with open(config_file, 'r') as f:
                settings_data = json.load(f)
            
            # Load face button mappings from controller_mapping
            if 'controller_mapping' in settings_data:
                saved_map = settings_data['controller_mapping']
                
                # Map our button names to libretro IDs
                name_to_retro = {
                    'A': RETRO_DEVICE_ID_JOYPAD_A,
                    'B': RETRO_DEVICE_ID_JOYPAD_B,
                    'L': RETRO_DEVICE_ID_JOYPAD_L,
                    'R': RETRO_DEVICE_ID_JOYPAD_R,
                    'START': RETRO_DEVICE_ID_JOYPAD_START,
                    'SELECT': RETRO_DEVICE_ID_JOYPAD_SELECT,
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
                    'DPAD_UP':    RETRO_DEVICE_ID_JOYPAD_UP,
                    'DPAD_DOWN':  RETRO_DEVICE_ID_JOYPAD_DOWN,
                    'DPAD_LEFT':  RETRO_DEVICE_ID_JOYPAD_LEFT,
                    'DPAD_RIGHT': RETRO_DEVICE_ID_JOYPAD_RIGHT,
                }
                
                has_dpad_bindings = False
                for dpad_key, retro_id in dpad_name_to_retro.items():
                    binding = saved_map.get(dpad_key)
                    if not isinstance(binding, dict):
                        continue
                    
                    has_dpad_bindings = True
                    source = binding.get('source', '')
                    
                    if source == 'hat':
                        axis = binding.get('axis', 'y')
                        value = binding.get('value', 0)
                        self._dpad_hat_map[retro_id] = (axis, value)
                    
                    elif source == 'button':
                        btn_idx = binding.get('button')
                        if btn_idx is not None:
                            self._dpad_button_map[retro_id] = btn_idx
                            # Disable hat for this direction since it's button-based
                            self._dpad_hat_map[retro_id] = None
                    
                    elif source == 'axis':
                        axis_idx = binding.get('axis_index', 0)
                        direction = binding.get('direction', 0)
                        # Store as special axis binding
                        # We'll check this in _handle_input
                        if not hasattr(self, '_dpad_axis_bindings'):
                            self._dpad_axis_bindings = {}
                        self._dpad_axis_bindings[retro_id] = (axis_idx, direction)
                        # Disable hat for this direction
                        self._dpad_hat_map[retro_id] = None
                
                if has_dpad_bindings:
                    print(f"[MgbaEmulator] Loaded d-pad bindings: hat={self._dpad_hat_map}")
                
                print(f"[MgbaEmulator] Loaded controller mappings: A={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_A)}, B={self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_B)}")
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
        
        Falls back to built-in defaults for any missing entries.
        """
        import json
        
        # Built-in defaults
        DEFAULT_KB = {
            RETRO_DEVICE_ID_JOYPAD_A:      [pygame.K_z],
            RETRO_DEVICE_ID_JOYPAD_B:      [pygame.K_x],
            RETRO_DEVICE_ID_JOYPAD_SELECT: [pygame.K_BACKSPACE],
            RETRO_DEVICE_ID_JOYPAD_START:  [pygame.K_RETURN],
            RETRO_DEVICE_ID_JOYPAD_UP:     [pygame.K_UP,   pygame.K_w],
            RETRO_DEVICE_ID_JOYPAD_DOWN:   [pygame.K_DOWN, pygame.K_s],
            RETRO_DEVICE_ID_JOYPAD_LEFT:   [pygame.K_LEFT, pygame.K_a],
            RETRO_DEVICE_ID_JOYPAD_RIGHT:  [pygame.K_RIGHT,pygame.K_d],
            RETRO_DEVICE_ID_JOYPAD_L:      [pygame.K_q],
            RETRO_DEVICE_ID_JOYPAD_R:      [pygame.K_e],
        }
        
        # Button name -> retro ID mapping for settings lookup
        NAME_TO_RETRO = {
            'A':      RETRO_DEVICE_ID_JOYPAD_A,
            'B':      RETRO_DEVICE_ID_JOYPAD_B,
            'SELECT': RETRO_DEVICE_ID_JOYPAD_SELECT,
            'START':  RETRO_DEVICE_ID_JOYPAD_START,
            'UP':     RETRO_DEVICE_ID_JOYPAD_UP,
            'DOWN':   RETRO_DEVICE_ID_JOYPAD_DOWN,
            'LEFT':   RETRO_DEVICE_ID_JOYPAD_LEFT,
            'RIGHT':  RETRO_DEVICE_ID_JOYPAD_RIGHT,
            'L':      RETRO_DEVICE_ID_JOYPAD_L,
            'R':      RETRO_DEVICE_ID_JOYPAD_R,
        }
        
        # Start from defaults
        self._kb_map = dict(DEFAULT_KB)
        
        if CONFIG_AVAILABLE and hasattr(config, 'SETTINGS_FILE'):
            config_file = config.SETTINGS_FILE
        elif CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
            config_file = os.path.join(config.BASE_DIR, "sinew_settings.json")
        else:
            config_file = "sinew_settings.json"
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    settings_data = json.load(f)
                
                saved = settings_data.get('keyboard_emulator_map', {})
                for btn_name, retro_id in NAME_TO_RETRO.items():
                    if btn_name in saved:
                        val = saved[btn_name]
                        if isinstance(val, list):
                            self._kb_map[retro_id] = [v for v in val if isinstance(v, int)]
                        elif isinstance(val, int):
                            self._kb_map[retro_id] = [val]
                
                if saved:
                    print(f"[MgbaEmulator] Loaded keyboard map from {config_file}")
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
        
        def audio_batch(ptr, frames):
            try:
                frames = int(frames)
                if frames == 0:
                    return 0
                arr = np.ctypeslib.as_array(ptr, shape=(frames * 2,)).copy()
                arr = arr.reshape(-1, 2)
                with self._audio_lock:
                    self.audio_queue.append(arr)
                return frames
            except Exception as e:
                print(f"[MgbaEmulator] Audio batch error: {e}")
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
                cast(data, POINTER(c_char_p))[0] = ctypes.addressof(self._system_dir_buf)
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
        
        if cmd in (RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2,
                   RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2_INTL,
                   RETRO_ENVIRONMENT_SET_CORE_OPTIONS,
                   RETRO_ENVIRONMENT_SET_CORE_OPTIONS_INTL):
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
        kb_map = getattr(self, '_kb_map', None) or {
            RETRO_DEVICE_ID_JOYPAD_A:      pygame.K_z,
            RETRO_DEVICE_ID_JOYPAD_B:      pygame.K_x,
            RETRO_DEVICE_ID_JOYPAD_SELECT: pygame.K_BACKSPACE,
            RETRO_DEVICE_ID_JOYPAD_START:  pygame.K_RETURN,
            RETRO_DEVICE_ID_JOYPAD_UP:     pygame.K_UP,
            RETRO_DEVICE_ID_JOYPAD_DOWN:   pygame.K_DOWN,
            RETRO_DEVICE_ID_JOYPAD_LEFT:   pygame.K_LEFT,
            RETRO_DEVICE_ID_JOYPAD_RIGHT:  pygame.K_RIGHT,
            RETRO_DEVICE_ID_JOYPAD_L:      pygame.K_a,
            RETRO_DEVICE_ID_JOYPAD_R:      pygame.K_s,
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
                        if axis == 'x' and hx == expected_value:
                            return 1
                        elif axis == 'y' and hy == expected_value:
                            return 1
                
                # D-pad via buttons (for controllers with button-based dpads)
                dpad_btn = self._dpad_button_map.get(button_id)
                if dpad_btn is not None:
                    num_buttons = self._joystick.get_numbuttons()
                    if dpad_btn < num_buttons and self._joystick.get_button(dpad_btn):
                        return 1
                
                # D-pad via specific axis bindings (from remapping)
                axis_bindings = getattr(self, '_dpad_axis_bindings', {})
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
            except:
                pass
        
        return 0
    
    def load_rom(self, rom_path, save_path=None):
        """
        Load a ROM file.
        
        Args:
            rom_path: Path to the GBA ROM
            save_path: Optional path to save file (auto-derived if not provided)
        """
        if not os.path.exists(rom_path):
            raise FileNotFoundError(f"ROM not found: {rom_path}")
        
        self.rom_path = os.path.abspath(rom_path)
        
        # Derive save path if not provided
        if save_path:
            self.save_path = os.path.abspath(save_path)
        else:
            rom_basename = os.path.splitext(os.path.basename(rom_path))[0]
            self.save_path = os.path.join(self.save_dir, f"{rom_basename}.sav")
        
        # Load the ROM
        game = retro_game_info(
            path=self.rom_path.encode("utf-8"),
            data=None,
            size=0,
            meta=None
        )
        
        if not self.lib.retro_load_game(byref(game)):
            raise RuntimeError(f"Failed to load ROM: {rom_path}")
        
        # Get AV info
        av_info = retro_system_av_info()
        self.lib.retro_get_system_av_info(byref(av_info))
        self.fps = av_info.timing.fps
        self.sample_rate = int(av_info.timing.sample_rate)
        
        print(f"[MgbaEmulator] Loaded: {os.path.basename(rom_path)}")
        print(f"[MgbaEmulator] FPS: {self.fps:.2f}, Sample rate: {self.sample_rate}")
        
        # Load SRAM
        self._load_sram()
        
        # Initialize audio
        self._init_audio()
        
        # Initialize joystick
        self._init_joystick()
        
        self.loaded = True
    
    def _init_joystick(self):
        """Initialize joystick if available."""
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()
            print(f"[MgbaEmulator] Controller: {self._joystick.get_name()}")
    
    def _init_audio(self):
        """Initialize audio playback."""
        try:
            # Stop any existing audio thread first
            self._audio_running = False
            if self._audio_thread and self._audio_thread.is_alive():
                try:
                    self._audio_thread.join(timeout=0.5)
                except:
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
            except:
                pass
            
            # Try to initialize mixer with multiple attempts
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    # Pre-init with specific settings for reliability
                    pygame.mixer.pre_init(
                        frequency=self.sample_rate,
                        size=-16,
                        channels=2,
                        buffer=1024
                    )
                    pygame.mixer.init()
                    
                    # Verify it actually initialized
                    init_info = pygame.mixer.get_init()
                    if init_info:
                        print(f"[MgbaEmulator] Mixer initialized: {init_info}")
                        break
                    else:
                        print(f"[MgbaEmulator] Mixer init returned None, attempt {attempt+1}/{max_attempts}")
                        pygame.time.wait(100)
                except Exception as e:
                    print(f"[MgbaEmulator] Mixer init attempt {attempt+1}/{max_attempts} failed: {e}")
                    pygame.time.wait(100)
            else:
                print("[MgbaEmulator] WARNING: All mixer init attempts failed!")
                return
            
            # Make sure we have enough channels and reserve one for emulator
            pygame.mixer.set_num_channels(8)
            self._audio_channel = pygame.mixer.Channel(7)
            
            # Verify channel is valid and set volume
            if self._audio_channel:
                self._audio_channel.set_volume(1.0)
                print(f"[MgbaEmulator] Audio channel reserved: {self._audio_channel}, volume: 1.0")
            else:
                print("[MgbaEmulator] WARNING: Failed to get audio channel!")
                return
            
            # Start audio thread
            self._audio_running = True
            self._audio_thread = threading.Thread(target=self._audio_thread_func, daemon=True)
            self._audio_thread.start()
            
        except Exception as e:
            print(f"[MgbaEmulator] Audio init failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _audio_thread_func(self):
        """Background thread to feed audio to pygame."""
        print("[MgbaEmulator] Audio thread started")
        error_count = 0
        chunks_played = 0
        reinit_attempted = False
        last_play_time = time.time()
        # How many chunks to keep buffered at most before dropping stale audio.
        # At ~32768 Hz with typical ~512-sample batches this is ~60-80ms of audio.
        # Keeping this small prevents latency from accumulating over long sessions.
        MAX_QUEUE_DEPTH = 4

        while self._audio_running:
            try:
                # Skip if paused
                if self.paused:
                    pygame.time.wait(10)
                    continue
                
                # Check if mixer is still initialized
                if not pygame.mixer.get_init():
                    if not reinit_attempted:
                        print("[MgbaEmulator] Mixer lost, attempting reinit...")
                        reinit_attempted = True
                        try:
                            sample_rate = getattr(self, 'sample_rate', 32768)
                            pygame.mixer.init(frequency=sample_rate, size=-16, channels=2, buffer=1024)
                            pygame.mixer.set_num_channels(8)
                            self._audio_channel = pygame.mixer.Channel(7)
                            print(f"[MgbaEmulator] Mixer reinitialized: {pygame.mixer.get_init()}")
                        except Exception as e:
                            print(f"[MgbaEmulator] Mixer reinit failed: {e}")
                    pygame.time.wait(100)
                    continue
                else:
                    reinit_attempted = False
                
                # Check if channel is ready for more audio
                if self._audio_channel:
                    is_busy = self._audio_channel.get_busy()
                    queue_status = self._audio_channel.get_queue()
                    
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
                                print(f"[MgbaEmulator] Audio latency correction: dropped {dropped} stale chunks")
                            if self.audio_queue:
                                chunk = self.audio_queue.popleft()
                        
                        if chunk is not None and len(chunk) > 0:
                            try:
                                sound = pygame.sndarray.make_sound(chunk)
                                
                                # If channel is not busy, use play() to start it
                                # If channel is busy but queue is empty, use queue() to line up next
                                if not is_busy:
                                    self._audio_channel.play(sound)
                                else:
                                    self._audio_channel.queue(sound)
                                
                                chunks_played += 1
                                last_play_time = time.time()
                                error_count = 0  # Reset on success
                            except Exception as e:
                                error_count += 1
                                if error_count < 5:
                                    print(f"[MgbaEmulator] Audio error: {e}")
                
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
                    slot_a_valid = (0 <= section_id_a <= 13)
                
                if len(data) >= 0xF000:
                    section_id_b = data[0xEFF4] | (data[0xEFF5] << 8)
                    slot_b_valid = (0 <= section_id_b <= 13)
                
                if not slot_a_valid and not slot_b_valid:
                    print(f"[MgbaEmulator] Warning: Save file appears blank (no valid slots)")
                    print(f"[MgbaEmulator] You can start a new game, existing save won't be overwritten")
                    return False
                
                copy_size = min(len(data), sram_size)
                ctypes.memmove(sram_ptr, data, copy_size)
                
                slot_info = []
                if slot_a_valid:
                    slot_info.append("A")
                if slot_b_valid:
                    slot_info.append("B")
                print(f"[MgbaEmulator] Loaded save: {os.path.basename(self.save_path)} ({copy_size} bytes, valid slots: {','.join(slot_info)})")
                
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
                slot_a_valid = (0 <= section_id_a <= 13)
            
            if len(data_bytes) >= 0xF000:
                section_id_b = data_bytes[0xEFF4] | (data_bytes[0xEFF5] << 8)
                slot_b_valid = (0 <= section_id_b <= 13)
            
            if not slot_a_valid and not slot_b_valid:
                print(f"[MgbaEmulator] BLOCKED: Would write blank save (no valid slots) to {os.path.basename(self.save_path)}")
                return False
            
            with open(self.save_path, "wb") as f:
                f.write(data_bytes)
            
            print(f"[MgbaEmulator] Saved: {os.path.basename(self.save_path)}")
            return True
        except Exception as e:
            print(f"[MgbaEmulator] Save failed: {e}")
            return False
    
    def run_frame(self):
        """Run one frame of emulation."""
        if not self.loaded or self.paused:
            return
        
        self.lib.retro_run()
        self._process_video()
    
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
        
        # Get absolute path for settings file
        if CONFIG_AVAILABLE and hasattr(config, 'SETTINGS_FILE'):
            settings_file = config.SETTINGS_FILE
        elif CONFIG_AVAILABLE and hasattr(config, 'BASE_DIR'):
            settings_file = os.path.join(config.BASE_DIR, "sinew_settings.json")
        else:
            settings_file = "sinew_settings.json"
        
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r") as f:
                    settings = json.load(f)
                    if "pause_combo" in settings:
                        return settings["pause_combo"]
        except:
            pass
        return default
    
    def check_pause_combo(self):
        """
        Check if the configured pause combo is held.
        
        Returns:
            bool: True if combo triggered (held for ~0.5 seconds)
        """
        if self._key_state is None:
            return False
        
        setting = getattr(self, '_pause_combo_setting', {"type": "combo", "buttons": ["START", "SELECT"]})
        combo_held = False
        
        if setting.get("type") == "custom":
            # Custom single button
            custom_btn = setting.get("button")
            if custom_btn is not None and self._joystick:
                try:
                    if custom_btn < self._joystick.get_numbuttons():
                        combo_held = self._joystick.get_button(custom_btn)
                except:
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
                    
                    # Map button names to gamepad indices
                    btn_map = {
                        "START": self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_START, 7),
                        "SELECT": self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_SELECT, 6),
                        "L": self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_L, 4),
                        "R": self._gamepad_map.get(RETRO_DEVICE_ID_JOYPAD_R, 5),
                    }
                    
                    for btn_name in required_buttons:
                        btn_idx = btn_map.get(btn_name)
                        if btn_idx is not None and btn_idx < num_buttons:
                            if self._joystick.get_button(btn_idx):
                                buttons_held[btn_name] = True
                except:
                    pass
            
            # Check if all required buttons are held
            combo_held = all(buttons_held.get(btn, False) for btn in required_buttons)
        
        if combo_held:
            self._start_held_frames += 1
            if self._start_held_frames >= self._pause_combo_frames:
                self._start_held_frames = 0
                return True
        else:
            self._start_held_frames = 0
        
        return False
    
    def toggle_pause(self):
        """Toggle pause state."""
        self.paused = not self.paused
        if self.paused:
            print("[MgbaEmulator] Paused - returning to Sinew")
            self.save_sram()  # Auto-save when pausing
        else:
            print("[MgbaEmulator] Resumed")
    
    def pause(self):
        """Pause emulation."""
        if not self.paused:
            self.paused = True
            self.save_sram()
            print("[MgbaEmulator] Paused")
    
    def resume(self):
        """Resume emulation."""
        if self.paused:
            print(f"[MgbaEmulator] Resuming... loaded={self.loaded}, paused={self.paused}")
            
            # Reload controller config in case it changed while paused
            self._load_controller_config()
            
            # Reinitialize audio (it may have been disrupted while paused)
            self._reinit_audio()
            
            self.paused = False
            print(f"[MgbaEmulator] Resumed - paused now={self.paused}")
    
    def _reinit_audio(self):
        """Ensure audio is working after pause/resume."""
        try:
            # Clear stale audio data
            with self._audio_lock:
                queue_size = len(self.audio_queue)
                self.audio_queue.clear()
                if queue_size > 0:
                    print(f"[MgbaEmulator] Cleared {queue_size} audio chunks from queue")
            
            # Get expected sample rate
            sample_rate = getattr(self, 'sample_rate', 32768)
            
            # Check if mixer is initialized at the correct frequency
            mixer_init = pygame.mixer.get_init()
            needs_full_reinit = False
            
            if not mixer_init:
                needs_full_reinit = True
                print(f"[MgbaEmulator] Mixer not initialized, will init at {sample_rate}Hz")
            elif mixer_init[0] != sample_rate:
                needs_full_reinit = True
                print(f"[MgbaEmulator] Mixer frequency mismatch: {mixer_init[0]} vs {sample_rate}")
            
            if needs_full_reinit:
                # Stop audio thread first
                self._audio_running = False
                if self._audio_thread and self._audio_thread.is_alive():
                    try:
                        self._audio_thread.join(timeout=0.5)
                    except:
                        pass
                self._audio_thread = None
                
                # Reinitialize mixer completely
                try:
                    pygame.mixer.quit()
                    pygame.time.wait(100)
                except:
                    pass
                
                pygame.mixer.pre_init(frequency=sample_rate, size=-16, channels=2, buffer=1024)
                pygame.mixer.init()
                pygame.mixer.set_num_channels(8)
                print(f"[MgbaEmulator] Mixer reinitialized: {pygame.mixer.get_init()}")
                
                # Get fresh channel and start new thread
                self._audio_channel = pygame.mixer.Channel(7)
                self._audio_channel.set_volume(1.0)
                
                self._audio_running = True
                self._audio_thread = threading.Thread(target=self._audio_thread_func, daemon=True)
                self._audio_thread.start()
                print("[MgbaEmulator] Audio thread started fresh")
            else:
                # Mixer is fine - just refresh channel reference and ensure thread is running
                pygame.mixer.set_num_channels(8)
                self._audio_channel = pygame.mixer.Channel(7)
                self._audio_channel.set_volume(1.0)
                
                # Make sure audio thread is running
                if self._audio_thread is None or not self._audio_thread.is_alive():
                    self._audio_running = True
                    self._audio_thread = threading.Thread(target=self._audio_thread_func, daemon=True)
                    self._audio_thread.start()
                    print("[MgbaEmulator] Audio thread restarted")
                # else thread is already running, it will resume automatically when paused=False
            
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
                except:
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
            except:
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
    
    # Get ROM path from config if available
    if CONFIG_AVAILABLE and hasattr(config, 'ROMS_DIR'):
        rom_path = os.path.join(config.ROMS_DIR, "Emerald.gba")
    else:
        rom_path = "roms/Emerald.gba"
    
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
            text = font.render("PAUSED - Hold Start+Select to resume", True, (255, 255, 0))
            rect = text.get_rect(center=(120 * SCALE, 80 * SCALE))
            screen.blit(text, rect)
        
        pygame.display.flip()
        clock.tick(emu.fps if emu.loaded else 60)
    
    emu.shutdown()
    pygame.quit()


if __name__ == "__main__":
    test_emulator()