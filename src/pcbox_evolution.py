#!/usr/bin/env python3
"""
ui_pcbox_evolution.py — Trade evolution and Altering Cave "Echoes" mixin for PCBox.

Extracted from pc_box.py. Provides PCBoxEvolutionMixin.

Usage
-----
    class PCBox(PCBoxDrawMixin, PCBoxInputMixin, PCBoxTransferMixin, PCBoxEvolutionMixin):
        ...

Methods call back into self.* for state (sinew_storage, manager, box_index,
warning_message, etc.) and other mixins (_show_warning, refresh_data).
"""

from config import ECHO_DELIVERED_PATH
import sys

try:
    from save_writer import load_save_file, write_pokemon_to_pc, write_save_file
    SAVE_WRITER_AVAILABLE = True
except ImportError:
    SAVE_WRITER_AVAILABLE = False

try:
    from trade_evolution import apply_evolution, evolve_raw_pokemon_bytes
    TRADE_EVOLUTION_AVAILABLE = True
except ImportError:
    apply_evolution = None
    evolve_raw_pokemon_bytes = None
    TRADE_EVOLUTION_AVAILABLE = False

try:
    from achievements_data import (
        ALTERING_CAVE_LOCATIONS,
        ALTERING_CAVE_POKEMON,
        ALTERING_CAVE_ZUBAT_SPECIES,
    )
    ALTERING_CAVE_AVAILABLE = True
except ImportError:
    ALTERING_CAVE_LOCATIONS = (183, 210)
    ALTERING_CAVE_ZUBAT_SPECIES = 41
    ALTERING_CAVE_POKEMON = []
    ALTERING_CAVE_AVAILABLE = False

try:
    from achievements import get_achievement_manager
    ACHIEVEMENTS_AVAILABLE = True
except ImportError:
    get_achievement_manager = None
    ACHIEVEMENTS_AVAILABLE = False

try:
    from sinew_storage import get_sinew_storage
    SINEW_STORAGE_AVAILABLE = True
except ImportError:
    get_sinew_storage = None
    SINEW_STORAGE_AVAILABLE = False


class PCBoxEvolutionMixin:
    """Mixin providing trade evolution and Altering Cave exchange for PCBox."""

    # ------------------------------------------------------------------ #
    #  Evolution dialog state setters                                      #
    # ------------------------------------------------------------------ #

    def _show_evolution_dialog(self, pokemon_data, evolution_info, box, slot):
        """Show the trade evolution dialog for Sinew storage"""
        self.evolution_dialog_open = True
        self.evolution_dialog_pokemon = pokemon_data
        self.evolution_dialog_info = evolution_info
        self.evolution_dialog_location = (box, slot)
        self.evolution_dialog_save_path = None  # None = Sinew storage
        self.evolution_dialog_game = "Sinew"
        self.evolution_selected = 0  # Default to "Evolve"

    def _show_evolution_dialog_game(
        self, pokemon_data, evolution_info, box, slot, save_path, game_name
    ):
        """Show the trade evolution dialog for game save"""
        self.evolution_dialog_open = True
        self.evolution_dialog_pokemon = pokemon_data
        self.evolution_dialog_info = evolution_info
        self.evolution_dialog_location = (box, slot)
        self.evolution_dialog_save_path = save_path
        self.evolution_dialog_game = game_name
        self.evolution_selected = 0  # Default to "Evolve"

    # ------------------------------------------------------------------ #
    #  Evolution controller                                                #
    # ------------------------------------------------------------------ #

    def _handle_evolution_controller(self, ctrl):
        """Handle controller input for evolution dialog"""
        if ctrl.is_dpad_just_pressed("left") or ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("left")
            ctrl.consume_dpad("right")
            self.evolution_selected = 1 - self.evolution_selected
            return True

        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            if self.evolution_selected == 0:  # Evolve
                self._execute_evolution()
            self.evolution_dialog_open = False
            return True

        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.evolution_dialog_open = False
            return True

        return True

    # ------------------------------------------------------------------ #
    #  Evolution execution                                                 #
    # ------------------------------------------------------------------ #

    def _execute_evolution(self):
        """Execute the trade evolution"""
        if (
            not self.evolution_dialog_pokemon
            or not self.evolution_dialog_info
            or not self.evolution_dialog_location
        ):
            return

        box, slot = self.evolution_dialog_location
        evolution_info = self.evolution_dialog_info
        save_path = getattr(self, "evolution_dialog_save_path", None)

        print("\n[PCBox] ===== TRADE EVOLUTION =====", file=sys.stderr, flush=True)
        print(
            f"[PCBox] {evolution_info['from_name']} -> {evolution_info['to_name']}",
            file=sys.stderr,
            flush=True,
        )

        try:
            if save_path is None:
                self._execute_sinew_evolution(box, slot, evolution_info)
            else:
                self._execute_game_evolution(box, slot, save_path, evolution_info)

            print("[PCBox] Evolution complete!", file=sys.stderr, flush=True)
            print("[PCBox] ===== EVOLUTION DONE =====\n", file=sys.stderr, flush=True)

            try:
                if ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
                    manager = get_achievement_manager()
                    if manager:
                        manager.increment_stat("sinew_evolutions", 1)
                        evolutions = manager.get_stat("sinew_evolutions", 0)
                        print(f"[PCBox] Sinew evolutions: {evolutions}")
                        manager.check_sinew_achievements(evolution_count=evolutions)
            except Exception as e:
                print(f"[PCBox] Evolution tracking error: {e}")

            self.refresh_data()

        except Exception as e:
            print(f"[PCBox] Evolution FAILED: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            self._show_warning(f"Evolution failed!\n{str(e)[:30]}")

    def _execute_sinew_evolution(self, box, slot, evolution_info):
        """Execute evolution for Pokemon in Sinew storage"""
        pokemon = self.sinew_storage.get_pokemon_at(box, slot)
        if not pokemon:
            raise ValueError("Pokemon not found in storage")

        current_nickname = pokemon.get("nickname", "")
        old_species_name = evolution_info.get("from_name", "")
        new_species_name = evolution_info.get("to_name", "")

        nickname_is_default = (
            not current_nickname
            or current_nickname.upper() == old_species_name.upper()
            or current_nickname.upper().strip() == old_species_name.upper().strip()
        )

        if apply_evolution:
            pokemon = apply_evolution(pokemon, evolution_info)
        else:
            pokemon["species"] = evolution_info["evolves_to"]
            pokemon["species_name"] = new_species_name
            if evolution_info.get("consumes_item"):
                pokemon["held_item"] = 0

        if nickname_is_default and new_species_name:
            pokemon["nickname"] = new_species_name.upper()
            print(
                f"[PCBox] Updated Sinew Pokemon nickname to {new_species_name.upper()}"
            )
            if pokemon.get("raw_bytes"):
                pokemon["raw_bytes"] = self._update_nickname_in_bytes(
                    pokemon["raw_bytes"], new_species_name
                )

        if not self.sinew_storage.set_pokemon_at(box, slot, pokemon):
            raise ValueError("Failed to save evolved Pokemon")

    def _execute_game_evolution(self, box, slot, save_path, evolution_info):
        """Execute evolution for Pokemon in a game save"""
        raw_bytes = self.evolution_dialog_pokemon.get("raw_bytes")
        if not raw_bytes:
            raise ValueError("No raw_bytes available for evolution")

        current_nickname = self.evolution_dialog_pokemon.get("nickname", "")
        old_species_name = evolution_info.get("from_name", "")
        new_species_name = evolution_info.get("to_name", "")

        nickname_is_default = (
            not current_nickname
            or current_nickname.upper() == old_species_name.upper()
            or current_nickname.upper().strip() == old_species_name.upper().strip()
        )

        if evolve_raw_pokemon_bytes:
            evolved_bytes = evolve_raw_pokemon_bytes(
                raw_bytes,
                evolution_info["evolves_to"],
                evolution_info.get("consumes_item", False),
                old_species_name,
                new_species_name,
            )
        else:
            raise ValueError("evolve_raw_pokemon_bytes not available")

        if nickname_is_default and new_species_name:
            evolved_bytes = self._update_nickname_in_bytes(
                evolved_bytes, new_species_name
            )
            print(
                f"[PCBox] Updated nickname to {new_species_name}",
                file=sys.stderr,
                flush=True,
            )

        game_type = "RSE"
        if (
            "Fire" in save_path
            or "Leaf" in save_path
            or "fire" in save_path
            or "leaf" in save_path
        ):
            game_type = "FRLG"

        save_data = load_save_file(save_path)
        write_pokemon_to_pc(save_data, box, slot, evolved_bytes, game_type)

        try:
            from save_writer import set_pokedex_flags_for_pokemon
            evolved_pokemon = {
                "species": evolution_info["evolves_to"],
                "species_name": new_species_name,
            }
            set_pokedex_flags_for_pokemon(
                save_data, evolved_pokemon, game_type=game_type
            )
            print(
                f"[PCBox] Updated Pokedex for evolved species "
                f"#{evolution_info['evolves_to']} ({new_species_name})",
                file=sys.stderr,
                flush=True,
            )
        except Exception as dex_err:
            print(
                f"[PCBox] Pokedex update for evolution skipped: {dex_err}",
                file=sys.stderr,
                flush=True,
            )

        write_save_file(save_path, save_data, create_backup_first=True)
        print(f"[PCBox] Evolution saved to {save_path}", file=sys.stderr, flush=True)

    # ------------------------------------------------------------------ #
    #  Nickname bytes helper (used by both evolution paths)               #
    # ------------------------------------------------------------------ #

    def _update_nickname_in_bytes(self, pokemon_bytes, new_nickname):
        """
        Update the nickname in Pokemon raw bytes.
        Nickname is stored at offset 0x08, 10 bytes, Gen 3 encoding.
        """
        pokemon_bytes = bytearray(pokemon_bytes)

        gen3_encode = {
            "A": 0xBB, "B": 0xBC, "C": 0xBD, "D": 0xBE, "E": 0xBF,
            "F": 0xC0, "G": 0xC1, "H": 0xC2, "I": 0xC3, "J": 0xC4,
            "K": 0xC5, "L": 0xC6, "M": 0xC7, "N": 0xC8, "O": 0xC9,
            "P": 0xCA, "Q": 0xCB, "R": 0xCC, "S": 0xCD, "T": 0xCE,
            "U": 0xCF, "V": 0xD0, "W": 0xD1, "X": 0xD2, "Y": 0xD3,
            "Z": 0xD4, "a": 0xD5, "b": 0xD6, "c": 0xD7, "d": 0xD8,
            "e": 0xD9, "f": 0xDA, "g": 0xDB, "h": 0xDC, "i": 0xDD,
            "j": 0xDE, "k": 0xDF, "l": 0xE0, "m": 0xE1, "n": 0xE2,
            "o": 0xE3, "p": 0xE4, "q": 0xE5, "r": 0xE6, "s": 0xE7,
            "t": 0xE8, "u": 0xE9, "v": 0xEA, "w": 0xEB, "x": 0xEC,
            "y": 0xED, "z": 0xEE, " ": 0x00, ".": 0xAD, "-": 0xAE,
            "0": 0xF1, "1": 0xF2, "2": 0xF3, "3": 0xF4, "4": 0xF5,
            "5": 0xF6, "6": 0xF7, "7": 0xF8, "8": 0xF9, "9": 0xFA,
            "!": 0xAB, "?": 0xAC, "♂": 0xB5, "♀": 0xB6,
        }

        encoded = []
        name_upper = new_nickname.upper()[:10]
        for char in name_upper:
            encoded.append(gen3_encode.get(char, 0x00))

        while len(encoded) < 10:
            encoded.append(0xFF)

        for i, byte in enumerate(encoded):
            pokemon_bytes[0x08 + i] = byte

        return bytes(pokemon_bytes)

    # ------------------------------------------------------------------ #
    #  Altering Cave "Echoes" feature                                      #
    # ------------------------------------------------------------------ #

    def _is_altering_cave_zubat(self, pokemon):
        """
        Check if a Pokemon is a Zubat caught in Altering Cave.
        These special Zubats can be exchanged for the never-released Altering Cave Pokemon.
        """
        if not pokemon or pokemon.get("empty") or pokemon.get("egg"):
            return False

        species = pokemon.get("species", 0)
        if species != ALTERING_CAVE_ZUBAT_SPECIES:
            return False

        met_location = pokemon.get("met_location", 0)
        if met_location not in ALTERING_CAVE_LOCATIONS:
            return False

        if ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
            manager = get_achievement_manager()
            if manager and manager.is_altering_cave_complete():
                return False

        return True

    def _show_altering_cave_dialog(self, pokemon, location_info):
        """
        Show the Altering Cave confirmation dialog.

        Args:
            pokemon: The Zubat Pokemon data
            location_info: (box, slot) for Sinew, or (save_path, box, slot) for game
        """
        self.altering_cave_dialog_open = True
        self.altering_cave_zubat = pokemon
        self.altering_cave_location = location_info
        self.altering_cave_selected = 0  # Default to "Yes"

        if len(location_info) == 2:
            box, slot = location_info
            print(
                f"[PCBox] Altering Cave dialog - Sinew: box_index={box} (Box {box+1}), slot={slot}"
            )
        else:
            _, box, slot = location_info
            print(
                f"[PCBox] Altering Cave dialog - Game: box_index={box} "
                f"(Box {box+1}), slot={slot}, current self.box_index={self.box_index}"
            )

    def _close_altering_cave_dialog(self):
        """Close the Altering Cave dialog without doing anything."""
        self.altering_cave_dialog_open = False
        self.altering_cave_zubat = None
        self.altering_cave_location = None

    def _start_altering_cave_spinner(self):
        """Start the slot machine spinner for Altering Cave Pokemon."""
        if ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
            manager = get_achievement_manager()
            remaining = manager.get_altering_cave_remaining()
        else:
            remaining = ALTERING_CAVE_POKEMON.copy()

        if not remaining:
            self.warning_message = "All Altering Cave Pokemon already claimed!"
            self.warning_message_timer = self.warning_message_duration
            self._close_altering_cave_dialog()
            return

        self.altering_cave_spinner_active = True
        self.altering_cave_spinner_speed = 25.0
        self.altering_cave_spinner_offset = 0.0
        self.altering_cave_spinner_stopped = False
        self.altering_cave_spinner_show_result = False
        self.altering_cave_spinner_result = None
        self.altering_cave_remaining = remaining

        import random
        from ui_scale import ui
        result_index = random.randint(0, len(remaining) - 1)
        self.altering_cave_spinner_result = remaining[result_index]

        item_height = ui.s(56)  # Must match draw code in ui_pcbox_draw.py
        full_rotations = random.randint(3, 5) * len(remaining) * item_height
        target_offset = full_rotations + (result_index * item_height)
        self.altering_cave_target_offset = target_offset
        print(
            f"[PCBox] Altering Cave spinner started - result will be: "
            f"{self.altering_cave_spinner_result['name']} (index {result_index})"
        )

    def _update_altering_cave_spinner(self, dt):
        """Update the spinner animation."""
        if not self.altering_cave_spinner_active:
            return

        if self.altering_cave_spinner_show_result:
            return

        if self.altering_cave_spinner_stopped:
            return

        remaining_distance = (
            self.altering_cave_target_offset - self.altering_cave_spinner_offset
        )

        if remaining_distance <= 0:
            self.altering_cave_spinner_offset = self.altering_cave_target_offset
            self.altering_cave_spinner_speed = 0
            self.altering_cave_spinner_stopped = True
            self.altering_cave_result_timer = 45
            return

        if remaining_distance < 200:
            self.altering_cave_spinner_speed = max(1.0, remaining_distance / 15)
        elif remaining_distance < 500:
            self.altering_cave_spinner_speed = max(3.0, remaining_distance / 30)
        else:
            self.altering_cave_spinner_speed = min(25.0, remaining_distance / 40)

        self.altering_cave_spinner_offset += self.altering_cave_spinner_speed * (
            dt / 16.0
        )

    def _handle_altering_cave_controller(self, ctrl):
        """Handle controller input for Altering Cave dialog/spinner"""
        if self.altering_cave_spinner_active:
            self._update_altering_cave_spinner(16)

            if self.altering_cave_spinner_show_result:
                if ctrl.is_button_just_pressed("A"):
                    ctrl.consume_button("A")
                    self._complete_altering_cave_exchange()
                    return True

            return True

        if ctrl.is_dpad_just_pressed("left") or ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("left")
            ctrl.consume_dpad("right")
            self.altering_cave_selected = 1 - self.altering_cave_selected
            return True

        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            if self.altering_cave_selected == 0:
                self._start_altering_cave_spinner()
            else:
                self._close_altering_cave_dialog()
            return True

        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self._close_altering_cave_dialog()
            return True

        return True

    def _complete_altering_cave_exchange(self):
        """
        Complete the Altering Cave exchange - replace Zubat with won Pokemon.
        
        ENHANCED: Now uses UPO system for automatic validation and debugging.
        Falls back to legacy generation if UPO unavailable.
        """
        if not self.altering_cave_spinner_result or not self.altering_cave_location:
            return

        result_pokemon = self.altering_cave_spinner_result

        try:
            # Try UPO-enhanced generation first
            try:
                from pokemon_generator import generate_echo_pokemon_upo

                current_game = self.get_current_game() if hasattr(self, "get_current_game") else "emerald"
                print(f"[PCBox] Echo generation - current_game='{current_game}'")
                result = generate_echo_pokemon_upo(result_pokemon["name"], current_game)
                if result is None:
                    print(f"[PCBox] ERROR: Could not generate {result_pokemon['name']}")
                    self.warning_message = (
                        f"Error: Could not generate {result_pokemon['name']}!"
                    )
                    self.warning_message_timer = self.warning_message_duration
                    self._close_altering_cave_spinner()
                    return
                
                pokemon_upo, pks_data, pokemon_dict = result
                pokemon_dict["raw_bytes"] = pks_data
                
                print(
                    f"[PCBox] Generated {result_pokemon['name']} (UPO): "
                    f"{len(pks_data)} bytes, species={pokemon_dict.get('species')}"
                )
                
                # Validate the generated Pokemon
                from legality_engine import validate_pokemon, ValidationLevel
                
                errors = validate_pokemon(pokemon_upo, ValidationLevel.STANDARD)
                if errors:
                    print(f"[PCBox] WARNING: Generated Pokemon has validation errors:")
                    for error in errors:
                        print(f"  - {error}")
                    print(f"[PCBox] Species: {result_pokemon['name']}")
                    print(f"[PCBox] PID: 0x{pokemon_upo.pid:08X}")
                    print(f"[PCBox] Proceeding with exchange anyway...")
                else:
                    print(f"[PCBox] ✓ Pokemon validation passed")
                
                # Optional: Log Echo deliveries
                try:
                    import json
                    import time
                    log_path = ECHO_DELIVERED_PATH
                    with open(log_path, "a") as f:
                        log_entry = {
                            "timestamp": time.time(),
                            "species": result_pokemon['name'],
                            "species_id": result_pokemon['species'],
                            "pid": f"0x{pokemon_upo.pid:08X}",
                            "shiny": pokemon_upo.is_shiny,
                            "ivs": pokemon_upo.ivs.to_tuple(),
                            "validation_passed": len(errors) == 0
                        }
                        f.write(json.dumps(log_entry) + "\n")
                except Exception as log_error:
                    # Don't fail exchange if logging fails
                    print(f"[PCBox] Could not log Echo delivery: {log_error}")
                
            except ImportError:
                # Fall back to legacy generation
                print("[PCBox] UPO not available, using legacy generation")
                from pokemon_generator import generate_echo_pokemon

                current_game = self.get_current_game() if hasattr(self, "get_current_game") else "emerald"
                result = generate_echo_pokemon(result_pokemon["name"], current_game)
                if result is None:
                    print(f"[PCBox] ERROR: Could not generate {result_pokemon['name']}")
                    self.warning_message = (
                        f"Error: Could not generate {result_pokemon['name']}!"
                    )
                    self.warning_message_timer = self.warning_message_duration
                    self._close_altering_cave_spinner()
                    return

                pks_data, pokemon_dict = result
                pokemon_dict["raw_bytes"] = pks_data
                print(
                    f"[PCBox] Generated {result_pokemon['name']} (legacy): "
                    f"{len(pks_data)} bytes, species={pokemon_dict.get('species')}"
                )

            location = self.altering_cave_location
            print(f"[PCBox] Exchange location tuple: {location}")

            if len(location) == 2:
                box, slot = location
                print(
                    f"[PCBox] Sinew mode: box_index={box} (Box {box+1}), slot={slot}"
                )
                if SINEW_STORAGE_AVAILABLE and get_sinew_storage:
                    storage = get_sinew_storage()
                    success = storage.set_pokemon_at(box + 1, slot, pokemon_dict)
                    if success:
                        print(
                            f"[PCBox] SUCCESS: Replaced Zubat with {result_pokemon['name']} "
                            f"in Sinew box {box+1} slot {slot}"
                        )
                    else:
                        print("[PCBox] ERROR: Failed to store in Sinew storage")
                        self.warning_message = "Error saving to Sinew storage!"
                        self.warning_message_timer = self.warning_message_duration
            else:
                save_path, box, slot = location
                print(
                    f"[PCBox] Game save mode: box_index={box} "
                    f"(will write to Box {box+1}), slot={slot}"
                )
                if SAVE_WRITER_AVAILABLE:
                    save_data = load_save_file(save_path)
                    if save_data:
                        print(
                            f"[PCBox] Calling write_pokemon_to_pc("
                            f"save_data, box={box+1}, slot={slot}, ...)"
                        )
                        write_pokemon_to_pc(save_data, box + 1, slot, pks_data)
                        write_save_file(save_path, save_data)
                        print(
                            f"[PCBox] SUCCESS: Replaced Zubat with {result_pokemon['name']} "
                            f"in game box {box+1} slot {slot}"
                        )
                    else:
                        print("[PCBox] ERROR: Could not load save file")
                        self.warning_message = "Error loading save file!"
                        self.warning_message_timer = self.warning_message_duration

            if ACHIEVEMENTS_AVAILABLE and get_achievement_manager:
                manager = get_achievement_manager()
                manager.claim_altering_cave_pokemon(result_pokemon["species"])

            self.warning_message = f"Obtained {result_pokemon['name']}!"
            self.warning_message_timer = int(self.warning_message_duration * 1.25)

            self.refresh_data()

        except ImportError as e:
            print(f"[PCBox] Pokemon generator not available: {e}")
            self.warning_message = "Error: Generator not available!"
            self.warning_message_timer = self.warning_message_duration
        except Exception as e:
            print(f"[PCBox] Error completing Altering Cave exchange: {e}")
            import traceback
            traceback.print_exc()
            self.warning_message = "Error during exchange!"
            self.warning_message_timer = self.warning_message_duration

        self._close_altering_cave_spinner()

    def _close_altering_cave_spinner(self):
        """Close the spinner and reset state."""
        self.altering_cave_spinner_active = False
        self.altering_cave_spinner_result = None
        self.altering_cave_spinner_stopped = False
        self.altering_cave_spinner_show_result = False
        self.altering_cave_target_offset = 0
        self.altering_cave_remaining = []
        self.altering_cave_dialog_open = False
        self.altering_cave_zubat = None
        self.altering_cave_location = None