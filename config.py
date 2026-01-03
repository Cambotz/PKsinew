"""
Sinew Configuration
All paths, constants, and configuration settings
"""

import os

# ===== Display Settings =====
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320  # 3.5" screen
SCREEN_WIDTH = WINDOW_WIDTH  # Alias for compatibility
SCREEN_HEIGHT = WINDOW_HEIGHT
FPS = 60

# ===== Directory Paths =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SINEW_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "Sinew")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Emulator paths
MGBA_CORE_PATH = os.path.join(BASE_DIR, "cores", "mgba_libretro.dll")
SYSTEM_DIR = os.path.join(BASE_DIR, "system")

# ROM and save directories - unified for both parser and emulator
ROMS_DIR = os.path.join(BASE_DIR, "roms")
SAVES_DIR = os.path.join(BASE_DIR, "saves")

# Colors
COLOR_BG = (24, 24, 32)
COLOR_ACCENT = (80, 120, 200)

# Create directories if they don't exist
for dir_path in [ROMS_DIR, SAVES_DIR, SYSTEM_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Data paths
DATA_DIR = os.path.join(SINEW_DIR, "data")
POKEMON_DB_PATH = os.path.join(DATA_DIR, "pokemon_db.json")
SPRITES_PATH = os.path.join(DATA_DIR, "sprites")

# Sprite directories
GEN3_NORMAL_DIR = os.path.join(SPRITES_PATH, "gen3", "normal")
GEN3_SHINY_DIR = os.path.join(SPRITES_PATH, "gen3", "shiny")
SHOWDOWN_NORMAL_DIR = os.path.join(SPRITES_PATH, "showdown", "normal")
SHOWDOWN_SHINY_DIR = os.path.join(SPRITES_PATH, "showdown", "shiny")
GEN3_BOX_DIR = os.path.join(SPRITES_PATH, "gen3box")
GEN3_BOX_ANIM_DIR = os.path.join(SPRITES_PATH, "gen3box")

# Font path
FONT_PATH = os.path.join(SCRIPT_DIR, "fonts", "Pokemon_GB.ttf")

# ===== Save Editor Paths =====
# SAVES_PATH is unified with SAVES_DIR for consistency
SAVES_PATH = SAVES_DIR

# External mGBA fallback (if integrated emulator not available)
MGBA_PATH = r"G:\Games\gba\mGBA\mGBA.exe"

# ROM and Save paths for each game
ROM_PATHS = {
    "FireRed": os.path.join(ROMS_DIR, "FireRed.gba"),
    "LeafGreen": os.path.join(ROMS_DIR, "LeafGreen.gba"),
    "Ruby": os.path.join(ROMS_DIR, "Ruby.gba"),
    "Sapphire": os.path.join(ROMS_DIR, "Sapphire.gba"),
    "Emerald": os.path.join(ROMS_DIR, "Emerald.gba"),
}

# Save paths derive from SAVES_DIR
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

# ===== Animation Settings =====
SHOWDOWN_FRAME_MS_DEFAULT = 100

# ===== UI Layout Constants =====
HEADER_HEIGHT_RATIO = 0.1
CARD_SIZE_RATIO = 0.25
CARDS_PER_ROW = 3


# ===== Helper Functions =====
def get_save_path(game_name):
    """Get save file path for a game by name."""
    return SAVE_PATHS.get(game_name, os.path.join(SAVES_DIR, f"{game_name}.sav"))

def get_rom_path(game_name):
    """Get ROM file path for a game by name."""
    return ROM_PATHS.get(game_name, os.path.join(ROMS_DIR, f"{game_name}.gba"))