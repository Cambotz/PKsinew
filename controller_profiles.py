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
    # ----- Xbox Family -----
    {
        "id": "xbox",
        "description": "Xbox Controller",
        "name_patterns": [
            "xbox", "x-box", "xinput", "microsoft gamepad",
            "microsoft controller", "xbox one", "xbox 360",
            "xbox series", "xbox elite", "xbox wireless",
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
    # ----- PlayStation Family -----
    # DualShock 3 / SIXAXIS
    # SDL GameControllerDB: a:b1, b:b2, x:b0, y:b3, leftshoulder:b4,
    # rightshoulder:b5, back:b8, start:b9
    # Note: Some Linux drivers report DS3 d-pad as buttons 4-7 (older) or
    # use hat. The auto-detect handles this, but we note the common
    # button-dpad variant here for reference.
    {
        "id": "ds3",
        "description": "DualShock 3 / SIXAXIS",
        "name_patterns": [
            "playstation 3", "ps3", "sixaxis", "dualshock 3",
            "sony playstation(r)3",
        ],
        "mapping": {
            "A": [1],      # Cross (b1)
            "B": [2],      # Circle (b2)
            "X": [0],      # Square (b0)
            "Y": [3],      # Triangle (b3)
            "L": [4],      # L1 (b4)
            "R": [5],      # R1 (b5)
            "SELECT": [8], # Select (b8)
            "START": [9],  # Start (b9)
        },
    },
    # DS3 variant where d-pad is reported as buttons (some USB adapters)
    {
        "id": "ds3_dpad_buttons",
        "description": "DualShock 3 (button d-pad)",
        "name_patterns": [
            "sony playstation(r)3 controller",
        ],
        "mapping": {
            "A": [14],     # Cross
            "B": [13],     # Circle
            "X": [15],     # Square
            "Y": [12],     # Triangle
            "L": [10],     # L1
            "R": [11],     # R1
            "SELECT": [0], # Select
            "START": [3],  # Start
            "_dpad_buttons": {
                "up": [4],
                "down": [6],
                "left": [7],
                "right": [5],
            },
        },
    },
    # DualShock 4
    # SDL GameControllerDB: a:b1, b:b2, x:b0, y:b3, leftshoulder:b4,
    # rightshoulder:b5, back:b8, start:b9
    {
        "id": "ds4",
        "description": "DualShock 4",
        "name_patterns": [
            "dualshock 4", "ps4", "playstation 4",
            "wireless controller",  # Generic PS4 name on many systems
            "sony interactive entertainment wireless controller",
        ],
        "mapping": {
            "A": [1],      # Cross (b1)
            "B": [2],      # Circle (b2)
            "X": [0],      # Square (b0)
            "Y": [3],      # Triangle (b3)
            "L": [4],      # L1 (b4)
            "R": [5],      # R1 (b5)
            "SELECT": [8], # Share (b8)
            "START": [9],  # Options (b9)
        },
    },
    # DualSense (PS5)
    # SDL GameControllerDB: a:b1, b:b2, x:b0, y:b3, leftshoulder:b4,
    # rightshoulder:b5, back:b8, start:b9 (same layout as DS4)
    {
        "id": "dualsense",
        "description": "DualSense (PS5)",
        "name_patterns": [
            "dualsense", "ps5", "playstation 5",
        ],
        "mapping": {
            "A": [1],      # Cross (b1)
            "B": [2],      # Circle (b2)
            "X": [0],      # Square (b0)
            "Y": [3],      # Triangle (b3)
            "L": [4],      # L1 (b4)
            "R": [5],      # R1 (b5)
            "SELECT": [8], # Create (b8)
            "START": [9],  # Options (b9)
        },
    },
    # ----- Nintendo Switch -----
    # SDL GameControllerDB positional (not label) mapping:
    # a:b0, b:b1, x:b2, y:b3, leftshoulder:b4, rightshoulder:b5, back:b8, start:b9
    # Note: SDL has two modes - label-based (a:b1,b:b0) and positional (a:b0,b:b1).
    # We use positional since Sinew treats A=confirm (bottom) and B=back (right).
    {
        "id": "switch_pro",
        "description": "Switch Pro Controller",
        "name_patterns": [
            "switch pro", "nintendo switch pro", "pro controller",
        ],
        "mapping": {
            "A": [0],      # A position (bottom face button)
            "B": [1],      # B position (right face button)
            "X": [2],      # X
            "Y": [3],      # Y
            "L": [4],      # L (b4)
            "R": [5],      # R (b5)
            "SELECT": [8], # Minus (b8)
            "START": [9],  # Plus (b9)
        },
    },
    # Joy-Cons (combined or individual in grip)
    {
        "id": "joycon",
        "description": "Nintendo Joy-Con",
        "name_patterns": [
            "joy-con", "joycon",
        ],
        "mapping": {
            "A": [0],
            "B": [1],
            "X": [2],
            "Y": [3],
            "L": [4],
            "R": [5],
            "SELECT": [8],
            "START": [9],
        },
    },
    # ----- 8BitDo Family -----
    {
        "id": "8bitdo_sn30_pro",
        "description": "8BitDo SN30 Pro / Pro 2",
        "name_patterns": [
            "8bitdo sn30 pro", "8bitdo pro 2", "sn30 pro",
            "8bitdo sf30 pro",
        ],
        "mapping": {
            # In XInput mode (most common): same as Xbox
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
    {
        "id": "8bitdo_generic",
        "description": "8BitDo Controller",
        "name_patterns": [
            "8bitdo", "8bit",
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
    # ----- Retro Handhelds (ROCKNIX/ArkOS/etc.) -----
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
    # Anbernic handhelds
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
    # ----- Generic / Linux virtual gamepads -----
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
    # Logitech controllers
    {
        "id": "logitech",
        "description": "Logitech Controller",
        "name_patterns": [
            "logitech", "rumblepad", "f310", "f510", "f710",
        ],
        "mapping": {
            # XInput mode: same as Xbox
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