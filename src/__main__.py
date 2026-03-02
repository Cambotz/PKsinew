#!/usr/bin/env python3

"""
__main__.py — Standalone entry point for PKsinew. Imports GameScreen from game_screen.py
    and runs the game loop.
"""

import os
import sys

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

    VIRTUAL_WIDTH = 480
    VIRTUAL_HEIGHT = 320

    WINDOW_WIDTH = 960
    WINDOW_HEIGHT = 640

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
    font = pygame.font.Font(FONT_PATH, 18)
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
            if not game_screen.emulator_manager.is_running:
                pygame.display.flip()
            continue

        # Handheld: reinitialise display if it was lost
        if IS_HANDHELD and not pygame.display.get_surface():
            scaler.reinit_display()
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

        screen = scaler.get_surface()
        game_screen.draw(screen)
        scaler.blit_scaled()

        game_screen.dim_screen(180 if (game_screen.emulator_manager
            and game_screen.emulator_manager.is_running) else 0)

    game_screen.cleanup()
    pygame.quit()


if __name__ == '__main__':
    run()
