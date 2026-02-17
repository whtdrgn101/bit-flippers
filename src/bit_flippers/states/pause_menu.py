"""Pause menu with resume, save, sub-screen access, and quit."""
import pygame
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT

MENU_OPTIONS = ["Resume", "Save Game", "Inventory", "Quest Log", "Character", "Skill Tree", "Quit Game"]


class PauseMenuState:
    def __init__(self, game, overworld):
        self.game = game
        self.overworld = overworld
        self.cursor = 0

        self.font_title = pygame.font.SysFont(None, 40)
        self.font_option = pygame.font.SysFont(None, 28)
        self.font_hint = pygame.font.SysFont(None, 22)

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((10, 10, 20, 200))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.game.pop_state()
        elif event.key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % len(MENU_OPTIONS)
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % len(MENU_OPTIONS)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._select(MENU_OPTIONS[self.cursor])

    def _select(self, option):
        if option == "Resume":
            self.game.pop_state()
        elif option == "Save Game":
            from bit_flippers.save import save_game
            save_game(self.overworld)
            self.game.pop_state()
            self.overworld.pickup_message = "Game saved!"
            from bit_flippers.settings import PICKUP_MESSAGE_DURATION
            self.overworld.pickup_message_timer = PICKUP_MESSAGE_DURATION
        elif option == "Inventory":
            from bit_flippers.states.inventory import InventoryState
            self.game.pop_state()
            self.game.push_state(
                InventoryState(self.game, self.overworld.inventory, self.overworld)
            )
        elif option == "Quest Log":
            from bit_flippers.states.quest_log import QuestLogState
            self.game.pop_state()
            self.game.push_state(QuestLogState(self.game, self.overworld.player_quests))
        elif option == "Character":
            from bit_flippers.states.character import CharacterScreenState
            self.game.pop_state()
            self.game.push_state(
                CharacterScreenState(self.game, self.overworld.stats, self.overworld.player_skills, self.overworld)
            )
        elif option == "Skill Tree":
            from bit_flippers.states.skill_tree import SkillTreeState
            self.game.pop_state()
            self.game.push_state(
                SkillTreeState(self.game, self.overworld.player_skills, self.overworld.stats, self.overworld)
            )
        elif option == "Quit Game":
            self.game.running = False

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title = self.font_title.render("PAUSED", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 4))

        # Menu options
        menu_x = SCREEN_WIDTH // 2 - 60
        menu_y = SCREEN_HEIGHT // 4 + 60
        for i, option in enumerate(MENU_OPTIONS):
            is_selected = i == self.cursor
            color = (255, 220, 100) if is_selected else (200, 200, 200)
            prefix = "> " if is_selected else "  "
            text = self.font_option.render(f"{prefix}{option}", True, color)
            screen.blit(text, (menu_x, menu_y + i * 34))

        # Controls hint
        hint = self.font_hint.render(
            "[UP/DOWN] Navigate   [ENTER] Select   [ESC] Resume",
            True, (120, 120, 120),
        )
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 30))
