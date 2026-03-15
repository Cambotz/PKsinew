#!/usr/bin/env python3

"""
jukebox.py — Jukebox music player screen for Sinew.

Users can drop audio files into dist/data/sounds/music/ and use
this screen to pick which track plays as menu music.

The selected track is persisted to sinew_settings.json under 'jukebox_track'
so that music_manager picks it up on next startup.

Controls:
    Up / Down   — navigate track list
    A / Enter   — play selected track (and save as startup track)
    X / Y       — stop current track
    B / Escape  — close (music keeps playing)
"""

import os

import pygame

import ui_colors
from config import MENU_MUSIC_PATH, MUSIC_DIR, MUSIC_EXTENSIONS, VOLUME_DEFAULT
from settings import load_sinew_settings, save_sinew_settings_merged
from ui_scale import ui, scaled_font


class JukeboxScreen:
    """
    Simple music player that lets users drop audio files into the music
    folder (dist/data/sounds/music/) and pick which one to play.
    """

    def __init__(self, width, height, close_callback=None):
        self.width = width
        self.height = height
        self.close_callback = close_callback
        self.visible = True

        self.font_header = scaled_font(16)
        self.font_text   = scaled_font(12)
        self.font_small  = scaled_font(10)

        self.tracks = []        # list of (display_name, full_path)
        self.selected = 0
        self.scroll = 0
        self.now_playing = None # full_path of currently playing track
        self.status_msg = ""
        self.status_timer = 0

        self._scan_tracks()
        self._sync_now_playing()

    # ------------------------------------------------------------------
    # Track scanning
    # ------------------------------------------------------------------

    def _scan_tracks(self):
        """Scan MUSIC_DIR for supported audio files."""
        self.tracks = []
        try:
            if not os.path.isdir(MUSIC_DIR):
                return
            for fname in sorted(os.listdir(MUSIC_DIR)):
                if fname.lower().endswith(MUSIC_EXTENSIONS):
                    display = os.path.splitext(fname)[0]
                    full    = os.path.join(MUSIC_DIR, fname)
                    self.tracks.append((display, full))
            print(f"[Jukebox] Found {len(self.tracks)} tracks in {MUSIC_DIR}")
        except Exception as e:
            print(f"[Jukebox] Error scanning tracks: {e}")

    def _sync_now_playing(self):
        """
        Reflect whatever pygame.mixer.music is currently playing into
        now_playing, and position the cursor on that track.
        """
        try:
            if not pygame.mixer.get_init() or not pygame.mixer.music.get_busy():
                return
            # Match against the saved jukebox_track setting
            s = load_sinew_settings()
            saved = s.get("jukebox_track") or MENU_MUSIC_PATH
            for i, (_, path) in enumerate(self.tracks):
                if os.path.normpath(path) == os.path.normpath(saved):
                    self.now_playing = path
                    self.selected = i
                    self._clamp_scroll()
                    return
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Playback helpers
    # ------------------------------------------------------------------

    def _play(self, path):
        """Start playing the given file and save it as the startup track."""
        try:
            pygame.mixer.music.load(path)
            s = load_sinew_settings()
            vol = s.get("master_volume", VOLUME_DEFAULT) / 100.0
            pygame.mixer.music.set_volume(max(0.0, min(1.0, vol)))
            pygame.mixer.music.play(-1)  # loop like menu music
            self.now_playing = path
            name = os.path.splitext(os.path.basename(path))[0]
            self._set_status(f"Now playing: {name}")
            print(f"[Jukebox] Playing: {path}")
            # Persist as the startup track
            save_sinew_settings_merged({"jukebox_track": path})
        except Exception as e:
            self._set_status("Error loading track")
            print(f"[Jukebox] Playback error: {e}")

    def _stop(self):
        """Stop playback and revert startup track to the default."""
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.now_playing = None
        self._set_status("Stopped - default track plays on next launch")
        # Clear saved track so startup reverts to SinewMenu.mp3
        save_sinew_settings_merged({"jukebox_track": None})
        print("[Jukebox] Stopped; jukebox_track cleared (default on next start)")

    def _set_status(self, msg):
        self.status_msg   = msg
        self.status_timer = 210  # ~3.5s at 60fps

    def _close(self):
        """Close the jukebox without affecting playback."""
        self.visible = False
        if self.close_callback:
            self.close_callback()

    # ------------------------------------------------------------------
    # Input — controller
    # ------------------------------------------------------------------

    def handle_controller(self, ctrl):
        """Handle controller input; returns True when consumed."""
        if not self.visible:
            return False

        consumed = False

        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            if self.selected > 0:
                self.selected -= 1
                self._clamp_scroll()
            consumed = True

        elif ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            if self.selected < len(self.tracks) - 1:
                self.selected += 1
                self._clamp_scroll()
            consumed = True

        elif ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            if self.tracks:
                _, path = self.tracks[self.selected]
                self._play(path)
            consumed = True

        elif ctrl.is_button_just_pressed("X") or ctrl.is_button_just_pressed("Y"):
            # X or Y stops playback (separate from close)
            if ctrl.is_button_just_pressed("X"):
                ctrl.consume_button("X")
            if ctrl.is_button_just_pressed("Y"):
                ctrl.consume_button("Y")
            if self.now_playing:
                self._stop()
            consumed = True

        elif ctrl.is_button_just_pressed("B"):
            # B always closes — music keeps playing
            ctrl.consume_button("B")
            self._close()
            consumed = True

        return consumed

    # ------------------------------------------------------------------
    # Input — keyboard (called by settings modal via update())
    # ------------------------------------------------------------------

    def update(self, events):
        """
        Handle pygame keyboard events and return self.visible.
        Called by the settings modal's sub-screen event loop.
        Controller input is handled separately via handle_controller().
        """
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    if self.selected > 0:
                        self.selected -= 1
                        self._clamp_scroll()

                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    if self.selected < len(self.tracks) - 1:
                        self.selected += 1
                        self._clamp_scroll()

                elif event.key in (pygame.K_RETURN, pygame.K_z):
                    if self.tracks:
                        _, path = self.tracks[self.selected]
                        self._play(path)

                elif event.key in (pygame.K_DELETE, pygame.K_F5):
                    # Delete or F5 stops the track — distinct from close
                    if self.now_playing:
                        self._stop()

                elif event.key in (pygame.K_ESCAPE, pygame.K_x):
                    # Always close; music keeps playing
                    self._close()

        return self.visible

    # ------------------------------------------------------------------
    # Scroll helpers
    # ------------------------------------------------------------------

    def _clamp_scroll(self):
        visible_rows = self._visible_rows()
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + visible_rows:
            self.scroll = self.selected - visible_rows + 1

    def _visible_rows(self):
        return max(1, (self.height - 130) // 28)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surf):
        if not self.visible:
            return

        # Background overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(245)
        overlay.fill(ui_colors.COLOR_BG)
        surf.blit(overlay, (0, 0))
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, (0, 0, self.width, self.height), 2)

        # Header
        title = self.font_header.render("Jukebox", True, ui_colors.COLOR_HIGHLIGHT)
        surf.blit(title, (ui.s(16), ui.s(12)))

        folder_hint = self.font_small.render(
            "Drop files into: data/sounds/music/",
            True, ui_colors.COLOR_BORDER,
        )
        surf.blit(folder_hint, (ui.s(16), ui.s(32)))

        close_hint = self.font_small.render("B: Close", True, ui_colors.COLOR_BORDER)
        surf.blit(close_hint, (self.width - close_hint.get_width() - ui.s(12), ui.s(15)))

        # Divider
        pygame.draw.line(
            surf, ui_colors.COLOR_BORDER,
            (ui.s(10), ui.s(52)), (self.width - ui.s(10), ui.s(52)),
        )

        if not self.tracks:
            msg = self.font_text.render("No music files found.", True, ui_colors.COLOR_BORDER)
            surf.blit(msg, msg.get_rect(centerx=self.width // 2, centery=self.height // 2))
        else:
            visible_rows = self._visible_rows()
            row_h = ui.s(28)
            list_top = ui.s(60)

            for i in range(visible_rows):
                idx = self.scroll + i
                if idx >= len(self.tracks):
                    break

                display_name, path = self.tracks[idx]
                is_selected = (idx == self.selected)
                is_playing  = (path == self.now_playing)
                row_y    = list_top + i * row_h
                row_rect = pygame.Rect(ui.s(10), row_y, self.width - ui.s(20), row_h - ui.s(2))

                # Row background
                if is_selected:
                    pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, row_rect, border_radius=ui.s(4))
                    border_col = ui_colors.COLOR_SUCCESS if is_playing else ui_colors.COLOR_HIGHLIGHT
                    pygame.draw.rect(surf, border_col, row_rect, 2, border_radius=ui.s(4))
                elif is_playing:
                    pygame.draw.rect(surf, ui_colors.COLOR_HEADER, row_rect, border_radius=ui.s(4))
                    pygame.draw.rect(surf, ui_colors.COLOR_SUCCESS, row_rect, 1, border_radius=ui.s(4))

                # Playing indicator - drawn as a filled triangle (play button shape)
                # so we don't rely on a music glyph the GBA font doesn't support.
                if is_playing:
                    tri_w = ui.s(7)
                    tri_h = ui.s(10)
                    tri_x = row_rect.x + ui.s(7)
                    tri_y = row_y + (row_h - tri_h) // 2
                    pygame.draw.polygon(surf, ui_colors.COLOR_SUCCESS, [
                        (tri_x,           tri_y),
                        (tri_x,           tri_y + tri_h),
                        (tri_x + tri_w,   tri_y + tri_h // 2),
                    ])
                    text_x = row_rect.x + ui.s(20)
                else:
                    text_x = row_rect.x + ui.s(10)

                text_col = ui_colors.COLOR_TEXT if is_selected or is_playing else ui_colors.COLOR_BORDER
                name_surf = self.font_text.render(display_name, True, text_col)
                surf.blit(name_surf, (text_x, row_y + (row_h - name_surf.get_height()) // 2))

            # Scroll arrows
            if self.scroll > 0:
                up = self.font_text.render("^", True, ui_colors.COLOR_HIGHLIGHT)
                surf.blit(up, (self.width - ui.s(20), list_top))
            if self.scroll + visible_rows < len(self.tracks):
                dn = self.font_text.render("v", True, ui_colors.COLOR_HIGHLIGHT)
                surf.blit(dn, (self.width - ui.s(20), list_top + visible_rows * row_h - row_h))

        # Status bar
        if self.status_timer > 0:
            self.status_timer -= 1
            status_surf = self.font_small.render(self.status_msg, True, ui_colors.COLOR_SUCCESS)
            surf.blit(
                status_surf,
                status_surf.get_rect(centerx=self.width // 2, bottom=self.height - ui.s(22)),
            )

        # Hint bar
        hints = "A: Play    X/Y: Stop    B: Close"
        hint_surf = self.font_small.render(hints, True, ui_colors.COLOR_BORDER)
        surf.blit(
            hint_surf,
            hint_surf.get_rect(centerx=self.width // 2, bottom=self.height - ui.s(6)),
        )