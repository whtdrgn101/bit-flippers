import random

import pygame
from bit_flippers.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    TILE_SIZE,
    PLAYER_MOVE_SPEED,
    PLAYER_MAX_HP,
    RANDOM_ENCOUNTER_CHANCE,
    MIN_STEPS_BETWEEN_ENCOUNTERS,
)
from bit_flippers.camera import Camera
from bit_flippers.tilemap import TileMap, DIRT
from bit_flippers.sprites import create_placeholder_player, create_placeholder_npc
from bit_flippers.npc import make_npc

MOVE_COOLDOWN = 0.15  # seconds between steps

# Map from pygame key to (dx, dy, direction_name)
DIRECTION_MAP = {
    pygame.K_UP:    (0, -1, "up"),
    pygame.K_DOWN:  (0,  1, "down"),
    pygame.K_LEFT:  (-1, 0, "left"),
    pygame.K_RIGHT: (1,  0, "right"),
}


class OverworldState:
    def __init__(self, game):
        self.game = game
        self.tilemap = TileMap()
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Logical tile position
        self.player_x = 2
        self.player_y = 2

        # Visual pixel position (for smooth interpolation)
        self.player_visual_x = float(self.player_x * TILE_SIZE)
        self.player_visual_y = float(self.player_y * TILE_SIZE)

        self.player_facing = "down"
        self.sprite = create_placeholder_player()

        self.move_timer = 0.0
        self.held_direction = None

        # Player HP (persists across combats)
        self.player_hp = PLAYER_MAX_HP

        # Random encounter tracking
        self.steps_since_encounter = 0

        # NPCs
        self.npcs = self._create_npcs()

        # Enemy NPCs (scripted encounters — removed after defeat)
        self.enemy_npcs = self._create_enemy_npcs()

        # Scripted combat tracking
        self._current_scripted_enemy = None

        # HUD font
        self.hud_font = pygame.font.SysFont(None, 22)

    def _create_npcs(self):
        return [
            make_npc(
                5, 5, "Old Tinker",
                [
                    "Ah, a traveler! Haven't seen one in ages.",
                    "The scrap piles around here hold useful parts.",
                    "Watch out for Rust Golems in the eastern corridors.",
                ],
                body_color=(80, 180, 80),
                facing="down",
            ),
            make_npc(
                16, 4, "Sparks",
                [
                    "Bzzt! I used to be a maintenance bot.",
                    "My circuits are a bit scrambled these days...",
                    "If you find any spare capacitors, I'd be grateful!",
                ],
                body_color=(200, 160, 50),
                facing="left",
            ),
            make_npc(
                22, 7, "Drifter",
                [
                    "Keep your voice down...",
                    "There's something lurking in the south tunnels.",
                    "I've heard strange sounds coming from the walls.",
                ],
                body_color=(160, 100, 180),
                facing="right",
            ),
            make_npc(
                34, 2, "Scout",
                [
                    "I've mapped most of this sector.",
                    "The northwest rooms are relatively safe.",
                    "But the open areas? That's where the rats swarm.",
                ],
                body_color=(100, 160, 200),
                facing="down",
            ),
        ]

    def _create_enemy_npcs(self):
        """Scripted encounter enemies placed on the map."""
        from bit_flippers.combat import ENEMY_TYPES

        return [
            {
                "tile_x": 10,
                "tile_y": 8,
                "enemy_data": ENEMY_TYPES["Rust Golem"],
                "sprite": create_placeholder_npc((160, 60, 40), facing="down"),
                "defeated": False,
            },
            {
                "tile_x": 30,
                "tile_y": 12,
                "enemy_data": ENEMY_TYPES["Volt Wraith"],
                "sprite": create_placeholder_npc((100, 40, 160), facing="left"),
                "defeated": False,
            },
        ]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in DIRECTION_MAP:
                self.held_direction = event.key
                self._try_move(event.key)
                self.move_timer = 0.0
            elif event.key == pygame.K_SPACE:
                self._try_interact()
        elif event.type == pygame.KEYUP:
            if event.key == self.held_direction:
                self.held_direction = None
                self.move_timer = 0.0

    def _try_interact(self):
        """Check the tile the player is facing and interact if an NPC is there."""
        dx, dy = 0, 0
        if self.player_facing == "up":
            dy = -1
        elif self.player_facing == "down":
            dy = 1
        elif self.player_facing == "left":
            dx = -1
        elif self.player_facing == "right":
            dx = 1

        target_x = self.player_x + dx
        target_y = self.player_y + dy

        # Check friendly NPCs
        for npc in self.npcs:
            if npc.tile_x == target_x and npc.tile_y == target_y:
                from bit_flippers.states.dialogue import DialogueState
                self.game.push_state(
                    DialogueState(self.game, npc.name, npc.dialogue_lines)
                )
                return

        # Check enemy NPCs
        for enemy_npc in self.enemy_npcs:
            if (
                not enemy_npc["defeated"]
                and enemy_npc["tile_x"] == target_x
                and enemy_npc["tile_y"] == target_y
            ):
                self._start_scripted_combat(enemy_npc)
                return

    def _start_scripted_combat(self, enemy_npc):
        from bit_flippers.states.combat import CombatState

        self._current_scripted_enemy = enemy_npc
        self.game.push_state(
            CombatState(self.game, enemy_npc["enemy_data"], self)
        )

    def on_combat_victory(self):
        """Called by CombatState when the player wins."""
        if self._current_scripted_enemy is not None:
            self._current_scripted_enemy["defeated"] = True
        self._current_scripted_enemy = None

    def on_combat_end(self):
        """Called by CombatState on defeat or flee."""
        self._current_scripted_enemy = None

    def _start_random_combat(self):
        from bit_flippers.combat import ENEMY_TYPES
        from bit_flippers.states.combat import CombatState

        # Pick a random weak enemy for random encounters
        enemy_data = random.choice([ENEMY_TYPES["Scrap Rat"], ENEMY_TYPES["Scrap Rat"], ENEMY_TYPES["Rust Golem"]])
        self.steps_since_encounter = 0
        self.game.push_state(CombatState(self.game, enemy_data, self))

    def _npc_at(self, tx, ty):
        """Check if any NPC (friendly or enemy) occupies the given tile."""
        for npc in self.npcs:
            if npc.tile_x == tx and npc.tile_y == ty:
                return True
        for enemy_npc in self.enemy_npcs:
            if not enemy_npc["defeated"] and enemy_npc["tile_x"] == tx and enemy_npc["tile_y"] == ty:
                return True
        return False

    def update(self, dt):
        # Handle held-key repeat movement
        if self.held_direction is not None:
            self.move_timer += dt
            if self.move_timer >= MOVE_COOLDOWN:
                self._try_move(self.held_direction)
                self.move_timer -= MOVE_COOLDOWN

        # Smooth visual interpolation toward logical position
        target_x = float(self.player_x * TILE_SIZE)
        target_y = float(self.player_y * TILE_SIZE)
        max_step = PLAYER_MOVE_SPEED * dt

        dx = target_x - self.player_visual_x
        dy = target_y - self.player_visual_y

        if abs(dx) > 0.5:
            self.player_visual_x += min(abs(dx), max_step) * (1 if dx > 0 else -1)
        else:
            self.player_visual_x = target_x

        if abs(dy) > 0.5:
            self.player_visual_y += min(abs(dy), max_step) * (1 if dy > 0 else -1)
        else:
            self.player_visual_y = target_y

        # Update sprite animation
        moving = abs(self.player_visual_x - target_x) > 0.5 or abs(self.player_visual_y - target_y) > 0.5
        if moving:
            self.sprite.set_animation(f"walk_{self.player_facing}")
        else:
            self.sprite.set_animation(f"idle_{self.player_facing}")
        self.sprite.update(dt)

        # Update NPC animations
        for npc in self.npcs:
            npc.update(dt)
        for enemy_npc in self.enemy_npcs:
            if not enemy_npc["defeated"]:
                enemy_npc["sprite"].update(dt)

        # Update camera to follow player visual position (center of sprite)
        self.camera.update(
            int(self.player_visual_x) + TILE_SIZE // 2,
            int(self.player_visual_y) + TILE_SIZE // 2,
            self.tilemap.width_px,
            self.tilemap.height_px,
        )

    def draw(self, screen):
        self.tilemap.draw(screen, self.camera)

        # Draw friendly NPCs
        for npc in self.npcs:
            npc_rect = pygame.Rect(
                npc.tile_x * TILE_SIZE, npc.tile_y * TILE_SIZE, TILE_SIZE, TILE_SIZE
            )
            screen_rect = self.camera.apply(npc_rect)
            screen.blit(npc.image, screen_rect)

        # Draw enemy NPCs
        for enemy_npc in self.enemy_npcs:
            if not enemy_npc["defeated"]:
                npc_rect = pygame.Rect(
                    enemy_npc["tile_x"] * TILE_SIZE,
                    enemy_npc["tile_y"] * TILE_SIZE,
                    TILE_SIZE, TILE_SIZE,
                )
                screen_rect = self.camera.apply(npc_rect)
                screen.blit(enemy_npc["sprite"].image, screen_rect)

        # Draw player sprite at visual position
        player_rect = pygame.Rect(
            int(self.player_visual_x), int(self.player_visual_y), TILE_SIZE, TILE_SIZE
        )
        screen_rect = self.camera.apply(player_rect)
        screen.blit(self.sprite.image, screen_rect)

        # HUD: HP bar (fixed position, not affected by camera)
        self._draw_hud(screen)

    def _draw_hud(self, screen):
        x, y = 10, 10
        bar_width, bar_height = 100, 12
        ratio = self.player_hp / PLAYER_MAX_HP

        # Label
        label = self.hud_font.render("HP", True, (255, 255, 255))
        screen.blit(label, (x, y))

        bar_x = x + 28
        # Background
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y + 2, bar_width, bar_height))
        # Fill
        color = (80, 200, 80) if ratio > 0.5 else (200, 200, 40) if ratio > 0.25 else (200, 60, 60)
        pygame.draw.rect(screen, color, (bar_x, y + 2, int(bar_width * ratio), bar_height))
        # Border
        pygame.draw.rect(screen, (180, 180, 180), (bar_x, y + 2, bar_width, bar_height), 1)

        # HP text
        hp_text = self.hud_font.render(f"{self.player_hp}/{PLAYER_MAX_HP}", True, (255, 255, 255))
        screen.blit(hp_text, (bar_x + bar_width + 6, y + 1))

    def _try_move(self, key):
        dx, dy, facing = DIRECTION_MAP[key]
        self.player_facing = facing

        new_x = self.player_x + dx
        new_y = self.player_y + dy

        if self.tilemap.is_walkable(new_x, new_y) and not self._npc_at(new_x, new_y):
            self.player_x = new_x
            self.player_y = new_y
            self.steps_since_encounter += 1

            # Random encounter check on DIRT tiles
            if (
                self.steps_since_encounter >= MIN_STEPS_BETWEEN_ENCOUNTERS
                and self.tilemap.grid[new_y][new_x] == DIRT
                and random.random() < RANDOM_ENCOUNTER_CHANCE
            ):
                self._start_random_combat()
