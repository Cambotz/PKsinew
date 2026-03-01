#!/usr/bin/env python3

"""
game_detection.py — ROM/save scanning and game availability logic for Sinew.

Extracted from main.py. Provides:
  - GAME_DEFINITIONS: known GBA game metadata (keywords, title GIFs)
  - find_rom_for_game / find_save_for_game: file-system lookups
  - detect_games_with_dirs: full game list with ROM + save paths
  - get_game_availability: three-state availability enum
"""

import os

from config import (
    ROMS_DIR,
    SAVES_DIR,
    SPRITES_DIR,
    identify_rom,
)

# =============================================================================
# Game definitions
# =============================================================================
# Keywords are checked against lowercase filename (without extension).
# More specific keywords should come first to avoid false matches.

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

# =============================================================================
# ROM scan cache
# =============================================================================
# Module-level ROM scan cache: populated once per directory on first call.
# Maps roms_dir -> {rom_path -> (game_name, priority) | None}
# Priority: 1 = Official ROM (hash match), 2 = ROM hack (header match)
# Avoids re-hashing every .gba file for each of the five game lookups.
_rom_scan_cache = {}


def _build_rom_scan_cache(roms_dir):
    """
    Scan roms_dir once, identify every .gba and .zip file, cache results.
    No-op if already scanned. Supports multiple directories independently.

    Uses keyword pre-filtering for BOTH .gba and .zip files to avoid
    hashing non-Pokemon ROMs (massive performance optimization).
    """
    if roms_dir in _rom_scan_cache:
        return

    scan = {}

    if not os.path.exists(roms_dir):
        _rom_scan_cache[roms_dir] = scan
        return

    # Build master keyword list from all games for pre-filtering
    all_keywords = set()
    for game_def in GAME_DEFINITIONS.values():
        all_keywords.update(kw.lower() for kw in game_def.get("keywords", []))

    # Also add common Pokemon-related keywords for better matching
    all_keywords.update(
        ["pokemon", "pkmn", "emerald", "ruby", "sapphire", "firered", "leafgreen"]
    )

    for filename in os.listdir(roms_dir):
        if not filename.lower().endswith((".gba", ".zip")):
            continue
        rom_path = os.path.join(roms_dir, filename)

        # Pass keywords to identify_rom for ALL files (.gba and .zip)
        # This skips hashing files that don't match Pokemon keywords (massive speedup)
        scan[rom_path] = identify_rom(rom_path, keywords_hint=all_keywords)

    _rom_scan_cache[roms_dir] = scan
    print(f"[GameScreen] ROM scan complete: {len(scan)} files in {roms_dir}")


# =============================================================================
# ROM / save finders
# =============================================================================

def find_rom_for_game(game_name, roms_dir, saves_dir):
    """
    Search for a ROM file matching the given game name.
    Prioritizes official ROMs (hash matches) over ROM hacks (header matches).

    Detection order:
      1. ROM scan cache (hash + header) - built once per directory
      2. Filename keyword fallback - for zips or unrecognised ROMs

    Args:
        game_name: Name of the game (e.g., "FireRed")
        roms_dir: Directory to search for ROMs
        saves_dir: Directory to search for saves

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
    best_match = None  # Track best ROM found (lowest priority number = best)
    best_priority = 999  # Start with worst priority

    for rom_path, detected in _rom_scan_cache[roms_dir].items():
        filename = os.path.basename(rom_path)
        name_lower = filename.lower()
        base_name = os.path.splitext(filename)[0]

        # Cache hit - ROM identified by hash/header
        if detected and detected[0] == game_name:
            _, priority = detected

            # If this is better priority than what we have, use it
            if priority < best_priority:
                # Try save detection first (content-based)
                sav_path = find_save_for_game(game_name, saves_dir)
                # Fallback to filename matching
                if not sav_path:
                    candidate = os.path.join(saves_dir, base_name + ".sav")
                    if os.path.exists(candidate):
                        sav_path = candidate

                best_match = (rom_path, sav_path)
                best_priority = priority

                # If we found an official ROM (priority 1), we're done
                if priority == 1:
                    print(f"[GameScreen] ROM match {game_name}: {filename} (official)")
                    return rom_path, sav_path

        # Keyword fallback for zips and unrecognised .gba files
        if keyword_fallback is None and detected is None:
            if any(ex.lower() in name_lower for ex in exclude):
                continue
            for keyword in keywords:
                if keyword.lower() in name_lower:
                    # Also try save detection for keyword matches
                    sav_path = find_save_for_game(game_name, saves_dir)
                    if not sav_path:
                        candidate = os.path.join(saves_dir, base_name + ".sav")
                        if os.path.exists(candidate):
                            sav_path = candidate
                    keyword_fallback = (rom_path, sav_path)
                    break

    # Return best match found (official ROM preferred, then ROM hack, then keyword)
    if best_match:
        rom_type = "ROM hack" if best_priority == 2 else "unknown priority"
        print(
            f"[GameScreen] ROM match {game_name}: {os.path.basename(best_match[0])} ({rom_type})"
        )
        return best_match

    if keyword_fallback:
        print(
            f"[GameScreen] Keyword match {game_name}: {os.path.basename(keyword_fallback[0])}"
        )
        return keyword_fallback

    return None, None


def find_save_for_game(game_name, saves_dir):
    """
    Search the saves directory for a .sav file matching the game.

    Detection order:
      1. Save scan cache (game code detection) - built once for the whole saves_dir
      2. Filename keyword fallback - for manually named saves

    Args:
        game_name: Name of the game (e.g., "FireRed")
        saves_dir: Directory to search for .sav files

    Returns:
        str or None: Path to the first matching .sav file, or None
    """
    from config import _build_save_scan_cache, _save_scan_cache

    if game_name not in GAME_DEFINITIONS:
        return None

    game_def = GAME_DEFINITIONS[game_name]
    keywords = game_def.get("keywords", [])
    exclude = game_def.get("exclude", [])

    if not os.path.exists(saves_dir):
        return None

    # Ensure the directory has been scanned (no-op if already done)
    _build_save_scan_cache(saves_dir)
    matches = []
    keyword_matches = []

    for save_path, detected in _save_scan_cache[saves_dir].items():
        name_lower = os.path.basename(save_path).lower()

        # Collect all "Cache Hit" matches
        if detected == game_name:
            matches.append(save_path)
            continue

        # Collect all "Keyword" matches (only if no cache hits found yet)
        if not matches and detected is None:
            if not any(ex.lower() in name_lower for ex in exclude):
                for keyword in keywords:
                    if keyword.lower() in name_lower:
                        keyword_matches.append(save_path)
                        break

    # Prioritization Logic
    final_list = matches if matches else keyword_matches

    if not final_list:
        return None

    # Prefer .sav > .srm > .sa1 > .sa2 (most common emulator formats first)
    for ext in (".sav", ".srm", ".sa1", ".sa2"):
        for path in final_list:
            if path.lower().endswith(ext):
                return path

    return final_list[0]


def detect_games_with_dirs(roms_dir, saves_dir):
    """
    Detect all available games by scanning the specified ROMs and saves directories.

    A game is included if it has a ROM, a save, or both.
    Games with neither are omitted entirely (filtered later by availability).

    Args:
        roms_dir: Directory to scan for ROM files
        saves_dir: Directory to scan for save files

    Returns:
        dict: Game configurations with detected ROM/save paths
    """
    games = {
        "Sinew": {"title_gif": None, "rom": None, "sav": None, "is_sinew": True},
    }

    for game_name, game_def in GAME_DEFINITIONS.items():
        rom_path, sav_path = find_rom_for_game(game_name, roms_dir, saves_dir)

        # If no ROM was found, still look for a matching save file independently
        if rom_path is None:
            sav_path = find_save_for_game(game_name, saves_dir)
        games[game_name] = {
            "title_gif": game_def["title_gif"],
            "rom": rom_path,
            "sav": sav_path,
        }

    return games


# =============================================================================
# Game availability
# =============================================================================
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


# Detect games on module load (uses default dirs from config)
GAMES = detect_games_with_dirs(ROMS_DIR, SAVES_DIR)
