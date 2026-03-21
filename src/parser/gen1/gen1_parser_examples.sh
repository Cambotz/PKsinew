#!/bin/bash
# Gen 1 Parser Usage Examples

SAVE="pokemon_red.sav"

echo "=== Pokémon Gen 1 Save Parser Examples ==="
echo

echo "1. Normal display (default)"
echo "   python3 gen1_parser_demo.py $SAVE"
echo

echo "2. Dump all Pokémon"
echo "   python3 gen1_parser_demo.py $SAVE --dump-all"
echo

echo "3. Show summary statistics"
echo "   python3 gen1_parser_demo.py $SAVE --summary"
echo

echo "4. Search for specific species"
echo "   python3 gen1_parser_demo.py $SAVE --search Pikachu"
echo

echo "5. Search with level filter"
echo "   python3 gen1_parser_demo.py $SAVE --search Mewtwo --min-level 50"
echo

echo "6. Count species"
echo "   python3 gen1_parser_demo.py $SAVE --species-count"
echo

echo "7. Export to JSON"
echo "   python3 gen1_parser_demo.py $SAVE --json export.json"
echo

