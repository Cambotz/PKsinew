#!/usr/bin/env python3
"""
pcbox_data.py — Data management, navigation, mouse, and pause-combo mixin for PCBox.

Extracted from pc_box.py. Provides PCBoxDataMixin.
"""

import os
import sys

import pygame

from config import POKEMON_DB_PATH, SETTINGS_FILE
from controller import NavigableList
from ui_components import scale_surface_preserve_aspect


class PCBoxDataMixin:
    """Mixin providing data management, navigation, mouse handling, and pause combo for PCBox."""

    # ------------------------------------------------------------------ #
    #  Pause combo                                                         #
    # ------------------------------------------------------------------ #

    def _load_pause_combo_setting(self):
        """Load pause combo setting from sinew_settings.json"""
        import json
        default = {"type": "combo", "buttons": ["START", "SELECT"]}
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    if "pause_combo" in settings:
                        return settings["pause_combo"]
        except Exception:
            pass
        return default

    def _check_pause_combo(self, ctrl):
        """
        Check if the configured pause combo is held (controller combo OR keyboard MENU key).
        No hold timer - triggers immediately with debounce handled by caller.

        Returns:
            bool: True if combo/key is currently pressed
        """
        combo_held = False

        try:
            if ctrl._is_button_pressed("MENU"):
                combo_held = True
        except Exception:
            pass

        if not combo_held:
            setting = self._load_pause_combo_setting()

            if setting.get("type") == "custom":
                custom_btn = setting.get("button")
                if custom_btn is not None:
                    try:
                        if pygame.joystick.get_count() > 0:
                            joy = pygame.joystick.Joystick(0)
                            joy.init()
                            if custom_btn < joy.get_numbuttons():
                                combo_held = joy.get_button(custom_btn)
                    except Exception:
                        pass
            else:
                required_buttons = setting.get("buttons", ["START", "SELECT"])
                try:
                    all_pressed = all(
                        ctrl._is_button_pressed(btn) for btn in required_buttons
                    )
                    combo_held = all_pressed
                except Exception:
                    combo_held = False

        return combo_held

    def _get_pause_combo_name(self):
        """Get human-readable name for the pause combo"""
        setting = self._pause_combo_setting
        if setting.get("type") == "custom":
            return f"Button {setting.get('button', '?')}"
        buttons = setting.get("buttons", ["START", "SELECT"])
        return "+".join(buttons)

    def _get_running_game_name(self):
        """Get the name of the currently running/paused game"""
        if self.is_game_running_callback:
            return self.is_game_running_callback()
        return None

    # ------------------------------------------------------------------ #
    #  Data management                                                     #
    # ------------------------------------------------------------------ #

    def _is_sinew_mode(self):
        """Check if we're currently viewing Sinew (cross-game storage)"""
        if self.get_current_game_callback:
            current_game = self.get_current_game_callback()
            return current_game == "Sinew"
        return False

    def is_sinew_storage(self):
        """Public method to check if currently in Sinew storage mode"""
        return self.sinew_mode

    def _get_current_save_path(self):
        """Get the save file path for the current game (non-Sinew)"""
        if self.manager and hasattr(self.manager, "current_save_path"):
            return self.manager.current_save_path
        return None

    def _update_sinew_mode(self):
        """Update Sinew mode state after game change"""
        was_sinew = self.sinew_mode
        self.sinew_mode = self._is_sinew_mode()

        if self.sinew_mode != was_sinew:
            self.box_index = 0
            self.sinew_scroll_offset = 0
            self.grid_selected = 0
            self.grid_nav = NavigableList(30, columns=6, wrap=False)

            if self.sinew_mode:
                self.box_names = [f"STORAGE {i+1}" for i in range(20)]
                self.max_boxes = 20
            else:
                self.box_names = [f"BOX {i+1}" for i in range(14)]
                self.max_boxes = 14

    def get_box_name(self, box_index):
        """Get the name for a specific box"""
        if self.sinew_mode:
            return f"STORAGE {box_index + 1}"
        return f"BOX {box_index + 1}"

    def refresh_data(self):
        """Refresh Pokemon data from save file or Sinew storage"""
        if self.sprite_cache:
            self.sprite_cache.clear()

        self._update_sinew_mode()

        if self.sinew_mode:
            if self.sinew_storage and self.sinew_storage.is_loaded():
                self.current_box_data = self.sinew_storage.get_box(self.box_index + 1)
                self.party_data = []

                for poke in self.current_box_data:
                    if poke and not poke.get("species_name"):
                        self._enrich_pokemon_data(poke)

                pokemon_count = sum(1 for p in self.current_box_data if p is not None)
                print(
                    f"[PCBox] Sinew Storage {self.box_index + 1}: {pokemon_count} Pokemon",
                    file=sys.stderr,
                    flush=True,
                )
            else:
                self.current_box_data = [None] * 120
                self.party_data = []
                print("[PCBox] Sinew storage not loaded!", file=sys.stderr, flush=True)
        else:
            save_path = getattr(self.manager, "current_save_path", None)
            if save_path and os.path.exists(save_path):
                if getattr(self, "_skip_reload", False):
                    print(
                        "[PCBox] Skipping reload (fresh parser already set)",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    try:
                        from parser.gen3_parser import Gen3SaveParser
                        fresh_parser = Gen3SaveParser()
                        fresh_parser.load(
                            save_path, game_hint=self.get_current_game() or None
                        )
                        self.manager.parser = fresh_parser
                        self.manager.loaded = fresh_parser.loaded
                        print(
                            f"[PCBox] Reloaded save from disk: {save_path}",
                            file=sys.stderr,
                            flush=True,
                        )
                    except Exception as e:
                        print(
                            f"[PCBox] Error reloading save: {e}",
                            file=sys.stderr,
                            flush=True,
                        )

            if self.manager.is_loaded():
                self.current_box_data = self.manager.get_box(self.box_index + 1)
                self.party_data = self.manager.get_party()

                pokemon_count = sum(
                    1 for p in self.current_box_data if p and p.get("species", 0) > 0
                )
                print(
                    f"[PCBox] Box {self.box_index + 1}: {pokemon_count} Pokemon",
                    file=sys.stderr,
                    flush=True,
                )
            else:
                self.current_box_data = []
                self.party_data = []
                print("[PCBox] Manager not loaded!", file=sys.stderr, flush=True)

    def _enrich_pokemon_data(self, pokemon):
        """Add species_name to Pokemon data if missing"""
        if not pokemon or pokemon.get("species_name"):
            return

        species_id = pokemon.get("species", 0)
        if species_id == 0:
            return

        try:
            import json
            if os.path.exists(POKEMON_DB_PATH):
                with open(POKEMON_DB_PATH, "r", encoding="utf-8") as f:
                    db = json.load(f)
                species_key = str(species_id).zfill(3)
                if species_key in db:
                    pokemon["species_name"] = db[species_key].get(
                        "name", f"#{species_id}"
                    )
                else:
                    pokemon["species_name"] = f"#{species_id}"
        except Exception:
            pokemon["species_name"] = f"#{species_id}"

    def get_pokemon_at_grid_slot(self, grid_index):
        """
        Get Pokemon at a specific grid slot.
        For Sinew mode, accounts for scroll offset.
        """
        if self.sinew_mode:
            actual_index = grid_index + (self.sinew_scroll_offset * 6)
            if 0 <= actual_index < len(self.current_box_data):
                return self.current_box_data[actual_index]
            return None
        if 0 <= grid_index < len(self.current_box_data):
            return self.current_box_data[grid_index]
        return None

    # ------------------------------------------------------------------ #
    #  Box navigation                                                      #
    # ------------------------------------------------------------------ #

    def prev_box(self):
        """Navigate to the previous box."""
        max_boxes = 20 if self.sinew_mode else 14
        self.box_index = (self.box_index - 1) % max_boxes
        self.box_button.text = self.get_box_name(self.box_index)
        self.sinew_scroll_offset = 0
        self.refresh_data()
        self.selected_pokemon = None

    def next_box(self):
        """Navigate to the next box."""
        max_boxes = 20 if self.sinew_mode else 14
        self.box_index = (self.box_index + 1) % max_boxes
        self.box_button.text = self.get_box_name(self.box_index)
        self.sinew_scroll_offset = 0
        self.refresh_data()
        self.selected_pokemon = None

    def scroll_sinew_up(self):
        """Scroll Sinew storage view up"""
        if self.sinew_mode and self.sinew_scroll_offset > 0:
            self.sinew_scroll_offset -= 1
            return True
        return False

    def scroll_sinew_down(self):
        """Scroll Sinew storage view down"""
        if self.sinew_mode:
            max_scroll = self.sinew_total_rows - self.sinew_visible_rows
            if self.sinew_scroll_offset < max_scroll:
                self.sinew_scroll_offset += 1
                return True
        return False

    # ------------------------------------------------------------------ #
    #  Game navigation                                                     #
    # ------------------------------------------------------------------ #

    def change_game(self, delta):
        """Change the current game and reload save data"""
        print("\n[PCBox] ===== GAME SWITCH =====", file=sys.stderr, flush=True)

        if self.prev_game_callback and delta < 0:
            self.prev_game_callback()
        elif self.next_game_callback and delta > 0:
            self.next_game_callback()

        new_game = self.get_current_game()
        print(f"[PCBox] Switched to: {new_game}", file=sys.stderr, flush=True)

        was_sinew = self.sinew_mode
        self.sinew_mode = new_game == "Sinew"

        if self.sinew_mode:
            print(
                "[PCBox] Sinew mode activated - using Sinew storage",
                file=sys.stderr,
                flush=True,
            )
            if not was_sinew:
                self.box_index = 0
                self.sinew_scroll_offset = 0
                self.box_names = [f"STORAGE {i+1}" for i in range(20)]
                self.max_boxes = 20
        else:
            new_path = getattr(self.manager, "current_save_path", None)
            print(f"[PCBox] Save path: {new_path}", file=sys.stderr, flush=True)

            if new_path:
                print(
                    f"[PCBox] File mtime: {os.path.getmtime(new_path)}",
                    file=sys.stderr,
                    flush=True,
                )

                from parser.gen3_parser import Gen3SaveParser
                fresh_parser = Gen3SaveParser()
                fresh_parser.load(new_path, game_hint=new_game)

                self.manager.parser = fresh_parser
                self.manager.loaded = fresh_parser.loaded
                self.manager.current_save_path = new_path

                print("[PCBox] Created fresh parser", file=sys.stderr, flush=True)

            if was_sinew:
                self.box_index = 0
                self.box_names = [f"BOX {i+1}" for i in range(14)]
                self.max_boxes = 14

        self.current_box_data = []
        self.party_data = []
        self.selected_pokemon = None
        self.sinew_scroll_offset = 0

        self.refresh_data()
        self.update_game_button_text()
        self.box_button.text = self.get_box_name(self.box_index)
        print("[PCBox] ===== SWITCH DONE =====\n", file=sys.stderr, flush=True)

    def get_current_game(self):
        """Get the current game name"""
        if self.get_current_game_callback:
            return self.get_current_game_callback()
        return "Unknown"

    def is_current_game_running(self):
        """Check if the currently displayed game is running in the emulator"""
        if self.is_game_running_callback:
            running_game = self.is_game_running_callback()
            if running_game:
                current_game = self.get_current_game()
                return running_game == current_game
        return False

    def update_game_button_text(self):
        """Update the game button to show current game"""
        self.game_button.text = self.get_current_game()

    # ------------------------------------------------------------------ #
    #  Sprite                                                              #
    # ------------------------------------------------------------------ #

    def set_sprite(self, path):
        """Load and scale a sprite image from the given path."""
        if not path or not os.path.exists(path):
            self.current_sprite_image = None
            return
        img = pygame.image.load(path).convert_alpha()
        img = scale_surface_preserve_aspect(
            img, int(self.sprite_area.width - 4), int(self.sprite_area.height - 4)
        )
        self.current_sprite_image = img

    # ------------------------------------------------------------------ #
    #  Party panel                                                         #
    # ------------------------------------------------------------------ #

    def toggle_party_panel(self):
        """Show or hide the party panel slide-in."""
        if self.sinew_mode:
            return

        self.party_panel_open = not self.party_panel_open
        if self.party_panel_open:
            self.party_panel_target_y = 0
            self.party_selected = 0
            self._update_party_selection()
        else:
            self.party_panel_target_y = -self.height

    # ------------------------------------------------------------------ #
    #  Mouse handling                                                      #
    # ------------------------------------------------------------------ #

    def handle_mouse(self, event):
        """Handle mouse events for buttons, party panel, and grid slots."""
        consumed = False
        for btn in [self.party_button, self.close_button]:
            btn.handle_event(event)
            if btn.rect.collidepoint(pygame.mouse.get_pos()):
                consumed = True

        if self.party_panel_open:
            panel_slots = self.get_party_slot_rects()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, slot in enumerate(panel_slots):
                    if slot.collidepoint(event.pos):
                        if i < len(self.party_data):
                            poke = self.party_data[i]
                            self.selected_pokemon = poke
                            self.party_selected = i
                        consumed = True

        if not self.party_panel_open:
            for btn in [
                self.left_game_arrow,
                self.game_button,
                self.right_game_arrow,
                self.left_box_arrow,
                self.box_button,
                self.right_box_arrow,
            ]:
                btn.handle_event(event)
                if btn.rect.collidepoint(pygame.mouse.get_pos()):
                    consumed = True

            if event.type == pygame.MOUSEBUTTONDOWN:
                grid_rects = self.get_grid_rects()
                for i, rect in enumerate(grid_rects):
                    if rect.collidepoint(event.pos):
                        poke = self.get_pokemon_at_grid_slot(i)
                        self.grid_nav.set_selected(i)
                        if poke and not poke.get("empty"):
                            self.selected_pokemon = poke
                            print(
                                f"Selected box Pokemon: {self.manager.format_pokemon_display(poke)}"
                            )
                        consumed = True
                        break

        return consumed

    # ------------------------------------------------------------------ #
    #  Rect helpers                                                        #
    # ------------------------------------------------------------------ #

    def get_party_slot_rects(self, inner_y=None, inner_height=None):
        """Return pygame.Rect list for each party slot in the panel."""
        slot_margin = 8
        panel_rect = self.party_panel_rect
        inner_y = inner_y or panel_rect.y
        inner_height = inner_height or panel_rect.height

        base_w = (panel_rect.width - slot_margin * 4) / 3
        base_h = (inner_height - slot_margin * 6) / 6
        slot_size = min(base_w, base_h) * self.party_slot_scale

        panel_cy = inner_y + inner_height / 2

        left_slot_rect = pygame.Rect(
            panel_rect.x + slot_margin + self.party_slot_x_offset,
            panel_cy - slot_size / 2,
            slot_size,
            slot_size,
        )

        right_slots = []
        right_x = left_slot_rect.right + slot_margin
        total_right_h = 5 * slot_size + 4 * slot_margin
        start_y = panel_cy - total_right_h / 2

        for i in range(5):
            slot = pygame.Rect(
                right_x, start_y + i * (slot_size + slot_margin), slot_size, slot_size
            )
            right_slots.append(slot)

        return [left_slot_rect] + right_slots

    def get_grid_rects(self):
        """Get all grid cell rectangles for the current box"""
        cell_w = (self.grid_rect.width - (self.grid_cols - 1)) / self.grid_cols
        cell_h = (self.grid_rect.height - (self.grid_rows - 1)) / self.grid_rows
        cell_size = min(cell_w, cell_h) * 1.1

        total_width = self.grid_cols * cell_size + (self.grid_cols - 1)
        grid_start_x = self.box_button.rect.centerx - total_width / 2
        grid_start_y = self.grid_rect.y - 10

        rects = []
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                rect = pygame.Rect(
                    grid_start_x + c * (cell_size + 1),
                    grid_start_y + r * (cell_size + 1),
                    cell_size,
                    cell_size,
                )
                rects.append(rect)

        return rects
