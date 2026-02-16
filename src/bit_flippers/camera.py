import pygame


class Camera:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x = 0
        self.y = 0

    def update(self, target_x, target_y, map_width_px, map_height_px):
        """Center on target, clamped so we never show void beyond the map."""
        self.x = target_x - self.screen_width // 2
        self.y = target_y - self.screen_height // 2

        # Clamp to map edges
        self.x = max(0, min(self.x, map_width_px - self.screen_width))
        self.y = max(0, min(self.y, map_height_px - self.screen_height))

    def apply(self, rect):
        """Offset a world-space rect into screen-space."""
        return pygame.Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)
