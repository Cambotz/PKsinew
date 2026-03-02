#!/usr/bin/env python3

"""
DBbuilder.py — Fetches Gen 3 sprites, item sprites, and metadata from online sources.

Downloads only missing files. Saves everything under data/ with separate folders.
Covers: normal + shiny sprites, item sprites, descriptions, abilities, egg groups,
evolution chains, forms, types, stats, height, and weight.
"""

import json
import os
import time
from typing import Dict, List, Optional

import requests

from config import SPRITES_DIR, GEN3_NORMAL_DIR, GEN3_SHINY_DIR, POKEMON_DB_PATH

# --------- Config ----------
MAX_POKEMON = 386  # up to Emerald
ITEMS_DIR = os.path.join(SPRITES_DIR, "items")

DB_PATH = POKEMON_DB_PATH

# Create directories
for d in (GEN3_NORMAL_DIR, GEN3_SHINY_DIR, ITEMS_DIR):
    os.makedirs(d, exist_ok=True)

# HTTP
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Sinew-PokeFetcher/1.0 (+https://example)"})


# -------------------------------------------------------------------
# Download helper — ONLY downloads if file does NOT already exist
# -------------------------------------------------------------------
def download_file(url: Optional[str], dest_path: str, timeout: float = 10.0) -> bool:
    """Download a file from url to dest_path; skip if the file already exists. Returns True on success."""
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
    """Extract and return the first English flavor-text entry from a PokeAPI species object."""
    for entry in species_data.get("flavor_text_entries", []):
        if entry.get("language", {}).get("name") == "en":
            text = entry.get("flavor_text", "")
            return text.replace("\n", " ").replace("\f", " ").strip()
    return None


# recursion for evolution parsing
def parse_evolution_chain(chain_node: Dict) -> List[Dict]:
    """Recursively parse a PokeAPI evolution-chain node into a flat list of species dicts."""
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
        return [{"base": results[0], "branches": extended}]
    return results


# -------------------------
# Item sprites (Poké Ball, Master Ball, Eggs)
# -------------------------
ITEM_SPRITES = {
    "pokeball": "poke-ball.png",
    "master_ball": "master-ball.png",
    "2km_egg": "2km-egg.png",
    "5km_egg": "5km-egg.png",
    "10km_egg": "10km-egg.png",
}

for _, filename in ITEM_SPRITES.items():
    url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{filename}"
    dest_path = os.path.join(ITEMS_DIR, filename)
    if download_file(url, dest_path):
        print(f"[Item] Downloaded {filename}", flush=True)

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
        key: os.path.join(ITEMS_DIR, filename) for key, filename in ITEM_SPRITES.items()
    }

# -------------------------
# Iterate Pokémon
# -------------------------
for i in range(1, MAX_POKEMON + 1):
    if (ui := globals().get("ui_instance")) and getattr(ui, "cancel_requested", False):
        break
    pid_str = f"{i:03d}"

    db_entry = pokemon_db.get(pid_str, {})
    has_height_weight = (
        db_entry.get("height") is not None and db_entry.get("weight") is not None
    )

    required_files = [
        os.path.join(GEN3_NORMAL_DIR, f"{pid_str}.png"),
        os.path.join(GEN3_SHINY_DIR, f"{pid_str}.png"),
    ]

    if (
        db_entry
        and has_height_weight
        and all(os.path.exists(f) for f in required_files)
    ):
        print(
            f"[{pid_str}] {db_entry.get('name', str(i))}: all files already exist, skipping"
        )
        continue

    try:
        pokemon_url = f"https://pokeapi.co/api/v2/pokemon/{i}/"
        species_url = f"https://pokeapi.co/api/v2/pokemon-species/{i}/"

        p_resp = SESSION.get(pokemon_url, timeout=10)
        if p_resp.status_code != 200:
            print(
                f"[{pid_str}] FAILED pokemon endpoint ({p_resp.status_code})",
                flush=True,
            )
            time.sleep(0.2)
            continue

        p_data = p_resp.json()
        s_resp = SESSION.get(species_url, timeout=10)
        species_data = s_resp.json() if s_resp.status_code == 200 else {}

        name = p_data.get("name")
        display_name = name.capitalize() if name else str(i)

        height = p_data.get("height")  # decimeters
        weight = p_data.get("weight")  # hectograms

        gen3_versions = (
            p_data.get("sprites", {}).get("versions", {}).get("generation-iii", {})
            or {}
        )
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

        abilities = [
            ab.get("ability", {}).get("name", "").replace("-", " ").title()
            for ab in p_data.get("abilities", [])
        ]

        egg_groups = [
            eg.get("name", "").replace("-", " ").title()
            for eg in species_data.get("egg_groups", [])
        ]

        types = [
            t.get("type", {}).get("name", "").title()
            for t in sorted(p_data.get("types", []), key=lambda x: x.get("slot", 0))
        ]

        stats = {s["stat"]["name"]: s["base_stat"] for s in p_data.get("stats", [])}
        forms = [f.get("name") for f in p_data.get("forms", [])]

        evolution_chain_info = None
        evo_url = species_data.get("evolution_chain", {}).get("url")
        if evo_url:
            evo_resp = SESSION.get(evo_url, timeout=10)
            if evo_resp.status_code == 200:
                evolution_chain_info = parse_evolution_chain(
                    evo_resp.json().get("chain", {})
                )

        description = get_english_description(species_data)

        pokemon_db[pid_str] = {
            "id": i,
            "name": display_name,
            "types": types,
            "height": height,
            "weight": weight,
            "description": description,
            "abilities": abilities,
            "egg_groups": egg_groups,
            "forms": forms,
            "stats": stats,
            "evolution_chain": evolution_chain_info,
            "sprites": {
                "gen3_normal": (
                    gen3_normal_path
                    if os.path.exists(gen3_normal_path)
                    else None
                ),
                "gen3_shiny": (
                    gen3_shiny_path
                    if os.path.exists(gen3_shiny_path)
                    else None
                ),
            },
            "games": ["Ruby", "Sapphire", "Emerald", "FireRed", "LeafGreen"],
        }

        parts = []
        if dl_gen3:
            parts.append("gen3")
        if dl_gen3_shiny:
            parts.append("gen3-shiny")

        if parts:
            print(
                f"[{pid_str}] {display_name}: downloaded {', '.join(parts)}, h={height} w={weight}"
            )
        else:
            print(
                f"[{pid_str}] {display_name}: updated metadata, h={height} w={weight}"
            )

        time.sleep(0.15)

    except Exception as e:
        print(f"[{pid_str}] ERROR: {e}")
        time.sleep(0.5)

# Save DB
with open(DB_PATH, "w", encoding="utf-8") as fh:
    json.dump(pokemon_db, fh, indent=2, ensure_ascii=False)

print("\nDone. Database saved to:", DB_PATH)
print("Sprite folders:")
print(" ", GEN3_NORMAL_DIR)
print(" ", GEN3_SHINY_DIR)
print(" ", ITEMS_DIR)
