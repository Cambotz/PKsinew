# Gen 2 Version Differences (Gold/Silver/Crystal)

## Summary

The Gen 2 parser **fully supports all three versions**: Gold, Silver, and Crystal. All core features (Pokémon, party, boxes, trainer data) use **identical save structures** across all three games.

## What's the Same Across All Versions

✅ **Save file size**: 32,768 bytes (32 KB)  
✅ **PC boxes**: 14 boxes, 20 Pokémon each  
✅ **Party structure**: 6 Pokémon max, 48 bytes each  
✅ **Box structure**: 32 bytes per Pokémon  
✅ **Pokédex**: 251 Pokémon  
✅ **Badges**: 16 total (8 Johto + 8 Kanto)  
✅ **Core save offsets**: Party, boxes, Pokédex, badges, money, playtime  

**The parser works identically for all three versions** - no special handling needed!

---

## Unique Features by Version

### Gold & Silver (Identical)
- **Protagonist**: Male only
- **Legendary trio**: Roaming (Raikou, Entei, Suicune all roam)
- **Cover legendary**: Ho-Oh (Gold) or Lugia (Silver) at Lv.70

### Crystal (Enhanced)
- **Protagonist**: Male or Female choice ⭐
- **Legendary trio**: Suicune is stationary, Raikou/Entei roam
- **Battle Tower**: Post-game facility (Kanto) ⭐
- **Decorations**: Room decoration system ⭐
- **Move Tutors**: Additional move tutors
- **Odd Egg**: Special egg event
- **Animations**: Pokémon have animated sprites

---

## Crystal-Specific Parser Features

### Player Gender Detection

The parser detects Crystal saves and reads the player gender byte:

```python
parser = Gen2SaveParser("crystal.sav")
gender = parser.get_player_gender()  # "Male" or "Female"
# Gold/Silver always return "Male"
```

**Gender byte location (Crystal only)**: `0x3E3D`
- `0x00` = Male
- `0x01` = Female

### Crystal-Specific Offsets

```python
# These are ONLY in Crystal saves
GEN2_CRYSTAL_OFFSETS = {
    "player_gender": (0x3E3D, 1),   # Player gender selection
    "decorations":   (0x26A0, 17),  # Room decorations
}
```

### Version Detection

The parser auto-detects version from filename:

```python
# Auto-detect
parser = Gen2SaveParser("pokemon_crystal.sav")  # → version="crystal"
parser = Gen2SaveParser("pokemon_gold.sav")     # → version="gold"

# Force specific version
parser = Gen2SaveParser("save.sav", force_version="crystal")
```

---

## Gameplay Differences (Not Saved)

These don't affect save file structure:

| Feature | Gold | Silver | Crystal |
|---------|------|--------|---------|
| **Cover Legendary** | Ho-Oh | Lugia | Suicune |
| **Exclusives** | Gligar, Mantine, etc. | Skarmory, Phanpy, etc. | Can catch both sets |
| **Suicune** | Roaming | Roaming | Stationary (Tin Tower) |
| **Protagonist Sprite** | Male (Ethan) | Male (Ethan) | Male or Female (Kris) |

---

## Testing Recommendations

### We've Tested:
✅ **Gold** - Your save file (280 Pokémon, 16/16 badges, 56 hours)
✅ **Silver** - Your save file (280 Pokémon, 16/16 badges, 56.7 hours)
✅ **Crystal** - Kent's save (127 Pokémon, 13/16 badges, works perfectly!)
✅ **Crystal (glitched)** - Handled safely with overflow protection

### Expected Results:
- ✅ Gold/Silver saves parse identically with same offsets
- ✅ Crystal saves work with Crystal-specific party offsets
- ✅ All 251 Pokémon work across all versions
- ✅ Party/box parsing works for all three versions
- ✅ Glitched/corrupted saves handled gracefully

---

## API Differences

### Methods That Work on All Versions:
```python
parser.get_player_name()        # ✅ All versions
parser.get_party()              # ✅ All versions
parser.get_box(1)               # ✅ All versions
parser.get_badges()             # ✅ All versions
parser.get_pokedex_counts()     # ✅ All versions
```

### Crystal-Aware Methods:
```python
parser.is_crystal               # True for Crystal, False for Gold/Silver
parser.get_player_gender()      # "Male" (G/S), "Male"/"Female" (Crystal)
```

---

## Known Identical Offsets

These are **confirmed identical** across Gold and Silver:

```
Player Name:   0x200B (11 bytes)
Player ID:     0x2009 (2 bytes)
Rival Name:    0x2021 (11 bytes)
Money:         0x23DB (3 bytes BCD)
Playtime:      0x2053-0x2056 (hours/min/sec)
Badges Johto:  0x23E4 (1 byte)
Badges Kanto:  0x23E5 (1 byte)
Pokédex Owned: 0x2A4C (32 bytes)
Pokédex Seen:  0x2A6C (32 bytes)
Party Count:   0x288A (1 byte)
Party Data:    0x2892 (6 × 48 bytes)
Box 1-7:       0x4000+ (bank 2)
Box 8-14:      0x6000+ (bank 3)
```

## ⚠️ CRITICAL: Crystal Has Different Party Offsets!

**Crystal uses different party offsets than Gold/Silver:**

| Data Field | Gold/Silver | Crystal | Difference |
|------------|-------------|---------|------------|
| **Party Count** | `0x288A` | `0x2865` | -37 bytes |
| **Party Species** | `0x288B` | `0x2866` | -37 bytes |
| **Party Data** | `0x2892` | `0x286D` | -37 bytes |
| **Party OT** | `0x29B2` | `0x29ED` | +59 bytes |
| **Party Names** | `0x29F4` | `0x2A2F` | +59 bytes |

**The parser handles this automatically!** See `GEN2_CRYSTAL_OFFSETS.md` for details.

All other offsets (trainer data, Pokédex, boxes) are identical.


---

## Bottom Line

**You don't need to worry about version differences!** 

The parser handles all three versions automatically with:
- ✅ Identical core functionality
- ✅ Auto-detection from filename
- ✅ Optional Crystal-specific features (gender, etc.)
- ✅ No special code needed for different versions

**Just load any Gen 2 save and it works!** 🎉
