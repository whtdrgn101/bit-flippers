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
    SCRAP_BONUS_ITEM_CHANCE,
    PICKUP_MESSAGE_DURATION,
    BASE_XP,
    LEVEL_UP_HP_BONUS,
    COLOR_XP_BAR,
    COLOR_MONEY_TEXT,
)
from bit_flippers.camera import Camera
from bit_flippers.tilemap import TileMap, DIRT, SCRAP
from bit_flippers.sprites import create_placeholder_player, create_placeholder_npc, load_player
from bit_flippers.npc import make_npc
from bit_flippers.items import Inventory

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
        self.sprite = load_player()

        self.move_timer = 0.0
        self.held_direction = None

        # Player HP (persists across combats)
        self.player_max_hp = PLAYER_MAX_HP
        self.player_hp = self.player_max_hp

        # Progression
        self.player_level = 1
        self.player_xp = 0
        self.player_money = 0

        # Inventory
        self.inventory = Inventory()

        # Pickup notification
        self.pickup_message = ""
        self.pickup_message_timer = 0.0

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

        # Start overworld music
        self.game.audio.play_music("overworld")

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
                npc_key="old_tinker",
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
                npc_key="sparks",
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
                npc_key="drifter",
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
                npc_key="scout",
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
            elif event.key == pygame.K_ESCAPE:
                from bit_flippers.states.inventory import InventoryState
                self.game.push_state(InventoryState(self.game, self.inventory, self))
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
        self.game.audio.stop_music()
        self.game.push_state(
            CombatState(self.game, enemy_npc["enemy_data"], self, self.inventory)
        )

    def xp_to_next_level(self):
        """XP required to advance from current level to the next."""
        return self.player_level * BASE_XP

    def _grant_rewards(self, enemy_data):
        """Grant XP and money from a defeated enemy, handling multi-level-ups."""
        self.player_xp += enemy_data.xp_reward
        self.player_money += enemy_data.money_reward

        # Level-up loop (supports multi-level-up from big XP rewards)
        leveled = False
        while self.player_xp >= self.xp_to_next_level():
            self.player_xp -= self.xp_to_next_level()
            self.player_level += 1
            # Increase max HP by 2%, minimum +1
            bonus = max(1, int(self.player_max_hp * LEVEL_UP_HP_BONUS))
            self.player_max_hp += bonus
            # Full heal on level up
            self.player_hp = self.player_max_hp
            leveled = True

        if leveled:
            self.pickup_message = f"Level up! Now level {self.player_level}!"
            self.pickup_message_timer = PICKUP_MESSAGE_DURATION

    def on_combat_victory(self, enemy_data=None):
        """Called by CombatState when the player wins."""
        if enemy_data is not None:
            self._grant_rewards(enemy_data)
        if self._current_scripted_enemy is not None:
            self._current_scripted_enemy["defeated"] = True
        self._current_scripted_enemy = None
        self.game.audio.play_music("overworld")

    def on_combat_end(self):
        """Called by CombatState on defeat or flee."""
        self._current_scripted_enemy = None
        self.game.audio.play_music("overworld")

    def _start_random_combat(self):
        from bit_flippers.combat import ENEMY_TYPES
        from bit_flippers.states.combat import CombatState

        # Pick a random weak enemy for random encounters
        enemy_data = random.choice([ENEMY_TYPES["Scrap Rat"], ENEMY_TYPES["Scrap Rat"], ENEMY_TYPES["Rust Golem"]])
        self.steps_since_encounter = 0
        self.game.audio.stop_music()
        self.game.push_state(CombatState(self.game, enemy_data, self, self.inventory))

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
        # Pickup message timer
        if self.pickup_message_timer > 0:
            self.pickup_message_timer -= dt
            if self.pickup_message_timer <= 0:
                self.pickup_message = ""

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

        # Level label
        level_label = self.hud_font.render(f"Lv {self.player_level}", True, (255, 255, 255))
        screen.blit(level_label, (x, y))
        y += 18

        # HP bar
        hp_ratio = self.player_hp / self.player_max_hp if self.player_max_hp > 0 else 0
        hp_label = self.hud_font.render("HP", True, (255, 255, 255))
        screen.blit(hp_label, (x, y))
        bar_x = x + 28
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y + 2, bar_width, bar_height))
        hp_color = (80, 200, 80) if hp_ratio > 0.5 else (200, 200, 40) if hp_ratio > 0.25 else (200, 60, 60)
        pygame.draw.rect(screen, hp_color, (bar_x, y + 2, int(bar_width * hp_ratio), bar_height))
        pygame.draw.rect(screen, (180, 180, 180), (bar_x, y + 2, bar_width, bar_height), 1)
        hp_text = self.hud_font.render(f"{self.player_hp}/{self.player_max_hp}", True, (255, 255, 255))
        screen.blit(hp_text, (bar_x + bar_width + 6, y + 1))
        y += 18

        # XP bar
        xp_label = self.hud_font.render("XP", True, (255, 255, 255))
        screen.blit(xp_label, (x, y))
        xp_needed = self.xp_to_next_level()
        xp_ratio = self.player_xp / xp_needed if xp_needed > 0 else 0
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y + 2, bar_width, bar_height))
        pygame.draw.rect(screen, COLOR_XP_BAR, (bar_x, y + 2, int(bar_width * xp_ratio), bar_height))
        pygame.draw.rect(screen, (180, 180, 180), (bar_x, y + 2, bar_width, bar_height), 1)
        xp_text = self.hud_font.render(f"{self.player_xp}/{xp_needed}", True, (255, 255, 255))
        screen.blit(xp_text, (bar_x + bar_width + 6, y + 1))
        y += 18

        # Money line
        money_label = self.hud_font.render(f"Scrap: {self.player_money}", True, COLOR_MONEY_TEXT)
        screen.blit(money_label, (x, y))

        # Pickup notification
        if self.pickup_message:
            msg_surf = self.hud_font.render(self.pickup_message, True, (255, 220, 100))
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, 50))

    def _try_move(self, key):
        dx, dy, facing = DIRECTION_MAP[key]
        self.player_facing = facing

        new_x = self.player_x + dx
        new_y = self.player_y + dy

        if self.tilemap.is_walkable(new_x, new_y) and not self._npc_at(new_x, new_y):
            self.player_x = new_x
            self.player_y = new_y
            self.steps_since_encounter += 1

            # Scrap pickup
            if self.tilemap.grid[new_y][new_x] == SCRAP:
                self.tilemap.grid[new_y][new_x] = DIRT
                self.inventory.add("Scrap Metal")
                self.game.audio.play_sfx("pickup")
                msg = "Picked up Scrap Metal!"
                # 25% chance for a bonus consumable
                if random.random() < SCRAP_BONUS_ITEM_CHANCE:
                    bonus = random.choice(["Repair Kit", "Voltage Spike", "Iron Plating"])
                    self.inventory.add(bonus)
                    msg += f" Also found {bonus}!"
                self.pickup_message = msg
                self.pickup_message_timer = PICKUP_MESSAGE_DURATION

            # Random encounter check on DIRT tiles
            if (
                self.steps_since_encounter >= MIN_STEPS_BETWEEN_ENCOUNTERS
                and self.tilemap.grid[new_y][new_x] == DIRT
                and random.random() < RANDOM_ENCOUNTER_CHANCE
            ):
                self._start_random_combat()
