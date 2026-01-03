import pygame
import ui_colors
from ui_components import Button, scale_surface_preserve_aspect

# Try to import PokemonSummary
try:
    from pokemon_summary import PokemonSummary
    SUMMARY_AVAILABLE = True
except ImportError:
    PokemonSummary = None
    SUMMARY_AVAILABLE = False

SLOT_COUNT = 6

class PartyScreen:
    def __init__(self, width=640, height=480, party_data=None, close_callback=None,
                 manager=None, game_type='RSE'):
        self.width = width
        self.height = height
        self.surface = pygame.Surface((self.width, self.height))
        self.manager = manager
        self.game_type = game_type
        self.sub_modal = None  # For PokemonSummary

        # ------------------------------------------------------------
        # FONTS
        # ------------------------------------------------------------
        self.font = pygame.font.Font("fonts/Pokemon_GB.ttf", 16)
        self.small_font = pygame.font.Font("fonts/Pokemon_GB.ttf", 12)

        # ============================================================
        # LAYOUT VARIABLES
        # ============================================================
        # LEFT PANEL
        self.left_margin = 10
        self.left_width = width // 3

        # Sprite box
        self.sprite_box_height = 120
        self.sprite_box_gap = 5

        # Info box
        self.info_box_height = 90
        self.info_box_gap = 5
        self.info_text_margin = 5
        self.info_line_spacing = -2

        # CLOSE BUTTON CONFIG (adjustable)
        self.close_button_text = "Close"
        self.close_button_height = 30
        self.close_button_gap = 5             # Distance below info box
        self.close_button_width = self.left_width - 3 * self.left_margin
        self.close_button_x = self.left_margin
        self.close_button_y = self.sprite_box_height + self.sprite_box_gap + self.info_box_height + self.close_button_gap

        # RIGHT PANEL (party cards)
        self.right_margin = 10
        self.card_spacing = 6
        self.card_width = width - self.left_width - 2 * self.right_margin
        self.card_height = (height - (SLOT_COUNT - 1) * self.card_spacing - 2 * self.right_margin) // SLOT_COUNT

        # Card offsets
        self.card_sprite_size = 32
        self.card_sprite_offset_x = 5
        self.card_name_offset_x = 45
        self.card_name_offset_y = 0
        self.card_level_offset_y = -10
        self.hp_bar_width = 100
        self.hp_bar_height_ratio = 0.2
        self.hp_bar_offset_x = 10
        self.hp_bar_offset_y = -2
        self.hp_text_offset_y = 2

        # ============================================================
        # LEFT PANEL RECTS
        # ============================================================
        self.sprite_rect = pygame.Rect(
            self.left_margin,
            self.left_margin,
            self.left_width - 2 * self.left_margin,
            self.sprite_box_height
        )

        self.info_rect = pygame.Rect(
            self.left_margin,
            self.sprite_rect.bottom + self.sprite_box_gap,
            self.left_width - 2 * self.left_margin,
            self.info_box_height
        )

        # Close button
        rel_rect = (
            self.close_button_x / self.width,
            self.close_button_y / self.height,
            self.close_button_width / self.width,
            self.close_button_height / self.height
        )
        self.close_button = Button(self.close_button_text, rel_rect, close_callback or (lambda: None))

        # ============================================================
        # PARTY CARDS RECTS
        # ============================================================
        self.cards = []
        start_y = self.right_margin
        for i in range(SLOT_COUNT):
            rect = pygame.Rect(
                self.left_width + self.right_margin,
                start_y + i * (self.card_height + self.card_spacing),
                self.card_width,
                self.card_height
            )
            self.cards.append({"rect": rect, "pokemon": None})

        # ============================================================
        # DATA
        # ============================================================
        self.party_data = [None] * SLOT_COUNT
        if party_data:
            self.update_party(party_data)

        self.selected_index = 0
        self.close_selected = False  # Tracks if close button is selected

    # ================================================================
    # DRAW
    # ================================================================
    def draw(self, surf):
        self.surface.fill(ui_colors.COLOR_BG)
        selected = self.party_data[self.selected_index]

        # SPRITE BOX
        pygame.draw.rect(self.surface, ui_colors.COLOR_BUTTON, self.sprite_rect)
        pygame.draw.rect(self.surface, ui_colors.COLOR_BORDER, self.sprite_rect, 2)
        if selected and selected.get("sprite"):
            sprite = scale_surface_preserve_aspect(selected["sprite"], self.sprite_rect.width -20, self.sprite_rect.height  -20)
            self.surface.blit(sprite, sprite.get_rect(center=self.sprite_rect.center))
        else:
            placeholder = self.font.render("No Sprite", True, ui_colors.COLOR_TEXT)
            self.surface.blit(placeholder, placeholder.get_rect(center=self.sprite_rect.center))

        # INFO BOX
        pygame.draw.rect(self.surface, ui_colors.COLOR_BUTTON, self.info_rect)
        pygame.draw.rect(self.surface, ui_colors.COLOR_BORDER, self.info_rect, 2)
        y = self.info_rect.y + self.info_text_margin
        if selected:
            lines = [
                f"{selected.get('name', 'Unknown')}",
                f"Lv{selected.get('level', '?')}",
                f"HP: {selected.get('hp', 0)}/{selected.get('max_hp', 1)}"
            ]
        else:
            lines = ["No Pokemon selected"]
        for line in lines:
            txt = self.font.render(line, True, ui_colors.COLOR_TEXT)
            self.surface.blit(txt, (self.info_rect.x + self.info_text_margin, y))
            y += self.font.get_linesize() + self.info_line_spacing

        # PARTY CARDS
        for i, card in enumerate(self.cards):
            rect = card["rect"]
            p = card["pokemon"]
            color = ui_colors.COLOR_BUTTON_HOVER if i == self.selected_index and not self.close_selected else ui_colors.COLOR_BUTTON
            pygame.draw.rect(self.surface, color, rect)
            pygame.draw.rect(self.surface, ui_colors.COLOR_BORDER, rect, 2)

            if p:
                # Sprite
                if p.get("sprite"):
                    sprite = scale_surface_preserve_aspect(p["sprite"], self.card_sprite_size, self.card_sprite_size)
                    sprite_y = rect.y + (rect.height - self.card_sprite_size) // 2
                    self.surface.blit(sprite, (rect.x + self.card_sprite_offset_x, sprite_y))

                # Name & Level
                name_surf = self.font.render(p.get("name", "???"), True, ui_colors.COLOR_TEXT)
                self.surface.blit(name_surf, (rect.x + self.card_name_offset_x, rect.y + self.card_name_offset_y))
                level_surf = self.small_font.render(f"Lv{p.get('level', '?')}", True, ui_colors.COLOR_TEXT)
                level_y = rect.y + self.card_name_offset_y + name_surf.get_height() + self.card_level_offset_y
                self.surface.blit(level_surf, (rect.x + self.card_name_offset_x, level_y))

                # HP bar
                hp_current = p.get("hp", 0)
                hp_max = p.get("max_hp", 1)
                hp_ratio = max(0, min(1, hp_current / hp_max))
                bar_height = max(6, int(rect.height * self.hp_bar_height_ratio))
                bar_x = rect.right - self.hp_bar_width - self.hp_bar_offset_x
                bar_y = rect.y + (rect.height - bar_height) // 2 + self.hp_bar_offset_y
                pygame.draw.rect(self.surface, (50, 50, 50), (bar_x, bar_y, self.hp_bar_width, bar_height))
                if hp_ratio > 0.5:
                    hp_col = (0, 200, 0)
                elif hp_ratio > 0.25:
                    hp_col = (220, 180, 0)
                else:
                    hp_col = (200, 0, 0)
                pygame.draw.rect(self.surface, hp_col, (bar_x, bar_y, int(self.hp_bar_width * hp_ratio), bar_height))
                hp_surf = self.small_font.render(f"{hp_current}/{hp_max}", True, ui_colors.COLOR_TEXT)
                hp_text_x = rect.right - hp_surf.get_width() - self.hp_bar_offset_x
                hp_text_y = bar_y + bar_height - self.hp_text_offset_y
                self.surface.blit(hp_surf, (hp_text_x, hp_text_y))

        # CLOSE BUTTON
        self.close_button.draw(self.surface, self.font, controller_selected=self.close_selected)

        surf.blit(self.surface, (0, 0))
        
        # Draw sub_modal on top if open
        if self.sub_modal and hasattr(self.sub_modal, 'draw'):
            self.sub_modal.draw(surf)

    # ================================================================
    # CONTROLLER / EVENTS
    # ================================================================
    def handle_controller(self, ctrl):
        consumed = False
        
        # If sub_modal is open, pass input to it
        if self.sub_modal:
            if hasattr(self.sub_modal, 'handle_controller'):
                self.sub_modal.handle_controller(ctrl)
            
            # B closes sub_modal
            if ctrl.is_button_just_pressed('B'):
                ctrl.consume_button('B')
                self.sub_modal = None
            return True
        
        # Navigation
        if ctrl.is_dpad_just_pressed('up'):
            ctrl.consume_dpad('up')
            if self.close_selected:
                self.close_selected = False
            else:
                self.selected_index = max(0, self.selected_index - 1)
            consumed = True
        if ctrl.is_dpad_just_pressed('down'):
            ctrl.consume_dpad('down')
            if self.selected_index == SLOT_COUNT - 1:
                self.close_selected = True
            else:
                self.selected_index = min(SLOT_COUNT - 1, self.selected_index + 1)
            consumed = True
        if ctrl.is_dpad_just_pressed('left'):
            ctrl.consume_dpad('left')
            self.close_selected = True
            consumed = True
        if ctrl.is_dpad_just_pressed('right'):
            ctrl.consume_dpad('right')
            if self.close_selected:
                self.close_selected = False
            consumed = True

        # Action buttons
        if ctrl.is_button_just_pressed('A'):
            ctrl.consume_button('A')
            if self.close_selected:
                self.close_button.activate()
            else:
                # Open summary for selected Pokemon
                self._open_summary()
            consumed = True
        if ctrl.is_button_just_pressed('B'):
            ctrl.consume_button('B')
            self.close_button.activate()
            consumed = True
        return consumed

    def handle_event(self, event):
        self.close_button.handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                if self.close_selected:
                    self.close_selected = False
                else:
                    self.selected_index = max(0, self.selected_index - 1)
            elif event.key == pygame.K_DOWN:
                if self.selected_index == SLOT_COUNT - 1:
                    self.close_selected = True
                else:
                    self.selected_index = min(SLOT_COUNT - 1, self.selected_index + 1)
            elif event.key == pygame.K_LEFT:
                self.close_selected = True
            elif event.key == pygame.K_RIGHT:
                if self.close_selected:
                    self.close_selected = False
            elif event.key == pygame.K_ESCAPE:
                self.close_button.activate()
            elif event.key == pygame.K_RETURN:
                # Open summary on Enter key
                if not self.close_selected:
                    self._open_summary()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, card in enumerate(self.cards):
                if card["rect"].collidepoint(mx, my):
                    self.selected_index = i
                    self.close_selected = False
                    break

    # ================================================================
    # SUMMARY SCREEN
    # ================================================================
    def _open_summary(self):
        """Open Pokemon summary for the selected party member"""
        if not SUMMARY_AVAILABLE or not PokemonSummary:
            return
        
        selected = self.party_data[self.selected_index]
        if not selected:
            return
        
        # Convert party_data format to pokemon dict format for summary
        pokemon = self._convert_to_pokemon_dict(selected)
        if not pokemon:
            return
        
        def close_summary():
            self.sub_modal = None
        
        self.sub_modal = PokemonSummary(
            pokemon=pokemon,
            width=self.width,
            height=self.height,
            font=self.font,
            close_callback=close_summary,
            manager=self.manager,
            game_type=self.game_type,
            prev_pokemon_callback=self._get_prev_pokemon,
            next_pokemon_callback=self._get_next_pokemon
        )
    
    def _convert_to_pokemon_dict(self, party_entry):
        """Convert party screen entry to Pokemon dict for summary"""
        if not party_entry:
            return None
        
        # If it already has 'species', it's likely already in the right format
        if 'species' in party_entry:
            return party_entry
        
        # Otherwise, try to extract from the 'raw' dict if available
        if 'raw' in party_entry:
            return party_entry['raw']
        
        # Build a minimal dict from available data
        return {
            'nickname': party_entry.get('name', '???'),
            'level': party_entry.get('level', 1),
            'current_hp': party_entry.get('hp', 0),
            'max_hp': party_entry.get('max_hp', 1),
            'species': party_entry.get('species', 0),
        }
    
    def _get_prev_pokemon(self):
        """Get previous party Pokemon for summary navigation"""
        # Find previous non-empty slot
        for i in range(1, SLOT_COUNT + 1):
            idx = (self.selected_index - i) % SLOT_COUNT
            if self.party_data[idx]:
                self.selected_index = idx
                return self._convert_to_pokemon_dict(self.party_data[idx])
        return None
    
    def _get_next_pokemon(self):
        """Get next party Pokemon for summary navigation"""
        # Find next non-empty slot
        for i in range(1, SLOT_COUNT + 1):
            idx = (self.selected_index + i) % SLOT_COUNT
            if self.party_data[idx]:
                self.selected_index = idx
                return self._convert_to_pokemon_dict(self.party_data[idx])
        return None

    # ================================================================
    # UPDATE PARTY
    # ================================================================
    def update_party(self, data):
        padded = [None] * SLOT_COUNT
        if data:
            for i in range(min(SLOT_COUNT, len(data))):
                padded[i] = data[i]
        self.party_data = padded
        for i in range(SLOT_COUNT):
            self.cards[i]["pokemon"] = self.party_data[i]