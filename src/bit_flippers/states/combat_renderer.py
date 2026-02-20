"""Combat screen rendering — extracted from CombatState for clarity."""

import pygame
from bit_flippers.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, COLOR_SP_BAR,
    COLOR_STATUS_POISON, COLOR_STATUS_STUN, COLOR_STATUS_BURN, COLOR_STATUS_DESPONDENT,
)
from bit_flippers.skills import SKILL_DEFS
from bit_flippers.particles import draw_particles, shake_offset


# Status color lookup (shared constant)
STATUS_COLORS = {
    "Poison": COLOR_STATUS_POISON,
    "Stun": COLOR_STATUS_STUN,
    "Burn": COLOR_STATUS_BURN,
    "Despondent": COLOR_STATUS_DESPONDENT,
}


class CombatRenderer:
    """Handles all drawing for the combat screen."""

    def __init__(self, font, font_big, font_small):
        self.font = font
        self.font_big = font_big
        self.font_small = font_small

    def draw(self, screen, combat):
        """Draw the full combat screen."""
        from bit_flippers.states.combat import Phase, MENU_OPTIONS

        screen.fill((15, 10, 25))

        # Screen shake offset
        sx, sy = shake_offset(combat.shake_intensity, combat.shake_timer)

        # Title
        title = self.font_big.render(f"VS  {combat.enemy.name}", True, (255, 200, 100))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2 + sx, 20 + sy))

        # Draw combatants (scaled up 2x for visibility)
        self._draw_combatant(screen, combat.player, (combat.player_pos[0] + sx, combat.player_pos[1] + sy), "player", combat)
        self._draw_combatant(screen, combat.enemy, (combat.enemy_pos[0] + sx, combat.enemy_pos[1] + sy), "enemy", combat)

        # Draw particles (after combatants, before UI)
        draw_particles(screen, combat.particles)

        # HP bars
        hp_bar_y = combat.player_pos[1] - TILE_SIZE - 16
        self._draw_hp_bar(screen, combat.player, combat.player_pos[0] - 10, hp_bar_y, 80)
        self._draw_hp_bar(screen, combat.enemy, combat.enemy_pos[0] - 10, combat.enemy_pos[1] - TILE_SIZE - 16, 80)

        # SP bar for player (right below HP bar)
        sp_y = hp_bar_y + 12
        self._draw_sp_bar(screen, combat.player_pos[0] - 10, sp_y, 80, combat.player_stats, combat._eq_max_sp_bonus)

        # Damage text
        if combat.damage_text_timer > 0:
            alpha = min(255, int(combat.damage_text_timer * 255))
            dmg_surf = self.font.render(combat.damage_text, True, (255, 80, 80))
            dmg_surf.set_alpha(alpha)
            screen.blit(dmg_surf, combat.damage_text_pos)

        # Debuff indicator on enemy (skill-based)
        if combat.debuff_turns_remaining > 0:
            debuff_parts = []
            if combat.enemy_atk_debuff:
                debuff_parts.append(f"ATK-{combat.enemy_atk_debuff}")
            if combat.enemy_def_debuff:
                debuff_parts.append(f"DEF-{combat.enemy_def_debuff}")
            debuff_label = f"{' '.join(debuff_parts)} ({combat.debuff_turns_remaining}t)"
            debuff_surf = self.font_small.render(debuff_label, True, (255, 120, 120))
            screen.blit(debuff_surf, (combat.enemy_pos[0] - 10, combat.enemy_pos[1] + TILE_SIZE * 2 + 5))

        # Status effect indicators on player
        status_y = combat.player_pos[1] + TILE_SIZE * 2 + 5
        for s in combat.status_mgr.player_statuses:
            color = STATUS_COLORS.get(s.name, (200, 200, 200))
            label = f"{s.name} ({s.turns_remaining}t)"
            surf = self.font_small.render(label, True, color)
            screen.blit(surf, (combat.player_pos[0] - 10, status_y))
            status_y += 16

        # Status effect indicators on enemy
        enemy_status_y = combat.enemy_pos[1] + TILE_SIZE * 2 + 5
        if combat.debuff_turns_remaining > 0:
            enemy_status_y += 16
        for s in combat.status_mgr.enemy_statuses:
            color = STATUS_COLORS.get(s.name, (200, 200, 200))
            label = f"{s.name} ({s.turns_remaining}t)"
            surf = self.font_small.render(label, True, color)
            screen.blit(surf, (combat.enemy_pos[0] - 10, enemy_status_y))
            enemy_status_y += 16

        # Message area
        if combat.message:
            msg_surf = self.font.render(combat.message, True, (220, 220, 220))
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT - 170))

        # Action menu / victory / defeat
        if combat.phase == Phase.CHOOSING:
            self._draw_menu(screen, combat.menu_index)
        elif combat.phase == Phase.ITEM_SELECT:
            self._draw_menu(screen, combat.menu_index)
            self._draw_item_submenu(screen, combat.item_list, combat.item_index, combat.inventory)
        elif combat.phase == Phase.SKILL_SELECT:
            self._draw_menu(screen, combat.menu_index)
            self._draw_skill_submenu(screen, combat.skill_list, combat.skill_index, combat.player_stats)
        elif combat.phase in (Phase.VICTORY, Phase.DEFEAT, Phase.FLED):
            if combat.phase == Phase.VICTORY and (combat.reward_xp or combat.reward_money):
                reward_y = SCREEN_HEIGHT - 110
                if combat.reward_xp:
                    xp_surf = self.font.render(f"+{combat.reward_xp} XP", True, (100, 180, 255))
                    screen.blit(xp_surf, (SCREEN_WIDTH // 2 - xp_surf.get_width() // 2, reward_y))
                    reward_y += 28
                if combat.reward_money:
                    money_surf = self.font.render(f"+{combat.reward_money} Scrap", True, (220, 200, 100))
                    screen.blit(money_surf, (SCREEN_WIDTH // 2 - money_surf.get_width() // 2, reward_y))
            prompt = self.font_small.render("[SPACE to continue]", True, (180, 180, 180))
            screen.blit(
                prompt,
                (SCREEN_WIDTH // 2 - prompt.get_width() // 2, SCREEN_HEIGHT - 40),
            )

    def _draw_combatant(self, screen, entity, pos, who, combat):
        img = entity.sprite.image
        iw, ih = img.get_size()
        if iw >= TILE_SIZE * 2 or ih >= TILE_SIZE * 2:
            scaled = img
        else:
            scaled = pygame.transform.scale(img, (iw * 2, ih * 2))
        sw, sh = scaled.get_size()

        draw_x = pos[0] - sw // 2 + TILE_SIZE // 2
        draw_y = pos[1] - sh // 2 + TILE_SIZE // 2

        if combat.flash_timer > 0 and combat.flash_target == who:
            flash_surf = scaled.copy()
            flash_surf.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(flash_surf, (draw_x, draw_y))
        else:
            screen.blit(scaled, (draw_x, draw_y))

    def _draw_hp_bar(self, screen, entity, x, y, width):
        bar_height = 8
        ratio = entity.hp / entity.max_hp if entity.max_hp > 0 else 0

        pygame.draw.rect(screen, (60, 60, 60), (x, y, width, bar_height))
        color = (80, 200, 80) if ratio > 0.5 else (200, 200, 40) if ratio > 0.25 else (200, 60, 60)
        pygame.draw.rect(screen, color, (x, y, int(width * ratio), bar_height))
        pygame.draw.rect(screen, (180, 180, 180), (x, y, width, bar_height), 1)

        hp_text = self.font_small.render(f"{entity.hp}/{entity.max_hp}", True, (255, 255, 255))
        screen.blit(hp_text, (x, y - 16))
        name_text = self.font_small.render(entity.name, True, (255, 255, 255))
        screen.blit(name_text, (x, y - 32))

    def _draw_sp_bar(self, screen, x, y, width, player_stats, eq_max_sp_bonus):
        bar_height = 6
        combat_max_sp = player_stats.max_sp + eq_max_sp_bonus
        ratio = player_stats.current_sp / combat_max_sp if combat_max_sp > 0 else 0
        pygame.draw.rect(screen, (40, 40, 40), (x, y, width, bar_height))
        pygame.draw.rect(screen, COLOR_SP_BAR, (x, y, int(width * ratio), bar_height))
        pygame.draw.rect(screen, (140, 140, 140), (x, y, width, bar_height), 1)
        sp_text = self.font_small.render(f"SP {player_stats.current_sp}/{combat_max_sp}", True, (180, 200, 255))
        screen.blit(sp_text, (x + width + 4, y - 2))

    def _draw_menu(self, screen, menu_index):
        from bit_flippers.states.combat import MENU_OPTIONS
        menu_x = SCREEN_WIDTH // 2 - 60
        menu_y = SCREEN_HEIGHT - 150
        for i, option in enumerate(MENU_OPTIONS):
            color = (255, 255, 100) if i == menu_index else (200, 200, 200)
            prefix = "> " if i == menu_index else "  "
            text = self.font.render(f"{prefix}{option}", True, color)
            screen.blit(text, (menu_x, menu_y + i * 28))

    def _draw_item_submenu(self, screen, item_list, item_index, inventory):
        box_x = SCREEN_WIDTH // 2 + 60
        box_y = SCREEN_HEIGHT - 160
        row_h = 24
        padding = 8

        box_h = len(item_list) * row_h + padding * 2
        box_w = 180
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((20, 20, 40, 220))
        screen.blit(bg, (box_x, box_y))
        pygame.draw.rect(screen, (180, 180, 180), (box_x, box_y, box_w, box_h), 1)

        for i, name in enumerate(item_list):
            count = inventory.get_count(name)
            is_sel = i == item_index
            color = (255, 220, 100) if is_sel else (200, 200, 200)
            prefix = "> " if is_sel else "  "
            label = f"{prefix}{name} x{count}"
            text = self.font_small.render(label, True, color)
            screen.blit(text, (box_x + padding, box_y + padding + i * row_h))

        hint = self.font_small.render("[ESC] Cancel", True, (120, 120, 120))
        screen.blit(hint, (box_x, box_y + box_h + 4))

    def _draw_skill_submenu(self, screen, skill_list, skill_index, player_stats):
        box_x = SCREEN_WIDTH // 2 + 60
        box_y = SCREEN_HEIGHT - 160
        row_h = 24
        padding = 8

        box_h = len(skill_list) * row_h + padding * 2
        box_w = 200
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((20, 20, 40, 220))
        screen.blit(bg, (box_x, box_y))
        pygame.draw.rect(screen, (100, 140, 220), (box_x, box_y, box_w, box_h), 1)

        for i, skill_id in enumerate(skill_list):
            skill = SKILL_DEFS[skill_id]
            is_sel = i == skill_index
            affordable = player_stats.current_sp >= skill.sp_cost
            if is_sel:
                color = (255, 220, 100) if affordable else (180, 100, 100)
            else:
                color = (200, 200, 200) if affordable else (100, 100, 100)
            prefix = "> " if is_sel else "  "
            label = f"{prefix}{skill.name} ({skill.sp_cost} SP)"
            text = self.font_small.render(label, True, color)
            screen.blit(text, (box_x + padding, box_y + padding + i * row_h))

        hint = self.font_small.render("[ESC] Cancel", True, (120, 120, 120))
        screen.blit(hint, (box_x, box_y + box_h + 4))
