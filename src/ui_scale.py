#!/usr/bin/env python3

"""
UI Scale Module for Sinew
Provides resolution-independent scaling for fonts, margins, spacing, and layout.

All UI code was originally designed for a 480x320 virtual resolution.
This module computes a scale factor from the actual virtual resolution
so that fonts, margins, and spacing scale proportionally.

Usage:
    from ui_scale import ui, scaled_font

    # Scale a pixel value (margin, spacing, width, height, etc.)
    margin = ui.s(10)        # 10px at 480x320 → 15px at 640x480

    # Get a scaled font (base size is what you'd use at 480x320)
    font = scaled_font(16)   # 16px at 480x320 → 24px at 640x480

    # Scale explicitly by width or height axis
    w = ui.sx(100)           # scale by width ratio only
    h = ui.sy(50)            # scale by height ratio only

    # Access the raw scale factor
    factor = ui.scale        # e.g. 1.5 at 640x480

Initialisation:
    Called once from __main__.py after the virtual resolution is known:

        from ui_scale import init_ui_scale
        init_ui_scale(VIRTUAL_WIDTH, VIRTUAL_HEIGHT)
"""

import pygame
from config import FONT_PATH

# ── Reference resolution (what all hardcoded values were designed for) ──
REF_WIDTH = 480
REF_HEIGHT = 320


class _UIScale:
    """Holds the current scale state. Accessed via the module-level `ui` instance."""

    def __init__(self):
        # Default to 1.0 (no scaling) until init_ui_scale() is called
        self.virtual_width = REF_WIDTH
        self.virtual_height = REF_HEIGHT
        self.scale_x = 1.0
        self.scale_y = 1.0
        # Use the *smaller* axis ratio so nothing overflows
        self.scale = 1.0

    def configure(self, virtual_width, virtual_height):
        """
        Recalculate scale factors for a new virtual resolution.
        Safe to call more than once (e.g. if resolution changes at runtime).
        """
        self.virtual_width = virtual_width
        self.virtual_height = virtual_height
        self.scale_x = virtual_width / REF_WIDTH
        self.scale_y = virtual_height / REF_HEIGHT
        # Uniform scale uses the *smaller* ratio to prevent overflow
        self.scale = min(self.scale_x, self.scale_y)
        # Clear the font cache so fonts are regenerated at the new scale
        _font_cache.clear()
        print(
            f"[ui_scale] Configured: {virtual_width}x{virtual_height} "
            f"(scale={self.scale:.3f}, sx={self.scale_x:.3f}, sy={self.scale_y:.3f})"
        )

    # ── Scaling helpers ──────────────────────────────────────────────

    def s(self, px):
        """
        Scale a pixel value uniformly (uses min of x/y scale).
        Use for margins, padding, spacing, border radii, icon sizes —
        anything that should stay proportional in both axes.

        Preserves sign for negative values (e.g. offscreen positions).
        Returns an int with minimum absolute value of 1 (unless input is 0).
        """
        if px == 0:
            return 0
        scaled = int(round(px * self.scale))
        if scaled == 0:
            return 1 if px > 0 else -1
        return scaled

    def sx(self, px):
        """Scale by width ratio only. Use for widths tied to the x-axis."""
        if px == 0:
            return 0
        scaled = int(round(px * self.scale_x))
        if scaled == 0:
            return 1 if px > 0 else -1
        return scaled

    def sy(self, px):
        """Scale by height ratio only. Use for heights tied to the y-axis."""
        if px == 0:
            return 0
        scaled = int(round(px * self.scale_y))
        if scaled == 0:
            return 1 if px > 0 else -1
        return scaled

    def sf(self, base_size):
        """
        Scale a font size. Identical to s() but with a minimum of 6px
        so tiny fonts remain readable.
        """
        return max(6, int(round(base_size * self.scale)))


# ── Module-level singleton ───────────────────────────────────────────
ui = _UIScale()

# ── Font cache (keyed on scaled size) ────────────────────────────────
_font_cache = {}


def scaled_font(base_size):
    """
    Return a pygame.font.Font scaled from *base_size* (designed for 480×320)
    to the current virtual resolution.

    Fonts are cached by their final pixel size, so repeated calls are cheap.

    Args:
        base_size: Font size in pixels at the reference 480×320 resolution.

    Returns:
        pygame.font.Font
    """
    actual_size = ui.sf(base_size)
    cache_key = (FONT_PATH, actual_size)

    if cache_key not in _font_cache:
        try:
            _font_cache[cache_key] = pygame.font.Font(FONT_PATH, actual_size)
        except Exception as e:
            print(f"[ui_scale] Font load failed ({FONT_PATH}, {actual_size}): {e}")
            _font_cache[cache_key] = pygame.font.SysFont(None, actual_size)

    return _font_cache[cache_key]


def clear_font_cache():
    """Clear the scaled font cache (call when theme changes the font file)."""
    _font_cache.clear()


# ── Public init function ─────────────────────────────────────────────
def init_ui_scale(virtual_width, virtual_height):
    """
    Initialise (or reinitialise) the UI scale system.

    Call once from __main__.py after deciding on the virtual resolution:

        from ui_scale import init_ui_scale
        init_ui_scale(VIRTUAL_WIDTH, VIRTUAL_HEIGHT)

    Also safe to call again if the virtual resolution changes at runtime.
    """
    ui.configure(virtual_width, virtual_height)