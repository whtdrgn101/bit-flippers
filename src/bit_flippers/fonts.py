"""Centralized font loading with pixel font + fallback."""
import os

import pygame

_FONT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "pixel.ttf"
)
_HAS_PIXEL_FONT = os.path.isfile(_FONT_PATH)
_cache: dict[int, pygame.font.Font] = {}


def get_font(size: int) -> pygame.font.Font:
    """Load a font at the given size, using pixel.ttf if available."""
    if size in _cache:
        return _cache[size]
    if _HAS_PIXEL_FONT:
        font = pygame.font.Font(_FONT_PATH, size)
    else:
        font = pygame.font.SysFont(None, size)
    _cache[size] = font
    return font
