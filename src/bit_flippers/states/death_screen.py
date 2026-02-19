"""Death screen shown after the player is defeated in combat."""
import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from bit_flippers.save import save_game


class DeathScreenState:
    def __init__(self, game, overworld, lost_scrap):
        self.game = game
        self.overworld = overworld
        self.lost_scrap = lost_scrap

        self.font_title = get_font(48)
        self.font_info = get_font(28)
        self.font_prompt = get_font(24)

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((60, 10, 10, 220))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_SPACE, pygame.K_RETURN):
            save_game(self.overworld)
            self.game.pop_state()

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title = self.font_title.render("YOU WERE DEFEATED", True, (220, 50, 50))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 3 - 30))

        # Penalty info
        penalty_y = SCREEN_HEIGHT // 2 - 10
        hp_text = self.font_info.render(
            f"Respawning at {self.overworld.stats.current_hp}/{self.overworld.stats.max_hp} HP",
            True, (200, 180, 180),
        )
        screen.blit(hp_text, (SCREEN_WIDTH // 2 - hp_text.get_width() // 2, penalty_y))

        if self.lost_scrap > 0:
            scrap_text = self.font_info.render(
                f"Lost {self.lost_scrap} Scrap", True, (200, 160, 100),
            )
            screen.blit(scrap_text, (SCREEN_WIDTH // 2 - scrap_text.get_width() // 2, penalty_y + 34))

        # Prompt
        prompt = self.font_prompt.render("[SPACE to respawn]", True, (160, 160, 160))
        screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, SCREEN_HEIGHT * 2 // 3 + 20))
