#!/bin/bash
# Gen 2 Save Parser - Usage Examples

SAVE="pokemon_gold.sav"

echo "=== Gen 2 Save Parser Examples ==="
echo

# Basic usage
echo "1. Normal display (trainer + party + boxes)"
echo "   python3 gen2_parser_demo.py $SAVE"
echo

# Summary
echo "2. Quick summary"
echo "   python3 gen2_parser_demo.py $SAVE --summary"
echo

# View specific box
echo "3. View Box 1 in detail"
echo "   python3 gen2_parser_demo.py $SAVE --box 1"
echo

# Dump all
echo "4. Show every Pokémon"
echo "   python3 gen2_parser_demo.py $SAVE --dump-all"
echo

# Search examples
echo "5. Find all Pikachu"
echo "   python3 gen2_parser_demo.py $SAVE --search Pikachu"
echo

echo "6. Find high-level Charizard"
echo "   python3 gen2_parser_demo.py $SAVE --search Charizard --min-level 70"
echo

echo "7. Find shiny Gyarados"
echo "   python3 gen2_parser_demo.py $SAVE --search Gyarados --shiny-only"
echo

echo "8. Find level 50-100 Mewtwo"
echo "   python3 gen2_parser_demo.py $SAVE --search Mewtwo --min-level 50 --max-level 100"
echo

# Analysis
echo "9. Count species duplicates"
echo "   python3 gen2_parser_demo.py $SAVE --species-count"
echo

# Export
echo "10. Export to JSON"
echo "    python3 gen2_parser_demo.py $SAVE --json output.json"
echo

# Version override
echo "11. Force Crystal version"
echo "    python3 gen2_parser_demo.py save.sav --version crystal"
echo

echo "=== Python API Examples ==="
echo

cat << 'PYTHON_EXAMPLE'
from gen2_parser_demo import Gen2SaveParser

# Load save
parser = Gen2SaveParser("pokemon_gold.sav")

# Get trainer info
print(f"Player: {parser.get_player_name()}")
print(f"Money: ₽{parser.get_money():,}")
hours, mins, secs = parser.get_playtime()
print(f"Time: {hours}h {mins}m {secs}s")

# Get party
party = parser.get_party()
for p in party:
    print(f"{p['species']} Lv.{p['level']}")

# Search for shinies
shinies = parser.find_pokemon(shiny_only=True)
print(f"Found {len(shinies)} shiny Pokémon!")

# Count duplicates
counts = parser.get_species_counts()
print(f"Top species: {max(counts, key=counts.get)}")

# Export to JSON
import json
with open("save.json", "w") as f:
    json.dump(parser.export_to_json(), f, indent=2)
PYTHON_EXAMPLE
