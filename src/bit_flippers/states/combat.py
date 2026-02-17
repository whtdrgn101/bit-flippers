import random
from enum import Enum, auto

import pygame
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, COLOR_SP_BAR
from bit_flippers.combat import create_enemy_combatant, CombatEntity
from bit_flippers.items import ITEM_REGISTRY
from bit_flippers.player_stats import effective_attack, effective_defense, calc_hit_chance
from bit_flippers.skills import SKILL_DEFS, calc_skill_effect


class Phase(Enum):
    CHOOSING = auto()
    PLAYER_ATTACK = auto()
    ENEMY_ATTACK = auto()
    VICTORY = auto()
    DEFEAT = auto()
    FLED = auto()
    ITEM_SELECT = auto()
    SKILL_SELECT = auto()


MENU_OPTIONS = ["Attack", "Defend", "Skill", "Item", "Flee"]


class CombatState:
    def __init__(self, game, enemy_data, overworld, inventory=None, player_skills=None):
        self.game = game
        self.overworld = overworld  # reference to overworld for HP sync
        self.inventory = inventory
        self.player_skills = player_skills
        self.enemy_data = enemy_data
        self.enemy = create_enemy_combatant(enemy_data)

        # Reward display (set on victory)
        self.reward_xp = 0
        self.reward_money = 0

        # Build a player combatant using stat-derived values
        from bit_flippers.sprites import load_player

        stats = overworld.stats
        self.player_stats = stats
        self.equipment = getattr(overworld, "equipment", None)

        # Apply equipment bonuses to max_hp/max_sp/dex/int for combat
        eq_bonuses = self.equipment.get_total_bonuses() if self.equipment else {}
        combat_max_hp = stats.max_hp + eq_bonuses.get("max_hp", 0)
        combat_max_sp = stats.max_sp + eq_bonuses.get("max_sp", 0)
        combat_hp = min(stats.current_hp + eq_bonuses.get("max_hp", 0), combat_max_hp)

        self.player = CombatEntity(
            name="Player",
            hp=combat_hp,
            max_hp=combat_max_hp,
            attack=effective_attack(stats, self.equipment),
            defense=effective_defense(stats, self.equipment),
            sprite=load_player(),
        )
        # Store bonus max_sp/dex for combat calculations
        self._eq_max_sp_bonus = eq_bonuses.get("max_sp", 0)
        self._eq_dex_bonus = eq_bonuses.get("dexterity", 0)
        self._eq_int_bonus = eq_bonuses.get("intelligence", 0)
        self._eq_max_hp_bonus = eq_bonuses.get("max_hp", 0)

        self.phase = Phase.CHOOSING
        self.menu_index = 0
        self.defending = False
        self.defense_buff = 0  # temporary defense boost from Iron Plating / skills

        # Item selection state
        self.item_list: list[str] = []
        self.item_index = 0

        # Skill selection state
        self.skill_list: list[str] = []  # list of skill_ids
        self.skill_index = 0

        # Enemy debuff tracking
        self.enemy_atk_debuff = 0
        self.enemy_def_debuff = 0
        self.debuff_turns_remaining = 0
        # Store original enemy stats for restoration
        self._enemy_base_attack = self.enemy.attack
        self._enemy_base_defense = self.enemy.defense

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

        # Layout positions — sprites in upper third, leaving room for 5-item menu
        self.player_pos = (SCREEN_WIDTH // 4 - TILE_SIZE, SCREEN_HEIGHT // 3)
        self.enemy_pos = (3 * SCREEN_WIDTH // 4 - TILE_SIZE, SCREEN_HEIGHT // 3)

        # Combat music
        self.game.audio.play_music("combat")

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
        elif self.phase == Phase.SKILL_SELECT:
            if event.key == pygame.K_ESCAPE:
                self.phase = Phase.CHOOSING
            elif event.key == pygame.K_UP:
                self.skill_index = (self.skill_index - 1) % len(self.skill_list)
            elif event.key == pygame.K_DOWN:
                self.skill_index = (self.skill_index + 1) % len(self.skill_list)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._use_combat_skill(self.skill_list[self.skill_index])
        elif self.phase in (Phase.VICTORY, Phase.DEFEAT, Phase.FLED):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._finish_combat()

    def _execute_player_action(self, action):
        if action == "Attack":
            # Hit/miss check (include equipment dex bonus)
            hit_chance = calc_hit_chance(self.player_stats.dexterity + self._eq_dex_bonus, self.enemy_data.dexterity)
            if random.random() > hit_chance:
                self.message = "Attack missed!"
                self.defending = False
                self.phase = Phase.PLAYER_ATTACK
                self.phase_timer = 0.6
                return

            damage = max(1, self.player.attack - self.enemy.defense + random.randint(-1, 1))
            self.enemy.hp = max(0, self.enemy.hp - damage)
            self.game.audio.play_sfx("hit")
            self.flash_target = "enemy"
            self.flash_timer = 0.3
            self.damage_text = f"-{damage}"
            self.damage_text_timer = 1.0
            self.damage_text_pos = (self.enemy_pos[0] + TILE_SIZE // 2, self.enemy_pos[1] - 10)
            self.defending = False

            if not self.enemy.is_alive:
                self._handle_enemy_defeated()
            else:
                self.phase = Phase.PLAYER_ATTACK
                self.phase_timer = 0.6

        elif action == "Defend":
            self.defending = True
            self.message = "Bracing for impact..."
            self.phase = Phase.PLAYER_ATTACK
            self.phase_timer = 0.4

        elif action == "Skill":
            if self.player_skills is None or not self.player_skills.unlocked:
                self.message = "No skills!"
                return
            unlocked = self.player_skills.get_unlocked_skills()
            if not unlocked:
                self.message = "No skills!"
                return
            self.skill_list = [s.skill_id for s in unlocked]
            self.skill_index = 0
            self.phase = Phase.SKILL_SELECT

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

    def _handle_enemy_defeated(self):
        """Shared victory logic for any action that kills the enemy."""
        self.phase = Phase.VICTORY
        self.message = f"Defeated {self.enemy.name}!"
        self.reward_xp = self.enemy_data.xp_reward
        self.reward_money = self.enemy_data.money_reward
        self.message_timer = 0.0
        self.game.audio.stop_music()
        self.game.audio.play_sfx("victory")

    def _use_combat_skill(self, skill_id):
        skill = SKILL_DEFS.get(skill_id)
        if not skill:
            return

        # Check SP
        if self.player_stats.current_sp < skill.sp_cost:
            self.message = "Not enough SP!"
            return

        # Deduct SP
        self.player_stats.current_sp -= skill.sp_cost
        self.defending = False

        # Use a copy of stats with equipment bonuses for skill calculation
        from copy import copy
        combat_stats = copy(self.player_stats)
        combat_stats.intelligence += self._eq_int_bonus
        value = calc_skill_effect(skill, combat_stats)

        if skill.effect_type == "damage":
            self.enemy.hp = max(0, self.enemy.hp - value)
            self.game.audio.play_sfx("hit")
            self.flash_target = "enemy"
            self.flash_timer = 0.3
            self.damage_text = f"-{value}"
            self.damage_text_timer = 1.0
            self.damage_text_pos = (self.enemy_pos[0] + TILE_SIZE // 2, self.enemy_pos[1] - 10)
            self.message = f"{skill.name}! Dealt {value} damage."
            if not self.enemy.is_alive:
                self._handle_enemy_defeated()
                return

        elif skill.effect_type == "heal":
            old_hp = self.player.hp
            self.player.hp = min(self.player.max_hp, self.player.hp + value)
            healed = self.player.hp - old_hp
            self.message = f"{skill.name}! Restored {healed} HP."

        elif skill.effect_type == "buff_defense":
            self.defense_buff += value
            self.player.defense += value
            self.message = f"{skill.name}! Defense +{value}."

        elif skill.effect_type == "drain":
            self.enemy.hp = max(0, self.enemy.hp - value)
            old_hp = self.player.hp
            self.player.hp = min(self.player.max_hp, self.player.hp + value)
            healed = self.player.hp - old_hp
            self.game.audio.play_sfx("hit")
            self.flash_target = "enemy"
            self.flash_timer = 0.3
            self.damage_text = f"-{value}"
            self.damage_text_timer = 1.0
            self.damage_text_pos = (self.enemy_pos[0] + TILE_SIZE // 2, self.enemy_pos[1] - 10)
            self.message = f"{skill.name}! Drained {value}, healed {healed}."
            if not self.enemy.is_alive:
                self._handle_enemy_defeated()
                return

        elif skill.effect_type == "debuff_attack":
            # Clear any existing debuffs first (restore then re-apply)
            self._clear_enemy_debuffs()
            self.enemy_atk_debuff = value
            self.enemy.attack = max(0, self._enemy_base_attack - value)
            # EMP Pulse (tier 2) also reduces DEF
            if skill.skill_id == "emp_pulse":
                self.enemy_def_debuff = value
                self.enemy.defense = max(0, self._enemy_base_defense - value)
                self.message = f"{skill.name}! Enemy ATK-{value}, DEF-{value} for 3 turns."
            else:
                self.message = f"{skill.name}! Enemy ATK-{value} for 3 turns."
            self.debuff_turns_remaining = 3

        self.phase = Phase.PLAYER_ATTACK
        self.phase_timer = 0.6

    def _clear_enemy_debuffs(self):
        """Restore enemy stats from debuffs."""
        self.enemy.attack = self._enemy_base_attack
        self.enemy.defense = self._enemy_base_defense
        self.enemy_atk_debuff = 0
        self.enemy_def_debuff = 0
        self.debuff_turns_remaining = 0

    def _use_combat_item(self, item_name):
        item = ITEM_REGISTRY.get(item_name)
        if not item:
            return

        self.inventory.remove(item_name)
        self.defending = False

        if item.effect_type == "heal":
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
                self._handle_enemy_defeated()
                return
        elif item.effect_type == "buff_defense":
            self.defense_buff += item.effect_value
            self.player.defense += item.effect_value
            self.message = f"Used {item_name}! Defense +{item.effect_value}."

        self.phase = Phase.PLAYER_ATTACK
        self.phase_timer = 0.6

    def _do_enemy_attack(self):
        # Hit/miss check for enemy (include equipment dex bonus)
        hit_chance = calc_hit_chance(self.enemy_data.dexterity, self.player_stats.dexterity + self._eq_dex_bonus)
        if random.random() > hit_chance:
            self.message = f"{self.enemy.name} missed!"
            self.defending = False
            self.phase = Phase.ENEMY_ATTACK
            self.phase_timer = 0.6
            return

        raw_damage = max(1, self.enemy.attack - self.player.defense + random.randint(-1, 1))
        damage = max(1, raw_damage // 2) if self.defending else raw_damage
        self.player.hp = max(0, self.player.hp - damage)
        self.game.audio.play_sfx("hit")
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
        # Sync HP back to overworld stats (subtract equipment max_hp bonus from combat HP)
        self.overworld.stats.current_hp = min(
            max(1, self.player.hp - self._eq_max_hp_bonus),
            self.overworld.stats.max_hp,
        )
        self.overworld.stats.current_sp = self.player_stats.current_sp

        from bit_flippers.maps import MAP_REGISTRY

        if self.phase == Phase.VICTORY:
            self.overworld.on_combat_victory(enemy_data=self.enemy_data)
            map_def = MAP_REGISTRY[self.overworld.current_map_id]
            self.game.audio.play_music(map_def.music_track)
            self.game.pop_state()
        elif self.phase == Phase.DEFEAT:
            # Apply death penalties: lose half scrap, respawn at half HP
            stats = self.overworld.stats
            lost_scrap = stats.money // 2
            stats.money -= lost_scrap
            stats.current_hp = max(1, stats.max_hp // 2)
            stats.current_sp = stats.max_sp

            self.overworld.on_combat_end()
            map_def = MAP_REGISTRY[self.overworld.current_map_id]
            self.game.audio.play_music(map_def.music_track)
            self.game.pop_state()

            from bit_flippers.states.death_screen import DeathScreenState
            self.game.push_state(DeathScreenState(
                self.game, self.overworld, lost_scrap,
            ))
        else:
            # Fled
            self.overworld.on_combat_end()
            map_def = MAP_REGISTRY[self.overworld.current_map_id]
            self.game.audio.play_music(map_def.music_track)
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
                # Tick down debuffs
                if self.debuff_turns_remaining > 0:
                    self.debuff_turns_remaining -= 1
                    if self.debuff_turns_remaining <= 0:
                        self._clear_enemy_debuffs()

                # SP regen: +1 per turn (cap at combat max_sp including equipment)
                combat_max_sp = self.player_stats.max_sp + self._eq_max_sp_bonus
                self.player_stats.current_sp = min(
                    combat_max_sp, self.player_stats.current_sp + 1
                )

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

        # HP bars — positioned well above the sprite (sprite top is pos[1] - 16)
        hp_bar_y = self.player_pos[1] - TILE_SIZE - 16
        self._draw_hp_bar(screen, self.player, self.player_pos[0] - 10, hp_bar_y, 80)
        self._draw_hp_bar(screen, self.enemy, self.enemy_pos[0] - 10, self.enemy_pos[1] - TILE_SIZE - 16, 80)

        # SP bar for player (right below HP bar: 8px bar + 4px gap)
        sp_y = hp_bar_y + 12
        self._draw_sp_bar(screen, self.player_pos[0] - 10, sp_y, 80)

        # Damage text
        if self.damage_text_timer > 0:
            alpha = min(255, int(self.damage_text_timer * 255))
            dmg_surf = self.font.render(self.damage_text, True, (255, 80, 80))
            dmg_surf.set_alpha(alpha)
            screen.blit(dmg_surf, self.damage_text_pos)

        # Debuff indicator on enemy
        if self.debuff_turns_remaining > 0:
            debuff_parts = []
            if self.enemy_atk_debuff:
                debuff_parts.append(f"ATK-{self.enemy_atk_debuff}")
            if self.enemy_def_debuff:
                debuff_parts.append(f"DEF-{self.enemy_def_debuff}")
            debuff_label = f"{' '.join(debuff_parts)} ({self.debuff_turns_remaining}t)"
            debuff_surf = self.font_small.render(debuff_label, True, (255, 120, 120))
            screen.blit(debuff_surf, (self.enemy_pos[0] - 10, self.enemy_pos[1] + TILE_SIZE * 2 + 5))

        # Message area
        if self.message:
            msg_surf = self.font.render(self.message, True, (220, 220, 220))
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT - 170))

        # Action menu (only during CHOOSING phase)
        if self.phase == Phase.CHOOSING:
            self._draw_menu(screen)
        elif self.phase == Phase.ITEM_SELECT:
            self._draw_menu(screen)
            self._draw_item_submenu(screen)
        elif self.phase == Phase.SKILL_SELECT:
            self._draw_menu(screen)
            self._draw_skill_submenu(screen)
        elif self.phase in (Phase.VICTORY, Phase.DEFEAT, Phase.FLED):
            if self.phase == Phase.VICTORY and (self.reward_xp or self.reward_money):
                reward_y = SCREEN_HEIGHT - 110
                if self.reward_xp:
                    xp_surf = self.font.render(f"+{self.reward_xp} XP", True, (100, 180, 255))
                    screen.blit(xp_surf, (SCREEN_WIDTH // 2 - xp_surf.get_width() // 2, reward_y))
                    reward_y += 28
                if self.reward_money:
                    money_surf = self.font.render(f"+{self.reward_money} Scrap", True, (220, 200, 100))
                    screen.blit(money_surf, (SCREEN_WIDTH // 2 - money_surf.get_width() // 2, reward_y))
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

    def _draw_sp_bar(self, screen, x, y, width):
        """Draw player SP bar in combat."""
        bar_height = 6
        combat_max_sp = self.player_stats.max_sp + self._eq_max_sp_bonus
        ratio = self.player_stats.current_sp / combat_max_sp if combat_max_sp > 0 else 0
        pygame.draw.rect(screen, (40, 40, 40), (x, y, width, bar_height))
        pygame.draw.rect(screen, COLOR_SP_BAR, (x, y, int(width * ratio), bar_height))
        pygame.draw.rect(screen, (140, 140, 140), (x, y, width, bar_height), 1)
        sp_text = self.font_small.render(f"SP {self.player_stats.current_sp}/{combat_max_sp}", True, (180, 200, 255))
        screen.blit(sp_text, (x + width + 4, y - 2))

    def _draw_menu(self, screen):
        menu_x = SCREEN_WIDTH // 2 - 60
        menu_y = SCREEN_HEIGHT - 150
        for i, option in enumerate(MENU_OPTIONS):
            color = (255, 255, 100) if i == self.menu_index else (200, 200, 200)
            prefix = "> " if i == self.menu_index else "  "
            text = self.font.render(f"{prefix}{option}", True, color)
            screen.blit(text, (menu_x, menu_y + i * 28))

    def _draw_item_submenu(self, screen):
        box_x = SCREEN_WIDTH // 2 + 60
        box_y = SCREEN_HEIGHT - 160
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

    def _draw_skill_submenu(self, screen):
        box_x = SCREEN_WIDTH // 2 + 60
        box_y = SCREEN_HEIGHT - 160
        row_h = 24
        padding = 8

        # Background box
        box_h = len(self.skill_list) * row_h + padding * 2
        box_w = 200
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((20, 20, 40, 220))
        screen.blit(bg, (box_x, box_y))
        pygame.draw.rect(screen, (100, 140, 220), (box_x, box_y, box_w, box_h), 1)

        for i, skill_id in enumerate(self.skill_list):
            skill = SKILL_DEFS[skill_id]
            is_sel = i == self.skill_index
            affordable = self.player_stats.current_sp >= skill.sp_cost
            if is_sel:
                color = (255, 220, 100) if affordable else (180, 100, 100)
            else:
                color = (200, 200, 200) if affordable else (100, 100, 100)
            prefix = "> " if is_sel else "  "
            label = f"{prefix}{skill.name} ({skill.sp_cost} SP)"
            text = self.font_small.render(label, True, color)
            screen.blit(text, (box_x + padding, box_y + padding + i * row_h))

        # Hint
        hint = self.font_small.render("[ESC] Cancel", True, (120, 120, 120))
        screen.blit(hint, (box_x, box_y + box_h + 4))
