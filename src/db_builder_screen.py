#!/usr/bin/env python3

"""
db_builder_screen.py — Database Builder Screen with Sprite Pack Selector.

Layout (left→right):
  [Pack List | Pikachu Preview + Description] [Terminal Log] [Buttons]

The pack list shows all available sprite packs.  Selecting one fetches the
Pikachu preview sprite and shows it live.  "Download Sprites" downloads that
pack's sprites for all 386 Pokémon into the normal/shiny sprite directories,
overwriting any existing sprites.  "Build Pokemon DB" downloads metadata and
uses whatever sprites are already present.
"""

import io
import json
import os
import runpy
import sys
import threading
import traceback

import pygame
import requests

import config
import ui_colors
from config import BASE_DIR, DATA_DIR, FONT_PATH, PACKS_DIR, SPRITES_DIR
from ui_scale import ui, scaled_font
from controller import get_controller
from sprite_pack_selector import (
    MAX_POKEMON,
    PIKACHU_ID,
    SPRITE_PACKS,
    get_sprite_url,
)
# Import sprite pack manager for custom pack support
from sprite_pack_manager import get_sprite_pack_manager

# Where we persist the pack choice so DBbuilder.py can read it
PACK_SELECTION_PATH = os.path.join(DATA_DIR, "sprite_pack_selection.json")

# HTTP session shared by preview fetches
_PREVIEW_SESSION = requests.Session()
_PREVIEW_SESSION.headers.update({"User-Agent": "Sinew-SpritePreview/1.0"})


# ---------------------------------------------------------------------------
# Async Pikachu preview loader — supports static PNG and animated GIF
# ---------------------------------------------------------------------------
class _PreviewLoader:
    """
    Fetches a Pikachu preview sprite in a background thread.
    For GIF URLs it extracts all frames via Pillow and stores them
    as a list of (surface, delay_ms) tuples for animated playback.
    For static images it stores a single-frame list.
    """

    def __init__(self):
        self._frames: list[tuple[pygame.Surface, int]] = []  # (surface, delay_ms)
        self._loading = False
        self._lock = threading.Lock()
        self._url: str | None = None
        # Animation state (driven by draw calls)
        self._frame_idx = 0
        self._frame_timer = 0  # ms accumulated since last frame advance

    def request(self, url: str | None):
        """Start loading a new preview URL (drops previous in-flight request)."""
        with self._lock:
            self._url = url
            self._frames = []
            self._loading = bool(url)
            self._frame_idx = 0
            self._frame_timer = 0
        if url:
            threading.Thread(target=self._fetch, args=(url,), daemon=True).start()

    def _fetch(self, url: str):
        try:
            # Handle file:// URLs for local custom pack sprites
            if url.startswith("file://"):
                file_path = url[7:]  # Remove "file://" prefix
                if not os.path.exists(file_path):
                    with self._lock:
                        if self._url == url:
                            self._loading = False
                    return
                
                # Load from local file
                with open(file_path, 'rb') as f:
                    data = f.read()
            else:
                # Load from URL
                r = _PREVIEW_SESSION.get(url, timeout=8)
                if r.status_code != 200 or not r.content:
                    with self._lock:
                        if self._url == url:
                            self._loading = False
                    return
                data = r.content

            frames: list[tuple[pygame.Surface, int]] = []

            # Try Pillow first so we can handle multi-frame GIFs
            try:
                from PIL import Image as PilImage
                pil_img = PilImage.open(io.BytesIO(data))
                n_frames = getattr(pil_img, "n_frames", 1)

                for f in range(n_frames):
                    pil_img.seek(f)
                    delay = pil_img.info.get("duration", 100)  # ms per frame
                    rgba = pil_img.convert("RGBA")
                    w, h = rgba.size
                    raw = rgba.tobytes()
                    surf = pygame.image.frombuffer(raw, (w, h), "RGBA").convert_alpha()
                    frames.append((surf, max(10, delay)))

            except Exception:
                # Pillow unavailable or failed — fall back to pygame loader (static only)
                surf = pygame.image.load(io.BytesIO(data))
                frames = [(surf, 100)]

            with self._lock:
                if self._url == url:
                    self._frames = frames
                    self._frame_idx = 0
                    self._frame_timer = 0
                    self._loading = False

        except Exception:
            with self._lock:
                if self._url == url:
                    self._loading = False

    def advance(self, dt_ms: int):
        """Call each frame with elapsed ms to advance GIF animation."""
        with self._lock:
            if len(self._frames) <= 1:
                return
            self._frame_timer += dt_ms
            delay = self._frames[self._frame_idx][1]
            if self._frame_timer >= delay:
                self._frame_timer -= delay
                self._frame_idx = (self._frame_idx + 1) % len(self._frames)

    @property
    def surface(self) -> pygame.Surface | None:
        with self._lock:
            if not self._frames:
                return None
            return self._frames[self._frame_idx][0]

    @property
    def loading(self) -> bool:
        with self._lock:
            return self._loading

    @property
    def is_animated(self) -> bool:
        with self._lock:
            return len(self._frames) > 1


# ---------------------------------------------------------------------------
# Sprite pack bulk downloader (runs on a background thread)
# ---------------------------------------------------------------------------
class _SpriteDownloader:
    """Downloads all 386 sprites for a chosen pack into GEN3_NORMAL/SHINY dirs."""

    def __init__(self, pack: dict, log_fn, done_fn):
        self.pack = pack
        self.log = log_fn
        self.done = done_fn
        self.cancel_requested = False
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Sinew-SpriteDownloader/1.0"})

    def _dl(self, url, path) -> bool:
        if not url:
            return False
        try:
            r = self._session.get(url, timeout=10)
            if r.status_code == 200 and r.content:
                with open(path, "wb") as f:
                    f.write(r.content)
                return True
            return False
        except Exception:
            return False

    def run(self):
        # Get pack directories from pack info or sprite pack manager
        pack_id = self.pack.get("id", "unknown")
        
        # For custom packs, use their pack_info
        if self.pack.get("_custom") and self.pack.get("_pack_info"):
            pack_info = self.pack["_pack_info"]
            normal_dir = pack_info.normal_dir
            shiny_dir = pack_info.shiny_dir if pack_info.has_shiny else pack_info.normal_dir
        else:
            # For official packs, construct path from PACKS_DIR
            from config import PACKS_DIR
            pack_dir = os.path.join(PACKS_DIR, pack_id)
            normal_dir = os.path.join(pack_dir, "normal")
            shiny_dir = os.path.join(pack_dir, "shiny")
        
        os.makedirs(normal_dir, exist_ok=True)
        if self.pack.get("has_shiny"):
            os.makedirs(shiny_dir, exist_ok=True)

        self.log(f"Downloading: {self.pack['display_name']}")
        self.log(f"Target: {normal_dir}")
        self.log("")

        ok = 0
        skip = 0
        consecutive_fails = 0
        max_consecutive_fails = 20  # Stop after 20 consecutive 404s (indicates pack ends)

        ext = self.pack.get("file_ext", "png")

        for i in range(1, MAX_POKEMON + 1):
            if self.cancel_requested:
                self.log("Download cancelled.")
                break

            pid_str = f"{i:03d}"
            normal_path = os.path.join(normal_dir, f"{pid_str}.{ext}")
            shiny_path = os.path.join(shiny_dir, f"{pid_str}.{ext}")

            normal_url = get_sprite_url(self.pack, i, shiny=False)
            shiny_url = get_sprite_url(self.pack, i, shiny=True) if self.pack["has_shiny"] else None

            # Skip if already exists (allow resume)
            already_exists = os.path.exists(normal_path)
            if already_exists and os.path.getsize(normal_path) > 0:
                n_ok = True
            else:
                n_ok = self._dl(normal_url, normal_path)
            
            if self.pack["has_shiny"]:
                already_exists_shiny = os.path.exists(shiny_path)
                if already_exists_shiny and os.path.getsize(shiny_path) > 0:
                    s_ok = True
                else:
                    s_ok = self._dl(shiny_url, shiny_path)
            else:
                s_ok = False

            if n_ok or s_ok:
                ok += 1
                consecutive_fails = 0  # Reset counter on success
                parts = []
                if n_ok:
                    parts.append("normal")
                if s_ok:
                    parts.append("shiny")
                self.log(f"[{pid_str}] Downloaded {', '.join(parts)}")
            else:
                skip += 1
                consecutive_fails += 1
                
                # Early termination for Gen 1 packs (151 sprites) or incomplete packs
                if consecutive_fails >= max_consecutive_fails:
                    self.log("")
                    self.log(f"Detected pack boundary at #{i - consecutive_fails}")
                    self.log(f"This appears to be a {i - consecutive_fails}-sprite pack.")
                    self.log("Stopping download (pack complete).")
                    break

            # Brief rate-limit courtesy
            if i % 10 == 0:
                import time; time.sleep(0.05)

        self.log("")
        self.log(f"Done: {ok} downloaded, {skip} skipped.")
        
        # Create pack.json metadata if it doesn't exist
        pack_json_path = os.path.join(os.path.dirname(normal_dir), "pack.json")
        if not os.path.exists(pack_json_path):
            try:
                metadata = {
                    "id": pack_id,
                    "display_name": self.pack.get("display_name", pack_id),
                    "description": self.pack.get("description", ""),
                    "has_shiny": self.pack.get("has_shiny", False),
                    "file_ext": ext
                }
                with open(pack_json_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                self.log(f"Created pack.json")
            except Exception as e:
                self.log(f"Warning: Could not create pack.json: {e}")
        
        # Force sprite pack manager refresh after download
        manager = get_sprite_pack_manager()
        manager.refresh()
        self.log("Sprite pack manager refreshed.")
        
        self.done()


# ---------------------------------------------------------------------------
# Main screen class
# ---------------------------------------------------------------------------
class DBBuilderScreen:
    """Screen for building the Pokemon database with sprite pack selector."""

    def __init__(self, width, height, close_callback=None, get_current_game_callback=None):
        self.width = width
        self.height = height
        self.visible = True
        self.close_callback = close_callback
        self.get_current_game_callback = get_current_game_callback
        self.controller = get_controller()

        # --- Layout constants ---
        self._HEADER_H = 40
        self._FOOTER_H = 20
        self._PADDING = 10
        self._PACK_LIST_W = 140  # Pack list width
        self._BUTTON_W = 130     # Slightly narrower buttons (was 150)
        self._PREVIEW_H = 180    # Preview at top

        # Fonts
        self.font_header   = scaled_font(16)
        self.font_body     = scaled_font(10)
        self.font_small    = scaled_font(8)
        self.font_terminal = scaled_font(10)

        # --- Sprite pack state ---
        # Load packs from sprite pack manager (includes both official and custom)
        pack_manager = get_sprite_pack_manager()
        all_pack_infos = pack_manager.get_all_packs()
        
        # Convert SpritePackInfo objects to dict format expected by UI
        self.packs = []
        for pack_info in all_pack_infos:
            # For official packs, use the original definition from sprite_pack_selector
            if pack_info.official_def:
                pack_dict = pack_info.official_def.copy()
                # Attach pack_info so we can check if it's downloaded
                pack_dict["_pack_info"] = pack_info
                self.packs.append(pack_dict)
            else:
                # For custom packs, create a compatible dict
                sprite_count = pack_info.get_sprite_count()
                is_downloaded = pack_info.is_downloaded()
                
                custom_pack_dict = {
                    "id": pack_info.pack_id,
                    "display_name": pack_info.display_name,
                    "description": pack_info.description,
                    "preview_normal_url": None,  # No URL for custom packs
                    "preview_shiny_url": None,
                    "normal_url_pattern": None,
                    "shiny_url_pattern": None,
                    "has_shiny": pack_info.has_shiny,
                    "file_ext": pack_info.metadata.get("file_ext", "png"),
                    "note": f"⭐ Custom - {sprite_count}/386 sprites {'✓' if is_downloaded else '○'}",
                    "_custom": True,  # Flag for custom pack
                    "_pack_info": pack_info,  # Store full pack info
                }
                self.packs.append(custom_pack_dict)
        
        # Sort: downloaded packs first, then by name
        self.packs.sort(key=lambda p: (
            not (p.get("_pack_info") and p["_pack_info"].is_downloaded()) if p.get("_custom") else False,
            p["display_name"]
        ))
        
        self.selected_pack_idx = self._load_saved_pack_idx()
        self._preview_loader = _PreviewLoader()
        self._preview_shiny_loader = _PreviewLoader()
        self._show_shiny_preview = False

        # --- Terminal output ---
        self.terminal_lines = []
        self.max_lines = 200
        self.scroll_offset = 0
        self._pending_scroll = False

        # --- Build / download state ---
        self.is_building = False
        self.cancel_requested = False
        self.build_thread = None
        self._sprite_downloader: _SpriteDownloader | None = None

        # --- Button state ---
        # Focus areas: 0=pack list, 1=terminal, 2=buttons
        # Navigation: LEFT/RIGHT to move between areas, UP/DOWN within area
        self.focus_area = 0
        self.selected_button = 0
        
        # Game selection popup state
        self.show_game_selector = False
        self.selected_game_idx = 0  # 0=Global, 1+=game list
        
        # Download confirmation popup state
        self.show_download_confirm = False
        self.download_confirm_game_idx = 0  # Which game we're trying to apply to
        self.download_confirm_pack = None  # Pack we're trying to download
        
        # List of known Gen 3 games for the selector
        # These are the games users typically play
        self.available_games = [
            "Ruby", "Sapphire", "Emerald",
            "FireRed", "LeafGreen"
        ]
        
        self.buttons = [
            "Apply Pack To...",   # Opens game selector popup
            "Download Sprites",
            "Build Pokemon DB",
            "Build Wallpapers",
            "Back",
        ]
        
        # Click debouncing
        self._last_click_time = 0
        self._click_debounce_ms = 200
        
        # Animation timing
        self._last_draw_ms = pygame.time.get_ticks()
        
        # Welcome instructions
        self._add_line("=== SPRITE PACK MANAGER ===")
        self._add_line("")
        self._add_line("SELECT A PACK:")
        self._add_line("Green = active  Yellow = dl'd")
        self._add_line("Grey  = not downloaded")
        self._add_line("")
        self._add_line("APPLYING:")
        self._add_line("'Apply Pack To...' sets pack")
        self._add_line("globally or per-game.")
        self._add_line("Global needs 386 sprites.")
        self._add_line("")
        self._add_line("DOWNLOADING:")
        self._add_line("'Download Sprites' fetches")
        self._add_line("all 386 sprites for the")
        self._add_line("selected pack.")
        self._add_line("")
        self._add_line("'Build Pokemon DB' downloads")
        self._add_line("metadata (names, types...)")
        self._add_line("")
        self._add_line("CUSTOM PACKS:")
        self._add_line("Place sprites in:")
        self._add_line("packs/PACKNAME/normal/")
        self._add_line("packs/PACKNAME/shiny/")
        self._add_line("Named 001.png to 386.png")
        self._add_line("(or .gif for animation)")
        self._add_line("")

        # Start terminal at top
        self.scroll_offset = 0
        self._pending_scroll = False

        # Load preview for initial pack
        self._load_preview_for_current_pack()
        
    def _db_exists(self) -> bool:
        """Check if Pokemon DB file exists."""
        db_path = os.path.join(DATA_DIR, "pokemon_db.json")
        return os.path.exists(db_path)
    
    def _wallpapers_exist(self) -> bool:
        """Check if wallpaper directory exists and has image files (png, jpg, gif)."""
        # Import TITLE_SPRITES_DIR from config (data/sprites/title)
        from config import TITLE_SPRITES_DIR
        
        wallpaper_dir = TITLE_SPRITES_DIR
        if not os.path.exists(wallpaper_dir):
            return False
        # Check if there are any image files
        try:
            files = os.listdir(wallpaper_dir)
            # Check for common image formats including GIF
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    filepath = os.path.join(wallpaper_dir, f)
                    if os.path.isfile(filepath):
                        return True
            return False
        except:
            return False

        self._add_line("2. Switch mode (Q/E)")
        self._add_line("3. Click 'Use This Pack'")
        self._add_line("")
        self._add_line("DOWNLOADING:")
        self._add_line("'Download Sprites' fetches all")
        self._add_line("386 Pokemon sprites.")
        self._add_line("")
        self._add_line("'Build Pokemon DB' downloads")
        self._add_line("metadata (names, types, etc.)")
        self._add_line("")

    # ------------------------------------------------------------------
    # Pack persistence
    # ------------------------------------------------------------------
    def _load_saved_pack_idx(self) -> int:
        try:
            if os.path.exists(PACK_SELECTION_PATH):
                with open(PACK_SELECTION_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pack_id = data.get("pack_id", "")
                for i, p in enumerate(self.packs):
                    if p["id"] == pack_id:
                        return i
        except Exception:
            pass
        return 0  # default: gen3_emerald

    def _save_pack_selection(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(PACK_SELECTION_PATH, "w", encoding="utf-8") as f:
                json.dump({"pack_id": self.packs[self.selected_pack_idx]["id"]}, f)
        except Exception as e:
            print(f"[DBBuilder] Could not save pack selection: {e}")

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    def _load_preview_for_current_pack(self):
        pack = self.packs[self.selected_pack_idx]
        
        # Check if this is a custom pack
        if pack.get("_custom"):
            # For custom packs, load preview from local file
            pack_info = pack.get("_pack_info")
            if pack_info:
                sample_path = pack_info.get_sample_sprite_path()
                if sample_path:
                    # Load local file as preview
                    self._preview_loader.request(f"file://{sample_path}")
                    # Custom packs might not have shiny
                    if pack_info.has_shiny:
                        # Try to find shiny sample
                        shiny_sample = sample_path.replace("/normal/", "/shiny/")
                        if os.path.exists(shiny_sample):
                            self._preview_shiny_loader.request(f"file://{shiny_sample}")
                        else:
                            self._preview_shiny_loader.request(None)
                    else:
                        self._preview_shiny_loader.request(None)
                else:
                    # No sample sprite found
                    self._preview_loader.request(None)
                    self._preview_shiny_loader.request(None)
            else:
                self._preview_loader.request(None)
                self._preview_shiny_loader.request(None)
        else:
            # Official pack - use URLs
            self._preview_loader.request(pack.get("preview_normal_url"))
            self._preview_shiny_loader.request(pack.get("preview_shiny_url"))

    # ------------------------------------------------------------------
    # Terminal helpers
    # ------------------------------------------------------------------
    def _add_line(self, text: str):
        max_chars = 36
        while len(text) > max_chars:
            self.terminal_lines.append(text[:max_chars])
            text = text[max_chars:]
        self.terminal_lines.append(text)
        if len(self.terminal_lines) > self.max_lines:
            self.terminal_lines = self.terminal_lines[-self.max_lines:]
        self._pending_scroll = True

    def _scroll_to_bottom(self):
        vis = self._get_visible_line_count()
        self.scroll_offset = max(0, len(self.terminal_lines) - vis)

    def _get_visible_line_count(self) -> int:
        terminal_rect = self._get_terminal_rect()
        return max(1, (terminal_rect.height - 10) // 14)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------
    def _get_left_panel_rect(self) -> pygame.Rect:
        """Pack list (left side, full height)."""
        return pygame.Rect(
            self._PADDING,
            self._HEADER_H + self._PADDING,
            self._PACK_LIST_W,
            self.height - self._HEADER_H - self._FOOTER_H - self._PADDING * 2,
        )

    def _get_preview_rect(self) -> pygame.Rect:
        """Preview panel (top right, above terminal)."""
        x = self._PADDING + self._PACK_LIST_W + self._PADDING
        btn_left = self.width - self._BUTTON_W - self._PADDING
        return pygame.Rect(
            x,
            self._HEADER_H + self._PADDING,
            btn_left - x - self._PADDING,
            self._PREVIEW_H,
        )
    
    def _get_button_rects(self) -> list[pygame.Rect]:
        """Action buttons (right side)."""
        bw = self._BUTTON_W
        bh = 28
        spacing = 8
        bx = self.width - bw - self._PADDING
        
        # Start from top
        start_y = self._HEADER_H + self._PADDING
        
        rects = []
        for i in range(len(self.buttons)):
            by = start_y + i * (bh + spacing)
            rects.append(pygame.Rect(bx, by, bw, bh))
        return rects

    def _get_terminal_rect(self) -> pygame.Rect:
        """Terminal (below preview panel, extends to right edge of buttons)."""
        preview_rect = self._get_preview_rect()
        btn_rects = self._get_button_rects()
        
        # Terminal starts at preview left
        tx = preview_rect.left
        ty = preview_rect.bottom + self._PADDING
        
        # Extend to right edge of buttons (instead of left edge)
        if btn_rects:
            tw = (btn_rects[0].right - tx)
        else:
            tw = self.width - tx - self._PADDING
        
        th = self.height - ty - self._FOOTER_H - self._PADDING
        
        return pygame.Rect(tx, ty, tw, th)

    # ------------------------------------------------------------------
    # Build / download logic
    # ------------------------------------------------------------------
    def _start_sprite_download(self):
        if self.is_building:
            return
        pack = self.packs[self.selected_pack_idx]
        self._save_pack_selection()

        self.is_building = True
        self.cancel_requested = False
        self.terminal_lines = []
        self._add_line(f"Pack: {pack['display_name']}")

        downloader = _SpriteDownloader(
            pack,
            log_fn=self._add_line,
            done_fn=self._on_download_done,
        )
        self._sprite_downloader = downloader
        t = threading.Thread(target=downloader.run, daemon=True)
        t.start()

    def _on_download_done(self):
        self.is_building = False
        self._sprite_downloader = None

    def _start_build(self):
        if self.is_building:
            return
        self._save_pack_selection()
        self.is_building = True
        self.cancel_requested = False
        self.terminal_lines = []
        self._add_line("Starting database build...")
        self._add_line("")
        self.build_thread = threading.Thread(target=self._run_build, daemon=True)
        self.build_thread.start()

    def _run_build(self):
        """Fetch Pokemon metadata from PokeAPI and write to pokemon_db.json."""
        self.is_building = True
        self.cancel_requested = False

        try:
            import json
            import time as _time

            MAX_POKEMON = 386
            DB_PATH = os.path.join(config.DATA_DIR, "pokemon_db.json")
            os.makedirs(config.DATA_DIR, exist_ok=True)

            self._add_line(f"DB: {DB_PATH}")

            session = requests.Session()
            session.headers.update({"User-Agent": "Sinew-DBBuilder/2.0"})

            def _fetch_json(url, retries=3):
                for attempt in range(retries):
                    try:
                        r = session.get(url, timeout=10)
                        if r.status_code == 200:
                            return r.json()
                        if r.status_code == 404:
                            return None
                    except Exception as e:
                        self._add_line(f"[warn] {e}")
                    _time.sleep(0.5 * (attempt + 1))
                return None

            def _english_desc(species_data):
                for entry in species_data.get("flavor_text_entries", []):
                    if entry.get("language", {}).get("name") == "en":
                        text = entry.get("flavor_text", "")
                        return text.replace("\n", " ").replace("\f", " ").strip()
                return None

            def _parse_evo(node):
                results = []
                species = node.get("species", {})
                url = species.get("url", "")
                try:
                    pid = int(url.rstrip("/").split("/")[-1])
                except Exception:
                    pid = None
                results.append({"name": species.get("name"), "species_id": pid})
                evolves_to = node.get("evolves_to") or []
                if evolves_to:
                    branches = [_parse_evo(e) for e in evolves_to]
                    if len(branches) == 1:
                        return [*results, *branches[0][1:]]
                    return [{"base": results[0], "branches": branches}]
                return results

            def _is_complete(entry):
                required = ("id", "name", "types", "stats", "abilities",
                            "height", "weight", "description", "egg_groups")
                return all(entry.get(k) is not None for k in required)

            if os.path.exists(DB_PATH):
                with open(DB_PATH, "r", encoding="utf-8") as fh:
                    pokemon_db = json.load(fh)
                self._add_line(f"Loaded: {len(pokemon_db)} entries")
            else:
                pokemon_db = {}
                self._add_line("Starting fresh DB")

            if "items" not in pokemon_db:
                pokemon_db["items"] = {
                    "pokeball":    "sprites/items/poke-ball.png",
                    "master_ball": "sprites/items/master-ball.png",
                    "egg":         "sprites/items/egg.png",
                }

            updated = skipped = failed = 0
            self._add_line(f"Fetching 1-{MAX_POKEMON}...")

            for i in range(1, MAX_POKEMON + 1):
                if self.cancel_requested:
                    self._add_line("Cancelled.")
                    break

                pid_str = f"{i:03d}"
                existing = pokemon_db.get(pid_str, {})

                if _is_complete(existing):
                    skipped += 1
                    continue

                p_data = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{i}/")
                if not p_data:
                    self._add_line(f"[{pid_str}] FAILED")
                    failed += 1
                    _time.sleep(0.5)
                    continue

                s_data = _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{i}/") or {}

                name = p_data.get("name", str(i)).replace("-", " ").title()
                types = [t["type"]["name"].title()
                         for t in sorted(p_data.get("types", []), key=lambda x: x.get("slot", 0))]
                stats = {s["stat"]["name"]: s["base_stat"] for s in p_data.get("stats", [])}
                abilities = [ab["ability"]["name"].replace("-", " ").title()
                             for ab in p_data.get("abilities", [])]
                egg_groups = [eg["name"].replace("-", " ").title()
                              for eg in s_data.get("egg_groups", [])]
                forms = [f.get("name") for f in p_data.get("forms", [])]
                description = _english_desc(s_data)

                evo_info = None
                evo_url = s_data.get("evolution_chain", {}).get("url")
                if evo_url:
                    evo_data = _fetch_json(evo_url)
                    if evo_data:
                        evo_info = _parse_evo(evo_data.get("chain", {}))

                pokemon_db[pid_str] = {
                    "id": i,
                    "name": name,
                    "types": types,
                    "height": p_data.get("height"),
                    "weight": p_data.get("weight"),
                    "description": description,
                    "abilities": abilities,
                    "egg_groups": egg_groups,
                    "forms": forms,
                    "stats": stats,
                    "evolution_chain": evo_info,
                    "sprites": existing.get("sprites", {}),
                    "games": ["Ruby", "Sapphire", "Emerald", "FireRed", "LeafGreen"],
                }

                self._add_line(f"[{pid_str}] {name}")
                updated += 1

                if updated % 25 == 0:
                    with open(DB_PATH, "w", encoding="utf-8") as fh:
                        json.dump(pokemon_db, fh, indent=2, ensure_ascii=False)
                    self._add_line(f"Checkpoint: {updated} saved")

                _time.sleep(0.15)

            with open(DB_PATH, "w", encoding="utf-8") as fh:
                json.dump(pokemon_db, fh, indent=2, ensure_ascii=False)

            self._add_line(f"Done! +{updated} skip={skipped} fail={failed}")

        except Exception:
            self._add_line(f"Error: {traceback.format_exc()}")
        finally:
            self.is_building = False

    def _start_wallpaper_build(self):
        if self.is_building:
            return
        self.is_building = True
        self.cancel_requested = False
        self.terminal_lines = []
        self._add_line("Starting wallpaper generation...")
        self._add_line("")
        self.build_thread = threading.Thread(
            target=self._run_wallpaper_build, daemon=True
        )
        self.build_thread.start()

    def _run_wallpaper_build(self):
        def execute():
            self.is_building = True
            self.cancel_requested = False
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            try:
                bundle_dir = getattr(sys, "_MEIPASS", config.BASE_DIR)
                if bundle_dir not in sys.path:
                    sys.path.insert(0, bundle_dir)
                script_path = os.path.join(config.BASE_DIR, "wallgen.py")

                class UILogger:
                    def __init__(self, func):
                        self.func = func
                    def write(self, s):
                        if s.strip():
                            self.func(s.strip())
                    def flush(self):
                        pass

                sys.stdout = UILogger(self._add_line)
                sys.stderr = sys.stdout
                self._add_line("Starting wallpaper generation...")

                custom_globals = globals().copy()
                custom_globals.update(
                    {"ui_instance": self, "config": config, "__name__": "__main__"}
                )
                runpy.run_path(
                    script_path, init_globals=custom_globals, run_name="__main__"
                )
                self._add_line("=" * 32)
                self._add_line("Wallpapers generated!")
            except Exception as e:
                self._add_line(f"ERROR: {e}")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                self.is_building = False
                self.build_thread = None

        self.build_thread = threading.Thread(target=execute, daemon=True)
        self.build_thread.start()

    def _cancel_build(self):
        if self.is_building:
            self._add_line("Cancelling...")
            self.is_building = False
            self.cancel_requested = True
            if self._sprite_downloader:
                self._sprite_downloader.cancel_requested = True

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------
    def _activate_button(self):
        """Activate whichever button is selected."""
        if self.focus_area == 0:
            # Pack list — no action on ENTER, just stay here
            return
        
        elif self.focus_area == 1:
            # Terminal — no action on ENTER, just stay here
            return
        
        # Focus area 2 - buttons
        idx = self.selected_button
        if self.is_building:
            self._cancel_build()
            return

        if idx == 0:
            # "Apply Pack To..." button - open game selector popup
            self.show_game_selector = True
            self.selected_game_idx = 0  # Start on Global
        elif idx == 1:
            self._start_sprite_download()
        elif idx == 2:
            self._start_build()
        elif idx == 3:
            self._start_wallpaper_build()
        else:
            self._close()
    
    def _toggle_pack_for_game(self):
        """Toggle the selected pack for the selected game in the popup.
        Called when user presses A on a game checkbox."""
        pack = self.packs[self.selected_pack_idx]
        pack_id = pack["id"]
        
        # Check if pack is downloaded
        pack_info = pack.get("_pack_info")
        is_downloaded = pack_info.is_downloaded() if pack_info else False
        
        from sprite_pack_manager import get_sprite_pack_manager
        manager = get_sprite_pack_manager()
        
        if self.selected_game_idx == 0:
            # ===== GLOBAL PACK =====
            if not is_downloaded:
                # Pack not downloaded - show download confirmation popup
                self.download_confirm_pack = pack
                self.download_confirm_game_idx = 0  # Global
                self.show_download_confirm = True
                return
            
            # Pack is downloaded - check it has full 386 sprites before setting as global
            sprite_count = pack_info.get_sprite_count() if pack_info else 0
            if sprite_count < 386:
                self._add_line("")
                self._add_line(f"Cannot set as global:")
                self._add_line(f"  Only {sprite_count}/386 sprites")
                self._add_line(f"  Use a full Gen 3 pack")
                self._add_line(f"  for global default.")
                self._add_line("")
                self.show_game_selector = False
                return

            # Pack is downloaded and complete - apply it
            old_global = manager.preferences.get("global_pack", "gen3_emerald")
            manager.set_global_pack(pack_id)
            self._save_pack_selection()
            
            self._add_line("")
            self._add_line("✓ PACK DOWNLOADED")
            self._add_line("")
            self._add_line(f"✓ Applied '{pack['display_name']}'")
            self._add_line("  as GLOBAL default")
            if old_global != pack_id:
                self._add_line(f"  (was: {old_global})")
            self._add_line("")
            self._scroll_to_bottom()
            
            # Close popup after success
            self.show_game_selector = False
            
        else:
            # ===== PER-GAME PACK =====
            game_name = self.available_games[self.selected_game_idx - 1]
            per_game = manager.preferences.get("per_game", {})
            current_pack = per_game.get(game_name)
            
            if current_pack == pack_id:
                # Already assigned - clear override
                manager.clear_game_pack(game_name)
                self._save_pack_selection()
                
                global_pack = manager.preferences.get("global_pack", "gen3_emerald")
                self._add_line("")
                self._add_line(f"✓ Cleared {game_name} override")
                self._add_line(f"  Now using global: {global_pack}")
                self._add_line("")
                self._scroll_to_bottom()
                
                # Close popup
                self.show_game_selector = False
                
            else:
                # Assigning new pack
                if not is_downloaded:
                    # Pack not downloaded - show download confirmation popup
                    self.download_confirm_pack = pack
                    self.download_confirm_game_idx = self.selected_game_idx  # Specific game
                    self.show_download_confirm = True
                    return
                
                # Pack is downloaded - apply it
                old_pack = current_pack or manager.preferences.get("global_pack", "gen3_emerald")
                manager.set_game_pack(game_name, pack_id)
                self._save_pack_selection()
                
                self._add_line("")
                self._add_line("✓ PACK DOWNLOADED")
                self._add_line("")
                self._add_line(f"✓ Applied '{pack['display_name']}'")
                self._add_line(f"  to {game_name}")
                if old_pack != pack_id:
                    self._add_line(f"  (was: {old_pack})")
                self._add_line("")
                self._scroll_to_bottom()
                
                # Close popup after success
                self.show_game_selector = False
    
    def _confirm_download_and_apply(self):
        """Download the pack and apply it to the selected game after download completes."""
        # Close download confirmation popup
        self.show_download_confirm = False
        
        # Close game selector popup
        self.show_game_selector = False
        
        # Start downloading the pack
        pack = self.download_confirm_pack
        self._save_pack_selection()
        
        self.is_building = True
        self.cancel_requested = False
        self.terminal_lines = []
        self._add_line(f"Pack: {pack['display_name']}")
        
        # Store which game to apply to after download
        pending_game_idx = self.download_confirm_game_idx
        
        def on_download_complete():
            """Called when download finishes successfully."""
            self.is_building = False
            
            # Now apply the pack to the game
            from sprite_pack_manager import get_sprite_pack_manager
            manager = get_sprite_pack_manager()
            pack_id = pack["id"]
            
            if pending_game_idx == 0:
                # Global
                old_global = manager.preferences.get("global_pack", "gen3_emerald")
                manager.set_global_pack(pack_id)
                self._save_pack_selection()
                
                self._add_line("")
                self._add_line("=" * 32)
                self._add_line("✓ PACK APPLIED")
                self._add_line("=" * 32)
                self._add_line("")
                self._add_line(f"Set '{pack['display_name']}'")
                self._add_line("as GLOBAL default")
                if old_global != pack_id:
                    self._add_line(f"(was: {old_global})")
                self._add_line("")
            else:
                # Specific game
                game_name = self.available_games[pending_game_idx - 1]
                per_game = manager.preferences.get("per_game", {})
                old_pack = per_game.get(game_name) or manager.preferences.get("global_pack", "gen3_emerald")
                
                manager.set_game_pack(game_name, pack_id)
                self._save_pack_selection()
                
                self._add_line("")
                self._add_line("=" * 32)
                self._add_line("✓ PACK APPLIED")
                self._add_line("=" * 32)
                self._add_line("")
                self._add_line(f"Set '{pack['display_name']}'")
                self._add_line(f"for {game_name}")
                if old_pack != pack_id:
                    self._add_line(f"(was: {old_pack})")
                self._add_line("")
            
            self._scroll_to_bottom()
        
        downloader = _SpriteDownloader(
            pack,
            log_fn=self._add_line,
            done_fn=on_download_complete
        )
        self._sprite_downloader = downloader
        
        # Start downloader in a thread (it's not a Thread subclass)
        t = threading.Thread(target=downloader.run, daemon=True)
        t.start()

    def handle_events(self, events):
        current_time = pygame.time.get_ticks()

        for event in events:
            if event.type == pygame.KEYDOWN:
                key = event.key
                
                # Download confirmation popup has highest priority
                if self.show_download_confirm:
                    if key == pygame.K_RETURN:
                        # Yes - download and apply
                        self._confirm_download_and_apply()
                    elif key == pygame.K_ESCAPE or key == pygame.K_BACKSPACE:
                        # No - cancel
                        self.show_download_confirm = False
                    continue
                
                # If game selector is showing, handle its input
                if self.show_game_selector:
                    if key == pygame.K_ESCAPE or key == pygame.K_BACKSPACE:
                        self.show_game_selector = False
                    elif key in (pygame.K_UP, pygame.K_w):
                        self.selected_game_idx = max(0, self.selected_game_idx - 1)
                    elif key in (pygame.K_DOWN, pygame.K_s):
                        max_idx = len(self.available_games)  # 0=Global, then games
                        self.selected_game_idx = min(max_idx, self.selected_game_idx + 1)
                    elif key == pygame.K_RETURN:
                        # Toggle pack for selected game
                        self._toggle_pack_for_game()
                    continue  # Don't process other inputs when popup is showing
                
                # Normal input handling
                if key == pygame.K_ESCAPE:
                    if self.is_building:
                        self._cancel_build()
                    else:
                        self._close()

                elif key == pygame.K_TAB:
                    # Cycle through focus areas: 0=pack list, 1=terminal, 2=buttons
                    self.focus_area = (self.focus_area + 1) % 3

                elif key in (pygame.K_UP, pygame.K_w):
                    if self.focus_area == 0:
                        # Pack list navigation
                        old = self.selected_pack_idx
                        self.selected_pack_idx = max(0, self.selected_pack_idx - 1)
                        if self.selected_pack_idx != old:
                            self._load_preview_for_current_pack()
                    elif self.focus_area == 1:
                        # Terminal - scroll up
                        self.scroll_offset = max(0, self.scroll_offset - 3)
                    else:
                        # Buttons - navigate up
                        self.selected_button = max(0, self.selected_button - 1)

                elif key in (pygame.K_DOWN, pygame.K_s):
                    if self.focus_area == 0:
                        # Pack list navigation
                        old = self.selected_pack_idx
                        self.selected_pack_idx = min(len(self.packs) - 1, self.selected_pack_idx + 1)
                        if self.selected_pack_idx != old:
                            self._load_preview_for_current_pack()
                    elif self.focus_area == 1:
                        # Terminal - scroll down
                        max_scroll = max(0, len(self.terminal_lines) - self._get_visible_line_count())
                        self.scroll_offset = min(max_scroll, self.scroll_offset + 3)
                    else:
                        # Buttons - navigate down
                        self.selected_button = min(len(self.buttons) - 1, self.selected_button + 1)

                elif key in (pygame.K_LEFT, pygame.K_a):
                    # Move focus area left: Buttons → Terminal → Pack List
                    self.focus_area = max(0, self.focus_area - 1)

                elif key in (pygame.K_RIGHT, pygame.K_d):
                    # Move focus area right: Pack List → Terminal → Buttons
                    self.focus_area = min(2, self.focus_area + 1)

                elif key == pygame.K_RETURN:
                    if current_time - self._last_click_time > self._click_debounce_ms:
                        self._last_click_time = current_time
                        # If on pack list, open game selector
                        if self.focus_area == 0:
                            self.show_game_selector = True
                            self.selected_game_idx = 0
                        else:
                            self._activate_button()

                elif key == pygame.K_BACKSPACE:
                    # Toggle shiny preview (SELECT button)
                    self._show_shiny_preview = not self._show_shiny_preview

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if current_time - self._last_click_time < self._click_debounce_ms:
                    continue
                self._last_click_time = current_time
                pos = event.pos

                # Check pack list clicks
                left_rect = self._get_left_panel_rect()
                if left_rect.collidepoint(pos):
                    self.focus_area = 0
                    item_h = 20
                    rel_y = pos[1] - left_rect.top - 18  # Account for header
                    clicked_idx = rel_y // item_h
                    
                    # Account for scroll position
                    max_items = (left_rect.height - 18) // item_h
                    start = self.selected_pack_idx
                    if start + max_items > len(self.packs):
                        start = max(0, len(self.packs) - max_items)
                    
                    actual_idx = start + clicked_idx
                    
                    if 0 <= actual_idx < len(self.packs):
                        if self.selected_pack_idx == actual_idx:
                            # Clicked same pack - open game selector
                            self.show_game_selector = True
                            self.selected_game_idx = 0
                        else:
                            # Different pack - select it and load preview
                            self.selected_pack_idx = actual_idx
                            self._load_preview_for_current_pack()

                # Check button clicks
                button_rects = self._get_button_rects()
                for i, rect in enumerate(button_rects):
                    if rect.collidepoint(pos):
                        self.focus_area = 1
                        self.selected_button = i
                        self._activate_button()
                        break

                # Toggle shiny if preview area clicked
                prev_rect = self._get_preview_rect()
                preview_img_rect = pygame.Rect(
                    prev_rect.left + 5, prev_rect.top + 5,
                    prev_rect.width - 10, 90
                )
                if preview_img_rect.collidepoint(pos):
                    self._show_shiny_preview = not self._show_shiny_preview

            elif event.type == pygame.MOUSEWHEEL:
                # Scroll terminal with mouse wheel
                max_scroll = max(0, len(self.terminal_lines) - self._get_visible_line_count())
                self.scroll_offset = max(0, min(max_scroll, self.scroll_offset - event.y * 2))

    def handle_controller(self, ctrl):
        if not ctrl:
            return
        current_time = pygame.time.get_ticks()
        
        # Download confirmation popup has highest priority
        if self.show_download_confirm:
            if ctrl.is_button_just_pressed("A"):
                ctrl.consume_button("A")
                # Yes - download and apply
                self._confirm_download_and_apply()
                return
            elif ctrl.is_button_just_pressed("B"):
                ctrl.consume_button("B")
                # No - cancel
                self.show_download_confirm = False
                return

        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            if self.show_game_selector:
                # Navigate in game selector popup
                self.selected_game_idx = max(0, self.selected_game_idx - 1)
            elif self.focus_area == 0:
                # Pack list navigation
                old = self.selected_pack_idx
                self.selected_pack_idx = max(0, self.selected_pack_idx - 1)
                if self.selected_pack_idx != old:
                    self._load_preview_for_current_pack()
            elif self.focus_area == 1:
                # Terminal - scroll up
                self.scroll_offset = max(0, self.scroll_offset - 3)
            else:
                # Buttons area - navigate up
                self.selected_button = max(0, self.selected_button - 1)

        elif ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            if self.show_game_selector:
                # Navigate in game selector popup
                max_idx = len(self.available_games)
                self.selected_game_idx = min(max_idx, self.selected_game_idx + 1)
            elif self.focus_area == 0:
                # Pack list navigation
                old = self.selected_pack_idx
                self.selected_pack_idx = min(len(self.packs) - 1, self.selected_pack_idx + 1)
                if self.selected_pack_idx != old:
                    self._load_preview_for_current_pack()
            elif self.focus_area == 1:
                # Terminal - scroll down
                max_scroll = max(0, len(self.terminal_lines) - self._get_visible_line_count())
                self.scroll_offset = min(max_scroll, self.scroll_offset + 3)
            else:
                # Buttons area - navigate down
                self.selected_button = min(len(self.buttons) - 1, self.selected_button + 1)

        elif ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_dpad("left")
            # Move focus left: Buttons → Terminal → Pack List
            self.focus_area = max(0, self.focus_area - 1)

        elif ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("right")
            # Move focus right: Pack List → Terminal → Buttons
            self.focus_area = min(2, self.focus_area + 1)

        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            if self.show_game_selector:
                # Toggle pack for selected game
                self._toggle_pack_for_game()
            elif current_time - self._last_click_time > self._click_debounce_ms:
                self._last_click_time = current_time
                # If on pack list, open game selector
                if self.focus_area == 0:
                    self.show_game_selector = True
                    self.selected_game_idx = 0
                else:
                    self._activate_button()

        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            if self.show_game_selector:
                # Close popup
                self.show_game_selector = False
            elif self.is_building:
                self._cancel_build()
            else:
                self._close()

        if ctrl.is_button_just_pressed("SELECT"):
            ctrl.consume_button("SELECT")
            self._show_shiny_preview = not self._show_shiny_preview

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        # Flush pending scroll from background thread
        if getattr(self, '_pending_scroll', False):
            self._pending_scroll = False
            self._scroll_to_bottom()

        # Advance GIF animation frames based on elapsed time
        now = pygame.time.get_ticks()
        dt = now - getattr(self, "_last_draw_ms", now)
        self._last_draw_ms = now
        self._preview_loader.advance(dt)
        self._preview_shiny_loader.advance(dt)

        surface.fill(ui_colors.COLOR_BG)
        self._draw_header(surface)
        self._draw_pack_list(surface)
        self._draw_preview_panel(surface)
        self._draw_terminal(surface)
        self._draw_buttons(surface)
        self._draw_footer(surface)
        
        # Draw game selector popup on top if showing
        if self.show_game_selector:
            self._draw_game_selector(surface)
        
        # Draw download confirmation popup on top of everything
        if self.show_download_confirm:
            self._draw_download_confirm(surface)

    def _draw_header(self, surface: pygame.Surface):
        header_rect = pygame.Rect(0, 0, self.width, self._HEADER_H)
        pygame.draw.rect(surface, ui_colors.COLOR_HEADER, header_rect)
        
        # Title
        title = self.font_header.render("Sprite Pack Manager", True, ui_colors.COLOR_TEXT)
        surface.blit(title, title.get_rect(midleft=(15, 20)))

        # Show working indicator
        if self.is_building:
            dots = "." * ((pygame.time.get_ticks() // 500) % 4)
            status = self.font_body.render(f"Working{dots}", True, ui_colors.COLOR_HIGHLIGHT)
            surface.blit(status, status.get_rect(midright=(self.width - 15, 20)))

    def _draw_game_selector(self, surface: pygame.Surface):
        """Draw the game selector popup for choosing which game(s) to apply the pack to."""
        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        
        # Popup panel
        panel_w = 300
        panel_h = min(400, self.height - 80)
        panel_x = (self.width - panel_w) // 2
        panel_y = (self.height - panel_h) // 2
        
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        
        # Panel background
        pygame.draw.rect(surface, ui_colors.COLOR_BG, panel_rect)
        pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, panel_rect, 3)
        
        # Title
        pack = self.packs[self.selected_pack_idx]
        title = self.font_header.render("Apply Pack To:", True, ui_colors.COLOR_TEXT)
        surface.blit(title, (panel_x + 10, panel_y + 10))
        
        # Pack name
        pack_name = self.font_body.render(pack["display_name"], True, ui_colors.COLOR_HIGHLIGHT)
        surface.blit(pack_name, (panel_x + 10, panel_y + 35))
        
        # Get sprite pack manager to check current assignments
        from sprite_pack_manager import get_sprite_pack_manager
        manager = get_sprite_pack_manager()
        current_global = manager.preferences.get("global_pack", "gen3_emerald")
        per_game = manager.preferences.get("per_game", {})
        pack_id = pack["id"]
        
        # Draw game list
        y = panel_y + 70
        item_h = 32
        
        # Global option
        is_selected = (self.selected_game_idx == 0)
        is_active = (current_global == pack_id)
        
        item_rect = pygame.Rect(panel_x + 10, y, panel_w - 20, item_h)
        
        if is_selected:
            pygame.draw.rect(surface, ui_colors.COLOR_BUTTON_HOVER, item_rect)
            pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, item_rect, 2)
        
        # Draw checkbox
        check_box = pygame.Rect(panel_x + 15, y + 8, 16, 16)
        pygame.draw.rect(surface, ui_colors.COLOR_BORDER, check_box, 2)
        if is_active:
            # Draw checkmark
            pygame.draw.line(surface, (100, 255, 100), (check_box.left + 3, check_box.centery),
                           (check_box.centerx, check_box.bottom - 4), 3)
            pygame.draw.line(surface, (100, 255, 100), (check_box.centerx, check_box.bottom - 4),
                           (check_box.right - 3, check_box.top + 3), 3)
        
        text = self.font_body.render("Global (All Games)", True, ui_colors.COLOR_TEXT)
        surface.blit(text, (panel_x + 40, y + 8))
        
        y += item_h
        
        # Individual games
        for i, game in enumerate(self.available_games):
            is_selected = (self.selected_game_idx == i + 1)
            is_active = (per_game.get(game) == pack_id)
            
            item_rect = pygame.Rect(panel_x + 10, y, panel_w - 20, item_h)
            
            if is_selected:
                pygame.draw.rect(surface, ui_colors.COLOR_BUTTON_HOVER, item_rect)
                pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, item_rect, 2)
            
            # Draw checkbox
            check_box = pygame.Rect(panel_x + 15, y + 8, 16, 16)
            pygame.draw.rect(surface, ui_colors.COLOR_BORDER, check_box, 2)
            if is_active:
                # Draw checkmark
                pygame.draw.line(surface, (100, 255, 100), (check_box.left + 3, check_box.centery),
                               (check_box.centerx, check_box.bottom - 4), 3)
                pygame.draw.line(surface, (100, 255, 100), (check_box.centerx, check_box.bottom - 4),
                               (check_box.right - 3, check_box.top + 3), 3)
            
            text = self.font_body.render(game, True, ui_colors.COLOR_TEXT)
            surface.blit(text, (panel_x + 40, y + 8))
            
            y += item_h
        
        # Instructions
        inst_y = panel_y + panel_h - 50
        inst1 = self.font_small.render("Up/Down: Select   A: Toggle   B: Close", True, ui_colors.COLOR_TEXT)
        surface.blit(inst1, inst1.get_rect(center=(panel_x + panel_w // 2, inst_y)))
        
        inst2 = self.font_small.render("Each game can only have one pack", True, (150, 150, 150))
        surface.blit(inst2, inst2.get_rect(center=(panel_x + panel_w // 2, inst_y + 15)))
    
    def _draw_download_confirm(self, surface: pygame.Surface):
        """Draw download confirmation popup."""
        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Popup panel (smaller than game selector)
        panel_w = 280
        panel_h = 200
        panel_x = (self.width - panel_w) // 2
        panel_y = (self.height - panel_h) // 2
        
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        
        # Panel background
        pygame.draw.rect(surface, ui_colors.COLOR_BG, panel_rect)
        pygame.draw.rect(surface, ui_colors.COLOR_ERROR, panel_rect, 3)
        
        # Warning icon/title
        title = self.font_header.render("Pack Not Downloaded", True, ui_colors.COLOR_ERROR)
        surface.blit(title, title.get_rect(centerx=panel_x + panel_w // 2, top=panel_y + 15))
        
        # Pack name
        if self.download_confirm_pack:
            pack_name = self.font_body.render(f"'{self.download_confirm_pack['display_name']}'", True, ui_colors.COLOR_TEXT)
            surface.blit(pack_name, pack_name.get_rect(centerx=panel_x + panel_w // 2, top=panel_y + 45))
        
        # Message
        msg1 = self.font_small.render("This pack needs to be", True, ui_colors.COLOR_TEXT)
        msg2 = self.font_small.render("downloaded before use.", True, ui_colors.COLOR_TEXT)
        surface.blit(msg1, msg1.get_rect(centerx=panel_x + panel_w // 2, top=panel_y + 70))
        surface.blit(msg2, msg2.get_rect(centerx=panel_x + panel_w // 2, top=panel_y + 85))
        
        # Question
        question = self.font_body.render("Download now?", True, ui_colors.COLOR_HIGHLIGHT)
        surface.blit(question, question.get_rect(centerx=panel_x + panel_w // 2, top=panel_y + 110))
        
        # Buttons
        btn_y = panel_y + 140
        btn_w = 100
        btn_h = 30
        btn_spacing = 15
        
        # Yes button (left)
        yes_rect = pygame.Rect(panel_x + 25, btn_y, btn_w, btn_h)
        pygame.draw.rect(surface, ui_colors.COLOR_SUCCESS, yes_rect)
        pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, yes_rect, 2)
        yes_text = self.font_body.render("Yes (A)", True, ui_colors.COLOR_TEXT)
        surface.blit(yes_text, yes_text.get_rect(center=yes_rect.center))
        
        # No button (right)
        no_rect = pygame.Rect(panel_x + panel_w - 125, btn_y, btn_w, btn_h)
        pygame.draw.rect(surface, ui_colors.COLOR_BUTTON, no_rect)
        pygame.draw.rect(surface, ui_colors.COLOR_BORDER, no_rect, 2)
        no_text = self.font_body.render("No (B)", True, ui_colors.COLOR_TEXT)
        surface.blit(no_text, no_text.get_rect(center=no_rect.center))

    def _draw_pack_list(self, surface: pygame.Surface):
        rect = self._get_left_panel_rect()

        # Background
        pygame.draw.rect(surface, (20, 20, 30), rect)
        border_color = ui_colors.COLOR_HIGHLIGHT if self.focus_area == 0 else ui_colors.COLOR_BORDER
        pygame.draw.rect(surface, border_color, rect, 2)

        # Header label
        lbl = self.font_small.render("SPRITE PACK", True, (120, 120, 160))
        surface.blit(lbl, (rect.left + 5, rect.top + 3))

        item_h = 20  # Increased height to prevent text cutoff
        y = rect.top + 18
        max_items = (rect.height - 18) // item_h

        # Scroll to keep selected visible - selected item should appear at top when possible
        start = self.selected_pack_idx
        # But if near the end, show as many items as possible
        if start + max_items > len(self.packs):
            start = max(0, len(self.packs) - max_items)
        
        # Get sprite pack manager for status checking
        from sprite_pack_manager import get_sprite_pack_manager
        manager = get_sprite_pack_manager()
        current_global = manager.preferences.get("global_pack", "gen3_emerald")
        per_game = manager.preferences.get("per_game", {})

        for i, pack in enumerate(self.packs[start: start + max_items]):
            real_idx = start + i
            # Highlight box with downward offset for proper text alignment
            item_rect = pygame.Rect(rect.left + 2, y + 7, rect.width - 4, item_h - 2)

            # Determine pack status
            pack_id = pack["id"]
            is_selected = (real_idx == self.selected_pack_idx)
            
            # Check if pack is downloaded
            pack_info = pack.get("_pack_info")
            is_downloaded = pack_info.is_downloaded() if pack_info else False
            
            # Check if pack is active (global OR for any game)
            is_active = (current_global == pack_id) or (pack_id in per_game.values())

            # Draw highlight box for selected item
            if is_selected:
                bg = ui_colors.COLOR_BUTTON_HOVER if self.focus_area == 0 else ui_colors.COLOR_BUTTON
                pygame.draw.rect(surface, bg, item_rect)
                pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, item_rect, 1)

            # Determine text color based on status
            if is_active:
                col = (100, 255, 100)  # Green for active
            elif is_downloaded:
                col = (255, 255, 100)  # Yellow for downloaded
            else:
                col = (128, 128, 128)  # Grey for not downloaded

            # Override with highlight color if selected
            if is_selected:
                col = ui_colors.COLOR_HIGHLIGHT

            name = pack["display_name"]
            # Truncate if needed
            while self.font_small.size(name)[0] > rect.width - 12 and len(name) > 4:
                name = name[:-1]
            txt = self.font_small.render(name, True, col)
            surface.blit(txt, (rect.left + 5, y + 6))
            y += item_h

    def _draw_preview_panel(self, surface: pygame.Surface):
        rect = self._get_preview_rect()
        pygame.draw.rect(surface, (20, 20, 30), rect)
        pygame.draw.rect(surface, ui_colors.COLOR_BORDER, rect, 2)

        pack = self.packs[self.selected_pack_idx]

        # --- Pikachu preview image ---
        preview_area = pygame.Rect(rect.left + 4, rect.top + 4, rect.width - 8, 88)
        pygame.draw.rect(surface, (12, 12, 20), preview_area)
        pygame.draw.rect(surface, (40, 40, 60), preview_area, 1)

        loader = self._preview_shiny_loader if self._show_shiny_preview else self._preview_loader
        sprite = loader.surface
        loading = loader.loading

        if sprite:
            # Scale to fit preview area preserving aspect ratio
            sw, sh = sprite.get_size()
            scale = min((preview_area.width - 8) / max(sw, 1), (preview_area.height - 8) / max(sh, 1))
            nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
            scaled = pygame.transform.scale(sprite, (nw, nh))
            px = preview_area.left + (preview_area.width - nw) // 2
            py = preview_area.top + (preview_area.height - nh) // 2
            surface.blit(scaled, (px, py))
        elif loading:
            dots = "." * ((pygame.time.get_ticks() // 400) % 4)
            lbl = self.font_small.render(f"Loading{dots}", True, (100, 100, 140))
            surface.blit(lbl, lbl.get_rect(center=preview_area.center))
        else:
            lbl = self.font_small.render("No preview", True, (80, 80, 100))
            surface.blit(lbl, lbl.get_rect(center=preview_area.center))

        # Shiny toggle label + animated indicator
        shiny_txt = "Shiny" if self._show_shiny_preview else "Normal"
        anim_tag = " ~GIF" if loader.is_animated else ""
        shiny_lbl = self.font_small.render(f"[SELECT]{shiny_txt}{anim_tag}", True, (140, 140, 180))
        surface.blit(shiny_lbl, (preview_area.left + 2, preview_area.bottom + 2))
        
        # Check if this pack is active (global or per-game)
        from sprite_pack_manager import get_sprite_pack_manager
        manager = get_sprite_pack_manager()
        current_global = manager.preferences.get("global_pack", "gen3_emerald")
        per_game = manager.preferences.get("per_game", {})
        pack_id = pack["id"]
        
        is_global = (current_global == pack_id)
        active_games = [game for game, pid in per_game.items() if pid == pack_id]
        
        # ACTIVE badge: top-left of preview area - shows ACTIVE + games below
        if is_global or active_games:
            badge_x = preview_area.left + 3
            badge_y = preview_area.top + 3
            # First line: ACTIVE
            active_surf = self.font_small.render("ACTIVE", True, (100, 255, 100))
            active_w = active_surf.get_width() + 6
            active_h = active_surf.get_height() + 2
            active_bg = pygame.Rect(badge_x, badge_y, active_w, active_h)
            pygame.draw.rect(surface, (0, 80, 0), active_bg, border_radius=3)
            pygame.draw.rect(surface, (100, 255, 100), active_bg, 1, border_radius=3)
            surface.blit(active_surf, (badge_x + 3, badge_y + 1))
            # Second line: which games
            if is_global and not active_games:
                scope_text = "Global"
            elif is_global:
                scope_text = "Global"
            else:
                scope_text = ", ".join(active_games[:2])
                if len(active_games) > 2:
                    scope_text += "..."
            scope_surf = self.font_small.render(scope_text, True, (80, 200, 80))
            surface.blit(scope_surf, (badge_x + 2, badge_y + active_h + 2))

        # DOWNLOADED badge: top-right of the text box (below preview_area)
        pack_info_obj = pack.get("_pack_info")
        if pack_info_obj and pack_info_obj.is_downloaded():
            sprite_count = pack_info_obj.get_sprite_count()
            dl_text = f"DL {sprite_count}/386"
            dl_surf = self.font_small.render(dl_text, True, (255, 220, 60))
            dl_x = rect.right - dl_surf.get_width() - 4
            dl_y = preview_area.bottom + 2
            surface.blit(dl_surf, (dl_x, dl_y))

        # Pack name (bold-ish via repeated blit)
        y = preview_area.bottom + 14
        name_words = pack["display_name"].split(" ")
        line = ""
        for word in name_words:
            test = (line + " " + word).strip()
            if self.font_small.size(test)[0] <= rect.width - 10:
                line = test
            else:
                lbl = self.font_small.render(line, True, ui_colors.COLOR_HIGHLIGHT)
                surface.blit(lbl, (rect.left + 5, y))
                y += 11
                line = word
        if line:
            lbl = self.font_small.render(line, True, ui_colors.COLOR_HIGHLIGHT)
            surface.blit(lbl, (rect.left + 5, y))
            y += 13

        # Description (word-wrap)
        desc = pack.get("description", "")
        desc_words = desc.split()
        line = ""
        for word in desc_words:
            test = (line + " " + word).strip()
            if self.font_small.size(test)[0] <= rect.width - 10:
                line = test
            else:
                lbl = self.font_small.render(line, True, (160, 160, 190))
                surface.blit(lbl, (rect.left + 5, y))
                y += 11
                line = word
            if y > rect.bottom - 12:
                break
        if line and y <= rect.bottom - 12:
            lbl = self.font_small.render(line, True, (160, 160, 190))
            surface.blit(lbl, (rect.left + 5, y))

    def _draw_terminal(self, surface: pygame.Surface):
        rect = self._get_terminal_rect()
        if rect.width < 10:
            return

        pygame.draw.rect(surface, (20, 20, 30), rect)
        # Highlight border if focused
        border_color = ui_colors.COLOR_HIGHLIGHT if self.focus_area == 1 else ui_colors.COLOR_BORDER
        pygame.draw.rect(surface, border_color, rect, 2)

        visible = self._get_visible_line_count()
        y = rect.top + 5
        lh = 14

        for i in range(self.scroll_offset, min(self.scroll_offset + visible, len(self.terminal_lines))):
            line = self.terminal_lines[i]
            if "ERROR" in line or "FAILED" in line or "Error" in line or "Traceback" in line:
                col = ui_colors.COLOR_ERROR
            elif line.startswith("[") and "]" in line:
                col = ui_colors.COLOR_SUCCESS
            elif line.startswith("[OK]"):
                col = ui_colors.COLOR_SUCCESS
            elif "=" in line and len(line) > 20:
                col = ui_colors.COLOR_HIGHLIGHT
            elif line.startswith("WARNING"):
                col = (255, 200, 100)
            else:
                col = ui_colors.COLOR_TEXT

            txt = self.font_terminal.render(line, True, col)
            surface.blit(txt, (rect.left + 6, y))
            y += lh

        # Scrollbar
        if len(self.terminal_lines) > visible:
            sb_h = rect.height - 10
            thumb_h = max(16, sb_h * visible // len(self.terminal_lines))
            max_scroll = len(self.terminal_lines) - visible
            thumb_y = rect.top + 5
            if max_scroll > 0:
                thumb_y += int((sb_h - thumb_h) * self.scroll_offset / max_scroll)
            sbx = rect.right - 10
            pygame.draw.rect(surface, (40, 40, 50), (sbx, rect.top + 5, 6, sb_h))
            pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, (sbx, thumb_y, 6, thumb_h))

    def _draw_buttons(self, surface: pygame.Surface):
        rects = self._get_button_rects()
        for i, btn_text in enumerate(self.buttons):
            rect = rects[i]
            is_selected = (i == self.selected_button and self.focus_area == 2)  # Focus area 2 for buttons
            
            # Determine button text and color based on state
            display_text = btn_text
            btn_color = ui_colors.COLOR_BUTTON
            text_color = ui_colors.COLOR_TEXT
            
            # Special handling for DB/Wallpaper buttons
            if i == 2:  # Build Pokemon DB
                if self._db_exists():
                    display_text = "Rebuild Pokemon DB"
                    btn_color = (40, 80, 40)  # Dark green
                    text_color = (100, 255, 100)  # Light green text
                else:
                    btn_color = (80, 40, 40)  # Dark red
                    text_color = (255, 100, 100)  # Light red text
            elif i == 3:  # Build Wallpapers
                if self._wallpapers_exist():
                    display_text = "Rebuild Wallpapers"
                    btn_color = (40, 80, 40)  # Dark green
                    text_color = (100, 255, 100)  # Light green text
                else:
                    btn_color = (80, 40, 40)  # Dark red
                    text_color = (255, 100, 100)  # Light red text
            
            # Override colors if building
            if self.is_building and i < 3:
                display_text = "Cancel"
                btn_color = ui_colors.COLOR_BUTTON
                text_color = ui_colors.COLOR_TEXT

            # Draw button background
            if is_selected:
                pygame.draw.rect(surface, ui_colors.COLOR_BUTTON_HOVER, rect)
                pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, rect, 3)
            else:
                pygame.draw.rect(surface, btn_color, rect)
                pygame.draw.rect(surface, ui_colors.COLOR_BORDER, rect, 2)

            # Handle text scrolling if truncated and selected
            max_width = rect.width - 10
            txt_surface = self.font_body.render(display_text, True, text_color)
            
            if txt_surface.get_width() > max_width:
                # Text is truncated
                if is_selected:
                    # Scroll text on hover
                    scroll_offset = (pygame.time.get_ticks() // 100) % len(display_text)
                    scrolled_text = display_text[scroll_offset:] + "  " + display_text[:scroll_offset]
                    txt_surface = self.font_body.render(scrolled_text, True, text_color)
                    # Create a clipped surface
                    clip_rect = pygame.Rect(0, 0, max_width, txt_surface.get_height())
                    surface.set_clip(rect.inflate(-5, 0))
                    surface.blit(txt_surface, (rect.left + 5, rect.centery - txt_surface.get_height() // 2))
                    surface.set_clip(None)
                else:
                    # Truncate with ellipsis
                    truncated = display_text
                    while self.font_body.size(truncated + "...")[0] > max_width and len(truncated) > 5:
                        truncated = truncated[:-1]
                    txt_surface = self.font_body.render(truncated + "...", True, text_color)
                    surface.blit(txt_surface, txt_surface.get_rect(center=rect.center))
            else:
                # Text fits normally
                surface.blit(txt_surface, txt_surface.get_rect(center=rect.center))

    def _draw_footer(self, surface: pygame.Surface):
        y = self.height - self._FOOTER_H + 4
        # Use ASCII characters instead of Unicode arrows
        hint = "L/R:Switch Area  Up/Down:Navigate  A:Select  SELECT:Shiny  B:Back"
        txt = self.font_body.render(hint, True, (100, 100, 120))
        surface.blit(txt, txt.get_rect(center=(self.width // 2, y)))

    def _close(self):
        self.visible = False
        if self.close_callback:
            self.close_callback()


# ---------------------------------------------------------------------------
# Modal wrapper (used by db_check_mixin.py and settings)
# ---------------------------------------------------------------------------
class DBBuilder:
    """Modal wrapper for DBBuilderScreen."""

    def __init__(self, width, height, close_callback=None):
        self.screen = DBBuilderScreen(width, height, close_callback)
        self.visible = True

    def update(self, events):
        self.screen.handle_events(events)
        self.visible = self.screen.visible
        return self.visible

    def handle_controller(self, ctrl):
        self.screen.handle_controller(ctrl)

    def draw(self, surface):
        self.screen.draw(surface)


# Alias
Modal = DBBuilder