import random

import pygame
from bit_flippers.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    VIEWPORT_HEIGHT,
    HUD_HEIGHT,
    HUD_Y,
    COLOR_HUD_BG,
    COLOR_HUD_BORDER,
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
from bit_flippers.sprites import create_placeholder_npc, load_player
from bit_flippers.npc import make_npc
from bit_flippers.items import Inventory, Equipment, WEAPONSMITH_STOCK, ARMORSMITH_STOCK
from bit_flippers.maps import MAP_REGISTRY, MapPersistence
from bit_flippers.player_stats import PlayerStats, points_for_level
from bit_flippers.save import save_game
from bit_flippers.strings import get_npc_dialogue

MOVE_COOLDOWN = 0.15  # seconds between steps

# Map from pygame key to (dx, dy, direction_name)
DIRECTION_MAP = {
    pygame.K_UP:    (0, -1, "up"),
    pygame.K_DOWN:  (0,  1, "down"),
    pygame.K_LEFT:  (-1, 0, "left"),
    pygame.K_RIGHT: (1,  0, "right"),
}


class OverworldState:
    def __init__(self, game, save_data=None):
        self.game = game

        # Pickup notification
        self.pickup_message = ""
        self.pickup_message_timer = 0.0

        # Scripted combat tracking
        self._current_scripted_enemy = None

        # HUD font
        self.hud_font = pygame.font.SysFont(None, 22)

        self.sprite = load_player("pipoya-characters/Male/Male 01-1")
        self.move_timer = 0.0
        self.held_direction = None

        # Map system
        self.npcs = []
        self.enemy_npcs = []
        self.tiled_renderer = None
        self.scrap_remaining = set()
        self.camera = None

        # TMX-first resolved map data (set by _load_map)
        self._current_doors = []
        self._all_scrap_positions = []
        self._current_icon_markers = []
        self._current_encounter_table = []
        self._current_encounter_chance = 0.0
        self._current_music_track = "overworld"
        self._current_display_name = ""

        # Quest tracking — enemies defeated this combat session
        self.last_combat_defeated_names: list[str] = []

        if save_data is not None:
            self._restore_from_save(save_data)
        else:
            self._fresh_start()

    def _fresh_start(self):
        """Initialize a brand-new game."""
        from bit_flippers.skills import PlayerSkills
        from bit_flippers.quests import PlayerQuests

        self.stats = PlayerStats()
        self.player_skills = PlayerSkills()
        self.inventory = Inventory()
        self.equipment = Equipment()
        self.player_quests = PlayerQuests()
        self.inventory.add("Repair Kit", 3)
        self.player_x = 2
        self.player_y = 2
        self.player_visual_x = float(self.player_x * TILE_SIZE)
        self.player_visual_y = float(self.player_y * TILE_SIZE)
        self.player_facing = "down"
        self.steps_since_encounter = 0
        self.current_map_id = "overworld"
        self.map_persistence: dict[str, MapPersistence] = {}
        self._load_map("overworld")

    def _restore_from_save(self, save_data):
        """Restore full game state from save data dict."""
        from bit_flippers.skills import PlayerSkills
        from bit_flippers.quests import PlayerQuests

        # Stats
        stats_data = save_data.get("stats", {})
        self.stats = PlayerStats(**{
            k: v for k, v in stats_data.items()
            if k in PlayerStats.__dataclass_fields__
        })

        # Skills
        skills_data = save_data.get("skills")
        self.player_skills = PlayerSkills.from_dict(skills_data) if skills_data else PlayerSkills()

        # Inventory
        inv_data = save_data.get("inventory")
        self.inventory = Inventory.from_dict(inv_data) if inv_data else Inventory()

        # Equipment
        eq_data = save_data.get("equipment")
        self.equipment = Equipment.from_dict(eq_data) if eq_data else Equipment()

        # Quests
        quest_data = save_data.get("quests")
        self.player_quests = PlayerQuests.from_dict(quest_data) if quest_data else PlayerQuests()

        # Position
        self.current_map_id = save_data.get("current_map_id", "overworld")
        self.player_x = save_data.get("player_x", 2)
        self.player_y = save_data.get("player_y", 2)
        self.player_visual_x = float(self.player_x * TILE_SIZE)
        self.player_visual_y = float(self.player_y * TILE_SIZE)
        self.player_facing = save_data.get("player_facing", "down")
        self.steps_since_encounter = save_data.get("steps_since_encounter", 0)

        # Map persistence
        self.map_persistence: dict[str, MapPersistence] = {}
        for map_id, pdata in save_data.get("map_persistence", {}).items():
            mp = MapPersistence()
            mp.collected_scrap = {tuple(c) for c in pdata.get("collected_scrap", [])}
            mp.defeated_enemies = set(pdata.get("defeated_enemies", []))
            self.map_persistence[map_id] = mp

        self._load_map(
            self.current_map_id,
            spawn_x=self.player_x,
            spawn_y=self.player_y,
            spawn_facing=self.player_facing,
        )

    def _get_persistence(self, map_id):
        """Get or create persistence data for a map."""
        if map_id not in self.map_persistence:
            self.map_persistence[map_id] = MapPersistence()
        return self.map_persistence[map_id]

    def _save_current_persistence(self):
        """Save scrap/enemy state from the current map to persistence."""
        if self.current_map_id is None:
            return
        persist = self._get_persistence(self.current_map_id)
        persist.collected_scrap = set(self._all_scrap_positions) - self.scrap_remaining
        # Record defeated enemies
        for enpc in self.enemy_npcs:
            if enpc["defeated"]:
                persist.defeated_enemies.add(enpc["index"])

    def _load_map(self, map_id, spawn_x=None, spawn_y=None, spawn_facing=None):
        """Load a map from the registry, applying persistence.

        TMX-first: if the TMX contains objects of a given type, use those.
        Otherwise fall back to the MapDef in the registry.
        """
        # Save current map state before switching
        self._save_current_persistence()

        map_def = MAP_REGISTRY[map_id]
        self.current_map_id = map_id

        # Load Tiled renderer
        from bit_flippers.tiled_loader import TiledMapRenderer
        self.tiled_renderer = TiledMapRenderer(map_def.tmx_file)

        # --- TMX-first entity resolution ---
        tmx_npcs = self.tiled_renderer.get_npcs()
        tmx_enemies = self.tiled_renderer.get_enemies()
        tmx_doors = self.tiled_renderer.get_doors()
        tmx_scrap = self.tiled_renderer.get_scrap_positions()
        tmx_spawn = self.tiled_renderer.get_spawn()
        tmx_icons = self.tiled_renderer.get_icon_markers()
        tmx_props = self.tiled_renderer.get_map_properties()

        npc_defs = tmx_npcs if tmx_npcs else map_def.npcs
        enemy_defs = tmx_enemies if tmx_enemies else map_def.enemies
        self._current_doors = tmx_doors if tmx_doors else map_def.doors
        scrap_positions = tmx_scrap if tmx_scrap else list(map_def.scrap_positions)
        self._all_scrap_positions = scrap_positions
        self._current_icon_markers = tmx_icons if tmx_icons else map_def.icon_markers
        self._current_encounter_table = (
            tmx_props.get("encounter_table", "").split(",")
            if tmx_props.get("encounter_table")
            else map_def.encounter_table
        )
        # Strip whitespace from encounter table entries
        self._current_encounter_table = [e.strip() for e in self._current_encounter_table if e.strip()]
        self._current_encounter_chance = (
            float(tmx_props["encounter_chance"])
            if "encounter_chance" in tmx_props
            else map_def.encounter_chance
        )
        self._current_music_track = tmx_props.get("music_track", map_def.music_track)
        self._current_display_name = tmx_props.get("display_name", map_def.display_name)

        # Build the set of scrap positions still available on this map
        persist = self._get_persistence(map_id)
        self.scrap_remaining = set(scrap_positions) - persist.collected_scrap

        self.camera = Camera(SCREEN_WIDTH, VIEWPORT_HEIGHT)

        # Set player position — TMX spawn when no explicit coords provided
        if spawn_x is not None:
            px, py = spawn_x, spawn_y
        elif tmx_spawn is not None:
            px, py = tmx_spawn[0], tmx_spawn[1]
            if spawn_facing is None:
                spawn_facing = tmx_spawn[2]
        else:
            px, py = map_def.player_start_x, map_def.player_start_y
        # Spawn validation: if position isn't walkable (e.g. map redesigned), fall back
        if not self.tiled_renderer.is_walkable(px, py):
            px = map_def.player_start_x
            py = map_def.player_start_y
        self.player_x = px
        self.player_y = py
        self.player_visual_x = float(px * TILE_SIZE)
        self.player_visual_y = float(py * TILE_SIZE)
        if spawn_facing:
            self.player_facing = spawn_facing

        # Build NPC list, resolving dialogue from strings.json
        self.npcs = []
        for npc_def in npc_defs:
            dialogue = get_npc_dialogue(npc_def.dialogue_key)
            self.npcs.append(
                make_npc(
                    npc_def.tile_x, npc_def.tile_y, npc_def.name,
                    dialogue, body_color=npc_def.color,
                    facing=npc_def.facing, npc_key=npc_def.sprite_key,
                    sprite_style=getattr(npc_def, "sprite_style", "humanoid"),
                )
            )

        # Build enemy NPC list
        from bit_flippers.combat import ENEMY_TYPES
        self.enemy_npcs = []
        for idx, edef in enumerate(enemy_defs):
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
        self.game.audio.play_music(self._current_music_track)

    def _handle_door_transition(self):
        """Check if the player is standing on a door and transition if so."""
        for door in self._current_doors:
            if door.x == self.player_x and door.y == self.player_y:
                self._load_map(
                    door.target_map_id,
                    spawn_x=door.target_spawn_x,
                    spawn_y=door.target_spawn_y,
                    spawn_facing=door.target_facing,
                )
                # Update quest visit tracking for the new map
                self.player_quests.update_visit(door.target_map_id)
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
            elif event.key == pygame.K_i:
                from bit_flippers.states.inventory import InventoryState
                self.game.push_state(InventoryState(self.game, self.inventory, self))
            elif event.key == pygame.K_c:
                from bit_flippers.states.character import CharacterScreenState
                self.game.push_state(CharacterScreenState(self.game, self.stats, self.player_skills, self))
            elif event.key == pygame.K_k:
                from bit_flippers.states.skill_tree import SkillTreeState
                self.game.push_state(SkillTreeState(self.game, self.player_skills, self.stats, self))
            elif event.key == pygame.K_q:
                from bit_flippers.states.quest_log import QuestLogState
                self.game.push_state(QuestLogState(self.game, self.player_quests))
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
                from bit_flippers.quests import QUEST_REGISTRY
                from bit_flippers.strings import get_npc_dialogue as _get_dialogue

                on_close = None
                dialogue_lines = npc.dialogue_lines

                # Check if this NPC has a quest interaction
                quest_info = self.player_quests.get_npc_quest(npc.name)
                if quest_info is not None:
                    qid, qstate = quest_info
                    qdef = QUEST_REGISTRY[qid]
                    if qstate == "available":
                        lines = _get_dialogue(qdef.dialogue_offer)
                        if lines:
                            dialogue_lines = lines
                        def on_close(_ow=self, _qid=qid):
                            _ow.player_quests.accept(_qid)
                            _ow.pickup_message = f"Quest accepted: {QUEST_REGISTRY[_qid].name}"
                            _ow.pickup_message_timer = PICKUP_MESSAGE_DURATION
                    elif qstate == "active":
                        # Update fetch objectives before showing dialogue
                        self.player_quests.update_fetch(self.inventory)
                        lines = _get_dialogue(qdef.dialogue_active)
                        if lines:
                            dialogue_lines = lines
                    elif qstate == "complete":
                        lines = _get_dialogue(qdef.dialogue_complete)
                        if lines:
                            dialogue_lines = lines
                        def on_close(_ow=self, _qid=qid):
                            _ow.player_quests.claim_rewards(_qid, _ow)
                            _ow.pickup_message = f"Quest complete: {QUEST_REGISTRY[_qid].name}!"
                            _ow.pickup_message_timer = PICKUP_MESSAGE_DURATION
                            save_game(_ow)
                    elif qstate == "done":
                        lines = _get_dialogue(qdef.dialogue_done)
                        if lines:
                            dialogue_lines = lines

                # Shop NPCs still open shop after quest dialogue
                if on_close is None:
                    if npc.name == "Shopkeeper":
                        def on_close(_ow=self):
                            from bit_flippers.states.shop import ShopState
                            _ow.game.push_state(ShopState(_ow.game, _ow))
                    elif npc.name == "Weaponsmith":
                        def on_close(_ow=self):
                            from bit_flippers.states.shop import ShopState
                            _ow.game.push_state(ShopState(_ow.game, _ow, stock_list=WEAPONSMITH_STOCK))
                    elif npc.name == "Armorsmith":
                        def on_close(_ow=self):
                            from bit_flippers.states.shop import ShopState
                            _ow.game.push_state(ShopState(_ow.game, _ow, stock_list=ARMORSMITH_STOCK))

                self.game.push_state(
                    DialogueState(self.game, npc.name, dialogue_lines, on_close=on_close)
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
        save_game(self)

    def on_combat_victory(self, enemy_data=None):
        """Called by CombatState when the player wins."""
        if enemy_data is not None:
            self._grant_rewards(enemy_data)
            # Update quest kill tracking
            self.player_quests.update_kill(enemy_data.name)
        if self._current_scripted_enemy is not None:
            self._current_scripted_enemy["defeated"] = True
        self._current_scripted_enemy = None
        self.game.audio.play_music(self._current_music_track)

    def on_combat_end(self):
        """Called by CombatState on defeat or flee."""
        self._current_scripted_enemy = None
        self.game.audio.play_music(self._current_music_track)

    def _start_random_combat(self):
        from bit_flippers.combat import ENEMY_TYPES
        from bit_flippers.states.combat import CombatState

        if not self._current_encounter_table:
            return
        enemy_data = ENEMY_TYPES[random.choice(self._current_encounter_table)]
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
        map_source = self.tiled_renderer
        self.camera.update(
            int(self.player_visual_x) + TILE_SIZE // 2,
            int(self.player_visual_y) + TILE_SIZE // 2,
            map_source.width_px,
            map_source.height_px,
        )

    def _draw_icon_markers(self, screen):
        """Draw branding icons on wall tiles adjacent to shop doors."""
        if not self._current_icon_markers:
            return
        for marker in self._current_icon_markers:
            world_rect = pygame.Rect(
                marker.x * TILE_SIZE, marker.y * TILE_SIZE, TILE_SIZE, TILE_SIZE
            )
            sr = self.camera.apply(world_rect)
            cx, cy = sr.centerx, sr.centery
            c = marker.color
            if marker.icon_type == "sword":
                # Simple sword: vertical blade + crossguard
                pygame.draw.line(screen, c, (cx, cy - 7), (cx, cy + 7), 2)
                pygame.draw.line(screen, c, (cx - 4, cy - 2), (cx + 4, cy - 2), 2)
                pygame.draw.line(screen, c, (cx - 1, cy + 7), (cx + 1, cy + 7), 2)
            elif marker.icon_type == "shield":
                # Simple shield: rounded rect outline
                shield_rect = pygame.Rect(cx - 5, cy - 6, 10, 12)
                pygame.draw.rect(screen, c, shield_rect, 2, border_radius=3)
                pygame.draw.line(screen, c, (cx, cy - 4), (cx, cy + 4), 2)

    def draw(self, screen):
        # Clip game world to the viewport area (top 360px)
        viewport_rect = pygame.Rect(0, 0, SCREEN_WIDTH, VIEWPORT_HEIGHT)
        screen.set_clip(viewport_rect)

        # Draw map tiles (below sprites)
        self.tiled_renderer.draw_below(screen, self.camera)
        self._draw_icon_markers(screen)

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

        # Draw map tiles (above sprites) for Tiled maps
        if self.tiled_renderer:
            self.tiled_renderer.draw_above(screen, self.camera)

        # Pickup notification (stays in viewport area)
        if self.pickup_message:
            msg_surf = self.hud_font.render(self.pickup_message, True, (255, 220, 100))
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, 50))

        # Remove clip before drawing HUD
        screen.set_clip(None)

        # HUD panel in the bottom 120px
        self._draw_hud(screen)

    def _draw_hud(self, screen):
        # Background panel
        pygame.draw.rect(screen, COLOR_HUD_BG, (0, HUD_Y, SCREEN_WIDTH, HUD_HEIGHT))
        pygame.draw.line(screen, COLOR_HUD_BORDER, (0, HUD_Y), (SCREEN_WIDTH, HUD_Y), 2)

        pad = 10
        bar_width, bar_height = 120, 12
        col_left = pad
        col_mid = SCREEN_WIDTH // 3 + pad
        col_right = 2 * SCREEN_WIDTH // 3 + pad

        # --- LEFT COLUMN: Level + HP/SP/XP bars ---
        y = HUD_Y + pad
        level_label = self.hud_font.render(f"Lv {self.stats.level}", True, (255, 255, 255))
        screen.blit(level_label, (col_left, y))
        y += 20

        bar_x = col_left + 28
        # HP bar
        hp_ratio = self.stats.current_hp / self.stats.max_hp if self.stats.max_hp > 0 else 0
        hp_label = self.hud_font.render("HP", True, (255, 255, 255))
        screen.blit(hp_label, (col_left, y))
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y + 2, bar_width, bar_height))
        hp_color = (80, 200, 80) if hp_ratio > 0.5 else (200, 200, 40) if hp_ratio > 0.25 else (200, 60, 60)
        pygame.draw.rect(screen, hp_color, (bar_x, y + 2, int(bar_width * hp_ratio), bar_height))
        pygame.draw.rect(screen, (180, 180, 180), (bar_x, y + 2, bar_width, bar_height), 1)
        hp_text = self.hud_font.render(f"{self.stats.current_hp}/{self.stats.max_hp}", True, (255, 255, 255))
        screen.blit(hp_text, (bar_x + bar_width + 6, y + 1))
        y += 20

        # SP bar
        sp_ratio = self.stats.current_sp / self.stats.max_sp if self.stats.max_sp > 0 else 0
        sp_label = self.hud_font.render("SP", True, (255, 255, 255))
        screen.blit(sp_label, (col_left, y))
        pygame.draw.rect(screen, (40, 40, 40), (bar_x, y + 2, bar_width, bar_height))
        pygame.draw.rect(screen, COLOR_SP_BAR, (bar_x, y + 2, int(bar_width * sp_ratio), bar_height))
        pygame.draw.rect(screen, (140, 140, 140), (bar_x, y + 2, bar_width, bar_height), 1)
        sp_text = self.hud_font.render(f"{self.stats.current_sp}/{self.stats.max_sp}", True, (255, 255, 255))
        screen.blit(sp_text, (bar_x + bar_width + 6, y + 1))
        y += 20

        # XP bar
        xp_label = self.hud_font.render("XP", True, (255, 255, 255))
        screen.blit(xp_label, (col_left, y))
        xp_needed = self.xp_to_next_level()
        xp_ratio = self.stats.xp / xp_needed if xp_needed > 0 else 0
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y + 2, bar_width, bar_height))
        pygame.draw.rect(screen, COLOR_XP_BAR, (bar_x, y + 2, int(bar_width * xp_ratio), bar_height))
        pygame.draw.rect(screen, (180, 180, 180), (bar_x, y + 2, bar_width, bar_height), 1)
        xp_text = self.hud_font.render(f"{self.stats.xp}/{xp_needed}", True, (255, 255, 255))
        screen.blit(xp_text, (bar_x + bar_width + 6, y + 1))

        # --- CENTER COLUMN: Money + map name ---
        y = HUD_Y + pad
        money_label = self.hud_font.render(f"Scrap: {self.stats.money}", True, COLOR_MONEY_TEXT)
        screen.blit(money_label, (col_mid, y))
        y += 20

        if self._current_display_name:
            map_label = self.hud_font.render(self._current_display_name, True, (200, 200, 200))
            screen.blit(map_label, (col_mid, y))

        # --- RIGHT COLUMN: Conditional notifications ---
        y = HUD_Y + pad
        if self.stats.unspent_points > 0:
            pts_label = self.hud_font.render(
                f"+{self.stats.unspent_points} pts [C]", True, (255, 220, 100)
            )
            screen.blit(pts_label, (col_right, y))
            y += 20

        if self.player_skills.skill_points > 0:
            skill_label = self.hud_font.render(
                f"+{self.player_skills.skill_points} skill pts [K]", True, (100, 180, 255)
            )
            screen.blit(skill_label, (col_right, y))
            y += 20

        if self.player_quests.has_completable():
            quest_label = self.hud_font.render("! Quest ready [Q]", True, (100, 255, 100))
            screen.blit(quest_label, (col_right, y))

        # Vertical dividers between columns
        div_x1 = SCREEN_WIDTH // 3
        div_x2 = 2 * SCREEN_WIDTH // 3
        pygame.draw.line(screen, COLOR_HUD_BORDER, (div_x1, HUD_Y + 6), (div_x1, HUD_Y + HUD_HEIGHT - 6), 1)
        pygame.draw.line(screen, COLOR_HUD_BORDER, (div_x2, HUD_Y + 6), (div_x2, HUD_Y + HUD_HEIGHT - 6), 1)

    def _try_move(self, key):
        dx, dy, facing = DIRECTION_MAP[key]
        self.player_facing = facing

        new_x = self.player_x + dx
        new_y = self.player_y + dy

        if self.tiled_renderer.is_walkable(new_x, new_y) and not self._npc_at(new_x, new_y):
            self.player_x = new_x
            self.player_y = new_y
            self.steps_since_encounter += 1

            # Check for door transition
            for door in self._current_doors:
                if door.x == new_x and door.y == new_y:
                    self._handle_door_transition()
                    return

            # Scrap pickup
            if (new_x, new_y) in self.scrap_remaining:
                self.scrap_remaining.discard((new_x, new_y))
                self.inventory.add("Scrap Metal")
                self.stats.money += 1
                self.game.audio.play_sfx("pickup")
                msg = "Picked up Scrap Metal!"
                # 25% chance for a bonus consumable
                if random.random() < SCRAP_BONUS_ITEM_CHANCE:
                    bonus = random.choice(["Repair Kit", "Voltage Spike", "Iron Plating"])
                    self.inventory.add(bonus)
                    msg += f" Also found {bonus}!"
                self.pickup_message = msg
                self.pickup_message_timer = PICKUP_MESSAGE_DURATION

            # Random encounter check
            if (
                self._current_encounter_table
                and self.steps_since_encounter >= MIN_STEPS_BETWEEN_ENCOUNTERS
                and self.tiled_renderer.is_walkable(new_x, new_y)
                and random.random() < self._current_encounter_chance
            ):
                self._start_random_combat()
