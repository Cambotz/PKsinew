#!/usr/bin/env python3

"""
Sinew Configuration
All paths, constants, and configuration settings

NOTE: All paths are absolute and should be constructed using os.path.join for cross-platform compatibility.
"""

import os
import platform
import sys

# ===== Display Settings =====
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320  # 3.5" screen
SCREEN_WIDTH = WINDOW_WIDTH  # Alias for compatibility
SCREEN_HEIGHT = WINDOW_HEIGHT
FPS = 60


# ===== Directory Paths =====

# Core directories (internal, read-only)
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
CORES_DIR = os.path.join(BASE_DIR, "cores")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
PARSER_DIR = os.path.join(BASE_DIR, "parser")

# External (user-accessible) directories and files
if os.environ.get("SINEW_BASE_DIR"):
    # PortMaster / handheld: launcher script tells us where everything is
    EXT_DIR = os.environ["SINEW_BASE_DIR"]
    # On handheld, cores/fonts/parser are alongside src/, not inside it
    CORES_DIR = os.path.join(EXT_DIR, "cores")
    FONTS_DIR = os.path.join(EXT_DIR, "fonts")
    PARSER_DIR = os.path.join(EXT_DIR, "parser")
elif getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    appimage_path = os.environ.get("APPIMAGE")
    if appimage_path:
        # Use the directory of the AppImage
        EXT_DIR = os.path.dirname(appimage_path)
    else:
        EXT_DIR = os.path.dirname(sys.executable)
else:
    EXT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../dist"))

DATA_DIR = os.path.join(EXT_DIR, "data")
ROMS_DIR = os.path.join(EXT_DIR, "roms")
SAVES_DIR = os.path.join(EXT_DIR, "saves")
SYSTEM_DIR = os.path.join(EXT_DIR, "system")

# Sinew-specific save paths
ACH_SAVE_PATH = os.path.join(SAVES_DIR, "sinew", "achievements_progress.json")
ACH_REWARDS_PATH = os.path.join(DATA_DIR, "achievements", "rewards", "rewards.json")
SETTINGS_FILE = os.path.join(SAVES_DIR, "sinew", "sinew_settings.json")

# Sprite directories
THEMES_DIR = os.path.join(DATA_DIR, "themes")
SPRITES_DIR = os.path.join(DATA_DIR, "sprites")

GEN3_SPRITES_DIR = os.path.join(SPRITES_DIR, "gen3")
GEN3_NORMAL_DIR = os.path.join(GEN3_SPRITES_DIR, "normal")
GEN3_SHINY_DIR = os.path.join(GEN3_SPRITES_DIR, "shiny")

SHOWDOWN_SPRITES_DIR = os.path.join(SPRITES_DIR, "showdown")
SHOWDOWN_NORMAL_DIR = os.path.join(SHOWDOWN_SPRITES_DIR, "normal")
SHOWDOWN_SHINY_DIR = os.path.join(SHOWDOWN_SPRITES_DIR, "shiny")

GEN3_BOX_DIR = os.path.join(SPRITES_DIR, "gen3box")
GEN3_BOX_ANIM_DIR = os.path.join(SPRITES_DIR, "gen3box")

GEN8_ICONS_DIR = os.path.join(SPRITES_DIR, "gen8", "icons")

TITLE_SPRITES_DIR = os.path.join(SPRITES_DIR, "title")

# Database paths
POKEMON_DB_PATH = os.path.join(DATA_DIR, "pokemon_db.json")

# Font Paths
FONT_PATH = os.path.join(FONTS_DIR, "Pokemon_GB.ttf")
FONT_SOLID_PATH = os.path.join(FONTS_DIR, "Pokemon Solid.ttf")
# ===== Emulator Paths =====
# Platform-specific core detection


def get_platform_info():
    """Get platform and architecture info for core selection."""
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

        arch_name = "x64" if struct.calcsize("P") == 8 else "x86"

    return os_name, arch_name, ext


def get_core_filename():
    """Get the platform-specific mGBA core filename."""
    os_name, arch_name, ext = get_platform_info()
    return f"mgba_libretro_{os_name}_{arch_name}{ext}"


MGBA_CORE_PATH = os.path.join(CORES_DIR, get_core_filename())

# ===== Platform Flags =====
# True when running on an embedded Linux ARM handheld (PortMaster / ROCKNIX / ArkOS etc.)
# Used to force fullscreen on startup and hide the fullscreen toggle in settings.
def _is_handheld():
    # PortMaster always sets SINEW_BASE_DIR in the launch script — most reliable signal
    if os.environ.get("SINEW_BASE_DIR"):
        return True
    # Fallback: native Linux ARM without AppImage wrapping = handheld build
    _sys = platform.system().lower()
    _mach = platform.machine().lower()
    if _sys == "linux" and _mach in ("aarch64", "arm64", "armv7l", "armv6l"):
        return True
    return False

IS_HANDHELD = _is_handheld()


# ===== Save Editor Paths =====

# GBA ROM identification
# Detection order for .gba files:
#   1. SHA-1 hash  -> exact vanilla dump match (all regions/revisions)
#   2. Header code -> ROM hack fallback (hacks inherit base game header at 0xAC)
#   3. Keyword     -> filename fallback for zips or anything else

# Header codes used as fallback for ROM hacks (inherit from base game)
_ROM_HEADER_CODES = {
    "BPRE": "FireRed",   "BPGE": "LeafGreen",
    "AXVE": "Ruby",      "AXPE": "Sapphire",
    "BPEE": "Emerald",   "BPRJ": "FireRed",
    "BPGJ": "LeafGreen", "AXVJ": "Ruby",
    "AXPJ": "Sapphire",  "BPEJ": "Emerald",
    "BPRD": "FireRed",   "BPGD": "LeafGreen",
    "AXVD": "Ruby",      "AXPD": "Sapphire",
    "BPED": "Emerald",   "BPRF": "FireRed",
    "BPGF": "LeafGreen", "AXVF": "Ruby",
    "AXPF": "Sapphire",  "BPEF": "Emerald",
    "BPRI": "FireRed",   "BPGI": "LeafGreen",
    "AXVI": "Ruby",      "AXPI": "Sapphire",
    "BPEI": "Emerald",   "BPRS": "FireRed",
    "BPGS": "LeafGreen", "AXVS": "Ruby",
    "AXPS": "Sapphire",  "BPES": "Emerald",
}

# SHA-1 hash lookup - built once on first use from data/games.json
_ROM_HASH_LOOKUP = {}  # sha1_hex -> game_name


def _load_rom_hashes():
    """Load games.json and build the SHA-1 lookup dict. No-op after first call."""
    if _ROM_HASH_LOOKUP:
        return

    hash_file = os.path.join(DATA_DIR, "games.json")
    if not os.path.exists(hash_file):
        print(f"[ROMDetect] games.json not found at {hash_file}")
        return

    try:
        import json
        with open(hash_file, "r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            sha1 = entry.get("sha1", "").lower().strip()
            game = entry.get("game", "")
            if sha1 and game:
                _ROM_HASH_LOOKUP[sha1] = game
        print(f"[ROMDetect] Loaded {len(_ROM_HASH_LOOKUP)} ROM hashes")
    except Exception as e:
        print(f"[ROMDetect] Failed to load games.json: {e}")


def identify_rom(rom_path):
    """
    Identify a GBA ROM file and return the canonical game name.

    Detection order:
      1. SHA-1 hash  — exact match against known vanilla dumps (all regions)
      2. Header code — fallback for ROM hacks (inherit base game serial at 0xAC)

    Args:
        rom_path: Path to a .gba ROM file

    Returns:
        str: Game name e.g. "Emerald", or None if unrecognised
    """
    import hashlib

    basename = os.path.basename(rom_path)

    try:
        with open(rom_path, "rb") as f:
            rom_data = f.read()
    except Exception as e:
        print(f"[ROMDetect] Could not read {basename}: {e}")
        return None

    # 1. SHA-1 hash check
    _load_rom_hashes()
    sha1 = hashlib.sha1(rom_data).hexdigest().lower()
    game = _ROM_HASH_LOOKUP.get(sha1)
    if game:
        print(f"[ROMDetect] Hash match: {basename} -> {game} (sha1={sha1[:8]}...)")
        return game

    # 2. Header code fallback (ROM hacks keep base game serial)
    try:
        code = rom_data[0xAC:0xB0].decode("ascii", errors="replace")
        game = _ROM_HEADER_CODES.get(code)
        if game:
            print(f"[ROMDetect] Header fallback: {basename} serial={code} -> {game} (ROM hack or unknown dump)")
            return game
    except Exception:
        pass

    print(f"[ROMDetect] Unrecognised ROM: {basename} (sha1={sha1[:8]}...)")
    return None


SAVES_PATH = SAVES_DIR  # Alias for compatibility

# ROM and Save paths for each game
ROM_PATHS = {
    "FireRed": os.path.join(ROMS_DIR, "FireRed.gba"),
    "LeafGreen": os.path.join(ROMS_DIR, "LeafGreen.gba"),
    "Ruby": os.path.join(ROMS_DIR, "Ruby.gba"),
    "Sapphire": os.path.join(ROMS_DIR, "Sapphire.gba"),
    "Emerald": os.path.join(ROMS_DIR, "Emerald.gba"),
}

SAVE_PATHS = {
    "FireRed": os.path.join(SAVES_DIR, "FireRed.sav"),
    "LeafGreen": os.path.join(SAVES_DIR, "LeafGreen.sav"),
    "Ruby": os.path.join(SAVES_DIR, "Ruby.sav"),
    "Sapphire": os.path.join(SAVES_DIR, "Sapphire.sav"),
    "Emerald": os.path.join(SAVES_DIR, "Emerald.sav"),
}

# ===== Parser Settings =====
PARSER_LOCATIONS = [
    os.path.join(BASE_DIR, "parser"),
]

# ===== Audio Defaults =====
# Platform-tuned defaults for the pygame mixer buffer size and the internal
# audio-queue depth used by the emulator's audio thread.  These can be
# overridden per-user via the mGBA → Audio section in Settings.
AUDIO_BUFFER_DEFAULT = 1024        # samples – desktop / generic
AUDIO_BUFFER_DEFAULT_ARM = 256     # samples – Linux ARM handhelds
AUDIO_QUEUE_DEPTH_DEFAULT = 4      # max queued chunks before dropping

# Allowed slider values exposed in Settings
AUDIO_BUFFER_OPTIONS  = [128, 256, 512, 1024, 2048, 4096]
AUDIO_QUEUE_OPTIONS   = [2, 3, 4, 6, 8, 12, 16]

# Master volume range (0–100, stored as int, applied as 0.0–1.0)
VOLUME_DEFAULT = 80
VOLUME_MIN = 0
VOLUME_MAX = 100
VOLUME_STEP = 5          # each d-pad press changes by this much

# ===== Animation Settings =====
SHOWDOWN_FRAME_MS_DEFAULT = 100

# ===== UI Layout Constants =====
HEADER_HEIGHT_RATIO = 0.1
CARD_SIZE_RATIO = 0.25
CARDS_PER_ROW = 3

# ===== Colors =====
COLOR_BG = (24, 24, 32)
COLOR_ACCENT = (80, 120, 200)


# ===== Helper Functions =====
def get_save_path(game_name):
    """Get save file path for a game by name."""
    return SAVE_PATHS.get(game_name, os.path.join(SAVES_DIR, f"{game_name}.sav"))


def get_rom_path(game_name):
    """Get ROM file path for a game by name."""
    return ROM_PATHS.get(game_name, os.path.join(ROMS_DIR, f"{game_name}.gba"))


def get_sprite_path(species, shiny=False, sprite_type="gen3"):
    """
    Get sprite path for a Pokemon species.

    Args:
        species: National dex number
        shiny: Whether to get shiny sprite
        sprite_type: "gen3", "showdown", or "gen8"

    Returns:
        str: Absolute path to sprite file
    """
    species_str = str(species).zfill(3)

    if sprite_type == "gen3":
        folder = GEN3_SHINY_DIR if shiny else GEN3_NORMAL_DIR
        return os.path.join(folder, f"{species_str}.png")
    elif sprite_type == "showdown":
        folder = SHOWDOWN_SHINY_DIR if shiny else SHOWDOWN_NORMAL_DIR
        return os.path.join(folder, f"{species_str}.gif")
    elif sprite_type == "gen8":
        return os.path.join(GEN8_ICONS_DIR, f"{species_str}.png")
    else:
        return os.path.join(GEN3_NORMAL_DIR, f"{species_str}.png")


def get_title_gif_path(game_name):
    """
    Get title screen GIF path for a game.

    Args:
        game_name: Name of the game (e.g., "Ruby", "Emerald")

    Returns:
        str: Absolute path to title GIF
    """
    return os.path.join(TITLE_SPRITES_DIR, f"{game_name.lower()}.gif")


def get_egg_sprite_path(sprite_type="gen3"):
    """
    Get egg sprite path.

    Args:
        sprite_type: "gen3" or "showdown"

    Returns:
        str: Absolute path to egg sprite
    """
    if sprite_type == "showdown":
        return os.path.join(SHOWDOWN_NORMAL_DIR, "egg.gif")
    else:
        return os.path.join(GEN3_NORMAL_DIR, "egg.png")


# ===== Directory Creation =====
# Create necessary directories if they don't exist
# Other external directories (data, themes, sprites) should be included in the distribution
for dir_path in [ROMS_DIR, SAVES_DIR, SYSTEM_DIR, os.path.dirname(SETTINGS_FILE)]:
    os.makedirs(dir_path, exist_ok=True)


# ===== Debug Info =====
def print_paths():
    """Print all configured paths for debugging."""
    print("=" * 50)
    print("PKsinew Path Configuration")
    print("=" * 50)
    print(f"BASE_DIR:     {BASE_DIR}")
    print(f"EXT_DIR:      {EXT_DIR}")
    print(f"DATA_DIR:     {DATA_DIR}")
    print(f"SPRITES_DIR:  {SPRITES_DIR}")
    print(f"FONTS_DIR:    {FONTS_DIR}")
    print(f"FONT_PATH:    {FONT_PATH}")
    print(f"ROMS_DIR:     {ROMS_DIR}")
    print(f"SAVES_DIR:    {SAVES_DIR}")
    print(f"CORES_DIR:    {CORES_DIR}")
    print(f"MGBA_CORE:    {MGBA_CORE_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    print_paths()