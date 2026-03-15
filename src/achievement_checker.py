#!/usr/bin/env python3

"""
achievement_checker.py — Achievement-checking mixin for the Sinew game screen.

GameScreen inherits AchievementCheckerMixin to get
all achievement-related methods without bloating main.py.
"""

import os
import time

from config import SAVE_PATHS


# =============================================================================
# Shared helper
# =============================================================================

def is_pokemon_shiny(pokemon):
    """
    Calculate whether a Pokemon is shiny from its TID/SID/PID values.

    Args:
        pokemon: dict with keys 'is_shiny', 'shiny', 'personality', 'ot_id', etc.

    Returns:
        bool: True if the Pokemon is shiny.
    """
    # Honour pre-computed flag first
    if pokemon.get("is_shiny") or pokemon.get("shiny", False):
        return True

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

    return (tid ^ sid ^ pid_low ^ pid_high) < 8


def check_hall_of_fame(raw_data) -> bool:
    """
    Check whether the player has ever entered the Hall of Fame.

    In Gen 3 saves the Hall of Fame sits at a fixed location outside the two
    rotating save slots:
      - Offset 0x1C000 in a standard 128 KB (0x20000-byte) save
      - Each of the 50 HoF entries is 60 bytes; the first 4 bytes of entry 0
        hold the first team member's personality value.
      - A blank / never-visited HoF reads as 0x00000000 or 0xFFFFFFFF.

    Args:
        raw_data: bytes or bytearray of the full save file.

    Returns:
        bool: True if a valid HoF entry exists.
    """
    if raw_data is None:
        return False
    try:
        HOF_OFFSET = 0x1C000
        if len(raw_data) < HOF_OFFSET + 4:
            return False
        import struct
        first_word = struct.unpack_from("<I", raw_data, HOF_OFFSET)[0]
        # 0x00000000 = never written; 0xFFFFFFFF = erased flash
        return first_word not in (0x00000000, 0xFFFFFFFF)
    except Exception:
        return False




class AchievementCheckerMixin:
    """
    Mixin that provides all achievement-checking methods to GameScreen.

    Requires the host class to have:
        self._achievement_manager
        self._achievement_notification
        self._sinew_game_data_cache
        self.games  (dict of game_name -> game_data)
        self.game_names  (list)
        self.current_game  (int index)
        self.width
        self.settings
        get_current_game_name()
        _load_current_save()
    """

    def _init_achievement_system(self):
        """Initialize the achievement notification system"""
        self._achievement_notification = None
        self._achievement_manager = None

        if init_achievement_system:
            try:
                self._achievement_manager, self._achievement_notification = (
                    init_achievement_system(self.width)
                )
                print("[GameScreen] Achievement system initialized")

                # Cache for Sinew aggregate: {game_name: contribution_dict}
                # Only the game that just changed is re-parsed; others use cached values.
                self._sinew_game_data_cache = {}
            except Exception as e:
                print(f"[GameScreen] Could not initialize achievements: {e}")

    def _check_all_achievements_on_startup(self):
        """Check achievements on startup - only parses the current (last active) game.
        Other games are handled lazily by _check_sinew_achievements_aggregate which
        uses per-game caching and only re-parses the game that changed."""
        if not self._achievement_manager:
            return

        # Determine current game from config SAVE_PATHS order
        current_game_name = (
            self.game_names[self.current_game]
            if self.game_names and self.current_game < len(self.game_names)
            else None
        )
        print(f"[Achievements] Startup check for current game: {current_game_name}")

        try:
            if current_game_name and current_game_name != "Sinew":
                game_data = self.games.get(current_game_name, {})
                # Use canonical save path from config as source of truth
                sav_path = game_data.get("sav")

                if sav_path and os.path.exists(sav_path):
                    try:
                        from save_data_manager import SaveDataManager
                        from achievements_data import (
                            check_achievement_unlocked,
                            get_achievements_for,
                        )

                        manager = SaveDataManager()
                        if manager.load_save(sav_path, game_hint=current_game_name):
                            loaded_game = (
                                manager.parser.game_code
                                if hasattr(manager, "parser") and manager.parser
                                else "unknown"
                            )
                            print(f"[Achievements] {current_game_name} loaded - game_code: {loaded_game}")  # pylint: disable=line-too-long  # noqa: E501

                            pokedex_data = (
                                manager.get_pokedex_count()
                                if hasattr(manager, "get_pokedex_count")
                                else {"caught": 0, "seen": 0}
                            )
                            party = manager.get_party() if hasattr(manager, "get_party") else []

                            if party:
                                for p in party:
                                    if p and not p.get("empty"):
                                        print(f"[Achievements] Startup {current_game_name} party[0]: level={p.get('level', 'NO LEVEL')}, species={p.get('species', '?')}")  # pylint: disable=line-too-long  # noqa: E501
                                        break

                            pc_pokemon = []
                            try:
                                for box_num in range(1, 15):
                                    if hasattr(manager, "get_box"):
                                        box = manager.get_box(box_num)
                                        if box:
                                            for p in box:
                                                if p and not p.get("empty"):
                                                    pc_pokemon.append(p)
                                if pc_pokemon:
                                    first = pc_pokemon[0]
                                    print(f"[Achievements] Startup {current_game_name} first PC Pokemon level: {first.get('level', 'NO LEVEL KEY')}")  # pylint: disable=line-too-long  # noqa: E501
                            except Exception as e:
                                print(f"[Achievements] Startup {current_game_name} PC load error: {e}")  # pylint: disable=line-too-long  # noqa: E501

                            owned_list = []
                            try:
                                if hasattr(manager, "get_pokedex_data"):
                                    pokedex = manager.get_pokedex_data()
                                    owned_list = pokedex.get("owned_list", [])
                            except Exception:
                                pass

                            playtime_hours = 0
                            try:
                                playtime = manager.get_play_time() if hasattr(manager,
                                    "get_play_time") else {}
                                playtime_hours = (playtime.get("hours",
                                    0) or 0) + ((playtime.get("minutes", 0) or 0) / 60.0)
                            except Exception:
                                pass

                            ach_save_data = {
                                "dex_caught": pokedex_data.get("caught", 0),
                                "dex_seen": pokedex_data.get("seen", 0),
                                "badges": manager.get_badge_count() if hasattr(manager,
                                    "get_badge_count") else 0,
                                "money": manager.get_money() if hasattr(manager,
                                    "get_money") else 0,
                                "party": party,
                                "pc_pokemon": pc_pokemon,
                                "owned_list": owned_list,
                                "playtime_hours": playtime_hours,
                                "has_hall_of_fame": check_hall_of_fame(
                                    manager.parser.data
                                    if hasattr(manager, "parser") and manager.parser
                                    and hasattr(manager.parser, "data")
                                    else None
                                ),
                            }

                            game_achievements = get_achievements_for(current_game_name)
                            pc_count = len([p for p in pc_pokemon if p and not p.get("empty")])
                            party_count = len([p for p in party if p and not p.get("empty")])

                            all_pokemon = [p for p in party + pc_pokemon if p
                                and not p.get("empty")]
                            max_level = max((p.get("level", 0) for p in all_pokemon), default=0)
                            pokemon_over_30 = sum(1 for p in all_pokemon if p.get("level", 0) >= 30)
                            pokemon_over_50 = sum(1 for p in all_pokemon if p.get("level", 0) >= 50)
                            pokemon_over_70 = sum(1 for p in all_pokemon if p.get("level", 0) >= 70)
                            pokemon_at_100 = sum(1 for p in all_pokemon if p.get("level", 0) >= 100)
                            shiny_count = sum(1 for p in all_pokemon if is_pokemon_shiny(p))

                            print(f"[Achievements] Startup {current_game_name}: dex={ach_save_data['dex_caught']}, badges={ach_save_data['badges']}, pc={pc_count}, party={party_count}, max_lv={max_level}")  # pylint: disable=line-too-long  # noqa: E501

                            # Log any legendaries found
                            legendary_ids = [144,145,146,150,151,377,378,379,380,381,382,383,384,385,386]  # pylint: disable=line-too-long  # noqa: E501
                            found_legendaries = [s for s in legendary_ids if s in owned_list]
                            if found_legendaries:
                                print(f"[Achievements] Startup {current_game_name} has legendaries: {found_legendaries}")  # pylint: disable=line-too-long  # noqa: E501

                            # Update per-game tracking
                            self._achievement_manager.set_current_game(current_game_name)
                            self._achievement_manager.update_tracking("dex_count",
                                ach_save_data["dex_caught"])
                            self._achievement_manager.update_tracking("dex_seen",
                                ach_save_data["dex_seen"])
                            self._achievement_manager.update_tracking("badges",
                                ach_save_data["badges"])
                            self._achievement_manager.update_tracking("money",
                                ach_save_data["money"])
                            self._achievement_manager.update_tracking("playtime_hours",
                                playtime_hours)
                            self._achievement_manager.update_tracking("party_size", party_count)
                            self._achievement_manager.update_tracking("pc_pokemon", pc_count)
                            self._achievement_manager.update_tracking("total_pokemon",
                                pc_count + party_count)
                            self._achievement_manager.update_tracking("any_pokemon_level",
                                max_level)
                            self._achievement_manager.update_tracking("pokemon_over_30",
                                pokemon_over_30)
                            self._achievement_manager.update_tracking("pokemon_over_50",
                                pokemon_over_50)
                            self._achievement_manager.update_tracking("pokemon_over_70",
                                pokemon_over_70)
                            self._achievement_manager.update_tracking("pokemon_at_100",
                                pokemon_at_100)
                            self._achievement_manager.update_tracking("shiny_count", shiny_count)
                            self._achievement_manager.update_tracking("owned_set", set(owned_list))
                            self._achievement_manager.update_tracking(
                                "has_hall_of_fame",
                                ach_save_data.get("has_hall_of_fame", False)
                            )

                            unlocked_count = 0
                            for ach in game_achievements:
                                if ach.get("game") != current_game_name:
                                    continue
                                if not self._achievement_manager.is_unlocked(ach["id"]):
                                    if check_achievement_unlocked(ach, ach_save_data):
                                        self._achievement_manager.progress[ach["id"]] = {
                                            "unlocked": True,
                                            "unlocked_at": time.time(),
                                            "reward_claimed": False,
                                        }
                                        self._achievement_manager.stats["total_unlocked"] = (
                                            self._achievement_manager.stats.get("total_unlocked",
                                                0) + 1
                                        )
                                        self._achievement_manager.stats["total_points"] = (
                                            self._achievement_manager.stats.get("total_points",
                                                0) + ach.get("points", 0)
                                        )
                                        unlocked_count += 1

                            if unlocked_count > 0:
                                print(f"[Achievements] Startup: {current_game_name} - {unlocked_count} achievements unlocked")  # pylint: disable=line-too-long  # noqa: E501

                    except Exception as e:
                        print(f"[Achievements] Startup error for {current_game_name}: {e}")
                else:
                    print(f"[Achievements] Skipping {current_game_name} - no save file")

            # Sinew aggregate: populates cache for ALL games (each only parsed once,
            # subsequent calls only re-parse the game that changed).
            self._check_sinew_achievements_aggregate()

            # Re-validate and save.
            # sinew_data_loaded=True only when the cache is non-empty, meaning at least
            # one save was successfully parsed. If the cache is empty (no local ROMs /
            # all saves at external paths), we cannot trust the aggregate zeros and must
            # not revoke Sinew achievements.
            sinew_data_loaded = bool(getattr(self, "_sinew_game_data_cache", {}))
            revoked = self._achievement_manager.revalidate_achievements(
                sinew_data_loaded=sinew_data_loaded
            )
            if revoked:
                print(f"[Achievements] Revoked {len(
                    revoked)} incorrectly unlocked achievements on startup")

            self._achievement_manager._save_progress()

            # Restore context to current game
            if current_game_name and current_game_name != "Sinew":
                self._load_current_save()

            print("[Achievements] Startup check complete")

        except Exception as e:
            print(f"[Achievements] Startup check error: {e}")
            import traceback
            traceback.print_exc()

    def _check_achievements_for_current_game(self):
        """Check achievements based on current game's save data"""
        if not self._achievement_manager:
            print("[Achievements] Manager not initialized, skipping achievement check")
            return

        try:
            # Get current game name
            game_name = self.get_current_game_name()
            if not game_name or game_name == "Sinew":
                # Even on Sinew screen, check Sinew achievements with aggregate data
                self._check_sinew_achievements_aggregate()
                return

            # Get save data from manager
            from save_data_manager import get_manager
            manager = get_manager()
            if not manager or not manager.loaded:
                return

            # Build achievement-compatible save data dict from manager
            pokedex_data = (
                manager.get_pokedex_count()
                if hasattr(manager, "get_pokedex_count")
                else {"caught": 0, "seen": 0}
            )

            # Get party Pokemon
            party = manager.get_party() if hasattr(manager, "get_party") else []

            # Get PC Pokemon (all boxes) - use get_box for properly enriched data
            pc_pokemon = []
            try:
                for box_num in range(1, 15):
                    if hasattr(manager, "get_box"):
                        box = manager.get_box(box_num)
                        if box:
                            for p in box:
                                if p and not p.get("empty"):
                                    pc_pokemon.append(p)
                print(
                    f"[Achievements] {game_name} PC Pokemon: {len(pc_pokemon)} from 14 boxes"
                )
                if pc_pokemon:
                    first = pc_pokemon[0]
                    print(
                        f"[Achievements] First PC Pokemon keys: {list(first.keys()) if isinstance(
                            first, dict) else type(first)}"
                    )
            except Exception as e:
                print(f"[Achievements] Error getting PC Pokemon: {e}")
                import traceback
                traceback.print_exc()

            # Get owned list from pokedex
            owned_list = []
            try:
                if hasattr(manager, "get_pokedex_data"):
                    pokedex = manager.get_pokedex_data()
                    owned_list = pokedex.get("owned_list", [])
                    print(
                        f"[Achievements] {game_name} owned_list: {len(owned_list)} species"
                    )
            except Exception as e:
                print(f"[Achievements] Error getting owned_list: {e}")

            ach_save_data = {
                "dex_caught": pokedex_data.get("caught", 0),
                "dex_seen": pokedex_data.get("seen", 0),
                "badges": (
                    manager.get_badge_count()
                    if hasattr(manager, "get_badge_count")
                    else 0
                ),
                "money": manager.get_money() if hasattr(manager, "get_money") else 0,
                "party": party,
                "pc_pokemon": pc_pokemon,
                "owned_list": owned_list,
            }

            # Add raw_data for FRLG Sevii achievement checking
            if (
                hasattr(manager, "parser")
                and manager.parser
                and hasattr(manager.parser, "data")
            ):
                ach_save_data["raw_data"] = manager.parser.data
                ach_save_data["has_hall_of_fame"] = check_hall_of_fame(manager.parser.data)

                game_name = self.get_current_game_name()
                if game_name in ("FireRed", "LeafGreen"):
                    try:
                        from save_writer import has_national_dex as check_nat_dex
                        from save_writer import has_rainbow_pass as check_rainbow

                        ach_save_data["has_national_dex"] = check_nat_dex(
                            manager.parser.data, "FRLG", game_name
                        )
                        ach_save_data["has_rainbow_pass"] = check_rainbow(
                            manager.parser.data, "FRLG"
                        )
                        print(
                            f"[Achievements] {game_name} Sevii prereqs: nat_dex={ach_save_data['has_national_dex']}, rainbow_pass={ach_save_data['has_rainbow_pass']}"  # pylint: disable=line-too-long  # noqa: E501
                        )
                    except Exception as e:
                        print(f"[Achievements] Error checking FRLG Sevii prereqs: {e}")
                        import traceback
                        traceback.print_exc()
                        ach_save_data["has_national_dex"] = False
                        ach_save_data["has_rainbow_pass"] = False

            # Get playtime if available
            if hasattr(manager, "get_play_time"):
                try:
                    playtime = manager.get_play_time()
                    hours = playtime.get("hours", 0) or 0
                    minutes = playtime.get("minutes", 0) or 0
                    ach_save_data["playtime_hours"] = hours + (minutes / 60.0)
                except Exception:
                    ach_save_data["playtime_hours"] = 0
            elif hasattr(manager, "parser") and manager.parser:
                try:
                    hours = getattr(manager.parser, "play_hours", 0) or 0
                    minutes = getattr(manager.parser, "play_minutes", 0) or 0
                    ach_save_data["playtime_hours"] = hours + (minutes / 60.0)
                except Exception:
                    ach_save_data["playtime_hours"] = 0

            playtime_h = ach_save_data.get("playtime_hours", 0)
            pc_count = len(pc_pokemon)
            party_count = len([p for p in party if p and not p.get("empty")])

            max_level = 0
            pokemon_over_30 = 0
            pokemon_over_50 = 0
            pokemon_over_70 = 0
            pokemon_at_100 = 0
            shiny_count = 0

            all_pokemon = [p for p in party + pc_pokemon if p and not p.get("empty")]
            total_pokemon = len(all_pokemon)

            for p in all_pokemon:
                level = p.get("level", 0)
                if level > max_level:
                    max_level = level
                if level >= 30:
                    pokemon_over_30 += 1
                if level >= 50:
                    pokemon_over_50 += 1
                if level >= 70:
                    pokemon_over_70 += 1
                if level >= 100:
                    pokemon_at_100 += 1
                if is_pokemon_shiny(p):
                    shiny_count += 1

            print(
                f"[Achievements] Checking {game_name}:"
                f" badges={ach_save_data['badges']},"
                f" dex={ach_save_data['dex_caught']}, money={ach_save_data['money']},"
                f" party={party_count}, pc={pc_count},"
                f" playtime={playtime_h:.1f}h, owned={len(owned_list)} species"
            )

            legendaries = [144, 145, 146, 150, 151, 377, 378, 379, 380, 381, 382, 383, 384, 385,
                386]
            found_legendaries = [s for s in legendaries if s in owned_list]
            if found_legendaries:
                print(
                    f"[Achievements] {game_name} has legendaries in owned_list: {found_legendaries}"
                )
            print(
                f"[Achievements] {game_name} Pokemon: total={total_pokemon},"
                f" max_lv={max_level}, lv50+={pokemon_over_50},"
                f" lv100={pokemon_at_100}, shiny={shiny_count}"
            )

            self._achievement_manager.set_current_game(game_name)
            self._achievement_manager.update_tracking("dex_count", ach_save_data["dex_caught"])
            self._achievement_manager.update_tracking("dex_seen", ach_save_data["dex_seen"])
            self._achievement_manager.update_tracking("badges", ach_save_data["badges"])
            self._achievement_manager.update_tracking("money", ach_save_data["money"])
            self._achievement_manager.update_tracking("playtime_hours", playtime_h)
            self._achievement_manager.update_tracking("party_size", party_count)
            self._achievement_manager.update_tracking("pc_pokemon", pc_count)
            self._achievement_manager.update_tracking("total_pokemon", total_pokemon)
            self._achievement_manager.update_tracking("any_pokemon_level", max_level)
            self._achievement_manager.update_tracking("pokemon_over_30", pokemon_over_30)
            self._achievement_manager.update_tracking("pokemon_over_50", pokemon_over_50)
            self._achievement_manager.update_tracking("pokemon_over_70", pokemon_over_70)
            self._achievement_manager.update_tracking("pokemon_at_100", pokemon_at_100)
            self._achievement_manager.update_tracking("shiny_count", shiny_count)
            self._achievement_manager.update_tracking("owned_set", set(owned_list))
            self._achievement_manager.update_tracking(
                "has_hall_of_fame", ach_save_data.get("has_hall_of_fame", False)
            )

            newly_unlocked = self._achievement_manager.check_and_unlock(ach_save_data, game_name)

            force_unlocked = self._achievement_manager.force_check_by_tracking(game_name)
            if force_unlocked:
                newly_unlocked.extend(force_unlocked)

            if newly_unlocked:
                print(
                    f"[Achievements] Unlocked {len(newly_unlocked)} achievements for {game_name}!"
                )

            self._check_sinew_achievements_aggregate()

        except Exception as e:
            print(f"[Achievements] Error checking achievements: {e}")
            import traceback
            traceback.print_exc()

    def _check_sinew_achievements_aggregate(self):
        """Check Sinew achievements based on aggregate data from all saves.

        PERFORMANCE: Uses self._sinew_game_data_cache to avoid re-parsing every
        save on every call.  Only the currently active game is re-parsed from disk;
        all other games use their cached contribution from the last time they were
        the active game (or from startup).
        """
        if not self._achievement_manager:
            return

        if not hasattr(self, "_sinew_game_data_cache"):
            self._sinew_game_data_cache = {}

        STARTER_LINES = [
            {1, 2, 3},        # Bulbasaur line
            {4, 5, 6},        # Charmander line
            {7, 8, 9},        # Squirtle line
            {252, 253, 254},  # Treecko line
            {255, 256, 257},  # Torchic line
            {258, 259, 260},  # Mudkip line
        ]
        EEVEELUTION_SPECIES = {133, 134, 135, 136, 196, 197}

        current_game_name = (
            self.game_names[self.current_game]
            if self.game_names and self.current_game < len(self.game_names)
            else None
        )

        def _parse_game_for_cache(game_name, sav_path):
            """Parse one save file and return a contribution dict for the cache."""
            from save_data_manager import SaveDataManager
            actual_path = sav_path
            if not actual_path or not os.path.exists(actual_path):
                print(f"[Achievements] No save found at {sav_path} for {game_name}")
                return None
            print(f"[Achievements] Found save for {game_name} at {actual_path}")

            manager = SaveDataManager()
            if not manager.load_save(actual_path, game_hint=game_name):
                print(f"[Achievements] Failed to load {game_name} for Sinew aggregate")
                return None

            badges = manager.get_badge_count() if hasattr(manager, "get_badge_count") else 0
            party = manager.get_party() if hasattr(manager, "get_party") else []
            active_party = [p for p in party if p and not p.get("empty")]

            pc_pokemon = []
            pc_count_raw = 0
            try:
                pc_count_raw = manager.get_pc_pokemon_count() if hasattr(manager,
                    "get_pc_pokemon_count") else 0
                for box_num in range(1, 15):
                    if hasattr(manager, "get_box"):
                        box = manager.get_box(box_num)
                        if box:
                            pc_pokemon.extend(p for p in box if p and not p.get("empty"))
            except Exception:
                pass

            all_pokemon = active_party + pc_pokemon
            level100 = sum(1 for p in all_pokemon if p.get("level", 0) >= 100)
            level50plus = sum(1 for p in all_pokemon if p.get("level", 0) >= 50)
            shiny_count = sum(1 for p in all_pokemon if is_pokemon_shiny(p))
            eeveelutions = {p.get("species") for p in all_pokemon if p.get(
                "species") in EEVEELUTION_SPECIES}

            dex_caught = 0
            owned_set = set()
            try:
                dex_data = manager.get_pokedex_count() if hasattr(manager,
                    "get_pokedex_count") else {"caught": 0}
                dex_caught = dex_data.get("caught", 0)
                if hasattr(manager, "get_pokedex_data"):
                    owned_set = set(manager.get_pokedex_data().get("owned_list", []))
            except Exception:
                pass

            money = 0
            try:
                money = manager.get_money() if hasattr(manager, "get_money") else 0
            except Exception:
                pass

            playtime_hours = 0.0
            try:
                pt = manager.get_play_time() if hasattr(manager, "get_play_time") else {}
                playtime_hours = (pt.get("hours", 0) or 0) + ((pt.get("minutes", 0) or 0) / 60.0)
            except Exception:
                pass

            is_frlg = game_name in ["FireRed", "LeafGreen"]
            regional_size = 151 if is_frlg else 202

            has_hof = check_hall_of_fame(
                manager.parser.data
                if hasattr(manager, "parser") and manager.parser
                and hasattr(manager.parser, "data")
                else None
            )

            print(
                f"[Achievements] Sinew cache: {game_name} -"
                f" {badges} badges, {dex_caught} dex, {len(all_pokemon)} pokemon,"
                f" hof={has_hof}"
            )

            return {
                "badges": badges,
                "dex_caught": dex_caught,
                "money": money,
                "playtime_hours": playtime_hours,
                "games_with_badges": 1 if badges > 0 else 0,
                "games_with_4plus_badges": 1 if badges >= 4 else 0,
                "games_with_champion": 1 if has_hof else 0,
                "games_with_full_party": 1 if len(active_party) >= 6 else 0,
                "games_with_full_dex": 1 if dex_caught >= regional_size else 0,
                "owned_set": owned_set,
                "pc_count": pc_count_raw,
                "shiny_count": shiny_count,
                "level100": level100,
                "level50plus": level50plus,
                "eeveelutions": eeveelutions,
            }

        try:
            # Update cache: re-parse current game, use cache for all others
            for game_name, game_data in self.games.items():
                if game_name == "Sinew":
                    continue
                sav_path = game_data.get("sav")
                if not sav_path or not os.path.exists(sav_path):
                    # sav path from self.games is authoritative (may be external).
                    # Only fall back to config SAVE_PATHS when self.games has no
                    # entry at all — never silently override an external path.
                    if not sav_path:
                        from config import SAVE_PATHS
                        sav_path = SAVE_PATHS.get(game_name, "")
                    if not sav_path or not os.path.exists(sav_path):
                        continue

                is_current = (game_name == current_game_name)
                not_cached = (game_name not in self._sinew_game_data_cache)

                if is_current or not_cached:
                    contribution = _parse_game_for_cache(game_name, sav_path)
                    if contribution is not None:
                        self._sinew_game_data_cache[game_name] = contribution
                # else: silently use existing cached values

            # Aggregate from cache
            total_badges = 0
            total_dex_caught = 0
            total_money = 0
            total_playtime = 0.0
            games_with_badges = 0
            games_with_4plus_badges = 0
            games_with_champion = 0
            games_with_full_party = 0
            games_with_full_dex = 0
            combined_pokedex = set()
            total_pc_pokemon = 0
            total_shiny_pokemon = 0
            total_level100 = 0
            total_level50plus = 0
            owned_eeveelutions = set()

            for contrib in self._sinew_game_data_cache.values():
                total_badges += contrib["badges"]
                total_dex_caught += contrib["dex_caught"]
                total_money += contrib["money"]
                total_playtime += contrib["playtime_hours"]
                games_with_badges += contrib["games_with_badges"]
                games_with_4plus_badges += contrib["games_with_4plus_badges"]
                games_with_champion += contrib["games_with_champion"]
                games_with_full_party += contrib["games_with_full_party"]
                games_with_full_dex += contrib["games_with_full_dex"]
                combined_pokedex |= contrib["owned_set"]
                total_pc_pokemon += contrib["pc_count"]
                total_shiny_pokemon += contrib["shiny_count"]
                total_level100 += contrib["level100"]
                total_level50plus += contrib["level50plus"]
                owned_eeveelutions |= contrib["eeveelutions"]

            # Also scan Sinew Storage for Pokemon stats
            try:
                from sinew_storage import get_sinew_storage

                sinew_storage = get_sinew_storage()

                if sinew_storage and sinew_storage.is_loaded():
                    sinew_pokemon_count = 0
                    for box_num in range(1, 21):  # 20 boxes
                        box_data = sinew_storage.get_box(box_num)
                        if box_data:
                            for pokemon in box_data:
                                if pokemon and not pokemon.get("empty"):
                                    sinew_pokemon_count += 1
                                    level = pokemon.get("level", 0)
                                    species = pokemon.get("species", 0)

                                    if level >= 100:
                                        total_level100 += 1
                                    if level >= 50:
                                        total_level50plus += 1

                                    if is_pokemon_shiny(pokemon):
                                        total_shiny_pokemon += 1
                                        print(f"[Achievements] Found shiny in Sinew: species {species} in box {box_num}")  # pylint: disable=line-too-long  # noqa: E501
                                    if species:
                                        combined_pokedex.add(species)

                                    if species in EEVEELUTION_SPECIES:
                                        owned_eeveelutions.add(species)

                    total_pc_pokemon += sinew_pokemon_count
            except Exception as e:
                print(f"[Achievements] Could not scan Sinew storage: {e}")

            # Count starter lines owned (using combined_pokedex)
            starter_lines_owned = sum(1 for line in STARTER_LINES if line & combined_pokedex)
            # Count eeveelutions from combined_pokedex too
            for species in EEVEELUTION_SPECIES:
                if species in combined_pokedex:
                    owned_eeveelutions.add(species)

            # Check if dev mode is activated
            dev_mode_activated = False
            try:
                from settings import load_sinew_settings as load_settings
                settings = load_settings()
                dev_mode_activated = settings.get("dev_mode", False)
            except Exception:
                pass

            print(
                f"[Achievements] Sinew aggregate:"
                f" badges={total_badges}, champions={games_with_champion},"
                f" dex={len(combined_pokedex)}, money={total_money},"
                f" playtime={total_playtime:.1f}h"
            )
            print(
                f"[Achievements] Pokemon stats: pc={total_pc_pokemon},"
                f" shiny={total_shiny_pokemon},"
                f" lv100={total_level100}, lv50+={total_level50plus}"
            )
            print(
                f"[Achievements] Special: starters={starter_lines_owned}/6,"
                f" eeveelutions={len(owned_eeveelutions)}/5,"
                f" dev_mode={dev_mode_activated}, full_dex={games_with_full_dex}"
            )

            # Debug: show if legendaries are in combined_pokedex
            legendaries = [150, 151, 380, 381, 382, 383, 384, 385, 386, 144, 145, 146, 377, 378,
                379]
            found_legendaries = [s for s in legendaries if s in combined_pokedex]
            if found_legendaries:
                print(f"[Achievements] Legendaries in combined_pokedex: {found_legendaries}")

            # Update tracking for Sinew achievements - SET CURRENT GAME TO SINEW
            self._achievement_manager.set_current_game("Sinew")
            self._achievement_manager.update_tracking("global_badges", total_badges)
            self._achievement_manager.update_tracking("global_dex_count", total_dex_caught)
            self._achievement_manager.update_tracking("combined_pokedex", len(combined_pokedex))
            self._achievement_manager.update_tracking("combined_pokedex_set", combined_pokedex)
            self._achievement_manager.update_tracking("global_money", total_money)
            self._achievement_manager.update_tracking("global_playtime", total_playtime)
            self._achievement_manager.update_tracking("global_champions", games_with_champion)
            self._achievement_manager.update_tracking("games_with_badges", games_with_badges)
            self._achievement_manager.update_tracking("games_with_4plus_badges",
                games_with_4plus_badges)
            self._achievement_manager.update_tracking("games_with_full_dex", games_with_full_dex)
            self._achievement_manager.update_tracking("global_pc_pokemon", total_pc_pokemon)
            self._achievement_manager.update_tracking("global_shiny_pokemon", total_shiny_pokemon)
            self._achievement_manager.update_tracking("global_level100_pokemon", total_level100)
            self._achievement_manager.update_tracking("global_level50plus_pokemon",
                total_level50plus)
            self._achievement_manager.update_tracking("global_full_parties", games_with_full_party)
            self._achievement_manager.update_tracking("global_starters", starter_lines_owned)
            self._achievement_manager.update_tracking("global_eeveelutions",
                len(owned_eeveelutions))
            self._achievement_manager.update_tracking("dev_mode_activated", dev_mode_activated)

            # Check Sinew progression achievements
            from achievements_data import get_achievements_for

            sinew_achievements = get_achievements_for("Sinew")

            for ach in sinew_achievements:
                if self._achievement_manager.is_unlocked(ach["id"]):
                    continue

                hint = ach.get("hint", "")
                unlocked = False

                if "global_badges >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_badges >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "global_dex_count >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_dex_caught >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "global_champions >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_champion >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "games_with_badges >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_badges >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "games_with_4plus_badges >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_4plus_badges >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "games_with_full_dex >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_full_dex >= required:
                            unlocked = True
                            print(f"[Achievements] Regional dex achievement: {games_with_full_dex}/{required}")  # pylint: disable=line-too-long  # noqa: E501
                    except Exception:
                        pass

                if "global_money >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_money >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "global_playtime >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_playtime >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "combined_pokedex >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if len(combined_pokedex) >= required:
                            unlocked = True
                            if required == 386:
                                print(f"[Achievements] DIRTY DEX COMPLETE! {len(
                                    combined_pokedex)}/386 unique species across all saves!")
                    except Exception:
                        pass

                if "owns_species_" in hint and "owns_species_380_or_381" not in hint:
                    try:
                        species_id = int(hint.split("owns_species_")[1].split("_")[0])
                        if species_id in combined_pokedex:
                            unlocked = True
                            print(
                                f"[Achievements] Legendary unlocked: {ach['name']}"
                                f" (species {species_id} found in combined pokedex)"
                            )
                        else:
                            if species_id in [150, 151, 380, 381, 382, 383, 384, 385, 386]:
                                print(f"[Achievements] Legendary NOT in pokedex: species {species_id} ({ach['name']})")  # pylint: disable=line-too-long  # noqa: E501
                    except Exception as e:
                        print(f"[Achievements] Error checking legendary {hint}: {e}")

                if "owns_species_380_or_381" in hint:
                    if 380 in combined_pokedex or 381 in combined_pokedex:
                        unlocked = True
                        print("[Achievements] Latias/Latios unlocked!")
                    else:
                        print(f"[Achievements] Latias/Latios check: 380 in pokedex={380 in combined_pokedex}, 381 in pokedex={381 in combined_pokedex}")  # pylint: disable=line-too-long  # noqa: E501

                if "owns_regi_trio" in hint:
                    if (
                        377 in combined_pokedex
                        and 378 in combined_pokedex
                        and 379 in combined_pokedex
                    ):
                        unlocked = True

                if "owns_weather_trio" in hint:
                    if (
                        382 in combined_pokedex
                        and 383 in combined_pokedex
                        and 384 in combined_pokedex
                    ):
                        unlocked = True

                if "global_pc_pokemon >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_pc_pokemon >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "global_shiny_pokemon >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_shiny_pokemon >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "global_level100_pokemon >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_level100 >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "global_level50plus_pokemon >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if total_level50plus >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "global_full_parties >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if games_with_full_party >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "global_starters >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if starter_lines_owned >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "global_eeveelutions >=" in hint:
                    try:
                        required = int(hint.split(">=")[1].strip().split()[0])
                        if len(owned_eeveelutions) >= required:
                            unlocked = True
                    except Exception:
                        pass

                if "dev_mode_activated == True" in hint:
                    if dev_mode_activated:
                        unlocked = True

                if unlocked:
                    self._achievement_manager.unlock(ach["id"], ach)
                    print(f"[Achievements] Unlocked Sinew achievement: {ach['name']}")

            # Also check Sinew Storage achievements
            self._check_sinew_storage_achievements()

            # Force check any Sinew achievements that might have been missed
            force_unlocked = self._achievement_manager.force_check_by_tracking("Sinew")
            if force_unlocked:
                print(f"[Achievements] Force unlocked {len(
                    force_unlocked)} Sinew achievements by tracking!")

        except Exception as e:
            print(f"[Achievements] Error checking Sinew achievements: {e}")
            import traceback
            traceback.print_exc()

    def _on_event_claimed(self, event_key):
        """
        Callback when an event item is claimed from the Events screen.
        Triggers the corresponding achievement unlock.
        """
        print(f"[Sinew] Event claimed: {event_key}")

        # Map event keys to achievement IDs
        achievement_map = {
            "eon_ticket": "SINEW_107",  # Southern Island Pass
            "aurora_ticket": "SINEW_108",  # Birth Island Pass
            "mystic_ticket": "SINEW_109",  # Navel Rock Pass
            "old_sea_map": "SINEW_110",  # Faraway Island Pass
        }

        # Unlock the per-event achievement
        ach_id = achievement_map.get(event_key)
        if ach_id and self._achievement_manager:
            try:
                from achievements_data import get_achievements_for

                sinew_achs = get_achievements_for("Sinew")
                for ach in sinew_achs:
                    if ach["id"] == ach_id:
                        self._achievement_manager.unlock_achievement(ach)
                        break
            except Exception as e:
                print(f"[Sinew] Error unlocking event achievement: {e}")

        # Check if all 4 events have been claimed across any games for the collector achievement.
        # events_claimed is now per-game: { "Ruby": {"eon_ticket": true}, "LeafGreen": {...} }
        # We flatten across all games to see if every ticket has been given out at least once.
        try:
            from settings import load_sinew_settings

            data = load_sinew_settings()
            all_claimed = data.get("events_claimed", {})

            claimed_anywhere = set()
            for game_data in all_claimed.values():
                if isinstance(game_data, dict):
                    for k, v in game_data.items():
                        if v:
                            claimed_anywhere.add(k)

            all_four = {"eon_ticket", "aurora_ticket", "mystic_ticket", "old_sea_map"}
            if all_four.issubset(claimed_anywhere):
                from achievements_data import get_achievements_for

                sinew_achs = get_achievements_for("Sinew")
                for ach in sinew_achs:
                    if ach.get("hint") == "all_events_claimed":
                        self._achievement_manager.unlock_achievement(ach)
                        break
        except Exception as e:
            print(f"[Sinew] Error checking all events: {e}")

    def _check_sinew_storage_achievements(self):
        """Check achievements based on Sinew storage contents"""
        if not self._achievement_manager:
            return

        try:
            from sinew_storage import get_sinew_storage
            sinew_storage = get_sinew_storage()

            if not sinew_storage or not sinew_storage.is_loaded():
                return

            total_pokemon = sinew_storage.get_total_pokemon_count()
            total_shinies = 0

            for box_num in range(1, 21):  # 20 boxes
                box_data = sinew_storage.get_box(box_num)
                if box_data:
                    for poke in box_data:
                        if poke and not poke.get("empty"):
                            if is_pokemon_shiny(poke):
                                total_shinies += 1
                                print(
                                    f"[Achievements] Sinew storage shiny: species {poke.get(
                                        'species', 0)} in box {box_num}"
                                )

            transfer_count = self._achievement_manager.get_stat("sinew_transfers", 0)
            evolution_count = self._achievement_manager.get_stat("sinew_evolutions", 0)

            print(
                f"[Achievements] Sinew storage:"
                f" {total_pokemon} Pokemon, {total_shinies} shiny,"
                f" {transfer_count} transfers, {evolution_count} evolutions"
            )

            self._achievement_manager.set_current_game("Sinew")
            self._achievement_manager.update_tracking("sinew_pokemon", total_pokemon)
            self._achievement_manager.update_tracking("shiny_count", total_shinies)
            self._achievement_manager.update_tracking("sinew_transfers", transfer_count)
            self._achievement_manager.update_tracking("sinew_evolutions", evolution_count)

            self._achievement_manager.check_sinew_achievements(
                sinew_storage_count=total_pokemon,
                transfer_count=transfer_count,
                shiny_count=total_shinies,
                evolution_count=evolution_count,
            )

        except ImportError:
            pass
        except Exception as e:
            print(f"[Achievements] Error checking Sinew storage: {e}")

    def _test_achievement_notification(self):
        """Test method to trigger a fake achievement notification (for development)"""
        if self._achievement_notification:
            test_ach = {
                "id": "test_001",
                "name": "Test Achievement",
                "desc": "This is a test achievement",
                "game": "Sinew",
                "points": 50,
            }
            self._achievement_notification.queue_achievement(test_ach)
            print("[Achievements] Test notification queued")


# Resolve the import that the mixin methods need at class definition time
try:
    from achievements import init_achievement_system
except ImportError:
    init_achievement_system = None