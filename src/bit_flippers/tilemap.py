import os

import pygame
from bit_flippers.settings import (
    TILE_SIZE, COLOR_DIRT, COLOR_WALL, COLOR_SCRAP, COLOR_DOOR,
    COLOR_GRASS, COLOR_PATH, COLOR_WATER, COLOR_TREE, COLOR_RUINS,
)

DIRT = 0
WALL = 1
SCRAP = 2
DOOR = 3
GRASS = 4
PATH = 5
WATER = 6
TREE = 7
RUINS = 8

TILE_COLORS = {
    DIRT: COLOR_DIRT,
    WALL: COLOR_WALL,
    SCRAP: COLOR_SCRAP,
    DOOR: COLOR_DOOR,
    GRASS: COLOR_GRASS,
    PATH: COLOR_PATH,
    WATER: COLOR_WATER,
    TREE: COLOR_TREE,
    RUINS: COLOR_RUINS,
}

_IMPASSABLE = frozenset({WALL, WATER, TREE, RUINS})

_ASSET_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, "assets")
)


def _load_tile_surfaces():
    """Load tile textures from assets/tiles/tileset.png. Returns dict or None."""
    path = os.path.join(_ASSET_DIR, "tiles", "tileset.png")
    if not os.path.isfile(path):
        return None
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except pygame.error:
        return None

    surfaces = {}
    for col, tile_id in enumerate((DIRT, WALL, SCRAP, DOOR, GRASS, PATH, WATER, TREE, RUINS)):
        src_x = col * TILE_SIZE
        if src_x + TILE_SIZE > sheet.get_width():
            break
        frame = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), (src_x, 0, TILE_SIZE, TILE_SIZE))
        surfaces[tile_id] = frame
    return surfaces

# fmt: off
DEFAULT_MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,2,0,0,1],
    [1,0,0,1,1,1,1,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,0,0,0,1,0,0,1,1,1,1,1,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,2,0,0,1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,2,1,0,0,0,0,0,0,1,0,2,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,2,0,0,1,1,1,0,0,0,0,0,0,0,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,2,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,2,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,2,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,0,2,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,1,1,1,1,1,1,1],
    [1,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0,0,0,1,1,1,1,1,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,2,0,0,0,0,0,1,0,2,0,0,1,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,0,2,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,1,1,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]
# fmt: on


class TileMap:
    def __init__(self, grid=None, tile_colors_override=None):
        self.grid = grid if grid is not None else DEFAULT_MAP
        self.height_tiles = len(self.grid)
        self.width_tiles = len(self.grid[0])
        self.width_px = self.width_tiles * TILE_SIZE
        self.height_px = self.height_tiles * TILE_SIZE
        self.tile_surfaces = _load_tile_surfaces()
        self._tile_colors = dict(TILE_COLORS)
        if tile_colors_override:
            self._tile_colors.update(tile_colors_override)

    def is_walkable(self, tile_x, tile_y):
        if 0 <= tile_x < self.width_tiles and 0 <= tile_y < self.height_tiles:
            return self.grid[tile_y][tile_x] not in _IMPASSABLE
        return False

    def draw(self, screen, camera):
        # Viewport culling: only draw tiles visible on screen
        start_col = max(0, camera.x // TILE_SIZE)
        end_col = min(self.width_tiles, (camera.x + camera.screen_width) // TILE_SIZE + 1)
        start_row = max(0, camera.y // TILE_SIZE)
        end_row = min(self.height_tiles, (camera.y + camera.screen_height) // TILE_SIZE + 1)

        for row_idx in range(start_row, end_row):
            for col_idx in range(start_col, end_col):
                tile = self.grid[row_idx][col_idx]
                world_rect = pygame.Rect(
                    col_idx * TILE_SIZE, row_idx * TILE_SIZE, TILE_SIZE, TILE_SIZE
                )
                screen_rect = camera.apply(world_rect)
                if self.tile_surfaces and tile in self.tile_surfaces:
                    screen.blit(self.tile_surfaces[tile], screen_rect)
                else:
                    color = self._tile_colors.get(tile, COLOR_DIRT)
                    pygame.draw.rect(screen, color, screen_rect)
