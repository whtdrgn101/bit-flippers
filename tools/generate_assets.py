#!/usr/bin/env python3
"""Generate pixel art PNGs and procedural audio for Bit Flippers.

Run:  python tools/generate_assets.py

Uses SDL dummy video driver for headless operation.
All outputs go under assets/ relative to the project root.
"""
import math
import os
import random
import struct
import sys
import wave

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame  # noqa: E402

pygame.init()
# Need a display surface even with dummy driver
pygame.display.set_mode((1, 1))

random.seed(42)

TILE = 32  # base tile size

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
TILES_DIR = os.path.join(PROJECT_ROOT, "assets", "tiles")
SOUNDS_DIR = os.path.join(PROJECT_ROOT, "assets", "sounds")
MUSIC_DIR = os.path.join(PROJECT_ROOT, "assets", "music")


def ensure_dirs():
    os.makedirs(SPRITES_DIR, exist_ok=True)
    os.makedirs(TILES_DIR, exist_ok=True)
    # Also create placeholder dirs for audio (no files yet)
    os.makedirs(os.path.join(PROJECT_ROOT, "assets", "sounds"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, "assets", "music"), exist_ok=True)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def outline_rect(surf, color, rect, thick=1):
    """Draw a filled rect with a darker outline."""
    pygame.draw.rect(surf, color, rect)
    dark = (max(0, color[0] - 60), max(0, color[1] - 60), max(0, color[2] - 60))
    pygame.draw.rect(surf, dark, rect, thick)


def highlight_px(surf, x, y, color, strength=40):
    """Add a highlight pixel (lighter version of color)."""
    c = (min(255, color[0] + strength), min(255, color[1] + strength), min(255, color[2] + strength))
    surf.set_at((x, y), c)


def shadow_px(surf, x, y, color, strength=40):
    """Add a shadow pixel (darker version of color)."""
    c = (max(0, color[0] - strength), max(0, color[1] - strength), max(0, color[2] - strength))
    surf.set_at((x, y), c)


def dark_outline(surf):
    """Add 1px dark outline around all non-transparent pixels."""
    w, h = surf.get_size()
    outline_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    outline_color = (20, 15, 10, 255)
    for y in range(h):
        for x in range(w):
            r, g, b, a = surf.get_at((x, y))
            if a > 0:
                continue
            # Check neighbors
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    _, _, _, na = surf.get_at((nx, ny))
                    if na > 128:
                        outline_surf.set_at((x, y), outline_color)
                        break
    # Blit outline under the sprite
    result = pygame.Surface((w, h), pygame.SRCALPHA)
    result.blit(outline_surf, (0, 0))
    result.blit(surf, (0, 0))
    return result


# ---------------------------------------------------------------------------
# Player sprite: 4 cols x 4 rows (128x128)
# Rows: down, up, left, right
# Cols: idle, walk1, walk2, walk3
# ---------------------------------------------------------------------------

def generate_player():
    sheet_w, sheet_h = TILE * 4, TILE * 4
    sheet = pygame.Surface((sheet_w, sheet_h), pygame.SRCALPHA)

    body_color = (50, 160, 200)
    armor_color = (70, 90, 110)
    helmet_color = (90, 100, 120)
    visor_color = (140, 220, 255)
    boot_color = (60, 50, 40)
    skin_color = (210, 170, 130)

    directions = ["down", "up", "left", "right"]

    for row, direction in enumerate(directions):
        for col in range(4):
            frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)

            # Walk bob
            bob = 0
            if col == 1:
                bob = -1
            elif col == 3:
                bob = 1

            # Helmet (top)
            for hx in range(10, 22):
                for hy in range(4 + bob, 12 + bob):
                    dist = abs(hx - 16) + abs(hy - (8 + bob))
                    if dist < 10:
                        frame.set_at((hx, hy), helmet_color)
                        if hy == 4 + bob or hx == 10 or hx == 21:
                            highlight_px(frame, hx, hy, helmet_color, 30)

            # Visor
            if direction == "down":
                for vx in range(12, 20):
                    frame.set_at((vx, 9 + bob), visor_color)
                    frame.set_at((vx, 10 + bob), visor_color)
            elif direction == "up":
                pass  # no visor from behind
            elif direction == "left":
                for vx in range(10, 14):
                    frame.set_at((vx, 9 + bob), visor_color)
                    frame.set_at((vx, 10 + bob), visor_color)
            elif direction == "right":
                for vx in range(18, 22):
                    frame.set_at((vx, 9 + bob), visor_color)
                    frame.set_at((vx, 10 + bob), visor_color)

            # Body / armor
            for bx in range(9, 23):
                for by in range(12 + bob, 22 + bob):
                    frame.set_at((bx, by), armor_color)
                    # Chest highlight
                    if bx in (14, 15, 16, 17) and by in (14 + bob, 15 + bob):
                        highlight_px(frame, bx, by, armor_color, 35)
                    # Bottom shadow
                    if by >= 20 + bob:
                        shadow_px(frame, bx, by, armor_color, 25)

            # Belt
            for bx in range(10, 22):
                frame.set_at((bx, 22 + bob), (80, 60, 40))

            # Legs
            leg_offset_l = 0
            leg_offset_r = 0
            if col == 1:
                leg_offset_l = -1
                leg_offset_r = 1
            elif col == 3:
                leg_offset_l = 1
                leg_offset_r = -1

            # Left leg
            for lx in range(11, 15):
                for ly in range(23 + bob, 28 + bob + leg_offset_l):
                    if 0 <= ly < TILE:
                        frame.set_at((lx, ly), body_color)
            # Right leg
            for lx in range(17, 21):
                for ly in range(23 + bob, 28 + bob + leg_offset_r):
                    if 0 <= ly < TILE:
                        frame.set_at((lx, ly), body_color)

            # Boots
            for lx in range(10, 15):
                for ly in range(max(0, 28 + bob + leg_offset_l), min(TILE, 30 + bob + leg_offset_l)):
                    if 0 <= ly < TILE:
                        frame.set_at((lx, ly), boot_color)
            for lx in range(17, 22):
                for ly in range(max(0, 28 + bob + leg_offset_r), min(TILE, 30 + bob + leg_offset_r)):
                    if 0 <= ly < TILE:
                        frame.set_at((lx, ly), boot_color)

            # Arms
            arm_swing = 0
            if col == 1:
                arm_swing = -2
            elif col == 3:
                arm_swing = 2

            # Left arm
            for ay in range(13 + bob, 21 + bob + arm_swing):
                if 0 <= ay < TILE:
                    frame.set_at((8, ay), skin_color)
                    frame.set_at((7, ay), skin_color)
            # Right arm
            for ay in range(13 + bob, 21 + bob - arm_swing):
                if 0 <= ay < TILE:
                    frame.set_at((23, ay), skin_color)
                    frame.set_at((24, ay), skin_color)

            frame = dark_outline(frame)
            sheet.blit(frame, (col * TILE, row * TILE))

    path = os.path.join(SPRITES_DIR, "player.png")
    pygame.image.save(sheet, path)
    print(f"  Created {path}")


# ---------------------------------------------------------------------------
# NPC sprites: 1 col x 4 rows (32x128)
# Rows: down, up, left, right
# ---------------------------------------------------------------------------

def generate_npc(name, body_color):
    sheet_w, sheet_h = TILE, TILE * 4
    sheet = pygame.Surface((sheet_w, sheet_h), pygame.SRCALPHA)

    hat_color = (max(0, body_color[0] - 40), max(0, body_color[1] - 40), max(0, body_color[2] - 40))
    eye_color = (255, 255, 255)
    pupil_color = (20, 20, 40)

    directions = ["down", "up", "left", "right"]
    dir_offsets = {"down": (0, 3), "up": (0, -3), "left": (-3, 0), "right": (3, 0)}

    for row, direction in enumerate(directions):
        frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        edx, edy = dir_offsets[direction]

        # Hat brim
        for hx in range(6, 26):
            for hy in range(3, 6):
                frame.set_at((hx, hy), hat_color)
                if hy == 3:
                    highlight_px(frame, hx, hy, hat_color, 30)

        # Hat top
        for hx in range(9, 23):
            for hy in range(0, 4):
                frame.set_at((hx, hy), hat_color)

        # Head
        for hx in range(10, 22):
            for hy in range(6, 14):
                frame.set_at((hx, hy), (210, 170, 130))

        # Eyes
        if direction != "up":
            ex, ey = 16 + edx, 9 + edy
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx * dx + dy * dy <= 5:
                        px, py = ex + dx, ey + dy
                        if 0 <= px < TILE and 0 <= py < TILE:
                            frame.set_at((px, py), eye_color)
            # Pupil
            px_c, py_c = ex + edx // 2, ey + edy // 2
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if dx * dx + dy * dy <= 1:
                        px, py = px_c + dx, py_c + dy
                        if 0 <= px < TILE and 0 <= py < TILE:
                            frame.set_at((px, py), pupil_color)

        # Body (robe-like)
        for bx in range(8, 24):
            for by in range(14, 28):
                frame.set_at((bx, by), body_color)
                # Highlight on left side
                if bx <= 10:
                    highlight_px(frame, bx, by, body_color, 25)
                # Shadow on right side
                if bx >= 22:
                    shadow_px(frame, bx, by, body_color, 20)

        # Feet
        for fx in range(10, 15):
            for fy in range(28, 31):
                if fy < TILE:
                    frame.set_at((fx, fy), (60, 50, 40))
        for fx in range(18, 23):
            for fy in range(28, 31):
                if fy < TILE:
                    frame.set_at((fx, fy), (60, 50, 40))

        frame = dark_outline(frame)
        sheet.blit(frame, (0, row * TILE))

    path = os.path.join(SPRITES_DIR, f"npc_{name}.png")
    pygame.image.save(sheet, path)
    print(f"  Created {path}")


# ---------------------------------------------------------------------------
# Enemy sprites: 2 cols x 1 row (64x32)
# Col 0: idle frame 1, Col 1: idle frame 2
# ---------------------------------------------------------------------------

def generate_enemy_scrap_rat():
    sheet = pygame.Surface((TILE * 2, TILE), pygame.SRCALPHA)
    body_color = (140, 100, 60)

    for col in range(2):
        frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        bob = -1 if col == 0 else 1

        # Body - hunched oval
        for x in range(8, 26):
            for y in range(12 + bob, 24 + bob):
                dx = (x - 17) / 9.0
                dy = (y - (18 + bob)) / 6.0
                if dx * dx + dy * dy <= 1.0:
                    frame.set_at((x, y), body_color)
                    if dy < -0.5:
                        highlight_px(frame, x, y, body_color, 30)

        # Head - small circle at front
        for x in range(4, 12):
            for y in range(10 + bob, 18 + bob):
                dx = (x - 8) / 4.0
                dy = (y - (14 + bob)) / 4.0
                if dx * dx + dy * dy <= 1.0:
                    frame.set_at((x, y), body_color)
                    if dy < -0.3:
                        highlight_px(frame, x, y, body_color, 25)

        # Eye
        frame.set_at((6, 12 + bob), (255, 60, 60))
        frame.set_at((7, 12 + bob), (255, 60, 60))
        frame.set_at((6, 13 + bob), (80, 0, 0))

        # Whiskers
        for wx in range(1, 5):
            wy = 14 + bob + (wx % 2)
            if 0 <= wy < TILE:
                frame.set_at((wx, wy), (180, 140, 100))
            wy2 = 16 + bob - (wx % 2)
            if 0 <= wy2 < TILE:
                frame.set_at((wx, wy2), (180, 140, 100))

        # Tail
        tail_y_base = 16 + bob
        for tx in range(26, 31):
            ty = tail_y_base - (tx - 26) + (col * 2 - 1)
            if 0 <= tx < TILE and 0 <= ty < TILE:
                frame.set_at((tx, ty), (120, 80, 50))
            if 0 <= tx < TILE and 0 <= ty + 1 < TILE:
                frame.set_at((tx, ty + 1), (120, 80, 50))

        # Ears
        frame.set_at((9, 9 + bob), (160, 120, 80))
        frame.set_at((10, 8 + bob), (160, 120, 80))
        frame.set_at((10, 9 + bob), (160, 120, 80))

        # Legs (small)
        for lx in range(12, 15):
            for ly in range(24 + bob, 27 + bob):
                if 0 <= ly < TILE:
                    frame.set_at((lx, ly), (100, 70, 40))
        for lx in range(20, 23):
            for ly in range(24 + bob, 27 + bob):
                if 0 <= ly < TILE:
                    frame.set_at((lx, ly), (100, 70, 40))

        frame = dark_outline(frame)
        sheet.blit(frame, (col * TILE, 0))

    path = os.path.join(SPRITES_DIR, "enemy_scrap_rat.png")
    pygame.image.save(sheet, path)
    print(f"  Created {path}")


def generate_enemy_rust_golem():
    sheet = pygame.Surface((TILE * 2, TILE), pygame.SRCALPHA)
    body_color = (160, 80, 40)

    for col in range(2):
        frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        bob = -1 if col == 0 else 1

        # Blocky body
        for x in range(6, 26):
            for y in range(6 + bob, 26 + bob):
                if 0 <= y < TILE:
                    frame.set_at((x, y), body_color)

        # Rust spots
        rust_color = (130, 55, 20)
        spots = [(10, 10), (20, 14), (12, 20), (22, 22), (8, 16), (18, 8)]
        for sx, sy in spots:
            sy += bob
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    px, py = sx + dx, sy + dy
                    if 6 <= px < 26 and 0 <= py < TILE:
                        frame.set_at((px, py), rust_color)

        # Highlight on top edge
        for x in range(7, 25):
            y = 6 + bob
            if 0 <= y < TILE:
                highlight_px(frame, x, y, body_color, 40)

        # Shadow on bottom
        for x in range(7, 25):
            y = 25 + bob
            if 0 <= y < TILE:
                shadow_px(frame, x, y, body_color, 35)

        # Eyes (glowing)
        for ex in range(10, 14):
            for ey in range(10 + bob, 13 + bob):
                if 0 <= ey < TILE:
                    frame.set_at((ex, ey), (255, 160, 60))
        for ex in range(18, 22):
            for ey in range(10 + bob, 13 + bob):
                if 0 <= ey < TILE:
                    frame.set_at((ex, ey), (255, 160, 60))

        # Mouth crack
        for mx in range(12, 20):
            my = 18 + bob + ((mx + col) % 2)
            if 0 <= my < TILE:
                frame.set_at((mx, my), (60, 30, 10))

        # Arms (blocky)
        for ay in range(10 + bob, 22 + bob):
            if 0 <= ay < TILE:
                frame.set_at((4, ay), body_color)
                frame.set_at((5, ay), body_color)
                frame.set_at((26, ay), body_color)
                frame.set_at((27, ay), body_color)

        # Legs
        for lx in range(8, 14):
            for ly in range(26 + bob, 30 + bob):
                if 0 <= ly < TILE:
                    frame.set_at((lx, ly), (120, 60, 30))
        for lx in range(18, 24):
            for ly in range(26 + bob, 30 + bob):
                if 0 <= ly < TILE:
                    frame.set_at((lx, ly), (120, 60, 30))

        frame = dark_outline(frame)
        sheet.blit(frame, (col * TILE, 0))

    path = os.path.join(SPRITES_DIR, "enemy_rust_golem.png")
    pygame.image.save(sheet, path)
    print(f"  Created {path}")


def generate_enemy_volt_wraith():
    sheet = pygame.Surface((TILE * 2, TILE), pygame.SRCALPHA)
    body_color = (100, 60, 180)

    for col in range(2):
        frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        bob = -1 if col == 0 else 1

        # Ethereal body - taper from wide middle to narrow top and bottom
        for y in range(4 + bob, 30 + bob):
            if not (0 <= y < TILE):
                continue
            cy = 16 + bob
            dist = abs(y - cy)
            half_w = max(2, 12 - dist // 2)
            for x in range(16 - half_w, 16 + half_w):
                if 0 <= x < TILE:
                    # Vary alpha for ethereal feel
                    alpha = max(100, 255 - dist * 8)
                    frame.set_at((x, y), (*body_color, alpha))

        # Lightning lines (electric effect)
        lightning_color = (180, 200, 255)
        rng = random.Random(42 + col)
        for _ in range(3):
            lx = rng.randint(10, 22)
            ly_start = rng.randint(6 + bob, 12 + bob)
            for step in range(8):
                ly = ly_start + step
                lx += rng.choice([-1, 0, 1])
                lx = max(8, min(24, lx))
                if 0 <= lx < TILE and 0 <= ly < TILE:
                    frame.set_at((lx, ly), lightning_color)

        # Glowing eyes
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if abs(dx) + abs(dy) <= 1:
                    ex1, ey1 = 12 + dx, 12 + bob + dy
                    ex2, ey2 = 20 + dx, 12 + bob + dy
                    if 0 <= ey1 < TILE:
                        frame.set_at((ex1, ey1), (200, 220, 255))
                    if 0 <= ey2 < TILE:
                        frame.set_at((ex2, ey2), (200, 220, 255))

        # Eye cores
        if 0 <= 12 + bob < TILE:
            frame.set_at((12, 12 + bob), (255, 255, 255))
            frame.set_at((20, 12 + bob), (255, 255, 255))

        # Wispy bottom tendrils
        for t in range(4):
            tx = 10 + t * 4 + (col * 2 - 1)
            for ty in range(26 + bob, 31 + bob):
                if 0 <= tx < TILE and 0 <= ty < TILE:
                    alpha = max(60, 180 - (ty - 26 - bob) * 30)
                    frame.set_at((tx, ty), (*body_color, alpha))

        frame = dark_outline(frame)
        sheet.blit(frame, (col * TILE, 0))

    path = os.path.join(SPRITES_DIR, "enemy_volt_wraith.png")
    pygame.image.save(sheet, path)
    print(f"  Created {path}")


# ---------------------------------------------------------------------------
# Tileset: 3 cols x 1 row (96x32)
# Col 0: DIRT (noise), Col 1: WALL (brick), Col 2: SCRAP (metallic)
# ---------------------------------------------------------------------------

def generate_tileset():
    sheet = pygame.Surface((TILE * 9, TILE), pygame.SRCALPHA)

    # DIRT tile — noise texture
    dirt_base = (139, 90, 43)
    dirt_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    rng = random.Random(100)
    for x in range(TILE):
        for y in range(TILE):
            variation = rng.randint(-15, 15)
            c = (
                max(0, min(255, dirt_base[0] + variation)),
                max(0, min(255, dirt_base[1] + variation)),
                max(0, min(255, dirt_base[2] + variation)),
            )
            dirt_frame.set_at((x, y), c)
    sheet.blit(dirt_frame, (0, 0))

    # WALL tile — brick pattern
    wall_base = (105, 105, 105)
    mortar_color = (70, 70, 70)
    wall_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    wall_frame.fill(mortar_color)

    brick_h = 8
    brick_w = 16
    rng2 = random.Random(200)
    for row in range(TILE // brick_h):
        offset = (brick_w // 2) if (row % 2) else 0
        for col_start in range(-brick_w, TILE + brick_w, brick_w):
            bx = col_start + offset
            by = row * brick_h
            variation = rng2.randint(-10, 10)
            brick_color = (
                max(0, min(255, wall_base[0] + variation)),
                max(0, min(255, wall_base[1] + variation)),
                max(0, min(255, wall_base[2] + variation)),
            )
            # Fill brick area (leave 1px mortar gap)
            for px in range(bx + 1, bx + brick_w - 1):
                for py in range(by + 1, by + brick_h - 1):
                    if 0 <= px < TILE and 0 <= py < TILE:
                        wall_frame.set_at((px, py), brick_color)
            # Top highlight on each brick
            for px in range(bx + 1, bx + brick_w - 1):
                py = by + 1
                if 0 <= px < TILE and 0 <= py < TILE:
                    highlight_px(wall_frame, px, py, brick_color, 20)
    sheet.blit(wall_frame, (TILE, 0))

    # SCRAP tile — pile of scrap metal on dirt background
    scrap_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    rng3 = random.Random(300)

    # Dirt background (matches dirt tile style)
    for x in range(TILE):
        for y in range(TILE):
            variation = rng3.randint(-12, 12)
            c = (
                max(0, min(255, dirt_base[0] + variation)),
                max(0, min(255, dirt_base[1] + variation)),
                max(0, min(255, dirt_base[2] + variation)),
            )
            scrap_frame.set_at((x, y), c)

    # Scrap pile — several overlapping metal pieces
    metal_dark = (130, 115, 50)
    metal_mid = (180, 160, 60)
    metal_light = (220, 200, 90)
    rust_color = (160, 90, 40)

    # Bottom piece — flat plate angled
    for x in range(8, 26):
        for y in range(20, 26):
            if y < 23 + (x - 8) // 6:
                scrap_frame.set_at((x, y), metal_dark)
                if y == 20:
                    highlight_px(scrap_frame, x, y, metal_dark, 35)

    # Middle piece — bent panel
    for x in range(6, 22):
        for y in range(14, 22):
            if abs(x - 14) + abs(y - 18) < 10:
                scrap_frame.set_at((x, y), metal_mid)
                if y <= 15:
                    highlight_px(scrap_frame, x, y, metal_mid, 40)
                if y >= 20:
                    shadow_px(scrap_frame, x, y, metal_mid, 30)

    # Top piece — small gear/cog shape
    gear_cx, gear_cy = 18, 12
    gear_color = (190, 175, 70)
    for x in range(gear_cx - 5, gear_cx + 6):
        for y in range(gear_cy - 5, gear_cy + 6):
            dx, dy = x - gear_cx, y - gear_cy
            dist = dx * dx + dy * dy
            if dist <= 16:
                if 0 <= x < TILE and 0 <= y < TILE:
                    scrap_frame.set_at((x, y), gear_color)
            # Gear teeth
            if dist <= 25 and dist > 12 and (abs(dx) <= 1 or abs(dy) <= 1):
                if 0 <= x < TILE and 0 <= y < TILE:
                    scrap_frame.set_at((x, y), gear_color)
    # Gear hole
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if abs(dx) + abs(dy) <= 1:
                scrap_frame.set_at((gear_cx + dx, gear_cy + dy), metal_dark)

    # Small pipe piece on the left
    pipe_color = (150, 140, 55)
    for y in range(10, 20):
        for x in range(9, 12):
            if 0 <= x < TILE and 0 <= y < TILE:
                scrap_frame.set_at((x, y), pipe_color)
                if x == 9:
                    highlight_px(scrap_frame, x, y, pipe_color, 30)
                if x == 11:
                    shadow_px(scrap_frame, x, y, pipe_color, 25)

    # Rust spots
    rust_spots = [(10, 22), (20, 18), (14, 16), (22, 24)]
    for sx, sy in rust_spots:
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                px, py = sx + dx, sy + dy
                if 0 <= px < TILE and 0 <= py < TILE:
                    scrap_frame.set_at((px, py), rust_color)

    # Metallic shine highlights on top edges
    shine_spots = [(12, 14), (18, 10), (15, 12), (20, 14)]
    for sx, sy in shine_spots:
        if 0 <= sx < TILE and 0 <= sy < TILE:
            scrap_frame.set_at((sx, sy), metal_light)
        if 0 <= sx + 1 < TILE and 0 <= sy < TILE:
            scrap_frame.set_at((sx + 1, sy), metal_light)

    sheet.blit(scrap_frame, (TILE * 2, 0))

    # DOOR tile — wooden door
    door_base = (80, 60, 40)
    door_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    rng4 = random.Random(400)
    # Wood background
    for x in range(TILE):
        for y in range(TILE):
            variation = rng4.randint(-8, 8)
            c = (
                max(0, min(255, door_base[0] + variation)),
                max(0, min(255, door_base[1] + variation)),
                max(0, min(255, door_base[2] + variation)),
            )
            door_frame.set_at((x, y), c)
    # Vertical wood planks
    plank_color = (60, 45, 30)
    for px in (8, 16, 24):
        for y in range(TILE):
            door_frame.set_at((px, y), plank_color)
    # Horizontal bands (top, middle, bottom)
    band_color = (50, 40, 25)
    for by in (4, 15, 27):
        for x in range(TILE):
            door_frame.set_at((x, by), band_color)
            if by + 1 < TILE:
                door_frame.set_at((x, by + 1), band_color)
    # Door handle
    handle_color = (180, 160, 80)
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            hx, hy = 22 + dx, 16 + dy
            if 0 <= hx < TILE and 0 <= hy < TILE and abs(dx) + abs(dy) <= 1:
                door_frame.set_at((hx, hy), handle_color)
    # Highlight on top edge
    for x in range(1, TILE - 1):
        highlight_px(door_frame, x, 1, door_base, 30)
    sheet.blit(door_frame, (TILE * 3, 0))

    # GRASS tile — vibrant green with wildflowers
    grass_base = (60, 140, 50)
    grass_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    rng5 = random.Random(500)
    for x in range(TILE):
        for y in range(TILE):
            variation = rng5.randint(-20, 20)
            c = (
                max(0, min(255, grass_base[0] + variation)),
                max(0, min(255, grass_base[1] + variation)),
                max(0, min(255, grass_base[2] + variation)),
            )
            grass_frame.set_at((x, y), c)
    # Grass tuft clusters — lighter green streaks
    tuft_color = (90, 180, 70)
    for _ in range(rng5.randint(6, 8)):
        tx, ty = rng5.randint(2, 29), rng5.randint(2, 29)
        for dx in range(-1, 2):
            for dy in range(0, 3):
                px, py = tx + dx, ty + dy
                if 0 <= px < TILE and 0 <= py < TILE:
                    grass_frame.set_at((px, py), tuft_color)
    # Tiny wildflower dots
    flower_colors = [(255, 220, 60), (240, 130, 180), (255, 180, 50)]
    for _ in range(rng5.randint(2, 3)):
        fx, fy = rng5.randint(3, 28), rng5.randint(3, 28)
        fc = rng5.choice(flower_colors)
        grass_frame.set_at((fx, fy), fc)
    # Sunlight highlight spots
    for _ in range(4):
        sx, sy = rng5.randint(2, 29), rng5.randint(2, 29)
        highlight_px(grass_frame, sx, sy, grass_base, 40)
    sheet.blit(grass_frame, (TILE * 4, 0))

    # PATH tile — cracked asphalt, overgrown edges
    path_base = (120, 115, 100)
    path_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    rng6 = random.Random(600)
    for x in range(TILE):
        for y in range(TILE):
            variation = rng6.randint(-10, 10)
            c = (
                max(0, min(255, path_base[0] + variation)),
                max(0, min(255, path_base[1] + variation)),
                max(0, min(255, path_base[2] + variation)),
            )
            path_frame.set_at((x, y), c)
    # Dark crack lines
    crack_color = (80, 75, 65)
    for _ in range(rng6.randint(2, 3)):
        cx = rng6.randint(6, 26)
        cy = rng6.randint(4, 10)
        for step in range(rng6.randint(8, 16)):
            if 0 <= cx < TILE and 0 <= cy < TILE:
                path_frame.set_at((cx, cy), crack_color)
            cx += rng6.choice([-1, 0, 1])
            cy += 1
            cx = max(0, min(TILE - 1, cx))
    # Green grass along edges (overgrown feel)
    edge_green = (70, 130, 55)
    for x in range(TILE):
        for y in range(0, rng6.randint(2, 4)):
            if rng6.random() < 0.6:
                path_frame.set_at((x, y), edge_green)
        for y in range(TILE - rng6.randint(2, 4), TILE):
            if rng6.random() < 0.6:
                path_frame.set_at((x, y), edge_green)
    # Lighter concrete patches
    for _ in range(3):
        px, py = rng6.randint(6, 26), rng6.randint(6, 26)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                ppx, ppy = px + dx, py + dy
                if 0 <= ppx < TILE and 0 <= ppy < TILE:
                    highlight_px(path_frame, ppx, ppy, path_base, 20)
    sheet.blit(path_frame, (TILE * 5, 0))

    # WATER tile — deep blue with ripple highlights
    water_base = (40, 90, 160)
    water_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    rng7 = random.Random(700)
    for x in range(TILE):
        for y in range(TILE):
            variation = rng7.randint(-12, 12)
            c = (
                max(0, min(255, water_base[0] + variation)),
                max(0, min(255, water_base[1] + variation)),
                max(0, min(255, water_base[2] + variation)),
            )
            water_frame.set_at((x, y), c)
    # Horizontal wavy ripple lines
    ripple_color = (80, 140, 210)
    for ry in (7, 13, 20, 26):
        rx = rng7.randint(0, 4)
        while rx < TILE:
            seg_len = rng7.randint(3, 7)
            for sx in range(rx, min(rx + seg_len, TILE)):
                water_frame.set_at((sx, ry), ripple_color)
            rx += seg_len + rng7.randint(2, 5)
    # White specular dots
    for _ in range(4):
        sx, sy = rng7.randint(3, 28), rng7.randint(3, 28)
        water_frame.set_at((sx, sy), (220, 230, 255))
    sheet.blit(water_frame, (TILE * 6, 0))

    # TREE tile — brown trunk with green foliage canopy
    tree_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    rng8 = random.Random(800)
    # Fill background with dark grass
    for x in range(TILE):
        for y in range(TILE):
            variation = rng8.randint(-15, 15)
            c = (
                max(0, min(255, 30 + variation)),
                max(0, min(255, 90 + variation)),
                max(0, min(255, 35 + variation)),
            )
            tree_frame.set_at((x, y), c)
    # Brown trunk at center-bottom
    trunk_color = (80, 55, 30)
    for tx in range(14, 18):
        for ty in range(20, 28):
            tree_frame.set_at((tx, ty), trunk_color)
            if tx == 14:
                shadow_px(tree_frame, tx, ty, trunk_color, 20)
            if tx == 17:
                highlight_px(tree_frame, tx, ty, trunk_color, 15)
    # Circular foliage canopy
    foliage_base = (30, 100, 40)
    cx, cy, radius = 16, 13, 11
    for x in range(TILE):
        for y in range(TILE):
            dx, dy = x - cx, y - cy
            dist_sq = dx * dx + dy * dy
            if dist_sq <= radius * radius:
                variation = rng8.randint(-15, 15)
                fc = (
                    max(0, min(255, foliage_base[0] + variation)),
                    max(0, min(255, foliage_base[1] + variation)),
                    max(0, min(255, foliage_base[2] + variation)),
                )
                tree_frame.set_at((x, y), fc)
    # Sun patches on top-left
    for _ in range(6):
        sx = rng8.randint(cx - 8, cx - 2)
        sy = rng8.randint(cy - 8, cy - 2)
        dx, dy = sx - cx, sy - cy
        if dx * dx + dy * dy <= radius * radius and 0 <= sx < TILE and 0 <= sy < TILE:
            highlight_px(tree_frame, sx, sy, foliage_base, 35)
    # Shadow on bottom-right
    for _ in range(6):
        sx = rng8.randint(cx + 2, cx + 8)
        sy = rng8.randint(cy + 2, cy + 8)
        dx, dy = sx - cx, sy - cy
        if dx * dx + dy * dy <= radius * radius and 0 <= sx < TILE and 0 <= sy < TILE:
            shadow_px(tree_frame, sx, sy, foliage_base, 30)
    sheet.blit(tree_frame, (TILE * 7, 0))

    # RUINS tile — weathered concrete with broken bricks, rebar, moss
    ruins_base = (90, 85, 80)
    ruins_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    rng9 = random.Random(900)
    # Base concrete with noise
    for x in range(TILE):
        for y in range(TILE):
            variation = rng9.randint(-12, 12)
            c = (
                max(0, min(255, ruins_base[0] + variation)),
                max(0, min(255, ruins_base[1] + variation)),
                max(0, min(255, ruins_base[2] + variation)),
            )
            ruins_frame.set_at((x, y), c)
    # Partial broken brick pattern
    brick_color = (110, 90, 75)
    mortar_gap = (65, 60, 55)
    for row in range(4):
        offset = 8 if (row % 2) else 0
        by = row * 8
        for bx_start in range(-8, TILE + 8, 16):
            bx = bx_start + offset
            # Some bricks missing
            if rng9.random() < 0.3:
                continue
            for px in range(bx + 1, bx + 15):
                for py in range(by + 1, by + 7):
                    if 0 <= px < TILE and 0 <= py < TILE:
                        ruins_frame.set_at((px, py), brick_color)
            # Mortar gaps
            for px in range(bx, bx + 16):
                if 0 <= px < TILE and 0 <= by < TILE:
                    ruins_frame.set_at((px, by), mortar_gap)
    # Rust-colored rebar lines
    rebar_color = (140, 70, 30)
    for _ in range(rng9.randint(2, 3)):
        ry = rng9.randint(4, 28)
        rx_start = rng9.randint(2, 10)
        rx_end = rng9.randint(rx_start + 6, min(rx_start + 16, 30))
        for rx in range(rx_start, rx_end):
            if 0 <= rx < TILE and 0 <= ry < TILE:
                ruins_frame.set_at((rx, ry), rebar_color)
    # Green moss patches in corners
    moss_color = (60, 110, 45)
    corners = [(2, 2), (28, 2), (2, 28), (28, 28)]
    for mcx, mcy in corners:
        if rng9.random() < 0.6:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) + abs(dy) <= 3:
                        mx, my = mcx + dx, mcy + dy
                        if 0 <= mx < TILE and 0 <= my < TILE:
                            ruins_frame.set_at((mx, my), moss_color)
    sheet.blit(ruins_frame, (TILE * 8, 0))

    path = os.path.join(TILES_DIR, "tileset.png")
    pygame.image.save(sheet, path)
    print(f"  Created {path}")


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

_DEFAULT_SAMPLE_RATE = 22050


def _make_sine(freq, duration, volume=0.5, sample_rate=_DEFAULT_SAMPLE_RATE):
    """Generate sine wave samples as a list of floats in [-1, 1]."""
    n = int(sample_rate * duration)
    return [volume * math.sin(2 * math.pi * freq * i / sample_rate) for i in range(n)]


def _make_noise(duration, volume=0.3, sample_rate=_DEFAULT_SAMPLE_RATE):
    """Generate white noise samples."""
    rng = random.Random(999)
    n = int(sample_rate * duration)
    return [volume * (rng.random() * 2 - 1) for _ in range(n)]


def _make_sweep(f0, f1, duration, volume=0.5, sample_rate=_DEFAULT_SAMPLE_RATE):
    """Generate a linear frequency sweep from f0 to f1."""
    n = int(sample_rate * duration)
    samples = []
    for i in range(n):
        t = i / sample_rate
        freq = f0 + (f1 - f0) * (i / n)
        samples.append(volume * math.sin(2 * math.pi * freq * t))
    return samples


def _apply_envelope(samples, attack=0.01, decay=0.05, sample_rate=_DEFAULT_SAMPLE_RATE):
    """Apply attack/decay envelope to samples."""
    n = len(samples)
    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    result = list(samples)
    for i in range(min(attack_samples, n)):
        result[i] *= i / attack_samples
    for i in range(min(decay_samples, n)):
        idx = n - 1 - i
        if idx >= 0:
            result[idx] *= i / decay_samples
    return result


def _mix(a, b):
    """Mix two sample lists together, zero-padding the shorter one."""
    length = max(len(a), len(b))
    result = [0.0] * length
    for i in range(len(a)):
        result[i] += a[i]
    for i in range(len(b)):
        result[i] += b[i]
    # Clamp
    return [max(-1.0, min(1.0, s)) for s in result]


def _concat(*parts):
    """Concatenate multiple sample lists."""
    result = []
    for p in parts:
        result.extend(p)
    return result


def _write_wav(path, samples, sample_rate=_DEFAULT_SAMPLE_RATE):
    """Write mono 16-bit WAV file from float samples in [-1, 1]."""
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = b""
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            data += struct.pack("<h", int(clamped * 32767))
        wf.writeframes(data)


# ---------------------------------------------------------------------------
# SFX generation
# ---------------------------------------------------------------------------

def generate_sfx():
    """Generate all sound effect WAV files."""

    # hit.wav — 80ms noise burst with fast decay
    samples = _make_noise(0.08, volume=0.6)
    samples = _apply_envelope(samples, attack=0.002, decay=0.06)
    path = os.path.join(SOUNDS_DIR, "hit.wav")
    _write_wav(path, samples)
    print(f"  Created {path}")

    # victory.wav — 3-note ascending arpeggio C5→E5→G5
    note_dur = 0.17
    c5 = _apply_envelope(_make_sine(523.25, note_dur, 0.4), attack=0.005, decay=0.08)
    e5 = _apply_envelope(_make_sine(659.25, note_dur, 0.4), attack=0.005, decay=0.08)
    g5 = _apply_envelope(_make_sine(783.99, note_dur, 0.4), attack=0.005, decay=0.08)
    samples = _concat(c5, e5, g5)
    path = os.path.join(SOUNDS_DIR, "victory.wav")
    _write_wav(path, samples)
    print(f"  Created {path}")

    # pickup.wav — quick rising chirp 400→1200 Hz
    samples = _make_sweep(400, 1200, 0.1, volume=0.4)
    samples = _apply_envelope(samples, attack=0.005, decay=0.05)
    path = os.path.join(SOUNDS_DIR, "pickup.wav")
    _write_wav(path, samples)
    print(f"  Created {path}")

    # dialogue_advance.wav — soft click/blip
    samples = _make_sine(800, 0.05, volume=0.25)
    samples = _apply_envelope(samples, attack=0.002, decay=0.03)
    path = os.path.join(SOUNDS_DIR, "dialogue_advance.wav")
    _write_wav(path, samples)
    print(f"  Created {path}")

    # level_up.wav — 4-note ascending arpeggio with harmony
    note_dur = 0.2
    c4 = _apply_envelope(_make_sine(261.63, note_dur, 0.35), attack=0.005, decay=0.1)
    c4h = _apply_envelope(_make_sine(329.63, note_dur, 0.15), attack=0.005, decay=0.1)
    e4 = _apply_envelope(_make_sine(329.63, note_dur, 0.35), attack=0.005, decay=0.1)
    e4h = _apply_envelope(_make_sine(392.00, note_dur, 0.15), attack=0.005, decay=0.1)
    g4 = _apply_envelope(_make_sine(392.00, note_dur, 0.35), attack=0.005, decay=0.1)
    g4h = _apply_envelope(_make_sine(493.88, note_dur, 0.15), attack=0.005, decay=0.1)
    c5 = _apply_envelope(_make_sine(523.25, note_dur, 0.4), attack=0.005, decay=0.15)
    c5h = _apply_envelope(_make_sine(659.25, note_dur, 0.2), attack=0.005, decay=0.15)
    samples = _concat(
        _mix(c4, c4h), _mix(e4, e4h), _mix(g4, g4h), _mix(c5, c5h),
    )
    path = os.path.join(SOUNDS_DIR, "level_up.wav")
    _write_wav(path, samples)
    print(f"  Created {path}")


# ---------------------------------------------------------------------------
# Music generation
# ---------------------------------------------------------------------------

def _make_note(freq, duration, volume=0.3, sample_rate=_DEFAULT_SAMPLE_RATE):
    """Make an enveloped sine note with slight harmonics for warmth."""
    fundamental = _make_sine(freq, duration, volume * 0.7, sample_rate)
    harmonic = _make_sine(freq * 2, duration, volume * 0.2, sample_rate)
    third = _make_sine(freq * 3, duration, volume * 0.1, sample_rate)
    mixed = _mix(_mix(fundamental, harmonic), third)
    return _apply_envelope(mixed, attack=0.01, decay=0.05, sample_rate=sample_rate)


def _make_bass_note(freq, duration, volume=0.25, sample_rate=_DEFAULT_SAMPLE_RATE):
    """Low-frequency bass note with quick attack."""
    fundamental = _make_sine(freq, duration, volume * 0.8, sample_rate)
    sub = _make_sine(freq * 0.5, duration, volume * 0.2, sample_rate)
    mixed = _mix(fundamental, sub)
    return _apply_envelope(mixed, attack=0.005, decay=0.03, sample_rate=sample_rate)


def generate_music():
    """Generate all music WAV files."""
    sr = _DEFAULT_SAMPLE_RATE

    # --- overworld.wav: calm major-key melody, ~20s loop ---
    tempo = 0.3  # seconds per note
    # C major melody
    melody_freqs = [
        261.63, 293.66, 329.63, 349.23, 392.00, 349.23, 329.63, 293.66,
        261.63, 329.63, 392.00, 523.25, 392.00, 329.63, 293.66, 261.63,
        293.66, 349.23, 392.00, 440.00, 392.00, 349.23, 329.63, 293.66,
        261.63, 329.63, 261.63, 196.00, 220.00, 261.63, 293.66, 261.63,
        329.63, 349.23, 392.00, 440.00, 523.25, 440.00, 392.00, 349.23,
        329.63, 293.66, 261.63, 293.66, 329.63, 261.63, 196.00, 261.63,
        261.63, 329.63, 392.00, 349.23, 329.63, 293.66, 261.63, 293.66,
        329.63, 392.00, 440.00, 392.00, 349.23, 329.63, 293.66, 261.63,
    ]
    bass_freqs = [
        130.81, 130.81, 164.81, 164.81, 196.00, 196.00, 164.81, 130.81,
        130.81, 164.81, 196.00, 261.63, 196.00, 164.81, 146.83, 130.81,
        146.83, 174.61, 196.00, 220.00, 196.00, 174.61, 164.81, 146.83,
        130.81, 164.81, 130.81, 98.00, 110.00, 130.81, 146.83, 130.81,
        164.81, 174.61, 196.00, 220.00, 261.63, 220.00, 196.00, 174.61,
        164.81, 146.83, 130.81, 146.83, 164.81, 130.81, 98.00, 130.81,
        130.81, 164.81, 196.00, 174.61, 164.81, 146.83, 130.81, 146.83,
        164.81, 196.00, 220.00, 196.00, 174.61, 164.81, 146.83, 130.81,
    ]
    melody = []
    bass = []
    for i, freq in enumerate(melody_freqs):
        melody.extend(_make_note(freq, tempo * 0.9, 0.25, sr))
        melody.extend([0.0] * int(sr * tempo * 0.1))
        bf = bass_freqs[i] if i < len(bass_freqs) else 130.81
        bass.extend(_make_bass_note(bf, tempo * 0.9, 0.15, sr))
        bass.extend([0.0] * int(sr * tempo * 0.1))
    samples = _mix(melody, bass)
    path = os.path.join(MUSIC_DIR, "overworld.wav")
    _write_wav(path, samples, sr)
    print(f"  Created {path}")

    # --- combat.wav: fast-paced minor key, ~15s loop ---
    tempo = 0.18
    combat_melody = [
        220.00, 261.63, 293.66, 349.23, 329.63, 261.63, 220.00, 196.00,
        220.00, 293.66, 349.23, 392.00, 349.23, 293.66, 261.63, 220.00,
        196.00, 220.00, 261.63, 293.66, 349.23, 329.63, 293.66, 261.63,
        220.00, 261.63, 293.66, 349.23, 392.00, 349.23, 293.66, 220.00,
        174.61, 196.00, 220.00, 261.63, 293.66, 329.63, 293.66, 261.63,
        220.00, 196.00, 174.61, 196.00, 220.00, 261.63, 220.00, 196.00,
        220.00, 261.63, 329.63, 349.23, 329.63, 293.66, 261.63, 220.00,
        196.00, 220.00, 261.63, 293.66, 261.63, 220.00, 196.00, 220.00,
        174.61, 196.00, 220.00, 261.63, 293.66, 349.23, 392.00, 349.23,
        293.66, 261.63, 220.00, 196.00, 174.61, 196.00, 220.00, 220.00,
    ]
    combat_bass = []
    combat_mel = []
    for i, freq in enumerate(combat_melody):
        combat_mel.extend(_make_note(freq, tempo * 0.85, 0.3, sr))
        combat_mel.extend([0.0] * int(sr * tempo * 0.15))
        bf = freq * 0.5
        combat_bass.extend(_make_bass_note(bf, tempo * 0.85, 0.2, sr))
        combat_bass.extend([0.0] * int(sr * tempo * 0.15))
    # Add rhythmic pulse
    pulse = []
    for i in range(len(combat_mel)):
        t = i / sr
        beat = int(t / (tempo * 2)) % 2
        pulse.append(0.08 if beat == 0 else 0.0)
    noise_pulse = [p * (random.Random(i).random() * 2 - 1) * 0.5 for i, p in enumerate(pulse)]
    samples = _mix(_mix(combat_mel, combat_bass), noise_pulse)
    path = os.path.join(MUSIC_DIR, "combat.wav")
    _write_wav(path, samples, sr)
    print(f"  Created {path}")

    # --- cave.wav: dark ambient drone + sparse notes, ~20s ---
    duration = 20.0
    n = int(sr * duration)
    # Low drone
    drone = _make_sine(65.41, duration, 0.15, sr)  # C2
    drone2 = _make_sine(98.00, duration, 0.08, sr)  # G2
    drone_mix = _mix(drone, drone2)
    # Sparse high notes
    sparse = [0.0] * n
    rng = random.Random(42)
    note_times = sorted([rng.uniform(0, duration - 1.0) for _ in range(12)])
    cave_notes = [196.00, 220.00, 261.63, 293.66, 329.63]
    for t in note_times:
        freq = rng.choice(cave_notes)
        note = _apply_envelope(_make_sine(freq, 0.8, 0.12, sr), attack=0.1, decay=0.4, sample_rate=sr)
        start = int(t * sr)
        for j, s in enumerate(note):
            if start + j < n:
                sparse[start + j] += s
    sparse = [max(-1.0, min(1.0, s)) for s in sparse]
    samples = _mix(drone_mix, sparse)
    path = os.path.join(MUSIC_DIR, "cave.wav")
    _write_wav(path, samples, sr)
    print(f"  Created {path}")

    # --- factory.wav: industrial rhythmic pulse, ~16s ---
    tempo = 0.25
    n_beats = 64
    factory_mel = []
    factory_rhythm = []
    rng = random.Random(77)
    factory_notes = [146.83, 164.81, 174.61, 196.00, 220.00, 246.94]
    for i in range(n_beats):
        # Metallic percussion on every beat
        hit = _make_noise(0.04, volume=0.15)
        hit = _apply_envelope(hit, attack=0.001, decay=0.03)
        # Heavier hit on downbeats
        if i % 4 == 0:
            heavy = _make_noise(0.06, volume=0.25)
            heavy = _apply_envelope(heavy, attack=0.001, decay=0.04)
            hit = _mix(hit, heavy)
        pad = [0.0] * max(0, int(sr * tempo) - len(hit))
        factory_rhythm.extend(hit)
        factory_rhythm.extend(pad)
        # Melodic note every 2 beats
        if i % 2 == 0:
            freq = rng.choice(factory_notes)
            note = _make_note(freq, tempo * 1.8, 0.2, sr)
            pad_mel = [0.0] * max(0, int(sr * tempo) - len(note))
            factory_mel.extend(note)
            factory_mel.extend(pad_mel)
        else:
            factory_mel.extend([0.0] * int(sr * tempo))
    # Match lengths
    max_len = max(len(factory_mel), len(factory_rhythm))
    factory_mel.extend([0.0] * (max_len - len(factory_mel)))
    factory_rhythm.extend([0.0] * (max_len - len(factory_rhythm)))
    samples = _mix(factory_mel, factory_rhythm)
    path = os.path.join(MUSIC_DIR, "factory.wav")
    _write_wav(path, samples, sr)
    print(f"  Created {path}")

    # --- reactor.wav: tense electronic, pulsing bass, dissonant, ~18s ---
    duration = 18.0
    n = int(sr * duration)
    # Pulsing bass (alternating low frequencies)
    bass_pulse = []
    pulse_period = 0.5  # seconds
    for i in range(n):
        t = i / sr
        cycle = int(t / pulse_period) % 4
        freqs = [55.0, 58.27, 61.74, 58.27]  # A1, Bb1, B1, Bb1 — dissonant
        freq = freqs[cycle]
        vol = 0.2 * (0.5 + 0.5 * math.sin(2 * math.pi * 2 * t))  # tremolo
        bass_pulse.append(vol * math.sin(2 * math.pi * freq * t))
    # High dissonant pad
    pad1 = _make_sine(440.0, duration, 0.06, sr)
    pad2 = _make_sine(466.16, duration, 0.06, sr)  # Bb4 — tritone-ish
    high_pad = _mix(pad1, pad2)
    # Sparse stabs
    stabs = [0.0] * n
    rng = random.Random(88)
    for _ in range(8):
        t = rng.uniform(0, duration - 0.3)
        freq = rng.choice([329.63, 349.23, 369.99, 392.00])
        stab = _apply_envelope(_make_sine(freq, 0.2, 0.2, sr), attack=0.005, decay=0.1, sample_rate=sr)
        start = int(t * sr)
        for j, s in enumerate(stab):
            if start + j < n:
                stabs[start + j] += s
    stabs = [max(-1.0, min(1.0, s)) for s in stabs]
    samples = _mix(_mix(bass_pulse, high_pad), stabs)
    path = os.path.join(MUSIC_DIR, "reactor.wav")
    _write_wav(path, samples, sr)
    print(f"  Created {path}")

    # --- shop.wav: warm peaceful melody, ~16s ---
    tempo = 0.35
    shop_melody_freqs = [
        329.63, 392.00, 440.00, 392.00, 329.63, 293.66, 329.63, 392.00,
        440.00, 523.25, 493.88, 440.00, 392.00, 329.63, 293.66, 329.63,
        261.63, 293.66, 329.63, 392.00, 440.00, 392.00, 349.23, 329.63,
        293.66, 329.63, 392.00, 440.00, 392.00, 349.23, 329.63, 293.66,
        261.63, 329.63, 392.00, 440.00, 523.25, 493.88, 440.00, 392.00,
        329.63, 293.66, 261.63, 293.66, 329.63, 261.63,
    ]
    shop_mel = []
    shop_bass = []
    for freq in shop_melody_freqs:
        note = _make_note(freq, tempo * 0.85, 0.2, sr)
        gap = [0.0] * int(sr * tempo * 0.15)
        shop_mel.extend(note)
        shop_mel.extend(gap)
        bn = _make_bass_note(freq * 0.5, tempo * 0.85, 0.1, sr)
        shop_bass.extend(bn)
        shop_bass.extend(gap)
    samples = _mix(shop_mel, shop_bass)
    path = os.path.join(MUSIC_DIR, "shop.wav")
    _write_wav(path, samples, sr)
    print(f"  Created {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Bit Flippers assets...")
    ensure_dirs()

    print("Sprites:")
    generate_player()
    generate_npc("old_tinker", (80, 180, 80))
    generate_npc("sparks", (200, 160, 50))
    generate_npc("drifter", (160, 100, 180))
    generate_npc("scout", (100, 160, 200))
    generate_enemy_scrap_rat()
    generate_enemy_rust_golem()
    generate_enemy_volt_wraith()

    print("Tiles:")
    generate_tileset()

    print("SFX:")
    generate_sfx()

    print("Music:")
    generate_music()

    print("Done! All assets written to assets/")


if __name__ == "__main__":
    main()
