"""Options menu — SFX and music volume controls."""
import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from bit_flippers.save import load_config, save_config


class OptionsMenuState:
    def __init__(self, game):
        self.game = game
        self.cursor = 0  # 0 = SFX, 1 = Music

        # Load current volumes (0-100 integer, in steps of 10)
        self.sfx_volume = round(game.audio._sfx_volume * 100 / 10) * 10
        self.music_volume = round(game.audio._music_volume * 100 / 10) * 10

        self.font_title = get_font(40)
        self.font_option = get_font(28)
        self.font_hint = get_font(22)

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((10, 10, 20, 200))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self._save_and_close()
        elif event.key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % 2
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % 2
        elif event.key == pygame.K_LEFT:
            self._adjust(-10)
        elif event.key == pygame.K_RIGHT:
            self._adjust(10)

    def _adjust(self, delta):
        if self.cursor == 0:
            self.sfx_volume = max(0, min(100, self.sfx_volume + delta))
            self.game.audio.set_sfx_volume(self.sfx_volume / 100.0)
        else:
            self.music_volume = max(0, min(100, self.music_volume + delta))
            self.game.audio.set_music_volume(self.music_volume / 100.0)

    def _save_and_close(self):
        config = load_config()
        config["sfx_volume"] = self.sfx_volume
        config["music_volume"] = self.music_volume
        save_config(config)
        self.game.pop_state()

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title = self.font_title.render("OPTIONS", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 4))

        options = [
            ("SFX Volume", self.sfx_volume),
            ("Music Volume", self.music_volume),
        ]

        menu_y = SCREEN_HEIGHT // 4 + 80
        bar_width = 200
        bar_height = 16

        for i, (label, value) in enumerate(options):
            is_sel = i == self.cursor
            color = (255, 220, 100) if is_sel else (200, 200, 200)
            prefix = "> " if is_sel else "  "

            # Label
            text = self.font_option.render(f"{prefix}{label}", True, color)
            screen.blit(text, (SCREEN_WIDTH // 2 - 180, menu_y + i * 60))

            # Slider bar
            bar_x = SCREEN_WIDTH // 2 + 40
            bar_y = menu_y + i * 60 + 6
            pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
            fill_w = int(bar_width * value / 100)
            fill_color = (100, 180, 255) if is_sel else (80, 140, 200)
            pygame.draw.rect(screen, fill_color, (bar_x, bar_y, fill_w, bar_height))
            pygame.draw.rect(screen, (180, 180, 180), (bar_x, bar_y, bar_width, bar_height), 1)

            # Value text
            val_text = self.font_option.render(f"{value}%", True, color)
            screen.blit(val_text, (bar_x + bar_width + 10, menu_y + i * 60))

        # Hints
        hint = self.font_hint.render(
            "[LEFT/RIGHT] Adjust   [UP/DOWN] Navigate   [ESC] Back",
            True, (100, 100, 100),
        )
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 40))
