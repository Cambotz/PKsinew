"""
achievements_data.py

Generates 100 achievements per game for:
 - Ruby, Sapphire, Emerald, FireRed, LeafGreen
and 100 cross-game "Sinew" achievements.

Each achievement is a dict:
{
    "id": "RUBY_001",
    "name": "First Steps",
    "desc": "Start your Ruby adventure",
    "category": "Story" / "Dex" / "Gyms" / "Legendaries" / "Trainer" / "Exploration" / "Items" / "Stats" / "Misc",
    "game": "Ruby" / "Sinew",
    "hint": "short hint of how to check (for authoring check_achievement_unlocked)"
    "reward": {"type": "theme", "value": "Theme Name.json"} or {"type": "pokemon", "value": "Mew.pks"}
    # unlocked boolean is not stored here - runtime state
}

Use get_achievements_for(game) to retrieve the list.
Use check_achievement_unlocked(achievement, save) as a template to implement checks against your parsed save data.
"""

from typing import List, Dict

GAMES = ["Ruby", "Sapphire", "Emerald", "FireRed", "LeafGreen"]
GAME_PREFIX = {
    "Ruby": "RUBY",
    "Sapphire": "SAPP",
    "Emerald": "EMER",
    "FireRed": "FR",
    "LeafGreen": "LG",
    "Sinew": "SINEW"
}

# =============================================================================
# ALTERING CAVE POKEMON
# =============================================================================
# These 7 Pokemon were supposed to be unlockable in Altering Cave via Mystery Events
# but the events were never distributed. Players can obtain them by finding Zubat
# caught in Altering Cave and using the "Echoes" slot machine feature.
#
# Location IDs for Altering Cave:
#   - RSE: 183
#   - Emerald exclusive: 210
#
# Zubat species ID: 41

ALTERING_CAVE_LOCATIONS = (183, 210)  # RSE and Emerald Altering Cave location IDs
ALTERING_CAVE_ZUBAT_SPECIES = 41

ALTERING_CAVE_POKEMON = [
    {"species": 179, "name": "Mareep"},
    {"species": 190, "name": "Aipom"},
    {"species": 204, "name": "Pineco"},
    {"species": 213, "name": "Shuckle"},
    {"species": 234, "name": "Stantler"},
    {"species": 228, "name": "Houndour"},
    {"species": 235, "name": "Smeargle"},
]

# =============================================================================
# REWARD MAPPINGS
# =============================================================================
# Maps achievement IDs to their rewards
# Types: "theme" (unlocks a theme), "pokemon" (grants a .pks file), "both" (both)

ACHIEVEMENT_REWARDS = {
    # Mythical Pokemon + Theme rewards (major milestones - UNCHANGED, before legendaries)
    "SINEW_033": {"type": "both", "theme": "GB classic.json", "pokemon_achievement": "SINEW_033", 
                  "theme_name": "GB Classic", "pokemon_name": "Celebi"},  # Complete 1 Regional Dex
    "SINEW_030": {"type": "both", "theme": "Champion Gold.json", "pokemon_achievement": "SINEW_030",
                  "theme_name": "Champion Gold", "pokemon_name": "Jirachi"},  # Champion in All 5 Games
    "SINEW_008": {"type": "both", "theme": "Mew.json", "pokemon_achievement": "SINEW_008",
                  "theme_name": "Mew", "pokemon_name": "Mew"},  # Sinew Dex: 300 Pokemon
    "SINEW_035": {"type": "pokemon", "pokemon_achievement": "SINEW_035", "name": "Shiny Mew"},  # Complete All 5 Regional Dexes
    
    # NEW Legendary Pokemon rewards
    "SINEW_049": {"type": "pokemon", "pokemon_achievement": "SINEW_049", "name": "Ho-Oh"},  # Own Legendary Birds (NEW)
    "SINEW_051": {"type": "pokemon", "pokemon_achievement": "SINEW_051", "name": "Lugia"},  # Own Weather Trio
    "SINEW_104": {"type": "pokemon", "pokemon_achievement": "SINEW_104", "name": "Deoxys"},  # Dirty Dex: Catch 'Em All! (386 Pokemon)
    
    # Theme-only rewards - UNCHANGED (before legendaries section)
    "SINEW_027": {"type": "theme", "value": "Ash Ketchum.json", "name": "Ash Ketchum"},  # Become Champion Once
    "SINEW_037": {"type": "theme", "value": "Team Rocket.json", "name": "Team Rocket"},  # Earn 500,000 Total Money
    "SINEW_041": {"type": "theme", "value": "Retro CRT.json", "name": "Retro CRT"},  # Play for 50 Hours Total
    "SINEW_042": {"type": "theme", "value": "Midnight Terminal.json", "name": "Midnight Terminal"},  # Play for 100 Hours Total
    "SINEW_005": {"type": "theme", "value": "Safari Zone.json", "name": "Safari Zone"},  # Sinew Dex: 150 Pokemon
    
    # Theme-only rewards - SHIFTED +1 (after legendaries section)
    "SINEW_063": {"type": "theme", "value": "Glitchcore.json", "name": "Glitchcore"},  # Dev Mode Discovered! (was 062)
    "SINEW_064": {"type": "theme", "value": "Prototype Debug.json", "name": "Prototype Debug"},  # Debug Tester! (was 063)
    "SINEW_094": {"type": "theme", "value": "Space Station.json", "name": "Space Station"},  # Store 100 Pokemon (was 093)
    "SINEW_100": {"type": "theme", "value": "Gengar.json", "name": "Gengar"},  # Evolve 5 Pokemon (was 099)
}

# Per-game achievement rewards (matched by suffix after game prefix)
# e.g., "RUBY_021", "FR_021", etc. all match "_021"
PERGAME_ACHIEVEMENT_REWARDS = {
    "_021": {"type": "theme", "value": "Brock.json", "name": "Brock"},  # First Badge (any game)
    "_028": {"type": "unlock", "value": "events", "name": "Events Access"},  # Pokemon Champion! - unlocks Events menu
    "_044": {"type": "theme", "value": "Pikachu.json", "name": "Pikachu"},  # First Level 50 (any game)
}

# Game-specific rewards (only for specific games)
GAME_SPECIFIC_REWARDS = {
    "FR_009": {"type": "theme", "value": "Misty.json", "name": "Misty"},  # Kanto Dex Complete (FireRed)
    "LG_009": {"type": "theme", "value": "Misty.json", "name": "Misty"},  # Kanto Dex Complete (LeafGreen)
    "FR_076": {"type": "theme", "value": "Mewtwo.json", "name": "Mewtwo"},  # Caught Mewtwo! (FireRed)
    "LG_076": {"type": "theme", "value": "Mewtwo.json", "name": "Mewtwo"},  # Caught Mewtwo! (LeafGreen)
    # FRLG: Events are unlocked by Sevii Pokemon Ranger (_057), NOT Champion (_028)
    "FR_028": {"type": "none"},  # Override - Champion does NOT unlock events in FRLG
    "LG_028": {"type": "none"},  # Override - Champion does NOT unlock events in FRLG
    "FR_057": {"type": "unlock", "value": "events", "name": "Events Access"},  # Sevii Pokemon Ranger unlocks Events in FireRed
    "LG_057": {"type": "unlock", "value": "events", "name": "Events Access"},  # Sevii Pokemon Ranger unlocks Events in LeafGreen
}

def get_reward_for_achievement(achievement_id: str) -> dict:
    """Get the reward for an achievement, if any.
    Returns None for achievements with no reward or type: 'none'"""
    reward = None
    
    # Check direct mapping first
    if achievement_id in ACHIEVEMENT_REWARDS:
        reward = ACHIEVEMENT_REWARDS[achievement_id]
    
    # Check game-specific rewards (takes precedence over per-game patterns)
    elif achievement_id in GAME_SPECIFIC_REWARDS:
        reward = GAME_SPECIFIC_REWARDS[achievement_id]
    
    # Check per-game pattern rewards (only for actual game prefixes, NOT Sinew)
    # Valid prefixes: RUBY_, SAPP_, EMER_, FR_, LG_
    else:
        game_prefixes = ('RUBY_', 'SAPP_', 'EMER_', 'FR_', 'LG_')
        if achievement_id.startswith(game_prefixes):
            for suffix, r in PERGAME_ACHIEVEMENT_REWARDS.items():
                if achievement_id.endswith(suffix):
                    reward = r
                    break
    
    # Return None for "none" type rewards (they're just overrides to disable a reward)
    if reward and reward.get("type") == "none":
        return None
    
    return reward

def get_theme_unlock_requirements() -> dict:
    """
    Returns a dict mapping theme filenames to achievement requirements.
    Used by themes_screen.py to show locked themes.
    """
    theme_requirements = {}
    
    # From ACHIEVEMENT_REWARDS
    for ach_id, reward in ACHIEVEMENT_REWARDS.items():
        if reward["type"] == "theme":
            theme_requirements[reward["value"]] = ach_id
        elif reward["type"] == "both":
            theme_requirements[reward["theme"]] = ach_id
    
    # From GAME_SPECIFIC_REWARDS
    for ach_id, reward in GAME_SPECIFIC_REWARDS.items():
        if reward["type"] == "theme":
            # For game-specific, use any matching achievement
            if reward["value"] not in theme_requirements:
                theme_requirements[reward["value"]] = ach_id
    
    # From PERGAME_ACHIEVEMENT_REWARDS (use pattern indicator)
    for suffix, reward in PERGAME_ACHIEVEMENT_REWARDS.items():
        if reward["type"] == "theme":
            # Store with a pattern indicator - * means check any game prefix
            theme_requirements[reward["value"]] = f"*{suffix}"
    
    return theme_requirements

def get_achievement_name_by_id(ach_id: str) -> str:
    """Get the achievement name given its ID"""
    # Handle pattern IDs (like *_021)
    if ach_id.startswith("*"):
        suffix = ach_id[1:]  # Remove the *
        for s, reward in PERGAME_ACHIEVEMENT_REWARDS.items():
            if s == suffix:
                # Return a generic description
                if suffix == "_021":
                    return "First Badge (any game)"
                elif suffix == "_044":
                    return "First Level 50 (any game)"
        return f"Achievement {suffix}"
    
    # Check all game achievements
    for game in GAMES + ["Sinew"]:
        try:
            achs = get_achievements_for(game)
            for ach in achs:
                if ach["id"] == ach_id:
                    return ach["name"]
        except:
            pass
    
    return ach_id  # Fallback to ID

def _calculate_points(hint: str, category: str) -> int:
    """Calculate points for an achievement based on difficulty"""
    # Base points by category
    base = {
        "Dex": 10,
        "Gyms/Story": 15,
        "Legendaries": 25,
        "Trainer": 10,
        "Exploration": 10,
        "Items": 10,
        "Stats": 20,
        "Misc": 15,
        "Storage": 15,
    }.get(category, 10)
    
    # Bonus for higher thresholds
    try:
        if ">=" in hint:
            val = int(hint.split(">=")[1].strip().split()[0])
            if val >= 100:
                base += 30
            elif val >= 50:
                base += 15
            elif val >= 20:
                base += 5
    except:
        pass
    
    # Bonus for specific achievements
    if "100" in hint or "champion" in hint.lower():
        base += 25
    if "level" in hint.lower() and "100" in hint:
        base += 20
    if "shiny" in hint.lower():
        base += 30
    
    return base


def _generate_game_achievements(game: str, start_idx: int = 1) -> List[Dict]:
    """
    Generate 100 achievements for a given game.
    Only includes achievements we can actually track from save data:
      - 20 Dex (caught/seen counts)
      - 20 Badges & Money
      - 15 Pokemon Levels
      - 15 Party & PC
      - 15 Playtime & Progress
      - 15 Shinies & Special
    """
    prefix = GAME_PREFIX[game]
    achs = []
    idx = start_idx
    
    # Determine regional dex size based on game
    is_frlg = game in ["FireRed", "LeafGreen"]
    regional_name = "Kanto" if is_frlg else "Hoenn"
    regional_size = 151 if is_frlg else 202

    # ========== 20 Pokedex achievements ==========
    dex_milestones = [
        (5, "First Catches", 10),
        (10, "Pokemon Trainer", 10),
        (25, "Collector", 15),
        (50, "Dedicated Collector", 20),
        (75, "Serious Collector", 25),
        (100, "Century Club", 30),
        (125, "Master Collector", 40),
        (150, "Elite Collector", 50),
    ]
    
    for cap, name, pts in dex_milestones:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": f"Catch {cap} Pokemon in {game}.",
            "category": "Dex", "game": game,
            "hint": f"dex_count >= {cap}",
            "points": pts
        })
        idx += 1
    
    # Regional dex completion
    achs.append({
        "id": f"{prefix}_{idx:03d}", "name": f"{regional_name} Dex Complete",
        "desc": f"Complete the {regional_name} Pokedex ({regional_size} Pokemon)!",
        "category": "Dex", "game": game,
        "hint": f"dex_count >= {regional_size}",
        "points": 150
    })
    idx += 1
    
    # National dex milestones
    national_milestones = [
        (200, "Going National", 60),
        (250, "National Progress", 75),
        (300, "National Expert", 100),
        (350, "Almost There", 150),
    ]
    
    for cap, name, pts in national_milestones:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": f"Catch {cap} Pokemon in {game}.",
            "category": "Dex", "game": game,
            "hint": f"dex_count >= {cap}",
            "points": pts
        })
        idx += 1
    
    # National dex completion
    achs.append({
        "id": f"{prefix}_{idx:03d}", "name": "National Dex Complete!",
        "desc": f"Catch all 386 Pokemon in {game}!",
        "category": "Dex", "game": game,
        "hint": "dex_count >= 386",
        "points": 500
    })
    idx += 1
    
    # Seen milestones
    seen_milestones = [(50, 10), (100, 15), (150, 20), (200, 25), (250, 30), (300, 35)]
    for cap, pts in seen_milestones:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": f"Seen {cap} Pokemon",
            "desc": f"See {cap} Pokemon in {game}'s Pokedex.",
            "category": "Dex", "game": game,
            "hint": f"dex_seen >= {cap}",
            "points": pts
        })
        idx += 1

    # ========== 20 Badges & Money ==========
    badge_achs = [
        (1, "First Badge", 10),
        (2, "Two Badges", 15),
        (3, "Three Badges", 20),
        (4, "Halfway There", 25),
        (5, "Five Badges", 30),
        (6, "Six Badges", 40),
        (7, "Seven Badges", 50),
        (8, "Pokemon Champion!", 100),
    ]
    for badges, name, pts in badge_achs:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": f"Earn {badges} badge{'s' if badges > 1 else ''} in {game}.",
            "category": "Badges", "game": game,
            "hint": f"badges >= {badges}",
            "points": pts
        })
        idx += 1
    
    # Money milestones
    money_achs = [
        (10000, "10K Club", 10),
        (50000, "50K Club", 15),
        (100000, "100K Club", 25),
        (250000, "250K Club", 35),
        (500000, "500K Club", 50),
        (999999, "Max Money!", 100),
    ]
    for amount, name, pts in money_achs:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": f"Have {amount:,} Pokedollars in {game}.",
            "category": "Money", "game": game,
            "hint": f"money >= {amount}",
            "points": pts
        })
        idx += 1
    
    # Playtime in this category too
    playtime_achs = [
        (1, "First Hour", 5),
        (5, "Getting Started", 10),
        (10, "Dedicated", 15),
        (25, "Committed", 25),
        (50, "Veteran", 40),
        (100, "Pokemon Master", 75),
    ]
    for hours, name, pts in playtime_achs:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": f"Play {game} for {hours} hour{'s' if hours > 1 else ''}.",
            "category": "Progress", "game": game,
            "hint": f"playtime_hours >= {hours}",
            "points": pts
        })
        idx += 1

    # ========== 15 Pokemon Levels ==========
    level_achs = [
        ("First Level 10", "any_pokemon_level >= 10", 5, "Raise a Pokemon to level 10."),
        ("First Level 20", "any_pokemon_level >= 20", 10, "Raise a Pokemon to level 20."),
        ("First Level 30", "any_pokemon_level >= 30", 15, "Raise a Pokemon to level 30."),
        ("First Level 50", "any_pokemon_level >= 50", 25, "Raise a Pokemon to level 50."),
        ("First Level 70", "any_pokemon_level >= 70", 35, "Raise a Pokemon to level 70."),
        ("First Level 100!", "any_pokemon_level >= 100", 75, "Raise a Pokemon to level 100!"),
        ("3 Pokemon Lv30+", "pokemon_over_30 >= 3", 20, "Have 3 Pokemon at level 30 or higher."),
        ("6 Pokemon Lv30+", "pokemon_over_30 >= 6", 30, "Have 6 Pokemon at level 30 or higher."),
        ("3 Pokemon Lv50+", "pokemon_over_50 >= 3", 35, "Have 3 Pokemon at level 50 or higher."),
        ("6 Pokemon Lv50+", "pokemon_over_50 >= 6", 50, "Have 6 Pokemon at level 50 or higher."),
        ("3 Pokemon Lv70+", "pokemon_over_70 >= 3", 50, "Have 3 Pokemon at level 70 or higher."),
        ("6 Pokemon Lv70+", "pokemon_over_70 >= 6", 75, "Have 6 Pokemon at level 70 or higher."),
        ("Full Lv100 Team", "pokemon_at_100 >= 6", 150, "Have a full party of level 100 Pokemon!"),
        ("10 Pokemon Lv50+", "pokemon_over_50 >= 10", 60, "Have 10 Pokemon at level 50 or higher."),
        ("20 Pokemon Lv50+", "pokemon_over_50 >= 20", 100, "Have 20 Pokemon at level 50 or higher."),
    ]
    for name, hint, pts, desc in level_achs:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": desc,
            "category": "Pokemon", "game": game,
            "hint": hint,
            "points": pts
        })
        idx += 1

    # ========== 15 Party & PC ==========
    # Note: For FRLG, "Party of 3" is replaced with "Sevii Pokemon Ranger"
    # which requires National Dex + Rainbow Pass (prerequisites for event tickets)
    if is_frlg:
        party_pc_achs = [
            ("First Pokemon", "party_size >= 1", 5, "Have at least 1 Pokemon in your party."),
            ("Sevii Pokemon Ranger", "has_national_dex AND has_rainbow_pass", 100, "Get the National Dex and Rainbow Pass."),
            ("Full Party!", "party_size >= 6", 20, "Fill your party with 6 Pokemon!"),
            ("PC Storage: 10", "pc_pokemon >= 10", 10, "Store 10 Pokemon in your PC."),
            ("PC Storage: 30", "pc_pokemon >= 30", 20, "Store 30 Pokemon in your PC."),
            ("PC Storage: 60", "pc_pokemon >= 60", 30, "Store 60 Pokemon in your PC."),
            ("PC Storage: 100", "pc_pokemon >= 100", 50, "Store 100 Pokemon in your PC."),
            ("PC Storage: 200", "pc_pokemon >= 200", 75, "Store 200 Pokemon in your PC."),
            ("PC Storage: 300", "pc_pokemon >= 300", 100, "Store 300 Pokemon in your PC."),
            ("PC Storage: 400", "pc_pokemon >= 400", 150, "Store 400 Pokemon in your PC!"),
            ("Total Pokemon: 50", "total_pokemon >= 50", 25, "Own 50 total Pokemon (party + PC)."),
            ("Total Pokemon: 100", "total_pokemon >= 100", 40, "Own 100 total Pokemon (party + PC)."),
            ("Total Pokemon: 200", "total_pokemon >= 200", 75, "Own 200 total Pokemon (party + PC)."),
            ("Total Pokemon: 300", "total_pokemon >= 300", 100, "Own 300 total Pokemon (party + PC)."),
            ("Total Pokemon: 400", "total_pokemon >= 400", 150, "Own 400 total Pokemon (party + PC)!"),
        ]
    else:
        party_pc_achs = [
            ("First Pokemon", "party_size >= 1", 5, "Have at least 1 Pokemon in your party."),
            ("Party of 3", "party_size >= 3", 10, "Have 3 Pokemon in your party."),
            ("Full Party!", "party_size >= 6", 20, "Fill your party with 6 Pokemon!"),
            ("PC Storage: 10", "pc_pokemon >= 10", 10, "Store 10 Pokemon in your PC."),
            ("PC Storage: 30", "pc_pokemon >= 30", 20, "Store 30 Pokemon in your PC."),
            ("PC Storage: 60", "pc_pokemon >= 60", 30, "Store 60 Pokemon in your PC."),
            ("PC Storage: 100", "pc_pokemon >= 100", 50, "Store 100 Pokemon in your PC."),
            ("PC Storage: 200", "pc_pokemon >= 200", 75, "Store 200 Pokemon in your PC."),
            ("PC Storage: 300", "pc_pokemon >= 300", 100, "Store 300 Pokemon in your PC."),
            ("PC Storage: 400", "pc_pokemon >= 400", 150, "Store 400 Pokemon in your PC!"),
            ("Total Pokemon: 50", "total_pokemon >= 50", 25, "Own 50 total Pokemon (party + PC)."),
            ("Total Pokemon: 100", "total_pokemon >= 100", 40, "Own 100 total Pokemon (party + PC)."),
            ("Total Pokemon: 200", "total_pokemon >= 200", 75, "Own 200 total Pokemon (party + PC)."),
            ("Total Pokemon: 300", "total_pokemon >= 300", 100, "Own 300 total Pokemon (party + PC)."),
            ("Total Pokemon: 400", "total_pokemon >= 400", 150, "Own 400 total Pokemon (party + PC)!"),
        ]
    for name, hint, pts, desc in party_pc_achs:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": desc,
            "category": "Collection", "game": game,
            "hint": hint,
            "points": pts
        })
        idx += 1

    # ========== 15 Shinies & Special ==========
    special_achs = [
        ("First Shiny!", "shiny_count >= 1", 100),
        ("Shiny Collector: 2", "shiny_count >= 2", 150),
        ("Shiny Collector: 3", "shiny_count >= 3", 200),
        ("Shiny Collector: 5", "shiny_count >= 5", 300),
        ("Shiny Hunter", "shiny_count >= 10", 500),
    ]
    for name, hint, pts in special_achs:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": f"{name} in {game}.",
            "category": "Shiny", "game": game,
            "hint": hint,
            "points": pts
        })
        idx += 1
    
    # Legendary ownership (check if in pokedex)
    if is_frlg:
        legendaries = [
            (150, "Mewtwo", 100),
            (144, "Articuno", 50),
            (145, "Zapdos", 50),
            (146, "Moltres", 50),
            (151, "Mew", 200),
        ]
    else:
        legendaries = [
            (382, "Kyogre", 75),
            (383, "Groudon", 75),
            (384, "Rayquaza", 100),
            (380, "Latias", 50),
            (381, "Latios", 50),
        ]
    
    for species_id, name, pts in legendaries:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": f"Caught {name}!",
            "desc": f"Own {name} in {game}.",
            "category": "Legendary", "game": game,
            "hint": f"owns_species_{species_id}",
            "points": pts
        })
        idx += 1
    
    # Fill remaining with additional milestones (need 15 more)
    remaining_achs = [
        ("Pokemon Scholar", "dex_seen >= 350", 50, "See 350 different Pokemon species."),
        ("See Them All!", "dex_seen >= 386", 100, "See all 386 Pokemon in the National Dex!"),
        ("Box Filler", "pc_pokemon >= 150", 40, "Store 150 Pokemon in your PC boxes."),
        ("Dedicated Player", "playtime_hours >= 75", 50, "Play for 75 hours."),
        ("True Dedication", "playtime_hours >= 150", 100, "Play for 150 hours. A true trainer!"),
        ("Long Journey", "playtime_hours >= 200", 125, "Play for 200 hours."),
        ("Pokemon Legend", "playtime_hours >= 300", 200, "Play for 300 hours. Legendary dedication!"),
        ("Rich Trainer", "money >= 750000", 75, "Have 750,000 Pokedollars."),
        ("30 Pokemon Lv50+", "pokemon_over_50 >= 30", 125, "Have 30 Pokemon at level 50 or higher."),
        ("Massive Collection", "total_pokemon >= 350", 175, "Own 350 total Pokemon (party + PC)."),
        ("PC Master", "pc_pokemon >= 350", 125, "Store 350 Pokemon in your PC boxes."),
        ("Almost Full PC", "pc_pokemon >= 420", 200, "Store 420 Pokemon - almost full PC!"),
        ("3 Pokemon Lv100", "pokemon_at_100 >= 3", 100, "Have 3 Pokemon at level 100."),
        ("10 Pokemon Lv100", "pokemon_at_100 >= 10", 175, "Have 10 Pokemon at level 100!"),
        ("Shiny Luck", "shiny_count >= 7", 400, "Find 7 shiny Pokemon. Lucky!"),
        # 5 more to reach 100
        ("40 Pokemon Lv50+", "pokemon_over_50 >= 40", 150, "Have 40 Pokemon at level 50 or higher."),
        ("50 Pokemon Lv50+", "pokemon_over_50 >= 50", 200, "Have 50 Pokemon at level 50 or higher!"),
        ("First Level 40", "any_pokemon_level >= 40", 20, "Raise a Pokemon to level 40."),
        ("First Level 60", "any_pokemon_level >= 60", 30, "Raise a Pokemon to level 60."),
        ("First Level 80", "any_pokemon_level >= 80", 45, "Raise a Pokemon to level 80."),
    ]
    for name, hint, pts, desc in remaining_achs:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": f"{desc}",
            "category": "Progress", "game": game,
            "hint": hint,
            "points": pts
        })
        idx += 1

    assert len(achs) == 100, f"{game} generated {len(achs)} achievements (expected 100)."
    return achs

def _generate_sinew_achievements(start_idx: int = 1) -> List[Dict]:
    """
    Generate 100 cross-save (Sinew) achievements.
    Categories similar but global across all saves.
    """
    prefix = GAME_PREFIX["Sinew"]
    achs = []
    idx = start_idx

    # 20 Global Dex milestones across saves (sum of caught across all saves)
    # These track total Pokemon caught summed across all games
    dex_milestones = [
        (10, "Getting Started", 10),
        (25, "Cross-Game Collector", 15),
        (50, "Multi-Game Hunter", 20),
        (100, "Dedicated Trainer", 30),
        (150, "Serious Collector", 40),
        (200, "Pokemon Expert", 50),
        (250, "Master Collector", 60),
        (300, "Elite Trainer", 75),
        (400, "Pokemon Professor", 100),
        (500, "Living Legend", 125),
        # Per-save completions (if you complete dex in multiple games)
        (151, "Kanto Master", 75),  # At least one FRLG complete
        (202, "Hoenn Master", 75),  # At least one RSE complete
        (386, "National Hero", 150),  # At least one national dex complete
        (537, "Double National", 200),  # 386 + 151
        (588, "Triple Regional", 250),  # 386 + 202 (or combos)
        # High totals for multiple playthroughs
        (700, "Pokemon Veteran", 150),
        (900, "Pokemon Legend", 200),
        (1000, "Pokemon Deity", 250),
        (1200, "Absolute Master", 300),
        (1500, "Beyond Mortal", 400),
    ]
    
    for cap, name, pts in dex_milestones:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": f"Sinew Dex: {name}",
            "desc": f"Catch {cap} total Pokemon across all saves (sum of all games).",
            "category": "Dex", "game": "Sinew",
            "hint": f"global_dex_count >= {cap}",
            "points": pts
        })
        idx += 1

    # 20 Global progression achievements (realistic goals)
    progression = [
        # Badge milestones (max 40 across 5 games)
        ("Collect 1 Badge", "global_badges >= 1", 10),
        ("Collect 8 Badges", "global_badges >= 8", 15),
        ("Collect 16 Badges", "global_badges >= 16", 25),
        ("Collect 24 Badges", "global_badges >= 24", 35),
        ("Collect 32 Badges", "global_badges >= 32", 50),
        ("Collect All 40 Badges", "global_badges >= 40", 100),
        # Champion milestones
        ("Become Champion Once", "global_champions >= 1", 25),
        ("Become Champion in 2 Games", "global_champions >= 2", 40),
        ("Become Champion in 3 Games", "global_champions >= 3", 60),
        ("Become Champion in All 5 Games", "global_champions >= 5", 150),
        # Multi-game progression
        ("Start All 5 Games", "games_with_badges >= 5", 20),
        ("Halfway in 3 Games", "games_with_4plus_badges >= 3", 40),
        ("Complete 1 Regional Dex", "games_with_full_dex >= 1", 50),
        ("Complete 2 Regional Dexes", "games_with_full_dex >= 2", 100),
        ("Complete All 5 Regional Dexes", "games_with_full_dex >= 5", 250),
        # Money milestones
        ("Earn 100,000 Total Money", "global_money >= 100000", 15),
        ("Earn 500,000 Total Money", "global_money >= 500000", 30),
        ("Earn 1,000,000 Total Money", "global_money >= 1000000", 50),
        ("Max Money in Any Game", "any_game_max_money == True", 40),
        # Playtime
        ("Play for 10 Hours Total", "global_playtime >= 10", 15),
        ("Play for 50 Hours Total", "global_playtime >= 50", 30),
        ("Play for 100 Hours Total", "global_playtime >= 100", 50),
    ]
    for name, hint, pts in progression:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": f"{name} across all saved games.",
            "category": "Gyms/Story", "game": "Sinew",
            "hint": hint,
            "points": pts
        })
        idx += 1

    # 11 cross-game Legendary milestones (using species IDs for checking)
    # Gen 3 Legendary IDs: Groudon=383, Kyogre=382, Rayquaza=384, Mewtwo=150, Mew=151
    # Latios=381, Latias=380, Regirock=377, Regice=378, Registeel=379
    # Jirachi=385, Deoxys=386, Birds=144,145,146, Ho-Oh=250, Lugia=249
    legendaries = [
        ("Own Groudon", "owns_species_383", 50, "Catch or obtain Groudon across any save."),
        ("Own Kyogre", "owns_species_382", 50, "Catch or obtain Kyogre across any save."),
        ("Own Rayquaza", "owns_species_384", 75, "Catch or obtain Rayquaza across any save."),
        ("Own Mewtwo", "owns_species_150", 75, "Catch or obtain Mewtwo across any save."),
        ("Own Mew", "owns_species_151", 100, "Obtain the mythical Mew!"),
        ("Own Latios or Latias", "owns_species_380_or_381", 40, "Catch a Lati@s across any save."),
        ("Own Legendary Birds", "owns_legendary_birds", 125, "Own Articuno, Zapdos, and Moltres!"),
        ("Own the Regi Trio", "owns_regi_trio", 100, "Own Regirock, Regice, and Registeel."),
        ("Own Weather Trio", "owns_weather_trio", 150, "Own Groudon, Kyogre, and Rayquaza."),
        ("Own Jirachi", "owns_species_385", 100, "Obtain the mythical Jirachi!"),
        ("Own Deoxys", "owns_species_386", 100, "Obtain the mythical Deoxys!"),
    ]
    for name, hint, pts, desc in legendaries:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": f"Legendary: {name}",
            "desc": desc,
            "category": "Legendaries", "game": "Sinew",
            "hint": hint,
            "points": pts
        })
        idx += 1

    # 10 Global Trainer / Progress milestones (using trackable data, avoiding duplicates with Gyms/Story)
    trainers = [
        ("Quad Champion", "global_champions >= 4", 100, "Become Champion in 4 different games."),
        ("Badge Collector: 10", "global_badges >= 10", 20, "Collect 10 badges across all saves."),
        ("Badge Collector: 20", "global_badges >= 20", 30, "Collect 20 badges across all saves."),
        ("Badge Collector: 28", "global_badges >= 28", 40, "Collect 28 badges across all saves."),
        ("Badge Collector: 36", "global_badges >= 36", 75, "Collect 36 badges across all saves."),
        ("Halfway Hero x2", "games_with_4plus_badges >= 2", 25, "Have 4+ badges in 2 different games."),
        ("Halfway Hero x4", "games_with_4plus_badges >= 4", 50, "Have 4+ badges in 4 different games."),
        ("Halfway Hero x5", "games_with_4plus_badges >= 5", 75, "Have 4+ badges in ALL 5 games."),
        ("Pokemon Millionaire", "global_money >= 5000000", 100, "Accumulate 5 million total money."),
        ("Dev Mode Discovered!", "dev_mode_activated == True", 50, "Find the secret Dev Mode!"),
        ("Debug Tester!", "debug_test_activated == True", 25, "Trigger the debug test in Dev Mode!"),
    ]
    for name, hint, pts, desc in trainers:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": desc,
            "category": "Trainer", "game": "Sinew",
            "hint": hint,
            "points": pts
        })
        idx += 1

    # 10 Global Time & Progress milestones
    explorations = [
        ("Dedicated Trainer: 25h", "global_playtime >= 25", 20, "Play for 25 hours total across all saves."),
        ("Veteran Trainer: 75h", "global_playtime >= 75", 40, "Play for 75 hours total across all saves."),
        ("Pokemon Master: 150h", "global_playtime >= 150", 75, "Play for 150 hours total. True dedication!"),
        ("Pokemon Legend: 250h", "global_playtime >= 250", 100, "Play for 250 hours total!"),
        ("PC Hoarder: 50", "global_pc_pokemon >= 50", 20, "Store 50 Pokemon in PC boxes across saves."),
        ("PC Hoarder: 150", "global_pc_pokemon >= 150", 40, "Store 150 Pokemon in PC boxes across saves."),
        ("PC Hoarder: 300", "global_pc_pokemon >= 300", 60, "Store 300 Pokemon in PC boxes across saves."),
        ("Shiny Hunter: 3", "global_shiny_pokemon >= 3", 50, "Own 3 shiny Pokemon across all saves."),
        ("Shiny Hunter: 10", "global_shiny_pokemon >= 10", 100, "Own 10 shiny Pokemon across all saves."),
        ("Shiny Hunter: 25", "global_shiny_pokemon >= 25", 200, "Own 25 shiny Pokemon. Incredible luck!"),
    ]
    for name, hint, pts, desc in explorations:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": desc,
            "category": "Progress", "game": "Sinew",
            "hint": hint,
            "points": pts
        })
        idx += 1

    # 10 Pokemon Level & Stats global (avoiding money duplicates)
    items = [
        ("Level 100 Club", "global_level100_pokemon >= 1", 25, "Raise a Pokemon to level 100."),
        ("Level 100 Team", "global_level100_pokemon >= 6", 50, "Have 6 Pokemon at level 100."),
        ("Level 100 Squad", "global_level100_pokemon >= 12", 75, "Have 12 Pokemon at level 100!"),
        ("Level 100 Army", "global_level100_pokemon >= 20", 100, "Have 20 Pokemon at level 100!"),
        ("Level 100 Legion", "global_level100_pokemon >= 50", 200, "Have 50 Pokemon at level 100!!"),
        ("Strong Team: 10", "global_level50plus_pokemon >= 10", 15, "Have 10 Pokemon at level 50+."),
        ("Strong Team: 30", "global_level50plus_pokemon >= 30", 30, "Have 30 Pokemon at level 50+."),
        ("Strong Team: 50", "global_level50plus_pokemon >= 50", 50, "Have 50 Pokemon at level 50+."),
        ("Strong Team: 100", "global_level50plus_pokemon >= 100", 75, "Have 100 Pokemon at level 50+!"),
        ("Full Party x5", "global_full_parties >= 5", 40, "Have a full party of 6 in all 5 games."),
    ]
    for name, hint, pts, desc in items:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": desc,
            "category": "Pokemon", "game": "Sinew",
            "hint": hint,
            "points": pts
        })
        idx += 1

    # 7 Party & Team composition achievements
    stats = [
        ("Full Party x1", "global_full_parties >= 1", 10, "Have 6 Pokemon in any save's party."),
        ("Full Party x3", "global_full_parties >= 3", 25, "Have full parties in 3 different games."),
        ("Starter Squad", "global_starters >= 2", 20, "Own Pokemon from 2 different starter lines."),
        ("Starter Collector", "global_starters >= 4", 40, "Own Pokemon from 4 different starter lines."),
        ("All Starters", "global_starters >= 6", 100, "Own Pokemon from all 6 starter lines!"),
        ("Eeveelution Fan", "global_eeveelutions >= 3", 40, "Own 3 different Eeveelutions."),
        ("Eeveelution Master", "global_eeveelutions >= 5", 75, "Own all 5 Gen 1-3 Eeveelutions!"),
    ]
    for name, hint, pts, desc in stats:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": desc,
            "category": "Team", "game": "Sinew",
            "hint": hint,
            "points": pts
        })
        idx += 1

    # 13 Sinew Storage milestones (actual storage system achievements)
    storage = [
        ("Store your first Pokemon in Sinew", "sinew_pokemon >= 1", 15),
        ("Store 50 Pokemon in Sinew Storage", "sinew_pokemon >= 50", 30),
        ("Store 100 Pokemon in Sinew Storage", "sinew_pokemon >= 100", 50),
        ("Store 250 Pokemon in Sinew Storage", "sinew_pokemon >= 250", 75),
        ("Transfer 10 Pokemon between games", "sinew_transfers >= 10", 20),
        ("Transfer 50 Pokemon between games", "sinew_transfers >= 50", 40),
        ("Store 5 shiny Pokemon in Sinew", "shiny_count >= 5", 50),
        # Evolution achievements
        ("First Sinew Evolution!", "sinew_evolutions >= 1", 25),
        ("Evolve 5 Pokemon via Sinew", "sinew_evolutions >= 5", 40),
        ("Evolve 10 Pokemon via Sinew", "sinew_evolutions >= 10", 60),
    ]
    for name, hint, pts in storage:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": name,
            "category": "Storage", "game": "Sinew",
            "hint": hint,
            "points": pts
        })
        idx += 1
    
    # 3 Dirty Dex achievements (combined Pokedex across ALL saves)
    dirty_dex = [
        ("Dirty Dex: 100 Species", "combined_pokedex >= 100", 50, "Own 100 unique species across all your save files."),
        ("Dirty Dex: 250 Species", "combined_pokedex >= 250", 75, "Own 250 unique species across all your save files."),
        ("Dirty Dex: Catch 'Em All!", "combined_pokedex >= 386", 500, "Own all 386 Pokemon across your combined saves! True Pokemon Master!"),
    ]
    for name, hint, pts, desc in dirty_dex:
        achs.append({
            "id": f"{prefix}_{idx:03d}", "name": name,
            "desc": desc,
            "category": "Storage", "game": "Sinew",
            "hint": hint,
            "points": pts
        })
        idx += 1
    
    # Special Altering Cave achievement (mystery Pokemon that were never distributed)
    # Progress is tracked manually when player uses the slot machine feature
    achs.append({
        "id": f"{prefix}_{idx:03d}",  # SINEW_105
        "name": "Echoes of What Never Was",
        "desc": "Discover all 7 Pokemon that were meant for Altering Cave but never released.",
        "category": "Storage",
        "game": "Sinew",
        "hint": "altering_cave_echoes >= 7",
        "points": 150
    })
    idx += 1

    # =============================================================================
    # EVENT ACHIEVEMENTS - Mystery Event Items System
    # Unlocked by claiming event tickets from the Events menu (requires Champion status
    # and claiming the "Become Champion Once" achievement reward first)
    # =============================================================================
    
    # Per-event item achievements
    event_items = [
        ("Southern Island Pass", "event_eon_ticket_claimed", "Obtain the Eon Ticket to visit Southern Island.", 25),
        ("Birth Island Pass", "event_aurora_ticket_claimed", "Obtain the Aurora Ticket to visit Birth Island.", 25),
        ("Navel Rock Pass", "event_mystic_ticket_claimed", "Obtain the Mystic Ticket to visit Navel Rock.", 25),
        ("Faraway Island Pass", "event_old_sea_map_claimed", "Obtain the Old Sea Map to visit Faraway Island.", 25),
    ]
    for name, hint, desc, pts in event_items:
        achs.append({
            "id": f"{prefix}_{idx:03d}",
            "name": name,
            "desc": desc,
            "category": "Events",
            "game": "Sinew",
            "hint": hint,
            "points": pts
        })
        idx += 1
    
    # All events collector achievement
    achs.append({
        "id": f"{prefix}_{idx:03d}",
        "name": "Event Collector",
        "desc": "Obtain all 4 mystery event items across your saves.",
        "category": "Events",
        "game": "Sinew",
        "hint": "all_events_claimed",
        "points": 100
    })
    idx += 1

    assert len(achs) >= 100, f"Sinew generated {len(achs)} achievements (expected at least 100)."
    return achs

# Build the full dict
GAME_ACHIEVEMENTS: Dict[str, List[Dict]] = {}
for g in GAMES:
    GAME_ACHIEVEMENTS[g] = _generate_game_achievements(g)
GAME_ACHIEVEMENTS["Sinew"] = _generate_sinew_achievements()

def get_achievements_for(game_name: str) -> List[Dict]:
    """Return a copy of the achievements list for the given game_name."""
    return GAME_ACHIEVEMENTS.get(game_name, []).copy()

# --- Check if achievement is unlocked based on save data ---
def check_achievement_unlocked(ach: Dict, save_data: Dict, all_saves: List[Dict] = None) -> bool:
    """
    Determine whether an achievement `ach` is unlocked given a parsed save_data dict.
    
    Args:
        ach: an achievement dict from the lists above
        save_data: parsed save structure containing:
            - dex_caught: int (number of Pokemon caught)
            - dex_seen: int (number of Pokemon seen)  
            - badges: int (number of badges, 0-8)
            - money: int
            - party: list of Pokemon dicts
            - pc_pokemon: list of PC Pokemon
            - playtime_hours: float
            - shiny_count: int
            - owned_list: list of species IDs owned
        all_saves: optional list of parsed save dicts across saves (for Sinew global checks)

    Returns:
        bool: True if achievement condition is met
    """
    hint = ach.get("hint", "")
    ach_id = ach.get("id", "unknown")
    
    # Helper to parse "field >= N" style hints
    def parse_threshold(hint_str):
        """Extract field name and required value from 'field >= N' hint"""
        if ">=" in hint_str:
            parts = hint_str.split(">=")
            field = parts[0].strip()
            try:
                required = int(parts[1].strip().split()[0])
                return field, required
            except:
                pass
        return None, None
    
    # Get common data
    dex_caught = save_data.get('dex_caught', 0)
    dex_seen = save_data.get('dex_seen', 0)
    badges = save_data.get('badges', 0)
    money = save_data.get('money', 0)
    party = save_data.get('party', [])
    pc_pokemon = save_data.get('pc_pokemon', [])
    playtime_hours = save_data.get('playtime_hours', 0)
    owned_list = save_data.get('owned_list', [])
    
    # Combine party and PC for total Pokemon
    all_pokemon = []
    for p in party:
        if p and not p.get('empty'):
            all_pokemon.append(p)
    for p in pc_pokemon:
        if p and not p.get('empty'):
            all_pokemon.append(p)
    
    # Count various stats
    party_size = len([p for p in party if p and not p.get('empty')])
    pc_count = len([p for p in pc_pokemon if p and not p.get('empty')])
    total_pokemon_count = len(all_pokemon)
    
    # Level stats
    max_level = 0
    pokemon_over_30 = 0
    pokemon_over_50 = 0
    pokemon_over_70 = 0
    pokemon_at_100 = 0
    shiny_count = 0
    
    for p in all_pokemon:
        level = p.get('level', 0)
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
        # Check for shiny - try both keys
        if p.get('is_shiny') or p.get('shiny', False):
            shiny_count += 1
    
    # =========================================================================
    # THRESHOLD-BASED CHECKS (handle most common patterns)
    # =========================================================================
    
    # Dex counts
    if "dex_count >=" in hint:
        _, required = parse_threshold(hint)
        return dex_caught >= required if required else False
    
    if "dex_seen >=" in hint:
        _, required = parse_threshold(hint)
        return dex_seen >= required if required else False
    
    # Badge counts
    if "badges >=" in hint:
        _, required = parse_threshold(hint)
        return badges >= required if required else False
    
    # Money counts
    if "money >=" in hint:
        _, required = parse_threshold(hint)
        return money >= required if required else False
    
    # Playtime
    if "playtime_hours >=" in hint:
        _, required = parse_threshold(hint)
        return playtime_hours >= required if required else False
    
    # Party size
    if "party_size >=" in hint:
        _, required = parse_threshold(hint)
        return party_size >= required if required else False
    
    # PC Pokemon count
    if "pc_pokemon >=" in hint:
        _, required = parse_threshold(hint)
        return pc_count >= required if required else False
    
    # Total Pokemon count
    if "total_pokemon >=" in hint:
        _, required = parse_threshold(hint)
        return total_pokemon_count >= required if required else False
    
    # Level thresholds for any Pokemon
    if "any_pokemon_level >=" in hint:
        _, required = parse_threshold(hint)
        return max_level >= required if required else False
    
    # Pokemon over level thresholds
    if "pokemon_over_30 >=" in hint:
        _, required = parse_threshold(hint)
        return pokemon_over_30 >= required if required else False
    
    if "pokemon_over_50 >=" in hint:
        _, required = parse_threshold(hint)
        return pokemon_over_50 >= required if required else False
    
    if "pokemon_over_70 >=" in hint:
        _, required = parse_threshold(hint)
        return pokemon_over_70 >= required if required else False
    
    if "pokemon_at_100 >=" in hint:
        _, required = parse_threshold(hint)
        return pokemon_at_100 >= required if required else False
    
    # Shiny count
    if "shiny_count >=" in hint:
        _, required = parse_threshold(hint)
        return shiny_count >= required if required else False
    
    # =========================================================================
    # LEGENDARY OWNERSHIP (check if species ID in owned_list)
    # =========================================================================
    if "owns_species_" in hint:
        try:
            # Extract species ID from hint like "owns_species_383"
            species_id = int(hint.split("owns_species_")[1].split()[0])
            result = species_id in owned_list
            # Debug output for legendary checks
            if len(owned_list) > 0:
                # Show whether found or not
                print(f"[Achievements] Legendary check: species {species_id} in owned_list ({len(owned_list)} species)? {result}")
                if not result and species_id in [150, 151, 380, 381, 382, 383, 384]:
                    # Show what type owned_list contains
                    sample = owned_list[:5] if len(owned_list) >= 5 else owned_list
                    print(f"[Achievements]   owned_list sample: {sample} (types: {[type(x).__name__ for x in sample]})")
            return result
        except Exception as e:
            print(f"[Achievements] Error checking legendary: {e}")
            import traceback
            traceback.print_exc()
    
    # =========================================================================
    # FRLG SEVII POKEMON RANGER ACHIEVEMENT
    # =========================================================================
    # Requires National Dex unlocked AND Rainbow Pass obtained
    if hint == "has_national_dex AND has_rainbow_pass":
        # First check if already parsed in save_data
        has_national_dex = save_data.get('has_national_dex', None)
        has_rainbow_pass = save_data.get('has_rainbow_pass', None)
        
        # If not pre-parsed, try to check using save_writer functions
        if has_national_dex is None or has_rainbow_pass is None:
            try:
                from save_writer import has_national_dex as check_nat_dex, has_rainbow_pass as check_rainbow
                raw_data = save_data.get('raw_data')
                if raw_data:
                    has_national_dex = check_nat_dex(raw_data, 'FRLG')
                    has_rainbow_pass = check_rainbow(raw_data, 'FRLG')
                else:
                    # Can't check without raw data
                    has_national_dex = False
                    has_rainbow_pass = False
            except Exception as e:
                print(f"[Achievements] Error checking Sevii prereqs: {e}")
                has_national_dex = save_data.get('has_national_dex', False)
                has_rainbow_pass = save_data.get('has_rainbow_pass', False)
        
        # Debug output
        print(f"[Achievements] Sevii check: national_dex={has_national_dex}, rainbow_pass={has_rainbow_pass}")
        
        return has_national_dex and has_rainbow_pass
    
    # =========================================================================
    # EVENT ACHIEVEMENTS (Mystery Event Items System)
    # =========================================================================
    
    # Endgame Access - any game with 8 badges (Champion status)
    if hint == "any_game_champion":
        # Check current save
        if badges >= 8:
            return True
        # Check all saves if provided
        if all_saves:
            for save in all_saves:
                if save.get('badges', 0) >= 8:
                    return True
        return False
    
    # Event item achievements - check events_tracker in save_data
    events_tracker = save_data.get('events_tracker', {})
    
    if hint == "event_eon_ticket_claimed":
        return events_tracker.get('eon_ticket', False)
    
    if hint == "event_aurora_ticket_claimed":
        return events_tracker.get('aurora_ticket', False)
    
    if hint == "event_mystic_ticket_claimed":
        return events_tracker.get('mystic_ticket', False)
    
    if hint == "event_old_sea_map_claimed":
        return events_tracker.get('old_sea_map', False)
    
    # All events collector
    if hint == "all_events_claimed":
        return all([
            events_tracker.get('eon_ticket', False),
            events_tracker.get('aurora_ticket', False),
            events_tracker.get('mystic_ticket', False),
            events_tracker.get('old_sea_map', False),
        ])
    
    # Default - not unlocked
    return False


# Example quick test (you can remove or adapt)
if __name__ == "__main__":
    # Show counts
    total = sum(len(v) for v in GAME_ACHIEVEMENTS.values())
    print(f"Generated achievements: {total}")
    for k in GAME_ACHIEVEMENTS:
        print(k, len(GAME_ACHIEVEMENTS[k]))