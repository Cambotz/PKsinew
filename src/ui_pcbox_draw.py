#!/usr/bin/env python3

"""
ui_pcbox_draw.py — Rendering mixin for PCBox.

All drawing methods extracted from pc_box.py so that the main
pc_box.py file can focus on data, input, and business logic.

The mixin assumes the usual PCBox instance attributes are present
(self.width, self.height, self.font, self.grid_rect, etc.).
It calls data/input helpers that remain in PCBox proper
(e.g. self._get_running_game_name(), self._get_pause_combo_name(),
self.get_grid_rects(), self.get_pokemon_at_grid_slot(), etc.).
"""

import math
import os

import pygame

import ui_colors
from config import (
    FONT_PATH,
    SPRITES_DIR,
    get_egg_sprite_path,
    get_sprite_path,
)
from sprite_paths import get_sprite_dirs_for_game
from ui_components import scale_surface_preserve_aspect
from ui_scale import ui, scaled_font
from text_utils import render_pokemon_name, contains_gender_symbol

# Optional dependencies — matched exactly to pc_box.py guard pattern
try:
    from achievements import get_achievement_manager, get_achievement_notification

    _ACHIEVEMENTS_AVAILABLE = True
except ImportError:
    get_achievement_manager = None
    get_achievement_notification = None
    _ACHIEVEMENTS_AVAILABLE = False

try:
    from achievements_data import (
        ALTERING_CAVE_POKEMON,
    )

    _ALTERING_CAVE_DATA_AVAILABLE = True
except ImportError:
    ALTERING_CAVE_POKEMON = []
    _ALTERING_CAVE_DATA_AVAILABLE = False


class PCBoxDrawMixin:
    """Mixin providing all rendering methods for PCBox."""

    # ------------------------------------------------------------------ #
    #  Shiny detection helper                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_is_shiny(pokemon):
        """
        Compute whether a Pokemon is shiny from its personality and OT ID.
        Gen 3 formula: TID ^ SID ^ PID_HIGH ^ PID_LOW < 8.
        Falls back to stored flags only if PID/OTID are missing.
        """
        if not pokemon or pokemon.get("empty") or pokemon.get("egg"):
            return False
        personality = pokemon.get("personality", 0)
        ot_id = pokemon.get("ot_id", 0)
        if personality and ot_id:
            tid     = ot_id & 0xFFFF
            sid     = (ot_id >> 16) & 0xFFFF
            pid_low = personality & 0xFFFF
            pid_high = (personality >> 16) & 0xFFFF
            return (tid ^ sid ^ pid_low ^ pid_high) < 8
        return pokemon.get("is_shiny", False) or pokemon.get("shiny", False)

    # ------------------------------------------------------------------ #
    #  Sprite scaling helpers                                              #
    # ------------------------------------------------------------------ #

    def _scale_sprite_crisp(self, surf_img, target_w, target_h):
        """
        Scale sprite using nearest-neighbor for crisp pixel art, with smart scale limiting
        (Same logic as Pokedex)
        """
        iw, ih = surf_img.get_size()
        if iw == 0 or ih == 0:
            return pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        
        # Calculate scale ratio to fit within target
        ratio = min(target_w / iw, target_h / ih)
        
        # Apply tiered max scale based on original sprite size
        original_size = max(iw, ih)
        if original_size < 40:
            max_scale = 1.5  # Very small sprites
        elif original_size < 60:
            max_scale = 2.0  # Small sprites
        else:
            max_scale = 2.75  # Normal/large sprites
        
        ratio = min(ratio, max_scale)
        
        new_w = max(1, int(iw * ratio))
        new_h = max(1, int(ih * ratio))
        # Use scale (nearest-neighbor) instead of smoothscale for pixel art
        return pygame.transform.scale(surf_img, (new_w, new_h))
    
    def _get_sprite_dirs(self):
        """Get sprite directories for current game (or global if no game)"""
        current_game = None
        if hasattr(self, 'get_current_game_callback') and self.get_current_game_callback:
            current_game = self.get_current_game_callback()
        
        return get_sprite_dirs_for_game(current_game)
    
    def _get_best_sprite_path(self, species_id, shiny=False, prefer_gif=True):
        """
        Get best available sprite path with proper priority.
        Results are cached to avoid redundant filesystem checks.
        
        Returns: (path, is_gif) or (None, False)
        """
        # Get current game name FIRST (for cache key)
        game_name = None
        if hasattr(self, 'get_current_game_callback') and self.get_current_game_callback:
            game_name = self.get_current_game_callback()
        
        # Create cache if it doesn't exist
        if not hasattr(self, '_sprite_path_cache'):
            self._sprite_path_cache = {}
        
        # Check cache first - INCLUDE GAME NAME in key to prevent cross-contamination
        cache_key = (game_name, species_id, shiny, prefer_gif)
        if cache_key in self._sprite_path_cache:
            return self._sprite_path_cache[cache_key]
        
        # Get game pack sprite path (PNG)
        game_png_path = None
        try:
            from sprite_paths import get_sprite_path_for_game
            game_png_path = get_sprite_path_for_game(
                species_id,
                game_name,
                shiny,
                fallback_to_global=False  # Don't fallback yet, we'll do it manually
            )
        except Exception:
            pass
        
        # Get directories for GIF checking
        game_normal_dir, game_shiny_dir = self._get_sprite_dirs()
        game_sprite_dir = game_shiny_dir if shiny else game_normal_dir
        game_gif_path = os.path.join(game_sprite_dir, f"{species_id:03d}.gif")
        
        # Check game pack (prefer GIF if requested)
        if prefer_gif and os.path.exists(game_gif_path) and os.path.isfile(game_gif_path):
            result = (game_gif_path, True)  # Game pack GIF
            self._sprite_path_cache[cache_key] = result
            return result
        
        if game_png_path and os.path.exists(game_png_path):
            result = (game_png_path, False)  # Game pack PNG
            self._sprite_path_cache[cache_key] = result
            return result
        
        # Fallback to global pack only if we're not already on global
        if game_name:
            # Get global pack paths
            global_png_path = None
            try:
                from sprite_paths import get_sprite_path_for_game
                global_png_path = get_sprite_path_for_game(
                    species_id,
                    None,  # Global pack
                    shiny,
                    fallback_to_global=False
                )
            except Exception:
                pass
            
            global_normal_dir, global_shiny_dir = get_sprite_dirs_for_game(None)
            global_sprite_dir = global_shiny_dir if shiny else global_normal_dir
            global_gif_path = os.path.join(global_sprite_dir, f"{species_id:03d}.gif")
            
            # Check global pack (prefer GIF if requested)
            if prefer_gif and os.path.exists(global_gif_path) and os.path.isfile(global_gif_path):
                result = (global_gif_path, True)  # Global pack GIF
                self._sprite_path_cache[cache_key] = result
                return result
            
            if global_png_path and os.path.exists(global_png_path):
                result = (global_png_path, False)  # Global pack PNG
                self._sprite_path_cache[cache_key] = result
                return result
        
        result = (None, False)  # Nothing found
        self._sprite_path_cache[cache_key] = result
        return result
    
    def clear_sprite_cache(self):
        """Clear sprite path cache (call when switching games/packs)"""
        if hasattr(self, '_sprite_path_cache'):
            self._sprite_path_cache.clear()
        if hasattr(self, '_pokemon_sprite_info_cache'):
            self._pokemon_sprite_info_cache.clear()
        if hasattr(self, '_static_gif_cache'):
            self._static_gif_cache.clear()
        if hasattr(self, '_grid_gif_cache'):
            self._grid_gif_cache.clear()
        if hasattr(self, '_party_gif_cache'):
            self._party_gif_cache.clear()

    def _load_gif_frames(self, gif_path, target_w, target_h):
        """
        Load GIF frames with nearest-neighbor scaling
        Returns: (frames_list, durations_list) or (None, None)
        """
        if not os.path.exists(gif_path):
            print(f"[PCBox] GIF not found: {gif_path}")
            return None, None
        
        try:
            from PIL import Image, ImageSequence
            pil_img = Image.open(gif_path)
            frames = []
            durations = []
            
            for frame in ImageSequence.Iterator(pil_img):
                frame_rgba = frame.convert('RGBA')
                data = frame_rgba.tobytes()
                surf = pygame.image.fromstring(data, frame_rgba.size, frame_rgba.mode).convert_alpha()
                
                # Scale with nearest-neighbor
                scaled = self._scale_sprite_crisp(surf, target_w, target_h)
                frames.append(scaled)
                durations.append(frame.info.get('duration', 100))
            
            pil_img.close()
            
            # Debug output
            if frames:
                print(f"[PCBox] Loaded GIF: {os.path.basename(gif_path)} - {len(frames)} frames")
                if len(frames) == 1:
                    print(f"[PCBox] WARNING: GIF only has 1 frame (static image)")
            
            return frames, durations
        except Exception as e:
            print(f"[PCBox] Error loading GIF {gif_path}: {e}")
            return None, None

    # ------------------------------------------------------------------ #
    #  Resume banner                                                       #
    # ------------------------------------------------------------------ #

    def _draw_resume_banner(self, surf):
        """
        Draw a dropdown banner from the top showing game is paused.
        Shows "[gamename]" running • Hold [combo] to resume
        with pulsing animation and scrolling text if too long.
        """
        # Get game name from callback
        game_name = self._get_running_game_name()
        if not game_name:
            return

        combo_name = self._get_pause_combo_name()

        # Build the full text
        full_text = f'"{game_name}" running  •  Hold {combo_name} to resume'

        # Banner dimensions - shorter and centered box
        banner_height = ui.s(21)
        banner_width = int(self.width * 0.85)
        banner_x = (self.width - banner_width) // 2
        banner_y = ui.s(4)
        padding = ui.s(12)
        border_radius = ui.s(6)

        # Update pulse time
        self._resume_banner_pulse_time += 0.08
        pulse = (math.sin(self._resume_banner_pulse_time) + 1) / 2  # 0 to 1

        # Pulsing background color (dark amber to lighter amber)
        bg_r = int(40 + 25 * pulse)
        bg_g = int(35 + 20 * pulse)
        bg_b = int(15 + 10 * pulse)

        # Draw banner background with rounded corners
        banner_rect = pygame.Rect(banner_x, banner_y, banner_width, banner_height)
        pygame.draw.rect(
            surf, (bg_r, bg_g, bg_b), banner_rect, border_radius=border_radius
        )

        # Pulsing border (gold tones)
        border_r = int(180 + 75 * pulse)
        border_g = int(140 + 60 * pulse)
        border_b = int(30 + 30 * pulse)
        pygame.draw.rect(
            surf,
            (border_r, border_g, border_b),
            banner_rect,
            2,
            border_radius=border_radius,
        )

        # Render text using the same font as the rest of the app
        banner_font = scaled_font(10)

        # Pulsing text color
        text_r = int(200 + 55 * pulse)
        text_g = int(180 + 55 * pulse)
        text_b = int(100 + 50 * pulse)
        text_color = (text_r, text_g, text_b)

        text_surf = banner_font.render(full_text, True, text_color)
        text_width = text_surf.get_width()

        # Available width for text (inside the box)
        available_width = banner_width - (padding * 2)

        if text_width <= available_width:
            # Text fits - center it
            text_x = banner_x + (banner_width - text_width) // 2
            text_y = banner_y + (banner_height - text_surf.get_height()) // 2
            surf.blit(text_surf, (text_x, text_y))
        else:
            # Text too long - scroll it
            clip_rect = pygame.Rect(
                banner_x + padding, banner_y, available_width, banner_height
            )

            # Update scroll offset
            scroll_width = text_width + ui.s(60)  # Add gap before repeat
            self._resume_banner_scroll_offset += self._resume_banner_scroll_speed
            if self._resume_banner_scroll_offset >= scroll_width:
                self._resume_banner_scroll_offset = 0

            # Calculate text position (scrolling left)
            text_x = banner_x + padding - self._resume_banner_scroll_offset
            text_y = banner_y + (banner_height - text_surf.get_height()) // 2

            # Draw text with clipping
            old_clip = surf.get_clip()
            surf.set_clip(clip_rect)

            surf.blit(text_surf, (text_x, text_y))
            # Draw second copy for seamless scrolling
            if text_x + text_width < banner_x + padding + available_width:
                surf.blit(text_surf, (text_x + scroll_width, text_y))

            surf.set_clip(old_clip)

    # ------------------------------------------------------------------ #
    #  ROM-hack overlay                                                    #
    # ------------------------------------------------------------------ #

    def _draw_rom_hack_overlay(self, surf, rect, size="small"):
        """
        Draw ROM hack indicator overlay on a slot.

        Args:
            surf: Surface to draw on
            rect: Rectangle of the slot
            size: 'small' for grid/party slots, 'large' for main sprite area
        """
        try:
            # Red semi-transparent overlay
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill((180, 0, 0, 100))
            surf.blit(overlay, rect.topleft)

            if size == "small":
                # "HACK" text for small slots
                tiny_font = scaled_font(6)
                hack_text = tiny_font.render("HACK", True, (255, 100, 100))
                hack_rect = hack_text.get_rect(
                    centerx=rect.centerx, bottom=rect.bottom - ui.s(2)
                )
                surf.blit(hack_text, hack_rect)
            else:
                # "ROM HACK" banner for large display
                banner_font = scaled_font(10)
                hack_text = banner_font.render("ROM HACK", True, (255, 80, 80))
                hack_rect = hack_text.get_rect(centerx=rect.centerx, top=rect.top + ui.s(5))

                # Draw background for text
                bg_rect = hack_rect.inflate(ui.s(10), ui.s(4))
                pygame.draw.rect(surf, (60, 0, 0), bg_rect)
                pygame.draw.rect(surf, (255, 80, 80), bg_rect, 1)
                surf.blit(hack_text, hack_rect)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Grid                                                                #
    # ------------------------------------------------------------------ #

    def draw_grid(self, surf):
        """Draw the PC box grid with Pokemon data."""

        rects = self.get_grid_rects()
        grid_selected_idx = self.grid_nav.get_selected()

        for i, rect in enumerate(rects):
            poke = self.get_pokemon_at_grid_slot(i)

            # Determine if this is the selected Pokemon
            is_selected = (
                poke
                and self.selected_pokemon
                and poke.get("species") == self.selected_pokemon.get("species")
                and poke.get("personality") == self.selected_pokemon.get("personality")
            )

            # Check if this slot is controller-selected
            is_controller_selected = (
                i == grid_selected_idx and not self.party_panel_open
            )

            # Base color for slot (use theme button color with transparency)
            if poke and not poke.get("empty"):
                # Occupied slot - slightly brighter
                r, g, b = (
                    ui_colors.COLOR_BUTTON_HOVER[:3]
                    if len(ui_colors.COLOR_BUTTON_HOVER) >= 3
                    else (80, 80, 100)
                )
                base_color = (r, g, b, 180)
            else:
                # Empty slot - dimmer
                r, g, b = (
                    ui_colors.COLOR_BUTTON[:3]
                    if len(ui_colors.COLOR_BUTTON) >= 3
                    else (60, 60, 60)
                )
                base_color = (r, g, b, 180)

            # Draw slot background with transparency
            slot_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(slot_surf, base_color, (0, 0, rect.width, rect.height))
            surf.blit(slot_surf, rect.topleft)

            # Draw border
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, rect, 1)

            # Highlight controller-selected slot
            if is_controller_selected:
                # Draw highlight cursor border
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, rect, 3)

            # Highlight selected Pokemon (when A is pressed) - keep yellow for distinction
            if is_selected and not is_controller_selected:
                # Draw bright highlight border (yellow to distinguish from cursor)
                pygame.draw.rect(surf, (255, 255, 100), rect, 3)

            # Draw pulsing border for Altering Cave Zubats (mystical purple pulse)
            if poke and not poke.get("empty") and self._is_altering_cave_zubat(poke):
                pulse_color = self._get_altering_cave_pulse_color()
                pygame.draw.rect(surf, pulse_color, rect, 2)

            # Draw Pokemon sprite (gen3 PNG or animated GIF) if available
            if poke and not poke.get("empty") and not poke.get("egg"):

                # Get Pokemon ID and shiny status
                poke_id = poke.get("species", 0)  # National dex number
                is_shiny = self._compute_is_shiny(poke)
                
                # Calculate target size with margin
                cell_size = min(rect.width, rect.height)
                sprite_size = int(cell_size * 0.8)
                
                sprite_drawn = False
                
                # Cache sprite info per Pokemon personality (unique ID)
                personality = poke.get("personality", 0)
                pokemon_cache_key = f"poke_{poke_id}_{personality}_{is_shiny}"
                
                # Get sprite info from cache or compute it
                if not hasattr(self, '_pokemon_sprite_info_cache'):
                    self._pokemon_sprite_info_cache = {}
                
                if pokemon_cache_key not in self._pokemon_sprite_info_cache:
                    # First time seeing this Pokemon - get its sprite
                    prefer_gif = True  # Always check for GIF first
                    sprite_path, is_gif = self._get_best_sprite_path(poke_id, is_shiny, prefer_gif=prefer_gif)
                    self._pokemon_sprite_info_cache[pokemon_cache_key] = {
                        'path': sprite_path,
                        'is_gif': is_gif
                    }
                
                sprite_info = self._pokemon_sprite_info_cache[pokemon_cache_key]
                sprite_path = sprite_info['path']
                is_gif = sprite_info['is_gif']
                
                # Try animated GIF if this slot is hovered/selected and we have a GIF
                if is_controller_selected and is_gif and sprite_path:
                        # Cache key for this grid slot
                        cache_key = f"grid_{i}"
                        if not hasattr(self, '_grid_gif_cache'):
                            self._grid_gif_cache = {}
                        
                        # Load GIF if not cached or path changed
                        if cache_key not in self._grid_gif_cache or self._grid_gif_cache[cache_key]['path'] != sprite_path:
                            frames, durations = self._load_gif_frames(sprite_path, sprite_size, sprite_size)
                            if frames:
                                self._grid_gif_cache[cache_key] = {
                                    'path': sprite_path,
                                    'frames': frames,
                                    'durations': durations,
                                    'index': 0,
                                    'timer': 0
                                }
                        
                        # Animate and draw
                        if cache_key in self._grid_gif_cache:
                            gif_data = self._grid_gif_cache[cache_key]
                            if gif_data['frames']:
                                # Update animation timer
                                gif_data['timer'] += 16
                                current_duration = gif_data['durations'][gif_data['index']]
                                
                                if gif_data['timer'] >= current_duration:
                                    gif_data['timer'] = 0
                                    gif_data['index'] = (gif_data['index'] + 1) % len(gif_data['frames'])
                                
                                # Draw current frame (centered)
                                frame = gif_data['frames'][gif_data['index']]
                                sprite_rect = frame.get_rect(center=rect.center)
                                surf.blit(frame, sprite_rect)
                                sprite_drawn = True
                
                # Static sprite (not selected/hovered)
                if not sprite_drawn and sprite_path:
                    if is_gif:
                        # Show first frame of GIF (static)
                        cache_key = f"static_{poke_id:03d}_{is_shiny}"
                        if not hasattr(self, '_static_gif_cache'):
                            self._static_gif_cache = {}
                        
                        # Load and cache first frame if not cached
                        if cache_key not in self._static_gif_cache:
                            try:
                                frames, _ = self._load_gif_frames(sprite_path, sprite_size, sprite_size)
                                if frames and len(frames) > 0:
                                    self._static_gif_cache[cache_key] = frames[0]
                            except Exception:
                                self._static_gif_cache[cache_key] = None
                        
                        # Draw cached static frame
                        if cache_key in self._static_gif_cache and self._static_gif_cache[cache_key]:
                            first_frame = self._static_gif_cache[cache_key]
                            sprite_rect = first_frame.get_rect(center=rect.center)
                            surf.blit(first_frame, sprite_rect)
                            sprite_drawn = True
                    else:
                        # PNG sprite
                        try:
                            sprite = pygame.image.load(sprite_path).convert_alpha()
                            sprite = scale_surface_preserve_aspect(sprite, sprite_size, sprite_size)
                            sprite_rect = sprite.get_rect(center=rect.center)
                            surf.blit(sprite, sprite_rect)
                            sprite_drawn = True
                        except Exception:
                            pass  # If sprite fails to load, just show colored cell

                # Draw ROM HACK overlay for Pokemon from ROM hacks
                if sprite_drawn and poke.get("rom_hack"):
                    self._draw_rom_hack_overlay(surf, rect, size="small")

            # For eggs, draw egg sprite
            elif poke and poke.get("egg"):
                # Try to load egg sprite
                egg_path = get_egg_sprite_path("gen3")
                if os.path.exists(egg_path):
                    try:
                        egg_sprite = pygame.image.load(egg_path).convert_alpha()
                        # Scale egg sprite to fit in cell with aspect ratio preserved
                        cell_size = min(rect.width, rect.height)
                        sprite_size = int(cell_size * 0.8)
                        egg_sprite = scale_surface_preserve_aspect(egg_sprite, sprite_size, sprite_size)
                        sprite_rect = egg_sprite.get_rect(center=rect.center)
                        surf.blit(egg_sprite, sprite_rect)
                    except Exception:
                        # Fallback to text if sprite fails
                        try:
                            tiny_font = scaled_font(8)
                            text = "EGG"
                            text_surf = tiny_font.render(
                                text, True, ui_colors.COLOR_TEXT
                            )
                            text_rect = text_surf.get_rect(center=rect.center)
                            surf.blit(text_surf, text_rect)
                        except Exception:
                            pass
                else:
                    # No egg sprite, show text
                    try:
                        tiny_font = scaled_font(8)
                        text = "EGG"
                        text_surf = tiny_font.render(text, True, ui_colors.COLOR_TEXT)
                        text_rect = text_surf.get_rect(center=rect.center)
                        surf.blit(text_surf, text_rect)
                    except Exception:
                        pass

        # Draw scrollbar for Sinew mode
        if self.sinew_mode:
            self._draw_sinew_scrollbar(surf)

    # ------------------------------------------------------------------ #
    #  Sinew scrollbar                                                     #
    # ------------------------------------------------------------------ #

    def _draw_sinew_scrollbar(self, surf):
        """Draw scrollbar for Sinew storage's 120-slot boxes."""
        # Scrollbar sits in the gap between the left panel and the grid
        scrollbar_width = ui.s(8)
        gap_left = self.sprite_area.right
        gap_right = self.grid_rect.left
        scrollbar_x = gap_left + ui.s(5)
        scrollbar_y = self.grid_rect.top + 2
        scrollbar_height = self.grid_rect.height - 4

        # Background track
        track_rect = pygame.Rect(
            scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height
        )
        pygame.draw.rect(surf, (40, 40, 50, 200), track_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, track_rect, 1)

        # Calculate thumb size and position
        # Total rows = 20, visible rows = 5
        max_scroll = self.sinew_total_rows - self.sinew_visible_rows  # 15
        if max_scroll > 0:
            thumb_height = max(
                30, scrollbar_height * self.sinew_visible_rows // self.sinew_total_rows
            )
            thumb_travel = scrollbar_height - thumb_height
            thumb_y = scrollbar_y + int(
                thumb_travel * self.sinew_scroll_offset / max_scroll
            )

            # Draw thumb
            thumb_rect = pygame.Rect(
                scrollbar_x + 1, thumb_y, scrollbar_width - 2, thumb_height
            )
            pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, thumb_rect)
            pygame.draw.rect(surf, ui_colors.COLOR_HOVER_TEXT, thumb_rect, 1)

        # Draw row indicator text below grid
        try:
            tiny_font = scaled_font(8)
            start_row = self.sinew_scroll_offset + 1
            end_row = min(
                self.sinew_scroll_offset + self.sinew_visible_rows,
                self.sinew_total_rows,
            )
            indicator_text = f"Rows {start_row}-{end_row}/{self.sinew_total_rows}"
            text_surf = tiny_font.render(indicator_text, True, ui_colors.COLOR_TEXT)
            gap_cx = gap_left + ui.s(5) + scrollbar_width // 2
            text_rect = text_surf.get_rect(
                centerx=gap_cx + ui.s(30), top=self.grid_rect.bottom + ui.s(3) + ui.s(10)
            )
            surf.blit(text_surf, text_rect)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Main draw                                                           #
    # ------------------------------------------------------------------ #

    def draw(self, surf, dt=16):
        """
        Draw the PC box screen.

        Args:
            surf: Surface to draw on
            dt: Delta time in milliseconds (for GIF animation)
        """

        # Init shiny overlay on first draw
        if not hasattr(self, '_shiny_overlay'):
            from gif_sprite_handler import ShinyOverlay
            self._shiny_overlay = ShinyOverlay()
            self._shiny_overlay_last_pid = None

        # Trigger shiny overlay when a new shiny is selected
        current_pid = (
            self.selected_pokemon.get('personality')
            if self.selected_pokemon and not self.selected_pokemon.get('empty')
            else None
        )
        if current_pid != self._shiny_overlay_last_pid:
            self._shiny_overlay_last_pid = current_pid
            if (self.selected_pokemon
                    and not self.selected_pokemon.get('empty')
                    and not self.selected_pokemon.get('egg')
                    and self._compute_is_shiny(self.selected_pokemon)):
                self._shiny_overlay.trigger(self.sprite_area)

        self._shiny_overlay.update(dt)

        # Background overlay (darken using theme BG color)
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        r, g, b = (
            ui_colors.COLOR_BG[:3] if len(ui_colors.COLOR_BG) >= 3 else (50, 50, 50)
        )
        overlay.fill((r, g, b, 180))
        surf.blit(overlay, (0, 0))

        pygame.draw.rect(
            surf, ui_colors.COLOR_BORDER, (0, 0, self.width, self.height), 2
        )

        # Draw "Game Running" warning banner if this game is being emulated
        warning_banner_height = 0
        if self.is_current_game_running():
            warning_banner_height = ui.s(25)
            # Draw warning banner at top
            banner_rect = pygame.Rect(0, 0, self.width, warning_banner_height)
            # Dark error background using theme
            er, eg, eb = (
                ui_colors.COLOR_ERROR[:3]
                if len(ui_colors.COLOR_ERROR) >= 3
                else (255, 80, 80)
            )
            pygame.draw.rect(surf, (er // 3, eg // 3, eb // 3), banner_rect)
            pygame.draw.rect(surf, ui_colors.COLOR_ERROR, banner_rect, 1)

            try:
                warning_font = scaled_font(12)
                warning_text = (
                    f"{self.get_current_game()} is running - transfers disabled"
                )
                text_surf = warning_font.render(
                    warning_text, True, ui_colors.COLOR_ERROR
                )
                text_rect = text_surf.get_rect(
                    center=(self.width // 2, warning_banner_height // 2)
                )
                surf.blit(text_surf, text_rect)
            except Exception:
                pass

        # Sprite area - semi-transparent background to match grid
        sprite_bg = pygame.Surface(
            (self.sprite_area.width, self.sprite_area.height), pygame.SRCALPHA
        )

        # Determine background color based on selection (using theme colors)
        if self.selected_pokemon and not self.selected_pokemon.get("empty"):
            # Pokemon/egg selected - brighter
            r, g, b = (
                ui_colors.COLOR_BUTTON_HOVER[:3]
                if len(ui_colors.COLOR_BUTTON_HOVER) >= 3
                else (80, 80, 100)
            )
            bg_color = (r, g, b, 180)
        else:
            # Nothing selected - dimmer
            r, g, b = (
                ui_colors.COLOR_BUTTON[:3]
                if len(ui_colors.COLOR_BUTTON) >= 3
                else (60, 60, 60)
            )
            bg_color = (r, g, b, 180)

        pygame.draw.rect(
            sprite_bg, bg_color, (0, 0, self.sprite_area.width, self.sprite_area.height)
        )
        surf.blit(sprite_bg, self.sprite_area.topleft)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.sprite_area, 2)

        # Show selected Pokemon sprite if available
        if self.selected_pokemon and not self.selected_pokemon.get("empty"):
            # Check if it's an egg
            if self.selected_pokemon.get("egg"):
                # Show egg sprite (try PNG, then GIF)
                normal_dir, _ = self._get_sprite_dirs()
                egg_png_path = get_egg_sprite_path("gen3")
                egg_gif_path = os.path.join(normal_dir, "egg.gif")

                # Try gen3 PNG first
                if os.path.exists(egg_png_path):
                    try:
                        egg_sprite = pygame.image.load(egg_png_path).convert_alpha()
                        sprite_width = int(self.sprite_area.width * 0.9)
                        sprite_height = int(self.sprite_area.height * 0.9)
                        egg_sprite = scale_surface_preserve_aspect(egg_sprite, sprite_width,
                            sprite_height)
                        rect = egg_sprite.get_rect(center=self.sprite_area.center)
                        surf.blit(egg_sprite, rect.topleft)
                    except Exception:
                        pass
                # Fallback to showdown GIF
                elif os.path.exists(egg_gif_path):
                    sprite_width = int(self.sprite_area.width * 0.9)
                    sprite_height = int(self.sprite_area.height * 0.9)

                    # Load or get cached GIF frames
                    if self._preview_gif_path != egg_gif_path:
                        self._preview_gif_frames, self._preview_gif_durations = self._load_gif_frames(
                            egg_gif_path, sprite_width, sprite_height
                        )
                        self._preview_gif_path = egg_gif_path
                        self._preview_gif_index = 0
                        self._preview_gif_timer = 0
                    
                    # Animate
                    if self._preview_gif_frames:
                        self._preview_gif_timer += dt
                        current_duration = self._preview_gif_durations[self._preview_gif_index]
                        
                        if self._preview_gif_timer >= current_duration:
                            self._preview_gif_timer = 0
                            self._preview_gif_index = (self._preview_gif_index + 1) % len(self._preview_gif_frames)
                        
                        # Draw current frame centered
                        frame = self._preview_gif_frames[self._preview_gif_index]
                        rect = frame.get_rect(center=self.sprite_area.center)
                        surf.blit(frame, rect.topleft)
            else:
                # Regular Pokemon - try GIF first for animation, fallback to PNG
                # Use "species" key (the national dex number) not "species_id"
                poke_id = self.selected_pokemon.get("species", 0)
                
                # Skip if no valid Pokemon (species = 0 means empty/invalid)
                if poke_id == 0:
                    # No Pokemon selected or invalid species - don't try to load sprites
                    if self.current_sprite_image:
                        rect = self.current_sprite_image.get_rect(
                            center=self.sprite_area.center
                        )
                        surf.blit(self.current_sprite_image, rect.topleft)
                else:
                    # Valid Pokemon - load sprite
                    poke_id = self.selected_pokemon.get("species", 0)
                    is_shiny = self._compute_is_shiny(self.selected_pokemon)
                    
                    # Get best sprite (prioritize GIF for animation)
                    sprite_path, is_gif = self._get_best_sprite_path(poke_id, is_shiny, prefer_gif=True)
                    
                    sprite_drawn = False
                    
                    if is_gif and sprite_path:
                        # Animated GIF sprite
                        sprite_width = int(self.sprite_area.width * 0.9)
                        sprite_height = int(self.sprite_area.height * 0.9)
                        
                        # Check if we need to load (path changed or not loaded yet)
                        need_load = (
                            not hasattr(self, '_preview_gif_path') or
                            self._preview_gif_path != sprite_path or
                            self._preview_gif_frames is None
                        )
                        
                        if need_load:
                            self._preview_gif_frames, self._preview_gif_durations = self._load_gif_frames(
                                sprite_path, sprite_width, sprite_height
                            )
                            self._preview_gif_path = sprite_path
                            self._preview_gif_index = 0
                            self._preview_gif_timer = 0
                        
                        # Animate
                        if self._preview_gif_frames and len(self._preview_gif_frames) > 0:
                            self._preview_gif_timer += dt
                            current_duration = self._preview_gif_durations[self._preview_gif_index]
                            
                            if self._preview_gif_timer >= current_duration:
                                self._preview_gif_timer = 0
                                self._preview_gif_index = (self._preview_gif_index + 1) % len(self._preview_gif_frames)
                            
                            # Draw current frame centered
                            frame = self._preview_gif_frames[self._preview_gif_index]
                            rect = frame.get_rect(center=self.sprite_area.center)
                            surf.blit(frame, rect.topleft)
                            sprite_drawn = True
                    
                    # Fallback to static PNG if GIF didn't work
                    if not sprite_drawn and not is_gif and sprite_path and os.path.exists(sprite_path):
                        try:
                            poke_sprite = pygame.image.load(sprite_path).convert_alpha()
                            sprite_width = int(self.sprite_area.width * 0.9)
                            sprite_height = int(self.sprite_area.height * 0.9)
                            poke_sprite = self._scale_sprite_crisp(poke_sprite, sprite_width, sprite_height)
                            rect = poke_sprite.get_rect(center=self.sprite_area.center)
                            surf.blit(poke_sprite, rect.topleft)
                            sprite_drawn = True
                        except Exception:
                            # Fallback to cached image if loading fails
                            if self.current_sprite_image:
                                rect = self.current_sprite_image.get_rect(
                                    center=self.sprite_area.center
                                )
                                surf.blit(self.current_sprite_image, rect.topleft)
                    
                    # Last resort: use cached image
                    if not sprite_drawn and self.current_sprite_image:
                        rect = self.current_sprite_image.get_rect(
                            center=self.sprite_area.center
                        )
                        surf.blit(self.current_sprite_image, rect.topleft)

                # Draw ROM HACK overlay for Pokemon from ROM hacks
                if self.selected_pokemon.get("rom_hack"):
                    self._draw_rom_hack_overlay(surf, self.sprite_area, size="large")

            # Draw shiny overlay (plays once when a shiny is selected)
            if hasattr(self, '_shiny_overlay'):
                self._shiny_overlay.draw(surf)

        # Info area - show selected Pokemon info (semi-transparent like grid)
        info_bg = pygame.Surface(
            (self.info_area.width, self.info_area.height), pygame.SRCALPHA
        )

        # Use same background color logic as sprite area (using theme colors)
        if self.selected_pokemon and not self.selected_pokemon.get("empty"):
            r, g, b = (
                ui_colors.COLOR_BUTTON_HOVER[:3]
                if len(ui_colors.COLOR_BUTTON_HOVER) >= 3
                else (80, 80, 100)
            )
            info_bg_color = (r, g, b, 180)
        else:
            r, g, b = (
                ui_colors.COLOR_BUTTON[:3]
                if len(ui_colors.COLOR_BUTTON) >= 3
                else (60, 60, 60)
            )
            info_bg_color = (r, g, b, 180)

        pygame.draw.rect(
            info_bg, info_bg_color, (0, 0, self.info_area.width, self.info_area.height)
        )
        surf.blit(info_bg, self.info_area.topleft)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, self.info_area, 2)

        if self.selected_pokemon and not self.selected_pokemon.get("empty"):
            # Create slightly bigger font for info text
            try:
                info_font = scaled_font(14)
            except Exception:
                info_font = self.font

            # Format name and info
            if self.selected_pokemon.get("egg"):
                lines = ["EGG"]
            else:
                nickname = self.selected_pokemon.get("nickname", "").strip()
                species_name = self.selected_pokemon.get("species_name", "").strip()
                level = self.selected_pokemon.get("level", 0)

                lines = []

                # Helper: detect fallback/unknown species names like "#151" or "Pokemon #151"
                def is_fallback_species(name):
                    if not name:
                        return True
                    n = name.strip()
                    return n.startswith("#") or ("Pokemon #" in n) or ("pokemon #" in n.lower())

                # Determine if the pokemon has a real custom nickname.
                # In Gen 3, a non-nicknamed Pokemon has its nickname set to the
                # species name in uppercase, so they match case-insensitively.
                species_is_known = species_name and not is_fallback_species(species_name)
                has_real_nickname = (
                    nickname
                    and species_is_known
                    and nickname.upper().strip() != species_name.upper().strip()
                )

                if has_real_nickname:
                    # Genuinely nicknamed: show nickname + (SpeciesName) below
                    lines.append(nickname)
                    lines.append(f"({species_name})")
                    lines.append(f"Lv.{level}")
                elif species_is_known:
                    # No custom nickname - just show species name, no sub-label
                    lines.append(species_name)
                    lines.append(f"Lv.{level}")
                elif nickname and not is_fallback_species(nickname):
                    # Species unknown but nickname looks valid - show it
                    lines.append(nickname)
                    lines.append(f"Lv.{level}")
                else:
                    lines.append("???")
                    lines.append(f"Lv.{level}")

            # Draw text lines with wrapping inside the info box
            try:
                padding = ui.s(8)
                y_offset = self.info_area.y + padding
                line_height = ui.s(16)

                for line in lines:
                    # Ensure text fits in the box width
                    max_width = self.info_area.width - (padding * 2)

                    # Render with gender symbol support
                    if contains_gender_symbol(line):
                        text_surf = render_pokemon_name(info_font, line, ui_colors.COLOR_TEXT)
                    else:
                        text_surf = info_font.render(line, True, ui_colors.COLOR_TEXT)

                    # If text is too wide, try to fit it
                    if text_surf.get_width() > max_width:
                        # Truncate with ellipsis
                        while len(line) > 3 and text_surf.get_width() > max_width:
                            line = line[:-1]
                            if contains_gender_symbol(line):
                                text_surf = render_pokemon_name(info_font, line + "...", ui_colors.COLOR_TEXT)
                            else:
                                text_surf = info_font.render(
                                    line + "...", True, ui_colors.COLOR_TEXT
                                )

                    # Center horizontally in info area
                    text_x = (
                        self.info_area.x
                        + (self.info_area.width - text_surf.get_width()) // 2
                    )

                    # Make sure we don't overflow the box
                    if y_offset + line_height <= self.info_area.bottom - padding:
                        surf.blit(text_surf, (text_x, y_offset))
                        y_offset += line_height
                    else:
                        break  # Stop if we run out of space
            except Exception:
                pass
        elif self.sinew_mode:
            # Show Sinew storage stats when no Pokemon selected
            try:
                info_font = scaled_font(10)
                padding = ui.s(8)
                y_offset = self.info_area.y + padding
                line_height = ui.s(14)

                # Get storage stats
                if self.sinew_storage:
                    total_pokemon = self.sinew_storage.get_total_pokemon_count()
                    box_pokemon = self.sinew_storage.get_box_pokemon_count(
                        self.box_index + 1
                    )
                    max_capacity = 20 * 120  # 20 boxes * 120 slots

                    lines = [
                        "SINEW STORAGE",
                        "",
                        f"This Box: {box_pokemon}/120",
                        f"Total: {total_pokemon}",
                        f"Capacity: {max_capacity}",
                    ]
                else:
                    lines = ["SINEW STORAGE", "", "Not loaded"]

                for line in lines:
                    if line == "":
                        y_offset += ui.s(4)
                        continue
                    text_surf = info_font.render(line, True, ui_colors.COLOR_TEXT)
                    text_x = (
                        self.info_area.x
                        + (self.info_area.width - text_surf.get_width()) // 2
                    )
                    if y_offset + line_height <= self.info_area.bottom - padding:
                        surf.blit(text_surf, (text_x, y_offset))
                        y_offset += line_height
            except Exception:
                pass

        # ---------------------------------------------------------------- #
        #  Top buttons                                                      #
        # ---------------------------------------------------------------- #
        # Draw Game button row (without highlighting arrows - they're not navigable)
        self.left_game_arrow.draw(surf, self.font)
        self.right_game_arrow.draw(surf, self.font)

        # Highlight game button if focused
        if self.focus_mode == "game_button":
            highlight_rect = self.game_button.rect.inflate(4, 4)
            pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 3)
        self.game_button.draw(surf, self.font)

        # Draw Box button row
        self.left_box_arrow.draw(surf, self.font)
        self.right_box_arrow.draw(surf, self.font)

        # Highlight box button if focused
        if self.focus_mode == "box_button":
            highlight_rect = self.box_button.rect.inflate(4, 4)
            pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 3)
        self.box_button.draw(surf, self.font)

        # Draw side buttons with focus indicators
        # Party button - disabled in Sinew mode
        if self.sinew_mode:
            # Draw disabled party button (dimmed theme colors)
            disabled_rect = self.party_button.rect
            r, g, b = (
                ui_colors.COLOR_BUTTON[:3]
                if len(ui_colors.COLOR_BUTTON) >= 3
                else (40, 40, 45)
            )
            pygame.draw.rect(surf, (r // 2, g // 2, b // 2), disabled_rect)
            pygame.draw.rect(surf, (r, g, b), disabled_rect, 2)
            try:
                btn_font = scaled_font(10)
                text = "No Party"
                # Dimmed text color
                tr, tg, tb = (
                    ui_colors.COLOR_TEXT[:3]
                    if len(ui_colors.COLOR_TEXT) >= 3
                    else (80, 80, 90)
                )
                text_surf = btn_font.render(text, True, (tr // 2, tg // 2, tb // 2))
                text_rect = text_surf.get_rect(center=disabled_rect.center)
                surf.blit(text_surf, text_rect)
            except Exception:
                pass
        else:
            if self.focus_mode == "side_buttons" and self.side_button_index == 0:
                highlight_rect = self.party_button.rect.inflate(4, 4)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 3)
            self.party_button.draw(surf, self.font)

        # Close button (always at index 1 now)
        if self.focus_mode == "side_buttons" and self.side_button_index == 1:
            highlight_rect = self.close_button.rect.inflate(4, 4)
            pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 3)
        self.close_button.draw(surf, self.font)

        # ---------------------------------------------------------------- #
        #  Undo button (centered between sprite and grid)                  #
        # ---------------------------------------------------------------- #
        if self.undo_available:
            # Position: bottom-right corner of sprite preview area
            undo_size = ui.s(32)
            padding = ui.s(5)
            undo_x = self.sprite_area.right - undo_size - padding
            undo_y = self.sprite_area.bottom - undo_size - padding
            undo_rect = pygame.Rect(undo_x, undo_y, undo_size, undo_size)

            # Store rect for click detection
            self.undo_button_rect = undo_rect

            # Draw button background using theme colors
            is_undo_focused = self.focus_mode == "undo_button"
            if is_undo_focused:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON_HOVER, undo_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, undo_rect, 3)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, undo_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, undo_rect, 2)

            # Draw undo icon (tinted to theme color)
            try:
                if self.undo_icon:
                    # Get current theme text color
                    current_color = (
                        ui_colors.COLOR_TEXT[:3]
                        if len(ui_colors.COLOR_TEXT) >= 3
                        else (255, 255, 255)
                    )

                    # Re-tint icon if color changed or not yet tinted
                    if (
                        self._undo_icon_last_color != current_color
                        or self.undo_icon_tinted is None
                    ):
                        self._undo_icon_last_color = current_color
                        # Create tinted copy
                        self.undo_icon_tinted = self.undo_icon.copy()
                        # Apply color tint by filling with color and using BLEND_RGB_MULT
                        self.undo_icon_tinted.fill(
                            current_color + (0,),
                            special_flags=pygame.BLEND_RGB_MULT,
                        )

                    # Draw the tinted icon centered in button
                    icon_rect = self.undo_icon_tinted.get_rect(
                        center=undo_rect.center
                    )
                    surf.blit(self.undo_icon_tinted, icon_rect)
                else:
                    # Fallback to "U" text if icon not loaded
                    undo_font = scaled_font(14)
                    u_surf = undo_font.render("U", True, ui_colors.COLOR_TEXT)
                    u_rect = u_surf.get_rect(center=undo_rect.center)
                    surf.blit(u_surf, u_rect)
            except Exception:
                pass
        else:
            self.undo_button_rect = None

        # ---------------------------------------------------------------- #
        #  Grid                                                             #
        # ---------------------------------------------------------------- #
        self.draw_grid(surf)

        # ---------------------------------------------------------------- #
        #  Controller hints                                                 #
        # ---------------------------------------------------------------- #
        try:
            hint_font = scaled_font(8)
            if self.sinew_mode:
                hints = "L/R: Scroll  A: Select  B: Back"
            elif self.party_panel_open:
                hints = "D-Pad: Move  A: Select  B: Close"
            else:
                hints = "L/R: Box  A: Select  B: Back"
            # Use dimmed theme text color
            tr, tg, tb = (
                ui_colors.COLOR_TEXT[:3]
                if len(ui_colors.COLOR_TEXT) >= 3
                else (120, 120, 120)
            )
            hint_surf = hint_font.render(hints, True, (tr // 2, tg // 2, tb // 2))
            surf.blit(hint_surf, (ui.s(10), self.height - ui.s(15)))
        except Exception:
            pass

        # ---------------------------------------------------------------- #
        #  Party panel (animated slide-in)                                 #
        # ---------------------------------------------------------------- #
        if (
            self.party_panel_open
            and self.party_panel_rect.y < self.party_panel_target_y
        ):
            self.party_panel_rect.y += self.party_panel_speed
            if self.party_panel_rect.y > self.party_panel_target_y:
                self.party_panel_rect.y = self.party_panel_target_y
        elif (
            not self.party_panel_open
            and self.party_panel_rect.y > self.party_panel_target_y
        ):
            self.party_panel_rect.y -= self.party_panel_speed
            if self.party_panel_rect.y < self.party_panel_target_y:
                self.party_panel_rect.y = self.party_panel_target_y

        if self.party_panel_rect.y > -self.height:
            # Make panel thinner (~40% smaller)
            panel_width = self.party_panel_rect.width * 0.7
            panel_rect = pygame.Rect(
                self.party_panel_rect.x,
                self.party_panel_rect.y,
                panel_width,
                self.party_panel_rect.height,
            )

            # Top/bottom padding
            top_pad = ui.s(10)
            bottom_pad = ui.s(10)
            inner_height = panel_rect.height - top_pad - bottom_pad
            inner_y = panel_rect.y + top_pad

            # Draw solid background (same color as buttons)
            panel_bg = pygame.Surface((panel_rect.width, panel_rect.height))
            panel_bg.fill(ui_colors.COLOR_BUTTON)  # Match button color
            surf.blit(panel_bg, (panel_rect.x, panel_rect.y))

            # Draw border
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, panel_rect, 2)

            # Draw slots inside inner area with party data
            slots = self.get_party_slot_rects(
                inner_y=inner_y, inner_height=inner_height
            )
            for i, slot in enumerate(slots):
                # Get Pokemon if exists
                poke = self.party_data[i] if i < len(self.party_data) else None

                # Determine if this is the selected Pokemon
                is_selected = (
                    poke
                    and self.selected_pokemon
                    and poke.get("species") == self.selected_pokemon.get("species")
                    and poke.get("personality")
                    == self.selected_pokemon.get("personality")
                )

                # Check if this slot is controller-selected
                is_controller_selected = (
                    i == self.party_selected and self.party_panel_open
                )

                # Base color for slot using theme colors
                if poke:
                    # Occupied slot - brighter
                    r, g, b = (
                        ui_colors.COLOR_BUTTON_HOVER[:3]
                        if len(ui_colors.COLOR_BUTTON_HOVER) >= 3
                        else (80, 80, 100)
                    )
                    base_color = (r, g, b, 180)
                else:
                    # Empty slot - dimmer
                    r, g, b = (
                        ui_colors.COLOR_BUTTON[:3]
                        if len(ui_colors.COLOR_BUTTON) >= 3
                        else (60, 60, 60)
                    )
                    base_color = (r, g, b, 180)

                # Draw slot background with transparency
                slot_surf = pygame.Surface((slot.width, slot.height), pygame.SRCALPHA)
                pygame.draw.rect(slot_surf, base_color, (0, 0, slot.width, slot.height))
                surf.blit(slot_surf, slot.topleft)

                # Draw border
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, slot, 2)

                # Highlight controller-selected slot
                if is_controller_selected:
                    pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, slot, 3)

                # Highlight selected Pokemon (yellow to distinguish from cursor)
                if is_selected and not is_controller_selected:
                    # Draw bright highlight border
                    pygame.draw.rect(surf, (255, 255, 100), slot, 3)

                # Draw Pokemon sprite (gen3) if available
                if poke:

                    if not poke.get("egg"):
                        # Get Pokemon ID and shiny status
                        poke_id = poke.get("species", 0)
                        is_shiny = self._compute_is_shiny(poke)
                        
                        # Calculate sprite size
                        max_sprite_w = int(slot.width * 0.7)
                        max_sprite_h = int(slot.height * 0.7)
                        sprite_size = min(max_sprite_w, max_sprite_h)
                        
                        sprite_drawn = False
                        
                        # Check if this is the hovered/selected party Pokemon
                        is_hovered = (i == self.party_selected and self.party_panel_open)
                        
                        # Cache sprite info per Pokemon
                        personality = poke.get("personality", 0)
                        pokemon_cache_key = f"party_poke_{poke_id}_{personality}_{is_shiny}"
                        
                        if not hasattr(self, '_pokemon_sprite_info_cache'):
                            self._pokemon_sprite_info_cache = {}
                        
                        if pokemon_cache_key not in self._pokemon_sprite_info_cache:
                            # First time - get sprite
                            prefer_gif = True
                            sprite_path, is_gif = self._get_best_sprite_path(poke_id, is_shiny, prefer_gif=prefer_gif)
                            self._pokemon_sprite_info_cache[pokemon_cache_key] = {
                                'path': sprite_path,
                                'is_gif': is_gif
                            }
                        
                        sprite_info = self._pokemon_sprite_info_cache[pokemon_cache_key]
                        sprite_path = sprite_info['path']
                        is_gif = sprite_info['is_gif']
                        
                        if is_hovered and is_gif and sprite_path:
                                # Load or get cached GIF for this slot
                                cache_key = f"party_{i}"
                                if not hasattr(self, '_party_gif_cache'):
                                    self._party_gif_cache = {}
                                
                                if cache_key not in self._party_gif_cache or self._party_gif_cache[cache_key]['path'] != sprite_path:
                                    frames, durations = self._load_gif_frames(sprite_path, sprite_size, sprite_size)
                                    if frames:
                                        self._party_gif_cache[cache_key] = {
                                            'path': sprite_path,
                                            'frames': frames,
                                            'durations': durations,
                                            'index': 0,
                                            'timer': 0
                                        }
                                
                                # Animate
                                if cache_key in self._party_gif_cache:
                                    gif_data = self._party_gif_cache[cache_key]
                                    if gif_data['frames']:
                                        gif_data['timer'] += 16  # Assume ~16ms per frame
                                        current_duration = gif_data['durations'][gif_data['index']]
                                        
                                        if gif_data['timer'] >= current_duration:
                                            gif_data['timer'] = 0
                                            gif_data['index'] = (gif_data['index'] + 1) % len(gif_data['frames'])
                                        
                                        # Draw current frame
                                        frame = gif_data['frames'][gif_data['index']]
                                        sprite_rect = frame.get_rect(center=slot.center)
                                        surf.blit(frame, sprite_rect)
                                        sprite_drawn = True
                        
                        # Static sprite (not hovered)
                        if not sprite_drawn and sprite_path:
                            if is_gif:
                                # Show first frame of GIF (static)
                                cache_key = f"static_{poke_id:03d}_{is_shiny}"
                                if not hasattr(self, '_static_gif_cache'):
                                    self._static_gif_cache = {}
                                
                                # Load and cache first frame if not cached
                                if cache_key not in self._static_gif_cache:
                                    try:
                                        frames, _ = self._load_gif_frames(sprite_path, sprite_size, sprite_size)
                                        if frames and len(frames) > 0:
                                            self._static_gif_cache[cache_key] = frames[0]
                                    except Exception:
                                        self._static_gif_cache[cache_key] = None
                                
                                # Draw cached static frame
                                if cache_key in self._static_gif_cache and self._static_gif_cache[cache_key]:
                                    first_frame = self._static_gif_cache[cache_key]
                                    sprite_rect = first_frame.get_rect(center=slot.center)
                                    surf.blit(first_frame, sprite_rect)
                                    sprite_drawn = True
                            else:
                                # PNG sprite
                                try:
                                    sprite = pygame.image.load(sprite_path).convert_alpha()
                                    sprite = scale_surface_preserve_aspect(sprite, sprite_size, sprite_size)
                                    sprite_rect = sprite.get_rect(center=slot.center)
                                    surf.blit(sprite, sprite_rect)
                                    sprite_drawn = True
                                except Exception:
                                    pass  # If sprite fails, fall back to text
                        
                        # Draw ROM HACK overlay for Pokemon from ROM hacks
                        if sprite_drawn and poke.get("rom_hack"):
                            self._draw_rom_hack_overlay(surf, slot, size="small")
                        
                        # If no sprite drawn, show text fallback
                        if not sprite_drawn:
                            try:
                                text = self.manager.format_pokemon_display(poke)
                                tiny_font = scaled_font(10)
                                text_surf = tiny_font.render(
                                    text[:8], True, ui_colors.COLOR_TEXT
                                )
                                text_rect = text_surf.get_rect(center=slot.center)
                                surf.blit(text_surf, text_rect)
                            except Exception:
                                pass
                    else:
                        # Draw egg sprite for eggs
                        egg_path = get_egg_sprite_path("gen3")
                        if os.path.exists(egg_path):
                            try:
                                egg_sprite = self.sprite_cache.get_png_sprite(
                                    egg_path, size=None
                                )
                                if egg_sprite:
                                    # Scale to fit slot with margin, preserving aspect ratio
                                    sprite_size = int(
                                        min(slot.width, slot.height) * 0.7
                                    )
                                    egg_sprite = scale_surface_preserve_aspect(
                                        egg_sprite, sprite_size, sprite_size
                                    )
                                    sprite_rect = egg_sprite.get_rect(
                                        center=slot.center
                                    )
                                    surf.blit(egg_sprite, sprite_rect)
                                else:
                                    raise Exception("Sprite cache failed")
                            except Exception:
                                # Fallback to text if sprite fails
                                try:
                                    tiny_font = scaled_font(10)
                                    text_surf = tiny_font.render(
                                        "EGG", True, ui_colors.COLOR_TEXT
                                    )
                                    text_rect = text_surf.get_rect(center=slot.center)
                                    surf.blit(text_surf, text_rect)
                                except Exception:
                                    pass
                        else:
                            # No egg sprite, show text
                            try:
                                tiny_font = scaled_font(10)
                                text_surf = tiny_font.render(
                                    "EGG", True, ui_colors.COLOR_TEXT
                                )
                                text_rect = text_surf.get_rect(center=slot.center)
                                surf.blit(text_surf, text_rect)
                            except Exception:
                                pass

        # Draw options menu overlay (on top of everything)
        self._draw_move_mode_overlay(surf)
        self._draw_options_menu(surf)
        self._draw_confirmation_dialog(surf)
        self._draw_evolution_dialog(surf)
        self._draw_altering_cave_dialog(surf)
        self._draw_warning_message(surf)

        # Draw sub_modal (summary screen) on top of everything
        if self.sub_modal:
            if hasattr(self.sub_modal, "update"):
                self.sub_modal.update(dt)
            if hasattr(self.sub_modal, "draw"):
                self.sub_modal.draw(surf)

    # ------------------------------------------------------------------ #
    #  Overlay drawing helpers                                             #
    # ------------------------------------------------------------------ #

    def _draw_move_mode_overlay(self, surf):
        """Draw the moving Pokemon sprite following cursor/selection."""
        if not self.move_mode or not self.moving_sprite:
            return

        # Draw "MOVE MODE" indicator at bottom
        try:
            font = scaled_font(12)
            mode_text = font.render(
                "MOVE MODE - Select empty slot", True, (255, 255, 100)
            )
            text_rect = mode_text.get_rect(
                centerx=self.width // 2, bottom=self.height - ui.s(10)
            )

            # Background for text
            bg_rect = text_rect.inflate(ui.s(20), ui.s(10))
            pygame.draw.rect(surf, (0, 0, 0, 200), bg_rect)
            pygame.draw.rect(surf, (255, 255, 100), bg_rect, 2)
            surf.blit(mode_text, text_rect)
        except Exception:
            pass

        # Draw sprite at current grid selection
        grid_index = self.grid_nav.get_selected()
        col = grid_index % self.grid_cols
        row = grid_index // self.grid_cols

        cell_w = self.grid_rect.width // self.grid_cols
        cell_h = self.grid_rect.height // self.grid_rows

        x = self.grid_rect.x + col * cell_w + cell_w // 2
        y = self.grid_rect.y + row * cell_h + cell_h // 2

        # Draw the sprite with slight offset and transparency effect
        sprite_rect = self.moving_sprite.get_rect(center=(x, y - ui.s(10)))

        # Draw shadow
        shadow = pygame.Surface((ui.s(40), ui.s(20)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), (0, 0, ui.s(40), ui.s(20)))
        surf.blit(shadow, (sprite_rect.centerx - ui.s(20), sprite_rect.bottom - ui.s(5)))

        # Draw sprite
        surf.blit(self.moving_sprite, sprite_rect)

    def _draw_options_menu(self, surf):
        """Draw the options menu overlay."""
        if not self.options_menu_open:
            return

        # Menu dimensions
        menu_width = ui.s(120)
        menu_height = len(self.options_menu_items) * ui.s(30) + ui.s(20)
        menu_x = self.width // 2 - menu_width // 2
        menu_y = self.height // 2 - menu_height // 2

        # Draw menu background using theme colors
        menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, menu_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, menu_rect, 3)

        # Draw menu items
        try:
            font = scaled_font(14)

            for i, item in enumerate(self.options_menu_items):
                item_y = menu_y + ui.s(15) + i * ui.s(30)

                # Highlight selected item
                if i == self.options_menu_selected:
                    highlight_rect = pygame.Rect(
                        menu_x + ui.s(5), item_y - ui.s(5), menu_width - ui.s(10), ui.s(28)
                    )
                    pygame.draw.rect(surf, ui_colors.COLOR_BUTTON_HOVER, highlight_rect)
                    pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, highlight_rect, 2)

                    # Draw cursor
                    cursor = font.render(">", True, ui_colors.COLOR_HIGHLIGHT)
                    surf.blit(cursor, (menu_x + ui.s(10), item_y))

                # Draw item text
                text = font.render(item, True, ui_colors.COLOR_TEXT)
                surf.blit(text, (menu_x + ui.s(30), item_y))
        except Exception:
            pass

    def _draw_confirmation_dialog(self, surf):
        """Draw the confirmation dialog overlay."""
        if not self.confirmation_dialog_open:
            return

        # Darken background
        dark_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 150))
        surf.blit(dark_overlay, (0, 0))

        # Dialog dimensions
        dialog_width = ui.s(300)
        dialog_height = ui.s(140)
        dialog_x = self.width // 2 - dialog_width // 2
        dialog_y = self.height // 2 - dialog_height // 2

        # Draw dialog background using theme colors
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, dialog_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, dialog_rect, 3)

        try:
            font = scaled_font(12)
            small_font = scaled_font(14)

            # Draw message (multiline)
            lines = self.confirmation_dialog_message.split("\n")
            for i, line in enumerate(lines):
                text = font.render(line, True, ui_colors.COLOR_TEXT)
                text_rect = text.get_rect(
                    centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(15) + i * ui.s(20)
                )
                surf.blit(text, text_rect)

            # Draw Yes/No buttons
            button_y = dialog_y + dialog_height - ui.s(40)
            yes_x = dialog_x + dialog_width // 4
            no_x = dialog_x + 3 * dialog_width // 4

            # Yes button
            yes_rect = pygame.Rect(yes_x - ui.s(40), button_y - ui.s(5), ui.s(80), ui.s(30))
            if self.confirmation_selected == 0:
                pygame.draw.rect(surf, ui_colors.COLOR_SUCCESS, yes_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, yes_rect, 2)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, yes_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, yes_rect, 2)
            yes_text = small_font.render("YES", True, ui_colors.COLOR_TEXT)
            yes_text_rect = yes_text.get_rect(center=yes_rect.center)
            surf.blit(yes_text, yes_text_rect)

            # No button
            no_rect = pygame.Rect(no_x - ui.s(40), button_y - ui.s(5), ui.s(80), ui.s(30))
            if self.confirmation_selected == 1:
                pygame.draw.rect(surf, ui_colors.COLOR_ERROR, no_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, no_rect, 2)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, no_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, no_rect, 2)
            no_text = small_font.render("NO", True, ui_colors.COLOR_TEXT)
            no_text_rect = no_text.get_rect(center=no_rect.center)
            surf.blit(no_text, no_text_rect)
        except Exception:
            pass

    def _draw_evolution_dialog(self, surf):
        """Draw the trade evolution dialog overlay."""
        if not self.evolution_dialog_open or not self.evolution_dialog_info:
            return

        # Darken background
        dark_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 180))
        surf.blit(dark_overlay, (0, 0))

        # Dialog dimensions
        dialog_width = ui.s(340)
        dialog_height = ui.s(160)
        dialog_x = self.width // 2 - dialog_width // 2
        dialog_y = self.height // 2 - dialog_height // 2

        # Draw dialog background using theme colors
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, dialog_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, dialog_rect, 3)

        try:
            font = scaled_font(12)
            title_font = scaled_font(14)
            small_font = scaled_font(14)

            evo_info = self.evolution_dialog_info
            pokemon = self.evolution_dialog_pokemon

            # Get Pokemon name (nickname or species name)
            pokemon_name = pokemon.get("nickname") or evo_info["from_name"]

            # Title
            title_text = title_font.render("What?", True, ui_colors.COLOR_HOVER_TEXT)
            title_rect = title_text.get_rect(
                centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(12)
            )
            surf.blit(title_text, title_rect)

            # Evolution message
            msg1 = f"{pokemon_name} is evolving!"
            if contains_gender_symbol(msg1):
                msg1_text = render_pokemon_name(font, msg1, ui_colors.COLOR_TEXT)
            else:
                msg1_text = font.render(msg1, True, ui_colors.COLOR_TEXT)
            msg1_rect = msg1_text.get_rect(
                centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(40)
            )
            surf.blit(msg1_text, msg1_rect)

            # Arrow and evolution target
            arrow_msg = f"-> {evo_info['to_name']}"
            if contains_gender_symbol(arrow_msg):
                arrow_text = render_pokemon_name(font, arrow_msg, ui_colors.COLOR_SUCCESS)
            else:
                arrow_text = font.render(arrow_msg, True, ui_colors.COLOR_SUCCESS)
            arrow_rect = arrow_text.get_rect(
                centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(62)
            )
            surf.blit(arrow_text, arrow_rect)

            # Item consumption message (if applicable)
            if evo_info.get("consumes_item") and evo_info.get("item_name"):
                item_msg = f"({evo_info['item_name']} will be used)"
                # Dimmed text
                tr, tg, tb = (
                    ui_colors.COLOR_TEXT[:3]
                    if len(ui_colors.COLOR_TEXT) >= 3
                    else (180, 180, 180)
                )
                item_text = font.render(
                    item_msg, True, (tr * 2 // 3, tg * 2 // 3, tb * 2 // 3)
                )
                item_rect = item_text.get_rect(
                    centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(84)
                )
                surf.blit(item_text, item_rect)

            # Draw Evolve/Stop buttons
            button_y = dialog_y + dialog_height - ui.s(40)
            evolve_x = dialog_x + dialog_width // 4
            stop_x = dialog_x + 3 * dialog_width // 4

            # Evolve button
            evolve_rect = pygame.Rect(evolve_x - ui.s(50), button_y - ui.s(5), ui.s(100), ui.s(30))
            if self.evolution_selected == 0:
                pygame.draw.rect(surf, ui_colors.COLOR_SUCCESS, evolve_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, evolve_rect, 2)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, evolve_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, evolve_rect, 2)
            evolve_text = small_font.render("EVOLVE", True, ui_colors.COLOR_TEXT)
            evolve_text_rect = evolve_text.get_rect(center=evolve_rect.center)
            surf.blit(evolve_text, evolve_text_rect)

            # Stop button
            stop_rect = pygame.Rect(stop_x - ui.s(50), button_y - ui.s(5), ui.s(100), ui.s(30))
            if self.evolution_selected == 1:
                pygame.draw.rect(surf, ui_colors.COLOR_ERROR, stop_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, stop_rect, 2)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, stop_rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, stop_rect, 2)
            stop_text = small_font.render("STOP", True, ui_colors.COLOR_TEXT)
            stop_text_rect = stop_text.get_rect(center=stop_rect.center)
            surf.blit(stop_text, stop_text_rect)
        except Exception as e:
            print(f"[PCBox] Error drawing evolution dialog: {e}")

    # ------------------------------------------------------------------ #
    #  Altering Cave dialog & spinner                                      #
    # ------------------------------------------------------------------ #

    def _draw_altering_cave_dialog(self, surf):
        """Draw the Altering Cave confirmation dialog or spinner."""
        # Update pulse timer
        self._altering_cave_pulse_timer = (self._altering_cave_pulse_timer + 1) % 60

        if not self.altering_cave_dialog_open:
            return

        if self.altering_cave_spinner_active:
            self._draw_altering_cave_spinner(surf)
            return

        # Darken background
        dark_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 180))
        surf.blit(dark_overlay, (0, 0))

        # Dialog dimensions
        dialog_width = ui.s(380)
        dialog_height = ui.s(180)
        dialog_x = self.width // 2 - dialog_width // 2
        dialog_y = self.height // 2 - dialog_height // 2

        # Draw dialog background with mystical purple tint
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        # Purple-ish background
        pygame.draw.rect(surf, (40, 30, 60), dialog_rect)
        pygame.draw.rect(surf, (150, 100, 200), dialog_rect, 3)

        try:
            font = scaled_font(11)
            title_font = scaled_font(13)
            small_font = scaled_font(12)

            # Title with wavy effect
            title_text = title_font.render("~ Echoes ~", True, (200, 150, 255))
            title_rect = title_text.get_rect(
                centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(12)
            )
            surf.blit(title_text, title_rect)

            # Message lines
            msg1 = "This Zubat from Altering Cave"
            msg2 = "carries echoes of what never was..."
            msg3 = "Care to try your luck?"

            msg1_text = font.render(msg1, True, (220, 220, 255))
            msg1_rect = msg1_text.get_rect(
                centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(45)
            )
            surf.blit(msg1_text, msg1_rect)

            msg2_text = font.render(msg2, True, (180, 180, 220))
            msg2_rect = msg2_text.get_rect(
                centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(65)
            )
            surf.blit(msg2_text, msg2_rect)

            msg3_text = font.render(msg3, True, (255, 255, 200))
            msg3_rect = msg3_text.get_rect(
                centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(95)
            )
            surf.blit(msg3_text, msg3_rect)

            # Progress indicator
            if _ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
                manager = get_achievement_manager()
                claimed = len(manager.get_altering_cave_claimed())
                progress_text = font.render(
                    f"({claimed}/7 discovered)", True, (150, 150, 180)
                )
                progress_rect = progress_text.get_rect(
                    centerx=dialog_x + dialog_width // 2, top=dialog_y + ui.s(115)
                )
                surf.blit(progress_text, progress_rect)

            # Draw Yes/No buttons
            button_y = dialog_y + dialog_height - ui.s(40)
            yes_x = dialog_x + dialog_width // 4
            no_x = dialog_x + 3 * dialog_width // 4

            # Yes button
            yes_rect = pygame.Rect(yes_x - ui.s(50), button_y - ui.s(5), ui.s(100), ui.s(30))
            if self.altering_cave_selected == 0:
                pygame.draw.rect(surf, (100, 80, 180), yes_rect)
                pygame.draw.rect(surf, (200, 150, 255), yes_rect, 2)
            else:
                pygame.draw.rect(surf, (50, 40, 80), yes_rect)
                pygame.draw.rect(surf, (100, 80, 150), yes_rect, 2)
            yes_text = small_font.render("YES", True, (255, 255, 255))
            yes_text_rect = yes_text.get_rect(center=yes_rect.center)
            surf.blit(yes_text, yes_text_rect)

            # No button
            no_rect = pygame.Rect(no_x - ui.s(50), button_y - ui.s(5), ui.s(100), ui.s(30))
            if self.altering_cave_selected == 1:
                pygame.draw.rect(surf, (80, 60, 60), no_rect)
                pygame.draw.rect(surf, (180, 100, 100), no_rect, 2)
            else:
                pygame.draw.rect(surf, (50, 40, 50), no_rect)
                pygame.draw.rect(surf, (100, 80, 100), no_rect, 2)
            no_text = small_font.render("NO", True, (255, 255, 255))
            no_text_rect = no_text.get_rect(center=no_rect.center)
            surf.blit(no_text, no_text_rect)
        except Exception as e:
            print(f"[PCBox] Error drawing Altering Cave dialog: {e}")

    def _draw_altering_cave_spinner(self, surf):
        """Draw the slot machine spinner for Altering Cave Pokemon."""
        # Darken background
        dark_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 200))
        surf.blit(dark_overlay, (0, 0))

        # Spinner dimensions - more compact to fit screen
        spinner_width = ui.s(220)
        spinner_height = ui.s(260)
        spinner_x = self.width // 2 - spinner_width // 2
        spinner_y = self.height // 2 - spinner_height // 2 + ui.s(10)  # Slight offset down

        # Ensure it doesn't go off screen
        spinner_y = max(ui.s(10), spinner_y)

        # Draw spinner frame (slot machine style)
        frame_rect = pygame.Rect(spinner_x, spinner_y, spinner_width, spinner_height)
        pygame.draw.rect(surf, (30, 20, 50), frame_rect)
        pygame.draw.rect(surf, (150, 100, 200), frame_rect, 3)

        try:
            title_font = scaled_font(10)
            font = scaled_font(9)

            # Title - inside the frame
            title = title_font.render("WHAT NEVER WAS", True, (200, 150, 255))
            title_rect = title.get_rect(
                centerx=spinner_x + spinner_width // 2, top=spinner_y + ui.s(10)
            )
            surf.blit(title, title_rect)

            # Reel window (center area where Pokemon scroll)
            window_width = ui.s(140)
            window_height = ui.s(140)
            window_x = spinner_x + (spinner_width - window_width) // 2
            window_y = spinner_y + ui.s(35)
            window_rect = pygame.Rect(window_x, window_y, window_width, window_height)

            # Window background
            pygame.draw.rect(surf, (20, 15, 35), window_rect)
            pygame.draw.rect(surf, (100, 70, 150), window_rect, 2)

            # Get Pokemon list for display
            remaining = getattr(self, "altering_cave_remaining", [])
            if not remaining:
                if _ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
                    manager = get_achievement_manager()
                    remaining = manager.get_altering_cave_remaining()
                else:
                    remaining = ALTERING_CAVE_POKEMON.copy()

            if remaining:
                item_height = ui.s(56)  # Height per Pokemon sprite
                total_height = len(remaining) * item_height

                # Wrap offset for continuous scrolling
                wrapped_offset = self.altering_cave_spinner_offset % total_height

                center_y = window_y + window_height // 2

                # Create a clipping surface for the window
                clip_surf = pygame.Surface(
                    (window_width - 4, window_height - 4), pygame.SRCALPHA
                )
                clip_surf.fill((20, 15, 35, 255))  # Match window background

                # Draw enough Pokemon to fill the window
                for i in range(-3, 5):
                    # Calculate which Pokemon index this is
                    poke_index = int((wrapped_offset // item_height) + i) % len(
                        remaining
                    )
                    poke = remaining[poke_index]

                    # Calculate y position relative to clip surface
                    base_y = (window_height - 4) // 2 + (i * item_height)
                    offset_in_item = wrapped_offset % item_height
                    y_pos = base_y - offset_in_item

                    # Get sprite - try multiple paths
                    species_id = poke["species"]
                    sprite = None
                    # Get current game name for per-game sprite pack support
                    game_name = None
                    if hasattr(self, 'get_current_game_callback') and self.get_current_game_callback:
                        game_name = self.get_current_game_callback()
                    
                    is_shiny = self._compute_is_shiny(poke)
                    
                    # Try sprite_paths system with fallback to global
                    try:
                        from sprite_paths import get_sprite_path_for_game
                        sprite_path = get_sprite_path_for_game(
                            species_id, 
                            game_name, 
                            is_shiny,
                            fallback_to_global=True  # If species not in pack, use global
                        )
                        
                        # Debug: log what we got
                        if sprite_path:
                            print(f"[PCBox Grid] Species {species_id}, game={game_name}, path={sprite_path}, exists={os.path.exists(sprite_path)}")
                        else:
                            print(f"[PCBox Grid] Species {species_id}, game={game_name}, NO PATH RETURNED")
                        
                        if sprite_path and os.path.exists(sprite_path):
                            try:
                                sprite = pygame.image.load(sprite_path).convert_alpha()
                                # Scale to 48x48, preserving aspect ratio
                                sprite = scale_surface_preserve_aspect(sprite, ui.s(48), ui.s(48))
                            except Exception as e:
                                print(f"[PCBox Grid] Failed to load sprite {sprite_path}: {e}")
                    except Exception as e:
                        print(f"[PCBox Grid] sprite_paths failed for species {species_id}: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    # Legacy fallback if sprite_paths fails
                    if not sprite:
                        sprite_paths = [get_sprite_path(species_id, sprite_type="gen3")]
                        for sprite_path in sprite_paths:
                            if os.path.exists(sprite_path):
                                try:
                                    sprite = pygame.image.load(sprite_path).convert_alpha()
                                    # Scale to 48x48, preserving aspect ratio
                                    sprite = scale_surface_preserve_aspect(sprite, ui.s(48), ui.s(48))
                                    break
                                except Exception:
                                    continue

                    if sprite:
                        sprite_rect = sprite.get_rect(
                            center=((window_width - 4) // 2, int(y_pos))
                        )
                        clip_surf.blit(sprite, sprite_rect)
                    else:
                        # Fallback: draw Pokemon name with gender symbol support
                        name_text = render_pokemon_name(font, poke["name"], (200, 200, 255))
                        name_rect = name_text.get_rect(
                            center=((window_width - 4) // 2, int(y_pos))
                        )
                        clip_surf.blit(name_text, name_rect)

                # Blit the clipped surface
                surf.blit(clip_surf, (window_x + 2, window_y + 2))

                # Draw selection indicator arrows on sides
                indicator_y = center_y
                # Left arrow
                arrow_points_l = [
                    (window_x - ui.s(12), indicator_y),
                    (window_x - ui.s(4), indicator_y - ui.s(8)),
                    (window_x - ui.s(4), indicator_y + ui.s(8)),
                ]
                pygame.draw.polygon(surf, (255, 200, 100), arrow_points_l)
                # Right arrow
                arrow_points_r = [
                    (window_x + window_width + ui.s(12), indicator_y),
                    (window_x + window_width + ui.s(4), indicator_y - ui.s(8)),
                    (window_x + window_width + ui.s(4), indicator_y + ui.s(8)),
                ]
                pygame.draw.polygon(surf, (255, 200, 100), arrow_points_r)

                # Horizontal lines above and below center slot
                line_color = (255, 200, 100)
                pygame.draw.line(
                    surf,
                    line_color,
                    (window_x + 3, indicator_y - item_height // 2),
                    (window_x + window_width - 3, indicator_y - item_height // 2),
                    2,
                )
                pygame.draw.line(
                    surf,
                    line_color,
                    (window_x + 3, indicator_y + item_height // 2),
                    (window_x + window_width - 3, indicator_y + item_height // 2),
                    2,
                )

            # Status text area
            if self.altering_cave_spinner_stopped:
                if self.altering_cave_result_timer > 0:
                    self.altering_cave_result_timer -= 1
                elif not self.altering_cave_spinner_show_result:
                    self.altering_cave_spinner_show_result = True

            status_y = spinner_y + spinner_height - ui.s(65)

            if (
                self.altering_cave_spinner_show_result
                and self.altering_cave_spinner_result
            ):
                # Show result with sprite
                result = self.altering_cave_spinner_result
                result_name = result["name"]

                # Draw result Pokemon name
                result_text = title_font.render(
                    f"{result_name}!", True, (100, 255, 100)
                )
                result_rect = result_text.get_rect(
                    centerx=spinner_x + spinner_width // 2, top=status_y
                )
                surf.blit(result_text, result_rect)

                # Press A prompt
                prompt_text = font.render("Press A", True, (200, 200, 200))
                prompt_rect = prompt_text.get_rect(
                    centerx=spinner_x + spinner_width // 2, top=status_y + ui.s(20)
                )
                surf.blit(prompt_text, prompt_rect)
            elif self.altering_cave_spinner_speed > 0:
                spin_text = font.render("Spinning...", True, (255, 255, 200))
                spin_rect = spin_text.get_rect(
                    centerx=spinner_x + spinner_width // 2, top=status_y + ui.s(10)
                )
                surf.blit(spin_text, spin_rect)
            elif not self.altering_cave_spinner_stopped:
                wait_text = font.render("...", True, (200, 200, 200))
                wait_rect = wait_text.get_rect(
                    centerx=spinner_x + spinner_width // 2, top=status_y + ui.s(10)
                )
                surf.blit(wait_text, wait_rect)

        except Exception as e:
            print(f"[PCBox] Error drawing spinner: {e}")
            import traceback

            traceback.print_exc()

    def _get_altering_cave_pulse_color(self):
        """Get the current pulse color for Altering Cave Zubat borders."""
        # Oscillate between purple shades
        t = self._altering_cave_pulse_timer / 60.0
        pulse = (math.sin(t * math.pi * 2) + 1) / 2  # 0 to 1

        r = int(100 + pulse * 100)  # 100-200
        g = int(50 + pulse * 50)   # 50-100
        b = int(150 + pulse * 105) # 150-255

        return (r, g, b)

    # ------------------------------------------------------------------ #
    #  Warning message popup                                               #
    # ------------------------------------------------------------------ #

    def _draw_warning_message(self, surf):
        """Draw warning message popup."""
        if not self.warning_message or self.warning_message_timer <= 0:
            self.warning_message = None
            return

        # Decrement timer
        self.warning_message_timer -= 1

        # Calculate fade out for last 30 frames
        alpha = 255
        if self.warning_message_timer < 30:
            alpha = int(255 * (self.warning_message_timer / 30))

        # Warning box dimensions
        warning_width = ui.s(280)
        lines = self.warning_message.split("\n")
        warning_height = ui.s(30) + len(lines) * ui.s(22)
        warning_x = self.width // 2 - warning_width // 2
        warning_y = self.height // 2 - warning_height // 2

        # Create semi-transparent surface
        warning_surf = pygame.Surface((warning_width, warning_height), pygame.SRCALPHA)

        # Draw warning background using theme error colors
        er, eg, eb = (
            ui_colors.COLOR_ERROR[:3]
            if len(ui_colors.COLOR_ERROR) >= 3
            else (255, 80, 80)
        )
        pygame.draw.rect(
            warning_surf,
            (er // 3, eg // 3, eb // 3, alpha),
            (0, 0, warning_width, warning_height),
        )
        pygame.draw.rect(
            warning_surf, (er, eg, eb, alpha), (0, 0, warning_width, warning_height), 3
        )

        try:
            font = scaled_font(12)

            # Draw warning text
            for i, line in enumerate(lines):
                text = font.render(line, True, ui_colors.COLOR_ERROR)
                text.set_alpha(alpha)
                text_rect = text.get_rect(centerx=warning_width // 2, top=ui.s(15) + i * ui.s(22))
                warning_surf.blit(text, text_rect)
        except Exception:
            pass

        surf.blit(warning_surf, (warning_x, warning_y))