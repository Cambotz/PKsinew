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
from config import BASE_DIR, DATA_DIR, FONT_PATH, GEN3_NORMAL_DIR, GEN3_SHINY_DIR
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
        os.makedirs(GEN3_NORMAL_DIR, exist_ok=True)
        os.makedirs(GEN3_SHINY_DIR, exist_ok=True)

        self.log(f"Downloading: {self.pack['display_name']}")
        self.log(f"Target: {GEN3_NORMAL_DIR}")
        self.log("")

        ok = 0
        skip = 0

        ext = self.pack.get("file_ext", "png")

        for i in range(1, MAX_POKEMON + 1):
            if self.cancel_requested:
                self.log("Download cancelled.")
                break

            pid_str = f"{i:03d}"
            normal_path = os.path.join(GEN3_NORMAL_DIR, f"{pid_str}.{ext}")
            shiny_path = os.path.join(GEN3_SHINY_DIR, f"{pid_str}.{ext}")

            normal_url = get_sprite_url(self.pack, i, shiny=False)
            shiny_url = get_sprite_url(self.pack, i, shiny=True) if self.pack["has_shiny"] else None

            n_ok = self._dl(normal_url, normal_path)
            s_ok = self._dl(shiny_url, shiny_path) if shiny_url else False

            if n_ok or s_ok:
                ok += 1
                parts = []
                if n_ok:
                    parts.append("normal")
                if s_ok:
                    parts.append("shiny")
                self.log(f"[{pid_str}] Downloaded {', '.join(parts)}")
            else:
                skip += 1

            # Brief rate-limit courtesy
            if i % 10 == 0:
                import time; time.sleep(0.05)

        self.log("")
        self.log(f"Done: {ok} downloaded, {skip} skipped.")
        self.done()


# ---------------------------------------------------------------------------
# Main screen class
# ---------------------------------------------------------------------------
class DBBuilderScreen:
    """Screen for building the Pokemon database with sprite pack selector."""

    # Layout constants
    # Total usable width at default modal size (480-40=440px):
    #   pack_list(100) + pad(6) + preview(100) + pad(6) + terminal(~116) + pad(6) + buttons(100) + pad(6)
    _PACK_LIST_W = 100
    _PREVIEW_W   = 100
    _BUTTON_W    = 100
    _HEADER_H    = 40
    _FOOTER_H    = 22
    _PADDING     = 6

    def __init__(self, width, height, close_callback=None):
        self.width = width
        self.height = height
        self.visible = True
        self.close_callback = close_callback
        self.controller = get_controller()

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
                self.packs.append(pack_info.official_def)
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

        # --- Build / download state ---
        self.is_building = False
        self.cancel_requested = False
        self.build_thread = None
        self._sprite_downloader: _SpriteDownloader | None = None

        # --- Button state ---
        # Focus areas: 0=pack list, 1=action buttons
        self.focus_area = 0
        self.selected_button = 0
        self.buttons = [
            "Download Sprites",
            "Build Pokemon DB",
            "Build Wallpapers",
            "Back",
        ]

        # Debounce
        self._last_click_time = 0
        self._click_debounce_ms = 300

        # Kick off initial Pikachu preview
        self._load_preview_for_current_pack()

        # Welcome message
        self._add_line("Sprite Pack Selector")
        self._add_line("=" * 32)
        self._add_line("")
        self._add_line("1. Pick a sprite pack from the")
        self._add_line("   list on the left.")
        self._add_line("2. Click 'Download Sprites' to")
        self._add_line("   fetch all 386 sprites.")
        self._add_line("3. Click 'Build Pokemon DB' to")
        self._add_line("   download metadata.")
        self._add_line("")
        self._add_line("Pack choice is saved and used")
        self._add_line("on future DB builds too.")
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
        self._scroll_to_bottom()

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
        """Pack list (left column)."""
        return pygame.Rect(
            self._PADDING,
            self._HEADER_H + self._PADDING,
            self._PACK_LIST_W,
            self.height - self._HEADER_H - self._FOOTER_H - self._PADDING * 2,
        )

    def _get_preview_rect(self) -> pygame.Rect:
        """Pikachu preview + description panel (second column)."""
        x = self._PADDING + self._PACK_LIST_W + self._PADDING
        return pygame.Rect(
            x,
            self._HEADER_H + self._PADDING,
            self._PREVIEW_W,
            self.height - self._HEADER_H - self._FOOTER_H - self._PADDING * 2,
        )

    def _get_button_rects(self) -> list[pygame.Rect]:
        bw = self._BUTTON_W
        bh = 28
        spacing = 8
        bx = self.width - bw - self._PADDING
        rects = []
        for i in range(len(self.buttons)):
            by = self._HEADER_H + self._PADDING + i * (bh + spacing)
            rects.append(pygame.Rect(bx, by, bw, bh))
        return rects

    def _get_terminal_rect(self) -> pygame.Rect:
        """Terminal occupies the space between preview panel and buttons."""
        preview_right = self._get_preview_rect().right
        btn_left = self._get_button_rects()[0].left
        tx = preview_right + self._PADDING
        ty = self._HEADER_H + self._PADDING
        tw = btn_left - tx - self._PADDING
        th = self.height - self._HEADER_H - self._FOOTER_H - self._PADDING * 2
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
        def execute():
            self.is_building = True
            self.cancel_requested = False
            old_stdout = sys.stdout
            old_stderr = sys.stderr

            try:
                if getattr(sys, "frozen", False):
                    bundle_dir = sys._MEIPASS
                    if bundle_dir not in sys.path:
                        sys.path.insert(0, bundle_dir)

                script_path = os.path.join(BASE_DIR, "DBbuilder.py")

                class UILogger:
                    def __init__(self, func):
                        self.func = func
                    def write(self, s):
                        if s.strip():
                            self.func(s.strip())
                    def flush(self):
                        pass

                sys.stdout = UILogger(self._add_line)
                sys.stderr = UILogger(self._add_line)

                custom_globals = globals().copy()
                custom_globals.update(
                    {"ui_instance": self, "config": config, "__name__": "__main__"}
                )
                runpy.run_path(
                    script_path, init_globals=custom_globals, run_name="__main__"
                )
                self._add_line("Build finished successfully!")

            except Exception:
                self._add_line(f"Build Error: {traceback.format_exc()}")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                self.is_building = False

        threading.Thread(target=execute, daemon=True).start()

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
        """Activate whichever button is selected, or act on pack list."""
        if self.focus_area == 0:
            # Pack list — Enter/A previews (already previewed on navigation),
            # just switch focus to buttons
            self.focus_area = 1
            return

        idx = self.selected_button
        if self.is_building:
            self._cancel_build()
            return

        if idx == 0:
            self._start_sprite_download()
        elif idx == 1:
            self._start_build()
        elif idx == 2:
            self._start_wallpaper_build()
        else:
            self._close()

    def handle_events(self, events):
        current_time = pygame.time.get_ticks()

        for event in events:
            if event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_ESCAPE:
                    if self.is_building:
                        self._cancel_build()
                    else:
                        self._close()

                elif key == pygame.K_TAB:
                    # Switch focus between pack list and buttons
                    self.focus_area = 1 - self.focus_area

                elif key in (pygame.K_UP, pygame.K_w):
                    if self.focus_area == 0:
                        old = self.selected_pack_idx
                        self.selected_pack_idx = max(0, self.selected_pack_idx - 1)
                        if self.selected_pack_idx != old:
                            self._load_preview_for_current_pack()
                    else:
                        self.selected_button = max(0, self.selected_button - 1)

                elif key in (pygame.K_DOWN, pygame.K_s):
                    if self.focus_area == 0:
                        old = self.selected_pack_idx
                        self.selected_pack_idx = min(len(self.packs) - 1, self.selected_pack_idx + 1)
                        if self.selected_pack_idx != old:
                            self._load_preview_for_current_pack()
                    else:
                        self.selected_button = min(len(self.buttons) - 1, self.selected_button + 1)

                elif key in (pygame.K_LEFT, pygame.K_a):
                    # Scroll terminal
                    self.scroll_offset = max(0, self.scroll_offset - 3)

                elif key in (pygame.K_RIGHT, pygame.K_d):
                    max_scroll = max(0, len(self.terminal_lines) - self._get_visible_line_count())
                    self.scroll_offset = min(max_scroll, self.scroll_offset + 3)

                elif key == pygame.K_RETURN:
                    if current_time - self._last_click_time > self._click_debounce_ms:
                        self._last_click_time = current_time
                        self._activate_button()

                elif key == pygame.K_x:
                    # Toggle shiny preview
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
                    item_h = 18
                    rel_y = pos[1] - left_rect.top - 4
                    clicked_idx = rel_y // item_h
                    if 0 <= clicked_idx < len(self.packs):
                        old = self.selected_pack_idx
                        self.selected_pack_idx = clicked_idx
                        if self.selected_pack_idx != old:
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

        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            if self.focus_area == 0:
                old = self.selected_pack_idx
                self.selected_pack_idx = max(0, self.selected_pack_idx - 1)
                if self.selected_pack_idx != old:
                    self._load_preview_for_current_pack()
            else:
                self.selected_button = max(0, self.selected_button - 1)

        elif ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            if self.focus_area == 0:
                old = self.selected_pack_idx
                self.selected_pack_idx = min(len(self.packs) - 1, self.selected_pack_idx + 1)
                if self.selected_pack_idx != old:
                    self._load_preview_for_current_pack()
            else:
                self.selected_button = min(len(self.buttons) - 1, self.selected_button + 1)

        elif ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_dpad("left")
            if self.focus_area == 1:
                self.focus_area = 0
            else:
                self.scroll_offset = max(0, self.scroll_offset - 3)

        elif ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("right")
            if self.focus_area == 0:
                self.focus_area = 1
            else:
                max_scroll = max(0, len(self.terminal_lines) - self._get_visible_line_count())
                self.scroll_offset = min(max_scroll, self.scroll_offset + 3)

        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            if current_time - self._last_click_time > self._click_debounce_ms:
                self._last_click_time = current_time
                self._activate_button()

        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            if self.is_building:
                self._cancel_build()
            else:
                self._close()

        if ctrl.is_button_just_pressed("X"):
            ctrl.consume_button("X")
            self._show_shiny_preview = not self._show_shiny_preview

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
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

    def _draw_header(self, surface: pygame.Surface):
        header_rect = pygame.Rect(0, 0, self.width, self._HEADER_H)
        pygame.draw.rect(surface, ui_colors.COLOR_HEADER, header_rect)
        title = self.font_header.render("Database Builder", True, ui_colors.COLOR_TEXT)
        surface.blit(title, title.get_rect(midleft=(15, 20)))

        if self.is_building:
            dots = "." * ((pygame.time.get_ticks() // 500) % 4)
            status = self.font_body.render(f"Working{dots}", True, ui_colors.COLOR_HIGHLIGHT)
            surface.blit(status, status.get_rect(midright=(self.width - 15, 20)))

    def _draw_pack_list(self, surface: pygame.Surface):
        rect = self._get_left_panel_rect()

        # Background
        pygame.draw.rect(surface, (20, 20, 30), rect)
        border_color = ui_colors.COLOR_HIGHLIGHT if self.focus_area == 0 else ui_colors.COLOR_BORDER
        pygame.draw.rect(surface, border_color, rect, 2)

        # Header label
        lbl = self.font_small.render("SPRITE PACK", True, (120, 120, 160))
        surface.blit(lbl, (rect.left + 5, rect.top + 3))

        item_h = 18
        y = rect.top + 16
        max_items = (rect.height - 16) // item_h

        # Simple scroll: keep selected visible
        start = max(0, self.selected_pack_idx - max_items + 1) if self.selected_pack_idx >= max_items else 0

        for i, pack in enumerate(self.packs[start: start + max_items]):
            real_idx = start + i
            item_rect = pygame.Rect(rect.left + 2, y, rect.width - 4, item_h - 2)

            if real_idx == self.selected_pack_idx:
                bg = ui_colors.COLOR_BUTTON_HOVER if self.focus_area == 0 else ui_colors.COLOR_BUTTON
                pygame.draw.rect(surface, bg, item_rect)
                pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, item_rect, 1)
                col = ui_colors.COLOR_HIGHLIGHT
            else:
                col = ui_colors.COLOR_TEXT

            name = pack["display_name"]
            # Truncate if needed
            while self.font_small.size(name)[0] > rect.width - 12 and len(name) > 4:
                name = name[:-1]
            txt = self.font_small.render(name, True, col)
            surface.blit(txt, (rect.left + 5, y + 3))
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
        shiny_lbl = self.font_small.render(f"[X]{shiny_txt}{anim_tag}", True, (140, 140, 180))
        surface.blit(shiny_lbl, (preview_area.left + 2, preview_area.bottom + 2))

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
        pygame.draw.rect(surface, ui_colors.COLOR_BORDER, rect, 2)

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
            is_selected = (i == self.selected_button and self.focus_area == 1)

            if is_selected:
                pygame.draw.rect(surface, ui_colors.COLOR_BUTTON_HOVER, rect)
                pygame.draw.rect(surface, ui_colors.COLOR_HIGHLIGHT, rect, 3)
            else:
                pygame.draw.rect(surface, ui_colors.COLOR_BUTTON, rect)
                pygame.draw.rect(surface, ui_colors.COLOR_BORDER, rect, 2)

            display_text = "Cancel" if (self.is_building and i < 3) else btn_text
            txt = self.font_body.render(display_text, True, ui_colors.COLOR_TEXT)
            surface.blit(txt, txt.get_rect(center=rect.center))

    def _draw_footer(self, surface: pygame.Surface):
        y = self.height - self._FOOTER_H + 4
        hint = "Tab:Switch  A/Enter:Select  X:Shiny  B:Back"
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