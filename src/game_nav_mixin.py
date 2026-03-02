#!/usr/bin/env python3

"""
game_nav_mixin.py — game selection, navigation, GIF loading, and menu helpers for GameScreen.

Covers:
  - Game init and detection  (_init_games, refresh_games)
  - GIF pre-caching          (precache_all, _ensure_gif_loaded, _draw_loading_screen)
  - Game navigation          (change_game, load_game_and_background, _change_game_*)
  - Menu helpers             (is_on_sinew, get_menu_items, get_current_game_*)
  - Events gate logic        (_is_events_unlocked_for_current_game, _save_matches_game,
                              _get_events_unlock_achievement_id, _get_running_game_name)
  - Input debounce           (_can_accept_input)
"""

import builtins
import os
import time

import pygame
from PIL import Image

from config import ROMS_DIR, SAVES_DIR, SPRITES_DIR
from game_detection import (
    GAME_DEFINITIONS,
    GAME_FULL,
    GAME_SAVE_ONLY,
    GAME_UNAVAILABLE,
    detect_games_with_dirs,
    get_game_availability,
)
from save_data_manager import get_manager


def _load_gif_frames(path, width, height):
    """Load GIF frames scaled to specified size (module-level helper)."""
    from PIL import ImageSequence
    import pygame as _pg

    frames, durations = [], []
    if not path or not os.path.exists(path):
        return frames, durations
    try:
        pil_img = Image.open(path)
        for frame in ImageSequence.Iterator(pil_img):
            frame = frame.convert("RGBA").resize((width, height), Image.NEAREST)
            data = frame.tobytes()
            surf = _pg.image.fromstring(data, frame.size, frame.mode).convert_alpha()
            frames.append(surf)
            durations.append(frame.info.get("duration", 100))
        pil_img.close()
    except Exception as e:
        print(f"Failed to open GIF {path}: {e}")
    return frames, durations


# Menu item lists (referenced by get_menu_items)
_GAME_MENU_ITEMS = [
    "Launch Game",
    "Pokedex",
    "Trainer Info",
    "PC Box",
    "Achievements",
    "Events",
    "Settings",
    "Export",
]
_SINEW_MENU_ITEMS = ["Pokedex", "PC Box", "Achievements", "Settings"]


class GameNavMixin:
    """Mixin providing game navigation and GIF-loading helpers to GameScreen."""

    # ------------------------------------------------------------------ #
    # Menu helpers                                                         #
    # ------------------------------------------------------------------ #

    def is_on_sinew(self):
        """Check if currently on Sinew (combined view)"""
        return self.get_current_game_name() == "Sinew"

    def get_menu_items(self):
        """Get menu items for current screen (Sinew vs individual game)"""
        if self.is_on_sinew():
            items = list(_SINEW_MENU_ITEMS)
            if self.emulator and self.emulator.loaded:
                items.insert(0, "Stop Game")
            items.append("Quit Sinew")
            return items

        # Game-specific menu
        items = []
        current_game = self.game_names[self.current_game]
        running_game = self._get_running_game_name()
        availability = self.get_current_game_availability()

        if running_game and running_game == current_game:
            items.append("Resume Game")
            items.append("Stop Game")
        elif running_game:
            items.append(f"Playing: {running_game}")
            items.append("Stop Game")
        elif availability == GAME_SAVE_ONLY:
            items.append("Save File Only")
        else:
            items.append("Launch Game")

        for item in _GAME_MENU_ITEMS:
            if item == "Launch Game":
                continue
            if item == "Events":
                if not self._is_events_unlocked_for_current_game():
                    continue
            items.append(item)

        items.append("Quit Sinew")
        return items

    def get_current_game_name(self):
        """Get current game name"""
        return self.game_names[self.current_game] if self.game_names else "Unknown"

    def get_current_game_availability(self):
        """Return the availability state of the currently selected game."""
        gname = self.get_current_game_name()
        if gname in self.games:
            return self.games[gname].get("availability", GAME_FULL)
        return GAME_FULL

    # ------------------------------------------------------------------ #
    # Events gate                                                          #
    # ------------------------------------------------------------------ #

    def _is_events_unlocked_for_current_game(self):
        """
        Check if Events menu should be shown for current game.

        RSE  (Ruby / Sapphire / Emerald):
            Requires the 'Pokemon Champion!' achievement reward to be claimed
            (i.e. player has all 8 badges and has collected that reward).

        FRLG (FireRed / LeafGreen):
            Requires the 'Sevii Pokemon Ranger' achievement reward to be claimed
            (i.e. player has the National Dex AND Rainbow Pass and collected that reward).
            Badge count is NOT used as the gate for FRLG.
        """
        current_game = self.get_current_game_name()
        if not current_game or current_game == "Sinew":
            return False

        is_frlg = current_game in ("FireRed", "LeafGreen")

        if is_frlg:
            if self._achievement_manager:
                events_ach_id = self._get_events_unlock_achievement_id(current_game)
                if events_ach_id:
                    if not self._achievement_manager.is_unlocked(events_ach_id):
                        return False
                    if not self._achievement_manager.is_reward_claimed(events_ach_id):
                        return False
            return True
        else:
            # RSE: gate on 8 badges (Pokemon Champion).
            badge_count = 0
            if self._achievement_manager:
                badge_count = self._achievement_manager.get_tracking(
                    "badges", default=0, game_name=current_game
                )

            if badge_count == 0:
                manager = get_manager()
                if manager and manager.is_loaded():
                    loaded_game = getattr(
                        getattr(manager, "parser", None), "game_name", None
                    )
                    if loaded_game and self._save_matches_game(
                        loaded_game, current_game
                    ):
                        try:
                            badges = manager.get_badges()
                            badge_count = sum(1 for b in badges if b)
                        except Exception:
                            pass

            if badge_count < 8:
                return False

            if self._achievement_manager:
                events_ach_id = self._get_events_unlock_achievement_id(current_game)
                if events_ach_id and not self._achievement_manager.is_reward_claimed(
                    events_ach_id
                ):
                    return False

            return True

    def _save_matches_game(self, loaded_game_name, expected_game_name):
        """
        Check if the parser's reported game_name matches the expected game.
        Handles paired parser names like 'FireRed/LeafGreen' and 'Ruby/Sapphire'.
        """
        if not loaded_game_name or not expected_game_name:
            return False
        if loaded_game_name == expected_game_name:
            return True
        if expected_game_name in loaded_game_name:
            return True
        return False

    def _get_events_unlock_achievement_id(self, game_name):
        """
        Return the achievement ID whose reward_claimed flag gates Events access.

        RSE  → _028  (Pokemon Champion!)
        FRLG → _057  (Sevii Pokemon Ranger — National Dex + Rainbow Pass)
        """
        prefix_map = {
            "Ruby": "RUBY",
            "Sapphire": "SAPP",
            "Emerald": "EMER",
            "FireRed": "FR",
            "LeafGreen": "LG",
        }
        prefix = prefix_map.get(game_name)
        if not prefix:
            return None
        if game_name in ("FireRed", "LeafGreen"):
            return f"{prefix}_057"
        return f"{prefix}_028"

    def _get_running_game_name(self):
        """Get the name of the currently running game, or None if no game is running."""
        if self.emulator and self.emulator.loaded and self.emulator.rom_path:
            rom_path = self.emulator.rom_path
            rom_name_lower = os.path.basename(rom_path).lower()

            for game_key, game_def in GAME_DEFINITIONS.items():
                keywords = game_def.get("keywords", [])
                exclude = game_def.get("exclude", [])

                excluded = any(ex.lower() in rom_name_lower for ex in exclude)
                if excluded:
                    continue

                for keyword in keywords:
                    if keyword.lower() in rom_name_lower:
                        return game_key

            return os.path.splitext(os.path.basename(rom_path))[0]
        return None

    # ------------------------------------------------------------------ #
    # Game init                                                            #
    # ------------------------------------------------------------------ #

    def _init_games(self):
        """Initialize game data and load GIFs"""
        # Re-detect games in case ROMs were added
        # Use a module-level reference so callers importing GAMES see the update
        import game_detection as _gd

        roms_dir = ROMS_DIR
        saves_dir = SAVES_DIR

        if (
            self.emulator_manager
            and self.emulator_manager.active_provider
            and not getattr(self.emulator_manager.active_provider, "is_integrated", False)
        ):
            provider = self.emulator_manager.active_provider
            ext_roms_dir = getattr(provider, "roms_dir", None)
            ext_saves_dir = getattr(provider, "saves_dir", None)

            if ext_roms_dir:
                roms_dir = ext_roms_dir
                print(f"[EmulatorManager] Scanning external ROMs: {roms_dir}")
            if ext_saves_dir:
                saves_dir = ext_saves_dir
                print(f"[EmulatorManager] Scanning external saves: {saves_dir}")

        _gd.GAMES = detect_games_with_dirs(roms_dir, saves_dir)

        self.games = {}

        for gname, g in _gd.GAMES.items():
            game_data = g.copy()

            g_conf = self.settings.get(gname, {})
            if "rom" in g_conf:
                game_data["rom"] = g_conf["rom"]
            if "sav" in g_conf:
                game_data["sav"] = g_conf["sav"]

            availability = get_game_availability(game_data)
            game_data["availability"] = availability

            if availability == GAME_UNAVAILABLE:
                print(f"[GameScreen] Hiding {gname}: no ROM and no save found")
                continue

            game_data["frames"] = None
            game_data["durations"] = None
            game_data["frame_index"] = 0
            game_data["time_accum"] = 0
            game_data["loaded"] = False

            self.games[gname] = game_data

        self.game_names = list(self.games.keys())

        full_games = [
            g for g in self.game_names
            if g != "Sinew" and self.games[g].get("availability") == GAME_FULL
        ]
        save_only = [
            g for g in self.game_names
            if g != "Sinew" and self.games[g].get("availability") == GAME_SAVE_ONLY
        ]

        if full_games:
            print(f"[GameScreen] Detected games (full): {', '.join(full_games)}")
        if save_only:
            print(f"[GameScreen] Save-only games (no ROM): {', '.join(save_only)}")
        if not full_games and not save_only:
            print("[GameScreen] No ROMs or saves detected in roms/ and saves/ folders")

        # Load Sinew background image
        self.sinew_logo = None
        self.sinew_bg_color = (255, 255, 255)
        sinew_logo_path = os.path.join(SPRITES_DIR, "title", "PKSINEW.png")
        if os.path.exists(sinew_logo_path):
            try:
                pil_img = Image.open(sinew_logo_path)
                pil_img = pil_img.convert("RGBA").resize(
                    (self.width, self.height), Image.NEAREST
                )
                data = pil_img.tobytes()
                self.sinew_logo = pygame.image.fromstring(
                    data, pil_img.size, pil_img.mode
                ).convert_alpha()
                pil_img.close()
            except Exception as e:
                print(f"Failed to load Sinew background: {e}")

    def refresh_games(self):
        """Re-detect games (call if ROMs were added/removed)"""
        current_game_name = (
            self.game_names[self.current_game] if self.game_names else "Sinew"
        )

        self._init_games()

        if current_game_name in self.game_names:
            self.current_game = self.game_names.index(current_game_name)
        else:
            self.current_game = 0

        print("[GameScreen] Games refreshed")

    # ------------------------------------------------------------------ #
    # GIF loading / pre-caching                                           #
    # ------------------------------------------------------------------ #

    def _ensure_gif_loaded(self, gname):
        """Lazy load GIF for a game"""
        game_data = self.games[gname]
        if not game_data["loaded"]:
            gif_path = game_data.get("title_gif")
            if gif_path and os.path.exists(gif_path):
                frames, durations = _load_gif_frames(gif_path, self.width, self.height)
                game_data["frames"] = frames
                game_data["durations"] = durations
            else:
                game_data["frames"] = []
                game_data["durations"] = []
            game_data["loaded"] = True

    def precache_all(self, screen=None):
        """
        Pre-load all GIF backgrounds.
        Save files are loaded lazily when needed (on-demand by SaveDataManager).
        Call this during startup to eliminate lag when switching games.

        Args:
            screen: Optional pygame surface to draw loading progress on
        """
        if self._precached:
            return

        total_items = sum(
            1 for _, gd in self.games.items() if gd.get("title_gif")
        )
        current_item = 0

        for gname, game_data in self.games.items():
            gif_path = game_data.get("title_gif")
            if gif_path and os.path.exists(gif_path):
                if screen:
                    self._draw_loading_screen(
                        screen,
                        f"Loading {gname} background...",
                        current_item,
                        total_items,
                    )
                if not game_data.get("loaded"):
                    frames, durations = _load_gif_frames(
                        gif_path, self.width, self.height
                    )
                    game_data["frames"] = frames
                    game_data["durations"] = durations
                    game_data["loaded"] = True
                current_item += 1

        self._precached = True

        if screen:
            self._draw_loading_screen(screen, "Ready!", total_items, total_items)
            pygame.time.wait(200)

    def _draw_loading_screen(self, screen, message, current, total):
        """Draw a loading screen with progress bar"""
        if screen is None:
            return
        screen.fill((30, 30, 40))

        title_font = self.font
        title = title_font.render("Sinew", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.width // 2, self.height // 3))
        screen.blit(title, title_rect)

        msg = title_font.render(message, True, (200, 200, 200))
        msg_rect = msg.get_rect(center=(self.width // 2, self.height // 2))
        screen.blit(msg, msg_rect)

        bar_width = int(self.width * 0.6)
        bar_height = 20
        bar_x = (self.width - bar_width) // 2
        bar_y = int(self.height * 0.6)

        pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_width, bar_height))

        if total > 0:
            fill_width = int((current / total) * bar_width)
            pygame.draw.rect(
                screen, (100, 200, 100), (bar_x, bar_y, fill_width, bar_height)
            )

        pygame.draw.rect(
            screen, (100, 100, 120), (bar_x, bar_y, bar_width, bar_height), 2
        )

        progress_text = title_font.render(f"{current}/{total}", True, (150, 150, 150))
        progress_rect = progress_text.get_rect(
            center=(self.width // 2, bar_y + bar_height + 20)
        )
        screen.blit(progress_text, progress_rect)

        if self.scaler:
            self.scaler.blit_scaled()
        else:
            pygame.display.flip()

    # ------------------------------------------------------------------ #
    # Input debounce                                                       #
    # ------------------------------------------------------------------ #

    def _can_accept_input(self):
        """Check if enough time has passed since last input (debouncing)"""
        current_time = time.time()
        if current_time - self._last_input_time >= self.INPUT_COOLDOWN:
            self._last_input_time = current_time
            return True
        return False

    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #

    def change_game(self, delta):
        """Switch to next/previous game index only"""
        if len(self.game_names) == 0:
            return
        self.current_game = (self.current_game + delta) % len(self.game_names)

    def load_game_and_background(self):
        """
        Load the save and GIF background for the current game.
        Resets GIF animation state so the new game's background starts from frame 0.
        """
        self._load_current_save()

        gname = self.game_names[self.current_game]
        self._ensure_gif_loaded(gname)

        game_data = self.games[gname]
        game_data["frame_index"] = 0
        game_data["time_accum"] = 0

    def _change_game_and_reload(self, delta):
        """Helper: change index then reload save + background"""
        if not self._can_accept_input():
            return
        self.change_game(delta)
        self.load_game_and_background()
        self.menu_index = 0

    def _change_game_skip_sinew(self, delta):
        """Change game but skip Sinew (index 0) - used by PC Box"""
        if not self._can_accept_input():
            return
        self._change_game_skip_sinew_no_debounce(delta)

    def _change_game_skip_sinew_no_debounce(self, delta):
        """Change game but skip Sinew - with built-in cooldown for modal use"""
        if len(self.game_names) <= 1:
            return

        current_time = pygame.time.get_ticks()
        if not hasattr(self, "_last_modal_game_switch"):
            self._last_modal_game_switch = 0

        if current_time - self._last_modal_game_switch < 800:
            return

        self._last_modal_game_switch = current_time

        for _ in range(len(self.game_names)):
            self.current_game = (self.current_game + delta) % len(self.game_names)
            if self.current_game != 0:
                break

        self.load_game_and_background()
        self.menu_index = 0

    def _change_game_include_sinew(self, delta):
        """Change game including Sinew - for Pokedex which can show combined view"""
        if len(self.game_names) <= 1:
            return
        self.current_game = (self.current_game + delta) % len(self.game_names)
        self.load_game_and_background()
        self.menu_index = 0

    def _set_game_by_name(self, game_name):
        """Set to a specific game by name and reload"""
        if game_name in self.game_names:
            self.current_game = self.game_names.index(game_name)
            self.load_game_and_background()
            return True
        return False
