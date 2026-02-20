"""Loader for Tiled (.tmx) map files using pytmx."""

from __future__ import annotations

import os

import pygame
import pytmx
import pytmx.util_pygame

from bit_flippers.settings import TILE_SIZE
from bit_flippers.maps import NPCDef, EnemyNPCDef, DoorDef, IconMarker
from bit_flippers.events import TileEvent

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

    # ------------------------------------------------------------------
    # Entity parsing — read object layers from the TMX
    # ------------------------------------------------------------------

    def _obj_prop(self, obj, key, default=None):
        """Read a custom property from a Tiled object."""
        props = getattr(obj, "properties", {}) or {}
        return props.get(key, default)

    def _obj_color(self, obj):
        """Extract (r, g, b) tuple from color_r/g/b properties."""
        r = int(self._obj_prop(obj, "color_r", 180))
        g = int(self._obj_prop(obj, "color_g", 180))
        b = int(self._obj_prop(obj, "color_b", 180))
        return (r, g, b)

    def _objects_by_type(self, type_name: str):
        """Yield all objects across all object groups matching *type_name*."""
        for obj_group in self.tmx_data.objectgroups:
            for obj in obj_group:
                if getattr(obj, "type", None) == type_name:
                    yield obj

    def get_npcs(self) -> list[NPCDef]:
        npcs = []
        for obj in self._objects_by_type("NPC"):
            tx = int(obj.x) // self.tile_width
            ty = int(obj.y) // self.tile_height
            name = getattr(obj, "name", "") or ""
            dialogue_key = self._obj_prop(obj, "dialogue_key", "")
            sprite_key = self._obj_prop(obj, "sprite_key", "") or None
            sprite_style = self._obj_prop(obj, "sprite_style", "humanoid")
            facing = self._obj_prop(obj, "facing", "down")
            color = self._obj_color(obj)
            npcs.append(NPCDef(
                tile_x=tx, tile_y=ty, name=name,
                dialogue_key=dialogue_key, color=color,
                facing=facing, sprite_key=sprite_key,
                sprite_style=sprite_style,
            ))
        return npcs

    def get_enemies(self) -> list[EnemyNPCDef]:
        enemies = []
        for obj in self._objects_by_type("Enemy"):
            tx = int(obj.x) // self.tile_width
            ty = int(obj.y) // self.tile_height
            enemy_type_key = self._obj_prop(obj, "enemy_type_key", "")
            color = self._obj_color(obj)
            enemies.append(EnemyNPCDef(
                tile_x=tx, tile_y=ty,
                enemy_type_key=enemy_type_key, color=color,
            ))
        return enemies

    def get_doors(self) -> list[DoorDef]:
        doors = []
        for obj in self._objects_by_type("Door"):
            tx = int(obj.x) // self.tile_width
            ty = int(obj.y) // self.tile_height
            target_map_id = self._obj_prop(obj, "target_map_id", "")
            target_spawn_x = int(self._obj_prop(obj, "target_spawn_x", 0))
            target_spawn_y = int(self._obj_prop(obj, "target_spawn_y", 0))
            target_facing = self._obj_prop(obj, "target_facing", "down")
            doors.append(DoorDef(
                x=tx, y=ty,
                target_map_id=target_map_id,
                target_spawn_x=target_spawn_x,
                target_spawn_y=target_spawn_y,
                target_facing=target_facing,
            ))
        return doors

    def get_scrap_positions(self) -> list[tuple[int, int]]:
        positions = []
        for obj in self._objects_by_type("Scrap"):
            tx = int(obj.x) // self.tile_width
            ty = int(obj.y) // self.tile_height
            positions.append((tx, ty))
        return positions

    def get_spawn(self) -> tuple[int, int, str] | None:
        """Return (tile_x, tile_y, facing) for the first Spawn object, or None."""
        for obj in self._objects_by_type("Spawn"):
            tx = int(obj.x) // self.tile_width
            ty = int(obj.y) // self.tile_height
            facing = self._obj_prop(obj, "facing", "down")
            return (tx, ty, facing)
        return None

    def get_icon_markers(self) -> list[IconMarker]:
        markers = []
        for obj in self._objects_by_type("IconMarker"):
            tx = int(obj.x) // self.tile_width
            ty = int(obj.y) // self.tile_height
            icon_type = self._obj_prop(obj, "icon_type", "")
            color = self._obj_color(obj)
            markers.append(IconMarker(x=tx, y=ty, icon_type=icon_type, color=color))
        return markers

    def get_events(self) -> list[TileEvent]:
        """Parse Event objects from TMX object layers."""
        events = []
        for obj in self._objects_by_type("Event"):
            tx = int(obj.x) // self.tile_width
            ty = int(obj.y) // self.tile_height
            event_type = self._obj_prop(obj, "event_type", "custom")
            once_raw = self._obj_prop(obj, "once", True)
            once = once_raw not in (False, "false", "False", 0, "0")
            props = {}
            # Collect event-specific properties
            for key in ("item", "text_key", "damage", "message"):
                val = self._obj_prop(obj, key)
                if val is not None:
                    props[key] = val
            events.append(TileEvent(
                x=tx, y=ty, event_type=event_type,
                properties=props, once=once,
            ))
        return events

    def get_map_properties(self) -> dict:
        """Return map-level custom properties as a dict."""
        props = {}
        if hasattr(self.tmx_data, "properties") and self.tmx_data.properties:
            props.update(self.tmx_data.properties)
        return props
