# Gen 3 Pokemon Save Parser

A modular Python parser for Generation 3 Pokemon save files.

## Supported Games
- Pokemon FireRed, LeafGreen, Ruby, Sapphire, Emerald

## Structure

```
parser/
├── __init__.py         # Package exports
├── constants.py        # Lookup tables, offsets, EXP tables
├── crypto.py           # Decryption, text encoding/decoding
├── pokemon.py          # Party & PC Pokemon parsing
├── trainer.py          # Trainer info, natures, shiny check
├── items.py            # Bag/item parsing
├── save_structure.py   # Save file sections, game detection
└── gen3_parser.py      # Main facade class
```

## Usage

```python
from parser import Gen3SaveParser

parser = Gen3SaveParser("path/to/save.sav")

if parser.loaded:
    print(f"Trainer: {parser.trainer_name}")
    for poke in parser.party_pokemon:
        print(f"  {poke['nickname']} Lv.{poke['level']}")
```

## Migration

Replace your import:
```python
# Old:
from gen3_save_parser import Gen3SaveParser

# New:
from parser import Gen3SaveParser
```

The API is backwards compatible.
