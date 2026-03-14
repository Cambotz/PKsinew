#!/usr/bin/env python3

"""
Universal Pokemon Object (UPO) - Multi-Generation Support
Sinew's internal standard format for Pokemon across all generations.

The UPO serves as the canonical representation of a Pokemon that can be:
  - Parsed from any generation's save format
  - Converted between generations
  - Validated for legality
  - Written back to any supported generation

Architecture:
    Gen Save File → Gen Parser → UniversalPokemon
    UniversalPokemon → Legality Engine
    UniversalPokemon → Gen Writer → Gen Save File

Author: Sinew Development Team
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
import json


# =============================================================================
# HELPER DATACLASSES
# =============================================================================

@dataclass
class MoveSlot:
    """Represents a single move slot."""
    move_id: int
    pp: int
    pp_ups: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)


@dataclass
class IVSet:
    """Individual Values (0-31 in Gen 3+, converted from DVs for Gen 1/2)."""
    hp: int = 0
    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

    def to_tuple(self) -> tuple:
        """Return IVs as (HP, Atk, Def, SpA, SpD, Spe)"""
        return (self.hp, self.attack, self.defense, 
                self.sp_attack, self.sp_defense, self.speed)


@dataclass
class EVSet:
    """Effort Values (0-255 per stat, max 510 total in Gen 3+)."""
    hp: int = 0
    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

    def total(self) -> int:
        """Calculate total EVs"""
        return sum([self.hp, self.attack, self.defense,
                   self.sp_attack, self.sp_defense, self.speed])

    def to_tuple(self) -> tuple:
        """Return EVs as (HP, Atk, Def, SpA, SpD, Spe)"""
        return (self.hp, self.attack, self.defense,
                self.sp_attack, self.sp_defense, self.speed)


@dataclass
class StatSet:
    """Calculated battle stats (recalculable from base stats + IVs + EVs + nature)."""
    hp: int = 0
    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)


@dataclass
class ContestStats:
    """Contest stats (Gen 3+, used in Hoenn contests)."""
    cool: int = 0
    beauty: int = 0
    cute: int = 0
    smart: int = 0
    tough: int = 0
    sheen: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)


# =============================================================================
# UNIVERSAL POKEMON OBJECT
# =============================================================================

@dataclass
class UniversalPokemon:
    """
    Universal Pokemon Object - the canonical internal representation.
    
    This object contains ALL fields that exist across Pokemon generations,
    even if some fields are None for older generations.
    
    Design principles:
    - Fields default to None if not present in origin generation
    - IVs are standardized to 0-31 (converted from DVs for Gen 1/2)
    - All data needed for legality checking is preserved
    - Generation-specific data is stored in raw_data dict
    - Lossless conversion when possible
    """

    # -------------------------------------------------------------------------
    # CORE IDENTITY
    # -------------------------------------------------------------------------
    
    species: int = 0                    # National Dex number
    form: Optional[int] = None          # Form ID (Deoxys, Rotom, etc.) - Gen 3+
    nickname: str = ""                  # 10 chars in Gen 3
    language: int = 2                   # Language ID (default English = 2)
    gender: Optional[int] = None        # 0=Male, 1=Female, 2=Genderless
    
    is_egg: bool = False
    is_shiny: Optional[bool] = None     # Can be calculated from PID/TID/SID

    # -------------------------------------------------------------------------
    # TRAINER DATA
    # -------------------------------------------------------------------------
    
    ot_name: str = ""                   # Original Trainer name
    tid: int = 0                        # Trainer ID (16-bit)
    sid: Optional[int] = None           # Secret ID (Gen 3+ only)
    ot_gender: Optional[int] = None     # Trainer gender (0=Male, 1=Female)

    # -------------------------------------------------------------------------
    # GROWTH & PROGRESSION
    # -------------------------------------------------------------------------
    
    level: int = 1
    experience: int = 0
    friendship: int = 0                 # Base friendship in Gen 3, evolves with use

    # -------------------------------------------------------------------------
    # BATTLE ATTRIBUTES
    # -------------------------------------------------------------------------
    
    nature: Optional[int] = None        # Nature ID (Gen 3+ only, 0-24)
    ability: Optional[int] = None       # Ability ID (Gen 3+ only)
    ability_slot: Optional[int] = None  # Which ability slot (0 or 1)
    held_item: Optional[int] = None     # Held item ID (Gen 2+)

    # -------------------------------------------------------------------------
    # GENETIC DATA (Critical for legality)
    # -------------------------------------------------------------------------
    
    pid: Optional[int] = None           # Personality Value (Gen 3+, determines nature/ability/gender/shiny)
    
    ivs: IVSet = field(default_factory=IVSet)
    evs: EVSet = field(default_factory=EVSet)

    # -------------------------------------------------------------------------
    # MOVES
    # -------------------------------------------------------------------------
    
    moves: List[Optional[MoveSlot]] = field(
        default_factory=lambda: [None, None, None, None]
    )

    # -------------------------------------------------------------------------
    # CALCULATED STATS
    # -------------------------------------------------------------------------
    
    stats: StatSet = field(default_factory=StatSet)
    current_hp: int = 0                 # Current HP in battle

    # -------------------------------------------------------------------------
    # STATUS & CONDITION
    # -------------------------------------------------------------------------
    
    status_condition: int = 0           # Status ailment (0=None, 2=Poison, 4=Burn, etc.)
    pokerus: int = 0                    # Pokerus status (Gen 2+)

    # -------------------------------------------------------------------------
    # ENCOUNTER METADATA (Legality-critical)
    # -------------------------------------------------------------------------
    
    met_location: Optional[int] = None  # Location ID where caught
    met_level: Optional[int] = None     # Level when caught
    met_game: Optional[str] = None      # Game of origin (e.g., "Emerald")
    met_date: Optional[str] = None      # Date met (Gen 4+)
    
    pokeball: Optional[int] = None      # Pokeball type (Gen 3+)
    fateful_encounter: bool = False     # Event Pokemon flag

    # -------------------------------------------------------------------------
    # COSMETIC & ACHIEVEMENTS
    # -------------------------------------------------------------------------
    
    markings: int = 0                   # PC marking flags
    ribbons: List[int] = field(default_factory=list)
    contest_stats: ContestStats = field(default_factory=ContestStats)

    # -------------------------------------------------------------------------
    # SINEW-SPECIFIC METADATA
    # -------------------------------------------------------------------------
    
    sinew_id: Optional[str] = None      # Echo/Achievement ID (e.g., "SINEW_001")
    sinew_source: Optional[str] = None  # "echo", "achievement", "generator"
    
    # -------------------------------------------------------------------------
    # LEGALITY METADATA
    # -------------------------------------------------------------------------
    
    origin_generation: Optional[int] = None  # Generation this Pokemon originated from
    origin_game: Optional[str] = None        # Specific game (e.g., "Emerald")
    
    legal: Optional[bool] = None             # Legality check result
    legal_errors: List[str] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # RAW GENERATION DATA (Prevents data loss on conversion)
    # -------------------------------------------------------------------------
    
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def to_dict(self) -> Dict:
        """
        Serialize Pokemon to dictionary (JSON-compatible).
        
        Returns:
            Dict: Full Pokemon data including nested structures
        """
        data = {}
        for key, value in asdict(self).items():
            if isinstance(value, (IVSet, EVSet, StatSet, ContestStats)):
                data[key] = value.to_dict() if hasattr(value, 'to_dict') else asdict(value)
            elif isinstance(value, list) and value and hasattr(value[0], 'to_dict'):
                # Handle list of MoveSlots
                data[key] = [m.to_dict() if m else None for m in value]
            else:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'UniversalPokemon':
        """
        Deserialize Pokemon from dictionary.
        
        Args:
            data: Dictionary containing Pokemon data
            
        Returns:
            UniversalPokemon: Reconstructed Pokemon object
        """
        # Handle nested structures
        if 'ivs' in data and isinstance(data['ivs'], dict):
            data['ivs'] = IVSet.from_dict(data['ivs'])
        if 'evs' in data and isinstance(data['evs'], dict):
            data['evs'] = EVSet.from_dict(data['evs'])
        if 'stats' in data and isinstance(data['stats'], dict):
            data['stats'] = StatSet.from_dict(data['stats'])
        if 'contest_stats' in data and isinstance(data['contest_stats'], dict):
            data['contest_stats'] = ContestStats.from_dict(data['contest_stats'])
        
        # Handle move slots
        if 'moves' in data and isinstance(data['moves'], list):
            data['moves'] = [
                MoveSlot.from_dict(m) if m else None 
                for m in data['moves']
            ]
        
        return cls(**data)

    def to_json(self, indent: int = 2) -> str:
        """
        Export Pokemon as JSON string.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            str: JSON representation
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> 'UniversalPokemon':
        """
        Load Pokemon from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            UniversalPokemon: Reconstructed Pokemon
        """
        return cls.from_dict(json.loads(json_str))

    # =========================================================================
    # DERIVED CALCULATIONS
    # =========================================================================

    def calculate_shiny(self) -> Optional[bool]:
        """
        Calculate shininess from PID, TID, SID (Gen 3+ only).
        
        Formula: (TID ^ SID ^ (PID >> 16) ^ (PID & 0xFFFF)) < 8
        
        Returns:
            bool: True if shiny, False if not, None if unable to calculate
        """
        if self.pid is None or self.sid is None:
            return None
        
        xor_result = (
            (self.tid ^ self.sid) ^
            ((self.pid >> 16) ^ (self.pid & 0xFFFF))
        )
        
        return xor_result < 8

    def derive_nature(self) -> Optional[int]:
        """
        Derive nature from PID (Gen 3+ only).
        
        Formula: nature = PID % 25
        
        Returns:
            int: Nature ID (0-24), or None if no PID
        """
        if self.pid is None:
            return None
        return self.pid % 25

    def derive_ability_slot(self) -> Optional[int]:
        """
        Derive ability slot from PID (Gen 3 only).
        
        Formula: ability_slot = PID & 1
        
        Returns:
            int: 0 or 1, or None if no PID
        """
        if self.pid is None:
            return None
        return self.pid & 1

    def derive_gender_from_pid(self, gender_ratio: int) -> Optional[int]:
        """
        Derive gender from PID and species gender ratio (Gen 3+).
        
        Args:
            gender_ratio: Species gender ratio
                         255 = Genderless
                         254 = Always Female
                         0   = Always Male
                         127 = 50/50
                         
        Returns:
            int: 0=Male, 1=Female, 2=Genderless, or None if no PID
        """
        if self.pid is None:
            return None
        
        if gender_ratio == 255:
            return 2  # Genderless
        if gender_ratio == 254:
            return 1  # Always female
        if gender_ratio == 0:
            return 0  # Always male
        
        # Compare lowest byte of PID to gender ratio
        gender_value = self.pid & 0xFF
        return 1 if gender_value < gender_ratio else 0

    def validate_consistency(self) -> List[str]:
        """
        Validate internal consistency (PID relationships, stat calculations, etc.).
        
        Returns:
            List[str]: List of consistency errors (empty if valid)
        """
        errors = []
        
        # Check PID-derived attributes for Gen 3+
        if self.pid is not None:
            # Nature consistency
            if self.nature is not None:
                derived_nature = self.derive_nature()
                if derived_nature != self.nature:
                    errors.append(f"Nature mismatch: stored={self.nature}, derived={derived_nature}")
            
            # Ability slot consistency
            if self.ability_slot is not None:
                derived_slot = self.derive_ability_slot()
                if derived_slot != self.ability_slot:
                    errors.append(f"Ability slot mismatch: stored={self.ability_slot}, derived={derived_slot}")
            
            # Shiny consistency
            if self.is_shiny is not None and self.sid is not None:
                derived_shiny = self.calculate_shiny()
                if derived_shiny != self.is_shiny:
                    errors.append(f"Shiny mismatch: stored={self.is_shiny}, derived={derived_shiny}")
        
        # Check move count
        valid_moves = [m for m in self.moves if m is not None]
        if len(valid_moves) > 4:
            errors.append(f"Too many moves: {len(valid_moves)} (max 4)")
        
        # Check EV total (Gen 3+: max 510)
        if self.origin_generation and self.origin_generation >= 3:
            ev_total = self.evs.total()
            if ev_total > 510:
                errors.append(f"EV total too high: {ev_total} (max 510)")
        
        return errors

    # =========================================================================
    # GENERATION-SPECIFIC CHECKS
    # =========================================================================

    def is_gen1_compatible(self) -> bool:
        """Check if this Pokemon can exist in Gen 1."""
        # Gen 1 only has species 1-151
        if self.species > 151:
            return False
        # No abilities, natures, held items in Gen 1
        if self.ability is not None or self.nature is not None or self.held_item is not None:
            return False
        return True

    def is_gen2_compatible(self) -> bool:
        """Check if this Pokemon can exist in Gen 2."""
        # Gen 2 has species 1-251
        if self.species > 251:
            return False
        # No abilities or natures in Gen 2
        if self.ability is not None or self.nature is not None:
            return False
        return True

    def is_gen3_compatible(self) -> bool:
        """Check if this Pokemon can exist in Gen 3."""
        # Gen 3 has species 1-386 (National Dex in FRLG/Emerald)
        if self.species > 386:
            return False
        return True


# =============================================================================
# CONVERSION HELPERS
# =============================================================================

def dv_to_iv(dv: int) -> int:
    """
    Convert Gen 1/2 DV (0-15) to Gen 3+ IV (0-31).
    
    Formula: IV = DV * 2 + (random 0 or 1)
    For perfect conversion: IV = DV * 2
    
    Args:
        dv: DV value (0-15)
        
    Returns:
        int: IV value (0-31)
    """
    return min(31, dv * 2)


def iv_to_dv(iv: int) -> int:
    """
    Convert Gen 3+ IV (0-31) to Gen 1/2 DV (0-15).
    
    Formula: DV = IV // 2
    Note: This loses precision (31 IV → 15 DV)
    
    Args:
        iv: IV value (0-31)
        
    Returns:
        int: DV value (0-15)
    """
    return min(15, iv // 2)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Create a Gen 3 Pikachu
    pikachu = UniversalPokemon(
        species=25,
        nickname="SPARKY",
        level=35,
        tid=12345,
        sid=54321,
        pid=382947293,
        ot_name="CAM",
        
        nature=3,  # Adamant
        ability=9,  # Static
        ability_slot=0,
        held_item=45,  # Oran Berry
        
        ivs=IVSet(hp=31, attack=31, defense=20, sp_attack=25, sp_defense=28, speed=30),
        evs=EVSet(attack=252, sp_attack=252, speed=4),
        
        friendship=220,
        pokeball=4,  # Great Ball
        met_location=16,
        met_level=5,
        met_game="Emerald",
        
        origin_generation=3,
        origin_game="Emerald",
        
        sinew_id="SINEW_001",
        sinew_source="echo",
    )
    
    # Add moves
    pikachu.moves[0] = MoveSlot(move_id=85, pp=10, pp_ups=2)  # Thunderbolt
    pikachu.moves[1] = MoveSlot(move_id=98, pp=15, pp_ups=1)  # Quick Attack
    
    # Validate
    errors = pikachu.validate_consistency()
    print(f"Validation errors: {errors if errors else 'None'}")
    
    # Serialize
    print("\n=== JSON Export ===")
    print(pikachu.to_json(indent=2))
    
    # Calculate derived values
    print(f"\n=== Derived Values ===")
    print(f"Shiny: {pikachu.calculate_shiny()}")
    print(f"Nature (derived): {pikachu.derive_nature()}")
    print(f"Ability slot (derived): {pikachu.derive_ability_slot()}")
