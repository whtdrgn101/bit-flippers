#!/usr/bin/env python3
"""Generate an upgraded Tinker's Shop TMX using the Pipoya tileset.

Replaces the placeholder tinker_shop.tmx with a richer version using
BaseChip tiles for indoor floors, stone walls, counter, and decoration.

Run: uv run python tools/generate_tinker_shop_tmx.py
"""

import os

# ---------------------------------------------------------------------------
# Tileset GID layout (same as overworld generator)
# ---------------------------------------------------------------------------
BASE_GID = 1  # BaseChip firstgid


def bc(row, col):
    """BaseChip GID from row, col."""
    return BASE_GID + row * 8 + col


# ---------------------------------------------------------------------------
# Tile definitions — verified against basechip catalog
# ---------------------------------------------------------------------------
# Floor: row 0 ground colors
FLOOR_WOOD = bc(0, 3)      # tan/sandy — warm wood floor feel
FLOOR_DARK = bc(0, 2)      # brown — under walls

# Walls: rows 54-55 = stone block tiles (gray stone)
WALL_STONE = bc(54, 0)     # gray stone wall block
WALL_STONE_B = bc(55, 0)   # gray stone wall lower

# Counter: row 44-45 = wooden building front (works as wooden counter)
COUNTER_TOP = bc(44, 1)    # wooden plank surface
COUNTER_BOT = bc(45, 1)    # wooden plank base

# Objects (verified from catalog)
BARREL = bc(5, 2)          # tree stump / barrel
SHELF = bc(5, 0)           # green bush = potted plant / shelf decoration
CRATE = bc(6, 0)           # mushroom = basket / crate
LAMP = bc(5, 4)            # blue crystal = lamp/light
FLOWER_POT = bc(5, 3)      # yellow flowers = potted plant

# Door — dark arched doorway (row 76, col 2)
DOOR_TILE = bc(76, 2)

# Shop dimensions (matches existing grid)
W, H = 12, 10


def generate():
    ground = [[0] * W for _ in range(H)]
    detail = [[0] * W for _ in range(H)]
    above = [[0] * W for _ in range(H)]

    # --- Ground layer: floor everywhere ---
    for y in range(H):
        for x in range(W):
            ground[y][x] = FLOOR_WOOD

    # Walls get darker floor base
    for y in range(H):
        for x in range(W):
            if _is_perimeter(x, y):
                ground[y][x] = FLOOR_DARK

    # --- Detail layer: walls, counter, door, furniture ---
    # Perimeter walls
    for x in range(W):
        detail[0][x] = WALL_STONE      # top wall
        detail[H - 1][x] = WALL_STONE  # bottom wall
    for y in range(H):
        detail[y][0] = WALL_STONE      # left wall
        detail[y][W - 1] = WALL_STONE  # right wall

    # Counter (row 3, cols 3-7)
    for x in range(3, 8):
        detail[3][x] = COUNTER_TOP

    # Door at (5, 8) — arched doorway
    detail[8][5] = DOOR_TILE
    detail[8][5] = 0

    # Shelves/display along top wall (row 1, inside)
    detail[1][2] = SHELF
    detail[1][4] = SHELF
    detail[1][7] = SHELF
    detail[1][9] = SHELF

    # Barrels/crates in corners
    detail[1][1] = BARREL
    detail[1][10] = BARREL
    detail[7][1] = CRATE
    detail[7][10] = CRATE

    # Decorative items
    detail[5][2] = FLOWER_POT
    detail[5][9] = LAMP

    # --- Write TMX ---
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "maps", "tinker_shop.tmx"
    )
    write_tmx(output_path, W, H, ground, detail, above)
    print(f"Generated {output_path} ({W}x{H} tiles)")


def _is_perimeter(x, y):
    """Check if position is on the perimeter wall."""
    return x == 0 or x == W - 1 or y == 0 or y == H - 1


def write_tmx(path, width, height, ground, detail, above):
    """Write a TMX XML file."""

    def csv_data(layer):
        rows = []
        for row in layer:
            rows.append(",".join(str(gid) for gid in row))
        return ",\n".join(rows)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.11" orientation="orthogonal" renderorder="right-down"
     width="{width}" height="{height}" tilewidth="32" tileheight="32"
     infinite="0" nextlayerid="4" nextobjectid="1">
 <tileset firstgid="{BASE_GID}" source="tilesets/basechip.tsx"/>
 <layer id="1" name="ground" width="{width}" height="{height}">
  <data encoding="csv">
{csv_data(ground)}
</data>
 </layer>
 <layer id="2" name="detail" width="{width}" height="{height}">
  <data encoding="csv">
{csv_data(detail)}
</data>
 </layer>
 <layer id="3" name="above" width="{width}" height="{height}">
  <data encoding="csv">
{csv_data(above)}
</data>
 </layer>
</map>"""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(xml)


if __name__ == "__main__":
    generate()
