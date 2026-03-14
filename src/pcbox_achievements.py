#!/usr/bin/env python3
"""
pcbox_achievements.py — Achievement tracking and dev-export mixin for PCBox.

Extracted from pc_box.py. Provides PCBoxAchievementsMixin.
"""

import os
import sys

try:
    from achievements import get_achievement_manager
    ACHIEVEMENTS_AVAILABLE = True
except ImportError:
    get_achievement_manager = None
    ACHIEVEMENTS_AVAILABLE = False


class PCBoxAchievementsMixin:
    """Mixin providing achievement tracking, warning display, and dev export for PCBox."""

    def _is_current_game_running(self):
        """Check if the currently displayed game is the one running in the emulator"""
        if self.is_game_running_callback:
            running_game = self.is_game_running_callback()
            if running_game:
                current_game = self.get_current_game()
                return running_game.lower() == current_game.lower()
        return False

    def _show_warning(self, message):
        """Show a warning message popup"""
        self.warning_message = message
        self.warning_message_timer = self.warning_message_duration

    def _track_sinew_achievement(self, deposit=False, transfer=False, is_shiny=False):
        """Track Sinew-related achievement progress"""
        if not ACHIEVEMENTS_AVAILABLE or not get_achievement_manager:
            return

        try:
            manager = get_achievement_manager()

            if deposit:
                manager.increment_stat("sinew_deposits", 1)
            if transfer:
                manager.increment_stat("sinew_transfers", 1)
            if is_shiny:
                manager.increment_stat("sinew_shinies", 1)

            total_pokemon = 0
            total_shinies = 0

            if self.sinew_storage:
                total_pokemon = self.sinew_storage.get_total_pokemon_count()
                for box_num in range(1, 21):
                    box_data = self.sinew_storage.get_box(box_num)
                    if box_data:
                        for poke in box_data:
                            if poke and not poke.get("empty") and poke.get("is_shiny"):
                                total_shinies += 1

            transfer_count = manager.get_stat("sinew_transfers", 0)

            newly_unlocked = manager.check_sinew_achievements(
                sinew_storage_count=total_pokemon,
                transfer_count=transfer_count,
                shiny_count=total_shinies,
            )

            if newly_unlocked:
                print(f"[PCBox] Unlocked {len(newly_unlocked)} Sinew achievements!")

        except Exception as e:
            print(f"[PCBox] Achievement tracking error: {e}")

    def _export_pokemon_for_achievement(self):
        """
        Export the selected Pokemon as a .pks file for achievement rewards (DEV MODE ONLY)
        
        ENHANCED: Now uses UPO system to ensure proper PP values and validation.
        """
        print("[PCBox] *** DEV: Export triggered ***", file=sys.stderr, flush=True)

        if not self.selected_pokemon:
            print(
                "[PCBox] *** DEV: No Pokemon selected! ***",
                file=sys.stderr,
                flush=True,
            )
            self._show_warning("No Pokemon selected!")
            return

        pokemon = self.selected_pokemon
        print(
            f"[PCBox] *** DEV: Exporting {pokemon.get('species_name', 'Unknown')} ***",
            file=sys.stderr,
            flush=True,
        )

        raw_bytes = pokemon.get("raw_bytes")
        if not raw_bytes:
            print(
                "[PCBox] *** DEV: No raw bytes available - cannot export! ***",
                file=sys.stderr,
                flush=True,
            )
            self._show_warning("No raw bytes!\nCannot export")
            return

        if isinstance(raw_bytes, (list, bytearray)):
            raw_bytes = bytes(raw_bytes)

        if len(raw_bytes) < 80:
            print(
                f"[PCBox] *** DEV: Raw bytes too short ({len(raw_bytes)} bytes) ***",
                file=sys.stderr,
                flush=True,
            )
            self._show_warning(f"Invalid data!\nOnly {len(raw_bytes)} bytes")
            return

        species_name = pokemon.get("species_name", "Unknown")
        safe_name = "".join(
            c for c in species_name if c.isalnum() or c in " _-"
        ).strip()
        if not safe_name:
            safe_name = f"Pokemon_{pokemon.get('species', 0)}"

        script_dir = os.path.dirname(os.path.abspath(__file__))
        rewards_dir = os.path.join(script_dir, "data", "achievements", "rewards")
        print(
            f"[PCBox] *** DEV: Rewards dir: {rewards_dir} ***",
            file=sys.stderr,
            flush=True,
        )

        try:
            os.makedirs(rewards_dir, exist_ok=True)
        except Exception as e:
            print(
                f"[PCBox] *** DEV: Failed to create dir: {e} ***",
                file=sys.stderr,
                flush=True,
            )
            self._show_warning(f"Dir create failed!\n{str(e)[:20]}")
            return

        base_filename = f"{safe_name}.pks"
        filepath = os.path.join(rewards_dir, base_filename)

        counter = 1
        while os.path.exists(filepath):
            base_filename = f"{safe_name}_{counter}.pks"
            filepath = os.path.join(rewards_dir, base_filename)
            counter += 1

        print(
            f"[PCBox] *** DEV: Writing to {filepath} ***", file=sys.stderr, flush=True
        )

        try:
            # Try UPO-enhanced export (fixes PP values and validates)
            try:
                from gen3_converter import gen3_to_universal, universal_to_gen3
                from legality_engine import validate_pokemon, ValidationLevel

                # Get current game for correct data lookup
                current_game = self.get_current_game() if hasattr(self, "get_current_game") else "Emerald"
                current_game_display = current_game.title() if current_game else "Emerald"

                # Convert to UPO
                pokemon_upo = gen3_to_universal(raw_bytes[:80], current_game_display)
                
                # Validate before export
                errors = validate_pokemon(pokemon_upo, ValidationLevel.STANDARD)
                if errors:
                    print(f"[PCBox] *** DEV: Validation warnings: ***", file=sys.stderr, flush=True)
                    for error in errors:
                        print(f"  - {error}", file=sys.stderr, flush=True)
                else:
                    print(f"[PCBox] *** DEV: ✓ Validation passed ***", file=sys.stderr, flush=True)
                
                print(f"[PCBox] *** DEV: PID: 0x{pokemon_upo.pid:08X} ***", file=sys.stderr, flush=True)
                print(f"[PCBox] *** DEV: PID lowest bit: {pokemon_upo.pid & 1} ***", file=sys.stderr, flush=True)
                print(f"[PCBox] *** DEV: Species: {pokemon_upo.species} ***", file=sys.stderr, flush=True)
                print(f"[PCBox] *** DEV: Level: {pokemon_upo.level} ***", file=sys.stderr, flush=True)
                print(f"[PCBox] *** DEV: Met Level: {pokemon_upo.met_level} ***", file=sys.stderr, flush=True)
                print(f"[PCBox] *** DEV: Ability slot (from UPO): {pokemon_upo.ability_slot} ***", file=sys.stderr, flush=True)
                print(f"[PCBox] *** DEV: Shiny: {pokemon_upo.is_shiny} ***", file=sys.stderr, flush=True)
                print(f"[PCBox] *** DEV: Moves: ***", file=sys.stderr, flush=True)
                for i, move in enumerate(pokemon_upo.moves[:4]):
                    if move:
                        print(f"  {i+1}. ID={move.move_id}, PP={move.pp}, PP_Ups={move.pp_ups}", file=sys.stderr, flush=True)
                    else:
                        print(f"  {i+1}. (empty)", file=sys.stderr, flush=True)
                
                # Convert back to Gen 3 (this fixes PP values!)
                # Use PC format (80 bytes) for .pk3 export
                fixed_bytes = universal_to_gen3(pokemon_upo, "pc")
                
                # After conversion, verify what we wrote
                print(f"[PCBox] *** DEV: Re-reading exported bytes... ***", file=sys.stderr, flush=True)
                verify_upo = gen3_to_universal(fixed_bytes[:80], current_game_display)
                print(f"[PCBox] *** DEV: Verified PID: 0x{verify_upo.pid:08X} ***", file=sys.stderr, flush=True)
                print(f"[PCBox] *** DEV: Verified ability slot: {verify_upo.ability_slot} ***", file=sys.stderr, flush=True)
                print(f"[PCBox] *** DEV: PID & 1 = {verify_upo.pid & 1} ***", file=sys.stderr, flush=True)
                
                if verify_upo.ability_slot != (verify_upo.pid & 1):
                    print(f"[PCBox] *** DEV: ⚠️ WARNING: Ability slot mismatch! ***", file=sys.stderr, flush=True)
                    print(f"[PCBox] *** DEV:   Expected: {verify_upo.pid & 1} ***", file=sys.stderr, flush=True)
                    print(f"[PCBox] *** DEV:   Got: {verify_upo.ability_slot} ***", file=sys.stderr, flush=True)
                else:
                    print(f"[PCBox] *** DEV: ✓ Ability slot matches PID! ***", file=sys.stderr, flush=True)
                
                pks_data = fixed_bytes[:80]
                
                print(
                    f"[PCBox] *** DEV: Using UPO export (PP fixed) ***",
                    file=sys.stderr,
                    flush=True
                )
                
            except ImportError as import_err:
                # Fall back to simple export
                print(
                    f"[PCBox] *** DEV: UPO not available ({import_err}), using simple export ***",
                    file=sys.stderr,
                    flush=True
                )
                pks_data = raw_bytes[:80]
            
            # Write to file
            with open(filepath, "wb") as f:
                f.write(pks_data)
            
            print(
                f"[PCBox] *** DEV: SUCCESS! Exported {len(pks_data)} bytes to {filepath} ***",
                file=sys.stderr,
                flush=True,
            )
            self._show_warning(f"Exported!\n{base_filename}")
            
        except Exception as e:
            print(
                f"[PCBox] *** DEV: Export failed: {e} ***", file=sys.stderr, flush=True
            )
            import traceback
            traceback.print_exc()
            self._show_warning(f"Export failed!\n{str(e)[:20]}")