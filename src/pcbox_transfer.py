#!/usr/bin/env python3
"""
ui_pcbox_transfer.py — Move/transfer pipeline mixin for PCBox.

Extracted from pc_box.py. Provides PCBoxTransferMixin.

Usage
-----
    class PCBox(PCBoxDrawMixin, PCBoxInputMixin, PCBoxTransferMixin):
        ...

All methods call back into self.* for state (manager, sinew_storage, box_index,
sinew_scroll_offset, etc.) and other mixins (_show_warning, _cancel_move_mode,
_is_current_game_running, _track_sinew_achievement, _show_evolution_dialog*,
refresh_data, get_current_game, get_pokemon_at_grid_slot).
"""

import os
import sys

import pygame

from config import GEN3_NORMAL_DIR, GEN3_SHINY_DIR, get_egg_sprite_path
from ui_components import scale_surface_preserve_aspect

try:
    from save_writer import (
        clear_pc_slot,
        find_section_by_id,
        get_active_block,
        load_save_file,
        write_pokemon_to_pc,
        write_save_file,
    )
    SAVE_WRITER_AVAILABLE = True
except ImportError:
    SAVE_WRITER_AVAILABLE = False

try:
    from trade_evolution import can_evolve_by_trade
    TRADE_EVOLUTION_AVAILABLE = True
except ImportError:
    can_evolve_by_trade = None
    TRADE_EVOLUTION_AVAILABLE = False


class PCBoxTransferMixin:
    """Mixin providing the move/transfer pipeline for PCBox."""

    @staticmethod
    def _resolve_game_type(game_name):
        """
        Resolve a game name to the correct save-writer game_type.

        Returns 'RS', 'E', or 'FRLG' — never the collapsed 'RSE'.
        This ensures Emerald gets its own pocket offsets, event flag
        offsets, etc. rather than being lumped in with Ruby/Sapphire.
        """
        if not game_name:
            return "RS"
        if "Fire" in game_name or "Leaf" in game_name:
            return "FRLG"
        if "Emerald" in game_name:
            return "E"
        # Ruby, Sapphire, or unknown Hoenn game
        return "RS"

    # ------------------------------------------------------------------ #
    #  Move mode entry / exit                                              #
    # ------------------------------------------------------------------ #

    def _start_move_mode(self):
        """Start move mode with currently selected Pokemon"""
        if not self.selected_pokemon:
            return

        # Block moving eggs
        if self.selected_pokemon.get("egg"):
            self._show_warning("Cannot move eggs!")
            return

        # Sinew mode doesn't need save writer for internal moves
        if not self.sinew_mode and not SAVE_WRITER_AVAILABLE:
            print("Save writer not available - cannot move Pokemon")
            return

        # Check if current game is running - block moves from/to active game (not for Sinew)
        if not self.sinew_mode and self._is_current_game_running():
            self._show_warning("Game is running!\nStop game to move Pokemon")
            return

        self.move_mode = True
        self.moving_pokemon = self.selected_pokemon

        # Store source location with save path
        grid_index = self.grid_nav.get_selected()
        current_game = self.get_current_game()

        if self.sinew_mode:
            # Sinew storage - calculate actual slot with scroll offset
            actual_slot = grid_index + (self.sinew_scroll_offset * 6)
            self.moving_pokemon_source = {
                "type": "box",
                "box": self.box_index + 1,
                "slot": actual_slot,
                "game": "Sinew",
                "save_path": None,
            }
        elif self.party_panel_open:
            # Party moves are complex - require in-game withdrawal first
            self._show_warning("Cannot move from party.\nWithdraw to PC in-game first.")
            return
        else:
            current_save_path = getattr(self.manager, "current_save_path", None)
            self.moving_pokemon_source = {
                "type": "box",
                "box": self.box_index + 1,
                "slot": grid_index,
                "game": current_game,
                "save_path": current_save_path,
            }

        pokemon_name = self.moving_pokemon.get("nickname") or "Pokemon"
        print(
            f"[PCBox] Picked up {pokemon_name} from {current_game}",
            file=sys.stderr,
            flush=True,
        )

        # Load sprite for the moving Pokemon
        self._load_moving_sprite()

        pokemon_name = self.moving_pokemon.get("nickname") or self.moving_pokemon.get(
            "species_name", "Pokemon"
        )
        print(f"Move mode: Picked up {pokemon_name}")

    def _load_moving_sprite(self):
        """Load the sprite for the Pokemon being moved"""
        if not self.moving_pokemon:
            self.moving_sprite = None
            return

        sprite_path = self._get_pokemon_sprite_path(self.moving_pokemon)

        if sprite_path and os.path.exists(sprite_path):
            try:
                self.moving_sprite = pygame.image.load(sprite_path).convert_alpha()
                self.moving_sprite = scale_surface_preserve_aspect(
                    self.moving_sprite, 40, 40
                )
            except Exception as e:
                print(f"Failed to load moving sprite: {e}")
                self.moving_sprite = None
        else:
            self.moving_sprite = None

    def _get_pokemon_sprite_path(self, pokemon):
        """Get sprite path for a Pokemon (works for both game and Sinew storage Pokemon)"""
        if not pokemon or pokemon.get("empty"):
            return None

        if pokemon.get("egg"):
            egg_path = get_egg_sprite_path("gen3")
            if os.path.exists(egg_path):
                return egg_path
            return None

        species = pokemon.get("species", 0)
        if species == 0:
            return None

        shiny = self._is_pokemon_shiny(pokemon)
        species_str = str(species).zfill(3)
        sprite_folder = GEN3_SHINY_DIR if shiny else GEN3_NORMAL_DIR
        sprite_path = os.path.join(sprite_folder, f"{species_str}.png")

        if os.path.exists(sprite_path):
            return sprite_path
        return None

    def _is_pokemon_shiny(self, pokemon):
        """Check if a Pokemon is shiny"""
        if not pokemon or pokemon.get("empty") or pokemon.get("egg"):
            return False

        personality = pokemon.get("personality", 0)
        ot_id = pokemon.get("ot_id", 0)

        if personality == 0 or ot_id == 0:
            return False

        tid = ot_id & 0xFFFF
        sid = (ot_id >> 16) & 0xFFFF
        pid_low = personality & 0xFFFF
        pid_high = (personality >> 16) & 0xFFFF
        shiny_value = tid ^ sid ^ pid_low ^ pid_high

        return shiny_value < 8

    def _cancel_move_mode(self, reason="cancelled"):
        """Clear move mode state after a move completes or is cancelled."""
        self.move_mode = False
        self.moving_pokemon = None
        self.moving_pokemon_source = None
        self.moving_sprite = None
        print(f"[PCBox] Move mode cleared ({reason})")

    # ------------------------------------------------------------------ #
    #  Sinew internal move                                                 #
    # ------------------------------------------------------------------ #

    def _execute_sinew_move(self, dest_type, dest_box, dest_slot):  # pylint: disable=unused-argument
        """Execute a move within Sinew storage"""
        if not self.sinew_storage or not self.moving_pokemon:
            self._cancel_move_mode()
            return

        source_box = self.moving_pokemon_source.get("box", 1)
        source_slot = self.moving_pokemon_source.get("slot", 0)

        actual_dest_slot = dest_slot + (self.sinew_scroll_offset * 6)
        dest_box_num = self.box_index + 1

        print(
            f"[PCBox] Sinew move: Box {source_box} Slot {source_slot} "
            f"-> Box {dest_box_num} Slot {actual_dest_slot}",
            file=sys.stderr,
            flush=True,
        )

        dest_poke = self.sinew_storage.get_pokemon_at(dest_box_num, actual_dest_slot)
        source_poke_copy = self.moving_pokemon.copy() if self.moving_pokemon else None
        dest_poke_copy = dest_poke.copy() if dest_poke else None

        if dest_poke is not None:
            print("[PCBox] Swapping Pokemon", file=sys.stderr, flush=True)

        if self.sinew_storage.move_pokemon(
            source_box, source_slot, dest_box_num, actual_dest_slot
        ):
            print("[PCBox] Sinew move successful", file=sys.stderr, flush=True)

            self.undo_action = {
                "type": "move",
                "move_type": "sinew_to_sinew",
                "source": {"box": source_box, "slot": source_slot},
                "dest": {"box": dest_box_num, "slot": actual_dest_slot},
                "source_pokemon": source_poke_copy,
                "dest_pokemon": dest_poke_copy,
            }
            self.undo_available = True

            self.refresh_data()
            self._track_sinew_achievement()
        else:
            print("[PCBox] Sinew move failed", file=sys.stderr, flush=True)

        self._cancel_move_mode()

    # ------------------------------------------------------------------ #
    #  Game -> Sinew deposit                                               #
    # ------------------------------------------------------------------ #

    def _attempt_game_to_sinew_move(self, dest_type, dest_box, dest_slot):  # pylint: disable=unused-argument
        """Attempt to deposit Pokemon from a game save into Sinew storage"""
        if not self.sinew_storage:
            self._show_warning("Sinew storage\nnot available!")
            self._cancel_move_mode()
            return

        source_game = self.moving_pokemon_source.get("game", "")
        if self.is_game_running_callback:
            running_game = self.is_game_running_callback()
            if running_game and source_game in running_game:
                self._show_warning("Source game is running!\nStop game first")
                self._cancel_move_mode()
                return

        if not self.moving_pokemon.get("raw_bytes"):
            self._show_warning("Pokemon data missing!\nCannot transfer")
            self._cancel_move_mode()
            return

        actual_dest_slot = dest_slot + (self.sinew_scroll_offset * 6)
        dest_box_num = self.box_index + 1

        dest_poke = self.sinew_storage.get_pokemon_at(dest_box_num, actual_dest_slot)
        if dest_poke is not None:
            self._show_warning("Slot is occupied!\nChoose an empty slot")
            return

        pokemon_name = self.moving_pokemon.get("nickname") or self.moving_pokemon.get(
            "species_name", "Pokemon"
        )
        source = self.moving_pokemon_source

        if source["type"] == "box":
            source_loc = f"Box {source['box']}, Slot {source['slot'] + 1}"
        else:
            source_loc = f"Party Slot {source['slot'] + 1}"

        message = (
            f"Deposit {pokemon_name}\nfrom {source['game']}\n"
            f"{source_loc}\nto Sinew Storage {dest_box_num}?"
        )

        self.pending_move_dest = {
            "type": "sinew",
            "box": dest_box_num,
            "slot": actual_dest_slot,
            "game": "Sinew",
        }

        self.confirmation_dialog_message = message
        self.confirmation_dialog_open = True
        self.confirmation_selected = 0
        self.confirmation_dialog_callback = self._execute_game_to_sinew_move

    def _execute_game_to_sinew_move(self):
        """Execute the deposit from game to Sinew storage"""
        if (
            not self.moving_pokemon
            or not self.moving_pokemon_source
            or not hasattr(self, "pending_move_dest")
        ):
            self._cancel_move_mode()
            return

        source = self.moving_pokemon_source
        dest = self.pending_move_dest

        print("\n[PCBox] ===== DEPOSIT TO SINEW =====", file=sys.stderr, flush=True)
        print(
            f"[PCBox] From: {source['game']} {source['type']} "
            f"{source.get('box', 'N/A')}, slot {source.get('slot')}",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"[PCBox] To: Sinew Storage {dest['box']}, slot {dest['slot']}",
            file=sys.stderr,
            flush=True,
        )

        pokemon_copy = self.moving_pokemon.copy()

        try:
            pokemon_data = self.moving_pokemon.copy()

            if not self.sinew_storage.set_pokemon_at(
                dest["box"], dest["slot"], pokemon_data
            ):
                raise ValueError("Failed to store in Sinew storage")

            print("[PCBox] Stored in Sinew storage", file=sys.stderr, flush=True)

            source_save_path = source.get("save_path")
            if source_save_path and source["type"] == "box":
                source_game_type = self._resolve_game_type(source["game"])
                source_save_data = load_save_file(source_save_path)
                clear_pc_slot(
                    source_save_data, source["box"], source["slot"], source_game_type
                )
                write_save_file(
                    source_save_path, source_save_data, create_backup_first=True
                )
                print(
                    f"[PCBox] Cleared source slot in {source['game']}",
                    file=sys.stderr,
                    flush=True,
                )

            self.undo_action = {
                "type": "move",
                "move_type": "game_to_sinew",
                "source": {
                    "type": source["type"],
                    "box": source.get("box"),
                    "slot": source.get("slot"),
                    "game": source.get("game"),
                    "save_path": source_save_path,
                },
                "dest": {"box": dest["box"], "slot": dest["slot"]},
                "pokemon": pokemon_copy,
            }
            self.undo_available = True

            if TRADE_EVOLUTION_AVAILABLE and can_evolve_by_trade:
                species_id = pokemon_data.get("species", 0)
                held_item = pokemon_data.get("held_item", 0)
                evolution_info = can_evolve_by_trade(species_id, held_item)

                if evolution_info:
                    print(
                        f"[PCBox] Trade evolution available: "
                        f"{evolution_info['from_name']} -> {evolution_info['to_name']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    self._show_evolution_dialog(
                        pokemon_data, evolution_info, dest["box"], dest["slot"]
                    )

            self.refresh_data()

            pokemon_name = self.moving_pokemon.get("nickname") or "Pokemon"
            print(
                f"[PCBox] Deposit complete: {pokemon_name}", file=sys.stderr, flush=True
            )
            print("[PCBox] ===== DEPOSIT DONE =====\n", file=sys.stderr, flush=True)

            self._track_sinew_achievement(
                deposit=True, is_shiny=pokemon_data.get("is_shiny", False)
            )

        except Exception as e:
            print(f"[PCBox] Deposit FAILED: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            self._show_warning(f"Deposit failed!\n{str(e)[:30]}")

        finally:
            self._cancel_move_mode()
            if hasattr(self, "pending_move_dest"):
                del self.pending_move_dest

    # ------------------------------------------------------------------ #
    #  Sinew -> Game withdrawal                                            #
    # ------------------------------------------------------------------ #

    def _attempt_sinew_to_game_move(self, dest_type, dest_box, dest_slot):  # pylint: disable=unused-argument
        """Attempt to withdraw Pokemon from Sinew storage to a game save"""
        dest_game = self.get_current_game()
        if self.is_game_running_callback:
            running_game = self.is_game_running_callback()
            if running_game and dest_game in running_game:
                self._show_warning("Destination game\nis running!\nStop game first")
                self._cancel_move_mode()
                return

        if not self.moving_pokemon.get("raw_bytes"):
            self._show_warning("Pokemon data missing!\nCannot transfer")
            self._cancel_move_mode()
            return

        dest_poke = self.get_pokemon_at_grid_slot(dest_slot)
        if dest_poke and not dest_poke.get("empty"):
            self._show_warning("Slot is occupied!\nChoose an empty slot")
            return

        current_save_path = getattr(self.manager, "current_save_path", None)
        if not current_save_path:
            dest_game_name = dest_game or "destination game"
            self._show_warning(
                f"No save file loaded\nfor {dest_game_name}!\nLoad a save first."
            )
            return

        if SAVE_WRITER_AVAILABLE:
            try:
                _check_data = load_save_file(current_save_path)
                _block_offset = get_active_block(_check_data)
                if find_section_by_id(_check_data, _block_offset, 5) is None:
                    self._show_warning(
                        "Save too early in game!\nGet the Pokedex first,\nthen save before transferring."  # pylint: disable=line-too-long  # noqa: E501
                    )
                    self._cancel_move_mode()
                    return
            except Exception as _e:
                print(
                    f"[PCBox] PC init check failed: {_e}", file=sys.stderr, flush=True
                )

        obedience_warning = None
        pokemon_level = self.moving_pokemon.get("level", 1)

        dest_badge_count = 0
        if self.manager.is_loaded() and hasattr(self.manager, "get_badges"):
            badges = self.manager.get_badges()
            if badges:
                dest_badge_count = sum(1 for b in badges if b)

        dest_game_type = self._resolve_game_type(dest_game)

        obedience_levels = {
            0: 10, 1: 20, 2: 30, 3: 40,
            4: 50, 5: 60, 6: 70, 7: 80, 8: 100,
        }
        max_level = obedience_levels.get(dest_badge_count, 10)

        if pokemon_level > max_level:
            pokemon_name = self.moving_pokemon.get(
                "nickname"
            ) or self.moving_pokemon.get("species_name", "Pokemon")
            obedience_warning = (
                f"WARNING: {pokemon_name} (Lv.{pokemon_level})\nmay not obey!\n"
                f"{dest_game} has {dest_badge_count} badge(s)\n(max Lv.{max_level})"
            )

        self.pending_move_dest = {
            "type": dest_type,
            "box": self.box_index + 1,
            "slot": dest_slot,
            "game": dest_game,
            "save_path": current_save_path,
            "game_type": dest_game_type,
        }

        pokemon_name = self.moving_pokemon.get("nickname") or self.moving_pokemon.get(
            "species_name", "Pokemon"
        )
        message = (
            f"Withdraw {pokemon_name}\nfrom Sinew Storage\n"
            f"to {dest_game}\nBox {self.box_index + 1}, Slot {dest_slot + 1}?"
        )

        if obedience_warning:
            self.confirmation_dialog_message = obedience_warning + "\n\nMove anyway?"
        else:
            self.confirmation_dialog_message = message

        self.confirmation_dialog_open = True
        self.confirmation_selected = 0
        self.confirmation_dialog_callback = self._execute_sinew_to_game_move

    def _execute_sinew_to_game_move(self):
        """Execute the withdrawal from Sinew storage to game save"""
        if (
            not self.moving_pokemon
            or not self.moving_pokemon_source
            or not hasattr(self, "pending_move_dest")
        ):
            self._cancel_move_mode()
            return

        source = self.moving_pokemon_source
        dest = self.pending_move_dest

        print("\n[PCBox] ===== WITHDRAW FROM SINEW =====", file=sys.stderr, flush=True)
        print(
            f"[PCBox] From: Sinew Storage {source['box']}, slot {source['slot']}",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"[PCBox] To: {dest['game']} box {dest['box']}, slot {dest['slot']}",
            file=sys.stderr,
            flush=True,
        )

        pokemon_copy = self.moving_pokemon.copy()
        _withdraw_success = False

        try:
            raw_bytes = self.moving_pokemon.get("raw_bytes")
            if not raw_bytes:
                raise ValueError("No raw_bytes in Pokemon data")

            dest_save_path = dest.get("save_path")
            dest_game_type = dest.get("game_type") or self._resolve_game_type(dest.get("game"))

            if not dest_save_path:
                raise ValueError("No destination save path")

            dest_save_data = load_save_file(dest_save_path)
            write_pokemon_to_pc(
                dest_save_data, dest["box"], dest["slot"], raw_bytes, dest_game_type
            )

            try:
                from save_writer import set_pokedex_flags_for_pokemon
                result = set_pokedex_flags_for_pokemon(
                    dest_save_data, self.moving_pokemon, game_type=dest_game_type
                )
                if result:
                    pokemon_name = self.moving_pokemon.get("species_name", "Pokemon")
                    species = self.moving_pokemon.get("species", 0)
                    print(
                        f"[PCBox] Updated Pokedex: #{species} ({pokemon_name}) "
                        f"marked as seen/caught",
                        file=sys.stderr,
                        flush=True,
                    )
            except Exception as dex_err:
                print(
                    f"[PCBox] Pokedex update skipped: {dex_err}",
                    file=sys.stderr,
                    flush=True,
                )

            write_save_file(dest_save_path, dest_save_data, create_backup_first=True)

            print(f"[PCBox] Written to {dest['game']}", file=sys.stderr, flush=True)

            if self.sinew_storage:
                self.sinew_storage.clear_slot(source["box"], source["slot"])
                print("[PCBox] Cleared Sinew storage slot", file=sys.stderr, flush=True)

            self.undo_action = {
                "type": "move",
                "move_type": "sinew_to_game",
                "source": {"box": source["box"], "slot": source["slot"]},
                "dest": {
                    "box": dest["box"],
                    "slot": dest["slot"],
                    "game": dest.get("game"),
                    "save_path": dest_save_path,
                    "game_type": dest_game_type,
                },
                "pokemon": pokemon_copy,
            }
            self.undo_available = True

            if TRADE_EVOLUTION_AVAILABLE and can_evolve_by_trade:
                species_id = pokemon_copy.get("species", 0)
                held_item = pokemon_copy.get("held_item", 0)
                print(
                    f"[PCBox] Evolution check: species={species_id}, held_item={held_item}",
                    file=sys.stderr,
                    flush=True,
                )
                evolution_info = can_evolve_by_trade(species_id, held_item)

                if evolution_info:
                    print(
                        f"[PCBox] Trade evolution available: "
                        f"{evolution_info['from_name']} -> {evolution_info['to_name']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    self._show_evolution_dialog_game(
                        pokemon_copy,
                        evolution_info,
                        dest["box"],
                        dest["slot"],
                        dest_save_path,
                        dest.get("game", "Game"),
                    )
                else:
                    print(
                        f"[PCBox] No evolution available for species {species_id}",
                        file=sys.stderr,
                        flush=True,
                    )

            from parser.gen3_parser import Gen3SaveParser
            fresh_parser = Gen3SaveParser()
            fresh_parser.load(dest_save_path, game_hint=dest.get("game"))
            self.manager.parser = fresh_parser
            self.manager.loaded = fresh_parser.loaded
            self.manager.current_save_path = dest_save_path

            self._skip_reload = True
            self.current_box_data = []
            self.party_data = []
            self.selected_pokemon = None
            self.refresh_data()
            self._skip_reload = False

            pokemon_name = self.moving_pokemon.get("nickname") or "Pokemon"
            print(
                f"[PCBox] Withdraw complete: {pokemon_name}",
                file=sys.stderr,
                flush=True,
            )
            print("[PCBox] ===== WITHDRAW DONE =====\n", file=sys.stderr, flush=True)
            _withdraw_success = True

            self._track_sinew_achievement(transfer=True)

        except Exception as e:
            print(f"[PCBox] Withdraw FAILED: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            err_str = str(e)
            if "\n" in err_str and len(err_str) <= 120:
                self._show_warning(err_str)
            else:
                self._show_warning(f"Withdraw failed!\n{err_str[:40]}")

        finally:
            self._cancel_move_mode(
                reason="withdraw complete" if _withdraw_success else "failed"
            )
            if hasattr(self, "pending_move_dest"):
                del self.pending_move_dest

    # ------------------------------------------------------------------ #
    #  Destination dispatch                                                #
    # ------------------------------------------------------------------ #

    def _attempt_place_pokemon(self, dest_type, dest_box, dest_slot):
        """Attempt to place the moving Pokemon at destination"""
        if not self.move_mode or not self.moving_pokemon:
            return

        source_is_sinew = self.moving_pokemon_source.get("game") == "Sinew"
        dest_is_sinew = self.sinew_mode

        if source_is_sinew or dest_is_sinew:
            if source_is_sinew and dest_is_sinew:
                self._execute_sinew_move(dest_type, dest_box, dest_slot)
            elif source_is_sinew and not dest_is_sinew:
                self._attempt_sinew_to_game_move(dest_type, dest_box, dest_slot)
            else:
                self._attempt_game_to_sinew_move(dest_type, dest_box, dest_slot)
            return

        if self._is_current_game_running():
            self._show_warning("Game is running!\nStop game to move Pokemon")
            return

        if dest_type == "box":
            dest_poke = self.get_pokemon_at_grid_slot(dest_slot)
            if dest_poke and not dest_poke.get("empty"):
                print("Slot is occupied - choose an empty slot")
                return

        if not self.moving_pokemon.get("raw_bytes"):
            print("Error: Pokemon data missing raw_bytes - cannot transfer")
            self._cancel_move_mode()
            return

        obedience_warning = None
        source_game = self.moving_pokemon_source.get("game", "???")
        dest_game = self.get_current_game()

        if source_game != dest_game:
            pokemon_level = self.moving_pokemon.get("level", 1)

            dest_badge_count = 0
            if self.manager.is_loaded() and hasattr(self.manager, "get_badges"):
                badges = self.manager.get_badges()
                if badges:
                    dest_badge_count = sum(1 for b in badges if b)

            obedience_levels = {
                0: 10, 1: 20, 2: 30, 3: 40,
                4: 50, 5: 60, 6: 70, 7: 80, 8: 100,
            }
            max_level = obedience_levels.get(dest_badge_count, 10)

            if pokemon_level > max_level:
                pokemon_name = self.moving_pokemon.get(
                    "nickname"
                ) or self.moving_pokemon.get("species_name", "Pokemon")
                obedience_warning = (
                    f"WARNING: {pokemon_name} (Lv.{pokemon_level})\nmay not obey!\n"
                    f"{dest_game} trainer has\n{dest_badge_count} badge(s) (max Lv.{max_level})"
                )

        current_save_path = getattr(self.manager, "current_save_path", None)

        if not current_save_path:
            dest_game_name = self.get_current_game() or "destination game"
            self._show_warning(
                f"No save file loaded\nfor {dest_game_name}!\nLoad a save first."
            )
            return

        if SAVE_WRITER_AVAILABLE and current_save_path:
            try:
                _check_data = load_save_file(current_save_path)
                _block_offset = get_active_block(_check_data)
                if find_section_by_id(_check_data, _block_offset, 5) is None:
                    self._show_warning(
                        "Save too early in game!\nGet the Pokedex first,\n"
                        "then save before transferring."
                    )
                    self._cancel_move_mode()
                    return
            except Exception as _e:
                print(
                    f"[PCBox] PC init check failed: {_e}", file=sys.stderr, flush=True
                )

        self.pending_move_dest = {
            "type": dest_type,
            "box": dest_box,
            "slot": dest_slot,
            "game": self.get_current_game(),
            "save_path": current_save_path,
        }

        pokemon_name = self.moving_pokemon.get("nickname") or self.moving_pokemon.get(
            "species_name", "Pokemon"
        )

        if self.moving_pokemon_source["type"] == "box":
            src = self.moving_pokemon_source
            source_loc = f"Box {src['box']}, Slot {src['slot'] + 1}"
        else:
            source_loc = f"Party Slot {self.moving_pokemon_source['slot'] + 1}"

        dest_loc = f"Box {dest_box}, Slot {dest_slot + 1}"

        if obedience_warning:
            self.confirmation_dialog_message = obedience_warning + "\n\nMove anyway?"
        elif source_game != dest_game:
            self.confirmation_dialog_message = (
                f"Move {pokemon_name}\nfrom {source_game} {source_loc}\nto {dest_game} {dest_loc}?"
            )
        else:
            self.confirmation_dialog_message = (
                f"Move {pokemon_name}\nfrom {source_loc}\nto {dest_loc}?"
            )

        self.confirmation_dialog_open = True
        self.confirmation_selected = 0
        self.confirmation_dialog_callback = self._execute_move

    # ------------------------------------------------------------------ #
    #  Game-to-game transfer                                               #
    # ------------------------------------------------------------------ #

    def _execute_move(self):
        """Execute the confirmed move operation"""
        if (
            not self.moving_pokemon
            or not self.moving_pokemon_source
            or not hasattr(self, "pending_move_dest")
        ):
            print("Error: Missing move data", file=sys.stderr, flush=True)
            self._cancel_move_mode()
            return

        source = self.moving_pokemon_source
        dest = self.pending_move_dest

        print("\n[PCBox] ===== EXECUTING TRANSFER =====", file=sys.stderr, flush=True)
        print(
            f"[PCBox] From: {source['game']} box {source.get('box')}, slot {source.get('slot')}",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"[PCBox] To: {dest['game']} box {dest['box']}, slot {dest['slot']}",
            file=sys.stderr,
            flush=True,
        )

        pokemon_copy = self.moving_pokemon.copy()
        _transfer_success = False

        try:
            raw_bytes = self.moving_pokemon.get("raw_bytes")
            if not raw_bytes:
                raise ValueError("No raw_bytes in Pokemon data")

            dest_game_type = self._resolve_game_type(dest["game"])
            source_game_type = self._resolve_game_type(source["game"])

            dest_save_path = dest.get("save_path")
            source_save_path = source.get("save_path")

            if not dest_save_path or not source_save_path:
                raise ValueError(
                    f"Missing save paths: dest={dest_save_path}, source={source_save_path}"
                )

            dest_save_data = load_save_file(dest_save_path)

            if source_save_path != dest_save_path and source["type"] == "box":
                source_save_data = load_save_file(source_save_path)
            else:
                source_save_data = None

            write_pokemon_to_pc(
                dest_save_data, dest["box"], dest["slot"], raw_bytes, dest_game_type
            )

            try:
                from save_writer import set_pokedex_flags_for_pokemon
                result = set_pokedex_flags_for_pokemon(
                    dest_save_data, self.moving_pokemon, game_type=dest_game_type
                )
                if result:
                    pokemon_name = self.moving_pokemon.get("species_name", "Pokemon")
                    species = self.moving_pokemon.get("species", 0)
                    print(
                        f"[PCBox] Updated Pokedex: #{species} ({pokemon_name}) "
                        f"marked as seen/caught in {dest['game']}",
                        file=sys.stderr,
                        flush=True,
                    )
            except Exception as dex_err:
                print(
                    f"[PCBox] Pokedex update skipped: {dex_err}",
                    file=sys.stderr,
                    flush=True,
                )

            if source["type"] == "box":
                if source_save_path == dest_save_path:
                    clear_pc_slot(
                        dest_save_data, source["box"], source["slot"], dest_game_type
                    )
                else:
                    clear_pc_slot(
                        source_save_data,
                        source["box"],
                        source["slot"],
                        source_game_type,
                    )

            write_save_file(dest_save_path, dest_save_data, create_backup_first=True)

            if source_save_data is not None and source_save_path != dest_save_path:
                write_save_file(
                    source_save_path, source_save_data, create_backup_first=True
                )

            self.undo_action = {
                "type": "move",
                "move_type": "game_to_game",
                "source": {
                    "type": source["type"],
                    "box": source.get("box"),
                    "slot": source.get("slot"),
                    "game": source.get("game"),
                    "save_path": source_save_path,
                    "game_type": source_game_type,
                },
                "dest": {
                    "box": dest["box"],
                    "slot": dest["slot"],
                    "game": dest.get("game"),
                    "save_path": dest_save_path,
                    "game_type": dest_game_type,
                },
                "pokemon": pokemon_copy,
            }
            self.undo_available = True

            print("[PCBox] Files written successfully", file=sys.stderr, flush=True)

            from parser.gen3_parser import Gen3SaveParser
            fresh_parser = Gen3SaveParser()
            fresh_parser.load(dest_save_path, game_hint=dest.get("game"))
            self.manager.parser = fresh_parser
            self.manager.loaded = fresh_parser.loaded
            self.manager.current_save_path = dest_save_path
            print("[PCBox] Created fresh parser", file=sys.stderr, flush=True)

            self._skip_reload = True
            self.current_box_data = []
            self.party_data = []
            self.selected_pokemon = None
            self.refresh_data()
            self._skip_reload = False

            pokemon_name = self.moving_pokemon.get("nickname") or "Pokemon"
            print(
                f"[PCBox] Transfer complete: {pokemon_name}",
                file=sys.stderr,
                flush=True,
            )
            print("[PCBox] ===== TRANSFER DONE =====\n", file=sys.stderr, flush=True)
            _transfer_success = True

            if (
                source["game"] != dest["game"]
                and TRADE_EVOLUTION_AVAILABLE
                and can_evolve_by_trade
            ):
                species_id = self.moving_pokemon.get("species", 0)
                held_item = self.moving_pokemon.get("held_item", 0)
                evolution_info = can_evolve_by_trade(species_id, held_item)

                if evolution_info:
                    print(
                        f"[PCBox] Trade evolution available: "
                        f"{evolution_info['from_name']} -> {evolution_info['to_name']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    self._show_evolution_dialog_game(
                        self.moving_pokemon,
                        evolution_info,
                        dest["box"],
                        dest["slot"],
                        dest["save_path"],
                        dest["game"],
                    )

        except Exception as e:
            print(f"[PCBox] Transfer FAILED: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()

        finally:
            self._cancel_move_mode(
                reason="transfer complete" if _transfer_success else "failed"
            )
            if hasattr(self, "pending_move_dest"):
                del self.pending_move_dest