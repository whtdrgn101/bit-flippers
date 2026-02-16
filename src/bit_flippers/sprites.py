import pygame
from bit_flippers.settings import TILE_SIZE


class SpriteSheet:
    def __init__(self, surface, frame_width, frame_height):
        self.surface = surface
        self.frame_width = frame_width
        self.frame_height = frame_height

    def get_frame(self, col, row):
        """Extract a single frame by grid position."""
        frame = pygame.Surface((self.frame_width, self.frame_height), pygame.SRCALPHA)
        frame.blit(
            self.surface,
            (0, 0),
            (col * self.frame_width, row * self.frame_height,
             self.frame_width, self.frame_height),
        )
        return frame


class AnimatedSprite:
    def __init__(self, animations, default="idle_down"):
        """animations: dict of name -> (frames_list, frame_duration_sec)"""
        self.animations = animations
        self.current_anim = default
        self.frame_index = 0
        self.timer = 0.0

    def set_animation(self, name):
        if name != self.current_anim and name in self.animations:
            self.current_anim = name
            self.frame_index = 0
            self.timer = 0.0

    def update(self, dt):
        frames, duration = self.animations[self.current_anim]
        self.timer += dt
        if self.timer >= duration:
            self.timer -= duration
            self.frame_index = (self.frame_index + 1) % len(frames)

    @property
    def image(self):
        frames, _ = self.animations[self.current_anim]
        return frames[self.frame_index % len(frames)]


def create_placeholder_player():
    """Procedurally generate a simple player sprite with 4 directions x 3 walk frames + idle."""
    size = TILE_SIZE
    body_color = (50, 180, 220)
    eye_color = (255, 255, 255)
    pupil_color = (20, 20, 40)

    # Direction offsets for the "eye" indicator
    # (eye_dx, eye_dy) relative to center, showing which way the character faces
    dir_offsets = {
        "down":  (0, 4),
        "up":    (0, -4),
        "left":  (-4, 0),
        "right": (4, 0),
    }

    animations = {}

    for direction, (edx, edy) in dir_offsets.items():
        frames = []
        for frame_i in range(3):
            surf = pygame.Surface((size, size), pygame.SRCALPHA)

            # Body: rounded-ish rectangle via circle + rect
            body_rect = pygame.Rect(4, 4, size - 8, size - 8)
            pygame.draw.rect(surf, body_color, body_rect, border_radius=6)

            # Slight "bob" animation: shift body up by 1px on frames 0 and 2
            bob = -1 if frame_i != 1 else 1
            body_rect_bob = pygame.Rect(4, 4 + bob, size - 8, size - 8)
            surf.fill((0, 0, 0, 0))
            pygame.draw.rect(surf, body_color, body_rect_bob, border_radius=6)

            # Eye (white circle + dark pupil)
            cx, cy = size // 2, size // 2 + bob
            pygame.draw.circle(surf, eye_color, (cx + edx, cy + edy), 5)
            pygame.draw.circle(surf, pupil_color, (cx + edx + edx // 2, cy + edy + edy // 2), 2)

            # Walk frame variation: slight foot markers on frames 0 and 2
            if frame_i == 0:
                pygame.draw.rect(surf, (30, 140, 180), (8, size - 6 + bob, 5, 3))
            elif frame_i == 2:
                pygame.draw.rect(surf, (30, 140, 180), (size - 13, size - 6 + bob, 5, 3))

            frames.append(surf)

        # Walk animation: 3 frames, 0.12s each
        animations[f"walk_{direction}"] = (frames, 0.12)
        # Idle animation: just the middle frame, slow "breathing"
        animations[f"idle_{direction}"] = ([frames[1]], 0.5)

    return AnimatedSprite(animations, default="idle_down")


def create_placeholder_npc(body_color, facing="down"):
    """Procedurally generate a simple NPC sprite with 4-direction idle frames.

    Different from the player: has a flat-top hat shape and no walk frames.
    """
    size = TILE_SIZE
    eye_color = (255, 255, 255)
    pupil_color = (20, 20, 40)
    hat_color = (
        max(0, body_color[0] - 40),
        max(0, body_color[1] - 40),
        max(0, body_color[2] - 40),
    )

    dir_offsets = {
        "down": (0, 4),
        "up": (0, -4),
        "left": (-4, 0),
        "right": (4, 0),
    }

    animations = {}
    for direction, (edx, edy) in dir_offsets.items():
        surf = pygame.Surface((size, size), pygame.SRCALPHA)

        # Body: slightly wider rectangle
        body_rect = pygame.Rect(3, 8, size - 6, size - 10)
        pygame.draw.rect(surf, body_color, body_rect, border_radius=5)

        # Flat-top hat
        hat_rect = pygame.Rect(5, 2, size - 10, 10)
        pygame.draw.rect(surf, hat_color, hat_rect, border_radius=3)

        # Eye
        cx, cy = size // 2, size // 2 + 2
        pygame.draw.circle(surf, eye_color, (cx + edx, cy + edy), 4)
        pygame.draw.circle(
            surf, pupil_color, (cx + edx + edx // 2, cy + edy + edy // 2), 2
        )

        animations[f"idle_{direction}"] = ([surf], 0.5)

    return AnimatedSprite(animations, default=f"idle_{facing}")


def create_placeholder_enemy(body_color):
    """Procedurally generate an enemy sprite with a spiky/angular look."""
    size = TILE_SIZE
    eye_color = (255, 60, 60)
    pupil_color = (80, 0, 0)

    animations = {}
    for frame_i in range(2):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)

        # Spiky body: diamond-ish shape
        bob = -1 if frame_i == 0 else 1
        cx, cy = size // 2, size // 2 + bob
        points = [
            (cx, 2 + bob),  # top spike
            (size - 4, cy - 4),  # right upper
            (size - 2, cy + 4),  # right lower
            (cx + 6, size - 4 + bob),  # bottom right
            (cx, size - 2 + bob),  # bottom center
            (cx - 6, size - 4 + bob),  # bottom left
            (2, cy + 4),  # left lower
            (4, cy - 4),  # left upper
        ]
        pygame.draw.polygon(surf, body_color, points)
        # Dark outline
        pygame.draw.polygon(
            surf,
            (max(0, body_color[0] - 60), max(0, body_color[1] - 60), max(0, body_color[2] - 60)),
            points,
            2,
        )

        # Angry eyes
        pygame.draw.circle(surf, eye_color, (cx - 5, cy - 2), 4)
        pygame.draw.circle(surf, eye_color, (cx + 5, cy - 2), 4)
        pygame.draw.circle(surf, pupil_color, (cx - 5, cy - 1), 2)
        pygame.draw.circle(surf, pupil_color, (cx + 5, cy - 1), 2)

        animations[f"idle_frame_{frame_i}"] = surf

    # Use 2 frames for a subtle idle bob animation
    animations["idle_down"] = ([animations.pop("idle_frame_0"), animations.pop("idle_frame_1")], 0.4)

    return AnimatedSprite(animations, default="idle_down")
