"""Full-screen save/load menu with 5 slots."""
import time

import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from bit_flippers.save import get_slot_summary, save_game, load_game, has_save

_NUM_SLOTS = 5


class SaveMenuState:
    """Full-screen menu for saving to or loading from 5 save slots.

    mode="save": selecting a slot saves overworld state there.
    mode="load": selecting a slot loads from it (callback receives save_data).
    """

    def __init__(self, game, mode, overworld=None, on_load=None):
        self.game = game
        self.mode = mode  # "save" or "load"
        self.overworld = overworld
        self.on_load = on_load  # callback(save_data) for load mode
        self.cursor = 0

        # Confirmation state
        self.confirming = False
        self.confirm_cursor = 0  # 0 = Yes, 1 = No

        # Feedback message
        self.message = ""
        self.message_timer = 0.0

        # Fonts
        self.font_title = get_font(40)
        self.font_slot = get_font(26)
        self.font_detail = get_font(22)
        self.font_hint = get_font(22)

        # Overlay
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((10, 10, 20, 240))

        # Load slot summaries
        self.summaries = [get_slot_summary(i) for i in range(_NUM_SLOTS)]

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.confirming:
            self._handle_confirm(event)
            return

        if event.key == pygame.K_ESCAPE:
            self.game.pop_state()
        elif event.key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % _NUM_SLOTS
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % _NUM_SLOTS
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._select_slot()

    def _select_slot(self):
        slot = self.cursor
        summary = self.summaries[slot]

        if self.mode == "save":
            if summary is not None:
                # Confirm overwrite
                self.confirming = True
                self.confirm_cursor = 0
            else:
                self._do_save(slot)
        else:  # load
            if summary is None:
                self.message = "Empty slot!"
                self.message_timer = 1.0
                return
            self.confirming = True
            self.confirm_cursor = 0

    def _handle_confirm(self, event):
        if event.key in (pygame.K_LEFT, pygame.K_UP):
            self.confirm_cursor = 0
        elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
            self.confirm_cursor = 1
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.confirm_cursor == 0:  # Yes
                if self.mode == "save":
                    self._do_save(self.cursor)
                else:
                    self._do_load(self.cursor)
            self.confirming = False
        elif event.key == pygame.K_ESCAPE:
            self.confirming = False

    def _do_save(self, slot):
        if self.overworld is None:
            return
        self.overworld.active_save_slot = slot
        save_game(self.overworld, slot=slot)
        self.summaries[slot] = get_slot_summary(slot)
        self.message = f"Saved to Slot {slot + 1}!"
        self.message_timer = 1.5

    def _do_load(self, slot):
        save_data = load_game(slot)
        if save_data is None:
            self.message = "Failed to load!"
            self.message_timer = 1.5
            return
        self.game.pop_state()  # pop save menu
        if self.on_load:
            self.on_load(save_data, slot)

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title_text = "SAVE GAME" if self.mode == "save" else "LOAD GAME"
        title = self.font_title.render(title_text, True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        # Slot boxes
        slot_width = SCREEN_WIDTH - 120
        slot_height = 56
        start_x = 60
        start_y = 90
        gap = 8

        for i in range(_NUM_SLOTS):
            y = start_y + i * (slot_height + gap)
            is_selected = i == self.cursor
            summary = self.summaries[i]

            # Background
            bg_color = (40, 40, 60) if is_selected else (25, 25, 40)
            pygame.draw.rect(screen, bg_color, (start_x, y, slot_width, slot_height))

            # Border
            border_color = (255, 220, 100) if is_selected else (80, 80, 100)
            pygame.draw.rect(screen, border_color, (start_x, y, slot_width, slot_height), 2)

            # Slot label
            label = f"Slot {i + 1}"
            label_surf = self.font_slot.render(label, True, (255, 255, 255))
            screen.blit(label_surf, (start_x + 12, y + 6))

            if summary is not None:
                # Level
                level_surf = self.font_detail.render(f"Lv {summary['level']}", True, (200, 200, 200))
                screen.blit(level_surf, (start_x + 12, y + 32))

                # Map
                map_surf = self.font_detail.render(summary["map_id"], True, (160, 160, 160))
                screen.blit(map_surf, (start_x + 100, y + 32))

                # Scrap
                scrap_surf = self.font_detail.render(f"{summary['money']} Scrap", True, (220, 200, 100))
                screen.blit(scrap_surf, (start_x + 260, y + 32))

                # Timestamp
                ts = summary.get("timestamp", 0)
                if ts > 0:
                    time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
                    time_surf = self.font_detail.render(time_str, True, (140, 140, 140))
                    screen.blit(time_surf, (start_x + slot_width - time_surf.get_width() - 12, y + 8))
            else:
                empty_surf = self.font_detail.render("Empty", True, (100, 100, 100))
                screen.blit(empty_surf, (start_x + 12, y + 32))

        # Feedback message
        if self.message:
            msg = self.font_slot.render(self.message, True, (100, 255, 100))
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT - 60))

        # Hint
        hint = self.font_hint.render(
            "[UP/DOWN] Navigate   [ENTER] Select   [ESC] Back",
            True, (120, 120, 120),
        )
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 30))

        # Confirmation overlay
        if self.confirming:
            self._draw_confirm(screen)

    def _draw_confirm(self, screen):
        confirm_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        confirm_overlay.fill((10, 10, 20, 200))
        screen.blit(confirm_overlay, (0, 0))

        if self.mode == "save":
            prompt = f"Overwrite Slot {self.cursor + 1}?"
        else:
            prompt = f"Load Slot {self.cursor + 1}?"

        box_w = 300
        box_h = 100
        box_x = SCREEN_WIDTH // 2 - box_w // 2
        box_y = SCREEN_HEIGHT // 2 - box_h // 2
        pygame.draw.rect(screen, (30, 30, 50), (box_x, box_y, box_w, box_h))
        pygame.draw.rect(screen, (180, 180, 180), (box_x, box_y, box_w, box_h), 2)

        prompt_surf = self.font_slot.render(prompt, True, (255, 255, 255))
        screen.blit(prompt_surf, (box_x + box_w // 2 - prompt_surf.get_width() // 2, box_y + 20))

        yes_color = (255, 220, 100) if self.confirm_cursor == 0 else (180, 180, 180)
        no_color = (255, 220, 100) if self.confirm_cursor == 1 else (180, 180, 180)
        yes_surf = self.font_slot.render("Yes", True, yes_color)
        no_surf = self.font_slot.render("No", True, no_color)
        btn_y = box_y + 60
        screen.blit(yes_surf, (box_x + box_w // 3 - yes_surf.get_width() // 2, btn_y))
        screen.blit(no_surf, (box_x + 2 * box_w // 3 - no_surf.get_width() // 2, btn_y))
