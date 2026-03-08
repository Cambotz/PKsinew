#!/usr/bin/env python3

"""
sprite_pack_selector.py — Sprite pack definitions for all packs in the PokeAPI/sprites repo.

Download strategy
-----------------
The PokeAPI/sprites GitHub repo does NOT offer per-subfolder zip downloads.
The only bulk download available is the entire repo archive (~300 MB+), which
contains every generation, back sprites, icons, items, and much more that
Sinew doesn't need.

Instead we download sprites individually via raw.githubusercontent.com.
For 386 Pokémon this is 386–772 HTTP requests (normal + shiny), which takes
roughly 1–3 minutes on a reasonable connection.  Files are small (1–30 KB
each), so this is fast in practice.  The downloader skips files that already
exist, so interrupted downloads resume cleanly.

Pack catalogue
--------------
Based on the full directory tree of https://github.com/PokeAPI/sprites

Each pack entry:
  id                   unique string key, persisted in sprite_pack_selection.json
  display_name         shown in the UI list
  description          one-line blurb shown in the preview panel
  preview_normal_url   direct URL for Pikachu (#25) — used for the live preview
  preview_shiny_url    shiny Pikachu URL, or None if no shiny variant exists
  normal_url_pattern   URL pattern for any Pokémon; {id} is replaced with the integer ID
  shiny_url_pattern    shiny URL pattern, or None
  has_shiny            True if the pack has a shiny subfolder
  file_ext             "png", "gif", or "svg" — used when saving files
  note                 optional extra info shown in the UI
"""

_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"

SPRITE_PACKS = [
    # -----------------------------------------------------------------------
    # Generation I
    # -----------------------------------------------------------------------
    {
        "id": "gen1_rb",
        "display_name": "Gen I - Red/Blue",
        "description": "Original Game Boy sprites. Classic monochrome pixel art.",
        "preview_normal_url": f"{_BASE}/versions/generation-i/red-blue/25.png",
        "preview_shiny_url": None,
        "normal_url_pattern": f"{_BASE}/versions/generation-i/red-blue/{{id}}.png",
        "shiny_url_pattern": None,
        "has_shiny": False,
        "file_ext": "png",
        "note": "No shiny variants in Gen I",
    },
    {
        "id": "gen1_rb_gray",
        "display_name": "Gen I - Red/Blue (Gray)",
        "description": "Game Boy sprites in greyscale — the authentic DMG look.",
        "preview_normal_url": f"{_BASE}/versions/generation-i/red-blue/gray/25.png",
        "preview_shiny_url": None,
        "normal_url_pattern": f"{_BASE}/versions/generation-i/red-blue/gray/{{id}}.png",
        "shiny_url_pattern": None,
        "has_shiny": False,
        "file_ext": "png",
        "note": "No shiny variants in Gen I",
    },
    {
        "id": "gen1_yellow",
        "display_name": "Gen I - Yellow",
        "description": "Pokémon Yellow sprites. Pikachu finally looks like Pikachu.",
        "preview_normal_url": f"{_BASE}/versions/generation-i/yellow/25.png",
        "preview_shiny_url": None,
        "normal_url_pattern": f"{_BASE}/versions/generation-i/yellow/{{id}}.png",
        "shiny_url_pattern": None,
        "has_shiny": False,
        "file_ext": "png",
        "note": "No shiny variants in Gen I",
    },
    {
        "id": "gen1_yellow_gbc",
        "display_name": "Gen I - Yellow (GBC)",
        "description": "Yellow sprites with Game Boy Color palette applied.",
        "preview_normal_url": f"{_BASE}/versions/generation-i/yellow/gbc/25.png",
        "preview_shiny_url": None,
        "normal_url_pattern": f"{_BASE}/versions/generation-i/yellow/gbc/{{id}}.png",
        "shiny_url_pattern": None,
        "has_shiny": False,
        "file_ext": "png",
        "note": "No shiny variants in Gen I",
    },
    # -----------------------------------------------------------------------
    # Generation II
    # -----------------------------------------------------------------------
    {
        "id": "gen2_gold",
        "display_name": "Gen II - Gold",
        "description": "Pokémon Gold sprites. First generation with colour.",
        "preview_normal_url": f"{_BASE}/versions/generation-ii/gold/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-ii/gold/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-ii/gold/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-ii/gold/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "gen2_silver",
        "display_name": "Gen II - Silver",
        "description": "Pokémon Silver sprites. Slightly cooler palette than Gold.",
        "preview_normal_url": f"{_BASE}/versions/generation-ii/silver/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-ii/silver/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-ii/silver/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-ii/silver/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "gen2_crystal",
        "display_name": "Gen II - Crystal",
        "description": "Pokémon Crystal sprites. Richer GBC colour palette.",
        "preview_normal_url": f"{_BASE}/versions/generation-ii/crystal/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-ii/crystal/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-ii/crystal/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-ii/crystal/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    # -----------------------------------------------------------------------
    # Generation III
    # -----------------------------------------------------------------------
    {
        "id": "gen3_rs",
        "display_name": "Gen III - Ruby/Sapphire",
        "description": "The original GBA sprites. The OG Gen 3 look.",
        "preview_normal_url": f"{_BASE}/versions/generation-iii/ruby-sapphire/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-iii/ruby-sapphire/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-iii/ruby-sapphire/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-iii/ruby-sapphire/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "gen3_emerald",
        "display_name": "Gen III - Emerald",
        "description": "Pokémon Emerald GBA sprites. Slightly updated from RS.",
        "preview_normal_url": f"{_BASE}/versions/generation-iii/emerald/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-iii/emerald/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-iii/emerald/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-iii/emerald/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "gen3_frlg",
        "display_name": "Gen III - FireRed/LeafGreen",
        "description": "FireRed & LeafGreen GBA sprites. Cleaner Kanto redraws.",
        "preview_normal_url": f"{_BASE}/versions/generation-iii/firered-leafgreen/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-iii/firered-leafgreen/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-iii/firered-leafgreen/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-iii/firered-leafgreen/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    # -----------------------------------------------------------------------
    # Generation IV
    # -----------------------------------------------------------------------
    {
        "id": "gen4_dp",
        "display_name": "Gen IV - Diamond/Pearl",
        "description": "Nintendo DS sprites from Diamond & Pearl. Higher detail.",
        "preview_normal_url": f"{_BASE}/versions/generation-iv/diamond-pearl/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-iv/diamond-pearl/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-iv/diamond-pearl/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-iv/diamond-pearl/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "gen4_platinum",
        "display_name": "Gen IV - Platinum",
        "description": "Pokémon Platinum DS sprites. Subtle refinements over DP.",
        "preview_normal_url": f"{_BASE}/versions/generation-iv/platinum/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-iv/platinum/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-iv/platinum/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-iv/platinum/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "gen4_hgss",
        "display_name": "Gen IV - HeartGold/SoulSilver",
        "description": "HGSS DS sprites. Larger canvas with smoother shading.",
        "preview_normal_url": f"{_BASE}/versions/generation-iv/heartgold-soulsilver/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-iv/heartgold-soulsilver/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-iv/heartgold-soulsilver/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-iv/heartgold-soulsilver/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    # -----------------------------------------------------------------------
    # Generation V
    # -----------------------------------------------------------------------
    {
        "id": "gen5_bw",
        "display_name": "Gen V - Black/White",
        "description": "Crisp DS sprites from Black & White. The last pixel sprites.",
        "preview_normal_url": f"{_BASE}/versions/generation-v/black-white/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-v/black-white/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-v/black-white/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-v/black-white/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "gen5_bw_animated",
        "display_name": "Gen V - BW Animated",
        "description": "Animated GIFs from Black & White. Sprites bounce in battle.",
        "preview_normal_url": f"{_BASE}/versions/generation-v/black-white/animated/25.gif",
        "preview_shiny_url": f"{_BASE}/versions/generation-v/black-white/animated/shiny/25.gif",
        "normal_url_pattern": f"{_BASE}/versions/generation-v/black-white/animated/{{id}}.gif",
        "shiny_url_pattern": f"{_BASE}/versions/generation-v/black-white/animated/shiny/{{id}}.gif",
        "has_shiny": True,
        "file_ext": "gif",
        "note": "Animated GIFs — preview plays in the panel",
    },
    # -----------------------------------------------------------------------
    # Generation VI
    # -----------------------------------------------------------------------
    {
        "id": "gen6_xy",
        "display_name": "Gen VI - X/Y",
        "description": "3DS sprites from X & Y. First 3D games, 2D art still used.",
        "preview_normal_url": f"{_BASE}/versions/generation-vi/x-y/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-vi/x-y/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-vi/x-y/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-vi/x-y/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "gen6_oras",
        "display_name": "Gen VI - ORAS",
        "description": "OmegaRuby/AlphaSapphire 3DS sprites. Gen 3 remakes.",
        "preview_normal_url": f"{_BASE}/versions/generation-vi/omegaruby-alphasapphire/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-vi/omegaruby-alphasapphire/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-vi/omegaruby-alphasapphire/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-vi/omegaruby-alphasapphire/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    # -----------------------------------------------------------------------
    # Generation VII
    # -----------------------------------------------------------------------
    {
        "id": "gen7_sm",
        "display_name": "Gen VII - Sun/Moon",
        "description": "Sun & Moon 3DS sprites. High-res square canvas.",
        "preview_normal_url": f"{_BASE}/versions/generation-vii/sun-moon/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-vii/sun-moon/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-vii/sun-moon/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-vii/sun-moon/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "gen7_usum",
        "display_name": "Gen VII - UltraSun/UltraMoon",
        "description": "USUM 3DS sprites. The last dedicated sprite art from GameFreak.",
        "preview_normal_url": f"{_BASE}/versions/generation-vii/ultra-sun-ultra-moon/25.png",
        "preview_shiny_url": f"{_BASE}/versions/generation-vii/ultra-sun-ultra-moon/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/versions/generation-vii/ultra-sun-ultra-moon/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/versions/generation-vii/ultra-sun-ultra-moon/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    # -----------------------------------------------------------------------
    # Other / Modern
    # -----------------------------------------------------------------------
    {
        "id": "home",
        "display_name": "Pokémon HOME",
        "description": "Clean modern art from Pokémon HOME. Vector-like, transparent BG.",
        "preview_normal_url": f"{_BASE}/other/home/25.png",
        "preview_shiny_url": f"{_BASE}/other/home/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/other/home/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/other/home/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
    },
    {
        "id": "official_artwork",
        "display_name": "Official Artwork",
        "description": "High-res Ken Sugimori artwork. Large transparent PNGs.",
        "preview_normal_url": f"{_BASE}/other/official-artwork/25.png",
        "preview_shiny_url": f"{_BASE}/other/official-artwork/shiny/25.png",
        "normal_url_pattern": f"{_BASE}/other/official-artwork/{{id}}.png",
        "shiny_url_pattern": f"{_BASE}/other/official-artwork/shiny/{{id}}.png",
        "has_shiny": True,
        "file_ext": "png",
        "note": "Large files (~100–500 KB each). Download takes longer.",
    },
    {
        "id": "showdown",
        "display_name": "Showdown Animated",
        "description": "Animated GIFs from Pokémon Showdown. Based on B/W sprites.",
        "preview_normal_url": f"{_BASE}/other/showdown/25.gif",
        "preview_shiny_url": f"{_BASE}/other/showdown/shiny/25.gif",
        "normal_url_pattern": f"{_BASE}/other/showdown/{{id}}.gif",
        "shiny_url_pattern": f"{_BASE}/other/showdown/shiny/{{id}}.gif",
        "has_shiny": True,
        "file_ext": "gif",
        "note": "Animated GIFs — preview plays in the panel",
    },
    {
        "id": "dream_world",
        "display_name": "Dream World (SVG)",
        "description": "Vector SVG art from the Pokémon Dream World browser game.",
        "preview_normal_url": f"{_BASE}/other/dream-world/25.svg",
        "preview_shiny_url": None,
        "normal_url_pattern": f"{_BASE}/other/dream-world/{{id}}.svg",
        "shiny_url_pattern": None,
        "has_shiny": False,
        "file_ext": "svg",
        "note": "SVG format — may not display in all parts of Sinew",
    },
]

# Quick lookup by id
SPRITE_PACK_BY_ID = {p["id"]: p for p in SPRITE_PACKS}

PIKACHU_ID = 25       # Always used for preview
MAX_POKEMON = 386     # Gen 1–3 coverage (up to Emerald)

# Default pack used when no selection has been saved
DEFAULT_PACK_ID = "gen3_emerald"


def get_sprite_url(pack: dict, pokemon_id: int, shiny: bool = False) -> str | None:
    """Return the URL for a specific Pokémon ID from a given pack."""
    pattern_key = "shiny_url_pattern" if shiny else "normal_url_pattern"
    pattern = pack.get(pattern_key)
    if not pattern:
        return None
    return pattern.replace("{id}", str(pokemon_id))


def get_default_pack() -> dict:
    """Return the default sprite pack (Gen III Emerald)."""
    return SPRITE_PACK_BY_ID[DEFAULT_PACK_ID]