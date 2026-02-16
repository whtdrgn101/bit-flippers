#!/usr/bin/env python3
"""Generate pixel art PNGs for Bit Flippers.

Run:  python tools/generate_assets.py

Uses SDL dummy video driver for headless operation.
All outputs go under assets/ relative to the project root.
"""
import os
import random
import sys

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
    sheet = pygame.Surface((TILE * 3, TILE), pygame.SRCALPHA)

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

    # SCRAP tile — metallic shine
    scrap_base = (204, 180, 60)
    scrap_frame = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    rng3 = random.Random(300)
    for x in range(TILE):
        for y in range(TILE):
            variation = rng3.randint(-12, 12)
            c = (
                max(0, min(255, scrap_base[0] + variation)),
                max(0, min(255, scrap_base[1] + variation)),
                max(0, min(255, scrap_base[2] + variation)),
            )
            scrap_frame.set_at((x, y), c)

    # Diagonal metallic shine lines
    for offset in range(0, TILE * 2, 8):
        for i in range(3):
            x = offset - TILE + i
            y = i
            while x < TILE and y < TILE:
                if 0 <= x < TILE and 0 <= y < TILE:
                    highlight_px(scrap_frame, x, y, scrap_base, 45)
                x += 1
                y += 1

    # Metallic rivets
    rivet_color = (170, 150, 40)
    for rx, ry in [(4, 4), (28, 4), (4, 28), (28, 28), (16, 16)]:
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if abs(dx) + abs(dy) <= 1:
                    px, py = rx + dx, ry + dy
                    if 0 <= px < TILE and 0 <= py < TILE:
                        scrap_frame.set_at((px, py), rivet_color)

    sheet.blit(scrap_frame, (TILE * 2, 0))

    path = os.path.join(TILES_DIR, "tileset.png")
    pygame.image.save(sheet, path)
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

    print("Done! All assets written to assets/")


if __name__ == "__main__":
    main()
