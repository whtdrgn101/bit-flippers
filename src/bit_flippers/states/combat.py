import random
from enum import Enum, auto

import pygame
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from bit_flippers.combat import create_enemy_combatant, CombatEntity
from bit_flippers.items import ITEM_REGISTRY


class Phase(Enum):
    CHOOSING = auto()
    PLAYER_ATTACK = auto()
    ENEMY_ATTACK = auto()
    VICTORY = auto()
    DEFEAT = auto()
    FLED = auto()
    ITEM_SELECT = auto()


MENU_OPTIONS = ["Attack", "Defend", "Item", "Flee"]


class CombatState:
    def __init__(self, game, enemy_data, overworld, inventory=None):
        self.game = game
        self.overworld = overworld  # reference to overworld for HP sync
        self.inventory = inventory
        self.enemy = create_enemy_combatant(enemy_data)

        # Build a lightweight player combatant using overworld HP
        from bit_flippers.sprites import create_placeholder_player
        from bit_flippers.settings import PLAYER_MAX_HP, PLAYER_ATTACK, PLAYER_DEFENSE

        self.player = CombatEntity(
            name="Player",
            hp=overworld.player_hp,
            max_hp=PLAYER_MAX_HP,
            attack=PLAYER_ATTACK,
            defense=PLAYER_DEFENSE,
            sprite=create_placeholder_player(),
        )

        self.phase = Phase.CHOOSING
        self.menu_index = 0
        self.defending = False
        self.defense_buff = 0  # temporary defense boost from Iron Plating

        # Item selection state
        self.item_list: list[str] = []
        self.item_index = 0

        # Animation timers
        self.phase_timer = 0.0
        self.flash_timer = 0.0
        self.flash_target = None  # "player" or "enemy"
        self.damage_text = ""
        self.damage_text_timer = 0.0
        self.damage_text_pos = (0, 0)
        self.message = ""
        self.message_timer = 0.0

        # Fonts
        self.font = pygame.font.SysFont(None, 28)
        self.font_big = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 22)

        # Layout positions
        self.player_pos = (SCREEN_WIDTH // 4 - TILE_SIZE, SCREEN_HEIGHT // 2 - TILE_SIZE)
        self.enemy_pos = (3 * SCREEN_WIDTH // 4 - TILE_SIZE, SCREEN_HEIGHT // 2 - TILE_SIZE)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.phase == Phase.CHOOSING:
            if event.key == pygame.K_UP:
                self.menu_index = (self.menu_index - 1) % len(MENU_OPTIONS)
            elif event.key == pygame.K_DOWN:
                self.menu_index = (self.menu_index + 1) % len(MENU_OPTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._execute_player_action(MENU_OPTIONS[self.menu_index])
        elif self.phase == Phase.ITEM_SELECT:
            if event.key == pygame.K_ESCAPE:
                self.phase = Phase.CHOOSING
            elif event.key == pygame.K_UP:
                self.item_index = (self.item_index - 1) % len(self.item_list)
            elif event.key == pygame.K_DOWN:
                self.item_index = (self.item_index + 1) % len(self.item_list)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._use_combat_item(self.item_list[self.item_index])
        elif self.phase in (Phase.VICTORY, Phase.DEFEAT, Phase.FLED):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._finish_combat()

    def _execute_player_action(self, action):
        if action == "Attack":
            damage = max(1, self.player.attack - self.enemy.defense + random.randint(-1, 1))
            self.enemy.hp = max(0, self.enemy.hp - damage)
            self.flash_target = "enemy"
            self.flash_timer = 0.3
            self.damage_text = f"-{damage}"
            self.damage_text_timer = 1.0
            self.damage_text_pos = (self.enemy_pos[0] + TILE_SIZE // 2, self.enemy_pos[1] - 10)
            self.defending = False

            if not self.enemy.is_alive:
                self.phase = Phase.VICTORY
                self.message = f"Defeated {self.enemy.name}!"
                self.message_timer = 0.0
            else:
                self.phase = Phase.PLAYER_ATTACK
                self.phase_timer = 0.6

        elif action == "Defend":
            self.defending = True
            self.message = "Bracing for impact..."
            self.phase = Phase.PLAYER_ATTACK
            self.phase_timer = 0.4

        elif action == "Item":
            if self.inventory is None:
                self.message = "No items!"
                return
            consumables = self.inventory.get_consumables()
            if not consumables:
                self.message = "No items!"
                return
            self.item_list = consumables
            self.item_index = 0
            self.phase = Phase.ITEM_SELECT

        elif action == "Flee":
            if random.random() < 0.5:
                self.phase = Phase.FLED
                self.message = "Got away safely!"
                self.message_timer = 0.0
            else:
                self.message = "Couldn't escape!"
                self.phase = Phase.PLAYER_ATTACK
                self.phase_timer = 0.6

    def _use_combat_item(self, item_name):
        item = ITEM_REGISTRY.get(item_name)
        if not item:
            return

        self.inventory.remove(item_name)
        self.defending = False

        if item.effect_type == "heal":
            from bit_flippers.settings import PLAYER_MAX_HP
            old_hp = self.player.hp
            self.player.hp = min(self.player.max_hp, self.player.hp + item.effect_value)
            healed = self.player.hp - old_hp
            self.message = f"Used {item_name}! Restored {healed} HP."
        elif item.effect_type == "damage":
            self.enemy.hp = max(0, self.enemy.hp - item.effect_value)
            self.flash_target = "enemy"
            self.flash_timer = 0.3
            self.damage_text = f"-{item.effect_value}"
            self.damage_text_timer = 1.0
            self.damage_text_pos = (self.enemy_pos[0] + TILE_SIZE // 2, self.enemy_pos[1] - 10)
            self.message = f"Used {item_name}! Dealt {item.effect_value} damage."
            if not self.enemy.is_alive:
                self.phase = Phase.VICTORY
                self.message = f"Defeated {self.enemy.name}!"
                self.message_timer = 0.0
                return
        elif item.effect_type == "buff_defense":
            self.defense_buff += item.effect_value
            self.player.defense += item.effect_value
            self.message = f"Used {item_name}! Defense +{item.effect_value}."

        self.phase = Phase.PLAYER_ATTACK
        self.phase_timer = 0.6

    def _do_enemy_attack(self):
        raw_damage = max(1, self.enemy.attack - self.player.defense + random.randint(-1, 1))
        damage = max(1, raw_damage // 2) if self.defending else raw_damage
        self.player.hp = max(0, self.player.hp - damage)
        self.flash_target = "player"
        self.flash_timer = 0.3
        self.damage_text = f"-{damage}"
        self.damage_text_timer = 1.0
        self.damage_text_pos = (self.player_pos[0] + TILE_SIZE // 2, self.player_pos[1] - 10)
        self.defending = False

        if not self.player.is_alive:
            self.phase = Phase.DEFEAT
            self.message = "You were defeated..."
            self.message_timer = 0.0
        else:
            self.phase = Phase.ENEMY_ATTACK
            self.phase_timer = 0.6

    def _finish_combat(self):
        # Remove temporary defense buff before syncing
        self.player.defense -= self.defense_buff
        # Sync HP back to overworld
        self.overworld.player_hp = self.player.hp
        # Notify overworld of victory so scripted enemies can be removed
        if self.phase == Phase.VICTORY:
            self.overworld.on_combat_victory()
        else:
            self.overworld.on_combat_end()
        self.game.pop_state()

    def update(self, dt):
        # Update sprites
        self.player.sprite.update(dt)
        self.enemy.sprite.update(dt)

        # Timers
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.damage_text_timer > 0:
            self.damage_text_timer -= dt
        if self.message_timer < 10:
            self.message_timer += dt

        # Phase transitions
        if self.phase == Phase.PLAYER_ATTACK:
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                self._do_enemy_attack()
        elif self.phase == Phase.ENEMY_ATTACK:
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                self.phase = Phase.CHOOSING
                self.message = ""

    def draw(self, screen):
        # Dark background (full screen combat replaces overworld visually)
        screen.fill((15, 10, 25))

        # Title
        title = self.font_big.render(f"VS  {self.enemy.name}", True, (255, 200, 100))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

        # Draw combatants (scaled up 2x for visibility)
        self._draw_combatant(screen, self.player, self.player_pos, "player")
        self._draw_combatant(screen, self.enemy, self.enemy_pos, "enemy")

        # HP bars
        self._draw_hp_bar(screen, self.player, self.player_pos[0] - 10, self.player_pos[1] - 30, 80)
        self._draw_hp_bar(screen, self.enemy, self.enemy_pos[0] - 10, self.enemy_pos[1] - 30, 80)

        # Damage text
        if self.damage_text_timer > 0:
            alpha = min(255, int(self.damage_text_timer * 255))
            dmg_surf = self.font.render(self.damage_text, True, (255, 80, 80))
            dmg_surf.set_alpha(alpha)
            screen.blit(dmg_surf, self.damage_text_pos)

        # Message area
        if self.message:
            msg_surf = self.font.render(self.message, True, (220, 220, 220))
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT - 140))

        # Action menu (only during CHOOSING phase)
        if self.phase == Phase.CHOOSING:
            self._draw_menu(screen)
        elif self.phase == Phase.ITEM_SELECT:
            self._draw_menu(screen)
            self._draw_item_submenu(screen)
        elif self.phase in (Phase.VICTORY, Phase.DEFEAT, Phase.FLED):
            prompt = self.font_small.render("[SPACE to continue]", True, (180, 180, 180))
            screen.blit(
                prompt,
                (SCREEN_WIDTH // 2 - prompt.get_width() // 2, SCREEN_HEIGHT - 40),
            )

    def _draw_combatant(self, screen, entity, pos, who):
        img = entity.sprite.image
        # Scale up 2x
        scaled = pygame.transform.scale(img, (TILE_SIZE * 2, TILE_SIZE * 2))

        # Flash effect on hit
        if self.flash_timer > 0 and self.flash_target == who:
            flash_surf = scaled.copy()
            flash_surf.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(flash_surf, (pos[0] - TILE_SIZE // 2, pos[1] - TILE_SIZE // 2))
        else:
            screen.blit(scaled, (pos[0] - TILE_SIZE // 2, pos[1] - TILE_SIZE // 2))

    def _draw_hp_bar(self, screen, entity, x, y, width):
        bar_height = 8
        ratio = entity.hp / entity.max_hp if entity.max_hp > 0 else 0

        # Background
        pygame.draw.rect(screen, (60, 60, 60), (x, y, width, bar_height))
        # Fill
        color = (80, 200, 80) if ratio > 0.5 else (200, 200, 40) if ratio > 0.25 else (200, 60, 60)
        pygame.draw.rect(screen, color, (x, y, int(width * ratio), bar_height))
        # Border
        pygame.draw.rect(screen, (180, 180, 180), (x, y, width, bar_height), 1)

        # HP text
        hp_text = self.font_small.render(f"{entity.hp}/{entity.max_hp}", True, (255, 255, 255))
        screen.blit(hp_text, (x, y - 16))
        name_text = self.font_small.render(entity.name, True, (255, 255, 255))
        screen.blit(name_text, (x, y - 32))

    def _draw_menu(self, screen):
        menu_x = SCREEN_WIDTH // 2 - 60
        menu_y = SCREEN_HEIGHT - 120
        for i, option in enumerate(MENU_OPTIONS):
            color = (255, 255, 100) if i == self.menu_index else (200, 200, 200)
            prefix = "> " if i == self.menu_index else "  "
            text = self.font.render(f"{prefix}{option}", True, color)
            screen.blit(text, (menu_x, menu_y + i * 28))

    def _draw_item_submenu(self, screen):
        box_x = SCREEN_WIDTH // 2 + 60
        box_y = SCREEN_HEIGHT - 140
        row_h = 24
        padding = 8

        # Background box
        box_h = len(self.item_list) * row_h + padding * 2
        box_w = 180
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((20, 20, 40, 220))
        screen.blit(bg, (box_x, box_y))
        pygame.draw.rect(screen, (180, 180, 180), (box_x, box_y, box_w, box_h), 1)

        for i, name in enumerate(self.item_list):
            count = self.inventory.get_count(name)
            is_sel = i == self.item_index
            color = (255, 220, 100) if is_sel else (200, 200, 200)
            prefix = "> " if is_sel else "  "
            label = f"{prefix}{name} x{count}"
            text = self.font_small.render(label, True, color)
            screen.blit(text, (box_x + padding, box_y + padding + i * row_h))

        # Hint
        hint = self.font_small.render("[ESC] Cancel", True, (120, 120, 120))
        screen.blit(hint, (box_x, box_y + box_h + 4))
