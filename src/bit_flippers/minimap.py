"""Minimap renderer for the overworld."""
import pygame


class Minimap:
    """Renders a small overview of the current map."""

    def __init__(self, tiled_renderer, width=120, height=90):
        self.tiled_renderer = tiled_renderer
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self._blink_timer = 0.0

        # Colors
        self._color_bg = (0, 0, 0, 160)
        self._color_walkable = (50, 50, 60)
        self._color_wall = (100, 100, 110)
        self._color_door = (220, 200, 60)
        self._color_player = (255, 255, 255)

    def update(self, player_tile_x, player_tile_y, doors, dt=0.0):
        """Rebuild the minimap image centered on the player."""
        self._blink_timer += dt

        tr = self.tiled_renderer
        map_w = tr.width_tiles
        map_h = tr.height_tiles

        # Scale: fit entire map into minimap, with each tile as 1-2px
        scale_x = max(1, self.width // max(1, map_w))
        scale_y = max(1, self.height // max(1, map_h))
        scale = min(scale_x, scale_y, 2)  # cap at 2px per tile

        # Compute the pixel size of the rendered map area
        rendered_w = map_w * scale
        rendered_h = map_h * scale

        # Offset to center the map in the minimap surface
        off_x = (self.width - rendered_w) // 2
        off_y = (self.height - rendered_h) // 2

        self.surface.fill(self._color_bg)

        # Draw tiles
        for ty in range(map_h):
            for tx in range(map_w):
                px = off_x + tx * scale
                py = off_y + ty * scale
                if tr.is_walkable(tx, ty):
                    color = self._color_walkable
                else:
                    color = self._color_wall
                if scale == 1:
                    self.surface.set_at((px, py), color)
                else:
                    pygame.draw.rect(self.surface, color, (px, py, scale, scale))

        # Draw doors
        for door in doors:
            px = off_x + door.x * scale
            py = off_y + door.y * scale
            if scale == 1:
                self.surface.set_at((px, py), self._color_door)
            else:
                pygame.draw.rect(self.surface, self._color_door, (px, py, scale, scale))

        # Draw player (blinking white dot)
        if int(self._blink_timer * 3) % 2 == 0:
            px = off_x + player_tile_x * scale
            py = off_y + player_tile_y * scale
            player_size = max(scale, 2)
            pygame.draw.rect(self.surface, self._color_player, (px, py, player_size, player_size))

    def draw(self, screen, x, y):
        """Blit the minimap onto the screen at (x, y)."""
        screen.blit(self.surface, (x, y))
