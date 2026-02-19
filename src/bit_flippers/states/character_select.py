"""Character selection screen — choose a player sprite at game start."""
import os

import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT

_ASSET_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, os.pardir, "assets")
)

# 8 curated sprite choices (4 male + 4 female)
SPRITE_CHOICES = [
    "pipoya-characters/Male/Male 01-1",
    "pipoya-characters/Male/Male 02-1",
    "pipoya-characters/Male/Male 03-1",
    "pipoya-characters/Male/Male 04-1",
    "pipoya-characters/Female/Female 01-1",
    "pipoya-characters/Female/Female 02-1",
    "pipoya-characters/Female/Female 03-1",
    "pipoya-characters/Female/Female 04-1",
]


def _load_preview(sprite_key):
    """Load the idle_down frame (middle column, first row) from a Pipoya sheet at 2x."""
    path = os.path.join(_ASSET_DIR, "sprites", f"{sprite_key}.png")
    if not os.path.isfile(path):
        # Fallback: colored rectangle
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        surf.fill((120, 120, 120))
        return surf
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except pygame.error:
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        surf.fill((120, 120, 120))
        return surf
    # Pipoya layout: 3 cols x 4 rows, 32x32 frames. Row 0 = down, col 1 = idle
    frame = pygame.Surface((32, 32), pygame.SRCALPHA)
    frame.blit(sheet, (0, 0), (32, 0, 32, 32))
    return pygame.transform.scale(frame, (64, 64))


class CharacterSelectState:
    def __init__(self, game, on_select):
        self.game = game
        self.on_select = on_select
        self.cursor = 0
        self.previews = [_load_preview(key) for key in SPRITE_CHOICES]

        self.font_title = get_font(40)
        self.font_label = get_font(22)
        self.font_hint = get_font(20)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_LEFT:
            self.cursor = (self.cursor - 1) % len(SPRITE_CHOICES)
        elif event.key == pygame.K_RIGHT:
            self.cursor = (self.cursor + 1) % len(SPRITE_CHOICES)
        elif event.key == pygame.K_UP:
            self.cursor = (self.cursor - 4) % len(SPRITE_CHOICES)
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 4) % len(SPRITE_CHOICES)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            sprite_key = SPRITE_CHOICES[self.cursor]
            self.game.pop_state()
            self.on_select(sprite_key)
        elif event.key == pygame.K_ESCAPE:
            self.game.pop_state()

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((10, 8, 20))

        # Title
        title = self.font_title.render("Choose Your Character", True, (255, 220, 100))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 40))

        # Grid: 4 columns x 2 rows
        grid_x = SCREEN_WIDTH // 2 - (4 * 80) // 2
        grid_y = 120
        cell_w, cell_h = 80, 100

        for i, preview in enumerate(self.previews):
            col = i % 4
            row = i // 4
            cx = grid_x + col * cell_w + cell_w // 2
            cy = grid_y + row * cell_h + cell_h // 2

            # Selection highlight
            if i == self.cursor:
                highlight = pygame.Rect(cx - 36, cy - 36, 72, 72)
                pygame.draw.rect(screen, (255, 220, 100), highlight, 2, border_radius=4)

            # Draw preview centered
            px = cx - preview.get_width() // 2
            py = cy - preview.get_height() // 2
            screen.blit(preview, (px, py))

        # Label for selected
        key = SPRITE_CHOICES[self.cursor]
        # Extract a friendly name from the key
        name = key.split("/")[-1]
        label = self.font_label.render(name, True, (200, 200, 200))
        screen.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, grid_y + 2 * cell_h + 20))

        # Hints
        hint = self.font_hint.render(
            "[Arrows] Navigate   [ENTER] Select   [ESC] Back",
            True, (100, 100, 100),
        )
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 40))
