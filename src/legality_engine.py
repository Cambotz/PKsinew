#!/usr/bin/env python3

"""
Pokemon Legality Validation Engine
Validates Pokemon for internal consistency and Gen 3 legality.

Author: Sinew Development Team
"""

from typing import List, Optional
from universal_pokemon import UniversalPokemon


# =============================================================================
# VALIDATION LEVELS
# =============================================================================

class ValidationLevel:
    """Validation strictness levels."""
    PERMISSIVE = 0   # Only check critical errors (Bad Egg prevention)
    STANDARD = 1     # Check common legality issues
    STRICT = 2       # Full legality enforcement (for competitive)


# =============================================================================
# CORE VALIDATION
# =============================================================================

def validate_pokemon(
    pokemon: UniversalPokemon, 
    level: int = ValidationLevel.STANDARD
) -> List[str]:
    """
    Validate Pokemon legality.
    
    Args:
        pokemon: UniversalPokemon to validate
        level: Validation strictness level
        
    Returns:
        List of error strings (empty if legal)
    """
    errors = []
    
    # === CRITICAL (PERMISSIVE) ===
    # These prevent Bad Eggs and game crashes
    
    # 1. Internal consistency (PID-derived attributes)
    errors.extend(pokemon.validate_consistency())
    
    # 2. Species validity
    if pokemon.species < 1 or pokemon.species > 493:  # Up to Gen 4
        errors.append(f"Invalid species ID: {pokemon.species}")
    
    # 3. Level validity
    if pokemon.level < 1 or pokemon.level > 100:
        errors.append(f"Invalid level: {pokemon.level} (must be 1-100)")
    
    # 4. Move count
    move_count = len([m for m in pokemon.moves if m is not None])
    if move_count > 4:
        errors.append(f"Too many moves: {move_count} (max 4)")
    
    if level == ValidationLevel.PERMISSIVE:
        return errors
    
    # === STANDARD ===
    # Common legality issues
    
    # 5. Generation compatibility
    if pokemon.origin_generation == 3:
        if not pokemon.is_gen3_compatible():
            errors.append(f"Species {pokemon.species} not available in Gen 3")
    
    # 6. EV total (Gen 3+: max 510, max 255 per stat)
    if pokemon.origin_generation and pokemon.origin_generation >= 3:
        ev_total = pokemon.evs.total()
        if ev_total > 510:
            errors.append(f"EV total too high: {ev_total} (max 510)")
        
        for stat_name, stat_value in pokemon.evs.__dict__.items():
            if stat_value > 255:
                errors.append(f"EV {stat_name} too high: {stat_value} (max 255)")
    
    # 7. IV validity (Gen 3+: 0-31)
    for stat_name, stat_value in pokemon.ivs.__dict__.items():
        if stat_value < 0 or stat_value > 31:
            errors.append(f"IV {stat_name} invalid: {stat_value} (must be 0-31)")
    
    # 8. Nature validity (Gen 3+: 0-24)
    if pokemon.nature is not None:
        if pokemon.nature < 0 or pokemon.nature > 24:
            errors.append(f"Invalid nature: {pokemon.nature} (must be 0-24)")
    
    # 9. Gender validity
    if pokemon.gender is not None:
        if pokemon.gender not in (0, 1, 2):  # Male, Female, Genderless
            errors.append(f"Invalid gender: {pokemon.gender}")
    
    # 10. Friendship/Happiness validity (0-255)
    if pokemon.friendship < 0 or pokemon.friendship > 255:
        errors.append(f"Invalid friendship: {pokemon.friendship} (must be 0-255)")
    
    if level == ValidationLevel.STANDARD:
        return errors
    
    # === STRICT ===
    # Full legality enforcement
    
    # 11. Move legality (would require move learnset data)
    # TODO: Check if Pokemon can learn its moves
    
    # 12. Evolution legality (would require evolution data)
    # TODO: Check if level is valid for evolution stage
    
    # 13. Encounter legality (would require encounter tables)
    # TODO: Check if met_location is valid for species
    
    # 14. Ability legality (would require ability tables)
    # TODO: Check if ability exists for species
    
    return errors


# =============================================================================
# SPECIFIC VALIDATORS
# =============================================================================

def validate_pid_consistency(pokemon: UniversalPokemon) -> List[str]:
    """
    Validate PID-derived attributes are consistent.
    This is the most critical check - prevents Bad Eggs.
    
    Returns:
        List of errors (empty if valid)
    """
    errors = []
    
    if pokemon.pid is None:
        errors.append("PID is None (required for Gen 3)")
        return errors
    
    # Check nature
    if pokemon.nature is not None:
        derived_nature = pokemon.derive_nature()
        if derived_nature != pokemon.nature:
            errors.append(
                f"Nature mismatch: stored={pokemon.nature}, "
                f"derived from PID={derived_nature} (PID={pokemon.pid:08X})"
            )
    
    # Check ability slot
    if pokemon.ability_slot is not None:
        derived_slot = pokemon.derive_ability_slot()
        if derived_slot != pokemon.ability_slot:
            errors.append(
                f"Ability slot mismatch: stored={pokemon.ability_slot}, "
                f"derived from PID={derived_slot} (PID={pokemon.pid:08X})"
            )
    
    # Check shiny
    if pokemon.is_shiny is not None and pokemon.sid is not None:
        derived_shiny = pokemon.calculate_shiny()
        if derived_shiny != pokemon.is_shiny:
            errors.append(
                f"Shiny mismatch: stored={pokemon.is_shiny}, "
                f"calculated={derived_shiny} (PID={pokemon.pid:08X}, "
                f"TID={pokemon.tid}, SID={pokemon.sid})"
            )
    
    return errors


def validate_for_generation(pokemon: UniversalPokemon, generation: int) -> List[str]:
    """
    Validate Pokemon can exist in a specific generation.
    
    Args:
        pokemon: Pokemon to validate
        generation: Target generation (1, 2, 3, etc.)
        
    Returns:
        List of errors (empty if valid)
    """
    errors = []
    
    if generation == 1:
        if not pokemon.is_gen1_compatible():
            errors.append("Pokemon has features not available in Gen 1")
            if pokemon.species > 151:
                errors.append(f"Species {pokemon.species} not in Gen 1")
            if pokemon.ability is not None:
                errors.append("Gen 1 has no abilities")
            if pokemon.nature is not None:
                errors.append("Gen 1 has no natures")
            if pokemon.held_item is not None:
                errors.append("Gen 1 has no held items")
    
    elif generation == 2:
        if not pokemon.is_gen2_compatible():
            errors.append("Pokemon has features not available in Gen 2")
            if pokemon.species > 251:
                errors.append(f"Species {pokemon.species} not in Gen 2")
            if pokemon.ability is not None:
                errors.append("Gen 2 has no abilities")
            if pokemon.nature is not None:
                errors.append("Gen 2 has no natures")
    
    elif generation == 3:
        if not pokemon.is_gen3_compatible():
            errors.append("Pokemon has features not available in Gen 3")
            if pokemon.species > 386:
                errors.append(f"Species {pokemon.species} not in Gen 3")
    
    return errors


def validate_sinew_pokemon(pokemon: UniversalPokemon) -> List[str]:
    """
    Validate Sinew-generated Pokemon (achievement/echo system).
    
    Additional checks specific to Sinew's delivery systems.
    
    Returns:
        List of errors (empty if valid)
    """
    errors = []
    
    # All Sinew Pokemon should have origin metadata
    if not pokemon.sinew_id and not pokemon.sinew_source:
        errors.append("Missing Sinew metadata (sinew_id or sinew_source)")
    
    # Achievement Pokemon should have specific metadata
    if pokemon.sinew_source == "achievement":
        if not pokemon.sinew_id or not pokemon.sinew_id.startswith("SINEW_"):
            errors.append(
                f"Invalid achievement ID: {pokemon.sinew_id} "
                "(should start with 'SINEW_')"
            )
        
        # Achievement Pokemon are typically event Pokemon (fateful encounter)
        if not pokemon.fateful_encounter:
            errors.append("Achievement Pokemon should have fateful_encounter=True")
    
    # Echo Pokemon (Altering Cave) validations
    if pokemon.sinew_source == "echo":
        # Echo Pokemon should be from Altering Cave
        # (location_id would need to be checked against constants)
        pass
    
    return errors


# =============================================================================
# VALIDATION REPORTS
# =============================================================================

class ValidationReport:
    """Detailed validation report."""
    
    def __init__(self, pokemon: UniversalPokemon, level: int = ValidationLevel.STANDARD):
        self.pokemon = pokemon
        self.level = level
        self.errors = validate_pokemon(pokemon, level)
        self.warnings = []  # Future: non-critical issues
    
    @property
    def is_valid(self) -> bool:
        """Check if Pokemon passed validation."""
        return len(self.errors) == 0
    
    @property
    def is_legal(self) -> bool:
        """Alias for is_valid."""
        return self.is_valid
    
    def __str__(self) -> str:
        """String representation of report."""
        if self.is_valid:
            return f"✓ {self.pokemon.species} is LEGAL"
        else:
            lines = [f"✗ {self.pokemon.species} is ILLEGAL:"]
            for error in self.errors:
                lines.append(f"  - {error}")
            return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Export report as dictionary."""
        return {
            "valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "pokemon_summary": {
                "species": self.pokemon.species,
                "level": self.pokemon.level,
                "pid": f"0x{self.pokemon.pid:08X}" if self.pokemon.pid else None,
                "sinew_id": self.pokemon.sinew_id,
            }
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def is_legal(pokemon: UniversalPokemon, level: int = ValidationLevel.STANDARD) -> bool:
    """
    Quick legality check.
    
    Returns:
        True if Pokemon is legal, False otherwise
    """
    return len(validate_pokemon(pokemon, level)) == 0


def get_validation_report(
    pokemon: UniversalPokemon, 
    level: int = ValidationLevel.STANDARD
) -> ValidationReport:
    """
    Get detailed validation report.
    
    Returns:
        ValidationReport object
    """
    return ValidationReport(pokemon, level)


# =============================================================================
# BATCH VALIDATION
# =============================================================================

def validate_pokemon_list(
    pokemon_list: List[UniversalPokemon],
    level: int = ValidationLevel.STANDARD
) -> dict:
    """
    Validate a list of Pokemon (e.g., entire PC box).
    
    Returns:
        Summary dict with counts and details
    """
    results = {
        "total": len(pokemon_list),
        "legal": 0,
        "illegal": 0,
        "reports": []
    }
    
    for pokemon in pokemon_list:
        if pokemon is None:
            continue
        
        report = ValidationReport(pokemon, level)
        results["reports"].append(report)
        
        if report.is_valid:
            results["legal"] += 1
        else:
            results["illegal"] += 1
    
    return results


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    from universal_pokemon import UniversalPokemon, IVSet
    
    print("=== Pokemon Legality Validator ===\n")
    
    # Test 1: Valid Pokemon
    print("Test 1: Valid Pokemon")
    valid_pokemon = UniversalPokemon(
        species=25,  # Pikachu
        level=50,
        pid=0x12345678,
        tid=31337,
        sid=1337,
        nature=0x12345678 % 25,  # Derived correctly
        ability_slot=0x12345678 & 1,  # Derived correctly
        ivs=IVSet(hp=31, attack=31, defense=31, sp_attack=31, sp_defense=31, speed=31),
        origin_generation=3,
    )
    
    report = get_validation_report(valid_pokemon)
    print(report)
    print()
    
    # Test 2: Invalid Pokemon (PID mismatch)
    print("Test 2: Invalid Pokemon (PID mismatch)")
    invalid_pokemon = UniversalPokemon(
        species=25,
        level=50,
        pid=0x12345678,
        tid=31337,
        sid=1337,
        nature=10,  # Wrong! Should be pid % 25 = 8
        ability_slot=0,  # Wrong! Should be pid & 1 = 0... wait this is correct
        ivs=IVSet(hp=31, attack=31, defense=31, sp_attack=31, sp_defense=31, speed=31),
        origin_generation=3,
    )
    
    report = get_validation_report(invalid_pokemon)
    print(report)
    print()
    
    # Test 3: Batch validation
    print("Test 3: Batch Validation")
    pokemon_box = [valid_pokemon, invalid_pokemon, None, valid_pokemon]
    results = validate_pokemon_list(pokemon_box)
    
    print(f"Total: {results['total']}")
    print(f"Legal: {results['legal']}")
    print(f"Illegal: {results['illegal']}")
    
    for i, report in enumerate(results['reports']):
        if not report.is_valid:
            print(f"\n  Pokemon {i}: {report}")
