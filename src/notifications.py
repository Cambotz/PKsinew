#!/usr/bin/env python3

"""
notifications.py - In-game notification and resume-banner overlay mixin

Provides two overlay widgets drawn on top of the Sinew game screen:

  ResumeBanner  (_draw_resume_banner)
      A pulsing amber banner along the top of the screen shown whenever
      mGBA is paused and the user is in the Sinew menu.  Displays the
      running game name and the current pause-combo hint with a scrolling
      marquee when the text is too wide to fit.

  Slide-down Notification  (_show_notification / _update_notification /
                             _draw_notification)
      A small box that slides down from the top, holds for a configurable
      duration, then slides back up.  Used for one-off status messages
      (e.g. "Save exported").

Both widgets operate entirely on GameScreen instance state initialised in
__init__ and have no hard dependencies beyond pygame and ui_colors.
"""

import math

import pygame

import ui_colors
from config import FONT_PATH
from ui_scale import ui, scaled_font


class NotificationsMixin:
    """
    Mixin providing resume-banner and slide-down notification overlays.

    Expected instance attributes (set in GameScreen.__init__):
        self.width / self.height
        self.font
        self._resume_banner_pulse_time      float  (0.0)
        self._resume_banner_scroll_offset   float  (0.0)
        self._resume_banner_scroll_speed    float  (pixels per frame)
        self._notification_text             str | None
        self._notification_subtext          str | None
        self._notification_timer            float
        self._notification_duration         float  (ms, e.g. 3000)
        self._notification_y                float
        self._notification_target_y         float

    Also calls (provided by PauseComboMixin):
        self._get_pause_combo_name()
        self._get_running_game_name()  (GameScreen method)
    """

    # ------------------------------------------------------------------
    # Resume banner (shown while mGBA is paused / user is in Sinew menu)
    # ------------------------------------------------------------------

    def _draw_resume_banner(self, surf):
        """
        Draw a pulsing amber banner at the top of the screen while mGBA is
        paused.  Shows '[game] running • Hold [combo] to resume' with a
        scrolling marquee when the text is too wide.
        """
        game_name = self._get_running_game_name() or "Game"
        combo_name = self._get_pause_combo_name()
        full_text = f'"{game_name}" running  •  Hold {combo_name} to resume'

        banner_height = ui.s(21)
        banner_width = int(self.width * 0.85)
        banner_x = (self.width - banner_width) // 2
        banner_y = ui.s(4)
        padding = ui.s(12)
        border_radius = ui.s(6)

        self._resume_banner_pulse_time += 0.08
        pulse = (math.sin(self._resume_banner_pulse_time) + 1) / 2  # 0 → 1

        # Pulsing background (dark amber → lighter amber)
        bg_r = int(40 + 25 * pulse)
        bg_g = int(35 + 20 * pulse)
        bg_b = int(15 + 10 * pulse)

        banner_rect = pygame.Rect(banner_x, banner_y, banner_width, banner_height)
        pygame.draw.rect(surf, (bg_r, bg_g, bg_b), banner_rect, border_radius=border_radius)

        # Pulsing border (gold tones)
        border_r = int(180 + 75 * pulse)
        border_g = int(140 + 60 * pulse)
        border_b = int(30 + 30 * pulse)
        pygame.draw.rect(
            surf, (border_r, border_g, border_b), banner_rect, 2,
            border_radius=border_radius,
        )

        banner_font = scaled_font(10)
        text_r = int(200 + 55 * pulse)
        text_g = int(180 + 55 * pulse)
        text_b = int(100 + 50 * pulse)
        text_surf = banner_font.render(full_text, True, (text_r, text_g, text_b))
        text_width = text_surf.get_width()
        available_width = banner_width - (padding * 2)

        if text_width <= available_width:
            text_x = banner_x + (banner_width - text_width) // 2
            text_y = banner_y + (banner_height - text_surf.get_height()) // 2
            surf.blit(text_surf, (text_x, text_y))
        else:
            clip_rect = pygame.Rect(banner_x + padding, banner_y, available_width, banner_height)
            scroll_width = text_width + ui.s(60)
            self._resume_banner_scroll_offset += self._resume_banner_scroll_speed
            if self._resume_banner_scroll_offset >= scroll_width:
                self._resume_banner_scroll_offset = 0

            text_x = banner_x + padding - self._resume_banner_scroll_offset
            text_y = banner_y + (banner_height - text_surf.get_height()) // 2

            old_clip = surf.get_clip()
            surf.set_clip(clip_rect)
            surf.blit(text_surf, (text_x, text_y))
            if text_x + text_width < banner_x + padding + available_width:
                surf.blit(text_surf, (text_x + scroll_width, text_y))
            surf.set_clip(old_clip)

    # ------------------------------------------------------------------
    # Slide-down notification widget
    # ------------------------------------------------------------------

    def _show_notification(self, text, subtext=None):
        """Trigger a slide-down notification box."""
        self._notification_text = text
        self._notification_subtext = subtext
        self._notification_timer = self._notification_duration
        self._notification_y = ui.s(-80)  # Start above the screen

    def _update_notification(self, dt):
        """Advance the notification slide animation each frame."""
        if self._notification_timer <= 0:
            # Slide back up and hide
            self._notification_y -= dt * 0.3
            if self._notification_y < ui.s(-80):
                self._notification_text = None
                self._notification_subtext = None
        else:
            # Slide down into view
            self._notification_timer -= dt
            if self._notification_y < self._notification_target_y:
                self._notification_y += dt * 0.5
                self._notification_y = min(self._notification_y, self._notification_target_y)

    def _draw_notification(self, surf):
        """Draw the slide-down notification box if one is active."""
        if self._notification_text is None:
            return

        box_width = min(self.width - ui.s(40), ui.s(400))
        box_height = ui.s(60) if self._notification_subtext else ui.s(40)
        box_x = (self.width - box_width) // 2
        box_y = int(self._notification_y)

        if box_y < -box_height:
            return

        # Shadow
        pygame.draw.rect(
            surf, (0, 10, 20),
            pygame.Rect(box_x + ui.s(3), box_y + ui.s(3), box_width, box_height),
            border_radius=ui.s(8),
        )

        # Box
        box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(surf, ui_colors.COLOR_HEADER, box_rect, border_radius=ui.s(8))
        pygame.draw.rect(surf, ui_colors.COLOR_BORDER, box_rect, 2, border_radius=ui.s(8))

        font = self.font if self.font else scaled_font(24)

        text_surf = font.render(self._notification_text, True, ui_colors.COLOR_TEXT)
        surf.blit(text_surf, text_surf.get_rect(centerx=box_x + box_width // 2, top=box_y + ui.s(8)))

        if self._notification_subtext:
            sub_color = tuple(max(0, c - 40) for c in ui_colors.COLOR_TEXT)
            sub_surf = font.render(self._notification_subtext, True, sub_color)
            surf.blit(sub_surf, sub_surf.get_rect(centerx=box_x + box_width // 2, top=box_y + ui.s(32)))