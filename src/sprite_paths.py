#!/usr/bin/env python3

"""
sprite_paths.py — Dynamic sprite path resolution using pack manager.

This module provides helper functions that replace the static paths in config.py
with dynamic paths based on the active sprite pack.
"""

import os
from typing import Optional

from sprite_pack_manager import get_sprite_pack_manager


def get_sprite_dirs_for_game(game_name: Optional[str] = None) -> tuple:
    """
    Get sprite directories for a specific game (or global default).
    
    Args:
        game_name: Game name (e.g., "Ruby", "Emerald") or None for global
    
    Returns:
        (normal_dir, shiny_dir) tuple
    """
    manager = get_sprite_pack_manager()
    
    if game_name:
        pack = manager.get_pack_for_game(game_name)
    else:
        # Use global pack
        global_pack_id = manager.preferences.get("global_pack", "gen3_emerald")
        pack = manager.get_pack(global_pack_id)
    
    if pack:
        return pack.normal_dir, pack.shiny_dir
    
    # Fallback to gen3 default (shouldn't happen)
    from config import GEN3_NORMAL_DIR, GEN3_SHINY_DIR
    return GEN3_NORMAL_DIR, GEN3_SHINY_DIR


def get_sprite_path_for_game_any_format(
    species: int,
    game_name: Optional[str] = None,
    shiny: bool = False,
    prefer_gif: bool = True,
    fallback_to_global: bool = True
) -> tuple[Optional[str], bool]:
    """
    Get best sprite path (GIF or PNG) for a Pokemon with proper priority.
    
    Priority:
    1. Game pack GIF (if prefer_gif=True and exists)
    2. Game pack PNG (if exists)
    3. Global pack GIF (if fallback_to_global and prefer_gif=True and exists)
    4. Global pack PNG (if fallback_to_global and exists)
    
    Args:
        species: National dex number
        game_name: Game name or None for global pack
        shiny: Whether to get shiny sprite
        prefer_gif: If True, prioritize GIF over PNG
        fallback_to_global: If True, fall back to global pack if not found in game pack
    
    Returns:
        (path, is_gif) tuple where path is the sprite path and is_gif indicates if it's a GIF
    """
    manager = get_sprite_pack_manager()
    
    # Get game pack
    if game_name:
        game_pack = manager.get_pack_for_game(game_name)
    else:
        global_pack_id = manager.preferences.get("global_pack", "gen3_emerald")
        game_pack = manager.get_pack(global_pack_id)
    
    if game_pack:
        sprite_dir = game_pack.shiny_dir if shiny else game_pack.normal_dir
        
        # Check game pack - GIF first if preferred
        if prefer_gif:
            gif_path = os.path.join(sprite_dir, f"{species:03d}.gif")
            if os.path.exists(gif_path):
                return (gif_path, True)
        
        # Check game pack - PNG
        ext = game_pack.metadata.get("file_ext", "png")
        png_path = os.path.join(sprite_dir, f"{species:03d}.{ext}")
        if os.path.exists(png_path):
            return (png_path, False)
    
    # Fallback to global pack if enabled and not already on global
    if fallback_to_global and game_name:
        global_pack_id = manager.preferences.get("global_pack", "gen3_emerald")
        global_pack = manager.get_pack(global_pack_id)
        
        if global_pack:
            global_sprite_dir = global_pack.shiny_dir if shiny else global_pack.normal_dir
            
            # Check global pack - GIF first if preferred
            if prefer_gif:
                global_gif_path = os.path.join(global_sprite_dir, f"{species:03d}.gif")
                if os.path.exists(global_gif_path):
                    return (global_gif_path, True)
            
            # Check global pack - PNG
            global_ext = global_pack.metadata.get("file_ext", "png")
            global_png_path = os.path.join(global_sprite_dir, f"{species:03d}.{global_ext}")
            if os.path.exists(global_png_path):
                return (global_png_path, False)
    
    return (None, False)


def get_sprite_path_for_game(
    species: int, 
    game_name: Optional[str] = None, 
    shiny: bool = False,
    fallback_to_global: bool = False
) -> Optional[str]:
    """
    Get sprite path for a Pokemon for a specific game.
    
    Args:
        species: National dex number
        game_name: Game name or None for global pack
        shiny: Whether to get shiny sprite
        fallback_to_global: If True and sprite not found in game pack, try global pack
    
    Returns:
        Path to sprite file or None if not found
    """
    manager = get_sprite_pack_manager()
    
    if game_name:
        pack = manager.get_pack_for_game(game_name)
    else:
        global_pack_id = manager.preferences.get("global_pack", "gen3_emerald")
        pack = manager.get_pack(global_pack_id)
    
    if not pack:
        return None
    
    sprite_dir = pack.shiny_dir if shiny else pack.normal_dir
    ext = pack.metadata.get("file_ext", "png")
    
    sprite_path = os.path.join(sprite_dir, f"{species:03d}.{ext}")
    
    # If sprite exists in the requested pack, return it
    if os.path.exists(sprite_path):
        return sprite_path
    
    # If fallback enabled and we're not already using global, try global pack
    if fallback_to_global and game_name:
        global_pack_id = manager.preferences.get("global_pack", "gen3_emerald")
        global_pack = manager.get_pack(global_pack_id)
        
        if global_pack:
            global_sprite_dir = global_pack.shiny_dir if shiny else global_pack.normal_dir
            global_ext = global_pack.metadata.get("file_ext", "png")
            global_sprite_path = os.path.join(global_sprite_dir, f"{species:03d}.{global_ext}")
            
            if os.path.exists(global_sprite_path):
                return global_sprite_path
    
    return None


def get_egg_sprite_path_for_game(game_name: Optional[str] = None) -> Optional[str]:
    """
    Get egg sprite path. Egg sprites are now in data/sprites/items, not in packs.
    
    Args:
        game_name: Game name (ignored - egg is in items folder)
    
    Returns:
        Path to egg sprite or None
    """
    from config import DATA_DIR
    
    # Egg sprite is now in items folder, not in sprite packs
    items_dir = os.path.join(DATA_DIR, "sprites", "items")
    egg_path = os.path.join(items_dir, "egg.png")
    
    return egg_path if os.path.exists(egg_path) else None