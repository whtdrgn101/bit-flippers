"""Level-up celebration overlay with particles and auto-dismiss."""
import math

import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from bit_flippers.particles import spawn_particles, update_particles, draw_particles


# Gold particle burst preset for level-up
_LEVEL_UP_PRESET = "level_up"

# Register it dynamically so particles.py stays generic
from bit_flippers.particles import SKILL_PARTICLES
SKILL_PARTICLES[_LEVEL_UP_PRESET] = {
    "color": (255, 220, 80),
    "pattern": "burst",
    "count": 30,
    "speed": 120,
    "lifetime": 1.2,
    "size": 3.5,
    "target": "player",
    "shake": 0,
}


class LevelUpState:
    """Semi-transparent celebration overlay for leveling up."""

    AUTO_DISMISS = 2.0  # seconds before auto-dismiss

    def __init__(self, game, new_level, stat_points, skill_points):
        self.game = game
        self.new_level = new_level
        self.stat_points = stat_points
        self.skill_points = skill_points
        self.timer = 0.0

        self.font_big = get_font(48)
        self.font_med = get_font(28)
        self.font_hint = get_font(22)

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((10, 10, 30, 180))

        # Spawn gold particle burst at center
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2 - 30
        self.particles = spawn_particles(cx, cy, _LEVEL_UP_PRESET)

        # Try to play level_up SFX
        self.game.audio.play_sfx("level_up")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.game.pop_state()

    def update(self, dt):
        self.timer += dt
        self.particles = update_particles(self.particles, dt)
        if self.timer >= self.AUTO_DISMISS:
            self.game.pop_state()

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Draw particles behind text
        draw_particles(screen, self.particles)

        cx = SCREEN_WIDTH // 2

        # "LEVEL UP!" with subtle pulse
        pulse = 1.0 + 0.05 * math.sin(self.timer * 6)
        title = self.font_big.render("LEVEL UP!", True, (255, 220, 80))
        tw, th = title.get_size()
        scaled = pygame.transform.scale(title, (int(tw * pulse), int(th * pulse)))
        screen.blit(scaled, (cx - scaled.get_width() // 2, SCREEN_HEIGHT // 3 - scaled.get_height() // 2))

        # Info lines
        y = SCREEN_HEIGHT // 2
        level_surf = self.font_med.render(f"Now Level {self.new_level}", True, (255, 255, 255))
        screen.blit(level_surf, (cx - level_surf.get_width() // 2, y))
        y += 34

        if self.stat_points > 0:
            stat_surf = self.font_med.render(f"+{self.stat_points} stat point{'s' if self.stat_points > 1 else ''}", True, (100, 255, 100))
            screen.blit(stat_surf, (cx - stat_surf.get_width() // 2, y))
            y += 30

        if self.skill_points > 0:
            skill_surf = self.font_med.render(f"+{self.skill_points} skill point{'s' if self.skill_points > 1 else ''}", True, (100, 180, 255))
            screen.blit(skill_surf, (cx - skill_surf.get_width() // 2, y))
            y += 30

        # Dismiss hint
        hint = self.font_hint.render("[SPACE to continue]", True, (160, 160, 160))
        screen.blit(hint, (cx - hint.get_width() // 2, SCREEN_HEIGHT * 2 // 3 + 20))
