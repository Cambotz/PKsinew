"""
Controller Profiles Database for Sinew
Known controller mappings for auto-detection and automatic configuration.

When a controller is detected, we match its name (and optionally SDL GUID)
against this database to apply the correct button mapping automatically.
Users can still override via the Button Mapper in Settings.

Profiles are matched in order:
  1. Exact GUID match (most specific)
  2. Name substring match (fuzzy but covers variants)
  3. Heuristic based on button/axis count
  4. Xbox-style fallback (most common layout)
"""

import json
import os


# ============================================================================
# KNOWN CONTROLLER PROFILES
# ============================================================================
# Each profile maps GBA buttons to physical controller button indices.
# The key names match ControllerManager.button_map keys.
#
# "name_patterns" is a list of lowercase substrings to match against
# the controller's reported name (case-insensitive).
#
# "guids" is an optional list of exact SDL GUIDs for precise matching.
#
# "description" is for human-readable display in the UI.
#
# D-pad configuration (optional, in the "mapping" dict):
#   "_dpad_buttons": dict mapping direction -> [button indices]
#       For controllers that report d-pad as regular buttons.
#       Example: {"up": [11], "down": [12], "left": [13], "right": [14]}
#
#   "_dpad_axes": list of (x_axis, y_axis) tuples to check
#       For controllers that use non-standard axis indices.
#       Example: [(0, 1), (4, 5)]  -- check left stick AND axes 4/5
#
# If neither is specified, the auto-detection in controller.py will
# try to figure it out based on the controller's capabilities.
# ============================================================================

PROFILES = [
    # ----- Retro Handhelds (ROCKNIX/ArkOS/etc.) -----
    # These embedded Linux devices are NOT in GameControllerDB since they're
    # not USB/Bluetooth gamepads — they use built-in kernel input devices.
    #
    # Powkiddy X55
    {
        "id": "powkiddy_x55",
        "description": "Powkiddy X55",
        "name_patterns": [
            "powkiddy x55", "x55",
            "deeplay-keys",  # Some X55 units report this
        ],
        "mapping": {
            "A": [0],
            "B": [1],
            "X": [2],
            "Y": [3],
            "L": [4],
            "R": [5],
            "SELECT": [6],
            "START": [7],
        },
    },
    # Powkiddy generic (RGB30, RK2023, etc.)
    {
        "id": "powkiddy_generic",
        "description": "Powkiddy Controller",
        "name_patterns": [
            "powkiddy", "rk2023", "rgb30",
        ],
        "mapping": {
            "A": [0],
            "B": [1],
            "X": [2],
            "Y": [3],
            "L": [4],
            "R": [5],
            "SELECT": [6],
            "START": [7],
        },
    },
    # Anbernic handhelds (older models not in GameControllerDB)
    {
        "id": "anbernic",
        "description": "Anbernic Handheld",
        "name_patterns": [
            "anbernic", "rg35xx", "rg353", "rg505", "rg556", "rg28xx",
            "rg351", "rg552", "rg503",
            "gameforce",
        ],
        "mapping": {
            "A": [0],
            "B": [1],
            "X": [2],
            "Y": [3],
            "L": [4],
            "R": [5],
            "SELECT": [6],
            "START": [7],
        },
    },
    # Retroid Pocket
    {
        "id": "retroid",
        "description": "Retroid Pocket",
        "name_patterns": [
            "retroid",
        ],
        "mapping": {
            "A": [0],
            "B": [1],
            "X": [2],
            "Y": [3],
            "L": [4],
            "R": [5],
            "SELECT": [6],
            "START": [7],
        },
    },
    # Miyoo Mini / Trimui etc.
    {
        "id": "miyoo",
        "description": "Miyoo / Trimui",
        "name_patterns": [
            "miyoo", "trimui",
        ],
        "mapping": {
            "A": [0],
            "B": [1],
            "X": [2],
            "Y": [3],
            "L": [4],
            "R": [5],
            "SELECT": [6],
            "START": [7],
        },
    },
    # ----- USB Retro Controllers (user-submitted, NOT in GameControllerDB) -----
    # DragonRise Inc. "Generic USB Joystick" — the chip inside most cheap
    # USB N64, SNES, Genesis, and other retro-style controller adapters.
    # Vendor 0x0079, Product 0x0006.  12 buttons, 4 axes, 1 hat.
    # Button layout confirmed from user-submitted mapping (N64-style pad).
    {
        "id": "dragonrise_usb",
        "description": "USB Retro Pad (DragonRise)",
        "guids": [
            "0300f020790000000600000000000000",  # Windows
            "030000007900000006000000",          # Linux (shorter GUID format)
        ],
        "name_patterns": [
            "generic usb joystick",
            "dragonrise",
        ],
        "mapping": {
            "A": [5],
            "B": [4],
            "X": [2],
            "Y": [3],
            "L": [6],
            "R": [7],
            "SELECT": [0],
            "START": [9],
        },
    },
    # USB Gamepad — vendor 0x081f, product 0xe401.
    # Another common cheap USB gamepad chipset.  10 buttons, 2 axes, 0 hats.
    # D-pad is reported as axes 0 (X) and 1 (Y), no hat.
    {
        "id": "usb_gamepad_081f",
        "description": "USB Gamepad (081F)",
        "guids": [
            "03004d2a1f08000001e4000000000000",  # Windows
            "0300000001f000000100e400",            # Linux (shorter)
        ],
        "name_patterns": [
            "usb gamepad",
        ],
        "mapping": {
            "A": [1],
            "B": [2],
            "X": [0],
            "Y": [3],
            "L": [4],
            "R": [5],
            "SELECT": [8],
            "START": [9],
            "_dpad_axes": [(0, 1)],
        },
    },
    # DragonRise Inc. "USB Gamepad" — vendor 0x0079, product 0x0011.
    # 10 buttons, 5 axes, 0 hats.  D-pad is axis-based: UP/DOWN on axis 4,
    # LEFT/RIGHT on axis 0.  Another cheap USB retro pad variant.
    {
        "id": "dragonrise_usb_0011",
        "description": "USB Gamepad (DragonRise 0011)",
        "guids": [
            "03006ce8790000001100000000000000",  # Windows
            "030000007900000011000000",           # Linux (shorter)
        ],
        "name_patterns": [],  # Too generic — rely on GUID match only
        "mapping": {
            "A": [1],
            "B": [2],
            "X": [0],
            "Y": [3],
            "L": [4],
            "R": [5],
            "SELECT": [8],
            "START": [9],
            "_dpad_axes": [(0, 4)],
        },
    },
    # ----- Generic / catch-all -----
    # Matches controllers not in GameControllerDB and not matching above.
    # Uses standard Xbox-style layout as the most common convention.
    {
        "id": "generic_gamepad",
        "description": "Generic Gamepad",
        "name_patterns": [
            "gamepad", "joystick", "game controller", "usb gamepad",
            "generic", "twin usb", "controller (", "hid gamepad",
        ],
        "mapping": {
            "A": [0],
            "B": [1],
            "X": [2],
            "Y": [3],
            "L": [4],
            "R": [5],
            "SELECT": [6],
            "START": [7],
        },
    },
]

# The absolute fallback mapping when nothing matches
DEFAULT_MAPPING = {
    "A": [0],
    "B": [1],
    "X": [2],
    "Y": [3],
    "L": [4],
    "R": [5],
    "SELECT": [6],
    "START": [7],
}


# ============================================================================
# SDL GAMECONTROLLERDB INTEGRATION
# ============================================================================
# Parses the community-sourced gamecontrollerdb.txt (from
# https://github.com/mdqinc/SDL_GameControllerDB) to provide automatic
# button mappings for thousands of controllers by GUID.
#
# This is used as a fallback AFTER our hand-crafted profiles but BEFORE
# the heuristic/default detection, giving us broad coverage without
# bloating our own profiles list.
# ============================================================================

# Cached DB: maps (guid, platform) -> parsed mapping dict
_gcdb_cache = None
_gcdb_loaded = False


def _get_current_platform():
    """Get the current platform string matching gamecontrollerdb format."""
    import platform as _plat
    system = _plat.system().lower()
    if system == 'windows':
        return 'Windows'
    elif system == 'darwin':
        return 'Mac OS X'
    else:
        return 'Linux'


def _find_gcdb_path():
    """Find gamecontrollerdb.txt in likely locations."""
    candidates = []
    
    try:
        import config as cfg
        if hasattr(cfg, 'EXT_DIR'):
            candidates.append(os.path.join(cfg.EXT_DIR, "gamecontrollerdb.txt"))
    except ImportError:
        pass
    
    candidates.append(os.path.abspath("gamecontrollerdb.txt"))
    
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _parse_sdl_mapping_value(value_str):
    """Parse a single SDL mapping value like 'b0', 'h0.1', 'a2', '-a1', '+a0'.
    
    Also handles the '~' inversion suffix (e.g. 'a3~' = inverted axis 3).
    
    Returns:
        tuple: (type, data) where type is 'button', 'hat', 'axis_dir',
               or 'axis_full'. None if unparseable.
    """
    v = value_str.strip().rstrip('~')  # Strip inversion marker
    
    try:
        if v.startswith('b'):
            return ('button', int(v[1:]))
        
        elif v.startswith('h'):
            parts = v[1:].split('.')
            hat_idx = int(parts[0])
            hat_val = int(parts[1])
            return ('hat', (hat_idx, hat_val))
        
        elif v.startswith('-a') or v.startswith('+a'):
            sign = -1 if v[0] == '-' else 1
            axis_idx = int(v[2:])
            return ('axis_dir', (axis_idx, sign))
        
        elif v.startswith('a'):
            axis_idx = int(v[1:])
            return ('axis_full', axis_idx)
    except (ValueError, IndexError):
        pass
    
    return None


def _convert_sdl_mapping(mapping_str):
    """Convert an SDL GameControllerDB mapping string to Sinew format.
    
    Input: 'a:b0,b:b1,back:b6,dpup:h0.1,...,platform:Windows,'
    Output: Sinew mapping dict with A, B, L, R, SELECT, START, and dpad config
    """
    result = {}
    dpad_buttons = {}
    dpad_axes = set()
    has_dpad = False
    
    # SDL name -> Sinew name mapping
    # SDL uses SNES-style labels: a=bottom, b=right, x=left, y=top
    # For GBA: A=confirm (bottom face), B=back (right face)
    sdl_to_sinew = {
        'a': 'A',           # Bottom face button -> GBA A (confirm)
        'b': 'B',           # Right face button -> GBA B (back)
        'x': 'X',           # Left face button
        'y': 'Y',           # Top face button
        'leftshoulder': 'L',
        'rightshoulder': 'R',
        'back': 'SELECT',
        'start': 'START',
    }
    
    # Hat value -> direction mapping (SDL standard)
    # h0.1=up, h0.2=right, h0.4=down, h0.8=left
    hat_to_direction = {
        1: 'up',
        2: 'right',
        4: 'down',
        8: 'left',
    }
    
    # D-pad SDL names
    dpad_sdl_names = {
        'dpup': 'up',
        'dpdown': 'down',
        'dpleft': 'left',
        'dpright': 'right',
    }
    
    entries = mapping_str.split(',')
    for entry in entries:
        entry = entry.strip()
        if not entry or ':' not in entry:
            continue
        
        key, value = entry.split(':', 1)
        key = key.strip()
        value = value.strip()
        
        if key == 'platform':
            continue
        
        parsed = _parse_sdl_mapping_value(value)
        if parsed is None:
            continue
        
        ptype, pdata = parsed
        
        # Handle face/shoulder buttons
        if key in sdl_to_sinew:
            sinew_name = sdl_to_sinew[key]
            if ptype == 'button':
                result[sinew_name] = [pdata]
        
        # Handle d-pad
        elif key in dpad_sdl_names:
            has_dpad = True
            direction = dpad_sdl_names[key]
            
            if ptype == 'hat':
                # Hat-based d-pad — this is the most common.
                # We don't need to store anything special; controller.py's
                # default hat_map handles standard hat values.
                pass
            
            elif ptype == 'button':
                # Button-based d-pad
                dpad_buttons[direction] = [pdata]
            
            elif ptype == 'axis_dir':
                # Axis-based d-pad (e.g. dpup:-a1)
                axis_idx, sign = pdata
                # Add the axis pair
                if direction in ('left', 'right'):
                    pair_y = axis_idx + 1 if axis_idx % 2 == 0 else axis_idx
                    dpad_axes.add((axis_idx, pair_y))
                else:
                    pair_x = axis_idx - 1 if axis_idx % 2 == 1 else axis_idx
                    dpad_axes.add((pair_x, axis_idx))
    
    # Add d-pad config to result
    if dpad_buttons:
        result['_dpad_buttons'] = dpad_buttons
    if dpad_axes:
        result['_dpad_axes'] = list(dpad_axes)
    
    return result


def _load_gamecontrollerdb():
    """Load and parse gamecontrollerdb.txt, caching the results.
    
    Returns:
        dict: Maps GUID string -> {'name': str, 'mapping': dict}
              Only entries for the current platform are included.
    """
    global _gcdb_cache, _gcdb_loaded
    
    if _gcdb_loaded:
        return _gcdb_cache
    
    _gcdb_loaded = True
    _gcdb_cache = {}
    
    path = _find_gcdb_path()
    if not path:
        return _gcdb_cache
    
    current_platform = _get_current_platform()
    count = 0
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Check platform filter
                if f'platform:{current_platform},' not in line:
                    continue
                
                # Parse: GUID,Name,mappings...,platform:XXX,
                parts = line.split(',', 2)
                if len(parts) < 3:
                    continue
                
                guid = parts[0].strip()
                name = parts[1].strip()
                mapping_str = parts[2]
                
                if not guid or not name:
                    continue
                
                mapping = _convert_sdl_mapping(mapping_str)
                if mapping:
                    _gcdb_cache[guid] = {
                        'name': name,
                        'mapping': mapping,
                    }
                    count += 1
        
        if count > 0:
            print(f"[ControllerProfiles] Loaded {count} mappings from {os.path.basename(path)} ({current_platform})")
    except Exception as e:
        print(f"[ControllerProfiles] Error loading gamecontrollerdb.txt: {e}")
    
    return _gcdb_cache


def lookup_gamecontrollerdb(guid):
    """Look up a controller GUID in the GameControllerDB.
    
    Args:
        guid: SDL GUID string
        
    Returns:
        dict with 'name', 'mapping' if found, None otherwise
    """
    db = _load_gamecontrollerdb()
    return db.get(guid)


# ============================================================================
# PROFILE MATCHING
# ============================================================================

def identify_controller(name, guid=None, num_buttons=0, num_axes=0, num_hats=0):
    """
    Identify a controller and return the best matching profile.
    
    Args:
        name: Controller name string from pygame (joy.get_name())
        guid: Optional SDL GUID string (joy.get_guid() in pygame 2.x)
        num_buttons: Number of buttons reported
        num_axes: Number of axes reported
        num_hats: Number of hats reported
    
    Returns:
        dict with keys:
            "id": profile id string
            "description": human-readable name
            "mapping": button mapping dict
            "match_type": "guid", "name", "heuristic", or "default"
    """
    name_lower = (name or "").lower().strip()
    
    # Pass 1: Try GUID match (most precise)
    if guid:
        for profile in PROFILES:
            if guid in profile.get("guids", []):
                return {
                    "id": profile["id"],
                    "description": profile["description"],
                    "mapping": dict(profile["mapping"]),
                    "match_type": "guid",
                }
    
    # Pass 2: Try name substring match
    # We iterate in order so more specific patterns (e.g. "dualshock 4")
    # are checked before generic ones (e.g. "wireless controller").
    if name_lower:
        for profile in PROFILES:
            for pattern in profile["name_patterns"]:
                if pattern in name_lower:
                    return {
                        "id": profile["id"],
                        "description": profile["description"],
                        "mapping": dict(profile["mapping"]),
                        "match_type": "name",
                    }
    
    # Pass 2.5: Try GameControllerDB (community database with ~2000+ entries)
    if guid:
        gcdb_result = lookup_gamecontrollerdb(guid)
        if gcdb_result:
            return {
                "id": "gcdb",
                "description": gcdb_result["name"],
                "mapping": dict(gcdb_result["mapping"]),
                "match_type": "gcdb",
            }
    
    # Pass 3: Heuristic based on button/axis count
    # PS4/PS5 controllers typically report 13+ buttons
    # Most Xbox controllers report 11 buttons
    # Nintendo Switch Pro reports 15+ buttons
    if num_buttons >= 13 and num_axes >= 4:
        # Likely a modern controller, use Xbox-style as safest bet
        return {
            "id": "heuristic_modern",
            "description": f"Detected Gamepad ({num_buttons}btn/{num_axes}ax)",
            "mapping": dict(DEFAULT_MAPPING),
            "match_type": "heuristic",
        }
    
    if num_buttons >= 8:
        return {
            "id": "heuristic_standard",
            "description": f"Standard Gamepad ({num_buttons}btn)",
            "mapping": dict(DEFAULT_MAPPING),
            "match_type": "heuristic",
        }
    
    # Pass 4: Default fallback
    return {
        "id": "default",
        "description": "Unknown Controller",
        "mapping": dict(DEFAULT_MAPPING),
        "match_type": "default",
    }


def get_profile_by_id(profile_id):
    """Look up a profile by its ID string."""
    for profile in PROFILES:
        if profile["id"] == profile_id:
            return profile
    return None


# ============================================================================
# PER-CONTROLLER SAVED PROFILES
# ============================================================================
# Saved in sinew_settings.json under "controller_profiles" keyed by
# controller name (since GUID isn't always available).
#
# Format:
# {
#     "controller_profiles": {
#         "Xbox Wireless Controller": {
#             "profile_id": "xbox",
#             "mapping": { "A": [0], "B": [1], ... },
#             "guid": "optional-guid-string"
#         },
#         ...
#     },
#     "controller_mapping": { ... }  // legacy flat mapping, still supported
# }
# ============================================================================

def _get_settings_path():
    """Get the path to sinew_settings.json"""
    try:
        import config as cfg
        if hasattr(cfg, 'SETTINGS_FILE'):
            return cfg.SETTINGS_FILE
        elif hasattr(cfg, 'BASE_DIR'):
            return os.path.join(cfg.BASE_DIR, "sinew_settings.json")
    except ImportError:
        pass
    return "sinew_settings.json"


def load_saved_profile(controller_name, guid=None):
    """
    Load a saved controller profile from settings.
    
    Args:
        controller_name: The controller's reported name
        guid: Optional SDL GUID
    
    Returns:
        dict with mapping if found, None otherwise
    """
    config_file = _get_settings_path()
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            profiles = data.get("controller_profiles", {})
            
            # Try exact name match first
            if controller_name in profiles:
                saved = profiles[controller_name]
                return {
                    "id": saved.get("profile_id", "custom"),
                    "description": f"Saved: {controller_name}",
                    "mapping": saved.get("mapping", {}),
                    "match_type": "saved",
                }
            
            # Try GUID match
            if guid:
                for name, saved in profiles.items():
                    if saved.get("guid") == guid:
                        return {
                            "id": saved.get("profile_id", "custom"),
                            "description": f"Saved: {name}",
                            "mapping": saved.get("mapping", {}),
                            "match_type": "saved",
                        }
    except Exception as e:
        print(f"[ControllerProfiles] Error loading saved profile: {e}")
    
    return None


def save_controller_profile(controller_name, mapping, profile_id="custom", guid=None):
    """
    Save a controller profile to settings.
    
    Args:
        controller_name: The controller's reported name
        mapping: Button mapping dict
        profile_id: Profile ID that was the base
        guid: Optional SDL GUID
    """
    config_file = _get_settings_path()
    try:
        data = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
        
        if "controller_profiles" not in data:
            data["controller_profiles"] = {}
        
        profile_data = {
            "profile_id": profile_id,
            "mapping": mapping,
        }
        if guid:
            profile_data["guid"] = guid
        
        data["controller_profiles"][controller_name] = profile_data
        
        # Also write to legacy "controller_mapping" for backward compatibility
        data["controller_mapping"] = mapping
        
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"[ControllerProfiles] Saved profile for '{controller_name}' (base: {profile_id})")
        return True
    except Exception as e:
        print(f"[ControllerProfiles] Error saving profile: {e}")
        return False


def resolve_mapping(controller_name, guid=None, num_buttons=0, num_axes=0, num_hats=0):
    """
    The main entry point: figure out what mapping to use for a controller.
    
    Priority:
      1. User-saved profile for this exact controller
      2. Known profile from the built-in database
      3. Legacy flat "controller_mapping" from settings
      4. Xbox-style default
    
    Args:
        controller_name: Controller name from pygame
        guid: Optional SDL GUID
        num_buttons: Number of buttons
        num_axes: Number of axes
        num_hats: Number of hats
    
    Returns:
        dict with "id", "description", "mapping", "match_type"
    """
    # 1. Check for saved per-controller profile
    saved = load_saved_profile(controller_name, guid)
    if saved and saved.get("mapping"):
        print(f"[ControllerProfiles] Using saved profile for '{controller_name}'")
        return saved
    
    # 2. Check built-in database
    detected = identify_controller(controller_name, guid, num_buttons, num_axes, num_hats)
    if detected["match_type"] in ("guid", "name"):
        print(f"[ControllerProfiles] Auto-detected as '{detected['description']}' "
              f"(match: {detected['match_type']})")
        return detected
    
    # 3. Check legacy flat mapping in settings
    config_file = _get_settings_path()
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            if "controller_mapping" in data:
                legacy_map = data["controller_mapping"]
                # Validate it has at least A and B
                if "A" in legacy_map and "B" in legacy_map:
                    print(f"[ControllerProfiles] Using legacy controller_mapping from settings")
                    return {
                        "id": "legacy",
                        "description": "Saved Mapping (legacy)",
                        "mapping": legacy_map,
                        "match_type": "legacy",
                    }
    except Exception:
        pass
    
    # 4. Fall back to detected (heuristic or default)
    print(f"[ControllerProfiles] Using {detected['match_type']} mapping for '{controller_name}'")
    return detected


def get_all_profile_names():
    """Get a list of all known profile descriptions for display."""
    return [p["description"] for p in PROFILES]