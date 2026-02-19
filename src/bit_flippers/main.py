import pygame
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, COLOR_BLACK
from bit_flippers.audio import AudioManager
from bit_flippers.save import load_config
from bit_flippers.states.title_screen import TitleScreenState


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bit Flippers")
        self.clock = pygame.time.Clock()
        self.running = True
        self.audio = AudioManager()

        # Apply saved volume preferences
        config = load_config()
        if "sfx_volume" in config:
            self.audio.set_sfx_volume(config["sfx_volume"] / 100.0)
        if "music_volume" in config:
            self.audio.set_music_volume(config["music_volume"] / 100.0)

        self.state_stack: list = []
        self.state_stack.append(TitleScreenState(self))

    @property
    def active_state(self):
        return self.state_stack[-1]

    def push_state(self, state):
        self.state_stack.append(state)

    def pop_state(self):
        if len(self.state_stack) > 1:
            self.state_stack.pop()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            self.active_state.handle_event(event)

    def update(self, dt):
        self.active_state.update(dt)

    def draw(self):
        self.screen.fill(COLOR_BLACK)
        # Draw all states in order so overlays (dialogue, combat) render on top
        for state in self.state_stack:
            state.draw(self.screen)
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()


def main():
    pygame.init()
    game = Game()
    game.run()
    pygame.quit()


if __name__ == "__main__":
    main()
