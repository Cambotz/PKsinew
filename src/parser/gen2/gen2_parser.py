#!/usr/bin/env python3
"""
Pokemon Gen 2 (Gold/Silver/Crystal) Save File Parser

Parses .sav files from Pokemon Gold, Silver, and Crystal versions.
Supports party, all 14 PC boxes, trainer info, and full Pokemon data.
"""

import sys
import argparse
from pathlib import Path
from gen2_parser_tables import *

class Gen2SaveParser:
    def __init__(self, save_path: Path, force_version: str = None):
        """
        Initialize Gen 2 save parser.
        
        Args:
            save_path: Path to .sav file
            force_version: Optional manual override - 'gold', 'silver', or 'crystal'
        """
        self.path = Path(save_path)
        with open(save_path, "rb") as f:
            self.data = bytearray(f.read())
        
        if len(self.data) != 32816:
            print(f"⚠ Warning: Save file is {len(self.data)} bytes, expected 32816")
        
        # Detect or override game version
        if force_version:
            self.version = force_version.lower()
        else:
            self.version = self._detect_version()
    
        
        # Use Crystal-specific offsets if Crystal, otherwise use Gold/Silver offsets
        if self.version == 'crystal':
            self.offsets = GEN2_CRYSTAL_OFFSETS
        else:
            self.offsets = GEN2_SAVE_OFFSETS
    def _detect_version(self) -> str:
        """Detect Gold/Silver/Crystal from filename."""
        filename = self.path.name.lower()
        if 'crystal' in filename:
            return 'crystal'
        elif 'silver' in filename:
            return 'silver'
        elif 'gold' in filename:
            return 'gold'
        return 'gold'
    
    @property
    def is_crystal(self) -> bool:
        """Check if this is a Crystal save."""
        return self.version == 'crystal'
    
    # ── Reading Functions ─────────────────────────────────────────────────────
    
    def read_u8(self, offset: int) -> int:
        """Read unsigned 8-bit."""
        return self.data[offset]
    
    def read_u16_be(self, offset: int) -> int:
        """Read unsigned 16-bit big-endian."""
        return (self.data[offset] << 8) | self.data[offset + 1]
    
    def read_u24_be(self, offset: int) -> int:
        """Read unsigned 24-bit big-endian."""
        return (self.data[offset] << 16) | (self.data[offset + 1] << 8) | self.data[offset + 2]
    
    def read_string(self, offset: int, length: int) -> str:
        """Read Gen 2 string (uses same encoding as Gen 1)."""
        result = []
        for i in range(length):
            byte = self.data[offset + i]
            if byte == 0x50:
                break
            char = GEN2_CHAR_TABLE.get(byte, f'[{byte:02X}]')
            result.append(char)
        return ''.join(result)
    
    # ── Trainer Info ──────────────────────────────────────────────────────────
    
    def get_player_name(self) -> str:
        """Get player name."""
        offset, length = self.offsets["player_name"]
        return self.read_string(offset, length)
    
    def get_rival_name(self) -> str:
        """Get rival name."""
        offset, length = self.offsets["rival_name"]
        return self.read_string(offset, length)
    
    def get_trainer_id(self) -> int:
        """Get trainer ID."""
        offset, _ = self.offsets["player_id"]
        return self.read_u16_be(offset)
    
    def get_money(self) -> int:
        """Get money (BCD encoded)."""
        offset, _ = self.offsets["money"]
        bcd = self.data[offset:offset+3]
        return int(f"{bcd[0]:02d}{bcd[1]:02d}{bcd[2]:02d}")
    
    def get_playtime(self) -> tuple[int, int, int]:
        """Get playtime as (hours, minutes, seconds)."""
        h_offset, _ = self.offsets["playtime_h"]
        m_offset, _ = self.offsets["playtime_m"]
        s_offset, _ = self.offsets["playtime_s"]
        
        hours = self.read_u16_be(h_offset)
        minutes = self.read_u8(m_offset)
        seconds = self.read_u8(s_offset)
        
        return (hours, minutes, seconds)
    
    def get_badges(self) -> tuple[list[str], list[str]]:
        """Get badges as (johto_badges, kanto_badges)."""
        johto_offset, _ = self.offsets["badges_johto"]
        kanto_offset, _ = self.offsets["badges_kanto"]
        
        johto_bits = self.read_u8(johto_offset)
        kanto_bits = self.read_u8(kanto_offset)
        
        johto_names = ["Zephyr", "Hive", "Plain", "Fog", "Storm", "Mineral", "Glacier", "Rising"]
        kanto_names = ["Boulder", "Cascade", "Thunder", "Rainbow", "Soul", "Marsh", "Volcano", "Earth"]
        
        johto_badges = [johto_names[i] for i in range(8) if johto_bits & (1 << i)]
        kanto_badges = [kanto_names[i] for i in range(8) if kanto_bits & (1 << i)]
        
        return (johto_badges, kanto_badges)
    
    def get_pokedex_counts(self) -> tuple[int, int]:
        """Get (owned, seen) counts out of 251."""
        owned_offset, owned_len = self.offsets["pokedex_owned"]
        seen_offset, seen_len = self.offsets["pokedex_seen"]
        
        owned_bits = self.data[owned_offset:owned_offset+owned_len]
        seen_bits = self.data[seen_offset:seen_offset+seen_len]
        
        owned_count = sum(bin(byte).count('1') for byte in owned_bits)
        seen_count = sum(bin(byte).count('1') for byte in seen_bits)
        
        return (owned_count, seen_count)
    
    def get_player_gender(self) -> str:
        """Get player gender (Crystal only, Gold/Silver always Male)."""
        if not self.is_crystal:
            return "Male"
        
        # Crystal-specific gender byte at 0x3E3D
        gender_byte = self.read_u8(0x3E3D)
        return "Female" if gender_byte == 0x01 else "Male"
    
    # ── Pokemon Parsing ───────────────────────────────────────────────────────
    
    def parse_box_pokemon(self, pkmn_data: bytes, ot_name: str, nickname: str) -> dict:
        """Parse a 32-byte box Pokemon structure."""
        
        # Species
        species_id = pkmn_data[GEN2_BOX_POKEMON_STRUCT["species"][0]]
        species_name = GEN2_INTERNAL_SPECIES.get(species_id, f"??#{species_id:02X}")
        
        # Held item
        item_id = pkmn_data[GEN2_BOX_POKEMON_STRUCT["held_item"][0]]
        held_item = get_item_name(item_id)
        
        # Moves
        moves = []
        for i in range(1, 5):
            move_offset = GEN2_BOX_POKEMON_STRUCT[f"move{i}"][0]
            pp_offset = GEN2_BOX_POKEMON_STRUCT[f"move{i}_pp"][0]
            
            move_id = pkmn_data[move_offset]
            pp_byte = pkmn_data[pp_offset]
            
            if move_id > 0:
                move_name = get_move_name(move_id)
                pp_ups = (pp_byte >> 6) & 0x3
                pp_current = pp_byte & 0x3F
                pp_max = get_move_max_pp(move_id)
                pp_max_with_ups = pp_max + (pp_max // 5) * pp_ups
                
                moves.append({
                    'name': move_name,
                    'id': move_id,
                    'pp_current': pp_current,
                    'pp_max': pp_max_with_ups,
                    'pp_ups': pp_ups
                })
        
        # OT ID
        ot_id_offset = GEN2_BOX_POKEMON_STRUCT["ot_id"][0]
        ot_id = (pkmn_data[ot_id_offset] << 8) | pkmn_data[ot_id_offset + 1]
        
        # EXP
        exp_offset = GEN2_BOX_POKEMON_STRUCT["exp"][0]
        exp = (pkmn_data[exp_offset] << 16) | (pkmn_data[exp_offset + 1] << 8) | pkmn_data[exp_offset + 2]
        
        # EVs
        hp_ev = (pkmn_data[0x0B] << 8) | pkmn_data[0x0C]
        atk_ev = (pkmn_data[0x0D] << 8) | pkmn_data[0x0E]
        def_ev = (pkmn_data[0x0F] << 8) | pkmn_data[0x10]
        spd_ev = (pkmn_data[0x11] << 8) | pkmn_data[0x12]
        spc_ev = (pkmn_data[0x13] << 8) | pkmn_data[0x14]
        
        # DVs
        dv_word = (pkmn_data[0x15] << 8) | pkmn_data[0x16]
        atk_dv = (dv_word >> 12) & 0xF
        def_dv = (dv_word >> 8) & 0xF
        spd_dv = (dv_word >> 4) & 0xF
        spc_dv = dv_word & 0xF
        hp_dv = ((atk_dv & 1) << 3) | ((def_dv & 1) << 2) | ((spd_dv & 1) << 1) | (spc_dv & 1)
        
        # Gender
        gender_threshold = get_gender_threshold(species_id)
        if gender_threshold == 255:
            gender = "—"
        elif gender_threshold == 254:
            gender = "F"
        elif gender_threshold == 0:
            gender = "M"
        else:
            gender = "M" if atk_dv >= (gender_threshold >> 4) else "F"
        
        # Shiny
        shiny = is_shiny(atk_dv, def_dv, spd_dv, spc_dv)
        
        # Unown form
        unown_form = None
        if species_id == 0xC9:
            unown_form = get_unown_form(atk_dv, def_dv, spd_dv, spc_dv)
        
        # Friendship
        friendship = pkmn_data[0x1B]
        
        # Pokerus
        pokerus_byte = pkmn_data[0x1C]
        pokerus_strain = (pokerus_byte >> 4) & 0xF
        pokerus_days = pokerus_byte & 0xF
        has_pokerus = pokerus_strain > 0
        pokerus_cured = pokerus_strain > 0 and pokerus_days == 0
        
        # Caught data
        caught_word = (pkmn_data[0x1D] << 8) | pkmn_data[0x1E]
        time_of_day = caught_word & 0xF
        level_met = (caught_word >> 4) & 0x3F
        ball_type = (caught_word >> 12) & 0xF
        ball_name = GEN2_BALLS.get(ball_type, f"Ball#{ball_type:02X}")
        
        # Level
        level = pkmn_data[0x1F]
        
        return {
            'species': species_name,
            'species_id': species_id,
            'level': level,
            'exp': exp,
            'held_item': held_item,
            'nickname': nickname,
            'ot_name': ot_name,
            'ot_id': ot_id,
            'gender': gender,
            'shiny': shiny,
            'unown_form': unown_form,
            'friendship': friendship,
            'pokerus': {
                'infected': has_pokerus,
                'cured': pokerus_cured,
                'strain': pokerus_strain,
                'days': pokerus_days
            },
            'caught': {
                'ball': ball_name,
                'level': level_met,
                'time': ['Morning', 'Day', 'Night'][time_of_day] if time_of_day < 3 else '?'
            },
            'dvs': {
                'hp': hp_dv,
                'attack': atk_dv,
                'defense': def_dv,
                'speed': spd_dv,
                'special': spc_dv
            },
            'evs': {
                'hp': hp_ev,
                'attack': atk_ev,
                'defense': def_ev,
                'speed': spd_ev,
                'special': spc_ev
            },
            'moves': moves,
            'hp_current': 0,
        }
    
    # ── Box Storage ───────────────────────────────────────────────────────────
    
    def get_box_count(self, box_number: int) -> int:
        """Get number of Pokemon in a box (1-14)."""
        offset = get_gen2_box_offset(box_number)
        return self.read_u8(offset)
    
    def get_box(self, box_number: int) -> list[dict]:
        """Get all Pokemon in a box (1-14)."""
        offset = get_gen2_box_offset(box_number)
        count = self.read_u8(offset)
        
        if count == 0:
            return []
        
        result = []
        data_offset = offset + 1 + 21
        ot_offset = offset + 1 + 21 + (20 * 32)
        nick_offset = offset + 1 + 21 + (20 * 32) + (20 * 11)
        
        for i in range(count):
            pkmn_data = self.data[data_offset + i * 32:data_offset + i * 32 + 32]
            ot_name = self.read_string(ot_offset + i * 11, 11)
            nickname = self.read_string(nick_offset + i * 11, 11)
            
            pokemon = self.parse_box_pokemon(bytes(pkmn_data), ot_name, nickname)
            result.append(pokemon)
        
        return result
    
    def get_all_boxes(self) -> dict[int, list[dict]]:
        """Get all 14 PC boxes."""
        return {i: self.get_box(i) for i in range(1, 15)}
    
    # ── Party ─────────────────────────────────────────────────────────────────
    
    def get_party_count(self) -> int:
        """Get number of Pokemon in party."""
        offset, _ = self.offsets["party_count"]
        count = self.read_u8(offset)
        # Validate party count (should be 0-6, but corrupted saves can have any value)
        if count > 6:
            # This is a corrupted/glitched save - cap at 6 to prevent crashes
            return 6
        return count
    
    def get_party(self) -> list[dict]:
        """Get party Pokemon (up to 6)."""
        count = self.get_party_count()
        
        if count == 0:
            return []
        
        result = []
        party_data_offset, _ = self.offsets["party_data"]
        party_ot_offset, _ = self.offsets["party_ot"]
        party_nick_offset, _ = self.offsets["party_names"]
        
        for i in range(count):
            pkmn_data = self.data[party_data_offset + i * 48:party_data_offset + i * 48 + 48]
            ot_name = self.read_string(party_ot_offset + i * 11, 11)
            nickname = self.read_string(party_nick_offset + i * 11, 11)
            
            pokemon = self.parse_box_pokemon(bytes(pkmn_data[:32]), ot_name, nickname)
            
            # Add party-only fields
            pokemon['status'] = pkmn_data[0x20]
            pokemon['hp_current'] = (pkmn_data[0x22] << 8) | pkmn_data[0x23]
            pokemon['hp_max'] = (pkmn_data[0x24] << 8) | pkmn_data[0x25]
            pokemon['attack'] = (pkmn_data[0x26] << 8) | pkmn_data[0x27]
            pokemon['defense'] = (pkmn_data[0x28] << 8) | pkmn_data[0x29]
            pokemon['speed'] = (pkmn_data[0x2A] << 8) | pkmn_data[0x2B]
            pokemon['sp_attack'] = (pkmn_data[0x2C] << 8) | pkmn_data[0x2D]
            pokemon['sp_defense'] = (pkmn_data[0x2E] << 8) | pkmn_data[0x2F]
            
            result.append(pokemon)
        
        return result
    
    # ── Advanced Features ─────────────────────────────────────────────────────
    
    def find_pokemon(self, species_name: str = None, min_level: int = None,
                     max_level: int = None, nickname: str = None, shiny_only: bool = False) -> list[dict]:
        """Find Pokemon matching criteria."""
        results = []
        
        # Search party
        for i, pkmn in enumerate(self.get_party(), 1):
            if species_name and pkmn['species'].lower() != species_name.lower():
                continue
            if min_level and pkmn['level'] < min_level:
                continue
            if max_level and pkmn['level'] > max_level:
                continue
            if nickname and pkmn['nickname'].lower() != nickname.lower():
                continue
            if shiny_only and not pkmn['shiny']:
                continue
            
            results.append({'location': 'Party', 'slot': i, 'pokemon': pkmn})
        
        # Search boxes
        for box_num in range(1, 15):
            for i, pkmn in enumerate(self.get_box(box_num), 1):
                if species_name and pkmn['species'].lower() != species_name.lower():
                    continue
                if min_level and pkmn['level'] < min_level:
                    continue
                if max_level and pkmn['level'] > max_level:
                    continue
                if nickname and pkmn['nickname'].lower() != nickname.lower():
                    continue
                if shiny_only and not pkmn['shiny']:
                    continue
                
                results.append({'location': f'Box {box_num}', 'slot': i, 'pokemon': pkmn})
        
        return results
    
    def get_species_counts(self) -> dict[str, int]:
        """Count how many of each species (party + all boxes)."""
        from collections import Counter
        species_list = []
        
        for pkmn in self.get_party():
            species_list.append(pkmn['species'])
        
        for box_num in range(1, 15):
            for pkmn in self.get_box(box_num):
                species_list.append(pkmn['species'])
        
        return dict(Counter(species_list))
    
    def get_save_summary(self) -> dict:
        """Get save file summary statistics."""
        party_count = self.get_party_count()
        
        box_counts = {}
        total_box_pokemon = 0
        for i in range(1, 15):
            count = self.get_box_count(i)
            box_counts[i] = count
            total_box_pokemon += count
        
        player_name = self.get_player_name()
        hours, minutes, seconds = self.get_playtime()
        johto_badges, kanto_badges = self.get_badges()
        owned, seen = self.get_pokedex_counts()
        
        return {
            "game_version": self.version.title(),
            "player_name": player_name,
            "playtime_hours": hours + (minutes / 60) + (seconds / 3600),
            "party_count": party_count,
            "box_pokemon": total_box_pokemon,
            "total_pokemon": party_count + total_box_pokemon,
            "badges_johto": len(johto_badges),
            "badges_kanto": len(kanto_badges),
            "badges_total": len(johto_badges) + len(kanto_badges),
            "pokedex_owned": owned,
            "pokedex_seen": seen,
            "box_counts": box_counts,
        }
    
    def export_to_json(self) -> dict:
        """Export entire save to JSON."""
        johto_badges, kanto_badges = self.get_badges()
        
        return {
            "game_version": self.version.title(),
            "trainer": {
                "name": self.get_player_name(),
                "rival": self.get_rival_name(),
                "id": self.get_trainer_id(),
                "money": self.get_money(),
                "badges_johto": johto_badges,
                "badges_kanto": kanto_badges,
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
            "party": self.get_party(),
            "boxes": {str(i): self.get_box(i) for i in range(1, 15)}
        }


# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def print_separator():
    print("──────────────────────────────────────────────────────────────────────")

def print_trainer_info(parser: Gen2SaveParser):
    print_separator()
    game_version = parser.version.title()
    player = parser.get_player_name()
    rival = parser.get_rival_name()
    tid = parser.get_trainer_id()
    money = parser.get_money()
    h, m, s = parser.get_playtime()
    johto_badges, kanto_badges = parser.get_badges()
    owned, seen = parser.get_pokedex_counts()
    
    print(f"  Game:     Pokémon {game_version}")
    print(f"  Trainer:  {player}  (#{tid:05d})")
    print(f"  Rival:    {rival}")
    print(f"  Money:    ₽{money:,}")
    print(f"  Time:     {h}h {m:02d}m {s:02d}s")
    
    all_badges = johto_badges + kanto_badges
    print(f"  Badges:   {len(all_badges)}/16  (Johto: {', '.join(johto_badges) if johto_badges else 'None'})")
    if kanto_badges:
        print(f"            {'':17}(Kanto: {', '.join(kanto_badges)})")
    print(f"  Pokédex:  {owned}/251 owned,  {seen}/251 seen")
    print_separator()

def print_party(parser: Gen2SaveParser):
    party = parser.get_party()
    
    # Check for corrupted party count
    raw_count_offset, _ = parser.offsets["party_count"]
    raw_count = parser.data[raw_count_offset]
    
    if raw_count > 6:
        print(f"\n  ── Party ({len(party)}/6) ──")
        print(f"\n⚠ Warning: Save reports {raw_count} party Pokémon (glitched/corrupted)")
        print(f"  Showing first 6 only to prevent crashes\n")
    else:
        print(f"\n  ── Party ({len(party)}/6) ──\n")
    
    for i, pkmn in enumerate(party, 1):
        # Display name with shiny indicator
        shiny = "✨" if pkmn['shiny'] else ""
        gender = f" {pkmn['gender']}" if pkmn['gender'] != "—" else ""
        
        # Check if nickname is corrupted (contains hex bytes like [XX])
        nickname = pkmn['nickname']
        is_corrupted = nickname and '[' in nickname and ']' in nickname
        
        if nickname and nickname != pkmn['species'].upper() and not is_corrupted:
            display_name = f"{nickname} ({pkmn['species']})"
        else:
            display_name = pkmn['species']
        
        held = f" @{pkmn['held_item']}" if pkmn['held_item'] else ""
        
        # Status
        status_byte = pkmn.get('status', 0)
        if status_byte == 0:
            status_str = "OK"
        elif status_byte & 0x07:  # Sleep
            status_str = f"SLP ({status_byte & 0x07})"
        elif status_byte & 0x08:
            status_str = "PSN"
        elif status_byte & 0x10:
            status_str = "BRN"
        elif status_byte & 0x20:
            status_str = "FRZ"
        elif status_byte & 0x40:
            status_str = "PAR"
        else:
            status_str = f"? (0x{status_byte:02X})"
        
        # Get types (would need type lookup - for now show as placeholder)
        # TODO: Add dual-type support when we add base stats table
        type_str = "Normal"  # Placeholder
        
        print(f"  [{i}] {display_name}{gender} {shiny}(Lv.{pkmn['level']}){held}")
        print(f"       OT: {pkmn['ot_name']} #{pkmn['ot_id']:05d}  |  Status: {status_str}")
        print(f"       HP: {pkmn['hp_current']}/{pkmn['hp_max']}  |  Type: {type_str}")
        print(f"       Atk: {pkmn['attack']:3d}  Def: {pkmn['defense']:3d}  Spd: {pkmn['speed']:3d}  SpA: {pkmn['sp_attack']:3d}  SpD: {pkmn['sp_defense']:3d}")
        
        dvs = pkmn['dvs']
        print(f"       DVs: Atk={dvs['attack']} Def={dvs['defense']} Spd={dvs['speed']} Spc={dvs['special']} HP={dvs['hp']}")
        print(f"       EXP: {pkmn['exp']:,}")
        
        # Pokérus indicator
        if pkmn['pokerus']['infected']:
            if pkmn['pokerus']['cured']:
                print(f"       Pokérus: CURED ✓")
            else:
                print(f"       Pokérus: ACTIVE! Strain {pkmn['pokerus']['strain']}, {pkmn['pokerus']['days']} days")
        
        # Friendship (Gen 2 exclusive)
        print(f"       Friendship: {pkmn['friendship']}/255")
        
        if pkmn['moves']:
            print(f"       Moves:")
            for move in pkmn['moves']:
                # Match Gen 1 spacing: move name left-aligned in 18 chars, then PP
                pp_str = f"{move['pp_current']:2d}/{move['pp_max']:2d} PP"
                if move['pp_ups'] > 0:
                    pp_str += f" (+{move['pp_ups']} PP Up)"
                print(f"         • {move['name']:<18}{pp_str}")
        print()

def print_all_boxes(parser: Gen2SaveParser):
    print(f"\n  ── PC Storage (14 boxes) ──\n")
    
    for box_num in range(1, 15):
        count = parser.get_box_count(box_num)
        bar = '█' * count + '░' * (20 - count)
        print(f"    Box {box_num:2d}: [{bar}] {count:2d}/20")
    
    total = sum(parser.get_box_count(i) for i in range(1, 15))
    print(f"\n    Total: {total}/280 box slots")

def print_box(parser: Gen2SaveParser, box_number: int):
    """Print detailed view of a single box."""
    box = parser.get_box(box_number)
    
    print(f"\n  ── Box {box_number} ({len(box)}/20) ──\n")
    
    if not box:
        print("  (Empty)\n")
        return
    
    for i, pkmn in enumerate(box, 1):
        shiny = "✨" if pkmn['shiny'] else ""
        gender = pkmn['gender']
        name = pkmn['nickname'] if pkmn['nickname'] else pkmn['species']
        held = f" @{pkmn['held_item']}" if pkmn['held_item'] else ""
        
        print(f"  {i:2d}. {name} ({gender}) {shiny}Lv.{pkmn['level']:3d}{held}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN / CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser_cli = argparse.ArgumentParser(description='Pokémon Gen 2 Save File Parser')
    parser_cli.add_argument('save_file', help='Path to .sav file')
    parser_cli.add_argument('--dump-all', action='store_true', help='Dump all Pokémon details')
    parser_cli.add_argument('--json', metavar='FILE', help='Export to JSON file')
    parser_cli.add_argument('--search', metavar='SPECIES', help='Search for specific species')
    parser_cli.add_argument('--min-level', type=int, metavar='N', help='Minimum level filter')
    parser_cli.add_argument('--max-level', type=int, metavar='N', help='Maximum level filter')
    parser_cli.add_argument('--shiny-only', action='store_true', help='Show only shiny Pokémon')
    parser_cli.add_argument('--species-count', action='store_true', help='Show species counts')
    parser_cli.add_argument('--summary', action='store_true', help='Show save summary stats')
    parser_cli.add_argument('--box', type=int, metavar='N', help='Show detailed view of box N (1-14)')
    parser_cli.add_argument('--version', choices=['gold', 'silver', 'crystal'], help='Force game version')
    
    args = parser_cli.parse_args()
    
    save_path = Path(args.save_file)
    if not save_path.exists():
        print(f"Error: File not found: {save_path}")
        sys.exit(1)
    
    print(f"\nParsing: {save_path.name}\n")
    
    parser = Gen2SaveParser(save_path, force_version=args.version)
    
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
            max_level=args.max_level,
            shiny_only=args.shiny_only
        )
        
        if not results:
            print(f"No {args.search} found")
            filters = []
            if args.min_level:
                filters.append(f"level >= {args.min_level}")
            if args.max_level:
                filters.append(f"level <= {args.max_level}")
            if args.shiny_only:
                filters.append("shiny only")
            if filters:
                print(f"  (with filters: {', '.join(filters)})")
        else:
            print(f"Found {len(results)} {args.search}:\n")
            for r in results:
                pkmn = r['pokemon']
                shiny = "✨" if pkmn['shiny'] else ""
                name = pkmn['nickname'] if pkmn['nickname'] else pkmn['species']
                print(f"  {r['location']:10} Slot {r['slot']:2d}: {name} ({pkmn['gender']}) {shiny}Lv.{pkmn['level']:3d}")
        print()
        return
    
    # Species count mode
    if args.species_count:
        counts = parser.get_species_counts()
        print("Species Counts (Party + All Boxes):\n")
        for species, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {species:<20} × {count}")
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
        print(f"  Badges:       {summary['badges_total']}/16 ({summary['badges_johto']} Johto + {summary['badges_kanto']} Kanto)")
        print(f"  Pokédex:      {summary['pokedex_owned']}/251 owned, {summary['pokedex_seen']}/251 seen")
        print(f"  Party:        {summary['party_count']}/6")
        print(f"  Boxes:        {summary['box_pokemon']}/280")
        print(f"  Total:        {summary['total_pokemon']} Pokémon")
        print()
        
        print("  Box Storage:")
        for i in range(1, 15):
            count = summary['box_counts'][i]
            bar = '█' * count + '░' * (20 - count)
            print(f"    Box {i:2d}: [{bar}] {count:2d}/20")
        print()
        return
    
    # Single box view
    if args.box:
        if not 1 <= args.box <= 14:
            print(f"Error: Box number must be 1-14")
            sys.exit(1)
        print_trainer_info(parser)
        print_box(parser, args.box)
        print_separator()
        return
    
    # Dump all mode
    if args.dump_all:
        print("=" * 70)
        print("ALL POKÉMON IN SAVE FILE")
        print("=" * 70)
        
        # Party
        print("\n=== PARTY ===\n")
        party = parser.get_party()
        for i, pkmn in enumerate(party, 1):
            shiny = "✨" if pkmn['shiny'] else ""
            name = pkmn['nickname'] if pkmn['nickname'] else pkmn['species']
            print(f"  {i}. {name} ({pkmn['gender']}) {shiny}Lv.{pkmn['level']:3d}  |  HP: {pkmn['hp_current']:3d}/{pkmn['hp_max']:3d}")
        
        # All 14 boxes
        for box_num in range(1, 15):
            box = parser.get_box(box_num)
            if not box:
                print(f"\n=== BOX {box_num} (0/20) ===\n  Empty")
                continue
            
            print(f"\n=== BOX {box_num} ({len(box)}/20) ===\n")
            for i, pkmn in enumerate(box, 1):
                shiny = "✨" if pkmn['shiny'] else ""
                name = pkmn['nickname'] if pkmn['nickname'] else pkmn['species']
                print(f"  {i:2d}. {name} ({pkmn['gender']}) {shiny}Lv.{pkmn['level']:3d}")
        
        print("\n" + "=" * 70)
        total = len(party) + sum(parser.get_box_count(i) for i in range(1, 15))
        print(f"TOTAL: {total} Pokémon")
        print("=" * 70 + "\n")
        return
    
    # Normal display
    print_trainer_info(parser)
    print_party(parser)
    print_all_boxes(parser)
    print_separator()


if __name__ == "__main__":
    main()

    def __init__(self, save_path: Path, force_version: str = None):
        """
        Initialize Gen 2 save parser.
        
        Args:
            save_path: Path to .sav file
            force_version: Optional manual override - 'gold', 'silver', or 'crystal'
        """
        self.path = Path(save_path)
        with open(save_path, "rb") as f:
            self.data = bytearray(f.read())
        
        if len(self.data) != 32816:
            print(f"⚠ Warning: Save file is {len(self.data)} bytes, expected 32816")
        
        # Detect or override game version
        if force_version:
            self.version = force_version.lower()
        else:
            self.version = self._detect_version()
    
    def _detect_version(self) -> str:
        """Detect Gold/Silver/Crystal from filename."""
        filename = self.path.name.lower()
        if 'crystal' in filename:
            return 'crystal'
        elif 'silver' in filename:
            return 'silver'
        elif 'gold' in filename:
            return 'gold'
        # Default to Gold if can't determine
        return 'gold'
    
    # ── Reading Functions ─────────────────────────────────────────────────────
    
    def read_u8(self, offset: int) -> int:
        """Read unsigned 8-bit."""
        return self.data[offset]
    
    def read_u16_be(self, offset: int) -> int:
        """Read unsigned 16-bit big-endian."""
        return (self.data[offset] << 8) | self.data[offset + 1]
    
    def read_u24_be(self, offset: int) -> int:
        """Read unsigned 24-bit big-endian."""
        return (self.data[offset] << 16) | (self.data[offset + 1] << 8) | self.data[offset + 2]
    
    def read_string(self, offset: int, length: int) -> str:
        """Read Gen 2 string (uses same encoding as Gen 1)."""
        result = []
        for i in range(length):
            byte = self.data[offset + i]
            if byte == 0x50:  # Terminator
                break
            char = GEN2_CHAR_TABLE.get(byte, f'[{byte:02X}]')
            result.append(char)
        return ''.join(result)
    
    # ── Trainer Info ──────────────────────────────────────────────────────────
    
    def get_player_name(self) -> str:
        """Get player name."""
        offset, length = self.offsets["player_name"]
        return self.read_string(offset, length)
    
    def get_rival_name(self) -> str:
        """Get rival name."""
        offset, length = self.offsets["rival_name"]
        return self.read_string(offset, length)
    
    def get_trainer_id(self) -> int:
        """Get trainer ID."""
        offset, _ = self.offsets["player_id"]
        return self.read_u16_be(offset)
    
    def get_money(self) -> int:
        """Get money (BCD encoded)."""
        offset, _ = self.offsets["money"]
        bcd = self.data[offset:offset+3]
        return int(f"{bcd[0]:02d}{bcd[1]:02d}{bcd[2]:02d}")
    
    def get_playtime(self) -> tuple[int, int, int]:
        """Get playtime as (hours, minutes, seconds)."""
        h_offset, _ = self.offsets["playtime_h"]
        m_offset, _ = self.offsets["playtime_m"]
        s_offset, _ = self.offsets["playtime_s"]
        
        hours = self.read_u16_be(h_offset)
        minutes = self.read_u8(m_offset)
        seconds = self.read_u8(s_offset)
        
        return (hours, minutes, seconds)
    
    def get_badges(self) -> tuple[list[str], list[str]]:
        """
        Get badges as (johto_badges, kanto_badges).
        Returns lists of badge names.
        """
        johto_offset, _ = self.offsets["badges_johto"]
        kanto_offset, _ = self.offsets["badges_kanto"]
        
        johto_bits = self.read_u8(johto_offset)
        kanto_bits = self.read_u8(kanto_offset)
        
        johto_names = ["Zephyr", "Hive", "Plain", "Fog", "Storm", "Mineral", "Glacier", "Rising"]
        kanto_names = ["Boulder", "Cascade", "Thunder", "Rainbow", "Soul", "Marsh", "Volcano", "Earth"]
        
        johto_badges = [johto_names[i] for i in range(8) if johto_bits & (1 << i)]
        kanto_badges = [kanto_names[i] for i in range(8) if kanto_bits & (1 << i)]
        
        return (johto_badges, kanto_badges)
    
    def get_pokedex_counts(self) -> tuple[int, int]:
        """Get (owned, seen) counts out of 251."""
        owned_offset, owned_len = self.offsets["pokedex_owned"]
        seen_offset, seen_len = self.offsets["pokedex_seen"]
        
        owned_bits = self.data[owned_offset:owned_offset+owned_len]
        seen_bits = self.data[seen_offset:seen_offset+seen_len]
        
        owned_count = sum(bin(byte).count('1') for byte in owned_bits)
        seen_count = sum(bin(byte).count('1') for byte in seen_bits)
        
        return (owned_count, seen_count)
    
    # ── Pokemon Parsing ───────────────────────────────────────────────────────
    
    def parse_box_pokemon(self, pkmn_data: bytes, ot_name: str, nickname: str) -> dict:
        """Parse a 32-byte box Pokemon structure."""
        
        # Species
        species_id = pkmn_data[GEN2_BOX_POKEMON_STRUCT["species"][0]]
        species_name = GEN2_INTERNAL_SPECIES.get(species_id, f"??#{species_id:02X}")
        
        # Held item
        item_id = pkmn_data[GEN2_BOX_POKEMON_STRUCT["held_item"][0]]
        held_item = get_item_name(item_id)
        
        # Moves
        moves = []
        for i in range(1, 5):
            move_offset = GEN2_BOX_POKEMON_STRUCT[f"move{i}"][0]
            pp_offset = GEN2_BOX_POKEMON_STRUCT[f"move{i}_pp"][0]
            
            move_id = pkmn_data[move_offset]
            pp_byte = pkmn_data[pp_offset]
            
            if move_id > 0:
                move_name = get_move_name(move_id)
                pp_ups = (pp_byte >> 6) & 0x3
                pp_current = pp_byte & 0x3F
                pp_max = get_move_max_pp(move_id)
                
                # Calculate actual max PP with PP Ups
                pp_max_with_ups = pp_max + (pp_max // 5) * pp_ups
                
                moves.append({
                    'name': move_name,
                    'id': move_id,
                    'pp_current': pp_current,
                    'pp_max': pp_max_with_ups,
                    'pp_ups': pp_ups
                })
        
        # OT ID
        ot_id_offset = GEN2_BOX_POKEMON_STRUCT["ot_id"][0]
        ot_id = (pkmn_data[ot_id_offset] << 8) | pkmn_data[ot_id_offset + 1]
        
        # EXP
        exp_offset = GEN2_BOX_POKEMON_STRUCT["exp"][0]
        exp = (pkmn_data[exp_offset] << 16) | (pkmn_data[exp_offset + 1] << 8) | pkmn_data[exp_offset + 2]
        
        # EVs
        hp_ev = (pkmn_data[0x0B] << 8) | pkmn_data[0x0C]
        atk_ev = (pkmn_data[0x0D] << 8) | pkmn_data[0x0E]
        def_ev = (pkmn_data[0x0F] << 8) | pkmn_data[0x10]
        spd_ev = (pkmn_data[0x11] << 8) | pkmn_data[0x12]
        spc_ev = (pkmn_data[0x13] << 8) | pkmn_data[0x14]
        
        # DVs
        dv_word = (pkmn_data[0x15] << 8) | pkmn_data[0x16]
        atk_dv = (dv_word >> 12) & 0xF
        def_dv = (dv_word >> 8) & 0xF
        spd_dv = (dv_word >> 4) & 0xF
        spc_dv = dv_word & 0xF
        hp_dv = ((atk_dv & 1) << 3) | ((def_dv & 1) << 2) | ((spd_dv & 1) << 1) | (spc_dv & 1)
        
        # Gender
        gender_threshold = get_gender_threshold(species_id)
        if gender_threshold == 255:
            gender = "—"  # Genderless
        elif gender_threshold == 254:
            gender = "F"  # Always female
        elif gender_threshold == 0:
            gender = "M"  # Always male
        else:
            gender = "M" if atk_dv >= (gender_threshold >> 4) else "F"
        
        # Shiny
        shiny = is_shiny(atk_dv, def_dv, spd_dv, spc_dv)
        
        # Unown form
        unown_form = None
        if species_id == 0xC9:  # Unown
            unown_form = get_unown_form(atk_dv, def_dv, spd_dv, spc_dv)
        
        # Friendship
        friendship = pkmn_data[0x1B]
        
        # Pokerus
        pokerus_byte = pkmn_data[0x1C]
        pokerus_strain = (pokerus_byte >> 4) & 0xF
        pokerus_days = pokerus_byte & 0xF
        has_pokerus = pokerus_strain > 0
        pokerus_cured = pokerus_strain > 0 and pokerus_days == 0
        
        # Caught data
        caught_word = (pkmn_data[0x1D] << 8) | pkmn_data[0x1E]
        time_of_day = caught_word & 0xF
        level_met = (caught_word >> 4) & 0x3F
        ball_type = (caught_word >> 12) & 0xF
        ball_name = GEN2_BALLS.get(ball_type, f"Ball#{ball_type:02X}")
        
        # Level
        level = pkmn_data[0x1F]
        
        # Calculate stats (box Pokemon don't have current stats stored)
        # TODO: Implement stat calculation
        hp_current = 0
        
        return {
            'species': species_name,
            'species_id': species_id,
            'level': level,
            'exp': exp,
            'held_item': held_item,
            'nickname': nickname,
            'ot_name': ot_name,
            'ot_id': ot_id,
            'gender': gender,
            'shiny': shiny,
            'unown_form': unown_form,
            'friendship': friendship,
            'pokerus': {
                'infected': has_pokerus,
                'cured': pokerus_cured,
                'strain': pokerus_strain,
                'days': pokerus_days
            },
            'caught': {
                'ball': ball_name,
                'level': level_met,
                'time': ['Morning', 'Day', 'Night'][time_of_day] if time_of_day < 3 else '?'
            },
            'dvs': {
                'hp': hp_dv,
                'attack': atk_dv,
                'defense': def_dv,
                'speed': spd_dv,
                'special': spc_dv
            },
            'evs': {
                'hp': hp_ev,
                'attack': atk_ev,
                'defense': def_ev,
                'speed': spd_ev,
                'special': spc_ev
            },
            'moves': moves,
            'hp_current': hp_current,
        }
    
    # ── Box Storage ───────────────────────────────────────────────────────────
    
    def get_box_count(self, box_number: int) -> int:
        """Get number of Pokemon in a box (1-14)."""
        offset = get_gen2_box_offset(box_number)
        return self.read_u8(offset)
    
    def get_box(self, box_number: int) -> list[dict]:
        """Get all Pokemon in a box (1-14)."""
        offset = get_gen2_box_offset(box_number)
        count = self.read_u8(offset)
        
        if count == 0:
            return []
        
        result = []
        
        # Species list starts at offset + 1
        # Pokemon data starts at offset + 1 + 21
        # OT names start at offset + 1 + 21 + (20 * 32)
        # Nicknames start at offset + 1 + 21 + (20 * 32) + (20 * 11)
        
        data_offset = offset + 1 + 21
        ot_offset = offset + 1 + 21 + (20 * 32)
        nick_offset = offset + 1 + 21 + (20 * 32) + (20 * 11)
        
        for i in range(count):
            pkmn_data = self.data[data_offset + i * 32:data_offset + i * 32 + 32]
            ot_name = self.read_string(ot_offset + i * 11, 11)
            nickname = self.read_string(nick_offset + i * 11, 11)
            
            pokemon = self.parse_box_pokemon(bytes(pkmn_data), ot_name, nickname)
            result.append(pokemon)
        
        return result
    
    def get_all_boxes(self) -> dict[int, list[dict]]:
        """Get all 14 PC boxes."""
        return {i: self.get_box(i) for i in range(1, 15)}
    
    # ── Party ─────────────────────────────────────────────────────────────────
    
    def get_party_count(self) -> int:
        """Get number of Pokemon in party."""
        offset, _ = self.offsets["party_count"]
        return self.read_u8(offset)
    
    def get_party(self) -> list[dict]:
        """Get party Pokemon (up to 6)."""
        count = self.get_party_count()
        
        if count == 0:
            return []
        
        result = []
        party_data_offset, _ = self.offsets["party_data"]
        party_ot_offset, _ = self.offsets["party_ot"]
        party_nick_offset, _ = self.offsets["party_names"]
        
        for i in range(count):
            # Party Pokemon is 48 bytes (32 box + 16 party-only)
            pkmn_data = self.data[party_data_offset + i * 48:party_data_offset + i * 48 + 48]
            ot_name = self.read_string(party_ot_offset + i * 11, 11)
            nickname = self.read_string(party_nick_offset + i * 11, 11)
            
            # Parse as box Pokemon first (first 32 bytes)
            pokemon = self.parse_box_pokemon(bytes(pkmn_data[:32]), ot_name, nickname)
            
            # Add party-only fields (bytes 32-47)
            pokemon['status'] = pkmn_data[0x20]
            pokemon['hp_current'] = (pkmn_data[0x22] << 8) | pkmn_data[0x23]
            pokemon['hp_max'] = (pkmn_data[0x24] << 8) | pkmn_data[0x25]
            pokemon['attack'] = (pkmn_data[0x26] << 8) | pkmn_data[0x27]
            pokemon['defense'] = (pkmn_data[0x28] << 8) | pkmn_data[0x29]
            pokemon['speed'] = (pkmn_data[0x2A] << 8) | pkmn_data[0x2B]
            pokemon['sp_attack'] = (pkmn_data[0x2C] << 8) | pkmn_data[0x2D]
            pokemon['sp_defense'] = (pkmn_data[0x2E] << 8) | pkmn_data[0x2F]
            
            result.append(pokemon)
        
        return result


if __name__ == "__main__":
    main()