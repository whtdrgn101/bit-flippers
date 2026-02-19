import random
from enum import Enum, auto

import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, COLOR_SP_BAR,
    COLOR_STATUS_POISON, COLOR_STATUS_STUN, COLOR_STATUS_BURN, COLOR_STATUS_DESPONDENT,
)
from bit_flippers.combat import create_enemy_combatant, CombatEntity, StatusEffect
from bit_flippers.items import ITEM_REGISTRY
from bit_flippers.player_stats import effective_attack, effective_defense, calc_hit_chance, calc_debuff_duration
from bit_flippers.skills import SKILL_DEFS, calc_skill_effect
from bit_flippers.particles import (
    spawn_particles, update_particles, draw_particles,
    get_shake_intensity, shake_offset, SKILL_PARTICLES,
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
            sprite=load_player("pipoya-characters/Male/Male 01-1"),
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

        # Status effect tracking (per-combat)
        self.player_statuses: list[StatusEffect] = []
        self.enemy_statuses: list[StatusEffect] = []
        self.burn_atk_reduction = 0  # track Burn ATK penalty separately

        # Status color lookup
        self._status_colors = {
            "Poison": COLOR_STATUS_POISON,
            "Stun": COLOR_STATUS_STUN,
            "Burn": COLOR_STATUS_BURN,
            "Despondent": COLOR_STATUS_DESPONDENT,
        }

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
            # Hit/miss check (include equipment dex bonus, Despondent penalty)
            player_dex = self.player_stats.dexterity + self._eq_dex_bonus
            if self._has_status(self.player_statuses, "Despondent"):
                player_dex -= 4
            hit_chance = calc_hit_chance(player_dex, self.enemy_data.dexterity)
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
            player_dex = self.player_stats.dexterity + self._eq_dex_bonus
            enemy_dex = self.enemy_data.dexterity
            flee_chance = max(0.20, min(0.80, 0.40 + (player_dex - enemy_dex) * 0.03))
            if random.random() < flee_chance:
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

        self._spawn_skill_particles(skill_id)

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

        elif skill.effect_type == "cure_status":
            if self.burn_atk_reduction > 0:
                self.player.attack += self.burn_atk_reduction
                self.burn_atk_reduction = 0
            self.player_statuses.clear()
            self.message = f"{skill.name}! Status effects cleared."

        self.phase = Phase.PLAYER_ATTACK
        self.phase_timer = 0.6

    def _spawn_skill_particles(self, skill_id):
        """Spawn particles for a skill at the appropriate target position."""
        preset = SKILL_PARTICLES.get(skill_id)
        if not preset:
            return
        target = preset.get("target", "enemy")
        if target == "enemy":
            cx = self.enemy_pos[0] + TILE_SIZE // 2
            cy = self.enemy_pos[1] + TILE_SIZE // 2
            tp = (self.player_pos[0] + TILE_SIZE // 2, self.player_pos[1] + TILE_SIZE // 2)
        else:
            cx = self.player_pos[0] + TILE_SIZE // 2
            cy = self.player_pos[1] + TILE_SIZE // 2
            tp = (self.enemy_pos[0] + TILE_SIZE // 2, self.enemy_pos[1] + TILE_SIZE // 2)
        # For converge (scrap_leech), particles start at enemy and converge on player
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

    def _has_status(self, statuses: list[StatusEffect], name: str) -> bool:
        return any(s.name == name for s in statuses)

    def _apply_status(self, target: str, effect_name: str):
        """Apply a status effect to 'player' or 'enemy'. Refreshes duration if already present."""
        durations = {"Poison": 3, "Stun": 1, "Burn": 3, "Despondent": 3}
        duration = durations.get(effect_name, 3)

        # Constitution reduces debuff duration when applied to the player
        if target == "player":
            duration = calc_debuff_duration(duration, self.player_stats.constitution)

        statuses = self.player_statuses if target == "player" else self.enemy_statuses

        # Refresh if already present
        for s in statuses:
            if s.name == effect_name:
                s.turns_remaining = duration
                return

        statuses.append(StatusEffect(name=effect_name, turns_remaining=duration))

        # Burn: reduce ATK by 2
        if effect_name == "Burn":
            if target == "player":
                self.burn_atk_reduction = 2
                self.player.attack = max(0, self.player.attack - 2)
            else:
                self.enemy.attack = max(0, self.enemy.attack - 2)

    def _tick_statuses(self):
        """Process status effects at end of turn. Returns list of messages."""
        messages = []

        # --- Player statuses ---
        expired_player = []
        for s in self.player_statuses:
            if s.name == "Poison":
                self.player.hp = max(0, self.player.hp - 2)
                messages.append("Poison dealt 2 damage!")
            elif s.name == "Burn":
                self.player.hp = max(0, self.player.hp - 1)
                messages.append("Burn dealt 1 damage!")
            # Stun and Despondent: no tick damage

            s.turns_remaining -= 1
            if s.turns_remaining <= 0:
                expired_player.append(s.name)

        for name in expired_player:
            self.player_statuses = [s for s in self.player_statuses if s.name != name]
            if name == "Burn":
                self.player.attack += self.burn_atk_reduction
                self.burn_atk_reduction = 0
            messages.append(f"{name} wore off!")

        # --- Enemy statuses ---
        expired_enemy = []
        for s in self.enemy_statuses:
            if s.name == "Poison":
                self.enemy.hp = max(0, self.enemy.hp - 2)
                messages.append(f"{self.enemy.name} took 2 poison damage!")
            elif s.name == "Burn":
                self.enemy.hp = max(0, self.enemy.hp - 1)
                messages.append(f"{self.enemy.name} took 1 burn damage!")

            s.turns_remaining -= 1
            if s.turns_remaining <= 0:
                expired_enemy.append(s.name)

        for name in expired_enemy:
            self.enemy_statuses = [s for s in self.enemy_statuses if s.name != name]
            if name == "Burn":
                # Restore the 2 ATK that burn removed (capped at base)
                self.enemy.attack = min(self._enemy_base_attack, self.enemy.attack + 2)
            messages.append(f"{self.enemy.name}'s {name} wore off!")

        return messages

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
        elif item.effect_type == "cure_status":
            # Restore Burn ATK reduction before clearing
            if self.burn_atk_reduction > 0:
                self.player.attack += self.burn_atk_reduction
                self.burn_atk_reduction = 0
            self.player_statuses.clear()
            self.message = f"Used {item_name}! Status effects cleared."

        self.phase = Phase.PLAYER_ATTACK
        self.phase_timer = 0.6

    def _do_enemy_attack(self):
        # Check if enemy is stunned
        if self._has_status(self.enemy_statuses, "Stun"):
            self.enemy_statuses = [s for s in self.enemy_statuses if s.name != "Stun"]
            self.message = f"{self.enemy.name} is stunned and can't move!"
            self.defending = False
            self.phase = Phase.ENEMY_ATTACK
            self.phase_timer = 0.6
            return

        # Check for special ability
        ability = self.enemy_data.ability
        if ability and random.random() < ability["chance"]:
            self._apply_status("player", ability["status_effect"])
            # Deal half normal damage
            half_damage = max(1, (self.enemy.attack - self.player.defense + random.randint(-1, 1)) // 2)
            if self.defending:
                half_damage = max(1, half_damage // 2)
            self.player.hp = max(0, self.player.hp - half_damage)
            self.game.audio.play_sfx("hit")
            self.flash_target = "player"
            self.flash_timer = 0.3
            self.damage_text = f"-{half_damage}"
            self.damage_text_timer = 1.0
            self.damage_text_pos = (self.player_pos[0] + TILE_SIZE // 2, self.player_pos[1] - 10)
            self.message = f"{ability['name']}! {ability['status_effect']} inflicted! -{half_damage} HP"
            self.defending = False

            if not self.player.is_alive:
                self.phase = Phase.DEFEAT
                self.message = "You were defeated..."
                self.message_timer = 0.0
            else:
                self.phase = Phase.ENEMY_ATTACK
                self.phase_timer = 0.6
            return

        # Normal attack — hit/miss check (include equipment dex bonus)
        player_dex = self.player_stats.dexterity + self._eq_dex_bonus
        if self._has_status(self.player_statuses, "Despondent"):
            player_dex -= 4
        hit_chance = calc_hit_chance(self.enemy_data.dexterity, player_dex)
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
        from bit_flippers.states.transition import FadeTransition

        # Remove temporary defense buff before syncing
        self.player.defense -= self.defense_buff
        # Remove Burn ATK reduction before syncing
        if self.burn_atk_reduction > 0:
            self.player.attack += self.burn_atk_reduction
            self.burn_atk_reduction = 0
        # Clear all status effects so nothing lingers
        self.player_statuses.clear()
        self.enemy_statuses.clear()
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
                status_msgs = self._tick_statuses()

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
                if self._has_status(self.player_statuses, "Stun"):
                    self.player_statuses = [s for s in self.player_statuses if s.name != "Stun"]
                    self.message = "You are stunned and can't move!"
                    self.defending = False
                    # Go straight to enemy attack after a brief pause
                    self.phase = Phase.PLAYER_ATTACK
                    self.phase_timer = 0.6
                else:
                    self.phase = Phase.CHOOSING

    def draw(self, screen):
        # Dark background (full screen combat replaces overworld visually)
        screen.fill((15, 10, 25))

        # Screen shake offset
        sx, sy = shake_offset(self.shake_intensity, self.shake_timer)

        # Title
        title = self.font_big.render(f"VS  {self.enemy.name}", True, (255, 200, 100))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2 + sx, 20 + sy))

        # Draw combatants (scaled up 2x for visibility)
        self._draw_combatant(screen, self.player, (self.player_pos[0] + sx, self.player_pos[1] + sy), "player")
        self._draw_combatant(screen, self.enemy, (self.enemy_pos[0] + sx, self.enemy_pos[1] + sy), "enemy")

        # Draw particles (after combatants, before UI)
        draw_particles(screen, self.particles)

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

        # Debuff indicator on enemy (skill-based)
        if self.debuff_turns_remaining > 0:
            debuff_parts = []
            if self.enemy_atk_debuff:
                debuff_parts.append(f"ATK-{self.enemy_atk_debuff}")
            if self.enemy_def_debuff:
                debuff_parts.append(f"DEF-{self.enemy_def_debuff}")
            debuff_label = f"{' '.join(debuff_parts)} ({self.debuff_turns_remaining}t)"
            debuff_surf = self.font_small.render(debuff_label, True, (255, 120, 120))
            screen.blit(debuff_surf, (self.enemy_pos[0] - 10, self.enemy_pos[1] + TILE_SIZE * 2 + 5))

        # Status effect indicators on player
        status_y = self.player_pos[1] + TILE_SIZE * 2 + 5
        for s in self.player_statuses:
            color = self._status_colors.get(s.name, (200, 200, 200))
            label = f"{s.name} ({s.turns_remaining}t)"
            surf = self.font_small.render(label, True, color)
            screen.blit(surf, (self.player_pos[0] - 10, status_y))
            status_y += 16

        # Status effect indicators on enemy
        enemy_status_y = self.enemy_pos[1] + TILE_SIZE * 2 + 5
        if self.debuff_turns_remaining > 0:
            enemy_status_y += 16  # offset below skill debuff indicator
        for s in self.enemy_statuses:
            color = self._status_colors.get(s.name, (200, 200, 200))
            label = f"{s.name} ({s.turns_remaining}t)"
            surf = self.font_small.render(label, True, color)
            screen.blit(surf, (self.enemy_pos[0] - 10, enemy_status_y))
            enemy_status_y += 16

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
        iw, ih = img.get_size()
        # If the sprite is already large (e.g. Pipoya monster 64x64+), use as-is; otherwise 2x
        if iw >= TILE_SIZE * 2 or ih >= TILE_SIZE * 2:
            scaled = img
        else:
            scaled = pygame.transform.scale(img, (iw * 2, ih * 2))
        sw, sh = scaled.get_size()

        # Center the sprite on the position
        draw_x = pos[0] - sw // 2 + TILE_SIZE // 2
        draw_y = pos[1] - sh // 2 + TILE_SIZE // 2

        # Flash effect on hit
        if self.flash_timer > 0 and self.flash_target == who:
            flash_surf = scaled.copy()
            flash_surf.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(flash_surf, (draw_x, draw_y))
        else:
            screen.blit(scaled, (draw_x, draw_y))

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
