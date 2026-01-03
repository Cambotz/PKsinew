"""
Sinew Export Modal
View and export save data in readable format
"""

import pygame
import json
import os
from datetime import datetime
import ui_colors  # Import module to get dynamic theme colors
from controller import get_controller, NavigableList

# Try to import save data manager and name lookups
try:
    from save_data_manager import get_manager, get_species_name
    SAVE_MANAGER_AVAILABLE = True
except ImportError:
    SAVE_MANAGER_AVAILABLE = False
    get_species_name = lambda x: f"Pokemon #{x}"
    print("[ExportModal] Save data manager not available")

try:
    from item_names import get_item_name
except ImportError:
    get_item_name = lambda x: f"Item #{x}"

try:
    from move_data import get_move_name
except ImportError:
    get_move_name = lambda x: f"Move #{x}"

try:
    from location_data import get_location_name
except ImportError:
    get_location_name = lambda x, y=None: f"Location #{x}"

try:
    from pokemon_summary import get_base_stats, calculate_hp
    HP_CALC_AVAILABLE = True
except ImportError:
    HP_CALC_AVAILABLE = False
    get_base_stats = lambda x: {}
    calculate_hp = lambda b, i, e, l: 0


def sanitize_for_json(obj):
    """
    Recursively sanitize an object for JSON serialization.
    Removes bytes and converts problematic types.
    """
    if isinstance(obj, bytes):
        return None
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items() 
                if not isinstance(v, bytes) and k not in ('raw_data', 'raw_bytes', 'data', 'encrypted_data')}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj if not isinstance(item, bytes)]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        try:
            return str(obj)
        except:
            return None


class ExportModal:
    """Modal for viewing and exporting save data"""
    
    def __init__(self, width, height, game_name=None, close_callback=None):
        self.width = width
        self.height = height
        self.game_name = game_name or "Unknown"
        self.close_callback = close_callback
        self.visible = True
        
        # Fonts
        try:
            self.font_header = pygame.font.Font("fonts/Pokemon_GB.ttf", 14)
            self.font_text = pygame.font.Font("fonts/Pokemon_GB.ttf", 10)
            self.font_small = pygame.font.Font("fonts/Pokemon_GB.ttf", 8)
        except:
            self.font_header = pygame.font.SysFont(None, 20)
            self.font_text = pygame.font.SysFont(None, 14)
            self.font_small = pygame.font.SysFont(None, 12)
        
        # Tabs
        self.tabs = ["Trainer & Items", "Pokemon", "Export"]
        self.selected_tab = 0
        self.tab_focus = True
        
        # Scroll positions for each tab
        self.scroll_positions = {0: 0, 1: 0, 2: 0}
        
        # Export options (toggles)
        self.export_options = [
            {"name": "Trainer Info", "key": "trainer", "value": True},
            {"name": "Items", "key": "items", "value": True},
            {"name": "Party Pokemon", "key": "party", "value": True},
            {"name": "PC Box Pokemon", "key": "box", "value": True},
            {"name": "Full Pokemon Details", "key": "detailed", "value": False},
        ]
        self.selected_option = 0
        
        # Status message
        self.status_message = None
        self.status_timer = 0
        
        # Determine game type for location lookups
        self.game_type = 'FRLG' if 'Fire' in self.game_name or 'Leaf' in self.game_name else 'RSE'
        
        # Load save data
        self.save_data = self._load_save_data()
        
        # Debug output
        print(f"[ExportModal] Loaded data - Party: {len(self.save_data.get('party', []))}, Box: {len(self.save_data.get('box', []))}")
        
        # Pre-render content lines for scrolling
        self._prepare_content()
    
    def _load_save_data(self):
        """Load current save data"""
        data = {
            "trainer": {},
            "items": [],
            "party": [],
            "box": [],
        }
        
        if not SAVE_MANAGER_AVAILABLE:
            return data
        
        try:
            manager = get_manager()
            if not manager.parser:
                return data
            
            # Trainer info
            try:
                trainer_info = manager.get_trainer_info()
                if trainer_info:
                    data["trainer"] = {
                        "name": trainer_info.get("name", "Unknown"),
                        "id": trainer_info.get("id", 0),
                        "secret_id": trainer_info.get("secret_id", 0),
                        "money": trainer_info.get("money", 0),
                        "gender": trainer_info.get("gender", "Unknown"),
                        "playtime": manager.get_play_time() if hasattr(manager, 'get_play_time') else "0:00",
                        "badges": manager.get_badge_count() if hasattr(manager, 'get_badge_count') else 0,
                    }
            except Exception as e:
                print(f"[ExportModal] Error loading trainer: {e}")
            
            # Items
            try:
                items = manager.get_items_with_names() if hasattr(manager, 'get_items_with_names') else []
                if items:
                    data["items"] = items
            except Exception as e:
                print(f"[ExportModal] Error loading items: {e}")
            
            # Party Pokemon
            try:
                party = manager.get_party()
                if party:
                    data["party"] = [p for p in party if p and not p.get('empty')]
            except Exception as e:
                print(f"[ExportModal] Error loading party: {e}")
            
            # PC Box Pokemon
            try:
                if hasattr(manager, 'get_all_boxes'):
                    all_boxes = manager.get_all_boxes()
                    if all_boxes:
                        for box_num, box_pokemon in all_boxes.items():
                            if box_pokemon:
                                for pkmn in box_pokemon:
                                    if pkmn and not pkmn.get('empty'):
                                        data["box"].append(pkmn)
                        print(f"[ExportModal] Loaded {len(data['box'])} box pokemon")
            except Exception as e:
                print(f"[ExportModal] Error loading box: {e}")
            
        except Exception as e:
            print(f"[ExportModal] Error loading save data: {e}")
        
        return data
    
    def _enrich_pokemon_for_export(self, pkmn):
        """Convert Pokemon IDs to readable names for export"""
        if not isinstance(pkmn, dict):
            return pkmn
        
        result = {}
        
        species_id = pkmn.get('species', 0)
        result['species'] = get_species_name(species_id) if species_id else "Unknown"
        result['species_id'] = species_id
        
        nickname = pkmn.get('nickname', '')
        if nickname and nickname != result['species']:
            result['nickname'] = nickname
        
        result['level'] = pkmn.get('level', 0)
        
        # Get HP - calculate if not available (common for PC box pokemon)
        current_hp = pkmn.get('current_hp')
        max_hp = pkmn.get('max_hp')
        
        # If max_hp is missing, try to calculate it
        if max_hp is None and HP_CALC_AVAILABLE and species_id:
            base_stats = get_base_stats(species_id)
            base_hp = base_stats.get('hp', 0)
            if base_hp > 0:
                # Get IVs and EVs
                ivs = pkmn.get('ivs', {})
                evs = pkmn.get('evs', {})
                iv_hp = ivs.get('hp', 0) if isinstance(ivs, dict) else 0
                ev_hp = evs.get('hp', 0) if isinstance(evs, dict) else 0
                level = pkmn.get('level', 1)
                
                max_hp = calculate_hp(base_hp, iv_hp, ev_hp, level)
        
        # If we have max_hp but no current_hp, assume full health
        if max_hp is not None:
            result['max_hp'] = max_hp
            result['current_hp'] = current_hp if current_hp is not None else max_hp
        elif current_hp is not None:
            result['current_hp'] = current_hp
        
        if 'ot_name' in pkmn:
            result['original_trainer'] = pkmn['ot_name']
        if 'ot_id' in pkmn:
            result['ot_id'] = pkmn['ot_id']
        
        if 'nature' in pkmn:
            result['nature'] = pkmn['nature']
        
        held_item = pkmn.get('held_item', 0)
        if held_item:
            result['held_item'] = get_item_name(held_item)
            result['held_item_id'] = held_item
        
        moves = pkmn.get('moves', [])
        if moves:
            result['moves'] = []
            for move in moves:
                if isinstance(move, dict):
                    move_id = move.get('id', move.get('move_id', 0))
                    if move_id:
                        result['moves'].append({
                            'name': get_move_name(move_id),
                            'id': move_id,
                            'pp': move.get('pp', 0),
                            'pp_ups': move.get('pp_ups', 0)
                        })
                elif isinstance(move, int) and move:
                    result['moves'].append({
                        'name': get_move_name(move),
                        'id': move
                    })
        
        met_location = pkmn.get('met_location', 0)
        if met_location:
            result['met_location'] = get_location_name(met_location, self.game_type)
            result['met_location_id'] = met_location
        
        ball = pkmn.get('pokeball', pkmn.get('ball', 0))
        if ball:
            result['pokeball'] = get_item_name(ball)
        
        if 'experience' in pkmn:
            result['experience'] = pkmn['experience']
        if 'friendship' in pkmn:
            result['friendship'] = pkmn['friendship']
        if 'is_shiny' in pkmn:
            result['is_shiny'] = pkmn['is_shiny']
        
        ability = pkmn.get('ability', pkmn.get('ability_num', None))
        if ability is not None:
            result['ability_slot'] = ability
        
        return result
    
    def _enrich_pokemon_detailed(self, pkmn):
        """Add detailed stats to pokemon export"""
        result = self._enrich_pokemon_for_export(pkmn)
        
        ivs = pkmn.get('ivs', {})
        if ivs:
            result['ivs'] = ivs
        
        evs = pkmn.get('evs', {})
        if evs:
            result['evs'] = evs
        
        stats = pkmn.get('stats', {})
        if stats:
            result['stats'] = stats
        
        if 'pokerus' in pkmn:
            result['pokerus'] = pkmn['pokerus']
        if 'markings' in pkmn:
            result['markings'] = pkmn['markings']
        
        contest = pkmn.get('contest_stats', {})
        if contest:
            result['contest_stats'] = contest
        
        return result
    
    def _prepare_content(self):
        """Prepare content lines for each tab"""
        self.tab_content = {
            0: self._prepare_trainer_items_content(),
            1: self._prepare_pokemon_content(),
            2: [],
        }
    
    def _prepare_trainer_items_content(self):
        """Prepare trainer and items content lines"""
        lines = []
        
        lines.append(("header", "TRAINER INFO"))
        lines.append(("spacer", ""))
        
        trainer = self.save_data.get("trainer", {})
        lines.append(("data", f"Name: {trainer.get('name', 'Unknown')}"))
        lines.append(("data", f"ID: {trainer.get('id', 0):05d}"))
        lines.append(("data", f"Secret ID: {trainer.get('secret_id', 0):05d}"))
        lines.append(("data", f"Money: ${trainer.get('money', 0):,}"))
        lines.append(("data", f"Gender: {trainer.get('gender', 'Unknown')}"))
        lines.append(("data", f"Play Time: {trainer.get('playtime', '0:00')}"))
        lines.append(("data", f"Badges: {trainer.get('badges', 0)}"))
        
        lines.append(("spacer", ""))
        lines.append(("spacer", ""))
        
        lines.append(("header", "ITEMS"))
        lines.append(("spacer", ""))
        
        items = self.save_data.get("items", {})
        if isinstance(items, dict):
            for pocket_name, pocket_items in items.items():
                if pocket_items:
                    lines.append(("subheader", f"  {pocket_name}"))
                    for item in pocket_items:
                        if isinstance(item, dict):
                            name = item.get("name", "Unknown")
                            qty = item.get("quantity", 1)
                            if qty > 0:
                                lines.append(("data", f"    {name} x{qty}"))
                    lines.append(("spacer", ""))
        elif isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    name = item.get("name", "Unknown")
                    qty = item.get("quantity", 1)
                    lines.append(("data", f"{name} x{qty}"))
        
        if not items:
            lines.append(("dim", "No items found"))
        
        return lines
    
    def _prepare_pokemon_content(self):
        """Prepare pokemon content lines"""
        lines = []
        
        lines.append(("header", "PARTY POKEMON"))
        lines.append(("spacer", ""))
        
        party = self.save_data.get("party", [])
        valid_party = [p for p in party if isinstance(p, dict) and not p.get('empty')]
        
        if valid_party:
            for i, pkmn in enumerate(valid_party):
                lines.extend(self._format_pokemon(pkmn, i + 1))
                lines.append(("spacer", ""))
        else:
            lines.append(("dim", "No party pokemon"))
        
        lines.append(("spacer", ""))
        
        lines.append(("header", "PC BOX POKEMON"))
        lines.append(("spacer", ""))
        
        box = self.save_data.get("box", [])
        valid_box = [p for p in box if isinstance(p, dict) and not p.get('empty')]
        
        if valid_box:
            lines.append(("data", f"Total in PC: {len(valid_box)}"))
            lines.append(("spacer", ""))
            
            for pkmn in valid_box[:50]:
                lines.extend(self._format_pokemon_brief(pkmn))
            
            if len(valid_box) > 50:
                lines.append(("dim", f"... and {len(valid_box) - 50} more"))
        else:
            lines.append(("dim", "No pokemon in PC"))
        
        return lines
    
    def _format_pokemon(self, pkmn, slot=None):
        """Format a pokemon for display (detailed)"""
        lines = []
        
        if isinstance(pkmn, dict) and not pkmn.get('empty'):
            nickname = pkmn.get("nickname", "")
            species_id = pkmn.get('species', 0)
            species = pkmn.get("species_name") or get_species_name(species_id)
            level = pkmn.get("level", 0)
            
            if nickname and nickname != species:
                display_name = f"{nickname} ({species})"
            else:
                display_name = species
            
            if slot:
                lines.append(("subheader", f"Slot {slot}: {display_name}"))
            else:
                lines.append(("subheader", display_name))
            
            lines.append(("data", f"  Level: {level}"))
            
            # Get HP - calculate if not available
            hp = pkmn.get("current_hp", pkmn.get("hp"))
            max_hp = pkmn.get("max_hp") or pkmn.get("stats", {}).get("hp")
            
            # Calculate max_hp if missing
            if max_hp is None and HP_CALC_AVAILABLE and species_id:
                base_stats = get_base_stats(species_id)
                base_hp = base_stats.get('hp', 0)
                if base_hp > 0:
                    ivs = pkmn.get('ivs', {})
                    evs = pkmn.get('evs', {})
                    iv_hp = ivs.get('hp', 0) if isinstance(ivs, dict) else 0
                    ev_hp = evs.get('hp', 0) if isinstance(evs, dict) else 0
                    level = pkmn.get('level', 1)
                    max_hp = calculate_hp(base_hp, iv_hp, ev_hp, level)
            
            if max_hp:
                # Assume full HP if current_hp not available
                display_hp = hp if hp is not None else max_hp
                lines.append(("data", f"  HP: {display_hp}/{max_hp}"))
            
            held_item = pkmn.get('held_item', 0)
            if held_item:
                lines.append(("data", f"  Item: {get_item_name(held_item)}"))
            
            ot = pkmn.get("ot_name")
            if ot:
                lines.append(("data", f"  OT: {ot}"))
            
            nature = pkmn.get("nature")
            if nature:
                lines.append(("data", f"  Nature: {nature}"))
            
            moves = pkmn.get('moves', [])
            if moves:
                move_names = []
                for move in moves[:4]:
                    if isinstance(move, dict):
                        move_id = move.get('id', move.get('move_id', 0))
                        if move_id:
                            move_names.append(get_move_name(move_id))
                    elif isinstance(move, int) and move:
                        move_names.append(get_move_name(move))
                if move_names:
                    lines.append(("data", f"  Moves: {', '.join(move_names)}"))
        
        return lines
    
    def _format_pokemon_brief(self, pkmn):
        """Format a pokemon briefly (one line)"""
        lines = []
        
        if isinstance(pkmn, dict) and not pkmn.get('empty'):
            nickname = pkmn.get("nickname", "")
            species_id = pkmn.get('species', 0)
            species = pkmn.get("species_name") or get_species_name(species_id)
            level = pkmn.get("level", 0)
            
            if nickname and nickname != species:
                text = f"Lv.{level} {nickname} ({species})"
            else:
                text = f"Lv.{level} {species}"
            
            lines.append(("data", text))
        
        return lines
    
    def handle_controller(self, ctrl):
        """Handle controller input"""
        if self.status_timer > 0:
            self.status_timer -= 1
            if self.status_timer <= 0:
                self.status_message = None
        
        consumed = False
        
        if ctrl.is_button_just_pressed('L'):
            ctrl.consume_button('L')
            self.selected_tab = (self.selected_tab - 1) % len(self.tabs)
            self.tab_focus = True
            consumed = True
        
        if ctrl.is_button_just_pressed('R'):
            ctrl.consume_button('R')
            self.selected_tab = (self.selected_tab + 1) % len(self.tabs)
            self.tab_focus = True
            consumed = True
        
        if self.tab_focus:
            if ctrl.is_dpad_just_pressed('left'):
                ctrl.consume_dpad('left')
                self.selected_tab = (self.selected_tab - 1) % len(self.tabs)
                consumed = True
            
            if ctrl.is_dpad_just_pressed('right'):
                ctrl.consume_dpad('right')
                self.selected_tab = (self.selected_tab + 1) % len(self.tabs)
                consumed = True
            
            if ctrl.is_dpad_just_pressed('down') or ctrl.is_button_just_pressed('A'):
                if ctrl.is_dpad_just_pressed('down'):
                    ctrl.consume_dpad('down')
                if ctrl.is_button_just_pressed('A'):
                    ctrl.consume_button('A')
                self.tab_focus = False
                consumed = True
        else:
            if self.selected_tab == 2:
                if ctrl.is_dpad_just_pressed('up'):
                    ctrl.consume_dpad('up')
                    if self.selected_option == 0:
                        self.tab_focus = True
                    else:
                        self.selected_option = self.selected_option - 1
                    consumed = True
                
                if ctrl.is_dpad_just_pressed('down'):
                    ctrl.consume_dpad('down')
                    self.selected_option = (self.selected_option + 1) % (len(self.export_options) + 1)
                    consumed = True
                
                if ctrl.is_dpad_just_pressed('left') or ctrl.is_dpad_just_pressed('right'):
                    ctrl.consume_dpad('left')
                    ctrl.consume_dpad('right')
                    if self.selected_option < len(self.export_options):
                        self.export_options[self.selected_option]["value"] = not self.export_options[self.selected_option]["value"]
                    consumed = True
                
                if ctrl.is_button_just_pressed('A'):
                    ctrl.consume_button('A')
                    if self.selected_option < len(self.export_options):
                        self.export_options[self.selected_option]["value"] = not self.export_options[self.selected_option]["value"]
                    else:
                        self._do_export()
                    consumed = True
            else:
                if ctrl.is_dpad_just_pressed('up'):
                    ctrl.consume_dpad('up')
                    if self.scroll_positions[self.selected_tab] == 0:
                        self.tab_focus = True
                    else:
                        self.scroll_positions[self.selected_tab] = self.scroll_positions[self.selected_tab] - 1
                    consumed = True
                
                if ctrl.is_dpad_just_pressed('down'):
                    ctrl.consume_dpad('down')
                    max_scroll = max(0, len(self.tab_content.get(self.selected_tab, [])) - 15)
                    self.scroll_positions[self.selected_tab] = min(max_scroll, self.scroll_positions[self.selected_tab] + 1)
                    consumed = True
        
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            if not self.tab_focus:
                self.tab_focus = True
            else:
                self.visible = False
                if self.close_callback:
                    self.close_callback()
            consumed = True
        
        return consumed
    
    def _do_export(self):
        """Export selected data to JSON file"""
        export_data = {
            "game": self.game_name,
            "exported_at": datetime.now().isoformat(),
        }
        
        include_trainer = any(o["key"] == "trainer" and o["value"] for o in self.export_options)
        include_items = any(o["key"] == "items" and o["value"] for o in self.export_options)
        include_party = any(o["key"] == "party" and o["value"] for o in self.export_options)
        include_box = any(o["key"] == "box" and o["value"] for o in self.export_options)
        include_detailed = any(o["key"] == "detailed" and o["value"] for o in self.export_options)
        
        if include_trainer:
            export_data["trainer"] = sanitize_for_json(self.save_data.get("trainer", {}))
        
        if include_items:
            items = self.save_data.get("items", {})
            if isinstance(items, dict):
                flattened = []
                for pocket_name, pocket_items in items.items():
                    for item in pocket_items:
                        if isinstance(item, dict) and item.get("quantity", 0) > 0:
                            flattened.append({
                                "pocket": pocket_name,
                                "name": item.get("name", "Unknown"),
                                "quantity": item.get("quantity", 0),
                            })
                export_data["items"] = flattened
            else:
                export_data["items"] = sanitize_for_json(items)
        
        if include_party:
            party = self.save_data.get("party", [])
            if include_detailed:
                export_data["party"] = [
                    sanitize_for_json(self._enrich_pokemon_detailed(p))
                    for p in party if isinstance(p, dict) and not p.get('empty')
                ]
            else:
                export_data["party"] = [
                    sanitize_for_json(self._enrich_pokemon_for_export(p))
                    for p in party if isinstance(p, dict) and not p.get('empty')
                ]
        
        if include_box:
            box = self.save_data.get("box", [])
            if include_detailed:
                export_data["box"] = [
                    sanitize_for_json(self._enrich_pokemon_detailed(p))
                    for p in box if isinstance(p, dict) and not p.get('empty')
                ]
            else:
                export_data["box"] = [
                    sanitize_for_json(self._enrich_pokemon_for_export(p))
                    for p in box if isinstance(p, dict) and not p.get('empty')
                ]
        
        os.makedirs("exports", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"exports/{self.game_name}_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.status_message = f"Saved: {filename}"
            self.status_timer = 180
            print(f"[ExportModal] Exported to {filename}")
        except Exception as e:
            self.status_message = f"Export failed!"
            self.status_timer = 180
            print(f"[ExportModal] Export error: {e}")
    
    def draw(self, surf):
        """Draw the export modal"""
        # Get theme colors dynamically
        COLOR_BG = ui_colors.COLOR_BG
        COLOR_HEADER = ui_colors.COLOR_HEADER
        COLOR_BORDER = ui_colors.COLOR_BORDER
        COLOR_TEXT = ui_colors.COLOR_TEXT
        COLOR_HIGHLIGHT = ui_colors.COLOR_HIGHLIGHT
        COLOR_BUTTON = ui_colors.COLOR_BUTTON
        COLOR_BUTTON_HOVER = ui_colors.COLOR_BUTTON_HOVER
        COLOR_SUCCESS = ui_colors.COLOR_SUCCESS
        COLOR_ERROR = ui_colors.COLOR_ERROR
        
        # Background
        pygame.draw.rect(surf, COLOR_BG, (0, 0, self.width, self.height))
        pygame.draw.rect(surf, COLOR_BORDER, (0, 0, self.width, self.height), 2)
        
        # Title
        title = f"Export - {self.game_name}"
        title_surf = self.font_header.render(title, True, COLOR_TEXT)
        surf.blit(title_surf, (15, 10))
        
        # Tab bar background
        tab_bar_rect = pygame.Rect(0, 32, self.width, 28)
        pygame.draw.rect(surf, COLOR_HEADER, tab_bar_rect)
        pygame.draw.line(surf, COLOR_BORDER, (0, 60), (self.width, 60), 1)
        
        # Tabs
        tab_y = 35
        tab_x = 10
        for i, tab in enumerate(self.tabs):
            is_selected = (i == self.selected_tab)
            is_focused = is_selected and self.tab_focus
            
            tab_surf = self.font_text.render(tab, True, COLOR_TEXT)
            tab_width = tab_surf.get_width() + 14
            tab_rect = pygame.Rect(tab_x, tab_y, tab_width, 22)
            
            if is_selected:
                pygame.draw.rect(surf, COLOR_BUTTON, tab_rect, border_radius=3)
                border_color = COLOR_HIGHLIGHT if is_focused else COLOR_BORDER
                pygame.draw.rect(surf, border_color, tab_rect, 2, border_radius=3)
                text_color = COLOR_HIGHLIGHT if is_focused else COLOR_TEXT
                tab_surf = self.font_text.render(tab, True, text_color)
            
            surf.blit(tab_surf, (tab_x + 7, tab_y + 5))
            tab_x += tab_width + 5
        
        # L/R hint
        lr_hint = self.font_small.render("L/R", True, COLOR_BORDER)
        surf.blit(lr_hint, (self.width - lr_hint.get_width() - 10, tab_y + 6))
        
        # Content area
        content_y = 65
        content_height = self.height - content_y - 45
        content_rect = pygame.Rect(10, content_y, self.width - 20, content_height)
        pygame.draw.rect(surf, COLOR_HEADER, content_rect, border_radius=5)
        pygame.draw.rect(surf, COLOR_BORDER, content_rect, 1, border_radius=5)
        
        # Draw tab content
        if self.selected_tab == 2:
            self._draw_export_options(surf, content_rect)
        else:
            self._draw_scrollable_content(surf, content_rect)
        
        # Bottom hints/status
        hint_y = self.height - 18
        
        if self.status_message:
            msg_surf = self.font_text.render(self.status_message, True, COLOR_SUCCESS)
            msg_rect = msg_surf.get_rect(centerx=self.width // 2, centery=hint_y)
            surf.blit(msg_surf, msg_rect)
        else:
            if self.tab_focus:
                hints = "< > Tabs   Down: Enter   B: Close"
            elif self.selected_tab == 2:
                hints = "Up/Down: Select   < > Toggle   A: Confirm   B: Back"
            else:
                hints = "Up/Down: Scroll   B: Back"
            hint_surf = self.font_small.render(hints, True, COLOR_BORDER)
            hint_rect = hint_surf.get_rect(centerx=self.width // 2, centery=hint_y)
            surf.blit(hint_surf, hint_rect)
    
    def _draw_scrollable_content(self, surf, rect):
        """Draw scrollable text content"""
        COLOR_BORDER = ui_colors.COLOR_BORDER
        COLOR_HIGHLIGHT = ui_colors.COLOR_HIGHLIGHT
        COLOR_TEXT = ui_colors.COLOR_TEXT
        COLOR_BUTTON = ui_colors.COLOR_BUTTON
        
        content = self.tab_content.get(self.selected_tab, [])
        scroll = self.scroll_positions.get(self.selected_tab, 0)
        
        y = rect.y + 8
        line_height = 14
        max_lines = (rect.height - 16) // line_height
        
        for i, (line_type, text) in enumerate(content[scroll:scroll + max_lines]):
            if line_type == "header":
                color = COLOR_BORDER
                text_surf = self.font_text.render(text, True, color)
            elif line_type == "subheader":
                color = COLOR_HIGHLIGHT
                text_surf = self.font_text.render(text, True, color)
            elif line_type == "dim":
                color = COLOR_BUTTON
                text_surf = self.font_small.render(text, True, color)
            elif line_type == "spacer":
                y += line_height // 2
                continue
            else:
                color = COLOR_TEXT
                text_surf = self.font_small.render(text, True, color)
            
            surf.blit(text_surf, (rect.x + 10, y))
            y += line_height
        
        if scroll > 0:
            up_surf = self.font_text.render("^", True, COLOR_BORDER)
            surf.blit(up_surf, (rect.right - 20, rect.y + 5))
        
        if scroll + max_lines < len(content):
            down_surf = self.font_text.render("v", True, COLOR_BORDER)
            surf.blit(down_surf, (rect.right - 20, rect.bottom - 18))
    
    def _draw_export_options(self, surf, rect):
        """Draw export options with toggle switches"""
        COLOR_BORDER = ui_colors.COLOR_BORDER
        COLOR_HIGHLIGHT = ui_colors.COLOR_HIGHLIGHT
        COLOR_TEXT = ui_colors.COLOR_TEXT
        COLOR_BUTTON = ui_colors.COLOR_BUTTON
        COLOR_BUTTON_HOVER = ui_colors.COLOR_BUTTON_HOVER
        COLOR_HEADER = ui_colors.COLOR_HEADER
        COLOR_SUCCESS = ui_colors.COLOR_SUCCESS
        COLOR_ERROR = ui_colors.COLOR_ERROR
        
        y = rect.y + 12
        
        info_surf = self.font_text.render("Export Options", True, COLOR_BORDER)
        surf.blit(info_surf, (rect.x + 15, y))
        y += 22
        
        option_height = 26
        for i, opt in enumerate(self.export_options):
            is_selected = (not self.tab_focus and self.selected_option == i)
            
            row_rect = pygame.Rect(rect.x + 8, y - 2, rect.width - 16, option_height)
            if is_selected:
                pygame.draw.rect(surf, COLOR_BUTTON, row_rect, border_radius=4)
                pygame.draw.rect(surf, COLOR_HIGHLIGHT, row_rect, 2, border_radius=4)
            
            text_color = COLOR_HIGHLIGHT if is_selected else COLOR_TEXT
            label_surf = self.font_text.render(opt["name"], True, text_color)
            surf.blit(label_surf, (rect.x + 15, y + 4))
            
            toggle_x = rect.right - 60
            toggle_rect = pygame.Rect(toggle_x, y + 3, 40, 18)
            pygame.draw.rect(surf, COLOR_HEADER, toggle_rect, border_radius=9)
            
            if opt["value"]:
                indicator_x = toggle_x + 22
                indicator_color = COLOR_SUCCESS
            else:
                indicator_x = toggle_x + 4
                indicator_color = COLOR_ERROR
            
            indicator_rect = pygame.Rect(indicator_x, y + 5, 14, 14)
            pygame.draw.rect(surf, indicator_color, indicator_rect, border_radius=7)
            
            y += option_height
        
        y += 10
        
        is_btn_selected = (not self.tab_focus and self.selected_option == len(self.export_options))
        
        btn_rect = pygame.Rect(rect.x + 20, y, rect.width - 40, 28)
        if is_btn_selected:
            pygame.draw.rect(surf, COLOR_BUTTON_HOVER, btn_rect, border_radius=5)
            pygame.draw.rect(surf, COLOR_SUCCESS, btn_rect, 2, border_radius=5)
            btn_color = COLOR_SUCCESS
        else:
            pygame.draw.rect(surf, COLOR_BUTTON, btn_rect, border_radius=5)
            pygame.draw.rect(surf, COLOR_BORDER, btn_rect, 1, border_radius=5)
            btn_color = COLOR_TEXT
        
        btn_surf = self.font_text.render("Export to JSON", True, btn_color)
        btn_text_rect = btn_surf.get_rect(center=btn_rect.center)
        surf.blit(btn_surf, btn_text_rect)
    
    def update(self, events):
        """Update method for compatibility"""
        return self.visible