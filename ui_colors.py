"""
Sinew Color and Font Definitions
All color constants and font settings used throughout the UI
"""

import pygame

# Background colors
COLOR_BG = (0, 20, 40)
COLOR_HEADER = (10, 40, 80)

# Button colors
COLOR_BUTTON = (20, 60, 100)
COLOR_BUTTON_HOVER = (50, 120, 200)

# Text colors
COLOR_TEXT = (180, 220, 255)
COLOR_HOVER_TEXT = (255, 255, 255)

# Accent / border colors
COLOR_BORDER = (100, 200, 255)
COLOR_HIGHLIGHT = (0, 255, 255)   # cyan used to highlight selected cards

# Status / misc
COLOR_SUCCESS = (100, 255, 200)
COLOR_ERROR = (255, 80, 80)

# Health bar colors (use depending on percent)
HP_COLOR_GOOD = (0, 200, 0)    # green
HP_COLOR_WARN = (220, 180, 0)  # yellow/orange
HP_COLOR_BAD  = (200, 0, 0)    # red

# Font settings (can be changed by themes)
FONT_PATH = "fonts/Pokemon_GB.ttf"

# Font cache to avoid recreating fonts constantly
_font_cache = {}

def get_font(size):
    """
    Get a pygame font with the current theme's font path.
    Caches fonts by (path, size) to avoid recreation.
    
    Args:
        size: Font size in pixels
        
    Returns:
        pygame.font.Font object
    """
    cache_key = (FONT_PATH, size)
    
    if cache_key not in _font_cache:
        try:
            _font_cache[cache_key] = pygame.font.Font(FONT_PATH, size)
        except:
            # Fallback to system font
            _font_cache[cache_key] = pygame.font.SysFont(None, size)
    
    return _font_cache[cache_key]

def clear_font_cache():
    """Clear the font cache (call when theme changes font)"""
    global _font_cache
    _font_cache = {}