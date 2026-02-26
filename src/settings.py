"""
Sinew Main Setup / Settings
Tabbed settings modal with controller support
"""

import json
import os
import time
import webbrowser

import pygame

import ui_colors  # Import module for dynamic theme colors
from config import DATA_DIR, EXT_DIR, FONT_PATH, IS_HANDHELD, POKEMON_DB_PATH, SETTINGS_FILE
from controller import NavigableList, get_controller


def load_sinew_settings():
    """Load settings from sinew_settings.json"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_sinew_settings(data):
    """Save settings to sinew_settings.json"""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Settings] Failed to save settings: {e}")


# Try to import button mapper
try:
    from button_mapper import ButtonMapper

    BUTTON_MAPPER_AVAILABLE = True
except ImportError:
    BUTTON_MAPPER_AVAILABLE = False

# Try to import themes screen
try:
    from themes_screen import ThemesScreen

    THEMES_SCREEN_AVAILABLE = True
except ImportError:
    THEMES_SCREEN_AVAILABLE = False


# -----------------------------
# Confirmation Popup
# -----------------------------
class ConfirmationPopup:
    """Simple Yes/No confirmation popup"""

    def __init__(self, width, height, message, on_confirm=None, on_cancel=None):
        self.width = width
        self.height = height
        self.message = message
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.visible = True

        # Selection: 0 = Yes, 1 = No
        self.selected = 1  # Default to No for safety

        # Fonts
        self.font_text = pygame.font.Font(FONT_PATH, 12)
        self.font_small = pygame.font.Font(FONT_PATH, 10)

    def handle_controller(self, ctrl):
        """Handle controller input"""
        # Navigate left/right between Yes/No
        if ctrl.is_dpad_just_pressed("left") or ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("left")
            ctrl.consume_dpad("right")
            self.selected = 1 - self.selected  # Toggle between 0 and 1
            return True

        # Confirm selection
        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            self.visible = False
            if self.selected == 0 and self.on_confirm:
                self.on_confirm()
            elif self.selected == 1 and self.on_cancel:
                self.on_cancel()
            return True

        # Cancel (B always cancels)
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.visible = False
            if self.on_cancel:
                self.on_cancel()
            return True

        return False

    def draw(self, surf):
        """Draw the confirmation popup"""
        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))

        # Popup box
        box_w, box_h = 280, 120
        box_x = (self.width - box_w) // 2
        box_y = (self.height - box_h) // 2
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)

        pygame.draw.rect(surf, ui_colors.COLOR_BG, box_rect, border_radius=10)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, box_rect, 3, border_radius=10)

        # Message
        msg_surf = self.font_text.render(self.message, True, ui_colors.COLOR_TEXT)
        msg_rect = msg_surf.get_rect(centerx=self.width // 2, centery=box_y + 35)
        surf.blit(msg_surf, msg_rect)

        # Yes/No buttons
        btn_y = box_y + 75
        btn_width = 80
        btn_height = 28
        btn_spacing = 30

        # Yes button
        yes_x = self.width // 2 - btn_width - btn_spacing // 2
        yes_rect = pygame.Rect(yes_x, btn_y, btn_width, btn_height)
        yes_selected = self.selected == 0

        if yes_selected:
            pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, yes_rect, border_radius=5)
            pygame.draw.rect(
                surf, ui_colors.COLOR_SUCCESS, yes_rect, 2, border_radius=5
            )
            yes_color = ui_colors.COLOR_SUCCESS
        else:
            pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, yes_rect, border_radius=5)
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, yes_rect, 2, border_radius=5)
            yes_color = ui_colors.COLOR_TEXT

        yes_surf = self.font_text.render("Yes", True, yes_color)
        yes_text_rect = yes_surf.get_rect(center=yes_rect.center)
        surf.blit(yes_surf, yes_text_rect)

        # No button
        no_x = self.width // 2 + btn_spacing // 2
        no_rect = pygame.Rect(no_x, btn_y, btn_width, btn_height)
        no_selected = self.selected == 1

        if no_selected:
            pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, no_rect, border_radius=5)
            pygame.draw.rect(surf, ui_colors.COLOR_ERROR, no_rect, 2, border_radius=5)
            no_color = ui_colors.COLOR_ERROR
        else:
            pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, no_rect, border_radius=5)
            pygame.draw.rect(surf, ui_colors.COLOR_BORDER, no_rect, 2, border_radius=5)
            no_color = ui_colors.COLOR_TEXT

        no_surf = self.font_text.render("No", True, no_color)
        no_text_rect = no_surf.get_rect(center=no_rect.center)
        surf.blit(no_surf, no_text_rect)

        # Hint
        hint_surf = self.font_small.render(
            "A: Select   B: Cancel", True, ui_colors.COLOR_BORDER
        )
        hint_rect = hint_surf.get_rect(
            centerx=self.width // 2, bottom=box_y + box_h - 8
        )
        surf.blit(hint_surf, hint_rect)

    def update(self, events):
        """Update method for compatibility"""
        return self.visible


# -----------------------------
# Pause Combo Selector
# -----------------------------
class PauseComboSelector:
    """Screen for selecting the pause/menu combo with toggle switches"""

    # Preset combo options
    COMBO_OPTIONS = [
        {"name": "START + SELECT", "type": "combo", "buttons": ["START", "SELECT"]},
        {"name": "L + R", "type": "combo", "buttons": ["L", "R"]},
        {"name": "L + R + START", "type": "combo", "buttons": ["L", "R", "START"]},
        {"name": "L + R + SELECT", "type": "combo", "buttons": ["L", "R", "SELECT"]},
        {"name": "Custom Button", "type": "custom", "buttons": []},
    ]

    # Custom button capture timeout (5 seconds at 60fps)
    CAPTURE_TIMEOUT = 300

    def __init__(
        self,
        width,
        height,
        close_callback=None,
        controller=None,
        reload_combo_callback=None,
    ):
        self.width = width
        self.height = height
        self.close_callback = close_callback
        self.controller = controller
        self.reload_combo_callback = reload_combo_callback
        self.visible = True

        # State
        self.selected_index = 0  # Currently highlighted option
        self.active_index = 0  # Currently active/toggled option
        self.custom_button = None

        # Capture state
        self.capture_mode = False
        self.capture_timer = 0

        # Message state
        self.message = None
        self.message_timer = 0
        self.message_color = ui_colors.COLOR_SUCCESS

        # Error state
        self.error_message = None
        self.error_timer = 0

        # Saved confirmation state
        self.just_saved = False
        self.saved_timer = 0

        # Load current setting
        settings = load_sinew_settings()
        self.current_combo = settings.get(
            "pause_combo", {"type": "combo", "buttons": ["START", "SELECT"]}
        )

        # If current is custom, store the button
        if self.current_combo.get("type") == "custom":
            self.custom_button = self.current_combo.get("button")

        # Find which option is currently active
        self._find_active_option()

        # Fonts
        self.font_header = pygame.font.Font(FONT_PATH, 16)
        self.font_text = pygame.font.Font(FONT_PATH, 12)
        self.font_small = pygame.font.Font(FONT_PATH, 10)

    def _find_active_option(self):
        """Find which option matches current setting"""
        if self.current_combo.get("type") == "custom":
            self.active_index = len(self.COMBO_OPTIONS) - 1  # Custom is last
        else:
            current_buttons = set(self.current_combo.get("buttons", []))
            for i, opt in enumerate(self.COMBO_OPTIONS):
                if opt["type"] == "combo" and set(opt["buttons"]) == current_buttons:
                    self.active_index = i
                    break
        # Start with cursor on active option
        self.selected_index = self.active_index

    def _get_bound_buttons(self):
        """Get list of buttons that are already bound to GBA functions"""
        bound = set()
        if self.controller and hasattr(self.controller, "button_map"):
            for name in ["A", "B", "X", "Y", "L", "R", "START", "SELECT"]:
                indices = self.controller.button_map.get(name, [])
                for idx in indices:
                    if isinstance(idx, int):
                        bound.add(idx)
        return bound

    def _get_button_name_for_index(self, idx):
        """Get a display name for a button index"""
        if self.controller and hasattr(self.controller, "button_map"):
            for name, indices in self.controller.button_map.items():
                if idx in indices:
                    return name
        return f"Button {idx}"

    def handle_controller(self, ctrl):
        """Handle controller input"""
        # Update timers
        if self.capture_timer > 0:
            self.capture_timer -= 1
            if self.capture_timer <= 0:
                self.capture_mode = False
                self.message = "Timed out"
                self.message_timer = 90
                self.message_color = ui_colors.COLOR_HIGHLIGHT

        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer <= 0:
                self.message = None

        if self.error_timer > 0:
            self.error_timer -= 1
            if self.error_timer <= 0:
                self.error_message = None

        if self.saved_timer > 0:
            self.saved_timer -= 1
            if self.saved_timer <= 0:
                self.just_saved = False

        # Handle capture mode
        if self.capture_mode:
            return self._handle_button_capture(ctrl)

        # Navigate options
        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            self.selected_index = (self.selected_index - 1) % len(self.COMBO_OPTIONS)
            return True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            self.selected_index = (self.selected_index + 1) % len(self.COMBO_OPTIONS)
            return True

        # Toggle with A or Left/Right
        if (
            ctrl.is_button_just_pressed("A")
            or ctrl.is_dpad_just_pressed("left")
            or ctrl.is_dpad_just_pressed("right")
        ):
            if ctrl.is_button_just_pressed("A"):
                ctrl.consume_button("A")
            ctrl.consume_dpad("left")
            ctrl.consume_dpad("right")
            self._toggle_option()
            return True

        # Back
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.visible = False
            if self.close_callback:
                self.close_callback()
            return True

        return False

    def _handle_button_capture(self, ctrl):
        """Handle capturing a custom button press"""
        try:
            if pygame.joystick.get_count() > 0:
                joy = pygame.joystick.Joystick(0)
                joy.init()
                num_buttons = joy.get_numbuttons()

                bound_buttons = self._get_bound_buttons()

                for btn_idx in range(num_buttons):
                    if joy.get_button(btn_idx):
                        if btn_idx in bound_buttons:
                            btn_name = self._get_button_name_for_index(btn_idx)
                            self.error_message = (
                                f"Button {btn_idx} is bound to {btn_name}!"
                            )
                            self.error_timer = 120
                            self.capture_timer = self.CAPTURE_TIMEOUT
                            return True

                        self.custom_button = btn_idx
                        self.capture_mode = False
                        self._save_custom_button(btn_idx)
                        return True
        except Exception as e:
            print(f"[PauseCombo] Error capturing button: {e}")

        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.capture_mode = False
            self.message = "Cancelled"
            self.message_timer = 60
            self.message_color = ui_colors.COLOR_HIGHLIGHT
            return True

        return True

    def _toggle_option(self):
        """Toggle the currently selected option (radio button behavior)"""
        option = self.COMBO_OPTIONS[self.selected_index]

        if option["type"] == "custom":
            # Start capture mode
            self.capture_mode = True
            self.capture_timer = self.CAPTURE_TIMEOUT
            self.error_message = None
            self.message = None
        else:
            # Toggle on this option, which toggles off all others
            self.active_index = self.selected_index
            self._save_combo(option)

    def _save_combo(self, option):
        """Save a combo option"""
        settings = load_sinew_settings()
        settings["pause_combo"] = {
            "type": "combo",
            "buttons": option["buttons"],
            "name": option["name"],
        }
        save_sinew_settings(settings)
        self.current_combo = settings["pause_combo"]
        print(f"[PauseCombo] Saved combo: {option['name']}")

        self.just_saved = True
        self.saved_timer = 90
        self.message = f"Saved: {option['name']}"
        self.message_timer = 90
        self.message_color = ui_colors.COLOR_SUCCESS

        if self.reload_combo_callback:
            self.reload_combo_callback()

    def _save_custom_button(self, btn_idx):
        """Save a custom button selection"""
        settings = load_sinew_settings()
        settings["pause_combo"] = {
            "type": "custom",
            "button": btn_idx,
            "name": f"Button {btn_idx}",
        }
        save_sinew_settings(settings)
        self.current_combo = settings["pause_combo"]
        self.active_index = len(self.COMBO_OPTIONS) - 1  # Custom is last
        print(f"[PauseCombo] Saved custom button: {btn_idx}")

        self.just_saved = True
        self.saved_timer = 90
        self.message = f"Saved: Button {btn_idx}"
        self.message_timer = 90
        self.message_color = ui_colors.COLOR_SUCCESS

        if self.reload_combo_callback:
            self.reload_combo_callback()

    def draw(self, surf):
        """Draw the selector screen with toggle switches"""
        # Background
        bg_rect = pygame.Rect(0, 0, self.width, self.height)
        pygame.draw.rect(surf, ui_colors.COLOR_BG, bg_rect)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, bg_rect, 3)

        # Header
        title = "Pause/Menu Combo"
        title_surf = self.font_header.render(title, True, ui_colors.COLOR_TEXT)
        title_rect = title_surf.get_rect(centerx=self.width // 2, y=20)
        surf.blit(title_surf, title_rect)

        # Subtitle
        if self.capture_mode:
            remaining = self.capture_timer // 60 + 1
            subtitle = f"Press a button... ({remaining}s)"
            subtitle_color = ui_colors.COLOR_HIGHLIGHT
        else:
            subtitle = "Select combo to pause/resume game"
            subtitle_color = ui_colors.COLOR_TEXT

        sub_surf = self.font_small.render(subtitle, True, subtitle_color)
        sub_rect = sub_surf.get_rect(centerx=self.width // 2, y=45)
        surf.blit(sub_surf, sub_rect)

        # Options with toggle switches
        start_y = 75
        option_height = 32

        for i, option in enumerate(self.COMBO_OPTIONS):
            y = start_y + i * option_height
            is_selected = i == self.selected_index and not self.capture_mode
            is_active = i == self.active_index

            # Row background when selected
            row_rect = pygame.Rect(15, y - 2, self.width - 30, option_height - 2)
            if is_selected:
                pygame.draw.rect(
                    surf, ui_colors.COLOR_BUTTON, row_rect, border_radius=4
                )
                pygame.draw.rect(
                    surf, ui_colors.COLOR_HIGHLIGHT, row_rect, 2, border_radius=4
                )

            # Option name
            if option["type"] == "custom":
                if self.custom_button is not None:
                    display_name = f"Custom: Button {self.custom_button}"
                else:
                    display_name = "Custom Button..."
            else:
                display_name = option["name"]

            text_color = (
                ui_colors.COLOR_HIGHLIGHT if is_selected else ui_colors.COLOR_TEXT
            )
            opt_surf = self.font_text.render(display_name, True, text_color)
            opt_rect = opt_surf.get_rect(x=25, centery=y + option_height // 2 - 2)
            surf.blit(opt_surf, opt_rect)

            # Toggle switch on the right
            toggle_x = self.width - 70
            toggle_rect = pygame.Rect(toggle_x, y + 4, 40, 18)
            pygame.draw.rect(surf, ui_colors.COLOR_HEADER, toggle_rect, border_radius=9)

            # Toggle indicator
            if is_active:
                indicator_x = toggle_x + 22
                indicator_color = ui_colors.COLOR_SUCCESS
            else:
                indicator_x = toggle_x + 4
                indicator_color = ui_colors.COLOR_ERROR

            indicator_rect = pygame.Rect(indicator_x, y + 6, 14, 14)
            pygame.draw.rect(surf, indicator_color, indicator_rect, border_radius=7)

        # Capture mode overlay
        if self.capture_mode:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surf.blit(overlay, (0, 0))

            box_w, box_h = 280, 100
            box_x = (self.width - box_w) // 2
            box_y = (self.height - box_h) // 2
            box_rect = pygame.Rect(box_x, box_y, box_w, box_h)

            pygame.draw.rect(surf, ui_colors.COLOR_BG, box_rect, border_radius=10)
            pygame.draw.rect(
                surf, ui_colors.COLOR_HIGHLIGHT, box_rect, 3, border_radius=10
            )

            remaining = self.capture_timer // 60 + 1
            prompt_text = f"Press any button ({remaining}s)"
            prompt_surf = self.font_text.render(
                prompt_text, True, ui_colors.COLOR_HIGHLIGHT
            )
            prompt_rect = prompt_surf.get_rect(
                centerx=self.width // 2, centery=self.height // 2 - 15
            )
            surf.blit(prompt_surf, prompt_rect)

            cancel_surf = self.font_small.render(
                "B: Cancel", True, ui_colors.COLOR_TEXT
            )
            cancel_rect = cancel_surf.get_rect(
                centerx=self.width // 2, centery=self.height // 2 + 20
            )
            surf.blit(cancel_surf, cancel_rect)

        # Success/info message
        if self.message and self.message_timer > 0:
            msg_surf = self.font_text.render(self.message, True, self.message_color)
            msg_rect = msg_surf.get_rect(centerx=self.width // 2, y=self.height - 80)
            surf.blit(msg_surf, msg_rect)

        # Error message
        if self.error_message and self.error_timer > 0:
            err_surf = self.font_small.render(
                self.error_message, True, ui_colors.COLOR_ERROR
            )
            err_rect = err_surf.get_rect(centerx=self.width // 2, y=self.height - 60)
            surf.blit(err_surf, err_rect)

        # Controller hints
        hint_y = self.height - 30
        if not self.capture_mode:
            hint = "A / < > Toggle   B: Back"
            hint_surf = self.font_small.render(hint, True, ui_colors.COLOR_BORDER)
            hint_rect = hint_surf.get_rect(centerx=self.width // 2, y=hint_y)
            surf.blit(hint_surf, hint_rect)

    def update(self, events):
        """Update method for compatibility with sub_screen handling"""
        return self.visible


class Settings:
    """Settings modal - wrapper that manages the settings screen"""

    def __init__(
        self,
        w,
        h,
        font=None,
        close_callback=None,
        music_mute_callback=None,
        fullscreen_callback=None,
        swap_ab_callback=None,
        db_builder_callback=None,
        scaler=None,
        reload_combo_callback=None,
    ):
        self.width = w
        self.height = h
        self.font = font
        self.screen = MainSetup(
            w,
            h,
            close_callback=close_callback,
            music_mute_callback=music_mute_callback,
            fullscreen_callback=fullscreen_callback,
            swap_ab_callback=swap_ab_callback,
            db_builder_callback=db_builder_callback,
            scaler=scaler,
            reload_combo_callback=reload_combo_callback,
        )
        self.visible = True

    def update(self, events):
        self.screen.handle_events(events)
        self.visible = self.screen.visible
        return self.visible

    def handle_controller(self, ctrl):
        return self.screen.handle_controller(ctrl)

    def draw(self, surf):
        self.screen.draw(surf)


# Alias for backwards compatibility
Modal = Settings


# -----------------------------
# Keyboard Mapper
# -----------------------------
class KeyboardMapper:
    """
    Screen for rebinding keyboard keys for both Sinew UI navigation
    and in-emulator GBA buttons.

    Saves to sinew_settings.json under:
      'keyboard_nav_map'      -> Sinew menu navigation (arrows/WASD etc.)
      'keyboard_emulator_map' -> In-game GBA buttons (z/x/enter etc.)
    """

    # Navigation actions shown in the UI tab
    NAV_ACTIONS = [
        ("up", "Up / W"),
        ("down", "Down / S"),
        ("left", "Left / A"),
        ("right", "Right / D"),
        ("A", "Confirm"),
        ("B", "Back"),
        ("L", "Page Up"),
        ("R", "Page Down"),
    ]

    # Emulator GBA button actions
    EMU_ACTIONS = [
        ("A", "GBA A"),
        ("B", "GBA B"),
        ("L", "GBA L"),
        ("R", "GBA R"),
        ("START", "GBA Start"),
        ("SELECT", "GBA Select"),
        ("UP", "GBA Up"),
        ("DOWN", "GBA Down"),
        ("LEFT", "GBA Left"),
        ("RIGHT", "GBA Right"),
    ]

    # Default bindings (pygame key constants)
    DEFAULT_NAV = {
        "up": [pygame.K_UP, pygame.K_w],
        "down": [pygame.K_DOWN, pygame.K_s],
        "left": [pygame.K_LEFT, pygame.K_a],
        "right": [pygame.K_RIGHT, pygame.K_d],
        "A": [pygame.K_RETURN, pygame.K_z],
        "B": [pygame.K_ESCAPE, pygame.K_x],
        "L": [pygame.K_PAGEUP, pygame.K_q],
        "R": [pygame.K_PAGEDOWN, pygame.K_e],
    }
    DEFAULT_EMU = {
        "A": [pygame.K_z],
        "B": [pygame.K_x],
        "L": [pygame.K_q],
        "R": [pygame.K_e],
        "START": [pygame.K_RETURN],
        "SELECT": [pygame.K_BACKSPACE],
        "UP": [pygame.K_UP, pygame.K_w],
        "DOWN": [pygame.K_DOWN, pygame.K_s],
        "LEFT": [pygame.K_LEFT, pygame.K_a],
        "RIGHT": [pygame.K_RIGHT, pygame.K_d],
    }

    LISTEN_TIMEOUT = 5.0  # seconds

    def __init__(
        self,
        width,
        height,
        close_callback=None,
        controller=None,
        reload_kb_callback=None,
    ):
        self.width = width
        self.height = height
        self.close_callback = close_callback
        self.controller = controller
        self.reload_kb_callback = reload_kb_callback  # Called after saving
        self.visible = True

        # Tabs: 0 = navigation, 1 = emulator
        self.active_tab = 0
        self.TABS = ["Navigation", "Emulator"]

        # Selection
        self.selected_index = 0

        # Listening state
        self.listening = False
        self.listen_action = None
        self.listen_tab = None
        self.listen_start = 0.0
        self.listen_keys = []  # Keys recorded during capture

        # Status message
        self._status = None
        self._status_time = 0

        # Load current bindings
        self.nav_map = {k: list(v) for k, v in self.DEFAULT_NAV.items()}
        self.emu_map = {k: list(v) for k, v in self.DEFAULT_EMU.items()}
        self._load_bindings()

        # Fonts
        self.font_header = pygame.font.Font(FONT_PATH, 16)
        self.font_text = pygame.font.Font(FONT_PATH, 11)
        self.font_small = pygame.font.Font(FONT_PATH, 9)

    def _load_bindings(self):
        """Load saved bindings from sinew_settings.json"""
        settings = load_sinew_settings()
        saved_nav = settings.get("keyboard_nav_map", {})
        for k in self.nav_map:
            if k in saved_nav and isinstance(saved_nav[k], list):
                self.nav_map[k] = [v for v in saved_nav[k] if isinstance(v, int)]
        saved_emu = settings.get("keyboard_emulator_map", {})
        for k in self.emu_map:
            if k in saved_emu and isinstance(saved_emu[k], list):
                self.emu_map[k] = [v for v in saved_emu[k] if isinstance(v, int)]

    def _save_bindings(self):
        """Persist current bindings to sinew_settings.json"""
        settings = load_sinew_settings()
        settings["keyboard_nav_map"] = self.nav_map
        settings["keyboard_emulator_map"] = self.emu_map
        save_sinew_settings(settings)
        print("[KeyboardMapper] Saved keyboard bindings")
        if self.reload_kb_callback:
            self.reload_kb_callback()

    def _reset_to_defaults(self):
        """Reset all bindings to defaults"""
        self.nav_map = {k: list(v) for k, v in self.DEFAULT_NAV.items()}
        self.emu_map = {k: list(v) for k, v in self.DEFAULT_EMU.items()}
        self._save_bindings()
        self._status = "Reset to defaults"
        self._status_time = pygame.time.get_ticks()

    @staticmethod
    def key_name(key_const):
        """Convert a pygame key constant to a short display string"""
        name = pygame.key.name(key_const)
        # Clean up some verbose names
        name = (
            name.replace("keypad ", "KP").replace("left ", "L-").replace("right ", "R-")
        )
        return name.upper() if len(name) <= 4 else name.capitalize()

    def _keys_display(self, key_list):
        """Format a list of key constants as a comma-separated string"""
        if not key_list:
            return "---"
        return " / ".join(self.key_name(k) for k in key_list[:2])

    def _current_actions(self):
        return self.NAV_ACTIONS if self.active_tab == 0 else self.EMU_ACTIONS

    def _current_map(self):
        return self.nav_map if self.active_tab == 0 else self.emu_map

    def _start_listening(self, action):
        self.listening = True
        self.listen_action = action
        self.listen_tab = self.active_tab
        self.listen_start = time.time()
        self.listen_keys = []
        # Disable the controller's keyboard event filter so all
        # KEYDOWN events (including nav-mapped keys) reach us
        if self.controller:
            self.controller.kb_filter_enabled = False

    def _stop_listening(self, save=True):
        if save and self.listen_keys:
            mapping = self._current_map()
            mapping[self.listen_action] = list(self.listen_keys)
            self._save_bindings()
            self._status = f"Bound to {self._keys_display(self.listen_keys)}"
            self._status_time = pygame.time.get_ticks()
        self.listening = False
        self.listen_action = None
        self.listen_keys = []
        # Re-enable the filter
        if self.controller:
            self.controller.kb_filter_enabled = True

    def on_close(self):
        self._save_bindings()
        self.visible = False
        # Ensure filter is re-enabled if we were still listening
        if self.controller:
            self.controller.kb_filter_enabled = True
        if self.close_callback:
            self.close_callback()

    def handle_events(self, events):
        """Handle pygame events"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.listening:
                    if event.key == pygame.K_ESCAPE:
                        self._stop_listening(save=False)
                        self._status = "Cancelled"
                        self._status_time = pygame.time.get_ticks()
                    else:
                        # Record this key; allow up to 2 keys per action
                        if event.key not in self.listen_keys:
                            self.listen_keys.append(event.key)
                        if len(self.listen_keys) >= 2:
                            self._stop_listening(save=True)
                else:
                    actions = self._current_actions()
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.selected_index = max(0, self.selected_index - 1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected_index = min(
                            len(actions) - 1, self.selected_index + 1
                        )
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.active_tab = (self.active_tab - 1) % len(self.TABS)
                        self.selected_index = 0
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.active_tab = (self.active_tab + 1) % len(self.TABS)
                        self.selected_index = 0
                    elif event.key in (pygame.K_RETURN, pygame.K_z):
                        action_key = self._current_actions()[self.selected_index][0]
                        self._start_listening(action_key)
                    elif event.key == pygame.K_BACKSPACE:
                        # Clear binding for selected action
                        action_key = self._current_actions()[self.selected_index][0]
                        self._current_map()[action_key] = []
                        self._save_bindings()
                        self._status = "Cleared"
                        self._status_time = pygame.time.get_ticks()
                    elif event.key == pygame.K_ESCAPE:
                        self.on_close()

    def handle_controller(self, ctrl):
        """Handle controller input"""
        if self.listening:
            elapsed = time.time() - self.listen_start
            if elapsed >= self.LISTEN_TIMEOUT:
                if self.listen_keys:
                    # Lock in whatever was pressed
                    self._stop_listening(save=True)
                else:
                    self._stop_listening(save=False)
                    self._status = "Timed out"
                    self._status_time = pygame.time.get_ticks()
            return True

        actions = self._current_actions()

        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            self.selected_index = max(0, self.selected_index - 1)
        elif ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            self.selected_index = min(len(actions) - 1, self.selected_index + 1)
        elif ctrl.is_dpad_just_pressed("left"):
            ctrl.consume_dpad("left")
            self.active_tab = (self.active_tab - 1) % len(self.TABS)
            self.selected_index = 0
        elif ctrl.is_dpad_just_pressed("right"):
            ctrl.consume_dpad("right")
            self.active_tab = (self.active_tab + 1) % len(self.TABS)
            self.selected_index = 0

        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            action_key = self._current_actions()[self.selected_index][0]
            self._start_listening(action_key)

        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.on_close()

        if ctrl.is_button_just_pressed("L"):
            ctrl.consume_button("L")
            self._reset_to_defaults()

        return True

    def update(self, events):
        self.handle_events(events)
        # Auto-stop listening on timeout
        if self.listening:
            elapsed = time.time() - self.listen_start
            if elapsed >= self.LISTEN_TIMEOUT:
                if self.listen_keys:
                    # Lock in whatever was pressed
                    self._stop_listening(save=True)
                else:
                    self._stop_listening(save=False)
                    self._status = "Timed out"
                    self._status_time = pygame.time.get_ticks()
        return self.visible

    def draw(self, surf):
        """Draw the keyboard mapper screen"""
        # Background
        overlay = pygame.Surface((self.width, self.height))
        overlay.fill(ui_colors.COLOR_BG)
        surf.blit(overlay, (0, 0))
        pygame.draw.rect(
            surf, ui_colors.COLOR_BORDER, (0, 0, self.width, self.height), 2
        )

        # Title
        title_surf = self.font_header.render(
            "Keyboard Bindings", True, ui_colors.COLOR_HIGHLIGHT
        )
        surf.blit(title_surf, title_surf.get_rect(centerx=self.width // 2, top=10))

        # Tabs
        tab_y = 34
        tab_w = (self.width - 40) // len(self.TABS)
        for i, tab in enumerate(self.TABS):
            tx = 20 + i * tab_w
            tab_rect = pygame.Rect(tx, tab_y, tab_w - 4, 20)
            is_active = i == self.active_tab
            bg_col = (
                ui_colors.COLOR_BUTTON_HOVER if is_active else ui_colors.COLOR_BUTTON
            )
            border_col = (
                ui_colors.COLOR_HIGHLIGHT if is_active else ui_colors.COLOR_BORDER
            )
            pygame.draw.rect(surf, bg_col, tab_rect, border_radius=4)
            pygame.draw.rect(surf, border_col, tab_rect, 1, border_radius=4)
            ts = self.font_small.render(tab, True, ui_colors.COLOR_TEXT)
            surf.blit(ts, ts.get_rect(center=tab_rect.center))

        # Action rows with scrolling support
        actions = self._current_actions()
        mapping = self._current_map()
        row_h = 22  # Back to 22px
        start_y = 72
        col_label = 20
        col_keys = self.width // 2

        # Column headers
        hdr_label = self.font_small.render("Action", True, ui_colors.COLOR_BORDER)
        hdr_keys = self.font_small.render(
            "Bound Keys  (A=bind, Bksp=clear)", True, ui_colors.COLOR_BORDER
        )
        surf.blit(hdr_label, (col_label, start_y - 16))
        surf.blit(hdr_keys, (col_keys, start_y - 16))

        # Calculate how many rows fit on screen
        available_height = (
            self.height - start_y - 35
        )  # Reduced from 50 to fit ~2 more rows
        visible_rows = available_height // row_h

        # Calculate scroll offset to keep selected item visible
        scroll_offset = 0
        if self.selected_index >= visible_rows:
            scroll_offset = self.selected_index - visible_rows + 1

        # Draw only visible rows
        for i in range(len(actions)):
            visible_index = i - scroll_offset
            if visible_index < 0 or visible_index >= visible_rows:
                continue  # Skip rows outside visible area

            action_key, label = actions[i]
            row_y = start_y + visible_index * row_h
            is_sel = i == self.selected_index
            is_listening = (
                self.listening
                and self.listen_action == action_key
                and self.listen_tab == self.active_tab
            )

            # Row background
            row_rect = pygame.Rect(10, row_y - 2, self.width - 20, row_h - 2)
            if is_listening:
                pygame.draw.rect(surf, (60, 30, 10), row_rect, border_radius=3)
                pygame.draw.rect(surf, (255, 140, 0), row_rect, 1, border_radius=3)
            elif is_sel:
                pygame.draw.rect(
                    surf, ui_colors.COLOR_BUTTON, row_rect, border_radius=3
                )
                pygame.draw.rect(
                    surf, ui_colors.COLOR_HIGHLIGHT, row_rect, 1, border_radius=3
                )

            # Label
            label_col = ui_colors.COLOR_HIGHLIGHT if is_sel else ui_colors.COLOR_TEXT
            ls = self.font_text.render(label, True, label_col)
            surf.blit(ls, (col_label, row_y))

            # Keys display
            if is_listening:
                elapsed = time.time() - self.listen_start
                remaining = max(0, self.LISTEN_TIMEOUT - elapsed)
                recorded = (
                    self._keys_display(self.listen_keys) if self.listen_keys else "..."
                )
                ks_text = f"Press key(s)... {recorded}  [{remaining:.1f}s]"
                ks = self.font_text.render(ks_text, True, (255, 160, 50))
            else:
                keys = mapping.get(action_key, [])
                ks = self.font_text.render(
                    self._keys_display(keys), True, (150, 220, 150)
                )
            surf.blit(ks, (col_keys, row_y))

        # Scroll indicator if there are more items
        if len(actions) > visible_rows:
            scroll_text = f"Row {self.selected_index + 1}/{len(actions)}"
            scroll_surf = self.font_small.render(scroll_text, True, (100, 100, 100))
            surf.blit(
                scroll_surf,
                scroll_surf.get_rect(right=self.width - 15, top=start_y - 16),
            )

        # Status message (positioned above hints)
        if self._status and pygame.time.get_ticks() - self._status_time < 2500:
            st = self.font_small.render(self._status, True, ui_colors.COLOR_SUCCESS)
            surf.blit(st, st.get_rect(centerx=self.width // 2, bottom=self.height - 24))

        # Hints (moved closer to status)
        hint = "A: Bind   Bksp: Clear   L: Reset Defaults   B: Close"
        hs = self.font_small.render(hint, True, (80, 80, 80))
        surf.blit(hs, hs.get_rect(centerx=self.width // 2, bottom=self.height - 8))


# -----------------------------
# Main Setup / Settings Class
# -----------------------------
class MainSetup:
    def __init__(
        self,
        width,
        height,
        close_callback=None,
        music_mute_callback=None,
        fullscreen_callback=None,
        swap_ab_callback=None,
        db_builder_callback=None,
        scaler=None,
        reload_combo_callback=None,
    ):
        self.width = width
        self.height = height
        self.visible = True
        self.close_callback = close_callback
        self.music_mute_callback = music_mute_callback
        self.fullscreen_callback = fullscreen_callback
        self.swap_ab_callback = swap_ab_callback
        self.db_builder_callback = db_builder_callback
        self.scaler = scaler
        self.reload_combo_callback = reload_combo_callback
        self.controller = get_controller()

        # Sub-screen state
        self.sub_screen = None  # Can hold ButtonMapper, etc.
        self._sub_screen_open_tick = 0  # Frame when sub_screen was opened

        # Cache message state
        self._cache_message = None
        self._cache_message_time = 0

        # Secret dev mode state (non-persistent)
        self._dev_mode_counter = 0
        self._dev_mode_active = False

        # Toggle debounce timer (prevents rapid toggling, especially for fullscreen)
        self._last_toggle_time = 0
        self._toggle_debounce_ms = 300  # 300ms debounce

        # Fonts
        self.font_header = pygame.font.Font(FONT_PATH, 18)
        self.font_text = pygame.font.Font(FONT_PATH, 12)
        self.font_small = pygame.font.Font(FONT_PATH, 10)

        # Tab definitions
        self.tabs = ["General", "Input", "mGBA", "Info"]
        self.selected_tab = 0

        # Track if we're navigating tabs or options
        self.tab_focus = True  # Start with tab focus

        # Options per tab
        self.tab_options = {
            "General": [
                # Fullscreen has no meaning on a handheld — hide it entirely
                *([] if IS_HANDHELD else [{"name": "Fullscreen", "type": "toggle", "value": False}]),
                {"name": "Mute Menu Music", "type": "toggle", "value": False},
                {"name": "Themes", "type": "button"},
                {"name": "Build/Rebuild Pokemon DB", "type": "button"},
            ],
            "Input": [
                {"name": "Swap A/B Buttons", "type": "toggle", "value": False},
                {"name": "Pause/Menu Combo", "type": "button"},
                {"name": "Map Buttons", "type": "button"},
                {"name": "Reset to Default", "type": "button"},
                {"name": "Map Keyboard Keys", "type": "button"},
                {"name": "Reset Keyboard Defaults", "type": "button"},
            ],
            "mGBA": [
                {
                    "name": "Fast-Forward",
                    "type": "toggle",
                    "value": False,
                },
                {
                    "name": "Fast-Forward Speed",
                    "type": "slider",
                    "slider_index": 0,
                    "labels": ["2x", "3x", "4x", "5x", "6x", "7x", "8x", "9x", "10x"],
                    "speed_values": [2, 3, 4, 5, 6, 7, 8, 9, 10],
                },
            ],
            "Info": [
                {"name": "Sinew Version", "type": "label", "value": "v1.3.4"},
                {"name": "Author", "type": "label", "value": "Cameron Penna"},
                {"name": "Pokemon DB Status", "type": "label", "value": "Checking..."},
                {"name": "About/Legal", "type": "button"},
                {"name": "Changelog", "type": "button"},
            ],
            "Dev": [
                {"name": "Use External Emulator", "type": "toggle", "value": False},
                {"name": "Reset ALL Achievements", "type": "button"},
                {"name": "Reset Game Achievements...", "type": "button"},
                {"name": "Export Achievement Data", "type": "button"},
            ],
        }

        # Achievement reset modal state
        self._ach_reset_modal = None
        self._ach_reset_game = None
        self._ach_reset_list = []
        self._ach_reset_selected = 0
        self._ach_reset_scroll = 0

        # Load initial values from settings
        self._load_settings_values()

        # Update Pokemon DB status
        self._update_pokemon_db_status()

        # Navigation
        self.selected_option = 0
        self._update_option_nav()

    def _load_settings_values(self):
        """Load initial toggle values from sinew_settings.json"""
        settings = load_sinew_settings()

        # Load General tab settings
        for opt in self.tab_options["General"]:
            if opt["name"] == "Mute Menu Music":
                opt["value"] = settings.get("mute_menu_music", False)
            elif opt["name"] == "Fullscreen":
                opt["value"] = settings.get("fullscreen", False)

        # Load Input tab settings
        for opt in self.tab_options["Input"]:
            if opt["name"] == "Swap A/B Buttons":
                opt["value"] = settings.get("swap_ab", False)

        # Load mGBA tab settings
        for opt in self.tab_options["mGBA"]:
            if opt["name"] == "Fast-Forward":
                opt["value"] = settings.get("mgba_fastforward_enabled", False)
            elif opt["name"] == "Fast-Forward Speed":
                saved_idx = settings.get("mgba_fastforward_index", 0)
                opt["slider_index"] = max(0, min(saved_idx, len(opt["speed_values"]) - 1))

        # Load Dev tab settings
        for opt in self.tab_options["Dev"]:
            if opt["name"] == "Use External Emulator":
                opt["value"] = settings.get("use_external_emulator", False)

    def _update_option_nav(self):
        """Update NavigableList for current tab"""
        count = len(self.tab_options[self.current_tab()])
        self.option_nav = NavigableList(count, columns=1, wrap=True)

    # -------------------
    # Helpers
    # -------------------
    def _get_pokemon_db_status(self):
        """Get the current Pokemon database status"""
        db_path = POKEMON_DB_PATH

        if not os.path.exists(db_path):
            return "Not Built"

        try:
            # Check file size
            file_size = os.path.getsize(db_path)

            if file_size < 100:
                return "Empty/Invalid"

            # Try to load and count entries
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both dict and list formats
            if isinstance(data, dict):
                count = len(data)
            elif isinstance(data, list):
                count = len(data)
            else:
                return "Invalid Format"

            if count >= 386:
                return f"Loaded ({count})"
            elif count > 0:
                return f"Partial ({count}/386)"
            else:
                return "Empty"

        except json.JSONDecodeError as e:
            print(f"[Settings] Pokemon DB JSON error: {e}")
            return "JSON Error"
        except Exception as e:
            print(f"[Settings] Pokemon DB status error: {e}")
            return "Error"

    def _update_pokemon_db_status(self):
        """Update the Pokemon DB status in Info tab"""
        for opt in self.tab_options["Info"]:
            if opt["name"] == "Pokemon DB Status":
                opt["value"] = self._get_pokemon_db_status()
                break

    def current_tab(self):
        return self.tabs[self.selected_tab]

    def current_options(self):
        return self.tab_options[self.current_tab()]

    def on_back(self):
        self.visible = False
        if self.close_callback:
            self.close_callback()

    def _change_tab(self, direction):
        """Change tab by direction (-1 or +1)"""
        self.selected_tab = (self.selected_tab + direction) % len(self.tabs)
        self.selected_option = 0
        self._update_option_nav()

    def _adjust_option(self, direction):
        """Adjust current option value by direction (-1 or +1)"""
        option = self.current_options()[self.selected_option]

        if option["type"] == "toggle":
            # Debounce toggle to prevent rapid switching (especially for fullscreen)
            current_time = pygame.time.get_ticks()
            if current_time - self._last_toggle_time < self._toggle_debounce_ms:
                return False  # Ignore this toggle, too soon
            self._last_toggle_time = current_time

            option["value"] = not option["value"]
            # Call appropriate callback
            self._handle_toggle_callback(option["name"], option["value"])
            return True
        elif option["type"] == "choice":
            choices = option["choices"]
            idx = choices.index(option["value"])
            option["value"] = choices[(idx + direction) % len(choices)]
            return True
        elif option["type"] == "slider":
            old_idx = option.get("slider_index", 0)
            max_idx = len(option["speed_values"]) - 1
            new_idx = max(0, min(old_idx + direction, max_idx))
            option["slider_index"] = new_idx
            # Save the new speed index whenever it changes
            self._save_mgba_fastforward_settings()
            return True
        return False

    def _handle_toggle_callback(self, name, value):
        """Call the appropriate callback for a toggle option"""
        if name == "Swap A/B Buttons" and self.swap_ab_callback:
            self.swap_ab_callback(value)
        elif name == "Fullscreen" and self.fullscreen_callback:
            self.fullscreen_callback(value)
        elif name == "Mute Menu Music" and self.music_mute_callback:
            self.music_mute_callback(value)
        elif name == "Use External Emulator":
            try:
                settings = load_sinew_settings()
                settings["use_external_emulator"] = value
                save_sinew_settings(settings)
                import builtins

                builtins.SINEW_USE_EXTERNAL_EMULATOR = value
                status = "ON" if value else "OFF"
                print(f"[Settings] Use External Emulator: {status}")
                self._status_msg(f"External Emulator: {status}")
            except Exception as e:
                print(f"[Settings] Failed to save external emulator setting: {e}")
        elif name == "Fast-Forward":
            self._save_mgba_fastforward_settings()
            self._apply_fastforward_to_emulator()

    def _save_mgba_fastforward_settings(self):
        """Persist fast-forward toggle + speed index to sinew_settings.json."""
        enabled = False
        speed_index = 0
        speed_values = [2, 3, 4, 5, 6, 7, 8, 9, 10]
        for opt in self.tab_options.get("mGBA", []):
            if opt["name"] == "Fast-Forward":
                enabled = opt.get("value", False)
            elif opt["name"] == "Fast-Forward Speed":
                speed_index = opt.get("slider_index", 0)
                speed_values = opt.get("speed_values", speed_values)
        multiplier = speed_values[speed_index] if enabled else 1
        try:
            s = load_sinew_settings()
            s["mgba_fastforward_enabled"] = enabled
            s["mgba_fastforward_index"] = speed_index
            s["mgba_fastforward_speed"] = speed_values[speed_index]
            save_sinew_settings(s)
            print(f"[Settings] Fast-Forward: {'ON' if enabled else 'OFF'} @ {speed_values[speed_index]}x")
        except Exception as e:
            print(f"[Settings] Failed to save fast-forward settings: {e}")

    def _apply_fastforward_to_emulator(self):
        """Push the current fast-forward state to the running emulator via builtins."""
        enabled = False
        speed_index = 0
        speed_values = [2, 3, 4, 5, 6, 7, 8, 9, 10]
        for opt in self.tab_options.get("mGBA", []):
            if opt["name"] == "Fast-Forward":
                enabled = opt.get("value", False)
            elif opt["name"] == "Fast-Forward Speed":
                speed_index = opt.get("slider_index", 0)
                speed_values = opt.get("speed_values", speed_values)
        multiplier = speed_values[speed_index] if enabled else 1
        try:
            import builtins
            emu = getattr(builtins, "SINEW_EMULATOR", None)
            if emu is not None and hasattr(emu, "set_fast_forward"):
                emu.set_fast_forward(multiplier)
                label = f"{multiplier}x" if enabled else "Off"
                print(f"[Settings] Applied fast-forward to emulator: {label}")
        except Exception as e:
            print(f"[Settings] Could not apply fast-forward to emulator: {e}")

    def _activate_option(self):
        """Activate/select current option"""
        option = self.current_options()[self.selected_option]

        if option["type"] == "button":
            self._handle_button(option["name"])
            return True
        elif option["type"] == "toggle":
            # Debounce toggle to prevent rapid switching (especially for fullscreen)
            current_time = pygame.time.get_ticks()
            if current_time - self._last_toggle_time < self._toggle_debounce_ms:
                return False  # Ignore this toggle, too soon
            self._last_toggle_time = current_time

            option["value"] = not option["value"]
            # Call appropriate callback
            self._handle_toggle_callback(option["name"], option["value"])
            return True
        elif option["type"] == "path":
            # TODO: Open file browser
            print(f"Would open path picker for: {option['name']}")
            return True
        return False

    def _handle_button(self, name):
        """Handle button press actions"""
        if name == "Themes":
            if THEMES_SCREEN_AVAILABLE:
                print("[Settings] Opening themes screen...")
                self._set_sub_screen(
                    ThemesScreen(
                        self.width, self.height, close_callback=self._close_sub_screen
                    )
                )
            else:
                print("[Settings] Themes screen not available")
        elif name == "Build/Rebuild Pokemon DB":
            print("[Settings] Opening Pokemon DB builder...")
            if self.db_builder_callback:
                self.db_builder_callback()
            else:
                print("[Settings] DB builder callback not available")
        elif name == "Map Buttons":
            if BUTTON_MAPPER_AVAILABLE:
                print("[Settings] Opening button mapper...")
                self._set_sub_screen(
                    ButtonMapper(
                        self.width,
                        self.height,
                        close_callback=self._close_sub_screen,
                        controller=self.controller,
                    )
                )
            else:
                print("[Settings] Button mapper not available")
        elif name == "Pause/Menu Combo":
            print("[Settings] Opening pause combo selector...")
            self._set_sub_screen(
                PauseComboSelector(
                    self.width,
                    self.height,
                    close_callback=self._close_sub_screen,
                    controller=self.controller,
                    reload_combo_callback=self.reload_combo_callback,
                )
            )
        elif name == "Map Keyboard Keys":
            print("[Settings] Opening keyboard mapper...")
            self._set_sub_screen(
                KeyboardMapper(
                    self.width,
                    self.height,
                    close_callback=self._close_sub_screen,
                    controller=self.controller,
                    reload_kb_callback=self._on_keyboard_saved,
                )
            )
        elif name == "Reset Keyboard Defaults":
            km = KeyboardMapper(self.width, self.height)
            km._reset_to_defaults()
            self._status_msg("Keyboard defaults restored")
        elif name == "Reset to Default":
            print("[Settings] Resetting controller to defaults...")
            if self.controller:
                # Reset to default mapping
                self.controller.button_map = {
                    "A": [0],
                    "B": [1],
                    "X": [2],
                    "Y": [3],
                    "L": [4],
                    "R": [5],
                    "SELECT": [6],
                    "START": [7],
                }
                print("[Settings] Controller reset to defaults")
        elif name == "About/Legal":
            print("[Settings] Opening About/Legal screen...")
            self._set_sub_screen(
                AboutLegalScreen(
                    self.width, self.height, close_callback=self._close_sub_screen
                )
            )
        elif name == "Changelog":
            print("[Settings] Opening Changelog screen...")
            self._set_sub_screen(
                ChangelogScreen(
                    self.width, self.height, close_callback=self._close_sub_screen
                )
            )
        # Dev tab handlers
        elif name == "Reset ALL Achievements":
            self._set_sub_screen(
                ConfirmationPopup(
                    self.width,
                    self.height,
                    "Reset ALL achievements?",
                    on_confirm=self._do_reset_all_achievements,
                    on_cancel=self._close_sub_screen,
                )
            )
        elif name == "Reset Game Achievements...":
            self._open_game_achievement_selector()
        elif name == "Export Achievement Data":
            self._export_achievement_data()
        else:
            print(f"[Settings] Activated: {name}")

    def _close_sub_screen(self):
        """Close any open sub-screen"""
        self.sub_screen = None

    def _set_sub_screen(self, screen):
        """Open a sub-screen with input guard to prevent bleed-through.

        Records the current tick so that handle_events and handle_controller
        skip delegating to the sub_screen on the same frame it was opened.
        This prevents the key/button that activated the option from also
        being processed by the newly opened sub_screen.
        """
        self.sub_screen = screen
        self._sub_screen_open_tick = pygame.time.get_ticks()

    def _status_msg(self, msg):
        """Show a temporary status message"""
        self._cache_message = msg
        self._cache_message_time = pygame.time.get_ticks()

    def _on_keyboard_saved(self):
        """Called after keyboard bindings are saved; reloads controller and emulator maps."""
        # Do NOT close the sub_screen here — the user may still be binding keys.
        # The mapper will close itself via on_close -> close_callback.

        # Reload controller keyboard nav map
        try:
            ctrl = get_controller()
            if hasattr(ctrl, "reload_kb_nav_map"):
                ctrl.reload_kb_nav_map()
        except Exception as e:
            print(f"[Settings] Could not reload controller kb map: {e}")
        # Reload emulator keyboard map if one is active
        try:
            # The active emulator instance is accessed through main - best effort
            import sys

            for obj in sys.modules.values():
                if hasattr(obj, "emulator") and hasattr(
                    obj.emulator, "reload_keyboard_config"
                ):
                    obj.emulator.reload_keyboard_config()
                    break
        except Exception:
            pass

    def _show_cache_status(self, message):
        """Show cache clear status message"""
        self._cache_message = message
        self._cache_message_time = pygame.time.get_ticks()

    # -------------------
    # Achievement Reset Functions (Dev Mode)
    # -------------------
    def _do_reset_all_achievements(self):
        """Reset all achievements after confirmation"""
        self.sub_screen = None
        try:
            from achievements import get_achievement_manager

            manager = get_achievement_manager()
            if manager:
                manager.reset_all()
                print("[Settings] All achievements reset!")
                self._cache_message = "All achievements reset!"
                self._cache_message_time = pygame.time.get_ticks()
        except Exception as e:
            print(f"[Settings] Error resetting achievements: {e}")
            self._cache_message = f"Error: {e}"
            self._cache_message_time = pygame.time.get_ticks()

    def _open_game_achievement_selector(self):
        """Open a selector for which game's achievements to reset"""
        self._ach_reset_modal = "game_select"
        self._ach_reset_list = [
            "Ruby",
            "Sapphire",
            "Emerald",
            "FireRed",
            "LeafGreen",
            "Sinew",
        ]
        self._ach_reset_selected = 0
        self._ach_reset_scroll = 0

    def _open_unlocked_achievements_viewer(self):
        """Open a viewer showing all unlocked achievements"""
        try:
            from achievements import get_achievement_manager
            from achievements_data import GAMES, get_achievements_for

            manager = get_achievement_manager()
            if not manager:
                return

            # Gather all unlocked achievements
            unlocked = []
            for game in GAMES + ["Sinew"]:
                achievements = get_achievements_for(game)
                for ach in achievements:
                    if manager.is_unlocked(ach["id"]):
                        unlocked.append(ach)

            if not unlocked:
                self._cache_message = "No achievements unlocked yet!"
                self._cache_message_time = pygame.time.get_ticks()
                return

            self._ach_reset_modal = "view_unlocked"
            self._ach_reset_list = unlocked
            self._ach_reset_selected = 0
            self._ach_reset_scroll = 0

        except Exception as e:
            print(f"[Settings] Error viewing achievements: {e}")

    def _open_specific_achievement_reset(self, game_name):
        """Open a list of unlocked achievements for a specific game to reset"""
        try:
            from achievements import get_achievement_manager
            from achievements_data import get_achievements_for

            manager = get_achievement_manager()
            if not manager:
                return

            achievements = get_achievements_for(game_name)
            unlocked = [a for a in achievements if manager.is_unlocked(a["id"])]

            if not unlocked:
                self._cache_message = f"No {game_name} achievements to reset!"
                self._cache_message_time = pygame.time.get_ticks()
                self._ach_reset_modal = None
                return

            self._ach_reset_modal = "specific_reset"
            self._ach_reset_game = game_name
            self._ach_reset_list = unlocked
            self._ach_reset_selected = 0
            self._ach_reset_scroll = 0

        except Exception as e:
            print(f"[Settings] Error loading achievements: {e}")

    def _reset_specific_achievement(self, achievement):
        """Reset a specific achievement"""
        try:
            from achievements import get_achievement_manager

            manager = get_achievement_manager()
            if manager:
                manager.reset_achievement(achievement["id"])
                print(f"[Settings] Reset achievement: {achievement['name']}")
                self._cache_message = f"Reset: {achievement['name']}"
                self._cache_message_time = pygame.time.get_ticks()

                # Remove from list
                if achievement in self._ach_reset_list:
                    self._ach_reset_list.remove(achievement)
                    if self._ach_reset_selected >= len(self._ach_reset_list):
                        self._ach_reset_selected = max(0, len(self._ach_reset_list) - 1)

                # Close modal if list is empty
                if not self._ach_reset_list:
                    self._ach_reset_modal = None

        except Exception as e:
            print(f"[Settings] Error resetting achievement: {e}")

    def _reset_all_game_achievements(self, game_name):
        """Reset all achievements for a specific game"""
        try:
            from achievements import get_achievement_manager
            from achievements_data import get_achievements_for

            manager = get_achievement_manager()
            if not manager:
                return

            achievements = get_achievements_for(game_name)
            count = 0
            for ach in achievements:
                if manager.is_unlocked(ach["id"]):
                    manager.reset_achievement(ach["id"])
                    count += 1

            print(f"[Settings] Reset {count} {game_name} achievements")
            self._cache_message = f"Reset {count} {game_name} achievements!"
            self._cache_message_time = pygame.time.get_ticks()
            self._ach_reset_modal = None

        except Exception as e:
            print(f"[Settings] Error resetting game achievements: {e}")

    def _export_achievement_data(self):
        """Export achievement progress data"""
        try:
            from achievements import get_achievement_manager

            manager = get_achievement_manager()
            if not manager:
                return

            export_path = os.path.join(DATA_DIR, "achievements_export.json")

            # Get list of unlocked achievement IDs
            unlocked_ids = [
                aid
                for aid, data in manager.progress.items()
                if data.get("unlocked", False)
            ]

            data = {
                "unlocked": unlocked_ids,
                "progress": manager.progress,
                "stats": manager.stats,
                "export_time": str(pygame.time.get_ticks()),
            }

            with open(export_path, "w") as f:
                json.dump(data, f, indent=2)

            print(f"[Settings] Exported achievements to {export_path}")
            self._cache_message = f"Exported to {export_path}"
            self._cache_message_time = pygame.time.get_ticks()

        except Exception as e:
            print(f"[Settings] Error exporting achievements: {e}")
            self._cache_message = f"Export error: {e}"
            self._cache_message_time = pygame.time.get_ticks()

    def _handle_ach_reset_modal(self, ctrl):
        """Handle input for achievement reset modals"""
        if not self._ach_reset_modal:
            return False

        consumed = False

        # Navigation
        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            if self._ach_reset_selected > 0:
                self._ach_reset_selected -= 1
                # Adjust scroll
                if self._ach_reset_selected < self._ach_reset_scroll:
                    self._ach_reset_scroll = self._ach_reset_selected
            consumed = True

        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            if self._ach_reset_selected < len(self._ach_reset_list) - 1:
                self._ach_reset_selected += 1
                # Adjust scroll (show 6 items max)
                if self._ach_reset_selected >= self._ach_reset_scroll + 6:
                    self._ach_reset_scroll = self._ach_reset_selected - 5
            consumed = True

        # Confirm selection
        if ctrl.is_button_just_pressed("A"):
            ctrl.consume_button("A")
            if self._ach_reset_modal == "game_select":
                # Selected a game - open its achievements
                game = self._ach_reset_list[self._ach_reset_selected]
                self._open_specific_achievement_reset(game)
            elif self._ach_reset_modal == "specific_reset":
                # Reset the selected achievement
                if self._ach_reset_list:
                    self._reset_specific_achievement(
                        self._ach_reset_list[self._ach_reset_selected]
                    )
            elif self._ach_reset_modal == "view_unlocked":
                # Just viewing - A does nothing or could show details
                pass
            consumed = True

        # Cancel / Back
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            if self._ach_reset_modal == "specific_reset":
                # Go back to game select
                self._open_game_achievement_selector()
            else:
                self._ach_reset_modal = None
            consumed = True

        # Reset all for current game (L button)
        if self._ach_reset_modal == "specific_reset" and ctrl.is_button_just_pressed(
            "L"
        ):
            ctrl.consume_button("L")
            self._reset_all_game_achievements(self._ach_reset_game)
            consumed = True

        return consumed

    def _draw_ach_reset_modal(self, surf):
        """Draw achievement reset modal"""
        if not self._ach_reset_modal:
            return

        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))

        # Modal box
        modal_w = int(self.width * 0.85)
        modal_h = int(self.height * 0.7)
        modal_x = (self.width - modal_w) // 2
        modal_y = (self.height - modal_h) // 2

        pygame.draw.rect(surf, ui_colors.COLOR_BG, (modal_x, modal_y, modal_w, modal_h))
        pygame.draw.rect(
            surf, ui_colors.COLOR_BORDER, (modal_x, modal_y, modal_w, modal_h), 2
        )

        # Title
        if self._ach_reset_modal == "game_select":
            title = "Select Game to Reset"
        elif self._ach_reset_modal == "specific_reset":
            title = f"Reset {self._ach_reset_game} Achievements"
        elif self._ach_reset_modal == "view_unlocked":
            title = "Unlocked Achievements"
        else:
            title = "Achievements"

        title_surf = self.font_header.render(title, True, ui_colors.COLOR_TEXT)
        surf.blit(title_surf, (modal_x + 10, modal_y + 8))

        # List items
        y_start = modal_y + 35
        item_height = 28
        visible_items = 6

        for i, item in enumerate(
            self._ach_reset_list[
                self._ach_reset_scroll : self._ach_reset_scroll + visible_items
            ]
        ):
            actual_idx = self._ach_reset_scroll + i
            y = y_start + i * item_height
            is_selected = actual_idx == self._ach_reset_selected

            # Background
            if is_selected:
                pygame.draw.rect(
                    surf,
                    ui_colors.COLOR_HIGHLIGHT,
                    (modal_x + 5, y, modal_w - 10, item_height - 2),
                )

            # Text
            if self._ach_reset_modal == "game_select":
                text = item
            else:
                # Achievement dict
                text = f"{item.get('name', 'Unknown')}"
                if len(text) > 35:
                    text = text[:32] + "..."

            text_color = (255, 255, 255) if is_selected else ui_colors.COLOR_TEXT
            text_surf = self.font_text.render(text, True, text_color)
            surf.blit(text_surf, (modal_x + 12, y + 4))

            # Points for achievements
            if self._ach_reset_modal != "game_select" and isinstance(item, dict):
                pts = item.get("points", 0)
                pts_surf = self.font_small.render(
                    f"{pts}pts", True, (255, 215, 0) if is_selected else (150, 150, 100)
                )
                surf.blit(pts_surf, (modal_x + modal_w - 50, y + 6))

        # Scroll indicators
        if self._ach_reset_scroll > 0:
            up_arrow = self.font_text.render("^", True, (100, 200, 100))
            surf.blit(up_arrow, (modal_x + modal_w - 20, y_start - 15))

        if self._ach_reset_scroll + visible_items < len(self._ach_reset_list):
            down_arrow = self.font_text.render("v", True, (100, 200, 100))
            surf.blit(
                down_arrow,
                (modal_x + modal_w - 20, y_start + visible_items * item_height - 10),
            )

        # Hints at bottom
        if self._ach_reset_modal == "game_select":
            hint = "A:Select  B:Back"
        elif self._ach_reset_modal == "specific_reset":
            hint = "A:Reset  L:Reset All  B:Back"
        else:
            hint = "B:Back"

        hint_surf = self.font_small.render(hint, True, (100, 100, 100))
        surf.blit(hint_surf, (modal_x + 10, modal_y + modal_h - 18))

    def handle_controller(self, ctrl):
        # Delegate to sub-screen if active (but not on the frame it was just opened,
        # to prevent the activating button press from bleeding through)
        if self.sub_screen:
            if pygame.time.get_ticks() != self._sub_screen_open_tick:
                result = self.sub_screen.handle_controller(ctrl)
                # Check if sub_screen closed (either via callback or visible flag)
                if self.sub_screen and not self.sub_screen.visible:
                    self.sub_screen = None
                return result
            return True

        # Handle achievement reset modal if open
        if self._ach_reset_modal:
            return self._handle_ach_reset_modal(ctrl)

        consumed = False

        # L/R shoulder buttons still work for quick tab switching
        if ctrl.is_button_just_pressed("L"):
            ctrl.consume_button("L")
            self._change_tab(-1)
            self.tab_focus = True
            consumed = True

        if ctrl.is_button_just_pressed("R"):
            ctrl.consume_button("R")
            self._change_tab(1)
            self.tab_focus = True
            consumed = True

        # D-pad navigation depends on focus mode
        if self.tab_focus:
            # In tab focus: left/right changes tabs, down enters options
            if ctrl.is_dpad_just_pressed("left"):
                ctrl.consume_dpad("left")
                self._change_tab(-1)
                consumed = True

            if ctrl.is_dpad_just_pressed("right"):
                ctrl.consume_dpad("right")
                self._change_tab(1)
                consumed = True

            if ctrl.is_dpad_just_pressed("down"):
                ctrl.consume_dpad("down")
                self.tab_focus = False
                self.selected_option = 0
                consumed = True

            # A button also enters options
            if ctrl.is_button_just_pressed("A"):
                ctrl.consume_button("A")
                self.tab_focus = False
                self.selected_option = 0
                consumed = True
        else:
            # In options focus: up/down navigates, left/right adjusts values
            if ctrl.is_dpad_just_pressed("up"):
                ctrl.consume_dpad("up")
                if self.selected_option > 0:
                    self.selected_option -= 1
                else:
                    # At top of options, go back to tab focus
                    self.tab_focus = True
                consumed = True

            if ctrl.is_dpad_just_pressed("down"):
                ctrl.consume_dpad("down")
                if self.selected_option < len(self.current_options()) - 1:
                    self.selected_option += 1
                    # Reset dev mode counter if we moved
                    self._dev_mode_counter = 0
                else:
                    # At bottom of list - check for secret dev mode activation
                    if self.current_tab() == "Info":
                        self._dev_mode_counter += 1
                        print(
                            f"[Settings] Dev mode counter: {self._dev_mode_counter}/10"
                        )
                        if self._dev_mode_counter >= 10 and not self._dev_mode_active:
                            self._dev_mode_active = True
                            self._dev_mode_counter = 0
                            # Set global dev mode flag
                            import builtins

                            builtins.SINEW_DEV_MODE = True
                            print("[Settings] *** DEV MODE ACTIVATED ***")
                            # Add Dev tab if not already present
                            if "Dev" not in self.tabs:
                                self.tabs.append("Dev")
                            self._cache_message = "Dev Mode Activated!"
                            self._cache_message_time = pygame.time.get_ticks()

                            # Save dev_mode to settings
                            try:
                                settings = load_sinew_settings()
                                settings["dev_mode"] = True
                                save_sinew_settings(settings)
                            except Exception:
                                pass

                            # Trigger Dev Mode achievement instantly
                            try:
                                from achievements import (
                                    get_achievement_manager,
                                    get_achievement_notification,
                                )

                                manager = get_achievement_manager()
                                notif = get_achievement_notification()
                                if manager and notif:
                                    dev_ach = {
                                        "id": "SINEW_063",  # Updated: was 062, shifted +1 after adding Legendary Birds
                                        "name": "Dev Mode Discovered!",
                                        "desc": "Find the secret Dev Mode!",
                                        "game": "Sinew",
                                        "category": "Trainer",
                                        "points": 50,
                                    }
                                    if not manager.is_unlocked(dev_ach["id"]):
                                        manager.unlock(dev_ach["id"], dev_ach)
                                        print(
                                            "[Settings] Dev Mode achievement unlocked!"
                                        )
                                    else:
                                        print(
                                            "[Settings] Dev Mode achievement already unlocked"
                                        )
                            except Exception as e:
                                print(f"[Settings] Dev mode achievement error: {e}")
                        elif self._dev_mode_active and self._dev_mode_counter >= 3:
                            # In dev mode, pressing down 3 more times unlocks Debug Tester achievement AND triggers test notification
                            self._dev_mode_counter = 0
                            try:
                                from achievements import (
                                    get_achievement_manager,
                                    get_achievement_notification,
                                )

                                manager = get_achievement_manager()
                                notif = get_achievement_notification()

                                # Unlock Debug Tester achievement if not already unlocked
                                if manager and notif:
                                    debug_ach = {
                                        "id": "SINEW_064",  # Updated: was 063, shifted +1 after adding Legendary Birds
                                        "name": "Debug Tester!",
                                        "desc": "Trigger the debug test in Dev Mode!",
                                        "game": "Sinew",
                                        "category": "Trainer",
                                        "points": 25,
                                    }
                                    if not manager.is_unlocked(debug_ach["id"]):
                                        manager.unlock(debug_ach["id"], debug_ach)
                                        self._cache_message = "Debug Tester unlocked!"
                                        print(
                                            "[Settings] Debug Tester achievement unlocked!"
                                        )
                                    else:
                                        # Already unlocked - just show test notification
                                        print(
                                            "[Settings] Debug Tester already unlocked, showing test notification"
                                        )
                                        test_ach = {
                                            "id": "test_001",
                                            "name": "Test Achievement",
                                            "desc": "This is a test notification",
                                            "game": "Sinew",
                                            "points": 50,
                                        }
                                        notif.queue_achievement(test_ach)
                                        self._cache_message = "Test notif queued!"
                                    self._cache_message_time = pygame.time.get_ticks()
                            except Exception as e:
                                print(f"[Settings] Debug Tester achievement error: {e}")
                    else:
                        self._dev_mode_counter = 0
                consumed = True

            # Adjust values with Left/Right d-pad
            if ctrl.is_dpad_just_pressed("left"):
                ctrl.consume_dpad("left")
                if self._adjust_option(-1):
                    consumed = True

            if ctrl.is_dpad_just_pressed("right"):
                ctrl.consume_dpad("right")
                if self._adjust_option(1):
                    consumed = True

            # Activate / Select with A
            if ctrl.is_button_just_pressed("A"):
                ctrl.consume_button("A")
                self._activate_option()
                consumed = True

        # Close modal with B (works in both modes)
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            if self.tab_focus:
                self.on_back()
            else:
                # Go back to tab focus first
                self.tab_focus = True
            consumed = True

        return consumed

    # -------------------
    # Keyboard / Pygame events
    # -------------------
    def handle_events(self, events):
        # Delegate to sub-screen if active (but not on the frame it was just opened,
        # to prevent the activating keypress from bleeding through)
        if self.sub_screen:
            if pygame.time.get_ticks() != self._sub_screen_open_tick:
                self.sub_screen.update(events)
                # Check if sub_screen closed (either via callback or visible flag)
                if self.sub_screen and not self.sub_screen.visible:
                    self.sub_screen = None
            return

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.tab_focus:
                        self.on_back()
                    else:
                        self.tab_focus = True
                # Tab switching with Q/E or Tab+Shift (always works)
                elif event.key == pygame.K_q or event.key == pygame.K_PAGEUP:
                    self._change_tab(-1)
                    self.tab_focus = True
                elif event.key == pygame.K_e or event.key == pygame.K_PAGEDOWN:
                    self._change_tab(1)
                    self.tab_focus = True
                elif event.key == pygame.K_TAB:
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        self._change_tab(-1)
                    else:
                        self._change_tab(1)
                    self.tab_focus = True
                # Navigation depends on focus mode
                elif event.key == pygame.K_UP:
                    if not self.tab_focus:
                        if self.selected_option > 0:
                            self.selected_option -= 1
                        else:
                            self.tab_focus = True
                elif event.key == pygame.K_DOWN:
                    if self.tab_focus:
                        self.tab_focus = False
                        self.selected_option = 0
                    else:
                        if self.selected_option < len(self.current_options()) - 1:
                            self.selected_option += 1
                elif event.key == pygame.K_LEFT:
                    if self.tab_focus:
                        self._change_tab(-1)
                    else:
                        self._adjust_option(-1)
                elif event.key == pygame.K_RIGHT:
                    if self.tab_focus:
                        self._change_tab(1)
                    else:
                        self._adjust_option(1)
                # Activate
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    if self.tab_focus:
                        self.tab_focus = False
                        self.selected_option = 0
                    else:
                        self._activate_option()

    # -------------------
    # Drawing
    # -------------------
    def draw(self, surf):
        # Draw sub-screen if active
        if self.sub_screen:
            self.sub_screen.draw(surf)
            return

        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(230)
        overlay.fill(ui_colors.COLOR_BG)
        surf.blit(overlay, (0, 0))

        # Border
        pygame.draw.rect(
            surf, ui_colors.COLOR_BORDER, (0, 0, self.width, self.height), 2
        )

        # Title
        title = self.font_header.render("Sinew Setup", True, ui_colors.COLOR_TEXT)
        surf.blit(title, (20, 15))

        # Tab bar background
        tab_bar_rect = pygame.Rect(0, 45, self.width, 30)
        pygame.draw.rect(surf, ui_colors.COLOR_HEADER, tab_bar_rect)
        pygame.draw.line(surf, ui_colors.COLOR_BORDER, (0, 75), (self.width, 75), 1)

        # Tabs
        tab_x = 15
        for i, tab in enumerate(self.tabs):
            is_selected = i == self.selected_tab
            is_focused = is_selected and self.tab_focus

            # Tab background for selected
            tab_surf = self.font_text.render(tab, True, ui_colors.COLOR_TEXT)
            tab_width = tab_surf.get_width() + 16

            if is_selected:
                tab_rect = pygame.Rect(tab_x - 8, 48, tab_width, 24)
                pygame.draw.rect(
                    surf, ui_colors.COLOR_BUTTON, tab_rect, border_radius=3
                )
                # Cyan border when focused, dimmer when not
                border_color = (
                    ui_colors.COLOR_HIGHLIGHT if is_focused else ui_colors.COLOR_BORDER
                )
                pygame.draw.rect(surf, border_color, tab_rect, 2, border_radius=3)
                text_color = (
                    ui_colors.COLOR_HIGHLIGHT if is_focused else ui_colors.COLOR_TEXT
                )
                tab_surf = self.font_text.render(tab, True, text_color)

            surf.blit(tab_surf, (tab_x, 52))
            tab_x += tab_width + 8

        # Navigation hints
        if self.tab_focus:
            hint_text = "<  >  to switch tabs"
        else:
            hint_text = "L/R"
        hint_surf = self.font_small.render(hint_text, True, ui_colors.COLOR_BORDER)
        surf.blit(hint_surf, (self.width - hint_surf.get_width() - 10, 52))

        # Draw options for current tab
        y_start = 85
        option_height = 32
        max_visible = (self.height - y_start - 30) // option_height

        options = self.current_options()

        # Calculate scroll offset if needed
        scroll_offset = 0
        if self.selected_option >= max_visible:
            scroll_offset = self.selected_option - max_visible + 1

        for i, option in enumerate(options):
            if i < scroll_offset:
                continue
            if i >= scroll_offset + max_visible:
                break

            y = y_start + (i - scroll_offset) * option_height
            is_selected = (i == self.selected_option) and not self.tab_focus

            # Highlight selected option
            option_rect = pygame.Rect(10, y, self.width - 20, option_height - 2)
            if is_selected:
                pygame.draw.rect(
                    surf, ui_colors.COLOR_BUTTON, option_rect, border_radius=4
                )
                pygame.draw.rect(
                    surf, ui_colors.COLOR_HIGHLIGHT, option_rect, 2, border_radius=4
                )

                # Selection cursor
                cursor = self.font_text.render(">", True, ui_colors.COLOR_HIGHLIGHT)
                surf.blit(cursor, (15, y + 8))

            # Draw option name
            name_color = (
                ui_colors.COLOR_HIGHLIGHT if is_selected else ui_colors.COLOR_TEXT
            )
            name_surf = self.font_text.render(option["name"], True, name_color)
            surf.blit(name_surf, (35, y + 8))

            # Draw value based on type
            self._draw_option_value(surf, option, y, option_height, is_selected)

        # Scroll indicators
        if scroll_offset > 0:
            up_arrow = self.font_text.render("^", True, ui_colors.COLOR_BORDER)
            surf.blit(up_arrow, (self.width // 2, y_start - 12))
        if scroll_offset + max_visible < len(options):
            down_arrow = self.font_text.render("v", True, ui_colors.COLOR_BORDER)
            surf.blit(down_arrow, (self.width // 2, self.height - 35))

        # Controller hints at bottom (context-aware)
        if self.tab_focus:
            hints = "D-Pad: Switch Tabs   A/Down: Enter Options   B: Close"
        else:
            hints = "D-Pad: Navigate/Adjust   A: Select   B: Back to Tabs"
        hint_surf = self.font_small.render(hints, True, ui_colors.COLOR_BORDER)
        hint_rect = hint_surf.get_rect(centerx=self.width // 2, bottom=self.height - 8)
        surf.blit(hint_surf, hint_rect)

        # Draw cache message if active
        if self._cache_message:
            elapsed = (pygame.time.get_ticks() - self._cache_message_time) / 1000.0
            if elapsed < 2.5:  # Show for 2.5 seconds
                # Fade out in last 0.5 seconds
                alpha = 255 if elapsed < 2.0 else int(255 * (2.5 - elapsed) / 0.5)

                msg_surf = self.font_text.render(
                    self._cache_message, True, ui_colors.COLOR_SUCCESS
                )
                msg_rect = msg_surf.get_rect(
                    centerx=self.width // 2, centery=self.height // 2
                )

                # Background box
                box_rect = msg_rect.inflate(20, 16)
                box_surf = pygame.Surface(box_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(
                    box_surf, (30, 50, 40, alpha), box_surf.get_rect(), border_radius=8
                )
                pygame.draw.rect(
                    box_surf,
                    (100, 255, 100, alpha),
                    box_surf.get_rect(),
                    2,
                    border_radius=8,
                )
                surf.blit(box_surf, box_rect)

                msg_surf.set_alpha(alpha)
                surf.blit(msg_surf, msg_rect)
            else:
                self._cache_message = None

        # Draw achievement reset modal on top if open
        if self._ach_reset_modal:
            self._draw_ach_reset_modal(surf)

    def _draw_option_value(self, surf, option, y, height, is_selected):
        """Draw the value portion of an option"""
        opt_type = option["type"]
        right_x = self.width - 25
        center_y = y + height // 2

        if opt_type == "toggle":
            val = option["value"]
            val_text = "ON" if val else "OFF"
            val_color = ui_colors.COLOR_SUCCESS if val else ui_colors.COLOR_ERROR

            # Draw toggle box
            box_rect = pygame.Rect(right_x - 50, y + 6, 45, 20)
            pygame.draw.rect(surf, ui_colors.COLOR_HEADER, box_rect, border_radius=10)

            # Toggle indicator
            indicator_x = right_x - 15 if val else right_x - 45
            indicator_rect = pygame.Rect(indicator_x, y + 8, 16, 16)
            pygame.draw.rect(surf, val_color, indicator_rect, border_radius=8)

        elif opt_type == "choice":
            # Show arrows and current value
            val_text = option["value"]
            arrows_color = (
                ui_colors.COLOR_HIGHLIGHT if is_selected else ui_colors.COLOR_BUTTON
            )

            val_surf = self.font_text.render(val_text, True, ui_colors.COLOR_TEXT)
            val_width = val_surf.get_width()

            # Left arrow
            left_arrow = self.font_text.render("<", True, arrows_color)
            surf.blit(left_arrow, (right_x - val_width - 30, y + 8))

            # Value
            surf.blit(val_surf, (right_x - val_width - 10, y + 8))

            # Right arrow
            right_arrow = self.font_text.render(">", True, arrows_color)
            surf.blit(right_arrow, (right_x + 5, y + 8))

        elif opt_type == "label":
            val_surf = self.font_text.render(
                str(option["value"]), True, ui_colors.COLOR_BORDER
            )
            val_rect = val_surf.get_rect(right=right_x, centery=center_y)
            surf.blit(val_surf, val_rect)

        elif opt_type == "path":
            # Show truncated path with folder icon
            path = option["value"]
            if len(path) > 20:
                path = "..." + path[-17:]
            val_surf = self.font_small.render(path, True, ui_colors.COLOR_TEXT)
            val_rect = val_surf.get_rect(right=right_x, centery=center_y)
            surf.blit(val_surf, val_rect)

        elif opt_type == "slider":
            slider_index = option.get("slider_index", 0)
            labels = option.get("labels", [])
            max_idx = max(len(labels) - 1, 1)
            label_text = labels[slider_index] if labels else str(slider_index)
            arrows_color = ui_colors.COLOR_HIGHLIGHT if is_selected else ui_colors.COLOR_BUTTON

            # Track bar
            bar_width = 72
            bar_x = right_x - bar_width - 32
            bar_y = center_y - 4
            bar_h = 8
            pygame.draw.rect(surf, ui_colors.COLOR_HEADER,
                             pygame.Rect(bar_x, bar_y, bar_width, bar_h), border_radius=4)
            # Fill
            fill_w = int(bar_width * slider_index / max_idx)
            if fill_w > 0:
                fill_color = ui_colors.COLOR_HIGHLIGHT if is_selected else ui_colors.COLOR_BORDER
                pygame.draw.rect(surf, fill_color,
                                 pygame.Rect(bar_x, bar_y, fill_w, bar_h), border_radius=4)
            # Arrows
            surf.blit(self.font_text.render("<", True, arrows_color), (bar_x - 14, center_y - 7))
            surf.blit(self.font_text.render(">", True, arrows_color), (bar_x + bar_width + 4, center_y - 7))
            # Label
            lbl = self.font_text.render(label_text, True, ui_colors.COLOR_TEXT)
            surf.blit(lbl, lbl.get_rect(left=bar_x + bar_width + 18, centery=center_y))

        elif opt_type == "button":
            # Show press indicator when selected
            if is_selected:
                btn_text = "[Press A]"
                btn_surf = self.font_small.render(
                    btn_text, True, ui_colors.COLOR_HIGHLIGHT
                )
                btn_rect = btn_surf.get_rect(right=right_x, centery=center_y)
                surf.blit(btn_surf, btn_rect)


# -----------------------------
# Changelog Screen
# -----------------------------
class ChangelogScreen:
    """Screen showing changelog.txt content with scrolling"""

    def __init__(self, width, height, close_callback=None):
        self.width = width
        self.height = height
        self.visible = True
        self.close_callback = close_callback
        self.scroll = 0

        # Fonts
        try:
            self.font_header = pygame.font.Font(FONT_PATH, 16)
            self.font_text = pygame.font.Font(FONT_PATH, 11)
            self.font_small = pygame.font.Font(FONT_PATH, 9)
        except Exception:
            self.font_header = pygame.font.SysFont(None, 22)
            self.font_text = pygame.font.SysFont(None, 16)
            self.font_small = pygame.font.SysFont(None, 12)

        self.lines = self._load_changelog()

    def _load_changelog(self):
        """Load and parse changelog.txt into (text, style) tuples"""
        changelog_path = os.path.join(EXT_DIR, "changelog.txt")

        lines = []
        try:
            if not os.path.exists(changelog_path):
                print(f"[Changelog] changelog.txt not found at: {changelog_path}")
                lines.append(("changelog.txt not found", "normal"))
                return lines
            with open(changelog_path, "r", encoding="utf-8") as f:
                text = f.read()
            for raw_line in text.splitlines():
                stripped = raw_line.rstrip()
                if not stripped:
                    lines.append(("", "normal"))
                elif stripped.startswith("===") or stripped.startswith("---"):
                    lines.append(("", "normal"))
                elif (
                    stripped.startswith("v")
                    or stripped.startswith("V")
                    or stripped.startswith("[")
                ):
                    lines.append((stripped, "subheader"))
                else:
                    for wrapped in self._word_wrap(stripped, 50):
                        lines.append((wrapped, "normal"))
        except Exception as e:
            print(f"[Changelog] Error loading changelog.txt: {e}")
            lines.append((f"Error: {e}", "normal"))
        return lines

    def _word_wrap(self, text, max_chars):
        """Simple word wrap"""
        words = text.split()
        result = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= max_chars:
                current = (current + " " + word).strip()
            else:
                if current:
                    result.append(current)
                current = word
        if current:
            result.append(current)
        return result if result else [""]

    def handle_controller(self, ctrl):
        """Handle controller input"""
        consumed = False
        if ctrl.is_dpad_just_pressed("up"):
            ctrl.consume_dpad("up")
            self.scroll = max(0, self.scroll - 1)
            consumed = True
        if ctrl.is_dpad_just_pressed("down"):
            ctrl.consume_dpad("down")
            max_scroll = max(0, len(self.lines) - 10)
            self.scroll = min(max_scroll, self.scroll + 1)
            consumed = True
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self._close()
            consumed = True
        return consumed

    def update(self, events):
        """Handle pygame events"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._close()
                elif event.key == pygame.K_UP:
                    self.scroll = max(0, self.scroll - 1)
                elif event.key == pygame.K_DOWN:
                    max_scroll = max(0, len(self.lines) - 10)
                    self.scroll = min(max_scroll, self.scroll + 1)

    def _close(self):
        self.visible = False
        if self.close_callback:
            self.close_callback()

    def draw(self, surf):
        """Draw the changelog screen"""
        # Background overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(240)
        overlay.fill(ui_colors.COLOR_BG)
        surf.blit(overlay, (0, 0))

        pygame.draw.rect(
            surf, ui_colors.COLOR_BORDER, (0, 0, self.width, self.height), 2
        )

        # Title
        title = self.font_header.render("Changelog", True, ui_colors.COLOR_TEXT)
        surf.blit(title, (20, 12))

        close_hint = self.font_small.render("B: Close", True, ui_colors.COLOR_BORDER)
        surf.blit(close_hint, (self.width - close_hint.get_width() - 15, 15))

        # Content area
        content_rect = pygame.Rect(10, 45, self.width - 20, self.height - 75)
        pygame.draw.rect(surf, ui_colors.COLOR_HEADER, content_rect, border_radius=5)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, content_rect, 1, border_radius=5)

        line_height = 16
        max_lines = (content_rect.height - 20) // line_height
        y = content_rect.y + 10

        for _, (text, style) in enumerate(
            self.lines[self.scroll : self.scroll + max_lines]
        ):
            if y > content_rect.bottom - 15:
                break
            if style == "subheader":
                color = ui_colors.COLOR_HIGHLIGHT
                font = self.font_text
            else:
                color = ui_colors.COLOR_TEXT
                font = self.font_small
            if text:
                surf.blit(font.render(text, True, color), (content_rect.x + 15, y))
            y += line_height

        # Scroll indicators
        if self.scroll > 0:
            surf.blit(
                self.font_text.render("^", True, ui_colors.COLOR_HIGHLIGHT),
                (content_rect.right - 20, content_rect.y + 5),
            )
        if self.scroll + max_lines < len(self.lines):
            surf.blit(
                self.font_text.render("v", True, ui_colors.COLOR_HIGHLIGHT),
                (content_rect.right - 20, content_rect.bottom - 20),
            )

        # Hint
        hint = self.font_small.render(
            "Up/Down: Scroll    B: Close", True, ui_colors.COLOR_BORDER
        )
        surf.blit(hint, hint.get_rect(centerx=self.width // 2, bottom=self.height - 8))


# -----------------------------
# About/Legal Screen
# -----------------------------
class AboutLegalScreen:
    """Screen showing About, License, Third-Party, and Acknowledgments tabs"""

    def __init__(self, width, height, close_callback=None):
        self.width = width
        self.height = height
        self.visible = True
        self.close_callback = close_callback

        # Fonts
        try:
            self.font_header = pygame.font.Font(FONT_PATH, 16)
            self.font_text = pygame.font.Font(FONT_PATH, 11)
            self.font_small = pygame.font.Font(FONT_PATH, 9)
        except Exception:
            self.font_header = pygame.font.SysFont(None, 22)
            self.font_text = pygame.font.SysFont(None, 16)
            self.font_small = pygame.font.SysFont(None, 12)

        # Tabs
        self.tabs = ["About", "License", "Third-Party", "Acknowledgments"]
        self.selected_tab = 0
        self.tab_focus = True

        # Scroll state per tab
        self.scroll_offsets = {tab: 0 for tab in self.tabs}

        # Load JSON data
        self.tab_content = {}
        self._load_json_data()

        # Pre-render content for each tab
        self.rendered_content = {}
        self._render_all_content()

        # Link selection for controller navigation
        self.selected_link = 0
        self._link_indices = {}  # {tab: [line_indices that are links]}
        self._build_link_indices()

    def _load_json_data(self):
        """Load JSON files for each tab"""
        json_files = {
            "About": os.path.join(EXT_DIR, "licenses", "about.json"),
            "License": os.path.join(EXT_DIR, "licenses", "sinewLicense.json"),
            "Third-Party": os.path.join(EXT_DIR, "licenses", "3pLicenses.json"),
            "Acknowledgments": os.path.join(EXT_DIR, "licenses", "AKN.json"),
        }

        for tab, filepath in json_files.items():
            try:
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        self.tab_content[tab] = json.load(f)
                else:
                    self.tab_content[tab] = None
                    print(f"[AboutLegal] File not found: {filepath}")
            except Exception as e:
                print(f"[AboutLegal] Error loading {filepath}: {e}")
                self.tab_content[tab] = None

    def _render_all_content(self):
        """Pre-render scrollable content for each tab"""
        for tab in self.tabs:
            lines = self._get_content_lines(tab)
            self.rendered_content[tab] = lines

    def _build_link_indices(self):
        """Build list of line indices that are links for each tab"""
        for tab in self.tabs:
            lines = self.rendered_content.get(tab, [])
            self._link_indices[tab] = [
                i for i, (text, style) in enumerate(lines) if style == "link"
            ]

    def _get_content_lines(self, tab):
        """Convert JSON content to list of (text, style) tuples"""
        lines = []
        data = self.tab_content.get(tab)

        if data is None:
            lines.append(("Content not available", "normal"))
            return lines

        if tab == "About":
            # About format: single object
            if data.get("app_name"):
                lines.append((data["app_name"], "header"))
                lines.append(("", "normal"))
            if data.get("version"):
                lines.append((f"Version: {data['version']}", "normal"))
            if data.get("author"):
                lines.append((f"Author: {data['author']}", "normal"))
            lines.append(("", "normal"))
            if data.get("description"):
                lines.append((data["description"], "normal"))
            lines.append(("", "normal"))
            if data.get("source_url"):
                lines.append((f"Source: {data['source_url']}", "link"))
            if data.get("devlog"):
                lines.append((f"Devlog: {data['devlog']}", "link"))
            if data.get("discord"):
                lines.append((f"Discord: {data['discord']}", "link"))
            lines.append(("", "normal"))
            if data.get("disclaimer"):
                lines.append(("Disclaimer:", "subheader"))
                # Word wrap the disclaimer
                for wrapped in self._word_wrap(data["disclaimer"], 45):
                    lines.append((wrapped, "small"))

        elif tab == "License":
            # License format: sections array
            sections = data.get("sections", [])
            for section in sections:
                if section.get("title"):
                    lines.append((section["title"], "header"))
                    lines.append(("", "normal"))
                for entry in section.get("entries", []):
                    if entry.get("name"):
                        lines.append((entry["name"], "subheader"))
                    for line in entry.get("lines", []):
                        if line:
                            for wrapped in self._word_wrap(line, 50):
                                lines.append((wrapped, "normal"))
                        else:
                            lines.append(("", "normal"))
                    lines.append(("", "normal"))

        elif tab == "Third-Party":
            # Same format as License
            sections = data.get("sections", [])
            for section in sections:
                if section.get("title"):
                    lines.append((section["title"], "header"))
                    lines.append(("", "normal"))
                for entry in section.get("entries", []):
                    if entry.get("name"):
                        lines.append((entry["name"], "subheader"))
                    for line in entry.get("lines", []):
                        if line:
                            for wrapped in self._word_wrap(line, 50):
                                lines.append((wrapped, "normal"))
                        else:
                            lines.append(("", "normal"))
                    lines.append(("", "normal"))

        elif tab == "Acknowledgments":
            # Acknowledgments format: acknowledgments array
            acks = data.get("acknowledgments", [])
            for ack in acks:
                if ack.get("title"):
                    lines.append((ack["title"], "header"))
                    lines.append(("", "normal"))
                if ack.get("text"):
                    for para in ack["text"].split("\n"):
                        if para.strip():
                            for wrapped in self._word_wrap(para, 50):
                                lines.append((wrapped, "normal"))
                        else:
                            lines.append(("", "normal"))
                lines.append(("", "normal"))

        return lines

    def _word_wrap(self, text, max_chars):
        """Simple word wrap"""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines if lines else [""]

    def handle_controller(self, ctrl):
        """Handle controller input"""
        consumed = False
        current_tab = self.tabs[self.selected_tab]
        link_indices = self._link_indices.get(current_tab, [])

        # Tab switching with L/R
        if ctrl.is_button_just_pressed("L"):
            ctrl.consume_button("L")
            self.selected_tab = (self.selected_tab - 1) % len(self.tabs)
            self.tab_focus = True
            self.selected_link = 0
            consumed = True

        if ctrl.is_button_just_pressed("R"):
            ctrl.consume_button("R")
            self.selected_tab = (self.selected_tab + 1) % len(self.tabs)
            self.tab_focus = True
            self.selected_link = 0
            consumed = True

        # D-pad navigation
        if self.tab_focus:
            if ctrl.is_dpad_just_pressed("left"):
                ctrl.consume_dpad("left")
                self.selected_tab = (self.selected_tab - 1) % len(self.tabs)
                self.selected_link = 0
                consumed = True

            if ctrl.is_dpad_just_pressed("right"):
                ctrl.consume_dpad("right")
                self.selected_tab = (self.selected_tab + 1) % len(self.tabs)
                self.selected_link = 0
                consumed = True

            if ctrl.is_dpad_just_pressed("down"):
                ctrl.consume_dpad("down")
                self.tab_focus = False
                self.selected_link = 0
                consumed = True

            if ctrl.is_button_just_pressed("A"):
                ctrl.consume_button("A")
                self.tab_focus = False
                self.selected_link = 0
                consumed = True
        else:
            # Content navigation - move between links or scroll
            if ctrl.is_dpad_just_pressed("up"):
                ctrl.consume_dpad("up")
                if link_indices and self.selected_link > 0:
                    # Move to previous link
                    self.selected_link -= 1
                    # Auto-scroll to keep link visible
                    link_line = link_indices[self.selected_link]
                    if link_line < self.scroll_offsets[current_tab]:
                        self.scroll_offsets[current_tab] = link_line
                else:
                    # Scroll up
                    self.scroll_offsets[current_tab] = max(
                        0, self.scroll_offsets[current_tab] - 1
                    )
                consumed = True

            if ctrl.is_dpad_just_pressed("down"):
                ctrl.consume_dpad("down")
                if link_indices and self.selected_link < len(link_indices) - 1:
                    # Move to next link
                    self.selected_link += 1
                    # Auto-scroll to keep link visible
                    link_line = link_indices[self.selected_link]
                    max_visible = 10
                    if link_line >= self.scroll_offsets[current_tab] + max_visible:
                        self.scroll_offsets[current_tab] = link_line - max_visible + 1
                else:
                    # Scroll down
                    max_scroll = max(
                        0, len(self.rendered_content.get(current_tab, [])) - 10
                    )
                    self.scroll_offsets[current_tab] = min(
                        max_scroll, self.scroll_offsets[current_tab] + 1
                    )
                consumed = True

            # Open selected link with A
            if ctrl.is_button_just_pressed("A"):
                ctrl.consume_button("A")
                if link_indices and 0 <= self.selected_link < len(link_indices):
                    link_line = link_indices[self.selected_link]
                    lines = self.rendered_content.get(current_tab, [])
                    if link_line < len(lines):
                        text, style = lines[link_line]
                        if ": " in text:
                            url = text.split(": ", 1)[1]
                            try:
                                webbrowser.open(url)
                                print(f"[AboutLegal] Opened: {url}")
                            except Exception as e:
                                print(f"[AboutLegal] Failed to open URL: {e}")
                consumed = True

        # Close with B
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            if self.tab_focus:
                self._close()
            else:
                self.tab_focus = True
            consumed = True

        return consumed

    def update(self, events):
        """Handle pygame events"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                current_tab = self.tabs[self.selected_tab]

                if event.key == pygame.K_ESCAPE:
                    if self.tab_focus:
                        self._close()
                    else:
                        self.tab_focus = True
                elif event.key == pygame.K_LEFT:
                    if self.tab_focus:
                        self.selected_tab = (self.selected_tab - 1) % len(self.tabs)
                elif event.key == pygame.K_RIGHT:
                    if self.tab_focus:
                        self.selected_tab = (self.selected_tab + 1) % len(self.tabs)
                elif event.key == pygame.K_UP:
                    if not self.tab_focus:
                        self.scroll_offsets[current_tab] = max(
                            0, self.scroll_offsets[current_tab] - 1
                        )
                elif event.key == pygame.K_DOWN:
                    if self.tab_focus:
                        self.tab_focus = False
                    else:
                        max_scroll = max(
                            0, len(self.rendered_content.get(current_tab, [])) - 10
                        )
                        self.scroll_offsets[current_tab] = min(
                            max_scroll, self.scroll_offsets[current_tab] + 1
                        )
                elif event.key == pygame.K_RETURN:
                    if self.tab_focus:
                        self.tab_focus = False

            # Handle mouse clicks on links
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and hasattr(self, "_link_rects"):
                    for link_rect, url in self._link_rects:
                        if link_rect.collidepoint(event.pos):
                            try:
                                webbrowser.open(url)
                                print(f"[AboutLegal] Opened: {url}")
                            except Exception as e:
                                print(f"[AboutLegal] Failed to open URL: {e}")
                            break

    def _close(self):
        """Close the screen"""
        self.visible = False
        if self.close_callback:
            self.close_callback()

    def draw(self, surf):
        """Draw the About/Legal screen"""
        # Background overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(240)
        overlay.fill(ui_colors.COLOR_BG)
        surf.blit(overlay, (0, 0))

        # Border
        pygame.draw.rect(
            surf, ui_colors.COLOR_BORDER, (0, 0, self.width, self.height), 2
        )

        # Title
        title = self.font_header.render("About / Legal", True, ui_colors.COLOR_TEXT)
        surf.blit(title, (20, 12))

        # Close hint
        close_hint = self.font_small.render("B: Close", True, ui_colors.COLOR_BORDER)
        surf.blit(close_hint, (self.width - close_hint.get_width() - 15, 15))

        # Tab bar
        tab_y = 40
        tab_x = 10
        for i, tab in enumerate(self.tabs):
            is_selected = i == self.selected_tab
            is_focused = is_selected and self.tab_focus

            # Shorter names for display
            display_name = tab
            if tab == "Third-Party":
                display_name = "3rd Party"
            elif tab == "Acknowledgments":
                display_name = "Thanks"

            tab_surf = self.font_small.render(display_name, True, ui_colors.COLOR_TEXT)
            tab_width = tab_surf.get_width() + 14

            tab_rect = pygame.Rect(tab_x, tab_y, tab_width, 22)

            if is_selected:
                pygame.draw.rect(
                    surf, ui_colors.COLOR_BUTTON, tab_rect, border_radius=3
                )
                border_color = (
                    ui_colors.COLOR_HIGHLIGHT if is_focused else ui_colors.COLOR_BORDER
                )
                pygame.draw.rect(surf, border_color, tab_rect, 2, border_radius=3)
                text_color = (
                    ui_colors.COLOR_HIGHLIGHT if is_focused else ui_colors.COLOR_TEXT
                )
                tab_surf = self.font_small.render(display_name, True, text_color)

            surf.blit(tab_surf, (tab_x + 7, tab_y + 5))
            tab_x += tab_width + 5

        # Content area
        content_rect = pygame.Rect(10, 70, self.width - 20, self.height - 100)
        pygame.draw.rect(surf, ui_colors.COLOR_HEADER, content_rect, border_radius=5)
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, content_rect, 1, border_radius=5)

        # Draw content
        current_tab = self.tabs[self.selected_tab]
        lines = self.rendered_content.get(current_tab, [])
        scroll = self.scroll_offsets[current_tab]

        y = content_rect.y + 10
        line_height = 16
        max_lines = (content_rect.height - 20) // line_height

        # Track clickable links
        self._link_rects = []

        # Get link indices for highlighting
        link_indices = self._link_indices.get(current_tab, [])

        for i, (text, style) in enumerate(lines[scroll : scroll + max_lines]):
            if y > content_rect.bottom - 15:
                break

            actual_line_index = scroll + i
            is_selected_link = (
                not self.tab_focus
                and actual_line_index in link_indices
                and link_indices.index(actual_line_index) == self.selected_link
            )

            if style == "header":
                color = ui_colors.COLOR_HIGHLIGHT
                font = self.font_text
            elif style == "subheader":
                color = ui_colors.COLOR_TEXT
                font = self.font_text
            elif style == "small":
                color = ui_colors.COLOR_BORDER
                font = self.font_small
            elif style == "link":
                if is_selected_link:
                    color = (255, 255, 100)  # Yellow highlight for selected link
                else:
                    color = (100, 180, 255)  # Light blue for clickable links
                font = self.font_small
            else:
                color = ui_colors.COLOR_TEXT
                font = self.font_small

            if text:
                text_surf = font.render(text, True, color)
                text_x = content_rect.x + 15

                # Draw selection indicator for selected link
                if is_selected_link:
                    # Draw arrow indicator
                    arrow = self.font_small.render(">", True, (255, 255, 100))
                    surf.blit(arrow, (content_rect.x + 5, y))

                surf.blit(text_surf, (text_x, y))

                # Track link for click detection
                if style == "link" and ": " in text:
                    url = text.split(": ", 1)[1]
                    link_rect = pygame.Rect(
                        text_x, y, text_surf.get_width(), line_height
                    )
                    self._link_rects.append((link_rect, url))

            y += line_height

        # Scroll indicators
        if scroll > 0:
            up_arrow = self.font_text.render("^", True, ui_colors.COLOR_HIGHLIGHT)
            surf.blit(up_arrow, (content_rect.right - 20, content_rect.y + 5))

        if scroll + max_lines < len(lines):
            down_arrow = self.font_text.render("v", True, ui_colors.COLOR_HIGHLIGHT)
            surf.blit(down_arrow, (content_rect.right - 20, content_rect.bottom - 20))

        # Navigation hints
        if self.tab_focus:
            hints = "< > Switch Tabs    Down/A: Scroll    B: Close"
        else:
            hints = "Up/Down: Scroll    B: Back to Tabs"
        hint_surf = self.font_small.render(hints, True, ui_colors.COLOR_BORDER)
        hint_rect = hint_surf.get_rect(centerx=self.width // 2, bottom=self.height - 8)
        surf.blit(hint_surf, hint_rect)