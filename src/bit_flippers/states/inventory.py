import pygame
from bit_flippers.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_INVENTORY_BG,
    COLOR_ITEM_HIGHLIGHT,
    PLAYER_MAX_HP,
)
from bit_flippers.items import ITEM_REGISTRY


class InventoryState:
    def __init__(self, game, inventory, overworld):
        self.game = game
        self.inventory = inventory
        self.overworld = overworld
        self.cursor = 0
        self.scroll_offset = 0
        self.max_visible = 10
        self.message = ""
        self.message_timer = 0.0

        self.font_title = pygame.font.SysFont(None, 36)
        self.font_item = pygame.font.SysFont(None, 26)
        self.font_desc = pygame.font.SysFont(None, 22)

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill(COLOR_INVENTORY_BG)

    def _get_item_list(self):
        """Return sorted list of (name, count) for all items with count > 0."""
        return [
            (name, count)
            for name, count in sorted(self.inventory.items.items())
            if count > 0
        ]

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        items = self._get_item_list()

        if event.key == pygame.K_ESCAPE:
            self.game.pop_state()
        elif event.key == pygame.K_UP:
            if items:
                self.cursor = (self.cursor - 1) % len(items)
                self._ensure_visible()
        elif event.key == pygame.K_DOWN:
            if items:
                self.cursor = (self.cursor + 1) % len(items)
                self._ensure_visible()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if items:
                name, _count = items[self.cursor]
                self._try_use_item(name)

    def _ensure_visible(self):
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.cursor - self.max_visible + 1

    def _try_use_item(self, item_name):
        item = ITEM_REGISTRY.get(item_name)
        if not item or item.item_type != "consumable":
            self.message = "Can't use that here."
            self.message_timer = 1.5
            return

        if item.effect_type == "heal":
            if self.overworld.player_hp >= PLAYER_MAX_HP:
                self.message = "HP is already full!"
                self.message_timer = 1.5
                return
            self.overworld.player_hp = min(
                PLAYER_MAX_HP, self.overworld.player_hp + item.effect_value
            )
            self.inventory.remove(item_name)
            self.message = f"Used {item_name}! HP restored."
            self.message_timer = 1.5
        else:
            self.message = "Can't use that here."
            self.message_timer = 1.5

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title = self.font_title.render("INVENTORY", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        items = self._get_item_list()

        if not items:
            empty = self.font_item.render("No items.", True, (160, 160, 160))
            screen.blit(empty, (SCREEN_WIDTH // 2 - empty.get_width() // 2, 100))
        else:
            list_x = 80
            list_y = 80
            row_height = 30

            visible = items[self.scroll_offset : self.scroll_offset + self.max_visible]
            for i, (name, count) in enumerate(visible):
                abs_index = self.scroll_offset + i
                is_selected = abs_index == self.cursor

                color = COLOR_ITEM_HIGHLIGHT if is_selected else (200, 200, 200)
                prefix = "> " if is_selected else "  "
                text = self.font_item.render(f"{prefix}{name} x{count}", True, color)
                screen.blit(text, (list_x, list_y + i * row_height))

            # Scroll indicators
            if self.scroll_offset > 0:
                up_arrow = self.font_desc.render("^ more ^", True, (160, 160, 160))
                screen.blit(up_arrow, (list_x, list_y - 20))
            if self.scroll_offset + self.max_visible < len(items):
                down_arrow = self.font_desc.render("v more v", True, (160, 160, 160))
                screen.blit(
                    down_arrow,
                    (list_x, list_y + self.max_visible * row_height + 4),
                )

            # Description for selected item
            if 0 <= self.cursor < len(items):
                selected_name = items[self.cursor][0]
                item_data = ITEM_REGISTRY.get(selected_name)
                if item_data:
                    desc = self.font_desc.render(
                        item_data.description, True, (180, 180, 180)
                    )
                    screen.blit(desc, (80, SCREEN_HEIGHT - 80))

        # Feedback message
        if self.message:
            msg = self.font_item.render(self.message, True, (100, 255, 100))
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT - 40))

        # Controls hint
        hint = self.font_desc.render("[ESC] Close   [ENTER] Use", True, (120, 120, 120))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 20))
