"""
Pokemon Database Manager
Handles loading and managing Pokemon data and sprites
"""

import os
import json
import pygame
import config

# Try to import PIL for GIF animation support
try:
    from PIL import Image, ImageSequence
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class PokemonDatabase:
    """Manages Pokemon data and sprites"""
    
    def __init__(self):
        self.pokemon_db = {}
        self.PIL_AVAILABLE = PIL_AVAILABLE
        
    def load(self):
        """Load Pokemon database from JSON"""
        if not os.path.exists(config.POKEMON_DB_PATH):
            raise FileNotFoundError(f"pokemon_db.json not found at {config.POKEMON_DB_PATH}")
        
        with open(config.POKEMON_DB_PATH, 'r', encoding='utf-8') as fh:
            self.pokemon_db = json.load(fh)
        
        # Preload sprites
        self._preload_sprites()
        
        return self.pokemon_db
    
    def _preload_sprites(self):
        """Preload all Pokemon sprites"""
        for pkey, p in self.pokemon_db.items():
            pid = int(p.get('id', int(pkey)))
            pid_str = f"{pid:03d}"
            
            # Load Gen3 static sprites
            self._load_gen3_sprites(p, pid_str)
            
            # Load Showdown animated GIFs
            self._load_showdown_sprites(p, pid_str)
            
            # Ensure description exists
            p['description'] = (
                p.get('description') or 
                p.get('desc') or 
                p.get('flavor_text') or 
                "No description available."
            )
    
    def _load_gen3_sprites(self, pokemon_data, pid_str):
        """Load Gen3 static sprites"""
        gen3_path = os.path.join(config.DATA_DIR, "sprites", "gen3", "normal", f"{pid_str}.png")
        gen3_shiny_path = os.path.join(config.DATA_DIR, "sprites", "gen3", "shiny", f"{pid_str}.png")
        
        pokemon_data['gen3_normal_path'] = gen3_path if os.path.exists(gen3_path) else None
        pokemon_data['gen3_shiny_path'] = gen3_shiny_path if os.path.exists(gen3_shiny_path) else None
        
        if pokemon_data['gen3_normal_path']:
            try:
                pokemon_data['image'] = pygame.image.load(pokemon_data['gen3_normal_path']).convert_alpha()
            except Exception:
                pokemon_data['image'] = None
        else:
            pokemon_data['image'] = None
    
    def _load_showdown_sprites(self, pokemon_data, pid_str):
        """Load Showdown animated GIF sprites"""
        sd_normal = os.path.join(config.DATA_DIR, "sprites", "showdown", "normal", f"{pid_str}.gif")
        sd_shiny = os.path.join(config.DATA_DIR, "sprites", "showdown", "shiny", f"{pid_str}.gif")
        
        chosen = None
        if os.path.exists(sd_normal):
            chosen = sd_normal
            pokemon_data['_showdown_is_shiny'] = False
        elif os.path.exists(sd_shiny):
            chosen = sd_shiny
            pokemon_data['_showdown_is_shiny'] = True
        else:
            chosen = None
            pokemon_data['_showdown_is_shiny'] = False
        
        # Initialize animation data
        pokemon_data['_showdown_frames'] = None
        pokemon_data['_showdown_frame_durations'] = None
        pokemon_data['_showdown_frame_idx'] = 0
        pokemon_data['_showdown_frame_timer'] = 0
        
        if chosen:
            self._load_gif_frames(pokemon_data, chosen)
    
    def _load_gif_frames(self, pokemon_data, gif_path):
        """Load frames from a GIF file"""
        if self.PIL_AVAILABLE:
            try:
                pil_img = Image.open(gif_path)
                frames = []
                durations = []
                for frame in ImageSequence.Iterator(pil_img):
                    frame = frame.convert('RGBA')
                    size = frame.size
                    data = frame.tobytes()
                    surf = pygame.image.frombuffer(data, size, 'RGBA').convert_alpha()
                    frames.append(surf)
                    dur = frame.info.get('duration', config.SHOWDOWN_FRAME_MS_DEFAULT)
                    durations.append(int(dur) if isinstance(dur, int) else config.SHOWDOWN_FRAME_MS_DEFAULT)
                if frames:
                    pokemon_data['_showdown_frames'] = frames
                    pokemon_data['_showdown_frame_durations'] = durations
                pil_img.close()
            except Exception:
                # Fallback to single frame
                self._load_single_frame(pokemon_data, gif_path)
        else:
            # Without PIL, just load first frame
            self._load_single_frame(pokemon_data, gif_path)
    
    def _load_single_frame(self, pokemon_data, gif_path):
        """Load GIF as a single static frame"""
        try:
            surf = pygame.image.load(gif_path).convert_alpha()
            pokemon_data['_showdown_frames'] = [surf]
            pokemon_data['_showdown_frame_durations'] = [config.SHOWDOWN_FRAME_MS_DEFAULT]
        except Exception:
            pokemon_data['_showdown_frames'] = None
            pokemon_data['_showdown_frame_durations'] = None
    
    def get_pokemon(self, pokemon_id):
        """Get Pokemon data by ID"""
        return self.pokemon_db.get(str(pokemon_id))
    
    def get_all_pokemon(self):
        """Get all Pokemon data"""
        return self.pokemon_db
    
    def search_pokemon(self, query):
        """
        Search Pokemon by name
        
        Args:
            query: Search string
            
        Returns:
            List of matching Pokemon
        """
        if not query:
            return list(self.pokemon_db.values())
        
        query_lower = query.lower()
        results = []
        
        for pokemon in self.pokemon_db.values():
            name = pokemon.get('name', '').lower()
            if query_lower in name:
                results.append(pokemon)
        
        return results