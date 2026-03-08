#!/usr/bin/env python3

"""
text_utils.py - Text rendering utilities for Sinew

Handles special rendering cases like Pokemon gender symbols that aren't
available in the Pokemon_GB.ttf font.
"""

import pygame


def render_pokemon_name(font, name, base_color):
    """
    Render a Pokemon name with proper gender symbol handling.
    
    Pokemon_GB.ttf doesn't have Unicode ♂/♀ symbols, so we substitute:
    - ♂ → blue M
    - ♀ → pink F
    
    Args:
        font: pygame.Font to use for rendering
        name: Pokemon name (may contain ♂ or ♀ symbols)
        base_color: Color tuple for normal text
        
    Returns:
        pygame.Surface with rendered text
    """
    if not name:
        return font.render("", True, base_color)
    
    # Gender symbol colors
    MALE_COLOR = (100, 149, 237)    # Cornflower blue
    FEMALE_COLOR = (255, 182, 193)  # Light pink
    
    # Check if name contains gender symbols
    has_male = "♂" in name
    has_female = "♀" in name
    
    if not (has_male or has_female):
        # No gender symbols, render normally
        return font.render(name, True, base_color)
    
    # Replace Unicode with ASCII for detection
    display_name = name.replace("♂", "M").replace("♀", "F")
    
    # Find where M or F appears
    if has_male:
        parts = display_name.split("M", 1)
        gender_char = "M"
        gender_color = MALE_COLOR
    else:  # has_female
        parts = display_name.split("F", 1)
        gender_char = "F"
        gender_color = FEMALE_COLOR
    
    if len(parts) != 2:
        # Couldn't split properly, render normally
        return font.render(display_name, True, base_color)
    
    # Render each part
    before = parts[0]
    after = parts[1]
    
    before_surf = font.render(before, True, base_color) if before else None
    gender_surf = font.render(gender_char, True, gender_color)
    after_surf = font.render(after, True, base_color) if after else None
    
    # Calculate total width
    total_width = gender_surf.get_width()
    if before_surf:
        total_width += before_surf.get_width()
    if after_surf:
        total_width += after_surf.get_width()
    
    # Create composite surface
    height = font.get_height()
    result = pygame.Surface((total_width, height), pygame.SRCALPHA)
    result.fill((0, 0, 0, 0))  # Transparent background
    
    # Blit parts together
    x = 0
    if before_surf:
        result.blit(before_surf, (x, 0))
        x += before_surf.get_width()
    
    result.blit(gender_surf, (x, 0))
    x += gender_surf.get_width()
    
    if after_surf:
        result.blit(after_surf, (x, 0))
    
    return result


def contains_gender_symbol(name):
    """
    Check if a Pokemon name contains a gender symbol.
    
    Args:
        name: Pokemon name string
        
    Returns:
        bool: True if name contains ♂ or ♀
    """
    if not name:
        return False
    return "♂" in name or "♀" in name
