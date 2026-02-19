"""Title screen with New Game / Continue / About."""
import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from bit_flippers.strings import get_string, load_strings
from bit_flippers.save import has_save


class TitleScreenState:
    def __init__(self, game):
        self.game = game
        self.cursor = 0
        self.options = ["New Game", "Continue", "About"]

        self.font_title = get_font(56)
        self.font_subtitle = get_font(28)
        self.font_option = get_font(32)
        self.font_hint = get_font(22)

        self.title_text = get_string("title_screen.title")
        self.subtitle_text = get_string("title_screen.subtitle")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % len(self.options)
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % len(self.options)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._select(self.options[self.cursor])

    def _select(self, option):
        if option == "New Game":
            from bit_flippers.states.overworld import OverworldState
            self.game.state_stack.clear()
            self.game.push_state(OverworldState(self.game))
        elif option == "Continue":
            if not has_save():
                return
            from bit_flippers.states.save_menu import SaveMenuState

            def _on_load(save_data, slot, _game=self.game):
                from bit_flippers.states.overworld import OverworldState
                _game.state_stack.clear()
                _game.push_state(OverworldState(_game, save_data=save_data))

            self.game.push_state(SaveMenuState(self.game, mode="load", on_load=_on_load))
        elif option == "About":
            from bit_flippers.states.about_screen import AboutScreenState
            self.game.push_state(AboutScreenState(self.game))

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((10, 8, 20))

        # Title
        title_surf = self.font_title.render(self.title_text, True, (255, 220, 100))
        screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 80))

        # Subtitle
        sub_surf = self.font_subtitle.render(self.subtitle_text, True, (180, 180, 200))
        screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 140))

        # Menu
        menu_y = SCREEN_HEIGHT // 2
        save_exists = has_save()
        for i, option in enumerate(self.options):
            is_selected = i == self.cursor

            if option == "Continue" and not save_exists:
                color = (80, 80, 80)
            elif is_selected:
                color = (255, 220, 100)
            else:
                color = (200, 200, 200)

            prefix = "> " if is_selected else "  "
            text = self.font_option.render(f"{prefix}{option}", True, color)
            screen.blit(text, (SCREEN_WIDTH // 2 - 70, menu_y + i * 40))

        # Hint
        hint = self.font_hint.render(
            "[UP/DOWN] Navigate   [ENTER] Select",
            True, (100, 100, 100),
        )
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 40))
