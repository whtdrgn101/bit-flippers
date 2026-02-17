import pygame
from bit_flippers.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    DIALOGUE_CHARS_PER_SEC,
    COLOR_DIALOGUE_BG,
    COLOR_DIALOGUE_TEXT,
    COLOR_NPC_NAME,
)


class DialogueState:
    def __init__(self, game, npc_name, lines, on_close=None):
        self.game = game
        self.npc_name = npc_name
        self.lines = lines
        self.on_close = on_close
        self.line_index = 0
        self.chars_revealed = 0.0
        self.fully_revealed = False

        # Panel dimensions
        self.panel_height = SCREEN_HEIGHT // 4
        self.panel_y = SCREEN_HEIGHT - self.panel_height
        self.padding = 12

        # Pre-render fonts
        self.name_font = pygame.font.SysFont(None, 28)
        self.text_font = pygame.font.SysFont(None, 24)

        # Semi-transparent panel surface
        self.panel_surface = pygame.Surface(
            (SCREEN_WIDTH, self.panel_height), pygame.SRCALPHA
        )
        self.panel_surface.fill(COLOR_DIALOGUE_BG)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_SPACE,
            pygame.K_RETURN,
        ):
            if not self.fully_revealed:
                # Instantly reveal full line
                self.chars_revealed = len(self.lines[self.line_index])
                self.fully_revealed = True
            else:
                # Advance to next line or dismiss
                self.line_index += 1
                if self.line_index >= len(self.lines):
                    self.game.pop_state()
                    if self.on_close:
                        self.on_close()
                else:
                    self.chars_revealed = 0.0
                    self.fully_revealed = False
                    self.game.audio.play_sfx("dialogue_advance")

    def update(self, dt):
        if not self.fully_revealed:
            self.chars_revealed += DIALOGUE_CHARS_PER_SEC * dt
            current_line = self.lines[self.line_index]
            if self.chars_revealed >= len(current_line):
                self.chars_revealed = len(current_line)
                self.fully_revealed = True

    def draw(self, screen):
        # Don't clear screen — overworld stays visible underneath
        screen.blit(self.panel_surface, (0, self.panel_y))

        # NPC name in gold
        name_surf = self.name_font.render(self.npc_name, True, COLOR_NPC_NAME)
        screen.blit(name_surf, (self.padding, self.panel_y + self.padding))

        # Dialogue text with typewriter effect
        current_line = self.lines[self.line_index]
        visible_text = current_line[: int(self.chars_revealed)]
        text_surf = self.text_font.render(visible_text, True, COLOR_DIALOGUE_TEXT)
        screen.blit(
            text_surf,
            (self.padding, self.panel_y + self.padding + 28),
        )

        # Prompt indicator when line is fully revealed
        if self.fully_revealed:
            is_last = self.line_index >= len(self.lines) - 1
            prompt = "[SPACE to close]" if is_last else "[SPACE]"
            prompt_surf = self.text_font.render(prompt, True, (180, 180, 180))
            screen.blit(
                prompt_surf,
                (
                    SCREEN_WIDTH - prompt_surf.get_width() - self.padding,
                    self.panel_y + self.panel_height - prompt_surf.get_height() - self.padding,
                ),
            )
