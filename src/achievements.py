"""
Achievements System for Sinew
Manages achievement tracking, unlocking, rewards, and display.
"""

import pygame
import json
import os
import time
import math
from ui_components import Button
import ui_colors
from controller import get_controller, NavigableList
from config import EXT_DIR, FONT_PATH, ACH_SAVE_PATH, ACH_REWARDS_PATH

# Lazy imports to avoid circular import issues
# from achievements_data import get_achievements_for, check_achievement_unlocked, GAME_ACHIEVEMENTS, GAMES
# These are imported inside functions that need them


# =============================================================================
# ACHIEVEMENT NOTIFICATION SYSTEM
# =============================================================================

class AchievementNotification:
    """
    Handles slide-down achievement unlock notifications.
    Queues multiple achievements and displays them one at a time.
    """
    
    SLIDE_DURATION = 0.3      # Seconds to slide in/out
    DISPLAY_DURATION = 3.0    # Seconds to stay visible
    NOTIFICATION_HEIGHT = 60
    
    STATE_HIDDEN = 0
    STATE_SLIDING_IN = 1
    STATE_VISIBLE = 2
    STATE_SLIDING_OUT = 3
    
    # Game icon filenames
    GAME_ICON_FILES = {
        "Ruby": "ruby.png",
        "Sapphire": "sapphire.png",
        "Emerald": "emerald.png",
        "FireRed": "firered.png",
        "LeafGreen": "leafgreen.png",
        "Sinew": "trophy.png",
    }
    
    def __init__(self, screen_width):
        self.screen_width = screen_width
        self.queue = []  # Queue of achievement dicts to display
        self.current = None  # Currently displaying achievement
        self.state = self.STATE_HIDDEN
        self.state_start_time = 0
        self.y_offset = -self.NOTIFICATION_HEIGHT  # Start off-screen
        
        # Fonts
        try:
            self.font_title = pygame.font.Font(FONT_PATH, 12)
            self.font_text = pygame.font.Font(FONT_PATH, 9)
            self.font_sinew = pygame.font.Font(FONT_PATH, 24)
        except:
            self.font_title = pygame.font.SysFont(None, 18)
            self.font_text = pygame.font.SysFont(None, 14)
            self.font_sinew = pygame.font.SysFont(None, 32)
        
        # Load game icons
        self.game_icons = {}
        self._load_game_icons()
    
    def _load_game_icons(self):
        """Load game icons for achievement display"""
        icon_size = 36  # Size for the notification icon
        
        for game_name, filename in self.GAME_ICON_FILES.items():
            icon_path = os.path.join("data", "sprites", "icons", filename)
            try:
                if os.path.exists(icon_path):
                    icon = pygame.image.load(icon_path).convert_alpha()
                    icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
                    self.game_icons[game_name] = icon
                    print(f"[AchNotify] Loaded icon: {game_name}")
            except Exception as e:
                print(f"[AchNotify] Could not load icon for {game_name}: {e}")
    
    def queue_achievement(self, achievement):
        """Add an achievement to the notification queue"""
        self.queue.append(achievement)
        print(f"[AchNotify] Queued: {achievement.get('name', 'Unknown')}")
        
        # Start showing if not already showing something
        if self.state == self.STATE_HIDDEN and self.current is None:
            self._show_next()
    
    def _show_next(self):
        """Show the next achievement in queue"""
        if not self.queue:
            self.current = None
            self.state = self.STATE_HIDDEN
            return
        
        self.current = self.queue.pop(0)
        self.state = self.STATE_SLIDING_IN
        self.state_start_time = time.time()
        self.y_offset = -self.NOTIFICATION_HEIGHT
        print(f"[AchNotify] Showing: {self.current.get('name', 'Unknown')}")
    
    def update(self):
        """Update notification animation state"""
        if self.state == self.STATE_HIDDEN:
            if self.queue and self.current is None:
                self._show_next()
            return
        
        elapsed = time.time() - self.state_start_time
        
        if self.state == self.STATE_SLIDING_IN:
            # Animate sliding down
            progress = min(1.0, elapsed / self.SLIDE_DURATION)
            # Ease out cubic
            progress = 1 - (1 - progress) ** 3
            self.y_offset = -self.NOTIFICATION_HEIGHT + (self.NOTIFICATION_HEIGHT * progress)
            
            if elapsed >= self.SLIDE_DURATION:
                self.state = self.STATE_VISIBLE
                self.state_start_time = time.time()
                self.y_offset = 0
        
        elif self.state == self.STATE_VISIBLE:
            if elapsed >= self.DISPLAY_DURATION:
                self.state = self.STATE_SLIDING_OUT
                self.state_start_time = time.time()
        
        elif self.state == self.STATE_SLIDING_OUT:
            # Animate sliding up
            progress = min(1.0, elapsed / self.SLIDE_DURATION)
            # Ease in cubic
            progress = progress ** 3
            self.y_offset = -(self.NOTIFICATION_HEIGHT * progress)
            
            if elapsed >= self.SLIDE_DURATION:
                self.state = self.STATE_HIDDEN
                self.current = None
                # Check for more in queue
                if self.queue:
                    self._show_next()
    
    def draw(self, surf):
        """Draw the notification if visible"""
        if self.state == self.STATE_HIDDEN or self.current is None:
            return
        
        # Gap from top of screen
        top_gap = 10
        
        # Background banner
        banner_width = min(350, self.screen_width - 40)
        banner_x = (self.screen_width - banner_width) // 2
        banner_rect = pygame.Rect(banner_x, int(self.y_offset) + top_gap, banner_width, self.NOTIFICATION_HEIGHT)
        
        # Draw shadow
        shadow_rect = banner_rect.copy()
        shadow_rect.y += 3
        shadow_rect.x += 3
        pygame.draw.rect(surf, (0, 0, 0, 100), shadow_rect, border_radius=8)
        
        # Draw banner background with gradient feel
        pygame.draw.rect(surf, (40, 50, 70), banner_rect, border_radius=8)
        pygame.draw.rect(surf, (255, 215, 0), banner_rect, 3, border_radius=8)  # Gold border
        
        # Game icon area
        icon_rect = pygame.Rect(banner_rect.x + 8, banner_rect.y + 10, 40, 40)
        pygame.draw.rect(surf, (255, 215, 0), icon_rect, border_radius=5)
        
        # Draw game icon or Sinew "S"
        game = self.current.get('game', 'Sinew')
        if game in self.game_icons:
            # Use game icon
            icon = self.game_icons[game]
            icon_pos = (icon_rect.x + (icon_rect.width - icon.get_width()) // 2,
                       icon_rect.y + (icon_rect.height - icon.get_height()) // 2)
            surf.blit(icon, icon_pos)
        else:
            # Sinew or unknown - draw "S"
            s_text = self.font_sinew.render("S", True, (50, 40, 0))
            s_rect = s_text.get_rect(center=icon_rect.center)
            surf.blit(s_text, s_rect)
        
        # "Achievement Unlocked!" header
        header = self.font_text.render("Achievement Unlocked!", True, (255, 215, 0))
        surf.blit(header, (banner_rect.x + 55, banner_rect.y + 8))
        
        # Achievement name
        name = self.current.get('name', 'Unknown Achievement')
        if len(name) > 28:
            name = name[:25] + "..."
        name_surf = self.font_title.render(name, True, (255, 255, 255))
        surf.blit(name_surf, (banner_rect.x + 55, banner_rect.y + 24))
        
        # Points
        points = self.current.get('points', 0)
        pts_surf = self.font_text.render(f"+{points} pts", True, (100, 255, 100))
        surf.blit(pts_surf, (banner_rect.x + 55, banner_rect.y + 42))
        
        # Check if this achievement has a reward
        try:
            from achievements_data import get_reward_for_achievement
            reward = get_reward_for_achievement(self.current.get('id', ''))
            if reward:
                reward_type = reward.get("type", "")
                if reward_type == "theme":
                    reward_text = "+ Theme!"
                elif reward_type == "pokemon":
                    reward_text = "+ Pokemon!"
                elif reward_type == "both":
                    reward_text = "+ Theme & Pokemon!"
                elif reward_type == "unlock":
                    reward_text = "+ Unlock!"
                else:
                    reward_text = "+ REWARD!"
                gift_surf = self.font_text.render(reward_text, True, (255, 200, 100))
                surf.blit(gift_surf, (banner_rect.x + 130, banner_rect.y + 42))
        except:
            pass
        
        # Game tag
        game = self.current.get('game', '')
        if game:
            game_surf = self.font_text.render(game, True, (150, 150, 200))
            surf.blit(game_surf, (banner_rect.right - 60, banner_rect.y + 42))
    
    def is_active(self):
        """Check if notification is currently showing"""
        return self.state != self.STATE_HIDDEN


# =============================================================================
# ACHIEVEMENT MANAGER
# =============================================================================

class AchievementManager:
    """
    Manages achievement state across all games.
    Handles loading, saving, checking conditions, and granting rewards.
    """
    
    def __init__(self):
        self.progress = {}  # {achievement_id: {"unlocked": bool, "unlocked_at": timestamp, "reward_claimed": bool}}
        self.stats = {}     # Global stats like total_transfers, total_sinew_stored, etc.
        self.tracking = {}  # PER-GAME tracking values {game_name: {hint_key: current_value}}
        self.high_water_marks = {}  # High water marks for values that should only go up {game: {key: max_value}}
        self.altering_cave_claimed = []  # List of species IDs claimed from Altering Cave slot machine
        self.current_game = None  # Currently active game for tracking
        self.notification_callback = None  # Callback to trigger notifications
        self._load_progress()
    
    def set_notification_callback(self, callback):
        """Set callback for achievement unlock notifications"""
        self.notification_callback = callback
    
    def set_current_game(self, game_name):
        """Set the current game for tracking purposes"""
        self.current_game = game_name
    
    def update_tracking(self, key, value, game_name=None):
        """Update a tracking value for progress display"""
        # Use specified game or current game or 'global' for Sinew/aggregate data
        game = game_name or self.current_game or 'global'
        if game not in self.tracking:
            self.tracking[game] = {}
        self.tracking[game][key] = value
    
    def update_high_water_mark(self, key, value, game_name=None):
        """
        Update a high water mark - value only increases, never decreases.
        Used for money tracking so spending doesn't reduce achievement progress.
        
        Returns the current high water mark (may be higher than value passed in).
        """
        game = game_name or self.current_game or 'global'
        if game not in self.high_water_marks:
            self.high_water_marks[game] = {}
        
        current_max = self.high_water_marks[game].get(key, 0)
        if value > current_max:
            self.high_water_marks[game][key] = value
            self._save_progress()  # Persist the new high water mark
            return value
        return current_max
    
    def get_high_water_mark(self, key, game_name=None, default=0):
        """Get the high water mark for a key"""
        game = game_name or self.current_game or 'global'
        return self.high_water_marks.get(game, {}).get(key, default)
    
    def get_tracking(self, key, default=0, game_name=None):
        """Get a tracking value for a specific game"""
        game = game_name or self.current_game or 'global'
        return self.tracking.get(game, {}).get(key, default)
    
    def get_tracking_for_game(self, game_name):
        """Get all tracking values for a specific game"""
        return self.tracking.get(game_name, {})
    
    # ==========================================================================
    # ALTERING CAVE ECHOES FEATURE
    # ==========================================================================
    
    def get_altering_cave_claimed(self):
        """
        Get list of species IDs that have been claimed from the Altering Cave slot machine.
        
        Returns:
            list: Species IDs (e.g., [179, 190, 204])
        """
        return list(self.altering_cave_claimed)
    
    def get_altering_cave_remaining(self):
        """
        Get list of Altering Cave Pokemon that haven't been claimed yet.
        
        Returns:
            list: Dicts with species, name, file for unclaimed Pokemon
        """
        from achievements_data import ALTERING_CAVE_POKEMON
        claimed = set(self.altering_cave_claimed)
        return [p for p in ALTERING_CAVE_POKEMON if p['species'] not in claimed]
    
    def claim_altering_cave_pokemon(self, species_id):
        """
        Mark an Altering Cave Pokemon as claimed.
        
        Args:
            species_id: The species ID that was claimed (e.g., 179 for Mareep)
            
        Returns:
            bool: True if this was a new claim, False if already claimed
        """
        if species_id in self.altering_cave_claimed:
            return False
        
        self.altering_cave_claimed.append(species_id)
        
        # Update tracking for the achievement
        count = len(self.altering_cave_claimed)
        self.update_tracking('altering_cave_echoes', count, 'Sinew')
        
        # Save progress
        self._save_progress()
        
        # Check if achievement should unlock (all 7 claimed)
        if count >= 7:
            from achievements_data import get_achievements_for
            sinew_achs = get_achievements_for("Sinew")
            for ach in sinew_achs:
                if "altering_cave_echoes" in ach.get("hint", ""):
                    if not self.is_unlocked(ach["id"]):
                        self.unlock(ach["id"], ach)
                    break
        
        print(f"[Achievements] Altering Cave Pokemon claimed: species {species_id} ({count}/7)")
        return True
    
    def is_altering_cave_complete(self):
        """Check if all 7 Altering Cave Pokemon have been claimed."""
        return len(self.altering_cave_claimed) >= 7
    
    def force_check_by_tracking(self, game_name=None):
        """
        Force check all achievements based on current tracking values.
        This catches achievements where tracking shows completion but unlock wasn't triggered.
        """
        from achievements_data import get_achievements_for, GAMES
        
        if game_name:
            games_to_check = [game_name]
        else:
            # BUGFIX: Only check games that actually have tracking data loaded.
            # Checking games with no tracking data causes false-positives for threshold
            # achievements (e.g. "dex_count >= 0" would pass on an empty dict) and
            # prevents phantom Emerald/FireRed achievements firing for Ruby-only players.
            games_to_check = [g for g in (GAMES + ["Sinew"]) if g in self.tracking]
        
        newly_unlocked = []
        
        for game in games_to_check:
            achievements = get_achievements_for(game)
            
            # Get the correct tracking data for this game
            if game == "Sinew":
                game_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
            else:
                game_tracking = self.tracking.get(game, {})
            
            # Get Sinew/global tracking for species checks
            sinew_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
            
            for ach in achievements:
                if self.is_unlocked(ach["id"]):
                    continue
                
                hint = ach.get("hint", "")
                unlocked = False
                
                # Check >= style hints against per-game tracking
                if ">=" in hint:
                    try:
                        parts = hint.split(">=")
                        key = parts[0].strip()
                        required = int(parts[1].strip().split()[0])
                        
                        # For money-related keys, use high water marks
                        if 'money' in key.lower():
                            current = self.get_high_water_mark(key, game)
                            # Also check current tracking in case it's higher
                            tracking_val = game_tracking.get(key, 0)
                            if tracking_val > current:
                                current = self.update_high_water_mark(key, tracking_val, game)
                        else:
                            current = game_tracking.get(key, 0)
                        
                        if current >= required:
                            unlocked = True
                            print(f"[Achievements] Force unlock: {ach['name']} ({current}/{required} for '{key}' in {game})")
                    except Exception as e:
                        pass
                
                # Check == True style hints
                if "== True" in hint:
                    try:
                        key = hint.split("==")[0].strip()
                        if game_tracking.get(key, False):
                            unlocked = True
                            print(f"[Achievements] Force unlock (bool): {ach['name']} ({key}=True)")
                    except:
                        pass
                
                # Species ownership hints - use per-game owned_set for non-Sinew, combined_pokedex for Sinew
                if "owns_species_" in hint and "owns_species_380_or_381" not in hint:
                    try:
                        species_id = int(hint.split("owns_species_")[1].split("_")[0].split()[0])
                        if game == "Sinew":
                            owned = sinew_tracking.get("combined_pokedex_set", set())
                        else:
                            owned = game_tracking.get("owned_set", set())
                        if species_id in owned:
                            unlocked = True
                            print(f"[Achievements] Force unlock (species): {ach['name']} (species {species_id} in {game} pokedex)")
                    except:
                        pass
                
                # Check Latias/Latios
                if "owns_species_380_or_381" in hint:
                    if game == "Sinew":
                        owned = sinew_tracking.get("combined_pokedex_set", set())
                    else:
                        owned = game_tracking.get("owned_set", set())
                    if 380 in owned or 381 in owned:
                        unlocked = True
                        print(f"[Achievements] Force unlock: {ach['name']} (Latias/Latios in {game})")
                
                # Check Regi trio
                if "owns_regi_trio" in hint:
                    if game == "Sinew":
                        owned = sinew_tracking.get("combined_pokedex_set", set())
                    else:
                        owned = game_tracking.get("owned_set", set())
                    if 377 in owned and 378 in owned and 379 in owned:
                        unlocked = True
                        print(f"[Achievements] Force unlock: {ach['name']} (Regi trio in {game})")
                
                # Check Weather trio
                if "owns_weather_trio" in hint:
                    if game == "Sinew":
                        owned = sinew_tracking.get("combined_pokedex_set", set())
                    else:
                        owned = game_tracking.get("owned_set", set())
                    if 382 in owned and 383 in owned and 384 in owned:
                        unlocked = True
                        print(f"[Achievements] Force unlock: {ach['name']} (Weather trio in {game})")
                
                # Check Legendary Birds (Articuno=144, Zapdos=145, Moltres=146)
                if "owns_legendary_birds" in hint:
                    if game == "Sinew":
                        owned = sinew_tracking.get("combined_pokedex_set", set())
                    else:
                        owned = game_tracking.get("owned_set", set())
                    if 144 in owned and 145 in owned and 146 in owned:
                        unlocked = True
                        print(f"[Achievements] Force unlock: {ach['name']} (Legendary Birds in {game})")
                
                if unlocked:
                    if self.unlock(ach["id"], ach):
                        newly_unlocked.append(ach["id"])
        
        return newly_unlocked
    
    def debug_stuck_achievements(self):
        """Debug function to show achievements where progress >= required but not unlocked"""
        from achievements_data import get_achievements_for, GAMES
        
        print("\n[Achievements] === STUCK ACHIEVEMENTS DEBUG ===")
        
        # Show tracking values for each game
        print(f"[Achievements] Per-game tracking:")
        for game in GAMES + ["Sinew", "global"]:
            game_tracking = self.tracking.get(game, {})
            if game_tracking:
                badges = game_tracking.get('badges', 'N/A')
                dex = game_tracking.get('dex_count', 'N/A')
                money = game_tracking.get('money', 'N/A')
                pc = game_tracking.get('pc_pokemon', 'N/A')
                owned_set = game_tracking.get('owned_set', set())
                owned_count = len(owned_set) if isinstance(owned_set, set) else 'N/A'
                print(f"[Achievements]   {game}: badges={badges}, dex={dex}, money={money}, pc={pc}, owned_set={owned_count} species")
                
                # Show legendaries in this game's owned_set
                if isinstance(owned_set, set) and owned_set:
                    legendaries = [144, 145, 146, 150, 151, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386]
                    found = [s for s in legendaries if s in owned_set]
                    if found:
                        print(f"[Achievements]     Legendaries in {game} owned_set: {found}")
        
        # Show Sinew/global tracking for combined pokedex
        sinew_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
        combined_set = sinew_tracking.get("combined_pokedex_set", set())
        print(f"[Achievements] combined_pokedex_set has {len(combined_set)} species")
        
        # Show legendary species in combined set
        legendaries = [144, 145, 146, 150, 151, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386]
        found = [s for s in legendaries if s in combined_set]
        if found:
            print(f"[Achievements] Legendaries in combined_pokedex_set: {found}")
        
        for game in GAMES + ["Sinew"]:
            achievements = get_achievements_for(game)
            for ach in achievements:
                if self.is_unlocked(ach["id"]):
                    continue
                
                progress = self.get_achievement_progress(ach)
                if progress:
                    current, required, percentage = progress
                    if percentage >= 100:
                        print(f"[Achievements] STUCK: {ach['name']} ({game})")
                        print(f"[Achievements]   hint: {ach.get('hint', 'N/A')}")
                        print(f"[Achievements]   progress: {current}/{required} ({percentage}%)")
                        print(f"[Achievements]   id: {ach['id']}")
        
        print("[Achievements] === END STUCK DEBUG ===\n")
    
    def get_achievement_progress(self, achievement):
        """
        Get progress for an achievement.
        
        Returns:
            tuple: (current, required, percentage) or None if not trackable
        """
        hint = achievement.get("hint", "")
        ach_game = achievement.get("game", "Sinew")
        
        # Determine which tracking data to use
        # For Sinew achievements, use global tracking
        # For per-game achievements, use that game's tracking
        if ach_game == "Sinew":
            game_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
        else:
            game_tracking = self.tracking.get(ach_game, {})
        
        # Parse ">=" style hints
        if ">=" in hint:
            try:
                parts = hint.split(">=")
                key = parts[0].strip()
                required = int(parts[1].strip().split()[0])
                
                # For money-related keys, use high water marks so progress never decreases
                if 'money' in key.lower():
                    current = self.get_high_water_mark(key, ach_game)
                    # Also check current tracking in case it's higher
                    tracking_val = game_tracking.get(key, 0)
                    if tracking_val > current:
                        current = self.update_high_water_mark(key, tracking_val, ach_game)
                else:
                    current = game_tracking.get(key, 0)
                
                # Special handling for milestone achievements (First Level X, etc.)
                # These should show 0/1 or 1/1, not current_level/required_level
                milestone_keys = ['any_pokemon_level']
                if key in milestone_keys:
                    achieved = 1 if current >= required else 0
                    return (achieved, 1, achieved * 100)
                
                percentage = min(100, int((current / required) * 100)) if required > 0 else 0
                return (current, required, percentage)
            except:
                pass
        
        # Boolean checks (== True style hints)
        if "== True" in hint:
            key = hint.split("==")[0].strip()
            current = 1 if game_tracking.get(key, False) else 0
            return (current, 1, current * 100)
        
        # Species ownership - use DIFFERENT data depending on whether it's a Sinew or per-game achievement
        # Per-game achievements should check that game's owned_set
        # Sinew achievements should check the combined_pokedex_set
        
        if "owns_species_" in hint:
            # Single species ownership
            try:
                species_id = int(hint.split("owns_species_")[1].split("_")[0])
                
                if ach_game == "Sinew":
                    # Sinew achievement - use combined pokedex from all games
                    sinew_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
                    owned = sinew_tracking.get("combined_pokedex_set", set())
                else:
                    # Per-game achievement - use that game's owned_set
                    owned = game_tracking.get("owned_set", set())
                
                current = 1 if species_id in owned else 0
                return (current, 1, current * 100)
            except:
                pass
        
        if "owns_regi_trio" in hint:
            if ach_game == "Sinew":
                sinew_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
                owned = sinew_tracking.get("combined_pokedex_set", set())
            else:
                owned = game_tracking.get("owned_set", set())
            count = sum(1 for s in [377, 378, 379] if s in owned)
            return (count, 3, int((count / 3) * 100))
        
        if "owns_weather_trio" in hint:
            if ach_game == "Sinew":
                sinew_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
                owned = sinew_tracking.get("combined_pokedex_set", set())
            else:
                owned = game_tracking.get("owned_set", set())
            count = sum(1 for s in [382, 383, 384] if s in owned)
            return (count, 3, int((count / 3) * 100))
        
        if "owns_legendary_birds" in hint:
            if ach_game == "Sinew":
                sinew_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
                owned = sinew_tracking.get("combined_pokedex_set", set())
            else:
                owned = game_tracking.get("owned_set", set())
            count = sum(1 for s in [144, 145, 146] if s in owned)
            return (count, 3, int((count / 3) * 100))
        
        if "owns_species_380_or_381" in hint:
            if ach_game == "Sinew":
                sinew_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
                owned = sinew_tracking.get("combined_pokedex_set", set())
            else:
                owned = game_tracking.get("owned_set", set())
            has_either = 380 in owned or 381 in owned
            return (1 if has_either else 0, 1, 100 if has_either else 0)
        
        # Altering Cave Echoes - special tracking
        if "altering_cave_echoes" in hint:
            claimed_count = len(getattr(self, 'altering_cave_claimed', []))
            return (claimed_count, 7, int((claimed_count / 7) * 100))
        
        return None
    
    def _load_progress(self):
        """Load achievement progress from file"""
        try:
            if os.path.exists(ACH_SAVE_PATH):
                with open(ACH_SAVE_PATH, 'r') as f:
                    data = json.load(f)
                    self.progress = data.get("progress", {})
                    self.stats = data.get("stats", {})
                    self.high_water_marks = data.get("high_water_marks", {})
                    self.altering_cave_claimed = data.get("altering_cave_claimed", [])
                print(f"[Achievements] Loaded progress: {len(self.progress)} achievements tracked")
                if self.altering_cave_claimed:
                    print(f"[Achievements] Altering Cave progress: {len(self.altering_cave_claimed)}/7 claimed")
        except Exception as e:
            print(f"[Achievements] Could not load progress: {e}")
            self.progress = {}
            self.stats = {}
            self.high_water_marks = {}
            self.altering_cave_claimed = []
    
    def _save_progress(self):
        """Save achievement progress to file"""
        try:
            os.makedirs(os.path.dirname(ACH_SAVE_PATH), exist_ok=True)
            with open(ACH_SAVE_PATH, 'w') as f:
                json.dump({
                    "progress": self.progress,
                    "stats": self.stats,
                    "high_water_marks": getattr(self, 'high_water_marks', {}),
                    "altering_cave_claimed": getattr(self, 'altering_cave_claimed', [])
                }, f, indent=2)
        except Exception as e:
            print(f"[Achievements] Could not save progress: {e}")
    
    def is_unlocked(self, achievement_id):
        """Check if an achievement is unlocked"""
        return self.progress.get(achievement_id, {}).get("unlocked", False)
    
    def unlock(self, achievement_id, achievement_data=None):
        """Unlock an achievement and optionally trigger notification"""
        if achievement_id not in self.progress:
            self.progress[achievement_id] = {}
        
        if not self.progress[achievement_id].get("unlocked"):
            self.progress[achievement_id]["unlocked"] = True
            self.progress[achievement_id]["unlocked_at"] = time.time()
            self.progress[achievement_id]["reward_claimed"] = False
            self._save_progress()
            print(f"[Achievements] *** UNLOCKED: {achievement_id} ***")
            
            # Trigger notification if callback set and we have achievement data
            if self.notification_callback and achievement_data:
                self.notification_callback(achievement_data)
            
            return True
        return False
    
    def unlock_achievement(self, achievement_data):
        """
        Alias for unlock() that accepts an achievement dict.
        Called from main.py's _on_event_claimed and similar callback paths.
        """
        if not achievement_data:
            return False
        ach_id = achievement_data.get("id") if isinstance(achievement_data, dict) else achievement_data
        return self.unlock(ach_id, achievement_data if isinstance(achievement_data, dict) else None)

    def is_reward_claimed(self, achievement_id):
        """Check if reward was claimed"""
        return self.progress.get(achievement_id, {}).get("reward_claimed", False)
    
    def get_reward_info(self, achievement_id):
        """Get reward info for an achievement"""
        from achievements_data import get_reward_for_achievement
        return get_reward_for_achievement(achievement_id)
    
    def has_reward(self, achievement_id):
        """Check if an achievement has a reward"""
        return self.get_reward_info(achievement_id) is not None
    
    def get_unclaimed_rewards_count(self):
        """Count achievements that are unlocked, have rewards, and should be shown for claiming"""
        from achievements_data import ACHIEVEMENT_REWARDS, GAME_SPECIFIC_REWARDS, PERGAME_ACHIEVEMENT_REWARDS, GAMES, GAME_PREFIX
        
        count = 0
        
        # Check ACHIEVEMENT_REWARDS
        for ach_id in ACHIEVEMENT_REWARDS:
            if self.is_unlocked(ach_id) and not self.is_reward_claimed(ach_id):
                if self.should_show_reward(ach_id):
                    count += 1
        
        # Check GAME_SPECIFIC_REWARDS
        for ach_id in GAME_SPECIFIC_REWARDS:
            if self.is_unlocked(ach_id) and not self.is_reward_claimed(ach_id):
                if self.should_show_reward(ach_id):
                    count += 1
        
        # Check PERGAME_ACHIEVEMENT_REWARDS (for each game)
        for suffix in PERGAME_ACHIEVEMENT_REWARDS:
            for game in GAMES:
                prefix = GAME_PREFIX.get(game, game.upper()[:4])
                full_id = f"{prefix}{suffix}"
                if self.is_unlocked(full_id) and not self.is_reward_claimed(full_id):
                    if self.should_show_reward(full_id):
                        count += 1
        
        return count
    
    def claim_reward(self, achievement_id):
        """
        Claim the reward for an achievement.
        UPDATED: Now uses dynamic Pokemon generation instead of .pks files.
        Returns: (success: bool, message: str)
        """
        if not self.is_unlocked(achievement_id):
            return False, "Achievement not unlocked"
        
        if self.is_reward_claimed(achievement_id):
            return False, "Reward already claimed"
        
        reward = self.get_reward_info(achievement_id)
        if not reward:
            return False, "No reward for this achievement"
        
        reward_type = reward.get("type", "")
        messages = []
        
        try:
            if reward_type == "theme":
                theme_file = reward.get("value", "")
                theme_name = reward.get("name", theme_file)
                success = self._unlock_theme(theme_file)
                if success:
                    messages.append(f"Theme '{theme_name}' unlocked!")
                else:
                    return False, f"Failed to unlock theme"
                    
            elif reward_type == "pokemon":
                # UPDATED: Use achievement ID for dynamic generation
                pokemon_achievement = reward.get("pokemon_achievement", achievement_id)
                pokemon_name = reward.get("name", "Pokemon")
                success, msg = self._deliver_pokemon(pokemon_achievement)
                if success:
                    messages.append(f"{pokemon_name} added to Sinew Storage!")
                else:
                    return False, msg
                    
            elif reward_type == "both":
                # Deliver both theme and pokemon
                theme_file = reward.get("theme", "")
                theme_name = reward.get("theme_name", theme_file)
                # UPDATED: Use achievement ID for dynamic generation
                pokemon_achievement = reward.get("pokemon_achievement", achievement_id)
                pokemon_name = reward.get("pokemon_name", "Pokemon")
                
                # Theme first
                theme_success = self._unlock_theme(theme_file)
                if theme_success:
                    messages.append(f"Theme '{theme_name}' unlocked!")
                
                # Then pokemon - UPDATED to use dynamic generation
                poke_success, poke_msg = self._deliver_pokemon(pokemon_achievement)
                if poke_success:
                    messages.append(f"{pokemon_name} added to Sinew Storage!")
                
                if not theme_success and not poke_success:
                    return False, "Failed to deliver rewards"
            
            elif reward_type == "unlock":
                # Special unlock type - just marks as claimed, unlocks a feature
                unlock_name = reward.get("name", "Feature")
                messages.append(f"{unlock_name} unlocked!")
            
            # Mark as claimed
            self.progress[achievement_id]["reward_claimed"] = True
            self._save_progress()
            
            return True, " ".join(messages)
            
        except Exception as e:
            print(f"[Achievements] Error claiming reward: {e}")
            return False, f"Error: {str(e)}"
    
    def _unlock_theme(self, theme_filename):
        """Unlock a theme by adding it to the unlocked themes list in settings"""
        try:
            import json
            import os
            
            settings_path = os.path.join(os.path.dirname(__file__), "sinew_settings.json")
            
            # Load current settings
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            
            # Add to unlocked themes
            if "unlocked_themes" not in settings:
                settings["unlocked_themes"] = []
            
            if theme_filename not in settings["unlocked_themes"]:
                settings["unlocked_themes"].append(theme_filename)
            
            # Save settings
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
            
            print(f"[Achievements] Theme unlocked: {theme_filename}")
            return True
            
        except Exception as e:
            print(f"[Achievements] Error unlocking theme: {e}")
            return False
    
    def _is_theme_unlocked(self, theme_filename):
        """Check if a theme is already unlocked"""
        try:
            import json
            import os
            
            settings_path = os.path.join(os.path.dirname(__file__), "sinew_settings.json")
            
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    unlocked = settings.get("unlocked_themes", [])
                    return theme_filename in unlocked
            return False
        except Exception:
            return False
    
    def should_show_reward(self, achievement_id):
        """
        Determine if an achievement reward should be shown/pinned for claiming.
        - Theme-only rewards: skip if theme already unlocked
        - Pokemon rewards (or both): always show (can claim multiple times)
        """
        reward = self.get_reward_info(achievement_id)
        if not reward:
            return False
        
        reward_type = reward.get("type", "")
        
        # Pokemon rewards can always be claimed again
        if reward_type == "pokemon":
            return True
        
        # "both" rewards (theme + pokemon) - show if pokemon not claimed OR theme not unlocked
        if reward_type == "both":
            # Always allow because it includes a Pokemon
            return True
        
        # Theme-only rewards - skip if theme already unlocked
        if reward_type == "theme":
            theme_file = reward.get("value", "")
            if self._is_theme_unlocked(theme_file):
                return False
            return True
        
        return True
    
    def _deliver_pokemon(self, achievement_id):
        """
        Deliver a Pokemon reward by generating it dynamically.
        UPDATED: Uses pokemon_generator instead of .pks files.
        Returns: (success: bool, message: str)
        """
        try:
            # Import the generator
            from pokemon_generator import generate_achievement_pokemon
            
            # Generate the Pokemon
            result = generate_achievement_pokemon(achievement_id)
            if result is None:
                print(f"[Achievements] No recipe found for achievement: {achievement_id}")
                return False, f"No recipe found for achievement: {achievement_id}"
            
            pokemon_bytes, pokemon_dict = result
            species_name = pokemon_dict.get('species_name', 'Pokemon')
            print(f"[Achievements] Generated {species_name}: {len(pokemon_bytes)} bytes")
            
            # Import Sinew storage
            try:
                from sinew_storage import get_sinew_storage
                sinew = get_sinew_storage()
                
                if not sinew or not sinew.is_loaded():
                    return False, "Sinew Storage not available"
                
                # Find first empty slot
                for box_num in range(1, 21):  # 20 boxes
                    box = sinew.get_box(box_num)
                    if box:
                        for slot_idx, slot in enumerate(box):
                            # Check if slot is truly empty
                            is_empty = (slot is None or 
                                       slot.get('empty', False) == True or 
                                       slot.get('species', 0) == 0)
                            
                            if is_empty:
                                # Store the Pokemon
                                pokemon_dict['raw_bytes'] = pokemon_bytes
                                pokemon_dict['empty'] = False
                                pokemon_dict['is_reward'] = True
                                success = sinew.set_pokemon_at(box_num, slot_idx, pokemon_dict)
                                if success:
                                    print(f"[Achievements] {species_name} delivered to Box {box_num}, Slot {slot_idx + 1}")
                                    return True, f"Stored in Box {box_num}"
                
                return False, "No empty slot in Sinew Storage"
                
            except ImportError:
                return False, "Sinew Storage module not available"
                
        except ImportError as e:
            print(f"[Achievements] Pokemon generator not available: {e}")
            return False, "Pokemon generator module not available"
        except Exception as e:
            print(f"[Achievements] Error delivering Pokemon: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error: {str(e)}"
    
    def _parse_pks_file(self, data):
        """
        Parse a Gen 3 .pks file (80 bytes) into a Pokemon data dict.
        
        Gen 3 Box Pokemon Structure (80 bytes):
        - 0-3: Personality Value (PID)
        - 4-7: Original Trainer ID (OT ID)  
        - 8-17: Nickname (10 bytes)
        - 18-19: Language
        - 20-26: OT Name (7 bytes)
        - 27: Markings
        - 28-29: Checksum
        - 30-31: Padding
        - 32-79: Encrypted data (48 bytes - 4 substructures)
        """
        import struct
        
        if len(data) < 80:
            print(f"[Achievements] Invalid .pks file: only {len(data)} bytes")
            return None
        
        try:
            # Read header
            personality = struct.unpack('<I', data[0:4])[0]
            ot_id = struct.unpack('<I', data[4:8])[0]
            
            # Nickname
            nickname = self._decode_gen3_text(data[8:18])
            
            # OT Name  
            ot_name = self._decode_gen3_text(data[20:27])
            
            # Decrypt the 48-byte data section
            encrypted_data = bytearray(data[32:80])
            decryption_key = personality ^ ot_id
            
            # Decrypt in 4-byte chunks
            decrypted = bytearray(48)
            for i in range(0, 48, 4):
                chunk = struct.unpack('<I', encrypted_data[i:i+4])[0]
                decrypted_chunk = chunk ^ decryption_key
                decrypted[i:i+4] = struct.pack('<I', decrypted_chunk)
            
            # Determine substructure order based on PID % 24
            orders = [
                [0,1,2,3], [0,1,3,2], [0,2,1,3], [0,3,1,2], [0,2,3,1], [0,3,2,1],
                [1,0,2,3], [1,0,3,2], [2,0,1,3], [3,0,1,2], [2,0,3,1], [3,0,2,1],
                [1,2,0,3], [1,3,0,2], [2,1,0,3], [3,1,0,2], [2,3,0,1], [3,2,0,1],
                [1,2,3,0], [1,3,2,0], [2,1,3,0], [3,1,2,0], [2,3,1,0], [3,2,1,0]
            ]
            order = orders[personality % 24]
            
            # Reorder substructures to G, A, E, M order
            substructs = [bytearray(12) for _ in range(4)]
            for i, target in enumerate(order):
                substructs[target] = decrypted[i*12:(i+1)*12]
            
            # Parse Growth substructure (G)
            species = struct.unpack('<H', substructs[0][0:2])[0]
            held_item = struct.unpack('<H', substructs[0][2:4])[0]
            experience = struct.unpack('<I', substructs[0][4:8])[0]
            friendship = substructs[0][9]
            
            # Parse Attacks substructure (A)
            moves = []
            for i in range(4):
                move_id = struct.unpack('<H', substructs[1][i*2:(i*2)+2])[0]
                if move_id > 0:
                    moves.append({'id': move_id, 'pp': substructs[1][8+i]})
            
            # Parse EVs substructure (E)
            evs = {
                'hp': substructs[2][0],
                'attack': substructs[2][1],
                'defense': substructs[2][2],
                'speed': substructs[2][3],
                'sp_attack': substructs[2][4],
                'sp_defense': substructs[2][5]
            }
            
            # Parse Misc substructure (M)
            # Byte 0: Pokerus status
            # Byte 1: Met location
            # Bytes 2-3: Origins info (met level, game of origin, ball, trainer gender)
            # Bytes 4-7: IVs/Egg/Ability
            # Bytes 8-11: Ribbons
            pokerus = substructs[3][0]
            met_location = substructs[3][1]
            origins_info = struct.unpack('<H', substructs[3][2:4])[0]
            iv_egg_ability = struct.unpack('<I', substructs[3][4:8])[0]
            
            # Extract origins info
            met_level = origins_info & 0x7F  # bits 0-6
            game_of_origin = (origins_info >> 7) & 0xF  # bits 7-10
            pokeball = (origins_info >> 11) & 0xF  # bits 11-14
            ot_gender = (origins_info >> 15) & 0x1  # bit 15
            
            # Extract IVs (5 bits each)
            ivs = {
                'hp': iv_egg_ability & 0x1F,
                'attack': (iv_egg_ability >> 5) & 0x1F,
                'defense': (iv_egg_ability >> 10) & 0x1F,
                'speed': (iv_egg_ability >> 15) & 0x1F,
                'sp_attack': (iv_egg_ability >> 20) & 0x1F,
                'sp_defense': (iv_egg_ability >> 25) & 0x1F
            }
            
            is_egg = bool((iv_egg_ability >> 30) & 1)
            ability_bit = (iv_egg_ability >> 31) & 1
            
            # Calculate level from experience (simplified - uses species growth rate)
            level = self._calc_level_from_exp(species, experience)
            
            # Check shiny
            tid = ot_id & 0xFFFF
            sid = (ot_id >> 16) & 0xFFFF
            pid_high = (personality >> 16) & 0xFFFF
            pid_low = personality & 0xFFFF
            shiny_value = tid ^ sid ^ pid_high ^ pid_low
            is_shiny = shiny_value < 8
            
            pokemon = {
                'personality': personality,
                'ot_id': ot_id,
                'nickname': nickname if nickname else self._get_species_name(species),
                'ot_name': ot_name,
                'species': species,
                'species_name': self._get_species_name(species),
                'held_item': held_item,
                'experience': experience,
                'level': level,
                'friendship': friendship,
                'moves': moves,
                'evs': evs,
                'ivs': ivs,
                'is_egg': is_egg,
                'is_shiny': is_shiny,
                'ability_bit': ability_bit,
                'met_location': met_location,
                'met_level': met_level,
                'pokeball': pokeball,
                'game_of_origin': game_of_origin,
                'ot_gender': ot_gender,
                'pokerus': pokerus,
                'raw_bytes': bytes(data[:80]),
                'is_reward': True,
            }
            
            print(f"[Achievements] Parsed Pokemon: {pokemon['species_name']} Lv.{pokemon['level']}")
            return pokemon
            
        except Exception as e:
            print(f"[Achievements] Error parsing .pks: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _decode_gen3_text(self, data):
        """Decode Gen 3 character encoding to string"""
        # Gen 3 character table
        char_table = {
            0x00: ' ', 0xAB: '!', 0xAC: '?', 0xAD: '.', 0xAE: '-',
            0xB0: '.', 0xB1: '"', 0xB2: '"', 0xB3: "'", 0xB4: "'",
            0xB5: 'm', 0xB6: 'f',
            0xBB: 'A', 0xBC: 'B', 0xBD: 'C', 0xBE: 'D', 0xBF: 'E',
            0xC0: 'F', 0xC1: 'G', 0xC2: 'H', 0xC3: 'I', 0xC4: 'J',
            0xC5: 'K', 0xC6: 'L', 0xC7: 'M', 0xC8: 'N', 0xC9: 'O',
            0xCA: 'P', 0xCB: 'Q', 0xCC: 'R', 0xCD: 'S', 0xCE: 'T',
            0xCF: 'U', 0xD0: 'V', 0xD1: 'W', 0xD2: 'X', 0xD3: 'Y',
            0xD4: 'Z', 0xD5: 'a', 0xD6: 'b', 0xD7: 'c', 0xD8: 'd',
            0xD9: 'e', 0xDA: 'f', 0xDB: 'g', 0xDC: 'h', 0xDD: 'i',
            0xDE: 'j', 0xDF: 'k', 0xE0: 'l', 0xE1: 'm', 0xE2: 'n',
            0xE3: 'o', 0xE4: 'p', 0xE5: 'q', 0xE6: 'r', 0xE7: 's',
            0xE8: 't', 0xE9: 'u', 0xEA: 'v', 0xEB: 'w', 0xEC: 'x',
            0xED: 'y', 0xEE: 'z', 0xEF: '0', 0xF0: '1', 0xF1: '2',
            0xF2: '3', 0xF3: '4', 0xF4: '5', 0xF5: '6', 0xF6: '7',
            0xF7: '8', 0xF8: '9',
        }
        
        result = ""
        for byte in data:
            if byte == 0xFF:  # Terminator
                break
            result += char_table.get(byte, '')
        return result.strip()
    
    def _get_species_name(self, species_id):
        """Get species name from ID"""
        try:
            from pokemon_database import get_species_name
            return get_species_name(species_id)
        except:
            # Fallback for common mythicals
            names = {
                151: "Mew", 251: "Celebi", 385: "Jirachi", 386: "Deoxys"
            }
            return names.get(species_id, f"Pokemon #{species_id}")
    
    def _calc_level_from_exp(self, species_id, exp):
        """Calculate level from experience points (simplified)"""
        # Most Pokemon use medium-slow or medium-fast growth
        # This is a simplified calculation
        
        # Growth rate exp tables (up to level 100)
        # Using medium-slow as default (most common for mythicals)
        medium_slow = [
            0, 9, 57, 96, 135, 179, 236, 314, 419, 560, 742, 973, 1261, 
            1612, 2035, 2535, 3120, 3798, 4575, 5460, 6458, 7577, 8825, 
            10208, 11735, 13411, 15244, 17242, 19411, 21760, 24294, 27021, 
            29949, 33084, 36435, 40007, 43808, 47846, 52127, 56660, 61450, 
            66505, 71833, 77440, 83335, 89523, 96012, 102810, 109923, 117360, 
            125126, 133229, 141677, 150476, 159635, 169159, 179056, 189334, 
            199999, 211060, 222522, 234393, 246681, 259392, 272535, 286115, 
            300140, 314618, 329555, 344960, 360838, 377197, 394045, 411388, 
            429235, 447591, 466464, 485862, 505791, 526260, 547274, 568841, 
            590969, 613664, 636935, 660787, 685228, 710266, 735907, 762160, 
            789030, 816525, 844653, 873420, 902835, 932903, 963632, 995030, 
            1027103, 1059860
        ]
        
        for level in range(100, 0, -1):
            if exp >= medium_slow[level - 1]:
                return level
        return 1
    
    def reset_achievement(self, achievement_id):
        """Reset a specific achievement (dev mode)"""
        if achievement_id in self.progress:
            del self.progress[achievement_id]
            
            # Special handling for Altering Cave achievement
            if "altering_cave" in achievement_id.lower() or self._is_altering_cave_achievement(achievement_id):
                self.altering_cave_claimed = []
                # Also reset tracking
                if 'Sinew' in self.tracking:
                    self.tracking['Sinew']['altering_cave_echoes'] = 0
                print(f"[Achievements] Also reset Altering Cave progress (0/7)")
            
            self._save_progress()
            print(f"[Achievements] Reset: {achievement_id}")
            return True
        return False
    
    def _is_altering_cave_achievement(self, achievement_id):
        """Check if an achievement ID is the Altering Cave achievement"""
        from achievements_data import get_achievements_for
        try:
            sinew_achs = get_achievements_for("Sinew")
            for ach in sinew_achs:
                if ach["id"] == achievement_id and "altering_cave_echoes" in ach.get("hint", ""):
                    return True
        except:
            pass
        return False
    
    def reset_altering_cave(self):
        """Reset Altering Cave progress specifically (dev mode)"""
        self.altering_cave_claimed = []
        if 'Sinew' in self.tracking:
            self.tracking['Sinew']['altering_cave_echoes'] = 0
        
        # Also reset the achievement itself
        from achievements_data import get_achievements_for
        try:
            sinew_achs = get_achievements_for("Sinew")
            for ach in sinew_achs:
                if "altering_cave_echoes" in ach.get("hint", ""):
                    if ach["id"] in self.progress:
                        del self.progress[ach["id"]]
                        print(f"[Achievements] Removed achievement: {ach['id']}")
                    break
        except:
            pass
        
        self._save_progress()
        print(f"[Achievements] Altering Cave progress reset (0/7), claimed={self.altering_cave_claimed}")
    
    def force_reload(self):
        """Force reload progress from file (useful after external changes)"""
        self._load_progress()
        print(f"[Achievements] Force reloaded - altering_cave_claimed={self.altering_cave_claimed}")
    
    def nuclear_reset(self):
        """
        Complete nuclear reset - deletes the save file and reinitializes everything.
        Use when normal reset doesn't work.
        """
        import os
        print(f"[Achievements] NUCLEAR RESET - deleting {ACH_SAVE_PATH}")
        try:
            if os.path.exists(ACH_SAVE_PATH):
                os.remove(ACH_SAVE_PATH)
                print(f"[Achievements] Deleted save file")
        except Exception as e:
            print(f"[Achievements] Could not delete file: {e}")
        
        # Clear everything in memory
        self.progress = {}
        self.stats = {}
        self.altering_cave_claimed = []
        self.high_water_marks = {}
        self.tracking = {}
        
        # Save fresh empty state
        self._save_progress()
        print(f"[Achievements] Nuclear reset complete - altering_cave_claimed={self.altering_cave_claimed}")
    
    def reset_all(self):
        """Reset all achievements (dev mode)"""
        print(f"[Achievements] reset_all called - BEFORE: altering_cave_claimed={self.altering_cave_claimed}")
        self.progress = {}
        self.stats = {}
        self.altering_cave_claimed = []  # Also reset Altering Cave progress
        self.high_water_marks = {}  # Also reset high water marks
        self.tracking = {}  # Also reset all tracking data
        print(f"[Achievements] reset_all - AFTER clearing: altering_cave_claimed={self.altering_cave_claimed}")
        self._save_progress()
        print(f"[Achievements] reset_all - AFTER save: altering_cave_claimed={self.altering_cave_claimed}")
        print("[Achievements] All achievements, stats, tracking, and Altering Cave progress reset!")
    
    def reset_game(self, game_name):
        """Reset all achievements for a specific game"""
        from achievements_data import get_achievements_for
        
        achievements = get_achievements_for(game_name)
        reset_count = 0
        for ach in achievements:
            if ach["id"] in self.progress:
                del self.progress[ach["id"]]
                reset_count += 1
        
        # Special handling for Sinew - also reset Altering Cave progress
        if game_name == "Sinew":
            self.altering_cave_claimed = []
            if 'Sinew' in self.tracking:
                self.tracking['Sinew']['altering_cave_echoes'] = 0
            print("[Achievements] Also reset Altering Cave progress (0/7)")
        
        self._save_progress()
        print(f"[Achievements] Reset {reset_count} achievements for {game_name}")
        return reset_count
    
    def revalidate_achievements(self):
        """
        Re-validate all unlocked achievements against current tracking data.
        Un-unlocks any achievements that were incorrectly unlocked.
        Returns list of achievement IDs that were revoked.
        """
        from achievements_data import get_achievements_for, GAMES
        
        revoked = []
        
        print("[Achievements] Re-validating all unlocked achievements...")
        
        for game in GAMES + ["Sinew"]:
            achievements = get_achievements_for(game)
            
            # Get the correct tracking data for this game
            if game == "Sinew":
                game_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
            else:
                game_tracking = self.tracking.get(game, {})
            
            sinew_tracking = self.tracking.get("Sinew", self.tracking.get("global", {}))
            
            # BUGFIX: If we have no tracking data for this game at all, we cannot
            # reliably validate its achievements (tracking is in-memory only and
            # gets populated when a save is loaded). Keep all achievements for
            # unloaded games rather than falsely revoking them.
            game_has_tracking = game in self.tracking
            
            for ach in achievements:
                if not self.is_unlocked(ach["id"]):
                    continue
                
                hint = ach.get("hint", "")
                should_be_unlocked = False
                
                # Check >= style hints
                if ">=" in hint:
                    try:
                        parts = hint.split(">=")
                        key = parts[0].strip()
                        required = int(parts[1].strip().split()[0])
                        
                        if not game_has_tracking:
                            # No tracking data for this game - cannot validate, keep the achievement
                            should_be_unlocked = True
                        elif 'money' in key.lower():
                            # BUGFIX: Use high water mark for money so spending doesn't revoke achievements
                            current = self.get_high_water_mark(key, game)
                            tracking_val = game_tracking.get(key, 0)
                            current = max(current, tracking_val)
                            should_be_unlocked = current >= required
                        else:
                            current = game_tracking.get(key, 0)
                            should_be_unlocked = current >= required
                    except:
                        should_be_unlocked = True  # Can't verify, keep it
                
                # Check == True style hints
                elif "== True" in hint:
                    try:
                        key = hint.split("==")[0].strip()
                        # Special case: dev_mode and debug_test are permanent unlocks - never revoke them
                        if key in ("dev_mode_activated", "debug_test_activated"):
                            should_be_unlocked = True
                        elif not game_has_tracking:
                            should_be_unlocked = True  # Can't validate without tracking data
                        else:
                            should_be_unlocked = game_tracking.get(key, False)
                    except:
                        should_be_unlocked = True
                
                # Check species ownership
                elif "owns_species_" in hint and "owns_species_380_or_381" not in hint:
                    try:
                        species_id = int(hint.split("owns_species_")[1].split("_")[0].split()[0])
                        if game == "Sinew":
                            owned = sinew_tracking.get("combined_pokedex_set", set())
                        elif not game_has_tracking:
                            # No tracking data - can't validate, keep the achievement
                            should_be_unlocked = True
                            owned = None
                        else:
                            owned = game_tracking.get("owned_set", set())
                        if owned is not None:
                            should_be_unlocked = species_id in owned
                    except:
                        should_be_unlocked = True
                
                elif "owns_species_380_or_381" in hint:
                    if game == "Sinew":
                        owned = sinew_tracking.get("combined_pokedex_set", set())
                        should_be_unlocked = 380 in owned or 381 in owned
                    elif not game_has_tracking:
                        should_be_unlocked = True
                    else:
                        owned = game_tracking.get("owned_set", set())
                        should_be_unlocked = 380 in owned or 381 in owned
                
                elif "owns_regi_trio" in hint:
                    if game == "Sinew":
                        owned = sinew_tracking.get("combined_pokedex_set", set())
                        should_be_unlocked = 377 in owned and 378 in owned and 379 in owned
                    elif not game_has_tracking:
                        should_be_unlocked = True
                    else:
                        owned = game_tracking.get("owned_set", set())
                        should_be_unlocked = 377 in owned and 378 in owned and 379 in owned
                
                elif "owns_weather_trio" in hint:
                    if game == "Sinew":
                        owned = sinew_tracking.get("combined_pokedex_set", set())
                        should_be_unlocked = 382 in owned and 383 in owned and 384 in owned
                    elif not game_has_tracking:
                        should_be_unlocked = True
                    else:
                        owned = game_tracking.get("owned_set", set())
                        should_be_unlocked = 382 in owned and 383 in owned and 384 in owned
                
                elif "owns_legendary_birds" in hint:
                    if game == "Sinew":
                        owned = sinew_tracking.get("combined_pokedex_set", set())
                        should_be_unlocked = 144 in owned and 145 in owned and 146 in owned
                    elif not game_has_tracking:
                        should_be_unlocked = True
                    else:
                        owned = game_tracking.get("owned_set", set())
                        should_be_unlocked = 144 in owned and 145 in owned and 146 in owned
                
                else:
                    # Unknown hint type, keep the achievement
                    should_be_unlocked = True
                
                if not should_be_unlocked:
                    print(f"[Achievements] REVOKING: {ach['name']} ({game}) - hint: {hint}")
                    del self.progress[ach["id"]]
                    revoked.append(ach["id"])
        
        if revoked:
            self._save_progress()
            print(f"[Achievements] Revoked {len(revoked)} incorrectly unlocked achievements")
        else:
            print("[Achievements] All unlocked achievements are valid")
        
        return revoked
    
    def get_stat(self, stat_name, default=0):
        """Get a global stat"""
        return self.stats.get(stat_name, default)
    
    def set_stat(self, stat_name, value):
        """Set a global stat"""
        self.stats[stat_name] = value
        self._save_progress()
    
    def increment_stat(self, stat_name, amount=1):
        """Increment a global stat"""
        self.stats[stat_name] = self.stats.get(stat_name, 0) + amount
        self._save_progress()
    
    def check_and_unlock(self, save_data, game_name, sinew_data=None):
        """
        Check all relevant achievements against save data and unlock any that are earned.
        
        Args:
            save_data: Parsed save data dict
            game_name: Name of the game (Ruby, Sapphire, etc.)
            sinew_data: Optional Sinew storage data for cross-game checks
            
        Returns:
            List of newly unlocked achievement IDs
        """
        from achievements_data import get_achievements_for, check_achievement_unlocked
        
        # Debug output
        dex = save_data.get('dex_caught', 0)
        money = save_data.get('money', 0)
        badges = save_data.get('badges', 0)
        pc_list = save_data.get('pc_pokemon', [])
        pc_len = len([p for p in pc_list if p and not p.get('empty')])
        party_list = save_data.get('party', [])
        party_len = len([p for p in party_list if p and not p.get('empty')])
        playtime = save_data.get('playtime_hours', 0)
        owned = save_data.get('owned_list', [])
        
        # Update high water mark for money - achievements only track the max ever reached
        # This prevents spending money from reducing achievement progress
        money_hwm = self.update_high_water_mark('money', money, game_name)
        if money_hwm > money:
            print(f"[Achievements]   Using money high water mark: {money_hwm} (current: {money})")
        
        # Create a modified save_data with high water mark money for achievement checking
        save_data_for_check = dict(save_data)
        save_data_for_check['money'] = money_hwm
        
        print(f"[Achievements] check_and_unlock for {game_name}:")
        print(f"[Achievements]   dex_caught={dex}, money={money} (hwm={money_hwm}), badges={badges}")
        print(f"[Achievements]   pc_pokemon={pc_len}, party={party_len}, playtime={playtime:.1f}h")
        print(f"[Achievements]   owned_list has {len(owned)} species")
        
        newly_unlocked = []
        
        # Check game-specific achievements
        game_achievements = get_achievements_for(game_name)
        checked_count = 0
        already_unlocked = 0
        
        for ach in game_achievements:
            if not self.is_unlocked(ach["id"]):
                checked_count += 1
                result = check_achievement_unlocked(ach, save_data_for_check)
                # Debug: show checks for key achievements
                hint = ach.get("hint", "")
                if "pc_pokemon" in hint or "money >=" in hint or "dex_count >=" in hint:
                    print(f"[Achievements]   Checking {ach['name']}: {hint} -> {result}")
                if result:
                    if self.unlock(ach["id"], ach):  # Pass achievement data for notification
                        newly_unlocked.append(ach["id"])
            else:
                already_unlocked += 1
        
        print(f"[Achievements]   Checked {checked_count} locked achievements, {already_unlocked} already unlocked")
        
        # Check Sinew achievements if sinew_data provided
        # BUGFIX: Sinew achievements must only be checked using aggregate sinew_data,
        # never using the per-game save_data. Passing Ruby's save_data to Sinew
        # achievement checks caused Emerald/FireRed achievements to fire incorrectly
        # because Sinew achievements share the same hint keys (dex_count, badges, etc.)
        if sinew_data:
            sinew_achievements = get_achievements_for("Sinew")
            # Build aggregate save data for Sinew checks
            all_saves = sinew_data.get("all_saves", [])
            sinew_save_data = sinew_data.get("aggregate", {})  # Use aggregate, not per-game data
            if sinew_save_data:  # Only check if we have proper aggregate data
                for ach in sinew_achievements:
                    if not self.is_unlocked(ach["id"]):
                        if check_achievement_unlocked(ach, sinew_save_data, all_saves):
                            if self.unlock(ach["id"], ach):
                                newly_unlocked.append(ach["id"])
        
        return newly_unlocked
    
    def get_unlocked_count(self, game_name=None):
        """Get count of unlocked achievements for a game or all"""
        from achievements_data import get_achievements_for, GAMES
        
        if game_name:
            achievements = get_achievements_for(game_name)
        else:
            achievements = []
            for game in GAMES + ["Sinew"]:
                achievements.extend(get_achievements_for(game))
        
        return sum(1 for a in achievements if self.is_unlocked(a["id"]))
    
    def get_total_count(self, game_name=None):
        """Get total achievement count for a game or all"""
        from achievements_data import get_achievements_for, GAMES
        
        if game_name:
            return len(get_achievements_for(game_name))
        else:
            total = 0
            for game in GAMES + ["Sinew"]:
                total += len(get_achievements_for(game))
            return total
    
    def get_points(self, game_name=None):
        """Get total points earned"""
        from achievements_data import get_achievements_for, GAMES
        
        if game_name:
            achievements = get_achievements_for(game_name)
        else:
            achievements = []
            for game in GAMES + ["Sinew"]:
                achievements.extend(get_achievements_for(game))
        
        return sum(a.get("points", 0) for a in achievements if self.is_unlocked(a["id"]))
    
    def check_sinew_achievements(self, sinew_storage_count=None, transfer_count=None, shiny_count=None, evolution_count=None):
        """
        Check Sinew-specific achievements based on storage stats.
        Call this after deposits/withdrawals/transfers.
        
        Note: Dirty Dex achievements are checked separately using combined_pokedex
        from all saves in _check_sinew_achievements_aggregate().
        
        Args:
            sinew_storage_count: Total Pokemon in Sinew storage
            transfer_count: Total transfers made
            shiny_count: Total shinies in Sinew storage
            evolution_count: Total evolutions triggered via Sinew
        """
        from achievements_data import get_achievements_for
        
        print(f"[Achievements] check_sinew_achievements: storage={sinew_storage_count}, transfers={transfer_count}, shiny={shiny_count}, evolutions={evolution_count}")
        
        newly_unlocked = []
        sinew_achievements = get_achievements_for("Sinew")
        
        for ach in sinew_achievements:
            if self.is_unlocked(ach["id"]):
                continue
            
            hint = ach.get("hint", "")
            unlocked = False
            
            # Check storage count achievements
            if sinew_storage_count is not None and "sinew_pokemon >=" in hint:
                try:
                    required = int(hint.split(">=")[1].strip().split()[0])
                    if sinew_storage_count >= required:
                        unlocked = True
                        print(f"[Achievements] Sinew storage achievement unlocked: {ach['name']} ({sinew_storage_count}/{required})")
                except:
                    pass
            
            # Check transfer count achievements  
            if transfer_count is not None and "sinew_transfers >=" in hint:
                try:
                    required = int(hint.split(">=")[1].strip().split()[0])
                    if transfer_count >= required:
                        unlocked = True
                except:
                    pass
            
            # Check shiny count achievements
            if shiny_count is not None and "shiny_count >=" in hint:
                try:
                    required = int(hint.split(">=")[1].strip().split()[0])
                    print(f"[Achievements] Checking shiny achievement: {ach['name']} - {shiny_count}/{required}")
                    if shiny_count >= required:
                        unlocked = True
                        print(f"[Achievements] Shiny achievement unlocked: {ach['name']}")
                except:
                    pass
            
            # Check evolution count achievements
            if evolution_count is not None and "sinew_evolutions >=" in hint:
                try:
                    required = int(hint.split(">=")[1].strip().split()[0])
                    if evolution_count >= required:
                        unlocked = True
                except:
                    pass
            
            if unlocked:
                if self.unlock(ach["id"], ach):
                    newly_unlocked.append(ach["id"])
        
        return newly_unlocked


# Global manager instance
_manager = None

# Global notification instance
_notification = None

def get_achievement_manager():
    """Get the global achievement manager instance"""
    global _manager
    if _manager is None:
        _manager = AchievementManager()
    return _manager

def get_achievement_notification(screen_width=None):
    """Get the global achievement notification instance"""
    global _notification
    if _notification is None and screen_width:
        _notification = AchievementNotification(screen_width)
    return _notification

def init_achievement_system(screen_width):
    """Initialize the achievement system with notification support"""
    manager = get_achievement_manager()
    notification = get_achievement_notification(screen_width)
    
    # Connect manager to notification system
    if notification:
        manager.set_notification_callback(notification.queue_achievement)
    
    return manager, notification


# =============================================================================
# UI COMPONENTS
# =============================================================================

class Modal:
    """Modal wrapper for achievements screen"""
    
    def __init__(self, w, h, font, game_filter=None, get_current_game_callback=None):
        self.width = w
        self.height = h
        self.font = font
        self.screen = AchievementsScreen(w, h, game_filter, get_current_game_callback)
    
    def update(self, events):
        self.screen.handle_events(events)
        return self.screen.visible
    
    def handle_controller(self, ctrl):
        """Handle controller input"""
        return self.screen.handle_controller(ctrl)
    
    def draw(self, surf):
        self.screen.draw(surf, self.font)


class AchievementsScreen:
    """Main achievements display screen"""
    
    # Game icon filenames
    GAME_ICON_FILES = {
        "Ruby": "ruby.png",
        "Sapphire": "sapphire.png",
        "Emerald": "emerald.png",
        "FireRed": "firered.png",
        "LeafGreen": "leafgreen.png",
        "Sinew": "trophy.png",
    }
    
    def __init__(self, width, height, game_filter=None, get_current_game_callback=None):
        from achievements_data import GAMES
        
        self.width = width
        self.height = height
        self.visible = True
        self.game_filter = game_filter  # None = all, or specific game name
        self.get_current_game_callback = get_current_game_callback
        
        # Get manager
        self.manager = get_achievement_manager()
        
        # Get controller
        self.controller = get_controller()
        
        # Fonts
        try:
            self.font_header = pygame.font.Font(FONT_PATH, 16)
            self.font_text = pygame.font.Font(FONT_PATH, 11)
            self.font_small = pygame.font.Font(FONT_PATH, 9)
            self.font_sinew = pygame.font.Font(FONT_PATH, 16)
        except:
            self.font_header = pygame.font.SysFont(None, 22)
            self.font_text = pygame.font.SysFont(None, 16)
            self.font_small = pygame.font.SysFont(None, 12)
            self.font_sinew = pygame.font.SysFont(None, 20)
        
        # Load game icons
        self.game_icons = {}
        self._load_game_icons()
        
        # Tab system
        self.tabs = ["All"] + GAMES + ["Sinew"]
        self.selected_tab = 0
        self.tab_focus = True  # True = navigating tabs, False = navigating achievements
        
        # Load achievements for current tab
        self._load_achievements()
        
        # Navigation
        self.selected_achievement = 0
        self.scroll_offset = 0
        self.achievements_per_page = 5
        
        # Detail popup
        self.detail_popup = None
        self._claim_button_rect = None
        
        # Reward claim message
        self._reward_message = None
        self._reward_message_time = 0
    
    def _load_game_icons(self):
        """Load game icons for achievement display"""
        icon_size = 24  # Size for the list icons
        
        for game_name, filename in self.GAME_ICON_FILES.items():
            icon_path = os.path.join("data", "sprites", "icons", filename)
            try:
                if os.path.exists(icon_path):
                    icon = pygame.image.load(icon_path).convert_alpha()
                    icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
                    self.game_icons[game_name] = icon
            except Exception as e:
                print(f"[Achievements] Could not load icon for {game_name}: {e}")
    
    def _load_achievements(self):
        """Load achievements for the current tab"""
        from achievements_data import get_achievements_for, GAMES
        
        # Debug: show any achievements that appear stuck (progress >= required but not unlocked)
        self.manager.debug_stuck_achievements()
        
        # Force check achievements against current tracking values
        # This catches any that should be unlocked but weren't
        self.manager.force_check_by_tracking()
        
        tab_name = self.tabs[self.selected_tab]
        
        if tab_name == "All":
            self.achievements = []
            for game in GAMES + ["Sinew"]:
                self.achievements.extend(get_achievements_for(game))
        else:
            self.achievements = get_achievements_for(tab_name)
        
        # Custom sort:
        # 1. Unlocked with unclaimed gifts (pulsing) - at top
        # 2. Unlocked achievements - by most recently unlocked
        # 3. Locked achievements - by completion percentage (highest first)
        def sort_key(a):
            ach_id = a["id"]
            is_unlocked = self.manager.is_unlocked(ach_id)
            has_reward = self.manager.has_reward(ach_id)
            reward_claimed = self.manager.is_reward_claimed(ach_id)
            # Only show as unclaimed if should_show_reward returns True
            # (skips theme-only rewards that are already unlocked)
            should_show = self.manager.should_show_reward(ach_id) if has_reward else False
            has_unclaimed_gift = is_unlocked and has_reward and not reward_claimed and should_show
            
            if has_unclaimed_gift:
                # Priority 0: unclaimed gifts at very top
                unlock_time = self.manager.progress.get(ach_id, {}).get("unlocked_at", 0)
                return (0, -unlock_time)  # Most recent first
            elif is_unlocked:
                # Priority 1: unlocked, sorted by unlock time (most recent first)
                unlock_time = self.manager.progress.get(ach_id, {}).get("unlocked_at", 0)
                return (1, -unlock_time)
            else:
                # Priority 2: locked, sorted by completion percentage (highest first)
                progress = self.manager.get_achievement_progress(a)
                if progress:
                    percentage = progress[2]  # (current, required, percentage)
                else:
                    percentage = 0
                return (2, -percentage, -a.get("points", 0))
        
        self.achievements.sort(key=sort_key)
        
        # Reset selection
        self.selected_achievement = 0
        self.scroll_offset = 0
    
    def on_back(self):
        self.visible = False
    
    def handle_controller(self, ctrl):
        """Handle controller input"""
        consumed = False
        
        # B button closes or goes back to tabs
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            if self.detail_popup:
                self.detail_popup = None
            elif not self.tab_focus:
                self.tab_focus = True
            else:
                self.visible = False
            return True
        
        # A button for details/claim
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if self.tab_focus:
                # Enter achievement list
                self.tab_focus = False
                self.selected_achievement = 0
            elif self.detail_popup:
                # Check if there's an unclaimed reward to claim
                ach = self.detail_popup
                is_unlocked = self.manager.is_unlocked(ach["id"])
                has_reward = self.manager.has_reward(ach["id"])
                reward_claimed = self.manager.is_reward_claimed(ach["id"])
                
                if is_unlocked and has_reward and not reward_claimed:
                    # Claim the reward
                    success, message = self.manager.claim_reward(ach["id"])
                    if success:
                        print(f"[Achievements] Reward claimed: {message}")
                        # Show a brief message (could add a toast notification later)
                        self._reward_message = message
                        self._reward_message_time = pygame.time.get_ticks()
                    else:
                        print(f"[Achievements] Reward claim failed: {message}")
                else:
                    # Close detail popup
                    self.detail_popup = None
            elif self.achievements:
                # Show detail popup
                ach = self.achievements[self.selected_achievement]
                self.detail_popup = ach
            return True
        
        if self.tab_focus:
            # Tab navigation
            if ctrl.is_dpad_just_pressed('left'):
                ctrl.consume_dpad('left')
                self.selected_tab = (self.selected_tab - 1) % len(self.tabs)
                self._load_achievements()
                consumed = True
            
            if ctrl.is_dpad_just_pressed('right'):
                ctrl.consume_dpad('right')
                self.selected_tab = (self.selected_tab + 1) % len(self.tabs)
                self._load_achievements()
                consumed = True
            
            if ctrl.is_dpad_just_pressed('down'):
                ctrl.consume_dpad('down')
                if self.achievements:
                    self.tab_focus = False
                    self.selected_achievement = 0
                consumed = True
        else:
            # Achievement list navigation
            if ctrl.is_dpad_just_pressed('up'):
                ctrl.consume_dpad('up')
                if self.selected_achievement > 0:
                    self.selected_achievement -= 1
                    if self.selected_achievement < self.scroll_offset:
                        self.scroll_offset = self.selected_achievement
                else:
                    # Go back to tabs
                    self.tab_focus = True
                consumed = True
            
            if ctrl.is_dpad_just_pressed('down'):
                ctrl.consume_dpad('down')
                if self.selected_achievement < len(self.achievements) - 1:
                    self.selected_achievement += 1
                    if self.selected_achievement >= self.scroll_offset + self.achievements_per_page:
                        self.scroll_offset = self.selected_achievement - self.achievements_per_page + 1
                consumed = True
        
        # L/R for quick tab switch
        if ctrl.is_button_just_pressed('L'):
            ctrl.consume_button('L')
            self.selected_tab = (self.selected_tab - 1) % len(self.tabs)
            self._load_achievements()
            consumed = True
        
        if ctrl.is_button_just_pressed('R'):
            ctrl.consume_button('R')
            self.selected_tab = (self.selected_tab + 1) % len(self.tabs)
            self._load_achievements()
            consumed = True
        
        return consumed
    
    def handle_events(self, events):
        """Handle pygame events"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.detail_popup:
                        self.detail_popup = None
                    else:
                        self.visible = False
    
    def draw(self, surf, font):
        # Background
        surf.fill(ui_colors.COLOR_BG)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, (0, 0, self.width, self.height), 2)
        
        # Title
        title = self.font_header.render("Achievements", True, ui_colors.COLOR_TEXT)
        surf.blit(title, (15, 10))
        
        # Progress for current tab
        tab_name = self.tabs[self.selected_tab]
        if tab_name == "All":
            unlocked = self.manager.get_unlocked_count()
            total = self.manager.get_total_count()
            points = self.manager.get_points()
        else:
            unlocked = self.manager.get_unlocked_count(tab_name)
            total = self.manager.get_total_count(tab_name)
            points = self.manager.get_points(tab_name)
        
        progress_text = f"{unlocked}/{total}"
        progress_surf = self.font_text.render(progress_text, True, (100, 200, 100))
        surf.blit(progress_surf, (self.width - 80, 12))
        
        # Points
        points_text = f"{points}pts"
        points_surf = self.font_small.render(points_text, True, (255, 215, 0))
        surf.blit(points_surf, (self.width - 80, 26))
        
        # Unclaimed gifts indicator
        unclaimed_count = self.manager.get_unclaimed_rewards_count()
        if unclaimed_count > 0:
            gift_text = f"{unclaimed_count} REWARD{'S' if unclaimed_count > 1 else ''} TO CLAIM!"
            gift_surf = self.font_small.render(gift_text, True, (255, 180, 100))
            # Center it under the title
            gift_x = 15 + title.get_width() + 20
            surf.blit(gift_surf, (gift_x, 15))
        
        # Draw tabs
        tab_y = 40
        tab_x = 10
        total_width = self.width - 20
        
        # Calculate tab widths based on text length
        tab_labels = ["All", "Ruby", "Sapphire", "Emerald", "FireRed", "LeafGreen", "Sinew"]
        
        for i, tab in enumerate(self.tabs):
            is_selected = (i == self.selected_tab)
            
            # Calculate position - distribute evenly
            tab_width = total_width // len(self.tabs)
            tab_rect = pygame.Rect(tab_x + i * tab_width, tab_y, tab_width - 2, 22)
            
            if is_selected:
                bg_color = ui_colors.COLOR_HIGHLIGHT if self.tab_focus else (60, 80, 60)
                pygame.draw.rect(surf, bg_color, tab_rect)
                text_color = (255, 255, 255)
            else:
                pygame.draw.rect(surf, (40, 40, 50), tab_rect)
                text_color = (150, 150, 150)
            
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, tab_rect, 1)
            
            # Full tab label
            label = tab
            label_surf = self.font_small.render(label, True, text_color)
            label_rect = label_surf.get_rect(center=tab_rect.center)
            surf.blit(label_surf, label_rect)
        
        # Draw achievements list
        y_start = 70
        item_height = 42
        
        if not self.achievements:
            no_ach = self.font_text.render("No achievements", True, (100, 100, 100))
            surf.blit(no_ach, (self.width // 2 - 60, y_start + 50))
        else:
            visible_achievements = self.achievements[self.scroll_offset:self.scroll_offset + self.achievements_per_page]
            
            for i, achievement in enumerate(visible_achievements):
                actual_index = self.scroll_offset + i
                y = y_start + i * item_height
                is_selected = (actual_index == self.selected_achievement) and not self.tab_focus
                is_unlocked = self.manager.is_unlocked(achievement["id"])
                
                # Check for unclaimed gift (respecting should_show_reward)
                has_reward = self.manager.has_reward(achievement["id"])
                reward_claimed = self.manager.is_reward_claimed(achievement["id"])
                should_show = self.manager.should_show_reward(achievement["id"]) if has_reward else False
                has_unclaimed_gift = is_unlocked and has_reward and not reward_claimed and should_show
                
                # Draw achievement box
                box_rect = pygame.Rect(10, y, self.width - 20, item_height - 3)
                
                # Background color
                if has_unclaimed_gift:
                    # Special background for unclaimed gifts
                    bg_color = (60, 55, 40) if not is_selected else (80, 70, 50)
                elif is_unlocked:
                    bg_color = (50, 70, 50) if not is_selected else (60, 100, 60)
                else:
                    bg_color = (35, 35, 45) if not is_selected else (50, 50, 70)
                
                pygame.draw.rect(surf, bg_color, box_rect)
                
                # Border - pulsing for unclaimed gifts
                if has_unclaimed_gift:
                    # Pulsing gold border
                    pulse = (math.sin(pygame.time.get_ticks() * 0.005) + 1) / 2  # 0 to 1
                    pulse_color = (
                        int(180 + 75 * pulse),  # 180-255
                        int(140 + 75 * pulse),  # 140-215
                        int(50 * pulse)          # 0-50
                    )
                    pygame.draw.rect(surf, pulse_color, box_rect, 3)
                elif is_selected:
                    pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, box_rect, 2)
                else:
                    pygame.draw.rect(surf, ui_colors.COLOR_BORDER, box_rect, 1)
                
                # Status icon - use game icon
                icon_rect = pygame.Rect(box_rect.x + 5, box_rect.y + 5, 28, 28)
                game = achievement.get('game', 'Sinew')
                
                if is_unlocked:
                    pygame.draw.rect(surf, (255, 215, 0), icon_rect, border_radius=3)
                else:
                    pygame.draw.rect(surf, (60, 60, 60), icon_rect, border_radius=3)
                
                # Draw game icon or Sinew "S"
                if game in self.game_icons:
                    icon = self.game_icons[game]
                    # Center the icon
                    icon_x = icon_rect.x + (icon_rect.width - icon.get_width()) // 2
                    icon_y = icon_rect.y + (icon_rect.height - icon.get_height()) // 2
                    # Dim if locked
                    if not is_unlocked:
                        dimmed = icon.copy()
                        dimmed.fill((100, 100, 100, 180), special_flags=pygame.BLEND_RGBA_MULT)
                        surf.blit(dimmed, (icon_x, icon_y))
                    else:
                        surf.blit(icon, (icon_x, icon_y))
                else:
                    # Sinew - draw "S"
                    s_color = (50, 50, 0) if is_unlocked else (80, 80, 80)
                    s_text = self.font_sinew.render("S", True, s_color)
                    s_rect = s_text.get_rect(center=icon_rect.center)
                    surf.blit(s_text, s_rect)
                
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, icon_rect, 1)
                
                # Achievement name (no truncation)
                name_color = ui_colors.COLOR_TEXT if is_unlocked else (120, 120, 120)
                name_surf = self.font_text.render(achievement['name'], True, name_color)
                surf.blit(name_surf, (box_rect.x + 40, box_rect.y + 4))
                
                # Progress or description
                if is_unlocked:
                    # Show description for unlocked (no truncation)
                    desc_color = (150, 150, 150)
                    desc_text = achievement.get('desc', '')
                    desc_surf = self.font_small.render(desc_text, True, desc_color)
                    surf.blit(desc_surf, (box_rect.x + 40, box_rect.y + 20))
                else:
                    # Show progress for locked achievements
                    progress = self.manager.get_achievement_progress(achievement)
                    if progress:
                        current, required, percentage = progress
                        # Progress bar background
                        bar_x = box_rect.x + 40
                        bar_y = box_rect.y + 22
                        bar_width = 120
                        bar_height = 8
                        
                        pygame.draw.rect(surf, (40, 40, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=2)
                        
                        # Progress bar fill
                        fill_width = int((bar_width - 2) * (percentage / 100))
                        if fill_width > 0:
                            # Color based on progress: red -> yellow -> green
                            if percentage < 33:
                                bar_color = (180, 80, 80)
                            elif percentage < 66:
                                bar_color = (180, 180, 80)
                            else:
                                bar_color = (80, 180, 80)
                            pygame.draw.rect(surf, bar_color, (bar_x + 1, bar_y + 1, fill_width, bar_height - 2), border_radius=2)
                        
                        # Progress text
                        progress_text = f"{current}/{required}"
                        progress_surf = self.font_small.render(progress_text, True, (150, 150, 150))
                        surf.blit(progress_surf, (bar_x + bar_width + 5, bar_y - 2))
                    else:
                        # No trackable progress - show description (no truncation)
                        desc_color = (80, 80, 80)
                        desc_text = achievement.get('desc', '')
                        desc_surf = self.font_small.render(desc_text, True, desc_color)
                        surf.blit(desc_surf, (box_rect.x + 40, box_rect.y + 20))
                
                # Points (top right corner)
                points = achievement.get('points', 0)
                pts_color = (255, 215, 0) if is_unlocked else (80, 80, 80)
                pts_surf = self.font_small.render(f"{points}pts", True, pts_color)
                surf.blit(pts_surf, (box_rect.right - 45, box_rect.y + 4))
                
                # Reward indicator (under points, if has reward)
                # has_reward and reward_claimed already calculated at top of loop
                if has_reward:
                    reward_info = self.manager.get_reward_info(achievement["id"])
                    
                    if reward_info:
                        # Get reward name with proper label prefix
                        reward_type = reward_info.get("type", "")
                        if reward_type == "both":
                            pokemon_name = reward_info.get('pokemon_name', 'Gift')
                            theme_name = reward_info.get('theme_name', 'Theme')
                            reward_name = f"Theme + Pokemon"
                        elif reward_type == "pokemon":
                            reward_name = f"Pokemon: {reward_info.get('name', 'Pokemon')}"
                        elif reward_type == "theme":
                            reward_name = f"Theme: {reward_info.get('name', 'Theme')}"
                        elif reward_type == "unlock":
                            reward_name = f"Unlock: {reward_info.get('name', 'Feature')}"
                        else:
                            reward_name = reward_info.get("name", "Reward")
                        
                        if has_unclaimed_gift:
                            # Unclaimed gift - bright and attention-grabbing
                            gift_text = f"[{reward_name}]"
                            gift_color = (255, 200, 100)  # Orange/gold
                            gift_surf = self.font_small.render(gift_text, True, gift_color)
                            surf.blit(gift_surf, (box_rect.right - gift_surf.get_width() - 5, box_rect.y + 18))
                        elif is_unlocked and reward_claimed:
                            # Already claimed - bright green (was too dark)
                            gift_text = f"[{reward_name}]"
                            gift_color = (100, 255, 100)  # Bright green
                            gift_surf = self.font_small.render(gift_text, True, gift_color)
                            surf.blit(gift_surf, (box_rect.right - gift_surf.get_width() - 5, box_rect.y + 18))
                        else:
                            # Locked - show reward preview dimmed
                            gift_text = f"[{reward_name}]"
                            gift_color = (100, 100, 100)
                            gift_surf = self.font_small.render(gift_text, True, gift_color)
                            surf.blit(gift_surf, (box_rect.right - gift_surf.get_width() - 5, box_rect.y + 18))
        
        # Scroll indicators
        if len(self.achievements) > self.achievements_per_page:
            if self.scroll_offset > 0:
                up_arrow = self.font_text.render("^", True, (100, 200, 100))
                surf.blit(up_arrow, (self.width - 20, y_start - 5))
            
            max_scroll = len(self.achievements) - self.achievements_per_page
            if self.scroll_offset < max_scroll:
                down_arrow = self.font_text.render("v", True, (100, 200, 100))
                surf.blit(down_arrow, (self.width - 20, y_start + self.achievements_per_page * item_height - 15))
        
        # Controller hints
        hints = "L/R:Tab  D-Pad:Nav  A:Details  B:Back"
        hint_surf = self.font_small.render(hints, True, (100, 100, 100))
        surf.blit(hint_surf, (10, self.height - 18))
        
        # Draw detail popup if active
        if self.detail_popup:
            self._draw_detail_popup(surf)
    
    def _draw_detail_popup(self, surf):
        """Draw achievement detail popup with reward claiming"""
        ach = self.detail_popup
        is_unlocked = self.manager.is_unlocked(ach["id"])
        has_reward = self.manager.has_reward(ach["id"])
        reward_claimed = self.manager.is_reward_claimed(ach["id"])
        reward_info = self.manager.get_reward_info(ach["id"]) if has_reward else None
        # Check if this reward should be shown (respects theme-already-unlocked logic)
        should_show = self.manager.should_show_reward(ach["id"]) if has_reward else False
        
        # Overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))
        
        # Calculate popup height based on content
        if has_reward:
            popup_h = 220  # Taller for reward section
        else:
            popup_h = 180
        
        # Popup box
        popup_w = self.width - 40
        popup_x = 20
        popup_y = (self.height - popup_h) // 2
        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
        
        pygame.draw.rect(surf, ui_colors.COLOR_BG, popup_rect)
        border_color = (255, 215, 0) if is_unlocked else ui_colors.COLOR_BORDER
        pygame.draw.rect(surf, border_color, popup_rect, 3)
        
        # Title
        title_surf = self.font_header.render(ach["name"], True, ui_colors.COLOR_TEXT)
        surf.blit(title_surf, (popup_x + 15, popup_y + 15))
        
        # Status
        status = "UNLOCKED!" if is_unlocked else "Locked"
        status_color = (100, 255, 100) if is_unlocked else (255, 100, 100)
        status_surf = self.font_text.render(status, True, status_color)
        surf.blit(status_surf, (popup_x + popup_w - 100, popup_y + 18))
        
        # Description
        desc = ach.get("desc", "No description")
        desc_surf = self.font_text.render(desc, True, (200, 200, 200))
        surf.blit(desc_surf, (popup_x + 15, popup_y + 45))
        
        # Progress bar for locked achievements
        if not is_unlocked:
            progress = self.manager.get_achievement_progress(ach)
            if progress:
                current, required, percentage = progress
                
                # Progress label
                progress_label = self.font_small.render("Progress:", True, (150, 150, 100))
                surf.blit(progress_label, (popup_x + 15, popup_y + 70))
                
                # Progress bar
                bar_x = popup_x + 80
                bar_y = popup_y + 72
                bar_width = popup_w - 180
                bar_height = 12
                
                pygame.draw.rect(surf, (40, 40, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=3)
                
                fill_width = int((bar_width - 2) * (percentage / 100))
                if fill_width > 0:
                    if percentage < 33:
                        bar_color = (180, 80, 80)
                    elif percentage < 66:
                        bar_color = (180, 180, 80)
                    else:
                        bar_color = (80, 180, 80)
                    pygame.draw.rect(surf, bar_color, (bar_x + 1, bar_y + 1, fill_width, bar_height - 2), border_radius=3)
                
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, (bar_x, bar_y, bar_width, bar_height), 1, border_radius=3)
                
                # Progress text
                progress_text = f"{current}/{required} ({percentage}%)"
                progress_surf = self.font_small.render(progress_text, True, (200, 200, 200))
                surf.blit(progress_surf, (bar_x + bar_width + 10, bar_y))
            else:
                # Show hint if no progress tracking
                hint = ach.get("hint", "")
                if hint:
                    hint_label = self.font_small.render("Hint:", True, (150, 150, 100))
                    surf.blit(hint_label, (popup_x + 15, popup_y + 70))
                    hint_text = hint[:50] + "..." if len(hint) > 50 else hint
                    hint_surf = self.font_small.render(hint_text, True, (120, 120, 100))
                    surf.blit(hint_surf, (popup_x + 50, popup_y + 70))
        
        # Game and Points row
        game = ach.get("game", "Sinew")
        game_surf = self.font_small.render(f"Game: {game}", True, (100, 150, 200))
        surf.blit(game_surf, (popup_x + 15, popup_y + 95))
        
        points = ach.get("points", 0)
        pts_surf = self.font_text.render(f"{points} Points", True, (255, 215, 0))
        surf.blit(pts_surf, (popup_x + 15, popup_y + 115))
        
        # Category
        category = ach.get("category", "")
        if category:
            cat_surf = self.font_small.render(f"Category: {category}", True, (150, 150, 150))
            surf.blit(cat_surf, (popup_x + 15, popup_y + 140))
        
        # Reward section (show for any achievement with reward)
        if has_reward:
            reward_y = popup_y + 160
            
            # Build reward description with proper labels
            reward_type = reward_info.get("type", "")
            
            if reward_type == "theme":
                reward_desc = f"Theme: {reward_info.get('name', 'Theme')}"
            elif reward_type == "pokemon":
                reward_desc = f"Pokemon: {reward_info.get('name', 'Pokemon')}"
            elif reward_type == "both":
                theme_name = reward_info.get('theme_name', 'Theme')
                pokemon_name = reward_info.get('pokemon_name', 'Pokemon')
                reward_desc = f"Theme: {theme_name} + Pokemon: {pokemon_name}"
            elif reward_type == "unlock":
                reward_desc = f"Unlock: {reward_info.get('name', 'Feature')}"
            else:
                reward_desc = "Reward available"
            
            if not is_unlocked:
                # Show reward preview (greyed out)
                reward_surf = self.font_small.render(f"[LOCKED] {reward_desc}", True, (120, 120, 120))
                surf.blit(reward_surf, (popup_x + 15, reward_y))
            elif reward_claimed and not should_show:
                # Already claimed and shouldn't show again (theme-only)
                reward_surf = self.font_small.render(f"[CLAIMED] {reward_desc}", True, (150, 255, 150))
                surf.blit(reward_surf, (popup_x + 15, reward_y))
            elif not should_show:
                # Theme already unlocked from another achievement
                reward_surf = self.font_small.render(f"[OWNED] {reward_desc}", True, (150, 255, 150))
                surf.blit(reward_surf, (popup_x + 15, reward_y))
            else:
                # Show claim button - UNCLAIMED AND UNLOCKED (or Pokemon re-claim)
                reward_surf = self.font_small.render(reward_desc, True, (255, 200, 100))
                surf.blit(reward_surf, (popup_x + 15, reward_y))
                
                # Claim button
                btn_x = popup_x + popup_w - 120
                btn_y = reward_y - 5
                btn_rect = pygame.Rect(btn_x, btn_y, 100, 25)
                
                # Button styling (highlighted green)
                pygame.draw.rect(surf, (80, 120, 80), btn_rect, border_radius=5)
                pygame.draw.rect(surf, (100, 200, 100), btn_rect, 2, border_radius=5)
                
                btn_text = self.font_small.render("CLAIM (A)", True, (255, 255, 255))
                btn_text_rect = btn_text.get_rect(center=btn_rect.center)
                surf.blit(btn_text, btn_text_rect)
                
                # Store claim button rect for click detection
                self._claim_button_rect = btn_rect
        else:
            self._claim_button_rect = None
        
        # Close hint
        close_y = popup_y + popup_h - 20
        if has_reward and is_unlocked and should_show:
            close_hint = self.font_small.render("A = Claim | B = Close", True, (100, 100, 100))
        else:
            close_hint = self.font_small.render("Press A or B to close", True, (100, 100, 100))
        hint_rect = close_hint.get_rect(centerx=popup_x + popup_w // 2, y=close_y)
        surf.blit(close_hint, hint_rect)
        
        # Show reward claim success message
        current_time = pygame.time.get_ticks()
        if self._reward_message and current_time - self._reward_message_time < 3000:
            # Draw success message overlay
            msg_surf = self.font_text.render(self._reward_message, True, (255, 255, 255))
            msg_rect = msg_surf.get_rect(centerx=popup_x + popup_w // 2, centery=popup_y + popup_h // 2)
            
            # Background box
            bg_rect = msg_rect.inflate(30, 20)
            pygame.draw.rect(surf, (40, 100, 40), bg_rect, border_radius=8)
            pygame.draw.rect(surf, (100, 200, 100), bg_rect, 3, border_radius=8)
            
            surf.blit(msg_surf, msg_rect)
    
    def handle_event(self, event):
        """Legacy event handler"""
        pass