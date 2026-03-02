#!/usr/bin/env python3

"""
game_dialogs.py — Simple dialog/popup widgets used by the Sinew game screen.
"""

import pygame

import ui_colors
from config import FONT_PATH
from ui_components import Button


class PlaceholderModal:
    """Placeholder for unimplemented modals"""

    def __init__(self, title, width, height, font, close_callback):
        self.width = width
        self.height = height
        self.title = title
        self.font = font
        self.close_callback = close_callback
        self.back_button = Button(
            "Back", rel_rect=(0.75, 0.02, 0.22, 0.08), callback=close_callback
        )

    def update(self, events):
        """Process pygame events and delegate to the back button."""
        for event in events:
            self.back_button.handle_event(event)

    def draw(self, surf):
        """Render the placeholder modal background, title, and back button to surf."""
        surf.fill(ui_colors.COLOR_BG)
        txt = self.font.render(self.title, True, ui_colors.COLOR_TEXT)
        surf.blit(txt, (16, 16))
        self.back_button.draw(surf, self.font)

    def handle_mouse(self, event):
        """Handle a mouse button event by forwarding it to the back button."""
        return self.back_button.handle_event(event)

    def handle_controller(self, ctrl):
        """Invoke the close callback and consume the B button press."""
        if ctrl.is_button_just_pressed("B"):
            ctrl.consume_button("B")
            self.close_callback()
            return True
        return False


class DBWarningPopup:
    """Popup warning about missing/incomplete Pokemon database"""

    def __init__(
        self,
        width,
        height,
        title,
        message,
        build_callback=None,
        close_callback=None,
        screen_size=None,
    ):
        self.width = width
        self.height = height
        self.title = title
        self.message = message
        self.build_callback = build_callback
        self.close_callback = close_callback
        self.visible = True
        self.screen_size = screen_size  # (screen_width, screen_height) for mouse offset

        # Button state
        self.selected_button = 0  # 0 = Build Now, 1 = Later
        self.buttons = ["Build Now", "Later"]

        # Debounce
        self._last_click_time = 0
        self._click_debounce_ms = 300

        # Fonts
        try:
            self.font_title = pygame.font.Font(FONT_PATH, 14)
            self.font_text = pygame.font.Font(FONT_PATH, 10)
            self.font_button = pygame.font.Font(FONT_PATH, 11)
        except Exception:
            self.font_title = pygame.font.SysFont(None, 20)
            self.font_text = pygame.font.SysFont(None, 16)
            self.font_button = pygame.font.SysFont(None, 18)

    def _get_screen_offset(self):
        """Get the offset of this popup on screen (for mouse coordinate translation)"""
        if self.screen_size:
            screen_w, screen_h = self.screen_size
            offset_x = (screen_w - self.width) // 2
            offset_y = (screen_h - self.height) // 2
            return offset_x, offset_y
        return 0, 0

    def update(self, events):
        """Process keyboard and mouse events for the DB warning popup; returns visibility flag."""
        current_time = pygame.time.get_ticks()
        offset_x, offset_y = self._get_screen_offset()

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._close()
                elif event.key == pygame.K_RETURN:
                    if current_time - self._last_click_time > self._click_debounce_ms:
                        self._last_click_time = current_time
                        self._activate_button()
                elif event.key == pygame.K_LEFT:
                    self.selected_button = max(0, self.selected_button - 1)
                elif event.key == pygame.K_RIGHT:
                    self.selected_button = min(
                        len(self.buttons) - 1, self.selected_button + 1
                    )

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if current_time - self._last_click_time < self._click_debounce_ms:
                        continue

                    # Translate mouse position to popup-local coordinates
                    local_pos = (event.pos[0] - offset_x, event.pos[1] - offset_y)

                    button_rects = self._get_button_rects()
                    for i, rect in enumerate(button_rects):
                        if rect.collidepoint(local_pos):
                            self._last_click_time = current_time
                            self.selected_button = i
                            self._activate_button()
                            break

        return self.visible

    def handle_controller(self, ctrl):
        """Handle controller D-pad and button input for the DB warning popup."""
        if not ctrl:
            return

        current_time = pygame.time.get_ticks()

        if ctrl.is_dpad_just_pressed("left"):
            self.selected_button = max(0, self.selected_button - 1)
        elif ctrl.is_dpad_just_pressed("right"):
            self.selected_button = min(len(self.buttons) - 1, self.selected_button + 1)

        if ctrl.is_button_just_pressed("A"):
            if current_time - self._last_click_time > self._click_debounce_ms:
                self._last_click_time = current_time
                self._activate_button()

        if ctrl.is_button_just_pressed("B"):
            self._close()

    def _activate_button(self):
        if self.selected_button == 0:
            # Build Now
            if self.build_callback:
                self.build_callback()
        else:
            # Later
            self._close()

    def _close(self):
        self.visible = False
        if self.close_callback:
            self.close_callback()

    def _get_button_rects(self):
        # Match the positioning in draw()
        # Approximate: title at top, message in middle, buttons below
        # For a 180px height popup, buttons should be near the bottom
        button_y = self.height - 50
        button_width = 100
        button_height = 30
        button_spacing = 20
        total_width = (
            len(self.buttons) * button_width + (len(self.buttons) - 1) * button_spacing
        )
        start_x = (self.width - total_width) // 2

        rects = []
        for i in range(len(self.buttons)):
            btn_x = start_x + i * (button_width + button_spacing)
            rects.append(pygame.Rect(btn_x, button_y, button_width, button_height))
        return rects

    def draw(self, surf):
        """Render the DB warning popup title, message, and action buttons to surf."""
        # Semi-transparent background
        surf.fill(ui_colors.COLOR_BG)

        # Title - centered near top
        title_y = 20
        title_surf = self.font_title.render(self.title, True, ui_colors.COLOR_ERROR)
        title_rect = title_surf.get_rect(centerx=self.width // 2, top=title_y)
        surf.blit(title_surf, title_rect)

        # Message - word wrap, centered
        message_y = title_rect.bottom + 15
        words = self.message.split()
        lines = []
        current_line = []
        max_width = self.width - 40

        for word in words:
            current_line.append(word)
            test_text = " ".join(current_line)
            test_surf = self.font_text.render(test_text, True, ui_colors.COLOR_TEXT)
            if test_surf.get_width() > max_width:
                current_line.pop()
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        for line in lines:
            line_surf = self.font_text.render(line, True, ui_colors.COLOR_TEXT)
            line_rect = line_surf.get_rect(centerx=self.width // 2, top=message_y)
            surf.blit(line_surf, line_rect)
            message_y += 16

        # Buttons - use same positioning as _get_button_rects
        button_rects = self._get_button_rects()
        for i, (btn_text, rect) in enumerate(
            zip(self.buttons, button_rects, strict=False)
        ):
            if i == self.selected_button:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON_HOVER, rect)
                pygame.draw.rect(surf, ui_colors.COLOR_HIGHLIGHT, rect, 3)
            else:
                pygame.draw.rect(surf, ui_colors.COLOR_BUTTON, rect)
                pygame.draw.rect(surf, ui_colors.COLOR_BORDER, rect, 2)

            text_surf = self.font_button.render(btn_text, True, ui_colors.COLOR_TEXT)
            text_rect = text_surf.get_rect(center=rect.center)
            surf.blit(text_surf, text_rect)
