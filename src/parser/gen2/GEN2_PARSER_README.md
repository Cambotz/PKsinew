# Pokémon Gen 2 Save Parser

Complete save file parser for Pokémon Gold, Silver, and Crystal versions (Gen 2).

## Features

### ✅ Fully Supported

- **All 251 Pokémon** - Complete species data from Bulbasaur to Celebi
- **All 251 Moves** - Every move from Gen 1 + all 86 new Gen 2 moves with max PP
- **All Items** - TMs, HMs, berries, held items, Apricorn balls, and more
- **Party Pokémon** - Up to 6 party members with full stats
- **PC Storage** - All 14 boxes (20 Pokémon each = 280 total capacity)
- **Trainer Info** - Name, rival, ID, money, playtime, badges
- **Pokédex** - Owned/seen counts out of 251
- **Gender Detection** - Calculated from DVs and species ratio
- **Shiny Detection** - DV-based shiny calculation (1/8192 odds)
- **Pokérus** - Strain, days remaining, cured status
- **Unown Forms** - All 26 letter forms (A-Z)
- **Caught Data** - Ball type, level met, time of day
- **DVs/EVs** - Individual Values and Effort Values
- **Friendship** - Happiness values (0-255)
- **Held Items** - What each Pokémon is holding

### 📊 Advanced Features

- **Search** - Find Pokémon by species, level range, shiny status
- **Species Count** - Count duplicates across party + all boxes
- **JSON Export** - Export entire save to structured JSON
- **Box Visualization** - Progress bars for all 14 boxes
- **Summary Stats** - Quick overview of save file

## Installation

**No dependencies required!** Pure Python 3. Completely self-contained.

```bash
# Just copy these two files:
gen2_parser.py          # Data tables and helper functions
gen2_parser_demo.py     # Main parser and CLI

# No need for gen1_parser - Gen 2 parser is standalone!
```

Run directly:
```bash
python3 gen2_parser_demo.py pokemon_gold.sav
```

## Usage

### Basic Usage

```bash
# Display trainer info, party, and box overview
python3 gen2_parser_demo.py pokemon_gold.sav

# View a specific box in detail
python3 gen2_parser_demo.py pokemon_gold.sav --box 1

# Show summary statistics
python3 gen2_parser_demo.py pokemon_gold.sav --summary

# Dump all Pokémon (party + all 14 boxes)
python3 gen2_parser_demo.py pokemon_gold.sav --dump-all
```

### Search & Filter

```bash
# Find all Pikachu
python3 gen2_parser_demo.py pokemon_gold.sav --search Pikachu

# Find high-level Charizard
python3 gen2_parser_demo.py pokemon_gold.sav --search Charizard --min-level 70

# Find shiny Pokémon
python3 gen2_parser_demo.py pokemon_gold.sav --search Gyarados --shiny-only

# Level range search
python3 gen2_parser_demo.py pokemon_gold.sav --search Mewtwo --min-level 50 --max-level 100
```

### Analysis

```bash
# Count how many of each species you have
python3 gen2_parser_demo.py pokemon_gold.sav --species-count

# Export to JSON for external tools
python3 gen2_parser_demo.py pokemon_gold.sav --json output.json
```

### Version Detection

```bash
# Auto-detect from filename (default)
python3 gen2_parser_demo.py pokemon_gold.sav

# Force specific version
python3 gen2_parser_demo.py save.sav --version crystal
```

## Python API

```python
from gen2_parser_demo import Gen2SaveParser

# Initialize parser
parser = Gen2SaveParser("pokemon_gold.sav")

# Trainer info
player = parser.get_player_name()
rival = parser.get_rival_name()
tid = parser.get_trainer_id()
money = parser.get_money()
hours, minutes, seconds = parser.get_playtime()
johto_badges, kanto_badges = parser.get_badges()
owned, seen = parser.get_pokedex_counts()

# Party Pokémon
party = parser.get_party()
for pokemon in party:
    print(f"{pokemon['species']} Lv.{pokemon['level']}")
    print(f"  HP: {pokemon['hp_current']}/{pokemon['hp_max']}")
    print(f"  Stats: Atk={pokemon['attack']} Def={pokemon['defense']}")
    print(f"  DVs: {pokemon['dvs']}")
    print(f"  Shiny: {pokemon['shiny']}")
    print(f"  Moves: {[m['name'] for m in pokemon['moves']]}")

# PC Boxes
box1 = parser.get_box(1)  # Box 1 (1-14)
all_boxes = parser.get_all_boxes()  # All 14 boxes
box_count = parser.get_box_count(5)  # How many in box 5

# Search
results = parser.find_pokemon(
    species_name="Pikachu",
    min_level=20,
    max_level=50,
    shiny_only=True
)

# Statistics
species_counts = parser.get_species_counts()
summary = parser.get_save_summary()

# Export
json_data = parser.export_to_json()
```

## Pokémon Data Structure

Each Pokémon (party or box) is returned as a dict:

```python
{
    'species': 'Pikachu',
    'species_id': 0x19,
    'level': 25,
    'exp': 15625,
    'nickname': 'PIKA',  # or species name if no nickname
    'ot_name': 'ASH',
    'ot_id': 12345,
    'gender': 'M',  # 'M', 'F', or '—' (genderless)
    'shiny': False,
    'held_item': 'Light Ball',  # or None
    'friendship': 255,
    
    # DVs (0-15 each)
    'dvs': {
        'hp': 15,
        'attack': 12,
        'defense': 14,
        'speed': 13,
        'special': 15
    },
    
    # EVs (0-65535 each)
    'evs': {
        'hp': 1000,
        'attack': 500,
        'defense': 800,
        'speed': 1200,
        'special': 600
    },
    
    # Pokérus
    'pokerus': {
        'infected': True,
        'cured': False,
        'strain': 3,
        'days': 2
    },
    
    # Caught info
    'caught': {
        'ball': 'Great Ball',
        'level': 5,
        'time': 'Morning'  # or 'Day', 'Night'
    },
    
    # Moves (up to 4)
    'moves': [
        {
            'name': 'Thunderbolt',
            'id': 0x55,
            'pp_current': 15,
            'pp_max': 15,
            'pp_ups': 0
        }
    ],
    
    # Party-only fields (48-byte structure)
    'status': 0,
    'hp_current': 85,
    'hp_max': 85,
    'attack': 55,
    'defense': 40,
    'speed': 90,
    'sp_attack': 50,
    'sp_defense': 50
}
```

## Gen 2 Save File Structure

```
Total: 32,816 bytes (32 KB)

0x0000-0x1FFF: Bank 0 (8 KB)  - SRAM bank 0
0x2000-0x3FFF: Bank 1 (8 KB)  - Main save data
0x4000-0x5FFF: Bank 2 (8 KB)  - PC Boxes 1-7
0x6000-0x7FFF: Bank 3 (8 KB)  - PC Boxes 8-14
0x8000-0x802F: Extra (48 bytes)
```

**Main Save Data (Bank 1):**
- Player/Rival names
- Trainer ID
- Money (BCD encoded)
- Playtime
- Badges (16 total: 8 Johto + 8 Kanto)
- Pokédex (251 bits owned + 251 bits seen)
- Party Pokémon (6 × 48 bytes)

**PC Boxes (Banks 2-3):**
- 14 boxes total
- 20 Pokémon per box
- Each box = 1,104 bytes:
  - Count (1 byte)
  - Species list (21 bytes with 0xFF terminator)
  - Pokémon data (20 × 32 bytes)
  - OT names (20 × 11 bytes)
  - Nicknames (20 × 11 bytes)

**Pokémon Structures:**
- Box Pokémon: 32 bytes
- Party Pokémon: 48 bytes (32 box + 16 party-only)

## Gen 2 Mechanics

### Shiny Detection

Shiny if: `Def=10 AND Spd=10 AND Spc=10 AND Atk∈{2,3,6,7,10,11,14,15}`

Odds: 1/8192 in wild, but DV requirements mean shinies always have:
- Defense DV = 10
- Speed DV = 10
- Special DV = 10
- Attack DV = 2, 3, 6, 7, 10, 11, 14, or 15

### Gender Calculation

Gender determined by Attack DV vs. species gender ratio:
- **Genderless** - Magnemite, Voltorb, Staryu, legendaries, Unown
- **Always Male** - Nidoran♂, Tauros, Hitmons
- **Always Female** - Nidoran♀, Chansey, Miltank, Jynx, Smoochum
- **87.5% Male** - All starters (Atk DV ≥ 2 = Male)
- **50/50** - Most Pokémon (Atk DV ≥ 8 = Male)

### Unown Forms

26 forms (A-Z) determined by specific DV combination.

### Pokérus

Virus that doubles EV gain:
- Strain 0 = never infected
- Strain 1-15 = infected (random)
- Days 0 = cured (immune, no longer contagious)
- Days 1-15 = active (contagious)

## CLI Options Reference

```
Positional:
  save_file              Path to .sav file

Display Options:
  (no flags)             Normal display (trainer + party + box overview)
  --dump-all             Show all Pokémon in party + all 14 boxes
  --summary              Save file statistics
  --box N                Detailed view of box N (1-14)

Search/Filter:
  --search SPECIES       Find specific species
  --min-level N          Minimum level filter
  --max-level N          Maximum level filter
  --shiny-only           Show only shiny Pokémon
  --species-count        Count duplicates

Export:
  --json FILE            Export to JSON

Other:
  --version gold|silver|crystal    Force game version
```

## Examples

### Complete Pokédex Save

```bash
$ python3 gen2_parser_demo.py pokemon_gold.sav --summary

Save File Summary:

  Game:         Gold
  Trainer:      Mattia♂
  Play Time:    56.0 hours
  Badges:       16/16 (8 Johto + 8 Kanto)
  Pokédex:      251/251 owned, 251/251 seen
  Party:        0/6
  Boxes:        274/280
  Total:        274 Pokémon
```

### Find High-Level Legendaries

```bash
$ python3 gen2_parser_demo.py pokemon_crystal.sav --search Lugia --min-level 50

Found 1 Lugia:
  Box 14     Slot  1: LUGIA (—) Lv. 70
```

### Species Collection Analysis

```bash
$ python3 gen2_parser_demo.py pokemon_silver.sav --species-count

Species Counts (Party + All Boxes):

  Electrode            × 4
  Eevee                × 3
  Spearow              × 2
  Pikachu              × 2
  ...
  Total: 274 Pokémon
```

## Validation

Parser tested and validated against:
- ✅ Pokémon Gold save (274 Pokémon, 16/16 badges, 251/251 Pokédex)
- ✅ All 251 species parsing correctly
- ✅ All 251 moves with correct max PP
- ✅ Gender/shiny/Unown form calculations
- ✅ Party and box storage
- ✅ Search and filter functions
- ✅ JSON export

## Differences from Gen 1

| Feature | Gen 1 | Gen 2 |
|---------|-------|-------|
| Pokémon | 151 | 251 |
| Moves | 165 | 251 |
| PC Boxes | 12 (20 each) | 14 (20 each) |
| Party Structure | 44 bytes | 48 bytes |
| Box Structure | 33 bytes | 32 bytes |
| Badges | 8 | 16 (8 Johto + 8 Kanto) |
| Stats | HP/Atk/Def/Spd/Spc | HP/Atk/Def/Spd/SpA/SpD |
| New Features | — | Gender, Shiny, Held Items, Pokérus, Time of Day |

## Known Limitations

- Stat calculation not yet implemented for box Pokémon (party stats are stored)
- Growth rate mapping incomplete (defaults to medium_fast)
- Crystal-specific features not fully tested

## Credits

- Gen 2 save structure: [Bulbapedia](https://bulbapedia.bulbagarden.net/)
- Character encoding: Same as Gen 1
- Tested with real save files from Pokémon Gold/Silver/Crystal

## License

Public domain. Use freely for your Pokémon projects!
