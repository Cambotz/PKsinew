#!/usr/bin/env python3

"""
GIF Sprite Handler for Pokemon Showdown Sprites
Handles loading and animating GIF sprites in Pygame
"""

import os

import pygame
from PIL import Image, ImageSequence


class GIFSprite:
    """Handles animated GIF sprites"""

    def __init__(self, gif_path, target_size=None):
        """
        Load a GIF sprite

        Args:
            gif_path: Path to GIF file
            target_size: (width, height) to scale to, or None to keep original
        """
        self.gif_path = gif_path
        self.target_size = target_size
        self.frames = []
        self.durations = []
        self.current_frame = 0
        self.time_accumulator = 0
        self.loaded = False

        if os.path.exists(gif_path):
            self._load_gif()

    def _load_gif(self):
        """Load GIF frames into pygame surfaces"""
        try:
            pil_img = Image.open(self.gif_path)

            for frame in ImageSequence.Iterator(pil_img):
                # Convert frame to RGBA
                frame = frame.convert("RGBA")

                # Scale if needed
                if self.target_size:
                    frame = frame.resize(self.target_size, Image.NEAREST)

                # Convert to pygame surface
                data = frame.tobytes()
                surf = pygame.image.fromstring(
                    data, frame.size, frame.mode
                ).convert_alpha()

                self.frames.append(surf)

                # Get frame duration (in milliseconds)
                duration = frame.info.get("duration", 100)
                self.durations.append(duration)

            self.loaded = len(self.frames) > 0

        except Exception as e:
            print(f"Error loading GIF {self.gif_path}: {e}")
            self.loaded = False

    def update(self, dt):
        """
        Update animation

        Args:
            dt: Delta time in milliseconds
        """
        if not self.loaded or len(self.frames) <= 1:
            return

        self.time_accumulator += dt

        # Get duration of current frame
        current_duration = self.durations[self.current_frame] if self.durations else 100

        if self.time_accumulator >= current_duration:
            self.time_accumulator = 0
            self.current_frame = (self.current_frame + 1) % len(self.frames)

    def get_current_frame(self):
        """Get current frame surface"""
        if not self.loaded or not self.frames:
            return None
        return self.frames[self.current_frame]

    def draw(self, surf, pos):
        """
        Draw current frame at position

        Args:
            surf: Surface to draw on
            pos: (x, y) position or rect
        """
        frame = self.get_current_frame()
        if frame:
            if isinstance(pos, pygame.Rect):
                frame_rect = frame.get_rect(center=pos.center)
                surf.blit(frame, frame_rect.topleft)
            else:
                surf.blit(frame, pos)

    def reset(self):
        """Reset animation to first frame"""
        self.current_frame = 0
        self.time_accumulator = 0


class SpriteCache:
    """Cache for loaded sprites to avoid reloading"""

    def __init__(self):
        self.cache = {}  # sprite_key -> GIFSprite or pygame.Surface

    def get_gif_sprite(self, path, size=None):
        """
        Get a cached GIF sprite or load it

        Args:
            path: Path to GIF file
            size: (width, height) tuple or None

        Returns:
            GIFSprite or None
        """
        cache_key = f"{path}_{size}"

        if cache_key not in self.cache:
            if os.path.exists(path):
                self.cache[cache_key] = GIFSprite(path, size)
            else:
                self.cache[cache_key] = None

        return self.cache[cache_key]

    def get_png_sprite(self, path, size=None):
        """
        Get a cached PNG sprite or load it

        Args:
            path: Path to PNG file
            size: (width, height) tuple or None

        Returns:
            pygame.Surface or None
        """
        cache_key = f"{path}_{size}"

        if cache_key not in self.cache:
            if os.path.exists(path):
                try:
                    sprite = pygame.image.load(path).convert_alpha()
                    if size:
                        sprite = pygame.transform.smoothscale(sprite, size)
                    self.cache[cache_key] = sprite
                except Exception:
                    self.cache[cache_key] = None
            else:
                self.cache[cache_key] = None

        return self.cache[cache_key]

    def clear(self):
        """Clear the cache"""
        self.cache.clear()


# Global sprite cache instance
_sprite_cache = SpriteCache()


def get_sprite_cache():
    """Get the global sprite cache"""
    return _sprite_cache


def get_pokemon_sprite_with_fallback(species_id, game_name=None, shiny=False, prefer_gif=True, size=None):
    """
    Get Pokemon sprite using sprite pack system with automatic fallback.
    
    Args:
        species_id: National dex number
        game_name: Game name or None for global pack
        shiny: Whether to load shiny sprite
        prefer_gif: If True, prefer GIF over PNG for animation
        size: (width, height) tuple or None
    
    Returns:
        GIFSprite if GIF loaded, pygame.Surface if PNG loaded, or None if not found
    """
    try:
        from sprite_paths import get_sprite_path_for_game_any_format
        
        sprite_path, is_gif = get_sprite_path_for_game_any_format(
            species_id,
            game_name,
            shiny,
            prefer_gif=prefer_gif,
            fallback_to_global=True
        )
        
        if not sprite_path:
            return None
        
        cache = get_sprite_cache()
        
        if is_gif:
            return cache.get_gif_sprite(sprite_path, size)
        else:
            return cache.get_png_sprite(sprite_path, size)
            
    except Exception as e:
        print(f"[GIF Handler] Failed to load sprite for {species_id}: {e}")
        return None


def get_egg_sprite_with_fallback(game_name=None, size=None):
    """
    Get egg sprite using sprite pack system with automatic fallback.
    
    Args:
        game_name: Game name or None for global pack
        size: (width, height) tuple or None
    
    Returns:
        pygame.Surface or None
    """
    try:
        from sprite_paths import get_egg_sprite_path_for_game
        
        egg_path = get_egg_sprite_path_for_game(game_name)
        
        if not egg_path:
            return None
        
        cache = get_sprite_cache()
        return cache.get_png_sprite(egg_path, size)
        
    except Exception as e:
        print(f"[GIF Handler] Failed to load egg sprite: {e}")
        return None


# Global sprite cache instance
_sprite_cache = SpriteCache()


def get_sprite_cache():
    """Get the global sprite cache"""
    return _sprite_cache




# ============================================================
# SHINY OVERLAY
# ============================================================

class ShinyOverlay:
    """
    Plays shiny.gif once over a sprite, then stops.
    Lives in data/sprites/items/shiny.gif.

    Usage:
        overlay = ShinyOverlay()
        overlay.trigger(rect)       # call when a shiny is selected
        overlay.update(dt)          # call every frame
        overlay.draw(surf)          # call after drawing the sprite
    """

    def __init__(self):
        self._frames = []
        self._durations = []
        self._loaded = False
        self._active = False
        self._index = 0
        self._timer = 0.0
        self._rect = None
        self._sound = None
        self._load()
        self._load_sound()

    def _load(self):
        try:
            import os
            from config import SHINY_EFFECT_PATH
            path = SHINY_EFFECT_PATH
            if not os.path.exists(path):
                return
            from PIL import Image, ImageSequence
            import pygame
            pil_img = Image.open(path)
            for frame in ImageSequence.Iterator(pil_img):
                frame = frame.convert("RGBA")
                data = frame.tobytes()
                surf = pygame.image.fromstring(data, frame.size, frame.mode).convert_alpha()
                self._frames.append(surf)
                self._durations.append(frame.info.get("duration", 80))
            pil_img.close()
            self._loaded = len(self._frames) > 0
        except Exception as e:
            print(f"[ShinyOverlay] Failed to load shiny.gif: {e}")

    def _load_sound(self):
        try:
            import os
            import pygame
            from config import SHINY_SOUND_PATH
            if os.path.exists(SHINY_SOUND_PATH):
                self._sound = pygame.mixer.Sound(SHINY_SOUND_PATH)
        except Exception as e:
            print(f"[ShinyOverlay] Failed to load shiny.mp3: {e}")

    def trigger(self, rect):
        """Start playing the overlay over the given pygame.Rect."""
        if not self._loaded:
            return
        self._rect = rect
        self._index = 0
        self._timer = 0.0
        self._active = True
        # Play sound effect after 500ms delay
        self._sound_delay_timer = 500.0
        self._sound_pending = True

    def update(self, dt):
        """Advance animation. dt in milliseconds."""
        # Count down sound delay
        if getattr(self, '_sound_pending', False):
            self._sound_delay_timer -= dt
            if self._sound_delay_timer <= 0:
                self._sound_pending = False
                if self._sound:
                    try:
                        import pygame
                        self._sound.play()
                    except Exception:
                        pass

        if not self._active or not self._loaded:
            return
        self._timer += dt
        while self._timer >= self._durations[self._index]:
            self._timer -= self._durations[self._index]
            self._index += 1
            if self._index >= len(self._frames):
                # Played once - stop
                self._active = False
                self._index = 0
                self._timer = 0.0
                return

    def draw(self, surf):
        """Draw current overlay frame centred on the trigger rect."""
        if not self._active or not self._loaded or self._rect is None:
            return
        frame = self._frames[self._index]
        # Scale to rect size
        import pygame
        scaled = pygame.transform.scale(frame, (self._rect.width, self._rect.height))
        surf.blit(scaled, self._rect.topleft)

    @property
    def active(self):
        return self._active
# ============================================================
# USAGE EXAMPLES
# ============================================================
# Example 1: Simple GIF sprite usage
#
#   from gif_sprite_handler import GIFSprite
#   pikachu_gif = GIFSprite("data/sprites/showdown/normal/025.gif", target_size=(96, 96))
#   pikachu_gif.update(dt)
#   pikachu_gif.draw(screen, (100, 100))
#
# Example 2: Using the sprite cache
#
#   from gif_sprite_handler import get_sprite_cache
#   cache = get_sprite_cache()
#   gif_sprite = cache.get_gif_sprite("data/sprites/showdown/normal/025.gif", size=(96, 96))
#   png_sprite = cache.get_png_sprite("data/sprites/gen3/normal/025.png", size=(32, 32))