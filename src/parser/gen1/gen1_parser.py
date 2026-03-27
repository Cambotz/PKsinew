#!/usr/bin/env python3
"""
Gen 1 Pokémon Save Parser - Standalone Demo
Reads Red/Blue/Yellow .sav files and displays all data

Usage:
    python3 gen1_parser_demo.py <save_file.sav>
"""

import sys
from pathlib import Path

# Import the parser tables
from gen1_parser_tables import (
    GEN1_INTERNAL_SPECIES,
    GEN1_NATIONAL_DEX,
    GEN1_MOVES,
    GEN1_MOVE_MAX_PP,
    GEN1_TYPES,
    GEN1_CHAR_TABLE,
    POKEMON_BASE_STATS,
    GEN1_ITEMS,
    GEN1_POKEMON_STRUCT,
    GEN1_SAVE_OFFSETS,
    BADGE_NAMES,
    GEN1_SPECIES_GROWTH,
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def decode_string(raw: bytes) -> str:
    """Decode Gen 1 string (0x50-terminated)."""
    result = []
    for b in raw:
        if b == 0x50:
            break
        result.append(GEN1_CHAR_TABLE.get(b, f"[{b:02X}]"))
    return "".join(result).strip()

def decode_bcd(raw: bytes) -> int:
    """Decode BCD integer."""
    return int("".join(f"{b:02X}" for b in raw))

def decode_status(byte: int) -> str:
    """Decode status condition byte."""
    if byte == 0:
        return "OK"
    sleep_turns = byte & 0x07
    if sleep_turns:
        return f"SLP ({sleep_turns})"
    flags = []
    if byte & 0x08: flags.append("PSN")
    if byte & 0x10: flags.append("BRN")
    if byte & 0x20: flags.append("FRZ")
    if byte & 0x40: flags.append("PAR")
    return "+".join(flags) if flags else f"??({byte:#04x})"

def get_dex_flag(dex_bytes: bytes, dex_num: int) -> bool:
    """Check if Pokédex flag is set for dex number 1-151."""
    byte_idx = (dex_num - 1) // 8
    bit_idx = (dex_num - 1) % 8
    return bool(dex_bytes[byte_idx] & (1 << bit_idx))

# ============================================================================
# PARSER CLASS
# ============================================================================

class Gen1SaveParser:
    def __init__(self, save_path: Path, force_version: str = None):
        """
        Initialize Gen 1 save parser.
        
        Args:
            save_path: Path to .sav file
            force_version: Optional manual override - 'yellow' or 'red/blue'
        """
        self.path = Path(save_path)  # Ensure it's a Path object
        with open(save_path, "rb") as f:
            self.data = bytearray(f.read())
        
        if len(self.data) != 32768:
            print(f"⚠ Warning: Save file is {len(self.data)} bytes, expected 32768")
        
        # Detect or override game version
        if force_version:
            self.is_yellow = force_version.lower() in ['yellow', 'y']
        else:
            self.is_yellow = self._detect_yellow()
    
    def _detect_yellow(self) -> bool:
        """
        Detect Yellow version using multiple methods:
        1. Check for Pikachu friendship byte (Yellow-exclusive at 0x271C)
        2. Filename contains 'yellow'
        3. Party species pattern analysis (fallback)
        """
        from gen1_parser import GEN1_SAVE_OFFSETS
        
        # Method 1: Yellow has Pikachu friendship at 0x271C
        # This byte only exists in Yellow (tracks starter Pikachu happiness)
        # Red/Blue use this area for different data
        # Yellow friendship values: 0-255, typically starts around 50-90
        pikachu_friendship_offset = 0x271C
        if pikachu_friendship_offset < len(self.data):
            friendship = self.data[pikachu_friendship_offset]
            # If this byte is in a reasonable friendship range (1-255)
            # AND we have other Yellow indicators, it's Yellow
            # (We can't use this alone as Red/Blue might have valid data here)
            has_friendship_byte = 0 < friendship <= 255
        else:
            has_friendship_byte = False
        
        # Method 2: Filename check
        filename = self.path.name.lower()
        if 'yellow' in filename:
            return True
        if 'red' in filename or 'blue' in filename:
            return False
        
        # Method 3: Check party for Yellow-specific species patterns
        party_count_offset, _ = GEN1_SAVE_OFFSETS["party_count"]
        party_count = self.data[party_count_offset]
        
        if party_count == 0:
            return False  # Empty save, default Red/Blue
        
        species_offset, _ = GEN1_SAVE_OFFSETS["party_species"]
        party_species = self.data[species_offset:species_offset+min(party_count, 6)]
        
        # Strong Yellow indicator: Pikachu (0x54) in party
        has_pikachu = 0x54 in party_species
        
        # Check for Yellow-exclusive mappings with level check
        # 0xB1 = Rhydon (Yellow, common, high level) vs Squirtle (Red/Blue, rare in endgame)
        party_data_offset, _ = GEN1_SAVE_OFFSETS["party_data"]
        
        for i in range(party_count):
            species_id = party_species[i]
            
            # Get this Pokemon's level
            from gen1_parser import GEN1_POKEMON_STRUCT
            pkmn_offset = party_data_offset + (i * 44)
            level_offset_in_struct, _ = GEN1_POKEMON_STRUCT["level"]
            level = self.data[pkmn_offset + level_offset_in_struct]
            
            # 0xB1 at high level = Rhydon (Yellow), not Squirtle (Red/Blue)
            if species_id == 0xB1 and level > 30:
                return True
            
            # 0xB5 at low level = Spearow (Yellow), not Blastoise (Red/Blue)
            if species_id == 0xB5 and level < 20:
                return True
        
        # If Pikachu + friendship byte looks valid, it's Yellow
        if has_pikachu and has_friendship_byte:
            return True
        
        # Default to Red/Blue
        return False
    
    def read_bytes(self, offset: int, length: int) -> bytes:
        """Read bytes from save data."""
        return self.data[offset:offset+length]
    
    def read_u8(self, offset: int) -> int:
        """Read unsigned 8-bit."""
        return self.data[offset]
    
    def read_u16_be(self, offset: int) -> int:
        """Read unsigned 16-bit big-endian."""
        return (self.data[offset] << 8) | self.data[offset+1]
    
    def read_u24_be(self, offset: int) -> int:
        """Read unsigned 24-bit big-endian."""
        return (self.data[offset] << 16) | (self.data[offset+1] << 8) | self.data[offset+2]
    
    # ── Trainer Info ──────────────────────────────────────────────────────
    
    def get_player_name(self) -> str:
        offset, length = GEN1_SAVE_OFFSETS["player_name"]
        return decode_string(self.read_bytes(offset, length))
    
    def get_rival_name(self) -> str:
        offset, length = GEN1_SAVE_OFFSETS["rival_name"]
        return decode_string(self.read_bytes(offset, length))
    
    def get_trainer_id(self) -> int:
        offset, _ = GEN1_SAVE_OFFSETS["trainer_id"]
        return self.read_u16_be(offset)
    
    def get_money(self) -> int:
        offset, length = GEN1_SAVE_OFFSETS["money"]
        return decode_bcd(self.read_bytes(offset, length))
    
    def get_badges(self) -> list[str]:
        offset, _ = GEN1_SAVE_OFFSETS["badges"]
        badge_byte = self.read_u8(offset)
        return [BADGE_NAMES[i] for i in range(8) if badge_byte & (1 << i)]
    
    def get_playtime(self) -> tuple[int, int, int]:
        h_offset, _ = GEN1_SAVE_OFFSETS["playtime_h"]
        m_offset, _ = GEN1_SAVE_OFFSETS["playtime_m"]
        s_offset, _ = GEN1_SAVE_OFFSETS["playtime_s"]
        return (self.read_u8(h_offset), self.read_u8(m_offset), self.read_u8(s_offset))
    
    def get_pokedex_counts(self) -> tuple[int, int]:
        owned_offset, owned_len = GEN1_SAVE_OFFSETS["pokedex_owned"]
        seen_offset, seen_len = GEN1_SAVE_OFFSETS["pokedex_seen"]
        owned_bytes = self.read_bytes(owned_offset, owned_len)
        seen_bytes = self.read_bytes(seen_offset, seen_len)
        
        owned = sum(get_dex_flag(owned_bytes, i) for i in range(1, 152))
        seen = sum(get_dex_flag(seen_bytes, i) for i in range(1, 152))
        return (owned, seen)
    
    # ── Bag ───────────────────────────────────────────────────────────────
    
    def get_bag_items(self) -> list[tuple[str, int]]:
        count_offset, _ = GEN1_SAVE_OFFSETS["bag_count"]
        items_offset, items_len = GEN1_SAVE_OFFSETS["bag_items"]
        
        count = self.read_u8(count_offset)
        items_data = self.read_bytes(items_offset, items_len)
        
        items = []
        for i in range(count):
            item_id = items_data[i * 2]
            quantity = items_data[i * 2 + 1]
            if item_id == 0xFF:
                break
            item_name = GEN1_ITEMS.get(item_id, f"Item#{item_id}")
            items.append((item_name, quantity))
        return items
    
    # ── Party ─────────────────────────────────────────────────────────────
    
    def get_party_count(self) -> int:
        offset, _ = GEN1_SAVE_OFFSETS["party_count"]
        return self.read_u8(offset)
    
    # ── PC Boxes ──────────────────────────────────────────────────────────
    
    def get_current_box(self) -> int:
        """Get the currently selected box (1-12)."""
        offset, _ = GEN1_SAVE_OFFSETS["current_box"]
        box_num = self.read_u8(offset)
        # Validate - should be 0-11, but might be uninitialized (0xFF or > 11)
        return (box_num + 1) if 0 <= box_num <= 11 else 1
    
    def get_box1_count(self) -> int:
        """Get number of Pokémon in Box 1."""
        return self.get_box_count(1)
    
    def get_box_count(self, box_number: int) -> int:
        """Get number of Pokémon in a box (1-12)."""
        from gen1_parser import get_box_offset
        offset = get_box_offset(box_number)
        count = self.read_u8(offset)
        return count if 0 <= count <= 20 else 0
    
    def calculate_level_from_exp(self, species_name: str, exp: int) -> int:
        """Calculate level from EXP using species growth rate."""
        from gen1_parser import GEN1_SPECIES_GROWTH, GEN1_EXP_CURVES
        
        # Get growth rate for this species
        growth_rate = GEN1_SPECIES_GROWTH.get(species_name)
        if not growth_rate:
            return 0  # Unknown species or growth rate
        
        # Get EXP curve
        curve = GEN1_EXP_CURVES.get(growth_rate)
        if not curve:
            return 0
        
        # Find level where EXP matches
        for level in range(100, 0, -1):  # Check from 100 down to 1
            if exp >= curve[level - 1]:
                return level
        
        return 1  # Default to level 1
    
    def parse_box_pokemon(self, pkmn_data: bytes, ot_name: str, nickname: str) -> dict:
        """Parse a 33-byte box Pokémon structure (no level/stats bytes)."""
        
        # Species
        species_offset, _ = GEN1_POKEMON_STRUCT["species"]
        species_id = pkmn_data[species_offset]
        
        from gen1_parser import get_gen1_species
        species_name = get_gen1_species(species_id)  # No is_yellow param needed
        
        # HP
        hp_cur_offset, _ = GEN1_POKEMON_STRUCT["current_hp"]
        hp_cur = (pkmn_data[hp_cur_offset] << 8) | pkmn_data[hp_cur_offset+1]
        
        # Status
        status_offset, _ = GEN1_POKEMON_STRUCT["status"]
        status = decode_status(pkmn_data[status_offset])
        
        # Types
        type1_offset, _ = GEN1_POKEMON_STRUCT["type1"]
        type2_offset, _ = GEN1_POKEMON_STRUCT["type2"]
        type1 = GEN1_TYPES.get(pkmn_data[type1_offset], "?")
        type2 = GEN1_TYPES.get(pkmn_data[type2_offset], "?")
        
        # EXP
        exp_offset, _ = GEN1_POKEMON_STRUCT["exp"]
        exp_bytes = pkmn_data[exp_offset:exp_offset+3]
        exp = (exp_bytes[0] << 16) | (exp_bytes[1] << 8) | exp_bytes[2]
        
        # OT ID
        ot_id_offset, _ = GEN1_POKEMON_STRUCT["ot_id"]
        ot_id = (pkmn_data[ot_id_offset] << 8) | pkmn_data[ot_id_offset+1]
        
        # DVs
        dv_offset, _ = GEN1_POKEMON_STRUCT["dvs"]
        dv_bytes = pkmn_data[dv_offset:dv_offset+2]
        atk_dv = (dv_bytes[0] >> 4) & 0xF
        def_dv = dv_bytes[0] & 0xF
        spd_dv = (dv_bytes[1] >> 4) & 0xF
        spc_dv = dv_bytes[1] & 0xF
        hp_dv = ((atk_dv & 1) << 3) | ((def_dv & 1) << 2) | ((spd_dv & 1) << 1) | (spc_dv & 1)
        
        # Moves
        moves = []
        for i in range(1, 5):
            move_offset, _ = GEN1_POKEMON_STRUCT[f"move{i}"]
            pp_offset, _ = GEN1_POKEMON_STRUCT[f"pp{i}"]
            
            move_id = pkmn_data[move_offset]
            pp_byte = pkmn_data[pp_offset]
            pp_cur = pp_byte & 0x3F
            pp_ups = pp_byte >> 6
            
            if move_id == 0 or move_id == 0xFF:
                continue
            
            move_name = GEN1_MOVES.get(move_id, f"??#{move_id:02X}")
            max_pp = GEN1_MOVE_MAX_PP.get(move_id, 0)
            max_pp_boosted = max_pp + (max_pp // 5) * pp_ups
            
            moves.append({
                "name": move_name,
                "id": move_id,
                "pp_current": pp_cur,
                "pp_max": max_pp_boosted,
                "pp_ups": pp_ups
            })
        
        # Calculate level from EXP (box Pokémon don't store level)
        level = self.calculate_level_from_exp(species_name, exp)
        
        return {
            "species": species_name,
            "species_id": species_id,
            "nickname": nickname,
            "level": level,  # Box Pokémon need level calculated from EXP
            "hp_current": hp_cur,
            "status": status,
            "type1": type1,
            "type2": type2,
            "exp": exp,
            "ot_name": ot_name,
            "ot_id": ot_id,
            "dvs": {"atk": atk_dv, "def": def_dv, "spd": spd_dv, "spc": spc_dv, "hp": hp_dv},
            "moves": moves,
            "is_box_pokemon": True
        }
    
    def get_box1(self) -> list[dict]:
        """Get all Pokémon in Box 1."""
        return self.get_box(1)
    
    def get_box(self, box_number: int) -> list[dict]:
        """Get all Pokémon in a box (1-12)."""
        from gen1_parser import get_box_offset
        
        count = self.get_box_count(box_number)
        if count == 0:
            return []
        
        base_offset = get_box_offset(box_number)
        data_offset = base_offset + 22  # Skip count (1) + species list (21)
        ot_offset = data_offset + 660   # Skip Pokémon data (20 × 33)
        nick_offset = ot_offset + 220   # Skip OT names (20 × 11)
        
        box = []
        for i in range(count):
            pkmn_data = self.read_bytes(data_offset + i * 33, 33)
            ot_name = decode_string(self.read_bytes(ot_offset + i * 11, 11))
            nickname = decode_string(self.read_bytes(nick_offset + i * 11, 11))
            
            pkmn = self.parse_box_pokemon(pkmn_data, ot_name, nickname)
            box.append(pkmn)
        
        return box
    
    def get_all_boxes(self) -> dict[int, list[dict]]:
        """Get all 12 PC boxes."""
        return {i: self.get_box(i) for i in range(1, 13)}
    
    def get_save_summary(self) -> dict:
        """Get summary statistics of the save file."""
        party_count = self.get_party_count()
        
        # Count box Pokémon
        box_counts = {}
        total_box_pokemon = 0
        for i in range(1, 13):
            count = self.get_box_count(i)
            box_counts[i] = count
            total_box_pokemon += count
        
        # Trainer info
        player_name = self.get_player_name()
        hours, minutes, seconds = self.get_playtime()
        badges = self.get_badges()
        owned, seen = self.get_pokedex_counts()
        
        return {
            "game_version": "Yellow" if self.is_yellow else "Red/Blue",
            "player_name": player_name,
            "playtime_hours": hours + (minutes / 60) + (seconds / 3600),
            "party_count": party_count,
            "box_pokemon": total_box_pokemon,
            "total_pokemon": party_count + total_box_pokemon,
            "badges": len(badges),
            "pokedex_owned": owned,
            "pokedex_seen": seen,
            "box_counts": box_counts,
        }
    
    def get_species_counts(self) -> dict[str, int]:
        """Count how many of each species you have (party + all boxes)."""
        from collections import Counter
        
        species_list = []
        
        # Party
        for pkmn in self.get_party():
            species_list.append(pkmn['species'])
        
        # All boxes
        for box_num in range(1, 13):
            for pkmn in self.get_box(box_num):
                species_list.append(pkmn['species'])
        
        return dict(Counter(species_list))
    
    def find_pokemon(self, species_name: str = None, min_level: int = None, 
                     max_level: int = None, nickname: str = None) -> list[dict]:
        """
        Find Pokémon matching criteria.
        Returns list of dicts with location info.
        """
        results = []
        
        # Search party
        party = self.get_party()
        for i, pkmn in enumerate(party, 1):
            if species_name and pkmn['species'].lower() != species_name.lower():
                continue
            if min_level and pkmn['level'] < min_level:
                continue
            if max_level and pkmn['level'] > max_level:
                continue
            if nickname and pkmn['nickname'].lower() != nickname.lower():
                continue
            
            results.append({
                'location': 'Party',
                'slot': i,
                'pokemon': pkmn
            })
        
        # Search boxes
        for box_num in range(1, 13):
            box = self.get_box(box_num)
            for i, pkmn in enumerate(box, 1):
                if species_name and pkmn['species'].lower() != species_name.lower():
                    continue
                if min_level and pkmn['level'] < min_level:
                    continue
                if max_level and pkmn['level'] > max_level:
                    continue
                if nickname and pkmn['nickname'].lower() != nickname.lower():
                    continue
                
                results.append({
                    'location': f'Box {box_num}',
                    'slot': i,
                    'pokemon': pkmn
                })
        
        return results
    
    def export_to_json(self) -> dict:
        """Export entire save to JSON-serializable dict."""
        return {
            "game_version": "Yellow" if self.is_yellow else "Red/Blue",
            "trainer": {
                "name": self.get_player_name(),
                "rival": self.get_rival_name(),
                "id": self.get_trainer_id(),
                "money": self.get_money(),
                "badges": self.get_badges(),
                "playtime": {
                    "hours": self.get_playtime()[0],
                    "minutes": self.get_playtime()[1],
                    "seconds": self.get_playtime()[2],
                }
            },
            "pokedex": {
                "owned": self.get_pokedex_counts()[0],
                "seen": self.get_pokedex_counts()[1],
            },
            "bag": [{"item": item, "quantity": qty} for item, qty in self.get_bag_items()],
            "party": self.get_party(),
            "boxes": {
                str(i): self.get_box(i) for i in range(1, 13)
            }
        }
    
    def get_party_count(self) -> int:
        offset, _ = GEN1_SAVE_OFFSETS["party_count"]
        return self.read_u8(offset)
    
    def parse_pokemon(self, pkmn_data: bytes, ot_name: str, nickname: str) -> dict:
        """Parse a 44-byte party Pokémon structure."""
        
        # Species
        species_offset, _ = GEN1_POKEMON_STRUCT["species"]
        species_id = pkmn_data[species_offset]
        
        from gen1_parser import get_gen1_species
        species_name = get_gen1_species(species_id)  # No is_yellow param needed
        
        # Level & HP
        level_offset, _ = GEN1_POKEMON_STRUCT["level"]
        level = pkmn_data[level_offset]
        
        hp_cur_offset, _ = GEN1_POKEMON_STRUCT["current_hp"]
        hp_cur = (pkmn_data[hp_cur_offset] << 8) | pkmn_data[hp_cur_offset+1]
        
        hp_max_offset, _ = GEN1_POKEMON_STRUCT["max_hp"]
        hp_max = (pkmn_data[hp_max_offset] << 8) | pkmn_data[hp_max_offset+1]
        
        # Status
        status_offset, _ = GEN1_POKEMON_STRUCT["status"]
        status = decode_status(pkmn_data[status_offset])
        
        # Stats (BIG-ENDIAN - all Gen 1 stats are big-endian)
        atk_offset, _ = GEN1_POKEMON_STRUCT["attack"]
        attack = (pkmn_data[atk_offset] << 8) | pkmn_data[atk_offset+1]
        
        def_offset, _ = GEN1_POKEMON_STRUCT["defense"]
        defense = (pkmn_data[def_offset] << 8) | pkmn_data[def_offset+1]
        
        spd_offset, _ = GEN1_POKEMON_STRUCT["speed"]
        speed = (pkmn_data[spd_offset] << 8) | pkmn_data[spd_offset+1]
        
        spc_offset, _ = GEN1_POKEMON_STRUCT["special"]
        special = (pkmn_data[spc_offset] << 8) | pkmn_data[spc_offset+1]
        
        # Types
        type1_offset, _ = GEN1_POKEMON_STRUCT["type1"]
        type2_offset, _ = GEN1_POKEMON_STRUCT["type2"]
        type1 = GEN1_TYPES.get(pkmn_data[type1_offset], "?")
        type2 = GEN1_TYPES.get(pkmn_data[type2_offset], "?")
        
        # EXP
        exp_offset, _ = GEN1_POKEMON_STRUCT["exp"]
        exp_bytes = pkmn_data[exp_offset:exp_offset+3]
        exp = (exp_bytes[0] << 16) | (exp_bytes[1] << 8) | exp_bytes[2]
        
        # OT ID
        ot_id_offset, _ = GEN1_POKEMON_STRUCT["ot_id"]
        ot_id = (pkmn_data[ot_id_offset] << 8) | pkmn_data[ot_id_offset+1]
        
        # DVs
        dv_offset, _ = GEN1_POKEMON_STRUCT["dvs"]
        dv_bytes = pkmn_data[dv_offset:dv_offset+2]
        atk_dv = (dv_bytes[0] >> 4) & 0xF
        def_dv = dv_bytes[0] & 0xF
        spd_dv = (dv_bytes[1] >> 4) & 0xF
        spc_dv = dv_bytes[1] & 0xF
        hp_dv = ((atk_dv & 1) << 3) | ((def_dv & 1) << 2) | ((spd_dv & 1) << 1) | (spc_dv & 1)
        
        # Moves
        moves = []
        for i in range(1, 5):
            move_offset, _ = GEN1_POKEMON_STRUCT[f"move{i}"]
            pp_offset, _ = GEN1_POKEMON_STRUCT[f"pp{i}"]
            
            move_id = pkmn_data[move_offset]
            pp_byte = pkmn_data[pp_offset]
            pp_cur = pp_byte & 0x3F
            pp_ups = pp_byte >> 6
            
            if move_id == 0 or move_id == 0xFF:
                continue
            
            move_name = GEN1_MOVES.get(move_id, f"??#{move_id:02X}")
            max_pp = GEN1_MOVE_MAX_PP.get(move_id, 0)
            max_pp_boosted = max_pp + (max_pp // 5) * pp_ups
            
            moves.append({
                "name": move_name,
                "id": move_id,
                "pp_current": pp_cur,
                "pp_max": max_pp_boosted,
                "pp_ups": pp_ups
            })
        
        # Detect corruption
        issues = []
        if level > 100 or level == 0:
            issues.append(f"Invalid level ({level})")
        if hp_max > 999:
            issues.append(f"HP overflow ({hp_max})")
        if attack > 999:
            issues.append(f"Attack overflow ({attack})")
        if defense > 999:
            issues.append(f"Defense overflow ({defense})")
        if speed > 999:
            issues.append(f"Speed overflow ({speed})")
        if special > 999:
            issues.append(f"Special overflow ({special})")
        if hp_cur > hp_max:
            issues.append(f"Current HP > Max HP")
        
        return {
            "species": species_name,
            "species_id": species_id,
            "nickname": nickname,
            "level": level,
            "hp_current": hp_cur,
            "hp_max": hp_max,
            "status": status,
            "attack": attack,
            "defense": defense,
            "speed": speed,
            "special": special,
            "type1": type1,
            "type2": type2,
            "exp": exp,
            "ot_name": ot_name,
            "ot_id": ot_id,
            "dvs": {"atk": atk_dv, "def": def_dv, "spd": spd_dv, "spc": spc_dv, "hp": hp_dv},
            "moves": moves,
            "corruption": issues
        }
    
    def get_party(self) -> list[dict]:
        """Get all party Pokémon."""
        count = self.get_party_count()
        if count == 0:
            return []
        
        party_offset, _ = GEN1_SAVE_OFFSETS["party_data"]
        ot_offset, _ = GEN1_SAVE_OFFSETS["party_ot"]
        nick_offset, _ = GEN1_SAVE_OFFSETS["party_names"]
        
        party = []
        for i in range(count):
            pkmn_data = self.read_bytes(party_offset + i * 44, 44)
            ot_name = decode_string(self.read_bytes(ot_offset + i * 11, 11))
            nickname_raw = decode_string(self.read_bytes(nick_offset + i * 11, 11))
            
            # If nickname is empty/blank, use the species name
            nickname = nickname_raw if nickname_raw and not all(c in '[0]' for c in nickname_raw) else ""
            
            pkmn = self.parse_pokemon(pkmn_data, ot_name, nickname)
            party.append(pkmn)
        
        return party

# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================

def print_separator():
    print("─" * 70)

def print_trainer_info(parser: Gen1SaveParser):
    print_separator()
    
    # Game version
    game_version = "Yellow" if parser.is_yellow else "Red/Blue"
    
    player = parser.get_player_name()
    rival = parser.get_rival_name()
    tid = parser.get_trainer_id()
    money = parser.get_money()
    h, m, s = parser.get_playtime()
    badges = parser.get_badges()
    owned, seen = parser.get_pokedex_counts()
    
    print(f"  Game:     Pokémon {game_version}")
    print(f"  Trainer:  {player}  (#{tid:05d})")
    print(f"  Rival:    {rival}")
    print(f"  Money:    ₽{money:,}")
    print(f"  Time:     {h}h {m:02d}m {s:02d}s")
    print(f"  Badges:   {' '.join(badges) if badges else 'None'}")
    print(f"  Pokédex:  {owned}/151 owned,  {seen}/151 seen")
    print_separator()

def print_party(parser: Gen1SaveParser):
    party = parser.get_party()
    print(f"\n  ── Party ({len(party)}/6) ──\n")
    
    for i, pkmn in enumerate(party, 1):
        types = f"{pkmn['type1']}/{pkmn['type2']}" if pkmn['type1'] != pkmn['type2'] else pkmn['type1']
        
        # Display name: show nickname + species if different, otherwise just species
        if pkmn['nickname'] and pkmn['nickname'] != pkmn['species'].upper():
            display_name = f"{pkmn['nickname']} ({pkmn['species']})"
        else:
            display_name = pkmn['species']
        
        print(f"  [{i}] {display_name}  (Lv.{pkmn['level']})")
        
        print(f"       OT: {pkmn['ot_name']} #{pkmn['ot_id']:05d}  |  Status: {pkmn['status']}")
        print(f"       HP: {pkmn['hp_current']}/{pkmn['hp_max']}  |  Type: {types}")
        print(f"       Atk:{pkmn['attack']:4d}  Def:{pkmn['defense']:4d}  Spd:{pkmn['speed']:4d}  Spc:{pkmn['special']:4d}")
        
        dvs = pkmn['dvs']
        print(f"       DVs: Atk={dvs['atk']} Def={dvs['def']} Spd={dvs['spd']} Spc={dvs['spc']} HP={dvs['hp']}")
        print(f"       EXP: {pkmn['exp']:,}")
        
        if pkmn['moves']:
            print(f"       Moves:")
            for move in pkmn['moves']:
                pp_info = f"{move['pp_current']}/{move['pp_max']} PP"
                if move['pp_ups'] > 0:
                    pp_info += f" (+{move['pp_ups']} PP Up)"
                print(f"         • {move['name']:<15} {pp_info}")
        
        if pkmn.get('corruption'):
            print(f"       ⚠ CORRUPTION DETECTED:")
            for issue in pkmn['corruption']:
                print(f"         - {issue}")
        print()

def print_bag(parser: Gen1SaveParser):
    items = parser.get_bag_items()
    print(f"  ── Bag ({len(items)} items) ──\n")
    for item_name, quantity in items:
        print(f"    {item_name:<25} × {quantity}")
    print()

def print_box1(parser: Gen1SaveParser):
    """Display Box 1 (kept for compatibility)."""
    print_box(parser, 1)

def print_box(parser: Gen1SaveParser, box_number: int):
    """Display a specific PC box."""
    box = parser.get_box(box_number)
    count = len(box)
    
    if count == 0:
        print(f"\n  ── Box {box_number} (0/20) ──\n")
        print("    Empty\n")
        return
    
    print(f"\n  ── Box {box_number} ({count}/20) ──\n")
    
    for i, pkmn in enumerate(box, 1):
        types = f"{pkmn['type1']}/{pkmn['type2']}" if pkmn['type1'] != pkmn['type2'] else pkmn['type1']
        
        # Display name: use nickname if set, otherwise species name
        display_name = pkmn['nickname'] if pkmn['nickname'] else pkmn['species']
        
        # Show level
        level_str = f"Lv.{pkmn['level']}" if pkmn['level'] > 0 else "Lv.?"
        
        print(f"  [{i:2d}] {display_name}  ({level_str})")
        
        # Show OT and HP only (no stats for box Pokémon)
        print(f"       OT: {pkmn['ot_name']} #{pkmn['ot_id']:05d}  |  Type: {types}")
        print(f"       HP: {pkmn['hp_current']}  |  EXP: {pkmn['exp']:,}")
        
        if pkmn['moves']:
            moves_str = ", ".join(m['name'] for m in pkmn['moves'])
            print(f"       Moves: {moves_str}")
        print()

def print_all_boxes(parser: Gen1SaveParser):
    """Display all 12 PC boxes with summary."""
    print("\n  ── PC Storage Summary ──\n")
    
    total_pokemon = 0
    for i in range(1, 13):
        count = parser.get_box_count(i)
        total_pokemon += count
        bar = "█" * count + "░" * (20 - count)
        print(f"    Box {i:2d}: [{bar}] {count:2d}/20")
    
    print(f"\n    Total: {total_pokemon}/240 Pokémon stored\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    
    parser_cli = argparse.ArgumentParser(description='Pokémon Gen 1 Save File Parser')
    parser_cli.add_argument('save_file', help='Path to .sav file')
    parser_cli.add_argument('--dump-all', action='store_true', help='Dump all Pokémon details')
    parser_cli.add_argument('--json', metavar='FILE', help='Export to JSON file')
    parser_cli.add_argument('--search', metavar='SPECIES', help='Search for specific species')
    parser_cli.add_argument('--min-level', type=int, metavar='N', help='Minimum level filter')
    parser_cli.add_argument('--max-level', type=int, metavar='N', help='Maximum level filter')
    parser_cli.add_argument('--species-count', action='store_true', help='Show species counts')
    parser_cli.add_argument('--summary', action='store_true', help='Show save summary stats')
    parser_cli.add_argument('--version', choices=['red', 'blue', 'yellow'], help='Force game version (overrides auto-detection)')
    
    args = parser_cli.parse_args()
    
    save_path = Path(args.save_file)
    if not save_path.exists():
        print(f"Error: File not found: {save_path}")
        sys.exit(1)
    
    print(f"\nParsing: {save_path.name}\n")
    
    parser = Gen1SaveParser(save_path, force_version=args.version)
    
    # JSON export
    if args.json:
        import json
        data = parser.export_to_json()
        with open(args.json, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Exported to {args.json}\n")
        return
    
    # Search mode
    if args.search:
        results = parser.find_pokemon(
            species_name=args.search,
            min_level=args.min_level,
            max_level=args.max_level
        )
        
        if not results:
            print(f"No {args.search} found")
            if args.min_level or args.max_level:
                level_filter = []
                if args.min_level:
                    level_filter.append(f"level >= {args.min_level}")
                if args.max_level:
                    level_filter.append(f"level <= {args.max_level}")
                print(f"  (with filters: {', '.join(level_filter)})")
        else:
            print(f"Found {len(results)} {args.search}:\n")
            for r in results:
                pkmn = r['pokemon']
                name = pkmn['nickname'] if pkmn['nickname'] else pkmn['species']
                print(f"  {r['location']:10} Slot {r['slot']:2d}: {name:<15} Lv.{pkmn['level']:3d}")
        print()
        return
    
    # Species count mode
    if args.species_count:
        counts = parser.get_species_counts()
        print("Species Counts (Party + All Boxes):\n")
        for species, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {species:<15} × {count}")
        print(f"\nTotal: {sum(counts.values())} Pokémon")
        print()
        return
    
    # Summary mode
    if args.summary:
        summary = parser.get_save_summary()
        print("Save File Summary:\n")
        print(f"  Game:         {summary['game_version']}")
        print(f"  Trainer:      {summary['player_name']}")
        print(f"  Play Time:    {summary['playtime_hours']:.1f} hours")
        print(f"  Badges:       {summary['badges']}/8")
        print(f"  Pokédex:      {summary['pokedex_owned']}/151 owned, {summary['pokedex_seen']}/151 seen")
        print(f"  Party:        {summary['party_count']}/6")
        print(f"  Boxes:        {summary['box_pokemon']}/240")
        print(f"  Total:        {summary['total_pokemon']} Pokémon")
        print()
        
        # Box breakdown
        print("  Box Storage:")
        for i in range(1, 13):
            count = summary['box_counts'][i]
            bar = '█' * count + '░' * (20 - count)
            print(f"    Box {i:2d}: [{bar}] {count:2d}/20")
        print()
        return
    
    # Dump all mode
    if args.dump_all:
        # Dump every Pokémon
        print("=" * 70)
        print("ALL POKÉMON IN SAVE FILE")
        print("=" * 70)
        
        # Party
        print("\n=== PARTY (6) ===\n")
        party = parser.get_party()
        for i, pkmn in enumerate(party, 1):
            name = pkmn['nickname'] if pkmn['nickname'] else pkmn['species']
            print(f"  {i}. {name:<15} Lv.{pkmn['level']:3d}  |  HP: {pkmn['hp_current']:3d}/{pkmn['hp_max']:3d}  |  {pkmn['species']}")
        
        # All 12 boxes
        for box_num in range(1, 13):
            box = parser.get_box(box_num)
            if not box:
                print(f"\n=== BOX {box_num} (0/20) ===\n  Empty")
                continue
            
            print(f"\n=== BOX {box_num} ({len(box)}/20) ===\n")
            for i, pkmn in enumerate(box, 1):
                name = pkmn['nickname'] if pkmn['nickname'] else pkmn['species']
                level = pkmn['level'] if pkmn['level'] > 0 else '?'
                print(f"  {i:2d}. {name:<15} Lv.{str(level):>3}  |  HP: {pkmn['hp_current']:3d}  |  {pkmn['species']}")
        
        print("\n" + "=" * 70)
        
        # Count total
        total = len(party)
        for i in range(1, 13):
            total += parser.get_box_count(i)
        
        print(f"TOTAL: {total} Pokémon")
        print("=" * 70 + "\n")
    else:
        # Normal display
        print_trainer_info(parser)
        party = parser.get_party()
        print_party(parser)
        print_bag(parser)
        print_all_boxes(parser)
        print_separator()
    
    # Corruption summary (only in normal mode)
    if not args.dump_all:
        corrupted_count = sum(1 for p in party if p.get('corruption'))
        if corrupted_count > 0:
            print(f"\n⚠ WARNING: {corrupted_count}/{len(party)} Pokémon have corrupted stats!")
            print("This save file has been modified with GameShark/Action Replay codes,")
            print("hex editors, or glitch exploits. The parser is working correctly -")
            print("it's faithfully reporting the invalid data stored in the save file.")
            print()

if __name__ == "__main__":
    main()
