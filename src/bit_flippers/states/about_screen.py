"""About / credits screen loaded from strings.json."""
import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from bit_flippers.strings import load_strings


class AboutScreenState:
    def __init__(self, game):
        self.game = game
        self.font = get_font(28)
        self.font_hint = get_font(22)

        strings = load_strings()
        self.lines: list[str] = strings.get("about", [])

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((10, 8, 20, 240))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
            self.game.pop_state()

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Centered text block
        total_height = len(self.lines) * 30
        start_y = SCREEN_HEIGHT // 2 - total_height // 2

        for i, line in enumerate(self.lines):
            if line:
                surf = self.font.render(line, True, (220, 220, 220))
                screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, start_y + i * 30))

        # Hint
        hint = self.font_hint.render("[ESC / SPACE to return]", True, (100, 100, 100))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 40))
