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

# Core directories (internal, read-only - bundled with PyInstaller)
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
CORES_DIR = os.path.join(BASE_DIR, "cores")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
PARSER_DIR = os.path.join(BASE_DIR, "parser")

# External (user-accessible) directories and files
if os.environ.get("SINEW_BASE_DIR"):
    # PortMaster / handheld: launcher script tells us where data/roms/saves live
    EXT_DIR = os.environ["SINEW_BASE_DIR"]
    # NOTE: cores/fonts/parser stay in BASE_DIR (PyInstaller bundle)
    # Only data/roms/saves/system move to EXT_DIR
elif getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    appimage_path = os.environ.get("APPIMAGE")
    if appimage_path:
        # Use the directory of the AppImage
        EXT_DIR = os.path.dirname(appimage_path)
    else:
        EXT_DIR = os.path.dirname(sys.executable)
else:
    # Development mode: everything in ../dist
    EXT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../dist"))
    # In dev mode, cores/fonts/parser might also be in dist
    if os.path.exists(os.path.join(EXT_DIR, "cores")):
        CORES_DIR = os.path.join(EXT_DIR, "cores")
    if os.path.exists(os.path.join(EXT_DIR, "fonts")):
        FONTS_DIR = os.path.join(EXT_DIR, "fonts")
    if os.path.exists(os.path.join(EXT_DIR, "parser")):
        PARSER_DIR = os.path.join(EXT_DIR, "parser")

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


def _detect_cfw():
    """
    Detect which CFW is running (for CFW-specific tweaks).
    Returns CFW name string or None if not on a handheld.
    """
    if not IS_HANDHELD:
        return None
    
    # Check for CFW-specific markers
    # AmberELEC: /etc/os-release contains "AmberELEC"
    # ArkOS: /etc/os-release contains "ArkOS"
    # ROCKNIX: /etc/os-release contains "ROCKNIX" or "JELOS" (former name)
    # muOS: Check for /opt/muos/
    # Knulli: Check for /usr/share/knulli
    
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if 'amberelec' in content:
                    return 'amberelec'
                elif 'arkos' in content:
                    return 'arkos'
                elif 'rocknix' in content or 'jelos' in content:
                    return 'rocknix'
        
        # muOS detection - check for muOS-specific directory
        if os.path.exists('/opt/muos/'):
            return 'muos'
        
        # Knulli detection - check for Knulli-specific directory
        if os.path.exists('/usr/share/knulli'):
            return 'knulli'
            
    except Exception as e:
        print(f"[CFW Detection] Failed: {e}")
    
    return 'unknown'


CFW_NAME = _detect_cfw() if IS_HANDHELD else None


def _detect_video_driver():
    """
    Detect which video driver is in use.
    Returns 'panfrost' (open-source Mali), 'mali' (proprietary), or None.
    """
    if not IS_HANDHELD:
        return None
    
    try:
        # Check /sys/module for loaded kernel modules
        if os.path.exists('/sys/module/panfrost'):
            return 'panfrost'
        elif os.path.exists('/sys/module/mali'):
            return 'mali'
        elif os.path.exists('/sys/module/mali_kbase'):
            return 'mali'
        
    except Exception as e:
        print(f"[Video Driver Detection] Failed: {e}")
    
    return 'unknown'


VIDEO_DRIVER = _detect_video_driver() if IS_HANDHELD else None


# ===== Save Editor Paths =====

# GBA ROM identification
# Detection order for .gba and .zip files:
#   1. SHA-1 hash  -> exact vanilla dump match (all regions/revisions)
#   2. Header code -> ROM hack fallback (hacks inherit base game header at 0xAC)
#   3. Keyword     -> filename fallback for unrecognised files

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


def _extract_rom_from_zip(zip_path):
    """
    Extract a .gba ROM from a .zip file.
    
    Args:
        zip_path: Path to .zip file
    
    Returns:
        bytes: ROM data, or None if no .gba found
    """
    import zipfile
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Find first .gba file in the zip
            gba_files = [name for name in zf.namelist() if name.lower().endswith('.gba')]
            
            if not gba_files:
                print(f"[ROMDetect] No .gba file found in {os.path.basename(zip_path)}")
                return None
            
            # Extract the first .gba file
            gba_filename = gba_files[0]
            if len(gba_files) > 1:
                print(f"[ROMDetect] Multiple .gba files in zip, using: {gba_filename}")
            
            rom_data = zf.read(gba_filename)
            print(f"[ROMDetect] Extracted {gba_filename} from {os.path.basename(zip_path)} ({len(rom_data)} bytes)")
            return rom_data
            
    except Exception as e:
        print(f"[ROMDetect] Failed to extract from {os.path.basename(zip_path)}: {e}")
        return None


def identify_rom(rom_path, keywords_hint=None):
    """
    Identify a GBA ROM file and return the canonical game name with priority.
    Supports both .gba and .zip files (will extract .gba from zip).

    Detection order (priority):
      1. Filename keyword check (fast) - skip non-Pokemon ROMs entirely
      2. SHA-1 hash  — exact match against known vanilla dumps (PRIORITY 1)
      3. Header code — fallback for ROM hacks (PRIORITY 2)

    Args:
        rom_path: Path to a .gba or .zip file
        keywords_hint: Optional list of keywords to check filename
                      (performance optimization - skips hashing non-Pokemon ROMs)

    Returns:
        tuple: (game_name, priority) where priority is:
               1 = Official ROM (hash match)
               2 = ROM hack (header match)
               None if unrecognized
    """
    import hashlib

    basename = os.path.basename(rom_path)
    
    # OPTIMIZATION: Check filename keywords FIRST (before reading/hashing)
    # This applies to BOTH .gba and .zip files
    if keywords_hint:
        name_lower = basename.lower()
        has_keyword = any(kw.lower() in name_lower for kw in keywords_hint)
        if not has_keyword:
            # Doesn't look like a Pokemon ROM - skip entirely
            return None
    
    rom_data = None

    try:
        # Handle .zip files
        if rom_path.lower().endswith('.zip'):
            rom_data = _extract_rom_from_zip(rom_path)
            if rom_data is None:
                return None
        else:
            # Regular .gba file - only read if it passed keyword filter
            with open(rom_path, "rb") as f:
                rom_data = f.read()
    except Exception as e:
        print(f"[ROMDetect] Could not read {basename}: {e}")
        return None

    # 1. SHA-1 hash check (PRIORITY 1 - Official ROM)
    _load_rom_hashes()
    sha1 = hashlib.sha1(rom_data).hexdigest().lower()
    game = _ROM_HASH_LOOKUP.get(sha1)
    if game:
        print(f"[ROMDetect] Hash match: {basename} -> {game} (sha1={sha1[:8]}...)")
        return (game, 1)  # Priority 1 = Official ROM

    # 2. Header code fallback (PRIORITY 2 - ROM hack)
    try:
        code = rom_data[0xAC:0xB0].decode("ascii", errors="replace")
        game = _ROM_HEADER_CODES.get(code)
        if game:
            print(f"[ROMDetect] Header fallback: {basename} serial={code} -> {game} (ROM hack or unknown dump)")
            return (game, 2)  # Priority 2 = ROM hack
    except Exception:
        pass

    print(f"[ROMDetect] Unrecognised ROM: {basename} (sha1={sha1[:8]}...)")
    return None


def extract_zip_to_temp(zip_path):
    """
    Extract .gba ROM from zip to a temporary location for emulator loading.
    
    Args:
        zip_path: Path to .zip file
    
    Returns:
        str: Path to extracted .gba file in temp directory, or None if failed
    """
    import zipfile
    import tempfile
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Find first .gba file
            gba_files = [name for name in zf.namelist() if name.lower().endswith('.gba')]
            
            if not gba_files:
                print(f"[ZipExtract] No .gba file found in {os.path.basename(zip_path)}")
                return None
            
            gba_filename = gba_files[0]
            
            # Create temp directory for extracted ROMs
            temp_dir = os.path.join(tempfile.gettempdir(), 'sinew_roms')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Extract to temp with original filename
            temp_rom_path = os.path.join(temp_dir, os.path.basename(gba_filename))
            
            with open(temp_rom_path, 'wb') as f:
                f.write(zf.read(gba_filename))
            
            print(f"[ZipExtract] Extracted {gba_filename} to {temp_rom_path}")
            return temp_rom_path
            
    except Exception as e:
        print(f"[ZipExtract] Failed to extract {os.path.basename(zip_path)}: {e}")
        return None


def cleanup_temp_roms():
    """Clean up temporary extracted ROM files"""
    import tempfile
    import shutil
    
    temp_dir = os.path.join(tempfile.gettempdir(), 'sinew_roms')
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            print(f"[ZipExtract] Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            print(f"[ZipExtract] Failed to clean temp directory: {e}")


# ==============================================================================
# SAVE FILE DETECTION SYSTEM
# ==============================================================================

# Game code mappings for save file detection
# These are 4-byte game codes stored at Section 0 + 0xAC in Gen 3 saves
_SAVE_GAME_CODES = {
    b'BPRE': 'FireRed',    # FireRed (USA/Europe)
    b'BPRJ': 'FireRed',    # FireRed (Japan)
    b'BPGE': 'LeafGreen',  # LeafGreen (USA/Europe)
    b'BPGJ': 'LeafGreen',  # LeafGreen (Japan)
    b'AXVE': 'Ruby',       # Ruby (USA/Europe)
    b'AXVJ': 'Ruby',       # Ruby (Japan)
    b'AXPE': 'Sapphire',   # Sapphire (USA/Europe)
    b'AXPJ': 'Sapphire',   # Sapphire (Japan)
    b'BPEE': 'Emerald',    # Emerald (USA/Europe)
    b'BPEJ': 'Emerald',    # Emerald (Japan)
}

# Save scan cache - maps saves_dir -> {save_path -> game_name | None}
_save_scan_cache = {}


def identify_save(save_path):
    """
    Identify a Gen 3 Pokemon save file by reading its game code.
    
    Gen 3 saves are 128KB with two save slots. Each slot contains 14 sections.
    The game code is stored at Section 0 + 0xAC (4 bytes).
    
    Detection strategy:
    1. Find active save slot (highest save index)
    2. Locate Section 0 in active slot
    3. Read game code at offset 0xAC
    4. Map to canonical game name
    
    Args:
        save_path: Path to a .sav file
        
    Returns:
        str: Game name (e.g., "FireRed", "Emerald") or None if unrecognized
    """
    import struct
    
    basename = os.path.basename(save_path)
    
    try:
        with open(save_path, 'rb') as f:
            data = f.read()
    except Exception as e:
        print(f"[SaveDetect] Could not read {basename}: {e}")
        return None
    
    # Gen 3 saves are exactly 128KB
    if len(data) != 131072:
        return None  # Not a Gen 3 save or corrupted
    
    # Find the active save slot by checking save index at each slot
    # Save index is stored at offset 0x0FFC in slot A and 0xEFFC in slot B
    try:
        import struct
        slot_a_index = struct.unpack('<I', data[0x0FFC:0x1000])[0]
        slot_b_index = struct.unpack('<I', data[0xEFFC:0xF000])[0]
        
        # Active slot is the one with higher save index
        active_slot_offset = 0xE000 if slot_b_index > slot_a_index else 0x0000
        active_slot = 'B' if slot_b_index > slot_a_index else 'A'
    except Exception as e:
        print(f"[SaveDetect] Could not read save indices for {basename}: {e}")
        return None
    
    # Find Section 0 within the active slot
    # Each section is 4096 bytes, section ID is at offset +0xFF4
    section_0_offset = None
    
    for i in range(14):  # 14 sections per save slot
        section_offset = active_slot_offset + (i * 0x1000)
        section_id_offset = section_offset + 0xFF4
        
        try:
            section_id = struct.unpack('<H', data[section_id_offset:section_id_offset+2])[0]
            if section_id == 0:
                section_0_offset = section_offset
                break
        except Exception:
            continue
    
    if section_0_offset is None:
        return None
    
    # Read game code at Section 0 + 0xAC (4 bytes)
    game_code_offset = section_0_offset + 0xAC
    
    try:
        game_code = data[game_code_offset:game_code_offset+4]
        game_name = _SAVE_GAME_CODES.get(game_code)
        
        if game_name:
            print(f"[SaveDetect] Identified {basename} -> {game_name} (code={game_code.decode('ascii', errors='replace')}, slot={active_slot})")
            return game_name
    except Exception:
        pass
    
    return None


def _build_save_scan_cache(saves_dir):
    """
    Scan saves_dir once, identify every .sav file, and cache the results.
    Subsequent calls with the same directory are a no-op.
    
    Args:
        saves_dir: Directory containing .sav or .srm files
    """
    if saves_dir in _save_scan_cache:
        return
    
    scan = {}
    
    if not os.path.exists(saves_dir):
        _save_scan_cache[saves_dir] = scan
        return
    
    for filename in os.listdir(saves_dir):
        fn_lower = filename.lower()
        
        if not fn_lower.endswith(('.sav', '.srm')):
            continue
            
        if "pokemon" not in fn_lower:
            continue
        
        save_path = os.path.join(saves_dir, filename)
        
        scan[save_path] = identify_save(save_path)
    
    _save_scan_cache[saves_dir] = scan
    print(f"[SaveDetect] Filtered Pokemon scan complete: {len(scan)} files in {saves_dir}")


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
# audio-queue depth used by the emulator's audio thread. These can be
# overridden per-user via the mGBA → Audio section in Settings.

def _get_audio_defaults():
    """
    Get audio defaults based on platform and CFW.
    Returns tuple: (buffer_size, queue_depth)
    """
    if not IS_HANDHELD:
        return 1024, 4  # Desktop defaults
    
    # CFW-specific audio profiles (tuned per platform)
    # These are starting points - adjust after real-world testing
    cfw_audio_profiles = {
        'amberelec': (512, 4),   # Needs testing
        'arkos': (512, 4),       # Needs testing
        'rocknix': (256, 4),     # Verified working on X55
        'muos': (512, 4),        # Needs testing
        'knulli': (512, 4),      # Needs testing
        'unknown': (256, 4),     # Conservative default for unrecognized CFW
    }
    
    buffer, queue = cfw_audio_profiles.get(CFW_NAME, (256, 4))
    print(f"[Audio] CFW={CFW_NAME}, buffer={buffer}, queue={queue}")
    return buffer, queue

# Calculate recommended defaults based on detected platform/CFW
_AUDIO_BUFFER_RECOMMENDED, _AUDIO_QUEUE_RECOMMENDED = _get_audio_defaults()

# Exposed constants for settings UI and initial config
AUDIO_BUFFER_DEFAULT = 1024                    # Generic desktop default
AUDIO_BUFFER_DEFAULT_ARM = _AUDIO_BUFFER_RECOMMENDED  # Use CFW-specific for ARM
AUDIO_QUEUE_DEPTH_DEFAULT = _AUDIO_QUEUE_RECOMMENDED # Use CFW-specific queue depth

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
    print("-" * 50)
    print("Platform Detection:")
    print(f"IS_HANDHELD:  {IS_HANDHELD}")
    if IS_HANDHELD:
        print(f"CFW_NAME:     {CFW_NAME}")
        print(f"VIDEO_DRIVER: {VIDEO_DRIVER}")
        print(f"Audio Buffer: {AUDIO_BUFFER_DEFAULT_ARM} samples")
        print(f"Audio Queue:  {AUDIO_QUEUE_DEPTH_DEFAULT} chunks")
    else:
        print(f"Platform:     Desktop/PC")
        print(f"Audio Buffer: {AUDIO_BUFFER_DEFAULT} samples")
    print("=" * 50)


if __name__ == "__main__":
    print_paths()