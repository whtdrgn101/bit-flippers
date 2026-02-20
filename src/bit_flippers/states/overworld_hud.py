"""Overworld HUD rendering — extracted from OverworldState for clarity."""

import pygame
from bit_flippers.settings import (
    SCREEN_WIDTH,
    HUD_HEIGHT,
    HUD_Y,
    COLOR_HUD_BG,
    COLOR_HUD_BORDER,
    TILE_SIZE,
    COLOR_XP_BAR,
    COLOR_SP_BAR,
    COLOR_MONEY_TEXT,
)


def draw_icon_markers(screen, markers, camera):
    """Draw branding icons on wall tiles adjacent to shop doors."""
    if not markers:
        return
    for marker in markers:
        world_rect = pygame.Rect(
            marker.x * TILE_SIZE, marker.y * TILE_SIZE, TILE_SIZE, TILE_SIZE
        )
        sr = camera.apply(world_rect)
        cx, cy = sr.centerx, sr.centery
        c = marker.color
        if marker.icon_type == "sword":
            pygame.draw.line(screen, c, (cx, cy - 7), (cx, cy + 7), 2)
            pygame.draw.line(screen, c, (cx - 4, cy - 2), (cx + 4, cy - 2), 2)
            pygame.draw.line(screen, c, (cx - 1, cy + 7), (cx + 1, cy + 7), 2)
        elif marker.icon_type == "shield":
            shield_rect = pygame.Rect(cx - 5, cy - 6, 10, 12)
            pygame.draw.rect(screen, c, shield_rect, 2, border_radius=3)
            pygame.draw.line(screen, c, (cx, cy - 4), (cx, cy + 4), 2)


def draw_hud(screen, stats, player_skills, player_quests, xp_to_next,
             display_name, minimap, minimap_visible, hud_font):
    """Draw the full 3-column HUD panel in the bottom 120px."""
    # Background panel
    pygame.draw.rect(screen, COLOR_HUD_BG, (0, HUD_Y, SCREEN_WIDTH, HUD_HEIGHT))
    pygame.draw.line(screen, COLOR_HUD_BORDER, (0, HUD_Y), (SCREEN_WIDTH, HUD_Y), 2)

    pad = 10
    bar_width, bar_height = 120, 12
    col_left = pad
    col_mid = SCREEN_WIDTH // 3 + pad
    col_right = 2 * SCREEN_WIDTH // 3 + pad

    # --- LEFT COLUMN: Level + HP/SP/XP bars ---
    y = HUD_Y + pad
    level_label = hud_font.render(f"Lv {stats.level}", True, (255, 255, 255))
    screen.blit(level_label, (col_left, y))
    y += 20

    bar_x = col_left + 28
    # HP bar
    hp_ratio = stats.current_hp / stats.max_hp if stats.max_hp > 0 else 0
    hp_label = hud_font.render("HP", True, (255, 255, 255))
    screen.blit(hp_label, (col_left, y))
    pygame.draw.rect(screen, (60, 60, 60), (bar_x, y + 2, bar_width, bar_height))
    hp_color = (80, 200, 80) if hp_ratio > 0.5 else (200, 200, 40) if hp_ratio > 0.25 else (200, 60, 60)
    pygame.draw.rect(screen, hp_color, (bar_x, y + 2, int(bar_width * hp_ratio), bar_height))
    pygame.draw.rect(screen, (180, 180, 180), (bar_x, y + 2, bar_width, bar_height), 1)
    hp_text = hud_font.render(f"{stats.current_hp}/{stats.max_hp}", True, (255, 255, 255))
    screen.blit(hp_text, (bar_x + bar_width + 6, y + 1))
    y += 20

    # SP bar
    sp_ratio = stats.current_sp / stats.max_sp if stats.max_sp > 0 else 0
    sp_label = hud_font.render("SP", True, (255, 255, 255))
    screen.blit(sp_label, (col_left, y))
    pygame.draw.rect(screen, (40, 40, 40), (bar_x, y + 2, bar_width, bar_height))
    pygame.draw.rect(screen, COLOR_SP_BAR, (bar_x, y + 2, int(bar_width * sp_ratio), bar_height))
    pygame.draw.rect(screen, (140, 140, 140), (bar_x, y + 2, bar_width, bar_height), 1)
    sp_text = hud_font.render(f"{stats.current_sp}/{stats.max_sp}", True, (255, 255, 255))
    screen.blit(sp_text, (bar_x + bar_width + 6, y + 1))
    y += 20

    # XP bar
    xp_label = hud_font.render("XP", True, (255, 255, 255))
    screen.blit(xp_label, (col_left, y))
    xp_needed = xp_to_next
    xp_ratio = stats.xp / xp_needed if xp_needed > 0 else 0
    pygame.draw.rect(screen, (60, 60, 60), (bar_x, y + 2, bar_width, bar_height))
    pygame.draw.rect(screen, COLOR_XP_BAR, (bar_x, y + 2, int(bar_width * xp_ratio), bar_height))
    pygame.draw.rect(screen, (180, 180, 180), (bar_x, y + 2, bar_width, bar_height), 1)
    xp_text = hud_font.render(f"{stats.xp}/{xp_needed}", True, (255, 255, 255))
    screen.blit(xp_text, (bar_x + bar_width + 6, y + 1))

    # --- CENTER COLUMN: Money + map name ---
    y = HUD_Y + pad
    money_label = hud_font.render(f"Scrap: {stats.money}", True, COLOR_MONEY_TEXT)
    screen.blit(money_label, (col_mid, y))
    y += 20

    if display_name:
        map_label = hud_font.render(display_name, True, (200, 200, 200))
        screen.blit(map_label, (col_mid, y))

    # --- RIGHT COLUMN: Conditional notifications ---
    y = HUD_Y + pad
    if stats.unspent_points > 0:
        pts_label = hud_font.render(
            f"+{stats.unspent_points} pts [C]", True, (255, 220, 100)
        )
        screen.blit(pts_label, (col_right, y))
        y += 20

    if player_skills.skill_points > 0:
        skill_label = hud_font.render(
            f"+{player_skills.skill_points} skill pts [K]", True, (100, 180, 255)
        )
        screen.blit(skill_label, (col_right, y))
        y += 20

    if player_quests.has_completable():
        quest_label = hud_font.render("! Quest ready [Q]", True, (100, 255, 100))
        screen.blit(quest_label, (col_right, y))

    # Minimap in HUD (far right)
    if minimap is not None and minimap_visible:
        minimap.draw(screen, SCREEN_WIDTH - minimap.width - 6, HUD_Y + (HUD_HEIGHT - minimap.height) // 2)

    # Vertical dividers between columns
    div_x1 = SCREEN_WIDTH // 3
    div_x2 = 2 * SCREEN_WIDTH // 3
    pygame.draw.line(screen, COLOR_HUD_BORDER, (div_x1, HUD_Y + 6), (div_x1, HUD_Y + HUD_HEIGHT - 6), 1)
    pygame.draw.line(screen, COLOR_HUD_BORDER, (div_x2, HUD_Y + 6), (div_x2, HUD_Y + HUD_HEIGHT - 6), 1)
