"""
GIF Sprite Handler for Pokemon Showdown Sprites
Handles loading and animating GIF sprites in Pygame
"""

import pygame
from PIL import Image, ImageSequence
import os


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
                surf = pygame.image.fromstring(data, frame.size, frame.mode).convert_alpha()
                
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
                except:
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


# ============================================================
# USAGE EXAMPLES
# ============================================================

"""
Example 1: Simple GIF sprite usage

    from gif_sprite_handler import GIFSprite
    
    # Load a GIF sprite
    pikachu_gif = GIFSprite("data/sprites/showdown/normal/025.gif", target_size=(96, 96))
    
    # In your game loop:
    pikachu_gif.update(dt)  # dt in milliseconds
    pikachu_gif.draw(screen, (100, 100))


Example 2: Using the sprite cache

    from gif_sprite_handler import get_sprite_cache
    
    cache = get_sprite_cache()
    
    # Get showdown sprite (GIF)
    gif_sprite = cache.get_gif_sprite("data/sprites/showdown/normal/025.gif", size=(96, 96))
    
    # Get gen3 sprite (PNG)
    png_sprite = cache.get_png_sprite("data/sprites/gen3/normal/025.png", size=(32, 32))
    
    # In game loop:
    if gif_sprite:
        gif_sprite.update(dt)
        gif_sprite.draw(screen, rect)
    
    if png_sprite:
        screen.blit(png_sprite, (x, y))


Example 3: Integrating with PC Box screen

    class PCBox:
        def __init__(self, ...):
            # ... existing code ...
            self.sprite_cache = get_sprite_cache()
            self.current_gif = None
        
        def draw(self, surf):
            # ... existing code ...
            
            # For main sprite display (showdown GIF)
            if self.selected_pokemon and not self.selected_pokemon.get('empty'):
                sprite_path = self.manager.get_showdown_sprite_path(self.selected_pokemon)
                if sprite_path:
                    # Get or load GIF sprite
                    gif_sprite = self.sprite_cache.get_gif_sprite(
                        sprite_path, 
                        size=(self.sprite_area.width - 4, self.sprite_area.height - 4)
                    )
                    
                    if gif_sprite and gif_sprite.loaded:
                        # Update animation
                        gif_sprite.update(dt)  # You'll need to pass dt
                        
                        # Draw animated sprite
                        gif_sprite.draw(surf, self.sprite_area)


Example 4: Grid sprites (PNG)

    # In draw_grid method
    for i, rect in enumerate(rects):
        poke = self.get_pokemon_at_grid_slot(i)
        
        if poke and not poke.get('empty') and not poke.get('egg'):
            sprite_path = self.manager.get_gen3_sprite_path(poke)
            if sprite_path:
                sprite = self.sprite_cache.get_png_sprite(
                    sprite_path,
                    size=(int(rect.width * 0.8), int(rect.height * 0.8))
                )
                
                if sprite:
                    sprite_rect = sprite.get_rect(center=rect.center)
                    surf.blit(sprite, sprite_rect)
"""