"""
Sinew Configuration
All paths, constants, and configuration settings

IMPORTANT: All paths are anchored to the script location, not the working directory.
Use the resolve_path() function or pre-defined path constants to ensure paths work
regardless of where the script is executed from.
"""

import os

# ===== Base Directory Setup =====
# This is the KEY fix - anchor all paths to where config.py is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = SCRIPT_DIR  # These are the same - the project root

# ===== Path Resolution Helper =====
def resolve_path(*path_parts):
    """
    Resolve a path relative to the project root (BASE_DIR).
    
    This ensures paths work regardless of the current working directory.
    
    Args:
        *path_parts: Path components to join (e.g., "data", "sprites", "gen3")
        
    Returns:
        str: Absolute path anchored to the project root
        
    Examples:
        resolve_path("fonts", "Pokemon_GB.ttf")
        resolve_path("data/sprites/gen3/normal")  # Can use forward slashes too
    """
    # Handle single path with forward slashes
    if len(path_parts) == 1 and '/' in path_parts[0]:
        path_parts = path_parts[0].split('/')
    
    return os.path.join(BASE_DIR, *path_parts)


def resolve_data_path(*path_parts):
    """
    Resolve a path relative to the data directory.
    
    Args:
        *path_parts: Path components to join
        
    Returns:
        str: Absolute path anchored to the data directory
    """
    return os.path.join(DATA_DIR, *path_parts)


# ===== Display Settings =====
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320  # 3.5" screen
SCREEN_WIDTH = WINDOW_WIDTH  # Alias for compatibility
SCREEN_HEIGHT = WINDOW_HEIGHT
FPS = 60

# ===== Directory Paths =====
# Sinew parent directory (for shared data if needed)
SINEW_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "Sinew")

# Core directories - all anchored to BASE_DIR
CORES_DIR = os.path.join(BASE_DIR, "cores")
SYSTEM_DIR = os.path.join(BASE_DIR, "system")
ROMS_DIR = os.path.join(BASE_DIR, "roms")
SAVES_DIR = os.path.join(BASE_DIR, "saves")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
THEMES_DIR = os.path.join(BASE_DIR, "themes")

# Data directory structure
DATA_DIR = os.path.join(BASE_DIR, "data")
SPRITES_DIR = os.path.join(DATA_DIR, "sprites")

# Sprite directories
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

# ===== Font Paths =====
FONT_PATH = os.path.join(FONTS_DIR, "Pokemon_GB.ttf")
FONT_SOLID_PATH = os.path.join(FONTS_DIR, "Pokemon Solid.ttf")

# ===== Emulator Paths =====
# Platform-specific core detection
import platform as _platform

def get_platform_info():
    """Get platform and architecture info for core selection."""
    system = _platform.system().lower()
    machine = _platform.machine().lower()
    
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
        arch_name = 'x64' if struct.calcsize('P') == 8 else 'x86'
    
    return os_name, arch_name, ext

def get_core_filename():
    """Get the platform-specific mGBA core filename."""
    os_name, arch_name, ext = get_platform_info()
    return f"mgba_libretro_{os_name}_{arch_name}{ext}"

MGBA_CORE_PATH = os.path.join(CORES_DIR, get_core_filename())


# ===== Save Editor Paths =====
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
    os.path.join(SCRIPT_DIR, 'parser'),
    os.path.join(os.path.dirname(SCRIPT_DIR), 'parser'),
    SCRIPT_DIR,
]

# ===== Settings File =====
SETTINGS_FILE = os.path.join(BASE_DIR, "sinew_settings.json")

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
for dir_path in [ROMS_DIR, SAVES_DIR, SYSTEM_DIR, CORES_DIR]:
    os.makedirs(dir_path, exist_ok=True)


# ===== Debug Info =====
def print_paths():
    """Print all configured paths for debugging."""
    print("=" * 50)
    print("PKsinew Path Configuration")
    print("=" * 50)
    print(f"BASE_DIR:     {BASE_DIR}")
    print(f"SCRIPT_DIR:   {SCRIPT_DIR}")
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