"""Screen transition states: fade-to-black and combat wipe."""
import pygame
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT


class FadeTransition:
    """Fade to black, execute callback, then fade back in.

    Used for door transitions and returning from combat.
    """

    def __init__(self, game, callback):
        self.game = game
        self.callback = callback
        self.phase = "out"  # "out" -> "in" -> done
        self.alpha = 0.0
        self.fade_speed = 255 / 0.4  # full fade in 0.4s
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.overlay.fill((0, 0, 0))
        self._callback_done = False

    def handle_event(self, event):
        pass  # swallow all input

    def update(self, dt):
        if self.phase == "out":
            self.alpha = min(255.0, self.alpha + self.fade_speed * dt)
            if self.alpha >= 255.0:
                if not self._callback_done:
                    self.callback()
                    self._callback_done = True
                self.phase = "in"
        elif self.phase == "in":
            self.alpha = max(0.0, self.alpha - self.fade_speed * dt)
            if self.alpha <= 0.0:
                self.game.pop_state()

    def draw(self, screen):
        self.overlay.set_alpha(int(self.alpha))
        screen.blit(self.overlay, (0, 0))


class CombatTransition:
    """White flash + black bar stripe wipe for combat entry."""

    def __init__(self, game, callback):
        self.game = game
        self.callback = callback
        self.timer = 0.0
        self._callback_done = False

        self.white_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.white_overlay.fill((255, 255, 255))
        self.black_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.black_overlay.fill((0, 0, 0))

        # Timing
        self.flash_ramp = 0.12
        self.flash_hold = 0.17
        self.wipe_end = 0.50
        self.total = 0.50

    def handle_event(self, event):
        pass  # swallow all input

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.wipe_end and not self._callback_done:
            self._callback_done = True
            self.game.pop_state()  # pop transition first
            self.callback()        # then push combat state

    def draw(self, screen):
        t = self.timer

        if t < self.flash_ramp:
            # Ramp white alpha 0->255
            ratio = t / self.flash_ramp
            self.white_overlay.set_alpha(int(255 * ratio))
            screen.blit(self.white_overlay, (0, 0))

        elif t < self.flash_hold:
            # Hold white
            self.white_overlay.set_alpha(255)
            screen.blit(self.white_overlay, (0, 0))

        else:
            # Black bars close in from top/bottom with horizontal stripes
            progress = min(1.0, (t - self.flash_hold) / (self.wipe_end - self.flash_hold))
            bar_height = int(SCREEN_HEIGHT * 0.5 * progress)

            # Top bar
            if bar_height > 0:
                pygame.draw.rect(screen, (0, 0, 0), (0, 0, SCREEN_WIDTH, bar_height))
            # Bottom bar
            if bar_height > 0:
                pygame.draw.rect(screen, (0, 0, 0),
                                 (0, SCREEN_HEIGHT - bar_height, SCREEN_WIDTH, bar_height))

            # Horizontal stripe lines at the edges of the bars
            stripe_color = (40, 40, 60)
            num_stripes = 4
            for i in range(num_stripes):
                y_top = bar_height - (i + 1) * 3
                y_bot = SCREEN_HEIGHT - bar_height + i * 3
                if 0 <= y_top < SCREEN_HEIGHT:
                    pygame.draw.line(screen, stripe_color, (0, y_top), (SCREEN_WIDTH, y_top))
                if 0 <= y_bot < SCREEN_HEIGHT:
                    pygame.draw.line(screen, stripe_color, (0, y_bot), (SCREEN_WIDTH, y_bot))
