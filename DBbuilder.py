#!/usr/bin/env python3
"""
Fetch Gen3 sprites (normal + shiny), Gen8 icons, item sprites (Poké Ball, Master Ball, Eggs),
and metadata (description, abilities, egg groups, evolution chain, forms, types, stats, height, weight).
Only downloads missing files and metadata.
Saves everything under data/ with separate folders.
"""

import requests
import json
import os
import time
from typing import List, Dict, Optional

# --------- Config ----------
MAX_POKEMON = 386             # up to Emerald
DATA_DIR = "data"
SPRITES_DIR = os.path.join(DATA_DIR, "sprites")
GEN3_NORMAL_DIR = os.path.join(SPRITES_DIR, "gen3", "normal")
GEN3_SHINY_DIR = os.path.join(SPRITES_DIR, "gen3", "shiny")
GEN8_ICONS_DIR = os.path.join(SPRITES_DIR, "gen8", "icons")
ITEMS_DIR = os.path.join(SPRITES_DIR, "items")

DB_PATH = os.path.join(DATA_DIR, "pokemon_db.json")

# Create directories
for d in (GEN3_NORMAL_DIR, GEN3_SHINY_DIR, GEN8_ICONS_DIR, ITEMS_DIR):
    os.makedirs(d, exist_ok=True)

# HTTP
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Sinew-PokeFetcher/1.0 (+https://example)"})

# -------------------------------------------------------------------
# Download helper — ONLY downloads if file does NOT already exist
# -------------------------------------------------------------------
def download_file(url: Optional[str], dest_path: str, timeout: float = 10.0) -> bool:
    if not url or os.path.exists(dest_path):
        return False
    try:
        r = SESSION.get(url, timeout=timeout)
        if r.status_code == 200 and r.content:
            with open(dest_path, "wb") as fh:
                fh.write(r.content)
            return True
        return False
    except Exception:
        return False

# extract first english flavor text from species object
def get_english_description(species_data: Dict) -> Optional[str]:
    for entry in species_data.get("flavor_text_entries", []):
        if entry.get("language", {}).get("name") == "en":
            text = entry.get("flavor_text", "")
            return text.replace("\n", " ").replace("\f", " ").strip()
    return None

# recursion for evolution parsing
def parse_evolution_chain(chain_node: Dict) -> List[Dict]:
    results = []
    species = chain_node.get("species", {})
    name = species.get("name")
    url = species.get("url", "")
    try:
        pid = int(url.rstrip("/").split("/")[-1])
    except Exception:
        pid = None
    results.append({"name": name, "species_id": pid})

    evolves_to = chain_node.get("evolves_to", []) or []
    if evolves_to:
        extended = []
        for evo in evolves_to:
            tail = parse_evolution_chain(evo)
            extended.append(tail)
        if len(extended) == 1:
            return [*results, *extended[0][1:]]
        else:
            return [{"base": results[0], "branches": extended}]
    return results

# -------------------------
# Corrected item sprites (Poké Ball, Master Ball, 2km/5km/10km Eggs)
# -------------------------
ITEM_SPRITES = {
    "pokeball": "poke-ball.png",
    "master_ball": "master-ball.png",
    "2km_egg": "2km-egg.png",
    "5km_egg": "5km-egg.png",
    "10km_egg": "10km-egg.png"
}

for key, filename in ITEM_SPRITES.items():
    url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{filename}"
    dest_path = os.path.join(ITEMS_DIR, filename)
    if download_file(url, dest_path):
        print(f"[Item] Downloaded {filename}")

# -------------------------
# Load existing DB if it exists
# -------------------------
if os.path.exists(DB_PATH):
    with open(DB_PATH, "r", encoding="utf-8") as fh:
        pokemon_db = json.load(fh)
else:
    pokemon_db = {}

# Ensure item sprites are in DB
if "items" not in pokemon_db:
    pokemon_db["items"] = {
        key: f"sprites/items/{filename}" for key, filename in ITEM_SPRITES.items()
    }

# -------------------------
# Iterate Pokémon
# -------------------------
for i in range(1, MAX_POKEMON + 1):
    pid_str = f"{i:03d}"

    # Check if DB already has this Pokémon with height/weight and all files exist
    db_entry = pokemon_db.get(pid_str, {})
    has_height_weight = db_entry.get("height") is not None and db_entry.get("weight") is not None
    files_exist = True
    required_files = [
        os.path.join(GEN3_NORMAL_DIR, f"{pid_str}.png"),
        os.path.join(GEN3_SHINY_DIR, f"{pid_str}.png"),
        os.path.join(GEN8_ICONS_DIR, f"{pid_str}.png")
    ]
    for f in required_files:
        if not os.path.exists(f):
            files_exist = False
            break

    if db_entry and files_exist and has_height_weight:
        print(f"[{pid_str}] {db_entry.get('name', str(i))}: all files already exist, skipping")
        continue

    # Fetch from API
    try:
        pokemon_url = f"https://pokeapi.co/api/v2/pokemon/{i}/"
        species_url = f"https://pokeapi.co/api/v2/pokemon-species/{i}/"

        p_resp = SESSION.get(pokemon_url, timeout=10)
        if p_resp.status_code != 200:
            print(f"[{pid_str}] FAILED pokemon endpoint ({p_resp.status_code})")
            time.sleep(0.2)
            continue
        p_data = p_resp.json()

        s_resp = SESSION.get(species_url, timeout=10)
        species_data = s_resp.json() if s_resp.status_code == 200 else {}

        name = p_data.get("name")
        display_name = name.capitalize() if name else str(i)

        # ------------------------------------------------------
        # Height and Weight (from PokeAPI)
        # height is in decimeters, weight is in hectograms
        # ------------------------------------------------------
        height = p_data.get("height")  # decimeters (e.g., 4 = 0.4m)
        weight = p_data.get("weight")  # hectograms (e.g., 60 = 6.0kg)

        # ------------------------------------------------------
        # Gen 3 sprite URLs (emerald > FRLG > RS)
        # ------------------------------------------------------
        gen3_versions = p_data.get("sprites", {}).get("versions", {}).get("generation-iii", {}) or {}
        gen3_emerald = gen3_versions.get("emerald") or {}
        gen3_frlg = gen3_versions.get("firered-leafgreen") or {}
        gen3_rs = gen3_versions.get("ruby-sapphire") or {}

        gen3_url_normal = (
            gen3_emerald.get("front_default")
            or gen3_frlg.get("front_default")
            or gen3_rs.get("front_default")
        )
        gen3_url_shiny = (
            gen3_emerald.get("front_shiny")
            or gen3_frlg.get("front_shiny")
            or gen3_rs.get("front_shiny")
        )

        gen3_normal_path = os.path.join(GEN3_NORMAL_DIR, f"{pid_str}.png")
        gen3_shiny_path = os.path.join(GEN3_SHINY_DIR, f"{pid_str}.png")

        dl_gen3 = download_file(gen3_url_normal, gen3_normal_path)
        dl_gen3_shiny = download_file(gen3_url_shiny, gen3_shiny_path)

        # ------------------------------------------------------
        # Gen 8 icon
        # ------------------------------------------------------
        gen8_icon_path = os.path.join(GEN8_ICONS_DIR, f"{pid_str}.png")
        gen8_icon_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-viii/icons/{i}.png"
        dl_gen8_icon = download_file(gen8_icon_url, gen8_icon_path)

        # -------------------------
        # Abilities
        # -------------------------
        abilities = [
            ab.get("ability", {}).get("name", "").replace("-", " ").title()
            for ab in p_data.get("abilities", [])
        ]

        # -------------------------
        # Egg groups
        # -------------------------
        egg_groups = [
            eg.get("name", "").replace("-", " ").title()
            for eg in species_data.get("egg_groups", [])
        ]

        # -------------------------
        # Types
        # -------------------------
        types = [
            t.get("type", {}).get("name", "").title()
            for t in sorted(p_data.get("types", []), key=lambda x: x.get("slot", 0))
        ]

        # -------------------------
        # Stats
        # -------------------------
        stats = {s["stat"]["name"]: s["base_stat"] for s in p_data.get("stats", [])}

        # -------------------------
        # Forms
        # -------------------------
        forms = [f.get("name") for f in p_data.get("forms", [])]

        # -------------------------
        # Evolution chain
        # -------------------------
        evolution_chain_info = None
        evo_url = species_data.get("evolution_chain", {}).get("url")
        if evo_url:
            try:
                evo_resp = SESSION.get(evo_url, timeout=10)
                if evo_resp.status_code == 200:
                    evolution_chain_info = parse_evolution_chain(evo_resp.json().get("chain", {}))
            except Exception:
                evolution_chain_info = None

        # -------------------------
        # Description
        # -------------------------
        description = get_english_description(species_data)

        # -------------------------
        # Build DB entry
        # -------------------------
        pokemon_db[pid_str] = {
            "id": i,
            "name": display_name,
            "types": types,
            "height": height,      # in decimeters
            "weight": weight,      # in hectograms
            "description": description,
            "abilities": abilities,
            "egg_groups": egg_groups,
            "forms": forms,
            "stats": stats,
            "evolution_chain": evolution_chain_info,
            "sprites": {
                "gen3_normal": f"sprites/gen3/normal/{pid_str}.png" if os.path.exists(gen3_normal_path) else None,
                "gen3_shiny": f"sprites/gen3/shiny/{pid_str}.png" if os.path.exists(gen3_shiny_path) else None,
                "gen8_icon": f"sprites/gen8/icons/{pid_str}.png" if os.path.exists(gen8_icon_path) else None,
            },
            "games": ["Ruby", "Sapphire", "Emerald", "FireRed", "LeafGreen"]
        }

        # log
        parts = []
        if dl_gen3: parts.append("gen3")
        if dl_gen3_shiny: parts.append("gen3-shiny")
        if dl_gen8_icon: parts.append("gen8-icon")

        if parts:
            print(f"[{pid_str}] {display_name}: downloaded {', '.join(parts)}, h={height} w={weight}")
        else:
            print(f"[{pid_str}] {display_name}: updated metadata, h={height} w={weight}")

        time.sleep(0.15)

    except Exception as e:
        print(f"[{pid_str}] ERROR: {e}")
        time.sleep(0.5)
        continue

# Save DB
with open(DB_PATH, "w", encoding="utf-8") as fh:
    json.dump(pokemon_db, fh, indent=2, ensure_ascii=False)

print("\nDone. Database saved to:", DB_PATH)
print("Sprite folders:")
print(" ", GEN3_NORMAL_DIR)
print(" ", GEN3_SHINY_DIR)
print(" ", GEN8_ICONS_DIR)
print(" ", ITEMS_DIR)