from enum import Enum, auto

import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from bit_flippers.combat import create_enemy_combatant, CombatEntity
from bit_flippers.player_stats import effective_attack, effective_defense
from bit_flippers.skills import SKILL_DEFS
from bit_flippers.particles import (
    spawn_particles, update_particles,
    get_shake_intensity, SKILL_PARTICLES,
)
from bit_flippers.status_effects import StatusEffectManager
from bit_flippers.states.combat_renderer import CombatRenderer
from bit_flippers.combat_actions import (
    resolve_attack, resolve_skill, resolve_item,
    resolve_enemy_turn, resolve_flee,
)


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
            sprite=load_player(getattr(overworld, "player_sprite_key", "pipoya-characters/Male/Male 01-1")),
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

        # Status effect manager
        self.status_mgr = StatusEffectManager()

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

        # Particle system
        self.particles = []
        self.shake_timer = 0.0
        self.shake_intensity = 0.0

        # Fonts
        self.font = get_font(28)
        self.font_big = get_font(36)
        self.font_small = get_font(22)

        # Layout positions — sprites in upper third, leaving room for 5-item menu
        self.player_pos = (SCREEN_WIDTH // 4 - TILE_SIZE, SCREEN_HEIGHT // 3)
        self.enemy_pos = (3 * SCREEN_WIDTH // 4 - TILE_SIZE, SCREEN_HEIGHT // 3)

        # Renderer
        self.renderer = CombatRenderer(self.font, self.font_big, self.font_small)

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

    # ------------------------------------------------------------------
    # Action helpers
    # ------------------------------------------------------------------

    def _apply_damage_to_enemy(self, result):
        """Apply damage from an ActionResult to the enemy, set UI state."""
        if result.damage > 0:
            self.enemy.hp = max(0, self.enemy.hp - result.damage)
            self.game.audio.play_sfx("hit")
        if result.flash_target == "enemy":
            self.flash_target = "enemy"
            self.flash_timer = 0.3
            self.damage_text = f"-{result.damage}"
            self.damage_text_timer = 1.0
            self.damage_text_pos = (self.enemy_pos[0] + TILE_SIZE // 2, self.enemy_pos[1] - 10)
        if result.heal > 0:
            self.player.hp = min(self.player.max_hp, self.player.hp + result.heal)

    def _apply_damage_to_player(self, result):
        """Apply damage from an ActionResult to the player, set UI state."""
        if result.damage > 0:
            self.player.hp = max(0, self.player.hp - result.damage)
            self.game.audio.play_sfx("hit")
        if result.flash_target == "player":
            self.flash_target = "player"
            self.flash_timer = 0.3
            self.damage_text = f"-{result.damage}"
            self.damage_text_timer = 1.0
            self.damage_text_pos = (self.player_pos[0] + TILE_SIZE // 2, self.player_pos[1] - 10)

    def _handle_enemy_defeated(self):
        """Shared victory logic for any action that kills the enemy."""
        self.phase = Phase.VICTORY
        self.message = f"Defeated {self.enemy.name}!"
        self.reward_xp = self.enemy_data.xp_reward
        self.reward_money = self.enemy_data.money_reward
        self.message_timer = 0.0
        self.game.audio.stop_music()
        self.game.audio.play_sfx("victory")

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------

    def _execute_player_action(self, action):
        if action == "Attack":
            result = resolve_attack(
                self.player_stats, self.player, self.enemy, self.enemy_data,
                self._eq_dex_bonus, self.status_mgr,
            )
            self.defending = False
            self.message = result.message

            if not result.hit:
                self.phase = Phase.PLAYER_ATTACK
                self.phase_timer = 0.6
                return

            self._apply_damage_to_enemy(result)
            if result.target_killed:
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
            result = resolve_flee(self.player_stats, self.enemy_data, self._eq_dex_bonus)
            self.message = result.message
            if result.fled:
                self.phase = Phase.FLED
                self.message_timer = 0.0
            else:
                self.phase = Phase.PLAYER_ATTACK
                self.phase_timer = 0.6

    def _use_combat_skill(self, skill_id):
        skill = SKILL_DEFS.get(skill_id)
        if not skill:
            return

        if self.player_stats.current_sp < skill.sp_cost:
            self.message = "Not enough SP!"
            return

        result = resolve_skill(
            skill_id, self.player_stats, self.player, self.enemy,
            self._eq_int_bonus,
        )

        # Deduct SP
        self.player_stats.current_sp -= result.sp_cost
        self.defending = False

        # Spawn particles
        if result.skill_particles:
            self._spawn_skill_particles(result.skill_particles)

        # Apply result
        self.message = result.message

        if result.damage > 0:
            self._apply_damage_to_enemy(result)
            if result.target_killed:
                self._handle_enemy_defeated()
                return

        if result.heal > 0 and result.damage == 0:
            self.player.hp = min(self.player.max_hp, self.player.hp + result.heal)

        if result.buff_defense > 0:
            self.defense_buff += result.buff_defense
            self.player.defense += result.buff_defense

        if result.debuff_attack > 0:
            self._clear_enemy_debuffs()
            self.enemy_atk_debuff = result.debuff_attack
            self.enemy.attack = max(0, self._enemy_base_attack - result.debuff_attack)
            if result.debuff_defense > 0:
                self.enemy_def_debuff = result.debuff_defense
                self.enemy.defense = max(0, self._enemy_base_defense - result.debuff_defense)
            self.debuff_turns_remaining = result.debuff_turns

        if result.status_cured:
            self.status_mgr.cure_player(self.player)

        self.phase = Phase.PLAYER_ATTACK
        self.phase_timer = 0.6

    def _use_combat_item(self, item_name):
        result = resolve_item(item_name, self.player, self.enemy)
        self.inventory.remove(item_name)
        self.defending = False
        self.message = result.message

        if result.damage > 0:
            self._apply_damage_to_enemy(result)
            if result.target_killed:
                self._handle_enemy_defeated()
                return

        if result.heal > 0:
            self.player.hp = min(self.player.max_hp, self.player.hp + result.heal)

        if result.buff_defense > 0:
            self.defense_buff += result.buff_defense
            self.player.defense += result.buff_defense

        if result.status_cured:
            self.status_mgr.cure_player(self.player)

        self.phase = Phase.PLAYER_ATTACK
        self.phase_timer = 0.6

    # ------------------------------------------------------------------
    # Enemy turn
    # ------------------------------------------------------------------

    def _do_enemy_attack(self):
        result = resolve_enemy_turn(
            self.enemy_data, self.enemy, self.player, self.player_stats,
            self._eq_dex_bonus, self.status_mgr, self.defending,
        )
        self.defending = False
        self.message = result.message

        # Apply status effect if the enemy used an ability
        if result.apply_status:
            self.status_mgr.apply_status(
                result.apply_status_target, result.apply_status,
                constitution=self.player_stats.constitution,
                player_entity=self.player, enemy_entity=self.enemy,
            )

        if result.damage > 0:
            self._apply_damage_to_player(result)

        if result.target_killed:
            self.phase = Phase.DEFEAT
            self.message = "You were defeated..."
            self.message_timer = 0.0
        elif not result.hit or result.damage > 0 or result.apply_status:
            self.phase = Phase.ENEMY_ATTACK
            self.phase_timer = 0.6
        else:
            # Stunned — no damage, just message
            self.phase = Phase.ENEMY_ATTACK
            self.phase_timer = 0.6

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _spawn_skill_particles(self, skill_id):
        """Spawn particles for a skill at the appropriate target position."""
        preset = SKILL_PARTICLES.get(skill_id)
        if not preset:
            return
        target = preset.get("target", "enemy")
        if target == "enemy":
            cx = self.enemy_pos[0] + TILE_SIZE // 2
            cy = self.enemy_pos[1] + TILE_SIZE // 2
        else:
            cx = self.player_pos[0] + TILE_SIZE // 2
            cy = self.player_pos[1] + TILE_SIZE // 2
        if preset.get("pattern") == "converge":
            self.particles.extend(spawn_particles(
                self.enemy_pos[0] + TILE_SIZE // 2,
                self.enemy_pos[1] + TILE_SIZE // 2,
                skill_id,
                target_pos=(self.player_pos[0] + TILE_SIZE // 2, self.player_pos[1] + TILE_SIZE // 2),
            ))
        else:
            self.particles.extend(spawn_particles(cx, cy, skill_id))
        shake = get_shake_intensity(skill_id)
        if shake > 0:
            self.shake_intensity = shake
            self.shake_timer = 0.4

    def _clear_enemy_debuffs(self):
        """Restore enemy stats from debuffs."""
        self.enemy.attack = self._enemy_base_attack
        self.enemy.defense = self._enemy_base_defense
        self.enemy_atk_debuff = 0
        self.enemy_def_debuff = 0
        self.debuff_turns_remaining = 0

    def _finish_combat(self):
        from bit_flippers.states.transition import FadeTransition

        # Remove temporary defense buff before syncing
        self.player.defense -= self.defense_buff
        # Clear all status effects (restores Burn ATK reduction)
        self.status_mgr.clear_all(self.player)
        # Sync HP back to overworld stats (subtract equipment max_hp bonus from combat HP)
        self.overworld.stats.current_hp = min(
            max(1, self.player.hp - self._eq_max_hp_bonus),
            self.overworld.stats.max_hp,
        )
        self.overworld.stats.current_sp = self.player_stats.current_sp

        phase = self.phase
        overworld = self.overworld
        enemy_data = self.enemy_data
        game = self.game
        combat_state = self  # capture reference to remove from stack

        if phase == Phase.VICTORY:
            def _on_fade():
                overworld.on_combat_victory(enemy_data=enemy_data)
                if combat_state in game.state_stack:
                    game.state_stack.remove(combat_state)
            game.push_state(FadeTransition(game, _on_fade))
        elif phase == Phase.DEFEAT:
            # Apply death penalties: lose 30% scrap, respawn at 60% HP
            stats = overworld.stats
            lost_scrap = int(stats.money * 0.30)
            stats.money -= lost_scrap
            stats.current_hp = max(1, int(stats.max_hp * 0.60))
            stats.current_sp = stats.max_sp

            def _on_fade():
                overworld.on_combat_end()
                if combat_state in game.state_stack:
                    game.state_stack.remove(combat_state)
                from bit_flippers.states.death_screen import DeathScreenState
                game.push_state(DeathScreenState(game, overworld, lost_scrap))
            game.push_state(FadeTransition(game, _on_fade))
        else:
            # Fled
            def _on_fade():
                overworld.on_combat_end()
                if combat_state in game.state_stack:
                    game.state_stack.remove(combat_state)
            game.push_state(FadeTransition(game, _on_fade))

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
        if self.shake_timer > 0:
            self.shake_timer -= dt

        # Update particles
        self.particles = update_particles(self.particles, dt)

        # Phase transitions
        if self.phase == Phase.PLAYER_ATTACK:
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                self._do_enemy_attack()
        elif self.phase == Phase.ENEMY_ATTACK:
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                # Tick down skill debuffs
                if self.debuff_turns_remaining > 0:
                    self.debuff_turns_remaining -= 1
                    if self.debuff_turns_remaining <= 0:
                        self._clear_enemy_debuffs()

                # Tick status effects (DoT, expiry)
                status_msgs = self.status_mgr.tick(
                    self.player, self.enemy, self._enemy_base_attack,
                )

                # Check for DoT deaths
                if not self.enemy.is_alive:
                    self._handle_enemy_defeated()
                    return
                if not self.player.is_alive:
                    self.phase = Phase.DEFEAT
                    self.message = "You were defeated..."
                    self.message_timer = 0.0
                    return

                # SP regen: base 1 + INT bonus per turn
                intel = self.player_stats.intelligence + self._eq_int_bonus
                sp_regen = 1 + max(0, (intel - 3) // 3)
                combat_max_sp = self.player_stats.max_sp + self._eq_max_sp_bonus
                self.player_stats.current_sp = min(
                    combat_max_sp, self.player_stats.current_sp + sp_regen
                )

                # Show status tick messages if any
                if status_msgs:
                    self.message = " ".join(status_msgs)
                else:
                    self.message = ""

                # Check for player stun — skip CHOOSING phase
                if self.status_mgr.remove_player_stun():
                    self.message = "You are stunned and can't move!"
                    self.defending = False
                    self.phase = Phase.PLAYER_ATTACK
                    self.phase_timer = 0.6
                else:
                    self.phase = Phase.CHOOSING

    def draw(self, screen):
        self.renderer.draw(screen, self)
