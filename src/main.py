#!/usr/bin/env python3

"""
Sinew Game Screen - Integrated Version
"""

import json
import logging
import os
import sys
import time
import builtins
import platform as _platform
from datetime import datetime
from logging.handlers import RotatingFileHandler

# --- ARM Linux SDL2 preload (MUST happen before pygame import) ---
# The PyInstaller-bundled SDL2 lacks kmsdrm support on minimal CFWs (ROCKNIX, ArkOS, JELOS, etc.)
# Preloading the system SDL2 globally fixes display initialisation on handhelds.
# Falls back silently on systems that don't need it (AYN Thor, desktop Linux, Windows, macOS).
if sys.platform == 'linux' and _platform.machine().lower() in ('aarch64', 'arm64', 'armv7l', 'armv6l'):
    import ctypes as _ctypes
    _sdl2_paths = [
        '/usr/lib/libSDL2-2.0.so.0',
        '/usr/lib/libSDL2.so',
        '/usr/lib/aarch64-linux-gnu/libSDL2-2.0.so.0',
        '/usr/lib/arm-linux-gnueabihf/libSDL2-2.0.so.0',
        '/usr/local/lib/libSDL2.so',
    ]
    for _sdl2_path in _sdl2_paths:
        try:
            _ctypes.CDLL(_sdl2_path, mode=_ctypes.RTLD_GLOBAL)
            print(f"[Main] Preloaded system SDL2: {_sdl2_path}")
            break
        except OSError:
            continue
    else:
        print("[Main] System SDL2 not found in known paths, using bundled version")

import pygame
from PIL import Image, ImageSequence

import config
import ui_colors
from config import (
    CORES_DIR,
    DATA_DIR,
    EXT_DIR,
    FONT_PATH,
    IS_HANDHELD,
    MGBA_CORE_PATH,
    ROMS_DIR,
    SAVES_DIR,
    SETTINGS_FILE,
    SPRITES_DIR,
    SYSTEM_DIR,
    identify_rom,
)
from save_data_manager import get_manager, precache_save
from ui_components import Button

# =============================================================================
# LOGGING SETUP - Initialize before other imports to capture all output
# =============================================================================


def setup_logging():
    """
    Set up logging to file only.
    Creates sinew.log in the base directory with rotation.
    Console output is handled separately by the print redirector.
    """
    # Determine base directory for log file
    try:
        log_dir = EXT_DIR
    except ImportError:
        log_dir = os.path.dirname(os.path.abspath(__file__))

    log_file = os.path.join(log_dir, "sinew.log")

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # File handler with rotation (5MB max, keep 3 backups)
    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"  # 5MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create log file: {e}")

    # Note: No console handler - the LoggingPrintRedirector handles console output
    # Adding a console handler here would cause duplicate output

    return log_file


class LoggingPrintRedirector:
    """
    Redirects print() output to both console and log file.
    Intercepts sys.stdout to capture all print statements.
    """

    # Patterns to suppress from both console and log (verbose debug spam)
    SUPPRESS_PATTERNS = [
        "[PC] Species conversion:",
        "[SaveData] Species conversion:",
        "Species conversion:",
    ]

    def __init__(self, original_stdout, logger):
        self.original_stdout = original_stdout
        self.logger = logger
        self.buffer = ""

    def _should_suppress(self, line):
        """Check if a line should be suppressed from output."""
        for pattern in self.SUPPRESS_PATTERNS:
            if pattern in line:
                return True
        return False

    def write(self, text):
        # Buffer text and process complete lines
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():  # Only process non-empty lines
                # Skip verbose debug messages entirely
                if self._should_suppress(line):
                    continue
                # Write to original stdout (console)
                if self.original_stdout:
                    self.original_stdout.write(line + "\n")
                # Log to file
                self.logger.info(line.rstrip())

    def flush(self):
        if self.original_stdout:
            self.original_stdout.flush()
        # Flush any remaining buffer
        if self.buffer.strip():
            if not self._should_suppress(self.buffer):
                if self.original_stdout:
                    self.original_stdout.write(self.buffer)
                self.logger.info(self.buffer.rstrip())
            self.buffer = ""


# Initialize logging
_log_file_path = setup_logging()
_sinew_logger = logging.getLogger("sinew")

# Redirect stdout to capture print statements
_original_stdout = sys.stdout
sys.stdout = LoggingPrintRedirector(_original_stdout, _sinew_logger)

# Also capture stderr for error messages
_original_stderr = sys.stderr
_stderr_logger = logging.getLogger("sinew.error")
sys.stderr = LoggingPrintRedirector(_original_stderr, _stderr_logger)

# Log startup
_sinew_logger.info("=" * 60)
_sinew_logger.info(f"Sinew starting - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
_sinew_logger.info(f"Log file: {_log_file_path}")
_sinew_logger.info(f"Python: {sys.version}")
_sinew_logger.info(f"Platform: {sys.platform}")
_sinew_logger.info("=" * 60)

# SDL hints for audio stability in fullscreen mode
# Set these before importing pygame
os.environ.setdefault("SDL_AUDIO_ALLOW_CHANGES", "0")  # Prevent audio format changes
if sys.platform == "win32" and not getattr(sys, "frozen", False):
    # Windows dev mode: prefer directsound for stability with fullscreen.
    # Skip when frozen (PyInstaller) — let SDL auto-select; forcing directsound
    # can fail if the driver DLL isn't found in the temp extraction folder.
    os.environ.setdefault("SDL_AUDIODRIVER", "directsound")

# Try to import modals
try:
    from pc_box import PCBox
except ImportError:
    PCBox = None

try:
    from trainerinfo import Modal as TrainerInfoModal
except ImportError:
    TrainerInfoModal = None

try:
    from Itembag import Modal as ItemBagModal
except ImportError:
    ItemBagModal = None

try:
    from achievements import Modal as AchievementsModal
    from achievements import (
        get_achievement_notification,
        init_achievement_system,
    )
except ImportError:
    AchievementsModal = None
    init_achievement_system = None
    get_achievement_notification = None

try:
    from settings import Settings
except ImportError:
    Settings = None

try:
    from db_builder_screen import DBBuilder
except ImportError:
    DBBuilder = None

try:
    from PokedexModal import PokedexModal
except ImportError:
    PokedexModal = None

try:
    from export_modal import ExportModal
except ImportError:
    ExportModal = None

try:
    from events_screen import EventsModal, is_events_unlocked
except ImportError:
    EventsModal = None
    is_events_unlocked = None

# Import integrated mGBA emulator
try:
    from mgba_emulator import MgbaEmulator, find_core_path, get_platform_core_extension

    EMULATOR_AVAILABLE = True
except ImportError:
    MgbaEmulator = None
    find_core_path = None
    get_platform_core_extension = None
    EMULATOR_AVAILABLE = False
    print("Warning: mgba_emulator not available, will use external mGBA")

# Menu items for individual games (Export instead of Settings)
GAME_MENU_ITEMS = [
    "Launch Game",
    "Pokedex",
    "Trainer Info",
    "PC Box",
    "Achievements",
    "Events",
    "Settings",
    "Export",
]

# Menu items for Sinew home screen (NO Events here - only per-game)
SINEW_MENU_ITEMS = ["Pokedex", "PC Box", "Achievements", "Settings"]

# Game definitions with keywords for flexible ROM detection
# Keywords are checked against lowercase filename (without extension)
# More specific keywords should come first to avoid false matches
GAME_DEFINITIONS = {
    "Ruby": {
        "title_gif": os.path.join(SPRITES_DIR, "title", "ruby.gif"),
        "keywords": ["ruby"],
        "exclude": ["omega"],  # Exclude Omega Ruby (3DS)
    },
    "Sapphire": {
        "title_gif": os.path.join(SPRITES_DIR, "title", "sapphire.gif"),
        "keywords": ["sapphire"],
        "exclude": ["alpha"],  # Exclude Alpha Sapphire (3DS)
    },
    "Emerald": {
        "title_gif": os.path.join(SPRITES_DIR, "title", "emerald.gif"),
        "keywords": ["emerald"],
        "exclude": [],
    },
    "FireRed": {
        "title_gif": os.path.join(SPRITES_DIR, "title", "firered.gif"),
        "keywords": ["firered", "fire red", "fire_red"],
        "exclude": [],
    },
    "LeafGreen": {
        "title_gif": os.path.join(SPRITES_DIR, "title", "leafgreen.gif"),
        "keywords": ["leafgreen", "leaf green", "leaf_green"],
        "exclude": [],
    },
}


# Module-level ROM scan cache: populated once per directory on first call.
# Maps roms_dir -> {rom_path -> game_name | None}
# Avoids re-hashing every .gba file for each of the five game lookups.
_rom_scan_cache = {}  # roms_dir -> {rom_path -> game_name | None}


def _build_rom_scan_cache(roms_dir):
    """
    Scan roms_dir once, hash every .gba, cache results.
    No-op if already scanned. Supports multiple directories independently.
    """
    if roms_dir in _rom_scan_cache:
        return

    scan = {}

    if not os.path.exists(roms_dir):
        _rom_scan_cache[roms_dir] = scan
        return

    for filename in os.listdir(roms_dir):
        if not filename.lower().endswith((".gba", ".zip", ".7z")):
            continue
        rom_path = os.path.join(roms_dir, filename)
        scan[rom_path] = identify_rom(rom_path) if filename.lower().endswith(".gba") else None

    _rom_scan_cache[roms_dir] = scan
    print(f"[GameScreen] ROM scan complete: {len(scan)} files in {roms_dir}")


def find_rom_for_game(game_name, roms_dir):
    """
    Search for a ROM file matching the given game name.

    Detection order:
      1. ROM scan cache (hash + header) - built once per directory
      2. Filename keyword fallback - for zips or unrecognised ROMs

    Args:
        game_name: Name of the game (e.g., "FireRed")
        roms_dir: Directory to search for ROMs

    Returns:
        tuple: (rom_path, save_path) or (None, None) if not found
    """
    if game_name not in GAME_DEFINITIONS:
        return None, None

    game_def = GAME_DEFINITIONS[game_name]
    keywords = game_def.get("keywords", [])
    exclude = game_def.get("exclude", [])

    if not os.path.exists(roms_dir):
        return None, None

    # Ensure directory has been scanned (no-op if already done)
    _build_rom_scan_cache(roms_dir)

    keyword_fallback = None

    for rom_path, detected in _rom_scan_cache[roms_dir].items():
        filename = os.path.basename(rom_path)
        name_lower = filename.lower()
        base_name = os.path.splitext(filename)[0]

        # Cache hit
        if detected == game_name:
            sav_path = os.path.join(SAVES_DIR, base_name + ".sav")
            print(f"[GameScreen] ROM match {game_name}: {filename}")
            return rom_path, sav_path

        # Keyword fallback for zips and unrecognised .gba files
        if keyword_fallback is None and detected is None:
            if any(ex.lower() in name_lower for ex in exclude):
                continue
            for keyword in keywords:
                if keyword.lower() in name_lower:
                    sav_path = os.path.join(SAVES_DIR, base_name + ".sav")
                    keyword_fallback = (rom_path, sav_path)
                    break

    if keyword_fallback:
        print(f"[GameScreen] Keyword match {game_name}: {os.path.basename(keyword_fallback[0])}")
        return keyword_fallback

    return None, None


def find_save_for_game(game_name, saves_dir):
    """
    Search the saves directory for a .sav file matching the game's keywords.
    Used as a fallback when no ROM is found, so save-only games are detected.

    Args:
        game_name: Name of the game (e.g., "FireRed")
        saves_dir: Directory to search for .sav files

    Returns:
        str or None: Path to the first matching .sav file, or None
    """
    if game_name not in GAME_DEFINITIONS:
        return None

    game_def = GAME_DEFINITIONS[game_name]
    keywords = game_def.get("keywords", [])
    exclude = game_def.get("exclude", [])

    if not os.path.exists(saves_dir):
        return None

    for filename in os.listdir(saves_dir):
        if not filename.lower().endswith(".sav"):
            continue

        name_lower = filename.lower()

        # Check exclusions
        if any(ex.lower() in name_lower for ex in exclude):
            continue

        # Check keywords
        for keyword in keywords:
            if keyword.lower() in name_lower:
                sav_path = os.path.join(saves_dir, filename)
                print(f"[GameScreen] Found save-only {game_name}: {filename}")
                return sav_path

    return None


def detect_games():
    """
    Detect all available games by scanning the ROMs and saves directories.

    A game is included if it has a ROM, a save, or both.
    Games with neither are omitted entirely (filtered later by availability).

    Returns:
        dict: Game configurations with detected ROM/save paths
    """
    games = {
        "Sinew": {"title_gif": None, "rom": None, "sav": None, "is_sinew": True},
    }

    for game_name, game_def in GAME_DEFINITIONS.items():
        rom_path, sav_path = find_rom_for_game(game_name, ROMS_DIR)

        # If no ROM was found, still look for a matching save file independently
        if rom_path is None:
            sav_path = find_save_for_game(game_name, SAVES_DIR)
        games[game_name] = {
            "title_gif": game_def["title_gif"],
            "rom": rom_path,
            "sav": sav_path,
        }

    return games


# ---------------------------------------------------------------------------
# Game Availability
# ---------------------------------------------------------------------------
# Three-state availability for a game entry.
# UNAVAILABLE : no ROM and no save  → hide from all menus/navigation entirely
# SAVE_ONLY   : save found, but no ROM → show in menus but Launch is disabled
# FULL        : ROM found (save may or may not exist) → normal behaviour
# Adding a new game type (e.g. a ROM hack) only requires adding it to
# GAME_DEFINITIONS; availability is derived automatically from these states.

GAME_UNAVAILABLE = "unavailable"
GAME_SAVE_ONLY = "save_only"
GAME_FULL = "full"


def get_game_availability(game_data):
    """
    Return the availability state for a single game_data dict.

    Args:
        game_data: dict with optional keys 'rom' (path) and 'sav' (path)

    Returns:
        str: One of GAME_UNAVAILABLE, GAME_SAVE_ONLY, GAME_FULL
    """
    # Sinew itself is always available (it has no ROM/save of its own)
    if game_data.get("is_sinew"):
        return GAME_FULL

    has_rom = bool(game_data.get("rom") and os.path.exists(game_data["rom"]))
    has_sav = bool(game_data.get("sav") and os.path.exists(game_data["sav"]))

    if has_rom:
        return GAME_FULL
    if has_sav:
        return GAME_SAVE_ONLY
    return GAME_UNAVAILABLE


# Detect games on module load
GAMES = detect_games()


def load_settings():
    """Load settings from sinew_settings.json"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_settings_file(data):
    """Save settings to sinew_settings.json"""
    # Ensure the directory exists (e.g. saves/sinew/ may not exist on first run)
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    # Merge with existing settings to preserve other data
    existing = load_settings()
    existing.update(data)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def load_gif_frames(path, width, height):
    """Load GIF frames scaled to specified size"""
    frames, durations = [], []
    if not path or not os.path.exists(path):
        return frames, durations
    try:
        pil_img = Image.open(path)
        for frame in ImageSequence.Iterator(pil_img):
            frame = frame.convert("RGBA").resize((width, height), Image.NEAREST)
            data = frame.tobytes()
            surf = pygame.image.fromstring(data, frame.size, frame.mode).convert_alpha()
            frames.append(surf)
            durations.append(frame.info.get("duration", 100))
        pil_img.close()
    except Exception as e:
        print(f"Failed to open GIF {path}: {e}")
    return frames, durations


class PlaceholderModal:
    """Placeholder for unimplemented modals"""

    def __init__(self, title, width, height, font, close_callback):
        self.width = width
        self.height = height
        self.title = title
        self.font = font
        self.close_callback = close_callback
        self.back_button = Button(
            "Back", rel_rect=(0.75, 0.02, 0.22, 0.08), callback=close_callback
        )

    def update(self, events):
        for event in events:
            self.back_button.handle_event(event)
        return True

    def draw(self, surf):
        surf.fill(ui_colors.COLOR_BG)
        txt = self.font.render(self.title, True, ui_colors.COLOR_TEXT)
        surf.blit(txt, (16, 16))
        self.back_button.draw(surf, self.font)

    def handle_mouse(self, event):
        return self.back_button.handle_event(event)

    def handle_controller(self, ctrl):
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.close_callback()
            return True
        return False


class DBWarningPopup:
    """Popup warning about missing/incomplete Pokemon database"""

    def __init__(
        self,
        width,
        height,
        title,
        message,
        build_callback=None,
        close_callback=None,
        screen_size=None,
    ):
        self.width = width
        self.height = height
        self.title = title
        self.message = message
        self.build_callback = build_callback
        self.close_callback = close_callback
        self.visible = True
        self.screen_size = screen_size  # (screen_width, screen_height) for mouse offset

        # Button state
        self.selected_button = 0  # 0 = Build Now, 1 = Later
        self.buttons = ["Build Now", "Later"]

        # Debounce
        self._last_click_time = 0
        self._click_debounce_ms = 300

        # Fonts
        try:
            self.font_title = pygame.font.Font(FONT_PATH, 14)
            self.font_text = pygame.font.Font(FONT_PATH, 10)
            self.font_button = pygame.font.Font(FONT_PATH, 11)
        except Exception:
            self.font_title = pygame.font.SysFont(None, 20)
            self.font_text = pygame.font.SysFont(None, 16)
            self.font_button = pygame.font.SysFont(None, 18)

    def _get_screen_offset(self):
        """Get the offset of this popup on screen (for mouse coordinate translation)"""
        if self.screen_size:
            screen_w, screen_h = self.screen_size
            offset_x = (screen_w - self.width) // 2
            offset_y = (screen_h - self.height) // 2
            return offset_x, offset_y
        return 0, 0

    def update(self, events):
        current_time = pygame.time.get_ticks()
        offset_x, offset_y = self._get_screen_offset()

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._close()
                elif event.key == pygame.K_RETURN:
                    if current_time - self._last_click_time > self._click_debounce_ms:
                        self._last_click_time = current_time
                        self._activate_button()
                elif event.key == pygame.K_LEFT:
                    self.selected_button = max(0, self.selected_button - 1)
                elif event.key == pygame.K_RIGHT:
                    self.selected_button = min(
                        len(self.buttons) - 1, self.selected_button + 1
                    )

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if current_time - self._last_click_time < self._click_debounce_ms:
                        continue

                    # Translate mouse position to popup-local coordinates
                    local_pos = (event.pos[0] - offset_x, event.pos[1] - offset_y)

                    button_rects = self._get_button_rects()
                    for i, rect in enumerate(button_rects):
                        if rect.collidepoint(local_pos):
                            self._last_click_time = current_time
                            self.selected_button = i
                            self._activate_button()
                            break

        return self.visible

    def handle_controller(self, ctrl):
        if not ctrl:
            return

        current_time = pygame.time.get_ticks()

        if ctrl.is_dpad_just_pressed("left"):
            self.selected_button = max(0, self.selected_button - 1)
        elif ctrl.is_dpad_just_pressed("right"):
            self.selected_button = min(len(self.buttons) - 1, self.selected_button + 1)

        if ctrl.is_button_just_pressed("A"):
            if current_time - self._last_click_time > self._click_debounce_ms:
                self._last_click_time = current_time
                self._activate_button()

        if ctrl.is_button_just_pressed("B"):
            self._close()

    def _activate_button(self):
        if self.selected_button == 0:
            # Build Now
            if self.build_callback:
                self.build_callback()
        else:
            # Later
            self._close()

    def _close(self):
        self.visible = False
        if self.close_callback:
            self.close_callback()

    def _get_button_rects(self):
        # Match the positioning in draw()
        # Approximate: title at top, message in middle, buttons below
        # For a 180px height popup, buttons should be near the bottom
        button_y = self.height - 50
        button_width = 100
        button_height = 30
        button_spacing = 20
        total_width = (
            len(self.buttons) * button_width + (len(self.buttons) - 1) * button_spacing
        )
        start_x = (self.width - total_width) // 2

        rects = []
        for i in range(len(self.buttons)):
            btn_x = start_x + i * (button_width + button_spacing)
            rects.append(pygame.Rect(btn_x, button_y, button_width, button_height))
        return rects

    def draw(self, surf):
        # Semi-transparent background
        surf.fill(ui_colors.COLOR_BG)

        # Title - centered near top
        title_y = 20
        title_surf = self.font_title.render(self.title, True, ui_colors.COLOR_ERROR)
        title_rect = title_surf.get_rect(centerx=self.width // 2, top=title_y)
        surf.blit(title_surf, title_rect)

        # Message - word wrap, centered
        message_y = title_rect.bottom + 15
        words = self.message.split()
        lines = []
        current_line = []
        max_width = self.width - 40

        for word in words:
            current_line.append(word)
            test_text = " ".join(current_line)
            test_surf = self.font_text.render(test_text, True, ui_colors.COLOR_TEXT)
            if test_surf.get_width() > max_width:
                current_line.pop()
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        for line in lines:
            line_surf = self.font_text.render(line, True, ui_colors.COLOR_TEXT)
            line_rect = line_surf.get_rect(centerx=self.width // 2, top=message_y)
            surf.blit(line_surf, line_rect)
            message_y += 16

        # Buttons - use same positioning as _get_button_rects
        button_rects = self._get_button_rects()
        for i, (btn_text, rect) in enumerate(
            zip(self.buttons, button_rects, strict=False)
        ):
            if i == self.selected_button:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON_HOVER, rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, rect, 3)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, rect, 2)

            text_surf = self.font_button.render(btn_text, True, ui_colors.COLOR_TEXT)
            text_rect = text_surf.get_rect(center=rect.center)
            surf.blit(text_surf, text_rect)


class GameScreen:
    """
    Game selection and management screen
    Displays animated title GIFs and provides access to game features
    Sinew is the first entry - a combined view of all saves
    """

    # Input debouncing cooldown (seconds)
    INPUT_COOLDOWN = 0.25

    def __init__(
        self, width, height, font, back_callback=None, controller=None, scaler=None,
        screen=None
    ):
        self.width = width
        self.height = height
        self.font = font
        self.back_callback = back_callback
        self.controller = controller
        self.scaler = scaler  # Optional scaler for resolution scaling
        self._loading_screen = screen  # Surface for startup loading screen

        # Load settings
        self.settings = load_settings()

        # Initialize dev mode builtins from persisted settings
        import builtins

        if not hasattr(builtins, "SINEW_DEV_MODE"):
            builtins.SINEW_DEV_MODE = self.settings.get("dev_mode", False)
        if not hasattr(builtins, "SINEW_USE_EXTERNAL_EMULATOR"):
            builtins.SINEW_USE_EXTERNAL_EMULATOR = self.settings.get(
                "use_external_emulator", False
            )

        # Instantiate ExternalEmulator once — reused for ROM scanning and launching.
        # Falls back gracefully if external_emulator.py isn't present.
        self.external_emu = None
        try:
            from external_emulator import ExternalEmulator

            self.external_emu = ExternalEmulator()
            if self.external_emu.active_provider:
                print(
                    f"[ExternalEmu] Provider ready: {type(self.external_emu.active_provider).__name__}"
                )
            else:
                print("[ExternalEmu] No provider matched this environment")
        except ImportError:
            print(
                "[ExternalEmu] external_emulator.py not found — external emulator unavailable"
            )

        # Load pause combo setting
        self._load_pause_combo_setting()

        # Load saved theme preference
        try:
            from theme_manager import load_theme_preference

            load_theme_preference()
        except Exception as e:
            print(f"[GameScreen] Could not load theme: {e}")

        # Initialize menu music
        self._init_menu_music()

        # Initialize games data
        self.games = {}
        self.game_names = []
        self._init_games()

        # State
        self.current_game = 0  # Starts on Sinew (index 0)
        self.menu_index = 0
        self.modal_instance = None
        self.should_close = False

        # Emulator state
        self.emulator = None
        self.emulator_active = False
        self._emulator_pause_combo_released = True  # Track if combo was released

        # External emulator dev mode state
        self._ext_sav_path = None  # Live save in the external emu's saves folder
        self._sinew_backup_sav_path = None  # Sinew's own saves/ copy (read by editors)
        self._ext_emu_closed_needs_reload = (
            False  # Set by bg thread; acted on in update()
        )

        # Notification state (slide-down box)
        self._notification_text = None
        self._notification_subtext = None
        self._notification_timer = 0
        self._notification_duration = 3000  # 3 seconds
        self._notification_y = -60  # Start above screen
        self._notification_target_y = 10  # Slide to this position

        # Resume game banner state (dropdown from top)
        self._resume_banner_scroll_offset = 0
        self._resume_banner_scroll_speed = 1.5  # pixels per frame
        self._resume_banner_pulse_time = 0

        # Input debouncing
        self._last_input_time = time.time()  # Start with cooldown active
        self._modal_just_closed = False  # Track if modal was closed this frame

        # Precache state
        self._precached = False

        # Show startup loading screen as early as possible
        self._draw_loading_screen(self._loading_screen, "Starting up...", 0, 3)

        # Load initial save + background
        # Use the combined loader so GIF frames + save are ready
        self._draw_loading_screen(self._loading_screen, "Loading save data...", 1, 3)
        self.load_game_and_background()

        # Start menu music after everything is loaded
        self._start_menu_music()

        # Check database completeness
        self._draw_loading_screen(self._loading_screen, "Checking database...", 2, 3)
        self._check_database()

        # Initialize achievement system (no startup scan - checks happen on drop-back)
        self._init_achievement_system()

    def _init_achievement_system(self):
        """Initialize the achievement notification system"""
        self._achievement_notification = None
        self._achievement_manager = None

        if init_achievement_system:
            try:
                self._achievement_manager, self._achievement_notification = (
                    init_achievement_system(self.width)
                )
                print("[GameScreen] Achievement system initialized")

                # Cache for Sinew aggregate: {game_name: contribution_dict}
                # Only the game that just changed is re-parsed; others use cached values.
                self._sinew_game_data_cache = {}
            except Exception as e:
                print(f"[GameScreen] Could not initialize achievements: {e}")

    def _check_all_achievements_on_startup(self):
        """Check achievements on startup - only parses the current (last active) game.
        Other games are handled lazily by _check_sinew_achievements_aggregate which
        uses per-game caching and only re-parses the game that changed."""
        if not self._achievement_manager:
            return

        # Determine current game from config SAVE_PATHS order
        current_game_name = (
            self.game_names[self.current_game]
            if self.game_names and self.current_game < len(self.game_names)
            else None
        )
        print(f"[Achievements] Startup check for current game: {current_game_name}")

        try:
            if current_game_name and current_game_name != "Sinew":
                game_data = self.games.get(current_game_name, {})
                # Use canonical save path from config as source of truth
                from config import SAVE_PATHS
                sav_path = SAVE_PATHS.get(current_game_name, game_data.get("sav"))

                if sav_path and os.path.exists(sav_path):
                    try:
                        from save_data_manager import SaveDataManager
                        from achievements_data import check_achievement_unlocked, get_achievements_for

                        manager = SaveDataManager()
                        if manager.load_save(sav_path, game_hint=current_game_name):
                            loaded_game = (
                                manager.parser.game_code
                                if hasattr(manager, "parser") and manager.parser
                                else "unknown"
                            )
                            print(f"[Achievements] {current_game_name} loaded - game_code: {loaded_game}")

                            pokedex_data = (
                                manager.get_pokedex_count()
                                if hasattr(manager, "get_pokedex_count")
                                else {"caught": 0, "seen": 0}
                            )
                            party = manager.get_party() if hasattr(manager, "get_party") else []

                            if party:
                                for p in party:
                                    if p and not p.get("empty"):
                                        print(f"[Achievements] Startup {current_game_name} party[0]: level={p.get('level', 'NO LEVEL')}, species={p.get('species', '?')}")
                                        break

                            pc_pokemon = []
                            try:
                                for box_num in range(1, 15):
                                    if hasattr(manager, "get_box"):
                                        box = manager.get_box(box_num)
                                        if box:
                                            for p in box:
                                                if p and not p.get("empty"):
                                                    pc_pokemon.append(p)
                                if pc_pokemon:
                                    first = pc_pokemon[0]
                                    print(f"[Achievements] Startup {current_game_name} first PC Pokemon level: {first.get('level', 'NO LEVEL KEY')}")
                            except Exception as e:
                                print(f"[Achievements] Startup {current_game_name} PC load error: {e}")

                            owned_list = []
                            try:
                                if hasattr(manager, "get_pokedex_data"):
                                    pokedex = manager.get_pokedex_data()
                                    owned_list = pokedex.get("owned_list", [])
                            except Exception:
                                pass

                            playtime_hours = 0
                            try:
                                playtime = manager.get_play_time() if hasattr(manager, "get_play_time") else {}
                                playtime_hours = (playtime.get("hours", 0) or 0) + ((playtime.get("minutes", 0) or 0) / 60.0)
                            except Exception:
                                pass

                            ach_save_data = {
                                "dex_caught": pokedex_data.get("caught", 0),
                                "dex_seen": pokedex_data.get("seen", 0),
                                "badges": manager.get_badge_count() if hasattr(manager, "get_badge_count") else 0,
                                "money": manager.get_money() if hasattr(manager, "get_money") else 0,
                                "party": party,
                                "pc_pokemon": pc_pokemon,
                                "owned_list": owned_list,
                                "playtime_hours": playtime_hours,
                            }

                            game_achievements = get_achievements_for(current_game_name)
                            pc_count = len([p for p in pc_pokemon if p and not p.get("empty")])
                            party_count = len([p for p in party if p and not p.get("empty")])

                            def _is_shiny(pokemon):
                                if pokemon.get("is_shiny") or pokemon.get("shiny", False):
                                    return True
                                if not pokemon or pokemon.get("empty") or pokemon.get("egg"):
                                    return False
                                personality = pokemon.get("personality", 0)
                                ot_id = pokemon.get("ot_id", 0)
                                if personality == 0 or ot_id == 0:
                                    return False
                                tid = ot_id & 0xFFFF
                                sid = (ot_id >> 16) & 0xFFFF
                                return (tid ^ sid ^ (personality & 0xFFFF) ^ ((personality >> 16) & 0xFFFF)) < 8

                            all_pokemon = [p for p in party + pc_pokemon if p and not p.get("empty")]
                            max_level = max((p.get("level", 0) for p in all_pokemon), default=0)
                            pokemon_over_30 = sum(1 for p in all_pokemon if p.get("level", 0) >= 30)
                            pokemon_over_50 = sum(1 for p in all_pokemon if p.get("level", 0) >= 50)
                            pokemon_over_70 = sum(1 for p in all_pokemon if p.get("level", 0) >= 70)
                            pokemon_at_100 = sum(1 for p in all_pokemon if p.get("level", 0) >= 100)
                            shiny_count = sum(1 for p in all_pokemon if _is_shiny(p))

                            print(f"[Achievements] Startup {current_game_name}: dex={ach_save_data['dex_caught']}, badges={ach_save_data['badges']}, pc={pc_count}, party={party_count}, max_lv={max_level}")

                            # Log any legendaries found
                            legendary_ids = [144,145,146,150,151,377,378,379,380,381,382,383,384,385,386]
                            found_legendaries = [s for s in legendary_ids if s in owned_list]
                            if found_legendaries:
                                print(f"[Achievements] Startup {current_game_name} has legendaries: {found_legendaries}")

                            # Update per-game tracking
                            self._achievement_manager.set_current_game(current_game_name)
                            self._achievement_manager.update_tracking("dex_count", ach_save_data["dex_caught"])
                            self._achievement_manager.update_tracking("dex_seen", ach_save_data["dex_seen"])
                            self._achievement_manager.update_tracking("badges", ach_save_data["badges"])
                            self._achievement_manager.update_tracking("money", ach_save_data["money"])
                            self._achievement_manager.update_tracking("playtime_hours", playtime_hours)
                            self._achievement_manager.update_tracking("party_size", party_count)
                            self._achievement_manager.update_tracking("pc_pokemon", pc_count)
                            self._achievement_manager.update_tracking("total_pokemon", pc_count + party_count)
                            self._achievement_manager.update_tracking("any_pokemon_level", max_level)
                            self._achievement_manager.update_tracking("pokemon_over_30", pokemon_over_30)
                            self._achievement_manager.update_tracking("pokemon_over_50", pokemon_over_50)
                            self._achievement_manager.update_tracking("pokemon_over_70", pokemon_over_70)
                            self._achievement_manager.update_tracking("pokemon_at_100", pokemon_at_100)
                            self._achievement_manager.update_tracking("shiny_count", shiny_count)
                            self._achievement_manager.update_tracking("owned_set", set(owned_list))

                            unlocked_count = 0
                            for ach in game_achievements:
                                if ach.get("game") != current_game_name:
                                    continue
                                if not self._achievement_manager.is_unlocked(ach["id"]):
                                    if check_achievement_unlocked(ach, ach_save_data):
                                        self._achievement_manager.progress[ach["id"]] = {
                                            "unlocked": True,
                                            "unlocked_at": time.time(),
                                            "reward_claimed": False,
                                        }
                                        self._achievement_manager.stats["total_unlocked"] = (
                                            self._achievement_manager.stats.get("total_unlocked", 0) + 1
                                        )
                                        self._achievement_manager.stats["total_points"] = (
                                            self._achievement_manager.stats.get("total_points", 0) + ach.get("points", 0)
                                        )
                                        unlocked_count += 1

                            if unlocked_count > 0:
                                print(f"[Achievements] Startup: {current_game_name} - {unlocked_count} achievements unlocked")

                    except Exception as e:
                        print(f"[Achievements] Startup error for {current_game_name}: {e}")
                else:
                    print(f"[Achievements] Skipping {current_game_name} - no save file")

            # Sinew aggregate: populates cache for ALL games (each only parsed once,
            # subsequent calls only re-parse the game that changed).
            self._check_sinew_achievements_aggregate()

            # Re-validate and save
            revoked = self._achievement_manager.revalidate_achievements()
            if revoked:
                print(f"[Achievements] Revoked {len(revoked)} incorrectly unlocked achievements on startup")

            self._achievement_manager._save_progress()

            # Restore context to current game
            if current_game_name and current_game_name != "Sinew":
                self._load_current_save()

            print("[Achievements] Startup check complete")

        except Exception as e:
            print(f"[Achievements] Startup check error: {e}")
            import traceback
            traceback.print_exc()

    def _check_achievements_for_current_game(self):
        """Check achievements based on current game's save data"""
        if not self._achievement_manager:
            return

        def is_pokemon_shiny(pokemon):
            """Calculate if a Pokemon is shiny from TID/SID/PID"""
            # First check if already set
            if pokemon.get("is_shiny") or pokemon.get("shiny", False):
                return True

            if not pokemon or pokemon.get("empty") or pokemon.get("egg"):
                return False

            personality = pokemon.get("personality", 0)
            ot_id = pokemon.get("ot_id", 0)

            if personality == 0 or ot_id == 0:
                return False

            # Extract trainer ID and secret ID
            tid = ot_id & 0xFFFF
            sid = (ot_id >> 16) & 0xFFFF

            # Extract PID high and low
            pid_low = personality & 0xFFFF
            pid_high = (personality >> 16) & 0xFFFF

            # Calculate shiny value
            shiny_value = tid ^ sid ^ pid_low ^ pid_high

            # Pokemon is shiny if value < 8
            return shiny_value < 8

        try:
            # Get current game name
            game_name = self.get_current_game_name()
            if not game_name or game_name == "Sinew":
                # Even on Sinew screen, check Sinew achievements with aggregate data
                self._check_sinew_achievements_aggregate()
                return

            # Get save data from manager
            manager = get_manager()
            if not manager or not manager.loaded:
                return

            # Build achievement-compatible save data dict from manager
            pokedex_data = (
                manager.get_pokedex_count()
                if hasattr(manager, "get_pokedex_count")
                else {"caught": 0, "seen": 0}
            )

            # Get party Pokemon
            party = manager.get_party() if hasattr(manager, "get_party") else []

            # Get PC Pokemon (all boxes) - use get_box for properly enriched data
            pc_pokemon = []
            try:
                # Iterate through all 14 boxes
                for box_num in range(1, 15):
                    if hasattr(manager, "get_box"):
                        box = manager.get_box(box_num)
                        if box:
                            for p in box:
                                if p and not p.get("empty"):
                                    pc_pokemon.append(p)
                print(
                    f"[Achievements] {game_name} PC Pokemon: {len(pc_pokemon)} from 14 boxes"
                )
                # Debug: show first PC Pokemon structure
                if pc_pokemon:
                    first = pc_pokemon[0]
                    print(
                        f"[Achievements] First PC Pokemon keys: {list(first.keys()) if isinstance(first, dict) else type(first)}"
                    )
            except Exception as e:
                print(f"[Achievements] Error getting PC Pokemon: {e}")
                import traceback

                traceback.print_exc()

            # Get owned list from pokedex
            owned_list = []
            try:
                if hasattr(manager, "get_pokedex_data"):
                    pokedex = manager.get_pokedex_data()
                    owned_list = pokedex.get("owned_list", [])
                    print(
                        f"[Achievements] {game_name} owned_list: {len(owned_list)} species"
                    )
            except Exception as e:
                print(f"[Achievements] Error getting owned_list: {e}")

            ach_save_data = {
                "dex_caught": pokedex_data.get("caught", 0),
                "dex_seen": pokedex_data.get("seen", 0),
                "badges": (
                    manager.get_badge_count()
                    if hasattr(manager, "get_badge_count")
                    else 0
                ),
                "money": manager.get_money() if hasattr(manager, "get_money") else 0,
                "party": party,
                "pc_pokemon": pc_pokemon,
                "owned_list": owned_list,
            }

            # Add raw_data for FRLG Sevii achievement checking
            if (
                hasattr(manager, "parser")
                and manager.parser
                and hasattr(manager.parser, "data")
            ):
                ach_save_data["raw_data"] = manager.parser.data

                # Pre-check FRLG prerequisites for Sevii Pokemon Ranger achievement
                game_name = self.get_current_game_name()
                if game_name in ("FireRed", "LeafGreen"):
                    try:
                        from save_writer import has_national_dex as check_nat_dex
                        from save_writer import has_rainbow_pass as check_rainbow

                        # IMPORTANT: Pass 'FRLG' as game_type, not the game_name
                        ach_save_data["has_national_dex"] = check_nat_dex(
                            manager.parser.data, "FRLG", game_name
                        )
                        ach_save_data["has_rainbow_pass"] = check_rainbow(
                            manager.parser.data, "FRLG"
                        )
                        print(
                            f"[Achievements] {game_name} Sevii prereqs: nat_dex={ach_save_data['has_national_dex']}, rainbow_pass={ach_save_data['has_rainbow_pass']}"
                        )
                    except Exception as e:
                        print(f"[Achievements] Error checking FRLG Sevii prereqs: {e}")
                        import traceback

                        traceback.print_exc()
                        ach_save_data["has_national_dex"] = False
                        ach_save_data["has_rainbow_pass"] = False

            # Get playtime if available
            if hasattr(manager, "get_play_time"):
                try:
                    playtime = manager.get_play_time()
                    hours = playtime.get("hours", 0) or 0
                    minutes = playtime.get("minutes", 0) or 0
                    ach_save_data["playtime_hours"] = hours + (minutes / 60.0)
                except Exception:
                    ach_save_data["playtime_hours"] = 0
            elif hasattr(manager, "parser") and manager.parser:
                try:
                    hours = getattr(manager.parser, "play_hours", 0) or 0
                    minutes = getattr(manager.parser, "play_minutes", 0) or 0
                    ach_save_data["playtime_hours"] = hours + (minutes / 60.0)
                except Exception:
                    ach_save_data["playtime_hours"] = 0

            playtime_h = ach_save_data.get("playtime_hours", 0)
            pc_count = len(pc_pokemon)
            party_count = len([p for p in party if p and not p.get("empty")])

            # Count level stats
            max_level = 0
            pokemon_over_30 = 0
            pokemon_over_50 = 0
            pokemon_over_70 = 0
            pokemon_at_100 = 0
            shiny_count = 0
            total_pokemon = 0

            all_pokemon = []
            for p in party:
                if p and not p.get("empty"):
                    all_pokemon.append(p)
            for p in pc_pokemon:
                if p and not p.get("empty"):
                    all_pokemon.append(p)

            total_pokemon = len(all_pokemon)

            for p in all_pokemon:
                level = p.get("level", 0)
                if level > max_level:
                    max_level = level
                if level >= 30:
                    pokemon_over_30 += 1
                if level >= 50:
                    pokemon_over_50 += 1
                if level >= 70:
                    pokemon_over_70 += 1
                if level >= 100:
                    pokemon_at_100 += 1
                # Check for shiny using calculation
                if is_pokemon_shiny(p):
                    shiny_count += 1

            print(
                f"[Achievements] Checking {game_name}: badges={ach_save_data['badges']}, dex={ach_save_data['dex_caught']}, money={ach_save_data['money']}, party={party_count}, pc={pc_count}, playtime={playtime_h:.1f}h, owned={len(owned_list)} species"
            )

            # Debug: show legendary species in owned_list
            legendaries = [
                144,
                145,
                146,
                150,
                151,
                377,
                378,
                379,
                380,
                381,
                382,
                383,
                384,
                385,
                386,
            ]
            found_legendaries = [s for s in legendaries if s in owned_list]
            if found_legendaries:
                print(
                    f"[Achievements] {game_name} has legendaries in owned_list: {found_legendaries}"
                )
            print(
                f"[Achievements] {game_name} Pokemon: total={total_pokemon}, max_lv={max_level}, lv50+={pokemon_over_50}, lv100={pokemon_at_100}, shiny={shiny_count}"
            )

            # Update tracking for per-game achievements - SET THE CURRENT GAME FIRST
            self._achievement_manager.set_current_game(game_name)
            self._achievement_manager.update_tracking(
                "dex_count", ach_save_data["dex_caught"]
            )
            self._achievement_manager.update_tracking(
                "dex_seen", ach_save_data["dex_seen"]
            )
            self._achievement_manager.update_tracking("badges", ach_save_data["badges"])
            self._achievement_manager.update_tracking("money", ach_save_data["money"])
            self._achievement_manager.update_tracking("playtime_hours", playtime_h)
            self._achievement_manager.update_tracking("party_size", party_count)
            self._achievement_manager.update_tracking("pc_pokemon", pc_count)
            self._achievement_manager.update_tracking("total_pokemon", total_pokemon)
            self._achievement_manager.update_tracking("any_pokemon_level", max_level)
            self._achievement_manager.update_tracking(
                "pokemon_over_30", pokemon_over_30
            )
            self._achievement_manager.update_tracking(
                "pokemon_over_50", pokemon_over_50
            )
            self._achievement_manager.update_tracking(
                "pokemon_over_70", pokemon_over_70
            )
            self._achievement_manager.update_tracking("pokemon_at_100", pokemon_at_100)
            self._achievement_manager.update_tracking("shiny_count", shiny_count)
            # Store owned_set for per-game legendary checks
            self._achievement_manager.update_tracking("owned_set", set(owned_list))

            # Check game-specific achievements
            newly_unlocked = self._achievement_manager.check_and_unlock(
                ach_save_data, game_name
            )

            # Also force check by tracking values in case any were missed
            force_unlocked = self._achievement_manager.force_check_by_tracking(
                game_name
            )
            if force_unlocked:
                newly_unlocked.extend(force_unlocked)

            if newly_unlocked:
                print(
                    f"[Achievements] Unlocked {len(newly_unlocked)} achievements for {game_name}!"
                )

            # Also check Sinew achievements with aggregate data
            self._check_sinew_achievements_aggregate()

        except Exception as e:
            print(f"[Achievements] Error checking achievements: {e}")
            import traceback

            traceback.print_exc()

    def _check_sinew_achievements_aggregate(self):
        """Check Sinew achievements based on aggregate data from all saves.

        PERFORMANCE: Uses self._sinew_game_data_cache to avoid re-parsing every
        save on every call.  Only the currently active game is re-parsed from disk;
        all other games use their cached contribution from the last time they were
        the active game (or from startup).  Pass nothing - the current game is
        always treated as the one that may have changed.
        """
        if not self._achievement_manager:
            return

        # Safety: ensure cache exists even if __init__ path was unusual
        if not hasattr(self, "_sinew_game_data_cache"):
            self._sinew_game_data_cache = {}

        def is_pokemon_shiny(pokemon):
            """Calculate if a Pokemon is shiny from TID/SID/PID"""
            if pokemon.get("is_shiny") or pokemon.get("shiny", False):
                return True
            if not pokemon or pokemon.get("empty") or pokemon.get("egg"):
                return False
            personality = pokemon.get("personality", 0)
            ot_id = pokemon.get("ot_id", 0)
            if personality == 0 or ot_id == 0:
                return False
            tid = ot_id & 0xFFFF
            sid = (ot_id >> 16) & 0xFFFF
            pid_low = personality & 0xFFFF
            pid_high = (personality >> 16) & 0xFFFF
            return (tid ^ sid ^ pid_low ^ pid_high) < 8

        STARTER_LINES = [
            {1, 2, 3},        # Bulbasaur line
            {4, 5, 6},        # Charmander line
            {7, 8, 9},        # Squirtle line
            {252, 253, 254},  # Treecko line
            {255, 256, 257},  # Torchic line
            {258, 259, 260},  # Mudkip line
        ]
        EEVEELUTION_SPECIES = {133, 134, 135, 136, 196, 197}

        # Which game just changed? Always the currently selected one.
        current_game_name = (
            self.game_names[self.current_game]
            if self.game_names and self.current_game < len(self.game_names)
            else None
        )

        def _parse_game_for_cache(game_name, sav_path):
            """Parse one save file and return a contribution dict for the cache."""
            from save_data_manager import SaveDataManager
            from config import SAVE_PATHS
            # Always use config as source of truth for save path
            canonical_path = SAVE_PATHS.get(game_name, sav_path)
            actual_path = canonical_path if os.path.exists(canonical_path) else sav_path

            manager = SaveDataManager()
            if not manager.load_save(actual_path, game_hint=game_name):
                print(f"[Achievements] Failed to load {game_name} for Sinew aggregate")
                return None

            badges = manager.get_badge_count() if hasattr(manager, "get_badge_count") else 0

            party = manager.get_party() if hasattr(manager, "get_party") else []
            active_party = [p for p in party if p and not p.get("empty")]

            pc_pokemon = []
            pc_count_raw = 0
            try:
                pc_count_raw = manager.get_pc_pokemon_count() if hasattr(manager, "get_pc_pokemon_count") else 0
                for box_num in range(1, 15):
                    if hasattr(manager, "get_box"):
                        box = manager.get_box(box_num)
                        if box:
                            pc_pokemon.extend(p for p in box if p and not p.get("empty"))
            except Exception:
                pass

            all_pokemon = active_party + pc_pokemon
            level100 = sum(1 for p in all_pokemon if p.get("level", 0) >= 100)
            level50plus = sum(1 for p in all_pokemon if p.get("level", 0) >= 50)
            shiny_count = sum(1 for p in all_pokemon if is_pokemon_shiny(p))
            eeveelutions = {p.get("species") for p in all_pokemon if p.get("species") in EEVEELUTION_SPECIES}

            dex_caught = 0
            owned_set = set()
            try:
                dex_data = manager.get_pokedex_count() if hasattr(manager, "get_pokedex_count") else {"caught": 0}
                dex_caught = dex_data.get("caught", 0)
                if hasattr(manager, "get_pokedex_data"):
                    owned_set = set(manager.get_pokedex_data().get("owned_list", []))
            except Exception:
                pass

            money = 0
            try:
                money = manager.get_money() if hasattr(manager, "get_money") else 0
            except Exception:
                pass

            playtime_hours = 0.0
            try:
                pt = manager.get_play_time() if hasattr(manager, "get_play_time") else {}
                playtime_hours = (pt.get("hours", 0) or 0) + ((pt.get("minutes", 0) or 0) / 60.0)
            except Exception:
                pass

            is_frlg = game_name in ["FireRed", "LeafGreen"]
            regional_size = 151 if is_frlg else 202

            print(f"[Achievements] Sinew cache: {game_name} - {badges} badges, {dex_caught} dex, {len(all_pokemon)} pokemon")

            return {
                "badges": badges,
                "dex_caught": dex_caught,
                "money": money,
                "playtime_hours": playtime_hours,
                "games_with_badges": 1 if badges > 0 else 0,
                "games_with_4plus_badges": 1 if badges >= 4 else 0,
                "games_with_champion": 1 if badges >= 8 else 0,
                "games_with_full_party": 1 if len(active_party) >= 6 else 0,
                "games_with_full_dex": 1 if dex_caught >= regional_size else 0,
                "owned_set": owned_set,
                "pc_count": pc_count_raw,
                "shiny_count": shiny_count,
                "level100": level100,
                "level50plus": level50plus,
                "eeveelutions": eeveelutions,
            }

        try:
            # Update cache: re-parse current game, use cache for all others
            for game_name, game_data in self.games.items():
                if game_name == "Sinew":
                    continue
                sav_path = game_data.get("sav")
                if not sav_path or not os.path.exists(sav_path):
                    # Also check config canonical path
                    from config import SAVE_PATHS
                    sav_path = SAVE_PATHS.get(game_name, "")
                    if not sav_path or not os.path.exists(sav_path):
                        continue

                is_current = (game_name == current_game_name)
                not_cached = (game_name not in self._sinew_game_data_cache)

                if is_current or not_cached:
                    contribution = _parse_game_for_cache(game_name, sav_path)
                    if contribution is not None:
                        self._sinew_game_data_cache[game_name] = contribution
                # else: silently use existing cached values

            # Aggregate from cache
            total_badges = 0
            total_dex_caught = 0
            total_money = 0
            total_playtime = 0.0
            games_with_badges = 0
            games_with_4plus_badges = 0
            games_with_champion = 0
            games_with_full_party = 0
            games_with_full_dex = 0
            combined_pokedex = set()
            total_pc_pokemon = 0
            total_shiny_pokemon = 0
            total_level100 = 0
            total_level50plus = 0
            owned_eeveelutions = set()

            for contrib in self._sinew_game_data_cache.values():
                total_badges += contrib["badges"]
                total_dex_caught += contrib["dex_caught"]
                total_money += contrib["money"]
                total_playtime += contrib["playtime_hours"]
                games_with_badges += contrib["games_with_badges"]
                games_with_4plus_badges += contrib["games_with_4plus_badges"]
                games_with_champion += contrib["games_with_champion"]
                games_with_full_party += contrib["games_with_full_party"]
                games_with_full_dex += contrib["games_with_full_dex"]
                combined_pokedex |= contrib["owned_set"]
                total_pc_pokemon += contrib["pc_count"]
                total_shiny_pokemon += contrib["shiny_count"]
                total_level100 += contrib["level100"]
                total_level50plus += contrib["level50plus"]
                owned_eeveelutions |= contrib["eeveelutions"]

            # Also scan Sinew Storage for Pokemon stats
            try:
                from sinew_storage import get_sinew_storage

                sinew_storage = get_sinew_storage()

                if sinew_storage and sinew_storage.is_loaded():
                    sinew_pokemon_count = 0
                    for box_num in range(1, 21):  # 20 boxes
                        box_data = sinew_storage.get_box(box_num)
                        if box_data:
                            for pokemon in box_data:
                                if pokemon and not pokemon.get("empty"):
                                    sinew_pokemon_count += 1
                                    level = pokemon.get("level", 0)
                                    species = pokemon.get("species", 0)

                                    if level >= 100:
                                        total_level100 += 1
                                    if level >= 50:
                                        total_level50plus += 1

                                    if is_pokemon_shiny(pokemon):
                                        total_shiny_pokemon += 1
                                        print(f"[Achievements] Found shiny in Sinew: species {species} in box {box_num}")

                                    if species:
                                        combined_pokedex.add(species)

                                    if species in EEVEELUTION_SPECIES:
                                        owned_eeveelutions.add(species)

                    total_pc_pokemon += sinew_pokemon_count
                    print(f"[Achievements] Sinew storage: {sinew_pokemon_count} Pokemon scanned, {total_shiny_pokemon} shiny found")
            except Exception as e:
                print(f"[Achievements] Could not scan Sinew storage: {e}")

            # Count starter lines owned (using combined_pokedex)
            starter_lines_owned = sum(1 for line in STARTER_LINES if line & combined_pokedex)

            # Count eeveelutions from combined_pokedex too
            for species in EEVEELUTION_SPECIES:
                if species in combined_pokedex:
                    owned_eeveelutions.add(species)

            # Check if dev mode is activated
            dev_mode_activated = False
            try:
                from settings import load_settings

                settings = load_settings()
                dev_mode_activated = settings.get("dev_mode", False)
            except Exception:
                pass

            print(
                f"[Achievements] Sinew aggregate: badges={total_badges}, champions={games_with_champion}, dex={len(combined_pokedex)}, money={total_money}, playtime={total_playtime:.1f}h"
            )
            print(
                f"[Achievements] Pokemon stats: pc={total_pc_pokemon}, shiny={total_shiny_pokemon}, lv100={total_level100}, lv50+={total_level50plus}"
            )
            print(
                f"[Achievements] Special: starters={starter_lines_owned}/6, eeveelutions={len(owned_eeveelutions)}/5, dev_mode={dev_mode_activated}, full_dex={games_with_full_dex}"
            )

            # Debug: show if legendaries are in combined_pokedex
            legendaries = [
                150,
                151,
                380,
                381,
                382,
                383,
                384,
                385,
                386,
                144,
                145,
                146,
                377,
                378,
                379,
            ]
            found_legendaries = [s for s in legendaries if s in combined_pokedex]
            if found_legendaries:
                print(
                    f"[Achievements] Legendaries in combined_pokedex: {found_legendaries}"
                )

            # Update tracking for Sinew achievements - SET CURRENT GAME TO SINEW
            self._achievement_manager.set_current_game("Sinew")
            self._achievement_manager.update_tracking("global_badges", total_badges)
            self._achievement_manager.update_tracking(
                "global_dex_count", total_dex_caught
            )
            self._achievement_manager.update_tracking(
                "combined_pokedex", len(combined_pokedex)
            )
            self._achievement_manager.update_tracking(
                "combined_pokedex_set", combined_pokedex
            )  # For species checks
            self._achievement_manager.update_tracking("global_money", total_money)
            self._achievement_manager.update_tracking("global_playtime", total_playtime)
            self._achievement_manager.update_tracking(
                "global_champions", games_with_champion
            )
            self._achievement_manager.update_tracking(
                "games_with_badges", games_with_badges
            )
            self._achievement_manager.update_tracking(
                "games_with_4plus_badges", games_with_4plus_badges
            )
            self._achievement_manager.update_tracking(
                "games_with_full_dex", games_with_full_dex
            )  # Regional dex completions

            # New tracking for Pokemon stats
            self._achievement_manager.update_tracking(
                "global_pc_pokemon", total_pc_pokemon
            )
            self._achievement_manager.update_tracking(
                "global_shiny_pokemon", total_shiny_pokemon
            )
            self._achievement_manager.update_tracking(
                "global_level100_pokemon", total_level100
            )
            self._achievement_manager.update_tracking(
                "global_level50plus_pokemon", total_level50plus
            )
            self._achievement_manager.update_tracking(
                "global_full_parties", games_with_full_party
            )
            self._achievement_manager.update_tracking(
                "global_starters", starter_lines_owned
            )
            self._achievement_manager.update_tracking(
                "global_eeveelutions", len(owned_eeveelutions)
            )
            self._achievement_manager.update_tracking(
                "dev_mode_activated", dev_mode_activated
            )

            # Check Sinew progression achievements
            from achievements_data import get_achievements_for

            sinew_achievements = get_achievements_for("Sinew")

            for ach in sinew_achievements:
                if self._achievement_manager.is_unlocked(ach["id"]):
                    continue

                hint = ach.get("hint", "")
                unlocked = False

                # Global badges
                if "global_badges >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_badges >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Global dex count (sum of caught across all saves)
                if "global_dex_count >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_dex_caught >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Global champions
                if "global_champions >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_champion >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Games with badges
                if "games_with_badges >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_badges >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Games with 4+ badges (halfway)
                if "games_with_4plus_badges >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_4plus_badges >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Games with full regional dex
                if "games_with_full_dex >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_full_dex >= required:
                            unlocked = True
                            print(
                                f"[Achievements] Regional dex achievement: {games_with_full_dex}/{required}"
                            )
                    except Exception:
                        pass

                # Global money
                if "global_money >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_money >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Global playtime
                if "global_playtime >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_playtime >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Combined pokedex (Dirty Dex - unique species across all saves)
                if "combined_pokedex >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if len(combined_pokedex) >= required:
                            unlocked = True
                            if required == 386:
                                print(
                                    f"[Achievements] DIRTY DEX COMPLETE! {len(combined_pokedex)}/386 unique species across all saves!"
                                )
                    except Exception:
                        pass

                # Legendary ownership checks (species ID based)
                if "owns_species_" in hint and "owns_species_380_or_381" not in hint:
                    try:
                        # Extract species ID from hint like "owns_species_383"
                        species_id = int(hint.split("owns_species_")[1].split("_")[0])
                        if species_id in combined_pokedex:
                            unlocked = True
                            print(
                                f"[Achievements] Legendary unlocked: {ach['name']} (species {species_id} found in combined pokedex)"
                            )
                        else:
                            # Debug: show which legendaries are missing
                            if species_id in [
                                150,
                                151,
                                380,
                                381,
                                382,
                                383,
                                384,
                                385,
                                386,
                            ]:
                                print(
                                    f"[Achievements] Legendary NOT in pokedex: species {species_id} ({ach['name']})"
                                )
                    except Exception as e:
                        print(f"[Achievements] Error checking legendary {hint}: {e}")

                # Special multi-species checks
                if "owns_species_380_or_381" in hint:
                    # Latias (380) or Latios (381)
                    if 380 in combined_pokedex or 381 in combined_pokedex:
                        unlocked = True
                        print("[Achievements] Latias/Latios unlocked!")
                    else:
                        print(
                            f"[Achievements] Latias/Latios check: 380 in pokedex={380 in combined_pokedex}, 381 in pokedex={381 in combined_pokedex}"
                        )

                if "owns_regi_trio" in hint:
                    # Regirock (377), Regice (378), Registeel (379)
                    if (
                        377 in combined_pokedex
                        and 378 in combined_pokedex
                        and 379 in combined_pokedex
                    ):
                        unlocked = True

                if "owns_weather_trio" in hint:
                    # Groudon (383), Kyogre (382), Rayquaza (384)
                    if (
                        382 in combined_pokedex
                        and 383 in combined_pokedex
                        and 384 in combined_pokedex
                    ):
                        unlocked = True

                # New trackable achievement checks
                # PC Pokemon count
                if "global_pc_pokemon >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_pc_pokemon >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Shiny Pokemon count
                if "global_shiny_pokemon >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_shiny_pokemon >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Level 100 Pokemon
                if "global_level100_pokemon >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_level100 >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Level 50+ Pokemon
                if "global_level50plus_pokemon >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_level50plus >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Full parties count
                if "global_full_parties >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_full_party >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Starter Pokemon
                if "global_starters >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if starter_lines_owned >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Eeveelutions
                if "global_eeveelutions >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if len(owned_eeveelutions) >= required:
                            unlocked = True
                    except Exception:
                        pass

                # Dev mode discovery
                if "dev_mode_activated == True" in hint:
                    if dev_mode_activated:
                        unlocked = True

                if unlocked:
                    self._achievement_manager.unlock(ach["id"], ach)
                    print(f"[Achievements] Unlocked Sinew achievement: {ach['name']}")

            # Also check Sinew Storage achievements
            self._check_sinew_storage_achievements()

            # Force check any Sinew achievements that might have been missed
            force_unlocked = self._achievement_manager.force_check_by_tracking("Sinew")
            if force_unlocked:
                print(
                    f"[Achievements] Force unlocked {len(force_unlocked)} Sinew achievements by tracking!"
                )

        except Exception as e:
            print(f"[Achievements] Error checking Sinew achievements: {e}")
            import traceback

            traceback.print_exc()

    def _check_sinew_storage_achievements(self):
        """Check achievements based on Sinew storage contents"""
        if not self._achievement_manager:
            return

        try:
            from sinew_storage import get_sinew_storage

            sinew_storage = get_sinew_storage()

            if not sinew_storage or not sinew_storage.is_loaded():
                return

            def is_pokemon_shiny(pokemon):
                """Calculate if a Pokemon is shiny from TID/SID/PID"""
                # First check if already set
                if pokemon.get("is_shiny") or pokemon.get("shiny", False):
                    return True

                if not pokemon or pokemon.get("empty") or pokemon.get("egg"):
                    return False

                personality = pokemon.get("personality", 0)
                ot_id = pokemon.get("ot_id", 0)

                if personality == 0 or ot_id == 0:
                    return False

                # Extract trainer ID and secret ID
                tid = ot_id & 0xFFFF
                sid = (ot_id >> 16) & 0xFFFF

                # Extract PID high and low
                pid_low = personality & 0xFFFF
                pid_high = (personality >> 16) & 0xFFFF

                # Calculate shiny value
                shiny_value = tid ^ sid ^ pid_low ^ pid_high

                # Pokemon is shiny if value < 8
                return shiny_value < 8

            # Count Pokemon and shinies in storage
            total_pokemon = sinew_storage.get_total_pokemon_count()
            total_shinies = 0

            for box_num in range(1, 21):  # 20 boxes
                box_data = sinew_storage.get_box(box_num)
                if box_data:
                    for poke in box_data:
                        if poke and not poke.get("empty"):
                            # Check for shiny using calculation
                            if is_pokemon_shiny(poke):
                                total_shinies += 1
                                print(
                                    f"[Achievements] Sinew storage shiny: species {poke.get('species', 0)} in box {box_num}"
                                )

            # Get transfer and evolution counts from manager stats
            transfer_count = self._achievement_manager.get_stat("sinew_transfers", 0)
            evolution_count = self._achievement_manager.get_stat("sinew_evolutions", 0)

            print(
                f"[Achievements] Sinew storage: {total_pokemon} Pokemon, {total_shinies} shiny, {transfer_count} transfers, {evolution_count} evolutions"
            )

            # Update tracking for storage achievements - ensure we're tracking under Sinew
            self._achievement_manager.set_current_game("Sinew")
            self._achievement_manager.update_tracking("sinew_pokemon", total_pokemon)
            self._achievement_manager.update_tracking("shiny_count", total_shinies)
            self._achievement_manager.update_tracking("sinew_transfers", transfer_count)
            self._achievement_manager.update_tracking(
                "sinew_evolutions", evolution_count
            )

            # Check Sinew storage achievements (not Dirty Dex - that uses combined_pokedex)
            self._achievement_manager.check_sinew_achievements(
                sinew_storage_count=total_pokemon,
                transfer_count=transfer_count,
                shiny_count=total_shinies,
                evolution_count=evolution_count,
            )

        except ImportError:
            pass  # Sinew storage not available
        except Exception as e:
            print(f"[Achievements] Error checking Sinew storage: {e}")

    def _test_achievement_notification(self):
        """Test method to trigger a fake achievement notification (for development)"""
        if self._achievement_notification:
            test_ach = {
                "id": "test_001",
                "name": "Test Achievement",
                "desc": "This is a test achievement",
                "game": "Sinew",
                "points": 50,
            }
            self._achievement_notification.queue_achievement(test_ach)
            print("[Achievements] Test notification queued")

    def _init_menu_music(self):
        """Initialize menu music system"""
        self._menu_music_path = os.path.join(DATA_DIR, "sounds", "SinewMenu.mp3")
        self._menu_music_playing = False
        self._menu_music_muted = self.settings.get("mute_menu_music", False)

        # Check if music file exists
        if not os.path.exists(self._menu_music_path):
            print(f"[Sinew] Menu music not found: {self._menu_music_path}")
            self._menu_music_path = None

    def _start_menu_music(self):
        """Start playing menu music (if not muted and file exists)"""
        if self._menu_music_path is None:
            return

        if self._menu_music_muted:
            return

        if self._menu_music_playing:
            return

        try:
            # Always reinitialise the mixer to Sinew's known-good settings.
            # The emulator may have left the mixer configured with the user's
            # custom buffer size (which could be unstable).  A full quit/init
            # cycle guarantees a clean slate for menu music playback.
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
                    pygame.time.wait(50)
            except Exception:
                pass

            pygame.mixer.pre_init(
                frequency=32768, size=-16, channels=2, buffer=1024
            )
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
            print(
                f"[Sinew] Mixer initialized for menu music: {pygame.mixer.get_init()}"
            )

            # Use pygame.mixer.music for background music (separate from sound effects)
            pygame.mixer.music.load(self._menu_music_path)
            # Apply saved master volume (default 80%)
            try:
                from config import VOLUME_DEFAULT
                from settings import load_sinew_settings
                _vol = load_sinew_settings().get("master_volume", VOLUME_DEFAULT)
                pygame.mixer.music.set_volume(max(0.0, min(1.0, _vol / 100.0)))
            except Exception:
                pygame.mixer.music.set_volume(0.8)
            pygame.mixer.music.play(-1)  # Loop indefinitely
            self._menu_music_playing = True
            print("[Sinew] Menu music started")
        except Exception as e:
            print(f"[Sinew] Could not start menu music: {e}")

    def _stop_menu_music(self):
        """Stop menu music"""
        if not self._menu_music_playing:
            return

        try:
            pygame.mixer.music.stop()
            # Unload to free resources (pygame 2.0+)
            if hasattr(pygame.mixer.music, "unload"):
                pygame.mixer.music.unload()
            self._menu_music_playing = False
            # Small delay to let audio system settle before game audio takes over
            pygame.time.wait(30)
            print("[Sinew] Menu music stopped")
        except Exception as e:
            print(f"[Sinew] Could not stop menu music: {e}")

    def _set_menu_music_muted(self, muted):
        """Set menu music mute state and save to settings"""
        self._menu_music_muted = muted
        self.settings["mute_menu_music"] = muted
        save_settings_file(self.settings)

        if muted:
            self._stop_menu_music()
        else:
            # Only start if we're not in a game
            if not self.emulator_active:
                self._start_menu_music()

    def _set_fullscreen(self, enabled):
        """Set fullscreen mode and save to settings"""
        self.settings["fullscreen"] = enabled
        save_settings_file(self.settings)

        if self.scaler:
            self.scaler.set_fullscreen(enabled)
            print(f"[Sinew] Fullscreen {'enabled' if enabled else 'disabled'}")

    def _set_swap_ab(self, enabled):
        """Set A/B button swap and save to settings"""
        self.settings["swap_ab"] = enabled
        save_settings_file(self.settings)

        # Update controller mapping
        if self.controller:
            self.controller.set_swap_ab(enabled)

        # Update emulator mapping if active (both gamepad and keyboard maps)
        if self.emulator:
            try:
                from mgba_emulator import (
                    RETRO_DEVICE_ID_JOYPAD_A,
                    RETRO_DEVICE_ID_JOYPAD_B,
                )

                # --- Gamepad button map ---
                gmap = getattr(self.emulator, "_gamepad_map", None)
                if gmap is not None:
                    if not hasattr(self.emulator, "_original_a_btn"):
                        self.emulator._original_a_btn = gmap.get(
                            RETRO_DEVICE_ID_JOYPAD_A, 0
                        )
                        self.emulator._original_b_btn = gmap.get(
                            RETRO_DEVICE_ID_JOYPAD_B, 1
                        )
                    if enabled:
                        gmap[RETRO_DEVICE_ID_JOYPAD_A] = self.emulator._original_b_btn
                        gmap[RETRO_DEVICE_ID_JOYPAD_B] = self.emulator._original_a_btn
                    else:
                        gmap[RETRO_DEVICE_ID_JOYPAD_A] = self.emulator._original_a_btn
                        gmap[RETRO_DEVICE_ID_JOYPAD_B] = self.emulator._original_b_btn
                    print(
                        f"[Sinew] Emulator gamepad A/B: A→btn{gmap[RETRO_DEVICE_ID_JOYPAD_A]}, B→btn{gmap[RETRO_DEVICE_ID_JOYPAD_B]}"
                    )

                # --- Keyboard map ---
                kb_map = getattr(self.emulator, "_kb_map", None)
                if kb_map is not None:
                    if not hasattr(self.emulator, "_original_a_keys"):
                        self.emulator._original_a_keys = kb_map.get(
                            RETRO_DEVICE_ID_JOYPAD_A, []
                        )
                        self.emulator._original_b_keys = kb_map.get(
                            RETRO_DEVICE_ID_JOYPAD_B, []
                        )
                    if enabled:
                        kb_map[RETRO_DEVICE_ID_JOYPAD_A] = (
                            self.emulator._original_b_keys
                        )
                        kb_map[RETRO_DEVICE_ID_JOYPAD_B] = (
                            self.emulator._original_a_keys
                        )
                    else:
                        kb_map[RETRO_DEVICE_ID_JOYPAD_A] = (
                            self.emulator._original_a_keys
                        )
                        kb_map[RETRO_DEVICE_ID_JOYPAD_B] = (
                            self.emulator._original_b_keys
                        )
                    print(
                        f"[Sinew] Emulator kb A/B: A→{kb_map.get(RETRO_DEVICE_ID_JOYPAD_A)}, B→{kb_map.get(RETRO_DEVICE_ID_JOYPAD_B)}"
                    )

            except Exception as e:
                print(f"[Sinew] Could not update emulator A/B swap: {e}")

        print(f"[Sinew] A/B swap {'enabled' if enabled else 'disabled'}")

    def _open_db_builder(self):
        """Open the database builder screen (called from Settings)"""
        # Close current modal (Settings) and open DB Builder
        self._close_modal()

        # Get modal dimensions
        modal_w = self.width - 40
        modal_h = self.height - 40

        # Open DB Builder
        if DBBuilder:
            self.modal_instance = DBBuilder(
                modal_w, modal_h, close_callback=self._close_modal
            )
        else:
            print("[Sinew] DBBuilder not available")

    def _check_database(self):
        """Check if the Pokemon database exists and is complete"""
        db_path = os.path.join(DATA_DIR, "pokemon_db.json")
        # Check if database file exists
        if not os.path.exists(db_path):
            print(f"[Sinew] Pokemon database not found: {db_path}")
            self._show_db_warning(
                "Pokemon database not found",
                "The database needs to be built before you can use all features.",
            )
            return False

        # Check if database has all Pokemon (386 for Gen 3)
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db = json.load(f)

            # Count Pokemon entries (keys that are 3-digit numbers)
            pokemon_count = sum(
                1 for key in db.keys() if key.isdigit() and len(key) == 3
            )

            if pokemon_count < 386:
                print(f"[Sinew] Pokemon database incomplete: {pokemon_count}/386")
                self._show_db_warning(
                    "Pokemon database incomplete",
                    f"Only {pokemon_count}/386 Pokemon found. Build the database to get all data.",
                )
                return False
        
            print(f"[Sinew] Pokemon database OK: {pokemon_count} Pokemon")
            return True
        
        except Exception as e:
            print(f"[Sinew] Error checking database: {e}")
            self._show_db_warning("Database error", f"Could not read database: {e}")
            return False

    def _show_db_warning(self, title, message):
        """Show a warning popup about the database"""
        modal_w = self.width - 80
        modal_h = 180
        self.modal_instance = DBWarningPopup(
            modal_w,
            modal_h,
            title,
            message,
            build_callback=self._open_db_builder_from_warning,
            close_callback=self._close_modal,
            screen_size=(self.width, self.height),
        )

    def _open_db_builder_from_warning(self):
        """Open DB builder from the warning popup"""
        self._close_modal()

        modal_w = self.width - 40
        modal_h = self.height - 40

        if DBBuilder:
            self.modal_instance = DBBuilder(
                modal_w, modal_h, close_callback=self._close_modal
            )

    def is_on_sinew(self):
        """Check if currently on Sinew (combined view)"""
        return self.get_current_game_name() == "Sinew"

    def get_menu_items(self):
        """Get menu items for current screen (Sinew vs individual game)"""
        if self.is_on_sinew():
            # Sinew menu - add Stop Game if a game is running
            items = list(SINEW_MENU_ITEMS)

            if self.emulator and self.emulator.loaded:
                items.insert(0, "Stop Game")
            items.append("Quit Sinew")
            return items

        # Game-specific menu
        items = []

        # Check if THIS game is currently running
        current_game = self.game_names[self.current_game]
        running_game = self._get_running_game_name()
        availability = self.get_current_game_availability()

        if running_game and running_game == current_game:
            # This game is running - show Resume and Stop options
            items.append("Resume Game")
            items.append("Stop Game")
        elif running_game:
            # Different game is running - show that info and Stop option
            items.append(f"Playing: {running_game}")
            items.append("Stop Game")
        elif availability == GAME_SAVE_ONLY:
            # Save exists but no ROM — show disabled label instead of Launch Game
            items.append("Save File Only")
        else:
            # No game running, full availability
            items.append("Launch Game")

        # Add standard menu items (from GAME_MENU_ITEMS, excluding Launch Game which we handle above)
        for item in GAME_MENU_ITEMS:
            if item == "Launch Game":
                continue
            # Only show Events if:
            # 1. Current game has 8 badges (Champion status)
            # 2. Endgame Access achievement has been CLAIMED
            if item == "Events":
                if not self._is_events_unlocked_for_current_game():
                    continue
            items.append(item)

        items.append("Quit Sinew")

        return items

    def _is_events_unlocked_for_current_game(self):
        """
        Check if Events menu should be shown for current game.

        RSE  (Ruby / Sapphire / Emerald):
            Requires the 'Pokemon Champion!' achievement reward to be claimed
            (i.e. player has all 8 badges and has collected that reward).

        FRLG (FireRed / LeafGreen):
            Requires the 'Sevii Pokemon Ranger' achievement reward to be claimed
            (i.e. player has the National Dex AND Rainbow Pass and collected that reward).
            Badge count is NOT used as the gate for FRLG.
        """
        current_game = self.get_current_game_name()
        if not current_game or current_game == "Sinew":
            return False

        is_frlg = current_game in ("FireRed", "LeafGreen")

        if is_frlg:
            # For FRLG the gate is the Sevii Pokemon Ranger achievement reward.
            # We trust the achievement manager's reward_claimed flag — the achievement
            # itself is only unlocked when the player has National Dex + Rainbow Pass.
            if self._achievement_manager:
                events_ach_id = self._get_events_unlock_achievement_id(current_game)
                if events_ach_id:
                    # Achievement must be unlocked AND its reward claimed
                    if not self._achievement_manager.is_unlocked(events_ach_id):
                        return False
                    if not self._achievement_manager.is_reward_claimed(events_ach_id):
                        return False
            return True

        else:
            # RSE: gate on 8 badges (Pokemon Champion).
            # Read from per-game tracking first so the global manager singleton
            # doesn't bleed wrong-game badge counts after the startup scan.
            badge_count = 0
            if self._achievement_manager:
                badge_count = self._achievement_manager.get_tracking(
                    "badges", default=0, game_name=current_game
                )

            # Fall back to global manager only when tracking is empty
            if badge_count == 0:
                manager = get_manager()
                if manager and manager.is_loaded():
                    loaded_game = getattr(
                        getattr(manager, "parser", None), "game_name", None
                    )
                    if loaded_game and self._save_matches_game(
                        loaded_game, current_game
                    ):
                        try:
                            badges = manager.get_badges()
                            badge_count = sum(1 for b in badges if b)
                        except Exception:
                            pass

            if badge_count < 8:
                return False

            # Also require the Pokemon Champion reward to have been claimed
            if self._achievement_manager:
                events_ach_id = self._get_events_unlock_achievement_id(current_game)
                if events_ach_id and not self._achievement_manager.is_reward_claimed(
                    events_ach_id
                ):
                    return False

            return True

    def _save_matches_game(self, loaded_game_name, expected_game_name):
        """
        Check if the parser's reported game_name matches the expected game.
        Handles paired parser names like 'FireRed/LeafGreen' and 'Ruby/Sapphire'.
        """
        if not loaded_game_name or not expected_game_name:
            return False
        if loaded_game_name == expected_game_name:
            return True
        # Parser returns paired names (e.g. 'FireRed/LeafGreen')
        if expected_game_name in loaded_game_name:
            return True
        return False

    def _get_events_unlock_achievement_id(self, game_name):
        """
        Return the achievement ID whose reward_claimed flag gates Events access.

        RSE  → _028  (Pokemon Champion!)
        FRLG → _057  (Sevii Pokemon Ranger — National Dex + Rainbow Pass)
        """
        prefix_map = {
            "Ruby": "RUBY",
            "Sapphire": "SAPP",
            "Emerald": "EMER",
            "FireRed": "FR",
            "LeafGreen": "LG",
        }
        prefix = prefix_map.get(game_name)
        if not prefix:
            return None

        if game_name in ("FireRed", "LeafGreen"):
            return f"{prefix}_057"  # Sevii Pokemon Ranger

        return f"{prefix}_028"  # Pokemon Champion!

    def _get_running_game_name(self):
        """Get the name of the currently running game, or None if no game is running."""
        if self.emulator and self.emulator.loaded and self.emulator.rom_path:
            # Try to match the ROM path to one of our game definitions
            rom_path = self.emulator.rom_path
            rom_name_lower = os.path.basename(rom_path).lower()

            for game_key, game_def in GAME_DEFINITIONS.items():
                keywords = game_def.get("keywords", [])
                exclude = game_def.get("exclude", [])

                # Check exclusions first
                excluded = False
                for ex in exclude:
                    if ex.lower() in rom_name_lower:
                        excluded = True
                        break

                if excluded:
                    continue

                # Check if any keyword matches
                for keyword in keywords:
                    if keyword.lower() in rom_name_lower:
                        return game_key

            # Fallback to ROM filename if no match found
            return os.path.splitext(os.path.basename(rom_path))[0]
        return None

    def precache_all(self, screen=None):
        """
        Pre-load all GIF backgrounds and parse all save files.
        Call this during startup to eliminate lag when switching games.

        Args:
            screen: Optional pygame surface to draw loading progress on
        """
        if self._precached:
            return

        # Count total items to load
        total_items = 0
        for _, game_data in self.games.items():
            if game_data.get("title_gif"):
                total_items += 1
            if game_data.get("sav"):
                total_items += 1

        current_item = 0

        for gname, game_data in self.games.items():
            # Load GIF
            gif_path = game_data.get("title_gif")
            if gif_path and os.path.exists(gif_path):
                if screen:
                    self._draw_loading_screen(
                        screen,
                        f"Loading {gname} background...",
                        current_item,
                        total_items,
                    )

                if not game_data.get("loaded"):
                    frames, durations = load_gif_frames(
                        gif_path, self.width, self.height
                    )
                    game_data["frames"] = frames
                    game_data["durations"] = durations
                    game_data["loaded"] = True
                current_item += 1

            # Parse save file
            sav_path = game_data.get("sav")
            if sav_path and os.path.exists(sav_path):
                if screen:
                    self._draw_loading_screen(
                        screen, f"Loading {gname} save...", current_item, total_items
                    )

                precache_save(sav_path, game_hint=gname if gname != "Sinew" else None)
                current_item += 1

        self._precached = True

        # Final loading screen
        if screen:
            self._draw_loading_screen(screen, "Ready!", total_items, total_items)
            pygame.time.wait(200)  # Brief pause to show "Ready!"

    def _draw_loading_screen(self, screen, message, current, total):
        """Draw a loading screen with progress bar"""
        if screen is None:
            return
        screen.fill((30, 30, 40))  # Dark background

        # Title
        title_font = self.font
        title = title_font.render("Sinew", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.width // 2, self.height // 3))
        screen.blit(title, title_rect)

        # Loading message
        msg = title_font.render(message, True, (200, 200, 200))
        msg_rect = msg.get_rect(center=(self.width // 2, self.height // 2))
        screen.blit(msg, msg_rect)

        # Progress bar
        bar_width = int(self.width * 0.6)
        bar_height = 20
        bar_x = (self.width - bar_width) // 2
        bar_y = int(self.height * 0.6)

        # Background
        pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_width, bar_height))

        # Fill
        if total > 0:
            fill_width = int((current / total) * bar_width)
            pygame.draw.rect(
                screen, (100, 200, 100), (bar_x, bar_y, fill_width, bar_height)
            )

        # Border
        pygame.draw.rect(
            screen, (100, 100, 120), (bar_x, bar_y, bar_width, bar_height), 2
        )

        # Progress text
        progress_text = title_font.render(f"{current}/{total}", True, (150, 150, 150))
        progress_rect = progress_text.get_rect(
            center=(self.width // 2, bar_y + bar_height + 20)
        )
        screen.blit(progress_text, progress_rect)

        # Use scaler if available, otherwise direct flip
        if self.scaler:
            self.scaler.blit_scaled()
        else:
            pygame.display.flip()

    def _can_accept_input(self):
        """Check if enough time has passed since last input (debouncing)"""
        current_time = time.time()
        if current_time - self._last_input_time >= self.INPUT_COOLDOWN:
            self._last_input_time = current_time
            return True
        return False

    def _init_games(self):
        """Initialize game data and load GIFs"""
        # Re-detect games in case ROMs were added
        global GAMES
        GAMES = detect_games()

        # If external emulator mode is active, overlay ROM/save paths from the
        # provider's known dirs so the carousel shows what the external emu has.
        import builtins

        if (
            getattr(builtins, "SINEW_DEV_MODE", False)
            and getattr(builtins, "SINEW_USE_EXTERNAL_EMULATOR", False)
            and self.external_emu
            and self.external_emu.active_provider
        ):
            provider = self.external_emu.active_provider
            ext_roms_dir = getattr(provider, "roms_dir", None)
            ext_saves_dir = getattr(provider, "saves_dir", None)
            if ext_roms_dir or ext_saves_dir:
                print(
                    f"[Dev] Scanning external dirs — ROMs: {ext_roms_dir}  Saves: {ext_saves_dir}"
                )
                for game_name in list(GAMES.keys()):
                    if game_name == "Sinew":
                        continue
                    if ext_roms_dir:
                        ext_rom, _ = find_rom_for_game(game_name, ext_roms_dir)
                        if ext_rom:
                            GAMES[game_name]["rom"] = ext_rom
                            print(
                                f"[Dev] External ROM for {game_name}: {os.path.basename(ext_rom)}"
                            )
                    if ext_saves_dir:
                        ext_sav = find_save_for_game(game_name, ext_saves_dir)
                        if not ext_sav and GAMES[game_name].get("rom"):
                            base = os.path.splitext(
                                os.path.basename(GAMES[game_name]["rom"])
                            )[0]
                            candidate = os.path.join(ext_saves_dir, base + ".sav")
                            if os.path.exists(candidate):
                                ext_sav = candidate
                        if ext_sav:
                            GAMES[game_name]["sav"] = ext_sav
                            print(
                                f"[Dev] External save for {game_name}: {os.path.basename(ext_sav)}"
                            )

        self.games = {}  # Reset so we rebuild cleanly

        for gname, g in GAMES.items():
            game_data = g.copy()

            # Apply settings overrides
            g_conf = self.settings.get(gname, {})
            if "rom" in g_conf:
                game_data["rom"] = g_conf["rom"]
            if "sav" in g_conf:
                game_data["sav"] = g_conf["sav"]

            # Stamp availability AFTER overrides so overridden paths are respected
            availability = get_game_availability(game_data)
            game_data["availability"] = availability

            # Skip games that have neither ROM nor save – hide them entirely
            if availability == GAME_UNAVAILABLE:
                print(f"[GameScreen] Hiding {gname}: no ROM and no save found")
                continue

            # Load GIF frames (lazy - don't load until needed)
            game_data["frames"] = None
            game_data["durations"] = None
            game_data["frame_index"] = 0
            game_data["time_accum"] = 0
            game_data["loaded"] = False

            self.games[gname] = game_data

        self.game_names = list(self.games.keys())

        # Print detected games
        full_games = [
            g
            for g in self.game_names
            if g != "Sinew" and self.games[g].get("availability") == GAME_FULL
        ]
        save_only = [
            g
            for g in self.game_names
            if g != "Sinew" and self.games[g].get("availability") == GAME_SAVE_ONLY
        ]

        if full_games:
            print(f"[GameScreen] Detected games (full): {', '.join(full_games)}")
        if save_only:
            print(f"[GameScreen] Save-only games (no ROM): {', '.join(save_only)}")
        if not full_games and not save_only:
            print("[GameScreen] No ROMs or saves detected in roms/ and saves/ folders")

        # Load Sinew background image (scaled to screen size like other games)
        self.sinew_logo = None
        self.sinew_bg_color = (255, 255, 255)  # Default white
        sinew_logo_path = os.path.join(SPRITES_DIR, "title", "PKSINEW.png")
        if os.path.exists(sinew_logo_path):
            try:
                # Load and scale to screen size like other game backgrounds
                pil_img = Image.open(sinew_logo_path)
                pil_img = pil_img.convert("RGBA").resize(
                    (self.width, self.height), Image.NEAREST
                )
                data = pil_img.tobytes()
                self.sinew_logo = pygame.image.fromstring(
                    data, pil_img.size, pil_img.mode
                ).convert_alpha()
                pil_img.close()
            except Exception as e:
                print(f"Failed to load Sinew background: {e}")

    def refresh_games(self):
        """Re-detect games (call if ROMs were added/removed)"""
        current_game_name = (
            self.game_names[self.current_game] if self.game_names else "Sinew"
        )

        self._init_games()

        # Try to restore position to same game
        if current_game_name in self.game_names:
            self.current_game = self.game_names.index(current_game_name)
        else:
            self.current_game = 0

        print("[GameScreen] Games refreshed")

    def _ensure_gif_loaded(self, gname):
        """Lazy load GIF for a game"""
        game_data = self.games[gname]
        if not game_data["loaded"]:
            gif_path = game_data.get("title_gif")
            if gif_path and os.path.exists(gif_path):
                frames, durations = load_gif_frames(gif_path, self.width, self.height)
                game_data["frames"] = frames
                game_data["durations"] = durations
            else:
                game_data["frames"] = []
                game_data["durations"] = []
            game_data["loaded"] = True

    def _load_current_save(self):
        """Load save file for current game (skip for Sinew)"""
        gname = self.game_names[self.current_game]

        if self.is_on_sinew():
            return

        sav_path = self.games[gname].get("sav")

        if sav_path and os.path.exists(sav_path):
            manager = get_manager()
            manager.load_save(sav_path, game_hint=gname if gname != "Sinew" else None)
        else:
            print(f"Save file not found: {sav_path}")
            # Clear stale data so screens show empty/default state
            # instead of the previously loaded game's data
            get_manager().unload()

    def _reload_save_for_game(self, game_name):
        """Reload save for a specific game if it's currently active"""
        if game_name not in self.games:
            return False

        # If this is the current game, reload immediately
        current_game_name = self.game_names[self.current_game]
        if current_game_name == game_name:
            sav_path = self.games[game_name].get("sav")
            if sav_path and os.path.exists(sav_path):
                manager = get_manager()
                manager.load_save(sav_path, game_hint=game_name)

        return True

    def _force_reload_current_save(self):
        """Force reload save file for current game, clearing cache.
        Used when returning from emulator to ensure fresh data."""
        gname = self.game_names[self.current_game]

        if self.is_on_sinew():
            return

        sav_path = self.games[gname].get("sav")

        if sav_path and os.path.exists(sav_path):
            manager = get_manager()
            # Use reload() to clear cache and get fresh data
            if hasattr(manager, "reload"):
                manager.reload()
                print(f"[Sinew] Force reloaded save for {gname}")
            else:
                manager.load_save(sav_path, game_hint=gname)

    # ----- NEW: separate index change from loading -----
    def change_game(self, delta):
        """Switch to next/previous game index only"""
        if len(self.game_names) == 0:
            return
        self.current_game = (self.current_game + delta) % len(self.game_names)

    def load_game_and_background(self):
        """
        Load the save and GIF background for the current game.
        Resets GIF animation state so the new game's background starts from frame 0.
        """
        # 1) Load save file for the current index
        self._load_current_save()

        # 2) Load GIF frames for the current game (lazy)
        gname = self.game_names[self.current_game]
        self._ensure_gif_loaded(gname)

        # 3) Reset animation state
        game_data = self.games[gname]
        game_data["frame_index"] = 0
        game_data["time_accum"] = 0

        # print(f"Switched to: {gname} (save + background loaded)")

    def _change_game_and_reload(self, delta):
        """Helper: change index then reload save + background"""
        if not self._can_accept_input():
            return  # Debounce - ignore rapid inputs
        self.change_game(delta)
        self.load_game_and_background()
        # Reset menu index when changing games (menu items differ for Sinew vs games)
        self.menu_index = 0

    def _change_game_skip_sinew(self, delta):
        """Change game but skip Sinew (index 0) - used by PC Box"""
        if not self._can_accept_input():
            return  # Debounce - ignore rapid inputs
        self._change_game_skip_sinew_no_debounce(delta)

    def _change_game_skip_sinew_no_debounce(self, delta):
        """Change game but skip Sinew - with built-in cooldown for modal use"""
        if len(self.game_names) <= 1:
            return

        # Cooldown to prevent double-triggers
        current_time = pygame.time.get_ticks()
        if not hasattr(self, "_last_modal_game_switch"):
            self._last_modal_game_switch = 0

        if current_time - self._last_modal_game_switch < 800:
            return

        self._last_modal_game_switch = current_time

        # Keep cycling until we're not on Sinew
        for _ in range(len(self.game_names)):
            self.current_game = (self.current_game + delta) % len(self.game_names)
            if self.current_game != 0:
                break

        self.load_game_and_background()
        self.menu_index = 0

    def _change_game_include_sinew(self, delta):
        """Change game including Sinew - for Pokedex which can show combined view"""
        if len(self.game_names) <= 1:
            return

        self.current_game = (self.current_game + delta) % len(self.game_names)
        self.load_game_and_background()
        self.menu_index = 0

    def _set_game_by_name(self, game_name):
        """Set to a specific game by name and reload"""
        if game_name in self.game_names:
            self.current_game = self.game_names.index(game_name)
            self.load_game_and_background()
            return True
        return False

    # ----- end new actions -----

    def get_current_game_name(self):
        """Get current game name"""
        return self.game_names[self.current_game] if self.game_names else "Unknown"

    def get_current_game_availability(self):
        """Return the availability state of the currently selected game."""
        gname = self.get_current_game_name()
        if gname in self.games:
            return self.games[gname].get("availability", GAME_FULL)
        return GAME_FULL

    def _launch_game(self):
        """Launch the current game ROM"""
        if self.is_on_sinew():
            print("Sinew is a combined view - no game to launch")
            return

        # Check if a game is already running
        if self.emulator and self.emulator.loaded:
            running_game = "Unknown"
            if self.emulator.rom_path:
                running_game = os.path.splitext(
                    os.path.basename(self.emulator.rom_path)
                )[0]
            self._show_notification(
                f"Currently playing: {running_game}",
                self._get_pause_combo_hint_text("return"),
            )
            return

        gname = self.game_names[self.current_game]
        rom_path = self.games[gname].get("rom")
        sav_path = self.games[gname].get("sav")

        if not rom_path or not os.path.exists(rom_path):
            if self.games[gname].get("availability") == GAME_SAVE_ONLY:
                self._show_notification(
                    f"{gname}: No ROM found",
                    "Place a matching .gba ROM in the roms/ folder",
                )
            else:
                print(f"ROM not found: {rom_path}")
            return

        import builtins

        use_external = getattr(builtins, "SINEW_USE_EXTERNAL_EMULATOR", False)
        dev_mode = getattr(builtins, "SINEW_DEV_MODE", False)

        # External emulator path — only if toggle is on AND a provider is actually ready
        if (
            dev_mode
            and use_external
            and self.external_emu
            and self.external_emu.active_provider
        ):
            if self._launch_external_emulator(rom_path, sav_path):
                return
            print("[Dev] External emulator failed — falling back to integrated mGBA")

        # Integrated mGBA path (fallback)
        if EMULATOR_AVAILABLE and MgbaEmulator:
            try:
                self._launch_integrated_emulator(rom_path, sav_path)
            except Exception as e:
                print(f"Integrated emulator failed: {e}")
                print("No compatible emulator core found for this platform.")

    def _launch_external_emulator(self, rom_path, sav_path):
        """
        Launch via ExternalEmulator.  The provider handles the actual process;
        we handle save mirroring so Sinew edits flow to the external save dir
        and in-game saves flow back to Sinew afterwards.

        Save strategy:
          - sav_path is Sinew's current save (may already point to provider's
            saves_dir if _init_games found ROMs/saves there).
          - We push a copy to the provider's saves_dir before launch so the
            external emulator starts with the latest Sinew edits.
          - register_ext_mirror() keeps them live-synced while Sinew is open.
          - A background thread waits for the process to exit then pulls the
            save back into Sinew's saves/ and reloads the display.
        """
        import shutil
        import threading

        provider = self.external_emu.active_provider
        ext_saves_dir = getattr(provider, "saves_dir", None)

        # --- Resolve the external save path ---
        ext_sav = None
        if hasattr(provider, "get_save_path"):
            ext_sav = provider.get_save_path(rom_path)
        if not ext_sav and ext_saves_dir:
            base = (
                os.path.basename(sav_path)
                if sav_path
                else os.path.splitext(os.path.basename(rom_path))[0] + ".sav"
            )
            ext_sav = os.path.join(ext_saves_dir, base)
        if not ext_sav:
            ext_sav = os.path.splitext(rom_path)[0] + ".sav"  # last resort
        ext_sav = os.path.abspath(ext_sav)

        # --- Sinew backup path (always in Sinew's own saves/) ---
        sinew_saves_dir = getattr(
            config, "SAVES_DIR", os.path.join(os.path.dirname(__file__), "saves")
        )
        os.makedirs(sinew_saves_dir, exist_ok=True)
        sinew_backup = os.path.join(sinew_saves_dir, os.path.basename(ext_sav))

        # --- Push latest Sinew save → external dir before launch ---
        source = (
            sav_path
            if (sav_path and os.path.exists(sav_path))
            else (sinew_backup if os.path.exists(sinew_backup) else None)
        )
        if source and os.path.abspath(source) != ext_sav:
            try:
                os.makedirs(os.path.dirname(ext_sav), exist_ok=True)
                shutil.copy2(source, ext_sav)
                print(f"[Dev] Pushed save → external: {ext_sav}")
            except Exception as e:
                print(f"[Dev] Warning: could not push save: {e}")

        # --- Register mirror: Sinew edits → external save dir ---
        sinew_edit_path = os.path.abspath(sav_path if sav_path else sinew_backup)
        if sinew_edit_path != ext_sav:
            try:
                from save_writer import register_ext_mirror

                register_ext_mirror(sinew_edit_path, ext_sav)
                print(
                    f"[Dev] Mirror: {os.path.basename(sinew_edit_path)} → {os.path.basename(ext_sav)}"
                )
            except ImportError:
                print("[Dev] Warning: save_writer.register_ext_mirror not available")

        self._ext_sav_path = ext_sav
        self._sinew_backup_sav_path = sinew_backup

        print(
            f"[Dev] Launching {type(provider).__name__} — ROM: {os.path.basename(rom_path)}"
        )
        print(f"[Dev]   External save → {ext_sav}")
        print(f"[Dev]   Sinew save    → {sinew_edit_path}")

        # --- Launch ---
        success = self.external_emu.launch(rom_path)
        if not success:
            if sinew_edit_path != ext_sav:
                try:
                    from save_writer import unregister_ext_mirror

                    unregister_ext_mirror(sinew_edit_path)
                except ImportError:
                    pass
            self._ext_sav_path = None
            self._sinew_backup_sav_path = None
            print(
                f"[Dev] External emulator launch failed for {os.path.basename(rom_path)}"
            )
            return False

        # Tell the UI we're "in game" (stops music etc.)
        self.emulator_active = True
        self._stop_menu_music()

        # Watch for process exit on a background thread
        def _watch():
            try:
                self.external_emu.process.wait()
            except Exception:
                pass
            self._on_external_emulator_closed(sinew_edit_path)

        threading.Thread(target=_watch, daemon=True).start()
        self._show_notification(
            "[Dev] External emulator launched", f"Using {type(provider).__name__}"
        )
        return True

    def _on_external_emulator_closed(self, sinew_edit_path):
        """
        Called from a background thread when the external emulator process exits.
        Pulls the updated save back into Sinew and signals the main thread to reload.
        """
        import shutil

        ext_sav = self._ext_sav_path
        sinew_backup = self._sinew_backup_sav_path

        # Unregister mirror so Sinew edits no longer flow outward
        if sinew_edit_path and sinew_edit_path != ext_sav:
            try:
                from save_writer import unregister_ext_mirror

                unregister_ext_mirror(sinew_edit_path)
                print(f"[Dev] Mirror unregistered: {os.path.basename(sinew_edit_path)}")
            except ImportError:
                pass

        # Pull external save → Sinew backup
        if ext_sav and sinew_backup and os.path.exists(ext_sav):
            try:
                shutil.copy2(ext_sav, sinew_backup)
                print(f"[Dev] Pulled save → Sinew: {sinew_backup}")
            except Exception as e:
                print(f"[Dev] Pull-back failed: {e}")

        # Also update the live sav_path if it differs from the backup
        if (
            sinew_edit_path
            and sinew_backup
            and os.path.abspath(sinew_edit_path) != os.path.abspath(sinew_backup)
            and os.path.exists(sinew_backup)
        ):
            try:
                shutil.copy2(sinew_backup, sinew_edit_path)
            except Exception:
                pass

        self._ext_sav_path = None
        self._sinew_backup_sav_path = None
        self.emulator_active = False
        self._ext_emu_closed_needs_reload = True
        print("[Dev] External emulator closed — save pulled back to Sinew")

    def _launch_integrated_emulator(self, rom_path, sav_path):
        """Launch the game using the integrated mGBA emulator"""
        # Initialize emulator if needed
        if self.emulator is None:
            # MgbaEmulator will auto-detect the correct core for the platform
            # If core_path is None, it will search cores_dir for the appropriate file
            # (.dll on Windows, .so on Linux, .dylib on macOS)
            self.emulator = MgbaEmulator(
                core_path=MGBA_CORE_PATH,
                save_dir=SAVES_DIR,
                system_dir=SYSTEM_DIR,
                cores_dir=CORES_DIR,
            )

        # Load the ROM
        self.emulator.load_rom(rom_path, sav_path)
        builtins.SINEW_EMULATOR = self.emulator
        self.emulator_active = True
        self._emulator_pause_combo_released = True

        # Stop menu music while in game
        self._stop_menu_music()

        # Switch scaler to GBA native resolution for direct GPU scaling
        if self.scaler:
            self.scaler.set_virtual_resolution(240, 160)

        print(f"[Sinew] Launched: {os.path.basename(rom_path)}")

    def _show_return_loading_screen(self, message="Returning to Sinew..."):
        """Show a brief loading screen when dropping back from a game to the Sinew menu."""
        # Always grab the current display surface - the cached _loading_screen
        # may be stale/quit after a scaler resolution change
        try:
            screen = pygame.display.get_surface()
        except Exception:
            screen = self._loading_screen
        if screen is None:
            return
        screen.fill((30, 30, 40))

        title_font = self.font
        title = title_font.render("Sinew", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.width // 2, self.height // 3))
        screen.blit(title, title_rect)

        msg = title_font.render(message, True, (200, 200, 200))
        msg_rect = msg.get_rect(center=(self.width // 2, self.height // 2))
        screen.blit(msg, msg_rect)

        bar_width = int(self.width * 0.6)
        bar_height = 20
        bar_x = (self.width - bar_width) // 2
        bar_y = int(self.height * 0.6)
        pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, (100, 200, 100), (bar_x, bar_y, bar_width // 2, bar_height))
        pygame.draw.rect(screen, (100, 100, 120), (bar_x, bar_y, bar_width, bar_height), 2)

        if self.scaler:
            self.scaler.blit_scaled()
        else:
            pygame.display.flip()

    def _stop_emulator(self):
        """Stop and cleanup the integrated mGBA emulator"""
        builtins.SINEW_EMULATOR = None
        if self.emulator:
            # Unpause first in case it was paused
            if self.emulator.paused:
                self.emulator.resume()
            self.emulator.save_sram()
            self.emulator.unload()
        self.emulator_active = False

        # Restore keyboard filter in case it was disabled (e.g. KeyboardMapper left it off)
        if self.controller and hasattr(self.controller, "kb_filter_enabled"):
            self.controller.kb_filter_enabled = True

        # Reset pause combo state
        self._emulator_pause_combo_released = True

        # Restore menu virtual resolution and show loading screen
        if self.scaler:
            self.scaler.restore_virtual_resolution()
        self._show_return_loading_screen("Returning to Sinew...")

        # Reload save data in Sinew since it may have changed
        self.load_game_and_background()

        # Resume menu music
        self._start_menu_music()

        print("[Sinew] Returned from game")

    def _update_emulator(self, events, dt):
        """
        Update emulator when active

        Returns:
            bool: True to keep running
        """
        # Check for quit events
        for event in events:
            if event.type == pygame.QUIT:
                self._stop_emulator()
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F5:
                    # Manual save
                    self.emulator.save_sram()

        # Run emulation frame if not paused
        if not self.emulator.paused:
            self.emulator.run_frame()
        else:
            # Debug: this shouldn't happen when we're supposed to be running
            print(
                f"[Sinew] WARNING: emulator.paused={self.emulator.paused} but emulator_active={self.emulator_active}"
            )

        # Check for pause combo (Start + Select held)
        combo_held = self._check_emulator_pause_combo()

        if combo_held and self._emulator_pause_combo_released:
            # Combo just triggered
            self._emulator_pause_combo_released = False

            if self.emulator.paused:
                # Resume game
                self._stop_menu_music()  # Stop menu music when resuming game
                self.emulator.resume()
                # Switch to emulator resolution
                if self.scaler:
                    self.scaler.set_virtual_resolution(240, 160)
                print("[Sinew] Resuming game")
            else:
                # Pause and return to Sinew
                self.emulator.pause()
                self.emulator_active = False
                # Restore menu virtual resolution and show loading screen
                if self.scaler:
                    self.scaler.restore_virtual_resolution()
                self._show_return_loading_screen("Returning to Sinew...")
                # Force reload save data since it was modified by emulator
                self._force_reload_current_save()
                # Check achievements based on updated save data
                # (also runs _check_sinew_achievements_aggregate internally)
                self._check_achievements_for_current_game()
                # Start menu music when returning to Sinew
                self._start_menu_music()
                print("[Sinew] Paused - returned to Sinew menu")

        elif not combo_held:
            # Combo released, allow next trigger
            self._emulator_pause_combo_released = True

        return True

    def _check_emulator_pause_combo(self):
        """
        Check if Start+Select are both held for pause combo.
        Uses the emulator's built-in combo detection.

        Returns:
            bool: True if combo is triggered
        """
        if self.emulator:
            return self.emulator.check_pause_combo()
        return False

    def _load_pause_combo_setting(self):
        """Load pause combo setting from sinew_settings.json"""
        self._pause_combo_setting = {"type": "combo", "buttons": ["START", "SELECT"]}
        try:
            settings = load_settings()
            if "pause_combo" in settings:
                self._pause_combo_setting = settings["pause_combo"]
                print(
                    f"[Sinew] Pause combo: {self._pause_combo_setting.get('name', 'START+SELECT')}"
                )
        except Exception as e:
            print(f"[Sinew] Could not load pause combo setting: {e}")

    def _reload_pause_combo_setting(self):
        """Reload pause combo setting (called when user changes it in settings)"""
        self._load_pause_combo_setting()

        # Also reload in emulator if running
        if self.emulator and hasattr(self.emulator, "_load_pause_combo_setting"):
            self.emulator._pause_combo_setting = (
                self.emulator._load_pause_combo_setting()
            )
            print("[Sinew] Reloaded pause combo in emulator")

    def _get_pause_combo_name(self):
        """Get the name of the current pause combo (e.g., 'START+SELECT')"""
        setting = self._pause_combo_setting
        if setting.get("type") == "custom":
            return f"Button {setting.get('button', '?')}"
        else:
            buttons = setting.get("buttons", ["START", "SELECT"])
            return "+".join(buttons)

    def _get_pause_combo_hint_text(self, action="resume"):
        """Get the hint text for the current pause combo"""
        return f"Hold {self._get_pause_combo_name()} to {action}"

    def _draw_resume_banner(self, surf):
        """
        Draw a dropdown banner from the top showing game is paused.
        Shows "[gamename] running • Hold [combo] to resume"
        with pulsing animation and scrolling text if too long.
        """
        import math

        # Get game name
        game_name = self._get_running_game_name() or "Game"
        combo_name = self._get_pause_combo_name()

        # Build the full text
        full_text = f'"{game_name}" running  •  Hold {combo_name} to resume'

        # Banner dimensions - shorter and centered box
        banner_height = 21
        banner_width = int(self.width * 0.85)
        banner_x = (self.width - banner_width) // 2
        banner_y = 4
        padding = 12
        border_radius = 6

        # Update pulse time
        self._resume_banner_pulse_time += 0.08
        pulse = (math.sin(self._resume_banner_pulse_time) + 1) / 2  # 0 to 1

        # Pulsing background color (dark amber to lighter amber)
        bg_r = int(40 + 25 * pulse)
        bg_g = int(35 + 20 * pulse)
        bg_b = int(15 + 10 * pulse)

        # Draw banner background with rounded corners
        banner_rect = pygame.Rect(banner_x, banner_y, banner_width, banner_height)
        pygame.draw.rect(
            surf, (bg_r, bg_g, bg_b), banner_rect, border_radius=border_radius
        )

        # Pulsing border (gold tones)
        border_r = int(180 + 75 * pulse)
        border_g = int(140 + 60 * pulse)
        border_b = int(30 + 30 * pulse)
        pygame.draw.rect(
            surf,
            (border_r, border_g, border_b),
            banner_rect,
            2,
            border_radius=border_radius,
        )

        # Render text using the same font as the rest of the app
        try:
            banner_font = pygame.font.Font(FONT_PATH, 10)
        except Exception:
            try:
                banner_font = pygame.font.Font(None, 18)
            except Exception:
                banner_font = pygame.font.SysFont(None, 18)

        # Pulsing text color
        text_r = int(200 + 55 * pulse)
        text_g = int(180 + 55 * pulse)
        text_b = int(100 + 50 * pulse)
        text_color = (text_r, text_g, text_b)

        text_surf = banner_font.render(full_text, True, text_color)
        text_width = text_surf.get_width()

        # Available width for text (inside the box)
        available_width = banner_width - (padding * 2)

        if text_width <= available_width:
            # Text fits - center it
            text_x = banner_x + (banner_width - text_width) // 2
            text_y = banner_y + (banner_height - text_surf.get_height()) // 2
            surf.blit(text_surf, (text_x, text_y))
        else:
            # Text too long - scroll it
            clip_rect = pygame.Rect(
                banner_x + padding, banner_y, available_width, banner_height
            )

            # Update scroll offset
            scroll_width = text_width + 60  # Add gap before repeat
            self._resume_banner_scroll_offset += self._resume_banner_scroll_speed
            if self._resume_banner_scroll_offset >= scroll_width:
                self._resume_banner_scroll_offset = 0

            # Calculate text position (scrolling left)
            text_x = banner_x + padding - self._resume_banner_scroll_offset
            text_y = banner_y + (banner_height - text_surf.get_height()) // 2

            # Draw text with clipping
            old_clip = surf.get_clip()
            surf.set_clip(clip_rect)

            surf.blit(text_surf, (text_x, text_y))
            # Draw second copy for seamless scrolling
            if text_x + text_width < banner_x + padding + available_width:
                surf.blit(text_surf, (text_x + scroll_width, text_y))

            surf.set_clip(old_clip)

    def _check_pause_combo_direct(self):
        """
        Check pause combo directly using pygame input.
        Used when emulator is paused and we're in Sinew menu.

        Returns:
            bool: True if combo held for required frames
        """
        if not hasattr(self, "_pause_combo_counter"):
            self._pause_combo_counter = 0

        setting = getattr(
            self,
            "_pause_combo_setting",
            {"type": "combo", "buttons": ["START", "SELECT"]},
        )
        combo_held = False

        if setting.get("type") == "custom":
            # Custom single button
            custom_btn = setting.get("button")
            if custom_btn is not None:
                try:
                    if pygame.joystick.get_count() > 0:
                        joy = pygame.joystick.Joystick(0)
                        joy.init()
                        if custom_btn < joy.get_numbuttons():
                            combo_held = joy.get_button(custom_btn)
                except Exception:
                    pass
        else:
            # Button combo
            required_buttons = setting.get("buttons", ["START", "SELECT"])
            buttons_held = {}

            # Check keyboard (for START/SELECT)
            keys = pygame.key.get_pressed()
            if "START" in required_buttons:
                buttons_held["START"] = keys[pygame.K_RETURN]
            if "SELECT" in required_buttons:
                buttons_held["SELECT"] = keys[pygame.K_BACKSPACE]

            # Check controller
            try:
                if pygame.joystick.get_count() > 0:
                    joy = pygame.joystick.Joystick(0)
                    joy.init()
                    num_buttons = joy.get_numbuttons()

                    for btn_name in required_buttons:
                        btn_indices = (
                            [7]
                            if btn_name == "START"
                            else [6] if btn_name == "SELECT" else []
                        )

                        if self.controller and hasattr(self.controller, "button_map"):
                            btn_indices = self.controller.button_map.get(
                                btn_name, btn_indices
                            )

                        for idx in btn_indices:
                            if isinstance(idx, int) and idx < num_buttons:
                                if joy.get_button(idx):
                                    buttons_held[btn_name] = True
            except Exception:
                pass

            # Check if all required buttons are held
            combo_held = all(buttons_held.get(btn, False) for btn in required_buttons)

        if combo_held:
            self._pause_combo_counter += 1
            if self._pause_combo_counter >= 30:  # ~0.5 seconds at 60fps
                self._pause_combo_counter = 0
                return True
        else:
            self._pause_combo_counter = 0

        return False

    def _is_controller_combo_held(self):
        """Check if pause combo is currently held on controller."""
        setting = getattr(
            self,
            "_pause_combo_setting",
            {"type": "combo", "buttons": ["START", "SELECT"]},
        )

        try:
            if pygame.joystick.get_count() > 0:
                joy = pygame.joystick.Joystick(0)
                joy.init()
                num_buttons = joy.get_numbuttons()

                if setting.get("type") == "custom":
                    # Custom single button
                    custom_btn = setting.get("button")
                    if custom_btn is not None and custom_btn < num_buttons:
                        return joy.get_button(custom_btn)
                else:
                    # Button combo
                    required_buttons = setting.get("buttons", ["START", "SELECT"])
                    buttons_held = {}

                    for btn_name in required_buttons:
                        btn_indices = (
                            [7]
                            if btn_name == "START"
                            else [6] if btn_name == "SELECT" else []
                        )

                        if self.controller and hasattr(self.controller, "button_map"):
                            btn_indices = self.controller.button_map.get(
                                btn_name, btn_indices
                            )

                        for idx in btn_indices:
                            if isinstance(idx, int) and idx < num_buttons:
                                if joy.get_button(idx):
                                    buttons_held[btn_name] = True
                                    break

                    return all(buttons_held.get(btn, False) for btn in required_buttons)
        except Exception:
            pass
        return False

    def _show_notification(self, text, subtext=None):
        """Show a slide-down notification box."""
        self._notification_text = text
        self._notification_subtext = subtext
        self._notification_timer = self._notification_duration
        self._notification_y = -80  # Start above screen

    def _update_notification(self, dt):
        """Update notification animation."""
        if self._notification_timer <= 0:
            # Slide up and hide
            self._notification_y -= dt * 0.3
            if self._notification_y < -80:
                self._notification_text = None
                self._notification_subtext = None
        else:
            # Slide down
            self._notification_timer -= dt
            if self._notification_y < self._notification_target_y:
                self._notification_y += dt * 0.5
                if self._notification_y > self._notification_target_y:
                    self._notification_y = self._notification_target_y

    def _draw_notification(self, surf):
        """Draw the notification box."""
        if self._notification_text is None:
            return

        # Box dimensions
        box_width = min(self.width - 40, 400)
        box_height = 60 if self._notification_subtext else 40
        box_x = (self.width - box_width) // 2
        box_y = int(self._notification_y)

        # Don't draw if completely off screen
        if box_y < -box_height:
            return

        # Draw shadow (darker version of background)
        shadow_rect = pygame.Rect(box_x + 3, box_y + 3, box_width, box_height)
        pygame.draw.rect(surf, (0, 10, 20), shadow_rect, border_radius=8)

        # Draw box background - using COLOR_HEADER style
        box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(surf, ui_colors.COLOR_HEADER, box_rect, border_radius=8)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, box_rect, 2, border_radius=8)

        # Get font (use self.font or create a default one)
        font = self.font if self.font else pygame.font.Font(None, 24)

        # Draw main text
        text_surf = font.render(self._notification_text, True, ui_colors.COLOR_TEXT)
        text_rect = text_surf.get_rect(centerx=box_x + box_width // 2, top=box_y + 8)
        surf.blit(text_surf, text_rect)

        # Draw subtext - slightly dimmer (use text color with reduced brightness)
        if self._notification_subtext:
            sub_color = tuple(max(0, c - 40) for c in ui_colors.COLOR_TEXT)
            sub_surf = font.render(self._notification_subtext, True, sub_color)
            sub_rect = sub_surf.get_rect(centerx=box_x + box_width // 2, top=box_y + 32)
            surf.blit(sub_surf, sub_rect)

    def _draw_emulator(self, surf):
        """Draw the emulator screen — direct blit, scaler handles upscaling via GPU"""
        # Blit emulator frame directly to the virtual surface (now 240x160)
        emu_surf = self.emulator.get_surface(scale=1)
        surf.blit(emu_surf, (0, 0))

        # Draw pause indicator if paused
        if self.emulator.paused:
            # Dark overlay
            sw, sh = surf.get_size()
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surf.blit(overlay, (0, 0))

            # Pause text (smaller font since we're at 240x160 now)
            try:
                pause_font = pygame.font.Font(FONT_PATH, 8)
            except Exception:
                pause_font = self.font

            pause_text = pause_font.render("PAUSED", True, (255, 255, 0))
            hint_text = pause_font.render(
                self._get_pause_combo_hint_text(), True, (200, 200, 200)
            )

            pause_rect = pause_text.get_rect(center=(sw // 2, sh // 2 - 12))
            hint_rect = hint_text.get_rect(center=(sw // 2, sh // 2 + 12))

            surf.blit(pause_text, pause_rect)
            surf.blit(hint_text, hint_rect)

    def _close_modal(self):
        """Close current modal"""
        self.modal_instance = None
        # Add debounce to prevent immediate menu selection after closing
        self._last_input_time = time.time()
        # Set flag to skip main menu input this frame
        self._modal_just_closed = True

    def _resume_game_from_modal(self):
        """Close modal and resume game (called by START+SELECT in modals)"""
        self.modal_instance = None
        self._last_input_time = time.time()
        self._modal_just_closed = True

        # Resume game if emulator is loaded (same condition as "Resume Game" menu)
        if self.emulator and self.emulator.loaded:
            self._stop_menu_music()
            self.emulator.resume()
            self.emulator_active = True
            # Switch to emulator resolution
            if self.scaler:
                self.scaler.set_virtual_resolution(240, 160)
            print("[Sinew] Resumed game from modal via START+SELECT")

    def _on_event_claimed(self, event_key):
        """
        Callback when an event item is claimed from the Events screen.
        Triggers the corresponding achievement unlock.
        """
        print(f"[Sinew] Event claimed: {event_key}")

        # Map event keys to achievement IDs
        achievement_map = {
            "eon_ticket": "SINEW_107",  # Southern Island Pass
            "aurora_ticket": "SINEW_108",  # Birth Island Pass
            "mystic_ticket": "SINEW_109",  # Navel Rock Pass
            "old_sea_map": "SINEW_110",  # Faraway Island Pass
        }

        # Unlock the per-event achievement
        ach_id = achievement_map.get(event_key)
        if ach_id and self._achievement_manager:
            try:
                from achievements_data import get_achievements_for

                sinew_achs = get_achievements_for("Sinew")
                for ach in sinew_achs:
                    if ach["id"] == ach_id:
                        self._achievement_manager.unlock_achievement(ach)
                        break
            except Exception as e:
                print(f"[Sinew] Error unlocking event achievement: {e}")

        # Check if all 4 events have been claimed across any games for the collector achievement.
        # events_claimed is now per-game: { "Ruby": {"eon_ticket": true}, "LeafGreen": {...} }
        # We flatten across all games to see if every ticket has been given out at least once.
        try:
            from settings import load_sinew_settings

            data = load_sinew_settings()
            all_claimed = data.get("events_claimed", {})

            # Flatten: collect every ticket key claimed across all games
            claimed_anywhere = set()
            for game_data in all_claimed.values():
                if isinstance(game_data, dict):
                    for k, v in game_data.items():
                        if v:
                            claimed_anywhere.add(k)

            all_four = {
                "eon_ticket",
                "aurora_ticket",
                "mystic_ticket",
                "old_sea_map",
            }
            if all_four.issubset(claimed_anywhere):
                from achievements_data import get_achievements_for

                sinew_achs = get_achievements_for("Sinew")
                for ach in sinew_achs:
                    if ach.get("hint") == "all_events_claimed":
                        self._achievement_manager.unlock_achievement(ach)
                        break
        except Exception as e:
            print(f"[Sinew] Error checking all events: {e}")

    def _open_menu(self, name):
        """Open a menu item"""
        if name == "Launch Game":
            self._launch_game()
            return

        if name == "Save File Only":
            # No ROM available - show informational notification, do nothing else
            gname = self.game_names[self.current_game]
            self._show_notification(
                f"{gname}: No ROM found",
                "Place a matching .gba ROM in the roms/ folder",
            )
            return

        if name == "Resume Game":
            # Resume the currently paused game
            if self.emulator and self.emulator.loaded:
                self._stop_menu_music()  # Stop menu music when resuming game
                self.emulator.resume()
                self.emulator_active = True
                # Switch to emulator resolution
                if self.scaler:
                    self.scaler.set_virtual_resolution(240, 160)
                print("[Sinew] Resuming game via menu")
            return

        if name == "Stop Game":
            # Stop the currently running game
            self._stop_game()
            return

        if name == "Quit Sinew":
            # Quit the application
            self._quit_sinew()
            return

        if name.startswith("Playing:"):
            # Show notification about currently playing game
            running_game = self._get_running_game_name()
            self._show_notification(
                f"Currently playing: {running_game}",
                self._get_pause_combo_hint_text("return"),
            )
            return

        modal_w = self.width - 30
        modal_h = self.height - 30

        if name == "Pokedex" and PokedexModal:
            # Check if database exists first
            if not self._check_database(): return

            try:
                # Always collect save paths for potential combined mode
                all_save_paths = []
                for gname, gdata in self.games.items():
                    if gname != "Sinew":
                        sav = gdata.get("sav")
                        if sav and os.path.exists(sav):
                            all_save_paths.append(sav)

                # Check if we're on Sinew (combined mode)
                if self.is_on_sinew():
                    # Combined mode - merged view from all saves
                    self.modal_instance = PokedexModal(
                        close_callback=self._close_modal,
                        get_current_game_callback=self.get_current_game_name,
                        set_game_callback=self._set_game_by_name,
                        prev_game_callback=lambda: self._change_game_include_sinew(-1),
                        next_game_callback=lambda: self._change_game_include_sinew(1),
                        combined_mode=True,
                        all_save_paths=all_save_paths,
                        width=self.width,
                        height=self.height,
                    )
                else:
                    # Single game mode - use current save via manager
                    # Still pass all_save_paths so user can switch to combined mode
                    self.modal_instance = PokedexModal(
                        close_callback=self._close_modal,
                        get_current_game_callback=self.get_current_game_name,
                        set_game_callback=self._set_game_by_name,
                        prev_game_callback=lambda: self._change_game_include_sinew(-1),
                        next_game_callback=lambda: self._change_game_include_sinew(1),
                        save_data_manager=get_manager(),
                        all_save_paths=all_save_paths,
                        width=self.width,
                        height=self.height,
                    )
            except FileNotFoundError:
                self._show_db_warning(
                    "Pokemon database not found",
                    "Build the database first to use the Pokedex.",
                )
                return
        elif name == "PC Box" and PCBox:
            # Pass the combined reload callbacks so modal arrows update everything
            # Include Sinew in the cycle - it has its own storage
            self.modal_instance = PCBox(
                modal_w,
                modal_h,
                self.font,
                close_callback=self._close_modal,
                prev_game_callback=lambda: self._change_game_include_sinew(-1),
                next_game_callback=lambda: self._change_game_include_sinew(1),
                get_current_game_callback=self.get_current_game_name,
                is_game_running_callback=self._get_running_game_name,
                reload_save_callback=self._reload_save_for_game,
                resume_game_callback=self._resume_game_from_modal,
            )
        elif name == "Trainer Info" and TrainerInfoModal:
            self.modal_instance = TrainerInfoModal(
                modal_w,
                modal_h,
                self.font,
                prev_game_callback=lambda: self._change_game_skip_sinew_no_debounce(-1),
                next_game_callback=lambda: self._change_game_skip_sinew_no_debounce(1),
                get_current_game_callback=self.get_current_game_name,
            )
        elif name == "Achievements" and AchievementsModal:
            self.modal_instance = AchievementsModal(
                modal_w,
                modal_h,
                self.font,
                get_current_game_callback=self.get_current_game_name,
            )
        elif name == "Settings" and Settings:
            self.modal_instance = Settings(
                modal_w,
                modal_h,
                self.font,
                close_callback=self._close_modal,
                music_mute_callback=self._set_menu_music_muted,
                fullscreen_callback=self._set_fullscreen,
                swap_ab_callback=self._set_swap_ab,
                db_builder_callback=self._open_db_builder,
                scaler=self.scaler,
                reload_combo_callback=self._reload_pause_combo_setting,
            )
        elif name == "Export" and ExportModal:
            current_game = self.get_current_game_name()
            self.modal_instance = ExportModal(
                modal_w,
                modal_h,
                game_name=current_game,
                close_callback=self._close_modal,
            )
        elif name == "Events" and EventsModal:
            # Events modal - for claiming mystery event items
            # Pass the current game name from the game screen (determined by filename)
            current_game_name = self.get_current_game_name()
            self.modal_instance = EventsModal(
                modal_w,
                modal_h,
                self.font,
                on_close=self._close_modal,
                on_event_claimed=self._on_event_claimed,
                game_name=current_game_name,
            )
        elif name == "DB Builder" and DBBuilder:
            self.modal_instance = DBBuilder(
                modal_w, modal_h, close_callback=self._close_modal
            )
        else:
            # Placeholder modal
            self.modal_instance = PlaceholderModal(
                name, modal_w, modal_h, self.font, self._close_modal
            )

    def _stop_game(self):
        """Stop the currently running game."""
        if self.emulator and self.emulator.loaded:
            game_name = self._get_running_game_name() or "game"
            try:
                self.emulator.save_sram()  # Save before stopping
                self.emulator.unload()
            except Exception as e:
                print(f"[Sinew] Error stopping game: {e}")
            self.emulator_active = False
            # Restore menu virtual resolution
            if self.scaler:
                self.scaler.restore_virtual_resolution()
            # Reset menu index to point at "Launch Game" for quick restart
            self.menu_index = 0
            self._show_notification(f"Stopped: {game_name}", "Game saved")
            print(f"[Sinew] Stopped game: {game_name}")

    def _quit_sinew(self):
        """Quit the Sinew application."""
        print("[Sinew] Quit requested")

        # Stop any running game first
        if self.emulator:
            try:
                if self.emulator.loaded:
                    self.emulator.save_sram()
                self.emulator.shutdown()
            except Exception as e:
                print(f"[Sinew] Error during shutdown: {e}")
            self.emulator = None
            self.emulator_active = False

        # Signal to close - this will be checked by main loop
        self.should_close = True

    def update(self, events, dt):
        """
        Update game screen state

        Args:
            events: List of pygame events
            dt: Delta time in milliseconds

        Returns:
            bool: False if screen should close, True otherwise
        """
        # Reset modal close flag only after cooldown has passed
        if self._modal_just_closed and (
            time.time() - self._last_input_time >= self.INPUT_COOLDOWN
        ):
            self._modal_just_closed = False

        # Update notification animation
        self._update_notification(dt)

        # Update achievement notification
        if self._achievement_notification:
            self._achievement_notification.update()

        # Handle emulator if active
        if self.emulator_active and self.emulator:
            return self._update_emulator(events, dt)

        # [Dev] External emulator closed — reload on the main thread.
        # _on_external_emulator_closed() runs on a bg thread and sets this flag;
        # we act on it here where it's safe to touch pygame/save state.
        if self._ext_emu_closed_needs_reload:
            self._ext_emu_closed_needs_reload = False
            if self.scaler:
                self.scaler.restore_virtual_resolution()
            self.load_game_and_background()
            self._start_menu_music()
            print("[Dev] Reloaded save after external emulator closed")

        # Check for resume combo when emulator is paused but we're in Sinew menu
        self._pause_combo_active = False
        if self.emulator and self.emulator.loaded and not self.emulator_active:
            # Check if combo keys are held (even if not yet triggered)
            combo_held = self._check_pause_combo_direct()

            # Block Enter key while combo keys are being held
            keys = pygame.key.get_pressed()
            if keys[pygame.K_RETURN] and keys[pygame.K_BACKSPACE]:
                self._pause_combo_active = True

            # Resume when combo triggers and was previously released
            if combo_held and self._emulator_pause_combo_released:
                self._emulator_pause_combo_released = False
                print("[Sinew] Resume triggered - calling emulator.resume()")
                print(
                    f"[Sinew] Before resume: paused={self.emulator.paused}, loaded={self.emulator.loaded}"
                )
                self._stop_menu_music()  # Stop menu music when resuming
                self.emulator.resume()
                print(f"[Sinew] After resume: paused={self.emulator.paused}")
                self.emulator_active = True
                # Switch to emulator resolution
                if self.scaler:
                    self.scaler.set_virtual_resolution(240, 160)
                print("[Sinew] Resuming game - emulator_active set to True")
                return True

            # Reset release flag when keys are released
            if not self._pause_combo_active and not self._is_controller_combo_held():
                self._emulator_pause_combo_released = True

        # Update GIF animation for current game
        gname = self.game_names[self.current_game]
        self._ensure_gif_loaded(gname)
        game_data = self.games[gname]

        if game_data["frames"]:
            game_data["time_accum"] += dt
            dur = (
                game_data["durations"][game_data["frame_index"]]
                if game_data["durations"]
                else 100
            )
            if game_data["time_accum"] >= dur:
                game_data["time_accum"] = 0
                game_data["frame_index"] = (game_data["frame_index"] + 1) % len(
                    game_data["frames"]
                )

        # Handle events
        for event in events:
            if self.modal_instance:
                # Pass to modal
                if hasattr(self.modal_instance, "handle_mouse"):
                    self.modal_instance.handle_mouse(event)
                if hasattr(self.modal_instance, "handle_event"):
                    self.modal_instance.handle_event(event)
            elif not self._modal_just_closed and (
                time.time() - self._last_input_time >= self.INPUT_COOLDOWN
            ):
                # Handle main menu events (skip if modal was just closed or within cooldown)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.back_callback:
                            self.back_callback()
                            return False
                    elif event.key == pygame.K_DOWN:
                        menu_items = self.get_menu_items()
                        self.menu_index = (self.menu_index + 1) % len(menu_items)
                    elif event.key == pygame.K_UP:
                        menu_items = self.get_menu_items()
                        self.menu_index = (self.menu_index - 1) % len(menu_items)
                    elif event.key == pygame.K_RIGHT:
                        # previously change_game(1)
                        self._change_game_and_reload(1)
                    elif event.key == pygame.K_LEFT:
                        # previously change_game(-1)
                        self._change_game_and_reload(-1)
                    elif event.key == pygame.K_RETURN:
                        # Don't open menu if pause combo is active (Enter+Backspace held)
                        if not getattr(self, "_pause_combo_active", False):
                            menu_items = self.get_menu_items()
                            if self.menu_index >= len(menu_items):
                                self.menu_index = 0
                            self._open_menu(menu_items[self.menu_index])

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Scroll wheel for menu
                    menu_items = self.get_menu_items()
                    if event.button == 4:
                        self.menu_index = (self.menu_index - 1) % len(menu_items)
                    elif event.button == 5:
                        self.menu_index = (self.menu_index + 1) % len(menu_items)
                    elif event.button == 1:
                        # Check menu button click
                        menu_button = Button(
                            menu_items[self.menu_index],
                            rel_rect=(0.25, 0.65, 0.5, 0.12),
                            callback=lambda item=menu_items[
                                self.menu_index
                            ]: self._open_menu(item),
                        )
                        menu_button.handle_event(event)

        # Handle controller
        if self.controller:
            if self.modal_instance:
                # Pass to modal - let modal handle all its own input including B
                if hasattr(self.modal_instance, "handle_controller"):
                    self.modal_instance.handle_controller(self.controller)
                # Note: Don't check B here - modal handles its own closing
                # and signals via update() returning False
            elif not self._modal_just_closed and (
                time.time() - self._last_input_time >= self.INPUT_COOLDOWN
            ):
                # Main menu controller (skip if modal was just closed or within cooldown)
                menu_items = self.get_menu_items()

                if self.controller.is_dpad_just_pressed("up"):
                    self.controller.consume_dpad("up")
                    self.menu_index = (self.menu_index - 1) % len(menu_items)

                if self.controller.is_dpad_just_pressed("down"):
                    self.controller.consume_dpad("down")
                    self.menu_index = (self.menu_index + 1) % len(menu_items)

                if self.controller.is_dpad_just_pressed("left"):
                    self.controller.consume_dpad("left")
                    # reload on change
                    self._change_game_and_reload(-1)

                if self.controller.is_dpad_just_pressed("right"):
                    self.controller.consume_dpad("right")
                    self._change_game_and_reload(1)

                if self.controller.is_button_just_pressed("L"):
                    self.controller.consume_button("L")
                    self._change_game_and_reload(-1)

                if self.controller.is_button_just_pressed("R"):
                    self.controller.consume_button("R")
                    self._change_game_and_reload(1)

                if self.controller.is_button_just_pressed("A"):
                    self.controller.consume_button("A")
                    if self.menu_index >= len(menu_items):
                        self.menu_index = 0
                    self._open_menu(menu_items[self.menu_index])

                if self.controller.is_button_just_pressed("B"):
                    self.controller.consume_button("B")
                    if self.back_callback:
                        self.back_callback()
                        return False

        # Update modal
        if self.modal_instance:
            if hasattr(self.modal_instance, "update"):
                result = self.modal_instance.update(events)
                if not result:
                    self._close_modal()

        return not self.should_close

    def draw(self, surf):
        """Draw the game screen"""
        # Draw emulator if active
        if self.emulator_active and self.emulator:
            self._draw_emulator(surf)
            return

        # Draw background (animated GIF, solid color, or Sinew logo)
        gname = self.game_names[self.current_game]
        game_data = self.games[gname]

        if self.is_on_sinew():
            # Sinew background - full screen like other games
            if self.sinew_logo:
                surf.blit(self.sinew_logo, (0, 0))
            else:
                surf.fill(self.sinew_bg_color)
        elif game_data["frames"]:
            bg_surf = game_data["frames"][game_data["frame_index"]]
            surf.blit(bg_surf, (0, 0))
        else:
            surf.fill(ui_colors.COLOR_BG)

        # Draw main menu or modal
        if self.modal_instance:
            # Draw modal - use modal's own dimensions if available
            if hasattr(self.modal_instance, "width") and hasattr(
                self.modal_instance, "height"
            ):
                modal_w = self.modal_instance.width
                modal_h = self.modal_instance.height
            else:
                modal_w = self.width - 30
                modal_h = self.height - 30

            modal_surf = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)

            if hasattr(self.modal_instance, "draw"):
                self.modal_instance.draw(modal_surf)

            pygame.draw.rect(
                modal_surf, ui_colors.COLOR_BORDER, (0, 0, modal_w, modal_h), 2
            )

            # Center the modal on screen
            modal_x = (self.width - modal_w) // 2
            modal_y = (self.height - modal_h) // 2
            surf.blit(modal_surf, (modal_x, modal_y))

            # Draw resume game banner on top of modal (if game is paused)
            if self.emulator and self.emulator.loaded and not self.emulator_active:
                self._draw_resume_banner(surf)
        else:
            # Draw menu button
            menu_items = self.get_menu_items()
            # Ensure menu_index is within bounds (menu can change dynamically)
            if self.menu_index >= len(menu_items):
                self.menu_index = 0

            current_menu_item = menu_items[self.menu_index]
            is_disabled = current_menu_item == "Save File Only"

            menu_button = Button(
                current_menu_item,
                rel_rect=(0.25, 0.65, 0.5, 0.12),
                callback=lambda: None,
            )

            if is_disabled:
                # Draw a visually distinct greyed-out version
                btn_rect = menu_button.rect if hasattr(menu_button, "rect") else None
                # Compute rect the same way Button does
                bx = int(0.25 * self.width)
                by = int(0.65 * self.height)
                bw = int(0.5 * self.width)
                bh = int(0.12 * self.height)
                btn_rect = pygame.Rect(bx, by, bw, bh)

                # Greyed-out fill and muted border
                pygame.draw.rect(surf, (50, 50, 55), btn_rect, border_radius=4)
                pygame.draw.rect(surf, (80, 80, 85), btn_rect, 2, border_radius=4)

                # Dim text
                try:
                    btn_font = pygame.font.Font(FONT_PATH, 14)
                except Exception:
                    btn_font = self.font
                txt_surf = btn_font.render(current_menu_item, True, (100, 100, 105))
                txt_rect = txt_surf.get_rect(center=btn_rect.center)
                surf.blit(txt_surf, txt_rect)

                # Small lock / no-entry icon hint below
                try:
                    hint2_font = pygame.font.Font(FONT_PATH, 7)
                except Exception:
                    hint2_font = pygame.font.SysFont(None, 12)
                hint2_surf = hint2_font.render(
                    "No ROM — place a .gba file in roms/", True, (90, 90, 90)
                )
                hint2_rect = hint2_surf.get_rect(
                    centerx=self.width // 2, top=btn_rect.bottom + 3
                )
                surf.blit(hint2_surf, hint2_rect)
            else:
                menu_button.draw(surf, self.font)

            # Draw navigation hints at bottom of screen
            hint_text = "< > Change Game    ^ v Scroll Menu"
            try:
                hint_font = pygame.font.Font(FONT_PATH, 8)
            except Exception:
                hint_font = pygame.font.SysFont(None, 14)
            hint_surf = hint_font.render(hint_text, True, (150, 150, 150))
            hint_rect = hint_surf.get_rect(
                centerx=self.width // 2, bottom=self.height - 5
            )
            surf.blit(hint_surf, hint_rect)

            # Draw resume game banner at top if emulator is paused
            if self.emulator and self.emulator.loaded and not self.emulator_active:
                self._draw_resume_banner(surf)

        # Draw notification on top of everything
        self._draw_notification(surf)

        # Draw achievement notification on top of everything else
        if self._achievement_notification:
            self._achievement_notification.draw(surf)

    def cleanup(self):
        """Cleanup resources when closing the game screen"""
        if self.emulator:
            try:
                self.emulator.shutdown()
            except Exception as e:
                print(f"[Sinew] Cleanup error: {e}")
            self.emulator = None
        self.emulator_active = False


# For backwards compatibility - can still run standalone
if __name__ == "__main__":
    from controller import get_controller
    from scaler import Scaler

    pygame.init()

    # Pre-initialize mixer before video mode changes (helps with fullscreen audio)
    # GBA sample rate is typically 32768 Hz
    try:
        pygame.mixer.pre_init(frequency=32768, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        print(f"[Main] Mixer pre-initialized: {pygame.mixer.get_init()}")
    except Exception as e:
        print(f"[Main] Mixer pre-init failed: {e}")

    # Load saved theme preference
    try:
        from theme_manager import load_theme_preference

        load_theme_preference()
        print("[Main] Theme preference loaded")
    except Exception as e:
        print(f"[Main] Could not load theme preference: {e}")

    # =========================================================================
    # SCALER SETUP
    # =========================================================================
    # Virtual resolution - what the game renders at (fixed)
    VIRTUAL_WIDTH = 480
    VIRTUAL_HEIGHT = 320

    # Initial window size (2x scale)
    WINDOW_WIDTH = 960
    WINDOW_HEIGHT = 640

    # Load fullscreen setting.
    # On handhelds there is no windowed mode — always fullscreen regardless of
    # what's saved. On desktop, respect the user's saved preference.
    if IS_HANDHELD:
        start_fullscreen = True
    else:
        start_fullscreen = False
        try:
            settings = load_settings()
            start_fullscreen = settings.get("fullscreen", False)
        except Exception:
            pass

    # Create scaler
    scaler = Scaler(
        virtual_width=VIRTUAL_WIDTH,
        virtual_height=VIRTUAL_HEIGHT,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        fullscreen=start_fullscreen,
        integer_scaling=False,
    )

    # Get the virtual surface to render to
    screen = scaler.get_surface()

    clock = pygame.time.Clock()
    font = pygame.font.Font(FONT_PATH, 18)
    controller = get_controller()

    # Start with GameScreen using virtual resolution
    game_screen = GameScreen(
        VIRTUAL_WIDTH, VIRTUAL_HEIGHT, font, controller=controller, scaler=scaler,
        screen=screen
    )

    # Precache all GIF backgrounds and save files to eliminate lag when switching
    game_screen.precache_all(screen)

    running = True
    while running:
        dt = clock.tick(60)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

            # Handle window resize
            elif event.type == pygame.VIDEORESIZE:
                scaler.handle_resize(event.w, event.h)

            # Handle fullscreen toggle (F11 or Alt+Enter)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    scaler.toggle_fullscreen()
                elif event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT):
                    scaler.toggle_fullscreen()

            # Convert mouse coordinates for mouse events
            if event.type in (
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
            ):
                event.pos = scaler.scale_mouse(event.pos)

            controller.process_event(event)

        # Update controller AFTER event.get() so key.get_pressed() is current
        controller.update(dt)

        # Strip KEYDOWN/KEYUP events for keys the controller already handles
        # via keyboard polling.  This prevents double-processing (once through
        # controller.handle_controller and once through raw KEYDOWN handlers).
        filtered_events = controller.filter_kb_events(events)

        # Check if game_screen wants to close
        if game_screen.should_close:
            running = False
            continue

        if not game_screen.update(filtered_events, dt):
            running = False

        # Render to virtual surface
        screen = scaler.get_surface()
        game_screen.draw(screen)

        # Scale and display to window
        scaler.blit_scaled()

    # Cleanup before exiting
    game_screen.cleanup()
    pygame.quit()