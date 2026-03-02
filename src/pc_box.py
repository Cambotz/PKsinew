#!/usr/bin/env python3

"""
pc_box.py — PCBox

Composition root for the PC Box screen. All logic lives in the mixin files below;
this file wires them together and owns __init__.

Mixins:
  PCBoxDrawMixin         ui_pcbox_draw.py        rendering & drawing
  PCBoxInputMixin        pcbox_input.py          controller & keyboard input
  PCBoxTransferMixin     pcbox_transfer.py       move / transfer logic
  PCBoxEvolutionMixin    pcbox_evolution.py      trade evolution handling
  PCBoxAchievementsMixin pcbox_achievements.py   achievement tracking & export
  PCBoxDataMixin         pcbox_data.py           data management, navigation, mouse, grid
"""

import os

import pygame
from config import SPRITES_DIR
from gif_sprite_handler import get_sprite_cache
from save_data_manager import get_manager
from ui_components import Button

# Try to import Sinew storage
try:
    from sinew_storage import get_sinew_storage

    SINEW_STORAGE_AVAILABLE = True
except ImportError:
    get_sinew_storage = None
    SINEW_STORAGE_AVAILABLE = False
    print("[PCBox] sinew_storage not available")

from controller import NavigableList, get_controller
from ui_pcbox_draw import PCBoxDrawMixin
from pcbox_achievements import PCBoxAchievementsMixin
from pcbox_data import PCBoxDataMixin
from pcbox_evolution import PCBoxEvolutionMixin
from pcbox_input import PCBoxInputMixin
from pcbox_transfer import PCBoxTransferMixin

class PCBox(  # pylint: disable=too-many-instance-attributes
    PCBoxDrawMixin,
    PCBoxInputMixin,
    PCBoxTransferMixin,
    PCBoxEvolutionMixin,
    PCBoxAchievementsMixin,
    PCBoxDataMixin,
):
    """PC Box screen — composition of all PCBox mixin classes."""
    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        width,
        height,
        font,
        close_callback,
        prev_game_callback=None,
        next_game_callback=None,
        get_current_game_callback=None,
        party_slot_scale=1.0,  # pylint: disable=unused-argument
        party_slot_x_offset=0,
        is_game_running_callback=None,
        reload_save_callback=None,
        resume_game_callback=None,
    ):
        self.width = width
        self.height = height
        self.font = font
        self.close_callback = close_callback
        self.prev_game_callback = prev_game_callback
        self.next_game_callback = next_game_callback
        self.get_current_game_callback = get_current_game_callback
        self.is_game_running_callback = is_game_running_callback
        self.reload_save_callback = reload_save_callback
        self.resume_game_callback = resume_game_callback
        self.party_slot_scale = 1.2
        self.party_slot_x_offset = party_slot_x_offset

        self.box_index = 0  # 0-13 for boxes 1-14 (or 0-19 for Sinew)
        self.selected_pokemon = None
        self.sub_modal = None  # For summary screen
        self.current_sprite_image = None
        self.current_gif_sprite = None  # For animated showdown sprites

        # Get save data manager
        self.manager = get_manager()

        # Get Sinew storage (cross-game storage)
        self.sinew_storage = get_sinew_storage() if SINEW_STORAGE_AVAILABLE else None

        # Check if we're on Sinew (cross-game mode)
        self.sinew_mode = self._is_sinew_mode()

        # Sinew mode has 120 slots per box with scrolling
        self.sinew_scroll_offset = 0  # Scroll offset for Sinew's 120-slot boxes
        self.sinew_visible_rows = 5  # Number of visible rows at a time
        self.sinew_total_rows = 20  # 120 slots / 6 columns = 20 rows

        # Get sprite cache
        self.sprite_cache = get_sprite_cache()

        # Get controller
        self.controller = get_controller()

        # Box names - use different names for Sinew vs regular games
        if self.sinew_mode:
            self.box_names = [f"STORAGE {i+1}" for i in range(20)]
            self.max_boxes = 20
        else:
            self.box_names = [f"BOX {i+1}" for i in range(14)]
            self.max_boxes = 14

        # Load current box data
        self.current_box_data = []
        self.party_data = []
        self.refresh_data()

        # ------------------- Navigation State -------------------
        # Grid navigation - different for Sinew mode
        if self.sinew_mode:
            # Sinew: 6 columns x 5 visible rows = 30 visible slots (of 120 total)
            self.grid_nav = NavigableList(30, columns=6, wrap=False)
        else:
            # Regular: 6 columns x 5 rows = 30 slots
            self.grid_nav = NavigableList(30, columns=6, wrap=False)
        self.grid_selected = 0  # Currently selected grid slot

        # Party navigation (6 slots)
        self.party_nav = NavigableList(6, columns=2, wrap=True)
        self.party_selected = 0

        # Focus state: 'grid', 'party', 'game_button', 'box_button', 'side_buttons', 'undo_button'
        self.focus_mode = "grid"

        # Side button navigation (Party, Close)
        self.side_button_index = 0  # 0 = Party, 1 = Close

        # ------------------- Options Menu State -------------------
        self.options_menu_open = False
        self.options_menu_items = ["MOVE", "SUMMARY", "RELEASE", "CANCEL"]
        self.options_menu_selected = 0

        # ------------------- Move Mode State -------------------
        self.move_mode = False  # True when holding a Pokemon to move
        self.moving_pokemon = None  # Pokemon data being moved
        self.moving_pokemon_source = (
            None  # {'type': 'box'/'party', 'box': int, 'slot': int, 'game': str}
        )
        self.moving_sprite = None  # Sprite surface for the Pokemon being moved

        # ------------------- Confirmation Dialog State -------------------
        self.confirmation_dialog_open = False
        self.confirmation_dialog_message = ""
        self.confirmation_dialog_callback = None
        self.confirmation_selected = 0  # 0 = Yes, 1 = No

        # ------------------- Evolution Dialog State -------------------
        self.evolution_dialog_open = False
        self.evolution_dialog_pokemon = None  # Pokemon that can evolve
        self.evolution_dialog_info = None  # Evolution info from can_evolve_by_trade
        self.evolution_dialog_location = None  # (box, slot) in Sinew storage
        self.evolution_selected = 0  # 0 = Evolve, 1 = Stop

        # ------------------- Altering Cave "Echoes" Feature -------------------
        # When a Zubat caught in Altering Cave is clicked, show special dialog
        self.altering_cave_dialog_open = False
        self.altering_cave_zubat = None  # The Zubat pokemon data
        self.altering_cave_location = None  # (box, slot) or (save_path, box, slot)
        self.altering_cave_selected = 0  # 0 = Yes, 1 = No

        # Slot machine state for Altering Cave reward
        self.altering_cave_spinner_active = False
        self.altering_cave_spinner_speed = 0  # Current spin speed
        self.altering_cave_spinner_offset = 0.0  # Vertical offset for animation
        self.altering_cave_spinner_result = None  # The Pokemon that was selected
        self.altering_cave_spinner_stopped = False
        self.altering_cave_spinner_show_result = False
        self.altering_cave_result_timer = 0
        self.altering_cave_target_offset = 0  # Target offset to land on result
        self.altering_cave_remaining = []  # Cached list of remaining Pokemon

        # Pulse animation for Altering Cave Zubats
        self._altering_cave_pulse_timer = 0

        # ------------------- Warning Message State -------------------
        self.warning_message = None

        # ------------------- Resume Banner State -------------------
        self._resume_banner_scroll_offset = 0
        self._resume_banner_scroll_speed = 1.5
        self._resume_banner_pulse_time = 0
        self._pause_combo_setting = self._load_pause_combo_setting()

        # ------------------- Undo State -------------------
        self.undo_available = False
        self.undo_action = None  # {'type': 'move'/'release', 'data': {...}}
        self.warning_message_timer = 0
        self.warning_message_duration = 120  # frames (2 seconds at 60fps)

        # ------------------- Sprite Area -------------------
        self.sprite_area = pygame.Rect(
            0.02 * width, 0.03 * height, 0.28 * width, 0.45 * height
        )

        # ------------------- Top Buttons -------------------
        self.party_button = Button(
            "Party", rel_rect=(0.02, 0.69, 0.26, 0.09), callback=self.toggle_party_panel
        )
        self.close_button = Button(
            "Close", rel_rect=(0.02, 0.79, 0.26, 0.09), callback=self.close_callback
        )

        # Undo button rect - set dynamically during draw when undo is available
        self.undo_button_rect = None

        # Load undo/refresh icon
        self.undo_icon = None
        self.undo_icon_tinted = None
        self._undo_icon_last_color = None
        try:
            icon_path = os.path.join(SPRITES_DIR, "icons", "refresh-icon.png")
            if os.path.exists(icon_path):
                self.undo_icon = pygame.image.load(icon_path).convert_alpha()
                # Scale to fit button (24x24 for a 32x32 button)
                self.undo_icon = pygame.transform.smoothscale(self.undo_icon, (24, 24))
        except Exception as e:
            print(f"[PCBox] Failed to load undo icon: {e}")

        self.left_game_arrow = Button(
            "<",
            rel_rect=(0.31, 0.02, 0.04, 0.09),
            callback=lambda: self.change_game(-1),
        )
        self.game_button = Button(
            self.get_current_game(),
            rel_rect=(0.36, 0.02, 0.50, 0.09),
            callback=lambda: print(f"Current game: {self.get_current_game()}"),
        )
        self.right_game_arrow = Button(
            ">", rel_rect=(0.87, 0.02, 0.04, 0.09), callback=lambda: self.change_game(1)
        )

        self.left_box_arrow = Button(
            "<", rel_rect=(0.31, 0.12, 0.04, 0.09), callback=self.prev_box
        )
        self.box_button = Button(
            self.get_box_name(self.box_index),
            rel_rect=(0.36, 0.12, 0.50, 0.09),
            callback=lambda: print(f"Box {self.box_index+1} clicked"),
        )
        self.right_box_arrow = Button(
            ">", rel_rect=(0.87, 0.12, 0.04, 0.09), callback=self.next_box
        )

        # ------------------- Info Area -------------------
        self.info_area = pygame.Rect(
            self.sprite_area.x,
            self.party_button.rect.y - 0.27 * height,
            self.sprite_area.width,
            0.25 * height,
        )

        # ------------------- Grid -------------------
        self.grid_cols = 6
        self.grid_rows = 5
        self.grid_rect = pygame.Rect(
            self.sprite_area.right + 0.02 * width,
            0.28 * height,
            width - (self.sprite_area.right + 0.04 * width),
            0.65 * height,
        )

        # ------------------- Party Panel -------------------
        self.party_panel_open = False
        self.party_panel_target_y = 0
        self.party_panel_rect = pygame.Rect(
            self.sprite_area.right,  # start at sprite area right
            -height,  # start off-screen
            (width - self.sprite_area.right) * 0.55,  # half of remaining screen
            height,
        )
        self.party_panel_speed = 15
