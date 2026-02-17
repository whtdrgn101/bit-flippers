import copy
import random

import pygame
from bit_flippers.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    TILE_SIZE,
    PLAYER_MOVE_SPEED,
    MIN_STEPS_BETWEEN_ENCOUNTERS,
    SCRAP_BONUS_ITEM_CHANCE,
    PICKUP_MESSAGE_DURATION,
    BASE_XP,
    COLOR_XP_BAR,
    COLOR_SP_BAR,
    COLOR_MONEY_TEXT,
)
from bit_flippers.camera import Camera
from bit_flippers.tilemap import TileMap, DIRT, SCRAP, DOOR
from bit_flippers.sprites import create_placeholder_npc, load_player
from bit_flippers.npc import make_npc
from bit_flippers.items import Inventory
from bit_flippers.maps import MAP_REGISTRY, MapPersistence
from bit_flippers.player_stats import (
    PlayerStats, load_stats, save_stats, points_for_level,
)

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

        # Player stats and skills
        self.stats, self.player_skills = load_stats()

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

        # Inventory — start with a few healing items
        self.inventory = Inventory()
        self.inventory.add("Repair Kit", 3)

        # Pickup notification
        self.pickup_message = ""
        self.pickup_message_timer = 0.0

        # Random encounter tracking
        self.steps_since_encounter = 0

        # Scripted combat tracking
        self._current_scripted_enemy = None

        # HUD font
        self.hud_font = pygame.font.SysFont(None, 22)

        # Map system
        self.current_map_id = "overworld"
        self.map_persistence: dict[str, MapPersistence] = {}
        self.npcs = []
        self.enemy_npcs = []
        self.tilemap = None
        self.camera = None

        # Load the starting map
        self._load_map("overworld")

    def _get_persistence(self, map_id):
        """Get or create persistence data for a map."""
        if map_id not in self.map_persistence:
            self.map_persistence[map_id] = MapPersistence()
        return self.map_persistence[map_id]

    def _save_current_persistence(self):
        """Save scrap/enemy state from the current map to persistence."""
        if self.current_map_id is None or self.tilemap is None:
            return
        persist = self._get_persistence(self.current_map_id)
        map_def = MAP_REGISTRY[self.current_map_id]
        # Record collected scrap: compare current grid vs original
        for y in range(len(map_def.grid)):
            for x in range(len(map_def.grid[y])):
                if map_def.grid[y][x] == SCRAP and self.tilemap.grid[y][x] != SCRAP:
                    persist.collected_scrap.add((x, y))
        # Record defeated enemies
        for enpc in self.enemy_npcs:
            if enpc["defeated"]:
                persist.defeated_enemies.add(enpc["index"])

    def _load_map(self, map_id, spawn_x=None, spawn_y=None, spawn_facing=None):
        """Load a map from the registry, applying persistence."""
        # Save current map state before switching
        self._save_current_persistence()

        map_def = MAP_REGISTRY[map_id]
        self.current_map_id = map_id

        # Deep-copy the grid so modifications (scrap pickup) don't affect the template
        grid = copy.deepcopy(map_def.grid)

        # Apply persistence — remove collected scrap
        persist = self._get_persistence(map_id)
        for (sx, sy) in persist.collected_scrap:
            if 0 <= sy < len(grid) and 0 <= sx < len(grid[sy]):
                grid[sy][sx] = DIRT

        # Create tilemap and camera
        self.tilemap = TileMap(grid, tile_colors_override=map_def.tile_colors_override)
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Set player position
        px = spawn_x if spawn_x is not None else map_def.player_start_x
        py = spawn_y if spawn_y is not None else map_def.player_start_y
        self.player_x = px
        self.player_y = py
        self.player_visual_x = float(px * TILE_SIZE)
        self.player_visual_y = float(py * TILE_SIZE)
        if spawn_facing:
            self.player_facing = spawn_facing

        # Build NPC list from MapDef
        self.npcs = []
        for npc_def in map_def.npcs:
            self.npcs.append(
                make_npc(
                    npc_def.tile_x, npc_def.tile_y, npc_def.name,
                    npc_def.dialogue, body_color=npc_def.color,
                    facing=npc_def.facing, npc_key=npc_def.sprite_key,
                )
            )

        # Build enemy NPC list from MapDef
        from bit_flippers.combat import ENEMY_TYPES
        self.enemy_npcs = []
        for idx, edef in enumerate(map_def.enemies):
            defeated = idx in persist.defeated_enemies
            self.enemy_npcs.append({
                "index": idx,
                "tile_x": edef.tile_x,
                "tile_y": edef.tile_y,
                "enemy_data": ENEMY_TYPES[edef.enemy_type_key],
                "sprite": create_placeholder_npc(edef.color, facing="down"),
                "defeated": defeated,
            })

        # Play map music
        self.game.audio.play_music(map_def.music_track)

    def _handle_door_transition(self):
        """Check if the player is standing on a door and transition if so."""
        map_def = MAP_REGISTRY[self.current_map_id]
        for door in map_def.doors:
            if door.x == self.player_x and door.y == self.player_y:
                self._load_map(
                    door.target_map_id,
                    spawn_x=door.target_spawn_x,
                    spawn_y=door.target_spawn_y,
                    spawn_facing=door.target_facing,
                )
                return

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in DIRECTION_MAP:
                self.held_direction = event.key
                self._try_move(event.key)
                self.move_timer = 0.0
            elif event.key == pygame.K_SPACE:
                self._try_interact()
            elif event.key == pygame.K_ESCAPE:
                from bit_flippers.states.pause_menu import PauseMenuState
                self.game.push_state(PauseMenuState(self.game, self))
            elif event.key == pygame.K_c:
                from bit_flippers.states.character import CharacterScreenState
                self.game.push_state(CharacterScreenState(self.game, self.stats, self.player_skills))
            elif event.key == pygame.K_k:
                from bit_flippers.states.skill_tree import SkillTreeState
                self.game.push_state(SkillTreeState(self.game, self.player_skills, self.stats, self))
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
            CombatState(self.game, enemy_npc["enemy_data"], self, self.inventory, self.player_skills)
        )

    def xp_to_next_level(self):
        """XP required to advance from current level to the next."""
        return self.stats.level * BASE_XP

    def _grant_rewards(self, enemy_data):
        """Grant XP and money from a defeated enemy, handling multi-level-ups."""
        from bit_flippers.skills import skill_points_for_level

        self.stats.xp += enemy_data.xp_reward
        self.stats.money += enemy_data.money_reward

        # Level-up loop (supports multi-level-up from big XP rewards)
        leveled = False
        while self.stats.xp >= self.xp_to_next_level():
            self.stats.xp -= self.xp_to_next_level()
            self.stats.level += 1
            pts = points_for_level(self.stats.level)
            self.stats.unspent_points += pts
            # Grant skill points
            skill_pts = skill_points_for_level(self.stats.level)
            self.player_skills.skill_points += skill_pts
            # Full heal on level up
            self.stats.current_hp = self.stats.max_hp
            self.stats.current_sp = self.stats.max_sp
            leveled = True

        if leveled:
            self.pickup_message = f"Level up! Now level {self.stats.level}!"
            self.pickup_message_timer = PICKUP_MESSAGE_DURATION

        # Auto-save after rewards
        save_stats(self.stats, self.player_skills)

    def on_combat_victory(self, enemy_data=None):
        """Called by CombatState when the player wins."""
        if enemy_data is not None:
            self._grant_rewards(enemy_data)
        if self._current_scripted_enemy is not None:
            self._current_scripted_enemy["defeated"] = True
        self._current_scripted_enemy = None
        map_def = MAP_REGISTRY[self.current_map_id]
        self.game.audio.play_music(map_def.music_track)

    def on_combat_end(self):
        """Called by CombatState on defeat or flee."""
        self._current_scripted_enemy = None
        map_def = MAP_REGISTRY[self.current_map_id]
        self.game.audio.play_music(map_def.music_track)

    def _start_random_combat(self):
        from bit_flippers.combat import ENEMY_TYPES
        from bit_flippers.states.combat import CombatState

        map_def = MAP_REGISTRY[self.current_map_id]
        if not map_def.encounter_table:
            return
        enemy_data = ENEMY_TYPES[random.choice(map_def.encounter_table)]
        self.steps_since_encounter = 0
        self.game.audio.stop_music()
        self.game.push_state(CombatState(self.game, enemy_data, self, self.inventory, self.player_skills))

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
        bar_x = x + 28

        # Level label
        level_label = self.hud_font.render(f"Lv {self.stats.level}", True, (255, 255, 255))
        screen.blit(level_label, (x, y))
        y += 18

        # HP bar
        hp_ratio = self.stats.current_hp / self.stats.max_hp if self.stats.max_hp > 0 else 0
        hp_label = self.hud_font.render("HP", True, (255, 255, 255))
        screen.blit(hp_label, (x, y))
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y + 2, bar_width, bar_height))
        hp_color = (80, 200, 80) if hp_ratio > 0.5 else (200, 200, 40) if hp_ratio > 0.25 else (200, 60, 60)
        pygame.draw.rect(screen, hp_color, (bar_x, y + 2, int(bar_width * hp_ratio), bar_height))
        pygame.draw.rect(screen, (180, 180, 180), (bar_x, y + 2, bar_width, bar_height), 1)
        hp_text = self.hud_font.render(f"{self.stats.current_hp}/{self.stats.max_hp}", True, (255, 255, 255))
        screen.blit(hp_text, (bar_x + bar_width + 6, y + 1))
        y += 18

        # SP bar
        sp_ratio = self.stats.current_sp / self.stats.max_sp if self.stats.max_sp > 0 else 0
        sp_label = self.hud_font.render("SP", True, (255, 255, 255))
        screen.blit(sp_label, (x, y))
        pygame.draw.rect(screen, (40, 40, 40), (bar_x, y + 2, bar_width, bar_height))
        pygame.draw.rect(screen, COLOR_SP_BAR, (bar_x, y + 2, int(bar_width * sp_ratio), bar_height))
        pygame.draw.rect(screen, (140, 140, 140), (bar_x, y + 2, bar_width, bar_height), 1)
        sp_text = self.hud_font.render(f"{self.stats.current_sp}/{self.stats.max_sp}", True, (255, 255, 255))
        screen.blit(sp_text, (bar_x + bar_width + 6, y + 1))
        y += 18

        # XP bar
        xp_label = self.hud_font.render("XP", True, (255, 255, 255))
        screen.blit(xp_label, (x, y))
        xp_needed = self.xp_to_next_level()
        xp_ratio = self.stats.xp / xp_needed if xp_needed > 0 else 0
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y + 2, bar_width, bar_height))
        pygame.draw.rect(screen, COLOR_XP_BAR, (bar_x, y + 2, int(bar_width * xp_ratio), bar_height))
        pygame.draw.rect(screen, (180, 180, 180), (bar_x, y + 2, bar_width, bar_height), 1)
        xp_text = self.hud_font.render(f"{self.stats.xp}/{xp_needed}", True, (255, 255, 255))
        screen.blit(xp_text, (bar_x + bar_width + 6, y + 1))
        y += 18

        # Money line
        money_label = self.hud_font.render(f"Scrap: {self.stats.money}", True, COLOR_MONEY_TEXT)
        screen.blit(money_label, (x, y))
        y += 18

        # Unspent points indicator
        if self.stats.unspent_points > 0:
            pts_label = self.hud_font.render(
                f"+{self.stats.unspent_points} pts [C]", True, (255, 220, 100)
            )
            screen.blit(pts_label, (x, y))
            y += 18

        # Skill points indicator
        if self.player_skills.skill_points > 0:
            skill_label = self.hud_font.render(
                f"+{self.player_skills.skill_points} skill pts [K]", True, (100, 180, 255)
            )
            screen.blit(skill_label, (x, y))
            y += 18

        # Map name
        map_def = MAP_REGISTRY.get(self.current_map_id)
        if map_def and self.current_map_id != "overworld":
            map_label = self.hud_font.render(map_def.display_name, True, (200, 200, 200))
            screen.blit(map_label, (x, y))

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

            # Check for door transition
            if self.tilemap.grid[new_y][new_x] == DOOR:
                self._handle_door_transition()
                return

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
            map_def = MAP_REGISTRY[self.current_map_id]
            if (
                map_def.encounter_table
                and self.steps_since_encounter >= MIN_STEPS_BETWEEN_ENCOUNTERS
                and self.tilemap.grid[new_y][new_x] == DIRT
                and random.random() < map_def.encounter_chance
            ):
                self._start_random_combat()
