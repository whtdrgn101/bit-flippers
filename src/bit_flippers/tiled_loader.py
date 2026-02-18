"""Loader for Tiled (.tmx) map files using pytmx."""

import os

import pygame
import pytmx
import pytmx.util_pygame

from bit_flippers.settings import TILE_SIZE

_ASSET_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, "assets")
)

# Layer names that render above sprites (e.g. tree canopies, rooftops)
_FRINGE_NAMES = frozenset({"fringe", "above", "overlay"})


class TiledMapRenderer:
    """Renders a Tiled (.tmx) map with support for below/above sprite layers."""

    def __init__(self, tmx_file: str):
        path = os.path.join(_ASSET_DIR, "maps", tmx_file)
        self.tmx_data = pytmx.util_pygame.load_pygame(path)

        self.width_tiles = self.tmx_data.width
        self.height_tiles = self.tmx_data.height
        self.tile_width = self.tmx_data.tilewidth
        self.tile_height = self.tmx_data.tileheight
        self.width_px = self.width_tiles * self.tile_width
        self.height_px = self.height_tiles * self.tile_height

        # Categorize tile layers by index into below-sprite and above-sprite groups
        # get_tile_image() takes a layer index (int)
        # visible_tile_layers yields layer indices
        self._below_layers = []
        self._above_layers = []
        for layer_idx in self.tmx_data.visible_tile_layers:
            layer = self.tmx_data.layers[layer_idx]
            name = layer.name.lower().strip()
            if name in _FRINGE_NAMES:
                self._above_layers.append(layer_idx)
            else:
                self._below_layers.append(layer_idx)

        # Build walkability grid from tile properties or collision objects
        self._walkable = self._build_walkability()

    def _build_walkability(self) -> list[list[bool]]:
        """Build a 2D grid of walkability flags.

        A tile is not walkable if:
        - Any tile layer has a tile with property 'walkable' set to False/'false'
        - A collision object layer contains a rectangle covering the tile
        """
        walkable = [[True] * self.width_tiles for _ in range(self.height_tiles)]

        # Check tile properties on all tile layers
        for layer in self.tmx_data.layers:
            if not hasattr(layer, 'data'):
                continue
            for x, y, gid in layer:
                if gid == 0:
                    continue
                props = self.tmx_data.get_tile_properties_by_gid(gid)
                if props:
                    w = props.get("walkable")
                    if w is False or w == "false" or w == "False":
                        walkable[y][x] = False

        # Check object layers named "collision" or "collisions"
        for obj_group in self.tmx_data.objectgroups:
            if obj_group.name.lower().strip() in ("collision", "collisions"):
                for obj in obj_group:
                    # Convert pixel coords to tile coords
                    tx_start = int(obj.x) // self.tile_width
                    ty_start = int(obj.y) // self.tile_height
                    tx_end = (int(obj.x) + int(obj.width) - 1) // self.tile_width
                    ty_end = (int(obj.y) + int(obj.height) - 1) // self.tile_height
                    for ty in range(max(0, ty_start), min(self.height_tiles, ty_end + 1)):
                        for tx in range(max(0, tx_start), min(self.width_tiles, tx_end + 1)):
                            walkable[ty][tx] = False

        return walkable

    def is_walkable(self, tile_x: int, tile_y: int) -> bool:
        if 0 <= tile_x < self.width_tiles and 0 <= tile_y < self.height_tiles:
            return self._walkable[tile_y][tile_x]
        return False

    def _draw_layers(self, screen, camera, layer_indices):
        """Draw a set of tile layers with viewport culling."""
        start_col = max(0, camera.x // self.tile_width)
        end_col = min(self.width_tiles, (camera.x + camera.screen_width) // self.tile_width + 1)
        start_row = max(0, camera.y // self.tile_height)
        end_row = min(self.height_tiles, (camera.y + camera.screen_height) // self.tile_height + 1)

        for layer_idx in layer_indices:
            for row in range(start_row, end_row):
                for col in range(start_col, end_col):
                    image = self.tmx_data.get_tile_image(col, row, layer_idx)
                    if image:
                        world_rect = pygame.Rect(
                            col * self.tile_width, row * self.tile_height,
                            self.tile_width, self.tile_height,
                        )
                        screen_rect = camera.apply(world_rect)
                        screen.blit(image, screen_rect)

    def draw_below(self, screen, camera):
        """Draw tile layers that render below sprites (ground, detail)."""
        self._draw_layers(screen, camera, self._below_layers)

    def draw_above(self, screen, camera):
        """Draw tile layers that render above sprites (fringe, canopy)."""
        self._draw_layers(screen, camera, self._above_layers)
