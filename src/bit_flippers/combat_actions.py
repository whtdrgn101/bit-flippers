"""Pure combat action resolution — extracted from CombatState.

Each resolve_* function computes what happens for an action and returns an
ActionResult.  CombatState applies the result to its UI state (flash timers,
damage text, phase transitions).
"""

from __future__ import annotations

import random
from copy import copy
from dataclasses import dataclass, field

from bit_flippers.items import ITEM_REGISTRY
from bit_flippers.player_stats import calc_hit_chance
from bit_flippers.skills import SKILL_DEFS, calc_skill_effect


@dataclass
class ActionResult:
    damage: int = 0
    heal: int = 0
    message: str = ""
    hit: bool = True
    target_killed: bool = False
    flash_target: str | None = None  # "player" or "enemy"
    buff_defense: int = 0
    debuff_attack: int = 0
    debuff_defense: int = 0
    debuff_turns: int = 0
    status_cured: bool = False
    skill_particles: str | None = None  # skill_id for particle spawning
    sp_cost: int = 0
    fled: bool = False
    defending: bool = False
    # Status effect application (enemy ability)
    apply_status: str | None = None
    apply_status_target: str | None = None


def resolve_attack(player_stats, player_entity, enemy_entity, enemy_data,
                   eq_dex_bonus: int, status_mgr) -> ActionResult:
    """Resolve a player basic attack."""
    result = ActionResult()

    player_dex = player_stats.dexterity + eq_dex_bonus
    if status_mgr.has_status("player", "Despondent"):
        player_dex -= 4
    hit_chance = calc_hit_chance(player_dex, enemy_data.dexterity)

    if random.random() > hit_chance:
        result.hit = False
        result.message = "Attack missed!"
        return result

    damage = max(1, player_entity.attack - enemy_entity.defense + random.randint(-1, 1))
    result.damage = damage
    result.flash_target = "enemy"
    result.message = f"-{damage}"
    result.target_killed = (enemy_entity.hp - damage) <= 0
    return result


def resolve_skill(skill_id: str, player_stats, player_entity, enemy_entity,
                  eq_int_bonus: int) -> ActionResult:
    """Resolve a player skill use."""
    skill = SKILL_DEFS.get(skill_id)
    if not skill:
        return ActionResult(message="Unknown skill!")

    result = ActionResult()
    result.sp_cost = skill.sp_cost
    result.skill_particles = skill_id

    # Calculate scaled value with equipment INT bonus
    combat_stats = copy(player_stats)
    combat_stats.intelligence += eq_int_bonus
    value = calc_skill_effect(skill, combat_stats)

    if skill.effect_type == "damage":
        result.damage = value
        result.flash_target = "enemy"
        result.message = f"{skill.name}! Dealt {value} damage."
        result.target_killed = (enemy_entity.hp - value) <= 0

    elif skill.effect_type == "heal":
        actual_heal = min(player_entity.max_hp - player_entity.hp, value)
        result.heal = actual_heal
        result.message = f"{skill.name}! Restored {actual_heal} HP."

    elif skill.effect_type == "buff_defense":
        result.buff_defense = value
        result.message = f"{skill.name}! Defense +{value}."

    elif skill.effect_type == "drain":
        result.damage = value
        actual_heal = min(player_entity.max_hp - player_entity.hp, value)
        result.heal = actual_heal
        result.flash_target = "enemy"
        result.message = f"{skill.name}! Drained {value}, healed {actual_heal}."
        result.target_killed = (enemy_entity.hp - value) <= 0

    elif skill.effect_type == "debuff_attack":
        result.debuff_attack = value
        if skill.skill_id == "emp_pulse":
            result.debuff_defense = value
            result.message = f"{skill.name}! Enemy ATK-{value}, DEF-{value} for 3 turns."
        else:
            result.message = f"{skill.name}! Enemy ATK-{value} for 3 turns."
        result.debuff_turns = 3

    elif skill.effect_type == "cure_status":
        result.status_cured = True
        result.message = f"{skill.name}! Status effects cleared."

    return result


def resolve_item(item_name: str, player_entity, enemy_entity) -> ActionResult:
    """Resolve a combat item use."""
    item = ITEM_REGISTRY.get(item_name)
    if not item:
        return ActionResult(message="Unknown item!")

    result = ActionResult()

    if item.effect_type == "heal":
        old_hp = player_entity.hp
        potential = min(player_entity.max_hp, player_entity.hp + item.effect_value)
        result.heal = potential - old_hp
        result.message = f"Used {item_name}! Restored {result.heal} HP."

    elif item.effect_type == "damage":
        result.damage = item.effect_value
        result.flash_target = "enemy"
        result.message = f"Used {item_name}! Dealt {item.effect_value} damage."
        result.target_killed = (enemy_entity.hp - item.effect_value) <= 0

    elif item.effect_type == "buff_defense":
        result.buff_defense = item.effect_value
        result.message = f"Used {item_name}! Defense +{item.effect_value}."

    elif item.effect_type == "cure_status":
        result.status_cured = True
        result.message = f"Used {item_name}! Status effects cleared."

    return result


def resolve_enemy_turn(enemy_data, enemy_entity, player_entity, player_stats,
                       eq_dex_bonus: int, status_mgr, defending: bool) -> ActionResult:
    """Resolve the enemy's turn (ability or normal attack)."""
    result = ActionResult()

    # Check if enemy is stunned
    if status_mgr.remove_enemy_stun():
        result.message = f"{enemy_entity.name} is stunned and can't move!"
        return result

    # Check for special ability
    ability = enemy_data.ability
    if ability and random.random() < ability["chance"]:
        result.apply_status = ability["status_effect"]
        result.apply_status_target = "player"

        half_damage = max(1, (enemy_entity.attack - player_entity.defense + random.randint(-1, 1)) // 2)
        if defending:
            half_damage = max(1, half_damage // 2)
        result.damage = half_damage
        result.flash_target = "player"
        result.message = f"{ability['name']}! {ability['status_effect']} inflicted! -{half_damage} HP"
        result.target_killed = (player_entity.hp - half_damage) <= 0
        return result

    # Normal attack — hit/miss check
    player_dex = player_stats.dexterity + eq_dex_bonus
    if status_mgr.has_status("player", "Despondent"):
        player_dex -= 4
    hit_chance = calc_hit_chance(enemy_data.dexterity, player_dex)

    if random.random() > hit_chance:
        result.hit = False
        result.message = f"{enemy_entity.name} missed!"
        return result

    raw_damage = max(1, enemy_entity.attack - player_entity.defense + random.randint(-1, 1))
    damage = max(1, raw_damage // 2) if defending else raw_damage
    result.damage = damage
    result.flash_target = "player"
    result.target_killed = (player_entity.hp - damage) <= 0
    return result


def resolve_flee(player_stats, enemy_data, eq_dex_bonus: int) -> ActionResult:
    """Resolve a flee attempt."""
    result = ActionResult()
    player_dex = player_stats.dexterity + eq_dex_bonus
    enemy_dex = enemy_data.dexterity
    flee_chance = max(0.20, min(0.80, 0.40 + (player_dex - enemy_dex) * 0.03))

    if random.random() < flee_chance:
        result.fled = True
        result.message = "Got away safely!"
    else:
        result.message = "Couldn't escape!"

    return result
