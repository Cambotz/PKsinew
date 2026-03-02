#!/usr/bin/env python3

"""
game_screen.py — Main game screen class for Sinew; composes all mixin modules into the primary UI.
"""

import json
import os
import sys
import time
import builtins
import platform as _platform
from datetime import datetime

# On Linux ARM devices, preload the system SDL2 so pygame uses it
if sys.platform == 'linux' and _platform.machine().lower() in ('aarch64', 'arm64', 'armv7l',
    'armv6l'):
    import ctypes as _ctypes
    _sdl2_paths = [
        '/usr/lib/libSDL2-2.0.so.0',
        '/usr/lib/libSDL2.so',
        '/usr/lib/aarch64-linux-gnu/libSDL2-2.0.so.0',
        '/usr/lib/arm-linux-gnueabihf/libSDL2-2.0.so.0',
        '/usr/local/lib/libSDL2.so',
    ]
    for _sdl2_path in _sdl2_paths:
        try:
            _ctypes.CDLL(_sdl2_path, mode=_ctypes.RTLD_GLOBAL)
            print(f'[Main] Preloaded system SDL2: {_sdl2_path}')
            break
        except OSError:
            pass
    else:
        print('[Main] System SDL2 not found in known paths, using bundled version')

import pygame
from PIL import Image, ImageSequence
import ui_colors
from config import (
    CORES_DIR, DATA_DIR, EXT_DIR, FONT_PATH, IS_HANDHELD,
    MGBA_CORE_PATH, ROMS_DIR, SAVES_DIR, SAVE_PATHS,
    SPRITES_DIR, SYSTEM_DIR,
)
from save_data_manager import get_manager
from ui_components import Button
from sinew_logging import init_redirectors
_log_file_path = init_redirectors()

# Ensure SDL audio change flag is set before pygame mixer init
os.environ.setdefault('SDL_AUDIO_ALLOW_CHANGES', '0')

# On Windows (non-frozen), force directsound for reliable audio
if sys.platform == 'win32' and not getattr(sys, 'frozen', False):
    os.environ.setdefault('SDL_AUDIODRIVER', 'directsound')

# Modal imports
from pc_box import PCBox
from trainerinfo import Modal as TrainerInfoModal
from Itembag import Modal as ItemBagModal
from achievements import Modal as AchievementsModal
from achievements import get_achievement_notification, init_achievement_system
from settings import Settings
from db_builder_screen import DBBuilder
from PokedexModal import PokedexModal
from export_modal import ExportModal
from events_screen import EventsModal

from game_detection import (
    GAME_DEFINITIONS, GAME_FULL, GAME_SAVE_ONLY, GAME_UNAVAILABLE,
    GAMES, _rom_scan_cache,
    detect_games_with_dirs, find_rom_for_game, find_save_for_game,
    get_game_availability,
)
from settings import (
    load_sinew_settings as load_settings,
    save_sinew_settings_merged as save_settings_file,
)

from game_dialogs import PlaceholderModal, DBWarningPopup

# Mixin imports
from achievement_checker import AchievementCheckerMixin
from pause_combo import PauseComboMixin
from notifications import NotificationsMixin
from music_manager import MusicManagerMixin
from emulator_session import EmulatorSessionMixin
from ui_gamescreen_draw import GameScreenDrawMixin
from save_load_mixin import SaveLoadMixin
from settings_apply_mixin import SettingsApplyMixin
from game_nav_mixin import GameNavMixin
from db_check_mixin import DBCheckMixin
from modal_launcher_mixin import ModalLauncherMixin


def load_gif_frames(path, width, height):  # noqa: F401  # kept for external callers
    """Load GIF frames scaled to specified size"""
    frames = []
    durations = []

    if not path or not os.path.exists(path):
        return (frames, durations)

    try:
        pil_img = Image.open(path)
        for frame in ImageSequence.Iterator(pil_img):
            frame = frame.convert('RGBA').resize((width, height), Image.NEAREST)
            data = frame.tobytes()
            surf = pygame.image.fromstring(data, frame.size, frame.mode).convert_alpha()
            frames.append(surf)
            durations.append(frame.info.get('duration', 100))
        pil_img.close()
        return (frames, durations)
    except Exception as e:
        print(f'Failed to open GIF {path}: {e}')
        return (frames, durations)


class GameScreen(
    AchievementCheckerMixin,
    PauseComboMixin,
    NotificationsMixin,
    MusicManagerMixin,
    EmulatorSessionMixin,
    GameScreenDrawMixin,
    SaveLoadMixin,
    SettingsApplyMixin,
    GameNavMixin,
    DBCheckMixin,
    ModalLauncherMixin,
):
    """
    Game selection and management screen
    Displays animated title GIFs and provides access to game features
    Sinew is the first entry - a combined view of all saves
    """

    INPUT_COOLDOWN = 0.25

    def __init__(self, width, height, font, back_callback=None, controller=None, scaler=None,
        screen=None):
        self.width = width
        self.height = height
        self.font = font
        self.back_callback = back_callback
        self.controller = controller
        self.scaler = scaler
        self._loading_screen = screen

        # Load settings
        self.settings = load_settings()

        # Dev mode flag stored in builtins for cross-module access
        import builtins
        if not hasattr(builtins, 'SINEW_DEV_MODE'):
            builtins.SINEW_DEV_MODE = self.settings.get('dev_mode', False)
        if not hasattr(builtins, 'SINEW_USE_EMULATOR_PROVIDER'):
            builtins.SINEW_USE_EMULATOR_PROVIDER = self.settings.get('use_emulator_provider', False)

        # Emulator manager — always initialized; use_provider controls whether
        # external (subprocess) providers are included alongside built-in mGBA.
        use_provider = self.settings.get('use_emulator_provider', False)
        try:
            from emulator_manager import EmulatorManager
            self.emulator_manager = EmulatorManager(use_external_providers=use_provider)
            if self.emulator_manager.active_provider:
                print(f'[EmulatorManager] Provider ready: {type(
                    self.emulator_manager.active_provider).__name__}')
            else:
                print('[EmulatorManager] No provider matched this environment')
        except ImportError:
            self.emulator_manager = None
            print('[EmulatorManager] emulator_manager.py not found — provider unavailable')  # pylint: disable=line-too-long  # noqa: E501

        # Pause combo
        self._load_pause_combo_setting()

        # Music
        self._init_menu_music()

        # Games
        self.games = {}
        self.game_names = []
        self._init_games()

        # Navigation state
        self.current_game = 0
        self.menu_index = 0
        self.modal_instance = None
        self.should_close = False

        # Emulator state
        self.emulator = None
        self.emulator_active = False
        self._emulator_pause_combo_released = True
        self._ext_emu_closed_needs_reload = False

        # Notification state
        self._notification_text = None
        self._notification_subtext = None
        self._notification_timer = 0
        self._notification_duration = 3000
        self._notification_y = -60
        self._notification_target_y = 10

        # Resume banner animation
        self._resume_banner_scroll_offset = 0
        self._resume_banner_scroll_speed = 1.5
        self._resume_banner_pulse_time = 0

        # Input timing
        self._last_input_time = time.time()
        self._modal_just_closed = False

        # Precache flag
        self._precached = False

        # Loading screen steps
        self._draw_loading_screen(self._loading_screen, 'Starting up...', 0, 3)
        self._draw_loading_screen(self._loading_screen, 'Loading save data...', 1, 3)
        self.load_game_and_background()
        self._start_menu_music()
        self._draw_loading_screen(self._loading_screen, 'Checking database...', 2, 3)
        self._check_database()
        self._init_achievement_system()
        self._check_all_achievements_on_startup()

    def _close_modal(self):
        """Close current modal"""
        self.modal_instance = None
        self._last_input_time = time.time()
        self._modal_just_closed = True

    def _resume_game_from_modal(self):
        """Close modal and resume game (called by START+SELECT in modals)"""
        self.modal_instance = None
        self._last_input_time = time.time()
        self._modal_just_closed = True

        if self.emulator and self.emulator.loaded:
            self._stop_menu_music()
            self.emulator.resume()
            self.emulator_active = True
            if self.scaler:
                self.scaler.set_virtual_resolution(240, 160)
            print('[Sinew] Resumed game from modal via START+SELECT')

    def update(self, events, dt):
        """
        Update game screen state

        Args:
            events: List of pygame events
            dt: Delta time in milliseconds

        Returns:
            bool: False if screen should close, True otherwise
        """
        # Reset modal close flag only after cooldown has passed
        if self._modal_just_closed and (
            time.time() - self._last_input_time >= self.INPUT_COOLDOWN
        ):
            self._modal_just_closed = False

        # Update notification animation
        self._update_notification(dt)

        # Update achievement notification
        if self._achievement_notification:
            self._achievement_notification.update()

        # Handle emulator if active
        if self.emulator_active and self.emulator:
            return self._update_emulator(events, dt)

        # External emulator closed — reload on the main thread.
        if self._ext_emu_closed_needs_reload:
            self._ext_emu_closed_needs_reload = False
            if self.scaler:
                self.scaler.restore_virtual_resolution()
            self._reload_settings_from_disk()
            self.load_game_and_background()
            self._force_reload_current_save()
            self._check_achievements_for_current_game()
            self._start_menu_music()
            print("[Sinew] Returned from external emulator")

        # Check for resume combo when emulator is paused but we're in Sinew menu
        self._pause_combo_active = False
        if self.emulator and self.emulator.loaded and not self.emulator_active:
            combo_held = self._check_pause_combo_direct()

            keys = pygame.key.get_pressed()
            if keys[pygame.K_RETURN] and keys[pygame.K_BACKSPACE]:
                self._pause_combo_active = True

            if self.controller and hasattr(self.controller, 'kb_nav_map'):
                try:
                    menu_keys = self.controller.kb_nav_map.get("MENU", [pygame.K_m])
                    for menu_key in menu_keys:
                        if keys[menu_key]:
                            self._pause_combo_active = True
                            break
                except Exception:
                    pass

            if combo_held and self._emulator_pause_combo_released:
                self._emulator_pause_combo_released = False
                print("[Sinew] Resume triggered - calling emulator.resume()")
                print(
                    f"[Sinew] Before resume:"
                    f" paused={self.emulator.paused},"
                    f" loaded={self.emulator.loaded}"
                )
                self._stop_menu_music()
                self.emulator.resume()
                print(f"[Sinew] After resume: paused={self.emulator.paused}")
                self.emulator_active = True
                if self.scaler:
                    self.scaler.set_virtual_resolution(240, 160)
                print("[Sinew] Resuming game - emulator_active set to True")
                return True

            menu_held = False
            keys = pygame.key.get_pressed()
            if self.controller and hasattr(self.controller, 'kb_nav_map'):
                try:
                    menu_keys = self.controller.kb_nav_map.get("MENU", [pygame.K_m])
                    for menu_key in menu_keys:
                        if keys[menu_key]:
                            menu_held = True
                            break
                except Exception:
                    pass

            if (
                not self._pause_combo_active
                and not self._is_controller_combo_held()
                and not menu_held
            ):
                self._emulator_pause_combo_released = True

        # Update GIF animation for current game (if we have games)
        if self.game_names and 0 <= self.current_game < len(self.game_names):
            gname = self.game_names[self.current_game]
            self._ensure_gif_loaded(gname)
            game_data = self.games[gname]

            if game_data["frames"]:
                game_data["time_accum"] += dt
                dur = (
                    game_data["durations"][game_data["frame_index"]]
                    if game_data["durations"]
                    else 100
                )
                if game_data["time_accum"] >= dur:
                    game_data["time_accum"] = 0
                    game_data["frame_index"] = (game_data["frame_index"] + 1) % len(
                        game_data["frames"]
                    )

        # Handle events
        for event in events:
            if self.modal_instance:
                if hasattr(self.modal_instance, "handle_mouse"):
                    self.modal_instance.handle_mouse(event)
                if hasattr(self.modal_instance, "handle_event"):
                    self.modal_instance.handle_event(event)
            elif not self._modal_just_closed and (
                time.time() - self._last_input_time >= self.INPUT_COOLDOWN
            ):
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.back_callback:
                            self.back_callback()
                            return False
                    elif event.key == pygame.K_DOWN:
                        menu_items = self.get_menu_items()
                        self.menu_index = (self.menu_index + 1) % len(menu_items)
                    elif event.key == pygame.K_UP:
                        menu_items = self.get_menu_items()
                        self.menu_index = (self.menu_index - 1) % len(menu_items)
                    elif event.key == pygame.K_RIGHT:
                        self._change_game_and_reload(1)
                    elif event.key == pygame.K_LEFT:
                        self._change_game_and_reload(-1)
                    elif event.key == pygame.K_RETURN:
                        if not getattr(self, "_pause_combo_active", False):
                            menu_items = self.get_menu_items()
                            if self.menu_index >= len(menu_items):
                                self.menu_index = 0
                            self._open_menu(menu_items[self.menu_index])

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    menu_items = self.get_menu_items()
                    if event.button == 4:
                        self.menu_index = (self.menu_index - 1) % len(menu_items)
                    elif event.button == 5:
                        self.menu_index = (self.menu_index + 1) % len(menu_items)
                    elif event.button == 1:
                        menu_button = Button(
                            menu_items[self.menu_index],
                            rel_rect=(0.25, 0.65, 0.5, 0.12),
                            callback=lambda item=menu_items[
                                self.menu_index
                            ]: self._open_menu(item),
                        )
                        menu_button.handle_event(event)

        # Handle controller
        if self.controller:
            if self.modal_instance:
                if hasattr(self.modal_instance, "handle_controller"):
                    self.modal_instance.handle_controller(self.controller)
            elif not self._modal_just_closed and (
                time.time() - self._last_input_time >= self.INPUT_COOLDOWN
            ):
                menu_items = self.get_menu_items()

                if self.controller.is_dpad_just_pressed("up"):
                    self.controller.consume_dpad("up")
                    self.menu_index = (self.menu_index - 1) % len(menu_items)

                if self.controller.is_dpad_just_pressed("down"):
                    self.controller.consume_dpad("down")
                    self.menu_index = (self.menu_index + 1) % len(menu_items)

                if self.controller.is_dpad_just_pressed("left"):
                    self.controller.consume_dpad("left")
                    self._change_game_and_reload(-1)

                if self.controller.is_dpad_just_pressed("right"):
                    self.controller.consume_dpad("right")
                    self._change_game_and_reload(1)

                if self.controller.is_button_just_pressed("L"):
                    self.controller.consume_button("L")
                    self._change_game_and_reload(-1)

                if self.controller.is_button_just_pressed("R"):
                    self.controller.consume_button("R")
                    self._change_game_and_reload(1)

                if self.controller.is_button_just_pressed("A"):
                    self.controller.consume_button("A")
                    if self.menu_index >= len(menu_items):
                        self.menu_index = 0
                    self._open_menu(menu_items[self.menu_index])

                if self.controller.is_button_just_pressed("B"):
                    self.controller.consume_button("B")
                    if self.back_callback:
                        self.back_callback()
                        return False

        # Update modal
        if self.modal_instance:
            if hasattr(self.modal_instance, "update"):
                result = self.modal_instance.update(events)
                if not result:
                    self._close_modal()

        return not self.should_close

    def draw(self, surf):
        """Draw the game screen"""
        if self.emulator_active and self.emulator:
            self._draw_emulator(surf)
            return

        if not self.game_names or self.current_game >= len(self.game_names):
            surf.fill(ui_colors.COLOR_BG)
            return

        gname = self.game_names[self.current_game]
        game_data = self.games[gname]

        if self.is_on_sinew():
            if self.sinew_logo:
                surf.blit(self.sinew_logo, (0, 0))
            else:
                surf.fill(self.sinew_bg_color)
        elif game_data["frames"]:
            bg_surf = game_data["frames"][game_data["frame_index"]]
            surf.blit(bg_surf, (0, 0))
        else:
            surf.fill(ui_colors.COLOR_BG)

        if self.modal_instance:
            if hasattr(self.modal_instance, "width") and hasattr(
                self.modal_instance, "height"
            ):
                modal_w = self.modal_instance.width
                modal_h = self.modal_instance.height
            else:
                modal_w = self.width - 30
                modal_h = self.height - 30

            modal_surf = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)

            if hasattr(self.modal_instance, "draw"):
                self.modal_instance.draw(modal_surf)

            pygame.draw.rect(
                modal_surf, ui_colors.COLOR_BORDER, (0, 0, modal_w, modal_h), 2
            )

            modal_x = (self.width - modal_w) // 2
            modal_y = (self.height - modal_h) // 2
            surf.blit(modal_surf, (modal_x, modal_y))

            if self.emulator and self.emulator.loaded and not self.emulator_active:
                self._draw_resume_banner(surf)
        else:
            menu_items = self.get_menu_items()
            if self.menu_index >= len(menu_items):
                self.menu_index = 0

            current_menu_item = menu_items[self.menu_index]
            is_disabled = current_menu_item == "Save File Only"

            menu_button = Button(
                current_menu_item,
                rel_rect=(0.25, 0.65, 0.5, 0.12),
                callback=lambda: None,
            )

            if is_disabled:
                bx = int(0.25 * self.width)
                by = int(0.65 * self.height)
                bw = int(0.5 * self.width)
                bh = int(0.12 * self.height)
                btn_rect = pygame.Rect(bx, by, bw, bh)

                pygame.draw.rect(surf, (50, 50, 55), btn_rect, border_radius=4)
                pygame.draw.rect(surf, (80, 80, 85), btn_rect, 2, border_radius=4)

                try:
                    btn_font = pygame.font.Font(FONT_PATH, 14)
                except Exception:
                    btn_font = self.font
                txt_surf = btn_font.render(current_menu_item, True, (100, 100, 105))
                txt_rect = txt_surf.get_rect(center=btn_rect.center)
                surf.blit(txt_surf, txt_rect)

                try:
                    hint2_font = pygame.font.Font(FONT_PATH, 7)
                except Exception:
                    hint2_font = pygame.font.SysFont(None, 12)
                hint2_surf = hint2_font.render(
                    "No ROM \u2014 place a .gba file in roms/", True, (90, 90, 90)
                )
                hint2_rect = hint2_surf.get_rect(
                    centerx=self.width // 2, top=btn_rect.bottom + 3
                )
                surf.blit(hint2_surf, hint2_rect)
            else:
                menu_button.draw(surf, self.font)

            hint_text = "< > Change Game    ^ v Scroll Menu"
            try:
                hint_font = pygame.font.Font(FONT_PATH, 8)
            except Exception:
                hint_font = pygame.font.SysFont(None, 14)
            hint_surf = hint_font.render(hint_text, True, (150, 150, 150))
            hint_rect = hint_surf.get_rect(
                centerx=self.width // 2, bottom=self.height - 5
            )
            surf.blit(hint_surf, hint_rect)

            if self.emulator and self.emulator.loaded and not self.emulator_active:
                self._draw_resume_banner(surf)

        self._draw_notification(surf)

        if self._achievement_notification:
            self._achievement_notification.draw(surf)

    def dim_screen(self, alpha=128):
        """
        Dim the game screen by drawing a semi-transparent black overlay.
        If alpha is 0 or less, remove the overlay (destroy surface).
        """
        if not hasattr(self, '_dim_overlay'):
            self._dim_overlay = None
        if alpha > 0:
            self._dim_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self._dim_overlay.fill((0, 0, 0, alpha))
            target_surface = self.scaler.get_surface() if self.scaler else self._loading_screen
            if target_surface:
                target_surface.blit(self._dim_overlay, (0, 0))
                if self.scaler:
                    self.scaler.blit_scaled()
                else:
                    pygame.display.flip()
        else:
            self._dim_overlay = None

    def cleanup(self):
        """Cleanup resources when closing the game screen"""
        if self.emulator:
            try:
                self.emulator.shutdown()
            except Exception as e:
                print(f"[Sinew] Cleanup error: {e}")
            self.emulator = None

        if hasattr(self, 'emulator_manager') and self.emulator_manager and self.emulator_manager.is_running:
            self.emulator_manager.terminate()
