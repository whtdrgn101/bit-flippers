#!/usr/bin/env python3
"""Generate the overworld TMX map from the existing grid definition.

Reads the _build_overworld() 80x60 grid and produces a multi-layered TMX file
using the Pipoya tileset.

Run: uv run python tools/generate_overworld_tmx.py
"""

import os
import sys
import random

# Add src to path so we can import game modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from bit_flippers.maps import _build_overworld  # noqa: E402
from bit_flippers.tilemap import DIRT, WALL, SCRAP, DOOR, GRASS, PATH, WATER, TREE, RUINS  # noqa: E402

# ---------------------------------------------------------------------------
# Tileset GID layout
# ---------------------------------------------------------------------------
# BaseChip: firstgid=1, 1064 tiles (8 cols x 133 rows)
#   GID = 1 + row*8 + col
# Grass autotile: firstgid=1065, 528 tiles
#   Grass1 set = tiles 0-47 (8x6), Grass1-Dirt1 = tiles 48-95, etc.
#   GID = 1065 + tile_index
# Water static: firstgid=1593, 48 tiles (8x6)
#   GID = 1593 + tile_index

BASE_GID = 1          # BaseChip firstgid
GRASS_GID = 1065      # Grass autotile firstgid
WATER_GID = 1593      # Water static firstgid


def bc(row, col):
    """BaseChip GID from row, col."""
    return BASE_GID + row * 8 + col


# ---------------------------------------------------------------------------
# Tile mapping — verified against basechip catalog and Pipoya sample map
# ---------------------------------------------------------------------------

# Row 0: ground color variants
GROUND = {
    GRASS: bc(0, 0),    # light green grass
    DIRT:  bc(0, 2),    # brown earth
    PATH:  bc(0, 3),    # tan/sandy path
    WALL:  bc(0, 2),    # dirt under walls
    DOOR:  bc(0, 3),    # path under doors
    SCRAP: bc(0, 0),    # grass under scrap
    TREE:  bc(0, 4),    # dark green forest floor
    RUINS: bc(0, 1),    # gray stone under ruins
    WATER: 0,           # handled separately
}

# ---------------------------------------------------------------------------
# Trees: 2x2 tiles — rows 1-2 (verified from sample map + catalog)
# Row 1 = canopy tops, Row 2 = trunks
# ---------------------------------------------------------------------------
TREE_TL = bc(1, 0)   # canopy top-left (green)
TREE_TR = bc(1, 1)   # canopy top-right
TREE_BL = bc(2, 0)   # trunk bottom-left
TREE_BR = bc(2, 1)   # trunk bottom-right

# Darker tree variant (cols 2-3)
TREE2_TL = bc(1, 2)
TREE2_TR = bc(1, 3)
TREE2_BL = bc(2, 2)
TREE2_BR = bc(2, 3)

# ---------------------------------------------------------------------------
# Small objects (rows 5-7 verified from catalog)
# ---------------------------------------------------------------------------
BUSH1 = bc(5, 0)       # green bush
BUSH2 = bc(5, 1)       # smaller bush
FLOWER1 = bc(5, 3)     # yellow flowers
FLOWER2 = bc(6, 4)     # small flowers
ROCK1 = bc(6, 0)       # mushroom/rock
STUMP = bc(5, 2)       # tree stump

# Scrap object — stump/log to represent salvageable material
SCRAP_OBJ = bc(5, 2)

# Ruins marker — skull/bones (row 7 col 3)
RUINS_TILE = bc(7, 3)

# Door — dark arched doorway (row 76, col 2)
DOOR_TILE = bc(76, 2)

# ---------------------------------------------------------------------------
# Building wall tiles (rows 70-73 = brown building, rows 44-45 = front face)
# Verified from Pipoya sample map building layer
# ---------------------------------------------------------------------------
# Brown building walls (top-down: eaves → body → base)
BLDG_ROOF = bc(70, 0)       # roof/eave top edge
BLDG_UPPER = bc(71, 0)      # upper wall
BLDG_BODY = bc(72, 0)       # wall body fill
BLDG_BASE = bc(73, 0)       # wall base/foundation

# Building front face (visible bottom edge facing the player)
# Rows 44-45: left edge, center fill, right edge
FRONT_TL = bc(44, 0)        # front top-left
FRONT_TC = bc(44, 1)        # front top-center
FRONT_TR = bc(44, 2)        # front top-right
FRONT_BL = bc(45, 0)        # front bottom-left
FRONT_BC = bc(45, 1)        # front bottom-center
FRONT_BR = bc(45, 2)        # front bottom-right

# Stone wall tiles (rows 54-55) — for cave entrance / ruins
STONE_TOP = bc(54, 0)       # stone wall top
STONE_BOT = bc(55, 0)       # stone wall front

# ---------------------------------------------------------------------------
# Grass autotile indices (within the Grass1 set, tiles 0-47)
# Layout: 8 cols x 6 rows. Right half (cols 4-7) = standard edges
# ---------------------------------------------------------------------------
G_CENTER    = 14   # full grass fill
G_TOP       = 6    # top edge
G_BOTTOM    = 22   # bottom edge
G_LEFT      = 13   # left edge
G_RIGHT     = 15   # right edge
G_TL        = 5    # top-left corner
G_TR        = 7    # top-right corner
G_BL        = 21   # bottom-left corner
G_BR        = 23   # bottom-right corner
G_INNER_NE  = 28   # inner corners
G_INNER_NW  = 29
G_INNER_SE  = 36
G_INNER_SW  = 37
G_HORIZ     = 1    # horizontal strip
G_VERT      = 8    # vertical strip
G_SINGLE    = 0    # single isolated tile

# Water autotile uses the same layout pattern
W_CENTER    = 14
W_TOP       = 6
W_BOTTOM    = 22
W_LEFT      = 13
W_RIGHT     = 15
W_TL        = 5
W_TR        = 7
W_BL        = 21
W_BR        = 23
W_INNER_NE  = 28
W_INNER_NW  = 29
W_INNER_SE  = 36
W_INNER_SW  = 37


def get_neighbors(grid, x, y, tile_type):
    """Return dict of which cardinal+diagonal neighbors match tile_type."""
    H, W = len(grid), len(grid[0])

    def is_match(nx, ny):
        if 0 <= nx < W and 0 <= ny < H:
            return grid[ny][nx] == tile_type
        return True  # treat out-of-bounds as same (no edge)

    return {
        'n':  is_match(x, y - 1),
        's':  is_match(x, y + 1),
        'w':  is_match(x - 1, y),
        'e':  is_match(x + 1, y),
        'nw': is_match(x - 1, y - 1),
        'ne': is_match(x + 1, y - 1),
        'sw': is_match(x - 1, y + 1),
        'se': is_match(x + 1, y + 1),
    }


def pick_autotile(neighbors, center, top, bottom, left, right,
                   tl, tr, bl, br,
                   inner_ne, inner_nw, inner_se, inner_sw,
                   horiz=None, vert=None, single=None):
    """Pick the right autotile index based on cardinal neighbors."""
    n, s, e, w = neighbors['n'], neighbors['s'], neighbors['e'], neighbors['w']

    if n and s and e and w:
        ne, nw, se, sw = neighbors['ne'], neighbors['nw'], neighbors['se'], neighbors['sw']
        if not ne:
            return inner_ne
        if not nw:
            return inner_nw
        if not se:
            return inner_se
        if not sw:
            return inner_sw
        return center

    # Edges
    if not n and s and e and w:
        return top
    if n and not s and e and w:
        return bottom
    if n and s and not e and w:
        return right
    if n and s and e and not w:
        return left

    # Outer corners
    if not n and not w and s and e:
        return tl
    if not n and not e and s and w:
        return tr
    if not s and not w and n and e:
        return bl
    if not s and not e and n and w:
        return br

    # Thin strips
    if horiz is not None and not n and not s and e and w:
        return horiz
    if vert is not None and n and s and not e and not w:
        return vert
    if single is not None and not n and not s and not e and not w:
        return single

    return center


def _is_wall_neighbor(grid, x, y):
    """Check if tile at (x,y) is WALL or DOOR (part of a building structure)."""
    H, W = len(grid), len(grid[0])
    if 0 <= x < W and 0 <= y < H:
        return grid[y][x] in (WALL, DOOR)
    return False


def generate():
    grid = _build_overworld()
    H = len(grid)
    W = len(grid[0])
    rng = random.Random(42)

    # Layer data: 0 = empty tile in TMX
    ground = [[0] * W for _ in range(H)]
    detail = [[0] * W for _ in range(H)]
    above  = [[0] * W for _ in range(H)]

    # --- Pass 1: Ground layer (base terrain) ---
    for y in range(H):
        for x in range(W):
            tile = grid[y][x]
            if tile == WATER:
                nb = get_neighbors(grid, x, y, WATER)
                idx = pick_autotile(
                    nb, W_CENTER, W_TOP, W_BOTTOM, W_LEFT, W_RIGHT,
                    W_TL, W_TR, W_BL, W_BR,
                    W_INNER_NE, W_INNER_NW, W_INNER_SE, W_INNER_SW,
                )
                ground[y][x] = WATER_GID + idx
            elif tile == GRASS:
                # Grass autotile on detail layer over dirt base
                ground[y][x] = bc(0, 2)  # dirt base
                nb = get_neighbors(grid, x, y, GRASS)
                # Treat TREE and SCRAP as "grass-like" for edge blending
                for key in nb:
                    if not nb[key]:
                        dx = {'w': -1, 'e': 1, 'nw': -1, 'ne': 1, 'sw': -1, 'se': 1}.get(key, 0)
                        dy = {'n': -1, 's': 1, 'nw': -1, 'ne': -1, 'sw': 1, 'se': 1}.get(key, 0)
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < W and 0 <= ny < H and grid[ny][nx] in (TREE, SCRAP):
                            nb[key] = True
                idx = pick_autotile(
                    nb, G_CENTER, G_TOP, G_BOTTOM, G_LEFT, G_RIGHT,
                    G_TL, G_TR, G_BL, G_BR,
                    G_INNER_NE, G_INNER_NW, G_INNER_SE, G_INNER_SW,
                    G_HORIZ, G_VERT, G_SINGLE,
                )
                detail[y][x] = GRASS_GID + idx
            elif tile == TREE:
                ground[y][x] = bc(0, 4)  # dark green forest floor
            elif tile == SCRAP:
                ground[y][x] = GROUND[GRASS]
                detail[y][x] = SCRAP_OBJ
            else:
                ground[y][x] = GROUND.get(tile, bc(0, 2))

    # --- Pass 2: Trees on detail + above layers ---
    placed_trees = set()
    for y in range(H):
        for x in range(W):
            if grid[y][x] == TREE and (x, y) not in placed_trees:
                can_place = (
                    x + 1 < W and y + 1 < H
                    and grid[y][x + 1] == TREE
                    and grid[y + 1][x] == TREE
                    and grid[y + 1][x + 1] == TREE
                    and (x + 1, y) not in placed_trees
                    and (x, y + 1) not in placed_trees
                    and (x + 1, y + 1) not in placed_trees
                )
                if can_place:
                    if rng.random() < 0.6:
                        ttl, ttr, tbl, tbr = TREE_TL, TREE_TR, TREE_BL, TREE_BR
                    else:
                        ttl, ttr, tbl, tbr = TREE2_TL, TREE2_TR, TREE2_BL, TREE2_BR
                    # Canopy on above layer (overlaps player)
                    above[y][x] = ttl
                    above[y][x + 1] = ttr
                    # Trunks on detail layer
                    detail[y + 1][x] = tbl
                    detail[y + 1][x + 1] = tbr
                    placed_trees.update([(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)])

    # Remaining single TREE tiles get a bush
    for y in range(H):
        for x in range(W):
            if grid[y][x] == TREE and (x, y) not in placed_trees:
                detail[y][x] = BUSH1 if rng.random() < 0.5 else BUSH2
                placed_trees.add((x, y))

    # --- Pass 3: Scatter decorations on GRASS tiles ---
    for y in range(H):
        for x in range(W):
            if grid[y][x] == GRASS and detail[y][x] == 0 and rng.random() < 0.03:
                detail[y][x] = rng.choice([FLOWER1, FLOWER2, ROCK1])

    # --- Pass 4: Building walls with proper tile selection ---
    for y in range(H):
        for x in range(W):
            if grid[y][x] == WALL:
                above_is_wall = _is_wall_neighbor(grid, x, y - 1)
                below_is_wall = _is_wall_neighbor(grid, x, y + 1)
                left_is_wall = _is_wall_neighbor(grid, x - 1, y)
                right_is_wall = _is_wall_neighbor(grid, x + 1, y)

                if not above_is_wall:
                    # Top row of building → roof on above layer
                    above[y][x] = BLDG_ROOF
                    detail[y][x] = BLDG_BODY
                elif not below_is_wall:
                    # Bottom row (front face) → visible wall front
                    if not left_is_wall:
                        detail[y][x] = FRONT_BL
                    elif not right_is_wall:
                        detail[y][x] = FRONT_BR
                    else:
                        detail[y][x] = FRONT_BC
                else:
                    # Middle wall body
                    detail[y][x] = BLDG_BODY

            elif grid[y][x] == DOOR:
                # Door = dark archway entrance on the building front
                detail[y][x] = DOOR_TILE

            elif grid[y][x] == RUINS:
                detail[y][x] = RUINS_TILE

    # --- Write TMX ---
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "maps", "overworld.tmx"
    )
    write_tmx(output_path, W, H, ground, detail, above)
    print(f"Generated {output_path} ({W}x{H} tiles)")


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
 <tileset firstgid="{GRASS_GID}" source="tilesets/grass_autotile.tsx"/>
 <tileset firstgid="{WATER_GID}" source="tilesets/water_static.tsx"/>
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
