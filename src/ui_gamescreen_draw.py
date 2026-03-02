#!/usr/bin/env python3

"""
ui_gamescreen_draw.py - GameScreen rendering mixin

Contains the two drawing methods for the Sinew main menu screen:

  draw(surf)          — full-frame render: background, modal or menu button,
                        navigation hints, resume banner, notifications, and
                        achievement popups.
  dim_screen(alpha)   — apply / remove a semi-transparent black overlay,
                        used during modal transitions.

Both methods are pure rendering — they read GameScreen state but do not
modify it (except the dim_overlay cache and minor animation counters
handled by sub-mixins).
"""

import pygame

import ui_colors
from config import FONT_PATH
from ui_components import Button


class GameScreenDrawMixin:
    """
    Mixin providing the main draw() and dim_screen() methods for GameScreen.

    Expected instance attributes:
        self.width / self.height
        self.font
        self.scaler
        self.games / self.game_names / self.current_game
        self.modal_instance
        self.menu_index
        self.emulator / self.emulator_active
        self.sinew_logo / self.sinew_bg_color
        self._loading_screen
        self._achievement_notification

    Also calls other mixin methods:
        self._draw_emulator()         (EmulatorSessionMixin)
        self._draw_resume_banner()    (NotificationsMixin)
        self._draw_notification()     (NotificationsMixin)
        self.is_on_sinew()
        self.get_menu_items()
    """

    def draw(self, surf):
        """Full-frame render of the Sinew game screen."""
        # Emulator is active — hand off entirely
        if self.emulator_active and self.emulator:
            self._draw_emulator(surf)
            return

        # No games detected yet
        if not self.game_names or self.current_game >= len(self.game_names):
            surf.fill(ui_colors.COLOR_BG)
            return

        # --- Background ---
        gname = self.game_names[self.current_game]
        game_data = self.games[gname]

        if self.is_on_sinew():
            if self.sinew_logo:
                surf.blit(self.sinew_logo, (0, 0))
            else:
                surf.fill(self.sinew_bg_color)
        elif game_data["frames"]:
            surf.blit(game_data["frames"][game_data["frame_index"]], (0, 0))
        else:
            surf.fill(ui_colors.COLOR_BG)

        # --- Modal or main menu ---
        if self.modal_instance:
            self._draw_modal(surf)
        else:
            self._draw_menu(surf)

        # --- Overlays (always on top) ---
        self._draw_notification(surf)
        if self._achievement_notification:
            self._achievement_notification.draw(surf)

    # ------------------------------------------------------------------
    # Private draw helpers
    # ------------------------------------------------------------------

    def _draw_modal(self, surf):
        """Composite the active modal onto surf, then draw the resume banner."""
        if hasattr(self.modal_instance, "width") and hasattr(self.modal_instance, "height"):
            modal_w = self.modal_instance.width
            modal_h = self.modal_instance.height
        else:
            modal_w = self.width - 30
            modal_h = self.height - 30

        modal_surf = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
        if hasattr(self.modal_instance, "draw"):
            self.modal_instance.draw(modal_surf)

        pygame.draw.rect(modal_surf, ui_colors.COLOR_BORDER, (0, 0, modal_w, modal_h), 2)

        modal_x = (self.width - modal_w) // 2
        modal_y = (self.height - modal_h) // 2
        surf.blit(modal_surf, (modal_x, modal_y))

        if self.emulator and self.emulator.loaded and not self.emulator_active:
            self._draw_resume_banner(surf)

    def _draw_menu(self, surf):
        """Draw the single-button menu, nav hints, and resume banner."""
        menu_items = self.get_menu_items()
        if self.menu_index >= len(menu_items):
            self.menu_index = 0

        current_menu_item = menu_items[self.menu_index]
        is_disabled = current_menu_item == "Save File Only"

        menu_button = Button(
            current_menu_item,
            rel_rect=(0.25, 0.65, 0.5, 0.12),
            callback=lambda: None,
        )

        if is_disabled:
            bx = int(0.25 * self.width)
            by = int(0.65 * self.height)
            bw = int(0.5 * self.width)
            bh = int(0.12 * self.height)
            btn_rect = pygame.Rect(bx, by, bw, bh)

            pygame.draw.rect(surf, (50, 50, 55), btn_rect, border_radius=4)
            pygame.draw.rect(surf, (80, 80, 85), btn_rect, 2, border_radius=4)

            try:
                btn_font = pygame.font.Font(FONT_PATH, 14)
            except Exception:
                btn_font = self.font
            txt_surf = btn_font.render(current_menu_item, True, (100, 100, 105))
            surf.blit(txt_surf, txt_surf.get_rect(center=btn_rect.center))

            try:
                hint2_font = pygame.font.Font(FONT_PATH, 7)
            except Exception:
                hint2_font = pygame.font.SysFont(None, 12)
            hint2_surf = hint2_font.render(
                "No ROM — place a .gba file in roms/", True, (90, 90, 90)
            )
            surf.blit(
                hint2_surf,
                hint2_surf.get_rect(centerx=self.width // 2, top=btn_rect.bottom + 3),
            )
        else:
            menu_button.draw(surf, self.font)

        # Navigation hints
        try:
            hint_font = pygame.font.Font(FONT_PATH, 8)
        except Exception:
            hint_font = pygame.font.SysFont(None, 14)
        hint_surf = hint_font.render(
            "< > Change Game    ^ v Scroll Menu", True, (150, 150, 150)
        )
        surf.blit(
            hint_surf,
            hint_surf.get_rect(centerx=self.width // 2, bottom=self.height - 5),
        )

        if self.emulator and self.emulator.loaded and not self.emulator_active:
            self._draw_resume_banner(surf)

    # ------------------------------------------------------------------

    def dim_screen(self, alpha=128):
        """
        Draw a semi-transparent black overlay over the current frame.
        Pass alpha=0 (or negative) to remove the overlay.
        """
        if not hasattr(self, "_dim_overlay"):
            self._dim_overlay = None

        if alpha > 0:
            self._dim_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self._dim_overlay.fill((0, 0, 0, alpha))
            target = self.scaler.get_surface() if self.scaler else self._loading_screen
            if target:
                target.blit(self._dim_overlay, (0, 0))
                if self.scaler:
                    self.scaler.blit_scaled()
                else:
                    pygame.display.flip()
        else:
            self._dim_overlay = None
