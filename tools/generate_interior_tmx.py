#!/usr/bin/env python3
"""Generate TMX files for all interior maps using the Pipoya tileset.

Reads the grid definitions from maps.py and produces themed TMX files
for: scrap_cave, scrap_factory, reactor_core, volt_forge, iron_shell.

Run: uv run python tools/generate_interior_tmx.py
"""

import os
import sys
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from bit_flippers.maps import MAP_REGISTRY  # noqa: E402
from bit_flippers.tilemap import DIRT, WALL, SCRAP, DOOR  # noqa: E402

BASE_GID = 1


def bc(row, col):
    """BaseChip GID from row, col."""
    return BASE_GID + row * 8 + col


# ---------------------------------------------------------------------------
# Per-theme tile palettes
# ---------------------------------------------------------------------------
# Each theme defines: floor, floor_under_wall, wall, door, scrap_obj,
# and optional decorations

THEMES = {
    "scrap_cave": {
        "floor": bc(0, 2),        # brown earth
        "floor_wall": bc(0, 2),   # same brown under walls
        "wall": bc(54, 0),        # stone wall top
        "wall_front": bc(55, 0),  # stone wall front (bottom-facing)
        "door": bc(76, 2),        # dark arched doorway
        "scrap": bc(5, 2),        # stump/barrel = scrap
        "decor": [bc(6, 0), bc(5, 2)],  # mushroom, stump
        "decor_chance": 0.04,
    },
    "scrap_factory": {
        "floor": bc(0, 1),        # gray stone
        "floor_wall": bc(0, 1),
        "wall": bc(72, 0),        # brown building body
        "wall_front": bc(73, 0),  # building base
        "door": bc(76, 2),
        "scrap": bc(5, 2),
        "decor": [bc(6, 0)],      # crate/barrel
        "decor_chance": 0.03,
    },
    "reactor_core": {
        "floor": bc(0, 1),        # gray stone
        "floor_wall": bc(0, 1),
        "wall": bc(54, 0),        # stone walls
        "wall_front": bc(55, 0),
        "door": bc(76, 2),
        "scrap": bc(5, 2),
        "decor": [],
        "decor_chance": 0.0,
    },
    "volt_forge": {
        "floor": bc(0, 3),        # tan/sandy warm
        "floor_wall": bc(0, 2),   # brown under walls
        "wall": bc(54, 0),        # stone walls
        "wall_front": bc(55, 0),
        "door": bc(76, 2),
        "scrap": bc(5, 2),
        "counter": bc(44, 1),     # wooden counter
        "decor": [bc(5, 0), bc(5, 4)],  # bush/plant, crystal/lamp
        "decor_chance": 0.0,      # manual placement for shops
    },
    "iron_shell": {
        "floor": bc(0, 1),        # gray/cool
        "floor_wall": bc(0, 2),
        "wall": bc(54, 0),
        "wall_front": bc(55, 0),
        "door": bc(76, 2),
        "scrap": bc(5, 2),
        "counter": bc(44, 1),
        "decor": [bc(5, 0), bc(5, 4)],
        "decor_chance": 0.0,
    },
}


def generate_map(map_id):
    """Generate a TMX file for the given interior map."""
    map_def = MAP_REGISTRY[map_id]
    grid = map_def.grid
    theme = THEMES[map_id]
    H = len(grid)
    W = len(grid[0])
    rng = random.Random(hash(map_id))

    ground = [[0] * W for _ in range(H)]
    detail = [[0] * W for _ in range(H)]
    above = [[0] * W for _ in range(H)]

    # --- Ground: floor everywhere ---
    for y in range(H):
        for x in range(W):
            if grid[y][x] == WALL:
                ground[y][x] = theme["floor_wall"]
            else:
                ground[y][x] = theme["floor"]

    # --- Detail: walls, doors, scrap, decorations ---
    for y in range(H):
        for x in range(W):
            tile = grid[y][x]

            if tile == WALL:
                # Check if the tile below is not a wall (bottom-facing wall)
                below_is_wall = (y + 1 < H and grid[y + 1][x] == WALL)
                if not below_is_wall:
                    detail[y][x] = theme["wall_front"]
                else:
                    detail[y][x] = theme["wall"]

            elif tile == DOOR:
                detail[y][x] = theme["door"]

            elif tile == SCRAP:
                detail[y][x] = theme["scrap"]

            elif tile == DIRT:
                # Scatter decorations on empty floor
                if theme["decor"] and rng.random() < theme["decor_chance"]:
                    detail[y][x] = rng.choice(theme["decor"])

    # --- Shop-specific: add counter row if present ---
    if "counter" in theme:
        # Find the counter row from the grid (row with wall segments in middle)
        for y in range(1, H - 1):
            wall_count = sum(1 for x in range(1, W - 1) if grid[y][x] == WALL)
            if 2 <= wall_count <= W - 4:
                # This is the counter row — replace interior walls with counter
                for x in range(1, W - 1):
                    if grid[y][x] == WALL:
                        detail[y][x] = theme["counter"]
                        # Counter is on detail, so set ground to regular floor
                        ground[y][x] = theme["floor"]
                break

    # --- Write TMX ---
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "maps", f"{map_id}.tmx"
    )
    write_tmx(output_path, W, H, ground, detail, above)
    print(f"Generated {map_id}.tmx ({W}x{H} tiles)")


def write_tmx(path, width, height, ground, detail, above):
    """Write a TMX XML file."""

    def csv_data(layer):
        rows = []
        for row in layer:
            rows.append(",".join(str(gid) for gid in row))
        return ",\n".join(rows)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.11.2" orientation="orthogonal" renderorder="right-down"
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
    for mid in ["scrap_cave", "scrap_factory", "reactor_core", "volt_forge", "iron_shell"]:
        generate_map(mid)
