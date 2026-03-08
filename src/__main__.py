#!/usr/bin/env python3

"""
__main__.py — Standalone entry point for PKsinew. Imports GameScreen from game_screen.py
    and runs the game loop.
"""

import os
import sys

# CRITICAL: SDL2 preload for ARM Linux handhelds (must be FIRST, before any imports)
# 
# PortMaster's pm_platform_helper may set LD_PRELOAD with system SDL2. If so, use that.
# Otherwise, manually preload system SDL2 for KMSDRM/Mali GPU support on handhelds.
# This prevents segfaults from pygame's bundled SDL2 which lacks device drivers.
#
# Skip preloading if:
# - LD_PRELOAD already contains libSDL2 (PortMaster already handled it)
# - Not on ARM Linux (desktop/Windows/Mac don't need this)
if 'LD_PRELOAD' not in os.environ or 'libSDL2' not in os.environ.get('LD_PRELOAD', ''):
    import platform as _platform
    if sys.platform == 'linux' and _platform.machine().lower() in ('aarch64', 'arm64', 'armv7l', 'armv6l'):
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
else:
    print(f'[Main] Using PortMaster preloaded SDL2 from LD_PRELOAD')

_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from sinew_logging import init_redirectors as _init_redirectors
_init_redirectors()

import pygame
from controller import get_controller
from scaler import Scaler
from config import FONT_PATH, IS_HANDHELD
from settings import load_sinew_settings as load_settings
from game_screen import GameScreen
from ui_scale import init_ui_scale


def run():
    """Initialize pygame, apply theme, build the scaled game window, and start the main event loop."""
    pygame.init()

    try:
        pygame.mixer.pre_init(frequency=32768, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        print(f"[Main] Mixer pre-initialized: {pygame.mixer.get_init()}")
    except Exception as e:
        print(f"[Main] Mixer pre-init failed: {e}")

    try:
        from theme_manager import load_theme_preference
        load_theme_preference()
        print("[Main] Theme preference loaded")
    except Exception as e:
        print(f"[Main] Could not load theme preference: {e}")

    VIRTUAL_WIDTH = 640
    VIRTUAL_HEIGHT = 480

    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 960

    # Initialise resolution-independent UI scaling
    init_ui_scale(VIRTUAL_WIDTH, VIRTUAL_HEIGHT)

    if IS_HANDHELD:
        start_fullscreen = True
    else:
        start_fullscreen = False
        try:
            settings = load_settings()
            start_fullscreen = settings.get("fullscreen", False)
        except Exception:
            pass

    scaler = Scaler(
        virtual_width=VIRTUAL_WIDTH,
        virtual_height=VIRTUAL_HEIGHT,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        fullscreen=start_fullscreen,
        integer_scaling=False,
    )
    screen = scaler.get_surface()
    clock = pygame.time.Clock()
    from ui_scale import scaled_font
    font = scaled_font(18)
    controller = get_controller()

    game_screen = GameScreen(
        VIRTUAL_WIDTH,
        VIRTUAL_HEIGHT,
        font,
        controller=controller,
        scaler=scaler,
        screen=screen,
    )
    game_screen.precache_all(screen)

    running = True
    while running:
        # While an emulator provider is running, just idle
        if game_screen.emulator_manager and game_screen.emulator_manager.is_running:
            pygame.time.wait(500)
            # On dual-screen systems (AYN Thor), display is iconified not quit
            # Only try to flip if display still exists (dual-screen case)
            try:
                if not game_screen.emulator_manager.is_running and pygame.display.get_surface():
                    pygame.display.flip()
            except pygame.error:
                # Display was quit for single-screen external emulator
                pass
            continue

        # Handheld: reinitialise display if it was lost
        if IS_HANDHELD:
            try:
                surf = pygame.display.get_surface()
                if not surf:
                    # Display was quit, make sure it's initialized then recreate window
                    if not pygame.display.get_init():
                        pygame.display.init()
                    scaler._create_window()
                    controller.resume()
            except pygame.error:
                # Display was quit for external emulator, reinit when it returns
                if not pygame.display.get_init():
                    pygame.display.init()
                scaler._create_window()
                controller.resume()

        dt = clock.tick(60)
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.VIDEORESIZE:
                scaler.handle_resize(event.w, event.h)
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    scaler.toggle_fullscreen()
                elif event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT):
                    scaler.toggle_fullscreen()

            # Scale mouse coordinates to virtual resolution
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                event.pos = scaler.scale_mouse(event.pos)

            controller.process_event(event)

        controller.update(dt)
        filtered_events = controller.filter_kb_events(events)

        if game_screen.should_close:
            running = False
            continue

        if not game_screen.update(filtered_events, dt):
            running = False

        # Don't try to draw if display was quit for external emulator
        try:
            screen = scaler.get_surface()
            if screen:
                game_screen.draw(screen)
                scaler.blit_scaled()

                game_screen.dim_screen(180 if (game_screen.emulator_manager
                    and game_screen.emulator_manager.is_running) else 0)
        except pygame.error:
            # Display was quit, skip drawing until it's reinitialized
            pass

    game_screen.cleanup()
    pygame.quit()


if __name__ == '__main__':
    run()