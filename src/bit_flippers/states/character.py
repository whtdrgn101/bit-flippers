"""Character screen for viewing and allocating stat points."""
import pygame
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from bit_flippers.player_stats import (
    PlayerStats, save_stats,
    STAT_ORDER, STAT_POINT_VALUES, STAT_DESCRIPTIONS, STAT_DISPLAY_NAMES,
    effective_attack, effective_defense,
)


class CharacterScreenState:
    def __init__(self, game, stats: PlayerStats):
        self.game = game
        self.stats = stats
        self.cursor = 0

        self.font_title = pygame.font.SysFont(None, 36)
        self.font_stat = pygame.font.SysFont(None, 28)
        self.font_desc = pygame.font.SysFont(None, 22)

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((15, 15, 25, 220))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            save_stats(self.stats)
            self.game.pop_state()
        elif event.key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % len(STAT_ORDER)
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % len(STAT_ORDER)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._allocate_point()

    def _allocate_point(self):
        if self.stats.unspent_points <= 0:
            return
        stat_key = STAT_ORDER[self.cursor]
        increment = STAT_POINT_VALUES[stat_key]
        old_val = getattr(self.stats, stat_key)
        setattr(self.stats, stat_key, old_val + increment)
        self.stats.unspent_points -= 1

        # When allocating to max_hp/max_sp, also increase current values
        if stat_key == "max_hp":
            self.stats.current_hp += increment
        elif stat_key == "max_sp":
            self.stats.current_sp += increment

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title = self.font_title.render("CHARACTER", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

        # Unspent points
        pts_color = (255, 220, 100) if self.stats.unspent_points > 0 else (160, 160, 160)
        pts_text = self.font_stat.render(
            f"Unspent Points: {self.stats.unspent_points}", True, pts_color
        )
        screen.blit(pts_text, (SCREEN_WIDTH // 2 - pts_text.get_width() // 2, 56))

        # Level / XP info
        info = self.font_desc.render(
            f"Level {self.stats.level}   XP: {self.stats.xp}   Scrap: {self.stats.money}",
            True, (180, 180, 180),
        )
        screen.blit(info, (SCREEN_WIDTH // 2 - info.get_width() // 2, 82))

        # Stat list
        list_x = 80
        list_y = 115
        row_height = 32

        for i, stat_key in enumerate(STAT_ORDER):
            is_selected = i == self.cursor
            value = getattr(self.stats, stat_key)
            display_name = STAT_DISPLAY_NAMES[stat_key]
            increment = STAT_POINT_VALUES[stat_key]

            # Highlight color
            if is_selected:
                color = (255, 220, 100)
                prefix = "> "
            else:
                color = (200, 200, 200)
                prefix = "  "

            # Stat name and value
            label = f"{prefix}{display_name}: {value}"
            if self.stats.unspent_points > 0:
                label += f"  (+{increment})"

            text = self.font_stat.render(label, True, color)
            screen.blit(text, (list_x, list_y + i * row_height))

        # Description for selected stat
        selected_key = STAT_ORDER[self.cursor]
        desc_text = STAT_DESCRIPTIONS.get(selected_key, "")
        desc_surf = self.font_desc.render(desc_text, True, (180, 180, 180))
        screen.blit(desc_surf, (80, list_y + len(STAT_ORDER) * row_height + 20))

        # Derived stats
        derived_y = list_y + len(STAT_ORDER) * row_height + 50
        atk = effective_attack(self.stats)
        dfn = effective_defense(self.stats)
        derived = self.font_desc.render(
            f"Attack: {atk}   Defense: {dfn}   HP: {self.stats.current_hp}/{self.stats.max_hp}   SP: {self.stats.current_sp}/{self.stats.max_sp}",
            True, (160, 200, 160),
        )
        screen.blit(derived, (80, derived_y))

        # Controls hint
        hint = self.font_desc.render(
            "[ESC] Close   [ENTER] Allocate Point   [UP/DOWN] Navigate",
            True, (120, 120, 120),
        )
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 30))
