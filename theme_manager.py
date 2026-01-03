"""
Sinew Theme Manager
Handles loading, applying, and saving theme preferences
"""

import os
import json

# Default theme values (Dark theme)
DEFAULT_THEME = {
    "COLOR_BG": [0, 20, 40],
    "COLOR_HEADER": [10, 40, 80],
    "COLOR_BUTTON": [20, 60, 100],
    "COLOR_BUTTON_HOVER": [50, 120, 200],
    "COLOR_TEXT": [180, 220, 255],
    "COLOR_HOVER_TEXT": [255, 255, 255],
    "COLOR_BORDER": [100, 200, 255],
    "COLOR_HIGHLIGHT": [0, 255, 255],
    "COLOR_SUCCESS": [100, 255, 200],
    "COLOR_ERROR": [255, 80, 80],
    "HP_COLOR_GOOD": [0, 200, 0],
    "HP_COLOR_WARN": [220, 180, 0],
    "HP_COLOR_BAD": [200, 0, 0],
    "FONT_PATH": "fonts/Pokemon_GB.ttf",
}

# Theme directory
THEMES_DIR = "themes"

# Current theme name
_current_theme_name = "Dark"


def get_available_themes():
    """
    Get list of available theme names from the themes directory.
    
    Returns:
        list: Theme names (without .json extension)
    """
    themes = ["Dark"]  # Default is always available
    
    if os.path.exists(THEMES_DIR):
        for filename in os.listdir(THEMES_DIR):
            if filename.endswith('.json') or filename.endswith('_theme.json'):
                # Extract theme name
                name = filename.replace('_theme.json', '').replace('.json', '')
                # Capitalize nicely
                name = name.replace('_', ' ').title()
                if name not in themes:
                    themes.append(name)
    
    return sorted(themes)


def load_theme(theme_name):
    """
    Load a theme from file.
    
    Args:
        theme_name: Name of the theme (e.g., "Candy", "Dark")
        
    Returns:
        dict: Theme color values, or None if not found
    """
    if theme_name.lower() == "dark":
        return DEFAULT_THEME.copy()
    
    # Try different filename patterns
    base_name = theme_name.lower().replace(' ', '_')
    possible_files = [
        os.path.join(THEMES_DIR, f"{base_name}_theme.json"),
        os.path.join(THEMES_DIR, f"{base_name}.json"),
        os.path.join(THEMES_DIR, f"{theme_name}_theme.json"),
        os.path.join(THEMES_DIR, f"{theme_name}.json"),
    ]
    
    for filepath in possible_files:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    theme_data = json.load(f)
                print(f"[ThemeManager] Loaded theme from: {filepath}")
                return theme_data
            except Exception as e:
                print(f"[ThemeManager] Error loading {filepath}: {e}")
    
    print(f"[ThemeManager] Theme not found: {theme_name}")
    return None


def apply_theme(theme_name):
    """
    Apply a theme by updating ui_colors module variables.
    
    Args:
        theme_name: Name of the theme to apply
        
    Returns:
        bool: True if successful
    """
    global _current_theme_name
    
    theme_data = load_theme(theme_name)
    if theme_data is None:
        return False
    
    try:
        import ui_colors
        
        # Check if font is changing
        old_font = getattr(ui_colors, 'FONT_PATH', None)
        new_font = theme_data.get('FONT_PATH', None)
        font_changed = new_font and old_font != new_font
        
        # Update each setting in ui_colors module
        for key, value in theme_data.items():
            if hasattr(ui_colors, key):
                # Convert list to tuple for pygame compatibility (colors)
                if isinstance(value, list):
                    value = tuple(value)
                setattr(ui_colors, key, value)
                print(f"[ThemeManager] Set {key} = {value}")
        
        # Clear font cache if font changed
        if font_changed and hasattr(ui_colors, 'clear_font_cache'):
            ui_colors.clear_font_cache()
            print(f"[ThemeManager] Cleared font cache for new font: {new_font}")
        
        _current_theme_name = theme_name
        print(f"[ThemeManager] Applied theme: {theme_name}")
        return True
        
    except Exception as e:
        print(f"[ThemeManager] Error applying theme: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_current_theme():
    """Get the name of the currently applied theme."""
    return _current_theme_name


def get_theme_preview(theme_name):
    """
    Get preview colors for a theme without applying it.
    
    Args:
        theme_name: Name of the theme
        
    Returns:
        dict: Theme colors or None
    """
    return load_theme(theme_name)


def save_theme_preference(theme_name, settings_path="sinew_settings.json"):
    """
    Save the theme preference to settings file.
    
    Args:
        theme_name: Name of the theme to save
        settings_path: Path to settings JSON file
    """
    settings = {}
    
    # Load existing settings if present
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
        except:
            pass
    
    settings['theme'] = theme_name
    
    try:
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)
        print(f"[ThemeManager] Saved theme preference: {theme_name}")
    except Exception as e:
        print(f"[ThemeManager] Error saving settings: {e}")


def load_theme_preference(settings_path="sinew_settings.json"):
    """
    Load and apply the saved theme preference.
    
    Args:
        settings_path: Path to settings JSON file
        
    Returns:
        str: Name of the loaded theme
    """
    theme_name = "Dark"  # Default
    
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                theme_name = settings.get('theme', 'Dark')
        except:
            pass
    
    apply_theme(theme_name)
    return theme_name